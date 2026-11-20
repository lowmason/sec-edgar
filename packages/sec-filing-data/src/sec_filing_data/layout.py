"""Paths under one output root, and the step-time record."""

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sec_filing_data import version


@dataclass(frozen=True)
class Layout:
    """The paths of one output root.

    With `tables_dir`, the tables are read and written there, and every other path stays
    under `root`. The rebuild uses it to write its tables to a temporary folder while it
    reads the bytes and the ledgers in place. With `stage4_tables_dir`, the Stage 4 tables
    are there in place of `stage4/tables`.
    """

    root: Path
    tables_dir: Path | None = None
    stage4_tables_dir: Path | None = None

    @property
    def tables(self) -> Path:
        return self.root / "tables" if self.tables_dir is None else self.tables_dir

    @property
    def tables_stage1(self) -> Path:
        """The copy of the tables that the Stage 1 findings rest on."""
        return self.root / "tables-stage1"

    @property
    def tables_stage2(self) -> Path:
        """The copy of the tables that the Stage 2 findings rest on."""
        return self.root / "tables-stage2"

    @property
    def manifests(self) -> Path:
        """The folder of the manifests, one file for each table set and code version."""
        return self.root / "manifests"

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

    @property
    def stage2(self) -> Path:
        return self.root / "stage2"

    @property
    def stage2_ledger(self) -> Path:
        return self.stage2 / "fetch-log.jsonl"

    @property
    def refetch_dir(self) -> Path:
        return self.stage2 / "refetch"

    @property
    def stage4(self) -> Path:
        return self.root / "stage4"

    @property
    def stage4_bytes(self) -> Path:
        """The complete submission files of the Stage 4 partners."""
        return self.stage4 / "bytes"

    @property
    def stage4_ledger(self) -> Path:
        return self.stage4 / "fetch-log.jsonl"

    @property
    def stage4_tables(self) -> Path:
        return self.stage4 / "tables" if self.stage4_tables_dir is None else self.stage4_tables_dir

    @property
    def stage4_view(self) -> Layout:
        """The same root, with the Stage 4 tables where the tables are.

        A function that reads or writes `tables` through a layout then reads or writes the
        Stage 4 tables. Every other path, including `runs`, `lock` and `manifests`, stays
        where it is.
        """
        return Layout(self.root, tables_dir=self.stage4_tables)

    def table(self, name: str) -> Path:
        return self.tables / f"{name}.parquet"

    def submission(self, accession: str) -> Path:
        return self.bytes_dir / f"{accession}.txt"

    def instance(self, accession: str) -> Path:
        return self.bytes_dir / f"{accession}_htm.xml"

    def refetched(self, accession: str) -> Path:
        return self.refetch_dir / f"{accession}.txt"

    def partner_submission(self, accession: str) -> Path:
        return self.stage4_bytes / f"{accession}.txt"


@contextmanager
def record_step(layout: Layout, step: str) -> Iterator[None]:
    """Append the start time, end time and length of one step to `runs.jsonl`.

    The record also names the code version (the commit, or null) and whether the pinned paths
    were clean (true, false or null). It is written when the step fails too, so a crashed run
    still shows its time.
    """
    started_at = datetime.now(UTC)
    started = time.monotonic()
    try:
        yield
    finally:
        checkout = version.current_checkout()
        record = {
            "step": step,
            "started_at": started_at.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "seconds": round(time.monotonic() - started, 3),
            "code_version": checkout.commit,
            "tree_clean": checkout.clean,
        }
        layout.root.mkdir(parents=True, exist_ok=True)
        with layout.runs.open("a", encoding="utf-8") as runs:
            runs.write(json.dumps(record) + "\n")
