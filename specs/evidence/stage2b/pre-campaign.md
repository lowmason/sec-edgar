# Stage 2b pre-campaign check (plan 8, Task 2)

Run date: 2026-11-06. Release `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`.
Everything here ran offline, on a scratch copy of `data/` under the ignored `logs/stage2b/`.
No SEC request was made. Nothing was written under `data/`.

**Result: the D2 wall limit is breached.** The longest member wall is 3,239.6 s (step 2, daily 2026-07-01). The limit is 1,440 s.
Under D2, plan 8 stops here for an owner decision. Task 3 and later tasks have not run.

## Store check

| Check | Expected | Found |
| --- | --- | --- |
| Writer processes | `no writer` | `no writer` |
| `conf/sec-edgar-local.json` file hash | `7d61c3e2…` | `7d61c3e2da7fd4e88eea5aaf65ab10e4b7a36b9b96d5c6e7f70a3a69429bafda` |
| Last commit that touched `scripts/baseline-campaign.py` | the Task 1 commit | `d8c2e07` |
| Hash of the file list of `data/` (5,269 files) | `8f173474…6cfe` | `8f1734742943c72d86dccb5988801855cc0bae340190934b35bc7af6e8db6cfe` |
| Same hash after the timing run | unchanged | `8f1734742943c72d86dccb5988801855cc0bae340190934b35bc7af6e8db6cfe` (`data-unchanged`) |

The store is the one that F1–F3 described. The F1–F3 results stay valid.

## Preflight

Values in `pre-campaign/preflight.json`:

| Field | Value |
| --- | --- |
| `backfill` | `["2020Q1", "open"]` |
| `dispatch_reserve_seconds` | `1800` |
| `effective_config_sha256` | `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733` |
| `release_id` | `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec` |

All four match the plan.

## Member timing

Tool: `scratch/order-timing.py`. It ran from 2026-11-06T15:05:46Z to 17:27:59Z.
It calls `run_transform` and `run_publish` in-process, in the order of plan 8 Task 2 Step 3. The 18 result lines are in `pre-campaign/order-timing.jsonl`.
The wall of one call is `time.monotonic()` around the production call only.
The scratch script excludes the `collect` step, the child process start and the completion check. Live walls are therefore higher than the walls below.

**D** (the daily whose 2024Q1 rows meet a v2 quarterly authority) is the **2026-08-07** daily, source `4ecf5916…`. It is the daily source with the earliest period in the active 2024Q1 manifest. Step 3 ran.

| Step | Source | Transform (s) | Publish (s) | Member wall (s) | 1.25 × wall (s) | Against 1,440 s | Outcomes (transform / publish) |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 1 | quarterly 2024Q1 | 300.0 | 826.9 | 1,126.9 | 1,409 | ok | success / success |
| 2 | daily 2026-07-01 | 5.2 | 3,234.4 | **3,239.6** | **4,049** | **over (2.25×)** | success / success |
| 3 | daily 2026-08-07 (D) | 2.4 | 1.8 | 4.2 | 5 | ok | unchanged / unchanged |
| 4 | daily 2026-10-01 | 2.1 | 185.7 | 187.8 | 235 | ok | unchanged / success |
| 5 | quarterly 2026Q1 | 296.8 | 1,102.0 | 1,398.8 | 1,749 | ok (97%) | success / success |
| 6 | quarterly 2026Q3 | 237.9 | 993.7 | 1,231.6 | 1,539 | ok | success / awaiting_approval |
| 7 | 2026Q3 publish again | n/a | 939.6 | 939.6 | 1,175 | ok | awaiting_approval |
| 8 | daily 2026-09-24 | 3.0 | 7.7 | 10.8 | 13 | ok | success / success |
| 9 | 2026-09-24 publish again | n/a | 1.6 | 1.6 | 2 | ok | unchanged |
| 10 | quarterly 2026Q4 | 67.6 | 250.1 | 317.6 | 397 | ok | success / success |

Other Expected lines of Step 4:

- 18 result lines. No `quarantined`, `failed` or gap count above 0 in any line.
- 2026Q3 ended `awaiting_approval` in steps 6 and 7. The gated generation `507815be…` has `withdrawn` 42, `added` 21,571 and `row_count` 302,494. This meets "at least 42 withdrawals".
- 2026Q3 in steps 8 and 9 ended **`published`** (step 8) and `unchanged` (step 9). It did not end `awaiting_approval`. The plan names this as valid evidence. A daily that is new to 2026Q3 after the gate publishes cleanly. It adds no withdrawals.
- The 2024Q1 source and the 2026Q4 source each have more than one registered member. All of them are complete.

Costs of steps 7–9 in the live run:

- Step 7: each later invocation pays about **940 s** to retry the gated 2026Q3 member (F5), unless the runner skips it.
- Step 8: each body discovered after the 2026Q3 gate pays about **11 s** once.
- Step 9: that body then pays about **2 s** on each later run.

### Why step 2 is long

Step 2 is the first v2 write to 2026Q3. Its one publish call rebuilt 9 quarters:

| Quarter | Rows |
| --- | ---: |
| 2024Q3, 2024Q4, 2025Q1, 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | 3,612 together |
| 2026Q3 | 280,965 |

The 2026Q3 rebuild is more than 98% of the rows, with `provenance_refreshed` 280,965 and `added` 0. The call has one wall, so the split by quarter is an inference from row counts and not a measurement. At about 11.4 ms per row, this is roughly five times the 2.2 ms per row of the 2024Q1 publish in step 1 (826.9 s for 370,318 rows).

Step 6 gives a like-for-like check that rules out noise on the machine. It refreshed 280,923 rows of the same quarter on a v2 base, and its publish call took 993.7 s, about 3.5 ms per row. Step 2 did the same refresh from a v1 base at about 11.4 ms per row. The extra cost is therefore the one-time v1 to v2 conversion of 2026Q3. A second timing of step 2 alone would add little.

The copy note in plan Step 3 says the walls of steps 2–4 can only overstate the live cost. That holds for the eight small quarters. It does not hold for 2026Q3. In the true order (F2), the 2026Q3 quarterly runs last. The first 2026 daily is therefore the first v2 write to 2026Q3 in the live store as well.

## Convergence

Tool output: `pre-campaign/convergence.json`. Every registered member of each stepped source was evaluated with `evaluate_member` under the live parser and schema versions.

| Step | Source | Members | Complete | Gaps |
| --- | --- | ---: | ---: | --- |
| 1 | quarterly 2024Q1 | 2 | 2 | none |
| 2 | daily 2026-07-01 | 1 | 1 | none |
| 3 | daily 2026-08-07 | 1 | 1 | none |
| 4 | daily 2026-10-01 | 2 | 2 | none |
| 5 | quarterly 2026Q1 | 1 | 1 | none |
| 6 | quarterly 2026Q3 | 1 | 0 | `publication_pending` |
| 8 | daily 2026-09-24 | 1 | 1 | none |
| 10 | quarterly 2026Q4 | 3 | 3 | none |

This matches the Expected line. The 2026Q3 member is incomplete with only `publication_pending`, which is the gate that D3 leaves for Stage 4. Every daily member is complete after its quarter took a v2 authority. There is no feasibility blocker for stop rule 10.

## Wall limit (D2)

Rule (D2): if every member wall is at most 1,440 s, `max_member_wall_seconds` becomes 1,440. If one is above, the plan stops for an owner decision.

**Result: breach.** `max` = 3,239.6 s (step 2). Every other step is at or below 1,398.8 s.

Facts that bear on the decision:

- The run length is fixed in code. A live config must have `execution.max_run_seconds` equal to 3600 (`config.py`, `WORKER_ALLOWANCE_SECONDS`), and the reserve must be below it. A 1.25× margin on a 3,240 s member needs a reserve of 4,049 s. No admissible config can give that.
- The launcher sets the deadline to start + `timeout_seconds` (`local_cli.py`, `prepare_invocation`). The default is 3,300 s (O3), and the maximum is `max_run_seconds`, 3,600 s. At the deadline the launcher sends SIGTERM to the engine, and SIGKILL after 10 s.
- The runner starts no member after deadline − reserve (`runner.py`). That is 1,500 s at O3 = 3,300 s, and 1,800 s at O3 = 3,600 s. The runner would start this member at any time up to that cutoff. A member that is running at the cutoff is not stopped by the runner (§4.7), but the deadline still ends it.
- **At O3 = 3,300 s** the member cannot finish unless it starts within about 60 s of the invocation start, before the `collect`, child-start and completion-check time that this script excludes. That margin is 2% of the wall. The member can probably not finish in any invocation. Repeated deadline kills would use the 30-invocation budget.
- **At O3 = 3,600 s** (a launcher argument, not a config edit) the margin from a start at time 0 is about 360 s, 11% of the wall, before those overheads. D2 asks for 25%. A start later than about 360 s into the invocation still ends in a deadline kill, and the next invocation then starts the member first.
- Step 5 (2026Q1) is also close to the cap: 1,398.8 s is 97% of 1,440 s before the excluded overheads. If the cap stays at 1,440, stop rule 7 can halt on this member.

`max_member_wall_seconds` is not set. `campaign.json` and `campaign.md` are not written. The backup is not taken.
