# sec-edgar-ingest

`sec-edgar-ingest` is the sole SEC filing-index acquisition implementation in this
workspace. It requires Python 3.14 or newer and exposes the `sec_edgar_ingest`
import package, the `sec-edgar-ingest` console entry point, and
`python -m sec_edgar_ingest`.

At this milestone the CLI provides help and version `0.1.0`. Invoking it without
arguments prints help. `discover` and `collect` are not implemented yet;
acquisition completion is a later milestone.

From the repository root:

```sh
uv run --frozen --package sec-edgar-ingest sec-edgar-ingest --help
uv run --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
```

The package pins Requests and the Azure identity, Blob Storage, and Table Storage
SDKs for the approved acquisition boundary. The root constrains their accepted
transitive versions, and `uv.lock` records the workspace resolution. A local
package build does not establish container compatibility or worker capacity.

The client and download scaffolds are preserved as references, outside the
workspace and runtime dependency graph. This milestone performs no live SEC
requests or Azure operations.

Configuration v1 in `conf/sec-edgar-ingest.yaml` uses **JSON syntax**, a subset
of YAML 1.2. The stdlib JSON loader rejects general YAML, duplicate keys and
nonfinite values. `Settings.from_mapping` validates settings without constructing
credentials, clients or transports; `load_config` only reads the selected file.
`pin_context` resolves `open` once from the explicit run-start date and freezes
the complete effective configuration, its SHA-256, image/parser/schema provenance
and finite UTC command deadline into the workset context.

The checked-in configuration explicitly selects `local-fixture`, the ignored
`.fixture-state/` root, synthetic parser provenance and an all-zero fixture image
digest. Loading it creates no state directory. Fixture storage initialization is
responsible for creating that root later, and all contenders must share the same
root and binding. Fixture-only HTTP caps can be smaller for bounded generated
streams; `fixture.allow_clock_override` and `fixture.allow_deadline_override`
explicitly label test overrides. Azure refuses these override markers, synthetic
provenance and the all-zero digest. No real image digest, principal or endpoint
configuration is supplied by the fixture file.

Azure configuration must explicitly name the accepted `secedgardevb8617` account,
its credential-free Blob/Table HTTPS endpoints, `raw`, `worksets`, `quarantine`
and `locks` containers, `SourceState` and `Attempts`, Blob API `2026-04-06` and
Table API `2020-12-06`, immutable image provenance and parser/schema identifiers.
All workflows bind to namespace `sec-owner-lowell-mason`, lock blob
`sec-owner-lowell-mason/sentinel.json` and binding registry blob
`sec-owner-lowell-mason/binding.json` in `locks`. The later storage adapter must
conditionally create/check the registry; settings validation creates no lane or
resource. Lease 60 seconds, renewal every 20 seconds and clock uncertainty at
most 2 seconds are application mechanics. The adapter must derive actual
server-time bounds and fail closed when they exceed the configured uncertainty.

The accepted starting values are 2015 Q1 through the run's open quarter for
initial development, daily handoff `2026-10-01`, 3 SEC requests per second with
no bursts, one active collector, five total HTTP attempts, exponential jitter
from 2 seconds capped at 120 seconds while honoring longer server delays,
15/60-second connect/read timeouts, a 90-second complete exchange, 67,108,864
received bytes and 536,870,912 expanded IDX bytes. Job retry limit is zero and
orchestration permits at most one confirmed-transient replay. The intended full
historical range starts in 2010 Q1. Daily scheduling starts at 05:00 Eastern every
day; reconciliation starts Sunday at 06:00 Eastern. Trigger definitions and
activation belong to later stages. These defaults establish no coverage,
recovery horizon, worker capacity or SLA.

Workset JSON uses `sec-acquisition-v1`; schema provenance remains `sec-index-v1`.
Source members and directory outcomes are sorted deterministically, and strict
decoders verify their content hash and exact membership. Snapshots name each
source and its immutable raw hash/path. The selected acquisition envelope
identifiers are `sec-quarterly-envelope-v1` for ZIP and `sec-daily-envelope-v1`
for IDX. `parser_version` remains provenance; no row parser is implemented here.
