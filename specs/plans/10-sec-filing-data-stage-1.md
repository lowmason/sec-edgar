# Stage 1: Filing Data Mechanics on the 2026Q3 Sample — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 1 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Deliver the 2026Q3 filing index (O1), the original documents of 500 filings sampled from it (O2), and their as-filed XBRL facts (O3) and ownership records (O4), end to end on real data, from the working tree.

**Architecture:** A new uv workspace member, `packages/sec-filing-data` (import `sec_filing_data`), runs one subcommand per step: `index`, `sample`, `fetch`, `envelopes`, `facts`, `ownership`, `report`. Each step reads earlier steps' Parquet tables under one output root and writes its own. Only `fetch` (and the conditional `fetch-instances`) loads the SEC client, so a parser fix re-runs at no SEC cost.

**Tech Stack:** Python 3.14, uv, `requests` 2.34.2 and `pyarrow` 25.0.1 (both already locked), and the standard library (`zipfile`, `hashlib`, `xml.etree.ElementTree`, `fcntl`, `unittest`).

**Spec:** none. The plan implements Stage 1 of `specs/sec-filing-data-roadmap.md`: its entry, and "Choices made" under Outcomes. Read both. `specs/completed/sec-filing-platform.md` (parked) is background for facts, and its Verification section defines the checks V1–V13 and V15 that D5 names.

## Global Constraints

- Python 3.14 in the existing uv workspace. One new member, `packages/sec-filing-data`; its `[build-system]` block copies `packages/sec-edgar-ingest/pyproject.toml`. Runtime dependencies: `requests` and `pyarrow` only (the root `constraint-dependencies` pin them).
- "No code of the old engine or of the platform branch is an input." Nothing imports `sec_edgar_ingest`, or copies code from it or from branch `platform-stage1`.
- Input: the roadmap's file (3,505,445 bytes, SHA-256 `526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150`), "read in place as a plain file, not through the old store". `index` refuses another size or hash, and writes nothing beside the file.
- SEC budget: "at most 1,500 requests and 5 GB received, at most 3 requests a second, and no other SEC client running." Every HTTP attempt counts, retries included. 5 GB is 5,000,000,000 bytes on the wire, before gzip decoding. The ledger `fetch-log.jsonl` carries the budget across every Stage 1 run.
- Client rules, "a declared User-Agent, at most 3 requests a second, retries, byte guards":
  - User-Agent from `SEC_USER_AGENT`. Live runs take `sec.user_agent` from `conf/sec-edgar.json`, a tracked file that stays as it is. No line that this plan adds holds that value or the contact address in it. Tests use a made-up User-Agent.
  - Request starts at least 0.34 s apart.
  - At most 5 attempts per URL. The delay before attempt k+1 is min(120, 2 × 2^(k−1)) s plus 0–1 s of jitter, or a longer numeric `Retry-After`.
  - Timeouts: 15 s connect, 60 s read.
  - At most 268,435,456 decoded bytes (256 MiB) per response.
- "the original bytes kept with their SHA-256" and "the UTC time of each fetch", in the O2 tables and in the ledger.
- "Plain tables of O1–O4, kept outside `data/`", where removing a worktree cannot delete them. Every command takes a required `--out ROOT`. The live root is `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3` (D3). Values from documents are stored as filed text, with no numeric conversion.
- "fixture and live data kept apart in tests": tests read only `tests/fixtures/` and temporary folders. `tests/__init__.py` makes socket connects and DNS lookups raise.
- Only `client.py` and `fetch.py` import `requests`.
- Lighter process (D1): code runs from the working tree, and a fix needs no release. No per-run deadline, reserve or member-wall tuning. `specs/sec-filing-data-stage-1-findings.md` is the only evidence record. The stage fixes each problem its run finds and records it there. A new stage needs the owner's word.
- Live steps run commands on the live root: Tasks 6 and 7, the `fetch-instances` run in Task 8 Step 0, and the "Run live" steps of Tasks 8–10. Only the controller runs them and checks their output. Implementer subagents and review loops never run them. Only `fetch` and `fetch-instances` send SEC requests and spend the owner's budget. A re-run of `fetch` sends no request for a filing already on disk. The other commands send no request, and the controller re-runs them after each fix (D1).
- Leaves out: what the roadmap's Stage 1 entry lists.
- Test command: `uv run --package sec-filing-data python -m unittest discover -s packages/sec-filing-data/tests -t packages/sec-filing-data`. A pass ends with `OK`. In each code task, Step 2 sees the new tests fail and Step 4 sees `OK`.

## Review Focus

1. A fetch is interrupted. The next run refetches the filing left as `.part`, skips finished ones, and counts the unmatched request at 268,435,456 bytes. Task 5 `test_resume_after_interrupt`.
2. The budget runs out mid-run. Earlier rows stay, later rows read `budget`, and the quota strata came first. Task 5 `test_budget_stop_marks_the_rest`.
3. A filing lacks the expected document: a legacy text `SC 13D/A`, a 10-Q with no instance, a Form 4 with no XML. It gets a status row with a reason, not a crash. Task 8 `test_no_instance_gives_reason`, Task 9 `test_no_ownership_xml_gives_reason`, Task 10 `test_legacy_text_schedule_gives_reason`.
4. XML prefixes differ by filer. Parsers match local names. Task 8 `test_instance_with_default_namespace`, Task 10 `test_13f_prefixed_namespace`.
5. Header bytes are not UTF-8. The parse succeeds with a replacement character. Task 4 `test_non_utf8_header_bytes`.

## Decisions

- **D1** (owner, brief, 2026-11-16): the lighter process, as Global Constraints states it. Applied in: Global Constraints, Tasks 6–10.
- **D2** (owner, plan review, 2026-11-16): O3 reads one XBRL instance per filing: an `EX-101.INS` document, else the SEC-extracted `*_htm.xml`. Never both, and no inline XBRL parser in Stage 1. This departs from R16 of the parked platform spec, which is background only. Owner's words: "XBRL instance (Recommended)". Applied in: Tasks 6, 8.
- **D3** (owner, plan review, 2026-11-16): the live root `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`, in the main checkout and git-ignored. The plan commit adds `filing-data/` to `.gitignore`, and local `main` fast-forwards to it. Owner's words: "Main checkout (Recommended)" and "Fast-forward local main (Recommended)". Applied in: Global Constraints, Task 6.
- **D4** (plan default, stated at the plan review on 2026-11-16, no change asked): "each form type that O3 and O4 name" means the original types `10-K`, `10-Q`, `3`, `4`, `5`, `SCHEDULE 13D`, `SCHEDULE 13G` and `13F-HR`. No `/A` strata. Form 13F is `13F-HR`, not `13F-NT`. The legacy `SC 13D/A` enters only through the 5 repeated-key accessions. Applied in: Task 2.
- **D5** (owner, plan review, 2026-11-17): plan 10 takes in the parts of the parked platform items Stages 2, 3 and 6 (`specs/deferred_items.md`, section `sec-filing-platform-roadmap — 2026-11-16`) that fit Stage 1, D2 and D4, with no extra SEC request. These parts are: the response headers for V3; header checks over all sampled filings for V5, V6, V7, V9 and V10; the V13 cases of an `<XBRL>`-wrapped instance and of an instance counted once; and, in the findings file, a result or an open item for each of V1–V12, and the sampled filings with their SHA-256 as the committed sample manifest. The owner chose the sample manifest over the option "Fits, no filing list", which left manifests to roadmap Stage 3. Platform Stage 6 is planned here. Stages 2 and 3 stay deferred, because their other V13 and V15 cases need an inline XBRL parser (D2) or amendment handling (roadmap Stage 4). This edit is committed, and local `main` fast-forwards to it. Owner's words: "What fits Stage 1 (Recommended)" and "Commit and fast-forward (Recommended)". Applied in: Tasks 3–8 and 10.
- **D6** (owner, plan review, 2026-11-17): wording fixes from the handoff review. The User-Agent and live-steps lines of Global Constraints are corrected. Task 8 Step 0 says that the controller runs `fetch-instances`. Task 1 Step 1 writes the index fixture with `\r\n` line endings. D5 names the option the owner passed over. Owner's words: "Apply and fast-forward (Recommended)". Applied in: Global Constraints, Tasks 1 and 8, D5.

## Root layout and tables

Under `ROOT`: `tables/<name>.parquet`; `bytes/<accession>.txt` (the complete submission file, gzip-decoded); `bytes/<accession>_htm.xml` (only from `fetch-instances`); `fetch-log.jsonl` (the ledger); `runs.jsonl` (step times); `fetch.lock`.

Schemas, all in `tables.py`. Columns are strings unless typed:

| Table | Columns |
|---|---|
| `index` | `line_number` int64 (1-based line in `master.idx`), `cik` int64, `company_name`, `form_type`, `date_filed` date32, `filename`, `accession_number` |
| `sample` | `draw` int32, `stratum` (`quota`, `repeated`, `uniform`), `accession_number`, `form_type`, `cik` int64, `company_name`, `date_filed` date32, `filename`, `url` |
| `fetches` | `accession_number`, `form_type`, `outcome` (`ok`, `not_found`, `too_large`, `forbidden`, `failed`, `budget`, `not_attempted`), `reason`, `status` int32, `attempts` int32, `wire_bytes` int64, `body_bytes` int64, `sha256`, `fetched_at` timestamp[us, UTC], `path` |
| `filings` | `accession_number`, `form_type`, `outcome`, `reason`, `fetched_at` timestamp[us, UTC], `sha256`, `submission_type`, `acceptance_datetime`, `filed_as_of_date`, `date_as_of_change`, `private_to_public` bool, `period_of_report`, `public_document_count`, `document_count` int32, `parse_error` |
| `parties` | `accession_number`, `role`, `name`, `cik` |
| `documents` | `accession_number`, `sequence` int32, `type`, `filename`, `description`, `text_offset` int64, `text_length` int64 |
| `facts` | `accession_number`, `source_document`, `concept`, `value`, `unit`, `period_start`, `period_end`, `period_instant`, `decimals`, `context_id`, `dimensions`, `is_nil` bool |
| `facts_status` | `accession_number`, `form_type`, `source_document`, `fact_count` int32, `reason` |
| `ownership` | `accession_number`, `form_type`, `record_kind`, `issuer_cik`, `issuer_name`, `issuer_cusip`, `owner_cik`, `owner_name`, `owner_count` int32, `security_title`, `shares`, `shares_kind`, `put_call`, `transaction_date`, `transaction_code`, `acquired_disposed`, `price_per_share`, `shares_after`, `direct_indirect`, `percent_of_class`, `value_usd` |
| `ownership_status` | `accession_number`, `form_type`, `record_count` int32, `reason` |

A sampled `form_type` that joins several types with `;` (stratum `repeated`) is in a form set when any of its types is.

---

### Task 1: Package and the O1 index table

**Files:**
- Create: `packages/sec-filing-data/pyproject.toml` (script `sec-filing-data = "sec_filing_data.cli:main"`); `src/sec_filing_data/__init__.py`, `layout.py`, `tables.py`, `index.py`, `cli.py`; `tests/__init__.py`, `tests/test_index.py`, `tests/fixtures/master-fixture.idx`
- Modify: `pyproject.toml` (`[tool.uv.workspace] members`), `uv.lock`

**Interfaces (produces):**
- `layout.py`: `Layout(root: Path)` (frozen dataclass) with `tables`, `bytes_dir`, `ledger`, `lock`, `runs`, `table(name: str)`, `submission(accession: str)` and `instance(accession: str)`, all returning the paths of "Root layout". `record_step(layout: Layout, step: str) -> ContextManager[None]` appends `{"step", "started_at", "finished_at", "seconds"}` to `runs.jsonl`.
- `tables.py`: `SCHEMAS: dict[str, pa.Schema]`; `write_table(layout: Layout, name: str, rows: list[dict]) -> None` (temporary file, then rename); `read_table(layout: Layout, name: str) -> pa.Table`.
- `index.py`: `INDEX_SHA256`, `INDEX_SIZE` (the Global Constraints values); `read_index(zip_path: Path, *, sha256: str, size: int) -> list[dict]`.
- `cli.py`: `main(argv: list[str] | None = None) -> int`. Subcommand `index --zip PATH --out ROOT` writes `index` and prints `rows: <n>`.

- [ ] **Step 1: Write the failing tests** in `tests/test_index.py`, over a `master.zip` built in a temporary folder from `fixtures/master-fixture.idx`. The fixture holds the real file's 11 header lines and 6 data rows. The test writes the zip member with `\r\n` line endings, as the real file has. Two rows share path `edgar/data/1326200/0001104659-26-081696.txt`, under `SC 13D/A` and `SC TO-T/A`.
  - `test_keeps_every_row`: 6 rows; each `line_number` is the row's line in the file; that path gives `accession_number` `0001104659-26-081696`; `date_filed` is a `datetime.date`.
  - `test_refuses_wrong_hash_or_size`: `ValueError` for either.
  - `test_bad_row_names_line`: a 4-field row raises `ValueError` naming its line number.
  - `test_index_command_writes_only_under_out`: with `INDEX_SHA256` and `INDEX_SIZE` patched to the fixture's values, `main(["index", "--zip", z, "--out", root])` writes 6 rows and leaves the zip's folder unchanged.
- [ ] **Step 2: Run the test command.** Expected: failures, `sec_filing_data` not found.
- [ ] **Step 3: Implement.** `read_index` checks size and SHA-256 before it parses. It reads member `master.idx` as strict UTF-8, requires `CIK|Company Name|Form Type|Date Filed|Filename` and then a dashed line, and splits each later non-empty line into exactly 5 fields, with no dedupe. `tests/__init__.py` replaces `socket.socket.connect`, `socket.socket.connect_ex` and `socket.getaddrinfo` with functions that raise `OSError`. Run `uv lock`.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `git add pyproject.toml uv.lock packages/sec-filing-data`, then `feat(filing-data): add the package and the 2026Q3 index table`

### Task 2: The sample

**Files:** Create `src/sec_filing_data/sample.py`, `tests/test_sample.py`. Modify `cli.py`.

**Interfaces (produces):** `QUOTA_FORMS = ("10-K", "10-Q", "3", "4", "5", "SCHEDULE 13D", "SCHEDULE 13G", "13F-HR")`; `draw_sample(index_rows: list[dict], *, size: int = 500, quota: int = 20, seed: int = 20260930) -> list[dict]` (rows of `sample`). Subcommand `sample --out ROOT` prints the count per stratum and per quota form.

Rule. `rng = random.Random(seed)`. Sort candidates by `accession_number` before each draw.
1. Group rows by `accession_number`. The row with the smallest `line_number` gives `cik`, `company_name`, `date_filed` and `filename`.
2. Quota: for each form F of `QUOTA_FORMS`, in order, draw `rng.sample(candidates, min(quota, len(candidates)))` from the undrawn accessions with a row of form F. Stratum `quota`, `form_type` F.
3. Repeated: each undrawn accession whose rows carry more than one form type, in sorted order. `form_type` joins its sorted types with `;`.
4. Uniform: `rng.sample` of the remaining count up to `size`, from the undrawn rest. `form_type` comes from the first row.
5. `draw` is the 1-based position in this order. `url` is `https://www.sec.gov/Archives/` + `filename`.

- [ ] **Step 1: Write the failing tests.**
  - `test_quota_then_repeated_then_uniform`: rows with 3 `10-K` accessions, 1 `5`, 1 accession under `SC 13D/A` and `SC TO-T/A`, and 30 `8-K`. `size=10, quota=2` gives strata `["quota"] * 3 + ["repeated"] + ["uniform"] * 6`, unique accessions, and the `repeated` `form_type` `SC 13D/A;SC TO-T/A`.
  - `test_one_row_per_accession`: an accession under 2 CIKs is drawn once, with the CIK of its first line.
  - `test_seed_is_deterministic`: the same seed gives equal lists; another seed gives a different list.
  - `test_sample_command`: `main(["sample", "--out", root])` over a written `index` writes `sample`.
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the rule.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): draw the 500-filing sample`

### Task 3: The ledger and the SEC client

**Files:** Create `src/sec_filing_data/ledger.py`, `client.py`, `tests/test_client.py`.

**Interfaces (produces):**
- `ledger.py` (no `requests` import): `MAX_REQUESTS = 1_500`, `MAX_WIRE_BYTES = 5_000_000_000`, `MAX_RESPONSE_BYTES = 268_435_456`; `Usage(requests: int, wire_bytes: int)` (frozen dataclass); `append(path: Path, record: dict) -> None` (one JSON line, flushed and fsynced); `read_ledger(path: Path) -> list[dict]`; `ledger_usage(path: Path) -> Usage`.
- `client.py`: `BudgetExhausted(Exception)`; `AccessDenied(Exception)`; `FetchResult` (frozen dataclass: `key`, `url`, `outcome` (`ok`, `not_found`, `too_large`, `failed`), `status: int | None`, `attempts: int`, `wire_bytes: int`, `body_bytes: int`, `sha256: str | None`, `fetched_at: datetime | None`, `reason: str | None`); `exclusive_lock(path: Path) -> ContextManager[None]`; `SecClient(user_agent: str, ledger: Path, *, session=None, monotonic=time.monotonic, sleep=time.sleep, utcnow=<UTC now>, rng: random.Random | None = None)` with `fetch(url: str, dest: Path, *, key: str) -> FetchResult`.

Ledger records:
- Before each attempt: `{"event": "request", "id", "key", "url", "attempt", "at"}`.
- After each attempt, also one that raised: `{"event": "response", "id", "key", "status", "wire_bytes", "body_bytes", "sha256", "outcome", "reason", "content_encoding", "etag", "last_modified", "at"}`. `outcome` is `ok`, `not_found`, `too_large`, `forbidden`, `budget`, `retry` (another attempt follows) or `failed`. `content_encoding`, `etag` and `last_modified` are the response's `Content-Encoding`, `ETag` and `Last-Modified` headers, or null (V3, D5). `at` is UTC ISO 8601 with `Z`.
- `ledger_usage` counts request records and sums response `wire_bytes`. A request with no response counts as `MAX_RESPONSE_BYTES`.

Client rules:
- An empty `user_agent` raises `ValueError`.
- Before each attempt, raise `BudgetExhausted` when usage has reached `MAX_REQUESTS`, or fewer than 1,048,576 wire bytes of budget remain. Nothing is sent. Then wait out the 0.34 s spacing on the monotonic clock.
- `GET` with headers `User-Agent` and `Accept-Encoding: gzip, deflate`, `stream=True`, timeouts `(15, 60)`.
- 200: stream 1 MiB chunks into `<dest>.part` and hash the decoded bytes. Wire bytes come from `response.raw.tell()`. A `Content-Length` above `MAX_RESPONSE_BYTES`, or decoded bytes passing it, gives `too_large`. Before each chunk, when fewer than 1,048,576 wire bytes of budget remain (usage plus this response's wire bytes so far), record `budget` and raise `BudgetExhausted`. On success, write the record, then rename the part file to `dest`. `fetched_at` is the record's time.
- 404 gives `not_found`. 403: record `forbidden`, then raise `AccessDenied`. Statuses 429, 500, 502, 503 and 504, `requests.ConnectionError`, `requests.Timeout` and `requests.exceptions.ChunkedEncodingError` give `retry`, then `failed` after the fifth attempt. Other statuses give `failed`. No outcome leaves a `.part` file.
- `exclusive_lock` takes `fcntl.flock(LOCK_EX | LOCK_NB)`. A held lock raises `RuntimeError("another fetch holds <path>")`.

- [ ] **Step 1: Write the failing tests.** A fake session's `get(url, headers=..., stream=..., timeout=...)` returns scripted fake responses (`status_code`, `headers`, `iter_content`, `raw.tell()`, `close()`). Fake `monotonic`, `sleep` and `utcnow` record calls. Pre-filled ledgers hold matched request and response records.
  - `test_ok_writes_bytes_hash_and_ledger`: the file equals the body; `sha256 == hashlib.sha256(body).hexdigest()`; one request and one response record. With headers `Content-Encoding: gzip` and `ETag: "e1"` and no `Last-Modified`, the response record holds `gzip`, `"e1"` and null.
  - `test_sends_declared_user_agent`
  - `test_spacing_between_requests`: two fetches at fake time 0 give `sleep(0.34)`.
  - `test_retries_then_succeeds`: 503, then 200 gives `attempts == 2` and a sleep of at least 2 s. With `Retry-After: 30`, a sleep of at least 30 s.
  - `test_gives_up_after_five_attempts`: five 503s give `failed` and 5 request records.
  - `test_connection_error_is_recorded_and_retried`: the raised attempt has a response record with outcome `retry`.
  - `test_not_found_is_not_retried`
  - `test_forbidden_halts`: `AccessDenied`, and the ledger holds the `forbidden` record.
  - `test_too_large_by_header_and_by_stream`: both give `too_large`, and neither `dest` nor `.part` exists.
  - `test_budget_refuses_before_sending`: at 1,500 requests, or at 5,000,000,000 wire bytes, `BudgetExhausted` is raised and the session is never called.
  - `test_budget_stops_inside_stream`: the recorded total stays at most `MAX_WIRE_BYTES`.
  - `test_unmatched_request_counts_full_response`: one request record alone gives `Usage(1, 268_435_456)`.
  - `test_second_lock_fails`
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the rules.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the SEC client and its request ledger`

### Task 4: The submission parser

**Files:** Create `src/sec_filing_data/envelope.py`, `tests/test_envelope.py`, `tests/fixtures/submission-13f.txt`.

**Interfaces (produces):** frozen dataclasses `Party(role: str, name: str | None, cik: str | None)`, `Document(sequence: int | None, type: str, filename: str | None, description: str | None, text_offset: int, text_length: int)` and `Submission(fields: tuple[tuple[str, str], ...], acceptance_datetime: str | None, private_to_public: bool, parties: tuple[Party, ...], documents: tuple[Document, ...])`, with `Submission.field(label: str) -> str | None` (first value); `EnvelopeError(ValueError)`; `parse_submission(raw: bytes) -> Submission`; `document_text(raw: bytes, doc: Document) -> bytes`.

Grammar of the complete submission file, parsed as bytes:
- The header is the text between line-initial `<SEC-HEADER>` and `</SEC-HEADER>`, decoded as UTF-8 with `errors="replace"`. The `<SEC-HEADER>` line can carry text after the tag. No header raises `EnvelopeError`.
- Values are stripped. A label followed only by whitespace, such as `REPORTING-OWNER:` and a tab, has no value.
- The `<ACCEPTANCE-DATETIME>` line gives `acceptance_datetime` as filed, such as `20260814160523`.
- `private_to_public` is true when a header line contains `PRIVATE-TO-PUBLIC` (V7, D5).
- A line with no leading whitespace, `LABEL:`, tabs and a value, is a field. With no value, it starts a party with `role = LABEL`, such as `FILER`, `REPORTING-OWNER`, `ISSUER`, `SUBJECT COMPANY` or `FILED BY`. In a party, the first indented `COMPANY CONFORMED NAME:` and `CENTRAL INDEX KEY:` give its name and CIK. Other lines are skipped.
- A document runs from a line-initial `<DOCUMENT>` to the next line-initial `</DOCUMENT>`. Its `<TYPE>`, `<SEQUENCE>`, `<FILENAME>` and `<DESCRIPTION>` lines before `<TEXT>` give its values (the rest of the line, stripped). Its text is the bytes after the `<TEXT>` line, up to the line-initial `</TEXT>`. `text_offset` and `text_length` are byte positions in `raw`. No `</TEXT>` raises `EnvelopeError`.
- `document_text` returns the text without surrounding whitespace and without one outer `<XML>…</XML>` or `<XBRL>…</XBRL>` wrapper.

- [ ] **Step 1: Write the fixture and the failing tests.** The fixture is hand-built in this grammar. It has 6 header fields (`ACCESSION NUMBER: 0001000097-26-000006`, `CONFORMED SUBMISSION TYPE: 13F-HR`, `PUBLIC DOCUMENT COUNT: 2`, `CONFORMED PERIOD OF REPORT: 20260630`, `FILED AS OF DATE: 20260814`, `DATE AS OF CHANGE: 20260814`), `<ACCEPTANCE-DATETIME>20260814160523`, and one `FILER` party (`KINGDON CAPITAL MANAGEMENT, L.L.C.`, `0001000097`). It has 2 `<XML>`-wrapped documents: `13F-HR`, sequence 1, `primary_doc.xml`, and `INFORMATION TABLE`, sequence 2, `infotable.xml`. The second text holds a line `  </TEXT> not at line start`.
  - `test_header_fields_and_acceptance`
  - `test_private_to_public_tag`: the fixture gives `False`; with a `<PRIVATE-TO-PUBLIC>` line added after `<ACCEPTANCE-DATETIME>`, `True`.
  - `test_parties`
  - `test_document_list_and_offsets`: types, sequences and filenames as above; `raw[o:o + n]` equals each text.
  - `test_document_text_strips_xml_wrapper`: the result starts with `b"<?xml"`.
  - `test_closing_tag_must_start_a_line`
  - `test_missing_header_raises`
  - `test_non_utf8_header_bytes`: a company name holding byte `\xe9` parses, and the name contains `"�"`.
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the grammar.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): parse submission headers and document lists`

### Task 5: The fetch, envelopes and report commands

**Files:** Create `src/sec_filing_data/fetch.py`, `submissions.py`, `report.py`, `tests/test_commands.py`. Modify `ledger.py`, `cli.py`.

**Interfaces:**
- Consumes: Tasks 1, 3 and 4.
- Produces:
  - `ledger.build_fetches(layout: Layout) -> list[dict]`: one `fetches` row per sampled filing. It is `ok` when `submission(accession)` exists, with the values of its last `ok` record. Else it takes its last response record's outcome, reading `retry` as `failed`. Else it is `budget` when `ledger_usage` has reached a limit, and `not_attempted` otherwise. `attempts` counts all its request records.
  - `fetch.run_fetch(layout: Layout, *, user_agent: str, per_form: int | None = None, session=None) -> int`. It holds `exclusive_lock(layout.lock)` and walks `sample` in `draw` order, with `key = accession_number`. With `per_form`, it takes only the first `per_form` rows of each quota form. It skips filings on disk and deletes a stale `.part` file. `BudgetExhausted` stops the walk and returns 5, `AccessDenied` returns 6, and a full walk returns 0. Every exit path writes `fetches` from `build_fetches`.
  - `submissions.run_envelopes(layout: Layout) -> int` writes `filings` (one row per sampled filing), `parties` and `documents`. A fetch that is not `ok` sets `reason` to its outcome. An `EnvelopeError` sets `parse_error`.
  - `report.run_report(layout: Layout) -> str` returns Markdown: index rows; the sample per stratum and per quota form; fetch outcomes; requests and wire bytes from `ledger_usage`, and decoded bytes; envelope parse errors; filings with no party, and filings with a null `submission_type`, `acceptance_datetime`, `filed_as_of_date` or `public_document_count`; wall time per step and in total, from `runs.jsonl`; disk use, as the sum of file sizes under the root. It ends with a `Platform checks` section (D5): V3, the `ok` responses per `content_encoding` value, and those with an `etag` or a `last_modified`; V5, each `repeated` filing's `form_type`, `submission_type` and `document_count`; V6, the filings whose `date_as_of_change` is later than `filed_as_of_date`; V7, the filings with `private_to_public`; V9, the filings with a null `acceptance_datetime`; V10, the filings that hold documents described `IDEA: XBRL DOCUMENT`, split by whether `public_document_count` equals `document_count`, equals `document_count` minus that number, or neither.
  - `cli.py`: `fetch --out ROOT [--per-form N]` returns 2 when `SEC_USER_AGENT` is unset, and imports `fetch` inside its handler. Also `envelopes --out ROOT` and `report --out ROOT`. Each command runs inside `record_step`.

- [ ] **Step 1: Write the failing tests,** with a fake session that serves `fixtures/submission-13f.txt` for every URL.
  - `test_fetch_walks_draw_order_and_writes_fetches`
  - `test_per_form_limits_the_pilot`: `per_form=1` fetches one filing per quota form and no `uniform` row.
  - `test_resume_after_interrupt`: given one finished filing, a `.part` file for the next and an unmatched request record, a second run sends no request for the finished filing, refetches the other, and leaves no `.part` file. `ledger_usage(...).wire_bytes` is at least 268,435,456.
  - `test_budget_stop_marks_the_rest`: a ledger of 1,499 matched request and response records gives one fetched filing, the rest `budget`, and exit 5.
  - `test_forbidden_returns_6`
  - `test_envelopes_one_row_per_sampled_filing`: `ok` rows hold parsed fields and the fetch's `fetched_at` and `sha256`, with `date_as_of_change == "20260814"` and `private_to_public` false. A corrupt file gives `parse_error`. A row that is not `ok` gives `reason`.
  - `test_offline_modules_never_import_requests`: a subprocess (`sys.executable`) imports every `sec_filing_data` module except `client` and `fetch` (found with `pkgutil.iter_modules`) and prints `"requests" in sys.modules`. Expected: `False`.
  - `test_report_lists_cost`: lines for requests, wire bytes, wall time, disk use and filings with no party.
  - `test_report_lists_platform_checks`: the `Platform checks` section names V3, V5, V6, V7, V9 and V10. The V6 count is 0, because the fixture's two dates are equal.
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the interfaces.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Commit:** `feat(filing-data): add the fetch, envelopes and report commands`

### Task 6: Live pilot and checkpoint

These are Stage 1's first SEC requests. Each live command runs from the worktree root with these variables:

```bash
ROOT=/Users/lowell/Projects/sec-edgar/filing-data/2026Q3
ZIP=/Users/lowell/Projects/sec-edgar/data/objects/raw/sec/indexes/kind=quarterly/period=2026Q3/sha256=526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150/master.zip
export SEC_USER_AGENT="$(python3 -c 'import json; print(json.load(open("conf/sec-edgar.json"))["sec"]["user_agent"])')"
```

Commands below are short for `uv run --package sec-filing-data sec-filing-data <command> --out "$ROOT"`.

- [ ] **Step 1: Check the preconditions.** `pgrep -fl '[s]ec-edgar-ingest|[s]ec-filing-data fetch'` prints nothing. `git -C /Users/lowell/Projects/sec-edgar check-ignore -q filing-data/x` exits 0. If it does not, the plan commit's `.gitignore` line has not reached `main`: append `/filing-data/` to `/Users/lowell/Projects/sec-edgar/.git/info/exclude` and check again.
- [ ] **Step 2: Build O1 and the sample.** `index --zip "$ZIP"`. Expected: `rows: 302499`. Then `sample`. Expected: 160 `quota` (20 for each of the 8 forms), 5 `repeated`, 335 `uniform`.
- [ ] **Step 3: Run the pilot:** `fetch --per-form 2`, then `envelopes` and `report`. Expected: exit 0, 16 filings `ok`, about 16 requests.
- [ ] **Step 4: Read the checkpoint** from `filings`, `parties` and `documents` for the 16 pilot filings, and record:
  - Header: `submission_type` equals the sample's `form_type`. `acceptance_datetime`, `filed_as_of_date` and `public_document_count` are not null. Each filing has at least one party with a role and a CIK. Forms 3, 4 and 5 have both `REPORTING-OWNER` and `ISSUER`. Record `public_document_count` against `document_count`.
  - For each 10-K and 10-Q: whether a document of type `EX-101.INS` or a filename ending `_htm.xml` is present, and how many documents carry the description `IDEA: XBRL DOCUMENT`.
  - For each Form 3, 4 and 5, `SCHEDULE 13D`, `SCHEDULE 13G` and `13F-HR`: the type, filename and XML root element of the document that holds the records.

  A failed header check is a problem to fix (D1) before Task 7. If every pilot 10-K and 10-Q has an instance inside, Task 8 skips its Step 0. Otherwise Task 8 runs Step 0.
- [ ] **Step 5: Pin the parser to real bytes.** Trim a pilot Form 4 submission (its header and first document) into `tests/fixtures/submission-form4.txt`. Add `test_real_form4_header` to `tests/test_envelope.py`: it asserts the fixture's `CONFORMED SUBMISSION TYPE`, `acceptance_datetime`, and its `REPORTING-OWNER` and `ISSUER` parties with their CIKs. Run the test command. Expected: `OK`, after any fix the test calls for.
- [ ] **Step 6: Start `specs/sec-filing-data-stage-1-findings.md`** with the sections `Run record` (root, commit), `O1`, `Sample`, `Pilot checkpoint`, `O2`, `O3`, `O4`, `Platform checks` (D5), `Problems found and fixed`, `Measured cost`, `Exit check` and `Sample list` (D5). Fill O1, Sample and Pilot checkpoint. Fix each problem the pilot finds in place (D1), record it, and re-run the pilot.
- [ ] **Step 7: Commit:** `test(filing-data): pin the submission parser to a real Form 4` and `docs(specs): record the Stage 1 pilot checkpoint`

### Task 7: Live full fetch (O2)

- [ ] **Step 1: Fetch.** With the Task 6 variables, run `fetch` in the background. Then run `envelopes` and `report`.
- [ ] **Step 2: Check O2.** `filings` has 500 rows. Each row has parsed header fields, or a `reason` or `parse_error`. Each quota form has at least one `ok` filing. Requests are at most 1,500, and wire bytes at most 5,000,000,000.
- [ ] **Step 3: Record** O2 in the findings: outcomes per kind, parse errors, and requests, wire bytes, decoded bytes and wall time so far. Copy the report's V3, V5, V6, V7, V9 and V10 lines under `Platform checks`. Fix and record each problem found (D1).
- [ ] **Step 4: Commit:** `docs(specs): record the Stage 1 fetch`

### Task 8: XBRL facts (O3)

**Files:** Create `src/sec_filing_data/xbrl.py`, `facts.py`, `tests/test_xbrl.py`, `tests/fixtures/instance-10q.xml`. Modify `cli.py`, `report.py`, and for Step 0 only, `fetch.py` and `tests/test_commands.py`.

**Interfaces:**
- Consumes: `parse_submission`, `document_text`, `Document`, `read_table`, `write_table`.
- Produces:
  - `xbrl.py`: `Fact` (frozen dataclass: `concept: str`, `value`, `unit`, `period_start`, `period_end`, `period_instant`, `decimals` (each `str | None`), `context_id: str`, `dimensions: str | None`, `is_nil: bool`); `XbrlError(ValueError)`; `parse_instance(xml: bytes) -> list[Fact]`; `find_instance(documents: Sequence[Document]) -> Document | None`.
  - `facts.py`: `FACT_FORMS = frozenset({"10-K", "10-K/A", "10-Q", "10-Q/A"})`; `run_facts(layout: Layout) -> int` writes `facts`, and `facts_status` with one row per sampled filing in `FACT_FORMS`.
  - Step 0 only: `fetch.run_fetch_instances(layout: Layout, *, user_agent: str, session=None) -> int`, and subcommand `fetch-instances --out ROOT`.

Rules:
- `find_instance`: the first document of type `EX-101.INS`, else the first whose filename ends `_htm.xml`, else `None`.
- `parse_instance` refuses bytes that hold `<!DOCTYPE` (`XbrlError`), and matches XBRL elements by local name.
  - Contexts by `id`. The period is `instant`, or `startDate` and `endDate`, as filed; `forever` leaves all three null. `dimensions` lists each `explicitMember` as `<dimension>=<member>` and each `typedMember` as `<dimension>=<child text>`, sorted and joined with `;`, or null.
  - Units by `id`: the `measure` text; a `divide` as `<numerator>/<denominator>`; several measures joined with `*`.
  - Facts: each direct child of the root with a `contextRef` attribute. `concept` is `prefix:local` with the document's own prefix (from `iterparse` `start-ns` events), else `{namespace}local`. `value` is the text as filed, or null when `xsi:nil="true"`. An element with child elements is skipped.
- `facts_status.source_document` is the instance filename, or `<filename> (fetched separately)`. No instance gives `reason = "no XBRL instance in the submission"`. An `XbrlError` gives `reason = "instance parse error: <message>"`. A fetch that is not `ok` gives its outcome.
- Step 0: for each `ok` filing in `FACT_FORMS` with no instance, the primary document is the first whose type equals the form type and whose filename ends `.htm`. Fetch `https://www.sec.gov/Archives/edgar/data/<cik>/<accession without dashes>/<primary stem>_htm.xml` to `layout.instance(accession)` with `key = <accession>/instance`. A 404 is recorded. `run_facts` then reads that file.

- [ ] **Step 0, only when Task 6 found no instance inside a pilot 10-K or 10-Q:** write `test_fetch_instances_builds_folder_url`, see it fail, implement `run_fetch_instances`, see `OK`, and commit `feat(filing-data): fetch SEC-extracted instances separately`. Then the controller, not the implementer, runs `fetch-instances` live.
- [ ] **Step 1: Write the fixture and the failing tests.** Trim the fixture from a pilot 10-Q instance. Keep the root with its namespace declarations, 2 contexts (an instant, and a duration with one explicit member), 2 units (`usd` and a `divide` unit), and 4 facts: an instant number, a duration number in the dimensional context, a `dei:` text fact and an `xsi:nil` fact. Assert the fixture's values.
  - `test_parses_numeric_text_and_nil_facts`
  - `test_periods_and_dimensions`
  - `test_units_including_divide`
  - `test_instance_with_default_namespace`: the fixture rewritten with the XBRL instance namespace as the default namespace gives the same facts.
  - `test_find_instance_prefers_ex101_ins`
  - `test_doctype_refused`
  - `test_no_instance_gives_reason`: `run_facts` over a 10-Q submission with no instance writes that reason and no facts.
  - `test_xbrl_wrapped_instance` (V13, D5): `run_facts` over a 10-K submission whose `EX-101.INS` text is the fixture wrapped in `<XBRL>` gives the fixture's facts.
  - `test_instance_counted_once` (V13, D5): `run_facts` over a 10-Q submission that holds the fixture both as `EX-101.INS` and as a `*_htm.xml` writes each fact once, and `source_document` is the `EX-101.INS` filename.

  These tests build their submissions in the test, in the Task 4 grammar.
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the rules, the `facts --out ROOT` subcommand, and a facts section in `run_report`: filings, fact rows, source documents, and the filings that gave none, per reason.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Run live:** `facts`, then `report`. Record O3 in the findings. Fix and record each problem found (D1).
- [ ] **Step 6: Commit:** `feat(filing-data): extract as-filed XBRL facts`

### Task 9: Ownership records from Forms 3, 4 and 5

**Files:** Create `src/sec_filing_data/ownership.py`, `forms345.py`, `tests/test_ownership.py`, `tests/fixtures/form4.xml`, `tests/fixtures/form3.xml`. Modify `cli.py`, `report.py`.

**Interfaces:**
- Consumes: `parse_submission`, `document_text`, `Submission`, `read_table`, `write_table`.
- Produces:
  - `ownership.py`: `OwnershipRecord` (frozen dataclass: the `ownership` columns from `record_kind` to `value_usd`, each `str | None`, except `owner_count: int`); `OWNERSHIP_FORMS = frozenset({"3", "3/A", "4", "4/A", "5", "5/A", "SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A", "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "13F-HR", "13F-HR/A"})`; `xml_document(raw: bytes, submission: Submission, root: str) -> bytes | None` (the first document whose text parses as XML with that root local name); `run_ownership(layout: Layout) -> int` writes `ownership`, and `ownership_status` with one row per sampled filing in `OWNERSHIP_FORMS`.
  - `forms345.py`: `parse_form345(xml: bytes) -> list[OwnershipRecord]`.

Mapping, by local name (`a/b` is a child path):
- Issuer: `issuer/issuerCik`, `issuer/issuerName`. Owner: the first `reportingOwner/reportingOwnerId/rptOwnerCik` and `rptOwnerName`. `owner_count` is the number of `reportingOwner` elements.
- One record per `nonDerivativeTransaction`, `nonDerivativeHolding`, `derivativeTransaction` and `derivativeHolding`, with `record_kind` `non_derivative_transaction`, `non_derivative_holding`, `derivative_transaction` or `derivative_holding`.
- `security_title` = `securityTitle/value`; `transaction_date` = `transactionDate/value`; `transaction_code` = `transactionCoding/transactionCode`; `shares` = `transactionAmounts/transactionShares/value`; `price_per_share` = `transactionAmounts/transactionPricePerShare/value`; `acquired_disposed` = `transactionAmounts/transactionAcquiredDisposedCode/value`; `shares_after` = `postTransactionAmounts/sharesOwnedFollowingTransaction/value`; `direct_indirect` = `ownershipNature/directOrIndirectOwnership/value`. A missing element gives null.
- Status: no `ownershipDocument` gives `reason = "no ownership XML document"`. The schedule and 13F forms give `reason = "parser not built"` until Task 10.

- [ ] **Step 1: Write the fixtures and the failing tests.** The fixtures are the `ownershipDocument` of a pilot Form 4 and a pilot Form 3, trimmed to at most 2 rows per table. Assert the fixtures' values.
  - `test_form4_transactions`: one record per row; the first record's fields equal the fixture's values.
  - `test_form3_holdings`
  - `test_two_reporting_owners`: the Form 4 fixture with a second `reportingOwner` gives `owner_count == 2` and keeps the first owner.
  - `test_no_ownership_xml_gives_reason`
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the mapping, the `ownership --out ROOT` subcommand, and an ownership section in `run_report`: records per `record_kind`, and the filings that gave none, per reason.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Run live:** `ownership`. Forms 3, 4 and 5 give records. Fix and record each problem found (D1).
- [ ] **Step 6: Commit:** `feat(filing-data): extract Form 3, 4 and 5 ownership records`

### Task 10: Schedules 13D and 13G, Form 13F, and the findings

**Files:** Create `src/sec_filing_data/schedule13.py`, `form13f.py`, `tests/fixtures/schedule13d.xml`, `tests/fixtures/schedule13g.xml`, `tests/fixtures/infotable.xml`. Modify `ownership.py`, `tests/test_ownership.py`, `specs/sec-filing-data-stage-1-findings.md`.

**Interfaces:**
- Consumes: `OwnershipRecord`, `xml_document`, `Submission.parties`.
- Produces: `parse_schedule13(xml: bytes) -> list[OwnershipRecord]`; `parse_form13f_table(xml: bytes, *, owner_cik: str | None, owner_name: str | None) -> list[OwnershipRecord]`.

Mapping:
- Schedules (root `edgarSubmission`): one record per reporting person, `record_kind = "schedule13_reporting_person"`. The cover page gives `issuer_cik`, `issuer_name`, `issuer_cusip` and `security_title`. Each person gives `owner_name`, `owner_cik` where present, `shares` (the aggregate amount beneficially owned) and `percent_of_class`. The 13D and 13G schemas name these elements differently. Read the names from the pilot's documents, match by local name, and list the names used in the findings.
- Form 13F (root `informationTable`): one record per `infoTable`, `record_kind = "form13f_holding"`. `issuer_name` = `nameOfIssuer`, `issuer_cusip` = `cusip`, `security_title` = `titleOfClass`, `value_usd` = `value`, `shares` = `shrsOrPrnAmt/sshPrnamt`, `shares_kind` = `shrsOrPrnAmt/sshPrnamtType`, `put_call` = `putCall`. The owner is the submission's `FILER` party, with `owner_count` 1.

- [ ] **Step 1: Write the fixtures and the failing tests.** Trim the fixtures from pilot documents: at most 2 reporting persons, at most 3 holdings. Assert the fixtures' values.
  - `test_schedule13d_reporting_persons`
  - `test_schedule13g_reporting_persons`
  - `test_13f_holdings`
  - `test_13f_prefixed_namespace`: the information table rewritten with an `ns1:` prefix gives the same records.
  - `test_legacy_text_schedule_gives_reason`: an `SC 13D/A` submission with only a text document gets `reason = "no ownership XML document"`.
- [ ] **Step 2: Run the test command.** Expected: failures.
- [ ] **Step 3: Implement** the mapping, and remove the `parser not built` reason.
- [ ] **Step 4: Run the test command.** Expected: `OK`.
- [ ] **Step 5: Run live:** `ownership`, then `report`.
- [ ] **Step 6: Complete the findings file:**
  - O1: 302,499 rows. O2: the results.
  - O3 and O4: counts, and the filings that gave none, with their reasons.
  - Problems found and fixed.
  - Measured cost: SEC requests and wire bytes (inside 1,500 and 5,000,000,000), decoded bytes, wall time per step and in total, and disk use of `ROOT`.
  - Exit check: one line per outcome against the roadmap's Stage 1 Exit, each with its evidence.
  - Platform checks (D5): one line for each of V1–V12 of `specs/completed/sec-filing-platform.md`, with its result and evidence, or an open item with a proposed disposition. V3, V9 and V10 have results. V5, V6 and V7 have a 2026Q3 result, and an open item for their part outside the sample: the 2024Q1 pairs, the refetches and the 2026-10-15 submissions. V1, V2, V4, V8, V11 and V12 need Feed archives, `submissions.zip` or SEC documentation, so each is an open item. Then name the V13 and V15 cases that Tasks 8 and 10 test, by test name. Legacy `SC 13G` has no 2026Q3 filing (0 in the index): a named gap.
  - Sample list (D5): one row per sampled filing, with `draw`, `accession_number`, `form_type`, `outcome` and `sha256`.

  Then ask the owner, in one question, for a disposition on each open item, and record the answers.
- [ ] **Step 7: Run the test command** (expected: `OK`), **then commit** `feat(filing-data): extract Schedule 13D/G and Form 13F records` and `docs(specs): record the Stage 1 findings`.

Then run the Plan Completion Protocol of writing-plans, step 3a included: a Handoff section for Stages 2–4, and the roadmap's tick and stamp. Its step 3 ticks the platform Stage 6 item (D5) when each V1–V12 line has a result or an owner disposition and the sample list is committed.
