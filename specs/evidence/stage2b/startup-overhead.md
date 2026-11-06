# Invocation 1: where the first 1,800 s went

Observation, not a finding. Source: modification times of the files that invocation 1 wrote (`run 0746b217-d4ca-4f1d-9b05-d0c447b734ce`), read as metadata only, and the invocation record. Times are UTC.

Invocation 1 started at 17:52:57Z with a 3,600 s timeout. The dispatch cutoff was 18:22:57Z (deadline − 1,800 s). The run dispatched no member. All 155 members ended `pending` with `workflow_deferred`, and the run wrote its durable result.

| Phase | From | To | Length | What the files show |
| --- | --- | --- | --- | --- |
| Before the first child call | 17:52:57Z (`intent.json`) | 18:08:01Z (first `children/…/call.json`) | 904 s | No file written |
| Discovery | 18:08:01Z | 18:13:50Z | 349 s | 28 source worksets written, about 13 s apart. 37 request attempts (36 received, 1 failed) |
| After discovery | 18:13:50Z | 18:23:06Z (`selection.json`) | 556 s | No file written. The cutoff (18:22:57Z) fell in this phase |
| Finish | 18:23:06Z | 18:23:20Z (`result.json`) | 14 s | |

About 1,460 s of the 1,810 s elapsed outside the network. The run had no time left to dispatch a member.

Hypothesis (not measured): the two quiet phases are passes of `evaluate_member` over the registered members. Under v2, none of the 127 registered members is complete (F1). The convergence step of Task 2 evaluated 12 members in at most 64 s, about 5.4 s each. The same cost over 127 and 155 members gives about 690 s and 840 s, the same order as the 904 s and 556 s above.

If this cost recurs in every invocation, the pre-dispatch time is about 1,800 s, and the dispatch cutoff (1,800 s at a 3,600 s timeout) leaves no time to start a member. Invocation 2 shows whether it recurs. Stop rule 10 halts when a rerun does not reduce the eligible list.

## Correction to the premise of D6

D6 assumed the daily 2026-07-01 member could start within about 360 s of the invocation start and so finish before the 3,600 s deadline. Invocation 1 shows that no member starts that early.

- Every invocation first runs discovery. It then runs a selection pass. Selection is tied to the run, so a new run repeats it. In invocation 1 these two phases took 349 s and 556 s.
- A member can start only after both. A 904 s phase before discovery may also recur.
- If these phases stay near 900 s, the 2026-07-01 member (3,239.6 s in the offline timing) starts at about 900 s or later and ends after 4,100 s. The 3,600 s deadline then kills it, and stop rule 2 halts the campaign.
- Under this reading the D6 exception does not let that member finish in any invocation. The reserve does not change this, and the run length is fixed at 3,600 s in code. A fix has to cut the pre-dispatch work or the member's cost, which is a code change. Plan 8 forbids code changes.
- The campaign reaches this member only after the 25 closed quarterly members. Invocation 2 and the next ones are not affected. The owner can decide before the campaign gets there.

## What invocation 1 showed that F1 did not predict

- **Members.** 155 members, not 127. They cover 113 sources: 74 sources have one member, 37 have two, one has three and one has four. The members differ in their parent source workset (6 distinct parents). Invocation 1 added 28 members under one new source workset (`06db4861…`).
- **Gap `baseline_publication_missing` (2).** The quarters 2022Q4 and 2023Q1 have no readable generation. Both are quarters that daily rows never reached. Their quarterly members should publish them.
- **Gap `legacy_member_unresolved` (1).** "source member is after the pinned endpoint", not retryable, with no named source (record kind `DiscoverySession`). No stop rule covers it. The next invocations show whether it blocks dispatch.
- **Gaps `permit_expired` (1) and `ancestor_failed` (2).** The failed attempt is the listing `https://www.sec.gov/Archives/edgar/daily-index/index.json`. The two parents are `daily-index/index.json` and `daily-index/2026/index.json`. Both are under `daily-index/`, so stop rule 11 option (a) applies, as in Stage 2.

## Invocation 2 and the cost per member

Run `bdefaa5d-856d-4bc4-a621-018e66b6ef1e`, 18:31:08Z to 19:16:24Z (2,717 s), same method. Discovery completed this time (53 sources, 39 requests, all received). The run again dispatched no member: `complete_sources` 0, `downloaded_sources` 0, 208 members `pending`.

| Phase | Invocation 1 | Invocation 2 |
| --- | --- | --- |
| Before the first child call | 904 s | 1,093 s |
| Discovery | 349 s (cut short by `permit_expired`) | 862 s (complete) |
| After discovery, before `selection.json` | 556 s | 760 s |
| Total before any dispatch | 1,809 s | 2,715 s |
| Dispatch cutoff (from the run start) | 1,800 s | 1,800 s |
| Registered members at the start / after | 127 / 155 | 155 / 208 |

- The cutoff passed during discovery in invocation 2, and during selection in invocation 1.
- The two quiet phases scale with the member count. Before discovery: 904 s / 127 = 7.1 s and 1,093 s / 155 = 7.05 s for each member. After discovery: 556 s / 155 = 3.6 s and 760 s / 208 = 3.65 s for each member. Together about 10.7 s for each registered member in each run. At 208 members that is about 2,200 s, more than the 1,800 s cutoff, without any discovery time.
- The member count grows when discovery writes a new source workset. Invocation 1 added 28 members and invocation 2 added 53. Source worksets are content-addressed, so a run that finds the same listings adds none. A new business day adds new daily bodies and so a new workset.
- Pending sources grew from 113 to 117 (4 new daily bodies, 2026-11-02 to 2026-11-05). The eligible list therefore did not shrink, and stop rule 10 halts.

Reading: with 208 registered members, no invocation reaches its first dispatch before the 1,800 s cutoff, at a 3,600 s run. The campaign cannot make progress under the live config and the 2a release. The cause is the pre-dispatch cost per registered member, which is the cost of `evaluate_member` in the selection passes (hypothesis, not profiled). Plan 8 has no step that lowers it. A fix needs a code change or a different dispatch design, which plan 8 forbids.

## Comparison with Stage 2 (release 1c, `c4de77b8…`)

Indicative only. Source: `specs/evidence/baseline-campaign/invocations/*.json` and `logs/baseline-campaign/timing-after-*.json`. The member counts and slices differ, and Stage 2's records do not give the registered member count at each start.

| Run | Release | Time before the first member starts | Note |
| --- | --- | --- | --- |
| Stage 2, k = 2 (pilot slice, 75 members) | 1c | 62 s | A narrow slice |
| Stage 2, k = 4 (live config, range `2020Q1`–`open`) | 1c | 624 s | The same pattern as now. A third of the 1,500 s cutoff of a 3,300 s run |
| Stage 2b, k = 1 | 2a | no member started; 1,809 s of work first | 127 registered members at the start |
| Stage 2b, k = 2 | 2a | no member started; 2,715 s of work first | 155 registered members at the start |

Reading: the pre-dispatch cost also exists on 1c, at about 5 s for each registered member (624 s for about 127 members, discovery included). On 2a it is at least about 3 times higher. So the follow-up has two parts. The cost grows with the number of registered members, which is a dispatch-design property. It also rose in 2a. The 2a part is not profiled.
