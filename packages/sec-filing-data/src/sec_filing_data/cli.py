"""The `sec-filing-data` command. Each subcommand is one step of the run."""

import argparse
import os
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from sec_filing_data import (
    facts,
    index,
    manifest,
    ownership,
    rebuild,
    refetches,
    report,
    sample,
    submissions,
    verify,
    version,
)
from sec_filing_data.layout import Layout, record_step
from sec_filing_data.ledger import FETCH_OUTCOMES, STAGE2_LIMITS, ledger_usage, run_fetches
from sec_filing_data.tables import read_table

USER_AGENT_VARIABLE = "SEC_USER_AGENT"


def _user_agent() -> str | None:
    """The User-Agent from the environment. When it is not set, print an error and give None."""
    user_agent = os.environ.get(USER_AGENT_VARIABLE, "")
    if not user_agent.strip():
        print(f"error: {USER_AGENT_VARIABLE} is not set", file=sys.stderr)
        return None
    return user_agent


def _refuse_unless_clean() -> int | None:
    """Refuse a command that writes under the root when no clean commit can be read.

    Print the reason and give the refusal exit code. Give None when the command may run.
    """
    checkout = version.current_checkout()
    if checkout.clean:
        return None
    print(f"error: refused: {checkout.problem}", file=sys.stderr)
    return version.REFUSED_EXIT


def _run_index(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "index"):
        rows = index.run_index(layout, Path(args.zip))
    print(f"rows: {len(rows)}")
    return 0


def _run_sample(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "sample"):
        rows = sample.run_sample(layout)
    strata = Counter(row["stratum"] for row in rows)
    quota_forms = Counter(row["form_type"] for row in rows if row["stratum"] == "quota")
    for name in sample.STRATA:
        print(f"{name}: {strata[name]}")
    for name in sample.QUOTA_FORMS:
        print(f"{name}: {quota_forms[name]}")
    return 0


def _run_fetch(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    user_agent = _user_agent()
    if user_agent is None:
        return 2
    # Only `fetch` and `refetch` load the SEC client, so the other commands never import
    # requests.
    from sec_filing_data import fetch

    layout = Layout(Path(args.out))
    with record_step(layout, "fetch"):
        code = fetch.run_fetch(layout, user_agent=user_agent, per_form=args.per_form)
    _print_fetch_outcomes(read_table(layout, "fetches").to_pylist())
    return code


def _run_build_fetches(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "build-fetches"):
        rows = run_fetches(layout)
    _print_fetch_outcomes(rows)
    return 0


def _print_fetch_outcomes(rows: list[dict]) -> None:
    """Print `<outcome>: <n>` for each outcome of FETCH_OUTCOMES that has a row."""
    outcomes = Counter(row["outcome"] for row in rows)
    for outcome in FETCH_OUTCOMES:
        if outcomes[outcome]:
            print(f"{outcome}: {outcomes[outcome]}")


def _run_refetch(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    user_agent = _user_agent()
    if user_agent is None:
        return 2
    # As in `fetch`: only this command and `fetch` load the SEC client.
    from sec_filing_data import fetch

    layout = Layout(Path(args.out))
    try:
        with record_step(layout, "refetch"):
            code = fetch.run_refetch(layout, user_agent=user_agent, accessions=args.accession)
    except fetch.UnknownAccession as error:
        # Only this refusal sends and writes nothing. Any other error propagates, because
        # a request record may already be in the Stage 2 ledger.
        print(f"error: {error}", file=sys.stderr)
        return 2
    rows = refetches.build_refetches(layout)
    outcomes = {row["accession_number"]: row["outcome"] for row in rows}
    for accession in dict.fromkeys(args.accession):
        print(f"{accession}: {outcomes.get(accession, 'not refetched')}")
    requests_sent = ledger_usage(layout.stage2_ledger).requests
    print(f"stage 2 requests: {requests_sent} of {STAGE2_LIMITS.requests}")
    return code


def _run_compare_refetches(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "compare-refetches"):
        code = refetches.run_compare_refetches(layout)
    print(f"refetches: {read_table(layout, 'refetches').num_rows}")
    return code


def _run_envelopes(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "envelopes"):
        code = submissions.run_envelopes(layout)
    for name in ("filings", "parties", "documents"):
        print(f"{name}: {read_table(layout, name).num_rows}")
    return code


def _run_facts(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "facts"):
        code = facts.run_facts(layout)
    print(f"facts: {read_table(layout, 'facts').num_rows}")
    _print_status_counts(layout, "facts_status")
    return code


def _run_ownership(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    layout = Layout(Path(args.out))
    with record_step(layout, "ownership"):
        code = ownership.run_ownership(layout)
    print(f"ownership: {read_table(layout, 'ownership').num_rows}")
    _print_status_counts(layout, "ownership_status")
    return code


def _print_status_counts(layout: Layout, table: str) -> None:
    """Print `status ok: n`, then `status <reason>: n` for each reason, sorted."""
    reasons = Counter(row["reason"] for row in read_table(layout, table).to_pylist())
    # A filing that gave rows has no reason. It prints first, as `ok`.
    print(f"status ok: {reasons.pop(None, 0)}")
    for reason, count in sorted(reasons.items()):
        print(f"status {reason}: {count}")


def _run_report(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "report"):
        text = report.run_report(layout)
    sys.stdout.write(text)
    return 0


def _run_rebuild(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "rebuild"):
        code, lines = rebuild.run_rebuild(layout, Path(args.zip))
    _print_lines(lines)
    return code


def _run_check_stage1(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "check-stage1"):
        code, lines = rebuild.check_stage1(layout)
    _print_lines(lines)
    return code


def _run_check_frozen(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "check-frozen"):
        code, lines = rebuild.check_frozen(layout, layout.root / args.folder)
    _print_lines(lines)
    return code


def _run_manifest(args: argparse.Namespace) -> int:
    if (refused := _refuse_unless_clean()) is not None:
        return refused
    zip_path = None if args.zip is None else Path(args.zip)
    if (problem := manifest.zip_problem(args.set, zip_path)) is not None:
        print(f"error: {problem}", file=sys.stderr)
        return 2
    layout = Layout(Path(args.out))
    path = manifest.manifest_path(layout, args.set, version.current_checkout().commit)
    if path.exists():
        print(f"error: {path} exists", file=sys.stderr)
        return 1
    with record_step(layout, "manifest"):
        try:
            path = manifest.write_manifest(layout, args.set, zip_path=zip_path)
        except FileNotFoundError as error:
            # The manifest is built before it is written, so nothing was left behind.
            print(f"error: {error}", file=sys.stderr)
            return 1
    print(f"manifest: {path}")
    print(f"sha256: {manifest.sha256_of(path)}")
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "verify"):
        code, lines = verify.run_verify(layout, Path(args.manifest), rows=args.rows, seed=args.seed)
    _print_lines(lines)
    return code


def _print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


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

    refetch_parser = commands.add_parser(
        "refetch",
        help=f"fetch named sampled filings again, under stage2/ (needs {USER_AGENT_VARIABLE})",
    )
    refetch_parser.add_argument("--out", required=True, help="output root")
    refetch_parser.add_argument(
        "--accession",
        action="append",
        required=True,
        help="accession number of a sampled filing; repeat it for more",
    )
    refetch_parser.set_defaults(run=_run_refetch)

    build_fetches_parser = commands.add_parser(
        "build-fetches",
        help="write the fetches table from the ledger and the bytes on disk (sends no request)",
    )
    build_fetches_parser.add_argument("--out", required=True, help="output root")
    build_fetches_parser.set_defaults(run=_run_build_fetches)

    compare_parser = commands.add_parser(
        "compare-refetches", help="write the refetches table from both ledgers and copies"
    )
    compare_parser.add_argument("--out", required=True, help="output root")
    compare_parser.set_defaults(run=_run_compare_refetches)

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

    ownership_parser = commands.add_parser(
        "ownership",
        help=(
            "write the ownership and ownership_status tables from the Forms 3, 4 and 5,"
            " Schedules 13D and 13G, and Form 13F"
        ),
    )
    ownership_parser.add_argument("--out", required=True, help="output root")
    ownership_parser.set_defaults(run=_run_ownership)

    report_parser = commands.add_parser("report", help="print the Markdown report of the root")
    report_parser.add_argument("--out", required=True, help="output root")
    report_parser.set_defaults(run=_run_report)

    rebuild_parser = commands.add_parser(
        "rebuild",
        help="build every table again in a temporary folder and compare it with the live table",
    )
    rebuild_parser.add_argument("--zip", required=True, help="path of the quarter's master.zip")
    rebuild_parser.add_argument("--out", required=True, help="output root")
    rebuild_parser.set_defaults(run=_run_rebuild)

    check_parser = commands.add_parser(
        "check-stage1",
        help="compare the Stage 1 columns of each live table with tables-stage1",
    )
    check_parser.add_argument("--out", required=True, help="output root")
    check_parser.set_defaults(run=_run_check_stage1)

    frozen_parser = commands.add_parser(
        "check-frozen",
        help="compare each table of a frozen folder with the live table, on every column",
    )
    frozen_parser.add_argument("--out", required=True, help="output root")
    frozen_parser.add_argument(
        "--folder",
        required=True,
        choices=("tables-stage2",),
        help="the frozen folder under the output root",
    )
    frozen_parser.set_defaults(run=_run_check_frozen)

    manifest_parser = commands.add_parser(
        "manifest",
        help="write the manifest of one table set: each file with its size and SHA-256",
    )
    manifest_parser.add_argument("--out", required=True, help="output root")
    manifest_parser.add_argument(
        "--set", required=True, choices=manifest.SETS, help="the table set to list"
    )
    manifest_parser.add_argument(
        "--zip", help="path of the quarter's master.zip (for --set tables only)"
    )
    manifest_parser.set_defaults(run=_run_manifest)

    verify_parser = commands.add_parser(
        "verify",
        help="check a manifest against the root: its files, then record hashes against its inputs",
    )
    verify_parser.add_argument("--out", required=True, help="output root")
    verify_parser.add_argument("--manifest", required=True, help="path of the manifest to check")
    verify_parser.add_argument(
        "--rows",
        type=int,
        default=verify.DEFAULT_ROWS,
        help="rows to derive again from each records table (default: %(default)s)",
    )
    verify_parser.add_argument(
        "--seed",
        type=int,
        default=verify.VERIFY_SEED,
        help="seed of the row sample (default: %(default)s)",
    )
    verify_parser.set_defaults(run=_run_verify)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.run(args)
