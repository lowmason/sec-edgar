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

### Task 2: Validate acquisition settings and freeze identity/workset contracts

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/config.py`, `models.py`, `urls.py`, `worksets.py`; `conf/sec-edgar-ingest.yaml`; `packages/sec-edgar-ingest/tests/support.py`, `test_config.py`, `test_urls.py`, `test_worksets.py` and `fixtures/config/local.json`.

**Interfaces:** Produces the records in Cross-task schemas; `Settings.from_mapping(value: dict[str,object]) -> Settings`; `load_config(path: Path) -> Settings`; `pin_context(settings: Settings, context: RunContext, today: date) -> tuple[RunContext,str]`; `canonical_source_url(url: str, kind: str) -> str`; `canonical_listing_url(url: str) -> str`; `child_url(parent: str, href: str, name: str, is_directory: bool) -> str`; `source_id(url: str) -> str`; `encode_workset(workset: SourceWorkset | SnapshotWorkset) -> bytes`; `decode_source_workset(body: bytes) -> SourceWorkset`; `decode_snapshot_workset(body: bytes) -> SnapshotWorkset`; `make_source_workset(context: RunContext, end_quarter: str, discovery_id: str, members: tuple[Source,...], directories: tuple[DirectoryOutcome,...], overlap_from: date) -> SourceWorkset`; `make_snapshot_workset(source: SourceWorkset, snapshots: tuple[Snapshot,...]) -> SnapshotWorkset`. Produces test builders `fixture_settings(**overrides) -> Settings`, `fixture_context(command='collect', priority='backfill') -> RunContext`, `fixture_source(period='2015Q1', kind='quarterly') -> Source`, `fixture_workset(members: tuple[Source,...], discovery_complete=True) -> SourceWorkset`.

- [ ] **Step 1: Write/run validation and immutability RED cases.** A config error must precede any credential/client/transport factory call. Include this behavior, adapting unittest method placement without changing assertions:

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

- [ ] **Step 2: Implement canonical identities and workset codecs.** Use frozen dataclasses plus deeply immutable nested mappings/tuples for the declared schemas and explicit complete mapping conversion; detached serializers cannot mutate the stored/workset object. This identity core is shared by source/workset records:

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

- [ ] **Step 3: Implement validated settings and explicit fixture configuration.** Configuration v1 accepts JSON syntax, a valid YAML 1.2 subset, in `conf/sec-edgar-ingest.yaml`; load with stdlib `json.loads` and explain the syntax restriction in the README. Do not add an unverified YAML dependency. Use nested typed settings with `to_mapping`, an effective config SHA, and these fixture values:

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

- [ ] **Step 4: Complete the contract matrix, commit/review.** Run config/URL/workset tests GREEN, including deepcopy/frozen-record checks, same URL stable ID, changed content/version different workset ID, UTC/quarter/leap-day boundaries and two callers with mismatched namespaces refusing access. Add only named files; commit `feat: define validated acquisition and workset contracts`; obtain task Spec/Quality PASS.

**Checkpoint:** Later tasks can depend on explicit versioned types and serialization; malformed configuration reaches no external I/O.
