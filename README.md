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

`facts` and `ownership` read the `filings` table, so run them after `envelopes`. `envelopes` also writes the filing times on the sampled rows of `index`, so a later `index` run alone resets them to null.

The `fetch` command needs the `SEC_USER_AGENT` environment variable. The SEC asks for a User-Agent that names the requester and gives a contact address. Without the variable, `fetch` exits with code 2. Live runs take the value from `sec.user_agent` in `conf/sec-edgar.json` at tag `ingest-parked-2026-11-16`, so the value stays out of the files on `main`. This command sets it in any checkout or worktree:

```bash
export SEC_USER_AGENT="$(git show ingest-parked-2026-11-16:conf/sec-edgar.json | python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"])')"
```

The `fetch` command keeps the Stage 1 budget. It sends at most 1,500 requests and 5 GB, and it starts each request at least 0.34 s after the one before. It records each request in `ROOT/fetch-log.jsonl`.

### Output

All output is under `ROOT`:

- `tables/<name>.parquet`: one Parquet file for each table. The schemas are `SCHEMAS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`.
- `bytes/`: each fetched submission file, as fetched.
- `fetch-log.jsonl`: the request ledger.
- `stage2/`: the Stage 2 ledger, `fetch-log.jsonl`, and the refetched files in `refetch/`.
- `tables-stage1/`: the Stage 1 tables, copied once before Stage 2 changed them.
- `runs.jsonl`: the start and end time of each step.
- `fetch.lock`: the lock that stops two `fetch` runs at the same time.

## sec-edgar-ingest (removed)

The roadmap reset parked the older filing-index engine, `sec-edgar-ingest`, on 2026-11-16, and plan 12 removed it from `main`. Tag `ingest-parked-2026-11-16` holds its last state: `packages/sec-edgar-ingest/`, `conf/`, its scripts in `scripts/`, `docs/runbooks/` and `.sdd/`. To read a file, run `git show ingest-parked-2026-11-16:<path>`. Its specs, plans and evidence stay in `specs/`. Do not use its code or its store as an input to `sec-filing-data`.
