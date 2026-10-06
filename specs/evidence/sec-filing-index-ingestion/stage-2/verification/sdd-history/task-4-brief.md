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

### Task 4: Coordinate every request across collectors and safe takeover

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/coordination.py`, `packages/sec-edgar-ingest/tests/test_coordination.py`; extend only Task 4 helpers in `tests/support.py` and lease-journal primitives in `storage/contracts.py`, `storage/local.py`, `storage/azure.py` with Task 3 interfaces preserved.

**Interfaces:** Consumes Task 3 state/lease stores and Task 2 settings/Permit. Extend `LeaseStore` with `read_journal(handle: LeaseHandle) -> Versioned` and `write_journal(handle: LeaseHandle, value: dict[str,object], version: str) -> Versioned`; both operate on the leased sentinel, enforce the actual lease ID plus version, and fail on loss. Queue tickets live in SourceState; SEC pacing/takeover authority lives in the leased Blob journal, avoiding a claim that its lease fences Table entities.

Produces `Clock.now() -> datetime`, `monotonic() -> float`, `sleep(seconds: float) -> None`; `ManualClock.advance(seconds: float) -> None`; `Coordinator(settings: Settings, store: StateStore, leases: LeaseStore, clock: Clock)` with `turn(owner_id: str, priority: str, deadline: datetime) -> ContextManager[Turn]`, `Turn.reserve(request_id: str) -> Permit`, `Turn.assert_current(permit: Permit) -> None`, `Turn.complete(permit: Permit, drained: bool) -> None`, and per-turn `cancelled: Event`, `Coordinator.defer_until(instant: datetime) -> None`. `Coordinator.exchange(context: RunContext, url: str, sender: Sender) -> BodyReceipt` is the only HTTP entry point; it acquires a turn, reserves pacing, passes that turn's cancellation event, calls `Sender.send(url: str, context: RunContext, permit: Permit, *, cancellation: Event) -> BodyReceipt`, and reports ownership loss with a retained partial receipt. Sender is implemented in Task 5; tests use a controlled sender with the same interface.

Test helper `coordination_harness(root: Path, *, clock: Clock) -> CoordinationHarness` provides `start(owner: str, priority: str)`, `reserve(owner: str) -> Permit`, `hold_request(owner: str)`, `expire_owner(owner: str)`, `finish_request(owner: str)`, `acquire_successor(owner: str)`, `starts: list[tuple[str,datetime]]`, `maximum_active: int`. It drives real coordinator/store instances and barriers, not a second simplified scheduler.

- [ ] **Step 1: Write/run overlap, loss and takeover RED tests.** Include a deliberately live prior request; counting only lease holders is insufficient:

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

- [ ] **Step 2: Implement a finite ownership and durable pacing journal.** Journal v1 fields are `owner_id, epoch, ownership_until, unsafe_until, last_start, not_before, request_id, clean_release`; all timing is conservative server-derived UTC bounds. A Table queue ticket cannot issue a request. Only the owner of the one leased sentinel can reserve a permit and change the journal.

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

- [ ] **Step 3: Implement bounded turns and priority with real coordinator entry points.** Enqueue a ticket with finite expiry; select oldest valid daily ticket before non-daily work. Each bounded exchange releases its turn, including failed/retry attempts. Retry sleeps occur outside ownership while cooldown remains shared. Stale ticket removal uses CAS and cannot clear another ticket. Renewals use the same sentinel; they do not create new owners or traffic budgets. Expiry/loss sets `Turn.cancelled`, the same spawn-compatible event passed into `Sender.send`; `assert_current` refuses a stale epoch/permit before any new request.

  Add a test that calls `Coordinator.exchange` from three independent processes sharing local lease/journal state; all scripted transport starts append through one synchronized recorder. Assert no interval overlap, minimum1/3-second logical spacing, retries included, daily chosen before remaining lower-priority work, and no starts under an old epoch. Faults after journal reservation consume conservative pacing/guard even if no socket was opened. This is deliberate fail-closed recovery, not a requirement to reclaim an uncertain unused slot.

- [ ] **Step 4: Verify, commit/review.** Run all coordination and Storage contract tests GREEN. Save event traces including acquire/renew/loss/request-start/request-end/takeover/queue choice, not just a successful final count. Commit `feat: coordinate collector ownership pacing and takeover`; obtain task Spec/Quality PASS.

**Checkpoint:** Fixtures demonstrate one coordinated issuer, stopped stale ownership and bounded in-flight takeover. Actual Azure timing/effective lease behavior and other owner-wide traffic allocation remain S7-11/S7-12 obligations.
