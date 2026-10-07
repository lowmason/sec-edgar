# SEC EDGAR filing-index ingestion

This Python 3.14+ workspace implements acquisition and retained-byte ETL in
[`sec-edgar-ingest`](packages/sec-edgar-ingest/README.md), imported as
`sec_edgar_ingest`. The root coordinates the workspace and is not an installable
Python package. The CLI supports `discover`, `collect`, `transform`, `publish`, help, and version
`0.1.0`. It produces immutable source, snapshot and transformed worksets, validated
Parquet generations, captured reads and durable command results.

Set up the workspace using the already authorized cache, then build the installable
wheel without changing pins:

```sh
uv sync --offline --frozen --package sec-edgar-ingest
uv build --offline --all-packages
```

For a fresh wheel installation, follow the exact lock-export/hash-checked cached
dependency/wheel commands in the [package installation instructions](packages/sec-edgar-ingest/README.md)
and [runbook](docs/runbooks/sec-edgar-ingest-acquisition.md). Python 3.14+, uv and
cached runtime/build requirements are prerequisites; a missing cache requires
separately authorized setup.

Run the complete local check using cached, pinned dependencies:

```sh
scripts/check-sec-edgar-ingest.sh
```

The script runs offline fixture and mocked Azure tests, builds wheel and sdist,
checks both CLI entry points, compiles the package, and checks the diff. A missing
cache is a prerequisite failure. Tests use committed synthetic/retained fixtures;
the suite installs network/resolution and provider-auth denial before test imports.
Only explicitly selected bounded loopback fixture origins are allowed, including
in their spawned transport children. Production CLI/SDK behavior is outside this
test-only guard.

Configuration in `conf/sec-edgar-ingest.yaml` uses JSON syntax, a YAML 1.2 subset.
Its `local-fixture` acquisition backend requires an explicit validated
`--fixture-pack`; retained-byte ETL reads stored inputs without a fixture pack.
There is no live fallback. See the [acquisition runbook](docs/runbooks/sec-edgar-ingest-acquisition.md)
for commands, shared issuer requirements, failure meanings, and safe recovery.
The [Stage 2 verification record](specs/evidence/sec-filing-index-ingestion/stage-2/verification.md)
distinguishes retained and synthetic evidence from the later runtime gates.

The `sec-edgar-client` and `sec-edgar-download` scaffolds remain on disk for
reference, excluded from the workspace and runtime dependencies. The four
superseded `sec-edgar-index-ingest` files remain deleted and unstaged. The local
planning roadmap is ignored. The [ETL publication runbook](docs/runbooks/sec-edgar-etl-publication.md) describes
raw-only replay, per-quarter CAS publication, captured reads and recovery. The
[Stage 3 verification record](specs/evidence/sec-filing-index-ingestion/stage-3/verification.md)
records passing native offline capability proofs and the separate retained-source
acceptance blocker: SEC-0141–0143 contain 51 conflicting observations. Stage 3
completion remains blocked. Reconciliation approval, Azure provisioning and
scheduled activation remain later-stage work; all 22 integrated checks are
reserved for roadmap Stage 7.
