# Whole-branch recovery fixes I1/I2

Scope: approved Plan 3 recovery findings at BASE `3c868351ea8c417d2a5edf88c6091ef0b72d519a`. Documentation/configuration work was separately committed by its owner as `d3c46768321de9a973f1b82258f1e224506848e5`. This worker changed only:

- `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`
- `packages/sec-edgar-ingest/tests/test_etl_cli.py`

No state/storage helper change was needed. Evidence is retained beside this report, not staged with the four code/test files. Primary checkout, retained-source policy, pins, parser/schema/result fields, batch size and CAS bound were not changed. All SEC/Azure/authentication/compute/deployment/image/fetch authorizations stayed closed.

## Diagnosis and behavior

I1: `_affected_quarters` previously selected old quarters through Processing and PublicationReceipt records. The actual hard-crash regressions commit Q3 at `publication.after_pointer`, before any receipt exists, then publish a newer snapshot of the same source with filing dates moved to Q4 without resuming the old command. Before the fix both daily and quarterly cases reported Q4 only. Discovery now scans QuarterPublication captures, validates the exact manifest and complete candidate through the existing validator, verifies the pointer fingerprint, and selects committed quarters whose manifest source IDs intersect the incoming source IDs. No recoverable index is a selection authority. Empty worksets retain their unchanged/zero-quarter behavior.

The daily regression now returns Q3 and Q4 published: Q3 retains its existing key, has zero withdrawals and one unresolved absence, and records the revised source. The quarterly regression now explicitly returns Q3 invalid_source and Q4 published; the Q3 pointer stays unchanged because the revised own-quarter membership is empty. No withdrawal rule or source tolerance changed. Additional tests corrupt the prior manifest, prior data, or pointer fingerprint; each refuses before advancing Q4.

I2: `publish_quarter` used to propagate an ordinary receipt/membership error after CAS without its committed result. `run_publish` converted it to a failed quarter with no generation, and CLI froze a terminal result that exact replay could not repair. The new `PublicationRepairError(RuntimeError)` carries the truthful committed `PublicationResult` in `.result`, the original ordinary exception in `.error`, and preserves it as `__cause__`. It covers unchanged-capture repair and all ordinary exceptions after successful CAS, including the named after_pointer/after_repair observers. BaseException crash behavior stays intact; the existing direct API RuntimeError catch regression passes.

`run_publish` recognizes this error, retains its published/unchanged capture, continues other quarters, and finally raises `PublicationRepairPending(RuntimeError)` if ancillary work is incomplete. Its `.details` contains:

- `quarters`: every attempted quarter's complete PublicationResult mapping, including truthful committed generation/manifest refs, gates, and failures;
- `gaps`: ordinary failed-quarter Error mappings;
- `repair_errors`: dictionaries containing `quarter`, original exception `type`, and original exception `message`.

CLI retains this as a retryable structured Attempt error with `details.type=PublicationRepairPending` plus those fields. It uses the existing failure stdout shape, with outcome `internal_error`, exit 9, `result_ref=null`, and null source/snapshot workset refs; it writes no terminal ETL result object and leaves Attempt.result null. The Attempt may record an operational error outcome/end timestamp through the existing retention mechanism, but the existing exact-intent/no-result path resumes it with its original context. Retry repairs both quarters and returns unchanged without another pointer advance. A completed retry result still replays byte-for-byte.

## Proposed interfaces.md refinement (controller-owned file)

All public function signatures and immutable record/result schemas remain unchanged. Add this clarification to the Task 6 / publication recovery notes:

> Affected quarters are the union of incoming quarter_counts and matching source IDs discovered from fully validated current QuarterPublication/manifest captures; recoverable receipts are not authoritative for discovery. `publish_quarter` can raise `PublicationRepairError(RuntimeError)` after a successful CAS or unchanged-capture repair failure, retaining the committed PublicationResult as `.result` and the original exception as `.error`/`__cause__`. `run_publish` continues independent quarters, then raises `PublicationRepairPending(RuntimeError)` with `.details = {quarters, gaps, repair_errors}` rather than returning a misleading terminal failure result. CLI retains this progress in a retryable Attempt error, exits 9 with no result_ref, and leaves Attempt.result null so an exact retry can repair indexes without advancing an unchanged pointer.

This refines Task 6's receipt-based wording to honor the already approved pointer publication boundary and repairable-index contract; it does not extend source acceptance or public result fields. Direct callers that previously caught a specific OSError/Conflict from post-commit ancillary work now receive a RuntimeError subclass with the original error available; generic RuntimeError handling remains compatible. Before-commit exceptions are unchanged.

## Red/green and verification

Every package-import/test child used `uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py ... -v`. The guard installs before test imports. Only cached dependencies were used. `run.py` is a stdlib-only parent logger; each numbered directory retains exact argv/cwd/environment, wall timing, exit code, raw stdout/stderr, fixture state, actual command outputs and an SHA256/length inventory.

| Evidence | Result | Test runtime | Parent wall time |
|---|---|---:|---:|
| 01-red | Five intended failures: two missing Q3 outcomes; three frozen result_ref failures after actual commits | 0.922 s | 1.159 s |
| 02-green | Same five regressions pass | 1.641 s | 1.829 s |
| 03-neighbors | Three corrupt-authority and two post-commit observer exception cases pass | 1.078 s | 1.273 s |
| 04-covering | `test_etl_cli test_etl_publication test_etl_catalog`: 93 pass, exit 0 | 46.170 s | 46.370 s |

All stdout and stderr were inspected in full. The covering run's stdout contains the expected mocked SDK proof line; unittest stderr contains 93 successful test records and OK, with no warnings, errors or skips. `whitespace.json` retains the owned-path `git diff --check` exit 0 with empty stdout/stderr. `owned.diff` preserves the reviewed code/test diff. `audit.json` verifies all numbered-run inventory payloads and reads the actual CLI checkpoints independently of unittest assertions:

- 01-red: 132 records / 1,078,061 bytes;
- 02-green: 140 records / 1,324,723 bytes;
- 03-neighbors: 126 records / 1,125,374 bytes;
- 04-covering: 802 records / 5,831,579 bytes.

The audit confirms both I1 interrupted old commands had Q3 committed with zero receipts, and the revised outputs contain both quarters. For each of five I2 variants, the pre-retry Attempt has no result and no immutable result object, carries two truthful quarter captures in a retryable error, and both pointer values/versions are exactly equal before/after retry. Two receipts exist afterward. Tests also assert Processing.published, frozen context equality, and immutable completed replay equality.

Clean-code application: N1/N4 names explicitly distinguish committed repair failures from pre-commit failures; C3 preserves the reason receipt absence cannot drive discovery; G30 keeps discovery and publication/repair boundaries cohesive; T5/T6 cover the crash window, ordinary exceptions, unchanged captures and corrupt authority. No adjacent cleanup or unrelated production change was performed.

## Limits and handoff

Scanning fully validated current captures increases discovery I/O with the number and size of committed quarters. This is the conservative minimal correctness fix without introducing an authoritative secondary index; no production capacity claim is made. A malformed capture encountered during discovery fails the invocation before publication because its source membership cannot be safely inferred. The scan is not a global multi-quarter transaction; existing per-quarter CAS/rebuild semantics remain the concurrency boundary.

Focused checks are complete. Combined full suite, current wheel, sequence/installed proofs and documented sample run are assigned separately by the controller. No broad full check, specimen rescan, acceptance stamp, roadmap tick, integration or cleanup was run. Plan completion remains blocked independently by the 51 retained-source conflicts. No policy reconciliation was attempted.

Commit readiness: four explicitly owned files verified; controller authorized a scoped commit after the separate documentation commit. Commit identity is retained in `commit.json` after execution.
