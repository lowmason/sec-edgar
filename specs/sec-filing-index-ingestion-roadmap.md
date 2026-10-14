> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

## Gap analysis

**Derived:** 2026-10-05. **Status:** stage partition pending approval; implementation has not started.
**Sources:** [Design spec](sec-filing-index-ingestion-spec.md) and
[ADR](sec-filing-index-ingestion-adr.md). All § references below refer to the design spec unless
marked ADR. The owner confirmed index-only scope and inclusion of workspace alignment in this roadmap.

The repository contains package scaffolds, not an ingestion implementation. The search covered all
tracked files and current untracked files, including `packages/`, configuration, tests, infrastructure,
documentation and `specs/`. No existing roadmap header, completed stage stamps or
`specs/deferred_items.md` was found. Deployed Azure resources were not inspected.

Evidence shorthand: **S** = `packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py:1`
(`hello()` only); **W** = `pyproject.toml:19` (workspace membership).
“None found” refers to the repository search boundary above.

| Req | Verdict | Evidence (path:line, plan id, or none found) | Note |
|---|---|---|---|
| R1 | missing | S; none found | No baseline workflow. |
| R2 | missing | S; none found | No daily workflow. |
| R3 | missing | S; none found | No parser or transformation. |
| R4 | missing | None found in `infra/`, configuration or deployment files | No Azure stack or orchestration definitions. |
| R5 | missing | S; none found | No shared workflow implementation. |
| R6 | missing | S; none found | No raw snapshots or replay path. |
| R7 | missing | S; none found | No reconciliation workflow. |
| R8 | missing | S; none found | No downloader or shared request coordination. |
| R9 | missing | S; none found | No generation publisher or reader interface. |
| R10 | missing | S; none found | No withdrawal gate or approval interface. |
| R11 | missing | None found in configuration, worker or pipeline files | No validated operating defaults. |
| Package boundary (§4.9; ADR Decision) | implemented-differently | W; `packages/sec-edgar-client/src/sec_edgar_client/__init__.py:1`; `packages/sec-edgar-download/src/sec_edgar_download/__init__.py:1` | Spec/ADR select one implementation package; the workspace also includes client/download scaffolds and references the locally deleted index-ingest package. The root CLI at `pyproject.toml:13` references an absent module. |
| Readiness (§7 step 1; §10) | missing | `specs/sec-filing-index-ingestion-spec.md:3`; `specs/sec-filing-index-ingestion-adr.md:3`; none found | Acceptance, deployment inputs and source/provider findings are not recorded. |
| Error outcomes (§5) | missing | S; none found | No structured errors or recovery outcomes. |
| Verification (§6) | missing | None found in tests, fixtures or CI configuration | No automated verification. |
| Worker/pipeline delivery (§7 step 2) | missing | S; none found | No runnable image or orchestrated pipelines. |
| Isolated integration (§7 step 3) | missing | None found in tests or run reports | No deployed integration or fault-injection evidence. |
| Live smoke (§7 step 4) | missing | None found in run reports | No measured source/runtime evidence. |
| Replay/recovery rehearsal (§7 step 5) | missing | None found in tests, reports or runbooks | No offline replay, approval or rollback evidence. |
| Baseline rollout (§7 step 6) | missing | None found in release or run reports | No accepted historical coverage record. |
| Daily activation (§7 step 7) | missing | None found in release or run reports | No accepted catch-up or trigger-enablement record. |
| Reconciliation activation (§7 step 8) | missing | None found in release or run reports | No accepted initial reconciliation or trigger-enablement record. |
| Scheduled acceptance (§7 step 9) | missing | None found in release or run reports | No observed scheduled executions. |
| Documentation/infrastructure (§8) | missing | Empty root/package READMEs; none found in `docs/` or `infra/` | No runbooks or versioned deployment definitions. |

§4 elaborates R1–R11; its numbered backfill and publication steps are covered by those rows.
The additional rows track repository alignment and the separately observable delivery/rollout gates.
The `hello()` scaffolds establish no ingestion behavior outside the spec; no other extra behavior
or implementation owned by another repository was found.

## Stages

There is no priority ranking in the spec. This order follows the deployment-before-activation
sequence in §§7 and 10, while splitting implementation by dependency: acquisition, publication,
workflows, then Azure integration. Readiness goes first because its findings determine the supported
range and implementation environment. Each build stage includes its applicable §5 handling and §6
tests; Stage 7 consolidates acceptance evidence rather than postponing testing until deployment.
Production triggers remain disabled through Stage 7 (§7).

- [x] Stage 1: Scope and feasibility findings
      Objective: Establish an accepted implementation boundary and resolve source, runtime and deployment prerequisites before building.
      Spec: §§2, 4.8–4.9, 7 step 1, 10; ADR Decision and Consequences.
      Gap closed: Readiness.
      Consumes: Source spec/ADR, repository inventory and owner-confirmed scope/package alignment.
      Produces: Accepted stage spec and written findings recording the supported range, handoff, deployment inputs, provider/version checks and resolution of blocking uncertainties.
      Exit: An owner-accepted readiness finding identifies a viable supported source/runtime combination and records the decisions needed to unblock subsequent stages.
      ROUTING: brainstorming

- [x] Stage 2: Durable discovery and collection
      Objective: Deliver a runnable acquisition boundary that retains exact inputs and resumes incomplete source work.
      Spec: §§4.1–4.3, 4.5, 4.8–4.9, 5–6; ADR Decision.
      Gap closed: R8; Package boundary.
      Consumes: Stage 1 findings and accepted source/configuration boundaries.
      Produces: Aligned workspace and ingest CLI, validated acquisition configuration, discovery worksets, pinned raw snapshots and durable source/attempt state in the §4.5 contracts.
      Exit: Concurrent-collector and takeover fixtures show one coordinated request issuer (R8); workspace build and CLI checks succeed with the ADR-aligned package boundary (Package boundary).
      ROUTING: writing-plans

- [x] Stage 3: Replayable ETL and safe publication
      Objective: Turn retained snapshots into readable quarter generations with deterministic replay and recoverable commits.
      Spec: §§4.4–4.6, 5–6.
      Gap closed: R3; R6; R9.
      Consumes: Stage 2 pinned snapshots, state interfaces and supported source fixtures.
      Produces: Versioned observation outputs, canonical catalog generation builder, change reports, publisher and pointer-resolving reader interface; §4.4 gates apply from first publication.
      Exit: Golden fixtures yield the expected normalized rows (R3); raw-only replay makes no SEC requests or duplicate filings (R6); crash and competing-publisher fixtures expose complete generations without lost updates (R9).
      ROUTING: writing-plans

- [x] Stage 4: Backfill and daily catch-up workflows
      Objective: Compose acquisition and publication into manually runnable historical and daily workflows.
      Spec: §§4.1–4.2, 4.5, 4.7–4.8, 5–6.
      Gap closed: R1; R2.
      Consumes: Stage 3 shared acquisition/ETL interfaces and Stage 1 range/handoff decisions.
      Produces: Parameterized baseline and daily workflows, durable discovery boundaries and run reports that later orchestration can consume.
      Exit: A bounded fixture backfill publishes the expected quarters and reports unresolved units (R1); outage/overlap fixtures catch up across quarter boundaries without losing older pending sources (R2).
      ROUTING: writing-plans

- [x] Stage 5: Reconciliation and withdrawal approval
      Objective: Complete the shared workflows with correction handling and an auditable approval path.
      Spec: §§4.2, 4.4–4.7, 5–6.
      Gap closed: R5; R7; R10.
      Consumes: Stage 4 workflow/run interfaces and Stage 3 catalog, change-report and publication contracts.
      Produces: Reconciliation workflow, candidate/approval records, approval operation, recorded pointer rollback (§4.7; owner decision 2026-10-11) and change history usable by deployment and recovery tooling.
      Exit: All three workflows exercise the same acquisition/ETL implementation (R5); corrected fixtures produce expected deltas and unchanged-input outcomes (R7); approval, stale-replay and reintroduction fixtures yield the expected active membership (R10).
      ROUTING: writing-plans

- [x] Stage 6: Azure orchestration and deployment definitions
      Objective: Package the complete worker and connect it to the selected Azure services through versioned deployment definitions.
      Spec: §§4.1, 4.7–4.9, 5–6, 7 step 2, 8.
      Gap closed: R4; R11; Worker/pipeline delivery.
      Consumes: Stage 1 deployment/provider decisions and Stage 5 complete worker/result contracts.
      Produces: Pinned worker image, Azure resources/identities, ADF pipelines with start/poll/result handling, disabled triggers, telemetry/alerts and versioned configuration; the read-only operator `history` command (deferred item "Read-only `history` CLI"; owner-approved at resume, 2026-10-12).
      Exit: Infrastructure and orchestration checks exercise the selected service boundaries (R4); configuration/schedule checks enforce accepted defaults (R11); the built image runs every command and start/status/result failures cannot pass a pipeline (Worker/pipeline delivery).
      ROUTING: writing-plans
      > Stage 6: COMPLETE (2026-10-13) — implemented by plan 10 (specs/plans/completed/10-sec-filing-index-ingestion-stage-6-spec.md), after plan 9 (specs/plans/completed/9-sec-filing-index-ingestion-stage-6-spec.md). Its Handoff section names what Stages 7 and 8 consume.
      > Next: resume the roadmap.

- [ ] Stage 7: Deployment checkpoint and recovery evidence
      Objective: Validate the integrated system in isolation and establish measured release/recovery evidence before production operation.
      Spec: §§4.7–4.9, 5–6, 7 steps 3–5, 8, 10; Stage 6 spec §11 (`completed/sec-filing-index-ingestion-stage-6-spec.md`) (plan 10, Handoff; Resolved at resume, 2026-10-14).
      Gap closed: Error outcomes; Verification; Isolated integration; Live smoke; Replay/recovery rehearsal; Documentation/infrastructure.
      Consumes: The Stage 6 stack as built — compiled template, deployment inputs, pipeline contract, alerts and stopped triggers, with no release image (plan 10, Handoff; Resolved at resume, 2026-10-14) — and complete worker/workflow contracts; a stable offline suite, with the deferred "Load-flaky multi-process tests" item closed (owner-approved at resume, 2026-10-12).
      Produces: Acceptance reports, reviewed runtime configuration, release candidate whose release image is built by ACR quick task and pinned by digest (S7-05), exercised runbooks including a verified staleness-alert enable command, and retained smoke/recovery artifacts (plan 10, Handoff; Resolved at resume, 2026-10-14).
      Exit: Failure fixtures emit the expected named outcomes, and a direct run with a hostile pipeline parameter ends `execution_unknown` before any request (Error outcomes); CI and integration checks pass (§6 Verification); Azure identity/coordination/fault-injection reports pass, and `validate`, `what-if` and the live checks prove each Stage 6 assumption or correct it in `infra/azure/sec-edgar-ingest/` (Isolated integration); bounded quarterly/daily smoke reports record required measurements (Live smoke); offline replay and approval/rollback rehearsals pass (Replay/recovery rehearsal); versioned infrastructure, carrying a `summary_error` alert before the first deploy, and exercised operating/reader documentation are reviewable (Documentation/infrastructure). The three additions are plan 10, Handoff, "Deferred into Stage 7" (Resolved at resume, 2026-10-14).
      ROUTING: writing-plans

- [ ] Stage 8: Baseline and scheduled-operation acceptance
      Objective: Establish accepted production coverage and verify the enabled schedules through observed executions.
      Spec: §§4.2, 4.7–4.9, 7 steps 6–9 and Exit, 10.
      Gap closed: Baseline rollout; Daily activation; Reconciliation activation; Scheduled acceptance.
      Consumes: Stage 7 approved release candidate, recovery evidence and deployment checkpoint acceptance; Stage 6's stopped triggers, whose start times are deployment parameters, its disabled staleness alerts and Stage 7's verified enable command (plan 10, Handoff; Resolved at resume, 2026-10-14).
      Produces: Accepted baseline/catch-up/reconciliation reports, controlled records enabling each trigger with its staleness alert (plan 10, Handoff; Resolved at resume, 2026-10-14) and release evidence naming image/configuration versions and quarter generations.
      Exit: Coverage records account for every requested baseline unit or an explicitly approved incomplete range (Baseline rollout); accepted catch-up precedes enabling the daily trigger and its staleness alert (Daily activation); accepted manual reconciliation precedes enabling the weekly trigger and its staleness alert (Reconciliation activation); subsequent scheduled executions have matching durable reports and logs (Scheduled acceptance). The paired enablements are plan 10, Handoff (Resolved at resume, 2026-10-14).
      ROUTING: writing-plans

## Stage-spec stamp

Every stage spec's Rollout note carries the following line, with its stage number substituted;
`writing-plans` copies it verbatim into the stage plan header:

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage N — on plan completion, tick the
> stage and re-validate later stages against what shipped.

On completion, replace it with the authoritative stamp:

> Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path).
> Next: resume the roadmap.

Stage 1 is an investigation stage: its exit artifact is the accepted written finding rather than
software. Its completion must retain that finding's reference. A checked box alone is not proof
of stage completion; stage-spec Rollout stamps govern reconciliation.

## Completion

Obtain approval of this partition before Stage 1. Route that stage by its bare skill name in a
fresh session, then stop. Later transitions require the owner to request “resume the roadmap.”

After all stages are checked, re-run the gap rubric over the accumulated system, citing implementing
stage/plan evidence, recorded deviations and operational reports for every row. Code review or a
manual smoke test alone cannot discharge scheduled-operation acceptance (§7).

Unmet requirements either create a new stage or receive an explicit written deferral in
`specs/deferred_items.md`; they cannot disappear through retirement. Retire the roadmap and source
spec to `specs/completed/` only after the conformance audit accounts for every requirement. If the
owner parks the work earlier, preserve the remaining stages as self-contained deferred items and
mark the retired roadmap `PARKED (YYYY-MM-DD) — N of M stages complete`.
## Stage 1 completion and later-stage consistency

Stage 1 completed 2026-10-06 through [plan 1](plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md)
and its [authoritative Stage 1 spec stamp](completed/sec-filing-index-ingestion-stage-1-spec.md#9-rollout-note).
Lowell Mason accepted [finding F1](sec-filing-index-ingestion-stage-1-findings.md), revision date
2026-10-05, accepted 2026-10-05, exact SHA-256
`939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`, with the complete limitations.
The [accepted 1,584-record manifest](evidence/sec-filing-index-ingestion/stage-1/final-candidate/evidence-manifest.json)
has SHA-256 `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`;
the [owner receipt](evidence/sec-filing-index-ingestion/stage-1/final-candidate/owner-acceptance.json)
records the exact acceptance context. The gap-analysis heading/table above remains the historical baseline
from roadmap derivation, including its then-missing acceptance statements; the accepted finding and stamp
supply current Stage 1 evidence.

Stages 2–8 remain unticked and their definitions unchanged. Stage 2 workspace/CLI alignment (D10)
remains required. Selected source families, cross-quarter filing dates and nullable accession require later
golden parser verification; accepted historical daily listing gaps remain explicit recovery obligations.
Raw-byte retention/replay, shared request coordination, publication/recovery and hash-bound approval
safeguards remain consistent with the parent contract and the accepted finding. Stage 7 must produce
all [22 reserved integrated checks](evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md),
including effective permissions, start/correlation/results, connectivity, release/rollback availability,
DST, observability and actual worker memory/runtime; documentation selections and native compatibility
probes do not discharge them. Stage 8 production coverage and scheduled-operation acceptance remain required.
This consistency note begins no later-stage investigation, implementation or plan. Stop at this boundary;
the owner must separately request “resume the roadmap.”

## Stage 3 reconciliation and Stage 4 planning — 2026-10-07

Resume reconciled against merged `origin/main` / primary `main`
`fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`, using the authoritative
[completed Stage 3 stamp](completed/sec-filing-index-ingestion-stage-3-spec.md#9-rollout-note)
and [completed Plan 3](plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md).
Stages 1–3 are complete. Historical derivation and earlier consistency notes remain historical;
untracked Stage 3 planning originals are retained inputs, not completion authority.
The exact SEC-0141/0142/0143 quarantines are accepted documentary exceptions; strict whole-source
refusal, no accepted observations and no publication remain intact (§8 of the completed Stage 3 spec).

Every remaining stage was revalidated against the shipped package: Stage 4 still requires R1/R2
workflow composition, durable unresolved-unit coverage and outage/overlap proof; Stage 5 still
requires reconciliation and approval operations; Stage 6 still requires complete-worker Azure
orchestration; Stage 7 retains all 22 integrated checks reserved/not_run; Stage 8 still requires
accepted production coverage and observed schedules. The existing stage partition is unchanged.

The owner initiated resume and Stage 4 planning. Route only Stage 4 via `writing-plans`, under
[Stage 4 spec](sec-filing-index-ingestion-stage-4-spec.md) and
[Plan 4](plans/4-sec-filing-index-ingestion-stage-4-spec.md), both pending owner approval.
Stages 4–8 remain unticked. All live-access authorizations remain closed. The
[reconciliation receipt](evidence/sec-filing-index-ingestion/stage-4/planning-reconciliation.json)
records fresh preservation, additional retained drift, fast-forward and authority boundaries.
The original ignored roadmap bytes are retained in its cited preservation directory.
Stop for owner approval before Stage 4 implementation.

## Stage 4 completion and later-stage consistency

Stage 4: COMPLETE (2026-10-08) — implemented by plan 5 ([retired executed plan](plans/completed/5-sec-filing-index-ingestion-stage-4-spec.md)). The [hash-bound completion record](evidence/sec-filing-index-ingestion/stage-4/plan5-execution/completion/completion-record.md) supplements the unchanged approved shared Stage 4 spec. The owner accepted final actual offline coverage and the verified checkpoint/retained-evidence planning disposition. Original Plan 4 is superseded for execution.

Only Stage 4 is ticked by this completion. Stage 5 remains responsible for reconciliation and withdrawal approval; the shipped workflow/report contracts are its inputs. Stage 6 remains responsible for the complete worker image, Azure deployment/orchestration, configuration and disabled triggers. Stage 7 remains responsible for integrated validation, live smoke and recovery evidence; all 22 integrated checks remain reserved/not_run. Stage 8 remains responsible for accepted production coverage, activation and observed schedules. None of those exits is established by Stage 4 synthetic fixture proof. Their existing objectives, contracts and routing remain unchanged. Resume requires a separate owner request.

This execution roadmap was derived from the preserved historical primary/approval roadmap. Those original bytes remain unchanged. The execution branch/worktree is kept for a later deliberate integration decision.

## Stage 5 planning — 2026-10-11

The owner resumed the roadmap against `main` at `6ef957bb` (merged PR #4). Stages 1–4 carry authoritative stamps. Stages 6–8 were re-validated against the shipped package and are unchanged. For Stage 5 onward, the owner chose a lean process: TDD, per-task and whole-branch review, the full offline suite, and a wheel build with CLI smoke. Azure adapters stay in step with the local backend.

Only Stage 5 is routed, via `writing-plans`, under the [Stage 5 spec](completed/sec-filing-index-ingestion-stage-5-spec.md) and [Plan 6](plans/completed/6-sec-filing-index-ingestion-stage-5-spec.md), both on branch `stage-5-reconcile`. The owner's decisions are recorded in spec §9:

- Reverts to older bytes are detected and reported as `source_reverted`, not published.
- Stage 5 builds the explicit recorded rollback (§4.7), so its Produces line now names it. Stage 6 maps the rollback operator role; Stage 7's rollback rehearsal (§7 step 5) consumes it.
- Stale approval and stale rollback exit 11.
- The shared run-level reducer reports gate-only unresolved work as `awaiting_approval`, even beside completed sources (Stage 5 spec §3). This amends shipped Stage 4 behavior under one reading of Stage 4 spec §5; the hash-bound Stage 4 spec is not edited.
- The gated-then-reverted limitation (Stage 5 spec §4) is deferred, to be recorded in `specs/deferred_items.md` at stage exit.

Stages 5–8 remain unticked. All live-access authorizations remain closed. Resuming past Stage 5 requires a separate owner request.

## Stage 5 completion and later-stage consistency

Stage 5: COMPLETE (2026-10-11) — implemented by plan 6 ([retired executed plan](plans/completed/6-sec-filing-index-ingestion-stage-5-spec.md); [retired spec](completed/sec-filing-index-ingestion-stage-5-spec.md)). The lean process ran as chosen: red/green TDD per task, a task review each, a whole-branch Opus review, the full offline suite (654 tests OK) and a wheel build with `--help` smoke tests for `reconcile`, `approve`, `candidates` and `rollback`. The final review found no Critical issues; its fixes landed in the fix commit, and the remaining findings plus the owner-deferred gated-then-reverted limitation are in `specs/deferred_items.md`. The Codex second-opinion seat did not run (the CLI rejected its configured model for the ChatGPT account), so integration needs a Codex pass first. This is not a live-access authorization.

Stages 6–8 were re-validated against what shipped, and their objectives, contracts and routing are unchanged:

- **Stage 6** consumes the `reconcile` workflow command (a third command on the Stage 4 runner), the operator commands `approve`, `candidates` and `rollback`, exit code 10 for gated work, exit 11 for a stale approval or rollback, exit 2 for a refused one, and the `Approvals` table with the `approvals` blob container, which sit in the accepted table and container scope but must be provisioned by the deployment definitions. The built image must run every command. Pipelines must treat exit 10 as a distinct gated outcome and exit 11 as stale, never as success. Stage 6 must also map the approval and rollback operator roles to the read/write sets in Stage 5 spec §5, and decide how approval, rollback and re-activation actors are identified (deferred item).
- **Stage 7**'s rollback rehearsal (parent §7 step 5) consumes `rollback`. The operator procedure reads `quarter_history`, which is library-only until the deferred read-only history command exists. All 22 integrated checks remain reserved/not_run; Stage 5's offline proofs discharge none of them.
- **Stage 8**'s reconciliation activation (accepted manual reconciliation precedes weekly enablement) consumes `reconcile`. A closed-quarter withdrawal still needs an operator `approve` and is never a successful scheduled run.

Stages 6–8 remain unticked. All live-access authorizations remain closed. Resuming past Stage 5 requires a separate owner request.

## Stage 6 resume — 2026-10-12

The owner resumed the roadmap against `main` at `07067a0a` (merged PR #11). Stages 1–5 carry authoritative stamps. Stage 5's open condition, "integration needs a Codex pass first", is discharged: PR #5's test plan records a full-branch Codex review with no actionable findings.

Since Stage 5, plans 7 (gated-revert supersession, PR #10) and 8 (v1 workflow-selection reader, PR #11) shipped, plus `/deferred` quick fixes (PRs #6–#9). These are deferred-item plans, not roadmap stages, and tick nothing. None of plans 6–8 has a `## Handoff to later stages` section, so no entry is amended from a Handoff. What Stages 6–8 now see:

- `candidates` lists a derived `superseded` status, and `approve` refuses a superseded candidate as `approval_stale` (exit 11, already in the Stage 5 note's exit mapping).
- The shared CLI error handlers always emit their JSON result with the outcome-mapped exit code, never a traceback, whatever the exception text. Acquisition and supervisor failures with unsafe text are recorded as one-line gaps (PRs #6–#9).
- New workflow selections are `sec-workflow-selection-v2`; stored v1 selections stay readable.
- A gated member whose source reverted clears on the following run, which Stage 8's reconciliation activation inherits.

The owner approved two scope changes in one question, applied to the entries above: Stage 6 Produces gains the read-only `history` command, and Stage 7 Consumes gains the closed load-flaky test item. No stage is added, split, dropped or reordered, and routing is unchanged.

Stage 6 also accounts for the deferred items bound to it in `specs/deferred_items.md`: actor identification and re-activation attribution (its Done-when names Stage 6), operator commands creating a store at a mistyped path, and download evidence outside retained members (both "Revisit if Stage 6 changes…"). The derived `activated` field stays an ordinary deferred item.

Known planning input, not a change: F1 §2 D-08 records Bicep and local Docker/buildx as absent and requires separate owner authority for a build facility or installation. Re-observed 2026-10-12: `docker`, `podman` and `bicep` absent, `az` present. Stage 6's Exit ("the built image runs every command") needs that authority; S7-04/05 build, push and digest-pull proof remain Stage 7's.

Stages 6–8 remain unticked. All live-access authorizations remain closed. Only Stage 6 is routed, via `writing-plans`.

## Stage 7 resume — 2026-10-14

The owner resumed the roadmap against `main` at `c5c1e016` (merged PR #13). Stages 1–6 carry authoritative stamps; Stage 6's names plan 10, after plan 9. Plan 10's `## Handoff to later stages` already reflects the two commits after its completion record (`412aeba8`, the observation-deadline wait fix, and `2a2d9845`). Plan 9 has no Handoff section, so it amends nothing.

Amended from plan 10, Handoff, each point marked Resolved at resume, 2026-10-14:

- **Stage 7.** Spec gains Stage 6 spec §11. Consumes names the stack as built, with no release image. Produces gains the release image built by ACR quick task and pinned by digest (S7-05), which moves from Stage 6's Produces line, and a verified staleness-alert enable command. Exit gains the three items the Handoff defers into Stage 7: each live assumption proven or corrected, hostile direct-run parameters, and a `summary_error` alert before the first deploy.
- **Stage 8.** Consumes gains the stopped triggers, the disabled staleness alerts and Stage 7's enable command. Produces and Exit pair each trigger enablement with its staleness alert.

No stage is added, split, dropped or reordered, and routing is unchanged.

Stage 7 also accounts for deferred items bound to it in `specs/deferred_items.md` by their Done-when, as planning inputs rather than entry changes: from the plan 9 section, image smoke hardening ("at Stage 7's image work") and the Colima pre-build image check (at the next `colima start`); run-worker scenario coverage, whose `execution_reference` waits on observed execution-name syntax; and operations runbook polish. The runbook item dates the alert-enable command to Stage 8, while the Handoff has Stage 7 verify it; the entries above follow the Handoff.

**Stage 7's Consumes are not yet met.** The "Load-flaky multi-process tests" item is still open. The owner chose (2026-10-12) a separate `/deferred` plan to close it before Stage 7, and plan 9 recorded further failures in full runs that overlapped concurrent work. Stage 7 routes via `writing-plans` once that plan ticks the item; Stage 8 consumes Stage 7.

Stages 7–8 remain unticked. All live-access authorizations remain closed; Stage 7's deployment, live smoke and integrated checks need owner-granted access that this resume does not open.
