# Stage 2b baseline campaign: scope, budget and approval

**Status:** Approved for live execution within the limits above.
**Plan:** [plan 8](../../plans/8-sec-filing-index-ingestion-spec.md).
**Spec:** §§4.2–4.9, 5–6, 7 G2 of the [ingestion spec](../../sec-filing-index-ingestion-spec.md).
**History:** this campaign repeats the method of [Stage 2](../baseline-campaign/campaign.md) on the 2a release. Stage 2's records stay unchanged. Where this file says "plan 2", it means the [completed plan 2](../../plans/completed/2-sec-filing-index-ingestion-spec.md).

## Identity

| Item | Value |
| --- | --- |
| Release | `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec` (application 0.2.0, `git_revision` `32863852ce57f1da99db4720bd1c729727b4ec0c`), selected at `4d1f806` |
| Live config | `conf/sec-edgar-local.json`, range `2020Q1`–`open`, daily handoff `2026-10-01`, parser / schema `sec-index-parser-v2` / `sec-index-v2`. File SHA-256 `7d61c3e2da7fd4e88eea5aaf65ab10e4b7a36b9b96d5c6e7f70a3a69429bafda`. Effective SHA-256 `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733`. |
| Dispatch reserve / floor | 1,800 s / 480 s. At the 3,600 s timeout (O3, D6), no member starts after 1,800 s. |
| Configs | The live config only. No config under `conf/stage2/` is ever run. |
| Data / log roots | `/Users/lowell/Projects/sec-edgar-local/data` / `…/logs` |
| Pre-campaign backup | `backups/stage2b-pre-campaign-20261106T174241Z`. Backup `state.sqlite3` SHA-256 `afb9071ae698b7578806b81ba60420c5f866f2262dc33c34971012e2a693cec6`. See `pre-campaign.md`, section `Backup`. |
| Evidence tool | `scripts/baseline-campaign.py` at commit `d8c2e07` |

## Release gate

Open on F1, F3, Task 2's member timing and the Step 2 preflight. Live work still needs the Approval below.

1. **Every member re-runs (F1).** The store holds 127 registered members. Under v2 none is complete, so the first invocation selects all of them and lists no source as already complete.
2. **One expected gate (F3, D3).** Only 2026Q3 should gate. Task 2 measured 42 withdrawals on the scratch copy, and `awaiting_approval`. The campaign leaves it gated for Stage 4 and runs no `approve`.
3. **Member timing in dispatch order (Task 2).** [pre-campaign.md](pre-campaign.md) has the ten steps. The longest member wall is 3,239.6 s, the daily 2026-07-01, which is the first v2 write to 2026Q3. It is above the 1,440 s limit of D2. The owner accepted it as an exception (D6). The next longest is 1,398.8 s (2026Q1). The scratch walls exclude `collect`, child start and the completion check, so live walls are higher.
4. **Convergence (Task 2).** Every daily member is complete after its quarter took a v2 authority. The 2026Q3 member is incomplete with only `publication_pending`.
5. **The offline preflight passes** on this release (`pre-campaign/preflight.json`): backfill `2020Q1`–`open`, reserve 1,800 s, effective hash `f2082322…`.
6. **A fresh backup exists (D4)**, verified against the files report.
7. **Origin releases are installed.** The `collect` child of a member that a v1 release completed runs on that release's interpreter. The releases `c4de77b8…` (1c), `9fa189a0…` (1b) and `fc68adef…` are still installed under `releases/`. The fixture tests cannot cover this path.

## Source scope

- Workflow: launcher `backfill` only, with the live config. No `daily`, `reconcile`, low-level command, `approve` or `rollback`.
- Requested units: the quarterly sources 2020Q1–2026Q4, which is 28 units, and the 7 duplicate-key daily sources 2026-07-08, 2026-07-13, 2026-07-22, 2026-07-27, 2026-09-17, 2026-09-24 and 2026-10-21. 2026Q4 is the open quarter. Its source is quarter-to-date, and absence from it is not withdrawal authority (§4.4).
- Every other daily source runs as retained work (O5). The finding reports it apart, for Stage 3. Daily bodies after 2026-10-30 are registered as the runs discover them. A run that lists them meets the revisit condition of deferred item 2 (`specs/deferred_items.md`). The finding reports the evidence and does not diagnose it.
- Dispatch order (F2): the quarterly members 2020Q1–2025Q4, then the daily members, then the quarterly members 2026Q1–2026Q4. The runner defers the rest at the cutoff, and stop rule 10 reruns until nothing is waiting.
- Source quarters and output filing quarters differ (§4.2). Daily rows can be back-dated into old filing quarters. Coverage lists quarters outside the range under `other_filing_quarters`.
- Expected exceptions:
  - 2026Q3 `gated` (F3, D3), and its re-check on each later run (F5, about 940 s each).
  - Daily members held `awaiting_approval` by that gate.
  - A deadline kill of the 2026-07-01 daily member, when it starts after about 360 s into an invocation (D6). Stop rule 2 still halts on it.
  - A refused incremental candidate (C6): halt, remove no objects, Stage 4 disposition (rule 8).

## Budget

| Bound | Limit | Enforced by | Basis |
| --- | --- | --- | --- |
| Invocations | 30 | audit, stop rule 4 | O1: about 13 for the 25 closed quarterly members at about 2 for each run (F2, F4), 2 for the dailies, 3 for 2026Q1–2026Q4, and a margin |
| Runtime per invocation | 3,600 s (the live maximum) | launcher | O3, D6. Must stay above the 1,800 s reserve |
| Dispatch cutoff | deadline − 1,800 s, which is 1,800 s into a run | runner | parent spec §4.7 |
| Member wall | 3,600 s (`max_member_wall_seconds`) | timing after the invocation, stop rule 7 | D6. D2's limit was 1,440 s. The daily 2026-07-01 measured 3,239.6 s and the next longest 1,398.8 s. At 3,600 s the rule trips only above the invocation maximum. A deadline kill is rule 2. |
| Request rate | 3/s, one collector | coordinator | §4.8 |
| Attempts per URL per command | 5 | downloader | §4.8 |
| Bytes per response | 67,108,864 received / 536,870,912 expanded | downloader | §4.8 |
| Request attempts per invocation | 700 | audit after the invocation | O1; about 50 attempts for each run (F9) |
| Request attempts, campaign | 2,500 | audit | O1 |
| Distinct URLs, campaign | 300 | audit | O1 |
| Received bytes, campaign | 1,073,741,824 | audit | O1. Stage 2's invocation 4 received 95,057,260 bytes (F9). The quarterly snapshots are retained, so later runs reuse them. |
| Expanded validation bytes, campaign | declared 16 GiB | not counted durably by the launcher; reported after the campaign from retained raw ZIP member sizes | as plan 2 |
| Free disk before each invocation | at least 50 GiB | pre-check | 455 GiB were free at planning (F7) |
| Store growth | at most 30 GiB over the 1 GiB size of `data/` in `pre-campaign.md` | pre-check | whole-quarter generations are rewritten by full rebuilds |
| Window | from the approved UTC start to 2026-11-20T13:00:00Z (O2) | pre-check | must end before 2027-01-01T00:00:00Z, so `open` stays 2026Q4 |

The audit checks the aggregate limits between invocations, not inside one. Inside one invocation, the hard bounds are the runtime, the dispatch cutoff, the rate, the per-URL attempt limit and the per-response byte limits.

## Stop rules

After each invocation, apply the first rule that matches.

1. **Halt** on a launcher exit of 2, 6, 8, 9 or 11, or any exit outside 0, 3, 4, 5, 7 and 10.
2. **Halt** when the run left no `result_ref` or no `workflow_summary`. This is a deadline or crash (plan 2 F8). Follow `docs/runbooks/local-recovery.md` with the owner before any further invocation.
3. **Halt** on a workflow outcome of `access_blocked`, `ownership_lost`, `state_conflict` or `internal_error`.
4. **Halt** on any audit breach, any HTTP 403, or any `uncertain` transport attempt.
5. **Halt** when the files comparison against L12 reports `missing` or `changed_immutable`.
6. **Halt** when `workflow_summary.summary_error` is not null.
7. **Halt** when the timing report has a breach: a member wall above `max_member_wall_seconds` (3,600 s, D6).
8. **Halt** when any member has outcome `invalid_source` and is not quarantined (C6; plan 2 O16). Read the member's gaps and report them.
9. **Halt** when `after.gated` names a quarter other than 2026Q3, or `after.quarantined` is not empty (O4). Report the member's gaps and the gate's change counts.
10. **Rerun** when `after.eligible` is not empty, and this is k = 1 or the previous invocation reduced its length. Halt when a rerun does not reduce it.
11. **Halt** on the second consecutive invocation with `discovery_complete: false`, unless every `discovery_failed` directory lies under `https://www.sec.gov/Archives/edgar/daily-index/` and every discovery gap is `permit_expired` or `ancestor_failed` (plan 2 rule 10, option (a)).
12. **Finish** when every quarter 2020Q1–2026Q4 has a campaign result and no member has outcome `pending`, `deferred` or `throttled`. Quarantined, failed and `awaiting_approval` members are not eligible work.

A halt stops the campaign. The operator reports to the owner and does nothing else. A halt is evidence, not a failure of the plan.

## Evidence locations

- Committed: `specs/evidence/stage2b/`. That is `pre-campaign.md`, `pre-campaign/`, `campaign.json`, this file, `invocations.md`, `invocations/<k>-<run-id>.json`, `final/` and the finding.
- Raw and ignored: `data/` (store, durable results), `logs/<run-id>/<attempt-id>/` (launcher evidence), `logs/stage2b/` (coverage, audit, timing and files reports after each invocation), and `backups/` (the pre-campaign backup).

## Approval boundary

- A live invocation needs all four of these: (1) the Release gate above, open; (2) the `Approval` section below, completed with the owner's words and committed; (3) the latest files check with exit 0; (4) the sole-issuer declaration, with its start time.
- Never authorized here: `approve`, `rollback`, `daily`, `reconcile`, a low-level command, a parser, schema, release or live config change, a second root, object removal, or any SEC request outside the launcher.
- The owner's D2 exception (D6, recorded in `pre-campaign.md`) covers the member-wall limit and the runtime only. It is not live authority.

## Approval

The owner answered each of the 10 items of plan 8 Task 4 as a separate question in the operator session. Quoted text is the option the owner selected. The owner's earlier answer on the D2 breach (D6, "Exception, O3 3600") is recorded in `pre-campaign.md`.

- Owner: Lowell Mason. Approved on (UTC): 2026-11-06T17:49:43Z. The owner gave no timestamp; this is when the operator recorded the answers.
- 1. Range and units: "Confirm as proposed (Recommended)" (2020Q1–2026Q4, 28 units, and the 7 duplicate-key daily sources).
- 2. Source scope, budget and stop rules: "Confirm as proposed (Recommended)".
- 3. Runtime per invocation: "3600 s (Recommended)".
- 4. Window: "Starts at approval, ends 2026-11-20T13:00:00Z (Recommended)". It starts 2026-11-06T17:49:43Z and ends 2026-11-20T13:00:00Z.
- 5. Member-wall limit: "3600 s; halt on a deadline kill (Recommended)". Stop rule 2 stays as written. After a deadline kill the operator halts, reports to the owner and follows `docs/runbooks/local-recovery.md` with the owner. No rerun without the owner.
- 6. The 2026Q3 gate: "Leave gated, no approve (Recommended)" (D3).
- 7. Other daily sources and bodies after 2026-10-30: "Run as retained work (Recommended)" (O5).
- 8. A refused incremental candidate: "Halt, remove nothing (Recommended)".
- 9. The backup: "Accept this backup (Recommended)". Path `backups/stage2b-pre-campaign-20261106T174241Z`, backup `state.sqlite3` SHA-256 `afb9071ae698b7578806b81ba60420c5f866f2262dc33c34971012e2a693cec6`.
- 10. Sole-issuer declaration: "I make this declaration (Recommended)". The owner selected this drafted wording: "During the campaign window, the launcher on this machine is the only SEC client under my identity. No other machine and not the original sec-edgar Azure project sends SEC requests under it." The declaration starts 2026-11-06T17:49:43Z.
