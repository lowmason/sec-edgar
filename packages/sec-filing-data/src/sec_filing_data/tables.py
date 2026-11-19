"""Schemas of the plain tables, and their parquet read and write."""

import hashlib
import os
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from sec_filing_data import version
from sec_filing_data.layout import Layout

_TIMESTAMP = pa.timestamp("us", tz="UTC")


def _schema(*columns: str | tuple[str, pa.DataType]) -> pa.Schema:
    """Build a schema. A bare column name is a string column."""
    return pa.schema(
        pa.field(*column) if isinstance(column, tuple) else pa.field(column, pa.string())
        for column in columns
    )


# The five times of a filing, as they are copied onto each record of it.
FILING_TIME_COLUMNS = ("accepted_at", "public_at", "public_rule", "last_modified_at", "fetched_at")
_FILING_TIMES = (
    ("accepted_at", _TIMESTAMP),
    ("public_at", _TIMESTAMP),
    "public_rule",
    ("last_modified_at", _TIMESTAMP),
    ("fetched_at", _TIMESTAMP),
)
_PROVENANCE = ("source_url", "source_sha256", *_FILING_TIMES)


SCHEMAS: dict[str, pa.Schema] = {
    "index": _schema(
        ("line_number", pa.int64()),
        ("cik", pa.int64()),
        "company_name",
        "form_type",
        ("date_filed", pa.date32()),
        "filename",
        "accession_number",
        "source_url",
        "source_sha256",
        ("index_built_at", _TIMESTAMP),
        "index_data_through",
        ("index_received_at", _TIMESTAMP),
        ("index_last_modified_at", _TIMESTAMP),
        *_FILING_TIMES,
    ),
    "sample": _schema(
        ("draw", pa.int32()),
        "stratum",
        "accession_number",
        "form_type",
        ("cik", pa.int64()),
        "company_name",
        ("date_filed", pa.date32()),
        "filename",
        "url",
    ),
    "fetches": _schema(
        "accession_number",
        "form_type",
        "outcome",
        "reason",
        ("status", pa.int32()),
        ("attempts", pa.int32()),
        ("wire_bytes", pa.int64()),
        ("body_bytes", pa.int64()),
        "sha256",
        ("fetched_at", _TIMESTAMP),
        "path",
    ),
    "filings": _schema(
        "accession_number",
        "form_type",
        "outcome",
        "reason",
        ("fetched_at", _TIMESTAMP),
        "sha256",
        "submission_type",
        "acceptance_datetime",
        "filed_as_of_date",
        "date_as_of_change",
        ("private_to_public", pa.bool_()),
        "period_of_report",
        "public_document_count",
        ("document_count", pa.int32()),
        "parse_error",
        "source_url",
        ("accepted_at", _TIMESTAMP),
        ("public_at", _TIMESTAMP),
        "public_rule",
        ("last_modified_at", _TIMESTAMP),
    ),
    "parties": _schema("accession_number", "role", "name", "cik", *_PROVENANCE),
    "documents": _schema(
        "accession_number",
        ("sequence", pa.int32()),
        "type",
        "filename",
        "description",
        ("text_offset", pa.int64()),
        ("text_length", pa.int64()),
        *_PROVENANCE,
    ),
    "facts": _schema(
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
        ("is_nil", pa.bool_()),
        *_PROVENANCE,
    ),
    "facts_status": _schema(
        "accession_number",
        "form_type",
        "source_document",
        ("fact_count", pa.int32()),
        "reason",
    ),
    "ownership": _schema(
        "accession_number",
        "form_type",
        "record_kind",
        "issuer_cik",
        "issuer_name",
        "issuer_cusip",
        "owner_cik",
        "owner_name",
        ("owner_count", pa.int32()),
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
        "source_url",
        "source_sha256",
        "source_document",
        *_FILING_TIMES,
    ),
    "ownership_status": _schema(
        "accession_number",
        "form_type",
        ("record_count", pa.int32()),
        "reason",
    ),
    "refetches": _schema(
        "accession_number",
        "outcome",
        "stage1_sha256",
        "refetch_sha256",
        ("sha256_equal", pa.bool_()),
        ("stage1_last_modified_at", _TIMESTAMP),
        ("refetch_last_modified_at", _TIMESTAMP),
        ("refetched_at", _TIMESTAMP),
        "changed_header_fields",
        "changed_documents",
    ),
    "partners": _schema(
        "accession_number",
        "form_type",
        ("cik", pa.int64()),
        "company_name",
        ("date_filed", pa.date32()),
        "filename",
        "url",
        "rule",
        "sampled_accession",
    ),
    "links": _schema(
        "accession_number",
        "form_type",
        "held_in",
        "link_rule",
        "declared_previous_accession",
        "declared_original_date",
        "declared_period",
        "amendment_number",
        "amendment_type",
        "original_accession",
        "original_held_in",
        "link_problem",
        "source_url",
        "source_sha256",
        "source_document",
        *_FILING_TIMES,
    ),
}

# The tables of `tables/`, in the order of `SCHEMAS`. The tables of `stage4/tables/` are the
# ones of `STAGE4_TABLES`: five of them repeat a Stage 3 name.
STAGE3_TABLES = (
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
STAGE4_TABLES = (
    "partners",
    "fetches",
    "filings",
    "parties",
    "documents",
    "ownership",
    "ownership_status",
    "links",
)

# The format number of each table. It goes up by 1 when the table's columns, their order or
# their types change. `tests/test_tables.py` pins each schema to its number.
TABLE_FORMATS: dict[str, int] = {
    "index": 2,
    "sample": 1,
    "fetches": 1,
    "filings": 2,
    "parties": 2,
    "documents": 2,
    "facts": 2,
    "facts_status": 1,
    "ownership": 2,
    "ownership_status": 1,
    "refetches": 1,
    "partners": 1,
    "links": 1,
}

# The four values that a table file records about its origin. Each is stored in the file's
# key-value metadata under `sec_filing_data.<key>`.
STAMP_KEYS = ("code_version", "python_version", "pyarrow_version", "table_format")
_METADATA_PREFIX = "sec_filing_data."


def schema_fingerprint(schema: pa.Schema) -> str:
    """The SHA-256 of the schema's column names and types, in order, as hex."""
    description = "\n".join(f"{field.name}: {field.type}" for field in schema)
    return hashlib.sha256(description.encode("utf-8")).hexdigest()


def _stamped_schema(name: str) -> pa.Schema:
    stamp = version.current_stamp()
    values = {
        "code_version": stamp.code_version or version.NOT_RECORDED,
        "python_version": stamp.python_version,
        "pyarrow_version": stamp.pyarrow_version,
        "table_format": str(TABLE_FORMATS[name]),
    }
    return SCHEMAS[name].with_metadata(
        {f"{_METADATA_PREFIX}{key}": values[key] for key in STAMP_KEYS}
    )


def read_stamp(path: Path) -> dict[str, str]:
    """The four stamp values of a table file, by short key. An absent key reads `not recorded`."""
    footer = pq.read_metadata(path).metadata or {}
    return {
        key: footer.get(f"{_METADATA_PREFIX}{key}".encode(), version.NOT_RECORDED.encode()).decode()
        for key in STAMP_KEYS
    }


def write_table(layout: Layout, name: str, rows: list[dict[str, Any]]) -> None:
    """Write `rows` as table `name`: to a temporary file first, then rename it into place.

    The file's metadata holds the stamp of the code that wrote it and the table's format number.
    A key that is not in the schema raises `ValueError`, because pyarrow would drop it
    silently. A missing key is written as null.
    """
    schema = _stamped_schema(name)
    unknown = set().union(*rows) - set(schema.names)
    if unknown:
        raise ValueError(f"table {name}: keys not in its schema: {sorted(unknown)}")
    table = pa.Table.from_pylist(rows, schema=schema)
    path = layout.table(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    try:
        pq.write_table(table, temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_table(layout: Layout, name: str) -> pa.Table:
    return pq.read_table(layout.table(name))


def as_table_rows(name: str, rows: list[dict]) -> list[dict]:
    """`rows` as they read back from table `name`: the schema's types, null for a missing key."""
    return pa.Table.from_pylist(rows, schema=SCHEMAS[name]).to_pylist()
