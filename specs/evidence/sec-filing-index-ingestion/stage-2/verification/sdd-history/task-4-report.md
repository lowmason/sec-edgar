# Task 4 implementation report

Status: DONE_WITH_CONCERNS (fix round 1 verified; fresh Spec/Quality re-review belongs to the controller).
Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`.
BASE: `129ca3a16dafdb82013a8fd28d3d653b58831112`.
Commit: `1d6f61947fac947d872cf0a395e93bbc252adaa2` — `feat: coordinate collector ownership pacing and takeover`.

## Before/after insights

Before: Task 3 supplied durable conditional stores, but its `LeaseHandle.observed_until` was a conservative **lower** valid-until bound. It could not safely serve as a successor's upper expiry/acquisition observation. A queue ticket also supplied no lease-fenced pacing authority.
After: one finite leased sentinel holds the durable epoch, reservation, cooldown and successor guard. Three independent processes use actual Coordinator.exchange and durable clients. A transport reservation charges its latest admissible dispatch time, preserving actual start spacing even when dispatch or Storage is delayed. Current takeover eligibility stays fixed while renewal advances only the future successor's guard.

## Actual interfaces and scope

The brief's `Clock`, `ManualClock`, `Coordinator.turn`, `Turn.reserve/assert_current/complete`, `Turn.cancelled`, `Coordinator.defer_until`, `Coordinator.exchange` and controlled `Sender.send(url, context, permit, *, cancellation)` are implemented. Each turn reserves one finite exchange. QueueTicket rows use SourceState with CAS expiry/status updates; no Table Coordination row controls pacing. Daily receives the next turn ahead of queued backfill/reconciliation, with FIFO within a priority class. Failed attempts, discovery, downloads and retries all pass through exchange; retry sleeps belong outside ownership.

Storage extensions preserve existing Task 3 method signatures:

```python
TimeBounds(lower: datetime, upper: datetime, monotonic_at: float)
TimeBounds.at(mono: float) -> TimeBounds
LeaseHandle(..., acquired_upper: datetime | None = None,
            ownership_until_upper: datetime | None = None,
            observation: TimeBounds | None = None)
LeaseStore.observe_time(handle: LeaseHandle | None = None) -> TimeBounds
LeaseStore.read_journal(handle: LeaseHandle) -> Versioned
LeaseStore.write_journal(handle: LeaseHandle, value: dict[str, object], version: str) -> Versioned
LocalLeaseStore.release_clean(handle: LeaseHandle, value: dict[str, object], version: str) -> Versioned
Permit(..., next_allowed_at: datetime | None = None)
```

`observed_until` retains its lower-bound meaning. Azure upper observations include whole-second server Date precision plus measured operation RTT and reject width exceeding two seconds. Acquisition/renewal use confirmed actual server observations. Journal HEAD/GET/PUT operations carry the actual lease ID and exact ETag; fenced reads rewrite identical bytes and return the actual new PUT ETag. ID/ETag loss and uncertain service outcomes fail closed. No live service was contacted.

The local sentinel is represented by a private SQLite journal table fenced in the same transaction as the existing sentinel lease record. It is one sentinel, not generic StateStore pacing. Exact versions and owner/lease/finite-expiry checks protect every read/write. Local paired UTC/monotonic samples bound measured sampling latency, rounded upward; acquisition upper is sampled after conditional confirmation. Optional atomic release_clean updates that journal and expires its actual lease in one transaction, shortening only after positive drain. Real SQLite constructor contention discovered by the final regression was corrected: read current journal mode, avoid a redundant WAL transition, and retry only SQLITE_BUSY on a fresh closed/reopened connection, at most three attempts using existing finite connection timeouts. Persistent locks still fail closed; no sleep or fixture preinitialization workaround was added.

Renewals retain a conservative prewritten possible-ownership guard before calling Storage, then persist confirmed upper expiry. Unknown renewal/write outcomes stop the turn, set a spawn-compatible Event, and preserve the full unsafe window. Before any release attempt the old turn is irreversibly stopped. `earliest_safe` is captured once; a successor requires both the prior unsafe guard and a full possible exchange after its confirmed acquisition. Returned Sender receipts mean positively drained transport; unknown exceptions never earn clean release. Loss after a returned body, including release or queue-cleanup outage, returns the retained receipt with `complete=False` and structured ownership_lost metadata. Real renewal monitoring wakes/recomputes when a reservation installs the short exchange deadline; deterministic real-clock 0.4-second coverage proves cancellation while the lease otherwise remains valid.

## Explicit deviation and Task 5/8 handoff

**Azure clean-release optimization is unavailable through two independent journal-write/release operations.** A shortened journal written before an unknown release could erase the required unsafe guard. As explicitly authorized by the controller, Azure retains `clean_release=False` and the full guard for both known and unknown separate release outcomes. Successors still make bounded progress after that guard expires. Local atomic release_clean supplies the optimization safely. Actual pinned-SDK scripted known/unknown release tests verify Azure never writes a shortened guard; durable separate-release-shaped tests verify successor progress. Fresh review must assess this deviation against the plan contract. Task 8 README/runbook should explain the resulting Azure throughput wait and absence of operator lease breaking. No README outside this task's ownership was edited.

**Permit timing:** start_before_mono/deadline_mono use the injected Clock domain. Production Clock uses OS `time.monotonic()`, shared across spawned processes on the same host. ManualClock and ProcessClock values are logical fixture times and must never be fed to a real OS-clock BoundedSender. Dispatch allowance is one rate interval (default 1/3 second), clipped by the whole exchange deadline; the durable last_start charges the latest permissible dispatch upper bound and adds an upward-rounded rate interval. This conservatively permits lower throughput than 3/s while preserving the no-burst maximum. Task 5 must check cancellation and OS monotonic deadlines immediately before any socket, refuse stale children, include spawn overhead in the fixture's 0.4-second whole lifetime, and never widen or independently re-pace a permit. Same Sender return contract requires positive child drain/join. Preserve exceptions/unknown outcomes and final server cooldown timing in attempt evidence; reservation's validated detached next_allowed_at supplies Task 3 transport rows.

## TDD and verification evidence

Evidence root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task4-evidence/`.
All logs retain the exact command, actual exit and full output. Commands use offline/frozen pinned dependencies:

```text
FOCUSED: uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_coordination.py -v
FULL: uv run --offline --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_*.py -v
```

Narrow RED commands add unittest `-k` as recorded in their logs.

| Evidence log | Observed result |
| --- | --- |
| red-invariants.txt / red-protocol-matrix.txt | Missing coordinator/journal/Permit behavior before implementation; exit 1, retained bootstrap failures. |
| red-storage-upper-bounds.txt | Includes actual erroneous acceptance of 1.01-second RTT plus Date precision outside the two-second bound; exit 1. |
| green-core-protocol.txt | 19/19, exit 0 after full core invariant matrix. |
| red-clean-release-deadlines.txt / green-release-deadlines.txt | 3 actual release/deadline assertion failures, then 25/25 exit 0. |
| red-three-process-exchange.txt / three-process-first-implementation.txt | Missing real exchange-process helper, then 26/26 exit 0. |
| red-final-timing-and-outage.txt / green-final-timing-and-outage.txt | Actual starts compressed to 0.133344 seconds and queue-cleanup outage masked the body; fixed, 30/30 exit 0. |
| green-refactor.txt / green-full.txt | 32/32 focused and 110/110 full, exit 0 at that earlier state. |
| red-local-confirmed-observation.txt / green-local-confirmed-observation.txt / green-full-final.txt | Actual missing confirmation/sampling upper bounds, then 34/34 and 112/112 exit 0. |
| red-real-monitor-short-deadline.txt / green-real-monitor-short-deadline.txt | Barrier proves missed short-deadline cancellation (1 assertion, exit 1); fixed, 35/35 exit 0. |
| green-full-monitor-final.txt | **Failed** intermediate full run: 112/113, exit 1; actual cold-root WAL constructor contention. Filename is historical, not a success claim. |
| red-sqlite-constructor-contention.txt / green-sqlite-constructor-contention.txt | Real SQLite lock reproduces the constructor failure, exit 1; minimal adapter fix yields 36/36 exit 0. |
| green-constructor-refactor.txt | Intermediate persistent-lock probe failure from its old connection caching DELETE mode; retained honestly. |
| green-constructor-probe-final.txt / green-full-verified.txt | **Initial implementation final** focused 37/37 and full 115/115, exit 0, pristine. Full run includes all original 78 tests. |

Initial `coordination-first-implementation.txt` errors are retained: temporary-directory cleanup ordering and overlarge ManualClock fixture jumps were corrected before the core GREEN. No production result is inferred from that failed harness run. Unit fixtures use finite Events/conditions/barriers and bounded logical stepping; no arbitrary wall-clock sleeps.

## Retained actual traces and boundaries

Final trace directory is `task4-evidence/full-verified-traces/` under the absolute evidence root. `three-process-exchange.json` contains 132 synchronized events and three actual PIDs (31593, 31594, 31595), four actual controlled Sender starts at logical `[0.0, 2.0, 2.666668, 3.333336]`, epochs `[1,2,3,4]`, order backfill/daily/reconciliation/backfill retry. Intervals are `[0,.1]`, `[2,2.1]`, `[2.666668,2.766668]`, `[3.333336,3.433336]`; they do not overlap and starts meet minimum 1/3-second spacing. Each start checks its actual journal owner/epoch/lease and dispatch deadline. First 503 persists global cooldown to logical 2 before positive drain. Logical timestamps prove fixture invariants; separate real_monotonic_ns/PIDs identify OS execution and are not SEC socket timing claims.

Named neighboring trace files retain acquire/renew/loss/request-start/request-end/takeover/queue choice, including `test_full_exchange_after_unknown_renewal_waits_confirmed_successor_guard.json`, `test_takeover_guard_remains_fixed_while_successor_renews-1.json`, `test_renewal_loss_during_body_returns_retained_partial_and_shared_cancellation.json`, `test_storage_latency_cannot_undercount_latest_permitted_dispatch-1.json`, and `test_real_monitor_wakes_when_reservation_installs_short_exchange_deadline.json`. `initialized-root-constructor-probe.json` proves the actual three-process warm startup. The cancellation-child test positively joins an actual spawned process using the same Event. Parent-abandon fixtures keep a controlled request alive only within its finite permit; real hard-cancel socket supervision and kill-parent loopback proofs remain Tasks 5/8. Azure effective timing and owner-wide external allocation remain S7-11/S7-12.

## Self-review and scope preservation

Self-review corrected concrete timing, acknowledgement-loss, receipt-retention, monitor-wake and constructor-boundary issues with retained RED/GREEN evidence. Applied clean-code rules N1/N4 (upper/lower/domain naming), G6/G30 (one journal authority and bounded turn), G25 (named guards/attempt bound), T1/T5/T6 (actual durable transitions, deterministic barriers, deadline assertions); no adjacent refactor or independent scheduler was introduced.

Exactly seven authorized paths were committed: coordination.py; minimal Permit addition in models.py; storage/contracts.py, local.py, azure.py; tests/test_coordination.py and Task 4 additions to tests/support.py. `scope-and-commit.txt` records exact-path staging, git diff checks (exit 0), actual commit and post-commit status; `../task-4-diff.patch` is the committed BASE-to-HEAD diff. Post-commit status contains only the four original unstaged index-ingest deletions. Primary checkout, scaffolds, roadmap, accepted F1/manifest, parent/plan and plan checkboxes were not edited. Reports/logs remain local evidence. No SEC, Azure, auth, compute or registry live network occurred.


## Review fix round 1

Fresh receipt `task-4-review.md` was read completely before edits: Spec FAIL / Quality FAIL, two P1 and one P2 timing findings. All three were reproduced as actual assertion failures against unchanged production commit `1d6f61947fac947d872cf0a395e93bbc252adaa2`. Fix commit: `251de56f44bcc7dda4e56aa034ea78cf7057d9e6` — `fix: keep coordination clock samples paired`. Latest verification supersedes the initial implementation counts above: **41/41 focused and 119/119 full, exit 0, pristine**, after the last production change. Fresh scoped re-review remains pending; this implementer does not claim Spec/Quality PASS.

Before: elapsed time between two otherwise valid samples was discarded or added to a deadline. After: each conversion reuses the anchor actually represented by its interval. Reservation advances returned bounds to the same captured dispatch mono before deriving or persisting UTC last_start/end bounds. Azure measures RTT and returns TimeBounds with one captured receive mono. Conservative lease validity uses the advanced bounds' own monotonic_at instead of a second sample. The analogous old-UTC/later-mono conversion in Coordinator.turn now captures mono before sampling UTC remaining time, preventing an extended absolute turn deadline. Only coordination.py, storage/azure.py and test_coordination.py changed in this repair; all queue, journal, renewal, cancellation, loss and conservative Azure release contracts remain intact.

Scoped inspection covered observation/conversion boundaries in coordination.py, storage/contracts.py, storage/local.py and storage/azure.py. Coordinator._time/_refresh and TimeBounds.at advance to the captured mono they return; local observation includes the entire measured paired-sampling interval and anchors at that same after sample. Azure request-start samples participate in validation and conservative lower validity; the returned server interval is anchored exclusively by the repaired receive sample. Static ownership expiry bounds are not elapsed-time observations and were not advanced. The inspection produced the one analogous turn-deadline RED, not a broader refactor. The documentation handoff typo is corrected to Task 8; only eight tasks are authorized.

Round evidence root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task4-evidence/review-round1/`. Every log retains exact offline/frozen unittest command, actual exit and full output; targeted RED/GREEN commands use `-k` selectors on test_coordination.py, focused/full commands are unchanged from the prior report.

| RED log (each exit 1) | Actual failure before repair | Targeted GREEN (each exit 0) |
| --- | --- | --- |
| red-reservation-refresh-return.txt | Shared durable harness starts compressed to 0.083345 seconds after a 0.25-second pause following refresh return. | green-reservation-refresh-return.txt |
| red-azure-receive-anchor.txt | Accepted upper T+1.05 excludes actual fixture time T+1.2 after the second sample pause. | green-azure-receive-anchor.txt |
| red-validity-conversion.txt | Lease validity extended to 60.25 rather than conservative 60.0. | green-validity-conversion.txt |
| red-turn-deadline-conversion.txt | Absolute turn deadline extended to 1.25 rather than 1.0. | green-turn-deadline-conversion.txt |

`green-focused.txt`: 41/41; `green-full.txt`: 119/119, both actual exit 0 with pristine output. The new tests use real durable stores and injected deterministic clocks, not wall-clock sleeps. `full-traces/test_refresh_return_pause_cannot_compress_actual_transport_starts-1.json` retains corrected actual controlled starts T+0.583323/T+0.916668 (spacing 0.333345 seconds). `full-traces/three-process-exchange.json` retains 132 events, actual PIDs 32585/32586/32587, starts [0.0,2.0,2.666668,3.333336] and epochs [1,2,3,4]; nonoverlap, priority and same-journal checks remain GREEN. UTC/logical timing and OS execution timestamps retain their prior distinct meanings; no live Azure/SEC timing claim is made.

`scope-and-commit.txt` confirms an initially empty index, explicit three-path staging, successful diff checks and the actual repair commit. `../../task-4-fix-round1-diff.patch` is the initial-commit-to-repair diff (located in the SDD task directory); earlier task-4-diff.patch remains the original implementation diff. Post-commit status still contains only the four original unstaged deletions. No primary/protected/unrelated paths, plan checkboxes or live network were touched. Azure release throughput remains the explicit accepted deviation, with no additional blocker assigned by the receipt; S7-11/S7-12 and Task 5/8 concrete hard-socket/parent-death gates remain outstanding.
