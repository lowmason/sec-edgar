"""The `facts` command: the as-filed XBRL facts of each sampled 10-K and 10-Q filing."""

from dataclasses import asdict, dataclass, field
from operator import itemgetter

from sec_filing_data.envelope import EnvelopeError, document_text, parse_submission
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import build_fetches
from sec_filing_data.provenance import read_provenance
from sec_filing_data.tables import read_table, write_table
from sec_filing_data.xbrl import Fact, XbrlError, find_instance, parse_instance

FACT_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})

NO_INSTANCE = "no XBRL instance in the submission"
NO_FACTS = "no facts in the instance"


@dataclass(frozen=True)
class Extraction:
    """What one filing gave: its instance file, why it gave no facts (or None), the facts."""

    source_document: str | None
    reason: str | None
    facts: list[Fact] = field(default_factory=list)


def run_facts(layout: Layout) -> int:
    """Write `facts` and `facts_status` (one row per sampled filing in FACT_FORMS).

    It reads `fetches` from its table, or builds it from the ledger when the table is
    missing. A filing that gave no facts has a `reason` and no `fact_count`. Each fact carries
    the source and the times of its filing, from `filings`: without that table it raises
    FileNotFoundError.
    """
    provenance = read_provenance(layout)
    sample = sorted(read_table(layout, "sample").to_pylist(), key=itemgetter("draw"))
    fetches = {row["accession_number"]: row for row in _read_fetches(layout)}
    facts, statuses = [], []
    for sampled in sample:
        if not in_fact_forms(sampled["form_type"]):
            continue
        accession = sampled["accession_number"]
        outcome = fetches[accession]["outcome"]
        raw = layout.submission(accession).read_bytes() if outcome == "ok" else None
        extraction = extract_facts(outcome, raw)
        statuses.append(
            {
                "accession_number": accession,
                "form_type": sampled["form_type"],
                "source_document": extraction.source_document,
                "fact_count": len(extraction.facts) if extraction.reason is None else None,
                "reason": extraction.reason,
            }
        )
        # `provenance[accession]` is read only for a filing that has facts.
        if extraction.facts:
            facts.extend(fact_rows(accession, extraction, provenance[accession]))
    write_table(layout, "facts", facts)
    write_table(layout, "facts_status", statuses)
    return 0


def _read_fetches(layout: Layout) -> list[dict]:
    if layout.table("fetches").exists():
        return read_table(layout, "fetches").to_pylist()
    return build_fetches(layout)


def in_fact_forms(form_type: str) -> bool:
    """A form type that joins several types with `;` is in the set when any of them is."""
    return any(part in FACT_FORMS for part in form_type.split(";"))


def extract_facts(outcome: str, raw: bytes | None) -> Extraction:
    """Read the facts of one filing, from its fetch `outcome` and its bytes `raw`.

    `raw` is None unless the outcome is `ok`. The checks run in the order of the `reason` values.
    """
    if outcome != "ok":
        return Extraction(None, outcome)
    try:
        submission = parse_submission(raw)
    except EnvelopeError as error:
        return Extraction(None, f"submission parse error: {error}")
    instance = find_instance(submission.documents)
    if instance is None:
        return Extraction(None, NO_INSTANCE)
    try:
        facts = parse_instance(document_text(raw, instance))
    except XbrlError as error:
        return Extraction(instance.filename, f"instance parse error: {error}")
    if not facts:
        return Extraction(instance.filename, NO_FACTS)
    return Extraction(instance.filename, None, facts)


def fact_rows(accession: str, extraction: Extraction, provenance: dict) -> list[dict]:
    """One `facts` row per fact of `extraction`. `provenance` is that of the filing."""
    return [
        {"accession_number": accession, "source_document": extraction.source_document}
        | asdict(fact)
        | provenance
        for fact in extraction.facts
    ]
