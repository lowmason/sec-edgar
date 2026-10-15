# Load-Flaky Multi-Process Tests Implementation Plan

**Status: COMPLETE (2026-10-14)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The offline suite passes on a busy machine. A fresh local store's switch to WAL waits out a competing initializer. Every test that times a real spawned child gives it windows that a slow spawn fits in. The one failure that is not about spawning names its cause.

**Architecture:** Planning reproduced three causes (see Evidence).

1. **WAL fast fail (production).** `LocalStateStore.__init__` (`storage/local.py`) runs `PRAGMA journal_mode=WAL` on a fresh store. That statement upgrades a read lock. While another connection holds RESERVED, SQLite refuses the upgrade at once with `SQLITE_BUSY` and does not call the busy handler, to avoid deadlock. The 5 s connection timeout therefore never applies, and the store's three unpaused retries can all land while another initializer finishes its switch. Task 1 keeps retrying, with a doubling pause, until that same 5 s, now named `SQLITE_BUSY_TIMEOUT_SECONDS`.
2. **Spawn latency (tests).** Tests that time a real spawned child use production windows: 1/3 s to start (the coordinator's `1 / requests_per_second`, or `real_permit`'s default) and 0.4 s or 0.8 s to finish. On a loaded host the spawn alone can take longer. Tasks 2–5 size those windows from one named allowance (`support.SPAWN_ALLOWANCE_SECONDS`). Where the real coordinator issues the permit, `support.spawn_tolerant_settings()` widens its windows with a lower fixture request rate and a later exchange deadline. Each task also adds a child that always starts 0.5 s late, so every run proves the windows absorb a slow spawn.
3. **Reservation-to-send stall (tests; explained, not fixed).** The in-process fixture transport refuses a permit once 1/3 s has passed since its reservation, so a stalled process loses one discovery listing. Every fixture workflow test shares this window, and widening it is a design choice (Decisions, default 5). Task 6 makes the one test that hit it print the cause; Plan completion defers the choice.

Production timing is unchanged apart from Task 1. The coordinator, `REQUEST_BUDGET_PER_SECOND`, the fixture config and the bounded sender keep their windows.

**Tech Stack:** Python 3.14; stdlib `unittest`, `sqlite3` and `multiprocessing` (spawn), run through `tests/network_guard.py`; uv workspace (`--offline --frozen`).

**Spec:** none (spec-less `/deferred` plan, 2026-10-14). The requirement is the deferred item "Load-flaky multi-process tests" in `specs/deferred_items.md`, section `6-sec-filing-index-ingestion-stage-5-spec — 2026-10-11`. Its closure condition: *Done when: the WAL open retries or the tests serialize, the deadline-bound tests tolerate a slow spawn (and the timer test deletes its trace in a `finally`), and several consecutive full-suite runs pass.* Roadmap Stage 7 needs this item closed before it starts (`specs/sec-filing-index-ingestion-roadmap.md`, "Stage 7 resume — 2026-10-14").

**Branch and BASE:** worktree `.claude/worktrees/deferred-f9741e` on branch `claude/deferred-f9741e`, cut from `main` at **BASE=`6400dba9`**. Per-task reviews and the final review diff against `6400dba9`.

## Global Constraints

- Offline only: every command uses `uv run --offline --frozen --package sec-edgar-ingest …`; no SEC, Azure, credential, deployment or trigger activity.
- Pinned dependencies unchanged (`pyproject.toml`, `uv.lock` untouched).
- Lean process (`lean-stage-process`): red/green TDD per task, a review per task, a final whole-branch review, then the full offline suite plus wheel build and CLI smoke (`scripts/check-sec-edgar-ingest.sh`). No evidence bundles, hash-bound snapshots or preservation audits.
- Production timing stays as it is. Do not edit `coordination.py`, `download.py`, `config.py` (including `REQUEST_BUDGET_PER_SECOND = 3`) or `tests/fixtures/config/local.json`. In `src/`, only `storage/local.py` changes.
- No new state kinds; the Azure adapters need no change (`storage/azure.py` has no WAL setup or init retry).
- The full offline suite must print nothing to stdout (`unittest -v` reports on stderr).
- Do not edit `specs/evidence/`; its historical patches still name `SQLITE_INIT_ATTEMPTS`.
- Scratch scripts and logs go under `/tmp/plan11/`, never into the repository.
- End each commit message with a blank line, then the `Co-Authored-By` line for the model that wrote the commit: `Claude Opus 5.5`, `Claude Sonnet 5.5` or `Claude Haiku 5.5`, each with `<noreply@anthropic.com>`. The commit steps below show the Sonnet line; an implementer on another model uses its own. Work stays on this branch, never on `main`.
- Do not push, open a PR, merge or deploy. Integration goes back to the owner.

Single-file test command, from the repository root. Add `-k <substring>` to select tests; repeat `-k` to OR them.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_storage.py' -v
```

## Decisions

- **D1** (owner, plan review, 2026-10-14): Plan approved as written, with all five defaults below accepted. Execute via subagent-driven-development in a fresh Sonnet session, in this worktree. Applied in: whole plan.

**Defaults set while planning (approved at plan review, D1):**

1. **"The WAL open retries", not "the tests serialize".** On `SQLITE_BUSY` from the WAL switch, the store pauses 1 ms, doubling up to 50 ms, and retries until `SQLITE_BUSY_TIMEOUT_SECONDS` (5 s, the existing connection timeout) has passed. A cross-process file lock would also work, but it adds a file to every store root. This changes a contract from 2026-10-06: `test_coordination`'s WAL contention test asserts that a persistent startup lock fails closed after exactly three attempts. Under Task 1 it still fails closed, but after the busy timeout, so a store blocked by a lock that is never released now takes 5 s to refuse instead of milliseconds. No spec names the attempt count; it lives only in that test, completed plan 9 and `specs/evidence/`. Task 1.
2. **One named allowance.** `SPAWN_ALLOWANCE_SECONDS = 3`, about 3× the slowest spawn measured at load average 26, sizes every window a test must sit through. Waits that return as soon as a process is ready use `SPAWN_WAIT_SECONDS = 30`, which only bounds a hang. Tasks 2–5.
3. **A built-in slow spawn in every task.** A child that sleeps `SLOW_SPAWN_SECONDS = 0.5` first overruns every production window on any machine. It supplies each task's red step and then stays in the tests, so every run proves the new windows absorb a slow spawn. Tests that already sit through their deadline pay nothing for it; other cases pay 0.5 s each. Tasks 2–5.
4. **Some tests run longer.** A test that must sit through its deadline, or through the coordinator's pacing, now waits out 3 s windows. At 1/3 request per second, each request gets a 3 s start window plus 3 s before the next. Measured on the final candidate: `BoundedProcessTests` 14 tests in 32 s; the five acquisition-process tests plus the runner test in 38 s. The held-socket proof goes from about 7 s to about 29 s. In total about +60 s of test time. Full-suite runs under the same load could not separate that from run-to-run noise: BASE took 2,159 s beside 6 burners, the plan 1,984 s.
5. **The fixture reservation-to-send stall is explained, not fixed.** There are two ways to widen the fixture transport's 1/3 s window. A lower request rate in every workflow test's settings slows each discovery several-fold. A new fixture-only setting means a change to production config. Both are design choices, so this plan only makes the affected test print its discovery gaps and defers the choice (Plan completion). Task 6.

## Evidence gathered while planning (2026-10-14; scratch scripts in `/tmp`, nothing committed)

- **WAL fast fail.** Hold RESERVED on a fresh store from a raw connection (`BEGIN IMMEDIATE`). `LocalStateStore(root)` then raises `OperationalError('database is locked')` (code 5) after 0.001 s, despite `timeout=5`.
- **WAL race.**
  - Setup: six spawned workers each built `LocalStateStore` and `LocalLeaseStore` on the same fresh root, for 1,000 rounds beside 14 CPU burners.
  - Result: 29 of 6,000 inits failed, all at `storage/local.py:185` (`PRAGMA journal_mode=WAL`). With Task 1's retry, monkeypatched in, 0 of 6,000 failed.
  - Three workers with no added load (host load average about 7): 2 of 900 failed.
- **Spawn latency**, from `Process.start()` to the child's first line, with the child importing `sec_edgar_ingest.download`. 20 samples at load average 26 on 14 cores: median 0.15 s, p90 0.65 s, max 1.03 s.
- **Baseline beside 14 CPU burners** (load average 22–47), 12 runs per test:
  - Timer test: 12/12 failed. `SenderFailure: HTTP child reported an unconfirmed outcome`: the child was killed at the 0.4 s deadline before it wrote its outcome.
  - Independent-child test: 12/12 failed, with `independent child timer failed while supervisor was stalled` or `0 not greater than 0`.
  - Held-socket test: 12/12 failed with `old child did not reach held loopback`.
  - Runner deadline test: 0/12.
  - Three-process coordination test: 0/12. The WAL race fails about 0.5% of inits, so 12 runs rarely hit it.
- **Full suite of BASE beside 6 CPU burners** (load average about 13): 836 tests in 2,159 s, five failures, all in `test_download.BoundedProcessTests`. In each one, a child missed a production window:
  - the supervisor-crash test: `spawn child must reach the selected loopback before supervisor crash`;
  - the delayed-adapter test: its first child refused a stale dispatch window (`permit_expired`);
  - both received-cap modes: `'permit_expired' != 'received_limit'`, then `2 != 1` on the first mode's leftover trace;
  - the IPC-loss test: `b'' != b'retained after IPC loss'`.

  The class's other tests use the same windows, so Task 3 covers the whole class.
- **The plan applied literally** (every replace block, in order) to a `git archive` of BASE, then the full suite beside the same 6 burners: 839 tests in 1,984 s. The five `BoundedProcessTests` failures were gone. One existing test failed: `test_coordination`'s WAL contention test, which pinned the old three-attempt contract (`[5, 5, …] != [5, 5, 5]`). Task 1 now moves that test to the new contract. The received-cap `finally` (Task 3) was added after this run; it changes failure paths only.
- **Full-core stress of the plan copy** (Plan completion 1a beside 14 burners, load average about 36): 5 runs each of `BoundedProcessTests`, `test_acquisition_processes` and the three-process coordination test, all passing. `wal_race.py` (Task 1 Step 5) beside 14 burners: 5 of 6,000 inits failed on BASE, none with the plan. Task 1's three timing tests (two new, one updated, each with a 0.2 s budget) beside 14 burners: 30 runs each, all passing.
- **Each red step below was run on a scratch copy** built by applying this plan's replace blocks literally to a `git archive` of BASE. Each fails as its "Expected" line says. The scratch scripts ran as written; for the plan copy, only their paths were pointed at it. The final candidate of Tasks 2–6 passes:
  - `BoundedProcessTests`: 14 tests, 32 s.
  - `test_acquisition_processes` plus the runner test: 6 tests, 38 s.
  - Held-socket test: 4 of 4 runs beside a loaded full suite.
- **Runner test.**
  - Not reproduced in 12 runs beside 14 CPU burners, nor in 15 rounds of its discovery beside 8 fsync burners and 6 CPU burners.
  - A 0.4 s sleep injected before the fixture send of `full-index/2026/QTR3/index.json` reproduces it exactly: 1 member instead of 2. The gaps are `ownership_lost` ("exchange stopped without a confirmed transport outcome: fixture transport refuses a cancelled or expired permit") and `baseline_source_missing` for 2026Q3.
  - `_FixtureSender.send` (`download.py:744`) refuses a permit once 1/3 s has passed since `Turn.reserve`.
- **Production note (not changed here).** Each `BoundedSender` request spawns a child that must start within the same 1/3 s. A slow spawn ends in `permit_expired`, which `RequestClient._outcome` treats as non-retryable, so the source waits for the next run. Plan completion records this as a watch item for Stage 7's live smoke.

## File structure

| File | Change | Task |
|---|---|---|
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py` | `SQLITE_BUSY_TIMEOUT_SECONDS` and two pause constants replace `SQLITE_INIT_ATTEMPTS`; the init loop retries BUSY until the timeout | 1 |
| `packages/sec-edgar-ingest/tests/test_storage.py` | New `LocalStateInitTests` | 1 |
| `packages/sec-edgar-ingest/tests/test_coordination.py` | The WAL contention test's persistent-lock case moves from "exactly three attempts" to "retried until the busy timeout, then refused" | 1 |
| `packages/sec-edgar-ingest/tests/support.py` | Task 2: spawn constants and slow-spawn children. Task 3: `spawn_tolerant_settings`, `LoopbackServer(drip_seconds=…)`, `crash_supervisor` settings. Task 5: held-socket proof settings, waits and pacing check | 2, 3, 5 |
| `packages/sec-edgar-ingest/tests/test_download.py` | Task 2: `send()` start window and the timer test. Task 3: `BoundedProcessTests` defaults, a slow-spawn test and the deadline-bound tests | 2, 3 |
| `packages/sec-edgar-ingest/tests/test_acquisition_processes.py` | Independent-child and stale-sender windows | 4 |
| `packages/sec-edgar-ingest/tests/test_workflow_runner.py` | The discovery precondition reports its gaps | 6 |

---

### Task 1: A fresh store's WAL switch waits out a competing initializer

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py:27` (constant), `:181-196` (init loop), `:201` (`_connection`)
- Test: `packages/sec-edgar-ingest/tests/test_storage.py` (imports at the top; new class at the end of the file)
- Test: `packages/sec-edgar-ingest/tests/test_coordination.py:208-269` (`test_local_constructor_recovers_real_wal_transition_contention_and_skips_warm_transition`, which pins the old three-attempt contract)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `storage.local.SQLITE_BUSY_TIMEOUT_SECONDS = 5`, the busy timeout of every state connection and the retry budget for store creation. Also `SQLITE_INIT_FIRST_PAUSE_SECONDS = 0.001` and `SQLITE_INIT_MAX_PAUSE_SECONDS = 0.05`. `SQLITE_INIT_ATTEMPTS` is removed. No other code references it; completed plan 9 and `specs/evidence/` name it as history and stay unchanged. `LocalLeaseStore` builds a `LocalStateStore`, so it gets the retry too; `local.py:185` is the only WAL switch in the package.

- [x] **Step 1: Write the failing tests**

In `packages/sec-edgar-ingest/tests/test_storage.py`, replace the import block at the top:

```python
import hashlib
import importlib
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
```

with:

```python
import hashlib
import importlib
import importlib.util
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
```

Append this class at the end of the file:

```python


class LocalStateInitTests(unittest.TestCase):
    """A fresh store's WAL switch must wait out another initializer, within the connection busy timeout."""

    def setUp(self):
        self.local = importlib.import_module("sec_edgar_ingest.storage.local")
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def hold_reserved(self):
        # Act as another initializer between its RESERVED and EXCLUSIVE locks. SQLite then refuses the
        # store's read-lock upgrade at once, without its busy handler: the race seen in parallel test runs.
        holder = sqlite3.connect(self.root / "state.sqlite3", isolation_level=None, check_same_thread=False)
        self.addCleanup(holder.close)
        holder.execute("BEGIN IMMEDIATE")
        return holder

    def test_init_waits_out_a_competing_wal_switch(self):
        holder = self.hold_reserved()
        release = threading.Timer(0.3, holder.execute, ("COMMIT",))
        release.start()
        self.addCleanup(release.join)
        started = time.monotonic()
        store = self.local.LocalStateStore(self.root)
        self.addCleanup(store.close)
        self.assertGreaterEqual(time.monotonic() - started, 0.25)
        with store._connection() as connection:
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_init_gives_up_when_the_busy_timeout_expires(self):
        self.hold_reserved()
        with patch.object(self.local, "SQLITE_BUSY_TIMEOUT_SECONDS", 0.2):
            started = time.monotonic()
            with self.assertRaises(sqlite3.OperationalError) as raised:
                self.local.LocalStateStore(self.root)
        self.assertGreaterEqual(time.monotonic() - started, 0.15)
        self.assertEqual(raised.exception.sqlite_errorcode & 0xFF, sqlite3.SQLITE_BUSY)
```

`test_coordination.py`'s WAL contention test pins the old contract: under a startup lock that is never released, the store must refuse after exactly three attempts. Move it to the new contract, still failing closed, but once the busy timeout expires. It patches that timeout to 0.2 s so it stays fast. In `test_local_constructor_recovers_real_wal_transition_contention_and_skips_warm_transition`, replace:

```python
        import sqlite3
        from unittest.mock import patch
        from sec_edgar_ingest.storage.local import LocalStateStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = LocalStateStore(root)
```

with:

```python
        import sqlite3
        import time
        from unittest.mock import patch
        from sec_edgar_ingest.storage.local import LocalStateStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = LocalStateStore(root)
```

and replace:

```python
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        LocalStateStore(root)
                    self.assertEqual(busy, [sqlite3.SQLITE_BUSY]*3,
                                     "A persistent startup lock must fail closed after finite attempts")
                finally:
                    blocker.rollback()
```

with:

```python
                try:
                    with patch("sec_edgar_ingest.storage.local.SQLITE_BUSY_TIMEOUT_SECONDS", 0.2):
                        started = time.monotonic()
                        with self.assertRaises(sqlite3.OperationalError):
                            LocalStateStore(root)
                    self.assertGreaterEqual(time.monotonic() - started, 0.15)
                    self.assertGreater(len(busy), 1, "A busy startup lock is retried, not refused at once")
                    self.assertEqual(set(busy), {sqlite3.SQLITE_BUSY},
                                     "A persistent startup lock must fail closed once the busy timeout expires")
                finally:
                    blocker.rollback()
```

- [x] **Step 2: Run the tests to verify they fail**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_storage.py' -k LocalStateInitTests -v
```

Expected: `FAILED (errors=2)`:
- `test_init_waits_out_a_competing_wal_switch` raises `sqlite3.OperationalError: database is locked` within milliseconds.
- `test_init_gives_up_when_the_busy_timeout_expires` raises `AttributeError: <module 'sec_edgar_ingest.storage.local' …> does not have the attribute 'SQLITE_BUSY_TIMEOUT_SECONDS'`.

Then run the contention test:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_coordination.py' -k test_local_constructor_recovers_real_wal_transition_contention -v
```

Expected: `FAILED (errors=1)`. Its persistent-lock case raises the same `AttributeError` for `SQLITE_BUSY_TIMEOUT_SECONDS`, from the patch.

- [x] **Step 3: Implement the retry**

In `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py`, replace:

```python
SQLITE_INIT_ATTEMPTS = 3
```

with:

```python
# Every state connection waits this long for a lock. Creating a store also retries its WAL switch until then,
# because SQLite returns BUSY for that switch at once instead of waiting.
SQLITE_BUSY_TIMEOUT_SECONDS = 5
SQLITE_INIT_FIRST_PAUSE_SECONDS = 0.001
SQLITE_INIT_MAX_PAUSE_SECONDS = 0.05
```

In `LocalStateStore.__init__`, replace:

```python
        for attempt in range(SQLITE_INIT_ATTEMPTS):
            try:
                with self._connection() as connection:
                    if connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                        mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                        if mode != "wal":
                            raise Conflict("local state did not confirm WAL mode")
                    connection.execute("CREATE TABLE IF NOT EXISTS records (table_name TEXT NOT NULL, partition TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, version TEXT NOT NULL, PRIMARY KEY(table_name, partition, key))")
                    connection.commit()
                break
            except sqlite3.OperationalError as error:
                # Competing WAL transitions can return BUSY without honoring the busy timeout.
                # Closing the losing connection releases its read lock before bounded retry.
                if error.sqlite_errorcode & 0xff != sqlite3.SQLITE_BUSY or attempt == SQLITE_INIT_ATTEMPTS-1:
                    raise
```

with:

```python
        deadline = time.monotonic() + SQLITE_BUSY_TIMEOUT_SECONDS
        pause = SQLITE_INIT_FIRST_PAUSE_SECONDS
        while True:
            try:
                with self._connection() as connection:
                    if connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                        mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                        if mode != "wal":
                            raise Conflict("local state did not confirm WAL mode")
                    connection.execute("CREATE TABLE IF NOT EXISTS records (table_name TEXT NOT NULL, partition TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, version TEXT NOT NULL, PRIMARY KEY(table_name, partition, key))")
                    connection.commit()
                break
            except sqlite3.OperationalError as error:
                # Switching to WAL upgrades a read lock, so SQLite returns BUSY at once, skipping the busy handler
                # to avoid deadlock, while another initializer holds RESERVED. Closing the losing connection
                # releases its read lock; pause, then retry until the busy timeout every other lock wait gets.
                if error.sqlite_errorcode & 0xff != sqlite3.SQLITE_BUSY or time.monotonic() + pause > deadline:
                    raise
            time.sleep(pause)
            pause = min(2 * pause, SQLITE_INIT_MAX_PAUSE_SECONDS)
```

In `_connection`, replace:

```python
        connection = sqlite3.connect(self.database, timeout=5)
```

with:

```python
        connection = sqlite3.connect(self.database, timeout=SQLITE_BUSY_TIMEOUT_SECONDS)
```

`time` is already imported in `local.py`.

- [x] **Step 4: Run the tests to verify they pass**

Run both Step 2 commands. Expected: `Ran 2 tests` … `OK`, then `Ran 1 test` … `OK`.

Then run the store, state, lease and coordination modules:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_st*.py' -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_coordination.py' -v
```

Expected: both `OK`. The first pattern covers `test_state.py` and `test_storage.py`.

- [x] **Step 5: Show the race is gone under load (scratch, not committed)**

Write `/tmp/plan11/wal_race.py`:

```python
"""N spawned workers race to create the same fresh local store, R rounds, beside B CPU burners."""
import multiprocessing
import sys
import tempfile
from pathlib import Path


def burn(stop):
    while not stop.is_set():
        sum(range(10_000))


def race(roots, barrier, results):
    from sec_edgar_ingest.storage.local import LocalLeaseStore, LocalStateStore
    for root in roots:
        barrier.wait()
        try:
            LocalStateStore(Path(root)).close()
            LocalLeaseStore(Path(root)).close()
            results.put(None)
        except Exception as error:
            results.put(f"{type(error).__name__}: {error}")


if __name__ == "__main__":
    workers, rounds, burners = (int(value) for value in sys.argv[1:4])
    spawn = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory() as directory:
        roots = [str(Path(directory) / str(index)) for index in range(rounds)]
        barrier, results, stop = spawn.Barrier(workers), spawn.Queue(), spawn.Event()
        hot = [spawn.Process(target=burn, args=(stop,)) for _ in range(burners)]
        racers = [spawn.Process(target=race, args=(roots, barrier, results)) for _ in range(workers)]
        for process in hot + racers:
            process.start()
        failures = [error for error in (results.get(timeout=300) for _ in range(workers * rounds)) if error]
        stop.set()
        for process in hot + racers:
            process.join(30)
        print(f"inits={workers * rounds} failures={len(failures)}", *sorted(set(failures))[:3], sep="\n")
```

Run:

```bash
mkdir -p /tmp/plan11 && uv run --offline --frozen --package sec-edgar-ingest python /tmp/plan11/wal_race.py 6 1000 "$(sysctl -n hw.ncpu)"
```

Expected: `inits=6000 failures=0`. In planning, this script failed 5 of 6,000 inits on BASE (an earlier race script: 29 of 6,000) and none with this task.

- [x] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py packages/sec-edgar-ingest/tests/test_storage.py packages/sec-edgar-ingest/tests/test_coordination.py
git commit -m "$(cat <<'EOF'
fix(storage): retry a fresh store's WAL switch until the busy timeout

SQLite refuses the read-lock upgrade in PRAGMA journal_mode=WAL at once while
another initializer holds RESERVED, so three unpaused retries could all lose.
Retry with a doubling pause until the 5 s connection busy timeout instead. A
startup lock that is never released still fails closed, after the timeout
rather than after three attempts.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Named spawn allowances; the timer test absorbs a slow spawn

**Files:**
- Modify: `packages/sec-edgar-ingest/tests/support.py:18` (constants after `FIXTURE_CONFIG`), `:782` (two children before `stale_start_child`)
- Modify: `packages/sec-edgar-ingest/tests/test_download.py:11` (import), `:465-469` (`send()`), `:610-622` (timer test)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces, in `support`:
  - `SPAWN_ALLOWANCE_SECONDS = 3`;
  - `SPAWN_WAIT_SECONDS = 30`;
  - `SLOW_SPAWN_SECONDS = 0.5`;
  - `slow_spawn_timer_failure_child(transport, cancellation, channel)`;
  - `slow_spawn_child_exchange(transport, cancellation, channel)`, the real `download._child_exchange` after a 0.5 s sleep.

  Both children are module-level, so spawn can pickle them as `target=`.
- Produces, in `BoundedProcessTests.send()`: keyword `start_seconds` (default `1/3`), passed to `real_permit`.

- [x] **Step 1: Write the failing case**

In `packages/sec-edgar-ingest/tests/support.py`, replace:

```python
FIXTURE_CONFIG = Path(__file__).parent / "fixtures/config/local.json"
```

with:

```python
FIXTURE_CONFIG = Path(__file__).parent / "fixtures/config/local.json"
# Spawned-child timing. Measured 2026-10-14 on a 14-core host at load average 26, spawn-to-first-line latency
# was median 0.15 s, p90 0.65 s and max 1.03 s, against production windows of 1/3 s to start a request.
# A window a test must sit through is SPAWN_ALLOWANCE_SECONDS long. A wait that returns once a process reaches
# its point uses SPAWN_WAIT_SECONDS, which only bounds a hang. SLOW_SPAWN_SECONDS is a deterministic start delay
# longer than every production window (1/3 s to start, 0.4 s to finish), so a test can exercise a slow spawn.
SPAWN_ALLOWANCE_SECONDS = 3
SPAWN_WAIT_SECONDS = 30
SLOW_SPAWN_SECONDS = 0.5
```

In the same file, replace:

```python
def stale_start_child(transport, cancellation, channel):
```

with:

```python
def slow_spawn_timer_failure_child(transport, cancellation, channel):
    import time
    time.sleep(SLOW_SPAWN_SECONDS)
    timer_failure_child(transport, cancellation, channel)


def slow_spawn_child_exchange(transport, cancellation, channel):
    import time
    import sec_edgar_ingest.download as download
    time.sleep(SLOW_SPAWN_SECONDS)
    download._child_exchange(transport, cancellation, channel)


def stale_start_child(transport, cancellation, channel):
```

In `packages/sec-edgar-ingest/tests/test_download.py`, in `test_timer_installation_failure_and_stale_child_start_send_zero_requests`, replace:

```python
        from support import timer_failure_child, stale_start_child, stale_preparation_child, retain_process_evidence
        for name, target, code in (("timer-installation-failure", timer_failure_child, "hard_timer_unavailable"), ("stale-spawn-start", stale_start_child, "permit_expired"), ("stale-prepared-request", stale_preparation_child, "permit_expired")):
```

with:

```python
        from support import (retain_process_evidence, slow_spawn_timer_failure_child, stale_preparation_child,
                             stale_start_child, timer_failure_child)
        for name, target, code in (("timer-installation-failure", timer_failure_child, "hard_timer_unavailable"),
                                   ("timer-installation-failure-after-slow-spawn", slow_spawn_timer_failure_child,
                                    "hard_timer_unavailable"),
                                   ("stale-spawn-start", stale_start_child, "permit_expired"),
                                   ("stale-prepared-request", stale_preparation_child, "permit_expired")):
```

- [x] **Step 2: Run it to verify it fails**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_download.py' -k test_timer_installation_failure -v
```

Expected: `FAILED`. The case `timer-installation-failure-after-slow-spawn` fails with `AssertionError: 'exchange_deadline' != 'hard_timer_unavailable'`. Its child starts 0.5 s late and is killed at the 0.4 s deadline, before it writes an outcome. The test's sender pins one spool for every case (production uses a fresh temporary directory per send), so the supervisor reads the previous case's leftover `receipt.json` and reports the deadline.

The stale cases after it then fail too, for example `AssertionError: 2 != 1` from `assert_drained`. The failed case never deleted its `transport.jsonl`: this is the cascade the deferred item recorded. On a busy host the first case can also fail: its child, killed before writing any outcome, finds no leftover receipt, and the test errors with `SenderFailure: HTTP child reported an unconfirmed outcome; retain unsafe guard`.

- [x] **Step 3: Give each case its windows and delete leftovers in a `finally`**

In `packages/sec-edgar-ingest/tests/test_download.py`, replace the module's `support` import line:

```python
from support import DownloadHarness, body_receipt, download_harness, fixture_context, fixture_settings, fixture_source, store_bundle, zip_bytes
```

with:

```python
from support import (SPAWN_ALLOWANCE_SECONDS, DownloadHarness, body_receipt, download_harness, fixture_context,
                     fixture_settings, fixture_source, store_bundle, zip_bytes)
```

In `BoundedProcessTests`, replace:

```python
    def send(self, server, *, target=None, cancellation=None, seconds=0.4):
        import multiprocessing
        from support import loopback_sender, real_context, real_permit
        sender = loopback_sender(self.settings, self.clock, server.origin, target=target, spool=self.root/"sender")
        permit = real_permit(self.clock, seconds)
```

with:

```python
    def send(self, server, *, target=None, cancellation=None, seconds=0.4, start_seconds=1/3):
        import multiprocessing
        from support import loopback_sender, real_context, real_permit
        sender = loopback_sender(self.settings, self.clock, server.origin, target=target, spool=self.root/"sender")
        permit = real_permit(self.clock, seconds, start_seconds=start_seconds)
```

In the timer test, replace the loop you edited in Step 1, from its `for` line to the end of the method:

```python
        for name, target, code in (("timer-installation-failure", timer_failure_child, "hard_timer_unavailable"),
                                   ("timer-installation-failure-after-slow-spawn", slow_spawn_timer_failure_child,
                                    "hard_timer_unavailable"),
                                   ("stale-spawn-start", stale_start_child, "permit_expired"),
                                   ("stale-prepared-request", stale_preparation_child, "permit_expired")):
            with self.subTest(name=name):
                server = self.server()
                receipt = self.send(server, target=target)
                self.assertFalse(receipt.complete)
                self.assertEqual(receipt.error.code, code)
                self.assertFalse(server.connected.is_set())
                self.assertEqual(server.requests, [])
                self.assert_drained(receipt)
                retain_process_evidence(name, receipt.temporary_path.parent, server, {"receipt": receipt.to_mapping()})
                (self.root/"sender/transport.jsonl").unlink()
```

with:

```python
        # Every deadline outlasts a slow spawn. The timer cases also get a start window that absorbs one;
        # the stale cases keep the production 1/3 s start window and overrun it on purpose.
        seconds = SPAWN_ALLOWANCE_SECONDS + 1
        cases = (("timer-installation-failure", timer_failure_child, SPAWN_ALLOWANCE_SECONDS, "hard_timer_unavailable"),
                 ("timer-installation-failure-after-slow-spawn", slow_spawn_timer_failure_child, SPAWN_ALLOWANCE_SECONDS,
                  "hard_timer_unavailable"),
                 ("stale-spawn-start", stale_start_child, 1/3, "permit_expired"),
                 ("stale-prepared-request", stale_preparation_child, 1/3, "permit_expired"))
        for name, target, start_seconds, code in cases:
            with self.subTest(name=name):
                try:
                    server = self.server()
                    receipt = self.send(server, target=target, seconds=seconds, start_seconds=start_seconds)
                    self.assertFalse(receipt.complete)
                    self.assertEqual(receipt.error.code, code)
                    self.assertFalse(server.connected.is_set())
                    self.assertEqual(server.requests, [])
                    self.assert_drained(receipt)
                    retain_process_evidence(name, receipt.temporary_path.parent, server, {"receipt": receipt.to_mapping()})
                finally:
                    # The cases share one spool, so a failed case must not leave its outcome or trace to the next.
                    for left in ("transport.jsonl", "receipt.json"):
                        (self.root/"sender"/left).unlink(missing_ok=True)
```

- [x] **Step 4: Run the tests to verify they pass**

Run the Step 2 command. Expected: `Ran 1 test` … `OK`. Then run the whole module:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_download.py' -v
```

Expected: `OK`. Other `BoundedProcessTests` can still fail on a busy host until Task 3.

- [x] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/tests/support.py packages/sec-edgar-ingest/tests/test_download.py
git commit -m "$(cat <<'EOF'
test(download): give the timer test windows a slow spawn fits in

Name the spawn allowances in support, add children that always start 0.5 s
late, and delete each case's trace and receipt in a finally so one failed case
cannot fail the next.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Every bounded-sender test's windows absorb a slow spawn

**Files:**
- Modify: `packages/sec-edgar-ingest/tests/support.py` (`spawn_tolerant_settings` after `fixture_settings`; `LoopbackServer.__init__` and its `headers` mode; `crash_supervisor`)
- Modify: `packages/sec-edgar-ingest/tests/test_download.py`:
  - the import line;
  - `BoundedProcessTests.setUp` and `send()`;
  - a new test;
  - the trickle, delayed-adapter, slow-headers, received-cap, cancellation and supervisor-crash tests.

**Interfaces:**
- Consumes (Task 2): `SPAWN_ALLOWANCE_SECONDS`, `SPAWN_WAIT_SECONDS`, `slow_spawn_child_exchange`; `send(…, start_seconds=…)`.
- Produces (used by Task 5):
  - `support.spawn_tolerant_settings(**overrides: dict) -> Settings`. Its defaults are `sec.requests_per_second = 1 / SPAWN_ALLOWANCE_SECONDS` (a 3 s dispatch window) and `http.exchange_deadline_seconds = SPAWN_ALLOWANCE_SECONDS + 0.5`. Each override is a dict merged into its section.
  - `LoopbackServer(…, drip_seconds=0.02)`: the per-byte pause in `mode="headers"`.

- [x] **Step 1: Write the failing test**

In `packages/sec-edgar-ingest/tests/test_download.py`, in `BoundedProcessTests`, replace:

```python
        self.assertEqual(receipt.sha256, hashlib.sha256(receipt.temporary_path.read_bytes()).hexdigest())
        return events

    def test_real_trickle_is_cancelled_by_total_lifetime_with_partial_socket_evidence(self):
```

with:

```python
        self.assertEqual(receipt.sha256, hashlib.sha256(receipt.temporary_path.read_bytes()).hexdigest())
        return events

    def test_default_windows_absorb_a_slow_spawn(self):
        from sec_edgar_ingest.coordination import Coordinator
        from support import loopback_sender, real_context, slow_spawn_child_exchange
        with self.subTest(path="direct send"):
            server = self.server(b"sent after a slow spawn")
            receipt = self.send(server, target=slow_spawn_child_exchange)
            self.assertTrue(receipt.complete, receipt.to_mapping())
            self.assertEqual(receipt.temporary_path.read_bytes(), server.body)
            self.assert_drained(receipt)
        with self.subTest(path="coordinator exchange"):
            server = self.server(b"exchanged after a slow spawn")
            store, _, leases = store_bundle(self.root/"state", clock=self.clock)
            self.addCleanup(store.close)
            self.addCleanup(leases.close)
            coordinator = Coordinator(self.settings, store, leases, self.clock)
            sender = loopback_sender(self.settings, self.clock, server.origin, target=slow_spawn_child_exchange,
                                     spool=self.root/"coordinated")
            receipt = coordinator.exchange(real_context(self.clock, self.settings), server.url, sender)
            self.assertTrue(receipt.complete, receipt.to_mapping())
            self.assertEqual(receipt.temporary_path.read_bytes(), server.body)
            self.assert_drained(receipt)

    def test_real_trickle_is_cancelled_by_total_lifetime_with_partial_socket_evidence(self):
```

- [x] **Step 2: Run it to verify it fails**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_download.py' -k test_default_windows_absorb_a_slow_spawn -v
```

Expected: `FAILED (errors=2)`. Both subtests raise `sec_edgar_ingest.download.SenderFailure: HTTP child reported an unconfirmed outcome; retain unsafe guard`: the 0.4 s deadline kills each child before it writes its outcome.

- [x] **Step 3: Widen the class's windows**

> Deviation: the `support.py` block that inserts `spawn_tolerant_settings` ends its old text with `def fixture_context(` and a newline, but that line continues in the file; it was applied as a mid-line fragment, giving the same result the block intends.

In `packages/sec-edgar-ingest/tests/support.py`, replace:

```python
    return Settings.from_mapping(value)


def fixture_context(
```

with:

```python
    return Settings.from_mapping(value)


def spawn_tolerant_settings(**overrides: dict) -> "Settings":
    """Fixture settings whose real coordinator windows absorb a slow spawn.

    A permit gives its child 1 / requests_per_second to start and exchange_deadline_seconds to finish.
    """
    sections = {"sec": {"requests_per_second": 1 / SPAWN_ALLOWANCE_SECONDS},
                "http": {"exchange_deadline_seconds": SPAWN_ALLOWANCE_SECONDS + 0.5}}
    for key, value in overrides.items():
        sections[key] = {**sections.get(key, {}), **value}
    return fixture_settings(**sections)


def fixture_context(
```

In `LoopbackServer`, replace:

```python
    def __init__(self, body=b"fixture prefix", *, mode="complete", status=200, headers=None):
```

with:

```python
    def __init__(self, body=b"fixture prefix", *, mode="complete", status=200, headers=None, drip_seconds=0.02):
```

and:

```python
        self.body, self.mode, self.status, self.headers = body, mode, status, dict(headers or {})
```

with:

```python
        self.body, self.mode, self.status, self.headers = body, mode, status, dict(headers or {})
        self.drip_seconds = drip_seconds
```

and, in its `headers` mode:

```python
                        peer.sendall(bytes([byte]))
                        if self.stopped.wait(0.02):
```

with:

```python
                        peer.sendall(bytes([byte]))
                        if self.stopped.wait(self.drip_seconds):
```

In `crash_supervisor`, replace:

```python
    settings = fixture_settings(http={"exchange_deadline_seconds": 0.4}, coordination={"lease_seconds": 2, "renew_every_seconds": 1})
```

with:

```python
    settings = spawn_tolerant_settings(coordination={"lease_seconds": 2, "renew_every_seconds": 1})
```

In `packages/sec-edgar-ingest/tests/test_download.py`, replace the `support` import from Task 2:

```python
from support import (SPAWN_ALLOWANCE_SECONDS, DownloadHarness, body_receipt, download_harness, fixture_context,
                     fixture_settings, fixture_source, store_bundle, zip_bytes)
```

with:

```python
from support import (SPAWN_ALLOWANCE_SECONDS, SPAWN_WAIT_SECONDS, DownloadHarness, body_receipt, download_harness,
                     fixture_context, fixture_settings, fixture_source, spawn_tolerant_settings, store_bundle,
                     zip_bytes)
```

In `BoundedProcessTests.setUp`, replace:

```python
        self.clock = Clock()
        self.settings = fixture_settings(http={"exchange_deadline_seconds": 0.4})
```

with:

```python
        self.clock = Clock()
        # Every child here is a real spawn, so the coordinator's windows must absorb a slow one.
        self.settings = spawn_tolerant_settings()
```

Replace the `send()` signature line:

```python
    def send(self, server, *, target=None, cancellation=None, seconds=0.4, start_seconds=1/3):
```

with:

```python
    def send(self, server, *, target=None, cancellation=None, seconds=SPAWN_ALLOWANCE_SECONDS + 1,
             start_seconds=SPAWN_ALLOWANCE_SECONDS):
```

The tests whose deadline ends the exchange keep their meaning against the new deadline. Make each of these replacements.

In `test_real_trickle_is_cancelled_by_total_lifetime_with_partial_socket_evidence`:

```python
        self.assertLess(elapsed, 1.2)
```

becomes:

```python
        self.assertLess(elapsed, self.settings.http.exchange_deadline_seconds + 0.8)
```

In `test_next_actual_get_waits_for_drain_spacing_after_in_adapter_delay`, delete the line

```python
        self.settings = fixture_settings(http={"exchange_deadline_seconds": 1.0})
```

(the class settings now allow 3.5 s for the 0.55 s adapter delay), and in its spacing assertion replace

```python
            self.assertGreaterEqual(second_get-first_get, 1/3, "actual GET timestamps
```

with

```python
            self.assertGreaterEqual(second_get-first_get, 1/self.settings.sec.requests_per_second, "actual GET timestamps
```

leaving the rest of that line unchanged.

In `test_slow_headers_are_bounded_even_without_inactivity_timeout`, replace:

```python
        server = self.server(mode="headers")
        started = time.monotonic()
        receipt = self.send(server)
        self.assertFalse(receipt.complete)
        self.assertLess(time.monotonic()-started, 1.2)
```

with:

```python
        # The header bytes drip for longer than the exchange deadline, so only the deadline can end the exchange.
        server = self.server(mode="headers", drip_seconds=0.25)
        started = time.monotonic()
        receipt = self.send(server)
        self.assertFalse(receipt.complete)
        self.assertLess(time.monotonic()-started, SPAWN_ALLOWANCE_SECONDS + 1 + 0.8)
```

In `test_received_cap_refuses_extra_byte_before_spool_write`, the two modes share one spool, as the timer test's cases do. In the planning baseline the `complete` mode missed its start window, and `unadvertised` then failed `2 != 1` on the leftover trace. Give it the same `finally`. Replace:

```python
        self.settings = fixture_settings(http={"exchange_deadline_seconds": 0.4, "max_received_bytes": 4})
        for mode in ("complete", "unadvertised"):
            with self.subTest(mode=mode):
                server = self.server(b"12345", mode=mode)
                receipt = self.send(server)
                self.assertFalse(receipt.complete)
                self.assertEqual(receipt.error.code, "received_limit")
                self.assertLessEqual(receipt.byte_count, 4)
                if mode == "unadvertised":
                    self.assertEqual(receipt.temporary_path.read_bytes(), b"1234")
                self.assert_drained(receipt)
                (self.root/"sender/transport.jsonl").unlink()
```

with:

```python
        self.settings = spawn_tolerant_settings(http={"max_received_bytes": 4})
        for mode in ("complete", "unadvertised"):
            with self.subTest(mode=mode):
                try:
                    server = self.server(b"12345", mode=mode)
                    receipt = self.send(server)
                    self.assertFalse(receipt.complete)
                    self.assertEqual(receipt.error.code, "received_limit")
                    self.assertLessEqual(receipt.byte_count, 4)
                    if mode == "unadvertised":
                        self.assertEqual(receipt.temporary_path.read_bytes(), b"1234")
                    self.assert_drained(receipt)
                finally:
                    # The modes share one spool, so a failed mode must not leave its outcome or trace to the next.
                    for left in ("transport.jsonl", "receipt.json"):
                        (self.root/"sender"/left).unlink(missing_ok=True)
```

In `test_cancelled_sender_returns_only_after_child_join_and_socket_close`, `server.prefix_sent.wait(1)` becomes `server.prefix_sent.wait(SPAWN_WAIT_SECONDS)`, and `thread.join(1)` becomes `thread.join(SPAWN_WAIT_SECONDS)`.

In `test_independent_fatal_timer_survives_supervisor_death_during_blocking_headers`:

```python
        self.settings = fixture_settings(http={"exchange_deadline_seconds": 0.4}, coordination={"lease_seconds": 2, "renew_every_seconds": 1})
```

becomes:

```python
        self.settings = spawn_tolerant_settings(coordination={"lease_seconds": 2, "renew_every_seconds": 1})
```

`server.connected.wait(2)` and `server.closed.wait(1)` become `…wait(SPAWN_WAIT_SECONDS)`; keep their messages. Then replace:

```python
            context = replace(real_context(self.clock, self.settings), priority="daily")
```

with:

```python
            # The successor first waits out the dead owner's unsafe interval, so its run deadline is generous.
            context = replace(real_context(self.clock, self.settings), priority="daily",
                              deadline=self.clock.now() + timedelta(seconds=4 * SPAWN_WAIT_SECONDS))
```

`timedelta` and `replace` are already imported at the top of `test_download.py`.

- [x] **Step 4: Run the tests to verify they pass**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_download.py' -k BoundedProcessTests -v
```

Expected: `Ran 14 tests` … `OK`, in about 30–40 s. Then run the whole module (the Task 2 Step 4 command). Expected: `OK`.

- [x] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/tests/support.py packages/sec-edgar-ingest/tests/test_download.py
git commit -m "$(cat <<'EOF'
test(download): size every bounded-sender window for a slow spawn

BoundedProcessTests timed real spawns against production windows (1/3 s to
start, 0.4 s to finish). Use spawn_tolerant_settings and the spawn allowance
throughout, keep the deadline-bound tests meaningful against the later
deadline, and prove both send paths absorb a child that starts 0.5 s late.
The received-cap test's modes share a spool, so clean it in a finally, as the
timer test does.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: The acquisition-process deadline tests absorb a slow spawn

**Files:**
- Modify: `packages/sec-edgar-ingest/tests/test_acquisition_processes.py:104-122` (stale sender), `:123-152` (independent child)

**Interfaces:**
- Consumes (Task 2): `SPAWN_ALLOWANCE_SECONDS`, `SPAWN_WAIT_SECONDS`, `slow_spawn_child_exchange`.
- Produces: nothing new.

- [x] **Step 1: Make the independent child start late**

In `test_independent_child_deadline_records_actual_fatal_exit_and_prefix`, replace:

```python
        from support import LoopbackServer, fixture_settings, loopback_sender, real_context, real_permit
        from sec_edgar_ingest.coordination import Clock
        with tempfile.TemporaryDirectory(prefix='sec-acquisition-deadline-') as temporary:
```

with:

```python
        from support import LoopbackServer, fixture_settings, loopback_sender, real_context, real_permit, slow_spawn_child_exchange
        from sec_edgar_ingest.coordination import Clock
        with tempfile.TemporaryDirectory(prefix='sec-acquisition-deadline-') as temporary:
```

and:

```python
                sender = loopback_sender(settings, clock, server.origin, spool=Path(temporary) / 'sender')
                from unittest.mock import patch
```

with:

```python
                sender = loopback_sender(settings, clock, server.origin, target=slow_spawn_child_exchange,
                                         spool=Path(temporary) / 'sender')
                from unittest.mock import patch
```

- [x] **Step 2: Run it to verify it fails**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_acquisition_processes.py' -k test_independent_child_deadline -v
```

Expected: `FAILED (failures=1)` with `AssertionError: 0 not greater than 0`. The child starts after its 0.4 s deadline, so it records `exchange_deadline` before receiving any bytes. On a busy host the failure can instead read `AssertionError: independent child timer failed while supervisor was stalled`: the late child is still alive when the stalled supervisor's `join(1)` returns.

- [x] **Step 3: Widen both tests' windows**

In the same test, replace:

```python
        from support import LoopbackServer, fixture_settings, loopback_sender, real_context, real_permit, slow_spawn_child_exchange
```

with:

```python
        from support import (SPAWN_ALLOWANCE_SECONDS, SPAWN_WAIT_SECONDS, LoopbackServer, fixture_settings,
                             loopback_sender, real_context, real_permit, slow_spawn_child_exchange)
```

and replace:

```python
                sender = loopback_sender(settings, clock, server.origin, target=slow_spawn_child_exchange,
                                         spool=Path(temporary) / 'sender')
                from unittest.mock import patch
                def stalled_supervisor(process, cancellation, deadline, clock):
                    process.join(1)
                    if process.is_alive():
                        raise AssertionError('independent child timer failed while supervisor was stalled')
                    return True
                with patch('sec_edgar_ingest.download.wait_for_sender', stalled_supervisor):
                    receipt = sender.send(server.url, real_context(clock, settings), real_permit(clock, seconds=0.4), cancellation=multiprocessing.get_context('spawn').Event())
                self.assertFalse(receipt.complete)
                self.assertGreater(receipt.byte_count, 0)
                self.assertTrue(server.closed.wait(1))
```

with:

```python
                # The child always starts late, so every run shows the start window absorbing a slow spawn;
                # the half second after that window leaves time for a trickled prefix before the fatal timer.
                sender = loopback_sender(settings, clock, server.origin, target=slow_spawn_child_exchange,
                                         spool=Path(temporary) / 'sender')
                permit = real_permit(clock, seconds=SPAWN_ALLOWANCE_SECONDS + 0.5, start_seconds=SPAWN_ALLOWANCE_SECONDS)
                from unittest.mock import patch
                def stalled_supervisor(process, cancellation, deadline, clock):
                    # Never terminate the child: only its own fatal timer may end it.
                    process.join(max(0.0, deadline - clock.monotonic()) + SPAWN_WAIT_SECONDS)
                    if process.is_alive():
                        raise AssertionError('independent child timer failed while supervisor was stalled')
                    return True
                with patch('sec_edgar_ingest.download.wait_for_sender', stalled_supervisor):
                    receipt = sender.send(server.url, real_context(clock, settings), permit, cancellation=multiprocessing.get_context('spawn').Event())
                self.assertFalse(receipt.complete)
                self.assertGreater(receipt.byte_count, 0)
                self.assertTrue(server.closed.wait(SPAWN_WAIT_SECONDS))
```

In `test_stale_sender_awakened_after_allowed_start_sends_zero`, replace:

```python
        from support import LoopbackServer, fixture_settings, loopback_sender, real_context, real_permit, stale_start_child
```

with:

```python
        from support import (SPAWN_ALLOWANCE_SECONDS, LoopbackServer, fixture_settings, loopback_sender, real_context,
                             real_permit, stale_start_child)
```

and:

```python
                receipt = sender.send(server.url, real_context(clock, settings), real_permit(clock, seconds=0.4), cancellation=multiprocessing.get_context('spawn').Event())
                self.assertFalse(receipt.complete)
                self.assertEqual(len(server.requests), 0)
```

with:

```python
                # Only the 1/3 s start window is stale; the deadline outlasts a slow spawn.
                permit = real_permit(clock, seconds=SPAWN_ALLOWANCE_SECONDS + 1)
                receipt = sender.send(server.url, real_context(clock, settings), permit, cancellation=multiprocessing.get_context('spawn').Event())
                self.assertFalse(receipt.complete)
                self.assertEqual(len(server.requests), 0)
```

- [x] **Step 4: Run the tests to verify they pass**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_acquisition_processes.py' -k test_independent_child_deadline -k test_stale_sender -v
```

Expected: `Ran 2 tests` … `OK`. The independent-child test takes about 3.5 s, because it sits through its deadline.

- [x] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/tests/test_acquisition_processes.py
git commit -m "$(cat <<'EOF'
test(acquisition): size the child-deadline windows for a slow spawn

The independent-child test now always starts its child 0.5 s late inside a
3 s start window, and its stalled supervisor waits past the deadline instead
of 1 s. The stale-sender test keeps its 1/3 s start window but outlasts a slow
spawn.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: The held-socket takeover proof absorbs a slow spawn

**Files:**
- Modify: `packages/sec-edgar-ingest/tests/support.py`:
  - `_integrated_settings` (`:1532`);
  - `integrated_old_sender` (`:1555`);
  - `integrated_successor` (`:1599`);
  - `integrated_takeover_proof` (`:1635-1670`).

  Line numbers are from BASE; earlier tasks shift them.

**Interfaces:**
- Consumes (Task 2): `SPAWN_ALLOWANCE_SECONDS`, `SPAWN_WAIT_SECONDS`, `slow_spawn_child_exchange`. Consumes (Task 3): `spawn_tolerant_settings`.
- Produces: nothing new. The proof's keys and the assertions in `test_held_socket_parent_death_zero_successor_unsafe_interval_and_daily_next` are unchanged.

- [x] **Step 1: Make the old sender's child start late**

In `integrated_old_sender`, replace:

```python
    sender = loopback_sender(settings, clock, origin, spool=root / 'old-sender')
```

with:

```python
    # The old child always starts late, so every run shows the dispatch window absorbing a slow spawn.
    sender = loopback_sender(settings, clock, origin, target=slow_spawn_child_exchange, spool=root / 'old-sender')
```

- [x] **Step 2: Run it to verify it fails**

Run:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_acquisition_processes.py' -k test_held_socket -v
```

Expected: `FAILED (failures=1)` with `AssertionError: old child did not reach held loopback`. The coordinator's 1/3 s dispatch window expires before the late child starts, so it never connects.

- [x] **Step 3: Widen the proof's windows and waits**

Replace:

```python
def _integrated_settings():
    return fixture_settings(http={'exchange_deadline_seconds': 0.8},
                            coordination={'lease_seconds': 2, 'renew_every_seconds': 1, 'clock_uncertainty_seconds': 0.05})
```

with:

```python
def _integrated_settings():
    # The lease outlasts both successors' spawn and queueing, so they queue inside the unsafe interval.
    return spawn_tolerant_settings(coordination={'lease_seconds': 2 * SPAWN_ALLOWANCE_SECONDS,
                                                 'renew_every_seconds': SPAWN_ALLOWANCE_SECONDS,
                                                 'clock_uncertainty_seconds': 0.05})
```

In `integrated_successor`, replace `deadline=clock.now() + timedelta(seconds=20))` with `deadline=clock.now() + timedelta(seconds=4 * SPAWN_WAIT_SECONDS))`.

In `integrated_takeover_proof`, make these replacements (each line appears once):

| Before | After |
|---|---|
| `if not old.connected.wait(3): raise` | `if not old.connected.wait(SPAWN_WAIT_SECONDS): raise` |
| `if not backfill_ready.wait(2): raise` | `if not backfill_ready.wait(SPAWN_WAIT_SECONDS): raise` |
| `if not daily_ready.wait(2): raise` | `if not daily_ready.wait(SPAWN_WAIT_SECONDS): raise` |
| `if not old.closed.wait(1): raise` | `if not old.closed.wait(SPAWN_WAIT_SECONDS): raise` |
| `if after['monotonic'] - before['monotonic'] < 1 / 3: raise` | `if after['monotonic'] - before['monotonic'] < 1 / _integrated_settings().sec.requests_per_second: raise` |

and replace:

```python
            for process in (daily, backfill):
                process.join(10)
```

with:

```python
            for process in (daily, backfill):
                process.join(4 * SPAWN_WAIT_SECONDS)
```

Leave each `raise AssertionError(...)` message as it is. The pacing check now compares against the configured interval (3 s), which the coordinator guarantees: it charges each permit at the end of its dispatch window.

- [x] **Step 4: Run the test to verify it passes**

Run the Step 2 command. Expected: `Ran 1 test` … `OK`, in about 30 s. Then run the whole module:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_acquisition_processes.py' -v
```

Expected: `Ran 5 tests` … `OK`.

- [x] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/tests/support.py
git commit -m "$(cat <<'EOF'
test(acquisition): size the held-socket takeover proof for a slow spawn

The proof's real coordinator gave each child 1/3 s to start. Run it with
spawn_tolerant_settings and a lease that outlasts the successors' spawn, wait
for processes by SPAWN_WAIT_SECONDS, check pacing against the configured
rate, and start the old child 0.5 s late on every run.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: The runner deadline test names a lost discovery listing

**Files:**
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_runner.py:52-54` (`test_deadline_after_selection_records_undispatched_units_without_child_work`)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: nothing new.

- [x] **Step 1: Reproduce today's message (scratch, not committed)**

Write `/tmp/plan11/runner_stall.py`. It stalls one fixture send by 0.4 s, which is over the fixture transport's 1/3 s window:

```python
"""Run the runner deadline test with one fixture send stalled past its 1/3 s reservation window."""
import sys
import time
import unittest

sys.path.insert(0, "packages/sec-edgar-ingest/tests")
from network_guard import install
install()
import sec_edgar_ingest.download as download

original, stalled = download._FixtureSender.send, []


def stalling_send(self, url, context, permit, *, cancellation):
    if url.endswith("full-index/2026/QTR3/index.json") and not stalled:
        stalled.append(url)
        time.sleep(0.4)
    return original(self, url, context, permit, cancellation=cancellation)


download._FixtureSender.send = stalling_send
suite = unittest.defaultTestLoader.loadTestsFromName(
    "test_workflow_runner.RunnerTests.test_deadline_after_selection_records_undispatched_units_without_child_work")
unittest.TextTestRunner(verbosity=2).run(suite)
```

Run it from the repository root:

```bash
uv run --offline --frozen --package sec-edgar-ingest python /tmp/plan11/runner_stall.py
```

Expected: `FAIL` with `AssertionError: 1 != 2` at `report.counts['pending_sources']`. That is the recorded failure, and the message does not say why. The run takes about 2.5 minutes (154 s in planning), most of it idle. The refused exchange ends its turn without a confirmed outcome, so the next discovery request waits out the old turn's unsafe guard before it may send. That guard is lease end plus exchange deadline plus clock uncertainty, up to 60 + 90 + 2 s with the fixture config (`coordination.reservation_guard`).

- [x] **Step 2: Assert the precondition with its gaps**

In `test_deadline_after_selection_records_undispatched_units_without_child_work`, replace:

```python
                selected = select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
                freeze_selection(context, selected, h.store, h.objects)
                expired = context.deadline + timedelta(seconds=1)
```

with:

```python
                selected = select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
                # Discovery runs in real time: a stall of over 1/3 s before a fixture send loses that listing
                # (deferred by plan 11). Report the gaps here instead of a bare count mismatch further down.
                self.assertEqual(len(selected['members']), 2, selected['gaps'])
                freeze_selection(context, selected, h.store, h.objects)
                expired = context.deadline + timedelta(seconds=1)
```

- [x] **Step 3: Re-run the stall and the test**

Run the Step 1 command again (again about 2.5 minutes). Expected: `FAIL` at the new assertion, `AssertionError: 1 != 2 : [...]`, with the list containing an `ownership_lost` gap whose message includes `fixture transport refuses a cancelled or expired permit`, and a `baseline_source_missing` gap for `2026Q3`.

Then run the test normally:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_runner.py' -v
```

Expected: `OK`.

- [x] **Step 4: Commit**

```bash
git add packages/sec-edgar-ingest/tests/test_workflow_runner.py
git commit -m "$(cat <<'EOF'
test(workflows): name a lost discovery listing in the runner deadline test

A stall of over 1/3 s before a fixture send loses one listing, which surfaced
only as pending_sources 1 != 2. Assert the two discovered members first and
show the discovery gaps.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
)"
```

---

## Plan completion

1. **Verify under load (scratch).** Run the three checks below one at a time, because overlapping loads change what each one measures. If any check fails, investigate before treating the plan as done. Is a spawn slower than `SPAWN_ALLOWANCE_SECONDS` (read the child traces in the failure output), or is it another cause?

   **a. The fixed tests beside one burner per core.** Write `/tmp/plan11/stress.sh`:

   ```bash
   #!/bin/zsh
   # usage: stress.sh <rounds> <burners> <test-id>... - each test alone, <rounds> times, beside <burners> CPU burners
   cd "$(git rev-parse --show-toplevel)"
   rounds=$1; burners=$2; shift 2
   pids=()
   for i in $(seq $burners); do python3 -c 'while True: pass' & pids+=($!); done
   trap 'kill $pids 2>/dev/null' EXIT INT TERM
   for test in "$@"; do
     failed=0
     for round in $(seq $rounds); do
       if ! output=$(uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py "$test" 2>&1); then
         failed=$((failed+1)); print -r -- "=== FAIL $test round $round"; print -r -- "$output" | tail -25
       fi
     done
     print -r -- "### $test: $failed/$rounds failed beside $burners burners"
   done
   ```

   Run it beside as many burners as the host has cores:

   ```bash
   chmod +x /tmp/plan11/stress.sh && /tmp/plan11/stress.sh 5 "$(sysctl -n hw.ncpu)" test_download.BoundedProcessTests test_acquisition_processes test_coordination.CoordinationTests.test_three_independent_exchange_processes_prove_intervals_priority_and_epochs > /tmp/plan11/stress.log 2>&1; grep '###' /tmp/plan11/stress.log
   ```

   Expected: every line reads `0/5 failed`. Before this plan, the timer, independent-child and held-socket tests each failed 12 of 12 at this load.

   > Deviation: the first run, on HEAD `b25085f7`, failed 3 of 5 `BoundedProcessTests` rounds (the other two groups passed 5 of 5). It was diagnosed rather than rerun until green. Established: the failures are late child starts (every spawned test child runs `network_guard.install()`, which imports `azure.identity` and `msal`: 0.22 s idle, 2.0-2.5 s under a process-creation-heavy competing load), with no parent stalls; 14 CPU burners alone did not reproduce it (18 of 18 rounds passed in the diagnosis). Inferred, not established: that run coincided with such competing load. One failure shape, a leftover `server.closed.wait(1)`, was fixed in `78007ce2` (six sites, now `SPAWN_WAIT_SECONDS`). The rerun on `78007ce2` passed 15 of 15 at an ambient load peaking at 75. The guard import is recorded as a deferred item with the owner's decision.

   **b. The WAL race.** Re-run Task 1 Step 5. Expected: `inits=6000 failures=0`.

   **c. The full suite beside 6 burners**, the planning baseline's load. Write `/tmp/plan11/suite_under_load.sh`:

   ```bash
   #!/bin/zsh
   # usage: suite_under_load.sh <burners> <log> - one full offline suite run beside CPU burners
   cd "$(git rev-parse --show-toplevel)"
   pids=()
   for i in $(seq $1); do python3 -c 'while True: pass' & pids+=($!); done
   trap 'kill $pids 2>/dev/null' EXIT INT TERM
   started=$SECONDS
   uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' > $2 2>&1
   echo "exit=$? elapsed=$((SECONDS-started))s" >> $2
   ```

   Run:

   ```bash
   chmod +x /tmp/plan11/suite_under_load.sh && /tmp/plan11/suite_under_load.sh 6 /tmp/plan11/suite-load6.log; grep -E '^(FAIL|ERROR):|^Ran |^OK|^FAILED|^exit=' /tmp/plan11/suite-load6.log
   ```

   Expected: `Ran 839 tests`, `OK` and `exit=0`. At this load BASE ran 836 tests in 2,159 s and failed five; planning's run of the plan took 1,984 s (Evidence).

   > Deviation: 840 tests ran, because the final-review fix added one test. Result: `OK`, `exit=0`, 2,106 s.
2. **Final review.** Run the final whole-branch review (subagent-driven-development's closing `code-reviewer`) over `6400dba9..HEAD`. For the Codex second-opinion seat, use `-c model=gpt-6-astra`, because the default model is rejected for the ChatGPT account:

   ```bash
   mkdir -p /tmp/codex-review && codex exec review -c sandbox_mode=read-only -c model=gpt-6-astra --base 6400dba9 -o /tmp/codex-review/plan11.md
   ```

   Resolve or consciously defer its findings. Engage with them critically: fix the underlying issue, and push back where warranted.

   > Deviation: the final review ran before step 1, because it is the only step that can change code and the load runs are long. Both seats reviewed `6400dba9..69220339`. They agreed on one Important finding: after Task 3 widened the dispatch window to 3 s, `test_next_actual_get_waits_for_drain_spacing_after_in_adapter_delay` could no longer fail, because reservation pacing alone satisfies it. Codex also found that the WAL waits-out test sampled its start time after arming its release timer. Both were fixed in `b25085f7` (a deterministic logical-clock test whose failure under a deleted drain update was shown on a scratch copy; the timestamp moved before the timer; the delayed-adapter run deadline widened; a misleading 0.4 s setting removed), and a scoped re-review passed. Codex's alternative of lengthening the adapter delay was rejected because it would depend on spawn speed again. `b25085f7` and `78007ce2` were not covered by a second Codex pass.
3. **Several consecutive full-suite runs (the item's Done-when).** Run `scripts/check-sec-edgar-ingest.sh` from the repository root three times in a row, with no code change between runs. Each run is the full offline suite, wheel and sdist build, CLI help, compileall, whitespace check, pipeline render and pinned Bicep compile, about 20–30 minutes. Each must exit 0. On the first run, also confirm the suite prints nothing to stdout:

   ```bash
   for run in 1 2 3; do scripts/check-sec-edgar-ingest.sh > /tmp/plan11/check-$run.log 2>&1; echo "run $run exit $?"; done
   uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' > /tmp/plan11/suite.stdout 2> /tmp/plan11/suite.stderr; tail -n 3 /tmp/plan11/suite.stderr; wc -c < /tmp/plan11/suite.stdout
   ```

   Expected: `run 1 exit 0`, `run 2 exit 0`, `run 3 exit 0`; then `OK` and `0`. If any run fails, find the cause before re-running. A failure is not cleared by a passing rerun.

   > Deviation: none in the runs. Three consecutive runs exited 0 (1,885 s, 1,903 s, 1,872 s), each `Ran 840 tests`, `OK`, on `78007ce2` with no change between them; the stdout check printed 0 bytes. They ran on a quiet machine (load about 3-8, swap falling from 20 GB to 6 GB), so they show repeatability, not behaviour under the heavy competing load that failed the first step 1a run.
4. **Run writing-plans' Plan Completion Protocol.**
   - In its deferred-items step, tick the item "Load-flaky multi-process tests" (section `6-sec-filing-index-ingestion-stage-5-spec — 2026-10-11`) as `- [x]`, and append `→ done in plan 11 (WAL switch retries until the busy timeout; spawn-timed tests sized by support.SPAWN_ALLOWANCE_SECONDS; three consecutive check runs passed)`.
   - Append a `## 11-load-flaky-multi-process-tests — <date>` section with at least these two items, plus anything the reviews leave deferred:
     - [ ] Fixture reservation-to-send stall (plan 11, Task 6). Every fixture workflow test runs discovery and collection through `_FixtureSender.send` (`download.py:744`). It refuses a permit once 1/3 s (`1 / requests_per_second`) has passed since `Turn.reserve`, so any process stall over 1/3 s loses that request. Seen once in `test_workflow_runner` as `pending_sources 1 != 2`; reproduced by injecting a 0.4 s stall; not reproduced by CPU or fsync load. A lost request also leaves the coordinator's unsafe guard in place, so that test's next request waits up to about 150 s (`coordination.reservation_guard` with the fixture config). There are two options:
       - (a) give the fixture workflow settings a lower `sec.requests_per_second`, which slows every fixture discovery about 9-fold at 1/3 request per second;
       - (b) add a fixture-only grace setting, which is a production config change.

       Size: design. Done when: the owner chooses (a), (b) or accepting the rare stall, and the choice lands or is recorded here.
     - [ ] Production spawn latency against the 1/3 s dispatch window (plan 11 Evidence). Each `BoundedSender` request spawns a child that must start within `1 / requests_per_second`. Planning measured spawn latency at load average 26 on 14 cores: median 0.15 s, p90 0.65 s, max 1.03 s. A slow spawn ends in `permit_expired`, which `RequestClient._outcome` treats as non-retryable, so the source waits for the next run. Size: design. Revisit if: Stage 7's live smoke or integrated checks record `permit_expired` from a late child start, or measure worker spawn latency near 1/3 s.
   > Deviation: the section carries four items beyond the two listed above: the test-guard eager Azure import (with the owner's decision on its posture), the supervisor-crash test's duration cliff, the remaining short bounds in the spawn-timed tests, and drain-spacing test hardening. Cosmetic review Minors with no closure condition were dropped, not deferred.
5. **Hand back.** Stop and hand integration (merge, PR or cleanup) back to the owner. Do not merge, push or deploy without that decision. With the item ticked, roadmap Stage 7's Consumes is met. Resuming the roadmap ("resume the roadmap") is the owner's call.
