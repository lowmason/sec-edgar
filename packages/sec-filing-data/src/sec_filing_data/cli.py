"""The `sec-filing-data` command. Each subcommand is one step of the run."""

import argparse
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from sec_filing_data import facts, index, report, sample, submissions
from sec_filing_data.layout import Layout, record_step
from sec_filing_data.ledger import FETCH_OUTCOMES
from sec_filing_data.tables import read_table, write_table

USER_AGENT_VARIABLE = "SEC_USER_AGENT"


def _run_index(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "index"):
        rows = index.read_index(
            Path(args.zip), sha256=index.INDEX_SHA256, size=index.INDEX_SIZE
        )
        write_table(layout, "index", rows)
    print(f"rows: {len(rows)}")
    return 0


def _run_sample(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "sample"):
        rows = sample.draw_sample(read_table(layout, "index").to_pylist())
        write_table(layout, "sample", rows)
    strata = Counter(row["stratum"] for row in rows)
    quota_forms = Counter(row["form_type"] for row in rows if row["stratum"] == "quota")
    for name in sample.STRATA:
        print(f"{name}: {strata[name]}")
    for name in sample.QUOTA_FORMS:
        print(f"{name}: {quota_forms[name]}")
    return 0


def _run_fetch(args: argparse.Namespace) -> int:
    user_agent = os.environ.get(USER_AGENT_VARIABLE, "")
    if not user_agent.strip():
        print(f"error: {USER_AGENT_VARIABLE} is not set", file=sys.stderr)
        return 2
    # Only this command loads the SEC client, so the other commands never import requests.
    from sec_filing_data import fetch

    layout = Layout(Path(args.out))
    with record_step(layout, "fetch"):
        code = fetch.run_fetch(layout, user_agent=user_agent, per_form=args.per_form)
    outcomes = Counter(row["outcome"] for row in read_table(layout, "fetches").to_pylist())
    for outcome in FETCH_OUTCOMES:
        if outcomes[outcome]:
            print(f"{outcome}: {outcomes[outcome]}")
    return code


def _run_envelopes(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "envelopes"):
        code = submissions.run_envelopes(layout)
    for name in ("filings", "parties", "documents"):
        print(f"{name}: {read_table(layout, name).num_rows}")
    return code


def _run_facts(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "facts"):
        code = facts.run_facts(layout)
    print(f"facts: {read_table(layout, 'facts').num_rows}")
    reasons = Counter(row["reason"] for row in read_table(layout, "facts_status").to_pylist())
    # A filing that gave facts has no reason. It prints first, as `ok`.
    print(f"status ok: {reasons.pop(None, 0)}")
    for reason, count in sorted(reasons.items()):
        print(f"status {reason}: {count}")
    return code


def _run_report(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "report"):
        text = report.run_report(layout)
    sys.stdout.write(text)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sec-filing-data")
    commands = parser.add_subparsers(dest="command", required=True)

    index_parser = commands.add_parser("index", help="write the index table from master.zip")
    index_parser.add_argument("--zip", required=True, help="path of the quarter's master.zip")
    index_parser.add_argument("--out", required=True, help="output root")
    index_parser.set_defaults(run=_run_index)

    sample_parser = commands.add_parser("sample", help="draw the sample from the index table")
    sample_parser.add_argument("--out", required=True, help="output root")
    sample_parser.set_defaults(run=_run_sample)

    fetch_parser = commands.add_parser(
        "fetch", help=f"fetch the sampled submission files (needs {USER_AGENT_VARIABLE})"
    )
    fetch_parser.add_argument("--out", required=True, help="output root")
    fetch_parser.add_argument(
        "--per-form", type=int, help="fetch only the first N quota filings of each form"
    )
    fetch_parser.set_defaults(run=_run_fetch)

    envelopes_parser = commands.add_parser(
        "envelopes", help="write the filings, parties and documents tables"
    )
    envelopes_parser.add_argument("--out", required=True, help="output root")
    envelopes_parser.set_defaults(run=_run_envelopes)

    facts_parser = commands.add_parser(
        "facts", help="write the facts and facts_status tables from the XBRL instances"
    )
    facts_parser.add_argument("--out", required=True, help="output root")
    facts_parser.set_defaults(run=_run_facts)

    report_parser = commands.add_parser("report", help="print the Markdown report of the root")
    report_parser.add_argument("--out", required=True, help="output root")
    report_parser.set_defaults(run=_run_report)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.run(args)
