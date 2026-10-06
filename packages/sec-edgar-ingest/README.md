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
