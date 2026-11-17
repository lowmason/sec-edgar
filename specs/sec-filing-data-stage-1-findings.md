# sec-filing-data Stage 1 findings

This file is the evidence record of Stage 1 of the [sec-filing-data roadmap](sec-filing-data-roadmap.md),
implemented by [plan 10](plans/10-sec-filing-data-stage-1.md). Under the lighter process (D1), it is the
only evidence record. It records the results of the real run, each problem found and fixed, and the
measured cost.

## Run record

- Output root: `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3` (D3). It is in the main checkout
  and git-ignored, so removing a worktree cannot delete it.
- Code: branch `claude/sec-filing-data-stage-1-07efee`, run from the working tree. The pilot ran at
  commit `4facfd6`.
- Input: `data/objects/raw/sec/indexes/kind=quarterly/period=2026Q3/sha256=526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150/master.zip`
  in the main checkout, 3,505,445 bytes, read in place. `index` checks the size and the SHA-256 before
  it parses. The zip's folder was unchanged after the run.
- User-Agent: `sec.user_agent` from `conf/sec-edgar.json`, passed in `SEC_USER_AGENT`. The value is not
  copied here.
- Dates: the pilot ran on 2026-11-17.

## O1

- The `index` table holds 302,499 rows: lines 12 to 302,510 of `master.idx`. Every data row split into
  exactly 5 fields.
- The file is strict UTF-8 with `\r\n` line endings, and has 11 header lines. The last header line is the
  dashed line.
- The rows hold 216,057 distinct accession numbers. 5 accessions carry more than one form type (the
  "repeated keys"). No row was dropped or merged.
- Wall time: 0.4 s.

## Sample

- Rule: plan 10 Task 2, seed `20260930`, size 500, quota 20.
- Strata: 160 `quota` (20 for each of the 8 forms), 5 `repeated`, 335 `uniform`. Total 500 distinct
  accessions.
- Accessions in the index for each quota form (the draw pool):

  | Form | Accessions |
  |---|---|
  | `10-K` | 349 |
  | `10-Q` | 5,288 |
  | `3` | 3,868 |
  | `4` | 33,519 |
  | `5` | 35 |
  | `SCHEDULE 13D` | 270 |
  | `SCHEDULE 13G` | 2,561 |
  | `13F-HR` | 9,442 |

- `repeated`: 4 accessions under `SC 13D/A;SC TO-T/A`, and 1 under `SC 13E3;SC TO-I`. None of them
  carries a quota form.
- The legacy `SC 13D/A` enters only through the repeated keys, as D4 says. No `uniform` row has form
  type `SC 13D/A`. Two `uniform` rows have form type `SCHEDULE 13D/A`.
- Legacy `SC 13G` has no filing in the 2026Q3 index (0 rows).

## Pilot checkpoint

The pilot ran `fetch --per-form 2`, then `envelopes` and `report`: 16 filings, the first 2 in draw order
of each quota form.

- Fetch: exit 0. 16 filings `ok`. 17 requests: one SEC `503` on a Form 5, retried once, then `ok`.
  2,489,212 wire bytes and 26,632,991 decoded bytes. Fetch wall time: 29.2 s.
- Every `ok` response had `Content-Encoding: gzip`. Each recorded `wire_bytes` was above 0 and well
  below the decoded size, for example 855,350 against 8,778,858 for a 10-Q. The ledger does not record
  `Transfer-Encoding`, so the pilot does not show whether any response was chunked. The client counts
  wire bytes the same way in both cases (see Problems found and fixed, item 1).
- Envelopes: 0 parse errors.

Header checks, all passed for the 16 filings:

| Check | Result |
|---|---|
| `submission_type` equals the sample's `form_type` | 16 of 16 |
| `acceptance_datetime`, `filed_as_of_date` and `public_document_count` not null | 16 of 16 |
| At least one party with a role and a CIK | 16 of 16 |
| Forms 3, 4 and 5 have both `REPORTING-OWNER` and `ISSUER` | 6 of 6 |
| `public_document_count` equals `document_count` | 16 of 16 |

- One Form 4 (`0000905148-26-003534`) has 5 `REPORTING-OWNER` parties and 1 `ISSUER`.
- Schedules 13D and 13G name their parties `SUBJECT COMPANY` and `FILED BY`. 10-K, 10-Q and 13F-HR
  filings have one `FILER` party.
- `period_of_report` is null for the 4 schedules. Their headers have no `CONFORMED PERIOD OF REPORT`.

XBRL instances in the pilot 10-K and 10-Q filings:

| Accession | Form | `EX-101.INS` | `*_htm.xml` document | Documents described `IDEA: XBRL DOCUMENT` |
|---|---|---|---|---|
| `0001493152-26-041491` | 10-K | none | `form10-k_htm.xml` | 32 |
| `0001477932-26-005718` | 10-K | none | `aoxy_10k_htm.xml` | 47 |
| `0001045450-26-000042` | 10-Q | none | `epr-20260630_htm.xml` | 54 |
| `0001193125-26-322462` | 10-Q | none | `vicr-20260630_htm.xml` | 58 |

Each `*_htm.xml` is a document of type `XML` inside the submission, described `IDEA: XBRL DOCUMENT`.
So every pilot 10-K and 10-Q has an instance inside, and Task 8 skips its Step 0 (`fetch-instances`).

Documents that hold the ownership records:

| Form | Document type | Filename | XML root element |
|---|---|---|---|
| 3 | `3` | `primary_doc.xml`, `ownership.xml` | `ownershipDocument` |
| 4 | `4` | `wk-form4_1783027358.xml`, `form4.xml` | `ownershipDocument` |
| 5 | `5` | `ownership.xml`, `form5.xml` | `ownershipDocument` |
| SCHEDULE 13D | `SCHEDULE 13D` | `primary_doc.xml` | `edgarSubmission` |
| SCHEDULE 13G | `SCHEDULE 13G` | `primary_doc.xml` | `edgarSubmission` |
| 13F-HR | `INFORMATION TABLE` | `infotable.xml`, `Compass_Planning_13F_2026-Q2.xml` | `informationTable`, `ns1:informationTable` |

- The 13F-HR cover page is a second document, `primary_doc.xml`, with root `edgarSubmission`.
- One 13F information table uses the prefix `ns1:`. This is the case of Review Focus 4.
- One `SCHEDULE 13G` also holds an `EX-99.1` HTML exhibit.

## O2

To be filled at Task 7.

## O3

To be filled at Task 8.

## O4

To be filled at Tasks 9 and 10.

## Platform checks

To be filled at Tasks 7 and 10 (D5).

## Problems found and fixed

Found while building, before any SEC request:

1. **Wire bytes of a chunked response.** Plan 10 Task 3 said "Wire bytes come from
   `response.raw.tell()`". With urllib3 2.8.0, `tell()` stays at 0 for a response with
   `Transfer-Encoding: chunked`. An offline probe over a real urllib3 response gave `tell` 15,102 for a
   gzip body with `Content-Length`, and 0 for the same body sent chunked. The budget guard and the cost
   record would then be blind. Global Constraints define 5 GB as bytes on the wire, so the client now
   reads `raw.stream(..., decode_content=False)`, counts each raw piece as wire bytes, and decodes gzip
   and deflate itself, with a bound on each decode step. Test `RealUrllib3Tests` pins a chunked gzip
   body to its compressed length. Commit `52b1f65`.
2. **Redirects.** `requests` follows redirects by default. Each hop would be an SEC request with no
   ledger record and no spacing. The client now sends `allow_redirects=False`, and a 3xx status gives
   `failed`. Commit `52b1f65`.
3. **A corrupt compressed body.** A gzip or deflate body that fails to decode gives `failed` for that
   filing, and the walk goes on. Commit `970ce75`.
4. **An `ok` record with no file.** When a hard kill falls between the `ok` record and the rename,
   `fetches` gives `failed` with the reason `ok response, but <path> is missing`, so `ok` always means
   the bytes are on disk. The next `fetch` refetches the filing. Commit `4facfd6`.

Found by the live run: none so far.

## Measured cost

So far (pilot, before Task 7):

| Measure | Value |
|---|---|
| SEC requests | 17 of 1,500 |
| Wire bytes | 2,489,212 of 5,000,000,000 |
| Decoded bytes | 26,632,991 |
| Wall time | `index` 0.4 s, `sample` 0.7 s, `fetch` 29.2 s, `envelopes` 0.1 s |
| Disk use of the root | 35,427,496 bytes |

## Exit check

To be filled at Task 10.

## Sample list

To be filled at Task 10 (D5).
