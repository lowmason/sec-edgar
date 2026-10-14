#!/bin/sh
set -eu
# Includes real spawned ETL publication/repair proofs and every command's help contract.
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
uv build --offline --all-packages
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
for command in discover collect transform publish backfill daily reconcile approve candidates rollback history; do
  uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest "$command" --help >/dev/null
done
uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
uv run --offline --frozen --package sec-edgar-ingest python -m compileall -q packages/sec-edgar-ingest/src
# Quarterly original-byte fixtures intentionally retain CRLF; no repository config is changed.
git -c core.whitespace=cr-at-eol diff --check
# The pipeline JSON is its rendered source, and main.json is its pinned compile (spec §9).
uv run --offline --frozen --package sec-edgar-ingest python infra/azure/sec-edgar-ingest/pipelines/render.py
git diff --exit-code -- infra/azure/sec-edgar-ingest/pipelines
bicep="${BICEP:-$HOME/.azure/bin/bicep}"
"$bicep" --version | grep -q '^Bicep CLI version 0\.38\.33 '
compiled="$(mktemp -d)"
"$bicep" build infra/azure/sec-edgar-ingest/main.bicep --outfile "$compiled/main.json"
cmp "$compiled/main.json" infra/azure/sec-edgar-ingest/main.json
rm -r "$compiled"
