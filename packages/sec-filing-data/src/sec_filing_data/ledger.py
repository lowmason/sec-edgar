"""The request ledger `fetch-log.jsonl`: it carries the SEC budget across every run.

Each HTTP attempt writes a request record before it is sent and a response record after
it ends. The two records share an `id`. This module does not import `requests`.
"""

import io
import json
import os
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from operator import itemgetter
from pathlib import Path

from sec_filing_data.layout import Layout
from sec_filing_data.tables import read_table, write_table

MAX_REQUESTS = 1_500
MAX_WIRE_BYTES = 5_000_000_000
MAX_RESPONSE_BYTES = 268_435_456
# The client's BUDGET_MARGIN. It is repeated here because this module cannot import the client.
BUDGET_MARGIN = 1_048_576

FETCH_OUTCOMES = ("ok", "not_found", "too_large", "forbidden", "failed", "budget", "not_attempted")


@dataclass(frozen=True)
class Usage:
    requests: int
    wire_bytes: int


@dataclass(frozen=True)
class Limits:
    """The request and wire-byte limits that a ledger is counted against."""

    requests: int
    wire_bytes: int


STAGE1_LIMITS = Limits(MAX_REQUESTS, MAX_WIRE_BYTES)
STAGE2_LIMITS = Limits(20, 50_000_000)
STAGE4_LIMITS = Limits(30, 50_000_000)


def append(path: Path, record: dict) -> None:
    """Append one JSON line, and flush and fsync it before returning."""
    line = json.dumps(record) + "\n"
    with path.open("a", encoding="utf-8") as ledger:
        ledger.write(line)
        ledger.flush()
        os.fsync(ledger.fileno())


def read_ledger(path: Path) -> list[dict]:
    """All records in file order. A missing ledger has none.

    A line that is not JSON raises, so a damaged ledger stops the client before it sends.
    """
    if not path.exists():
        return []
    return parse_ledger(path.read_bytes())


def parse_ledger(data: bytes) -> list[dict]:
    """The records of `read_ledger`, from the bytes of the ledger.

    The lines split as a text file reads them, so that a file and its bytes give one result.
    """
    with io.TextIOWrapper(io.BytesIO(data), encoding="utf-8") as ledger:
        return [json.loads(line) for line in ledger if line.strip()]


def ledger_usage(path: Path) -> Usage:
    """Count request records and sum response wire bytes.

    A request with no response (a run that was killed) counts as `MAX_RESPONSE_BYTES`.
    """
    return _usage(read_ledger(path))


def _usage(records: list[dict]) -> Usage:
    sent = [record for record in records if record["event"] == "request"]
    responses = [record for record in records if record["event"] == "response"]
    answered = {record["id"] for record in responses}
    unanswered = sum(1 for record in sent if record["id"] not in answered)
    wire_bytes = sum(record["wire_bytes"] for record in responses)
    return Usage(len(sent), wire_bytes + unanswered * MAX_RESPONSE_BYTES)


def budget_spent(usage: Usage, limits: Limits = STAGE1_LIMITS) -> bool:
    """The client's rule before each attempt: no request is left, or less than the margin."""
    return usage.requests >= limits.requests or limits.wire_bytes - usage.wire_bytes < BUDGET_MARGIN


def ok_responses(path: Path) -> dict[str, dict]:
    """The last `ok` response record of each key. A key with no `ok` response is absent."""
    return last_ok(read_ledger(path))


def last_ok(records: list[dict]) -> dict[str, dict]:
    """The last `ok` response record of each key, from `records`."""
    ok_by_key: dict[str, dict] = {}
    for record in records:
        if record["event"] == "response" and record["outcome"] == "ok":
            ok_by_key[record["key"]] = record
    return ok_by_key


def build_fetches(layout: Layout) -> list[dict]:
    """One `fetches` row per sampled filing, in draw order, from the ledger and the disk.

    See `fetch_rows`.
    """
    records = read_ledger(layout.ledger)
    return fetch_rows(layout, read_table(layout, "sample").to_pylist(), records)


def fetch_rows(layout: Layout, sample: list[dict], records: list[dict]) -> list[dict]:
    """One `fetches` row per row of `sample`, in draw order, from `records` and the disk.

    See `filing_fetch_rows`. The bytes sit at `layout.submission`, and the Stage 1 limits count.
    """
    return filing_fetch_rows(
        sorted(sample, key=itemgetter("draw")),
        records,
        path_of=layout.submission,
        limits=STAGE1_LIMITS,
    )


def filing_fetch_rows(
    filings: list[dict],
    records: list[dict],
    *,
    path_of: Callable[[str], Path],
    limits: Limits,
) -> list[dict]:
    """One `fetches` row per entry of `filings`, in the given order, from `records` and the disk.

    Each entry has `accession_number` and `form_type`. A filing is `ok` when its bytes are on
    disk at `path_of(accession_number)`. Else its last response record gives the outcome, with
    `retry` read as `failed`. Else it is `budget` when `records` spend `limits`, and
    `not_attempted` otherwise. Records match a filing by `key == accession_number`.
    """
    spent = budget_spent(_usage(records), limits)
    attempts: Counter[str] = Counter()
    last_response: dict[str, dict] = {}
    for record in records:
        if record["event"] == "request":
            attempts[record["key"]] += 1
        elif record["event"] == "response":
            last_response[record["key"]] = record
    ok_by_key = last_ok(records)
    rows = []
    for filing in filings:
        accession = filing["accession_number"]
        row = {
            "accession_number": accession,
            "form_type": filing["form_type"],
            "outcome": "budget" if spent else "not_attempted",
            "reason": None,
            "status": None,
            "attempts": attempts[accession],
            "wire_bytes": None,
            "body_bytes": None,
            "sha256": None,
            "fetched_at": None,
            "path": None,
        }
        path = path_of(accession)
        if path.exists():
            row.update(outcome="ok", path=str(path))
            if accession in ok_by_key:
                row.update(_ok_values(ok_by_key[accession]))
        elif accession in last_response:
            row.update(_answer_values(last_response[accession], path))
        rows.append(row)
    return rows


def run_fetches(layout: Layout) -> list[dict]:
    """Write the `fetches` table from the ledger and the bytes on disk. Give its rows.

    This is the offline form of the table that `fetch` writes. It sends no request.
    """
    rows = build_fetches(layout)
    write_table(layout, "fetches", rows)
    return rows


def _ok_values(record: dict) -> dict:
    return {
        "status": record["status"],
        "wire_bytes": record["wire_bytes"],
        "body_bytes": record["body_bytes"],
        "sha256": record["sha256"],
        "fetched_at": datetime.fromisoformat(record["at"]),
    }


def _answer_values(record: dict, path: Path) -> dict:
    """The outcome of a filing that is not on disk, from its last response record."""
    outcome, reason = record["outcome"], record["reason"]
    if outcome == "retry":
        outcome = "failed"
    elif outcome == "ok":
        # A kill between the ok record and the rename leaves no bytes on disk.
        outcome, reason = "failed", f"ok response, but {path} is missing"
    return {
        "outcome": outcome,
        "reason": reason,
        "status": record["status"],
        "wire_bytes": record["wire_bytes"],
        "body_bytes": record["body_bytes"],
    }
