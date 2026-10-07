# SEC filing-index ingestion — Stage 2 Durable Discovery and Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the single-package acquisition CLI, durable discovery/source/attempt state, original-byte collection and immutable pinned snapshot worksets, verified with offline failure, concurrency and recovery fixtures.

**Architecture:** Keep discovery and collection in `packages/sec-edgar-ingest/`, behind explicit state, object, lease, clock and HTTP interfaces. Implement Azure Blob/Table adapters and a durable local fixture backend against the same application contracts; coordinate every SEC exchange through one renewable lease, persisted pacing/priority and a bounded sender. Separate immutable source worksets, write-once member bindings and immutable snapshot worksets so incomplete attempts resume without changing accepted inputs.

**Tech Stack:** Python >=3.14; uv 0.12.15/uv_build; standard-library dataclasses, JSON, unittest, sqlite3 and multiprocessing; Requests 2.34.2; azure-identity 1.26.0; azure-storage-blob 12.31.0; azure-data-tables 12.7.0. Blob service version 2026-04-06; Table service version 2020-12-06. No Parquet dependency or infrastructure build in this stage.

**Status: COMPLETE (2026-10-06)** — executed via subagent-driven-development; nothing deferred
**Implementing spec:** [Stage 2 scope and rollout](../../completed/sec-filing-index-ingestion-stage-2-spec.md), not the parent design spec.
**Authority:** [Parent design](../../sec-filing-index-ingestion-spec.md), [ADR](../../sec-filing-index-ingestion-adr.md), [roadmap](../../sec-filing-index-ingestion-roadmap.md), [accepted F1](../../sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1), [completed Stage 1 spec](../../completed/sec-filing-index-ingestion-stage-1-spec.md), and [completed plan 1](1-sec-filing-index-ingestion-stage-1-spec.md).

> Historical approval record: the paragraph below preserves the approved planning receipt; the completion status and evidence above/below supersede its then-pending execution statements.

**Owner approval record:** Lowell Mason replied **“Approved”** to the request to approve Plan 2 for fresh-session execution via `subagent-driven-development`, recorded on 2026-10-06 America/New_York. The approved pre-recording plan SHA-256 is `a868939950abb0838625bf539fc46bc4fcc5c10f384b75764a3af4d9bc4f601c`; its Stage 2 implementing spec SHA-256 is `ed256aa56319269bb0ac7ad3ed54c91ffcfae13357be8daa7851c0e2555b0b0c`. This update records approval and handoff status only; technical tasks, interfaces, safeguards and completion gates are unchanged. Approval authorizes the prescribed fresh-session implementation, not live access, Stage 2 completion or Stage 3 work. No owner-authored time of day was supplied.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

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

## Reconciled baseline and execution boundary

This section preserves the historical planning baseline and execution handoff. Current completion, interfaces and review results are recorded in the completion evidence.

Plan ID 2 is the next available integer: the only existing numeric plan is completed plan 1. This plan implements only Stage 2's R8 and package-boundary gaps; it does not discharge whole-roadmap verification or deployment acceptance.

On 2026-10-06 `HEAD` and cached `origin/main` were `17731c33961f8ae3669e472765c1d1745ade44b4`. The working tree has four unstaged deletions under index-ingest and an untracked roadmap. Root `pyproject.toml` still references that missing member, includes the two unused scaffolds, and exposes `sec-edgar = sec_edgar:main` despite no root module. The ingest package contains only `hello()` and `py.typed`. There are no ingestion tests, lockfile, worker, infrastructure or CI definitions. Do not run workspace setup/builds in this planning session.

The parent design and ADR hashes still match F1 (`6c4f27aead06659864497c737ddd8f29a07d4ee0f671cd5c22529da857e89b93`, `55852d3b85ba2e6f7c0cbf1559615e769f751fda01a7f781fb5e73ff6a337807`). Fresh offline checks verified all 1,584 manifest records, including the manifest's explicit immutable alias for the pre-acceptance finding; its current appendix-bearing path has a different hash by design. Stage 1 completed 2026-10-06; F1 was accepted 2026-10-05 America/New_York. See Stage 2 spec §1 for unticked-stage consistency, without later-stage planning.

Owner approval is recorded in this plan and the Stage 2 spec; technical content is unchanged. At fresh-session execution preflight, commit only `specs/plans/2-sec-filing-index-ingestion-stage-2-spec.md` and `specs/sec-filing-index-ingestion-stage-2-spec.md` as `docs: approve Stage 2 acquisition plan`. This makes both implementing documents available to isolated execution and later `git mv` retirement. Do not include the roadmap or original deletions in that commit. The document commit and implementation belong to the fresh execution session; nothing is staged or committed by this approval record.

At execution start use `using-git-worktrees` to establish isolation according to the owner's execution choice. Native managed worktree tools are preferred and must use the inspected current base, not silently pick another default. If a worktree is used, first compare its contents with the protected primary checkout: carry only the approved Stage 2 spec/plan and preserve the local deletion state in the isolated baseline without committing those original deletions. A fresh checkout may materialize the old tracked index-ingest files; do not restore them into the primary checkout, and exclude the stale package before build. Do not remove or stage the user's primary files. If preserving a deletion in the isolated checkout would require an unauthorized destructive command, obtain that concrete filesystem permission rather than reset/stash anything. The roadmap is a read-only local input copied only when needed, excluded from commits; do not assume Git carried it.

Recheck HEAD, primary status and hashes, plan/spec bytes, and any drift before task dispatch. Pre-existing root build failure is an authorized Task 1 target, not permission to repair unrelated packages. Use the standalone stdlib bootstrap check before workspace setup. All remaining tests run against committed fixtures, scripted transports or an explicit loopback fixture server. Loopback fixture URLs enter only the fixture transport; production URL validation continues to accept only the selected SEC families.

## File structure and task ownership

Paths are relative to the repository root. Each implementer owns only the task's named files. Workers are not alone: preserve other edits and accommodate approved interface deviations recorded in the progress ledger. Implementation tasks execute in order, one writer at a time; independent read-only checks can run in parallel. No agent creates an independent SEC issuer or budget.

| Task | Files/responsibility |
|---|---|
| 1 | Root/package `pyproject.toml`, `uv.lock`, `.gitignore`, package `__init__.py`, `__main__.py`, initial `cli.py`, root/package README, `tests/test_workspace.py`: one build/import/CLI boundary |
| 2 | `config.py`, `models.py`, `urls.py`, `worksets.py`, fixture config, `tests/support.py`, config/identity/workset tests: validated typed configuration and immutable serialized contracts |
| 3 | `storage/contracts.py`, `storage/local.py`, `storage/azure.py`, `state.py`, storage/state tests: durable create/CAS/blob/lease adapters, source/attempt/binding state and restart proof |
| 4 | `coordination.py`, coordination tests/support: shared turn queue, pacing/cooldown, lease renewal/loss and takeover protocol |
| 5 | `download.py`, `validation.py`, HTTP/validation tests and synthetic raw fixtures: bounded HTTP sender, retry outcomes, exact-byte envelope acceptance/quarantine |
| 6 | `discovery.py`, discovery tests/listing fixtures: trusted discovery graph, source worksets, durable coverage boundaries and recovery selection |
| 7 | `collection.py`, collection tests: raw promotion, write-once pins, resumption and snapshot worksets |
| 8 | Final `cli.py`, `results.py`, acquisition CLI/process tests, acquisition runbook, CI and verification report: commands, named outcomes, end-to-end proof and Stage 2 documentation |

Every implementation file above lives under `packages/sec-edgar-ingest/src/sec_edgar_ingest/`. Every test lives under `packages/sec-edgar-ingest/tests/`. Exact per-task paths appear below. `storage/__init__.py` and `tests/__init__.py` are folded into the task that first needs them. Do not add `workflows/` implementations in Stage 2.

## Cross-task schemas and interfaces

Task 2 defines these deeply immutable records and deterministic JSON codecs. Convert nested mappings to read-only mappings/immutable values, and make mapping serializers return detached copies; frozen dataclass attributes alone do not freeze a dict. UTC timestamps are timezone-aware ISO strings; SHA-256 is 64 lower-case hex; immutable IDs hash canonical UTF-8 JSON with sorted keys, compact separators and no NaN. Include versions and effective config hash in the digest. Sort members by source ID and directories by canonical URL; reject duplicates rather than hide conflicting members.

| Record | Fields used across tasks |
|---|---|
| `Source` | `source_id: str`, `canonical_url: str`, `kind: Literal['quarterly','daily']`, `period: str`, `representation: Literal['zip','idx']` |
| `RunContext` | `run_id, execution_id, command, attempt_id, image_digest, parser_version, schema_version, config_sha256: str`; `started_at, deadline: datetime`; `priority: Literal['daily','backfill','reconciliation']` |
| `DirectoryOutcome` | `url, period: str`; `outcome: Literal['available','no_new_sources','discovery_failed']`; `listing_sha256: str | None`; `source_ids: tuple[str,...]`; `error: Error | None` |
| `SourceWorkset` | `workset_id: str`, frozen `context: RunContext`, `pinned_end_quarter: str`, `discovery_id: str`, `members: tuple[Source,...]`, `directories: tuple[DirectoryOutcome,...]`, `discovery_complete: bool`, `overlap_from: date`, `acquisition_mode: Literal['reuse_accepted','refresh']` |
| `Snapshot` | `source_id, sha256, raw_path: str`; `byte_count: int`; `received_at: datetime`; `validators: Mapping[str,str]`; `representation, envelope_version: str` |
| `Binding` | `source_workset_id, source_id, snapshot_sha256: str` |
| `SnapshotWorkset` | `workset_id, source_workset_id: str`; `context: RunContext`; `snapshots: tuple[Snapshot,...]`; exact `pinned_end_quarter`, `directories`, `overlap_from`; no mutable latest references |
| `Error` | `code, message: str`; `retryable: bool`; `source_id: str | None`; `details: Mapping[str,object]` |
| `CommandResult` | `context: RunContext`; `outcome: str`; `source_workset_ref, snapshot_workset_ref: str | None`; counters `discovered,downloaded,unchanged,pending,failed,quarantined: int`; `gaps: tuple[Error,...]`; `started_at,ended_at: datetime` |
| `Versioned` | `value: dict[str,object]`; `version: str` (opaque actual Table ETag or local revision) |
| `QueueTicket` | `ticket_id, owner_id, priority: str`; `enqueued_at, expires_at: datetime` |
| `Permit` | `owner_id: str`, `epoch: int`, `request_id: str`; `must_start_before, must_end_by, takeover_after: datetime`; `start_before_mono, deadline_mono: float` |
| `BodyReceipt` | `url: str`, `status: int`, `headers: dict[str,str]`, `temporary_path: Path`, `received_at: datetime`, `byte_count: int`, `sha256: str`, `complete: bool`, `error: Error | None` |
| `ValidatedBody` | `receipt: BodyReceipt`; `representation, envelope_version: str`; `expanded_byte_count: int` |

`Attempt` durable rows include parent §4.5's run/execution/command/attempt/image tuple, start/end, outcome and structured error; transport-attempt child rows include request ID, ordinal 1–5, URL, status, bytes, ownership epoch and next-allowed time. Discovery status and acquisition status are separate; a later discovery/download failure never deletes `latest_downloaded_snapshot` or existing bindings. Stage 2 creates no processing identity claiming transformation/publication.

The generic state adapter stores `Source`, `Snapshot`, `Binding`, `DirectoryProgress`, `DiscoveryBoundary`, `Coordination` and `QueueTicket` rows in **SourceState**, and attempts in **Attempts**. Namespace/kind are partition keys; stable identities are row keys. This adds no unapproved table binding. Use paginated reads for pending work. Snapshots are keyed by `(source_id, sha256)`; bindings by `(source_workset_id, source_id)`. A snapshot is not an approval or active publication pointer.

All named helper methods in code examples below are defined by the producing task's Interfaces block. Type protocol bodies may use `...` because they define interfaces, not unimplemented production behavior. Examples show the critical executable core and assertions; implementers must finish the specified surrounding modules and named matrix cases through red/green cycles, without replacing the behavioral requirements with examples alone.

## Evidence and review procedure for every task

Use the `subagent-driven-development` task brief/report/diff-file handoff. Record BASE before dispatch; never substitute `HEAD~1`. Each task's loop is: write its first failing behavioral test, run and retain the observed failure, implement the minimum required behavior, run covering tests, refactor, run covering tests again, commit only its named files, dispatch a fresh task reviewer, fix/re-review until both **Spec PASS** and **Quality PASS**. Commit messages below describe task boundaries. The progress ledger carries actual interfaces/deviations, commands and outputs; clean task-review evidence does not imply Stage 7 acceptance.

The commands after Task 1 assume a working workspace, cwd at its execution root:

```bash
uv run --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

For a targeted module use `python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_NAME.py' -v` through the same `uv run --frozen --package sec-edgar-ingest` prefix. This plan uses stdlib unittest so no unverified development dependency version is invented. Test failures must assert contract violations, not mirror private implementation details. No wall-clock sleeps in unit tests: use deterministic injected clocks/barriers. A separate bounded process test verifies the actual hard sender cancellation against a loopback server.

### Task 1: Align the workspace and establish a buildable CLI boundary

**Ownership/files:** Modify `pyproject.toml`, `packages/sec-edgar-ingest/pyproject.toml`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py`, `README.md`, `packages/sec-edgar-ingest/README.md`, `.gitignore`. Create `uv.lock`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/__main__.py`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `packages/sec-edgar-ingest/tests/__init__.py`, `packages/sec-edgar-ingest/tests/test_workspace.py`. Do not modify the client/download scaffolds or the original deleted files.

**Interfaces:** Consumes current pyproject/scaffolds and the approved scaffold disposition. Produces import `sec_edgar_ingest`, CLI function `main(argv: Sequence[str] | None = None) -> int`, module invocation `python -m sec_edgar_ingest`, and one workspace member/dependency. At this milestone help/version work; discover/collect become runnable only in Task 8 and are not falsely advertised as finished.

- [x] **Step 1: Write and run the standalone failing workspace test.** Bootstrap tests must not invoke the broken root editable build. Put this content in `tests/test_workspace.py` and retain its actual failure against the stale membership/script:

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

- [x] **Step 2: Replace stale root packaging and add the initial CLI.** Keep root project metadata/author/Python floor, remove root scripts and build-system, use these sections:

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

- [x] **Step 3: Resolve, inspect and lock the accepted acquisition combination.** Add the constraints below first, then run `uv lock`, `uv sync --frozen`, and `uv build --all-packages`. Dependency-registry access is distinct from closed SEC/Azure authority; use the environment's concrete permission flow if needed. Compare the resolution to Stage 1's exact 21-distribution lock, using the following root `[tool.uv]` constraints for its 20 acquisition distributions (all except PyArrow) rather than copying the Linux wheel-only lock into a universal uv lock:

> Deviation: Exact acquisition pins were retained; local verification used macOS 26.6.2 arm64/Python 3.14.0, distinct from accepted Linux amd64/Python 3.14.8 evidence and a future worker image.

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

- [x] **Step 4: Verify the boundary and commit/review.** Rerun `test_workspace.py` through the workspace prefix: GREEN. Verify client/download files are byte-identical, no index-ingest restoration/staging occurred, and the roadmap is still present with its protected hash. Stage only the exact Task 1 files with `git add -- <named paths>`; commit `build: align the SEC ingest workspace and CLI`. Produce its task brief/report/diff package and obtain Spec/Quality PASS before Task 2.

**Checkpoint:** One workspace package builds/imports, one CLI works, and primary local changes remain protected. This does not implement acquisition yet.

### Task 2: Validate acquisition settings and freeze identity/workset contracts

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/config.py`, `models.py`, `urls.py`, `worksets.py`; `conf/sec-edgar-ingest.yaml`; `packages/sec-edgar-ingest/tests/support.py`, `test_config.py`, `test_urls.py`, `test_worksets.py` and `fixtures/config/local.json`.

**Interfaces:** Produces the records in Cross-task schemas; `Settings.from_mapping(value: dict[str,object]) -> Settings`; `load_config(path: Path) -> Settings`; `pin_context(settings: Settings, context: RunContext, today: date) -> tuple[RunContext,str]`; `canonical_source_url(url: str, kind: str) -> str`; `canonical_listing_url(url: str) -> str`; `child_url(parent: str, href: str, name: str, is_directory: bool) -> str`; `source_id(url: str) -> str`; `encode_workset(workset: SourceWorkset | SnapshotWorkset) -> bytes`; `decode_source_workset(body: bytes) -> SourceWorkset`; `decode_snapshot_workset(body: bytes) -> SnapshotWorkset`; `make_source_workset(context: RunContext, end_quarter: str, discovery_id: str, members: tuple[Source,...], directories: tuple[DirectoryOutcome,...], overlap_from: date) -> SourceWorkset`; `make_snapshot_workset(source: SourceWorkset, snapshots: tuple[Snapshot,...]) -> SnapshotWorkset`. Produces test builders `fixture_settings(**overrides) -> Settings`, `fixture_context(command='collect', priority='backfill') -> RunContext`, `fixture_source(period='2015Q1', kind='quarterly') -> Source`, `fixture_workset(members: tuple[Source,...], discovery_complete=True) -> SourceWorkset`.

- [x] **Step 1: Write/run validation and immutability RED cases.** A config error must precede any credential/client/transport factory call. Include this behavior, adapting unittest method placement without changing assertions:

  ```python
  from dataclasses import replace
  import unittest
  from sec_edgar_ingest.config import Settings
  from sec_edgar_ingest.worksets import encode_workset, decode_source_workset
  from support import fixture_settings, fixture_source, fixture_workset

  class ContractTests(unittest.TestCase):
      def test_second_collector_is_refused(self):
          value = fixture_settings().to_mapping()
          value['sec']['max_active_collectors'] = 2
          with self.assertRaisesRegex(ValueError, 'max_active_collectors'):
              Settings.from_mapping(value)

      def test_member_order_does_not_change_workset_identity(self):
          a, b = fixture_source('2015Q1'), fixture_source('2015Q2')
          first = fixture_workset((a, b))
          second = fixture_workset((b, a))
          self.assertEqual(first.workset_id, second.workset_id)
          self.assertEqual(decode_source_workset(encode_workset(first)), first)
          changed = replace(first, pinned_end_quarter='2026Q3')
          with self.assertRaisesRegex(ValueError, 'identity'):
              decode_source_workset(encode_workset(changed))
  ```

  Add named subtests for missing identity/range/handoff, reversed quarters, future/unpinned endpoint, unsupported schema/version, absent/synthetic-in-Azure image digest, non-positive limits, NaN/infinity, target >=10, illegal independent namespace, missing Azure endpoints, credentials in URLs, unsafe output path and unknown keys. `Settings.to_mapping() -> dict[str,object]` returns a deep copy; fixture helpers may not bypass validation. Azure-mode command deadlines must be finite, after the start and within the accepted3,600-second worker allowance; fixture-only clock/deadline overrides are explicitly labelled. Lower fixture-only byte/time caps let guard tests use small generated streams without allocating512MiB in memory. Run each target module and retain RED before implementation.

- [x] **Step 2: Implement canonical identities and workset codecs.** Use frozen dataclasses plus deeply immutable nested mappings/tuples for the declared schemas and explicit complete mapping conversion; detached serializers cannot mutate the stored/workset object. This identity core is shared by source/workset records:

> Deviation: RunContext adds deeply immutable effective_config and pinned_on; make_source_workset accepts keyword-only acquisition_mode, copied into SnapshotWorkset, with strict shared source/directory/raw-period identity validation.

  ```python
  import hashlib
  import json

  def canonical_json(value: object) -> bytes:
      return json.dumps(value, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False, allow_nan=False).encode('utf-8')

  def source_id(url: str) -> str:
      return hashlib.sha256(url.encode('utf-8')).hexdigest()

  def workset_digest(payload: dict[str,object]) -> str:
      return hashlib.sha256(canonical_json(payload)).hexdigest()
  ```

  Codec payloads include `format_version='sec-acquisition-v1'`, frozen effective context/config, resolved endpoint, acquisition mode and directory outcomes; hash excludes only the `workset_id` field itself. Decoders recompute and reject wrong IDs, unknown versions, duplicate sources, missing snapshot members, mutable latest references, non-UTC timestamps, non-hex hashes and incomplete source inputs passed to `make_snapshot_workset`. A complete zero-member workset is valid only with successful directory outcomes; failed empty discovery stays incomplete. Snapshot worksets name source ID, raw path and hash for every source member, including representation metadata.

  In `urls.py`, parse with `urllib.parse.urlsplit`; require exact `https`, host `www.sec.gov`, no userinfo/port/query/fragment and normalized safe path beneath `/Archives/edgar/full-index/` or `/Archives/edgar/daily-index/` matching kind. Decode segments before checking `.`/`..`, encoded separators/control characters; reject foreign absolute child hrefs, path escape, conflicting name/href and filing-content paths. Keep case-sensitive path content; canonicalize only the accepted origin. Every file must originate from a validated listing child, never a calendar-generated filename. `canonical_source_url` permits only selected quarterly master.zip or daily master.YYYYMMDD.idx file shapes; `canonical_listing_url` permits index.json beneath the accepted hierarchy. `child_url` validates name/href agreement, returns only immediate safe descendants, and never follows parent-dir metadata.

- [x] **Step 3: Implement validated settings and explicit fixture configuration.** Configuration v1 accepts JSON syntax, a valid YAML 1.2 subset, in `conf/sec-edgar-ingest.yaml`; load with stdlib `json.loads` and explain the syntax restriction in the README. Do not add an unverified YAML dependency. Use nested typed settings with `to_mapping`, an effective config SHA, and these fixture values:

  ```json
  {
    "config_version": "sec-acquisition-v1",
    "backfill": {"start_quarter": "2015Q1", "end_quarter": "open"},
    "daily": {"start_date": "2026-10-01"},
    "sec": {"user_agent": "Lowell Mason sec-edgar-ingest mason.lowell@mac.com", "requests_per_second": 3, "max_active_collectors": 1},
    "http": {"max_attempts": 5, "retry_base_seconds": 2, "retry_cap_seconds": 120, "connect_timeout_seconds": 15, "read_timeout_seconds": 60, "exchange_deadline_seconds": 90, "max_received_bytes": 67108864, "max_expanded_bytes": 536870912},
    "coordination": {"lease_seconds": 60, "renew_every_seconds": 20, "namespace": "sec-owner-lowell-mason", "clock_uncertainty_seconds": 2},
    "storage": {"backend": "local-fixture", "root": ".fixture-state", "source_table": "SourceState", "attempt_table": "Attempts", "blob_api_version": "2026-04-06", "table_api_version": "2020-12-06"},
    "etl": {"parser_version": "fixture-envelope-v1", "schema_version": "sec-index-v1"},
    "worker": {"image_digest": "sha256:0000000000000000000000000000000000000000000000000000000000000000", "provenance": "synthetic-fixture"},
    "jobs": {"replica_retry_limit": 0},
    "orchestration": {"transient_replays": 1},
    "reconciliation": {"require_withdrawal_approval": true}
  }
  ```

  `.fixture-state/` is ignored, created only when the fixture backend is explicitly chosen. No real Azure endpoint/principal/image digest is invented. Azure configuration must explicitly supply the accepted account endpoints, container references, shared lock object, SourceState/Attempts names, real immutable image digest and accepted parser/schema identifiers; reject account/namespace divergence from the deployment's one binding. For this owner that binding is the accepted `secedgardevb8617` Storage account and fixed `sec-owner-lowell-mason` coordination namespace; one fixed leased sentinel governs all workflows. Persist/check the binding registry with conditional create under the common lock container, and reject callers proposing another sentinel/namespace/budget rather than create their independent lane. In fixture mode all contenders explicitly share one fixture root/binding. A fixture marker or all-zero digest is rejected for Azure. `parser_version` is provenance only here, not a row-parser capability claim.

  The proposed implementation settings lease60/renew20/clock uncertainty2 are mechanics reviewed with this plan, not observed effective Azure values. The adapter derives server-time bounds and fails closed when the actual uncertainty exceeds 2 seconds; it must never assume the host wall clock meets that bound. Validate `0 < renew < lease`, finite request lifetime and guard values before constructing clients. Copy the accepted schedule defaults in documentation, leaving trigger definitions to their own stage.

- [x] **Step 4: Complete the contract matrix, commit/review.** Run config/URL/workset tests GREEN, including deepcopy/frozen-record checks, same URL stable ID, changed content/version different workset ID, UTC/quarter/leap-day boundaries and two callers with mismatched namespaces refusing access. Add only named files; commit `feat: define validated acquisition and workset contracts`; obtain task Spec/Quality PASS.

**Checkpoint:** Later tasks can depend on explicit versioned types and serialization; malformed configuration reaches no external I/O.

### Task 3: Implement durable state and Blob/Table/local adapters

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/__init__.py`, `storage/contracts.py`, `storage/local.py`, `storage/azure.py`, `state.py`; `packages/sec-edgar-ingest/tests/test_storage.py`, `test_state.py`, `test_azure_contracts.py`; extend `tests/support.py` with shared test stores and fault injection. Retain SDK signature checks under `specs/evidence/sec-filing-index-ingestion/stage-2/sdk-signatures.json` during execution, not planning.

**Interfaces:** Consumes Task 2 records/settings. Produces `StateStore.get(kind: str, key: str) -> Versioned | None`, `insert(kind: str, key: str, value: dict[str,object]) -> Versioned`, `replace(kind: str, key: str, value: dict[str,object], version: str) -> Versioned`, `scan(kind: str, filters: dict[str,object]) -> Iterator[Versioned]`; `ObjectStore.put_once(path: str, body: bytes) -> str`, `read(path: str) -> bytes`, `stage(path: str, body: Path) -> str`, `promote(temporary_ref: str, raw_path: str, sha256: str, byte_count: int) -> str`, `verify(path: str, sha256: str, byte_count: int) -> None`; `LeaseStore.acquire(owner: str, seconds: int) -> LeaseHandle`, `renew(handle: LeaseHandle) -> LeaseHandle`, `release(handle: LeaseHandle) -> None`, `assert_owned(handle: LeaseHandle) -> None`, with `LeaseHandle(owner_id: str, lease_id: str, observed_until: datetime)` and bounded server-time observation. Errors: `AlreadyExists`, `Conflict`, `OwnershipLost`, `ClockUncertain`.

`AcquisitionState(store: StateStore)` produces `observe(source: Source, at: datetime, discovery_status: str) -> None`, `get_source(source_id: str) -> Versioned | None`, `pending_sources() -> tuple[Source,...]`, `remember_snapshot(snapshot: Snapshot) -> Snapshot`, `snapshot(source_id: str, sha256: str) -> Snapshot`, `binding(workset_id: str, source_id: str) -> Binding | None`, `bind_once(binding: Binding) -> Binding`, `begin_attempt(context: RunContext) -> None`, `finish_attempt(result: CommandResult) -> None`, `record_failure(source: Source, error: Error) -> None`, `request_attempt(context: RunContext, receipt: BodyReceipt, permit: Permit, ordinal: int) -> None`. Directory and coordination rows use generic store methods; their payloads are defined in Tasks 4/6.

Fixture helper `store_bundle(root: Path) -> tuple[StateStore,ObjectStore,LeaseStore]` returns separate clients to the same SQLite/files directory. `Faults.at(point: str, action: Callable[[],None]) -> None` schedules a one-shot exception/crash at a named durable boundary. Production code accepts this hook as an optional no-op observer, never a special path that bypasses state transitions.

- [x] **Step 1: Write/run restart, pin-race and failure-preservation RED tests.** Actual state persists across closing/reopening clients; a dict fake is insufficient:

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

- [x] **Step 2: Inspect the installed exact SDK and retain mocked HTTP contracts.** Assert installed versions and collect public signatures without credentials/client construction:

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

- [x] **Step 3: Implement conditional durable primitives and state transitions.** Local state uses SQLite transactions with a revision token; objects use create-exclusive temporary files, fsync and atomic create/link under validated paths, not overwrite-rename. Verify same-existing bytes on immutable conflict; different bytes is corruption. File/SQLite transaction boundaries deliberately remain separate for crash tests.

> Deviation: AzureStateStore accepts keyword-only objects/observer and keeps legacy small Payload rows; oversized whole records use verified canonical worksets/state/sha256=<hash>.json objects plus one bounded Table descriptor with actual ETag CAS.

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

- [x] **Step 4: Verify both adapters' contract suites, commit/review.** Run local durability/race tests and scripted Azure request tests GREEN; no Azure account/auth request occurs. Insert/replace conflict handling must have bounded retry limits and surface unresolved conflicts. Commit `feat: add durable acquisition stores and source state` with only Task 3 paths and the execution-time signature report. Obtain task Spec/Quality PASS.

**Checkpoint:** Durable restart/CAS/write-once semantics and the actual selected SDK request shapes are locally verified. Effective Azure permissions, lease timing, HNS/Table behavior and crash behavior remain Stage 7 checks.

### Task 4: Coordinate every request across collectors and safe takeover

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/coordination.py`, `packages/sec-edgar-ingest/tests/test_coordination.py`; extend only Task 4 helpers in `tests/support.py` and lease-journal primitives in `storage/contracts.py`, `storage/local.py`, `storage/azure.py` with Task 3 interfaces preserved.

**Interfaces:** Consumes Task 3 state/lease stores and Task 2 settings/Permit. Extend `LeaseStore` with `read_journal(handle: LeaseHandle) -> Versioned` and `write_journal(handle: LeaseHandle, value: dict[str,object], version: str) -> Versioned`; both operate on the leased sentinel, enforce the actual lease ID plus version, and fail on loss. Queue tickets live in SourceState; SEC pacing/takeover authority lives in the leased Blob journal, avoiding a claim that its lease fences Table entities.

Produces `Clock.now() -> datetime`, `monotonic() -> float`, `sleep(seconds: float) -> None`; `ManualClock.advance(seconds: float) -> None`; `Coordinator(settings: Settings, store: StateStore, leases: LeaseStore, clock: Clock)` with `turn(owner_id: str, priority: str, deadline: datetime) -> ContextManager[Turn]`, `Turn.reserve(request_id: str) -> Permit`, `Turn.assert_current(permit: Permit) -> None`, `Turn.complete(permit: Permit, drained: bool) -> None`, and per-turn `cancelled: Event`, `Coordinator.defer_until(instant: datetime) -> None`. `Coordinator.exchange(context: RunContext, url: str, sender: Sender) -> BodyReceipt` is the only HTTP entry point; it acquires a turn, reserves pacing, passes that turn's cancellation event, calls `Sender.send(url: str, context: RunContext, permit: Permit, *, cancellation: Event) -> BodyReceipt`, and reports ownership loss with a retained partial receipt. Sender is implemented in Task 5; tests use a controlled sender with the same interface.

Test helper `coordination_harness(root: Path, *, clock: Clock) -> CoordinationHarness` provides `start(owner: str, priority: str)`, `reserve(owner: str) -> Permit`, `hold_request(owner: str)`, `expire_owner(owner: str)`, `finish_request(owner: str)`, `acquire_successor(owner: str)`, `starts: list[tuple[str,datetime]]`, `maximum_active: int`. It drives real coordinator/store instances and barriers, not a second simplified scheduler.

- [x] **Step 1: Write/run overlap, loss and takeover RED tests.** Include a deliberately live prior request; counting only lease holders is insufficient:

  ```python
  import tempfile
  import unittest
  from pathlib import Path
  from support import coordination_harness, fixture_clock

  class CoordinationTests(unittest.TestCase):
      def test_expired_lease_does_not_allow_overlap_with_old_request(self):
          with tempfile.TemporaryDirectory() as directory:
              clock = fixture_clock()
              h = coordination_harness(Path(directory), clock=clock)
              h.start('backfill-a', 'backfill')
              clock.advance(59)
              h.hold_request('backfill-a')
              h.expire_owner('backfill-a')
              h.acquire_successor('daily-b')
              clock.advance(89)
              self.assertEqual([owner for owner, _ in h.starts], ['backfill-a'])
              h.finish_request('backfill-a')
              clock.advance(3)
              h.reserve('daily-b')
              self.assertEqual(h.maximum_active, 1)
              self.assertEqual([owner for owner, _ in h.starts], ['backfill-a', 'daily-b'])
  ```

  `fixture_clock() -> ManualClock` starts at a fixed UTC instant. The harness expires ownership at a persisted upper-bound instant and permits successor acquisition there; takeover tests include the full guard calculation rather than assuming 89/92 seconds universally. Add tests for a request begun just before expiry, a parent crash with surviving bounded sender, renewal failure during body streaming, delayed permit dispatch, process restart during cooldown, simultaneous backfill/daily/reconciliation contenders, daily's next-turn priority, expired queue tickets, a storage outage and clock uncertainty >2 seconds. Expected RED is a concrete early request/overlap or missing coordination behavior.

- [x] **Step 2: Implement a finite ownership and durable pacing journal.** Journal v1 fields are `owner_id, epoch, ownership_until, unsafe_until, last_start, not_before, request_id, clean_release`; all timing is conservative server-derived UTC bounds. A Table queue ticket cannot issue a request. Only the owner of the one leased sentinel can reserve a permit and change the journal.

> Deviation: TimeBounds and LeaseHandle upper observations bound takeover; Azure clean release retains the full unsafe_until guard because journal update and release are separate operations, while local release_clean is atomic.

  Lease duration60/renew20 use bounded Storage calls; check actual ownership before a reservation and renew while a body is in flight. Persist the reservation before any SEC socket opens. The following pure calculations define the guard, not the whole distributed algorithm:

  ```python
  from datetime import datetime, timedelta

  def takeover_time(previous_unsafe: datetime, acquired_upper: datetime,
                    exchange_seconds: float, uncertainty_seconds: float,
                    clean_release: bool) -> datetime:
      if clean_release:
          return previous_unsafe
      return max(previous_unsafe,
                 acquired_upper + timedelta(seconds=exchange_seconds + uncertainty_seconds))

  def reservation_guard(ownership_until: datetime, exchange_seconds: float,
                        uncertainty_seconds: float) -> datetime:
      return ownership_until + timedelta(seconds=exchange_seconds + uncertainty_seconds)

  def next_start(last_start: datetime | None, not_before: datetime,
                 earliest_safe: datetime, rate: float) -> datetime:
      if last_start is None:
          return max(not_before, earliest_safe)
      return max(not_before, earliest_safe,
                 last_start + timedelta(seconds=1 / rate))
  ```

  On uncertain acquisition/takeover, wait until BOTH the prior journal guard and a full possible exchange after confirmed acquisition have expired. Holding the new lease while waiting requires renewal but cannot issue HTTP. Capture the previous owner's takeover guard once on acquisition as this turn's `earliest_safe`; renewing the new lease must not repeatedly move its own start time forward. New reservations update the future successor guard independently. A clean release shortens the extra wait only after the sender is positively drained and journal/lease release outcomes are known. At that point write `clean_release=True` and reduce `unsafe_until` to the verified drain-time upper bound before release. An uncertain write/release preserves the conservative guard and stops the old owner from reusing the turn. Persist last-start/cooldown across every release and restart. Honor a server's longer delay globally; never reset rate counters in a new process.

  Storage `Date` with send/receive monotonic observations supplies a bounded interval, including server Date precision and request RTT. Refuse when that uncertainty cannot fit the configured2-second bound; do not merely subtract local UTC timestamps. Use monotonic deadlines inside a process. Uncertain renewal, lease-ID/ETag conflict or journal-write failure stops new requests, cancels/drains the sender, and leaves a conservative unsafe window. Recording future ownership before a renewal must be conservative; a successor also waits a full exchange from its own confirmed acquisition to cover an unknown prior renewal outcome. No operator lease break is exposed by the normal CLI.

- [x] **Step 3: Implement bounded turns and priority with real coordinator entry points.** Enqueue a ticket with finite expiry; select oldest valid daily ticket before non-daily work. Each bounded exchange releases its turn, including failed/retry attempts. Retry sleeps occur outside ownership while cooldown remains shared. Stale ticket removal uses CAS and cannot clear another ticket. Renewals use the same sentinel; they do not create new owners or traffic budgets. Expiry/loss sets `Turn.cancelled`, the same spawn-compatible event passed into `Sender.send`; `assert_current` refuses a stale epoch/permit before any new request.

  Add a test that calls `Coordinator.exchange` from three independent processes sharing local lease/journal state; all scripted transport starts append through one synchronized recorder. Assert no interval overlap, minimum1/3-second logical spacing, retries included, daily chosen before remaining lower-priority work, and no starts under an old epoch. Faults after journal reservation consume conservative pacing/guard even if no socket was opened. This is deliberate fail-closed recovery, not a requirement to reclaim an uncertain unused slot.

- [x] **Step 4: Verify, commit/review.** Run all coordination and Storage contract tests GREEN. Save event traces including acquire/renew/loss/request-start/request-end/takeover/queue choice, not just a successful final count. Commit `feat: coordinate collector ownership pacing and takeover`; obtain task Spec/Quality PASS.

**Checkpoint:** Fixtures demonstrate one coordinated issuer, stopped stale ownership and bounded in-flight takeover. Actual Azure timing/effective lease behavior and other owner-wide traffic allocation remain S7-11/S7-12 obligations.

### Task 5: Bound HTTP exchanges and validate original-byte acquisition envelopes

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/download.py`, `validation.py`; `packages/sec-edgar-ingest/tests/test_download.py`, `test_validation.py`, `fixtures/raw/quarterly.idx`, `fixtures/raw/daily.idx`, `fixtures/raw/denial.html`; extend sender/receipt helpers in `tests/support.py`. Synthetic ZIPs are built reproducibly from fixture IDX bytes in tests, not presented as SEC receipts.

**Interfaces:** Produces `Sender.send(url: str, context: RunContext, permit: Permit, *, cancellation: Event) -> BodyReceipt`; production `BoundedSender(settings: Settings, clock: Clock)`; fixture `ScriptedSender(responses: Sequence[ResponseSpec])`, where `ResponseSpec(status: int, body: bytes, headers: dict[str,str], fault: str | None = None)`. `ResponseSpec` is fixture-only. `RequestClient(settings: Settings, coordinator: Coordinator, sender: Sender, state: AcquisitionState, clock: Clock)` produces `fetch(url: str, context: RunContext, source: Source | None = None) -> BodyReceipt` and records every request attempt. `validate_envelope(source: Source, receipt: BodyReceipt, settings: Settings) -> ValidatedBody`; `retry_after(value: str | None, now: datetime) -> float | None`; `retry_delay(ordinal: int, server_delay: float | None, settings: Settings, jitter: float) -> float`.

`ValidationError(code: str, receipt: BodyReceipt)` carries partial evidence. `fetch` never directly constructs a second SEC transport outside `Coordinator.exchange`. A listing request has `source=None` and still consumes the same coordinator, attempt ledger and retry policy. `FetchError(error: Error, receipt: BodyReceipt)` reports terminal/deferred/pending outcomes without pretending a non-200 body is a valid index. Define `AcquisitionState.begin_request(context: RunContext, url: str, source_id: str | None, request_id: str, ordinal: int) -> None` and `request_history(context: RunContext, url: str) -> tuple[Versioned,...]`; atomically persist the ordinal before dispatch, then finish its receipt after dispatch. A crash with no receipt is an accounted uncertain attempt, not an unused retry. Request identity includes the current command's run/attempt and URL. Resuming the same command attempt retains ordinal/exhaustion; a deliberately new command attempt is separately auditable. No automatic new-attempt loop is created here.

- [x] **Step 1: Write/run RED byte, retry and fail-closed tests.** Use complete original ZIP bytes and a truncation/access-denial matrix:

  ```python
  import hashlib
  import unittest
  from support import download_harness, fixture_source, zip_bytes

  class DownloadTests(unittest.TestCase):
      def test_archive_original_is_not_replaced_by_decoded_idx(self):
          body = zip_bytes(b'CIK|Company Name|Form Type|Date Filed|Filename\r\n1|A|10-K|2015-01-02|edgar/data/1/a.txt\r\n')
          h = download_harness([(200, body, {'Content-Length': str(len(body))})])
          receipt = h.fetch(fixture_source())
          self.assertEqual(receipt.temporary_path.read_bytes(), body)
          self.assertEqual(receipt.sha256, hashlib.sha256(body).hexdigest())

      def test_retry_after_longer_than_local_cap_is_never_shortened(self):
          h = download_harness([(429, b'', {'Retry-After': '180'}),
                                (200, b'valid fixture', {})])
          h.fetch_response_only()
          self.assertGreaterEqual(h.starts[1] - h.starts[0], 180)
          self.assertEqual(h.attempt_count, 2)
          self.assertEqual(h.maximum_active, 1)
  ```

  Define `zip_bytes(body: bytes) -> bytes` with exactly one DEFLATE `master.idx`, fixed timestamp and CRC via stdlib zipfile. `download_harness(responses: Sequence[tuple[int,bytes,dict[str,str]]]) -> DownloadHarness` uses the actual RequestClient/Coordinator with ManualClock; `fetch(source)`, `fetch_response_only()`, `starts: list[float]` (monotonic seconds), `attempt_count: int` and `maximum_active: int` from the shared interval recorder expose behavior. Test a fifth failed attempt is terminal and no sixth is sent; retrying a timeout still consumes rate;403 and explicit denial page halt further run requests; listed404 remains pending;3xx is refused without auto-follow; HTML200 quarantines; Content-Length mismatch and nested IncompleteRead preserve partial bytes; slow headers/body hit absolute90-second exchange bound; length64MiB+1/expanded512MiB+1 refuse; ownership loss cancels the old sender.

- [x] **Step 2: Implement the sender as a hard-bounded exchange.** Requests connect/read timeouts are inactivity bounds, not a whole-body lifetime. Run one exchange in a supervised child process, with explicit IPC result/partial spool and absolute monotonic deadline; terminate/join it at the deadline or lease cancellation, close sockets and retain the partial spool. The child checks the permit's start/deadline immediately before network activity and on each streaming iteration; expired permits never open a socket. The supervisor and child both enforce the deadline. The child arms an independent OS-enforced fatal timer before opening a socket; loop checks alone cannot bound a blocking read after its parent dies. Parent crash/takeover fixtures exercise that independent timer and the remaining bounded-child lifetime.

  Disable requests/urllib3 automatic HTTP retries and redirects. Send the exact identifying User-Agent and `Accept-Encoding: identity`; stream `response.raw` with `decode_content=False`, removing transfer framing only. Reject unexpected Content-Encoding as an unsupported transport rather than hash transparently decoded content. Preserve status, relevant/full response headers, validators and UTC receipt even on failure. Every body chunk counts toward64MiB before write; SHA-256 covers exactly the retained entity bytes. Retain `IncompleteRead.partial` through nested errors and compare advertised Content-Length when applicable. ZIP validation uses512MiB expanded cap while streaming; never extract to paths from member names.

  The critical supervisor core must retain a bounded sender even when inactivity never trips:

  ```python
  def wait_for_sender(process, cancellation, deadline_mono, clock):
      while process.is_alive():
          remaining = deadline_mono - clock.monotonic()
          if cancellation.is_set() or remaining <= 0:
              process.terminate()
              process.join(timeout=1)
              if process.is_alive():
                  process.kill()
                  process.join(timeout=1)
              if process.is_alive():
                  raise OwnershipLost('sender did not drain; retain unsafe window')
              return False
          process.join(timeout=min(remaining, 0.05))
      return True
  ```

  The child hard timer core is:

  ```python
  import signal
  import time

  def arm_child_deadline(permit):
      now = time.monotonic()
      if now >= permit.start_before_mono:
          raise OwnershipLost('permit expired before socket start')
      remaining = permit.deadline_mono - now
      if remaining <= 0:
          raise OwnershipLost('exchange deadline expired')
      signal.signal(signal.SIGALRM, signal.SIG_DFL)
      signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGALRM})
      signal.setitimer(signal.ITIMER_REAL, remaining)
  ```

  `start_before_mono` is derived conservatively by the coordinator from its server-time bound and current ownership, while `deadline_mono` covers the complete exchange including child startup. Arm before DNS/TLS/socket activity; installation failure sends no request. This OS timer runs independently of a Python read loop or surviving supervisor. The process is created without SDK clients/credentials; it owns one Requests session. Fail to produce a receipt, unverified shutdown, IPC loss or supervisor crash never marks a clean release. The child must also bound itself after losing the supervisor channel. On the selected Linux runtime and local macOS fixture runtime, arm an unblocked `SIGALRM` with its default fatal disposition and `signal.setitimer(signal.ITIMER_REAL, remaining)` before opening a socket. The deadline covers process startup plus the complete exchange, and is checked against monotonic time before arming. Reject an execution platform without a proven independent hard-timer primitive rather than quietly use a soft deadline. Use the explicit Python multiprocessing spawn context, not fork-inherited clients. A killed child leaves an incomplete spool; the supervisor/recovery recalculates its prefix hash and retains it as partial evidence.

- [x] **Step 3: Implement retry outcomes and envelope validation.** Attempt ordinal is1–5 inclusive, persisted per URL/request identity; an ordinary resumed transport attempt cannot reset exhaustion to five unseen attempts. An explicitly new command attempt remains distinct and records prior exhaustion. 429/retryable5xx/connection failure/timeouts use full-jitter exponential delay capped locally at120, then `max(local_delay, server_delay)`. Parse Retry-After seconds and HTTP-date; invalid header retains diagnostic and uses local bounded policy. If delay exceeds the command deadline, persist `deferred` and do not sleep/retry early. Access denial sets a durable run halt visible to the next source; it is never retried under another identity.

> Deviation: Coordinator.exchange adds keyword-only on_response and a shared fail-closed policy latch; durable request_history/begin_request retain retry ordinals and server delays across attempts without reusing historical host-monotonic values.

  ```python
  def retry_delay(ordinal, server_delay, settings, jitter):
      local = min(settings.http.retry_cap_seconds,
                  settings.http.retry_base_seconds * (2 ** (ordinal - 1)))
      if not 0 <= jitter <= 1:
          raise ValueError('jitter outside [0,1]')
      return max(local * jitter, server_delay or 0)
  ```

  Validate complete transport, nonempty body, advertised size, selected representation and strict text envelope. Quarterly: ZIP central-directory integrity, exactly one safe `master.idx`, DEFLATE, no encrypted/extra members, full CRC and bounded expanded stream; scan strict ASCII/CRLF for exact selected column header. Daily: retain IDX bytes, scan strict ASCII/LF for the daily header. Reject denial/HTML/error pages, unsupported headers/encoding/archive shapes and truncated bodies. A header without data is not assumed to be a valid empty replacement. Keep syntactic row/date/key normalization out of this stage; a downloaded envelope can still fail the later parser and never gains publication authority. Do not drop raw bytes after a validation failure.

- [x] **Step 4: Run synthetic and retained-byte tests, commit/review.** Validate all ten original bodies from Stage1 `listings/SEC-0141.body` through `SEC-0150.body`, cross-checking the specimen matrix's original hashes; do not edit/copy over Stage1 artifacts or call it comprehensive golden parser coverage. Retain each synthetic bad-body reason and quarantine bytes. Add a bounded real-process loopback test with a fixture-only0.4-second exchange limit: send occasional bytes faster than the read inactivity bound and verify cancellation by the total deadline, process joined, socket closed and partial retained. This proves local hard lifetime mechanics, not the full90-second worker performance envelope.

  Run download/validation/coordination tests GREEN; commit `feat: collect bounded original bytes with SEC access outcomes`; obtain task Spec/Quality PASS.

**Checkpoint:** Original bytes and bounded retries/denial/quarantine/HTTP lifetime are verified locally. This is acquisition envelope proof, not row parser/global format or effective worker-capacity proof.

### Task 6: Discover actual sources and preserve failed-directory boundaries

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py`, `packages/sec-edgar-ingest/tests/test_discovery.py`, `fixtures/listings/empty.json`, `fixtures/listings/malformed.json`, `fixtures/listings/unsafe.json`, `fixtures/listings/leap-day.json`, `fixtures/listings/late-daily.json`; extend discovery helpers in `tests/support.py`. Do not alter Stage1 evidence tools or raw receipts.

**Interfaces:** Consumes Task 2 contracts, Task 3 stores/state and Task 5 RequestClient. Produces `DirectoryEntry(name: str, href: str, kind: Literal['dir','file'], size_label: str, modified_label: str)`; `parse_listing(url: str, body: bytes) -> tuple[DirectoryEntry,...]`; `quarter_of(day: date) -> str`; `quarter_span(start: str, end: str) -> tuple[str,...]`; `required_daily_quarters(today: date, handoff: date, boundary: date | None, pending_periods: tuple[str,...]) -> tuple[str,...]`; `advance_daily_boundary(previous: date | None, today: date, outcomes: tuple[DirectoryOutcome,...]) -> date | None`; `discover(settings: Settings, context: RunContext, mode: Literal['quarterly','daily'], discovery_id: str, client: RequestClient, state: AcquisitionState, objects: ObjectStore, today: date, refresh: bool = False) -> SourceWorkset`.

Extend `SourceWorkset` with `acquisition_mode: Literal['reuse_accepted','refresh']`, default `reuse_accepted`, included in its hash and codec. `discover(refresh=True)` freezes `refresh`; it is a collection primitive, not a reconciliation workflow. `AcquisitionState` gains `directory_progress(discovery_id: str, url: str) -> Versioned | None`, `record_directory(discovery_id: str, outcome: DirectoryOutcome, members: tuple[Source,...]) -> None`, `failed_directories() -> tuple[DirectoryOutcome,...]`, `daily_boundary() -> date | None`, `advance_boundary(candidate: date, discovery_id: str, outcomes: tuple[DirectoryOutcome,...]) -> None` using exact CAS. Support `discovery_harness(root: Path, responses: dict[str,list[ResponseSpec]]) -> DiscoveryHarness` with `run(mode: str, today: date, discovery_id: str) -> SourceWorkset`, `boundary`, `attempted_urls`, `requested_quarters`, `add_pending(source: Source)`.

- [x] **Step 1: Write/run failure-vs-empty, outage and overlap RED tests.** Start with a failed earlier quarter and a later successful directory:

  ```python
  import tempfile
  import unittest
  from datetime import date
  from pathlib import Path
  from support import discovery_harness, listing_response, failed_response

  class DiscoveryTests(unittest.TestCase):
      def test_later_success_cannot_cross_a_failed_directory(self):
          with tempfile.TemporaryDirectory() as directory:
              h = discovery_harness(Path(directory), {
                  '2026Q2': [failed_response(503)],
                  '2026Q3': [listing_response('2026Q3', ['master.20260930.idx'])],
                  '2026Q4': [listing_response('2026Q4', ['master.20261001.idx'])],
              })
              h.seed_boundary(date(2026, 3, 31))
              workset = h.run('daily', date(2026, 10, 6), 'outage-a')
              self.assertFalse(workset.discovery_complete)
              self.assertEqual(h.boundary, date(2026, 3, 31))
              self.assertTrue(any(d.outcome == 'discovery_failed' for d in workset.directories))
              self.assertIn('2026Q2', h.requested_quarters)

      def test_valid_empty_listing_has_a_distinct_outcome(self):
          h = discovery_harness(None, {'2026Q4': [listing_response('2026Q4', [])]})
          workset = h.run_single_directory('2026Q4')
          self.assertTrue(workset.discovery_complete)
          self.assertEqual(workset.members, ())
          self.assertEqual(workset.directories[0].outcome, 'no_new_sources')
  ```

  Define `listing_response(period: str, names: list[str]) -> ResponseSpec`, `failed_response(status: int) -> ResponseSpec`, and harness `seed_boundary(day: date)`, `run_single_directory(period: str) -> SourceWorkset`; `root=None` allocates an owned temporary fixture directory. They build real JSON `directory/item` schemas, include ancestor root/year listings, and use actual discovery code. Add first-run handoff/preceding-quarter tests, leap-day names, year/quarter rollover, multi-quarter outage, pending2015 source revisited in2026, failed ancestor hierarchy, malformed/untrusted listing, delayed file arriving on a fresh discovery session, missing requested quarter, duplicate/unsafe child, unsupported-only representation and absence without withdrawal. Retain RED.

- [x] **Step 2: Implement trusted listing traversal and source selection.** Production v1 parses the retained JSON family explicitly: top-level `directory` object, `name` and `parent-dir` strings, `item` list; each item has string `name/href/type/size/last-modified`, with type dir/file. Ignore provider ordering; preserve unparsed size/time labels as discovery metadata, never coverage dates or received sizes. The retained `parent-dir='../'` is metadata, not a URL to follow; accepting it does not permit a child href to escape. Check the directory name against the actual requested family/path. Refuse duplicate conflicting entries or entries with missing/wrong types.

  Start from trusted full-index/daily-index roots and follow validated actual year and QTR child hrefs. Generate expected quarter labels for coverage accounting, not source URLs. A missing requested year/quarter is an unresolved unit, not a successfully empty child listing. Select actual quarterly `master.zip` children; for the open quarter use its discovered full-index quarter-to-date child, recording the root bridge as an alternative, not assuming future root/quarter byte equality or collecting both as independent coverage. Daily selects actual `master.YYYYMMDD.idx` children with valid filename dates, not a constructed yesterday path. Filename dates select acquisition units only; later parsing can assign rows to other filing quarters.

  Optional `.sit/.z/.Z/.gz`/daily archive codecs are not silently selected. If a supported representation exists, ignore alternate codecs with a reason. If only an unsupported master representation exists, report an unresolved unsupported-source gap rather than `no_new_sources`. JSON absence/HTML/XML/malformed replies remain discovery failures with retained evidence; v1 does not claim fallback-format support. No parent rule requires pretending an unsuccessful JSON read was empty.

- [x] **Step 3: Persist discovery progress and immutable source worksets.** Pin today/end quarter/config once per discovery session. Save exact listing bytes and receipt metadata in content-addressed workset support paths before recording successful DirectoryProgress. Reopening `discovery_id` reuses verified successful listing outcomes and retries failed units; a new discovery ID refreshes listings to find delayed entries. An older immutable workset is never modified when a retry discovers more children: publish a new workset ID from the resumed discovery inventory and record its predecessor/session provenance.

> Deviation: AcquisitionState adds discovery_session/begin_discovery/directory_gap/finish_discovery and record_directory evidence/selection/expected_gap keywords; immutable origin provenance is verified on cached recovery.

  Required daily units are the union of open/preceding quarters, every quarter from handoff or last contiguous successful discovery boundary through today, all pending/failed source quarters, and unresolved directory units. Retain overlap with the baseline; do not filter pending older sources out by handoff. Bindings remain a later collection concern. The conservative boundary core is:

  ```python
  def advance_daily_boundary(previous, today, outcomes):
      if not outcomes or any(item.outcome == 'discovery_failed' for item in outcomes):
          return previous
      return today if previous is None else max(previous, today)
  ```

  This deliberately keeps the existing boundary on any required directory failure; successful per-directory progress is still durable and reused. The boundary means successful directory discovery through that run date, not complete filing coverage. `advance_boundary` uses exact CAS, validates the complete required-unit outcome set and never overwrites another discovery's outstanding gap with an unrelated success. Persist successful/no-source outcomes as evidence-backed statuses, and failures separately. `discover` observes sources in AcquisitionState, writes canonical immutable workset bytes via `put_once`, and sets `discovery_complete=False` while any requested unit is unresolved.

- [x] **Step 4: Verify retained schemas and recovery, commit/review.** Use exact retained listing bodies `SEC-0001`, `0002`, `0003`, `0028`, `0085`, `0086`, `0087`, `0088`, `0089`, `0104`, `0135`, `0137`, `0138`, `0139` under Stage1 `listings/`, with headers/intent sidecars. Rehash before read, and retain their provenance in a fixture manifest; do not present them as invented sources or global-format proof. Build synthetic empty/malformed/delayed responses separately and label them.

  Restart after one successful and one failed directory: successful original listing SHA and sources persist, failure is retried, new final workset differs and earlier immutable bytes remain. Test a concurrently advancing discovery boundary cannot erase an older required gap. Run discovery/config/URL/workset tests GREEN, commit `feat: discover durable source worksets without hiding gaps`, obtain task Spec/Quality PASS.

**Checkpoint:** Daily outage/handoff/overlap and explicit gaps are represented in acquisition state; no historical recovery horizon or full workflow/coverage claim is made.

### Task 7: Promote raw bytes, bind each member once and resume collection

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/collection.py`, `packages/sec-edgar-ingest/tests/test_collection.py`; extend collection/fault builders in `tests/support.py`. Modify `state.py` only for the Task 7 methods below and `worksets.py` only for actual snapshot-workset assembly.

**Interfaces:** Consumes SourceWorkset, RequestClient, envelope validator, AcquisitionState and ObjectStore. Produces `collect(workset: SourceWorkset, context: RunContext, settings: Settings, client: RequestClient, state: AcquisitionState, objects: ObjectStore, faults: Faults) -> CommandResult`; `collect_member(workset: SourceWorkset, source: Source, context: RunContext, settings: Settings, client: RequestClient, state: AcquisitionState, objects: ObjectStore, faults: Faults) -> Snapshot`; `raw_path(source: Source, sha256: str) -> str`; `AcquisitionState.reusable_snapshot(source: Source, envelope_version: str) -> Snapshot | None`; `AcquisitionState.promotion_receipt(workset_id: str, source_id: str) -> dict[str,object] | None`; `AcquisitionState.record_promotion(workset_id: str, snapshot: Snapshot) -> None`; `AcquisitionState.record_receipt(workset_id: str, source: Source, receipt: BodyReceipt, temporary_ref: str) -> None`; `AcquisitionState.staged_receipt(workset_id: str, source_id: str) -> dict[str,object] | None`. A promotion receipt is a repairable acquisition checkpoint, not a pin; Binding remains sole write-once selection authority.

Test helper `collection_harness(root: Path, responses: Sequence[ResponseSpec]) -> CollectionHarness` exposes `collect(workset: SourceWorkset) -> CommandResult`, `source_state`, `objects`, `fail_at(point: str)`, `fetch_count`, `reopen() -> CollectionHarness` and `snapshot_workset(result: CommandResult) -> SnapshotWorkset`. Errors use Task 2/5 codes; no failed member rewrites successful snapshot or binding state.

- [x] **Step 1: Write/run RED pinning and crash/resume tests.** A mutable latest snapshot changing between attempts must not change the workset's accepted pin:

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

- [x] **Step 2: Implement content-first ordering and write-once adoption.** Use these paths:

> Deviation: collection.stage_receipt adds optional keyword-only request_id; production supplies the verified actual transport reservation and omission fails closed, preserving BodyReceipt and write-once Binding identity.

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

- [x] **Step 3: Assemble immutable snapshot worksets only after all requested acquisition is complete.** Confirm source-workset digest/path, frozen config/image/parser/schema compatibility and every member's binding plus raw hash/length. The collector's new run/execution/attempt identifiers go into its result/Attempt; the snapshot workset retains immutable source-workset origin and versions, yielding the same snapshot-workset ID on retry.

  If discovery is incomplete or any member unbound, persist progress/gaps and return `incomplete` with no complete snapshot-workset reference. Retained successful downloads/pins remain reusable. Successful empty discovery emits a valid empty snapshot workset and `no_new_sources`; an empty failed directory yields `incomplete/discovery_failed`, never success. On all pins present, construct snapshot workset with exact source-member matching, write it create-only, then write the result. Crash after writing the snapshot workset can reuse its exact existing bytes. It does not imply a published generation or a processing state beyond downloaded.

- [x] **Step 4: Inject each durable-boundary crash, verify/review.** Test forced process exits after temporary receipt checkpoint, raw promotion, promotion record, snapshot record, binding, snapshot-workset write and before result write. Reopen stores and rerun with the same source workset; assert exact pins and raw hashes remain, no successful member is fetched again, unresolved members alone continue, counters/gaps are honest and the final snapshot workset is byte-identical. Raw-only retained validation/reuse uses a sender that raises if called. Test two concurrent collectors with a forced CAS race and changed bytes; only the winner pin reaches the workset.

  Run collection/state/storage/download/workset tests GREEN. Commit `feat: pin immutable snapshots and resume incomplete collection`; obtain task Spec/Quality PASS.

**Checkpoint:** Restartable acquisition and exact immutable snapshot inputs are proven. Row-level replay, dataset publication and reconciliation remain unimplemented later-stage contracts.

### Task 8: Deliver acquisition commands, durable results and the Stage 2 proof bundle

**Ownership/files:** Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `README.md`, `packages/sec-edgar-ingest/README.md`, `.gitignore`; create `results.py`, `packages/sec-edgar-ingest/tests/test_cli.py`, `test_acquisition_processes.py`, `fixtures/acquisition/manifest.json`, `scripts/check-sec-edgar-ingest.sh`, `docs/runbooks/sec-edgar-ingest-acquisition.md`; retain execution outputs under `specs/evidence/sec-filing-index-ingestion/stage-2/verification/` and summary `specs/evidence/sec-filing-index-ingestion/stage-2/verification.md`. No production CI provider, infrastructure, schedules or live source runs are provisioned.

**Interfaces:** Consumes all earlier tasks. Final `main(argv: Sequence[str] | None = None) -> int` has help/version plus `discover` and `collect`. Common arguments: `--config PATH`, `--run-id`, `--execution-id`, `--attempt-id`, `--deadline UTC`. `discover` also requires `--mode quarterly|daily`, `--discovery-id`; `--refresh` freezes explicit acquisition refresh. `collect` requires `--workset REF` (object path to an immutable source workset). Fixture mode requires `--fixture-pack PATH`; optional `--state-dir PATH`/`--today YYYY-MM-DD` are fixture-only and refuse in Azure mode. `transform`/`publish` are not offered before their implementations.

`results.py` produces `write_result(result: CommandResult, objects: ObjectStore, state: AcquisitionState) -> str`, `read_result(path: str, objects: ObjectStore) -> CommandResult`, `exit_code(outcome: str) -> int`, and `log_event(context: RunContext, event: str, fields: dict[str,object]) -> None`. Results are immutable at `runs/sec/<run-id>/<command>/<attempt-id>/result.json`. Return stdout as one JSON object containing outcome, result reference and workset references; logs are structured JSON to stderr. Resume a completed command attempt by returning its matching existing result; use a new attempt ID to continue an earlier terminal incomplete result. Frozen worksets/pins survive either case.

`FixturePack.load(path: Path) -> FixturePack` is defined in `download.py`, containing validated `url -> tuple[ResponseSpec,...]` mappings and no live fallback. Manifest v1 fields are `fixture_version='sec-acquisition-fixture-v1'`, `provenance='synthetic'|'retained-stage-1'`, `responses: dict[str,list[dict]]`; response dict fields are `status`, `headers`, `body_path`, `body_sha256`, optional `fault`. Body paths are safe relative files beneath the manifest directory or an explicitly validated retained-evidence root. Missing/exhausted mappings raise a fixture error; they never fetch the URL. `FixturePack.sender(state: StateStore) -> Sender` conditionally persists each mapping's response cursor under an explicitly fixture-only record, so a restarted CLI can progress from a scripted404 to its later successful body. This cursor is never production acquisition state or live authorization. The production RequestClient still validates SEC source URLs while the fixture sender substitutes responses after that validation.

- [x] **Step 1: Write/run CLI and result-integrity RED tests.** Validate before constructing a backend, and report unresolved work with a non-success exit:

  ```python
  import json
  import unittest
  from support import cli_harness

  class CliTests(unittest.TestCase):
      def test_failed_discovery_is_not_empty_success(self):
          h = cli_harness(fixture='failed-earlier-quarter')
          completed = h.discover()
          self.assertEqual(completed.returncode, 3)
          result = json.loads(completed.stdout)
          self.assertEqual(result['outcome'], 'discovery_failed')
          self.assertIsNone(result['snapshot_workset_ref'])
          self.assertTrue(h.read_durable_result(result['result_ref']).gaps)

      def test_missing_identity_creates_no_external_clients(self):
          h = cli_harness(fixture='valid-quarter-and-daily', missing_user_agent=True)
          completed = h.discover()
          self.assertEqual(completed.returncode, 2)
          self.assertEqual(h.external_client_constructions, 0)
  ```

  Define `cli_harness(fixture: str, missing_user_agent: bool = False) -> CliHarness` with `discover() -> CompletedProcess[str]`, `collect(workset_ref: str) -> CompletedProcess[str]`, `read_durable_result(ref: str) -> CommandResult`, `external_client_constructions: int`. It exercises actual CLI argument parsing and subprocess invocation against fixture config, not a replacement command. Add installed-wheel invocation, correct result correlation tuple/hash, unknown/missing workset, completed-attempt ID reuse, snapshot references independent of source latest, no-new-sources0 vs failed-directory3, pending4044, retry exhaustion5, access block6, quarantine7 and ownership-loss8. Retain RED.

- [x] **Step 2: Wire commands and explicit acquisition outcomes.** Parse arguments, load/validate config/context, select an explicit backend, then construct client/state/coordinator. Discovery outputs its source workset even if incomplete and returns an honest gap-bearing result. Collection preserves source workset pins and reports the matching snapshot workset only when complete. Catch named acquisition errors; unexpected exceptions retain an attempt error and return9, never manufacture a successful durable result.

  ```python
  EXIT_CODES = {
      'success': 0, 'no_new_sources': 0,
      'configuration': 2,
      'discovery_failed': 3, 'incomplete': 3,
      'pending': 4,
      'retry_exhausted': 5, 'deferred': 5, 'throttled': 5,
      'access_blocked': 6,
      'quarantined': 7, 'invalid_source': 7,
      'ownership_lost': 8,
      'state_conflict': 9, 'internal_error': 9,
  }

  def exit_code(outcome: str) -> int:
      return EXIT_CODES[outcome]

  def write_result(result, objects, state):
      path = (f'runs/sec/{result.context.run_id}/{result.context.command}/'
              f'{result.context.attempt_id}/result.json')
      objects.put_once(path, result.to_json())
      state.finish_attempt(result)
      return path
  ```

  `CommandResult.to_json() -> bytes` and `.from_json(body: bytes) -> CommandResult` use the Task 2 canonical codec; exact same-existing-result conflicts are harmless, different content for the same attempt is a refusal. Result writes precede ancillary attempt completion so a crash can repair the attempt from that immutable result; this is result recovery, not a dataset publication pointer. Every result includes counters, explicit gaps and run/execution/attempt/image/config/versions. A resumed collection's result names current command context and source/snapshot workset identities; it cannot claim its upstream discover command was the collecting execution. Pre-validation configuration errors can write structured stderr without external storage I/O.

  Aggregate incomplete results keep every member outcome; a run-wide block/ownership loss takes precedence over generic incomplete, and a single-source404 may be `pending`. A multi-source partial result has `incomplete` with pending/error counts. Discovery failures stay `discovery_failed`; an authenticated, successfully decoded empty fixture directory is `no_new_sources`. No acquisition outcome claims transformation, publication or withdrawal.

- [x] **Step 3: Add the repeatable offline check entry point and real process fixtures.** `scripts/check-sec-edgar-ingest.sh` is a local/CI entry point; future CI can call it without SEC access. Its executable content is:

  ```sh
  #!/bin/sh
  set -eu
  uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
  uv build --offline --all-packages
  uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
  uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
  uv run --offline --frozen --package sec-edgar-ingest python -m compileall -q packages/sec-edgar-ingest/src
  git diff --check
  ```

  Preinstall/lock build requirements once during authorized Task 1 dependency setup; missing offline cache is a prerequisite failure, not authority to contact SEC or quietly change pins. Unit-test support blocks unapproved external network/auth and allows only the expressly bounded loopback process fixture. Scripted Azure transports remain offline; CI has no Azure/SEC credentials.

  In `test_acquisition_processes.py`, spawn three collectors with independent clients/processes and shared durable local state. Barrier-force a competing request and a binding insert race. Pause one sender with a loopback server that retains the connection; lose its lease/kill the parent, acquire a successor, observe zero successor requests through the persisted unsafe interval, then release/timeout the old sender and observe successor progress. Assert one active issuer at every event, shared pacing across retry/discovery/download, daily next-turn priority and unchanged winner pin after restart. Include the independent child hard deadline test from Task 5 and a stale permit awakened after its allowed start. Do not satisfy the test with only a mutex counter or a final successful result. Retain timestamped interval/ownership traces, child exit receipts and exact artifact hashes.

  Build both wheel and sdist with `uv build --all-packages`; inspect artifact names/metadata and install the wheel into a fresh temporary environment using the pinned cached dependencies. Run import, installed entry point and fixture discover/collect there so tests do not pass only through editable source imports.

- [x] **Step 4: Run a complete fixture CLI sequence and retain proof.** With a synthetic pack covering one archived quarter, the handoff daily source and a pending delayed source, invoke:

> Deviation: Generated synthetic configs keep relative storage.root with absolute fixture --state-dir and explicit clock/deadline override flags; quarterly uses 2015Q1 and owner-approved dailyend=open uses 2026-10-06, with the exact Yes receipt retained.

  ```python
  import json
  import shutil
  import subprocess
  import tempfile
  from pathlib import Path

  with tempfile.TemporaryDirectory(prefix='sec-edgar-stage-2-') as temporary:
      root = Path(temporary)
      config = json.loads(Path('conf/sec-edgar-ingest.yaml').read_text())
      config['backfill'] = {'start_quarter': '2015Q1', 'end_quarter': '2015Q1'}
      config['storage']['root'] = str(root / 'state')
      config_path = root / 'fixture-config.json'
      config_path.write_text(json.dumps(config))
      common = ['--config', str(config_path), '--fixture-pack',
                'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json',
                '--deadline', '2099-01-01T00:00:00Z']
      prefix = ['uv', 'run', '--offline', '--frozen', '--package',
                'sec-edgar-ingest', 'sec-edgar-ingest']

      def invoke(command, arguments, expected_exit):
          argv = prefix + [command] + common + arguments
          completed = subprocess.run(argv, capture_output=True, text=True)
          label = arguments[arguments.index('--attempt-id') + 1]
          (root / (label + '.argv.json')).write_text(json.dumps(argv))
          (root / (label + '.stdout')).write_text(completed.stdout)
          (root / (label + '.stderr')).write_text(completed.stderr)
          (root / (label + '.exit.json')).write_text(json.dumps({'exit': completed.returncode}))
          assert completed.returncode == expected_exit, completed.stderr
          return json.loads(completed.stdout)

      try:
          discovered = invoke('discover', ['--today', '2026-10-06', '--mode', 'quarterly',
              '--discovery-id', 'fixture-quarter', '--run-id', 'fixture-run',
              '--execution-id', 'fixture-discover', '--attempt-id', 'discover-1'], 0)
          first = invoke('collect', ['--workset', discovered['source_workset_ref'],
              '--run-id', 'fixture-run', '--execution-id', 'fixture-collect',
              '--attempt-id', 'collect-1'], 0)
          replay = invoke('collect', ['--workset', discovered['source_workset_ref'],
              '--run-id', 'fixture-run', '--execution-id', 'fixture-collect-retry',
              '--attempt-id', 'collect-2'], 0)
          assert replay['snapshot_workset_ref'] == first['snapshot_workset_ref']
          daily = invoke('discover', ['--today', '2026-10-06', '--mode', 'daily',
              '--discovery-id', 'fixture-daily', '--run-id', 'fixture-daily',
              '--execution-id', 'fixture-daily-discover', '--attempt-id', 'daily-discover-1'], 0)
          pending = invoke('collect', ['--workset', daily['source_workset_ref'],
              '--run-id', 'fixture-daily', '--execution-id', 'fixture-daily-collect',
              '--attempt-id', 'daily-collect-1'], 3)
          assert pending['outcome'] == 'incomplete'
          recovered = invoke('collect', ['--workset', daily['source_workset_ref'],
              '--run-id', 'fixture-daily', '--execution-id', 'fixture-daily-retry',
              '--attempt-id', 'daily-collect-2'], 0)
          assert recovered['snapshot_workset_ref'] is not None
      finally:
          retained = Path('specs/evidence/sec-filing-index-ingestion/stage-2/verification') / root.name
          retained.parent.mkdir(parents=True, exist_ok=True)
          shutil.copytree(root, retained)
          (retained / 'retention-map.json').write_text(json.dumps({'original_root': str(root), 'retained_root': str(retained)}))
  ```

  The pack includes valid full-index root/year/QTR1 listings for2015Q1 and its ZIP, plus daily root/year/QTR3/QTR4 listings for2026 with handoff `master.20261001.idx` and delayed `master.20261002.idx`. The handoff body is immediately valid; the delayed body returns404 once then a valid IDX through its persisted fixture cursor. The previous-quarter listing is valid, even when it contributes no post-handoff source. The narrow fixture backfill is labelled as a fixture subset, not a revision of the accepted intended/development range. The distant deadline is fixture-only; Azure rejects that provenance and deadline. The finally block retains command failures as well as successful outputs before temporary cleanup; retain bundle hashes and its explicit original-to-retained root map. Assert completed earlier members make no new requests and final hashes/pins remain stable. This deterministic sequence establishes no live SEC availability, historical coverage or SLA.

  Write `verification.md` naming source/config/review revisions, local OS/Python/SDK versions, commands/exits, raw-byte hashes, acquired/pending/failed/quarantine counts, event traces and limits. Label synthetic vs retained receipts and mocked Azure vs real local process proof. Keep S7-11/12/14/18/19 and the rest of the22 checks reserved: actual shared owner-wide behavior, Azure lease/in-flight/CAS/HNS operations, identities/network, worker measurements and integrated smoke/replay are not passed by this bundle.

- [x] **Step 5: Document acquisition recovery, verify and commit/review.** README/runbook give exact install/build/fixture commands, JSON-compatible YAML format, shared namespace/budget obligations, source-vs-snapshot identities, failure/valid-empty meanings, pending older work, guard violations, raw archive retention, result references and stopped-ownership/takeover handling. Explain safe resumption with existing workset/new attempt, and that failed-directory discovery produces a new immutable source workset on successful recovery. Do not instruct deletion of manifests, anonymous keys, independent direct Requests sessions, blind retries or a mutable latest ETL input.

> Deviation: The latest post-fix prescribed check passed 302 tests; fresh installed-wheel and approved combined/process/recovery proofs cover the final source, and fresh GPT-6.1 Max default-role fallback review closed all findings; same-family Codex CLI second seat was explicitly skipped.

  Run `scripts/check-sec-edgar-ingest.sh` GREEN once after the last Task 8 change and inspect full output. Capture primary-checkout preservation status/hashes separately from execution-branch status. Commit `feat: expose durable acquisition commands and fixture verification` with only Task 8 paths; obtain task Spec/Quality PASS.

**Checkpoint:** Runnable discover/collect commands, meaningful local process/recovery evidence and workspace wheel/sdist/CLI checks pass. Stage 2 stays unticked until the final review/completion gates below.

## Final whole-branch review and Stage 2 completion gates

These gates execute only after all eight tasks and their per-task reviews. They are not planning-time accomplishments.

1. Run the complete offline check entry point after the last implementation change; retain the actual result. If any required build, CLI, concurrency, takeover, invalid-input, discovery-gap or recovery test fails, resolve it before review/completion. No safeguard deferral can substitute for Stage 2's exit.
2. Compute the branch's actual merge base against its intended base and reviewed HEAD. Generate a whole-branch diff package for that range. Dispatch a **fresh read-only `code-reviewer` with `model='gpt-6.1-sol'`, `reasoning_effort='max'`, `fork_turns='none'`** using `requesting-code-review`'s template; supply this plan/spec, parent/F1 constraints, task reports, proof bundle and Minor findings ledger. Require an explicit whole-branch verdict, path/line findings and coverage of the acquisition contracts. Do not inherit this planning session or silently substitute another model.
3. Follow the review skill's second-opinion rule: in a Codex execution session it expressly skips another same-family Codex CLI run. Record that reason; the required GPT-6.1 Max whole-branch reviewer still runs. If executing under another model family, launch the prescribed Codex second opinion concurrently at the same base/HEAD. Do not mutate the branch during either review. Merge actual findings, fix Critical/Important issues, decide remaining Minor findings explicitly, rerun covering tests after fixes and obtain scoped re-review. Review cannot waive failed Stage 2 exits.
4. Only after all reviews resolve, run `writing-plans`' resolve-before-defer gate. Batch any genuinely missing owner decisions with remaining plan/review questions. Preserve safeguards; unresolved required work blocks completion. Review leftovers cannot disappear through a tick or undocumented deferral. Run backlog health/triage as prescribed even if nothing is deferred.
5. Record actual completion date and evidence/review references in the **Stage 2-specific implementing spec**, then complete/retire plan2 and that spec under the completion protocol. Final paths are `specs/plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md` and `specs/completed/sec-filing-index-ingestion-stage-2-spec.md`; repair relative links for both depths. Parent design spec, ADR, Stage1 finding/evidence and roadmap stay active.
6. Only after the authoritative Stage2 completion stamp exists, reconcile/tick its local roadmap entry and revalidate later unticked stages for consistency with shipped interfaces. Keep the roadmap untracked/local unless the owner separately authorizes its inclusion. Record a retained Stage2 completion receipt with actual stamp/reference/hash, since the roadmap's local checkbox is not branch-shared completion authority. Do not interpret this consistency pass as authority to begin or plan Stage 3.
7. Use `finishing-a-development-branch` for a deliberate integration choice and isolated-worktree cleanup. Preserve the primary checkout's four deletions and any other local edits; do not stash/reset/restore them to force an integration. Commit/stage only named plan-owned artifacts, never `git add .`/`git add -A`. If primary drift makes integration unsafe, report the concrete conflict and leave the isolated work recoverable. A feature branch/PR carries retirement/stamp evidence atomically; if the branch is discarded, it cannot establish completed Stage2.

Stage2's completion stamp must reference plan2 and the actual verification/review evidence. A checked roadmap box, passing mock Storage test or successful job-start request alone does not complete this stage or the parent roadmap.

## Coverage and planning self-review

| Stage 2 requirement/parent contract | Planned task/evidence |
|---|---|
| Single package, distribution/import/CLI; accepted D10 | Task1; Task8 installed wheel and CLI checks |
| Validated range/handoff/identity/versions/defaults/guards | Task2; Task8 no-client-on-config-error tests |
| Discovery from actual children, quarter/leap/outage/pending/overlap | Task6; failure-vs-empty and boundary recovery fixtures |
| Shared all-request budget, daily turn, lease loss/in-flight/takeover | Tasks4–5; Task8 coordinated process event traces |
| Exact original bytes, SHA/validators, raw-before-state/quarantine | Tasks3/5/7; retained-body/invalid/truncated/cap fixtures |
| Durable source/attempt state, exact CAS, no cross-service transaction | Task3; Task7 crash boundary fixtures |
| Immutable source worksets, write-once pins, snapshot worksets | Tasks2/6/7; pin race, changed latest, raw-only retry tests |
| Failed discovery/404/denial/exhaustion/deferred/ownership outcomes | Tasks5–8; durable gap/count/exit-code tests |
| Local proof distinct from actual Azure/worker proof | Every checkpoint; Task8 verification limits; final review |
| Per-task TDD/review; final GPT-6.1 Max review; gated stamp/retirement | Every task and final completion gates |

Self-review before handoff must confirm exact interfaces/code references, every required deliverable, required tests rather than implementation-mirroring assertions, all step checkboxes empty, no implementation files touched, no scope/approval invented and no source/compute access reopened. Missing SDK signatures are handled by Task3's explicit installed-code gate; accepted production bindings are carried forward, not requested again. The owner answered both genuinely missing Stage2 choices and approved Plan 2; implementation remains for the fresh execution session.

## Fresh-session execution prompt

Lowell Mason approved Plan 2 on 2026-10-06 America/New_York. Use this prompt in a fresh task/session so execution starts from this complete file rather than the planning history:

```text
Execute only Stage 2 of the SEC filing-index ingestion roadmap in /Users/lowell/Projects/sec-edgar, using subagent-driven-development against specs/plans/2-sec-filing-index-ingestion-stage-2-spec.md and its Stage 2-specific implementing spec specs/sec-filing-index-ingestion-stage-2-spec.md. Lowell Mason approved Plan 2 on 2026-10-06 America/New_York with the message “Approved”; the approval record is in both documents. Proceed under that approval without requesting it again.

Recheck the current base and local changes. The planning baseline was main/cached origin/main at 17731c33961f8ae3669e472765c1d1745ade44b4. Preserve the untracked/local roadmap and four original deletions under packages/sec-edgar-index-ingest/, plus any subsequent edits. Do not restore, stash/reset or stage unrelated changes. Use using-git-worktrees for execution isolation according to the owner's approved execution choice, preferring native managed tools. Do not infer that a fresh worktree copied the untracked documents or deletion state.

Read the parent design spec/ADR and accepted Stage 1 final acceptance/completion records as required by the plan. Stage 1 F1 accepted 2026-10-05 America/New_York; completed 2026-10-06. Its finding hash is 939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff and accepted manifest hash is 124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131. Capture-time pending statements are historical. Keep client/download scaffolds excluded but intact; approved acquisition guards are 90 seconds / 64 MiB received / 512 MiB expanded.

Execute tasks 1–8 in order, with explicit file ownership, red/green tests and fresh per-task Spec/Quality reviews. Preserve actual interfaces/deviations in the SDD progress ledger. All SEC-like fixture traffic uses one coordinator; no delegated independent issuers/budgets. Use retained evidence/scripted transports/local process fixtures; Stage1 live SEC and temporary compute authorizations are closed. Fresh necessary live access needs a concrete bounded owner authorization. No Azure provisioning, image build/push facility, worker measurement or schedule activation is authorized by this prompt.

Run the required workspace build/installed-wheel/CLI, failure/concurrency/takeover and crash/resumption checks. Obtain a fresh read-only whole-branch review on GPT-6.1 Max (gpt-6.1-sol, effort max), resolve findings and then run the gated Stage 2-specific completion/retirement protocol. Keep local fixture proof separate from all 22 reserved Stage 7 effective Azure/worker checks. Stage 2 stays unticked until its prescribed gates pass. Preserve parent design/ADR/roadmap at retirement. Stop at the completed Stage 2 boundary; do not begin or plan Stage 3.
```

Planning authorization ends with the approval presentation. Do not execute this prompt as a side effect of saving the plan.
