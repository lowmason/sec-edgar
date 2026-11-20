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
- `manifest --set SET [--zip PATH]` writes the manifest of one table set. `SET` is `tables`, `tables-stage1`, `tables-stage2` or `stage4`. The `stage4` set has its own rules, in the Stage 4 list below. The manifest is the file `ROOT/manifests/SET@COMMIT.json`, where `COMMIT` is the first 12 characters of the code version. It lists each file in `ROOT/SET/` with its size and SHA-256. For each Parquet file, it also lists the row count and the stamp (see Code version). The manifest of `tables` also lists the inputs that `rebuild` reads. So `--set tables` needs `--zip PATH`, the path of `master.zip`, and no other set takes `--zip`. The command prints `manifest: PATH` and `sha256: HASH`. It never overwrites a manifest. It exits 0 when it writes the manifest. It exits 1 when the manifest exists, or when the set folder is missing. For `tables`, it also exits 1 when the zip or `ROOT/fetch-log.jsonl` is missing. It exits 2 when `--zip` is missing for `tables` or given for another set. It exits 3 when it refuses.
- `verify --manifest PATH [--rows N] [--seed S]` checks the root against a manifest. `--out` must be the `root` that the manifest names. The command prints `seed: S`, then one line for each check. It exits 0 when every line is `ok` or `not run`, and 1 otherwise. A manifest that it cannot read gives one line and exit 1. It writes nothing except its `runs.jsonl` line. It has three parts. Parts 2 and 3 run for the manifests of `tables` and `stage4`. Their lines read `not run, no inputs listed` for the other manifests.
  1. Files: each listed file is there with its listed size, SHA-256 and stamp, and no unlisted file is in the set folder. For the manifest of `tables`, this covers `bytes/` and `stage2/refetch/` too.
  2. Binding: each record hash and each ledger hash ties to a listed input. It covers every row.
  3. Re-derivation: `N` rows of each of the `index`, `filings`, `parties`, `documents`, `facts` and `ownership` tables are derived again from the listed input bytes. Each derived row must equal its table row. `--rows` is `N` and defaults to 20. An `N` below 1 is a usage error (exit 2). `--seed` seeds the choice of rows and defaults to 20261119.

Stage 4 added four commands and one manifest set. They add the partners of the sampled filings and an as-of query. A partner is a filing in the index that is not in the sample, and that a rule ties to a sampled filing. A CIK is the SEC number of a filer. Run these three commands after the Stage 3 steps, in this order:

1. `partners` writes `ROOT/stage4/tables/partners.parquet` from the `index` and `sample` tables and the bytes of the sampled amendments. It sends no request. It prints `partners: N`, then one line for each rule with its row count. It exits 0, or 3 when it refuses. Three rules choose the partners:
   - `original_previous_accession`: a sampled Schedule 13D/A, Schedule 13G/A or Form D/A names its original. The index must list that original.
   - `original_date_issuer_owner`: a sampled Form 3/A, 4/A or 5/A gives the date, issuer and owners of its original. The index must list exactly one matching filing.
   - `candidate_amendment`: a sampled filing has form type X, and the index lists a filing of form type X/A. It has the same CIKs, and its filing date is the same or later. X is `SCHEDULE 13D`, `SCHEDULE 13G`, `SC 13D`, `SC 13G`, `D`, `3`, `4`, `5` or `13F-HR`.
2. `fetch-partners` fetches the submission file of each partner into `ROOT/stage4/bytes/`. It sends SEC requests, and it needs `SEC_USER_AGENT` like `fetch`. It skips a partner whose file exists, and it tries a failed partner again. It counts each request in `ROOT/stage4/fetch-log.jsonl`. After each run, it writes the `fetches` table under `ROOT/stage4/tables/`. It prints the outcome counts, `stage 4 requests: N of 30` and `stage 4 wire bytes: N of 50000000`. Its exit codes are:
   - 0 after a full walk.
   - 1 when the `partners` table is missing.
   - 2 without `SEC_USER_AGENT`.
   - 3 when it refuses.
   - 5 when the Stage 4 budget is spent.
   - 6 when the SEC answers 403.
3. `partner-tables` writes the other Stage 4 tables under `ROOT/stage4/tables/`. They are `fetches`, `filings`, `parties`, `documents`, `ownership`, `ownership_status` and `links`. It sends no request. It reads the partner bytes and the Stage 4 ledger, and it parses them with the Stage 3 code. It prints `<table>: <rows>` for each table. It exits 0, 1 when the `partners` table is missing, or 3 when it refuses.

The `links` table has one row for each held amendment, from the sample or from the partners. A held filing is a filing whose fetch is `ok`. An amendment is a held filing whose form type ends in `/A`. The row names the original that the bytes of the amendment declare. When the rule finds no original, the row names the problem instead.

The Stage 4 budget is at most 30 requests and 50,000,000 wire bytes. `fetch-partners` starts each request at least 0.34 s after the one before, so it sends under 3 requests a second. It takes `ROOT/fetch.lock`, so no other `fetch`, `refetch` or `fetch-partners` runs on the root. Run no other SEC client at the same time. When the budget is spent, `fetch-partners` stops and exits with code 5.

The other Stage 4 commands and checks:

- `manifest --set stage4` writes `ROOT/manifests/stage4@COMMIT.json`.
  - It lists each file in `ROOT/stage4/tables/` with its size, SHA-256, row count and stamp.
  - It lists each file in `ROOT/stage4/bytes/` and `ROOT/stage4/fetch-log.jsonl` as an input.
  - It records `builds_on`, the path and SHA-256 of the `tables` manifest. Write the `tables` manifest first.
  - It takes no `--zip`.
  - It exits 0 when it writes the manifest. It exits 1 when the manifest exists. It also exits 1 when `ROOT/stage4/tables/`, the `tables` manifest or the Stage 4 ledger is missing. It exits 1 too when the files of `tables` name more than one code version. It exits 2 when `--zip` is given. It exits 3 when it refuses.
- `asof --out ROOT --at T [--table NAME]` prints what was public by the time `T`.
  - `T` is a date `YYYY-MM-DD`, which means the end of that day in New York. It can also be an ISO 8601 instant with a UTC offset or `Z`.
  - A filing is known from its `known_from` time. That time is when the stored copy was last modified, or else when we fetched it.
  - `asof` keeps each record of the sample and of the partners whose `known_from` is at or before `T`.
  - Before it answers, it checks each table file that it reads against the `tables` manifest and the `stage4` manifest. Write both manifests first.
  - It prints `at: T` in UTC, one line for each manifest, and one line for each table. A table line gives the row count by `held_in`. The value of `held_in` is where the filing is held: `sample`, `partner`, or `index` for an index row of a filing that we do not hold.
  - `--table NAME` also prints the rows of one table as JSON Lines to stdout, and it moves the summary to stderr. `NAME` is `index`, `filings`, `parties`, `documents`, `facts`, `ownership` or `links`. Each row keeps its stored columns and gains `known_from` and `held_in`.
  - It writes only its `runs.jsonl` line, and it never refuses for the tree state.
  - It exits 0 on an answer, 1 on a refusal, and 2 on a usage error. A refusal means that a file differs from its manifest, that a manifest is missing, or that the manifests do not fit together.
- `verify` runs the same three parts on the `stage4` manifest.
  - Part 1 also checks the `tables` manifest that `builds_on` names. It checks each `tables/` file and sampled byte file that Stage 4 reads too.
  - Part 2 ties each source hash of `filings`, `parties`, `documents`, `ownership` and `links` to a listed input. It does the same for each ledger hash of `fetches`.
  - Part 3 derives the whole `partners` table again. It also derives `N` seeded rows of each of `filings`, `parties`, `documents`, `ownership` and `links`.
- `rebuild` prints 19 lines on a root with a `ROOT/stage4/` folder. It re-creates the Stage 4 tables in its temporary folder too. It prints the 11 Stage 3 lines, then 8 lines `stage4 <table>: <result>`. All 19 lines must be `equal` at the Stage 4 commit. A root with no `ROOT/stage4/` folder gives the 11 lines as before.
- `report` has a Stage 4 section before Versions. When `ROOT/stage4/tables/` exists, Versions lists the Stage 4 tables with the label `stage4`. The Stage 4 section gives:
  - the partners by rule, the partner fetch outcomes, and the Stage 4 ledger use against its limits.
  - the links by rule, and by where the original is held.
  - the pairs. A pair is a link whose amendment and original are both held. A forward pair has a sampled original and a partner amendment. Two partners make a forward pair too, when both come from one sampled filing and the original is a `candidate_amendment` partner. A reverse pair has a sampled amendment and a partner original. The report counts the other pairs apart.
  - the pairs whose amendment answers first.
  - the held filings that are known before their `public_at`. The `public_at` time is the earliest time that a filing could be public.

`facts` and `ownership` read the `filings` table, so run them after `envelopes`. `envelopes` also writes the filing times on the sampled rows of `index`, so a later `index` run alone resets them to null.

The `fetch` command needs the `SEC_USER_AGENT` environment variable. The SEC asks for a User-Agent that names the requester and gives a contact address. Without the variable, `fetch` exits with code 2. Live runs take the value from `sec.user_agent` in `conf/sec-edgar.json` at tag `ingest-parked-2026-11-16`, so the value stays out of the files on `main` outside `specs/`. This command sets it in any checkout or worktree:

```bash
export SEC_USER_AGENT="$(git show ingest-parked-2026-11-16:conf/sec-edgar.json | python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"])')"
```

The `fetch` command keeps the Stage 1 budget. It sends at most 1,500 requests and 5 GB, and it starts each request at least 0.34 s after the one before. It records each request in `ROOT/fetch-log.jsonl`.

### Code version

Each table records the commit of the code that wrote it. The code version is the full 40-character commit of the git checkout that holds the package code. The code finds that checkout from its own module path, not from the current folder.

Thirteen commands write tables, files or manifests under `ROOT`. This text calls them the write commands. They are `index`, `sample`, `fetch`, `refetch`, `envelopes`, `facts`, `ownership`, `compare-refetches`, `build-fetches`, `manifest`, `partners`, `fetch-partners` and `partner-tables`. Each write command refuses to run unless the pinned paths have no uncommitted change. The pinned paths are `packages/sec-filing-data`, `pyproject.toml`, `uv.lock` and `.python-version`, all from the top of the checkout. Staged, unstaged and untracked changes count. Ignored files do not count, and neither do changes outside the pinned paths, such as `specs/` or `README.md`. A write command also refuses when no commit can be read, for example when `git` is missing.

A refusal prints `error: refused: <reason>` to stderr and exits with code 3. No other outcome uses code 3. The refusal comes first, so a refused write command writes nothing under `ROOT`, not even a `runs.jsonl` line. It also comes before the `SEC_USER_AGENT` check, so `fetch` on a changed tree exits 3 and not 2. The read-only commands never refuse: `report`, `rebuild`, `check-stage1`, `check-frozen`, `verify` and `asof`.

`write_table` writes four keys into the Parquet key-value metadata of each table file. They are `sec_filing_data.code_version`, `sec_filing_data.python_version`, `sec_filing_data.pyarrow_version` and `sec_filing_data.table_format`. Together they are the stamp of the file. The format number, `table_format`, comes from `TABLE_FORMATS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`. A file with no stamp reads `not recorded` for each key. The Versions section of `report` shows, for each table, the first 12 characters of the code version, the format number and the row count. It then counts the tables for each code version, so a mixed set shows.

Each `runs.jsonl` line has two more keys. `code_version` is the commit, or null when no commit can be read. `tree_clean` is true, false or null. A write command always writes true, because it refuses on any other state. A line from before Stage 3 has neither key.

### Output

All output is under `ROOT`:

- `tables/<name>.parquet`: one Parquet file for each table. The schemas are `SCHEMAS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`.
- `bytes/`: each fetched submission file, as fetched.
- `fetch-log.jsonl`: the request ledger.
- `stage2/`: the Stage 2 ledger, `fetch-log.jsonl`, and the refetched files in `refetch/`.
- `stage4/`: the Stage 4 files. `tables/<name>.parquet` holds the 8 Stage 4 tables. `bytes/` holds each fetched partner submission file. `fetch-log.jsonl` is the Stage 4 request ledger.
- `tables-stage1/`: the Stage 1 tables, copied once before Stage 2 changed them.
- `manifests/`: the manifests that `manifest` writes, one file for each table set and code version.
- `runs.jsonl`: the start and end time of each step.
- `fetch.lock`: the lock that stops two `fetch` runs at the same time.

## sec-edgar-ingest (removed)

The roadmap reset parked the older filing-index engine, `sec-edgar-ingest`, on 2026-11-16, and plan 12 removed it from `main`. Tag `ingest-parked-2026-11-16` holds its last state: `packages/sec-edgar-ingest/`, `conf/`, its scripts in `scripts/`, `docs/runbooks/` and `.sdd/`. To read a file, run `git show ingest-parked-2026-11-16:<path>`. Its specs, plans and evidence stay in `specs/`. Do not use its code or its store as an input to `sec-filing-data`.
