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

### Task 1: Establish baseline, decision register and access boundary

**Files:** Create `baseline.md`, `decisions.md`, `access-window.md`, `index.csv`, `discrepancies.csv` under the evidence root above.

**Interfaces:** Consumes approved spec/parent/ADR/roadmap and current worktree. Produces protected baseline, pinned investigation endpoint, recorded decisions and an exclusive bounded access window for Task 2.

- [ ] **Step 1: Capture the repository baseline without mutation.** Run from the repository:

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

- [ ] **Step 2: Initialize evidence registers using the schemas in this plan.** Discrepancy columns are `id,claim,evidence_ids,parent_reference,blocking,proposed_resolution,owner,accepted_revision,accepted_date,status`. Use status `open`, `resolved` or `reserved_stage_7`; a required input left unchosen is open/blocking, not a deferral.

- [ ] **Step 3: Pin evaluation date and end quarter.** Use America/New_York for the run-start date. Store endpoint once and enumerate quarter ordinals inclusively. On 2026-10-05, endpoint is 2026 Q4, yielding 68 intended and 48 development units; on another date recompute both counts and latest closed quarter. Keep these as requested units, separate from discovered source units.

- [ ] **Step 4: Record every approved §4 input and parent acceptance, then request the missing concrete decisions as one batch.** Obtain tenant/subscription UUIDs and cloud, proposed dedicated resource-group name, environment/naming scheme, deployment operator identity and authority, registry location/type and permission mode, pull identity choice, rollback digest retention/availability policy, and deployment-tool prerequisites. Record owner confirmation of these choices; never substitute example UUIDs or a guessed default subscription. New resource principal IDs remain Stage 7 deployment records. Registry and tooling may be proposed during Tasks 4–5, but all concrete choices must be accepted before readiness.

- [ ] **Step 5: Establish one investigation issuer and account for other owner traffic before SEC access.** Record issuer/operator, coordination method, exclusive sampling window and owner traffic allocation. Proposed bounded window: at most 45 minutes, 240 total HTTP attempts including retries, 512 MiB received and 12 initial complete source specimens; request starts spaced at least 1/3 second, sequential, no bursts. Reduce the rate if other owner traffic requires it. This is an investigation limit, not a production settings revision. Pause at the first exhausted budget, new format family or required additional sampling; record a bounded continuation window before resuming. No second issuer, independent retry budget or identity rotation. Honor longer Retry-After; halt on 403/access-denial content. Record unresolved traffic allocation as blocking; independent documentation work can continue.

**Checkpoint:** Baseline protections and decision statuses are reviewable. No live SEC request proceeds without the recorded traffic/window boundary. No readiness is inferred from spec approval.
