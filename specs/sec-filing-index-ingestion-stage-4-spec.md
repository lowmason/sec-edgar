# SEC filing-index ingestion — Stage 4: Backfill and daily catch-up workflows

**Status: PROPOSED (2026-10-07) — pending owner approval; implementation not started.**
**Owner:** Lowell Mason.
**Implementing plan:** [Plan 4](plans/4-sec-filing-index-ingestion-stage-4-spec.md).
**Authority:** [Parent design](sec-filing-index-ingestion-spec.md), [ADR](sec-filing-index-ingestion-adr.md), [roadmap](sec-filing-index-ingestion-roadmap.md), accepted [F1](sec-filing-index-ingestion-stage-1-findings.md), completed [Stage 2](completed/sec-filing-index-ingestion-stage-2-spec.md) and [Stage 3](completed/sec-filing-index-ingestion-stage-3-spec.md). Only roadmap Stage 4 / R1 and R2 are proposed here.

## 1. Reconciliation and scope

Primary `main` was safely fast-forwarded from `5f90a2116eab21525e88a02d0988567e71d95967` to locally available `origin/main` at `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`. No network fetch was performed. The [planning receipt](evidence/sec-filing-index-ingestion/stage-4/planning-reconciliation.json) records fresh preservation of 19,089 files / 294,547,731 bytes and four required legacy package-file absences. Prior inventory records showed no drift; five additional ignored build/SDD files were inspected and copied. Four byte-identical untracked evidence collisions were relocated into the preservation directory before the fast-forward, then supplied by the incoming tracked tree. Untracked original Stage 3 plan/spec remain historical inputs in place. Retained original roadmap bytes precede the Stage 3 tick and appended resume note.

Completed Stage 3 spec and Plan 3 establish completion. Their acceptance amendment binds only exact SEC-0141/0142/0143 raw bytes: 21/24/6 conflicting observations, no accepted Processing/ObservationRef and no pointer mutation. Quarantine remains a whole-source refusal. Stage 4 must report those sources as unresolved if encountered; Stage 3 acceptance does not license successful baseline coverage for them. Retained full-suite/build results are historical results, not newly executed Stage 4 checks.

One cohesive workflow subsystem composes existing discovery, collection, transformation and publication. It introduces manually runnable `backfill` and `daily` commands, durable workflow intent/member tracking and reports. It reuses the same four command boundaries and coordination namespace. It does not introduce another parser, downloader, publication authority, or baseline implementation.

## 2. Constraints inherited by Plan 4

The following sentences are copied verbatim from the accepted parent contract:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- `start_quarter` and `end_quarter` are required, inclusive parameters.
- One source file is the checkpoint and retry unit.
- An invalid member prevents a claim of complete coverage, not the retention of work already completed.
- Daily discovery starts at the approved handoff date and replays overlap with the baseline.
- Deduplication handles overlap; a calendar cutover is not trusted to prevent it.
- Also revisit pending and failed source identities regardless of their quarter.
- Never advance discovery past a failed directory read.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- The pointer update is the publication boundary.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Carry accepted pins unchanged: Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, existing complete `uv.lock`. No new dependencies. Preserve 90-second exchange, 67,108,864 received-byte and 536,870,912 expanded-byte guards; 3 requests/second/no bursts; one issuer; five total HTTP attempts; accepted 3,600-second worker allowance; 8,192-row ETL batches/SQLite scratch. These are selected limits, not measured deployed fit.

All live-access authorizations remain closed. Use offline evidence and fixtures only. All 22 Stage 7 integrated checks remain reserved/not_run. No SEC/Azure/authentication/compute/provisioning/deployment/image build/network fetch or trigger enablement is authorized. An unavailable cached dependency blocks execution rather than authorizing a fetch or changed pin. Raw/observation/generation/manifest/candidate/quarantine/report retention remains indefinite during development. Existing binding registry/config/workset bytes must not be rewritten.

## 3. Workflow intent and discovery

Public interface: `sec-edgar-ingest backfill|daily --config PATH --run-id ID --execution-id ID --attempt-id ID --deadline UTC [--state-dir PATH --fixture-pack PATH --today YYYY-MM-DD]`. Backfill obtains mandatory inclusive endpoints from existing `backfill.start_quarter` / `backfill.end_quarter`; `open` resolves once to a pinned quarter. Daily uses accepted `daily.start_date` **2026-10-01**, current/open and preceding quarters, outage-spanning quarters and all older unresolved source/directory units. No additional implicit start year. F1's intended 2010Q1 and development 2015Q1 starts remain selections; no range is declared globally supported by fixture success.

A workflow attempt freezes command, correlation IDs, pin date, actual endpoint, exact effective settings/hash, image/parser/schema, deadline and fixture manifest hash before dispatch. Exact completed replay returns its immutable report with no discovery/SEC sender construction, even after deadline. Different correlation/config/version/date/deadline/fixture bytes for the same result path refuse. Interrupted exact replay reuses saved child command identities; a completed failed child attempt is immutable, so retry uses a new workflow attempt or a new run, not a rewritten old result. No automatic failure replay is added here; the parent's maximum one transient orchestration replay remains Stage 6's ceiling.

Invoke shipped `discover` with one deterministic discovery ID per run and exact child attempt IDs. Keep its required-unit ledger, actual-parent traversal, CAS gap tokens, immutable listing receipts and conservative daily boundary. A failed directory preserves the prior boundary. Discovery success can advance independently of publication; unresolved source tracking prevents that progress from hiding ETL backlog. First run uses handoff/overlap; new runs discover fresh listings rather than treating a prior successful DiscoverySession as current.

## 4. Exact per-source work and durable unresolved units

After reading and validating the discovered source workset, derive one complete source workset for each member whose immediate directory succeeded. Retain parent workset ID/ref plus the exact member and its immediate DirectoryOutcome/listing hash. Projection may only reduce that directory's `source_ids` to the member; it may not alter the source, origin context, endpoint, overlap, acquisition mode or original listing provenance. Store canonical bytes at the ordinary content-addressed source-workset path; persist the projection's parent binding before executing children. Keep all failed parent directories in the workflow report. Never reinterpret the parent as discovery-complete.

Persist immutable `WorkflowMember` records in existing SourceState, keyed by projected workset ID. Persist per-attempt `WorkflowMemberResult` receipts, linking collection/snapshot/transform/publish refs, per-quarter outcomes and origin acquisition config. Derive pending work from the union of current discovery members and every member without a successful complete receipt under current parser/schema; source-id equality alone cannot mark a processing identity successful. Downloaded-but-untransformed, transformed-but-unpublished, quarantined, gated and partially published members remain visible across runs, independent of discovery's `needs_acquisition` flag. An old valid member remains eligible even if a newer listing omits it; collection resumes from its retained canonical source and pinned bytes. An absent listing never supplies withdrawal authority.

Process sources sequentially in period/source-id/workset-id order. For collection use the exact projected workset's origin effective settings and versions; preserve binding and accepted raw pins. For transform/publish use the current workflow's pinned settings/parser/schema, retaining origin provenance. Reuse existing CLI exact invocation/result repair boundaries through a checked child dispatcher; read and validate durable results rather than trusting a printed outcome or exit code alone. Never select a mutable latest snapshot. If a parser replay is required, use Stage 3's contributing-input reprocessing rules; do not combine versions ad hoc.

Each valid source can finish while an unrelated source fails. Shared halt/access/ownership errors stop later acquisition dispatch immediately; deadline expiration retains undispatched work as pending. Continue already completed, safe independent work only within the shared deadline. `PublicationRepairPending` or a crash after CAS leaves the exact publish command resumable; neither workflow result nor member completion may be finalized until child repair completes. No workflow lock substitutes for the shipped coordinator or publication CAS.

## 5. Publication and reports

Use existing `run_transform`/`run_publish` command interfaces, processing identity, active-pointer reader, immutable generation manifests, source selection/precedence, withdrawal gate and post-CAS repair. Publish every affected output quarter, including quarters preceding a daily filename's period. Open-quarter baseline seed and daily overlap use the same logical keys. Closed-quarter removals remain `awaiting_approval`; Stage 4 exposes no approval mutation or force bypass.

Durable `runs/sec/<run-id>/<backfill|daily>/<attempt-id>/result.json` is the workflow result authority; write canonical bytes before a repairable WorkflowAttempt index. Version is `sec-workflow-result-v1`. Report exact context/intent, requested baseline units or required discovery directories, parent/member/snapshot/transformed workset refs, child result refs, complete/pending/failed source units, quarantines, awaiting-approval candidates, every quarter's outcome and captured generation, gaps, boundary before/after, counts and start/end times. Counts are source units for discovered/downloaded/transformed/completed/pending/failed/quarantined, and quarter operations for published/unchanged/awaiting_approval; labels make the distinction explicit. No maximum date substitutes for coverage. Complete/pending/failed are disjoint; quarantine is a failed subset, gate is a pending subset. Keep error details and raw hashes/line reasons from child reports.

`success` requires successful required discovery, all requested quarterly units accounted for, and every selected/retried member fully published or unchanged in all affected quarters. A valid empty quarterly listing is an unresolved baseline unit, even if discovery itself succeeds. For daily, valid listings and no new/unresolved members produce `no_new_sources`; failure, missing directory, old backlog or unpublished sources prohibit that outcome. A successful repeat with unchanged input produces `unchanged` and no new logical filings. Fatal outcomes keep existing exit codes; mixed progress is `incomplete`; all-quarantined is `quarantined`; gate-only unresolved work is `awaiting_approval`; no coverage success is synthesized from a child stdout status. Partial quarter advancement is reported, never rolled back automatically.

## 6. Verification and later-stage boundary

| Requirement | Offline exit proof | Plan tasks |
|---|---|---|
| R1 / §§4.1–4.2 | Inclusive fixture backfill, closed/open quarters, exact baseline accounting, empty quarter and invalid member with retained valid quarter progress | 1–5, 7 |
| R2 / §4.2 | First handoff/overlap, multiple-outage-quarter catch-up, Q4/Q1 transition, older acquisition/ETL/gated backlog, failed-directory boundary hold, valid empty daily distinction | 2–5, 7 |
| §4.5 / §4.7 | Frozen intent, member receipts, exact completed replay, interrupted child/report repair, durable result counters/gaps/captures | 1, 3–5, 7 |
| §4.8 / §§5–6 | Validation before adapters, exact version/binding compatibility, halt/deadline, named exits, network/auth guard and regression/build/installed-wheel proof | 5–7 |

Each implementation task runs a meaningful red/green cycle and scoped review. Completion requires full offline suite/build/help/version/compile/whitespace checks, fresh installed-wheel backfill/daily/read proof, hash-bound fixtures/results, resolved reviews and owner review of coverage. No native test discharges deployed integration, measured worker memory/runtime/scratch, real identities/HNS/ETags/connectivity, smoke, approval/rollback or observed schedules. Stage 5 owns reconciliation and approval operations/R5/R7/R10; Stage 6 owns the complete worker image/IaC/ADF/disabled schedules; Stage 7 owns all 22 integrated checks; Stage 8 owns production coverage and activation.

## 7. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 4 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

Stop for owner approval of this spec and Plan 4 before implementation. This document is not a completion stamp or live-access authorization. After implementation and review, apply `writing-plans` completion protocol, retire only Stage 4's plan/spec, stamp Stage 4 then tick its roadmap entry. Preserve historical primary inputs and all four legacy file absences throughout; never use `git add -A` or stash/reset/restore in the primary checkout.
