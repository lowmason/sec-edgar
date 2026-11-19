# Stage 3: Manifests, hash-bound evidence and release pinning — Implementation Plan

**Status: COMPLETE (2026-11-19)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 3 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

**Goal:** Stamp every table with the one committed code version that made it, list each output and input set in a manifest with SHA-256 values, check every record's hash against its kept bytes and re-derive a seeded sample of rows from those bytes, then re-make the live tables under one pinned commit.

**Architecture:** The commands stay in place (spec D4). A new `version.py` reads the commit and the clean-tree state with `git`. Each command that writes under the root refuses a dirty tree before `record_step`, and `write_table` stamps each Parquet file. A new `manifest.py` writes one manifest for each table set. A new `verify.py` checks files, binds hashes and re-derives rows through parse functions that take bytes. Task 5 adds those functions with no change in behavior. The live run freezes `tables/` as `tables-stage2/` and then re-makes it.

**Tech Stack:** Python 3.14, uv, `pyarrow` (already locked), and the standard library (`subprocess`, `functools`, `platform`, `hashlib`, `json`, `random`).

**Spec:** `specs/completed/sec-filing-data-stage-3-manifests-and-pinning.md` (approved 2026-11-19). Section 8 holds D1–D4 and the calls that the owner approved with the spec. Background: plan 11 (`specs/plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md`) and its Handoff section.

## Global Constraints

- Stage 1's and Stage 2's constraints carry over (spec section 3): Python 3.14 in the uv workspace. Runtime dependencies are `requests` and `pyarrow` only. Tests read only `tests/fixtures/` and temporary folders, and `tests/__init__.py` blocks sockets. The code runs `git` through `subprocess` from the standard library.
- Only `client.py` and `fetch.py` import `requests`. Each new module (`version`, `manifest`, `verify`) joins the name set of `test_offline_modules_never_import_requests` (`tests/test_commands.py`) in the task that creates it. The offline `fetches` step does not go into `fetch.py`, because that module imports the SEC client.
- **Owner gate:** Stage 3 sends no SEC request (spec section 2, non-goal and anti-goal 3). If a task seems to need one, stop and ask the owner: that would amend the spec. No task sets `SEC_USER_AGENT`.
- Exit codes already in use: 0, 1, 2 (usage errors and a missing User-Agent), 5 and 6. The clean-tree refusal exits `version.REFUSED_EXIT = 3`, and no other outcome uses 3.
- `record_step` writes its `runs.jsonl` line in a `finally` block (`layout.py:74-93`). So the refusal runs first in the CLI handler, before `record_step`, and before the `SEC_USER_AGENT` check of `fetch` and `refetch`. A refused command writes nothing under the root. Commands that write under the root, and so refuse: `index`, `sample`, `fetch`, `refetch`, `envelopes`, `facts`, `ownership`, `compare-refetches`, `build-fetches` and `manifest`. Read-only commands never refuse: `report`, `rebuild`, `check-stage1`, `check-frozen` and `verify`.
- Every caller reads the checkout as `version.current_checkout()`, looked up on the module at call time. Never import the name. The cache sits on the real function, so the refusal, `record_step` and `write_table` share one `git` read in each process.
- Tests give the stamp by a test patch only, never by an environment variable or a command flag (spec 5.1). `tests/__init__.py` sets `version.current_checkout` for the whole suite. A test that starts a subprocess and runs a command that writes under the root sets `version.current_checkout` in the subprocess code first. Only `tests/test_version.py` makes temporary git repositories. Its helper runs `git -c user.name=t -c user.email=t@t -c commit.gpgsign=false -c core.hooksPath=/dev/null`, and depends on no branch name.
- Tests that break by design are updated, never loosened. The exact key set of a run line (`tests/test_index.py:321`) gains `code_version` and `tree_clean`. The tests that call `cli.main` on a writing command pass unchanged under the global patch: `test_index.py:300`, `:347`, `test_sample.py:227`, `:263`, and the helpers at `test_commands.py:1006`, `test_refetch.py:497`, `test_ownership.py:1106` and `test_xbrl.py:739`.
- No stamp, manifest or verify line takes a value from the clock (spec anti-goal 6). Only `record_step` keeps its times.
- Nothing changes a byte file, a ledger line, `stage2/refetch/`, `tables-stage1/` or the input copy under `filing-data/inputs/`. Nothing touches `data/`, `backups/`, tag `ingest-parked-2026-11-16` or the `[build-system]` range of `sec-filing-data` (it was widened on purpose in `a477c54`). No committed line holds the User-Agent or the contact address.
- Only the controller runs Task 9. Implementer subagents and review loops never run a `sec-filing-data` command on the live root. The final whole-branch review and its fixes come before Task 9. No commit lands on the branch from Task 9 Step 3 to Step 9, in any path.
- The implementation PR opens only after Task 9 Step 11, when the findings and every Plan Completion Protocol commit are on the branch. Auto-merge can land the PR as soon as it opens. It merges with a merge commit (spec section 3). Use `ccd_pr` `set_auto_merge` with `merge_method: "merge"`, or, under the PR lifecycle fallback, `gh pr merge <n> --merge --delete-branch`.
- Test command, from the worktree root: `uv run --locked --package sec-filing-data python -m unittest discover -s packages/sec-filing-data/tests -t packages/sec-filing-data`. The baseline is `Ran 327 tests` and `OK`. In each code task, Step 2 sees the new tests fail and Step 4 sees `OK`.

## Review Focus

1. A stray file sits in a set folder, for example `.DS_Store` or a `.part` file left by a crash. `manifest` lists it with null `rows` and null stamp values, and does not crash. A stray file added after the manifest fails part 1 of `verify`. Task 4 `test_manifest_lists_a_file_that_is_not_parquet`.
2. A table is missing when `verify` runs. Each line that needs the table names it, and `verify` exits 1 with no traceback. Task 6 `test_verify_names_a_missing_table`.
3. A manifest does not parse as JSON, or its `manifest_format` is not 1. `verify` prints one `manifest:` line that names it, and exits 1. Task 6 `test_verify_refuses_an_unreadable_manifest`.
4. The owner runs a read-only command while edits are in progress. It runs, and its run line has `tree_clean` false and the commit. Task 1 `test_read_only_commands_run_on_a_dirty_tree`.
5. `--rows` is odd, 1, or larger than a table. The draw takes every row of a small table once. An odd count gives its extra `index` row to the rows without times. Task 7 `test_draw_sizes`.

## Decisions

- **D1** (owner, plan review, 2026-11-19): the plan is approved as written, with the calls C1–C12 and no change asked. Owner's words: "Approve plan". Applied in: Calls made in this plan.

## Calls made in this plan

Spec section 9 leaves these to the builder. The owner may correct any of them at the plan review.

- C1. Modules: `version.py` (code version, clean-tree rule, stamp), `manifest.py` and `verify.py`. None of them imports `requests`. The offline `fetches` step is `ledger.run_fetches`. The frozen-copy check is `rebuild.check_frozen`.
- C2. The refusal exits 3. Each writing handler checks the tree first, before any other check.
- C3. Tests: `tests/__init__.py` sets `version.current_checkout` to return `TEST_CHECKOUT`, a clean checkout at commit `TEST_COMMIT = "5ca1ab1e" * 5`.
- C4. When no commit can be read, `write_table` writes `code_version` as `not recorded`. Outside tests, only `rebuild`'s temporary tables can get there.
- C5. Parse code that takes bytes (Task 5): `index.parse_index`, `ledger.parse_ledger`, `ledger.fetch_rows`, `submissions.filing_records`, `facts.extract_facts` and `fact_rows`, `ownership.extract_ownership` and `ownership_rows`. The step commands call them, so each command and `verify` share one code path.
- C6. Command names: `build-fetches` is the offline `fetches` step, named apart from the live `fetch`, as plan 11 named `compare-refetches`. `check-frozen --folder tables-stage2` compares whole tables, schema included (spec 5.8 step 4: "on every column"). `check-stage1` stays as it is.
- C7. Schema fingerprint: the SHA-256 of the lines `<name>: <type>`, one per field, joined with `\n`. The pairs `(table, format)` and their fingerprints are committed in `tests/test_tables.py`.
- C8. `verify` defaults: `--rows 20` and `--seed 20261119` (`VERIFY_SEED`). Each table draws with its own `random.Random(seed)`. The `index` draw takes `rows // 2` from rows with filing times, and the rest from rows without. Neither half is topped up from the other.
- C9. Manifest JSON: `json.dumps(manifest, sort_keys=True, indent=2) + "\n"`. Stamp values are strings, as stored in the file. `root` is `str(layout.root.absolute())`, and the zip path is `str(zip_path.absolute())`. `manifest` prints the manifest file's SHA-256 for the findings.
- C10. `verify` compares `--out` with the manifest's `root` after `.absolute()` only, not `.resolve()`, because `fetches.path` keeps the root as it was given. A failure in one table does not stop the checks of the others.
- C11. For the filing times on an `index` row, `verify` finds the filing's bytes through the manifest, by the `sha256` of the `fetches` row that it re-derives from the Stage 1 ledger.
- C12. The report's Versions section comes after Refetches.

---

### Task 1: The code version, the clean-tree rule and run lines

**Files:** Create `src/sec_filing_data/version.py`, `tests/test_version.py`. Modify `src/sec_filing_data/layout.py`, `cli.py`; `tests/__init__.py`, `tests/test_index.py`, `tests/test_commands.py` (the name set). Paths are under `packages/sec-filing-data/`.

**Interfaces (produces):**
- `PINNED_PATHS = ("packages/sec-filing-data", "pyproject.toml", "uv.lock", ".python-version")`, `NOT_RECORDED = "not recorded"`, `REFUSED_EXIT = 3`.
- `Checkout(commit: str | None, clean: bool | None, problem: str | None)` (frozen dataclass). A clean checkout has its 40-character commit, `clean` True and no `problem`. A dirty one has its commit, `clean` False and a `problem` that names each changed pinned path. With no readable commit, `commit` and `clean` are None and `problem` says why.
- `inspect_checkout(path: Path) -> Checkout` runs, with `capture_output=True, text=True, check=False`:
  1. `git -C <path> rev-parse --show-toplevel` gives the top folder.
  2. `git -C <top> rev-parse --verify HEAD^{commit}` gives the commit.
  3. `git -C <top> status --porcelain=v1 --untracked-files=all -- <PINNED_PATHS>`: each output line is one change. Ignored files do not show.

  A missing `git` (`FileNotFoundError`) or a non-zero exit at step 1 or 2 gives no commit.
- `current_checkout() -> Checkout`: `functools.cache`, and `inspect_checkout(Path(__file__).resolve().parent)`.
- `Stamp(code_version: str | None, python_version: str, pyarrow_version: str)` (frozen dataclass). `current_stamp() -> Stamp` takes `current_checkout().commit`, `platform.python_version()` and `pyarrow.__version__`.
- `record_step` adds `code_version` (the commit or null) and `tree_clean` (`clean` or null), from `version.current_checkout()`.
- `cli._refuse_unless_clean() -> int | None` prints `error: refused: <problem>` to stderr and gives 3, or gives None. It is the first line of the handlers of `index`, `sample`, `fetch`, `refetch`, `envelopes`, `facts`, `ownership` and `compare-refetches`.
- `tests/__init__.py`: `TEST_COMMIT = "5ca1ab1e" * 5`, `TEST_CHECKOUT = Checkout(TEST_COMMIT, True, None)`, and `version.current_checkout = lambda: TEST_CHECKOUT`.
- `tests/test_version.py`: `make_repo(folder: Path) -> Path` commits `packages/sec-filing-data/src/sec_filing_data/x.py`, `pyproject.toml`, `uv.lock`, `.python-version`, `README.md` and a `.gitignore` with `__pycache__/`. It returns the module folder. `WRITING_ARGV: list[list[str]]` gives one argv for each writing command (`["index", "--zip", "missing.zip"]`, `["refetch", "--accession", "A"]`, and so on). Tasks 3 and 4 extend it.

- [x] **Step 1: Write the failing tests** in `tests/test_version.py`. Add `version` to the name set of the import test.
  - `test_a_clean_tree_gives_the_commit`: the commit equals `git rev-parse HEAD`, `clean` is True and `problem` is None.
  - `test_changes_in_the_pinned_paths_refuse`: in three fresh repos, an unstaged edit to `uv.lock`, a staged edit to `x.py`, and an untracked `packages/sec-filing-data/new.py` each give `clean` False, with the path in `problem`.
  - `test_changes_elsewhere_do_not_refuse`: an edit to `README.md`, an untracked `specs/new.md` and an ignored `__pycache__/x.pyc` under the module folder give `clean` True.
  - `test_no_repository_refuses`: a plain temporary folder, and a repo with `PATH` patched to `""`, each give `commit` None and a `problem`.
  - `test_a_refused_command_writes_nothing`: with `version.current_checkout` patched to `inspect_checkout` of a dirty repo, each argv of `WRITING_ARGV` makes `cli.main` return 3. With `SEC_USER_AGENT` unset, stderr names the changed path, and the root folder stays empty, with no `runs.jsonl`. The same holds with `Checkout(None, None, "no git")`.
  - `test_run_lines_carry_the_code_version`: a `record_step` line has `code_version == TEST_COMMIT` and `tree_clean` True. Under `Checkout(None, None, "no git")`, both are null.
  - `test_read_only_commands_run_on_a_dirty_tree` (Review Focus 4): under `Checkout(TEST_COMMIT, False, "…")`, `report` and `check-stage1` do not return 3. Their run lines have `tree_clean` False and `code_version == TEST_COMMIT`.
  - `tests/test_index.py:321`: the key set becomes `{"step", "started_at", "finished_at", "seconds", "code_version", "tree_clean"}`. Assert the two new values too.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.version` not found.
- [x] **Step 3: Implement** `version.py`, the `record_step` keys, the refusal in the eight handlers, and the patch in `tests/__init__.py`.
  > Deviation: Added tests beyond the plan: two for `current_stamp`, one that runs the real `current_checkout` from a folder that is not a repository (the module path, one cached read), and one for edits to only `pyproject.toml` or only `.python-version` (review fix round, tests only).
- [x] **Step 4: Run the test command.** Expected: `OK`, with the eight existing CLI tests unchanged.
- [x] **Step 5: Commit:** `feat(filing-data): refuse uncommitted changes and record the code version`

### Task 2: The stamp in each table file and the format numbers

**Files:** Modify `src/sec_filing_data/tables.py`; `tests/test_tables.py`.

**Interfaces:**
- Consumes: Task 1 `version.current_stamp`, `NOT_RECORDED`.
- Produces:
  - `TABLE_FORMATS: dict[str, int]`: 2 for `index`, `filings`, `parties`, `documents`, `facts` and `ownership`; 1 for `sample`, `fetches`, `facts_status`, `ownership_status` and `refetches` (spec 5.2).
  - `STAMP_KEYS = ("code_version", "python_version", "pyarrow_version", "table_format")`. Each is stored in the file under the key `sec_filing_data.<key>`.
  - `schema_fingerprint(schema: pa.Schema) -> str` (C7).
  - `write_table` builds its table with `SCHEMAS[name].with_metadata(...)`, which holds the four keys from `version.current_stamp()` and `TABLE_FORMATS[name]`. A null `code_version` is written as `not recorded` (C4).
  - `read_stamp(path: Path) -> dict[str, str]` gives the four values by short key, from `pq.read_metadata(path).metadata`. Each absent key gives `not recorded`.

- [x] **Step 1: Write the failing tests** in `tests/test_tables.py`, with this committed oracle:

  ```python
  SCHEMA_FINGERPRINTS = {
      ("index", 2): "a7857af677b0e856d626122c613dff01ae4d766b2841cb2568dddd2d8bb55e2d",
      ("sample", 1): "9886543d42ba21b786105cc19314423dbe59d9ceb7398e1de601ca730d391a97",
      ("fetches", 1): "1bfc23da407bd93ace0d59aa073a3e99f60018301df3e4be104f48f4a1508050",
      ("filings", 2): "c70f25e610e2b566b692bb7b092599f3e5960e024c14c9c15f5e9656de9d13b5",
      ("parties", 2): "bba2192ed60a8e6b51556c594054a8191ec48f4e3e89f4a68a6850dcfd6e0ffb",
      ("documents", 2): "40f91b91ba0d1819d20c876d6c5e5170ee737d62ed84accf0abcf5f1408f730b",
      ("facts", 2): "4b4a1a91f687ef129c5536ab89cc2ef2291bbeda6b648f006ea0d87591443030",
      ("facts_status", 1): "a0d12f8149eb016d3efc8458caf7d96635f4f61aaca16f6f1f6c9380ef6d6e23",
      ("ownership", 2): "f40995ce69a304dd4ce568a3106376f0cce78488a544cb87ddb04f410b6271a6",
      ("ownership_status", 1): "fd8744133acfd2fb77070ba8247e8b72ddc2fbad948b8c34a84f93cc30027ff8",
      ("refetches", 1): "8f0f9ed4ca108ee081d70f862a8f62cadc3d66e66255c948a1b5710d96c28b19",
  }
  ```

  - `test_each_schema_matches_its_format_number`: `set(TABLE_FORMATS) == set(SCHEMAS)`. For each name, `SCHEMA_FINGERPRINTS[(name, TABLE_FORMATS[name])] == schema_fingerprint(SCHEMAS[name])`.
  - `test_a_changed_schema_with_the_old_number_fails`: these schemas each give a fingerprint other than `SCHEMA_FINGERPRINTS[("sample", 1)]`: `sample` with an added string column, `sample` with two columns swapped, and `sample` with `draw` as `int64`.
  - `test_a_written_table_carries_the_stamp`: after `write_table` of `sample`, `read_stamp` gives `{"code_version": TEST_COMMIT, "python_version": platform.python_version(), "pyarrow_version": pa.__version__, "table_format": "1"}`. The footer keys are `ARROW:schema` and the four stamp keys.
  - `test_no_commit_writes_not_recorded`: under `Checkout(None, None, "no git")`, `code_version` reads `not recorded`.
  - `test_a_file_with_no_stamp_reads_not_recorded`: a file written by `pq.write_table` alone reads `not recorded` for all four keys.
  - `test_same_rows_and_stamp_give_the_same_bytes`: `facts_status` written twice, to two roots, gives equal bytes.
  - `test_compare_ignores_the_stamp`: the same rows, written under `TEST_COMMIT` and under another commit, give `compare_table(...) == "equal"`.
- [x] **Step 2: Run the test command.** Expected: failures and import errors in `test_tables`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): stamp each table with its code version and format number`

### Task 3: The offline `fetches` step and the frozen-copy check

**Files:** Modify `src/sec_filing_data/ledger.py`, `layout.py`, `rebuild.py`, `cli.py`; `tests/test_rebuild.py`, `tests/test_version.py`.

**Interfaces:**
- Consumes: Task 1 `_refuse_unless_clean`, `WRITING_ARGV`.
- Produces:
  - `ledger.run_fetches(layout: Layout) -> list[dict]` writes `fetches` from `build_fetches(layout)` and returns its rows. `rebuild._build_tables` calls it.
  - CLI `build-fetches --out ROOT` refuses first. In `record_step(layout, "build-fetches")` it calls `run_fetches`, then prints `<outcome>: <n>` for each non-zero outcome of `FETCH_OUTCOMES`, as `fetch` does. Exit 0. Add it to `WRITING_ARGV`.
  - `Layout.tables_stage2` is `root/"tables-stage2"`.
  - `rebuild.check_frozen(layout: Layout, frozen_dir: Path) -> tuple[int, list[str]]`: for each `*.parquet` in `frozen_dir`, sorted by name, the line is `<name>: <compare_table(frozen, live)>` over the whole table, or `<name>: no live table`. A missing folder gives `no <folder name> folder`, and an empty one `no tables in <folder name>`. Both exit 1.
  - CLI `check-frozen --out ROOT --folder tables-stage2` (`choices=("tables-stage2",)`) runs inside `record_step(layout, "check-frozen")` and never refuses.

- [x] **Step 1: Write the failing tests** in `tests/test_rebuild.py` (on `FixtureRootTestCase`):
  - `test_build_fetches_writes_the_table_of_build_fetches`: delete `tables/fetches.parquet`. `cli.main(["build-fetches", ...])` returns 0 and prints `ok: <n>`. The table rows equal `build_fetches(layout)`.
  - `test_build_fetches_never_loads_requests`: in a subprocess, first set `version.current_checkout = lambda: version.Checkout("5ca1ab1e" * 5, True, None)`, then run `cli.main(["build-fetches", "--out", root])`. It prints `0` and `False` for `'requests' in sys.modules`.
  - `test_check_frozen_compares_every_column`:
    - After `shutil.copytree(tables, tables-stage2)`, the result is `(0, [f"{name}: equal" for name in sorted names])`.
    - With one live `documents` value changed, the `documents` line starts `documents: row 0 column`, and the code is 1.
    - With the frozen `sample.parquet` re-written by `pq.write_table` with an added column, the `sample` line starts `sample: schema:`.
    - With no folder, the result is `(1, ["no tables-stage2 folder"])`.
- [x] **Step 2: Run the test command.** Expected: failures in `test_rebuild` and `test_version`.
- [x] **Step 3: Implement.**
  > Deviation: The outcome printing of `fetch` moved into `cli._print_fetch_outcomes`, which `build-fetches` shares. `rebuild._compare_whole` is the whole-table compare behind `check_frozen`. `--folder` is required. `check-frozen` joined the dirty-tree read-only test, and one test covers a live column that the frozen copy lacks.
- [x] **Step 4: Run the test command.** Expected: `OK`, with the `check-stage1` and rebuild tests unchanged.
- [x] **Step 5: Commit:** `feat(filing-data): add the offline fetches step and the frozen-copy check`

### Task 4: Manifests

**Files:** Create `src/sec_filing_data/manifest.py`, `tests/test_manifest.py`. Modify `layout.py`, `cli.py`; `tests/test_commands.py` (the name set), `tests/test_version.py`.

**Interfaces:**
- Consumes: Task 1 `Stamp`, `current_stamp`. Task 2 `read_stamp`, `STAMP_KEYS`. Task 3 `Layout.tables_stage2`. Plan 11 `build_fixture_root` (`tests/test_report.py`) and `FixtureRootTestCase` (`tests/test_rebuild.py`).
- Produces:
  - `Layout.manifests` is `root/"manifests"`.
  - `MANIFEST_FORMAT = 1`, `SETS = ("tables", "tables-stage1", "tables-stage2")`.
  - `manifest_path(layout: Layout, set_name: str, commit: str) -> Path` gives `manifests/<set>@<commit[:12]>.json`.
  - `build_manifest(layout: Layout, set_name: str, *, zip_path: Path | None, stamp: Stamp) -> dict`. Hashes use `hashlib.file_digest`. A missing set folder raises `FileNotFoundError` with its path. The keys:
    - `manifest_format`; `set`; `root`; and `written_by` (`code_version`, `python_version`, `pyarrow_version` of `stamp`).
    - `outputs`: one entry for each file under `root/<set>/`, sorted by `path`. Each entry has `path` (relative to the root, POSIX), `bytes`, `sha256`, `rows`, and one key for each of `STAMP_KEYS`. For a `.parquet` file, `rows` comes from `pq.read_metadata` and the stamp values from `read_stamp`. For any other file they are null.
    - `inputs`, only for `tables`, sorted by `path`. Each entry has `path`, `kind`, `bytes` and `sha256`. The inputs, by kind:
      - `index`: the zip, at its absolute path.
      - `submission`: each file under `bytes/`.
      - `ledger`: `fetch-log.jsonl`, and `stage2/fetch-log.jsonl` when it exists.
      - `refetch`: each file under `stage2/refetch/`.

      A `tables` manifest with no `zip_path`, or a frozen set with one, raises `ValueError`.
  - `write_manifest(layout: Layout, set_name: str, *, zip_path: Path | None) -> Path` writes `build_manifest(..., stamp=version.current_stamp())` to `manifest_path(...)`. It opens the file with mode `"x"` and raises `FileExistsError` when the file exists.
  - CLI `manifest --out ROOT --set {tables,tables-stage1,tables-stage2} [--zip PATH]`. Its checks, in order, each before `record_step` and each writing nothing:
    1. The tree refusal gives 3.
    2. A wrong `--zip` use gives `error: …` and exit 2.
    3. An existing manifest gives `error: <path> exists` and exit 1.

    Otherwise, inside `record_step(layout, "manifest")`, it writes the manifest, prints `manifest: <path>` and `sha256: <SHA-256 of the manifest file>`, and exits 0. Add `["manifest", "--set", "tables", "--zip", "missing.zip"]` to `WRITING_ARGV`.

- [x] **Step 1: Write the failing tests** in `tests/test_manifest.py`, on `FixtureRootTestCase`. Add `manifest` to the name set.
  - `test_set_manifest_lists_every_file`: the `tables` manifest's output paths are `tables/<name>.parquet` for the 11 tables, sorted. Each entry's `bytes`, `sha256` and `rows` match the file. Each entry's stamp values are `TEST_COMMIT`, the Python version, the PyArrow version and `str(TABLE_FORMATS[name])`. `manifest_format` is 1, `root` is the absolute root, and `written_by` holds `TEST_COMMIT`. The file text equals `json.dumps(json.loads(text), sort_keys=True, indent=2) + "\n"`.
  - `test_tables_manifest_lists_each_input_kind`: the kinds count as `{"index": 1, "submission": <files in bytes/>, "ledger": 2, "refetch": 1}`. The `index` path is the absolute zip path, and each `sha256` matches its file.
  - `test_frozen_manifest_lists_outputs_only`: `tables-stage1` holds files written by `pq.write_table` alone. Its manifest has no `inputs` key, and each stamp value is `not recorded`.
  - `test_manifest_refuses_to_overwrite`: a second `manifest --set tables` at the same commit exits 1, and stderr names the path. The manifest's bytes and the line count of `runs.jsonl` stay as they were.
  - `test_two_code_versions_give_two_names`: write the `tables` manifest under `TEST_COMMIT`. Then, under commit `"b" * 40`, re-write `sample` and write the manifest again. `manifests/` holds `tables@5ca1ab1e5ca1.json` and `tables@bbbbbbbbbbbb.json`. In the second manifest, `sample` has `code_version` `"b" * 40` and `facts_status` has `TEST_COMMIT`.
  - `test_manifest_lists_a_file_that_is_not_parquet` (Review Focus 1): with `tables/.DS_Store` present, the command exits 0. The entry for that file has its `sha256`, and null `rows` and stamp values.
  - `test_manifest_zip_rules`: `--set tables` without `--zip`, and `--set tables-stage1 --zip <zip>`, each exit 2 and write no `manifests/`.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.manifest` not found.
- [x] **Step 3: Implement.**
  > Deviation: The CLI catches `FileNotFoundError` around `write_manifest`, prints `error: <message>` and exits 1, so a missing set folder, zip or ledger writes no `manifests/` folder. `manifest.zip_problem` serves both the CLI check and `build_manifest`. Three tests were added.
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): add manifests of each table set and its inputs`

### Task 5: Parse code that takes bytes

**Files:** Modify `src/sec_filing_data/tables.py`, `index.py`, `ledger.py`, `submissions.py`, `facts.py`, `ownership.py`; `tests/test_index.py`, `tests/test_commands.py`, `tests/test_rebuild.py`.

No behavior changes. Each step command calls the new functions, so a command and `verify` share one code path (C5).

**Interfaces (produces):**
- `tables.as_table_rows(name: str, rows: list[dict]) -> list[dict]` gives `pa.Table.from_pylist(rows, schema=SCHEMAS[name]).to_pylist()`: rows as they read back from the table.
- `index.parse_index(data: bytes, *, sha256: str, size: int, label: str) -> list[dict]`. Its error messages name `label` where `read_index`'s name the path. `read_index` calls it with `label=str(zip_path)`.
- `ledger.parse_ledger(data: bytes) -> list[dict]`, which `read_ledger` uses. `ledger.last_ok(records: list[dict]) -> dict[str, dict]` (the current `_last_ok`, made public). `ledger.fetch_rows(layout: Layout, sample: list[dict], records: list[dict]) -> list[dict]` is the body of `build_fetches`, with `sample` sorted by `draw` inside. `build_fetches(layout)` passes the `sample` table and `read_ledger(layout.ledger)`.
- `submissions.FilingRecords(NamedTuple)`: `filing: dict`, `parties: list[dict]`, `documents: list[dict]`. `submissions.filing_records(sampled: dict, fetched: dict, raw: bytes | None, ok_record: dict | None) -> FilingRecords` is one pass of the loop in `run_envelopes`. `raw` is None unless the outcome is `ok`. `ok_record` is the accession's last `ok` ledger record, or None.
- `facts.Extraction` (renamed from `_Extraction`). `facts.in_fact_forms(form_type: str) -> bool`, `facts.extract_facts(outcome: str, raw: bytes | None) -> Extraction` and `facts.fact_rows(accession: str, extraction: Extraction, provenance: dict) -> list[dict]`.
- `ownership.Extraction` (renamed from `_Extraction`). `ownership.ownership_form(form_type: str) -> str | None`, `ownership.extract_ownership(form: str, outcome: str, raw: bytes | None) -> Extraction` and `ownership.ownership_rows(accession: str, form_type: str, extraction: Extraction, provenance: dict) -> list[dict]`.

- [x] **Step 1: Write the failing tests.**
  - `test_parse_index_takes_bytes` (`test_index.py`): `parse_index(zip_bytes, sha256=..., size=..., label="L")` equals `read_index(zip_path, ...)`. A wrong size raises `ValueError` whose message holds `L`.
  - `test_parse_ledger_matches_read_ledger` (`test_commands.py`): after a fixture fetch, `parse_ledger(layout.ledger.read_bytes()) == read_ledger(layout.ledger)`.
  - `test_fetch_rows_follow_the_given_sample` (`test_commands.py`): `fetch_rows(layout, list(reversed(sample)), records) == build_fetches(layout)`. With a one-row sample list, the result is one row.
  - `test_per_filing_functions_give_the_table_rows` (`test_rebuild.py`, `FixtureRootTestCase`). For each sampled filing, with `raw` its bytes when `ok`, these equal that accession's table rows, in order:
    - `as_table_rows` of `filing_records(...)`'s `filing`, `parties` and `documents`;
    - `fact_rows(accession, extract_facts(outcome, raw), record_provenance(filing))` for a filing in the fact forms;
    - `ownership_rows(...)` for a filing with an ownership form.
- [x] **Step 2: Run the test command.** Expected: import errors for the new names.
- [x] **Step 3: Implement.** `run_envelopes`, `run_facts`, `run_ownership` and `build_fetches` call the new functions and read each file by path, as today.
  > Deviation: Added `test_as_table_rows_gives_the_rows_as_the_table_reads_them_back` and fixed anchors in the four plan tests, because their equality checks are circular after the refactor.
- [x] **Step 4: Run the test command.** Expected: `OK`. `test_equal_tables_give_exit_0` still gives 11 lines `equal`, so the refactor moved no value.
- [x] **Step 5: Commit:** `refactor(filing-data): let the parse steps take the bytes they read`

### Task 6: `verify`, parts 1 and 2

**Files:** Create `src/sec_filing_data/verify.py`, `tests/test_verify.py`. Modify `cli.py`; `tests/test_commands.py` (the name set).

**Interfaces:**
- Consumes: Task 2 `read_stamp`, `STAMP_KEYS`. Task 4 `write_manifest` and the manifest keys. `FixtureRootTestCase`.
- Produces:
  - `VERIFY_SEED = 20261119`, `DEFAULT_ROWS = 20`, `RECORDS_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership")`.
  - `run_verify(layout: Layout, manifest_path: Path, *, rows: int = DEFAULT_ROWS, seed: int = VERIFY_SEED) -> tuple[int, list[str]]` gives its lines in this order. A manifest with inputs gives:

    ```
    seed: <seed>
    files: ok
    binding <table>: ok          (for each of RECORDS_TABLES, then fetches, then refetches)
    rederive <table>: ok, <n> rows   (for each of RECORDS_TABLES; Task 7)
    ```

    A manifest with no `inputs` gives `seed`, `files`, `binding: not run, no inputs listed` and `rederive: not run, no inputs listed`. The exit is 0 only when every line is `ok` or `not run`.
  - A manifest that does not parse as JSON, or whose `manifest_format` is not 1, gives the single line `manifest: <path>: <reason>` and exit 1 (Review Focus 3).
  - When `str(layout.root.absolute())` differs from the manifest's `root`, the lines are `seed`, then `files: --out <a> differs from the manifest root <b>`. The exit is 1 and nothing else runs (C10).
  - **Part 1 (files)** gives the first failure, naming the path as listed:
    - `<path>: missing`;
    - `<path>: <n> bytes, listed <m>`;
    - `<path>: SHA-256 differs from the listed value`;
    - `<path>: not listed`, for each file in the set folder that is not an output, and, in a `tables` manifest, for each file under `bytes/` and `stage2/refetch/` that is not an input;
    - `<path>: stamp <key> <value> differs from the listed <value>`.
  - **Part 2 (binding)** builds the set of listed input SHA-256 values. Then:
    - A records table fails at its first source hash with no listed input: `binding <table>: <column> <hash> matches no listed input`. The column is `source_sha256`, or `sha256` of the `ok` rows of `filings`.
    - `fetches`: for each `ok` row, `Path(row["path"]).relative_to(<manifest root>)` must be a listed input whose `sha256` equals the row's. A failure names the accession and the path, including a path that is not under the root.
    - `refetches`: for each `ok` row, `stage2/refetch/<accession>.txt` must be listed with `sha256 == refetch_sha256`.

    Each table reads only the columns that it checks.
  - An exception inside one table's check gives `<part> <table>: failed: <ExceptionType>: <message>`, and the other tables still run (Review Focus 2).
  - CLI `verify --out ROOT --manifest PATH [--rows N] [--seed S]` never refuses. It runs inside `record_step(layout, "verify")`, prints its lines and returns its code.

- [x] **Step 1: Write the failing tests** in `tests/test_verify.py`, on `FixtureRootTestCase`. Each test writes the `tables` manifest with the fixture zip unless it says otherwise. Add `verify` to the name set.
  - `test_an_untouched_root_passes`: the code is 0. The lines start `["seed: 20261119", "files: ok", "binding index: ok", ..., "binding refetches: ok"]`.
  - Each case below gives exit 1 and a line that names the file or row:
    - `test_a_changed_byte_fails`: one byte is appended to a file under `bytes/`, and the `files:` line names it.
    - `test_a_removed_file_fails`: `tables/sample.parquet` is deleted, and the `files:` line names it.
    - `test_an_unlisted_file_fails`: separately, `bytes/extra.txt` and `tables/extra.parquet` are added, and the `files:` line names each.
    - `test_swapped_byte_files_fail`: the 13F file (`FETCHED_13F`) and one other file under `bytes/` swap names, and the `files:` line names one of them.
    - `test_a_source_hash_with_no_input_fails`: before the manifest, `facts` is re-written with one `source_sha256` set to `"0" * 64`. The `binding facts:` line holds that hash.
    - `test_the_path_check_catches_one_of_two_equal_files`: before the manifest, a byte is appended to a file under `bytes/` whose bytes another kept file shares. The `binding fetches:` line names that path, and `binding filings: ok` still shows.
  - `test_a_frozen_manifest_runs_part_1_only`: copy `tables/` to `tables-stage2/` and write its manifest. The result is `(0, ["seed: 20261119", "files: ok", "binding: not run, no inputs listed", "rederive: not run, no inputs listed"])`.
  - `test_verify_names_a_missing_table` (Review Focus 2): delete `tables/ownership.parquet` before the manifest. The `binding ownership:` line names `ownership` and the code is 1. No exception escapes.
  - `test_verify_refuses_an_unreadable_manifest` (Review Focus 3): a manifest file holding `{`, and a manifest with `manifest_format` 2, each give one `manifest:` line and exit 1.
  - `test_verify_needs_the_manifest_root`: `--out` another root gives the `files: --out` line, which names both roots, and exit 1.
  - `test_verify_writes_only_its_run_line`: the SHA-256 of each file under the root, except `runs.jsonl`, stays as it was. `runs.jsonl` gains one `verify` line.
  - `test_verify_never_loads_requests`: in a subprocess, `cli.main(["verify", ...])` prints `0` and `False` for `'requests' in sys.modules`.
- [x] **Step 2: Run the test command.** Expected: errors, `sec_filing_data.verify` not found.
- [x] **Step 3: Implement** parts 1 and 2, with a `rederive` stub that Task 7 replaces. Until then, `test_an_untouched_root_passes` asserts only the lines above.
  > Deviation: `manifest._files` became the public `files_under`, shared by `manifest` and `verify`. A malformed `inputs` list gives one `binding: failed: …` line (review fix). `verify` joined the dirty-tree read-only test. Tests were added for nested unlisted files and for malformed manifests.
- [x] **Step 4: Run the test command.** Expected: `OK`.
- [x] **Step 5: Commit:** `feat(filing-data): check listed files and bind record hashes to inputs`

### Task 7: `verify`, part 3

**Files:** Modify `src/sec_filing_data/verify.py`; `tests/test_verify.py`.

**Interfaces:**
- Consumes: Task 5 `parse_index`, `parse_ledger`, `last_ok`, `fetch_rows`, `filing_records`, `in_fact_forms`, `extract_facts`, `fact_rows`, `ownership_form`, `extract_ownership`, `ownership_rows` and `as_table_rows`. Also `sample.draw_sample` (its defaults are the committed sample seed), `provenance.record_provenance`, `provenance.filing_times` and `index.INDEX_SHA256` and `INDEX_SIZE`.
- Produces:
  - `draw_positions(total: int, count: int, rng: random.Random) -> list[int]` gives `sorted(rng.sample(range(total), min(count, total)))`.
  - `draw_index_positions(with_times: list[int], without: list[int], count: int, rng: random.Random) -> list[int]` takes `min(count // 2, len(with_times))` from `with_times`, then `min(count - count // 2, len(without))` from `without`, and gives them sorted (C8). A row has times when its `fetched_at` is not null.
  - Part 3, for a manifest with inputs:
    1. `read_listed(entry) -> bytes` reads a listed file once and hashes those bytes. A hash that differs from the entry fails, naming the path. Bytes are cached by SHA-256.
    2. The sample is `draw_sample` of `parse_index` of the input of kind `index`, read with `read_listed`, with `sha256=index.INDEX_SHA256` and `size=index.INDEX_SIZE`. A drawn `index` row is derived from `parse_index` of the input whose hash equals its `source_sha256`.
    3. The Stage 1 ledger is the input at `fetch-log.jsonl`, read with `read_listed` and parsed with `parse_ledger`. `fetch_rows(layout, sample, records)` gives each accession's fetch row, and `ok_records = last_ok(records)` its last `ok` record.
    4. For each records table, draw positions with a fresh `random.Random(seed)`, and read those rows. For each drawn row:
       - Find a listed input whose SHA-256 equals the row's source hash (`sha256` for `filings`). Read it with `read_listed`. A null hash gives `raw` None.
       - Derive the filing's rows: `filing_records(sampled, fetched, raw, ok_records.get(accession))`. Then `fact_rows` and `ownership_rows` with `record_provenance(filing)`, as the steps do.
       - The drawn row must equal one row of `as_table_rows(table, derived rows of its accession)`.
       - For an `index` row, the derived row is the parsed row with the same `line_number`. When its accession is in the sample, it also takes `filing_times` of that filing. The filing is derived from bytes found by the fetch row's `sha256` (C11), or from `raw` None when the fetch row is not `ok`.
       - A drawn row whose accession is not in the sample fails.
  - A failure line is `rederive <table>: row <position> of <accession>: <reason>`.

- [x] **Step 1: Write the failing tests** in `tests/test_verify.py`.
  - `test_an_untouched_root_passes` gains the six `rederive` lines. For `index`, `<n>` is `min(10, rows with times) + min(10, rows without)`. For each other table, `<n>` is `min(20, the table's rows)`.
  - `test_a_changed_value_fails_the_rederive`: before the manifest, re-write `parties` with row 0's `name` changed. With `rows=1000`, the `rederive parties:` line starts `rederive parties: row 0 of <its accession>:`, the `binding parties: ok` line shows, and the code is 1.
  - `test_a_changed_index_time_fails`: before the manifest, change `public_at` on one `index` row with times. With `rows=1000`, the `rederive index:` line names that row.
  - `test_rederive_ignores_sample_parquet`: before the manifest, re-write `sample` with every `url` changed. The code is 0, because the sample comes from the zip and its seed.
  - `test_rederive_reads_the_bytes_it_hashed`: after the manifest, a byte is appended to the 13F file under `bytes/`. Its hash (`FETCHED_13F`) is the only one of its kind on the fixture root, so `verify` must read that file. With `rows=1000`, the `rederive filings:` line names that path.
  - `test_same_seed_draws_same_rows`: `draw_positions(1000, 20, random.Random(5))` twice gives equal lists. Seed 6 gives a different list.
  - `test_draw_sizes` (Review Focus 5):
    - `draw_index_positions(list(range(740)), list(range(740, 302499)), 20, rng)` has 10 positions below 740 and 10 at 740 or above.
    - With 21, the split is 10 and 11.
    - With 1, it is 0 and 1.
    - `draw_positions(5, 1000, rng) == [0, 1, 2, 3, 4]`.
- [x] **Step 2: Run the test command.** Expected: failures in `test_verify`.
- [x] **Step 3: Implement.**
- [x] **Step 4: Run the test command.** Expected: `OK`.
  > Deviation: Part 3 gives one `rederive: failed: …` line when its preparation fails. An unsampled `index` row is valid with null times. `split_by_times` joins the chunks first, because the final review found a crash on an empty `index` table. Tests were added for the `index` split, every `index` column, empty tables, chunk positions and the ledger source of the fetch rows.
- [x] **Step 5: Commit:** `feat(filing-data): re-derive a seeded sample of rows from the hashed bytes`

### Task 8: The Versions section of the report, and the README

**Files:** Modify `src/sec_filing_data/report.py`, `README.md` (repository root); `tests/test_report.py`.

**Interfaces:**
- Consumes: Task 2 `read_stamp`, `TABLE_FORMATS`. `build_fixture_root`.
- Produces: `report` appends a **Versions** section after Refetches (C12). Its lines:
  - For each table, in `SCHEMAS` order: `- <table>: code <first 12 characters, or not recorded>, format <n, or not recorded>, <rows> rows`. The row count comes from `pq.read_metadata`. A missing table gives `- <table>: no \`<table>\` table yet`.
  - Then `- tables made at <12 characters, or not recorded>: <n>` for each code version, in first-seen order.
  - README, section `sec-filing-data`:
    - the clean-tree rule: the pinned paths, exit 3, and that read-only commands never refuse;
    - the two new keys of each run line;
    - the commands `build-fetches`, `check-frozen`, `manifest` and `verify`, with their flags and exits.

- [x] **Step 1: Write the failing tests** in `tests/test_report.py`.
  - `test_report_versions_section`: from `build_fixture_root`, there are 11 table lines `- <table>: code 5ca1ab1e5ca1, format <TABLE_FORMATS[table]>, <rows> rows`, then `- tables made at 5ca1ab1e5ca1: 11`.
  - `test_versions_tell_two_commits_apart`: re-write `sample` under commit `"b" * 40`, and re-write `refetches` with `pq.write_table` alone. The `sample` line names `bbbbbbbbbbbb`, and the `refetches` line reads `code not recorded, format not recorded`. The count lines are `- tables made at 5ca1ab1e5ca1: 9`, `- tables made at bbbbbbbbbbbb: 1` and `- tables made at not recorded: 1`.
- [x] **Step 2: Run the test command.** Expected: failures in `test_report`.
- [x] **Step 3: Implement** the section, and write the README text (plain technical English).
  > Deviation: Four existing end-of-list order checks moved by one index (`test_report`, `test_commands`, `test_ownership`, `test_xbrl`), because Versions is now the last section. Two tests beyond the plan cover the missing-table line and a root with no tables. The README Output list gained a `manifests/` bullet.
- [x] **Step 4: Run** `sh scripts/check-sec-filing-data.sh`. Expected: `OK` and no whitespace errors.
- [x] **Step 5: Commit:** `feat(filing-data): report the code version of each table`

### Task 9: The live run and the findings

Only the controller runs this task, after the final whole-branch review and its fixes (Global Constraints). It sends no SEC request and needs no `SEC_USER_AGENT`. Run each command from the worktree root, with these variables:

```bash
ROOT=/Users/lowell/Projects/sec-edgar/filing-data/2026Q3
ZIP=/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip
```

In the steps below, a command name is short for `uv run --locked --package sec-filing-data sec-filing-data <command> --out "$ROOT"`. `--locked` keeps `uv` from re-writing `uv.lock`, which is a pinned path.

- [x] **Step 1: Check the preconditions** (spec 5.8 step 1). Each item has its expected result:
  - `git status --porcelain -- packages/sec-filing-data pyproject.toml uv.lock .python-version` prints nothing.
  - Record `git rev-parse HEAD` as the run commit.
  - `uv run --locked --package sec-filing-data python -c "import sec_filing_data; print(sec_filing_data.__file__)"` prints a path in this worktree.
  - `git -C /Users/lowell/Projects/sec-edgar check-ignore -q filing-data/x` exits 0.
  - `pgrep -fl '[s]ec-filing-data'` prints nothing.
  - `find "$ROOT" -name '.*'` prints nothing.
  - `sh scripts/check-sec-filing-data.sh` gives `OK`.
  - Record `wc -l` (1006 and 2 lines) and `shasum -a 256` of both ledgers.
  - Record the digest over the kept bytes: `(cd "$ROOT/bytes" && find . -type f | sort | xargs shasum -a 256 | shasum -a 256)`. The Stage 2 value starts `c854e7e5`.
  - `shasum -a 256 "$ZIP"` starts `526d2dbf2dd2e4c6`.
  > Deviation: Step 1 also counted the files of `bytes/` (500) and `stage2/refetch/` (1), and checked that the printed module path starts with `<worktree>/packages/sec-filing-data/src`.
- [x] **Step 2: Freeze** (step 2). Run `test ! -e "$ROOT/tables-stage2" && cp -Rp "$ROOT/tables" "$ROOT/tables-stage2"`. It refuses when the folder exists. Expected: the 11 Parquet files.
- [x] **Step 3: Re-make** (step 3). Run each command in order, with its expected output:

  | Command | Expected output |
  |---|---|
  | `index --zip "$ZIP"` | `rows: 302499` |
  | `sample` | `quota: 160`, `repeated: 5`, `uniform: 335`, then `20` for each quota form |
  | `build-fetches` | `ok: 500` |
  | `envelopes` | `filings: 500`, `parties: 757`, `documents: 5756` |
  | `facts` | `facts: 45358` |
  | `ownership` | `ownership: 6847` |
  | `compare-refetches` | `refetches: 1` |
- [x] **Step 4: Compare by value** (step 4). `check-frozen --folder tables-stage2` gives exit 0 and 11 lines `equal`. `check-stage1` gives exit 0 and 10 lines `equal`.
- [x] **Step 5: Rebuild** (step 5). `rebuild --zip "$ZIP"` gives exit 0 and 11 lines `equal`.
- [x] **Step 6: Manifests** (step 6). Run `manifest --set tables --zip "$ZIP"`, `manifest --set tables-stage2` and `manifest --set tables-stage1`. Record each printed path and SHA-256. Each name ends `@<run commit, first 12 characters>.json`.
- [x] **Step 7: Verify** (step 7). `verify --manifest <tables manifest>` gives exit 0 and `seed: 20261119`, `files: ok`, 8 `binding … ok` lines, and 6 lines `rederive <table>: ok, 20 rows`. Each frozen manifest gives exit 0, `files: ok` and the two `not run` lines.
- [x] **Step 8: Report** (step 8). In the report's Versions section, every table line names the run commit's 12 characters, and the section ends with `- tables made at <12 characters>: 11`.
- [x] **Step 9: Check that the inputs did not change** (step 9). The ledgers' line counts and SHA-256, the digest over `bytes/`, and the SHA-256 of `$ZIP` equal their Step 1 values.

  A result that differs is a problem to fix and record (spec 5.8). Fix it in a commit, and repeat Steps 1 and 3–9 at the new commit. The freeze stays, and the manifests of the earlier commit stay in `manifests/`.
- [x] **Step 10: Write `specs/sec-filing-data-stage-3-findings.md`** (spec section 7). Its sections:
  - Run record: root, run commit and stamp.
  - Freeze and the frozen-copy check.
  - Rebuild.
  - Manifests: the three paths and their SHA-256 values.
  - Verify: each manifest's lines, and the seed.
  - Versions.
  - Inputs unchanged.
  - Measured cost: wall time from `runs.jsonl`, disk use, and 0 SEC requests.
  - Problems found and fixed.
  - Exit check: spec section 7's table, filled in.

  Commit: `docs(specs): record the Stage 3 run`.
- [x] **Step 11: Run the Plan Completion Protocol, then open the PR.** The protocol's commits touch only `specs/`. All of them land before the PR opens: the gate, the markup, the deferred items, the 3a Handoff section with the roadmap tick and stamp, the backlog report and the retirement. The protocol:
  - ticks the item "Re-hash the kept files in `refetches`" in `specs/deferred_items.md`, section `11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`. It cites `verify` part 1 and part 2's path check (spec 5.5).
  - records in the Handoff section the two roadmap departures of spec section 10: D2's clean-tree rule, which Stage 4 inherits, and the listing of `master.zip` among the inputs.

  Then open the PR (Global Constraints), and run the PR lifecycle rule.

## Handoff to later stages

Roadmap departures (spec section 10). The roadmap's Stage 3 entry was not amended. That is derive-roadmap's job at the resume.

- D2 changes the lighter process under the roadmap's Choices made. From Stage 3 on, a command that writes under the root needs a clean tree at a commit. The pinned paths are `packages/sec-filing-data`, `pyproject.toml`, `uv.lock` and `.python-version`. A refusal exits 3 and writes nothing under the root. A fix still needs no release, only a commit. Stage 4 inherits the rule.
- The Stage 3 Exit lists the inputs that `rebuild` reads as the retained bytes, both ledgers and the refetch copies. `rebuild --zip` also reads `master.zip`, so the `tables` manifest lists it too (kind `index`, at its absolute path).

- **Stage 4 (as-of views).** Consumes, as built:
  - The live tables in `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3/tables/`, re-made at commit `c36aa2cf55711d57d1c040d2192eea6449bc2678` and equal by value to the Stage 2 tables (`check-frozen`, 11 lines `equal`). The frozen copies stay: `tables-stage1/` (10 files) and `tables-stage2/` (11 files, no stamp). The findings of Stage 1 and Stage 2 rest on them.
  - A stamp in each table file: the footer keys `sec_filing_data.code_version`, `sec_filing_data.python_version`, `sec_filing_data.pyarrow_version` and `sec_filing_data.table_format`, all stored as strings. `tables.read_stamp(path)` reads them and gives `not recorded` for an absent key. `tables.TABLE_FORMATS` holds each table's format number, and `SCHEMA_FINGERPRINTS` in `tests/test_tables.py` pins it to the schema. A schema change needs a new number. `runs.jsonl` lines carry `code_version` and `tree_clean` (null when `git` cannot be read).
  - Manifests in `ROOT/manifests/<set>@<commit12>.json`, written by `manifest --out ROOT --set {tables,tables-stage1,tables-stage2} [--zip PATH]` and never overwritten. Keys: `manifest_format` (1), `set`, `root`, `written_by`, `outputs` and, for `tables` only, `inputs` (504 entries: `master.zip`, 500 submission files, both ledgers, the refetch copy). The findings file records the SHA-256 of each manifest (`specs/sec-filing-data-stage-3-findings.md`, Manifests). The frozen sets' manifests list outputs only, and every stamp value in them is `not recorded`.
  - `verify --out ROOT --manifest PATH [--rows N] [--seed S]`. Part 1 checks every listed file and every unlisted file. Part 2 binds every row's source hash to a listed input, and each ledger hash to its own file by path. Part 3 re-derives 20 rows of each records table from the hashed bytes (seed `20261119`). A new view can cite a manifest and a `verify` exit 0 as its trace to the source bytes.
  - Parse functions that take bytes, shared by the step commands and `verify`: `index.parse_index`, `ledger.parse_ledger`, `ledger.last_ok`, `ledger.fetch_rows`, `submissions.filing_records`, `facts.extract_facts` and `fact_rows`, `ownership.extract_ownership` and `ownership_rows`, and `tables.as_table_rows`.
  - Differs from the roadmap's Produces: nothing. Manifests, hash-bound evidence, versioned record formats and a pinned code version all shipped. The format version is one number for each table, not for each record.
  - Traps: find the `index` input of a manifest by `kind`, not by position, because its absolute path sorts first. `verify --out` must repeat the absolute root of the manifest, because `fetches.path` keeps it. A manifest names the commit that wrote it, so a new table set needs its own manifest at its own commit. `write_table` stamps `HEAD` when a Python caller writes a table outside a command, and the clean-tree rule does not guard that path. Each new module joins the name set of `test_offline_modules_never_import_requests`. In PyArrow 25.0.1, `pc.indices_nonzero` on a Parquet column with no valid chunks kills the process (exit 139). Call `combine_chunks()` first (see `verify.split_by_times`).
  - Deferred, in `specs/deferred_items.md`, section `13-sec-filing-data-stage-3-manifests-and-pinning — 2026-11-19`: three small items on bad-input errors, Python-level writes and test gaps → item: 13-sec-filing-data-stage-3-manifests-and-pinning — 2026-11-19. The earlier question of whether an archive copy changes after a correction stays deferred, in section `11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`.
