"""The `ownership` command: the ownership records of each sampled Form 3, 4 and 5, Schedule 13D
and 13G, and Form 13F.

A filing that gave no records gets a status row with a `reason`. Values stay as filed
text, with no numeric conversion. Elements are matched by local name.
"""

import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from functools import partial
from operator import itemgetter

from sec_filing_data.envelope import EnvelopeError, Submission, document_text, parse_submission
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import build_fetches
from sec_filing_data.tables import read_table, write_table

FORMS_345 = frozenset({"3", "3/A", "4", "4/A", "5", "5/A"})
SCHEDULE_FORMS = frozenset(
    {
        "SCHEDULE 13D",
        "SCHEDULE 13D/A",
        "SCHEDULE 13G",
        "SCHEDULE 13G/A",
        "SC 13D",
        "SC 13D/A",
        "SC 13G",
        "SC 13G/A",
    }
)
FORMS_13F = frozenset({"13F-HR", "13F-HR/A"})
OWNERSHIP_FORMS = FORMS_345 | SCHEDULE_FORMS | FORMS_13F

FORM345_ROOT = "ownershipDocument"
SCHEDULE_ROOT = "edgarSubmission"
FORM13F_ROOT = "informationTable"
FILER_ROLE = "FILER"

NO_DOCUMENT = "no ownership XML document"
NO_SECURITIES = "no securities owned"
NO_RECORDS = "no records in the ownership document"

_DOCTYPE = b"<!DOCTYPE"
_BYTE_ORDER_MARK = b"\xef\xbb\xbf"


@dataclass(frozen=True)
class OwnershipRecord:
    """One row of the `ownership` table, without its accession number and form type."""

    record_kind: str | None
    issuer_cik: str | None
    issuer_name: str | None
    issuer_cusip: str | None
    owner_cik: str | None
    owner_name: str | None
    owner_count: int
    security_title: str | None
    shares: str | None
    shares_kind: str | None
    put_call: str | None
    transaction_date: str | None
    transaction_code: str | None
    acquired_disposed: str | None
    price_per_share: str | None
    shares_after: str | None
    direct_indirect: str | None
    percent_of_class: str | None
    value_usd: str | None


@dataclass(frozen=True)
class _Extraction:
    """What one filing gave: why it gave no records (or None), and the records."""

    reason: str | None
    records: list[OwnershipRecord] = field(default_factory=list)


def local_name(tag: str) -> str:
    """The local name of an ElementTree tag, whatever its namespace."""
    return tag.rpartition("}")[2]


def element_at(parent: ET.Element | None, *path: str) -> ET.Element | None:
    """The element at `path`, each step the first direct child with that local name."""
    for name in path:
        if parent is None:
            return None
        parent = next((kid for kid in parent if local_name(kid.tag) == name), None)
    return parent


def text_at(parent: ET.Element | None, *path: str) -> str | None:
    """The stripped text of the element at `path`, or None when it is missing or empty."""
    element = element_at(parent, *path)
    if element is None:
        return None
    return (element.text or "").strip() or None


def xml_document(raw: bytes, submission: Submission, root: str) -> bytes | None:
    """The text of the first document that parses as XML with a root named `root`, or None.

    One leading UTF-8 byte-order mark is removed, with any whitespace after it, and the text
    that comes back does not hold it. A document is skipped when its text does not start with
    `<`, when it has a DOCTYPE declaration, and when it is not well-formed XML. The root
    matches by local name.
    """
    for document in submission.documents:
        text = document_text(raw, document).removeprefix(_BYTE_ORDER_MARK).lstrip()
        if not text.startswith(b"<") or _DOCTYPE in text:
            continue
        try:
            element = ET.fromstring(text)
        except ET.ParseError:
            continue
        if local_name(element.tag) == root:
            return text
    return None


def run_ownership(layout: Layout) -> int:
    """Write `ownership` and `ownership_status` (one row per sampled filing in OWNERSHIP_FORMS).

    It reads `fetches` from its table, or builds it from the ledger when the table is
    missing. `record_count` is the number of records of the filing, 0 when it gave none.
    """
    sample = sorted(read_table(layout, "sample").to_pylist(), key=itemgetter("draw"))
    fetches = {row["accession_number"]: row for row in _read_fetches(layout)}
    records, statuses = [], []
    for sampled in sample:
        form_type = sampled["form_type"]
        form = _ownership_form(form_type)
        if form is None:
            continue
        accession = sampled["accession_number"]
        extraction = _extract(layout, accession, form, fetches[accession]["outcome"])
        statuses.append(
            {
                "accession_number": accession,
                "form_type": form_type,
                "record_count": len(extraction.records),
                "reason": extraction.reason,
            }
        )
        records.extend(
            {"accession_number": accession, "form_type": form_type} | asdict(record)
            for record in extraction.records
        )
    write_table(layout, "ownership", records)
    write_table(layout, "ownership_status", statuses)
    return 0


def _read_fetches(layout: Layout) -> list[dict]:
    if layout.table("fetches").exists():
        return read_table(layout, "fetches").to_pylist()
    return build_fetches(layout)


def _ownership_form(form_type: str) -> str | None:
    """The form that decides how a filing is read, or None for a filing outside the forms.

    A form type that joins several types with `;` uses its first part, in sorted order,
    that is in OWNERSHIP_FORMS.
    """
    return next((part for part in sorted(form_type.split(";")) if part in OWNERSHIP_FORMS), None)


def _extract(layout: Layout, accession: str, form: str, outcome: str) -> _Extraction:
    """Read the records of one filing. The checks run in the order of the `reason` values."""
    # The parser modules import OwnershipRecord from this module, so they are imported here.
    from sec_filing_data.form13f import parse_form13f_table
    from sec_filing_data.forms345 import no_securities_owned, parse_form345
    from sec_filing_data.schedule13 import parse_schedule13

    if outcome != "ok":
        return _Extraction(outcome)
    raw = layout.submission(accession).read_bytes()
    try:
        submission = parse_submission(raw)
    except EnvelopeError as error:
        return _Extraction(f"submission parse error: {error}")
    if form in FORMS_345:
        root, parse = FORM345_ROOT, parse_form345
    elif form in SCHEDULE_FORMS:
        root, parse = SCHEDULE_ROOT, parse_schedule13
    else:
        # The owner of a 13F holding is the filing manager: the first FILER party.
        filer = next((party for party in submission.parties if party.role == FILER_ROLE), None)
        owner_cik, owner_name = (filer.cik, filer.name) if filer else (None, None)
        root = FORM13F_ROOT
        parse = partial(parse_form13f_table, owner_cik=owner_cik, owner_name=owner_name)
    xml = xml_document(raw, submission, root)
    if xml is None:
        return _Extraction(NO_DOCUMENT)
    records = parse(xml)
    if records:
        return _Extraction(None, records)
    owns_nothing = form in FORMS_345 and no_securities_owned(xml)
    return _Extraction(NO_SECURITIES if owns_nothing else NO_RECORDS)
