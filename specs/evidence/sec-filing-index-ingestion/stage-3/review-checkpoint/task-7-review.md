## Spec Compliance

**Issues found: the finite child-cleanup requirement is incomplete.** The remaining Task 7 delivery is supported by the supplied diff and retained evidence.

Reviewed the exact **44,727,064-byte** package `.sdd/3-sec-filing-index-ingestion-stage-3-spec/review-63c32739..4b6e54c1.diff`, covering:

- **BASE:** `63c327390f76d466e04fb8285f7c95f39e4f4937`
- **HEAD:** `4b6e54c18b886e02ff75643d6f5b399e0ededf3b`
- **Commits:** `d3d58590` and `4b6e54c1`

Fulfilled requirements:

- Real spawn races use independent stores, a first-CAS-only barrier, actual `commit_pointer` calls, recorded conflict exceptions, and final source/key union assertions. Retained insert/replace traces show `AlreadyExists`/`Conflict`, new bases, and successful rebuilds. The gate loser rebuilds to `awaiting_approval`. See [etl_proof.py:84](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:84).
- Actual `os._exit(73)` children cover all four requested boundaries. Reopened captures, unchanged frozen envelopes, exact CLI resumption, and post-CAS pointer stability are verified. See [etl_proof.py:185](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:185).
- Complete specimen scans use the production parser and duplicate-policy helpers. I compared all ten current receipts with the independent preflight: hashes, lengths, 970,622 rows, bounds, selected parsed rows, quarter counts, distinct counts and duplicate outcomes agree. See [etl_proof.py:274](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:274).
- Raw-only command execution covers replay, no-op, parser-v2, cross-quarter output and gates, with acquisition constructors prohibited. Installed proof uses frozen hash-bearing requirements, offline installation, external cwd, removed `PYTHONPATH`, guarded imports and verified site-packages bytes. See [etl_proof.py:343](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:343) and [etl_proof.py:426](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:426).
- Documentation covers exact references, capture/read, origin versus transform context, gates, repair and native-only limits. No production module or dependency pin changes appear in this task.

**Known blocked acceptance gate:** SEC-0141/0142/0143 retain 21/24/6 conflicts. Specimens correctly exit **1**. Stage 3 remains blocked pending owner policy reconciliation; no completion, roadmap tick, retirement, integration or cleanup is justified. [verification.md:3](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-3/verification.md:3) states this accurately.

**Disclosed deviations:** The committed historical evidence whitespace check exits **2** across 14 archived files; the owned implementation/docs check exits **0**. Exact historical bytes remain preserved. Early red/green wrapper duration is explicitly unavailable. These are documented limitations, not concealed successes or new production defects.

## Code Quality Strengths

The driver delegates ETL behavior to actual production APIs rather than duplicating the algorithm. Its race instrumentation observes real CAS results, and its exclusive output directories preserve failed attempts. The installed runner has the necessary spawn guard. Successful final logs contain no warnings or unexpected tracebacks.

Evidence inspected includes:

- `verification/final-check/{command.json,stdout.txt,stderr.txt}`: exit **0**, **439 tests in 160.832s**, wheel/sdist build, help/version and compile checks.
- `verification/sequence/processes/`, `verification/final-check/processes/`, and `verification/installed/installed-sequence/processes/`: independent PID sets, actual CAS transitions, death markers and retained logs.
- Final install command records, `installed/report.json`, and `installed/installed-sequence/report.json`: isolated installed proof exit **0**, exact pins and 28-source equality.
- `artifact-inspection.json`, `readme-wheel-build/`, and `runbook-proof.json`: final wheel/README equality, successful metadata rebuild and saved-capture repair proof.
- Primary approval/reconciliation/version copies: byte equality with primary confirmed.
- Root SHA inventory: **6,634 records**, exact file coverage, safe relative paths, matching lengths/hashes. Major nested inventories also matched, including **5,503** archived history files.

## Findings

**Critical:** None.

**Important — clean up every owned child before raising on timeout.**
[etl_proof.py:128](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:128)

`join_children` raises immediately after the first timed-out child is terminated. Subsequent children never receive a join or termination attempt. Because these are non-daemon processes, a still-hung sibling can keep interpreter shutdown waiting indefinitely, defeating the explicit finite-run requirement. The terminated child is also not checked again after its ten-second join.

Collect timeout failures while cleaning up **all** supplied children, verify termination, use a bounded kill fallback where necessary, and raise only after cleanup. Cover the case where the first child times out while another remains alive; also ensure a partially started race cleans up already-started children.

**Minor — retain subprocess output when a command times out.**
[etl_proof.py:416](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:416)

`subprocess.run(..., timeout=300)` can raise before the command record is saved. The top-level failure report then preserves a traceback but loses that subprocess's captured stdout/stderr and per-command timing record. Catch `TimeoutExpired`, retain its partial outputs with an explicit timeout outcome and unavailable exit status, then propagate failure. Current successful evidence is unaffected.

## Cannot Verify

No suites or live operations were rerun. This review does not establish Linux amd64/Python 3.14.8 capacity, ADLS/HNS, identity or actual Azure concurrency; all 22 integrated checks remain **reserved**. Unchanged production internals and prior tasks' full correctness remain outside this task-scoped review. No unchanged production source inspection was needed.

## Assessment

**Task delivery: Needs fixes** for the owned-child timeout cleanup defect. The retained successful capability evidence is credible and the remaining implementation is well supported.

**Stage 3 acceptance: Blocked independently** by the retained-source policy conflicts, regardless of the harness fix.
