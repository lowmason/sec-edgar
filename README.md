# sec-edgar

This repository is one uv workspace with two Python packages:

- `sec-filing-data` (live): makes plain tables from the SEC filings of one quarter, 2026Q3.
- `sec-edgar-ingest` (parked on 2026-11-16): the older filing-index ingestion engine. No current output depends on it. It will be removed from `main` under a git tag after Stage 2.

The work follows the [roadmap](specs/sec-filing-data-roadmap.md). Stage 1 is complete. Its results are in the [Stage 1 findings](specs/sec-filing-data-stage-1-findings.md). Stage 2 adds provenance and filing times. Its [spec](specs/sec-filing-data-stage-2-provenance-and-timing.md) and [plan](specs/plans/11-sec-filing-data-stage-2-provenance-and-timing.md) are in `specs/`.

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

The `fetch` command needs the `SEC_USER_AGENT` environment variable. The SEC asks for a User-Agent that names the requester and gives a contact address. Without the variable, `fetch` exits with code 2. The live runs take the value from `sec.user_agent` in `conf/sec-edgar.json`.

The `fetch` command keeps the Stage 1 budget. It sends at most 1,500 requests and 5 GB, and it starts each request at least 0.34 s after the one before. It records each request in `ROOT/fetch-log.jsonl`.

### Output

All output is under `ROOT`:

- `tables/<name>.parquet`: one Parquet file for each table. The schemas are `SCHEMAS` in `packages/sec-filing-data/src/sec_filing_data/tables.py`.
- `bytes/`: each fetched submission file, as fetched.
- `fetch-log.jsonl`: the request ledger.
- `runs.jsonl`: the start and end time of each step.
- `fetch.lock`: the lock that stops two `fetch` runs at the same time.

## sec-edgar-ingest (parked)

The roadmap reset parked this package on 2026-11-16. Do not use its code or its store as an input to `sec-filing-data`. The text below describes it as it was when it was parked.

A native local fork of SEC filing-index ingestion, distribution/import `sec-edgar-ingest` / `sec_edgar_ingest` version 0.2.0. It retains immutable SEC index originals, transforms validated observations, and publishes captured per-quarter Parquet generations with reconciliation, withdrawal approval and recorded rollback.

The first supported host is this Mac: CPython 3.14, macOS arm64, and a native filesystem with working SQLite locking and atomic filesystem operations. Runtime dependencies are Requests 2.34.2, PyArrow 25.0.1 and their exact locked transitives. No cloud SDK, CLI, container service or cloud fallback is required.

Start with [native setup](docs/runbooks/native-setup.md), then [manual local ingestion](docs/runbooks/local-ingestion.md). Keep [recovery](docs/runbooks/local-recovery.md) and [release upgrades](docs/runbooks/release-upgrades.md) with operational evidence. Dependencies/artifacts are prepared explicitly before the offline checks:

```sh
uv sync --locked
sh scripts/check-sec-edgar-ingest.sh
```

The complete check fails if its declared offline artifacts are absent. Test-only `SEC_LOCAL_PROOF_CACHE` and `SEC_LOCAL_PROOF_CATALOG` are described in setup. Ingestion uses an immutable non-editable installed release and never syncs dependencies. No scheduling or notifications are installed.

L01–L11/L13 have [renewed passing offline evidence](specs/evidence/local-port/offline-renewal-task15.md). The separate [genuine SEC acceptance record](specs/evidence/local-port/sec-acceptance.md) records an L12 pass established by a reviewed supplemental offline adjudication of the preserved genuine attempt; the original run and verification remain incomplete with exit 12. This bounded result does not establish historical coverage or authorize further live runs. The preserved generated default config still references the old `900952a8…` release and was not selected for this acceptance case; further operation requires explicit reviewed release/config selection, budgets and operating gates.
