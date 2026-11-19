"""The `partners` command: the in-quarter amendment partners of the sampled filings (spec 5.2).

It reads the `index` and `sample` tables and the bytes of the sampled amendments, and writes
`stage4/tables/partners.parquet`. It sends no request, and does not import `requests`.
"""

from collections.abc import Callable
from functools import partial

from sec_filing_data.amendments import (
    AMENDMENT_SUFFIX,
    CANDIDATE_FORMS,
    DATE_ISSUER_OWNER_FORMS,
    PREVIOUS_ACCESSION_FORMS,
    IndexFiling,
    declaring_form,
    index_filings,
    match_date_issuer_owner,
    read_declared,
)
from sec_filing_data.layout import Layout
from sec_filing_data.sample import ARCHIVES
from sec_filing_data.tables import read_table, write_table

RULES = ("original_previous_accession", "original_date_issuer_owner", "candidate_amendment")
REPEATED_STRATUM = "repeated"


def choose_partners(
    index_rows: list[dict],
    sample: list[dict],
    read_sampled: Callable[[str], bytes | None],
) -> list[dict]:
    """The `partners` rows: one for each partner that a rule chooses from a sampled filing.

    `read_sampled` gives the bytes of a sampled filing, or None when they are not on disk. A
    `repeated` sample row starts no rule, and no rule chooses a sampled accession. A partner
    takes its columns from its first index row, and its form type joins its form types, sorted,
    with `;`. Rows sort by accession, then by rule in RULES order, then by sampled accession.
    """
    filings = index_filings(index_rows)
    sampled = {row["accession_number"] for row in sample}
    by_form: dict[str, list[str]] = {}
    for accession, filing in filings.items():
        for form_type in filing.form_types:
            by_form.setdefault(form_type, []).append(accession)
    rows = []
    for row in sample:
        if row["stratum"] == REPEATED_STRATUM:
            continue
        accession, form_type = row["accession_number"], row["form_type"]
        for rule, partner in _chosen(accession, form_type, filings, by_form, read_sampled):
            if partner not in sampled:
                rows.append(_partner_row(filings[partner], rule, accession))
    return sorted(
        rows,
        key=lambda row: (
            row["accession_number"],
            RULES.index(row["rule"]),
            row["sampled_accession"],
        ),
    )


def _chosen(
    accession: str,
    form_type: str,
    filings: dict[str, IndexFiling],
    by_form: dict[str, list[str]],
    read_sampled: Callable[[str], bytes | None],
) -> list[tuple[str, str]]:
    """(rule, partner) for each partner that a rule chooses from one sampled filing.

    Rule 3 starts from a form type in CANDIDATE_FORMS. Rules 1 and 2 start from the
    `declaring_form` of the form type, and read the filing's bytes.
    """
    if form_type in CANDIDATE_FORMS:
        own = filings[accession]
        return [
            ("candidate_amendment", candidate)
            for candidate in by_form.get(form_type + AMENDMENT_SUFFIX, ())
            if filings[candidate].ciks == own.ciks
            and filings[candidate].date_filed >= own.date_filed
        ]
    form = declaring_form(form_type)
    if form not in PREVIOUS_ACCESSION_FORMS and form not in DATE_ISSUER_OWNER_FORMS:
        return []
    raw = read_sampled(accession)
    if raw is None:
        return []
    declared = read_declared(form, raw)
    if form in PREVIOUS_ACCESSION_FORMS:
        previous = declared.previous_accession
        return [("original_previous_accession", previous)] if previous in filings else []
    match = match_date_issuer_owner(declared, form, filings)
    return [] if match.accession is None else [("original_date_issuer_owner", match.accession)]


def _partner_row(filing: IndexFiling, rule: str, sampled_accession: str) -> dict:
    first = filing.first
    return {
        "accession_number": first["accession_number"],
        "form_type": ";".join(sorted(filing.form_types)),
        "cik": first["cik"],
        "company_name": first["company_name"],
        "date_filed": first["date_filed"],
        "filename": first["filename"],
        "url": ARCHIVES + first["filename"],
        "rule": rule,
        "sampled_accession": sampled_accession,
    }


def distinct_partners(partners: list[dict]) -> list[dict]:
    """The first row of each partner accession, in accession order."""
    first: dict[str, dict] = {}
    for row in partners:
        first.setdefault(row["accession_number"], row)
    return [first[accession] for accession in sorted(first)]


def read_partners(layout: Layout) -> list[dict]:
    """The rows of `stage4/tables/partners.parquet`. Raises FileNotFoundError when it is missing."""
    stage4 = layout.stage4_view
    path = stage4.table("partners")
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run partners first")
    return read_table(stage4, "partners").to_pylist()


def run_partners(layout: Layout) -> list[dict]:
    """Write `partners` under `stage4/tables/`, from the `index` and `sample` tables and the
    sampled bytes, and give its rows."""
    rows = choose_partners(
        read_table(layout, "index").to_pylist(),
        read_table(layout, "sample").to_pylist(),
        partial(_sampled_bytes, layout),
    )
    write_table(layout.stage4_view, "partners", rows)
    return rows


def _sampled_bytes(layout: Layout, accession: str) -> bytes | None:
    path = layout.submission(accession)
    return path.read_bytes() if path.exists() else None
