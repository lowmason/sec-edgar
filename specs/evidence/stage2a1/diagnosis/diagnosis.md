# Stage 2a1 diagnosis: the work before the first dispatch

**Date:** 2026-11-13 (UTC 2026-11-14). **Runs diagnosed:** plan 8 invocation 1 (`0746b217-d4ca-4f1d-9b05-d0c447b734ce`)
and invocation 2 (`bdefaa5d-856d-4bc4-a621-018e66b6ef1e`). **Code:** the 2a release `e49d3ba8…` and the 1c release
`c4de77b8…`, each from its own venv. **Stores:** APFS clones of `data/` (208 registered members) and of the Task 3
backup's raw copy (`backups/stage2b-pre-campaign-20261106T174241Z/data-raw`, 127 members), under the ignored
`logs/stage2a1-diag-20261114T031611Z/`. Each timed run used its own fresh clone, because these "read" paths write
(repair rows, `put_once`, `immutable`, bindings). No dispatcher was built, so no discovery child ran and no SEC request
was possible. Nothing was written under `data/` or `backups/` (§10).

Owner approval to profile: 2026-11-13, "Yes, profile now".

## 1. Cause

The selection step (`runner.select_work`, `runner.py:184`) repeats store-wide work once for each registered member.
Each repeat re-validates every stored record it touches, and record decoding is slow. The cost per run is therefore
about (registered members) × (history size), and both grow during a campaign.

1. **History pass for each member.** `evaluate_member` and `WorkflowMembers.completed` both call `_obligations`
   (`completion.py:590`), which calls `_publish_calls` (`completion.py:551`). That function scans every
   `WorkflowChildCall` row (328) and every `Attempt` row (342), re-validates each child call (`checked._authority`),
   and re-validates each of the 75 publish inputs (`checked._transformed_input`). One pass takes about 3.4 s. Before
   discovery each member runs two passes (`completed`, then `evaluate_member`). After discovery each member runs one.
2. **Registry check for each new member.** For a new member with no binding whose source needs no download,
   `reuse_exact_binding` (`runner.py:25`) calls `WorkflowMembers.inventory()` (`runner.py:42`). That re-validates
   every registered member: 208 `read_member` calls, 208 `read_parent` calls and 5,373 listing re-opens. It took
   23.3 s at 208 members.
3. **Parent re-validation for each member.** `read_member` calls `read_parent` (`provenance.py:122`), which re-opens
   every listing of the parent's discovery session. A member costs three `read_parent` calls before discovery.
   `bootstrap_legacy` and `inventory` together made 624 `read_parent` calls and 210 full `WorkflowMember` scans
   (43,680 rows).
4. **Slow record decoding.** `models.record_from_mapping` (`models.py:226`) calls `typing.get_type_hints` on every
   record it decodes. Child-call and listing-receipt checks rebuild `Settings` and re-pin each saved context
   (`config.pin_context`). One `_publish_calls` pass made 58,146 `get_type_hints` calls. One `inventory()` made
   406,287. Hashing raw files is minor: 64 MB per pass.

`evaluate_member` itself is cheap once the history pass is removed. Under v2 no member has a v2 `Processing` row,
so it returns `transform_pending` or `acquisition_pending` right after the history pass.

## 2. Counts

| Record kind | Live copy (208 members) | Backup copy (127 members) |
| --- | ---: | ---: |
| `WorkflowMember` | 208 | 127 |
| `WorkflowChildCall` | 328 | 326 |
| `Attempt` | 342 | 340 |
| `WorkflowMemberResult` | 123 | 123 |
| `Processing` | 77 | 77 |

Plan 8 added only 2 child calls and 2 attempts (one discover child per invocation). The history is the history that
Stage 2 left. Full counts: `outputs/counts-live-208.txt`, `outputs/counts-backup-127.txt`.

## 3. Where invocation 2's time went

File times in the live store (metadata only), UTC, from the run start at 18:31:08Z:

| Phase | From | To | Length | What ran |
| --- | --- | --- | ---: | --- |
| Before discovery | 18:31:08 | 18:49:21 (child `call.json`) | 1,093 s | `bootstrap_legacy`, `inventory`, then `completed` and `evaluate_member` for 155 members |
| Discovery child | 18:49:22 | 18:49:51 (child `result.json`) | 29 s | 39 listing requests, 39 receipts |
| Member projection | 18:49:51 | 19:03:43 (last member workset) | 832 s | 53 new members: `project_member`, then `reuse_exact_binding`, one every 14–21 s, slower as the count grew |
| After discovery | 19:03:43 | 19:16:23 (`selection.json`, 18.5 MB) | 760 s | `evaluate_member` and `capture_member_provenance` for 208 members, then `freeze_selection` |

Plan 8 (`specs/evidence/stage2b/startup-overhead.md`) counted the first three rows' boundary differently: its
"discovery 862 s" is the discovery child (29 s) plus the member projection (832 s). The network part of discovery was
29 s.

The same pieces, timed on the live copy with the 2a release (`outputs/2a-live-*.json`):

| Piece | Measured on the copy | Rebuilt for invocation 2 | Invocation 2 |
| --- | --- | ---: | ---: |
| `bootstrap_legacy` + `inventory` (208) | 80.3 s + 23.3 s | about 77 s at 155 | |
| `completed` + `evaluate_member`, per member | 3.68 s + 3.52 s = 7.2 s (n = 12) | 155 × 7.2 = 1,116 s | 1,093 s (with the row above) |
| `project_member` + `reuse_exact_binding`, per new member | 0.18 s + one `inventory()` (17–23 s) | 53 × about 20 s = 1,060 s | 832 s |
| `evaluate_member` + `capture_member_provenance`, per member | 3.65 s + 0.28 s = 3.93 s (n = 12) | 208 × 3.93 = 817 s | 760 s (with the row below) |
| `freeze_selection` (208) | 25.3 s | 25 s | |

The rebuilt totals run 10–25 % above the live run, because the counters add overhead. The ratio of the two passes
(7.2 s to 3.9 s) matches plan 8's 7.05 s and 3.65 s for each member.

The sampled `reuse_exact_binding` on the copy returned at once (0.16 s), because invocation 2 had already bound
those 53 members. `outputs/2a-live-reuse.json` removes one member's `Binding` row on a fresh clone and reruns it: the
call re-binds the member and spends all its time in `inventory()` (`outputs/2a-live-reuse.prof.txt`, under cProfile).

## 4. The rise from the 1c release to the 2a release

Same 127-member backup copy, `before` phase, 24 members sampled evenly (`outputs/ab-*-before.json`):

| Release, versions | Finished members (of 24) | Per finished member | Per pending member | Mean per member |
| --- | ---: | ---: | ---: | ---: |
| 1c, v1 | 12 | 4.50 s | 3.67 s + 3.81 s | 5.99 s |
| 2a, v1 | 12 | 4.43 s | 3.63 s + 3.75 s | 5.90 s |
| 2a, v2 | 0 | | 3.79 s + 3.72 s | 7.51 s |

The 2a code costs the same as the 1c code on the same store and versions. The rise has four parts, none of them a
code regression:

- Under v2 no member counts as finished, so every member takes the pending path (two history passes) before
  discovery, and every member is in the after-discovery pass.
- Registered members grew from 127 to 208.
- Each new member registered in a run pays one `inventory()` (§1 item 2). Invocation 2 registered 53.
- Stage 2's invocation 4 ran when the history was smaller, so its passes were cheaper.

Plan 8's comparison (`startup-overhead.md`, about 5 s per member on 1c) is consistent with this.

## 5. Member growth

A member is one source projected from one discovery parent workset (`provenance.project_member`). A parent is
content-addressed. When a new business day changes the daily listing, the run's discovery writes a new parent, and
every source in it is registered again as a new member: 28 in invocation 1 and 53 in invocation 2, against 4 new daily
bodies. Older members of the same source stay registered and are evaluated in every run. So registered members grow by
about the parent's source count, now 53 and one more each business day, for each business day that an invocation runs.
A run that finds the same listings adds none.

## 6. The daily 2026-07-01 member

Plan 8 Task 2 measured this member at 3,239.6 s offline (`specs/evidence/stage2b/pre-campaign.md`, step 2). It is
the first v2 write to nine quarters, 2024Q3 to 2026Q3. Rerun here on a fresh live copy with the plan 8 method
(`run_transform`, then `run_publish`, fresh pinned contexts, no network client), with timers around the publish
steps (`outputs/2a-member-20260701.json`):

| Step | Time | Calls |
| --- | ---: | ---: |
| Transform (the member's own source) | 6.0 s | 1 |
| Publish, total | 3,453.3 s | 1 |
| `validate_candidate_content` | 1,649.5 s | 9 (one per quarter) |
| `transform_member` (v1 base sources re-transformed to v2, or reused) | 913.3 s | 380 |
| `_load_observations` | 767.5 s | 9 |
| `_load_active` | 48.6 s | 9 |
| `_write_parquet` | 44.1 s | 18 |
| `typing.get_type_hints` | | 49,970,107 |

By quarter, with the base sources read from each v1 base manifest:

| Quarter | Base sources (all daily) | Base rows | `build_candidate` |
| --- | ---: | ---: | ---: |
| 2024Q3 | 16 | 29 | 185 s |
| 2024Q4 | 21 | 63 | 196 s |
| 2025Q1 | 26 | 119 | 230 s |
| 2025Q2 | 28 | 226 | 240 s |
| 2025Q3 | 41 | 882 | 349 s |
| 2025Q4 | 44 | 592 | 350 s |
| 2026Q1 | 59 | 666 | 488 s |
| 2026Q2 | 68 | 1,035 | 544 s |
| 2026Q3 | 77 | 280,965 | 867 s |

The base sources sum to 380, the `transform_member` call count. A quarter costs about 7 to 11 s for each base source,
whatever its row count. 2026Q3 costs more because of its rows. A v1 base never takes the incremental path
(`incremental.py:42`), so each of the nine quarters is a full rebuild that re-reads and re-validates every base
source.

The run took 6.6 % longer than plan 8's, because of the timers and the call counter.

The cost is a one-time transition cost. A later daily on a quarter with a v2 base publishes incrementally (plan 8
step 8: 7.7 s).

**Hypothesis, not checked:** in the campaign's real order the quarterly members 2020Q1 to 2025Q4 run before this
daily, because period `2025Q4` sorts before `2026-07-01`. If the quarterly for 2024Q3 to 2025Q4 publishes clear, and
this daily's pinned snapshot is the same snapshot that its v2 base holds, this daily finds that quarter unchanged. Both
conditions are open. A closed quarter with withdrawals gates, as 2026Q3 did with 42. A different snapshot gives a
different processing key, and the newer receipt then forces a full rebuild. 2026Q1 to 2026Q3 stay v1 until this daily
runs, because `2026-07-01` sorts before `2026Q1`. Those three quarters took 1,900 s here, so even under the hypothesis
the member stays above the 1,440 s that D2 allowed (1,800 s reserve ÷ 1.25).

## 6a. Spike: one type-hints result per record type

A diagnosis-only spike, not a fix: the scripts' `--cache-type-hints` switch replaces `models.get_type_hints` in the
script's process with a per-type cache. Both call sites pass one type and only read the result. Same live copy, same
samples (`outputs/2a-live-*-cachedhints.json`):

| Piece | Plain | Cached hints |
| --- | ---: | ---: |
| `bootstrap_legacy` | 80.3 s | 41.3 s |
| `inventory` | 23.3 s | 11.8 s |
| `completed` + `evaluate_member`, per member | 7.2 s | 3.47 s |
| `evaluate_member` + `capture_member_provenance`, per member | 3.93 s | 1.88 s |

The decode cost is about half of every piece. The repetition (§1 items 1–3) remains, so at 208 members the work
before the first dispatch would still be about 1,200 s.

The daily 2026-07-01 member, rerun on a fresh live copy with the same switch
(`outputs/2a-member-20260701-cachedhints.json`):

| Step | Plain (§6) | Cached hints |
| --- | ---: | ---: |
| Transform | 6.0 s | 1.9 s |
| Publish, total | 3,453.3 s | 988.5 s |
| `validate_candidate_content` | 1,649.5 s | 474.8 s |
| `transform_member` | 913.3 s | 264.0 s |
| `_load_observations` | 767.5 s | 216.6 s |
| 2026Q3 `build_candidate` | 867 s | 255 s |

Same nine quarters published, same call counts (380 `transform_member`, 49,970,107 `get_type_hints` calls, which the
counter still wraps). This is the worst case: all nine quarters on v1 bases. About 990 s is below the 1,440 s that the
1,800 s reserve allows under D2's 1.25 factor.

## 6b. Spike: each store-wide step once, with cached type hints

A second diagnosis-only spike bounds what removing the repetition (§1 items 1–3) could save. The `--memoize-store-wide`
switch computes, in the script's process, `_publish_calls` once, `read_parent` once per parent ref and
`WorkflowMembers.inventory` once. It is not safe across writes and is not a design. `_obligations` still decodes every
publish input for each member, so the estimate is conservative. All 208 members, fresh live copy
(`outputs/2a-live-*-memo-cachedhints.json`):

| Piece | Plain (§3) | Cached hints and memo |
| --- | ---: | ---: |
| `bootstrap_legacy` + `inventory` | 103.6 s | 4.8 s |
| `completed` + `evaluate_member`, 208 members | about 1,498 s | 65.7 s (0.32 s each) |
| `evaluate_member` + `capture_member_provenance`, 208 members | about 817 s | 46.4 s (0.22 s each) |

With `freeze_selection` (25.3 s plain, not re-timed) and the 29 s discovery child, the first member would start at
about 170 s at 208 members. The projection loop adds about 0.2 s for each new member once `inventory()` runs once. In
invocation 2 the first dispatch would have been due at 2,715 s or later. The cost per member is then about 0.6 s for
each run, so the work still grows with registered members, now slowly.

## 7. Projection

Without a change, at the current history, the work before the first dispatch is about:

- before discovery: 0.5 s × N + 7.2 s × N (N = registered members at the start);
- member projection: about 0.11 s × N for each new member registered;
- after discovery: 3.9 s × N' + 0.12 s × N' (N' = N plus the new members).

At N = 208 and no new members that is about 2,500 s, above the 1,800 s cutoff with no discovery at all. Each history
pass also grows with the history (`specs/deferred_items.md`, "History-scan cost": 0.022 to 0.029 s per
`WorkflowChildCall` row for each pass).

## 8. Relation to the deferred item "History-scan cost"

It is the same scan. The deferred item (`specs/deferred_items.md`, section `5-sec-filing-index-per-member-cost —
2026-10-28`) names `_obligations` and `reuse_exact_binding` and measures per-member engine time against
`WorkflowChildCall` rows. This diagnosis finds the same functions in selection, where they run once per registered
member instead of once per dispatched member. The member's own completion check (`processing.py`, through
`evaluate_member`) still runs one history pass per dispatched member.

## 9. What this does not cover

- The `daily` and `reconcile` commands use the same `select_work`, so the same cost applies. Only `backfill` was timed.
- The discovery child was not run (no SEC request). Its 29 s comes from invocation 2's file times.
- Times on the copy include the counters' overhead. cProfile times (`*.prof.txt`) are about 2.7 times the plain times.

## 10. Side effects and store checks

- **Live store.** `outputs/live-data-before.sha256` (5,452 files) was taken before the first clone. No writer ran,
  and `data/` had no `-wal` or `-shm` file.
- **Backup.** `outputs/backup-before.sha256` (5,270 files). The backup was only read, by `cp -c`.
- **Bytecode caches in the release venvs.** The first timing runs used `python -I` without `-B -X
  pycache_prefix=/dev/null`. Python wrote 50 `.pyc` files into each of the 2a and 1c release venvs
  (`sec_edgar_ingest` and `pyarrow` `__pycache__` folders). All were created on 2026-11-13. The release payload check
  skips `__pycache__` (`runtime.py:476`), and every release command runs with `-B -X pycache_prefix=/dev/null`, so
  they change neither verification nor execution. The member runs (§6) passed `preflight_current` on the 2a release
  with the files present. The 1b release venv holds 44 such files from 2026-10-29. The list of the 100 files is in
  `logs/stage2a1-diag-20261114T031611Z/pyc-created-2026-11-13.txt`. They stay until the owner decides. Later runs used
  the release flags.
- **After the runs.** The live `data/` and the backup were hashed again after the member run of §6 and the spike of
  §6a: both lists are identical to the before lists, and `data/` still holds only `objects` and `state.sqlite3`. A
  final check after the last run is in §12.

## 12. Final store check

After the last run (§6b), with no diagnosis process running: the live `data/` file list and hashes equal
`outputs/live-data-before.sha256` (5,452 files), `data/` holds only `objects` and `state.sqlite3`, and the backup
equals `outputs/backup-before.sha256` (5,270 files). No SEC request was sent.

## 11. Files

- `scripts/profile_selection.py`: times the selection pieces by phase (`before`, `project`, `after`, `freeze`).
- `scripts/profile_pieces.py`: one `_publish_calls` pass under cProfile, and the unbound-member reuse path.
- `scripts/profile_member.py`: the daily 2026-07-01 member's transform and publish, timed by phase.
- `outputs/`: the JSON results, cProfile summaries, counts and hash lists named above.
