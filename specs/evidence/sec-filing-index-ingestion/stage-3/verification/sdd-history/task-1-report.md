# Task 1 report: versioned ETL contracts and accepted storage boundaries

Status: DONE

Commit: `966bd9e6bc8d5ce3803c0db7e95a4011e94e2ee9` (`feat: add versioned ETL and publication storage contracts`). Base: `8bb17c1277544ee46a1d351982d9e3e9c6e0d122`.

Worktree: `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`, branch `codex/sec-edgar-stage-3`. The primary checkout was never modified. No subagents were dispatched. All activity was offline; live SEC/Azure/authentication/compute/provisioning/deployment authorizations remain closed. Native checks are not Stage 7 Linux worker capacity evidence; `all22_stage7_checks: reserved`.

## Outcome and implementation

Added the exact Task 1 immutable records, explicit canonical/observation/change Arrow schemas, processing identity and observation paths, strict versioned transformed-workset codec, ETL state facade, accepted logical Blob routing and exclusive streamed materialization. Added optional keyword-only ActivePointers client while retaining two-client construction and factory's three-object return. Pointer insert/replace propagates actual CAS conflicts. Publication indexes accumulate per-quarter/per-generation memberships through bounded CAS without altering acquisition Source rows. Accepted transforms and candidates reject changed immutable payloads. Publication receipts verify the accepted transform before creating their index.

The observation schema is flat canonical columns plus `original_fields: fixed_size_list<item: string not null>[5] not null` and `line_number: int64 not null`. Canonical filing date is date32; accession is the sole nullable canonical column. Change before/after are nullable full canonical structs; reason is nullable string; change_type/cik/archive_path are non-null strings.

The transformed envelope format is `sec-transformed-workset-v1`. Its ID hashes canonical envelope payload excluding only workset_id; encoding and decoding verify identity, canonical byte spelling, version and exact fields. Run contexts remain separate original acquisition and current transformation records. `quarter_counts` counts retained observation rows including identical duplicates and sums to source_row_count; distinct_key_count stays separate. CIK uses the parser's prescribed ten-digit zero-padding. Unrecognized safe legacy paths are retained with null accession; recognized numeric path CIK disagreement is refused.

Closed quarters can retain daily-only conservative additions/updates without a membership source. Withdrawals or withdrawal approval gates require selected quarterly membership authority. The controller confirmed these semantics during implementation. Publication memberships keep all committed generation receipts, avoiding older repair overwriting a newer membership.

## Verification and evidence

Evidence directory: `.sdd/3-sec-filing-index-ingestion-stage-3-spec/task1-evidence` (ignored task workspace; retained intentionally). Each numbered command has exact argv, cwd and exit in `.command.json`, plus complete separate `.stdout.txt` and `.stderr.txt`. Failed and intermediate attempts remain under distinct names. `23-final-owned.diff` contains the full staged source/test/dependency patch, including newly created files. `25-postcommit-status` confirms a clean checkout after the explicit commit.

- 01-red: initial guarded discovery, exit 1, expected missing sec_edgar_ingest.etl and blob_address.
- 02-lock: `uv lock --offline`, exit 0, added only pyarrow 25.0.1; original lock retained as 02-lock-before.toml.
- 03-sync: `uv sync --offline --frozen --package sec-edgar-ingest`, exit 0.
- 04-import: prescribed `uv run --offline --frozen --package sec-edgar-ingest python -c 'import pyarrow, pyarrow.parquet; assert pyarrow.__version__ == "25.0.1"; print(pyarrow.__version__)'`, exit 0, printed 25.0.1.
- 05-signatures: installed public Arrow schema/ParquetWriter/iter_batches and Blob download/chunks/upload and Table create/update signatures, exit 0. No credentials constructed.
- 06-expanded-red and 07-records-red: guarded contract/storage RED before implementation, exit 1 for missing interfaces.
- 08-initial-green-attempt: 14 tests, exit 1 for the test's registry locator (`binding.json`, not a registry-named file).
- 09-covering-green-attempt: 73 tests, exit 1 for test-only issues: the URL assertion needed the SDK's percent-encoded equals sign, and the factory assertion needed its returned state assigned.
- 10-semantics-red: two controller-confirmed contract corrections reproduced, exit 1.
- 11-covering-green: 75 tests, exit 0.
- 12-parser-alignment-red: padded CIK/legacy-path contract reproduced, exit 1.
- 13-boundaries-red: missing ActivePointers performed large-content upload before refusal; scratch close failure left scratch. Both reproduced, exit 1.
- 14-boundaries-green: 78 tests, exit 0.
- 15-receipt-order-red: accepted-transform conflict left a receipt before raising; reproduced, exit 1. Bounded CAS and monotonic membership test already passed.
- 16-final-covering-green: final six required suites, **80 tests, exit 0**, `OK` (0.527 seconds test runtime).
- 17-pin-signature-proof: all 22 prior package versions unchanged, only pyarrow 25.0.1 added; all produced signatures inspected, exit 0.
- 18-diff-check and 22-staged-diff: exit 0. 21-owned-add and 24-commit: exit 0. Exact staged filename set was asserted equal to the Task 1 allowlist before commit.

The final guarded test invocation was:

```sh
uv run --offline --frozen --package sec-edgar-ingest python -c "import sys; sys.path.insert(0, 'packages/sec-edgar-ingest/tests'); import network_guard; network_guard.main(['test_etl_contracts', 'test_etl_storage', 'test_worksets', 'test_storage', 'test_azure_contracts', 'test_azure_state_payloads', '-v'])"
```

Every test invocation installed existing network_guard before test imports. The full 302-test baseline was not rerun; it belongs to the controller's baseline and Task 7 final check. Source code was not changed after final GREEN.

Native platform: macOS 26.6.2 arm64, CPython 3.14.0, PyArrow 25.0.1. This is explicitly separate from accepted retained Stage 1 Linux evidence and reserved Stage 7 Linux amd64/Python 3.14.8 worker measurements. No codec fallback, pin relaxation, package fetch, image build, schedule activation, or client authentication occurred.

## Immutable compatibility and SDK wire evidence

The Stage 2 completion receipt identified `specs/evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-46bhxh8j`. All four existing worksets were decoded and re-encoded to identical original bytes; each embedded Settings mapping and config hash was preserved. Their byte hashes and lengths are emitted in final GREEN stdout:

- snapshot aee51809276870393e90d9ede0399baacfe2f96798a6ae9c2ed26c4aba01bb98: 68ecdcd9c4f1034b7d81ac989d9edbcfafde46f72397028c8850a8b0e560ee03, 4579 bytes.
- snapshot b6388dacb7dd1743eeb58d05c4dff7a4cdef255ac5c24ceefd96542a06efaec5: 9e1706ceb0f9148b7674c2a973fdcd82b7def738b501a6ce177b001e20afbe95, 3704 bytes.
- source 2d51330ddb11231aa5331f83a835b647913f79b3e902f04620b9493781f2622c: 3ebc1529bd24507416f5866825752e7c59778efe25dafd2ace6c4e0c7538a00f, 3885 bytes.
- source f9885e59487ca8fc3adb228658c4829f7c4bf39e668b477527e2dd5c7132ea4d: f40f6275b5bd04ce86929143abfa392185698fc6c977575e13beea8e7754bf45, 3325 bytes.

Registry binding.json reconstructs identically: SHA256 14ea024fdafb0377c529edcdda6431bf5d7332caf321ba669b808efc31161d56, 937 bytes. Settings/model/workset implementations and retained receipt files were untouched.

Real pinned SDK fake transports emitted mapped PUT/GET URLs for results/runs, manifests/curated, generations/observations and raw/staging, plus create-only If-None-Match `*`. Actual ActivePointers POST and conditional PUT used observed `W/"first"`; 412 propagated Conflict. A 71,822-byte logical record used the existing content-first descriptor under worksets/state, verified content before ActivePointers insertion, and round-tripped with actual `W/"service-1"`. No real endpoints were contacted. Full paths/descriptors/ETags appear in final GREEN stdout.

## Exact produced signatures

```text
canonical_schema () -> 'pa.Schema'
observation_schema () -> 'pa.Schema'
change_schema () -> 'pa.Schema'
processing_key (source_id: 'str', snapshot_sha256: 'str', parser_version: 'str', schema_version: 'str') -> 'str'
observation_base (source_id: 'str', snapshot_sha256: 'str', parser_version: 'str', schema_version: 'str') -> 'str'
encode_transformed (workset: 'TransformedWorkset') -> 'bytes'
decode_transformed (body: 'bytes') -> 'TransformedWorkset'
transformed_ref (workset: 'TransformedWorkset') -> 'str'
IndexRow (cik: 'str', company_name: 'str', form_type: 'str', archive_path: 'str', filing_date: 'date', accession_number: 'str | None', source_id: 'str', source_sha256: 'str', parser_version: 'str', schema_version: 'str') -> None
Observation (row: 'IndexRow', original_fields: 'tuple[str, str, str, str, str]', line_number: 'int') -> None
ObservationRef (source: 'Source', snapshot: 'Snapshot', parser_version: 'str', schema_version: 'str', rows_ref: 'str', manifest_ref: 'str', rows_sha256: 'str', rows_bytes: 'int', source_row_count: 'int', distinct_key_count: 'int', quarter_counts: 'Mapping[str, int]') -> None
TransformedWorkset (workset_id: 'str', snapshot_workset_ref: 'str', origin_context: 'RunContext', context: 'RunContext', observations: 'tuple[ObservationRef, ...]', failures: 'tuple[Error, ...]', complete: 'bool') -> None
FileRef (path: 'str', sha256: 'str', byte_count: 'int', row_count: 'int', role: "Literal['data', 'changes']") -> None
GenerationManifest (quarter: 'str', generation_id: 'str', base_generation_id: 'str | None', source_fingerprint: 'str', parser_version: 'str', schema_version: 'str', image_digest: 'str', sources: 'tuple[ObservationRef, ...]', files: 'tuple[FileRef, ...]', row_count: 'int', added: 'int', updated: 'int', withdrawn: 'int', unresolved_absence: 'int', provenance_refreshed: 'int', quarter_mode: "Literal['open', 'closed']", membership_source: 'ObservationRef | None', retained_from_generation: 'str | None', gate: "Literal['clear', 'awaiting_approval']", format_version: 'str' = 'sec-generation-v1') -> None
Candidate (manifest: 'GenerationManifest', manifest_ref: 'str', manifest_sha256: 'str', manifest_bytes: 'int', candidate_ref: 'str | None') -> None
PublicationResult (quarter: 'str', outcome: 'str', generation_id: 'str | None', manifest_ref: 'str | None', candidate_ref: 'str | None', conflicts: 'int') -> None
GenerationCapture (quarter: 'str', generation_id: 'str', manifest_ref: 'str', manifest_sha256: 'str', manifest_bytes: 'int') -> None
EtlResult (context: 'RunContext', outcome: 'str', input_ref: 'str', transformed_workset_ref: 'str | None', transformed: 'int', published: 'int', unchanged: 'int', quarantined: 'int', awaiting_approval: 'int', failed: 'int', quarters: 'tuple[PublicationResult, ...]', gaps: 'tuple[Error, ...]', started_at: 'datetime', ended_at: 'datetime', format_version: 'str' = 'sec-etl-result-v1') -> None
blob_address (path: 'str') -> 'tuple[str, str]'
ObjectStore.materialize (self, path: 'str', target: 'Path') -> 'None'
LocalObjectStore.materialize (self, path: 'str', target: 'Path') -> 'None'
AzureObjectStore.materialize (self, path: 'str', target: 'Path') -> 'None'
AzureStateStore (source_client: 'TableClient', attempt_client: 'TableClient', *, objects: 'ObjectStore | None' = None, observer: 'BoundaryObserver | None' = None, active_client: 'TableClient | None' = None)
open_azure_stores (settings: 'Settings', *, observer: 'BoundaryObserver | None' = None)
EtlState (store: 'StateStore')
EtlState.processing (self, ref: 'ObservationRef') -> 'Versioned | None'
EtlState.accept_transform (self, ref: 'ObservationRef') -> 'None'
EtlState.pointer (self, quarter: 'str') -> 'Versioned | None'
EtlState.commit_pointer (self, quarter: 'str', value: 'dict[str, object]', previous: 'Versioned | None') -> 'Versioned'
EtlState.record_candidate (self, candidate: 'Candidate') -> 'None'
EtlState.record_publication (self, manifest: 'GenerationManifest') -> 'None'
```

## Owned files and self-review

Only these 12 approved files are committed:

```text
packages/sec-edgar-ingest/pyproject.toml
packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/__init__.py
packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py
packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py
packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py
packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py
packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py
packages/sec-edgar-ingest/tests/test_azure_contracts.py
packages/sec-edgar-ingest/tests/test_etl_contracts.py
packages/sec-edgar-ingest/tests/test_etl_storage.py
pyproject.toml
uv.lock
```

Self-review checked exact file scope, all pre-existing pins, default Settings bytes, immutable registry bytes, deep frozen mapping behavior, duplicate/unknown/canonical JSON refusal, Arrow nullability, raw-only promotion preservation, no wildcard pointer replace, no swallowed pointer conflicts, optional-client fail-before-write, created-scratch cleanup, content-first overflow behavior and bounded ancillary CAS.

Clean-code applications: N1/N4 name processing/receipt identities and pointer fields explicitly; G25 names ORIGINAL_FIELD_COUNT/format identifiers/POINTER_FIELDS and reuses CAS_ATTEMPTS/FILE_CHUNK_BYTES; G30 keeps record/codecs and state/storage boundaries cohesive; T1/T5/T6 add identity, duplicate, legacy, stream-failure, conflict-ordering and old-byte boundary coverage. No adjacent cleanups or unrelated files were changed.

## Deviations and concerns

No unresolved implementation concerns. Initial contract tests preceded the dependency gate; broader contract tests were then expanded before production. Additional inherited-SDK/regression coverage and the controller's semantic corrections were added during self-review, with separately retained reproduction evidence for behavioral fixes. The task report and evidence remain in ignored .sdd as requested; the controller owns durable downstream evidence packaging and fresh Spec/Quality review. Task 5 may extend the facade for reader/repair operations within its ownership. Task 7 retains the final full-suite/installed-wheel obligation.
