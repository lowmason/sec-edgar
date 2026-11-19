"""The `partner-tables` command: the Stage 4 tables of the partner filings (spec 5.4).

It reads `stage4/tables/partners`, the Stage 4 ledger and the partner bytes, and writes
`fetches`, `filings`, `parties`, `documents`, `ownership` and `ownership_status` under
`stage4/tables/`. The parse code is the Stage 3 code, unchanged, so each table has the schema
and the format number of its namesake under `tables/`. It sends no request, and does not
import `requests`.
"""

from typing import NamedTuple

from sec_filing_data.layout import Layout
from sec_filing_data.ledger import last_ok, read_ledger
from sec_filing_data.ownership import extract_ownership, ownership_form, ownership_rows
from sec_filing_data.partners import distinct_partners, partner_fetch_rows, read_partners
from sec_filing_data.provenance import record_provenance
from sec_filing_data.submissions import filing_records
from sec_filing_data.tables import as_table_rows, write_table


class PartnerRecords(NamedTuple):
    """The rows that one partner gives: its `filings` row, its `parties`, `documents` and
    `ownership` rows, and its `ownership_status` row, or None for a form with no ownership."""

    filing: dict
    parties: list[dict]
    documents: list[dict]
    ownership: list[dict]
    ownership_status: dict | None


def partner_records(
    partner: dict, fetched: dict, raw: bytes | None, ok_record: dict | None
) -> PartnerRecords:
    """The rows of one partner, from its `partners` row, its `fetches` row and its bytes.

    `raw` is None unless the outcome of `fetched` is `ok`. `ok_record` is the partner's last
    `ok` record in the Stage 4 ledger, or None. The rows are those that `envelopes` and
    `ownership` give for a sampled filing.
    """
    filing, parties, documents = filing_records(partner, fetched, raw, ok_record)
    form = ownership_form(partner["form_type"])
    if form is None:
        return PartnerRecords(filing, parties, documents, [], None)
    accession, form_type = partner["accession_number"], partner["form_type"]
    extraction = extract_ownership(form, fetched["outcome"], raw)
    status = {
        "accession_number": accession,
        "form_type": form_type,
        "record_count": len(extraction.records),
        "reason": extraction.reason,
    }
    # `ownership` reads the provenance from the stored `filings` table, so it is read the same
    # way here: with the table's types.
    provenance = record_provenance(as_table_rows("filings", [filing])[0])
    records = ownership_rows(accession, form_type, extraction, provenance)
    return PartnerRecords(filing, parties, documents, records, status)


def run_partner_tables(layout: Layout) -> dict[str, int]:
    """Write the partner tables under `stage4/tables/`, and give the row count of each.

    `fetches` comes from the Stage 4 ledger and the bytes on disk. The other tables take one
    distinct partner at a time, in accession order. A missing `partners` table raises
    FileNotFoundError before anything is written.
    """
    partners = read_partners(layout)
    records = read_ledger(layout.stage4_ledger)
    fetches = partner_fetch_rows(layout, partners, records)
    fetched = {row["accession_number"]: row for row in fetches}
    ok_records = last_ok(records)
    tables: dict[str, list[dict]] = {
        "fetches": fetches,
        "filings": [],
        "parties": [],
        "documents": [],
        "ownership": [],
        "ownership_status": [],
    }
    for partner in distinct_partners(partners):
        accession = partner["accession_number"]
        outcome = fetched[accession]["outcome"]
        raw = layout.partner_submission(accession).read_bytes() if outcome == "ok" else None
        parts = partner_records(partner, fetched[accession], raw, ok_records.get(accession))
        tables["filings"].append(parts.filing)
        tables["parties"].extend(parts.parties)
        tables["documents"].extend(parts.documents)
        tables["ownership"].extend(parts.ownership)
        if parts.ownership_status is not None:
            tables["ownership_status"].append(parts.ownership_status)
    for name, rows in tables.items():
        write_table(layout.stage4_view, name, rows)
    return {name: len(rows) for name, rows in tables.items()}
