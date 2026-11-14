# Pre-Dispatch Cost and Its Release Implementation Plan

**Approval:** Approved by the owner, 2026-11-14, with P1–P5 and P7–P11 as proposed and P6 changed (D1 below), as committed at `586b145`. This plan authorizes no SEC request and no live run.

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a1 — on plan completion, tick the stage and re-validate later stages against what shipped.

(The line above is the spec's §9 Rollout note, copied verbatim.)

**Goal:** Ship a reviewed native release on which a backfill starts its first member well before the 1,500 s dispatch cutoff at the growth allowance (450 registered members, 55 new), with offline evidence on the 2a release and the new release, and every Stage 2b member wall measured against 1,056 s.

**Architecture:** The work has five parts.

1. A per-type cache in front of `typing.get_type_hints` for record decoding (H6).
2. `SelectionChecks`, built by `select_work`, keeps the publish-call authority and the parent re-validations for one phase of one selection. It drops them when the discovery child returns or raises (H2, H3). Every other path passes no `checks` and runs as today (H4).
3. `reuse_exact_binding` validates only the registered members of its own source (H5).
4. Two evidence scripts under `specs/evidence/stage2a1/`: a replay of plan 8's two invocations from their own restored starting states, and the member-wall timing.
5. The release is built from clean `main` after the gate and the merge. The timings run on the installed releases. Both stop rules hold the live-config selection.

Code and the two scripts land on a feature branch in a worktree. They merge to `main` after the full gate, a whole-branch review and an owner checkpoint. The release, the timings, the selection and the amendments run on `main` in the main checkout.

**Tech Stack:** Python 3.14 (CPython 3.14.0, macOS arm64). PyArrow 25.0.1 Parquet. SQLite through `sqlite3`. Stdlib `unittest` under `packages/sec-edgar-ingest/tests/network_guard.py`. `uv` offline and locked. Installed releases under `releases/sha256=<id>/`.

**Spec:** [specs/sec-filing-index-pre-dispatch-cost.md](../sec-filing-index-pre-dispatch-cost.md) (Stage 2a1, committed at `003c516`). Its status line reads "Draft for owner review". The owner's approval is recorded in its §8, "Spec" (`:316`). Parent spec: [specs/sec-filing-index-ingestion-spec.md](../sec-filing-index-ingestion-spec.md). Inputs: the [diagnosis](../evidence/stage2a1/diagnosis/diagnosis.md), [plan 8](8-sec-filing-index-ingestion-spec.md) (halted evidence; Handoff, bullet "Task 5 halt (2026-11-06)"), [plan 7](completed/7-sec-filing-index-duplicate-key.md) (the release pattern), and the [Stage 2b evidence](../evidence/stage2b/pre-campaign.md).

## Global Constraints

Copied from the spec. Every task's requirements include this section.

- Offline. No SEC request and no live run. Nothing is written under `data/` or `backups/`. Every directory under `releases/` stays, `artifact-cache` included (spec §1, §6, §8 "Spec").
- H1: for the same store, intent and discovery result, the new release's selection equals the 2a release's selection, apart from the run context: the same members, jobs, already-complete captures, superseded members, gaps and counts, in the same order.
- H2: within one selection, while the computation succeeds, `_publish_calls` runs at most once before the discovery child and once after it, and each parent ref is re-validated (`read_parent`) at most once in each of those two phases.
- H3: a kept value never crosses a child execution. Every kept value is dropped when the discovery child returns or raises. A failure is never kept.
- H4: outside `select_work`, every check runs as today. The dispatch loop, `process_member`, `sibling_completion`, the finish step, `freeze_selection` and every low-level command use no kept value.
- H5: `reuse_exact_binding` validates only the registered members of the member's own source, and finds the same candidates, returns the same gaps in the same order, and writes the same binding as today.
- H6: record decoding computes each record type's hints once per process. Decoded values and error messages are unchanged.
- H7: no format changes. The new release continues 2a-origin pending work, and the 2a release continues work that the new release left pending.
- H8: parser and schema stay `sec-index-parser-v2` / `sec-index-v2`. No config key is added. The 3,600 s maximum and the 3,300 s launcher default are unchanged.
- H9: the release is built by `build_release` from clean committed `main`. The version stays `0.2.0`. `uv.lock` and the requirement lines of `uv export --package sec-edgar-ingest --no-dev --no-emit-workspace` are byte-identical to the 2a build inputs, with no platform member. The 2a release and older releases are retained.
- Anti-goals (spec §2.3): a selection that differs from the 2a release's apart from the run context; a kept value used after a child process ran, or a kept failure; a dispatched member, low-level command or finish step that skips a check it runs today; a record that decodes to a different value or a refusal with a different message.
- Run length: the 3,300 s launcher default with the 1,800 s reserve, so the cutoff is 1,500 s after the run starts. Plan 8 D6 does not carry over (spec §2.2, §6).
- Pre-dispatch bar (spec §6): the projected first dispatch on the new release must be before 1,500 s, and none before it on the 2a release. "If the projection exceeds 600 s, the stage stops before the live-config selection and reports to the owner."
- Member-wall stop rule (spec §6): "The limit is 1,056 s (O1, §8). If the longest member wall exceeds it, the Exit is not met. The stage stops before the live-config selection and asks the owner to choose one of three paths." The paths: approve a named limit backed by the measured wall; raise the reserve under the Stage 1b rule; add cost work and measure again.
- No cost work beyond spec §4. If the owner takes the third path, this plan is revised then.
- Order (spec §6): the gate passes on the branch, the branch merges to `main`, the release is built from `main`, and the evidence timings run on the installed release. A release that fails a bar stays in `releases/` and is never selected.
- Timing runs (spec §6): scratch copies outside `data/` and `backups/`, made with no writer running. Each timed run starts from a fresh copy. Every release interpreter runs as `<release>/venv/bin/python -I -B -X pycache_prefix=/dev/null`.
- Live-config selection changes only `runtime.release_manifest`. The reserve stays at 1,800 s unless the owner takes the second stop-rule path.
- Tests use stdlib `unittest` under `network_guard.py`. Write each test before its implementation.
- The full gate is `scripts/check-sec-edgar-ingest.sh`. The 2a gate took 4,417 s, so run it in the background.

Execution environment (planning facts, not spec text):

- Tasks 1–8 run on branch `stage2a1-pre-dispatch-cost` in the worktree `/Users/lowell/Projects/sec-edgar-local/.claude/worktrees/stage2a1-pre-dispatch-cost` (using-git-worktrees). Leave every other worktree and branch alone, `platform-stage1` and `claude/platform-stage1-1973ff` included.
- Tasks 9–13 run in the main checkout `/Users/lowell/Projects/sec-edgar-local` on `main`, after the Task 8 merge.
- `data/`, `backups/`, `releases/` and `logs/` exist only in the main checkout. From a worktree, reach them by absolute path. Never recreate them in a worktree. Put every scratch copy under `/Users/lowell/Projects/sec-edgar-local/logs/`.
- Never open the live `data/state.sqlite3` in SQLite. Open only clones. Make clones with `cp -c -R` (an APFS clone) while no writer runs.
- Shadow venv, created once in "Before Task 1" Step 3 (plan 7 method):

  ```bash
  WT=/Users/lowell/Projects/sec-edgar-local/.claude/worktrees/stage2a1-pre-dispatch-cost
  /Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14 -m venv /tmp/s2a1-venv
  printf '%s\n%s\n' "$WT/packages/sec-edgar-ingest/src" /Users/lowell/Projects/sec-edgar-local/.venv/lib/python3.14/site-packages > /tmp/s2a1-venv/lib/python3.14/site-packages/s2a1.pth
  /tmp/s2a1-venv/bin/python -I -c "import sec_edgar_ingest, pyarrow; print(sec_edgar_ingest.__file__, pyarrow.__version__)"
  printf '%s\n' '#!/tmp/s2a1-venv/bin/python' 'import sys' 'from sec_edgar_ingest.cli import main' 'sys.exit(main())' > /tmp/s2a1-venv/bin/sec-edgar-ingest
  chmod +x /tmp/s2a1-venv/bin/sec-edgar-ingest
  mkdir -p "$WT/releases" && ln -s /Users/lowell/Projects/sec-edgar-local/releases/artifact-cache "$WT/releases/artifact-cache"
  ```

  Expected: a path under `$WT/packages/sec-edgar-ingest/src`, and `25.0.1`.
- Test command, from the worktree root (`<target>` is a module, class or test):

  ```bash
  SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a1-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py <target> -v
  ```
- Branch interpreter for the two evidence scripts (Tasks 6–7): `/tmp/s2a1-venv/bin/python -I -B -X pycache_prefix=/dev/null`, with `--branch`, which skips `preflight_current`. It is not a release venv. Its results are checks, never evidence (spec §6).

## Review Focus

1. **`daily` and `reconcile` selections.** They run the same `select_work`, and only `backfill` was timed (spec §4.4 item 5). Each must give the same selection with and without kept values. Test: Task 4, `test_daily_and_reconcile_selections_equal_without_kept_values`.
2. **A resumed attempt whose `selection.json` exists.** `run_workflow` must freeze the saved selection and build no `SelectionChecks` (spec §4.4 item 4). Test: Task 4, `test_resumed_attempt_builds_no_selection_checks`.
3. **Two members of one source pinned to different snapshots, and a third member unbound.** Reuse must bind nothing and return the same gaps as today (H5, `len(candidates) != 1`). Test: Task 3, `test_two_pins_of_one_source_bind_nothing_as_today`.
4. **A first run on a store with no registered member and no publish history.** The selection must equal the selection without kept values, and the empty call list is computed once per phase (spec §4.4 item 3). Test: Task 4, `test_empty_store_selection_equal_and_counted`.
5. **A refusal after the cache is warm.** A record that fails to decode must give the same message before and after its type's hints are cached, for a nested record too (H6). Test: Task 1, `test_refusal_text_is_unchanged_after_the_cache_is_warm`.

## Decisions

- **D1** (owner, plan review, 2026-11-14): plan 9 approved as committed at `586b145`, with P1–P5 and P7–P11 as proposed. P6 changes: the band widens by 200 s, from 52.8 s to 252.8 s. So a longest measured wall above 803.2 s and not above 1,056 s also stops the stage for the owner. This is a plan-level change. No spec-level change. Owner's words: "Add an additional 200 s to P6. Otherwise approved." Applied in: P6, Task 11 Step 7, and every task through P1–P11.
- **D2** (owner, plan review, 2026-11-14): the plan's default for the `.pyc` question stands. The 100 files that the diagnosis left in the 2a and 1c release venvs stay. The 44 older files in the 1b venv are out of scope. Nothing under `releases/` is removed. Owner's words: "Otherwise approved." Applied in: the Handoff (spec §6).

## Defaults for owner review

Planning settled these points. Each is plan-level and is applied in the tasks as written. P1–P3 and P5 change a default of the handoff brief, on the evidence named. The owner approves or changes each at plan review.

- **P1 — Each replay runs under its own invocation's context, not a new run ID.** The brief proposed a new run ID and attempt ID. `freeze_selection` refuses that: `_validate_selection` raises "selection discovery call belongs to another workflow" when the recorded discovery call's `run_id` or `workflow_attempt_id` differs from the context (`workflows/results.py:258-261`, F2). So the harness loads the context from the attempt's `intent.json`. On the clone it removes the attempt's `selection.json` and `result.json` and resets both refs of its `WorkflowAttempt` row to null (`results.py:55-82`, `:348-368` refuse a second selection descriptor). Then it calls `run_workflow`, which selects again (`runner.py:105-111`). An observer raises at `workflow.after_selection` (`runner.py:111`), after `freeze_selection` and before the dispatch loop. The context's deadline (2026-11-06) is past, and nothing before that event reads it. The check gets stronger: the replay's `selection.json` must be byte-equal to the saved one. Applied in: Tasks 6 and 10.
- **P2 — A starting state is restored by a cut taken from a row diff.** The brief proposed removing one `WorkflowMember` and one `Binding` row for each new member. That does not restore the start. `bootstrap_legacy` re-projects every member of every parent that a `DiscoverySession` or `Attempt` row names (`workflows/legacy.py:98-136`, `:153-198`, F3). So the 53 members would return before discovery, and invocation 2 bound only 48 of them (F4). The harness diffs a live clone against a Task 3 backup clone, row by row and object by object, and assigns each added row to invocation 1 or 2. For the replayed invocation, it cuts the rows that its discovery child and its dispatcher wrote, and the replay dispatcher puts them back at the `discover` call. It cuts the members and bindings that the projection wrote, for good, because the replay writes them again. Any row that the diff cannot assign stops the task. Applied in: Tasks 6 and 10.
- **P3 — The two member counts come from plan 8's two invocations, both on live clones.** The brief proposed a clone of the Task 3 backup for the second count. The backup holds only the four v1 workflow runs (F1), so a replay there would select under v1 versions and time other work. The replays: invocation 2 (155 registered at the start, 53 new, 208 after) and invocation 1 (127, 28 new, 155 after; invocation 2's rows are also cut, for good). Only invocation 2's replay must be byte-equal to its saved selection. A difference there stops the task (HUMAN). Invocation 1's comparison is recorded only, because its clone keeps the `Source` rows that invocation 2's discovery later updated. Applied in: Tasks 6 and 10.
- **P4 — The projection model.** Each phase is fitted as a line through the new release's two replays: before discovery against the registered count at the start (127, 155); projection against the new members that reach the registry check; after discovery and freeze against the count after projection (155, 208). The projection at the allowance is 1 s + before(450) + 29 s + projection(55) + after(505) + freeze(505). The 1 s is the launcher's time before `run_workflow`, which the replay does not run. All 55 new members are assumed to reach the registry check. The before-discovery counts are only 28 apart, so each slope is clamped at zero or above and checked against the median per-member call time of its phase. A difference of more than a factor of 2 stops the task. On the 2a release, `inventory()` runs only for new members that pass reuse's early returns, so its per-new-member cost divides by that count, not by 53. The 2a release has one measured count. Its figure at the allowance is at least its measured time, because every phase grows with members. The evidence also gives a ratio-scaled figure. Applied in: Task 10.
- **P5 — Member walls: production calls as plan 8 timed them, engine work in-process.** The brief proposed timing engine work in-process. Planning found why no real child may run: `deployment_binding` leaves out the storage root (`storage/contracts.py:165-185`, F5), and `process_member` dispatches `collect` with the member's origin settings (`workflows/processing.py:32`, `:53-54`), which name the live `data/`. So the script keeps `order-timing.py`'s targets, order and production calls on a backup clone, and adds, per member, in-process on the new release:
  - before the transform: `sibling_completion`, `read_member`, `WorkflowMembers.replay` and `evaluate_member`;
  - after the publish: `evaluate_member`, `validate_capture` of its capture twice (once in `process_member`, once in `registry.record`), `read_member`, and `read_etl_result` of the transform and publish results twice;
  - the `collect` body of a bound member: `objects.verify` of its pinned raw snapshot and the state reads of `collection.py:192-200`;
  - three child starts. Each start is the median of five runs of a fixed probe (import the CLI, `load_config`, `preflight_current`). `transform` and `publish` use the new release and the scratch config. `collect` runs on the release that `resolve_child` picks from the member's origin context (`runtime.py:572-580`), with a config built from that origin context's effective config and the scratch storage and logging roots: an older release refuses the v2 scratch config. Member IDs are hashes, so a member that Stage 2b discovers may sort first for its source. So the `collect` start of a target is the largest median over the origin releases of every registered member of its source on a live clone, and the evidence names that release.

  Following the brief, the engine work is added once per member. Steps 7 and 9 keep plan 8's publish-only walls. Applied in: Tasks 7 and 11.
- **P6 — Unmeasured wall terms and a stop band.** Three terms cannot be measured offline: the full per-call child-result validation inside `validate_member_evidence` (run twice), the dispatcher's call and execution writes, and `collect`'s attempt bookkeeping. P5 measures the parts it can reach. The 2026-07-01 wall sits within a few percent of the limit (spec §8, O1). So a longest measured wall above 803.2 s but not above 1,056 s also stops the stage for the owner, as under the stop rule. The band is 252.8 s: 5 % of 1,056 s (52.8 s) plus the 200 s that the owner added at plan review (D1). Applied in: Task 11.
- **P7 — The kept-value interface and its test seam.** `SelectionChecks` in `workflows/selection_checks.py`, as in Task 2's Interfaces. It looks up `completion._publish_calls` and `provenance.read_parent` at call time, so a counting wrapper sees each computation. `select_work` builds it through the name `runner.SelectionChecks` and accepts `None` from that name. With `None`, every function runs its `checks is None` path, which is today's code. So the oracle "without kept values" of spec §5 items 1–2 is `patch('sec_edgar_ingest.workflows.runner.SelectionChecks', lambda *args: None)`. A test double that keeps nothing would share the new code path and could hide a plumbing fault, so the plan uses none. Applied in: Tasks 2 and 4.
- **P8 — The package version stays `0.2.0`.** The locked inputs stay byte-identical to the 2a build inputs at revision `32863852ce57f1da99db4720bd1c729727b4ec0c` (H9). The release ID changes through the Git revision and the wheel. Applied in: Tasks 8 and 9.
- **P9 — The 2a interpreter in gate tests.** `support_release.TWO_A_REVISION = '32863852ce57f1da99db4720bd1c729727b4ec0c'` builds the 2a application with `origin_release`, as plan 7 P9 did for 1c. One extra evidence run uses the installed `e49d3ba8…` through `SEC_LOCAL_2A_RELEASE` (spec §5 item 7). Applied in: Tasks 5 and 8.
- **P10 — Stop rule for existing tests.** If an existing test fails because of this change, stop and ask. Never weaken a test. Applied in: every code task.
- **P11 — A branch check before the merge.** Task 6 runs invocation 2's replay once on the branch code, as spec §6 allows. It catches an H1 failure before a release is built. Applied in: Task 6.

### Question for plan review

- **The `.pyc` files in the release venvs.** The diagnosis left 100 files, 50 each in the 2a and 1c venvs (`diagnosis.md:249-255`; list in `specs/evidence/stage2a1/diagnosis/outputs/pyc-created-2026-11-13.txt`). The 1b venv holds 44 older ones from 2026-10-29. They are older and out of scope unless the owner includes them. Release verification skips `__pycache__` (`runtime.py:476`). Default: leave all of them. A removal deletes files under `releases/`, so it needs the owner's yes. Answered at plan review: the default stands (D2). The answer goes into the Handoff (spec §6).

## Facts established while planning (read-only, 2026-11-14)

F1 and F4 come from a throwaway clone of the diagnosis's `pristine` copy, which was deleted afterwards.

- **F1 — Workflow runs in the live store.** Six `WorkflowAttempt` rows exist. Four are v1 backfills (2026-10-29 and 2026-10-31) and are also in the Task 3 backup. Two are v2: invocation 1 (`0746b217-d4ca-4f1d-9b05-d0c447b734ce`, attempt `6efe8c93-e50a-434f-b209-4128936e09e7`) and invocation 2 (`bdefaa5d-856d-4bc4-a621-018e66b6ef1e`, attempt `625ccd33-4701-4e4b-ac0c-a43c98d39e91`). Both are pinned on 2026-11-06, and both have a selection and a result ref.
- **F2 — A recorded discovery result belongs to its own workflow.** `results.py:258-261` requires the call's template `run_id` and `workflow_attempt_id` to equal the context's. `results.py:290-300` requires the session's `pinned_on` and endpoint to equal the context's.
- **F3 — `bootstrap_legacy` registers members from discovery rows.** It retains every parent named by a `DiscoverySession` revision (`legacy.py:98-136`) or by an `Attempt` result (`:153-187`), and projects all of their sources (`:189-198`). Invocation 2's session (key `b253f970…`) names parent `bd4d52a98339…`. Invocation 1's session (key `8c40fde4…`) names parent `06db48619772…`.
- **F4 — Members and bindings written by plan 8.** Parent `bd4d52a98339…` has 53 registered members, with 48 `Binding` rows keyed by their member IDs (`source_workset_id`). Parent `06db48619772…` has 28 members and 28 bindings. The state database has no delete call. The diagnosis removed rows with `DELETE FROM records WHERE partition LIKE '%:<Kind>' AND …` on a clone (`specs/evidence/stage2a1/diagnosis/scripts/profile_pieces.py:57-62`).
- **F5 — Origin settings name the live root.** `deployment_binding` holds the acquisition mode, SEC policy and coordination only (`storage/contracts.py:165-185`). So `Dispatcher.execute` accepts origin settings with another root. `resolve_child` runs the origin release's interpreter (`runtime.py:572-580`).
- **F6 — A bound member's `collect` sends nothing.** `collect_member` returns the pinned snapshot after `_verify_snapshot` (`collection.py:192-200`).
- **F7 — Invocation 2's recorded discovery call** is under `data/objects/runs/sec/bdefaa5d-856d-4bc4-a621-018e66b6ef1e/backfill/625ccd33-4701-4e4b-ac0c-a43c98d39e91/children/wf-9d6e24b5586f3b747981db4ba6d1db6ae62fd34e/call.json`.
- **F8 — Releases.** `releases/` holds `sha256=49b7a2ed…`, `sha256=900952a8…`, `sha256=9fa189a0…`, `sha256=aa8de1ac…`, `sha256=c4de77b8…`, `sha256=d718ae5f…`, `sha256=e49d3ba8…` and `sha256=fc68adef…`, plus `artifact-cache` and `task14-guard-proofs`. The 2a release was built at revision `32863852ce57f1da99db4720bd1c729727b4ec0c`.
- **F9 — The live config** selects `e49d3ba8…` with effective-config SHA-256 `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733`, floor 480 s and reserve 1,800 s (plan 7, Handoff). Live policy requires `execution.max_run_seconds` 3,600 (`config.py:266-267`).
- **F10 — Store hash lists.** `specs/evidence/stage2a1/diagnosis/outputs/live-data-before.sha256` (5,452 files) and `backup-before.sha256` (5,270 lines, the outer `state.sqlite3` among them). Both were made from the project root with paths prefixed `data/` or `backups/…/data-raw/`.
- **F11 — The 2a gate** ran 1,187 tests in 75 modules (`specs/evidence/stage2a/gate.md:18-19`).

## File structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/sec_edgar_ingest/models.py` | `record_type_hints` cache | 1 |
| `src/sec_edgar_ingest/workflows/selection_checks.py` (new) | `SelectionChecks` | 2 |
| `src/sec_edgar_ingest/workflows/completion.py`, `provenance.py`, `members.py`, `legacy.py` | optional `checks` keyword | 2 |
| `src/sec_edgar_ingest/workflows/members.py`, `runner.py` (`reuse_exact_binding`) | source filter | 3 |
| `src/sec_edgar_ingest/workflows/runner.py` (`select_work`) | one `SelectionChecks` per selection | 4 |
| `tests/test_pre_dispatch_cost.py` (new) | Tasks 1–4 tests | 1–4 |
| `tests/support_selection.py` (new) | fixture stores for Task 4 | 4 |
| `tests/support_release.py`, `tests/test_release_2a1.py` (new) | `TWO_A_REVISION`, H7 | 5 |
| `specs/evidence/stage2a1/predispatch/replay.py` (new) | diff, cut, replay, projection | 6, 10 |
| `specs/evidence/stage2a1/walls/member-walls.py` (new) | member walls | 7, 11 |
| `specs/evidence/stage2a1/gate.md`, `release.md`, `predispatch.md`, `walls.md` (new) | evidence | 8–12 |
| `conf/sec-edgar-local.json` | `runtime.release_manifest` | 12 |
| `specs/sec-filing-index-ingestion-spec.md`, `docs/runbooks/local-ingestion.md`, `docs/runbooks/release-upgrades.md` | spec §7 amendments | 13 |

All `src` and `tests` paths are under `packages/sec-edgar-ingest/`.

---

## Before Task 1

- [x] **Step 1: Plan review (HUMAN).** The owner reviews the plan, answers P1–P11 and the `.pyc` question. Log each answer in `## Decisions`, in the owner's words. The approval of the plan is D1, in the format of plan 7 D1. Apply each plan-level change, and re-run the writing-plans Self-Review on what changed. Record the approval on the **Approval** line.
- [x] **Step 2: Commit the review** on the branch that holds this plan.

```bash
git add specs/plans/9-sec-filing-index-pre-dispatch-cost.md
git commit -m "docs(plans): record the owner review of plan 9"
```

- [ ] **Step 3: Create the worktree and the shadow venv.** Use the using-git-worktrees skill for branch `stage2a1-pre-dispatch-cost` at `.claude/worktrees/stage2a1-pre-dispatch-cost`, from `main` with this plan merged. Then run the shadow-venv commands in Global Constraints.

---

### Task 1: Record type-hints cache (H6; spec §5 item 6)

**Files:**
- Modify: `src/sec_edgar_ingest/models.py` (`record_from_mapping` `:226-240`, `validate_record_fields` `:279-282`)
- Create: `tests/test_pre_dispatch_cost.py`, class `TypeHintsCacheTests`

**Interfaces:**
- Produces: `models.record_type_hints(record_type: type) -> Mapping[str, object]`. It is wrapped in `functools.cache`, and it returns `types.MappingProxyType(get_type_hints(record_type))`. It calls `get_type_hints` through the module global, so a test can count calls. A raise is not cached. `record_from_mapping` and `validate_record_fields` use it in place of their `get_type_hints` calls.

- [ ] **Step 1: Write the failing tests** in class `TypeHintsCacheTests`:
  - `test_cached_hints_equal_get_type_hints_for_every_record_type`: import every module under `sec_edgar_ingest` with `pkgutil.walk_packages`. Collect each class that `dataclasses.is_dataclass` accepts and whose `__module__` is that module. For each, `dict(record_type_hints(t)) == typing.get_type_hints(t)`. Assert that more than 30 types were checked.
  - `test_cached_hints_cannot_be_changed`: assigning to `record_type_hints(Source)['x']` raises `TypeError`.
  - `test_hints_are_computed_once_per_type`: call `record_type_hints.cache_clear()`, patch `models.get_type_hints` with `wraps=` the original, and decode one `Source` mapping three times with `Source.from_mapping`. The wrapper saw `Source` once.
  - `test_refusal_text_is_unchanged_after_the_cache_is_warm` (Review Focus 5): after `cache_clear()`, decode a `RunContext` mapping with one wrong field type, and a `CommandResult` mapping whose nested `Error` has an unknown key. Record each `ValueError` text. Decode both again. Each text is equal.
- [ ] **Step 2: Run** `test_pre_dispatch_cost.TypeHintsCacheTests` and confirm that it fails with `ImportError` on `record_type_hints`.
- [ ] **Step 3: Implement the Interfaces above.**
- [ ] **Step 4: Run** `test_pre_dispatch_cost test_state test_worksets test_etl_contracts test_workflow_contracts test_validation test_config`. Expected: `OK`.
- [ ] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/models.py packages/sec-edgar-ingest/tests/test_pre_dispatch_cost.py
git commit -m "perf(models): cache record type hints once per type"
```

---

### Task 2: `SelectionChecks` and the optional `checks` keyword (H2, H3; spec §4.1, §4.3, §5 item 3)

**Files:**
- Create: `src/sec_edgar_ingest/workflows/selection_checks.py`
- Modify: `src/sec_edgar_ingest/workflows/completion.py` (`capture_parent_provenance` `:101`, `capture_member_provenance` `:356`, `_obligations` `:590`, `outstanding_repairs` `:662`, `evaluate_member` `:812`)
- Modify: `src/sec_edgar_ingest/workflows/provenance.py` (`project_member` `:187`, `read_member` `:201`, `transfer_binding` `:216`)
- Modify: `src/sec_edgar_ingest/workflows/members.py` (`inventory` `:15`, `completed` `:131`), `workflows/legacy.py` (`reconstruct_parent` `:38`, `bootstrap_legacy` and its `retain` `:68-198`)
- Test: `tests/test_pre_dispatch_cost.py`, class `SelectionChecksTests`

**Interfaces:**
- Produces, in `workflows/selection_checks.py`:
  - `PublishCall = tuple[Mapping[str, object], TransformedWorkset]`: one checked publish call and its decoded transformed input.
  - `class SelectionChecks`, with `__init__(self, store, objects)` and three methods:
    - `publish_calls(self) -> tuple[PublishCall, ...]`. The first call runs `completion._publish_calls(store, objects)`, then `decode_transformed(objects.read(call['input_ref']))` once for each call. Later calls return the kept tuple.
    - `parent(self, ref: str) -> SourceWorkset` returns `provenance.read_parent(ref, store, objects)`. Results are kept by `ref`.
    - `renew(self) -> None` drops every kept value.
  - Both computations look up their module attribute at call time. A value is kept only after its computation returns. A raise propagates, and nothing is kept.
- Produces: a keyword-only `checks: SelectionChecks | None = None` on `_obligations`, `outstanding_repairs`, `evaluate_member`, `capture_member_provenance`, `capture_parent_provenance`, `read_member`, `project_member`, `transfer_binding`, `WorkflowMembers.inventory`, `WorkflowMembers.completed`, `reconstruct_parent` and `bootstrap_legacy`. Each passes it on to the calls listed here. With `checks`, every `read_parent` call becomes `checks.parent(ref)`, and `_obligations` iterates `checks.publish_calls()` in place of `_publish_calls` and its per-call decode. With `None`, each function runs today's code unchanged: `_obligations` still decodes each input lazily inside its loop (H4).
- Import `selection_checks` in `completion.py` only under `TYPE_CHECKING`, so there is no import cycle.

- [ ] **Step 1: Write the failing tests** in class `SelectionChecksTests`. Build stores with `support_workflows.CommandHarness` and `simple_pack`, plus the setups of the existing tests named below.
  - `test_publish_calls_are_kept_until_renew`: with `completion._publish_calls` patched `wraps=`, two `publish_calls()` calls make one computation. After `renew()`, the next call makes a second. The kept tuple equals `tuple((c, decode_transformed(objects.read(c['input_ref']))) for c in completion._publish_calls(store, objects))`.
  - `test_a_failed_computation_is_not_kept`: patch `completion._publish_calls` to raise `Conflict` once and then return. The first `publish_calls()` raises. The second returns, after two computations. Do the same for `parent` with `provenance.read_parent`.
  - `test_kept_values_equal_fresh_ones_after_each_write_kind` (spec §4.3, §5 item 3): keep `publish_calls()` and `parent(ref)`. Then make, in turn, the writes of `_obligations` (repair rows and a resolution, from the setup of `test_workflow_completion.test_fresh_attempt_resolves_repair_without_rewriting_original_attempt`), `project_member` and `transfer_binding`. After each, the kept values equal a fresh `completion._publish_calls` with decoded inputs and a fresh `provenance.read_parent`.
  - `test_a_recovered_parent_passes_on_the_next_read` (spec §5 item 3): use the setup of `test_workflow_legacy.test_crash_before_parent_write_recovers_all_original_units`. `checks.parent(ref)` raises before `reconstruct_parent` writes its `WorkflowParentRecovery` row. After the write, the same `checks` returns the parent.
  - `test_without_checks_each_call_recomputes`: two `evaluate_member` calls with no `checks` make two `_publish_calls` computations (H4).
- [ ] **Step 2: Run** `test_pre_dispatch_cost.SelectionChecksTests` and confirm the failures.
- [ ] **Step 3: Implement the Interfaces above.**
- [ ] **Step 4: Run** `test_pre_dispatch_cost test_workflow_completion test_member_completion test_workflow_provenance test_workflow_legacy test_workflow_runner`. Expected: `OK`. Apply P10 to any other failure.
- [ ] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows packages/sec-edgar-ingest/tests/test_pre_dispatch_cost.py
git commit -m "perf(workflows): add per-phase selection checks behind an optional keyword"
```

---

### Task 3: Reuse validates only its own source (H5; spec §4.4 items 6–7, §5 item 5)

**Files:**
- Modify: `src/sec_edgar_ingest/workflows/members.py` (new method), `workflows/runner.py` (`reuse_exact_binding` `:25-61`)
- Test: `tests/test_pre_dispatch_cost.py`, class `ReuseSourceFilterTests`

**Interfaces:**
- Consumes: Task 2 (`checks`).
- Produces:
  - `WorkflowMembers.of_source(self, source: Mapping, *, checks: SelectionChecks | None = None) -> tuple[Mapping, ...]`. It scans `WorkflowMember` rows. It reads a row's `source` only when the row's value is a `dict`, and skips the row unless that `source` equals `source`. It validates each remaining row with `read_member` (with `checks`), skips a row that raises one of `inventory()`'s error types, and sorts by `inventory()`'s key.
  - `reuse_exact_binding(value: Mapping, store, objects, *, checks: SelectionChecks | None = None) -> tuple[Error, ...]` uses `of_source(value['source'], checks=checks)` in place of `inventory()` and its source filter. Its `read_member` and `transfer_binding` calls get `checks`. Nothing else changes. `sibling_completion` keeps calling it without `checks`.

- [ ] **Step 1: Write the failing tests** in class `ReuseSourceFilterTests`. The oracle is `_reuse_today`, a copy in the test module of `reuse_exact_binding` at `003c516` (`runner.py:25-61`). Each case runs the oracle and the new function on two copies of one fixture store (`shutil.copytree`). It compares the gap mappings in order and the `Binding` rows after the call. Corrupt rows as `test_workflow_runner.test_corrupt_retained_registry_and_receipt_do_not_block_valid_siblings` does.
  - `test_same_result_with_a_corrupt_member_of_another_source` (spec §5 item 5).
  - `test_same_result_with_a_corrupt_member_of_the_same_source` (spec §5 item 5).
  - `test_same_result_with_a_corrupt_reuse_pin` (spec §5 item 5): the gap text is `retained reuse pin is corrupt: …` in both.
  - `test_same_result_with_a_malformed_member_row` (spec §4.4 item 7): a `WorkflowMember` value that is a list.
  - `test_two_pins_of_one_source_bind_nothing_as_today` (Review Focus 3): two members of one source pinned to different snapshots, and a third unbound member. Neither function writes a binding, and the gaps are equal.
  - `test_reuse_validates_only_its_own_source`: with every module's `read_member` wrapped to count, a store with 3 members of the value's source and 5 of other sources makes 4 `read_member` calls (the value itself plus 3).
  - `test_sibling_completion_never_runs_the_full_inventory`: with `WorkflowMembers.inventory` patched to raise `AssertionError`, `sibling_completion` for a complete sibling returns its processed member.
- [ ] **Step 2: Run** `test_pre_dispatch_cost.ReuseSourceFilterTests` and confirm the failures.
- [ ] **Step 3: Implement the Interfaces above.**
- [ ] **Step 4: Run** `test_pre_dispatch_cost test_workflow_runner test_workflow_drain test_reconcile_workflow test_workflow_provenance`. Expected: `OK`.
- [ ] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows packages/sec-edgar-ingest/tests/test_pre_dispatch_cost.py
git commit -m "perf(workflows): validate only the member's own source in reuse"
```

---

### Task 4: `select_work` computes store-wide checks once per phase (H1, H2, H4; spec §4.2, §4.4, §5 items 1, 2, 4)

**Files:**
- Modify: `src/sec_edgar_ingest/workflows/runner.py` (`select_work` `:184-296`)
- Create: `tests/support_selection.py`
- Test: `tests/test_pre_dispatch_cost.py`, classes `SelectionEqualityTests`, `SelectionCountTests`, `UnchangedPathTests`

**Interfaces:**
- Consumes: Tasks 2 and 3.
- Produces: `select_work` keeps its signature and order. It builds one `checks = SelectionChecks(store, objects)`, through the name `runner.SelectionChecks`. Phase 1 passes `checks` to `bootstrap_legacy`, `inventory`, `completed` and `evaluate_member`. `checks.renew()` runs in a `finally` around `dispatcher.execute('discover', …)`. Phase 2 uses `checks.parent(parent_ref)` at `:219`, and passes `checks` to `project_member`, `reuse_exact_binding`, `evaluate_member`, `capture_parent_provenance` and `capture_member_provenance`. When the name returns `None` (P7), `select_work` skips `renew()` and calls `read_parent` at `:219` as today. `run_workflow`, `sibling_completion`, `process_member`, `freeze_selection` and the low-level commands do not change.
- Produces, in tests (`tests/support_selection.py`):
  - `NO_CHECKS = patch('sec_edgar_ingest.workflows.runner.SelectionChecks', lambda *args: None)`: the oracle "without kept values" (P7).
  - `support_selection.scenario(root: Path, name: str) -> CommandHarness` for the names `finished`, `pending`, `superseded`, `repair_obligation`, `corrupt_member`, `corrupt_parent`, `corrupt_publish_call` and `empty`. Each reuses the setup of an existing test: `superseded` from `test_reconcile_workflow.test_superseded_gated_member_completes_on_the_following_reconcile`, `repair_obligation` from `test_workflow_completion.test_fresh_attempt_resolves_repair_without_rewriting_original_attempt` (before its repair), `corrupt_publish_call` from `test_workflow_completion.test_corrupt_begun_checked_call_blocks_completion`, `corrupt_parent` from the session corruption of `test_workflow_completion.test_historical_provenance_rejects_session_and_registry_corruption` (spec §4.4 item 1), and `corrupt_member` from `test_workflow_runner.test_corrupt_retained_registry_and_receipt_do_not_block_valid_siblings`.
  - `support_selection.registered_store(root: Path, members: int) -> CommandHarness`: a fixture `daily` run over `members` daily sources whose deadline leaves no dispatch time, as `test_workflow_runner.test_deadline_after_selection_records_undispatched_units_without_child_work` does. Every member is registered, and none is processed.
  - `support_selection.select_twice(harness, command: str, *, discovery_fails: bool = False) -> tuple[bytes, bytes]`: two copies of the harness store, one `select_work` with real checks and one under `NO_CHECKS`, under the same pinned context and intent and the fixture `Dispatcher`. Both run inside `support_process.checked_clock(root, <one fixed instant>)`, so their discovery children see the same clock. It returns `canonical_json` of each selection. With `discovery_fails`, the dispatcher's `discover` raises the `ChildUnfinished` of `test_workflow_runner.test_no_result_discovery_keeps_required_ledger_and_older_pending_jobs`. If the two selections differ only in a value that a discovery child takes from the wall clock, stop and ask (P10).

- [ ] **Step 1: Write the failing tests.**
  - `SelectionEqualityTests.test_selection_equal_with_and_without_kept_values` (spec §5 item 1): one `subTest` per scenario name, plus `pending` with `discovery_fails=True`. The two byte strings are equal. The test fails until `select_work` builds `runner.SelectionChecks`.
  - `SelectionEqualityTests.test_daily_and_reconcile_selections_equal_without_kept_values` (Review Focus 1): `select_twice` on `scenario(root, 'pending')` for `daily` and for `reconcile`.
  - `SelectionCountTests.test_counts_per_phase_at_1_10_50_members` (spec §5 item 2): on `registered_store(root, n)` for n in 1, 10 and 50, one more `daily` selection. Count `completion._publish_calls` and, by ref, each module's `read_parent` (`provenance`, `completion`, `members`, `legacy`, `runner`). Split the counts at the dispatcher's `discover` entry and return. Each phase has at most one `_publish_calls` and at most one `read_parent` per ref, and the totals do not grow with n.
  - `SelectionCountTests.test_empty_store_selection_equal_and_counted` (Review Focus 4): on `scenario(root, 'empty')`, the selections are equal, and each phase computes `_publish_calls` once.
  - `SelectionCountTests.test_renew_runs_when_discovery_returns_and_when_it_raises` (H3): a spy on `SelectionChecks.renew` is called once in each case, and the first phase-2 `publish_calls` recomputes.
  - `UnchangedPathTests.test_dispatch_and_finish_use_no_kept_value` (spec §5 item 4): wrap `evaluate_member`, `read_member`, `_obligations`, `reuse_exact_binding` and `read_parent` to record the `checks` argument. Patch each name in every module under `sec_edgar_ingest.workflows` that binds it, because these functions are imported by name. Run `run_workflow` on `simple_pack` with members that dispatch, as `RunnerTests.run_parent` does, then `write_workflow_result`. At least one `evaluate_member` call and one `read_member` call are recorded after the observer event `workflow.after_selection`, and every call recorded after it has `checks is None`. So does every call under `CommandHarness.invoke('transform', …)` and `invoke('publish', …)`.
  - `UnchangedPathTests.test_resumed_attempt_builds_no_selection_checks` (Review Focus 2): patch `runner.SelectionChecks` to raise `AssertionError`. `run_workflow` on an attempt whose `selection.json` exists completes.
- [ ] **Step 2: Run** the three classes and confirm the failures.
- [ ] **Step 3: Implement the Interfaces above.**
- [ ] **Step 4: Run** `test_pre_dispatch_cost test_workflow_runner test_workflow_drain test_workflow_selection_v1 test_reconcile_workflow test_workflow_results test_workflow_acceptance test_local_workflow_contracts` in the background. Expected: `OK`.
- [ ] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/tests/support_selection.py packages/sec-edgar-ingest/tests/test_pre_dispatch_cost.py
git commit -m "perf(workflows): compute selection's store-wide checks once per phase"
```

---

### Task 5: Two-way continuation with the 2a release (H7; spec §4.5, §5 item 7; P9)

**Files:**
- Modify: `tests/support_release.py` (`TWO_A_REVISION`)
- Create: `tests/test_release_2a1.py`

**Interfaces:**
- Consumes: Task 4. `support_release.origin_release(project, cache, revision)`, `support_release.proof_releases(project, cache)` (its second release is the current code) and `workflow_proof.upgrade_sequence(output, a_manifest, b_manifest)`.
- Produces: `TWO_A_REVISION = '32863852ce57f1da99db4720bd1c729727b4ec0c'  # source revision of the 2a release e49d3ba8…`. The env var `SEC_LOCAL_2A_RELEASE` replaces the built 2a release with the installed `release.json`.

- [ ] **Step 1: Write the tests** in class `TwoReleaseTests`, set up as `test_release_2a.TwoReleaseTests.setUpClass` with the 2a release in place of the 1c release:
  - `test_new_release_continues_2a_origin_pending_work`: `upgrade_sequence` with the 2a release as A and the current release as B, with no `a_schema`. Assert what `test_release_2a.test_v2_release_continues_1c_origin_pending_work` asserts (`:117-147`): `exit == 0`; each case `b_exit == 0` and `rows > 0`; the A-child expectation; the process and checkout-guard records.
  - `test_2a_release_continues_new_origin_pending_work`: the same, with the current release as A and the 2a release as B.
- [ ] **Step 2: Run** `test_release_2a1` in the background. Expected: 2 tests, `OK`. If a continuation fails, stop and ask: H7 is a requirement, and a fix is not planned.
- [ ] **Step 3: Commit.**

```bash
git add packages/sec-edgar-ingest/tests/support_release.py packages/sec-edgar-ingest/tests/test_release_2a1.py
git commit -m "test(release): prove two-way continuation between the 2a release and this change"
```

---

### Task 6: Pre-dispatch replay script and the branch check (spec §6 "Pre-dispatch measurement"; P1–P4, P11)

**Files:**
- Create: `specs/evidence/stage2a1/predispatch/replay.py`, `specs/evidence/stage2a1/predispatch/diff.json`, `specs/evidence/stage2a1/predispatch/branch-check.json`

**Interfaces:**
- Produces: the script's command line. The script runs on the 2a interpreter as well as the new one (Task 10). So it imports only names that the 2a release has, and looks up names that only the new code has (`WorkflowMembers.of_source`, `runner.SelectionChecks`) with `getattr`. Every subcommand refuses a `<root>` under `/Users/lowell/Projects/sec-edgar-local/data` or `…/backups`, after `Path.resolve()`. It opens a store only by explicit path and its stored binding, as `order-timing.py` does (`REGISTRY_PATH`, `LocalObjectStore`, `LocalStateStore`, `create=False`). It never builds a stores object from settings.
  - `replay.py diff <live-root> <backup-root> <diff.json>`: read-only. It opens both `state.sqlite3` files with a `mode=ro` URI. It lists every row that is added or changed in `<live-root>` by `(partition, key)`, with the SHA-256 of each value but never the value. It assigns each added row to invocation 1 or 2 (F1) by these fields: the context `run_id` (`Attempt`, `WorkflowAttempt`, `WorkflowChildCall`, `WorkflowChildExecution`, `QueueTicket`, `TransportAttempt`); the `discovery_id` (`DiscoverySession`, `DirectoryProgress`); the `parent_ref` (`WorkflowMember`); the member ID (`Binding.source_workset_id`); the earliest invocation whose parent lists the source (`Source`). It also lists the added object paths, for the record only: objects are not assigned and not cut, apart from the two files named under `cut`. For each invocation it records its saved `selection.json` SHA-256 and byte count. It exits 2 if a row is unassigned, or if a changed row's kind is not `Source`, `_Lease`, `QueueTicket` or `TransportAttempt`. Either exit stops the task: report it and ask.
  - `replay.py cut <root> <diff.json> {1,2} <saved-rows.json>`: on a fresh live clone. For the chosen invocation, it saves to `<saved-rows.json>` and deletes the rows that its discovery child and dispatcher added: `DiscoverySession`, `DirectoryProgress`, the discover `Attempt`, `WorkflowChildCall`, `WorkflowChildExecution`, `QueueTicket`, `TransportAttempt`, and the `Source` rows that the diff assigns to it. It deletes its added `WorkflowMember` and `Binding` rows for good. It copies `selection.json` to `<saved-rows.json>`'s folder as `saved-selection-<n>.json`, deletes `selection.json` and `result.json`, and sets `selection_ref` and `result_ref` of its `WorkflowAttempt` row to null. For invocation 1 it also deletes, for good, every row that the diff assigns to invocation 2, except invocation 2's `WorkflowAttempt` row. Rows are deleted with raw SQLite on the clone (F4). It then checks the registered count: 155 for invocation 2, 127 for invocation 1. If the count differs, it exits 2. `<saved-rows.json>` and the saved selection always stay in the scratch folder `$W`, and are never committed.
  - `replay.py run <root> <saved-rows.json> {1,2} <out.json> [--branch]`: unless `--branch`, it calls `preflight_current(Path(sys.prefix).parent / 'release.json')`, the manifest of the release whose venv runs it. It loads the context from the attempt's `intent.json`, the intent from the same file, and `settings = Settings.from_mapping(context.to_mapping()['effective_config'])`. Its dispatcher accepts exactly one call, `execute('discover', 'discover', settings, flags)`, with the flags of the recorded call's intent. That call inserts the saved discovery rows with `store.insert` and returns `CheckedChild(call, call['result_ref'], read_child(call, store, objects))` for the recorded `call.json` (F7 for invocation 2). Any other call raises. It calls `run_workflow` with an observer that raises a private `Stop` at `workflow.after_selection`. It records phase marks: run start; `discover` entry and return; the last return of `runner.reuse_exact_binding`; `runner.freeze_selection` entry; and the observer event. Each mark is a wrapper on the module attribute. From the marks it gives five phases: before discovery, discovery (replayed), projection, after discovery and freeze. Inside the phases it records each call time of `WorkflowMembers.completed`, `evaluate_member`, `project_member`, `reuse_exact_binding` and `capture_member_provenance`, through wrappers on the module attributes. It also records: the registered count at the start and after projection; the new members; the new members that reached the registry check (`WorkflowMembers.inventory` calls inside reuse on the 2a release, `WorkflowMembers.of_source` on the new release); the `os.getloadavg()` at start and end; the release ID or `branch`; the frozen `selection.json` SHA-256 and byte count; and whether it equals the saved selection. If it does not, the script writes the top-level fields that differ. It then exits 3 for invocation 2, and 0 for invocation 1, whose comparison is recorded only (P3). The time to the first dispatch is 1 s plus the sum of the five phases, with the replayed discovery replaced by 29 s. The 1 s is the launcher's time from `started_at` to `run_workflow`, which the replay does not run: in invocation 2, `started_at` was 18:31:08.26Z (F1) and `intent.json` was written at 18:31:08Z (diagnosis §3).
  - `replay.py project <new-1.json> <new-2.json> <2a-2.json> <projection.json>`: the P4 fits, with each slope clamped at zero or above. For each fitted phase it compares the slope with the median per-member call time of that phase. If they differ by more than a factor of 2, it exits 4 and projects nothing. Otherwise it gives the figure at the allowance (450 registered, 55 new, 29 s discovery, 1 s launcher) for the new release, and the 2a release's measured and ratio-scaled figures. It compares each with 1,500 s, and the new release with 600 s.

- [ ] **Step 1: Write `replay.py`** to the Interfaces above. Then run `releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/venv/bin/python -I -B -X pycache_prefix=/dev/null <worktree>/specs/evidence/stage2a1/predispatch/replay.py --help` from the main checkout. Expected: exit 0, so the script imports on the 2a release. Fix any import here, on the branch.
- [ ] **Step 2: Confirm that no writer runs.** Run `pgrep -fl -- '-m sec_edgar_ingest|scripts/sec-edgar-local|local-bootstrap|local_bootstrap|order-timing|member-walls|replay.py'`. Expected: no output. If a writer runs, stop and ask.
- [ ] **Step 3: Check `data/` against the diagnosis's list, then make the clones.**

```bash
cd /Users/lowell/Projects/sec-edgar-local
W=/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-branch-$(date -u +%Y%m%dT%H%M%SZ)
mkdir "$W"
find data -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 > "$W/live-data-before.sha256"
diff <(LC_ALL=C sort "$W/live-data-before.sha256") <(LC_ALL=C sort specs/evidence/stage2a1/diagnosis/outputs/live-data-before.sha256) && echo data-as-diagnosed
cp -c -R data "$W/live" && cp -c -R data "$W/replay-2" && cp -c -R backups/stage2b-pre-campaign-20261106T174241Z/data-raw "$W/backup"
echo "$W"
```

Expected: `data-as-diagnosed`. If the lists differ, stop and ask.
- [ ] **Step 4: Run `diff`** from the worktree root, with the branch interpreter and Step 3's `$W`: `replay.py diff "$W/live" "$W/backup" specs/evidence/stage2a1/predispatch/diff.json`. Expected: exit 0. Invocation 1 has 28 `WorkflowMember` and 28 `Binding` rows, and invocation 2 has 53 and 48 (F4). Each has one `DiscoverySession`, one `WorkflowAttempt`, one `WorkflowChildCall` and one discover `Attempt`.
- [ ] **Step 5: Branch check (P11).** Run `cut "$W/replay-2" … 2 "$W/rows-2.json"`, then `run "$W/replay-2" "$W/rows-2.json" 2 specs/evidence/stage2a1/predispatch/branch-check.json --branch`. Expected: exit 0, with the selection byte-equal to the saved one. If the script exits 3, stop. Show the owner the differing fields (HUMAN), and log the answer as a Decision. These times are a check, not evidence.
- [ ] **Step 6: Confirm `data/` is unchanged.** Hash `data/` again with Step 3's `find` command into `$W/live-data-after.sha256`, and compare it with the before list as Step 3 does, both sorted with `LC_ALL=C sort`. Expected: no output. Then `rm -rf "$W"`.
- [ ] **Step 7: Commit.**

```bash
git add specs/evidence/stage2a1/predispatch
git commit -m "feat(evidence): add the Stage 2a1 pre-dispatch replay and its branch check"
```

---

### Task 7: Member-wall script (spec §6 "Member walls"; P5, P6)

**Files:**
- Create: `specs/evidence/stage2a1/walls/member-walls.py`, a copy of `specs/evidence/stage2b/scratch/order-timing.py`. Leave the Stage 2b file unedited.
- Create: `specs/evidence/stage2a1/walls/origins.json`

**Interfaces:**
- Produces: the copy keeps `FIXED`, `REPEATS`, `pick_d`, `locate`, `plan`, `transform_call`, `publish_call`, `convergence` and their records unchanged. It adds Task 6's root guard. It adds three subcommands, with today's arguments under `walls`:
  - `member-walls.py walls <root> <config> <results.jsonl> <convergence.json> [--validate-only] [--branch]`: for each step that is not a repeat, `plan` also picks the member: the registered member of the step's source with the lowest `member_id` that passes `read_member`. If a step has none, the script raises an `Anomaly`. If that member has no binding, the collect body verifies the step's chosen snapshot instead, and the record says `unbound: true`. Around the step's production calls, it times each P5 engine term in-process. It uses a fresh workflow context per member (command `backfill`, built like `new_context` and pinned), with the step's source, and writes one result line per term. `--validate-only` also prints the chosen members.
  - `member-walls.py origins <live-root> <origins.json>`: read-only on a fresh live clone. For each target source, it records every registered member, its parent, and the release ID in its origin context's runtime, with the lowest `member_id` marked. For each distinct origin release it keeps one origin effective config.
  - `member-walls.py starts <scratch-config> <origins.json> <scratch-root> <starts.json>`: for the new release with `<scratch-config>`, and for each origin release in `<origins.json>` with a config made from its origin effective config, with `storage.root` and `logging.root` set under `<scratch-root>`, it runs the P5 child-start probe five times. Each probe is a child process started with `native_python_argv(<release python>)`. It records each wall, the median per release, and per target the largest `collect` median and its release.

- [ ] **Step 1: Write `member-walls.py`** to the Interfaces above.
- [ ] **Step 2: Make fresh clones and a scratch config.** Use Task 6 Steps 2–3 with `W=/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-walls-branch-<UTC stamp>`, cloning `data` to `$W/live` and the backup's `data-raw` to `$W/data`. Copy `conf/sec-edgar-local.json` to `$W/config.json`, and set `storage.root` to `$W/data` and `logging.root` to `$W/logs`. Change nothing else.
- [ ] **Step 3: Run `origins`** with the branch interpreter on `$W/live` into `specs/evidence/stage2a1/walls/origins.json`. Expected: one entry per target source, each with release IDs from F8. Then run `starts` with `$W/config.json`, `origins.json` and `$W` into `$W/starts.json`. Expected: a median for each release. This checks the probe on the branch. Its config still selects the 2a release, so the evidence run is Task 11.
- [ ] **Step 4: Run `walls --validate-only --branch`** on `$W/data`. Expected: exit 0. The same D and targets as `specs/evidence/stage2b/pre-campaign.md` ("Member timing"), and one member per non-repeat step. If an `Anomaly` is printed, stop and report it.
- [ ] **Step 5: Confirm `data/` is unchanged** (Task 6 Step 6), and `rm -rf "$W"`.
- [ ] **Step 6: Commit.**

```bash
git add specs/evidence/stage2a1/walls
git commit -m "feat(evidence): add the Stage 2a1 member-wall timing"
```

---

### Task 8: Full gate, evidence, whole-branch review and merge (HUMAN checkpoint)

**Files:**
- Create: `specs/evidence/stage2a1/gate.md`

- [ ] **Step 1: Run the full gate in the background,** from the worktree root, with plan 7 Task 8 Step 1's commands. Use `/tmp/s2a1-venv` and the log `/Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a1-gate.log`. Expected: the log ends with `exit 0`, and unittest prints `OK`. The count is F11's 1,187 plus the new tests, in 77 modules (75 plus `test_pre_dispatch_cost` and `test_release_2a1`). Record the exact count. Then `rm .venv`.
- [ ] **Step 2: Evidence run on the installed 2a release (P9).**

```bash
SEC_LOCAL_2A_RELEASE=/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a1-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py test_release_2a1 -v > /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a1-installed-2a.log 2>&1; echo "exit $?" >> /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a1-installed-2a.log
```

Expected: 2 tests, `OK`, `exit 0`.
- [ ] **Step 3: Record the gate.** `gate.md` holds what `specs/evidence/stage2a/gate.md` holds: the branch, the gated commit, the command, the start and end times, `Ran N tests in S s`, `OK`, the module count and the Step 2 result. Add the Task 6 branch check, and a table that maps spec §5 items 1–7 and Review Focus 1–5 to their test names. Commit: `docs(evidence): record the Stage 2a1 branch gate`.
- [ ] **Step 4: Whole-branch review.** Use the requesting-code-review skill on `main..stage2a1-pre-dispatch-cost`, against the spec, this plan and its Decisions. Name these focuses:
  - the anti-goals of spec §2.3;
  - every `read_parent` and `_publish_calls` site in phase 1 and phase 2 of `select_work`;
  - `renew()` on both discovery outcomes;
  - the `checks is None` paths (H4);
  - `of_source` against `inventory()`;
  - the two scripts' root guard and their row cut.

  Fix each accepted finding with a test. If a fix changes `src`, run Step 1 again and update `gate.md`. Record the review in `gate.md` under `## Review`: the reviewer, the commit range, each finding and its fix or ruling.
- [ ] **Step 5: Check the locked inputs and the platform member (P8, H9)** with plan 7 Task 8 Step 5's commands, using revision `32863852ce57f1da99db4720bd1c729727b4ec0c` and branch `stage2a1-pre-dispatch-cost`. Expected: `members = ["packages/sec-edgar-ingest"]`, and no diff output.
- [ ] **Step 6: Owner checkpoint (HUMAN).** Show `gate.md`, the review result and `git log --oneline main..stage2a1-pre-dispatch-cost`. Ask for approval to merge. Stop until the owner answers. Log the answer as a Decision.
- [ ] **Step 7: Merge** in the main checkout with plan 6 Task 4 Step 8's commands, branch `stage2a1-pre-dispatch-cost`, message `merge: Stage 2a1 pre-dispatch cost`. Both `git status --porcelain --untracked-files=all` calls print nothing. Keep the worktree until Task 13 ends.

---

### Task 9: Build and verify the release (spec §6 "Release"; H9)

Run in the main checkout on `main`.

**Files:**
- Create: `specs/evidence/stage2a1/release.md`

**Interfaces:**
- Produces: `releases/sha256=<2A1>/`. Its ID, manifest path and `git_revision` feed Tasks 10–13 and the Handoff.

- [ ] **Step 1: Confirm a clean tree** (`git status --porcelain --untracked-files=all` prints nothing), and record `git rev-parse HEAD`.
- [ ] **Step 2: Build** with plan 6 Task 5 Step 2's command. Record `<2A1>`.
- [ ] **Step 3: Check identity, lock and export against the 2a inputs.** Run plan 6 Task 5 Step 3's commands with `C=releases/sha256=<2A1>`, `B=releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec` and revision `32863852ce57f1da99db4720bd1c729727b4ec0c`. Expected: `lock-identical`, `export-lines-identical`, `inputs-identical`, version `0.2.0` in both, the `<2A1>` `git_revision` equal to Step 1's revision, and equal dependency lists with no platform package.
- [ ] **Step 4: Offline verification** with plan 6 Task 5 Step 4's commands on `releases/sha256=<2A1>`. Copy the evidence to `fixture-data/s2a1-verify-evidence`. Expected: verifier JSON with `"exit": 0` and `"release_id": "<2A1>"`, and `preflight_current` printing `<2A1>`.
- [ ] **Step 5: Confirm retention.** `ls releases` lists F8's eight releases and `sha256=<2A1>`, plus `artifact-cache` and `task14-guard-proofs`.
- [ ] **Step 6: Write `release.md`** in the 2a layout (`## Release`, `## Locked inputs`, `## Offline verification`, retention), with the line "No SEC request was sent. Verification used fixture acquisition only." Commit: `docs(evidence): record the 2a1 release build and offline verification`.

---

### Task 10: Pre-dispatch timings on the installed releases (spec §6; pre-dispatch bar; P1–P4)

Run in the main checkout on `main`. This task reads `data/` once to clone it, and writes nothing under it.

**Files:**
- Create: `specs/evidence/stage2a1/predispatch/` outputs: `2a-2.json`, `new-2.json`, `new-1.json`, `projection.json`, `live-data-before.sha256`, `live-data-after.sha256`. The saved rows and saved selections stay in `$W`.
- Create: `specs/evidence/stage2a1/predispatch.md`

- [ ] **Step 1: Confirm that no writer runs, check `data/` and make three fresh live clones,** as in Task 6 Steps 2–3, with `W=/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-predispatch-<UTC stamp>` and clones `$W/r-2a-2`, `$W/r-new-2` and `$W/r-new-1`. Expected: `data-as-diagnosed`.
- [ ] **Step 2: Cut each clone.** Run `cut` with invocation 2 on `r-2a-2` and `r-new-2`, and with invocation 1 on `r-new-1`, with the new release's interpreter (`releases/sha256=<2A1>/venv/bin/python -I -B -X pycache_prefix=/dev/null`) and the committed `diff.json`. Expected: each exits 0, with 155, 155 and 127 registered.
- [ ] **Step 3: Time the 2a release.** Run `run "$W/r-2a-2" … 2 …/2a-2.json` on the 2a interpreter (`releases/sha256=e49d3ba8…/venv/bin/python -I -B -X pycache_prefix=/dev/null`), in the background. One timing runs at a time. Expected: exit 0, byte-equal to the saved selection, and a time to the first dispatch above 1,500 s. If the run exits 3, stop and show the owner the differing fields (HUMAN).
- [ ] **Step 4: Time the new release.** Run `run` for invocation 2 into `new-2.json`, then for invocation 1 into `new-1.json`, on the `<2A1>` interpreter. Expected: exit 0 for both. `new-2.json` has the same selection SHA-256 as `2a-2.json`. That is H1 between the releases. If the SHA-256s differ, stop: H1 fails, and the release must not be selected.
- [ ] **Step 5: Project** with `project new-1.json new-2.json 2a-2.json projection.json`. Expected: exit 0. Exit 4 means that a slope and its per-member median disagree. Stop and show the owner both values for each phase (HUMAN).
- [ ] **Step 6: Apply the pre-dispatch bar.** If the new release's projection is at or above 1,500 s, the Exit is not met. If it is above 600 s, stop: the stage stops before the live-config selection and reports to the owner (HUMAN). Log the answer as a Decision.
- [ ] **Step 7: Confirm `data/` is unchanged** (Task 6 Step 6), into `predispatch/live-data-after.sha256`.
- [ ] **Step 8: Record and commit.** Write `predispatch.md` with:
  - the clone path, the interpreters, the cut counts, the load averages and each phase per run;
  - both releases' times to the first dispatch on invocation 2's replay, and H1;
  - the per-phase cost of each registered member and of each new member on the new release;
  - the projection to the allowance against 600 s and 1,500 s;
  - invocation 1's comparison with its saved selection;
  - the line "No SEC request was sent. Nothing was written under `data/`."

  Commit: `docs(evidence): record the Stage 2a1 pre-dispatch timings`. Then `rm -rf "$W"`.

---

### Task 11: Member walls on the installed release (spec §6 "Member walls", stop rule; P5, P6)

Run in the main checkout on `main`.

**Files:**
- Create: `specs/evidence/stage2a1/walls/` outputs: `results.jsonl`, `member-walls-targets.json`, `convergence.json`, `starts.json`, `config.json`, `backup-before.sha256`, `backup-after.sha256`
- Create: `specs/evidence/stage2a1/walls.md`

- [ ] **Step 1: Confirm that no writer runs.** Hash the backup: run `find backups/stage2b-pre-campaign-20261106T174241Z -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256` into `walls/backup-before.sha256`, and compare it with F10's `backup-before.sha256`, both sorted with `LC_ALL=C sort`. Expected: no output. Then clone the backup's `data-raw` to `$W/data`, with `W=/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-walls-<UTC stamp>`.
- [ ] **Step 2: Write the scratch config** as in Task 7 Step 2, with `runtime.release_manifest` set to the `<2A1>` manifest. Copy it to `walls/config.json`.
- [ ] **Step 3: Validate** with `walls --validate-only` on the `<2A1>` interpreter. Expected: as in Task 7 Step 4.
- [ ] **Step 4: Run `walls`** in the background on the `<2A1>` interpreter. Expected: one result line per production call and per engine term, with no `quarantined`, `failed` or `error`. If the run fails, stop and report.
- [ ] **Step 5: Run `starts`** with `walls/config.json`, `walls/origins.json` and `$W`, into `walls/starts.json`. Expected: a median for the new release and for each origin release. If an origin release refuses its config, stop and report.
- [ ] **Step 6: Compute each member wall.** A wall is the transform plus the publish plus that member's engine terms, the collect body and three child starts. Plan 8's step 3 is a member too. Steps 7 and 9 stay publish-only (P5).
- [ ] **Step 7: Apply the member-wall stop rule and the P6 band.** If the longest wall is above 1,056 s, stop: report every wall to the owner and ask them to choose one of the three paths (HUMAN). If it is above 803.2 s and not above 1,056 s, stop and ask the same (P6, D1). Log the answer as a Decision. The live-config selection (Task 12) waits for it.
- [ ] **Step 8: Confirm that `data/` and the backup are unchanged.** Hash `data/` (Task 6 Step 6) and the backup (Step 1) again. Each must equal its before list.
- [ ] **Step 9: Record and commit.** Write `walls.md` in the layout of `pre-campaign.md` "Member timing". Include:
  - every wall against 1,056 s, with the 2026-07-01 member in bold, and each wall's terms;
  - the comparison with plan 8's walls;
  - the unmeasured terms (P6);
  - the members and origin releases;
  - the line "No SEC request was sent. Nothing was written under `data/` or `backups/`."

  Commit: `docs(evidence): record the Stage 2a1 member walls`. Then `rm -rf "$W"`.

---

### Task 12: Select the release in the live config (spec §6 "Live-config selection"; HUMAN checkpoint)

**Files:**
- Modify: `conf/sec-edgar-local.json` (`runtime.release_manifest`)
- Modify: `specs/evidence/stage2a1/release.md`

- [ ] **Step 1: Confirm that both stop rules let the stage go on**, from Tasks 10 and 11 and their Decisions.
- [ ] **Step 2: Edit the config.** Set `runtime.release_manifest` to `/Users/lowell/Projects/sec-edgar-local/releases/sha256=<2A1>/release.json`. Change nothing else, unless the owner took the second stop-rule path: then the reserve changes as decided.
- [ ] **Step 3: Offline preflight** with plan 6 Task 7 Step 2's command on the `<2A1>` interpreter. Expected: `floor 480`, `reserve 1800`, `release <2A1>`, and a new `effective` SHA-256 (before: `f2082322…`, F9). `git diff` shows one changed value. Run no launcher command.
- [ ] **Step 4: Owner checkpoint (HUMAN).** Show the diff, the Step 3 output, `predispatch.md` and `walls.md`. Ask for approval of the selection. Stop until the owner answers. Log the answer as a Decision. The approval authorizes no SEC traffic.
- [ ] **Step 5: Record and commit.** Append `## Live-config selection` to `release.md`, with the effective-config SHA-256, floor, reserve and binding, and the line "No SEC request was sent in this stage." Commit: `chore(config): select the 2a1 release`.

---

### Task 13: Parent-spec and runbook amendments (spec §7)

**Files:**
- Modify: `specs/sec-filing-index-ingestion-spec.md` (§§4.2, 4.8, 4.9, 6)
- Modify: `docs/runbooks/local-ingestion.md`, `docs/runbooks/release-upgrades.md`
- Modify: `specs/evidence/stage2a1/release.md` (the Task 12 commit hash)

- [ ] **Step 1: Write the amendments** that spec §7 lists, each tagged `(Stage 2a1, plan 9, <date>)`:
  - §4.2: one paragraph, in the spec's words, on one computation per phase between child executions;
  - §4.8: `<2A1>`, its commit and the effective-config SHA-256, and the reserve;
  - §4.9: no format change, and selecting the 2a release again is supported;
  - §6: the tests now cover selection equality and the kept-value rules.

  §9 needs no change.
- [ ] **Step 2: Update the runbooks** with the new release.
- [ ] **Step 3: Owner review of the wording (HUMAN).** Show the diff. Apply the answer and log it as a Decision.
- [ ] **Step 4: Commit:** `docs(specs): amend the parent spec and runbooks for the 2a1 release`.

---

## After the last task

Run the writing-plans Plan Completion Protocol, step 3a included. Do not edit the roadmap before then. The "862 s" and Exit wording change at the roadmap resume after this stage (spec §7). The Handoff to Stage 2b names at least the items of spec §6, "Handoff to Stage 2b", and the `.pyc` decision. Append the deferred item on registered-member accumulation (spec §2.2), with Stage 5 as its consumer. The item "History-scan cost" and item 1 of section `2-sec-filing-index-ingestion-spec — 2026-10-31` stay open. Leave plan 8 unedited. Then remove the worktree and `/tmp/s2a1-venv`.
