# Stage 2: Provenance and timing — Design Spec

**COMPLETE (2026-11-18)**, implemented by [plan 11](../plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md). Results: [Stage 2 findings](../sec-filing-data-stage-2-findings.md).

**Status:** Approved by the owner, 2026-11-17. Owner's words: "Approve spec".
**Project:** `/Users/lowell/Projects/sec-edgar`, package `packages/sec-filing-data`.
**Roadmap:** [sec-filing-data roadmap](../sec-filing-data-roadmap.md), Stage 2.
**Inputs:** Stage 1 as built: [plan 10](../plans/completed/10-sec-filing-data-stage-1.md) (its Handoff section),
the [Stage 1 findings](../sec-filing-data-stage-1-findings.md), and the live root
`/Users/lowell/Projects/sec-edgar/filing-data/2026Q3` (tables, bytes, `fetch-log.jsonl`). The items that the owner
carried into Stage 2: `specs/deferred_items.md`, section `10-sec-filing-data-stage-1 — 2026-11-17` (the V6 refetch,
and the SEC documentation checks for V7 and V8). Background only: the parked
[platform spec](sec-filing-platform.md), R9 and R11–R12. One record of the parked store, cited by owner
decision D5 and copied as constants: the receipt of `master.zip` (section 6.2).

## 1. Purpose

Stage 1 delivered the 2026Q3 index (O1), 500 sampled filings (O2), their XBRL facts (O3) and their ownership
records (O4). Each record knows its accession number, and each filing knows its fetch time. No record says which
bytes it came from, when the SEC accepted the filing, or when the filing became public.

Stage 2 gives every record of O1–O4 its source, the SHA-256 of its source bytes, and the times that point-in-time
use needs. Stage 4 builds as-of views on these times. Stage 3 builds manifests and hash-bound evidence on this
provenance. So Stage 2 decides the clocks that later stages read, and it must not present one clock as another.

Stage 2 also proves that the tables re-derive from the kept bytes with no SEC request. It meets the Done-when of
the three items that the owner carried in from Stage 1. The question behind the V6 refetch stays open (D6).

## 2. Scope

**Goals**

- G1. Each filing of the sample has an acceptance time, a public time with its rule, the `Last-Modified` time of
  the stored copy, and its fetch time, all in UTC. The as-filed text values stay unchanged beside them.
- G2. Each record of O1–O4 names its source URL, the SHA-256 of its source file, and its times. Facts and ownership
  records also name the document inside the file that they came from.
- G3. A rebuild re-creates every table from the kept bytes, the ledgers and `master.zip`. It sends no SEC request,
  and its tables equal the live tables.
- G4. A refetch of `9999999995-26-002992` records its SHA-256 beside the Stage 1 SHA-256 (V6). The findings state
  what this refetch can show and what it cannot (6.3).
- G5. This spec cites SEC documentation for V7 and V8 (section 4).

**Non-goals**

- Manifests, hashes of single documents or values, versioned record formats and code versions: Stage 3.
- As-of views and amendment handling: Stage 4.
- Other quarters, Feed archives, `submissions.zip`, SEC holiday calendars and inline XBRL. The deferred items keep
  them.
- Times for the 301,759 index rows of accessions outside the sample. Their filings have no fetched header, and
  Stage 2 fetches no header for them. (The 500 sampled accessions have 740 index rows, because an accession is
  listed once for each CIK and form type.)
- New fetches of sampled filings, other than the V6 refetch.
- Whether an archive copy changes after a correction. Stage 1 fetched every copy on 2026-11-17, after the changes
  in question, so no Stage 2 request can answer it (D6). It goes back to `specs/deferred_items.md` (section 11).

**Anti-goals.** Stage 2 fails, even if its tables are complete, when:

- it changes an as-filed value, or replaces one with a derived value;
- a public time is earlier than its filing's acceptance;
- it labels the rule time as observed, or `Last-Modified` as the public time;
- the rebuild sends an SEC request, or reads anything from the network;
- it changes or deletes a Stage 1 byte file, or a line of the Stage 1 ledger.

## 3. Constraints

- Stage 1's constraints carry over: Python 3.14 in the uv workspace, `requests` and `pyarrow` as the only runtime
  dependencies, the client rules (declared User-Agent, at least 0.34 s between request starts, at most 5 attempts,
  timeouts, the 256 MiB response guard), fixture and live data kept apart in tests, and socket calls blocked in
  tests. Only the client and fetch code import `requests`.
- SEC budget for Stage 2 (owner, D2): at most 20 requests and 50,000,000 wire bytes, at most 3 requests a second,
  and no other SEC client running. Every attempt counts, retries included. Stage 1's ledger and its 1,500-request
  limit stay as they are. Stage 2 counts in its own ledger. Planned use: 1 request, the V6 refetch (D6).
- Documentation reads (D2): at most 10 SEC documentation pages, read by hand in the browser, outside the data
  budget. This spec used 2 of them (section 4). eCFR is not an SEC host and is not counted.
- The lighter process of Stage 1 continues (my call, section 9). Code runs from the working tree, a fix needs no
  release, the run fixes each problem it finds, and `specs/sec-filing-data-stage-2-findings.md` is the only evidence
  record.
- Time-zone conversion uses `zoneinfo` from the standard library, with the key `America/New_York`.
- The `master.zip` receipt (D5) holds the owner's User-Agent in its context block. Stage 2 copies only the URL, the
  receive time and `Last-Modified` from it. No committed line holds the User-Agent or the contact address in it.

## 4. SEC documentation (V7, V8 and the time zone)

Read on 2026-11-17.

- **Filing date (Rule 13 of Regulation S-T, 17 CFR 232.13, eCFR, current to 2026-11-13).** A filing whose
  transmission starts at or before 5:30 p.m. Eastern time is filed that business day. One that starts later is
  filed the next business day (232.13(a)(2)). Forms 3, 4, 5 and 144 and Schedules 13D, 13G and 14N keep the same
  day until 10 p.m. (232.13(a)(4)). Registration statements under Rule 462(b) do too (232.13(a)(3)). The cutoff
  applies to the start of transmission, not to acceptance. So acceptance alone cannot place a filing on either side
  of 5:30 p.m., and `FILED AS OF DATE` is the authority. One sampled 497K, accepted at 17:30:03, kept its date.
  <https://www.ecfr.gov/current/title-17/chapter-II/part-232/subpart-A/section-232.13>
- **V8, dissemination of a late filing (SEC, "Determine the Status of My Filing", last updated 2024-10-31).**
  EDGAR operates from 6:00 a.m. to 10:00 p.m. ET on business days. Most submissions that start after 5:30 p.m. ET
  get a filing date of 6:00 a.m. ET the next business day, and EDGAR does not disseminate them until that day. The
  10 p.m. form types are disseminated until 10 p.m. on the day sent. **Answer: the next business day, from 6:00 a.m.
  ET.** <https://www.sec.gov/page/edgar-how-do-i-determine-status-my-filing>
- **V7, `<PRIVATE-TO-PUBLIC>` (EDGAR PDS Technical Specification, draft version 2.0, March 2025).** The tag
  "identifies an SEC-approved private-to-public document dissemination". It is present only in a `*.pr`
  dissemination. Private documents are held at the SEC, and the SEC releases some of them later, at its own
  discretion. **Answer: a tagged submission became public at a later SEC release. Its header does not give that
  time, and its acceptance time is not its public time.**
  <https://www.sec.gov/files/edgar/pds_dissemination_spec.pdf>
- **Time zone.** The same specification gives the control block's acceptance time as "(EST)". The data shows New
  York local time, which is EDT in summer. Read as EDT, each of the 500 sampled acceptances comes 12 s or more
  before its own `Last-Modified`. Read as fixed EST, each summer acceptance would come about 1 hour after its own
  `Last-Modified`, which cannot happen. So the conversion uses `America/New_York`.

The data agrees with these answers. In the 500 sampled filings, 22 have a `FILED AS OF DATE` one or more business
days after their acceptance date. Their copies appeared on EDGAR at 06:00–06:07 ET on that filing date, weekends
skipped. For 456 of the 477 filings that kept their date, the copy appeared within 60 s of acceptance.

## 5. Approaches

The owner chose A (D4).

- **A. Extend the Stage 1 steps in place (chosen).** The existing steps gain the new columns, and the live tables
  are re-written with them. One set of tables serves Stages 3 and 4, and each record can be read on its own. Cost:
  the Stage 1 schemas and tests change, and the live tables are replaced. A frozen copy of the Stage 1 tables and
  the rebuild check cover that.
- **B. A new step on top.** A `provenance` step writes new tables beside the Stage 1 tables, which stay untouched.
  Cost: two table sets, 45,358 facts stored twice, and later stages must know which set to read. `ownership` must
  change anyway, because only it knows which XML document gave a record.
- **C. Separate provenance tables joined by key.** One row per filing holds the source and the times. Records keep
  only their keys. Cost: a record names its times only through a join, and each as-of query needs joins.

## 6. Design

### 6.1 The times of a filing

The `filings` table keeps `acceptance_datetime`, `filed_as_of_date`, `date_as_of_change` and `fetched_at` as they
are. It gains these columns:

| Column | Type | Meaning |
|---|---|---|
| `accepted_at` | timestamp, UTC | `acceptance_datetime` read as New York local time |
| `public_at` | timestamp, UTC | The public time by rule. Null under rules `private_to_public` and `no_acceptance`. |
| `public_rule` | string | `acceptance`, `next_opening`, `private_to_public` or `no_acceptance` |
| `last_modified_at` | timestamp, UTC | The `Last-Modified` header of the `ok` response that gave the stored bytes, from the ledger. Null when absent. |

The rule, for each `ok` filing with a parsed header:

1. When the header carries `PRIVATE-TO-PUBLIC`: `public_at` is null and the rule is `private_to_public` (V7).
2. When `acceptance_datetime` is null: `public_at` is null and the rule is `no_acceptance`.
3. Take the later of `accepted_at` and 06:00 New York time on `filed_as_of_date`.
4. When that time is before 06:00 New York time, move it to 06:00 the same day. When it is at or after 22:00, move
   it to 06:00 the next calendar day.
5. The rule is `acceptance` when the result equals `accepted_at`, else `next_opening`.

`public_at` is the earliest time that the filing could have been public. `last_modified_at` is the latest, as far
as the stored copy shows: the copy existed by then. A later change to the archive copy moves `Last-Modified` later
but never earlier. Stage 4 chooses which bound an as-of view reads. A view that must never show a filing early
reads `last_modified_at`.

Step 4 uses calendar days, not business days, so it needs no holiday calendar. A calendar day is never later than
the business day, so `public_at` stays a lower bound. Filings whose date moved past a weekend or a holiday are
handled by step 3, because `FILED AS OF DATE` already skips those days.

Expected result on the sample, from a check of this rule against the Stage 1 data on 2026-11-17: 477 filings
`acceptance` and 23 `next_opening` (the 22 moved filings and `EFFECT` `9999999995-26-002992`, accepted at 00:15).
No `public_at` comes after its `last_modified_at`. The gap between them is 12 s to 432 s for 499 filings. For the
10-Q `0001836875-26-000073` it is 13 days: accepted on 2026-08-14 at 17:04:31 ET, last modified on 2026-08-27 at
11:24:30 ET. Its `DATE AS OF CHANGE` equals its filing date. So the archive copy can change after acceptance with no
sign in the header, and the findings record this case.

### 6.2 Provenance and times on each table

Records tables get the new columns. Status tables (`facts_status`, `ownership_status`), `sample` and `fetches` stay
as they are.

| Table | Outcome | New columns |
|---|---|---|
| `index` | O1 | `source_url`, `source_sha256`, `index_built_at`, `index_data_through`, `index_received_at`, `index_last_modified_at`, and the five filing times (below) |
| `filings` | O2 | `source_url`, and the times of 6.1. Its existing `sha256` is the source SHA-256. |
| `parties`, `documents` | O2 | `source_url`, `source_sha256`, and the five filing times |
| `facts` | O3 | `source_url`, `source_sha256`, and the five filing times. `source_document` exists. |
| `ownership` | O4 | `source_url`, `source_sha256`, `source_document`, and the five filing times |

- The five filing times are `accepted_at`, `public_at`, `public_rule`, `last_modified_at` and `fetched_at`, copied
  from the record's filing.
- For a filing, `source_url` is the URL that was fetched (`sample.url`), and `source_sha256` is the SHA-256 of the
  stored file (`filings.sha256`). The source is the complete submission file as fetched, not a URL of a single
  document that was never requested.
- `ownership.source_document` is the filename of the XML document that gave the record. `xml_document` finds that
  document today, but returns only its text, so it must also give the filename.
- The index rows:
  - `source_url`, `index_received_at` and `index_last_modified_at` come from the parked engine's receipt of the same
    file (D5): `data/objects/staging/sec/88738b7d-cd8e-48c4-b301-b78dc4b993bd/wf-02586348dbe3e7033d621f8c2cd9c908fa3f62f7/5005901a1e8132207ea0cf7a0d4bec1d7b9ca3a6f0371b9e45c9eb2863045086/4fdd5bb903fc43f5921ee46c2bf47714/receipt.json` in the main checkout.
    The receipt's `sha256` equals `INDEX_SHA256`. Its values are:
    - `source_url`: `https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.zip` (the receipt's `url`).
    - `index_received_at`: `2026-10-31T17:54:33.039228Z` (the receipt's `received_at`).
    - `index_last_modified_at`: `2026-10-31T07:50:09Z` (the receipt's `Last-Modified` header). Like
      `last_modified_at` for a filing, it is observed. Every row of the file was listed by then.
  - These three values are committed constants beside `INDEX_SHA256`, with the receipt's path as their source. The
    run and the rebuild never read the parked store.
  - `source_sha256` is `INDEX_SHA256` (`526d2dbf…`).
  - `index_built_at` is the UTC modification time in the zip's extended-timestamp field (header ID `0x5455`) of the
    `master.idx` member: `2026-10-31T07:49:35Z`. Python's `zipfile` does not decode this field, so the code reads
    it. The member's DOS time (`2026-10-31 03:49:36`, New York time, rounded to 2 s) agrees with it.
  - `index_data_through` is the header line `Last Data Received:` as filed, `September 30, 2026`.
  - The rows of sampled accessions carry their filing's five times. The other rows have null filing times.
- Facts and ownership records of a filing that is not `ok` cannot exist, so their columns are never null for that
  reason.

### 6.3 Refetches

A new command, `refetch --out ROOT --accession A [--accession A ...]`:

- It refetches each named sampled filing from its `sample.url`. It refuses an accession that is not in `sample`.
- It writes to `ROOT/stage2/refetch/<accession>.txt` and records in `ROOT/stage2/fetch-log.jsonl`. It never writes
  under `ROOT/bytes/` and never appends to `ROOT/fetch-log.jsonl`.
- It uses the Stage 1 client rules, with the Stage 2 limits of 20 requests and 50,000,000 wire bytes counted over
  the Stage 2 ledger. It takes `ROOT/fetch.lock`.
- It sends no request for an accession already refetched. Each refetch happens once.
- An offline step writes a `refetches` table: one row per refetched accession, with the Stage 1 and refetch
  SHA-256, whether they are equal, both `Last-Modified` times, the refetch time, and, when the bytes differ, the
  header fields and the document entries that changed.

Live run: `9999999995-26-002992` only (D6). Expected: 1 request, about 1 KB on the wire. The 20-request limit stays
as approved.

What the refetch shows (D6). Stage 1 fetched this copy on 2026-11-17. Its `Last-Modified` is 2026-09-18 at 06:03
ET, the next opening after its acceptance and on its `DATE AS OF CHANGE`. The refetch compares two copies taken after
that date. So equal hashes show only that the copy did not change after 2026-11-17. They do not show that a
correction leaves the copy unchanged. The findings state this limit in those words or plainer ones.

Known effect: Stage 1's ledger counts a request with no response as 268,435,456 bytes. That is more than the Stage
2 byte limit. So a refetch interrupted mid-request spends the whole Stage 2 byte budget in the count, and later
refetches are refused. The run then stops and asks the owner. Stage 2 keeps this rule.

### 6.4 Rebuild

A new command, `rebuild --out ROOT --zip PATH`:

- In a new temporary folder, it re-creates every table under `ROOT/tables`: `index`, `sample` (drawn again with its
  seed), `fetches`, `filings`, `parties`, `documents`, `facts`, `facts_status`, `ownership`, `ownership_status` and
  `refetches`.
- Its inputs are `master.zip`, `ROOT/bytes/`, `ROOT/fetch-log.jsonl`, `ROOT/stage2/refetch/` and
  `ROOT/stage2/fetch-log.jsonl`, and the committed constants of 6.2. It reads them in place and does not copy the
  bytes. The ledgers are inputs because `fetched_at` and `Last-Modified` exist only there.
- It compares each table with the live table: schema, row count, and every row in order. It does not compare the
  Parquet file bytes.
- It prints one line per table, `equal` or the first difference. It exits 0 when every table is equal, and 1
  otherwise. It removes the temporary folder.
- It loads no module that imports `requests`, and it adds no ledger line.

### 6.5 The live run

1. Check the preconditions: no other SEC client runs, and `filing-data/` is git-ignored in the main checkout.
2. Copy `ROOT/tables` to `ROOT/tables-stage1`, once. Refuse when it exists. This keeps the tables behind the Stage
   1 findings.
3. Run `refetch` for `9999999995-26-002992` (live).
4. Re-run the offline steps: `index`, `envelopes`, `facts`, `ownership`, the `refetches` table, then `report`.
5. Check that the Stage 1 columns of each re-written table equal `tables-stage1`, row for row.
6. Run `rebuild`. Expected: every table `equal`.
7. Write the findings.

### 6.6 Report

`report` gains three sections:

- **Times:** filings per `public_rule`. The gap from `public_at` to `last_modified_at`: least, median and largest.
  The filings with a gap above 1 hour. The count of filings with `public_at` after `last_modified_at` (expected 0).
- **Provenance:** per records table, the rows with a null `source_url` or `source_sha256`, and the rows of `ok`
  filings with a null `accepted_at` or `fetched_at`.
- **Refetches:** each row of `refetches`, and the Stage 2 ledger's requests and wire bytes against the Stage 2
  limits.

## 7. Verification

Offline tests come first and fail before the code exists (red, then green), as in Stage 1. They read only fixtures
and temporary folders.

- The time rule: a same-day acceptance; a date moved to the next weekday; a date moved past a weekend; the `EFFECT`
  case (filing date before the acceptance date, accepted before 06:00); an acceptance at or after 22:00; a
  `PRIVATE-TO-PUBLIC` header; no acceptance line; a summer date (UTC−4) and a winter date (UTC−5); and the parse of
  an HTTP `Last-Modified` date.
- Provenance: `facts`, `ownership`, `parties` and `documents` carry their filing's source and times.
  `ownership.source_document` names the XML document. The index columns come from the extended-timestamp field, the
  header line and the constants. A test zip built with a `0x5455` field gives its UTC time, and a zip without the
  field gives null.
- Refetch: with a fake session, it writes only under `stage2/`, refuses an unknown accession, refuses the 21st
  request before sending it, and gives an equal row and a changed row in `refetches`.
- Rebuild: equal tables give exit 0. A changed live table gives exit 1 and names the table. It loads no module that
  imports `requests`.
- The existing Stage 1 tests pass, with their schemas extended.

## 8. Exit evidence

| Roadmap Exit part | Evidence in `specs/sec-filing-data-stage-2-findings.md` |
|---|---|
| Each record of O1–O4 names its source, its raw-byte SHA-256 and its times | The report's Provenance section: 0 null sources in the records tables, and the times per rule |
| A rebuild from the kept bytes reproduces the tables with no SEC request | `rebuild` exit 0 with every table `equal`, and both ledgers' line counts unchanged by it |
| The V6 refetch meets its Done-when | The `refetches` row of `9999999995-26-002992`, with both SHA-256 values, and the limit of 6.3 |
| The V7 and V8 checks meet their Done-when | Section 4 of this spec, repeated in the findings |
| Each live request is inside the Stage 2 budget | The Stage 2 ledger: at most 20 requests and 50,000,000 wire bytes |

The findings also record the Stage 1 column check (6.5 step 5), the 10-Q whose copy changed 13 days after
acceptance (6.1), the measured cost (requests, wire bytes, wall time, disk use), each problem found and fixed, and
the commit that ran.

## 9. Decisions and calls

**Owner decisions, 2026-11-17**

- D1. Public time: a rule-derived time of record, plus `Last-Modified` as an observed check column. Owner's words:
  "C: rule + Last-Modified".
- D2. SEC budget for Stage 2: at most 20 requests and 50,000,000 wire bytes, for the V6 refetch and the 10-Q
  refetch. Up to 10 SEC documentation pages read in the browser, outside the data budget. Owner's words: "Approve
  budget".
- D3. Provenance on each record as in 6.2, with the refetches, the rebuild and the Stage 3 boundary as stated here.
  Owner's words: "Looks right".
- D4. Approach A. Owner's words: "A: extend in place".
- D5. O1's URL, receive time and `Last-Modified` come from the parked engine's receipt of the same `master.zip`, as
  committed constants, so they read as recorded. This is the one parked record that Stage 2 cites. Owner's words:
  "Cite the receipt (Recommended)".
- D6. Only the V6 refetch runs (1 request). The 10-Q refetch of D2 is dropped. The findings state what the refetch
  cannot show, and the correction question goes back to the deferred items. Owner's words: "V6 only, state limit
  (Recommended)".

**Calls made in this spec** (the owner may correct any of them)

- The lighter process of Stage 1 continues.
- Acceptance text is New York local time (section 4).
- Step 4 of the rule rolls over by calendar day, which keeps `public_at` a lower bound with no holiday calendar.
- A `PRIVATE-TO-PUBLIC` filing has a null `public_at`. Only its `last_modified_at` bounds its public time.
- `index_built_at` is read from the zip's extended-timestamp field, not from the DOS time.
- Only records tables gain columns. Status tables, `sample` and `fetches` do not.
- The frozen copy `tables-stage1`, and the Stage 2 folder `ROOT/stage2/`.
- The rebuild works in a temporary folder and reads the bytes in place.

## 10. Left to the builder

- Which step writes the times on sampled `index` rows (for example, `envelopes` re-writes `index`). The rebuild
  runs the steps in one fixed order.
- The module layout. For example, a `times.py` with no network import, and the refetch code in `fetch.py`, or in a
  new module added to the exceptions of `test_offline_modules_never_import_requests`.
- How the client takes its limits as parameters in place of the module constants of `ledger.py`.
- How a `Layout` points the rebuild at a temporary tables folder while it reads the bytes in place.
- The format of the changed header fields and document entries in `refetches`.
- Column names, when a name here reads badly in code. The meanings stay.
- The report's wording.

## 11. Rollout note

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 2 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

The next step is writing-plans, in a fresh session, against this file. The plan's completion ticks the V6 refetch
and the V7 and V8 items in `specs/deferred_items.md`, section `10-sec-filing-data-stage-1 — 2026-11-17`. It also adds
one deferred item (D6): whether an EDGAR archive copy changes after a correction. That needs a copy fetched before a
correction and another after it. Revisit if: a roadmap stage fetches filings on the day they are filed.

One departure from the roadmap's Stage 2 entry: its Consumes line names Stage 1's outputs only, and D5 adds one
record of the parked store, the `master.zip` receipt, as committed constants. The re-validation at plan completion
should note it.
