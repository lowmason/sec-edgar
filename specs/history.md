# Development history

## 9-sec-filing-index-pre-dispatch-cost — 2026-11-15
Plan: specs/plans/completed/9-sec-filing-index-pre-dispatch-cost.md · Spec: specs/completed/sec-filing-index-pre-dispatch-cost.md (retired) · Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a1

Differences from the design:
- Ruling, contradicts spec (Task 3): concern 1 (spec :183-185 says a malformed WorkflowMember row "is skipped, as `inventory()` skips it today"; on the real LocalStateStore a list-valued row makes `scan` raise ValueError('value must be a mapping'), so neither today's reuse nor inventory() skips it) stays as built — deciding spec sentence (specs/sec-filing-index-pre-dispatch-cost.md:97): "It finds the same candidates, returns the same gaps in the same order, and writes the same binding as today." — new and old reuse raise the same ValueError and bind nothing, so H5 holds; the isinstance(dict) guard is reachable only from a simulated store — if wrong, nothing in production differs; spec :183-185 wording is imprecise for the real store (note for the final review, no spec edit).
- Ruling (Task 6): finding 3 (freeze had no factor-2 check): controller chose a sixth timed function pair (results.validate_member_provenance, results.validate_capture) over failing closed — P4 (plan line 101) says each slope is "checked against the median per-member call time of its phase" — if wrong, the freeze check is looser than P4 intends.
- Deviation: the worktree was made with `git worktree add`, not `EnterWorktree`. Source: plan, header.
- Deviation (Task 4): D4: `select_twice` primes one discovery before the store copy, so the equality tests cover a primed discovery only. Source: plan, Task 4.
- Deviation (Task 4): D5: the drain test's `reuse` stand-in takes `**kwargs`. Source: plan, Task 4.
- Deviation (Task 6): after the task review, the path refusal compares file identity (`os.path.samefile`). Source: plan, Task 6.
- Deviation (Task 6): D6: `diff` assigns the 3 added `Failure` rows by `run_id` plus `discovery_id`. Source: plan, Task 6.
- Deviation (Task 8): the `.venv` link pointed at `/tmp/s2a1-venv`, so the gate tested the worktree's code. Source: plan, Task 8.
- Deviation (Task 8): the final review found one Important test gap (the H4 test), fixed in `20ac48b`; a test only, so the gate did not run again. Source: plan, Task 8.
- Deviation (Task 9): the Step 4 commands ran from a temporary script with `set -e`. Source: plan, Task 9.
- Deviation (Task 10): Steps 3 and 4 ran as one background chain that stops at the first non-zero exit. Source: plan, Task 10.
- Deviation (Task 10): `project` exited 4 for `before_discovery`; the owner accepted a hand-worked bound of 281.2 s (D9). Source: plan, Task 10.
- Deviation (Task 11): `walls` ran from a temporary script that sampled the load. Source: plan, Task 11.
- Deviation (Task 11): the longest wall, 1,074.9 s, is above 1,056 s; the owner raised the reserve under the Stage 1b rule (D10). Source: plan, Task 11.
- Deviation (Task 12): the reserve changed from 1800 to 1824 as well as the release (D10, D11). Source: plan, Task 12.
- Deviation (Task 12): `release.md` elides `sec.user_agent` in the binding, because it holds the owner's contact address. Source: plan, Task 12.
- Deviation (Task 13): beyond spec §7's list: the 2a release's 3,200 s selection time, a reserve of 1824 in the runbook example, and the gap name in the 2a1 spec §4.4 item 1 (D12). Source: plan, Task 13.
- Deferred: 3 items. Source: specs/deferred_items.md, § 9-sec-filing-index-pre-dispatch-cost.
