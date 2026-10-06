# Stage 1 decision register

Owner/decider: Lowell Mason. Category of accepted entries: **Owner decision**.
Accepted document revisions and policy values are separate from unresolved concrete inputs.
Owner questions were sent by the root chat and are pending; no proposal is acceptance.

## Accepted document revisions

| Document | Accepted revision | Acceptance date | Boundary |
|---|---|---|---|
| `specs/sec-filing-index-ingestion-stage-1-spec.md` | SHA-256 `bb28b0c27646d4f7b15669660e56c230d3247148966e3b075b96ca196a0b5140` at approval HEAD | 2026-10-05 | Written contract/investigation scope; no readiness acceptance |
| `specs/sec-filing-index-ingestion-spec.md` | SHA-256 `6c4f27aead06659864497c737ddd8f29a07d4ee0f671cd5c22529da857e89b93` at approval HEAD | 2026-10-05 | Written contract/investigation scope; no readiness acceptance |
| `specs/sec-filing-index-ingestion-adr.md` | SHA-256 `55852d3b85ba2e6f7c0cbf1559615e769f751fda01a7f781fb5e73ff6a337807` at approval HEAD | 2026-10-05 | Written contract/investigation scope; no readiness acceptance |

The parent spec's acceptance record accepts the ADR/spec and operating defaults. Stage 1
§4 records the selected inputs. Draft/proposed wording elsewhere preserves document provenance;
it does not revoke the acceptance record. The roadmap remains untracked and unticked, with its
original hash protected; its stale gap-analysis acceptance wording is not readiness evidence.
No contract revision or accepted readiness finding has been produced by this task.

## Accepted Stage 1 §4 inputs

| Input | Accepted value | Reference | Acceptance |
|---|---|---|---|
| Intended historical range | 2010 Q1 through the open quarter inclusive | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Initial development range | 2015 Q1 through the open quarter inclusive | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| End-quarter rule | Resolve and pin at each run's start | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Daily handoff | 2026-10-01; retain parent §4.2 overlap | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| SEC User-Agent | Lowell Mason sec-edgar-ingest mason.lowell@mac.com | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Azure target | New dedicated resource group in an existing subscription | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Region order | eastus, then eastus2, then centralus | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Networking | Public HTTPS; managed identities; scoped roles; anonymous blob access disabled | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Infrastructure as code | Bicep | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Python/container candidate | Python 3.14; Linux amd64 | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Initial compute candidate | General-purpose Consumption; 2 vCPU; 4 GiB RAM | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Initial execution settings | One replica; parallelism 1; completion count 1; timeout 3,600 seconds | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Initial storage candidate | Standard general-purpose v2; HNS enabled; Hot; ZRS | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Ingestion-artifact retention | Indefinite during development: raw snapshots, observations, generations, manifests, approvals, quarantine evidence, run reports | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Operational-log retention | 90 days | Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Alert owner/destination | Lowell Mason; mason.lowell@mac.com | Stage 1 §4 | Lowell Mason; 2026-10-05 |

Resource settings remain starting candidates. Exact runtime pins/probe results, provider support,
and actual Stage 7 memory/runtime or effective deployed permissions are separate evidence.

## Accepted parent defaults and safeguards

| Setting | Accepted value | Reference | Acceptance |
|---|---|---|---|
| Daily schedule | 05:00 Eastern daily; supported ADF identifier/DST evidence pending | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Reconciliation schedule | Sunday 06:00 Eastern; all supported quarters | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| SEC target/collectors | 3 requests/second, no bursts; 1 active collector across application pipelines | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| HTTP attempt budget | 5 total attempts per request including first | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Retry delay | 2-second exponential/jitter base; 120-second local cap; honor longer server delays | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| HTTP timeouts | 15-second connection; 60-second read | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Native job retries | Zero; no automatic retry of ambiguous starts | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Transient-failure replay | At most 1 automatic confirmed-transient-failure replay | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Withdrawal approval | Required for every closed-quarter candidate removing keys | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |
| Versions | Required explicit parser/schema/worker digest per workset | Parent §4.8; Stage 1 §4 | Lowell Mason; 2026-10-05 |

The parent safeguards remain authoritative: §4.2 requested/discovered coverage and overlap;
§4.3 coordinated identity/access; §4.4 precedence and withdrawal gate; §§4.5–4.6 exact raw
inputs, immutable generations and conditional pointer publication; §§4.7–4.9 and §5 recovery,
identity and failure handling. Package/workload authority is parent §§2, 4.1, 4.9 and ADR Decision.
No resource-profile comparison or weakening of these contracts is authorized.

## Required concrete decisions

| ID | Required choice | Reference | Status | Acceptance |
|---|---|---|---|---|
| D-01 | Tenant and subscription UUIDs; Azure cloud | Stage 1 §5.3; parent §4.9 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-02 | Dedicated resource-group name | Stage 1 §§4, 5.3 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-03 | Environment and naming scheme | Stage 1 §5.3; parent §4.9 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-04 | Deployment operator identity and authority | Stage 1 §5.3; parent §4.9 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-05 | Registry location/type and permission mode | Stage 1 §5.2 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-06 | Image-pull identity choice | Stage 1 §§5.2–5.3 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-07 | Rollback digest retention/availability policy | Stage 1 §5.2; parent §4.7 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-08 | Deployment-tool prerequisites | Stage 1 §§5.2–5.3 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |
| D-09 | Owner-wide SEC traffic allocation and exclusive window confirmation | Stage 1 §5.1; parent §§4.3, 4.8, 5 | OPEN/BLOCKING | Pending Lowell Mason; no accepted value/date |

No tenant/subscription UUID, default subscription, concrete resource-group name, registry or
operator is inferred. Registry/tooling options may be proposed later; owner acceptance is
required before readiness. Newly created resource principal IDs are **Reserved Stage 7 check**,
not missing existing-owner bindings. Effective permissions, quotas/capacity and actual Azure
integration are also Stage 7 checks; they do not excuse unresolved concrete Stage 1 choices.

## Timestamped execution prerequisites

The copied `prerequisites-initial.json` retains exact root command observations:
`uv --version` returned 0.12.15 (exit 0); `docker version`, `docker buildx version`,
`az version` and `az bicep version` were absent (exit 127).
Separately, root reported a broader `shutil.which` search found no docker, podman,
colima, limactl, nerdctl, container or named x86_64 QEMU facility on the macOS arm64
host. That broader search is root-reported and is not a command result retained in
the copied JSON. Neither observation establishes a selected deployment setup.

The owner separately requested Azure CLI installation. Root verified Azure CLI **2.90.0**
with exit 0 at **2026-10-05T23:08:19.306595+00:00**, retained in
`azure-cli-verification.json`. This later observation preserves the initial absent result;
it does not establish authentication, account selection, deployment authority or resource access.

**D-12 OPEN/BLOCKING:** no available Linux amd64 execution facility has been established for
the required combined container-runtime probe. Resolution belongs to the root/owner: provide
or accept an isolated execution facility and then retain reproducible probe evidence.
Local tooling installation alone cannot discharge Task 4 or Stage 1 readiness.

## Root-reported Azure authentication observation

Root report received at **2026-10-05T23:13:05.217073+00:00**; this is receipt time, not an invented exact
Azure call access timestamp. Owner authorized Azure CLI installation and subsequently
stated, “I would much rather you get an Azure authentication or resource setup.”
Root reports `az login --output none` exited 0 through browser authentication and
selected the sole available subscription 1 for the CLI session.

Root-reported `az account show` cached metadata (exit 0): AzureCloud; Enabled;
tenant `0bb72127-3aa2-408f-a5e4-ba9abcfc6db6`; subscription
`3c92a216-8ed6-4897-b741-11ed287b8617` (LGM Consulting); user
`mason.lowell@mac.com` (type user). Exact command/results and limitations are retained
in `azure-auth-root-report.json`; no credential or token data are retained.

Category: **Source/probe observation**. These observed IDs are concrete candidates,
but **D-01 and D-04 remain OPEN/BLOCKING**: owner acceptance of deployment binding,
operator and effective authority is pending. CLI session selection does not constitute
accepted deployment selection. Cached account metadata does not prove effective roles;
no Azure resources were read or created by these observations.

The owner initially preferred Azure-hosted probing; the subsequent explicit existing-VM
direction below supersedes the unresolved-host-direction assessment. New provisioning remains
outside Stage 1. D-12 remains OPEN/BLOCKING pending a concrete host/access/capability.
SEC traffic allocation/window confirmation is still unanswered and the inactive zero-access
ledger remains in effect.

## Owner answer: binding undecided; existing VM direction

Owner decision date: **2026-10-05**. Root report received `2026-10-05T23:14:36.236507+00:00`.
On whether to accept observed Azure cloud/tenant/subscription as deployment binding, Lowell
Mason answered exactly **“Keep binding undecided”**. D-01 deliberately remains OPEN/BLOCKING;
no default binding is inferred from CLI selection or upcoming inventory.

On runtime-host direction for the isolated compatibility probe, Lowell Mason answered exactly
**“Use an existing Azure VM”**. This selects the existing-VM direction; it does not choose a
concrete host, access path or demonstrated isolated Linux amd64 capability. D-12 remains
OPEN/BLOCKING for those concrete prerequisites. No new resource provisioning or Stage 1
scope amendment is authorized or required merely to investigate existing host candidates.
Root is conducting read-only candidate VM inventory in the explicitly supplied observed
subscription `3c92a216-8ed6-4897-b741-11ed287b8617`; that inquiry does not accept it as the
deployment binding. Inventory results are separate evidence, not established by this answer.
Exact answers/question contexts are retained in `owner-binding-host-direction.json`.

Root-reported VM inventory received `2026-10-05T23:15:09.473633+00:00`: the retained `az vm list` command exited 0
and returned `[]` in the observed subscription. This is an actual ARM read reported by root,
not merely cached account metadata. It establishes only that no VMs were returned to this
actor by this inventory; it does not prove global VM absence or authority beyond this read.
Root requested a specific existing VM resource ID and access method from the owner.
D-12 remains open/blocking. Record: `azure-vm-inventory-root-report.json`.

## Accepted narrow temporary probe exception

Owner Lowell Mason answered exactly **“Accept temporary probe proposal”** on 2026-10-05.
Root report received `2026-10-05T23:24:21.325547+00:00`. Accepted immutable proposal: `probe-setup-proposal.md`,
**revision 1**, SHA-256 `5946673f1cdd8fc3a346ae61b4a2d711cccb3fa660031060a412f1b8e5ffeb84`. Its original “pending” status text is preserved;
explicit acceptance is a separate record. Root-reported acceptance is retained in
`temporary-probe-acceptance-root-report.json`; setup-agent `probe-setup/acceptance.json`
is now retained separately at `2026-10-05T23:24:41.527771+00:00` and confirms this exact
revision/hash and zero task runs submitted during setup.

Acceptance authorizes only temporary Basic ACR/RBAC registry permissions and dedicated group
`rg-sec-edgar-stage1-probe-20261005`, registry `secedgarstage1probe20261005b8617`, eastus,
AzureCloud tenant `0bb72127-3aa2-408f-a5e4-ba9abcfc6db6` and subscription
`3c92a216-8ed6-4897-b741-11ed287b8617`, with operator `mason.lowell@mac.com`.
It authorizes `Microsoft.ContainerRegistry` registration (not unregistering on cleanup),
bounded quick-task probes and exact dedicated-resource cleanup after evidence retention.
No role assignments, production resources/images, worker publication or automatic triggers.

Method adaptation: ACR quick tasks replace local Docker commands; actual compatibility probes
remain **Task 4 in ordered execution**. At most four sequential submitted runs, including
failed/canceled runs; linux/amd64, two vCPU, 1,800-second timeout, no cache, no push;
USD 5 operational budget (not Azure-enforced) and maximum 24-hour lifecycle from creation.
Only reviewed isolated `/private/tmp` contexts may be uploaded. Cleanup authority is limited
to the proposal's exact registry/group resource IDs with inventory verification and retained
outcomes; unexpected contents require stopping group deletion. Original specs/plan remain
unchanged; this ledger records the explicit exception acceptance and method deviation.

The earlier existing-VM direction is preserved as history and superseded for this probe by
this accepted proposal. **D-01 remains deliberately OPEN/BLOCKING**: temporary accepted
binding is not accepted production deployment binding. **D-12 remains OPEN/BLOCKING** pending
actual facility setup and native probe evidence. Setup is in progress under a separate agent;
no create/run/expiry result or effective authority is inferred here. SEC allocation/window
remains unanswered/inactive. No production success or Task 4 completion is claimed.

## SEC allocation/window confirmation accepted

Owner Lowell Mason replied exactly **“Confirm window; all other SEC traffic paused”** on
2026-10-05. `sec-window-owner-acceptance.json` retains question boundary and answer. Other
owner traffic is 0/paused; root sole sequential issuer at maximum 3 rps, no bursts, starts
at least 1/3 second apart. Accepted caps: 45 minutes from recorded activation, 240 attempts
including retries, 512 MiB and 12 specimens. **D-09 resolved**. Authorization is recorded;
actual start/end activation waits for root Task 2 checkpoint and zero accounting remains.
This accepted operational boundary does not choose unresolved production deployment inputs.

The separate acceptance record has been indexed as E-TEMPACCEPTANCE. Its existence proves
accepted scope only; setup outcomes, actual expiry and native compatibility remain separate
future observations. Task 1 source-access controls are prepared for root reviewer assessment:
protected baseline, requested endpoint, accepted access allocation/caps, sole issuer, zero
ledger and explicit unanswered production choices. Root alone may activate the window after
its ordered Task 2 checkpoint. Full readiness still requires all concrete choices and evidence.

## Latest Task 4 investigation observation (2026-10-05 local date)

Category: **Source/probe observation**, not a new owner deployment decision. Earlier open facility/tooling statements above are retained history. Actual exact compatibility proof now resolves D-12 for the probed minimal combination: official Python 3.14.8 Debian bookworm Linux amd64 child digest `sha256:d1e795fbdab8a4744432467f32f348c6baa99f07abc05ffde710913f65c8261d`; glibc 2.36; ABI `cpython-314-x86_64-linux-gnu`; pip 26.2.1; 21-distribution binary-wheel hash lock SHA-256 `523b2da36079ce4a7c6b11ac06feb0a7992a8c3aef757c32909850685023b5c2`. Resolver ca2 and both independent fresh uncached validations ca3/ca4 succeeded. Each validation passed all 15 commands, all 21 distribution imports (including native cryptography/cffi), synthetic Parquet and all ten retained specimen receipt decodes; root independently rehashed all 158 exported artifacts. Receipts are under runtime/results/, with the root check in root-native-output-verification.json. Task-scoped spec/quality review remains pending at this observation.

The CLI argument failure occurred before upload/submission and consumed zero tasks. The retained ca1 scanner failure consumed one; all four actual submissions are exhausted. The FROM-only correction is retained alongside the explicit SDK CPU/cache/platform/push/timeout request. This establishes a compatibility combination, not Azure credential/data access, production worker image publication, parser coverage, service eligibility, worker memory/runtime or deployment authorization. DFS omission remains provisional pending Task 5's per-object Blob/DFS lifecycle decision; adding a DFS dependency requires a new exact proof and separately authorized compute.

The temporary registry and dedicated group were deleted after retained-output verification; absence was independently verified at `2026-10-06T00:51:14.960875+00:00`, before the accepted expiry. Provider registration remains, as authorized. Cleanup evidence: probe-setup/cleanup-summary.json and its ten hashed receipts. Actual billed cost was not queried; neither the retail estimate nor cleanup proves zero cost. No temporary resources or remaining run allowance are available.

D-01 remains deliberately OPEN/BLOCKING, and D-02–D-08 concrete production selections remain unresolved. Temporary probe acceptance does not select production cloud/tenant/subscription/group/operator/registry/rollback. Azure CLI 2.90.0 and uv 0.12.15 are observed; local Docker/buildx and Bicep CLI remain absent. Missing deployment tooling is a recorded prerequisite, not authorization to install/repair. SEC sampling is closed with 150 attempts, 15,293,779 bytes and ten complete specimen receipts; all other-owner traffic was released. No new SEC access is authorized. Stage 1 remains unticked and readiness/acceptance are pending.
