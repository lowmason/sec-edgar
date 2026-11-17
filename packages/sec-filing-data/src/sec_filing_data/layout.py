"""Paths under one output root, and the step-time record."""

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    root: Path

    @property
    def tables(self) -> Path:
        return self.root / "tables"

    @property
    def bytes_dir(self) -> Path:
        return self.root / "bytes"

    @property
    def ledger(self) -> Path:
        return self.root / "fetch-log.jsonl"

    @property
    def lock(self) -> Path:
        return self.root / "fetch.lock"

    @property
    def runs(self) -> Path:
        return self.root / "runs.jsonl"

    def table(self, name: str) -> Path:
        return self.tables / f"{name}.parquet"

    def submission(self, accession: str) -> Path:
        return self.bytes_dir / f"{accession}.txt"

    def instance(self, accession: str) -> Path:
        return self.bytes_dir / f"{accession}_htm.xml"


@contextmanager
def record_step(layout: Layout, step: str) -> Iterator[None]:
    """Append the start time, end time and length of one step to `runs.jsonl`.

    The record is written when the step fails too, so a crashed run still shows its time.
    """
    started_at = datetime.now(UTC)
    started = time.monotonic()
    try:
        yield
    finally:
        record = {
            "step": step,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "seconds": round(time.monotonic() - started, 3),
        }
        layout.root.mkdir(parents=True, exist_ok=True)
        with layout.runs.open("a", encoding="utf-8") as runs:
            runs.write(json.dumps(record) + "\n")
