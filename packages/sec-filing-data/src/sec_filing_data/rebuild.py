"""The `rebuild` command: every table built again in a temporary folder and compared with
the live table, and the Stage 4 tables too when the root has a `stage4/` folder. The
`check-stage1` command: the Stage 1 columns of each live table compared with the frozen copy in
`tables-stage1`. The `check-frozen` command: every table of a frozen folder compared with the
live table, on every column.

All three read the root in place and write nothing under it. This module does not import
`requests`.
"""

import tempfile
from pathlib import Path

import pyarrow as pa

from sec_filing_data import (
    facts,
    index,
    ownership,
    partner_tables,
    partners,
    refetches,
    sample,
    submissions,
)
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import run_fetches
from sec_filing_data.tables import STAGE3_TABLES, STAGE4_TABLES, read_table

REBUILT_TABLES = STAGE3_TABLES

EQUAL = "equal"
NO_LIVE_TABLE = "no live table"
NO_STAGE1_FOLDER = "no tables-stage1 folder"
NO_STAGE1_TABLES = "no tables in tables-stage1"


def compare_table(expected: pa.Table, actual: pa.Table) -> str:
    """`equal`, or the first difference: the schema, then the row count, then the first
    value in row order, column by column."""
    if expected.equals(actual):
        return EQUAL
    if not expected.schema.equals(actual.schema):
        return f"schema: {_describe(expected.schema)} against {_describe(actual.schema)}"
    if expected.num_rows != actual.num_rows:
        return f"rows: {expected.num_rows} against {actual.num_rows}"
    rows = zip(expected.to_pylist(), actual.to_pylist(), strict=True)
    for number, (want, got) in enumerate(rows):
        for name in expected.column_names:
            if want[name] != got[name]:
                return f"row {number} column {name}: {want[name]!r} against {got[name]!r}"
    # Not reached for the column types of SCHEMAS: equal values in equal schemas are equal tables.
    return "differs, but no value does"


def _describe(schema: pa.Schema) -> str:
    """The schema's fields on one line."""
    text = schema.to_string(show_field_metadata=False, show_schema_metadata=False)
    return text.replace("\n", ", ")


def run_rebuild(
    layout: Layout, zip_path: Path, *, temp_parent: Path | None = None
) -> tuple[int, list[str]]:
    """Build every table of REBUILT_TABLES again in a temporary folder, and compare it with
    the live table of `layout`. When the root has a `stage4/` folder, do the same for each
    table of STAGE4_TABLES.

    The steps read the zip, the bytes and the ledgers in place, through the live root. The
    Stage 4 tables take the Stage 3 tables that were just rebuilt as their inputs. Gives one
    line per table and exit 0 when every table is equal. A Stage 4 line reads
    `stage4 <name>: <result>`, because five Stage 4 tables have the name of a Stage 3 table.
    A step or a table read that raises gives one `rebuild failed` line and exit 1. The
    temporary folder is removed in every case.
    """
    with tempfile.TemporaryDirectory(dir=temp_parent) as folder:
        scratch = Layout(
            layout.root, tables_dir=Path(folder), stage4_tables_dir=Path(folder) / "stage4"
        )
        try:
            _build_tables(scratch, zip_path)
            results = [(name, _compare_with_live(layout, scratch, name)) for name in REBUILT_TABLES]
            if layout.stage4.is_dir():
                _build_stage4_tables(scratch)
                results += [
                    (
                        f"stage4 {name}",
                        _compare_with_live(layout.stage4_view, scratch.stage4_view, name),
                    )
                    for name in STAGE4_TABLES
                ]
        except Exception as error:
            return 1, [f"rebuild failed: {type(error).__name__}: {error}"]
    return _outcome(results)


def _build_tables(scratch: Layout, zip_path: Path) -> None:
    """Run the offline steps in the order of the live run. `fetches` is written as `fetch`
    writes it, from the ledger and the bytes on disk."""
    index.run_index(scratch, zip_path)
    sample.run_sample(scratch)
    run_fetches(scratch)
    # `envelopes` writes `filings`, which `facts` and `ownership` read.
    submissions.run_envelopes(scratch)
    facts.run_facts(scratch)
    ownership.run_ownership(scratch)
    refetches.run_compare_refetches(scratch)


def _build_stage4_tables(scratch: Layout) -> None:
    """Run the offline Stage 4 steps on the rebuilt Stage 3 tables. They read the Stage 4
    ledger and the partner bytes in place, and write the Stage 4 tables of `scratch`."""
    partners.run_partners(scratch)
    partner_tables.run_partner_tables(scratch)


def _compare_with_live(live: Layout, rebuilt: Layout, name: str) -> str:
    if not live.table(name).exists():
        return NO_LIVE_TABLE
    return compare_table(read_table(live, name), read_table(rebuilt, name))


def check_stage1(layout: Layout) -> tuple[int, list[str]]:
    """Compare each table of `tables-stage1`, by name, with the same columns of the live table.

    Gives one line per frozen table and exit 0 when every table is equal. A missing or empty
    `tables-stage1` gives one line and exit 1, as it compares nothing.
    """
    if not layout.tables_stage1.is_dir():
        return 1, [NO_STAGE1_FOLDER]
    frozen = Layout(layout.root, tables_dir=layout.tables_stage1)
    names = sorted(path.stem for path in layout.tables_stage1.glob("*.parquet"))
    if not names:
        return 1, [NO_STAGE1_TABLES]
    return _outcome([(name, _compare_frozen(frozen, layout, name)) for name in names])


def _compare_frozen(frozen: Layout, live: Layout, name: str) -> str:
    if not live.table(name).exists():
        return NO_LIVE_TABLE
    expected, actual = read_table(frozen, name), read_table(live, name)
    missing = [column for column in expected.column_names if column not in actual.column_names]
    if missing:
        return f"missing columns {', '.join(missing)}"
    return compare_table(expected, actual.select(expected.column_names))


def check_frozen(layout: Layout, frozen_dir: Path) -> tuple[int, list[str]]:
    """Compare each table of `frozen_dir`, by name, with the live table, schema and values.

    Unlike `check_stage1`, it compares the whole table: a column that only one side has is a
    difference. Gives one line per frozen table and exit 0 when every table is equal. A
    missing or empty folder gives one line and exit 1, as it compares nothing.
    """
    if not frozen_dir.is_dir():
        return 1, [f"no {frozen_dir.name} folder"]
    names = sorted(path.stem for path in frozen_dir.glob("*.parquet"))
    if not names:
        return 1, [f"no tables in {frozen_dir.name}"]
    frozen = Layout(layout.root, tables_dir=frozen_dir)
    return _outcome([(name, _compare_whole(frozen, layout, name)) for name in names])


def _compare_whole(frozen: Layout, live: Layout, name: str) -> str:
    if not live.table(name).exists():
        return NO_LIVE_TABLE
    return compare_table(read_table(frozen, name), read_table(live, name))


def _outcome(results: list[tuple[str, str]]) -> tuple[int, list[str]]:
    code = 0 if all(result == EQUAL for _, result in results) else 1
    return code, [f"{name}: {result}" for name, result in results]
