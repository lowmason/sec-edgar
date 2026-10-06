# SEC EDGAR filing-index ingestion

This Python 3.14+ workspace implements acquisition in
[`sec-edgar-ingest`](packages/sec-edgar-ingest/README.md), imported as
`sec_edgar_ingest`. The root coordinates the workspace and is not an installable
Python package. The CLI supports `discover`, `collect`, help, and version `0.1.0`.
It produces immutable source and snapshot worksets and durable command results.

Run the complete local check using cached, pinned dependencies:

```sh
scripts/check-sec-edgar-ingest.sh
```

The script runs offline fixture and mocked Azure tests, builds wheel and sdist,
checks both CLI entry points, compiles the package, and checks the diff. A missing
cache is a prerequisite failure. Tests use committed synthetic/retained fixtures;
only the expressly bounded process fixtures contact local loopback servers.

Configuration in `conf/sec-edgar-ingest.yaml` uses JSON syntax, a YAML 1.2 subset.
Its `local-fixture` backend requires an explicit validated `--fixture-pack` and
has no live fallback. See the [acquisition runbook](docs/runbooks/sec-edgar-ingest-acquisition.md)
for commands, shared issuer requirements, failure meanings, and safe recovery.
The [Stage 2 verification record](specs/evidence/sec-filing-index-ingestion/stage-2/verification.md)
distinguishes retained and synthetic evidence from the later runtime gates.

The `sec-edgar-client` and `sec-edgar-download` scaffolds remain on disk for
reference, excluded from the workspace and runtime dependencies. The four
superseded `sec-edgar-index-ingest` files remain deleted and unstaged. The local
planning roadmap is ignored. Row parsing, publication, reconciliation approval,
Azure provisioning, and scheduled activation belong to later stages.
