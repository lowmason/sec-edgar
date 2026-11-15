> For agentic workers: REQUIRED SKILL: derive-roadmap — resume via its
> reconcile step; route each unticked stage per its ROUTING line; never plan
> this document wholesale.

## Gap analysis

**Project:** `/Users/lowell/Projects/sec-edgar`.
**Rewritten:** 2026-10-18, replacing the copied Azure roadmap in place.
**Source:** [Local filing-index spec](sec-filing-index-ingestion-spec.md). Requirement and gate IDs
below refer to its §§3 and 7. **Status:** local stage partition proposed for review; no remaining
stage is started or approved for execution by this rewrite. The owner approved the partition at
resume, 2026-10-21, with the Stage 2 `Consumes` amendment below. Approval of the partition does not
authorize live execution of any stage. The owner requested inclusion of a
future local scheduling phase; its design remains open. **Resume, 2026-10-22:** inserted Stage 1a
(the D5 release) was approved by the owner with defaults (i)–(iii) under Open questions. **Resume,
2026-10-27:** inserted Stage 1b (per-member cost, plan 4 D2) was approved by the owner as proposed
under Open questions. **Resume, 2026-10-29:** inserted Stage 1c (the member-completion conflict
fix, plan 2 D12) was approved by the owner with defaults (vii)–(ix) under Open questions. **Resume,
2026-10-31:** inserted Stages 2a (the duplicate-key parser/schema design) and 2b (baseline coverage on its
release) were approved by the owner with defaults (x)–(xii) under Open questions. **Resume, 2026-11-13:**
inserted Stage 2a1 (the pre-dispatch cost and its release) was approved by the owner with defaults (xiii)–(xvi)
under Open questions.

The native port is complete, not a scaffold. Its [retired plan](plans/completed/1-sec-edgar-local-spec.md)
and [final completion review](evidence/local-port/completion-review.md) control delivery status.
The checked local Stage 1 below is a retrospective mapping to that completed plan; it does not
import parent-project stage numbers, replay their history, or create a new completion claim.
The current config now selects the 2a release `e49d3ba8…`, at commit `4d1f806` (§4.8 of the spec;
plan 7, Handoff, Stage 2b bullet; Resolved at resume, 2026-11-02), after the 1c release `c4de77b8…`
(plan 6, Handoff, Stage 2 bullet; Resolved at resume, 2026-10-30), the 1b release `9fa189a0…`
(plan 5, Handoff; Resolved at resume, 2026-10-28) and the D5 release (plan 4, Handoff; Resolved at
resume, 2026-10-27); acceptance-time old-default statements remain historical. The completed port records
nothing deferred; plan 4's deferred items are in `specs/deferred_items.md` (plan 4, Handoff; Resolved
at resume, 2026-10-27).

Search boundary: this checkout's runtime/tests, current config, runbooks, retired local design/plan,
and retained port evidence. Live stores were not opened to measure new coverage, and no acquisition,
acceptance, or scheduler was run for this rewrite. A `missing` operational verdict means no accepted
report establishing that gate was found here, not that the underlying command is absent.

| Req | Verdict | Evidence | Note |
|---|---|---|---|
| R1 | implemented-as-specified | [Runner](../packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py), [discovery tests](../packages/sec-edgar-ingest/tests/test_discovery.py) | Inclusive quarterly selection and retained gaps; G2 is separate. |
| R2 | implemented-as-specified | [Discovery](../packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py), [workflow acceptance tests](../packages/sec-edgar-ingest/tests/test_workflow_acceptance.py) | Outage/overlap/pending handling exists; G3 is separate. |
| R3 | implemented-as-specified | [Parser](../packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/parser.py), [local ETL tests](../packages/sec-edgar-ingest/tests/test_local_etl_contracts.py) | Strict ten-field rows and whole-source refusal. |
| R4 | implemented-as-specified | [Completed local design](completed/sec-edgar-local-spec.md#4-components-and-data-flow), [native preflight tests](../packages/sec-edgar-ingest/tests/test_runtime_preflight.py) | Installed native execution and local SQLite/objects replace cloud services. |
| R5 | implemented-as-specified | [Workflow processing](../packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/processing.py), [checked child tests](../packages/sec-edgar-ingest/tests/test_workflow_checked.py) | Shared checked acquisition/transform/publish sequence. |
| R6 | implemented-as-specified | [Runtime](../packages/sec-edgar-ingest/src/sec_edgar_ingest/runtime.py), [native dispatch tests](../packages/sec-edgar-ingest/tests/test_native_dispatch.py), [completion review](evidence/local-port/completion-review.md) | Exact replay, original producers, two-release continuation/repair verified. |
| R7 | implemented-as-specified | [Reconciliation tests](../packages/sec-edgar-ingest/tests/test_reconcile_workflow.py), [catalog](../packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/catalog.py) | Corrections/reverts supported; G4 is separate. |
| R8 | implemented-as-specified | [Coordinator](../packages/sec-edgar-ingest/src/sec_edgar_ingest/coordination.py), [coordination tests](../packages/sec-edgar-ingest/tests/test_coordination.py), [live config](../conf/sec-edgar.json) | Local pacing/fencing/drain; external sole issuer remains an owner operating fact. |
| R9 | implemented-as-specified | [Publisher](../packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py), [reader](../packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py), [workflow completion tests](../packages/sec-edgar-ingest/tests/test_workflow_completion.py) | Per-quarter CAS and validated captures; no global historical-completeness claim. |
| R10 | implemented-as-specified | [Operator commands](../packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py), [reconciliation acceptance tests](../packages/sec-edgar-ingest/tests/test_reconcile_acceptance.py) | Exact approval, supersession/reverts, and recorded rollback. |
| R11 | implemented-as-specified | [Config tests](../packages/sec-edgar-ingest/tests/test_local_config.py), [launcher tests](../packages/sec-edgar-ingest/tests/test_local_launcher.py), [live config](../conf/sec-edgar.json) | Bound paths/policies and archived native invocation evidence. |
| R12 | implemented-as-specified | [Final completion review](evidence/local-port/completion-review.md), [recovery runbook](../docs/runbooks/local-recovery.md) | Renewed offline gate and separate reviewed L12 supplement; originals remain incomplete/exit 12. |
| R13 | missing | [Completed design scope](completed/sec-edgar-local-spec.md#1-outcome-and-boundaries), [launcher](../scripts/sec-edgar); no scheduler definitions found in `scripts/` or config | Future local scheduling was outside the port; user now requests a future phase. |
| G1 | implemented-as-specified | [Completed local plan](plans/completed/1-sec-edgar-local-spec.md), [completion review](evidence/local-port/completion-review.md), [current config](../conf/sec-edgar.json) | Reviewed release selected; offline preflight passed. No broad coverage inferred. |
| G2 | missing | [Bounded acceptance](evidence/local-port/sec-acceptance.md); no broad accepted baseline report found | Quarterly 2024Q1 quarantine and 73 pending discoveries remain explicit acceptance limits. |
| G3 | missing | [Bounded acceptance](evidence/local-port/sec-acceptance.md); no full handoff-to-current catch-up acceptance found | Two selected daily bodies do not establish complete daily catch-up. |
| G4 | missing | [Offline renewal](evidence/local-port/offline-renewal-task15.md); no broad operational reconciliation acceptance found | Fixture/recovery tests establish behavior, not operational range acceptance. |
| G5 | missing | [Spec §4.10](sec-filing-index-ingestion-spec.md#410-future-local-scheduling); no local scheduler installation or observed schedule evidence found | Neither parent Azure schedules nor a manual run establish local scheduled operation. |

The Azure platform/schedule/identity/deployment requirements were deliberately replaced or excluded
by local spec §§2, 4.1, 4.9–4.10, and 9. They are owned by the original `sec-edgar` project; they
are not missing local implementation tasks. No parent ADR, absent stage spec, cloud API check,
container release, or source-project PR is needed to resume this roadmap.

Resume reconcile, 2026-10-22: no stage carries a new COMPLETE stamp. [Plan 2](plans/2-sec-filing-index-ingestion-spec.md)
is blocked at its Task 4 (Status line, Feasibility blocker); its Handoff (`:1668–1690`) is the carrier for
the amendments below. Engine source under `packages/sec-edgar-ingest/src` is unchanged since the
`fc68adef…` build revision `3ca50c7` (its manifest `git_revision`; empty `git diff 3ca50c7 HEAD`): `runner.run_workflow` still defers only at `now >= deadline` (plan 2 F8). The rubric
verdicts above stand; this resume does not re-run gap analysis.

Resume reconcile, 2026-10-27: Stage 1a carries a new COMPLETE stamp (plan 4). Its Handoff
(`specs/plans/completed/4-sec-filing-index-bounded-drain.md`, `## Handoff to later stages`) amends the
gap-analysis selection line above and Stages 2, 3 and 5 below; Stage 4 is unchanged ("Nothing
differs"). Stage 1a's `Produces` held as built, except that the live reserve is provisional (plan 4
D2, D4). Plan 3 DF6 is now open, but that merge belongs to the platform roadmap. The rubric verdicts
above stand; this resume does not re-run gap analysis.

Resume reconcile, 2026-10-28: Stage 1b carries a new COMPLETE stamp (plan 5). Its Handoff
(`specs/plans/completed/5-sec-filing-index-per-member-cost.md`, `## Handoff to later stages`) amends the
selection line above and Stages 2–5 below. Stage 1b's `Produces` held as built. The one difference, no
named measured limit, is named by the Handoff itself: the fit gate passed, and the 1800 s reserve is now
measured (plan 5 D10). No stage is added, split, dropped or reordered, so no change set was put to the
owner. Deferred items that no Handoff bullet assigns to a stage stay in `specs/deferred_items.md`. The
Handoff's platform bullet (plan 3 DF6) belongs to the platform roadmap. The rubric verdicts above stand;
this resume does not re-run gap analysis.

Resume reconcile, 2026-10-29: no stage carries a new COMPLETE stamp. [Plan 2](plans/2-sec-filing-index-ingestion-spec.md)
halted at Task 5: invocation 1 ended with launcher exit 9 and `state_conflict` at
`workflows/processing.py:96`, and the owner routed it to an engine diagnosis and fix (plan 2 D12). Its
Handoff bullet "Task 5 halt (2026-10-29)" is the carrier for the Stage 2 amendment below. Engine source
under `packages/sec-edgar-ingest/src` is unchanged since the 1b build revision `50423a4` (its manifest
`git_revision`; empty `git diff 50423a4 HEAD`). The ten raw logs and reports that the invocation 1 record
cites match their recorded SHA-256 values. The halt is not diagnosed, so the rubric verdicts above stand.
This resume does not re-run gap analysis.

Resume reconcile, 2026-10-30: Stage 1c carries a new COMPLETE stamp (plan 6). Its Handoff
(`specs/plans/completed/6-sec-filing-index-member-completion.md`, `## Handoff to later stages`) amends the
selection line above, Stage 1c's Exit, and Stages 2–5 below. Stage 1c's `Produces` held as built. Engine
source under `packages/sec-edgar-ingest/src` is unchanged since the 1c build revision `3af121a` (its
manifest `git_revision`; empty `git diff 3af121a HEAD`). No stage is added, split, dropped or reordered,
so no change set was put to the owner. The Handoff's platform bullet (1c spec S2: the platform member may
now merge under plan 3's Merge gate) belongs to the platform roadmap. The rubric verdicts above stand;
this resume does not re-run gap analysis.

Resume reconcile, 2026-10-31: Stage 2 carries a new COMPLETE stamp (plan 2). Its Handoff
(`specs/plans/completed/2-sec-filing-index-ingestion-spec.md`, `## Handoff to later stages`) amends Stages
3–5 below. Stage 2 met its Exit as owner-approved incomplete: all 28 quarterly units are quarantined with an
owner disposition, and no quarterly baseline exists ([coverage finding](evidence/baseline-campaign/coverage-finding.md)
§§1, 4.1, 6). The G2 row above stays the entry-time verdict. The completion review re-runs it and keeps approved
incomplete apart from complete coverage (spec §7). Engine source under `packages/sec-edgar-ingest/src` is
unchanged since the 1c build revision `3af121a` (empty `git diff 3af121a HEAD`). The Handoff defers the
parser/schema design item into both Stage 3 and Stage 4. The change set under Open questions settles its owner.
The Handoff has no platform bullet. This resume does not re-run gap analysis.

Resume reconcile, 2026-11-02: Stage 2a carries a new COMPLETE stamp (plan 7). Its Handoff
(`specs/plans/completed/7-sec-filing-index-duplicate-key.md`, `## Handoff to later stages`) amends the
selection line above and Stages 2b–5 below. Stage 2a's `Produces` held as built. Its scratch run transformed
all 35 duplicate-key sources, and `data/` stayed unchanged (`specs/evidence/stage2a/release.md`). Engine source
under `packages/sec-edgar-ingest/src` is unchanged since the 2a build revision `3286385` (its manifest
`git_revision`; empty `git diff 3286385 HEAD`). No stage is added, split, dropped or reordered, so no change set
was put to the owner. Item 1 of `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec —
2026-10-31`, stays open for Stage 2b. The Handoff has no platform bullet, and the release's locked inputs carry
no platform member (2a spec D12). The rubric verdicts above stand; this resume does not re-run gap analysis.

Resume reconcile, 2026-11-06: no stage carries a new COMPLETE stamp. [Plan 8](plans/8-sec-filing-index-ingestion-spec.md)
halted at Task 5 after two live invocations (stop rule 10). No member was dispatched and no generation was published,
because the work before the first dispatch took longer than the 1,800 s dispatch cutoff (1,809 s, then 2,715 s). Its
Handoff bullet "Task 5 halt (2026-11-06)" is the carrier for the Stage 2b amendment below, and its "Stages 3, 4 and 5"
bullet for their amendments. Engine source under `packages/sec-edgar-ingest/src` is unchanged since the 2a build
revision `3286385` (empty `git diff 3286385 HEAD`). The owner chose to stop plan 8 and to plan anew, and paused that
choice. No stage is added, split, dropped or reordered, and the routing question stays open under Open questions. The
Handoff has no platform bullet. The rubric verdicts above stand; this resume does not re-run gap analysis.

Resume reconcile, 2026-11-13: no stage carries a new COMPLETE stamp, and nothing was committed after the 2026-11-06
resume (`2047a3a`). Engine source under `packages/sec-edgar-ingest/src` is unchanged since the 2a build revision
`3286385` (empty `git diff 3286385 HEAD`). No Handoff is newly cited, so no entry is amended from one. No unticked
stage had all its `Consumes` met: Stage 2b needs a release on which a member starts before the dispatch cutoff (plan
8, Handoff, bullet "Task 5 halt (2026-11-06)"), and Stages 3–5 need the Stage 2b finding. The owner unpaused the
routing question and approved the change set under Open questions. It inserts Stage 2a1 and amends Stages 2b–5. The
rubric verdicts above stand. This resume does not re-run gap analysis.

## Open questions

One change set was put to the owner as a single approve-or-amend at the 2026-10-22 resume:

Insert Stage 1a (the D5 release) ahead of Stage 2, per plan 2 D5 and Handoff `:1673`, and keep every
existing stage number, because plan 2's header and Handoff and the platform roadmap cite them. Proposed
defaults inside that change: (i) Stage 1a carries `Gap closed: none directly`; it removes the F11 blocker
on G2 and G3, and its stage spec proposes any spec amendment it needs (for example to §4.7). (ii) No
separate investigation stage: the unexplained publish-time spread and the unmeasured closed-quarter
publish (plan 2 F11) change only Stage 1a's own design, so its design work measures them offline.
(iii) Stage 1a ends with the reviewed live-config `release_manifest` selection and offline preflight, as
Stage 1 did for `fc68adef…` (§4.8), so the plan 2 revision consumes a fixed effective-config hash. The
amendments to Stages 2–5 cite plan 2 D5 rather than Stage 1a, so they stand however this is answered.

*Owner's answer (2026-10-22):* approved as proposed. Owner's words: "Approve the Stage 1a
insertion with defaults (i)–(iii) as written in the roadmap's Open questions." Approval authorizes no
SEC request or live run.

One change set was put to the owner as a single approve-or-amend at the 2026-10-27 resume:

Insert Stage 1b (per-member cost) ahead of Stage 2, per plan 4 D2 and Handoff, and keep every existing
stage number. Proposed defaults inside that change: (iv) one stage, not an investigation stage plus a
build stage: diagnosing the engine gap and measuring the unmeasured marks change only Stage 1b's own
design, as default (ii) settled for Stage 1a. (v) Stage 1b takes the deferred items "Per-member cost",
"Unmeasured drain costs" and "Provisional live reserve", and the "B4 single-candidate limit" as a
revisit trigger; the test-hygiene and order-aware-proof items stay deferred. (vi) Stage 2 consumes
Stage 1b's release in place of the D5 release, and the plan 2 revision is written against it.

*Owner's answer (2026-10-27):* approved as proposed. Owner's words: "Approve as proposed
(Recommended)". Approval authorizes no SEC request or live run.

One change set was put to the owner as a single approve-or-amend at the 2026-10-29 resume:

Insert Stage 1c (the member-completion conflict fix) ahead of the rest of Stage 2, per plan 2 D12 and
Handoff, bullet "Task 5 halt (2026-10-29)", and keep every existing stage number. Proposed defaults
inside that change: (vii) one stage, not an investigation stage plus a build stage: the diagnosis changes
only Stage 1c's own design, as defaults (ii) and (iv) settled for Stages 1a and 1b. (viii) Stage 1c designs
and proves offline the recovery path for the nine pointers that moved without member completion. The
recovery runs on the live store only in the plan 2 revision, under its own owner gate. (ix) Stages 3–5
consume Stage 1c's release wherever they now name the 1b release, because their members run through the
same checked member boundary (R5) that failed in invocation 1. No Handoff bullet names those
stages, so this is part of the change set, not an amendment. The Stage 2 amendment cites plan 2 D12
rather than Stage 1c, so it stands however this is answered.

*Owner's answer (2026-10-29):* approved as proposed. Owner's words: "Approve as proposed
(Recommended)". Approval authorizes no SEC request or live run.

One change set was put to the owner as a single approve-or-amend at the 2026-10-31 resume:

Insert Stage 2a (the duplicate-key parser/schema design and its release) and Stage 2b (baseline coverage on
that release) ahead of Stage 3, per plan 2, Handoff, and keep every existing stage number. The Handoff defers
the parser/schema design item into both Stage 3 and Stage 4. Two stages cannot own one item, and Stage 4 has
no quarterly authority to reconcile against until a fix ships. Proposed defaults inside that change: (x) Stage
2a is one stage, offline only, as defaults (ii), (iv) and (vii) settled for Stages 1a–1c. It takes item 1 of
`specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, from Stages 3 and 4.
Items 2–4 stay where the Handoff put them. (xi) Stage 2b covers or re-quarantines the 28 quarterly units and
the 7 daily duplicate-key sources and ends with a revised G2 finding. Stage 2's accepted finding stays as
history. The quarterly ZIPs are retained, so Stage 2b's plan decides whether any SEC request is needed. (xii)
Stages 3–5 consume the Stage 2a release and the Stage 2b finding wherever they name the 1c release or Stage 2's
finding. This order diverges from the Handoff's placement of item 1: the seven quarantined daily sources
re-run on every invocation (plan 2, Handoff, Stage 3 bullet, trap (c)), so an accepted Stage 3 report would
describe a store that Stages 2a and 2b then change. The Stage 3–5 amendments cite plan 2, Handoff, so they
stand however this is answered.

*Owner's answer (2026-10-31):* approved as proposed. Owner's words: "Approve as proposed
(Recommended)". Approval authorizes no SEC request or live run.

At the 2026-11-06 resume, after plan 8 halted, the owner chose "Stop, new plan" and then paused it. Owner's words:
"Stop, new plan. But not now. Let's pause. Just update the roadmap." That resume proposed no stage and no routing.

One change set was put to the owner as a single approve-or-amend at the 2026-11-13 resume:

Insert Stage 2a1 (the pre-dispatch cost and its release) ahead of Stage 2b, per plan 8, Handoff, bullet "Task 5 halt
(2026-11-06)", and keep every existing stage number, because plan 8's header and the deferred-item notes cite Stage
2b. Two `Consumes` are unmet. Stage 2b needs a release on which a member starts before the dispatch cutoff, which
blocks Stage 2b. Stage 2a1 produces it. Stages 3–5 need the Stage 2b finding, which blocks Stages 3, 4 and 5. Stage
2b produces it after Stage 2a1. Proposed defaults inside that change: (xiii) one stage, not an investigation stage
plus a build stage: profiling the cost changes only Stage 2a1's own design, as defaults (ii), (iv), (vii) and (x)
settled. Its objective is an outcome. At the live store's registered-member count, the first member starts before
the dispatch cutoff, and the longest Stage 2b member fits one invocation, or the owner approves a named, measured
limit. Discovery alone took 862 s in invocation 2, so the stage spec decides how the 2026-07-01 member (3,239.6 s
offline) fits. (xiv) The stage spec settles whether this release's locked inputs carry the platform member
(platform roadmap D1, plan 3 DF6), as Stages 1b, 1c and 2a did. The timing of the platform merge is decided there.
(xv) Stage 2b gets a new plan, written against Stage 2a1's release ("Stop, new plan"). Plan 8 stays as halted
evidence, and the new plan carries its Handoff forward. Plan 8's live approval and D6 do not carry over. (xvi)
Stages 3–5 consume Stage 2a1's release wherever they name the 2a release, because every workflow command probably
runs the same work before dispatch (plan 8, Handoff, "Stages 3, 4 and 5" bullet). Deferred items stay where their
Handoffs put them. The alternative was a revision inside Stage 2b: one plan with an engine change, a release build
and the campaign, against the pattern of Stages 1a, 1b, 1c and 2a.

*Owner's answer (2026-11-13):* approved as proposed. Owner's words: "Approve as proposed
(Recommended)". Approval authorizes no SEC request or live run.

## Stages

Order follows dependency and evidence needs: accept operational baseline coverage before daily
catch-up and initial reconciliation, then design/enable unattended operation. This retains the
parent rollout's baseline-before-activation intent while replacing its completed implementation
and cloud deployment stages. Scheduling is included by the owner's rewrite instruction; this
partition and each stage's execution still need their normal review. It contains no implementation
task list and does not reopen the completed 16-task native plan. Proposed Stage 1a follows the same
dependency rule: Stages 2, 3 and 5 each need an invocation that ends with a durable result inside its
deadline (plan 2 F8, F11), so the release that provides it comes first. Stage 1b follows the same
rule: on the D5 release no reserve lets a full-size quarterly member fit one invocation (plan 4 D2),
so the release that cuts per-member cost comes before Stage 2. Stage 1c follows the same
rule: on the 1b release the pilot's first member failed the member-completion check after its publish
moved nine pointers, and no further invocation runs until the fix (plan 2 D12), so the release that
fixes it comes before the rest of Stage 2. Stages 2a and 2b follow the same rule: Stage 2 left no
quarterly baseline, Stage 4 has nothing to reconcile against until the duplicate-key design ships, and
Stage 3 would otherwise accept a store that they then change (plan 2, Handoff), so both come before
Stage 3. This diverges from the Handoff's own placement of that design item. Stage 2a1 follows the same rule: on
the 2a release no invocation started a member before the dispatch cutoff at 127 or more registered members (plan 8,
Handoff), so the release that fixes it comes before Stage 2b's new plan. The spec ranks no stages, so
this order diverges from no spec ranking.

`Consumes` name the inputs needed to plan a stage. Each operational stage's plan must establish
its finite source scope, runtime/request/byte budget, evidence locations, and approval boundary.
Review of those campaign limits and confirmation of the sole-issuer condition are prerequisites
to live execution, not prerequisites to writing the plan that defines them.

- [x] Stage 1: Native local delivery and bounded acceptance
      Objective: Establish the completed native implementation and its reviewed release as the input to operational rollout.
      Spec: §§2.1, 3 R1–R12, 4.1–4.9, 5–6, 7 G1.
      Gap closed: R1–R12 implementation; G1.
      Consumes: The pinned parent import and approved local port design recorded by local plan 1.
      Produces: Native manual workflows/operators, versioned persistence/provenance, renewed offline proofs, and the separate reviewed bounded L12 result.
      Exit: Final local completion review approves the implemented contracts and both acceptance gates, retaining original incomplete run/verification and a separate supplemental pass.
      ROUTING: writing-plans

  > Stage 1: COMPLETE (2026-10-18) — implemented by plan 1 ([completed native local plan](plans/completed/1-sec-edgar-local-spec.md)). This stamp maps the existing completion record; no new stage execution occurred.
  > Next: resume the roadmap.

- [x] Stage 1a: Deadline-safe drain engine change and the D5 release (approved at resume, 2026-10-22)
      Objective: Ship a reviewed native release on which an invocation carrying the pending-source backlog ends with a durable workflow result inside its deadline.
      Spec: §3 R2, R5–R6, R12; §§4.2, 4.7–4.9, 5–6, 9; plan 2 D5, F8, F10, F11.
      Gap closed: None directly; removes the plan 2 F11 blocker that keeps G2 and G3 open.
      Consumes: Stage 1 release `fc68adef…` and its offline gate; plan 2 D5 and Handoff (`:1673–1676`) for the fix areas and measured inputs; the gate condition in `specs/evidence/baseline-campaign/campaign.md`, Release gate; [release upgrades](../docs/runbooks/release-upgrades.md). Platform roadmap D1 ("D5 first, platform after"): the release carries no platform item. Plan 3 DF6: the platform workspace member stays off `main` until this release is built.
      Produces: A stage spec and plan; the engine change with offline tests; the D5 release (its content-addressed release ID, setup and preflight evidence, and review record); the reviewed live-config selection with its effective-config SHA-256; and a plan Handoff that names every value the plan 2 revision must change, including any change to the §4.8 coordination values.
      Exit: Offline evidence on the D5 release shows the release side of the `campaign.md` Release gate: undispatched members defer before the deadline, or the pilot's drain fits one invocation with margin (the stage spec fixes what evidence counts for each; plan 2 F11); the offline checker and offline preflight pass on it, with `fc68adef…` and older releases retained (§4.9); its locked inputs carry no platform member; no SEC request was sent.
      ROUTING: brainstorming

  > Stage 1a: COMPLETE (2026-10-27) — implemented by plan 4 ([completed bounded-drain plan](plans/completed/4-sec-filing-index-bounded-drain.md)). Its Handoff section names what Stages 2–5 consume.
  > Next: resume the roadmap.

- [x] Stage 1b: Per-member cost and its release (approved at resume, 2026-10-27)
      Objective: Ship a reviewed native release on which every member a Stage 2 or Stage 3 invocation dispatches finishes inside one invocation, under a reserve set from measured costs.
      Spec: §3 R5, R9, R12; §§4.2, 4.6–4.9, 5–6, 9; plan 4 D2, D4.
      Gap closed: None directly; removes the plan 4 D2 per-member-cost limit that keeps G2 and G3 open.
      Consumes: The D5 release and its evidence (`specs/evidence/d5-release/`), with `measurement.md` and `finish-measurement.json` as the measured inputs and their stated limits; plan 4 D2, D4 and Handoff, "Next roadmap resume" bullet; `specs/deferred_items.md`, section `4-sec-filing-index-bounded-drain — 2026-10-27`, the four items named by default (v). Platform roadmap D1 and plan 3 DF6: the stage spec settles whether this release's locked inputs carry the platform member.
      Produces: A stage spec and plan; a diagnosis of the engine gap; measurements of the marks plan 4 never reached, or a spec record that they are not needed; the cost change with offline tests; a reviewed release with setup, preflight and review evidence; the reviewed live-config selection with a reserve set from measured costs and its effective-config SHA-256; and a plan Handoff that names every value the plan 2 revision must change.
      Exit: Offline evidence on the new release shows full-size quarterly members and open-quarter daily members at the high marks finishing within the launcher default minus the reserve, or the owner approves a named, measured limit; the offline checker and preflight pass on it, with the D5 release and older releases retained (§4.9); the provenance and reader contracts hold or an explicit versioned transition is reviewed (§9); no SEC request was sent.
      ROUTING: brainstorming

  > Stage 1b: COMPLETE (2026-10-28) — implemented by plan 5 (specs/plans/completed/5-sec-filing-index-per-member-cost.md). Its Handoff section names what Stages 2–5 consume.
  > Next: resume the roadmap.

- [x] Stage 1c: Member-completion conflict fix and its release (approved at resume, 2026-10-29)
      Objective: Ship a reviewed native release on which a member whose publish completes also passes the member-completion check, and which repairs the store state that invocation 1 left.
      Spec: §3 R5, R6, R9, R12; §§4.6–4.9, 5–6, 9; plan 2 D12, F17.
      Gap closed: None directly; removes the plan 2 D12 blocker that keeps G2 and G3 open.
      Consumes: The 1b release `9fa189a0…` and its evidence (`specs/evidence/stage1b/`). Plan 2 D12, F17 and Handoff, bullet "Task 5 halt (2026-10-29)": the failure, the observations that are not a cause, and the store state the fix must handle. The invocation 1 record `specs/evidence/baseline-campaign/invocations/1-8305a3d9-54a1-46ae-863c-af8227118417.json`, `invocations.md`, and the raw logs it cites by SHA-256. [Local recovery](../docs/runbooks/local-recovery.md), row "Crash after pointer update". Platform roadmap D1 and plan 3 DF6: the stage spec settles whether this release's locked inputs carry the platform member.
      Produces: A stage spec and plan; a written diagnosis of the `processing.py:96` conflict; the fix with offline tests; a recovery path for the nine filing-quarter pointers that moved without member completion, exercised offline; a reviewed release with setup, preflight and review evidence; the reviewed live-config selection with its effective-config SHA-256; and a plan Handoff that names every value the plan 2 revision must change, including how Task 5 treats the repair obligation and ledger row k = 1.
      Exit: An offline reproduction of the diagnosed cause fails on the 1b release and passes on the new release (1c spec §5 item 1 and §6 Exit; the diagnosis ruled out the F17 shape, and the F17 fixture stays deferred; plan 6, Handoff, "Roadmap resume" bullet; spec S1; Resolved at resume, 2026-10-30); offline, a re-run through the checked boundary completes a member whose pointers moved without member completion and moves no pointer twice (§4.7); the offline checker and preflight pass on the new release, with the 1b release and older releases retained (§4.9); the provenance and reader contracts hold or an explicit versioned transition is reviewed (§9); no SEC request was sent and nothing was written under `data/`.
      ROUTING: brainstorming

  > Stage 1c: COMPLETE (2026-10-30) — implemented by plan 6 (specs/plans/completed/6-sec-filing-index-member-completion.md). Its Handoff section names what Stages 2–5 consume.
  > Next: resume the roadmap.

- [x] Stage 2: Baseline campaign and coverage decision
      Objective: Produce an accepted written finding on the requested historical baseline, including every unresolved exception.
      Spec: §§4.2–4.9, 5–6, 7 G2.
      Gap closed: G2.
      Consumes: Stage 1 evidence, the explicitly selected native release/current config, the intended range, and preserved live-root evidence. The [submissions findings](findings/sec-filing-submissions-findings.md) §§2, 4.6–4.7: daily indexes add back-dated rows to old filing quarters (Approved at resume, 2026-10-21). Plan 2 Tasks 1–3 and 8 as offline preparation (`4508859`, `7b63168`, `ea482dd`, `780ea51`, `4004f2e`). The D5 release, then a reviewed revision of plan 2 for it before Tasks 4–7, scoped by plan 2, Handoff `:1676` (Resolved at resume, 2026-10-22). The values that revision must change, read against the release selected when it is written: plan 4, Handoff, Stage 2 bullet (Resolved at resume, 2026-10-27). Stage 1b's release and Handoff; the plan 2 revision is written against that release, not the D5 release (default (vi), approved at resume, 2026-10-27). The 1b release as built, the values the plan 2 revision must change, and its traps: plan 5, Handoff, Stage 2 bullet; the items deferred into this stage are in `specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost — 2026-10-28`, and the B4 revisit trigger in section `4-sec-filing-index-bounded-drain — 2026-10-27` (Resolved at resume, 2026-10-28). The release from the engine fix that plan 2 D12 routes, and its Handoff; the plan 2 revision is written against that release, not the 1b release, before any further invocation. That revision also covers the repair obligation of the nine moved pointers, ledger row k = 1, the window end 2026-11-05T13:00:00Z and the open quarter 2026Q4 (plan 2 D12, Handoff, bullet "Task 5 halt (2026-10-29)"; Resolved at resume, 2026-10-29). That release is the 1c release `c4de77b8…` (spec `specs/completed/sec-filing-index-member-completion.md`; evidence `specs/evidence/stage1c/`). The plan 2 revision is written against it, with its config, reserve and floor; the values it must change, the repair of member `3554e8ef…` and ledger row k = 1, the three members complete without a receipt, the skipped daily-index listing, and traps (a)–(e): plan 6, Handoff, Stage 2 bullet. No new item is deferred into this stage; "Two-release proof covers only first-generation 1b stores" stays open in `specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost — 2026-10-28` (Resolved at resume, 2026-10-30).
      Produces: A reviewed finite campaign scope/budget, per-invocation results/captures, a source-and-quarter coverage inventory, and an explicit complete-or-incomplete operating decision.
      Exit: Every requested baseline unit is accounted for by validated publication or a named gap/quarantine with owner disposition; the committed port evidence, immutable live-root objects and releases remain intact, and the absent L12 external directory stays recorded as lost (§6, `780ea51`; plan 2, Handoff; Resolved at resume, 2026-10-22).
      ROUTING: writing-plans

  > Stage 2: COMPLETE (2026-10-31) — implemented by plan 2 (specs/plans/completed/2-sec-filing-index-ingestion-spec.md). Its Handoff section names what Stages 3, 4 and 5 consume.
  > Next: resume the roadmap.

- [x] Stage 2a: Duplicate-key parser/schema design and its release (approved at resume, 2026-10-31)
      Objective: Ship a reviewed native release, under an owner-approved versioned design, on which an index source whose rows repeat a logical key no longer quarantines for that reason alone.
      Spec: §3 R3, R5, R9, R12; §§4.4–4.9, 5–6, 9; plan 2, Handoff.
      Gap closed: None directly; removes the duplicate-key quarantine that leaves G2 approved incomplete and gives G4 no quarterly authority.
      Consumes: The 1c release `c4de77b8…` and its evidence (`specs/evidence/stage1c/`). Stage 2's accepted finding, its quarantine enumerations and final coverage (`specs/evidence/baseline-campaign/coverage-finding.md` §§4.1–4.2, `quarantine/`, `final/coverage.json`), and the [submissions findings](findings/sec-filing-submissions-findings.md) §5. `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, item 1 (default (x)). Its stage spec proposes any amendment it needs to the spec's own duplicate-key rule (§4.4), as default (i) allowed for Stage 1a. Platform roadmap D1 and plan 3 DF6: the stage spec settles whether this release's locked inputs carry the platform member.
      Produces: A stage spec and plan; the owner-approved versioned parser/schema design; the change with offline tests; an offline re-transform of the retained duplicate-key sources; a reviewed release with setup, preflight and review evidence; the reviewed live-config selection with its effective-config SHA-256; and a plan Handoff that names every value Stage 2b's plan must use.
      Exit: Offline, on a copy of the retained objects, each of the 28 quarterly sources and 7 daily sources that quarantined with `conflicting duplicate logical key` transforms on the new release or stays quarantined for a reason other than the repeated key alone, which the stage spec names; the provenance and reader contracts hold or an explicit versioned transition is reviewed (§9); the offline checker and preflight pass on the new release, with the 1c release and older releases retained (§4.9); no SEC request was sent and nothing was written under `data/`.
      ROUTING: brainstorming

  > Stage 2a: COMPLETE (2026-11-02) — implemented by plan 7 (specs/plans/completed/7-sec-filing-index-duplicate-key.md). Its Handoff section names what Stages 2b, 3, 4 and 5 consume.
  > Next: resume the roadmap.

- [x] Stage 2a1: Pre-dispatch cost and its release (approved at resume, 2026-11-13)
      Objective: Ship a reviewed native release on which an invocation at the live store's registered-member count starts its first member before the dispatch cutoff, and the longest Stage 2b member fits one invocation.
      Spec: §3 R1, R2, R5, R6, R12; §§4.2, 4.7–4.9, 5–6, 9; plan 8, Handoff.
      Gap closed: None directly. It removes the plan 8 pre-dispatch limit that keeps G2 and G3 open.
      Consumes: The 2a release `e49d3ba8…` and its evidence (`specs/evidence/stage2a/`). Plan 8, Handoff, bullet "Task 5 halt (2026-11-06)": the phases before the first dispatch, the cost per registered member and its growth, the comparison with Stage 2 on the 1c release, the wrong premise of D6, and the store state. The Stage 2b evidence (`specs/evidence/stage2b/`: `startup-overhead.md`, `invocations/*.json`, `pre-campaign.md`). The run length fixed in code (`config.py`). Discovery alone took 862 s in invocation 2, so the stage spec decides how the 2026-07-01 member (3,239.6 s offline) fits (default (xiii)). Platform roadmap D1 and plan 3 DF6: the stage spec settles whether this release's locked inputs carry the platform member (default (xiv)).
      Produces: A stage spec and plan. A profiled diagnosis of the work before the first dispatch, including its rise from the 1c release to the 2a release. The change with offline tests. A reviewed release with setup, preflight and review evidence. The reviewed live-config selection with its effective-config SHA-256. A plan Handoff that names every value Stage 2b's new plan must use, including the growth in registered members per business day and the 2026-07-01 member's fit or its named limit.
      Exit: Offline, at a registered-member count that the stage spec fixes from the live store (208 at plan 8's halt) plus a growth allowance, and with discovery time taken from plan 8's measurements, a measurement shows no member starting before the dispatch cutoff on the 2a release and the first member starting before it on the new release. The longest Stage 2b member fits one invocation on the new release, or the owner approves a named, measured limit. The offline checker and preflight pass on the new release, with the 2a release and older releases retained (§4.9). The provenance and reader contracts hold, or an explicit versioned transition is reviewed (§9). No SEC request was sent and nothing was written under `data/`.
      ROUTING: brainstorming

  > Stage 2a1: COMPLETE (2026-11-15) — implemented by plan 9 (specs/plans/completed/9-sec-filing-index-pre-dispatch-cost.md). Its Handoff section names what Stages 2b, 3, 4 and 5 consume.
  > Next: resume the roadmap.

- [ ] Stage 2b: Baseline coverage on the Stage 2a release (approved at resume, 2026-10-31)
      Objective: Produce a revised, owner-accepted G2 finding on the Stage 2a release for the 28 quarterly units and the 7 daily duplicate-key sources.
      Spec: §§4.2–4.9, 5–6, 7 G2.
      Gap closed: G2, as a revised finding; Stage 2's approved-incomplete finding stays as history.
      Consumes: Stage 2a's release and Handoff. Stage 2's campaign evidence (`specs/evidence/baseline-campaign/`), accepted finding and dispositions, and plan 2's campaign files and stop rules as amended by Revision 4 (plan 2, Handoff). `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, item 1, its "Done when" (default (xi)). The quarterly ZIPs are retained, so the plan decides whether any SEC request is needed. If one is, the plan establishes the campaign limits that this section's opening requires before it is sent. Stage 2a's release as built is `e49d3ba8…`, selected by the live config at `4d1f806` with its effective-config SHA-256, reserve and floor. Its scratch-run times against the reserve, the launcher default and the 1,500 s budget, the 2a spec §6 expectations (the 2026Q3 approval gate among them), and its traps: plan 7, Handoff, Stage 2b bullet. Plan 2's campaign configs (`conf/stage2/*.json`) do not load on that release, so this stage needs v2 campaign configs, and plan 2's Stage 3 traps (a), (b) and (d) still apply (same bullet). Item 1 ages from 2026-10-31 until this stage's plan adds its own `→ planned` note (same bullet) (Resolved at resume, 2026-11-02). **Not met since 2026-11-06:** plan 8 halted at Task 5. Its Handoff, bullet "Task 5 halt (2026-11-06)", records that on the 2a release no member started before the dispatch cutoff at 127 or more registered members, that the D6 exception rests on a wrong premise, and what is still unknown. Do not route this stage again until the owner has decided how that is resolved (Amended at resume, 2026-11-06; see Open questions). The owner decided at resume, 2026-11-13: this stage consumes Stage 2a1's release and Handoff wherever this entry names the Stage 2a release, and gets a new plan written against that release. Plan 8 stays as halted evidence, and the new plan carries plan 8's Handoff forward. Plan 8's live approval and D6 do not carry over (default (xv), approved at resume, 2026-11-13).
      Produces: A reviewed scope and budget, per-invocation results and captures, a source-and-quarter coverage inventory, and a revised complete-or-incomplete operating decision. The retained-quarantine count in `docs/runbooks/local-ingestion.md` changes to match the campaign's result (plan 7, Handoff, Stage 2b bullet, trap "Stale count after a campaign"; Resolved at resume, 2026-11-02).
      Exit: Each of the 28 quarterly units and 7 daily duplicate-key sources is accounted for by validated publication or a named gap/quarantine with owner disposition; Stage 2's finding, the committed evidence, immutable live-root objects and releases remain intact (§6).
      ROUTING: writing-plans

- [ ] Stage 3: Daily catch-up acceptance
      Objective: Establish accepted manual daily continuation over the handoff and retained pending inventory.
      Spec: §§4.2–4.9, 5, 7 G3.
      Gap closed: G3.
      Consumes: Stage 2 coverage decision and explicit exceptions, retained discovery boundaries/pending work, and selected native release/current config. The D5 release, since F11 applies to a `daily` invocation too, and the pending inventory from Stage 2's `final/coverage.json` `daily_sources` plus a fresh discovery (plan 2 D5, O5, F4, Handoff; Resolved at resume, 2026-10-22). The D5 cutoff semantics (parent spec §4.7) and their overrun limit for a member running at the cutoff (plan 4 D4, Handoff, Stage 3 and Stage 5 bullet; Resolved at resume, 2026-10-27). The 1b release, config, reserve and floor that Stage 2 consumes, its measured member classes and traps, and the unmeasured A1 member class and history-scan cost deferred into this stage (plan 5, Handoff, Stage 3 bullet; `specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost — 2026-10-28`; Resolved at resume, 2026-10-28). Stage 1c's release, wherever this entry names the 1b release (default (ix), approved at resume, 2026-10-29). That release is `c4de77b8…`, with the same config, reserve and floor as Stage 2; each invocation lists the members `3554e8ef…`, `dc790624…` and `00c1f46d…` as already complete, and trap (a) of the Stage 2 bullet applies to every workflow command (plan 6, Handoff, "Stages 3, 4 and 5" bullet; Resolved at resume, 2026-10-30). Stage 2's coverage decision is approved incomplete, and Stage 2 left no quarterly baseline. Its daily and already-complete sources as built, the live config, traps (a)–(d) and the items deferred into this stage: plan 2, Handoff, Stage 3 bullet; `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31` (Resolved at resume, 2026-10-31). Stage 2a takes the parser/schema design item from this stage, and this stage consumes the Stage 2a release and the Stage 2b finding wherever it names the 1c release or Stage 2's coverage decision (defaults (x) and (xii), approved at resume, 2026-10-31). The Stage 2a release is `e49d3ba8…`, with the config, reserve and floor that Stage 2b consumes. Readers meet v1 and v2 row versions, and a multi-quarter read can hold both. Plan 6's list of three already-complete members still applies, but plan 7 did not re-check it. The traps: plan 7, Handoff, "Stages 3, 4 and 5" bullet (Resolved at resume, 2026-11-02). Stage 2b halted and has no finding, so wherever this entry names the Stage 2b finding the input is not met. The cost before dispatch probably also applies to the `daily` command, which was not measured (plan 8, Handoff, "Stages 3, 4 and 5" bullet; Amended at resume, 2026-11-06). Stage 2a1's release, wherever this entry names the Stage 2a release (default (xvi), approved at resume, 2026-11-13).
      Produces: A dated catch-up report with exact results/captures, boundary evidence, and unresolved-work disposition usable by later scheduling.
      Exit: Handoff-to-current daily discovery and pending units are accounted for without skipping failed directories or erasing older gaps; the owner accepts the reported coverage/limits.
      ROUTING: writing-plans

- [ ] Stage 4: Manual reconciliation acceptance
      Objective: Establish accepted operational reconciliation and operator handling before unattended reconciliation.
      Spec: §§4.2, 4.4, 4.6–4.9, 5, 7 G4.
      Gap closed: G4.
      Consumes: Stages 2–3 reports/exceptions, selected native release/config, and retained candidate/history/approval/rollback contracts. Stage 2's `gated` units and reconciliation-bound quarantine dispositions, and the closed-quarter quarterly-membership limit (plan 2 F5, F7, O6, O10, Handoff; Resolved at resume, 2026-10-22). The 1b release's full-check and full-rebuild paths, and the refused-C6-candidate retry block, which needs a recovery disposition when it occurs (plan 5, Handoff, Stage 4 bullet; `specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost — 2026-10-28`; Resolved at resume, 2026-10-28). Stage 1c's release, wherever this entry names the 1b release (default (ix), approved at resume, 2026-10-29). That release is `c4de77b8…`, with the same config, reserve and floor as Stage 2; each invocation lists the members `3554e8ef…`, `dc790624…` and `00c1f46d…` as already complete, and trap (a) of the Stage 2 bullet applies to every workflow command (plan 6, Handoff, "Stages 3, 4 and 5" bullet; Resolved at resume, 2026-10-30). Stage 2 left no `gated` unit, no refused incremental candidate and no quarterly membership authority, in place of the `gated` units and dispositions named above. A reconciliation has no quarterly authority to compare with until the duplicate-key design ships. The quarantine enumerations, the O10 trap and the item deferred into this stage: plan 2, Handoff, Stage 4 bullet; `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31` (Resolved at resume, 2026-10-31). Stage 2a takes that item from this stage, and this stage consumes the Stage 2a release and the Stage 2b finding wherever it names the 1c release or Stage 2's reports (defaults (x) and (xii), approved at resume, 2026-10-31). The Stage 2a release is `e49d3ba8…`, with the config, reserve and floor that Stage 2b consumes. Readers meet v1 and v2 row versions, and a multi-quarter read can hold both. Plan 6's list of three already-complete members still applies, but plan 7 did not re-check it. The traps: plan 7, Handoff, "Stages 3, 4 and 5" bullet (Resolved at resume, 2026-11-02). Stage 2b halted and has no finding, so wherever this entry names the Stage 2b finding the input is not met (plan 8, Handoff, "Stages 3, 4 and 5" bullet; Amended at resume, 2026-11-06). Stage 2a1's release, wherever this entry names the Stage 2a release (default (xvi), approved at resume, 2026-11-13).
      Produces: A reconciliation report with exact source/candidate/generation evidence and accepted change, gate, revert, quarantine, and recovery dispositions.
      Exit: The reviewed range has a retained manual refresh outcome, every unresolved candidate/gap has explicit disposition, and required approvals name exact authority without bypassing refusal rules.
      ROUTING: writing-plans

- [ ] Stage 5: Local scheduling and observed-operation acceptance
      Objective: Design and validate unattended local invocation of the accepted workflows.
      Spec: §§2.2–2.3, 3 R13, 4.7–4.10, 5–6, 7 G5.
      Gap closed: R13; G5.
      Consumes: Stages 2–4 accepted operating reports/limits and the existing native launcher; no scheduler mechanism or cadence is assumed approved. The D5 release and plan 2's invocation rules: work fits one invocation (F8), and no member is after the pinned end (F9) (plan 2 D5, Handoff; Resolved at resume, 2026-10-22). The D5 cutoff semantics (parent spec §4.7) and their overrun limit for a member running at the cutoff (plan 4 D4, Handoff, Stage 3 and Stage 5 bullet; Resolved at resume, 2026-10-27). The 1b release, config, reserve and floor, and the history-scan growth and unmeasured A1 member class deferred into this stage (plan 5, Handoff, Stage 5 bullet; `specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost — 2026-10-28`; Resolved at resume, 2026-10-28). Stage 1c's release, wherever this entry names the 1b release (default (ix), approved at resume, 2026-10-29). That release is `c4de77b8…`, with the same config, reserve and floor as Stage 2; each invocation lists the members `3554e8ef…`, `dc790624…` and `00c1f46d…` as already complete, and trap (a) of the Stage 2 bullet applies to every workflow command (plan 6, Handoff, "Stages 3, 4 and 5" bullet; Resolved at resume, 2026-10-30). Stage 2's run times, audit totals and stop rules as amended by plan 2 Revision 4, its traps, and the quarantine-retention item deferred into this stage: plan 2, Handoff, Stage 5 bullet; `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31` (Resolved at resume, 2026-10-31). This stage consumes the Stage 2a release and the Stage 2b finding wherever it names the 1c release or Stage 2's reports (default (xii), approved at resume, 2026-10-31). The Stage 2a release is `e49d3ba8…`, with the config, reserve and floor that Stage 2b consumes. Readers meet v1 and v2 row versions, and a multi-quarter read can hold both. Plan 6's list of three already-complete members still applies, but plan 7 did not re-check it. The traps: plan 7, Handoff, "Stages 3, 4 and 5" bullet (Resolved at resume, 2026-11-02). Stage 2b halted and has no finding, so wherever this entry names the Stage 2b finding the input is not met. The cost before dispatch bears on unattended runs, because an invocation that starts no member makes no progress (plan 8, Handoff, "Stages 3, 4 and 5" bullet; Amended at resume, 2026-11-06). Stage 2a1's release, wherever this entry names the Stage 2a release (default (xvi), approved at resume, 2026-11-13).
      Produces: A reviewed scheduler design/implementation, disabled installation and explicit enable/disable records, operating/recovery documentation, and observed scheduled-run evidence.
      Exit: R13 has scheduler-specific verification and accepted actual daily/reconciliation executions linked to durable results/logs; missed-run, overlap, host lifecycle and DST policies are exercised or their approved limits recorded.
      ROUTING: brainstorming

## Stage-spec stamp

Each future stage spec's Rollout note, copied into its plan header, carries:

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage N — on plan completion, tick the
> stage and re-validate later stages against what shipped.

Completion requires an implementing plan or accepted investigation finding and its evidence. Add:

> Stage N: COMPLETE (YYYY-MM-DD) — implemented by plan <id> (path).
> Next: resume the roadmap.

Do not tick a stage from an exit code, source-project stamp, manual smoke, or this rewrite alone.
Stage 1 is the explicit retrospective exception supported by the already completed local plan.
Future plan handoffs must name changed assumptions for later stages; historical artifacts stay
unchanged when new configuration or operating evidence is added.

## Completion

The owner reviews this local partition before Stage 2, and each inserted stage (1a, 1b, 1c, 2a, 2b) before
it is routed; approving either authorizes no SEC request or live run. Rewriting these files starts no campaign,
installs/enables no schedule, and grants no live-access or budget authorization. On a later request
to resume, use derive-roadmap to reconcile actual completion stamps and route only the first
unticked stage whose planning Consumes are met. Its plan must establish the additional live-execution
gates above before any acquisition. Stage 2 is a planning handoff, not a direction to rerun the
completed port or genuine acceptance harness. Do not plan the whole roadmap as one implementation.

Retire this roadmap/spec only after a final conformance audit accounts for R1–R13 and G1–G5 using
local implementation, operational, and observed-schedule evidence. Keep “approved incomplete
coverage” distinct from complete historical coverage. Unmet requirements need a new stage or an
explicit written deferral in `specs/deferred_items.md`; they do not vanish through retirement.
If parked earlier, retain self-contained remaining work and label the parked status explicitly.

Preserve the existing data root, all releases, retired native plan/design, original incomplete
acceptance results, and separate reviewed supplemental L12 pass. Future evidence is additive;
it never relabels the original execution or turns bounded acquisition into historical coverage.
