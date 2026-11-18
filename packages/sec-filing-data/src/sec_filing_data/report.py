"""The `report` command: a Markdown summary of one output root: its cost, its platform checks,
its filing times, its sources and its refetches.

The report sends no request and writes nothing. A table that an earlier step has not
written yet makes its section say so.
"""

import json
import statistics
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from operator import itemgetter

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sec_filing_data.layout import Layout
from sec_filing_data.ledger import FETCH_OUTCOMES, STAGE2_LIMITS, ledger_usage, read_ledger
from sec_filing_data.sample import QUOTA_FORMS, STRATA
from sec_filing_data.tables import read_table
from sec_filing_data.times import PUBLIC_RULES
from sec_filing_data.xbrl import INSTANCE_TYPE, SEC_EXTRACTED_SUFFIX

IDEA_XBRL = "IDEA: XBRL DOCUMENT"
NULL_CHECKED = (
    "submission_type",
    "acceptance_datetime",
    "filed_as_of_date",
    "public_document_count",
)
INSTANCE_KINDS = (INSTANCE_TYPE, f"*{SEC_EXTRACTED_SUFFIX}")
LONG_GAP = timedelta(hours=1)
RECORDS_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership")
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
    facts_status: list[dict] | None
    ownership: list[dict] | None
    ownership_status: list[dict] | None
    refetches: list[dict] | None

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
            facts_status=rows("facts_status"),
            ownership=rows("ownership"),
            ownership_status=rows("ownership_status"),
            refetches=rows("refetches"),
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


def _facts(root: _Root) -> list[str]:
    """The filings in the fact forms, their fact rows, and why some gave none."""
    if root.facts_status is None:
        return [f"- {_no_table('facts_status')}"]
    with_facts = [status for status in root.facts_status if status["reason"] is None]
    kinds = Counter(_instance_kind(status["source_document"]) for status in with_facts)
    reasons = Counter(
        status["reason"] for status in root.facts_status if status["reason"] is not None
    )
    return [
        f"- filings in the fact forms: {len(root.facts_status)}",
        f"- fact rows: {sum(status['fact_count'] for status in with_facts)}",
        f"- filings with facts: {len(with_facts)}",
        *(f"  - {kind}: {kinds[kind]}" for kind in INSTANCE_KINDS),
        f"- filings with no facts: {len(root.facts_status) - len(with_facts)}",
        *(f"  - {reason}: {count}" for reason, count in sorted(reasons.items())),
    ]


def _instance_kind(source_document: str | None) -> str:
    """`*_htm.xml` for an SEC-extracted instance, else the `EX-101.INS` the filer sent."""
    if source_document is not None and source_document.endswith(SEC_EXTRACTED_SUFFIX):
        return INSTANCE_KINDS[1]
    return INSTANCE_KINDS[0]


def _ownership(root: _Root) -> list[str]:
    """The filings in the ownership forms, their records per kind, and why some gave none."""
    for name, rows in (("ownership_status", root.ownership_status), ("ownership", root.ownership)):
        if rows is None:
            return [f"- {_no_table(name)}"]
    kinds = Counter(row["record_kind"] for row in root.ownership)
    reasons = Counter(
        status["reason"] for status in root.ownership_status if status["reason"] is not None
    )
    with_records = sum(1 for status in root.ownership_status if status["reason"] is None)
    return [
        f"- filings in the ownership forms: {len(root.ownership_status)}",
        f"- records: {len(root.ownership)}",
        *(f"  - {kind}: {count}" for kind, count in sorted(kinds.items())),
        f"- filings with records: {with_records}",
        f"- filings with no records: {len(root.ownership_status) - with_records}",
        *(f"  - {reason}: {count}" for reason, count in sorted(reasons.items())),
    ]


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


def _times(root: _Root) -> list[str]:
    """The `public_rule` counts, and the gap from `public_at` to `last_modified_at`.

    Every line is over the parsed `ok` filings. A gap is in whole seconds and is negative
    when the filing was last modified before the earliest time it could be public.
    """
    if root.filings is None:
        return [f"- {_no_table('filings')}"]
    parsed = root.parsed
    rules = Counter(filing["public_rule"] for filing in parsed)
    gaps = {
        filing["accession_number"]: _seconds(filing["last_modified_at"] - filing["public_at"])
        for filing in parsed
        if filing["public_at"] is not None and filing["last_modified_at"] is not None
    }
    unmodified = sum(1 for filing in parsed if filing["last_modified_at"] is None)
    return [
        *(f"- {rule}: {rules[rule]}" for rule in PUBLIC_RULES),
        f"- filings with a null last_modified_at: {unmodified}",
        _gap_summary(list(gaps.values())),
        *_gap_lines(
            "filings with a gap above 1 hour",
            {accession: gap for accession, gap in gaps.items() if gap > _seconds(LONG_GAP)},
        ),
        *_counted(
            "filings with public_at after last_modified_at",
            [accession for accession, gap in gaps.items() if gap < 0],
        ),
        *_counted(
            "filings with public_at before accepted_at",
            [
                filing["accession_number"]
                for filing in parsed
                if filing["public_at"] is not None
                and filing["accepted_at"] is not None
                and filing["public_at"] < filing["accepted_at"]
            ],
        ),
    ]


def _seconds(delta: timedelta) -> int:
    return int(delta.total_seconds())


def _gap_summary(gaps: list[int]) -> str:
    label = "gap from public_at to last_modified_at"
    if not gaps:
        return f"- {label}: no filing has both times"
    return (
        f"- {label}: least {min(gaps)} s, median {statistics.median_low(gaps)} s,"
        f" largest {max(gaps)} s"
    )


def _gap_lines(label: str, gaps: dict[str, int]) -> list[str]:
    return [
        f"- {label}: {len(gaps)}",
        *(f"  - {accession}: {gap} s" for accession, gap in gaps.items()),
    ]


def _provenance(root: _Root) -> list[str]:
    """Per records table, the rows without a source and the rows of `ok` filings without times.

    Each table is read for the columns it counts and no more: `index`, `facts` and
    `ownership` have too many rows to hold as Python values.
    """
    ok_accessions = (
        None
        if root.filings is None
        else [f["accession_number"] for f in root.filings if f["outcome"] == "ok"]
    )
    lines = [_provenance_line(root.layout, name, ok_accessions) for name in RECORDS_TABLES]
    if not root.layout.table("index").exists():
        return [*lines, f"- index rows with filing times: {_no_table('index')}"]
    with_times = _columns(root.layout, "index", ["fetched_at"])["fetched_at"]
    return [*lines, f"- index rows with filing times: {len(with_times) - with_times.null_count}"]


def _provenance_line(layout: Layout, name: str, ok_accessions: list[str] | None) -> str:
    if not layout.table(name).exists():
        return f"- {name}: {_no_table(name)}"
    checksum = "sha256" if name == "filings" else "source_sha256"
    table = _columns(
        layout, name, ["accession_number", "source_url", checksum, "accepted_at", "fetched_at"]
    )
    no_source = pc.or_(pc.is_null(table["source_url"]), pc.is_null(table[checksum]))
    count = f"{table.filter(no_source).num_rows} rows with a null source_url or source_sha256"
    if ok_accessions is None:
        return f"- {name}: {count}, rows of ok filings: {_no_table('filings')}"
    ok = pc.is_in(table["accession_number"], value_set=pa.array(ok_accessions, pa.string()))
    no_time = pc.or_(pc.is_null(table["accepted_at"]), pc.is_null(table["fetched_at"]))
    no_times = table.filter(pc.and_(ok, no_time)).num_rows
    return f"- {name}: {count}, {no_times} rows of ok filings with a null accepted_at or fetched_at"


def _columns(layout: Layout, name: str, columns: list[str]) -> pa.Table:
    return pq.read_table(layout.table(name), columns=columns)


def _refetches(root: _Root) -> list[str]:
    usage = ledger_usage(root.layout.stage2_ledger)
    rows = (
        [f"- {_no_table('refetches')}"]
        if root.refetches is None
        else [_refetch_line(row) for row in root.refetches]
    )
    return [
        *rows,
        f"- Stage 2 requests: {usage.requests} of {STAGE2_LIMITS.requests}",
        f"- Stage 2 wire bytes: {usage.wire_bytes} of {STAGE2_LIMITS.wire_bytes}",
    ]


def _refetch_line(row: dict) -> str:
    """A `refetches` row with all its columns, as `<accession>: <column> <value>, ...`."""
    values = (
        f"{column} {value.isoformat() if isinstance(value, datetime) else _text(value)}"
        for column, value in row.items()
        if column != "accession_number"
    )
    return f"- {row['accession_number']}: {', '.join(values)}"


_SECTIONS: tuple[tuple[str, Callable[[_Root], list[str]]], ...] = (
    ("Index", _index),
    ("Sample", _sample),
    ("Fetch outcomes", _fetch_outcomes),
    ("Cost", _cost),
    ("Envelope parse errors", _parse_errors),
    ("Header checks", _header_checks),
    ("Wall time", _wall_time),
    ("Disk use", _disk_use),
    ("Facts", _facts),
    ("Ownership", _ownership),
    ("Platform checks", _platform_checks),
    ("Times", _times),
    ("Provenance", _provenance),
    ("Refetches", _refetches),
)
