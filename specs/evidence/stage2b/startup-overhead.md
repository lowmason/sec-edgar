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
