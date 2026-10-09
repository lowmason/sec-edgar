# Task 3 execution report

Status: DONE. Commit `248737df5054f3b910b7fb11fc068ba3cab99a26`. Final checked suite: 13 tests passed, exit 0; CLI: 25 passed; ETL CLI: 38 passed; staged whitespace check: exit 0.

## Scope and authority

Executed the approved Task 3 brief in `/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar`, branch `codex/sec-edgar-stage4-plan5`, following Task 1/2 accepted APIs. Created only `workflows/checked.py`, `tests/support_checked.py`, and `tests/test_workflow_checked.py` for the implementation commit. This report and create-only Task 3 evidence remain unstaged for controller review. No controller ledger or approved document was edited.

The brief's verbatim Global Constraints were read and retained: original bytes and immutable input identity, invalid member retention without complete-coverage claims, no mutable latest, per-quarter pointer publication authority, recoverable indexes, closed live access, indefinite development retention, pinned dependencies and accepted guards. No new dependencies, pins, parser tolerance, network/provider construction, deployment, triggers, or Stage 7 execution occurred.

## Actual TDD evidence

Evidence directory: `specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/task-3/`.

1. Created the complete prescribed real-store builder and 12 named tests from the brief before production code.
2. `01-red.json`: prescribed offline/frozen network-guarded checked test command exited 1 with missing `sec_edgar_ingest.workflows.checked` import, the specified initial red condition.
3. Implemented the approved checked module. `02-green-attempt.json`: identical supplied tests passed, 12 tests, exit 0.
4. `03-cli-regression.json`: required `test_cli.py`, 25 tests passed, exit 0. `04-etl-cli-regression.json`: required `test_etl_cli.py`, 38 tests passed, exit 0. `05-diff-check.json`: required whitespace command exited 0.
5. `06-child-cli-captures.json` retains four actual discover/collect/transform/publish CLI argument vectors, exit codes, complete stdout and stderr from a separate real-store retry-prefix chain; all exits were 0. `07-child-capture-command.json` retains the enclosing offline invocation and exit/output. The patched wrapper delegates to the actual production CLI and preserves output forwarding; no fake durable results are used.
6. Self-review explored source-workset byte tampering. `08-source-chain-red.json` is an exploratory PASS, despite its initial filename: current readback calls historical capture first and already refused noncanonical source bytes. It is not claimed as red evidence.
7. Extended the new test to guard the new child CLI boundary. `09-source-pre-dispatch-red.json`: one actual assertion failure, exit 1, because a noncanonical retained source object reached the child CLI instead of being rejected first. No production fix preceded this genuine red.
8. Corrected only `_snapshot_input` in `checked.py`, then reran the entire checked test module with all supplied and added assertions unchanged. `10-final-checked-green.json` records the final result.

All evidence files retain exact argv, exit, stdout and stderr. No full-suite repetition was performed; Task 11 owns that milestone. The local helper correction does not alter shipped CLI/ETL helpers exercised by the already passing corresponding subsets.

## Interfaces and implementation

- `CheckedChild(call, result_ref, result)` retains the exact three requested fields, recursively freezes call through Record validation, accepts decoded CommandResult/EtlResult, and rejects inconsistent references; construction does not certify completion.
- `ChildCall` and `_validated` enforce exact closed fields, expected namespace/context/input/result path, canonical intent and exact bool/null flag types.
- `child_attempt_id(run_id, workflow_command, workflow_attempt_id, step_id, command)` hashes parent command into child identity; `call_ref` and `call_key` preserve the approved namespace and state identity.
- `make_call(context, command, attempt_id, input_ref, fixture_sha256=None, *, workflow_command, workflow_attempt_id, step_id, today=None, mode=None, discovery_id=None, refresh=False, force=False)` preserves the prescribed API.
- `Dispatcher(context, settings, fixture_pack, state_dir, store, objects, observer=None).execute(command, step_id, settings, flags)` retains exact storage/issuer binding, origin collection settings/priority and current transform/publication versions, writes immutable call before call index and dispatch, then validates durable result and command plus exact repaired Attempt/input-chain evidence before comparing exit/stdout.
- `read_child(call, store, objects)` and `read_child_capture(call, objects)` share immutable authority; the latter reads no mutable indexes or active pointer. Publication evidence follows exact result manifest/candidate paths.
- `unfinished_child(call, store)` reads retained unfinished Attempt/context/errors without completion; `ChildUnfinished` carries call/outcome/gaps/repair_pending/exit/stdout/stderr and the prescribed resumability/details payload. Post-CAS repair stays unfinished until shipped CLI replay repairs it.

## Deviation from prescribed code and self-review

The one production correction moves canonical `_source_input` validation ahead of the mutable/object-only branches of `_snapshot_input`. The prescribed code performed this only in the object-only branch; mutable `_pinned_members` decoded but did not certify original source bytes before CLI invocation. Existing current readback was already protected by its preliminary historical capture, explaining the exploratory passing test. The new regression proves pre-dispatch refusal as well as both readback paths. The correction retains the public API and all shipped helper semantics. The controller explicitly approved proceeding with this reproduced in-scope correction.

Clean-code applied: cohesive canonical-input verification remains at the checked boundary (G6/G30); explanatory `snapshots` and `sources` variables make retained-chain authority visible (G19/N1); named CHILD_COMMANDS/CALL_FIELDS and versioned descriptor names retain the prescribed intent (G25/N3); new corruption-boundary test exercises real immutable source bytes and both readback paths (T1/T5/T6). No adjacent cleanup was applied, and no structural-only tidy was mixed into this feature commit.

Self-review confirmed constructor freezing, exact flag booleans, namespace collisions, call object-before-index-before-CLI ordering, origin/current version separation, raw and binding refusals, no latest-pointer access, terminal durable failed results versus unfinished ordinary ancillary failure, and retained retry-prefix quarantine separate from terminal source refusal. Fatal collection/terminal parser consumer coverage remains explicitly assigned to Task 5, advancing-pointer historical replay to Task 6, and workflow corruption matrix to Task 10.

No unresolved implementation concern identified in this scope. The fixture context uses actual current start time with an explicit pinned fixture date as prescribed; saved exact result starts remain CLI-selected and are checked against the parent lower bound/deadline.
