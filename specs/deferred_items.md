# Deferred items

## 6-sec-filing-index-ingestion-stage-5-spec — 2026-10-11
- [ ] Gated-then-reverted member cannot clear (owner-deferred, Stage 5 spec §4 and
      plan Stage exit): a gated member whose source later reverts to its base bytes
      is re-staged as the same candidate on every run, so the run stays
      `awaiting_approval`. Fix: let a later completed download of the same source
      supersede older pending members; touches `workflows/completion.py`
      (`accounts_for`) and the runner's member selection (`workflows/runner.py`). See
      specs/plans/completed/6-sec-filing-index-ingestion-stage-5-spec.md. Size: plan.
      Done when: that supersession rule lands, with a gated-then-reverted fixture
      that completes.
- [ ] Read-only `history` CLI (final review, plan-level gap): `quarter_history` and
      `EtlState.rollbacks` (`etl/history.py`, `etl/state.py`) are library-only, yet
      docs/runbooks/sec-edgar-reconciliation-approval.md tells operators to take the
      rollback `--to-generation` and the revert target "from `quarter_history`".
      An operator without Python cannot follow that procedure. Add a read-only
      operator command next to `candidates` (reuse `cli._operator_main`). Size: plan.
      Done when: a CLI command prints the active lineage (counts, gate, membership
      hash, approval) and the quarter's rollback records as canonical JSON, and the
      runbook uses it.
- [ ] Capture who re-activates an approved candidate (final review, accepted
      semantics): after a rollback to an approved candidate's base, a further
      `approve` re-activates it under the FIRST stored approval (first approval wins,
      `etl/approval.py` `_store_approval`) and records nothing about the acting
      operator; the new `--approver` is discarded. Also, an `approve` that loses its
      pointer race leaves an exact-bound approval record while reporting
      `approval_stale` with `approval: null`. Both are safe and documented in
      docs/runbooks/sec-edgar-reconciliation-approval.md. Size: design.
      Done when: Stage 6's operator-role mapping decides how approval and rollback
      actors are identified, and re-activation attribution (event or record) is
      implemented or consciously declined there.
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
      Size: plan. Done when: the WAL open retries or the tests serialize, and several
      consecutive full-suite runs pass.
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
- [ ] Review Minor, reconcile/workflow coverage (T3/T4/T7): the refresh-flip test
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
      Revisit if: those modules are next edited or a regression slips through them.
- [ ] Operator commands create a store at a mistyped path (final review Minor,
      pre-existing): `cli._operator_main` calls `open_stores`, which creates the root,
      writes the binding registry and creates the sqlite schema, so a mistyped
      fixture-only `--state-dir` makes `candidates` print `[]` with exit 0. Size:
      quick-fix. Revisit if: an operator reports an empty `candidates` listing against
      a wrong directory, or Stage 6 changes how operator commands open stores.
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
