# SEC filing-index ingestion — Stage 1: Scope and feasibility findings

**Status:** APPROVED (2026-10-05) — written spec accepted by Lowell Mason.
**Owner and decider:** Lowell Mason.
**Repository:** /Users/lowell/Projects/sec-edgar.
**Authorization:** The owner authorized Stage 1 and approved its approach, scope, evidence boundary,
deliverables and readiness criteria on 2026-10-05. The parent ADR and overall spec were formally
accepted on that date; their acceptance records are in those documents.

**Parent documents:** [Roadmap](sec-filing-index-ingestion-roadmap.md),
[overall design spec](sec-filing-index-ingestion-spec.md), and
[ADR](sec-filing-index-ingestion-adr.md).

## 1. Purpose and stage boundary

Establish an accepted implementation boundary and resolve the source, runtime and deployment
prerequisites needed by later stages. Stage 1 exits with an owner-accepted written readiness
finding identifying a viable source/runtime combination and the decisions needed to proceed.

Use an evidence-led review: current official documentation, a source-directory inventory,
bounded retained source samples, and isolated runtime compatibility probes. Document facts,
decisions and limits before concluding readiness.

The workload remains filing indexes: historical quarterly backfill, ongoing daily ingestion,
metadata ETL and reconciliation. Parent §2 defines its scope; parent §4.9 and the ADR Decision
define the single sec-edgar-ingest implementation package. Accepting this stage does not expand
that workload.

Allowed investigation work includes read-only repository inspection, provider-document review,
bounded SEC directory/source access, archive inspection and isolated dependency/container probes.
Keep probe environments separate from the workspace packages. Retain evidence, not production
ingestion modules.

Package/workspace repairs belong to Stage 2. Ingestion implementation, production parsers and
tests, Bicep resource definitions, Azure provisioning, production data publication and trigger
activation are outside Stage 1. No resource-profile comparison is authorized. Actual worker
memory/runtime measurements and live Azure integration remain Stage 7 checks.

## 2. Contract authority

The accepted parent spec remains the implementation contract. Reference it when recording
decisions instead of creating a second version of its safeguards.

| Boundary | Authoritative reference |
|---|---|
| Workload and service/package ownership | Parent §§2, 4.1, 4.9; ADR Decision |
| Discovery, requested units, overlap and source coverage | Parent §4.2 |
| Source acceptance and coordinated SEC access | Parent §4.3 |
| Identity, precedence, reconciliation and withdrawal approval | Parent §4.4 |
| Retained inputs, provenance and replay | Parent §§4.5–4.6 |
| Generation publication and reader behavior | Parent §4.6 |
| Recovery, observability, defaults and identity | Parent §§4.7–4.9 and §5 |
| Verification and deployment/operational gates | Parent §§6–7 and 10 |

An evidence conflict must be recorded with its affected contract, resolution and owner decision.
Changing an accepted contract requires explicit acceptance of the revision. An assumption or
unsupported source format cannot silently weaken a safeguard.

## 3. Repository baseline

Rechecked on 2026-10-05, before writing this stage spec:

- The ingest, client and download packages contain only hello() scaffolds and type markers.
  Their READMEs and the root README are empty.
- No ingestion tests, worker implementation, CI definitions or Azure infrastructure were found.
- [Root configuration](../pyproject.toml) declares Python >=3.14, references the locally deleted
  sec-edgar-index-ingest workspace member, includes the client/download scaffolds, and declares
  a sec-edgar CLI targeting the absent sec_edgar module.
- The existing deletions under packages/sec-edgar-index-ingest/ and the untracked roadmap are
  local changes to preserve. No deployed Azure resources were inspected.

Record any drift when the investigation starts. The parent spec's original statements about
not inspecting a repository are draft provenance; this inventory supplies the Stage 1 baseline.
The finding must identify the Stage 2 alignment work without performing those repairs.

## 4. Accepted inputs and starting settings

| Input | Owner-approved value |
|---|---|
| Intended historical range | 2010 Q1 through the open quarter, inclusive |
| Initial development range | 2015 Q1 through the open quarter, inclusive |
| End-quarter rule | Resolve and pin the end quarter at each run's start |
| Daily handoff | 2026-10-01, retaining baseline overlap under parent §4.2 |
| SEC User-Agent | Lowell Mason sec-edgar-ingest mason.lowell@mac.com |
| Azure target | A new dedicated resource group in an existing subscription |
| Region order | eastus, then eastus2, then centralus |
| Networking | Public HTTPS endpoints, managed identities, scoped roles, anonymous blob access disabled |
| Infrastructure as code | Bicep |
| Python/container candidate | Python 3.14; Linux amd64 container |
| Initial compute candidate | General-purpose Consumption workload profile; 2 vCPU and 4 GiB RAM |
| Initial execution settings | One replica; parallelism 1; completion count 1; replica timeout 3,600 seconds |
| Initial storage candidate | Standard general-purpose v2; hierarchical namespace enabled; Hot tier; ZRS |
| Ingestion-artifact retention | Indefinite during initial development: raw snapshots, observations, generations, manifests, approvals, quarantine evidence and run reports |
| Operational-log retention | 90 days |
| Alert owner and destination | Lowell Mason; mason.lowell@mac.com |

The owner accepted the parent §4.8 operating defaults, including the production schedules and
retry/access policies. Select ADF's supported Eastern time-zone identifier from current evidence;
preserve the accepted local schedule times and DST behavior.

These resource settings are starting candidates, not measured capacity or freshness guarantees.
Assess expansion and temporary-storage requirements without comparing resource profiles.
If the evidence exposes an incompatibility, record it and obtain an explicit settings revision.
Stage 7 validates the actual worker against the chosen memory/runtime limits.

On 2026-10-05, the open quarter is 2026 Q4. The requested ranges therefore contain 68 intended
quarterly units and 48 development units. The finding must record its own evaluation date and
pinned end quarter; later runs resolve their endpoint afresh. New quarters require discovery and
format validation under the parent contracts.

## 5. Evidence requirements

### 5.1 Source availability, discovery and formats

Inventory every intended quarterly unit through the pinned end quarter, marking the development
subset separately. Resolve actual archived-quarter and open-quarter full-index URLs, available
representations, and directory-discovery methods. Inspect daily discovery from the handoff date
and document historical daily-directory availability relevant to outage recovery.

Use bounded retained samples covering:

- 2010 Q1 and 2015 Q1;
- the latest closed quarter and the open quarter;
- the daily handoff and an already published daily index;
- year/quarter transitions and each distinct format family found during inventory.

Do not require every optional archive codec when a supported representation covers the source.
Conversely, an unexamined representation or legacy row/path family cannot be declared supported.
Record which representations are selected and why.

For listings, capture URL, access time, response outcome, representation/schema, discovered
children and source-selection decisions. Distinguish valid no-source outcomes from failed
discovery. Account for unavailable directories or listed files without manufacturing calendar
URLs or inferring withdrawals; parent §§4.2–4.4 govern those outcomes.

For source samples, retain exact original bytes and record SHA-256, received byte count,
available validators, content/transport encoding, archive member details, expanded size, text
encoding, line endings, headers, representative fields/paths and observed date coverage.
Investigate legacy path/accession conventions within both ranges, preserving parent §4.4's
nullable-accession contract.

When the selected source is compressed, retain the original archive as the raw specimen.
Decoded index content is a derivative. The finding must reconcile the selected representation,
raw filename/format metadata and parent §4.5's path examples without replacing original bytes
with decoded content.

Assess cumulative volume, the largest observed source, temporary disk needs and the assumptions
required to fit bounded work within the starting allocation. Directory sizes are estimates;
they do not prove archive expansion, parser working memory or worker runtime. Golden parser
fixtures and ingestion coverage verification belong to the later build stages under parent §6.

SEC investigation access uses the approved identity and parent §§4.3, 4.8 and §5 rate,
identification and failure controls. Coordinate one bounded investigation issuer operationally,
record the sampling window/request budget, and account for other owner traffic before access.
The production Storage-backed lease is implemented in Stage 2; its absence does not authorize
concurrent investigation issuers or independent request budgets. Do not make live SEC access a
CI dependency.

### 5.2 Python, container and dependency compatibility

Select exact, reproducible versions for Python 3.14, the Linux amd64 base image, the SEC HTTP
client, Azure identity/storage libraries and the Parquet implementation. Record the base-image
digest, Python build/ABI, OS/architecture, direct and resolved dependencies, installer/tool
versions and commands.

The dependency matrix must cover azure-identity, azure-storage-blob and azure-data-tables,
plus azure-storage-file-datalake if the selected operations need its DFS APIs, and relevant
native/transitive dependencies. Record actual package Python requirements and wheel/platform
availability; a minimum-version statement alone is not combined-runtime compatibility evidence.

Isolated probes must demonstrate installation/imports, decoding the selected archive formats
and a small Parquet write/read round trip. Retain commands, inputs, outputs and exit codes.
Do not repair or build the broken root workspace to make these probes pass, and do not implement
the ingestion parser/catalog as a compatibility probe.

The Stage 1 base-image/dependency record is distinct from the built worker image and release
digest delivered later. Record registry choice, image-pull authorization, rollback-image
availability and deployment tool prerequisites as decisions.

### 5.3 Azure management, identity and scheduling

Use current official Microsoft documentation to select and record:

- Management/resource API versions for Jobs creation/start/execution get/list, ADF pipelines
  and triggers, Storage and the selected monitoring/registry resources. Keep related operation
  versions consistent and record Bicep/tooling requirements.
- Start-response and asynchronous-operation handling, exact execution correlation, documented
  execution states, polling limits, and conservative treatment of uncertain outcomes. Explain
  what documentation proves and what actual 200/202 response shapes still require Stage 7.
- An actor/operation/resource-scope permission matrix: ADF job control and durable-result reads;
  worker Blob/ADLS, lease and Table operations; registry pulls; readers/approval operators;
  and deployment/role-assignment authority. Record identity type, token audience, role/actions
  and scope. Newly created principal IDs are established during deployment.
- Storage lease and conditional-entity-write capabilities, their limits, and any relevant
  ADLS multi-protocol constraints. A lease on an Azure blob does not itself fence SEC requests
  or create a Blob/Table transaction.
- ADF Eastern time-zone identifier, Day/Week recurrence, DST semantics and trigger time
  serialization. Specify expected local and UTC behavior across both DST transitions.
- Public-endpoint authorization and network requirements for workers, ADF result reads, registry
  pulls and telemetry; resource/profile, storage-redundancy and log-retention support.

Resolve the concrete tenant/subscription binding and proposed resource-group name, operator
authority, registry choice and environment naming before readiness acceptance. Documentation
can establish capability and required permissions; effective deployed authorization is Stage 7
evidence.

Document the rationale for retaining zero native job retries despite Microsoft's maintenance
interruption guidance. Preserve parent §4.1/§5 handling of ambiguous starts and §4.8's bounded
confirmed-failure replay. Reserve the maintenance-failure recovery verification for Stage 7.

### 5.4 Evidence record and discrepancy handling

Every record identifies the claim/decision, category, method, direct official URL or retained
artifact, access/receipt time, applicable versions, result and limitation. Source artifacts
carry hashes; probes carry commands and exit codes.

Use these categories explicitly:

| Category | Meaning |
|---|---|
| Verified documentation | Capability or limit stated by the provider |
| Source/probe observation | Result actually observed for the named input and environment |
| Owner decision | Accepted scope, policy, setting or contract revision |
| Assumption | Unverified proposition with impact and a resolution/check obligation |
| Reserved Stage 7 check | Effective deployed behavior requiring the integrated system |

Record failed checks and absent evidence as such. Resolve blocking uncertainty before a ready
conclusion. The finding may conclude not ready, but accepting a not-ready report does not meet
this stage's readiness exit.

## 6. Initial evidence from brainstorming

The following records were checked against official sources on 2026-10-05. Reverify them against
the versions selected during the investigation. They guide the work; they are not a completed
source survey, runtime probe or deployment finding.

| Topic | Verified fact or bounded observation | Consequence for the investigation |
|---|---|---|
| SEC source families and discovery | SEC describes quarterly/current-quarter full indexes, daily indexes and HTML/XML/JSON directory metadata. [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) | Verify actual listings, bodies, selected representations and coverage across the range. |
| SEC access | The SEC publishes a user-wide ceiling of 10 requests/second across machines and identifying User-Agent guidance. [SEC developer resources](https://www.sec.gov/about/developer-resources) | The lower target and coordination policy remain owner/application contracts. |
| SEC timing and corrections | Nightly index work starts around 22:00 Eastern; full/quarterly correction rebuilding is described as early Saturday. [SEC access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) | The accepted schedules are operating choices; neither guarantees source readiness or correction completeness. |
| Listed archive sizes | 2015 Q1 lists master.zip at 3,749 KB and master.idx at 27,214 KB; 2026 Q3 lists 3,420 KB and 26,884 KB respectively. [2015 Q1](https://www.sec.gov/Archives/edgar/full-index/2015/QTR1/), [2026 Q3](https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/) | These two metadata observations do not establish maximum size, measured expansion or processing memory. |
| Region shortlist | Microsoft's product matrix lists the required service products in all three candidate regions; general-purpose Consumption covers supported regions. [Regional matrix](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/table/), [workload profiles](https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview) | This is product-level support. Jobs/profile eligibility, quota, capacity, policy and the selected storage/telemetry configuration remain deployment checks. |
| Python/Parquet | PyArrow documents Python 3.14 support; official Python container tags include the 3.14 family. [PyArrow installation](https://arrow.apache.org/docs/python/install.html), [official Python image](https://hub.docker.com/_/python?tab=description) | Resolve exact versions and prove the selected combination locally. |
| Azure SDK candidates | Current Microsoft references describe Identity 1.26.0, Blob 12.31.0 and Tables 12.7.0. [Identity](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python), [Blob](https://learn.microsoft.com/en-us/python/api/overview/azure/storage-blob-readme?view=azure-python), [Tables](https://learn.microsoft.com/en-us/python/api/overview/azure/data-tables-readme?view=azure-python) | These are documented candidates, not selected or tested dependency pins. |
| ADF time zone | Eastern Standard Time observes DST; adjustment is supported for Day and higher recurrence, including Week. [Schedule triggers](https://learn.microsoft.com/en-us/azure/data-factory/how-to-create-schedule-trigger) | Record correct serialization and preserve the accepted local schedule times. |
| ADF asynchronous calls | Web activity defaults to following a 202 Location through GET polling; that handles an HTTP operation. [Web activity](https://learn.microsoft.com/en-us/azure/data-factory/control-flow-web-activity) | ARM operation completion must remain separate from execution and matching worker-result success. |
| Jobs API and states | Non-preview 2026-07-01 and 2025-07-01 Start references exist; 2026-07-01 documents 200 execution output and 202 Location/Retry-After. Exact execution GET lists seven states without fully defining each terminal meaning. [Start 2026](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/jobs/start?view=rest-resource-manager-containerapps-2026-07-01), [Start 2025](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/jobs/start?view=rest-resource-manager-containerapps-2025-07-01), [execution GET](https://learn.microsoft.com/en-us/rest/api/resource-manager/containerapps/job-execution/job-execution?view=rest-resource-manager-containerapps-2026-07-01) | Select versions and document conservative state/correlation handling; a start timeout is not an idempotency guarantee. |
| Native retries | Zero retries is supported; Microsoft recommends at least one for long-running replicas affected by maintenance. [Jobs guidance](https://learn.microsoft.com/en-us/azure/container-apps/jobs) | Record the accepted zero-retry rationale and the required later recovery evidence. |
| Storage coordination/publication | Renewable finite Blob leases allow 15–60 seconds; Table updates support ETag/If-Match and return 412 for a mismatch. [Lease Blob](https://learn.microsoft.com/en-us/rest/api/storageservices/lease-blob), [Update Entity](https://learn.microsoft.com/en-us/rest/api/storageservices/update-entity2) | Document primitive limits and preserve the parent coordination/publication safeguards. |
| Temporary storage | Container Apps documentation ties ephemeral capacity to replica CPU and lists 8 GiB above one vCPU. [Storage mounts](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts) | Confirm applicability to the selected Jobs configuration; account for its temporary lifetime and verify actual use in Stage 7. |
| Storage and identity | Standard GPv2 supports Blob/ADLS and Tables; Entra data operations have specific permissions. [Storage accounts](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview), [Storage authorization](https://learn.microsoft.com/en-us/rest/api/storageservices/authorize-with-azure-active-directory) | Review selected account features, redundancy and scoped permissions; generic management authority does not prove data access. |
| Logs and retention | Microsoft documents Container Apps log routing and workspace/table retention configuration. [Log options](https://learn.microsoft.com/en-us/azure/container-apps/log-options), [retention](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure) | Select settings that retain the relevant operational tables for 90 days and reserve delivery/alert verification for Stage 7. |

SEC guidance does not guarantee historical daily retention, a publication SLA, every archive
codec, or the completeness of each observed source. Directory timestamps alone do not establish
correction coverage. Likewise, SDK minimum Python versions do not prove native dependency
compatibility, and managed identity does not bypass network restrictions.

## 7. Written finding to deliver

Write the self-contained finding to
specs/sec-filing-index-ingestion-stage-1-findings.md. Retain its evidence index and bounded
specimens/probe reports under specs/evidence/sec-filing-index-ingestion/stage-1/.

The finding must contain:

1. A ready/not-ready conclusion, evaluated date/end quarter, parent/spec revisions and the precise
   supported implementation boundary.
2. The accepted decision record, including the concrete deployment bindings and remaining
   deployment-gate conditions.
3. The quarterly/daily source inventory, development subset, selected format/representation
   coverage, specimen references/hashes and explicit gap resolutions.
4. The reproducible runtime/dependency matrix and successful or failed probe reports.
5. The versioned Azure API, execution-state/correlation, permission and Eastern-time/DST findings.
6. The initial resource/temporary-storage assessment, its method and limitations, and the
   zero-native-retry rationale.
7. A discrepancy register linking evidence to resolutions and any explicitly accepted revisions.
8. The repository-alignment handoff for Stage 2 and the distinct checks reserved for Stage 7.
9. Owner acceptance naming the finding revision, date and accepted limitations.

The Stage 7 check register must cover effective identity permissions, selected-region
registration/profile/quota/capacity/policy, public endpoint reachability, registry pulls, actual
job 200/202 start/correlation/status/result behavior, lease/CAS failure behavior, native-maintenance
recovery, Eastern/DST trigger behavior, log/alert delivery and actual worker memory/runtime.
Refer to parent §§6–7 for the required integration, smoke, offline replay and recovery evidence.
Do not infer those results from documentation or local compatibility probes.

## 8. Observable readiness exit criteria

Stage 1 is ready to complete only when:

- The decision record includes every input in §4, concrete deployment bindings, selected
  runtime/tool/API versions, permission requirements and recorded parent acceptance.
- The source matrix accounts for every requested quarterly unit and relevant daily discovery;
  retained samples cover the selected representations and observed format families; gaps have
  explicit accepted resolutions.
- Exact base-image/dependency pins and retained successful isolated probe results identify a
  reproducible viable runtime combination.
- Official evidence supports the selected provider primitives, versions and scheduling behavior;
  execution uncertainty and permission/network limitations have explicit handling/check duties.
- No blocking uncertainty remains. A scope or contract revision has explicit owner acceptance;
  reserved deployment checks are clearly identified rather than represented as passed.
- The owner accepts the written ready finding by revision/date, including its limitations.
- Existing local changes remain preserved and Stage 2 repairs have not been performed.

Acceptance of this stage spec authorizes the investigation plan. It does not satisfy these
readiness criteria or constitute accepted historical ingestion coverage.

## 9. Rollout note

Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 1 — on plan completion, tick the stage and re-validate later stages against what shipped.

After owner approval of this written spec, hand off to writing-plans in a fresh session for
Stage 1 only, then stop this brainstorming session. The plan produces the finding and evidence;
it does not implement or plan the remaining roadmap.

Keep Stage 1 unticked until the investigation plan completes, its ready finding is accepted,
and the authoritative completion stamp is recorded. The stamp must identify the completion date,
implementing plan ID/path and accepted finding revision/reference. Only then tick Stage 1 and
revalidate later stages against the decisions and evidence delivered. The subsequent transition
is owner-initiated by resuming the roadmap.

No Azure resources are provisioned and no production triggers are enabled by approving or
committing this spec.
