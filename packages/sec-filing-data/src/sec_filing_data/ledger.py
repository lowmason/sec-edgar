"""The request ledger `fetch-log.jsonl`: it carries the SEC budget across every run.

Each HTTP attempt writes a request record before it is sent and a response record after
it ends. The two records share an `id`. This module does not import `requests`.
"""

import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from operator import itemgetter
from pathlib import Path

from sec_filing_data.layout import Layout
from sec_filing_data.tables import read_table

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
    with path.open(encoding="utf-8") as ledger:
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


def build_fetches(layout: Layout) -> list[dict]:
    """One `fetches` row per sampled filing, in draw order, from the ledger and the disk.

    A filing is `ok` when its bytes are on disk. Else its last response record gives the
    outcome, with `retry` read as `failed`. Else it is `budget` when the budget is spent,
    and `not_attempted` otherwise. Records match a filing by `key == accession_number`.
    """
    records = read_ledger(layout.ledger)
    spent = budget_spent(_usage(records))
    attempts: Counter[str] = Counter()
    last_response: dict[str, dict] = {}
    last_ok: dict[str, dict] = {}
    for record in records:
        if record["event"] == "request":
            attempts[record["key"]] += 1
        elif record["event"] == "response":
            last_response[record["key"]] = record
            if record["outcome"] == "ok":
                last_ok[record["key"]] = record
    sample = sorted(read_table(layout, "sample").to_pylist(), key=itemgetter("draw"))
    rows = []
    for sampled in sample:
        accession = sampled["accession_number"]
        row = {
            "accession_number": accession,
            "form_type": sampled["form_type"],
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
        path = layout.submission(accession)
        if path.exists():
            row.update(outcome="ok", path=str(path))
            if accession in last_ok:
                row.update(_ok_values(last_ok[accession]))
        elif accession in last_response:
            row.update(_answer_values(last_response[accession], path))
        rows.append(row)
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
