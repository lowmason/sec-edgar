# sec-edgar-ingest

`sec-edgar-ingest` acquires immutable SEC filing-index originals on Python 3.14+.
It exposes the `sec_edgar_ingest` import package, `sec-edgar-ingest` console entry
point, and `python -m sec_edgar_ingest`. Invoking it without arguments prints help.
`discover` freezes a source workset; `collect` resolves that workset's members to
write-once snapshot pins and emits a separate snapshot workset when complete.

From the repository root:

```sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
uv build --offline --all-packages
scripts/check-sec-edgar-ingest.sh
```

Build/dependency requirements were cached during the accepted setup. Installation
uses the lock's exact 20 runtime versions and the four direct pins in this package.
Offline checks refuse a missing cache. This local macOS build does not establish
Linux container compatibility or worker capacity.


Set up the existing workspace from the accepted cache without changing the lock:

```sh
uv sync --offline --frozen --package sec-edgar-ingest
uv build --offline --all-packages
```

Python 3.14+, uv, the locked runtime wheels and the cached `uv_build` build
requirement must already be available from the authorized dependency setup.
A missing cache is a prerequisite failure; obtain that separately authorized
setup rather than fetching dependencies or changing pins during a fixture run.

To install the built wheel in a fresh environment, run from the repository root:

```sh
python3 -m venv --without-pip /tmp/sec-edgar-installed
uv export --offline --frozen --no-dev --no-emit-workspace \
  --output-file /tmp/sec-edgar-pinned-requirements.txt
uv pip install --offline --no-index \
  --find-links specs/evidence/sec-filing-index-ingestion/stage-2/verification/sdd-history/task1-evidence/wheels \
  --python /tmp/sec-edgar-installed/bin/python --require-hashes \
  -r /tmp/sec-edgar-pinned-requirements.txt
uv pip install --offline --no-index --no-deps \
  --python /tmp/sec-edgar-installed/bin/python \
  dist/sec_edgar_ingest-0.1.0-py3-none-any.whl
/tmp/sec-edgar-installed/bin/sec-edgar-ingest --help
/tmp/sec-edgar-installed/bin/python -m sec_edgar_ingest --version
```

Use a fresh unused environment path. `python3` must be the available Python 3.14+
interpreter (the workspace `.venv/bin/python` also works). The retained wheel
cache contains the accepted 20 runtime versions for this local macOS platform;
other platforms require their separately authorized matching cached artifacts.
The hash-bearing export preserves exact lock pins. Wheel installation uses
`--no-deps` only after that explicit dependency installation. These uv pip/build
commands have no `--frozen` option; the lock export, exact hashes, offline and
no-index flags enforce the selected installation. Run fixture commands with
`/tmp/sec-edgar-installed/bin/sec-edgar-ingest` and the same explicit config,
pack and state-dir arguments below. The console works outside the source checkout;
no editable import or PYTHONPATH is needed.

The configuration filename is YAML, but its supported syntax is strict **JSON**,
a subset of YAML 1.2. Duplicate keys, nonfinite values, unsupported fields, missing
identity/version pins, invalid storage bindings, and unsafe paths are refused.
Loading/validating configuration constructs no external clients. The checked-in
file selects `local-fixture`, relative `.fixture-state`, synthetic parser/image
provenance and the accepted SEC User-Agent. Every fixture invocation must supply
`--fixture-pack PATH`. Fixture manifests bind canonical SEC URLs to explicit
original body files and SHA-256 values; missing/exhausted responses never fetch
the URL. Fixture-only durable response cursors let a new process advance a
scripted 404 to its later valid response.

Every acquisition command requires `--config`, `--run-id`, `--execution-id`,
`--attempt-id`, and an aware UTC `--deadline`. `discover` requires `--mode
quarterly|daily` and `--discovery-id`; `--refresh` freezes explicit acquisition
refresh. `collect --workset REF` accepts the exact immutable source object path,
`worksets/sec/source/sha256=<id>/workset.json`. Help describes the full arguments.
Identifier path segments are checked before any backend construction.

`--state-dir PATH` is fixture-only: it selects the base directory beneath which
relative `storage.root` is placed. The actual durable root is
`PATH / storage.root`, and its resolved path is part of the shared deployment
registry. Contenders must use the same root and binding. The config hash continues
to include its unchanged relative root. `--today YYYY-MM-DD` requires the explicit
`fixture.allow_clock_override` marker; distant fixture deadlines require
`fixture.allow_deadline_override`. Arbitrary input configurations do not receive
implicit override markers. Azure rejects fixture packs, state/date overrides,
these marker fields, synthetic versions, all-zero images, and distant deadlines.

Pinning resolves `end_quarter=open` once at command start and freezes the exact
configuration, its SHA-256, actual pin date, image digest, parser/schema versions,
and deadline. Daily discovery needs an endpoint containing the current quarter.
A closed historical-quarter config cannot admit October 2026 daily sources.
Fixture subsets do not revise the accepted development/intended historical range.

All collectors share namespace `sec-owner-lowell-mason`, one finite leased Blob
sentinel and one request budget across discovery, downloads, retries, and
reconciliation. Azure uses the explicitly configured accepted account
`secedgardevb8617`, containers `raw`, `worksets`, `quarantine`, `locks`, tables
`SourceState`, `Attempts`, Blob API `2026-04-06`, Table API `2020-12-06`, and fixed
sentinel/registry keys in `locks`. Construction checks the durable binding;
it provisions nothing. Lease/server time uncertainty fails closed.

Accepted starting values are 2015 Q1 through the run's open quarter for initial
development, intended history from 2010 Q1, daily handoff `2026-10-01`, 3 requests
per second without bursts, one active collector, five total request attempts,
exponential jitter from 2 seconds capped at 120 while honoring longer server
delays, connect/read timeouts 15/60 seconds, and guards of 90 seconds per complete
exchange, 67,108,864 received bytes, and 536,870,912 expanded IDX bytes. Job retry
limit is zero; at most one positively confirmed transient orchestration replay
is a later contract. These values establish no coverage, recovery horizon,
capacity, or SLA.

The selected acquisition envelopes are one DEFLATE `master.idx` in a quarterly
ZIP and plain daily IDX. Original archives remain raw ZIP bytes. Worksets use
`sec-acquisition-v1`; schema is `sec-index-v1`; envelope identifiers are
`sec-quarterly-envelope-v1` and `sec-daily-envelope-v1`. Parser version is pinned
provenance. No row parser is implemented.

Stdout is one JSON object with outcome, result reference, and source/snapshot
workset references. Stderr is structured command logging. Durable results live at
`runs/sec/<run-id>/<command>/<attempt-id>/result.json`. Exactly matching completed
attempts replay that result without HTTP; a new attempt continues terminal
incomplete work using the existing frozen workset. See the
[runbook](../../docs/runbooks/sec-edgar-ingest-acquisition.md) for exit codes,
quarantine/pending work, result repair, stopped ownership, and the conservative
Azure clean-release guard.
