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

### Task 3: Implement durable state and Blob/Table/local adapters

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/__init__.py`, `storage/contracts.py`, `storage/local.py`, `storage/azure.py`, `state.py`; `packages/sec-edgar-ingest/tests/test_storage.py`, `test_state.py`, `test_azure_contracts.py`; extend `tests/support.py` with shared test stores and fault injection. Retain SDK signature checks under `specs/evidence/sec-filing-index-ingestion/stage-2/sdk-signatures.json` during execution, not planning.

**Interfaces:** Consumes Task 2 records/settings. Produces `StateStore.get(kind: str, key: str) -> Versioned | None`, `insert(kind: str, key: str, value: dict[str,object]) -> Versioned`, `replace(kind: str, key: str, value: dict[str,object], version: str) -> Versioned`, `scan(kind: str, filters: dict[str,object]) -> Iterator[Versioned]`; `ObjectStore.put_once(path: str, body: bytes) -> str`, `read(path: str) -> bytes`, `stage(path: str, body: Path) -> str`, `promote(temporary_ref: str, raw_path: str, sha256: str, byte_count: int) -> str`, `verify(path: str, sha256: str, byte_count: int) -> None`; `LeaseStore.acquire(owner: str, seconds: int) -> LeaseHandle`, `renew(handle: LeaseHandle) -> LeaseHandle`, `release(handle: LeaseHandle) -> None`, `assert_owned(handle: LeaseHandle) -> None`, with `LeaseHandle(owner_id: str, lease_id: str, observed_until: datetime)` and bounded server-time observation. Errors: `AlreadyExists`, `Conflict`, `OwnershipLost`, `ClockUncertain`.

`AcquisitionState(store: StateStore)` produces `observe(source: Source, at: datetime, discovery_status: str) -> None`, `get_source(source_id: str) -> Versioned | None`, `pending_sources() -> tuple[Source,...]`, `remember_snapshot(snapshot: Snapshot) -> Snapshot`, `snapshot(source_id: str, sha256: str) -> Snapshot`, `binding(workset_id: str, source_id: str) -> Binding | None`, `bind_once(binding: Binding) -> Binding`, `begin_attempt(context: RunContext) -> None`, `finish_attempt(result: CommandResult) -> None`, `record_failure(source: Source, error: Error) -> None`, `request_attempt(context: RunContext, receipt: BodyReceipt, permit: Permit, ordinal: int) -> None`. Directory and coordination rows use generic store methods; their payloads are defined in Tasks 4/6.

Fixture helper `store_bundle(root: Path) -> tuple[StateStore,ObjectStore,LeaseStore]` returns separate clients to the same SQLite/files directory. `Faults.at(point: str, action: Callable[[],None]) -> None` schedules a one-shot exception/crash at a named durable boundary. Production code accepts this hook as an optional no-op observer, never a special path that bypasses state transitions.

- [ ] **Step 1: Write/run restart, pin-race and failure-preservation RED tests.** Actual state persists across closing/reopening clients; a dict fake is insufficient:

  ```python
  import tempfile
  import unittest
  from pathlib import Path
  from sec_edgar_ingest.models import Binding
  from sec_edgar_ingest.state import AcquisitionState
  from support import fixture_source, fixture_snapshot, store_bundle

  class StateTests(unittest.TestCase):
      def test_first_pin_survives_reopen_and_a_newer_snapshot(self):
          with tempfile.TemporaryDirectory() as directory:
              root = Path(directory)
              store, objects, leases = store_bundle(root)
              state = AcquisitionState(store)
              source = fixture_source()
              old = fixture_snapshot(source, b'original')
              new = fixture_snapshot(source, b'changed')
              state.remember_snapshot(old)
              winner = state.bind_once(Binding('workset-a', source.source_id, old.sha256))
              state.remember_snapshot(new)
              reopened = AcquisitionState(store_bundle(root)[0])
              loser = reopened.bind_once(Binding('workset-a', source.source_id, new.sha256))
              self.assertEqual(loser, winner)
              self.assertEqual(reopened.snapshot(source.source_id, winner.snapshot_sha256), old)
  ```

  Define `fixture_snapshot(source: Source, body: bytes) -> Snapshot` in support with a real SHA and byte length. Add create-conflict, stale-CAS, two processes inserting the same binding, source success plus later failure, pagination, interrupted attempts and immutable-object same/different-content collision cases. Each process opens its own connection; barriers force both to observe an absent binding before racing the conditional insert. Run the three named test modules RED.

- [ ] **Step 2: Inspect the installed exact SDK and retain mocked HTTP contracts.** Assert installed versions and collect public signatures without credentials/client construction:

  ```python
  import inspect
  import json
  from importlib.metadata import version
  from azure.storage.blob import BlobClient, BlobLeaseClient, BlobServiceClient
  from azure.data.tables import TableClient, TableServiceClient

  assert version('azure-storage-blob') == '12.31.0'
  assert version('azure-data-tables') == '12.7.0'
  members = [BlobServiceClient, BlobClient, BlobLeaseClient,
             BlobLeaseClient.acquire, BlobLeaseClient.renew, BlobLeaseClient.release,
             BlobClient.upload_blob, BlobClient.download_blob,
             BlobClient.get_blob_properties, TableClient, TableServiceClient,
             TableClient.create_entity, TableClient.get_entity, TableClient.update_entity]
  signatures = {f'{item.__module__}.{item.__qualname__}': str(inspect.signature(item))
                for item in members}
  print(json.dumps(signatures, indent=2, sort_keys=True))
  ```

  Retain stdout, installed-source hashes and exact conditional keyword semantics in the evidence file. Where signatures expose `**kwargs`, inspect the installed request construction and test with a scripted Azure SDK transport. Assert `x-ms-version` is selected explicitly, `If-None-Match: *` for immutable creates, opaque `If-Match` for replace, real lease ID for sentinel writes, and no wildcard/upsert. Full signatures were not present in Stage 1 evidence; resolving this code-level gate is required before accepting these adapters. If the installed pins contradict the recorded REST primitive contract, surface a concrete plan deviation; no live experiment or guessed parameter is allowed.

- [ ] **Step 3: Implement conditional durable primitives and state transitions.** Local state uses SQLite transactions with a revision token; objects use create-exclusive temporary files, fsync and atomic create/link under validated paths, not overwrite-rename. Verify same-existing bytes on immutable conflict; different bytes is corruption. File/SQLite transaction boundaries deliberately remain separate for crash tests.

  Azure uses managed identity credentials, Blob-created objects throughout (no DFS rename or lifecycle mixing), conditional create and exact ETag Table updates. SDK network retries may retry only idempotent Storage operations under explicit settings; this does not authorize SEC retries. Adopt these call shapes only after Step 2 verifies the exact installed signatures:

  ```python
  from azure.core import MatchConditions
  from azure.core.exceptions import ResourceExistsError, ResourceModifiedError
  from azure.data.tables import UpdateMode

  def conditional_replace(client, entity, version):
      if not version or version == '*':
          raise ValueError('exact ETag required')
      try:
          client.update_entity(entity=entity, mode=UpdateMode.REPLACE,
                               etag=version, match_condition=MatchConditions.IfNotModified)
      except ResourceModifiedError as exc:
          raise Conflict(str(exc)) from exc

  def bind_once(self, candidate: Binding) -> Binding:
      key = candidate.source_workset_id + ':' + candidate.source_id
      try:
          self.store.insert('Binding', key, candidate.to_mapping())
          return candidate
      except AlreadyExists:
          existing = self.store.get('Binding', key)
          if existing is None:
              raise Conflict('binding vanished after create conflict')
          return Binding.from_mapping(existing.value)
  ```

  Define mapping conversion on each Task 2 record, and map exact SDK 409/412/not-found to store errors rather than broad retries. Refresh/read actual versions after writes. `scan` must follow continuations until exhausted. `observe` updates first/last discovery independently of successful snapshot pointers. `remember_snapshot` is idempotent on `(source_id,hash)` and conditionally updates latest receipt without allowing an older receipt to overwrite newer state. Failed/unfinished attempt rows remain auditable. Verify raw content exists before calling `remember_snapshot` from the collection path; isolated state tests can use explicit synthetic snapshots.

- [ ] **Step 4: Verify both adapters' contract suites, commit/review.** Run local durability/race tests and scripted Azure request tests GREEN; no Azure account/auth request occurs. Insert/replace conflict handling must have bounded retry limits and surface unresolved conflicts. Commit `feat: add durable acquisition stores and source state` with only Task 3 paths and the execution-time signature report. Obtain task Spec/Quality PASS.

**Checkpoint:** Durable restart/CAS/write-once semantics and the actual selected SDK request shapes are locally verified. Effective Azure permissions, lease timing, HNS/Table behavior and crash behavior remain Stage 7 checks.
