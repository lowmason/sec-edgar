# sec-filing-data Stage 3 findings

This file is the evidence record of Stage 3 of the [sec-filing-data roadmap](completed/sec-filing-data-roadmap.md).
[Plan 13](plans/completed/13-sec-filing-data-stage-3-manifests-and-pinning.md) implemented it, against the
[Stage 3 spec](completed/sec-filing-data-stage-3-manifests-and-pinning.md). Under the lighter process (spec section 3, with
the clean-tree rule of D2), this file is the only evidence record. It records the results of the live run, each
problem found and fixed, and the measured cost.

## Run record

- Output root: `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3`. It is the Stage 1 and Stage 2 root. It sits in
  the main checkout and is git-ignored.
- Code: branch `claude/sec-filing-stage-3-6d8be2`. The run used commit
  `c36aa2cf55711d57d1c040d2192eea6449bc2678`, the final code commit. It holds Tasks 1 to 8 and the fix wave of the
  final whole-branch review. The suite had 413 passing tests at that commit. The baseline was 327.
- Stamp: code version `c36aa2cf5571…` (the run commit), Python 3.14.0 and PyArrow 25.0.1.
- Tree: `git status --porcelain` on the pinned paths printed nothing before the run. No commit landed on the branch
  from the first re-make step to the last check. The branch merges with a merge commit, so the run commit stays
  reachable from `main`.
- Date: the run took place on 2026-11-19, from 18:47 UTC.
- Input: `master.zip` in place at `/Users/lowell/Projects/sec-edgar/filing-data/inputs/2026Q3/master.zip`. It has
  3,505,445 bytes and SHA-256 `526d2dbf…`. `index` checked both values before it parsed.
- SEC access: none. Stage 3 sends no request, so no `SEC_USER_AGENT` was set.
- Before the run (plan Task 9, Step 1):
  - The installed package path was inside this worktree: `packages/sec-filing-data/src/sec_filing_data/`.
  - `filing-data/` was git-ignored in the main checkout. No `sec-filing-data` process ran. `find "$ROOT" -name '.*'`
    printed nothing.
  - The Stage 1 ledger had 1,006 lines (SHA-256 `c348d7d4…`). The Stage 2 ledger had 2 lines (SHA-256
    `551069cb…`).
  - One digest over the files of `bytes/` was `c854e7e5…`. `bytes/` held 500 files. `stage2/refetch/` held 1 file.
  - `tables/` held 11 Parquet files, and `tables-stage1/` held 10. Neither held a stray file.

## Freeze and the frozen-copy check

- Freeze: `cp -Rp tables tables-stage2`, after a test that `tables-stage2/` did not exist. The copy has the 11
  Parquet files. `diff -r` shows it identical to `tables/`. Its per-file SHA-256 values equal the values recorded
  just before the copy.
- Re-make, in order, each at the run commit with a clean tree:

  | Command | Output |
  |---|---|
  | `index --zip` | `rows: 302499` |
  | `sample` | `quota: 160`, `repeated: 5`, `uniform: 335`, then 20 for each of the 8 quota forms |
  | `build-fetches` | `ok: 500` |
  | `envelopes` | `filings: 500`, `parties: 757`, `documents: 5756` |
  | `facts` | `facts: 45358`, and 46 filings with `status ok` |
  | `ownership` | `ownership: 6847`, and 216 filings with a status |
  | `compare-refetches` | `refetches: 1` |

- `check-frozen --folder tables-stage2`: exit 0, and 11 lines `equal`. The tables are `documents`, `facts`,
  `facts_status`, `fetches`, `filings`, `index`, `ownership`, `ownership_status`, `parties`, `refetches` and
  `sample`. The check compares whole tables, schema included. The frozen files have no stamp, and the re-made files
  have one. A stamp is not a value, so it is not a difference.
- `check-stage1`: exit 0, and 10 lines `equal`.
- So the code that changed after the Stage 2 run (commits `d683628` and `7985dff`) and the Task 5 refactor moved
  no value. The re-made tables equal the Stage 2 tables.

## Rebuild

`rebuild --out /Users/lowell/Projects/sec-edgar/filing-data/2026Q3 --zip <master.zip>` re-created every table in a
temporary folder and compared it with the live table. Exit 0. 11 lines, each `equal`: `index`, `sample`, `fetches`,
`filings`, `parties`, `documents`, `facts`, `facts_status`, `ownership`, `ownership_status` and `refetches`. It
sent no request.

## Manifests

Each manifest is in `/Users/lowell/Projects/sec-edgar/filing-data/2026Q3/manifests/`, and its name ends in
`@c36aa2cf5571.json`. `shasum -a 256` of each file gives the printed value.

| Set | File | SHA-256 | Outputs | Inputs |
|---|---|---|---|---|
| `tables` | `tables@c36aa2cf5571.json` | `a9a1e8339ce2608c1e876ed0875026e1956dd2b9ca2563f9b625cfe282a64dc6` | 11 | 504 |
| `tables-stage2` | `tables-stage2@c36aa2cf5571.json` | `ae7b60ec6ed7d4feeafa2f4886f13b1a653d2d2fda836b4ef7dbd98596aa1fde` | 11 | none |
| `tables-stage1` | `tables-stage1@c36aa2cf5571.json` | `571cb031b095a40c9f57ca33219ef28604adcf0969bf86070fcad20ebab4f0bf` | 10 | none |

- The 504 inputs of the `tables` manifest are `master.zip` (kind `index`, 1), the files of `bytes/` (kind
  `submission`, 500), both ledgers (kind `ledger`, 2) and the refetch copy (kind `refetch`, 1).
- Each output of the `tables` manifest has the stamp `c36aa2cf55711d57d1c040d2192eea6449bc2678`, `3.14.0`, `25.0.1`
  and its format number (2 for six tables, 1 for five).
- Every output of the two frozen manifests has `not recorded` for all four stamp values. No record shows which
  code made the frozen tables.
- No manifest holds a time. A search of the three files for a date or a clock time finds none.
- The SHA-256 values above anchor each manifest in git. A later edit to a manifest shows against this file.

## Verify

The seed is `20261119` (the default, `VERIFY_SEED`).

- `verify --manifest tables@c36aa2cf5571.json`: exit 0, with these lines:

  ```
  seed: 20261119
  files: ok
  binding index: ok
  binding filings: ok
  binding parties: ok
  binding documents: ok
  binding facts: ok
  binding ownership: ok
  binding fetches: ok
  binding refetches: ok
  rederive index: ok, 20 rows
  rederive filings: ok, 20 rows
  rederive parties: ok, 20 rows
  rederive documents: ok, 20 rows
  rederive facts: ok, 20 rows
  rederive ownership: ok, 20 rows
  ```

  Binding covers every row. The re-derive covers 120 rows. For `index`, 10 rows come from the 740 rows with
  filing times, and 10 come from the other rows.
- `verify` on each frozen manifest: exit 0. Each gives `seed: 20261119`, `files: ok`,
  `binding: not run, no inputs listed` and `rederive: not run, no inputs listed`.
- Each manifest lists every file in its folder, and `files: ok` shows that no unlisted file sits there. For the
  `tables` manifest, the same holds for `bytes/` and `stage2/refetch/`.

## Versions

The report's Versions section, read on the live root after the run:

```
- index: code c36aa2cf5571, format 2, 302499 rows
- sample: code c36aa2cf5571, format 1, 500 rows
- fetches: code c36aa2cf5571, format 1, 500 rows
- filings: code c36aa2cf5571, format 2, 500 rows
- parties: code c36aa2cf5571, format 2, 757 rows
- documents: code c36aa2cf5571, format 2, 5756 rows
- facts: code c36aa2cf5571, format 2, 45358 rows
- facts_status: code c36aa2cf5571, format 1, 46 rows
- ownership: code c36aa2cf5571, format 2, 6847 rows
- ownership_status: code c36aa2cf5571, format 1, 216 rows
- refetches: code c36aa2cf5571, format 1, 1 rows
- tables made at c36aa2cf5571: 11
```

All 11 tables name one code version, and it is the run commit. The footer of each of the 11 live table files holds
the key `ARROW:schema` and the four `sec_filing_data.*` stamp keys, and nothing else. All 17 Stage 3 lines of `runs.jsonl` have
`code_version` `c36aa2cf5571…` and `tree_clean` true.

## Inputs unchanged

After the run, each value equals its value before the run:

- Stage 1 ledger: 1,006 lines, SHA-256 `c348d7d4…`.
- Stage 2 ledger: 2 lines, SHA-256 `551069cb…`.
- Digest over the files of `bytes/`: `c854e7e5…`. `bytes/` still holds 500 files.
- `stage2/refetch/`: 1 file, `9999999995-26-002992.txt`, SHA-256 `740252a6…`.
- `master.zip`: SHA-256 `526d2dbf…`.
- `tables-stage2/` has the same per-file SHA-256 values as `tables/` had before the re-make. `tables-stage1/` has its
  Stage 1 dates and sizes.

The run wrote only `tables/`, `tables-stage2/` (once), `manifests/` and `runs.jsonl`. The branch diff touches only
`README.md` and `packages/sec-filing-data/`. It changes no pinned path outside the package. Nothing touched `data/`,
`backups/` or tag `ingest-parked-2026-11-16`.

## Measured cost

- SEC requests: 0. Wire bytes: 0.
- Wall time, from the 17 Stage 3 lines of `runs.jsonl`: `index` 0.78 s, `sample` 1.88 s, `build-fetches` 0.02 s,
  `envelopes` 3.06 s, `facts` 1.30 s, `ownership` 0.31 s, `compare-refetches` 0.00 s, `check-frozen` 0.11 s,
  `check-stage1` 0.11 s, `rebuild` 7.98 s, `manifest` 0.55 s (`tables`) and 0.01 s (each frozen set), `verify` 2.65 s
  (`tables`) and 0.05 s (each frozen set), `report` 0.19 s. The sum is 19.05 s. It does not include `uv` start-up.
- Disk (`du -sh`): `tables/` 15 MB, `tables-stage2/` 15 MB, `tables-stage1/` 14 MB, `manifests/` 108 KB. `bytes/`
  stays at 1.1 GB, and Stage 3 added nothing to it.

## Problems found and fixed

The live run found no problem. Every step gave its expected result at the first commit that was run. The reviews
found the items below, and fix rounds closed them before the run:

- Task 1 review: no test reached the real `version.current_checkout`, so a version that read the current folder
  instead of the module path would have passed. No test edited only `pyproject.toml` or `.python-version`, so a typo
  in `PINNED_PATHS` would have passed. Two tests were added.
- Task 6 review: a malformed `inputs` list in a manifest ended in a traceback and hid every `verify` line. It now
  gives one `binding: failed: …` line. No test added an unlisted file in a nested folder, so a scan that skipped
  sub-folders would have passed. Tests were added for both.
- Task 7 review: no test pinned the half-and-half draw of `index` rows, and no test changed an `index` column other
  than the times. A plain draw, or a derived row copied from the table, would have passed. Two tests were added.
- Final review (Opus): `verify` crashed the process (exit 139, a PyArrow 25.0.1 fault) on an empty `index` table,
  because `indices_nonzero` fails on a column with no valid values. The crash skipped every other line and the run
  line. `split_by_times` now joins the chunks first. The live `index` has 302,499 rows and was not affected. The
  review also found that no test showed that part 3 takes its fetch rows from the hashed ledger and not from
  `fetches.parquet`. A test was added, and the empty-table path has a test for each table.

Points that the reviews raised and the plan does not ask for. The run does not change for them. The first, second and fourth are items in `specs/deferred_items.md` (→ item: 13-sec-filing-data-stage-3-manifests-and-pinning — 2026-11-19):

- A corrupt Parquet file, or a `--zip` that names a folder, ends a command in a traceback and not in one error line.
- `verify` needs an absolute `--out` that equals the manifest `root`, because `fetches.path` keeps the root as given
  (plan C10). A relative `--out` fails the path check of part 2.
- A `tables` manifest that someone edits by hand to drop its `inputs` runs as a frozen manifest and shows the two
  `not run` lines. `manifest` always writes `inputs` for `tables`.
- `write_table` called from Python (not from a command) on a changed tree stamps the commit at `HEAD`. Spec 5.1 puts
  the rule on the commands.
- The Codex second opinion of the final review was skipped at the owner's word.

## Exit check

Spec section 7:

| Roadmap Exit part | Evidence | Result |
|---|---|---|
| A check re-derives a sample of parsed values from the retained bytes through their hashes | `verify` exit 0 on the `tables` manifest. Part 2 over every row (8 `binding … ok` lines), part 3 over 120 rows (6 × 20), seed `20261119` | Met |
| Each manifest lists every output file with its SHA-256 | The three manifests of the Manifests section, each with its own SHA-256. Part 1 of `verify` gave `files: ok` on each, so no unlisted file | Met |
| Each output names the code version that made it | The Versions section: one commit for all 11 tables, and it is the run commit `c36aa2cf5571…` | Met |
| The outputs of two code versions are told apart | The `tables` manifest against the two frozen manifests (`not recorded`), and the tests that write one table at two commits (`test_manifest.py`, `test_report.py`) | Met |
| The manifests list the inputs that `rebuild` reads | The 504 `inputs` of the `tables` manifest: `master.zip`, 500 submission files, both ledgers and the refetch copy | Met |

Anti-goal checks (spec section 2):

- Every table names the run commit, and the pinned paths were clean at that commit. Each write command refuses
  first on a changed tree. All 17 Stage 3 run lines have `tree_clean` true.
- `verify` fails on a changed or removed listed file, on an unlisted file (also in a nested folder), on swapped byte
  files, on a source hash with no input, on a changed row and on an edited copy of two equal files (the path check).
  The tests cover each case. On the live root every manifest gave `files: ok`.
- Stage 3 sent no SEC request. `verify`, `manifest` and `build-fetches` load no module that imports `requests`, and
  tests check it.
- No byte file, ledger line, refetch copy, `tables-stage1/` file or input copy changed (the Inputs unchanged
  section).
- The re-made tables equal their `tables-stage2/` copies: `check-frozen` gave 11 lines `equal`.
- No stamp and no manifest holds a clock value. Two writes of the same rows with the same stamp give the same
  bytes, and a test shows it.
