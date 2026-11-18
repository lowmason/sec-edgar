"""O2: the sample of filings, drawn from the `index` table."""

import random
from dataclasses import dataclass

from sec_filing_data.layout import Layout
from sec_filing_data.tables import read_table, write_table

QUOTA_FORMS = ("10-K", "10-Q", "3", "4", "5", "SCHEDULE 13D", "SCHEDULE 13G", "13F-HR")
STRATA = ("quota", "repeated", "uniform")

_ARCHIVES = "https://www.sec.gov/Archives/"


@dataclass
class _Filing:
    """One accession: its first index row, and every form type its rows carry."""

    first: dict
    form_types: set[str]


def draw_sample(
    index_rows: list[dict], *, size: int = 500, quota: int = 20, seed: int = 20260930
) -> list[dict]:
    """Return the rows of `sample`, one per accession, in draw order.

    Strata, in order: `quota` (up to `quota` accessions for each of QUOTA_FORMS), `repeated`
    (every accession whose rows carry several form types), then `uniform` (the rest, up to
    `size` in all). An accession drawn in one step is not a candidate in any later step.
    Each draw samples from accessions sorted by accession number, so the input order does
    not matter.
    """
    filings = _group_by_accession(index_rows)
    accessions = sorted(filings)
    rng = random.Random(seed)
    chosen: list[tuple[str, str, str]] = []  # (stratum, form type, accession)
    drawn: set[str] = set()

    for form_type in QUOTA_FORMS:
        candidates = [
            accession
            for accession in accessions
            if accession not in drawn and form_type in filings[accession].form_types
        ]
        picked = rng.sample(candidates, min(quota, len(candidates)))
        chosen.extend(("quota", form_type, accession) for accession in picked)
        drawn.update(picked)

    for accession in accessions:
        form_types = filings[accession].form_types
        if accession not in drawn and len(form_types) > 1:
            chosen.append(("repeated", ";".join(sorted(form_types)), accession))
            drawn.add(accession)

    rest = [accession for accession in accessions if accession not in drawn]
    picked = rng.sample(rest, max(0, min(size - len(chosen), len(rest))))
    chosen.extend(
        ("uniform", filings[accession].first["form_type"], accession) for accession in picked
    )

    return [
        _sample_row(draw, stratum, form_type, filings[accession].first)
        for draw, (stratum, form_type, accession) in enumerate(chosen, start=1)
    ]


def run_sample(layout: Layout) -> list[dict]:
    """Write the `sample` table, drawn from the `index` table, and return its rows."""
    rows = draw_sample(read_table(layout, "index").to_pylist())
    write_table(layout, "sample", rows)
    return rows


def _group_by_accession(index_rows: list[dict]) -> dict[str, _Filing]:
    filings: dict[str, _Filing] = {}
    for row in index_rows:
        filing = filings.setdefault(row["accession_number"], _Filing(row, set()))
        if row["line_number"] < filing.first["line_number"]:
            filing.first = row
        filing.form_types.add(row["form_type"])
    return filings


def _sample_row(draw: int, stratum: str, form_type: str, first: dict) -> dict:
    return {
        "draw": draw,
        "stratum": stratum,
        "accession_number": first["accession_number"],
        "form_type": form_type,
        "cik": first["cik"],
        "company_name": first["company_name"],
        "date_filed": first["date_filed"],
        "filename": first["filename"],
        "url": _ARCHIVES + first["filename"],
    }
