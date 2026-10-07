# Task 3 implementation report

Status: DONE
Base: 3b2c03a4f129d88d1bb4cd7f9ada314fb895ad85
Commit: 1f6726d66f7cd13af377c2cd8f9e3d52c741e99b
Worktree: /Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar

## Scope and produced interfaces

Committed exactly transform.py, tests/test_etl_transform.py, and tests/support_etl.py under packages/sec-edgar-ingest. The existing Task 1 EtlState.accept_transform already implements create-or-adopt matching immutable ObservationRef while preserving publication membership; state.py needed no change. This is the only file-plan deviation. Evidence and this report remain under the assigned ignored .sdd directory. No primary checkout, dependency pins, acquisition Settings/registry, old evidence, roadmap, live client, credentials, deployment, or transport was changed or used.

```python
transform_member(source: Source, snapshot: Snapshot, context: RunContext, settings: Settings,
                 objects: ObjectStore, state: EtlState, *, force: bool = False,
                 observer: BoundaryObserver | None = None) -> ObservationRef
transform_workset(snapshot_ref: str, context: RunContext, settings: Settings, objects: ObjectStore,
                  state: EtlState, acquisition: AcquisitionState, *, force: bool = False,
                  observer: BoundaryObserver | None = None) -> TransformedWorkset
read_observations(ref: ObservationRef, objects: ObjectStore) -> Iterator[Observation]
seed_snapshot(root, source, body)  # returns StateStore, ObjectStore, SnapshotWorkset
etl_context(parser_version='fixture-index-parser-v1', command='transform', attempt='etl1')
```

The fixture helper follows the prescribed real source/snapshot codecs and stores, remembers snapshots, and writes exact Binding records through AcquisitionState.bind_once. It closes the unused lease store. Transform contexts use a real current pin date and future deadline; acquisition contexts remain untouched.

## Behavior and boundaries

Every member materializes retained raw bytes and reruns existing received/expanded/envelope/hash/length validation. Retained entity headers apply; original transfer framing does not become replay transport framing. ZIP validation includes full CRC/decompression checks. No mutable latest is read. Workset identity/address, exact reconstructed source membership/context, every Binding identity field, and remembered snapshot metadata are verified before member processing.

Parquet uses the fixed contract schema, 8192-row batches, Parquet 2.6/snappy, no dictionary, and use_compliant_nested_type=False to preserve the specified nested item field name on readback. No run/time/image data enters row bytes. SQLite scratch detects conflicting logical keys across the entire source; identical duplicates remain as separate observations and count toward source_row_count and quarter_counts. distinct_key_count is independent. Full-source local and durable readback verifies bytes, schema, original fields against canonical parsing, provenance, increasing physical lines, conflicting keys, counts and quarter totals before acceptance.

Observation manifests are canonical sec-observation-v1 with exact keys format_version/observation/image_digest and no self-hash. Existing manifests and data must validate before reuse; missing/corrupt accepted data fails closed. Force repeats parsing/readback and compares immutable bytes. Concurrent writers adopt verified identical output, preserving the existing producer image. Crash points follow actual rows, manifest, Processing and workset durability operations. A manifest without Processing repairs without reparsing. Partial transformed worksets retain successful refs and failures; retry reuses successful Processing and creates a new complete workset. Complete empty input is explicit. Transformed worksets use sec-transformed-workset-v1, strict codec roundtrip, content-derived ID and independent full-byte verification.

Failure records retain source/raw SHA/parser/schema/line/reason under the required quarantine error.json address. If the same attempt encounters a different failure, its first error.json remains immutable and the additional error is retained as error-<content hash>.json. Context managers close scratch directories, Parquet readers/writers, parser generators and SQLite connections; read_observations retains scratch until exhaustion/explicit iterator close.

## Retained command evidence

All command evidence is in task3-evidence. Every numbered command has distinct complete argv/cwd/exit JSON and complete stdout/stderr files. All uv invocations use --offline --frozen. Every test and standalone artifact/restart proof installs tests/network_guard.py before application imports. The unittest child also installs the guard before its imports. No dependency resolution/baseline was repeated.

- 01-red and 02-matrix-red: exit 1, expected missing transform module.
- 03-green: exit 1; fixture parser detection incorrectly used optional fixture override object. Corrected to actual local-fixture backend.
- 04-green: exit 1; default Parquet nested naming differed from exact schema. Pinned use_compliant_nested_type=False.
- 05-green: exit 0; initial 16 transform/parser tests.
- 06-extended-red: exit 1; new exact-binding test demonstrated missing source-workset identity comparison. Added full Binding identity comparison; all other extended tests passed.
- 07-green and 16-precommit-green: exit 0; all 28 tests (21 transform and 7 parser tests) pass. Command is `uv run --offline --frozen --package sec-edgar-ingest python -c "import sys; sys.path.insert(0, 'packages/sec-edgar-ingest/tests'); import network_guard; network_guard.main(['test_etl_transform','test_etl_parser','-v'])"`.
- 08-diff-check, 12-staged-check: exit 0; staged whitespace clean.
- 09-status, 11-add, 13-owned-diff, 14-owned-diff: retained explicit owned staging, stat and full diff.
- 10-artifact-proof: exit 0; retained immutable originals/output, actual hashes, crash after manifest with zero Processing rows, repair with parser patched to fail, and force replay with exact same output/workset.
- 15-process-restart: exit 0; a separate guarded process loads the retained context/artifacts, patches reparsing to fail, and reuses the exact Processing/observation/workset.
- 17-commit, 18-head, 19-status: exit 0; explicit owned-file commit and clean checkout.

Tests cover parser v2 replay with unchanged raw/source/snapshot originals; zero Coordinator/BoundedSender/RequestClient construction; duplicate retention/cross-quarter counts; conflicting final duplicate after a full 8192-row batch; raw length/hash drift; malformed rows/envelopes/ZIP CRC; all durability observer points; actual manifest-to-Processing repair; corrupt/missing accepted output; image changes with force; partial recovery; complete empty inputs/incomplete membership; separate-process reuse; concurrent same-identity writes; injected-clock timeout; complete readback counts and scratch lifetime; and corruption immediately after stage preventing a manifest/checkpoint. The concurrent test forces both workers past independent parsing to a shared after_rows barrier and asserts identical results and one Processing record.

## Actual retained artifact identities

Full references, context, observation and proof booleans are in task3-evidence/artifact-hashes.json. Actual retained files are under task3-evidence/retained-artifacts.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Raw daily fixture | 133 | 322ce1308160bc5572ea72dc2c53ce17ad3862d0fc04ea9a98bdc288ff8bf543 |
| Observation Parquet | 4253 | c0a5c3d0b56a2f438d1dd6068bd3bda3ad368e2da203d76aea35e8765678d5d2 |
| Observation manifest | 1584 | 5beffe2e8c7ef65b08c986b86182f59a78b671cfe40886e4edc45280d89c17b6 |
| Snapshot workset bytes | 3058 | 223563a5d062a1539c0009b032432919e6b59f3993da89d55da716439eca5e5a |
| Transformed workset bytes | 5692 | aaf639bd4bf13712c03060860f6f372c385031fd8ec893fa264aff188a667949 |

Snapshot workset ID: 1fc26eb80f9c75a3f28f58eacac49638ccca544db52101cd01e5205885bd0ab9.
Transformed workset ID: 407b60261b57dc8ab0fcf564f70e34e10d32dcfcb65e8f5ee006294b73bdf25a.
Retained output has source_row_count=1, distinct_key_count=1, quarter_counts={2025Q3:1}; source period remains 2026-09-30. The distinct duplicate test separately verifies three retained rows/two keys and two quarters.

## Self-review and clean-code application

Reviewed full owned staged diff against every Task 3 step and interface. Applied N1/N4/N7 to effectful parsing/verification/staging helpers; G25 to batch, format, transport status and Parquet version constants; G30/G34 to separation of pinned membership, raw validation, bounded row output/readback, and immutable adoption; T1/T5/T6 to durability, boundary, duplicate, corruption and exact-binding regressions. C3 retains only intent comments. No unrelated cleanup occurred. Existing EtlState was consumed directly rather than rewritten. No subagent was spawned and no user code contribution was requested because the behavior was fully prescribed.

Concerns: none blocking. Stage 7 Linux capacity, full baseline, all-ten retained-row proof and all22 integrated checks remain reserved; native offline unit/fixture evidence makes no deployed capacity claim. Publish refusal of incomplete transformed input belongs to downstream publication implementation; Task 3 produces complete=false faithfully.
