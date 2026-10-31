# Stage 2 baseline coverage finding (G2)

**Status:** Accepted by the owner on 2026-10-31. **Plan:** [plan 2](../../plans/2-sec-filing-index-ingestion-spec.md).
**Range:** 2020Q1–2026Q4 (28 quarterly units; 2026Q4 open; start set by plan 2 D10). **Release:** `9fa189a0…` for
invocation 1, `c4de77b8…` from invocation 2 (reserve 1,800 s). Configs: `conf/stage2/1b/` for invocation 1,
`conf/stage2/1c/backfill-2026Q4-open.json` for invocation 2, `backfill-2020Q1-2020Q4.json` (since removed) for invocation 3,
and the live config `conf/sec-edgar-local.json` for invocation 4 (plan 2 Revision 4). See [invocations.md](invocations.md).

## 1. Result

No requested unit is covered. [final/coverage.json](final/coverage.json) (full check) gives `quarantined` 28 and
`complete` false. Every quarterly source from 2020Q1 to 2026Q4 downloaded, and every one failed its transform with
`conflicting duplicate logical key`, at a different line in each file. The store holds 26 daily-only filing quarters
(361,367 validated rows, no quarterly membership authority) and no quarterly-sourced generation. The same error
stopped 2024Q1 at line 88043 in the L12 run (findings §5), and the raw enumeration finds repeated keys with different
form types in all 28 files. The proposed operating decision is "approved incomplete" (§6), with a parser or schema design
as the proposed disposition for all 28 units. The campaign ran four invocations: k = 1 and k = 3 halted, and stop rule 12
finished it at k = 4.

## 2. Campaign as run

Window: 2026-10-29T13:00:00Z to 2026-11-05T13:00:00Z for invocation 1 (D10), from 2026-10-31T16:30:00Z for invocations 2
and 3, and from 2026-10-31T17:30:00Z for invocation 4 (Revision 4), all ending 2026-11-05T13:00:00Z. Totals ([final/audit.json](final/audit.json)): 167 attempts of 1,500, 150 distinct
URLs of 300, 127,347,240 received bytes of 1,073,741,824, 4 invocations of 24, 0 uncertain, 0 access denied, no breach. Three
attempts ended with status 0: the `daily-index/index.json` listing in invocations 1 and 2, and the 2026-10-27 daily body in
invocation 4.

| k | Config | Run | Exit / outcome | Elapsed (s) | Dispatch cutoff | Deferred at cutoff | Slowest member wall (s) | `tail_seconds` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1b pilot | `8305a3d9…` | 9 / `state_conflict`, no result | 67 | n/a | n/a | not timed | n/a |
| 2 | 1c pilot | `07992ac6…` | 3 / `incomplete` | 1,323 | 16:55:49Z (not reached) | 0 | 36.13 (daily 2026-08-26) | 34.592 |
| 3 | `2020Q1`–`2020Q4` | `b6e4e1f9…` | 9 / `state_conflict` | 353 | 17:23:20Z | 9 pending after a failed discovery, none dispatched | none | none |
| 4 | live config | `88738b7d…` | 3 / `incomplete` | 1,481 | 17:55:44Z (not reached) | 0 | 39.958 (quarterly 2025Q4, quarantined) | 16.096 |

The slowest member of the campaign took 39.958 s, against the fixture value 1,010.9 s and the limit 1,056 s
([final/timing.json](final/timing.json), 0 breaches). By class: a closed first publication, a closed rebuild by an incoming
quarterly authority, and an open-quarter daily member after a 2026Q4 quarterly publish (A1) did not occur, because no
quarterly source was published. Closed-quarter daily members took at most 36.13 s (2026-08-26), and open-quarter (2026Q4)
daily members at most 35.348 s (2026-10-29). Unique expanded bytes: 737,865,756 across 28 retained quarterly ZIPs (sum of
`master.idx` sizes from the ZIP directories). This is post hoc, not enforced.

Invocation 1 halted with exit 9 and `state_conflict`, no result, after 67 s, and nine filing-quarter pointers moved. Its
`daily-index/index.json` request was refused with `permit_expired` and was refused again in invocation 2. Invocation 2
completed member `3554e8ef…` (2026-07-01, source `924fd5f5…`) without a child and moved no pointer for it (`repair_check`
`{"listed": true, "ran_children": []}`, plan 2 Revision 3 item 2).

Invocation 3 halted under stop rules 1 and 3: the `discover` child refused with "source member is after the pinned
endpoint". The engine retains every incomplete member, quarantined ones included, so no slice that ends before 2026Q4 can run
once the 2026Q4 quarterly source is quarantined. Plan 2 F9 had assumed otherwise. The owner approved Revision 4 (D15): all
later invocations run the live config. Nothing was published in invocation 3.

## 3. Baseline units

| Quarter | Verdict | Source ID | Member outcome | Active generation (daily-only) | Membership source equals unit source | Validated rows | Daily rows considered |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2020Q1 | quarantined | `bd2d51a024fe` | quarantined | `4894ce81b994` | no | 2 | 3 |
| 2020Q2 | quarantined | `d48449efef9c` | quarantined | `87d25bee13fd` | no | 2 | 3 |
| 2020Q3 | quarantined | `fe9845224379` | quarantined | `16a560efd30a` | no | 2 | 3 |
| 2020Q4 | quarantined | `4cce6ce98641` | quarantined | `4c3bab29ca2d` | no | 4 | 5 |
| 2021Q1 | quarantined | `3320547af4a8` | quarantined | `0449783f4f4d` | no | 12 | 18 |
| 2021Q2 | quarantined | `6a0020e924d9` | quarantined | `48a12f25c228` | no | 38 | 44 |
| 2021Q3 | quarantined | `cbd02147f588` | quarantined | `66455aeca93a` | no | 30 | 42 |
| 2021Q4 | quarantined | `1928beeb17d6` | quarantined | `7ac9c6858e20` | no | 16 | 22 |
| 2022Q1 | quarantined | `89a438366b5d` | quarantined | `0452631f6c34` | no | 17 | 20 |
| 2022Q2 | quarantined | `aa3f15489c2d` | quarantined | `df8dc6d90911` | no | 1 | 1 |
| 2022Q3 | quarantined | `5b9178624fda` | quarantined | `62597dde8b3e` | no | 3 | 3 |
| 2022Q4 | quarantined | `5bf45a54eb1d` | quarantined | `-` | no | - | - |
| 2023Q1 | quarantined | `d5993ae0df71` | quarantined | `-` | no | - | - |
| 2023Q2 | quarantined | `ddb29ce18a35` | quarantined | `0c8f8d77e790` | no | 4 | 4 |
| 2023Q3 | quarantined | `567e24a500ff` | quarantined | `8c71a647a1d9` | no | 15 | 17 |
| 2023Q4 | quarantined | `537e61351070` | quarantined | `2a89cceb63bc` | no | 12 | 12 |
| 2024Q1 | quarantined | `b2d153963f7d` | quarantined | `b14de2bd6174` | no | 21 | 21 |
| 2024Q2 | quarantined | `d6232d2baa25` | quarantined | `ac422c4e1cdc` | no | 14 | 14 |
| 2024Q3 | quarantined | `006745fd2f89` | quarantined | `13253bde8757` | no | 29 | 29 |
| 2024Q4 | quarantined | `52bf7b8dc46c` | quarantined | `4a0cbfd2cce1` | no | 63 | 64 |
| 2025Q1 | quarantined | `5649cc6ee978` | quarantined | `20157e984d1f` | no | 119 | 125 |
| 2025Q2 | quarantined | `41c1edd82ed6` | quarantined | `cd0217a761bb` | no | 226 | 235 |
| 2025Q3 | quarantined | `e19b1bf15d2f` | quarantined | `24a3348c0152` | no | 882 | 918 |
| 2025Q4 | quarantined | `644b37c7184b` | quarantined | `448de2056397` | no | 592 | 625 |
| 2026Q1 | quarantined | `f8f05c9fd9e6` | quarantined | `c2608302342d` | no | 666 | 667 |
| 2026Q2 | quarantined | `239446e779b8` | quarantined | `0653eb012f4d` | no | 1035 | 1035 |
| 2026Q3 | quarantined | `5005901a1e81` | quarantined | `913892913dcb` | no | 280965 | 284387 |
| 2026Q4 | quarantined | `d64895140b03` | quarantined | `a75e1b5fc380` | no | 76597 | 77823 |

## 4. Exceptions and dispositions

### 4.1 The 28 quarterly units (2020Q1–2026Q4), all `quarantined`

- Evidence: gap `transform_failed`, message `conflicting duplicate logical key`, outcome `quarantined`, in every unit.
  - 2020Q1: parser stopped at line 136135; raw enumeration lists 9 repeated key(s) ([quarantine/2020Q1.txt](quarantine/2020Q1.txt))
  - 2020Q2: parser stopped at line 120629; raw enumeration lists 8 repeated key(s) ([quarantine/2020Q2.txt](quarantine/2020Q2.txt))
  - 2020Q3: parser stopped at line 35242; raw enumeration lists 19 repeated key(s) ([quarantine/2020Q3.txt](quarantine/2020Q3.txt))
  - 2020Q4: parser stopped at line 36140; raw enumeration lists 8 repeated key(s) ([quarantine/2020Q4.txt](quarantine/2020Q4.txt))
  - 2021Q1: parser stopped at line 197614; raw enumeration lists 3 repeated key(s) ([quarantine/2021Q1.txt](quarantine/2021Q1.txt))
  - 2021Q2: parser stopped at line 9629; raw enumeration lists 4 repeated key(s) ([quarantine/2021Q2.txt](quarantine/2021Q2.txt))
  - 2021Q3: parser stopped at line 89518; raw enumeration lists 1 repeated key(s) ([quarantine/2021Q3.txt](quarantine/2021Q3.txt))
  - 2021Q4: parser stopped at line 55568; raw enumeration lists 16 repeated key(s) ([quarantine/2021Q4.txt](quarantine/2021Q4.txt))
  - 2022Q1: parser stopped at line 1849; raw enumeration lists 13 repeated key(s) ([quarantine/2022Q1.txt](quarantine/2022Q1.txt))
  - 2022Q2: parser stopped at line 1565; raw enumeration lists 3 repeated key(s) ([quarantine/2022Q2.txt](quarantine/2022Q2.txt))
  - 2022Q3: parser stopped at line 1578; raw enumeration lists 2 repeated key(s) ([quarantine/2022Q3.txt](quarantine/2022Q3.txt))
  - 2022Q4: parser stopped at line 7090; raw enumeration lists 17 repeated key(s) ([quarantine/2022Q4.txt](quarantine/2022Q4.txt))
  - 2023Q1: parser stopped at line 1848; raw enumeration lists 9 repeated key(s) ([quarantine/2023Q1.txt](quarantine/2023Q1.txt))
  - 2023Q2: parser stopped at line 1786; raw enumeration lists 15 repeated key(s) ([quarantine/2023Q2.txt](quarantine/2023Q2.txt))
  - 2023Q3: parser stopped at line 1814; raw enumeration lists 16 repeated key(s) ([quarantine/2023Q3.txt](quarantine/2023Q3.txt))
  - 2023Q4: parser stopped at line 63015; raw enumeration lists 7 repeated key(s) ([quarantine/2023Q4.txt](quarantine/2023Q4.txt))
  - 2024Q1: parser stopped at line 88043; raw enumeration lists 3 repeated key(s) ([quarantine/2024Q1.txt](quarantine/2024Q1.txt))
  - 2024Q2: parser stopped at line 71223; raw enumeration lists 7 repeated key(s) ([quarantine/2024Q2.txt](quarantine/2024Q2.txt))
  - 2024Q3: parser stopped at line 64598; raw enumeration lists 24 repeated key(s) ([quarantine/2024Q3.txt](quarantine/2024Q3.txt))
  - 2024Q4: parser stopped at line 49150; raw enumeration lists 16 repeated key(s) ([quarantine/2024Q4.txt](quarantine/2024Q4.txt))
  - 2025Q1: parser stopped at line 26239; raw enumeration lists 18 repeated key(s) ([quarantine/2025Q1.txt](quarantine/2025Q1.txt))
  - 2025Q2: parser stopped at line 33324; raw enumeration lists 7 repeated key(s) ([quarantine/2025Q2.txt](quarantine/2025Q2.txt))
  - 2025Q3: parser stopped at line 64418; raw enumeration lists 1 repeated key(s) ([quarantine/2025Q3.txt](quarantine/2025Q3.txt))
  - 2025Q4: parser stopped at line 136173; raw enumeration lists 1 repeated key(s) ([quarantine/2025Q4.txt](quarantine/2025Q4.txt))
  - 2026Q1: parser stopped at line 84152; raw enumeration lists 5 repeated key(s) ([quarantine/2026Q1.txt](quarantine/2026Q1.txt))
  - 2026Q2: parser stopped at line 51530; raw enumeration lists 23 repeated key(s) ([quarantine/2026Q2.txt](quarantine/2026Q2.txt))
  - 2026Q3: parser stopped at line 40303; raw enumeration lists 5 repeated key(s) ([quarantine/2026Q3.txt](quarantine/2026Q3.txt))
  - 2026Q4: parser stopped at line 8665; raw enumeration lists 1 repeated key(s) ([quarantine/2026Q4.txt](quarantine/2026Q4.txt))
- The raw-field enumeration lists repeated (CIK, path) keys that carry more than one form type. For 2024Q1 it matches
  findings §5.2 (CIK 1426332 at lines 88033/88043 and 88035/88044, and CIK 1481241 at 98688/98690). The parser's normalized
  key could merge more rows than the raw enumeration shows. The other 27 files are shown by the enumerations, not by a
  parser trace.
- Downstream limitation: no quarterly-sourced generation exists. Closed filing quarters hold only back-dated daily rows
  (O10), and 2022Q4 and 2023Q1 have no readable generation at all (`baseline_publication_missing`). No quarter is a
  complete baseline for Stage 3 or later.
- Proposed disposition: deferred to a versioned parser/schema design (Size: design), for all 28 units.
- Owner disposition (2026-10-31): "Defer to parser design (Recommended)" (deferred to a versioned parser/schema design, Size: design).

### 4.2 Daily sources, reported apart from the baseline units

- Quarantined (conflicting duplicate logical key): 2026-07-08, 2026-07-13, 2026-07-22, 2026-07-27, 2026-09-17, 2026-09-24
  and 2026-10-21. Incomplete: 2026-10-27, with `permit_expired` ("child refused a stale dispatch window"). Proposed
  disposition: the seven quarantined as "deferred to a versioned parser/schema design (Size: design)", and 2026-10-27 as
  "re-run in a later campaign".
- Owner disposition (2026-10-31): "As proposed (Recommended)".

### 4.3 The refused `daily-index/index.json` listing and retained legacy gaps

- Evidence: the listing was refused with `permit_expired` in invocations 1 and 2, and the cause is not diagnosed.
  Invocation 4's discovery was complete. Invocation 4 also carried 15 non-retryable `legacy_member_unresolved` gaps: 14
  "source has no verified original parent" and one "source member is after the pinned endpoint" (a record of invocation 3's
  failed discovery). They stopped nothing. Their cause is not investigated.
- Proposed disposition: "accepted named gap" for this campaign, with both investigated in a later stage.
- Owner disposition (2026-10-31): "Accepted named gap (Recommended)".

### 4.4 No withdrawal gates and no refused incremental candidate

- No unit is `gated` or `awaiting_approval`, and no `refused` entry exists in any invocation record (O6, O16).

## 5. Other output

- Filing quarters outside the range (`other_filing_quarters`): none ([final/coverage.json](final/coverage.json)).
- Daily sources processed as retained work: 82, periods 2026-07-02 to 2026-10-30, outcomes `success` 74, `quarantined` 7,
  `incomplete` 1. These are Stage 3 inputs.
- Sources complete without a receipt (3, source IDs first 8 hex): `924fd5f5` (2026-07-01), `5c8146c6` and `cd8ecb90`
  (2026-10-14 and 2026-10-15). Invocations 2, 3 and 4 each listed them. They count as complete, not as work any
  invocation did (O21).
- Sources that invocation 2 completed and invocation 4 then listed as already complete (9): `6cf7f339` (2026-10-01),
  `0a6a3b58` (10-02), `668fa827` (10-05), `fd002406` (10-06), `16b45f8b` (10-07), `24a4e1d9` (10-08), `2de20d15` (10-09),
  `fc4e22ff` (10-13) and `f4bfa6da` (10-16). Each ran collect, transform and publish in invocation 2 with outcome `success`,
  so they are completed work, not a receipt anomaly.
- The open quarter 2026Q4: its quarter-to-date source (conflict at line 8665) was quarantined, so its absences were never
  used. They are not withdrawal authority (§4.4). The evidence tool does not report the snapshot receipt time.
- Downstream limitation (O10): closed-quarter publication keeps only quarterly-membership keys. No quarter has a membership
  source here, so the 26 published filing quarters hold daily rows only (`membership_source_id` null).

## 6. Operating decision

Decision: "Approved incomplete: coverage is accepted with the named exceptions in §4 and these downstream limitations: no
quarterly baseline exists for any of the 28 requested quarters; the 26 published filing quarters are daily-only and cannot
be used as quarterly baselines. Refused rows and sources are not accepted data."

Owner decision (2026-10-31): "Approved incomplete (Recommended)". The owner chose this option in the operator session; the words are the option label.

## 7. Evidence integrity

- L12-inventoried immutable files are unchanged ([final/files.json](final/files.json): 0 missing, 0 changed immutable, 5,116
  added, SQLite state changed by design). Full inventory `logs/baseline-campaign/files-final.json`, SHA-256
  `f8950d561c0902778c7f9782772c8a5b66e33b6449578b5503caebd7d8921c04`.
- Pre-campaign facts: the 2021Q1 manifest restoration and the absent L12 external directory ([pre-campaign.md](pre-campaign.md)).
  Stage 2 cannot restore the absent directory.
- Release history: invocation 1 ran on `9fa189a0…`, and every later invocation on `c4de77b8…` (invocations/*.json). The
  selection changed once, at `f64c212`, in Stage 1c. Selecting `fc68adef…`, `aa8de1ac…` or `9fa189a0…` for this store is
  unsupported (parent spec §4.9).
- Finder files `data/.DS_Store` and `data/objects/.DS_Store` stayed in place and appear under `added` (O24).

## 8. Revisit triggers deferred into Stage 2

- **B4 single-candidate limit** (`specs/deferred_items.md`, 4-sec-filing-index-bounded-drain, 2026-10-27). Condition: Stage 2
  shows repeated child sequences or refused-skip scans as a material share of run time. Evidence: `b4_members` 0 in both
  timed runs; `repeated_sources` 1 (invocation 2) and 2 (invocation 4). The share of total member wall spent by members of repeated sources is 11.3 s of 1,226.9 s (0.9%) in
  invocation 2 and 69.3 s of 847.5 s (8.2%) in invocation 4. Verdict: not met. The repeated sources were quarantined
  members that retry on every run.
- **History-scan cost** (5-sec-filing-index-per-member-cost, 2026-10-28). Condition: a live run's per-member engine time grows
  past the measured slope, or the projection exceeds the reserve's margin. Evidence: engine seconds per timed member 7.06 in
  invocation 2 (child-call rows grew from 6 to 223) and 9.77 in invocation 4 (224 to 326). The fit 1.38 s + 0.0290 s per row
  gives about 4.7 s and 9.4 s at the mean row counts. Invocation 2 is above the fit and invocation 4 is near it. Verdict: not
  determinable, because the rows at each member's start were not reported.
- **Unmeasured A1 member class.** Condition: a live open-quarter member with a quarterly authority has a wall above 1,010.9 s.
  Evidence: the 2026Q4 quarterly source was quarantined, so no 2026Q4 daily member ran with a quarterly authority. Verdict:
  not determinable.
- **Refused C6 candidate retry block.** Condition: a candidate is refused. Evidence: none occurred. Verdict: not met.
- **Two-release proof covers only first-generation 1b stores.** The release changed from 1b to 1c, not to D5, and the
  condition names only a D5 run. Verdict: not met. Invocation 1's eight incremental 1b generations on `fc68adef…` bases are the
  evidence the item's note already cites, and 1c published later incremental generations onto them with no reader failure.
