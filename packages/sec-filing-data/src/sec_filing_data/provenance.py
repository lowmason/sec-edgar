"""The source and the times of a filing, as later tables copy them from its `filings` row.

This module does not import `requests`.
"""

from sec_filing_data.layout import Layout
from sec_filing_data.tables import FILING_TIME_COLUMNS, read_table


def filing_times(filing: dict) -> dict:
    """The five times of a `filings` row."""
    return {column: filing[column] for column in FILING_TIME_COLUMNS}


def record_provenance(filing: dict) -> dict:
    """What a record of this filing carries: where its bytes came from, and the five times."""
    return {
        "source_url": filing["source_url"],
        "source_sha256": filing["sha256"],
        **filing_times(filing),
    }


def read_provenance(layout: Layout) -> dict[str, dict]:
    """`record_provenance` of each `filings` row, by accession number."""
    path = layout.table("filings")
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run `envelopes` first")
    return {
        row["accession_number"]: record_provenance(row)
        for row in read_table(layout, "filings").to_pylist()
    }
