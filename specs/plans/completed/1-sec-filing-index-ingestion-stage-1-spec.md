# SEC filing-index ingestion — Stage 1 Investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce retained investigation evidence and an owner-accepted ready finding identifying a viable source/runtime combination under the approved Stage 1 contract.

**Architecture:** Review official provider documentation, inventory SEC sources with one bounded investigation issuer, retain representative original inputs, and run isolated Linux amd64 compatibility probes. Assemble a finding that distinguishes documented capabilities, observed results, owner decisions, assumptions and deployment checks; complete Stage 1 only after Lowell Mason accepts the exact ready-finding revision.

**Tech Stack:** Markdown/CSV/JSON evidence; SEC HTTPS directory metadata and indexes; Python 3.14 and a digest-pinned official Linux amd64 Python container; isolated pip dependency resolution; Azure SDK and Parquet compatibility probes; official SEC/Microsoft resource and API documentation. Bicep is the accepted deployment tool, but no infrastructure is authored here.

**Status: COMPLETE (2026-10-06)** — executed via subagent-driven-development; nothing deferred

Original plan written 2026-10-05. Completion covers the accepted bounded investigation; every effective deployment/worker check remains reserved. Controller retirement review/commit and final SDD archive are subsequent provenance actions, not accomplishments claimed here.

**Authority:** [Approved Stage 1 spec](../../completed/sec-filing-index-ingestion-stage-1-spec.md), accepted by Lowell Mason on 2026-10-05 at `321c93af78b54c7e63efbb0e69252c69a238fec6`; [roadmap](../../sec-filing-index-ingestion-roadmap.md), [parent design spec](../../sec-filing-index-ingestion-spec.md), [ADR](../../sec-filing-index-ingestion-adr.md). Parent contracts remain authoritative; this plan supplies investigation methods, not replacement safeguards.

**Completion provenance:** Stage 1 COMPLETE (2026-10-06); [accepted F1 finding](../../sec-filing-index-ingestion-stage-1-findings.md), accepted 2026-10-05, exact SHA-256 `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`; [authoritative stage stamp](../../completed/sec-filing-index-ingestion-stage-1-spec.md#9-rollout-note). Later stages remain unticked; resume requires the owner’s separate request.

**Completion restriction:** The line above takes effect only after all investigation tasks complete, the ready finding is accepted by revision/date and the authoritative Stage 1 stamp is recorded. Writing or approving this plan does not tick Stage 1. Accepting a not-ready report does not discharge the readiness exit. Later-stage transitions remain owner-initiated by resuming the roadmap.

## Global Constraints

- Repository: `/Users/lowell/Projects/sec-edgar`; owner and decider: Lowell Mason.
- Workload remains filing indexes: historical quarterly backfill, ongoing daily ingestion, metadata ETL and reconciliation. One implementation package is `packages/sec-edgar-ingest/`, distribution/CLI `sec-edgar-ingest`, import `sec_edgar_ingest`; see parent §§2, 4.1, 4.9 and ADR Decision.
- Intended historical range: 2010 Q1 through the open quarter, inclusive. Initial development range: 2015 Q1 through the open quarter, inclusive. End-quarter rule: Resolve and pin the end quarter at each run's start.
- Daily handoff: 2026-10-01, retaining baseline overlap under parent §4.2.
- SEC User-Agent: Lowell Mason sec-edgar-ingest mason.lowell@mac.com.
- Azure target: A new dedicated resource group in an existing subscription. Region order: eastus, then eastus2, then centralus.
- Networking: Public HTTPS endpoints, managed identities, scoped roles, anonymous blob access disabled. Infrastructure as code: Bicep.
- Python/container candidate: Python 3.14; Linux amd64 container.
- Initial compute candidate: General-purpose Consumption workload profile; 2 vCPU and 4 GiB RAM. Initial execution settings: One replica; parallelism 1; completion count 1; replica timeout 3,600 seconds.
- Initial storage candidate: Standard general-purpose v2; hierarchical namespace enabled; Hot tier; ZRS.
- Ingestion-artifact retention: Indefinite during initial development: raw snapshots, observations, generations, manifests, approvals, quarantine evidence and run reports.
- Operational-log retention: 90 days. Alert owner and destination: Lowell Mason; mason.lowell@mac.com.
- Accepted parent §4.8 defaults: daily 05:00 Eastern; Sunday reconciliation 06:00 Eastern; 3 requests/second, no bursts; 1 active collector; 5 total HTTP attempts; 2 s exponential/jitter base and 120 s local cap while honoring longer server delays; 15 s connection / 60 s read timeout; zero native job retries; at most 1 confirmed-transient-failure replay. Parent §§4.3, 4.8 and §5 govern all SEC investigation access.
- Preserve existing local deletions in `packages/sec-edgar-index-ingest/` and the untracked roadmap. Preserve any additional execution-time changes. No broad staging, stash, reset, restoration or package repair.
- Read-only inspection, bounded source/archive inspection and isolated dependency/container probes are authorized. No production ingestion modules, parser/catalog implementation, golden parser tests, workspace repairs, Bicep resource definitions, provisioning, publication or trigger activation.
- No resource-profile comparison. Actual worker memory/runtime and live integrated Azure behavior belong to Stage 7. A local probe has no deployment authority.

## Evidence design and file ownership

All execution outputs below are relative to the repository root. Each has one responsibility. The finding links the evidence; it must remain readable without this planning conversation.

| Path | Responsibility |
|---|---|
| `specs/sec-filing-index-ingestion-stage-1-findings.md` | Self-contained conclusion, boundary, decisions, evidence, limitations and owner acceptance |
| `specs/evidence/sec-filing-index-ingestion/stage-1/index.csv` | Evidence index; one row per independently supportable claim |
| `specs/evidence/sec-filing-index-ingestion/stage-1/baseline.md` | Repository status, revisions, protected-change hashes and scope drift |
| `specs/evidence/sec-filing-index-ingestion/stage-1/decisions.md` | Accepted settings and concrete environment/deployment choices |
| `specs/evidence/sec-filing-index-ingestion/stage-1/access-window.md` | Single issuer, other owner traffic, request/byte/time budgets and access history |
| `specs/evidence/sec-filing-index-ingestion/stage-1/provider-review.md` | Versioned official documentation findings and retrieval failures |
| `specs/evidence/sec-filing-index-ingestion/stage-1/provider/` | Retained provider extracts/snapshots with URL/time and hash |
| `specs/evidence/sec-filing-index-ingestion/stage-1/requests.csv` | Every SEC attempt, including listing, failure and retry requests |
| `specs/evidence/sec-filing-index-ingestion/stage-1/listings/` | Exact directory response bodies and metadata sidecars |
| `specs/evidence/sec-filing-index-ingestion/stage-1/quarterly.csv` | Every requested quarter, development membership, actual discovered sources and outcome |
| `specs/evidence/sec-filing-index-ingestion/stage-1/daily.csv` | Handoff/outage-recovery listing coverage, published files and gaps |
| `specs/evidence/sec-filing-index-ingestion/stage-1/specimens/` | Original source bytes and metadata; content-addressed filenames preserve archive extension |
| `specs/evidence/sec-filing-index-ingestion/stage-1/source-assessment.md` | Inspected format/path families, coverage limits, volume and temporary-space assessment |
| `specs/evidence/sec-filing-index-ingestion/stage-1/runtime/` | Exact base/platform record, direct requirements, hashed resolution, probe inputs/scripts/logs/results |
| `specs/evidence/sec-filing-index-ingestion/stage-1/azure-contracts.md` | API versions, polling/correlation and operation-level actor permissions |
| `specs/evidence/sec-filing-index-ingestion/stage-1/schedules.md` | Eastern serialization and expected DST behavior |
| `specs/evidence/sec-filing-index-ingestion/stage-1/discrepancies.csv` | Evidence conflict, affected contract, blocking flag, disposition and acceptance |
| `specs/evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md` | Explicit reserved integrated checks and passing evidence required later |
| `specs/evidence/sec-filing-index-ingestion/stage-1/readiness-checklist.md` | Requirement-to-evidence coverage and acceptance gate results |

Temporary probe installations, wheel caches and container output staging go in a new `/private/tmp/sec-edgar-stage-1-*` directory. Retain only scripts, inputs, resolution metadata and reports in `runtime/`; no environment or production image is added to workspace packages. Do not overwrite prior evidence: use receipt-time/hash suffixes and append attempt records.

Evidence-index columns: `evidence_id,claim,category,method,url_or_artifact,accessed_or_received_at_utc,versions,result,limitation,sha256,command,exit_code`. Categories are exactly **Verified documentation**, **Source/probe observation**, **Owner decision**, **Assumption**, **Reserved Stage 7 check**. Split a mixed claim across rows. Documentation needs a direct official URL and retrieval time; source bytes need receipt metadata and hash; probes need complete commands, outputs and exit codes; decisions need owner/date/revision. An assumption needs an impact, owner and resolution obligation. Do not classify a retrieval error as a verified fact.

Each task ends with a reviewable deliverable and checkpoint. Steps are short actions; inventory/sampling steps repeat per directory/specimen. There is no library implementation test cycle in this investigation. Evidence checks and isolated assertions replace red/green production tests. Execute in order: later conclusions depend on earlier observations. Parallel agents must not create concurrent SEC issuers.

## Planning-time official review (2026-10-05)

These documentation checks were made while writing the plan. They establish methods and candidates only. Execution must re-access the selected versions, retain evidence and record precise timestamps. No archive sizes from brainstorming, live source outcomes, image digests or successful local probes are carried forward as verified execution evidence.

| Topic | Verified documentation / limitation | Direct official reference |
|---|---|---|
| SEC discovery and corrections | Directory metadata includes HTML/XML/JSON; full indexes bridge the current quarter to daily indexes. Nightly work begins around 22:00 ET; full/quarterly rebuilds incorporate later corrections weekly. No historical-daily-retention or publication SLA inferred. | [Accessing EDGAR](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) |
| SEC owner-wide access | Published ceiling is 10 requests/s per user across machines. The accepted lower target and single-issuer policy remain application decisions. | [Developer resources](https://www.sec.gov/about/developer-resources) |
| Jobs operations | Non-preview 2026-07-01 create/update, start, execution GET and execution list references exist. Start documents 200 execution output and 202 Location/Retry-After. Documentation does not prove deployed response/correlation behavior. | [Create/update](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/jobs/create-or-update?view=rest-resource-manager-containerapps-2026-07-01), [Start](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/jobs/start?view=rest-resource-manager-containerapps-2026-07-01), [Execution GET](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/job-execution/job-execution?view=rest-resource-manager-containerapps-2026-07-01), [List](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/jobs-executions/list?view=rest-resource-manager-containerapps-2026-07-01) |
| Jobs states | GET enumerates Running, Processing, Stopped, Degraded, Failed, Unknown, Succeeded; individual descriptions do not fully define terminal semantics. | [Execution GET](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/job-execution/job-execution?view=rest-resource-manager-containerapps-2026-07-01) |
| Jobs retry/authority | Zero retries is supported; maintenance guidance recommends at least one. Start permission can override templates and use attached identities. Built-in Job roles include broad actions; review exact needed permissions. | [Jobs](https://learn.microsoft.com/en-us/azure/container-apps/jobs) |
| ADF Web | Default 202 handling follows Location with GET; managed-identity ARM audience is `https://management.azure.com/`. HTTP-operation completion is distinct from worker completion. Web output is limited to 4 MB and requires JSON. | [Web activity](https://learn.microsoft.com/en-us/azure/data-factory/control-flow-web-activity) |
| Eastern scheduling | `Eastern Standard Time` observes DST; documented local timestamp format has no Z. Day-or-higher recurrence supports DST adjustment. | [Schedule triggers](https://learn.microsoft.com/en-us/azure/data-factory/how-to-create-schedule-trigger) |
| Coordination primitives | Finite blob leases allow 15–60 s. Table ETag mismatch returns 412; wildcard If-Match bypasses concurrency. Neither primitive provides a Blob/Table transaction or fences external SEC traffic. | [Lease Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/lease-blob), [Update Entity](https://learn.microsoft.com/en-us/rest/api/storageservices/update-entity2) |
| ADLS multi-protocol | Blob and DFS can access the same data, with restrictions on mixing write APIs for an individual file and on block operations. | [ADLS known issues](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-known-issues) |
| Temporary storage | Apps documentation lists 8 GiB for replicas above one vCPU, with ephemeral lifetime. Applicability/effective capacity for selected Jobs must be resolved without calling it measured worker capacity. | [Storage mounts](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts) |
| Resource support | Consumption, GPv2/redundancy, image pulls and log retention have provider capability documentation. Product-region page retrieval supplied no usable service matrix in this review; shortlist eligibility is unresolved here. | [Profiles](https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview), [Accounts](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview), [Redundancy](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy), [Region matrix](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/table/), [Image pulls](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity-image-pull), [Log options](https://learn.microsoft.com/en-us/azure/container-apps/log-options), [Retention](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure) |
| Runtime candidates | Microsoft pages identify Identity 1.26.0, Blob 12.31.0 and Tables 12.7.0 candidates. Arrow installation and official Python image references are available; this review selects no combined runtime pins. | [Identity](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python), [Blob](https://learn.microsoft.com/en-us/python/api/overview/azure/storage-blob-readme?view=azure-python), [Tables](https://learn.microsoft.com/en-us/python/api/overview/azure/data-tables-readme?view=azure-python), [Arrow](https://arrow.apache.org/docs/python/install.html), [Python image](https://hub.docker.com/_/python?tab=description) |

### Task 1: Establish baseline, decision register and access boundary

**Files:** Create `baseline.md`, `decisions.md`, `access-window.md`, `index.csv`, `discrepancies.csv` under the evidence root above.

**Interfaces:** Consumes approved spec/parent/ADR/roadmap and current worktree. Produces protected baseline, pinned investigation endpoint, recorded decisions and an exclusive bounded access window for Task 2.

- [x] **Step 1: Capture the repository baseline without mutation.** Run from the repository:

  ```bash
  git status --porcelain=v1
  git rev-parse HEAD
  git show 321c93a:specs/sec-filing-index-ingestion-stage-1-spec.md
  git diff -- specs/sec-filing-index-ingestion-stage-1-spec.md
  git ls-files
  rg --files --hidden -g '!.git' -g '!.venv'
  shasum -a 256 specs/sec-filing-index-ingestion-roadmap.md pyproject.toml
  ```

  Record outputs/exit codes and hashes of every changed/untracked file, including roadmap bytes. Expected initial HEAD is approval commit `321c93a`; four index-ingest files are deleted and roadmap is untracked. Record drift rather than forcing this state. Read package configs/scaffolds and root CLI configuration; identify Stage 2 alignment needs without changing them.

- [x] **Step 2: Initialize evidence registers using the schemas in this plan.** Discrepancy columns are `id,claim,evidence_ids,parent_reference,blocking,proposed_resolution,owner,accepted_revision,accepted_date,status`. Use status `open`, `resolved` or `reserved_stage_7`; a required input left unchosen is open/blocking, not a deferral.

- [x] **Step 3: Pin evaluation date and end quarter.** Use America/New_York for the run-start date. Store endpoint once and enumerate quarter ordinals inclusively. On 2026-10-05, endpoint is 2026 Q4, yielding 68 intended and 48 development units; on another date recompute both counts and latest closed quarter. Keep these as requested units, separate from discovered source units.

- [x] **Step 4: Record every approved §4 input and parent acceptance, then request the missing concrete decisions as one batch.** Obtain tenant/subscription UUIDs and cloud, proposed dedicated resource-group name, environment/naming scheme, deployment operator identity and authority, registry location/type and permission mode, pull identity choice, rollback digest retention/availability policy, and deployment-tool prerequisites. Record owner confirmation of these choices; never substitute example UUIDs or a guessed default subscription. New resource principal IDs remain Stage 7 deployment records. Registry and tooling may be proposed during Tasks 4–5, but all concrete choices must be accepted before readiness.

> Deviation: Concrete production choices were deliberately left open at the Task 1 checkpoint and resolved by the exact R3 batched owner acceptances and Task 5 owner checkpoint before readiness; no answer was inferred.

- [x] **Step 5: Establish one investigation issuer and account for other owner traffic before SEC access.** Record issuer/operator, coordination method, exclusive sampling window and owner traffic allocation. Proposed bounded window: at most 45 minutes, 240 total HTTP attempts including retries, 512 MiB received and 12 initial complete source specimens; request starts spaced at least 1/3 second, sequential, no bursts. Reduce the rate if other owner traffic requires it. This is an investigation limit, not a production settings revision. Pause at the first exhausted budget, new format family or required additional sampling; record a bounded continuation window before resuming. No second issuer, independent retry budget or identity rotation. Honor longer Retry-After; halt on 403/access-denial content. Record unresolved traffic allocation as blocking; independent documentation work can continue.

> Deviation: The owner confirmed all other SEC traffic paused; only the controller issued requests, and the novel daily family caused an explicit pause and accepted bounded continuation before further sampling.

**Checkpoint:** Baseline protections and decision statuses are reviewable. No live SEC request proceeds without the recorded traffic/window boundary. No readiness is inferred from spec approval.

### Task 2: Inventory requested quarterly and relevant daily sources

**Files:** Create `requests.csv`, `quarterly.csv`, `daily.csv`, `listings/`; update access and evidence registers.

**Interfaces:** Consumes Task 1 endpoint/window. Produces exhaustive requested-quarter accounting, actual discovered URLs, representations, daily retention observations and specimen candidates for Task 3.

- [x] **Step 1: Define row contracts before requesting directories.** Quarterly columns: `quarter,development_subset,requested_at,listing_evidence_id,discovered_url,representation,listed_size,listed_size_unit,source_status,selection_reason,gap_id`. Keep one summary outcome per requested quarter plus child representation rows. Daily columns: `directory_period,listing_evidence_id,discovered_url,listed_date,representation,handoff_relation,outcome,gap_id`. Request ledger columns: `attempt_id,issuer,start_utc,end_utc,url,status,received_bytes,body_sha256,response_headers_artifact,exit_code,retry_reason,next_allowed_at,outcome`. Sidecars preserve URL, UTC receipt, HTTP status, headers, transport/content encoding, redirect chain, schema, discovered children and selection decision. Avoid automatic client retry/redirect behavior that escapes the shared attempt ledger.

- [x] **Step 2: Discover the full-index hierarchy from official roots.** Start at `https://www.sec.gov/Archives/edgar/full-index/index.json`; follow validated child entries through years and quarters within the requested range. Inspect current-quarter root representations too; record the actual relationship between root and year/QTR full indexes rather than assuming they are equivalent. Resolve canonical HTTPS SEC URLs only within the accepted Archives index families. Capture exact listing bytes and hash before inspecting JSON. If JSON is absent or malformed, inspect the documented XML/HTML representation under the same budget and record the fallback/schema. Generated quarter labels are allowed for expected coverage; generated file URLs are not evidence of availability.

- [x] **Step 3: Inventory every intended quarter and mark the development subset.** Repeat listing capture per unit and enumerate master representations/extensions, sizes and dates. Record `available`, `valid_no_source`, `discovery_failed`, or `listed_source_pending` based on evidence. A missing/inaccessible directory is not a successful empty listing; a listed file's 404 is pending. Follow parent §§4.2–4.4, retain all failed outcomes and do not infer withdrawals. Record selected representation per observed family; no need to support optional codecs when an inspected alternative covers the source.

- [x] **Step 4: Inspect daily discovery from the handoff and across outage boundaries.** Start at `https://www.sec.gov/Archives/edgar/daily-index/index.json`; follow its actual hierarchy. Inspect current and preceding quarters, the handoff quarter, available year directories throughout the intended range and at least the first/last available quarter of each discovered historical year. Record which historical directories exist and which remain uninspected. If the proposed supported outage horizon exceeds observed daily availability, inspect the relevant additional directories in another bounded window or obtain an explicit gap resolution. Discover dates from listings; never manufacture weekend/holiday filenames. Keep 2026-10-01 as a required inspection even if absent, and select an already-published daily body from a successful listing.

- [x] **Step 5: Check inventory completeness against the pinned requested set.** Independently recompute inclusive quarter count; verify no duplicate/missing quarter summary and correct 2015 Q1 subset boundary. Cross-check each successful row against retained child entries. Record receipt-date-sensitive open-quarter status. Record every gap and its effect on supported range/recovery; obtain owner acceptance of an actual range/contract revision if needed rather than calling absence harmless.

> Deviation: The incomplete-read chain was fixed and checked before Task 2 acceptance; no failed or incomplete listing was recast as complete.

**Checkpoint:** All requested quarters have evidence-linked outcomes; daily discovery has a documented historical observation boundary. Listings alone do not establish format support or historical ingestion coverage.

### Task 3: Retain specimens and assess formats, paths and space

**Files:** Create `specimens/`, `source-assessment.md`; update `quarterly.csv`, `daily.csv`, discrepancies and index.

**Interfaces:** Consumes discovered sources. Produces format/representation support boundary, original-byte samples, archive decoding inputs for Task 4 and bounded volume/space assessment.

- [x] **Step 1: Choose the bounded specimen matrix from actual inventory.** Include 2010 Q1, 2015 Q1, latest closed and open quarter; handoff daily and already-published daily; closed/open transition daily pair where listed; a year-transition pair; every distinct selected format/legacy path family exposed by inventory or inspection. Multiple samples can cover one requirement. For absent handoff/transition files record absence and inspect the nearest listed files on both sides; seek explicit accepted resolution of unmet required coverage. Expand beyond the initial 12 only through a recorded continuation budget. Do not download all representations speculatively.

> Deviation: Ten body receipts satisfied the selected coverage matrix under the accepted continuation; no global family or nullable-accession golden coverage is claimed.

- [x] **Step 2: Retain original bodies and receipt evidence.** Each archive stays an archive named by hash plus original extension; decoded content is a separate derivative. Preserve HTTP transport bytes/content-encoding interpretation explicitly: use Accept-Encoding identity where supported and disable transparent body decoding in the acquisition tool. Hash the bytes actually retained; preserve advertised Content-Length and compare when applicable. Record User-Agent, validators, MIME type, received byte count, UTC receipt, status and body hash. Quarantine HTML/truncation/error bodies as evidence; they are not source specimens. Use bounded reads and parent failure rules.

- [x] **Step 3: Inspect archives safely and retain member reports.** List member names, codec, compressed/expanded sizes and checksums; reject unexpected members, traversal/absolute paths, excess count or expansion before extraction. Decode to the isolated directory, not repository package paths. Proposed investigation expansion cap is 512 MiB per specimen; an over-cap source remains unexamined pending a bounded revision. Record actual expanded byte count and derivative hash, integrity-check output and exit code. Do not overwrite archive bytes with `master.idx`.

- [x] **Step 4: Inspect source text and legacy conventions without building the parser.** Record encoding evidence and decoding failures (never use lossy replacement), BOM, newline distribution, header/column separator, representative raw rows/fields/paths and observed minimum/maximum filing dates with the inspection method. Inspect early-range path families, accession-shaped and non-extractable paths; preserve nullable accession under parent §4.4. If a complete format-family scan is not performed, state the inspected-row boundary. Additional bodies may be needed when metadata cannot reveal format changes. No unexamined family becomes supported merely by analogy; later golden parser verification remains required under parent §6.

> Deviation: A novel daily header/date/newline family required the accepted continuation; original bytes and cross-quarter filing dates were preserved. Initial misnamed fixture diagnostics were overwritten; the limited evidence loss remains disclosed, with corrected red/green receipts retained.

- [x] **Step 5: Reconcile raw representation with parent §4.5 examples.** Record selected archive extension/member and original-byte raw naming. Parent `master.idx` is an example and does not permit storing decoded content as original bytes. If a chosen durable naming scheme changes an accepted contract, record the proposed revision and owner acceptance before readiness. Otherwise explain how original extension/format metadata and derivative paths preserve the contract.

> Deviation: The annotation helper initially mishandled historical daily CSV rows; the exact frozen Task 2 rows and order were restored, versioned, and independently checked before acceptance.

- [x] **Step 6: Calculate bounded volume and disk requirements.** Sum listed quarterly sizes by representation with explicit units/unknowns; use observed download sizes separately. Report largest listed and largest retained source, expansion ratio per inspected archive, sample count and uninspected-tail uncertainty. Calculate temporary peak as simultaneous original archives + expanded derivatives + planned observation/output scratch + candidate-generation scratch + installer/runtime/log reserve. Identify which terms are measured and which are assumptions; recommend bounded source units without designing the worker. Compare with documented candidate temporary capacity, never call it a measured 4 GiB-memory or 3,600-second-runtime fit. Blocking incompatibility requires an accepted setting revision; actual memory/runtime belongs to Stage 7.

> Deviation: The one-unit space model uses measured inputs plus explicit scratch/reserve assumptions; documented 8 GiB applicability remains an assumption and actual worker fit stays reserved for Stage 7.

**Checkpoint:** Every supported selected representation/family has retained evidence; unknowns/gaps have explicit dispositions. Hashes independently recompute with `shasum -a 256` on each original and derivative. Directory size estimates are not expansion or processing measurements.

### Task 4: Prove an exact isolated Python/container dependency combination

**Files:** Create `runtime/base-image.json`, `runtime/requirements.in`, `runtime/requirements.lock`, `runtime/dependency-matrix.csv`, `runtime/probe.py`, `runtime/commands.md`, `runtime/results/`; update index/discrepancies.

**Interfaces:** Consumes Task 3 formats and specimen bytes. Produces exact reproducible base/runtime pins, dependency/wheel metadata and retained successful compatibility results, or a blocking failure.

- [x] **Step 1: Inspect tool prerequisites outside the workspace.** Record `docker version`, `docker buildx version`, `uv --version`, `az version`, and `az bicep version` when installed, with exit codes. Missing tools are evidence, not permission to install or repair packages. Use an available isolated container facility; if none can run Linux amd64, record the runtime proof as blocked. Native macOS/arm64 imports alone do not satisfy this task.

> Deviation: Local Docker was absent; the owner explicitly accepted the bounded temporary ACR Tasks setup exception. Azure CLI 2.90.0 was installed/authenticated under separate authorization; Bicep remained absent.

- [x] **Step 2: Select and inspect one exact Python 3.14 patch image.** Resolve an official Debian slim Python tag to immutable registry manifest and Linux amd64 child digest using `docker buildx imagetools inspect` and retain its output. Record tag, registry, manifest/child digest, OS variant and libc, `sys.version`, implementation/ABI (`sysconfig.get_config_var('SOABI')`), architecture and installer versions. Re-run by digest with `--platform linux/amd64`; do not select `latest`. Label emulated amd64 as such and do not infer production performance. Exact patch/digests are outputs of investigation, not invented pins in this plan.

> Deviation: Official registry/publisher metadata and retained SDK/API requests replaced unavailable local Docker inspection; immutable Linux amd64 child digest and exact platform pins were retained.

- [x] **Step 3: Resolve a minimal direct dependency set in that image.** Start with documented Identity 1.26.0, Blob 12.31.0 and Tables 12.7.0 candidates; select an exact SEC HTTP client and PyArrow version from current publisher package metadata. Use synchronous requests unless selected operations justify async dependencies. Include azure-storage-file-datalake only if the recorded operation map requires DFS APIs; record why omitted otherwise. Freeze exact direct pins into `requirements.in`, resolve all transitives into a hash-locked `requirements.lock` with the recorded installer version, and preserve downloaded artifact hashes/metadata. Matrix columns: `distribution,version,direct_or_transitive,requires_python,artifact_filename,wheel_tags,sha256,source_url,install_result,import_result,limitation`. Cover cryptography/cffi, Azure core/MSAL and Parquet native artifacts when resolved. A package minimum version is insufficient evidence; if a source build is needed record build prerequisites and prove it in the selected image or select a supported wheel combination.

- [x] **Step 4: Reinstall the lock in a fresh container, not the resolver environment.** Bind evidence read-only as `/evidence`, bind a new isolated output directory as `/out`; record complete expanded commands, stdout/stderr and exit codes. Commands use the selected digest and exact installer pins recorded in `base-image.json`/`commands.md`, never an unconstrained tag. Run `python -m pip install --require-hashes -r /evidence/runtime/requirements.lock`, `python -m pip check`, `python -m pip inspect`, `python -m pip debug --verbose`, and `python /evidence/runtime/probe.py`. Expected install/check/probe exit code: 0; retain nonzero results too. No `uv sync` at repository root. Install is networked dependency access, not an Azure authentication test.

> Deviation: Fresh uncached ACR Tasks contexts replaced local read-only bind mounts; frozen input hashes and separate export receipts prove retained inputs/results. The first CLI command failed locally on unsupported arguments and submitted no task.

- [x] **Step 5: Run this offline import/Parquet probe and decode each selected archive separately.** Save the following complete core probe as `runtime/probe.py`; inputs are synthetic compatibility rows, not normalized SEC data:

  ```python
  import importlib
  import json
  import platform
  import sys
  import sysconfig
  from importlib.metadata import version
  from pathlib import Path

  import pyarrow as pa
  import pyarrow.parquet as pq

  matrix = Path('/evidence/runtime/dependency-matrix.csv').read_text()
  modules = ['azure.identity', 'azure.storage.blob', 'azure.data.tables']
  if 'azure-storage-file-datalake,' in matrix:
      modules.append('azure.storage.filedatalake')
  for module in modules:
      importlib.import_module(module)
  direct = Path('/evidence/runtime/requirements.in').read_text().splitlines()
  installed = {}
  for line in direct:
      line = line.strip()
      if line and not line.startswith('#'):
          name, pin = line.split('==')
          assert version(name) == pin, (name, pin, version(name))
          installed[name] = pin
  assert sys.version_info[:2] == (3, 14)
  assert platform.machine() in ('x86_64', 'amd64'), platform.machine()
  rows = pa.table({'probe_id': [1, 2], 'text': ['SEC', 'café'],
                   'optional': pa.array([None, 'x'], type=pa.string())})
  target = Path('/out/roundtrip.parquet')
  pq.write_table(rows, target)
  restored = pq.read_table(target)
  assert restored.equals(rows)
  print(json.dumps({'python': sys.version, 'machine': platform.machine(),
                    'abi': sysconfig.get_config_var('SOABI'),
                    'installed': installed, 'parquet_roundtrip': 'passed'}))
  ```

  Import the chosen HTTP-client module with a separate `python -c` command; it must make no requests. For selected ZIP use `python -m zipfile -t` and the bounded member inspection from Task 3 in the fresh container. For selected gzip use `gzip -t` if available plus bounded decompression; for another codec use its documented exact decoder and retain commands/exit codes. Compare decoded hashes to Task 3 derivatives. Plain `.idx` needs a recorded no-archive decision and exact-byte/encoding check. Include every selected codec; optional unselected codecs remain unsupported. Do not implement SEC row parsing/catalog publication in this probe.

- [x] **Step 6: Repeat reproducibility verification and record limits.** Fresh-container installation plus imports, selected-archive decoding and Parquet round trip must all pass for one exact combination. Retain failed candidates with discrepancy resolutions. Distinguish base-image digest from a future built worker/release digest. Include registry choice, pull authorization requirements, rollback-image availability decision and exact deployment tool versions/prerequisites in the decision record, without building/pushing a worker or accessing deployed resources.

> Deviation: Actual ca1 failed during ACR dependency scanning on FROM --platform grammar; ca2 resolved and ca3/ca4 independently validated the corrected pinned context. All four accepted runs are retained; temporary registry/group deletion and absence were verified.

**Checkpoint:** The combined Linux amd64/Python 3.14 matrix is supported by actual successful isolated outputs with hashes, commands and exit codes. No successful Azure data access, production worker capacity or parser coverage is implied.

### Task 5: Resolve versioned Azure capability, permissions and schedules

**Files:** Create `provider-review.md`, `provider/`, `azure-contracts.md`, `schedules.md`, `stage-7-checks.md`; update decisions and discrepancies.

**Interfaces:** Consumes accepted architecture/settings and source/runtime limits. Produces documented selected API/tool versions, identity/operation matrix, schedule expectations and explicit deployment obligations for the readiness finding.

- [x] **Step 1: Reverify and retain official evidence for the selected operation versions.** Use planning references above as starting URLs. For each resource record resource type, exact version, operation, method/path, response schema, source URL/time and any unsupported field. Select one consistent non-preview Jobs family for create/start/execution GET/list (2026-07-01 is a documented candidate); record any justified departure. Resolve ADF factory/pipeline/trigger versions from [pipeline reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.datafactory/factories/pipelines) and [trigger reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.datafactory/factories/triggers). Resolve Storage account/blob/table resource and service `x-ms-version` choices from [Storage reference](https://learn.microsoft.com/en-us/azure/templates/microsoft.storage/storageaccounts) and selected SDK implementation metadata; management versions and data-plane versions are separate columns. Include managed environments, identities/role assignments, registry, Log Analytics workspace/tables, diagnostic settings, action groups and selected alert resource types via their official Microsoft resource references. Record exact Azure CLI/Bicep versions required; no resource definitions or deployment are created. A missing reference/version remains unresolved, not guessed.

> Deviation: A project-aware uv Ruff attempt failed in the broken root editable build and created task-local .venv/lock artifacts; only proven task-created artifacts were removed, with receipts. No workspace repair or lint pass is claimed.

- [x] **Step 2: Write the start/correlation decision table.** Separate ARM start acceptance/async completion, exact execution state and matching durable worker-result validation. Record 200 execution-reference extraction, 202 Location/Retry-After handling, approved host/path/token audience, and ADF `turnOffAsync` choice supported by the selected design. If ADF's async output cannot prove exact correlation, require operator recovery and Stage 7 evidence rather than selecting the latest execution. Correlation includes execution id, ADF run id, command/attempt, workset and image digest. Timeout/unknown id is `execution_unknown`, never an automatic launch retry. List-by-time alone cannot prove identity. Record documented request/async limits separately from application polling settings; Jobs event `pollingInterval` is not ADF execution polling. Proposed bounded status polling: 30 s base, honor longer server delay, explicit 4,200 s application observation deadline including the 3,600 s replica allowance; classify deadline/unknown outcome conservatively and seek owner acceptance of this new setting. No observed 200/202 shape is claimed until Stage 7.

- [x] **Step 3: Map all seven documented states conservatively.** Running/Processing continue bounded observation; Succeeded is only a candidate success requiring the exact matching successful durable result. Failed is failed; Stopped is unsuccessful; Degraded/Unknown remain uncertain unless authoritative selected-version evidence resolves them. Unknown enum, unavailable GET or deadline cannot pass; no uncertain state authorizes transient replay. Record per-state documented meaning, policy decision and Stage 7 check. Confirmed transient failure may use at most the accepted one replay with durable workset/attempt handling; do not invent idempotency from start response semantics.

- [x] **Step 4: Produce the actor/operation/resource-scope permission matrix.** Columns: actor, identity type, token audience, exact API/operation, management Actions or data DataActions, role/custom-role choice, assignment scope, network prerequisite, evidence and Stage 7 proof. Review [Storage Entra authorization](https://learn.microsoft.com/en-us/rest/api/storageservices/authorize-with-azure-active-directory), [ACR roles](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-rbac-built-in-roles-overview) and image-pull docs. Required actor coverage:

> Deviation: The owner accepted worker approval bookkeeping and the human approval boundary in exact R3/F1 records; scoped reviews corrected role-union denial claims and preserved hash-bound application safeguards.

  | Actor | Required operation coverage |
  |---|---|
  | ADF managed identity | Job read/start, exact execution GET/list and necessary async-operation read; durable JSON result Blob read with Storage audience `https://storage.azure.com/`; separate ARM `https://management.azure.com/` audience |
  | Collector/worker managed identity | Raw/workset/result/quarantine/generation Blob or DFS read/write; lease acquire/renew/release; source/attempt/pointer/approval Table read and conditional write; explicit container/table scopes |
  | Registry pull identity | Repository/image pull by digest; permission-mode-specific role and registry token audience; registry ARM-token authentication prerequisite where applicable |
  | Reader | Active-pointer Table read and manifest/data Blob read; document scope limitations for table/container granularity |
  | Approval/rollback operator | Read exact candidate evidence and write approved records/pointer operations under the application contract; do not describe RBAC alone as enforcing hash-bound approval |
  | Deployment/role-assignment operator | Resource creation/update, provider-registration requirements and role-assignment authority at the chosen scopes; separate management authority from data authority |

  Verify Actions/DataActions against official definitions, not role names alone. Avoid using broad Jobs role wildcards as least-privilege proof. Start authority can execute overrides using attached identities; record the resulting trust boundary. Resolve identity type and concrete operator authority before ready acceptance; actual new principal IDs and effective authorization remain reserved.

- [x] **Step 5: Record Storage/network/resource/log limits.** Review lease durations/renewal/break semantics and conditional Table writes (no wildcard If-Match for CAS); retain parent takeover/in-flight requirements because blob leases do not fence SEC requests. Review DFS/Blob write restrictions, choosing an API per object write lifecycle; determine DFS dependency need for Task 4 and repeat that probe if the selection changes. Verify GPv2 HNS/Hot/ZRS and Table coexistence, chosen regional service capability, Consumption Jobs CPU/memory eligibility and temporary storage applicability without profile comparison. If regional matrix is inaccessible, retain the failed retrieval and use another current official Microsoft source or leave it unresolved. Product support is distinct from subscription registration, Jobs profile eligibility, quota, capacity and policy. Record public HTTPS paths for worker SEC/Storage/Entra/registry/telemetry and ADF ARM/results, DNS/TLS/egress and firewall implications; managed identity does not bypass network controls. Select log routing and relevant tables with 90-day operational retention, alert resource/API and destination; neither retention configuration nor docs prove delivery.

- [x] **Step 6: Record Eastern serialization and both DST transitions.** Select `Eastern Standard Time`, daily Day interval 1 with hours `[5]`/minutes `[0]`, weekly Week interval 1 with Sunday hours `[6]`/minutes `[0]`. Record local `startTime`/`endTime` format `yyyy-MM-ddTHH:mm:ss` without Z for this zone; monitoring query timestamps are UTC. Keep production triggers disabled in later deployment; this task authors no trigger definition. Expected values for local conversion checks:

  | Local date/time | UTC daily 05:00 | UTC Sunday 06:00 |
  |---|---|---|
  | 2026-03-07 before spring change | 10:00 | Standard-time expectation 11:00 |
  | 2026-03-08 after spring change | 09:00 | 10:00 |
  | 2026-10-31 before fall change | 09:00 | Daylight-time expectation 10:00 |
  | 2026-11-01 after fall change | 10:00 | 11:00 |

  Saturday rows show offset expectations; they do not imply a reconciliation run on Saturday. Check the Sunday before/after each transition as well. Use Python `zoneinfo.ZoneInfo('America/New_York')` only as a local conversion observation, not proof that ADF's Windows-zone trigger executed. Record zone-data version. If evaluation year differs, include that year's transitions too. Actual trigger/DST execution evidence is Stage 7.

- [x] **Step 7: Record zero-native-retry rationale and Stage 7 obligations.** Retain Microsoft's maintenance recommendation alongside the accepted policy: central orchestration distinguishes ambiguous starts from confirmed transient failures and limits replay, while durable source worksets preserve progress. Zero retries can leave maintenance-interrupted work incomplete; it is a trade-off, not a maintenance guarantee. Require Stage 7 maintenance-failure recovery evidence and owner review of the rationale without silently changing the accepted default.

- [x] **Step 8: Populate the reserved Stage 7 register.** Every entry has parent reference, selected configuration/version, unresolved effective behavior, required passing artifact and responsible role. Cover effective identity permissions; region registration/profile/quota/capacity/policy; public endpoint reachability; registry pulls; actual job 200/202 start/correlation/status/durable-result behavior; lease/CAS failure and takeover; maintenance recovery; Eastern/DST trigger behavior; logs/alerts; actual worker memory/runtime. Include parent §§6–7 integration/fault injection, bounded quarterly/daily smoke, SEC-disabled replay, withdrawal approval and rollback evidence. Mark all `reserved/not_run`; do not plan their implementation here.

**Checkpoint:** Provider capability and uncertainty policies are evidenced; owner decisions are recorded; exact deployment behavior stays reserved. Revisit Task 4 if SDK/DFS/tool selections change, and surface the dependency deviation.

### Task 6: Assemble readiness finding and obtain exact-revision acceptance

**Files:** Create `specs/sec-filing-index-ingestion-stage-1-findings.md` and `readiness-checklist.md`; finalize index, discrepancies, decisions and evidence hashes.

**Interfaces:** Consumes Tasks 1–5 artifacts. Produces a ready/not-ready finding and, only when ready, owner acceptance naming its immutable revision/hash and limitations.

- [x] **Step 1: Write the nine required finding sections.** Use the Stage 1 §7 list as the exact content checklist: conclusion/evaluation endpoint/contract revisions/boundary; decisions and deployment bindings; quarterly/daily inventory and gaps; exact runtime/probes; Azure APIs/states/permissions/DST; resource/space and retry rationale; discrepancy resolutions; Stage 2 handoff and Stage 7 register; owner acceptance. Cite evidence ids and paths for every material claim. Record parent §4.2 overlap, §4.4 nullable accession/withdrawal rules, §§4.5–4.6 original-byte/replay/publication safeguards without rewriting them. Stage 2 handoff identifies broken root workspace membership/CLI and redundant scaffolds; no repairs are performed and no Stage 2 plan is written.

- [x] **Step 2: Run the §8 readiness gate line by line.** Map each requirement to artifact/row/decision and pass/block status. Confirm complete requested-quarter accounting; required daily/transition/family specimens or explicitly accepted gap revisions; exact digest/locks; successful isolated combined probes; selected provider/API/tool/permission evidence; concrete tenant/subscription/group/operator/registry/naming decisions; recorded parent acceptance. Missing runtime proof, traffic allocation, binding or unresolved required capability is blocking, not merely a Stage 7 entry. Genuine integrated-deployment checks may remain reserved with clear obligations.

- [x] **Step 3: Resolve discrepancies before a ready conclusion.** Show the owner one batch of decisions/contract revisions that need acceptance, linked to evidence and effects. Update the affected accepted contract only with explicit revision acceptance. Repeat impacted checks/probes and update references; unsupported sources/settings cannot weaken safeguards. If blocked, conclude not ready and preserve all evidence. A not-ready report can be reviewed, but the plan and Stage 1 remain incomplete; no completion protocol or stage tick follows.

> Deviation: Required owner decisions were resolved at Task 5, so no unanswered decision batch remained at the final gate; D10 Stage 2 alignment and D11/22 Stage 7 obligations remain original later-stage duties.

- [x] **Step 4: Validate evidence integrity and preservation.** Recompute hashes, verify every local evidence link exists, match specimen byte counts, check all required probes' exit codes, reconcile counts/categories and scan for unsupported success claims. Run `git diff --check` (expected exit 0) and `git status --porcelain=v1`; compare protected paths/status/hashes with Task 1. Recheck original approval commit/reference. No code build/test is needed to validate documentation, and the broken workspace must not be repaired for this check.

> Deviation: Four duplicate index IDs were normalized with immutable before versions; final whole-branch review required additional categorized claim coverage and an obsolete Stage 7 condition correction. Both were fixed and scoped re-reviewed; historical generation verifiers retain their original boundaries.

- [x] **Step 5: Present the ready finding for owner acceptance by revision/date.** First freeze the reviewable evidence/finding revision (commit restricted paths when authorized, or use finding SHA-256 plus evidence-manifest SHA-256). Request acceptance from Lowell Mason of that exact ready conclusion, supported boundary, decisions and listed limitations. Record the accepted pre-acceptance finding hash/revision and acceptance date in the finding; retain the reviewed version so adding the acceptance record does not invalidate its referent. Any material change after acceptance requires renewed acceptance of the new revision. No automatic acceptance inferred from a prior spec approval or silence.

> Deviation: Restricted-path commit was deferred to the controller; exact immutable F1 finding SHA-256 plus the 1,584-record manifest SHA-256 identify the accepted candidate. Lowell Mason explicitly replied Approved, accepted 2026-10-05; the controller receipt timestamp is not owner-authored.

**Checkpoint:** An owner-accepted **ready** finding exists with reproducible evidence and no blocking uncertainty. Until this checkpoint passes, retain the unexecuted/in-progress plan and unticked Stage 1.

### Task 7: Record gated completion and stop at the Stage 1 boundary

**Files:** Only after Task 6 acceptance: update this plan, Stage 1 spec rollout stamp and roadmap Stage 1 checkbox; retire this plan/Stage 1 spec according to writing-plans completion protocol. Parent design spec, ADR and roadmap remain active.

**Interfaces:** Consumes the exact accepted ready finding/reference. Produces authoritative Stage 1 completion provenance and consistency notes; no later-stage plan or execution.

- [x] **Step 1: Run resolve-before-defer before completion markup.** Missing Stage 1 exit evidence cannot be deferred to manufacture readiness. Resolve skipped tasks/findings requiring owner input. Stage 7 checks are required later-stage obligations, not invented Stage 1 accomplishments. Apply writing-plans deferred-item rules only to legitimate nonblocking leftovers; preserve existing backlog entries.

- [x] **Step 2: Mark this plan complete and retire with correct links.** Only after all exit gates pass, tick completed steps and record actual execution skill/date and deviations. Apply writing-plans Plan Completion Protocol (backlog tick/append if applicable, health report/triage and restricted-path retirement). Plan 1 final path is `specs/plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md`; Stage 1 spec final path is `specs/completed/sec-filing-index-ingestion-stage-1-spec.md` if no other live plan implements it. Fix links for the extra directory depth; finding/evidence paths stay stable. Do not retire the parent spec or roadmap.

> Deviation: The implementing plan was untracked, so filesystem moves replaced git mv. Controller review, the named-path retirement commit and final SDD retention/removal remain separate controller actions; no Git mutation occurred here.

- [x] **Step 3: Write the authoritative Stage 1 rollout stamp before ticking the roadmap.** Stamp the Stage 1 spec with actual completion date, plan 1 final path and the accepted finding revision/reference, using:

  ```text
  Stage 1: COMPLETE (YYYY-MM-DD) — implemented by plan 1
  (specs/plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md).
  Accepted ready finding: specs/sec-filing-index-ingestion-stage-1-findings.md,
  revision/reference as recorded in its owner acceptance record; accepted YYYY-MM-DD.
  Next: resume the roadmap.
  ```

  Substitute the recorded actual dates and exact accepted revision, not the planning date or example text. Tick Stage 1 only after this stamp exists. Revalidate later roadmap stages against the delivered decisions/evidence as consistency notes or explicitly accepted corrections; do not investigate or plan those stages. Roadmap's draft gap-analysis statements about missing acceptance remain historical baseline, not current completion evidence.

- [x] **Step 4: Verify final provenance and stop.** Run `git diff --check`, inspect final `git status --porcelain=v1`, recompute protected-change hashes and verify completion stamp/accepted finding/final plan links resolve. If committing, stage only named Stage 1 artifacts and intentionally accepted rollout/retirement edits, never `git add .` or `git add -A`; the formerly untracked roadmap must not be committed incidentally. Report Stage 1 evidence/acceptance/stamp and reserved checks. Later transition requires the owner's separate request to resume the roadmap.

> Deviation: Completion checks verify the intentionally retired paths and accepted immutable F1 alias rather than rewriting earlier pre-retirement generation checks; this task asserts no controller review, commit or SDD removal.

**Checkpoint:** Checkbox, completion stamp, retired implementing plan and exact accepted finding agree. Stop here.

## Historical planning self-review and execution handoff (2026-10-05)

Coverage: Stage spec §§1–3 → Task 1 and global constraints; §4 → Tasks 1/4/5; §5.1 → Tasks 2–3; §5.2 → Task 4; §5.3 → Task 5; §5.4 → evidence schema/all checkpoints; §6 → official review and reverification; §§7–8 → Task 6; §9 → Task 7. No ingestion implementation, package repair, Azure provisioning or later-stage planning is included.

The original planning handoff below is historical, not investigation evidence or current status. At that handoff all task checkboxes were empty; Stage 1 stays unticked and its spec stays approved, without a completion stamp.

Recommended: open a fresh execution session with this plan as the complete handoff. Choose subagent-driven-development or inline executing-plans there. Keep one operational SEC issuer regardless of execution method. The original planning request authorized writing this Stage 1 plan only; do not start investigation tasks as a side effect of saving it.
