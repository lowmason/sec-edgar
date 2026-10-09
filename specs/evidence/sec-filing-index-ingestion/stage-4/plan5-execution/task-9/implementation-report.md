# Task 9 implementation report

Status: implemented and verified locally; independent task review is pending. No Task 10 execution or acceptance is claimed.

Checkout: `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`.
Branch: `codex/sec-edgar-stage4-plan5`.
Accepted predecessor base: `cf92292317c77cdeca07c235d9ecb7158c40cc00`.
Owned implementation commit: `1122e3697903017d64a28570597db4d31f19c213` (`feat: expose checked backfill and daily workflow commands`).

## Scope and behavior

Only the five approved implementation paths were committed: `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `packages/sec-edgar-ingest/tests/test_workflow_cli.py`, `packages/sec-edgar-ingest/README.md`, `docs/runbooks/sec-edgar-ingest-acquisition.md`, and `docs/runbooks/sec-edgar-etl-publication.md`. This report and newly created Task 9 evidence remain unstaged. No predecessor implementation, plan, specification, retained input, binding/config/workset, controller ledger, dependency or pin was changed.

The complete specified parser admits `backfill` and `daily` with the required config/run/execution/attempt/deadline fields and optional state/fixture/today fields. Child-only mode/discovery-id/refresh/workset/force flags are not public workflow arguments. `main` routes workflows before the existing child validation branch. Workflow validation checks IDs, parser/schema, lease granularity, UTC deadline, date format and fixture controls before opening stores. The implementation reads immutable intent or the durable begun WorkflowAttempt pin before constructing the workflow context. Invocation remains exactly `{command,today,fixture_sha256,pinned_end_quarter}`. Saved intent/report repair, child dispatch, immutable completion and error/resource-close behavior use accepted T1–T8 boundaries unchanged.

The README/runbooks describe inclusive endpoints and once-pinned open quarter, handoff/outage discovery and retained retries, exact invocation replay, original captured generations, report/index ordering, source versus quarter counters, empty unresolved baseline units, whole-source quarantine versus transport prefixes, gates and post-CAS recovery, exits 0–10, and captured readers. The README replaces the stale Stage 3 blocking statement with the specified owner amendment and retains its existing verification-record link.

## Public signatures consumed

- `main(argv: Sequence[str] | None = None) -> int` remains unchanged.
- `Dispatcher(context, settings, fixture_pack, state_dir, store, objects, observer=None)` is imported as `WorkflowDispatcher`; child adapters stay inside their public CLI paths.
- `freeze_workflow(current, intent, store, objects) -> RunContext` owns saved intent/pin checks.
- `read_workflow_result(path, store, objects) -> WorkflowResult` owns authoritative completed-report validation and index repair.
- `write_workflow_result(result, store, objects, observer=None) -> str` owns immutable completion.
- `run_workflow(context, settings, intent, dispatcher, store, objects)` remains the accepted runner boundary.
- WorkflowResult uses `source_workset_ref`; MemberResult uses `parent_ref`. No API was renamed or changed.

## Red, diagnostics and green

Evidence root: `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-9/`. Every JSON evidence entry contains exact argv, exit code and complete stdout/stderr; none was overwritten.

Tests were extracted from the approved brief and written before the CLI implementation. `red.json` records the exact scoped command below exiting 1: five methods errored with argparse rejecting the missing `backfill` command. The sixth, `test_failure_closes_all_opened_resources_and_writes_no_report`, errored before invocation because `patch.object(cli, 'run_workflow', ...)` raised AttributeError for the absent CLI helper. Both are missing-feature failures; the sixth is specifically patch setup against an absent implementation symbol, not an argparse failure. No missing dependency cache caused the red run.

```sh
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_cli.py -v
```

`green-initial.json` retains the first post-implementation run: five methods passed; the omitted-today first invocation returned exit 8. `omitted-date-reproduction.json` retains the exact independent reproduction; `omitted-date-cause.json` additionally retains the actual report with the discovery/transport gap: “process wall time diverged from its monotonic clock.” The example patched `cli.Clock.now`, which is the shared coordination.Clock class, to a constant historical wall time while real monotonic time continued advancing during no-burst fixture pacing. Coordinator._time correctly refused after its accepted 2-second uncertainty allowance. This is an example clock setup defect, not a production contract defect.

The only setup correction imports `time`, records an origin, and advances the first mocked wall clock with elapsed `time.monotonic()`. Every assertion is unchanged: first call success, immutable report replay, original Oct 7 pin, next-day behavior, and no dispatcher construction on replay. The parent explicitly agreed to this fixture-only correction. No production/predecessor clock, pacing or ownership guard was relaxed.

`green-final.json` records the unchanged scoped command exiting 0, six methods PASS (52.805 seconds). It covers inclusive Q3/Q4 baseline plus daily deduplication/captured reader, completed post-deadline replay without dispatch/cursor use, changed invocation conflict and immutable report, omitted-today saved pin after calendar change, pre-backend validation/private child flags, and closing all resources/no fabricated result on conflict.

## Regression and help verification

```sh
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_cli.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_cli.py -v
git -c core.whitespace=cr-at-eol diff --check
```

`cli-regression.json`: exit 0, 25 PASS (62.228 seconds).
`etl-cli-regression.json`: exit 0, 38 PASS (6.980 seconds).
`help.json`, `backfill-help.json`, `daily-help.json`: exit 0 each, guard installed before importing CLI; full exact Python argv is retained. Root help lists all six commands; both workflow help surfaces show only approved fields.
`diff-check.json` and `diff-check-final.json`: exit 0, no whitespace findings.
`commit.json` records the explicit owned-path commit, exit 0. No add-A or unrelated staging occurred.

## Deviations and self-review

Two narrow deviations from illustrative brief text are documented: the reproduced constant-wall-clock test setup correction above, and qualification of the proposed native/installed workflow-proof sentence. Those workflow proofs are still the next Task 10/11 verification gate; docs do not claim unrun proof. The parent agreed to the factual qualification. Required limitations and later-stage responsibilities remain unchanged. Imports and prose wrapping follow existing style; specified helpers/parser/main behavior is unchanged.

Applied skill checks: clean-code/clean-coder, test-driven-development, systematic-debugging, verification-before-completion. Applied: workflow helpers separate validation, saved authority, context and stdout responsibilities (G30/G34); names retain contract vocabulary (N1/N2); intent comments explain immutable pin/repair constraints (C3/C4); tests independently exercise actual public commands and stores, lifecycle/time/conflict boundaries (T1/T5/T6). The fixture elapsed-wall-clock correction restores repeatable timing without weakening behavior. No adjacent tidying or structural extraction was performed.

Self-review checked the diff against every task clause, consumed signatures and exact codec names; verified child paths are unchanged, replay occurs before dispatcher construction, errors have no invented completed result, all opened resources close, immutable evidence survives conflicts, documentation matches accepted behavior, and only owned files are committed. No unresolved implementation concern was found. This self-review is not the required independent review; actual reviewer identity/diff/test findings belong to the controller review checkpoint before Task 10.

All verification was offline with cached frozen dependencies and network/provider guards. No live SEC/Azure/authentication/compute/provisioning/deployment/image/network fetch or trigger enablement occurred. The selected limits/pins and indefinite development retention remain intact. All 22 Stage 7 integrated checks remain reserved/not_run; no production coverage, deployed fit or historical completeness is claimed.

## Independent reviewer report correction

The independent Task 9 reviewer approved specification compliance and code quality with a minor report-accuracy finding. The red summary above now distinguishes the actual five argparse missing-command errors from the sixth AttributeError for absent `cli.run_workflow` during patch setup before invocation. Original `red.json` remains unchanged. This correction changes only the ignored Task 9 report; no code, test, rerun or commit was needed. The controller retains reviewer identity and acceptance evidence.
