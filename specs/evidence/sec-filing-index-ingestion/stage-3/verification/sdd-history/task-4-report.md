# Task 4 implementation report

Status: DONE; isolated worktree `/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar`, branch `codex/sec-edgar-stage-3`, base `1f6726d66f7cd13af377c2cd8f9e3d52c741e99b`.

## Scope and interfaces

Created only `etl/catalog.py`, `etl/manifest.py`, and `tests/test_etl_catalog.py` in `packages/sec-edgar-ingest`. Existing `tests/support_etl.py`, `etl/state.py`, contracts, storage, transform and parser are unchanged. No primary-checkout modifications, pointers, approvals, acquisition, live clients, credentials, network, pins, or deployment changes.

Actual required signatures:

```python
select_sources(existing: tuple[ObservationRef, ...], incoming: tuple[ObservationRef, ...]) -> tuple[ObservationRef, ...]
source_fingerprint(quarter: str, sources: tuple[ObservationRef, ...], *, mode: str, membership_source: ObservationRef | None, retained_from_generation: str | None) -> str
build_candidate(quarter: str, previous: GenerationCapture | None, incoming: tuple[ObservationRef, ...], context: RunContext, settings: Settings, objects: ObjectStore, state: EtlState, *, observer: BoundaryObserver | None = None) -> Candidate
read_manifest(capture: GenerationCapture, objects: ObjectStore) -> GenerationManifest
validate_candidate(candidate: Candidate, objects: ObjectStore) -> None
```

`source_fingerprint` is implemented in manifest and re-exported by catalog to avoid a circular import. `iter_file_rows(FileRef, ObjectStore)` streams schema/hash/length/count-verified Parquet dictionaries (date32 values remain Python dates); Task 5 can construct `IndexRow(**value)` from data rows. `validate_candidate_content` validates the complete immutable output before the gate can be staged; public `validate_candidate` additionally requires exact gate bytes. `generation_base`, `gate_ref`, and `generation_identity` centralize layout/identity. No state facade changes are needed.

## Implementation

The prescribed source revision selection keeps newest receipts, rejects equal-time distinct snapshots, adopts an existing same-hash snapshot, detects metadata and observation conflicts, and preserves all prior selected contributors. Version-mismatched contributors replay their exact raw snapshots through the real transform. Sources and fingerprints are deterministically sorted. Acquisition origin contexts are not required to equal current processing contexts.

SQLite stores observations, active/proposed rows, and changes. Ranked source rows prefer quarterly fields, then source period, receipt and source ID; membership authority is restricted to a quarterly source for the target filing quarter. Mode uses the attempt-pinned publication date. Closed authoritative candidates withhold daily-only keys and gate withdrawals. Open absence and closed daily-only absence retain exact old rows with unresolved records. Empty target-quarter quarterly membership is quarantined as invalid_source. Off-period rows remain retained/reported in ObservationRef.quarter_counts and can contribute fields without falsely asserting membership.

Data and full before/after changes stream in batches of 8192 using fixed explicit Arrow schemas, Parquet 2.6/snappy, no dictionaries. Tests inspect 8193-row outputs as exactly two 8192/1 row groups. Data is ordered by (cik, archive_path); changes by (cik, archive_path, change_type). Business-field changes and provenance-only refresh counts are distinct. File readback precedes the manifest; complete validation precedes every gate index write. Four named boundaries support durable interruption/retry.

Validation checks exact canonical manifest capture hash/length/identity, source-set fingerprint, files/layout/schemas/hashes/counts/ordering, exact source observation manifests and rows, canonical row origin and winning rank, complete selected keys, membership, change shapes/after rows/business differences, retained dependency and exact gate contents. Immutable existing outputs preserve their original image. No-op compares fingerprints using the prior retained basis before creating a base-bound new identity.

## RED / GREEN evidence

Every actual command result preserves argv, cwd, exit, stdout and stderr under `task4-evidence/`.

- `red-missing-catalog.json`: prescribed missing-module RED, exit 1.
- `green-attempt-1.json`, `green-attempt-2.json`, `green-core.json`: failed fixture setup attempts retained without overwriting; exact ZIP_DEFLATED, CRLF, quarterly Filename header, daily compact-date and labelled clock-override contracts were corrected in tests only.
- `green-core-corrected-fixtures.json`: 6 tests, exit 0.
- `red-matrix.json`, `red-strict-validation.json`: exposed missing gate validation, adopted-candidate boundary notification and invented-row acceptance; fixture-only date regex/source constructor/image-config mismatches corrected.
- `green-matrix-1.json`: 20 tests, exit 0.
- `red-precedence-validation.json`: valid-source loser-row tampering reproduced, exit 1.
- `green-matrix-2.json`: 25 tests, exit 0; actual immutable proof retained.
- `red-missing-selected-key.json`: self-review missing-key tampering reproduced, exit 1.
- `green-final.json`: 26 tests, exit 0, 30.044 seconds.

Final command:

```text
uv run --offline python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_catalog.py -v
```

The guard installs before application imports. Evidence output override: `SEC_EDGAR_CATALOG_PROOF=<worktree>/.sdd/3-sec-filing-index-ingestion-stage-3-spec/task4-evidence/generation-proof`. Final proof has 19 actual immutable objects; `artifact-ledger.json` hashes every retained proof file. This is native macOS arm64/Python 3.14.0/PyArrow 25.0.1 development verification, not Stage 7 Linux amd64/Python 3.14.8/all22 capacity evidence. Final cross-task checks remain Task 7's responsibility.

## Retained dependency implementation detail

Controller confirmed keeping the public manifest contract unchanged. For any retained absent rows, the generation contains create-once `<generation-prefix>/retained-base.json`, canonical exact `GenerationCapture.to_mapping()` with quarter, generation_id, manifest_ref, manifest_sha256, manifest_bytes. It is written before the manifest; adoption validates the same sidecar. Its quarter and generation must match `retained_from_generation` and the candidate's base. Validation reads only that exact hash/length-bound manifest and explicit files. Missing, noncanonical, corrupt or mismatched sidecars fail. The sidecar also supports conservative closed daily-only retained absences. This supporting immutable artifact is an implementation deviation from the listed three output files, not a public contract extension. Task 5 should rely on `validate_candidate`; no mutable latest lookup is introduced.

## Concrete immutable proof

### initial

Generation `3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933`; base `None`; fingerprint `ecc713dd3f451209b355e27d461cced181e959b1eb1f266b016bd57bda385863`.

Manifest `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/manifest.json`; SHA-256 `96c0f0ac4a09fa43d1140753c37a218526fe14498db16663d2332650e9f5e724`; 4045 bytes.

- data: `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/part-00000.parquet`; SHA-256 `7b996abadf0810f6edad025670f888a05f3b687bb6ade6fa6732b382ec7d0fba`; 3508 bytes; 2 rows.
- changes: `curated/sec/filing_index/year=2026/quarter=4/generation=3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933/changes.parquet`; SHA-256 `ee32ea27dfe6af556f69d10144c9b0175c3899a465a364fe8bb4e4acecbb2e83`; 6715 bytes; 2 rows.

### retained

Generation `3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b`; base `3a193a609b62f817bed0cbd9a25d3e589dbcd94c308fee9128c51ac5ae7e0933`; fingerprint `e4cd03c77425ffa8b17546a9c27057c7474b548fb17f9d70af8388c3af851cb5`.

Manifest `curated/sec/filing_index/year=2026/quarter=4/generation=3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b/manifest.json`; SHA-256 `7b5ecd453084b617c081f3c79c82072ef7d43afe95628b3fd7980c6034e1b641`; 4169 bytes.

- data: `curated/sec/filing_index/year=2026/quarter=4/generation=3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b/part-00000.parquet`; SHA-256 `9a3dd57b5233b8f6115108e0a63e973b03e3ae4c6a51facccd02fe8a79f0540f`; 3570 bytes; 2 rows.
- changes: `curated/sec/filing_index/year=2026/quarter=4/generation=3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b/changes.parquet`; SHA-256 `4950434663fe501e729ea1e7b046444b12fb45ebaf2f471eddd56021206663f6`; 8601 bytes; 2 rows.

### gated

Generation `01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc`; base `3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b`; fingerprint `9bf89e54b0c059f5d39b48a5e4238f716b38130a3f0db84b4683a334697647f7`.

Manifest `curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/manifest.json`; SHA-256 `7b6a5c484be1a5aa577f9628c6112b6869dbbdcaf39f25c1dbd70b8dbd1827e5`; 4121 bytes.

- data: `curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/part-00000.parquet`; SHA-256 `17928e2ef90800e199237d1649582048fc564d2a26e625994a6265e66f2d0e75`; 3437 bytes; 1 rows.
- changes: `curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/changes.parquet`; SHA-256 `ba63676e658bb83e15337b4f09cf0e6b16ab64084c88546072bd2793ef852d04`; 6842 bytes; 1 rows.

Gate `worksets/sec/candidates/sha256=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/candidate.json`; exact byte SHA-256 `59dcddb403b88c8845d73e814a6416e94fa226e489ec0ec318d8fc327a0307a8`. Complete canonical selected-source-set SHA-256 `6d0802a59ca10ca9d396840f11ff6acad94cfc84ed866ea51c34cf9df21c7f66`. Full candidate mappings/source refs and byte hex are in `generation-proof/proof.json`; all objects remain under `generation-proof/objects/`.

## Self-review and concerns

Checked every required Task 4 public signature and brief step, actual output ordering and row groups, isolation, lack of pointer writes, exact gated-base bindings, and immutable adoption. Self-review identified and fixed semantic tampering gaps using separately retained RED/GREEN tests. No production stubs or alternate test catalog algorithm. Whole-quarter data lives in SQLite, with bounded Python Arrow batches; only the small selected-source set is a Python mapping/tuple.

Applied clean-code guidance: named BUSINESS_FIELDS and reused BATCH_ROWS/PARQUET_VERSION (G25); separated source selection, disk resolution, file emission, gate staging and manifest verification by cohesive responsibilities (G30/G34); explicit retained-generation and source-fingerprint names (N1/N4); retained why-oriented immutable dependency documentation (C3); adversarial equal-time, empty-membership, future-quarter, row-group, crash, hash-valid tampering and no-op tests (T1/T5/T6). No adjacent cleanup performed.

No unresolved functional blocker. Validation deliberately rereads immutable data several times; performance/worker sizing remains unmeasured here and belongs to Stage 7. The support fixture file and state facade required no modifications. `.sdd` evidence/report are locally retained ignored development evidence, as in preceding tasks; the explicit source/test commit excludes unrelated files.

Commit and exact diff metadata are appended after the owned-file commit below.

Commit: `9f47166ca318b0a9f8e8cf6bb428e49bfb8e4486` (three owned files; 985 insertions). `task4-evidence/owned.diff` contains the exact staged diff; `diff-check.json` records exit 0, `diff-stat.json` records exact file scope. `commit.json` retains actual commit argv/stdout/stderr/exit.

## Review round 1 remediation: I1 (supersedes earlier delta-validation claim)

The fresh reviewer identified that closed withdrawal candidates had no retained dependency and the validator trusted their supplied delta counts. Verified four failures before implementation: removing the complete withdrawal change file while recomputing all hashes/counts and clearing the gate; omitting a business update; inventing its before value; suppressing provenance_refreshed. The initial report's claim of strict complete change validation was too broad; this fix closes that concrete gap.

Every noninitial generation now writes its exact supplied base capture to `<generation-prefix>/retained-base.json` before the manifest, including candidates whose `retained_from_generation` is null. The sidecar name is preserved; its scope now covers every base, while the public `retained_from_generation` field keeps its original absent-key meaning. `_base_manifest` requires canonical exact fields, matching quarter/base_generation_id, captured SHA-256/length and explicit verified files. The approved public records and signatures remain unchanged. Existing candidates missing this required capture fail closed; no fallback, migration, pointer lookup or mutable latest is used.

The validator loads base rows, output rows and actual changes into SQLite and independently recomputes every expected change over the sorted union of base/output keys. It compares exact full before/after rows and change types/reasons, checks added/updated/withdrawn/unresolved sets and all five counters including provenance_refreshed, rejects duplicate or extra change keys, and checks that unwithdrawable absences preserve base rows. No whole-quarter Python collection is introduced. Both direct validation and immutable adoption reject suppressed withdrawals before gate/index acceptance. Existing membership/rank/source verification and the four interruption boundaries remain covered.

New regression tests: suppressed withdrawal with consistent hashes and clear gate (also retries immutable adoption); omitted update; forged before value; forged provenance count; missing/noncanonical/mismatched base capture for a candidate with no retained absent rows. Tests use actual immutable fixture stores and Parquet files; the tampering helper only changes test bytes and references and contains no alternate catalog builder.

Evidence, all separate from original evidence:

- `task4-fix1-evidence/red-delta-validation.json`: frozen/offline/guarded focused RED, 5 tests with four expected failures, exit 1.
- `task4-fix1-evidence/green-focused.json`: same five tests, exit 0.
- `task4-fix1-evidence/green-covering.json`: full catalog suite, 31 tests, exit 0, 31.025 seconds; full command/argv/cwd/env/stdout/stderr retained.

Exact covering command:

```text
uv run --offline --frozen python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_catalog.py -v
```

Proof override targets only `task4-fix1-evidence/generation-proof`; the original evidence directory is untouched. `prior-artifacts-unchanged.json` verifies every original proof artifact against the original SHA-256/length ledger. Fresh complete candidates and 20 actual immutable objects are retained under `task4-fix1-evidence/generation-proof`, with every file hashed in its `artifact-ledger.json`. Native development verification only; Stage 7 deployment/capacity limits unchanged.

Fresh exact gated proof:

Generation `01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc`; base `3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b`; source fingerprint `9bf89e54b0c059f5d39b48a5e4238f716b38130a3f0db84b4683a334697647f7`. Manifest `curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/manifest.json` SHA-256 `7b6a5c484be1a5aa577f9628c6112b6869dbbdcaf39f25c1dbd70b8dbd1827e5`, 4121 bytes. Gate `worksets/sec/candidates/sha256=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/candidate.json` SHA-256 `59dcddb403b88c8845d73e814a6416e94fa226e489ec0ec318d8fc327a0307a8`. Selected-source-set SHA-256 `6d0802a59ca10ca9d396840f11ff6acad94cfc84ed866ea51c34cf9df21c7f66`.

- `generation-proof/objects/curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/changes.parquet`: `ba63676e658bb83e15337b4f09cf0e6b16ab64084c88546072bd2793ef852d04`, 6842 bytes.
- `generation-proof/objects/curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/manifest.json`: `7b6a5c484be1a5aa577f9628c6112b6869dbbdcaf39f25c1dbd70b8dbd1827e5`, 4121 bytes.
- `generation-proof/objects/curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/part-00000.parquet`: `17928e2ef90800e199237d1649582048fc564d2a26e625994a6265e66f2d0e75`, 3437 bytes.
- `generation-proof/objects/curated/sec/filing_index/year=2026/quarter=4/generation=01804c6b200d05bdc7bbfad611dfd0d4fcd6830c5776821896fe9b049ba7dadc/retained-base.json`: `91a6f63e579e81644613678f86aeb894977a6fd89791872da1096f8e3a62e1cf`, 362 bytes.
- `generation-proof/objects/curated/sec/filing_index/year=2026/quarter=4/generation=3aa2c1d70f4748450f37aa74a72d45c3a929de8bde9c722455dada30332d560b/retained-base.json`: `e64bab56f6a3b41081edcb351e4d2630db25edeb421b8f1f6a3e17b5c2fe713a`, 362 bytes.

Self-review: source/context/pins/state/helpers unchanged; only three owned files differ. No network or authentication, no pointer or approval operations, no Task 5 work. Cohesive independent delta verification (G30), explicit base-row names (N1), and adversarial counterexample coverage (T5/T6). No unresolved I1 concern; scoped reviewer confirmation remains the controller's next step. Exact fix diff and commit metadata follow.

I1 fix commit: `e460df72b72f090762f382136cbb9e7689635d21`; three owned files, 145 insertions/13 deletions. `task4-fix1-evidence/owned.diff` and `diff-stat.json` retain exact scope; `diff-check.json` exit 0; `commit.json` retains full commit output.
