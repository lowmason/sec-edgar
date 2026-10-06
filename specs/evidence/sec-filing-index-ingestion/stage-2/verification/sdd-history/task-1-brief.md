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

### Task 1: Align the workspace and establish a buildable CLI boundary

**Ownership/files:** Modify `pyproject.toml`, `packages/sec-edgar-ingest/pyproject.toml`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py`, `README.md`, `packages/sec-edgar-ingest/README.md`, `.gitignore`. Create `uv.lock`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/__main__.py`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `packages/sec-edgar-ingest/tests/__init__.py`, `packages/sec-edgar-ingest/tests/test_workspace.py`. Do not modify the client/download scaffolds or the original deleted files.

**Interfaces:** Consumes current pyproject/scaffolds and the approved scaffold disposition. Produces import `sec_edgar_ingest`, CLI function `main(argv: Sequence[str] | None = None) -> int`, module invocation `python -m sec_edgar_ingest`, and one workspace member/dependency. At this milestone help/version work; discover/collect become runnable only in Task 8 and are not falsely advertised as finished.

- [ ] **Step 1: Write and run the standalone failing workspace test.** Bootstrap tests must not invoke the broken root editable build. Put this content in `tests/test_workspace.py` and retain its actual failure against the stale membership/script:

  ```python
  import pathlib
  import tomllib
  import unittest

  ROOT = pathlib.Path(__file__).resolve().parents[3]

  class WorkspaceTests(unittest.TestCase):
      def test_only_ingest_is_a_workspace_member(self):
          root = tomllib.loads((ROOT / 'pyproject.toml').read_text())
          self.assertEqual(root['tool']['uv']['workspace']['members'],
                           ['packages/sec-edgar-ingest'])
          self.assertFalse(root['tool']['uv']['package'])
          self.assertNotIn('scripts', root['project'])
          package = tomllib.loads(
              (ROOT / 'packages/sec-edgar-ingest/pyproject.toml').read_text())
          self.assertEqual(package['project']['name'], 'sec-edgar-ingest')
          self.assertEqual(package['project']['scripts']['sec-edgar-ingest'],
                           'sec_edgar_ingest.cli:main')
  ```

  Run `uv run --no-project --offline --python 3.14 python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_workspace.py -v`. Expected RED: membership assertion fails, exit nonzero. If no local 3.14 exists, record that prerequisite instead of downloading a runtime without the relevant execution permission. The working project requires >=3.14; older bootstrap syntax compatibility does not waive that floor.

- [ ] **Step 2: Replace stale root packaging and add the initial CLI.** Keep root project metadata/author/Python floor, remove root scripts and build-system, use these sections:

  ```toml
  [project]
  name = "sec-edgar"
  version = "0.1.0"
  description = "SEC filing-index ingestion workspace"
  readme = "README.md"
  requires-python = ">=3.14"
  dependencies = ["sec-edgar-ingest"]

  [tool.uv]
  package = false

  [tool.uv.sources]
  sec-edgar-ingest = { workspace = true }

  [tool.uv.workspace]
  members = ["packages/sec-edgar-ingest"]
  ```

  In the existing ingest project retain `uv_build>=0.12.15,<0.13.0`, set a specific acquisition description, add exactly these acquisition dependency pins and script:

  ```toml
  dependencies = [
      "requests==2.34.2",
      "azure-identity==1.26.0",
      "azure-storage-blob==12.31.0",
      "azure-data-tables==12.7.0",
  ]

  [project.scripts]
  sec-edgar-ingest = "sec_edgar_ingest.cli:main"
  ```

  Define `__version__ = '0.1.0'` in `__init__.py`, a stdlib argparse help/version CLI, and a main guard in `__main__.py`:

  ```python
  # cli.py
  import argparse
  from collections.abc import Sequence
  from . import __version__

  def main(argv: Sequence[str] | None = None) -> int:
      parser = argparse.ArgumentParser(prog='sec-edgar-ingest')
      parser.add_argument('--version', action='version', version=__version__)
      parser.parse_args(argv)
      parser.print_help()
      return 0
  ```

  ```python
  # __main__.py
  from .cli import main

  if __name__ == '__main__':
      raise SystemExit(main())
  ```

  Remove the unused `hello()` API as part of the approved scaffold replacement. Add `/specs/sec-filing-index-ingestion-roadmap.md` to `.gitignore` so it stays local; do not add that file. Preserve the original four deletion statuses. Root/package READMEs explain one ingest implementation and excluded scaffolds, with no claim that acquisition is finished yet.

- [ ] **Step 3: Resolve, inspect and lock the accepted acquisition combination.** Add the constraints below first, then run `uv lock`, `uv sync --frozen`, and `uv build --all-packages`. Dependency-registry access is distinct from closed SEC/Azure authority; use the environment's concrete permission flow if needed. Compare the resolution to Stage 1's exact 21-distribution lock, using the following root `[tool.uv]` constraints for its 20 acquisition distributions (all except PyArrow) rather than copying the Linux wheel-only lock into a universal uv lock:

  ```toml
  constraint-dependencies = [
      "azure-core==1.41.0", "azure-data-tables==12.7.0", "azure-identity==1.26.0",
      "azure-storage-blob==12.31.0", "certifi==2026.7.22", "cffi==2.1.1",
      "charset-normalizer==3.5.2", "cryptography==50.0.2", "idna==3.20",
      "isodate==0.7.2", "msal-extensions==1.3.1", "msal==1.39.0",
      "multidict==7.0.0", "propcache==0.5.4", "pycparser==3.0", "PyJWT==2.15.1",
      "requests==2.34.2", "typing_extensions==4.16.0", "urllib3==2.8.0", "yarl==1.25.1",
  ]
  ```

  These are version constraints for packages that actually enter the acquisition dependency graph, not a requirement to import/install unused optional distributions. Do not upgrade direct or native pins silently. Retain installed versions/platform and differences between local hashes and the accepted Linux amd64 wheel hashes. Package build does not establish container compatibility or worker fit.

  Run `uv run --frozen --package sec-edgar-ingest python -c "import sec_edgar_ingest; print(sec_edgar_ingest.__version__)"`, `uv run --frozen --package sec-edgar-ingest sec-edgar-ingest --help`, and `uv run --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version`. Expected: import succeeds, help names `sec-edgar-ingest`, version `0.1.0`, all exit 0. Test installed metadata/entry point with `importlib.metadata.distribution('sec-edgar-ingest')`, not only source import.

- [ ] **Step 4: Verify the boundary and commit/review.** Rerun `test_workspace.py` through the workspace prefix: GREEN. Verify client/download files are byte-identical, no index-ingest restoration/staging occurred, and the roadmap is still present with its protected hash. Stage only the exact Task 1 files with `git add -- <named paths>`; commit `build: align the SEC ingest workspace and CLI`. Produce its task brief/report/diff package and obtain Spec/Quality PASS before Task 2.

**Checkpoint:** One workspace package builds/imports, one CLI works, and primary local changes remain protected. This does not implement acquisition yet.
