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
