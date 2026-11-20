"""The values that an amendment declares about its original, and the index grouped by accession.

Values stay as filed text. Only a comparison converts them: a CIK with `as_cik` and a date
with `as_date`, because the index holds `cik` as an int and `date_filed` as a date. This module
does not import `requests`.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from sec_filing_data.envelope import EnvelopeError, Submission, parse_submission
from sec_filing_data.ownership import FILER_ROLE, local_name, text_at, xml_document
from sec_filing_data.sample import group_by_accession
from sec_filing_data.submissions import HEADER_FIELDS

# The forms that declare their original (C5), by the rule that reads them.
SCHEDULE_AMENDMENT_FORMS = frozenset({"SCHEDULE 13D/A", "SCHEDULE 13G/A", "SC 13D/A", "SC 13G/A"})
FORM_D_AMENDMENT = "D/A"
PREVIOUS_ACCESSION_FORMS = SCHEDULE_AMENDMENT_FORMS | {FORM_D_AMENDMENT}
DATE_ISSUER_OWNER_FORMS = frozenset({"3/A", "4/A", "5/A"})
FILER_PERIOD_FORMS = frozenset({"13F-HR/A"})
DECLARING_FORMS = PREVIOUS_ACCESSION_FORMS | DATE_ISSUER_OWNER_FORMS | FILER_PERIOD_FORMS

# The sampled forms whose amendments are partner candidates (spec 5.2, rule 3).
CANDIDATE_FORMS = ("SCHEDULE 13D", "SCHEDULE 13G", "SC 13D", "SC 13G", "D", "3", "4", "5", "13F-HR")

AMENDMENT_SUFFIX = "/A"
SUBMISSION_ROOT = "edgarSubmission"
OWNERSHIP_ROOT = "ownershipDocument"

_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


@dataclass(frozen=True)
class Declared:
    """What an amendment's bytes declare, as filed text. A value that is not declared is None.

    `source_document` is the filename of the XML document that the values come from. `problem`
    is `submission parse error: <message>` for bytes that do not parse, else None.
    """

    previous_accession: str | None = None
    original_date: str | None = None
    issuer_cik: str | None = None
    owner_ciks: tuple[str, ...] = ()
    period: str | None = None
    amendment_number: str | None = None
    amendment_type: str | None = None
    filer_cik: str | None = None
    source_document: str | None = None
    problem: str | None = None


@dataclass(frozen=True)
class IndexFiling:
    """One accession of the index: its first row, its form types, its date filed and its CIKs."""

    first: dict
    form_types: frozenset[str]
    date_filed: date
    ciks: frozenset[int]


@dataclass(frozen=True)
class Match:
    """The one accession that a rule found, or None with the problem that kept it from one."""

    accession: str | None
    problem: str | None


def is_amendment(form_type: str) -> bool:
    """True when a part of the form type (parts are joined with `;`) ends in `/A`."""
    return any(part.endswith(AMENDMENT_SUFFIX) for part in form_type.split(";"))


def declaring_form(form_type: str) -> str | None:
    """The form that decides how a filing declares its original, or None.

    A form type that joins several types with `;` uses its first part, in sorted order, that
    is in DECLARING_FORMS, as `ownership.ownership_form` does.
    """
    return next((part for part in sorted(form_type.split(";")) if part in DECLARING_FORMS), None)


def as_cik(text: str | None) -> int | None:
    """A CIK as an int, from text of ASCII digits only (zero-padded or not); else None."""
    if text is None or not (text.isascii() and text.isdigit()):
        return None
    return int(text)


def as_date(text: str | None) -> date | None:
    """A date from `YYYY-MM-DD` text that names a real date; else None."""
    if text is None or _DATE.fullmatch(text) is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def read_declared(form: str, raw: bytes) -> Declared:
    """The values that a filing of `form` declares, read by the element paths of its form.

    `filer_cik` is the CIK of the first FILER party of the header, for any form. A form outside
    DECLARING_FORMS gives nothing else. A 13F-HR/A takes `period` from the header's
    `CONFORMED PERIOD OF REPORT`, never from its XML.
    """
    try:
        submission = parse_submission(raw)
    except EnvelopeError as error:
        return Declared(problem=f"submission parse error: {error}")
    filer = next((party for party in submission.parties if party.role == FILER_ROLE), None)
    values: dict = {"filer_cik": filer.cik if filer else None}
    if form in FILER_PERIOD_FORMS:
        values["period"] = submission.field(HEADER_FIELDS["period_of_report"])
    reader = _READERS.get(form)
    if reader is not None:
        values |= _xml_values(raw, submission, *reader)
    return Declared(**values)


def _xml_values(
    raw: bytes, submission: Submission, root: str, read: Callable[[ET.Element], dict]
) -> dict:
    document = xml_document(raw, submission, root)
    if document is None:
        return {}
    return read(ET.fromstring(document.text)) | {"source_document": document.filename}


def _schedule_values(root: ET.Element) -> dict:
    return {
        "previous_accession": text_at(root, "headerData", "previousAccessionNumber"),
        "amendment_number": text_at(root, "formData", "coverPageHeader", "amendmentNo"),
    }


def _form_d_values(root: ET.Element) -> dict:
    return {
        "previous_accession": text_at(
            root, "offeringData", "typeOfFiling", "newOrAmendment", "previousAccessionNumber"
        )
    }


def _form345_values(root: ET.Element) -> dict:
    owners = (child for child in root if local_name(child.tag) == "reportingOwner")
    owner_ciks = (text_at(owner, "reportingOwnerId", "rptOwnerCik") for owner in owners)
    return {
        "original_date": text_at(root, "dateOfOriginalSubmission"),
        "issuer_cik": text_at(root, "issuer", "issuerCik"),
        "owner_ciks": tuple(cik for cik in owner_ciks if cik is not None),
    }


def _form13f_values(root: ET.Element) -> dict:
    return {
        "amendment_number": text_at(root, "formData", "coverPage", "amendmentNo"),
        "amendment_type": text_at(
            root, "formData", "coverPage", "amendmentInfo", "amendmentType"
        ),
    }


# The XML root and the reader of each form in DECLARING_FORMS.
_READERS: dict[str, tuple[str, Callable[[ET.Element], dict]]] = (
    dict.fromkeys(SCHEDULE_AMENDMENT_FORMS, (SUBMISSION_ROOT, _schedule_values))
    | {FORM_D_AMENDMENT: (SUBMISSION_ROOT, _form_d_values)}
    | dict.fromkeys(DATE_ISSUER_OWNER_FORMS, (OWNERSHIP_ROOT, _form345_values))
    | dict.fromkeys(FILER_PERIOD_FORMS, (SUBMISSION_ROOT, _form13f_values))
)


def index_filings(index_rows: list[dict]) -> dict[str, IndexFiling]:
    """Each accession of the index rows, grouped by `sample.group_by_accession`.

    Its CIKs are the set of `cik` values over its rows, and its date filed is that of its first
    row.
    """
    ciks: dict[str, set[int]] = {}
    for row in index_rows:
        ciks.setdefault(row["accession_number"], set()).add(row["cik"])
    return {
        accession: IndexFiling(
            first=filing.first,
            form_types=frozenset(filing.form_types),
            date_filed=filing.first["date_filed"],
            ciks=frozenset(ciks[accession]),
        )
        for accession, filing in group_by_accession(index_rows).items()
    }


def match_date_issuer_owner(
    declared: Declared, form: str, filings: dict[str, IndexFiling]
) -> Match:
    """The one index accession of the base form of `form` (`4` for `4/A`) that was filed on the
    declared `dateOfOriginalSubmission` and that the index lists under exactly the declared
    issuer and owner CIKs.

    CIKs compare as ints and dates as dates. The checks run in the order of their problems.
    """
    filed = as_date(declared.original_date)
    if filed is None:
        return Match(
            None, f"dateOfOriginalSubmission {declared.original_date} is not a YYYY-MM-DD date"
        )
    if declared.issuer_cik is None or not declared.owner_ciks:
        return Match(None, "no issuerCik or rptOwnerCik")
    ciks = set()
    for text in (declared.issuer_cik, *declared.owner_ciks):
        cik = as_cik(text)
        if cik is None:
            return Match(None, f"CIK {text} is not a number")
        ciks.add(cik)
    base_form = form.removesuffix(AMENDMENT_SUFFIX)
    matches = sorted(
        accession
        for accession, filing in filings.items()
        if base_form in filing.form_types and filing.date_filed == filed and filing.ciks == ciks
    )
    if not matches:
        listed = ", ".join(str(cik) for cik in sorted(ciks))
        return Match(None, f"no index match for {filed.isoformat()} and CIKs {listed}")
    if len(matches) > 1:
        return Match(None, f"{len(matches)} index matches: {', '.join(matches)}")
    return Match(matches[0], None)
