"""The `sec-filing-data` command. Each subcommand is one step of the run."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from sec_filing_data import index
from sec_filing_data.layout import Layout, record_step
from sec_filing_data.tables import write_table


def _run_index(args: argparse.Namespace) -> int:
    layout = Layout(Path(args.out))
    with record_step(layout, "index"):
        rows = index.read_index(
            Path(args.zip), sha256=index.INDEX_SHA256, size=index.INDEX_SIZE
        )
        write_table(layout, "index", rows)
    print(f"rows: {len(rows)}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sec-filing-data")
    commands = parser.add_subparsers(dest="command", required=True)

    index_parser = commands.add_parser("index", help="write the index table from master.zip")
    index_parser.add_argument("--zip", required=True, help="path of the quarter's master.zip")
    index_parser.add_argument("--out", required=True, help="output root")
    index_parser.set_defaults(run=_run_index)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.run(args)
