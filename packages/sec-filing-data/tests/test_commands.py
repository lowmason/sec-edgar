import contextlib
import datetime
import gzip
import hashlib
import io
import json
import os
import pkgutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sec_filing_data
from sec_filing_data import cli, client, ledger
from sec_filing_data import fetch as fetch_module
from sec_filing_data.client import exclusive_lock
from sec_filing_data.envelope import parse_submission
from sec_filing_data.fetch import run_fetch
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import (
    MAX_REQUESTS,
    MAX_WIRE_BYTES,
    STAGE2_LIMITS,
    Usage,
    append,
    budget_spent,
    build_fetches,
    fetch_rows,
    last_ok,
    ledger_usage,
    ok_responses,
    parse_ledger,
    read_ledger,
)
from sec_filing_data.provenance import filing_times, read_provenance, record_provenance
from sec_filing_data.report import run_report
from sec_filing_data.submissions import run_envelopes
from sec_filing_data.tables import FILING_TIME_COLUMNS, SCHEMAS, read_table, write_table
from tests.test_client import USER_AGENT, FakeClock, FakeResponse, fill_ledger

FIXTURE_BYTES = (Path(__file__).parent / "fixtures" / "submission-13f.txt").read_bytes()
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()


def utc(*parts: int) -> datetime.datetime:
    return datetime.datetime(*parts, tzinfo=datetime.UTC)


# A parsed submission with no party, no acceptance time, no filing date and no document count.
NO_PARTY = (
    b"<SEC-HEADER>\n"
    b"CONFORMED SUBMISSION TYPE:\t4\n"
    b"</SEC-HEADER>\n"
    b"<DOCUMENT>\n<TYPE>4\n<SEQUENCE>1\n<TEXT>\nownership\n</TEXT>\n</DOCUMENT>\n"
)

IDEA = "IDEA: XBRL DOCUMENT"


def accession_of(number: int) -> str:
    return f"0000000001-26-{number:06d}"


def url_of(accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/1000/{accession}.txt"


def sample_row(draw: int, stratum: str, form_type: str) -> dict:
    accession = accession_of(draw)
    return {
        "draw": draw,
        "stratum": stratum,
        "accession_number": accession,
        "form_type": form_type,
        "cik": 1000,
        "company_name": "ACME CORP",
        "date_filed": datetime.date(2026, 8, 14),
        "filename": f"edgar/data/1000/{accession}.txt",
        "url": url_of(accession),
    }


def standard_sample() -> list[dict]:
    """Two quota forms with two rows each, a repeated row naming a quota form, a uniform row."""
    return [
        sample_row(1, "quota", "10-K"),
        sample_row(2, "quota", "10-K"),
        sample_row(3, "quota", "4"),
        sample_row(4, "quota", "4"),
        sample_row(5, "repeated", "4;SC 13D"),
        sample_row(6, "uniform", "8-K"),
    ]


def index_row(number: int) -> dict:
    accession = accession_of(number)
    return {
        "line_number": number,
        "cik": 1000,
        "company_name": "ACME CORP",
        "form_type": "10-K",
        "date_filed": datetime.date(2026, 8, 14),
        "filename": f"edgar/data/1000/{accession}.txt",
        "accession_number": accession,
    }


def request_record(request_id: str, key: str, attempt: int = 1) -> dict:
    return {
        "event": "request",
        "id": request_id,
        "key": key,
        "url": url_of(key),
        "attempt": attempt,
        "at": "2026-11-16T10:00:00.000000Z",
    }


def response_record(request_id: str, key: str, **values) -> dict:
    record = {
        "event": "response",
        "id": request_id,
        "key": key,
        "status": 200,
        "wire_bytes": 0,
        "body_bytes": None,
        "sha256": None,
        "outcome": "ok",
        "reason": None,
        "content_encoding": None,
        "etag": None,
        "last_modified": None,
        "at": "2026-11-16T10:00:01.000000Z",
    }
    record.update(values)
    return record


def xbrl_submission(
    public_document_count: str,
    descriptions: list[str | None],
    *,
    date_as_of_change: str = "20260814",
    private_to_public: bool = False,
    acceptance: bool = True,
) -> bytes:
    """A submission with one party and one document per entry of `descriptions`."""
    lines = ["<SEC-HEADER>"]
    if acceptance:
        lines.append("<ACCEPTANCE-DATETIME>20260814160523")
    lines += [
        "CONFORMED SUBMISSION TYPE:\t10-Q",
        f"PUBLIC DOCUMENT COUNT:\t\t{public_document_count}",
        "FILED AS OF DATE:\t\t20260814",
        f"DATE AS OF CHANGE:\t\t{date_as_of_change}",
    ]
    if private_to_public:
        lines.append("<PRIVATE-TO-PUBLIC>")
    lines += [
        "FILER:",
        "\tCOMPANY DATA:",
        "\t\tCOMPANY CONFORMED NAME:\tACME CORP",
        "\t\tCENTRAL INDEX KEY:\t0000001000",
        "</SEC-HEADER>",
    ]
    for sequence, description in enumerate(descriptions, start=1):
        lines += ["<DOCUMENT>", "<TYPE>EX-101.INS", f"<SEQUENCE>{sequence}"]
        if description is not None:
            lines.append(f"<DESCRIPTION>{description}")
        lines += ["<TEXT>", "text", "</TEXT>", "</DOCUMENT>"]
    return ("\n".join(lines) + "\n").encode("utf-8")


class FixtureSession:
    """Serves the 13F fixture for every URL, unless `replies` scripts another reply for it."""

    def __init__(self, replies: dict | None = None) -> None:
        self.replies = dict(replies or {})
        self.urls: list[str] = []

    def get(self, url, *, headers, stream, timeout, allow_redirects):
        self.urls.append(url)
        reply = self.replies.pop(url, None)
        if reply is None:
            return FakeResponse(200, [FIXTURE_BYTES])
        if isinstance(reply, BaseException):
            raise reply
        return reply


class CommandTestCase(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.layout = Layout(Path(folder.name) / "root")
        self.layout.root.mkdir()
        self.clock = FakeClock()

    def write_sample(self, rows: list[dict]) -> list[dict]:
        """Write `rows` as the sample table, out of draw order, and return them in draw order."""
        write_table(self.layout, "sample", list(reversed(rows)))
        return rows

    def fetch(self, session: FixtureSession, **kwargs) -> int:
        return run_fetch(
            self.layout,
            user_agent=USER_AGENT,
            session=session,
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
            **kwargs,
        )

    def fetches(self) -> list[dict]:
        return read_table(self.layout, "fetches").to_pylist()

    def outcomes(self) -> list[str]:
        return [row["outcome"] for row in self.fetches()]

    def records(self, event: str) -> list[dict]:
        return [record for record in read_ledger(self.layout.ledger) if record["event"] == event]

    def part_of(self, accession: str) -> Path:
        submission = self.layout.submission(accession)
        return submission.with_name(submission.name + ".part")


class FetchTests(CommandTestCase):
    def test_fetch_walks_draw_order_and_writes_fetches(self):
        rows = self.write_sample(standard_sample())
        accessions = [row["accession_number"] for row in rows]
        session = FixtureSession()

        code = self.fetch(session)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [row["url"] for row in rows])
        self.assertEqual([record["key"] for record in self.records("request")], accessions)
        table = read_table(self.layout, "fetches")
        self.assertEqual(table.schema, SCHEMAS["fetches"])
        fetches = table.to_pylist()
        self.assertEqual([row["accession_number"] for row in fetches], accessions)
        self.assertEqual([row["form_type"] for row in fetches], [row["form_type"] for row in rows])
        responses = {record["key"]: record for record in self.records("response")}
        for row in fetches:
            accession = row["accession_number"]
            self.assertEqual(self.layout.submission(accession).read_bytes(), FIXTURE_BYTES)
            self.assertEqual(
                row,
                {
                    "accession_number": accession,
                    "form_type": row["form_type"],
                    "outcome": "ok",
                    "reason": None,
                    "status": 200,
                    "attempts": 1,
                    "wire_bytes": len(FIXTURE_BYTES),
                    "body_bytes": len(FIXTURE_BYTES),
                    "sha256": FIXTURE_SHA256,
                    "fetched_at": datetime.datetime.fromisoformat(responses[accession]["at"]),
                    "path": str(self.layout.submission(accession)),
                },
            )

    def test_per_form_limits_the_pilot(self):
        rows = self.write_sample(standard_sample())
        session = FixtureSession()

        code = self.fetch(session, per_form=1)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [rows[0]["url"], rows[2]["url"]])
        self.assertEqual(
            self.outcomes(),
            ["ok", "not_attempted", "ok", "not_attempted", "not_attempted", "not_attempted"],
        )

    def test_resume_after_interrupt(self):
        rows = self.write_sample(standard_sample()[:3])
        finished, interrupted, untouched = (row["accession_number"] for row in rows)
        # A finished filing: its bytes on disk, and its matched request and response records.
        self.layout.bytes_dir.mkdir()
        self.layout.submission(finished).write_bytes(FIXTURE_BYTES)
        append(self.layout.ledger, request_record("r1", finished))
        append(
            self.layout.ledger,
            response_record(
                "r1", finished, wire_bytes=777, body_bytes=len(FIXTURE_BYTES), sha256="a" * 64
            ),
        )
        # A hard kill during the next filing: a .part file and a request with no response.
        self.part_of(interrupted).write_bytes(FIXTURE_BYTES[:100])
        append(self.layout.ledger, request_record("r2", interrupted))
        session = FixtureSession()

        code = self.fetch(session)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [rows[1]["url"], rows[2]["url"]])
        self.assertEqual(self.layout.submission(interrupted).read_bytes(), FIXTURE_BYTES)
        self.assertEqual(list(self.layout.bytes_dir.glob("*.part")), [])
        self.assertGreaterEqual(ledger_usage(self.layout.ledger).wire_bytes, 268_435_456)
        fetches = {row["accession_number"]: row for row in self.fetches()}
        self.assertEqual([row["outcome"] for row in fetches.values()], ["ok", "ok", "ok"])
        self.assertEqual(fetches[finished]["wire_bytes"], 777)
        self.assertEqual(fetches[finished]["sha256"], "a" * 64)
        self.assertEqual(fetches[finished]["attempts"], 1)
        self.assertEqual(
            fetches[finished]["fetched_at"],
            datetime.datetime(2026, 11, 16, 10, 0, 1, tzinfo=datetime.UTC),
        )
        self.assertEqual(fetches[interrupted]["attempts"], 2)
        self.assertEqual(fetches[interrupted]["sha256"], FIXTURE_SHA256)
        self.assertEqual(fetches[untouched]["attempts"], 1)

    def test_budget_stop_marks_the_rest(self):
        rows = self.write_sample(standard_sample())
        fill_ledger(self.layout.ledger, [100] * 1_499)
        # A .part file left by an earlier hard kill. The client stops before its attempt,
        # so only the walk's own cleanup can remove it.
        stale = self.part_of(rows[1]["accession_number"])
        stale.parent.mkdir()
        stale.write_bytes(b"partial")
        session = FixtureSession()

        code = self.fetch(session)

        self.assertEqual(code, 5)
        self.assertEqual(session.urls, [rows[0]["url"]])
        self.assertFalse(stale.exists())
        self.assertEqual(self.outcomes(), ["ok"] + ["budget"] * 5)
        self.assertEqual(ledger_usage(self.layout.ledger).requests, MAX_REQUESTS)

    def test_forbidden_returns_6(self):
        rows = self.write_sample(standard_sample()[:3])
        session = FixtureSession({rows[1]["url"]: FakeResponse(403, [b"denied"])})

        code = self.fetch(session)

        self.assertEqual(code, 6)
        self.assertEqual(session.urls, [rows[0]["url"], rows[1]["url"]])
        fetches = self.fetches()
        self.assertEqual([row["outcome"] for row in fetches], ["ok", "forbidden", "not_attempted"])
        forbidden = fetches[1]
        self.assertEqual(forbidden["status"], 403)
        self.assertEqual(forbidden["reason"], "HTTP 403")
        self.assertEqual(forbidden["attempts"], 1)
        self.assertIsNone(forbidden["path"])
        self.assertIsNone(forbidden["sha256"])


class FetchExitTests(CommandTestCase):
    def test_rerun_sends_no_request_for_filings_on_disk(self):
        self.write_sample(standard_sample())
        self.fetch(FixtureSession(), per_form=1)
        session = FixtureSession()

        code = self.fetch(session, per_form=1)

        self.assertEqual(code, 0)
        self.assertEqual(session.urls, [])
        self.assertEqual(len(self.records("request")), 2)

    def test_held_lock_refuses_and_writes_nothing(self):
        self.write_sample(standard_sample())
        session = FixtureSession()

        with exclusive_lock(self.layout.lock), self.assertRaises(RuntimeError):
            self.fetch(session)

        self.assertEqual(session.urls, [])
        self.assertFalse(self.layout.table("fetches").exists())
        self.assertFalse(self.layout.ledger.exists())

    def test_interrupt_still_writes_fetches(self):
        rows = self.write_sample(standard_sample()[:3])
        session = FixtureSession({rows[1]["url"]: KeyboardInterrupt()})

        with self.assertRaises(KeyboardInterrupt):
            self.fetch(session)

        self.assertEqual(self.outcomes(), ["ok", "failed", "not_attempted"])
        self.assertEqual(list(self.layout.bytes_dir.glob("*.part")), [])


class BuildFetchesTests(CommandTestCase):
    def test_matches_keys_exactly_and_reads_retry_as_failed(self):
        rows = self.write_sample(standard_sample()[:3])
        retried, lost, untouched = (row["accession_number"] for row in rows)
        for record in [
            # Killed during the backoff after a 503.
            request_record("a1", retried),
            response_record("a1", retried, status=503, outcome="retry", reason="HTTP 503"),
            # Another kind of fetch under a longer key: it is not this filing's record.
            request_record("i1", f"{retried}/instance"),
            response_record("i1", f"{retried}/instance", wire_bytes=50, sha256="b" * 64),
            # Killed between the ok record and the rename: no bytes on disk.
            request_record("l1", lost),
            response_record("l1", lost, wire_bytes=60, body_bytes=60, sha256="c" * 64),
        ]:
            append(self.layout.ledger, record)

        fetches = build_fetches(self.layout)

        self.assertEqual([row["accession_number"] for row in fetches], [retried, lost, untouched])
        self.assertEqual(
            fetches[0],
            {
                "accession_number": retried,
                "form_type": "10-K",
                "outcome": "failed",
                "reason": "HTTP 503",
                "status": 503,
                "attempts": 1,
                "wire_bytes": 0,
                "body_bytes": None,
                "sha256": None,
                "fetched_at": None,
                "path": None,
            },
        )
        self.assertEqual(fetches[1]["outcome"], "failed")
        self.assertIn("missing", fetches[1]["reason"])
        self.assertIsNone(fetches[1]["sha256"])
        self.assertIsNone(fetches[1]["path"])
        self.assertEqual(fetches[2]["outcome"], "not_attempted")
        self.assertEqual(fetches[2]["attempts"], 0)

    def test_fetch_rows_follow_the_given_sample(self):
        rows = self.write_sample(standard_sample()[:3])
        retried, on_disk, untouched = (row["accession_number"] for row in rows)
        for record in [
            request_record("a1", retried),
            response_record("a1", retried, status=503, outcome="retry", reason="HTTP 503"),
            request_record("d1", on_disk),
            response_record("d1", on_disk, wire_bytes=70, body_bytes=70, sha256="d" * 64),
        ]:
            append(self.layout.ledger, record)
        self.layout.bytes_dir.mkdir()
        self.layout.submission(on_disk).write_bytes(FIXTURE_BYTES)
        records = read_ledger(self.layout.ledger)
        expected = build_fetches(self.layout)
        self.assertEqual([row["outcome"] for row in expected], ["failed", "ok", "not_attempted"])
        self.assertEqual(
            [row["accession_number"] for row in expected], [retried, on_disk, untouched]
        )

        with self.subTest("in the order of the table, which is reverse draw order"):
            self.assertEqual(fetch_rows(self.layout, list(reversed(rows)), records), expected)
        with self.subTest("in draw order"):
            self.assertEqual(fetch_rows(self.layout, rows, records), expected)
        with self.subTest("one row"):
            self.assertEqual(fetch_rows(self.layout, [rows[1]], records), [expected[1]])
        with self.subTest("the given records, not the ledger"):
            (row,) = fetch_rows(self.layout, [rows[0]], [])
            self.assertEqual((row["outcome"], row["attempts"]), ("not_attempted", 0))

    def test_file_on_disk_without_ok_record_is_ok(self):
        rows = self.write_sample(standard_sample()[:1])
        accession = rows[0]["accession_number"]
        self.layout.bytes_dir.mkdir()
        self.layout.submission(accession).write_bytes(FIXTURE_BYTES)

        (row,) = build_fetches(self.layout)

        self.assertEqual(row["outcome"], "ok")
        self.assertEqual(row["path"], str(self.layout.submission(accession)))
        self.assertIsNone(row["sha256"])
        self.assertIsNone(row["fetched_at"])
        self.assertEqual(row["attempts"], 0)

    def test_budget_rule_matches_the_client(self):
        self.assertEqual(ledger.BUDGET_MARGIN, client.BUDGET_MARGIN)
        room = MAX_WIRE_BYTES - ledger.BUDGET_MARGIN
        self.assertFalse(budget_spent(Usage(MAX_REQUESTS - 1, room)))
        self.assertTrue(budget_spent(Usage(MAX_REQUESTS, 0)))
        self.assertTrue(budget_spent(Usage(0, room + 1)))
        self.assertFalse(budget_spent(Usage(19, 0), STAGE2_LIMITS))
        self.assertTrue(budget_spent(Usage(20, 0), STAGE2_LIMITS))
        self.assertTrue(
            budget_spent(Usage(0, 50_000_000 - ledger.BUDGET_MARGIN + 1), STAGE2_LIMITS)
        )


class EnvelopeTests(CommandTestCase):
    def test_envelopes_one_row_per_sampled_filing(self):
        rows = self.write_sample(standard_sample()[:3])
        parsed, corrupt, missing = (row["accession_number"] for row in rows)
        corrupt_bytes = b"not a submission\n"
        self.fetch(
            FixtureSession(
                {
                    rows[1]["url"]: FakeResponse(200, [corrupt_bytes]),
                    rows[2]["url"]: FakeResponse(404, [b"missing"]),
                }
            )
        )
        fetches = {row["accession_number"]: row for row in self.fetches()}

        code = run_envelopes(self.layout)

        self.assertEqual(code, 0)
        table = read_table(self.layout, "filings")
        self.assertEqual(table.schema, SCHEMAS["filings"])
        filings = table.to_pylist()
        self.assertEqual([row["accession_number"] for row in filings], [parsed, corrupt, missing])
        self.assertEqual(
            filings[0],
            {
                "accession_number": parsed,
                "form_type": "10-K",
                "outcome": "ok",
                "reason": None,
                "fetched_at": fetches[parsed]["fetched_at"],
                "sha256": FIXTURE_SHA256,
                "submission_type": "13F-HR",
                "acceptance_datetime": "20260814160523",
                "filed_as_of_date": "20260814",
                "date_as_of_change": "20260814",
                "private_to_public": False,
                "period_of_report": "20260630",
                "public_document_count": "2",
                "document_count": 2,
                "parse_error": None,
                "source_url": rows[0]["url"],
                "accepted_at": utc(2026, 8, 14, 20, 5, 23),
                "public_at": utc(2026, 8, 14, 20, 5, 23),
                "public_rule": "acceptance",
                "last_modified_at": None,
            },
        )
        self.assertIsNotNone(filings[0]["fetched_at"])
        self.assertEqual(
            filings[1],
            {
                "accession_number": corrupt,
                "form_type": "10-K",
                "outcome": "ok",
                "reason": None,
                "fetched_at": fetches[corrupt]["fetched_at"],
                "sha256": hashlib.sha256(corrupt_bytes).hexdigest(),
                "submission_type": None,
                "acceptance_datetime": None,
                "filed_as_of_date": None,
                "date_as_of_change": None,
                "private_to_public": None,
                "period_of_report": None,
                "public_document_count": None,
                "document_count": None,
                "parse_error": "no <SEC-HEADER> ... </SEC-HEADER> block",
                "source_url": rows[1]["url"],
                "accepted_at": None,
                "public_at": None,
                "public_rule": None,
                "last_modified_at": None,
            },
        )
        self.assertEqual(filings[2]["outcome"], "not_found")
        self.assertEqual(filings[2]["reason"], "not_found")
        self.assertIsNone(filings[2]["submission_type"])
        self.assertIsNone(filings[2]["private_to_public"])
        self.assertIsNone(filings[2]["parse_error"])
        self.assertEqual(filings[2]["source_url"], rows[2]["url"])
        for column in ("accepted_at", "public_at", "public_rule", "last_modified_at"):
            self.assertIsNone(filings[2][column])
        provenance = record_provenance(filings[0])

        parties = read_table(self.layout, "parties")
        self.assertEqual(parties.schema, SCHEMAS["parties"])
        self.assertEqual(
            parties.to_pylist(),
            [
                {
                    "accession_number": parsed,
                    "role": "FILER",
                    "name": "KINGDON CAPITAL MANAGEMENT, L.L.C.",
                    "cik": "0001000097",
                    **provenance,
                }
            ],
        )
        documents = read_table(self.layout, "documents")
        self.assertEqual(documents.schema, SCHEMAS["documents"])
        expected = parse_submission(FIXTURE_BYTES).documents
        self.assertEqual(
            documents.to_pylist(),
            [
                {
                    "accession_number": parsed,
                    "sequence": document.sequence,
                    "type": document.type,
                    "filename": document.filename,
                    "description": document.description,
                    "text_offset": document.text_offset,
                    "text_length": document.text_length,
                    **provenance,
                }
                for document in expected
            ],
        )
        self.assertEqual(
            [row["type"] for row in documents.to_pylist()], ["13F-HR", "INFORMATION TABLE"]
        )

    def test_envelopes_builds_fetches_when_the_table_is_missing(self):
        self.write_sample(standard_sample()[:2])
        self.fetch(FixtureSession())
        self.layout.table("fetches").unlink()

        run_envelopes(self.layout)

        filings = read_table(self.layout, "filings").to_pylist()
        self.assertEqual([row["outcome"] for row in filings], ["ok", "ok"])
        self.assertEqual([row["sha256"] for row in filings], [FIXTURE_SHA256] * 2)
        self.assertEqual([row["submission_type"] for row in filings], ["13F-HR"] * 2)


    def test_filing_times_come_from_the_header_and_the_ledger(self):
        rows = self.write_sample(standard_sample()[:1])
        accession = rows[0]["accession_number"]
        reply = FakeResponse(
            200, [FIXTURE_BYTES], {"Last-Modified": "Fri, 14 Aug 2026 20:06:00 GMT"}
        )
        self.fetch(FixtureSession({rows[0]["url"]: reply}))
        fetched_at = self.fetches()[0]["fetched_at"]

        run_envelopes(self.layout)

        (filing,) = read_table(self.layout, "filings").to_pylist()
        self.assertEqual(filing["last_modified_at"], utc(2026, 8, 14, 20, 6))
        self.assertEqual(filing["fetched_at"], fetched_at)
        times = {
            "accepted_at": utc(2026, 8, 14, 20, 5, 23),
            "public_at": utc(2026, 8, 14, 20, 5, 23),
            "public_rule": "acceptance",
            "last_modified_at": utc(2026, 8, 14, 20, 6),
            "fetched_at": fetched_at,
        }
        for name in ("parties", "documents"):
            table = read_table(self.layout, name)
            self.assertEqual(table.schema, SCHEMAS[name])
            children = table.to_pylist()
            self.assertTrue(children)
            for child in children:
                self.assertEqual(child["accession_number"], accession)
                self.assertEqual(child["source_url"], rows[0]["url"])
                self.assertEqual(child["source_sha256"], FIXTURE_SHA256)
                self.assertEqual({key: child[key] for key in times}, times)

    def test_envelopes_writes_filing_times_on_sampled_index_rows(self):
        rows = self.write_sample(standard_sample()[:2])
        sampled, other_sample = (row["accession_number"] for row in rows)
        unsampled = accession_of(99)
        receipt = {
            "source_url": "https://example.test/master.zip",
            "source_sha256": "ab" * 32,
            "index_built_at": utc(2026, 10, 31, 7, 49, 35),
            "index_data_through": "September 30, 2026",
            "index_received_at": utc(2026, 10, 31, 17, 54, 33),
            "index_last_modified_at": utc(2026, 10, 31, 7, 50, 9),
        }
        index_rows = [
            {**index_row(1), "accession_number": unsampled, "line_number": 1},
            {**index_row(2), "accession_number": sampled, "line_number": 2, "cik": 1000},
            {**index_row(3), "accession_number": other_sample, "line_number": 3},
            {**index_row(4), "accession_number": sampled, "line_number": 4, "cik": 2000},
            {**index_row(5), "accession_number": unsampled, "line_number": 5, "cik": 3000},
        ]
        write_table(self.layout, "index", [{**row, **receipt} for row in index_rows])
        before = read_table(self.layout, "index")
        reply = FakeResponse(
            200, [FIXTURE_BYTES], {"Last-Modified": "Fri, 14 Aug 2026 20:06:00 GMT"}
        )
        self.fetch(FixtureSession({rows[0]["url"]: reply}))
        run_envelopes(self.layout)

        after = read_table(self.layout, "index")
        filings = {
            row["accession_number"]: row for row in read_table(self.layout, "filings").to_pylist()
        }
        # The sampled filings differ, so a swap of one accession's times for another's shows.
        self.assertEqual(filings[sampled]["last_modified_at"], utc(2026, 8, 14, 20, 6))
        self.assertIsNone(filings[other_sample]["last_modified_at"])
        self.assertNotEqual(filings[sampled]["fetched_at"], filings[other_sample]["fetched_at"])
        self.assertEqual(after.schema, SCHEMAS["index"])
        self.assertEqual(after.num_rows, 5)
        after_rows = after.to_pylist()
        no_times = dict.fromkeys(FILING_TIME_COLUMNS)
        for row, was in zip(after_rows, before.to_pylist(), strict=True):
            times = {name: row[name] for name in FILING_TIME_COLUMNS}
            with self.subTest(line_number=row["line_number"]):
                if row["accession_number"] == unsampled:
                    self.assertEqual(times, no_times)
                else:
                    self.assertEqual(times, filing_times(filings[row["accession_number"]]))
                    self.assertIsNotNone(times["fetched_at"])
                # Every other column, and the order of the rows, stay as written before.
                self.assertEqual(
                    {key: value for key, value in row.items() if key not in FILING_TIME_COLUMNS},
                    {key: value for key, value in was.items() if key not in FILING_TIME_COLUMNS},
                )
        self.assertEqual([row["line_number"] for row in after_rows], [1, 2, 3, 4, 5])
        self.assertEqual(
            [row["cik"] for row in after_rows if row["accession_number"] == sampled], [1000, 2000]
        )
        self.assertEqual(
            after_rows[1]["accepted_at"], utc(2026, 8, 14, 20, 5, 23)
        )
        self.assertEqual(after_rows[1]["public_rule"], "acceptance")
        self.assertEqual(after_rows[1]["last_modified_at"], utc(2026, 8, 14, 20, 6))
        self.assertEqual(after_rows[3]["last_modified_at"], utc(2026, 8, 14, 20, 6))
        self.assertIsNone(after_rows[2]["last_modified_at"])
        self.assertEqual(after_rows[2]["fetched_at"], filings[other_sample]["fetched_at"])

    def test_envelopes_without_an_index_table_writes_none(self):
        self.write_sample(standard_sample()[:1])
        self.fetch(FixtureSession())

        run_envelopes(self.layout)

        self.assertFalse(self.layout.table("index").exists())

    def test_last_modified_is_kept_for_an_ok_filing_that_does_not_parse(self):
        rows = self.write_sample(standard_sample()[:1])
        reply = FakeResponse(
            200, [b"not a submission\n"], {"Last-Modified": "Fri, 14 Aug 2026 20:06:00 GMT"}
        )
        self.fetch(FixtureSession({rows[0]["url"]: reply}))

        run_envelopes(self.layout)

        (filing,) = read_table(self.layout, "filings").to_pylist()
        self.assertEqual(filing["outcome"], "ok")
        self.assertIsNotNone(filing["parse_error"])
        self.assertEqual(filing["last_modified_at"], utc(2026, 8, 14, 20, 6))
        for column in ("accepted_at", "public_at", "public_rule"):
            self.assertIsNone(filing[column])

    def test_public_rule_follows_the_header(self):
        rows = self.write_sample(standard_sample()[:3])
        # The change date (20260820) is later than the filed date (20260814): only the filed
        # date counts, so the filing is public at its acceptance.
        later_change = xbrl_submission("1", ["a"], date_as_of_change="20260820")
        private = xbrl_submission("1", ["a"], date_as_of_change="20260820", private_to_public=True)
        self.fetch(
            FixtureSession(
                {
                    rows[0]["url"]: FakeResponse(200, [later_change]),
                    rows[1]["url"]: FakeResponse(200, [private]),
                    rows[2]["url"]: FakeResponse(200, [NO_PARTY]),
                }
            )
        )

        run_envelopes(self.layout)

        filings = read_table(self.layout, "filings").to_pylist()
        times = [(row["accepted_at"], row["public_at"], row["public_rule"]) for row in filings]
        self.assertEqual(
            times,
            [
                (utc(2026, 8, 14, 20, 5, 23), utc(2026, 8, 14, 20, 5, 23), "acceptance"),
                (utc(2026, 8, 14, 20, 5, 23), None, "private_to_public"),
                (None, None, "no_acceptance"),
            ],
        )
        self.assertEqual([row["private_to_public"] for row in filings], [False, True, False])

    def test_the_stage_1_ledger_alone_gives_last_modified(self):
        rows = self.write_sample(standard_sample()[:2])
        first, second = (row["accession_number"] for row in rows)
        self.fetch(FixtureSession())
        for accession, header in ((first, "Fri, 14 Aug 2026 20:06:00 GMT"), (second, "not a date")):
            append(
                self.layout.ledger,
                response_record(f"x-{accession}", accession, last_modified=header),
            )

        run_envelopes(self.layout)

        filings = read_table(self.layout, "filings").to_pylist()
        self.assertEqual(filings[0]["last_modified_at"], utc(2026, 8, 14, 20, 6))
        self.assertIsNone(filings[1]["last_modified_at"])

    def test_read_provenance_needs_filings(self):
        with self.assertRaises(FileNotFoundError) as caught:
            read_provenance(self.layout)

        self.assertIn("envelopes", str(caught.exception))
        self.assertIn(str(self.layout.table("filings")), str(caught.exception))

    def test_read_provenance_gives_each_filing_by_accession(self):
        rows = self.write_sample(standard_sample()[:2])
        self.fetch(FixtureSession({rows[1]["url"]: FakeResponse(404, [b"missing"])}))
        run_envelopes(self.layout)
        filings = {
            row["accession_number"]: row for row in read_table(self.layout, "filings").to_pylist()
        }

        provenance = read_provenance(self.layout)

        self.assertEqual(set(provenance), set(filings))
        for accession, filing in filings.items():
            self.assertEqual(provenance[accession], record_provenance(filing))
        parsed = provenance[rows[0]["accession_number"]]
        self.assertEqual(parsed["source_url"], rows[0]["url"])
        self.assertEqual(parsed["source_sha256"], FIXTURE_SHA256)
        self.assertEqual(parsed["public_at"], utc(2026, 8, 14, 20, 5, 23))
        missing = provenance[rows[1]["accession_number"]]
        self.assertEqual(missing["source_url"], rows[1]["url"])
        self.assertIsNone(missing["public_at"])


class OkResponsesTests(CommandTestCase):
    def test_gives_the_last_ok_response_of_each_key(self):
        for record in [
            request_record("a1", "k1"),
            response_record("a1", "k1", last_modified="first"),
            request_record("a2", "k1", 2),
            response_record("a2", "k1", last_modified="second"),
            request_record("a3", "k1", 3),
            response_record("a3", "k1", status=503, outcome="retry", reason="HTTP 503"),
            request_record("b1", "k2"),
            response_record("b1", "k2", status=404, outcome="not_found"),
            request_record("c1", "k1/instance"),
            response_record("c1", "k1/instance", last_modified="other"),
        ]:
            append(self.layout.ledger, record)

        found = ok_responses(self.layout.ledger)

        self.assertEqual(set(found), {"k1", "k1/instance"})
        self.assertEqual(found["k1"]["last_modified"], "second")
        self.assertEqual(found["k1/instance"]["last_modified"], "other")
        self.assertEqual(last_ok(read_ledger(self.layout.ledger)), found)

    def test_a_missing_ledger_has_none(self):
        self.assertEqual(ok_responses(self.layout.ledger), {})


class ParseLedgerTests(CommandTestCase):
    def test_parse_ledger_matches_read_ledger(self):
        self.write_sample(standard_sample()[:3])
        self.assertEqual(self.fetch(FixtureSession()), 0)

        data = self.layout.ledger.read_bytes()

        records = parse_ledger(data)

        self.assertEqual(records, read_ledger(self.layout.ledger))
        self.assertEqual(len(records), len(data.splitlines()))
        self.assertEqual({record["event"] for record in records}, {"request", "response"})
        with self.subTest("blank lines are skipped"):
            self.assertEqual(parse_ledger(b'{"a": 1}\n\n   \n{"b": 2}\n'), [{"a": 1}, {"b": 2}])
        with self.subTest("a line that is not JSON raises"):
            with self.assertRaises(json.JSONDecodeError):
                parse_ledger(b'{"a": 1}\nnot json\n')


class OfflineTests(unittest.TestCase):
    def test_offline_modules_never_import_requests(self):
        names = {module.name for module in pkgutil.iter_modules(sec_filing_data.__path__)}
        self.assertLessEqual({"cli", "client", "fetch", "ledger", "manifest", "provenance", "rebuild", "refetches", "report", "submissions", "times", "verify", "version"}, names)
        code = (
            "import importlib, pkgutil, sys\n"
            "import sec_filing_data\n"
            "for module in pkgutil.iter_modules(sec_filing_data.__path__):\n"
            "    if module.name not in ('client', 'fetch'):\n"
            "        importlib.import_module('sec_filing_data.' + module.name)\n"
            "print('requests' in sys.modules)\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )

        self.assertEqual(result.stdout.strip(), "False")


def section(report: str, title: str) -> list[str]:
    """The lines of one `## title` section, up to the next section."""
    lines = report.split("\n")
    start = lines.index(f"## {title}") + 1
    end = next(
        (number for number in range(start, len(lines)) if lines[number].startswith("## ")),
        len(lines),
    )
    return [line for line in lines[start:end] if line]


def disk_use(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


class ReportTests(CommandTestCase):
    def build_root(self) -> list[dict]:
        """Four sampled filings: gzip fixture, a submission with no party, fixture, and a 404."""
        rows = self.write_sample(
            [
                sample_row(1, "quota", "10-K"),
                sample_row(2, "quota", "4"),
                sample_row(3, "repeated", "4;SC 13D"),
                sample_row(4, "uniform", "8-K"),
            ]
        )
        write_table(self.layout, "index", [index_row(number) for number in range(1, 7)])
        self.gzip_bytes = gzip.compress(FIXTURE_BYTES, mtime=0)
        self.fetch(
            FixtureSession(
                {
                    rows[0]["url"]: FakeResponse(
                        200,
                        [self.gzip_bytes],
                        {
                            "Content-Encoding": "gzip",
                            "ETag": '"e1"',
                            "Last-Modified": "Fri, 14 Aug 2026 20:05:23 GMT",
                        },
                    ),
                    rows[1]["url"]: FakeResponse(200, [NO_PARTY]),
                    rows[3]["url"]: FakeResponse(404, [b"missing"]),
                }
            )
        )
        run_envelopes(self.layout)
        steps = [("index", 0.5), ("fetch", 2.5), ("envelopes", 0.25), ("fetch", 1.0)]
        self.layout.runs.write_text(
            "".join(
                json.dumps({"step": step, "seconds": seconds}) + "\n" for step, seconds in steps
            )
        )
        return rows

    def test_report_lists_cost(self):
        rows = self.build_root()
        expected_disk_use = disk_use(self.layout.root)

        report = run_report(self.layout)

        self.assertIn("- requests: 4", report.split("\n"))
        wire = len(self.gzip_bytes) + len(NO_PARTY) + len(FIXTURE_BYTES)
        self.assertIn(f"- wire bytes: {wire}", report.split("\n"))
        decoded = 2 * len(FIXTURE_BYTES) + len(NO_PARTY)
        self.assertIn(f"- decoded bytes: {decoded}", report.split("\n"))
        self.assertEqual(
            section(report, "Wall time"),
            ["- index: 0.500 s", "- fetch: 3.500 s", "- envelopes: 0.250 s", "- total: 4.250 s"],
        )
        self.assertEqual(section(report, "Disk use"), [f"- disk use: {expected_disk_use} bytes"])
        no_party = section(report, "Header checks")
        self.assertIn("- filings with no party, among 3 parsed filings: 1", no_party)
        self.assertIn(f"  - {rows[1]['accession_number']}", no_party)

    def test_report_lists_platform_checks(self):
        self.build_root()

        report = run_report(self.layout)

        titles = [line for line in report.split("\n") if line.startswith("## ")]
        self.assertEqual(titles[-5], "## Platform checks")
        checks = section(report, "Platform checks")
        labels = [line[2:].split(" ")[0] for line in checks if line.startswith("- ")]
        self.assertEqual(labels, ["V3", "V5", "V6", "V7", "V9", "V10"])
        (v6,) = [line for line in checks if line.startswith("- V6 ")]
        self.assertTrue(v6.endswith(": 0"), v6)


class ReportPlatformTests(CommandTestCase):
    def test_report_counts_platform_cases(self):
        rows = self.write_sample(
            [
                sample_row(1, "quota", "10-Q"),
                sample_row(2, "quota", "10-K"),
                sample_row(3, "repeated", "4;SC 13D"),
                sample_row(4, "uniform", "8-K"),
                sample_row(5, "uniform", "8-K"),
            ]
        )
        accessions = [row["accession_number"] for row in rows]
        minus = xbrl_submission(
            "2", [None, IDEA, None], date_as_of_change="20260815", private_to_public=True
        )
        equal = xbrl_submission("3", [None, IDEA, None])
        neither = xbrl_submission("7", [IDEA, IDEA, None])
        no_acceptance = xbrl_submission("1", [None], acceptance=False)
        self.fetch(
            FixtureSession(
                {
                    rows[0]["url"]: FakeResponse(200, [minus]),
                    rows[1]["url"]: FakeResponse(200, [equal]),
                    rows[3]["url"]: FakeResponse(
                        200,
                        [gzip.compress(neither, mtime=0)],
                        {"Content-Encoding": "gzip", "ETag": '"e4"'},
                    ),
                    rows[4]["url"]: FakeResponse(200, [no_acceptance]),
                }
            )
        )
        # An ok record under a key that is not a sampled accession is not a V3 response.
        append(self.layout.ledger, request_record("i1", f"{accessions[0]}/instance"))
        append(
            self.layout.ledger,
            response_record("i1", f"{accessions[0]}/instance", content_encoding="gzip"),
        )
        run_envelopes(self.layout)

        checks = section(run_report(self.layout), "Platform checks")

        self.assertEqual(
            checks,
            [
                "- V3 ok responses: 5",
                "  - Content-Encoding gzip: 1",
                "  - Content-Encoding none: 4",
                "  - with ETag: 1",
                "  - with Last-Modified: 0",
                "- V5 repeated filings: 1",
                (
                    f"  - {accessions[2]}: form_type 4;SC 13D, submission_type 13F-HR,"
                    " document_count 2"
                ),
                "- V6 filings whose date_as_of_change is later than filed_as_of_date: 1",
                f"  - {accessions[0]}",
                "- V7 filings with private_to_public: 1",
                f"  - {accessions[0]}",
                "- V9 filings with a null acceptance_datetime: 1",
                f"  - {accessions[4]}",
                f"- V10 filings with documents described {IDEA}: 3",
                "  - public_document_count equals document_count: 1",
                "  - public_document_count equals document_count minus those documents: 1",
                "  - neither: 1",
            ],
        )

    def test_report_runs_before_envelopes(self):
        self.write_sample(standard_sample())

        report = run_report(self.layout)

        self.assertEqual(section(report, "Index"), ["- no `index` table yet"])
        self.assertIn("- no `fetches` table yet", section(report, "Fetch outcomes"))
        self.assertIn("- requests: 0", section(report, "Cost"))
        checks = section(report, "Platform checks")
        self.assertIn("- V3 ok responses: 0", checks)
        self.assertIn("- V6: no `filings` table yet", checks)
        self.assertIn("- V10: no `filings` table yet", checks)
        self.assertEqual(section(report, "Wall time"), ["- no steps recorded yet"])


class CliTests(CommandTestCase):
    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main([*argv, "--out", str(self.layout.root)])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_fetch_needs_a_user_agent(self):
        self.write_sample(standard_sample())
        before = sorted(self.layout.root.rglob("*"))
        for environment in ({}, {"SEC_USER_AGENT": ""}):
            with mock.patch.dict(os.environ, environment):
                if not environment:
                    os.environ.pop("SEC_USER_AGENT", None)
                code, stdout, stderr = self.run_cli("fetch")

            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertIn("SEC_USER_AGENT", stderr)
            self.assertEqual(sorted(self.layout.root.rglob("*")), before)

    def test_commands_print_counts_and_record_steps(self):
        self.write_sample(standard_sample())
        real_run_fetch = fetch_module.run_fetch
        calls = []

        def offline_run_fetch(layout, *, user_agent, per_form=None):
            calls.append((user_agent, per_form))
            return real_run_fetch(
                layout,
                user_agent=user_agent,
                per_form=per_form,
                session=FixtureSession(),
                monotonic=self.clock.monotonic,
                sleep=self.clock.sleep,
            )

        with (
            mock.patch.object(fetch_module, "run_fetch", offline_run_fetch),
            mock.patch.dict(os.environ, {"SEC_USER_AGENT": USER_AGENT}),
        ):
            fetched = self.run_cli("fetch", "--per-form", "1")
        enveloped = self.run_cli("envelopes")
        reported = self.run_cli("report")

        self.assertEqual(calls, [(USER_AGENT, 1)])
        self.assertEqual(fetched, (0, "ok: 2\nnot_attempted: 4\n", ""))
        self.assertEqual(enveloped, (0, "filings: 6\nparties: 2\ndocuments: 4\n", ""))
        code, stdout, stderr = reported
        self.assertEqual((code, stderr), (0, ""))
        self.assertTrue(stdout.startswith("# sec-filing-data report\n"), stdout[:80])
        self.assertIn("## Platform checks", stdout)
        steps = [
            json.loads(line)["step"]
            for line in self.layout.runs.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(steps, ["fetch", "envelopes", "report"])


if __name__ == "__main__":
    unittest.main()
