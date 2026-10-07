# Task 1 implementer report

Status: DONE (implementation complete; controller-owned Spec/Quality review is still pending).

Execution root: `/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar`

BASE: `09c649aad9c7049b1a58f641bb843917b6b61aa8`

Commit: `046f240f655b1c1398e56ff57f2cac850b9d9a5c` — `build: align the SEC ingest workspace and CLI`.

## Implemented boundary

The root retains name/version/author and Python >=3.14, removes the stale root script and build backend, and becomes a virtual uv coordinator (`package = false`) with exactly one workspace member/source/dependency: `sec-edgar-ingest`. The package retains its accepted uv_build backend range, exposes the console entry point, and pins the four acquisition dependencies and root's 20 accepted transitive constraints. The universal `uv.lock` was resolved from the registry instead of copying a Linux wheel-only requirements lock. It includes 20 acquisition distributions, the actual ingest package, and virtual root metadata (22 resolution records; 21 installed distributions).

Actual interfaces:

- `sec_edgar_ingest.__version__ = "0.1.0"`; the unused greeting API is removed as explicitly approved.
- `sec_edgar_ingest.cli.main(argv: Sequence[str] | None = None) -> int`. Empty arguments print argparse help and return 0. `--help` and `--version` follow argparse's standard `SystemExit(0)` behavior. Unknown commands exit 2.
- Installed `sec-edgar-ingest = sec_edgar_ingest.cli:main` entry point and `python -m sec_edgar_ingest` both provide help/version.
- READMEs state the current milestone honestly: `discover`/`collect` are unfinished and rejected; no acquisition implementation is claimed. Client/download scaffolds remain outside the workspace and runtime graph.
- The local roadmap is specifically ignored by the root `.gitignore`.

No requirement or interface deviation. No SEC request, Azure authentication/service operation, compute activity, parsing, publication, reconciliation, or scheduler work occurred.

## TDD and verification evidence

1. Before modifying production metadata/code, wrote the specified standalone workspace test. Ran the offline/no-project bootstrap with local CPython 3.14.0. **Observed RED**: `test_only_ingest_is_a_workspace_member ... FAIL`, `AssertionError: Lists differ`, with the deleted index-ingest/client/download members still present. `Ran 1 test`, `FAILED (failures=1)`, exit 1. This is the intended behavioral failure, rather than an editable-build error.
2. Added CLI/import/installed-metadata/process invocation tests before implementation. Retained additional RED: missing `sec_edgar_ingest`, absent console entry point, and the stale workspace membership. `Ran 6 tests`, `FAILED (failures=3, errors=6)`, exit 1. Imports are deferred into test methods so the standalone bootstrap can still discover the workspace test.
3. Implemented the minimum approved workspace and CLI boundary. `uv lock`, `uv sync --frozen`, and `uv build --all-packages` all exited 0. Built `dist/sec_edgar_ingest-0.1.0.tar.gz` and `dist/sec_edgar_ingest-0.1.0-py3-none-any.whl`.
4. **Observed GREEN**: focused workspace suite ran six tests, all passed. It verifies membership/script boundary, no-argument help and return value, help/version exit behavior, rejection of unfinished commands, installed distribution version/dependencies/entry-point resolution, and real console/module subprocess invocations. Four subprocess subcases cover both invocation forms with both options.
5. In-scope refactor/self-review checkpoint: reviewed the full owned diff, public behavior, lock membership and installed distribution contract. No additional extraction/tidying was warranted for the cohesive 11-line CLI, so the production source was retained unchanged. Re-ran the complete `test_*.py` suite after that checkpoint: **6/6 PASS**, `Ran 6 tests in 0.092s`, `OK`, exit 0, with no warnings or stray output. No adjacent cleanup was applied.
6. Direct import/version, console help, and module version commands each exited 0. Help begins `usage: sec-edgar-ingest [-h] [--version]`; version is exactly `0.1.0`.
7. Resolution inspection exited 0, verifies all installed acquisition versions, exact graph membership, local archive hashes against `uv.lock`, and every packaged file (except the installer-rewritten RECORD) against installed contents. `git diff --check` and staged diff check both exited 0.

Exact commands and complete logs (each command ran from the execution root):

- `bootstrap-red`: `uv run --no-project --offline --python 3.14 python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_workspace.py -v`; exit 1. Exact cwd/argv/exit and full output: `task1-evidence/bootstrap-red.command.json`, `task1-evidence/bootstrap-red.stdout.txt`, `task1-evidence/bootstrap-red.stderr.txt`.
- `cli-red`: `uv run --no-project --offline --python 3.14 python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_workspace.py -v`; exit 1. Exact cwd/argv/exit and full output: `task1-evidence/cli-red.command.json`, `task1-evidence/cli-red.stdout.txt`, `task1-evidence/cli-red.stderr.txt`.
- `uv-lock`: `uv lock`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/uv-lock.command.json`, `task1-evidence/uv-lock.stdout.txt`, `task1-evidence/uv-lock.stderr.txt`.
- `uv-sync`: `uv sync --frozen`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/uv-sync.command.json`, `task1-evidence/uv-sync.stdout.txt`, `task1-evidence/uv-sync.stderr.txt`.
- `uv-build`: `uv build --all-packages`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/uv-build.command.json`, `task1-evidence/uv-build.stdout.txt`, `task1-evidence/uv-build.stderr.txt`.
- `workspace-green`: `uv run --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p test_workspace.py -v`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/workspace-green.command.json`, `task1-evidence/workspace-green.stdout.txt`, `task1-evidence/workspace-green.stderr.txt`.
- `import-version`: `uv run --frozen --package sec-edgar-ingest python -c 'import sec_edgar_ingest; print(sec_edgar_ingest.__version__)'`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/import-version.command.json`, `task1-evidence/import-version.stdout.txt`, `task1-evidence/import-version.stderr.txt`.
- `console-help`: `uv run --frozen --package sec-edgar-ingest sec-edgar-ingest --help`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/console-help.command.json`, `task1-evidence/console-help.stdout.txt`, `task1-evidence/console-help.stderr.txt`.
- `module-version`: `uv run --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/module-version.command.json`, `task1-evidence/module-version.stdout.txt`, `task1-evidence/module-version.stderr.txt`.
- `resolution-inspection`: `uv run --frozen --package sec-edgar-ingest python /Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar/.sdd/2-sec-filing-index-ingestion-stage-2-spec/task1-evidence/inspect_resolution.py`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/resolution-inspection.command.json`, `task1-evidence/resolution-inspection.stdout.txt`, `task1-evidence/resolution-inspection.stderr.txt`.
- `final-green`: `uv run --frozen --package sec-edgar-ingest python -m unittest discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/final-green.command.json`, `task1-evidence/final-green.stdout.txt`, `task1-evidence/final-green.stderr.txt`.
- `diff-check`: `git diff --check`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/diff-check.command.json`, `task1-evidence/diff-check.stdout.txt`, `task1-evidence/diff-check.stderr.txt`.
- `git-add`: `git add -- pyproject.toml packages/sec-edgar-ingest/pyproject.toml packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py README.md packages/sec-edgar-ingest/README.md .gitignore uv.lock packages/sec-edgar-ingest/src/sec_edgar_ingest/__main__.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/__init__.py packages/sec-edgar-ingest/tests/test_workspace.py`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/git-add.command.json`, `task1-evidence/git-add.stdout.txt`, `task1-evidence/git-add.stderr.txt`.
- `git-staged-check`: `git diff --cached --check`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/git-staged-check.command.json`, `task1-evidence/git-staged-check.stdout.txt`, `task1-evidence/git-staged-check.stderr.txt`.
- `git-staged-paths`: `git diff --cached --name-only`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/git-staged-paths.command.json`, `task1-evidence/git-staged-paths.stdout.txt`, `task1-evidence/git-staged-paths.stderr.txt`.
- `git-commit`: `git commit -m 'build: align the SEC ingest workspace and CLI'`; exit 0. Exact cwd/argv/exit and full output: `task1-evidence/git-commit.command.json`, `task1-evidence/git-commit.stdout.txt`, `task1-evidence/git-commit.stderr.txt`.

## Resolution and platform evidence

Local interpreter: `3.14.0 (main, Oct 14 2025, 21:10:22) [Clang 20.1.4 ]`.

Platform: `macOS-26.6.2-arm64-arm-64bit-Mach-O`; machine: `arm64`.

Stage 1's 21-distribution lock contains PyArrow for later ETL, which is correctly absent here. The 20 acquisition distributions have **zero version differences**. Fourteen use the same universal wheel hashes as accepted Linux evidence; six native macOS artifacts have different hashes: cffi, charset-normalizer, cryptography, multidict, propcache, and yarl. This is an artifact/platform difference, with no pin substitution. Exact local and accepted SHA-256 values, artifact filenames, tags, and packaged-file comparison counts are in `task1-evidence/resolution-inspection.json`; independently downloaded registry wheel archives are retained under `task1-evidence/wheels/`. The inspecting script is `task1-evidence/inspect_resolution.py`.

| Distribution | Installed version | Installed wheel tags | Local vs accepted Linux SHA-256 |
|---|---|---|---|
| azure-core | 1.41.0 | py3-none-any | same |
| azure-data-tables | 12.7.0 | py3-none-any | same |
| azure-identity | 1.26.0 | py3-none-any | same |
| azure-storage-blob | 12.31.0 | py3-none-any | same |
| certifi | 2026.7.22 | py3-none-any | same |
| cffi | 2.1.1 | cp314-cp314-macosx_11_0_arm64 | different |
| charset-normalizer | 3.5.2 | cp314-cp314-macosx_10_15_universal2 | different |
| cryptography | 50.0.2 | cp311-abi3-macosx_11_0_arm64 | different |
| idna | 3.20 | py3-none-any | same |
| isodate | 0.7.2 | py3-none-any | same |
| msal | 1.39.0 | py3-none-any | same |
| msal-extensions | 1.3.1 | py3-none-any | same |
| multidict | 7.0.0 | cp314-cp314-macosx_11_0_arm64 | different |
| propcache | 0.5.4 | cp314-cp314-macosx_11_0_arm64 | different |
| pycparser | 3.0 | py3-none-any | same |
| pyjwt | 2.15.1 | py3-none-any | same |
| requests | 2.34.2 | py3-none-any | same |
| typing-extensions | 4.16.0 | py3-none-any | same |
| urllib3 | 2.8.0 | py3-none-any | same |
| yarl | 1.25.1 | cp314-cp314-macosx_11_0_arm64 | different |

Local package builds and imports provide no new container compatibility or worker-fit claim. The uv_build range was retained exactly; it is a build requirement rather than an acquisition runtime dependency.

## Preservation and commit scope

`task1-evidence/preservation-before.json` records BASE status and SHA-256 for all eight client/download scaffold files, roadmap, parent spec, Stage 2 spec, ADR and Stage 1 findings. `preservation-after.json` records verification immediately before staging, plus built artifact hashes. `preservation-post-commit.json` records the post-commit verification. For both the execution checkout and primary checkout, protected bytes equal the baseline, all four original index-ingest deletions remain absent and unstaged, and the Git index is empty after the commit. The roadmap remains present at SHA-256 `e4fdf810785daa3700a92c96b65e08f671f4afbdfe273eed6154dcd255a9cf02`; `git check-ignore` confirms the intended execution-checkout ignore rule. The primary checkout was only read.

Staged paths were compared as a set against the exact 11 named Task 1 paths before committing. Neither roadmap, parent documents, scaffold exclusions, deletion paths nor local evidence/reports were staged. Post-commit execution status contains only the four original unstaged deletions.

Changed/created files:

- `pyproject.toml`
- `packages/sec-edgar-ingest/pyproject.toml`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py`
- `README.md`
- `packages/sec-edgar-ingest/README.md`
- `.gitignore`
- `uv.lock`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/__main__.py`
- `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`
- `packages/sec-edgar-ingest/tests/__init__.py`
- `packages/sec-edgar-ingest/tests/test_workspace.py`

Review handoff: this report, `task-1-brief.md`, `shared-contracts.md`, and `task-1.diff` in the same `.sdd` directory. The diff was generated from the recorded BASE to the exact Task 1 commit, scoped to the named paths, never from `HEAD~1`. No reviewer was spawned by the implementer; the controller handles the fresh Spec/Quality review before Task 2.

## In-scope clean-code application

- Fixed: replaced the obsolete `hello()` greeting API with the approved package version boundary (G9/F4) — `packages/sec-edgar-ingest/src/sec_edgar_ingest/__init__.py:1`. This is part of the approved behavioral scaffold replacement, not an unrelated tidying.
- Fixed: gave the installed CLI a single cohesive argument/help/version responsibility (G30/G6) — `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py:7`.
- Fixed: used descriptive contract test names and variables (N1/N4) — `packages/sec-edgar-ingest/tests/test_workspace.py`.
- Fixed: added installed-entry-point and subprocess behavior checks where a source-only import could miss broken packaging (T1/T3) — `packages/sec-edgar-ingest/tests/test_workspace.py:62`.

## Before/after educational Insights

Before, the root advertised `sec-edgar:main` without an actual import package and selected a deleted member, so workspace setup was the wrong test bootstrap. After, `[tool.uv] package = false` makes the root coordinate one buildable package; the initial `--no-project --offline` test exposes configuration failures independently of editable packaging.

Before, the ingest package offered only `hello()`. After, a single `main(argv)` powers both the installed console entry point and module invocation; injecting `argv` lets tests verify argument semantics without changing global process arguments. Checking `importlib.metadata.distribution` and loading its console entry point proves that installation metadata matches the source API.

Before, the accepted Linux wheel lock was platform-specific evidence. After, the universal uv lock preserves the accepted versions while allowing macOS artifacts. A different native wheel hash therefore means a different platform artifact, not an implicit version upgrade; the per-file comparison ties downloaded wheel evidence back to what was actually installed.

## Self-review findings and concerns

No known implementation concern or unapproved scope deviation. Spec/Quality PASS remains a controller review gate; this report does not claim that review or Stage 7 acceptance has occurred.
