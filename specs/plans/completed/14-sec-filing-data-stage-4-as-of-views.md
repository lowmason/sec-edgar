# Stage 4: As-of views — Implementation Plan

**Status: COMPLETE (2026-11-19)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 4 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** For any time `T`, return each record of the 2026Q3 sample and of its 20 in-quarter amendment partners that was public by `T`, with each answer bound to its manifests and source bytes.

**Architecture:** One root. `Layout` gains the Stage 4 paths under `ROOT/stage4/` and a `stage4_view`, a layout whose tables folder is `stage4/tables/`. `partners` writes the partner list from the Stage 3 tables and the sampled bytes. `fetch-partners` fetches the list under `STAGE4_LIMITS`. `partner-tables` writes the partner tables with the Stage 3 parse functions, and the `links` table. A `stage4` manifest names the `tables` manifest in `builds_on`, and `verify` checks it in three parts. `asof.answer` checks both sets against their manifests, then keeps the rows whose `known_from` is at or before `T`.

**Tech Stack:** Python 3.14, uv, `pyarrow` (already locked), and the standard library (`xml.etree.ElementTree`, `zoneinfo`, `json`, `random`, `hashlib`, `re`).

**Spec:** `specs/completed/sec-filing-data-stage-4-as-of-views.md` (approved 2026-11-19). Section 8 holds D1–D3 and the calls that the owner approved with the spec. Background: plan 13 (`specs/plans/completed/13-sec-filing-data-stage-3-manifests-and-pinning.md`) and its Handoff section.

## Global Constraints

- Stage 3's constraints carry over (spec section 3): Python 3.14 in the uv workspace. Runtime dependencies are `requests` and `pyarrow` only. Tests read only `tests/fixtures/` and temporary folders, and `tests/__init__.py` blocks sockets. Code paths below are under `packages/sec-filing-data/`.
- **Import order.** `ledger.py` imports no Stage 4 module, because `ownership` imports `ledger` (`ownership.py:15`) and `amendments` imports `ownership`. Stage 4 code may import `ledger`. `verify_stage4` imports `verify`, and `verify` imports `verify_stage4` only inside `run_verify` (Task 8).
- Only `client.py` and `fetch.py` import `requests`. Each new module (`amendments`, `partners`, `partner_tables`, `links`, `asof`, `verify_stage4`) joins the name set of `test_offline_modules_never_import_requests` (`tests/test_commands.py:866`) in the task that creates it. `cli.py` imports `fetch` only inside the handlers of `fetch`, `refetch` and `fetch-partners`, as `_run_fetch` does today. `fetch` never joins the module-level import of `cli.py`.
- **Clean-tree rule.** The handlers of `partners`, `fetch-partners`, `partner-tables` and `manifest --set stage4` call `_refuse_unless_clean()` first, before the `SEC_USER_AGENT` check and before `record_step`. `asof` is read-only. It never refuses for the tree state, and runs inside `record_step(layout, "asof")`. Add `["partners"]`, `["fetch-partners"]`, `["partner-tables"]` and `["manifest", "--set", "stage4"]` to `WRITING_ARGV` (`tests/test_version.py:34`).
- **One root** (spec section 3). Stage 4 never builds `Layout(ROOT/"stage4")`. Every Stage 4 path is a property of the one root, and `runs.jsonl`, `fetch.lock` and `manifests/` stay where they are.
- **Owner gate, the SEC budget (D2).** `STAGE4_LIMITS = Limits(30, 50_000_000)`. The client keeps 0.34 s between request starts. Only Task 11 sends SEC requests, and only through `fetch-partners`. No other task, implementer or review loop sets `SEC_USER_AGENT` or runs a `sec-filing-data` command on the live root. When the budget is spent, by the limit or by a hard kill, the run stops, and only the owner can set more.
- Exit codes: 0, 1, 2, 3, 5 and 6 keep their meanings. `fetch-partners` exits 5 and 6 as `fetch` does. `asof` exits 0 on an answer, 1 on a refusal and 2 on a usage error.
- **Frozen** (spec section 3). Nothing changes a file under `tables/`, `tables-stage1/`, `tables-stage2/`, `bytes/` or `stage2/`, a ledger line, a Stage 3 manifest or the input copy under `filing-data/inputs/`. The live run writes only under `ROOT/stage4/`, the file `ROOT/manifests/stage4@<commit12>.json` and `runs.jsonl` lines. Nothing touches `data/`, `backups/`, tag `ingest-parked-2026-11-16` or the `[build-system]` range of `sec-filing-data` (widened on purpose in `a477c54`). No committed line holds the User-Agent or the contact address.
- No stamp, manifest, `known_from` or `asof` result takes a value from the clock (spec anti-goal 7). Only `record_step` keeps its times.
- **Comparisons across types.** CIKs compare as integers: `index.cik` and `sample.cik` are int64, and XML CIKs and `parties.cik` are zero-padded text. Dates compare as dates: `index.date_filed` is a date, and `dateOfOriginalSubmission` is `YYYY-MM-DD` text. The 13F period compares header text with header text (`YYYYMMDD`), never with the XML `periodOfReport` (`MM-DD-YYYY`). Test fixtures use padded CIKs, so a test cannot pass on matching types.
- **CIK sets come from the index, grouped by accession, on both sides.** `sample.cik` keeps only the first index row's CIK, and never serves as a CIK set.
- Tests that break by design are updated, never loosened:
  - `tests/test_tables.py`: the fingerprint oracle gains two entries (Task 1).
  - `tests/test_report.py:448`, `:491` and `:499` iterate `STAGE3_TABLES` in place of `SCHEMAS` (Task 1).
  - The report gains a `## Stage 4` section before `## Versions` (Task 10). So `test_report.py:427` checks `titles[-6:]`, `test_commands.py:963` checks `titles[-6]`, and `test_xbrl.py:784` and `test_ownership.py:1145` check `titles[-8:-5]`.
  - The name set and `WRITING_ARGV`, as above.

  Every other test passes unchanged. That includes `ALL_EQUAL` (`tests/test_rebuild.py:157`), the 11 lines of `rebuild` on a root with no `stage4/` folder.
- Only the controller runs Task 11. The final whole-branch review and its fixes come before Task 11. Within one pass of Task 11, no commit lands between Step 2 and Step 10.
- The implementation PR opens only after Task 11 Step 12, when the findings and every Plan Completion Protocol commit are on the branch. It merges with a merge commit (spec section 3): `ccd_pr` `set_auto_merge` with `merge_method: "merge"`, or, under the PR lifecycle fallback, `gh pr merge <n> --merge --delete-branch`.
- Test command, from the worktree root: `uv run --locked --package sec-filing-data python -m unittest discover -s packages/sec-filing-data/tests -t packages/sec-filing-data`. The baseline is `Ran 415 tests` and `OK`. In each code task, Step 2 sees the new tests fail, and Step 4 sees `OK`.

## Review Focus

1. A partner fetch fails, for example with a 404. That partner is not held. Its `filings` row has outcome `not_found` and no records. It has no `links` row, and `asof` never returns its filing. Its `index` rows answer from `index_last_modified_at` with `held_in` `index`. Task 7 `test_a_failed_partner_never_answers`.
2. Two rules, or two sampled filings, choose the same partner. `partners` keeps one row for each. The fetch sends one request for it, and `fetches`, `filings` and `links` each hold one row for it. Task 2 `test_one_partner_chosen_twice_is_one_distinct_partner`, Task 3 `test_fetch_partners_walks_distinct_partners_in_accession_order`.
3. A hard kill leaves `stage4/bytes/<accession>.txt.part`. The next `fetch-partners` removes it, fetches the partner again, and leaves only the complete file. Task 3 `test_a_leftover_part_file_is_replaced`.
4. `--at` is not a valid time, for example `2026-02-30`, `2026-08-14T12:00` (no offset) or `soon`. `asof` prints one usage error, exits 2 and writes nothing. Task 7 `test_a_bad_at_is_a_usage_error`.
5. A step runs out of order: `fetch-partners` or `partner-tables` before `partners`, or `asof` before `manifest --set stage4`. Each prints one `error:` line and exits 1. The first two write nothing under `stage4/`. Task 3 `test_fetch_partners_needs_the_partner_list`, Task 4 `test_partner_tables_need_the_partner_list`, Task 7 `test_asof_refuses_before_the_stage4_manifest`.

## Decisions

- **D1** (owner, plan review, 2026-11-19): the plan is approved as written, with the calls C1–C16 and no change asked. Owner's words: "Approved". Applied in: Calls made in this plan.
- **D2** (owner, final review, 2026-11-19): skip the Codex second opinion. Owner's words: "Skip Codex (Recommended)". Applied in: the final whole-branch review, which ran the code-reviewer seat only.
- **D3** (owner, completion gate, 2026-11-19): keep `Declared.owner_ciks` as `()` when nothing is declared, and defer both lines that the final review declined to judge. Owner's words: "Keep () (Recommended)", "Defer as an item (Recommended)" and "Defer as an item (Recommended)". Applied in: `specs/deferred_items.md`, section `14-sec-filing-data-stage-4-as-of-views — 2026-11-19`.

## Calls made in this plan

Spec section 9 leaves these to the builder, and the advisor pass found the rest. The owner may correct any of them at the plan review.

- C1. Modules: `amendments.py` (the form sets, the declared values and the index grouping), `partners.py` (the rules of spec 5.2), `partner_tables.py` (spec 5.4), `links.py` (spec 5.5), `asof.py` (spec 5.6) and `verify_stage4.py` (spec 5.7). `fetch.py` gains the partner fetch. None of the new modules imports `requests`.
- C2. `Layout` gains `stage4`, `stage4_bytes`, `stage4_ledger`, `stage4_tables`, `partner_submission(accession)` and `stage4_view`. A new field, `stage4_tables_dir`, redirects `stage4_tables`, as `tables_dir` redirects `tables`. `write_table(layout.stage4_view, name, rows)` writes `stage4/tables/<name>.parquet`.
- C3. Commands: `partners`, `fetch-partners`, `partner-tables` (one command for spec 5.4 and 5.5) and `asof`. `manifest --set stage4`. `verify` reads the set from the manifest.
- C4. The partner row takes its columns from the accession's first index row (the lowest `line_number`), as `sample` does. Its `form_type` is the accession's form types, sorted and joined with `;`. Rows sort by accession, then by rule in `RULES` order, then by `sampled_accession`.
- C5. The rule forms. Rule 1 and `previous_accession`: `SCHEDULE 13D/A`, `SCHEDULE 13G/A`, `SC 13D/A`, `SC 13G/A` and `D/A`. Rule 2 and `original_date_issuer_owner`: `3/A`, `4/A` and `5/A`. `filer_period`: `13F-HR/A`. For a form type with several parts, the first part in sorted order that is in these sets picks the rule, as `ownership_form` does. So the 4 repeated `SC 13D/A;SC TO-T/A` filings take `previous_accession`, find no `edgarSubmission` document and fall to `none_declared`.
- C6. Element paths, from the live bytes (the spec's `typeOfFiling/newOrAmendment` sits under `offeringData`):

  | Form | Value | Path from the root |
  |---|---|---|
  | Schedule 13D/A, 13G/A | `previousAccessionNumber` | `edgarSubmission/headerData/previousAccessionNumber` |
  | Schedule 13D/A, 13G/A | `amendmentNo` | `edgarSubmission/formData/coverPageHeader/amendmentNo` |
  | D/A | `previousAccessionNumber` | `edgarSubmission/offeringData/typeOfFiling/newOrAmendment/previousAccessionNumber` |
  | 3/A, 4/A, 5/A | `dateOfOriginalSubmission` | `ownershipDocument/dateOfOriginalSubmission` |
  | 3/A, 4/A, 5/A | `issuerCik` | `ownershipDocument/issuer/issuerCik` |
  | 3/A, 4/A, 5/A | `rptOwnerCik` | `ownershipDocument/reportingOwner/reportingOwnerId/rptOwnerCik`, for each `reportingOwner` |
  | 13F-HR/A | `amendmentNo` | `edgarSubmission/formData/coverPage/amendmentNo` |
  | 13F-HR/A | `amendmentType` | `edgarSubmission/formData/coverPage/amendmentInfo/amendmentType` |
  | 13F-HR/A | period | header `CONFORMED PERIOD OF REPORT` |
  | 13F-HR/A | filer | the first `FILER` party of the header, as `extract_ownership` takes it |

  The document is `ownership.xml_document(raw, submission, root)`, and values are `ownership.text_at`, so the space in `NEW HOLDINGS` stays.
- C7. A `links` row sets `original_accession` only when its rule finds one accession. It finds one in the 2026Q3 index for `previous_accession` and `original_date_issuer_owner`, and among the held 13F-HR filings for `filer_period`. Otherwise `original_accession` and `original_held_in` are null, and `link_problem` says why. An original in the index that we do not hold keeps its `original_accession`, with `original_held_in` null and no `link_problem`. The order check of spec 5.5 runs only when both `accepted_at` values are present.
- C8. `known_from` comes from the filing's `filings` row: null when its outcome is not `ok`, else `last_modified_at`, else `fetched_at`. A held filing is an `ok` row of `tables/filings` or `stage4/tables/filings`. An `index` row of a sampled filing whose fetch is not `ok` is not held: it takes `index_last_modified_at` and `held_in` `index`, which is never early.
- C9. `links` already stores `held_in` (spec 5.5), and its value is the one that spec 5.6 would add. So `asof` keeps the stored column for `links` and adds only `known_from`.
- C10. `asof` output. Without `--table`, the summary goes to stdout. With `--table`, the summary goes to stderr and the rows go to stdout as JSON Lines, one object per row, in column order, with each `datetime` and `date` as its `isoformat()`.
- C11. The `stage4` manifest keeps `manifest_format` 1. It adds one key, `builds_on`, with `path` (under the root, POSIX) and `sha256`. Its outputs are the files under `stage4/tables/` only. Its inputs are the files under `stage4/bytes/` (kind `submission`) and `stage4/fetch-log.jsonl` (kind `ledger`). The `tables` manifest that it builds on is the one named by the code version in the stamps of `tables/`.
- C12. `rebuild` re-makes the Stage 4 tables from the Stage 3 tables that it has just re-made, so all 19 lines come from the inputs. Its 8 Stage 4 lines read `stage4 <name>: <result>`, because the names of five tables repeat Stage 3 names. A root with no `stage4/` folder gives the 11 lines of today.
- C13. Part 3 of `verify` derives a `links` row from the hashed tables `tables/index`, `tables/filings` and `tables/parties`, the partner records that it derives again from the Stage 4 bytes, and the amendment's own hashed bytes.
- C14. The report's `Stage 4` section comes after `Refetches` and before `Versions`. Versions lists the Stage 4 set only when `stage4/tables/` exists, with its own count line.
- C15. `asof` refuses a root with no `stage4/tables/` folder, as it refuses a missing manifest.
- C16. Tests control the fixture sample with a test patch of `sample.draw_sample` that keeps only the named sampled accessions. `run_sample`, `rebuild` and `verify` all look up `sample.draw_sample` at call time, so all three see the same sample.

---

### Task 1: Stage 4 paths, budget and table formats

**Files:** Modify `src/sec_filing_data/layout.py`, `ledger.py`, `tables.py`, `rebuild.py`, `report.py`. Tests: `tests/test_tables.py`, `tests/test_commands.py`, `tests/test_report.py`.

**Interfaces (produces):**
- `Layout(root, tables_dir=None, stage4_tables_dir=None)`. Properties: `stage4` is `root/"stage4"`, `stage4_bytes` is `stage4/"bytes"`, `stage4_ledger` is `stage4/"fetch-log.jsonl"`, and `stage4_tables` is `stage4/"tables"` or `stage4_tables_dir`. `partner_submission(accession: str) -> Path` is `stage4_bytes/f"{accession}.txt"`. `stage4_view -> Layout` is `Layout(root, tables_dir=stage4_tables)`.
- `ledger.STAGE4_LIMITS = Limits(30, 50_000_000)`, beside `STAGE2_LIMITS`.
- `ledger.filing_fetch_rows(filings: list[dict], records: list[dict], *, path_of: Callable[[str], Path], limits: Limits) -> list[dict]`: one `fetches` row for each entry of `filings`, in the given order. Each entry has `accession_number` and `form_type`. It is the body of today's `fetch_rows`, with `path_of` in place of `layout.submission` and `limits` in place of the default. `fetch_rows(layout, sample, records)` calls it with `sorted(sample, key=itemgetter("draw"))`, `layout.submission` and `STAGE1_LIMITS`, so its behavior does not change.
- `tables.SCHEMAS` gains, each with `TABLE_FORMATS` 1:
  - `partners`: `accession_number`, `form_type`, `cik` (int64), `company_name`, `date_filed` (date32), `filename`, `url`, `rule`, `sampled_accession`.
  - `links`: `accession_number`, `form_type`, `held_in`, `link_rule`, `declared_previous_accession`, `declared_original_date`, `declared_period`, `amendment_number`, `amendment_type`, `original_accession`, `original_held_in`, `link_problem`, `source_url`, `source_sha256`, `source_document`, then the five filing times (`_FILING_TIMES`). Every column other than the times is a string.
- `tables.STAGE3_TABLES`: the 11 names of today, in today's `SCHEMAS` order. `tables.STAGE4_TABLES = ("partners", "fetches", "filings", "parties", "documents", "ownership", "ownership_status", "links")`.
- `rebuild.REBUILT_TABLES = STAGE3_TABLES`. `report._versions` iterates `STAGE3_TABLES`.

- [x] **Step 1: Write the failing tests.**
  - `tests/test_tables.py`: `SCHEMA_FINGERPRINTS` gains `("partners", 1): "f0d74d67c35e1a6cbf341e07c517cc72ea178a209805c3b1e2707743bef40c5f"` and `("links", 1): "dee89c92c27f2d799d1d15f497edd260cb23db94e292a75c3a6c14438a2caa54"`. `test_each_schema_matches_its_format_number` is unchanged.
  - `test_stage4_paths_stay_under_one_root` (`test_tables.py`): for `Layout(Path("/r"))`, `stage4_bytes`, `stage4_ledger`, `stage4_tables` and `partner_submission("A")` are `/r/stage4/bytes`, `/r/stage4/fetch-log.jsonl`, `/r/stage4/tables` and `/r/stage4/bytes/A.txt`. `stage4_view.table("links")` is `/r/stage4/tables/links.parquet`. `stage4_view.runs`, `.lock` and `.manifests` are `/r/runs.jsonl`, `/r/fetch.lock` and `/r/manifests`. With `stage4_tables_dir=Path("/t")`, `stage4_view.table("links")` is `/t/links.parquet`.
  - `test_a_stage4_table_is_written_under_stage4` (`test_tables.py`): `write_table(layout.stage4_view, "partners", [])` makes `root/stage4/tables/partners.parquet`. Its `read_stamp` gives `table_format` `"1"`, and `root/tables/` does not exist.
  - `test_filing_fetch_rows_follow_the_order_and_limits` (`test_commands.py`): `fill_ledger` writes 30 matched pairs for keys that are not in the list. Two filings are given in reverse accession order, and the bytes of one sit at its `path_of` path. With `STAGE4_LIMITS`, the rows keep the given order, the file on disk reads `ok` with its path, and the other reads `budget`. With `STAGE1_LIMITS`, the other reads `not_attempted`.
  - `tests/test_report.py:448`, `:491` and `:499` iterate `STAGE3_TABLES`.
- [x] **Step 2: Run the test command.** Expected: failures and import errors in `test_tables` and `test_commands`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`, with `test_fetch_rows_follow_the_given_sample` and `ALL_EQUAL` unchanged.
- [x] **Step 5: Commit:** `feat(filing-data): add the Stage 4 paths, budget and table formats`
  > Deviation: `tests/test_manifest.py:20` also broke by design, because `sorted(TABLE_FORMATS)` gained the two new formats. It now reads `sorted(STAGE3_TABLES)`, the same 11 files (controller ruling).

### Task 2: Declared values and the partner list

**Files:** Create `src/sec_filing_data/amendments.py`, `partners.py`, `tests/stage4_root.py`, `tests/test_partners.py`. Modify `sample.py`, `cli.py`. Tests: `tests/test_commands.py` (the name set), `tests/test_version.py` (`WRITING_ARGV`).

**Interfaces:**
- Consumes: Task 1 `Layout.stage4_view`, `SCHEMAS["partners"]`. `ownership.xml_document`, `text_at`, `element_at`, `local_name`, `FILER_ROLE`. `envelope.parse_submission`.
- Produces:
  - `sample.ARCHIVES` (today's `_ARCHIVES`) and `sample.group_by_accession` (today's `_group_by_accession`), made public with no change in behavior.
  - `amendments.PREVIOUS_ACCESSION_FORMS`, `DATE_ISSUER_OWNER_FORMS`, `FILER_PERIOD_FORMS` (C5), and `CANDIDATE_FORMS = ("SCHEDULE 13D", "SCHEDULE 13G", "SC 13D", "SC 13G", "D", "3", "4", "5", "13F-HR")`.
  - `amendments.is_amendment(form_type: str) -> bool`: some `;` part ends in `/A`. `amendments.declaring_form(form_type: str) -> str | None` (C5).
  - `amendments.Declared` (frozen dataclass): `previous_accession`, `original_date`, `issuer_cik`, `owner_ciks: tuple[str, ...]`, `period`, `amendment_number`, `amendment_type`, `filer_cik`, `source_document`, `problem`. Every value is text as filed, or None. `problem` is `submission parse error: <message>`, or None.
  - `amendments.read_declared(form: str, raw: bytes) -> Declared`, by the paths of C6. A form outside C5 gives only `filer_cik` and `problem`.
  - `amendments.as_cik(text: str | None) -> int | None` (ASCII digits only) and `amendments.as_date(text: str | None) -> date | None` (a strict `YYYY-MM-DD` that is a real date).
  - `amendments.IndexFiling` (frozen dataclass): `first: dict`, `form_types: frozenset[str]`, `date_filed: date`, `ciks: frozenset[int]`. `amendments.index_filings(index_rows: list[dict]) -> dict[str, IndexFiling]`, grouped by accession with `sample.group_by_accession`.
  - `amendments.Match(accession: str | None, problem: str | None)`. `amendments.match_date_issuer_owner(declared: Declared, form: str, filings: dict[str, IndexFiling]) -> Match`: the one accession whose `form_types` hold `form.removesuffix("/A")`, whose `date_filed` is the declared date, and whose `ciks` equal the issuer CIK and every owner CIK. The problems, in order: `dateOfOriginalSubmission <text> is not a YYYY-MM-DD date`, `no issuerCik or rptOwnerCik`, `CIK <text> is not a number`, `no index match for <date> and CIKs <c1>, <c2>` (sorted) and `<n> index matches: <a>, <b>` (sorted).
  - `partners.RULES = ("original_previous_accession", "original_date_issuer_owner", "candidate_amendment")`.
  - `partners.choose_partners(index_rows: list[dict], sample: list[dict], read_sampled: Callable[[str], bytes | None]) -> list[dict]`. `read_sampled` gives a sampled filing's bytes, or None when they are not on disk. It skips `repeated` rows and never chooses a sampled accession. Rule 1 reads `previous_accession` and keeps it when the index lists it. Rule 2 uses `match_date_issuer_owner`. Rule 3 compares `index_filings[sampled].ciks`, never `sample.cik`, and keeps each accession whose `form_types` hold `<form>/A`, whose CIK set is equal and whose `date_filed` is on or after the sampled filing's. Row columns and order: C4, with `url` as `ARCHIVES + filename`.
  - `partners.distinct_partners(partners: list[dict]) -> list[dict]`: the first row of each accession, in accession order.
  - `partners.read_partners(layout: Layout) -> list[dict]`. A missing table raises `FileNotFoundError("<path> is missing: run partners first")`.
  - `partners.run_partners(layout: Layout) -> list[dict]` reads `index` and `sample` from `layout`, and each sampled file through `layout.submission`. It writes `partners` to `layout.stage4_view` and gives its rows.
  - CLI `partners --out ROOT` refuses first. Inside `record_step(layout, "partners")`, it prints `partners: <distinct accessions>`, then `<rule>: <rows>` for each of `RULES`, and exits 0.
  - `tests/stage4_root.py`, the submission builder and its XML parts:
    - `submission(form_type, *, accepted: str, filed: str, parties: list[tuple[str, str, str]], period: str | None = None, documents: list[tuple[str, str, bytes]] = ()) -> bytes`. `parties` holds (role, name, padded CIK). Each document is (type, filename, text), and an XML text is wrapped in `<XML>`.
    - `schedule13_xml(form, *, previous, amendment_no, issuer_cik)` with one `reportingPersonInfo`, `form_d_xml(*, previous)`, `form345_xml(form, *, original_date, issuer_cik, owner_ciks)` with one `nonDerivativeTransaction`, `form13f_cover_xml(form, *, amendment_no, amendment_type)` and `infotable_xml()` with one `infoTable`.

- [x] **Step 1: Write the failing tests** in `tests/test_partners.py`. Each test writes `index` and `sample` with `write_table`, and the sampled bytes under `bytes/`. Add `amendments` and `partners` to the name set, and `["partners"]` to `WRITING_ARGV`.
  - `test_read_declared_reads_each_form`: a `SCHEDULE 13D/A` gives `previous_accession` and `amendment_number` `"4"`. A `D/A` gives `previous_accession` from the `offeringData` path. A `4/A` gives `original_date` `"2026-07-06"`, `issuer_cik` `"0000763532"` and two `owner_ciks`. A `13F-HR/A` with header period `20211231` and XML `periodOfReport` `12-31-2021` gives `period` `"20211231"`, `amendment_number` `"1"` and `amendment_type` `"NEW HOLDINGS"`. An `8-K/A` with no XML gives every value None except `filer_cik`. Bytes with no `<SEC-HEADER>` give a `problem` that starts with `submission parse error:`.
  - `test_rule_1`: a sampled `D/A` names an accession that the index lists: one row with rule `original_previous_accession`. One that the index does not list gives none. One that names a sampled accession gives none.
  - `test_rule_2_compares_ciks_as_numbers_and_dates_as_dates`: the XML gives `0000000051` and `0000000052`, and the index rows give the int64 values 51 and 52. One `4` filed on the declared date under exactly {51, 52} gives one row. A `4` on another date gives none. Two such `4` filings give none.
  - `test_rule_3`: a sampled `SCHEDULE 13D` sits on index rows under CIKs 61 and 62, and its `sample.cik` is 61. Each of these `SCHEDULE 13D/A` candidates gives a row: one under {61, 62} filed later, and one filed on the same date. A candidate under {61, 62, 63}, one filed earlier and a sampled one give none.
  - `test_repeated_rows_and_partners_of_partners_are_skipped`: a `repeated` row of `SC 13D/A;SC TO-T/A` that names an indexed accession gives none. When rule 1 chooses a `D`, a `D/A` of the same CIKs that the index lists is not chosen, because the `D` is not sampled.
  - `test_one_partner_chosen_twice_is_one_distinct_partner` (Review Focus 2): two sampled `SCHEDULE 13D` filings with one CIK set choose the same `SCHEDULE 13D/A`. `choose_partners` gives two rows, and `distinct_partners` gives one.
  - `test_partners_command_writes_under_stage4`: `cli.main(["partners", ...])` returns 0 and prints the counts. `stage4/tables/partners.parquet` holds the rows, and the SHA-256 of each file under `tables/` and `bytes/` stays as it was.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.partners` not found.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): choose the in-quarter partners of the sampled filings`
  > Deviation: `Declared.owner_ciks` is `()` when nothing is declared, not None (D3). `form13f_cover_xml` in `tests/stage4_root.py` also takes `period_of_report`.

### Task 3: The partner fetch

**Files:** Modify `src/sec_filing_data/fetch.py`, `partners.py`, `cli.py`. Create `tests/test_fetch_partners.py`. Tests: `tests/test_version.py` (`WRITING_ARGV`).

**Interfaces:**
- Consumes: Task 1 `STAGE4_LIMITS`, `filing_fetch_rows`, `Layout.partner_submission`, `stage4_ledger`, `stage4_view`. Task 2 `read_partners`, `distinct_partners`. `client.SecClient`, `exclusive_lock`. Test helpers `FakeResponse`, `FixtureSession`, `FakeClock`, `fill_ledger`.
- Produces (in `partners.py`, never in `ledger.py`: see Global Constraints):
  - `partners.partner_fetch_rows(layout: Layout, partners: list[dict], records: list[dict]) -> list[dict]` is `filing_fetch_rows(distinct_partners(partners), records, path_of=layout.partner_submission, limits=STAGE4_LIMITS)`. `partners.build_partner_fetches(layout) -> list[dict]` reads `read_partners(layout)` and `read_ledger(layout.stage4_ledger)`. `partners.run_partner_fetches(layout) -> list[dict]` writes them as `fetches` to `layout.stage4_view` and gives them.
  - `fetch.run_fetch_partners(layout: Layout, *, user_agent: str, session=None, monotonic=time.monotonic, sleep=time.sleep) -> int`:
    1. `read_partners(layout)`, before the lock. A missing table raises, and nothing is sent or written.
    2. `exclusive_lock(layout.lock)`. A held lock raises `RuntimeError`, as in `run_fetch`.
    3. `layout.stage4.mkdir(exist_ok=True)`, then `try`:
       - Return 5 when `budget_spent(ledger_usage(layout.stage4_ledger), STAGE4_LIMITS)`.
       - Build `SecClient(user_agent, layout.stage4_ledger, ..., limits=STAGE4_LIMITS)`.
       - Walk `distinct_partners` in accession order. Skip a partner whose `partner_submission` exists. Unlink its `.part` file. Call `sec.fetch(url, dest, key=accession)`. `BudgetExhausted` gives 5, and `AccessDenied` gives 6.
    4. `finally`: `run_partner_fetches(layout)`.

    Return 0 after the walk.
  - CLI `fetch-partners --out ROOT`. Its checks, in order:
    1. The tree refusal gives 3.
    2. A missing `SEC_USER_AGENT` gives exit 2.
    3. It imports `fetch` inside the handler.

    Inside `record_step(layout, "fetch-partners")`, a `FileNotFoundError` prints `error: <message>` and exits 1. Then it prints `_print_fetch_outcomes` of the Stage 4 `fetches`, `stage 4 requests: <n> of 30` and `stage 4 wire bytes: <n> of 50000000`, and returns the code.

- [x] **Step 1: Write the failing tests** in `tests/test_fetch_partners.py`. Each test writes `partners` to `layout.stage4_view`. Add `["fetch-partners"]` to `WRITING_ARGV`.
  - `test_fetch_partners_walks_distinct_partners_in_accession_order` (Review Focus 2): three accessions, one of them on two rows, are written out of order. The session sees the three URLs once each, in accession order. The ledger keys follow the same order. `stage4/tables/fetches.parquet` has three `ok` rows in that order. `bytes/`, `fetch-log.jsonl`, `stage2/` and `tables/` do not exist.
  - `test_fetch_partners_stops_at_30_requests`: 31 accessions, each answered 200. The exit is 5 after 30 requests, and the 31st row reads `budget`.
  - `test_fetch_partners_stops_at_the_wire_byte_limit`: `fill_ledger` puts 48,000,000 wire bytes in the Stage 4 ledger. The first reply has a body of 1,500,000 bytes. The exit is 5, and the second row reads `budget`.
  - `test_fetch_partners_returns_5_at_once_when_spent`: the Stage 4 ledger holds 30 requests. The exit is 5, the session sees no call, and `fetches` is written.
  - `test_fetch_partners_skips_held_partners_and_tries_failed_ones_again`: in run 1, partner A gets a 404 and B gets 200. In run 2, the session sees only A's URL.
  - `test_a_leftover_part_file_is_replaced` (Review Focus 3): `stage4/bytes/<A>.txt.part` exists before the run. After it, only `<A>.txt` exists, with the reply's bytes.
  - `test_a_held_lock_refuses`: with `exclusive_lock(layout.lock)` held, `RuntimeError` is raised and `stage4/` does not exist.
  - `test_fetch_partners_exits_6_on_403`.
  - `test_fetch_partners_needs_the_partner_list` (Review Focus 5): with `SEC_USER_AGENT` patched to a test value and no `partners` table, `cli.main` returns 1. Stderr is `error: <path> is missing: run partners first`, and `stage4/` does not exist.
  - `test_fetch_partners_needs_a_user_agent`: with the variable unset, the exit is 2 and nothing is sent.
- [x] **Step 2: Run the test command.** Expected: failures in `test_fetch_partners` and `test_version`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): fetch the partner filings under the Stage 4 budget`
  > Deviation: `fetch._walk` takes `path_of`, so `fetch` and `fetch-partners` share one walk.

### Task 4: The partner tables and the Stage 4 fixture root

**Files:** Create `src/sec_filing_data/partner_tables.py`, `tests/test_partner_tables.py`. Modify `cli.py`, `tests/stage4_root.py`. Tests: `tests/test_commands.py` (the name set), `tests/test_version.py` (`WRITING_ARGV`).

**Interfaces:**
- Consumes: Task 3 `partner_fetch_rows`, `run_fetch_partners`. Task 2 `read_partners`, `distinct_partners`, `run_partners`, the submission builder. `submissions.filing_records`, `ownership.ownership_form`, `extract_ownership`, `ownership_rows`, `provenance.record_provenance`, `tables.as_table_rows`, `ledger.last_ok`, `read_ledger`.
- Produces:
  - `partner_tables.PartnerRecords(NamedTuple)`: `filing: dict`, `parties: list[dict]`, `documents: list[dict]`, `ownership: list[dict]`, `ownership_status: dict | None`.
  - `partner_tables.partner_records(partner: dict, fetched: dict, raw: bytes | None, ok_record: dict | None) -> PartnerRecords`. The first three come from `filing_records(partner, fetched, raw, ok_record)`. For a form type with an `ownership_form`, it calls `extract_ownership(form, fetched["outcome"], raw)`. The status row is as `run_ownership` writes it. The records are `ownership_rows(accession, form_type, extraction, record_provenance(as_table_rows("filings", [filing])[0]))`.
  - `partner_tables.run_partner_tables(layout: Layout) -> dict[str, int]` reads `read_partners(layout)` and the Stage 4 ledger once. It writes `fetches` (`partner_fetch_rows`), then `filings`, `parties`, `documents`, `ownership` and `ownership_status` to `layout.stage4_view`, one distinct partner at a time, in accession order. `raw` is the partner's bytes when its outcome is `ok`. It gives the row count of each table that it wrote.
  - CLI `partner-tables --out ROOT` refuses first. Inside `record_step(layout, "partner-tables")`, a `FileNotFoundError` prints `error: <message>` and exits 1. Otherwise it prints `<table>: <rows>` for each table written, in `STAGE4_TABLES` order, and exits 0.
  - `tests/stage4_root.py`:
    - The accessions: `SAMPLED_D_A = "0000000041-26-000002"` (D/A, CIK 41) names `PARTNER_D = "0000000041-26-000001"` (D). `SAMPLED_4_A = "0000000051-26-000009"` (4/A under CIKs 51 and 52, declared date 2026-08-04) finds `PARTNER_4 = "0000000051-26-000003"` (4, filed 2026-08-04). `SAMPLED_13D = "0000000061-26-000001"` (SCHEDULE 13D under CIKs 61 and 62) has `PARTNER_13D_A1 = "0000000061-26-000002"`, which names `SAMPLED_13D`, and `PARTNER_13D_A2 = "0000000061-26-000003"`, which names `PARTNER_13D_A1`. `SAMPLED_13F = "0000000071-26-000001"` (13F-HR, FILER 71, period 20260630) has `PARTNER_13F_A = "0000000071-26-000002"` (13F-HR/A, same filer and period). `SAMPLED_8K_A = "0000000081-26-000001"` has no XML. Every XML CIK is zero-padded.
    - `SAMPLED` and `PARTNERS` (tuples). `SUBMISSIONS: dict[str, bytes]` and `LAST_MODIFIED: dict[str, str]`, the `Last-Modified` header of each accession. `PARTNER_D`'s copy is last modified after `SAMPLED_D_A`'s, so that pair's amendment answers first. Every other original is last modified before its amendment.
    - `build_stage4_root(case: CommandTestCase, *, failing: frozenset[str] = frozenset()) -> Path`:
      1. Write the fixture zip with `write_zip`, and patch `index.INDEX_SHA256` and `INDEX_SIZE`, as `build_fixture_root` does.
      2. Patch `sample.draw_sample` (C16) with a wrapper that keeps the rows of `SAMPLED` from the real draw and numbers them again from 1.
      3. Run `index`, `sample`, the fetch (a `FixtureSession` that serves `SUBMISSIONS` with `LAST_MODIFIED`), `envelopes`, `facts`, `ownership` and `compare-refetches`.
      4. Run `run_partners`, `run_fetch_partners` (with `monotonic=case.clock.monotonic` and `sleep=case.clock.sleep`, as `build_fixture_root` passes them to `run_refetch`, and a 404 for each URL in `failing`) and `run_partner_tables`.

      It gives the zip path.
    - `Stage4RootTestCase(CommandTestCase)` builds it in `setUp`, as `self.zip_path`.

- [x] **Step 1: Write the failing tests** in `tests/test_partner_tables.py`, on `Stage4RootTestCase`. Add `partner_tables` to the name set, and `["partner-tables"]` to `WRITING_ARGV`.
  - `test_fixture_partners`: the partner rows are `PARTNER_D` by rule 1, `PARTNER_4` by rule 2, and `PARTNER_13D_A1`, `PARTNER_13D_A2` and `PARTNER_13F_A` by rule 3, each from its sampled filing. The Stage 4 `fetches` has 5 `ok` rows in accession order.
  - `test_partner_tables_match_their_namesakes`: each Stage 4 table has the schema `SCHEMAS[name]` and the stamp `table_format` of `TABLE_FORMATS[name]`. `filings` has the 5 partners in accession order. Each row has `accepted_at`, `public_at`, `fetched_at`, `source_url` (the partner's `url`), `sha256` (the file's SHA-256) and `last_modified_at` read from its `LAST_MODIFIED` value.
  - `test_partner_ownership_by_form`: `ownership` has rows for `PARTNER_4`, `PARTNER_13D_A1`, `PARTNER_13D_A2` and `PARTNER_13F_A`, and none for `PARTNER_D`, which also has no `ownership_status` row. Each ownership row's `source_sha256` and five times equal those of its `filings` row.
  - `test_partner_records_give_the_table_rows`: for each distinct partner, `as_table_rows` of each part of `partner_records(...)` equals that accession's stored rows, in order.
  - `test_a_failed_partner_is_not_held`: with `failing={PARTNER_13D_A2}`, its `fetches` and `filings` rows read `not_found`. It has no `parties`, `documents` or `ownership` rows, and its `ownership_status` row has reason `not_found`.
  - `test_partner_tables_write_only_stage4`: the CLI run returns 0. The SHA-256 of each file outside `stage4/`, except `runs.jsonl`, stays as it was, and `runs.jsonl` gains one `partner-tables` line.
  - `test_partner_tables_need_the_partner_list` (Review Focus 5): on a root with no `partners`, the CLI returns 1, stderr ends with `run partners first`, and `stage4/` does not exist.
  - `test_the_stage4_root_still_rebuilds_stage3`: `run_rebuild(layout, zip_path)` gives code 0, and its first 11 lines equal `ALL_EQUAL`.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.partner_tables` not found.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): write the partner tables with the Stage 3 parse code`
  > Deviation: `test_a_failed_partner_is_not_held` sits on a `CommandTestCase` that calls `build_stage4_root(self, failing=...)`, because a built root already holds the partner's bytes. The fixture adds one unrelated 10-K, which the draw wrapper drops.

### Task 5: The `links` table

**Files:** Create `src/sec_filing_data/links.py`, `tests/test_links.py`. Modify `partner_tables.py`. Tests: `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 2 `Declared`, `read_declared`, `declaring_form`, `is_amendment`, `IndexFiling`, `index_filings`, `match_date_issuer_owner`, `as_cik`. Task 4 `run_partner_tables`, `Stage4RootTestCase`.
- Produces:
  - `links.LINK_RULES = ("previous_accession", "original_date_issuer_owner", "filer_period", "none_declared")`.
  - `links.HeldFiling` (frozen dataclass): `accession_number`, `form_type`, `held_in`, `accepted_at: datetime | None`, `period_of_report: str | None`, `filer_cik: int | None` (the first `FILER` row of its `parties`, in table order).
  - `links.LinkContext` (frozen dataclass): `index: dict[str, IndexFiling]`, `held: dict[str, HeldFiling]`. `links.link_context(index_rows: list[dict], filings: dict[str, list[dict]], parties: dict[str, list[dict]]) -> LinkContext`. The keys of `filings` and `parties` are `sample` and `partner`, and only `ok` filings are held.
  - `links.amendment_filings(filings: list[dict]) -> list[dict]`: the `ok` rows whose form type `is_amendment`.
  - `links.link_row(filing: dict, held_in: str, raw: bytes, context: LinkContext) -> dict`, one `links` row:
    1. `form = declaring_form(form_type)`, and `declared = read_declared(form, raw)` when `form` is not None. The `declared_*`, `amendment_*` and `source_document` columns come from `declared`. `declared_period` and `amendment_type` are set for `13F-HR/A` only.
    2. `link_rule` is the rule of `form` (C5) when its value is present: `previous_accession`, `original_date`, or `period`. Otherwise it is `none_declared`, with `link_problem` from `declared.problem`, or null.
    3. The original:
       - `previous_accession`: the declared accession when `context.index` lists it, else the problem `not in the 2026Q3 index`.
       - `original_date_issuer_owner`: `match_date_issuer_owner`.
       - `filer_period`: the one held filing with form type `13F-HR`, the amendment's filer and the same `period_of_report`. Otherwise one of these problems: `no FILER party`, `no held 13F-HR of filer <cik> for period <period>` or `<n> held 13F-HR matches: <a>, <b>`.
    4. `original_held_in` is the original's `held_in`, or null (C7).
    5. A held original whose `accepted_at` is after the amendment's is no link. Both originals columns are null, and `link_problem` reads `<original> was accepted at <iso>, after this amendment at <iso>`.
    6. `source_url`, `source_sha256` and the five times come from `record_provenance` of the amendment's `filings` row.
  - `run_partner_tables` also writes `links`, sorted by accession. Its amendments are `amendment_filings` of `tables/filings` (held in `sample`, bytes through `layout.submission`) and of the Stage 4 `filings` that it has just built (held in `partner`, bytes through `layout.partner_submission`). The context reads `tables/index` and both sets of `filings` and `parties`.

- [x] **Step 1: Write the failing tests** in `tests/test_links.py`. Add `links` to the name set.
  - `test_fixture_links` (`Stage4RootTestCase`): the rows, as (accession, `link_rule`, `original_accession`, `original_held_in`, `link_problem`):
    - (`PARTNER_13D_A1`, `previous_accession`, `SAMPLED_13D`, `sample`, None)
    - (`PARTNER_13D_A2`, `previous_accession`, `PARTNER_13D_A1`, `partner`, None)
    - (`PARTNER_13F_A`, `filer_period`, `SAMPLED_13F`, `sample`, None)
    - (`SAMPLED_D_A`, `previous_accession`, `PARTNER_D`, `partner`, None)
    - (`SAMPLED_4_A`, `original_date_issuer_owner`, `PARTNER_4`, `partner`, None)
    - (`SAMPLED_8K_A`, `none_declared`, None, None, None)

    Each row's `source_sha256` is its amendment's file SHA-256, and its times equal its `filings` row. `PARTNER_13F_A` has `declared_period` `"20260630"` and `amendment_type` `"NEW HOLDINGS"`.
  - The cases below build a `LinkContext` from rows and call `link_row` on bytes from the submission builder:
    - `test_a_named_original_outside_the_index`: `original_accession` is null, `link_problem` is `not in the 2026Q3 index`, and `declared_previous_accession` keeps the value.
    - `test_rule_2_with_two_index_matches`: `link_problem` is `2 index matches: <a>, <b>`.
    - `test_rule_2_with_padded_ciks`: the XML gives `0000000051` and the index gives 51. The original is found.
    - `test_an_original_in_the_index_that_is_not_held`: `original_accession` is set, and `original_held_in` and `link_problem` are null.
    - `test_filer_period_compares_header_periods`: a 13F-HR/A with header `20211231` and XML `12-31-2021` links to a held 13F-HR of the same filer whose `period_of_report` is `20211231`. With no such filing, `link_problem` is `no held 13F-HR of filer 71 for period 20211231`.
    - `test_an_original_accepted_after_its_amendment_is_no_link`: both originals columns are null, and `link_problem` names both times.
    - `test_a_slash_a_filing_with_no_xml_is_none_declared`.
    - `test_a_repeated_form_type_picks_its_declaring_part`: `SC 13D/A;SC TO-T/A` with no XML gives `none_declared`. With an `edgarSubmission` that names an indexed accession, it gives `previous_accession`.
    - `test_amendment_filings_take_held_slash_a_filings_only`: a `not_found` `D/A` and an `ok` `D` are left out.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.links` not found.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): link each held amendment to the original its bytes declare`
  > Deviation: `filer_period` has a fourth problem text, `CIK <text> is not a number`, for a FILER CIK that is not a number.

### Task 6: The `stage4` manifest

**Files:** Modify `src/sec_filing_data/manifest.py`, `cli.py`, `tests/stage4_root.py`. Tests: `tests/test_manifest.py`, `tests/test_version.py` (`WRITING_ARGV`).

**Interfaces:**
- Consumes: Task 4 `Stage4RootTestCase`. Plan 13 `build_manifest`, `write_manifest`, `files_under`, `read_stamp`.
- Produces:
  - `manifest.STAGE4_SET = "stage4"`, and `SETS` gains it.
  - `manifest.set_folder(layout: Layout, set_name: str) -> Path` gives `layout.stage4_tables` for `stage4`, else `layout.root / set_name`. `build_manifest`, `find_manifest` and `asof` use it.
  - `manifest.set_version(folder: Path) -> str`: the one `code_version` in the stamps of the `*.parquet` files of `folder`. Several versions raise `ValueError` that names each one. No table raises `FileNotFoundError`.
  - `manifest.find_manifest(layout: Layout, set_name: str) -> Path` gives `manifest_path(layout, set_name, set_version(set_folder(layout, set_name)))`. A manifest that does not exist raises `FileNotFoundError` with its path.
  - `build_manifest(layout, "stage4", zip_path=None, stamp=...)` lists outputs from `set_folder`. `inputs` holds the files under `stage4_bytes` (kind `submission`) and `stage4_ledger` (kind `ledger`), sorted by path. `builds_on` is `{"path": <find_manifest(layout, "tables") under the root>, "sha256": <its SHA-256>}` (C11). A missing ledger or `tables` manifest raises `FileNotFoundError`, and the CLI's existing handler gives exit 1.
  - `tests/stage4_root.py`: `write_both_manifests(case) -> tuple[Path, Path]` writes the `tables` manifest (with `case.zip_path`) and then the `stage4` manifest. It gives both paths.

- [x] **Step 1: Write the failing tests** in `tests/test_manifest.py`, on `Stage4RootTestCase`. Add `["manifest", "--set", "stage4"]` to `WRITING_ARGV`.
  - `test_stage4_manifest_lists_outputs_inputs_and_builds_on`: the name is `stage4@5ca1ab1e5ca1.json`. The outputs are `stage4/tables/<name>.parquet` for each of `STAGE4_TABLES`, sorted, with stamps. The input kinds count `{"submission": 5, "ledger": 1}`, and no input has kind `index`. `builds_on` is `{"path": "manifests/tables@5ca1ab1e5ca1.json", "sha256": <that file's SHA-256>}`, and `manifest_format` is 1.
  - `test_stage4_manifest_needs_the_tables_manifest`: with no `tables` manifest, the CLI exits 1, stderr names `manifests/tables@5ca1ab1e5ca1.json`, and no `stage4` manifest exists.
  - `test_stage4_manifest_refuses_to_overwrite`: a second run exits 1, and the file's bytes stay as they were.
  - `test_stage4_takes_no_zip`: `--set stage4 --zip <zip>` exits 2.
  - `test_set_version_refuses_two_versions`: under commit `"b" * 40`, `links` is re-written. `set_version(layout.stage4_tables)` raises `ValueError` that names both versions.
- [x] **Step 2: Run the test command.** Expected: failures in `test_manifest` and `test_version`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`, with the Stage 3 manifest tests unchanged.
- [x] **Step 5: Commit:** `feat(filing-data): add the stage4 manifest that builds on the tables manifest`
  > Deviation: `manifest` also catches `ValueError`, so a set with two code versions gives one `error:` line and exit 1.

### Task 7: The as-of query

**Files:** Create `src/sec_filing_data/asof.py`, `tests/test_asof.py`. Modify `cli.py`. Tests: `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 6 `set_version`, `find_manifest`, `set_folder`, `write_both_manifests`. Task 1 `STAGE3_TABLES`, `Layout.stage4_view`. `times.NEW_YORK`, `tables.read_stamp`, `index.INDEX_LAST_MODIFIED_AT`.
- Produces:
  - `asof.ASOF_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership", "links")` and `asof.HELD_IN = ("sample", "partner", "index")`. The `tables` set gives the first six, and the `stage4` set gives `filings`, `parties`, `documents`, `ownership` and `links`.
  - `asof.AsOfRefused(Exception)`.
  - `asof.parse_at(text: str) -> datetime`, in UTC. A text that fully matches `\d{4}-\d{2}-\d{2}` and is a real date is the end of that day in New York: `datetime.combine(day + timedelta(days=1), time(0), tzinfo=NEW_YORK).astimezone(UTC) - timedelta(microseconds=1)`. Any other text goes to `datetime.fromisoformat`, and must give an offset. Otherwise it raises `ValueError` that quotes the text.
  - `asof.known_from(filing: dict) -> datetime | None` (C8).
  - `asof.ManifestUsed(set_name: str, path: Path, sha256: str)` and `asof.Answer(at: datetime, manifests: tuple[ManifestUsed, ...], tables: dict[str, pa.Table])`, both frozen dataclasses.
  - `asof.answer(root: Path, at: datetime) -> Answer`. A naive `at` raises `ValueError`. Steps:
    1. **Check.** For `tables`, then `stage4`: the set folder exists (C15). `set_version` gives one version. `find_manifest` gives a file, which is read as JSON and hashed. Each table file that the answer reads is read once as bytes. Its size and SHA-256 must equal its `outputs` entry, and `read_stamp` of the file must equal the entry's stamp. The table is parsed from those bytes. Last, the `stage4` manifest's `builds_on` path must be the `tables` manifest's path under the root, and its `sha256` must equal that file's SHA-256. Each failure raises `AsOfRefused` with a message that names the file, and no answer comes back.
    2. **Known from.** One map from accession to `known_from` comes from both `filings` tables. A row of `filings`, `parties`, `documents`, `facts`, `ownership` or `links` takes its accession's value, or null. An `index` row takes its accession's value and its set's `held_in` when the filing is held, else `index_last_modified_at` and `index`.
    3. **Answer.** Each table holds its rows with `known_from <= at`: the `tables` rows first, then the `stage4` rows. The stored columns come first and stay unchanged. Then `known_from` (`timestamp[us, tz=UTC]`), then `held_in` (string), which is `sample` for `tables` rows and `partner` for `stage4` rows. `links` keeps its stored `held_in` and adds only `known_from` (C9). The answer writes nothing.
  - CLI `asof --out ROOT --at T [--table NAME]`. `--at` uses an argparse type around `parse_at`, so a bad value exits 2. `--table` takes a name from `ASOF_TABLES`. It never refuses for the tree state. Inside `record_step(layout, "asof")`, `AsOfRefused` prints `error: <message>` and exits 1. The summary lines (C10):

    ```
    at: <at.isoformat()>
    manifest tables: <path> <sha256>
    manifest stage4: <path> <sha256>
    <table>: <n> rows, sample <n>, partner <n>, index <n>      (for each of ASOF_TABLES)
    ```

- [x] **Step 1: Write the failing tests** in `tests/test_asof.py`. Tests on `Stage4RootTestCase` call `write_both_manifests` first. Add `asof` to the name set.
  - `test_parse_at`:
    - `2026-08-14` gives `2026-08-15T03:59:59.999999Z` (EDT).
    - `2026-01-15` gives `2026-01-16T04:59:59.999999Z` (EST).
    - `2026-03-08` gives `2026-03-09T03:59:59.999999Z`, and `2026-11-01` gives `2026-11-02T04:59:59.999999Z` (the two clock changes).
    - `2026-08-14T12:00:00-04:00` and `2026-08-14T16:00:00Z` both give `16:00Z`.
    - `2026-08-14T12:00:00`, `2026-02-30`, `20260814` and `soon` raise `ValueError`.
  - `test_known_from`: an `ok` row with `last_modified_at` gives it. An `ok` row with a null `last_modified_at` gives `fetched_at`. A `not_found` row with both times set gives None.
  - `test_index_rows_take_their_filings_known_from`: at `INDEX_LAST_MODIFIED_AT` minus 1 µs, the `index` counts are the fixture's sampled rows as `sample` and its partner rows as `partner`, with `index` 0. At `INDEX_LAST_MODIFIED_AT`, the count is every `index` row.
  - `test_the_cutoff_is_inclusive`: a filing whose `known_from` is `K` answers at `K` and not at `K` minus 1 µs.
  - `test_an_answer_keeps_every_stored_value`: at 2026-11-19, for each table, the column names are the stored names plus `known_from` and `held_in` (for `links`, plus `known_from` only). With those columns dropped, the rows equal the stored rows of `tables/` and then `stage4/tables/`.
  - `test_the_pairs_answer_in_their_own_order` (spec 6, "The pair"): the forward pair `SAMPLED_13D` and `PARTNER_13D_A1`, at 1 µs before the earlier `known_from`, at a time between, and at the later `known_from`, answers neither, then the original only, then both. The reverse pair `SAMPLED_D_A` and `PARTNER_D` answers neither, then the amendment only, then both.
  - `test_answer_refuses_a_changed_table_file`: one byte appended to `tables/parties.parquet`, and separately `stage4/tables/links.parquet` re-written with one changed value. Each raises `AsOfRefused` that names the file.
  - `test_answer_refuses_a_missing_manifest`, `test_answer_refuses_two_versions_in_a_set` (one `tables/` file re-written under `"b" * 40`) and `test_answer_refuses_a_changed_builds_on` (the `tables` manifest re-written with an added key): each raises `AsOfRefused`.
  - `test_a_failed_partner_never_answers` (Review Focus 1): with `failing={PARTNER_13D_A2}`, at 2026-11-19 no table holds a row of it. Its `index` rows answer with `held_in` `index` at `INDEX_LAST_MODIFIED_AT`, and not 1 µs before.
  - `test_an_answer_before_every_known_from_is_empty`: at `2026-01-01`, every table has 0 rows and the two added columns.
  - `test_asof_prints_counts_and_rows`: without `--table`, stdout is the summary, and stderr is empty. With `--table filings`, stderr is that summary, and each stdout line parses as JSON with `known_from` as an ISO text.
  - `test_a_bad_at_is_a_usage_error` (Review Focus 4): `2026-02-30`, `2026-08-14T12:00` and `soon` each exit 2, and `runs.jsonl` does not exist.
  - `test_asof_refuses_before_the_stage4_manifest` (Review Focus 5): with only the `tables` manifest written, the exit is 1, and stderr names the missing `stage4` manifest.
  - `test_asof_runs_on_a_dirty_tree`: under `Checkout(TEST_COMMIT, False, "…")`, the exit is 0, and the run line has `tree_clean` False.
  - `test_asof_writes_only_its_run_line`: every file's SHA-256 stays as it was, except `runs.jsonl`, which gains one `asof` line.
  - `test_asof_never_loads_requests`: in a subprocess, `cli.main(["asof", ...])` prints `0` and `False` for `'requests' in sys.modules`.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.asof` not found.
- [x] **Step 3: Implement.** Compute `known_from` and the filters with `pyarrow.compute`, because `index` has 302,499 rows on the live root.
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): answer what was public by a given time`
  > Deviation: `manifest.set_version` names a table file that PyArrow cannot read. A fix round (`a6ed24f`) added a same-length change test, so a test reaches the SHA-256 refusal.

### Task 8: `verify` on the `stage4` manifest, parts 1 and 2

**Files:** Create `src/sec_filing_data/verify_stage4.py`, `tests/test_verify_stage4.py`. Modify `verify.py`. Tests: `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 6 `set_folder`, `STAGE4_SET`, `write_both_manifests`. Task 2 `is_amendment`.
- Produces:
  - In `verify.py`, these become public with no change in behavior: `guarded`, `failure`, `content_problem`, `stamp_problem`, `records_result`, `fetches_result`, `ledger_problem`, `difference`.
  - `run_verify` keeps its manifest read, its root check and its `seed` line. For a manifest whose `set` is `stage4`, every later line comes from `verify_stage4.check(layout, manifest, rows=rows, seed=seed)`, in place of the Stage 3 parts. `run_verify` imports `verify_stage4` inside the function. A comment says why: `verify_stage4` imports this module's checks, as `ownership.extract_ownership` imports its parsers.
  - `verify_stage4.STAGE4_READS = ("index", "sample", "filings", "parties")`, the `tables/` files that Stage 4 reads. `verify_stage4.BINDING_TABLES = ("filings", "parties", "documents", "ownership", "links")`.
  - `verify_stage4.check(layout, manifest, *, rows, seed) -> list[str]` gives `files: <result>`, `binding <table>: <result>` for each of `BINDING_TABLES`, then `binding fetches: <result>`. Task 9 adds the `rederive` lines.
  - **Part 1** gives the first failure, as `check_files` does:
    - Each output and input: `content_problem`.
    - `<path>: not listed`, for a file under `stage4/tables/` or `stage4/bytes/` that is not listed.
    - Each output stamp: `stamp_problem`.
    - `<builds_on path>: missing`, or `<builds_on path>: SHA-256 differs from the listed value`.
    - `tables/<name>.parquet: differs from <builds_on path>`, for each of `STAGE4_READS` whose size or SHA-256 differs from its output entry there.
    - `bytes/<accession>.txt: differs from <builds_on path>`, for each `sample` row that `is_amendment` whose file differs from its input entry there.
  - **Part 2.** `filings`, `parties`, `documents` and `ownership` use `records_result(layout.stage4_view, name, listed)`, where `listed` is the set of Stage 4 input SHA-256 values. A `links` row held in `partner` must bind to `listed`. One held in `sample` must bind to the `submission` inputs of the `builds_on` manifest. A failure reads `source_sha256 <hash> of <accession> matches no listed input`. `fetches` uses `fetches_result(layout.stage4_view, root, inputs)`.

- [x] **Step 1: Write the failing tests** in `tests/test_verify_stage4.py`, on `Stage4RootTestCase`, after `write_both_manifests` unless a test says otherwise. Add `verify_stage4` to the name set.
  - `test_an_untouched_stage4_root_passes`: the code is 0. The lines start `["seed: 20261119", "files: ok", "binding filings: ok", "binding parties: ok", "binding documents: ok", "binding ownership: ok", "binding links: ok", "binding fetches: ok"]`.
  - Each case below gives exit 1 and a line that names the file or row:
    - `test_a_changed_partner_byte_fails`: one byte appended to `stage4/bytes/<PARTNER_D>.txt`.
    - `test_an_unlisted_partner_file_fails`: `stage4/bytes/extra.txt` added.
    - `test_a_changed_index_table_fails`: after both manifests, `tables/index.parquet` re-written with one value changed. The `files:` line names `tables/index.parquet`.
    - `test_a_changed_tables_manifest_fails`: the `tables` manifest re-written with an added key. The `files:` line names its path.
    - `test_a_links_row_binds_by_its_set`: before the `stage4` manifest, the `SAMPLED_D_A` row of `links` is re-written with `held_in` `partner`. The `binding links:` line names `SAMPLED_D_A`.
  - `test_the_tables_manifest_still_verifies`: `verify` on the `tables` manifest of the Stage 4 root gives exit 0 and the Stage 3 lines.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.verify_stage4` not found.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`, with every `test_verify.py` test unchanged.
- [x] **Step 5: Commit:** `feat(filing-data): verify the stage4 manifest's files and hashes`
  > Deviation: a fix round (`c2de8bf`) added two tests that change a Stage 4 output file after the manifest. The `verify.py` helpers became public, so `verify_stage4` reuses them.

### Task 9: `verify` on the `stage4` manifest, part 3

**Files:** Modify `src/sec_filing_data/verify_stage4.py`. Tests: `tests/test_verify_stage4.py`.

**Interfaces:**
- Consumes: Task 2 `choose_partners`. Task 3 `partner_fetch_rows`. Task 4 `partner_records`. Task 5 `link_context`, `link_row`. `verify.draw_positions`, `RederiveError`, `difference`. `ledger.parse_ledger`, `last_ok`. `tables.as_table_rows`.
- Produces: `check` adds, after the binding lines, `rederive partners: <result>`, then `rederive <table>: <result>` for each of `BINDING_TABLES`. A pass reads `ok, <n> rows`. Steps:
  1. A `read_listed` like `verify._Sources.read_listed` reads each listed file once and hashes the bytes that it read. It serves the Stage 4 inputs and, through `builds_on`, the `tables/` outputs and the `submission` inputs of the `tables` manifest.
  2. **`partners`.** `choose_partners` runs on the rows of the hashed `tables/index` and `tables/sample` bytes (`pq.read_table(pa.BufferReader(data))`). `read_sampled` gives the hashed `bytes/<accession>.txt` of the `builds_on` manifest, or None when it is not listed. `as_table_rows("partners", derived)` must equal the stored table, row for row. A failure reads `rows: <n> against <m>` or `row <i> of <accession>: <difference>`.
  3. **Partner records.** `records = parse_ledger(<the Stage 4 ledger input>)`. `fetched` is `partner_fetch_rows(layout, derived partners, records)` by accession, and `ok_records = last_ok(records)`. Every partner's `partner_records` comes from the input whose SHA-256 is its fetch row's `sha256`.
  4. **`links`.** `link_context` reads the hashed `tables/index`, `tables/filings` and `tables/parties`, and the partner `filings` and `parties` of step 3 (C13). The amendment's `filings` row comes from the hashed `tables/filings` (`sample`) or step 3 (`partner`). Its bytes come from the input whose SHA-256 is the row's `source_sha256`.
  5. **Draw.** Each table of `BINDING_TABLES` draws `draw_positions(num_rows, rows, random.Random(seed))`. Each drawn row must equal one row of `as_table_rows(table, <its accession's derived rows>)`. A failure reads `row <position> of <accession>: <reason>`, as in Stage 3.
- [x] **Step 1: Write the failing tests.**
  - `test_an_untouched_stage4_root_passes` gains `rederive partners: ok, 5 rows`, then `rederive <table>: ok, <min(20, rows)> rows` for each of `BINDING_TABLES`.
  - `test_a_changed_partners_row_fails`: before the `stage4` manifest, `partners` is re-written with one `rule` changed. `files: ok` shows, and the `rederive partners:` line names that row.
  - `test_a_changed_links_value_fails`: before the `stage4` manifest, one `link_problem` is changed. With `rows=1000`, the `rederive links:` line starts `rederive links: row <i> of <accession>:`.
  - `test_rederive_reads_the_hashed_bytes`: after the manifests, a byte is appended to `stage4/bytes/<PARTNER_4>.txt`. With `rows=1000`, the `rederive filings:` line names that path.
- [x] **Step 2: Run the test command.** Expected: failures in `test_verify_stage4`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): re-derive the partner list and Stage 4 rows from the hashed bytes`

### Task 10: `rebuild`, the report and the README

**Files:** Modify `src/sec_filing_data/rebuild.py`, `report.py`, `README.md` (repository root). Tests: `tests/test_rebuild.py`, `tests/test_report.py`, and the four order checks of Global Constraints.

**Interfaces:**
- Consumes: Task 2 `run_partners`. Task 4 `run_partner_tables`. Task 5 `LINK_RULES`. Task 7 `known_from`. Task 1 `STAGE4_TABLES`, `STAGE4_LIMITS`.
- Produces:
  - `run_rebuild` uses `scratch = Layout(layout.root, tables_dir=<temp>/"tables", stage4_tables_dir=<temp>/"stage4")`. After the Stage 3 steps, when `layout.stage4.is_dir()`, it runs `run_partners(scratch)` and `run_partner_tables(scratch)`. For each of `STAGE4_TABLES`, it adds the line `stage4 <name>: <compare_table(live, rebuilt)>`, where live and rebuilt are read through each layout's `stage4_view`, or `stage4 <name>: no live table` (C12).
  - `report` gains `("Stage 4", _stage4)` between `Refetches` and `Versions` (C14). With no `stage4/tables/` folder, the section is `- no Stage 4 tables yet`. Otherwise its lines, in order:
    1. `- partners: <distinct> distinct, <rows> rows`, then `- partners by <rule>: <n>` for each of `RULES`.
    2. `- fetch <outcome>: <n>` for each non-zero outcome of `FETCH_OUTCOMES`, then `- Stage 4 requests: <n> of 30` and `- Stage 4 wire bytes: <n> of 50000000`.
    3. `- links: <n>`, then `- links by <rule>: <n>` for each of `LINK_RULES`, then `- original held in sample: <n>`, `- original held in partner: <n>` and `- original not held: <n>`.
    4. `- forward pairs: <n>`, `- reverse pairs: <n>` and `- other pairs: <n>`. Each is followed by one sub-line `  - <amendment> amends <original>` for each pair, in accession order. A pair is forward when the amendment is a partner and the original is sampled. It is also forward when both are partners and the original is a `candidate_amendment` partner of the same `sampled_accession` (spec 5.5). A pair is reverse when the amendment is sampled and the original is a partner.
    5. `- pairs whose amendment answers first: <n>`, each with `  - <amendment> (<known_from>) before <original> (<known_from>)`. Then `- pairs with equal known_from: <n>`, each with the same kind of sub-line.
    6. `- held filings: <n>`, then `- known_from before public_at: <n>` with one sub-line for each such accession, then `- no public_at: <n>`.
  - Versions: after the Stage 3 lines and their count lines, and only when `stage4/tables/` exists, it prints `- stage4 <table>: code <c>, format <f>, <rows> rows` (or `- stage4 <table>: no \`<table>\` table yet`) for each of `STAGE4_TABLES`. Then `- stage4 tables made at <c>: <n>`.
  - README, section `sec-filing-data`:
    - the four new commands with their flags and exits (`partners`, `fetch-partners`, `partner-tables`, `asof`), and `manifest --set stage4`.
    - the Stage 4 budget.
    - `verify` on a `stage4` manifest, and the 19 lines of `rebuild`.
    - an Output bullet for `stage4/`.
    - the write commands list, extended to `partners`, `fetch-partners`, `partner-tables`, with `asof` among the read-only commands.

- [x] **Step 1: Write the failing tests.**
  - `test_a_stage4_root_gives_19_equal_lines` (`test_rebuild.py`, `Stage4RootTestCase`): `(0, ALL_EQUAL + [f"stage4 {name}: equal" for name in STAGE4_TABLES])`, and the temporary parent is empty afterwards.
  - `test_a_changed_stage4_table_gives_exit_1`: with one `links` value changed in the live table, the line starts `stage4 links: row`, and the code is 1.
  - `test_report_stage4_section` (`test_report.py`, `Stage4RootTestCase`): the counts are 5 distinct partners (1, 1 and 3 by rule) and `fetch ok: 5`. There are 6 links (3, 1, 1 and 1 by rule), and originals held in sample 2, in partner 3 and not held 1. There are 3 forward pairs, 2 reverse and 0 other. One pair's amendment answers first (`SAMPLED_D_A` before `PARTNER_D`). `held filings: 10`, `known_from before public_at: 0` and `no public_at: 0`.
  - `test_report_without_stage4`: `build_fixture_root` gives the one line `- no Stage 4 tables yet`, and Versions has no `stage4` line.
  - `test_versions_cover_the_stage4_set`: on `Stage4RootTestCase`, Versions ends with 8 `- stage4 <table>: code 5ca1ab1e5ca1, …` lines and `- stage4 tables made at 5ca1ab1e5ca1: 8`.
  - The four order checks of Global Constraints.
- [x] **Step 2: Run the test command.** Expected: failures in `test_rebuild` and `test_report`.
- [x] **Step 3: Implement**, and write the README text (plain technical English).
- [x] **Step 4: Run** `sh scripts/check-sec-filing-data.sh`. Expected: `OK` and no whitespace errors.
- [x] **Step 5: Commit:** `feat(filing-data): rebuild and report the Stage 4 tables`
  > Deviation: the `rebuild` scratch keeps `tables_dir=<temp>` and puts the Stage 4 tables in `<temp>/stage4`, because `<temp>/tables` breaks `tests/test_rebuild.py:383` and `:393`. The `test_commands.py` order check sat at line 996, not 963.

### Task 11: The live run and the findings

Only the controller runs this task, after the final whole-branch review and its fixes (Global Constraints). Run each command from the worktree root, with these variables:

```bash
ROOT=/Users/lowell/Projects/sec-edgar/filing-data/2026Q3
ZIP=/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip
```

A command name below is short for `uv run --locked --package sec-filing-data sec-filing-data <command> --out "$ROOT"`.

- [x] **Step 1: Check the preconditions** (spec 5.9 step 1). Each item has its expected result:
  - `git status --porcelain -- packages/sec-filing-data pyproject.toml uv.lock .python-version` prints nothing. Record `git rev-parse HEAD` as the run commit.
  - `uv run --locked --package sec-filing-data python -c "import sec_filing_data; print(sec_filing_data.__file__)"` prints a path under `<worktree>/packages/sec-filing-data/src`.
  - `git -C /Users/lowell/Projects/sec-edgar check-ignore -q filing-data/x` exits 0.
    > Deviation: the check ran in the worktree, because the worktree guard refuses `git -C` on the main checkout. The branch has not changed `.gitignore` since `66f81c5`, the main checkout's commit.
  - `pgrep -fl '[s]ec-filing-data'` and `pgrep -fl '[s]ec_edgar'` print nothing (D2: no other SEC client).
  - `find "$ROOT" -name '.*'` prints nothing. On the first pass, `test ! -e "$ROOT/stage4"` holds.
  - `sh scripts/check-sec-filing-data.sh` gives `OK`.
  - Record:
    - `wc -l` and `shasum -a 256` of both ledgers.
    - the digest over `bytes/`, `(cd "$ROOT/bytes" && find . -type f | sort | xargs shasum -a 256 | shasum -a 256)`, which starts `c854e7e5`.
    - `shasum -a 256` of each file of `tables/` and of the three Stage 3 manifests.
    - `shasum -a 256 "$ZIP"`, which starts `526d2dbf2dd2e4c6`.
  - `verify --manifest "$ROOT/manifests/tables@c36aa2cf5571.json"` gives exit 0.
- [x] **Step 2: Partners** (step 2). `partners` prints `partners: 20`, `original_previous_accession: 2`, `original_date_issuer_owner: 2` and `candidate_amendment: 16`. Print `stage4/tables/partners.parquet` with `pyarrow`, and compare its (partner, form, date filed, rule, sampled filing) rows with spec Appendix A. A different list stops the run. Then it is a code fix, and no request is sent. Nobody edits Appendix A without the owner.
- [x] **Step 3: Fetch** (step 3). Set `SEC_USER_AGENT` with the command of README section Run (it reads tag `ingest-parked-2026-11-16`). Then run `fetch-partners`. Expected: exit 0, `ok: 20`, `stage 4 requests: 20 of 30` and less than 5,000,000 wire bytes. A failed partner may be fetched again by one more `fetch-partners` while requests remain. Exit 5 stops the run for the owner (spec section 3). So does exit 6.
  > Deviation: a wrapper script in the ignored execution workspace ran the README's `SEC_USER_AGENT` command and the fetch, so the value was never printed.
- [x] **Step 4: Partner tables and links** (step 4). `partner-tables` prints `fetches: 20`, `filings: 20` and `links: 43`. With `pyarrow`, the 27 `links` rows held in `sample` give the counts of spec 5.5:
  - The sampled D/A `0002065248-26-000003` and `0002135638-26-000005`, and 4/A `0000892251-26-000099` and `0001628280-26-051492`, link to their partners.
  - 14 have `link_problem` `not in the 2026Q3 index`.
  - `0000108985-26-000080` has `no index match for 2026-04-16 …`.
  - `0000905148-26-003942` has `no held 13F-HR of filer 1257391 for period 20211231`.
  - 7 are `none_declared`.

  Record the 16 partner amendments' links. Pin no expected link for `0001921640-26-000017`.
- [x] **Step 5: Rebuild** (step 5). `rebuild --zip "$ZIP"` gives exit 0 and 19 lines `equal`.
- [x] **Step 6: Manifest** (step 6). `manifest --set stage4`. Record its path and SHA-256. The name ends `@<run commit, first 12 characters>.json`.
- [x] **Step 7: Verify** (step 7). `verify` on the `stage4` manifest gives exit 0 with `seed: 20261119`, `files: ok`, 6 `binding … ok` lines, `rederive partners: ok, 20 rows` and 5 `rederive … ok` lines. `verify` on `tables@c36aa2cf5571.json` gives exit 0 with the Stage 3 lines.
- [x] **Step 8: As-of** (step 8). Run `asof --at <date>` for 2026-06-30, 2026-07-31, 2026-08-14, 2026-08-27, 2026-09-30, 2026-10-31 and 2026-11-19, and record each summary. Through 2026-09-30, `index` has at most 775 rows, with `index 0`. At 2026-10-31 and 2026-11-19, `index` has 302,499 rows. For each confirmed pair, run `asof --at <instant> --table filings` at 1 µs before the earlier `known_from`, between the two, and at the later `known_from`. Expected: neither, then the earlier filing only, then both. Record each pair whose amendment answers first, and each pair whose two values are equal, for which the middle instant does not exist.
- [x] **Step 9: Report** (step 9). The Stage 4 section shows `known_from before public_at: 0`. Record the section.
- [x] **Step 10: Check that the inputs did not change** (step 10). The ledgers, the `bytes/` digest, the `tables/` files, the Stage 3 manifests and `$ZIP` equal their Step 1 values.

  A result that differs is a problem to fix and record (spec 5.9). Fix it in a commit, and repeat Steps 1, 2 and 4–10 at the new commit. The fetch is not repeated for a partner that has bytes. A fix that would change a Stage 3 value is not a Stage 4 fix: the run stops, and the owner decides.
- [x] **Step 11: Write `specs/sec-filing-data-stage-4-findings.md`** (spec section 7). Its sections:
  - Run record: root, run commit and stamp.
  - Partners: the list, compared with Appendix A.
  - SEC use: requests and wire bytes from the Stage 4 ledger, against 30 and 50,000,000.
  - Partner tables and links: the counts, the links of the sampled amendments, and the confirmed pairs in each direction. If no forward pair is confirmed, the findings say so for the roadmap's completion review (spec 5.5).
  - Rebuild, Manifest and Verify.
  - As-of: the seven summaries and the pair checks.
  - Report, Inputs unchanged, and Measured cost (wall time from `runs.jsonl`, disk use).
  - Problems found and fixed.
  - Exit check: spec section 7's table, filled in.

  Commit: `docs(specs): record the Stage 4 run`.
- [x] **Step 12: Run the Plan Completion Protocol, then open the PR.** The protocol's commits touch only `specs/`, and all of them land before the PR opens. Stage 4 is the roadmap's last stage. So the 3a Handoff section records the three roadmap departures of spec section 10, then reads `None: last stage.` The resume handoff routes to the roadmap's completion review (derive-roadmap §6). The 16 held parked items of `specs/deferred_items.md` stay as they are. Then open the PR (Global Constraints), and run the PR lifecycle rule.

## Handoff to later stages

Roadmap departures (spec section 10). The roadmap's Stage 4 entry was not amended. That is derive-roadmap's job at the resume.

- Stage 4 sent live SEC requests under its own owner budget (D2 of the spec): 20 of 30 requests and 1,578,979 of 50,000,000 wire bytes, counted in `ROOT/stage4/fetch-log.jsonl` (`specs/sec-filing-data-stage-4-findings.md`, SEC use).
- Stage 4 holds 20 in-quarter partner filings beyond the 500-filing sample (D1 of the spec), in `ROOT/stage4/`, with their own ledger, tables and manifest. The roadmap's Stage 4 entry names the sample only.
- The Exit's amendment clause took the in-quarter reading (D1 of the spec). Originals in other quarters stay out. On the live root, 10 forward and 4 reverse pairs confirmed, and 23 sampled amendments keep a `link_problem` or `none_declared` (findings, Partner tables and links).

None: last stage.
