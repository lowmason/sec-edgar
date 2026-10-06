## Global Constraints

- Repository: `/Users/lowell/Projects/sec-edgar`; owner and decider: Lowell Mason.
- Workload remains filing indexes: historical quarterly backfill, ongoing daily ingestion, metadata ETL and reconciliation. One implementation package is `packages/sec-edgar-ingest/`, distribution/CLI `sec-edgar-ingest`, import `sec_edgar_ingest`; see parent §§2, 4.1, 4.9 and ADR Decision.
- Intended historical range: 2010 Q1 through the open quarter, inclusive. Initial development range: 2015 Q1 through the open quarter, inclusive. End-quarter rule: Resolve and pin the end quarter at each run's start.
- Daily handoff: 2026-10-01, retaining baseline overlap under parent §4.2.
- SEC User-Agent: Lowell Mason sec-edgar-ingest mason.lowell@mac.com.
- Azure target: A new dedicated resource group in an existing subscription. Region order: eastus, then eastus2, then centralus.
- Networking: Public HTTPS endpoints, managed identities, scoped roles, anonymous blob access disabled. Infrastructure as code: Bicep.
- Python/container candidate: Python 3.14; Linux amd64 container.
- Initial compute candidate: General-purpose Consumption workload profile; 2 vCPU and 4 GiB RAM. Initial execution settings: One replica; parallelism 1; completion count 1; replica timeout 3,600 seconds.
- Initial storage candidate: Standard general-purpose v2; hierarchical namespace enabled; Hot tier; ZRS.
- Ingestion-artifact retention: Indefinite during initial development: raw snapshots, observations, generations, manifests, approvals, quarantine evidence and run reports.
- Operational-log retention: 90 days. Alert owner and destination: Lowell Mason; mason.lowell@mac.com.
- Accepted parent §4.8 defaults: daily 05:00 Eastern; Sunday reconciliation 06:00 Eastern; 3 requests/second, no bursts; 1 active collector; 5 total HTTP attempts; 2 s exponential/jitter base and 120 s local cap while honoring longer server delays; 15 s connection / 60 s read timeout; zero native job retries; at most 1 confirmed-transient-failure replay. Parent §§4.3, 4.8 and §5 govern all SEC investigation access.
- Preserve existing local deletions in `packages/sec-edgar-index-ingest/` and the untracked roadmap. Preserve any additional execution-time changes. No broad staging, stash, reset, restoration or package repair.
- Read-only inspection, bounded source/archive inspection and isolated dependency/container probes are authorized. No production ingestion modules, parser/catalog implementation, golden parser tests, workspace repairs, Bicep resource definitions, provisioning, publication or trigger activation.
- No resource-profile comparison. Actual worker memory/runtime and live integrated Azure behavior belong to Stage 7. A local probe has no deployment authority.

### Task 4: Prove an exact isolated Python/container dependency combination

**Files:** Create `runtime/base-image.json`, `runtime/requirements.in`, `runtime/requirements.lock`, `runtime/dependency-matrix.csv`, `runtime/probe.py`, `runtime/commands.md`, `runtime/results/`; update index/discrepancies.

**Interfaces:** Consumes Task 3 formats and specimen bytes. Produces exact reproducible base/runtime pins, dependency/wheel metadata and retained successful compatibility results, or a blocking failure.

- [ ] **Step 1: Inspect tool prerequisites outside the workspace.** Record `docker version`, `docker buildx version`, `uv --version`, `az version`, and `az bicep version` when installed, with exit codes. Missing tools are evidence, not permission to install or repair packages. Use an available isolated container facility; if none can run Linux amd64, record the runtime proof as blocked. Native macOS/arm64 imports alone do not satisfy this task.

- [ ] **Step 2: Select and inspect one exact Python 3.14 patch image.** Resolve an official Debian slim Python tag to immutable registry manifest and Linux amd64 child digest using `docker buildx imagetools inspect` and retain its output. Record tag, registry, manifest/child digest, OS variant and libc, `sys.version`, implementation/ABI (`sysconfig.get_config_var('SOABI')`), architecture and installer versions. Re-run by digest with `--platform linux/amd64`; do not select `latest`. Label emulated amd64 as such and do not infer production performance. Exact patch/digests are outputs of investigation, not invented pins in this plan.

- [ ] **Step 3: Resolve a minimal direct dependency set in that image.** Start with documented Identity 1.26.0, Blob 12.31.0 and Tables 12.7.0 candidates; select an exact SEC HTTP client and PyArrow version from current publisher package metadata. Use synchronous requests unless selected operations justify async dependencies. Include azure-storage-file-datalake only if the recorded operation map requires DFS APIs; record why omitted otherwise. Freeze exact direct pins into `requirements.in`, resolve all transitives into a hash-locked `requirements.lock` with the recorded installer version, and preserve downloaded artifact hashes/metadata. Matrix columns: `distribution,version,direct_or_transitive,requires_python,artifact_filename,wheel_tags,sha256,source_url,install_result,import_result,limitation`. Cover cryptography/cffi, Azure core/MSAL and Parquet native artifacts when resolved. A package minimum version is insufficient evidence; if a source build is needed record build prerequisites and prove it in the selected image or select a supported wheel combination.

- [ ] **Step 4: Reinstall the lock in a fresh container, not the resolver environment.** Bind evidence read-only as `/evidence`, bind a new isolated output directory as `/out`; record complete expanded commands, stdout/stderr and exit codes. Commands use the selected digest and exact installer pins recorded in `base-image.json`/`commands.md`, never an unconstrained tag. Run `python -m pip install --require-hashes -r /evidence/runtime/requirements.lock`, `python -m pip check`, `python -m pip inspect`, `python -m pip debug --verbose`, and `python /evidence/runtime/probe.py`. Expected install/check/probe exit code: 0; retain nonzero results too. No `uv sync` at repository root. Install is networked dependency access, not an Azure authentication test.

- [ ] **Step 5: Run this offline import/Parquet probe and decode each selected archive separately.** Save the following complete core probe as `runtime/probe.py`; inputs are synthetic compatibility rows, not normalized SEC data:

  ```python
  import importlib
  import json
  import platform
  import sys
  import sysconfig
  from importlib.metadata import version
  from pathlib import Path

  import pyarrow as pa
  import pyarrow.parquet as pq

  matrix = Path('/evidence/runtime/dependency-matrix.csv').read_text()
  modules = ['azure.identity', 'azure.storage.blob', 'azure.data.tables']
  if 'azure-storage-file-datalake,' in matrix:
      modules.append('azure.storage.filedatalake')
  for module in modules:
      importlib.import_module(module)
  direct = Path('/evidence/runtime/requirements.in').read_text().splitlines()
  installed = {}
  for line in direct:
      line = line.strip()
      if line and not line.startswith('#'):
          name, pin = line.split('==')
          assert version(name) == pin, (name, pin, version(name))
          installed[name] = pin
  assert sys.version_info[:2] == (3, 14)
  assert platform.machine() in ('x86_64', 'amd64'), platform.machine()
  rows = pa.table({'probe_id': [1, 2], 'text': ['SEC', 'café'],
                   'optional': pa.array([None, 'x'], type=pa.string())})
  target = Path('/out/roundtrip.parquet')
  pq.write_table(rows, target)
  restored = pq.read_table(target)
  assert restored.equals(rows)
  print(json.dumps({'python': sys.version, 'machine': platform.machine(),
                    'abi': sysconfig.get_config_var('SOABI'),
                    'installed': installed, 'parquet_roundtrip': 'passed'}))
  ```

  Import the chosen HTTP-client module with a separate `python -c` command; it must make no requests. For selected ZIP use `python -m zipfile -t` and the bounded member inspection from Task 3 in the fresh container. For selected gzip use `gzip -t` if available plus bounded decompression; for another codec use its documented exact decoder and retain commands/exit codes. Compare decoded hashes to Task 3 derivatives. Plain `.idx` needs a recorded no-archive decision and exact-byte/encoding check. Include every selected codec; optional unselected codecs remain unsupported. Do not implement SEC row parsing/catalog publication in this probe.

- [ ] **Step 6: Repeat reproducibility verification and record limits.** Fresh-container installation plus imports, selected-archive decoding and Parquet round trip must all pass for one exact combination. Retain failed candidates with discrepancy resolutions. Distinguish base-image digest from a future built worker/release digest. Include registry choice, pull authorization requirements, rollback-image availability decision and exact deployment tool versions/prerequisites in the decision record, without building/pushing a worker or accessing deployed resources.

**Checkpoint:** The combined Linux amd64/Python 3.14 matrix is supported by actual successful isolated outputs with hashes, commands and exit codes. No successful Azure data access, production worker capacity or parser coverage is implied.
