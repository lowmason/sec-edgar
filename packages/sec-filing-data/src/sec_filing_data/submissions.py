"""The `envelopes` command: the header and document list of each fetched submission file."""

from operator import itemgetter

from sec_filing_data.envelope import EnvelopeError, Submission, parse_submission
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import build_fetches, ok_responses
from sec_filing_data.provenance import record_provenance
from sec_filing_data.tables import read_table, write_table
from sec_filing_data.times import accepted_at, last_modified_at, public_time

# `filings` columns that hold one header field each, as filed text.
HEADER_FIELDS = {
    "submission_type": "CONFORMED SUBMISSION TYPE",
    "filed_as_of_date": "FILED AS OF DATE",
    "date_as_of_change": "DATE AS OF CHANGE",
    "period_of_report": "CONFORMED PERIOD OF REPORT",
    "public_document_count": "PUBLIC DOCUMENT COUNT",
}

_NOT_PARSED = dict.fromkeys(
    [*HEADER_FIELDS, "acceptance_datetime", "private_to_public", "document_count", "parse_error"]
)
_NO_TIMES = dict.fromkeys(["accepted_at", "public_at", "public_rule", "last_modified_at"])


def run_envelopes(layout: Layout) -> int:
    """Write `filings` (one row per sampled filing), `parties` and `documents`.

    It reads `fetches` from its table, or builds it from the ledger when the table is
    missing. Only `ok` filings are parsed. A filing that is not `ok` gets its outcome as
    `reason`, and one whose bytes do not parse gets `parse_error`.
    """
    sample = sorted(read_table(layout, "sample").to_pylist(), key=itemgetter("draw"))
    fetches = {row["accession_number"]: row for row in _read_fetches(layout)}
    last_ok = ok_responses(layout.ledger)
    filings, parties, documents = [], [], []
    for sampled in sample:
        accession = sampled["accession_number"]
        fetched = fetches[accession]
        filing = {
            "accession_number": accession,
            "form_type": sampled["form_type"],
            "outcome": fetched["outcome"],
            "reason": None,
            "fetched_at": fetched["fetched_at"],
            "sha256": fetched["sha256"],
            "source_url": sampled["url"],
            **_NOT_PARSED,
            **_NO_TIMES,
        }
        if fetched["outcome"] != "ok":
            filing["reason"] = fetched["outcome"]
        else:
            if accession in last_ok:
                filing["last_modified_at"] = last_modified_at(last_ok[accession]["last_modified"])
            try:
                submission = parse_submission(layout.submission(accession).read_bytes())
            except EnvelopeError as error:
                filing["parse_error"] = str(error)
            else:
                filing.update(_header_columns(submission))
                filing.update(_public_times(submission))
                provenance = record_provenance(filing)
                parties.extend(_party_rows(accession, submission, provenance))
                documents.extend(_document_rows(accession, submission, provenance))
        filings.append(filing)
    write_table(layout, "filings", filings)
    write_table(layout, "parties", parties)
    write_table(layout, "documents", documents)
    return 0


def _read_fetches(layout: Layout) -> list[dict]:
    if layout.table("fetches").exists():
        return read_table(layout, "fetches").to_pylist()
    return build_fetches(layout)


def _header_columns(submission: Submission) -> dict:
    columns = {column: submission.field(label) for column, label in HEADER_FIELDS.items()}
    columns.update(
        acceptance_datetime=submission.acceptance_datetime,
        private_to_public=submission.private_to_public,
        document_count=len(submission.documents),
    )
    return columns


def _public_times(submission: Submission) -> dict:
    accepted = accepted_at(submission.acceptance_datetime)
    public, rule = public_time(
        accepted,
        submission.field(HEADER_FIELDS["filed_as_of_date"]),
        private_to_public=submission.private_to_public,
    )
    return {"accepted_at": accepted, "public_at": public, "public_rule": rule}


def _party_rows(accession: str, submission: Submission, provenance: dict) -> list[dict]:
    return [
        {
            "accession_number": accession,
            "role": party.role,
            "name": party.name,
            "cik": party.cik,
            **provenance,
        }
        for party in submission.parties
    ]


def _document_rows(accession: str, submission: Submission, provenance: dict) -> list[dict]:
    return [
        {
            "accession_number": accession,
            "sequence": document.sequence,
            "type": document.type,
            "filename": document.filename,
            "description": document.description,
            "text_offset": document.text_offset,
            "text_length": document.text_length,
            **provenance,
        }
        for document in submission.documents
    ]
