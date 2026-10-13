#!/bin/sh
# Assemble the worker image build context: Dockerfile, F1's hash-pinned lock and the offline-built wheel.
# The same context serves the Stage 6 local build and the Stage 7 ACR quick task.
set -eu
[ $# -eq 1 ] || { echo "usage: scripts/build-image-context.sh OUT_DIR" >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$1"
out=$(CDPATH= cd -- "$1" && pwd)
if [ -n "$(ls -A "$out")" ]; then
  echo "context directory must be new or empty: $out" >&2
  exit 2
fi
cp "$root/infra/azure/sec-edgar-ingest/image/Dockerfile" "$root/infra/azure/sec-edgar-ingest/image/requirements.lock" "$out/"
(cd "$root" && uv build --offline --package sec-edgar-ingest --wheel --out-dir "$out" >&2)
count=$(find "$out" -maxdepth 1 -name 'sec_edgar_ingest-*.whl' | wc -l | tr -d ' ')
[ "$count" -eq 1 ] || { echo "expected exactly one wheel in $out, found $count" >&2; exit 1; }
ls -1 "$out"
