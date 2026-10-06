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

### Task 7: Record gated completion and stop at the Stage 1 boundary

**Files:** Only after Task 6 acceptance: update this plan, Stage 1 spec rollout stamp and roadmap Stage 1 checkbox; retire this plan/Stage 1 spec according to writing-plans completion protocol. Parent design spec, ADR and roadmap remain active.

**Interfaces:** Consumes the exact accepted ready finding/reference. Produces authoritative Stage 1 completion provenance and consistency notes; no later-stage plan or execution.

- [ ] **Step 1: Run resolve-before-defer before completion markup.** Missing Stage 1 exit evidence cannot be deferred to manufacture readiness. Resolve skipped tasks/findings requiring owner input. Stage 7 checks are required later-stage obligations, not invented Stage 1 accomplishments. Apply writing-plans deferred-item rules only to legitimate nonblocking leftovers; preserve existing backlog entries.

- [ ] **Step 2: Mark this plan complete and retire with correct links.** Only after all exit gates pass, tick completed steps and record actual execution skill/date and deviations. Apply writing-plans Plan Completion Protocol (backlog tick/append if applicable, health report/triage and restricted-path retirement). Plan 1 final path is `specs/plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md`; Stage 1 spec final path is `specs/completed/sec-filing-index-ingestion-stage-1-spec.md` if no other live plan implements it. Fix links for the extra directory depth; finding/evidence paths stay stable. Do not retire the parent spec or roadmap.

- [ ] **Step 3: Write the authoritative Stage 1 rollout stamp before ticking the roadmap.** Stamp the Stage 1 spec with actual completion date, plan 1 final path and the accepted finding revision/reference, using:

  ```text
  Stage 1: COMPLETE (YYYY-MM-DD) — implemented by plan 1
  (specs/plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md).
  Accepted ready finding: specs/sec-filing-index-ingestion-stage-1-findings.md,
  revision/reference as recorded in its owner acceptance record; accepted YYYY-MM-DD.
  Next: resume the roadmap.
  ```

  Substitute the recorded actual dates and exact accepted revision, not the planning date or example text. Tick Stage 1 only after this stamp exists. Revalidate later roadmap stages against the delivered decisions/evidence as consistency notes or explicitly accepted corrections; do not investigate or plan those stages. Roadmap's draft gap-analysis statements about missing acceptance remain historical baseline, not current completion evidence.

- [ ] **Step 4: Verify final provenance and stop.** Run `git diff --check`, inspect final `git status --porcelain=v1`, recompute protected-change hashes and verify completion stamp/accepted finding/final plan links resolve. If committing, stage only named Stage 1 artifacts and intentionally accepted rollout/retirement edits, never `git add .` or `git add -A`; the formerly untracked roadmap must not be committed incidentally. Report Stage 1 evidence/acceptance/stamp and reserved checks. Later transition requires the owner's separate request to resume the roadmap.

**Checkpoint:** Checkbox, completion stamp, retired implementing plan and exact accepted finding agree. Stop here.
