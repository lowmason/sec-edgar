# Stage 4: As-of views — Design Spec

**Status:** Draft for owner review, 2026-11-19.
**Project:** `/Users/lowell/Projects/sec-edgar`, package `packages/sec-filing-data`.
**Roadmap:** [sec-filing-data roadmap](sec-filing-data-roadmap.md), Stage 4, the last stage.
**Inputs:** Stage 3 as built: [plan 13](plans/completed/13-sec-filing-data-stage-3-manifests-and-pinning.md) (its
Handoff section), the [Stage 3 findings](sec-filing-data-stage-3-findings.md) and the
[Stage 3 spec](completed/sec-filing-data-stage-3-manifests-and-pinning.md). Stage 2's times as built:
[plan 11](plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md), Handoff section. The live root
`/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`: `tables/`, `bytes/`, both ledgers and the manifest
`manifests/tables@c36aa2cf5571.json` (SHA-256 `a9a1e833…`, recorded in the Stage 3 findings). Background only: the
parked platform spec's time and amendment rules, R9–R13 and R22–R24 with V14 and V15
(`specs/completed/sec-filing-platform.md`), which two held items of `specs/deferred_items.md` carry. Stage 4 does not
tick, move or retire them.

## 1. Purpose

The owner's reason for this stage, in the owner's words: "Point-in-time awareness."

Stages 2 and 3 gave each record of O1–O4 its source, its times and a hash-bound trace to its bytes. No part of the
code answers the question that those times exist for: what was public on a given date?

Stage 4 answers it. For any time `T`, an as-of query returns each filing, party, document, fact, ownership record
and index row of the 2026Q3 sample that was public by `T`. The query never returns a record early, and each answer
names the manifests and the source bytes that it rests on.

Amendments are the part of the question that the sample cannot show alone. 27 sampled filings are amendments, but
none of their originals is in the sample. For 13 sampled filings of forms whose amendments declare their original,
the 2026Q3 index lists a later amendment by the same filers. Stage 4 fetches these in-quarter partners, 20 filings, and links each amendment to its original
through what the amendment's own bytes declare (D1). An original and its amendment then each answer at their own
times.

## 2. Scope

**Goals**

- G1. Each held record has a `known_from` time: the latest time by which we can prove that it was public (5.1).
- G2. An offline step writes the list of 20 partner filings, and the rule that chose each one, before any request
  (5.2).
- G3. A partner fetch gets each partner's complete submission file, inside the owner's Stage 4 budget (D2, 5.3).
- G4. The partners' records go to `ROOT/stage4/tables/`, made by the same parse code as the sample's records (5.4).
- G5. A `links` table gives each held amendment its original, the rule that found it and the values that the
  amendment declared (5.5).
- G6. A read-only `asof` query returns every record with `known_from` at or before `T`, from both table sets. It
  first checks each table file that it reads against its manifest (5.6).
- G7. A `stage4` manifest lists every Stage 4 output and input, and names the Stage 3 `tables` manifest that it
  builds on. `verify` checks it in three parts, as it checks `tables` (5.7).
- G8. The Stage 4 commit still reproduces the Stage 3 tables: `rebuild` gives 11 lines `equal` (5.8).

**Non-goals**

- A current-state view. An amendment never replaces or hides its original. The rules that decide whether an
  amendment supersedes its original (platform R23 for 13F, R24 for Form 4) stay with the held parked item. The
  `links` table keeps the declared amendment type and number, so a later stage can apply them.
- Partners of partners. The partner rule goes one hop from a sampled filing.
- Originals in other quarters (15 of the sampled amendments name one), amendments filed after 2026Q3, and
  amendments listed under other CIKs. The roadmap leaves other quarters out (owner, 2026-11-16).
- Links for forms that declare no original in their bytes: 8-K/A, 6-K/A, N-CEN/A, C/A, F-1/A, NPORT-P/A and
  SC TO-T/A. They answer at their own times, with no link.
- Filing times for index rows of filings that we do not hold. Such a row answers from the index file's own
  `Last-Modified` time (5.1).
- A view on this project's own clock: what a run at `T` could read (the platform's Known^plat). The view is on the
  SEC's clock only.
- XBRL facts for partners. No partner form is a 10-K or 10-Q, so `stage4/tables/` has no facts tables.
- Whether an archive copy changes after a correction. The item stays deferred: Stage 4 fetches filings weeks after
  their filing day, so its `Revisit if` does not fire.
- Feed archives, SEC reference data and inline XBRL. Their deferred items' `Revisit if` conditions do not fire.

**Anti-goals.** Stage 4 fails, even if every check passes, when:

- an answer for `T` holds a record whose `known_from` is after `T`, or a held filing has a `known_from` before its
  `public_at`.
- a link rests on the index match alone. A link needs a value that the amendment's bytes declare.
- an amendment hides, drops or changes a record of its original, or an answer changes a stored value.
- the partner fetch sends more than 30 requests, receives more than 50,000,000 wire bytes, runs while another SEC
  client runs, or fetches a filing that is not on the partner list.
- it changes a file of `tables/`, `tables-stage1/`, `tables-stage2/`, `bytes/`, `stage2/`, the Stage 1 or Stage 2
  ledger, a Stage 3 manifest or the input copy, or touches `data/`, `backups/` or tag `ingest-parked-2026-11-16`.
- `asof` answers from a table file whose SHA-256 differs from its manifest, or writes any file except its
  `runs.jsonl` line.
- a stamp, a manifest or a `known_from` takes a value from the clock.

## 3. Constraints

- Stage 3's constraints carry over: Python 3.14 in the uv workspace, `requests` and `pyarrow` as the only runtime
  dependencies, fixture and live data kept apart in tests, and socket calls blocked in tests. Only `client.py` and
  `fetch.py` import `requests`. Each new module joins the name set that
  `test_offline_modules_never_import_requests` asserts.
- **Process.** The lighter process with Stage 3's clean-tree rule (roadmap, Choices made). A command that writes
  under the root refuses to run when the pinned paths have an uncommitted change, and exits 3. A fix needs a commit
  but no release. `specs/sec-filing-data-stage-4-findings.md` is the only evidence record.
- **SEC budget for Stage 4 (owner, D2).** At most 30 requests and 50,000,000 wire bytes, at most 3 requests a
  second, and no other SEC client running. Every attempt counts, retries included. The fetch counts in its own
  ledger, `ROOT/stage4/fetch-log.jsonl`. The Stage 1 and Stage 2 ledgers stay as they are. Planned use: 20 requests.
  The Stage 1 client rules hold: a declared User-Agent from `SEC_USER_AGENT`, at least 0.34 s between request
  starts, at most 5 attempts, timeouts and the 256 MiB response guard. As in Stages 1 and 2, a request with no
  response record counts as 256 MiB of wire bytes. So a hard kill during the fetch spends the budget. The run then
  stops, and only the owner can set more.
- **One root.** `stage4/` is a folder of the one root, like `stage2/`. Every command takes the same `--out`, appends
  to the one `runs.jsonl` and takes the one `fetch.lock`. So the deferred item about a second root
  (`specs/deferred_items.md`, section `11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`, "Command
  robustness") does not fire.
- **No write outside a command.** `asof` and its Python function write no table. So the deferred item about
  Python-level writes (section `13-sec-filing-data-stage-3-manifests-and-pinning — 2026-11-19`) does not fire.
- **Frozen.** Plan 13's frozen set still holds, and Stage 4 adds the files that Stage 3 made: nothing changes a byte
  file, a ledger line, `stage2/refetch/`, `tables-stage1/`, `tables-stage2/`, `tables/`, a Stage 3 manifest or the
  input copy. The live run writes only `ROOT/stage4/`, `ROOT/manifests/stage4@<commit12>.json` and `runs.jsonl`
  lines.
- `--out` repeats the absolute root, because `fetches.path` stores paths under it.
- The plan's pull request merges with a merge commit, so the commit that the Stage 4 tables name stays reachable
  from `main`.
- No committed line holds the User-Agent or the contact address.

## 4. Approaches

The owner chose A (D3). The amendment reach was a separate choice (D1).

- **A. A `stage4/` folder beside the Stage 3 tables (chosen).** The partners' bytes, ledger and tables go to
  `ROOT/stage4/`. `tables/` and `tables@c36aa2cf5571.json` stay as they are, and a new `stage4` manifest names the
  Stage 3 manifest by its SHA-256. An answer reads two table sets, each made at one commit and traced to its own
  manifest. Cost: the steps learn to read a second list and a second bytes folder, and an answer joins two sets.
  The two code versions are sound only while the Stage 4 commit still reproduces `tables/`. So `rebuild` must give
  11 lines `equal` at the Stage 4 commit (G8).
- **B. One re-made set.** The partners join `tables/` as extra rows. `tables/` is frozen as `tables-stage3/` and
  re-made at the Stage 4 commit, under one new manifest. Gain: one set and one code version in each answer. Cost:
  most tables need a column that tells partners from the sample, so most format numbers go up. A third frozen copy
  of about 15 MB. The sample's tables no longer hold the sample alone.
- **C. Stored as-of tables.** Each record gets a stored `known_from`. Dropped: every record already carries
  `last_modified_at`, so the tables would only copy 45,358 facts and 302,499 index rows.

The amendment reach had four options (D1). A: link only pairs where both filings are sampled, which gives zero
real pairs. B: link to originals in the index with no fetch. Those have a filing date only, and the strict cutoff
would place each original after its amendment. C: fetch the partners inside 2026Q3 (chosen). D: also fetch the 15
originals in other quarters, which reopens the owner's quarter decision of 2026-11-16 and four deferred items.

## 5. Design

### 5.1 `known_from`: when a record is public

Stage 2 gave each filing two bounds. `public_at` is the earliest time that it could have been public, by rule.
`last_modified_at` is the `Last-Modified` time of the stored copy, by which time the bytes that we hold existed on
EDGAR. The as-of view reads the strict bound, so it never shows a record early.

- **A held filing.** `known_from` is its `last_modified_at`. When that is null, it is its `fetched_at`, because the
  bytes existed when we fetched them. (All 500 sampled filings have a `last_modified_at`.) A filing whose fetch is
  not `ok` has no `known_from`, and none of its rows answers.
- **A record of a held filing** (`parties`, `documents`, `facts`, `ownership`, `links`) takes its filing's
  `known_from`.
- **An index row** takes the `known_from` of its filing when we hold that filing, in the sample or in the partners.
  Every other index row takes `index_last_modified_at`, 2026-10-31T07:50:09Z: the index file listed the row by
  then.
- `public_at` and the other times stay on each row, unchanged. They never serve as the cutoff.
- **The cost.** The 10-Q `0001836875-26-000073` was accepted on 2026-08-14, and its copy was last modified on
  2026-08-27. It answers from 2026-08-27. The bytes that were public before that date are not the bytes we hold.

**The query time `T`.** A query takes one of these:

- an ISO 8601 instant with a UTC offset or `Z`. The query converts it to UTC.
- a date, `YYYY-MM-DD`. It means the end of that day in New York: 1 µs before 00:00 of the next day, in
  `America/New_York`. So "public by 2026-08-14" includes a filing known at 23:00 ET on 2026-08-14.

An instant with no offset is a usage error, because it names no clock. A record answers at `T` when its
`known_from` is at or before `T`.

### 5.2 The partner list

A new offline command, `partners --out ROOT`, writes `ROOT/stage4/tables/partners.parquet`. It reads the `tables`
set's `index` and `sample` tables and the bytes of the sampled amendments. It sends no request.

Three rules choose a partner. Each skips the sample's `repeated` stratum (form types joined with `;`), and none
chooses a sampled filing.

1. **`original_previous_accession`.** A sampled Schedule 13D/A, Schedule 13G/A or Form D/A names
   `previousAccessionNumber` in its XML. (In a schedule, the element is in `headerData`. In a Form D, it is in
   `typeOfFiling/newOrAmendment`.) The named accession is a partner when the 2026Q3 index lists it.
2. **`original_date_issuer_owner`.** A sampled Form 3/A, 4/A or 5/A gives `dateOfOriginalSubmission`, the
   `issuerCik` and each `rptOwnerCik`. The partner is the one index accession of the base form type (`4` for
   `4/A`) that was filed on that date and that the index lists under exactly those CIKs. Zero or several matches
   give no partner. This is the platform's R24 link.
3. **`candidate_amendment`.** A sampled filing has form type `SCHEDULE 13D`, `SCHEDULE 13G`, `SC 13D`, `SC 13G`,
   `D`, `3`, `4`, `5` or `13F-HR`. Each index accession of the same form type plus `/A` is a partner when the
   index lists it under exactly the same CIKs and its date filed is on or after the sampled filing's. Each of these
   forms declares its original in its bytes, so 5.5 confirms or rejects the link after the fetch.

"The CIKs of an accession" means the set of `cik` values over its index rows. The index lists an accession once for
each CIK and form type.

Each `partners` row has `accession_number`, `form_type`, `cik`, `company_name`, `date_filed`, `filename` and `url`,
taken as `sample` takes them from the index. It also has `rule` and `sampled_accession`, the sampled filing that
the rule started from. A partner that two rules or two sampled filings choose has one row for each. The fetch walks
the distinct accessions in accession order.

On the live root the rules give 20 partners (Appendix A): 2 by rule 1, 2 by rule 2 and 16 by rule 3. The 16
candidates are 12 Schedule 13D/A, 2 13F-HR/A, 1 Form 4/A and 1 Form D/A, for 13 sampled filings. One candidate,
Form 4/A `0001921640-26-000017`, has a lower accession number than its sampled Form 4 of the same day. It probably
amends an earlier filing, and its bytes will tell.

### 5.3 The partner fetch

A new command, `fetch-partners --out ROOT`, fetches each partner's complete submission file from its `url` into
`ROOT/stage4/bytes/<accession>.txt`.

- It refuses a tree that is not clean, and it needs `SEC_USER_AGENT`, as `fetch` does.
- It takes `ROOT/fetch.lock`, so no other client of this root runs. It counts in `stage4/fetch-log.jsonl` against a
  new `STAGE4_LIMITS` of 30 requests and 50,000,000 wire bytes. It returns 5 at once when the Stage 4 budget is
  already spent.
- It skips a partner whose bytes exist. A partner whose fetch failed is tried again by a later run, while budget
  remains, as `fetch` does.
- It returns 0 after the walk, 5 when the budget runs out and 6 when the SEC answers 403. Every exit writes the
  `stage4/tables/fetches` table, one row for each distinct partner.
- It writes nothing under `bytes/` and nothing to the Stage 1 or Stage 2 ledger.

### 5.4 The partner tables

An offline step writes the rest of `ROOT/stage4/tables/` from the partner bytes and the Stage 4 ledger: `fetches`
(the offline form, as `build-fetches` gives it), `filings`, `parties`, `documents`, `ownership` and
`ownership_status`. These tables have the same schemas and format numbers as their `tables/` namesakes. The parse
code is shared and unchanged: `filing_records`, `extract_ownership` and `ownership_rows`. The step reads `partners`
in place of `sample`, the Stage 4 bytes in place of `bytes/`, and the Stage 4 ledger for the `Last-Modified` times.

Each partner's `filings` row gets the Stage 2 times by the Stage 2 rule. Each partner record carries its source URL,
its source SHA-256 and the five filing times, as sampled records do. Schedule 13D/A, 13F-HR/A and Form 4 and 4/A
partners give ownership records. Form D and D/A partners give `filings`, `parties` and `documents` rows only.

### 5.5 The `links` table

The same step writes `ROOT/stage4/tables/links.parquet`: one row for each held filing whose form type has a part
that ends in `/A`. On the live root that is 27 sampled filings and 16 partners. Its first format number is 1.

| Column | Meaning |
|---|---|
| `accession_number`, `form_type` | The amendment |
| `held_in` | `sample` or `partner` |
| `link_rule` | `previous_accession`, `original_date_issuer_owner`, `filer_period` or `none_declared` |
| `declared_previous_accession` | `previousAccessionNumber` as filed, or null |
| `declared_original_date` | `dateOfOriginalSubmission` as filed, or null |
| `declared_period` | For a 13F-HR/A: `CONFORMED PERIOD OF REPORT` from the header, as filed, or null |
| `amendment_number`, `amendment_type` | `amendmentNo` and the 13F `amendmentType`, as filed, or null |
| `original_accession` | The original that the rule finds, or null |
| `original_held_in` | `sample`, `partner` or null when we do not hold the original |
| `link_problem` | Null, or why the rule found no original, for example "not in the 2026Q3 index" or "2 index matches: …" |
| `source_url`, `source_sha256`, `source_document` | The amendment's bytes, and the XML document that declared the values |
| the five filing times | The amendment's, as on its other records |

The rules, by form:

- **`previous_accession`** (Schedule 13D/A, 13G/A, Form D/A): the original is the named accession.
- **`original_date_issuer_owner`** (Form 3/A, 4/A, 5/A): rule 2 of 5.2, over the 2026Q3 index.
- **`filer_period`** (13F-HR/A): the original is the held 13F-HR of the same filer (the first `FILER` party) with
  the same `CONFORMED PERIOD OF REPORT`. This is the platform's R23 link. When no held 13F-HR matches, the link is
  null.
- **`none_declared`**: every other amendment, and any amendment whose bytes give none of these values.

An amendment is filed after its original. So when both are held and the rule finds an original whose `accepted_at`
is after the amendment's, that original is no link: `original_accession` stays null, and `link_problem` says why.
This can happen under rule 2, where the declared date matches a same-day filing (my call).

A Schedule 13D/A often names the amendment before it, not the first filing. So links can form a chain, for example
sampled 13D, partner 13D/A No. 1, partner 13D/A No. 2. The table holds one hop. A reader follows a chain by joining
`original_accession` to `accession_number`.

A **confirmed pair** is a `links` row whose amendment and original are both held. A candidate whose bytes name
another filing stays held, with its own link. It answers at its own time like every other held filing.

**Order in a pair.** Each filing of a pair answers at its own `known_from`. Usually the original answers first. But
EDGAR can rewrite a copy after acceptance, as it did for the 10-Q `0001836875-26-000073`. When it rewrote an
original's copy after its amendment's, the original's `known_from` is the later one, and the amendment answers
first. This is not an error, and no rule moves either time: the bytes of the original that we hold existed only from
their `Last-Modified` time. The report and the findings name each pair in this order (my call).

Expected for the 27 sampled amendments, from the live bytes: 2 Form D/A and 2 Form 4/A link to partners. 14 name an
original that is not in the 2026Q3 index. 1 Form 4/A has no index match for its declared date, 2026-04-16. The
13F-HR/A declares period 2021-12-31, and we hold no 13F-HR for it. 7 are `none_declared`.

### 5.6 The as-of query

A new module, `asof.py`, gives a function `answer(root, at)`. It returns the instant `at` in UTC, the manifests that
it used (set, path and SHA-256), and one Arrow table for each of `index`, `filings`, `parties`, `documents`,
`facts`, `ownership` and `links`.

- Each table holds the rows of `tables/<name>` and `stage4/tables/<name>` whose `known_from` is at or before `at`.
  `index` and `facts` come from `tables/` only, and `links` from `stage4/tables/` only.
- Each row keeps every stored column unchanged and gains two columns: `known_from`, and `held_in` (`sample`,
  `partner`, or `index` for an index row of a filing that we do not hold).
- **Manifest check first.** For each set, the function finds the manifest by the set name and the code version in
  the set's table stamps. It refuses when the files of a set name more than one version, when the manifest is
  missing, when a table file that it reads differs from its manifest entry in size, SHA-256 or stamp, or when the
  `stage4` manifest's `builds_on` SHA-256 differs from the `tables` manifest file. A refusal raises, and no partial
  answer comes back.
- It writes nothing.

A new command, `asof --out ROOT --at T [--table NAME]`, prints `T` in UTC, each manifest's path and SHA-256, and
for each table the number of rows that answer, by `held_in`. With `--table`, it also prints that table's rows as
JSON Lines, kept apart from the summary so that the rows can be piped. It runs inside `record_step`, writes nothing
else under the root, and never refuses for the tree state. It exits 0 on an answer, 1 on a refusal and 2 on a usage
error.

The trace from an answer to its bytes: the answer names both manifests by SHA-256. Each row keeps its
`source_sha256`, and `verify` part 2 binds every such hash to a listed input file (5.7).

### 5.7 The `stage4` manifest and `verify`

`manifest --out ROOT --set stage4` writes `ROOT/manifests/stage4@<commit12>.json`. It refuses when the file exists,
as Stage 3's sets do.

- `outputs`: each file under `stage4/tables/`, with its size, SHA-256, rows and stamp.
- `inputs`: each file under `stage4/bytes/` (kind `submission`), and `stage4/fetch-log.jsonl` (kind `ledger`).
- `builds_on`: the path and SHA-256 of the `tables` manifest that the Stage 4 tables read from. The sampled
  amendments' bytes and the `index` and `sample` tables are inputs of Stage 4 through that manifest, where they are
  already listed.

`verify --manifest stage4@….json` runs three parts, as for `tables`:

1. **Files.** Each listed file has its size and SHA-256. Each file under `stage4/tables/` and `stage4/bytes/` is
   listed. Each stamp equals its entry. The `builds_on` file has its listed SHA-256, and each `tables/` file and
   sampled byte file that Stage 4 reads equals its entry in that manifest.
2. **Binding.** Every source SHA-256 of `filings`, `parties`, `documents`, `ownership` and `links` is the SHA-256 of
   a listed input or, for a sampled amendment's `links` row, of a byte file that the `builds_on` manifest lists.
   Each `ok` row of the Stage 4 `fetches` has, at its `path`, the SHA-256 that its ledger line gives.
3. **Re-derive.** The whole `partners` table re-derives from the hashed `index` and `sample` tables and the hashed
   sampled bytes. `N` seeded rows of each of `filings`, `parties`, `documents`, `ownership` and `links` re-derive
   from the hashed bytes, as Stage 3's part 3 does.

`verify` on the `tables` manifest and on the frozen manifests works as before, and gives the Stage 3 results.

### 5.8 `rebuild` and `report`

- `rebuild` also re-creates the Stage 4 tables in its temporary folder, from the Stage 4 bytes and ledger, and
  compares them by value. With a `stage4/` folder present it prints 8 more lines. At the Stage 4 commit, all 19
  lines must be `equal`. The 11 Stage 3 lines show that the Stage 4 code does not move a Stage 3 value.
- `report` gains a Stage 4 section: the partners by rule, the partner fetch outcomes and the Stage 4 ledger use
  against its limits, the links by rule and by `original_held_in`, the number of confirmed pairs and the pairs whose
  amendment answers first, and the
  `known_from` check: for each held filing, `known_from` is at or after `public_at`. The Versions section covers the
  Stage 4 set too.

### 5.9 The live run

Each command runs from the plan's final code commit, with a clean tree. The final whole-branch review and its fixes
come before the run. `$ROOT` is `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`. `$ZIP` is
`/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip`.

1. **Preconditions.** The pinned paths are clean at the commit. No `sec-filing-data` command runs on the root.
   Record the line count and SHA-256 of both ledgers, one digest over `bytes/`, the SHA-256 of each `tables/` file,
   of each Stage 3 manifest and of `$ZIP`. `verify` on `tables@c36aa2cf5571.json` gives exit 0.
2. **Partners.** `partners`. Expected: 20 distinct partners, as in Appendix A. A different list stops the run.
3. **Fetch.** With `SEC_USER_AGENT` set, `fetch-partners`. Expected: 20 `ok`, about 20 requests and less than
   5 MB received.
4. **Partner tables and links.** The offline step of 5.4 and 5.5.
5. **Rebuild.** `rebuild --zip "$ZIP"`. Expected: 19 lines `equal`.
6. **Manifest.** `manifest --set stage4`.
7. **Verify.** `verify` on the `stage4` manifest (three parts) and on the `tables` manifest (three parts, as in
   Stage 3).
8. **As-of.** `asof` at the end of each of these dates: 2026-06-30, 2026-07-31, 2026-08-14, 2026-08-27, 2026-09-30,
   2026-10-31 and 2026-11-19, with the counts recorded. For each confirmed pair, `asof --table filings` at three
   instants: 1 µs before the earlier `known_from`, between the two `known_from` values, and at the later
   `known_from`. Expected: neither, then the earlier filing only, then both. The findings name each pair whose
   amendment answers first (5.5). Where both have the same `known_from`, the middle instant does not exist, and the
   findings say so.
9. **Report.** The Stage 4 section shows every held filing with `known_from` at or after `public_at`.
10. **Inputs unchanged.** The ledgers, the `bytes/` digest, the `tables/` files, the Stage 3 manifests and `$ZIP`
    equal their step 1 values.
11. **Findings.** Write `specs/sec-filing-data-stage-4-findings.md` (section 7).

A result that differs is a problem to fix and record, under the lighter process. The fix is a commit, and the
offline steps (2, 4–10) run again at the new commit. The fetch is not repeated for a partner that has bytes. A fix
that would change a Stage 3 value is not a Stage 4 fix: the run stops, and the owner decides.

## 6. Verification

Offline tests come first and fail before the code exists (red, then green), as in Stages 1 to 3. They read only
fixtures and temporary folders.

- **`known_from`:** a filing with `last_modified_at` takes it. A filing with a null `last_modified_at` takes
  `fetched_at`. A filing that is not `ok` answers never. An index row of a held filing takes the filing's value,
  for a sampled and for a partner filing. Any other index row takes `index_last_modified_at`.
- **The query time:** a date reads as the end of that day in New York, in summer (EDT) and in winter (EST). An
  instant with an offset converts to UTC. An instant with no offset is a usage error.
- **The cutoff:** a record with `known_from` equal to `T` answers at `T` and not at `T` minus 1 µs. An answer keeps
  every stored value and adds only `known_from` and `held_in`.
- **The manifest check:** `answer` refuses when a byte of a table file changes, when the manifest is missing, when a
  set's files name two versions, and when the `builds_on` SHA-256 differs. `asof` writes nothing under the root
  except its `runs.jsonl` line. `asof` loads no module that imports `requests`.
- **Partner rules,** on a fixture index and fixture bytes: rule 1 with the named accession in the index, not in the
  index, and in the sample. Rule 2 with one, zero and two matches. Rule 3 with the same CIK set, a larger CIK set
  (no partner), an earlier date (no partner), the same date (a partner) and a sampled accession (no partner). The
  `repeated` stratum is skipped. A partner of a partner is not chosen.
- **The partner fetch,** with a fake session: it stops at 30 requests and at the wire-byte limit with exit 5. It
  returns 5 at once when the Stage 4 budget is spent. A held lock refuses. It skips a partner with bytes. It writes
  only `stage4/`. It refuses a tree that is not clean and runs without a User-Agent.
- **Links,** from fixture XML: each of the four rules, a chain through a partner, a 13F-HR/A with no held
  original, a Form 4/A with two index matches (`link_problem`), a found original accepted after its amendment (no
  link), and a `/A` filing with no XML document.
- **The pair:** a fixture original and its amendment answer neither, then the original only, then both, at the
  three instants of step 8. A second pair, whose original has the later `known_from`, answers neither, then the
  amendment only, then both.
- **Manifest and `verify`:** the `stage4` manifest lists every file of `stage4/tables/` and `stage4/bytes/`, and
  `builds_on`. It refuses to overwrite. `verify` gives exit 0 on an untouched fixture root. Each of these gives exit
  1 and names the file or row: a changed partner byte file, an unlisted file in `stage4/bytes/`, a changed
  `tables/index.parquet`, a changed `tables` manifest, a changed `links` value, and a changed `partners` row.
- **Rebuild:** the Stage 4 tables compare `equal` on a fixture root, and a changed Stage 4 table does not.
- **Formats:** `partners` and `links` have format number 1, pinned by schema fingerprints.
- The existing tests pass.

## 7. Exit evidence

| Roadmap Exit part | Evidence in `specs/sec-filing-data-stage-4-findings.md` |
|---|---|
| For the 2026Q3 sample, an as-of query for any date returns only what was public by that date | The cutoff rule (5.1) and its tests. The report's check that each held filing has `known_from` at or after `public_at`. The `asof` counts at the seven dates of step 8 |
| Each answer traces to its manifest and its source bytes | `asof` names both manifests by SHA-256, and refuses on a changed table file. `verify` exit 0 on the `stage4` and `tables` manifests: part 2 binds every row's source hash to a listed file |
| Where a sampled filing has an amendment, the original and the amendment each answer at their own dates | The `links` table on the live root: the count of confirmed pairs, and the three `asof` answers for each pair. The sampled amendments whose original is not held, each with its `link_problem` |

The findings also record the run record (root, commit, stamp), the partner list, the SEC use against the Stage 4
budget (requests and wire bytes from the Stage 4 ledger), the `rebuild` lines, the `stage4` manifest's SHA-256, the
inputs unchanged (step 10), the wall time and disk use, and each problem found and fixed.

## 8. Decisions and calls

**Owner decisions, 2026-11-19**

- The reason: point-in-time awareness. Owner's words: "Point-in-time awareness."
- D1. Amendment handling reaches the in-quarter partners: the in-quarter originals of sampled amendments, and the
  in-quarter amendments of sampled filings whose bytes declare their original. Owner's words: "C: fetch
  in-quarter".
- D2. The SEC budget for Stage 4: at most 30 requests and 50 MB received, at most 3 requests a second, and no other
  SEC client running. Owner's words: "Approve 30 ／ 50 MB".
- D3. Approach A, a `stage4/` folder beside the Stage 3 tables. Owner's words: "A: Stage 4 folder".

**Calls made in this spec** (the owner did not correct them, and may still)

- The cutoff is `last_modified_at`, else `fetched_at`. `public_at` never serves as the cutoff (5.1).
- A date means the end of that day in New York. An instant needs an offset.
- An answer holds every record that was public by `T`. Nothing is dropped or replaced (platform R24's default).
- Index rows of filings that we do not hold answer from the index file's `Last-Modified`.
- The partner rules of 5.2, with "the same CIKs" as the set of `cik` values over the index rows, a same-day
  candidate included, and one hop only.
- The partner list is a table written before any request.
- A failed partner fetch may be tried again while budget remains, as in `fetch`, not once only as in `refetch`.
- The `links` rules of 5.5. A link needs a declared value. The 13F link follows R23: filer and period of report.
- A rejected candidate stays held and answers at its own time with its own link.
- A found original that the SEC accepted after its amendment is no link (5.5).
- In a pair, each filing answers at its own `known_from`, even when the amendment answers first. The report and the
  findings name such pairs (5.5).
- `asof` returns the answer in memory and prints counts. It finds each manifest by the set's stamps and checks the
  table files that it reads.
- The `stage4` manifest names the `tables` manifest in `builds_on`, and does not list the sampled bytes again.
- `rebuild` covers the Stage 4 tables too. All 19 lines must be `equal`.
- The report gains a Stage 4 section.
- Neither watch item of the brief fires (section 3), so neither needs an owner decision.

## 9. Left to the builder

- The module layout, for example `partners.py`, `links.py` and `asof.py`, none of which imports `requests`.
- How the shared steps read a second list, bytes folder and ledger. For example, `Layout` can gain the Stage 4 paths
  as properties, as it holds `stage2/` today. It must not become a second root (section 3).
- The command name and flags of the offline step of 5.4 and 5.5, and whether it is one command or two.
- How `asof --table` keeps the rows apart from the summary.
- The JSON field names and the `manifest_format` number of the `stage4` manifest. The meanings in 5.7 stay.
- The wording of `link_problem` values and of the report section.
- The README text for the new commands.

## 10. Rollout note

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 4 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

The next step is writing-plans, in a fresh session, against this file.

Three departures from the roadmap, for the re-validation at plan completion:

- Stage 4 sends live SEC requests. The roadmap authorizes live requests only within Stage 1's budget (Completion).
  The owner set a Stage 4 budget (D2), as for Stage 2. This is the stage's one new owner gate.
- Stage 4 holds 20 filings beyond the 500-filing sample, the in-quarter partners (D1). They live in
  `ROOT/stage4/`, with their own ledger, tables and manifest. The roadmap's Stage 4 entry names the sample only.
- The Exit's amendment clause has two readings. The owner chose the in-quarter reach (D1). Originals in other
  quarters stay out, under the owner's decision of 2026-11-16.

Stage 4 is the roadmap's last stage. After its plan completes, the roadmap's completion review (derive-roadmap §6)
re-runs the rubric over O1–O4. The 16 held parked items of `specs/deferred_items.md` wait for that review. Stage 4
does not tick, move or retire them.

## Appendix A. The partner list on the live root

From the rules of 5.2 over `tables/index.parquet`, `tables/sample.parquet` and the sampled bytes, read on
2026-11-19 with no SEC request.

| Partner | Form | Date filed | Rule | Sampled filing |
|---|---|---|---|---|
| `0002065248-26-000002` | D | 2026-07-06 | `original_previous_accession` | `0002065248-26-000003` (D/A) |
| `0001840735-26-000021` | D | 2026-07-30 | `original_previous_accession` | `0002135638-26-000005` (D/A) |
| `0000892251-26-000081` | 4 | 2026-07-06 | `original_date_issuer_owner` | `0000892251-26-000099` (4/A) |
| `0001628280-26-047904` | 4 | 2026-07-10 | `original_date_issuer_owner` | `0001628280-26-051492` (4/A) |
| `0001193125-26-315913` | SCHEDULE 13D/A | 2026-07-24 | `candidate_amendment` | `0001193125-26-303495` |
| `0001193125-26-328063` | SCHEDULE 13D/A | 2026-07-31 | `candidate_amendment` | `0001193125-26-303495` |
| `0002143027-26-000010` | 13F-HR/A | 2026-08-07 | `candidate_amendment` | `0002143027-26-000004` |
| `0001477932-26-004961` | SCHEDULE 13D/A | 2026-08-13 | `candidate_amendment` | `0001477932-26-004693` |
| `0002147707-26-000003` | SCHEDULE 13D/A | 2026-08-18 | `candidate_amendment` | `0002147707-26-000002` |
| `0001119032-26-000009` | 13F-HR/A | 2026-08-21 | `candidate_amendment` | `0001119032-26-000007` |
| `0000912282-26-001155` | SCHEDULE 13D/A | 2026-08-24 | `candidate_amendment` | `0000912282-26-000961` |
| `0001104659-26-106301` | SCHEDULE 13D/A | 2026-09-09 | `candidate_amendment` | `0001104659-26-084244` |
| `0001361570-26-000019` | SCHEDULE 13D/A | 2026-09-09 | `candidate_amendment` | `0001361570-26-000017` |
| `0001493152-26-042291` | SCHEDULE 13D/A | 2026-09-11 | `candidate_amendment` | `0001493152-26-035145` |
| `0001493152-26-042523` | SCHEDULE 13D/A | 2026-09-14 | `candidate_amendment` | `0001493152-26-035149` |
| `0001921640-26-000017` | 4/A | 2026-09-17 | `candidate_amendment` | `0001921640-26-000018` |
| `0000902664-26-003894` | SCHEDULE 13D/A | 2026-09-22 | `candidate_amendment` | `0000902664-26-003832` |
| `0002146534-26-000002` | D/A | 2026-09-24 | `candidate_amendment` | `0002146534-26-000001` |
| `0001361570-26-000021` | SCHEDULE 13D/A | 2026-09-25 | `candidate_amendment` | `0001361570-26-000017` |
| `0000902664-26-003970` | SCHEDULE 13D/A | 2026-09-29 | `candidate_amendment` | `0000902664-26-003832` |
