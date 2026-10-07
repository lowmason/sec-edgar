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
