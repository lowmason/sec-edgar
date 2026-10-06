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

- [ ] Stage 1: Scope and feasibility findings
      Objective: Establish an accepted implementation boundary and resolve source, runtime and deployment prerequisites before building.
      Spec: §§2, 4.8–4.9, 7 step 1, 10; ADR Decision and Consequences.
      Gap closed: Readiness.
      Consumes: Source spec/ADR, repository inventory and owner-confirmed scope/package alignment.
      Produces: Accepted stage spec and written findings recording the supported range, handoff, deployment inputs, provider/version checks and resolution of blocking uncertainties.
      Exit: An owner-accepted readiness finding identifies a viable supported source/runtime combination and records the decisions needed to unblock subsequent stages.
      ROUTING: brainstorming

- [ ] Stage 2: Durable discovery and collection
      Objective: Deliver a runnable acquisition boundary that retains exact inputs and resumes incomplete source work.
      Spec: §§4.1–4.3, 4.5, 4.8–4.9, 5–6; ADR Decision.
      Gap closed: R8; Package boundary.
      Consumes: Stage 1 findings and accepted source/configuration boundaries.
      Produces: Aligned workspace and ingest CLI, validated acquisition configuration, discovery worksets, pinned raw snapshots and durable source/attempt state in the §4.5 contracts.
      Exit: Concurrent-collector and takeover fixtures show one coordinated request issuer (R8); workspace build and CLI checks succeed with the ADR-aligned package boundary (Package boundary).
      ROUTING: writing-plans

- [ ] Stage 3: Replayable ETL and safe publication
      Objective: Turn retained snapshots into readable quarter generations with deterministic replay and recoverable commits.
      Spec: §§4.4–4.6, 5–6.
      Gap closed: R3; R6; R9.
      Consumes: Stage 2 pinned snapshots, state interfaces and supported source fixtures.
      Produces: Versioned observation outputs, canonical catalog generation builder, change reports, publisher and pointer-resolving reader interface; §4.4 gates apply from first publication.
      Exit: Golden fixtures yield the expected normalized rows (R3); raw-only replay makes no SEC requests or duplicate filings (R6); crash and competing-publisher fixtures expose complete generations without lost updates (R9).
      ROUTING: writing-plans

- [ ] Stage 4: Backfill and daily catch-up workflows
      Objective: Compose acquisition and publication into manually runnable historical and daily workflows.
      Spec: §§4.1–4.2, 4.5, 4.7–4.8, 5–6.
      Gap closed: R1; R2.
      Consumes: Stage 3 shared acquisition/ETL interfaces and Stage 1 range/handoff decisions.
      Produces: Parameterized baseline and daily workflows, durable discovery boundaries and run reports that later orchestration can consume.
      Exit: A bounded fixture backfill publishes the expected quarters and reports unresolved units (R1); outage/overlap fixtures catch up across quarter boundaries without losing older pending sources (R2).
      ROUTING: writing-plans

- [ ] Stage 5: Reconciliation and withdrawal approval
      Objective: Complete the shared workflows with correction handling and an auditable approval path.
      Spec: §§4.2, 4.4–4.7, 5–6.
      Gap closed: R5; R7; R10.
      Consumes: Stage 4 workflow/run interfaces and Stage 3 catalog, change-report and publication contracts.
      Produces: Reconciliation workflow, candidate/approval records, approval operation and change history usable by deployment and recovery tooling.
      Exit: All three workflows exercise the same acquisition/ETL implementation (R5); corrected fixtures produce expected deltas and unchanged-input outcomes (R7); approval, stale-replay and reintroduction fixtures yield the expected active membership (R10).
      ROUTING: writing-plans

- [ ] Stage 6: Azure orchestration and deployment definitions
      Objective: Package the complete worker and connect it to the selected Azure services through versioned deployment definitions.
      Spec: §§4.1, 4.7–4.9, 5–6, 7 step 2, 8.
      Gap closed: R4; R11; Worker/pipeline delivery.
      Consumes: Stage 1 deployment/provider decisions and Stage 5 complete worker/result contracts.
      Produces: Pinned worker image, Azure resources/identities, ADF pipelines with start/poll/result handling, disabled triggers, telemetry/alerts and versioned configuration.
      Exit: Infrastructure and orchestration checks exercise the selected service boundaries (R4); configuration/schedule checks enforce accepted defaults (R11); the built image runs every command and start/status/result failures cannot pass a pipeline (Worker/pipeline delivery).
      ROUTING: writing-plans

- [ ] Stage 7: Deployment checkpoint and recovery evidence
      Objective: Validate the integrated system in isolation and establish measured release/recovery evidence before production operation.
      Spec: §§4.7–4.9, 5–6, 7 steps 3–5, 8, 10.
      Gap closed: Error outcomes; Verification; Isolated integration; Live smoke; Replay/recovery rehearsal; Documentation/infrastructure.
      Consumes: Stage 6 deployable stack, disabled triggers and complete worker/workflow contracts.
      Produces: Acceptance reports, reviewed runtime configuration, release candidate, exercised runbooks and retained smoke/recovery artifacts.
      Exit: Failure fixtures emit the expected named outcomes (Error outcomes); CI and integration checks pass (§6 Verification); Azure identity/coordination/fault-injection reports pass (Isolated integration); bounded quarterly/daily smoke reports record required measurements (Live smoke); offline replay and approval/rollback rehearsals pass (Replay/recovery rehearsal); versioned infrastructure and exercised operating/reader documentation are reviewable (Documentation/infrastructure).
      ROUTING: writing-plans

- [ ] Stage 8: Baseline and scheduled-operation acceptance
      Objective: Establish accepted production coverage and verify the enabled schedules through observed executions.
      Spec: §§4.2, 4.7–4.9, 7 steps 6–9 and Exit, 10.
      Gap closed: Baseline rollout; Daily activation; Reconciliation activation; Scheduled acceptance.
      Consumes: Stage 7 approved release candidate, recovery evidence and deployment checkpoint acceptance.
      Produces: Accepted baseline/catch-up/reconciliation reports, controlled trigger-enablement records and release evidence naming image/configuration versions and quarter generations.
      Exit: Coverage records account for every requested baseline unit or an explicitly approved incomplete range (Baseline rollout); accepted catch-up precedes daily enablement (Daily activation); accepted manual reconciliation precedes weekly enablement (Reconciliation activation); subsequent scheduled executions have matching durable reports and logs (Scheduled acceptance).
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
