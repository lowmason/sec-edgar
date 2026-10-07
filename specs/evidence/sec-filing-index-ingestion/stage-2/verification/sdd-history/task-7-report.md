# Stage 2 Task 7 implementation report

Status: DONE, implementation and verification complete; fresh task Spec/Quality reviews remain the controller's gate. Written 2026-10-06. Commit details are recorded below after the named-path commit.

Worktree: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`, branch `codex/sec-edgar-stage-2`; dispatched base `4cbc9d8afcc793aa8d8402321019807e5ea3e526`. Requirements are the approved `task-7-brief.md`, including its verbatim Global Constraints, plus the controller's reservation-identity and current-result/frozen-origin clarifications. The primary checkout was not used for writes. No additional human permission was requested; approved tool escalation was used for the authorized isolated worktree writes and test/Git operations.

## Implemented behavior and scope

Collection now checks the actual retained source-workset object at `worksets/sec/source/sha256=<id>/workset.json`, its canonical bytes/digest, and the collector's exact effective configuration, image, parser, schema and pinned context. A real `discover(...)` to `collect(...)` integration test exercises this path, including corrupt retained-input refusal. Collection can have a new command/run/execution/attempt context while the snapshot workset keeps the immutable discovery origin.

For each member, an existing Binding wins before recovery, refresh policy or mutable SourceState pointers are inspected. Collection verifies the pinned Snapshot's exact source/kind/period/representation/envelope/raw hash/length. Otherwise, it uses an exact durable receipt checkpoint, or a verified reusable snapshot for `reuse_accepted`, or issues a new request through the existing RequestClient/coordinator. Explicit `refresh` is frozen on a new source workset; it cannot replace a binding on an existing workset.

New downloads preserve original entity bytes and full receipt headers. The sequence is staging body and receipt metadata, immutable state receipt checkpoint, raw promotion, immutable promotion checkpoint, immutable Snapshot record, atomic write-once Binding adoption, then verification of the winner. Concurrent losers adopt the existing Binding even when their downloaded originals differ. Snapshot assembly re-reads Binding authority and verifies every raw entity again before writing the snapshot workset create-only. No SourceState latest field selects an existing workset's input. Existing `remember_snapshot` behavior preserves first receipt metadata and monotonic SourceState recency; the existing methods were not rewritten.

Recovery reads only exact member checkpoint references. It validates the frozen original context and stored transport attempt/Permit against real request history, then validates exact retained bytes with the selected envelope validator. Raw-only recovery needs no HTTP sender. A staged-only receipt with absent raw can be promoted after verification; a lost staged-only entity allows a newly accounted request. An existing promotion checkpoint with missing/corrupt raw refuses repair even if staging remains. There is no object glob or mutable latest repair in production collection.

Ordinary acquisition failures retain gaps and allow safe independent members to continue. Every nonempty failed HTTP receipt, including retry prefixes before a later success, is quarantined under its real request identity with body hash, byte count, complete flag, headers, original context and error. Failed members do not erase earlier successful Snapshots or Bindings. Access denial, ownership loss and owner-wide policy block stop further sends; later existing pins can still be verified offline for honest pending counters. Existing durable denial/cooldown policy and inclusive five-attempt accounting remain authoritative.

Complete successful acquisition writes an immutable snapshot workset at `worksets/sec/snapshot/sha256=<id>/workset.json`. Successful empty discovery returns `no_new_sources` with an empty snapshot workset; incomplete/failed discovery or an unbound member yields no complete snapshot-workset reference. Create-only collision or missing/corrupt referenced raw produces a state-conflict gap.

Task 7 returns an honest CommandResult and exposes `before_result_write` immediately before return. Result-object persistence and Attempt finalization belong to Task 8; no results.py or CLI command implementation was added. No row parser, normalization, publication, reconciliation, orchestration, credentials, live SEC request or live Azure/compute operation was implemented or performed.

## Actual interfaces and durable shapes

`collection.py` provides the specified `collect(...) -> CommandResult`, `collect_member(...) -> Snapshot`, `raw_path(source, sha256) -> str`, `expected_envelope(source) -> str`, `snapshot_for(source, body) -> Snapshot`, and `recover_promoted(workset, source, state, objects) -> Snapshot | None`. It defines a structural `Faults` protocol with `hit(point)`. Existing scheduled Faults in test support gained a `hit` alias that invokes its original scheduled-action behavior.

The five authorized AcquisitionState methods are implemented without altering Binding selection, request budgeting or models:

| Method | Actual semantics |
| --- | --- |
| `reusable_snapshot(source, envelope_version)` | Reads observed source identity and latest downloaded Snapshot only for an unresolved member's reuse policy; refuses incompatible source/path/representation, returns None for absent or different-envelope metadata. Object verification remains collection's responsibility. |
| `record_receipt(workset_id, source, receipt, temporary_ref)` | Requires the active audited request context and latest finalized accepted transport row; exact receipt/context/source/url/staging path must agree. Inserts an immutable StagedReceipt candidate with a SHA-256 canonical payload key. |
| `staged_receipt(workset_id, source_id)` | Returns None or `{workset_id, source_id, receipts: [...]}`. Each receipt contains `checkpoint_id`, workset/source IDs, full Source and RunContext, full BodyReceipt, `temporary_ref`, actual `request_id`, and full finalized `transport_attempt`. Candidates sort by original receipt time then checkpoint ID. |
| `record_promotion(workset_id, snapshot)` | Requires a durable receipt candidate with the exact body hash/count; inserts immutable PromotionReceipt containing workset/source IDs, complete Snapshot mapping and SHA-256 checkpoint ID. Recovery additionally requires exact original timestamp/headers and validates the original receipt/transport before accepting it. |
| `promotion_receipt(workset_id, source_id)` | Returns None or `{workset_id, source_id, snapshots: [...]}`, sorted by original receipt time then checkpoint ID. These are recovery candidates; only Binding selects accepted workset input. |

The new logical StagedReceipt/PromotionReceipt kinds use the existing `table_for` routing to SourceState. No new table, backend registration, resource or storage adapter edit was needed. TransportAttempt remains in Attempts via the existing routing.

Raw locations preserve representation exactly:

```text
raw/sec/indexes/kind=quarterly/period=<YYYYQn>/sha256=<hash>/master.zip
raw/sec/indexes/kind=daily/period=<YYYY-MM-DD>/sha256=<hash>/master.idx
staging/sec/<run-id>/<attempt-id>/<source-id>/<actual-request-id>/body
quarantine/sec/<run-id>/<source-id>/<attempt-id>/<actual-request-id>/body
```

The body sidecar `receipt.json` is create-only beside staged/quarantined bytes. Snapshot validators retain all original response headers. Historical Permit monotonic values are retained as provenance and never reused for timing or authority; the current existing coordinator and storage UTC remain authoritative.

`downloaded` counts successfully accepted requested members that issued a new audited exchange in this collection invocation. `unchanged` counts accepted members without a new exchange, including binding reuse and checkpoint recovery. `pending` is requested members not verified complete; `failed` counts member failures; `quarantined` counts actual nonempty failed receipt bodies retained, so retries can produce more quarantine bodies than failed members. These counters do not inspect mutable latest to classify old accepted pins. Complete snapshot-workset identity is independent of the new collection invocation context.

## Compatible extension and Task 8 handoff

The declared four-positional `stage_receipt(objects, context, source, receipt)` cannot infer an actual reservation from BodyReceipt, which has no request ID. The controller explicitly authorized the minimum keyword-only extension:

```python
stage_receipt(objects, context, source, receipt, *, request_id: str | None = None) -> str
```

Omitting `request_id` fails closed with ValueError before staging. No body-derived, random or fallback reservation identity is invented. Production collection finds the exact receipt in current-context request history, requires the latest finalized row, matching Source/context/receipt/Permit identity, and supplies that real request ID. Recovery cross-checks the embedded finalized row against actual durable history. This extension deliberately leaves the literal four-positional helper call unusable without explicit identity; it is a reported interface limitation, not a silently fabricated compatibility behavior. The omission test is part of the retained original RED and final GREEN.

The fixture `install_newer_snapshot` uses an explicit `synthetic-fixture-install` reservation label and claims no HTTP exchange. It still uses real envelope validation, staging, promotion, verification and Snapshot state. No BodyReceipt/model/hash/pinning extension was introduced.

A private `_path_segment(value, label)` validates a nonempty explicit identity using `require_text` and `safe_relative_path`, then rejects `/`. This rejects absolute/dot/parent/empty segments, backslash, colon, percent, query and fragment characters plus control/blank strings. Collection validates run_id and attempt_id before any request. No public reusable helper contract was introduced. Task 8 needs equivalent early checks for identifiers inserted into backend/result paths, before opening/writing those paths. Its pending common-fixture 2015Q1 versus October-2026 daily-endpoint owner question is unchanged; Task 7 uses valid existing frozen endpoint provenance and explicit fixture clock override in the discover/collect integration test.

## Files changed and in-scope code discipline

Only these five task-owned code/test paths are included in the commit:

1. New `packages/sec-edgar-ingest/src/sec_edgar_ingest/collection.py` (371 lines): collection and recovery orchestration, provenance, quarantine and immutable assembly.
2. New `packages/sec-edgar-ingest/tests/test_collection.py` (545 lines): 32 behavior tests, including real process/race proofs.
3. `packages/sec-edgar-ingest/tests/support.py`: collection/fault builders and retained process/race proof helpers only.
4. `packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py`: five named producing methods, their required imports and accepted-status constant only.
5. `packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py`: actual snapshot assembly's exact member raw address/representation/envelope checks and required imports only.

Applied clean-code rules to the added behavior, with no adjacent cleanup or structural-only tidying:

- Applied descriptive side-effect names (N1/N7) to `stage_receipt`, `recover_promoted`, `_retain_attempt_failures`, and the five producing state methods.
- Applied cohesion/one-level abstraction (G30/G34) to provenance verification, retained envelope validation, per-member collection and complete-workset assembly; the planned collection module remains one acquisition responsibility.
- Applied explanatory values (G19) to checkpoint/context/receipt/request/winner and exact assembly paths; promotion candidates are distinct from accepted Binding authority.
- Applied named accepted-status constants (G25) for new receipt guards; no existing unrelated code was tidied.
- Applied boundary and nearby-bug tests (T5/T6) for empty versus failed discovery, staged/raw missing versus corrupt objects, retry-prefix quarantine, fatal halt counters, exact metadata/context/period refusal and unsafe identifiers.
- Kept brief design-intent comments (C3) for bounded retained validation, Binding re-read authority, offline pin verification and synthetic fixture identity.

Existing support.py and state.py are large shared modules (1253 and 530 lines after these changes). The additions stay in the named ownership areas; no restructuring was undertaken. The task's planned new collection.py and test file remain focused on acquisition and restartability.

## TDD evidence and exact test commands

All commands below ran in the isolated worktree using the existing Python 3.14 virtual environment. Logs retain exact argv, complete stdout/stderr, unittest diagnostics and exit code. Focused import commands use `PYTHONPATH=packages/sec-edgar-ingest/tests`; final test runs use `PYTHONDONTWRITEBYTECODE=1` and an explicit task trace directory. No dependency installation or external network access was needed.

Initial RED occurred before collection.py existed:

```text
.venv/bin/python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_collection.py -v
Ran 19 tests in 0.002s
FAILED (failures=19)
exit_code=1
```

Each failure was the tests' explicit missing-production-module assertion. This established the initially required pinning, restart, changed-original race, quarantine, empty/failed workset, schema/config/context and immutable-collision contracts before implementation.

Retained intermediate logs are evidence of actual failures and fixes, not success claims:

| Log | Recorded result / meaning |
| --- | --- |
| `task-7-red.txt` | Initial 19 missing-module assertion failures, exit 1, before production code. |
| `task-7-behavior-red.txt` | First implementation: 19 tests, 12 failures/9 errors (including subtests), exit 1. Exact receipt lookup incorrectly compared FrozenMapping to dict; also exposed forced-exit transient semaphore cleanup noise. |
| `task-7-assembly-red.txt` | 19 tests, two true behavioral failures, exit 1: old pin accounting followed newer latest, and wrong source-period Snapshot could assemble. Seven process exits and changed-original race already passed here. |
| `task-7-boundary-red.txt` | Seven named tests, four failures/one error, exit 1: broken latest lookup, checkpoint transport tamper acceptance, missing retry-prefix quarantine, later pinned member counted pending after fatal halt, and repeated Attempt identity conflict propagation. Existing staged/raw refusal guards also ran. |
| `task-7-collection-green.txt` | 26/26 in 4.040s, exit 0, after those fixes. |
| `task-7-input-red.txt` | Four named tests, three failures/one error, exit 1: direct incompatible member context, unsafe identifiers and failed failure-checkpoint propagation; two-source process proof already passed. The initial attempt-ID test used a harness that replaced attempt IDs. |
| `task-7-path-red.txt` | Corrected direct unsafe run/attempt calls: both subtests truly failed, exit 1, before the identifier guard. |
| `task-7-process-green.txt` | 30/30 in 5.313s, exit 0; enriched actual checkpoint/raw/workset-byte and race-order traces, plus two-source restart. |
| `task-7-promotion-metadata-red.txt` | Two named tests, two true mutation failures (received_at and validators), exit 1; a changed promotion checkpoint could invent original receipt metadata. Quarterly original ZIP collection already passed. |
| `task-7-covering-green.txt` | Final prescribed 115/115 in 15.591s, exit 0, after matching promoted timestamp/headers and validated Snapshot against the exact original receipt. |
| `task-7-full-green.txt` | Full package 250/250 in 26.141s, exit 0; empty stdout and no warnings/unexpected stderr. |

The exact final prescribed command was:

```text
PYTHONPATH=packages/sec-edgar-ingest/tests .venv/bin/python -m unittest -v test_collection test_state test_storage test_download test_worksets
```

The exact full-package command was:

```text
.venv/bin/python -m unittest discover -s packages/sec-edgar-ingest/tests -v
```

The full run contains 32 collection, 11 state, 12 storage, 44 download, 16 workset, 43 discovery, 41 coordination, 17 Azure contract, 12 config, 12 validation, 4 URL and 6 workspace/CLI tests. Azure tests use retained scripted contracts; real transport process tests use existing local loopback fixtures. The unimplemented CLI commands remain rejected in the existing workspace tests.

No source change followed these final GREEN runs. Output was inspected, and `task-7-proof-check.py` plus `task-7-proof-check.txt` additionally assert every one of the 250 test records ends in `ok`, exact footer/count, empty stdout, no unexpected stderr and exit 0. That script verifies the retained final process/race records; it does not rerun tests or construct historical proof.

## Real process exits and actual binding conflict evidence

Final proof files are in `task-7-full-traces/`, with a separate preceding final-covering inventory in `task-7-covering-traces/`. Earlier iterations remain in `task-7-traces/`, `task-7-additional-traces/` and `task-7-process-proof/`; none was deleted to retry.

For each of seven points, the test starts a fresh independent Python process, forces `os._exit(73)`, then starts a distinct successor and another offline repeat. All seven have exits `[73, 0, 0]`, empty stdout/stderr, three distinct retained PIDs, exactly one actual finalized transport request, identical accepted raw hash `1b4118c7b3720065bd11eb565fa97647ea142ed0318f7205c31aee463bd309b7`, and byte-identical repeated final snapshot workset. The last two also compare the workset bytes already present before the forced exit to final bytes. The JSON includes exact subprocess argv, exit/stdout/stderr, full staged checkpoints with original transport reservation/context, promotion/Snapshot/Binding state at the crash, verified raw bytes and final workset bytes.

| Forced point | Required durable state observed before exit |
| --- | --- |
| `after_receipt_checkpoint` | Exact receipt checkpoint exists; raw/promotion/Snapshot/Binding absent. |
| `after_raw_promotion` | Exact raw exists and verifies; promotion/Snapshot/Binding absent. Test deletes only temporary fixture staging bodies and uses a successor sender that raises if called. |
| `after_promotion_receipt` | Exact raw and promotion checkpoint exist; Snapshot/Binding absent. |
| `after_snapshot_record` | Raw/promotion/Snapshot exist; Binding absent. |
| `after_binding` | Exact first Binding exists; immutable snapshot workset not yet written. |
| `after_snapshot_workset_write` | Exact immutable workset bytes already exist. |
| `before_result_write` | Exact workset exists; Task 7 return boundary reached; no Task 8 result writer is implied. |

Before forced exit, the fixture collects only completed Turn cycles to dispose of transient multiprocessing semaphores. It does not close stores, unwind the collector or clean durable state; the process then exits without normal cleanup. This removed the initial semaphore resource-warning noise without filtering/suppressing warnings.

`two-source-process-resume.json` proves the first member's Binding survives an actual process exit after binding. A new process fetches only the second unresolved URL, returns `success`, `downloaded=1`, `unchanged=1`, `pending=0`, and preserves the first pin. A third offline process exits 0 with identical workset bytes.

`changed-original-bind-race.json` proves two independently spawned collectors each complete an actual audited request through real local stores/independent SQLite connections. Their original hashes differ (`203964cb70ac1bfae0210db0776984db66030e5b302c3086c285595a03bc12a3` and `37e8d9f8431be0de04c50359c4dab6e3787681e23670cbb357df9c79c3ffcd74`). Barriers hold them after durable receipt checkpoints and after both real Binding reads observe absence. Both subsequently call the actual store insert; one succeeds, one receives actual AlreadyExists, and the loser re-reads/adopts the winner. Both exit 0 and emit the same snapshot-workset reference and Snapshot. Both originals remain at their exact raw paths. UTC and monotonic_ns events retain process IDs/order; the final proof checker confirms both absence reads precede the two insert attempts, one actual conflict and one shared winner. No mock counter or fabricated CAS response establishes this proof.

## Self-review findings, boundaries and concerns

Self-review read the new production/test files and complete diffs of the existing ownership paths. It found and fixed the concrete issues captured in retained RED logs: detached-mapping receipt comparison; mutable-latest pin accounting; exact source period assembly; finalized transport provenance during recovery; failed retry-prefix quarantine; fatal halt accounting; context/path refusal before request; known state-checkpoint errors escaping honest results; and changed promotion receipt timestamps/headers. Each behavioral fix has retained failing evidence and final passing coverage. Checkpoint histories remain repairable candidates and never substitute for atomic Binding authority.

The task-owned implementation is complete and the final relevant/full test output is pristine. Fresh Spec/Quality reviews are not self-declared PASS. The controller owns those gates and the final whole-branch GPT-6.1 Max review.

The common-fixture question for Task 8 is still pending with its owner and was not silently resolved here. Task 8 also owns actual result writing and Attempt finalization after this tested return boundary. These are handoff boundaries, not unfinished Task 7 implementation.

The selected DEFLATE quarterly archive/plain daily representation, guards of 90 seconds, 67,108,864 received bytes and 536,870,912 expanded bytes, one owner-wide active collector, 3 requests/second without bursts and five total attempts were preserved. Tests prove bounded synthetic/retained acquisition behavior and actual local crash/conflict semantics; they make no global format coverage, capacity, SEC recovery-horizon or live Azure runtime claim.

Git scope checks preserve the four original index-ingest deletions unstaged; the primary checkout, roadmap, parent ADR, accepted F1 and manifest were not edited. Reports/logs/traces remain under the existing ignored SDD directory for controller retention, separate from committed fixtures. Task 7 tests use the actual committed existing fixture/support resources, not an ignored historical SDD test dependency.

## Commit and final scope verification

Created commit `4761e0e027782a1a78a4f43af6512fe193e77bf4` — `feat: pin immutable snapshots and resume incomplete collection`. The commit contains exactly the five Task 7 paths listed above (1268 insertions, four deletions within owned code). The Git index is empty afterward. The only remaining tracked worktree changes are the four original index-ingest deletions, still unstaged.

`task-7-staged-checks.txt` retains the exact named `git add`, cached names/stat/whitespace check and unstaged-name audit; all exit 0. `task-7-commit.txt` retains exact commit/log/show/status/index commands, stdout/stderr and exits. No source file changed after the final 115-test prescribed and 250-test full GREEN runs.

## Fix Round 1: quarantine retry evidence before success checkpoints

Status: DONE for the one adopted Important finding; fresh scoped Spec/Quality review remains required. This appendix supersedes the prior completion claim at `4761e0e` on retry-prefix crash durability. The reviewed original commit had Spec FAIL / Quality Needs fixes; it had no Critical or Minor findings. Read `task-7-review.md`, the copied `task-7-review-probe.command.sh` and decisive `task-7-review-probe-fields.txt`; the historical reviewer script was not rerun or represented as complete untruncated output.

The actual code confirmed the root cause: `_retain_attempt_failures` was called only after collect_member returned, while the receipt/promotion/Snapshot/Binding fault hooks were earlier. An ordinary failed retry prefix followed by a valid response could therefore become dependent on the old temporary spool after a success checkpoint. A successor's new RunContext scanned no old request history and could complete with missing quarantine evidence.

The fix changes only collection.py, test_collection.py and the collection process builder in support.py. No state.py/worksets.py/model/config/hash/pin/storage adapter/resource changes were needed. The original authorized stage_receipt explicit-request-ID extension is unchanged. No Task 8, network, authentication, registry, compute or primary-checkout work was performed.

New downloads call `_retain_attempt_failures` immediately after successful RequestClient.fetch, before staging or recording the durable accepted receipt and before any success crash hook. It retains every finalized nonempty failed receipt in that original request context, preserving original request/Permit ID, context, byte count, hash, headers, complete flag and error in the existing exact quarantine body and sidecar paths.

`_retain_attempt_failures` now verifies an existing body before considering the temporary file. It stages only when the exact retained body is absent, verifies it, then uses existing create-only put_once for the exact original sidecar. A corrupt body or unequal sidecar refuses; it is never overwritten. An already retained body/sidecar can be confirmed with the failed-body spool completely removed. If both retained body and original temporary body are missing, recovery refuses completion.

New private `_recover_saved_receipt(workset, source, entry, state, objects) -> BodyReceipt` first validates the immutable receipt checkpoint and its finalized transport/Permit provenance through the existing `_validated_saved_receipt`, then verifies/repairs failed receipt evidence using `RunContext.from_mapping(entry['context'])`. Promoted/staged recovery invokes this helper. An existing pin still wins first and its raw object is verified; collection then confirms failed evidence from this workset's saved receipt candidates matching the accepted hash. Unrelated different-hash losing candidates cannot select or replace the pin. No mutable latest pointer or current successor context is used to construct historical quarantine paths.

The `quarantined` result counter confirms failed nonempty receipt bodies belonging to the current collection RunContext. Pre-checkpoint retention and the outer confirmation are not added twice: the existing successful-retry test still returns exactly 1. Verification of evidence from an older saved context is excluded from the new context's counter, so the new-context successor correctly returns `quarantined=0` while the exact old quarantine body/sidecar remain present. This is a per-context receipt count, not a cumulative inventory count or a claim that no historical quarantine exists. If the same context is resumed, its already retained failed receipts can still count once for that context's confirmation.

### Actual behavioral RED before production edits

Added committed tests first and retained exact argv/stdout/stderr/exits in `task-7-fix1-red.txt`:

```text
PYTHONPATH=packages/sec-edgar-ingest/tests .venv/bin/python -m unittest -v test_collection.CollectionTests.test_retry_prefix_quarantine_precedes_every_success_crash_boundary test_collection.CollectionTests.test_recovery_verifies_original_quarantine_without_failed_spool
Ran 2 tests in 2.494s
FAILED (failures=8)
exit_code=1
```

All seven real process cases ran. The five member-level crash points failed the assertion that quarantine was durable before exit; the two later snapshot-workset/result hooks already followed outer retention and passed. Three independent historical body/sidecar/missing-body mutations, with the failed temporary body deleted, incorrectly returned success instead of state_conflict. Distinct successor run/execution/attempt contexts and forbidden senders were used throughout. Exact process commands, exits, pre/post fields and body/sidecar bytes are retained in `task-7-fix1-red-traces/` rather than printing repeated configuration JSON.

Before production changes, a further test retained `task-7-fix1-multiple-red.txt`: one real failure, exit 1, showing that separate read-timeout and HTTP-503 retry bodies were absent at the accepted receipt checkpoint. The test additionally requires each original reservation's distinct body/headers/sidecar to survive recovery without its failed temporary file. The process test was strengthened to compare the recovered and repeated workset bytes explicitly; no implementation was written before the reported behavioral REDs.

### Final GREEN and process proof

`task-7-fix1-focused-green.txt` retains the four targeted regressions, including the existing same-context successful-retry counter check: 4/4 in 2.788s, exit 0, empty stdout, no warnings or unexpected stderr. Its seven prefix/crash records are separately retained in `task-7-fix1-focused-traces/`.

After the final production change, the prescribed covering command ran once:

```text
PYTHONPATH=packages/sec-edgar-ingest/tests .venv/bin/python -m unittest -v test_collection test_state test_storage test_download test_worksets
Ran 118 tests in 18.188s
OK
exit_code=0
```

`task-7-fix1-covering-green.txt` contains complete output: all 118 individual records end in ok, empty stdout and no warnings/unexpected stderr. There are now 35 collection tests; the covering run also executes all original state/storage/download/workset tests, seven original crash cases, two-source restart, real discover-to-collect path verification and actual two-insert binding conflict. No production source changed afterward. The previous 250-test full-package result is historical evidence for `4761e0e`; a new full-package result is not claimed. The focused fix changed no shared state/model/storage API and the prescribed covering set covers all touched behavior and downstream interfaces, so the requested restraint on redundant full-suite waves was followed.

`task-7-fix1-covering-traces/` contains 16 JSON proof files: seven new retry-prefix cases, seven original crash cases, the two-source restart and the actual changed-original binding race. New cases combine the exact 21-byte `b'retained retry prefix'`, SHA-256 `78a431c8a01f444e3b71b1be06b4b5b7240935db9153b88bf6bec6004cf46584`, with a valid original daily body. At every crash point the exact failed request's body/sidecar already verify before `os._exit(73)`. The fixture then removes only its synthetic sender's temporary spool, after verifying durable quarantine. Two distinct successor processes with `successor-run` / `successor-execution` / `successor-attempt` and a sender that raises if called exit 0; all three subprocesses have empty stdout/stderr.

The retained proof confirms two actual original requests (retry then received), no successor transport call, three distinct PIDs per case, identical failed body/sidecar before and after recovery, exact original request/Permit/context/header/error/hash agreement, accepted raw hash and receipt metadata, preserved bindings when already present, and byte-identical recovered/repeated snapshot worksets. The last two points additionally match the pre-exit workset bytes. Every successor returns success/downloaded 0/unchanged 1/pending 0/failed 0/quarantined 0/gaps empty with the current context while retaining the original snapshot-workset origin.

`task-7-fix1-proof-check.py` and `task-7-fix1-proof-check.txt` retain the exact read-only proof audit command and concise complete stdout/stderr/exit 0. The audit checks all 118 test records/footer/noise and all new prefix/process invariants, plus the original seven crashes and actual two absent reads / two inserts / one conflict / shared winner race. It reads actual new traces and does not fabricate or rerun historical review probes.

Self-review read the complete three-file fix diff. Applied N1/N7 and G30/G34 to the side-effect-aware recovery helper and idempotent retention, G19 to original context/evidence variables, and T5/T6 to all durable-boundary combinations, missing/corrupt body/sidecar cases, multiple receipts and counter confirmation. No adjacent cleanup, additional architectural decision or new correctness concern was identified. Existing broad support/state file-size concerns and all Task 8 endpoint/result/Attempt handoffs remain as documented above. Fresh scoped review must assess this fix before Task 8 proceeds.

Fix Round 1 commit: `73ea758e37f6b6ed78103b2a731b2f125bd96a96` — `fix: retain retry evidence before snapshot checkpoints`. Exactly the three named fix paths are committed (201 insertions, 11 deletions); state.py and worksets.py are unchanged from the reviewed commit. `task-7-fix1-staged-checks.txt` and `task-7-fix1-commit.txt` retain exact Git commands/outputs/exits, named scope and clean cached whitespace check. The index is empty afterward; only the four original index-ingest deletions remain unstaged. No source changed after the 118-test final covering GREEN. Fresh scoped review remains pending.
