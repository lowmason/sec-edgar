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

### Task 6: Assemble readiness finding and obtain exact-revision acceptance

**Files:** Create `specs/sec-filing-index-ingestion-stage-1-findings.md` and `readiness-checklist.md`; finalize index, discrepancies, decisions and evidence hashes.

**Interfaces:** Consumes Tasks 1–5 artifacts. Produces a ready/not-ready finding and, only when ready, owner acceptance naming its immutable revision/hash and limitations.

- [ ] **Step 1: Write the nine required finding sections.** Use the Stage 1 §7 list as the exact content checklist: conclusion/evaluation endpoint/contract revisions/boundary; decisions and deployment bindings; quarterly/daily inventory and gaps; exact runtime/probes; Azure APIs/states/permissions/DST; resource/space and retry rationale; discrepancy resolutions; Stage 2 handoff and Stage 7 register; owner acceptance. Cite evidence ids and paths for every material claim. Record parent §4.2 overlap, §4.4 nullable accession/withdrawal rules, §§4.5–4.6 original-byte/replay/publication safeguards without rewriting them. Stage 2 handoff identifies broken root workspace membership/CLI and redundant scaffolds; no repairs are performed and no Stage 2 plan is written.

- [ ] **Step 2: Run the §8 readiness gate line by line.** Map each requirement to artifact/row/decision and pass/block status. Confirm complete requested-quarter accounting; required daily/transition/family specimens or explicitly accepted gap revisions; exact digest/locks; successful isolated combined probes; selected provider/API/tool/permission evidence; concrete tenant/subscription/group/operator/registry/naming decisions; recorded parent acceptance. Missing runtime proof, traffic allocation, binding or unresolved required capability is blocking, not merely a Stage 7 entry. Genuine integrated-deployment checks may remain reserved with clear obligations.

- [ ] **Step 3: Resolve discrepancies before a ready conclusion.** Show the owner one batch of decisions/contract revisions that need acceptance, linked to evidence and effects. Update the affected accepted contract only with explicit revision acceptance. Repeat impacted checks/probes and update references; unsupported sources/settings cannot weaken safeguards. If blocked, conclude not ready and preserve all evidence. A not-ready report can be reviewed, but the plan and Stage 1 remain incomplete; no completion protocol or stage tick follows.

- [ ] **Step 4: Validate evidence integrity and preservation.** Recompute hashes, verify every local evidence link exists, match specimen byte counts, check all required probes' exit codes, reconcile counts/categories and scan for unsupported success claims. Run `git diff --check` (expected exit 0) and `git status --porcelain=v1`; compare protected paths/status/hashes with Task 1. Recheck original approval commit/reference. No code build/test is needed to validate documentation, and the broken workspace must not be repaired for this check.

- [ ] **Step 5: Present the ready finding for owner acceptance by revision/date.** First freeze the reviewable evidence/finding revision (commit restricted paths when authorized, or use finding SHA-256 plus evidence-manifest SHA-256). Request acceptance from Lowell Mason of that exact ready conclusion, supported boundary, decisions and listed limitations. Record the accepted pre-acceptance finding hash/revision and acceptance date in the finding; retain the reviewed version so adding the acceptance record does not invalidate its referent. Any material change after acceptance requires renewed acceptance of the new revision. No automatic acceptance inferred from a prior spec approval or silence.

**Checkpoint:** An owner-accepted **ready** finding exists with reproducible evidence and no blocking uncertainty. Until this checkpoint passes, retain the unexecuted/in-progress plan and unticked Stage 1.
