# Stage 2: Provenance and Timing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 2 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Give every record of O1–O4 its source URL, its source SHA-256 and its filing times, prove that the tables re-derive from the kept bytes with no SEC request, and run the one V6 refetch, all on the Stage 1 root.

**Architecture:** The Stage 1 steps gain the new columns in place (spec D4). A pure `times.py` holds the time rule. `envelopes` writes the times on `filings`, `parties`, `documents` and the sampled `index` rows, and `facts` and `ownership` copy them from `filings`. A live `refetch` command writes only under `ROOT/stage2/`, against its own ledger and limits. The offline `compare-refetches`, `check-stage1` and `rebuild` commands never load the SEC client.

**Tech Stack:** Python 3.14, uv, `requests` and `pyarrow` (already locked), and the standard library (`zoneinfo`, `email.utils`, `zipfile`, `struct`, `tempfile`, `unittest`).

**Spec:** `specs/sec-filing-data-stage-2-provenance-and-timing.md` (approved 2026-11-17). Its section 9 holds D1–D6. Background: plan 10 (`specs/plans/completed/10-sec-filing-data-stage-1.md`), its Handoff section, and its "Root layout and tables". Roadmap departure (spec section 11): D5 adds the `master.zip` receipt, as committed constants, to Stage 2's Consumes. The completion's Handoff section notes it.

## Global Constraints

- Stage 1's constraints carry over (spec section 3): Python 3.14 in the uv workspace; runtime dependencies `requests` and `pyarrow` only; the client rules (declared User-Agent, request starts at least 0.34 s apart, at most 5 attempts, timeouts `(15, 60)`, 268,435,456 decoded bytes per response); tests read only `tests/fixtures/` and temporary folders, with sockets blocked by `tests/__init__.py`.
- Only `client.py` and `fetch.py` import `requests`. Each new module joins the name set that `test_offline_modules_never_import_requests` asserts, in the task that creates it.
- SEC budget for Stage 2 (D2): "at most 20 requests and 50,000,000 wire bytes, at most 3 requests a second, and no other SEC client running. Every attempt counts, retries included." Stage 2 counts in its own ledger, `ROOT/stage2/fetch-log.jsonl`. Stage 1's ledger and its 1,500-request limit stay as they are. Planned use: 1 request, the V6 refetch of `9999999995-26-002992` (D6).
- No committed line holds the User-Agent or the contact address. From the `master.zip` receipt, Stage 2 copies only its URL, receive time and `Last-Modified`, as constants. No code or test reads the receipt or any other part of the parked store. `--zip` is the plain file that Stage 1 read (Task 9), read in place and checked by size and SHA-256.
- Time-zone conversion uses `zoneinfo.ZoneInfo("America/New_York")`.
- Anti-goals (spec section 2): no step changes an as-filed value or replaces it with a derived one. No `public_at` is earlier than its filing's acceptance. The rule time is never labeled observed, and `Last-Modified` never labeled the public time. The rebuild sends no request and reads nothing from the network. Nothing changes or deletes a Stage 1 byte file or a line of the Stage 1 ledger.
- No table column takes its value from the clock at step time. Every time comes from a ledger, the bytes or a committed constant, so the rebuild reproduces it.
- `write_table` builds rows with `pa.Table.from_pylist(rows, schema=...)`, which writes null for a missing key and drops an unknown key. So a misspelled column name is silently null. Tests assert the new columns by value.
- Tests that assert whole rows (`filings`, `parties` and `documents` in `test_commands.py`, `fact_row` in `test_xbrl.py`, `ownership_row` in `test_ownership.py`, and `test_keeps_every_row` in `test_index.py`) gain the new columns. Never weaken one to a subset of keys.
- Lighter process (spec section 3): code runs from the working tree, a fix needs no release, and the run fixes each problem it finds. `specs/sec-filing-data-stage-2-findings.md` is the only evidence record. Only the controller runs Task 9. Implementer subagents and review loops never run a live command. Only `refetch` sends SEC requests.
- Test command, from the worktree root: `uv run --package sec-filing-data python -m unittest discover -s packages/sec-filing-data/tests -t packages/sec-filing-data`. The baseline is `Ran 222 tests` and `OK`. In each code task, Step 2 sees the new tests fail and Step 4 sees `OK`.

## Review Focus

1. A rebuild must leave the live root as it found it. Every file under `ROOT` keeps its bytes, except one new `runs.jsonl` line. This covers each live table and both ledgers. Task 8 `test_rebuild_leaves_the_root_unchanged`.
2. A live table is missing, or a rebuild step raises. The rebuild names the table or the error, exits 1 and removes its temporary folder. It does not crash with a traceback. Task 8 `test_missing_live_table_and_failed_step`.
3. A refetch is killed mid-request, so the Stage 2 ledger holds a request with no response. That request counts as 268,435,456 bytes. The next refetch is refused before it sends anything, with exit 5 (spec 6.3, "Known effect"). Task 6 `test_interrupted_refetch_refuses_the_next`.
4. Acceptance text is unreadable, or the filing date is missing or unreadable. The step gives defined times and does not crash. An unreadable acceptance shows in the report as an `ok` filing with a null `accepted_at`. Task 1 `test_unreadable_acceptance_and_filing_date`, and Task 7 `test_report_provenance_section`.
5. `index` is re-run alone after `envelopes`, which resets the sampled rows' filing times to null. The report's Provenance section counts those rows, so the loss is not silent. Task 7 `test_index_rerun_after_envelopes_shows_in_provenance`.

## Decisions

- **D1** (owner, plan review, 2026-11-17): the plan is approved as written, with the calls C1–C11 and no change asked. Owner's words: "Approved". Applied in: Calls made in this plan.

## Calls made in this plan

The spec leaves these to the builder (section 10), or does not cover them. The owner may correct any of them at the plan review.

- C1. Modules: `times.py` (the rule), `provenance.py` (what a record copies from its filing), `refetches.py` (the offline `refetches` table) and `rebuild.py`. None of them imports `requests`. The live `run_refetch` goes into `fetch.py`.
- C2. Limits: a `Limits(requests, wire_bytes)` value. `STAGE1_LIMITS` is the default for `SecClient` and `budget_spent`, and `STAGE2_LIMITS` is `Limits(20, 50_000_000)`. Both client checks read it (brief T1). `build_fetches` keeps the Stage 1 limits. `BUDGET_MARGIN` stays 1,048,576 (brief T2).
- C3. `index` writes the six index columns and null filing times. `envelopes` re-writes `index` with the five times on the rows of sampled accessions, when `index` exists. The rebuild runs `index`, `sample`, `fetches`, `envelopes`, `facts`, `ownership`, then `refetches`.
- C4. `facts` and `ownership` copy the times from the `filings` table, so they now run after `envelopes`. Without `filings` they stop with an error that names `envelopes`.
- C5. `Layout(root, tables_dir=None)` points the rebuild and `check-stage1` at another tables folder. The rebuild keeps `root`, so it reads the bytes and ledgers in place and `fetches.path` stays equal.
- C6. "Already refetched" means that the refetch file exists, or that the Stage 2 ledger holds any request record for that accession. So `refetch` sends one fetch (up to 5 attempts) for each accession, once. It never retries a failed refetch, and any retry is the owner's call.
- C7. The offline step that writes `refetches` is the command `compare-refetches`, so it cannot be confused with the live `refetch`.
- C8. Refetch changes: `changed_header_fields` lists header labels, `ACCEPTANCE-DATETIME`, `PRIVATE-TO-PUBLIC` and `parties`. `changed_documents` lists document sequence numbers, or `#<position>` when a document has no sequence. Each list is joined with `;`. Both are null unless the SHA-256 values differ, and they read `unparsed` when either copy does not parse.
- C9. Unreadable acceptance text gives a null `accepted_at` and rule `no_acceptance`. When `FILED AS OF DATE` is null or unreadable, step 3 of the rule uses `accepted_at` alone. An unreadable `Last-Modified` gives null. The report shows each of these cases.
- C10. A new `check-stage1 --out ROOT` command does spec 6.5 step 5. Step 2's frozen copy is a guarded `cp -R`.
- C11. The three new report sections come after "Platform checks".

## New columns

Columns are strings unless typed. `ts` is `timestamp[us, UTC]`. The five filing times are `accepted_at` ts, `public_at` ts, `public_rule`, `last_modified_at` ts and `fetched_at` ts. Each table appends its new columns after its Stage 1 columns, in this order:

| Table | Appended columns |
|---|---|
| `index` | `source_url`, `source_sha256`, `index_built_at` ts, `index_data_through`, `index_received_at` ts, `index_last_modified_at` ts, the five filing times |
| `filings` | `source_url`, `accepted_at` ts, `public_at` ts, `public_rule`, `last_modified_at` ts (its `fetched_at` and `sha256` stay where they are) |
| `parties`, `documents`, `facts` | `source_url`, `source_sha256`, the five filing times (the `source_document` of `facts` stays where it is) |
| `ownership` | `source_url`, `source_sha256`, `source_document`, the five filing times |
| `refetches` (new) | `accession_number`, `outcome`, `stage1_sha256`, `refetch_sha256`, `sha256_equal` bool, `stage1_last_modified_at` ts, `refetch_last_modified_at` ts, `refetched_at` ts, `changed_header_fields`, `changed_documents` |

`facts_status`, `ownership_status`, `sample` and `fetches` do not change.

---

### Task 1: The time rule

**Files:** Create `src/sec_filing_data/times.py`, `tests/test_times.py`. Modify `tests/test_commands.py` (the name set of the import test).

**Interfaces (produces):**
- `NEW_YORK = ZoneInfo("America/New_York")`; `PUBLIC_RULES = ("acceptance", "next_opening", "private_to_public", "no_acceptance")`.
- `accepted_at(acceptance_datetime: str | None) -> datetime | None`: 14 ASCII digits `YYYYMMDDHHMMSS`, read as New York time and returned in UTC. None for None, or for text that is not 14 digits or not a valid time (C9).
- `public_time(accepted: datetime | None, filed_as_of_date: str | None, *, private_to_public: bool) -> tuple[datetime | None, str]`: steps 1–5 of spec 6.1, in that order, so `private_to_public` wins over a missing acceptance. A null or unreadable `YYYYMMDD` makes step 3 use `accepted` alone (C9). The result is UTC.
- `last_modified_at(header: str | None) -> datetime | None`: an HTTP date, by `email.utils.parsedate_to_datetime`, in UTC. None for None or unreadable text.

- [ ] **Step 1: Write the failing tests** in `tests/test_times.py`, with `utc(*parts)` short for `datetime(*parts, tzinfo=UTC)` and `pt(accepted, filed)` for `public_time(accepted, filed, private_to_public=False)`. Add `times` to the name set in `test_offline_modules_never_import_requests`.
  - `test_same_day_acceptance`: `accepted_at("20260814160523") == utc(2026, 8, 14, 20, 5, 23)`; `pt(that, "20260814") == (utc(2026, 8, 14, 20, 5, 23), "acceptance")`.
  - `test_date_moved_to_the_next_weekday`: `pt(accepted_at("20260813173512"), "20260814") == (utc(2026, 8, 14, 10, 0), "next_opening")`.
  - `test_date_moved_past_a_weekend`: `pt(accepted_at("20260814190000"), "20260817") == (utc(2026, 8, 17, 10, 0), "next_opening")` (Friday to Monday).
  - `test_effect_case`: `pt(accepted_at("20260918001500"), "20260917") == (utc(2026, 9, 18, 10, 0), "next_opening")`.
  - `test_at_or_after_2200`: `pt(accepted_at("20260814220000"), "20260814") == (utc(2026, 8, 15, 10, 0), "next_opening")`; `pt(accepted_at("20260814215959"), "20260814") == (utc(2026, 8, 15, 1, 59, 59), "acceptance")`.
  - `test_private_to_public`: `public_time(utc(2026, 8, 14, 20, 5, 23), "20260814", private_to_public=True) == (None, "private_to_public")`, and the same with `None` accepted.
  - `test_no_acceptance`: `pt(None, "20260814") == (None, "no_acceptance")`.
  - `test_summer_and_winter_offsets`: `accepted_at("20260814160523") == utc(2026, 8, 14, 20, 5, 23)`; `accepted_at("20261215160523") == utc(2026, 12, 15, 21, 5, 23)`.
  - `test_last_modified_parse`: `last_modified_at("Fri, 18 Sep 2026 10:03:06 GMT") == utc(2026, 9, 18, 10, 3, 6)`; `None` and `"not a date"` give None.
  - `test_unreadable_acceptance_and_filing_date` (Review Focus 4): `accepted_at` gives None for `"2026081416052"`, `"20261332160523"`, `"2026-08-14 16:05"` and `""`. `pt(utc(2026, 8, 15, 3, 10), None)` and `pt(utc(2026, 8, 15, 3, 10), "2026-08-14")` both give `(utc(2026, 8, 15, 10, 0), "next_opening")`.
  - `test_public_time_is_never_before_acceptance`: for each hour 0–23 of 2026-08-14 New York time and each filing date `"20260813"`, `"20260814"` and `"20260817"`, `public_at >= accepted`.
- [ ] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.times` not found.
- [ ] **Step 3: Implement** `times.py`.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the filing time rule`

### Task 2: Client limits as parameters

**Files:** Modify `src/sec_filing_data/ledger.py`, `client.py`; `tests/test_client.py`, `tests/test_commands.py`.

**Interfaces (produces):**
- `ledger.py`: `Limits(requests: int, wire_bytes: int)` (frozen dataclass); `STAGE1_LIMITS = Limits(MAX_REQUESTS, MAX_WIRE_BYTES)`; `STAGE2_LIMITS = Limits(20, 50_000_000)`; `budget_spent(usage: Usage, limits: Limits = STAGE1_LIMITS) -> bool`. `MAX_REQUESTS` and `MAX_WIRE_BYTES` stay, so the Stage 1 tests keep their imports.
- `client.py`: `SecClient(..., limits: Limits = STAGE1_LIMITS)`. `_usage_with_room` (before each attempt) and `_copy_body` (between body pieces) read the instance's limits, and their messages name them (brief T1).

- [ ] **Step 1: Write the failing tests.** `ClientTestCase.make_client(session, **options)` passes `options` to `SecClient`.
  - `test_stage2_limits_refuse_the_21st_request`: `fill_ledger(self.ledger, [0] * 20)`; a client with `limits=STAGE2_LIMITS` raises `BudgetExhausted`; `session.calls == []`.
  - `test_stage2_limits_stop_inside_the_stream`: `fill_ledger(self.ledger, [50_000_000 - 3 * MIB])`; a 10 × 1 MiB body raises `BudgetExhausted`; `ledger_usage(self.ledger).wire_bytes <= 50_000_000`; no `dest` and no `.part` file.
  - In `test_budget_rule_matches_the_client`, add: `budget_spent(Usage(19, 0), STAGE2_LIMITS)` is False; `Usage(20, 0)` and `Usage(0, 50_000_000 - ledger.BUDGET_MARGIN + 1)` are True.
- [ ] **Step 2: Run the test command.** Expected: failures for the three tests.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`, with every Stage 1 client test unchanged.
- [ ] **Step 5: Commit:** `feat(filing-data): take the request and byte limits as parameters`

### Task 3: Filing times and provenance in `envelopes`

**Files:** Create `src/sec_filing_data/provenance.py`. Modify `tables.py`, `ledger.py`, `submissions.py`; `tests/test_commands.py`.

**Interfaces:**
- Consumes: Task 1 `accepted_at`, `public_time`, `last_modified_at`.
- Produces:
  - `tables.py`: `FILING_TIME_COLUMNS = ("accepted_at", "public_at", "public_rule", "last_modified_at", "fetched_at")`. The `filings`, `parties` and `documents` columns follow "New columns".
  - `ledger.py`: `ok_responses(path: Path) -> dict[str, dict]` returns the last `ok` response record of each key. `build_fetches` uses it in place of its own loop.
  - `provenance.py`:
    - `filing_times(filing: dict) -> dict` returns the five times of a `filings` row.
    - `record_provenance(filing: dict) -> dict` returns `source_url`, `source_sha256` (the row's `sha256`) and the five times.
    - `read_provenance(layout: Layout) -> dict[str, dict]` returns `record_provenance` of each `filings` row, by accession. When `filings` is missing it raises `FileNotFoundError`, with a message that names its path and says to run `envelopes` first.

Values, for each `filings` row:
- `source_url` is `sample.url`, on every row.
- `last_modified_at` is `last_modified_at(ok_responses(layout.ledger)[accession]["last_modified"])` on `ok` rows that have an `ok` record. Otherwise it is null. Only the Stage 1 ledger is read.
- `accepted_at`, `public_at` and `public_rule` come from `accepted_at` and `public_time`, on `ok` rows with a parsed header. On every other row they are null.
- `parties` and `documents` rows add `record_provenance(filing)` of their filing.

- [ ] **Step 1: Write the failing tests** in `EnvelopeTests`.
  - `test_envelopes_one_row_per_sampled_filing` gains the new keys. The parsed row has `source_url` = its `url`, `accepted_at` and `public_at` = `utc(2026, 8, 14, 20, 5, 23)`, `public_rule` `"acceptance"` and `last_modified_at` None (the fixture session sends no `Last-Modified`). The corrupt row has its `source_url`, null times and `public_rule` None. The `not_found` row has its `source_url` and null times. The `parties` and `documents` rows gain `record_provenance` of the parsed filing.
  - `test_filing_times_come_from_the_header_and_the_ledger`: the fetch reply is `FakeResponse(200, [FIXTURE_BYTES], {"Last-Modified": "Fri, 14 Aug 2026 20:06:00 GMT"})`. The filing has `last_modified_at == utc(2026, 8, 14, 20, 6)` and `fetched_at` equal to its `fetches` row. Each `parties` and `documents` row of it has `source_url` = its `url`, `source_sha256 == FIXTURE_SHA256`, and the filing's five times.
  - `test_read_provenance_needs_filings`: with no `filings` table, `read_provenance` raises `FileNotFoundError`, and the message holds `envelopes`. Add `provenance` to the name set of the import test.
- [ ] **Step 2: Run the test command.** Expected: failures in `EnvelopeTests`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add filing times and sources to the envelope tables`

### Task 4: The index columns

**Files:** Modify `src/sec_filing_data/index.py`, `sample.py`, `submissions.py`, `tables.py`, `cli.py`; `tests/test_index.py`, `tests/test_commands.py`.

**Interfaces:**
- Consumes: Task 3 `filing_times`.
- Produces:
  - `index.py` constants, with a comment that names the receipt path of spec 6.2 as their source:
    - `INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.zip"`
    - `INDEX_RECEIVED_AT = datetime(2026, 10, 31, 17, 54, 33, 39228, tzinfo=UTC)`
    - `INDEX_LAST_MODIFIED_AT = datetime(2026, 10, 31, 7, 50, 9, tzinfo=UTC)`
  - `member_mtime(info: zipfile.ZipInfo) -> datetime | None`: the UTC mtime in the `0x5455` extended-timestamp field of `info.extra` (the central directory). Walk the `(header ID, size)` blocks. When flags bit 0 is set and the size is at least 5, read bytes 1–5 as an unsigned little-endian `int`. Do not size the field from its flags. The real file has flags `3` and size `5`. None when there is no such field.
  - `read_index(...)`: each row gains `source_url` (`INDEX_URL`), `source_sha256` (the checked `sha256` argument), `index_built_at` (`member_mtime` of `master.idx`), `index_data_through` (the stripped value of the header line that starts `Last Data Received:`, or None), `index_received_at` and `index_last_modified_at`. It sets no filing time, so those columns are written as null.
  - `index.run_index(layout: Layout, zip_path: Path) -> list[dict]` writes `index` (with `INDEX_SHA256` and `INDEX_SIZE`) and returns its rows. `sample.run_sample(layout: Layout) -> list[dict]` writes `sample` and returns its rows. The CLI's `index` and `sample` commands call them and print what they printed before.
  - `run_envelopes` re-writes `index` when the table exists. The rows of an accession in `filings` take `filing_times` of that filing. Every other row and column stays as it is, in the same order.

- [ ] **Step 1: Write the failing tests.**
  - `test_keeps_every_row` gains `source_url` `INDEX_URL`, `source_sha256` the fixture zip's SHA-256, `index_built_at` None, `index_data_through` `"September 30, 2026"`, and the two receipt constants.
  - `test_extended_timestamp_gives_the_built_time`: write `master.idx` with `ZipInfo("master.idx", date_time=(2026, 10, 31, 3, 49, 36))` and `extra = struct.pack("<HHBI", 0x5455, 5, 3, 1793432975)`. `index_built_at == datetime(2026, 10, 31, 7, 49, 35, tzinfo=UTC)`. With no `extra`, it is None.
  - `test_envelopes_writes_filing_times_on_sampled_index_rows` (in `test_commands.py`): `index` has two rows for sampled accession A (two CIKs) and one row for an accession that was not sampled. After `fetch` and `envelopes`, both A rows carry `filing_times` of A's `filings` row. The other row has null filing times. Every other column and the row order equal the table written before.
  - The existing `index` and `sample` command tests pass through `run_index` and `run_sample`.
- [ ] **Step 2: Run the test command.** Expected: failures in the new and extended tests.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the index source and build times`

### Task 5: Facts and ownership provenance

**Files:** Modify `src/sec_filing_data/tables.py`, `facts.py`, `ownership.py`; `tests/test_xbrl.py`, `tests/test_ownership.py`.

**Interfaces:**
- Consumes: Task 3 `read_provenance`.
- Produces:
  - `ownership.py`: `XmlDocument(filename: str | None, text: bytes)` (frozen dataclass). `xml_document(raw, submission, root) -> XmlDocument | None` gives the document that it finds today, now with that document's filename.
  - `facts` rows add `read_provenance(layout)[accession]`. `ownership` rows add the same, plus `source_document` (the `XmlDocument.filename`). Both commands read `filings` (C4).

- [ ] **Step 1: Write the failing tests.**
  - `FactsRootTestCase.write_tables` also writes a `filings` table, with one row for each added filing. Each row has `source_url` = its `url`, `sha256` = `f"sha-{draw}"`, and five distinct fixed times. `FactsRootTestCase.provenance(accession) -> dict` returns `record_provenance` of that row. `fact_row(accession, source, fact, provenance)` and `ownership_row(accession, form_type, row, provenance, source_document)` merge their extra arguments, and each call site passes `self.provenance(...)` (and `"doc.xml"` for ownership).
  - `test_facts_carry_their_filing_provenance`: two filings with different times; each fact row carries its own filing's `source_url`, `source_sha256` and five times.
  - `test_ownership_names_its_source_document`: a Form 4 row has `source_document == "doc.xml"` and its filing's provenance.
  - `test_xml_document_gives_its_filename`: `xml_document(...).filename` is the found document's `<FILENAME>`. The 11 existing calls of `xml_document` read `.text`.
  - `test_facts_and_ownership_need_filings`: with no `filings` table, `run_facts` and `run_ownership` each raise `FileNotFoundError`, and the message holds `envelopes`.
- [ ] **Step 2: Run the test command.** Expected: failures in `test_xbrl` and `test_ownership`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add sources and filing times to facts and ownership`

### Task 6: Refetch and the `refetches` table

**Files:** Create `src/sec_filing_data/refetches.py`, `tests/test_refetch.py`. Modify `layout.py`, `fetch.py`, `cli.py`, `tables.py`; `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 2 `STAGE2_LIMITS` and `SecClient(limits=...)`. Task 3 `ok_responses`. Task 1 `last_modified_at`.
- Produces:
  - `Layout`: `stage2` (`root/"stage2"`), `stage2_ledger` (`stage2/"fetch-log.jsonl"`), `refetch_dir` (`stage2/"refetch"`), and `refetched(accession)` (`refetch_dir/f"{accession}.txt"`).
  - `fetch.run_refetch(layout: Layout, *, user_agent: str, accessions: Sequence[str], session=None, monotonic=time.monotonic, sleep=time.sleep) -> int`. Its steps:
    1. Before the lock and before any request, raise `ValueError("<accession> is not in sample")` for the first accession that is not in `sample`.
    2. Take `exclusive_lock(layout.lock)`, and create `layout.stage2`.
    3. Use `SecClient(user_agent, layout.stage2_ledger, limits=STAGE2_LIMITS, ...)`.
    4. Walk the accessions in order, with repeats dropped. Skip an accession that is already refetched (C6). Fetch each other one from its `sample.url` into `layout.refetched(accession)`.
    5. Return 0, `BUDGET_SPENT_EXIT` (5) on `BudgetExhausted`, or `ACCESS_DENIED_EXIT` (6) on `AccessDenied`.
  - `refetches.build_refetches(layout: Layout) -> list[dict]` gives one row per key with a request record in the Stage 2 ledger, in first-request order:
    - `outcome` is the key's last response outcome, with `retry` read as `failed`, or `no_response` when its last request has no response.
    - The Stage 1 values come from `ok_responses(layout.ledger)`. The refetch values come from `ok_responses(layout.stage2_ledger)`, and only when `layout.refetched(accession)` exists. `refetched_at` is the `at` of that refetch record.
    - `sha256_equal` is null unless both SHA-256 values exist. The change columns follow C8, from `parse_submission` of both files.
  - `refetches.run_compare_refetches(layout: Layout) -> int` writes `refetches`, with 0 rows when there is no Stage 2 ledger.
  - CLI:
    - `refetch --out ROOT --accession A [--accession A ...]` needs `SEC_USER_AGENT` (exit 2 without it, as `fetch` does) and imports `fetch` only inside its handler. An unknown accession prints `error: …` to stderr and exits 2. After the walk it prints `<accession>: <outcome>` for each named accession (`not refetched` when it has no `refetches` row), then `stage 2 requests: <n> of 20`.
    - `compare-refetches --out ROOT` prints `refetches: <rows>`.

- [ ] **Step 1: Write the failing tests** in `tests/test_refetch.py`. They use `CommandTestCase`, `FixtureSession` and `sample_row` from `test_commands.py`, and `fill_ledger` and `FakeResponse` from `test_client.py`. Each test first fetches a two-row sample (A and B) in Stage 1. Add `refetches` to the name set of the import test.
  - `test_refetch_writes_only_under_stage2`: refetch A. `refetched(A)` holds the fixture bytes. The Stage 2 ledger holds 1 request and 1 response. The Stage 1 ledger's bytes, and the names and SHA-256 of the files under `bytes/`, equal what they were before.
  - `test_refetch_refuses_an_unknown_accession`: it raises `ValueError`, the session got no call, and no `stage2` folder exists.
  - `test_refetch_refuses_the_21st_request`: `fill_ledger(layout.stage2_ledger, [0] * 20)`. The refetch of A returns 5 with no session call.
  - `test_interrupted_refetch_refuses_the_next` (Review Focus 3): the Stage 2 ledger holds one request record for A with no response. The refetch of B returns 5 with no session call, and the Stage 2 ledger is unchanged.
  - `test_each_refetch_happens_once`: refetch `[A, A]`, then A again, then A once more after its file is deleted. There is 1 session call in all.
  - `test_refetch_takes_the_fetch_lock`: with `layout.lock` held, it raises `RuntimeError` and writes nothing.
  - `test_refetches_gives_an_equal_row_and_a_changed_row`: the Stage 1 replies are `xbrl_submission("1", [None])` with `Last-Modified` `Fri, 14 Aug 2026 20:06:00 GMT`. The refetch of A serves the same bytes, with `Last-Modified` `Sat, 15 Aug 2026 10:00:00 GMT`. The refetch of B serves `xbrl_submission("1", ["changed"], date_as_of_change="20260815")`. Row A has `sha256_equal` True, null change columns, and both `Last-Modified` times. Row B has `sha256_equal` False, `changed_header_fields == "DATE AS OF CHANGE"` and `changed_documents == "1"`.
  - `test_a_failed_refetch_gives_a_row`: a 404 gives `outcome` `not_found`, with null `refetch_sha256` and `sha256_equal`.
  - `test_stage2_never_reaches_the_stage1_tables`: after a refetch with another `Last-Modified`, `envelopes` gives the same `filings` rows as before.
  - CLI: `test_refetch_needs_a_user_agent` (exit 2 and nothing written), and `test_refetch_and_compare_refetches_print`, which uses `FixtureSession` through a patched `fetch.run_refetch`, as `test_commands_print_counts_and_record_steps` does.
- [ ] **Step 2: Run the test command.** Expected: failures in `test_refetch`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the refetch command and the refetches table`

### Task 7: The Stage 2 report sections

**Files:** Create `tests/test_report.py`. Modify `src/sec_filing_data/report.py`.

**Interfaces:**
- Consumes: Task 1 `PUBLIC_RULES`. Task 2 `STAGE2_LIMITS`. Task 4 `run_index`, `run_sample`. Task 6 `run_refetch`, `run_compare_refetches`, `Layout.stage2_ledger`.
- Produces:
  - `report` adds three sections, in this order, after "Platform checks". A missing table makes its line say `no \`<name>\` table yet`, as elsewhere. Gaps are whole seconds (`last_modified_at - public_at`). The median is `statistics.median_low`.
    - **Times**, over parsed `ok` filings:
      - `- <rule>: <n>` for each of `PUBLIC_RULES`;
      - `- filings with a null last_modified_at: <n>`;
      - `- gap from public_at to last_modified_at: least <a> s, median <b> s, largest <c> s`;
      - `- filings with a gap above 1 hour: <n>`, with one `  - <accession>: <s> s` line each;
      - `- filings with public_at after last_modified_at: <n>`, with one line per accession;
      - `- filings with public_at before accepted_at: <n>`, with one line per accession (an anti-goal, expected 0).
    - **Provenance**: one line per records table (`index`, `filings`, `parties`, `documents`, `facts`, `ownership`): `- <table>: <n> rows with a null source_url or source_sha256, <m> rows of ok filings with a null accepted_at or fetched_at`. For `filings`, the SHA-256 column is `sha256`. Then `- index rows with filing times: <n>` (rows with a non-null `fetched_at`). It reads only the columns it needs.
    - **Refetches**: one line for each `refetches` row, with all of its columns. Then `- Stage 2 requests: <n> of 20` and `- Stage 2 wire bytes: <n> of 50000000`, from `ledger_usage(layout.stage2_ledger)` and `STAGE2_LIMITS`. `_cost` stays as it is.
  - `tests/test_report.py`: `build_fixture_root(case: CommandTestCase) -> Path`, which Task 8 uses too.

- [ ] **Step 1: Write the failing tests** in `tests/test_report.py`.
  - Add the helper `build_fixture_root(case: CommandTestCase) -> Path`. It writes a zip from `fixtures/master-fixture.idx`, and patches `index.INDEX_SHA256` and `INDEX_SIZE` to that zip until the test ends (`case.enterContext`). Then it runs `run_index`, `run_sample`, `run_fetch` (`FixtureSession`), `run_envelopes`, `run_facts`, `run_ownership`, a `run_refetch` of the first sampled accession, and `run_compare_refetches`. It returns the zip path.
  - `test_report_times_section`: write `filings` directly with four parsed `ok` filings: `acceptance` with a gap of 12 s, `next_opening` with 186 s, `acceptance` with 1,102,799 s, and one whose `public_at` comes 5 s after its `last_modified_at` (a gap of -5 s). Add a fifth whose `public_at` is 1 s before its `accepted_at`, with a null `last_modified_at`. Assert the exact section lines: a null `last_modified_at` 1; least -5 s, median 12 s, largest 1102799 s (over the four with both times); the 1,102,799 s filing is the only one above 1 hour; the -5 s filing is the only one after; the fifth is the only one before.
  - `test_report_provenance_section` (Review Focus 4): from `build_fixture_root`, every table reads `0 rows ... 0 rows`, and `- index rows with filing times: 6`. After an `ok` filing's `accepted_at` is set to null, the `filings` line reads `1 rows of ok filings`, and a `parties` row with a null `source_url` gives `1 rows with a null source_url`.
  - `test_index_rerun_after_envelopes_shows_in_provenance` (Review Focus 5): after `build_fixture_root`, `run_index` runs again. The `index` line counts all 6 index rows under `rows of ok filings with a null accepted_at or fetched_at`, and `- index rows with filing times: 0`.
  - `test_report_refetches_section`: from `build_fixture_root`, there is one row line and `- Stage 2 requests: 1 of 20`.
- [ ] **Step 2: Run the test command.** Expected: failures in `test_report`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): report the Stage 2 times, sources and refetches`

### Task 8: Rebuild and the Stage 1 column check

**Files:** Create `src/sec_filing_data/rebuild.py`, `tests/test_rebuild.py`. Modify `layout.py`, `cli.py`; `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 4 `run_index`, `run_sample`. Task 3 `build_fetches` (via `ok_responses`). Task 6 `run_compare_refetches`. Task 7 `build_fixture_root`.
- Produces:
  - `Layout(root: Path, tables_dir: Path | None = None)`: `tables` returns `tables_dir` when it is set. `tables_stage1` is `root/"tables-stage1"`.
  - `rebuild.REBUILT_TABLES = ("index", "sample", "fetches", "filings", "parties", "documents", "facts", "facts_status", "ownership", "ownership_status", "refetches")`.
  - `compare_table(expected: pa.Table, actual: pa.Table) -> str` returns `"equal"` when `expected.equals(actual)`. Otherwise it returns the first difference: `schema: <expected> against <actual>`, `rows: <n> against <m>`, or `row <i> column <name>: <expected value> against <actual value>`.
  - `run_rebuild(layout: Layout, zip_path: Path, *, temp_parent: Path | None = None) -> tuple[int, list[str]]`. Its steps:
    1. In `tempfile.TemporaryDirectory(dir=temp_parent)`, with `Layout(layout.root, tables_dir=<temp>)`, run C3's steps in order. For `fetches`, write `build_fetches` of the scratch layout.
    2. Give one line per table of `REBUILT_TABLES`: `<name>: <compare_table(live, rebuilt)>`, or `<name>: no live table`.
    3. Return exit 0 only when every line is `equal`. A step that raises gives the single line `rebuild failed: <ExceptionType>: <message>` and exit 1.
    4. Remove the temporary folder in every case.
  - `check_stage1(layout: Layout) -> tuple[int, list[str]]`: for each table file in `tables_stage1`, sorted by name, the line is `<name>: <compare_table(frozen, live.select(frozen.column_names))>`. A missing `tables-stage1` folder gives `no tables-stage1 folder` and exit 1.
  - CLI: `rebuild --out ROOT --zip PATH` and `check-stage1 --out ROOT` print their lines and return their code. Each one runs inside `record_step`. Neither imports `fetch` or `client`.

- [ ] **Step 1: Write the failing tests** in `tests/test_rebuild.py`. Add `rebuild` to the name set of the import test.
  - `test_equal_tables_give_exit_0`: after `build_fixture_root`, `run_rebuild` gives `(0, [f"{name}: equal" for name in REBUILT_TABLES])`.
  - `test_a_changed_live_table_gives_exit_1_and_names_it`: re-write the live `parties` with one `name` changed. The code is 1, the `parties` line starts `parties: row 0 column name:`, and every other line is `equal`.
  - `test_rebuild_leaves_the_root_unchanged` (Review Focus 1): map each file under `ROOT` to its SHA-256, except `runs.jsonl`, before and after `cli.main(["rebuild", ...])`. The two maps are equal, and so are both ledgers' line counts.
  - `test_missing_live_table_and_failed_step` (Review Focus 2): with the live `refetches.parquet` deleted, the line is `refetches: no live table` and the code is 1. With `index.INDEX_SIZE` patched to a wrong value, the result is `(1, ["rebuild failed: ValueError: ..."])`. In both cases the `temp_parent` folder is empty afterwards.
  - `test_rebuild_never_loads_requests`: in a subprocess, patch the two index constants to the fixture zip and call `cli.main(["rebuild", ...])` on a fixture root. It prints exit 0, and `'requests' in sys.modules` is False.
  - `test_check_stage1_compares_the_frozen_columns`: write `tables-stage1` as each live table restricted to its Stage 1 columns. The result is `(0, ...)` with every line `equal`. After a Stage 1 value in the live `documents` is changed, the code is 1 and the `documents` line names the row.
- [ ] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.rebuild` not found.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the rebuild and the Stage 1 column check`

### Task 9: The live run and the findings

Only the controller runs this task (Global Constraints). It sends Stage 2's only SEC request. Each command runs from the worktree root with these variables, as in plan 10 Task 6:

```bash
ROOT=/Users/lowell/Projects/sec-edgar/filing-data/2026Q3
ZIP=/Users/lowell/Projects/sec-edgar/data/objects/raw/sec/indexes/kind=quarterly/period=2026Q3/sha256=526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150/master.zip
export SEC_USER_AGENT="$(python3 -c 'import json; print(json.load(open("conf/sec-edgar.json"))["sec"]["user_agent"])')"
```

The commands below are short for `uv run --package sec-filing-data sec-filing-data <command> --out "$ROOT"`.

- [ ] **Step 1: Check the preconditions** (spec 6.5 step 1). `pgrep -fl '[s]ec-edgar-ingest|[s]ec-filing-data (fetch|refetch)'` prints nothing. `git -C /Users/lowell/Projects/sec-edgar check-ignore -q filing-data/x` exits 0. The test command gives `OK`. Record `wc -l "$ROOT/fetch-log.jsonl"` (expected 1006), `shasum -a 256 "$ROOT/fetch-log.jsonl"`, and one digest over the Stage 1 bytes: `(cd "$ROOT/bytes" && find . -type f | sort | xargs shasum -a 256 | shasum -a 256)`.
- [ ] **Step 2: Freeze the Stage 1 tables** (step 2). Run `test ! -e "$ROOT/tables-stage1" && cp -Rp "$ROOT/tables" "$ROOT/tables-stage1"`. It refuses when the folder exists. Expected: the 10 Stage 1 Parquet files.
- [ ] **Step 3: Refetch** (step 3): `refetch --accession 9999999995-26-002992`. Expected: exit 0, `stage 2 requests: 1 of 20`, and about 1 KB on the wire (Stage 1 took 881 wire bytes). The Stage 1 ledger still has 1006 lines. Any other result follows spec 6.3, "Known effect": stop and ask the owner before any further request.
- [ ] **Step 4: Re-run the offline steps** (step 4): `index --zip "$ZIP"` (expected `rows: 302499`), `envelopes`, `facts`, `ownership`, `compare-refetches` (expected `refetches: 1`), then `report`. The expected report, from spec 6.1:
  - Times: `acceptance: 477`, `next_opening: 23`, `private_to_public: 0`, `no_acceptance: 0`; a null `last_modified_at` 0; least gap 12 s; largest gap 1102799 s; one filing above 1 hour, `0001836875-26-000073`; `public_at` after `last_modified_at` 0; `public_at` before `accepted_at` 0.
  - Provenance: `0 rows ... 0 rows` for each records table, and `- index rows with filing times: 740`.
  - Refetches: the row of `9999999995-26-002992`, with Stage 1 SHA-256 `740252a6178e54e6121c7701084949adabb113f5d002d00814ca9ec098f431f3` and Stage 1 `Last-Modified` 2026-09-18 10:03:06 UTC; then `Stage 2 requests: 1 of 20`.
  - The `EFFECT` row: `uv run --package sec-filing-data python -c "import pyarrow.parquet as pq; r = next(x for x in pq.read_table('$ROOT/tables/filings.parquet').to_pylist() if x['accession_number'] == '9999999995-26-002992'); print(r['public_rule'], r['public_at'].isoformat(), int((r['last_modified_at'] - r['public_at']).total_seconds()))"`. Expected: `next_opening 2026-09-18T10:00:00+00:00 186`.

  A result that differs is a problem to fix and record (D1 of plan 10, carried by spec section 3). Then re-run the offline steps.
- [ ] **Step 5: Check the Stage 1 columns** (step 5): `check-stage1`. Expected: exit 0 and 10 lines `equal`.
- [ ] **Step 6: Rebuild** (step 6): `rebuild --zip "$ZIP"`. `$ROOT` must be the same absolute path that Stage 1 used, because `fetches.path` holds paths under it. Expected: exit 0 and 11 lines `equal`. Both ledgers' `wc -l` match Steps 1 and 3. The Stage 1 ledger's SHA-256 and the digest over `bytes/` equal their Step 1 values (spec section 2: no Stage 1 byte file or ledger line changed).
- [ ] **Step 7: Write `specs/sec-filing-data-stage-2-findings.md`** (step 7, spec section 8). Its sections:
  - Run record: root and commit.
  - SEC documentation: spec section 4, repeated with its URLs.
  - Times: the rule counts, the gap, and the 10-Q `0001836875-26-000073`. Its copy changed after acceptance, with no sign in its header.
  - Provenance.
  - V6 refetch: both SHA-256 values, both `Last-Modified` times, and spec 6.3's limit in the spec's words or plainer ones.
  - Stage 1 column check.
  - Rebuild.
  - Measured cost: requests and wire bytes against the Stage 2 limits, wall time from `runs.jsonl`, and disk use.
  - Problems found and fixed.
  - Exit check: spec section 8's table, filled, and the anti-goal checks of Steps 4 and 6 (`public_at` before `accepted_at` 0, and the Stage 1 ledger and bytes unchanged).
- [ ] **Step 8: Commit:** `docs(specs): record the Stage 2 run`

The Plan Completion Protocol then ticks the V6 refetch item and the V7 and V8 item in `specs/deferred_items.md`, section `10-sec-filing-data-stage-1 — 2026-11-17`. It also appends the D6 item with spec section 11's wording and `Revisit if`.
