# Remove the Parked sec-edgar-ingest Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the parked `sec-edgar-ingest` engine and its support files from `main`, under an annotated tag that holds their last state.

**Architecture:** Tag `origin/main` first and push the tag. Then remove the package from the uv workspace, give `SEC_USER_AGENT` a documented source at the tag, remove `conf/`, the engine scripts, `docs/runbooks/` and `.sdd/`, and point the old-engine backlog sections at the tag. Each task ends with a command check. There is no new code, so the checks replace red/green unit tests. A guard before and after the merge proves that the engine paths did not change on `main` after the tag.

**Tech Stack:** git (annotated tags), uv 0.13 workspace and `uv.lock`, POSIX sh, Python 3.14 (`python3 -I` one-liners only).

**Spec:** `specs/deferred_items.md`, section `tech-debt-triage — 2026-11-18`, item "Remove the parked `sec-edgar-ingest` engine from `main`" (tech-debt row 4). Its Done when: `main` holds no `sec-edgar-ingest` code, a tag marks the last commit that held it, and `scripts/check-sec-filing-data.sh` passes.

## Global Constraints

- Tag: `ingest-parked-2026-11-16`, annotated, pushed to `origin` once. Never move or delete it after the push.
- Keep all of `specs/`. The only edits there are the findings lines in Task 2 and the pointer lines in Task 4. Retired plans 10 and 11, ADR 0001 and `specs/evidence/` (whose scripts import `sec_edgar_ingest`) stay byte-unchanged.
- Keep the root `constraint-dependencies = ["pyarrow==25.0.1", "requests==2.34.2"]` byte-unchanged.
- Do not touch `data/`, `backups/` or anything under `filing-data/` in the main checkout. Also leave `releases/`, `logs/`, `fixture-data/`, `dist/` and `.venv/` there alone.
- Do not edit `.gitignore`. It hides those local folders. Never run `git clean` in the main checkout. Leave the ignored `.sdd/` ledgers (about 343 files) and `__pycache__/` folders that stay there after the fast-forward. Report them.
- No tracked line gains the User-Agent value or the contact address. Never print the value. Compare SHA-256 digests only.
- Remove files by explicit path. Never use a glob over `scripts/`, because a script that lands on `main` later must survive.
- Do not change `packages/sec-filing-data/`, `.github/` or `scripts/check-sec-filing-data.sh`.
- The check is `sh scripts/check-sec-filing-data.sh`. Expected: `Ran 327 tests` and `OK`. It is the same command that CI runs.

## Review Focus

1. Lock drift: `uv lock` re-resolves a transitive pin of `sec-filing-data` (certifi, charset-normalizer, idna, urllib3). Pinned by the export diff in Task 1, Step 5.
2. A different or leaked User-Agent: the new source gives a value that differs from the one Stages 1 and 2 sent, or a tracked file gains it. Pinned by the digest compare in Task 2, Step 4 and the `git grep` in Task 3, Step 3.
3. A file that landed on `main` after this plan is deleted, or a removed path is left behind. Pinned by the `git ls-files` check in Task 3, Step 2.
4. The tag does not hold the engine's last state, because `main` changed an engine path after the tag. Pinned by the merge gate below.
5. Local folders in the main checkout are exposed or deleted after the fast-forward. Pinned by the `git status` check in the merge gate's post-merge step.

## Decisions

- **D1** (owner, brief, 2026-11-18): remove the parked engine after Stage 2 (tech-debt triage, "Label now, delete after Stage 2 (Recommended)"). Stage 2 merged on 2026-11-18 (PR #7). Applied in: Tasks 1–4.

Defaults for the owner's plan review. Each becomes a D-line when the owner rules on it:

- **P1:** `SEC_USER_AGENT` comes from `git show ingest-parked-2026-11-16:conf/sec-edgar.json`, as README documents. The value stays byte-identical to Stages 1 and 2, out of the files on `main`, and readable from any worktree. Alternative: an export line in the owner's shell profile, outside the repo. Applied in: Task 2.
- **P2:** The tag goes on `origin/main` at the start of execution, before any removal commit. Docs-only PRs (for example a Stage 3 spec) can merge before the removal. The tag is then not literally the last commit that held the engine. It holds the engine's last state, which the merge gate proves. Alternative: tag `<merge>^1` after the merge. Cost: the PR's README command, item tick and retired plan name a tag that does not exist yet. Applied in: Task 1, merge gate.
- **P3:** Plan approval authorizes the tag push to the public `origin` in Task 1, Step 2. Applied in: Task 1.
- **P4:** The two findings files get one pointer sentence each. Retired plans 10 and 11 stay unchanged, because they record how those runs happened. Applied in: Task 2.
- **P5:** The root `dependencies` becomes `[]`. Every documented command already uses `--package sec-filing-data`. Applied in: Task 1.
- **P6:** The backlog gets one pointer under each of 7 old-engine section headings. No item text is rewritten, and no old-engine item is ticked or retired. Those dispositions stay with `/deferred`. Applied in: Task 4.

---

### Task 1: Tag the engine and take it out of the workspace

**Files:**
- Delete: `packages/sec-edgar-ingest/` (285 tracked files)
- Modify: `pyproject.toml`
- Modify: `uv.lock` (regenerated)

**Interfaces:**
- Produces: tag `ingest-parked-2026-11-16` on `origin`. Tasks 2 and 4 and the merge gate name it.

- [ ] **Step 1: Start from current `main` and save the export baseline**

```bash
git fetch origin && git rebase origin/main
uv export --package sec-filing-data --frozen --no-dev --no-emit-workspace > "$TMPDIR/plan12-export-before.txt"
```

Expected: `git rev-parse HEAD` equals `git rev-parse origin/main`, and the export has 124 lines. It names certifi 2026.7.22, charset-normalizer 3.5.2, idna 3.20, pyarrow 25.0.1, requests 2.34.2 and urllib3 2.8.0, each with hashes.

- [ ] **Step 2: Create and push the tag**

```bash
git tag -a ingest-parked-2026-11-16 -m "sec-edgar-ingest as parked on 2026-11-16: the last state of the engine, conf/, its scripts, docs/runbooks/ and .sdd/ on main (plan 12)" origin/main
git push origin refs/tags/ingest-parked-2026-11-16
```

Expected: `git ls-remote --tags origin refs/tags/ingest-parked-2026-11-16` prints one line. `git rev-parse ingest-parked-2026-11-16:packages/sec-edgar-ingest/pyproject.toml` prints `ac75782d29110eba679d947e00eb78c8182b4b76`.

- [ ] **Step 3: Remove the package and edit the root `pyproject.toml`**

Run `git rm -r -q packages/sec-edgar-ingest`. In `pyproject.toml`, change only these:
- `description` becomes `"SEC filing data workspace: sec-filing-data"`.
- `dependencies` becomes `[]`.
- The `[tool.uv.sources]` table goes.
- `members` becomes `["packages/sec-filing-data"]`.

Leave `[tool.uv]` byte-unchanged.

- [ ] **Step 4: Regenerate the lock**

Run: `uv lock`
Expected: `Removed sec-edgar-ingest v0.2.0`. `git diff --numstat uv.lock` shows `0	22	uv.lock`, so the diff only deletes lines. `grep -c sec-edgar-ingest uv.lock` prints `0`.

- [ ] **Step 5: Prove the live package's pins did not move**

```bash
uv export --package sec-filing-data --frozen --no-dev --no-emit-workspace | diff "$TMPDIR/plan12-export-before.txt" - && echo export-same
sed -n '/^constraints = \[/,/^\]/p' uv.lock
sh scripts/check-sec-filing-data.sh
```

Expected: `export-same`. The constraints block lists `pyarrow ==25.0.1` and `requests ==2.34.2` only. The check prints `Ran 327 tests` and `OK`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: remove the parked sec-edgar-ingest package from the workspace"
```

### Task 2: Give `SEC_USER_AGENT` a source at the tag

**Files:**
- Modify: `README.md` (intro, the `SEC_USER_AGENT` paragraph under `### Run`, the `## sec-edgar-ingest (parked)` section)
- Modify: `specs/sec-filing-data-stage-1-findings.md:17-18`
- Modify: `specs/sec-filing-data-stage-2-findings.md:22-23`

**Interfaces:**
- Consumes: tag `ingest-parked-2026-11-16` (Task 1).

- [ ] **Step 1: Prove the tag holds today's config file**

Run: `git rev-parse ingest-parked-2026-11-16:conf/sec-edgar.json HEAD:conf/sec-edgar.json`
Expected: two equal lines, `ca2c6f3eafaecadd4b699fcc45bb65b5c34c28dc`.

- [ ] **Step 2: Edit `README.md`**

- Replace the first paragraph and its two bullets with: "This repository is one uv workspace with one Python package, `sec-filing-data`. It makes plain tables from the SEC filings of one quarter, 2026Q3."
- In the `SEC_USER_AGENT` paragraph, replace "The live runs take the value from `sec.user_agent` in `conf/sec-edgar.json`." with "Live runs take the value from `sec.user_agent` in `conf/sec-edgar.json` at tag `ingest-parked-2026-11-16`, so the value stays out of the files on `main`. This command sets it in any checkout or worktree:". Follow it with a `bash` block that holds this line:

```bash
export SEC_USER_AGENT="$(git show ingest-parked-2026-11-16:conf/sec-edgar.json | python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"])')"
```

- Replace the whole `## sec-edgar-ingest (parked)` section, from its heading to the end of the file, with:

```markdown
## sec-edgar-ingest (removed)

The roadmap reset parked the older filing-index engine, `sec-edgar-ingest`, on 2026-11-16, and plan 12 removed it from `main`. Tag `ingest-parked-2026-11-16` holds its last state: `packages/sec-edgar-ingest/`, `conf/`, its scripts in `scripts/`, `docs/runbooks/` and `.sdd/`. To read a file, run `git show ingest-parked-2026-11-16:<path>`. Its specs, plans and evidence stay in `specs/`. Do not use its code or its store as an input to `sec-filing-data`.
```

- [ ] **Step 3: Add the pointer sentence to both findings files**

In each file, the User-Agent bullet ends "The value is not copied here." Append after it: " Plan 12 removed `conf/` from `main`. The file is at tag `ingest-parked-2026-11-16`." Keep the existing line wrap.

- [ ] **Step 4: Run the README command and compare digests**

```bash
sh -c "$(sed -n '/^export SEC_USER_AGENT=/p' README.md)"'; printf %s "$SEC_USER_AGENT" | shasum -a 256' > "$TMPDIR/plan12-ua-tag.txt"
python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"], end="")' < conf/sec-edgar.json | shasum -a 256 | diff "$TMPDIR/plan12-ua-tag.txt" - && echo ua-same
```

Expected: `ua-same`, and no User-Agent value in the output. The README command runs from this worktree, so it also proves that a worktree can read the tag.

- [ ] **Step 5: Commit**

```bash
git add README.md specs/sec-filing-data-stage-1-findings.md specs/sec-filing-data-stage-2-findings.md
git commit -m "docs: give SEC_USER_AGENT a source at the parked-engine tag"
```

### Task 3: Remove `conf/`, the engine scripts, `docs/runbooks/` and `.sdd/`

**Files:**
- Delete: `conf/` (5 files), `docs/runbooks/` (4 files), `.sdd/` (2 tracked files)
- Delete: `scripts/accept-sec-native.py`, `scripts/baseline-campaign.py`, `scripts/check-sec-edgar-ingest.sh`, `scripts/local-bootstrap.py`, `scripts/measure-d5-drain.py`, `scripts/prepare-native-release.py`, `scripts/sec-acceptance-child.py`, `scripts/sec-edgar`, `scripts/verify-native-release.py`, `scripts/verify-sec-native-adjudication.py`

- [ ] **Step 1: Remove the files**

Run `git rm -r -q conf docs/runbooks .sdd`. Then run `git rm -q` with the 10 script paths above, named one by one.

- [ ] **Step 2: Check what is left**

Run: `git ls-files packages/sec-edgar-ingest conf docs scripts .sdd`
Expected: `scripts/check-sec-filing-data.sh` only. A script that landed on `main` after this plan also stays. Name it in the PR.

- [ ] **Step 3: Check that no stale reference or value is left outside `specs/`**

```bash
git grep -n -e sec_edgar_ingest -e sec-edgar-ingest -e 'conf/' -e 'docs/runbooks' -- ':!specs' | grep -v ingest-parked-2026-11-16
git show ingest-parked-2026-11-16:conf/sec-edgar.json | python3 -I -c 'import json, sys; print(json.load(sys.stdin)["sec"]["user_agent"], end="")' > "$TMPDIR/plan12-ua"
git grep -q -F -f "$TMPDIR/plan12-ua" -- ':!specs'; echo "value-in-tree: $?"; rm "$TMPDIR/plan12-ua"
sh scripts/check-sec-filing-data.sh
```

Expected: the first command prints one line, `README.md:<n>:## sec-edgar-ingest (removed)`. Then `value-in-tree: 1`: before this plan, the engine package, `docs/runbooks/local-ingestion.md`, `scripts/accept-sec-native.py` and `scripts/measure-d5-drain.py` held the value too. The check prints `Ran 327 tests` and `OK`.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: remove the parked engine's config, scripts, runbooks and SDD records"
```

### Task 4: Point the old-engine backlog sections at the tag

**Files:**
- Modify: `specs/deferred_items.md`

- [ ] **Step 1: Add the pointer under each of the 7 old-engine headings**

The headings are `4-sec-filing-index-bounded-drain`, `5-sec-filing-index-per-member-cost`, `6-sec-filing-index-member-completion`, `2-sec-filing-index-ingestion-spec`, `9-sec-filing-index-pre-dispatch-cost`, `sec-filing-index-ingestion-roadmap` and `sec-filing-platform-roadmap`. Put these two lines directly under each heading line:

```markdown
Plan 12 removed the parked engine from `main`. The paths that these items name under `packages/sec-edgar-ingest/`,
`conf/`, `scripts/` (except `check-sec-filing-data.sh`), `docs/runbooks/` and `.sdd/` are at tag `ingest-parked-2026-11-16`.
```

- [ ] **Step 2: Check the pointers and the backlog counts**

```bash
grep -c 'are at tag `ingest-parked-2026-11-16`' specs/deferred_items.md
uv run ~/.claude/skills/writing-plans/scripts/deferred_stats.py | head -1
```

Expected: `7`. The stats line reads `46 open, 6 ever closed` as before, unless a later PR changed the backlog. The pointers alone change no count.

- [ ] **Step 3: Commit**

```bash
git add specs/deferred_items.md
git commit -m "docs(specs): point the old-engine deferred items at the parked-engine tag"
```

---

## Merge gate

The Plan Completion Protocol ticks row 4 with `→ done <date> (plan 12)` and retires this plan inside the PR.

**Before you enable auto-merge:**

```bash
git fetch origin
git diff --quiet ingest-parked-2026-11-16 origin/main -- packages/sec-edgar-ingest conf docs/runbooks .sdd scripts ':(exclude)scripts/check-sec-filing-data.sh' && echo engine-unchanged
```

Expected: `engine-unchanged`. Any other result means `main` changed an engine path after the tag. Stop and ask the owner. Never move the pushed tag.

**After the merge** (PR lifecycle step 2), get the merge commit with `gh pr view <n> --json mergeCommit -q .mergeCommit.oid`. Run the same `git diff` with `<merge>^1` in place of `origin/main`, and report its result. Then check the Done when on `origin/main`:
- `git ls-tree -r --name-only origin/main -- packages/sec-edgar-ingest conf docs .sdd scripts` prints `scripts/check-sec-filing-data.sh` only.
- `git ls-remote --tags origin refs/tags/ingest-parked-2026-11-16` prints one line.
- CI passed on the merge.
- In the main checkout after the fast-forward, `git status --porcelain` prints nothing, and `data/`, `backups/` and `filing-data/` are still present. Report the ignored leftovers (the `.sdd/` ledgers and the `__pycache__/` folders under the removed paths), and do not delete them.
