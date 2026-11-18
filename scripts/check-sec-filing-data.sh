#!/bin/sh
# Check the live sec-filing-data package: its unit tests (no network) and a whitespace check.
# CI runs this script too (.github/workflows/sec-filing-data.yml).
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$project_root"
uv run --locked --package sec-filing-data python -m unittest discover \
  -s packages/sec-filing-data/tests -t packages/sec-filing-data
git -c core.whitespace=cr-at-eol diff --check
