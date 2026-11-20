# sec-filing-data reset review

Read-only review of 2026-11-16, made before the reset to the
[sec-filing-data roadmap](../completed/sec-filing-data-roadmap.md). Counts come from `git` on `main` at `f10c70f`
(tracked files only). No SEC request was sent.

## What worked on 2026-11-16

| Piece | Works on real data | Artifact | Evidence |
|---|---|---|---|
| Index download | Yes, download only | `data/objects/raw/sec/indexes/`: 28 quarterly ZIPs, 2020Q1–2026Q4 (97 MB), and 84 daily files, 2026-07-01 to 2026-10-30 (35 MB) | [Coverage finding](../evidence/baseline-campaign/coverage-finding.md) §2 |
| Index catalog from the daily files | Yes, partly | `data/objects/curated/sec/filing_index/`: v1 Parquet, 26 filing quarters, 361,367 rows, most in 2026Q3 | Same file, §1 |
| Parse of the 28 quarterly files (v2 rule) | Yes, once, offline, on a scratch copy that was deleted | None kept. 8,083,653 rows in 6,306 s. 2026Q3: 302,499 rows in 241 s, with 5 repeated keys. | [2a release record](../evidence/stage2a/release.md), "Scratch re-transform" |
| Live ingestion run (`backfill`) | No. The 2026-11-15 folder rename blocks every registered member. | None | `specs/evidence/stage2b/planning/rename-check.md` on branch `claude/sec-filing-index-stage-2b-0111b6` |
| Filing-document envelope parser | No. It passes fixtures only. | Branch `platform-stage1`, 60 tests | `specs/evidence/platform-stage1/stage-exit.md` on that branch |
| XBRL facts, ownership records, as-of views | No. Not built. | None | None |

## What made the work slow (largest first)

1. **Scope: final-standard machinery came before any answer.** Five of the seven ticked ingestion
   stages (1a, 1b, 1c, 2a, 2a1) were fix stages, and each shipped a reviewed content-addressed
   release. Together they took 9.9 days, 7,729 plan lines and 1,418 stage-spec lines. Three of the
   five dealt with run-time budgets. Live runs found the problems behind 1c, 2a and 2a1 only.
2. **Scope: the order followed the method, not the owner's question.** Two roadmaps held 24 stages.
   The first usable index was the 8th ingestion stage, and none of the 7 ticked stages gave a usable
   answer. Real filings came first at platform Stage 6, and published facts at Stage 12.
3. **Scope: the full range under strict rules.** The first campaign targeted 28 quarters, and one
   rule against repeated keys quarantined all 28. Registered members never retire. They grew from 127
   to 208, and the work before the first dispatch grew from 1,809 s to 2,715 s, against the 1,800 s
   cutoff of those runs.
4. **Process: the cost of each stage.** After the port, `specs/` gained 26,721 Markdown lines,
   against 1,437 source lines and 6,836 test lines (lines added after `5ae708b`, by
   `git log --numstat`). `main` holds 163 `docs(specs|plans|evidence)`
   commits and 101 `feat|fix|test` commits. The ingestion roadmap had 10 resume passes, and 4 of them
   added no stamp.
5. **External: limits outside the project were not binding.** The SEC allows 10 requests per second
   per user, and the engine capped itself at 3. All of Stage 2 used 167 requests and 127 MB.
