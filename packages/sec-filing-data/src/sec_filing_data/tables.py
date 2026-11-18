"""Schemas of the plain tables, and their parquet read and write."""

import os
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

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
}


def write_table(layout: Layout, name: str, rows: list[dict[str, Any]]) -> None:
    """Write `rows` as table `name`: to a temporary file first, then rename it into place.

    A key that is not in the schema raises `ValueError`, because pyarrow would drop it
    silently. A missing key is written as null.
    """
    schema = SCHEMAS[name]
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
