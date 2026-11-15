# Stage 2a1 branch gate

Plan: `specs/plans/9-sec-filing-index-pre-dispatch-cost.md`, Task 8. Spec: `specs/sec-filing-index-pre-dispatch-cost.md`.
No SEC request was sent. Every run below used fixture acquisition, the offline guard, or a scratch clone of the stores.

## Gate

- Branch: `stage2a1-pre-dispatch-cost`
- Merge base with `main`: `42ce078b05da29cd34c3002f279720c73e1230ee`
- Gated commit: `bb8b99067db8ea27b509a2b87351564ec1a7afb1`
- Command, from the worktree root:

```
env -u PYTHONDONTWRITEBYTECODE UV_PROJECT_ENVIRONMENT=/tmp/s2a1-venv UV_NO_SYNC=1 SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache sh scripts/check-sec-edgar-ingest.sh
```

- Start: `2026-11-15T14:36:59Z`. End: `2026-11-15T15:46:44Z`.
- Result: `Ran 1222 tests in 4179.723s`, then `OK`. The log ends with `exit 0`.
- Modules: 77 test modules (the 75 older modules, `test_pre_dispatch_cost` and `test_release_2a1`).
- Skipped, failed or errored tests: none in the log. The log has no warning.
- The check script also built the sdist and the wheel and ran the installed CLI help and version (`0.2.0`).
- Log: `fixture-data/stage2a1-gate.log`.

### Commits after the gated commit

The final review led to one commit: `20ac48b` (a test only, see `## Review`). It adds one test to `tests/test_pre_dispatch_cost.py` and changes no source file. So the gate was not run again. The module `test_pre_dispatch_cost` ran again on `20ac48b`: `Ran 33 tests in 394.765s`, `OK`.
The commits that add this file and the plan Decisions change documentation only. The code of the branch tip is the code that the gate tested.

### Deviation from the plan text

- The plan says to link `.venv` as plan 7 Task 8 Step 1 does. The link pointed at `/tmp/s2a1-venv`, as in plan 7, so the tests import the code of the worktree and not the code of the main checkout. The link was removed after the gate, and so was the `dist/` folder that the check script built.

## Installed 2a release run (Step 2, P9)

```
SEC_LOCAL_2A_RELEASE=/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a1-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py test_release_2a1 -v
```

Result on `bb8b990`: `Ran 2 tests in 133.847s`, `OK`, `exit 0` (started 2026-11-15T15:46:59Z). Log: `fixture-data/stage2a1-installed-2a.log`.
The installed `e49d3ba8…` release took the place of the 2a build that the gate builds from revision `32863852ce57f1da99db4720bd1c729727b4ec0c`.

## Branch check (Task 6, P11): a check, not evidence

Task 6 replayed invocation 2's selection on a fresh clone of the live store with the branch code (`replay.py run … --branch`, interpreter `/tmp/s2a1-venv/bin/python -I -B -X pycache_prefix=/dev/null`). The evidence for the release comes later, from the installed release (spec §6).

- `diff` assigned all 404 added rows and found no unassigned or removed row. Invocation 1 has 28 `WorkflowMember` and 28 `Binding` rows. Invocation 2 has 53 and 48 (F4). Three `Failure` rows of invocation 1 follow Decision D6.
- `cut … 2` left 155 registered members.
- `run … 2 --branch` exited 0. The frozen selection is byte-equal to the saved one: SHA-256 `4c928887c9c5e34fb4d1960d3663324db032296a7cd9675a155a4912fd390dec`, 18,560,172 bytes.
- 155 members at the start, 208 after projection, 53 new members, 48 of them reached the registry check (`WorkflowMembers.of_source`).
- Phases in seconds: before discovery 56.49, discovery (replayed) 0.19, projection 1.95, after discovery 43.14, freeze 18.61. Modelled first dispatch: 150.19 s.
- The machine load average was 10 to 14 from other projects during this run, so these times are high. An earlier run of the same step at a load of 3.7 to 5.3 gave 118.4 s.
- The refusal of every spelling of `data/` and `backups/` was tested with 90 refusal cases (wrong case, firmlink, symlink, paths below them, outputs). All exit 5 before a store opens.
- Files: `specs/evidence/stage2a1/predispatch/replay.py`, `diff.json`, `branch-check.json`.

## Locked inputs and the platform member (Step 5, P8, H9)

- `git show stage2a1-pre-dispatch-cost:pyproject.toml | grep -n members` prints `20:members = ["packages/sec-edgar-ingest"]`.
- `git diff --stat 32863852ce57f1da99db4720bd1c729727b4ec0c stage2a1-pre-dispatch-cost -- uv.lock pyproject.toml packages/sec-edgar-ingest/pyproject.toml` prints nothing.

## Spec section 5 to tests

All test names are in `packages/sec-edgar-ingest/tests/`.

| Item | What it checks | Tests |
|---|---|---|
| 1 | Selection equality (H1), with finished, pending, superseded, repair-obligation, corrupt-member, corrupt-parent, corrupt-publish-call and empty stores, and a discovery child that fails | `test_pre_dispatch_cost.SelectionEqualityTests.test_selection_equal_with_and_without_kept_values`, `SelectionEqualityTests.test_daily_and_reconcile_selections_equal_without_kept_values` |
| 2 | Counts (H2): one `_publish_calls` and one `read_parent` per ref per phase, at 1, 10 and 50 registered members | `SelectionCountTests.test_counts_per_phase_at_1_10_50_members`, `SelectionCountTests.test_empty_store_selection_equal_and_counted`, `SelectionChecksTests.test_every_threaded_function_takes_its_checks_from_the_kept_values` |
| 3 | Validity (H3): kept values equal fresh ones after each write kind, a failure is not kept, `renew()` drops everything | `SelectionChecksTests.test_kept_values_equal_fresh_ones_after_each_write_kind`, `SelectionChecksTests.test_a_recovered_parent_passes_on_the_next_read`, `SelectionChecksTests.test_publish_calls_are_kept_until_renew`, `SelectionChecksTests.test_parents_are_kept_by_ref_until_renew`, `SelectionChecksTests.test_a_failed_computation_is_not_kept`, `SelectionCountTests.test_renew_runs_when_discovery_returns_and_when_it_raises` |
| 4 | Unchanged paths (H4): `process_member`, `sibling_completion`, `freeze_selection` and the low-level commands receive no kept value | `UnchangedPathTests.test_no_path_after_select_work_uses_a_kept_value` (the final-review fix: spies on `SelectionChecks.parent` and `SelectionChecks.publish_calls`, two fixtures, six hand mutants caught), `UnchangedPathTests.test_dispatch_and_finish_use_no_kept_value`, `UnchangedPathTests.test_resumed_attempt_builds_no_selection_checks`, `ReuseSourceFilterTests.test_sibling_completion_never_runs_the_full_inventory`, `test_workflow_drain.SiblingCompletionTests.test_a_skip_check_gap_refuses_the_skip_and_stays_out_of_the_report` (Decision D5) |
| 5 | Reuse (H5): the same candidates, gaps, order and binding as today, with a corrupt member of another source, of the same source, and a corrupt reuse pin | `ReuseSourceFilterTests.test_same_result_with_a_corrupt_member_of_another_source`, `…_with_a_corrupt_member_of_the_same_source`, `…_with_a_corrupt_reuse_pin`, `…_with_a_malformed_member_row`, `test_two_pins_of_one_source_bind_nothing_as_today`, `test_reuse_validates_only_its_own_source`, `test_with_checks_the_result_is_unchanged_and_each_parent_is_read_once`, `test_the_new_checks_keywords_are_optional_and_keyword_only` |
| 6 | Decoding (H6): cached hints equal `typing.get_type_hints`, the mapping is read-only, refusal text is unchanged | `TypeHintsCacheTests.test_cached_hints_equal_get_type_hints_for_every_record_type`, `…test_cached_hints_cannot_be_changed`, `…test_hints_are_computed_once_per_type`, `…test_refusal_text_is_unchanged_after_the_cache_is_warm`, `…test_nested_record_refusal_is_unchanged_once_its_own_hints_are_cached`; the existing decoding and refusal tests pass unchanged |
| 7 | Two releases (H7), the 2a build from its revision, and once from the installed `e49d3ba8…` release | `test_release_2a1.TwoReleaseTests.test_new_release_continues_2a_origin_pending_work`, `TwoReleaseTests.test_2a_release_continues_new_origin_pending_work`; installed run above |

## Plan Review Focus to tests

| Focus | What it checks | Test |
|---|---|---|
| 1 | `daily` and `reconcile` selections equal with and without kept values | `SelectionEqualityTests.test_daily_and_reconcile_selections_equal_without_kept_values` |
| 2 | A resumed attempt freezes the saved selection and builds no `SelectionChecks` | `UnchangedPathTests.test_resumed_attempt_builds_no_selection_checks` |
| 3 | Two pins of one source and an unbound third member: reuse binds nothing, same gaps | `ReuseSourceFilterTests.test_two_pins_of_one_source_bind_nothing_as_today` |
| 4 | An empty store: equal selections, the empty call list computed once per phase | `SelectionCountTests.test_empty_store_selection_equal_and_counted` |
| 5 | A refusal after the cache is warm, for a nested record too | `TypeHintsCacheTests.test_refusal_text_is_unchanged_after_the_cache_is_warm`, `TypeHintsCacheTests.test_nested_record_refusal_is_unchanged_once_its_own_hints_are_cached` |

## Review

Two reviewers read the whole branch. A scoped re-review read only the fix.

- Seat 1, `code-reviewer` (opus), range `42ce078..bb8b990` (11 commits, 18 files; the three generated evidence JSON files were left out of its diff). It read the diff and the code and ran no test or build. Verdict: ready to merge with fixes, no Critical finding. It checked every `read_parent` and `_publish_calls` site in both phases of `select_work`, the validity argument of spec §4.3, `renew()` on both discovery outcomes, the `checks is None` paths, `of_source` against `inventory()`, the five Review Focus items, and the root guard and the row cut of both scripts.
- Seat 2, Codex (`codex exec review -m gpt-6-sol -c sandbox_mode=read-only --base 42ce078b05da29cd34c3002f279720c73e1230ee`, Decision D7), reviewed `bb8b990`. Result: no actionable regression. It did not run the test suite.
- Re-review, `code-reviewer` (opus), range `bb8b990..20ac48b`: the finding below is addressed. No new Critical or Important finding.

| # | Source | Finding | Result |
|---|---|---|---|
| 1 | Seat 1, Important | `UnchangedPathTests.test_dispatch_and_finish_use_no_kept_value` cannot fail for `freeze_selection`, `sibling_completion` or the low-level commands, although spec §5 item 4 says a test fails if one of them receives a kept value. The cause is the plan's wording of the test. The code is safe. | Fixed in `20ac48b` (test only). The new test is `UnchangedPathTests.test_no_path_after_select_work_uses_a_kept_value`. It spies on `SelectionChecks.parent` and `SelectionChecks.publish_calls`, runs a drain fixture (reaches `process_member`, `sibling_completion`, `freeze_selection`, the finish step, `transform` and `publish`) and a superseded fixture (reaches the loop in `freeze_selection`), and has a control that the spies fire inside `select_work`. Six hand mutants fail it. The old test fails for one of them. The plan test is unchanged. |
| 2 | Seat 2 | none | none |

Task reviews during the work (each ran at its own task, before this review):

- Task 1, 3, 4 and 5 passed on the first review. Task 4 took two owner stops (D4, D5).
- Task 2: two Important findings (a non-text `parent_ref` changed the refusal text, and two bypass paths had no test). Fixed in `26d85b4`.
- Task 6: three Important findings. The path refusal missed wrong-case and firmlink spellings of `data/` (fixed in `af150de`). Three `Failure` rows had been assigned instead of stopping the task (Decision D6). The freeze phase had no factor-2 check (fixed in `af150de`).
- Task 7: one Important finding, a member count in the implementer's report (22 instead of 21). It was a text error in a file outside the repository. No code changed.

Decisions of the owner during the run: D4 (the `select_twice` fixture primes one discovery, with scenario markers), D5 (the drain stand-in takes `**kwargs`), D6 (`Failure` rows are assigned by `run_id` and `discovery_id`), D7 (Codex review). The plan's Decisions hold the full text.

Rulings on items that the reviewers did not judge (`Ruling:` lines in the ledger, kept here in short form):

- Task 1: no test that a raise is not cached. Kept. `functools.cache` stores no exception, and Task 2 covers the rule for the new code.
- Task 2: with `checks`, `_obligations` decodes every input before its first loop body. Kept. The Interfaces and spec §4.4 item 1 give the same `state_conflict` gap. The selection is equal.
- Task 3: spec §4.4 item 7 says a malformed `WorkflowMember` row is skipped. On the real store a list-valued row makes `scan` raise, in today's code and in the new code. Kept, because spec line 97 requires the same result as today.
- Task 3: reuse no longer reads other-source rows. Kept. It is H5 by design, and `select_work` still runs the full `inventory()`.
- Task 5: the new tests omit the manifest schema check of the 1c test. Kept. The spec sentence names continuation, and H8 holds the schema.
- Task 5: in the pending scenario a hash-ordered sort can leave no cross-release child. Kept. It is the existing fallback, and the repair case always runs one.
- Task 6: a hard link from a scratch root into `data/` would not be refused. Kept. The clone commands make new inodes.
- Task 6: the factor-2 check on two points is sensitive to machine load. Kept for Task 10, which stops for the owner on exit 4.
- Task 6: the freeze phase gets the per-member functions `results.validate_member_provenance` and `results.validate_capture` instead of failing closed.
- Task 7: `walls` times the quick `sibling_completion` path. Kept. The full path applies only to later siblings, never to the member that has child work and the longest wall.
- Task 7: `--branch` runs the read-only `preflight()` and `retain_manifest`. Kept. Task 11 does not use `--branch`.
- Task 7: `walls` and `starts` do not refuse a scratch path under `releases/`, and the `sibling_completion` premise is not checked against the store. Kept. The plan puts every scratch folder under `logs/`, and the store is the fixed plan 8 backup.

## Items for the later tasks

- Task 10: the branch runs predict that the P4 factor-2 check stops on a phase, because two points that are 28 to 53 members apart swing with machine load. The plan already stops for the owner on exit 4. Check the load average first.
- Task 11: costs inside a member wall that are neither timed nor in P6's list: `resolve_child` before each child (0.20 to 0.31 s per child), the children's own bookkeeping, and some parent reads. Add them to the walls or name them in the evidence.
- Task 13: spec §4.4 item 1 says a corrupt parent gets "the same `state_conflict` gap as today". Today's code gives `legacy_member_unresolved`. The tests follow today's code. Show the owner a one-line spec amendment.
