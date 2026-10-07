# Task 5 — pointer publication, pinned readers, repair

Implemented in managed worktree `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`, branch `codex/sec-edgar-stage-3`, starting at `e460df72b72f090762f382136cbb9e7689635d21`. No primary checkout, old package, dependency pins, adapters, acquisition state, authorization, network, approval handling, workflows, deployment or later-stage work changed. No subagents spawned.

## Public interfaces and behavior

```python
# etl/publication.py
publish_quarter(quarter: str, incoming: tuple[ObservationRef, ...], context: RunContext,
                settings: Settings, objects: ObjectStore, state: EtlState, *,
                observer: BoundaryObserver | None = None) -> PublicationResult
repair_publication(quarter: str, objects: ObjectStore, state: EtlState) -> None
pointer_value(candidate: Candidate) -> dict[str, object]
unchanged_inputs(quarter: str, existing: GenerationManifest | None,
                 incoming: tuple[ObservationRef, ...], context: RunContext) -> bool
# etl/reader.py; capture_from_pointer also imported by publication.py
capture_from_pointer(row: Versioned) -> GenerationCapture
capture_quarter(quarter: str, objects: ObjectStore, state: EtlState) -> GenerationCapture | None
read_quarter(capture: GenerationCapture, objects: ObjectStore) -> Iterator[IndexRow]
validated_manifest(capture: GenerationCapture, objects: ObjectStore) -> GenerationManifest
```

Publication validates pinned context, all original incoming immutable observation references and their bytes, and the current pointer's exact fields/address/hash/length/fingerprint. It validates complete current and proposed generations with Task 4's public validator, including the exact retained-base sidecar, selected observation provenance, key membership and complete deltas. CAS uses the actual revision returned by state, with maximum CAS_ATTEMPTS=5. Both insert and stale replace conflicts reread the real winner and rebuild using the unchanged original incoming pins. There is no global lock or acquisition lease. A changed winner may make a retry gated; it then remains awaiting_approval. `_now() -> datetime` is a patchable UTC clock; production supplies datetime.now(timezone.utc). Deadline expiry before work, before CAS, during candidate construction, and after races cannot commit stale output.

No-op selection recomputes the full selected source set, aligned versions, mode, quarterly membership authority and the existing retained basis. It never fingerprints only the incoming workset or adopts the current generation as a new retained basis. It repairs existing memberships without rewriting the pointer. Forced observation replay adopts immutable output and remains unchanged. New parser versions cause Task 4 to replay contributors.

Reader capture reads one pointer and fully verifies the immutable manifest and candidate. Reader consumption never looks up a latest pointer, globs, or falls back. It validates every explicit file and source before yielding, then finishes a second verified data read into a temporary SQLite spool before exposing the first row. Late file/count/schema failures therefore leak no accepted partial result; Python memory does not scale with quarter row count. Old captures remain independently readable after pointer advancement. Gated manifests cannot be accepted as current by capture/read/repair.

## Processing repair fields for Task 6

Only `EtlState.record_publication` and `_record_membership` were changed in state.py. Existing method signatures remain unchanged. Receipts are written only for selected refs whose `quarter_counts` contains a positive count for the committed quarter. A source appearing in the selected source list with no rows in that quarter gets no receipt for it.

`Processing.value['publications']` retains the existing shape `{quarter: {generation_id: receipt_key}}`. `Processing.value['published']` is a new recoverable boolean set during membership repair: true only when every output quarter in that immutable ref's quarter_counts has a publication membership backed by the receipt written before the membership update. Before the first repair, transformed records may have no `published` field; callers must treat absence as false (`value.get('published', False)`). One committed quarter of a two-quarter ref sets false; the second sets true. Historical membership generations remain present. CAS retries reread and merge the latest whole Processing value, retaining output refs and newer quarter/generation memberships. The original `observation` field is never rewritten. Publication flags/receipts remain indexes, never commit authority.

repair_publication captures and fully validates the active manifest, then records its idempotent receipts. If a newer pointer wins during repair, the captured manifest was still committed; recording its historical memberships cannot roll back the newer memberships. A crash after pointer update is repaired without another pointer update/change event. Missing/corrupt current output fails before repair accepts it. Low-level record_publication expects a validated committed manifest from its caller, preserving Task 1's facade contract; the public repair/publication paths enforce this.

## Files and fixture helper

- Created `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/publication.py`.
- Created `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py`.
- Modified only repair-method lines in `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py`.
- Created `packages/sec-edgar-ingest/tests/test_etl_publication.py` (22 tests at initial covering green).
- Added `seed_observation(objects, state, context, settings, *, period='2026Q4', kind='quarterly', rows=None, seconds=0)` in permitted support_etl.py. It uses real ZIP/raw bytes, fixture Source/Snapshot and public transform_member to seed first and subsequent golden generations. Existing seed_snapshot and etl_context unchanged. No test-only production implementation.

## TDD and verification evidence

Every invoked test command uses `uv run --offline --frozen` and the existing tests/network_guard.py before tests import. Cached accepted pins only. Full command argv/cwd/stdout/stderr/exit (plus proof environment where applicable) are retained as distinct JSON files under `.sdd/3-sec-filing-index-ingestion-stage-3-spec/task5-evidence/`. Runner source is retained there as run.py and itself installs the guard before spawning the guarded child.

- red-interfaces.json: 2 tests, existing stale CAS passed; missing publication/reader assertion failed as prescribed.
- red-behavior.json: actual local-store behavioral tests failed only because the publication/reader implementation was absent.
- green-attempt-1.json: 11/12 pass; one test compared FrozenMapping to dict, corrected via detached mapping.
- red-incoming-and-matrix.json: exposed forged incoming ObservationRef accepted on no-op; two fixture errors also retained (40-ref descriptor was below 64 KiB, and canonical schema had no metadata to remove). The fixtures were corrected to 50 refs / unexpected schema metadata.
- green-core.json: 18 publication tests passed, including immutable incoming-ref verification.
- red-deadline.json: real missing behavior demonstrated when candidate construction raises deadline TimeoutError.
- green-covering.json: **65 tests passed**, 36.791 seconds, exit 0: 22 publication + 31 catalog + 12 storage.

The final covering invocation at this milestone was:

```sh
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_publication test_etl_catalog test_etl_storage -v
```

The runner was invoked with SEC_EDGAR_TASK5_PROOF_DIR set to the absolute task5-evidence/publication-proof directory, retained in green-covering.json. No broad full suite was run; it remains controller/Task 7 work after the last implementation change.

## Matrix covered

Independent missing-pointer insert and stale-replace races both force real local conditional conflicts and rebuild from winner sources. Winner business fields beat the losing incoming fields; new incoming keys survive union. Gate is re-evaluated after winner advance. Five persistent conflicts and deadlines cannot advance the pointer. Repeated no-op, retained-basis no-op, forced transform replay, new parser replay, old captures and orphan losing data are checked. Pointer shape/address/hash/fingerprint, gated pointer, absent/truncated manifest/data/changes, hash-consistent wrong schema/count/quarter/duplicate keys all fail before first accepted row. The seven named interruption points are candidate.after_data, candidate.after_changes, candidate.after_manifest, candidate.after_validation, publication.before_pointer, publication.after_pointer, publication.after_repair; a separate inside-repair interruption leaves committed pointer and receipt recoverable. Multiquarter partial/full repair, stale repair and a real competing-quarter membership CAS preserve newer state and output references. Acquisition Source rows remain untouched.

The pinned SDK mock uses real Azure Table/Blob client serialization and status translation; no sockets/auth provider activity occurs. It verifies insert 409, conditional replace 412, actual ETags, ActivePointers routing, a verified 73,739-byte Candidate state descriptor, and readback of a pointer referencing a 73,278-byte real manifest. Existing storage coverage additionally checks 71,822-byte ActivePointers payload descriptors.

## Self-review and limits

Reviewed the owned diff against each brief step, actual state contracts and reusable Task 4 validation. Applied clean-code N1/N4 names for captures/selected sources, G25 reuse of CAS_ATTEMPTS, G30/G34 cohesive pointer/reader/repair boundaries, C3 explanation of the pre-yield disk spool, T1/T5/T6 boundary and adversarial coverage. No adjacent cleanup. Work preserves duplicate-conflict refusal and the accepted exact pins.

Validation deliberately rereads immutable data several times. Native tests establish correctness on this machine, not Linux amd64/Python 3.14.8 worker memory/runtime/scratch or deployed capacity. Native/all-22 historical evidence and final reconciliation remain controller/Task 7. Previously established retained historical source duplicate conflicts remain independent blockers to the eventual Stage 3 stamp; this implementation does not suppress them. Evidence objects/report are ignored local development evidence retained indefinitely, not shipped source.

## Actual retained immutable proof identities

- Capture `3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933` (2026Q4), manifest `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/manifest.json`, SHA-256 `96c0f0ac4a09fa43d1140753c37a218526fe14498db16663d2332650e9f5e724`, 4045 bytes; 2 verified rows.
  - data: `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/part-00000.parquet`, SHA-256 `7b996abadf0810f6edad025670f888a05f3b687bb6ade6fa6732b382ec7d0fba`, 3508 bytes / 2 rows.
  - changes: `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/changes.parquet`, SHA-256 `ee32ea27dfe6af556f69d10144c9b0175c3899a465a364fe8bb4e4acecbb2e83`, 6715 bytes / 2 rows.
- Capture `a6494c1deb84c13b01803b15240b4be1640ea6d8d9e66ba137c20a3c6c1e9c0c` (2026Q4), manifest `curated/sec/filing_index/year=2026/quarter=4/generation=a6494c1deb84c13b01803b15240b4be1640ea6d8d9e66ba137c20a3c6c1e9c0c/manifest.json`, SHA-256 `3829a4d5a27394ebec52ee8870118e53f8eb45706922166eda6c0dfccc0f8ef8`, 5560 bytes; 3 verified rows.
  - data: `curated/sec/filing_index/year=2026/quarter=4/generation=a6494c1deb84c13b01803b15240b4be1640ea6d8d9e66ba137c20a3c6c1e9c0c/part-00000.parquet`, SHA-256 `265d979424b257ef4c1b9a5df3e6b0cc56aace030ede9b3bc3e31b4a979a8bbc`, 3634 bytes / 3 rows.
  - changes: `curated/sec/filing_index/year=2026/quarter=4/generation=a6494c1deb84c13b01803b15240b4be1640ea6d8d9e66ba137c20a3c6c1e9c0c/changes.parquet`, SHA-256 `9a8ac96340cb0848d2caf88ae284c825de134526c322797ee0376a39c790be07`, 6610 bytes / 1 rows.
- Capture `f939f9cd7dd44b64577796fca24ea19abd2d1e3ca4e389d6bbc5f1009c032857` (2026Q3), manifest `curated/sec/filing_index/year=2026/quarter=3/generation=f939f9cd7dd44b64577796fca24ea19abd2d1e3ca4e389d6bbc5f1009c032857/manifest.json`, SHA-256 `c6c26e5651b391ae9cdb5ea13ba52bfd2e2351b87ace2bfa4dbd84d33a03309c`, 2633 bytes; 1 verified rows.
  - data: `curated/sec/filing_index/year=2026/quarter=3/generation=f939f9cd7dd44b64577796fca24ea19abd2d1e3ca4e389d6bbc5f1009c032857/part-00000.parquet`, SHA-256 `0121f6fe903507d11552de931a2e6cb28d936ef949132a01e3dff12c61e897a2`, 3437 bytes / 1 rows.
  - changes: `curated/sec/filing_index/year=2026/quarter=3/generation=f939f9cd7dd44b64577796fca24ea19abd2d1e3ca4e389d6bbc5f1009c032857/changes.parquet`, SHA-256 `41567a20769c579589997f2ee4ab027a2812f813f1a12298a2f0d608dd50d880`, 6610 bytes / 1 rows.

Gated candidate: `worksets/sec/candidates/sha256=3451a13f1a2e83240601670175f5baa74609e675807da8f6c660b317f1863268/candidate.json`.

Actual index counts: Candidate=1, Processing=3, PublicationReceipt=4, QuarterPublication=2, Source=0.

Full exact records/readbacks are in task5-evidence/publication-proof/proof.json and immutable objects beneath its objects directory. Proof JSON SHA-256: `c149e234e28afaaedb5b5595758070ee42073b466a8d9afd5921da264c98f482`.

## Controller-approved conflict-evidence convention

The plan's control-loop example returned null manifest fields on conflicts, but the brief also requires latest attempted candidate/race evidence in command gaps. The controller approved preserving the last attempted `candidate.manifest_ref` in `PublicationResult.manifest_ref` for `outcome='publication_conflict'`. Its `generation_id` and `candidate_ref` remain null for a clear losing candidate. Before any candidate is available, manifest_ref remains null. This reference is an **uncommitted attempted artifact**, never a current capture or published-output claim. Published/unchanged retain their committed capture semantics; awaiting_approval retains its gate candidate reference. Task 6 must put this attempted reference in Error.details/command gaps and its strict result validation must distinguish conflict evidence from committed captures.

Retained `red-conflict-evidence.json` proves two missing behaviors: exhausted five-CAS retry and deadline expiry immediately after a lost CAS both discarded the attempted manifest. `_conflict_result` centralizes the corrected outcome-specific serialization. The subsequent final covering run is recorded separately as `green-final-covering.json`. No public record fields or call signatures changed.

## Final covering verification

`green-final-covering.json`: **66 tests passed**, 36.646 seconds, exit 0 (23 publication, 31 catalog, 12 storage), after the last implementation change. Exact command remains `uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_publication test_etl_catalog test_etl_storage -v`. No source/test changes after that green. The final run also reverified the identical SDK large descriptor and pointer hashes. The retained publication-proof from the earlier green remains unchanged; conflict-evidence serialization does not change any of its published/captured/repair artifacts.

Commit: `1d14c9ceee330affd5ab961974932f2f09782f1e` — `feat: commit quarter pointers with conflict rebuild and crash repair`. Only the five owned paths staged and committed. Exact stage/commit/check argv and results are retained as stage.json, staged-check.json, staged-names.json, commit.json, commit-sha.json; owned.diff is the exact reviewed diff.

## Review Minor M1 — explicit late spool fault regression

The reviewer correctly observed that the earlier corruption/count tests failed during initial candidate validation. Added `test_late_spool_failure_exposes_no_row_after_successful_validation` using real seeded raw/observation/generation objects, a real committed capture, production validated_manifest, and the actual production data iterator. A delegating boundary injector records successful validation, yields one real data row into the production SQLite spool, then raises OSError on the subsequent iteration. The first external `next(read_quarter(...))` raises that injected error; the test asserts the validation/real-row/failure order and proves the original two-row immutable capture remains readable afterward. It uses no fixed materialization call counts or alternate reader algorithm. Production reader code was correct and remains unchanged.

Only `tests/test_etl_publication.py` changed. Regression is expected green against existing correct behavior; no speculative production fix. Applied T5/T6 to distinguish prevalidation failures from postvalidation spool failures.

Verification: `uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py test_etl_publication -v` — **24 tests passed**, 6.071 seconds, exit 0. Full argv/cwd/stdout/stderr/exit retained at `minor1-evidence/green-publication.json`; guarded runner source is `minor1-evidence/run.py`. Catalog/storage unchanged and not repeated, per controller instructions.

M1 commit: `1ec404a29f945448c735efe712526edc41efaacc` — `test: cover late quarter reader spool failure`. Only the test path staged/committed; exact diff and Git evidence retained under minor1-evidence.
