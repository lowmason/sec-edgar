# sec-filing-data Stage 1 findings

This file is the evidence record of Stage 1 of the [sec-filing-data roadmap](completed/sec-filing-data-roadmap.md),
implemented by [plan 10](plans/completed/10-sec-filing-data-stage-1.md). Under the lighter process (D1), it is the
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
  copied here. Plan 12 removed `conf/` from `main`. The file is at tag `ingest-parked-2026-11-16`.
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
  that a broken body is retried, as Problems found and fixed item 1 requires. urllib3 2.8.0 raises
  "Response ended prematurely" only while it reads a chunked body (`urllib3/response.py:1383`), so the SEC
  sent this response with `Transfer-Encoding: chunked`. Under the plan's first rule (`raw.tell()`), a
  chunked response counts 0 wire bytes. This filing's successful attempt carried 114,609,809 wire bytes.
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

### Schedules 13D and 13G, and Form 13F

`ownership` ran again at commit `6d7504b`, with all three parsers. It sent no SEC request. The Form 3, 4
and 5 results above did not change.

- Filings in the ownership forms: 216. 193 gave records, 6,847 in total:

  | Form | Filings | Filings with records | Records | Record kind |
  |---|---|---|---|---|
  | 3, 4, 5, 4/A | 127 | 108 | 309 | Form 3, 4 and 5 kinds (above) |
  | SCHEDULE 13D | 20 | 20 | 51 | `schedule13_reporting_person` |
  | SCHEDULE 13D/A | 2 | 2 | 4 | `schedule13_reporting_person` |
  | SCHEDULE 13G | 22 | 22 | 33 | `schedule13_reporting_person` |
  | SCHEDULE 13G/A | 3 | 3 | 8 | `schedule13_reporting_person` |
  | 13F-HR | 37 | 37 | 6,441 | `form13f_holding` |
  | 13F-HR/A | 1 | 1 | 1 | `form13f_holding` |
  | `SC 13D/A;SC TO-T/A` (repeated keys) | 4 | 0 | 0 | none |

- 23 filings gave none. The 19 Form 3 and 4 filings are above. The other 4 are the repeated-key
  `SC 13D/A;SC TO-T/A` filings: each holds only text and HTML documents, so the reason is
  `no ownership XML document`. This is the legacy text schedule of Review Focus 3.
- Check without the parser: a separate scan of the raw documents counted 96 reporting-person elements in
  the 47 XML schedules and 6,441 `infoTable` rows in the 37 13F-HR tables. These equal the record counts.
- Schedule records: every one of the 96 has an issuer CUSIP, an amount owned and a percent of class. 42
  have an owner CIK. Schedule 13G names no reporting-person CIK in any sampled filing, and 13D gives one
  only where the person has a CIK. One schedule lists two CUSIPs, which are kept joined with `;`.
- 13F records: all 6,442 have a CUSIP and the filer's CIK as owner. 45 carry a `putCall`. 6,437 are
  share amounts (`SH`) and 5 are principal amounts (`PRN`). Many tables use the `ns1:` prefix, and the
  parser matches local names.

Element names the parsers read (by local name; the 13D and 13G schemas differ):

| Field | Schedule 13D | Schedule 13G | Form 13F information table |
|---|---|---|---|
| root | `edgarSubmission` (namespace `http://www.sec.gov/edgar/schedule13D`) | `edgarSubmission` (namespace `http://www.sec.gov/edgar/schedule13g`) | `informationTable` |
| `security_title` | `coverPageHeader/securitiesClassTitle` | `coverPageHeader/securitiesClassTitle` | `titleOfClass` |
| `issuer_cik` | `issuerInfo/issuerCIK` | `issuerInfo/issuerCik` | none |
| `issuer_name` | `issuerInfo/issuerName` | `issuerInfo/issuerName` | `nameOfIssuer` |
| `issuer_cusip` | `issuerCusips/issuerCusipNumber` | `issuerCusips/issuerCusipNumber` | `cusip` |
| one record per | `reportingPersons/reportingPersonInfo` | `coverPageHeaderReportingPersonDetails` | `infoTable` |
| `owner_name` | `reportingPersonName` | `reportingPersonName` | the `FILER` party |
| `owner_cik` | `reportingPersonCIK`, where present | none in the sample | the `FILER` party |
| `shares` | `aggregateAmountOwned` | `reportingPersonBeneficiallyOwnedAggregateNumberOfShares` | `shrsOrPrnAmt/sshPrnamt` |
| `percent_of_class` | `percentOfClass` | `classPercent` | none |
| other | none | none | `shares_kind` = `shrsOrPrnAmt/sshPrnamtType`, `put_call` = `putCall`, `value_usd` = `value` |

- Legacy `SC 13G` has no filing in the 2026Q3 index (0 rows), so the sample has none. This is a named gap.

## Platform checks

### V1–V12

One line for each check of the [parked platform spec](completed/sec-filing-platform.md), Verification
(D5). "Result" means the 2026Q3 sample answers the check. "Open" names what is missing and a proposed
disposition, for the owner to decide.

| Check | Status | Result, or what is missing | Proposed disposition |
|---|---|---|---|
| V1 Serialization reconciliation | Open | Needs Feed archive members. Stage 1 fetches complete submission files only. | Defer. Keep it as a deferred item. This roadmap fetches no Feed archive. |
| V2 Resumable transfer | Open | Needs a range request on a Feed archive. | Defer, with V1. |
| V3 Transport | Result | 500 of 500 responses have `Content-Encoding: gzip`, 0 have an `ETag` and 500 have a `Last-Modified`. | Closed. |
| V4 Submissions metadata | Open | Needs a `submissions.zip` snapshot, which is SEC reference data. | Defer. The roadmap leaves out checks against SEC reference data. |
| V5 Combined filings | Result for 2026Q3; open for 2024Q1 | Each of the 5 repeated-key pairs of 2026Q3 is one submission with one header. The 2024Q1 pairs are outside the sample. | Close for 2026Q3. Defer the 2024Q1 pairs: the roadmap leaves out other quarters. |
| V6 Corrections | Result for 2026Q3; open for refetches and `.corrNN` | 1 of 500 filings (`9999999995-26-002992`, `EFFECT`) has a `date_as_of_change` later than its filing date. No refetch was made. `.corrNN` members need Feed archives. | Carry the refetch of that one filing into Stage 2 (provenance and timing), at 1 request. Defer `.corrNN` with V1. |
| V7 Late-public submissions | Result for 2026Q3; open for the rest | 0 of 500 filings carry `PRIVATE-TO-PUBLIC`. The 101 tagged submissions of 2026-10-15 are in 2026Q4. SEC documentation was not read. | Carry the SEC documentation check into Stage 2, which defines when a filing became public. Defer the 2026-10-15 submissions: another quarter. |
| V8 Dissemination cutoff | Open | Needs SEC documentation, or acceptance times compared with Feed days. | Carry into Stage 2, with V7. |
| V9 Acceptance lines | Result | 500 of 500 filings have an acceptance line. | Closed. |
| V10 SEC-generated documents | Result | 112 of 500 filings hold documents described `IDEA: XBRL DOCUMENT`. In all 112, `public_document_count` equals `document_count`, so the public count includes them. | Closed. |
| V11 Filer Manual tables | Open | Needs the EDGAR Filer Manual. It matters only to an inline XBRL parser, which D2 leaves out. | Defer with the parked platform Stage 2 item (XBRL fact extraction). |
| V12 Axis conventions | Open | Needs the EDGAR XBRL Guide. It matters only to the R19 fact keys of an inline XBRL parser. | Defer with V11. |

The owner accepted every proposed disposition on 2026-11-17. Owner's words: "Accept all (Recommended)".
So each of V1–V12 has a result or an owner disposition.

### V13 and V15 cases tested

- V13, `<XBRL>`-wrapped traditional instance: `test_xbrl_wrapped_instance`.
- V13, SEC-extracted instance not counted twice: `test_instance_counted_once`.
- V15, both 13D and 13G type families: `test_schedule13d_reporting_persons` and
  `test_schedule13g_reporting_persons`.
- The other V13 cases need an inline XBRL parser (D2), and the other V15 cases need amendment handling
  (roadmap Stage 4). They stay with the parked platform Stages 2 and 3.

### Report lines

The report's lines over all 500 sampled filings.

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
   body to its compressed length. Commit `52b1f65`. The full fetch later showed that the SEC does send
   chunked responses (O2, the DEFR14A retry).
2. **Redirects.** `requests` follows redirects by default. Each hop would be an SEC request with no
   ledger record and no spacing. The client now sends `allow_redirects=False`, and a 3xx status gives
   `failed`. Commit `52b1f65`.
3. **A corrupt compressed body.** A gzip or deflate body that fails to decode gives `failed` for that
   filing, and the walk goes on. Commit `970ce75`.
4. **An `ok` record with no file.** When a hard kill falls between the `ok` record and the rename,
   `fetches` gives `failed` with the reason `ok response, but <path> is missing`, so `ok` always means
   the bytes are on disk. The next `fetch` refetches the filing. Commit `4facfd6`.

Found by the live run: none. Each live step ran once and gave its expected result, with no code fix. The
three retried fetches behaved as designed.

Found by the final review:

5. **An ownership document that starts with a byte-order mark.** `xml_document` skipped a document
   whose text starts with a UTF-8 byte-order mark, so such a filing would read `no ownership XML document`
   and lose its records. The parser now removes one leading mark. No sampled document starts with one, and
   a re-run of `ownership` gave the same 6,847 records. Commit `e7b3775`.

## Measured cost

The whole Stage 1 run, from `runs.jsonl` and the ledger. A step's wall time sums all its runs.

| Measure | Value |
|---|---|
| SEC requests | 503 of 1,500 (34%) |
| Wire bytes | 321,729,304 of 5,000,000,000 (6.4%) |
| Decoded bytes | 1,130,618,905 |
| Wall time, `index` | 0.4 s (1 run) |
| Wall time, `sample` | 0.7 s (1 run) |
| Wall time, `fetch` | 700.1 s (2 runs: the pilot and the full run) |
| Wall time, `envelopes` | 1.4 s (2 runs) |
| Wall time, `facts` | 1.3 s (1 run) |
| Wall time, `ownership` | 0.6 s (2 runs) |
| Wall time, `report` | 0.3 s (5 runs) |
| Wall time, total | 704.7 s |
| Disk use of the root | 1,145,878,614 bytes: 1.13 GB of filing bytes and 15 MB of tables |

No other SEC client ran during the fetches (`pgrep` before each run). In the ledger, the smallest gap
between two request starts is 0.34 s, and no 1-second window holds more than 3 requests.

The roadmap estimated 2–4 GB at 4–8 MB a filing. The sample measured 2.26 MB decoded and 0.64 MB on the
wire a filing, on average. The median filing is far smaller, and a few large `uniform` filings carry most
of the bytes.

## Exit check

One line for each part of the roadmap's Stage 1 Exit.

| Exit part | Met | Evidence |
|---|---|---|
| O1: the index table holds every row of the 2026Q3 file, and the findings give the row count | Yes | 302,499 rows, lines 12 to 302,510 of `master.idx` (O1) |
| O2: the sample holds filings of each form type that O3 and O4 name, where the index lists one | Yes | 20 each of `10-K`, `10-Q`, `3`, `4`, `5`, `SCHEDULE 13D`, `SCHEDULE 13G` and `13F-HR`. Legacy `SC 13D/A` enters through 4 repeated keys. Legacy `SC 13G` has no 2026Q3 filing (Sample). |
| O2: each of about 500 sampled filings has its original documents on disk, with a parsed header and document list, or a recorded reason | Yes | 500 of 500 `ok` on disk with SHA-256 and UTC fetch time. 0 parse errors (O2) |
| O3: a facts table holds as-filed XBRL facts for the sample's 10-K and 10-Q filings, and the findings count the filings that gave none | Yes | 45,358 facts from 46 of 46 filings. 0 gave none (O3) |
| O4: an ownership table holds records from Forms 3, 4 and 5, Schedules 13D and 13G and Form 13F, and the findings count the filings that gave none | Yes | 6,847 records from 193 of 216 filings. 23 gave none, each with a reason (O4) |
| The findings record the measured cost: SEC requests and bytes received inside the budget, wall time and disk use | Yes | 503 requests, 321,729,304 wire bytes, 704.7 s, 1,145,878,614 bytes (Measured cost) |

The roadmap's target was an answer within 3 working sessions or 7 calendar days. Stage 1 ran in one
session, on 2026-11-17.

## Sample list

The committed sample manifest (D5): one row per sampled filing, in draw order. The SHA-256 is that of
the decoded complete submission file under `bytes/`.

| Draw | Accession | Form type | Outcome | SHA-256 |
|---|---|---|---|---|
| 1 | `0001493152-26-041491` | `10-K` | ok | `72ecb8c788a63d9b28c0e1ce5fd36db3accc62a856daac37f19578b1e81e9e8b` |
| 2 | `0001477932-26-005718` | `10-K` | ok | `e67b962cc19454668a3f288c0f1355e9878e89e1b14ba371ca3a8ddaa5b7f67f` |
| 3 | `0001683168-26-007087` | `10-K` | ok | `3c8628e9a9a1c5824c2a95bce7ffcb3cc935b5436a1305e2466fa46f1a09c288` |
| 4 | `0001193125-26-381869` | `10-K` | ok | `4561c024d56ac4a683340282e2c74cc343a85573603438449e45bf0a3298bfda` |
| 5 | `0002057381-26-000021` | `10-K` | ok | `ba242ed232d22a0f57cfb3a39557ef2970c5aac74368653c99bafe1590f64dad` |
| 6 | `0001214659-26-008832` | `10-K` | ok | `03ca856ca8ed62587323d349083702da6944bda93b2a9d16c266748da75731aa` |
| 7 | `0001683168-26-007433` | `10-K` | ok | `5e4f659689f02c32312ab586b930d56794623d3c5163b9ddd44dfc5eb6ed7e91` |
| 8 | `0001493152-26-044688` | `10-K` | ok | `88131b323546824579c04dcdee7445a28e7efaea6b2807dccba27670bf79b287` |
| 9 | `0001683168-26-007453` | `10-K` | ok | `7b1f03cd75f39935121824cf9d984a641d9d46756ec0de89028c1c1baa77ea10` |
| 10 | `0001493152-26-033140` | `10-K` | ok | `09dab9ea1c7ee0c528cd7f6e750859f90aaea393b48428ffa238c32b87589c91` |
| 11 | `0000076334-26-000105` | `10-K` | ok | `4265c74bde44e303afbb8830fc0d0c0e6fa269a9eac5396d14220f0fe9f91661` |
| 12 | `0000730263-26-000027` | `10-K` | ok | `80b8af11a8dbd7c8429b4c3c7449401b8b24632d2f2ce502d1f0fc0bace580c9` |
| 13 | `0001628280-26-058018` | `10-K` | ok | `89a3627507bbc4abd278701a76f89dad5fabb984c4069b993f422c6ee892a100` |
| 14 | `0001213900-26-100146` | `10-K` | ok | `4ac153102ab07f5040ab41bdb364f896ba97ec9e16c7617ba54c63b9df192bc4` |
| 15 | `0001493152-26-042497` | `10-K` | ok | `59cc384f4bc3778a1a5a45823bd6628414a36dde54960646422129aa5d863679` |
| 16 | `0001634117-26-000070` | `10-K` | ok | `6fce00545c18a74db879628bf68c575a6d1ae8194975f98af0088b4668f25f2d` |
| 17 | `0001493152-26-034187` | `10-K` | ok | `e02b85e78eee34034bbfe8c820fe458be4dc4becf548ad449e0733971d97031c` |
| 18 | `0000096021-26-000033` | `10-K` | ok | `3695354166f69d0351878726329333329547e46340cf8fde687022a1921d0055` |
| 19 | `0000707549-26-000037` | `10-K` | ok | `01f7eb1aef39daa1cf3d45d8919ea6d174f58fe6965c6381ad36a2278997fd2d` |
| 20 | `0001493152-26-044574` | `10-K` | ok | `81b1e83df15f4b1047fa2624ddde85bf729f4808af6dbd94b4c8dd9e8a7ddbb7` |
| 21 | `0001045450-26-000042` | `10-Q` | ok | `4b1accc28be303ebdca6e2d7e92613921415bb07bc13e33bff6c83a06d145745` |
| 22 | `0001193125-26-322462` | `10-Q` | ok | `1209c1be42a28fcba3c1a6db0016508bf84bd4674e6da7510b841ba5ddc140a3` |
| 23 | `0001836875-26-000073` | `10-Q` | ok | `05f30a22c3bf801c400b4f7d2d4e9d733f6b8092d21c1a2b955b33333f603970` |
| 24 | `0001628280-26-056199` | `10-Q` | ok | `0c2a91974f7e84d6fc88aaf3e253368aee65a78b35e9f9795f4abf25846a0238` |
| 25 | `0001397187-26-000127` | `10-Q` | ok | `5fa7dc1b7e7677a85baa42c7da328fbff31fe194a865bafaa761e2e92c9022b0` |
| 26 | `0001013857-26-000050` | `10-Q` | ok | `1b218dfbcca47e11e86809d7b3cd4eab91a86b3bbaa3ec48da338572d62e4e1b` |
| 27 | `0001437749-26-027318` | `10-Q` | ok | `b8f35bf81d2637f4590556316af8361203cd22232a4a243245128147bac8236c` |
| 28 | `0001213900-26-092608` | `10-Q` | ok | `c013e4bcb7ca0dee6f0b143cea82ad88c8fb9ae660b8221dd3aad47333f0781b` |
| 29 | `0000908255-26-000051` | `10-Q` | ok | `5acbf1b7b442a4bc0bfda12ad493f5f9a2aeacd889a7ca9ec9968ad3f0a3951b` |
| 30 | `0001481792-26-000130` | `10-Q` | ok | `f13e6f5958dba8db91ca3966b9db80f3095ce54131708d09ad5b44129af20e5c` |
| 31 | `0000798359-26-000078` | `10-Q` | ok | `3c5b9e086370dff76f90868d3f490e3c24c829cf89eaaf1d8ff311894d66e029` |
| 32 | `0001193125-26-344956` | `10-Q` | ok | `16022f84ecf0d7c76829f579100dd29b683f311526295afc4ef7bc1ed679bfc1` |
| 33 | `0000029905-26-000027` | `10-Q` | ok | `f11778c4c9f34b82173665a3b3571d7e507d0643ed4494828f50727323c753bf` |
| 34 | `0001628280-26-053347` | `10-Q` | ok | `b0c760b0207bdcae417d7e6889ea8476cdc39b0f21fd166883a0b2dbe4286b18` |
| 35 | `0001213900-26-081419` | `10-Q` | ok | `f4d617f653d1ac062f0578c9a6fb02b749e37a1a14cf2151bd333a87df4e2c2f` |
| 36 | `0001493152-26-038581` | `10-Q` | ok | `c74a52c0f5511f93dd27a477478c5becb75b71cd060b5283461dfefccb19705c` |
| 37 | `0001628280-26-053886` | `10-Q` | ok | `01aa9282236593241d3566a8d6467b17312aff7286cf567b61a9e5f81d5fb565` |
| 38 | `0001628280-26-061160` | `10-Q` | ok | `c4986b74b2d1cbd9280608c361b82e10687dbe814da8e487f5483a45a4dd289e` |
| 39 | `0001096906-26-001354` | `10-Q` | ok | `bdb64547683c3957b76b88e4127d9d8d32e62abdfa8376a42d96f96f56261292` |
| 40 | `0001193125-26-335232` | `10-Q` | ok | `c4812270a6247429e62b28428391b483abb6b1b6edc447f3137824dca573d504` |
| 41 | `0001728513-26-000003` | `3` | ok | `952576bb1c49b85d3a7ff65b763f3a78e4cc460462c6a4afb1a34292429c06bf` |
| 42 | `0001829126-26-008981` | `3` | ok | `5372f8c9ea34c1a30dd2ea67b5184d8834c85a3ce833cca907a3ca9ac6dbb3ef` |
| 43 | `0001493152-26-039878` | `3` | ok | `290d6fc53b39d05bd032bba1adedbba9a4be37b35a2742cf16cf58e04547d42b` |
| 44 | `0001253637-26-000007` | `3` | ok | `61b8fd6099df55fe006409a4b5293f7c85634d14a531154ffc5a2b58acc784e9` |
| 45 | `0001729157-26-000003` | `3` | ok | `1cb2b14c6aab792b242ea7ed4f9858c2115eba5512572750f1812a3634e1c2e0` |
| 46 | `0001104659-26-089867` | `3` | ok | `9035200d956a1ca6451a6e4cf40b91794b5ebaf02045f45ff0c565362049f18f` |
| 47 | `0002148430-26-000002` | `3` | ok | `2f3e6f61647ef65efa25a1f7d7ae4000677acab2c9f2789d76917db118c0c292` |
| 48 | `0001193125-26-309035` | `3` | ok | `e291987fa1cef23a538046b2ced9a57b20d2c80013760ea399025426632307fa` |
| 49 | `0001749723-26-000153` | `3` | ok | `88d3821bad7cc7a241959e88f14e7a21f36a9353e3f40b3ad075313013150eca` |
| 50 | `0001193125-26-383637` | `3` | ok | `c11f240ed11fb18233f0977b11207c13e16cb695d71322cbced9dc7d8564cc89` |
| 51 | `0001829126-26-007220` | `3` | ok | `01ed2241aa6f90c8ddafee396b03df3ef4c2f5281c0df6941ba6386f212073a7` |
| 52 | `0001409453-26-000003` | `3` | ok | `88ddbc37d24d2d0c7732a7989ced3dcd526658129e98de0ba24afb8ea43a0321` |
| 53 | `0001213900-26-083553` | `3` | ok | `f0670d8e60125d0715836c2ce0ab25c8e326c5212fc9defbbb3e0580d0bc57d1` |
| 54 | `0001231919-26-000745` | `3` | ok | `021a52aba1003c550a984445e4e4d629789cccc8c9823e513fecf1d6300ffba6` |
| 55 | `0001193125-26-318368` | `3` | ok | `aebe5563965e8b0af5469b36dd35337e7476d81dec8ca3a50c6cb8728bc68873` |
| 56 | `0001104659-26-082588` | `3` | ok | `81c28518808fa5ea161c20357af5bac10b4445b4229eb76f3cf3c0c1b4752a79` |
| 57 | `0001729835-26-000009` | `3` | ok | `d2c02536e41516cf3e5a672a4164a217d6890a96707019a6d6338cfa1b467ff8` |
| 58 | `0001104659-26-095126` | `3` | ok | `c793acf48324f8cbbb021097cc4d9f4b317993c9a706aa33e76bc3bc480e22fa` |
| 59 | `0002153761-26-000002` | `3` | ok | `2fd483417b5bc37e5d58bdf90ac779bcbf51e8451703a6136499175b071ea1da` |
| 60 | `0000894189-26-025167` | `3` | ok | `97af7286e414662a04b982400fc9b4b8c9ebb616f139fda747ea555894d49b4f` |
| 61 | `0001700537-26-000016` | `4` | ok | `8adbfcf56cdca299fc2539d0ec4d1e4e54edf98997eb5ef1a3dcbdfa95679a80` |
| 62 | `0000905148-26-003534` | `4` | ok | `9c2c667191a4f58583e3da32770337b93c8c8a09fdc350ccf7b9c25d4a494b46` |
| 63 | `0002074521-26-000002` | `4` | ok | `9f1d8e5e2788be5b35034c0a41a19cc2e57765dfd4f2455dcceb904f3d21062b` |
| 64 | `0001437749-26-024321` | `4` | ok | `aab6e0ea649e35c51b71d65faf397c6dec959927d0d2ecc99e7d748f185f5e57` |
| 65 | `0001437749-26-024664` | `4` | ok | `790a16d92359835e59ab67191e3d01b79e099d7701f3feeb9672cfab9e541da3` |
| 66 | `0000080661-26-000257` | `4` | ok | `f48b5fc1e47e03a5211c46869e2f621f569abaa2e49cdd73baf50a32057a9ec2` |
| 67 | `0001596532-26-000158` | `4` | ok | `283aeec74830428cc2bba3723e787d3da008a6e6f58f9db55fdae5f631cf6245` |
| 68 | `0001193125-26-409201` | `4` | ok | `3154e31cb5eb06e77d95a1e3b7a1348d4363b71a550a7994039d606fa0bc5fe8` |
| 69 | `0001628280-26-048803` | `4` | ok | `01c03d03eca3160efebd57aff258f8d23be311e85a38890cf56fd814f931b931` |
| 70 | `0001437749-26-023780` | `4` | ok | `271da637a8a6bca8f230c32f46e90781817c6b96c343f680bafa8a8d7757959d` |
| 71 | `0001628280-26-047997` | `4` | ok | `f3640dddf873bdbe5fc4645fc88077384b1aeca966062eaaa26136406b40690e` |
| 72 | `0001193125-26-398085` | `4` | ok | `49c17a8442f50b9db50b15a600127028163e1ab05029d7bc35178c513564727a` |
| 73 | `0001040470-26-000207` | `4` | ok | `96e5650697c3314c9ebfc03f3090b5d541669fff1c9b6a6bf13e2ee6ab98156e` |
| 74 | `0001193125-26-310405` | `4` | ok | `c76afc8d1e32d954dfd71e8cf22e1e362e8ffa93c7266d3d3a2f347d065e823a` |
| 75 | `0001628280-26-060204` | `4` | ok | `f6392c37e2f8f7d42f4ec8badb1d22740a55c4f9d78f9d077532ca8cbec7755a` |
| 76 | `0001389308-26-000002` | `4` | ok | `4508ef8792fcd9b41401b6151549da06c40de3e82678ebea3e6c5ba5edc8ff0a` |
| 77 | `0001840706-26-000292` | `4` | ok | `2b77cf923d30269b4c2559a7d0cfca6df21735a50e9ab889974a565017791f77` |
| 78 | `0001963980-26-000012` | `4` | ok | `4831c5d8ec4c062aef5f029f5ec4419ca3468f4cd5af04c596be3304b05e11e5` |
| 79 | `0001437749-26-029483` | `4` | ok | `b8d8353a9ae2d74a57a0eafa33c5659fff83d659f3f3559799a1aa3ebec07229` |
| 80 | `0001569832-26-000002` | `4` | ok | `0495aed2131bc482696c85c18f708ee950a7d43971825e69f85870e4bc83b80f` |
| 81 | `0001493152-26-040857` | `5` | ok | `c83244fe2c23abeb4b3474114c2d883705271ef675e08f09d9b1946a8ab867d3` |
| 82 | `0000310354-26-000049` | `5` | ok | `223b6fbcf0b0232ffc81f77d4702fe4811b4d98ad58bb4704939a562d035784e` |
| 83 | `0001437749-26-027005` | `5` | ok | `b8134ae33e9a5b24f2750172f711944bea7f516ca71e4201090f951f612a625f` |
| 84 | `0001225208-26-007055` | `5` | ok | `7b225492930b305b556ee0b0484780c6bddf89e0195e3716c1e5e58ddce7a53b` |
| 85 | `0001493152-26-032664` | `5` | ok | `1ba9167a88a26e8ed369de871566d0e40447669d5aba4b370ec436a13f02f60a` |
| 86 | `0001493152-26-032666` | `5` | ok | `f17894d1f339ed39490b60e7cf490f25df0a3679373b0c26e1903b3c814bd1fa` |
| 87 | `0001493152-26-032728` | `5` | ok | `c66642b02bff3df5c7651ec1c0ca64cfd552d572e40fc1cc78c71982e2a33c2f` |
| 88 | `0001493152-26-032668` | `5` | ok | `9f23afa17f1fc93d1b0ecdb7e1ba9fdb4eaa98c6f5d2c3e70991e8e507fa1542` |
| 89 | `0001995337-26-000002` | `5` | ok | `c88d1759ecfb284d661de41a2084303fe44442750d4558379497543b9dd9c3c1` |
| 90 | `0000310354-26-000047` | `5` | ok | `1efd9c676c32d632afba22a18fc79f385993228e5b639ec16c583c4b7738c5cf` |
| 91 | `0001214659-26-009586` | `5` | ok | `d2e6dcb8d4ccb180b4881aa403dd1717b18b86b35023db2f24f91efc09ba6039` |
| 92 | `0001193125-26-300862` | `5` | ok | `0f1091758b0f4c529f3373110b97aefd650e4653ec322aaf7718684fecb3a060` |
| 93 | `0001214659-26-009585` | `5` | ok | `99e6848d25f1404a9d7bb764e7205f92dd7e99b5eb11f9bcfaf3015347cbc0dd` |
| 94 | `0001214659-26-009589` | `5` | ok | `5cdd636e1c37e9bd80db69d972d1575ad0bb3a08dc9ae814eb683d2b322d7839` |
| 95 | `0001214659-26-009590` | `5` | ok | `fa9a33b707771aaa28b9a31aef9f0e1595f700b063e4facd4bfcb53e6a72a229` |
| 96 | `0001493152-26-032671` | `5` | ok | `f96dbfad365b5ee0c26f41cfc95d216c49b529e610191a3747e6e4afa3843eb0` |
| 97 | `0001628280-26-046511` | `5` | ok | `e311823634d40f26f4019f5c6925946f8cda1399b76857966f043ac031c99dd5` |
| 98 | `0002131351-26-000006` | `5` | ok | `e715969c2c55666fae55549d90f39203661347ba571ef635ac001590d8961acc` |
| 99 | `0001493152-26-032674` | `5` | ok | `7b645cb4281dabcf197e1695d62942da2200c577503423bd1b5b567598ccb5d1` |
| 100 | `0001214659-26-009587` | `5` | ok | `14ad6e1800dbfaf5c16ee7c2f86efd06f7b98fbdad4bd28a969ea3be200621f7` |
| 101 | `0001437749-26-028927` | `SCHEDULE 13D` | ok | `df39e99780e047c30ce57b4415c3111eb58c3ff3eb47e36b187387c2caa86f60` |
| 102 | `0000897069-26-001544` | `SCHEDULE 13D` | ok | `4617d099e1bbea3d30577bd1225dc9927ba9d82b64328a26a1eb678e9d576152` |
| 103 | `0000912282-26-001247` | `SCHEDULE 13D` | ok | `4d1a1a92000d549e6cc7ed237c21076fe8849038fa14193f6865328ecddf0b70` |
| 104 | `0001193125-26-303495` | `SCHEDULE 13D` | ok | `7fbf2b335ddca9c3b7630f4f6616c3305d99c1176ef59a33e1ea1233d53f3035` |
| 105 | `0002147707-26-000002` | `SCHEDULE 13D` | ok | `18d97a95c9d2424b4b6d643e93ca6422c96e6f7890e2c2b164f6b513d9d9548a` |
| 106 | `0000912282-26-000961` | `SCHEDULE 13D` | ok | `4b9cfec5bbfa105ddf83efc8172cb09236fd1476ca7cc1aebd8b4ac5f42a6cdf` |
| 107 | `0000945621-26-001163` | `SCHEDULE 13D` | ok | `5b3913c26ce582af35614cf66d088dba6f0c5bccfb26ff09032cce72bb64f68f` |
| 108 | `0001493152-26-035149` | `SCHEDULE 13D` | ok | `08767e3f82db63df1b9a323776cd51d0b48494f1017b7e1938d22479b4b239e7` |
| 109 | `0001493152-26-035145` | `SCHEDULE 13D` | ok | `1946c08f82d9d3c4e7a1687d70b9d31a2b8aa5ceccfa085f6ee405f885c7e7fe` |
| 110 | `0001493152-26-033502` | `SCHEDULE 13D` | ok | `d98825fe1ecf4cdedf322a8edf7b67410189d836ad4198a5672bd540649929ce` |
| 111 | `0001493152-26-039482` | `SCHEDULE 13D` | ok | `dbfc3215d1fa2f1d5fc03ca65c4abad4705648b13a78adb1e827c92c26a46f33` |
| 112 | `0001104659-26-084244` | `SCHEDULE 13D` | ok | `79b8033306957c096312a25c61268e3ec4f41108b7b347fa1118e7a955a71ef4` |
| 113 | `0001213900-26-090217` | `SCHEDULE 13D` | ok | `68e05f16968242832820af6bc7f12a0971b70e80d803ab136b9dbc15465c5af8` |
| 114 | `0001213900-26-104723` | `SCHEDULE 13D` | ok | `d2545c0657502df92381619fb0a23f2a936df16027fdd61c95ddeab1e83ba4d8` |
| 115 | `0000921895-26-001957` | `SCHEDULE 13D` | ok | `d0c15680d18861b3ff09c5ddef9fe00890d2c2b77ca0bb284c63f8f4e4068d78` |
| 116 | `0001477932-26-004692` | `SCHEDULE 13D` | ok | `b69c7fe080755dfc154b5bbb3c5cbd01789c717d709920511486aaf569f0f6c1` |
| 117 | `0001477932-26-004693` | `SCHEDULE 13D` | ok | `754a34fbc18934bbe521e0a0ed43b0bfce4272fc8caf1a4cac7d59a7a2ba3618` |
| 118 | `0001361570-26-000017` | `SCHEDULE 13D` | ok | `b26d83125219b7a54154c8801f38ce2ea67f49e49d76726fbb9e71e6105ea59d` |
| 119 | `0000902664-26-003832` | `SCHEDULE 13D` | ok | `a77023f93a0fc2f293e021a021a48f129fb3e84a43f5523411b2fdc819e301df` |
| 120 | `0001062993-26-005116` | `SCHEDULE 13D` | ok | `bdc907c5239c102d82778eb3eca8b021d191007ea3b52ebb925e0ce8bf64df3e` |
| 121 | `0001104659-26-097317` | `SCHEDULE 13G` | ok | `17e10553a4e96cbd14bf29eaa48292edb0c31dd912fe4371fb9741403df08892` |
| 122 | `0000093751-26-000557` | `SCHEDULE 13G` | ok | `7cc82b952127322ed60efa3c9082f1b81fa0ac05c204674147b59ec6e6c8b254` |
| 123 | `0001844495-26-000028` | `SCHEDULE 13G` | ok | `f3b02bfd64bda3798058e0874aa28e431e625ca9781f74872b6571c49350c53f` |
| 124 | `0002100121-26-000871` | `SCHEDULE 13G` | ok | `789c405c8508f4c4961ceabd29690c9dd022d78e8025976d9920073e19540151` |
| 125 | `0002012383-26-002912` | `SCHEDULE 13G` | ok | `93454828388eda85100f40ae126f446bb67b6ee28ce653cdc9f68a0108e0e241` |
| 126 | `0000919574-26-005354` | `SCHEDULE 13G` | ok | `751d11bf4ed0538ab368ed9ebff6250e068c91efe6736a3469cb2e3a2bb602b4` |
| 127 | `0001214659-26-009898` | `SCHEDULE 13G` | ok | `a2ec1cafc90a222cf14d0b9950251c1cb60dfd86413c272f23a5679a1f3709e4` |
| 128 | `0002012383-26-003142` | `SCHEDULE 13G` | ok | `0dfb40bda36052a9ac1a7e94a1397b1aa2fe153ef466806c9f565fd5dea442ef` |
| 129 | `0002146263-26-000001` | `SCHEDULE 13G` | ok | `9af5916c2db8491c0e9b0be5b4d85493982d4ae126a95ebbeadce086af2247e0` |
| 130 | `0002012383-26-002835` | `SCHEDULE 13G` | ok | `2ae50277fa616d8a07806e8426c8d3434ac28b1494cfdcd2f1dd951c82e0334f` |
| 131 | `0000945621-26-001067` | `SCHEDULE 13G` | ok | `f81e0e2d31a7fd3e05f5d1643d31f8f46759797e52c5b6606412fcb4767daa75` |
| 132 | `0001398344-26-014652` | `SCHEDULE 13G` | ok | `f749dc7d007ad2bda3915ee711d81e62e8f5a87ad4875b5d30f1ef53c21f9621` |
| 133 | `0000814375-26-000043` | `SCHEDULE 13G` | ok | `53574ec9f27a13d21c03012a72280c927969a87c762a1dfb4dae6a1af11d926b` |
| 134 | `0000315066-26-001954` | `SCHEDULE 13G` | ok | `492332f86fdbc53153402d02d15f836de386b2c2f4a829ab9d65fdd3f95c510e` |
| 135 | `0000886982-26-000518` | `SCHEDULE 13G` | ok | `f2af14d3e6e2a0a4ed8bd0dbc99647def18b9656c3e11e8f5fb7d34b64d8a186` |
| 136 | `0001104659-26-098450` | `SCHEDULE 13G` | ok | `0cca62ea28e0340c0849a6d47efd7b639e92ed6b8bc294a60de83a9609935d9f` |
| 137 | `0002012383-26-002584` | `SCHEDULE 13G` | ok | `1095b58e96bd4fd15372a41d2ea260a327159ea396591a26f25ee535f2687181` |
| 138 | `0002100119-26-001476` | `SCHEDULE 13G` | ok | `4f7d8ab1bb195aaa3d676301a76de6f52a0cb6fde79dfaf5ff59314cbdde3993` |
| 139 | `0000354204-26-000775` | `SCHEDULE 13G` | ok | `e5d6a5e4b6bc9a9dc6035e8835742d19712020d5f46ff52857d059efdab71b86` |
| 140 | `0001446580-26-000094` | `SCHEDULE 13G` | ok | `ef3754f80b7ee94645cf614c227ccc1804c74611107d83008999bb766889c306` |
| 141 | `0002046823-26-000003` | `13F-HR` | ok | `9e254dfb59af47db29fb072513d97e9fe001eed8b55547e82872aba208278958` |
| 142 | `0001214659-26-009680` | `13F-HR` | ok | `8711ddec671e4c898ab66a26a78597817d468b45598d9a9797aadb520f72702e` |
| 143 | `0001815467-26-000002` | `13F-HR` | ok | `70bfbf9a1a263a1dcd60f53e28999e80b1b2c941fe4fcc98ff247b574ff15311` |
| 144 | `0002137372-26-000002` | `13F-HR` | ok | `c3d789a5d64e2965ee185630174f51e4902a4f9cada763a960f16c74655526a0` |
| 145 | `0001062993-26-004420` | `13F-HR` | ok | `1647be5d9c28914721138bb876025c269669ff9c3f44a01ac31f44e2565d97e9` |
| 146 | `0001901865-26-000002` | `13F-HR` | ok | `dab38def0d56e40d8208b5ab0c258db74571c528a1005a3de5d98d5f4314a967` |
| 147 | `0001104659-26-096450` | `13F-HR` | ok | `1df9f33770aa01362e328662af1dc211d9001698b0a7ae25a1afbb5ee2ca871e` |
| 148 | `0002051705-26-000007` | `13F-HR` | ok | `712208da2dd40dc8e662c9f77f8f8a3be6bc946c320dd776525d10f0afcef1b4` |
| 149 | `0000921531-26-000004` | `13F-HR` | ok | `bbc401de5bb167ae2adbbf88d6dd78932590cb2ec61eab70ba23d5b75c930981` |
| 150 | `0001213900-26-089660` | `13F-HR` | ok | `4c51719c80f27f74ebd5c616f3ecb8cf5beae07cffb2b93ca2b6598677416cee` |
| 151 | `0001763121-26-000008` | `13F-HR` | ok | `e5464d565511adeb22419d928165c5d19e03a1e44ac65856e6a8d171a87a583b` |
| 152 | `0001051359-26-000008` | `13F-HR` | ok | `d84c4276d6932c06bcbcadf86b99609407a642c4d214555a55776c2b3bdbf2c7` |
| 153 | `0001119032-26-000007` | `13F-HR` | ok | `d38d4a90799f1bc63f3c88d49e26c92b5ebb919dabaee808f3cc97f49de20fe3` |
| 154 | `0001790525-26-000003` | `13F-HR` | ok | `946fdfbf13f19623934541bfc880145a65bf760d3b6d8674d5f5f0ba5d6da31a` |
| 155 | `0002139665-26-000001` | `13F-HR` | ok | `6a0919db221c218c16935d2aed73c27ddbc585fa2dc083261313286acf1a5f4a` |
| 156 | `0001088859-26-000004` | `13F-HR` | ok | `0397625ca4f1ff3bd6291e96748aedf0aad271aa0a5e92a7eb94c81634a50a19` |
| 157 | `0002072160-26-000008` | `13F-HR` | ok | `15e195a23010ae231e217af0a660ea6e6e45c413ddb0fb778c500394549158c7` |
| 158 | `0001426960-26-000007` | `13F-HR` | ok | `28271a77138768e988b54c9424941fde8a9f5c005815493f71f9b784686c483d` |
| 159 | `0000895345-26-000360` | `13F-HR` | ok | `c134589dace2db4598fa13bf9eb9be78105155640fdbb7109e8d7fe268c7ac56` |
| 160 | `0001398344-26-014319` | `13F-HR` | ok | `aca3fdaa3e2562e1fec8a7e3f67cc8184ea4e47d7f0de0b49baa887739b5c23c` |
| 161 | `0001104659-26-081696` | `SC 13D/A;SC TO-T/A` | ok | `0b3d9ffd0a1f89ea491dbeb0bcacf4de6682926ed7dc4c149b04f93246212382` |
| 162 | `0001104659-26-081818` | `SC 13D/A;SC TO-T/A` | ok | `6fe32576fb60d19a3e498acc0a2e8114c2ae4e7456557a6d7e241fe4578332a9` |
| 163 | `0001104659-26-082921` | `SC 13D/A;SC TO-T/A` | ok | `1eb58c15d77b349f3f3530f8b80ac8bc30d6da7ecfe49cca50bfeea838eed0a8` |
| 164 | `0001104659-26-086886` | `SC 13D/A;SC TO-T/A` | ok | `b64ab6b4ec362efba43561984cd86cc5dfd84863465eb99423ca523c747e8401` |
| 165 | `0001654954-26-008429` | `SC 13E3;SC TO-I` | ok | `ea5b22eb84804ff62a61cb62eebd01d923160c042838b00db71b48056b370362` |
| 166 | `0001776865-26-000024` | `4` | ok | `37007c3f829c825ba978700996693d597d665192e181ce5967f1908d31bbeee1` |
| 167 | `0000892251-26-000099` | `4/A` | ok | `5051bf7bd82a610247437f9c7e4c7b0df8e237b0f142959a46169ca2df716e52` |
| 168 | `0001654954-26-008365` | `4` | ok | `5f889b6f3449127adcd9569f79317fc175de2a8e6a4b57d1132f2d546dfe10fd` |
| 169 | `0001213900-26-084296` | `8-K` | ok | `cccbe5fe3d6001ea1ec713b3c551e1888fb83c58de913923d8fd91c87e0a3897` |
| 170 | `0001114446-26-004974` | `424B2` | ok | `80d703be3414dc117961618f129ac7351c1ea0151c4aaf7eecd03ed37fc0e78a` |
| 171 | `0001445546-26-005062` | `S-6` | ok | `c16d07fa9e4cea6178bad541813cbc7ba3bfd4f3344fff13866ac840ff992326` |
| 172 | `0002140886-26-000001` | `D` | ok | `1882cb5841b74ea864d00281186f0ac91c7b010299b0f03c9684955532df7443` |
| 173 | `0001417835-26-000237` | `CERT` | ok | `afc17809eb287c0e3a9e7f22eb6ad987e474f23ad31adf49a7b0d24fb4d79115` |
| 174 | `0001754960-26-000719` | `13F-HR` | ok | `17a8f624ec48041cd635fe31daa04e7f2f98acccf8aa54bab07f57ac0a198f7b` |
| 175 | `0002152957-26-000001` | `D` | ok | `0d23bee72c374f9478853aa46c5edb6131645fa42762419c8fe07da426c21c9f` |
| 176 | `0001999371-26-016142` | `497K` | ok | `4dc55601495520ad6a9cc2f70fcaf21b1681cb8649a0170f0ada9a8e8ab4999c` |
| 177 | `0002143919-26-000001` | `D` | ok | `f19ed9737e580b0d6144c443153bda2524f481b763dec5e41690a597d77b875d` |
| 178 | `0001213900-26-085008` | `424B2` | ok | `5bba98bf013cf3e62fb4cad1386eb268671b2e6517d38ca588e93d8f8eb56c21` |
| 179 | `0001193125-26-314195` | `8-K` | ok | `73a5f34faba2d4dca4ae9eeafeefd7dcd06af844c393fb5607ab1bdd8adb0e3d` |
| 180 | `0001410368-26-088532` | `NPORT-P` | ok | `a6f10722ce2c24940f18a56b9b53495a1d5c607de0ad60e3a485c1141bbc1170` |
| 181 | `0002152690-26-000001` | `D` | ok | `2204f0dd60b2ba8081de9a1b5f1767ffd943e408c60b8f6c1cdae8d912e4f54c` |
| 182 | `0001437749-26-030234` | `ARS` | ok | `e8a3cf09d1cb7bc0261a26351fa7e84624f2448a8306d70facbde9f7db947a04` |
| 183 | `0001872856-26-000280` | `C/A` | ok | `d48fb22792b4311188eaa25bd197f76fe211691c43bb30f4c82f718e74f33427` |
| 184 | `0001918704-26-018993` | `424B2` | ok | `4da8c813d61040f0b3d897873c75315ed08eefd9c38c23b24de951825e847d0c` |
| 185 | `0001839882-26-034964` | `424B2` | ok | `7480c35397a1d32898d0645eaa88c357c14fabddc3f914abb0f402c8c1f2037b` |
| 186 | `0002011342-26-000004` | `N-PX` | ok | `94bac9015c4e5e0c70ab8495ac6b91551a8a263d98891f629243d537aa7a70d7` |
| 187 | `0001888524-26-012344` | `ABS-EE` | ok | `19c0a69beefda595a9cdb2f0ee1ddaf97b808247b541a58bfe900a4557cce07e` |
| 188 | `0001829126-26-009544` | `4` | ok | `8db8957b1e714d18b555b1d5ea7a5f08e91451314dafe507daf15750be7fd1c8` |
| 189 | `0001839882-26-034620` | `424B2` | ok | `c9571d9b9da6c7ce4824f7ef2b5b27be629f8a3677608a3ccc2da161482d484d` |
| 190 | `0001193125-26-320126` | `NPORT-P` | ok | `f2084642dffd52e73b268fc8828106c37c5e92f8d31e2ce99c0cf939936a2b59` |
| 191 | `0001140361-26-027108` | `424B2` | ok | `6982b1075ab5353da2548204b28919f6dccdc6f8175ea83208498bf56d6f87b1` |
| 192 | `0001062993-26-004609` | `6-K` | ok | `e94fac8e6fdfe2293160eb4cb764107b717744f7c655a4eda0fa02c51e752e9b` |
| 193 | `0001493152-26-033670` | `1-U` | ok | `b4660c2292f5b623599b045d2a3c2141c772bf34075d12b7fcef20d4a28e2808` |
| 194 | `0001999371-26-016103` | `497K` | ok | `5395b5513b0882e0ba728d7aa6a03c064a012973b300a63b6653543c616b2479` |
| 195 | `0001839882-26-035472` | `424B2` | ok | `00578367875c99377ae20805f26c8607ec72f8293415bd0ba66d278579649dfc` |
| 196 | `0001839882-26-048308` | `424B2` | ok | `9ec7aa79c843c6045b2d13cf3622be3cf7a19eb3fe780839299af7cb87a37401` |
| 197 | `0001846639-26-000005` | `13F-HR` | ok | `32fb285dffbc3aac53b3e75b79a435dc9156049c4587587e46ff8bfb87d234ad` |
| 198 | `0001654954-26-008086` | `6-K` | ok | `96ab0a5335fada508bc6200c4a383dab96d4abc2a3d22232f653861d1cd101d8` |
| 199 | `0001648256-26-000008` | `4` | ok | `7c5663b1b01bcb39f6dc7dbc0fc1bf5271946e127b42044281288f45d50054f3` |
| 200 | `0000732717-26-000288` | `4` | ok | `6ce7c19a257183eefd6423da5dbb98e9aed30fa324d3e1a1109aab7775b1e842` |
| 201 | `0001493152-26-037731` | `10-Q` | ok | `bdea37d40eef7db3c314212894e123e0a694c28450a661c01b760dcb1e7ba16d` |
| 202 | `0001437749-26-024249` | `4` | ok | `4c1f2401ba0910740872ce4733a12aa76fd30afd8b04fb749655509205297907` |
| 203 | `0001666700-26-000055` | `8-K` | ok | `9bbfeac96bae0ca2ac897c57fde2026716370d55368de9e416d1daaf56a77598` |
| 204 | `0001114446-26-005913` | `424B2` | ok | `ea4dbaf48d578fddb1a689b53451845e2724b8e75bb49b2a258e4fa079fd1649` |
| 205 | `0001829126-26-008972` | `3` | ok | `a219cb551234b9c00eb601c733cdbbc9d094633c8d0cd05d6b4447079b914f5c` |
| 206 | `0001918704-26-024844` | `424B2` | ok | `3ceb74605a4fd8615cfffb2655c4f581ffc1ffcd287ab99692574115f3a195cf` |
| 207 | `0001104659-26-096397` | `13F-HR` | ok | `9dc5c4f734fb2ca26cd72ef0d4669f8831f851c787dc0c51dbbd71fe646f36ec` |
| 208 | `0001918704-26-026948` | `424B2` | ok | `9ed394960ee62644fc14d6f9df978d855ac23dda5e9277919781aad66439954a` |
| 209 | `0001081400-26-000284` | `497K` | ok | `bc4e8f8500773837c6cfeefc8c3943badedd01ceae0602b4eebb245266846c3c` |
| 210 | `0001918704-26-024221` | `424B2` | ok | `de28d4cdb3c888ad1b860f50255cffcca7bb78026177f76088dc4152741edba6` |
| 211 | `0002097390-26-000006` | `SCHEDULE 13D/A` | ok | `d0ec31fbc54d15da29d22ef5ad20fbb4381fd0ced28f06a8f955b95f8e1ee584` |
| 212 | `0000929638-26-003730` | `10-D` | ok | `26143f748862d0cdbf5d35245b372e70ac5b73dc8d38c5423e93b2a420ef3b99` |
| 213 | `0001554339-26-000002` | `4` | ok | `9dea1be083905687926b2e946ba825925f31f3d6f21539aa77807c598f5bd812` |
| 214 | `0000030146-26-000390` | `497J` | ok | `b18dfc049e53a4e5f483d8a1bb2d1bf18b3df52d7262a023e3a6cae98bc50ea2` |
| 215 | `0001564708-26-000187` | `8-K` | ok | `6057d3da7fc91e029c2097dbf03e514f45b6b4fa128e8405eddaff25f9a99511` |
| 216 | `0001231919-26-000749` | `4` | ok | `cdf9cef1a21843d7df1b0c6de9224caf61a2b0da555571ea084321a1767079b1` |
| 217 | `9999999995-26-002992` | `EFFECT` | ok | `740252a6178e54e6121c7701084949adabb113f5d002d00814ca9ec098f431f3` |
| 218 | `0001213900-26-098236` | `DEFR14A` | ok | `ddd62cc174b3ecfad19fa2f861c83900c788e85f0ddc47005552c68d6b00dca1` |
| 219 | `0001104659-26-107124` | `8-K` | ok | `be1d6206b90e6716a10dc6ec25d0c9cad859f2fef8e843e3677110c15d0cb023` |
| 220 | `0001398344-26-013536` | `497K` | ok | `430e444f1d2712e469a2c2fb3474b9d4272e88513aa227c63e9525e2c74d1989` |
| 221 | `0001654954-26-007586` | `8-K` | ok | `489c526ea5ff22e49ae8d799238edbe4d033a010e1d2440622065cca347038a6` |
| 222 | `0001493152-26-032502` | `6-K` | ok | `27ef08ce66501fc441fe0df477f4833e1002aac4bbedb024e65c0605587012dd` |
| 223 | `0001171843-26-005955` | `6-K` | ok | `314869bbe5859bff6f2b8a85e59c325ce23eca9f7bc10ef93b707518227c64cb` |
| 224 | `0001628280-26-061318` | `8-K` | ok | `ee94683bc6b371f1e71f473ccf54b34fbd398bfa94acb193cbe63916cdbb739c` |
| 225 | `0000940400-26-035667` | `NPORT-P` | ok | `ad686c0b7b5503e3b7d06c397b6f94a56538f9e5cfacb2d708c07637113ad1bc` |
| 226 | `0001839882-26-035807` | `FWP` | ok | `9a6d53a459042726b79d21f9209a59e36dd5e9df60610a3d5efd1e451ef152cf` |
| 227 | `0001410368-26-085909` | `NPORT-P` | ok | `2c9916c7bec3346470adf19d595c3e3c2afcd6ce872ec46c0c5986d745cd1ba6` |
| 228 | `0001410368-26-099272` | `NPORT-P` | ok | `8b30d60f3a3fd6aa57514bb1cb95d25ffbb8e61a91e435ec86aca3a55c289300` |
| 229 | `0001628280-26-046743` | `4` | ok | `38b298a100a0ca733851190425ec704e45deeb62bb79ed65225932522c52876a` |
| 230 | `0001437749-26-030229` | `8-K` | ok | `428b75421137766cd10f81bb065b5804968551887f17d9feecc9bde389f63fab` |
| 231 | `0000919574-26-006523` | `485BPOS` | ok | `74baadb059cbda3e1ea1b22b7a87671b45a538fe7dd043f146015a19d216d6c7` |
| 232 | `0001628280-26-051492` | `4/A` | ok | `1705a551fdeb7dfdd089fe414d91e6d15924879306a3fca048366c8d69e712a0` |
| 233 | `0002146534-26-000001` | `D` | ok | `f46291bb1f0c9756dfc30811493a1bf26d15f53b660605991662c7c5e82659a6` |
| 234 | `0002148169-26-000001` | `D` | ok | `56c53d01bbf6fd44877a4a81253063fba0cdc68ed05dee5a96f8101ad971dcb1` |
| 235 | `0001213900-26-104579` | `D/A` | ok | `60c69783dd00c10a6fecd136444d845b6067eb8246911cbd1ff0afe33a6a8c0e` |
| 236 | `0001935243-26-000006` | `13F-HR` | ok | `3513fb8859a0a86d5684f77beb195a1b84f5f5a5e8d552be2c0bf182e7af8474` |
| 237 | `0001330399-26-000125` | `8-K` | ok | `d9fd4bbdab45cd3144ccca22f3ba8c7745d9befea80cdb185db32181f0dc0e39` |
| 238 | `0001104659-26-105051` | `4` | ok | `d6935860beb517c7e04199a030410c53b7347830537874ff803afbfcf67dfaf2` |
| 239 | `0001193125-26-302773` | `N-CEN` | ok | `936efede0c35bee7908696bb3837b6a68cf7375db0663cf68f53e84a38f13717` |
| 240 | `0001839882-26-033875` | `424B2` | ok | `03d61cf1a293bb69fe78124531f9f9416010e0ebf5c5d901375ebffb58305278` |
| 241 | `0002082903-26-000032` | `ABS-EE` | ok | `0f8aaa9da93b70525f9a71ea6fc0a2484519fbbabcb56e173475bb97d134fd63` |
| 242 | `0001104659-26-103159` | `N-PX` | ok | `25b8e3d8209d8c62c5087952d5f8116e474079d4e7ce61526e9df6e52535cfa5` |
| 243 | `0000919574-26-005912` | `AW` | ok | `97c492d0e83905536988d9ebf2e5b0355c32135db28a57a4024421540e49ed3c` |
| 244 | `0001532388-26-000004` | `4` | ok | `09de827547e59543570979ee1895b40d68a8494672ed03829785e51bf7c63993` |
| 245 | `0000911916-26-000051` | `D` | ok | `53a6093075d8d60f7b70ba2cd6df77f4af88eabdb5385a23a4cf564253e90dd9` |
| 246 | `0001839882-26-046267` | `424B2` | ok | `cbc9c194bead62f3efcc90a7914f2bcd75ca8e4d33710e5319d9a392a3658ee1` |
| 247 | `0001410368-26-100654` | `NPORT-P` | ok | `e74dff2b4cdde9c570d059aa7dcd3301e5429b2223bfe88174aff44b6079316c` |
| 248 | `0001493152-26-042311` | `4` | ok | `949c57c8ad88fc0b22baa277582fd544a7c9f7e960ac5f5151466d19128451df` |
| 249 | `0001837607-26-000061` | `8-K` | ok | `de515c6b7a9d20b7df24a445c3b427e54414015a3d5e6e93b0b5a2b026860470` |
| 250 | `0001628280-26-062057` | `4` | ok | `6bb61a2c9772a0ab7c624b161f62088b7ec997f7d2ac79c770e52c2ed8ecc447` |
| 251 | `0001104659-26-108476` | `497` | ok | `b4cc3d445c22baa4a9763bd3a32e395cb8ac3f73b4c37c8ce2c325a1d6026bfa` |
| 252 | `0001214659-26-009129` | `424B2` | ok | `d0fff20d98f706c525b165be4ff67c0ffd914b438db261049064778b636196eb` |
| 253 | `0001888524-26-014352` | `10-D` | ok | `e1458d0927103f604c537024c16eb089dc221ba4f25d2ed34122fbf0ca437eee` |
| 254 | `0001977454-26-000250` | `144` | ok | `f8cd6c8237b575fdf9da5af26673f719d6547f47f6a23723e0d2c6ccf6b43764` |
| 255 | `0001062993-26-003453` | `4` | ok | `bb6be34fdb1f23e70f85a1843d15c9fd301cd72578ba5af7274452743a8290e3` |
| 256 | `0001104659-26-085852` | `6-K` | ok | `4c6d94655254fb84468c9bf79cac2477ebb492282337e7d94090ae2e1bf31977` |
| 257 | `0001824755-26-000005` | `3` | ok | `b089d1e3163002d17463f8603faadcdad4933487345dd653d7bae4b522f0bba9` |
| 258 | `0001104659-26-088452` | `6-K` | ok | `5a0a75aa56e6a04842e284b301778ec31d22ce5669543a4c2a50ba3eb1fc1ce6` |
| 259 | `0001628280-26-051140` | `4` | ok | `efac46660b363d04795c44e66d14498e94310fc2c5c666e5f31913bb2f0efe96` |
| 260 | `0002071691-26-020305` | `NPORT-P` | ok | `7bc19ac3ed6e4670473d7aa4353828f965a1ff6b8b53fb5f25874e58ba334390` |
| 261 | `0001214659-26-011350` | `424B2` | ok | `c64de03bc9933d367eadc4983b31d48d0a5d4689925023d6397c4e24ec484ed5` |
| 262 | `0001628280-26-049665` | `8-K` | ok | `5734e314af2c854914fb65dadb4bd79eb9ac4b260da8375f4cfed1192c09e234` |
| 263 | `0001398344-26-014372` | `SCHEDULE 13G` | ok | `a444032e00223566258de16f08505a8a080ac47e5f26da558eab04f0ff8796b8` |
| 264 | `0001918704-26-026017` | `424B2` | ok | `58f1b334a34ce553b3b3a214f0072184775334ab6a121ff41d9dc9643d6bb720` |
| 265 | `0001888524-26-015969` | `10-D` | ok | `6f1a2645f36bbdbfea8bf2dba57d5c59b2c365f5ec2f595a9285ce5f33c13711` |
| 266 | `0001957845-26-000071` | `10-Q` | ok | `154e9f07cc00f567f78a934f976d526305ba7176f9ba95dcb86bc4a14c1e2f80` |
| 267 | `0001867096-26-000051` | `3` | ok | `f96599ea6782de7ef36b9cbed96c8fec8081da9a00a03eaeb5cc08bc345afe1b` |
| 268 | `0002050232-26-000006` | `D` | ok | `9bed2654fe38983a61d38a22197beac978f83200745c098ed035bc96a7f7bc8e` |
| 269 | `0002149467-26-000001` | `D` | ok | `2dcb4337c47bd7b0b92e871303e804e9800ad42e3112d1d410caa83dd722ecf0` |
| 270 | `0001193125-26-358064` | `8-K` | ok | `55123a549f798e53374d9c9df4f5fb7eaca45f4fb152ff8b9c2762f6aae89944` |
| 271 | `0001104659-26-095969` | `6-K` | ok | `3a8d52f1d48e92546650b89490c7dcf927dc8e9514bc75404269c7fdfc7d7513` |
| 272 | `0001193125-26-307602` | `497` | ok | `349a6e9fb27e2db7fe2055457491d905ecceaedd03a203116015ab8f5bacf0fe` |
| 273 | `0001062993-26-003657` | `6-K` | ok | `38fac826f71568d5852881fc5d604981186965b849c8e9670a6eef261b85ca59` |
| 274 | `0001918704-26-019189` | `FWP` | ok | `de41bfdf2b9a06ee588d0581ef304c44e5a96c5b8888b2f1289851dcc7c6e48f` |
| 275 | `0002074644-26-000008` | `4` | ok | `6df5dc44daf8dd868eefe047fa2f2683a6f1df4064fa09f138375fc7dbf10fb5` |
| 276 | `0001628280-26-049043` | `4` | ok | `0d5f2c9a93e8b4536ef4de533e43d7c1b9bc2f9cbf402cd44ddff9ac2f0ceef9` |
| 277 | `0001193125-26-302235` | `4` | ok | `72e5cf9f5ce4a70234435fdf5b81a41939c5786f3bbbbf8dea52e72dd83806f6` |
| 278 | `0001213900-26-086782` | `424B3` | ok | `76704c4f143f58ac3934a73d7f3f30a21b41bd4b13583bbf9a5b1b2581fc5b6f` |
| 279 | `0001420506-26-001401` | `13F-HR` | ok | `362d2183d9f458f209446bf12718f5e6d404646f195ed97b4aca32df6f44582e` |
| 280 | `0001213900-26-074871` | `F-1/A` | ok | `b702b94a053144f4191431db044a51ff1d9be1ea425c44b79027ee88033e8482` |
| 281 | `0001193125-26-326161` | `NPORT-P` | ok | `cdaac732d29f232ec960c0bb5a1a58e997051467888b51a978fd231ce7a5c505` |
| 282 | `0001213900-26-092462` | `424B2` | ok | `e251a03e59e0109f7c647ee704418d2e5afa455c9b10877b051fd34b950008d5` |
| 283 | `0000006281-26-000073` | `10-Q` | ok | `be901abb3e98d42e4ebc1ab2e60191939c71d9fdd7c3a01948a9c32b733e1ed4` |
| 284 | `0001242215-26-000018` | `4` | ok | `04432066ad9682753449161b7bd7e55203477d8dcdd8a13e2a56aa71c42e474c` |
| 285 | `0001437749-26-023058` | `8-K` | ok | `64c20431904d242574dea76f43ba31ea66834e6f54e0d96717075950f931a88a` |
| 286 | `0000950103-26-014399` | `425` | ok | `ed6c71f94f2e66a77c2b2508265ae3d31d9af13848d722c0ec0fc1a7c03c4fd4` |
| 287 | `0001193125-26-407400` | `NPORT-P` | ok | `4ef495aa246f06dc28c99229c6a91666c9a1fcdd0ba1bae97bd56cf11d64d4c9` |
| 288 | `0001133228-26-010139` | `N-CSRS` | ok | `af74c226726f97a6c5b55c691c3d6a78f02b5807891883625a869477485aec8e` |
| 289 | `0002048251-26-007260` | `NPORT-P` | ok | `e53f9fbb3a6587fd9a0eb92f3262520ea265d1afee0b0e87baff5735c05d3028` |
| 290 | `0001410368-26-088128` | `NPORT-P` | ok | `c4564dbce6db9fa1adf8d930ac580ac6599c6f67bc74eea8684334ea6ca582b5` |
| 291 | `0001140361-26-038036` | `4` | ok | `353aed98b45e2f3bb8e4753795f195308ae1f04a8085cfee09418f53027b3d50` |
| 292 | `0001193125-26-339935` | `N-MFP3` | ok | `de2b4e5c4a9155eca8165a7937f5affa8f64138c1feb30a5808ac4e4f7ae79fe` |
| 293 | `0001104659-26-082159` | `424B2` | ok | `1c2f7ebcbce12b7e27995e4affbdae48d0d778337c6815a5a3c2538836c6594f` |
| 294 | `0001597878-26-000003` | `N-PX` | ok | `418e723a43708291b1e4cd283725c70f15de2d6a541833817d09ed983432cd03` |
| 295 | `0002144711-26-000001` | `D` | ok | `5ba5893ff74986664833a80294ea68cb3fc3d5aa6a2ab44844edae21343e5975` |
| 296 | `0001839882-26-033282` | `424B2` | ok | `78ad8e7f2cd8f9650d0db848228bebf0a0a110f00c71e7968c125e3afa0fd5c6` |
| 297 | `0001512611-26-000004` | `13F-HR` | ok | `626394c20bc8a2363290f4a993791ac24a4c001bb818fef125cb6c930c2b734b` |
| 298 | `0002028907-26-000002` | `D/A` | ok | `42820b7eec7c2eb7acf393e8ace52c3d629e0e97a1dfcc7e8c6dbf01a8421180` |
| 299 | `0001968582-26-000765` | `144` | ok | `425678ca4d8bf83ff1c133198d385e5305598ab815ea886ee93ed79c4dd37fe2` |
| 300 | `0001185185-26-003272` | `6-K` | ok | `c4c628fb02c5aa9b52b2f79c5495d595462232be1616e6113d9d38eb5557177a` |
| 301 | `0001630064-26-000003` | `13F-HR` | ok | `2fe3fb4769a05d15e5fdbddc2ba247e67ee9e31fec9a9be3ec0d16adae141d12` |
| 302 | `0001839882-26-045589` | `424B2` | ok | `3721637ab70871eecf88ba13f88118786d4245ef6a00f2223cfc7a8375d8331c` |
| 303 | `0001976230-26-000006` | `4` | ok | `238436ae94319816151134219be92ea5a6ea062067ee9c9102d7e7da6e413964` |
| 304 | `0000950103-26-013524` | `FWP` | ok | `1015f7247b5fa2bfa9b524d13128100f380075ee65c6fed7fc88215bd58e5b15` |
| 305 | `0001213900-26-076090` | `D` | ok | `d2c0643d5f7e2c076801d3464c791fb83f7b3167f06bc2d0912633c2aa974453` |
| 306 | `0002143027-26-000004` | `13F-HR` | ok | `43407f7d7b9e7f3c9d8e3afe104a6ada1b38e4dbaa39112d0daf508bd757cae4` |
| 307 | `0001050269-26-000050` | `N-PX` | ok | `337517dc3298811a774772ef30587125724daaee82054f06d590e9bf67ee752a` |
| 308 | `0001004726-26-006380` | `NPORT-P` | ok | `54a7486e0a517e837aa71a8f49e900ff2043b0a6b30a9f683127207b63b48139` |
| 309 | `0001839882-26-047609` | `FWP` | ok | `06459ebebd900ac940ea2900d8ff41193ac1eeb38f6e63fb6b29c17ca08dda41` |
| 310 | `0001410368-26-088318` | `NPORT-P` | ok | `d9385cb7e4335d026545b4de99e888dd954b7352cb244a8baba228d2ee0de055` |
| 311 | `0001696841-26-000010` | `4` | ok | `f06feab1f9680c2999b5b7be28cbc491f14f1e561059a38cdb3e9bc849c70735` |
| 312 | `0001437749-26-027973` | `4` | ok | `2e01f3775d5a6e7efde7d8bf8cf27a971810aefdf23e71dae0d51c6eb313d407` |
| 313 | `0000354204-26-000855` | `SCHEDULE 13G` | ok | `a9e4d955a5ef47d26f2b4be69fc81ae5c527e2a29e5e58899b91ceada102c3b3` |
| 314 | `0002071691-26-020763` | `NPORT-P` | ok | `e3bf5b5a6c85c94fb0b2fcb4dff6d6ec5445e610766f90f81e9a0c2a3ac6556b` |
| 315 | `0001213900-26-097119` | `FWP` | ok | `082c1b022382f78e089108618d8ea382890c15b9fef97c264ffe17fb12f2af21` |
| 316 | `0001213900-26-075973` | `8-K` | ok | `85b80009bc39f535b63692bae44a602b4f6c69fac4e1c862686be1c2a36523f7` |
| 317 | `0001918704-26-019673` | `424B2` | ok | `cfc0cab894e38028e2e32f081ad1be8b1ee6e50a9894b5bf91d4aff63ecfaf1c` |
| 318 | `0001950047-26-007249` | `144` | ok | `81b14fcac363d39350e2fa6a747c7a7635f072250fbffaf130ee9d7446bf48c2` |
| 319 | `0001628280-26-060501` | `4` | ok | `f3b9ef19fed432a9d974b7845ba9c2e384ca09dfc38367ecef28f5154ed0e11d` |
| 320 | `0001839882-26-045675` | `424B2` | ok | `1943798700b1955f656578aa2f742f71dcab5f44c55ee554899cb0a24c219171` |
| 321 | `0001493152-26-040515` | `4` | ok | `f24ca3f26bb8e1a4d488851aacbc80f8d728986b8acb1c99c08b42c181dd2bfe` |
| 322 | `0002084811-26-000001` | `D/A` | ok | `f50035de9816842b08abc716f8358d0a70056647bd662325c1fa08267fe16453` |
| 323 | `0001628280-26-052605` | `10-Q` | ok | `77185c836b834169874390b128a4842a2ed39864c4f7579f3b10326961515c78` |
| 324 | `0001213900-26-100765` | `8-K` | ok | `7d8318e375dfa77286c75a72e188f3f1c46200305ed805876913f614cfef2284` |
| 325 | `0001630748-26-000011` | `MA-A` | ok | `971ce6d8c2de48e5e2dadb702c419eb83b1558e4acb9b591dbdd1d0267097f5c` |
| 326 | `0001046311-26-000025` | `10-Q` | ok | `1da23870763458829893e0d55b3f70ec77b7d2bd1fc94d95fba9176be09d6230` |
| 327 | `0001839882-26-046315` | `424B2` | ok | `a70ea712c529825f669b32f8ccd55e39cd36217a95a39ee116a7fc75481f6c5c` |
| 328 | `0002043395-26-000010` | `4` | ok | `5231df2b9471af11c824e8ca2197111cfd929ec490f2fea2473300dc7e50b5cc` |
| 329 | `0002065248-26-000003` | `D/A` | ok | `6e774a9665195ce4b3b42841135444e7e025d3f9287237a49d1ec66c9e3fd554` |
| 330 | `0002135638-26-000005` | `D/A` | ok | `72f8c05669e1676ee8f6a7946e05a4581b9030a0cd605be9ac5b72922303e0ac` |
| 331 | `0001810019-26-000105` | `4` | ok | `367decf9a73f0dbc5a9e2960d6765dcc733a3c63f2bf90648769ce9f47968148` |
| 332 | `0001172661-26-003802` | `SCHEDULE 13G/A` | ok | `84e6a2addecfc43309cefaaf682af46e0e23fe4d3b68f90ca9906e3baef04385` |
| 333 | `0001726026-26-000001` | `D/A` | ok | `0689af2e52119181e3d622072a3fdaf70b8ad3088cfe023e235560cd2757b267` |
| 334 | `0001108524-26-000190` | `10-Q` | ok | `ab6b045a69e32e96bbe8542d1cedbdcc651bf23e2f186f71505d5b7171a748fe` |
| 335 | `0001918704-26-021700` | `424B2` | ok | `a6dab5388debf33a398e8dd0e0e563061d0e0afb9a0c483cb124478778077d9b` |
| 336 | `0002145948-26-000001` | `D` | ok | `3e0fcee428bf8d928dad241c31bc29a32f7fb41774cad8267171ee18d326ee86` |
| 337 | `0001172661-26-002903` | `13F-HR` | ok | `a31916311695e15eccf9961d50f316c1ecb0c4b7e772477da887973a0f3a2463` |
| 338 | `0001104659-26-094857` | `ABS-EE` | ok | `9eae8a36315bb273082ba594b9a10febae8027203655f216f06562b7a5e2e515` |
| 339 | `0000940400-26-036287` | `NPORT-P` | ok | `dea01f95ce1656f46176f499d058cd1b1685b99759a8353881ec17ca2a6f58d6` |
| 340 | `0001040674-26-000058` | `485BXT` | ok | `446fb41294b4d883c7cc8b245d727e5d0070b01a0f8c6424b8e76871afb9c041` |
| 341 | `0001410368-26-086495` | `NPORT-P` | ok | `63d7c18e2c1c9afb319b2fc7e763fd1aa35a189bc4438a1b65f851d714acec54` |
| 342 | `0000950103-26-014697` | `424B2` | ok | `d5c4eed7f521820f2e10ead7719868662f83661510d037dfb725106c4cd42b0d` |
| 343 | `0001764387-26-000005` | `N-PX` | ok | `c8afdbd04567af3b772b3e05b60ab123c02d4c7c0988479c063cd83bd09e2e14` |
| 344 | `0001193125-26-306123` | `497` | ok | `2030e7c1fbf45467ff0f05691b8549c7a30dc7b1e6b8c3473993f905f16cefa4` |
| 345 | `0001405086-26-000547` | `D` | ok | `08a9ef2a77c80d33ca753ad03684991274def370b2652e1bea61857085066134` |
| 346 | `0001417835-26-000207` | `CERT` | ok | `e4838f37f3ef1419a8cee7d345b6bd43319c301f241632da8fb25e7e63b294f3` |
| 347 | `0001140361-26-033909` | `8-K` | ok | `2684056a62f9b1004b0d669889798b0a39000dc0649096966afe24bca02f2132` |
| 348 | `0001839882-26-047568` | `424B2` | ok | `30e282d87218d723bb01ba59a7a27e9a5d734f853f2083adf4133f5d6efe8d50` |
| 349 | `0001888524-26-018010` | `10-D` | ok | `f84bf43eba46a8686940cfc71eaf4e9cdeacb28fc59b8ce16ab69ebd1dde65c7` |
| 350 | `0000912938-26-000751` | `497K` | ok | `57e7363bc3f59e1d3c2310a71b036c2ec646598a18e10d1dd81c498b15fe83f3` |
| 351 | `0001123292-26-001114` | `D` | ok | `b09a4b7f6cd60f18718697f21197285c114c337fa5b80c483d802dd96018e3aa` |
| 352 | `0002041625-26-000003` | `3` | ok | `7dc647bbd51a666d15da5294b5ed528a1c2756891d7f4f5adcc6ef2cec203899` |
| 353 | `0001081400-26-000257` | `497K` | ok | `9149a232492e629f813e9434cc265abd66b9c51ef2f622e5888a11ab7f4f4adc` |
| 354 | `0001003715-26-003607` | `NPORT-P` | ok | `c216e35369c4da2a424ebb713cec51c23fe37335c6525bcb552925ab7ff7dae8` |
| 355 | `0001213900-26-103620` | `485APOS` | ok | `524bc23d69f90bb633a744526da0880b24f6599955b628edb9009f9b9ad0a7a6` |
| 356 | `0002052564-26-000005` | `13F-HR` | ok | `ee224cb131e806a39a26e91570168b4814f3f1d8d9ed7fbe0bdabae629b9c53e` |
| 357 | `0001999371-26-016349` | `497` | ok | `5fdc1f20eb952f8238274d62150c3212b0c2efedbb75c28ea9ffb3487e2b543a` |
| 358 | `0001918704-26-024982` | `424B2` | ok | `9259ff1db6873d4f52aef988eecb9b4d8aa2f8b6c8546da0cf8b5f53ee7f6757` |
| 359 | `0001193125-26-404871` | `424B2` | ok | `2792cabff078f02ba699460fa66939357e335f1e27b863fd45039b4ad6c4e3a8` |
| 360 | `0001410368-26-080444` | `NPORT-P` | ok | `cd2ae937aad4f78e763b849b515b2c9aa0897361c375826d11e5fad29e67782c` |
| 361 | `0001193125-26-394658` | `4` | ok | `24a259480a14bd7ce2d2717dca18d3a3e77a9c9a3f1502036543b212b3840a81` |
| 362 | `0001839882-26-039574` | `424B2` | ok | `7c2613dd73d56dd8ae6b3bf7f8577d51be166a82e07537eb8eede5fbc71fbd91` |
| 363 | `0001398344-26-017226` | `4` | ok | `2f8b37d9c1881de6199377d9014a64f89e1739a102969c60e935cdcfc3e3d091` |
| 364 | `0001193125-26-296187` | `6-K` | ok | `f8e3684a79c5b5369dec6a30764d31892df475ece641685f52670f5fdcaee30d` |
| 365 | `0002155738-26-000001` | `D` | ok | `f94aa880f74e08045368fc60b260ab77d4c29d391a416ed2d2658c76b0a70972` |
| 366 | `0001193125-26-341207` | `8-K` | ok | `ee717317ca43f0def620bcaed33445791de8fc6b250ef5de0ac26dc589fb6ada` |
| 367 | `0001921640-26-000018` | `4` | ok | `360cbe604fcaed10fff645b3343d3b3faea23d89e9dcb769221d86bcc6861699` |
| 368 | `0002142964-26-000001` | `D` | ok | `9c4a912309e8dafadf3c82d858c157fb584397f49b90f992dec29db2447de359` |
| 369 | `0001580642-26-004707` | `486BPOS` | ok | `99076520c33a74c50dc475e738b6cf1de0d8162afeb8852cc6d7cea013132e52` |
| 370 | `0001628280-26-056653` | `4` | ok | `28fc1d67a6aee377722337a6779b29b8476b4f2a4520f66a95b54d6bc76915e2` |
| 371 | `0001172661-26-003357` | `13F-HR` | ok | `34454b2405dbc67938444f4ddb854b1e5bc70441343978ded0f56465559cbff5` |
| 372 | `0001727269-26-000004` | `13F-HR` | ok | `222bfe3b0da2eeaa2d5e1b357233a9331f7fd58583b820e21d961a5d02537aff` |
| 373 | `0001839882-26-038902` | `424B2` | ok | `fe84095853bd43181aedfe035fe3cba445ad40d5df2f102fe4b1677e194f4d82` |
| 374 | `0000108985-26-000080` | `4/A` | ok | `0c53183f00c7e0262ae9ed8003df70e8e0138b7a7741296820363587e49e735e` |
| 375 | `0001213900-26-079025` | `8-K` | ok | `1a06096b523c509eba90fde7e426479d292e4b3710cb1d7a5ae0a757da7314c7` |
| 376 | `0001114446-26-004791` | `424B2` | ok | `ca4bdc911b1e42707e98fb7b9d7513c265898a1f09e19a1684791ec44f4a5c4f` |
| 377 | `0001410368-26-087900` | `NPORT-P/A` | ok | `c540c6fc586bbad3d40e7d7e68a56b6177596e83e375d29c40d1f396cc870d30` |
| 378 | `0001193125-26-311606` | `497` | ok | `4316b63f26f9ad90006737f3cb53c7c3189c303ae139449e320b8f06effffcf6` |
| 379 | `0001193125-26-321564` | `497K` | ok | `e2ad7fdf1c8a8601fee5f595bbc9f703248c4420c1cbdae239adfc17da35caec` |
| 380 | `0001185185-26-002833` | `8-A12B` | ok | `701f68d06b9b81025b94ec8192426f889b2df69962796e05ec917b87a4d10ac2` |
| 381 | `0001617982-26-000006` | `3` | ok | `ed9283c4ae3d9e9553cf9ebfb920968c54833eafba79a8e9f63fd0ae6754eafd` |
| 382 | `0001568651-26-000060` | `4` | ok | `ec460a57f75013ad2c85833441617a4ef2d2389e56f1e3a5db4934dc818e942e` |
| 383 | `0002057057-26-000003` | `13F-NT` | ok | `abf1d6d00bbe0016cf63c5ce78bc0d9838d7c38d0ba99f59e0ff6d5da1ea25a9` |
| 384 | `0001520262-26-000105` | `4` | ok | `832318a7f691bd028a2947bd4e8f666459501312f74a2a48ebe8fae4f95f8678` |
| 385 | `0001213900-26-101974` | `424B3` | ok | `e63257ff8d877f35bcf290c80e67f7ac4611873874613b057e143b55b83af0cc` |
| 386 | `0001018164-26-000070` | `8-K` | ok | `cfb1547d4a3cb535e8a0f7b9b1968aa6f24f0a448e50de11b22fec004fc9d866` |
| 387 | `0001885778-26-000014` | `N-CSRS` | ok | `cac3f85b78ac4e2114ac64ce61b337a42d9a756a928726ca1035851f243570c3` |
| 388 | `0001864158-26-000004` | `4` | ok | `5ae78803ac1c0d0a1265b4aabb38a3cd492c90bd00a1986dc608e8458c9e1acf` |
| 389 | `0002147422-26-000001` | `D` | ok | `b0857fccd738068e65d9fa68095b3799691b7394d408fd28ab542afc2266487a` |
| 390 | `0001465105-26-000010` | `4` | ok | `5047843dd9bd6cd1bb07158f676b2d9a17e757dfe6d5333b2734e31770cdc424` |
| 391 | `0002138999-26-000001` | `D` | ok | `51bb2f69db53cc3230c5585a6103b8840e3f3ecdc192e380c151f9bfb0501ffc` |
| 392 | `0001140361-26-030789` | `424B2` | ok | `d7e87d749e11c1dbcf831e03c566813856595da5b5f78c72d8b38712556248a6` |
| 393 | `0000065984-26-000291` | `4` | ok | `b9e0ff03added75b2fd51b3ad862da24d57441c4b3641bcdac56ca23f2b213e1` |
| 394 | `0001839882-26-045822` | `FWP` | ok | `f3bee742dc0c2f2beb735c794b3fd06026f20d711f56e7a989cbecc8232d2e83` |
| 395 | `0001980335-26-000001` | `D` | ok | `45fcdc6dc741336a170ece54257e82c6b3e68a984aefc1d5369b3ace733cba87` |
| 396 | `0001839882-26-043376` | `424B2` | ok | `ca5a2a089bb0ee9f2c83b9840223968a831e2db98fa12562bef09f4b009f01ad` |
| 397 | `0000919574-26-005731` | `D` | ok | `450f26ea0480f1728935d816942aec9b5a19b125ad838fec27c856b7c9bc7b7a` |
| 398 | `0001104659-26-079861` | `4` | ok | `1ae4a48f4457a331c75d50fe20fdc75e7d5b60fb5557946095e3908a25041254` |
| 399 | `0001839882-26-047942` | `424B2` | ok | `2e68a03b90df8df20275a2c4e9aa66a1052ac1372595a5dd942c37ac514ac4fe` |
| 400 | `0001141391-26-000097` | `4` | ok | `b0c6148b1ab7d658299b1e3193312b0fce165201faf80e78ae079dfb49ffc03a` |
| 401 | `0001193125-26-349753` | `4` | ok | `4d4acc41f0bceee7ce00573fe4835b9e147ae79c57eec69d80d3f5ad4f0b8b56` |
| 402 | `0002047271-26-000004` | `13F-HR` | ok | `2e4bcfb01ccff92a19270be6efe43f71ee3a91c5a0955acffe134c3902468d9c` |
| 403 | `0002085777-26-000003` | `D/A` | ok | `526e08f7ceae87973dac715b077219235bdd04044220447d70ef41cca9619cfc` |
| 404 | `0001114446-26-005331` | `424B2` | ok | `7b15853209d23f5ef8cb14477abab8ecd8050a451dde638bf785abe7f83592ff` |
| 405 | `0001839882-26-034245` | `424B2` | ok | `e9b279e730b9598e1af1a1f71a637ca5de0623ba329a2c21d5c3a623250c3164` |
| 406 | `0001918704-26-021201` | `424B2` | ok | `a83d3f4847e9ed2d6a15798a41022107cf622828b603d738f3763b2af84e4f07` |
| 407 | `0001918704-26-021417` | `424B2` | ok | `91611a3ab8fb4fb8ea7cf3c7658c1c62d52eac98a7a803a106e6b45f57a78f65` |
| 408 | `0001888524-26-017666` | `10-D` | ok | `d0f518e95b193c530c191b42f35ecaddc611086c3cd8d43e32b6bc8d1c648468` |
| 409 | `0000950103-26-014610` | `424B2` | ok | `81ed4f866a677f3f6c8cd4d688a74d2490ba929cf8d9abd44480231e1123f8bc` |
| 410 | `0001667718-26-000001` | `D/A` | ok | `2fdf3ed2573cc4f140955849a545664a0a46bcceca96813255bd7699c885a6ec` |
| 411 | `0001839882-26-043232` | `424B2` | ok | `5f68330867d089747db765537f082025c970ef87b91008801b30193c1bdd754f` |
| 412 | `0001214659-26-011226` | `N-PX` | ok | `638af53164f4666aab77880068ef23839a9ad7ab91d22d45f5cf971075f0329e` |
| 413 | `0001839882-26-038106` | `FWP` | ok | `f36ec40872e9810f0f90e1fdeafbdd685612e442c3578f3383533d939fb9ef61` |
| 414 | `0001193125-26-381367` | `424B2` | ok | `95eb4959f42dba98131ffd45d83abe683f8d5eb91b07f9b5dca6cd0a57274f4a` |
| 415 | `0002071691-26-021319` | `N-MFP3` | ok | `725d51253ac8b088d655a3bc13e1550eb0b09704707ac5d5238e9db20d66ea2a` |
| 416 | `0001628280-26-057388` | `DEFA14A` | ok | `b0d05dff4cb158a0e75292a021f3fb4f358a7cd5eaf92ea1f0368baaac3215ad` |
| 417 | `0000950103-26-011309` | `424B2` | ok | `c9818df9d9d6dc51b998c2b0485c23cb55784cf1971d9fd6bce09a330d66fd6f` |
| 418 | `0001140536-26-000190` | `4` | ok | `4d9ff0aeabc344d3ddee8468f2a39caf1d9a057e0ffc388088d51f5259acc87e` |
| 419 | `0002144320-26-000002` | `3` | ok | `18f2b99565cecc3844ecde4f679e8fd3e25d186cdf16f5ef4a379f06f19b43c0` |
| 420 | `0001213900-26-079668` | `DEFA14A` | ok | `a1c8f46444f7f25a4dfce30899ef86323747f740b32c2ad0b36f91f7ace4eaa1` |
| 421 | `0001654954-26-007702` | `6-K` | ok | `f379334183d763abe1f9331b64cc40f446d66c74f9babf713f047b2f59b0e2fb` |
| 422 | `0001193125-26-375617` | `N-PX` | ok | `bbc1bff05a41bf71267d4824d1cb07f879f9606ba9b854ad44af5fb72ef7289e` |
| 423 | `0001104659-26-083577` | `4` | ok | `723618a6548c0afa23f50bf0a08144fe49938fd03a700c0a104f511db33847a9` |
| 424 | `0001193125-26-398057` | `497K` | ok | `6830a26f94dfd1fd3965f2e52644b0fd6c4684220ca8ffe08a6a4a76c97e5bf0` |
| 425 | `0000038009-26-000057` | `424B3` | ok | `4c5cb9b5dbdd75eb22d93bc370b2170ba87600bd6ffb1cc1ad38bd69e49050a1` |
| 426 | `0001950047-26-009134` | `144` | ok | `c7a2ea73e3345a6f34031c099a7877b667f4989eda510d8079471cc767bd09ea` |
| 427 | `0001114446-26-004674` | `424B2` | ok | `7a4c4b873abb20e2b8abd8bb1470720be1f4257d938e4c5d0d1f0c518761acd2` |
| 428 | `0001950047-26-007344` | `144` | ok | `0a906a36bbccc00ea2dd3accca9860bb80e970f68fb88df43a0eb8dddff93da1` |
| 429 | `0001839882-26-042319` | `424B2` | ok | `98258dbfeed63040961724a58acdde96f861c1cf6bbc031702c7b749b9e5366a` |
| 430 | `0001410368-26-100633` | `NPORT-P` | ok | `c47762f09f296162a00c12f229dd37c706988afdcc32c474162cab41d80a5a6e` |
| 431 | `0001562577-26-000323` | `497VPI` | ok | `7fcd92396fd2dafa9dde8da2d6dc39d609bf7a7bc892265aaf009363d770c5b4` |
| 432 | `0001193125-26-389183` | `4` | ok | `69101c07e505b4c05724edfdfdb6c993cceb251271e5ae4ce735907c80c65105` |
| 433 | `0001793659-26-000045` | `8-K` | ok | `c79132d4c81429d003ae416bdc9e3a50f7ac7b8d32237e86fd7e289b52c83299` |
| 434 | `0001808471-26-000025` | `4` | ok | `6e4ddae2ef644429aadfc615607dee33c15b6a790def35cb7bf4874e517f58dd` |
| 435 | `0001709048-26-000221` | `4` | ok | `d349811dbb18013ebe2d6658e89c2af4b19b2cb4bafbd57b45e7542ac3864895` |
| 436 | `0000929638-26-003522` | `4` | ok | `4591f81c5e8b5aa48596fdbc3f227563c6e30f02e1d39a92e660a44edac077ec` |
| 437 | `0001959426-26-000047` | `10-D` | ok | `480c232ea927c39f0af0952e062f616c63d96303b3b8daa621cb611edfdccdc8` |
| 438 | `0001623632-26-001153` | `24F-2NT` | ok | `e619bbe38f98da1692036346820b38603e490caa66290fa7a88c4e10a2384cbd` |
| 439 | `0002000324-26-003029` | `NPORT-P` | ok | `2ea9a64bc12565d355f40a78b8ad8eb913838944be2093f01c9a3868986cf6b4` |
| 440 | `0001012975-26-000640` | `D/A` | ok | `b7f994fbcd1e35430a167c2877ed1339aa29a891b60e2adc2de84a7a6a0d5cbe` |
| 441 | `0001114446-26-005690` | `424B2` | ok | `00d67cc0f3674fb8bf6f1d63ae603aec96394fefdcfb7eac9e14d33a429b8f17` |
| 442 | `0001805385-26-000047` | `8-K` | ok | `13f82ceb2f13298794053ffd324391ea96b5eb1b98234919eb77e14c494748c2` |
| 443 | `0001445546-26-006878` | `24F-2NT` | ok | `58ca2fa85fcdee32c36f988cd3f91ffc12e662bd5c400aac7c0aa6d1345d29ff` |
| 444 | `0001143362-26-000324` | `CERT` | ok | `eae8b994b9de6de564321e1359491ad87ff7fdffde1aab53a66de89e0aecacec` |
| 445 | `0001937040-26-000003` | `4` | ok | `aa16f1326d9f13423324c237a4715aa09542dbb29f36af010dcb6efd972c3098` |
| 446 | `0001044905-26-000004` | `13F-HR` | ok | `b40aed0eb632394df0eca528c6ee4d3bbb638cc5869efcedf5895be6a43fd01e` |
| 447 | `0001839882-26-043407` | `FWP` | ok | `a6d4fb118a5a8c9cc7ea8a56447cfb9f81950b9b803e65601dcc3581dd57d9b4` |
| 448 | `0001770532-26-000004` | `13F-HR` | ok | `56f140a7314e3eb1602975b378548ea6012eec676562862e913e785729ff2562` |
| 449 | `0000921895-26-002624` | `SCHEDULE 13D/A` | ok | `6fbf5fc843b206de3e5adf4fe84824517c7484afb12b7d8ccad519080e98f61a` |
| 450 | `0001193125-26-340053` | `4` | ok | `4a5009d59ca7a8a5369537fac5980bfeee2e60e23fb8bbba01ca0032620717a4` |
| 451 | `0000931148-26-000069` | `4` | ok | `ce0f13a3bcd41e4482020e19d6f67d943596358ee9d28c30a3d97484f98bae4d` |
| 452 | `0000950103-26-013476` | `424B2` | ok | `cb068074192c2a3016b988f1c1c57245f255964c55e3f2aa05dbb0cc1d738cb8` |
| 453 | `0001193125-26-402723` | `NPORT-P` | ok | `14dfa002bacf0e6664efc9a1068b1901d06b250f7f32db966a260d402f65fea6` |
| 454 | `0001475597-26-000119` | `4` | ok | `364b3a0ecd603af322fc9bbdddb3883fac083be4ae54a20c32dce2370572d86c` |
| 455 | `0001422849-26-000118` | `SCHEDULE 13G/A` | ok | `123d89cc2dcf7996504de1bdb58663fb2874276aa910fb6a1fce042a9080eb76` |
| 456 | `0001951757-26-001208` | `13F-HR` | ok | `1e8556e2b8ec12bd26ab671cb5228c42701aabbe26e25b254151bc6a7608ad72` |
| 457 | `0001829126-26-009063` | `497` | ok | `dcc8a062b0bc9bdae44101a61452b4d3295292ec8efbb7fe1874465b47a0bd9a` |
| 458 | `0000940400-26-033171` | `NPORT-P` | ok | `f4da1ffbe736d742d4a8f0c9038cebe4963a09f8c4c6e24725ed8be1fa2d6c56` |
| 459 | `0000950103-26-011075` | `424B2` | ok | `4dff146f965f3e6ec0b129d99e8c8e76b5bef28a9a80fa8785c22ad4e41dfc7d` |
| 460 | `0001839307-26-000004` | `N-PX` | ok | `9b876b877b9dcbca59ca4a922bdfb34f4df1b3ba973e0ac703ef4e18ae7cd5f9` |
| 461 | `0001104659-26-112305` | `497K` | ok | `06033ead76dc808ce84a125712ca9761b002e55c3cf871fef0256ddc3e6c5fe8` |
| 462 | `0001950047-26-008338` | `144` | ok | `00122957bea1389c6deb5cdf5b8e373b9e2428a0e4a8ac2031989aa9e89a41a8` |
| 463 | `0002149291-26-000001` | `D` | ok | `6a53d7c100441fc476d6433b7a9838988c8e3fbdf4bdd684bc69c1dc33604e5b` |
| 464 | `0000902219-26-000309` | `SCHEDULE 13G/A` | ok | `aae96bdc1f02c53614322cd7188ee16ac93194973d4195b94980c12b4ae16cb0` |
| 465 | `0001839882-26-037808` | `424B2` | ok | `b9a03ec0f7e100e9b68457d20617d9ab73f207ee7ecafb8b80e413b577edd39c` |
| 466 | `0001801444-26-000001` | `4` | ok | `e891fff561462890b876ebaf09cee89c1659519f6b14bd5111152918f079b76c` |
| 467 | `0001728195-26-000005` | `13F-NT` | ok | `22c4d2aed25a60cbcf4fc0e3c1e82d4dee7fa34378d723dcda95bfa68777777b` |
| 468 | `0001918704-26-027688` | `424B2` | ok | `81b9d5af4f04f0d63481050bec6b05ae1532e895f9a4a0a62f52827f774eed68` |
| 469 | `0002025920-26-000003` | `D/A` | ok | `94196d0ccb7751a33c3d741b55025e19dcb13923c09787354706cccb11459ef5` |
| 470 | `0001959173-26-006637` | `144` | ok | `7614c8ca427152c6b2d538d795e0978d030152af51ad5547ccf25b819fa01337` |
| 471 | `0001926488-26-000012` | `4` | ok | `ffe0d5bcb29ebb4a4a2f37ca8434b982634709a13c9e2234adc348e3c3789b13` |
| 472 | `0001493152-26-033916` | `PRER14A` | ok | `05297822aab9c2e1d1c9f2e712bdf81248ac65bcba377998a7c27bd5bcde5b3d` |
| 473 | `0000910472-26-014368` | `N-CEN` | ok | `721d7476edc407b3bec82a7eb497b511fb86464fd0d977f769b2891ad7987c7d` |
| 474 | `0001104659-26-088724` | `FWP` | ok | `113637cab259b25a466eff8e082e0b31ec4e6824ae2ea62f3f3cbbd9318ec4ce` |
| 475 | `0001883131-26-000001` | `D/A` | ok | `990cc7731d0d620cf459ef7a3d44f227db7996dfbe748bc7866a901d618b915d` |
| 476 | `0001839882-26-036441` | `424B2` | ok | `9d10aedb4e6181af14874b621524d85b18b2c8715104258b2d82c03f81c3166a` |
| 477 | `0001864123-26-000010` | `13F-HR` | ok | `284e970081837b8b09b569354d8b2f80588e148548a2e564dcaef73414417866` |
| 478 | `0001509412-26-000009` | `4` | ok | `f79bd36e82379fae281db482332cdcb8fe596a357110b51d13d6940784ac149d` |
| 479 | `0000091388-26-000052` | `8-K` | ok | `92c4def9bd48d200b7ecfe34c55ef425c6d2c77dc59f37381153abf8ba066d22` |
| 480 | `0001839882-26-039257` | `424B2` | ok | `c5329791589cca351c33b6d8e295421fd7c2542fd7eccbc716c3ff0139e6d2f2` |
| 481 | `0002147162-26-000001` | `D` | ok | `f8c4d1a384f0343e78c640e8998b17f58c71d784286ed8ebda83f96e11ed5d50` |
| 482 | `0000905148-26-004175` | `4` | ok | `9ebc04ccce0a2638b5b8e6a5b4003cec51427d24948bf0371dd64c1b325ae096` |
| 483 | `0000950103-26-014430` | `424B2` | ok | `f914aa0d26401412d86f444d02989c8ce4163ab69237432c98863f324e61ed92` |
| 484 | `0001193125-26-329087` | `497K` | ok | `76c157980d854f8d5938eac583af4bae59be141985d81c1309bf36f8966d942c` |
| 485 | `0001104659-26-087990` | `10-D` | ok | `793b59ca33170bd33ddad0508faf387ead164c4e4faefdca151ce7e9af0e3635` |
| 486 | `0001839882-26-047843` | `424B2` | ok | `da9aa34036e5a41e35b9bcddd9f1ee6eda61e820ff24c5814fa62bb5436cfb14` |
| 487 | `0001625641-26-000184` | `4` | ok | `d73b1668e8e91e468774fa3b3e170b8c652e636d5e8fcc74e91157a28b5b3d1a` |
| 488 | `0001888524-26-016520` | `8-K` | ok | `f70520155e26889c2e762e594d5e4327e0bbfdbef87b7cd340f6378dfe8a3660` |
| 489 | `0001628280-26-046742` | `4` | ok | `b07ea470cecd4bab4c643b3feaf140e4c72d55a63ddb08a809e5559533aa536b` |
| 490 | `0002071691-26-020972` | `NPORT-P` | ok | `85e92d9d3db29d28fd71998c0ff2567eb63a73a8befcc5c5ec6f32a356c03ad6` |
| 491 | `0001213900-26-083640` | `424B5` | ok | `0ae924e6b04bc02ed41c5a9f4cc84d74ba5a7cd35d36d86f16cfd2e8872dbc3f` |
| 492 | `0001951757-26-001553` | `N-PX` | ok | `0083c6887bde6431e2671c8e91e695ef4cb9a15af663512500392b2e0e030a73` |
| 493 | `0001918704-26-021385` | `424B2` | ok | `b0bd8341d857cca610253eb51a4625a370c48a335bde17614dbe539e00817a5f` |
| 494 | `0001742084-26-000003` | `4` | ok | `34116d70fdcea3f64594715306aa12e73ddd578c23add601e4e9edfbca83ce29` |
| 495 | `0000940400-26-035323` | `NPORT-P` | ok | `712f20b6f370f1838adf70e729d0a9baca73e00aa62df9d3f077d4a464ee250f` |
| 496 | `0000884546-26-000403` | `497K` | ok | `ee60182aa13fe215c944adf7dedd8e50bb92001402083c7a566d9e77f3c43801` |
| 497 | `0001598549-26-000015` | `4` | ok | `f4d952492b320493e76ce2d7dff59b589b46ffd3060538e98ed2e8961cf03410` |
| 498 | `0002034641-26-000002` | `3` | ok | `65100773f265524b6f9edccda38f4e6ec5b184bb66fce043c8a27955afbd62bc` |
| 499 | `0000905148-26-003942` | `13F-HR/A` | ok | `b4bef70b51e75f64b8a4ce01d29a61bef3d4d1ce5fc661104dd88e083738d8fc` |
| 500 | `0002147559-26-000001` | `D` | ok | `92c13181d68d190c46b0c5a7d21fdcd523e0206454fcd2132ca1f16240bb4b3e` |
