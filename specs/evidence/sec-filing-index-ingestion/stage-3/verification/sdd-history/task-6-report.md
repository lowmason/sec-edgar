# Task 6 implementation report

Task 6 implements storage-only transform/publish CLI commands, strict ETL results, immutable command intent, per-quarter aggregation, and exact replay/repair. The final required covering run passed **57 tests in 66.703 seconds, exit 0**, after the final source/test changes. The full suite, wheel/build, process-kill proof, all-22 historical-source reconciliation, and Linux capacity measurements remain Task 7/controller work.

## Scope and actual APIs

Worktree: `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`, branch `codex/sec-edgar-stage-3`, base `1ec404a29f945448c735efe712526edc41efaacc`. Only seven assigned source/test files were changed:

- `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py` (new)
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py`
- `packages/sec-edgar-ingest/tests/test_etl_cli.py` (new)
- `packages/sec-edgar-ingest/tests/test_workspace.py`
- `packages/sec-edgar-ingest/tests/test_cli.py`

Read the brief, interfaces, consumed config/models/state/results/CLI, parser/contracts/transform/publication/ETL state, storage opening, helper contracts, existing CLI/workspace tests, mandatory network guard and Task 5 report before implementation. Used clean-code, clean-coder, test-driven-development and verification-before-completion. No subagents/reviewers were spawned; no primary checkout, dependency pins, old-package absences, roadmap, previous evidence or Task 4/5 source was modified.

Actual new public signatures in `etl/commands.py`:

```python
run_transform(snapshot_ref: str, context: RunContext, settings: Settings,
              objects: ObjectStore, store: StateStore, *, force: bool = False,
              observer: BoundaryObserver | None = None) -> EtlResult
run_publish(transformed_workset_ref: str, context: RunContext, settings: Settings,
            objects: ObjectStore, store: StateStore, *,
            observer: BoundaryObserver | None = None) -> EtlResult
write_etl_result(result: EtlResult, objects: ObjectStore,
                 acquisition: AcquisitionState, *,
                 observer: BoundaryObserver | None = None) -> str
read_etl_result(path: str, objects: ObjectStore) -> EtlResult
validate_workset_ref(path: str, kind: str) -> None
```

`AcquisitionState.finish_attempt` accepts the annotated `CommandResult | EtlResult` while preserving its exact context/result CAS behavior. `result_path` permits the four shared commands. `read_result`, `write_result`, `CommandResult` and acquisition result bytes are unchanged. Added exit mappings are unchanged=0, publication_conflict=9 and awaiting_approval=10; prior mappings remain unchanged.

Three explicit interface refinements:

1. Task 1's actual `EtlResult` inherits `Record` and has no `to_json`. The separate codec therefore uses `canonical_json(result.to_mapping())` and strict `EtlResult.from_mapping(parse_json(body))`; it does not add methods/defaults to acquisition or Task 1 contracts.
2. `write_etl_result` adds optional keyword-only `observer`, retaining all existing three-argument calls. This supports `etl_result.after_object` and `etl_result.after_attempt` through the actual writer. The controller explicitly accepted this backward-compatible refinement.
3. ETL `command.json` is a canonical envelope `{"context": <full exact RunContext mapping>, "intent": {"command", "today", "workset", "force"}}`. `force` is null for publish and Boolean for transform. Freezing the context is necessary because Attempt keys include image/execution, while command paths omit them. A crash before intent creation uses existing Attempt rows claiming the same run/command/attempt path; conflicting provenance is refused before creating another Attempt. Acquisition intent bytes retain their old shape.

## Behavior and matrix

Both commands require config/run/execution/attempt/deadline/workset. Transform alone accepts force. ETL accepts fixture state/date controls, refuses fixture-pack, validates parser/schema/settings/path/IDs/time syntax before opening stores, and branches before Coordinator/BoundedSender/RequestClient construction. Tests patch those actual acquisition constructors to raise and install the offline provider/network guard before imports. Empty publish also validates its producing parser/schema against the current context.

Transform uses retained immutable snapshot/source membership and actual `transform_workset`, keeping origin context distinct from current execution. Source-success and failure logs include correlation/source/raw hash/workset/observation references. New parser replay retains the old acquisition origin. Force rebuild reuses verified logical output and causes no second publication advance. Partial transforms retain successful observations and quarantine error line/reason; all-invalid is exit 7, partial is 3. Partial publication refuses before invoking any quarter publisher. Complete empty input is unchanged with zero advances.

Publication uses only the real `publish_quarter`, current state/receipt APIs and existing candidate validation. Affected quarters are incoming quarter counts union prior source-quarter PublicationReceipt memberships. A changed filing date visits both old and new quarters. Gates and failing quarters do not stop unrelated quarters. Harder errors dominate gates in aggregate, but every gate remains in quarters and counters. A gated two-quarter source has only the receipt-backed successful quarter and remains not fully published. There is no cross-quarter transaction or alternate commit/catalog algorithm.

Conflict result manifest references retain **attempted uncommitted evidence**, as approved in Task 5. Their generation/candidate are null. `Error.details` stores `quarter`, `conflicts`, `attempted_manifest_ref`; strict decoding distinguishes these from published/unchanged committed captures and gate-only candidate references. The codec rejects malformed format, missing/extra/duplicate fields, noncanonical JSON, unsafe correlation, forged effective config/hash/pin, wrong workset refs, unsupported outcomes, inconsistent counters, absent/orphan/duplicate error associations and retry counts beyond CAS_ATTEMPTS.

Frozen completed attempts replay after expiry and repair the exact Attempt from the result object. New expired attempts refuse. Begun intent resumes its original start/pin/config/image/versions/input/force/deadline. Changed image/execution/config/parser/workset/force/deadline reuse refuses. Result object is written before Attempt; after-object and after-attempt crashes preserve result bytes exactly. Pointer crash replay repairs memberships with no second pointer version advance. Persisted result replay uses the same CLI path rather than a test-specific recovery implementation.

## Red/green evidence

Evidence root: `.sdd/3-sec-filing-index-ingestion-stage-3-spec/task6-evidence/`. Each runner JSON retains full argv, cwd, relevant environment, stdout, stderr and exit. `run.py` installs `tests/network_guard.py` before imports and starts a child guarded runner using `uv run --offline --frozen`. Every test subprocess uses the existing guard; workspace console/module checks now bootstrap the guard before running the actual installed entry points.

- `red-boundary.json`: three tests; two expected failures, help omits transform/publish and argparse rejects transform.
- `red-replay-codec.json`: missing command/replay/result APIs captured separately.
- `intermediate-boundary.json`: initial core passes except a test's changed deadline exceeded the independent 3600-second allowance; changed that test to a different deadline within the allowance so it isolates frozen-identity refusal.
- `intermediate-matrix.json`: 17 ETL tests passed.
- `red-strict-intent.json`: reproduced changed-image begun-intent acceptance, missing conflict gap/excess retry acceptance, and empty publish parser mismatch.
- `green-strict-intent.json`: 21 ETL tests passed after fixes.
- `green-covering-initial.json`: 52 tests passed (21 ETL plus existing CLI/workspace regression tests).
- `green-extra-replay.json`: 24 ETL tests passed, adding force/no-advance, input path identity and exact result-write preconditions.
- `red-context-codec.json`: forged hash/config/pin/execution and orphan error accepted, missing source-failure log, all demonstrated as failing assertions.
- `green-final-covering.json`: 57 tests passed after the final production code changes.
- `green-recovery-evidence.json`: 26 ETL tests passed after adding retained crash checkpoint bytes and interrupted CLI traces.
- **`green-final-retained.json`: 57 tests passed, 66.703 seconds, exit 0**, after all source/test changes. No test failures or warning diagnostics.

Final command:

```sh
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_cli test_workspace test_cli -v
```

Cwd is the managed worktree above. `SEC_EDGAR_TASK6_PROOF_DIR` is the absolute `task6-evidence/green-final-retained-proof` path, `PYTHONDONTWRITEBYTECODE=1`; full process environment selection is retained in `green-final-retained.json`. All 26 ETL test roots have calls/config/object/store/canonical state records plus byte-hash ledgers. Crash tests retain named `files/checkpoints/*.json` containing exact pre/post state and immutable JSON body hex/hashes. `actual-summary.json` consolidates selected artifact identities, full results, counters and recovery checks; SHA-256 `d37cd6b6f8e0056cf601dd5f122cca7f11b3e664d9c336e1f554e2b174b83a86`.

## Actual immutable artifacts and recovery

In `green-final-retained-proof/test_real_transform_and_publish_without_acquisition_construction/files/.fixture-state/objects`:

- `runs/sec/etl-cli/transform/transform/command.json`: 2148 bytes, SHA `926a6f24d0055047ea37dc79b615bca918836db009b0883de0b5e37e9327d49b`.
- Matching transform `result.json`: 2496 bytes, SHA `0682aee7e1a38dd89b1b7f4c43d07709caace8453005ee36416b300662dae1dc`; transformed=1, all other counters=0, success.
- `runs/sec/etl-cli/publish/publish/command.json`: 2144 bytes, SHA `64bd1922ab1d37b9b45db9350e35bf6acf6b5f7b5d2c0fecfffa7e9dd1fec91b`.
- Matching publish `result.json`: 2807 bytes, SHA `42dc4d678f609cc3f34fc96e1d5a05fcbbe8fbdaad57b27ba76bc960a92a7516`; published=1, all other counters=0, success.
- Actual state counts: Attempt=2, Processing=1, PublicationReceipt=1, QuarterPublication=1, Candidate=0; TransportAttempt=0 asserted.

Selected other actual results:

- Gate plus progress: result SHA `90073ef10bde8d5dcd1ddab14420fc42e666181c2351309c729ae43698961faf`; awaiting_approval=1, published=1, failed=0, exit10; two active quarter pointers, three receipts, one candidate.
- Hard conflict plus gate: SHA `79b897b2f4f2dcfb4f7f4fd0482189ae45c86bee27f879690e26095c425a1204`; awaiting_approval=1, failed=1, published=0, aggregate publication_conflict/exit9.
- Persistent five-CAS conflict: SHA `77fb6e2ed35c5b7c99795c56b9217c220fad4d3c2553dfc7a67fc9392ee6de53`; failed=1, zero current pointers/receipts, attempted manifest only.
- Partial transform: SHA `d9401b84970b031b968531fea53c3d6ee99f51065e91d61e5b6f0bd5bff11c90`; transformed=1, quarantined=1, failed=1, incomplete/exit3. Its publish refusal has zero quarter pointers and SHA `9c6d43d4c968c6fe7370d1d10b9fbf411a98e25710ee7be3ed885e5a83b5dbf2`.
- Empty publish: SHA `13f73a78c9c06ebaf09ea3579653e761c1d4b8d57c281e676cac5277441fd546`; every counter zero, unchanged/exit0.

Recovery evidence:

- `etl_result.after_object`: pre-replay checkpoint SHA `d02ebe7a7c8445b77b902f6b314fefcd85fd2515e778e637bccea0c0797bba3b`, Attempt result absent; post-replay SHA `9a2102d7ef70c622e8968856bb3cf93de1cbef80b60f966d4bfe127f6695f60d`, Attempt exact result present. Test verifies unchanged result bytes.
- `etl_result.after_attempt`: both pre/post checkpoint SHAs `7368a882141d4a9384aeccfbb19ae0d2975f95bda3850f3b8bbc4a76183d9194`.
- Publish-result crash: canonical pointer-state SHA remains `f16e543d7bbacbd497afa82691da500b240cb81b2d7cbc7fd7f635df667c0b34`; receipt count remains1 while Attempt repairs.
- Publication-after-pointer crash: canonical pointer-state SHA remains `ae4add0067894b77e1f4aadc3da9ab72695c7b15f5f36fcb91b7e98c0d99dcbd`; receipts move0→1. Pre/post checkpoint SHAs are `13951f1eb3fe7fee2bf4e0105c60a2d0bd0d189063f79b2d01b241eefe5598ef` and `ba77f766943f0f76423c63f7ea9d31d1c40d1542c49bfdacd68122c8535f1e56`.

The tests compare real state versions, exact result bytes and receipt membership. Native interruption tests use BaseException observers; actual OS process death is reserved for Task7, using these same public observer APIs.

## Self-review and limits

Inspected owned diff and ran `git diff --check` successfully; status contains only the seven owned paths. Applied N1/N4 to explicit result/intent/capture terminology, G30/G34 to separate result-context, transform-result and per-quarter publication validation, G25 to reuse CAS_ATTEMPTS, C3 to explain why command-path identity differs from Attempt keys, and T1/T5/T6 to red/green replay, malformed-result, gate/conflict and crash boundaries. No adjacent cleanup was performed.

Native runtime recorded in `actual-summary.json`: Python **3.14.0**, macOS 26.6.2 arm64; PyArrow25.0.1, Requests2.34.2, Azure Identity1.26.0, Blob12.31.0 and Tables12.7.0. Exact pins/settings remain unchanged. These results establish native functional behavior, not Linux amd64/Python3.14.8 worker memory/runtime/scratch or deployed capacity. All22 historical/native evidence reconciliation and full suite/build/wheel/process proof are reserved for Task7. Previously retained SEC-0141/0142/0143 duplicate conflicts remain independent blockers to the eventual Stage3 completion stamp; duplicate refusal is preserved. No COMPLETE/roadmap stamp, live SEC/Azure/auth/provider/network work, provisioning, deployment, workflow, image build or later-stage routing was performed. Development evidence remains retained indefinitely under the ignored `.sdd` directory.

## Commit

`9c12b5738f8969380a0a5aad4f33295356abf239` — `feat: expose raw-only transform and safe publication commands`. Exact branch/base/stage/names/diff/check/commit/status argv and results are retained under task6-evidence; `owned.diff` is the complete committed diff. Post-commit status was clean.

## Review fix round 1 — Important I1

Confirmed the review finding through the existing acquisition decoder: normalized content identity permits whitespace/property ordering differences. Added two failing tests using semantically identical noncanonical bytes at the **matching** immutable snapshot content-ID path. Both red tests returned exit0 and produced outputs before the fix. The fix is six production lines in the owned `etl/commands.py`: read/decode snapshot, verify decoded path identity, compare original body with existing `encode_workset`, refuse with Conflict before calling transform_workset or scanning Processing. No global/acquisition decoder or Task3 change.

Existing acquisition behavior is explicitly verified independently in both tests: `decode_snapshot_workset(noncanonical) == decode_snapshot_workset(canonical)` and existing `encode_workset(snapshot)` reproduces canonical bytes. Tests use actual local stored object bytes and the actual CLI; they retain pre/post state/object byte snapshots. Green refusal exits9, leaves Processing/pointers empty, retains no result object, and has identical complete non-run object maps before/after (no observation/transformed/quarantine/curated output). Command intent/error Attempt audit remain available.

Evidence is separate in `task6-fix1-evidence/`: `red-canonical-snapshot.json` retains both expected failures; `green-etl-covering.json` retains **28 tests passed, 3.767 seconds, exit0**. Full argv/cwd/environment/stdout/stderr/exits are retained. Guarded commands:

```sh
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_cli.EtlCliTests.test_noncanonical_snapshot_whitespace_refuses_before_transform_outputs test_etl_cli.EtlCliTests.test_noncanonical_snapshot_property_order_refuses_before_transform_outputs -v
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_cli -v
```

Cwd: `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`. `SEC_EDGAR_TASK6_PROOF_DIR` selects separate red/green retained roots; each malformed case has `files/canonical-refusal-proof.json`, before/after checkpoints and full ledgers. Verified actual identities:

- test_noncanonical_snapshot_whitespace_refuses_before_transform_outputs: snapshot `worksets/sec/snapshot/sha256=4e059646c4a441d804d74d7056127cdda28691385dbe5a67886f5ad805290303/workset.json`, canonical body SHA `513a010be608636e74b819d4c11b9ac925115f29c7de461dfbd69812d9781c08`, noncanonical body SHA `87df086b02c7b23bce27203eddc5efd7efc459cbb1781812350d48080636ee26`, refusal proof SHA `2cd5c8a7f4e2cad3bab54c1daef4f24cfff9cd5b742f66f9b21d2619a67274d9`.
- test_noncanonical_snapshot_property_order_refuses_before_transform_outputs: snapshot `worksets/sec/snapshot/sha256=4e059646c4a441d804d74d7056127cdda28691385dbe5a67886f5ad805290303/workset.json`, canonical body SHA `513a010be608636e74b819d4c11b9ac925115f29c7de461dfbd69812d9781c08`, noncanonical body SHA `dd911eb03cad89e9abbaab771618c5e269a622b4b61e2413010f0ff0c134b0fd`, refusal proof SHA `b73ce808b8bbb695cd7fa124215222b6565766649f4bb7081bfdcdccb6108bc4`.

Self-review: inspected full two-file diff; `git diff --check` passed. Applied N1 explicit snapshot-body/decoded names, T5/T6 semantically equivalent byte variants and no-output assertions. No adjacent cleanup or additional source changes. Scoped ETL covering verification includes existing canonical real/empty/replay behavior. No full suite/acquisition/workspace rerun was needed for this isolated boundary fix.

Scope clarification superseding earlier report wording: **Task7 reports `all22_stage7_checks` as reserved. Execution of those22 integrated checks and Linux capacity measurement belong to the later roadmap Stage7.** Task7 still handles its authorized full suite/build/wheel/process evidence. Closed authorizations, exact dependency pins and historical duplicate refusal remain unchanged.

Fix commit: `63c327390f76d466e04fb8285f7c95f39e4f4937` — `fix: require canonical snapshot bytes before transform`. Exactly the two owned files committed; post-commit status clean.
