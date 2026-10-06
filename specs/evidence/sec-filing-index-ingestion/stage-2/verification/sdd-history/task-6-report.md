# Task 6 implementation report

Status: implementation and self-review complete; fresh controller Spec/Quality review pending. BASE: `50b2756330cbef91b5c664a5f4cc72c2f5c35626`. Branch: `codex/sec-edgar-stage-2`. Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`. Commit: `c51fe3b3350d71195ed94880359304ab3634aca9`. No task/plan checkbox was ticked.

## Result and scope

Implemented trusted retained-family JSON discovery, actual root/year/QTR traversal, explicit missing/unsupported/failed units, evidence-backed DirectoryProgress, per-discovery frozen checkpoints and conservative owner-wide CAS gap/boundary updates. Actual selected children are quarterly `master.zip` and daily `master.YYYYMMDD.idx` with valid matching calendar/hierarchy dates. Size/time labels remain unparsed discovery metadata. Root `master.zip` is an alternative only when the actual open quarter is requested; it never becomes an independent member or equality assumption. Selected and root alternate codecs carry omission reasons; unsupported-only quarter listings remain unresolved.

All HTTP uses the existing RequestClient with source=None and the existing Coordinator/owner budget. Access denial and owner PolicyBlocked remain terminal gaps; no transport, policy hook, retry, guard, source-envelope or coordination behavior changed. Successful listing bytes and exact original receipts are content-addressed, put_once-written and hash/length-verified before successful DirectoryProgress. Invalid/truncated/failed originals are retained under quarantine; failed DirectoryOutcome has no accepted listing hash or source IDs. Source observation times come from the actual successful receipt, including verified cached receipts, rather than command start or provider labels.

Applied the prescribed implementer prompt, test-driven-development, clean-code and clean-coder; applied verification-before-completion for the final checks. Read only the task brief with verbatim Global Constraints, shared contracts and Task 5's Review fix round 1 appendix, plus the named retained schema audit. No full-plan read, subagents, live SEC/Azure/compute/auth, parser/normalization/publication/reconciliation/orchestration or Task 7/8 implementation occurred. Existing models.py, worksets.py, config.py/pin_context and the committed retained manifest are unchanged.

## Actual interfaces

Public discovery interfaces match the brief:

```python
@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    name: str
    href: str
    kind: Literal['dir', 'file']
    size_label: str
    modified_label: str

parse_listing(url: str, body: bytes) -> tuple[DirectoryEntry, ...]
quarter_of(day: date) -> str
quarter_span(start: str, end: str) -> tuple[str, ...]
required_daily_quarters(today: date, handoff: date, boundary: date | None,
                        pending_periods: tuple[str, ...]) -> tuple[str, ...]
advance_daily_boundary(previous: date | None, today: date,
                       outcomes: tuple[DirectoryOutcome, ...]) -> date | None
discover(settings: Settings, context: RunContext, mode: Literal['quarterly', 'daily'],
         discovery_id: str, client: RequestClient, state: AcquisitionState,
         objects: ObjectStore, today: date, refresh: bool = False) -> SourceWorkset
```

The minimum authorized AcquisitionState additions are:

```python
directory_progress(discovery_id: str, url: str) -> Versioned | None
record_directory(discovery_id: str, outcome: DirectoryOutcome, members: tuple[Source, ...], *,
                 evidence: dict[str, object] | None = None,
                 selection: dict[str, object] | None = None,
                 expected_gap: str | None = None) -> None
failed_directories() -> tuple[DirectoryOutcome, ...]
daily_boundary() -> date | None
advance_boundary(candidate: date, discovery_id: str,
                 outcomes: tuple[DirectoryOutcome, ...]) -> None

discovery_session(discovery_id: str) -> Versioned | None
begin_discovery(discovery_id: str, frozen: dict[str, object], context: RunContext,
                mode: str, acquisition_mode: str) -> Versioned
directory_gap(url: str) -> str | None
finish_discovery(discovery_id: str, workset_id: str, context: RunContext) -> None
```

Keyword-only record_directory proof fields and the checkpoint helpers were explicitly accepted by the controller as the minimum producing state scope. Successful record_directory requires evidence containing its actual listing SHA; discovery supplies durable body/receipt references, hashes and lengths plus selection metadata. Exact member IDs and immediate listing parents are checked. There is no new resource/table: DirectoryProgress, DiscoverySession and DiscoveryBoundary route through existing SourceState; immutable directory-failure audit rows use existing Failure/Attempts with actual attempt key/context, original structured outcome and distinct event generation.

The new offline support builders return ResponseSpec: `listing_response(period: str, names: list[str], *, family: str = 'daily-index') -> ResponseSpec`, `failed_response(status: int) -> ResponseSpec`; `discovery_harness(root: Path | None, responses: dict[str,list[ResponseSpec]]) -> DiscoveryHarness`. Harness has run(mode,today,discovery_id,*,refresh=False), seed_boundary(day), run_single_directory(period), boundary, attempted_urls, requested_quarters, add_pending(source), workset_path(workset) and idempotent close. It uses real acquisition stores, RequestClient and Coordinator; its ScriptedSender subclass owns no scheduling state. Synthetic ancestors advertise fixture years 2010 through2027 and actual QTR children; this is fixture construction, never a recovery/coverage claim. Historical day overrides are explicitly fixture-labelled, with open endpoint configurations for daily tests.

## Durable paths, generations and provenance

Source workset bytes are now `worksets/sec/source/sha256=<workset_id>/workset.json` (corrected in review fix round 1 below). Accepted listing bytes are `worksets/discovery/listings/sha256=<actual-original-hash>/listing.body`; receipt objects are `worksets/discovery/listings/receipts/sha256=<metadata-hash>.json`. Metadata includes the original BodyReceipt, actual transport RunContext and durable body_path. Failure originals and receipts use analogous `quarantine/discovery/` paths. Receipt temporary_path remains original audit information; cache verification reads the durable body_path and requires matching receipt URL/status/completeness/hash/count, actual requested directory URL/period, selection and immediate members. Restart works after the original sender spool has been removed. Corrupt supporting bytes or cached directory metadata fail closed before reuse.

A DiscoverySession keyed by hashed discovery_id freezes original context, actual today, exact endpoint, config/version provenance, mode, refresh acquisition_mode, overlap and required directory inventory. A resume admits a new execution/attempt under the same immutable run/config/image/parser/schema and command provenance. The source workset retains original command/context identity. A new discovery ID performs fresh reads; a successfully cached listing in the same ID remains frozen. Newly delayed files need a fresh ID. A retry that resolves failed inventory emits new immutable bytes/ID, preserving all earlier bytes. finish_discovery exact-CAS-checkpoints workset_id, predecessor_workset_id and append-only history containing the actual resumed_by context; hashes/models do not gain mutable provenance fields.

The one global DiscoveryBoundary row holds only day and current unresolved gaps. Completed session inventories/history remain per session, so the global row does not accumulate every successful discovery. Initial required gaps are registered by exact CAS before requests; the session registration acknowledgment is separately persisted and crash-replayable. This does not assume a cross-object/table transaction.

A fresh read captures its exact gap generation before HTTP. Failed reads publish a distinct immutable failure event/gap generation before their failed progress. Successful evidence and progress are durable before resolving that exact observed generation. On a crash after progress but before resolution, verified cached progress replays only its recorded generation; it cannot remove a newer failure on the same URL. Unrelated gaps are never cleared. Boundary advance validates the exact complete frozen required-unit set against durable DirectoryProgress, requires the pinned run day, checks every outcome and every global gap, then updates with the actual store version. CAS loops are bounded by existing CAS_ATTEMPTS=5. A concurrently inserted older gap invalidates the stale CAS and remains visible on retry. No wildcard/version fabrication or assumed transaction is used.

Daily units include open/preceding quarters, every quarter from handoff/contiguous boundary through the pinned day, all paginated pending source periods and all unresolved units. Pending quarterly sources also cause their actual full-index quarter listings to be visited. Failed old root/year units are included even without pending sources. Boundary means successful required directory discovery through the pinned day, never filing coverage or collection completeness. Source absence does not erase pending acquisition, accepted snapshots or existing bindings.

## Context resolution and deviations

The initial NEEDS_CONTEXT pin collision was real and is retained in task-6-pin-collision.txt: a common closed 2015Q1 config pins2015Q1, rejects a valid 2026 daily member, and rejects inventing a2026Q4 endpoint. The controller explicitly resumed Task 6 using the reviewed pin/hash contract and valid open configurations. The distinct Task 8 example/config owner question remains outside this task; no Task 8 correction was made.

A later actual behavioral RED showed an empty daily listing set could otherwise advance while its exact endpoint excluded today's quarter (because the existing workset validator only checks member quarters). Discovery now rejects a NEW daily session with that excluded current endpoint before attempts/HTTP, without changing pin_context or any hash rules. Valid frozen resumes retain their initial day/end even when the supplied new transport day changes. Static endpoints equal to the current quarter still satisfy exact pinning. This is discovery validation, not a contract override.

The SourceWorkset acquisition_mode/default/codec already existed in reviewed Task2, so discover passes the existing maker keyword. No duplicate model extension was needed. All other changes stay within named discovery files/fixtures, minimum support additions and expressly authorized state methods.

## TDD commands and retained output

All focused commands use the frozen offline prefix below and the appropriate test pattern:

```bash
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_discovery.py' -v
```

RED evidence retained before the corresponding changes:

- task-6-red-initial.txt: initial 17 tests; missing module/API,13 feature-absence assertion failures/four import errors, exit1. This first log is interface absence, not claimed behavioral proof.
- task-6-first-iteration.txt: initial traversal integration revealed 11 errors, including stale outage candidate handling and missing explicit clock labels in the provisional helper.
- task-6-red-recovery-boundary.txt:24 tests, two actual assertion failures (unbacked future candidate accepted; durable successful progress crash could not finish its gap resolution) and two outage errors, exit1. task-6-green-recovery-boundary.txt then24/24 exit0.
- task-6-red-unresolved-and-open-bridge.txt:32 tests, three actual failures (historical bridge wrongly registered; failed old year omitted; completed sessions grew shared row from 322 to 2275 bytes), exit1. task-6-green-unresolved-and-open-bridge.txt then32/32 exit0.
- task-6-red-daily-endpoint.txt and task-6-red-receipt-observation.txt: empty excluded daily endpoint accepted; cached period tampering accepted; observation command-start timestamp differed from the exact received_at. The latter log 39 tests/four assertion failures, exit1. Partial-body replay also showed a synthetic helper erroneously consumed a200 fault once and exhausted its sequence; only that helper replay rule changed, not RequestClient.
- task-6-red-root-codec-reason.txt exposed missing root codec metadata; task-6-red-root-codec-assertion.txt restated it as a precise assertion (40 tests, one failure), before the root omission reason fix.

Final focused GREEN: task-6-green-discovery.txt **40/40 in6.433s, exit0/pristine**. Prescribed covering patterns/outputs are task-6-green-config.txt **12/12**, task-6-green-urls.txt **4/4**, task-6-green-worksets.txt **16/16**, task-6-green-state.txt **11/11**, all exit0/pristine. Focused commands replace only the discovery pattern with the named module pattern.

Final full command, run once after the final source/test change:

```bash
SEC_EDGAR_TASK4_TRACE_DIR=.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-6-full-evidence/coordination SEC_EDGAR_TASK5_TRACE_DIR=.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-6-full-evidence uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

Actual full output in task-6-full-tests.txt: **215/215 in19.767s, exit0/pristine**. Existing bounded loopback sender/socket and coordination traces are retained under task-6-full-evidence. No source or test changed between this original full verification and the original commit; review fix round 1 has its current verification below. No SEC/Azure/live request was made; Azure checks use existing mocked adapters.

## Retained proof and self-review

Before first decoding, independently rehashed all 14 exact named retained listing bodies (`SEC-0001/0002/0003/0028/0085/0086/0087/0088/0089/0104/0135/0137/0138/0139`) and their 28 original header/intent sidecars against the committed 83-record retained-manifest.json, plus both immutable provenance hashes. The committed tests repeat hash/length checks before decode and compare original intent/header URL/provenance; all 14 parse and preserve actual size/time labels. A full retained SEC-0001/0002/0003 root/year/quarter traversal selects the exact actual 2010Q1 ZIP child and preserves each original listing hash. Five separately labelled synthetic JSON fixtures cover empty, malformed, unsafe, leap-day and delayed daily bodies. Tests use no ignored SDD metadata. Final suite's retained-envelope test independently covers all 83 accepted records and both immutable provenance objects. Accepted F1 SHA 939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff and accepted manifest SHA 124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131 remain unchanged.

Self-review checked brief Steps1-4, immediate parent trust, failed-vs-empty semantics, rollover/leap dates, original-byte durability before progress, exact-source membership, immutable retry/predecessor history, same-session and new-session behavior, policy latch/denial, one budget, pending pagination, failed ancestor recovery and CAS interleavings. Actual REDs drove the fixes above. Discovery responsibilities remain in the mandated module; the already broad state.py gained only its producing methods, without unrelated restructuring.

Clean-code applications are limited to new/in-scope code: descriptive side-effect names `_persist_receipt`, `record_directory`, `finish_discovery` (N1/N7); cohesive parsing/selection/persistence/cache responsibilities (G30/G34); named QUARTERS_PER_YEAR/MONTHS_PER_QUARTER and existing HTTP_OK (G25); retained intent comments about gap accounting, metadata and separate durability boundaries (C3/C4); focused outage/calendar/crash/corruption/concurrency neighbors (T1/T5/T6). No adjacent cleanup was applied or bundled.

## Files and limits

Exactly nine owned production/test/fixture paths are intended for this commit:

- packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py
- packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py
- packages/sec-edgar-ingest/tests/test_discovery.py
- packages/sec-edgar-ingest/tests/support.py
- packages/sec-edgar-ingest/tests/fixtures/listings/empty.json
- packages/sec-edgar-ingest/tests/fixtures/listings/malformed.json
- packages/sec-edgar-ingest/tests/fixtures/listings/unsafe.json
- packages/sec-edgar-ingest/tests/fixtures/listings/leap-day.json
- packages/sec-edgar-ingest/tests/fixtures/listings/late-daily.json

Ignored SDD reports/logs/traces remain evidence on disk, never incidental commit content. Original four unstaged index-ingest deletions, primary checkout, local/untracked roadmap, scaffolds, parent/ADR/F1/manifest and every raw receipt/body remain preserved. No restore/stash/reset/blanket staging occurred.

No known failing test or unresolved Task 6 implementation question remains. Fresh Spec/Quality review is still the controller's gate. Same-session successful listings are immutable; newly advertised files/children require a new discovery ID. A complete frozen inventory can coexist with another discovery's later unrelated gap; global CAS prevents that gap from allowing a boundary advance. Storage/API/payload/capacity failures remain explicit failures; no recovery horizon, global format coverage, capacity, filing coverage, collection completion or complete workflow claim follows from these offline tests. All later-stage boundaries remain intact.

## Commit receipt

Committed exactly the nine named paths as `c51fe3b3350d71195ed94880359304ab3634aca9` (`feat: discover durable source worksets without hiding gaps`). Final BASE-to-HEAD whitespace validation passed with exit 0; the index is empty. Post-commit status contains only the original four unstaged index-ingest deletions. Exact command/output receipts are retained in task-6-scope-and-commit.txt. This receipt records the original commit before review fix round 1; current post-fix checks follow below. Fresh controller review remains pending.

## Review fix round 1

Read and adopted both Important findings in task-6-review.md against original commit `c51fe3b3350d71195ed94880359304ab3634aca9`. Fixed only discovery.py, test_discovery.py and the discovery harness workset_path line in support.py. No state.py, model, hash, config, pinning, transport or later-stage implementation changed. Fresh controller re-review remains pending.

Source worksets now publish the same canonical immutable bytes at `worksets/sec/source/sha256=<workset_id>/workset.json`. An independent test spells out that approved path without the harness helper, recalculates the canonical payload digest excluding workset_id, checks the path ID and strictly decodes the exact stored bytes. Existing delayed/restarted workset tests now read this approved path, preserving predecessor bytes and IDs.

New private `_verify_receipt_context(value: object, frozen_context: RunContext) -> None` strictly decodes persisted transport RunContext, validates its embedded effective config with existing Settings.from_mapping and validates its own actual pinned_on with existing pin_context. Missing config/pin, invalid record shape/schema, and an endpoint preceding configured start fail as Conflict. Immutable run_id/command/config_sha256/image_digest/parser_version/schema_version and exact effective config must match the frozen session. Execution_id, attempt_id and legitimate transport pin-date differences remain valid. `_reopen_listing(objects: ObjectStore, value: dict, unit: dict, frozen_context: RunContext)` receives that original frozen context and verifies receipt provenance before replaying successful progress or resolving a gap. Public discovery/state APIs and frozen workset context/endpoint are unchanged.

The negative regression recomputes receipt metadata hash/path/length and replaces actual DirectoryProgress with its current version, so byte integrity passes while false provenance is still rejected before any new request. It covers ten conflicting/invalid contexts. A positive real-store regression first leaves a failed leaf, retries it on a new execution/attempt and pin date, then successfully reopens those actual resumed receipts without HTTP or original workset context changes.

Exact focused commands (all frozen/offline) were:

```bash
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_discovery.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_config.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_urls.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_worksets.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_state.py' -v
```

Retained exact output under this report's directory:

| Evidence | Actual result |
| --- | --- |
| task-6-fix-1-red.txt | 43 tests in 8.353s; 11 assertion failures (approved path absent and ten cached context cases accepted); exit 1, before any production change |
| task-6-fix-1-green-discovery.txt | 43 tests in 8.033s; OK, exit 0 |
| task-6-fix-1-green-config.txt | 12 tests in 0.214s; OK, exit 0 |
| task-6-fix-1-green-urls.txt | 4 tests in 0.002s; OK, exit 0 |
| task-6-fix-1-green-worksets.txt | 16 tests in 0.150s; OK, exit 0 |
| task-6-fix-1-green-state.txt | 11 tests in 0.228s; OK, exit 0 |

Every GREEN output was read and contained no warnings/errors. The initial 215-test full run above is historical pre-review evidence; this minimal discovery-only fix received all prescribed covering checks, and shared producing state did not change. Self-review verified approved durable path/digest/codec identity, strict cached context provenance and config/pin validation, legitimate actual resumed transport, frozen context/endpoint preservation, scoped diff and whitespace. No source or test changed after these GREEN checks. No live/network/registry/auth work occurred. No Task 6 implementation question remains; fresh re-review and the separate Task 8 owner fixture-endpoint decision remain the controller's gates. Fix commit: `4cbc9d8afcc793aa8d8402321019807e5ea3e526` (`fix: enforce discovery workset paths and receipt provenance`). Scope/commit/whitespace command receipts are retained in task-6-fix-1-scope-and-commit.txt. Exactly three owned paths were committed; post-commit index is empty and status contains only the original four unstaged index-ingest deletions. All post-commit verification commands returned exit 0. Fresh controller re-review is pending.
