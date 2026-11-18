import contextlib
import datetime
import hashlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

import pyarrow as pa

from sec_filing_data import cli
from sec_filing_data import fetch as fetch_module
from sec_filing_data.client import exclusive_lock
from sec_filing_data.fetch import run_refetch
from sec_filing_data.ledger import append, ledger_usage, read_ledger
from sec_filing_data.refetches import build_refetches, run_compare_refetches
from sec_filing_data.submissions import run_envelopes
from sec_filing_data.tables import SCHEMAS, read_table
from tests.test_client import USER_AGENT, FakeResponse, fill_ledger
from tests.test_commands import (
    FIXTURE_BYTES,
    FIXTURE_SHA256,
    CommandTestCase,
    FixtureSession,
    accession_of,
    request_record,
    response_record,
    sample_row,
    utc,
    xbrl_submission,
)

LAST_MODIFIED = "Fri, 14 Aug 2026 20:06:00 GMT"
REFETCH_LAST_MODIFIED = "Sat, 15 Aug 2026 10:00:00 GMT"
UNKNOWN = accession_of(99)

TIMESTAMP = pa.timestamp("us", tz="UTC")
REFETCHES_SCHEMA = pa.schema(
    [
        pa.field("accession_number", pa.string()),
        pa.field("outcome", pa.string()),
        pa.field("stage1_sha256", pa.string()),
        pa.field("refetch_sha256", pa.string()),
        pa.field("sha256_equal", pa.bool_()),
        pa.field("stage1_last_modified_at", TIMESTAMP),
        pa.field("refetch_last_modified_at", TIMESTAMP),
        pa.field("refetched_at", TIMESTAMP),
        pa.field("changed_header_fields", pa.string()),
        pa.field("changed_documents", pa.string()),
    ]
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digests(root: Path, *, skip: Path | None = None) -> dict[str, str]:
    """The SHA-256 of each file under `root`, by its path relative to `root`."""
    return {
        str(path.relative_to(root)): sha256(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file() and (skip is None or not path.is_relative_to(skip))
    }


def no_refetch(accession: str, outcome: str) -> dict:
    """A `refetches` row with no refetch values, for a filing fetched as the fixture in Stage 1."""
    return {
        "accession_number": accession,
        "outcome": outcome,
        "stage1_sha256": FIXTURE_SHA256,
        "refetch_sha256": None,
        "sha256_equal": None,
        "stage1_last_modified_at": None,
        "refetch_last_modified_at": None,
        "refetched_at": None,
        "changed_header_fields": None,
        "changed_documents": None,
    }


class RefetchTestCase(CommandTestCase):
    """A two-row sample, A and B. Each test fetches it in Stage 1 first."""

    def setUp(self) -> None:
        super().setUp()
        rows = self.write_sample([sample_row(1, "quota", "10-K"), sample_row(2, "quota", "10-K")])
        self.a, self.b = (row["accession_number"] for row in rows)
        self.url_a, self.url_b = (row["url"] for row in rows)

    def fetch_stage1(self, replies: dict | None = None) -> None:
        self.assertEqual(self.fetch(FixtureSession(replies)), 0)

    def refetch(self, session: FixtureSession, *accessions: str) -> int:
        return run_refetch(
            self.layout,
            user_agent=USER_AGENT,
            accessions=list(accessions),
            session=session,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
        )

    def stage2_records(self, event: str) -> list[dict]:
        return [
            record for record in read_ledger(self.layout.stage2_ledger) if record["event"] == event
        ]


class RefetchTests(RefetchTestCase):
    def test_refetch_writes_only_under_stage2(self):
        self.fetch_stage1()
        stage1_ledger = self.layout.ledger.read_bytes()
        stage1_bytes = file_digests(self.layout.bytes_dir)
        outside = file_digests(self.layout.root, skip=self.layout.stage2)
        session = FixtureSession()

        code = self.refetch(session, self.a)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [self.url_a])
        self.assertEqual(self.layout.refetched(self.a).read_bytes(), FIXTURE_BYTES)
        (request,) = self.stage2_records("request")
        (response,) = self.stage2_records("response")
        self.assertEqual((request["key"], request["url"]), (self.a, self.url_a))
        self.assertEqual(
            (response["id"], response["outcome"], response["sha256"]),
            (request["id"], "ok", FIXTURE_SHA256),
        )
        self.assertEqual(self.layout.ledger.read_bytes(), stage1_ledger)
        self.assertEqual(file_digests(self.layout.bytes_dir), stage1_bytes)
        self.assertEqual(file_digests(self.layout.root, skip=self.layout.stage2), outside)
        self.assertEqual(
            sorted(file_digests(self.layout.stage2)),
            ["fetch-log.jsonl", f"refetch/{self.a}.txt"],
        )

    def test_refetch_refuses_an_unknown_accession(self):
        self.fetch_stage1()
        stage1_ledger = self.layout.ledger.read_bytes()
        # The whole list is checked before the walk, and the first unknown accession is named.
        for accessions in ([UNKNOWN], [self.a, UNKNOWN], [self.a, UNKNOWN, accession_of(98)]):
            with self.subTest(accessions=accessions):
                session = FixtureSession()

                with self.assertRaises(ValueError) as caught:
                    self.refetch(session, *accessions)

                self.assertEqual(str(caught.exception), f"{UNKNOWN} is not in sample")
                self.assertEqual(session.urls, [])
                self.assertFalse(self.layout.stage2.exists())
                self.assertEqual(self.layout.ledger.read_bytes(), stage1_ledger)

    def test_an_unknown_accession_is_refused_before_the_lock(self):
        self.fetch_stage1()
        session = FixtureSession()

        with exclusive_lock(self.layout.lock), self.assertRaises(ValueError):
            self.refetch(session, UNKNOWN)

        self.assertEqual(session.urls, [])
        self.assertFalse(self.layout.stage2.exists())

    def test_refetch_refuses_the_21st_request(self):
        self.fetch_stage1()
        self.layout.stage2.mkdir()
        fill_ledger(self.layout.stage2_ledger, [0] * 20)
        before = self.layout.stage2_ledger.read_bytes()
        session = FixtureSession()

        code = self.refetch(session, self.a)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [])
        self.assertEqual(self.layout.stage2_ledger.read_bytes(), before)
        self.assertFalse(self.layout.refetched(self.a).exists())

    def test_the_20th_request_is_sent(self):
        self.fetch_stage1()
        self.layout.stage2.mkdir()
        fill_ledger(self.layout.stage2_ledger, [0] * 19)
        session = FixtureSession()

        code = self.refetch(session, self.a, self.b)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [self.url_a])
        self.assertEqual(self.layout.refetched(self.a).read_bytes(), FIXTURE_BYTES)
        self.assertEqual(ledger_usage(self.layout.stage2_ledger).requests, 20)

    def test_interrupted_refetch_refuses_the_next(self):
        self.fetch_stage1()
        self.layout.stage2.mkdir()
        append(self.layout.stage2_ledger, request_record("r1", self.a))
        before = self.layout.stage2_ledger.read_bytes()
        session = FixtureSession()

        code = self.refetch(session, self.b)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [])
        self.assertEqual(self.layout.stage2_ledger.read_bytes(), before)
        self.assertEqual(build_refetches(self.layout), [no_refetch(self.a, "no_response")])

    def test_each_refetch_happens_once(self):
        self.fetch_stage1()
        session = FixtureSession()

        self.assertEqual(self.refetch(session, self.a, self.a), 0)
        self.assertEqual(self.refetch(session, self.a), 0)
        self.layout.refetched(self.a).unlink()
        self.assertEqual(self.refetch(session, self.a), 0)

        self.assertEqual(session.urls, [self.url_a])
        self.assertEqual(len(self.stage2_records("request")), 1)

    def test_a_failed_refetch_is_never_retried(self):
        self.fetch_stage1()
        self.assertEqual(
            self.refetch(FixtureSession({self.url_a: FakeResponse(404, [b"missing"])}), self.a), 0
        )
        session = FixtureSession()

        code = self.refetch(session, self.a, self.b)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [self.url_b])
        self.assertFalse(self.layout.refetched(self.a).exists())
        self.assertEqual(
            [record["key"] for record in self.stage2_records("request")], [self.a, self.b]
        )

    def test_refetch_takes_the_fetch_lock(self):
        self.fetch_stage1()
        before = file_digests(self.layout.root)
        session = FixtureSession()

        with exclusive_lock(self.layout.lock), self.assertRaises(RuntimeError):
            self.refetch(session, self.a)

        self.assertEqual(session.urls, [])
        self.assertFalse(self.layout.stage2.exists())
        self.assertEqual(file_digests(self.layout.root), before)

    def test_a_forbidden_refetch_stops_the_walk(self):
        self.fetch_stage1()
        session = FixtureSession({self.url_a: FakeResponse(403, [b"denied"])})

        code = self.refetch(session, self.a, self.b)

        self.assertEqual(code, 6)
        self.assertEqual(session.urls, [self.url_a])


class RefetchesTableTests(RefetchTestCase):
    def test_refetches_gives_an_equal_row_and_a_changed_row(self):
        stage1 = xbrl_submission("1", [None])
        self.fetch_stage1(
            {
                self.url_a: FakeResponse(200, [stage1], {"Last-Modified": LAST_MODIFIED}),
                self.url_b: FakeResponse(200, [stage1], {"Last-Modified": LAST_MODIFIED}),
            }
        )
        changed = xbrl_submission("1", ["changed"], date_as_of_change="20260815")
        session = FixtureSession(
            {
                self.url_a: FakeResponse(200, [stage1], {"Last-Modified": REFETCH_LAST_MODIFIED}),
                self.url_b: FakeResponse(200, [changed]),
            }
        )
        self.assertEqual(self.refetch(session, self.a, self.b), 0)
        refetched_at = {
            record["key"]: datetime.datetime.fromisoformat(record["at"])
            for record in self.stage2_records("response")
        }

        code = run_compare_refetches(self.layout)

        self.assertEqual(code, 0)
        table = read_table(self.layout, "refetches")
        self.assertEqual(table.schema, REFETCHES_SCHEMA)
        self.assertEqual(SCHEMAS["refetches"], REFETCHES_SCHEMA)
        self.assertEqual(
            table.to_pylist(),
            [
                {
                    "accession_number": self.a,
                    "outcome": "ok",
                    "stage1_sha256": sha256(stage1),
                    "refetch_sha256": sha256(stage1),
                    "sha256_equal": True,
                    "stage1_last_modified_at": utc(2026, 8, 14, 20, 6),
                    "refetch_last_modified_at": utc(2026, 8, 15, 10, 0),
                    "refetched_at": refetched_at[self.a],
                    "changed_header_fields": None,
                    "changed_documents": None,
                },
                {
                    "accession_number": self.b,
                    "outcome": "ok",
                    "stage1_sha256": sha256(stage1),
                    "refetch_sha256": sha256(changed),
                    "sha256_equal": False,
                    "stage1_last_modified_at": utc(2026, 8, 14, 20, 6),
                    "refetch_last_modified_at": None,
                    "refetched_at": refetched_at[self.b],
                    "changed_header_fields": "DATE AS OF CHANGE",
                    "changed_documents": "1",
                },
            ],
        )
        self.assertNotEqual(refetched_at[self.a], refetched_at[self.b])

    def test_a_failed_refetch_gives_a_row(self):
        self.fetch_stage1()
        session = FixtureSession({self.url_a: FakeResponse(404, [b"missing"])})
        self.assertEqual(self.refetch(session, self.a), 0)

        rows = build_refetches(self.layout)

        self.assertEqual(rows, [no_refetch(self.a, "not_found")])

    def test_stage2_never_reaches_the_stage1_tables(self):
        self.fetch_stage1(
            {self.url_a: FakeResponse(200, [FIXTURE_BYTES], {"Last-Modified": LAST_MODIFIED})}
        )
        run_envelopes(self.layout)
        names = ("filings", "parties", "documents")
        before = {name: read_table(self.layout, name).to_pylist() for name in names}
        self.assertEqual(before["filings"][0]["last_modified_at"], utc(2026, 8, 14, 20, 6))
        session = FixtureSession(
            {
                self.url_a: FakeResponse(
                    200, [FIXTURE_BYTES], {"Last-Modified": REFETCH_LAST_MODIFIED}
                ),
                self.url_b: FakeResponse(200, [xbrl_submission("1", ["changed"])]),
            }
        )
        self.assertEqual(self.refetch(session, self.a, self.b), 0)

        run_envelopes(self.layout)

        for name in names:
            with self.subTest(table=name):
                self.assertEqual(read_table(self.layout, name).to_pylist(), before[name])


class BuildRefetchesTests(CommandTestCase):
    def put_copies(self, accession: str, stage1: bytes, refetch: bytes) -> None:
        """Both copies of a filing on disk, each with an `ok` record in its own ledger."""
        self.layout.bytes_dir.mkdir(exist_ok=True)
        self.layout.refetch_dir.mkdir(parents=True, exist_ok=True)
        self.layout.submission(accession).write_bytes(stage1)
        self.layout.refetched(accession).write_bytes(refetch)
        for ledger, copy, prefix in (
            (self.layout.ledger, stage1, "s1"),
            (self.layout.stage2_ledger, refetch, "s2"),
        ):
            append(ledger, request_record(f"{prefix}-{accession}", accession))
            append(
                ledger,
                response_record(
                    f"{prefix}-{accession}",
                    accession,
                    wire_bytes=len(copy),
                    body_bytes=len(copy),
                    sha256=sha256(copy),
                ),
            )

    def test_changes_name_the_header_fields_and_the_documents(self):
        base = xbrl_submission("1", [None, "two"])
        no_sequence = base.replace(b"<SEQUENCE>2\n", b"")
        cases = [
            ("equal", base, base, None, None),
            # A longer value moves every document's offset, but no document changes.
            (
                "longer header value",
                base,
                xbrl_submission("12", [None, "two"]),
                "PUBLIC DOCUMENT COUNT",
                "",
            ),
            (
                "field only in the refetch",
                base,
                base.replace(
                    b"FILED AS OF DATE:", b"EFFECTIVENESS DATE:\t\t20260815\nFILED AS OF DATE:"
                ),
                "EFFECTIVENESS DATE",
                "",
            ),
            ("parties", base, base.replace(b"ACME CORP", b"ACME CORPORATION"), "parties", ""),
            (
                "acceptance",
                base,
                xbrl_submission("1", [None, "two"], acceptance=False),
                "ACCEPTANCE-DATETIME",
                "",
            ),
            (
                "two header changes",
                base,
                xbrl_submission(
                    "1", [None, "two"], date_as_of_change="20260815", private_to_public=True
                ),
                "DATE AS OF CHANGE;PRIVATE-TO-PUBLIC",
                "",
            ),
            ("document description", base, xbrl_submission("1", ["one", "two"]), "", "1"),
            ("document text", base, base.replace(b"\ntext\n", b"\nnew text\n"), "", "1;2"),
            ("added document", base, xbrl_submission("1", [None, "two", None]), "", "3"),
            (
                "document with no sequence",
                no_sequence,
                no_sequence.replace(b"<DESCRIPTION>two", b"<DESCRIPTION>TWO"),
                "",
                "#2",
            ),
            ("refetch does not parse", base, b"not a submission\n", "unparsed", "unparsed"),
            ("stage 1 does not parse", b"not a submission\n", base, "unparsed", "unparsed"),
        ]
        accessions = [accession_of(10 + number) for number in range(len(cases))]
        for accession, (_, stage1, refetch, _, _) in zip(accessions, cases, strict=True):
            self.put_copies(accession, stage1, refetch)

        rows = build_refetches(self.layout)

        self.assertEqual([row["accession_number"] for row in rows], accessions)
        for row, (name, stage1, refetch, header, documents) in zip(rows, cases, strict=True):
            with self.subTest(case=name):
                self.assertEqual(row["outcome"], "ok")
                self.assertEqual(row["sha256_equal"], stage1 == refetch)
                self.assertEqual(
                    (row["changed_header_fields"], row["changed_documents"]), (header, documents)
                )

    def test_outcome_comes_from_the_last_request_of_each_key(self):
        killed, retried, answered, lost = (accession_of(number) for number in (5, 3, 4, 1))
        self.layout.stage2.mkdir()
        for record in [
            request_record("k1", killed),
            response_record("k1", killed, status=503, outcome="retry", reason="HTTP 503"),
            request_record("r1", retried),
            response_record("r1", retried, status=503, outcome="retry", reason="HTTP 503"),
            request_record("k2", killed, 2),
            request_record("a1", answered),
            request_record("a2", answered, 2),
            response_record("a2", answered, status=404, outcome="not_found", reason="HTTP 404"),
            # An ok record whose refetch file is missing gives no refetch values.
            request_record("l1", lost),
            response_record("l1", lost, wire_bytes=60, body_bytes=60, sha256="c" * 64),
        ]:
            append(self.layout.stage2_ledger, record)

        rows = build_refetches(self.layout)

        self.assertEqual(
            [(row["accession_number"], row["outcome"]) for row in rows],
            [(killed, "no_response"), (retried, "failed"), (answered, "not_found"), (lost, "ok")],
        )
        for row in rows:
            with self.subTest(accession=row["accession_number"]):
                expected = no_refetch(row["accession_number"], row["outcome"])
                self.assertEqual(row, {**expected, "stage1_sha256": None})

    def test_compare_refetches_without_a_stage2_ledger_writes_no_rows(self):
        code = run_compare_refetches(self.layout)

        self.assertEqual(code, 0)
        table = read_table(self.layout, "refetches")
        self.assertEqual(table.num_rows, 0)
        self.assertEqual(table.schema, REFETCHES_SCHEMA)
        self.assertFalse(self.layout.stage2.exists())


class RefetchCliTests(RefetchTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()

    def offline(self, sessions: list[FixtureSession], calls: list) -> contextlib.ExitStack:
        """Patch `fetch.run_refetch` to use the next of `sessions`, and set the User-Agent."""
        real_run_refetch = fetch_module.run_refetch

        def offline_run_refetch(layout, *, user_agent, accessions):
            calls.append((user_agent, list(accessions)))
            return real_run_refetch(
                layout,
                user_agent=user_agent,
                accessions=accessions,
                session=sessions.pop(0),
                monotonic=self.clock.monotonic,
                sleep=self.clock.sleep,
            )

        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(fetch_module, "run_refetch", offline_run_refetch))
        stack.enter_context(mock.patch.dict(os.environ, {"SEC_USER_AGENT": USER_AGENT}))
        return stack

    def steps(self) -> list[str]:
        return [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]

    def test_refetch_needs_a_user_agent(self):
        self.fetch_stage1()
        before = sorted(self.layout.root.rglob("*"))
        digests = file_digests(self.layout.root)
        for environment in ({}, {"SEC_USER_AGENT": ""}, {"SEC_USER_AGENT": "  "}):
            with self.subTest(environment=environment):
                with mock.patch.dict(os.environ, environment):
                    if not environment:
                        os.environ.pop("SEC_USER_AGENT", None)
                    code, stdout, stderr = self.run_cli("refetch", "--accession", self.a)

                self.assertEqual(code, 2)
                self.assertEqual(stdout, "")
                self.assertIn("SEC_USER_AGENT", stderr)
                self.assertEqual(sorted(self.layout.root.rglob("*")), before)
                self.assertEqual(file_digests(self.layout.root), digests)

    def test_refetch_and_compare_refetches_print(self):
        self.fetch_stage1()
        sessions = [FixtureSession({self.url_b: FakeResponse(403, [b"denied"])}), FixtureSession()]
        calls = []

        with self.offline(sessions, calls):
            denied = self.run_cli(
                "refetch", "--accession", self.b, "--accession", self.a, "--accession", self.b
            )
            fetched = self.run_cli("refetch", "--accession", self.a, "--accession", self.b)
        compared = self.run_cli("compare-refetches")

        self.assertEqual(
            calls, [(USER_AGENT, [self.b, self.a, self.b]), (USER_AGENT, [self.a, self.b])]
        )
        self.assertEqual(
            denied,
            (6, f"{self.b}: forbidden\n{self.a}: not refetched\nstage 2 requests: 1 of 20\n", ""),
        )
        self.assertEqual(
            fetched, (0, f"{self.a}: ok\n{self.b}: forbidden\nstage 2 requests: 2 of 20\n", "")
        )
        self.assertEqual(compared, (0, "refetches: 2\n", ""))
        self.assertEqual(read_table(self.layout, "refetches").num_rows, 2)
        self.assertEqual(self.steps(), ["refetch", "refetch", "compare-refetches"])

    def test_refetch_prints_a_spent_budget(self):
        self.fetch_stage1()
        self.layout.stage2.mkdir()
        fill_ledger(self.layout.stage2_ledger, [0] * 20)
        session = FixtureSession()

        with self.offline([session], []):
            result = self.run_cli("refetch", "--accession", self.a)

        self.assertEqual(result, (5, f"{self.a}: not refetched\nstage 2 requests: 20 of 20\n", ""))
        self.assertEqual(session.urls, [])

    def test_refetch_prints_an_error_for_an_unknown_accession(self):
        self.fetch_stage1()
        session = FixtureSession()

        with self.offline([session], []):
            result = self.run_cli("refetch", "--accession", self.a, "--accession", UNKNOWN)

        self.assertEqual(result, (2, "", f"error: {UNKNOWN} is not in sample\n"))
        self.assertEqual(session.urls, [])
        self.assertFalse(self.layout.stage2.exists())


if __name__ == "__main__":
    unittest.main()
