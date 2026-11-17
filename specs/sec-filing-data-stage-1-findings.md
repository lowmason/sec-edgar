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

The full `fetch` ran on 2026-11-17 from 17:53:30Z to 18:04:42Z at commit `c0f5ee0`, then `envelopes` and
`report`. It skipped the 16 pilot filings already on disk.

- Fetch: exit 0. All 500 sampled filings are `ok`, with their bytes on disk under `bytes/`, and no `.part`
  file is left. No filing is `not_found`, `too_large`, `forbidden`, `failed` or `budget`.
- Each quota form has 20 `ok` filings. The 5 `repeated` and the 335 `uniform` filings are all `ok` too.
- `filings` has 500 rows. Each row has its parsed header fields: 0 parse errors, and no null
  `submission_type`, `acceptance_datetime`, `filed_as_of_date` or `public_document_count`. Each filing
  has at least one party. `parties` has 757 rows and `documents` 5,756.
- For each filing outside the `repeated` stratum, `submission_type` equals the sampled `form_type` (495 of
  495).
- Requests: 503 for 500 filings. 3 filings needed a second attempt:

  | Accession | Form | First attempt | Second attempt |
  |---|---|---|---|
  | `0000310354-26-000049` | 5 | SEC `503` | `ok` |
  | `0001839882-26-043407` | `uniform` | SEC `503` | `ok` |
  | `0001213900-26-098236` | DEFR14A (`uniform`) | status 200, then `ChunkedEncodingError: Response ended prematurely` mid-body | `ok` |

  The third case is the largest filing of the sample (181,664,551 decoded bytes). It shows on real data
  that a broken body is retried, as Problems found and fixed item 1 requires.
- Sizes per stratum, in bytes:

  | Stratum or quota form | Filings | Decoded, total | Decoded, median | Decoded, largest | Wire, total |
  |---|---|---|---|---|---|
  | 10-K | 20 | 189,093,302 | 7,820,184 | 29,357,244 | 38,503,120 |
  | 10-Q | 20 | 181,683,045 | 8,778,858 | 18,700,337 | 18,051,445 |
  | 3 | 20 | 779,585 | 11,173 | 361,260 | 440,023 |
  | 4 | 20 | 781,212 | 9,250 | 357,156 | 385,279 |
  | 5 | 20 | 131,860 | 6,116 | 15,137 | 35,588 |
  | SCHEDULE 13D | 20 | 1,206,504 | 19,530 | 371,293 | 490,811 |
  | SCHEDULE 13G | 20 | 229,997 | 10,915 | 22,995 | 70,255 |
  | 13F-HR | 20 | 2,130,646 | 62,305 | 530,007 | 169,001 |
  | `repeated` | 5 | 4,762,126 | 81,038 | 4,439,006 | 2,839,744 |
  | `uniform` | 335 | 749,820,628 | 62,783 | 181,664,551 | 233,470,387 |

- The 3 largest filings are `uniform`: a DEFR14A (181,664,551 decoded, 114,609,809 wire) and two ABS-EE
  (about 125 MB decoded and 4.5 MB wire each). The DEFR14A alone is 36% of all wire bytes.
- The most frequent `uniform` form types are `4` (57), `424B2` (55), `NPORT-P` (24), `8-K` (23), `D` (23)
  and `13F-HR` (17).

## O3

`facts` ran at commit `ea21c64`, then `report`. Wall time: 1.3 s. It sent no SEC request.

- Filings in the fact forms (`10-K`, `10-K/A`, `10-Q`, `10-Q/A`): 46. These are the 20 quota `10-K`, the
  20 quota `10-Q` and 6 `uniform` `10-Q`. The sample has no `/A` filing of these forms.
- All 46 gave facts. 0 filings gave none, so no reason is listed.
- Source document (D2): all 46 instances are the SEC-extracted `*_htm.xml` inside the submission. 0 came
  from an `EX-101.INS`. Task 8 Step 0 (`fetch-instances`) was not needed and was not built.
- `facts` has 45,358 rows. Facts per filing: 215 at least, 924 median, 2,365 at most.
- Check without the parser: in each of the 46 instances, the count of `contextRef` attributes in the raw
  text equals `fact_count`.
- Concepts: 4,325 distinct. Every concept has a prefix, so none fell back to `{namespace}local`. The most
  frequent prefixes are `us-gaap` (38,170), `dei` (1,582) and `ecd` (301). The rest are company prefixes.
- Periods: 16,734 instant and 28,624 duration facts. Every fact has a period.
- Dimensions: 22,481 facts (50%) have at least one dimension member.
- Units: `iso4217:USD` 31,424, `shares` 4,129, `pure` 2,211, `iso4217:USD/shares` 2,029 (a divide unit).
  5,111 facts have no unit (text facts).
- `xsi:nil` facts: 1,341. Their `value` is null.
- Values are stored as filed text, with no numeric conversion.

## O4

### Forms 3, 4 and 5

`ownership` ran at commit `65b4c1f`. It sent no SEC request.

- Filings of Forms 3, 4 and 5 in the sample: 127. These are 20 quota each, 57 `uniform` Form 4, 7
  `uniform` Form 3 and 3 `uniform` Form 4/A.
- 108 of them gave records: 76 Form 4, 20 Form 5, 9 Form 3 and 3 Form 4/A. They gave 309 records:
  232 from Form 4, 41 from Form 5, 30 from Form 3 and 6 from Form 4/A.
- Records per kind: 195 `non_derivative_transaction`, 46 `derivative_transaction`, 43
  `non_derivative_holding` and 25 `derivative_holding`.
- 19 filings gave none:
  - `no securities owned`: 18 Form 3 filings, each filed with `noSecuritiesOwned` set to 1.
  - `no records in the ownership document`: 1 Form 4, `0001801444-26-000001`. Its document has no
    transaction or holding table, and it is filed with `notSubjectToSection16` set to 1.
- Every record has an issuer CIK and an owner CIK. Every transaction record has a transaction date.
- 18 records come from filings with more than one reporting owner. Each record keeps the first owner,
  and `owner_count` gives the number of owners.

## Platform checks

The report's lines over all 500 sampled filings (D5). Task 10 adds one line for each of V1–V12 of the
[parked platform spec](completed/sec-filing-platform.md).

- V3: 500 `ok` responses. All 500 have `Content-Encoding: gzip`. 0 have an `ETag`. 500 have a
  `Last-Modified`.
- V5: the 5 repeated-key filings:

  | Accession | Sampled `form_type` | `submission_type` | `document_count` |
  |---|---|---|---|
  | `0001104659-26-081696` | `SC 13D/A;SC TO-T/A` | `SC TO-T/A` | 2 |
  | `0001104659-26-081818` | `SC 13D/A;SC TO-T/A` | `SC TO-T/A` | 2 |
  | `0001104659-26-082921` | `SC 13D/A;SC TO-T/A` | `SC TO-T/A` | 2 |
  | `0001104659-26-086886` | `SC 13D/A;SC TO-T/A` | `SC TO-T/A` | 2 |
  | `0001654954-26-008429` | `SC 13E3;SC TO-I` | `SC TO-I` | 33 |

  Each is one submission. Its header gives one of the index's two form types.
- V6: 1 filing has a `date_as_of_change` later than its `filed_as_of_date`: `9999999995-26-002992`, form
  `EFFECT` (`uniform`), filed `20260917`, changed `20260918`, accepted `20260918001512`.
- V7: 0 filings carry `PRIVATE-TO-PUBLIC`.
- V9: 0 filings have a null `acceptance_datetime`.
- V10: 112 filings hold documents described `IDEA: XBRL DOCUMENT`. In all 112, `public_document_count`
  equals `document_count`. So the count includes the SEC-generated XBRL documents.

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

So far (after Task 7, the full fetch):

| Measure | Value |
|---|---|
| SEC requests | 503 of 1,500 |
| Wire bytes | 321,729,304 of 5,000,000,000 |
| Decoded bytes | 1,130,618,905 |
| Wall time | `index` 0.4 s, `sample` 0.7 s, `fetch` 700.1 s (pilot and full run), `envelopes` 1.4 s, `report` 0.05 s |
| Disk use of the root | 1,139,936,818 bytes |

The roadmap estimated 2–4 GB at 4–8 MB a filing. The sample measured 2.26 MB decoded and 0.64 MB on the
wire a filing, on average. The median filing is far smaller, and a few large `uniform` filings carry most
of the bytes.

## Exit check

To be filled at Task 10.

## Sample list

To be filled at Task 10 (D5).
