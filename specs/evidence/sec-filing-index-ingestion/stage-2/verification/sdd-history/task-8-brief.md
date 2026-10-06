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

### Task 8: Deliver acquisition commands, durable results and the Stage 2 proof bundle

**Ownership/files:** Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`, `README.md`, `packages/sec-edgar-ingest/README.md`, `.gitignore`; create `results.py`, `packages/sec-edgar-ingest/tests/test_cli.py`, `test_acquisition_processes.py`, `fixtures/acquisition/manifest.json`, `scripts/check-sec-edgar-ingest.sh`, `docs/runbooks/sec-edgar-ingest-acquisition.md`; retain execution outputs under `specs/evidence/sec-filing-index-ingestion/stage-2/verification/` and summary `specs/evidence/sec-filing-index-ingestion/stage-2/verification.md`. No production CI provider, infrastructure, schedules or live source runs are provisioned.

**Interfaces:** Consumes all earlier tasks. Final `main(argv: Sequence[str] | None = None) -> int` has help/version plus `discover` and `collect`. Common arguments: `--config PATH`, `--run-id`, `--execution-id`, `--attempt-id`, `--deadline UTC`. `discover` also requires `--mode quarterly|daily`, `--discovery-id`; `--refresh` freezes explicit acquisition refresh. `collect` requires `--workset REF` (object path to an immutable source workset). Fixture mode requires `--fixture-pack PATH`; optional `--state-dir PATH`/`--today YYYY-MM-DD` are fixture-only and refuse in Azure mode. `transform`/`publish` are not offered before their implementations.

`results.py` produces `write_result(result: CommandResult, objects: ObjectStore, state: AcquisitionState) -> str`, `read_result(path: str, objects: ObjectStore) -> CommandResult`, `exit_code(outcome: str) -> int`, and `log_event(context: RunContext, event: str, fields: dict[str,object]) -> None`. Results are immutable at `runs/sec/<run-id>/<command>/<attempt-id>/result.json`. Return stdout as one JSON object containing outcome, result reference and workset references; logs are structured JSON to stderr. Resume a completed command attempt by returning its matching existing result; use a new attempt ID to continue an earlier terminal incomplete result. Frozen worksets/pins survive either case.

`FixturePack.load(path: Path) -> FixturePack` is defined in `download.py`, containing validated `url -> tuple[ResponseSpec,...]` mappings and no live fallback. Manifest v1 fields are `fixture_version='sec-acquisition-fixture-v1'`, `provenance='synthetic'|'retained-stage-1'`, `responses: dict[str,list[dict]]`; response dict fields are `status`, `headers`, `body_path`, `body_sha256`, optional `fault`. Body paths are safe relative files beneath the manifest directory or an explicitly validated retained-evidence root. Missing/exhausted mappings raise a fixture error; they never fetch the URL. `FixturePack.sender(state: StateStore) -> Sender` conditionally persists each mapping's response cursor under an explicitly fixture-only record, so a restarted CLI can progress from a scripted404 to its later successful body. This cursor is never production acquisition state or live authorization. The production RequestClient still validates SEC source URLs while the fixture sender substitutes responses after that validation.

- [ ] **Step 1: Write/run CLI and result-integrity RED tests.** Validate before constructing a backend, and report unresolved work with a non-success exit:

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

- [ ] **Step 2: Wire commands and explicit acquisition outcomes.** Parse arguments, load/validate config/context, select an explicit backend, then construct client/state/coordinator. Discovery outputs its source workset even if incomplete and returns an honest gap-bearing result. Collection preserves source workset pins and reports the matching snapshot workset only when complete. Catch named acquisition errors; unexpected exceptions retain an attempt error and return9, never manufacture a successful durable result.

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

- [ ] **Step 3: Add the repeatable offline check entry point and real process fixtures.** `scripts/check-sec-edgar-ingest.sh` is a local/CI entry point; future CI can call it without SEC access. Its executable content is:

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

- [ ] **Step 4: Run a complete fixture CLI sequence and retain proof.** With a synthetic pack covering one archived quarter, the handoff daily source and a pending delayed source, invoke:

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

- [ ] **Step 5: Document acquisition recovery, verify and commit/review.** README/runbook give exact install/build/fixture commands, JSON-compatible YAML format, shared namespace/budget obligations, source-vs-snapshot identities, failure/valid-empty meanings, pending older work, guard violations, raw archive retention, result references and stopped-ownership/takeover handling. Explain safe resumption with existing workset/new attempt, and that failed-directory discovery produces a new immutable source workset on successful recovery. Do not instruct deletion of manifests, anonymous keys, independent direct Requests sessions, blind retries or a mutable latest ETL input.

  Run `scripts/check-sec-edgar-ingest.sh` GREEN once after the last Task 8 change and inspect full output. Capture primary-checkout preservation status/hashes separately from execution-branch status. Commit `feat: expose durable acquisition commands and fixture verification` with only Task 8 paths; obtain task Spec/Quality PASS.

**Checkpoint:** Runnable discover/collect commands, meaningful local process/recovery evidence and workspace wheel/sdist/CLI checks pass. Stage 2 stays unticked until the final review/completion gates below.
