## Per-finding assessment

**Important — clean up every owned child before raising on timeout: ADDRESSED.**

[etl_proof.py:129](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:129) now accumulates failures, visits every supplied child, applies bounded terminate/join and kill/join steps, checks whether the child remains alive, and raises after cleanup. [etl_proof.py:179](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:179) cleans up already-started children on partial startup failure while preserving the original exception.

The regressions use real spawned children:

- [test_etl_processes.py:75](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/test_etl_processes.py:75) proves sibling cleanup and kill fallback when the first child ignores SIGTERM.
- [test_etl_processes.py:103](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/test_etl_processes.py:103) proves cleanup after the second process fails to start.

The full-check `timeouts/` receipts record PIDs **27520/27521 already dead with exits −9/−15 before emergency cleanup**, and partial-start PID **27528 dead with exit −15**, with the second process unstarted.

**Minor — retain subprocess output when a command times out: ADDRESSED.**

[etl_proof.py:443](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/etl_proof.py:443) catches `TimeoutExpired`, writes command/environment/timing metadata with `outcome: timeout` and `exit: null`, preserves partial streams, and reraises. Byte outputs receive separate lossless files and SHA records; display decoding does not replace the retained originals. The default timeout remains **300 seconds**.

[test_etl_processes.py:144](/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests/test_etl_processes.py:144) exercises a real timeout with invalid UTF-8 on both streams. I checked the retained **23-byte** stdout/stderr files against their recorded hashes; both match exactly.

## Evidence and regressions

Reviewed the relevant changed code/document hunks once from the supplied **11,599,056-byte** package `review-4b6e54c1..3c868351.diff`, covering:

- **BASE:** `4b6e54c18b886e02ff75643d6f5b399e0ededf3b`
- **HEAD:** `3c868351ea8c417d2a5edf88c6091ef0b72d519a`
- **Commit:** `3c868351`

Inspected retained evidence confirms:

- Corrected red: **six tests, three expected failures**, exit **1**.
- Green: **six tests in 5.644s**, exit **0**.
- Full check: **442 tests in 160.172s**, exit **0**, with successful builds and help/version checks.
- Refreshed sequence and isolated installed proofs: exit **0**.
- Root inventory: **7,525 records**; repair inventory: **77 records**. Both have exact coverage, safe relative paths and matching byte/hash records.
- Historical whitespace exit **2** and scoped implementation/prose exit **0** remain explicitly distinguished.

**New Critical findings:** None.
**New Important findings:** None.
**New Minor findings:** None.

## Cannot Verify

This was a read-only, offline re-review of the two findings and regressions introduced by their fixes. No suites were rerun, and unchanged Task 7 implementation was not re-reviewed. Retained native evidence establishes no Linux worker capacity or live Azure behavior; all 22 integrated checks remain reserved.

## Assessment

**Approved for this scoped Task 7 repair.** Both prior findings are addressed with concrete implementation changes and meaningful red/green evidence.

**Stage 3 acceptance remains blocked independently** by the unchanged 51 retained-source conflicts. This approval does not authorize a completion stamp, retirement, integration or cleanup.
