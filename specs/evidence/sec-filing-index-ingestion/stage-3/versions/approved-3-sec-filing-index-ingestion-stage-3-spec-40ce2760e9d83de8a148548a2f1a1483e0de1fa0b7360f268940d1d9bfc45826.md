# SEC filing-index ingestion — Stage 3 Replayable ETL and Safe Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn exact retained SEC index snapshots into versioned observations and readable quarter generations with raw-only replay, conservative withdrawal gates, conditional commits and crash recovery.

**Architecture:** Extend the existing ingest package and durable object/state adapters. Transform immutable snapshot-workset members independently; construct each quarter from the active manifest's exact source set plus incoming pins using streaming PyArrow and SQLite scratch. Write and validate complete immutable candidates before one Table ETag pointer change; readers and repairs take that pointer/manifest as authority.

**Tech Stack:** Python >=3.14, stdlib unittest/sqlite3/multiprocessing, uv 0.12.15/uv_build, PyArrow 25.0.1; retained Requests 2.34.2, azure-identity 1.26.0, azure-storage-blob 12.31.0, azure-data-tables 12.7.0. Blob API 2026-04-06; Table API 2020-12-06. Existing local fixture and mocked pinned-SDK backends; no provisioning or live access.

**Status:** PROPOSED (2026-10-07 America/New_York) — approval pending; no task executed.
**Implementing spec:** [Stage 3](../sec-filing-index-ingestion-stage-3-spec.md).
**Authority:** [Parent design](../sec-filing-index-ingestion-spec.md), [ADR](../sec-filing-index-ingestion-adr.md), [roadmap](../sec-filing-index-ingestion-roadmap.md), [accepted F1](../sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1), and completed [Stage 1](../completed/sec-filing-index-ingestion-stage-1-spec.md) / [Stage 2](../completed/sec-filing-index-ingestion-stage-2-spec.md) stamps. This plan implements Stage 3 only, not the parent wholesale.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 3 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

## Global Constraints

The following are copied verbatim from Stage 3 spec §3; every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An unrecognized legacy format does not by itself invalidate a usable index row.
- Never deduplicate on company name and filing date alone.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- A conflict requires rereading the active generation and rebuilding; never overwrite a newer pointer with stale work.
- The pointer update is the publication boundary.
- There is no assumed transaction spanning Blob Storage and Table Storage.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Exact values: Python >=3.14; PyArrow 25.0.1; Requests 2.34.2; Identity 1.26.0; Blob 12.31.0/API 2026-04-06; Tables 12.7.0/API 2020-12-06; canonical schema `sec-index-v1`; received-byte guard 67,108,864; expanded-byte guard 536,870,912; exchange deadline 90 seconds; batches 8,192 rows; CAS_ATTEMPTS 5. Retain accepted settings and pins, one ingest package and indefinite development evidence retention. Stage 7 measures actual Linux amd64/Python 3.14.8 worker memory, runtime and scratch; native proofs establish no deployed capacity.

Live SEC, Azure, authentication, compute, provisioning and deployment authorizations remain closed. Use cached libraries and retained evidence only. No auto-fetch fallback, optional codec selection, approval bypass, image build, workflow/schedule activation or later-stage routing belongs to this plan.

---

## Scope and preflight

One coupled deliverable closes R3/R6/R9: transform and publish pinned indexes safely. Splitting parser and pointer safety into separate stage plans would expose an ingestion boundary unable to satisfy first-publication §4.4 gates. Seven independently reviewable tasks below remain one Stage 3 cycle.

Planning baseline is local merged `HEAD = origin/main = 5f90a2116eab21525e88a02d0988567e71d95967`; no remote fetch was used. Stage 1 COMPLETE and Stage 2 COMPLETE are authoritative, including their recorded execution deviations. The planning receipt verifies the accepted 1,584-record F1 manifest (one declared immutable alias), both Stage 2 final bundles (78 and 96 payloads), and 88 current tested/reviewed files. Recheck local HEAD/current edits at execution; new drift is inspected and preserved, never overwritten with this baseline.

Protect the ignored local roadmap (15,853 bytes, SHA-256 `25cc4f40a9ddb34679fc5f226f4cc32a7be6739f75ea463e4dfde499d72aceab`) and four absent `packages/sec-edgar-index-ingest` files listed in Stage 3 spec §1. Preserve subsequent edits and all retained evidence. Never `git add -A`, stash/reset/restore the primary checkout, or commit those deletions. Keep Stage 3 unticked throughout implementation until completion gates and the authoritative stamp actually pass.

After owner approval, record the exact approved plan/spec byte hashes and approval receipt. Make only those documents available to isolation; if a document commit is needed, explicitly add those two paths. Use `using-git-worktrees` at execution time to choose/reuse isolation from the inspected base. A fresh checkout may materialize the original deleted package files; that does not authorize restoring them into the primary tree. Keep the old package excluded. Copy the ignored roadmap only as a read-only input if needed; Git does not carry it. Stop on unexplained base/protected-file drift and resolve it without destructive cleanup.

The local cache contains PyArrow 25.0.1 cp314/macos arm64 records and Stage 1 retains Linux wheel provenance, but cache names are not an install proof. Task 1 resolves/installs/builds offline and proves the actual native import. Failure to resolve the exact accepted pin blocks execution; retain the failure and request the concrete missing offline artifact. Do not change pins or access a package registry.

## File structure and ownership

All implementation paths below use prefix `packages/sec-edgar-ingest/src/sec_edgar_ingest/`; all test paths use prefix `packages/sec-edgar-ingest/tests/`. Task-specific lists use complete repository-relative paths so an isolated implementer can locate them. Execute writer tasks in order. Workers are not alone in the codebase: preserve others' changes, consume the ledger's approved interface deviations and do not revert unrelated edits.

| Task | Responsibility / files |
|---|---|
| 1 | `etl/contracts.py`, `etl/state.py`, `storage/contracts.py`, `storage/local.py`, `storage/azure.py`, exact PyArrow dependency/lock, `tests/test_etl_contracts.py`, `tests/test_etl_storage.py`: immutable contracts and accepted storage routing |
| 2 | `etl/parser.py`, `tests/test_etl_parser.py`, `tests/fixtures/etl/`: row parser and compact independent goldens |
| 3 | `etl/transform.py`, `etl/state.py`, `tests/test_etl_transform.py`: immutable observations, processing checkpoints and transformed worksets |
| 4 | `etl/catalog.py`, `etl/manifest.py`, `tests/test_etl_catalog.py`: disk-backed precedence, deltas, candidate identity/manifest and gate |
| 5 | `etl/publication.py`, `etl/reader.py`, `etl/state.py`, `tests/test_etl_publication.py`: conditional commit, pointer reader and ancillary repair |
| 6 | `cli.py`, `results.py`, `state.py`, `etl/commands.py`, `tests/test_etl_cli.py`, `tests/test_workspace.py`: separate ETL command branch, versioned results and replay correlation |
| 7 | `tests/test_etl_processes.py`, `tests/etl_proof.py`, `scripts/check-sec-edgar-ingest.sh`, read/replay runbook, package/root READMEs, Stage 3 verification evidence: real crash/race and installed-wheel proofs |

`etl/__init__.py` belongs to Task 1. Each module has one boundary; no workflows, parallel package extraction or parser-specific serving database. SQLite here is disposable ETL scratch, not authoritative ingestion state or an analytical service.

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

## Testing and review procedure

Use the existing guarded runner, not unguarded pytest or requests. Install offline before tests; do not disable `tests/network_guard.py`. Every task records actual failing command/exit, covering green command/exit, BASE, named owned-file diff and actual interfaces in the execution ledger. Commit only task-owned paths; dispatch fresh per-task Spec/Quality review via the approved execution skill; fix and re-review findings before the next task. Whole-branch review happens after Task 7, with no claim of integrated Azure behavior.

Focused runner from execution repo root:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_etl_NAME.py' -v
```

Expected red is a missing public interface or behavioral assertion against the old implementation; expected green is `OK`, exit 0. Retain full stdout/stderr and exits, including intermediate failures. Deterministic unit tests use injected clocks/barriers; process proofs use actual independent stores/processes and bounded real deadlines. New tests protect observable contracts rather than copy the algorithm.

### Task 1: Versioned ETL contracts and accepted storage boundaries

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/__init__.py`, `etl/contracts.py`, `etl/state.py` under the same full source prefix, `packages/sec-edgar-ingest/tests/test_etl_contracts.py`, `packages/sec-edgar-ingest/tests/test_etl_storage.py`. Modify `packages/sec-edgar-ingest/pyproject.toml`, `pyproject.toml`, `uv.lock`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py`, `storage/local.py`, `storage/azure.py` under that prefix, and existing `packages/sec-edgar-ingest/tests/test_azure_contracts.py` only for covering routing regressions.

**Interfaces:** Consumes existing Record/StateStore/ObjectStore contracts. Produces all Task 1 signatures above, strict ETL records/schemas, accepted logical Blob mapping, streamed materialization, optional keyword-only `active_client: TableClient | None = None` on AzureStateStore and EtlState CAS facade. Keep open_stores' three-return signature, old two-client construction, legacy config bytes and deployment registry unchanged. Factory obtains ActivePointers in the existing accepted account; provisioning and Approvals client are not needed.

- [ ] **Step 1: Write contract/routing tests and capture red before changes.** Start `test_etl_storage.py` with:

```python
import unittest
from sec_edgar_ingest.storage.contracts import blob_address

class EtlStorageTests(unittest.TestCase):
    def test_logical_paths_use_accepted_containers(self):
        self.assertEqual(blob_address('runs/sec/r/transform/a/result.json'),
                         ('results', 'runs/sec/r/transform/a/result.json'))
        path = 'curated/sec/filing_index/year=2026/quarter=4/generation=g/manifest.json'
        self.assertEqual(blob_address(path), ('manifests', path))
        path = 'observations/sec/indexes/source=s/sha256=h/parser=p/schema=v/rows.parquet'
        self.assertEqual(blob_address(path), ('generations', path))
        self.assertEqual(blob_address('raw/sec/a'), ('raw', 'sec/a'))
        with self.assertRaises(ValueError):
            blob_address('curated/../raw/a')
```

Add contract tests for all schema nullability/type fields, canonical codec byte identity, duplicate/unknown-field rejection, processing identities changing with parser/schema, and old retained snapshot workset decoding/config hash/registry equality. Use the final Stage 2 proof bundle's four worksets as immutable compatibility inputs. Add actual pinned-SDK fake-transport assertions for mapped container/blob URLs, create-only upload and ActivePointers insert/ETag replace/412 conflicts, including a >64KiB logical record using the existing content-first descriptor.

Run both `test_etl_contracts.py` and `test_etl_storage.py` through the focused runner. Expected: missing ETL contracts/blob_address failure before implementation.

- [ ] **Step 2: Add the exact offline dependency and inspect local public SDK/PyArrow calls.** Add `"pyarrow==25.0.1"` to package dependencies and root constraints without changing other pins; run:

```bash
uv lock --offline
uv sync --offline --frozen --package sec-edgar-ingest
uv run --offline --frozen --package sec-edgar-ingest python -c 'import pyarrow, pyarrow.parquet; assert pyarrow.__version__ == "25.0.1"; print(pyarrow.__version__)'
```

Expected: exit 0, `25.0.1`; preserve lock pin comparison and inspected installed public signatures for schema/ParquetWriter/iter_batches/download_blob.chunks/upload_blob and Table create/update. Use `inspect.signature`/`inspect.getsource` on installed packages without constructing credentials. Record native platform/Python separately from Stage 1's retained Linux probe. Do not resolve fresh versions. Stop on uncached artifacts.

- [ ] **Step 3: Implement contracts, storage routing and CAS facade.** Add explicit Arrow schemas matching the record table and strict immutable Record validation/codecs. Implement logical routing in contracts and use it consistently in Azure read/write/verify/materialize:

```python
def blob_address(path: str) -> tuple[str, str]:
    safe_relative_path(path, 'object path')
    root, separator, tail = path.partition('/')
    if not separator:
        raise ValueError('object path requires a root and object key')
    if root in {'raw', 'worksets', 'quarantine', 'locks', 'results',
                'generations', 'manifests', 'approvals'}:
        return root, tail
    if root == 'staging':
        return 'raw', path
    if root == 'runs':
        return 'results', path
    if root in {'observations', 'curated'}:
        return ('manifests' if path.endswith('/manifest.json') else 'generations'), path
    raise ValueError('object path has no accepted Blob binding')
```

Local materialize copies bytes in FILE_CHUNK_BYTES chunks to an exclusively created caller scratch file; Azure uses the mapped blob's bounded `download_blob(max_concurrency=1).chunks()` iterator. Callers verify against known SHA/length after download; materialize does not invent validators. A missing/corrupt stream deletes only its own temporary scratch and raises. `stage` remains create-only and verifies collision; `promote` remains raw-only. Never write production objects via DFS.

Route `QuarterPublication` to ActivePointers and existing attempt kinds to Attempts; Processing/Candidate/PublicationReceipt remain SourceState. AzureStateStore's new active_client is optional for old callers, validates exact endpoint/table, closes with the others and refuses pointer operations if omitted. `open_azure_stores` supplies it; preserve old registry canonical bytes. EtlState pointer commit performs insert for absent or exact-version replace for present, with no wildcard and no swallowed conflict. Define remaining EtlState methods with canonical identity/payload comparisons, bounded CAS on ancillary records, immutable accepted-transform conflicts and per-quarter publication receipts. These indexes never alter raw acquisition status.

- [ ] **Step 4: Cover green and acquisition compatibility.** Run focused `test_etl_contracts.py`, `test_etl_storage.py`, `test_worksets.py`, `test_storage.py`, `test_azure_contracts.py`, `test_azure_state_payloads.py` with the guarded runner. Expected all OK. Retain emitted SDK wire paths/ETags and byte comparisons, not merely a mocked method-call count.

- [ ] **Step 5: Commit owned files.** Use explicit files from this task only; inspect diff for all acquisition pins/settings/registry preservation.

```bash
git add pyproject.toml uv.lock packages/sec-edgar-ingest/pyproject.toml packages/sec-edgar-ingest/src/sec_edgar_ingest/etl packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/local.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py packages/sec-edgar-ingest/tests/test_etl_contracts.py packages/sec-edgar-ingest/tests/test_etl_storage.py packages/sec-edgar-ingest/tests/test_azure_contracts.py
git commit -m 'feat: add versioned ETL and publication storage contracts'
```

### Task 2: Strict row parsing and independent golden fixtures

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/parser.py`, `packages/sec-edgar-ingest/tests/test_etl_parser.py`, and `packages/sec-edgar-ingest/tests/fixtures/etl/{quarterly.idx,daily.idx,legacy.idx,expected.json,fixture-manifest.json}`. ZIP fixture is generated deterministically from quarterly.idx during tests; retained original ZIPs are separately replayed in Task 7. Do not alter Stage 1/2 receipts.

**Interfaces:** Consumes IndexRow/Observation and acquisition validation/constants. Produces ParseError, supported_parser, parse_fields and iter_observations signatures above. Duplicate conflict detection belongs to Task 3's source-wide scratch index, not parser row state.

- [ ] **Step 1: Write golden and refusal tests, run red.** Include this complete first test using existing fixture helpers:

```python
import unittest
from sec_edgar_ingest.etl.parser import parse_fields
from support import fixture_source, fixture_snapshot

class EtlParserTests(unittest.TestCase):
    def test_daily_date_chooses_older_output_quarter(self):
        source = fixture_source(kind='daily', period='2026-09-30')
        snapshot = fixture_snapshot(source, b'fixture-only')
        fields = ('123456', 'Example Corp', '10-K/A', '20250825',
                  'edgar/data/123456/0000123456-25-000001.txt')
        obs = parse_fields(fields, source, snapshot, line_number=12,
                           parser_version='fixture-index-parser-v1',
                           schema_version='sec-index-v1')
        self.assertEqual(obs.row.cik, '0000123456')
        self.assertEqual(obs.row.filing_date.isoformat(), '2025-08-25')
        self.assertEqual(obs.row.accession_number, '0000123456-25-000001')
        self.assertEqual(obs.row.form_type, '10-K/A')
        self.assertEqual(obs.original_fields, fields)
```

`fixture_source(period: str = "2015Q1", kind: str = "quarterly")` is the existing validated builder. Run focused test_etl_parser.py; expect missing parser or golden assertion failure.

- [ ] **Step 2: Implement the parser core and exact fixture bytes.** Register `sec-index-parser-v1` and local-only fixture aliases v1/v2; no arbitrary label may pretend to have a tested parser. `fixture-envelope-v1` is acquisition provenance only. Reject unsupported schema/parser before storage opens. parse_fields uses:

```python
# Within parse_fields, after requiring exactly five string fields:
original_fields = fields
cik, company, form, text_date, path = (value.strip() for value in fields)
if not re.fullmatch(r'[0-9]{1,10}', cik) or not company or not form:
    raise ParseError(line_number, 'invalid CIK or empty company/form')
normalized_cik = cik.zfill(10)
pattern = r'[0-9]{4}-[0-9]{2}-[0-9]{2}' if source.kind == 'quarterly' else r'[0-9]{8}'
if not re.fullmatch(pattern, text_date):
    raise ParseError(line_number, 'unsupported filing-date spelling')
try:
    filing_date = date.fromisoformat(text_date)
except ValueError as error:
    raise ParseError(line_number, 'invalid calendar date') from error
if any(char in path for char in ('\\', '%', '?', '#')):
    raise ParseError(line_number, 'unsafe archive path')
safe_relative_path(path, 'archive_path')
segments = path.split('/')
if (len(segments) >= 4 and segments[:2] == ['edgar', 'data'] and
        re.fullmatch(r'[0-9]{1,10}', segments[2]) and
        segments[2].zfill(10) != normalized_cik):
    raise ParseError(line_number, 'archive path CIK mismatch')
match = re.fullmatch(r'edgar/data/[0-9]{1,10}/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt', path)
accession = match.group(1) if match else None
row = IndexRow(normalized_cik, company, form, path, filing_date, accession,
               source.source_id, snapshot.sha256, parser_version, schema_version)
return Observation(row, original_fields, line_number)
```

Catch safe-path/record validation errors as ParseError with physical line number, never silently skip. iter_observations streams selected ZIP member/plain source, checks ASCII/line endings/header/separator and parses every subsequent nonempty row; a blank row within the data section is refused. Use acquisition validation for archive/member/CRC/size/denial checks at transform time and keep parsing independently strict. Source receipt without any rows is invalid. Preamble/footer cannot swallow data or repeated headers. Nullable legacy example is `edgar/data/123456/legacy-annual.txt`; preserve original path case and report its synthetic nature.

Create quarterly golden with ISO dates, CRLF and exact Filename header; daily with compact dates, LF and exact File Name header. Store hand-authored expected normalized rows in expected.json, including two paths with same company/date and distinct amendments. Manifest records exact fixture hashes and synthetic provenance; expected output is not generated by the production parser.

- [ ] **Step 3: Complete the refusal/boundary matrix and green.** Cases: decimal CIK length/zeros; leap/non-leap days; impossible compact/ISO dates; blank fields; four/six columns; absolute/traversal/double slash/backslash/escaped/query/fragment/control paths; CIK mismatch; safe legacy null including a nested/unrecognized safe path; case-preserving path; final newline/no final newline; bad ASCII/newline/header/separator; malformed last row after valid rows; amendments and cross-quarter daily filing date. Assert line/reason and unchanged originals. Run guarded test_etl_parser.py and existing test_validation.py; expect OK.

- [ ] **Step 4: Commit owned parser/tests/fixtures.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/parser.py packages/sec-edgar-ingest/tests/test_etl_parser.py packages/sec-edgar-ingest/tests/fixtures/etl
git commit -m 'feat: parse retained index rows with strict golden contracts'
```

### Task 3: Immutable observations, processing checkpoints and raw-only replay

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/transform.py`, `packages/sec-edgar-ingest/tests/test_etl_transform.py`; modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py`. Test setup helpers needed by later tasks live in `packages/sec-edgar-ingest/tests/support_etl.py` and are owned here.

**Interfaces:** Consumes Task 1/2 contracts, raw snapshot worksets/bindings and Settings. Produces transform_member/transform_workset/read_observations and test `seed_snapshot(root: Path, source: Source, body: bytes) -> tuple[StateStore,ObjectStore,SnapshotWorkset]`; helper writes actual immutable raw/source/snapshot worksets and binding through real local stores. It must use existing fixture_workset/fixture_snapshot plus encode_workset/make_snapshot_workset and AcquisitionState.bind_once; it implements no alternate transformation/publication logic.

- [ ] **Step 1: Write no-op/version replay test and capture red.** Use seed_snapshot with a golden daily body, then call transform_workset with a new fixture transform context (replace etl.parser_version in Settings mapping, reconstruct Settings, create/pin a fresh RunContext). Assert two calls return identical verified observation refs with unchanged raw/source/workset bytes. Change only the transform parser to fixture-index-parser-v2 in a new context; assert a new processing/output reference with identical logical rows and unchanged acquisition origin. Patch acquisition Coordinator/BoundedSender/RequestClient constructors to raise and assert neither call invokes them. Add corrupt hash/binding/source-workset mismatch and incomplete membership failures. Run test_etl_transform.py; expect missing implementation.

The exact first input setup helper is:

```python
def seed_snapshot(root, source, body):
    from sec_edgar_ingest.models import Binding
    from sec_edgar_ingest.state import AcquisitionState
    from sec_edgar_ingest.worksets import encode_workset, make_snapshot_workset
    from support import fixture_snapshot, fixture_workset, store_bundle
    store, objects, leases = store_bundle(root)
    source_set = fixture_workset(members=(source,))
    snapshot = fixture_snapshot(source, body)
    objects.put_once(snapshot.raw_path, body)
    objects.put_once(f'worksets/sec/source/sha256={source_set.workset_id}/workset.json',
                     encode_workset(source_set))
    acquisition = AcquisitionState(store)
    acquisition.remember_snapshot(snapshot)
    acquisition.bind_once(Binding(source_set.workset_id, source.source_id, snapshot.sha256))
    snapshot_set = make_snapshot_workset(source_set, (snapshot,))
    objects.put_once(f'worksets/sec/snapshot/sha256={snapshot_set.workset_id}/workset.json',
                     encode_workset(snapshot_set))
    return store, objects, snapshot_set
```


The concrete context builder and first replay test are:

```python
# tests/support_etl.py
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from sec_edgar_ingest.config import pin_context
from support import fixture_context, fixture_settings

def etl_context(parser_version='fixture-index-parser-v1', command='transform', attempt='etl1'):
    settings = fixture_settings(etl={'parser_version': parser_version})
    started = datetime.now(timezone.utc)
    context = replace(fixture_context(), command=command, attempt_id=attempt,
                      parser_version=parser_version, config_sha256=settings.config_sha256,
                      started_at=started, deadline=started + timedelta(seconds=3600),
                      effective_config={}, pinned_on=None)
    return settings, pin_context(settings, context, started.date())[0]

# tests/test_etl_transform.py
import tempfile
import unittest
from pathlib import Path
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.transform import transform_workset
from sec_edgar_ingest.state import AcquisitionState
from support import fixture_source
from support_etl import etl_context, seed_snapshot

class EtlTransformTests(unittest.TestCase):
    def test_parser_replay_keeps_raw_origin_and_changes_processing_identity(self):
        body = (b'CIK|Company Name|Form Type|Date Filed|File Name\n-----\n'
                b'123456|Example Corp|10-K/A|20250825|edgar/data/123456/0000123456-25-000001.txt\n')
        with tempfile.TemporaryDirectory() as directory:
            source = fixture_source('2026-09-30', 'daily')
            store, objects, origin = seed_snapshot(Path(directory), source, body)
            path = f'worksets/sec/snapshot/sha256={origin.workset_id}/workset.json'
            before = objects.read(path)
            settings, context = etl_context()
            first = transform_workset(path, context, settings, objects, EtlState(store), AcquisitionState(store))
            again = transform_workset(path, context, settings, objects, EtlState(store), AcquisitionState(store))
            settings2, context2 = etl_context('fixture-index-parser-v2', attempt='etl2')
            second = transform_workset(path, context2, settings2, objects, EtlState(store), AcquisitionState(store))
            self.assertTrue(first.complete and second.complete)
            self.assertEqual(first.observations, again.observations)
            self.assertNotEqual(first.observations[0].rows_ref, second.observations[0].rows_ref)
            self.assertEqual(second.origin_context, origin.context)
            self.assertEqual(objects.read(path), before)
            self.assertEqual(objects.read(origin.snapshots[0].raw_path), body)
```

`etl_context` returns `(Settings, RunContext)` and seeds a real future deadline; tests that target timeout use an injected clock rather than relying on the static Stage 2 fixture day. Source origin retains its original pin/config. Close stores/read iterators in test cleanup so process proofs cannot leak scratch or handles.

- [ ] **Step 2: Implement one-source transformation and immutable checkpoints.** Materialize/verify original bytes under TemporaryDirectory, create BodyReceipt with retained validators only where their transport meaning applies, and call existing `validate_envelope(source, receipt, settings)` using the exact source/envelope/limits. ZIP decoded scratch never replaces original. Stream observations into PyArrow ParquetWriter in 8,192-row batches with pinned schema/metadata/options (Parquet 2.6, compression snappy, dictionary disabled, no timestamps/run IDs). SQLite scratch has primary key `(cik,archive_path)` and canonical normalized row JSON. For each observation:

```python
key = (obs.row.cik, obs.row.archive_path)
normalized = canonical_json(obs.row.to_mapping())
old = db.execute('SELECT payload FROM seen WHERE cik=? AND path=?', key).fetchone()
if old is not None and old[0] != normalized:
    raise ParseError(obs.line_number, 'conflicting duplicate logical key')
if old is None:
    db.execute('INSERT INTO seen(cik,path,payload) VALUES(?,?,?)', (*key, normalized))
# Retain every identical duplicate observation in the Parquet source output.
batch.append(obs)
if len(batch) == BATCH_ROWS:
    writer.write_table(pa.Table.from_pylist([observation_mapping(x) for x in batch],
                                          schema=observation_schema()))
    batch.clear()
```

Define `observation_mapping(obs: Observation) -> dict[str,object]` locally: flatten obs.row.to_mapping(), replace filing_date with the actual date, and add original_fields as list and line_number. No complete-source output reference is accepted until the whole source parses and Parquet readback/schema/count/key/quarter totals pass. Failure retains raw and writes `quarantine/sec/<run>/<source>/transform/<attempt>/error.json` with line/reason/raw hash and versions; leave any previously successful processing identity unchanged. Release scratch on every path.

Upload observations with ObjectStore.stage, verify output SHA/length, create observation manifest only after data verification, then accept_transform by create-or-adopt matching immutable Processing row. Crash after output before Processing can repair from the validated observation manifest. Force repeats parsing/readback and verifies collision byte identity; mismatch raises state_conflict rather than overwriting immutable output.

Observation manifest contains source/snapshot/versions/counts/rows path/hash/length/producing image, canonical format `sec-observation-v1`; do not hash its own bytes into itself. Adoption verifies contents/counts/source/versions, preserves original producer metadata and returns its ObservationRef. read_observations materializes/validates referenced bytes and iterates batches while retaining scratch until the iterator closes.

- [ ] **Step 3: Implement exact workset transformation and complete/partial outputs.** Decode snapshot_ref and its referenced immutable source-workset, verify each exact binding and member metadata, keep origin_context untouched, and process members independently. Read inputs from objects only. Successful processing refs are reused if manifest/data validate; missing/corrupt accepted output fails closed with retained failure, never silently accepts empty results. Successful members survive failures. Build sorted immutable TransformedWorkset with complete=false/failures for partial success and complete=true only when all members succeed. Empty fully successful snapshot workset becomes an explicit complete empty transformed workset and later no-op, not a source deletion.

Write transformed workset create-only at transformed_ref; verify strict round trip and both ID/hash roles. Publish cannot accept partial worksets. Add named observer points `transform.after_rows`, `transform.after_manifest`, `transform.after_processing`, `transform.after_workset` against real durability operations.

- [ ] **Step 4: Green, failures and restart.** Run guarded test_etl_transform.py and test_etl_parser.py. Cover identical duplicates/source counts vs distinct keys, conflicting last row after batches, raw hash/length drift, malformed/envelope/ZIP CRC, interrupted data/manifest/Processing checkpoint, new-process restart/reuse, concurrent transform same identity adopting one exact output, parser v2 replay, partial source-set recovery and cross-quarter counts. Expected OK and zero transport starts. Retain actual raw/observation/workset hashes and immutable winner/loser evidence.

- [ ] **Step 5: Commit owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/transform.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py packages/sec-edgar-ingest/tests/test_etl_transform.py packages/sec-edgar-ingest/tests/support_etl.py
git commit -m 'feat: transform pinned raw snapshots into replayable observations'
```

### Task 4: Deterministic canonical generations, changes and first-publication gate

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/catalog.py`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py`, `packages/sec-edgar-ingest/tests/test_etl_catalog.py`. Extend `packages/sec-edgar-ingest/tests/support_etl.py` only with real-store row/manifest assertion helpers; no alternate catalog builder.

**Interfaces:** Consumes Task 3 ObservationRefs/read_observations/transform_member and Task 1 EtlState. Produces select_sources/source_fingerprint/build_candidate/read_manifest/validate_candidate. read_manifest loads only an exact GenerationCapture; Task 5 will create captures from pointer fields. Task 4 does not mutate pointers.

- [ ] **Step 1: Write source-selection and generation-gate tests, capture red.** First pure behavior test:

```python
import unittest
from dataclasses import replace
from datetime import timedelta
from sec_edgar_ingest.etl.catalog import select_sources
from sec_edgar_ingest.etl.contracts import ObservationRef, observation_base
from support import fixture_source, fixture_snapshot

class EtlCatalogTests(unittest.TestCase):
    def test_stale_snapshot_cannot_replace_newer_source_revision(self):
        source = fixture_source()
        old = fixture_snapshot(source, b'old')
        new = replace(fixture_snapshot(source, b'new'),
                      received_at=old.received_at + timedelta(seconds=1))
        def ref(snapshot):
            base = observation_base(source.source_id, snapshot.sha256,
                                    'fixture-index-parser-v1', 'sec-index-v1')
            return ObservationRef(source, snapshot, 'fixture-index-parser-v1',
                                  'sec-index-v1', base + '/rows.parquet',
                                  base + '/manifest.json', 'a'*64,
                                  12, 1, 1, {'2015Q1': 1})
        self.assertEqual(select_sources((ref(new),), (ref(old),)), (ref(new),))
```

Add real candidate tests: quarterly fields beat conflicting daily fields; latest daily wins without quarterly; open quarterly absence retains active key; closed missing key stages awaiting_approval with base/hash/candidate and does not remove active data; closed quarter membership prevents daily-only absent keys; malformed/zero-row input never becomes candidate. Run test_etl_catalog.py; expect missing catalog or failed gate assertion.

- [ ] **Step 2: Implement source selection, replay version alignment and disk-backed resolution.** Complete revision-selection core:

```python
def select_sources(existing, incoming):
    selected = {}
    for ref in (*existing, *incoming):
        identity = ref.source.source_id
        old = selected.get(identity)
        if old is None:
            selected[identity] = ref
            continue
        if old.source != ref.source:
            raise Conflict('source ID has conflicting source metadata')
        if old.snapshot.sha256 == ref.snapshot.sha256:
            if (old.parser_version, old.schema_version) == (ref.parser_version, ref.schema_version):
                if old.rows_sha256 != ref.rows_sha256:
                    raise Conflict('same processing identity has conflicting observations')
                continue
            # New-version alignment happens by raw replay in build_candidate.
            continue
        if old.snapshot.received_at == ref.snapshot.received_at:
            raise Conflict('same receipt time has ambiguous distinct snapshots')
        if ref.snapshot.received_at > old.snapshot.received_at:
            selected[identity] = ref
    return tuple(selected[key] for key in sorted(selected))
```

For each selected source with versions different from current transform context, call transform_member against its exact retained raw snapshot; preserve the source revision and build every contributing observation under one parser/schema. Do not force acquisition-context equality. Existing same-hash refs adopt unchanged snapshots; receipt times are not source-date coverage.

Load incoming refs plus prior manifest sources into SQLite scratch and stream observations for the target filing-date quarter. Insert canonical business/provenance rows and rank columns `(quarterly preference, daily source period, snapshot receipt, source ID)`; quarterly membership authority applies only to a quarterly source whose period equals the output quarter. Unexpected quarterly rows in another filing quarter are retained observations and reported; they provide field observations there, not a false complete membership boundary. Refuse two different quarterly sources claiming the same period at the same priority without an unambiguous selected source revision.

Use stable SQL `ORDER BY cik,path,quarterly_preference DESC,source_period DESC,received_at DESC,source_id ASC` and yield one row per logical key. Do not use a Python dict containing a whole quarter. Retain all source observation outputs. Detect conflicting same-source duplicate keys through Task 3; never resolve those conflicts with a rank.

Determine mode from context.pinned_on using quarter_for. Future output quarters fail configuration. For open quarter, merge active absent keys back with their original provenance and unresolved-absence changes. For closed quarter with valid quarterly authority, proposed membership is exactly its target-quarter keys; daily keys outside it are withheld, and active absent keys are proposed withdrawals. Without quarterly authority, merge active rows plus valid daily updates/additions and infer no withdrawals. Record authoritative membership source in manifest. An empty quarterly target-quarter membership is invalid replacement evidence and cannot withdraw; retain a quarantined/invalid_source outcome.

- [ ] **Step 3: Build candidate data and deltas, validate and stage gated record.** Merge sorted active/proposed rows in SQLite (or two ordered cursors) to compute added/updated/withdrawn/unresolved-absence before/after records; compare business fields for updated and count provenance refresh separately. Write canonical data sorted by `(cik,archive_path)` and changes sorted by `(cik,archive_path,change_type)`, in bounded Arrow batches with explicit schemas/options. Recompute row/key/quarter/schema/count/hash invariants from emitted files before creating manifest. The selected complete source set, mode, membership and retained-open-key base produce source_fingerprint; candidate generation includes base generation, so gate/diff belongs to that exact base.

Core identity/gate calculation:

```python
fingerprint = source_fingerprint(quarter, selected,
    mode=mode, membership_source=membership,
    retained_from_generation=previous.generation_id if retained_count and previous else None)
generation_id = hashlib.sha256(canonical_json({
    'quarter': quarter,
    'base_generation_id': previous.generation_id if previous else None,
    'source_fingerprint': fingerprint,
})).hexdigest()
gate = 'awaiting_approval' if mode == 'closed' and withdrawn_count else 'clear'
```

Paths come from the approved curated prefix. Emit part-00000.parquet, changes.parquet and manifest.json; one part initially is sufficient, with streaming row groups rather than an unbounded in-memory table. Manifest may retain preceding generation ref solely for open unresolved keys; include/verify that dependency explicitly, never resolve a mutable latest. GenerationManifest records producing image; a verified immutable existing candidate wins adoption rather than a new attempt overwriting metadata.

For a gated replacement create `worksets/sec/candidates/sha256=<generation_id>/candidate.json` with quarter/generation/base/source_fingerprint/quarterly_hash/manifest_ref/change_ref/gate, then EtlState.record_candidate. Files and manifest are validated before candidate index. Candidate IDs and hashes are retained even if no pointer exists. No code in this task creates or interprets human approval.

validate_candidate checks manifest canonical bytes/full hash/length, exact generation/quarter/base/files/versions/source-set identity, schemas/row counts/key uniqueness, filing quarter and change counts. read_manifest rejects missing/noncanonical/mismatched capture objects; no glob or unverified fallback. Named boundaries: `candidate.after_data`, `candidate.after_changes`, `candidate.after_manifest`, `candidate.after_validation`.

- [ ] **Step 4: Complete catalog matrix and green.** Guarded test_etl_catalog.py covers input-order determinism, duplicate overlap, amendment identity, safe null accession, cross-quarter daily distribution, source period vs filing-date, fresh/stale/equal-time hashes, newer field updates, open absence, open-to-closed classification using publication date, closed daily authority, empty/invalid replacement, provenance-only refresh, full source set retention, parser replay of previous raw contributors, corrupt manifest/data refusal, no-op fingerprint stability and changed base producing a different diff/candidate. Expected OK; all candidates use real immutable object writes and no pointer mutation.

- [ ] **Step 5: Commit owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/catalog.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py packages/sec-edgar-ingest/tests/test_etl_catalog.py packages/sec-edgar-ingest/tests/support_etl.py
git commit -m 'feat: build canonical quarter candidates with conservative withdrawal gates'
```

### Task 5: Pointer publication, manifest reader and post-commit repair

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py`, `packages/sec-edgar-ingest/tests/test_etl_publication.py`; modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py` only for per-quarter receipt/repair methods and `packages/sec-edgar-ingest/tests/support_etl.py` for first-golden-generation setup.

**Interfaces:** Consumes Task 4 candidate/manifest/readback functions, EtlState pointer actual version and immutable ObservationRefs. Produces publish_quarter/repair_publication/capture_quarter/read_quarter signatures. No global lock or reuse of the SEC collector lease; safety rests on pointer CAS, complete candidates and rebuild.

- [ ] **Step 1: Write commit-boundary and reader tests, run red.** First CAS interface test works without a catalog fixture:

```python
import tempfile
import unittest
from pathlib import Path
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.storage.contracts import Conflict
from support import store_bundle

class EtlPublicationTests(unittest.TestCase):
    def test_stale_pointer_version_cannot_replace_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            store, objects, leases = store_bundle(Path(directory))
            state = EtlState(store)
            first = state.commit_pointer('2026Q4', {
                'quarter': '2026Q4', 'generation_id': '1'*64,
                'manifest_ref': 'curated/sec/filing_index/year=2026/quarter=4/generation='+'1'*64+'/manifest.json',
                'manifest_sha256': 'a'*64, 'manifest_bytes': 10, 'source_fingerprint': 'b'*64}, None)
            newer = first.to_mapping()['value']
            newer['generation_id'] = '2'*64
            newer['manifest_ref'] = 'curated/sec/filing_index/year=2026/quarter=4/generation='+'2'*64+'/manifest.json'
            state.commit_pointer('2026Q4', newer, first)
            with self.assertRaises(Conflict):
                state.commit_pointer('2026Q4', first.to_mapping()['value'], first)
            self.assertEqual(state.pointer('2026Q4').value['generation_id'], '2'*64)
```

EtlState validates pointer shape and exact generations. Then actual publication tests seed transformed goldens, capture previous generation, kill/raise at each candidate/pointer boundary and assert readers return only validated old/new complete datasets. Run guarded test_etl_publication.py; expect missing publication implementation.

- [ ] **Step 2: Implement complete-candidate CAS and bounded rebuild.** For each iteration read current pointer; capture/validate manifest and source refs; combine original incoming immutable refs with winner's sources; check aligned source fingerprint/mode/membership for no-op before candidate building. A no-op repairs indexes and returns unchanged/current capture. CAS commits only fully validated clear candidate. Illustrative complete control core:

```python
def publish_quarter(quarter, incoming, context, settings, objects, state, *, observer=None):
    for conflicts in range(CAS_ATTEMPTS):
        if datetime.now(timezone.utc) >= context.deadline:
            return PublicationResult(quarter, 'publication_conflict', None, None, None, conflicts)
        current = state.pointer(quarter)
        previous = capture_from_pointer(current) if current is not None else None
        existing = read_manifest(previous, objects) if previous is not None else None
        if unchanged_inputs(quarter, existing, incoming, context):
            repair_publication(quarter, objects, state)
            return PublicationResult(quarter, 'unchanged', previous.generation_id,
                                     previous.manifest_ref, None, conflicts)
        candidate = build_candidate(quarter, previous, incoming, context, settings,
                                    objects, state, observer=observer)
        validate_candidate(candidate, objects)
        if candidate.manifest.gate == 'awaiting_approval':
            state.record_candidate(candidate)
            return PublicationResult(quarter, 'awaiting_approval', None, None,
                                     candidate.candidate_ref, conflicts)
        observe(observer, 'publication.before_pointer')
        try:
            state.commit_pointer(quarter, pointer_value(candidate), current)
        except (AlreadyExists, Conflict):
            observe(observer, 'publication.cas_lost')
            continue
        observe(observer, 'publication.after_pointer')
        state.record_publication(candidate.manifest)
        observe(observer, 'publication.after_repair')
        return PublicationResult(quarter, 'published', candidate.manifest.generation_id,
                                 candidate.manifest_ref, None, conflicts)
    return PublicationResult(quarter, 'publication_conflict', None, None, None, CAS_ATTEMPTS)
```

Define local helpers with these signatures and behavior: `capture_from_pointer(row: Versioned) -> GenerationCapture` checks exact pointer shape/quarter/generation/hash; `pointer_value(candidate: Candidate) -> dict[str,object]` serializes the six pointer fields; `unchanged_inputs(quarter: str, existing: GenerationManifest | None, incoming: tuple[ObservationRef,...], context: RunContext) -> bool` uses Task 4 selection and mode/membership/retained-basis logic, never merely incoming workset hash. For an unchanged selected source set, reuse `existing.retained_from_generation` when recomputing the fingerprint; using the current generation ID as a new retained basis would cause endless advances on identical open-quarter inputs. If versions differ, return false and replay old contributors in build_candidate. Use injectable clock for deterministic unit deadlines while CLI supplies real bounded UTC; retain equivalent deadline semantics in process proofs. Bound storage calls with current adapter timeouts.

A newly gated candidate built during a CAS retry remains awaiting_approval. Caller approval-looking metadata is refused in strict codecs and never changes this path. A CAS loser preserves all incoming source pins and rereads winner sources; no candidate-only retry against a new ETag. Failures preserve current pointer and name the latest candidate/race evidence in the command gap.

- [ ] **Step 3: Implement readers and repair from authoritative manifests.** capture_quarter reads one pointer row and returns a hash/length-bound immutable capture after manifest verification. read_quarter materializes only explicit data file refs, verifies checksums/schema/counts/quarter/key uniqueness before yielding any externally accepted row; either prevalidate fully then stream, or return a validated capture plus iterator whose initialization completes readback. No corrupt generation may leak a partial successful read. Old captures use the supplied generation; do not reread latest pointer when consuming them.

repair_publication captures/validates the current manifest and records idempotent per-processing/quarter/generation PublicationReceipt and Processing publication memberships. A Processing identity is fully published only after every quarter in its quarter_counts has a committed receipt naming a manifest that actually includes it. Provenance retained from an old generation is traceable; don't claim an unrelated incoming source published merely because some quarter advanced. record_publication is repairable bounded CAS and cannot roll a newer processing state backward or rewrite output references. If current pointer is already the candidate after a crash, verify and repair it; no second pointer advance/change event. Partial repair may be retried safely.

- [ ] **Step 4: Full publication/reader matrix and green.** Cover missing pointer insert race, stale replace race, winner source union, updated winner fields, withdrawal gate re-evaluation after winner advances, repeated no-op, forced replay adoption, old capture after pointer advancement, unreferenced losing data, incomplete/corrupt manifest/files, crash before files finish/before pointer/immediately after pointer/inside repair, multi-quarter source with only one published quarter, persistent 5-conflict outcome and unchanged acquisition state. Include mocked SDK ActivePointers create/ETag conditional replace with real 412 translation and large manifest references. Run test_etl_publication.py plus test_etl_catalog.py and test_etl_storage.py guarded; expected OK.

- [ ] **Step 5: Commit owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py packages/sec-edgar-ingest/tests/test_etl_publication.py packages/sec-edgar-ingest/tests/support_etl.py
git commit -m 'feat: commit quarter pointers with conflict rebuild and crash repair'
```

### Task 6: Offline transform/publish commands and durable ETL results

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py`, `packages/sec-edgar-ingest/tests/test_etl_cli.py`. Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `results.py`, `state.py` under the same source prefix, `packages/sec-edgar-ingest/tests/test_workspace.py` and `tests/test_cli.py` only for command/result regression expectations.

**Interfaces:** Consumes transform_workset/publish_quarter and existing Settings/RunContext/Attempt identity. Produces run_transform/run_publish/write_etl_result/read_etl_result. Existing CommandResult/old result bytes stay valid and unchanged; EtlResult has explicit sec-etl-result-v1 format, not silently added defaults on acquisition result codec. Allow result_path for four shared commands; read_result remains acquisition decoder, read_etl_result is separate strict decoder. AcquisitionState.finish_attempt accepts `CommandResult | EtlResult` by shared context/to_mapping/gaps/ended_at contract, preserving existing type/identity validation.

- [ ] **Step 1: Write command-boundary tests, capture red.** Add unittest assertions that help advertises transform/publish, transform accepts a retained snapshot workset without fixture-pack and publish accepts a complete transformed workset; require config/run/execution/attempt/deadline/workset. The no-acquisition assertion uses:

```python
from unittest.mock import patch

with patch('sec_edgar_ingest.cli.Coordinator', side_effect=AssertionError('ETL constructed SEC coordinator')), \
     patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('ETL constructed SEC sender')), \
     patch('sec_edgar_ingest.cli.RequestClient', side_effect=AssertionError('ETL constructed SEC request client')):
    code = main(argv)
self.assertEqual(code, 0)
```

Build argv from a real seeded snapshot_ref/config with synthetic provenance and future explicit deadline; use actual command invocation, not a fake EtlResult. Add missing/unsupported parser/schema/config/ref path failures before open_stores. Run test_etl_cli.py guarded; expect argparse missing-command failure.

- [ ] **Step 2: Implement the separate ETL CLI path and exact correlation.** Extend parser with transform/publish, shared correlation/config/deadline flags, `--workset`, fixture-only `--state-dir/--today`, and transform-only `--force`. ETL commands refuse `--fixture-pack`, since all input is stored. Validate parser/versions, IDs, relative immutable workset path shape, pin date and deadline before constructing adapters. Snapshot refs match `worksets/sec/snapshot/sha256=<64hex>/workset.json`; publish refs match transformed equivalent. Validate inside commands that path ID equals decoded payload ID and full canonical bytes.

Branch before acquisition transport creation; open selected stores, create EtlState/AcquisitionState, begin exact Attempt, persist create-only command.json intent, and invoke run_transform/run_publish. No Coordinator/Sender/RequestClient/fixture-pack/SEC HTTP construction in that branch. Azure runtime identity is for storage only; offline tests mock clients and forbid credentials. New command flags do not change Settings serialization or immutable origin config hash.

Current CLI _existing_context replays acquisition results; implement analogous ETL flow using read_etl_result. Preserve saved start/pinned date for exact same completed attempt, compare frozen config/image/parser/schema/deadline/input/force and reject mismatched reuse. A new attempt may have current versions/date and old snapshot acquisition origin. Expired completed result replay may repair Attempt from its frozen context; a new expired attempt refuses without work. A crash with a begun Attempt/intent but no result resumes frozen context rather than fabricating a new start.

- [ ] **Step 3: Implement aggregate results, outcome exits and result-first repair.** run_transform returns complete/partial processing counts/ref/gaps and run_publish iterates the union of incoming quarter_counts and prior affected source-quarter receipts so a changed filing date updates old/new quarter outcomes explicitly. Reject partial TransformedWorkset before any pointer changes. Each quarter may advance independently; continue unaffected quarters on a gated/failing quarter and report every outcome. Do not claim a multi-quarter source fully published until its complete per-quarter receipts exist.

Use exits: success/unchanged/no_new_sources 0; configuration 2; incomplete 3; quarantined/invalid_source 7; state_conflict/internal_error/publication_conflict 9; awaiting_approval 10. Preserve existing acquisition exit meanings. Any gate makes aggregate awaiting_approval unless a harder invalid/conflict/incomplete failure exists; include all gates in quarters/counters regardless of aggregate priority. A complete empty workset returns unchanged with zero quarter advances. Files produced are not publication success.

EtlResult-first commit core:

```python
def write_etl_result(result, objects, acquisition):
    row = acquisition.store.get('Attempt', attempt_key(result.context))
    if row is None or row.value['context'] != result.context.to_mapping():
        raise Conflict('ETL result requires exact begun Attempt')
    saved = row.value['result']
    if saved is not None and saved != result.to_mapping():
        raise Conflict('ETL result differs from completed Attempt')
    path = result_path(result.context)
    objects.put_once(path, result.to_json())
    acquisition.finish_attempt(result)
    return path
```

read_etl_result checks format/path/correlation/canonical bytes/outcome and counters. Add `etl_result.after_object` and `etl_result.after_attempt` observer points. A result-write crash after quarter commit yields recoverable pointer/manifest state; a replay repairs per-quarter flags and writes exact matching result rather than failing falsely or re-advancing pointer. Structured logs include run/execution/attempt, source/ref/raw hash and quarter/generation/candidate for each real transition.

- [ ] **Step 4: Cover CLI regression/replay matrix and green.** Guarded test_etl_cli.py, test_workspace.py and test_cli.py: transform/publish end-to-end, fixture no sender/provider construction, parser-version replay, same completed attempt/no extra writes, changed flags/workset/version/image/config rejection, expired new/completed attempts, crash result object before Attempt update, gated exit10 with active capture stable, persistent conflict9, partial source success/incomplete3, invalid source7, multi-quarter progress, no-op0 and empty0. Retain actual stdout/stderr/result.json/Attempt bytes and commands. Old discover/collect result JSON must decode identically and existing fixture-pack/coordination checks remain effective.

- [ ] **Step 5: Commit owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/commands.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/state.py packages/sec-edgar-ingest/tests/test_etl_cli.py packages/sec-edgar-ingest/tests/test_workspace.py packages/sec-edgar-ingest/tests/test_cli.py
git commit -m 'feat: expose raw-only transform and safe publication commands'
```

### Task 7: Real process, retained-specimen and installed-wheel proof; delivery documentation

**Files:** Create `packages/sec-edgar-ingest/tests/test_etl_processes.py`, `packages/sec-edgar-ingest/tests/etl_proof.py`, `docs/runbooks/sec-edgar-etl-publication.md`, `specs/evidence/sec-filing-index-ingestion/stage-3/verification.md` and proof artifacts under its adjacent `verification/`. Modify `scripts/check-sec-edgar-ingest.sh`, `packages/sec-edgar-ingest/README.md`, `README.md` for new command/read contracts only. Retain planning-reconciliation.json; do not rewrite earlier evidence to remove failures or pending historical statements.

**Interfaces:** Consumes installed commands and public transform/publish/read APIs. Produces test proof driver `main(argv: Sequence[str] | None = None) -> int` with required `--output` and modes `specimens`, `sequence`, `installed`; reports actual paths/versions/platform/argv/exits/hashes. No alternate ETL/commit algorithm. Test process targets import actual modules and independent real local stores.

- [ ] **Step 1: Add real adversarial process tests, capture the first uncovered failure.** Use multiprocessing spawn/barriers and existing network guard; two real publishers independently read the same absent/current pointer before either CAS, add distinct daily sources, then race. A shared observer barrier at publication.before_pointer aligns the first builds, releases exactly once, and does not block the losing publisher's rebuild. Record PIDs, exact base versions/candidate hashes, actual local insert/replace conflict, loser rebuild source set and final capture. Assert final keys equal the union and both updates remain, not merely that both processes exit. Each child has a finite join deadline and retained stdout/stderr; terminate only its own hung test process and report failure.

Additional real forced-exit children die at candidate.after_data, publication.before_pointer, publication.after_pointer and etl_result.after_object. Parent reopens independent stores, asserts old/new complete readable capture, resumes same frozen intent and verifies repair with no extra commit. Gate-race fixture has winner add a key that the loser's closed quarterly replacement omits; loser must rebuild and become awaiting_approval. Retain unreferenced losing candidate files and actual reader hashes. Never infer a real process race from a scripted conflict alone. Run test_etl_processes.py guarded and retain red for missing proof/boundary behavior before fixes.

- [ ] **Step 2: Implement retained-receipt and raw-only sequence proofs.** `specimens` reads the retained Stage 1 matrix, each inspection JSON's original_path relative to its stage root, verifies original hash/byte count and selected family, then invokes the actual parser on all ten complete receipts. Compare source-row counts, filing-date min/max, selected inspected rows, duplicate-key outcomes and quarter counts. A failing specimen blocks range claims; preserve its row/reason and do not patch retained bytes or weaken the parser to pass. Compact synthetic legacy goldens remain clearly separate from observed legacy evidence.

`sequence` seeds canonical stored inputs using actual fixture Source/Binding/workset codecs; it then executes actual transform, publish, read, repeat/no-op, fixture parser-v2 raw replay, cross-quarter daily addition, open absence and closed withdrawal gate against durable stores. Verify no collector constructors/transport requests and unchanged raw/pins; inspect complete manifests and per-quarter state. Exact acquisition-provenance config remains origin; separate transform configs use row-parser aliases. Record logical identity/output determinism separately from original ZIP receipt bytes and worker-image provenance. No download, SEC collection sequence or Azure auth is required.

Proof SHA inventory is computed from actual final files with relative safe paths, byte lengths and SHA256; exclude itself to avoid circularity. Retain failed/intermediate runs under distinct output directories, not overwriting success-looking summaries. Every command's output includes actual exit/platform/runtime/dependency versions and explicit `all22_stage7_checks: reserved`.

- [ ] **Step 3: Build and prove the installed wheel entirely offline.** Run the prescribed check once after final implementation change, with full output retained:

```bash
scripts/check-sec-edgar-ingest.sh
```

Expected: acquisition and ETL tests/process fixtures OK, wheel/sdist build exit0, four-command help, module version, compileall and whitespace exit0. The script already invokes the guarded runner; expand CLI help assertions in tests instead of adding a network-capable test path. Preserve accepted CRLF fixture handling with `git -c core.whitespace=cr-at-eol diff --check`.

The installed mode builds/uses the produced wheel, creates a temporary isolated uv venv using the already selected native Python, installs that exact wheel and cached lock pins with `uv pip install --offline`, runs commands with cwd outside the repository and PYTHONPATH removed, and imports sec_edgar_ingest from site-packages. Fail if source checkout import leaks in. Reuse the Stage 2 proof's cached-wheel install/readback pattern; do not copy its old approval-pending status as current. Compare installed wheel source bytes/version and retained wheel hash to the reviewed tree.

Concrete driver commands once it exists:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py specimens --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/specimens
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py sequence --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/sequence
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/etl_proof.py installed --output specs/evidence/sec-filing-index-ingestion/stage-3/verification/installed
```

Expected all exit0; actual row counts and native runtime come from inspected output, not invented future numbers. Full Linux worker/ADLS/HNS/identity/ETag behavior and memory/runtime/scratch stay Stage 7. Extend the guard into every proof child; cache/build tooling is offline and Python sockets/auth remain denied.

- [ ] **Step 4: Write and exercise the reader/replay/gate runbook.** Include exact storage reference shapes and commands, pinned origin vs transform context, null accession/date-to-quarter behavior, no-op/force semantics, pointer-capture Python example, files/checksums validation, per-quarter atomicity, safe post-CAS repair, partial progress and awaiting_approval exit10. Show replay selecting an exact retained snapshot workset and configuring a supported current parser without recollection. Show capture/read:

```python
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
capture = capture_quarter('2026Q4', objects, EtlState(store))
if capture is None:
    raise RuntimeError('quarter has no published generation')
for row in read_quarter(capture, objects):
    print(row.cik, row.archive_path)
```

`objects` and `store` are the selected open_stores outputs established in the runbook's configuration example; saved capture refs are sufficient for subsequent reproducible reads. Explain gate inspection using candidate ref and exact source hash; Stage 3 supplies no approval mutation, pointer rollback command or success claim for a gated run. Reserve those operations for later stages. Update README from acquisition-only scope to completed transform/publish capabilities only after proof passes. Verification report links full commands/logs/fixtures/file manifests/process outcomes/reviews, explicitly preserving historical failures and reserved integrated checks.

- [ ] **Step 5: Inspect proof artifacts and commit owned files.** Parse every retained command exit/full log, inspect real CAS and process kill/repair traces, verify every proof SHA record and installed source equality. Recheck primary preservation receipt and planned source scope. Fix implementation failures with a new covering test; rerun covering checks only when changes justify it. Then explicitly add this task's files/artifacts and commit:

```bash
git add packages/sec-edgar-ingest/tests/test_etl_processes.py packages/sec-edgar-ingest/tests/etl_proof.py scripts/check-sec-edgar-ingest.sh docs/runbooks/sec-edgar-etl-publication.md packages/sec-edgar-ingest/README.md README.md specs/evidence/sec-filing-index-ingestion/stage-3/verification.md specs/evidence/sec-filing-index-ingestion/stage-3/verification
git commit -m 'test: prove replay publication races and installed ETL recovery offline'
```

## Self-review and acceptance coverage

The planner runs this check itself; it is not a subagent review dispatch. Planning validates artifacts and existing evidence, not the unimplemented future tests.

| Stage 3 spec | Plan coverage |
|---|---|
| §1 authoritative reconciliation/local preservation/later-stage consistency | Preflight + immutable planning receipt; no roadmap edit |
| §§2–3 bounded scope/exact pins/offline constraints | Global constraints + Task 1 preflight + Task 7 proof boundaries |
| §4 exact origins/version identities/logical storage/accepted bindings | Tasks 1, 3, 6; compatibility regression fixtures |
| §5 strict parser/canonical and original observations | Tasks 1–3; Task 7 full retained-specimen proof |
| §6 precedence/replay/source union/deltas/gate | Tasks 3–5; first-publication and CAS gate-race tests |
| §7 conditional commit/reader/crash repair/per-quarter progress | Tasks 5–7, including real competing processes and result crashes |
| §8 applicable errors/test/review/build/evidence gates | Every task's guarded red/green + Task 7 full/installed proof |
| §9 unticked/proposed/approval-first execution/completion chain | Status + preflight + handoff below |

At approval presentation, confirm every task has explicit files, consumed/produced interfaces, actionable tests/code/commands and expected outcomes. Scan for unfinished placeholders, unresolved method/type names, inconsistent path/table/version fields and misleading future PASS claims. Check docs' local link targets, every source fixture hash, current protected-file preservation and no Stage 3 checkbox change. New algorithm parameters in this plan remain proposed pending approval; they do not revise accepted parent safeguards.

After actual execution resolves final whole-branch findings, run writing-plans' resolve-before-defer gate and completion protocol. Do not stamp COMPLETE just because tests pass while an owner-dependent blocker remains. Mark executed steps/deviations, reconcile any existing deferred items, record the final implementing revision/evidence, retire only this Stage 3 spec/plan when their gate passes, and publish its authoritative completed stamp before any authorized local checkbox. Revalidate Stages 4–8 without planning them. Use finishing-a-development-branch for deliberate merge/PR/cleanup and remove only the task's authorized isolated worktree. A later Stage 4 transition is owner-initiated by another roadmap resume.

## Approval and execution handoff

Stop here. Present this Stage 3 implementing spec and Plan 3 for Lowell Mason's approval; no code has been implemented, no execution choice is presumed and all live-access authorizations remain closed.

After approval, recommend a fresh session against the exact saved plan. Default execution is subagent-driven-development with per-task Spec/Quality review and final whole-branch review; inline executing-plans is available if the owner chooses it. The execution session performs its own isolation/protection preflight, offline dependency proof and task tests. Neither approval nor the passage of time grants live access or authorizes Stage 4. Keep the local roadmap unchanged and Stage 3 unticked until its actual completion boundary.
