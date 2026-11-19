"""The rebuild of every table in a temporary folder, and the check of the Stage 1 columns."""

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
from sec_filing_data import cli, index, sample, version
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import FETCH_OUTCOMES, build_fetches
from sec_filing_data.rebuild import (
    REBUILT_TABLES,
    check_frozen,
    check_stage1,
    compare_table,
    run_rebuild,
)
from sec_filing_data.tables import read_table, write_table

from tests.test_client import FakeResponse
from tests.test_commands import CommandTestCase, FixtureSession
from tests.test_index import fingerprint
from tests.test_ownership import INFOTABLE, PAR, submission_13f
from tests.test_report import build_fixture_root

# The Stage 1 copy of the sampled 13F-HR: one with an information table, so that `ownership`
# has rows. Its refetch gets the plain 13F fixture, so its `refetches` row lists changes.
FETCHED_13F = submission_13f(INFOTABLE, PAR)

# The columns of each Stage 1 table, as the Stage 1 `SCHEMAS` had them. Stage 1 had no
# `refetches` table.
STAGE1_COLUMNS = {
    "index": (
        "line_number",
        "cik",
        "company_name",
        "form_type",
        "date_filed",
        "filename",
        "accession_number",
    ),
    "sample": (
        "draw",
        "stratum",
        "accession_number",
        "form_type",
        "cik",
        "company_name",
        "date_filed",
        "filename",
        "url",
    ),
    "fetches": (
        "accession_number",
        "form_type",
        "outcome",
        "reason",
        "status",
        "attempts",
        "wire_bytes",
        "body_bytes",
        "sha256",
        "fetched_at",
        "path",
    ),
    "filings": (
        "accession_number",
        "form_type",
        "outcome",
        "reason",
        "fetched_at",
        "sha256",
        "submission_type",
        "acceptance_datetime",
        "filed_as_of_date",
        "date_as_of_change",
        "private_to_public",
        "period_of_report",
        "public_document_count",
        "document_count",
        "parse_error",
    ),
    "parties": ("accession_number", "role", "name", "cik"),
    "documents": (
        "accession_number",
        "sequence",
        "type",
        "filename",
        "description",
        "text_offset",
        "text_length",
    ),
    "facts": (
        "accession_number",
        "source_document",
        "concept",
        "value",
        "unit",
        "period_start",
        "period_end",
        "period_instant",
        "decimals",
        "context_id",
        "dimensions",
        "is_nil",
    ),
    "facts_status": ("accession_number", "form_type", "source_document", "fact_count", "reason"),
    "ownership": (
        "accession_number",
        "form_type",
        "record_kind",
        "issuer_cik",
        "issuer_name",
        "issuer_cusip",
        "owner_cik",
        "owner_name",
        "owner_count",
        "security_title",
        "shares",
        "shares_kind",
        "put_call",
        "transaction_date",
        "transaction_code",
        "acquired_disposed",
        "price_per_share",
        "shares_after",
        "direct_indirect",
        "percent_of_class",
        "value_usd",
    ),
    "ownership_status": ("accession_number", "form_type", "record_count", "reason"),
}

ALL_EQUAL = [f"{name}: equal" for name in REBUILT_TABLES]


def file_digests(root: Path) -> dict[str, str]:
    """The SHA-256 of each file under `root`, by relative path, except `runs.jsonl`."""
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != root / "runs.jsonl"
    }


def path_stamps(root: Path) -> dict[str, tuple[int, int] | None]:
    """Every path under `root` except `runs.jsonl`: a file's inode and modification time, or
    None for a folder. A file written again with the same bytes still changes its stamp."""
    stamps = {}
    for path in sorted(root.rglob("*")):
        if path == root / "runs.jsonl":
            continue
        status = path.stat()
        stamps[str(path.relative_to(root))] = (
            (status.st_ino, status.st_mtime_ns) if path.is_file() else None
        )
    return stamps


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def run_cli(*argv: str) -> tuple[int, list[str]]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        code = cli.main(list(argv))
    return code, stdout.getvalue().splitlines()


class LayoutTests(unittest.TestCase):
    def test_tables_dir_moves_only_the_tables(self):
        root, elsewhere = Path("/root"), Path("/elsewhere/tables")
        moved, plain = Layout(root, tables_dir=elsewhere), Layout(root)

        self.assertEqual(plain.tables, root / "tables")
        self.assertEqual(moved.tables, elsewhere)
        self.assertEqual(moved.table("facts"), elsewhere / "facts.parquet")
        self.assertEqual(moved.tables_stage1, root / "tables-stage1")
        self.assertEqual(plain.tables_stage1, root / "tables-stage1")
        self.assertEqual(moved.tables_stage2, root / "tables-stage2")
        self.assertEqual(plain.tables_stage2, root / "tables-stage2")
        for name in (
            "bytes_dir",
            "ledger",
            "lock",
            "runs",
            "stage2",
            "stage2_ledger",
            "refetch_dir",
        ):
            self.assertEqual(getattr(moved, name), getattr(plain, name), name)
        self.assertEqual(moved.submission("a"), plain.submission("a"))
        self.assertEqual(moved.refetched("a"), plain.refetched("a"))


class CompareTableTests(unittest.TestCase):
    SCHEMA = pa.schema([pa.field("a", pa.int64()), pa.field("b", pa.string())])

    def table(self, *rows: tuple, schema: pa.Schema = SCHEMA) -> pa.Table:
        return pa.Table.from_pylist(
            [dict(zip(schema.names, row, strict=True)) for row in rows], schema=schema
        )

    def test_equal_tables(self):
        table = self.table((1, "x"), (2, "y"))
        rechunked = pa.concat_tables([table.slice(0, 1), table.slice(1)])

        self.assertEqual(compare_table(table, rechunked), "equal")

    def test_a_schema_difference_comes_first(self):
        narrow = pa.schema([pa.field("a", pa.int32()), pa.field("b", pa.string())])

        self.assertEqual(
            compare_table(self.table((1, "x")), self.table((1, "x"), (2, "y"), schema=narrow)),
            "schema: a: int64, b: string against a: int32, b: string",
        )

    def test_a_schema_difference_with_equal_values(self):
        narrow = pa.schema([pa.field("a", pa.int32()), pa.field("b", pa.string())])

        self.assertEqual(
            compare_table(self.table((1, "x")), self.table((1, "x"), schema=narrow)),
            "schema: a: int64, b: string against a: int32, b: string",
        )

    def test_a_row_count_difference(self):
        self.assertEqual(
            compare_table(self.table((1, "x"), (2, "y")), self.table((1, "x"))), "rows: 2 against 1"
        )

    def test_rows_compare_in_order(self):
        self.assertEqual(
            compare_table(self.table((1, "x"), (2, "y")), self.table((2, "y"), (1, "x"))),
            "row 0 column a: 1 against 2",
        )

    def test_the_first_changed_value_is_named(self):
        self.assertEqual(
            compare_table(
                self.table((1, "x"), (2, "y"), (3, "z")), self.table((1, "x"), (2, None), (3, "w"))
            ),
            "row 1 column b: 'y' against None",
        )


class FixtureRootTestCase(CommandTestCase):
    """A root from `build_fixture_root`, in which the sampled 13F-HR is fetched as FETCHED_13F."""

    def setUp(self) -> None:
        super().setUp()
        self.zip_path = build_fixture_root(self)

    def fetch(self, session: FixtureSession, **kwargs) -> int:
        for row in read_table(self.layout, "sample").to_pylist():
            if row["form_type"] == "13F-HR":
                session.replies[row["url"]] = FakeResponse(200, [FETCHED_13F])
        return super().fetch(session, **kwargs)


class RebuildTests(FixtureRootTestCase):
    def setUp(self) -> None:
        super().setUp()
        parent = tempfile.TemporaryDirectory()
        self.addCleanup(parent.cleanup)
        self.temp_parent = Path(parent.name)

    def rebuild(self) -> tuple[int, list[str]]:
        return run_rebuild(self.layout, self.zip_path, temp_parent=self.temp_parent)

    def assert_temp_parent_empty(self) -> None:
        self.assertEqual(list(self.temp_parent.iterdir()), [])

    def test_equal_tables_give_exit_0(self):
        # The index fixture has no 10-K or 10-Q, so only `facts` and `facts_status` are empty.
        for name in REBUILT_TABLES:
            if name not in ("facts", "facts_status"):
                self.assertGreater(read_table(self.layout, name).num_rows, 0, name)
        refetch = read_table(self.layout, "refetches").to_pylist()[0]
        self.assertIs(refetch["sha256_equal"], False)
        self.assertTrue(refetch["changed_documents"])

        self.assertEqual(self.rebuild(), (0, ALL_EQUAL))
        self.assert_temp_parent_empty()

    def test_a_changed_live_table_gives_exit_1_and_names_it(self):
        rows = read_table(self.layout, "parties").to_pylist()
        original = rows[0]["name"]
        rows[0]["name"] = original + " CHANGED"
        write_table(self.layout, "parties", rows)

        code, lines = self.rebuild()

        self.assertEqual(code, 1)
        self.assertEqual(len(lines), len(REBUILT_TABLES))
        for name, line in zip(REBUILT_TABLES, lines, strict=True):
            if name == "parties":
                self.assertTrue(line.startswith("parties: row 0 column name:"), line)
                self.assertEqual(
                    line,
                    f"parties: row 0 column name: {original + ' CHANGED'!r} against {original!r}",
                )
            else:
                self.assertEqual(line, f"{name}: equal")

    def test_rebuild_leaves_the_root_unchanged(self):
        root = self.layout.root
        ledgers = (self.layout.ledger, self.layout.stage2_ledger)
        digests, stamps = file_digests(root), path_stamps(root)
        counts = [line_count(ledger) for ledger in ledgers]
        runs = line_count(self.layout.runs)
        self.assertTrue(all(counts), counts)
        self.assertIn("fetch.lock", digests)

        code, lines = run_cli("rebuild", "--out", str(root), "--zip", str(self.zip_path))

        self.assertEqual((code, lines), (0, ALL_EQUAL))
        self.assertEqual(file_digests(root), digests)
        self.assertEqual([line_count(ledger) for ledger in ledgers], counts)
        self.assertEqual(path_stamps(root), stamps)
        records = [json.loads(line) for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(len(records), runs + 1)
        self.assertEqual(records[-1]["step"], "rebuild")

    def test_missing_live_table_and_failed_step(self):
        self.layout.table("refetches").unlink()

        code, lines = self.rebuild()

        self.assertEqual(code, 1)
        self.assertIn("refetches: no live table", lines)
        self.assertEqual(lines, [*ALL_EQUAL[:-1], "refetches: no live table"])
        self.assert_temp_parent_empty()

        size = self.zip_path.stat().st_size
        with mock.patch.object(index, "INDEX_SIZE", size + 1):
            result = self.rebuild()

        self.assertEqual(
            result,
            (1, [f"rebuild failed: ValueError: {self.zip_path}: size {size}, expected {size + 1}"]),
        )
        self.assert_temp_parent_empty()

    def test_the_steps_write_only_into_a_folder_of_temp_parent(self):
        with mock.patch.object(sample, "run_sample", wraps=sample.run_sample) as spy:
            self.assertEqual(self.rebuild()[0], 0)

        scratch = spy.call_args.args[0]
        self.assertEqual(scratch.root, self.layout.root)
        self.assertEqual(scratch.tables.parent, self.temp_parent)
        self.assertFalse(scratch.tables.exists())

        with (
            mock.patch.object(index, "INDEX_SIZE", 0),
            mock.patch.object(index, "run_index", wraps=index.run_index) as spy,
        ):
            self.assertEqual(self.rebuild()[0], 1)

        scratch = spy.call_args.args[0]
        self.assertEqual(scratch.tables.parent, self.temp_parent)
        self.assertFalse(scratch.tables.exists())

    def test_rebuild_never_loads_requests(self):
        sha256, size = fingerprint(self.zip_path)
        code = (
            "import sys\n"
            "from sec_filing_data import cli, index\n"
            "index.INDEX_SHA256, index.INDEX_SIZE = sys.argv[1], int(sys.argv[2])\n"
            "print(cli.main(['rebuild', '--out', sys.argv[3], '--zip', sys.argv[4]]))\n"
            "print('requests' in sys.modules)\n"
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                sha256,
                str(size),
                str(self.layout.root),
                str(self.zip_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.splitlines()[-2:], ["0", "False"])


class CheckStage1Tests(FixtureRootTestCase):
    def freeze_stage1(self) -> None:
        """Write `tables-stage1` as each live table restricted to its Stage 1 columns."""
        self.layout.tables_stage1.mkdir()
        for name, columns in STAGE1_COLUMNS.items():
            frozen = read_table(self.layout, name).select(columns)
            pq.write_table(frozen, self.layout.tables_stage1 / f"{name}.parquet")

    def rewrite_documents(self, column: str, value: object) -> None:
        rows = read_table(self.layout, "documents").to_pylist()
        rows[0][column] = value
        write_table(self.layout, "documents", rows)

    def test_check_stage1_compares_the_frozen_columns(self):
        self.freeze_stage1()
        names = sorted(STAGE1_COLUMNS)

        self.assertEqual(check_stage1(self.layout), (0, [f"{name}: equal" for name in names]))

        self.rewrite_documents("type", "CHANGED")
        code, lines = check_stage1(self.layout)

        self.assertEqual(code, 1)
        for name, line in zip(names, lines, strict=True):
            if name == "documents":
                self.assertTrue(line.startswith("documents: row 0 column type:"), line)
            else:
                self.assertEqual(line, f"{name}: equal")

    def test_check_stage1_ignores_the_stage2_columns(self):
        self.freeze_stage1()

        self.rewrite_documents("public_rule", "CHANGED")

        self.assertEqual(
            check_stage1(self.layout), (0, [f"{name}: equal" for name in sorted(STAGE1_COLUMNS)])
        )

    def test_no_tables_stage1_folder(self):
        self.assertEqual(check_stage1(self.layout), (1, ["no tables-stage1 folder"]))

    def test_an_empty_tables_stage1_folder_fails(self):
        self.layout.tables_stage1.mkdir()
        # A leftover partial write is not a table.
        (self.layout.tables_stage1 / "documents.parquet.part").write_bytes(b"")

        self.assertEqual(check_stage1(self.layout), (1, ["no tables in tables-stage1"]))
        self.assertEqual(
            run_cli("check-stage1", "--out", str(self.layout.root)),
            (1, ["no tables in tables-stage1"]),
        )

    def test_a_live_table_without_a_frozen_column(self):
        self.freeze_stage1()
        # `documents` sorts first, so every other table comes after the short one.
        live = read_table(self.layout, "documents")
        pq.write_table(live.drop_columns(["description", "type"]), self.layout.table("documents"))
        expected = [
            "documents: missing columns type, description",
            *[f"{name}: equal" for name in sorted(STAGE1_COLUMNS) if name != "documents"],
        ]

        self.assertEqual(check_stage1(self.layout), (1, expected))
        self.assertEqual(run_cli("check-stage1", "--out", str(self.layout.root)), (1, expected))
        steps = [json.loads(line)["step"] for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(steps, ["check-stage1"])

    def test_a_frozen_table_with_no_live_table(self):
        self.freeze_stage1()
        self.layout.table("facts").unlink()

        code, lines = check_stage1(self.layout)

        self.assertEqual(code, 1)
        self.assertIn("facts: no live table", lines)

    def test_check_stage1_command(self):
        root = str(self.layout.root)
        self.assertEqual(run_cli("check-stage1", "--out", root), (1, ["no tables-stage1 folder"]))
        self.freeze_stage1()

        code, lines = run_cli("check-stage1", "--out", root)

        self.assertEqual((code, lines), (0, [f"{name}: equal" for name in sorted(STAGE1_COLUMNS)]))
        steps = [json.loads(line)["step"] for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(steps, ["check-stage1", "check-stage1"])


class BuildFetchesTests(FixtureRootTestCase):
    def test_build_fetches_writes_the_table_of_build_fetches(self):
        self.layout.table("fetches").unlink()
        expected = build_fetches(self.layout)
        counts = Counter(row["outcome"] for row in expected)
        self.assertGreater(counts["ok"], 0)

        with mock.patch.dict(os.environ):
            os.environ.pop(cli.USER_AGENT_VARIABLE, None)
            code, lines = run_cli("build-fetches", "--out", str(self.layout.root))

        self.assertEqual(code, 0)
        listed = [f"{name}: {counts[name]}" for name in FETCH_OUTCOMES if counts[name]]
        self.assertEqual(lines, listed)
        self.assertIn(f"ok: {counts['ok']}", lines)
        self.assertEqual(read_table(self.layout, "fetches").to_pylist(), expected)
        steps = [json.loads(line)["step"] for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(steps[-1], "build-fetches")

    def test_build_fetches_never_loads_requests(self):
        code = (
            "import sys\n"
            "from sec_filing_data import cli, version\n"
            "version.current_checkout = lambda: version.Checkout('5ca1ab1e' * 5, True, None)\n"
            "print(cli.main(['build-fetches', '--out', sys.argv[1]]))\n"
            "print('requests' in sys.modules)\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", code, str(self.layout.root)],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.splitlines()[-2:], ["0", "False"])


class CheckFrozenTests(FixtureRootTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.names = sorted(path.stem for path in self.layout.tables.glob("*.parquet"))
        self.frozen = self.layout.tables_stage2

    def freeze(self) -> None:
        shutil.copytree(self.layout.tables, self.frozen)

    def check(self) -> tuple[int, list[str]]:
        return check_frozen(self.layout, self.frozen)

    def test_check_frozen_compares_every_column(self):
        self.freeze()

        self.assertEqual(self.check(), (0, [f"{name}: equal" for name in self.names]))

        rows = read_table(self.layout, "documents").to_pylist()
        rows[0]["type"] = "CHANGED"
        write_table(self.layout, "documents", rows)
        code, lines = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(len(lines), len(self.names))
        for name, line in zip(self.names, lines, strict=True):
            if name == "documents":
                self.assertTrue(line.startswith("documents: row 0 column"), line)
            else:
                self.assertEqual(line, f"{name}: equal")

        path = self.frozen / "sample.parquet"
        table = pq.read_table(path)
        extra = pa.array([None] * table.num_rows, pa.string())
        pq.write_table(table.append_column("extra", extra), path)
        code, lines = self.check()

        self.assertEqual(code, 1)
        self.assertTrue(lines[self.names.index("sample")].startswith("sample: schema:"), lines)

        shutil.rmtree(self.frozen)

        self.assertEqual(self.check(), (1, ["no tables-stage2 folder"]))

    def test_a_live_column_that_the_frozen_table_lacks(self):
        # `check-stage1` lets a live column that the frozen copy lacks pass. This check does not.
        self.freeze()
        path = self.frozen / "documents.parquet"
        pq.write_table(pq.read_table(path).drop_columns(["description"]), path)

        code, lines = self.check()

        self.assertEqual(code, 1)
        line = lines[self.names.index("documents")]
        self.assertTrue(line.startswith("documents: schema:"), line)
        self.assertEqual(lines.count("documents: equal"), 0)

    def test_a_frozen_table_with_no_live_table(self):
        self.freeze()
        self.layout.table("facts").unlink()

        code, lines = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(lines[self.names.index("facts")], "facts: no live table")

    def test_an_empty_frozen_folder_fails(self):
        self.frozen.mkdir()
        # A leftover partial write is not a table.
        (self.frozen / "documents.parquet.part").write_bytes(b"")

        self.assertEqual(self.check(), (1, ["no tables in tables-stage2"]))

    def test_check_frozen_command(self):
        root = str(self.layout.root)
        argv = ["check-frozen", "--out", root, "--folder", "tables-stage2"]
        self.assertEqual(run_cli(*argv), (1, ["no tables-stage2 folder"]))
        self.freeze()

        dirty = version.Checkout("5ca1ab1e" * 5, False, "uncommitted changes in uv.lock")
        with mock.patch.object(version, "current_checkout", lambda: dirty):
            code, lines = run_cli(*argv)

        self.assertEqual((code, lines), (0, [f"{name}: equal" for name in self.names]))
        steps = [json.loads(line)["step"] for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(steps, ["check-frozen", "check-frozen"])

    def test_check_frozen_takes_only_the_stage2_folder(self):
        with (
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            run_cli("check-frozen", "--out", str(self.layout.root), "--folder", "tables-stage1")

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
