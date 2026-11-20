# sec-filing-data Stage 4 findings

This file is the evidence record of Stage 4 of the [sec-filing-data roadmap](sec-filing-data-roadmap.md).
[Plan 14](plans/14-sec-filing-data-stage-4-as-of-views.md) implemented it, against the
[Stage 4 spec](sec-filing-data-stage-4-as-of-views.md). Under the lighter process (spec section 3), this file is the
only evidence record. It records the results of the live run, each problem found and fixed, and the measured cost.

## Run record

- Output root: `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`. It is the Stage 1, 2 and 3 root. It sits in the
  main checkout and is git-ignored. Stage 4 wrote only `stage4/`, `manifests/stage4@42fb313956e0.json` and
  `runs.jsonl` lines.
- Code: branch `claude/sec-edgar-stage-4-exec`. The run used commit `42fb313956e08efa81163c1717a025bb7551c01f`, the
  final code commit. It holds Tasks 1 to 10 and the fix rounds of their reviews. The final whole-branch review found
  nothing to fix. The suite had 568 passing tests at that commit. The baseline was 415.
- Stamp: code version `42fb313956e0…` (the run commit), Python 3.14.0 and PyArrow 25.0.1.
- Tree: `git status --porcelain` on the pinned paths printed nothing before the run. No commit landed on the branch
  from Step 1 to Step 10. Every one of the 58 run lines of this run has `tree_clean` true.
- Date: the run took place from 2026-11-20 01:27 UTC to 01:30 UTC (2026-11-19, 20:27 to 20:30 in New York).
- Input: `master.zip` in place at `/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip`, SHA-256
  `526d2dbf…`.
- SEC access: `fetch-partners` only. `SEC_USER_AGENT` came from `sec.user_agent` at tag `ingest-parked-2026-11-16`,
  by the README command. A wrapper script in the ignored execution workspace ran that command and the fetch. The value
  was never printed, and no committed line holds it.
- Before the run (plan Task 11, Step 1):
  - The installed package path was inside the worktree: `packages/sec-filing-data/src/sec_filing_data/`.
  - `filing-data/` was git-ignored. The check ran in the worktree, because the session's worktree guard refuses
    `git -C` on the main checkout. The branch has not changed `.gitignore` since `66f81c5`, the main checkout's
    commit, so the rule is the same.
  - No `sec-filing-data` or `sec_edgar` process ran. `find "$ROOT" -name '.*'` printed nothing. `stage4/` did not
    exist.
  - The Stage 1 ledger had 1,006 lines (SHA-256 `c348d7d4…`). The Stage 2 ledger had 2 lines (SHA-256 `551069cb…`).
  - One digest over the files of `bytes/` was `c854e7e5…`.
  - `sh scripts/check-sec-filing-data.sh` gave `Ran 568 tests` and `OK`.
  - `verify` on `tables@c36aa2cf5571.json` gave exit 0, with `files: ok`, 9 `binding … ok` lines and 6
    `rederive … ok, 20 rows` lines.

## Partners

`partners` printed `partners: 20`, `original_previous_accession: 2`, `original_date_issuer_owner: 2` and
`candidate_amendment: 16`, and exited 0. It sent no request.

A script compared each row of `stage4/tables/partners.parquet` with spec Appendix A, as the tuple (partner, form, date
filed, rule, sampled filing). The two lists are equal, row for row: 20 rows, none only in the appendix and none only
in the table. No partner was chosen twice, so the table has 20 rows for 20 distinct accessions. Appendix A did not
change.

## SEC use

- `fetch-partners` exited 0 and printed `ok: 20`, `stage 4 requests: 20 of 30` and
  `stage 4 wire bytes: 1578979 of 50000000`.
- The Stage 4 ledger, `stage4/fetch-log.jsonl`, has 40 lines: 20 request records and 20 response records. No request
  was retried, and no second `fetch-partners` run was needed.
- Against the owner's budget (D2): 20 of 30 requests, and 1,578,979 of 50,000,000 wire bytes. The spec planned 20
  requests and less than 5,000,000 wire bytes.
- No other SEC client ran (`pgrep`, Step 1). The fetch took 9.24 s for 20 requests. The client kept at least 0.34 s
  between request starts.

## Partner tables and links

`partner-tables` exited 0 and printed `fetches: 20`, `filings: 20`, `parties: 36`, `documents: 37`,
`ownership: 258`, `ownership_status: 17` and `links: 43`.

- All 20 `fetches` rows are `ok`. The 17 partners of an ownership form each have an `ownership_status` row with no
  reason (12 Schedule 13D/A, 2 13F-HR/A, 2 Form 4 and 1 Form 4/A). The 3 Form D and D/A partners have none, as spec
  5.4 says.
- `links` has 43 rows: 27 held in `sample` and 16 held in `partner`.
  - By rule: `previous_accession` 25, `original_date_issuer_owner` 4, `filer_period` 3 and `none_declared` 11.
  - By `original_held_in`: `sample` 10, `partner` 4 and not held 29.

The 27 sampled amendments give the counts of spec 5.5:

- 4 link to their partners:
  - D/A `0002065248-26-000003` amends `0002065248-26-000002`.
  - D/A `0002135638-26-000005` amends `0001840735-26-000021`.
  - 4/A `0000892251-26-000099` amends `0000892251-26-000081`.
  - 4/A `0001628280-26-051492` amends `0001628280-26-047904`.
- 14 have `link_problem` `not in the 2026Q3 index`: 9 Form D/A and 5 Schedule 13D/A or 13G/A.
- 4/A `0000108985-26-000080` has `no index match for 2026-04-16 and CIKs 108985, 1434722`.
- 13F-HR/A `0000905148-26-003942` has `no held 13F-HR of filer 1257391 for period 20211231`.
- 7 are `none_declared`: the 4 `SC 13D/A;SC TO-T/A` filings, F-1/A `0001213900-26-074871`, NPORT-P/A
  `0001410368-26-087900` and C/A `0001872856-26-000280`.

The links of the 16 partner amendments:

- 10 link to a sampled original. These are the forward pairs below.
- 2 link to an original that the index lists and we do not hold:
  - Schedule 13D/A `0001361570-26-000021` names `0001361570-26-000020`. The index lists `-000020`, but no partner
    rule chose it, so we do not hold it. The other partner of the same sampled filing, `0001361570-26-000019`, names
    the sampled filing `0001361570-26-000017` and forms a forward pair.
  - Form 4/A `0001921640-26-000017` declares an original date, and rule 2 finds `0001921640-26-000011`. Spec 5.2
    expected that it amends an earlier filing, not its sampled Form 4 `0001921640-26-000018`. Its bytes confirm this.
- 4 Schedule 13D/A partners are `none_declared`: `0001104659-26-106301`, `0001193125-26-315913`,
  `0001193125-26-328063` and `0001477932-26-004961`. Each has an `edgarSubmission` document with no
  `previousAccessionNumber`, so its bytes name no original. Each stays held and answers at its own time.

Confirmed pairs, both filings held:

| Direction | Amendment | Original |
|---|---|---|
| forward | `0000902664-26-003894` | `0000902664-26-003832` |
| forward | `0000902664-26-003970` | `0000902664-26-003832` |
| forward | `0000912282-26-001155` | `0000912282-26-000961` |
| forward | `0001119032-26-000009` (13F-HR/A) | `0001119032-26-000007` |
| forward | `0001361570-26-000019` | `0001361570-26-000017` |
| forward | `0001493152-26-042291` | `0001493152-26-035145` |
| forward | `0001493152-26-042523` | `0001493152-26-035149` |
| forward | `0002143027-26-000010` (13F-HR/A) | `0002143027-26-000004` |
| forward | `0002146534-26-000002` (D/A) | `0002146534-26-000001` |
| forward | `0002147707-26-000003` | `0002147707-26-000002` |
| reverse | `0000892251-26-000099` (4/A) | `0000892251-26-000081` |
| reverse | `0001628280-26-051492` (4/A) | `0001628280-26-047904` |
| reverse | `0002065248-26-000003` (D/A) | `0002065248-26-000002` |
| reverse | `0002135638-26-000005` (D/A) | `0001840735-26-000021` |

That is 10 forward pairs, 4 reverse pairs and no other pair. The forward case rests on the live root, not only on the
fixture test (spec 5.5).

## Rebuild

`rebuild --zip "$ZIP"` exited 0 with 19 lines, all `equal`: the 11 Stage 3 tables, then `stage4 partners`,
`stage4 fetches`, `stage4 filings`, `stage4 parties`, `stage4 documents`, `stage4 ownership`,
`stage4 ownership_status` and `stage4 links`. So the Stage 4 commit moves no Stage 3 value, and the Stage 4 tables
re-derive from the inputs (C12).

## Manifest

- `manifest --set stage4` wrote `manifests/stage4@42fb313956e0.json`, SHA-256
  `3fd4e80679d16d15654aa1c02604334b45db999750ab9a10495905e949e40fae`. The name ends with the run commit's first 12
  characters.
- It lists 8 outputs (the files of `stage4/tables/`) and 21 inputs: 20 `submission` files of `stage4/bytes/` and the
  `ledger` `stage4/fetch-log.jsonl`.
- `builds_on` is `manifests/tables@c36aa2cf5571.json`, SHA-256
  `a9a1e8339ce2608c1e876ed0875026e1956dd2b9ca2563f9b625cfe282a64dc6`.

## Verify

- `verify` on `stage4@42fb313956e0.json` exited 0: `seed: 20261119`, `files: ok`, 6 `binding … ok` lines
  (`filings`, `parties`, `documents`, `ownership`, `links`, `fetches`), `rederive partners: ok, 20 rows` and 5
  `rederive … ok, 20 rows` lines.
- `verify` on `tables@c36aa2cf5571.json` exited 0 with the Stage 3 lines, as in Step 1.

## As-of

`asof --at <date>` at the seven dates of spec 5.9. Each answer named both manifests:
`tables@c36aa2cf5571.json` (`a9a1e833…`) and `stage4@42fb313956e0.json` (`3fd4e806…`). The counts read
"rows (sample, partner, index)":

| `--at` (end of day, New York) | `index` | `filings` | `parties` | `documents` | `facts` | `ownership` | `links` |
|---|---|---|---|---|---|---|---|
| 2026-06-30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2026-07-31 | 277 (267, 10, 0) | 178 (172, 6) | 281 (271, 10) | 1,382 (1,376, 6) | 8,549 | 2,622 (2,614, 8) | 12 (10, 2) |
| 2026-08-14 | 453 (440, 13, 0) | 297 (289, 8) | 458 (445, 13) | 2,802 (2,785, 17) | 23,085 | 6,404 (6,264, 140) | 20 (16, 4) |
| 2026-08-27 | 550 (532, 18, 0) | 365 (354, 11) | 558 (539, 19) | 3,944 (3,922, 22) | 34,134 | 6,634 (6,398, 236) | 30 (23, 7) |
| 2026-09-30 | 775 (740, 35, 0) | 520 (500, 20) | 793 (757, 36) | 5,793 (5,756, 37) | 45,358 | 7,105 (6,847, 258) | 43 (27, 16) |
| 2026-10-31 | 302,499 (740, 35, 301,724) | 520 (500, 20) | 793 (757, 36) | 5,793 (5,756, 37) | 45,358 | 7,105 (6,847, 258) | 43 (27, 16) |
| 2026-11-19 | 302,499 (740, 35, 301,724) | 520 (500, 20) | 793 (757, 36) | 5,793 (5,756, 37) | 45,358 | 7,105 (6,847, 258) | 43 (27, 16) |

- Through 2026-09-30, `index` has at most 775 rows, with `index 0`. The 301,724 rows of filings that we do not hold
  join at the index file's `Last-Modified` time, 2026-10-31T07:50:09Z, so they first answer at 2026-10-31.
- `facts` answers only from `sample`, because no partner is a 10-K or 10-Q.
- By 2026-09-30 every held filing answers. No held filing has a `known_from` after the end of the quarter.

The pair check ran `asof --at <instant> --table filings` for each of the 14 confirmed pairs, at three instants:
1 µs before the earlier `known_from`, half-way between the two, and the later `known_from`. Every pair answered
neither, then the original only, then both. In every pair the original answers first. No pair has its amendment
answer first, and no pair has two equal `known_from` values, so every pair had a middle instant.

| Pair (amendment amends original) | Amendment `known_from` | Original `known_from` |
|---|---|---|
| `0000892251-26-000099` amends `0000892251-26-000081` | 2026-07-13T20:43:22Z | 2026-07-06T20:20:18Z |
| `0000902664-26-003894` amends `0000902664-26-003832` | 2026-09-22T11:30:34Z | 2026-09-16T12:57:05Z |
| `0000902664-26-003970` amends `0000902664-26-003832` | 2026-09-29T13:04:23Z | 2026-09-16T12:57:05Z |
| `0000912282-26-001155` amends `0000912282-26-000961` | 2026-08-24T21:02:44Z | 2026-07-10T21:35:51Z |
| `0001119032-26-000009` amends `0001119032-26-000007` | 2026-08-21T18:47:56Z | 2026-08-17T14:19:04Z |
| `0001361570-26-000019` amends `0001361570-26-000017` | 2026-09-09T14:48:39Z | 2026-09-02T14:28:48Z |
| `0001493152-26-042291` amends `0001493152-26-035145` | 2026-09-11T10:24:00Z | 2026-07-29T17:27:42Z |
| `0001493152-26-042523` amends `0001493152-26-035149` | 2026-09-14T15:17:32Z | 2026-07-29T17:32:53Z |
| `0001628280-26-051492` amends `0001628280-26-047904` | 2026-07-31T22:23:33Z | 2026-07-10T20:57:15Z |
| `0002065248-26-000003` amends `0002065248-26-000002` | 2026-09-02T18:23:27Z | 2026-07-06T18:12:28Z |
| `0002135638-26-000005` amends `0001840735-26-000021` | 2026-08-07T10:04:33Z | 2026-07-30T10:03:49Z |
| `0002143027-26-000010` amends `0002143027-26-000004` | 2026-08-07T16:46:01Z | 2026-08-07T16:05:08Z |
| `0002146534-26-000002` amends `0002146534-26-000001` | 2026-09-24T14:27:01Z | 2026-08-28T10:00:51Z |
| `0002147707-26-000003` amends `0002147707-26-000002` | 2026-08-18T20:06:10Z | 2026-08-18T17:34:47Z |

## Report

The `## Stage 4` section of `report`, as printed:

```text
- partners: 20 distinct, 20 rows
- partners by original_previous_accession: 2
- partners by original_date_issuer_owner: 2
- partners by candidate_amendment: 16
- fetch ok: 20
- Stage 4 requests: 20 of 30
- Stage 4 wire bytes: 1578979 of 50000000
- links: 43
- links by previous_accession: 25
- links by original_date_issuer_owner: 4
- links by filer_period: 3
- links by none_declared: 11
- original held in sample: 10
- original held in partner: 4
- original not held: 29
- forward pairs: 10
- reverse pairs: 4
- other pairs: 0
- pairs whose amendment answers first: 0
- pairs with equal known_from: 0
- held filings: 520
- known_from before public_at: 0
- no public_at: 0
```

The sub-lines that name each pair are left out here. The pair table above lists the same pairs. Versions lists the 8
Stage 4 tables, each at code `42fb313956e0`, and `- stage4 tables made at 42fb313956e0: 8`.

## Inputs unchanged

The same script took a fingerprint before the run (Step 1) and after it (Step 10): the line count and SHA-256 of both
ledgers, the digest over `bytes/`, the SHA-256 of each file of `tables/`, of the three Stage 3 manifests and of
`master.zip`. The two fingerprints are equal. Stage 4 changed no frozen file.

## Measured cost

- SEC requests: 20. Wire bytes: 1,578,979.
- Wall time, from the 58 run lines of `runs.jsonl` at the run commit: `verify` 10.06 s (3 runs), `partners` 2.60 s,
  `fetch-partners` 9.24 s, `partner-tables` 2.62 s, `rebuild` 13.97 s, `manifest` 0.02 s, `asof` 6.60 s (49 runs, about
  0.13 s each) and `report` 0.25 s. The sum is 45.4 s. It does not include `uv` start-up.
- Disk (`du -sh`): `stage4/` 2.8 MB, of which `bytes/` 2.7 MB, `tables/` 96 KB and `fetch-log.jsonl` 16 KB. The
  `stage4` manifest is 8 KB.

## Problems found and fixed

The live run found no problem. Every step gave its expected result at the first commit that was run. The reviews
found the items below, and fix rounds closed them before the run:

- Task 7 review: no test reached the SHA-256 refusal of `asof`. Each test that changed a table file tripped an earlier
  check (the stamp read or the size), so a version without the SHA-256 comparison would have passed. A test now
  changes one letter of a stored value at the same length and expects the SHA-256 refusal.
- Task 8 review: no test changed a Stage 4 output file after the manifest, so a part 1 that checked the inputs only
  would have passed. Two tests now change `links.parquet` (a new size) and `partners.parquet` (the same size, a new
  hash).
- Task 10 self-review: the report's first pair filter counted a link to an original that the index lists and we do
  not hold, and printed a false `other pairs: 1`. The filter now needs `original_held_in`, with a test.

The plan had two small gaps, ruled in execution:

- Task 1: `tests/test_manifest.py` listed `sorted(TABLE_FORMATS)` as the `tables` files. The two new formats would have
  added `partners` and `links` to that list. It now reads `sorted(STAGE3_TABLES)`, the same 11 files.
- Task 10: the plan's scratch layout for `rebuild` would have broken two existing tests that pin the scratch folder.
  The scratch keeps its old `tables` folder and adds `stage4/` beside the tables.

Points that the reviews raised and the plan does not ask for. The run does not change for them:

- A hard kill during `fetch-partners` leaves a request with no response, which counts as 256 MiB. The next run then
  exits 5 before it reaches the leftover `.part` file. So Review Focus 3's removal of the `.part` file happens only
  after the owner sets more budget. Spec section 3 stops the run for the owner at that point.
- `asof` finds the `stage4` manifest by the commit stamped in the Stage 4 tables. A commit that lands between
  `partner-tables` and `manifest --set stage4` makes `asof` refuse and name the missing path. It never gives a wrong
  answer. Stage 3's manifest naming works the same way.
- The client keeps a wire-byte margin, so a reply that would leave less than that margin is discarded and its bytes
  count. It cannot bind at 1.6 MB of 50 MB.
- The Codex second opinion of the final review was skipped at the owner's word.

## Exit check

Spec section 7:

| Roadmap Exit part | Evidence | Result |
|---|---|---|
| For the 2026Q3 sample, an as-of query for any date returns only what was public by that date | The cutoff rule (5.1) and its tests (inclusive cutoff, both clock changes, a failed partner). The report's `known_from before public_at: 0` over all 520 held filings. The `asof` counts at the seven dates | Met |
| Each answer traces to its manifest and its source bytes | Each `asof` answer names both manifests by SHA-256. `asof` refuses a changed table file (tests, including a same-length change). `verify` exit 0 on the `stage4` and `tables` manifests: part 2 binds every row's source hash to a listed file | Met |
| Where a sampled filing has an amendment, the original and the amendment each answer at their own dates | 14 confirmed pairs on the live root: 10 forward and 4 reverse. Each pair answered neither, then the original only, then both. The 23 sampled amendments whose original is not held each keep their `link_problem` or `none_declared` | Met |

Anti-goal checks (spec section 2):

- No answer holds a record whose `known_from` is after `T`: `asof` keeps a row only when `known_from <= T`, the
  tests pin the cutoff, and the pair check shows it on the live root. No held filing has a `known_from` before its
  `public_at` (the report's check, 0).
- Every link rests on a value that the amendment's bytes declare. A `none_declared` row has no original, whatever the
  index lists.
- No amendment hides, drops or changes a record of its original. `asof` keeps every stored column and adds only
  `known_from` and `held_in` (tests). `rebuild` shows every table `equal`.
- The partner fetch sent 20 requests and received 1,578,979 wire bytes. No other SEC client ran. It fetched only the
  20 accessions of the partner list.
- Stage 4 changed no frozen file (Inputs unchanged). It did not touch `data/`, `backups/` or tag
  `ingest-parked-2026-11-16`, which it only read for the User-Agent.
- `asof` refused no live answer and wrote only its `runs.jsonl` lines (49 lines).
- No stamp, manifest or `known_from` takes a value from the clock. `known_from` comes from `last_modified_at`, else
  `fetched_at`. Only `runs.jsonl` keeps run times.
