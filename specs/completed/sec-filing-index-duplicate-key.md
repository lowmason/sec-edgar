# Duplicate-key parser/schema design and its release — Stage 2a Design Spec

**Status: COMPLETE (2026-11-02)** — implemented by plan 7
([completed duplicate-key plan](../plans/completed/7-sec-filing-index-duplicate-key.md)); nothing deferred by
plan 7. Item 1 of `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, stays
open for Stage 2b. The owner approved plan 7 with P1–P12 on 2026-10-31 (plan D1). Before that, this line read
"Draft for owner review, 2026-10-31".
**Project:** `/Users/lowell/Projects/sec-edgar-local`.
**Parent spec:** [SEC filing-index ingestion](../sec-filing-index-ingestion-spec.md) (§§3 R3, R5, R9, R12; 4.4–4.9; 5–6; 9).
**Roadmap:** [ingestion roadmap](../sec-filing-index-ingestion-roadmap.md), Stage 2a.
**Inputs:** the 1c release `c4de77b8…` and its evidence (`specs/evidence/stage1c/`); Stage 2's accepted
[coverage finding](../evidence/baseline-campaign/coverage-finding.md) §§4.1–4.2, its `quarantine/` enumerations and
`final/coverage.json`; the [submissions findings](../findings/sec-filing-submissions-findings.md) §5;
`specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, item 1; plan 2, Handoff
(`specs/plans/completed/2-sec-filing-index-ingestion-spec.md`); the [platform spec](../sec-filing-platform.md) R8.

## 1. Purpose

Stage 2 left no quarterly baseline. All 28 quarterly index files from 2020Q1 to 2026Q4 and 7 daily index files
quarantined with `conflicting duplicate logical key`. Parent spec §4.4 refuses a whole source when one logical key
`(cik, archive_path)` repeats inside it with different field values. So G2 stays approved incomplete, and Stage 4
has no quarterly authority to reconcile against.

This stage ships a reviewed native release with a new, versioned row schema, `sec-index-v2`. Under it, a source
whose rows repeat a key only because the SEC lists one filing under several form types or several company names
transforms and publishes. Every listed value is kept. Nothing is dropped and no value is chosen over another.

The stage is offline. It sends no SEC request and writes nothing under `data/`. The live store first meets the new
release in Stage 2b.

### 1.1 What the retained files show

A read-only scan of the 35 retained sources (2026-10-31, scripts outside the repo, nothing written under `data/`)
found 271 repeated keys. Each quarterly repeat has exactly 2 rows. Daily files also repeat keys with identical rows,
which already collapse today.

| Class | Keys | Rows differ in | What it is |
|---|---|---|---|
| Combined filing | 243 | `form_type` only | One accession listed under a tender-offer schedule (SC TO-T, SC TO-I, or their /A) and under SC 13E3 or SC 13D/A. |
| Company rename | 28 | `company_name` only | An `UPLOAD` letter (`0000000000-` accession) listed under the filer's old and new names, for example "9 METERS BIOPHARMA, INC." and "INNOVATE BIOPHARMACEUTICALS, INC.". |

No repeated key differs in filing date, path or CIK. The rename class occurs in 10 quarterly files (2020Q1,
2020Q4, 2022Q1, 2022Q2, 2022Q4, 2023Q1, 2023Q2, 2024Q4, 2025Q1, 2025Q2) and in daily 2026-07-22, which has only
that class. Deferred item 1 names only form types. A form-only design would leave those 11 sources quarantined.

The 1c release's own parser then read all 35 sources to the end, with only the duplicate check left out. All 35
parsed. So no other parser rule refuses a row after the first conflict line, and the Exit needs no second quarantine
reason (§6).

A cross-check of the 2026Q3 quarterly file against the retained 2026Q3 daily files found 306,028 exact matches,
48 daily keys absent from the quarterly file, 3 filing-date differences and 1 form-type difference. In that one
case the daily file lists SC 13E3 and the quarterly file lists only SC TO-I for the same filing. No company name
differed across sources.

## 2. Scope

### 2.1 Goals

- A `sec-index-v2` row that holds every listed form type and company name of a filing, with the key unchanged.
- Parser `sec-index-parser-v2`, which accepts within-source repeats that differ only in those two fields.
- A versioned reader transition: v1 generations stay readable, unchanged, beside v2 generations.
- Offline proof that all 35 duplicate-key sources transform on the new release, on a scratch copy of the store.
- A reviewed release, live-config selection, and a plan Handoff with the values Stage 2b's plan must use.

### 2.2 Non-goals

- Running the new release on the live store, or any SEC request. That is Stage 2b.
- Entity resolution, name history, or choosing a "current" company name.
- Deferred items 2–4 of section `2-sec-filing-index-ingestion-spec — 2026-10-31` (the `permit_expired` listing,
  the 14 `legacy_member_unresolved` gaps, the bounded-end `state_conflict`). They stay where plan 2's Handoff put
  them.
- The platform workspace member (decision S2, §8).
- Rewriting, relabeling or migrating existing v1 objects. They stay as written.

### 2.3 Anti-goals

The design fails, even if tests pass, when any of these holds:

- One listed form type or company name is lost, or one is shown as the "real" value.
- A within-source conflict in any other field (filing date included) stops quarantining.
- The result depends on file line order, SQLite scan order or batch boundaries.
- A v1 generation becomes unreadable, or reads back with different values.
- A form type that a later quarterly file drops becomes a withdrawal that needs approval. Today that is an update,
  and it stays one.

## 3. Requirements

| ID | Requirement |
|---|---|
| D1 | `sec-index-v2` rows have the key `(cik, archive_path)`, unique per generation, as in v1. |
| D2 | A v2 row carries `form_types` and `company_names`: sorted lists of distinct, non-empty strings, each with at least one item. It has no scalar `form_type` or `company_name`. All other v1 fields keep their v1 meaning and type. |
| D3 | Within one source, rows of one key may differ only in form type and company name. Any other difference refuses the whole source with `conflicting duplicate logical key`, as today. |
| D4 | A catalog row merges values only from the observations of the one source that precedence selects for that key. Values from different sources are never merged. |
| D5 | Merging is order-independent: the same observations in any order give byte-identical rows. |
| D6 | Change detection compares v2 business fields. A changed list is an `updated` change, not a withdrawal or an addition. Withdrawal rules are unchanged. |
| D7 | A v1 generation reads back exactly as today, as v1 rows. A v2 generation reads back as v2 rows. No reader silently converts one into the other. |
| D8 | A v2 candidate built on a v1 base maps the base's rows to one-item lists before comparison, keeping their v1 `parser_version` and `schema_version`. A re-transformed key whose business fields match then differs only in those versions, so it counts as `provenance_refreshed`, not `updated`. A retained row (`unresolved_absence`) is the mapped base row, so it keeps its v1 versions: a v2 data file can hold rows whose version fields say v1. The manifest's `schema_version` governs the file layout. The row's version fields record how its values were parsed. |
| D9 | The release writes only v2 observations and generations. It still validates retained v1 objects. |
| D10 | The 1c release and older releases stay retained and installable (§4.9). Selecting the 1c release for a store that holds v2 objects is unsupported and is stated in the parent spec. |
| D11 | The release continues 1c-origin pending work on a store the 1c release wrote. |
| D12 | The release's locked inputs carry no platform member. |

## 4. Design

### 4.1 Components

| Unit | Change |
|---|---|
| `etl/contracts.py` | Add `IndexRowV2` beside the unchanged `IndexRow` (v1). Version-aware `canonical_schema(version)`, `observation_schema(version)`, `change_schema(version)`, `arrow_row` and `BUSINESS_FIELDS`. A pure `upgrade_row(IndexRow) -> IndexRowV2`: one-item lists, and every other field unchanged, including `parser_version` and `schema_version`, which keep their v1 values as the row's provenance. |
| `models.py`, `config.py`, `cli.py`, `etl/commands.py` | The current versions become `sec-index-parser-v2` / `sec-index-v2`. New work requires them. Checks that today compare against one `SCHEMA_VERSION` accept v1 only where a retained v1 object is validated. |
| `etl/parser.py` | `sec-index-parser-v2` emits one v2 observation per source line, with one-item `form_types` and `company_names`. The v1 path stays to re-derive retained v1 observations. Field rules are unchanged. |
| `etl/transform.py` | `_remember_observation` compares the key's rows with `form_types` and `company_names` removed (D3). Counts (`source_row_count`, `distinct_key_count`, `quarter_counts`) keep their v1 meaning. |
| `etl/catalog.py` | The precedence pick selects the winning source per key, then unions `form_types` and `company_names` over that source's observations of the key (D4, D5). `_load_active` maps a v1 base with `upgrade_row` (D8). `_resolve` uses v2 business fields (D6). |
| `etl/manifest.py`, `etl/columnar.py` | Validate a data or changes file against the schema of its generation's `schema_version`. Key uniqueness and sort checks are unchanged. |
| `etl/incremental.py`, `etl/equivalence.py` | v2 rows and fields. The incremental path still needs an active generation with the same parser and schema, so the first v2 publish of each quarter takes the full rebuild. |
| `etl/reader.py`, `etl/history.py`, `etl/approval.py`, `etl/rollback.py` | Read each generation with its own row type (D7). |
| `conf/sec-edgar-local.json` | `etl.parser_version` and `etl.schema_version` change to v2 at the live-config selection, with the release (§6). |

The builder may reshape these units. The requirements in §3 bind, the table does not.

### 4.2 Data flow

1. **Transform.** Each source line becomes one v2 observation. The within-source check keys on `(cik,
   archive_path)` and compares every field except the two lists. Identical rows and rows that differ only in those
   lists pass. Every observation is kept, with its original fields and line number, as today.
2. **Select.** For each key in the quarter, the existing precedence order (quarterly preference, source period,
   receipt time, source ID) picks one source. All observations of the key from that source share every field
   except the lists (step 1), and share provenance.
3. **Merge.** The candidate row takes those shared fields and the sorted distinct union of the lists. Set union is
   order-independent, so no line-number tiebreak is needed (D5).
4. **Resolve.** Compare with the active generation's rows, mapped to v2 when the base is v1. The membership,
   absence, withdrawal and approval rules of parent §4.4 apply unchanged, key by key.
5. **Publish and read.** The manifest records `schema_version=sec-index-v2`. Readers choose the row type from it.

The 2024Q1 file's NGM case becomes one row:
`0001426332 | [NGM BIOPHARMACEUTICALS INC] | [SC 13E3, SC TO-T] | 2024-03-08 | edgar/data/1426332/0001140361-24-012376.txt`.

### 4.3 Transition from v1

- A v2 release meets a store with v1 observations, 26 daily-only v1 generations and their pointers. Nothing is
  rewritten.
- `build_candidate` already re-transforms a selected source whose processing versions differ from the run's. So the
  first v2 publish of a quarter re-transforms every source of its active generation and takes the full rebuild.
  Unchanged values give `provenance_refreshed` changes (D8). This is a cost for Stage 2b, not a new mechanism.
- A v1 generation stays a valid rollback target. Rolling back to it is allowed. The next publish of that quarter
  then builds v2 on the v1 base again.
- A multi-quarter read may hold v1 and v2 captures. Each capture already names its manifest, which names its
  schema.
- Exact replay of a completed v1-era result still needs its saved release (parent §4.9). New invocations continue
  unresolved v1-era members under the v2 config.

### 4.4 Errors and edge cases

1. A key whose rows differ in filing date inside one source: refused, `conflicting duplicate logical key`. None of
   the 35 sources has one.
2. A key whose rows differ in both lists at once: merged. None observed.
3. A key listed 3 times, as some daily files do: all rows merged. Identical rows add nothing.
4. A daily source and a quarterly source list different form types for one key: the quarterly row wins by
   precedence, as today. The daily form type is not carried into the row. It stays in the daily observations.
5. A later closed-quarter quarterly file drops one listed form type: `updated`, no gate (D6).
6. A list value containing `|`: impossible, because `|` is the field separator. No escaping rule is needed.

### 4.5 Release compatibility

- The 1c release refuses the v2 config, because its settings require `sec-index-v1`. After a v2 run has written to
  a store, selecting the 1c release again for that store is unsupported. This is stated in parent §4.9, as earlier
  releases are.
- Generation, manifest, receipt, selection, Attempt and outcome formats change only in their `schema_version`
  value and the data and changes file schemas. Exit codes are unchanged.

## 5. Verification (offline)

The offline checker gate covers, with synthetic fixtures:

1. Both classes merge: a combined filing and a company rename, in quarterly and daily families.
2. A filing-date conflict inside one source still quarantines the whole source, with the line and reason.
3. Order independence: permuted lines and batch boundaries give byte-identical generations.
4. Merging never crosses sources: a daily and a quarterly source that disagree give the quarterly row unchanged.
5. A v1 generation reads back byte-identically on the new release. A v2 generation reads back with lists.
6. A v2 candidate on a v1 base: unchanged keys are `provenance_refreshed`, a real change is `updated`.
7. A closed-quarter quarterly that drops one form type is `updated`, with gate `clear`.
8. Rollback from a v2 generation to a v1 generation, then a new v2 publish on it.
9. Two-release continuation: the new release continues 1c-origin pending work on a fixture store the 1c release
   wrote. The 1c release refuses the v2 config.
10. Existing duplicate-quarantine tests (`test_etl_transform.py`, `test_workflow_processing.py`) are updated, not
    deleted: form-or-name repeats now pass, and other repeats still refuse.

The full existing suite passes on the release. Offline preflight passes with the release selected.

## 6. Release and exit evidence

**Scratch re-transform (release evidence, not a gate test; 1c spec §5 item 7 is the pattern).** Take a consistent
copy of the store outside `data/` with no writer running. On the copy, transform each of the 35 sources with the
new release, through the installed engine's low-level commands, and record per source: row count, distinct keys,
keys merged by class, and wall time. Then, on the copy:

- **2023Q1** (both classes, no active generation): publish and read back with `capture_quarter` and
  `read_quarter`. Its gate is `clear`, because no active key can be withdrawn.
- **2026Q3** (largest file, daily-only v1 base): build the candidate. It is expected to stop at
  `awaiting_approval`, because 48 active daily keys are absent from the quarterly file and parent §4.4 makes them
  closed-quarter withdrawals. Validate the gated candidate's content directly and record its change counts. Do not
  approve it, not even on the copy, because approvals belong to Stage 4. The pointer stays on the v1 generation.

Record change counts and the full-rebuild wall time for both.
Expected result: all 35 sources transform. No source stays quarantined. If one does, the evidence names its reason,
and that reason must be something other than a repeat that differs only in form type or company name.

**Budget stop rule.** The budget for one first-v2 full rebuild is 1,500 s: the 3,300 s launcher default minus the
1,800 s reserve. If either measured full rebuild (2023Q1 or 2026Q3) exceeds 1,500 s, the Exit is not met. The stage
stops before the release and asks the owner to choose one of two paths. Either the owner approves a named limit
backed by the measured time, or the stage adds a cost fix and measures again. This follows the Stage 1b pattern.
The release and the Handoff record the measured times and the path taken.

**Release.** A content-addressed release from `main` with setup, preflight and review evidence under
`specs/evidence/stage2a/`, in the 1c layout. The 1c release and older releases stay retained.

**Live-config selection.** `release_manifest` and `etl.parser_version` / `etl.schema_version` change together in
`conf/sec-edgar-local.json`. Offline preflight confirms the new effective-config SHA-256. No workflow runs on the
live store.

**Handoff to Stage 2b.** The plan's Handoff names at least: the release ID and commit; the config hash; the
measured re-transform and full-rebuild times from the scratch run, against the 1,800 s reserve and the 3,300 s
launcher default; that every quarter's first v2 publish is a full rebuild, with every source of its active
generation re-transformed; that the 26 daily-only v1 generations stay readable and will change only by
`provenance_refreshed` or real changes; that the 1c release cannot be selected again once v2 is written; that a closed
quarter whose active daily-only generation holds keys absent from its quarterly file will stop at
`awaiting_approval` on its first quarterly publish (2026Q3 is the measured case), which is existing §4.4 behavior,
not a v2 effect; and the traps of plan 2's Handoff that still apply.

**Deferred items.** Item 1 stays open until Stage 2b covers or re-quarantines the 35 sources, per its "Done when".

## 7. Parent-spec amendments

At plan completion:

- **§4.4.** The published row becomes `sec-index-v2`, with `form_types` and `company_names` lists. The paragraph on
  duplicates becomes: identical observations collapse; observations of one key in one source that differ only in
  form type or company name merge into one row listing every value; any other conflicting duplicate quarantines the
  whole source. "No … conflict is silently dropped or assigned a winner" stays.
- **§4.8.** Parser / schema `sec-index-parser-v2` / `sec-index-v2`; the new release, commit and effective-config
  SHA-256.
- **§4.9.** A paragraph for this release: v1 generations stay readable; selecting the 1c release again for a store
  with v2 objects is unsupported.
- **§6.** Duplicate tests now cover merge and refusal.
- **§9.** Record this as the explicit versioned transition that §9 requires.

The runbooks `docs/runbooks/local-ingestion.md` and `release-upgrades.md` get the new versions and the
one-way release note.

## 8. Decisions

Owner answers at brainstorming, 2026-10-31:

- **Approach:** "A". One row per filing with list fields, under a new schema version.
- **S2 Platform:** "Yes". Hold the platform member off this release, as Stage 1c did.
- **Budget:** "Block the exit". A first-v2 full rebuild over 1,500 s stops the stage for an owner decision (§6).
- Roadmap defaults (x)–(xii), approved 2026-10-31: one stage, offline only; this stage takes deferred item 1 from
  Stages 3 and 4; Stage 2b covers the 35 sources; Stages 3–5 consume this release and the Stage 2b finding.

Calls made in writing this spec, for the owner's review:

- No scalar `form_type` or `company_name` in v2 (D2). A scalar beside the list would need a chosen value.
- The company-rename class is in scope, though deferred item 1 names only form types (§1.1).
- A filing-date conflict inside one source still refuses the source (D3).
- Observations become one-item-list v2 rows, so one row type runs from parser to reader (§4.1).
- A v1 generation stays a valid rollback target (§4.3).
- The scratch publish covers 2023Q1 (read back) and 2026Q3 (gated candidate, not approved) only, beyond the 35
  transforms the Exit needs (§6).
- `upgrade_row` keeps v1 version fields, so unchanged keys count as `provenance_refreshed` and retained rows keep
  true provenance (D8).
- `parse_fields` keeps a v1 path to re-derive retained v1 observations. The release never writes v1.

Approaches considered:

| Approach | What changes | Trade-off |
|---|---|---|
| A. One row per filing with lists (chosen) | `sec-index-v2`: `form_types`, `company_names`; key unchanged | Both classes under one rule. Corrections and gates keep their meaning. Readers must handle lists and a v1/v2 transition. |
| B. One row per form type | Key `(cik, archive_path, form_type)` | Plain string columns. Every key-uniqueness check changes. A dropped form type becomes a gated withdrawal. Renames need a second rule. |
| C. Keep one line by a fixed rule | §4.4 reversed to allow a winner | Cheapest. Drops true data, such as the SC TO-T listing, and works against platform R8. |

## 9. Rollout note

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a — on plan completion, tick the
> stage and re-validate later stages against what shipped.

Approval of this spec authorizes no SEC request, live run or campaign. Stage 2b's plan, written against this
release, and its owner gate stay the only route to live traffic on the new schema.
