# SEC EDGAR filing-index ingestion

This Python 3.14+ workspace has one implementation package:
[`sec-edgar-ingest`](packages/sec-edgar-ingest/README.md), imported as
`sec_edgar_ingest`. The root is a workspace coordinator and is not an installable
Python package.

The current milestone establishes packaging, version reporting, and CLI help.
Acquisition is still under development; `discover` and `collect` are not runnable
commands yet. Row parsing, publication, and orchestration are outside this
milestone.

```sh
uv sync --frozen
uv run --frozen --package sec-edgar-ingest sec-edgar-ingest --help
uv run --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
uv build --all-packages
```

Run the offline tests with:

```sh
uv run --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

The `sec-edgar-client` and `sec-edgar-download` scaffolds remain on disk for
reference. They are excluded from the workspace and runtime dependency graph.
The superseded `sec-edgar-index-ingest` scaffold remains deleted. The local
planning roadmap is ignored by Git.
