# 2a release build and offline verification (Stage 2a, plan 7 Task 9)

## Release
- **Release ID:** `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`
- **Manifest:** `/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json`
- **`git_revision`:** `32863852ce57f1da99db4720bd1c729727b4ec0c` (`main`, after the Stage 2a branch merge and the gate record). The tree was clean before the build (`git status --porcelain --untracked-files=all` printed nothing).
- **Build:** `scripts/prepare-native-release.py --offline` from the main checkout, on 2026-11-02. It printed the one release path above and exited 0.
- **Application wheel SHA-256:** `b8147687c056141ac0d0d6828819fdc3db726d2052ee596daead112ff069967a`. Package version `0.2.0`. The 1c wheel was `52716b7a…`. The wheel differs because the package code changed in Stage 2a.

## Locked inputs (D12)
The 1c release is `c4de77b89bb1d8ecc5d094f0e1dc6f8a5f3a7935e3595a9dd086d1e41a6b8aa7`. Its build revision is `3af121a468fdd6b3ec7d8286d5cf619493992d49`.

| Check | Result |
|---|---|
| `cmp` of `uv.lock` in the 2a release and in the 1c release | `lock-identical`. SHA-256 `e3d3dac9971ed75bdc5864ebd8c422c2e34bd24236a9a77bbadb6a87cddf1bbb`. |
| `runtime-requirements.txt` (the `uv export --package sec-edgar-ingest --no-dev --no-emit-workspace` output), without comment lines | `export-lines-identical`. Both files give SHA-256 `def62c21599d615c1945f47a984f6e7e053eeed63130422f8db65ed5a81fcb76`. See the note below. |
| `git diff --exit-code 3af121a468fdd6b3ec7d8286d5cf619493992d49 HEAD -- uv.lock pyproject.toml packages/sec-edgar-ingest/pyproject.toml` | `inputs-identical`. The diff is empty. |
| Package version | `0.2.0` in both releases. |
| `git_revision` in the 2a manifest | `32863852ce57f1da99db4720bd1c729727b4ec0c`. It equals `HEAD` of the clean tree before the build. |
| Dependencies | `certifi`, `charset-normalizer`, `idna`, `pyarrow`, `requests`, `urllib3`. The same six as the 1c release. No platform package. |

> Note: line 2 of `runtime-requirements.txt` is a comment. It records the random temporary directory that `uv export` used. So the check compares the requirement lines only, as plan 4, plan 5 and plan 6 did.

## Offline verification
> Note: the harness guard refuses any path inside a checkout, and the verifier children inherit the working directory. So the harness and the evidence directory were created under a temporary directory outside the checkout (`/var/folders/3m/6f8zc0l14dn8yz2x8yy2_3mw0000gn/T/tmp.gc8MYumfi9`). The verifier ran with that directory as its working directory. This is the same method as the 1b and 1c release evidence.

The verifier ran on the 2a interpreter (`-I -B -X pycache_prefix=/dev/null`) with `UV_OFFLINE=1` for the harness step. Its output is below. The `evidence` path in it is the temporary directory. The evidence was then copied to the durable evidence directory given below.

```json
{"exit": 0, "release_id": "e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec", "evidence": "/var/folders/3m/6f8zc0l14dn8yz2x8yy2_3mw0000gn/T/tmp.gc8MYumfi9/evidence"}
```

`preflight_current` on the 2a interpreter printed `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`.

**Evidence directory:** `/Users/lowell/Projects/sec-edgar-local/fixture-data/s2a-verify-evidence/` (git-ignored, because the temporary directory is not durable). `report.json` has SHA-256 `78856ef97f70f35ca049a9bfaef42a61aa7f8fba5b9325826587ce65a7a85032`. `command.json` has `118d2d80c65090821538ce7da037a000feac4c10cf387216e61bc27a58040ae2`.

## Retention (D10)
`releases/` holds these release directories:
- `sha256=49b7a2ed…`
- `sha256=900952a8…`
- `sha256=d718ae5f…`
- `sha256=fc68adef…`
- `sha256=aa8de1ac…` (D5)
- `sha256=9fa189a0…` (1b)
- `sha256=c4de77b8…` (1c)
- `sha256=e49d3ba8…` (2a, new)

`releases/` also holds `artifact-cache` and `task14-guard-proofs`. The 1c release and all older releases are kept. The build added one release directory and removed none. Selecting the 1c release for a store with v2 objects is unsupported (D10).

## Network
No SEC request was sent. Verification used fixture acquisition only.

## Statement
No SEC request was sent in this task. Nothing was written under `data/`. The live config (`conf/sec-edgar-local.json`) still selects the 1c release. The selection moves in a later task.

## Scratch re-transform
This section records plan 7 Task 10 (spec §6 "Scratch re-transform" and the budget stop rule). It ran on 2026-11-02 in the main checkout on `main` at `db0be14a49b0aa692e384d335f608c4859cb119c`.

- **Scratch path:** `/tmp/stage2a-scratch-20261102T121107Z`. It held a `cp -Rp` copy of `data/` (1.0 GB). The copy was removed after this record.
- **Interpreter:** `releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/venv/bin/python -I -B -X pycache_prefix=/dev/null` (the 2a release).
- **Config:** `scratch/config.json`. It is `conf/sec-edgar-local.json` with 4 changes: `storage.root` (the copy), `logging.root` (the scratch directory), `runtime.release_manifest` (the 2a manifest) and `etl` (`sec-index-parser-v2` / `sec-index-v2`). The live config was not changed.
- **Script:** `scratch/retransform.py`. It opens the copy with its stored binding (the `diag2.py` method). It loads the config, runs `preflight_current` and calls `runtime.retain_manifest` once in each invocation. Each `run_transform` or `run_publish` call gets a fresh `RunContext`: the start is the current UTC time, the deadline is the start plus `execution.max_run_seconds` (3,600 s), and `pin_context` uses the UTC date of the start (2026-11-02). So 2026Q3 is a closed quarter. The wall times below come from `time.monotonic()` around the production call only.
- **Records:** `scratch/sources.json` (the `locate` output), `scratch/results.json` (one JSON line for each step, 39 lines), `scratch/live-data-before.sha256` and `scratch/live-data-after.sha256`.

### Steps
1. The `pgrep` writer check printed nothing.
2. `data/` was hashed (5,269 files) and copied to the scratch path.
3. `locate` found 35 entries: 28 quarterly and 7 daily. Each source is in a snapshot workset with 1 member. The 2024Q1 quarterly source is in 2 worksets and the 2026Q4 quarterly source is in 3. The script chose a one-member workset for each. Every workset decoded. The store accepted the stored binding and the producer check.
4. The probe `transform --only 2943ef17ff8cda5083714c2749463d60c0374fe9b74798b89af107cff06bf971` (daily 2026-07-22) transformed the source in 2.5 s. No binding or producer refusal occurred. The source has 3,525 rows and 3,490 distinct keys. 3 keys merged, and all 3 are in the rename class (spec §1.1). 24 other keys are identical repeats: the same form type and the same company name on more than one line. The v1 code also accepted identical repeats, and they add no list item.
5. The full `transform` ran in the background from 12:17 to 14:03 UTC. All 35 sources transformed. No source stayed quarantined. The run did the 2026-07-22 workset again. It reused the probe observation (`unchanged`, 1.4 s). The table shows the probe numbers for that source.
6. `publish-2023Q1`, then `candidate-2026Q3`, each in the background (results below).
7. The `data/` comparison printed `data-unchanged`.

### Per-source results
Merged keys are counted by class. "Combined filing" means the same company name with more than one form type. "Rename" means the same form type with more than one company name. "Both" means both lists have more than one item. "Identical repeat" means repeated lines with one form type and one name. The source IDs are shortened. The full IDs and raw SHA-256 values are in `scratch/sources.json`.

| Source ID | Kind | Period | Rows | Distinct keys | Combined filing | Rename | Both | Identical repeat | Wall time (s) | Outcome |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `bd2d51a024fe…` | quarterly | 2020Q1 | 324,904 | 324,895 | 5 | 4 | 0 | 0 | 244.2 | transformed |
| `d48449efef9c…` | quarterly | 2020Q2 | 265,509 | 265,501 | 8 | 0 | 0 | 0 | 204.8 | transformed |
| `fe9845224379…` | quarterly | 2020Q3 | 221,732 | 221,713 | 19 | 0 | 0 | 0 | 171.8 | transformed |
| `4cce6ce98641…` | quarterly | 2020Q4 | 233,422 | 233,414 | 5 | 3 | 0 | 0 | 181.2 | transformed |
| `3320547af4a8…` | quarterly | 2021Q1 | 361,314 | 361,311 | 3 | 0 | 0 | 0 | 281.4 | transformed |
| `6a0020e924d9…` | quarterly | 2021Q2 | 300,161 | 300,157 | 4 | 0 | 0 | 0 | 234.1 | transformed |
| `cbd02147f588…` | quarterly | 2021Q3 | 252,239 | 252,238 | 1 | 0 | 0 | 0 | 196.8 | transformed |
| `1928beeb17d6…` | quarterly | 2021Q4 | 258,325 | 258,309 | 16 | 0 | 0 | 0 | 201.5 | transformed |
| `89a438366b5d…` | quarterly | 2022Q1 | 356,546 | 356,533 | 12 | 1 | 0 | 0 | 277.6 | transformed |
| `aa3f15489c2d…` | quarterly | 2022Q2 | 291,655 | 291,652 | 2 | 1 | 0 | 0 | 225.1 | transformed |
| `5b9178624fda…` | quarterly | 2022Q3 | 237,785 | 237,783 | 2 | 0 | 0 | 0 | 185.4 | transformed |
| `5bf45a54eb1d…` | quarterly | 2022Q4 | 230,687 | 230,670 | 16 | 1 | 0 | 0 | 180.2 | transformed |
| `d5993ae0df71…` | quarterly | 2023Q1 | 348,472 | 348,463 | 8 | 1 | 0 | 0 | 271.0 | transformed |
| `ddb29ce18a35…` | quarterly | 2023Q2 | 307,804 | 307,789 | 12 | 3 | 0 | 0 | 236.9 | transformed |
| `567e24a500ff…` | quarterly | 2023Q3 | 252,638 | 252,622 | 16 | 0 | 0 | 0 | 196.5 | transformed |
| `537e61351070…` | quarterly | 2023Q4 | 251,352 | 251,345 | 7 | 0 | 0 | 0 | 196.4 | transformed |
| `b2d153963f7d…` | quarterly | 2024Q1 | 370,321 | 370,318 | 3 | 0 | 0 | 0 | 289.4 | transformed |
| `d6232d2baa25…` | quarterly | 2024Q2 | 316,037 | 316,030 | 7 | 0 | 0 | 0 | 244.4 | transformed |
| `006745fd2f89…` | quarterly | 2024Q3 | 270,955 | 270,931 | 24 | 0 | 0 | 0 | 209.0 | transformed |
| `52bf7b8dc46c…` | quarterly | 2024Q4 | 284,205 | 284,189 | 12 | 4 | 0 | 0 | 221.1 | transformed |
| `5649cc6ee978…` | quarterly | 2025Q1 | 340,126 | 340,108 | 15 | 3 | 0 | 0 | 266.8 | transformed |
| `41c1edd82ed6…` | quarterly | 2025Q2 | 331,794 | 331,787 | 3 | 4 | 0 | 0 | 261.7 | transformed |
| `e19b1bf15d2f…` | quarterly | 2025Q3 | 287,910 | 287,909 | 1 | 0 | 0 | 0 | 225.9 | transformed |
| `644b37c7184b…` | quarterly | 2025Q4 | 276,646 | 276,645 | 1 | 0 | 0 | 0 | 216.6 | transformed |
| `f8f05c9fd9e6…` | quarterly | 2026Q1 | 370,368 | 370,363 | 5 | 0 | 0 | 0 | 293.4 | transformed |
| `239446e779b8…` | quarterly | 2026Q2 | 353,480 | 353,457 | 23 | 0 | 0 | 0 | 285.0 | transformed |
| `5005901a1e81…` | quarterly | 2026Q3 | 302,499 | 302,494 | 5 | 0 | 0 | 0 | 240.8 | transformed |
| `d64895140b03…` | quarterly | 2026Q4 | 84,767 | 84,766 | 1 | 0 | 0 | 0 | 67.2 | transformed |
| `bde739dfaa2e…` | daily | 2026-07-08 | 3,930 | 3,894 | 2 | 0 | 0 | 28 | 3.1 | transformed |
| `04d46fadab78…` | daily | 2026-07-13 | 2,989 | 2,952 | 1 | 0 | 0 | 29 | 2.4 | transformed |
| `2943ef17ff8c…` | daily | 2026-07-22 | 3,525 | 3,490 | 0 | 3 | 0 | 24 | 2.5 | transformed (probe) |
| `55caa01bcbeb…` | daily | 2026-07-27 | 4,099 | 4,011 | 1 | 0 | 0 | 82 | 3.3 | transformed |
| `1c20057e2749…` | daily | 2026-09-17 | 4,149 | 4,077 | 1 | 0 | 0 | 68 | 3.4 | transformed |
| `d2c80002601d…` | daily | 2026-09-24 | 3,699 | 3,582 | 1 | 0 | 0 | 112 | 2.9 | transformed |
| `ae3817980957…` | daily | 2026-10-21 | 3,283 | 3,251 | 1 | 0 | 0 | 26 | 2.6 | transformed |

Totals: the 28 quarterly sources have 236 combined-filing keys and 25 rename keys. The 7 daily sources have 7 combined-filing keys, 3 rename keys and 369 identical-repeat keys. No key is in the "both" class. The transform wall time is 6,306 s for the quarterly sources and 20 s for the daily sources.

### Full rebuilds
Each publish ran on the one-member transformed workset of its quarterly source. Each touched only its own quarter. A publish wall time covers `run_publish` only. It includes the inline v2 re-transform of the base generation's v1 sources. It excludes the readback and the extra candidate check.

| Quarter | Outcome | Gate | Base generation | Sources | Rows | Changes | Publish wall time |
|---|---|---|---|---:|---:|---|---:|
| 2023Q1 | `published` | `clear` | none (no 2023Q1 pointer existed) | 1 quarterly | 348,463 | added 348,463 | 733.8 s |
| 2026Q3 | `awaiting_approval` | `awaiting_approval` | `91389291…` (`sec-index-v1`, 77 daily sources) | 1 quarterly, 77 daily | 302,494 | added 21,571; updated 0; withdrawn 42; unresolved_absence 0; provenance_refreshed 280,923 | 1,306.7 s |

The percentages give the share of each limit that the publish used.

| Quarter | Publish wall time | Against the 1,500 s budget | Against the 1,800 s reserve | Against the 3,300 s launcher default |
|---|---:|---|---|---|
| 2023Q1 | 733.8 s | below: 49 %, 766.2 s left | below: 41 % | below: 22 % |
| 2026Q3 | 1,306.7 s | below: 87 %, 193.3 s left | below: 73 % | below: 40 % |

- **2023Q1:** generation `a09b511a8cee9907ea143a7025e70ece3a5d91d334d2e271e290b5ab28006ced` (`sec-index-v2`, closed). `capture_quarter` and `read_quarter` read back 348,463 rows, which equals the manifest `row_count`. The readback took 513.9 s. This publish made the first 2023Q1 generation. It had no v1 base, so it did not map base rows with `upgrade_row`.
- **2026Q3:** candidate `6674c9f6e93323a00e460a4089929636ded2c4af4f060c39b67e3a072d0b75b9` (`sec-index-v2`, closed). The 42 withdrawals gate it. `validate_candidate_content` passed on the gated candidate. The 2026Q3 pointer value and version (`cccb8624e7414dba943ff3332cec5210`) were the same before and after. The pointer still names the v1 generation `913892913dcb3ad6817757f50cbbf2d12f3ac519b56abdc7be1eef48fb4b95c5` (`sec-index-v1`). The copy holds no approval record.

### Budget stop rule (Step 8)
Both publish wall times are below 1,500 s. The stage did not stop, and no owner decision is needed under the budget stop rule. Task 11 (the live-config selection) can go ahead after its own owner checkpoint. The 2026Q3 margin is 193.3 s. That rebuild re-transforms 77 daily sources inline, and the count grows as daily sources are added to a quarter.

### Live data
The `cmp` of `live-data-before.sha256` and `live-data-after.sha256` printed `data-unchanged`. Both files have 5,269 lines. No line differs. Neither file lists `state.sqlite3-wal` or `state.sqlite3-shm`, because `data/` had neither file before or after. A `find data -newer` check after the probe printed nothing.

The 2026Q3 candidate was not approved.

No SEC request was sent. Nothing was written under `data/`.

## Live-config selection
This section records plan 7 Task 11 (spec §6 "Live-config selection"). It ran on 2026-11-02 in the main checkout on `main`. The owner approved the selection at the Task 11 checkpoint. The approval authorizes no SEC traffic and no live run.

- **Release ID (`<2A>`):** `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`.
- **Changed config values:** `conf/sec-edgar-local.json` changed in three values and nothing else.
  - `runtime.release_manifest`: from the 1c manifest (`releases/sha256=c4de77b8…/release.json`) to `/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json`.
  - `etl.parser_version`: from `sec-index-parser-v1` to `sec-index-parser-v2`.
  - `etl.schema_version`: from `sec-index-v1` to `sec-index-v2`.
- **Offline preflight:** it ran the plan 6 Task 7 Step 2 command on the 2a interpreter (`-I -B -X pycache_prefix=/dev/null`). It did not refuse. It printed:
  - `floor 480`
  - `reserve 1800`
  - `release e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`
  - `effective f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733`
  - `binding` (below)
- **Effective-config SHA-256:** `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733`. The earlier value was `fb93b0e8e05dbc1cbc9bd167ae02ef2d775629905c15938055a6a93c5fb95e96`, as recorded in the parent spec and in the baseline-campaign preflight evidence. The two values differ.
- **Floor:** 480 s (`DISPATCH_RESERVE_FLOOR_SECONDS`).
- **Reserve:** 1800 s. `execution.dispatch_reserve_seconds` is unchanged.
- **Binding**, as printed by the preflight. It holds no `execution` field.

```
{'binding_version': 'sec-local-binding-v1', 'root': '/Users/lowell/Projects/sec-edgar-local/data', 'acquisition_mode': 'live', 'namespace': 'sec-owner-lowell-mason', 'sec': {'user_agent': 'Lowell Mason sec-edgar-ingest mason.lowell@mac.com', 'requests_per_second': 3.0, 'max_active_collectors': 1}, 'coordination': {'lease_seconds': 60.0, 'renew_every_seconds': 20.0, 'namespace': 'sec-owner-lowell-mason', 'clock_uncertainty_seconds': 2.0}, 'storage_contract': 'sec-local-storage-v1'}
```

The Task 9 "Statement" section above says the live config still selects the 1c release. That was true at Task 9. This selection supersedes it.

No SEC request was sent in this stage.
