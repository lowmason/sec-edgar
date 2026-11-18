"""The `compare-refetches` command: each Stage 2 refetch beside the Stage 1 copy of its filing.

It reads both ledgers and both copies, and sends no request. This module does not import
`requests`.
"""

import hashlib
from datetime import datetime

from sec_filing_data.envelope import EnvelopeError, Submission, parse_submission
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import ok_responses, read_ledger
from sec_filing_data.tables import write_table
from sec_filing_data.times import last_modified_at

UNPARSED = "unparsed"
# The header values that `Submission.fields` does not hold, by the name a change lists.
ACCEPTANCE_DATETIME = "ACCEPTANCE-DATETIME"
PRIVATE_TO_PUBLIC = "PRIVATE-TO-PUBLIC"
PARTIES = "parties"


def run_compare_refetches(layout: Layout) -> int:
    """Write `refetches`. It has no rows when there is no Stage 2 ledger."""
    write_table(layout, "refetches", build_refetches(layout))
    return 0


def build_refetches(layout: Layout) -> list[dict]:
    """One row per key with a request record in the Stage 2 ledger, in first-request order.

    `outcome` is the outcome of the response to the key's last request, with `retry` read
    as `failed`, or `no_response` when that request has no response. The Stage 1 values
    come from the last `ok` record in the Stage 1 ledger. The refetch values come from the
    last `ok` record in the Stage 2 ledger, and only when the refetch file exists.
    """
    last_request: dict[str, str] = {}
    responses: dict[str, dict] = {}
    for record in read_ledger(layout.stage2_ledger):
        if record["event"] == "request":
            # A dict keeps the position of a key's first insertion: first-request order.
            last_request[record["key"]] = record["id"]
        elif record["event"] == "response":
            responses[record["id"]] = record
    stage1 = ok_responses(layout.ledger)
    refetched = ok_responses(layout.stage2_ledger)
    rows = []
    for accession, request_id in last_request.items():
        refetch = refetched.get(accession) if layout.refetched(accession).exists() else None
        rows.append(
            _row(layout, accession, responses.get(request_id), stage1.get(accession), refetch)
        )
    return rows


def _row(
    layout: Layout,
    accession: str,
    response: dict | None,
    stage1: dict | None,
    refetch: dict | None,
) -> dict:
    stage1_sha256 = stage1["sha256"] if stage1 else None
    refetch_sha256 = refetch["sha256"] if refetch else None
    both = stage1_sha256 is not None and refetch_sha256 is not None
    row = {
        "accession_number": accession,
        "outcome": _outcome(response),
        "stage1_sha256": stage1_sha256,
        "refetch_sha256": refetch_sha256,
        "sha256_equal": stage1_sha256 == refetch_sha256 if both else None,
        "stage1_last_modified_at": last_modified_at(stage1["last_modified"]) if stage1 else None,
        "refetch_last_modified_at": last_modified_at(refetch["last_modified"]) if refetch else None,
        "refetched_at": datetime.fromisoformat(refetch["at"]) if refetch else None,
        "changed_header_fields": None,
        "changed_documents": None,
    }
    if row["sha256_equal"] is False:
        row.update(
            _changes(
                layout.submission(accession).read_bytes(),
                layout.refetched(accession).read_bytes(),
            )
        )
    return row


def _outcome(response: dict | None) -> str:
    if response is None:
        return "no_response"
    return "failed" if response["outcome"] == "retry" else response["outcome"]


def _changes(stage1: bytes, refetch: bytes) -> dict:
    """The header fields and the documents that differ between two copies of a filing.

    Each is a list joined with `;`. It is empty when nothing of that kind differs.
    """
    try:
        before, after = parse_submission(stage1), parse_submission(refetch)
    except EnvelopeError:
        return {"changed_header_fields": UNPARSED, "changed_documents": UNPARSED}
    documents_before = _document_entries(stage1, before)
    documents_after = _document_entries(refetch, after)
    return {
        "changed_header_fields": ";".join(_changed_header(before, after)),
        "changed_documents": ";".join(_changed(documents_before, documents_after)),
    }


def _changed_header(before: Submission, after: Submission) -> list[str]:
    """Changed header labels, then `ACCEPTANCE-DATETIME`, `PRIVATE-TO-PUBLIC` and `parties`."""
    changed = _changed(_field_values(before), _field_values(after))
    if before.acceptance_datetime != after.acceptance_datetime:
        changed.append(ACCEPTANCE_DATETIME)
    if before.private_to_public != after.private_to_public:
        changed.append(PRIVATE_TO_PUBLIC)
    if before.parties != after.parties:
        changed.append(PARTIES)
    return changed


def _changed(before: dict[str, list], after: dict[str, list]) -> list[str]:
    """The names whose entries differ, in first-seen order: the Stage 1 copy's names first."""
    names = dict.fromkeys([*before, *after])
    return [name for name in names if before.get(name) != after.get(name)]


def _field_values(submission: Submission) -> dict[str, list[str]]:
    """Each header label with all its values, as a label can be filed more than once."""
    values: dict[str, list[str]] = {}
    for label, value in submission.fields:
        values.setdefault(label, []).append(value)
    return values


def _document_entries(raw: bytes, submission: Submission) -> dict[str, list[tuple]]:
    """Each document by its sequence number, or by `#<position>` (from 1) when it has none.

    An entry holds the document's type, file name, description and the SHA-256 of its text.
    Its offset is left out: it moves whenever an earlier part of the file changes length.
    """
    entries: dict[str, list[tuple]] = {}
    view = memoryview(raw)
    for position, document in enumerate(submission.documents, start=1):
        name = str(document.sequence) if document.sequence is not None else f"#{position}"
        end = document.text_offset + document.text_length
        text_sha256 = hashlib.sha256(view[document.text_offset : end]).hexdigest()
        entries.setdefault(name, []).append(
            (document.type, document.filename, document.description, text_sha256)
        )
    return entries
