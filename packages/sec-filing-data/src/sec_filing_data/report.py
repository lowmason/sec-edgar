"""The `report` command: a Markdown summary of one output root, its cost and its platform checks.

The report sends no request and writes nothing. A table that an earlier step has not
written yet makes its section say so.
"""

import json
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from operator import itemgetter

from sec_filing_data.layout import Layout
from sec_filing_data.ledger import FETCH_OUTCOMES, ledger_usage, read_ledger
from sec_filing_data.sample import QUOTA_FORMS, STRATA
from sec_filing_data.tables import read_table

IDEA_XBRL = "IDEA: XBRL DOCUMENT"
NULL_CHECKED = (
    "submission_type",
    "acceptance_datetime",
    "filed_as_of_date",
    "public_document_count",
)
V10_CASES = {
    "equal": "public_document_count equals document_count",
    "minus": "public_document_count equals document_count minus those documents",
    "neither": "neither",
}


@dataclass(frozen=True)
class _Root:
    """The tables of one root. A table that is not written yet is None."""

    layout: Layout
    index_rows: int | None
    sample: list[dict] | None
    fetches: list[dict] | None
    filings: list[dict] | None
    parties: list[dict] | None
    documents: list[dict] | None

    @classmethod
    def load(cls, layout: Layout) -> _Root:
        def rows(name: str) -> list[dict] | None:
            if not layout.table(name).exists():
                return None
            return read_table(layout, name).to_pylist()

        sample = rows("sample")
        return cls(
            layout=layout,
            index_rows=(
                read_table(layout, "index").num_rows if layout.table("index").exists() else None
            ),
            sample=sorted(sample, key=itemgetter("draw")) if sample is not None else None,
            fetches=rows("fetches"),
            filings=rows("filings"),
            parties=rows("parties"),
            documents=rows("documents"),
        )

    @property
    def parsed(self) -> list[dict]:
        """The filings whose bytes were fetched and parsed."""
        return [
            filing
            for filing in self.filings or []
            if filing["outcome"] == "ok" and filing["parse_error"] is None
        ]


def run_report(layout: Layout) -> str:
    root = _Root.load(layout)
    lines = ["# sec-filing-data report"]
    for title, section in _SECTIONS:
        lines += ["", f"## {title}", *section(root)]
    return "\n".join(lines) + "\n"


def _no_table(name: str) -> str:
    return f"no `{name}` table yet"


def _counted(label: str, accessions: list[str]) -> list[str]:
    """A count line, then one sub-line per accession."""
    return [f"- {label}: {len(accessions)}", *(f"  - {accession}" for accession in accessions)]


def _text(value: object) -> str:
    return "null" if value is None else str(value)


def _index(root: _Root) -> list[str]:
    if root.index_rows is None:
        return [f"- {_no_table('index')}"]
    return [f"- index rows: {root.index_rows}"]


def _sample(root: _Root) -> list[str]:
    if root.sample is None:
        return [f"- {_no_table('sample')}"]
    strata = Counter(row["stratum"] for row in root.sample)
    quota = Counter(row["form_type"] for row in root.sample if row["stratum"] == "quota")
    return [
        f"- sampled filings: {len(root.sample)}",
        *(f"- {stratum}: {strata[stratum]}" for stratum in STRATA),
        *(f"- quota {form}: {quota[form]}" for form in QUOTA_FORMS),
    ]


def _fetch_outcomes(root: _Root) -> list[str]:
    if root.fetches is None:
        return [f"- {_no_table('fetches')}"]
    outcomes = Counter(row["outcome"] for row in root.fetches)
    return [f"- {outcome}: {outcomes[outcome]}" for outcome in FETCH_OUTCOMES if outcomes[outcome]]


def _cost(root: _Root) -> list[str]:
    usage = ledger_usage(root.layout.ledger)
    lines = [f"- requests: {usage.requests}", f"- wire bytes: {usage.wire_bytes}"]
    if root.fetches is None:
        return [*lines, f"- decoded bytes: {_no_table('fetches')}"]
    decoded = sum(row["body_bytes"] or 0 for row in root.fetches if row["outcome"] == "ok")
    return [*lines, f"- decoded bytes: {decoded}"]


def _parse_errors(root: _Root) -> list[str]:
    if root.filings is None:
        return [f"- {_no_table('filings')}"]
    errors = [filing for filing in root.filings if filing["parse_error"] is not None]
    return [
        f"- parse errors: {len(errors)}",
        *(f"  - {filing['accession_number']}: {filing['parse_error']}" for filing in errors),
    ]


def _header_checks(root: _Root) -> list[str]:
    if root.filings is None:
        return [f"- {_no_table('filings')}"]
    parsed = root.parsed
    among = f"among {len(parsed)} parsed filings"
    lines = []
    if root.parties is None:
        lines.append(f"- filings with no party: {_no_table('parties')}")
    else:
        with_party = {party["accession_number"] for party in root.parties}
        lines += _counted(
            f"filings with no party, {among}",
            [f["accession_number"] for f in parsed if f["accession_number"] not in with_party],
        )
    for column in NULL_CHECKED:
        lines += _counted(
            f"filings with a null {column}, {among}",
            [f["accession_number"] for f in parsed if f[column] is None],
        )
    return lines


def _wall_time(root: _Root) -> list[str]:
    path = root.layout.runs
    records = []
    if path.exists():
        with path.open(encoding="utf-8") as runs:
            records = [json.loads(line) for line in runs if line.strip()]
    if not records:
        return ["- no steps recorded yet"]
    seconds: dict[str, float] = {}
    for record in records:
        seconds[record["step"]] = seconds.get(record["step"], 0.0) + record["seconds"]
    return [
        *(f"- {step}: {total:.3f} s" for step, total in seconds.items()),
        f"- total: {sum(seconds.values()):.3f} s",
    ]


def _disk_use(root: _Root) -> list[str]:
    files = (path for path in root.layout.root.rglob("*") if path.is_file())
    return [f"- disk use: {sum(path.stat().st_size for path in files)} bytes"]


def _platform_checks(root: _Root) -> list[str]:
    """The D5 checks V3, V5, V6, V7, V9 and V10. Each line starts with its label."""
    lines = _v3(root)
    if root.sample is None or root.filings is None:
        name = "sample" if root.sample is None else "filings"
        return lines + [
            f"- {label}: {_no_table(name)}" for label in ("V5", "V6", "V7", "V9", "V10")
        ]
    return lines + _v5(root) + _v6(root) + _v7(root) + _v9(root) + _v10(root)


def _v3(root: _Root) -> list[str]:
    """Response headers of the `ok` submission fetches."""
    if root.sample is None:
        return [f"- V3: {_no_table('sample')}"]
    sampled = {row["accession_number"] for row in root.sample}
    responses = [
        record
        for record in read_ledger(root.layout.ledger)
        if record["event"] == "response" and record["outcome"] == "ok" and record["key"] in sampled
    ]
    encodings = Counter(record["content_encoding"] or "none" for record in responses)
    return [
        f"- V3 ok responses: {len(responses)}",
        *(f"  - Content-Encoding {name}: {count}" for name, count in sorted(encodings.items())),
        f"  - with ETag: {_count(responses, 'etag')}",
        f"  - with Last-Modified: {_count(responses, 'last_modified')}",
    ]


def _count(records: Iterable[dict], field: str) -> int:
    return sum(1 for record in records if record[field])


def _v5(root: _Root) -> list[str]:
    """Each `repeated` filing: its sampled form types against its header."""
    filings = {filing["accession_number"]: filing for filing in root.filings}
    repeated = [row for row in root.sample if row["stratum"] == "repeated"]
    lines = [f"- V5 repeated filings: {len(repeated)}"]
    for row in repeated:
        filing = filings.get(row["accession_number"], {})
        lines.append(
            f"  - {row['accession_number']}: form_type {row['form_type']},"
            f" submission_type {_text(filing.get('submission_type'))},"
            f" document_count {_text(filing.get('document_count'))}"
        )
    return lines


def _v6(root: _Root) -> list[str]:
    def later(filing: dict) -> bool:
        changed, filed = filing["date_as_of_change"], filing["filed_as_of_date"]
        return _is_date(changed) and _is_date(filed) and changed > filed

    return _counted(
        "V6 filings whose date_as_of_change is later than filed_as_of_date",
        [filing["accession_number"] for filing in root.parsed if later(filing)],
    )


def _is_date(value: str | None) -> bool:
    """A filed `YYYYMMDD` date, which compares correctly as text."""
    return value is not None and len(value) == 8 and value.isascii() and value.isdigit()


def _v7(root: _Root) -> list[str]:
    return _counted(
        "V7 filings with private_to_public",
        [filing["accession_number"] for filing in root.parsed if filing["private_to_public"]],
    )


def _v9(root: _Root) -> list[str]:
    return _counted(
        "V9 filings with a null acceptance_datetime",
        [
            filing["accession_number"]
            for filing in root.parsed
            if filing["acceptance_datetime"] is None
        ],
    )


def _v10(root: _Root) -> list[str]:
    """`public_document_count` against `document_count` for filings with XBRL documents."""
    if root.documents is None:
        return [f"- V10: {_no_table('documents')}"]
    xbrl = Counter(
        document["accession_number"]
        for document in root.documents
        if document["description"] == IDEA_XBRL
    )
    cases: Counter[str] = Counter()
    holding = [filing for filing in root.parsed if xbrl[filing["accession_number"]]]
    for filing in holding:
        public = _filed_count(filing["public_document_count"])
        if public == filing["document_count"]:
            cases["equal"] += 1
        elif public == filing["document_count"] - xbrl[filing["accession_number"]]:
            cases["minus"] += 1
        else:
            cases["neither"] += 1
    return [
        f"- V10 filings with documents described {IDEA_XBRL}: {len(holding)}",
        *(f"  - {label}: {cases[case]}" for case, label in V10_CASES.items()),
    ]


def _filed_count(value: str | None) -> int | None:
    """A count filed as decimal text, or None when the text is not one."""
    return int(value) if value is not None and value.isascii() and value.isdigit() else None


_SECTIONS: tuple[tuple[str, Callable[[_Root], list[str]]], ...] = (
    ("Index", _index),
    ("Sample", _sample),
    ("Fetch outcomes", _fetch_outcomes),
    ("Cost", _cost),
    ("Envelope parse errors", _parse_errors),
    ("Header checks", _header_checks),
    ("Wall time", _wall_time),
    ("Disk use", _disk_use),
    ("Platform checks", _platform_checks),
)
