# Pre-dispatch cost and its release — Stage 2a1 Design Spec

**Status:** Draft for owner review, 2026-11-14.
**Project:** `/Users/lowell/Projects/sec-edgar-local`.
**Parent spec:** [SEC filing-index ingestion](sec-filing-index-ingestion-spec.md) (§§3 R1, R5, R6, R12; 4.2, 4.7–4.9; 6; 9).
**Roadmap:** [ingestion roadmap](sec-filing-index-ingestion-roadmap.md), Stage 2a1.
**Inputs:** the 2a release `e49d3ba8…` and its evidence (`specs/evidence/stage2a/`); plan 8, Handoff, bullet "Task 5
halt (2026-11-06)" (`specs/plans/8-sec-filing-index-ingestion-spec.md`); the Stage 2b evidence
(`specs/evidence/stage2b/`: `startup-overhead.md`, `invocations/*.json`, `pre-campaign.md`); the
[Stage 2a1 diagnosis](evidence/stage2a1/diagnosis/diagnosis.md); `specs/deferred_items.md`, item "History-scan cost";
the Stage 1b reserve rule ([1b spec](completed/sec-filing-index-per-member-cost.md) §6); `config.py` (the fixed
run length).

## 1. Purpose

Plan 8 halted at Task 5. In both live invocations on the 2a release, no member started before the dispatch cutoff.
The work before the first dispatch took 2,715 s or more at 208 registered members. So Stage 2b cannot make
progress on the 2a release, and G2 and G3 stay open.

This stage ships a reviewed native release on which an invocation starts its first member well before the cutoff,
at the registered-member count that Stage 2b will reach. The stage also shows that the longest Stage 2b member fits
one invocation, or it stops for the owner.

The stage is offline. It sends no SEC request and writes nothing under `data/`. The live store first meets the new
release in Stage 2b.

### 1.1 What the diagnosis found

The [diagnosis](evidence/stage2a1/diagnosis/diagnosis.md) profiled the work on scratch copies of the live store
(208 members) and of the plan 8 Task 3 backup (127 members). Its main findings:

- **Repetition.** `runner.select_work` repeats store-wide checks once for each registered member (§1 of the
  diagnosis). The history pass `_publish_calls` takes about 3.4 s and runs two or three times per member. A new
  member with no binding pays one full registry check (`WorkflowMembers.inventory()`, 23.3 s at 208). Each
  `read_member` re-validates its parent's whole discovery session.
- **Slow decoding.** `models.record_from_mapping` and `validate_record_fields` call `typing.get_type_hints` on every
  record. One publish of the daily 2026-07-01 member made 49,970,107 such calls.
- **No code regression.** On the same store and versions, the 2a code costs the same as the 1c code (§4 of the
  diagnosis). The rise comes from v2 (every member is pending), member growth (127 to 208), the per-new-member
  registry check and a larger history.
- **Discovery is short.** Plan 8 recorded "discovery 862 s" for invocation 2. The discovery child took 29 s. The
  other 832 s was the projection of 53 new members, which is selection work (§3 of the diagnosis).
- **Member growth.** Each business day with a new daily listing gives a new discovery parent. Every source in it
  registers again as a new member: 28 in invocation 1 and 53 in invocation 2. Old members stay registered (§5).

Two diagnosis-only spikes bound the effect of a fix:

| Spike | Effect at 208 members |
|---|---|
| One type-hints result per record type | Every selection piece about halves. The 2026-07-01 publish falls from 3,453.3 s to 988.5 s. |
| The same, plus each store-wide check once | The first member would start at about 170 s, plus about 0.2 s for each new member. |

## 2. Scope

### 2.1 Goals

- A per-type cache for record type hints.
- Within one selection, each store-wide check runs once between child executions, and every member reuses it.
- The registry check for a new member reads only that member's source.
- Offline evidence that, at the growth allowance, the first member starts before the cutoff on the new release and
  not on the 2a release.
- Offline member walls for the Stage 2b members on the new release, against the 1,056 s member-wall limit (O1, §8).
- A reviewed release, a live-config selection, and a plan Handoff with the values Stage 2b's new plan must use.

### 2.2 Non-goals

- A live run or any SEC request. That is Stage 2b.
- The per-member history pass in each dispatched member's own completion checks (`processing.py:33`, `:104`). It
  stays, and the type-hints cache halves it. The deferred item "History-scan cost" stays open (decision
  "Approach", §8).
- Retiring old registered members. Members accumulate at about 55 for each business day with a new listing. With
  this release that costs about 0.5 s for each registered member in each run. That is enough for Stage 2b, but not
  for a year of daily runs (about 13,750 members). The plan's Handoff records it as a deferred item for Stage 5.
- A run longer than the 3,300 s launcher default, or a change to the 3,600 s maximum in `config.py`. Plan 8 D6 does
  not carry over (roadmap default (xv)).
- The platform workspace member (decision "Platform", §8).
- Any change to the cost of transform or publish, apart from the type-hints cache.

### 2.3 Anti-goals

The design fails, even if tests pass, when any of these holds:

- A selection on the new release differs from the 2a release's selection for the same store and inputs, apart from
  the run context.
- A kept value is used after a child process has run, or a kept failure hides a later valid read.
- A dispatched member, a low-level command or the finish step skips a check that it runs today.
- A record decodes to a different value, or a refused record gives a different error message.

## 3. Requirements

| ID | Requirement |
|---|---|
| H1 | Selection decides as today. For the same store, intent and discovery result, the new release's selection equals the 2a release's selection, apart from the run context: the same members, jobs, already-complete captures, superseded members, gaps and counts, in the same order. |
| H2 | Within one selection, while the computation succeeds, the publish-call authority (`_publish_calls`) is computed at most once before the discovery child and once after it. Each parent ref is re-validated (`read_parent`) at most once in each of those two phases. A failed computation runs again for its next caller (H3). |
| H3 | A kept value never crosses a child execution. Every kept value is dropped when the discovery child returns or raises. A failure is never kept: a failed computation runs again for the next caller, as today. |
| H4 | Outside `select_work`, every check runs as today. The dispatch loop, `process_member`, `sibling_completion`, the finish step, `freeze_selection` and every low-level command use no kept value. |
| H5 | `reuse_exact_binding` validates only the registered members of the member's own source. It finds the same candidates, returns the same gaps in the same order, and writes the same binding as today. |
| H6 | Record decoding computes the type hints of each record type once per process. Decoded values and error messages are unchanged. |
| H7 | No format changes: generation, manifest, receipt, member evidence, selection, Attempt, config, outcome and exit-code formats stay as they are. The new release continues 2a-origin pending work. The 2a release continues work that the new release left pending. |
| H8 | Parser and schema stay `sec-index-parser-v2` / `sec-index-v2`. No config key is added. The 3,600 s maximum and the 3,300 s launcher default are unchanged. |
| H9 | The release is built by `build_release` from clean committed `main`. The package version stays `0.2.0`. `uv.lock` and the requirement lines of `uv export --package sec-edgar-ingest --no-dev --no-emit-workspace` are byte-identical to the 2a build inputs, with no platform member. The 2a release and older releases are retained (§4.9). |

## 4. Design

### 4.1 Components

| Unit | Change |
|---|---|
| `models.py` | A per-type cache in front of `typing.get_type_hints` for `record_from_mapping` (`:238`) and `validate_record_fields` (`:280`). It returns a read-only mapping. The cache holds one entry for each record type (H6). |
| New `workflows/selection_checks.py` | A `SelectionChecks` object, built by `select_work` and passed down. It keeps the publish-call authority and the parent re-validations for one phase of one selection (§4.2). |
| `workflows/completion.py` | `_obligations`, `outstanding_repairs`, `evaluate_member` and `capture_member_provenance` take an optional `checks` keyword. With `checks`, `_obligations` takes the call list and each call's decoded transformed input from it. Without `checks`, they run as today. |
| `workflows/provenance.py` | `read_member` and `project_member` take an optional `checks` keyword and use it for `read_parent`. Without it they run as today. |
| `workflows/members.py`, `workflows/legacy.py` | `WorkflowMembers.inventory`, `WorkflowMembers.completed` and `bootstrap_legacy` pass an optional `checks` through to `read_member` and `read_parent`. |
| `workflows/runner.py` | `select_work` builds one `SelectionChecks`, passes it to every check it calls, and drops its kept values after the discovery child (H3). `reuse_exact_binding` filters registered members by source before it validates them (H5). `run_workflow` and the dispatch loop are unchanged. |

`SelectionChecks` has three operations:

- `publish_calls()` returns each checked publish call with its decoded transformed input. The first call runs today's
  `_publish_calls` checks. Later calls return the kept result.
- `parent(ref)` returns `read_parent(ref, store, objects)`. Only a successful result is kept.
- `renew()` drops every kept value.

The builder may reshape these units, for example by passing the parent cache to `read_member` as its own argument.
The requirements in §3 bind, the table does not.

### 4.2 Data flow

`select_work` keeps its order. Only where each check comes from changes:

1. Build `checks`. Run `bootstrap_legacy` and `inventory()` with it. Parent re-validations are now kept, so a parent
   shared by many members is re-validated once.
2. For each retained member, run `completed` and, if needed, `evaluate_member`, with `checks`. The first history pass
   computes the publish-call list. Every later member filters the kept list by its source. Each member still reads
   its own repair rows, receipts, bindings and `Processing` row live.
3. Run the discovery child. Then call `checks.renew()`, whether the child returned or raised.
4. For each discovered source, run `project_member` and `reuse_exact_binding` with `checks`. A new member's reuse
   check validates only the members of its source (H5).
5. Run the second `evaluate_member` pass and `capture_member_provenance` with `checks`. The publish-call list and the
   parents are computed again once, then kept.
6. Return the selection. `freeze_selection` runs as today, and the dispatch loop runs as today (H4).

The diagnosis spike projects the work before the first dispatch with this design at about 370 s for 450 registered
members, 55 of them new in the run. That is conservative: the spike decoded each publish input once per member, and
`freeze_selection` was not re-timed with the cache.

### 4.3 Why each kept value stays valid

A kept value lives only between child executions. Selection runs one child, `discover`. The other writes inside the
same phase, and why they do not change a kept value:

- **Publish calls.** The list comes from `WorkflowChildCall` and `Attempt` rows for `publish`. Selection starts no
  publish child. `_obligations` writes repair rows, repair-authority objects and resolutions, but only for calls
  that are already in the list. A legacy `Attempt` joins the list when it has such a record, so the list cannot
  grow from these writes. `project_member` writes `WorkflowMember` rows and member worksets. `transfer_binding`
  writes `Binding` rows. `_publish_calls` reads neither.
- **Parents.** `read_parent` reads the content-addressed parent workset, its `DiscoverySession` row, its
  `DirectoryProgress` rows and listing receipts, and any `WorkflowParentRecovery` row. Inside one phase only
  `bootstrap_legacy` writes one of these: a recovery row, which can turn a failing read into a passing one. Failures
  are not kept (H3), so the next read sees it. The discovery child writes session and progress rows, and `renew()`
  follows it.

Tests prove both points with counters and with a fresh recomputation after each kind of write (§5).

The argument covers writes made by the selecting process. It assumes no other writer runs on the store during a
selection. Today's per-member re-reads give no consistent view under a concurrent writer either, so this adds no new
requirement.

**The trade-off.** Today each member re-reads and re-hashes the stored objects behind the history and its parent.
With this design, a selection does that once in each phase. An object damaged during a selection is caught by the
member's own checks at dispatch, which use no kept value (H4), or by the next run.

### 4.4 Errors and edge cases

1. **A corrupt publish call or parent.** The computation raises as today and nothing is kept. Each member that needs
   it gets the same `state_conflict` gap as today. That case costs what it costs today.
2. **The discovery child fails** (`ChildUnfinished`). `renew()` still runs. The rest of selection is unchanged.
3. **A store with no publish calls.** The kept list is empty and is reused.
4. **A resumed attempt** whose `selection.json` exists. `run_workflow` calls only `freeze_selection`, which uses no
   kept value.
5. **`daily` and `reconcile`.** They run the same `select_work` and get the same gain. Only `backfill` was timed.
6. **A sibling member at dispatch.** `sibling_completion` calls `reuse_exact_binding` without `checks`. The source
   filter (H5) also removes its full registry check.
7. **A malformed `WorkflowMember` row.** The source filter reads the row's `source` field only when the row is a
   mapping. A row that cannot be read is skipped, as `inventory()` skips it today. `select_work` still reports it
   through its own `inventory()` call.

### 4.5 Release compatibility

- Nothing that the new release writes differs in format from what the 2a release writes (H7). So the 2a release can
  continue a store that the new release wrote, and the reverse. A two-release test shows both directions (§5).
- Exact replay of a completed 2a-era result still needs the 2a release (parent §4.9).

## 5. Verification (offline)

The offline checker gate covers, with synthetic fixtures:

1. **Selection equality (H1).** For fixture stores with finished, pending, superseded, repair-obligation and
   corrupt members, `select_work` with `checks` returns the same selection as without. This includes a discovery
   child that fails.
2. **Counts (H2).** Call counters show one `_publish_calls` computation per phase and one `read_parent` per parent
   ref per phase, at 1, 10 and 50 registered members.
3. **Validity (H3).** After each write kind of §4.3, a fresh `_publish_calls` and `read_parent` equal the kept
   values. A parent that fails, then gains a recovery row, passes on the next read. After `renew()`, nothing is
   kept.
4. **Unchanged paths (H4).** `process_member`, `sibling_completion`, `freeze_selection` and the low-level commands
   run with no `checks`. A test fails if one of them receives a kept value.
5. **Reuse (H5).** The old and new `reuse_exact_binding` give the same candidates, gaps, order and binding. The
   fixtures include a corrupt member of another source, a corrupt member of the same source and a corrupt reuse
   pin.
6. **Decoding (H6).** For every record type in the package, the cached hints equal `typing.get_type_hints`. The
   existing decoding and refusal tests pass unchanged. The cached mapping cannot be changed by a caller.
7. **Two releases (H7).** On fixture stores, the new release continues 2a-origin pending work, and a 2a build
   continues work that the new release left pending. The 2a build comes from its revision in the branch gate, and
   once more from the installed `e49d3ba8…` release.

The full existing suite passes on the release. Offline preflight passes with the release selected.

## 6. Release and exit evidence

**Order.** The gate tests (§5) pass on the branch. The branch merges to `main`, and the release is built from `main`.
The timings below run on the installed release. Both stop rules hold the live-config selection, as plan 7 P11 did for
Stage 2a. A release that fails a bar stays retained in `releases/` and is never selected. The plan may run the
replay earlier on the branch as a check, but the evidence comes from the installed release.

All timing runs use scratch copies outside `data/` and `backups/`, made with no writer running. Each timed run
starts from a fresh copy, because these paths write. The interpreter flags are the release's own: `-I -B -X
pycache_prefix=/dev/null`.

**Pre-dispatch measurement.** A harness under `specs/evidence/stage2a1/` runs `run_workflow` on a scratch copy with a
dispatcher that sends no request. For `discover` it returns a recorded discovery result from plan 8. It stops at the
first member dispatch. It records the time of each phase: before discovery, discovery, projection, after discovery,
freeze. The plan chooses how the copy reaches a known starting state. The evidence must give:

- both releases on the same replay of invocation 2's selection, with the time to the first dispatch on each
- the per-phase cost of each registered member and of each new member on the new release, from runs at two member
  counts at least
- the selection equality of H1 between the two releases on that replay
- the projection to the growth allowance: 450 registered members at the start of a run, 55 new members in it, the
  29 s discovery child and today's history.

The allowance is 208 (plan 8's halt) plus 4 business days at 55 new members each, rounded up.

**Pre-dispatch bar.** With the 3,300 s launcher default and the 1,800 s reserve, the cutoff is 1,500 s after the run
starts. The Exit needs the projected first dispatch on the new release before the cutoff, and none before it on the
2a release. This spec also sets a target of 600 s or less for the new release (40 % of the window). If the
projection exceeds 600 s, the stage stops before the live-config selection and reports to the owner.

**Member walls.** Re-run plan 8's member timing (`specs/evidence/stage2b/scratch/order-timing.py`, ten steps in true
dispatch order) on the new release, on a scratch copy of the plan 8 Task 3 backup. That is the store plan 8 timed, so
each wall compares directly with `pre-campaign.md`. Plan 8's walls left out the engine work outside the production
calls: the member's two completion checks, its replay check and its child starts. The plan measures that work on
the new release and adds it to each wall. This follows the Stage 1b definition: from the member's entry into the run
loop to its durable receipt.

**Member-wall stop rule.** The limit is 1,056 s (O1, §8). If the longest member wall exceeds it, the
Exit is not met. The stage stops before the live-config selection and asks the owner to choose one of three paths:

- approve a named limit backed by the measured wall
- raise the reserve under the Stage 1b rule, which moves the cutoff earlier
- add cost work to this stage and measure again.

The plan carries no cost work beyond §4. If the owner takes the third path, the plan is revised then, and another
release is built.

**Release.** A content-addressed release from `main` with setup, preflight and review evidence under
`specs/evidence/stage2a1/`, in the 2a layout. The 2a release and older releases stay retained.

**Live-config selection.** Only `release_manifest` changes in `conf/sec-edgar-local.json`. The reserve stays at
1,800 s unless the owner takes the second path of the member-wall stop rule. Offline preflight confirms the new
effective-config SHA-256. No workflow runs on the live store.

**Handoff to Stage 2b.** The plan's Handoff names at least:

- the release ID and commit, and the config hash
- the pre-dispatch times on both releases, the per-member costs and the projection
- member growth: about 55 new members for each business day with a new listing, and none for a run that finds the
  same listings
- every measured member wall against the limit, and the 2026-07-01 member's wall
- that the run length is the 3,300 s launcher default, with the cutoff at 1,500 s
- that the diagnosis §6 hypothesis about the 2026-07-01 member in the real order is still unchecked
- that each dispatched member still runs its own history passes (deferred item "History-scan cost")
- the new deferred item on registered-member accumulation (§2.2)
- that selecting the 2a release again is supported (H7)
- the 100 `.pyc` files that the diagnosis left in the 2a and 1c release venvs, and the owner's decision on them
- the traps of plan 8's Handoff that still apply.

**Deferred items.** "History-scan cost" stays open, with its revisit triggers unchanged. The plan's completion adds
the accumulation item (§2.2) with its consumer, Stage 5.

## 7. Parent-spec and roadmap amendments

At plan completion:

- **§4.2.** One paragraph: within one selection, the publish-call authority and each parent's re-validation run once
  between child executions. Each dispatched member's own checks still re-validate everything.
- **§4.8.** The new release, its commit and the effective-config SHA-256. The reserve stays at 1800 s, unless the second path of the member-wall stop rule changes it.
- **§4.9.** A paragraph for this release: no format change, and selecting the 2a release again is supported.
- **§6.** Tests now cover selection equality and the kept-value rules.

§9 needs no change: no provenance or reader contract changes.

At the roadmap resume after this stage, the Stage 2a1 and 2b entries' wording "Discovery alone took 862 s" changes to
the 29 s discovery child plus 832 s of member projection (diagnosis §3). The Exit's "a measurement shows" at the
allowance reads as measured per-phase costs at two member counts, projected to the allowance (§6).

The runbooks `docs/runbooks/release-upgrades.md` and `local-ingestion.md` get the new release.

## 8. Decisions

Owner answers at brainstorming:

- **Profiling** (2026-11-13): "Yes, profile now". Read-only, on scratch copies of the store.
- **Approach** (2026-11-14): "A: once per run". The per-type hints cache plus one computation of each store-wide
  check per selection phase. Under approach A, the deferred item "History-scan cost" stays deferred. Approach B
  would have taken it into this stage.
- **Platform** (2026-11-14): "Yes, hold it". The release's locked inputs carry no platform member, as in Stages 1b,
  1c and 2a (H9). Plan 3's Merge gate waits for this release.
- Roadmap defaults (xiii)–(xvi), approved 2026-11-13: one stage, offline only. This stage settles the platform
  member. Stage 2b gets a new plan against this release. Stages 3–5 consume this release.
- **O1 — Member-wall limit** (2026-11-14): "1,056 s (Stage 1b)". A member that starts just before the cutoff must
  still leave the 480 s finish floor. Plan 8 D2 does not carry over. The options were:
  - **(a) Stage 1b rule (picked):** 1.25 × wall + 480 s ≤ 1,800 s, so a wall of 1,056 s or less. It keeps the
    measured floor for the finish step after a 25 % overrun.
  - **(b) Plan 8 D2:** 1.25 × wall ≤ 1,800 s, so a wall of 1,440 s or less. A member at that limit that starts at the
    cutoff ends 360 s before the deadline, which is less than the 480 s floor.

  On the 2a release, four plan 8 walls exceed 1,056 s: 2024Q1 (1,126.9 s), 2026Q3 (1,231.6 s), 2026Q1 (1,398.8 s)
  and 2026-07-01 (3,239.6 s). With the cache spike, only 2026-07-01 was re-timed: 988.5 s for its publish, under a
  call-counting wrapper. The other three are not measured with the cache. The full wall of 2026-07-01 adds its
  transform (1.9 s) and the engine work outside the production calls (§6). So under (a) it lands within a few
  percent of the limit, on either side. Under (b) it has about 400 s to spare.

Calls made in writing this spec, for the owner's review:

- **Growth allowance:** 450 registered members, 55 new in the run (§6). Stage 2b's length on the new release is not
  known until the member walls are measured. The Handoff gives the growth rate so Stage 2b's plan can check it.
- **Pre-dispatch target:** 600 s or less, beside the Exit's cutoff (§6).
- **Discovery time:** the 29 s discovery child, not plan 8's 862 s (§1.1, §7). Both figures come from plan 8's
  invocation 2. The other 832 s was member projection, which this design changes. With 862 s, the projection at the
  allowance would be about 1,200 s, above the 600 s target, and the stage would stop.
- **Measurement at the allowance:** the roadmap Exit says "a measurement shows" the first-dispatch result at the
  allowance. No store with 450 members exists offline. So the spec times both releases on a replay of invocation
  2, measures the new release's per-phase costs at two real member counts, and projects them to 450 (§6). With
  this design, the cost grows close to linearly with the member count.
- **Order of evidence:** merge, build, then time, with both stop rules holding the live-config selection (§6). This
  follows plan 7 P11.
- **No cost-work task in the plan.** The third path of the member-wall stop rule revises the plan (§6).
- **Run length:** the 3,300 s launcher default, so the cutoff is at 1,500 s. Plan 8's 3,600 s (D6) does not carry over.
- **Source filter in reuse (H5)** instead of keeping the registry. It also speeds the dispatch path, and no kept
  value is needed.
- **No failure is kept, and every kept value is dropped after the discovery child (H3).** Re-validating once more
  after discovery costs a few seconds and removes any question about the discovery child's writes.
- **Scope of kept values:** `select_work` only (H4). `freeze_selection` keeps its own checks and gains only from the
  cache.
- **The 100 `.pyc` files** stay in the release venvs until the owner decides. Release verification skips
  `__pycache__` (`runtime.py:476`).

Approaches considered:

| Approach | What changes | Trade-off |
|---|---|---|
| **A. Once per run** (picked) | The hints cache. Selection computes each store-wide check once per phase and reuses it for every member. | Narrow and easy to test. Every run still re-validates everything once. Each dispatched member keeps its own history passes, halved by the cache. |
| B. Once per process | The hints cache. A memo of every validated stored object, keyed by content hash, shared by selection and the member's completion checks. | Also removes the per-member passes, so it takes "History-scan cost". Wider change: `Attempt` rows change over time and need version keys. Damage during a run is caught only on the next run. |
| C. Durable indexes | The hints cache. Per-source indexes stored in the state database. | Scales best over years. New record kinds, a backfill of the live store and a §9 review: more than Stage 2b needs. |

## 9. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a1 — on plan completion, tick the stage and re-validate later stages against what shipped.
