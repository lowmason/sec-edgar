# sec-edgar

This repository is one uv workspace with one Python package, `sec-filing-data`. It makes plain tables from the SEC filings of one quarter, 2026Q3.

The work follows the [roadmap](specs/sec-filing-data-roadmap.md). Stages 1 and 2 are complete. Their results are in the [Stage 1 findings](specs/sec-filing-data-stage-1-findings.md) and the [Stage 2 findings](specs/sec-filing-data-stage-2-findings.md). Stage 2 added the source, the SHA-256 and the filing times to each record. Its [spec](specs/completed/sec-filing-data-stage-2-provenance-and-timing.md) and [plan](specs/plans/completed/11-sec-filing-data-stage-2-provenance-and-timing.md) are retired.

## sec-filing-data

The package makes four outcomes from the 2026Q3 quarterly index:

- O1: the filing index, with one row for each listed filing.
- O2: the original documents of about 500 filings sampled from the index, each split into its header and its document list.
- O3: the as-filed XBRL facts of the sampled 10-K and 10-Q filings.
- O4: the ownership records of the sampled Forms 3, 4 and 5, Schedules 13D and 13G, and Form 13F.

It needs Python 3.14 and [uv](https://docs.astral.sh/uv/). Its only runtime dependencies are PyArrow and Requests.

### Test

Run the check from the repository root:

```bash
sh scripts/check-sec-filing-data.sh
```

The check runs the package's unit tests. The tests open no network connection, because `packages/sec-filing-data/tests/__init__.py` blocks all sockets. GitHub Actions runs the same check on each pull request and on each push to `main`.

### Input

The only input is the 2026Q3 `master.zip` quarterly index, 3,505,445 bytes. The `index` command checks its size and its SHA-256 against `INDEX_SHA256` in `packages/sec-filing-data/src/sec_filing_data/index.py`. It refuses any other file, so a new download from the SEC that differs from this copy fails the check.

The file is not in git. In the main checkout, a copy is at `filing-data/inputs/2026Q3/master.zip`. The `filing-data/` folder is git-ignored.

### Run

Every command takes `--out ROOT`, the output root. Give an absolute path, because the `fetches` table stores the paths of the fetched files under `ROOT`. The live root is `filing-data/2026Q3` in the main checkout, outside every worktree.

Run the steps in this order. Each one is `uv run --package sec-filing-data sec-filing-data <command> --out "$ROOT"`.

1. `index --zip PATH` writes the `index` table from `master.zip`.
2. `sample` draws the sample from the `index` table.
3. `fetch [--per-form N]` fetches the sampled submission files from the SEC. It is the only command that sends SEC requests.
4. `envelopes` writes the `filings`, `parties` and `documents` tables.
5. `facts` writes the `facts` and `facts_status` tables from the XBRL instances.
6. `ownership` writes the `ownership` and `ownership_status` tables.
7. `report` prints a Markdown report of the root.

Stage 2 added four commands:

- `refetch --accession A [--accession A ...]` fetches a sampled submission file a second time, once for each accession. It writes under `ROOT/stage2/` only, and counts in its own ledger, `ROOT/stage2/fetch-log.jsonl`, against 20 requests and 50,000,000 wire bytes. It needs `SEC_USER_AGENT` like `fetch`. It never retries, and a refetch that was interrupted makes the next one exit with code 5.
- `compare-refetches` writes the `refetches` table from the Stage 2 ledger and the refetched files. It sends no request.
- `check-stage1` compares the Stage 1 columns of each table with the frozen copy in `ROOT/tables-stage1/`. It sends no request.
- `rebuild --zip PATH` re-creates every table in a temporary folder from `master.zip`, the kept bytes and both ledgers, and compares each one with the live table. It exits 0 only when every table is equal. It sends no request and leaves the root unchanged, except for one `runs.jsonl` line.

Stage 3 added four commands. None of them sends a request.

- `build-fetches` writes the `fetches` table from the `sample` table, `ROOT/fetch-log.jsonl` and the files in `ROOT/bytes/`. It needs no `SEC_USER_AGENT`. It exits 0, or 3 when it refuses (see Code version).
- `check-frozen --folder tables-stage2` compares each table in `ROOT/tables-stage2/` with the live table. That folder is the copy of the tables that the Stage 2 findings rest on, and it is the only value that `--folder` accepts. The command compares every column, where `check-stage1` compares the Stage 1 columns only. It prints one line for each table. It exits 0 only when every table is equal. It exits 1 for a difference, and when the folder is missing or holds no table.
- `manifest --set SET [--zip PATH]` writes the manifest of one table set. `SET` is `tables`, `tables-stage1` or `tables-stage2`. The manifest is the file `ROOT/manifests/SET@COMMIT.json`, where `COMMIT` is the first 12 characters of the code version. It lists each file in `ROOT/SET/` with its size and SHA-256. For each Parquet file, it also lists the row count and the stamp (see Code version). The manifest of `tables` also lists the inputs that `rebuild` reads. So `--set tables` needs `--zip PATH`, the path of `master.zip`, and no other set takes `--zip`. The command prints `manifest: PATH` and `sha256: HASH`. It never overwrites a manifest. It exits 0 when it writes the manifest. It exits 1 when the manifest exists, or when the set folder is missing. For `tables`, it also exits 1 when the zip or `ROOT/fetch-log.jsonl` is missing. It exits 2 when `--zip` is missing for `tables` or given for another set. It exits 3 when it refuses.
- `verify --manifest PATH [--rows N] [--seed S]` checks the root against a manifest. `--out` must be the `root` that the manifest names. The command prints `seed: S`, then one line for each check. It exits 0 when every line is `ok` or `not run`, and 1 otherwise. A manifest that it cannot read gives one line and exit 1. It writes nothing except its `runs.jsonl` line. It has three parts. Parts 2 and 3 run for the manifest of `tables` only, and their lines read `not run, no inputs listed` for the other manifests.
  1. Files: each listed file is there with its listed size, SHA-256 and stamp, and no unlisted file is in the set folder. For the manifest of `tables`, this covers `bytes/` and `stage2/refetch/` too.
  2. Binding: each record hash and each ledger hash ties to a listed input. It covers every row.
  3. Re-derivation: `N` rows of each of the `index`, `filings`, `parties`, `documents`, `facts` and `ownership` tables are derived again from the listed input bytes. Each derived row must equal its table row. `--rows` is `N` and defaults to 20. An `N` below 1 is a usage error (exit 2). `--seed` seeds the choice of rows and defaults to 20261119.

`facts` and `ownership` read the `filings` table, so run them after `envelopes`. `envelopes` also writes the filing times on the sampled rows of `index`, so a later `index` run alone resets them to null.

The `fetch` command needs the `SEC_USER_AGENT` environment variable. The SEC asks for a User-Agent that names the requester and gives a contact address. Without the variable, `fetch` exits with code 2. Live runs take the value from `sec.user_agent` in `conf/sec-edgar.json` at tag `ingest-parked-2026-11-16`, so the value stays out of the files on `main` outside `specs/`. This command sets it in any checkout or worktree:

```bash
export SEC_USER_AGENT="$(git show ingest-parked-2026-11-16:conf/sec-edgar.json | python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"])')"
```

The `fetch` command keeps the Stage 1 budget. It sends at most 1,500 requests and 5 GB, and it starts each request at least 0.34 s after the one before. It records each request in `ROOT/fetch-log.jsonl`.

### Code version

Each table records the commit of the code that wrote it. The code version is the full 40-character commit of the git checkout that holds the package code. The code finds that checkout from its own module path, not from the current folder.

Ten commands write tables, files or manifests under `ROOT`. This text calls them the write commands. They are `index`, `sample`, `fetch`, `refetch`, `envelopes`, `facts`, `ownership`, `compare-refetches`, `build-fetches` and `manifest`. Each write command refuses to run unless the pinned paths have no uncommitted change. The pinned paths are `packages/sec-filing-data`, `pyproject.toml`, `uv.lock` and `.python-version`, all from the top of the checkout. Staged, unstaged and untracked changes count. Ignored files do not count, and neither do changes outside the pinned paths, such as `specs/` or `README.md`. A write command also refuses when no commit can be read, for example when `git` is missing.

A refusal prints `error: refused: <reason>` to stderr and exits with code 3. No other outcome uses code 3. The refusal comes first, so a refused write command writes nothing under `ROOT`, not even a `runs.jsonl` line. It also comes before the `SEC_USER_AGENT` check, so `fetch` on a changed tree exits 3 and not 2. The read-only commands never refuse: `report`, `rebuild`, `check-stage1`, `check-frozen` and `verify`.

`write_table` writes four keys into the Parquet key-value metadata of each table file. They are `sec_filing_data.code_version`, `sec_filing_data.python_version`, `sec_filing_data.pyarrow_version` and `sec_filing_data.table_format`. Together they are the stamp of the file. The format number, `table_format`, comes from `TABLE_FORMATS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`. A file with no stamp reads `not recorded` for each key. The Versions section of `report` shows, for each table, the first 12 characters of the code version, the format number and the row count. It then counts the tables for each code version, so a mixed set shows.

Each `runs.jsonl` line has two more keys. `code_version` is the commit, or null when no commit can be read. `tree_clean` is true, false or null. A write command always writes true, because it refuses on any other state. A line from before Stage 3 has neither key.

### Output

All output is under `ROOT`:

- `tables/<name>.parquet`: one Parquet file for each table. The schemas are `SCHEMAS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`.
- `bytes/`: each fetched submission file, as fetched.
- `fetch-log.jsonl`: the request ledger.
- `stage2/`: the Stage 2 ledger, `fetch-log.jsonl`, and the refetched files in `refetch/`.
- `tables-stage1/`: the Stage 1 tables, copied once before Stage 2 changed them.
- `manifests/`: the manifests that `manifest` writes, one file for each table set and code version.
- `runs.jsonl`: the start and end time of each step.
- `fetch.lock`: the lock that stops two `fetch` runs at the same time.

## sec-edgar-ingest (removed)

The roadmap reset parked the older filing-index engine, `sec-edgar-ingest`, on 2026-11-16, and plan 12 removed it from `main`. Tag `ingest-parked-2026-11-16` holds its last state: `packages/sec-edgar-ingest/`, `conf/`, its scripts in `scripts/`, `docs/runbooks/` and `.sdd/`. To read a file, run `git show ingest-parked-2026-11-16:<path>`. Its specs, plans and evidence stay in `specs/`. Do not use its code or its store as an input to `sec-filing-data`.
