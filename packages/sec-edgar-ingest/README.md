# sec-edgar-ingest

`sec-edgar-ingest` acquires immutable SEC filing-index originals and transforms retained bytes
into per-quarter published Parquet generations on Python 3.14+.
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
uses the lock's exact 20 runtime versions plus the accepted PyArrow 25.0.1 ETL pin.
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

The offline installed-wheel driver creates a fresh temporary native Python 3.14+
environment, exports the frozen lock with hashes, installs PyArrow from the
existing uv registry cache, and installs the remaining exact pins from the
retained Stage 2 wheel cache. It then installs the exact built wheel, removes
PYTHONPATH, changes cwd outside the checkout and verifies site-packages source
bytes before running the raw-only sequence and real-process proof. The temporary
environment is removed after its complete logs and evidence are retained.

```sh
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py installed --output /absolute/new/installed-proof
```

Use a fresh output path. This proof requires the already selected Python 3.14+
and cached artifacts; no interpreter or dependency download fallback is allowed.
The retained Stage 2 wheels alone are insufficient for the new PyArrow pin.
The driver's retained `requirements.txt`, split hash-bearing requirement files,
venv/install command logs and wheel SHA identify the exact installation. For a
persistent installation, use those same logged commands with a retained venv
path. Other platforms require their separately authorized matching cached
artifacts. Neither editable imports nor PYTHONPATH is needed by the installed
package.

The configuration filename is YAML, but its supported syntax is strict **JSON**,
a subset of YAML 1.2. Duplicate keys, nonfinite values, unsupported fields, missing
identity/version pins, invalid storage bindings, and unsafe paths are refused.
Loading/validating configuration constructs no external clients. The checked-in
file selects `local-fixture`, relative `.fixture-state`, synthetic parser/image
provenance and the accepted SEC User-Agent. Every acquisition fixture invocation must supply
`--fixture-pack PATH`; `transform` and `publish` use exact stored references
and bypass collector construction. Fixture manifests bind canonical SEC URLs to explicit
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
provenance. `sec-index-parser-v1` parses the selected quarterly and daily families
into `sec-index-v1`; local fixture aliases support deterministic replay proof.

Stdout is one JSON object with outcome, result reference, and source/snapshot
workset references. Stderr is structured command logging. Durable results live at
`runs/sec/<run-id>/<command>/<attempt-id>/result.json`. Exactly matching completed
attempts replay that result without HTTP; a new attempt continues terminal
incomplete work using the existing frozen workset. See the
[runbook](../../docs/runbooks/sec-edgar-ingest-acquisition.md) for exit codes,
quarantine/pending work, result repair, stopped ownership, and the conservative
Azure clean-release guard.


For local ETL, pass `--config conf/sec-edgar-etl-fixture.yaml` from the repository
root. This separate [configuration](../../conf/sec-edgar-etl-fixture.yaml) selects
`fixture-index-parser-v1` and preserves the acquisition store binding. Leave
`conf/sec-edgar-ingest.yaml` unchanged: its `fixture-envelope-v1` value records
acquisition provenance and is not an accepted ETL row parser. First populate the
store with a raw snapshot workset through acquisition or explicit offline fixture
seeding, then use its exact reference below.

`transform --workset worksets/sec/snapshot/sha256=<id>/workset.json` freezes
observation outputs and returns an exact transformed workset. `publish --workset
worksets/sec/transformed/sha256=<id>/workset.json` builds and validates candidates,
then commits each quarter independently by conditional pointer update. Readers
capture the exact manifest and validate files before exposing rows. Repeated
unchanged input is a no-op; raw replay under a supported parser version retains
original acquisition provenance and filing identity. A closed withdrawal gate
returns `awaiting_approval` (exit 10), with no current-pointer change.

See the [ETL runbook](../../docs/runbooks/sec-edgar-etl-publication.md) for exact
commands, immutable reference shapes, captured Python reads and interruption
recovery. The [Stage 3 evidence](../../specs/evidence/sec-filing-index-ingestion/stage-3/verification.md)
includes actual spawn CAS races, forced exits, raw-only replay and an isolated
installed-wheel proof on native Python 3.14.0/macOS arm64. Complete retained
specimens SEC-0141–0143 contain 51 conflicting observations and are correctly
refused: Stage 3 source acceptance and completion remain blocked. All 22 later
integrated checks, Linux worker capacity and live Azure/authentication remain
reserved.

The installed ETL proof extends the Stage 2 installation above: export the exact
updated lock, install its hash-bearing PyArrow entry from the existing offline
uv cache, and install the other hash-bearing entries from the retained Stage 2
wheel directory. The executable driver automates this separation, installs the
exact built wheel and checks site-packages source equality outside the checkout:

```sh
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py installed --output /absolute/new/installed-proof
```
