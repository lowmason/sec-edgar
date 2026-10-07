## Global Constraints

The quoted contract sentences below are copied verbatim from the parent or ADR; numeric settings remain the accepted starting values. Every task includes these constraints.

- “The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.” (ADR Decision.)
- “All application requests to the SEC share one downloader and one request budget. More ETL workers must not mean more SEC traffic.” (Parent R8.)
- “Discovery requests, downloads, retries and reconciliation all count.” (Parent §4.3.)
- “All collectors in the owner's deployment use the same coordination namespace, including backfill and daily runs.” (Parent §4.3.)
- “Lease loss stops new requests. A successor waits for the previous ownership window and bounded in-flight request allowance to expire before issuing requests.” (Parent §4.3.)
- “Daily work gets the next turn ahead of remaining backfill or reconciliation units.” (Parent §4.3.)
- “Discovery writes an immutable source workset. Collection pins one accepted snapshot per member in the manifest, then emits a separate immutable snapshot workset naming exact hashes. Retries complete unresolved members without replacing pinned inputs. ETL never silently follows a mutable “latest”.” (Parent §4.1.)
- “Never advance discovery past a failed directory read.” (Parent §4.2.)
- “Also revisit pending and failed source identities regardless of their quarter.” (Parent §4.2.)
- “Daily discovery starts at the approved handoff date and replays overlap with the baseline.” (Parent §4.2.)
- “A truncated or invalid body is quarantined, never accepted as an empty index.” (Parent §4.3.)
- “Promote a valid download to its content-addressed raw location before marking it downloaded.” (Parent §4.3.)
- “Discovery may exist before a snapshot; failures belong to attempts and do not erase an earlier successful state.” (Parent §4.5.)
- “There is no assumed transaction spanning Blob Storage and Table Storage.” (Parent §4.6.)
- “An HTTP failure, absent listing or open-quarter absence is not a withdrawal.” (Parent R10.)
- “CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.” (Parent §6.)
- Python >=3.14; intended historical range 2010 Q1 through the open quarter; initial development range 2015 Q1 through the open quarter; resolve and pin the end quarter at each run's start; daily handoff 2026-10-01; SEC User-Agent `Lowell Mason sec-edgar-ingest mason.lowell@mac.com`.
- `sec.requests_per_second`: 3 requests/second, no bursts; `sec.max_active_collectors`: 1 across all application pipelines; `http.max_attempts`: 5 total per request, including the first.
- `http.retry_base_seconds`: 2; `http.retry_cap_seconds`: 120; exponential with jitter, honor longer server delays; `http.connect_timeout_seconds`: 15; `http.read_timeout_seconds`: 60.
- `jobs.replica_retry_limit`: 0; `orchestration.transient_replays`: at most 1 for positively confirmed transient failure; no automatic replay of an ambiguous start. No scheduler/job implementation here.
- Versions are required, explicit and pinned per workset: `etl.parser_version`, `etl.schema_version`, `worker.image_digest`; canonical schema remains `sec-index-v1`. Stage 2 does not implement a parser.
- Accepted acquisition guards, owner answer 2026-10-06: 90 seconds per complete HTTP exchange; 67,108,864 received bytes; 536,870,912 expanded IDX bytes. Guard violations retain evidence and leave unresolved work. No recovery-horizon, format-coverage or capacity claim follows from these values.
- Keep client/download scaffolds on disk but excluded from the workspace and runtime dependency graph. Preserve the four original index-ingest deletions without staging them. Preserve the local/untracked roadmap; never include it incidentally in a commit/PR.
- Accepted F1 remains immutable at SHA-256 `939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff`; accepted evidence manifest is `124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131`. Historical pending text is superseded by final acceptance and completion records.
- Quarterly ZIP with one DEFLATE `master.idx` and plain daily IDX are the selected acquisition representations. Bounded specimens are not global format coverage. The 33 uninspected historical daily directories establish no recovery horizon or ingestion coverage.
- Planning and ordinary tests use retained evidence/offline inspection. Stage 1 SEC and temporary compute windows are closed. Fresh live SEC/Azure/compute work needs concrete new authorization and one owner-wide issuer/budget. Delegating code never authorizes network work.
- Do not implement or plan row parsing/normalization, generation publication, reconciliation/withdrawal approval, Azure orchestration/provisioning or scheduled activation. Preserve their parent contracts and stage boundaries.
- Final whole-branch reviewer is explicitly `gpt-6.1-sol`, reasoning effort `max` (GPT-6.1 Max), fresh context and read-only. This owner instruction supersedes generic Opus routing. If unavailable, report the gate as unpassed; do not substitute silently.

---

### Task 7: Promote raw bytes, bind each member once and resume collection

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/collection.py`, `packages/sec-edgar-ingest/tests/test_collection.py`; extend collection/fault builders in `tests/support.py`. Modify `state.py` only for the Task 7 methods below and `worksets.py` only for actual snapshot-workset assembly.

**Interfaces:** Consumes SourceWorkset, RequestClient, envelope validator, AcquisitionState and ObjectStore. Produces `collect(workset: SourceWorkset, context: RunContext, settings: Settings, client: RequestClient, state: AcquisitionState, objects: ObjectStore, faults: Faults) -> CommandResult`; `collect_member(workset: SourceWorkset, source: Source, context: RunContext, settings: Settings, client: RequestClient, state: AcquisitionState, objects: ObjectStore, faults: Faults) -> Snapshot`; `raw_path(source: Source, sha256: str) -> str`; `AcquisitionState.reusable_snapshot(source: Source, envelope_version: str) -> Snapshot | None`; `AcquisitionState.promotion_receipt(workset_id: str, source_id: str) -> dict[str,object] | None`; `AcquisitionState.record_promotion(workset_id: str, snapshot: Snapshot) -> None`; `AcquisitionState.record_receipt(workset_id: str, source: Source, receipt: BodyReceipt, temporary_ref: str) -> None`; `AcquisitionState.staged_receipt(workset_id: str, source_id: str) -> dict[str,object] | None`. A promotion receipt is a repairable acquisition checkpoint, not a pin; Binding remains sole write-once selection authority.

Test helper `collection_harness(root: Path, responses: Sequence[ResponseSpec]) -> CollectionHarness` exposes `collect(workset: SourceWorkset) -> CommandResult`, `source_state`, `objects`, `fail_at(point: str)`, `fetch_count`, `reopen() -> CollectionHarness` and `snapshot_workset(result: CommandResult) -> SnapshotWorkset`. Errors use Task 2/5 codes; no failed member rewrites successful snapshot or binding state.

- [ ] **Step 1: Write/run RED pinning and crash/resume tests.** A mutable latest snapshot changing between attempts must not change the workset's accepted pin:

  ```python
  import tempfile
  import unittest
  from pathlib import Path
  from support import collection_harness, fixture_source, fixture_workset, valid_idx_response

  class CollectionTests(unittest.TestCase):
      def test_retry_preserves_first_member_pin(self):
          with tempfile.TemporaryDirectory() as directory:
              source = fixture_source(kind='daily', period='2026-10-01')
              workset = fixture_workset((source,))
              h = collection_harness(Path(directory), [valid_idx_response('daily')])
              first = h.collect(workset)
              old = h.snapshot_workset(first).snapshots[0]
              h.install_newer_snapshot(source, valid_idx_response('daily', company='Changed fixture').body)
              resumed = h.reopen().collect(workset)
              self.assertEqual(h.snapshot_workset(resumed).snapshots[0], old)
              self.assertEqual(h.fetch_count, 1)
  ```

  `valid_idx_response(kind: str, company: str = 'Fixture Co') -> ResponseSpec` supplies full synthetic envelope bytes; `install_newer_snapshot(source: Source, body: bytes) -> Snapshot` validates the fixture envelope, promotes/verifies the raw object and updates snapshot state using the actual collection helpers, without issuing a new HTTP request. Add two-source partial success/second404 followed by recovery, two concurrent workset binders fetching different valid originals, same hash skip, different new workset refresh, empty successful discovery vs failed empty workset, missing/corrupt raw on resume, schema/context mismatch and immutable snapshot-workset collision. Retain RED.

- [ ] **Step 2: Implement content-first ordering and write-once adoption.** Use these paths:

  ```text
  raw/sec/indexes/kind=<kind>/period=<period>/sha256=<hash>/master.zip
  raw/sec/indexes/kind=daily/period=<date>/sha256=<hash>/master.idx
  worksets/sec/source/sha256=<source-workset-id>/workset.json
  worksets/sec/snapshot/sha256=<snapshot-workset-id>/workset.json
  staging/sec/<run-id>/<attempt-id>/<source-id>/<request-id>/body
  quarantine/sec/<run-id>/<source-id>/<attempt-id>/<request-id>/body
  ```

  Raw archive extension preserves representation; parent `master.idx` is an illustrative path, not permission to replace an archive. Quarantine includes complete/partial byte counts, hash, response headers and error alongside the body. Retention is indefinite during development; do not delete evidence to retry.

  The collection ordering is executable core:

  ```python
  def collect_member(workset, source, context, settings, client, state, objects, faults):
      pinned = state.binding(workset.workset_id, source.source_id)
      if pinned is not None:
          snapshot = state.snapshot(source.source_id, pinned.snapshot_sha256)
          objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
          return snapshot
      snapshot = recover_promoted(workset, source, state, objects)
      if snapshot is None and workset.acquisition_mode == 'reuse_accepted':
          snapshot = state.reusable_snapshot(source, expected_envelope(source))
          if snapshot is not None:
              objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
      if snapshot is None:
          receipt = client.fetch(source.canonical_url, context, source)
          validated = validate_envelope(source, receipt, settings)
          temporary_ref = stage_receipt(objects, context, source, receipt)
          snapshot = snapshot_for(source, validated)
          state.record_receipt(workset.workset_id, source, receipt, temporary_ref)
          objects.promote(temporary_ref, snapshot.raw_path,
                          snapshot.sha256, snapshot.byte_count)
          faults.hit('after_raw_promotion')
          state.record_promotion(workset.workset_id, snapshot)
          faults.hit('after_promotion_receipt')
      state.remember_snapshot(snapshot)
      faults.hit('after_snapshot_record')
      winner = state.bind_once(Binding(workset.workset_id, source.source_id, snapshot.sha256))
      faults.hit('after_binding')
      accepted = state.snapshot(source.source_id, winner.snapshot_sha256)
      objects.verify(accepted.raw_path, accepted.sha256, accepted.byte_count)
      return accepted
  ```

  Define helpers in `collection.py`: `expected_envelope(source: Source) -> str`; `stage_receipt(objects: ObjectStore, context: RunContext, source: Source, receipt: BodyReceipt) -> str`; `snapshot_for(source: Source, body: ValidatedBody) -> Snapshot`; `recover_promoted(workset: SourceWorkset, source: Source, state: AcquisitionState, objects: ObjectStore) -> Snapshot | None`. Extend `Faults` with `hit(point: str) -> None` from its Task 3 scheduled actions. An attempt's durable staging/receipt metadata must be recorded BEFORE promotion so a crash immediately after raw creation can recover its exact hash/path by the member's recorded receipt; never choose a glob/latest object to repair a pin. `recover_promoted` verifies that recorded receipt and object, repairs snapshot/promotion metadata, and refuses corrupt/missing bytes; if no valid promoted object exists it resumes the unresolved download with accounted attempt history.

  Catch validation/HTTP/state errors at each member to retain quarantine/pending/error state and continue safe independent members unless the run-wide access-block/ownership halt requires stopping. A concurrent bind loser reads/verifies the winner even if it downloaded different valid bytes. Both originals may remain; neither can overwrite the binding. New worksets may explicitly refresh; existing worksets always reuse their pins. No ETL path consumes a SourceState latest field.

- [ ] **Step 3: Assemble immutable snapshot worksets only after all requested acquisition is complete.** Confirm source-workset digest/path, frozen config/image/parser/schema compatibility and every member's binding plus raw hash/length. The collector's new run/execution/attempt identifiers go into its result/Attempt; the snapshot workset retains immutable source-workset origin and versions, yielding the same snapshot-workset ID on retry.

  If discovery is incomplete or any member unbound, persist progress/gaps and return `incomplete` with no complete snapshot-workset reference. Retained successful downloads/pins remain reusable. Successful empty discovery emits a valid empty snapshot workset and `no_new_sources`; an empty failed directory yields `incomplete/discovery_failed`, never success. On all pins present, construct snapshot workset with exact source-member matching, write it create-only, then write the result. Crash after writing the snapshot workset can reuse its exact existing bytes. It does not imply a published generation or a processing state beyond downloaded.

- [ ] **Step 4: Inject each durable-boundary crash, verify/review.** Test forced process exits after temporary receipt checkpoint, raw promotion, promotion record, snapshot record, binding, snapshot-workset write and before result write. Reopen stores and rerun with the same source workset; assert exact pins and raw hashes remain, no successful member is fetched again, unresolved members alone continue, counters/gaps are honest and the final snapshot workset is byte-identical. Raw-only retained validation/reuse uses a sender that raises if called. Test two concurrent collectors with a forced CAS race and changed bytes; only the winner pin reaches the workset.

  Run collection/state/storage/download/workset tests GREEN. Commit `feat: pin immutable snapshots and resume incomplete collection`; obtain task Spec/Quality PASS.

**Checkpoint:** Restartable acquisition and exact immutable snapshot inputs are proven. Row-level replay, dataset publication and reconciliation remain unimplemented later-stage contracts.
