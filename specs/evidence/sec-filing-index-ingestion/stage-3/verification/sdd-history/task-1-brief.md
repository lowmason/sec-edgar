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
