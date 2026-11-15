# Stage 2a1 member walls on the installed release (plan 9 Task 11)

No SEC request was sent. Nothing was written under `data/` or `backups/`.

## Result in brief
- The longest member wall on the new release (`f414caf8…`) is **1,074.9 s**, for the 2026-07-01 daily (step 2). It is **18.9 s (1.8 %) above** the 1,056 s limit (spec §6, O1).
- So the member-wall stop rule applied. The stage stopped before the live-config selection, and the owner chose the second path: raise the reserve under the Stage 1b rule (Decision D10).
- Every other wall is at most 470.3 s. On the 2a release, plan 8 measured the same members at up to 3,239.6 s for transform plus publish.
- The wall figures are lower bounds. Three terms cannot be measured offline (P6, below).

## Setup
- **Date and checkout:** 2026-11-15, main checkout, `main` at `a5cad2d`. The code is the `e899d79` build.
- **Scratch folder:** `/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-walls-20261115T173751Z`. It held two APFS clones of `backups/stage2b-pre-campaign-20261106T174241Z/data-raw`, made with `cp -c -R`. The clone `validate` served the `--validate-only` run (Step 3) and was removed after it. The clone `data` had no command run on it before the timed `walls` run. The folder was removed after this record.
- **Checks before the run:** a `pgrep` check for a writer printed nothing. `data/` matched `diagnosis/outputs/live-data-before.sha256` (`data-as-diagnosed`). The backup (5,270 files) matched the diagnosis's `backup-before.sha256` (`backup-as-diagnosed`).
- **Config:** `walls/config.json` is `conf/sec-edgar-local.json` with 3 changes: `storage.root` (the `data` clone), `logging.root` (a scratch folder) and `runtime.release_manifest` (the new release's manifest). Nothing else differs. The live config was not changed. The `validate` run used a copy of it with `storage.root` set to the `validate` clone.
- **Interpreter:** `releases/sha256=f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18/venv/bin/python -I -B -X pycache_prefix=/dev/null`. The release is the one that `preflight_current` verifies.
- **Tool:** `walls/member-walls.py`, a copy of `specs/evidence/stage2b/scratch/order-timing.py` with the root guard of Task 6 and the subcommands `walls`, `origins` and `starts`.
- **Run times:** `walls` ran from 17:39:19Z to 18:30:13Z (51 min) and exited 0. `starts` ran at 18:30:55Z and exited 0 with `refused` empty.
- **Load.** Another project ran tests on the same 14-core machine, so the load was uneven. The 1-minute load average, sampled every 5 minutes from the start: 24.6, 43.6, 9.8, 14.4, 11.2, 14.1, 11.4, 8.8, 12.0, 14.8, 7.5. During step 2 it was 10.7 to 11.4. Each result line holds the load at its time. The walls carry load noise that this record cannot size.

## Validation (Step 3)
`walls --validate-only` on the throwaway clone exited 0. It chose one member for each of the 8 steps that are not repeats (steps 1 to 6, 8 and 10). **D** is the 2026-08-07 daily, source `4ecf5916…`, as in `specs/evidence/stage2b/pre-campaign.md`. The plan expected 18 production-call lines, and the timed run wrote them.

## Member walls
A wall is the transform, plus the publish, plus the member's engine terms, plus the collect body, plus three child starts (P5). The engine terms and the collect body are timed in-process. The child starts are the median of five runs of a fixed probe (import the CLI, `load_config`, `preflight_current`). Steps 7 and 9 are publish-only, as in plan 8. The result lines are in `walls/results.jsonl` (122 lines: 18 production calls and 104 engine terms). No line has `quarantined`, `failed` or `error`. The `validate_capture` terms of step 6 are `not_run`, because its publish ended `awaiting_approval` and no capture exists to validate.

The last column of the first table is the Stage 1b rule applied to each wall: a wall fits if `1.25 × wall + 480 s` is at most the 1,800 s reserve.

| Step | Source | Transform (s) | Publish (s) | Engine terms (s) | Child starts (s) | Member wall (s) | 1.25 × wall + 480 (s) | Against 1,056 s | Outcomes (transform / publish) |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | quarterly 2024Q1 | 132.3 | 328.7 | 5.20 | 1.80 | 468.1 | 1,065.1 | ok | success / success |
| **2** | **daily 2026-07-01** | 1.8 | 1,065.9 | 5.53 | 1.75 | **1,074.9** | **1,823.7** | **over (1.018×)** | success / success |
| 3 | daily 2026-08-07 (D) | 0.8 | 1.5 | 6.98 | 1.75 | 11.1 | 493.8 | ok | unchanged / unchanged |
| 4 | daily 2026-10-01 | 0.7 | 63.5 | 5.61 | 1.80 | 71.6 | 569.5 | ok | unchanged / success |
| 5 | quarterly 2026Q1 | 102.6 | 360.9 | 4.99 | 1.80 | 470.3 | 1,067.9 | ok | success / success |
| 6 | quarterly 2026Q3 | 80.4 | 365.6 | 4.45 | 1.80 | 452.2 | 1,045.3 | ok | success / awaiting_approval |
| 7 | 2026Q3 publish again | n/a | 357.7 | n/a | n/a | 357.7 | 927.1 | ok | n/a / awaiting_approval |
| 8 | daily 2026-09-24 | 1.0 | 5.0 | 4.88 | 1.75 | 12.6 | 495.8 | ok | success / success |
| 9 | 2026-09-24 publish again | n/a | 1.2 | n/a | n/a | 1.2 | 481.5 | ok | n/a / unchanged |
| 10 | quarterly 2026Q4 | 22.4 | 84.8 | 3.63 | 1.80 | 112.6 | 620.8 | ok | success / success |

The terms of each wall. The engine terms are `sibling_completion` and `WorkflowMembers.replay` (each under 0.001 s in every step) and the terms below. "×2" and "×4" give the number of calls in a wall.

| Step | `evaluate_member` ×2 | `validate_capture` ×2 | `read_member` ×2 | `read_etl_result` ×4 | `collect_body` | Starts: transform, publish, collect (s) |
|---|---:|---:|---:|---:|---:|---|
| 1 | 4.745 | 0.196 | 0.231 | 0.005 | 0.026 | 0.601, 0.601, 0.594 (`c4de77b8…`) |
| 2 | 4.923 | 0.519 | 0.042 | 0.006 | 0.044 | 0.601, 0.601, 0.545 (`fc68adef…`) |
| 3 | 6.367 | 0.514 | 0.040 | 0.005 | 0.055 | 0.601, 0.601, 0.545 (`fc68adef…`) |
| 4 | 5.124 | 0.273 | 0.199 | 0.005 | 0.007 | 0.601, 0.601, 0.594 (`c4de77b8…`) |
| 5 | 4.490 | 0.249 | 0.187 | 0.005 | 0.060 | 0.601, 0.601, 0.594 (`c4de77b8…`) |
| 6 | 4.223 | 0.000 | 0.182 | 0.005 | 0.043 | 0.601, 0.601, 0.594 (`c4de77b8…`) |
| 8 | 4.371 | 0.419 | 0.043 | 0.005 | 0.042 | 0.601, 0.601, 0.545 (`fc68adef…`) |
| 10 | 3.528 | 0.058 | 0.025 | 0.005 | 0.018 | 0.601, 0.601, 0.594 (`c4de77b8…`) |

Step 2's wall is 1.8 s of transform, 1,065.9 s of publish, 5.5 s of engine terms and 1.75 s of starts. The publish call is 99.2 % of it.

### Convergence
`walls/convergence.json` evaluates every registered member of the 8 stepped sources after the run (12 members). 11 are complete. One is incomplete: the 2026Q3 member of step 6, with the gap `publication_pending`. That is the expected state: its publish ended `awaiting_approval`.

## Comparison with plan 8
Plan 8's walls (`specs/evidence/stage2b/pre-campaign.md`, "Member timing") are the transform plus the publish only, on the 2a release. The table compares that part of each wall. The new release is 1.3 to 3.0 times lower.

| Step | Plan 8 transform + publish (s) | New transform + publish (s) | Ratio |
|---|---:|---:|---:|
| 1 | 1,126.9 | 461.1 | 2.4× lower |
| 2 | 3,239.6 | 1,067.7 | 3.0× lower |
| 3 | 4.2 | 2.3 | 1.8× lower |
| 4 | 187.8 | 64.2 | 2.9× lower |
| 5 | 1,398.8 | 463.5 | 3.0× lower |
| 6 | 1,231.6 | 446.0 | 2.8× lower |
| 7 | 939.6 | 357.7 | 2.6× lower |
| 8 | 10.8 | 6.0 | 1.8× lower |
| 9 | 1.6 | 1.2 | 1.3× lower |
| 10 | 317.6 | 107.2 | 3.0× lower |

Plan 8 had 4 walls above 1,056 s (steps 1, 2, 5 and 6). On the new release only step 2 is above it. The spec's earlier figure for step 2's publish was 988.5 s, under a call-counting wrapper (spec §8, O1). This run gives 1,065.9 s, 7.8 % higher, with another project's load on the machine. This record cannot say how much of the difference is load.

## Terms that are not measured (P6)
Three terms cannot be measured offline:
- the full per-call child-result validation inside `validate_member_evidence` (run twice);
- the dispatcher's call and execution writes;
- `collect`'s attempt bookkeeping.

`resolve_child` is also not in the walls. The start probe measured it at 0.19 s for each child (0.186 s on the new release, 0.186 to 0.191 s on the origin releases). Three children add about 0.6 s to a member. So every wall above is a lower bound. The Stage 1b rule's 25 % overrun margin is 268.7 s for step 2.

## Members and origin releases
`walls/origins.json` lists, for each of the 8 target sources, every registered member, its parent and the release in its origin context: 21 members, 4 origin releases (`9fa189a0…`, `c4de77b8…`, `e49d3ba8…`, `fc68adef…`), all in the F8 list, with no stop. The member that a step times is the lowest `member_id` of its source that passes `read_member`. A member that Stage 2b discovers may sort first for its source. So the `collect` start of a target is the largest median over the origin releases of all registered members of its source. `walls/starts.json` holds the five runs of each release. The medians are 0.601 s for the new release, and 0.545 to 0.594 s for the origin releases. No origin release refused its config.

| Step | Member | Origin release | Registered members of the source | `collect` start release | `collect` start median (s) |
|---|---|---|---:|---|---:|
| 1 | `982a0eb4…` | `c4de77b8…` | 2 | `c4de77b8…` | 0.594 |
| 2 | `3554e8ef…` | `fc68adef…` | 1 | `fc68adef…` | 0.545 |
| 3 | `951996f6…` | `fc68adef…` | 1 | `fc68adef…` | 0.545 |
| 4 | `4ba976d2…` | `c4de77b8…` | 2 | `c4de77b8…` | 0.594 |
| 5 | `c55de520…` | `c4de77b8…` | 1 | `c4de77b8…` | 0.594 |
| 6 | `32fe89cf…` | `c4de77b8…` | 1 | `c4de77b8…` | 0.594 |
| 8 | `ffecd154…` | `fc68adef…` | 1 | `fc68adef…` | 0.545 |
| 10 | `38148f77…` | `c4de77b8…` | 3 | `c4de77b8…` | 0.594 |

## Stop rule and Decision D10
The longest wall is 1,074.9 s, above the 1,056 s limit. So the Exit was not met. The stage stopped before the live-config selection, and the owner was asked to choose one of the three paths of spec §6. The owner chose to **raise the reserve under the Stage 1b rule** (plan 9, Decision D10, "Raise reserve").

- At this wall, `1.25 × 1,074.9 s + 480 s = 1,823.7 s`. So the reserve must be at least **1,824 s**. The reserve now is 1,800 s.
- The cutoff is the 3,300 s launcher default minus the reserve. At 1,824 s it is 1,476 s, and it is lower for a larger reserve.
- The owner gave no figure. The figure is set in Task 12 Step 2, not below 1,824 s, and the owner approves it at Task 12 Step 4 with the config diff.
- The pre-dispatch bars of `predispatch.md` hold against the lower cutoff. The new release's bound is 281.2 s, and the 2a release's measured first dispatch is 3,197.5 s. The 2a release is above the cutoff, and the new release is far below it.

## Data
`data/` and the backup were hashed again after the runs, with the same `find` commands. Each sorted list equals its list from before the run (`data-unchanged`, `backup-unchanged`). The lists are `walls/live-data-before.sha256`, `walls/live-data-after.sha256`, `walls/backup-before.sha256` and `walls/backup-after.sha256`.

## Files
`walls/member-walls.py`, `walls/origins.json`, `walls/member-walls-targets.json`, `walls/config.json`, `walls/results.jsonl`, `walls/convergence.json`, `walls/starts.json`, and the four hash lists named above.

No SEC request was sent. Nothing was written under `data/` or `backups/`.
