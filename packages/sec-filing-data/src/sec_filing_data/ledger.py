"""The request ledger `fetch-log.jsonl`: it carries the SEC budget across every run.

Each HTTP attempt writes a request record before it is sent and a response record after
it ends. The two records share an `id`. This module does not import `requests`.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path

MAX_REQUESTS = 1_500
MAX_WIRE_BYTES = 5_000_000_000
MAX_RESPONSE_BYTES = 268_435_456


@dataclass(frozen=True)
class Usage:
    requests: int
    wire_bytes: int


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
    records = read_ledger(path)
    sent = [record for record in records if record["event"] == "request"]
    responses = [record for record in records if record["event"] == "response"]
    answered = {record["id"] for record in responses}
    unanswered = sum(1 for record in sent if record["id"] not in answered)
    wire_bytes = sum(record["wire_bytes"] for record in responses)
    return Usage(len(sent), wire_bytes + unanswered * MAX_RESPONSE_BYTES)
