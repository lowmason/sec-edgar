import contextlib
import datetime
import io
import json
import os
from unittest import mock

from sec_filing_data import cli
from sec_filing_data import fetch as fetch_module
from sec_filing_data.client import exclusive_lock
from sec_filing_data.fetch import run_fetch_partners
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import STAGE4_LIMITS, append, ledger_usage, read_ledger
from sec_filing_data.partners import (
    build_partner_fetches,
    partner_fetch_rows,
    run_partner_fetches,
)
from sec_filing_data.sample import ARCHIVES
from sec_filing_data.tables import SCHEMAS, read_table, write_table
from tests.test_client import USER_AGENT, FakeResponse, fill_ledger
from tests.test_commands import (
    FIXTURE_BYTES,
    FIXTURE_SHA256,
    CommandTestCase,
    FixtureSession,
    accession_of,
    request_record,
    response_record,
)


def partner_row(number: int, rule: str = "candidate_amendment", sampled: int = 900) -> dict:
    """A `partners` row for accession `accession_of(number)`."""
    accession = accession_of(number)
    filename = f"edgar/data/1000/{accession}.txt"
    return {
        "accession_number": accession,
        "form_type": "D",
        "cik": 1000,
        "company_name": "ACME CORP",
        "date_filed": datetime.date(2026, 8, 3),
        "filename": filename,
        "url": ARCHIVES + filename,
        "rule": rule,
        "sampled_accession": accession_of(sampled),
    }


class FetchPartnersTestCase(CommandTestCase):
    def write_partners(self, rows: list[dict]) -> list[dict]:
        write_table(self.layout.stage4_view, "partners", rows)
        return rows

    def fetch_partners(self, session: FixtureSession, layout: Layout | None = None) -> int:
        return run_fetch_partners(
            layout or self.layout,
            user_agent=USER_AGENT,
            session=session,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
        )

    def stage4_fetches(self) -> list[dict]:
        return read_table(self.layout.stage4_view, "fetches").to_pylist()

    def stage4_outcomes(self) -> list[str]:
        return [row["outcome"] for row in self.stage4_fetches()]

    def stage4_records(self, event: str) -> list[dict]:
        records = read_ledger(self.layout.stage4_ledger)
        return [record for record in records if record["event"] == event]

    def part_of_partner(self, number: int):
        submission = self.layout.partner_submission(accession_of(number))
        return submission.with_name(submission.name + ".part")


class FetchPartnersTests(FetchPartnersTestCase):
    def test_fetch_partners_walks_distinct_partners_in_accession_order(self):
        # Three accessions, written out of order. Accession 2 is on two rows.
        self.write_partners(
            [
                partner_row(3),
                partner_row(2, "original_previous_accession", sampled=901),
                partner_row(1),
                partner_row(2, "candidate_amendment", sampled=902),
            ]
        )
        accessions = [accession_of(number) for number in (1, 2, 3)]
        session = FixtureSession()

        code = self.fetch_partners(session)

        self.assertEqual(code, 0)
        self.assertEqual(
            session.urls, [f"{ARCHIVES}edgar/data/1000/{accession}.txt" for accession in accessions]
        )
        self.assertEqual([record["key"] for record in self.stage4_records("request")], accessions)
        table = read_table(self.layout.stage4_view, "fetches")
        self.assertEqual(table.schema, SCHEMAS["fetches"])
        fetches = table.to_pylist()
        self.assertEqual([row["accession_number"] for row in fetches], accessions)
        responses = {record["key"]: record for record in self.stage4_records("response")}
        for row in fetches:
            accession = row["accession_number"]
            path = self.layout.partner_submission(accession)
            self.assertEqual(path.read_bytes(), FIXTURE_BYTES)
            self.assertEqual(
                row,
                {
                    "accession_number": accession,
                    "form_type": "D",
                    "outcome": "ok",
                    "reason": None,
                    "status": 200,
                    "attempts": 1,
                    "wire_bytes": len(FIXTURE_BYTES),
                    "body_bytes": len(FIXTURE_BYTES),
                    "sha256": FIXTURE_SHA256,
                    "fetched_at": datetime.datetime.fromisoformat(responses[accession]["at"]),
                    "path": str(path),
                },
            )
        self.assertEqual(self.stage4_outcomes(), ["ok", "ok", "ok"])
        # Nothing goes to the Stage 1 or Stage 2 places.
        self.assertFalse(self.layout.bytes_dir.exists())
        self.assertFalse(self.layout.ledger.exists())
        self.assertFalse(self.layout.stage2.exists())
        self.assertFalse(self.layout.tables.exists())

    def test_fetch_partners_stops_at_30_requests(self):
        self.write_partners([partner_row(number) for number in range(1, 32)])
        session = FixtureSession()

        code = self.fetch_partners(session)

        self.assertEqual(code, 5)
        self.assertEqual(len(session.urls), 30)
        self.assertEqual(ledger_usage(self.layout.stage4_ledger).requests, 30)
        self.assertEqual(self.stage4_outcomes(), ["ok"] * 30 + ["budget"])
        self.assertFalse(self.layout.partner_submission(accession_of(31)).exists())

    def test_fetch_partners_stops_at_the_wire_byte_limit(self):
        self.write_partners([partner_row(1), partner_row(2)])
        self.layout.stage4.mkdir(exist_ok=True)
        fill_ledger(self.layout.stage4_ledger, [48_000_000])
        first = partner_row(1)["url"]
        session = FixtureSession({first: FakeResponse(200, [b"x" * 1_500_000])})

        code = self.fetch_partners(session)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [first])
        # The reply leaves less than the client's margin of budget, so the client stops.
        self.assertEqual(self.stage4_outcomes(), ["budget", "budget"])
        self.assertEqual(ledger_usage(self.layout.stage4_ledger).requests, 2)
        self.assertEqual(self.stage4_records("response")[-1]["wire_bytes"], 1_500_000)

    def test_fetch_partners_returns_5_at_once_when_spent(self):
        self.write_partners([partner_row(1), partner_row(2)])
        self.layout.stage4.mkdir(exist_ok=True)
        fill_ledger(self.layout.stage4_ledger, [100] * STAGE4_LIMITS.requests)
        session = FixtureSession()

        code = self.fetch_partners(session)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [])
        self.assertEqual(self.stage4_outcomes(), ["budget", "budget"])
        self.assertEqual(ledger_usage(self.layout.stage4_ledger).requests, 30)

    def test_fetch_partners_skips_held_partners_and_tries_failed_ones_again(self):
        self.write_partners([partner_row(2), partner_row(1)])
        failed, held = partner_row(1), partner_row(2)
        first = FixtureSession({failed["url"]: FakeResponse(404, [b"not found"])})

        self.assertEqual(self.fetch_partners(first), 0)

        self.assertEqual(first.urls, [failed["url"], held["url"]])
        self.assertEqual(self.stage4_outcomes(), ["not_found", "ok"])
        second = FixtureSession()

        self.assertEqual(self.fetch_partners(second), 0)

        self.assertEqual(second.urls, [failed["url"]])
        fetches = self.stage4_fetches()
        self.assertEqual([row["outcome"] for row in fetches], ["ok", "ok"])
        self.assertEqual([row["attempts"] for row in fetches], [2, 1])

    def test_a_leftover_part_file_is_replaced(self):
        self.write_partners([partner_row(1)])
        stale = self.part_of_partner(1)
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"partial")
        reply = b"the complete partner filing\n"
        session = FixtureSession({partner_row(1)["url"]: FakeResponse(200, [reply])})

        code = self.fetch_partners(session)

        self.assertEqual(code, 0)
        self.assertEqual(
            [path.name for path in self.layout.stage4_bytes.iterdir()],
            [f"{accession_of(1)}.txt"],
        )
        self.assertEqual(self.layout.partner_submission(accession_of(1)).read_bytes(), reply)
        self.assertEqual(self.stage4_outcomes(), ["ok"])

    def test_a_leftover_part_file_is_removed_when_the_budget_is_spent(self):
        self.write_partners([partner_row(1), partner_row(2)])
        self.layout.stage4.mkdir(exist_ok=True)
        fill_ledger(self.layout.stage4_ledger, [100] * (STAGE4_LIMITS.requests - 1))
        stale = self.part_of_partner(2)
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"partial")

        code = self.fetch_partners(FixtureSession())

        self.assertEqual(code, 5)
        self.assertFalse(stale.exists())
        self.assertEqual(self.stage4_outcomes(), ["ok", "budget"])

    def test_a_held_lock_refuses(self):
        # The `partners` table sits outside `stage4/`, so that `stage4/` shows what the run makes.
        layout = Layout(self.layout.root, stage4_tables_dir=self.layout.root.parent / "partners")
        write_table(layout.stage4_view, "partners", [partner_row(1)])
        session = FixtureSession()

        with exclusive_lock(layout.lock), self.assertRaises(RuntimeError) as caught:
            self.fetch_partners(session, layout)

        self.assertEqual(str(caught.exception), f"another fetch holds {layout.lock}")
        self.assertEqual(session.urls, [])
        self.assertFalse(layout.stage4.exists())

    def test_fetch_partners_exits_6_on_403(self):
        self.write_partners([partner_row(number) for number in (1, 2, 3)])
        denied = partner_row(2)["url"]
        session = FixtureSession({denied: FakeResponse(403, [b"denied"])})

        code = self.fetch_partners(session)

        self.assertEqual(code, 6)
        self.assertEqual(session.urls, [partner_row(1)["url"], denied])
        self.assertEqual(self.stage4_outcomes(), ["ok", "forbidden", "not_attempted"])
        forbidden = self.stage4_fetches()[1]
        self.assertEqual((forbidden["status"], forbidden["reason"]), (403, "HTTP 403"))

    def test_an_interrupt_still_writes_fetches(self):
        self.write_partners([partner_row(number) for number in (1, 2, 3)])
        session = FixtureSession({partner_row(2)["url"]: KeyboardInterrupt()})

        with self.assertRaises(KeyboardInterrupt):
            self.fetch_partners(session)

        self.assertEqual(self.stage4_outcomes(), ["ok", "failed", "not_attempted"])
        self.assertEqual(list(self.layout.stage4_bytes.glob("*.part")), [])

    def test_a_missing_partner_list_raises_before_the_lock_and_writes_nothing(self):
        session = FixtureSession()

        with exclusive_lock(self.layout.lock), self.assertRaises(FileNotFoundError):
            self.fetch_partners(session)

        self.assertEqual(session.urls, [])
        self.assertFalse(self.layout.stage4.exists())


class PartnerFetchRowsTests(FetchPartnersTestCase):
    def test_rows_follow_the_distinct_partners_the_ledger_and_the_disk(self):
        rows = self.write_partners(
            [partner_row(3), partner_row(2), partner_row(1), partner_row(1, sampled=901)]
        )
        held, failed, untouched = (accession_of(number) for number in (1, 2, 3))
        self.layout.stage4_bytes.mkdir(parents=True)
        self.layout.partner_submission(held).write_bytes(FIXTURE_BYTES)
        append(self.layout.stage4_ledger, request_record("r1", failed))
        append(
            self.layout.stage4_ledger,
            response_record("r1", failed, status=404, outcome="not_found", reason="HTTP 404"),
        )

        built = build_partner_fetches(self.layout)

        self.assertEqual(
            built, partner_fetch_rows(self.layout, rows, read_ledger(self.layout.stage4_ledger))
        )
        self.assertEqual([row["accession_number"] for row in built], [held, failed, untouched])
        self.assertEqual([row["outcome"] for row in built], ["ok", "not_found", "not_attempted"])
        self.assertEqual(built[0]["path"], str(self.layout.partner_submission(held)))
        self.assertFalse(self.layout.stage4_view.table("fetches").exists())

        written = run_partner_fetches(self.layout)

        self.assertEqual(written, built)
        self.assertEqual(self.stage4_fetches(), built)

    def test_rows_read_the_stage_4_budget(self):
        rows = self.write_partners([partner_row(1)])
        self.layout.stage4.mkdir(exist_ok=True)
        fill_ledger(self.layout.stage4_ledger, [100] * STAGE4_LIMITS.requests)

        built = partner_fetch_rows(self.layout, rows, read_ledger(self.layout.stage4_ledger))

        self.assertEqual([row["outcome"] for row in built], ["budget"])

    def test_the_builders_need_the_partner_list(self):
        with self.assertRaises(FileNotFoundError):
            build_partner_fetches(self.layout)
        with self.assertRaises(FileNotFoundError):
            run_partner_fetches(self.layout)

        self.assertFalse(self.layout.stage4.exists())


class FetchPartnersCliTests(FetchPartnersTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_fetch_partners_needs_the_partner_list(self):
        with mock.patch.dict(os.environ, {"SEC_USER_AGENT": USER_AGENT}):
            code, stdout, stderr = self.run_cli("fetch-partners")

        path = self.layout.root / "stage4" / "tables" / "partners.parquet"
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, f"error: {path} is missing: run partners first\n")
        self.assertFalse(self.layout.stage4.exists())

    def test_fetch_partners_needs_a_user_agent(self):
        self.write_partners([partner_row(1)])
        before = sorted(self.layout.root.rglob("*"))
        for environment in ({}, {"SEC_USER_AGENT": ""}):
            with mock.patch.dict(os.environ, environment):
                if not environment:
                    os.environ.pop("SEC_USER_AGENT", None)
                code, stdout, stderr = self.run_cli("fetch-partners")

            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("SEC_USER_AGENT", stderr)
            self.assertEqual(sorted(self.layout.root.rglob("*")), before)

    def run_offline(self) -> tuple[int, str, str]:
        """Run `fetch-partners` with a test User-Agent and a session that serves the fixture."""
        real_run = fetch_module.run_fetch_partners

        def offline_run(layout, *, user_agent):
            self.assertEqual(user_agent, USER_AGENT)
            return real_run(
                layout,
                user_agent=user_agent,
                session=FixtureSession(),
                monotonic=self.clock.monotonic,
                sleep=self.clock.sleep,
            )

        with (
            mock.patch.object(fetch_module, "run_fetch_partners", offline_run),
            mock.patch.dict(os.environ, {"SEC_USER_AGENT": USER_AGENT}),
        ):
            return self.run_cli("fetch-partners")

    def test_fetch_partners_prints_the_outcomes_and_the_stage_4_budget(self):
        self.write_partners([partner_row(number) for number in (1, 2, 3)])

        code, stdout, stderr = self.run_offline()

        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            stdout,
            "ok: 3\n"
            "stage 4 requests: 3 of 30\n"
            f"stage 4 wire bytes: {3 * len(FIXTURE_BYTES)} of 50000000\n",
        )
        steps = [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["fetch-partners"])

    def test_fetch_partners_gives_the_exit_code_of_the_run(self):
        self.write_partners([partner_row(1), partner_row(2)])
        self.layout.stage4.mkdir(exist_ok=True)
        fill_ledger(self.layout.stage4_ledger, [100] * STAGE4_LIMITS.requests)

        code, stdout, stderr = self.run_offline()

        self.assertEqual((code, stderr), (5, ""))
        self.assertEqual(
            stdout,
            "budget: 2\nstage 4 requests: 30 of 30\nstage 4 wire bytes: 3000 of 50000000\n",
        )
