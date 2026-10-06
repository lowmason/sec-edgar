# Task 5 implementation report

Status: implementation and self-review complete; fresh controller Spec/Quality review pending. BASE: `251de56f44bcc7dda4e56aa034ea78cf7057d9e6`. Branch: `codex/sec-edgar-stage-2`. Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`. Final implementation commit: `77a07ee0e249f64de085347598b81e255a03a7ef` — `feat: collect bounded original bytes with SEC access outcomes`. No task/plan checkbox was ticked.

## Result and scope

Implemented one durable RequestClient around the existing Coordinator, an OS-bounded spawned HTTP child, original-entity receipts, explicit retry/denial/pending/deferred/quarantine outcomes, and selected quarterly/daily acquisition-envelope validation. Every listing, download and retry uses Coordinator.exchange and the same existing owner budget. Defaults remain 3 RPS, one issuer, five total attempts, 90 seconds including spawn startup, 67,108,864 received bytes and 536,870,912 expanded bytes.

The controller explicitly authorized minimal AcquisitionState request/run-halt additions and, after an actual delayed-adapter wire-spacing RED, the narrow Turn.complete drain-spacing update. No resources/tables, independent rate limiter, alternate production origin, infrastructure, later-stage collector/discovery command, row parser, normalization or publication work was added. SEC/Azure/compute/auth windows stayed closed. Only frozen offline dependencies, the selected scripted Azure adapter and explicitly bounded loopback fixtures were used.

## Actual interfaces for later tasks

The public interfaces in download.py are:

```python
BoundedSender(settings: Settings, clock: Clock)
BoundedSender.send(url: str, context: RunContext, permit: Permit, *, cancellation) -> BodyReceipt
ScriptedSender(responses: Sequence[ResponseSpec])
ResponseSpec(status: int, body: bytes, headers: dict[str, str], fault: str | None = None)
RequestClient(settings: Settings, coordinator: Coordinator, sender: Sender,
              state: AcquisitionState, clock: Clock)
RequestClient.fetch(url: str, context: RunContext, source: Source | None = None) -> BodyReceipt
FetchError(error: Error, receipt: BodyReceipt)
retry_after(value: str | None, now: datetime) -> float | None
retry_delay(ordinal: int, server_delay: float | None, settings: Settings, jitter: float) -> float
wait_for_sender(process, cancellation, deadline_mono: float, clock: Clock) -> bool
```

ResponseSpec and ScriptedSender are explicitly fixture-only. RequestClient rejects ScriptedSender for an Azure backend and verifies the same effective settings as its coordinator. A listing uses source=None: a successful listing returns its original transport receipt for the later directory decoder. For a Source, fetch validates the envelope before returning a successful receipt. A later stage can separately call `validate_envelope(source: Source, receipt: BodyReceipt, settings: Settings) -> ValidatedBody`; it raises `ValidationError(code: str, receipt: BodyReceipt)` with retained original bytes. A successful envelope grants no row-parser/publication authority.

FetchError always carries structured Error and the original/partial receipt. Its Error.details includes actual outcome, ordinal and request_id for completed audited requests. Access denial uses access_denied/halted, subsequent same-run calls run_halted/halted; listed 404 uses listed_missing/pending; redirects redirect_refused/failed; invalid 200 source envelopes use their validation code/quarantined; deadline deferral uses deferred/deferred; final failure uses attempts_exhausted/exhausted. Connection/timeouts and 429/5xx retry only within the accounted budget. `SenderFailure(message: str, receipt: BodyReceipt)` subclasses OwnershipLost and exposes a receipt when child protocol, IPC or shutdown cannot be confirmed. RequestClient stops immediately on that uncertainty and records an unresolved failure rather than retrying under a new identity.

AcquisitionState adds these typed methods and a compatible keyword-only extension:

```python
begin_request(context: RunContext, url: str, source_id: str | None,
              request_id: str, ordinal: int) -> None
request_history(context: RunContext, url: str) -> tuple[Versioned, ...]
request_attempt(context: RunContext, receipt: BodyReceipt, permit: Permit, ordinal: int, *,
                outcome: str = "received", error: Error | None = None,
                retry: dict[str, object] | None = None,
                next_allowed_at: datetime | None = None) -> None
halt_run(context: RunContext, error: Error) -> None
run_halt(context: RunContext) -> Error | None
```

TransportAttempt identity hashes the complete current run/execution/command/attempt identity plus URL and ordinal. begin_request atomically inserts an uncertain row before the actual Sender.send; independent clients racing the same ordinal produce one insert and one Conflict. History is sorted and validates command provenance. A crash with no receipt consumes the ordinal, including all five uncertain crashes. Reopening the store/client resumes at the next ordinal; the same attempt never sends a sixth. A deliberately new attempt starts its separate budget and stores prior_exhaustion identities, including prior five-row uncertain budgets. No automatic new-attempt loop exists.

Finalization CAS preserves the original context, request ID, ordinal, begun_at, prior audit and receipt identity; finished receipt/outcome is immutable and idempotent. The old direct request_attempt call remains supported. Rows contain outcome, structured error, complete original receipt/Permit, status, byte_count, ownership_epoch, ended_at, original permit_next_allowed_at and final next_allowed_at/retry metadata. TransportAttempt already routes to Attempts; RunHalt routes to SourceState through the existing generic kind mapping. A narrow scripted adapter test records actual POST URLs for both tables. No storage routing or resource change was needed.

RunHalt is keyed by run_id and validates immutable image/parser/schema/config provenance. First denial persists across next source, execution/command/attempt identity; conflicting provenance fails closed. New command attempts cannot bypass a halt in the same run.

## Retry authority and time-domain distinction

Retry uses full-jitter exponential local delay, capped locally at 120 seconds, then max(local, actual server delay). Numeric and HTTP-date Retry-After are parsed; invalid values retain their original value/diagnostic. A longer 180-second server delay is shared durably via the existing coordinator sentinel not_before before another request can run. Sleeps happen only after the exchange turn and cooldown-control turn end. The fifth/final failure retains its actual server cooldown even though the command exhausts.

Server UTC comes only from actual LeaseStore.observe_time TimeBounds; a missing/over-wide observation fails closed, including production Azure. A host UTC fallback was not added. Retry metadata records retry_after_value, retry_after_valid, server_delay_seconds, delay_seconds, not_before, server_lower, server_upper, observed_mono and ready_mono. The UTC not_before is server-authoritative. ready_mono is constructed from the actual bounds anchor and conservative lower bound, then compared with a command deadline captured in the same process monotonic domain. A server clock 120 seconds behind the host cannot turn a 180-second cooldown into an allowed retry within a 100-second command; this regression is deferred immediately without sleeping past the command.

**observed_mono/ready_mono and Permit monotonic fields are historical evidence in their originating process/host domain (OS monotonic in production, logical fixture time in ManualClock tests). They must never be imported as a schedule after restart, reboot or on another worker.** RequestClient does not reuse saved retry monotonic values: a resumed request reads budget history and obtains new Coordinator/Storage observations, with durable server UTC not_before in the sentinel remaining the scheduling authority. Store reopen/budget continuation and existing durable cooldown restart tests pass. UTC context deadlines are host command clocks; their comparison with server cooldowns is made only through the paired monotonic conversion.

Permit.next_allowed_at is the actual immutable original reservation value, retained as permit_next_allowed_at; it is not a fabricated completion timestamp. Later drain-floor and retry/server-floor updates belong to the sentinel and separately retained final next_allowed_at/retry data. On a successful nonretry request, attempt metadata retains the original Permit reservation floor; the later drain floor is journaled by Turn.complete and recorded by drain-pacing traces.

## Production transport and explicit loopback selection

Production BoundedSender has no loopback URL argument. It accepts only exact canonical strict SEC listing/source URLs and the exact real `Clock` type using the same-host OS time.monotonic domain. ManualClock and logical ProcessClock permits cannot feed its OS timer. Platforms outside Linux/macOS fail closed; child timer installation/disposition/mask verification failures open no socket.

The fixture selection API is `support.loopback_sender(settings, clock, origin, *, target=None, spool=None)`, returning the deliberately named nested `FixtureLoopbackSender(BoundedSender)`. Its override requires local-fixture backend, explicitly fixture-marked worker provenance and the selected exact http://127.0.0.1 origin/netloc; credentials, fragments and any different host/port are refused. The minimal spawned transport record carries this selection and repeats origin/fixture checks in the child. The strict base production validator is unchanged. Only tests use this subclass; real Clock, the same-host OS monotonic timer and the spawn-compatible cancellation Event are used in these fixtures.

A spawned child receives only a plain immutable transport specification (strings/numbers/bool), the spawn-compatible Event and completion channel. Actual frozen model Error mappingproxy pickling failed in a local check; no RunContext/Permit/frozen mappings/SDK clients are sent to the child. The child clears ambient environment before importing Requests. One fresh Session uses trust_env=False, zero HTTP/connect/read/status/redirect retries, exact identifying User-Agent, Accept-Encoding: identity, explicit proxies={}, TLS verification and direct adapter.send. Pinned Requests Session.send was observed to consume redirect bodies while preparing a potential redirect even with allow_redirects=False; direct adapter.send preserves original 302 bytes and never follows Location or invokes automatic decoding.

The child checks cancellation and permit immediately before adapter/DNS/socket activity and every raw streaming iteration. A preparation delay past the original 1/rate dispatch window is refused with zero requests; the window is never widened or repaced. Default-fatal SIGALRM is unblocked and ITIMER_REAL armed against the existing absolute deadline before DNS/socket. The timer remains armed through process exit/finalizers and independently kills a blocked child after supervisor death. Startup consumes the original deadline.

Pinned raw.read1(size, decode_content=False) yields available bytes rather than waiting for a large buffer, removes transfer framing only and retains nonempty trickle prefixes. Unexpected Content-Encoding retains original encoded bytes and reports unsupported transport. Nested IncompleteRead.partial is traversed through cause/context/args and retained once. The received guard is checked before writing: overflow retains at most the configured cap; the extra probe byte is never retained as accepted prefix. Supervisor hashes/counts the exact retained spool after positive join. The metadata/partial spool survives process death; the IPC payload is only a small completion marker.

Supervisor polls at <=0.05s and drains with terminate/join, then kill/join if necessary; a returned receipt always means the child was positively joined with confirmed exit. Unknown child exception, malformed metadata, missing/invalid IPC or unverified drain raises SenderFailure and leaves the coordinator unsafe guard intact. Cancellation and deadline retain incomplete receipt evidence and stop the old owner.

## Named cross-task pacing change

A controlled adapter delay of 0.55s after the final pre-adapter check caused a real first GET to arrive late and a queued second GET only **0.11944212485104799s** later, below the required 1/3s. Both children had drained and adapter invocations were separated; invocation pacing was insufficient. This actual RED, two server timestamps and exact child traces were retained before the controller authorized the minimum coordination.py change.

Turn.complete now uses an actual verified drain-time server upper bound and writes durable not_before >= upper + ceil(1/rate) before release. It preserves the old reservation last_start charge, immutable Permit and all cancellation/ownership/unsafe guard rules. Actual later wire activity is bounded above by the confirmed drain; successors therefore start after completion plus spacing without requiring an unobservable socket timestamp. Final full trace GETs are 2743797.572881291 and 2743798.033658, spacing **0.460776709s**. This named fixture uses an explicit 1.0s lifetime; default 90s remains unchanged.

This is conservatively paced after completion. Task4's accepted Azure full-unsafe-guard release deviation remains intact and must be stated in Task8's runbook. No throughput/capacity claim follows from these local timing fixtures.

## Selected acquisition envelopes

Daily validation checks complete HTTP 200, nonempty identity entity, original hash/count, advertised length/framing/type, ASCII/control-byte rules, exact LF and exact `CIK|Company Name|Form Type|Date Filed|File Name` header. Quarterly validation checks central/local ZIP shape, exactly one safe nonencrypted regular master.idx using DEFLATE, original bytes, and exact ASCII/CRLF `...|Filename` envelope. Final newline is optional in the accepted selected formats. Header-only or separator-only bodies do not become valid empty indexes.

Full quarterly validation streams exactly the compressed member range through public bounded zlib decoding, requires genuine DEFLATE EOF with no unused compressed tail, then checks complete expanded count and full CRC. It never extracts paths or accumulates expanded rows. This repairs two actually reproduced stdlib ZipExtFile acceptance gaps: forged expanded size + matching prefix CRC hid a suffix; a correctly re-offset compressed member missing the final DEFLATE marker also passed. Both now fail and retain their original ZIP bytes. Received/expanded limit+1 cases include scaled actual streaming guards and exact accepted-default advertised sizes 67,108,865/536,870,913; no giant memory/stress fixture was invented.

All 83 audited selected bodies/sidecars/matrix were hash+length checked before reading original evidence and rechecked after verification. The retained specimen matrix and each SEC-0141–0150 original body/headers are cross-checked before validation. All ten pass, including their missing final newline formats. They are bounded selected acquisition specimens, not global format or parser golden coverage. Accepted F1/manifest originals were not edited.

## TDD and verification evidence

Logs and evidence are local under `.sdd/2-sec-filing-index-ingestion-stage-2-spec/`; they are not included in the implementation commit. Every following unittest command uses `uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests`, with the shown pattern and optional selector. Initial tests failed before implementation; targeted regressions were reproduced against the still-unfixed code before each fix.

| Retained RED log | Command suffix / actual RED |
|---|---|
| task-5-red-download.txt | `-p test_download.py -v`: 16 expected missing-module behavioral failures before implementation |
| task-5-red-validation.txt | `-p test_validation.py -v`: 9 expected missing-module failures before implementation |
| task-5-red-process.txt | `-p test_download.py -v`: initial process/partial extraction contracts failed before BoundedSender existed |
| task-5-red-malformed-result.txt | `-p test_download.py -k malformed_result -v`: malformed/unknown results lacked the required retained structured receipt |
| task-5-red-stale-preparation.txt | `-p test_download.py -k timer_installation -v`: preparation delayed past dispatch window but transport completed |
| task-5-red-crash-exhaustion.txt | `-p test_download.py -k five_uncertain -v`: prior five uncertain crashes missing from new-attempt audit |
| task-5-red-quarantine-outcome.txt | `-p test_download.py -k html_200 -v`: Error.details missing quarantined outcome |
| task-5-red-corrupt-deflate.txt | `-p test_validation.py -k archive_shapes -v`: raw zlib error lacked ValidationError/original receipt |
| task-5-red-adapter-wire-spacing.txt | `-p test_download.py -k next_actual_get -v`: actual GET gap 0.11944212485104799s |
| task-5-red-server-offset-deadline.txt | `-p test_download.py -k server_clock_offset -v`: sender_unverified after sleeping past command instead of immediate deferred |
| task-5-red-zip-prefix-crc.txt | `-p test_validation.py -k forged_expanded -v`: hidden full DEFLATE suffix was accepted |
| task-5-red-deflate-eof.txt | `-p test_validation.py -k full_deflate_end_marker -v`: missing real DEFLATE EOF accepted after maintaining correct central-directory offset |

Additional fixture diagnosis retained task-5-red-supervisor-cleanup.txt (killed supervisor initially owned semaphores; five cleanup warnings) and task-5-red-takeover.txt plus exact queue trace. The surviving test parent now owns the Event, and explicitly daily successor selection exercises the required queue priority after actual supervisor death. The stale crashed backfill ticket otherwise consumes a backfill successor's own short command lifetime; no production queue behavior was altered.

Latest focused output: task-5-green-download.txt **35/35**, task-5-green-validation.txt **12/12**, task-5-green-state.txt **11/11**, task-5-green-coordination.txt **41/41**, all actual exit 0 and pristine. The full command below passed **166/166 in 12.767s**, actual exit 0 and pristine, in task-5-full-tests.txt after the last production/name change. A final exact-path staging check then removed one test trailing space; the justified final rerun (same command without the evidence environment override) also passed **166/166 in 12.490s**, actual exit 0 and pristine, in task-5-final-full-tests.txt. The first full evidence remains retained separately:

```bash
SEC_EDGAR_TASK5_TRACE_DIR=.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-5-full-evidence uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
```

The full-evidence directory retains 62 original invalid/terminal synthetic body files with structured reasons/receipts, plus exact child/server JSON/JSONL traces, bytes and metadata for bounded process cases. The initial RED wire-spacing traces remain separately in task-5-red-adapter-evidence, rather than being overwritten by later GREEN output.

## Exact final process evidence

Full-evidence process/trickle-total-lifetime: 315 bytes sent and all **315 original bytes retained**, SHA-256 `b34180630a9feae29904a0122fc777239cae4e29f68c0abfbb88ad67fcdf4cad`; child PID36258 joined with exit -15 at monotonic2743798.473377666 against original deadline2743798.4679191657. Server socket closed2743798.485381375. Whole coordinator fixture elapsed0.420005958s; child startup was included in the unchanged0.4s deadline. Receipt remains incomplete with actual ownership/deadline loss evidence; it is not an accepted index.

Full-evidence process/supervisor-crash-independent-timer: supervisor PID36248 terminated exit-15 at2743792.102759458; orphan PID36249 recorded unblocked/default-fatal alarm armed before socket against deadline2743792.441521166; blocked-header socket closed2743792.450293833, with no Python completion marker/session close and ps reporting no remaining process. The independent child timer, rather than a surviving Python supervisor loop, bounded this socket. Its body is empty because only incomplete headers were sent. The separate trickle proof supplies nonempty partial bytes.

Full-evidence process/supervisor-crash-successor: actual GET2743796.793714166 after orphan close and deadline; actual coordinator epoch2, renewals while waiting the fixed takeover floor, complete26-byte original response, positive child join and clean local release. The fixture changes lease to2s/renew1s and exchange0.4s, explicitly local only. Timer installation failure, stale spawn start and stale preparation traces each show **zero requests**. Malformed child metadata, unexpected child exception and IPC-loss traces retain partial bodies and stop unsafe ownership. All child return/join checks use actual processes and actual sockets.

## Self-review, files and limitations

Self-review read all owned production/test changes, task requirements and full output; corrected concrete observed pacing, clock-domain, archive termination, receipt/metadata, redirect-body and fixture-resource issues using RED/GREEN evidence. Applied clean-code G25 named bounds/constants; N1/N7 meaningful timing/domain names; G30 transport/model separation through minimal spawn data; C3 load-bearing comments explaining pinned redirect/ZIP behavior; T5/T6 exact boundary/real durable race/process tests. Existing tests/support.py is larger after the mandated Task5 helpers; no unrequested file split or adjacent refactor was performed.

The ten explicitly owned/authorized paths are download.py, validation.py, state.py, coordination.py (named authorized minimum), tests/test_download.py, tests/test_validation.py, tests/support.py and tests/fixtures/raw/{quarterly.idx,daily.idx,denial.html}, all under packages/sec-edgar-ingest. No additional storage/resource path changed. The four original unstaged index-ingest deletions, primary checkout, local roadmap, scaffolds, accepted F1 and parent documents remain preserved. The staging check exposed one trailing space in a new test, which was removed; quarterly fixture CRLF is intentional original format data. `git -c core.whitespace=cr-at-eol diff --cached --check` is the applicable check, without changing repository settings or fixture bytes.

No known failing test or unresolved correctness issue remains at this handoff. Fresh Spec/Quality review is still the controller's gate, not claimed by this report. The Linux timer branch is fail-closed code; actual process evidence is local macOS. There is no live Azure/SEC timing, full90-second worker/performance, recovery-horizon, global format, row-parser or publishing proof. RequestClient returns retained receipt/quarantined outcome for later collection decisions; content-addressed promotion/quarantine persistence belongs to later tasks and was not implemented here.

## Final commit receipt

`task-5-scope-and-commit.txt` records actual full SHA, exact ten committed paths, post-commit status containing only the four original unstaged deletions, and explicit `git -c core.whitespace=cr-at-eol diff --check BASE HEAD` exit 0. The same explicit cached check passed before commit. No repository setting changed; committed quarterly CRLF bytes match the original synthetic file. `task-5-diff.patch` is the actual BASE-to-HEAD committed diff for fresh review. Final source revision is `77a07ee0e249f64de085347598b81e255a03a7ef`; both final166-test outputs were read and verified, and no production/test code changed after that verification. Fresh Spec/Quality gate remains pending.

## Review fix round 1

The complete fresh receipt task-5-review.md was read before editing: Spec FAIL / Quality Needs fixes, three Important findings and a fresh-checkout fixture dependency. This appendix supersedes the initial handoff's policy correctness claim. Repair BASE is `77a07ee0e249f64de085347598b81e255a03a7ef`; fresh scoped re-review remains the controller's gate.

Three distinct behaviors were reproduced against the unchanged implementation in task-5-fix1-red-policy.txt (actual exit1, two assertion failures and one OverflowError): a caller that had already passed its first halt check still sent at logical0.666668 after another client durably denied the run; a next daily owner entered at0.666668 after429 before its180s cooldown was published; valid numeric Retry-After1000000000000 overflowed UTC addition and escaped without structured receipt handling. Independent actual SQLite/lease clients shared the same issuer namespace and one ManualClock. No network was used for these policy tests.

The compatible coordination interface is now:

```python
Coordinator.exchange(context: RunContext, url: str, sender: Sender, *,
                     on_response: Callable[[BodyReceipt, Permit], None] | None = None) -> BodyReceipt
Coordinator.block_requests(reason: Error) -> None
PolicyBlocked(reason: Error)  # RuntimeError with .reason carrying the stored structured Error
```

Existing exchange callers omit the optional hook and retain their behavior. The hook runs synchronously after a positively drained receipt, under the original live issuer turn, before Turn.complete and release. The turn verifies ownership/permit around policy processing. RequestClient publishes denial and cooldown in that hook. Only the small transport/access policy and a bounded denial-prefix peek are inside ownership; source envelope/expanded ZIP validation remains afterward. Retry sleeps remain outside ownership. The original90s lifetime, original immutable Permit reservation fields, completion drain-spacing floor and all Task4 unsafe/cancellation rules are unchanged.

Run halt is additionally rechecked inside the audited sender immediately before durable ordinal insertion and transport. This closes queued-caller admission and applies to each retry, including a denial written by another client during retry sleep. The queued caller consumes neither a transport ordinal nor a request after halt. A dedicated assertion observes the halt already durable at the original response turn's release.

Normal retry metadata now includes cooldown_confirmed=True only after the owner-sentinel write acknowledges. Callback/policy write failure cancels ownership, preserves the full prior unsafe guard, skips clean release and returns the original receipt as incomplete. An unconfirmed proposed not_before remains diagnostic in retry metadata with cooldown_confirmed=False; final next_allowed_at retains the actual original Permit reservation floor rather than falsely claiming the candidate was durably acknowledged. Additional actual REDs in task-5-fix1-red-unconfirmed-denial.txt and task-5-fix1-red-unconfirmed-cooldown.txt drove these classifications/metadata fixes. A failed halt write now reports ownership_lost/failed rather than pretending access_denied established a durable halt. Original403/429 bytes remain retained; no automatic retry/new attempt follows uncertainty.

For a valid server delay outside the supported UTC calendar or numeric representation, RequestClient retains the raw header/body in retry_delay_unrepresentable/deferred and publishes a structured policy_block latch in the same owner sentinel before release. It does not clamp the delay or replace it with local backoff. The original response remains in the attempt ledger; retry metadata contains policy_blocked=True, raw retry_after_value, actual server bounds, and null not_before/ready_mono. The request row's final next_allowed_at is null because no finite schedule exists; permit_next_allowed_at still retains its actual original reservation. A500-digit valid integer also blocks rather than becoming an invalid-header/local-delay fallback.

The sentinel schema gains optional policy_block: structured Error mapping | None. Legacy journals without it decode as None; present data passes the existing strict Error decoder. The first latch/reason is preserved by every later journal/turn/clean-release update. Turn.reserve checks it under acquired serialized ownership before permit/ordinal/send, so all clients and independent runs in the same fixed namespace are refused with policy_blocked/deferred. Malformed latch data fails before ordinal/transport. The latch has no timer expiry, reset API or automatic new-run escape. No resource/table or second budget was introduced. Task8 must document this exact blocked condition and raw reason, along with the already accepted Azure full-unsafe-guard clean-release deviation; no new operator reset procedure is implemented here. Historical monotonic retry metadata remains host/process-domain evidence only, never restored as a schedule.

The fresh-checkout warning was also reproduced: temporarily renaming only ignored retained-fixture-audit.json caused FileNotFoundError (task-5-fix1-red-missing-sdd.txt). The new committed tests/fixtures/retained-manifest.json contains exactly the existing83 path/hash/length records plus immutable finding and accepted-manifest paths/hashes. Creation verified all83 against accepted manifest records and physical byte hashes before copying metadata. The test independently rechecks both immutable provenance hashes and every record, then all ten selected originals. With the ignored audit unavailable it passes1/1 (task-5-fix1-green-missing-sdd.txt); only that renamed ignored copy was restored byte-exact. No Stage1 original, F1, manifest or unrelated Git file was restored or changed.

Focused policy tests progressed to9 covering queued admission, initial handoff, every retry, halt-before-release, calendar/numeric overflow, malformed durable latch and both uncertainty cases. Required focused output is retained in task-5-fix1-green-download.txt44/44, task-5-fix1-green-validation.txt12/12, task-5-fix1-green-state.txt11/11 and task-5-fix1-green-coordination.txt41/41, all actual exit0/pristine. The same offline frozen unittest commands described above were used with the corresponding pattern. A fixture-only evidence cleanup failure (shared clients each copied all sibling rows) was retained in task-5-fix1-red-shared-evidence-cleanup.txt; the helper now retains only the current sender's spools, preserving independent cleanup ownership. No production correction was needed for that fixture failure.

Self-review checked all seven repair paths and held-policy/receipt/guard transitions. No later-task work, policy reset, additional resources, primary checkout changes or broad refactor was added. Original four deletions remain unstaged. Explicit cr-at-eol whitespace checks preserve raw fixtures. Final full result and repair commit receipt follow after verification.

Final fix-round full command: `SEC_EDGAR_TASK5_TRACE_DIR=.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-5-fix1-full-evidence uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v`. Actual **175/175 in13.095s, exit0/pristine** in task-5-fix1-full-tests.txt, run once after the last repair/helper change. Fresh child/socket and retained original-byte traces remain in task-5-fix1-full-evidence. All required covering outputs and each listed RED were retained; no known failing test remains. Fresh scoped Spec/Quality review remains pending.

Fix-round final source revision is `50b2756330cbef91b5c664a5f4cc72c2f5c35626` (`fix: publish SEC response policy before owner release`). task-5-fix1-scope-and-commit.txt records the exact seven committed paths and post-commit status containing only the four original unstaged deletions. `git -c core.whitespace=cr-at-eol diff --check 77a07ee0e249f64de085347598b81e255a03a7ef 50b2756330cbef91b5c664a5f4cc72c2f5c35626` exited0; the same explicit cached check passed before commit. task-5-fix1-diff.patch is the actual repair-BASE-to-HEAD diff for fresh scoped review. No production/test source changed after final175-test verification. Accepted immutable provenance and original fixture bytes remain unchanged. Fresh Spec/Quality gate remains pending.
