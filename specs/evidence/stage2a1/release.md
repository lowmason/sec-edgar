# 2a1 release build and offline verification (Stage 2a1, plan 9 Task 9)

## Release
- **Release ID:** `f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18`
- **Manifest:** `/Users/lowell/Projects/sec-edgar-local/releases/sha256=f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18/release.json`
- **`git_revision`:** `e899d79a82fd4229558a3a42ac9fa532293d23e1` (`main`, after the Stage 2a1 branch merge, the gate record and Decision D8). The tree was clean before the build: `git status --porcelain --untracked-files=all` printed nothing.
- **Build:** `scripts/prepare-native-release.py --offline` from the main checkout, on 2026-11-15 (16:35:17 to 16:35:20 UTC). It used `UV_OFFLINE=1`, `uv run --offline --locked` and the artifact cache. It printed the one release path above and exited 0. The tree was still clean after the build.
- **Application wheel SHA-256:** `61ceab4210ed4a0504a9c4fa6de177b632823ce4679f1d314c2c82bd8d6728f5`. Package version `0.2.0`. The 2a wheel was `b8147687…`. The wheel differs because the package code changed (the Stage 2a1 source).

## Locked inputs (H9)
The 2a release is `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`. Its build revision is `32863852ce57f1da99db4720bd1c729727b4ec0c`.

| Check | Result |
|---|---|
| `cmp` of `uv.lock` in the 2a1 release and in the 2a release | `lock-identical`. SHA-256 `e3d3dac9971ed75bdc5864ebd8c422c2e34bd24236a9a77bbadb6a87cddf1bbb`. |
| `runtime-requirements.txt` (the `uv export --package sec-edgar-ingest --no-dev --no-emit-workspace` output), without comment lines | `export-lines-identical`. Both files give SHA-256 `def62c21599d615c1945f47a984f6e7e053eeed63130422f8db65ed5a81fcb76` (the hash of the lines without comments). |
| `git diff --exit-code 32863852ce57f1da99db4720bd1c729727b4ec0c HEAD -- uv.lock pyproject.toml packages/sec-edgar-ingest/pyproject.toml` | `inputs-identical`. The diff is empty. |
| Package version | `0.2.0` in both releases. |
| `git_revision` in the 2a1 manifest (`identity.git_revision`) | `e899d79a82fd4229558a3a42ac9fa532293d23e1`. It equals `HEAD` of the clean tree before the build. |
| `uv_lock_sha256` in the manifest identity | The same value in both releases: `e3d3dac9…`. |
| Dependencies | `certifi`, `charset-normalizer`, `idna`, `pyarrow`, `requests`, `urllib3`. The same six as the 2a release. No platform package. |

> Note: line 2 of `runtime-requirements.txt` is a comment. It records the random temporary directory that `uv export` used. So the check compares the requirement lines only, as the earlier release records do.

## Offline verification
> Note: the harness guard refuses any path inside a checkout, and the verifier children inherit the working directory. So the harness and the evidence directory were created under a temporary directory outside the checkout. The commands are those of plan 6 Task 5 Step 4, run from `/tmp/s2a1-task9-step4.sh` with `set -e` so that the run could go in the background.

The verifier ran on the 2a1 interpreter (`-I -B -X pycache_prefix=/dev/null`) with `UV_OFFLINE=1` for the harness step. Its output is below. The `evidence` path in it is the temporary directory. The evidence was copied afterward.

```json
{"exit": 0, "release_id": "f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18", "evidence": "/var/folders/3m/6f8zc0l14dn8yz2x8yy2_3mw0000gn/T/tmp.5f6cSgkd6a/evidence"}
```

`preflight_current` on the 2a1 interpreter printed `f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18`.

`report.json` shows `exit` 0, `release_id` equal to the ID above, `pythonpath_present` false, and `python` and `import_root` both inside the 2a1 release directory.

**Evidence directory:** `/Users/lowell/Projects/sec-edgar-local/fixture-data/s2a1-verify-evidence/` (git-ignored, because the temporary directory is not durable). `report.json` has SHA-256 `26db4e7b0b0a2e4736c6580fe33eebcd49603da520470e0c449f066c3641b518`. The run log is `fixture-data/stage2a1-verify.log` and the build log is `fixture-data/stage2a1-build.out` (both git-ignored).

## Retention
`releases/` holds these release directories:
- `sha256=49b7a2ed…`
- `sha256=900952a8…`
- `sha256=d718ae5f…`
- `sha256=fc68adef…`
- `sha256=aa8de1ac…`
- `sha256=9fa189a0…`
- `sha256=c4de77b8…` (1c)
- `sha256=e49d3ba8…` (2a)
- `sha256=f414caf8…` (2a1, new)

`releases/` also holds `artifact-cache` and `task14-guard-proofs`. The 2a release and all older releases are kept. The build added one release directory and removed none.

## Network
No SEC request was sent. Verification used fixture acquisition only.

## Statement
No SEC request was sent in this task. Nothing was written under `data/` or `backups/`. The 5,452 files of `data/` still match `specs/evidence/stage2a1/diagnosis/outputs/live-data-before.sha256` (`shasum -a 256 -c`: 5,452 OK, 0 not OK). The live config (`conf/sec-edgar-local.json`) still selects the 2a release. The selection moves in Task 12.

## Live-config selection
The statement above (the live config still selects the 2a release) was true when Task 9 ran. Task 12 changed it, on 2026-11-15, after the owner's approval (plan 9, Decision D11, "Approve selection").

The change in `conf/sec-edgar-local.json` is two values:
- `runtime.release_manifest` was `/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json`. It is now `/Users/lowell/Projects/sec-edgar-local/releases/sha256=f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18/release.json`.
- `execution.dispatch_reserve_seconds` was `1800`. It is now `1824`. This follows the member-wall stop rule (spec §6): the owner chose to raise the reserve under the Stage 1b rule (Decision D10, `walls.md`). The rule gives `1.25 × 1,074.9 s + 480 s = 1,823.7 s`, so 1,824 s is the least whole-second reserve that the measured wall allows. The cutoff is now 3,300 s − 1,824 s = 1,476 s after the run starts.

Offline preflight on the 2a1 interpreter (`releases/sha256=f414caf8…/venv/bin/python -I -B -X pycache_prefix=/dev/null`), with the plan 6 Task 7 command. The `sec.user_agent` value of the binding is elided here, because it holds the owner's contact address. It is unchanged from the config.

```
floor 480
reserve 1824
release f414caf89eaac416f8b6a27330773eb0d398cc5caedb881a37cf228379f7fa18
effective 74be83552796e73d20a78cf38cc297d4aac0b3962f875e4f1a5308a837851ba9
binding {'binding_version': 'sec-local-binding-v1', 'root': '/Users/lowell/Projects/sec-edgar-local/data', 'acquisition_mode': 'live', 'namespace': 'sec-owner-lowell-mason', 'sec': {'user_agent': '<elided>', 'requests_per_second': 3.0, 'max_active_collectors': 1}, 'coordination': {'lease_seconds': 60.0, 'renew_every_seconds': 20.0, 'namespace': 'sec-owner-lowell-mason', 'clock_uncertainty_seconds': 2.0}, 'storage_contract': 'sec-local-storage-v1'}
```

- **Effective-config SHA-256:** `74be83552796e73d20a78cf38cc297d4aac0b3962f875e4f1a5308a837851ba9`. Before the change it was `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733` (the 2a release, reserve 1,800 s).
- **Floor:** 480 s. **Reserve:** 1,824 s.
- **Binding:** it has no `execution` field, so the reserve change does not alter the store binding.
- `git diff` showed those two changed values and no other change. No launcher command was run.

The approval authorizes no SEC traffic.

**Selection commit:** `818066b6ca596dbe292627bf285f293f190ff073` (`chore(config): select the 2a1 release`).

No SEC request was sent in this stage.
