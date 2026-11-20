# Deferred items

## 4-sec-filing-index-bounded-drain — 2026-10-27
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [x] Per-member cost (owner decision D2, plan 4): the owner does not accept the measured
      per-member cost. Full-size quarterly members took more than 9,000 s, and no reserve fits
      them under the 3,300 s launcher default. A per-member-cost roadmap stage goes before
      Stage 2. Plan 4 did not place it. Inputs: specs/evidence/d5-release/measurement.md and
      finish-measurement.json. See specs/plans/completed/4-sec-filing-index-bounded-drain.md,
      Decisions D2 and Handoff. Size: design. Done when: derive-roadmap places the stage in
      specs/sec-filing-index-ingestion-roadmap.md and a plan for it completes.
      → done in plan 5 (specs/evidence/stage1b/measurement.md, specs/evidence/stage1b/release.md)
- [x] Unmeasured drain costs (plan 4 Task 2): the full measurement run reached its deadline, so
      measure 1 (a closed-quarter rebuild by one back-dated daily row), the 14-quarter fan-out,
      and the 40- and 80-source open-quarter publish marks were never measured.
      scripts/measure-d5-drain.py holds the scenarios. Size: plan. Done when: the per-member-cost
      stage measures them, or its spec records that they are not needed.
      → done in plan 5 (specs/evidence/stage1b/measurement.md)
- [x] Provisional live reserve (owner decisions D2 and D4): conf/sec-edgar-local.json sets
      execution.dispatch_reserve_seconds to 1800 without a measured basis. It covers a daily
      member with up to about 18 sources already in its quarter, not full-size quarterly
      members. Size: design. Done when: the owner approves a reserve set from measured member
      costs, or approves 1800 as final.
      → done in plan 5 (specs/evidence/stage1b/measurement.md, specs/evidence/stage1b/release.md)
- [x] B4 single-candidate limit (final-review note): runner.sibling_completion in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py never skips a source
      with two or more historical snapshots, so those sources keep F10's repeated child
      sequence. A refused skip also costs an extra inventory scan and evaluate_member before
      process_member repeats it. Size: plan. Revisit if: the per-member-cost stage or Stage 2
      shows repeated child sequences or refused-skip scans as a material share of run time.
      Checked against plan 5 section 6 (specs/evidence/stage1b/measurement.md, 2026-10-28): engine time inside a member's wall is 0.1% to 0.4% for the full-size members (closed baseline, authority) but 28.8% for the open daily members (about 3.7 s each) and 54.5% for the finish members. The scenarios do not separate repeated child sequences or refused-skip scans, so the revisit trigger is neither met nor cleared. Owner decision D12: keep open.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Order-aware two-release proofs (owner decision R2): member order is not pinnable because
      member_id hashes wall-clock and per-build inputs. In about half the runs of the pending
      scenario in packages/sec-edgar-ingest/tests/test_release_upgrade.py, and one run in four
      of the first test in test_release_origin.py, no child runs on the origin release. See
      specs/evidence/d5-release/two-release.md, "Limits of the proof". Size: plan. Revisit if:
      member ordering becomes deterministic, or an origin-release regression escapes these tests.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Test-hygiene Minors from plan 4 task reviews (all triaged to ship by the whole-branch
      review), in packages/sec-edgar-ingest/tests/:
      test_workflow_cli.py engine admission test has a vacuous assertFalse(live data exists),
      a comment that says "missing manifest" for a case that reaches the isolation refusal, and
      covers backfill only; stale comment near test_workflow_cli.py:72.
      test_workflow_drain.py: a comment near :174 overclaims; the missing-key test is weak; no
      test reuses a receipt after a cutoff; the P8 test compares () == () because fixture
      children emit no gaps; the tamper set is thin; replay checks are near-vacuous.
      test_release_upgrade.py has a tautological assertion near :203; the repair probe's
      both-B-first fallback was proven once, by a reverted local edit.
      Production: the contract-level B4 branch in workflows/contracts.py is looser than the full
      B4 shape (processing._validate_sibling_completion enforces it); a refusal message has a
      cosmetic order issue. Size: quick-fix. Done when: one test-hygiene pass over these files
      lands with the full gate green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.

## 5-sec-filing-index-per-member-cost — 2026-10-28
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [x] Review Minor (plan 5 Task 10, task review of the runtime race fix 17d78da; see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md, Decision D8): in `run_child`,
      packages/sec-edgar-ingest/src/sec_edgar_ingest/runtime.py, the two group-existence probes
      `os.killpg(process.pid, 0)` at :657-659 and :666-668 catch only `ProcessLookupError`. On
      macOS, `killpg` raises `PermissionError` (EPERM) when the only processes left in the group
      are unreaped zombies. Both probes run after `process.wait`, so the leader is reaped, but a
      detached descendant can be a short-lived zombie. Then `run_child` raises instead of
      returning a `ChildExit`. The reviewer did not reproduce it. `forward` (:613-623) already
      catches both errors since 17d78da. Deferred: the race-fix brief limited the change to
      `forward`, and `src` is frozen at the 1b release build. To do: write a test that keeps a
      zombie descendant in the child's group (model it on
      `test_native_dispatch.SupervisedProcessTests.test_overflow_survives_a_parent_that_reads_slowly`),
      then catch `PermissionError` in both probes. Open question: does EPERM count as drained?
      The review's kernel check covered a zombie group leader, alone or with a live member. It
      did not cover a reaped leader with a zombie descendant. Cost: full gate,
      release build, config selection. Size: quick-fix. Done when: both probes handle
      `PermissionError`, a zombie-descendant test pins it, and the full gate is green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] A candidate that the C6 equivalence check refuses blocks its own retry (plan 5 whole-branch
      review, finding I1; the owner chose "test and document" with no code change in Decision D7,
      and ruled on the recovery text in Decision D12, both 2026-10-28; see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md). In
      packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/catalog.py, `_incremental_candidate`
      (:261-287) stages both files and stores the manifest (`_store_manifest`, :283) before C6
      runs (:284). The store is write-once, and the generation address depends only on the
      quarter, the base generation and the source fingerprint. So a retry with the same inputs
      finds the stored candidate through `_existing` (:102-111) and runs the full content check on
      it. When that check fails, `publish` reports `invalid_source`, which is not retryable
      (packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py:245-249). A C5 code fix
      does not clear the block unless it changes the retained basis. Otherwise the quarter
      recovers only when its source set or base changes. Removing the candidate's objects is not
      a supported recovery step: parent spec §4.7 forbids deleting objects to reset state, no
      command does it, and such a removal needs a separately reviewed operational decision. Each
      blocked retry costs one full check, about 415 s for a full-size quarter
      (specs/evidence/stage1b/diagnosis.md §1). Tested: in
      packages/sec-edgar-ingest/tests/test_etl_incremental.py,
      `PrePointerRefusalTests.test_a_wrong_incremental_row_is_refused_before_the_pointer` shows
      that a retry also raises and the pointer does not move. Documented in
      specs/completed/sec-filing-index-per-member-cost.md §4.3 item 5, the parent spec
      (specs/completed/sec-filing-index-ingestion-spec.md) §4.6 and docs/runbooks/local-recovery.md (row
      "Refused incremental candidate"). The code fix is larger: run C6 on the local Parquet files
      before anything is staged or stored, so a refused candidate leaves no object. That changes
      C6's input and the incremental stage order, and it needs the full gate, a release build and
      a config selection. Size: design. Done when: the owner approves running C6 on the local
      Parquet files before anything is staged and it lands, or records a reviewed operator
      procedure for removing a refused candidate's objects.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] History-scan cost (spec decision S4, "Measure, defer fix"; plan 5 Task 12, see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md): per-member engine
      time grows with the `WorkflowChildCall` rows that the engine scans (`_obligations`,
      `reuse_exact_binding`). specs/evidence/stage1b/measurement.md, "History scan (S4)", fits
      engine seconds (member wall minus its children) against those rows at member start. Slopes
      in seconds per `WorkflowChildCall` row: `open` 0.0253, `closed` 0.0290, `authority` 0.0236,
      `finish` 0.0218 (measurement.json `measures.history`). Projections: 10.0 to 13.0 s per member
      at 400 child calls, and 28.3 to 36.2 s per member at 1,200. The most rows that a member saw
      was 241 (`open`), so both projections extend the fit. The live store's child-call count is
      not measured. Figures for the check: reserve 1,800 s; reserve rule 1.25 × 1,010.9 s + 480 s
      = 1,743.6 s; fit-gate room 489 s at a fixed reserve. The fit uses only `WorkflowChildCall`
      rows, but specs/completed/sec-filing-index-per-member-cost.md §6 (the "History growth" row)
      also names `Attempt` rows. The script keys each member's child times by command
      (scripts/measure-d5-drain.py :254-255), so a repeated child command would hide seconds. A
      read-only check of the four reports in fixture-data/s1b-measure-20261028T110945Z/ found no
      repeated child command, so the slopes are not affected. Deferred by S4: this stage measures
      the cost and does not fix it. Size: plan. Revisit if: a live run's per-member engine time
      grows past the measured slope, or the projection at the live store's child-call count
      exceeds the reserve's margin.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Unmeasured member class: an open-quarter member with a quarterly membership authority (the
      A1 locality exception; plan 5, specs/plans/completed/5-sec-filing-index-per-member-cost.md,
      "Defaults for owner review", A1). The §6 `open` scenario has no authority, and the
      `authority` scenario runs in a closed quarter (2026Q3), so
      specs/evidence/stage1b/measurement.md has no timing for this path. The whole-branch review
      found that this path read the whole authority as Python rows for each member. Commit
      fe6bca0 changed C5 and C6 to Arrow key filters (`columnar.quarter_key_column`; in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/, incremental.py:123-132 and
      equivalence.py:44-49). In a fixture spy test, authority rows read as Python fell from 40 to
      0 in C5 and from 41 to 1 in C6. The reviewer named this member class the common live case
      for roadmap Stages 3 and 5. Deferred: the owner approved the measurement as run, with floor
      480 s and reserve 1800 s (plan 5 Decision D10, 2026-10-28). Size: plan. Revisit if: a live
      open-quarter member with a quarterly authority has a member wall above the slowest measured
      wall (1,010.9 s), or a later stage needs this class in its reserve.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Full-check accounting and engine-path test gaps (plan 5 Task 3 and Task 4 reviews; see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md). Code and test paths below are
      under packages/sec-edgar-ingest/:
      (1) Lost `put_once` race: in src/sec_edgar_ingest/etl/catalog.py, `_store_manifest`
      (:92-97) catches `Conflict`
      and calls `_existing`, which runs the full check. `build_candidate` then runs
      `validate_candidate_content` again (:345). So one full-rebuild candidate gets two full
      checks, against the C3 row of specs/completed/sec-filing-index-per-member-cost.md ("fully
      checked once per build, not twice"). On the incremental path the same branch gives a full
      check and then C6. No test covers the race. (2) `EngineBudgetTests` in
      tests/test_full_check_budget.py (:27-60) runs only `backfill`. `daily`, `reconcile`, the
      repair-resolution paths and `source_revert_gaps` are covered only by reading the code.
      (3) Per the Task 3 review (not re-run at HEAD),
      `test_a_changed_generation_byte_is_a_conflict_on_engine_paths` (:46-60) also passed before
      the switch to C1, so it guards the behaviour but does not prove the switch. (4) No
      engine-caller test drives a changed observation rows-file byte through `validate_capture`,
      `evaluate_member` or `checked._transformed_input` (a grep of the tests at HEAD found none).
      The C11 wiring rests on the zero readback count in the budget test.
      Deferred: tests and `src` are frozen at the 1b release build. Item (1) changes `src` if the
      second check is removed. Size: plan. Done when: the race path is tested and either skips the
      second full check or the C3 row states two checks, the budget test covers `daily` and
      `reconcile`, an engine-caller C11 test exists, and the full gate is green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Test gaps in the columnar, equivalence, incremental and integrity tests (plan 5 Task 2, 5, 6
      and 7 reviews; see specs/plans/completed/5-sec-filing-index-per-member-cost.md), in
      packages/sec-edgar-ingest/tests/:
      test_etl_integrity.py: no test for a missing rows file in `checked_observation` (expect
      `FileNotFoundError`), and none for the identity-mismatch `ValueError` ("candidate differs
      from exact manifest/gate identity") in `check_candidate_integrity`
      (packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py:384-394).
      The "reads no rows" proofs patch named readers (`iter_file_rows`, `_verify_parquet`,
      `_validate_row_origins`), so a new reader would escape them.
      test_etl_columnar.py: three cheap tests. `key_mask` keeps `('1a','b')` apart from
      `('1','ab')`. `replace(ref, source_row_count=4, quarter_counts={'2026Q4':3,'2026Q3':1})`
      raises `ValueError` "observation readback counts differ". `generation_table(replace(data,
      role='changes'))` raises `ValueError` "generation Parquet schema differs". The reviewer
      argued that real data cannot collide, because a valid CIK has a fixed 10 characters (not
      re-checked).
      test_etl_equivalence.py:136-141: `test_refuses_a_duplicated_touched_row` does not assert
      that the duplicated row is the touched key (archive path ending `000003.txt`), as its name
      says.
      test_etl_incremental.py: `FallbackTests` (:130-160) has no case for a changed parser or
      schema version (C4 branch at
      packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/incremental.py:42-43; the re-transform
      in `build_candidate` also covers it). The oracle tests lack: a row count that is an exact
      multiple of 8,192 (`BATCH_ROWS`), a null `accession_number`, mixed-case or non-ASCII keys
      (Arrow byte order against SQLite BINARY, equal by inspection only), a `_best` tie on
      `source_id`, and an empty delta for the quarter.
      Deferred: tests are frozen with the 1b release build. Size: quick-fix. Done when: these
      tests land, each fails when its guard is removed by hand, and the full gate is green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Small cleanups in the frozen ETL code (plan 5 Task 2, 5 and 6 reviews; see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md), in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/:
      manifest.py:384-394: `check_candidate_integrity` repeats the identity and gate-record logic
      of `validate_candidate_content` (:367-375) and `validate_candidate` (:378-381). The plan gave
      that code verbatim. Extract one private helper.
      reader.py `_pinned_manifest`: the `check` parameter has no `Callable` annotation.
      columnar.py:56: `key_mask` sorts its value set. The sort is not needed.
      equivalence.py:101 assigns a lambda (`outside`). equivalence.py:28-32 `_change_payload`
      changes the dict that it is given.
      equivalence.py:74-78: C6 compares the candidate manifest with its base on gate, mode,
      membership authority, parser and schema. It never compares them with `context`. C4
      (`incremental.eligible`, incremental.py:36-47) does. A context check in C6 is defence in
      depth only.
      Deferred: `src` is frozen. Cost: full gate, release build, config selection, so do this
      with the next plan that builds a release. Size: quick-fix. Done when: the cleanups land in a
      release-building plan with the full gate green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Hardening of scripts/measure-d5-drain.py (plan 5 Task 9 review and implementer notes,
      triaged "may wait"; see specs/plans/completed/5-sec-filing-index-per-member-cost.md):
      (1) `history_fit` (:497-505) fits only `WorkflowChildCall` rows, and `history_counts`
      (:393-409) counts the whole `Attempts` table. specs/completed/sec-filing-index-per-member-cost.md
      §6 (the "History growth" row) names `Attempt` rows as a fit input. Align the spec or the
      fit. (2) `run_scenario` (:446-484) writes `WALLS` and `TIMINGS` into a failed report, but
      drops the member in progress (`OPEN_MEMBER`, :51). Per the Task 9 review, SIGTERM or SIGHUP
      can end the process without the `finally`, so no report is written. Not re-checked: while a
      child runs, `runtime.run_child` installs its own SIGTERM handler
      (packages/sec-edgar-ingest/src/sec_edgar_ingest/runtime.py:625-628), so the gap may apply
      only outside child runs. (3) `scenario` (:254-255) keys each member's children by command,
      so a repeated child command keeps only its last time and overstates engine time in
      `history_fit`. The 2026-10-28 reports have no repeats. (4) The step lists repeat in `run`
      (:334-349), `run_finish` (:352-354) and the `run_scenario` plans (:458-472). (5) `invoke`
      (:220-234) takes `splitlines()[-1]` of stdout, so an engine that refuses before it prints a
      result raises a bare `IndexError`. Deferred: the measurement record
      (specs/evidence/stage1b/measurement.md) was made with this script as it stands.
      Size: quick-fix. Done when: one pass lands with tests in
      packages/sec-edgar-ingest/tests/test_measure_cost.py and that module is green.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] Release-test assertions and documentation wording (plan 5 Task 1, 8, 11 and 14 notes; see
      specs/plans/completed/5-sec-filing-index-per-member-cost.md): (1)
      packages/sec-edgar-ingest/tests/test_release_1b.py
      `test_d5_runs_again_on_a_store_that_1b_wrote` (:28-39) asserts only exit 0 and an outcome of
      `success` or `unchanged`. The evidence also reports 0 jobs, no gaps and 2 `already_complete`
      entries (watcher only). The test could assert no gaps and no jobs. Its docstring argues a
      claim instead of saying what the test does. (2) specs/evidence/stage1b/two-release.md:5:
      "covers that half … does not test that half" reads oddly; add "(see Results item 2)". Lines
      :48 and :61 say that run 2's `d5-again` files were not captured. The Task 8 re-review says a
      partial tree exists (intent, discover call, exit, config, launch, discover result) without
      `selection.json` or the backfill `result.json` (not re-verified at HEAD). Suggested: "run 2's
      `d5-again` selection and result were not captured". (3) specs/evidence/stage1b/release.md:19
      "No platform package" rests on dependency names only. :36 "not durable" wording could be
      clearer. (4) specs/completed/sec-filing-index-per-member-cost.md: §5 items 1 and 3 each
      have one line of 127 and 133 columns against a wrap near 105, and the first §2 bullet has a
      doubled "and". (5) The §4.1 table of that spec has no row for
      packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py (shared constants and
      `arrow_row`, changed by plan 5) or packages/sec-edgar-ingest/src/sec_edgar_ingest/runtime.py
      (the EPERM fix, 17d78da). (6) The C4 row in section 3 of the same spec says "no incoming source
      is the quarter's quarterly membership authority". `incremental.eligible`
      (packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/incremental.py:36-47) also requires the
      membership authority to equal the active generation's and every active source to stay
      selected. The behaviour is the same in practice; align the row with the code.
      Deferred: the test file is frozen with the release build. The text items were triaged "may
      wait". Size: quick-fix. Done when: one wording and assertion pass lands and the full gate is
      green for the test change.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, with the test file of part (1). Parts (2)–(6) edit the parked engine's evidence and retired specs, which stay unchanged as the record.
- [x] Two-release proof covers only first-generation 1b stores (plan 5 Task 8; on 2026-10-28 the
      owner chose to narrow the evidence wording and add no new scenario, Decision D3 in
      specs/plans/completed/5-sec-filing-index-per-member-cost.md).
      In all six runs of packages/sec-edgar-ingest/tests/test_release_1b.py, each 1b generation
      was a full rebuild with `base_generation_id` null and one source. The D5 rerun dispatched
      only its `discover` child. So no test shows D5 reading an incremental 1b generation, and no
      test shows a D5 publish built on a 1b generation. The first rests on byte identity
      (specs/completed/sec-filing-index-per-member-cost.md §5 item 3). The limits are recorded in
      parent spec §4.9 and in specs/evidence/stage1b/two-release.md, "Limits of the proof". A
      stronger scenario needs new fixture design: 1b publishes an incremental generation, then D5
      runs and publishes on top. Related: the plan 4 item "Order-aware two-release proofs".
      Stage 1c (plan 6): the live store now holds such generations: eight incremental 1b
      generations on `fc68adef…` bases, from invocation 1. The Stage 1c diagnosis compared their
      data rows with a full rebuild and found them equal. Change rows were not compared
      (specs/evidence/stage1c/diagnosis/diagnosis.md). The item stays open.
      Size: plan. Revisit if: the D5 release must run again on a store that holds an incremental
      1b generation, or a later stage plans to select D5 after a live 1b run.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.

## 6-sec-filing-index-member-completion — 2026-10-30
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [x] The completion conflict names no cause when the evaluation has no gap (plan 6 Task 3, from
      the whole-branch review; the owner was told at the Task 4 checkpoint. See
      specs/plans/completed/6-sec-filing-index-member-completion.md). In
      packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/processing.py, the completion
      check after a finished child raises `child completion lacks all affected quarter/repair
      evidence` with no suffix when the evaluation has no gap, for example when it holds only
      repair obligations (spec M3 requires the stock text alone in that case). An operator then
      cannot see which obligation is open. Deferred: spec M3 fixes the text, and the 1c release is
      already built from this source. To do: decide a text that names the open obligations, add a
      test beside `test_member_completion.ProcessMemberTests`, and ship it in the next release.
      Size: quick-fix. Revisit if: an acceptance or campaign run ends with this stock conflict and
      the cause is not visible from the gaps or the obligation rows.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.

## 2-sec-filing-index-ingestion-spec — 2026-10-31
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [x] Parser/schema design for `conflicting duplicate logical key` (plan 2 Tasks 5 and 7, owner
      ruled defer). All 28 quarterly sources 2020Q1–2026Q4 and 7 daily sources quarantine on it.
      The raw enumeration shows one accession carrying several form types (SC 13E3 with SC TO-T).
      See specs/plans/completed/2-sec-filing-index-ingestion-spec.md; evidence in
      specs/evidence/baseline-campaign/quarantine/ and final/coverage.json; findings §5. Size:
      design. Done when: the owner approves a versioned parser/schema design for such rows, and a
      later campaign covers or re-quarantines the 28 units and 7 daily sources.
      → planned 2026-10-31: specs/plans/7-sec-filing-index-duplicate-key.md
      → planned 2026-11-05: specs/plans/8-sec-filing-index-ingestion-spec.md
      → retired 2026-11-19: plan 7 shipped the approved `sec-index-v2` design (its spec reads COMPLETE 2026-11-02), and plan 12 removed the parked engine from `main`. The campaign half of this item is the parked Stage 2b item → item: sec-filing-index-ingestion-roadmap — 2026-11-16
- [x] The `daily-index/index.json` listing is refused with `permit_expired`, and daily 2026-10-27
      ended `incomplete` for the same cause (plan 2 invocations 1, 2 and 4; owner accepted a named
      gap). The cause is not diagnosed. See specs/evidence/baseline-campaign/coverage-finding.md
      §4.2–4.3. Size: plan. Revisit if: Stage 3 discovery meets the refusal again, or a run lists
      daily bodies after 2026-10-30.
      → triggered 2026-11-19: the Stage 2b runs met the same refusal (`specs/evidence/stage2b/startup-overhead.md:35`) and listed the daily bodies of 2026-11-02 to 2026-11-05 (`:53`)
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] 14 non-retryable `legacy_member_unresolved` gaps, "source has no verified original parent"
      (plan 2 invocation 4, owner accepted a named gap). Cause not investigated; they stopped
      nothing. See specs/evidence/baseline-campaign/coverage-finding.md §4.3. Size: plan. Revisit
      if: a run stops on one of these gaps, or Stage 3 selects those sources.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.
- [x] The engine retains quarantined members, so any run whose pinned end lies before a retained
      member's period ends `state_conflict` (plan 2 invocation 3; F9 was wrong). See
      packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py `select_work` and
      worksets.py `_validate_source_directory`. Size: design. Revisit if: Stage 3 or Stage 5 needs
      a bounded-end command on a store that holds quarantined members.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.

## 9-sec-filing-index-pre-dispatch-cost — 2026-11-15
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [x] Registered-member accumulation (spec §2.2 of `specs/completed/sec-filing-index-pre-dispatch-cost.md`;
      plan 9 Handoff, owner ruled defer to Stage 5): registered members never retire. They grow by about 55 for each
      business day with a new listing, which is about 13,750 members in a year of daily runs. On the 2a1 release each
      registered member costs about 0.5 s in each run before the first dispatch (measured at 155 to 208 members: 38.1 s
      before discovery, 39.4 s after it and 10.2 s in the freeze phase). That is enough for Stage 2b (bounded at
      281.2 s for 450 registered members), but 13,750 members would cost about 6,900 s, above the 1,476 s cutoff. See
      `specs/evidence/stage2a1/predispatch.md`; touches `workflows/runner.py` (`select_work`) and
      `workflows/members.py`. Size: design. Done when: Stage 5's design retires old registered members or stops
      evaluating them, and an offline measurement at the resulting member count shows the first dispatch before the
      cutoff.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`. The parked Stage 5 item restates this requirement → item: sec-filing-index-ingestion-roadmap — 2026-11-16
- [x] Path guards of the Stage 2a1 evidence scripts (plan 9 Task 6 and Task 7 reviews, owner ruled defer):
      `specs/evidence/stage2a1/predispatch/replay.py` and `specs/evidence/stage2a1/walls/member-walls.py` refuse a path
      under `data/` or `backups/` by directory identity (`os.path.samefile`). They do not refuse a scratch file that is
      hard-linked to a live file in `data/`, and `walls` and `starts` do not refuse an output or scratch path under
      `releases/`. The plans' clone commands (`cp -c -R`) and the rule that scratch folders live under `logs/` avoid
      both cases. Size: quick-fix. Revisit if: a later plan names `replay.py` or `member-walls.py` in a step.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`. `specs/evidence/stage2a1/predispatch/replay.py:38` imports `sec_edgar_ingest`, so neither script runs on `main`.
- [x] Test-gap Minors from plan 9 (Task 1 and Task 5 reviews, owner ruled defer): (1) no test that
      `record_type_hints` does not cache a raised decode error (`functools.cache` stores no exception, and the
      `SelectionChecks` tests cover the rule for the new kept values); (2) `tests/test_release_2a1.py` omits the check
      at the end of `test_release_2a` that the published pending manifest has `schema_version` `sec-index-v2`; (3) in
      its pending scenario a hash-ordered member sort can leave no cross-release child (the repair case always runs
      one). Touches `packages/sec-edgar-ingest/tests/test_pre_dispatch_cost.py` and `test_release_2a1.py`.
      Size: quick-fix. Done when: each gap has a test, or the owner drops it with a reason.
      → retired 2026-11-19: plan 12 removed the parked engine from `main`, and no live roadmap stage uses it. Its last state is at tag `ingest-parked-2026-11-16`.

## sec-filing-index-ingestion-roadmap — 2026-11-16
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [ ] Stage 2b, baseline coverage on the 2a1 release (parked roadmap `specs/completed/sec-filing-index-ingestion-roadmap.md`,
      Stage 2b entry; parked at the roadmap reset, 2026-11-16): a revised G2 finding for the 28 quarterly units
      2020Q1–2026Q4 and the 7 daily duplicate-key sources, on release `f414caf8…`. It is blocked. The 2026-11-15 folder
      rename blocks every registered member, because each stored config names the old storage root
      (`workflows/checked.py:414–415`; `specs/evidence/stage2b/planning/rename-check.md` on branch
      `claude/sec-filing-index-stage-2b-0111b6`). Repair routes, none tested: (A) move the folder back and undo the
      rename's rewrites of the config, `binding.json` and the release launch files; (B) a link from the old path, which
      fails alone at the console-script check, with the old paths put back in the four origin releases (not analyzed);
      (C) compare bindings by store identity and look up releases from the current folder (under the current code, no
      proof on a cloned store passes). The owner chose (D) on 2026-11-16: leave the store parked. Plan 8's Handoff
      (`specs/plans/completed/8-sec-filing-index-ingestion-spec.md`) and plan 9's Handoff hold the inputs.
      Size: design. Done when: the owner accepts a revised G2 finding that accounts for each of the 28 quarterly units
      and the 7 daily duplicate-key sources by validated publication or by a named gap with an owner disposition.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 3, daily catch-up acceptance (parked roadmap, Stage 3 entry, G3): accepted manual daily continuation from
      the handoff to the current date over the retained pending inventory. It needs the Stage 2b finding. The `daily`
      command shares the cost before the first dispatch (plan 9, Handoff, "Stages 3, 4 and 5" bullet). Size: plan.
      Done when: a dated catch-up report accounts for the daily discovery and pending units from the handoff to the
      current date, and the owner accepts its coverage and limits.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 4, manual reconciliation acceptance (parked roadmap, Stage 4 entry, G4): accepted operational
      reconciliation with change, gate, revert, quarantine and recovery dispositions. It needs the Stage 2b finding and
      a quarterly authority to compare with. Plan 8 F3 predicted a 2026Q3 withdrawal gate of about 47 keys, which waits
      here. Size: plan. Done when: a reconciliation report gives each unresolved candidate and gap an explicit
      disposition, and each approval names its exact authority.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 5, local scheduling and observed-operation acceptance (parked roadmap, Stage 5 entry, R13, G5): a reviewed
      scheduler for unattended runs, with enable and disable records and observed scheduled runs. Its design retires
      old registered members or stops evaluating them (item "Registered-member accumulation", section
      `9-sec-filing-index-pre-dispatch-cost — 2026-11-15`). Size: design. Done when: R13 has scheduler-specific
      verification, and accepted scheduled daily and reconciliation runs link to durable results.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)

## sec-filing-platform-roadmap — 2026-11-16
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
- [ ] Stage 1, platform package and envelope parser (parked roadmap `specs/completed/sec-filing-platform-roadmap.md`,
      Stage 1 entry; plan 3, `specs/plans/completed/3-sec-filing-platform-stage-1.md`): the work ran to the end on
      branch `platform-stage1` (`12cb8e0`, 13 commits, package `sec-edgar-filings`, 60 fixture tests). The owner retired
      plan 3 unmerged at the roadmap reset (2026-11-16), and the new roadmap does not consume it. Merge gate items 2–4
      of plan 3 were never met. Size: plan. Done when: the `sec-edgar-filings` package is on `main` with its
      import-direction test and a recorded ingest export diff, or the owner drops the branch.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 2, XBRL fact extraction over fixtures (parked roadmap, Stage 2 entry; platform spec
      `specs/completed/sec-filing-platform.md` R18–R20, V13): a draft extractor with inline XBRL document sets, R18 fact
      keys, R19 duplicate classes and the cover record. Stage 1 of `specs/sec-filing-data-roadmap.md` parses as-filed
      facts on real filings without this design. Size: plan. Done when: each V13 case passes as a fixture test.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 3, ownership records over fixtures (parked roadmap, Stage 3 entry; platform spec R22–R24, V15): typed
      ownership records with the R23 13F rules and the R24 amendment row set. Size: plan. Done when: each V15 case
      passes as a fixture test.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 4, platform catalog release (parked roadmap, Stage 4 entry; platform spec R4–R7; ADR 0001): a release of
      the shared governor with a bulk lane, three priorities, a protocol version, platform URL classes and
      multi-application build and verify, plus ADR 0002 on shared code. Size: design. Done when: the owner approves the
      governor change and the release, and ADR 0002 is Accepted.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 5, governed retrieval and retention (parked roadmap, Stage 5 entry; platform spec R3 rules 1, 2 and 5,
      R5–R7, R26): governed fetch and retention of Feed archives, complete submission files and `submissions.zip`.
      Size: plan. Done when: offline tests show members mapped by header accession, snapshot records with their
      encoding and decoded-byte hashes, and oversize routing to the bulk lane, and the owner reviews the release.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [x] Stage 6, evidence campaign and finding (parked roadmap, Stage 6 entry; platform spec V1–V12, R30): a bounded live
      campaign that retains a real-submission sample and gives a result for each of V1–V12. Size: plan. Done when:
      each of V1–V12 has a recorded result or a named open item with an owner disposition, and the sample manifest is
      committed.
      → planned 2026-11-17: specs/plans/10-sec-filing-data-stage-1.md
      → done 2026-11-17 (plan 10): V1–V12 each have a result or an owner disposition, and the sample manifest is committed, in specs/sec-filing-data-stage-1-findings.md. The open parts carry on → item: 10-sec-filing-data-stage-1 — 2026-11-17
- [ ] Stage 7, parser freeze (parked roadmap, Stage 7 entry; platform spec R14–R16, R18–R20, R22–R24): revise the
      envelope, fact and ownership parsers against the retained sample and freeze their versions. Size: plan.
      Done when: each frozen version parses the whole sample, with a recorded reason for each refusal.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 8, point-in-time store and views (parked roadmap, Stage 8 entry; platform spec R9–R13, R26, R28, V14):
      per-quarter platform generations with four times, tombstones and both view clocks. Stages 2–4 of
      `specs/sec-filing-data-roadmap.md` cover point-in-time awareness for that roadmap's sample. Size: plan.
      Done when: each V14 sequence passes, and a generation publishes by conditional replace in a fixture store.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 9, entity history and events (parked roadmap, Stage 9 entry; platform spec R17, R25): ticker and name
      histories from as-filed sources, and 8-K item events. Size: plan. Done when: tests show ticker observations from
      both R17 sources, an item crosswalk with effective date ranges, and one event row per item.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 10, publication quality gates (parked roadmap, Stage 10 entry; platform spec R21, R27, V16): fact accuracy
      against SEC reference data, and a review policy for level-B fields. Size: design. Done when: a version of the
      fact extractor meets the V16 conditions, or is recorded as not fit with its residuals.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 11, run composition and accounting (parked roadmap, Stage 11 entry; platform spec R2, R3 rules 3, 4 and 6,
      R29, R31): backfill, daily, audit and replay runs with coverage accounting per quarter. Size: plan. Done when:
      fixture runs show selection from the pinned catalog only, a recorded gap for each unlisted Feed member, and a
      reported audit detection bound.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 12, storage gate and first backfill (parked roadmap, Stage 12 entry; platform spec R30, V17): the owner's
      storage budget and the first platform backfill over catalog-accepted quarters, at about 1.0–1.9 TB per quarter
      uncompressed. Size: plan. Done when: the measured volume and the owner's budget are recorded before the first
      backfill request, and each requested quarter is covered or named as a gap.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)
- [ ] Stage 13, daily continuation acceptance (parked roadmap, Stage 13 entry; platform spec R29, R31): accepted daily
      platform runs after the catalog's daily run. Size: plan. Done when: daily runs take each evening's Feed archive
      after the catalog's daily run, and the audit's detection bound is recorded.
      → held 2026-11-19: `specs/sec-filing-data-roadmap.md` retires to `specs/completed/` after its completion review (derive-roadmap §6)

## 10-sec-filing-data-stage-1 — 2026-11-17
- [ ] Feed archive checks V1, V2 and the `.corrNN` part of V6 (plan 10, findings `specs/sec-filing-data-stage-1-findings.md`,
      Platform checks; parked platform spec `specs/completed/sec-filing-platform.md`, Verification): reconcile Feed archive
      members with complete submission files, test range requests on a Feed archive, and read what a `.corrNN` member
      means. Stage 1 fetched complete submission files only, and the sec-filing-data roadmap fetches no Feed archive. The
      owner chose to defer (2026-11-17, "Accept all (Recommended)"). Size: plan. Revisit if: a roadmap stage or a plan
      adds a fetch of EDGAR Feed archives.
- [ ] Submissions metadata check V4 (plan 10 findings, Platform checks; parked platform spec V4): one `submissions.zip`
      snapshot shows the `items` format and the precision of old acceptance times. It is SEC reference data, which the
      sec-filing-data roadmap leaves out. The owner chose to defer (2026-11-17). Size: plan. Revisit if: a roadmap stage
      adds checks against SEC reference data.
- [ ] Other-quarter parts of V5 and V7 (plan 10 findings, Platform checks; parked platform spec V5, V7): the headers of
      the three 2024Q1 key pairs with two form types (V5), and the acceptance lines and complete submission files of the
      101 `PRIVATE-TO-PUBLIC` submissions of 2026-10-15 (V7). Stage 1's sample is 2026Q3 only, and the roadmap leaves
      out other quarters. The owner chose to defer (2026-11-17). Size: plan. Revisit if: a roadmap stage covers a
      quarter other than 2026Q3.
- [x] Refetch for V6 (plan 10 findings, Platform checks, V6 line): refetch `9999999995-26-002992` (form `EFFECT`, filed
      `20260917`, `DATE AS OF CHANGE` `20260918`) and compare its SHA-256 with the Stage 1 copy under
      `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3/bytes/`, to show whether the archive copy changes after a
      correction. 1 SEC request, which needs the owner's budget for that stage. The owner carried it into Stage 2 of
      `specs/sec-filing-data-roadmap.md` (2026-11-17). Size: quick-fix. Done when: a Stage 2 record gives the refetch's
      SHA-256 beside the Stage 1 SHA-256.
      → planned 2026-11-17: specs/plans/11-sec-filing-data-stage-2-provenance-and-timing.md
      → done 2026-11-18 (plan 11): the refetch SHA-256 equals the Stage 1 SHA-256 (`specs/sec-filing-data-stage-2-findings.md`, V6 refetch). Both copies were taken after the correction, so it cannot show whether a copy changes after a correction → item: 11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18
- [x] SEC documentation checks for V7 and V8 (plan 10 findings, Platform checks; parked platform spec V7, V8): what the
      `<PRIVATE-TO-PUBLIC>` tag means, and whether a late acceptance is disseminated that evening or the next business
      day. Stage 2 of `specs/sec-filing-data-roadmap.md` decides when each filing became public and needs both answers.
      The owner carried them into Stage 2 (2026-11-17). Size: design. Done when: Stage 2's spec or findings cite the SEC
      documentation for both answers.
      → planned 2026-11-17: specs/plans/11-sec-filing-data-stage-2-provenance-and-timing.md
      → done 2026-11-18 (plan 11): the spec and the findings cite the SEC documentation for both answers (`specs/sec-filing-data-stage-2-findings.md`, SEC documentation)
- [ ] XBRL guide checks V11 and V12 (plan 10 findings, Platform checks; parked platform spec V11, V12, R18–R20): the
      EDGAR Filer Manual's exhibit and Transformation Registry tables, and the EDGAR XBRL Guide's per-class and
      legal-entity axis conventions. They matter only to an inline XBRL parser, which plan 10's D2 leaves out (Stage 1
      reads the SEC-extracted instance). The owner chose to defer them with the parked platform Stage 2 item, section
      `sec-filing-platform-roadmap — 2026-11-16` (2026-11-17). Size: design. Revisit if: a plan builds an inline XBRL
      parser.

## tech-debt-triage — 2026-11-18
- [x] Remove the parked `sec-edgar-ingest` engine from `main` (tech-debt triage 2026-11-18, row 4): tag the last commit
      that holds it (for example `ingest-parked-2026-11-16`), then remove `packages/sec-edgar-ingest/`, `scripts/` other
      than `check-sec-filing-data.sh`, `conf/`, `docs/runbooks/` and `.sdd/`, and repoint the old-engine items in this
      file at the tag. Keep all of `specs/`, and keep the root `constraint-dependencies` (it pins PyArrow 25.0.1 and
      Requests 2.34.2 for `sec-filing-data` too). Do not touch `data/` or `backups/` in the main checkout. Before `conf/`
      goes, give `SEC_USER_AGENT` another documented source, because plans 10 and 11 read it from
      `conf/sec-edgar.json`. Later plans read the input from `filing-data/inputs/2026Q3/master.zip`, a byte-equal copy
      made on 2026-11-18, not from the parked store. No current output depends on the engine. The owner chose to label
      it parked now and remove it after Stage 2 (2026-11-18, "Label now, delete after Stage 2 (Recommended)"). Size:
      plan. Done when: `main` holds no `sec-edgar-ingest` code, a tag marks the last commit that held it, and
      `scripts/check-sec-filing-data.sh` passes.
      → planned 2026-11-18: specs/plans/12-remove-parked-sec-edgar-ingest.md
      → done 2026-11-18 (plan 12): the engine, `conf/`, its scripts, `docs/runbooks/` and `.sdd/` are removed from `main`, and tag `ingest-parked-2026-11-16` holds their last state

## 11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18
- [ ] Whether an EDGAR archive copy changes after a correction (spec `specs/completed/sec-filing-data-stage-2-provenance-and-timing.md`,
      section 11, owner decision D6): the V6 refetch compared two copies of `9999999995-26-002992` that were both taken
      after its `DATE AS OF CHANGE`, so equal hashes show only that the copy did not change between 2026-11-17 and
      2026-11-18. The question needs one copy fetched before a correction and another after it. Findings:
      `specs/sec-filing-data-stage-2-findings.md`, V6 refetch. Size: plan. Revisit if: a roadmap stage fetches filings
      on the day they are filed.
- [x] Re-hash the kept files in `refetches` (plan 11 final review, Codex review; `src/sec_filing_data/refetches.py`):
      `sha256_equal` takes both SHA-256 values from the ledgers and never hashes the stored files again, as plan C8
      says. An edit to a kept file after its `ok` record would not show. Stage 3's manifests are meant to cover byte
      integrity. Size: quick-fix. Revisit if: Stage 3's manifest check does not list the files under `ROOT/stage2/refetch/`.
      → planned 2026-11-19: specs/plans/13-sec-filing-data-stage-3-manifests-and-pinning.md
      → done 2026-11-19 (plan 13): `verify` part 1 hashes every file under `stage2/refetch/` again, and part 2 ties each `refetches` row's `refetch_sha256` to `stage2/refetch/<accession>.txt` by path. On the live root both gave `ok` (`specs/sec-filing-data-stage-3-findings.md`, Verify)
- [ ] Command robustness on an old or busy root (plan 11 final review; `src/sec_filing_data/report.py`, `cli.py`, `rebuild.py`):
      `report` raises a `KeyError` on a `filings` table that has no Stage 2 columns. A refused `refetch` of an unknown
      accession still writes one `runs.jsonl` line. `refetch` exits 0 after a 404 or a failed fetch, and prints the
      outcome. `rebuild` and `check-stage1` take no `fetch.lock`, so a running fetch could change the root under them.
      Size: quick-fix. Revisit if: a roadmap stage builds a second root, or runs a quarter other than 2026Q3.
- [ ] Input hardening for other data (plan 11 final review; `src/sec_filing_data/times.py`, `refetches.py`, `fetch.py`):
      `accepted_at` raises an `OverflowError` for an acceptance in the year 9999. A User-Agent that `requests` rejects
      after the request record is written spends the one refetch of that accession. `compare-refetches` raises a
      `FileNotFoundError` when the SHA-256 values differ and a Stage 1 byte file is missing. No sampled filing or live
      value meets any of these. Size: quick-fix. Revisit if: a roadmap stage reads a quarter other than 2026Q3.

## 13-sec-filing-data-stage-3-manifests-and-pinning — 2026-11-19
- [ ] Bad-input errors end in a traceback (plan 13 task reviews and final review; `src/sec_filing_data/cli.py`, `manifest.py`,
      `verify.py`, `rebuild.py`): a corrupt `.parquet` file in a set folder, a `--zip` that names a folder, a missing `sample`
      table for `build-fetches`, and a manifest nested deep enough to raise `RecursionError` each end a command in a traceback
      and not in one `error:` line. `verify` with a relative `--out` fails the `fetches` path check of part 2 (plan C10) and
      shows it only as a failed binding line. No live value meets any of these. Size: quick-fix. Revisit if: a roadmap stage
      runs a quarter other than 2026Q3.
- [ ] Python-level writes are not guarded by the clean-tree rule (plan 13 final review; `src/sec_filing_data/tables.py`,
      `version.py`): `write_table` stamps the commit at `HEAD` when a Python caller writes a table outside a command, even when
      the pinned paths have a change. Spec 5.1 puts the rule on the commands, and no command writes without it. Size: quick-fix.
      Revisit if: a roadmap stage adds a code path that writes a table without a command.
- [x] Small cleanups and test gaps in Stage 3 (plan 13 task reviews; `src/sec_filing_data/fetch.py`, `verify.py`, `cli.py`):
      `fetch.py` writes `fetches` through `write_table(layout, "fetches", build_fetches(layout))` and not through
      `ledger.run_fetches`, so two call sites write one table. No test counts the reads of a listed file in part 3, so a version
      that hashes one read and parses a second read passes. `verify --rows 0` gives `ok, 0 rows`, and a negative `--rows` gives a
      failed line for each table, with no usage error. Size: quick-fix. Done when: `fetch.py` calls `run_fetches`, a test counts
      the reads of one listed file in part 3 and fails for a version that reads it twice, and `--rows` below 1 gives a usage
      error (exit 2).
      → done 2026-11-19 (/deferred quick fix): `fetch.py` writes `fetches` through `ledger.run_fetches`, `test_rederive_reads_each_listed_file_once` counts the reads of one listed file in part 3 and fails for a version that reads it twice, and `verify --rows` below 1 is a usage error (exit 2)

## 14-sec-filing-data-stage-4-as-of-views — 2026-11-19
- [ ] A hard kill of `fetch-partners` blocks the next run (plan 14 final review, owner decision D3; `src/sec_filing_data/fetch.py`,
      `ledger.py`, `manifest.py`): a kill during a request leaves `stage4/bytes/<accession>.txt.part` and a request record
      with no answer in `stage4/fetch-log.jsonl`. `ledger_usage` counts an unanswered request as `MAX_RESPONSE_BYTES`
      (268,435,456 bytes), which is above the 50,000,000-byte budget. So the next `fetch-partners` exits 5 before `_walk`
      can remove the `.part`, and a later `manifest --set stage4` lists the `.part` as a `submission` input. Plan Review
      Focus 3 (the next run removes the `.part`) holds only after the owner raises the budget. Spec section 3 stops the run
      for the owner at exit 5, and the live run had no kill. The fix would remove a leftover `.part` under the lock before
      the budget check. Size: quick-fix. Revisit if: a `.part` file appears under `ROOT/stage4/bytes/`.
- [ ] `asof` refuses when a commit lands between the table steps and the stage4 manifest (plan 14 final review, owner
      decision D3; `src/sec_filing_data/manifest.py`, `asof.py`): `write_manifest` names `stage4@<commit12>.json` by the
      commit at `HEAD`, and `find_manifest` looks it up by the commit stamped in the Stage 4 tables. A commit after
      `partner-tables` and before `manifest --set stage4` gives two different names, so `asof` exits 1 with `does not
      exist`. It never gives a wrong answer. A manifest is never overwritten, so the way back is a new commit and the table
      steps again. Stage 3's manifest names work the same way, and Task 11 let no commit land between Steps 2 and 10. The
      fix would make `manifest --set stage4` refuse when the table stamps name a commit other than `HEAD`. Size: quick-fix.
      Revisit if: `asof` on a live root exits 1 because its `stage4` manifest does not exist.
