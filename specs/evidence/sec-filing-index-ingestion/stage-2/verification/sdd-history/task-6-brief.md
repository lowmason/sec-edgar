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

### Task 6: Discover actual sources and preserve failed-directory boundaries

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py`, `packages/sec-edgar-ingest/tests/test_discovery.py`, `fixtures/listings/empty.json`, `fixtures/listings/malformed.json`, `fixtures/listings/unsafe.json`, `fixtures/listings/leap-day.json`, `fixtures/listings/late-daily.json`; extend discovery helpers in `tests/support.py`. Do not alter Stage1 evidence tools or raw receipts.

**Interfaces:** Consumes Task 2 contracts, Task 3 stores/state and Task 5 RequestClient. Produces `DirectoryEntry(name: str, href: str, kind: Literal['dir','file'], size_label: str, modified_label: str)`; `parse_listing(url: str, body: bytes) -> tuple[DirectoryEntry,...]`; `quarter_of(day: date) -> str`; `quarter_span(start: str, end: str) -> tuple[str,...]`; `required_daily_quarters(today: date, handoff: date, boundary: date | None, pending_periods: tuple[str,...]) -> tuple[str,...]`; `advance_daily_boundary(previous: date | None, today: date, outcomes: tuple[DirectoryOutcome,...]) -> date | None`; `discover(settings: Settings, context: RunContext, mode: Literal['quarterly','daily'], discovery_id: str, client: RequestClient, state: AcquisitionState, objects: ObjectStore, today: date, refresh: bool = False) -> SourceWorkset`.

Extend `SourceWorkset` with `acquisition_mode: Literal['reuse_accepted','refresh']`, default `reuse_accepted`, included in its hash and codec. `discover(refresh=True)` freezes `refresh`; it is a collection primitive, not a reconciliation workflow. `AcquisitionState` gains `directory_progress(discovery_id: str, url: str) -> Versioned | None`, `record_directory(discovery_id: str, outcome: DirectoryOutcome, members: tuple[Source,...]) -> None`, `failed_directories() -> tuple[DirectoryOutcome,...]`, `daily_boundary() -> date | None`, `advance_boundary(candidate: date, discovery_id: str, outcomes: tuple[DirectoryOutcome,...]) -> None` using exact CAS. Support `discovery_harness(root: Path, responses: dict[str,list[ResponseSpec]]) -> DiscoveryHarness` with `run(mode: str, today: date, discovery_id: str) -> SourceWorkset`, `boundary`, `attempted_urls`, `requested_quarters`, `add_pending(source: Source)`.

- [ ] **Step 1: Write/run failure-vs-empty, outage and overlap RED tests.** Start with a failed earlier quarter and a later successful directory:

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

- [ ] **Step 2: Implement trusted listing traversal and source selection.** Production v1 parses the retained JSON family explicitly: top-level `directory` object, `name` and `parent-dir` strings, `item` list; each item has string `name/href/type/size/last-modified`, with type dir/file. Ignore provider ordering; preserve unparsed size/time labels as discovery metadata, never coverage dates or received sizes. The retained `parent-dir='../'` is metadata, not a URL to follow; accepting it does not permit a child href to escape. Check the directory name against the actual requested family/path. Refuse duplicate conflicting entries or entries with missing/wrong types.

  Start from trusted full-index/daily-index roots and follow validated actual year and QTR child hrefs. Generate expected quarter labels for coverage accounting, not source URLs. A missing requested year/quarter is an unresolved unit, not a successfully empty child listing. Select actual quarterly `master.zip` children; for the open quarter use its discovered full-index quarter-to-date child, recording the root bridge as an alternative, not assuming future root/quarter byte equality or collecting both as independent coverage. Daily selects actual `master.YYYYMMDD.idx` children with valid filename dates, not a constructed yesterday path. Filename dates select acquisition units only; later parsing can assign rows to other filing quarters.

  Optional `.sit/.z/.Z/.gz`/daily archive codecs are not silently selected. If a supported representation exists, ignore alternate codecs with a reason. If only an unsupported master representation exists, report an unresolved unsupported-source gap rather than `no_new_sources`. JSON absence/HTML/XML/malformed replies remain discovery failures with retained evidence; v1 does not claim fallback-format support. No parent rule requires pretending an unsuccessful JSON read was empty.

- [ ] **Step 3: Persist discovery progress and immutable source worksets.** Pin today/end quarter/config once per discovery session. Save exact listing bytes and receipt metadata in content-addressed workset support paths before recording successful DirectoryProgress. Reopening `discovery_id` reuses verified successful listing outcomes and retries failed units; a new discovery ID refreshes listings to find delayed entries. An older immutable workset is never modified when a retry discovers more children: publish a new workset ID from the resumed discovery inventory and record its predecessor/session provenance.

  Required daily units are the union of open/preceding quarters, every quarter from handoff or last contiguous successful discovery boundary through today, all pending/failed source quarters, and unresolved directory units. Retain overlap with the baseline; do not filter pending older sources out by handoff. Bindings remain a later collection concern. The conservative boundary core is:

  ```python
  def advance_daily_boundary(previous, today, outcomes):
      if not outcomes or any(item.outcome == 'discovery_failed' for item in outcomes):
          return previous
      return today if previous is None else max(previous, today)
  ```

  This deliberately keeps the existing boundary on any required directory failure; successful per-directory progress is still durable and reused. The boundary means successful directory discovery through that run date, not complete filing coverage. `advance_boundary` uses exact CAS, validates the complete required-unit outcome set and never overwrites another discovery's outstanding gap with an unrelated success. Persist successful/no-source outcomes as evidence-backed statuses, and failures separately. `discover` observes sources in AcquisitionState, writes canonical immutable workset bytes via `put_once`, and sets `discovery_complete=False` while any requested unit is unresolved.

- [ ] **Step 4: Verify retained schemas and recovery, commit/review.** Use exact retained listing bodies `SEC-0001`, `0002`, `0003`, `0028`, `0085`, `0086`, `0087`, `0088`, `0089`, `0104`, `0135`, `0137`, `0138`, `0139` under Stage1 `listings/`, with headers/intent sidecars. Rehash before read, and retain their provenance in a fixture manifest; do not present them as invented sources or global-format proof. Build synthetic empty/malformed/delayed responses separately and label them.

  Restart after one successful and one failed directory: successful original listing SHA and sources persist, failure is retried, new final workset differs and earlier immutable bytes remain. Test a concurrently advancing discovery boundary cannot erase an older required gap. Run discovery/config/URL/workset tests GREEN, commit `feat: discover durable source worksets without hiding gaps`, obtain task Spec/Quality PASS.

**Checkpoint:** Daily outage/handoff/overlap and explicit gaps are represented in acquisition state; no historical recovery horizon or full workflow/coverage claim is made.
