# Deferred items

## 6-sec-filing-index-ingestion-stage-5-spec — 2026-10-11
- [x] Gated-then-reverted member cannot clear (owner-deferred, Stage 5 spec §4 and
      plan Stage exit): a gated member whose source later reverts to its base bytes
      is re-staged as the same candidate on every run, so the run stays
      `awaiting_approval`. Fix: let a later completed download of the same source
      supersede older pending members; touches `workflows/completion.py`
      (`accounts_for`) and the runner's member selection (`workflows/runner.py`). See
      specs/plans/completed/6-sec-filing-index-ingestion-stage-5-spec.md. Size: plan.
      Done when: that supersession rule lands, with a gated-then-reverted fixture
      that completes. → done in plan 7
- [x] Read-only `history` CLI (final review, plan-level gap): `quarter_history` and
      `EtlState.rollbacks` (`etl/history.py`, `etl/state.py`) are library-only, yet
      docs/runbooks/sec-edgar-reconciliation-approval.md tells operators to take the
      rollback `--to-generation` and the revert target "from `quarter_history`".
      An operator without Python cannot follow that procedure. Add a read-only
      operator command next to `candidates` (reuse `cli._operator_main`). Size: plan.
      Done when: a CLI command prints the active lineage (counts, gate, membership
      hash, approval) and the quarter's rollback records as canonical JSON, and the
      runbook uses it. → bound to roadmap Stage 6 Produces (resume 2026-10-12) → done in plan 9
- [x] Capture who re-activates an approved candidate (final review, accepted
      semantics): after a rollback to an approved candidate's base, a further
      `approve` re-activates it under the FIRST stored approval (first approval wins,
      `etl/approval.py` `_store_approval`) and records nothing about the acting
      operator; the new `--approver` is discarded. Also, an `approve` that loses its
      pointer race leaves an exact-bound approval record while reporting
      `approval_stale` with `approval: null`. Both are safe and documented in
      docs/runbooks/sec-edgar-reconciliation-approval.md. Size: design.
      Done when: Stage 6's operator-role mapping decides how approval and rollback
      actors are identified, and re-activation attribution (event or record) is
      implemented or consciously declined there. → note: plan 7 narrows this flow (approve now refuses a superseded candidate after a rollback) → done in plan 9
- [ ] Derived `activated` field (final review, T5): `approved` in `candidates` and
      `quarter_history` (`etl/history.py`) means an approval was indexed, so
      `stale` + `approved: true` cannot tell "activated then superseded" from "approval
      recorded, pointer race lost, never active". The runbook now says so. Derive an
      `activated` field from lineage/pointer evidence, not the Approvals index row.
      Size: plan. Done when: both listings expose it, the acceptance test and runbook
      cover it, and the `approved` caveat in the runbook is updated.
- [x] Shared CLI error handler can itself fail (final review Minor): `models.Error`
      validates its message with `require_text`, which rejects empty strings and
      control characters including newlines. `cli.py` builds
      `Error(outcome, str(exception), ...)` in `_operator_main` and in the workflow and
      ETL command mains, so an exception with an empty or multi-line message (likely
      from Azure SDK errors) makes the handler raise: exit 1 with a traceback and no
      JSON instead of exit 9. Size: quick-fix. Done when: one helper normalizes
      exception text for every CLI error path, with a test using an empty and a
      multi-line exception message. → done 2026-10-11 (/deferred quick fix)
- [ ] `EXIT_CODES` doubles as the registry of workflow member outcomes (final review
      Minor): `results.py` `EXIT_CODES` feeds `workflows/contracts.py` member-outcome
      validation, so the new `approval_refused`, `approval_stale`, `rollback_refused`
      and `rollback_stale` codes validate as member outcomes (mapped failed/incomplete)
      although workflow members never emit them. Report validation is slightly looser.
      Size: quick-fix. Revisit if: a stored workflow report with one of those member
      outcomes is accepted, or the outcome tables are next edited.
- [x] Test stdout hygiene (final review): passing runs print wire-evidence lines:
      `pointer-wire`, `mapped-wire`, `large-pointer-descriptor` and `approval-wire` in
      `tests/test_etl_storage.py` (the last at the Stage 5 method, ~line 124),
      `task5-sdk-proof` in `tests/test_etl_publication.py:344`, and `retained-workset` /
      `retained-registry` in `tests/test_etl_contracts.py:96,103`. Remove them or turn
      them into assertions in one hygiene commit. Size: quick-fix. Done when: the full
      offline suite prints no stray stdout. → done 2026-10-11 (/deferred quick fix)
- [ ] Load-flaky multi-process tests (execution baseline, pre-existing):
      `test_coordination.CoordinationTests.test_three_independent_exchange_processes_prove_intervals_priority_and_epochs`
      (`sqlite3.OperationalError: database is locked` at `PRAGMA journal_mode=WAL` in
      `storage/local.py` `LocalStateStore.__init__`, ~line 167) and
      `test_acquisition_processes.AcquisitionProcessTests.test_held_socket_parent_death_zero_successor_unsafe_interval_and_daily_next`
      (integrated successor exited 1) failed together in the pre-execution full-suite
      baseline (620 tests, 924 s) but pass alone and passed in the later 654-test run.
      On 2026-10-12 a 684-test run at load average ~5 failed the held-socket test again,
      plus two tests bound to a 0.4 s exchange deadline that a slow spawn can miss:
      `test_download.BoundedProcessTests.test_timer_installation_failure_and_stale_child_start_send_zero_requests`
      (`timer-installation-failure` got `permit_expired`, as the child started after the
      1/3 s dispatch window; the `stale-*` subtests then failed only because the failed
      subtest never deleted its `transport.jsonl`) and
      `test_acquisition_processes.AcquisitionProcessTests.test_independent_child_deadline_records_actual_fatal_exit_and_prefix`
      (`byte_count` 0, as the fatal timer fired before any entity bytes were retained).
      All three passed 3 of 3 alone and in the next full run. On 2026-10-12 a fourth,
      `test_workflow_runner.RunnerTests.test_deadline_after_selection_records_undispatched_units_without_child_work`
      (`pending_sources` 1 != 2), failed once in a parallel covering run on plan 7's
      branch, with no retained members in its fixture, and passed 7 reruns alone.
      Size: plan. Done when: the WAL open retries or the tests serialize, the
      deadline-bound tests tolerate a slow spawn (and the timer test deletes its trace
      in a `finally`), and several consecutive full-suite runs pass. → bound to roadmap
      Stage 7 Consumes: close before Stage 7 (resume 2026-10-12); a separate /deferred
      plan closes it, not Stage 6 (owner, 2026-10-12)
      Plan 9 evidence (2026-10-13): `test_download` `BoundedProcessTests`,
      `test_coordination` (three-process WAL open) and `test_acquisition_processes` (held
      loopback, 3 s wait) each failed once in full runs that overlapped concurrent agent
      work, and none failed in the quiet full runs (Tasks 5-8, 10 and 12: 739-763 tests).
- [x] Review Minor, approval/Azure storage coverage gaps (T1/T2/T6): nothing tests that
      `AzureStateStore.close()` closes `approval_client`, that `_check_endpoint`
      rejects a foreign-endpoint Approvals client, that the local store keeps approval
      and rollback rows under `table_name='Approvals'`, the Azure 404 path for a
      missing approval through `validated_manifest`, or `QuarterRollback` with a
      missing Approvals client (the rollback object is uploaded before
      `record_rollback` fails when a store is built without `approval_client`; the
      production factory always supplies it). Files: `storage/azure.py`,
      `tests/test_etl_storage.py`, `tests/test_azure_contracts.py`. Size: quick-fix.
      Done when: those cases have tests. → done 2026-10-11 (/deferred quick fix)
- [x] Review Minor, rollback/history/candidates coverage and invariants (T5/T6):
      `lineage` cycle, self-reference and missing-base errors, the exit-9 `candidates`
      path and a corrupt candidate row failing the whole listing, the approved-but-not-
      active state; `rollback`: a lost race resolving to `unchanged`, a lineage-valid
      target that fails `validated_manifest` writing nothing, refusals asserting that no
      `rollback.json` exists, the exact stdout key set and a rollback config error
      (exit 2, empty stdout), `rollbacks()` in a quarter that also holds a
      `WithdrawalApproval`. Invariants to consider: `QuarterRollback` should require
      `to_manifest_ref == generation_base(quarter, to_generation_id) + '/manifest.json'`
      (`etl/contracts.py`), `rollback.py` could reuse `publication.pointer_value`, and
      `unchanged` returns before the from-generation and ancestry checks (spec §5 step
      order). Files: `etl/history.py`, `etl/rollback.py`, `tests/test_etl_history.py`,
      `tests/test_etl_rollback.py`. Size: quick-fix. Done when: the tests exist. → done 2026-10-11 (/deferred quick fix)
- [x] Review Minor, reconcile/workflow coverage (T3/T4/T7): the refresh-flip test
      (`tests/test_reconcile_workflow.py` `test_selection_requires_refresh_exactly_for_reconcile`)
      covers backfill and reconcile but not daily, and the refresh/command check in
      `workflows/results.py` runs only when `discovery_call` is present; `run_phase`
      returns `report=None` on error so `(code, report.outcome)` raises
      `AttributeError` before diagnostics; revert-gap details are partly asserted
      (source_id, generation_id, first < active < observed ordering);
      `source_revert_gaps` (`workflows/runner.py`) uses `read_manifest` rather than
      `validated_manifest`, and a revert in a quarter gated by another member of the
      same run is reported only on the next run; spec R10 "a later download needs its
      own approval" is covered at library level only
      (`tests/test_etl_approval.py`), not in `tests/test_reconcile_acceptance.py`;
      long unwrapped lines in packages/sec-edgar-ingest/README.md. Size: quick-fix.
      Revisit if: those modules are next edited or a regression slips through them. → trigger fired; runner-local cases done in plan 7, remainder re-deferred under plan 7
- [x] Operator commands create a store at a mistyped path (final review Minor,
      pre-existing): `cli._operator_main` calls `open_stores`, which creates the root,
      writes the binding registry and creates the sqlite schema, so a mistyped
      fixture-only `--state-dir` makes `candidates` print `[]` with exit 0. Size:
      quick-fix. Revisit if: an operator reports an empty `candidates` listing against
      a wrong directory, or Stage 6 changes how operator commands open stores. → done in plan 9
- [ ] Rollback invariants (split 2026-10-11 from the ticked "rollback/history/candidates
      coverage and invariants" item, whose tests landed via /deferred; its Done-when did
      not cover these): (1) `QuarterRollback.__post_init__` (`etl/contracts.py`) does not
      require `to_manifest_ref == generation_base(quarter, to_generation_id) +
      '/manifest.json'`, so a record can name a manifest outside its target generation;
      (2) `etl/rollback.py` builds the pointer value inline at the `commit_pointer` call,
      while `publication.pointer_value` builds the same shape from a `Candidate`, so
      sharing one builder needs a capture-based form; (3) `rollback` returns `unchanged`
      when the target is already active, before the from-generation and ancestry
      checks, whereas Stage 5 spec §5
      (specs/completed/sec-filing-index-ingestion-stage-5-spec.md) orders those checks
      first. Size: quick-fix. Done when: (1) is enforced with a test, (2) uses one
      shared pointer-value builder, and (3) is either reordered to match §5 or recorded
      in §5 and the runbook as intended idempotence.

## 7-gated-revert-supersession — 2026-10-12
- [ ] Task 3 leftovers (plan 7, Plan completion step 3): the refresh/command check in
      `workflows/results.py` runs only when `discovery_call` is present; spec R10 "a
      later download needs its own approval" is covered at library level only
      (`tests/test_etl_approval.py`), not in `tests/test_reconcile_acceptance.py`; a
      revert in a quarter gated by another member of the same run is reported only on the
      next run; long unwrapped lines in `packages/sec-edgar-ingest/README.md`. Also
      `packages/sec-edgar-ingest/README.md:167` still says `awaiting_approval` clears only
      through approval, but a gated member whose source reverted now clears through
      supersession (final review, outside the plan's file list). Size: quick-fix.
      Revisit if: those modules are next edited or a regression slips through them.
- [x] v1 workflow selections are unreadable (final review, Codex [P1]; owner kept the
      plan's decision 2026-10-12): `workflows/results.py` `SELECTION_FORMAT` is
      `sec-workflow-selection-v2` and `_validate_selection` requires the `superseded`
      field, so a stored `sec-workflow-selection-v1` report fails `read_workflow_result`
      and replay with `state_conflict`. Plan 7's Global Constraints chose this (no
      deployed state, local-fixture only); the only v1 selections in the repo are
      committed `.fixture-state` proof artifacts under `specs/evidence/` that no test
      reads. Size: quick-fix. Revisit if: real (non-fixture) workflow state exists before
      this ships; then accept v1 with no `superseded` entries while new selections stay v2.
      → done in plan 8 (owner reversed plan 7's decision 2026-10-12; this supersedes the
      item's "Revisit if" condition; test_workflow_selection_v1.py now reads the committed
      v1 artifacts, which the item said no test did)
- [ ] Download evidence outside the retained members (final review, Codex round-2 [P2]
      and reviewer Minors): supersession dates the pending bytes by the promotion receipts
      of retained members (`workflows/members.py` `SourceDownloads`), so a download
      recorded under a parent workset (`collect --workset <parent>`, `cli.py`) or by a
      member whose projection fails `inventory()` leaves no receipt there. A guard on the
      source's latest downloaded snapshot covers it only while that is the latest:
      gated A, then completed A+B, then a standalone A, then a quarantined download of C
      lets the older completion drop the hold. That matches `etl.approval.superseding`
      (candidate A is already refused once the latest is C), so it is benign today. Also a
      missing Source row or null `latest_downloaded_snapshot` skips the guard (approve
      treats it as not superseded; practically unreachable), and an unreadable Source row
      taints its source silently (no gap, no test). Cure: index every `PromotionReceipt`
      row by `source_id` whatever the workset (the witness becomes a workset id, so the
      `served_by` shape changes), fail closed on a missing latest, and give the Source
      taint a gap and tests. Size: plan. Revisit if: standalone `collect --workset` is
      used against a source with gated workflow members, or Stage 6 changes how downloads
      are recorded.
- [ ] Review Minor, supersession tests and validator (plan 7 task and final reviews): the
      `not evaluated.obligations` guard in `workflows/runner.py` `select_work` is untested
      (the plan acknowledged it, Task 1 Step 5); the stored-report validator is weaker
      than the producer by design (it accepts any recorded served time, does not re-check
      that `by` is the newest completion or that the pending member awaits only
      publication, and could also reject a `by` bound to the pending member's own bytes);
      the quarantine half of the runbook claim that a quarantined later download leaves
      the gated member in place is derived from `collection.py` and untested; Task 3's
      fail-closed exit 9 on a corrupt active generation is pinned only by calling
      `source_revert_gaps` directly, not through `h.invoke('reconcile', ...)`, and its
      test takes the data file as the first `ref.role != 'changes'` manifest entry
      (order-dependent). Size: quick-fix. Revisit if: these modules are next edited or a
      regression slips through them.
- [ ] Review Minor, approval and CLI coverage for `superseded` (Task 2 review): the
      `superseding` branches `observed is None`, `latest is None` and equal timestamps
      (`etl/approval.py`) have no direct test, and a small table test would cover them;
      `tests/test_etl_cli.py` patches `withdrawal_candidates`, so no CLI test exercises
      status `superseded` end to end; `test_a_candidate_whose_source_moved_on_is_listed_superseded_and_refused`
      builds `(result.outcome, result.error.details[...])` before comparing, so a regressed
      refusal dies with `AttributeError` instead of `'success' != 'approval_stale'` (assert
      the outcome on its own line first). Size: quick-fix. Revisit if: `etl/approval.py`
      or `etl/history.py` is next edited.

## 8-v1-workflow-selection-reader — 2026-10-12
- [ ] Selection-format literal in the runner (final review Minor, pre-existing from
      plan 7): `workflows/runner.py:233` (`select_work`) writes the string
      `'sec-workflow-selection-v2'` instead of `results.SELECTION_FORMAT`, which is now
      one of two format constants beside `LEGACY_SELECTION_FORMAT`. Plan 8 leaves
      `select_work` untouched. Task 2's first-write guard makes drift loud, not silent:
      after a `SELECTION_FORMAT` bump every first freeze would raise `new selection must
      use the current format` until the literal is edited. Cure: import
      `SELECTION_FORMAT` beside `freeze_selection` (runner.py already imports from
      `.results`, so there is no cycle). See specs/plans/completed/8-v1-workflow-selection-reader.md.
      Size: quick-fix. Revisit if: `select_work` is next edited or `SELECTION_FORMAT`
      changes.
- [ ] The first-write guard's position is unpinned (Task 2 review Minor, confirmed by the
      final review): `test_a_new_selection_cannot_be_frozen_in_the_legacy_v1_format`
      (`tests/test_workflow_results.py:253`, mandated verbatim by the plan) uses
      `self.selection()`, whose `discovery_error` is `None`, so it never reaches
      `_capture_or_validate_discovery_failure`. Moving the guard in `freeze_selection`
      (`workflows/results.py:353`) below that call would still pass, and a refused v1
      selection with a failed discovery would then leave a `terminal.json` behind that pins
      later v2 selections for the attempt. Cure: a second test that takes the selection
      from `test_fatal_discovery_without_result_preserves_frozen_prior_jobs`, switches it
      to v1 without `superseded`, asserts the `Conflict`, and asserts `FileNotFoundError`
      reading `call['result_ref'].rsplit('/', 1)[0] + '/terminal.json'`. Size: quick-fix.
      Done when: that test exists and fails with the guard moved below the discovery block.
- [ ] A non-object stored selection reports `internal_error` (final review Minor):
      `_validate_selection` (`workflows/results.py:162`) and the first-write guard
      (`:353`) call `selection.get('format_version')`, so a stored `selection.json` whose
      JSON is a string, list, null or number raises `AttributeError`, which `cli.py`
      reports as `internal_error` rather than `Conflict`/`state_conflict`. The old
      `set(selection) != fields` check gave a `Conflict` for a string or a list of strings
      but already raised `TypeError` for numbers, null and lists of objects, so the
      behaviour was never uniform. Only tampered stored bytes reach it, because only
      validated selections are written. Cure: put `not isinstance(selection, dict) or` at
      the front of the `_validate_selection` condition and in the guard, with a test
      per JSON type. Size: quick-fix. Revisit if: stored workflow state can be corrupted
      by anything other than tampering, or `_validate_selection` is next edited.
- [ ] No test reaches the no-rewrite enforcement for a stored v1 selection (final review
      Minor): every negative test in `tests/test_workflow_selection_v1.py` is refused by
      `_validate_selection`. None proposes a selection that passes validation but differs
      from the stored v1 bytes (for example `{**v1, 'format_version': V2, 'superseded':
      []}` against the stored `proof-repeat` selection), which would show that
      `freeze_selection`'s `put_once` and read-back compare (`workflows/results.py:374`)
      refuse it and leave the stored bytes unchanged. The guarantee holds for every storage
      backend through `put_once`, but nothing pins it for v1. Size: quick-fix. Done when:
      that test exists and passes against the committed plan-5 bundle copy.

## 9-sec-filing-index-ingestion-stage-6-spec — 2026-10-13
- [ ] Pending-approvals count loads every withdrawal history (Codex final review P2,
      owner-deferred; also Task 7 review Minor): `emit_summary` in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/summary.py computes
      `pending_approvals` through `etl/history.py` `withdrawal_candidates`, which
      re-validates every recorded `Candidate` and builds each candidate's full `withdrawn`
      list from `changes.parquet`, on every fresh workflow result, after the durable result
      is written and without a deadline check. Memory and I/O grow with total withdrawal
      history (the job has 4 GiB); an overrun after the result is written would leave a
      Failed execution beside an exit-0 result, which Plan 10 classifies `result_mismatch`.
      Cure: a status-only counter beside `withdrawal_candidates` that never materializes
      withdrawn rows, used by `emit_summary`, with a test. Size: quick-fix. Revisit if: the
      number of recorded gated candidates grows, or a job approaches its memory or
      `replicaTimeout` limit.
- [ ] Operator access with no credential falls back to the worker identity (Task 2 review):
      `open_azure_stores(..., access='operator', credential=None)` in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py calls
      `worker_credential()`. The only Azure operator caller (`cli._operator_main`) always
      passes the `az login` credential and the worker identity lacks Approvals writes, but a
      future caller could silently open as the worker. Cure: raise `ValueError` when `access
      == 'operator'` and `credential is None`, with a test. Size: quick-fix. Done when: the
      guard and its test exist.
- [ ] Workflow summary resilience and coverage (Task 7 review): in
      packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/summary.py, (a)
      `emit_summary` guards four independent extras with one `try`, so a failure in
      `describe` also skips the milestone advance and nulls `last_successful_reconcile_at`;
      (b) the `record_reconcile_success` docstring says the milestone "can be rebuilt from
      results" but no rebuild exists, and a crash between `write_workflow_result` and
      `emit_summary` leaves it stale until the next exit-0 reconcile; (c)
      tests/test_workflow_summary.py lacks the CAS retry and exhaustion branch,
      `oldest_unresolved_period` on a daily run with a gate pending, a check that fields
      computed before a failed extra stay filled, and `gap_codes` /
      `discovery_complete=False` contents. Size: quick-fix. Revisit if:
      `workflows/summary.py` is next edited, or a missed reconcile-staleness or
      pending-approval alert is traced to a swallowed `summary_error`.
- [ ] Plan 10 has no alert on `summary_error` (final review, for Plan 10's review): if
      `withdrawal_candidates` keeps failing (for example the integrity `Conflict` in
      `etl/history.py`), `pending_approvals` stays null and Plan 10's pending-approval alert
      (`toint(fields.pending_approvals) > 0`,
      specs/plans/10-sec-filing-index-ingestion-stage-6-spec.md near line 3859) is silently
      suppressed on every run. Also, `gap_codes` keys in `workflow_summary` are not limited
      to `EXIT_CODES` names (only `member_outcomes` keys are, and Plan 10's vocabulary test
      covers `member_outcomes` only). Owner (plan 10 review, 2026-10-13): declined for Plan
      10, and no Plan 10 alert reads `gap_codes` (Plan 10 D5). Size: quick-fix. Done when:
      an alert on a non-null `summary_error` is in the Azure definitions, before the Stage 7
      deploy.
- [ ] Operator, approval and deployment test and validation gaps (Plan 9 task reviews,
      triaged defer): operator-open conflict tests in tests/test_operator_open.py skip the
      no-write assertions used elsewhere; the Azure refusal of `rollback --operator` free
      text and approve's `open_stores` kwargs are unasserted in
      tests/test_operator_identity.py; `ApprovalActivation.__post_init__` in
      `etl/contracts.py` does not enforce `approval_ref == approval_ref(quarter,
      generation_id)` for index readers (`QuarterRollback` has the same gap; adding it risks
      a circular import from `etl.manifest`), and tests/test_approval_activation.py covers a
      stale candidate only by a moved base, not a superseding download; `deployment.main` in
      `deployment.py` writes outside its `try` (an unwritable `--out-dir` gives a traceback
      instead of exit 2, and the two files are not written atomically) and its CLI test
      covers only success (no exit-2 shape, no ARM `$schema` or `contentVersion`);
      `principal_from_token` in `storage/identity.py` does not fall back to
      `preferred_username` when `upn` is present but rejected;
      `scripts/build-image-context.sh` is tested only for its exec bit (the new-or-empty
      rule, usage exit 2 and one-wheel check were verified by hand) and
      tests/test_image_definition.py does not pin WORKDIR, HOME or `chmod 0700`.
      Size: quick-fix. Revisit if: those modules are next edited.
- [ ] Image smoke hardening (Task 11 review): in
      packages/sec-edgar-ingest/tests/image_smoke.py, a non-JSON stdout gives a bare
      `JSONDecodeError` that loses the container's output (`Smoke.command`), a
      `TimeoutExpired` kills only the `docker` CLI so the container can keep running in the
      VM, rollback is checked by count only (no active-generation assertion), and the
      workflows run with `--config` only while ADF passes `--config-env
      SEC_EDGAR_INGEST_CONFIG` (add one `-e SEC_EDGAR_INGEST_CONFIG=... --config-env`
      invocation). Owner (plan 10 review, 2026-10-13): Plan 10 builds no image, so it
      declines them (Plan 10 D6). Size: quick-fix. Done when: the smoke is next run, at
      Stage 7's image work, with those four changes.
- [ ] Colima VM image and an unexplained pre-build image (Task 11 review, owner disclosure):
      Task 11's `colima start` downloaded Colima's own aarch64 VM disk image (about 325 MB),
      a network use that D1 and D5 ("Nothing else touches the network") do not name; and the
      Task 11 report's `docker info` showed `Images: 1` before the build, unidentified
      (binfmt was ruled out). Owner (plan 10 review, 2026-10-13): D1 covers the VM image
      (Plan 10 D6). Size: quick-fix. Done when: `docker image ls -a --digests` at the next
      `colima start`, before any build, shows nothing or only the pinned
      `python@sha256:d1e795fb…` base.

## 10-sec-filing-index-ingestion-stage-6-spec — 2026-10-13
- [ ] Stage 7 must prove the Stage 6 offline assumptions against live Azure (final review of
      plan 10): every Stage 6 template, pipeline and alert was checked only offline against
      the committed `main.json`, pipeline JSON and alert KQL, so these remain assumptions:
      ADF's expression lexer accepts a raw TAB, LF or CR inside a quoted literal and `int()`
      reads an 18-digit negative text value (`pipelines/render.py` wait cap and `Location`
      validation); `waitTimeInSeconds: 0` is accepted; a real `Location` header carries no
      `%` or `\` and its region segment equals `asyncPrefix` (`main.bicep:181`); an operation
      result names the execution as `{id, name}` (a 202 body naming it is only a fallback when
      the `Location` is invalid, and no scenario pins that precedence); ADF wraps a non-JSON
      result body as `{Response: …}` (classifies `result_mismatch`, not `result_missing`;
      S7-09); the Web activity output cap (F1 cites 4 MB) does not end a large backfill result
      as `result_missing` on every run; the queries' columns (`ContainerAppConsoleLogs`
      `JobName` and `Log`; `ADFActivityRun` `ErrorCode` and `PipelineRunId`, with a Fail
      activity's custom code in `ErrorCode`) exist (`skipQueryValidation` hides a wrong name),
      each alert fires (S7-17), and `summarize arg_max(...)` with no `by` over an empty window
      returns no row (so `alert-sec-edgar-reconcile-staleness` is silent when no
      `workflow_summary` lands in two days); table-scope RBAC, user-assigned identity
      replication and AcrPull propagation (a first deployment may need one retry); and the
      Bicep property bodies that Bicep 0.38.33 cannot type (BCP081: Storage, ACR, Log
      Analytics, Jobs and managedEnvironments at the pinned API versions) pass `validate` and
      `what-if`. Also pin the grant `name` (a `guid` of scope id, principal and role) and each
      access deployment's `roleDefinitions` dependency, which neither `AccessTests` nor
      `GrantSetTests` checks, once a redeploy's what-if shows no change. Size: plan. Done when:
      Stage 7's checks (S7-05, S7-06, S7-09, S7-17 and the validate/what-if runs) have proven
      or refuted each assumption and any wrong one is corrected in
      `infra/azure/sec-edgar-ingest/`.
- [ ] Run-time pipeline parameters can redirect the ADF identity's tokens (final review of
      plan 10): `jobPath`, `asyncPrefix`, `resultsUrl`, `imageRef`, `imageDigest` and
      `containerEnv` are parameters of `pl-sec-edgar-run-worker` (`modules/factory.bicep`,
      `DEFAULTS` in `pipelines/render.py`). A direct run by a principal holding createRun with
      `jobPath='.evil.example/x'` changes the host of `concat('https://management.azure.com',
      jobPath)`, or points `resultsUrl` anywhere, or starts another image. Scheduled runs
      pass only `command` and `runId`, so they stay pinned, and spec §5 treats start
      authority as trusted at worker privilege. Cure: require `jobPath` to start with
      `/subscriptions/` and to contain none of `@`, `.` and `:`, validate `resultsUrl` and
      `asyncPrefix` the same way, or move the pinned values out of parameters; add scenario
      rows. Size: quick-fix. Done when: a direct run with a hostile value ends
      `execution_unknown` before any request is sent. Revisit if: another principal is given
      createRun on the factory.
- [ ] ADF interpreter validation gaps (plan 10 Task 1 and final reviews):
      `packages/sec-edgar-ingest/tests/adf_interpreter.py` checks function arity only when an
      expression is evaluated (a wrong-arity call in an untaken lazy branch passes
      `validate_pipeline`), does not check `pipeline().parameters.X` references (a typo
      fails one activity at run time and can be masked), defaults an unset `Bool` variable to
      `''`, and raises `KeyError` or `AttributeError` instead of `AdfUnsupported` for a Switch
      case without `activities` or when `run` skips `validate_pipeline`. Every pipeline test
      calls `validate_pipeline`, and ADF publish validation is the backstop. Size: quick-fix.
      Done when: `validate_pipeline` walks arity and parameter references, with tests.
      Revisit if: `adf_interpreter.py` is next edited.
- [ ] Run-worker scenario and fault coverage (plan 10 Task 2 and final reviews): add a
      `SCENARIOS` row for an `Azure-AsyncOperation` header alone (the pipeline never reads it,
      so the behaviour is structural), rows for the 202-with-body precedence, key the fault
      suite by (activity, occurrence) so a fault can hit launch 2 only, and derive the Until
      budget assertion in `test_run_worker_pipeline.py` from `DEFAULTS` instead of
      `3 * 3600 >= 2 * (4200 + 600)`. Also tighten `execution_reference` in
      `pipelines/render.py`, which accepts `.`, `..`, `\` and TAB/LF/CR as an execution name
      (it fails safe because the host is fixed and the result must name the execution), once
      Stage 7 records real execution-name syntax. Size: quick-fix. Done when: the rows and the
      derived assertion exist and `execution_reference` matches the observed name syntax.
- [ ] Compare `support_adf.DEFAULTS` with the template (plan 10 Task 5 review): `DEFAULTS`
      values for `containerName`, `containerResources`, `containerEnv` names and
      `maxLaunches == 1 + transient_replays` agree with `modules/job.bicep` and `main.bicep`
      today only by duplicated literals; `test_azure_template.py` checks names and the
      default-bearing parameters but not these values. Size: quick-fix. Done when: the test
      asserts them against `job_container` and the config template.
- [ ] Operations runbook polish (plan 10 Task 8 review),
      `docs/runbooks/sec-edgar-azure-operations.md`: the `stale` row says "re-run `candidates`
      or `history`" but `sec-edgar-reconciliation-approval.md` says reconcile then review
      candidates (`approval_stale`) or re-run `history` (`rollback_stale`), and no pipeline
      command emits exit 11 today (a defensive mapping, say so); the `pending` row's "the
      second launch" holds only while `transient_replays` is 1 (capped at 1 in
      `config.py`) and "the next scheduled run continues" does not apply to
      `pl-sec-edgar-backfill`, which has no trigger; Deploy step 4 names validate, what-if and
      deploy but shows only what-if; the redeploy step "re-enable both staleness alerts" says
      the runbook states no command and should carry a verified one; the trigger start-time
      parameters are length-checked only, so say the exact no-Z format. Size: quick-fix.
      Done when: Stage 7's runbook exercise has verified each command and the rows are
      corrected (the alert-enable command by Stage 8).
- [ ] Plan-exit check script polish (plan 10 Task 9 review):
      `scripts/check-sec-edgar-ingest.sh` runs `git diff --exit-code -- …/pipelines`, which
      misses a newly rendered untracked pipeline file and false-fails on pre-existing
      uncommitted edits, and leaks its temp directory when the Bicep build or `cmp` fails (no
      `trap`). Cure: add `git status --porcelain -- infra/azure/sec-edgar-ingest/pipelines`
      and a `trap 'rm -rf "$compiled"' EXIT`. Size: quick-fix. Revisit if: a pipeline file is
      added or the script is next edited.
