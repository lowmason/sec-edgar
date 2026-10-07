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

### Task 5: Bound HTTP exchanges and validate original-byte acquisition envelopes

**Ownership/files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/download.py`, `validation.py`; `packages/sec-edgar-ingest/tests/test_download.py`, `test_validation.py`, `fixtures/raw/quarterly.idx`, `fixtures/raw/daily.idx`, `fixtures/raw/denial.html`; extend sender/receipt helpers in `tests/support.py`. Synthetic ZIPs are built reproducibly from fixture IDX bytes in tests, not presented as SEC receipts.

**Interfaces:** Produces `Sender.send(url: str, context: RunContext, permit: Permit, *, cancellation: Event) -> BodyReceipt`; production `BoundedSender(settings: Settings, clock: Clock)`; fixture `ScriptedSender(responses: Sequence[ResponseSpec])`, where `ResponseSpec(status: int, body: bytes, headers: dict[str,str], fault: str | None = None)`. `ResponseSpec` is fixture-only. `RequestClient(settings: Settings, coordinator: Coordinator, sender: Sender, state: AcquisitionState, clock: Clock)` produces `fetch(url: str, context: RunContext, source: Source | None = None) -> BodyReceipt` and records every request attempt. `validate_envelope(source: Source, receipt: BodyReceipt, settings: Settings) -> ValidatedBody`; `retry_after(value: str | None, now: datetime) -> float | None`; `retry_delay(ordinal: int, server_delay: float | None, settings: Settings, jitter: float) -> float`.

`ValidationError(code: str, receipt: BodyReceipt)` carries partial evidence. `fetch` never directly constructs a second SEC transport outside `Coordinator.exchange`. A listing request has `source=None` and still consumes the same coordinator, attempt ledger and retry policy. `FetchError(error: Error, receipt: BodyReceipt)` reports terminal/deferred/pending outcomes without pretending a non-200 body is a valid index. Define `AcquisitionState.begin_request(context: RunContext, url: str, source_id: str | None, request_id: str, ordinal: int) -> None` and `request_history(context: RunContext, url: str) -> tuple[Versioned,...]`; atomically persist the ordinal before dispatch, then finish its receipt after dispatch. A crash with no receipt is an accounted uncertain attempt, not an unused retry. Request identity includes the current command's run/attempt and URL. Resuming the same command attempt retains ordinal/exhaustion; a deliberately new command attempt is separately auditable. No automatic new-attempt loop is created here.

- [ ] **Step 1: Write/run RED byte, retry and fail-closed tests.** Use complete original ZIP bytes and a truncation/access-denial matrix:

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

- [ ] **Step 2: Implement the sender as a hard-bounded exchange.** Requests connect/read timeouts are inactivity bounds, not a whole-body lifetime. Run one exchange in a supervised child process, with explicit IPC result/partial spool and absolute monotonic deadline; terminate/join it at the deadline or lease cancellation, close sockets and retain the partial spool. The child checks the permit's start/deadline immediately before network activity and on each streaming iteration; expired permits never open a socket. The supervisor and child both enforce the deadline. The child arms an independent OS-enforced fatal timer before opening a socket; loop checks alone cannot bound a blocking read after its parent dies. Parent crash/takeover fixtures exercise that independent timer and the remaining bounded-child lifetime.

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

- [ ] **Step 3: Implement retry outcomes and envelope validation.** Attempt ordinal is1–5 inclusive, persisted per URL/request identity; an ordinary resumed transport attempt cannot reset exhaustion to five unseen attempts. An explicitly new command attempt remains distinct and records prior exhaustion. 429/retryable5xx/connection failure/timeouts use full-jitter exponential delay capped locally at120, then `max(local_delay, server_delay)`. Parse Retry-After seconds and HTTP-date; invalid header retains diagnostic and uses local bounded policy. If delay exceeds the command deadline, persist `deferred` and do not sleep/retry early. Access denial sets a durable run halt visible to the next source; it is never retried under another identity.

  ```python
  def retry_delay(ordinal, server_delay, settings, jitter):
      local = min(settings.http.retry_cap_seconds,
                  settings.http.retry_base_seconds * (2 ** (ordinal - 1)))
      if not 0 <= jitter <= 1:
          raise ValueError('jitter outside [0,1]')
      return max(local * jitter, server_delay or 0)
  ```

  Validate complete transport, nonempty body, advertised size, selected representation and strict text envelope. Quarterly: ZIP central-directory integrity, exactly one safe `master.idx`, DEFLATE, no encrypted/extra members, full CRC and bounded expanded stream; scan strict ASCII/CRLF for exact selected column header. Daily: retain IDX bytes, scan strict ASCII/LF for the daily header. Reject denial/HTML/error pages, unsupported headers/encoding/archive shapes and truncated bodies. A header without data is not assumed to be a valid empty replacement. Keep syntactic row/date/key normalization out of this stage; a downloaded envelope can still fail the later parser and never gains publication authority. Do not drop raw bytes after a validation failure.

- [ ] **Step 4: Run synthetic and retained-byte tests, commit/review.** Validate all ten original bodies from Stage1 `listings/SEC-0141.body` through `SEC-0150.body`, cross-checking the specimen matrix's original hashes; do not edit/copy over Stage1 artifacts or call it comprehensive golden parser coverage. Retain each synthetic bad-body reason and quarantine bytes. Add a bounded real-process loopback test with a fixture-only0.4-second exchange limit: send occasional bytes faster than the read inactivity bound and verify cancellation by the total deadline, process joined, socket closed and partial retained. This proves local hard lifetime mechanics, not the full90-second worker performance envelope.

  Run download/validation/coordination tests GREEN; commit `feat: collect bounded original bytes with SEC access outcomes`; obtain task Spec/Quality PASS.

**Checkpoint:** Original bytes and bounded retries/denial/quarantine/HTTP lifetime are verified locally. This is acquisition envelope proof, not row parser/global format or effective worker-capacity proof.
