# sec-filing-data completion review

This is the completion review (derive-roadmap §6) of the [sec-filing-data roadmap](../completed/sec-filing-data-roadmap.md). It
was made on 2026-11-19, after all four stages merged (`main` at `1d18a2e`). It re-runs the gap rubric over the outcomes
O1–O4, with evidence from each stage. The roadmap's source is the owner's words, not a spec, so no spec requirement
needs a row. The evidence comes from the committed findings, the completed plans and specs, and
`specs/deferred_items.md`. No SEC request was sent, and no command ran on the live root.

In the Evidence column, S1 to S4 are the four findings files, `specs/sec-filing-data-stage-1-findings.md` to
`specs/sec-filing-data-stage-4-findings.md`. "Roadmap" is the retired roadmap,
`specs/completed/sec-filing-data-roadmap.md`. "Spec" is the Stage 4 spec,
`specs/completed/sec-filing-data-stage-4-as-of-views.md`, and "plan 14" is
`specs/plans/completed/14-sec-filing-data-stage-4-as-of-views.md`.

## Rubric

| Row | Verdict | Evidence | Note |
|---|---|---|---|
| O1, the 2026Q3 filing index | implemented-as-specified | S1 `:368`: 302,499 rows, every row of the file. S2 `:80`, `:177`: 0 null sources, and the 740 index rows of sampled filings carry times. S3 `:85`, `:202`: `binding index: ok` and `rederive index: ok, 20 rows`. S4 `:149`–`:160`: `asof` answers all 302,499 rows from 2026-10-31 | The 301,724 rows of filings that the project does not hold answer from the index file's `Last-Modified`, 2026-10-31T07:50:09Z (spec `:445`) |
| O2, the documents of about 500 sampled filings | implemented-as-specified | S1 `:369`–`:370`: 500 of 500 `ok`, 0 parse errors, and 20 filings of each quota form. S2 `:177`: a source and times on every record. S3 `:202`–`:206`: bound to their bytes, listed in manifests, and made by one code version. S4 `:273`–`:274`: each answer names its manifests, and no held filing has a `known_from` before its `public_at` | Legacy `SC 13G` has no 2026Q3 filing, so the sample has none (S1 `:53`). The 20 partner filings are the last row |
| O3, the as-filed XBRL facts of the sampled 10-K and 10-Q filings | implemented-as-specified | S1 `:371`: 45,358 facts from 46 of 46 filings. S2 `:177` and S3 `:202`: sources, times, binding and re-derive `ok`. S4 `:161`: `asof` answers the facts from the sample | The facts come from the SEC-extracted `*_htm.xml` instance in the submission file, not from the filer's inline XBRL document (S1 `:163`). The roadmap records this source in its Stage 2 entry (roadmap `:58`, from plan 10 D2), so this review counts it as specified. The inline XBRL checks V11 and V12 stay deferred (`specs/deferred_items.md:490`). The amendment clause is not exercised on live data for facts: the sample holds no 10-K/A or 10-Q/A (S1 `:161`), and no partner is a 10-K or 10-Q (S4 `:161`) |
| O4, the ownership records of the sampled Forms 3, 4 and 5, Schedules 13D and 13G, and Form 13F | implemented-as-specified | S1 `:372`: 6,847 records from 193 of 216 filings, and a reason for each of the other 23. S2 `:177` and S3 `:202`: sources, times, binding and re-derive `ok`. S4 `:149`–`:157`: `asof` answers 7,105 records, 6,847 from the sample and 258 from partners | The records are as filed. No amendment hides its original (spec `:54`). The rules for when an amendment supersedes its original (platform R23 and R24) stay with the held platform Stage 3 item (`specs/deferred_items.md:407`) |
| The Stage 4 amendment clause, over O2–O4 | implemented-differently, deliberate and recorded (spec D1, `:433`; plan 14 Handoff, `:524`) | Roadmap `:83`: where a sampled filing has an amendment, the original and the amendment each answer at their own dates. S4 `:97`–`:116` and `:164`–`:184`: 14 pairs with both filings held answer in order, 10 forward and 4 reverse. S4 `:71`–`:82`: 23 of the 27 sampled amendments answer alone | Of the 23, 16 point to an original that is not held. 14 name an accession that the 2026Q3 index does not list. A Form 4/A declares an original filing date of 2026-04-16, in 2026Q2. A 13F-HR/A declares the period 2021-12-31, and no held 13F-HR matches it. Its original is probably in an earlier quarter, but no partner rule searches the index by filer and period, so this is not checked. The spec counts 15 originals in other quarters (`:58`) and does not list them. The other 7 amendments declare no original. Amendments filed after 2026Q3 are not looked for (spec `:58`). The roadmap leaves other quarters out (roadmap `:48`). This review deferred them (Result) |
| What Stage 4 added: 20 partner filings, their ledger and a Stage 4 SEC budget | in-code-but-not-in-spec, deliberate and recorded (spec D1 and D2, `:433`–`:437`; plan 14 Handoff, `:522`–`:523`) | S4 `:38`–`:46`: 20 partners, equal to spec Appendix A. S4 `:48`–`:57`: 20 of 30 requests and 1,578,979 of 50,000,000 wire bytes. S4 `:126`–`:134`: the `stage4` manifest | The Stage 4 entry names the sample only (roadmap `:79`). The roadmap authorizes no live request beyond its Stage 1 budget (roadmap `:112`), and the owner set the Stage 4 budget in spec D2. The partners exist to meet the amendment clause. So they are a recorded decision, not drift |

## Measured cost

| Stage | SEC requests | Wire bytes | Step wall time (sum) | Evidence |
|---|---|---|---|---|
| 1 | 503 of 1,500 | 321,729,304 | 704.7 s | S1 `:336` |
| 2 | 1 of 20 | 881 | 29.0 s | S2 `:134` |
| 3 | 0 | 0 | 19.1 s | S3 `:156` |
| 4 | 20 of 30 | 1,578,979 | 45.4 s | S4 `:225` |
| All | 524 | 323,309,164 | 798.2 s | |

Stage 1 met its target of an answer within 3 working sessions or 7 calendar days. It ran in one session, on
2026-11-17 (S1 `:375`). The four stages ran from 2026-11-17 to 2026-11-19.

## Open deferred items

`specs/deferred_items.md` had 27 open items before this review. This review adds one, the watch item of Result item 2.

- **11 items from this roadmap's stages** (sections `10-…`, `11-…`, `13-…` and `14-…`). Each is a watch item with a
  `Revisit if`. None has fired. No stage fetched a Feed archive, read SEC reference data, covered another quarter,
  fetched a filing on its filing day, built a second root or an inline XBRL parser, or wrote a table outside a
  command. The Stage 4 run had no kill and no `asof` refusal (S4 `:236`, `:290`). These items stay open after the
  retirement.
- **16 held items**, the unticked stages of the two parked roadmaps. Each is held until this roadmap retires (the
  first note is at `specs/deferred_items.md:372`). Four of them cover the same data at platform scope: platform Stage 2, XBRL facts
  (`:402`), Stage 3, ownership records (`:407`), Stage 7, parser freeze (`:427`), and Stage 8, point-in-time store
  and views (`:431`). This roadmap met O2–O4 on its own sample without them. They stay outside this roadmap by the
  owner's decision of 2026-11-16.

## Result

No outcome is unmet. O1–O4 are implemented as specified. The amendment clause is implemented differently, by a
recorded owner decision (spec D1), and the owner counts O2–O4 as met under it. The owner approved the review's five
defaults on 2026-11-19. Owner's words: "Approve all five (Recommended)".

1. The ticked Stage 4 entry stays as written. This review cites plan 14's three departures as evidence (the last two
   rubric rows).
2. O2–O4 count as met under spec D1. The 16 originals that are not held are a written deferral, a watch item in
   `specs/deferred_items.md`, section `sec-filing-data-roadmap — 2026-11-19`.
3. This review writes no note on the 16 held items. After the retirement merges, the owner runs `/deferred`, which
   writes a `→ triggered` note on each item that the owner selects.
4. This review lives in `specs/findings/`, and the retired roadmap's header links it.
5. The roadmap retired to `specs/completed/` on 2026-11-19, with a `COMPLETE` header. The relative links to it were
   re-pointed. The plain-text path citations in plans, `specs/history.md` and `specs/deferred_items.md` are history,
   and they stay as written.
