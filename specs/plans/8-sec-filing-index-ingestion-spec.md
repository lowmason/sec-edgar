# Stage 2b Baseline Coverage on the 2a Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2b — on plan completion, tick the stage and re-validate later stages against what shipped.

**Goal:** Produce a revised, owner-accepted G2 finding on the 2a release `e49d3ba8…`. The finding accounts for each of the 28 quarterly units 2020Q1–2026Q4 and the 7 daily duplicate-key sources by a validated publication, or by a named gap, gate or quarantine with an owner disposition. It ends with a revised complete-or-incomplete operating decision.

**Architecture:** The campaign repeats plan 2's operating method on the new release: the launcher `backfill` workflow with the live config, an audit and an integrity report after each invocation, the stop rules, and one full coverage check at the end. It reuses plan 2's evidence tool, its step blocks and its stop rules, and names only what changes. Three offline tasks come first: a small tool change for v2 generations, timing of the largest members in true dispatch order on a scratch copy, and a fresh stopped-writer backup with the campaign files. Then an owner gate opens live execution.

**Tech Stack:** Installed native release `e49d3ba8…` (application 0.2.0, CPython 3.14.0, `git_revision` `32863852…`). Stdlib `unittest` under `packages/sec-edgar-ingest/tests/network_guard.py`. SQLite backup API. Launcher `scripts/sec-edgar-local`. Evidence tool `scripts/baseline-campaign.py`.

**Spec:** [specs/sec-filing-index-ingestion-spec.md](../sec-filing-index-ingestion-spec.md) §§4.2–4.9, 5–6, 7 G2. Stage 2b has no stage spec. Its inputs are the roadmap entry's `Consumes`; plan 7, Handoff, Stage 2b bullet (`specs/plans/completed/7-sec-filing-index-duplicate-key.md`); plan 2, Handoff, and its campaign files (`specs/plans/completed/2-sec-filing-index-ingestion-spec.md`, `specs/evidence/baseline-campaign/`); and the [2a spec](../completed/sec-filing-index-duplicate-key.md) §6.

## Status of authority

This plan authorizes no live traffic.

- Tasks 1–3 are offline and send no SEC request. Nothing writes under `data/`. Task 3 writes the backup under the ignored `backups/`.
- Task 4 is the owner's live-execution gate. Tasks 5–7 run only after the Task 4 approval commit exists.
- Planning sent no SEC request and wrote nothing under `data/`. The checks behind F1 and F3 read scratch copies under the ignored `logs/plan8-planning/`, and `data/` was unchanged by hash.

## Facts established while planning (read-only, 2026-11-05)

The planning scripts and their outputs are in `specs/evidence/stage2b/planning/`.

- **F1 — Every registered member re-runs under v2.** The store holds 127 registered members: 31 quarterly and 96 daily. `WorkflowMembers.completed` accepts only a receipt with the run's parser and schema versions (`workflows/members.py:131`), and `evaluate_member` keys Processing on them (`workflows/completion.py:812`). Under v1, 74 members are complete by receipt and 88 evaluate complete. Under v2, none is complete: 126 report `transform_pending` and 1 reports `acquisition_pending`, all retryable. No member stops before dispatch (plan 6 trap (e)). So the first v2 invocation selects all 127 members and lists no source as already complete (`planning/members.json`, from `planning/members.py`). Plan 7's Handoff does not name this. `test_release_2a` covers continuation of 1c pending work, not completed v1 members.
- **F2 — Dispatch order.** The runner sorts members by `(period, source_id, member_id)` as strings (`workflows/runner.py:261`). `-` sorts before `Q`. So the order is: the quarterly members 2020Q1–2025Q4 (25, two of them for 2024Q1); then the 96 daily members of 85 daily sources, 2026-07-01 to 2026-10-30 (two members each for the 11 business days 2026-10-01 to 2026-10-16); then the quarterly members 2026Q1, 2026Q2 and 2026Q3, and three for 2026Q4. Daily bodies discovered after 2026-10-30 sort after 2026-10-30 and before 2026Q1.
- **F3 — Predicted withdrawal gates.** `planning/gates.py` compared each quarter's active generation keys with the keys of its retained quarterly `master.idx` (`planning/gates.json`). Its quarterly key counts equal the 2a scratch counts. No closed quarter from 2020Q1 to 2026Q2 has an absent active key, so none should gate. 2026Q3 has 42 absent keys in its v1 base. The 7 duplicate-key dailies publish before the 2026Q3 quarterly member (F2) and hold 5 more absent keys (plan 7, Handoff), so expect about 47 withdrawals and `awaiting_approval`. 2026Q4 has 3 absent keys, but it is the open quarter, so they stay `unresolved_absence` with no gate (§4.4). Not checked: rows that the 7 dailies or new dailies add to 2026Q1 or 2026Q2 before those quarterly members run.
- **F4 — Member cost estimates** (`specs/evidence/stage2a/release.md`, "Scratch re-transform"). Quarterly transforms took 67.2–293.4 s. The 2023Q1 first publish (348,463 rows, no base) took 733.8 s. The 2026Q3 candidate took 1,306.7 s, including the inline v2 re-transform of 77 v1 daily sources. A workflow member runs both transform and publish, so a full-size closed member takes about 700–1,100 s, and the 2026Q3 member about 1,300–1,550 s. Two members were never measured: the first daily member (2026-07-01), which makes the first v2 rebuild of 2026Q3, and the first daily that touches 2026Q4. Plan 2's member-wall limit of 1,056 s (1.25 × w + 480 ≤ 1,800) would halt on a full-size quarter such as 2024Q1.
- **F5 — A gated quarter costs time on each later run.** `awaiting_approval` is a pending outcome, so the runner selects the gated member again. Its publish finds the stored candidate, runs the full content check and returns `awaiting_approval` again (`etl/publication.py:97–110`; §4.6). In planning, a full read of the 2026Q3 v1 generation (280,965 rows) together with a parse of its quarterly file took 398.2 s, so the read alone took at most that. Task 2 step 7 measures the retry. Stop rule 10 counts only `pending`, `deferred` and `throttled`, so a gated member does not keep the campaign running.
- **F6 — Configs.** The live config selects the 2a release with `sec-index-parser-v2` / `sec-index-v2`, range `2020Q1`–`open`. It is the campaign's only config, as in plan 2 from invocation 4 (Revision 4): a run whose pinned end lies before a retained member fails (plan 2, Handoff, Stage 3 trap (a)). The v1 configs under `conf/stage2/` do not load on the 2a release (plan 7, Handoff). They stay as history and are never run.
- **F7 — Store state.** `data/` holds 5,269 files, the same count as the 2a scratch record. The SHA-256 of its hash list (`hash_data` in the prelude) is `8f1734742943c72d86dccb5988801855cc0bae340190934b35bc7af6e8db6cfe`, with `./state.sqlite3` at `9dcea9dee400bd47bbb898485897d4ba5e7267619be44b40890734dbd8c9d398`. While that SHA-256 holds, F1–F3 stand. The only backup is `backups/stage2-pre-campaign-20261021T180646Z`, from before the Stage 2 campaign. 455 GiB were free.
- **F8 — Time.** Plan 2's window ended 2026-11-05T13:00:00Z (plan 2 D13), so Stage 2b sets its own window at Task 4. The open quarter stays 2026Q4 until 2027-01-01T00:00:00Z. Daily bodies after 2026-10-30 are not registered yet (plan 2 trap (d)). Each business day adds one.
- **F9 — Stage 2 request counts.** Invocation 4 on the live config made 75 attempts and received 95,057,260 bytes, most of it the 26 first quarterly downloads (`specs/evidence/baseline-campaign/final/audit.json`). The 28 quarterly snapshots are now retained, so later runs reuse them. The open quarter's snapshot is downloaded again when its bytes change: 2026Q4 has three snapshot worksets.
- **F10 — The runbook count.** `docs/runbooks/local-ingestion.md:66` says "Retained whole-source quarantines remain 21 conflicting observations in 2010Q1, 24 in 2015Q1 and 6 in 2026Q3, total 51." No local record gives the method behind these counts. 2010Q1 and 2015Q1 are outside the campaign range.

## Global Constraints

Every task's requirements include these lines.

- Release: `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec` (application 0.2.0, `git_revision` `32863852ce57f1da99db4720bd1c729727b4ec0c`), manifest `/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json`, selected at `4d1f806c70a522ce377b5c0391c9287ba2c246d7`. Evidence: `specs/evidence/stage2a/release.md`, `gate.md`.
- Live config: `conf/sec-edgar-local.json`, file SHA-256 `7d61c3e2da7fd4e88eea5aaf65ab10e4b7a36b9b96d5c6e7f70a3a69429bafda`, effective SHA-256 `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733`. Backfill `2020Q1` through `open`; daily handoff `2026-10-01`; parser / schema `sec-index-parser-v2` / `sec-index-v2`; `reconciliation.require_withdrawal_approval=true`. Do not edit it. Every invocation runs it. Never run a config under `conf/stage2/`.
- Dispatch reserve 1,800 s; floor 480 s; launcher default 3,300 s; live maximum 3,600 s. At 3,300 s the runner starts no member after 1,500 s, and a member running at that cutoff completes (§4.7).
- Release history: the 1c release `c4de77b8…` wrote this store last. After the first v2 write, selecting the 1c release or any older release for this store is unsupported (§4.9; 2a spec D10). Never change `runtime.release_manifest` during or after the campaign. The Task 3 backup is the only way back to a store the 1c release can read.
- Requested units: the 28 quarterly sources 2020Q1–2026Q4 (2026Q4 is open), and the 7 daily duplicate-key sources 2026-07-08, 2026-07-13, 2026-07-22, 2026-07-27, 2026-09-17, 2026-09-24 and 2026-10-21. Every other daily source runs as retained work. The finding reports it apart, for Stage 3.
- No parser, schema, runtime, storage, config or release change. No `--force`. No `approve`, `rollback`, `daily`, `reconcile` or low-level command on the live store (D3). No pointer edit or object deletion. A candidate that the C6 equivalence check refused stays in the store (§4.6; `docs/runbooks/local-recovery.md`, row "Refused incremental candidate").
- During the campaign window, the launcher is the only SEC client under the owner identity (§4.3). Do not send manual `curl`, browser or other requests with the owner User-Agent.
- Read store contents only through `scripts/baseline-campaign.py`, the release's validated readers, or a scratch copy under the ignored `logs/`. Do not open `data/` in an editor, Finder or Quick Look. Never read the store while the launcher runs.
- Put no campaign evidence under `/tmp` or `/private/tmp`. Committed evidence goes under `specs/evidence/stage2b/`. Raw evidence stays in the ignored `data/`, `logs/` and `backups/`, cited by path and SHA-256. Stage 2's records under `specs/evidence/baseline-campaign/` stay unchanged.
- Do not run `scripts/accept-sec-native.py` or `scripts/verify-sec-native-adjudication.py` (plan 7, Handoff, traps). Do not repeat acceptance (§6).
- Do not infer completeness from an exit code, latest filing date, directory presence or one nonempty captured quarter (§7). Keep approved incomplete coverage distinct from complete coverage.
- Shell prelude: shell state does not persist between steps, so every shell step starts with these lines. The shell is zsh.

```sh
project=/Users/lowell/Projects/sec-edgar-local
release="$project/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec"
native() { "$release/venv/bin/python" -I -B -X pycache_prefix=/dev/null "$@"; }
tool() { native "$project/scripts/baseline-campaign.py" "$@"; }
hash_data() { (cd "$project/data" && find . -type f | LC_ALL=C sort | xargs shasum -a 256); }
evidence="$project/specs/evidence/stage2b"
campaign_logs="$project/logs/stage2b"
cd "$project"
```

- Plan 2 blocks: several steps below run a named command block of plan 2 (`specs/plans/completed/2-sec-filing-index-ingestion-spec.md`) after this prelude. Those blocks write through the prelude names, so they write to this campaign's directories. Where a block names a Stage 2 path or value literally, its step gives the substitution. Apply exactly the substitutions that the step names, and no others.

## Review Focus

- **A long member that starts near the cutoff.** The owner expects a run that defers cleanly, not a deadline kill with no result. Task 2 measures the largest members in true order, and D2 stops the plan before any live run when one exceeds 1,440 s. Task 2 found one (3,239.6 s, the daily 2026-07-01). D6 records the owner's exception.
- **A store that holds v1 and v2 generations at once.** The owner expects the coverage report to read both and say which is which. Task 1's test reads a v1 generation and a v2 generation under the v2 config.
- **The gated 2026Q3 member on every later run.** The owner expects the campaign to finish while 2026Q3 waits for Stage 4. Task 2 Step 4 measures the gated retry, and stop rule 12 does not count `awaiting_approval` as eligible work.
- **New daily sources that publish back-dated 2026Q3 rows after the gate.** Their members also end `awaiting_approval` and are re-run on each invocation. The owner expects them to be named, not lost. Task 6 Step 2 lists every daily member that ends `awaiting_approval`, and the finding reports them for Stage 3.
- **A gate or quarantine that F3 and the 2a scratch run did not predict.** The owner expects the campaign to stop and report, not run on. Stop rule 9 halts on it, and Task 5 Step 5 records the `gated` and `quarantined` lists after each invocation.

## Decisions

- **D1** (owner, planning, 2026-11-05): Accept the full re-processing of all 127 registered members under v2 (F1), with a revised budget. No engine change. Applied in: Global Constraints, Tasks 3–5.
- **D2** (owner, planning, 2026-11-05): Measure the largest members in true dispatch order on a scratch copy. If every predicted member wall is at most 1,440 s (1.25 × wall ≤ the 1,800 s reserve), `max_member_wall_seconds` becomes 1,440, with no config change. If one is above, the plan stops for an owner decision. Applied in: Task 2, Task 3.
- **D3** (owner, planning, 2026-11-05): Leave 2026Q3 gated. Stage 2b runs no `approve`. Stage 4 reviews and disposes of the gate. Applied in: Global Constraints, Task 3 (stop rules), Task 7.
- **D4** (owner, planning, 2026-11-05): Take a fresh stopped-writer backup before the first v2 invocation. Applied in: Task 3.
- **D5** (owner, plan review, 2026-11-06): Approve defaults O1–O6 as written. Task 4 still asks for the window and the budget again. Applied in: Tasks 3–4.
- **D6** (owner, execution, 2026-11-06): Task 2 measured the daily 2026-07-01 member at 3,239.6 s, above D2's 1,440 s (`specs/evidence/stage2b/pre-campaign.md`). It is the first v2 write to 2026Q3, so the cost is real in the live run. The owner chose the exception ("Exception, O3 3600"). The runtime per invocation (O3) becomes 3,600 s, the live maximum, and `max_member_wall_seconds` becomes 3,600. D2's 1.25× margin is waived for that member. Its margin is about 360 s (11%) from a start at time 0. A start after about 360 s ends in a deadline kill, and stop rule 2 then halts the campaign. Task 4 asks whether one rerun may follow such a halt. The next largest member, 2026Q1, measured 1,398.8 s. Applied in: Tasks 3–4.

## Defaults for owner review

The owner approved these as written at plan review on 2026-11-06 (D5). Task 4 asks for the window and the budget again, with Task 2's measurements in front of the owner.

- **O1 — Budget** (`campaign.json`). `max_invocations` 30, `max_request_attempts` 2,500, `max_request_attempts_per_invocation` 700, `max_distinct_urls` 300, `max_received_bytes` 1,073,741,824. Basis: about 13 invocations for the 25 closed quarterly members at about 2 for each run (F2, F4), 2 for the dailies, 3 for 2026Q1–2026Q4, and a margin; about 50 attempts for each run (F9).
- **O2 — Window.** It starts at the Task 4 approval and ends at 2026-11-20T13:00:00Z. It must end before 2027-01-01T00:00:00Z, so that `open` stays 2026Q4.
- **O3 — Runtime per invocation.** 3,600 s, the live maximum (D6). The launcher default of 3,300 s leaves about 60 s of margin for the 2026-07-01 member. At 3,600 s the runner starts no member after 1,800 s.
- **O4 — Halt on an unexpected gate or quarantine.** Stop rule 9 is new. 2a spec §6 expects no quarantine, and F3 expects 2026Q3 as the only gate.
- **O5 — Other daily sources.** The other 78 registered daily sources (89 members) and the bodies after 2026-10-30 run as retained work, and the finding reports them for Stage 3. A run that lists bodies after 2026-10-30 meets the revisit condition of deferred item 2 (`specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`). The finding reports the evidence. Stage 2b does not diagnose it.
- **O6 — Coverage inputs.** Only Stage 2b's results feed the coverage report. Stage 2's finding stays as history.

## File structure

| Path | Responsibility | Task |
| --- | --- | --- |
| `scripts/baseline-campaign.py` | Evidence tool: adds each published quarter's `schema_version` | 1 |
| `packages/sec-edgar-ingest/tests/test_baseline_campaign.py` | Tool test for v1 and v2 generations | 1 |
| `specs/evidence/stage2b/scratch/order-timing.py` | Timing of the largest members in dispatch order, on a scratch copy | 2 |
| `specs/evidence/stage2b/pre-campaign.md`, `pre-campaign/` | Store check, preflight, timing, files and backup records | 2, 3 |
| `specs/evidence/stage2b/campaign.json`, `campaign.md` | Budget; scope, stop rules and approval | 3, 4 |
| `specs/evidence/stage2b/invocations.md`, `invocations/` | Ledger and one record for each invocation | 5 |
| `specs/evidence/stage2b/final/`, `quarantine/` | Final coverage, audit, timing, files; enumerations if any | 6 |
| `specs/evidence/stage2b/coverage-finding.md` | The revised G2 finding | 7 |
| `docs/runbooks/local-ingestion.md:66` | The retained-quarantine sentence | 7 |

---

### Task 1: The evidence tool reports each generation's schema (offline, TDD)

**Files:**
- Modify: `scripts/baseline-campaign.py` (`quarter_view`)
- Test: `packages/sec-edgar-ingest/tests/test_baseline_campaign.py`

**Interfaces:**
- Consumes: `v1_writable()` from `packages/sec-edgar-ingest/tests/support_etl.py`, which lets a test write a v1 base.
- Produces: `quarter_view(...)` returns `'schema_version'` (the manifest's value) for a published quarter. Tasks 5–7 read it from each unit's `filing_quarter`.

- [ ] **Step 1: Write the failing test**

In `FixtureStoreTests`, give `harness()` an optional `schema_version` that it passes in `etl` next to `parser_version`. `harness()` may now run more than once on one root: build the fixture pack only on the first call, and reuse it after. Then add:

```python
def test_coverage_reads_v1_and_v2_generations_and_reports_each_schema(self):
    quarterly = {2: LATE_KEY_IN_Q2, 3: Q3, 4: Q4}  # Q2 lists the late daily key, so no quarter gates
    with v1_writable():
        old = self.harness(quarterly, schema_version='sec-index-v1')
        code, daily = old.invoke('daily', run='d1', attempt='a1')
        self.assertEqual(code, 0, old.calls[-1])
        old.close()
    # The fixture default config (sec-index-v2) reads the v1 generations.
    code, report = self.coverage(self.harness(quarterly), daily['result_ref'])
    published = [unit['filing_quarter'] for unit in report['units'] if unit['filing_quarter']['status'] == 'published']
    self.assertTrue(published)
    for view in published:
        self.assertEqual(view['schema_version'], 'sec-index-v1')
        self.assertEqual(view['validated_rows'], view['row_count'])
    h = self.harness(quarterly)
    code, message = h.invoke('backfill', run='r1', attempt='a1')
    self.assertEqual(code, 0, h.calls[-1])
    code, report = self.coverage(h, message['result_ref'])
    self.assertTrue(report['complete'])
    self.assertEqual({unit['filing_quarter']['schema_version'] for unit in report['units']}, {'sec-index-v2'})
    # F1: the daily member that completed under v1 runs again under v2, so r1 lists it as a member.
    self.assertEqual({item['run_id'] for item in report['daily_sources']}, {'r1'})
```

- [ ] **Step 2: Run the test to verify that it fails**

```sh
cd /Users/lowell/Projects/sec-edgar-local
UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never uv run --offline --locked --package sec-edgar-ingest \
  python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests \
  -p test_baseline_campaign.py -v
```

Expected: 1 error, `KeyError: 'schema_version'`, in the new test. The other 16 tests pass.

- [ ] **Step 3: Add `'schema_version': manifest.schema_version` to the published mapping in `quarter_view`**

- [ ] **Step 4: Run the tests to verify that they pass**

Run the Step 2 command. Expected: `Ran 17 tests`, `OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/baseline-campaign.py packages/sec-edgar-ingest/tests/test_baseline_campaign.py
git commit -m "feat(evidence): report each published quarter's schema version"
```

---

### Task 2: Store check, preflight and member timing in dispatch order (offline, D1, D2)

**Files:**
- Create: `specs/evidence/stage2b/scratch/order-timing.py`
- Create: `specs/evidence/stage2b/pre-campaign/preflight.json`, `order-timing.jsonl`, `convergence.json`
- Create: `specs/evidence/stage2b/pre-campaign.md` (sections `Store check`, `Preflight`, `Member timing`, `Convergence`, `Wall limit (D2)`)

**Interfaces:**
- Consumes: F1–F7; the 2a scratch script `specs/evidence/stage2a/scratch/retransform.py` (its store opening, `new_context` and `locate` scan); `evaluate_member` (`workflows/completion.py:812`).
- Produces: the measured member walls, the convergence result, and `max_member_wall_seconds` (1,440 under D2, 3,600 under D6) for Task 3.

- [ ] **Step 1: Confirm the starting state**

```sh
# prelude
pgrep -fl -- '-m sec_edgar_ingest|scripts/sec-edgar-local|local-bootstrap|local_bootstrap' || echo 'no writer'
shasum -a 256 conf/sec-edgar-local.json
git log -1 --format='%h %s' -- scripts/baseline-campaign.py
hash_data | shasum -a 256
```

Expected: `no writer`; the file hash `7d61c3e2…` (Global Constraints); the Task 1 commit; the F7 list hash `8f173474…6cfe`. If the list hash differs, the store changed after planning: stop and report to the owner. F1–F3 must then be re-run with `planning/members.py` and `planning/gates.py` on a scratch copy.

- [ ] **Step 2: Offline preflight**

Run plan 2 Task 3c Step 3's block with `$evidence/pre-campaign/rev2` replaced by `$evidence/pre-campaign`.

Expected: `backfill` `["2020Q1", "open"]`, `dispatch_reserve_seconds` `1800`, `effective_config_sha256` `f2082322…` and `release_id` `e49d3ba8…`. Any difference stops the plan.

- [ ] **Step 3: Write `order-timing.py ROOT CONFIG RESULTS CONVERGENCE`**

The script opens ROOT with its stored binding and loads CONFIG, as `retransform.py` does. It creates no network client and never approves. It finds each target's snapshot workset with the `locate` scan of `worksets/sec/snapshot`. Where a source has more than one workset, it takes the one whose snapshot has the latest receipt time, and records every candidate. Before step 1, it reads the 2024Q1 active generation's manifest and picks D: the daily source with the earliest period among that manifest's daily sources.

Then it runs the steps below. Steps 2, 3 and 4 run in the ascending period order of their sources, as in F2. Step 3 is skipped when D is the 2026-07-01 source. Each step calls `run_transform` on the snapshot workset and then `run_publish` on the transformed workset, each with a fresh `new_context`. Steps 7 and 9 call only `run_publish`, with the transformed workset of the step before.

| Step | Source | Why |
| --- | --- | --- |
| 1 | quarterly 2024Q1 `b2d153963f7d7f903ea8c4d2fcb4b6cf58e8d12ffa633ddc82cb57de0131fd63` | The largest closed quarter before the dailies (F2) |
| 2 | daily 2026-07-01 `924fd5f5b380e8a8603bab21b91edcd9408962b3a25fe812f067b25777063d58` | The first daily: the first v2 rebuild of 2026Q3 |
| 3 | daily D | A daily whose 2024Q1 rows meet a v2 quarterly authority (convergence) |
| 4 | daily 2026-10-01 `6cf7f339fd98f08d888586fbf41d907cb071d3a54259128e659f51e1f7caaa72` | The first daily in 2026Q4: the first v2 rebuild of 2026Q4 |
| 5 | quarterly 2026Q1 `f8f05c9fd9e634303de40171631df987c8977b784ebd5919c1896e4e13d2ed12` | The largest quarterly source (370,363 keys) |
| 6 | quarterly 2026Q3 `5005901a1e8132207ea0cf7a0d4bec1d7b9ca3a6f0371b9e45c9eb2863045086` | The expected gate |
| 7 | 2026Q3 publish again | The gated retry (F5) |
| 8 | daily 2026-09-24 `d2c80002601d76fb076f7141eb07bb5c0c995f56ffe1f3dbed1a9bd427805dd2` | Proxy, out of order: a daily new to 2026Q3 after the gate, as each body discovered after the gate will be |
| 9 | 2026-09-24 publish again | That daily's retry on each later run |
| 10 | quarterly 2026Q4 `d64895140b037ef3df3e0c867437b555053c3a14c33d8c0c3526c9067354d0c7` | The open quarter with a quarterly authority |

For each call, append one JSON line to RESULTS: `step`, `source_id`, `kind`, `period`, `call` (`transform` or `publish`), `outcome`, the per-quarter outcomes, gates and change counts (as `retransform.py` records them for 2026Q3), and `wall_seconds` from `time.monotonic()` around the production call only.

After step 10, the convergence check: for each stepped source, evaluate every registered member of it with `evaluate_member` under CONFIG's parser and schema versions. Write CONVERGENCE as a JSON list of `step`, `source_id`, `period`, `member_id`, `complete` and the gap codes.

On the copy, the closed quarters other than 2024Q1 stay v1 until a step publishes them. So steps 2–4 also rebuild the small daily-only quarters that they touch. In true order, those quarters are already v2 with a quarterly authority. Those walls can therefore only overstate the live cost.

- [ ] **Step 4: Run it on a scratch copy**

Run it in the background with the agent harness's background mode. Expect about 2–2.5 hours.

```sh
# prelude
pgrep -fl -- '-m sec_edgar_ingest|scripts/sec-edgar-local|local-bootstrap|local_bootstrap' || echo 'no writer'
stamp=$(date -u +%Y%m%dT%H%M%SZ); scratch="$campaign_logs/scratch-$stamp"
mkdir -p "$scratch" "$evidence/pre-campaign"
hash_data > "$scratch/before.sha256"
cp -Rp "$project/data" "$scratch/data"
native - "$project/conf/sec-edgar-local.json" "$scratch" <<'PY' > "$scratch/config.json"
import json, sys
value = json.load(open(sys.argv[1]))
value['storage']['root'] = sys.argv[2] + '/data'
value['logging']['root'] = sys.argv[2] + '/logs'
print(json.dumps(value, indent=2))
PY
native "$evidence/scratch/order-timing.py" "$scratch/data" "$scratch/config.json" \
  "$evidence/pre-campaign/order-timing.jsonl" "$evidence/pre-campaign/convergence.json"
echo "order-timing exit=$?"
hash_data > "$scratch/after.sha256"; cmp -s "$scratch/before.sha256" "$scratch/after.sha256" && echo data-unchanged
```

Expected:

- `no writer`, `order-timing exit=0` and `data-unchanged`.
- 18 lines in `order-timing.jsonl`: two for each of steps 1–6, 8 and 10, and one each for steps 7 and 9. 16 lines when step 3 is skipped.
- No `quarantined` outcome.
- 2026Q3 `awaiting_approval` in steps 6 and 7, with at least 42 withdrawals (F3; the 7 duplicate-key dailies did not run before the gate on the copy). Steps 8 and 9 are predicted to end `awaiting_approval` for 2026Q3 as well. A `published` outcome there is also valid evidence: record which.
- In `convergence.json`, each source of steps 1–5 and 10 has at least one complete member. Each member of the 2026Q3 source is incomplete with only `publication_pending`. The 2026-09-24 members are complete, or incomplete with only `publication_pending` when step 8 ended `awaiting_approval`.

Then remove the copy: `rm -rf "$scratch"`. Any other result stops the plan: report it to the owner. A daily member that stays incomplete after its quarter took a v2 quarterly authority is a feasibility blocker, not a timing matter: rule 10 would halt the campaign.

- [ ] **Step 5: Apply the wall limit (D2)**

```sh
# prelude
native - "$evidence/pre-campaign/order-timing.jsonl" <<'PY'
import json, sys
from collections import defaultdict
walls = defaultdict(float)
for line in open(sys.argv[1]):
    item = json.loads(line)
    walls[(item['step'], item['period'])] += item['wall_seconds']
for key, wall in sorted(walls.items()):
    print(key, round(wall, 1), 'over 1440' if wall > 1440 else 'ok')
print('max', round(max(walls.values()), 1))
PY
```

The member wall of a step is the sum of its calls. Every step counts, steps 8 and 9 included, because bodies discovered after the 2026Q3 gate pay those costs in the live run. If `max` is at most 1,440, Task 3 sets `max_member_wall_seconds` to 1440. Otherwise stop the plan and report the walls to the owner (D2).

- [ ] **Step 6: Write `pre-campaign.md` and commit**

Write the five sections. `Store check` gives the Step 1 values. `Preflight` gives the Step 2 values. `Member timing` is a table of each step's calls and walls, with each member wall against 1,440 s and against the 1,800 s reserve. It names D, and the costs of steps 7–9. Each body discovered after the 2026Q3 gate pays the step 8 cost once and the step 9 cost on each later run, before the 2026Q1–2026Q4 members (F2). `Convergence` gives the `convergence.json` result for each source. `Wall limit (D2)` states the result and the limit.

```bash
git add specs/evidence/stage2b/scratch/order-timing.py specs/evidence/stage2b/pre-campaign/ specs/evidence/stage2b/pre-campaign.md
git commit -m "docs(evidence): record the Stage 2b store check and member timing"
```

---

### Task 3: Pre-campaign backup and campaign files (offline, D3, D4)

**Files:**
- Create (ignored): `backups/stage2b-pre-campaign-<stamp>/`
- Create: `specs/evidence/stage2b/pre-campaign/files-before.json`, `backup-files.json`
- Create: `specs/evidence/stage2b/campaign.json`, `campaign.md`
- Modify: `specs/evidence/stage2b/pre-campaign.md` (append `Backup`)

**Interfaces:**
- Consumes: Task 2's `max_member_wall_seconds`; O1–O6; `tool files`.
- Produces: the verified backup path and `state.sqlite3` hash; `campaign.json`, which Task 5 audits against; `campaign.md` with an empty `Approval` section, which Task 4 fills.

- [ ] **Step 1: Record the live root**

```sh
# prelude
pgrep -fl -- '-m sec_edgar_ingest|scripts/sec-edgar-local|local-bootstrap|local_bootstrap' || echo 'no writer'
hash_data | shasum -a 256
du -sg "$project/data" | cut -f1
tool files --root "$project/data" --recorded specs/evidence/local-port/sec-acceptance.json \
  > "$evidence/pre-campaign/files-before.json"; echo "files exit=$?"
```

Expected: `no writer`, the F7 list hash, a size of about 1 GiB, and `files exit=0`. Step 2 records the size in the `Backup` section, for Task 5's growth check.

- [ ] **Step 2: Make the stopped-writer backup (D4)**

Run plan 2 Task 2 Step 3's block with `stage2-pre-campaign-` replaced by `stage2b-pre-campaign-`.

Expected: `exit=0`, and the comparison `{'added': [], 'changed_immutable': [], 'changed_state': [], 'missing': []}`. Append a `Backup` section to `pre-campaign.md` with the backup path, the backup `state.sqlite3` SHA-256, and the Step 1 size of `data/`.

- [ ] **Step 3: Write `campaign.json`**

```json
{
 "format_version": "sec-baseline-campaign-budget-v1",
 "max_distinct_urls": 300,
 "max_invocations": 30,
 "max_member_wall_seconds": 3600,
 "max_received_bytes": 1073741824,
 "max_request_attempts": 2500,
 "max_request_attempts_per_invocation": 700
}
```

These are D6 (the member-wall limit, in place of D2's 1,440) and O1. Use the values that the owner confirmed at plan review and in D6.

- [ ] **Step 4: Write `campaign.md`**

Title it `# Stage 2b baseline campaign: scope, budget and approval`, with plan 2's sections in plan 2's order. Cite; do not copy Stage 2's text.

- **Identity:** the release, the live config with both hashes, reserve and floor, the backup path, and the Task 1 commit of the evidence tool.
- **Release gate:** open on F1, F3, Task 2's member timing, and the Step 2 preflight. Live work still needs the Approval.
- **Source scope:** the launcher `backfill` workflow with the live config only. The requested units (Global Constraints). The dispatch order (F2). Expected exceptions: 2026Q3 `gated` (F3, D3); its later re-checks (F5); and daily members held `awaiting_approval` by that gate. Also a deadline kill of the 2026-07-01 daily member, when it starts after about 360 s into an invocation (D6). Stop rule 2 still halts on it.
- **Budget:** plan 2's Budget table with the `campaign.json` values, the runtime (O3), the window (O2), at least 50 GiB free before each invocation, and at most 30 GiB of store growth.
- **Stop rules:** after each invocation, apply the first rule that matches:
  1. **Halt** on a launcher exit of 2, 6, 8, 9 or 11, or any exit outside 0, 3, 4, 5, 7 and 10.
  2. **Halt** when the run left no `result_ref` or no `workflow_summary` (a deadline or crash, plan 2 F8). Follow `docs/runbooks/local-recovery.md` with the owner before any further invocation.
  3. **Halt** on a workflow outcome of `access_blocked`, `ownership_lost`, `state_conflict` or `internal_error`.
  4. **Halt** on any audit breach, any HTTP 403, or any `uncertain` transport attempt.
  5. **Halt** when the files comparison against L12 reports `missing` or `changed_immutable`.
  6. **Halt** when `workflow_summary.summary_error` is not null.
  7. **Halt** when the timing report has a breach: a member wall above `max_member_wall_seconds`.
  8. **Halt** when any member has outcome `invalid_source` and is not quarantined (C6; plan 2 O16). Read the member's gaps and report them.
  9. **Halt** when `after.gated` names a quarter other than 2026Q3, or `after.quarantined` is not empty (O4). Report the member's gaps and the gate's change counts.
  10. **Rerun** when `after.eligible` is not empty, and this is k = 1 or the previous invocation reduced its length. Halt when a rerun does not reduce it.
  11. **Halt** on the second consecutive invocation with `discovery_complete: false`, unless every `discovery_failed` directory lies under `https://www.sec.gov/Archives/edgar/daily-index/` and every discovery gap is `permit_expired` or `ancestor_failed` (plan 2 rule 10, option (a)).
  12. **Finish** when every quarter 2020Q1–2026Q4 has a campaign result and no member has outcome `pending`, `deferred` or `throttled`. Quarantined, failed and `awaiting_approval` members are not eligible work.

  A halt stops the campaign. The operator reports to the owner and does nothing else.
- **Evidence locations:** committed under `specs/evidence/stage2b/`; raw in `data/`, `logs/<run-id>/<attempt-id>/`, `logs/stage2b/` and `backups/`.
- **Approval boundary:** a live invocation needs the Release gate open, the Approval section completed with the owner's words and committed, the latest files check with exit 0, and the sole-issuer declaration. Never authorized: `approve`, `rollback`, `daily`, `reconcile`, a low-level command, any config or release change, a second root, object removal, or any SEC request outside the launcher.
- **Approval:** empty.

- [ ] **Step 5: Commit**

```bash
git add specs/evidence/stage2b/campaign.json specs/evidence/stage2b/campaign.md specs/evidence/stage2b/pre-campaign/ specs/evidence/stage2b/pre-campaign.md
git commit -m "docs(evidence): propose the Stage 2b campaign scope, budget and stop rules"
```

---

### Task 4: Owner live-execution gate (human checkpoint)

**Files:**
- Modify: `specs/evidence/stage2b/campaign.md` (`Approval`)

**Interfaces:**
- Consumes: `campaign.md`, `campaign.json`, `pre-campaign.md`.
- Produces: the Approval commit that Task 5 Step 1 checks.

- [ ] **Step 1: Ask the owner, one item per question, with a recommended option first**

1. The range and units: 2020Q1–2026Q4 (28 units) and the 7 duplicate-key daily sources.
2. The source scope, budget and stop rules in `campaign.md`.
3. The runtime per invocation: 3,600 s (O3, D6).
4. The window: its UTC start and end (O2).
5. The member-wall limit: 3,600 s under the D6 exception (D2's limit was 1,440 s), with Task 2's measured walls. Say that a late start of the 2026-07-01 member ends in a deadline kill, and that rule 2 then halts. Ask whether the operator may rerun once, without a new approval, after a halt of that kind.
6. The 2026Q3 gate: left gated for Stage 4, with no `approve` (D3).
7. Other daily sources, and bodies after 2026-10-30: run as retained work and reported for Stage 3 (O5).
8. A refused incremental candidate: halt, remove no objects, Stage 4 disposition (rule 8).
9. The backup: the Task 3 path and hash, the only way back to a store the 1c release can read.
10. The sole-issuer declaration, with plan 2's drafted wording: "During the campaign window, the launcher on this machine is the only SEC client under my identity. No other machine and not the original sec-edgar Azure project sends SEC requests under it."

- [ ] **Step 2: Record and commit**

Fill `Approval` with the owner's name, the UTC time of recording, and each quoted answer. A changed answer changes `campaign.md` or `campaign.json` in the same commit.

```bash
git add specs/evidence/stage2b/campaign.md specs/evidence/stage2b/campaign.json
git commit -m "docs(evidence): record the Stage 2b live-execution approval"
```

---

### Task 5: Campaign invocations (live, after Task 4)

**Files:**
- Create: `specs/evidence/stage2b/invocations.md`, `invocations/<k>-<run-id>.json`
- Create (ignored): `logs/stage2b/coverage-after-<k>.json`, `audit-after-<k>.json`, `timing-after-<k>.json`, `files-after-<k>.json`, `launcher-exit-<k>`, `invocation-<k>.json`

**Interfaces:**
- Consumes: the Task 4 Approval commit, `campaign.json`, and the Task 1 tool.
- Produces: the result refs and run IDs for Task 6, in `invocations/*.json`, each with an `after` block.

Repeat Steps 1–6 for k = 1, 2, … until a stop rule says finish or halt. Never start an invocation while another writer runs.

- [ ] **Step 1: Pre-check**

Run plan 2 Task 5 Step 2's block with `specs/evidence/baseline-campaign/campaign.md` replaced by `specs/evidence/stage2b/campaign.md`, and without its last three lines (`k=…`, `last=…` and the `daily_open` line).

Expected: `no writer`; the last `campaign.md` commit is the Task 4 Approval commit, or at k ≥ 2 a ledger commit after it that left `campaign.md` unchanged; the file hash `7d61c3e2…`; at least 50 GiB free; store growth over the Task 3 Step 1 size of at most 30 GiB; and a UTC time inside the approved window, with room for the timeout before the window ends. If any check fails, halt.

- [ ] **Step 2: Run one invocation**

Run plan 2 Task 5 Step 3's block with `config="$project/conf/sec-edgar-local.json"` and the approved timeout. Run it in the background with the agent harness's background mode, and wait for the exit notification.

Expected: an exit code. A run that deferred members at the cutoff ends `incomplete` or `pending` (exit 3 or 4). A run whose 2026Q3 member is gated can end with exit 10.

- [ ] **Step 3: Record the invocation**

Run plan 2 Task 5 Step 4's block with `grep -v '/logs/baseline-campaign/'` replaced by `grep -Ev '/logs/(baseline-campaign|stage2b|plan2-rev3|plan8-planning)/'`.

Expected: release `e49d3ba8…`, config hash `f2082322…`, backfill `2020Q1`–`open`, `1800`, a non-null `result_ref` and `ended_at`, and `True`. If the release, config hash or reserve differs, halt. If `result_ref` is null, still run Steps 4 and 5, then apply stop rule 2.

- [ ] **Step 4: Audit the budget**

Run plan 2 Task 5 Step 5's block unchanged.

Expected: `audit exit=0`, the run count equal to k, and `breaches: []`. Otherwise halt (rule 4).

- [ ] **Step 5: Coverage, timing and integrity after the invocation**

Run plan 2 Task 5 Step 6's block with two changes in its Python part. Delete the `if entry['k'] == 2:` block (its three lines). Before `record.write_text(…)`, add:

```python
entry['after']['gated'] = [unit['quarter'] for unit in value['units'] if unit['verdict'] == 'gated']
entry['after']['quarantined'] = ([unit['quarter'] for unit in value['units'] if unit['verdict'] == 'quarantined']
                                 + [item['period'] for item in value['daily_sources'] if item['quarantined']])
```

Expected: `coverage exit=0` and `files exit=0`. `timing exit=0`, or `timing exit=1` with a non-empty `after.timing_breaches` (rule 7). At k = 1, `after.already_complete` is empty (F1). Any other nonzero exit is a tool failure: halt and report it.

- [ ] **Step 6: Decide, log and commit**

Apply the `campaign.md` stop rules in order, as plan 2 Task 5 Step 7 describes, with rule 9 reading `after.gated` and `after.quarantined`, and rule 10 reading `after.eligible`. Append one row to `invocations.md`. Create it at k = 1 with plan 2's header, the title `# Stage 2b campaign invocations`, and the `Slice` column renamed `Config` (each row: `live`).

```sh
# prelude
k=$(ls "$evidence"/invocations/*-*.json | wc -l | tr -d ' ')
git add specs/evidence/stage2b/invocations.md specs/evidence/stage2b/invocations/
git commit -m "docs(evidence): record Stage 2b campaign invocation $k"
```

On Rerun, go back to Step 1. On Finish, go to Task 6. On Halt, report to the owner with the invocation record and stop the plan. The owner decides whether Task 6 runs on the evidence so far.

---

### Task 6: Final coverage, audit, timing and integrity (offline)

**Files:**
- Create: `specs/evidence/stage2b/final/coverage.json`, `audit.json`, `timing.json`, `files.json`
- Create: `specs/evidence/stage2b/quarantine/<period>.txt`, only for a source still quarantined

**Interfaces:**
- Consumes: `invocations/*.json`.
- Produces: the inputs for Task 7.

- [ ] **Step 1: Final full coverage, audit, timing and integrity**

Run plan 2 Task 6 Steps 1 and 2's blocks unchanged. The full check reads every published quarter once. At about 400 s for each full-size quarter (F5), expect about 3 hours. Run it in the background.

Expected: `coverage exit=0`, `audit exit=0`, `timing exit=0` and `files exit=0`. The check is `full`, with 28 units and no `published_unchecked`. F3 predicts `covered` 26, `covered_open_quarter` 1 and `gated` 1 (2026Q3), each unit with `schema_version` `sec-index-v2`. A different result is evidence for Task 7, not a reason to stop. `missing` and `changed_immutable` are empty.

- [ ] **Step 2: The 7 duplicate-key sources and the daily members held by a gate**

```sh
# prelude
native - "$evidence/final/coverage.json" <<'PY'
import json, sys
value = json.load(open(sys.argv[1]))
seven = {'2026-07-08', '2026-07-13', '2026-07-22', '2026-07-27', '2026-09-17', '2026-09-24', '2026-10-21'}
for item in value['daily_sources']:
    if item['period'] in seven or item['outcome'] == 'awaiting_approval':
        print(item['period'], item['period'] in seven, item['outcome'], item['quarantined'],
              [(quarter['quarter'], quarter['outcome']) for quarter in item['quarters']])
PY
```

Expected: 7 lines marked `True`, each with outcome `success`, `quarantined` false, and quarter outcomes `published` or `unchanged`. Each line marked `False` is a daily member held by the 2026Q3 gate. Task 7 §5 lists them.

- [ ] **Step 3: Enumerate a remaining quarantine**

For each quarterly unit that is still `quarantined`, run plan 2 Task 6 Step 3's block for its quarter. Expected: none, because 2a spec §6 found no quarantine left among the 35 sources.

- [ ] **Step 4: Commit**

```bash
git add specs/evidence/stage2b/final/
git commit -m "docs(evidence): record final Stage 2b coverage"
```

---

### Task 7: Revised G2 finding, owner dispositions, operating decision and runbook count

**Files:**
- Create: `specs/evidence/stage2b/coverage-finding.md`
- Modify: `docs/runbooks/local-ingestion.md:66`

**Interfaces:**
- Consumes: Task 6 outputs, `invocations.md`, `campaign.md`, `pre-campaign.md`, Stage 2's [coverage finding](../evidence/baseline-campaign/coverage-finding.md), and `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`.
- Produces: the revised G2 finding that the Stage 2b Exit requires, and that Stages 3–5 consume.

- [ ] **Step 1: Write the finding**

Title it `# Stage 2b baseline coverage finding (G2, revised)`. Use plan 2 Task 7's sections in its order. Take every number from the cited JSON files, and do not round counts. Changes from plan 2's sections:

- **§1 Result** names Stage 2's finding as history that this one revises.
- **§2 Campaign as run** reports the first v2 write (k = 1) and the re-run of all 127 members (F1).
- **§3 Baseline units** adds a `Schema` column from `filing_quarter.schema_version`.
- **§4 Exceptions** gives 2026Q3's gate with its change counts and the proposed disposition "deferred to Stage 4 manual reconciliation (D3)", and each other exception.
- **§5 Other output** lists the retained daily sources for Stage 3, the bodies after 2026-10-30, the daily members held by the gate (Task 6 Step 2), and the open-quarter daily members that ran after the 2026Q4 quarterly publish (the A1 class), with their walls.
- **§7 Evidence integrity** names the Task 3 backup.
- **§8 Deferred items** gives item 1's "Done when" verdict, and the revisit conditions of items 2 and 3 in the same section, with evidence.

- [ ] **Step 2: Owner dispositions and the operating decision**

Ask the owner one question for each exception in §4, and one for the decision. Offer "Complete" only when every unit is `covered` or `covered_open_quarter`. Otherwise recommend "Approved incomplete", with the named exceptions and the downstream limits. Record each answer with its option label.

- [ ] **Step 3: Replace the runbook count**

In `docs/runbooks/local-ingestion.md:66`, replace the sentence that begins "Retained whole-source quarantines remain" with one that gives the whole-source quarantines retained in 2020Q1–2026Q4 after Stage 2b, by kind and period, from `final/coverage.json`, citing this finding (plan 7, Handoff, trap "Stale count after a campaign"). With none left, the sentence says so. Keep the 2010Q1 and 2015Q1 counts in a separate sentence, marked as outside the campaign range and not checked by it (F10).

- [ ] **Step 4: Commit**

```bash
git add specs/evidence/stage2b/coverage-finding.md docs/runbooks/local-ingestion.md
git commit -m "docs(evidence): record the revised Stage 2b G2 finding"
```

## After the last task

Run the writing-plans Plan Completion Protocol, step 3a included. In step 3, tick item 1 of `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, with `→ done <date> (plan 8)` only when §8 of the finding shows its "Done when" met. Write the Handoff for Stages 3, 4 and 5 from what ships, including the 2026Q3 gate for Stage 4 and the daily members it holds for Stage 3. The review base for the whole-plan review is the commit that adds this plan: every task runs on `main`.

## Handoff to later stages

> Written at a halt, not at completion. Plan 8 stopped at Task 5 after invocation 2 (stop rule 10, 2026-11-06). Tasks 6 and 7 and the Plan Completion Protocol have not run, and the plan is not retired. A plan or revision that resumes Stage 2b carries this section forward. Evidence: `specs/evidence/stage2b/` (`invocations.md`, `invocations/*.json`, `startup-overhead.md`, `pre-campaign.md`, `campaign.md`).

- **Task 5 halt (2026-11-06).**
  - **What ran.** Tasks 1–4 as written, with D6 (the owner's exception to D2: runtime 3,600 s and `max_member_wall_seconds` 3,600). The owner approved all ten gate items (`f30f8c1`). Invocations 1 and 2 (runs `0746b217-d4ca-4f1d-9b05-d0c447b734ce` and `bdefaa5d-856d-4bc4-a621-018e66b6ef1e`) ended with exit 3 (`incomplete`). There was no breach, no HTTP 403 and no `uncertain` attempt. They made 76 request attempts and received 244,388 bytes. **No member was dispatched and no generation was published.** No `approve` ran.
  - **Why it halted.** The runner starts no member after deadline − 1,800 s. The work before the first dispatch took 1,809 s in invocation 1 and 2,715 s in invocation 2. That work has three phases: a quiet phase before discovery (904 s, then 1,093 s), discovery (349 s, then 862 s) and a quiet phase after discovery (556 s, then 760 s). Stop rule 10 halted the campaign because the eligible list grew from 113 to 117.
  - **Cost per registered member.** The two quiet phases cost about 7.05 s and 3.65 s for each registered member in each run. Registered members grew 127 → 155 → 208, because each new source workset registers its sources again as members. As an inference, a run that finds the same listing adds none (source worksets are content-addressed). Each new business day adds daily bodies and so a new workset. The cause of the per-member cost is not profiled. The guess is the `evaluate_member` passes in selection.
  - **Comparison with Stage 2.** On the 1c release, Stage 2 invocation 4 (the same live-config pattern) took 624 s before its first member, about 5 s for each registered member. On 2a the same work took at least about 3 times longer. So the cost also exists on 1c, and it rose on 2a. The member counts differ, so the comparison is indicative.
  - **D6 rests on a wrong premise.** D6 assumed the daily 2026-07-01 member (3,239.6 s offline) could start near time 0 of an invocation. No member can, because discovery and selection come first. That member ends after the 3,600 s deadline unless the work before dispatch takes under about 360 s. The run length is fixed at 3,600 s in code (`config.py`), so a longer run cannot be set.
  - **Store state.** The Task 3 backup `backups/stage2b-pre-campaign-20261106T174241Z` is unchanged and remains the way back. The state database now holds members registered under the v2 parser and schema. Nobody has checked whether the 1c release can still operate on it. `data/` has two SQLite side files, `state.sqlite3-shm` and an empty `state.sqlite3-wal`, which the `files` comparison allows.
  - **Authority.** The Task 4 approval stays on record in `campaign.md`. Stop rule 10 halted the campaign, and nothing further runs under it without the owner. Another invocation raises the member count if the listing has changed. Treat the approved window (to 2026-11-20T13:00:00Z) as closed in practice.
  - **Still open.** Item 1 of `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, has no `→ done` note. The retained-quarantine count in `docs/runbooks/local-ingestion.md` is unchanged. The gaps `baseline_publication_missing` (2022Q4, 2023Q1) and `legacy_member_unresolved` (one, no source named) were seen in invocation 1 and not followed up. Daily bodies after 2026-10-30 are now discovered (four more by 2026-11-05), which meets the revisit condition of deferred item 2. Plan 8 did not diagnose it.
- **Stages 3, 4 and 5.** Stage 2b has no finding. These stages cannot consume it, and plan 8's campaign left Stage 2's finding as the latest coverage record. The pre-dispatch cost probably comes from the runner's selection of registered members. It probably applies to every workflow command, but it was measured only for `backfill`.
