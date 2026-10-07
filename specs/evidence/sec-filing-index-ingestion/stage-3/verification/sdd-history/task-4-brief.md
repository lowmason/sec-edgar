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
