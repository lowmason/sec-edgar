# Use Azure-managed orchestration for SEC filing indexes

- **Status:** Proposed
- **Date:** 2026-10-05
- **Deciders:** Lowell (owner; acceptance pending)
- **Blast radius:** historical and daily SEC index ingestion; the ingestion manifest; raw and
  curated storage; ETL execution; `packages/sec-edgar-ingest/`; deployment, monitoring and
  recovery procedures.
- **Design spec:** [SEC filing-index ingestion on Azure](sec-filing-index-ingestion-spec.md).

## Context

As of the workload discussion on 2026-10-05.

- The workload has three requested steps: download archived quarterly filing indexes once,
  download daily indexes thereafter, and run ETL. Both ingestion paths need checkpoints so an
  interruption does not restart the historical load or lose a daily file.
- The indexes are a filing catalog, not the filing-text corpus. They identify companies, form
  types, filing dates and submission paths. Downloading the referenced submissions, or collecting
  Feed and Oldloads archives, is a separate workload. [SEC index and archive guidance][sec-access]
- The preceding proposal adds reconciliation. The SEC describes weekly rebuilding of full and
  quarterly indexes to incorporate corrections; earlier daily indexes do not reflect every
  later removal. A one-time baseline and an append-only daily feed are therefore not sufficient
  for a corrected catalog. [SEC index maintenance][sec-access]
- SEC access is a shared constraint. Its published ceiling is 10 requests per second per user
  across machines, not per worker. Backfill, daily ingestion and reconciliation must share one
  download budget. [SEC developer resources][sec-developers]
- Airflow-like orchestration is wanted; compatibility with existing Airflow DAGs has not been
  required. No workload measurement supplied here establishes a need for Spark or a Kubernetes
  deployment. The business ETL beyond normalized index metadata, the serving layer and a freshness
  service-level objective have not been specified.

## Decision

We will use **Azure Data Factory (ADF)** to orchestrate three pipelines: historical backfill,
ongoing daily ingestion and recurring reconciliation. They will call shared Python processing
code in **Azure Container Apps Jobs**. Original source snapshots and transformed Parquet data
will live in **Azure Data Lake Storage Gen2 (ADLS)**; **Azure Table Storage** will hold the
manifest and active-publication pointers; **Azure Monitor and Log Analytics** will receive
execution logs and alerts. These services provide the scheduling, run-to-completion execution,
storage and observability used by this design. [ADF schedules][adf-schedule]
[Container Apps Jobs][aca-jobs] [ADLS][adls] [Table Storage][tables]
[Container Apps observability][aca-observability]

ADF owns workflow dependencies and run outcomes. The Python worker owns source discovery,
SEC-compliant HTTP access, validation, parsing and publication. ADF will start a job through its
Web activity and the Azure management API, then wait for that execution's terminal result.
Acceptance of a start request is not completion of the work. [ADF Web activity][adf-web]
[Container Apps job execution][aca-jobs]

The three pipelines will share source identities, immutable raw snapshots and versioned processing
contracts. One coordinated downloader will own all application traffic to the SEC. ETL workers
will read stored inputs, not fetch their own copies. Retries may repeat execution, but publication
must not duplicate records, expose partial output or overwrite a newer generation.

For this draft, ETL means **a validated, normalized filing-index dataset**. Filing-text extraction,
XBRL processing and a query-serving database are separate decisions. Reconciliation will retain
change history; a missing response or an incomplete replacement will never authorize a removal.
The spec defines conservative withdrawal handling and the proposed operating defaults.

**Monorepo package.** The implementation will live in **`packages/sec-edgar-ingest/`**, with
`sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import
package. `ingest` names the full responsibility: discovery, download, validation, parsing,
checkpoints, reconciliation and publication. Downloading stays in the internal module
`src/sec_edgar_ingest/download.py`, relative to the package root. The broader package name does
not expand the index-only scope of this decision.

Backfill, daily ingestion and reconciliation are workflows in that same package, under
`src/sec_edgar_ingest/workflows/`, not separate packages. Separate download and ETL job
executions invoke commands from the same package; execution boundaries do not require package
boundaries. Azure deployment definitions live separately at `infra/azure/sec-edgar-ingest/`.
These are proposed monorepo paths, not assertions about an existing repository.

No `sec-edgar-download` or `sec-edgar-client` package is introduced initially. Extract
`packages/sec-edgar-client/` only when a second package genuinely needs the same SEC HTTP access
and download primitives. The dependency will be `sec-edgar-ingest` → `sec-edgar-client`, never
the reverse. Workflows, ingestion state, parsing and publication remain in `sec-edgar-ingest`;
extracting a client does not create an independent SEC request budget for each consumer.

## Consequences

- **Positive:** orchestration is separated from SEC-specific code; historical and daily inputs use
  the same parser; raw snapshots support reprocessing without another SEC download; failures are
  recoverable at source-file boundaries; reconciliation can account for changes that a daily-only
  design misses. Download throughput and local transformation throughput can be controlled
  independently. One implementation package keeps the shared workflow contracts together
  without creating a separate package for each job.
- **Negative:** the system operates more resources than a scheduled script. ADF must track
  asynchronous job execution, and the application must implement a manifest, shared download
  coordination, source precedence and safe publication. Periodic reconciliation means historical
  indexes are downloaded again; “one-time” describes the initial backfill, not permanent immunity
  from later source changes. Plain Parquet requires an explicit publication protocol rather than
  an assumed upsert operation.
- **Neutral / follow-on:** the deployment must select an Azure region, network policy, identities,
  resource sizes, retention policy and alert destination. Those values are not established by this
  ADR. Filing-content ingestion can reuse the raw-store and manifest patterns, but it does not
  enter scope through an index-parser change.

## Alternatives considered

- **Container Apps Jobs without ADF** — not chosen for this proposal. A manual backfill job and
  a scheduled daily job would reduce orchestration resources, but dependency handling and
  workflow-level recovery would move into application code. Revisit if the implementation remains
  a single small workflow and the owner prefers that trade-off. [Job trigger types][aca-jobs]
- **ADF HTTP Copy for downloads** — not chosen as the primary ingestion implementation. The
  connector supports HTTP downloads and request headers, but this design keeps source discovery,
  the shared SEC request budget and validation together in Python. HTTP Copy remains a viable
  simplification for an index-only implementation. [ADF HTTP connector][adf-http]
- **Managed Airflow, or Airflow on AKS** — not selected. Existing DAG compatibility and custom
  Airflow deployment control are not requirements in the supplied workload; an Airflow platform
  would introduce a separate platform choice without changing the required data contracts.
- **Spark or Databricks as the initial ETL platform** — deferred. Reconsider against measured
  runtime, memory use or future filing-content transformations, not the historical date range
  alone.
- **Quarterly backfill followed only by daily appends** — rejected. It has no mechanism for
  reconciling later corrections and removals. [SEC index maintenance][sec-access]
- **`sec-edgar-download` as the implementation package** — rejected: acquisition is only one
  part of the workload. The package also owns validation, parsing, checkpoints, reconciliation
  and publication; `download` remains an internal module.
- **`sec-edgar-index-ingest`** — not chosen. It would be appropriate for a dedicated
  index-only package boundary; `sec-edgar-ingest` leaves room for separately approved EDGAR
  ingestion work without authorizing that work now.
- **One package per workflow or job, or an upfront shared SEC client** — not chosen. The initial
  workflows share the same implementation, and a second package needing reusable SEC access has
  not been established. Split on demonstrated reuse, not on ADF pipeline or job boundaries.

## Trade-offs & reversibility

A two-way door for the scheduler and worker runtime: source snapshots, manifests and the Python
contracts do not depend on an Airflow DAG or an ADF activity definition. Moving orchestration still
requires rebuilding deployment, scheduling and operational integration; it is not a configuration
switch. Revisit the package boundary when a second consumer needs the shared SEC-access
implementation; that extraction is not a reason to change source identities or publication
contracts.

Publication is a separate boundary. Retained generations allow the active dataset pointer to move
back, but they do not undo exports or decisions already made by downstream consumers. Retaining
snapshots also has a storage cost. Revisit this ADR when existing Airflow DAGs become a requirement,
index ETL exceeds the measured capacity of the chosen jobs, or filing-content processing changes
the workload. Until then, the [design spec](sec-filing-index-ingestion-spec.md) is the implementation
contract, once both documents are accepted.

[sec-access]: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
[sec-developers]: https://www.sec.gov/about/developer-resources
[adf-schedule]: https://learn.microsoft.com/en-us/azure/data-factory/how-to-create-schedule-trigger
[adf-web]: https://learn.microsoft.com/en-us/azure/data-factory/control-flow-web-activity
[adf-http]: https://learn.microsoft.com/en-us/azure/data-factory/connector-http
[aca-jobs]: https://learn.microsoft.com/en-us/azure/container-apps/jobs
[adls]: https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction
[tables]: https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-overview
[aca-observability]: https://learn.microsoft.com/en-us/azure/container-apps/observability
