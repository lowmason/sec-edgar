# SEC filing-index ingestion on Azure — Design Spec

**Status:** ACCEPTED (2026-10-05) — formally accepted by Lowell Mason.

**Acceptance record:** The owner accepted this spec and its ADR, including the operating
defaults, on 2026-10-05. Stage 1 records the selected range and deployment settings and investigates
readiness. Acceptance establishes the implementation contract; the readiness finding and later
deployment evidence remain separate gates. References below to the proposal or draft describe
the document's original design provenance.

**Decision:** [Use Azure-managed orchestration for SEC filing indexes](sec-filing-index-ingestion-adr.md).

**Basis:** The preceding workload discussion and Azure service proposal. The detailed contracts,
withdrawal safeguards and numeric defaults below are proposed here; they are not measured results
or previously approved requirements. Linked provider documentation is carried forward from that
discussion, not independently reverified for this draft.

**Repository:** No repository was supplied. Every code, configuration and deployment path below is
proposed. No resource is assumed to exist.

## 1. Purpose

Build a filing-index catalog from a historical quarterly baseline and ongoing daily indexes.
Run the same ETL over both, preserve source snapshots for replay, and reconcile later quarterly
changes. A failed run resumes from durable state; a successful run exposes a complete dataset
generation, not partially written files.

## 2. Scope

### 2.1 In scope

- **Backfill.** Enumerate and ingest archived quarterly indexes over a configured range. Use the
  current full index when the requested baseline reaches the open quarter.
- **Daily ingestion.** Discover available daily indexes, ingest new or pending sources, and catch
  up after missed runs, including across quarter boundaries.
- **Metadata ETL.** Parse, validate and normalize index rows; resolve duplicate observations;
  publish a canonical filing-index dataset in Parquet with provenance.
- **Reconciliation.** Re-read quarterly indexes, compare content hashes, and account for additions,
  changed fields and confirmed withdrawals without discarding source history.
- **Operations.** Request throttling, checkpoints, retries, coordinated publication, monitoring,
  deployment and recovery tests.

### 2.2 Out of scope

- Downloading filing documents, Feed or Oldloads archives; filing-text extraction; companyfacts
  or submissions JSON ingestion; XBRL transformation.
- A search index, warehouse, SQL serving database or business-specific analytical model.
- Apache Airflow deployment or migration, AKS, Spark and Databricks.
- Exactly-once execution across Azure services. The contract is repeatable execution with
  idempotent, versioned publication.
- A production freshness or cost guarantee before workload measurements and owner approval.

## 3. Rulings

From the workload brief:

- **R1. Baseline.** There is an initial download of archived quarterly filing indexes.
- **R2. Continuation.** Daily indexes are ingested on an ongoing basis.
- **R3. Processing.** Ingested indexes feed ETL.

From the architecture proposal, subject to ADR acceptance:

- **R4. Platform.** ADF orchestrates; Container Apps Jobs runs Python; ADLS holds files; Table
  Storage holds control state; Azure Monitor and Log Analytics hold operational evidence.
- **R5. Shared implementation.** Backfill, daily ingestion and reconciliation differ in source
  selection, not in their downloader, parser or publication code.
- **R6. Replay.** Original bytes are retained. A parser change reprocesses stored inputs without
  requiring a new download. Downloaded, transformed and published are different states.
- **R7. Corrections.** The quarterly baseline is reconciled periodically. “One-time” applies to
  building the initial baseline, not to never revisiting historical source files.
- **R8. Access.** All application requests to the SEC share one downloader and one request budget.
  More ETL workers must not mean more SEC traffic.

Draft implementation decisions:

- **R9. Publication.** Readers resolve a versioned quarter manifest through one active pointer.
  They never discover the current dataset by globbing all Parquet files.
- **R10. Withdrawals.** An HTTP failure, absent listing or open-quarter absence is not a withdrawal.
  A closed-quarter replacement that removes records requires explicit approval tied to its source
  hash before those records leave the active catalog (4.4).
- **R11. Defaults.** The schedules, retry limits and rate target in 4.8 are stated starting values.
  Changing them requires configuration review, not a claim that an SLA has been met.

## 4. Design

### 4.1 Services and ownership

| Component | Owns | Does not own |
|---|---|---|
| ADF | Triggers, pipeline parameters, stage dependencies, job execution polling, run outcome | SEC HTTP behavior, row parsing, data-level commit decisions |
| Container Apps Jobs | Shared Python discovery, collection, transformation and publication commands | A second independent production schedule |
| ADLS Gen2 | Original snapshots, transformed inputs, immutable dataset generations, run reports | A database-style Parquet upsert |
| Table Storage | Source state, attempts, active quarter pointers and approval records | Filing-text or analytical serving |
| Azure Monitor / Log Analytics | Structured logs, health metrics and alerts | The authoritative ingestion manifest |

The selected services expose the scheduling, job execution, storage and logging capabilities used
here. The ownership boundaries are application decisions. [ADF schedules][adf-schedule]
[Container Apps Jobs][aca-jobs] [ADLS][adls] [Table Storage][tables]
[Container Apps observability][aca-observability]

**One image, shared commands.** The `sec-edgar-ingest` CLI exposes `discover`, `collect`,
`transform` and `publish`. Commands exchange durable workset and result files in ADLS. Discovery
writes an immutable source workset. Collection pins one accepted snapshot per member in the
manifest, then emits a separate immutable snapshot workset naming exact hashes. Retries complete
unresolved members without replacing pinned inputs. ETL never silently follows a mutable “latest”.

ADF passes references, not index contents. Each job execution receives the ADF run id, workset
reference, command, attempt id and pinned image digest. ADF starts the execution through Web
activity using managed identity, records its execution id, and polls to a terminal outcome.
Success also requires the matching worker result file. [ADF Web activity][adf-web]
[Container Apps job execution][aca-jobs]

A start timeout with an unknown execution id is an ambiguous start, not permission to launch a
second copy. Resolve the existing execution or stop for operator recovery. The implementation
plan pins the management API version, terminal states and least-privilege role assignments.

### 4.2 Source discovery and pipeline units

**Sources.** Quarterly and quarter-to-date master indexes come from `Archives/edgar/full-index/`;
daily master indexes come from `Archives/edgar/daily-index/`. Use available `index.json` directory
listings for discovery rather than assuming every calendar date has a file. These source families
and directory representations are described in the SEC guidance. [SEC access documentation][sec-access]

**The unit.** One source file is the checkpoint and retry unit. Discovery writes an immutable
workset; collection and ETL checkpoint each member. A multi-file job may fail after finishing some
members; the next attempt reuses those completions. An invalid member prevents a claim of complete
coverage, not the retention of work already completed.

**Backfill.** `start_quarter` and `end_quarter` are required, inclusive parameters.

1. Enumerate the requested quarters and discover their source files.
2. Collect and validate each unprocessed source, preserving original bytes.
3. Transform the snapshot and publish its quarter (4.6).
4. Report complete, pending and failed units separately.

When the range includes the open quarter, its full index seeds the baseline; daily ingestion then
extends it. Daily discovery starts at the approved handoff date and replays overlap with the
baseline. Deduplication handles overlap; a calendar cutover is not trusted to prevent it.

**Daily ingestion.** Inspect the open and immediately preceding quarter, plus every quarter from
the last successful discovery boundary through the present after an outage. Also revisit pending
and failed source identities regardless of their quarter. On the first run, use the configured
handoff date. Never advance discovery past a failed directory read.

Process all discovered, unprocessed files, not just a constructed “yesterday” URL. For a valid
listing with no new files, report `no_new_sources`; do not report that a nonexistent file was
processed. A listed file that cannot be downloaded remains pending or failed. The report includes
unresolved gaps even when later files succeed.

**Reconciliation.** Each scheduled run refreshes every supported quarterly source. Unchanged bytes
skip transformation when parser and schema versions also match. Changed snapshots go through the
same validation and publication path, with 4.4's precedence and withdrawal rules. Reconciliation
failures leave the last valid catalog active and identify the affected quarters.

### 4.3 Collection and SEC access

The SEC's published ceiling is 10 requests per second per user across machines. Its automated
access guidance calls for an identifying User-Agent. The initial application target is lower:
3 requests per second, without bursts. [SEC developer resources][sec-developers]
[SEC download guidance][sec-downloads]

**One request budget.** Discovery requests, downloads, retries and reconciliation all count. The
collector acquires a shared, renewable Storage-backed lease before SEC access. All collectors in
the owner's deployment use the same coordination namespace, including backfill and daily runs.
Only one may issue requests at a time; it releases the lease between bounded work units. Daily
work gets the next turn ahead of remaining backfill or reconciliation units.

Lease loss stops new requests. A successor waits for the previous ownership window and bounded
in-flight request allowance to expire before issuing requests. Independent tools outside this
application are not controlled by that lease; the operator must allocate them within the same
owner-wide SEC ceiling. No worker may evade throttling by changing hosts, identities or addresses.

**Validation before acceptance.** Stream to a temporary object, compute SHA-256 over original bytes,
and check that the response is a complete supported index rather than an HTML error page. Preserve
source URL, receipt time, byte count and available response validators. A receipt timestamp is not
proof of the dates covered by the source.

Promote a valid download to its content-addressed raw location before marking it downloaded. A
truncated or invalid body is quarantined, never accepted as an empty index. Parser failures retain
the downloaded bytes for diagnosis. ETL reads those bytes from ADLS and makes no SEC requests.

### 4.4 Record identity, precedence and reconciliation

**Raw observations and the canonical catalog are different outputs.** Preserve each source's
parsed rows with source hash and parser version. The active catalog resolves those observations;
it does not destroy them.

**Identity.** The proposed logical key is `(cik, archive_path)`, with the CIK normalized to a
10-character decimal string and the path normalized as a relative path under the SEC Archives
root. Preserve original field values in the observation output. Extract an accession number when
the supported filename format permits it; an unrecognized legacy format does not by itself
invalidate a usable index row. Never deduplicate on company name and filing date alone.

A path change is an addition and a possible withdrawal, not an unproved assertion that two paths
identify the same submission. Duplicate keys with identical fields collapse in the canonical
output; conflicting duplicates within one source are refused. This key choice and conflict policy
are new contracts in this draft.

**Open quarter.** A valid quarter-to-date snapshot supplies preferred field values for keys it
contains. Daily observations add keys it does not yet contain. A later snapshot can update field
values, but absence from an open-quarter snapshot does not remove a previously published key:
the discussion does not establish a machine-readable coverage boundary sufficient to authorize
that deletion. Retain the key and report the unresolved absence.

**Closed quarter.** A validated quarterly snapshot is the preferred membership source. Compare it
with the active catalog. Additions and field updates can publish automatically when no keys would
be removed. If keys disappear, stage the entire replacement and a change report; leave the prior
generation active until approval names that exact source hash and candidate generation. Approval
cannot be reused for a later download.

After a replacement is approved, old daily observations cannot recreate a key it excludes. A
subsequent valid quarterly snapshot may reintroduce the key, recorded as a new change. Existing
source snapshots and previous generations remain available under the retention policy.

**Changes.** Each proposed generation records added, updated and withdrawn keys with before/after
values and source provenance. No response failure, empty replacement or unexplained format change
can produce withdrawals. This conservative policy delays some corrections; it is a deliberate
trade-off, not a claim of immediate mirroring of SEC removals.

### 4.5 Storage and manifest contracts

Proposed application paths:

```text
raw/sec/indexes/kind=<quarterly|daily>/period=<period>/sha256=<hash>/master.idx
observations/sec/indexes/source=<source-id>/sha256=<hash>/parser=<version>/rows.parquet
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/part-*.parquet
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/manifest.json
curated/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/changes.parquet
runs/sec/<run-id>/<command>/<attempt-id>/result.json
quarantine/sec/<run-id>/<source-id>/...
```

`period` is a quarter or filing-index date. `source-id` is a stable hash of the canonical source
URL. Paths are content- or generation-addressed; “immutable” is the application write contract,
not an assumption that a storage-account immutability policy has been configured.

**Source manifest.** Separate source identity, snapshot identity and processing identity.

| Record | Required fields |
|---|---|
| Source | Canonical URL, source kind, source period, first seen, last discovery, latest downloaded snapshot, discovery status |
| Snapshot | Source id, SHA-256, raw path, byte count, received time, response validators when available |
| Workset binding | Source-workset id, source id, pinned snapshot hash; write once when collection accepts that member |
| Processing | Source id, snapshot hash, parser version, schema version, state, transformed output reference, row counts |
| Attempt | Run id, execution id, command, attempt id, image digest, start/end times, outcome, structured error |
| Quarter publication | Quarter, active generation id, manifest reference, source-set fingerprint, conditional-write version |
| Withdrawal approval | Quarter, candidate generation, source hash, approver, approval time |

Processing transitions are `downloaded -> transformed -> published`. Discovery may exist before a
snapshot; failures belong to attempts and do not erase an earlier successful state. Parser and
schema changes create a new processing identity. A source is not published merely because the
worker produced Parquet files.

**Canonical row contract.** `schema_version: sec-index-v1`.

| Field | Contract |
|---|---|
| `cik` | Non-null, normalized 10-character decimal string |
| `company_name` | Non-null source name; no entity-resolution or enrichment step |
| `form_type` | Non-null source form type, including amendment suffixes |
| `filing_date` | Valid date; determines the output quarter |
| `archive_path` | Non-null, safe relative SEC Archives path |
| `accession_number` | Nullable; extracted only from a supported path format |
| `source_id`, `source_sha256` | Provenance of the observation selected for the canonical row |
| `parser_version`, `schema_version` | Versions that produced the row |

The publication manifest carries the complete contributing source set, file list, checksums and
row count. The row's chosen provenance need not repeat every duplicate observation. Distinct
amended filings remain distinct records; ETL does not collapse them into their original filing.

### 4.6 ETL and publication

**Parse.** Recognize the index header and expected columns, then parse every data row. Normalize
only the contract fields. Refuse malformed rows rather than silently dropping them; quarantine the
source and report the line and reason. Golden fixtures must cover the historical formats within
the chosen backfill range before that range is declared supported.

**Transform.** Write immutable observation output keyed by snapshot, parser and schema. Apply
4.4's precedence rules when rebuilding each affected quarter. An identical input fingerprint and
unchanged versions are a no-op. A forced replay may rebuild output, but cannot create a second
logical filing.

**Publish.** Plain Parquet is not the commit mechanism. For each affected quarter:

1. Read the active generation and its conditional-write version from Table Storage.
2. Build a candidate generation in a new path using the exact approved source set. Write its
   Parquet, change report and manifest. Validate all files, row counts and key uniqueness.
3. Apply the withdrawal gate (4.4). A gated candidate is `awaiting_approval`, not current.
4. Conditionally replace the quarter's active pointer only if the version read in step 1 still
   matches. A conflict requires rereading the active generation and rebuilding; never overwrite
   a newer pointer with stale work.
5. Record publication results. Readers follow the pointer to the manifest's explicit file list.

The pointer update is the publication boundary. There is no assumed transaction spanning Blob
Storage and Table Storage. A crash before the update leaves an unreferenced generation; a crash
after it leaves committed data whose ancillary manifest state can be repaired from the generation
manifest. Per-source published flags are recoverable indexes, not a second commit authority.

Atomicity is **per quarter**, not across the entire historical dataset. A run report lists which
quarters advanced. A consumer needing a reproducible multi-quarter read captures the generation
ids it uses. A future globally atomic catalog would require another contract.

### 4.7 Failure recovery and observability

All commands emit structured logs with run, execution, attempt, source and generation identifiers.
The durable run report records discovered, downloaded, transformed, published, unchanged, pending,
quarantined and awaiting-approval counts. It also records gaps; a maximum filing date alone is not
proof of complete coverage.

Alert on a failed job, ambiguous start, lease failure, access block, exhausted retry budget,
quarantine, unresolved publication conflict or pending withdrawal approval. Report discovery age,
oldest listed-but-unpublished source and last successful reconciliation separately. A no-new-file
run is distinct from a failed discovery; weekends alone do not imply stale ingestion.

Recovery reuses the workset and accepted snapshots. It does not delete the manifest to “start
clean.” Stop a bad deployment, retain its evidence, restore the previous image digest, and replay
failed units. Moving a quarter pointer back requires an explicit recorded rollback; it cannot
reverse downstream exports already consumed.

### 4.8 Configuration and stated defaults

All keys below are proposed. The implementation validates them before making network requests.

| Setting | Starting value | Config key |
|---|---|---|
| Historical range | Required, inclusive; no assumed start year | `backfill.start_quarter`, `backfill.end_quarter` |
| Daily handoff | Required at initial deployment | `daily.start_date` |
| Daily schedule | 05:00 Eastern, every day | `schedule.daily`, `schedule.time_zone` |
| Reconciliation | Sunday, 06:00 Eastern, all supported quarters | `schedule.reconciliation` |
| SEC identity | Required organization/name and contact email | `sec.user_agent` |
| SEC request target | 3 requests/second, no bursts | `sec.requests_per_second` |
| Active SEC collectors | 1 across all application pipelines | `sec.max_active_collectors` |
| HTTP attempts | 5 total per request, including the first | `http.max_attempts` |
| Retry delay | Exponential with jitter, 2 s base and 120 s local cap; honor longer server delays | `http.retry_base_seconds`, `http.retry_cap_seconds` |
| Connection / read timeout | 15 s / 60 s; both bounded | `http.connect_timeout_seconds`, `http.read_timeout_seconds` |
| Native job retries | Disabled initially; no automatic retry of an ambiguous start | `jobs.replica_retry_limit` |
| Confirmed failed-stage replay | At most 1 automatic replay for transient failure | `orchestration.transient_replays` |
| Withdrawal approval | Required for every closed-quarter candidate that removes keys | `reconciliation.require_withdrawal_approval` |
| Versions | Required, explicit and pinned per workset | `etl.parser_version`, `etl.schema_version`, `worker.image_digest` |

The daily time is a scheduling choice, not a source-publication guarantee. The SEC describes daily
index processing as starting around 22:00 Eastern and normally taking several hours; the roughly
03:00 bulk-JSON rebuild is a different process. [SEC index timing][sec-access]
[SEC API bulk downloads][sec-api]

ADF owns the production schedules, configured with its supported Eastern time-zone identifier and
daylight-saving behavior. Container Apps Jobs has no independent schedule for these same runs.
[ADF time-zone scheduling][adf-schedule]

A requested server delay beyond the job's remaining runtime defers the work; it does not authorize
an early retry. Resource sizes, job runtime limits, retention, region, network access and alert
recipients are required deployment values, selected in the implementation plan and smoke test.

### 4.9 Identity, deployment and interfaces

Use managed identities for ADF management calls and worker access to Azure resources. Pin and
review permissions; do not place storage keys in worksets or source URLs. The SEC User-Agent is
required identification, not an SEC API credential. The implementation plan verifies identities
against the actual deployed management and data-plane operations. [ADF managed-identity calls][adf-web]

Proposed code and deployment boundaries:

```text
packages/sec-edgar-ingest/
  pyproject.toml         distribution and CLI name: sec-edgar-ingest
  src/sec_edgar_ingest/  discovery, downloader, parser, manifest, workflows, publisher, CLI
  tests/fixtures/       quarterly, daily, legacy, malformed and corrected index examples
conf/sec-edgar-ingest.yaml      typed configuration and environment-specific references
infra/azure/sec-edgar-ingest/   versioned resources, identities, jobs, pipelines and alerts
docs/runbooks/                 backfill, catch-up, approval, replay, rollback and incidents
```

The implementation plan chooses the infrastructure-as-code tool and supported SDK versions; this
draft does not invent an existing repository convention. Production deployment pins the image
digest and configuration revision. Trigger enablement is an explicit release step, not a side
effect of creating infrastructure.

## 5. Error handling

Named outcomes; the implementation maps them to structured errors and process exit codes:

- **Configuration:** missing SEC identity or range, reversed quarters, unsupported versions,
  non-positive limits, a request target at or above the published ceiling, or a second independent
  collector configuration. Refuse before external I/O.
- **Discovery:** malformed listing, inaccessible directory or untrusted URL. Do not advance its
  boundary or interpret the result as an empty directory.
- **Not yet available:** a listed source returns 404. Keep it pending and report it; do not mark
  it published or remove existing records.
- **Throttled / transient:** 429, retryable 5xx, timeout or connection failure. Apply the bounded
  retry policy and server delay; preserve state when attempts are exhausted.
- **Access blocked:** 403 or an explicit access-denial page. Halt SEC access for the run and alert;
  do not loop aggressively or rotate identities.
- **Invalid source:** HTML in place of an index, truncated bytes, unsupported header, malformed row,
  invalid date/path or conflicting duplicate keys. Quarantine, retain evidence and refuse publication.
- **Ownership lost:** stop issuing requests. A worker without current ownership cannot continue as
  the collector.
- **Execution unknown:** ambiguous job start or unresolvable execution status. No false success and
  no blind launch retry.
- **Publication conflict:** active pointer changed while building. Keep the candidate unreferenced
  and rebuild against current inputs; persistent conflict fails the stage.
- **Withdrawal pending:** retain the active generation and emit an approval request naming exact
  hashes. This is a distinct gated outcome, not successful reconciliation.

Guarantees rather than refusals:

- Repeated execution over the same source and versions creates no duplicate logical records.
- Invalid replacement data cannot empty or shrink the active catalog.
- A failed publication leaves the previous generation readable.
- A valid pointer survives a crash before ancillary processing-state updates.
- Historical failures remain visible even when later periods complete.

## 6. Testing

CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

**Exit criteria (CI):**

- **Discovery and coverage.** Quarter boundaries, leap days, valid empty listings, delayed files,
  a failed listing, a missed run and an outage spanning multiple quarters. Pending older sources
  remain discoverable, and a failed directory does not advance the checkpoint.
- **Parsing.** Quarterly and daily golden files produce the same row contract. Supported legacy
  paths preserve nullable accession numbers. Amendments remain distinct. Malformed rows, bad
  paths, HTML responses and conflicting duplicates fail closed.
- **Access.** Concurrent backfill, daily and reconciliation collectors share one budget; retries
  count toward it; lease loss and takeover cannot create overlapping request issuers. Check
  User-Agent, Retry-After handling, bounded attempts and the halt on access denial.
- **Replay.** Repeated inputs produce the same logical catalog. A parser-version change reads raw
  storage without SEC requests. Unchanged hashes skip unnecessary work. Partial completion resumes
  without losing earlier successful units.
- **Reconciliation.** Additions and field updates are recorded. Open-quarter absence does not
  withdraw. Closed-quarter withdrawal requires hash-bound approval. Stale daily replay cannot
  resurrect a withdrawn key, while a later quarterly reintroduction is recorded explicitly.
- **Publication.** Inject crashes before files finish, before pointer update and immediately after
  pointer update. Readers see only complete generations. Competing publishers cannot lose an
  update; a committed pointer repairs lagging processing flags.
- **Orchestration.** A successful start is not job success. Failed, timed-out and unknown executions
  propagate correctly; a missing or mismatched worker result cannot pass the stage. A gated
  reconciliation is not reported as complete.
- **Observability.** Reports include source gaps, no-new-source outcomes, per-quarter generations,
  version identifiers and recoverable error context.

**Integration tests:** use isolated Azure resources to exercise actual identities, job start/poll,
Storage coordination, conditional pointer updates and log delivery. A controlled SEC smoke test
is a deployment gate, not an ordinary CI dependency.

## 7. Exit procedure

**Phase 1: code and infrastructure, ending at the deployment checkpoint.**

1. Accept the ADR and this spec. Record the range, handoff date, SEC identity, environment and
   deployment settings that 4.8 leaves to implementation.
2. Build the shared worker, manifest, pipelines and tests. Keep all production triggers disabled.
3. Deploy to an isolated environment. Run fixture-based integration tests and fault injection.
4. Run a bounded live smoke test against one archived quarter and one already published daily
   index. Record byte counts, row counts, elapsed time, peak memory, image digest and request rate.
5. Replay both from raw storage with SEC access disabled. Confirm unchanged logical output and no
   duplicate records. Rehearse approval and rollback with corrected fixtures, not invented SEC data.

**Phase 2: baseline and scheduled operation.**

6. Deploy the reviewed image and configuration. Run the parameterized backfill, recording every
   source's result; unresolved gaps prevent a claim of complete baseline coverage.
7. Catch daily ingestion up from the handoff date, including overlap with the baseline. Enable the
   daily trigger after the catch-up result is accepted.
8. Run reconciliation manually once, resolve any gated candidates, then enable its weekly trigger.
9. Check the next scheduled runs against their durable reports and logs. Record that operational
   evidence separately from the earlier fixture and smoke-test results.

**Exit:**

- Every requested baseline unit is published, or the approved incomplete range is explicitly
  recorded; no silent gaps.
- Daily discovery catches up from an interrupted run without losing older work.
- Reconciliation applies safe changes and gates withdrawals as specified.
- The shared downloader, replay and publication failure tests pass.
- Production identities, alerts, runbooks and rollback procedure have been exercised.
- The release record names image/configuration versions and active quarter generations.

Code review need not wait for a future SEC filing. Scheduled-operation acceptance does require
observed scheduled executions; it is not inferred from a manual run.

## 8. Documentation and infrastructure

No deletion or migration of existing code is prescribed: no repository was inspected.

Document the service boundaries and source-to-output flow in the project README. The runbooks cover
initial backfill, missed daily runs, reconciliation approval, malformed-source quarantine, parser
upgrades, SEC throttling or blocks, ambiguous job starts and generation rollback. Include the
reader contract: resolve the active pointer; never scan all retained generations as current data.

Keep infrastructure, role assignments, job definitions, ADF pipelines, schedules and alerts under
version control. A release records the image digest and configuration revision. Any schema change
states whether consumers can read both versions before a pointer moves.

## 9. Chosen approach and rejected alternatives

- **Orchestration.** Chosen: ADF plus shared container jobs (R4–R5). A schedule-only container
  deployment remains a simpler alternative if its application-owned dependency and recovery logic
  is preferred; see the ADR.
- **Source handling.** Chosen: Python collection and immutable raw snapshots. Rejected: separate
  download/parsing implementations for quarterly and daily inputs, or ETL that fetches its own data.
- **Recovery.** Chosen: source-file checkpoints and exact snapshot references. Rejected: a single
  “last successful date” as the whole state model; it hides earlier gaps.
- **Corrections.** Chosen: quarterly reconciliation with conservative, explicit withdrawals.
  Rejected: daily-only appends, or interpreting any smaller response as an authoritative deletion.
- **Publication.** Chosen: complete quarter generations and a conditional active pointer.
  Rejected: in-place overwrite while readers scan a partition, or assuming Parquet supplies upserts.
- **Compute.** Chosen: containerized index ETL first. Distributed processing and a serving database
  wait for measured requirements rather than entering through an unspecified “ETL” step.

## 10. Rollout note

**The operational switch is trigger enablement, not the code merge.** Backfill is a bounded initial
campaign. Daily ingestion and reconciliation are ongoing operations, with different schedules but
one set of contracts. Do not approve complete historical coverage while the manifest still shows
unresolved requested units.

**Before deployment.** Reconfirm the SEC access and publication guidance, source formats across the
chosen range, and the Azure API, identity and time-zone behavior against the versions actually
selected. The supplied discussion and linked documentation are design inputs, not deployment-test
evidence.

**Deferred decisions.** Filing-text ingestion, JSON/XBRL ingestion, a serving layer, global
multi-quarter snapshot publication, distributed compute and a contractual freshness target each
need an explicit scope decision. None is implied by accepting this index-ingestion design.

**Change boundary.** A parser or schema change produces new processing identities and candidate
generations from retained inputs. A scheduler/runtime change preserves the storage and publication
contracts or supplies an explicit migration. A rollback changes active pointers; it does not erase
source history or retract data that consumers have already used.

[sec-access]: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
[sec-developers]: https://www.sec.gov/about/developer-resources
[sec-downloads]: https://www.sec.gov/about/webmaster-frequently-asked-questions
[sec-api]: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
[adf-schedule]: https://learn.microsoft.com/en-us/azure/data-factory/how-to-create-schedule-trigger
[adf-web]: https://learn.microsoft.com/en-us/azure/data-factory/control-flow-web-activity
[aca-jobs]: https://learn.microsoft.com/en-us/azure/container-apps/jobs
[adls]: https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-introduction
[tables]: https://learn.microsoft.com/en-us/azure/storage/tables/table-storage-overview
[aca-observability]: https://learn.microsoft.com/en-us/azure/container-apps/observability
