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
