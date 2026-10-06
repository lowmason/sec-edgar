# Task 2 implementation report

Status: DONE (implementation complete; controller's fresh Spec/Quality review is pending).

Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`.
BASE: `046f240f655b1c1398e56ff57f2cac850b9d9a5c`.

Commits:

- `2fb97222660db59beb2144dbb1f33f4d82f15662` - `feat: define validated acquisition and workset contracts`.
- `1d1bd25237861eae40812e4b8b50fe567a6daaa1` - `refactor: name acquisition settings policy bounds`.

## Implemented behavior

Validated configuration v1 with nested frozen typed settings, exact accepted SEC owner identity, shared account/namespace/sentinel binding, selected Blob/Table API versions, required explicit Azure endpoints/container/object bindings, immutable version/digest provenance, finite positive HTTP/lease/guard bounds and strict retry/withdrawal limits. All validation is pure; `load_config` reads its selected file and initializes no state/client/credential/transport. General YAML, duplicate JSON keys, nonfinite numbers, unsafe relative output paths, foreign/credential-bearing endpoints, unsupported schemas, missing provenance and unknown fields fail before external factory use. Azure rejects synthetic/all-zero image provenance, fixture parser markers and fixture-only lower guard/deadline/clock overrides. Tests patch the actual installed credential/client/transport constructors and assert no calls on invalid configuration.

All 14 named cross-task records have complete strict `from_mapping` / detached `to_mapping` conversion, frozen dataclass fields and deeply immutable mappings/tuples. Native constructors also reject wrong typed nested records. `Versioned.value` and `BodyReceipt.headers` are read-only Mapping types rather than mutable dict annotations; their serializers return ordinary detached dictionaries. Snapshot paths are safe relative content addresses containing their exact source/hash, with selected representation and envelope metadata. UTC timestamps, nonnegative counts, opaque ETags, finite permit windows and queue lifetimes are validated.

URLs use urlsplit and exact HTTPS SEC origin/hierarchy checks, selected quarterly ZIP/daily IDX forms, calendar/quarter consistency, decoded dot/parent/separator/control rejection and case-sensitive paths. `child_url` accepts immediate name/href-agreeing children; retained listing forms name/ and name are supported. Foreign absolute URLs, escapes, parent metadata, nested or conflicting children and filing-content paths fail.

Source/snapshot codecs use canonical UTF-8 JSON, sec-acquisition-v1, explicit source/snapshot type metadata and SHA-256 over every field except workset_id. Effective configuration/provenance, endpoint, acquisition mode and directory outcomes all participate. Duplicate sources/directories, wrong/tampered IDs, unknown fields/versions, missing snapshot members and incomplete discoveries fail. Successful empty discovery with directory evidence is valid; failed empty discovery remains incomplete. Snapshot worksets copy exact source context, endpoint, directories, overlap and mode.

The checked-in YAML-named file intentionally contains strict JSON syntax and explicit local-fixture values; no real Azure principal/image/endpoint configuration was invented. README explains syntax, fixture overrides, accepted default schedules/guards and later-stage responsibilities. `.fixture-state/` is ignored. Loading settings creates no directory.

## Actual public interfaces for subsequent tasks

Required signatures are preserved:

```python
Settings.from_mapping(value: dict[str, object]) -> Settings
Settings.to_mapping() -> dict[str, object]
Settings.config_sha256  # read-only derived SHA-256 property of full effective to_mapping()
load_config(path: Path) -> Settings
pin_context(settings: Settings, context: RunContext, today: date) -> tuple[RunContext, str]
canonical_source_url(url: str, kind: str) -> str
canonical_listing_url(url: str) -> str
child_url(parent: str, href: str, name: str, is_directory: bool) -> str
source_id(url: str) -> str
canonical_json(value: object) -> bytes
workset_digest(payload: dict[str, object]) -> str
encode_workset(workset: SourceWorkset | SnapshotWorkset) -> bytes
decode_source_workset(body: bytes) -> SourceWorkset
decode_snapshot_workset(body: bytes) -> SnapshotWorkset
make_source_workset(context: RunContext, end_quarter: str, discovery_id: str,
                    members: tuple[Source, ...], directories: tuple[DirectoryOutcome, ...],
                    overlap_from: date) -> SourceWorkset
make_snapshot_workset(source: SourceWorkset, snapshots: tuple[Snapshot, ...]) -> SnapshotWorkset
fixture_settings(**overrides: object) -> Settings
fixture_context(command: str = 'collect', priority: str = 'backfill') -> RunContext
fixture_source(period: str = '2015Q1', kind: str = 'quarterly') -> Source
fixture_workset(members: tuple[Source, ...], discovery_complete: bool = True) -> SourceWorkset
```

`canonical_json` is defined in models and re-exported by worksets. All records expose `from_mapping`/`to_mapping`; strict record decoders require every serialized field, including serialized defaults.

Settings fields and exact typed section names:

- `config_version: str`; `backfill: BackfillSettings(start_quarter: str, end_quarter: str)`; `daily: DailySettings(start_date: date)`.
- `sec: SecSettings(user_agent: str, requests_per_second: float, max_active_collectors: int)`.
- `http: HttpSettings(max_attempts: int, retry_base_seconds: float, retry_cap_seconds: float, connect_timeout_seconds: float, read_timeout_seconds: float, exchange_deadline_seconds: float, max_received_bytes: int, max_expanded_bytes: int)`.
- `coordination: CoordinationSettings(lease_seconds: float, renew_every_seconds: float, namespace: str, clock_uncertainty_seconds: float)`.
- `storage: StorageSettings(backend: Literal['local-fixture','azure'], source_table: str, attempt_table: str, blob_api_version: str, table_api_version: str, root: str|None=None, account_name: str|None=None, blob_endpoint: str|None=None, table_endpoint: str|None=None, raw_container: str='raw', workset_container: str='worksets', quarantine_container: str='quarantine', lock_container: str='locks', lock_blob: str=LOCK_BLOB, binding_registry_blob: str=BINDING_REGISTRY_BLOB)`.
- `etl: EtlSettings(parser_version: str, schema_version: str)`; `worker: WorkerSettings(image_digest: str, provenance: str)`.
- `jobs: JobsSettings(replica_retry_limit: int)`; `orchestration: OrchestrationSettings(transient_replays: int)`; `reconciliation: ReconciliationSettings(require_withdrawal_approval: bool)`.
- `fixture: FixtureOverrides|None=None`; `FixtureOverrides(allow_clock_override: bool=False, allow_deadline_override: bool=False)`.

Public fixed binding constants in config:

```python
ACCOUNT_NAME = 'secedgardevb8617'
COORDINATION_NAMESPACE = 'sec-owner-lowell-mason'
LOCK_BLOB = 'sec-owner-lowell-mason/sentinel.json'
BINDING_REGISTRY_BLOB = 'sec-owner-lowell-mason/binding.json'
WORKER_ALLOWANCE_SECONDS = 3600
MAX_EXCHANGE_SECONDS = 90
MAX_RECEIVED_BYTES = 67108864
MAX_EXPANDED_BYTES = 536870912
```

The controller explicitly confirmed sentinel and registry object keys as fixed application details under container `locks`. Later storage work must conditionally persist/check this binding registry and fail closed on conflicts. Task 2 deliberately supplies validated settings with no storage I/O.

`RunContext` retains all specified fields, with additional `effective_config: Mapping[str,object]` defaulting to an empty immutable mapping until pinning. `pin_context` validates config SHA/image/parser/schema identity and finite deadline, then returns a copied context containing Settings.to_mapping() deeply frozen. Workset construction/decoding requires a nonempty pinned effective config and verifies its SHA and provenance. An ordinary pin date must match context.started_at.date(); explicitly labelled local-fixture clock override permits injected dates. A caller needing a different run quarter should construct its matching run-start UTC timestamp. Deadline must be after start and at most 3600 seconds; an explicitly labelled local-fixture deadline override alone can exceed this allowance.

`SourceWorkset` retains the specified fields; no separate config field duplicates context.effective_config. `SnapshotWorkset` adds `acquisition_mode: Literal['reuse_accepted','refresh']='reuse_accepted'` so mode remains explicit and hashed. `make_source_workset` selects refresh when `context.command == 'refresh'`, otherwise reuse_accepted. Both constructors sort members/directories and reject duplicates. DirectoryOutcome.source_ids are sorted. Source membership must match immediate successful directory outcomes exactly; complete snapshot membership must match those source IDs exactly. Future/unresolved endpoints are rejected relative to the run-start quarter.

Selected public constants in models, confirmed by the controller:

```python
FORMAT_VERSION = 'sec-acquisition-v1'
SCHEMA_VERSION = 'sec-index-v1'
QUARTERLY_ENVELOPE_VERSION = 'sec-quarterly-envelope-v1'
DAILY_ENVELOPE_VERSION = 'sec-daily-envelope-v1'
```

`Source.period` is YYYYQn for quarterly and YYYY-MM-DD for daily. Snapshot raw_path must be normalized POSIX-relative, include a source_id component and a hash component (exact SHA or SHA.zip/SHA.idx), and contain no latest component. Any zip/idx filename extension must agree with representation. BodyReceipt.status permits zero for no HTTP response or actual 100..599 status. These are data contracts; Task 5 still performs actual selected-body validation and Task 7 cross-checks stored immutable objects.

## TDD evidence and exact commands

Every evidence file starts with the full command and its exit code. All runs used:

```sh
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_config.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_urls.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_worksets.py' -v
```

1. Initial bootstrap RED before production files: `task2-evidence/red-config.txt` (8 assertion failures), `red-urls.txt` (4), `red-worksets.txt` (8). Tests failed explicitly at missing-contract assertions, not import errors. These alone establish only the missing-module gate.
2. Behavioral RED after minimal public records/codecs but before full boundary checks: `red-behavior-config.txt` (37 assertion failures), `red-behavior-urls.txt` (32), `red-behavior-worksets.txt` (10). All exit 1 with zero test errors. Representative failures: second collector accepted, credential/namespace/guard invalid values accepted, dangerous URLs accepted, missing snapshot members accepted and changed workset identity unchecked.
3. Initial focused GREEN: `green-initial-config.txt` (8/8), `green-initial-urls.txt` (4/4), `green-initial-worksets.txt` (8/8), exit 0.
4. Final named hardening RED: `red-hardening-config.txt` (11 methods; 1 failure for unlabelled fixture clock); `red-hardening-worksets.txt` originally had 6 failures and 1 error because wrong receipt type leaked AttributeError. The test was corrected to assert that the actual exception is ValueError, preserving the intended assertion and producing `red-hardening-worksets-corrected.txt` (11 methods; 7 failures, zero errors). Failures covered mutable wrong-typed nested records, unknown/mismatched envelopes and UTF-16 workset bytes. Both original and corrected observations remain retained honestly.
5. Final focused GREEN: `green-hardening-config.txt` (11/11), `green-hardening-urls.txt` (4/4), `green-hardening-worksets.txt` (11/11), all exit 0.
6. Full GREEN before feature commit: `green-full.txt` - 32/32, exit 0, pristine output.
7. Bounded pure tidy in a separate commit: named policy constants and removed one unused test import. Full GREEN after tidy: `green-full-refactor.txt` - same 32/32, exit 0, pristine output.

Full command for the last two runs:

```sh
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

Final check command: `git diff 046f240f655b1c1398e56ff57f2cac850b9d9a5c HEAD --check` - exit 0, no diagnostics. Exact changed paths/status retained in `task2-evidence/scope-and-diff-check.txt`. The 32 methods comprise 26 Task 2 methods and 6 unchanged Task 1 methods, with named subtests covering the specified matrix.

## Changed files and ownership

Exactly the Task 2 named creation paths were committed: config.py, models.py, urls.py, worksets.py under src/sec_edgar_ingest; tests/support.py, test_config.py, test_urls.py, test_worksets.py and tests/fixtures/config/local.json; conf/sec-edgar-ingest.yaml. The controller clarified that Task 2 Step 3's minimal package README and root .gitignore changes were in scope despite omission from the ownership table; those two files were also staged explicitly. No `git add .`/`-A`, reset, restore or stash was used. Report/evidence are local .sdd artifacts and were not added to a commit.

The four original packages/sec-edgar-index-ingest deletions are the only remaining git status entries and remain unstaged. Client/download files, dependency pins, roadmap, parent/plan documents and shared progress ledger were untouched.

## Self-review, quality and limitations

No remaining behavioral failures or known correctness concerns were found in the scoped self-review. All defined shared fields participate in strict detached conversion; immutable nested values and deepcopy are exercised. URL mutations are rejected before constructing a source, and codec mutations are rejected even when an attacker recomputes a nominal payload hash. A source content change, parser provenance/config change or listing content change changes workset identity. UTC, quarters, leap-day, deadline, empty-discovery and exact membership boundaries are covered. No SEC/Azure/auth/compute/registry access occurred; installed Azure imports are only patched offline factory assertions.

Clean-code applications: clear record/setting/source identity names and builder return types (N1/N4); pure settings versus file-loading/workset/URL responsibilities (G6/G30, N7); named acquisition policy bounds in the separate tidy commit (G25); exhaustive safety/temporal/empty/membership subtests (T1/T5/T6); removed one unused test import (F401). No adjacent cleanup or broader refactor was performed. Models is intentionally larger because it declares all 14 records plus the closed strict conversion grammar; no additional modules were invented.

Required follow-on responsibilities remain explicit: Task 3 persists/checks the registry and constructs storage clients only after validation; Task 5 validates the actual envelopes/guards; Task 7 verifies every referenced stored raw object and source-workset relation. A decoder cannot independently prove an external blob exists without storage access. These boundaries are not claims of Stage 7 acceptance, parsing, recovery horizon, deployment readiness or production coverage. The controller owns fresh review; this implementer did not spawn a reviewer or mark task/plan checkboxes.


## Fix round 1: three Important review findings

Status: DONE (corrections verified and committed; fresh scoped re-review remains the controller's gate).
Fix BASE: `1d1bd25237861eae40812e4b8b50fe567a6daaa1`.
Commit: `3085d6765f65529820743c2d86dca84a497c2060` - `fix: align snapshot paths mode and endpoint contracts`.

Read the receiving-code-review skill and verified all three findings against the implementation. The corrections below supersede the original report's invented raw-path component requirement, command-derived acquisition mode and run-start-only endpoint validation.

1. **Approved raw paths.** Snapshot now requires the approved exact grammar:
   `raw/sec/indexes/kind=quarterly/period=YYYYQn/sha256=<64-lowercase-hex>/master.zip` or
   `raw/sec/indexes/kind=daily/period=YYYY-MM-DD/sha256=<64-lowercase-hex>/master.idx`.
   The labelled path hash must match Snapshot.sha256; kind, calendar period, filename and representation must agree. Safe relative path checks remain. There is no invented source-ID or bare-hash path component; Snapshot.source_id carries source identity. The local snapshot test helper now uses the approved layout. Both selected representations round-trip through Snapshot mapping and snapshot workset codecs; unsafe paths, wrong hash/labels, invalid period/kind, latest and wrong filenames are rejected.
2. **Explicit mode.** The authorized compatible producer interface is now:

   ```python
   make_source_workset(context: RunContext, end_quarter: str, discovery_id: str,
                       members: tuple[Source, ...], directories: tuple[DirectoryOutcome, ...],
                       overlap_from: date, *,
                       acquisition_mode: Literal['reuse_accepted','refresh'] = 'reuse_accepted') -> SourceWorkset
   ```

   All six positional inputs remain unchanged. Mode is independent of context.command. Discovery passes acquisition_mode='refresh' for discover(refresh=True), leaving command='discover' intact. Mode remains in source identity and is copied into snapshot worksets. Regression coverage proves distinct source/snapshot IDs and exact round trips without changing command provenance; unsupported modes fail. The older test that rewrote command was corrected to pass the explicit mode.
3. **Exact endpoint and auditable pin date.** `RunContext` adds `pinned_on: date|None=None` after effective_config, preserving existing positional fields/default construction. `pin_context(settings, context, today)` keeps its signature and now returns the frozen copy with `pinned_on=today`, retaining started_at and deadline. Detached mapping serializes pinned_on as YYYY-MM-DD; the strict record codec requires the serialized field, and actual worksets require a non-null pin date. The source constructor and both workset decoders call pin_context with that retained date and require pinned_end_quarter to equal the exact returned endpoint, for both open and fixed config. Ordinary pin dates still match started_at.date(); labelled local-fixture clock overrides retain their actual date and still enforce exact resolution. A Q4 open run cannot accept a rehashed Q3 workset. A fixture pinned in Q3 cannot accept Q2 or Q4 merely because its run-start timestamp is in Q4. Context pin date participates in both identities and is copied into snapshot context.

### Retained RED/GREEN evidence

All evidence is under `task2-evidence/`; every log begins with its exact command and exit code. No outputs are repeated here.

| Finding/gate | RED evidence/result | GREEN evidence/result |
|---|---|---|
| Approved raw layout | `fix1-red-paths.txt`: 13 methods, 2 assertion failures, exit 1 | `fix1-green-paths.txt`: 13/13, exit 0 |
| Explicit discovery mode | `fix1-red-mode.txt`: 14 methods, 1 assertion failure, exit 1 | `fix1-green-mode.txt`: 14/14, exit 0 |
| Retained pin date | `fix1-red-endpoint-config.txt`: 12 methods, 1 assertion failure, exit 1 | `fix1-green-endpoint-config.txt`: 12/12, exit 0 |
| Exact endpoint, constructors/decoders/fixture | `fix1-red-endpoint-worksets.txt`: 16 methods, 4 assertion failures, exit 1 | `fix1-green-endpoint-worksets.txt`: 16/16, exit 0 |
| Full regression suite | — | `fix1-green-full.txt`: 38/38, exit 0, pristine output |
| Scope/diff check | — | `fix1-scope-and-diff-check.txt`: exact five paths, original four unstaged deletions retained; diff check exit 0 |

Exact commands used:

```sh
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_worksets.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_config.py' -v
uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
git diff 1d1bd25237861eae40812e4b8b50fe567a6daaa1 3085d6765f65529820743c2d86dca84a497c2060 --check
```

Each finding was resolved sequentially after its regression failed. Covering suites passed before moving to the next finding; final full suite contains 12 config, 4 URL, 16 workset and 6 unchanged Task 1 methods. Self-review checked the correction diff, exact producer compatibility, pin-date serialization/hash inclusion, both envelope paths and unchanged protected status. No known remaining correctness concerns in the three corrected findings. Clean-code applications: coherent snapshot address validation (G30), explicit producer semantics/provenance (N4), calendar/identity/mode regression boundaries (T5/T6). No unrelated tidying was performed.

Only owned config.py, models.py, worksets.py, test_config.py and test_worksets.py were staged explicitly. Report/logs remain local SDD artifacts. No plan, parent, shared ledger, README, dependency, roadmap or scaffold changes; no reset/stash/restore or broad staging. No live/network/auth/registry access occurred. The controller owns fresh scoped Spec/Quality re-review.
