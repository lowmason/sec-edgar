# Stage 3: Manifests, hash-bound evidence and release pinning — Design Spec

**Status:** Draft, for the owner's review.
**Project:** `/Users/lowell/Projects/sec-edgar`, package `packages/sec-filing-data`.
**Roadmap:** [sec-filing-data roadmap](sec-filing-data-roadmap.md), Stage 3.
**Inputs:** Stage 2 as built: [plan 11](plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md) (its
Handoff section), the [Stage 2 findings](sec-filing-data-stage-2-findings.md), the
[Stage 2 spec](completed/sec-filing-data-stage-2-provenance-and-timing.md), and the live root
`/Users/lowell/Projects/sec-edgar/filing-data/2026Q3` (`tables/`, `tables-stage1/`, `bytes/`, both ledgers,
`stage2/refetch/`). The input copy `/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip`. One
deferred item: "Re-hash the kept files in `refetches`" (`specs/deferred_items.md`, section
`11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`). Background only: the
[Stage 1 findings](sec-filing-data-stage-1-findings.md), which name commits in prose.

## 1. Purpose

Stage 2 gave each record of O1–O4 its source URL, the SHA-256 of its source file and its times. `rebuild` showed
that the code can re-create every table from the kept bytes. But no record says which code made a table, no file
lists the outputs with their hashes, and no check goes from a record's hash back to its bytes.

Stage 3 makes the outputs checkable and reproducible:

- **Pinned:** every table is made by one committed code version, and each table file names that version.
- **Listed:** a manifest lists each output file and each input file with its SHA-256.
- **Bound:** a check finds each record's source file by the record's hash, and re-derives a sample of rows from
  those bytes.

Stage 4 builds as-of views on these tables. Its Exit asks that each answer trace to its manifest and its source
bytes, and Stage 3 gives it both.

Today's tables came from several commits, run from a working tree, and no record maps a table to a commit. A
stamp after the fact could say only "reproduced by" a version, not "made by" it. So Stage 3 re-makes every table
under one pinned version (D1), after it freezes today's tables as evidence for the Stage 2 findings.

## 2. Scope

**Goals**

- G1. Every table in `ROOT/tables/` is made at one commit, from a tree with no uncommitted change in the pinned
  paths (5.1). Each table file names that commit.
- G2. Each table file names its record format number, which changes when the table's columns change (5.2).
- G3. Each `runs.jsonl` line names the commit that ran it (5.3).
- G4. A manifest for each table set lists every output file with its SHA-256. The live set's manifest also lists
  every input that `rebuild` reads, `master.zip` included (5.4).
- G5. A check hashes each listed file again, ties every record's source hash to a listed input, and re-derives a
  seeded sample of rows from the hashed bytes (5.5).
- G6. The re-made tables equal the Stage 2 tables by value. The Stage 2 tables stay, frozen, in
  `ROOT/tables-stage2/` (5.8).

**Non-goals**

- As-of views and amendment handling: Stage 4.
- Any SEC request. Stage 3 fetches nothing, so it needs no SEC budget and no User-Agent.
- A hash for each single document inside a submission file. A record binds to the hash of the whole submission
  file, which is kept whole. The `documents` table gives each document's offset and length inside it (my call,
  section 8).
- Protection against a deliberate attacker who can rewrite the files, the manifest and the git history together.
  A manifest catches accidental change and silent drift. The committed findings record each manifest's SHA-256,
  which anchors the manifest in git.
- A code version for the frozen sets `tables-stage1/` and `tables-stage2/`. No record maps them to a commit, so
  their manifests say "not recorded" and do not guess. The Stage 1 and 2 findings name the commits in prose.
- Locks for the read-only commands, and the other items of `specs/deferred_items.md`, section
  `11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`, except the re-hash item.

**Anti-goals.** Stage 3 fails, even if every check passes, when:

- a table names a code version that did not make it, or a commit that ran with uncommitted changes in the pinned
  paths.
- the check passes although a listed file changed or is missing, or an unlisted file sits in a checked folder.
- it sends an SEC request, or a new command loads the SEC client.
- it changes a byte file, a ledger line, the refetch copy, `tables-stage1/` or the input copy, or touches `data/`,
  `backups/` or tag `ingest-parked-2026-11-16`.
- a re-made table differs from its `tables-stage2/` copy and the findings do not explain the difference.
- a stamp or a manifest takes a value from the clock. A clock value would make two runs of one commit differ.

## 3. Constraints

- Stage 1's and Stage 2's constraints carry over: Python 3.14 in the uv workspace, `requests` and `pyarrow` as the
  only runtime dependencies, fixture and live data kept apart in tests, and socket calls blocked in tests. Only
  `client.py` and `fetch.py` import `requests`. Each new module joins the name set that
  `test_offline_modules_never_import_requests` asserts.
- The code reads the commit with the `git` tool through `subprocess` from the standard library. `git` is a tool on
  the machine, not a package dependency. Tests that need a repository make one in a temporary folder.
- **Process (D2).** The lighter process of Stages 1 and 2 changes in one point. A command that writes under the root
  refuses to run when the pinned paths have an uncommitted change (5.1). A fix still needs no release, only a
  commit. The run still fixes each problem that it finds, and `specs/sec-filing-data-stage-3-findings.md` is the
  only evidence record.
- No SEC budget. Stage 3 runs no `fetch` and no `refetch` (my call, section 8).
- The live run writes only `ROOT/tables/`, `ROOT/tables-stage2/` (once), `ROOT/manifests/` and `runs.jsonl` lines.
  It reads `master.zip` from the input copy, in place. `index` checks its size and SHA-256 against `INDEX_SHA256`.
- `--out` repeats the absolute root that Stage 1 used, because `fetches.path` stores paths under it.
- The plan's pull request merges with a merge commit, not a squash or a rebase. So the commit that the tables name
  stays reachable from `main` after the branch is deleted, and anyone can check it out. The repository already
  merges this way.
- No committed line holds the User-Agent or the contact address.

## 4. Approaches

The owner chose A (D4).

- **A. Extend the commands in place (chosen).** The tables stay in `ROOT/tables/`. `write_table` stamps each file,
  a new `manifest` command writes one manifest for each set, and a new `verify` command does the check. The run
  freezes `tables/` first and then re-makes it. Cost: the re-make overwrites `tables/`, so the freeze must come
  first, and the run checks it. Gain: `Layout`, the folder layout and Stage 4's read path stay as they are.
- **B. One folder for each version.** Each run that writes tables writes to `ROOT/sets/<commit>/tables/`, with its
  manifest beside it. No set is overwritten, so no freeze is needed, and two versions also differ by path. Cost:
  every command takes a set, Stage 4 names the set that it reads, and `tables/` and `tables-stage1/` become old
  folders that do not fit the layout. It fits many runs over time. This roadmap has one quarter, one sample and
  one re-make.
- **C. Manifests that standard tools check.** Each set gets a `SHA256SUMS` file for `shasum -a 256 -c`, and a
  `VERSION` file. Cost: no place for a file's role, its format number or its version, and the value check still
  needs package code to find a file by its hash. A can add a `SHA256SUMS` file later if one is wanted.

The route for today's tables was a separate choice (D1). The other route stamped today's tables after the fact,
with the version that `rebuild` reproduces them with. It could truthfully say only "reproduced by", which does
not meet the Exit's "the code version that made it" without a change to the roadmap.

## 5. Design

### 5.1 The code version and the clean-tree rule

- **The code version** is the full 40-character commit hash of the git checkout that holds the running package
  code. The code finds the checkout from its own module path, not from the current folder. (`uv` installs the
  workspace package in editable mode, so the module path is inside the checkout.)
- **The pinned paths** are `packages/sec-filing-data/`, and `pyproject.toml`, `uv.lock` and `.python-version` at
  the repository root. The locked PyArrow version shapes the bytes of the Parquet files, so the lock is pinned.
  Changes elsewhere, for example in `specs/` or `README.md`, do not block a run.
- **The tree is clean** when git shows no staged, unstaged or untracked change in the pinned paths. Ignored files,
  such as `__pycache__`, do not count.
- **The stamp** of a run is the code version, the Python version (`3.14.0` today) and the PyArrow version
  (`25.0.1` today). It holds no time.
- **Commands that write under the root** refuse to start when the tree is not clean, or when no commit can be read
  (no `git`, or the code is not in a checkout). These commands are `index`, `sample`, `fetch`, `refetch`,
  `envelopes`, `facts`, `ownership`, `compare-refetches`, the offline `fetches` step (5.6) and `manifest`. A
  refusal prints the reason and exits with a code that no other outcome uses. It happens before `record_step`, so
  a refused command writes nothing under the root, not even a `runs.jsonl` line.
- **Read-only commands** (`report`, `rebuild`, `check-stage1`, the frozen-copy check of 5.8 and `verify`) never
  refuse for the tree state. `rebuild` stamps the tables in its temporary folder with what it can read, and
  compares by value.
- Tests give the stamp directly, so the suite runs on a tree with edits in progress. Only the tests of the rule
  itself use a temporary git repository.

### 5.2 The stamp in each table file

- `write_table` writes four keys into the Parquet file's key-value metadata, beside `ARROW:schema`:
  `sec_filing_data.code_version`, `sec_filing_data.python_version`, `sec_filing_data.pyarrow_version` and
  `sec_filing_data.table_format`. So each table step stamps its tables with no code of its own.
- **Record format numbers.** `table_format` is a whole number for each table, committed beside `SCHEMAS`. It goes up
  by 1 when the table's columns, their order or their types change. The first values follow the history:
  - 2 for `index`, `filings`, `parties`, `documents`, `facts` and `ownership`, which Stage 2 changed.
  - 1 for `sample`, `fetches`, `facts_status` and `ownership_status`, which Stage 2 left as they were, and for
    `refetches`, which Stage 2 added.
- A test pins each table's schema to its format number, through a committed fingerprint of the schema. A schema
  change with no new number fails the test.
- A helper reads a file's stamp. A file with no stamp, such as every file of `tables-stage1/` and
  `tables-stage2/`, reads `not recorded` for each key.
- Comparisons ignore the metadata. `compare_table` uses `pa.Table.equals`, which does not check metadata by
  default. So `rebuild`, `check-stage1` and the frozen-copy check compare values, and a stamp is not a difference.
- Two writes of the same rows with the same stamp give the same bytes. PyArrow 25.0.1 writes no time into the file:
  the live files hold only `ARROW:schema` in their metadata. Stage 2 re-wrote `facts_status` and
  `ownership_status` with unchanged values, and they kept their Stage 1 bytes. A test shows it for one table.

### 5.3 Run lines

Each `runs.jsonl` line gains `code_version` and `tree_clean` (true or false). A line of a command that writes under
the root always has `tree_clean` true. When no commit can be read, a read-only command writes null for both. Lines
from before Stage 3 have neither key and stay as they are.

### 5.4 Manifests

A new command, `manifest`, writes the manifest of one table set: `tables`, `tables-stage1` or `tables-stage2`.

- **Place and name.** `ROOT/manifests/<set>@<commit12>.json`, where `<commit12>` is the first 12 characters of the
  code version that writes the manifest. The command refuses when the file exists. So manifests of two code
  versions never share a name, and no manifest is overwritten.
- **Content.** One JSON object, with sorted keys and a newline at the end:
  - `manifest_format`: 1.
  - `set`: the set name. `root`: the absolute root.
  - `written_by`: the stamp of the code that wrote the manifest.
  - `outputs`: one entry for each file in the set folder, sorted by path. Each entry has `path` (relative to the
    root), `bytes`, `sha256`, `rows`, and the four stamp values from the file (`not recorded` when absent).
  - `inputs`, in the manifest of `tables` only: one entry for each input that `rebuild` reads. They are
    `master.zip` (its absolute path as given, because the copy is outside the root), each file under `bytes/`,
    `fetch-log.jsonl`, `stage2/fetch-log.jsonl` and each file under `stage2/refetch/`. Each entry has `path`,
    `kind` (`index`, `submission`, `ledger` or `refetch`), `bytes` and `sha256`.
- **Left out:** `runs.jsonl`, `fetch.lock`, `manifests/` itself, and the other set folders. Every command appends
  to `runs.jsonl`, the check included, so a manifest that listed it would be out of date at once.
- The frozen sets' manifests list outputs only. No record shows which inputs made them.
- The findings record the SHA-256 of each manifest, so a later edit to a manifest on disk shows against git.

### 5.5 The value check

A new command, `verify --out ROOT --manifest PATH [--rows N] [--seed S]`. It sends no request, loads no module that
imports `requests`, and writes nothing except its `runs.jsonl` line. It has three parts:

1. **Files.** Each listed file exists, with its listed size and SHA-256. Each file in the set folder is listed. For
   the `tables` manifest, each file in `bytes/` and in `stage2/refetch/` is listed too. Each output's stamp in the
   file equals its manifest entry. `--out` equals the manifest's `root`.
2. **Binding** (manifests with inputs only). It covers every row, not a sample:
   - Each distinct `source_sha256` of the records tables (`index`, `parties`, `documents`, `facts`, `ownership`)
     and each `sha256` of `filings` is the SHA-256 of a listed input.
   - **By path.** For each `ok` row of `fetches`, the listed input at `fetches.path` has the SHA-256 that the row
     gives, which comes from the Stage 1 ledger. For each `ok` row of `refetches`, the listed input
     `stage2/refetch/<accession>.txt` has the row's `refetch_sha256`, which comes from the Stage 2 ledger. So each
     ledger hash is tied to its own file, not only to some file with the same hash. This matters because
     `9999999995-26-002992` has one SHA-256 in two files, its Stage 1 copy and its refetch copy. Without the path
     check, an edit to one copy before the manifest was written would pass through the other.
3. **Re-derive** (manifests with inputs only). It draws `N` rows (default 20) from each of `index`, `filings`,
   `parties`, `documents`, `facts` and `ownership`, with `random.Random(S)`. For `index`, half of the rows come from
   the rows that carry filing times (740 on the live root) and half from the rest. A plain draw of 20 rows would
   miss all 740 about 95% of the time, and the time path would not run on live data. The default seed is a
   committed constant, and the command prints the seed that it used. For each row:
   - It finds the listed input whose SHA-256 equals the row's source hash, through the manifest, not through the
     accession path. For `index` rows the input is `master.zip`. When two listed inputs share the hash, their
     bytes are equal, and either serves.
   - It reads that file once, hashes the bytes that it read, and confirms the hash.
   - It parses those same bytes with the step's own code, and confirms that the sampled row equals one row of the
     result, in every column. A column whose value comes from a ledger or a committed constant is re-derived from
     that ledger or constant, which part 1 hashed. A column that comes from `sample`, such as the form type or
     the URL, is re-derived from the hashed `master.zip` and the committed sample seed, not read from
     `sample.parquet`. The filing times on a sampled `index` row are re-derived from its filing's bytes and ledger
     lines, as `envelopes` derives them.

It prints one line for each part and each table, `ok` or the first failure. It exits 0 when every part passes, and
1 otherwise.

Part 1 hashes each file under `stage2/refetch/` again, and part 2 ties the Stage 2 ledger's hash to that file by
its path. Together they meet the deferred item "Re-hash the kept files in `refetches`": an edit to a kept file
after its `ok` record shows.

### 5.6 The offline `fetches` step

Only the live `fetch` command writes the `fetches` table today. A new offline command writes it from the ledger and
the bytes on disk, as `rebuild` does with `build_fetches`. It loads no SEC client and needs no User-Agent. The
re-make needs it, because Stage 3 runs no live command.

### 5.7 Report

`report` gains a **Versions** section. For each table it shows the code version (12 characters), the format number
and the number of rows. It also counts the tables for each code version, so a mixed set shows.

### 5.8 The live run

Each command runs from the plan's final code commit, with a clean tree. The plan's final whole-branch review and
its fixes come before the live run, because any later code commit makes steps 3 to 9 run again. No commit lands on
the branch from step 3 to step 9, in any path, because the code version is the commit at HEAD. The findings are
committed after step 9. `$ROOT` is
`/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`. `$ZIP` is
`/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip`.

1. **Preconditions.** The pinned paths are clean at the commit. `filing-data/` is git-ignored in the main checkout.
   No `sec-filing-data` command runs on the root. Record the line count and SHA-256 of both ledgers (1,006 and 2
   lines), one digest over the files of `bytes/` (Stage 2: `c854e7e5…`), and the SHA-256 of `$ZIP`.
2. **Freeze.** `test ! -e "$ROOT/tables-stage2" && cp -Rp "$ROOT/tables" "$ROOT/tables-stage2"`. It refuses when the
   folder exists. Expected: the 11 Parquet files.
3. **Re-make** with the offline steps: `index --zip "$ZIP"`, `sample`, the offline `fetches` step, `envelopes`,
   `facts`, `ownership`, then `compare-refetches`. Expected, as in Stage 2: `rows: 302499`, 500 filings, 45,358
   facts, 6,847 ownership records and `refetches: 1`.
4. **Compare by value.** The frozen-copy check compares each table of `tables-stage2/` with the live table, on every
   column. Expected: 11 lines `equal`. `check-stage1` still gives 10 lines `equal`. The code changed after the
   Stage 2 run (commits `d683628` and `7985dff`), so this step shows whether that change moved any value.
5. **Rebuild.** `rebuild --zip "$ZIP"`. Expected: 11 lines `equal`.
6. **Manifests** for `tables` (with `--zip "$ZIP"`), `tables-stage2` and `tables-stage1`.
7. **Verify** each manifest. The `tables` manifest runs all three parts. The frozen manifests run part 1.
8. **Report.** The Versions section shows one code version for all 11 tables.
9. **Inputs unchanged.** The ledgers and the `bytes/` digest equal their step 1 values.
10. **Findings.** Write `specs/sec-filing-data-stage-3-findings.md` (section 7).

A result that differs is a problem to fix and record, under the lighter process. The fix is a commit, and steps 3
to 9 run again at the new commit. The freeze of step 2 stays. Manifests of the earlier commit stay in
`manifests/`, because none is overwritten, and the findings name the three of the final commit. The run ends with
every table of `tables/` made at one commit.

The frozen-copy check generalizes `check-stage1` to another frozen folder. `check-stage1` keeps working as it is.

## 6. Verification

Offline tests come first and fail before the code exists (red, then green), as in Stages 1 and 2. They read only
fixtures and temporary folders.

- The clean-tree rule, in a temporary git repository: a clean tree gives the commit. A change to a tracked file, a
  staged change and an untracked file in the pinned paths each refuse. A change outside the pinned paths does not
  refuse. No repository refuses. A refused command writes nothing under the root, not even a `runs.jsonl` line.
- Stamps: a written table carries the four keys. A file with no stamp reads `not recorded`. Two writes of the same
  rows with the same stamp give the same bytes. `compare_table` gives `equal` for two tables that differ only in
  their stamps.
- Format numbers: each table's schema fingerprint matches its committed number, and a changed schema with the old
  number fails.
- Run lines carry `code_version` and `tree_clean`.
- Manifests: a set's manifest lists every file of the folder with its size and SHA-256. The `tables` manifest
  lists each input kind. The command refuses to overwrite a manifest. Two code versions give two names. A test
  writes one table at two commits, and the manifest and the report tell them apart.
- `verify`, on a fixture root: exit 0 on an untouched root. Each of these cases gives exit 1 and names the file or
  the row:
  - a byte changed in a listed file
  - a listed file removed
  - an unlisted file added to `bytes/` or to the set folder
  - two byte files with their names swapped
  - a records row whose source hash matches no input
  - a sampled row whose value was changed in the table
  - one of two files that share a ledger hash, edited before the manifest was written (the path check of part 2)

  The same seed draws the same rows. The `index` draw holds rows with filing times and rows without.
  `verify` loads no module that imports `requests`.
- The offline `fetches` step writes the same table as `build_fetches`, and loads no SEC client.
- The existing tests pass, with `write_table` stamping.

## 7. Exit evidence

| Roadmap Exit part | Evidence in `specs/sec-filing-data-stage-3-findings.md` |
|---|---|
| A check re-derives a sample of parsed values from the retained bytes through their hashes | `verify` exit 0 on the `tables` manifest: part 2 over every row, and part 3 over 120 rows, with the seed recorded |
| Each manifest lists every output file with its SHA-256 | The three manifests, each with its own SHA-256, and part 1 of `verify` with no unlisted file |
| Each output names the code version that made it | The Versions section of the report: one commit for all 11 tables, and that commit is the run's commit |
| The outputs of two code versions are told apart | The `tables` manifest against the two frozen manifests (`not recorded`), and the test of section 6 that writes one table at two commits |
| The manifests list the inputs that `rebuild` reads | The `inputs` of the `tables` manifest: `master.zip`, 500 submission files, both ledgers and the refetch copy |

The findings also record the run record (root, commit, stamp), the frozen-copy check and the rebuild, the inputs
unchanged (step 9), the measured cost (wall time from `runs.jsonl`, disk use, and 0 SEC requests), and each problem
found and fixed.

## 8. Decisions and calls

**Owner decisions, 2026-11-18**

- D1. Today's tables are re-made under one pinned version, after `tables/` is frozen as `tables-stage2/`. Owner's
  words: "Re-make, pinned".
- D2. A command that writes under the root refuses uncommitted changes. This changes the roadmap's lighter process
  for Stage 3 (section 10). Owner's words: "Refuse them".
- D3. The stamp, the run lines and the value check as in 5.1, 5.3 and 5.5: the pinned paths, a stamp of commit,
  Python and PyArrow versions, the commit on each run line, read-only commands that never refuse, tests that give
  the stamp, and `verify` with 20 seeded rows per records table found through their hashes. Owner's words: "Looks
  right".
- D4. Approach A. Owner's words: "In place".

**Calls made in this spec** (the owner did not correct them, and may still)

- Stage 3 sends no SEC request, so it has no SEC budget.
- The run and the manifest read `master.zip` from `filing-data/inputs/2026Q3/`, not from the parked store.
- The outputs are the 11 tables of `tables/`. The inputs are `master.zip`, `bytes/`, both ledgers and
  `stage2/refetch/`. `runs.jsonl`, `fetch.lock` and `manifests/` are left out.
- The stamp is stored inside each Parquet file and in the manifest.
- Each table has a record format number, with first values from the history (5.2).
- The frozen sets get manifests of their outputs, with the version `not recorded`.
- The findings record each manifest's SHA-256.
- `.python-version` is a pinned path.
- The code version comes from the checkout that holds the running code.
- The refusal comes before `record_step`.
- An offline `fetches` step (5.6).
- `verify` part 2 binds every row, beside the sampled re-derive.
- `verify` part 2 also ties each ledger hash to its own file by path (`fetches.path`, and
  `stage2/refetch/<accession>.txt`). Part 3 still finds its files by hash, as D3 says.
- Half of the 20 sampled `index` rows come from the rows with filing times. The count per table stays 20, as D3
  says.
- The final review comes before the live run, no commit lands during the run, and the plan's pull request merges
  with a merge commit.
- Manifests are named by set and writer commit, and never overwritten. They hold no clock value.
- Records bind to the hash of the whole submission file. No per-document hash (section 2).
- The report gains a Versions section.

## 9. Left to the builder

- The module layout. For example, `version.py`, `manifest.py` and `verify.py`, none of which imports `requests`.
- The exit code of a refusal, as long as no other outcome uses it.
- How the per-filing parse code takes the bytes that `verify` read and hashed, in place of a second read of the
  path.
- The command names and flags of the offline `fetches` step and the frozen-copy check.
- The form of the schema fingerprint, and the default seed.
- JSON field names, when a name here reads badly. The meanings stay.
- The report's wording, and the README text for the clean-tree rule and the new commands.

## 10. Rollout note

> Roadmap: specs/sec-filing-data-roadmap.md, Stage 3 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

The next step is writing-plans, in a fresh session, against this file. The plan's completion ticks the deferred
item "Re-hash the kept files in `refetches`" in `specs/deferred_items.md`, section
`11-sec-filing-data-stage-2-provenance-and-timing — 2026-11-18`, because `verify` part 1 hashes the files under
`stage2/refetch/` again.

Two departures from the roadmap, for the re-validation at plan completion:

- D2 changes the lighter process under the roadmap's Choices made. From Stage 3 on, a command that writes under the
  root needs a clean tree at a commit. A fix still needs no release. Stage 4 inherits the rule.
- The Stage 3 Exit lists the inputs that `rebuild` reads as the retained bytes, both ledgers and the refetch
  copies. `rebuild --zip` also reads `master.zip`, so the `tables` manifest lists it too.

After the run, the Stage 2 findings' evidence rests on `tables-stage2/`, as the Stage 1 findings rest on
`tables-stage1/`.
