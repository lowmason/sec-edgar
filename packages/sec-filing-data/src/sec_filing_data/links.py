"""The `links` table: each held amendment and the original that its bytes declare (spec 5.5).

A held filing is an `ok` row of `tables/filings` (held in `sample`) or of
`stage4/tables/filings` (held in `partner`). An amendment is a held filing whose form type has
a part that ends in `/A`. Its row names the one original that the rule of its form finds (C5,
C7), or the problem that kept the rule from one. `partner_tables.run_partner_tables` writes
the table. This module does not import `requests`.
"""

from dataclasses import dataclass
from datetime import datetime

from sec_filing_data.amendments import (
    DATE_ISSUER_OWNER_FORMS,
    FILER_PERIOD_FORMS,
    PREVIOUS_ACCESSION_FORMS,
    Declared,
    IndexFiling,
    Match,
    as_cik,
    declaring_form,
    index_filings,
    is_amendment,
    match_date_issuer_owner,
    read_declared,
)
from sec_filing_data.ownership import FILER_ROLE
from sec_filing_data.provenance import record_provenance

LINK_RULES = ("previous_accession", "original_date_issuer_owner", "filer_period", "none_declared")
PREVIOUS_ACCESSION, DATE_ISSUER_OWNER, FILER_PERIOD, NONE_DECLARED = LINK_RULES

# Where a held filing is held: in the sample (`tables/`) or among the partners (`stage4/`).
HELD_IN_SAMPLE = "sample"
HELD_IN_PARTNER = "partner"

# The form type of the original of a 13F-HR/A.
ORIGINAL_13F_FORM = "13F-HR"
NOT_IN_INDEX = "not in the 2026Q3 index"
NO_FILER = "no FILER party"


@dataclass(frozen=True)
class HeldFiling:
    """A held filing, as a `links` row compares it. `filer_cik` is the CIK of the first FILER
    row of its `parties`, in table order, or None."""

    accession_number: str
    form_type: str
    held_in: str
    accepted_at: datetime | None
    period_of_report: str | None
    filer_cik: int | None


@dataclass(frozen=True)
class LinkContext:
    """The 2026Q3 index by accession, and the held filings by accession."""

    index: dict[str, IndexFiling]
    held: dict[str, HeldFiling]


def link_context(
    index_rows: list[dict], filings: dict[str, list[dict]], parties: dict[str, list[dict]]
) -> LinkContext:
    """The context of the `links` rows, from the `index` rows and the `filings` and `parties`
    rows of each place that holds filings (`sample` and `partner`, the keys of both dicts).

    Only the `ok` filings are held.
    """
    held = {}
    for held_in, rows in filings.items():
        filers = _first_filers(parties[held_in])
        for row in rows:
            if row["outcome"] != "ok":
                continue
            accession = row["accession_number"]
            held[accession] = HeldFiling(
                accession_number=accession,
                form_type=row["form_type"],
                held_in=held_in,
                accepted_at=row["accepted_at"],
                period_of_report=row["period_of_report"],
                filer_cik=filers.get(accession),
            )
    return LinkContext(index_filings(index_rows), held)


def _first_filers(parties: list[dict]) -> dict[str, int | None]:
    """The CIK of the first FILER row of each accession, in table order."""
    filers: dict[str, int | None] = {}
    for row in parties:
        if row["role"] == FILER_ROLE:
            filers.setdefault(row["accession_number"], as_cik(row["cik"]))
    return filers


def amendment_filings(filings: list[dict]) -> list[dict]:
    """The `ok` rows of `filings` whose form type has a part that ends in `/A`, in their order."""
    return [row for row in filings if row["outcome"] == "ok" and is_amendment(row["form_type"])]


def link_row(filing: dict, held_in: str, raw: bytes, context: LinkContext) -> dict:
    """The `links` row of one held amendment, from its `filings` row and its bytes.

    The declared values come from the bytes, read by the `declaring_form` of the form type.
    The rule of that form runs only when the bytes give the value that the rule reads, else
    the rule is `none_declared`. A held original that was accepted after the amendment is no
    link (spec 5.5).
    """
    form = declaring_form(filing["form_type"])
    declared = Declared() if form is None else read_declared(form, raw)
    rule = _link_rule(form, declared)
    match = _original(rule, form, declared, context)
    original, problem = match.accession, match.problem
    held = None if original is None else context.held.get(original)
    if held is not None and _accepted_after(held.accepted_at, filing["accepted_at"]):
        problem = (
            f"{original} was accepted at {held.accepted_at.isoformat()},"
            f" after this amendment at {filing['accepted_at'].isoformat()}"
        )
        original, held = None, None
    return {
        "accession_number": filing["accession_number"],
        "form_type": filing["form_type"],
        "held_in": held_in,
        "link_rule": rule,
        "declared_previous_accession": declared.previous_accession,
        "declared_original_date": declared.original_date,
        "declared_period": declared.period,
        "amendment_number": declared.amendment_number,
        "amendment_type": declared.amendment_type,
        "original_accession": original,
        "original_held_in": None if held is None else held.held_in,
        "link_problem": problem,
        "source_document": declared.source_document,
        **record_provenance(filing),
    }


def _link_rule(form: str | None, declared: Declared) -> str:
    """The rule of `form` (C5) when the bytes declare the value that it reads."""
    if form in PREVIOUS_ACCESSION_FORMS and declared.previous_accession is not None:
        return PREVIOUS_ACCESSION
    if form in DATE_ISSUER_OWNER_FORMS and declared.original_date is not None:
        return DATE_ISSUER_OWNER
    if form in FILER_PERIOD_FORMS and declared.period is not None:
        return FILER_PERIOD
    return NONE_DECLARED


def _original(rule: str, form: str | None, declared: Declared, context: LinkContext) -> Match:
    """The one original that `rule` finds, or None with the problem (C7)."""
    if rule == PREVIOUS_ACCESSION:
        previous = declared.previous_accession
        return Match(previous, None) if previous in context.index else Match(None, NOT_IN_INDEX)
    if rule == DATE_ISSUER_OWNER:
        return match_date_issuer_owner(declared, form, context.index)
    if rule == FILER_PERIOD:
        return _held_13f_original(declared, context.held)
    return Match(None, declared.problem)


def _held_13f_original(declared: Declared, held: dict[str, HeldFiling]) -> Match:
    """The one held 13F-HR of the amendment's filer (the first FILER party of its header) with
    the same `CONFORMED PERIOD OF REPORT`. Periods compare as header text (`YYYYMMDD`)."""
    if declared.filer_cik is None:
        return Match(None, NO_FILER)
    filer = as_cik(declared.filer_cik)
    if filer is None:
        return Match(None, f"CIK {declared.filer_cik} is not a number")
    matches = sorted(
        filing.accession_number
        for filing in held.values()
        if filing.form_type == ORIGINAL_13F_FORM
        and filing.filer_cik == filer
        and filing.period_of_report == declared.period
    )
    if not matches:
        return Match(None, f"no held 13F-HR of filer {filer} for period {declared.period}")
    if len(matches) > 1:
        return Match(None, f"{len(matches)} held 13F-HR matches: {', '.join(matches)}")
    return Match(matches[0], None)


def _accepted_after(original: datetime | None, amendment: datetime | None) -> bool:
    """True when both times are known and the original's is after the amendment's."""
    return original is not None and amendment is not None and original > amendment
