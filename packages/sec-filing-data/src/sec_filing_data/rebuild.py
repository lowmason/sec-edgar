"""The `rebuild` command: every table built again in a temporary folder and compared with
the live table. The `check-stage1` command: the Stage 1 columns of each live table compared
with the frozen copy in `tables-stage1`.

Both read the root in place and write nothing under it. This module does not import
`requests`.
"""

import tempfile
from pathlib import Path

import pyarrow as pa

from sec_filing_data import facts, index, ownership, refetches, sample, submissions
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import build_fetches
from sec_filing_data.tables import read_table, write_table

REBUILT_TABLES = (
    "index",
    "sample",
    "fetches",
    "filings",
    "parties",
    "documents",
    "facts",
    "facts_status",
    "ownership",
    "ownership_status",
    "refetches",
)

EQUAL = "equal"
NO_LIVE_TABLE = "no live table"
NO_STAGE1_FOLDER = "no tables-stage1 folder"


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
    the live table of `layout`.

    The steps read the zip, the bytes and both ledgers in place, through the live root. Gives
    one line per table and exit 0 when every table is equal. A step or a table read that
    raises gives one `rebuild failed` line and exit 1. The temporary folder is removed in
    every case.
    """
    with tempfile.TemporaryDirectory(dir=temp_parent) as folder:
        scratch = Layout(layout.root, tables_dir=Path(folder))
        try:
            _build_tables(scratch, zip_path)
            results = [(name, _compare_with_live(layout, scratch, name)) for name in REBUILT_TABLES]
        except Exception as error:
            return 1, [f"rebuild failed: {type(error).__name__}: {error}"]
    return _outcome(results)


def _build_tables(scratch: Layout, zip_path: Path) -> None:
    """Run the offline steps in the order of the live run. `fetches` is written as `fetch`
    writes it, from the ledger and the bytes on disk."""
    index.run_index(scratch, zip_path)
    sample.run_sample(scratch)
    write_table(scratch, "fetches", build_fetches(scratch))
    # `envelopes` writes `filings`, which `facts` and `ownership` read.
    submissions.run_envelopes(scratch)
    facts.run_facts(scratch)
    ownership.run_ownership(scratch)
    refetches.run_compare_refetches(scratch)


def _compare_with_live(live: Layout, rebuilt: Layout, name: str) -> str:
    if not live.table(name).exists():
        return NO_LIVE_TABLE
    return compare_table(read_table(live, name), read_table(rebuilt, name))


def check_stage1(layout: Layout) -> tuple[int, list[str]]:
    """Compare each table of `tables-stage1`, by name, with the same columns of the live table.

    Gives one line per frozen table and exit 0 when every table is equal.
    """
    if not layout.tables_stage1.is_dir():
        return 1, [NO_STAGE1_FOLDER]
    frozen = Layout(layout.root, tables_dir=layout.tables_stage1)
    names = sorted(path.stem for path in layout.tables_stage1.glob("*.parquet"))
    return _outcome([(name, _compare_frozen(frozen, layout, name)) for name in names])


def _compare_frozen(frozen: Layout, live: Layout, name: str) -> str:
    if not live.table(name).exists():
        return NO_LIVE_TABLE
    expected = read_table(frozen, name)
    return compare_table(expected, read_table(live, name).select(expected.column_names))


def _outcome(results: list[tuple[str, str]]) -> tuple[int, list[str]]:
    code = 0 if all(result == EQUAL for _, result in results) else 1
    return code, [f"{name}: {result}" for name, result in results]
