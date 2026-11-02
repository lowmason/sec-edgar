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
