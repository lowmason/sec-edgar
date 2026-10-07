## Interfaces and immutable contracts

Reuse existing `models.Record`, `canonical_json`, `parse_json`, `RunContext`, `Source`, `Snapshot`, `SnapshotWorkset`, `Versioned`, `Error`; `worksets.decode_source_workset/decode_snapshot_workset`; `StateStore.get/insert/replace/scan`; `ObjectStore.put_once/read/stage/verify`; `AcquisitionState.binding/begin_attempt`; existing real local CAS and mocked Azure ETags. Do not reuse raw-only `ObjectStore.promote` for observations.

Task 1 defines the following deeply immutable `Record` subclasses and strict codecs; round trips reject unknown fields, invalid types, duplicates, unsafe paths, invalid hashes, noncanonical JSON and unsupported format versions. Mapping values are frozen/detached using existing Record conventions. All timestamps are aware UTC. Canonical row mappings use ISO dates for JSON, PyArrow date32 for Parquet.

| New record | Exact fields |
|---|---|
| `IndexRow` | `cik, company_name, form_type, archive_path: str`; `filing_date: date`; `accession_number: str | None`; `source_id, source_sha256, parser_version, schema_version: str` |
| `Observation` | `row: IndexRow`; `original_fields: tuple[str,str,str,str,str]`; `line_number: int` |
| `ObservationRef` | `source: Source`; `snapshot: Snapshot`; `parser_version, schema_version, rows_ref, manifest_ref, rows_sha256: str`; `rows_bytes, source_row_count, distinct_key_count: int`; `quarter_counts: Mapping[str,int]` |
| `TransformedWorkset` | `workset_id, snapshot_workset_ref: str`; `origin_context, context: RunContext`; `observations: tuple[ObservationRef,...]`; `failures: tuple[Error,...]`; `complete: bool` |
| `FileRef` | `path, sha256: str`; `byte_count, row_count: int`; `role: Literal['data','changes']` |
| `GenerationManifest` | `format_version: str = 'sec-generation-v1'`; `quarter, generation_id: str`; `base_generation_id: str | None`; `source_fingerprint, parser_version, schema_version, image_digest: str`; `sources: tuple[ObservationRef,...]`; `files: tuple[FileRef,...]`; `row_count, added, updated, withdrawn, unresolved_absence, provenance_refreshed: int`; `quarter_mode: Literal['open','closed']`; `membership_source: ObservationRef | None`; `retained_from_generation: str | None`; `gate: Literal['clear','awaiting_approval']` |
| `Candidate` | `manifest: GenerationManifest`; `manifest_ref, manifest_sha256: str`; `manifest_bytes: int`; `candidate_ref: str | None` |
| `PublicationResult` | `quarter, outcome: str`; `generation_id, manifest_ref: str | None`; `candidate_ref: str | None`; `conflicts: int` |
| `GenerationCapture` | `quarter, generation_id, manifest_ref: str`; `manifest_sha256: str`; `manifest_bytes: int` |
| `EtlResult` | `format_version: str = 'sec-etl-result-v1'`; `context: RunContext`; `outcome: str`; `input_ref: str`; `transformed_workset_ref: str | None`; `transformed, published, unchanged, quarantined, awaiting_approval, failed: int`; `quarters: tuple[PublicationResult,...]`; `gaps: tuple[Error,...]`; `started_at, ended_at: datetime` |

Processing keys hash canonical `[source_id, snapshot_sha256, parser_version, schema_version]`. Per-quarter receipt keys hash `[processing_key, quarter, generation_id]`. Transformed-workset IDs hash canonical payload excluding workset_id; full byte SHA is independent. A partial transformed workset retains successful member refs and failures, is immutable, and is not a publishable complete-input workset. A retry produces a new complete workset when failures resolve; it reuses accepted successful processing outputs.

Generation identity hashes canonical `{quarter, base_generation_id, source_fingerprint}`; fingerprint includes sorted full selected processing references, versions, current open/closed mode, membership-source identity and retained-open-key basis. It excludes attempt/run/time/scratch/destination paths and image digest; image is retained as producer provenance, not a new logical filing or a reason to overwrite old immutable output. For identical input with a different image, adopt verified existing output and preserve its original producing-image metadata. No-op compares source fingerprint before building a candidate against its own base. Manifest has no circular self-hash. Pointer contains `quarter/generation_id/manifest_ref/manifest_sha256/manifest_bytes/source_fingerprint`.

Changes Parquet has non-null `change_type: string`, `cik/archive_path: string`, nullable full `before/after: struct<sec-index-v1>`, and nullable `reason: string`. Types are `added/updated/withdrawn/unresolved_absence`. A provenance-only refresh is counted separately and does not become a business-field update. Business fields are company_name/form_type/filing_date/accession_number plus the logical key; provenance remains in before/after rows for all changes.

Public interfaces produced across tasks:

```python
# Task 1: etl/contracts.py
canonical_schema() -> pyarrow.Schema
observation_schema() -> pyarrow.Schema
change_schema() -> pyarrow.Schema
processing_key(source_id: str, snapshot_sha256: str, parser_version: str, schema_version: str) -> str
observation_base(source_id: str, snapshot_sha256: str, parser_version: str, schema_version: str) -> str
encode_transformed(workset: TransformedWorkset) -> bytes
decode_transformed(body: bytes) -> TransformedWorkset
transformed_ref(workset: TransformedWorkset) -> str
# Task 1: storage/contracts.py; etl/state.py
blob_address(path: str) -> tuple[str, str]
ObjectStore.materialize(path: str, target: Path) -> None
EtlState(store: StateStore)
EtlState.processing(ref: ObservationRef) -> Versioned | None
EtlState.accept_transform(ref: ObservationRef) -> None
EtlState.pointer(quarter: str) -> Versioned | None
EtlState.commit_pointer(quarter: str, value: dict[str, object], previous: Versioned | None) -> Versioned
EtlState.record_candidate(candidate: Candidate) -> None
EtlState.record_publication(manifest: GenerationManifest) -> None
# Task 2: etl/parser.py
ParseError(line_number: int, reason: str)  # ValueError subclass
iter_observations(path: Path, source: Source, snapshot: Snapshot, *, parser_version: str, schema_version: str) -> Iterator[Observation]
parse_fields(fields: tuple[str,str,str,str,str], source: Source, snapshot: Snapshot, *, line_number: int, parser_version: str, schema_version: str) -> Observation
supported_parser(version: str, *, fixture: bool) -> None
# Task 3: etl/transform.py
transform_member(source: Source, snapshot: Snapshot, context: RunContext, settings: Settings, objects: ObjectStore, state: EtlState, *, force: bool = False, observer: BoundaryObserver | None = None) -> ObservationRef
transform_workset(snapshot_ref: str, context: RunContext, settings: Settings, objects: ObjectStore, state: EtlState, acquisition: AcquisitionState, *, force: bool = False, observer: BoundaryObserver | None = None) -> TransformedWorkset
read_observations(ref: ObservationRef, objects: ObjectStore) -> Iterator[Observation]
# Task 4: etl/catalog.py / manifest.py
select_sources(existing: tuple[ObservationRef,...], incoming: tuple[ObservationRef,...]) -> tuple[ObservationRef,...]
source_fingerprint(quarter: str, sources: tuple[ObservationRef,...], *, mode: str, membership_source: ObservationRef | None, retained_from_generation: str | None) -> str
build_candidate(quarter: str, previous: GenerationCapture | None, incoming: tuple[ObservationRef,...], context: RunContext, settings: Settings, objects: ObjectStore, state: EtlState, *, observer: BoundaryObserver | None = None) -> Candidate
read_manifest(capture: GenerationCapture, objects: ObjectStore) -> GenerationManifest
validate_candidate(candidate: Candidate, objects: ObjectStore) -> None
# Task 5: etl/publication.py / reader.py
publish_quarter(quarter: str, incoming: tuple[ObservationRef,...], context: RunContext, settings: Settings, objects: ObjectStore, state: EtlState, *, observer: BoundaryObserver | None = None) -> PublicationResult
repair_publication(quarter: str, objects: ObjectStore, state: EtlState) -> None
capture_quarter(quarter: str, objects: ObjectStore, state: EtlState) -> GenerationCapture | None
read_quarter(capture: GenerationCapture, objects: ObjectStore) -> Iterator[IndexRow]
# Task 6: etl/commands.py
run_transform(snapshot_ref: str, context: RunContext, settings: Settings, objects: ObjectStore, store: StateStore, *, force: bool = False, observer: BoundaryObserver | None = None) -> EtlResult
run_publish(transformed_workset_ref: str, context: RunContext, settings: Settings, objects: ObjectStore, store: StateStore, *, observer: BoundaryObserver | None = None) -> EtlResult
write_etl_result(result: EtlResult, objects: ObjectStore, acquisition: AcquisitionState) -> str
read_etl_result(path: str, objects: ObjectStore) -> EtlResult
```

Interface listings declare signatures; they are not unimplemented production stub files. Implementation code below shows complete critical functions/test examples, supplemented by the exact behavior matrix for each module. Finish each module's specified public contract through its own red/green cycles; do not treat one illustrated assertion as the whole deliverable.

