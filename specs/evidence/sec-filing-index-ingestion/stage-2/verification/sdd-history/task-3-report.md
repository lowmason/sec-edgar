# Task 3 implementation report

Status: DONE (implementation verified; controller owns fresh Spec/Quality review).
Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`.
BASE: `3085d6765f65529820743c2d86dca84a497c2060`.
Final HEAD: `c22285aad83cbf88b238f3c49b836842f0ccbad8`.

Commits:

- `20128669bef75362eba2b5e9e5d30e84b1f62a28` — `feat: add durable acquisition stores and source state`.
- `c22285aad83cbf88b238f3c49b836842f0ccbad8` — `fix: use host errno for immutable object path guards`.

## Before/after insights

Before: no storage/state implementation existed. Task 2's corrected immutable mapping codecs, explicit acquisition mode, pin date and exact approved raw paths were the producing contracts.
After: independent clients/processes use real SQLite transactions and the same filesystem/registry; simultaneous absent reads converge on one first binding, and reopening returns that exact pin. Raw files and state transactions intentionally have separate durable boundaries. Later failures retain successful snapshot pointers and immutable pins; later receipts of the same bytes update receipt recency without rewriting the content identity.

## Implemented scope and actual interfaces

All specified `StateStore`, `ObjectStore`, `LeaseStore`, `LeaseHandle`, error classes and `AcquisitionState` methods are implemented. Only protocol bodies use ellipses. No Task 2 production record or config file was changed.

```python
open_stores(settings: Settings, *, base_path: Path | None = None,
            observer: BoundaryObserver | None = None) -> tuple[StateStore, ObjectStore, LeaseStore]
LocalStateStore(root: Path, *, page_size: int = 128, observer=None, binding=None)
LocalObjectStore(root: Path, *, observer=None, binding=None)
LocalLeaseStore(root: Path, *, clock=None, observer=None, binding=None)
AzureStateStore(source_client: TableClient, attempt_client: TableClient, *, observer=None)
AzureObjectStore(service: BlobServiceClient, *, observer=None)
AzureLeaseStore(service: BlobServiceClient, *, lease_seconds: int = 60,
                uncertainty_seconds: float = 2, clock=None, observer=None)
open_azure_stores(settings: Settings, *, observer=None)
AcquisitionState(store: StateStore, *, clock=None)
attempt_key(context: RunContext) -> str
store_bundle(root: Path, *, observer=None, clock=None) -> tuple[StateStore, ObjectStore, LeaseStore]
Faults.at(point: str, action: Callable[[], None]) -> None
```

Factories revalidate complete settings before side effects. Local roots resolve from the same configured `storage.root` under the explicit `base_path` (cwd by default). Injected local clocks expose `now()`; Azure observation clocks expose `now()` and `monotonic()`. Defaults use UTC/monotonic system clocks. Local state opens/closes a fresh SQLite connection per operation; `close()` closes the logical client. Lease clients retain durable ownership in the shared SQLite root.

All factories persist/check the same immutable registry at `locks/sec-owner-lowell-mason/binding.json`; no collector-specific namespace or request budget is created. The registry records fixed account/namespace, shared SEC and coordination policy, endpoints/tables/containers/API versions and resolved fixture root. Azure checks it before constructing Table authority clients. Conflicting bytes fail closed. All leases use `locks/sec-owner-lowell-mason/sentinel.json`; reopening preserves its existing journal. Registry and sentinel keys are fixed application constants.

Local objects use descriptor-relative validated parents, `O_NOFOLLOW`, exclusive temporary files, file/directory fsync and exclusive hard linking; no overwrite rename is used. Same-content collisions verify hash/length; differing bytes are corruption. Promotion verifies staging and approved raw address/content before exposing a raw reference, then verifies the result. Observers interrupt actual transitions at `state.after_insert`, `state.after_replace`, `object.after_fsync`, `object.before_link`, `object.after_link`, `object.before_promote`, `object.after_promote`; Azure adds `object.before_upload`, `object.after_upload` and lease post-operation boundaries. No hook bypasses a transition.

Table partitions are fixed namespace plus kind; ordinary source/snapshot/binding/directory/coordination/queue kinds use `SourceState`, and `Attempt`, `TransportAttempt`, `Failure` use `Attempts`. Row keys reversibly quote arbitrary stable keys; `StableKey` verifies their identity. Nested values use canonical JSON `Payload`, detached into immutable `Versioned` records. Actual opaque write/read header ETags are retained; query pages require service `odata.etag`, rejecting SDK Timestamp fallback. Every continuation, including an empty continued page, is exhausted. No wildcard update, merge, upsert or extra table binding exists.

Source row payloads contain nested `source`, `first_discovered_at`, `last_discovered_at`, `discovery_status`, `acquisition_status`, `needs_acquisition`, `latest_downloaded_snapshot` (exact hash), `latest_received_at`, `last_error`. Discovery first/last timestamps are monotonic extrema; status follows the latest observation. Successful Snapshot records remain immutable by `(source_id,sha256)`, including first accepted receipt metadata. A newly supplied receipt timestamp controls the mutable latest receipt pointer; older receipts never replace it. Failure keeps downloaded status/pointers where success exists and marks `needs_acquisition=True`. Pending scans include every period. A new binding requires a remembered snapshot; an existing durable binding always wins before retry-candidate validation. Conditional state update retries are bounded at five and then surface `Conflict`.

Attempt identity hashes the run/execution/command/attempt/image tuple. Begin is idempotent, interruption leaves `in_progress`, and finish records immutable result/error audit without overwriting an already finished different result. Transport rows retain full context/receipt/permit, request ID, ordinal 1–5, status/bytes/epoch and observed `next_allowed_at`. Failure rows retain source, structured error, timestamp and active attempt identity where a command was begun.

**Controller-confirmed next-task dependency:** Task 4 owns adding `Permit.next_allowed_at: datetime|None=None` from the leased Blob journal's persisted reservation/cooldown. Task 3 uses `getattr(permit, 'next_allowed_at', None)` and serializes supplied UTC observations; it stores explicit null for isolated cases. It fabricates no timestamp and reads no Table pacing authority. Task 5 must retain final actual retry/server-defer timing as attempt metadata. Task 4 also owns the prescribed `LeaseStore.read_journal` / `write_journal` extension.

## SDK execution gate and exact request semantics

Installed inspection ran before Azure implementation, with no credential/client construction or network. Evidence: `specs/evidence/sec-filing-index-ingestion/stage-2/sdk-signatures.json` contains exact versions, 18 public signatures, 27 installed-source SHA-256 hashes, enums, source references and conditional keyword semantics. An authorized independent helper performed read-only SDK inspection; this implementer remained the sole writer.

Selected versions are Blob 12.31.0, Tables 12.7.0, core 1.41.0, identity 1.26.0. Blob `api_version="2026-04-06"` and Tables `api_version="2020-12-06"` are explicit; Blob's installed default is newer, so relying on defaults would be incorrect. `MatchConditions` is the installed plural symbol. Blob immutable upload uses `overwrite=False` plus `MatchConditions.IfMissing`, yielding `If-None-Match: *`. Table `create_entity` uses atomic Insert Entity POST; no invented Blob-style If-None-Match argument is added. Replacement uses `UpdateMode.REPLACE`, actual ETag and `MatchConditions.IfNotModified`, yielding exact `If-Match` PUT. SDK lease methods return None and update `.id`; the server-returned ID is used in renew/release and the sentinel's `lease=` upload keyword.

Azure credentials are managed identity at the validated factory boundary. Tests patch that factory construction and use only a synthetic SAS for the SDK's pure Table constructor plus an in-memory transport; no credential acquisition/auth request occurs. Storage pipeline retries are explicitly zero for total/connect/read/status; factory connection/read timeouts are 5/10 seconds. Installed Blob downloads additionally retain bounded three-attempt idempotent content-processing loops (including SDK sleep), documented in the signature evidence; those SDK internals do not authorize SEC retries.

Lease observation reads raw success-response Date before SDK deserialization, bounds RTT/skew/wall-versus-monotonic divergence to configured uncertainty (at most 2 seconds), rejects absent/malformed/nonfinite/excess-latency observations, and returns conservative `observed_until=min(client_start,server_date)+duration-uncertainty`. Azure duration must be whole seconds in 15–60 and equal the configured duration. Ownership checks read the exact sentinel ETag and bytes and issue the same journal with both actual lease ID and exact If-Match; 404/409/412 ownership failures stop authority. Ambiguous acquisition/clock failure grants no handle; the provider's lease remains finite.

## Verification and TDD evidence

Every log starts with its exact command and exit code; complete outputs are retained at the absolute paths below. Bootstrap failures prove missing contracts only. Actual behavioral RED failures and corrected fixture/transport errors are distinguished honestly. No recorded failing output was replaced.

Focused command form:

```sh
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_storage.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_state.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_azure_contracts.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

Final result: **78/78, exit 0, pristine output**: 12 local storage, 11 state, 17 scripted Azure and 38 unchanged prior tests. The process race uses spawn, an absent-read barrier, independently opened connections and bounded joins; no wall-clock sleeps. All Azure sends reach only the scripted transport and reject unscripted requests.

| Gate | Full retained log | Result |
|---|---|---|
| Bootstrap only; missing contract assertions | [red-bootstrap-storage.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-bootstrap-storage.txt) | 10 methods / 10 failures; exit 1 |
| Bootstrap only; missing contract assertions | [red-bootstrap-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-bootstrap-state.txt) | 9 / 9 failures; exit 1 |
| Bootstrap only; missing contract assertion | [red-bootstrap-azure_contracts.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-bootstrap-azure_contracts.txt) | 1 / 1 failure; exit 1 |
| Initial state behavioral RED, including one frozen-mapping test correction | [red-behavior-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-behavior-state.txt) | 9 / 3 failures; exit 1 |
| Corrected actual source preservation/address/older-receipt RED | [red-behavior-corrected-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-behavior-corrected-state.txt) | 10 / 3 failures, no errors; exit 1 |
| Original sentinel reopen error retained | [red-behavior-corrected-storage.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-behavior-corrected-storage.txt) | 11 / 1 error; exit 1 |
| Corrected sentinel behavioral assertion RED | [red-sentinel-corrected.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-sentinel-corrected.txt) | 11 / 1 failure; exit 1 |
| Initial local GREEN | [green-local-storage.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-local-storage.txt) | 11 / 11 pass; exit 0 |
| Initial state GREEN | [green-local-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-local-state.txt) | 10 / 10 pass; exit 0 |
| Azure adapter absence RED before implementation | [red-azure-http-contracts.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-azure-http-contracts.txt) | 16 / 16 failures; exit 1 |
| Original scripted-transport/settings/Date errors retained | [azure-first-implementation.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/azure-first-implementation.txt) | 16 methods / 7 errors; exit 1 |
| Corrected transport isolates raw-Date behavioral RED | [red-azure-date-observation.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-azure-date-observation.txt) | 16 / 1 failure, no errors; exit 1 |
| Initial Azure GREEN | [green-azure-http-contracts.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-azure-http-contracts.txt) | 16 / 16 pass; exit 0 |
| Final pin/latest-receipt behavioral RED | [red-final-boundaries-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-final-boundaries-state.txt) | 11 / 2 failures; exit 1 |
| Final wall-clock/nonfinite elapsed behavioral RED | [red-final-boundaries-azure_contracts.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-final-boundaries-azure_contracts.txt) | 17 methods / 2 subtest failures; exit 1 |
| Final source/state GREEN | [green-final-boundaries-state.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-final-boundaries-state.txt) | 11 / 11 pass; exit 0 |
| Final Azure GREEN | [green-final-boundaries-azure_contracts.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-final-boundaries-azure_contracts.txt) | 17 / 17 pass; exit 0 |
| Full suite before feature commit | [green-full.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-full.txt) | 77 / 77 pass; exit 0 |
| Host ELOOP leaf-symlink behavioral RED | [red-host-errno.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/red-host-errno.txt) | 12 / 1 failure; exit 1 |
| Host errno focused GREEN | [green-host-errno.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-host-errno.txt) | 12 / 12 pass; exit 0 |
| Fresh final full regression before correction commit | [green-full-final.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/green-full-final.txt) | 78 / 78 pass; exit 0 |
| Exact ten-path staging/diff check/feature commit | [scope-and-commit.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/scope-and-commit.txt) | all commands exit 0 |
| Exact two-path correction/diff check/final status | [host-errno-commit.txt](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/host-errno-commit.txt) | all commands exit 0 |

## Scope, self-review and concerns

Exactly ten Task 3 paths were committed in the feature commit: four named storage modules, state.py, three named tests, tests/support.py and the prescribed SDK evidence file. The host-errno fix changed only local.py/test_storage.py after its regression failed on actual macOS ELOOP=62. Final BASE-to-HEAD `git diff --check` passed. Only the four original index-ingest deletions remain in status, unstaged; no broad staging/reset/stash/restore occurred. Reports/logs are local `.sdd` artifacts, not staged. Primary, roadmap/client/download scaffolds, F1, parent/plan, shared contracts/progress, dependency pins and Task 2 producing modules were not edited. No plan checkboxes were changed.

Self-review resolved source success preservation, monotonic receipt pointers, source-address rejection before insert, existing-pin precedence, preserved sentinel initialization, raw Date rejection, finite clock bounds and host errno translation. Clean-code applications: named conditional/durability policy constants and host errno symbols (G25), immutable adapter/state boundaries (G6/G30), meaningful stable keys/pointers/operation names (N1/N4/N7), deterministic restart/race/collision/failure/continuation/clock edge coverage (T1/T5/T6). No adjacent cleanup or out-of-scope refactoring was performed.

No known remaining Task 3 correctness concern. Offline request construction is locally verified; effective Azure permissions, server lease timing, HNS/Table behavior and real crash behavior remain Stage 7 checks. The collection path must verify promoted raw bytes before calling `remember_snapshot`; isolated state tests explicitly use synthetic Snapshots. No transaction spanning Blob/files and Table/SQLite is claimed. No Stage 1 live window was reopened; no SEC/Azure/auth/compute/registry network access or parser/publication/reconciliation/provisioning/scheduling work occurred. This is not Stage 7 acceptance, recovery-horizon/format-coverage evidence or deployment readiness. The controller owns the fresh task reviewer and integration decision.

## Fix round 1: deterministic conditional-create process validation

**DONE.** Review base `c22285aad83cbf88b238f3c49b836842f0ccbad8`; fix commit `129ca3a16dafdb82013a8fd28d3d653b58831112`. Only `packages/sec-edgar-ingest/tests/test_state.py` changed. The original external barrier could let `bind_once` see a completed binding before attempting its own insert. A test-only public StateStore wrapper now delegates to each independent real SQLite client, synchronizes the actual absent Binding read consumed inside `bind_once`, traces delegated insert outcomes and rethrows the actual `AlreadyExists` so production must reread/adopt the winner.

The stronger required assertions were RED before changing the harness: 11 tests, one failure, exit 1 (the old harness supplied no required internal event trace). After the harness correction, covering state **11/11** and full offline regression **78/78** passed, exit 0. Each retained process trace has nine globally ordered events with UTC timestamps, monotonic nanoseconds and PIDs: two internal absent reads before either insert, two insert attempts, one success, one actual create conflict, one loser reread and two identical adopted bindings. The successful create and loser reread retain the same version as the durable Binding row. No sleeps or repeated race loops were added.

```sh
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_state.py -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

Full logs: [RED](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-red-state.txt), [covering GREEN](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-green-state.txt), [full GREEN](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-green-full.txt), [scope/diff checks/commit](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-scope-and-commit.txt). Timestamped ordered traces: [covering](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-process-trace-state.json), [full](/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task3-evidence/fix1-process-trace-full.json). GREEN logs record exact commands and the `SEC_EDGAR_FIX1_TRACE` output environment.

Self-review: wrapper uses real public get/insert/replace/scan operations; it grants no alternate state and does not swallow the SQLite conflict. Both spawned processes open their own clients under the same configured root and binding. Working-tree and committed diff checks passed; only the explicit test path was staged. The four original index-ingest deletions remain unstaged. No production, SDK evidence, dependency, primary checkout or protected plan/client/download/F1 file was edited; no live access occurred. No remaining concern from this fix; controller owns scoped re-review.
