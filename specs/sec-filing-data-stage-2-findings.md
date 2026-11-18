# sec-filing-data Stage 2 findings

This file is the evidence record of Stage 2 of the [sec-filing-data roadmap](sec-filing-data-roadmap.md).
[Plan 11](plans/11-sec-filing-data-stage-2-provenance-and-timing.md) implemented it, against the
[Stage 2 spec](sec-filing-data-stage-2-provenance-and-timing.md). Under the lighter process (spec section 3),
this file is the only evidence record. It records the results of the live run, each problem found and fixed,
and the measured cost.

## Run record

- Output root: `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`. It is the Stage 1 root, in the main
  checkout and git-ignored.
- Code: branch `claude/sec-filing-stage-2-exec-d01d8b`, run from the working tree at commit `140062a`
  (the last code commit of Tasks 1 to 8). Plan 11 Tasks 1 to 8 had 324 passing tests at that commit
  (the baseline was 222). The final whole-branch review then led to two small fixes (commits `d683628` and
  `7985dff`, 327 tests). They do not touch a path that the live run used, except one added line in the
  report's Times section. `report` was run again on the live root at the final commit, and its other
  sections were identical.
- Date: the run took place on 2026-11-18.
- Input: the same `master.zip` that Stage 1 read, in place, under `data/objects/raw/` in the main checkout.
  `index` checked its size and SHA-256 (`526d2dbf…`) before it parsed.
- User-Agent: `sec.user_agent` from `conf/sec-edgar.json`, passed in `SEC_USER_AGENT`. The value is not
  copied here.
- Before the run: no other SEC client was running, and `filing-data/` was git-ignored. The Stage 1 ledger had
  1,006 lines (SHA-256 `c348d7d4…`). One digest over the files of `bytes/` was `c854e7e5…`.
- The Stage 1 tables were copied once to `tables-stage1/` (10 Parquet files) before any step changed a table.

## SEC documentation (V7, V8 and the time zone)

Read on 2026-11-17, and repeated here from spec section 4.

- **Filing date (Rule 13 of Regulation S-T, 17 CFR 232.13, eCFR, current to 2026-11-13).** A filing whose
  transmission starts at or before 5:30 p.m. Eastern time is filed that business day. One that starts later is
  filed the next business day (232.13(a)(2)). Forms 3, 4, 5 and 144 and Schedules 13D, 13G and 14N keep the same
  day until 10 p.m. (232.13(a)(4)). Registration statements under Rule 462(b) do too (232.13(a)(3)). The cutoff
  applies to the start of transmission, not to acceptance. So acceptance alone cannot place a filing on either
  side of 5:30 p.m., and `FILED AS OF DATE` is the authority.
  <https://www.ecfr.gov/current/title-17/chapter-II/part-232/subpart-A/section-232.13>
- **V8, dissemination of a late filing (SEC, "Determine the Status of My Filing", last updated 2024-10-31).**
  EDGAR operates from 6:00 a.m. to 10:00 p.m. ET on business days. Most submissions that start after 5:30 p.m. ET
  get a filing date of 6:00 a.m. ET the next business day, and EDGAR does not disseminate them until that day. The
  10 p.m. form types are disseminated until 10 p.m. on the day sent. Answer: the next business day, from
  6:00 a.m. ET. <https://www.sec.gov/page/edgar-how-do-i-determine-status-my-filing>
- **V7, `<PRIVATE-TO-PUBLIC>` (EDGAR PDS Technical Specification, draft version 2.0, March 2025).** The tag
  "identifies an SEC-approved private-to-public document dissemination". It is present only in a `*.pr`
  dissemination. Private documents are held at the SEC, and the SEC releases some of them later, at its own
  discretion. Answer: a tagged submission became public at a later SEC release. Its header does not give that
  time, and its acceptance time is not its public time.
  <https://www.sec.gov/files/edgar/pds_dissemination_spec.pdf>
- **Time zone.** The same specification gives the control block's acceptance time as "(EST)". The data shows New
  York local time, which is EDT in summer. Read as EDT, each of the 500 sampled acceptances comes 12 s or more
  before its own `Last-Modified`. Read as fixed EST, each summer acceptance would come about 1 hour after its own
  `Last-Modified`, which cannot happen. So the conversion uses `America/New_York`. The live run agrees: all 500
  gaps are 12 s or more.

## Times

The report's Times section, read on the live root after the Stage 2 steps:

- Rule counts: `acceptance` 477, `next_opening` 23, `private_to_public` 0, `no_acceptance` 0. This equals the
  spec's expected result. The 23 `next_opening` filings are the 22 filings whose `FILED AS OF DATE` is later
  than their acceptance date, and `EFFECT` `9999999995-26-002992`.
- Filings with a null `last_modified_at`: 0.
- Gap from `public_at` to `last_modified_at`: least 12 s, median 27 s, largest 1,102,799 s. For 499 of the 500
  filings the gap is 12 s to 432 s. The largest gap belongs to one 10-Q (below).
- Filings with a gap above 1 hour: 1, `0001836875-26-000073`.
- Filings with `public_at` after `last_modified_at`: 0.
- Filings with `public_at` before `accepted_at`: 0 (an anti-goal).
- Filings with an unreadable `filed_as_of_date`: 0. This line was added after the final review (see "Problems
  found and fixed") and read on the live root at the final commit.
- `EFFECT` `9999999995-26-002992`: `public_rule` `next_opening`, `public_at` 2026-09-18 10:00:00 UTC
  (06:00 ET), gap 186 s. This is the value that the spec's rule predicts.

**The 10-Q `0001836875-26-000073`.** It was accepted at 17:04:31 ET on 2026-08-14 (21:04:31 UTC). Its
`FILED AS OF DATE` and its `DATE AS OF CHANGE` are both `20260814`. Its stored copy has `Last-Modified`
2026-08-27 15:24:30 UTC. So the archive copy changed 13 days after acceptance, and nothing in its header shows
the change. `last_modified_at` is therefore a bound that the copy existed by then. It does not say that the
filing became public then, and it cannot say that the first public copy equalled the stored copy.

## Provenance

The report's Provenance section reads 0 for each records table, in both counts (rows with a null `source_url`
or `source_sha256`, and rows of `ok` filings with a null `accepted_at` or `fetched_at`):

| Table | Rows with null source | Rows of `ok` filings with null time |
|---|---|---|
| `index` | 0 | 0 |
| `filings` | 0 | 0 |
| `parties` | 0 | 0 |
| `documents` | 0 | 0 |
| `facts` (45,358 rows) | 0 | 0 |
| `ownership` (6,847 rows) | 0 | 0 |

`index rows with filing times` is 740. These are the index rows of the 500 sampled accessions. The other 301,759
index rows have null filing times, as spec section 2 says. `index` was re-run once, before `envelopes`, as plan
Task 9 Step 4 orders. A later `index` run alone would reset these 740 rows to null. The Provenance section would
show that loss.

## V6 refetch

- Command: `refetch --accession 9999999995-26-002992`, once. Exit 0. Output: `9999999995-26-002992: ok` and
  `stage 2 requests: 1 of 20`. The Stage 2 ledger holds 2 lines (one request, one response with status 200 and
  881 wire bytes). The copy is `stage2/refetch/9999999995-26-002992.txt`.
- SHA-256, Stage 1 copy: `740252a6178e54e6121c7701084949adabb113f5d002d00814ca9ec098f431f3`.
- SHA-256, refetch: `740252a6178e54e6121c7701084949adabb113f5d002d00814ca9ec098f431f3`. They are equal.
- `Last-Modified`, Stage 1 copy: 2026-09-18 10:03:06 UTC. `Last-Modified`, refetch: 2026-09-18 10:03:06 UTC.
  They are equal. The refetch was taken on 2026-11-18 at 19:41:54 UTC.
- `refetches` holds 1 row. Its `changed_header_fields` and `changed_documents` are null, because the SHA-256
  values are equal.
- **What this refetch shows, and what it cannot show (spec 6.3, D6).** Stage 1 fetched this copy on 2026-11-17.
  Its `Last-Modified` is 2026-09-18 at 06:03 ET, the next opening after its acceptance and on its
  `DATE AS OF CHANGE`. The refetch compares two copies that were both taken after that date. So equal hashes show
  only that the copy did not change between 2026-11-17 and 2026-11-18. They do not show that a correction leaves
  the copy unchanged. Only a copy fetched before a correction, and another after it, can answer that question.
  It goes back to `specs/deferred_items.md` (spec section 11).

## Stage 1 column check

`check-stage1` compared the Stage 1 columns of each re-written table with `tables-stage1`, row for row. Exit 0.
10 lines, each `equal`: `documents`, `facts`, `facts_status`, `fetches`, `filings`, `index`, `ownership`,
`ownership_status`, `parties`, `sample`. So Stage 2 changed no as-filed value (anti-goal 1).

## Rebuild

`rebuild --out /Users/lowell/Projects/sec-edgar/filing-data/2026Q3 --zip <master.zip>` re-created every table in a
temporary folder and compared it with the live table. Exit 0. 11 lines, each `equal`: `index`, `sample`,
`fetches`, `filings`, `parties`, `documents`, `facts`, `facts_status`, `ownership`, `ownership_status`,
`refetches`. It loaded no module that imports `requests`, and it sent no request.

After the rebuild, the Stage 1 ledger still had 1,006 lines with SHA-256 `c348d7d4…`, the Stage 2 ledger still
had 2 lines, and the digest over `bytes/` was still `c854e7e5…`. All three equal their values before the refetch.
The rebuild added one line to `runs.jsonl` and nothing else.

## Measured cost

- SEC requests: 1 of 20 (Stage 2 limit). Wire bytes: 881 of 50,000,000. No attempt failed or retried.
- Wall time, from `runs.jsonl`: `refetch` 0.26 s, `index` 0.91 s, `envelopes` 3.49 s, `facts` 1.73 s,
  `ownership` 0.69 s, `compare-refetches` 0.01 s, `report` 0.35 s, `check-stage1` 0.27 s, `rebuild` 21.3 s.
- Disk: `tables/` 14.9 MB (Stage 1: 14.6 MB in `tables-stage1/`), `stage2/` 8 KB. `bytes/` stays at 1.1 GB, and
  Stage 2 added nothing to it.

## Problems found and fixed

The live run found no problem. The task reviews found the first three items, and fix rounds closed them
before the run. The final whole-branch review found the next two, and a fix wave closed them after the run:

- Task 3 (`envelopes`): no test separated `last_modified_at` on an `ok` filing that does not parse from the
  parsed case, and no test pinned the `public_rule` values `private_to_public` and `no_acceptance`. Two tests
  were added.
- Task 6 (`refetch`): the CLI treated every `ValueError` as a refusal that writes nothing (exit 2). An error after
  a request record exists would have looked like an unknown-accession refusal, although the accession was then
  refetched for good under the once-only rule. Only the new `UnknownAccession` error is a refusal now.
- Task 8 (`check-stage1`): an empty `tables-stage1` folder passed with no line, and a missing frozen column
  crashed with a traceback. The first now exits 1 with one line. The second gives a line that names the columns.
- Final review, `refetch`: after an interrupted refetch of an accession, a re-run for the same accession skipped
  it and exited 0. Spec 6.3 says that later refetches are refused, so the re-run now exits 5 before it does
  anything.
- Final review, `report`: an unreadable but non-null `FILED AS OF DATE` fell back to `accepted_at` alone with no
  sign in the report. The Times section now counts these filings (0 on the live root).

A second review, by Codex, raised three more points. The owner's plan and the spec do not ask for them, so the
run does not change for them:

- The `refetches` table takes both SHA-256 values from the ledgers and does not hash the stored files again.
  This is what plan C8 says. Byte integrity of the kept files is a Stage 3 concern.
- `report` raises an error on a Stage 1 table that the Stage 2 steps have not yet rewritten. The live root was
  rewritten before `report` ran, so the case does not occur.
- A `refetch` of an unknown accession still writes one `runs.jsonl` line, because the command runs inside
  `record_step`. It sends no request and creates no `stage2/` folder.

## Exit check

Spec section 8:

| Roadmap Exit part | Evidence | Result |
|---|---|---|
| Each record of O1–O4 names its source, its raw-byte SHA-256 and its times | Provenance section: 0 null sources in the records tables, and the times per rule (477 `acceptance`, 23 `next_opening`) | Met |
| A rebuild from the kept bytes reproduces the tables with no SEC request | `rebuild` exit 0, 11 tables `equal`, and both ledgers' line counts unchanged by it (1,006 and 2) | Met |
| The V6 refetch meets its Done-when | The `refetches` row of `9999999995-26-002992`, with both SHA-256 values (equal) and the limit of spec 6.3 | Met |
| The V7 and V8 checks meet their Done-when | Section "SEC documentation" above, repeated from spec section 4 | Met |
| Each live request is inside the Stage 2 budget | Stage 2 ledger: 1 request and 881 wire bytes, against 20 and 50,000,000 | Met |

Anti-goal checks (spec section 2):

- No as-filed value changed: `check-stage1` gave 10 lines `equal`.
- `public_at` before `accepted_at`: 0.
- `Last-Modified` is only the `last_modified_at` column, and the rule time is only `public_at` with its
  `public_rule`. Neither is labeled as the other.
- The rebuild sent no request and loaded no module that imports `requests`.
- The Stage 1 ledger (1,006 lines, SHA-256 `c348d7d4…`) and the Stage 1 byte files (digest `c854e7e5…`) are
  unchanged.
