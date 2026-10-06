# SEC investigation access boundary

Recorded at `2026-10-05T23:06:52.076996+00:00`. Status: **AUTHORIZED — NOT ACTIVATED**. Owner-wide allocation/window confirmation is
accepted below. No SEC request occurs before root records actual activation start/end at
the Task 2 checkpoint.

Sole operational issuer: **root chat** for this Stage 1 investigation. Operator/owner:
Lowell Mason. Coordination: root chat owns one sequential request ledger and one shared
attempt/byte/specimen budget; subagents perform independent non-SEC preparation only.
No subagent SEC issuer, second issuer, independent retry budget or identity rotation.
SEC User-Agent: `Lowell Mason sec-edgar-ingest mason.lowell@mac.com`.

## Accepted limits (authorized; not activated)

| Boundary | Accepted limit | Current accounting |
|---|---|---|
| Exclusive sampling window | At most 45 minutes; start/end UTC require root activation | Not started |
| All HTTP attempts | At most 240 total, retries included | 0 |
| Received bytes | At most 512 MiB (536,870,912 bytes) | 0 |
| Initial complete source specimens | At most 12 | 0 |
| Issuing pattern | Sequential, no bursts, starts spaced at least 1/3 second | No requests |
| Owner traffic allocation | All other owner SEC traffic paused; allocation 0 | Accepted; no activation |

The accepted investigation cap does not revise parent production defaults. The application
remains at 3 requests/second and one active collector under parent §§4.3/4.8. The production
Storage lease is future Stage 2 work; its absence does not authorize parallel investigation.

Retries count against this same window/budget and the parent limit of five total attempts per
request. Use the accepted 2-second exponential/jitter base, 120-second local cap, bounded
15-second connection/60-second read timeouts, and honor longer Retry-After. If a required
server delay cannot fit the remaining window, defer; never retry early to fit the window.
Halt immediately on 403 or access-denial content; retain evidence and notify the owner.

Pause at the first exhausted time, attempt, byte or specimen budget, newly discovered format
family, or need for additional sampling. Root records a separately bounded continuation
window and owner traffic allocation before resuming. The first activation must record exact
start/end UTC, confirmed owner allocation, selected rate and limits, and attempt ledger.
No source availability/support/coverage claim follows from zero access.

## Owner confirmation

Lowell Mason replied exactly **“Confirm window; all other SEC traffic paused”** on
2026-10-05 to the proposed sole-root 45-minute, 240-attempt (retries included), 512 MiB,
12-specimen sequential maximum-3-rps window. Other owner SEC traffic allocation is **0;
paused**. Root is the sole issuer, sequential with no bursts and at least 1/3-second start
spacing. Acceptance is retained in `sec-window-owner-acceptance.json`; D-09 is resolved.
Authorization is not activation: start/end UTC remain unset until root's Task 2 checkpoint.
Accounting remains 0 attempts, 0 bytes, 0 specimens. All continuation/halt/retry rules above
remain binding.

## Root activation

Status: **ACTIVE**. Root recorded activation before the first SEC request.

Start UTC: `2026-10-05T23:40:28.753726+00:00`. Deadline UTC: `2026-10-06T00:25:28.753726+00:00`.

Owner allocation: all other SEC traffic paused (0). Sole issuer: root chat. Shared limits: 240 attempts including retries; 536,870,912 received bytes; 12 specimens; sequential starts at least 1/3 second apart. Initial accounting: 0 attempts, 0 bytes, 0 specimens. State: `sec-window-state.json`; ledger: `requests.csv`.


### Task 2 inventory accounting checkpoint

Root inventory command completed 2026-10-05T23:41:43.654694+00:00, exit 0: attempts SEC-0001 through SEC-0139, 1,609,165 original entity bytes, zero specimens. All 139 directory responses succeeded; no retries, redirects, denial or halts. Independent retained-evidence checks passed. Root subsequently fetched official SEC guidance as SEC-0140; shared accounting at verification 2026-10-05T23:43:57.567122+00:00 is 140 attempts, 1,689,512 bytes, zero specimens, no halt. The original activation/deadline remains authoritative; this checkpoint neither resets nor extends the shared window. Task 3 reuses this exact ledger/state/lock. No SEC access by the inventory agent.

## Accepted daily-family continuation

Lowell Mason replied exactly **Accept bounded daily-family continuation** on2026-10-05. Root recorded activation `2026-10-06T00:00:39.782687+00:00` after pausing at SEC-0146 novelty. Deadline is strictly `2026-10-06T00:25:28+00:00`, within originalwindow. Four additional listed daily bodies (20261001,20261002,20251231,20260102), at most20 attempts includingretries (starting146,totalceiling166), shared536870912byte/12specimencaps; rootsoleissuer, otherownertraffic0paused. No new independentbudget. Record: daily-family-continuation-acceptance.json. Existingrawdailybody146 may be fullyinspected; originals/failureevidencepreserved.

## Root sampling closure

Closed at `2026-10-06T00:06:34.400944+00:00` after all10selectedbodyreceipts were inspected. Finalshared accounting:150attempts,15,293,779receivedbytes,10completebodyreceipts. Acceptednoveltycontinuation used4attempts/4additionalbodies, within20attemptbound. No SECdenial; this is voluntarysamplingclosure. Otherownertraffic allocationpause is released atclosure. Any furtherroot SEC access requires newlyrecorded boundedauthorization/activation; no remainingbudget is silentlyreused. Statehalt recordsmanualclosure.
