# SEC filing-index ingestion — Stage 6: Azure orchestration and deployment definitions

**Status: COMPLETE (2026-10-13)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md
**Owner:** Lowell Mason.
**Implementing plans:** [Plan 9](../plans/completed/9-sec-filing-index-ingestion-stage-6-spec.md) (worker image and operator surface) and [Plan 10](../plans/completed/10-sec-filing-index-ingestion-stage-6-spec.md) (Azure definitions and orchestration), both written after this spec was approved (§13). Approved 2026-10-12 (Lowell Mason: "Approved — write both plans").
**Authority:** [Parent design](../sec-filing-index-ingestion-spec.md), [ADR](../sec-filing-index-ingestion-adr.md), [roadmap](../sec-filing-index-ingestion-roadmap.md) (Stage 6 entry and "Stage 6 resume — 2026-10-12"), accepted [F1](../sec-filing-index-ingestion-stage-1-findings.md), completed [Stage 5 spec](sec-filing-index-ingestion-stage-5-spec.md) and the roadmap's "Stage 5 completion and later-stage consistency" note. Only roadmap Stage 6 (R4, R11, Worker/pipeline delivery) and the `history` command the owner added to its Produces line are specified here.

## 1. Reconciliation and scope

Resumed 2026-10-12 against `main` at `07067a0a` (merged PR #11), on local branch `stage-6-azure-orchestration` (commits `aceba430` and `78d0321e`; no upstream). Stages 1–5 carry authoritative stamps. Plans 7 and 8 are deferred-item plans and tick nothing; the resume record lists what they changed for Stages 6–8.

Stage 6 re-validation against the shipped package found:

- No Dockerfile, `infra/` tree, ADF definition or alert exists.
- The shipped `conf/sec-edgar-ingest.yaml` is a local-fixture config. An Azure config must pass `config.py:237–251`, which rejects the all-zero digest, fixture or synthetic provenance and a fixture parser.
- `open_azure_stores` builds `ManagedIdentityCredential()` with no client ID (`storage/azure.py:515`). In Container Apps that selects the system-assigned identity, but F1 D-03 gives the job user-assigned identities.
- Every store open writes the binding registry into `locks` (`storage/azure.py:522`), operator commands included. No credential path exists for a human operator off Azure.
- `--approver` and `--operator` are free text. A re-activating `approve` records no actor.
- `--execution-id` is a required argument. The Container Apps execution name exists only after the start call returns, so ADF cannot pass it at launch.
- Workflow children run in-process with their stdout and stderr captured (`workflows/checked.py`). The container log therefore carries only workflow-level events, and those lack the fields that alerting needs.
- Log search alert queries scan at most two days, so an absence-of-event query cannot express an eight-day reconciliation staleness alert.

Stage 6 takes three deferred items. The first two are bound to it in `specs/deferred_items.md`; the third's trigger fires here:

- the read-only `history` command (roadmap Produces);
- actor identification and re-activation attribution, whose Done-when names Stage 6;
- operator commands creating a store at a mistyped path. §5 changes how operator commands open stores, which is that item's trigger.

It does not take "download evidence outside the retained members", because Stage 6 does not change how downloads are recorded. The derived `activated` field and every other deferred item also stay out.

**Process:** lean, as in Stage 5. Each task gets red/green TDD and a review, and a final whole-branch review closes each plan. Each plan exit runs the full offline suite, a wheel build and a CLI smoke test. Azure adapters stay in step with the local backend. The work is offline: no SEC, Azure management or data-plane, credential, deployment or trigger activity. D1 (§14) authorizes local tool installs only.

## 2. Constraints inherited by Plans 9 and 10

Copied verbatim from the accepted parent contract:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- ADF passes references, not index contents.
- A start timeout with an unknown execution id is an ambiguous start, not permission to launch a second copy.
- Resolve the existing execution or stop for operator recovery.
- Success also requires the matching worker result file.
- **Execution unknown:** ambiguous job start or unresolvable execution status. No false success and no blind launch retry.
- A successful start is not job success.
- Failed, timed-out and unknown executions propagate correctly; a missing or mismatched worker result cannot pass the stage.
- A gated reconciliation is not reported as complete.
- ADF owns the production schedules, configured with its supported Eastern time-zone identifier and daylight-saving behavior.
- Container Apps Jobs has no independent schedule for these same runs.
- Trigger enablement is an explicit release step, not a side effect of creating infrastructure.
- Use managed identities for ADF management calls and worker access to Azure resources.
- Pin and review permissions; do not place storage keys in worksets or source URLs.
- Production deployment pins the image digest and configuration revision.
- Keep infrastructure, role assignments, job definitions, ADF pipelines, schedules and alerts under version control.
- All commands emit structured logs with run, execution, attempt, source and generation identifiers.
- Alert on a failed job, ambiguous start, lease failure, access block, exhausted retry budget, quarantine, unresolved publication conflict or pending withdrawal approval.
- Report discovery age, oldest listed-but-unpublished source and last successful reconciliation separately.
- A no-new-file run is distinct from a failed discovery; weekends alone do not imply stale ingestion.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

**Accepted pins carried over.**

- **Python and SDKs:** Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, and the existing `uv.lock`. No dependency is added; `AzureCliCredential` ships in Identity 1.26.0.
- **F1 §2 bindings:** D-01 tenant and subscription; D-02 group `rg-sec-edgar-dev-eastus`; D-03 names; region order eastus → eastus2 → centralus.
- **F1 §4 runtime:** base `python:3.14.8-slim-bookworm`, Linux amd64 child `sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d`; lock SHA-256 `523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2`.
- **F1 §5 management API versions:** Jobs `2026-07-01`; ADF `2018-06-01`; Storage `2025-06-01`; UAMI `2024-11-30`; roles `2022-04-01`; ACR `2025-11-01`; Log Analytics `2025-07-01`; diagnostic settings `2021-05-01-preview`; action group `2023-01-01`; scheduled-query alert `2023-12-01`.
- **F1 §6 job values:** 2 vCPU / 4 GiB, one replica, parallelism 1, completion count 1, `replicaTimeout` 3,600 s, zero native retries.
- **D-18 observer:** 30 s poll base, a longer Retry-After honored, and a 4,200 s observation deadline.
- **Tools:** CLI **2.90.0**, Bicep **0.38.33**, uv **0.12.15**.

Existing config, workset and binding-registry bytes are never rewritten. All 22 Stage 7 integrated checks remain reserved/not_run.

## 3. Worker image

**Definition.**

- **Base:** `infra/azure/sec-edgar-ingest/image/Dockerfile` starts `FROM docker.io/library/python@sha256:d1e795fb…`, the exact reference F1's successful quick task used. That is `python:3.14.8-slim-bookworm`'s Linux amd64 child digest, so no platform selection is needed. (owner, plan 9, 2026-10-12) `FROM --platform` is never used: it failed F1's ACR quick-task scanner (F1 §4), and Stage 7 builds with quick tasks (S7-05).
- **Dependencies:** they come from `infra/azure/sec-edgar-ingest/image/requirements.lock`, a byte copy of F1's retained lock. A test asserts its SHA-256 equals `523b2da3…` and that its 21 pins equal the versions resolved in `uv.lock`. The install is `pip install --require-hashes --no-deps --only-binary=:all:`, followed by the offline-built `sec-edgar-ingest` wheel with `--no-deps`.
- **Runtime:**
  - the process runs as UID 1000;
  - `ENTRYPOINT ["sec-edgar-ingest"]`;
  - `TMPDIR` is `/tmp/sec-edgar-ingest`, created in the image and owned by UID 1000. It lives on the container's writable layer: an execution override cannot mount volumes (§4), so no EmptyDir is used. Whether that space fits the workload is S7-18;
  - the image carries no configuration (§4).
- **Build context:** a script assembles it from the Dockerfile, the lock and the wheel in a clean directory. The same context serves the local build here and the ACR quick task in Stage 7.

**Proof that the built image runs every command (D1).** The image is built locally with `docker buildx build --platform linux/amd64`. The platform choice is a CLI flag, never a Dockerfile line. A smoke script runs the image under `--network none` and checks:

- that it reports Linux x86_64 and CPython 3.14.8;
- `--version`, and `--help` for every subcommand;
- each subcommand at least once on mounted local-fixture state. `backfill`, `daily` and `reconcile` run directly, which runs `discover`, `collect`, `transform` and `publish` as workflow children. A corrected fixture gates one quarter so that `candidates`, `approve`, `history` and `rollback` run on real state.

The script asserts each exit code and stdout outcome. The workflow runs load PyArrow and cryptography natively under amd64 emulation. The local digest is never recorded as a release digest.

## 4. Configuration delivery and the image binding (owner decision Q1)

**Template and renderer.** `infra/azure/sec-edgar-ingest/config/sec-edgar-ingest.azure.template.json` holds the complete Azure configuration except `worker.image_digest` and `worker.provenance`. Its values:

- **Range and handoff:** backfill `2015Q1` through `open`; daily handoff `2026-10-01`.
- **Parser:** `sec-index-parser-v1`, the only legal Azure value.
- **Storage bindings:** all 13 that `config.py:198–203` requires. The endpoints are spelled without a trailing slash.
- **Defaults:** every other value is the accepted §4.8 default.

A renderer fills in the digest and provenance, validates the result through `Settings`, and emits:

- canonical config bytes;
- their `config_sha256`;
- an ARM parameters file carrying `configJson` and `configSha256`.

No release digest exists in Stage 6, so the template and renderer are the versioned configuration. Stage 7 renders the release config once S7-05 has published the image.

**Delivery.** A Jobs `2026-07-01` execution override carries only `args`, `command`, `env`, `image`, `name` and `resources` per container, and it replaces the whole template. Volumes therefore cannot carry the config into an ADF launch. Environment entries can reference job secrets by name.

- **Bicep inputs:** Bicep receives `configJson` and `configSha256` only.
- **Job image:** derived from the config, as `<registry>/sec-edgar-ingest@<json(configJson).worker.image_digest>`. The image and the config therefore cannot disagree.
- **Secret and variable:** the job stores `configJson` as the secret `ingest-config`. The job container, and ADF's override of it, set the environment variable `SEC_EDGAR_INGEST_CONFIG` with `secretRef: ingest-config`. The config is not sensitive; the secret is only the transport, so ADF never carries the config bytes.
- **CLI:** workflow commands accept `--config-env NAME` as the exclusive alternative to `--config PATH`. It reads the config JSON from that variable and applies identical validation. Workflow children keep receiving a temporary config file.
- **ADF expectations:** ADF receives the digest and `configSha256` as pipeline-parameter defaults from the same parameters file.
- **Assumption (S7-06):** that a `secretRef` in an override's `env` resolves against the job's secrets. The Jobs permission guidance warns of exactly this capability. The fallback is passing the config inline as an argument.
- **Changing either value redeploys the job.** An attempt begun under the old pair fails on replay with `Conflict` (`cli.py:175–185`). Every ADF launch is a fresh attempt (§7.1), so only an execution in flight at deploy time is exposed. The Stage 7 runbook deploys only with no execution in flight.

**What ties the digest to the running image.** The worker cannot measure its own digest: an image cannot embed a config that names the image. ADF closes the loop instead. It requires both of these:

- the observed execution's `template.containers[0].image` equals the pinned reference;
- the matching result's `context.image_digest` and `config_sha256` equal the expected values.

S7-04 and S7-09 prove that link live.

**One binding, frozen.** The deployment binding is written once per store, and every later open compares it byte for byte (`storage/azure.py:308–309`). Workers and operators therefore use the same rendered config. A committed golden `infra/azure/sec-edgar-ingest/config/deployment-binding.json` must equal `deployment_binding()` of a rendered test config. Any edit that would change the binding bytes, the endpoint spelling included, fails CI.

## 5. Identities, credentials and store opening (owner decision Q2)

**Credentials by command class.**

- **Workflow and stage commands** use `ManagedIdentityCredential(client_id=…)`. The client ID is the worker UAMI's, read from `SEC_EDGAR_INGEST_WORKER_CLIENT_ID`, which Bicep sets on the job container. A missing or empty value on Azure is `configuration` (exit 2) before any I/O. It is not a config key, so neither the binding nor `config_sha256` changes. The pull UAMI is only the registry identity.
- **Operator commands** (`approve`, `rollback`, `candidates`, `history`) use `AzureCliCredential` on Azure, which is the operator's `az login`. No command falls back through a credential chain.

**Verify-only operator open, on both backends.** Operator commands read the binding registry and compare it with `deployment_binding(settings)`. They never write the registry, and never create a root directory, sqlite schema, container or table.

- **Missing registry, or a missing local root or state database:** `configuration` (exit 2). stdout is empty and the reason goes to stderr.
- **A different registry:** `state_conflict` (exit 9).

This closes the "mistyped path" deferred item. Operators need only Blob read on `locks`, never write. Worker stores keep the shipped write-once registry open.

**Role matrix.** Custom roles carry only the listed Actions or DataActions. `B` and `T` abbreviate the Blob and Table entity prefixes from F1's permission notes.

| Role | Permissions |
|---|---|
| SecEdgar Job Controller | `Microsoft.App/jobs/read`, `jobs/start/action`, `jobs/execution/read`, `jobs/executions/read` |
| SecEdgar Job Async Observer | `Microsoft.App/locations/containerappsjoboperationresults/read`, `…/containerappsjoboperationstatuses/read` |
| SecEdgar Blob Reader | `B/read` |
| SecEdgar Blob Writer | `B/read`, `B/write` |
| SecEdgar Entity Reader | `T/read` |
| SecEdgar Entity Writer | `T/read`, `T/add/action`, `T/update/action` |

| Principal | Role → scope |
|---|---|
| ADF system-assigned identity | Job Controller → job; Job Async Observer → subscription; Blob Reader → `results` |
| Worker UAMI | Blob Writer → `raw`, `worksets`, `results`, `quarantine`, `generations`, `manifests`, `locks`; Blob Reader → `approvals`; Entity Writer → `SourceState`, `Attempts`, `ActivePointers`; Entity Reader → `Approvals` |
| Pull UAMI | built-in AcrPull → registry |
| Operator (Lowell, object ID parameter) | Blob Reader → `locks`, `worksets`, `generations`, `manifests`, `approvals`, `results` (owner, final review, 2026-10-13); Blob Writer → `approvals`; Entity Reader → `SourceState`; Entity Writer → `ActivePointers`, `Approvals` |

**Departures from F1's preliminary matrix:**

- **Worker narrowed.** The worker loses `Approvals` entity writes and `approvals` Blob writes. Only `approve` and `rollback` write them (`etl/approval.py`, `etl/rollback.py`), and a recorded fixture run asserts that workflow commands write neither. RBAC then enforces F1's rule that the worker never manufactures an approval.
- **Operator widened.** The operator gains `worksets` read (Stage 5 spec §5) and `SourceState` read, which `approve` needs for its superseded check and `candidates` for its listing, and `results` read, which the runbook's `execution_unknown` recovery needs to read a launch's `result.json` (owner, final review, 2026-10-13).
- **One operator role set.** `approve` and `rollback` have identical write sets (Stage 5 §5), so separate RBAC roles could not separate them. F1 D-04 names the same human for approval, rollback and reading.
- **Bootstrap stays outside the templates.** Deployment and bootstrap authority (D-04's subscription UAA, SecEdgarBootstrap Actions, RG Contributor and RBAC Administrator) is a Stage 7 prerequisite.

F1 §5's trust limits stand. Start authority is trusted at worker privilege. Table-scoped grants cover every entity in the table.

## 6. Operator commands: history and attribution (owner decision Q3)

**`sec-edgar-ingest history --config PATH --quarter YYYYQn [--state-dir PATH]`** is read-only. It prints canonical JSON `{outcome, quarter, lineage, rollbacks, activations, error}`:

- `lineage` is `quarter_history`;
- `rollbacks` is `EtlState.rollbacks(quarter)`;
- `activations` is `EtlState.activations(quarter)`, below.

The outcomes are `success` (exit 0), `configuration` (2) and `state_conflict` / `internal_error` (9). A quarter with no pointer gives an empty lineage. The runbooks take rollback and revert targets from it.

**Principal attribution on Azure.** `approve` and `rollback` take the actor from the operator's token. They decode the token issued by `AzureCliCredential` and record `entra:<tid>/<oid>`, followed by `<upn>` or `<preferred_username>` when present, in the existing `approver` or `operator` field. The value is one printable line of at most 256 characters.

- On Azure, `--approver` and `--operator` are refused (`configuration`). A token without `oid` is also refused.
- On the local-fixture backend, both flags stay required free text.
- The approval and rollback formats are unchanged.
- The token is decoded without signature verification: Entra has just issued it to this process. Attribution is evidence, and RBAC still authorizes the write.

**Activation records.** Every `approve` that reaches the pointer swap first writes one immutable object per attempted move:

```text
approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/activation=<activation-id>/activation.json
```

It is canonical JSON with format `sec-approval-activation-v1`, and its fields are:

- `quarter`, `generation_id`, `base_generation_id`, `from_pointer_version`;
- `approval_ref` and `approval_sha256`, for the stored approval it activates under;
- `actor` and `activated_at`.

`activation-id` is the SHA-256 of the canonical `[quarter, generation_id, from_pointer_version]`. A retry is idempotent, and the first record wins and is re-validated. A repairable index row of kind `ApprovalActivation`, routed to `Approvals`, mirrors it.

The record is written ahead of the compare-and-swap. Like a rollback record, it records an attempt, and the pointer decides what took effect. A first approval therefore writes the approval (the decision) and an activation (the move). A re-activation after a rollback writes only an activation, attributed to its own actor.

`unchanged`, refusals and an `approval_stale` found before the swap write no activation; a swap that lost a race keeps its activation as evidence of the attempt. (owner, plan 9, 2026-10-13) `approve` prints `activation_ref`. This closes the deferred item "Capture who re-activates an approved candidate" as implemented.

## 7. Orchestration

### 7.1 Launch contract

- **Pipelines.** `pl-sec-edgar-backfill`, `pl-sec-edgar-daily` and `pl-sec-edgar-reconcile` each call the shared `pl-sec-edgar-run-worker` with their command. Backfill has no trigger; it is a bounded manual campaign (parent §10).
- **Correlation.** `--run-id` is the calling pipeline's `RunId`. `--attempt-id` is `launch-<n>`, where n runs from 1 to 1 + `orchestration.transient_replays`. Every launch is a new attempt, because replay compares the whole saved context.
- **Execution ID.** On Azure, workflow commands take it from `CONTAINER_APP_JOB_EXECUTION_NAME`, which Container Apps sets in every job execution. `--execution-id` must then be omitted; supplying it is `configuration`. On the local-fixture backend it stays required. The result therefore names the actual execution.
- **Deadline.** `--deadline` is the launch time plus 3,300 s, in UTC. That stays inside the 3,600 s worker allowance and the replica timeout, and leaves 300 s to write the result.
- **Start.** A Web activity POSTs to the job's `start` operation (API `2026-07-01`) with managed identity, audience `https://management.azure.com/`, `turnOffAsync: true` and retry 0. An override replaces the whole template, so the body carries the full container: the name, the image by digest, resources, both environment variables (`SEC_EDGAR_INGEST_WORKER_CLIENT_ID` and `SEC_EDGAR_INGEST_CONFIG`) and the arguments, starting with `--config-env SEC_EDGAR_INGEST_CONFIG`. A test asserts that this container equals the job's own container in everything except the arguments.
- **Start responses.**
  - A 200 response naming an execution under the exact job path is observed.
  - A 202 response is followed only through an HTTPS `management.azure.com` Location on the selected async route.
  - Anything that yields no execution name is `execution_unknown`, never a relaunch.

### 7.2 Observation (D-18)

- **Polling.** The pipeline polls the exact execution GET every 30 s, or after a longer Retry-After. It stops at a terminal state, or at 4,200 s after that launch's start request.
- **States.** A failed GET keeps polling. `Running` and `Processing` keep polling. `Succeeded`, `Failed` and `Stopped` are terminal. `Degraded`, `Unknown`, any unrecognized state and the deadline are `execution_unknown`.
- **No cancellation.** The pipeline never stops an execution.
- **Exit-code assumption.** Container Apps is assumed to mark a non-zero exit `Failed`. S7-08 verifies this.

### 7.3 Result and classification

**Reading the result.** On `Succeeded` or `Failed`, ADF reads `results/runs/sec/<RunId>/<command>/launch-<n>/result.json` with `x-ms-version: 2026-04-06`. Today the worker uploads every object with the SDK default content type. Stage 6 therefore uploads `.json` objects with `Content-Type: application/json`, and the pipeline reads the Web activity's output as the parsed object. The §10 scenarios use exactly that shape. Whether ADF parses it so is an S7-09 assumption; the fallback is `json(…output.Response)`. A result matches when all of these hold:

- `format_version` is `sec-workflow-result-v1`;
- `context.run_id`, `context.command` and `context.attempt_id` equal the launch's;
- `context.execution_id` equals the observed execution name;
- `context.image_digest` and `context.config_sha256` equal the expected values.

**Exit codes are never read.** Pipelines classify by execution state and the result's `outcome`. For a pipeline this also removes the four meanings of exit 2: usage and configuration errors write no result, and approval or rollback refusals never run in one.

| Execution | Result | Pipeline outcome |
|---|---|---|
| Start unknown; not terminal by the deadline; `Degraded`, `Unknown` or unrecognized | — | `execution_unknown` |
| `Stopped` | any | `execution_stopped` |
| Template image is not the pinned reference | any | `execution_mismatch` |
| `Succeeded` or `Failed` | absent or unreadable | `result_missing` |
| `Succeeded` or `Failed` | present but not matching | `result_mismatch` |
| `Succeeded` | matching, outcome with exit 0 | **success** |
| `Failed` | matching, outcome with exit 0 | `result_mismatch` |
| `Succeeded` or `Failed` | matching, `awaiting_approval` | `awaiting_approval`: the distinct gated outcome |
| `Succeeded` or `Failed` | matching, an exit-11 outcome | `stale` |
| `Succeeded` or `Failed` | matching, `pending`, launches remaining | relaunch as `launch-<n+1>` |
| `Succeeded` or `Failed` | matching, any other non-zero outcome | that outcome's name |

Non-zero outcomes are classified by name whatever the terminal state. Gated and stale outcomes therefore stay distinct even if S7-08 shows Container Apps mapping a non-zero exit differently, and none of them is ever success. Only **success** ends a pipeline `Succeeded`. Every other row ends in a Fail activity whose error code is the pipeline outcome. Exit-0 outcomes are those that `results.EXIT_CODES` maps to 0. A test asserts the table covers every key exactly.

**Replay.** Only `pending` is replayed. It means a matching durable result whose unresolved work is all pending, deferred or throttled, with nothing completed or failed. Replays are capped at `orchestration.transient_replays` (1). Nothing else is replayed, including any execution whose state or result is unknown.

### 7.4 Triggers

- **Daily:** `tr-sec-edgar-daily` runs `pl-sec-edgar-daily` — ScheduleTrigger, frequency `Day`, interval 1, `Eastern Standard Time`, hours `[5]`, minutes `[0]`.
- **Reconciliation:** `tr-sec-edgar-reconcile` runs `pl-sec-edgar-reconcile` — frequency `Week`, interval 1, weekDays `["Sunday"]`, hours `[6]`, minutes `[0]`.
- **Start times:** `startTime` values are required deployment parameters with no default, written as local `yyyy-MM-ddTHH:mm:ss` with no `Z` (F1 schedule contract).
- **Disabled by construction:** the template schema has no settable `runtimeState`, and no deployment step starts a trigger, so triggers deploy stopped.
- **No job schedule:** the job is `Manual` and has no schedule of its own.

## 8. Telemetry and alerts (owner decision Q4)

**Worker telemetry.** After writing a fresh workflow result, the workflow command logs one `workflow_summary` event to stderr, which lands in `ContainerAppConsoleLogs`. Its fields:

- the context IDs, command, outcome and counts;
- `member_outcomes` and `gap_codes`, as counts by name;
- `discovery_complete` and `boundary_after`;
- `oldest_unresolved_period`, the earliest source period among the run's unresolved members;
- `pending_approvals`, the `candidates` entries with status `pending`;
- `last_successful_reconcile_at`.

Computing these extras never changes the exit code, stdout or the result. A failure is reported in a `summary_error` field.

**Reconciliation milestone.** After a `reconcile` result with an exit-0 outcome, the worker advances a `WorkflowMilestone` entity in `SourceState`, keyed `reconcile`, to the latest successful `ended_at` and `result_ref`. The update is a compare-and-swap that only moves forward, and the entity can be rebuilt from results. Every summary reports it, which lets the eight-day alert read the latest summary within the two-day query window.

**Monitoring resources.**

- **Workspace:** `law-sec-edgar-dev`, with 90-day retention.
- **Container Apps logs:** the environment logs to `azure-monitor`, with a diagnostic setting sending `ContainerAppConsoleLogs` and `ContainerAppSystemLogs` (resource-specific).
- **ADF logs:** an ADF diagnostic setting sends activity, pipeline and trigger runs (resource-specific).
- **Notification:** action group `ag-sec-edgar-dev` emails `mason.lowell@mac.com`.

| Alert | Source | Condition | Enabled at deploy |
|---|---|---|---|
| Failed job | `ADFActivityRun` Fail activities | any pipeline outcome other than `awaiting_approval` and `execution_unknown` | yes |
| Ambiguous start | `ADFActivityRun` Fail activities | `execution_unknown` | yes |
| Lease failure | console events | `ownership_lost` | yes |
| Access block | console events | `access_blocked` | yes |
| Exhausted retry budget | `workflow_summary` | `member_outcomes.retry_exhausted` > 0 | yes |
| Quarantine | console events | quarantined members or outcome | yes |
| Publication conflict | console events | `publication_conflict` | yes |
| Pending approval | `workflow_summary` | `pending_approvals` > 0, on every run | yes |
| Reconciliation staleness | latest `workflow_summary` | `last_successful_reconcile_at` older than 8 days, or absent | no — enabled with the reconcile trigger (Stage 8) |
| Daily discovery staleness | `workflow_summary` | no daily summary with `discovery_complete` in 30 h | no — enabled with the daily trigger (Stage 8) |

A test asserts that every alert query names only events, fields, outcomes and pipeline error codes that the code or pipelines emit. Discovery age and the oldest unresolved source are reported, not alerted, and the runbooks query them.

## 9. Deployment definitions

```text
infra/azure/sec-edgar-ingest/
  main.bicep          subscription scope: group, custom roles, async-observer assignment, module
  main.json           compiled with Bicep 0.38.33; committed; read by the tests
  modules/            storage, identities, registry, monitoring, job, factory, alerts, role assignments
  pipelines/          ADF pipeline JSON, loaded with loadJsonContent
  alerts/             KQL, loaded with loadTextContent
  config/             Azure config template and golden deployment binding (§4)
  image/              Dockerfile and requirements.lock (§3)
```

- **Storage.**
  - Account: StorageV2, Standard_ZRS, Hot, hierarchical namespace on.
  - Access: anonymous Blob access off, shared-key access off, TLS 1.2 minimum, public network access on (F1 selects public HTTPS).
  - Containers: `raw`, `worksets`, `quarantine`, `locks`, `results`, `generations`, `manifests`, `approvals`.
  - Tables: `SourceState`, `Attempts`, `ActivePointers`, `Approvals`.
- **Registry:** Basic, with the admin user off, anonymous pull off, ARM-token authentication on and classic RBAC (F1 D-05/D-06).
- **Job:** a `Manual` job in a Consumption environment, with the §2 job values. It has the `ingest-config` secret and no volumes (§4). It carries the worker and pull UAMIs and no system-assigned identity; the pull UAMI is the registry identity.
- **Factory:** ADF with a system-assigned identity. The pipelines use only Web, Until, Wait, If, Switch, Set Variable, Execute Pipeline and Fail activities.
- **Parameters without defaults:** `configJson`, `configSha256`, `operatorPrincipalId` and both trigger `startTime` values. Region defaults to `eastus`, restricted to eastus, eastus2 and centralus.

`az deployment … validate` and `what-if` call Azure, so they wait for Stage 7. At each plan's exit the check script rebuilds `main.json` with Bicep 0.38.33 and requires a clean diff.

## 10. Offline orchestration checks

All of these read `main.json` and the pipeline and alert sources with the stdlib; the suite needs no external tool.

- **Roles:** the compiled role definitions and assignments equal §5's tables exactly. Wildcard Actions, `listSecrets`, Owner, Contributor and the built-in Jobs Operator or Contributor roles are absent.
- **Triggers:** no `runtimeState` and no start step exist anywhere. Both recurrences equal §7.4, and `startTime` is a required parameter in the no-`Z` local format.
- **Job and configuration:** the job values equal §2 and the rendered config. The config passes `Settings` with the §4.8 defaults. The golden binding and the endpoint spelling hold. The job image derives from the config digest. ADF's start container equals the job container except for its arguments.
- **Pipeline logic:** the run-worker pipeline uses only a whitelisted subset of ADF expression functions. A small interpreter of that subset evaluates the pipeline's actual correlation, polling and classification expressions against a scenario table covering every §7.2 and §7.3 row. Those scenarios include:
  - start unknown;
  - each execution state;
  - the deadline;
  - a missing result;
  - each mismatched context field;
  - every `EXIT_CODES` outcome;
  - the replay cap.

  An unsupported function fails the test, which keeps the interpreter honest. This exercises R4 and D-18 offline on the committed JSON, not on a re-statement of it.
- **Alerts:** the name-reference test from §8, and the enabled/disabled split.

## 11. Contracts for Stage 7

**Deployment inputs:**

- the renderer and template (§4);
- the deployment parameters (§9);
- the operator principal's object ID;
- the trigger start times.

**Pipelines:** names, parameters, `launch-<n>` attempts, the result path, and the outcome codes and replay rule (§7).

**Worker and commands:**

- `SEC_EDGAR_INGEST_WORKER_CLIENT_ID`, `SEC_EDGAR_INGEST_CONFIG` with `--config-env`, and `CONTAINER_APP_JOB_EXECUTION_NAME`;
- `Content-Type: application/json` on `.json` objects;
- the `history` command;
- Azure principal attribution;
- the `sec-approval-activation-v1` object and the `ApprovalActivation` kind;
- `approve`'s `activation_ref`;
- the verify-only operator open.

**Telemetry:** the `workflow_summary` fields, the `WorkflowMilestone` entity, and which alerts Stage 8 enables.

**Local image proof (D1):** the build context script and the smoke script. The release image, its digest, and the live pull, start, state, result, trigger, alert and runtime evidence remain S7-04 to S7-10 and S7-16 to S7-18.

**Assumptions Stage 6 adds to the Stage 7 checks:**

- S7-06: an override's `env` `secretRef` resolves against the job's secrets (§4).
- S7-06: ADF evaluates the nested expressions in the start body's container to native values. Any other evaluation cannot yield a matching result, so the pipeline ends in a non-success outcome and never relaunches (§7.3). (owner, plan 10, 2026-10-13)
- S7-08: Container Apps marks a non-zero exit `Failed`. Classification no longer depends on it (§7.3).
- S7-09: ADF parses a JSON-typed result body into its output object (§7.3).
- S7-18: the container's writable layer holds the worker's temporary space (§3).

**Redeploying triggers:** ADF rejects an update to a started trigger. Any redeploy after Stage 8 enables triggers stops them first and restarts them afterwards, as a recorded release step.

## 12. Verification and boundary

| Requirement | Offline exit proof | Plan |
|---|---|---|
| R4 — selected service boundaries | Compiled template and pipelines: the role matrix, job, factory, storage, registry and monitoring resources at the F1 API versions; the start/poll/result/classification scenarios (§10) | 10 |
| R11 — accepted defaults | The rendered config validates with the §4.8 defaults. The job values, poll interval, observation deadline, replay cap and both recurrences equal the accepted values (§10) | 9, 10 |
| Worker/pipeline delivery | The image smoke runs every command on amd64 (§3). No start, status or result failure scenario reaches pipeline success; gated and stale outcomes stay distinct (§7.3) | 9, 10 |
| `history` deferred item | The command prints lineage, rollbacks and activations, and the runbook uses it | 9 |
| Attribution deferred item | Azure approve and rollback record the token principal and refuse free text. Activation records are written ahead of the swap, are idempotent and keep lost races; `history` lists them | 9 |
| Mistyped-path deferred item | Operator commands refuse a missing store on both backends and never write the registry | 9 |
| Azure in step | Credential selection, the verify-only open, the `ApprovalActivation` routing, the `WorkflowMilestone` routing and the JSON content type are exercised through pinned-SDK mocked transports. `--config-env` loads the same `Settings` as `--config` | 9 |
| Stage exit | Full offline suite, wheel build, help for every command, Bicep rebuild with a clean diff, image smoke | 9, 10 |

**Out of scope:**

- **Azure-side checks:** any Azure deployment, `validate` or `what-if`; the release image build, push and digest (S7-05); and bootstrap of deployment authority. All are Stage 7.
- **Activation and exercise:** trigger enablement and enabling the staleness alerts (Stage 8); runbook exercise and alert email receipt (Stage 7).
- **Network isolation:** private endpoints are out; F1 selects public HTTPS.
- **Other deferred items:** "download evidence outside the retained members", the derived `activated` field and the remaining items.

**Known limitations:**

- The token principal is decoded, not verified.
- Table- and container-scoped RBAC cannot restrict rows, blobs or approval content.
- Start authority is trusted at worker privilege.
- Telemetry rides on console logs, whose attribution is S7-17.
- `oldest_unresolved_period` covers the run's own selection. Daily revisits every pending and failed identity, so the daily figure is the complete one.

## 13. Implementing plans

The stage splits at a dependent seam: the worker contract feeds the definitions.

- **Plan 9 — worker image and operator surface.** It covers:
  - credentials and the verify-only open;
  - `history`;
  - attribution and activation records;
  - the execution ID and `--config-env` from the environment;
  - JSON content type on `.json` objects;
  - `workflow_summary` and the milestone;
  - the config template, renderer and golden binding;
  - the Dockerfile, build context and local image smoke.

  Its header names Stage 6 but does not carry the `Roadmap:` line, so its completion ticks nothing.
- **Plan 10 — Azure definitions and orchestration.** It covers:
  - the Bicep modules and compiled template;
  - the ADF pipelines and triggers;
  - the alerts;
  - the offline orchestration checks;
  - the deployment and operator runbooks.

  It carries the stage-spec stamp verbatim, so its completion ticks Stage 6.

## 14. Owner decisions (2026-10-12)

**D1 — Build and validation facility.** The owner chose: "Local build, Stage 6 only. Install a local container runtime with buildx (amd64 emulation) and Bicep 0.38.33. These are tool installs only, with no Azure or SEC calls. The local image proves the commands run; the release image is still built by ACR quick task in Stage 7 (S7-05), so its digest will differ." Reading:

- This departs from F1 D-08's build method, and only for Stage 6's "the built image runs every command" proof.
- The tools are installed during execution, not planning.
- The Dockerfile stays buildable by an ACR quick task (no `FROM --platform`).
- The local digest is never recorded as the pinned release digest.

**D2 — Stage spec before the plan.** The owner chose a spec first, with this owner-decisions section, following the Stage 2–5 precedent. Stage 6 still routes through `writing-plans`, and the roadmap is unchanged.

**Q1 — Configuration delivery:** the config is rendered from the committed template, stored as a job secret, and reaches the worker through an environment variable that references that secret. The job image is derived from the config's digest (§4).

The owner first chose a secret-volume file. That choice was re-asked the same day after F1's retained Jobs `2026-07-01` start reference showed that an execution override cannot carry volume mounts. The owner then chose the environment-variable form.

**Q2 — Operator access:** `AzureCliCredential` for operator commands and a verify-only open on both backends; the worker UAMI is selected by client ID (§5).

**Q3 — Attribution:** the authenticated principal is recorded in approval and rollback records, and every attempted approve move writes an activation record (§6).

**Q4 — Alerts:**

- the pending-approval alert fires on every run;
- reconciliation staleness at 8 days and daily discovery staleness at 30 h;
- both staleness alerts deploy disabled until their triggers are enabled in Stage 8;
- the recipient is the F1-selected email (§8).

**Defaults for approval with this spec:**

1. Two plans at the §13 seam.
2. Deferred-item scope as in §1.
3. Offline checks on the committed compiled template, with an expression interpreter for the pipeline logic (§10).
4. Replay only of `pending` (§7.3).
5. The 3,300 s worker deadline (§7.1).
6. The execution ID from `CONTAINER_APP_JOB_EXECUTION_NAME` (§7.1).
7. The worker narrowed to read-only on approvals, and one operator role set (§5).
8. The reconciliation milestone (§8).
9. The backfill range `2015Q1`–`open` in the template (§4).
10. Non-zero outcomes classified by name whatever the terminal state (§7.3).
11. `Content-Type: application/json` on `.json` objects, read by ADF as parsed output (§7.3).
12. The four Stage 7 assumptions listed in §11.

## 15. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 6 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

This document is not a live-access authorization. SEC, Azure, credential, deployment and trigger activity remain closed, and all 22 Stage 7 integrated checks remain reserved/not_run.
