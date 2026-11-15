# Stage 2a1 pre-dispatch timings on the installed releases (plan 9 Task 10)

No SEC request was sent. Nothing was written under `data/`.

## Result in brief
- On the 2a release, invocation 2's replay reaches its first dispatch at **3,197.5 s**. That is above the 1,500 s cutoff.
- On the new release (`f414caf8…`), the same replay reaches it at **126.2 s**. Invocation 1's replay reaches it at **116.0 s**.
- The new release freezes the same selection as the 2a release for invocation 2 (H1): byte for byte, SHA-256 `4c928887c9c5e34fb4d1960d3663324db032296a7cd9675a155a4912fd390dec`, 18,560,172 bytes.
- `replay.py project` exited 4 (the slope check failed for `before_discovery`). The script projected nothing. The owner accepted a stated bound (Decision D9). The bound is **281.2 s** at the growth allowance, below the 600 s bar and the 1,500 s cutoff.

## Setup
- **Date and checkout:** 2026-11-15, main checkout, `main` at `88711c2` (the code is the `e899d79` build).
- **Scratch folder:** `/Users/lowell/Projects/sec-edgar-local/logs/stage2a1-predispatch-20261115T163758Z`. It held three APFS clones of `data/` made with `cp -c -R`: `r-2a-2`, `r-new-2` and `r-new-1`. A `pgrep` check for a writer printed nothing first. `data/` matched `diagnosis/outputs/live-data-before.sha256` (`data-as-diagnosed`). The folder was removed after this record.
- **Interpreters:** each as `<release>/venv/bin/python -I -B -X pycache_prefix=/dev/null`.
  - 2a: `releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`.
  - New: `releases/sha256=f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18`.
- **Cuts** (`replay.py cut`, with the committed `diff.json`, on the new interpreter). Each exited 0.

| Clone | Invocation | Registered after the cut | Saved selection (SHA-256, bytes) |
|---|---|---:|---|
| `r-2a-2` | 2 | 155 | `4c928887…`, 18,560,172 |
| `r-new-2` | 2 | 155 | `4c928887…`, 18,560,172 |
| `r-new-1` | 1 | 127 | `9f10239b99cdbc5adbe490a2735ed032d000318fa660eb102f0f7df3d117baf0`, 12,759,217 |

- **Timed runs** (`replay.py run … --`, one at a time, each from its own fresh clone, in the order below). Each exited 0.
- **Load averages** (`os.getloadavg()`, 1, 5 and 15 minutes) were high because another project ran tests on the same 14-core machine. The 2a run began at a 1-minute load of 22.0. The load fell during the run. So the 2a figure carries load noise that this record cannot size.

| Run | Start (UTC) | Load at start | Load at end |
|---|---|---|---|
| 2a, invocation 2 | 16:38:49 | 22.01, 15.99, 11.39 | 9.29, 9.05, 9.69 |
| New, invocation 2 | 17:31:38 | 9.29, 9.05, 9.69 | 11.51, 9.55, 9.79 |
| New, invocation 1 | 17:33:15 | 11.95, 9.67, 9.83 | 13.71, 10.75, 10.22 |

## Time to the first dispatch
The model is: 1 s for the launcher, plus the five phases, with the replayed discovery replaced by 29 s (the figure of the recorded run). All times are seconds.

| Run | Before discovery | Discovery (replayed) | Projection | After discovery | Freeze | First dispatch |
|---|---:|---:|---:|---:|---:|---:|
| 2a, invocation 2 | 1,352.84 | 0.20 | 991.39 | 798.81 | 24.50 | **3,197.55** |
| New, invocation 2 | 42.69 | 0.19 | 2.12 | 39.52 | 11.88 | **126.21** |
| New, invocation 1 | 43.25 | 0.22 | 1.25 | 33.32 | 8.20 | **116.02** |

- Invocation 2 on the 2a release: 155 members were registered at the start and 208 after the projection. 53 members are new and 48 of them reached the registry check.
- Invocation 2 on the new release: the same counts.
- Invocation 1 on the new release: 127 registered at the start and 155 after the projection. 28 members are new and all 28 reached the registry check.
- No call fell outside a phase (`calls_outside_phases` is 0 in all three).
- The registry check, in `reuse_exact_binding`: on the 2a release it is `WorkflowMembers.inventory`, 48 calls, 964.7 s in total. On the new release it is `WorkflowMembers.of_source`, 48 calls, 0.86 s in total.

### H1 between the releases
Both invocation 2 replays froze a `selection.json` with the SHA-256 above, equal to the saved selection (`differing_fields` is empty in both). So the new release selects the same work as the 2a release here.

### Invocation 1 on the new release
The frozen selection equals the saved one: SHA-256 `9f10239b99cdbc5adbe490a2735ed032d000318fa660eb102f0f7df3d117baf0`, 12,759,217 bytes. This comparison is recorded only (P3). The run exited 0.

## Cost of each member
The tables give the call time of each member in a phase, in seconds. "Registered" members are the ones that were registered when the phase ran. The projection phase covers the new members only.

New release, invocation 2 (155 registered at the start, 53 new):

| Phase | Members | Median | Maximum | Total |
|---|---:|---:|---:|---:|
| Before discovery (`WorkflowMembers.completed`, `evaluate_member`) | 155 | 0.1860 | 1.568 | 38.13 |
| Projection (`project_member`, `reuse_exact_binding`), new members | 53 | 0.0349 | 0.204 | 2.00 |
| After discovery (`evaluate_member`, `capture_member_provenance`) | 208 | 0.1047 | 1.790 | 39.42 |
| Freeze (`validate_member_provenance`, `validate_capture`) | 208 | 0.0639 | 0.087 | 10.20 |

New release, invocation 1 (127 registered at the start, 28 new):

| Phase | Members | Median | Maximum | Total |
|---|---:|---:|---:|---:|
| Before discovery | 127 | 0.2416 | 1.709 | 39.08 |
| Projection, new members | 28 | 0.0352 | 0.139 | 1.15 |
| After discovery | 155 | 0.1412 | 2.057 | 33.20 |
| Freeze | 155 | 0.0238 | 0.115 | 6.98 |

2a release, invocation 2, for comparison:

| Phase | Members | Median | Maximum | Total |
|---|---:|---:|---:|---:|
| Before discovery | 155 | 7.7151 | 11.230 | 1,246.37 |
| Projection, new members | 53 | 20.2779 | 25.026 | 991.24 |
| After discovery | 208 | 3.7972 | 4.568 | 798.49 |
| Freeze | 208 | 0.1444 | 0.181 | 22.65 |

The median cost of a member is 41 times lower before discovery (7.7151 s against 0.1860 s) and 36 times lower after discovery (3.7972 s against 0.1047 s) on the new release. A new member's projection costs 0.0349 s against 20.2779 s.

## Projection to the allowance
The allowance is 450 registered members, 55 new members, 29 s of discovery and 1 s for the launcher (P4). The bars are 600 s (stage stop) and 1,500 s (cutoff).

### The script's result: exit 4
`replay.py project new-1.json new-2.json 2a-2.json projection.json` exited 4 and projected nothing. The `projection.json` file records the failed check. Each fitted slope must be within a factor of 2 of the median per-member call time of its phase. Slopes are in seconds per member.

| Phase | Raw slope | Median per member | Factor | Check |
|---|---:|---:|---:|---|
| `before_discovery` | −0.0199 (clamped to 0) | 0.2187 | none | **fail** |
| `after_discovery` | 0.1169 | 0.1208 | 1.03 | pass |
| `freeze` | 0.0695 | 0.0621 | 1.12 | pass |
| `projection` | 0.0435 | 0.0357 | 1.22 | pass |

`before_discovery` failed because the two new-release runs give almost the same phase time: 43.25 s at 127 registered members and 42.69 s at 155. The 28 added members did not add time, although a member costs 0.2187 s at the median. The two runs differ in member composition as well as count, and two points cannot show the cause.

### Decision D9: a stated bound
The owner accepted a stated bound in place of the failed fit (plan 9, Decision D9, "Accept bound"). The controller worked out the figures below by hand from `new-1.json`, `new-2.json` and `projection.json`. The script did not produce them. The fitted figures for the three passing phases are in `projection.json`.

| Bound | `before_discovery` | `after_discovery` | `projection` | `freeze` | Launcher and discovery | Total |
|---|---:|---:|---:|---:|---:|---:|
| Clamped-flat fit | 42.7 | 74.3 | 2.4 | 32.5 | 30 | 181.9 |
| Median-based `before_discovery` (0.2187 s × 450), fits for the other three | 98.4 | 74.3 | 2.4 | 32.5 | 30 | 237.6 |
| **Every phase scaled in proportion to its count from zero** (invocation 2 run: 42.69 s × 450 ÷ 155, 39.52 s × 505 ÷ 208, 2.12 s × 55 ÷ 48, 11.88 s × 505 ÷ 208) | 123.9 | 96.0 | 2.4 | 28.8 | 30 | **281.2** |

The bars are judged against the largest figure, 281.2 s. It assumes no fixed cost in any phase, so each phase grows as fast as possible in proportion to its count.

### The 2a release at the allowance
The 2a release's first dispatch was measured at **3,197.5 s** with 155 registered members. The script's ratio method (each 2a phase time times the allowance count divided by the 2a run's count of the same field) gives, by hand: 3,927.6 s before discovery, 1,136.0 s for the projection, 1,939.4 s after discovery, 59.5 s for the freeze, and 7,092.5 s in total with the 30 s. This is linear scaling. The 2a release's cost depends on the registered count in a way that is worse than linear, so 7,092.5 s is a low figure.

## Bars (Step 6)
| Bar | Release | Figure | Result |
|---|---|---:|---|
| Pre-dispatch cutoff: none before 1,500 s on the 2a release | 2a | 3,197.5 s measured | met |
| Pre-dispatch cutoff: first dispatch before 1,500 s | new | 281.2 s (stated bound), 126.2 s measured | met |
| Stage stop: a projection above 600 s stops the stage | new | 281.2 s (stated bound) | not triggered |

## Data
`data/` was hashed again after the runs, with the same `find` command. The sorted lists are equal (`data-unchanged`). The two lists are `predispatch/live-data-before.sha256` and `predispatch/live-data-after.sha256`.

## Files
`predispatch/2a-2.json`, `predispatch/new-2.json`, `predispatch/new-1.json`, `predispatch/projection.json` (the exit 4 record), `predispatch/live-data-before.sha256` and `predispatch/live-data-after.sha256`. The `projection.json` file lists the SHA-256 of each run file. The saved rows and saved selections stayed in the scratch folder.

No SEC request was sent. Nothing was written under `data/`.
