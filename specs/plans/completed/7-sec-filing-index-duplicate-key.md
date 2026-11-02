# Duplicate-Key Schema v2 and Its Release Implementation Plan

**Status: COMPLETE (2026-11-02)** — executed via subagent-driven-development; nothing deferred

**Approval:** Approved by the owner, 2026-10-31, with P1–P12 as proposed (D1 below), as committed at `b2033ce`. This plan authorizes no SEC request.

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 2a — on plan completion, tick the
> stage and re-validate later stages against what shipped.

Approval of this spec authorizes no SEC request, live run or campaign. Stage 2b's plan, written
against this release, and its owner gate stay the only route to live traffic on the new schema.

(The two paragraphs above are the spec's §9 Rollout note, copied verbatim.)

**Goal:** Ship a reviewed native release with row schema `sec-index-v2` and parser `sec-index-parser-v2`, on which an index source whose rows repeat a key only in form type or company name transforms and publishes, with every listed value kept.

**Architecture:** The work has four parts.

1. A version registry separates the versions a release can read (v1 and v2) from the version it writes (v2). `IndexRowV2` holds sorted `form_types` and `company_names` lists. One pure helper merges the rows of one key from one source.
2. The parser emits one-item-list v2 observations. The within-source check ignores the two lists. The full build, the incremental build (C5), the equivalence check (C6) and the full validator merge the lists over the observations of the one source that precedence selects. A v1 base is mapped with `upgrade_row`.
3. Every reader takes its row type from the generation's `schema_version`. v1 generations read back unchanged.
4. The release is built from clean `main`, all 35 duplicate-key sources are re-transformed on a scratch copy of the store, and the live config selects the release at an owner checkpoint.

Code lands on a feature branch in a worktree. It merges to `main` after the full gate, a whole-branch review and an owner checkpoint. The release, the scratch run, the selection and the amendments run on `main`.

**Tech Stack:** Python 3.14 (CPython 3.14.0, macOS arm64). PyArrow 25.0.1 Parquet. SQLite through `sqlite3`. Stdlib `unittest` under `packages/sec-edgar-ingest/tests/network_guard.py`. `uv` offline and locked. Installed releases under `releases/sha256=<id>/`.

**Spec:** [specs/sec-filing-index-duplicate-key.md](../../completed/sec-filing-index-duplicate-key.md) (Stage 2a, committed at `e99b184`; its status line reads "Draft for owner review"). Parent spec: [specs/sec-filing-index-ingestion-spec.md](../../sec-filing-index-ingestion-spec.md). Inputs: the [1c release evidence](../../evidence/stage1c/release.md), [plan 6](6-sec-filing-index-member-completion.md) (the release pattern), [plan 2](2-sec-filing-index-ingestion-spec.md), Handoff, and the [quarantine enumerations](../../evidence/baseline-campaign/quarantine/).

## Global Constraints

Copied from the spec. Every task's requirements include this section.

- Offline. No SEC request. Nothing is written under `data/` (spec §1, Exit). The live store first meets the release in Stage 2b.
- D1: the v2 key is `(cik, archive_path)`, unique per generation.
- D2: a v2 row has `form_types` and `company_names`, sorted lists of distinct non-empty strings with at least one item each. It has no scalar `form_type` or `company_name`. Every other v1 field keeps its v1 meaning and type.
- D3: rows of one key in one source may differ only in form type and company name. Any other difference refuses the whole source with `conflicting duplicate logical key`.
- D4: a catalog row merges values only from the observations of the one source that precedence selects. Values from different sources are never merged.
- D5: the same observations in any order, and across any batch boundary, give byte-identical rows.
- D6: a changed list is `updated`. Withdrawal rules are unchanged.
- D7: a v1 generation reads back exactly as today, as v1 rows. A v2 generation reads back as v2 rows. No reader converts one into the other.
- D8: a v2 candidate on a v1 base maps base rows with `upgrade_row`, which keeps their v1 `parser_version` and `schema_version`. A re-transformed key whose business fields match counts as `provenance_refreshed`. A retained (`unresolved_absence`) row keeps its v1 versions. The manifest's `schema_version` governs the file layout.
- D9: the release writes only v2 observations and generations. It still validates retained v1 objects.
- D10: the 1c release and older releases stay retained and installable. Selecting the 1c release for a store with v2 objects is unsupported.
- D11: the release continues 1c-origin pending work on a store the 1c release wrote.
- D12: the release's locked inputs carry no platform member (owner decision S2).
- Anti-goals (spec §2.3): no listed value is lost or shown as the "real" one; a non-list conflict still quarantines; no order, scan or batch dependence; no v1 generation becomes unreadable or changes; a dropped form type stays an update, never a gated withdrawal.
- Budget stop rule (spec §6): "If either measured full rebuild (2023Q1 or 2026Q3) exceeds 1,500 s, the Exit is not met. The stage stops before the release and asks the owner to choose one of two paths." The budget is the 3,300 s launcher default minus the 1,800 s reserve. This plan applies the stop before the live-config selection (Task 11), because the scratch run needs the installed release (P11).
- The 2026Q3 scratch candidate is never approved, not even on the copy (spec §6).
- Existing duplicate-quarantine tests are updated, not deleted (spec §5 item 10).
- Tests use stdlib `unittest` under `network_guard.py`. Write each test before its implementation.
- The full gate is `scripts/check-sec-edgar-ingest.sh`. The 1c gate took 4,305 s, so run it in the background.

Execution environment (planning facts, not spec text):

- Tasks 1–8 run on branch `stage2a-duplicate-key` in the worktree `/Users/lowell/Projects/sec-edgar-local/.claude/worktrees/stage2a-duplicate-key` (using-git-worktrees). Leave other worktrees alone. A worktree has no `releases/` or `data/`, so every test and gate command sets `SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache`.
- Tasks 9–12 run in the main checkout on `main`, after the Task 8 merge.
- Shadow venv, created once in "Before Task 1" Step 3 (plan 6 method):

  ```bash
  WT=/Users/lowell/Projects/sec-edgar-local/.claude/worktrees/stage2a-duplicate-key
  /Users/lowell/.local/share/uv/python/cpython-3.14.0-macos-aarch64-none/bin/python3.14 -m venv /tmp/s2a-venv
  printf '%s\n%s\n' "$WT/packages/sec-edgar-ingest/src" /Users/lowell/Projects/sec-edgar-local/.venv/lib/python3.14/site-packages > /tmp/s2a-venv/lib/python3.14/site-packages/s2a.pth
  /tmp/s2a-venv/bin/python -I -c "import sec_edgar_ingest, pyarrow; print(sec_edgar_ingest.__file__, pyarrow.__version__)"
  printf '%s\n' '#!/tmp/s2a-venv/bin/python' 'import sys' 'from sec_edgar_ingest.cli import main' 'sys.exit(main())' > /tmp/s2a-venv/bin/sec-edgar-ingest
  chmod +x /tmp/s2a-venv/bin/sec-edgar-ingest
  mkdir -p "$WT/releases" && ln -s /Users/lowell/Projects/sec-edgar-local/releases/artifact-cache "$WT/releases/artifact-cache"
  ```

  Expected: a path under `$WT/packages/sec-edgar-ingest/src`, and `25.0.1`.
- Test command, from the worktree root (`<target>` is a module, class or test):

  ```bash
  SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py <target> -v
  ```

## Review Focus

1. **The incremental path after the first v2 rebuild.** Stage 3's daily publishes take C5 and C6. A new daily source that lists a combined filing must give the same rows as a full rebuild, with both form types. Test: Task 5, `test_incremental_merges_a_combined_filing_like_the_full_rebuild`.
2. **A v2 generation holding v1-provenance rows (D8).** A reader must see list fields on every row, including retained rows whose version fields say v1, and the full validator must accept them. Test: Task 4, `test_retained_v1_row_reads_back_with_lists_and_v1_versions`.
3. **A key repeated 3 or more times, identical and differing rows mixed, across an 8,192-row batch boundary.** Output is one row with every value, byte-identical under any line order. Test: Task 3, `test_triple_repeat_across_batch_boundary_is_order_independent`.
4. **One process reading a v1 capture and a v2 capture of different quarters.** Each yields its own row type, and neither changes. Test: Task 4, `test_one_process_reads_v1_and_v2_quarters`.
5. **Rollback to a v1 generation, then a v2 rebuild with a retained absence.** The retained row keeps v1 versions and its absence change, and the gate stays `clear` in an open quarter. Test: Task 4, `test_rollback_to_v1_then_v2_rebuild_keeps_retained_absence`.

## Decisions

- **D1** (owner, plan review, 2026-10-31): plan 7 approved with P1–P12 as proposed, as committed at `b2033ce`. No plan-level or spec-level change. Owner's words: "Approve as proposed". Applied in: Before Task 1 Steps 1–2, and every task through P1–P12.
- **D2** (owner, Task 1 review, 2026-10-31): the two stale tests `test_config.py:43` and `test_collection.py:189-190` change `sec-index-v2` to `sec-index-v3` (P10 stop). Applied in: Task 1 fix round 1 (`a0673ab`).
- **D3** (owner, Task 6, 2026-11-01): each name-only conflict fixture gets a repeated row that differs in filing date (`simple_pack`, `quarter_pack`, `conflicting_bytes`, `poisoned()`, then `test_reconcile_workflow:84` and `test_baseline_campaign:231/274/288`). No assertion changes (P10 stop). Applied in: Task 6.
- **D4** (owner, Task 6, 2026-11-01): port all 46 v1-row-shape test entries to v2 with the same assertions (P10 stop). Applied in: Task 6.
- **D5** (owner, Task 6, 2026-11-01): bind each era test to its own release, with v1 configs and no assertion change. `ONE_C_REVISION` moves up from Task 7 (P8 stop). Applied in: Task 6 Step 4.
- **D6** (owner, Task 6, 2026-11-01): the `test_discovery.py:491` tamper becomes `sec-index-v1`. The `test_worksets.py:115` schema case becomes `sec-index-v3`, plus a new `sec-index-v1` case. No case is removed (P10 stop). Applied in: Task 6.
- **D7** (owner, Task 7, 2026-11-01): when `a_schema` is set, check the B producer on the current v2 generation and the 1c producer on its 1c base, keep the 1c observation bytes unchanged, and compare an operator rollback with the 1c generation's own v1 rows. The same-pair path does not change. About 10 lines in `workflow_proof.py`, outside Task 7's file list. Applied in: Task 7.
- **D8** (owner, Task 8, 2026-11-01): Codex second-opinion review of `c814119..` approved. It sends the diff and the files Codex reads to OpenAI. Applied in: Task 8 Step 4.
- **D9** (owner, Task 8, 2026-11-01): wrap the v1 transform of `ParserV2Tests.test_v1_form_or_name_repeat_still_refuses_the_source` in `v1_writable()`, keep the new `_validate_context` check, and change no assertion. Applied in: Task 8 fix wave (`557028c`).
- **D10** (owner, Task 8 Step 6, 2026-11-02): "Merge now", local only, no push. The worktree stays until Task 12 ends. Applied in: Task 8 Step 7.
- **D11** (owner, Task 8 Step 7, 2026-11-02): "Exit the worktree, I merge": the session left the worktree and merged from the main checkout. Applied in: Task 8 Step 7.
- **D12** (owner, Task 11 Step 3, 2026-11-02): "Approve selection" of the 2a release, effective-config SHA-256 `f2082322…`. It authorizes no SEC traffic and no live run. Applied in: Task 11 Step 4 (`4d1f806`).
- **D13** (owner, Task 12 Step 3, 2026-11-02): wording "Approve as written". Scope: also amend R3 and §4.5, and add no §6 L12 note. Applied in: Task 12 (`a8e2a75`).
- **D14** (owner, completion gate, 2026-11-02): confirm the final review's Declined-line rulings and defer no new item; keep hand fix `2c6d84a`; run Codex on `f2610ce..HEAD` and carry non-critical findings (it found none); change none of the 60 rulings. Applied in: plan completion.

## Defaults for owner review

Planning settled these points. Each is plan-level and is applied in the tasks as written. The owner approves or changes each at plan review.

- **P1 — Read versions and write versions are separate.** `models.KNOWN_SCHEMAS = ('sec-index-v1', 'sec-index-v2')` gates decoding and validation of stored records. `models.WRITABLE_SCHEMAS` gates new work (config, CLI, commands). Tasks 1–5 set `WRITABLE_SCHEMAS = frozenset(KNOWN_SCHEMAS)`, so every task's suite stays green while v2 is built beside v1. Task 6 narrows it to `frozenset({'sec-index-v2'})` and flips the defaults. That is the spec's "new work requires them". Applied in: Tasks 1 and 6.
- **P2 — Row type follows the schema, not the parser name.** `fixture-index-parser-v2` already means "a different fixture parser" (`tests/etl_proof.py:421`). So the parser emits `IndexRow` for `sec-index-v1` and `IndexRowV2` for `sec-index-v2`. Valid pairs: `sec-index-parser-v1` with v1 only, `sec-index-parser-v2` with v2 only, and each fixture parser with either. Applied in: Tasks 1 and 2.
- **P3 — One shared pure merge helper.** `contracts.merge_rows` is used by the full build, C5, C6 (through the full build's code) and the full validator. The equivalence module keeps C5 and C6 independent in their selection and resolution logic. Sharing a pure sorted-union helper adds no shared ranking logic. Direct unit tests pin the helper. Alternative: three separate unions, at the cost of three places to keep equal. Applied in: Tasks 1, 3 and 5.
- **P4 — Exact Arrow types.** A list column is `pa.list_(pa.field('item', pa.string(), nullable=False))`, non-nullable, written with `use_compliant_nested_type=False` like every other file. In the v2 change file, `before` and `after` are `pa.struct(canonical_schema('sec-index-v2'))`. Applied in: Task 1.
- **P5 — The package version stays `0.2.0`.** `uv.lock`, the three `pyproject.toml` files and the export requirement lines stay byte-identical to the 1c build inputs (revision `3af121a468fdd6b3ec7d8286d5cf619493992d49`). The release ID changes through the Git revision and the wheel. Alternative: bump to `0.3.0`, which changes `uv.lock`. Applied in: Tasks 8 and 9.
- **P6 — The scratch run uses a committed evidence script, not the CLI.** The deployment binding stores the resolved root (`storage/contracts.py:185`), and `LocalObjectStore` refuses a different binding (`storage/local.py:51`). So the CLI refuses a copy of `data/` at another path. The script opens the copy with its stored binding, as the 1c diagnosis scripts did (`specs/evidence/stage1c/diagnosis/scripts/diag2.py`). It calls the engine's low-level commands `etl.commands.run_transform` and `run_publish`, after `runtime.retain_manifest` as `cli.py:484` does. Applied in: Task 10.
- **P7 — Scripts with v1 hardcodes.** `scripts/accept-sec-native.py:501–502, 902` and `scripts/measure-d5-drain.py:171` write or check configs that the release must load, so they move to the current pair in Task 6 (`test_acceptance_selection` and `test_measure_cost` cover them). The edit changes the acceptance driver's bytes. Retained selections in `specs/evidence/local-port/` pin the driver's SHA-256. Their standard verify already refuses a changed driver, and `scripts/verify-sec-native-adjudication.py:33–49` verifies them through the archived originals in `harness-original/`, so the edit breaks no retained check. Alternative: leave the driver at v1, so it can no longer run on this release. `conf/stage2/*.json` are Stage 2 campaign records: they stay v1 and the Handoff says the new release refuses them. `scripts/baseline-campaign.py:176` only counts rows, so it needs no change. Applied in: Task 6, Handoff.
- **P8 — Old-release test configs pin v1.** Tests that run an older release (`test_release_1b`, `test_release_1c`, `test_release_origin`, `test_release_upgrade`, `test_workflow_installed_lock`, `workflow_proof.installed_upgrade_cases`) give the older interpreter a v1 config and the current one a v2 config. If a test needs more than that pin, stop and ask. Never weaken a test. Applied in: Tasks 6 and 7.
- **P9 — The 1c interpreter in gate tests.** `support_release.ONE_C_REVISION = '3af121a468fdd6b3ec7d8286d5cf619493992d49'` builds the 1c application with `origin_release`, as plan 6 P2 did for 1b. One extra evidence run uses the installed `c4de77b8…` through `SEC_LOCAL_1C_RELEASE`. Applied in: Tasks 7 and 8.
- **P10 — Stop rule for existing tests.** Only `test_etl_transform.py:66` and `test_workflow_processing.py:136` assert the old duplicate behavior (`grep`). If another existing test fails because of v2 semantics, stop and ask. Applied in: every code task.
- **P11 — Budget stop after the build.** The spec says the stage "stops before the release". The scratch run (Task 10) needs the installed release, so the build (Task 9) comes first, and the stop holds the live-config selection (Task 11). Cost: on the cost-fix path, the Task 9 release stays in `releases/` and is never selected. Applied in: Global Constraints, Tasks 9–11.
- **P12 — A test-only seam for v1 writes.** Tests that build a v1 base keep working after Task 6 through `support_etl.v1_writable()`, a context manager that patches `models.WRITABLE_SCHEMAS` to both versions. `require_writable_schema` reads the module global at call time for this reason. No `src` code uses the seam (Task 6 checks it). Alternative: build each v1 base with the 1c interpreter, which costs a release build per test class. Applied in: Tasks 1 and 6.

## Facts established while planning (read-only, 2026-10-31)

- **F1 — Every version check, by `file:line`.** Each must move to `KNOWN_SCHEMAS` (read) or `WRITABLE_SCHEMAS` (write):

  | Site | Today | Becomes |
  |---|---|---|
  | `models.py:19, 340` (`RunContext`) | `== SCHEMA_VERSION` | known. Stored v1 contexts in snapshot and transformed worksets and Attempts must decode (D11). |
  | `etl/contracts.py:47` (`_record`, every record with `parser_version`) | `== SCHEMA_VERSION` | known |
  | `etl/parser.py:14–16, 27–35` | one parser, one schema | P2 pairs |
  | `config.py:173` | `== SCHEMA_VERSION` | writable |
  | `config.py:251–252` (live policy) | parser `== 'sec-index-parser-v1'` | parser pairs with the writable schema |
  | `cli.py:26, 130, 392` | `== SCHEMA_VERSION` | writable |
  | `etl/commands.py:18, 218` | `== SCHEMA_VERSION` | writable |
  | `workflows/contracts.py:55, 104` (`MemberResult`) | `== 'sec-index-v1'`, parser set without v2 | known schemas, parser set with `sec-index-parser-v2`. Retained v1 member results must validate. |
- **F2 — Row constructors to route through one version-aware decoder** (`grep -n "IndexRow(\*\*\|IndexRow.from_mapping"`): `etl/transform.py:84`, `etl/columnar.py:94`, `etl/catalog.py:158`, `etl/manifest.py:157`, `etl/equivalence.py:61`, `etl/incremental.py:136`, `etl/reader.py:76–78`, `etl/history.py:75`, `etl/contracts.py:453` (`arrow_row`). Schema calls: `canonical_schema()`, `observation_schema()`, `change_schema()` at 34 sites in `src`. Giving the schema functions a required `layout` argument makes `grep` and the tests find every site.
- **F3 — The full validator assumes one observation per row.** `etl/manifest.py:248` (`allowed` holds single observation payloads), `:254` (`winners` keeps the first ranked observation), `:269–272` (an output row must equal one), `:261` (base rows decoded as v1), and the field tuples at `:299` and `:345`. A merged row fails each one.
- **F4 — The merge points.** `catalog._load_observations` (`catalog.py:142–148`, reused by C6 at `equivalence.py:57`), `incremental._best` and `_resolve_touched` (`incremental.py:56–104`), and `manifest._validate_row_origins` (`:254`).
- **F5 — The incremental path needs equal versions** (`incremental.py:36`), and `build_candidate` re-transforms a selected source whose versions differ (`catalog.py:306–308`). So the first v2 publish of a quarter is a full rebuild (spec §4.3).
- **F6 — The upgrade proof shares one config.** `workflow_proof.installed_upgrade_cases` (`:556–600`) builds one `base` settings with `fixture-index-parser-v1` and only swaps `runtime.release_manifest` per release (`:593–597`). `workflow_proof.py:130` expects `schema_version` `'sec-index-v1'` in its guards.
- **F7 — Fixture configs.** `tests/fixtures/config/local.json` (`FIXTURE_CONFIG`, `tests/support.py:19`) and `conf/sec-edgar-local-fixture.json` set `sec-index-v1`. Live-parser test overrides set `'sec-index-parser-v1'` at `test_config.py:84, 255`, `test_download.py:995`, `test_local_launcher.py:52, 414`, `test_local_modes.py:25, 88, 137`, `test_workflow_cli.py:54`, `test_local_config.py:37`, `test_acceptance_selection.py:274, 395`.
- **F8 — Gate baseline.** The 1c gate ran 1125 tests in 73 modules (`specs/evidence/stage1c/gate.md:7`). The branch tip held 1128. `main` has changed only `specs/` since.
- **F9 — The 35 sources.** The 28 quarterly raw objects are named in the first line of each `specs/evidence/baseline-campaign/quarantine/<quarter>.txt`, with their repeated keys and line numbers below it. The 7 daily sources are 2026-07-08, 07-13, 07-22, 07-27, 09-17, 09-24 and 10-21 (plan 2, Handoff, trap (c)), in `final/coverage.json` `daily_sources`.
- **F10 — The store.** `data/` holds about 1.0 GB. The live config selects `c4de77b8…` with effective-config SHA-256 `fb93b0e8e05dbc1cbc9bd167ae02ef2d775629905c15938055a6a93c5fb95e96`, reserve 1800 s, floor 480 s.
- **F11 — Runbooks** `docs/runbooks/local-ingestion.md` and `docs/runbooks/release-upgrades.md` exist.

## File structure

| File | Responsibility | Tasks |
|---|---|---|
| `src/sec_edgar_ingest/models.py` | `SCHEMA_V1`, `SCHEMA_V2`, `KNOWN_SCHEMAS`, `WRITABLE_SCHEMAS`, `SCHEMA_VERSION`, `require_known_schema`, `require_writable_schema` | 1, 6 |
| `src/sec_edgar_ingest/etl/contracts.py` | `IndexRowV2`, `Row`, `row_type`, `decode_row`, `upgrade_row`, `merge_rows`, `conflict_payload`, layout-taking schema functions, `business_fields`, `update_fields`, `arrow_row` | 1 |
| `src/sec_edgar_ingest/etl/parser.py` | v2 emission, P2 pairs | 2, 6 |
| `src/sec_edgar_ingest/etl/transform.py`, `etl/columnar.py` | D3 check, per-version observation reads | 2 |
| `src/sec_edgar_ingest/etl/catalog.py`, `etl/manifest.py` | merge, upgrade of a v1 base, v2 resolve, version-aware validation | 3 |
| `src/sec_edgar_ingest/etl/reader.py`, `etl/history.py`, `etl/rollback.py`, `etl/approval.py` | per-generation row types | 4 |
| `src/sec_edgar_ingest/etl/incremental.py`, `etl/equivalence.py` | merge in C5, v2 in C6 | 5 |
| `src/sec_edgar_ingest/config.py`, `cli.py`, `etl/commands.py`, `workflows/contracts.py` | writable and known checks | 1, 6 |
| `tests/test_etl_schema_v2.py` (new) | Tasks 1–5 unit and catalog tests | 1–5 |
| `tests/test_release_2a.py` (new) | D10, D11 (spec §5 item 9) | 7 |
| `tests/support_release.py`, `tests/workflow_proof.py` | `ONE_C_REVISION`, per-release configs | 6, 7 |
| `tests/fixtures/config/local.json`, `conf/sec-edgar-local-fixture.json` | default schema v2 | 6 |
| `scripts/accept-sec-native.py`, `scripts/measure-d5-drain.py` | current pair (P7) | 6 |
| `specs/evidence/stage2a/` (new) | gate, review, release, scratch run, selection | 8–11 |
| `conf/sec-edgar-local.json` | release and versions | 11 |
| `specs/sec-filing-index-ingestion-spec.md`, `docs/runbooks/local-ingestion.md`, `docs/runbooks/release-upgrades.md` | spec §7 amendments | 12 |

All `src` and `tests` paths are under `packages/sec-edgar-ingest/`.

---

## Before Task 1

- [x] **Step 1: Plan review (HUMAN).** The owner reviews the plan and answers P1–P12. The spec's status line still reads "Draft for owner review": ask the owner to confirm that the spec is approved. Log each answer in `## Decisions`, in the owner's words. Apply each plan-level change, and re-run the writing-plans Self-Review on what changed. Record the approval on the plan's **Approval** line.
- [x] **Step 2: Commit the review on `main`.**

```bash
cd /Users/lowell/Projects/sec-edgar-local
git add specs/plans/7-sec-filing-index-duplicate-key.md
git commit -m "docs(plans): record the owner review of plan 7"
```

- [x] **Step 3: Create the worktree and the shadow venv.** Use the using-git-worktrees skill for branch `stage2a-duplicate-key` at `.claude/worktrees/stage2a-duplicate-key`. Then run the shadow-venv commands in Global Constraints.

---

### Task 1: Version registry and the v2 row contract (D1, D2, D8; P1–P4)

**Files:**
- Modify: `src/sec_edgar_ingest/models.py:19, 340`
- Modify: `src/sec_edgar_ingest/etl/contracts.py` (`_record` `:47`, new row type and helpers, schema functions `:404–423`, `BUSINESS_FIELDS` and `arrow_row` `:446–453`)
- Modify: `src/sec_edgar_ingest/config.py:173`, `cli.py:130, 392`, `etl/commands.py:218`, `workflows/contracts.py:55, 104`
- Modify: every caller of the schema functions and `BUSINESS_FIELDS` (F2), passing today's layout `SCHEMA_V1`, so behavior does not change in this task
- Modify: `tests/support_etl.py`, `tests/support_catalog.py`, `tests/support_incremental.py`, `tests/etl_proof.py:353`
- Create: `tests/test_etl_schema_v2.py`

**Interfaces:**
- Produces, in `models.py`:
  - `SCHEMA_V1 = 'sec-index-v1'`, `SCHEMA_V2 = 'sec-index-v2'`, `KNOWN_SCHEMAS = (SCHEMA_V1, SCHEMA_V2)`, `WRITABLE_SCHEMAS = frozenset(KNOWN_SCHEMAS)` (narrowed in Task 6), `SCHEMA_VERSION = SCHEMA_V1` (the default for new work; `SCHEMA_V2` from Task 6).
  - `require_known_schema(version: str) -> None` and `require_writable_schema(version: str) -> None`. Both raise `ValueError('unsupported schema_version')`. `require_writable_schema` reads `models.WRITABLE_SCHEMAS` at call time (P12).
- Produces, in `etl/parser.py`: `parser.SCHEMA_VERSION` is deleted. `cli.py:26`, `etl/commands.py:18` and `tests/etl_proof.py:353` use `models.SCHEMA_VERSION`, so one constant names the default schema.
- Produces, in tests: `support_etl.v1_writable()` (P12); a `schema_version: str | None = None` keyword on `support_etl.etl_context`, `support_catalog.Lane` and `support_incremental.Twin`, where `None` means the fixture config's value. Tasks 2–5 pass `'sec-index-v2'`. Tests that build a v1 base pass `'sec-index-v1'` inside `v1_writable()`.
- Produces, in `etl/contracts.py`:
  - `class IndexRowV2(Record)` with fields, in order: `cik: str`, `company_names: tuple[str, ...]`, `form_types: tuple[str, ...]`, `archive_path: str`, `filing_date: date`, `accession_number: str | None`, `source_id: str`, `source_sha256: str`, `parser_version: str`, `schema_version: str`. It applies every `IndexRow` field check. Each list must be a nonempty tuple of distinct, non-empty strings in sorted order (`ValueError('<field> must be sorted distinct non-empty strings')`). Its `schema_version` may be v1 or v2 (D8).
  - `Row = IndexRow | IndexRowV2`. `Observation.row` becomes `Row`.
  - `row_type(layout: str) -> type[Row]`: `IndexRow` for v1, `IndexRowV2` for v2.
  - `decode_row(value: Mapping[str, object], layout: str) -> Row`: from an Arrow `to_pylist` mapping (a `date`) or a canonical JSON mapping (an ISO string). This replaces each `IndexRow(**value)` and `IndexRow.from_mapping` site in F2 (Tasks 2–5 switch them).
  - `upgrade_row(row: IndexRow) -> IndexRowV2`: one-item lists, every other field unchanged, versions included.
  - `merge_rows(rows: Iterable[Row]) -> Row`: refuses an empty input and mixed types. For `IndexRow`, every row must be equal, and it returns that row. For `IndexRowV2`, every row must have equal `conflict_payload`, and it returns the row with the sorted distinct union of each list. Otherwise `ValueError('rows differ outside form types and company names')`.
  - `conflict_payload(row: Row) -> bytes`: `canonical_json` of the row mapping without `form_types` and `company_names`. For an `IndexRow` it is the whole mapping.
  - `canonical_schema(layout: str)`, `observation_schema(layout: str)`, `change_schema(layout: str) -> pa.Schema`, with no default. The v1 schemas are byte-identical to today's. The v2 data schema replaces `company_name` and `form_type` by `company_names` and `form_types` at the same positions, with the P4 list type.
  - `business_fields(layout: str) -> tuple[str, ...]` replaces `BUSINESS_FIELDS`. v2: `('cik', 'company_names', 'form_types', 'archive_path', 'filing_date', 'accession_number')`.
  - `update_fields(layout: str) -> tuple[str, ...]`: business fields without the key. It replaces the tuples at `manifest.py:299, 345`.
  - `arrow_row(value: Mapping[str, object], layout: str) -> dict[str, object]`.

- [x] **Step 1: Write the failing tests** in `tests/test_etl_schema_v2.py`, class `RowContractTests`:
  - `test_v2_row_requires_sorted_distinct_nonempty_lists`: `('SC TO-T', 'SC 13E3')`, `('SC 13E3', 'SC 13E3')`, `()` and `('',)` each raise `ValueError`. `('SC 13E3', 'SC TO-T')` is accepted.
  - `test_v2_row_accepts_v1_versions`: an `IndexRowV2` with `'sec-index-parser-v1'` and `'sec-index-v1'` constructs (D8).
  - `test_unknown_schema_is_refused`: `IndexRowV2`, `IndexRow` and `RunContext` with `schema_version='sec-index-v3'` raise `ValueError`. An `IndexRow` with `'sec-index-v2'` raises too: a v1 row is only ever v1.
  - `test_upgrade_row_keeps_every_field_and_version`: the NGM row from spec §4.2 with form `SC 13E3` upgrades to `form_types == ('SC 13E3',)`, `company_names == ('NGM BIOPHARMACEUTICALS INC',)`, and equal `cik`, `archive_path`, `filing_date`, `accession_number`, `source_id`, `source_sha256`, `parser_version`, `schema_version`.
  - `test_merge_rows_unions_both_lists_in_any_order`: the two NGM rows (`SC TO-T`, `SC 13E3`) merge to `('SC 13E3', 'SC TO-T')` in both input orders, with byte-equal `canonical_json(row.to_mapping())`. A rename pair (`'9 METERS BIOPHARMA, INC.'`, `'INNOVATE BIOPHARMACEUTICALS, INC.'`) merges into both names. A pair that differs in both lists merges both (spec §4.4 item 2).
  - `test_merge_rows_refuses_other_differences`: rows that differ in `filing_date` raise `ValueError('rows differ outside form types and company names')`. Two unequal `IndexRow` rows raise too. An empty input and a mix of `IndexRow` and `IndexRowV2` raise.
  - `test_v1_schemas_are_unchanged`: `canonical_schema(SCHEMA_V1)`, `observation_schema(SCHEMA_V1)` and `change_schema(SCHEMA_V1)` equal the schemas built by today's code. Copy today's three functions into the test as the oracle.
  - `test_v2_schemas_round_trip_through_parquet`: a v2 data table and a v2 change table (lists inside `before` and `after`) written with the catalog writer settings (`version='2.6'`, `compression='snappy'`, `use_dictionary=False`, `use_compliant_nested_type=False`) read back with `schema_arrow.equals(schema, check_metadata=True)` true.
  - `test_business_and_update_fields`: exact tuples for both layouts.
  - `test_v1_member_result_still_validates`: a `MemberResult` with `'sec-index-v1'` validates, and one with `'sec-index-parser-v2'` and `'sec-index-v2'` validates.
- [x] **Step 2: Run the module and confirm it fails** with `ImportError` on `IndexRowV2`.
- [x] **Step 3: Implement the Interfaces above.** Switch the F1 read sites to `require_known_schema` and the write sites (`config.py:173`, `cli.py:130, 392`, `commands.py:218`) to `require_writable_schema`. Add `'sec-index-parser-v2'` to `workflows/contracts.SUPPORTED_PARSERS`. Pass `SCHEMA_V1` at every existing schema-function and `business_fields` call site for now. Tasks 2–5 make each site version-aware.
- [x] **Step 4: Run** `test_etl_schema_v2`, then `test_etl_contracts test_etl_parser test_etl_transform test_etl_catalog test_workflow_contracts test_config`. Expected: all `OK`.
- [x] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src packages/sec-edgar-ingest/tests/test_etl_schema_v2.py
git commit -m "feat(etl): add the sec-index-v2 row contract and version registry"
```

> Deviation: the commit staged `packages/sec-edgar-ingest/src` and `packages/sec-edgar-ingest/tests`, because the Files list also edits `tests/support_*.py` and `etl_proof.py`. Fix round 1 (`a0673ab`) re-raised each write site's original error text, and changed two stale `sec-index-v2` test values to `sec-index-v3` (D2).

---

### Task 2: Parser v2 and the within-source rule (D3; spec §5 items 2 and 10)

**Files:**
- Modify: `src/sec_edgar_ingest/etl/parser.py`, `etl/transform.py:72–95, 184–207`, `etl/columnar.py:44–94`
- Modify: `tests/test_etl_transform.py:66` (update, not delete)
- Test: `tests/test_etl_schema_v2.py`, class `ParserV2Tests`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `parser.PARSER_V1 = 'sec-index-parser-v1'`, `parser.PARSER_V2 = 'sec-index-parser-v2'`.
  - `parser.supported_parser(version: str, *, fixture: bool) -> None` accepts `PARSER_V1`, `PARSER_V2` and, with `fixture`, `FIXTURE_PARSERS`.
  - `parser.supported_pair(parser_version: str, schema_version: str, *, fixture: bool) -> None`: P2 pairs. It raises `ValueError('parser and schema versions do not pair')`.
  - `parse_fields(...)` and `iter_observations(...)` keep their signatures. With `schema_version='sec-index-v2'` the observation's row is an `IndexRowV2` with one-item lists. Field rules do not change.
  - `transform._remember_observation(db, obs)` compares `conflict_payload(obs.row)`.
  - `columnar.quarter_observations` and `transform.read_observations` decode with `ref.schema_version` and `observation_schema(ref.schema_version)`.

- [x] **Step 1: Write the failing tests** in class `ParserV2Tests`. Build daily and quarterly bodies with the existing fixture helpers in `support_etl.py` and `support_workflows.idx`.
  - `test_v2_observation_has_one_item_lists`: one quarterly line parses to `form_types == ('SC 13E3',)` and keeps `original_fields` and `line_number`.
  - `test_v1_path_still_emits_v1_rows`: the same line with `schema_version='sec-index-v1'` gives an `IndexRow` equal to today's.
  - `test_pairs`: `supported_pair('sec-index-parser-v2', 'sec-index-v1', fixture=False)` and `('sec-index-parser-v1', 'sec-index-v2', ...)` raise. Each fixture parser pairs with both schemas when `fixture=True`.
  - `test_combined_filing_transforms_in_both_families` (spec §5 item 1): a quarterly and a daily source, each with the NGM key under `SC TO-T` and `SC 13E3`, transform with v2. The observation ref has `source_row_count` 2 for that key, `distinct_key_count` counting it once, and both observations kept with their own line numbers.
  - `test_company_rename_transforms_in_both_families` (spec §5 item 1): an `UPLOAD` accession `0000000000-26-000001` under two company names transforms in both families.
  - `test_filing_date_conflict_still_refuses_the_source` (spec §5 item 2): two rows of one key that differ in filing date fail with a `ParseError` whose `reason` is `'conflicting duplicate logical key'` and whose `line_number` is the second row's line. The retained failure record names that line and reason.
- [x] **Step 2: Update `test_etl_transform.py:66`** (spec §5 item 10). Keep the test. Rename it to say it covers a non-list conflict, make its two rows differ in filing date, and keep the `'conflicting duplicate'` assertion. Add beside it `test_form_or_name_repeat_now_transforms`, using the rows the old test used, asserting `result.complete` and no failure under a v2 context.
- [x] **Step 3: Run** `test_etl_schema_v2.ParserV2Tests test_etl_transform` and confirm the new tests fail.
- [x] **Step 4: Implement the Interfaces above.** `_parquet_observations` and `_verify_parquet` take the layout from the ref.
- [x] **Step 5: Run** `test_etl_schema_v2 test_etl_transform test_etl_parser test_etl_columnar test_etl_processes`. Expected: `OK`.
- [x] **Step 6: Commit.**

```bash
git add packages/sec-edgar-ingest/src packages/sec-edgar-ingest/tests
git commit -m "feat(etl): parse sec-index-v2 observations and refuse only non-list duplicate conflicts"
```

---

### Task 3: Merge and resolve in the full build and the full validator (D4–D6, D8; spec §5 items 1, 3, 4, 6, 7)

**Files:**
- Modify: `src/sec_edgar_ingest/etl/catalog.py` (`_load_observations` `:130–148`, `_load_active` `:151–159`, `_resolve` `:168–197`, `_write_parquet` `:200–225`)
- Modify: `src/sec_edgar_ingest/etl/manifest.py` (`iter_file_rows` `:137–153`, `_row` `:156–160`, `validate_files`, `_validate_row_origins` `:228–318`, `_validate_deltas` `:321–364`)
- Test: `tests/test_etl_schema_v2.py`, class `CatalogV2Tests`. Build stores with `support_catalog.py`.

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces:
  - `catalog._load_observations(db, selected, quarter, membership, objects, context, read=read_observations)`, signature unchanged. With the existing `ORDER BY`, the first row of a key names the winning `source_id`. The `proposed` row is `merge_rows` over that key's rows from that source only (D4). A v1 run gives today's rows.
  - `catalog._load_active(db, previous, objects, layout: str)`: base rows decoded with `previous.schema_version`, and mapped with `upgrade_row` when the base is v1 and `layout` is v2 (D8).
  - `catalog._resolve(db, mode, membership, layout: str)`: compares `business_fields(layout)`.
  - `manifest._row(value, quarter, layout: str) -> Row` and `manifest.iter_file_rows(ref, objects, layout: str)`.
  - `_validate_row_origins`: for each `(key, source)` it computes the merged row of that source's observations. An output row must equal the merged row of the top-ranked source for its key, or, for an `unresolved_absence` key, the exact base row as `_load_active` maps it. Its `winners` table holds merged rows.
  - `_validate_deltas` and the provenance-only check use `update_fields(manifest.schema_version)`.

- [x] **Step 1: Write the failing tests** in class `CatalogV2Tests`. Each builds candidates with `build_candidate` and checks them with `validate_candidate_content`.
  - `test_combined_filing_and_rename_publish_one_row_each` (spec §5 item 1): a quarterly source with the NGM pair and a rename pair gives two rows. The NGM row is `0001426332 | [NGM BIOPHARMACEUTICALS INC] | [SC 13E3, SC TO-T] | 2024-03-08 | edgar/data/1426332/0001140361-24-012376.txt`. The rename row lists both names. The manifest says `schema_version == 'sec-index-v2'`.
  - `test_permuted_lines_give_byte_identical_generations` (spec §5 item 3): the same rows in two line orders give equal `generation_id` and byte-equal data and change files.
  - `test_triple_repeat_across_batch_boundary_is_order_independent` (Review Focus 3): one key listed 3 times (two identical rows, one with another form type), with lines 8,190, 8,193 and 8,197 of a 9,000-row source, gives one row with 2 form types. A reversed body gives byte-identical files.
  - `test_merge_never_crosses_sources` (spec §5 item 4, §4.4 item 4): a daily source lists the NGM key under `SC 13E3` only, and a quarterly source of the same quarter under `SC TO-I` only. The row lists `('SC TO-I',)` and its `source_id` is the quarterly source.
  - `test_v2_candidate_on_v1_base_counts_provenance_refresh` (spec §5 item 6): a v1 generation, built by a v1 context, is the base of a v2 build of the same source plus one changed key. Unchanged keys count in `provenance_refreshed`, the changed key is one `updated` change, and `added` and `withdrawn` are 0.
  - `test_dropped_form_type_is_updated_with_clear_gate` (spec §5 item 7): a closed-quarter v2 base whose key lists 2 form types, then a newer quarterly snapshot listing 1. One `updated` change, `withdrawn == 0`, `gate == 'clear'`.
  - `test_validator_refuses_a_cross_source_merge`: hand-write a data file whose row unions the daily and quarterly form types of the previous test. `validate_candidate_content` raises `ValueError`.

> Deviation: the permuted-lines and reversed-body assertions cannot hold literally, because every row's `source_sha256` names its snapshot. The spec D5 tests reverse the observation order through the build's `read=` seam instead. The reviewer confirmed that they fail under a first-wins or a last-wins merge.

- [x] **Step 2: Run** `test_etl_schema_v2.CatalogV2Tests` and confirm the failures.
- [x] **Step 3: Implement the Interfaces above.** Every layout is `context.schema_version` on the build path and `manifest.schema_version` on the validation path.
- [x] **Step 4: Run** `test_etl_schema_v2 test_etl_catalog test_etl_publication test_etl_integrity test_full_check_budget`. Expected: `OK`.
- [x] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src packages/sec-edgar-ingest/tests
git commit -m "feat(etl): merge form types and company names within the selected source"
```

---

### Task 4: Readers, history, approval and rollback by generation version (D7, D8; spec §5 items 5 and 8)

**Files:**
- Modify: `src/sec_edgar_ingest/etl/reader.py:65–78`, `etl/history.py:75`, `etl/approval.py`, `etl/rollback.py` (each row decode)
- Test: `tests/test_etl_schema_v2.py`, class `ReaderV2Tests`

**Interfaces:**
- Consumes: Task 3.
- Produces: `reader.read_quarter(capture, objects) -> Iterator[Row]` yields `row_type(manifest.schema_version)` rows. `history.withdrawal_candidates` decodes `before` with the manifest's layout. Approval and rollback signatures do not change.

- [x] **Step 1: Write the failing tests** in class `ReaderV2Tests`.
  - `test_v1_generation_reads_back_byte_identically` (spec §5 item 5, D7): publish a v1 generation, record `canonical_json` of every `read_quarter` row and the manifest bytes, then switch to v2 code paths (a v2 publish of another quarter) and read the v1 capture again. Equal bytes, and every row is an `IndexRow`.
  - `test_v2_generation_reads_back_with_lists` (spec §5 item 5): every row is an `IndexRowV2`.
  - `test_retained_v1_row_reads_back_with_lists_and_v1_versions` (Review Focus 2): an open-quarter v1 base with a key that the v2 build's sources omit and that no membership authority lists. The v2 generation holds it as `unresolved_absence`. `read_quarter` gives an `IndexRowV2` with one-item lists and `schema_version == 'sec-index-v1'`. `validated_manifest` passes.
  - `test_one_process_reads_v1_and_v2_quarters` (Review Focus 4): one store with a v1 capture of 2026Q3 and a v2 capture of 2026Q4. Both read in one process, in both orders, with their own row types and unchanged bytes.
  - `test_rollback_from_v2_to_v1_then_v2_publish` (spec §5 item 8): a v1 generation, a v2 generation on it, `rollback` to the v1 generation, then a v2 publish. The pointer holds the new v2 generation, and its `base_generation_id` is the v1 generation.
  - `test_rollback_to_v1_then_v2_rebuild_keeps_retained_absence` (Review Focus 5): as above, with one base key absent from the new sources in an open quarter. The new generation has one `unresolved_absence` with v1 versions and `gate == 'clear'`.
  - `test_history_lists_v1_and_v2_generations`: `quarter_history` over the lineage of the previous test lists every generation with its counts.
- [x] **Step 2: Run and confirm the failures.**
- [x] **Step 3: Implement the Interfaces above.**
- [x] **Step 4: Run** `test_etl_schema_v2 test_etl_history test_history_cli test_etl_approval test_approval_activation test_etl_rollback`. Expected: `OK`.
- [x] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src packages/sec-edgar-ingest/tests
git commit -m "feat(etl): read each generation with its own row schema"
```

---

### Task 5: The incremental build (C5) and its equivalence check (C6) under v2 (Review Focus 1)

**Files:**
- Modify: `src/sec_edgar_ingest/etl/incremental.py:56–169`, `etl/equivalence.py`
- Test: `tests/test_etl_schema_v2.py`, class `IncrementalV2Tests`. Use `support_incremental.py`.

**Interfaces:**
- Consumes: Tasks 1–4. `merge_rows` (P3).
- Produces: `incremental._best(candidates: list[tuple[Rank, str, bytes]], layout: str) -> bytes`: the winning source is the highest rank, then the lowest `source_id`. It returns `merge_rows` over that source's candidates. `_resolve_touched` and `build_incremental` take `layout` from `context.schema_version`. `columnar.generation_table(ref, objects, layout: str)` checks the file against the schema of `layout`. `equivalence` decodes with `manifest.schema_version`. `incremental.eligible` does not change (F5).

- [x] **Step 1: Write the failing tests** in class `IncrementalV2Tests`.
  - `test_incremental_merges_a_combined_filing_like_the_full_rebuild` (Review Focus 1): a v2 open-quarter base, then a new daily source with a combined filing (two lines, two form types). Use `support_incremental.Twin` with v2 lanes. `Twin.build` returns an incremental call count of 1, the fast lane's data row lists both form types, and its data and change files are byte-equal to the full lane's. `validate_incremental_candidate` passes.
  - `test_incremental_rename_in_new_daily_source`: the same with a rename pair.
  - `test_incremental_does_not_merge_base_and_delta_sources`: the base daily source lists a key under `SC TO-T`, the new daily source with a later period lists it under `SC 13E3`. The new source wins by precedence, and the row lists `('SC 13E3',)` only.
- [x] **Step 2: Run and confirm the failures.**
- [x] **Step 3: Implement the Interfaces above.**

> Deviation: the Files list missed `catalog.py` `_incremental_candidate`, which still wrote v1 schemas. The dispatch widened the task to it and to every remaining `SCHEMA_V1` hard-code. Commit `fc0bbc2` added a test for an incremental build over a retained v1 row before the review.

- [x] **Step 4: Run** `test_etl_schema_v2 test_etl_incremental test_etl_equivalence test_etl_columnar`. Expected: `OK`.
- [x] **Step 5: Commit.**

```bash
git add packages/sec-edgar-ingest/src packages/sec-edgar-ingest/tests
git commit -m "feat(etl): merge within the winning source in the incremental build"
```

---

### Task 6: Make v2 the only version for new work (D9; spec §5 item 10; P1, P7, P8)

**Files:**
- Modify: `src/sec_edgar_ingest/models.py` (`WRITABLE_SCHEMAS = frozenset({SCHEMA_V2})`, `SCHEMA_VERSION = SCHEMA_V2`), `etl/parser.py` (`PARSER_VERSION = PARSER_V2`), `config.py:251–252`
- Modify: `tests/fixtures/config/local.json`, `conf/sec-edgar-local-fixture.json` (`schema_version` to `sec-index-v2`)
- Modify: the F7 live-parser test overrides (to `sec-index-parser-v2`), `tests/workflow_proof.py:130`, `tests/test_workflow_processing.py:136` (update, not delete), `scripts/accept-sec-native.py:501–502, 902`, `scripts/measure-d5-drain.py:171`
- Modify: `tests/workflow_proof.py:589–597` and old-release tests (P8)
- Test: `tests/test_etl_schema_v2.py`, class `WriteVersionTests`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: the release's write rule. `load_config` refuses `etl.schema_version` `'sec-index-v1'` with `'unsupported etl.schema_version'`. The live policy requires `etl.parser_version == 'sec-index-parser-v2'` and raises `'live acquisition requires sec-index-parser-v2'`. Every v1 read path from Tasks 1–5 stays.

- [x] **Step 1: Write the failing tests** in class `WriteVersionTests`:
  - `test_v1_config_is_refused_for_new_work`: a fixture config with `sec-index-v1` raises `ValueError('unsupported etl.schema_version')`.
  - `test_live_policy_requires_parser_v2`: a live config with `sec-index-parser-v1` raises with the new message.
  - `test_publish_refuses_a_v1_context`: `run_publish` with a v1 `RunContext` raises `ValueError('unsupported ETL schema version')`, and a stored v1 snapshot workset still decodes.
  - `test_v2_transform_of_a_v1_era_snapshot`: a snapshot workset written under a v1 context is transformed by a v2 context, and its observation ref has `schema_version == 'sec-index-v2'`.
- [x] **Step 2: Run and confirm the failures.**
- [x] **Step 3: Narrow the write versions and flip the fixture configs.** Wrap each Task 1–5 test that builds a v1 base in `support_etl.v1_writable()`. Then `grep -rn v1_writable packages/sec-edgar-ingest/src` must print nothing. Update `test_workflow_processing.py:136` as in Task 2 Step 2: keep the test with a filing-date conflict, and add a form-only repeat that now completes. Update the F7 overrides, `workflow_proof.py:130` and the P7 scripts to the current pair.

> Deviation: `Settings` validates both known schemas and either release parser, so that stored v1 and 1c contexts still decode (spec D11). A new `admit_new_work` gate in `parse_config` enforces the writable schema and `sec-index-parser-v2`. The owner ruled on three P10 stops (D3, D4, D6). The forged test files now use `use_compliant_nested_type=False`, like the production writers.

- [x] **Step 4: Pin v1 for older interpreters (P8).** `proof_releases` builds A and B from the current source, so `test_release_upgrade` keeps both on the current pair. Add a keyword to `workflow_proof.upgrade_sequence(output, a_manifest, b_manifest, *, a_schema: str | None = None)` and pass it to `installed_upgrade_cases`. When `a_schema` is given, `settings(release)` gives release A `etl.schema_version = a_schema`, and release B keeps the current pair. Apply the same pin wherever a test gives a config to an older interpreter, such as the 1b side of `test_release_1c`. If a test needs more than the pin, stop and ask (P8).

> Deviation: each era test binds to its own release (D5). `test_release_origin`, `test_release_1b` and `test_release_1c` run only their older releases as children, with v1 configs. `test_release_2a` and `test_release_upgrade` cover the new release. `ONE_C_REVISION` moved up from Task 7.

- [x] **Step 5: Run the ETL, workflow and release modules** (`test_etl_* test_workflow_* test_local_* test_config test_cli test_download test_acceptance_selection test_measure_cost test_release test_release_1b test_release_1c test_release_origin test_release_upgrade`), in the background. Expected: `OK`. Stop and ask under P10 for any other failure.
- [x] **Step 6: Commit.**

```bash
git add conf/sec-edgar-local-fixture.json packages/sec-edgar-ingest scripts/accept-sec-native.py scripts/measure-d5-drain.py
git commit -m "feat(etl): write only sec-index-v2 and keep v1 readable"
```

> Deviation: the review found that `scripts/accept-sec-native.py` `validate_read` refused the v1-versioned retained rows of a v2 generation (spec D8). Fix round 2 (`767787c`) checks the parser and schema as a pair. The older provenance check from `2b64551` still refuses a retained row whose snapshot was replaced.

---

### Task 7: Two-release continuation with the 1c release (D10, D11; spec §5 item 9; P9)

**Files:**
- Modify: `tests/support_release.py` (`ONE_C_REVISION`)
- Create: `tests/test_release_2a.py`

**Interfaces:**
- Consumes: Task 6. `support_release.origin_release(project, cache, revision)`, `support_release.proof_releases(project, cache)` (its second release is the current code, as `test_release_1c.py:42` uses it), and `workflow_proof.upgrade_sequence(output, a_manifest, b_manifest, *, a_schema='sec-index-v1')`.
- Produces: `ONE_C_REVISION = '3af121a468fdd6b3ec7d8286d5cf619493992d49'  # source revision of the 1c release c4de77b8…`. The env var `SEC_LOCAL_1C_RELEASE` replaces the built 1c release with an installed one.

- [x] **Step 1: Write the tests** in `tests/test_release_2a.py`, class `TwoReleaseTests`, with the 1c release from `origin_release(..., ONE_C_REVISION)` or `SEC_LOCAL_1C_RELEASE`, and the current release from `support_release.proof_releases`:
  - `test_1c_release_refuses_the_v2_config`: the 1c interpreter runs `load_config` on a v2 fixture config in a child process. It exits non-zero with `unsupported etl.schema_version` on stderr.
  - `test_v2_release_continues_1c_origin_pending_work`: `upgrade_sequence` with the 1c release as A and the current release as B. Assert the same report fields as `test_release_upgrade.py:131–200`: `exit == 0`, each case `b_exit == 0` and `rows > 0`. Also assert that the `pending` case's published generation has `schema_version == 'sec-index-v2'`.
  - `test_v2_reads_the_1c_generation_unchanged` (spec §5 item 5, "on the new release"): the reference read runs on the 1c interpreter in a child process. It prints `canonical_json` of every `read_quarter` row of the 1c-written generation. The current release then reads the same capture in another child process. The two outputs are byte-equal, and every current-release row is an `IndexRow`.
- [x] **Step 2: Run** `test_release_2a` in the background. Expected: `OK`. If continuation fails, stop and ask: D11 is a requirement, and the fix is not planned.
- [x] **Step 3: Commit.**

```bash
git add packages/sec-edgar-ingest/tests
git commit -m "test(release): prove continuation of 1c-origin work on the v2 release"
```

> Deviation: test 2 failed in the shared harness, because B re-transforms a v1 observation as v2 and the 1c producer sits one step down the lineage. With the owner's approval (D7), `workflow_proof.py`, outside the Files list, checks the producer on the right generation when `a_schema` is set. Fix round 1 (`f2610ce`) saves the 1c observation bytes before `continue-b`.

---

### Task 8: Full gate, evidence, whole-branch review and merge (HUMAN checkpoint)

**Files:**
- Create: `specs/evidence/stage2a/gate.md`

**Interfaces:**
- Consumes: the branch after Tasks 1–7.
- Produces: `main` holding the reviewed change.

- [x] **Step 1: Run the full gate in the background,** from the worktree root, as plan 6 Task 4 Step 1:

```bash
ln -s /Users/lowell/Projects/sec-edgar-local/.venv .venv
env -u PYTHONDONTWRITEBYTECODE UV_PROJECT_ENVIRONMENT=/tmp/s2a-venv UV_NO_SYNC=1 SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache sh scripts/check-sec-edgar-ingest.sh > /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a-gate.log 2>&1; echo "exit $?" >> /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a-gate.log
```

Expected: the log ends with `exit 0`, and unittest prints `OK`. The count is 1128 (F8) plus the new tests, in 75 modules (73 plus `test_etl_schema_v2` and `test_release_2a`). Record the exact count. Then `rm .venv`.

> Deviation: the worktree `.venv` linked to `/tmp/s2a-venv`, not to the main checkout's `.venv`. The gate ran twice: on `f2610ce` (1185 tests, OK) and, after the final review's fix wave changed `src`, on `557028c` (1187 tests, OK). `gate.md` names `557028c`.

- [x] **Step 2: Evidence run on the installed 1c release (P9).**

```bash
SEC_LOCAL_1C_RELEASE=/Users/lowell/Projects/sec-edgar-local/releases/sha256=c4de77b89bb1d8ecc5d094f0e1dc6f8a5f3a7935e3595a9dd086d1e41a6b8aa7/release.json SEC_LOCAL_PROOF_CACHE=/Users/lowell/Projects/sec-edgar-local/releases/artifact-cache /tmp/s2a-venv/bin/python packages/sec-edgar-ingest/tests/network_guard.py test_release_2a -v > /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a-installed-1c.log 2>&1; echo "exit $?" >> /Users/lowell/Projects/sec-edgar-local/fixture-data/stage2a-installed-1c.log
```

Expected: 3 tests, `OK`, `exit 0`.
- [x] **Step 3: Record the gate.** `gate.md` holds the branch, the gated commit, the command, the start and end times, the `Ran N tests in S s` line, `OK`, the module count, the Step 2 result, and a table mapping spec §5 items 1–10 and Review Focus 1–5 to their test names. Commit it: `docs(evidence): record the Stage 2a branch gate`.
- [x] **Step 4: Whole-branch review.** Use the requesting-code-review skill on `main..stage2a-duplicate-key`, against the spec, this plan and its Decisions. Name these focuses: the anti-goals of spec §2.3; the F1 table (every read site known, every write site writable); the three merge points (F4) and the validator (F3); D8 rows in every reader; the v1 byte identity. Fix each accepted finding with a test. If a fix changes `src`, re-run Step 1 and update `gate.md`. Record the review in `gate.md` under `## Review`: the reviewer, the commit range, each finding and its fix or ruling.

> Deviation: Codex reviewed `f2610ce` (D8). Both seats raised the library write boundary. Commits `88ea529` (test only) and `557028c` (the `_validate_context` check, with one test wrapped in `v1_writable()`, D9) closed both findings, and a scoped re-review accepted them.

- [x] **Step 5: Check locked inputs and the platform member (P5, D12).**

```bash
git -C /Users/lowell/Projects/sec-edgar-local show stage2a-duplicate-key:pyproject.toml | grep -n 'members'
git -C /Users/lowell/Projects/sec-edgar-local diff --stat 3af121a468fdd6b3ec7d8286d5cf619493992d49 stage2a-duplicate-key -- uv.lock pyproject.toml packages/sec-edgar-ingest/pyproject.toml
```

Expected: `members = ["packages/sec-edgar-ingest"]`, and no output from the second command.

> Deviation: the check ran from the worktree without `git -C`, because the harness refused a redirect to the main checkout. It is the same repository, with the same result.

- [x] **Step 6: Owner checkpoint (HUMAN).** Show `gate.md`, the review result and `git log --oneline main..stage2a-duplicate-key`. Ask for approval to merge. Stop until the owner answers. Log the answer as a Decision.
- [x] **Step 7: Merge** in the main checkout with plan 6 Task 4 Step 8's commands, branch `stage2a-duplicate-key`, message `merge: Stage 2a duplicate-key schema v2`. Both `git status --porcelain --untracked-files=all` calls print nothing. Keep the worktree until Task 12 ends.

> Deviation: the session left the worktree to merge in the main checkout (D10, D11). `git merge --ff-only` fast-forwarded `c814119..3286385`, so no merge commit exists and the planned message was not used.

---

### Task 9: Build and verify the release (spec §6 "Release"; D10, D12)

Run in the main checkout on `main`.

**Files:**
- Create: `specs/evidence/stage2a/release.md`

**Interfaces:**
- Produces: `releases/sha256=<2A>/`. Its ID, manifest path and `git_revision` feed Tasks 10–12 and the Handoff.

- [x] **Step 1: Confirm a clean tree** (`git status --porcelain --untracked-files=all` prints nothing) and record `git rev-parse HEAD`.
- [x] **Step 2: Build** with plan 6 Task 5 Step 2's command. Record `<2A>`.
- [x] **Step 3: Check identity, lock and export against the 1c inputs.** Run plan 6 Task 5 Step 3's commands with `C=releases/sha256=<2A>`, `B=releases/sha256=c4de77b89bb1d8ecc5d094f0e1dc6f8a5f3a7935e3595a9dd086d1e41a6b8aa7` and revision `3af121a468fdd6b3ec7d8286d5cf619493992d49`. Expected: `lock-identical`, `export-lines-identical`, `inputs-identical`, version `0.2.0` in both, the 2a `git_revision` equal to Step 1's revision, and equal dependency lists with no platform package.
- [x] **Step 4: Offline verification** with plan 6 Task 5 Step 4's commands on `releases/sha256=<2A>`. Copy the evidence to `fixture-data/s2a-verify-evidence`. Expected: verifier JSON with `"exit": 0` and `"release_id": "<2A>"`, and `preflight_current` printing `<2A>`.
- [x] **Step 5: Confirm retention (D10).** `ls releases` lists `sha256=c4de77b8…`, `sha256=9fa189a0…`, `sha256=aa8de1ac…`, `sha256=fc68adef…`, `sha256=49b7a2ed…`, `sha256=900952a8…`, `sha256=d718ae5f…` and `sha256=<2A>`, plus `artifact-cache` and `task14-guard-proofs`.
- [x] **Step 6: Write `release.md`** in the 1c layout (`## Release`, `## Locked inputs`, `## Offline verification`, retention) and the line "No SEC request was sent. Verification used fixture acquisition only." Commit: `docs(evidence): record the 2a release build and offline verification`.

> Deviation: a review hand fix (`db0be14`) removed an unchecked "stay installable" claim from `release.md`.

---

### Task 10: Scratch re-transform and full rebuilds (spec §6 "Scratch re-transform", budget stop rule; P6)

Run in the main checkout on `main`. This task reads `data/` once to copy it and writes nothing under it.

**Files:**
- Create: `specs/evidence/stage2a/scratch/retransform.py`, `scratch/config.json`, `scratch/sources.json`, `scratch/results.json`, `scratch/live-data-before.sha256`, `scratch/live-data-after.sha256`
- Modify: `specs/evidence/stage2a/release.md`

**Interfaces:**
- Consumes: `<2A>`; F9.
- Produces: per-source and per-rebuild measurements for the Handoff.
- The script's command line: `retransform.py <root> <config> <sources.json> <results.json> {locate,transform,publish-2023Q1,candidate-2026Q3}`. It opens `<root>` with its stored binding (`diag2.py` method). It loads `<config>`, preflights the running release with `preflight_current`, and calls `runtime.retain_manifest` once. It builds a fresh `RunContext` for each command call, with the fields of `tests/support.py:83–90`, `started_at` = now (UTC), `deadline` = now + `execution.max_run_seconds`, and `pin_context(settings, context, today)` with today's UTC date, so 2026Q3 is a closed quarter. It appends one JSON line per step to `<results.json>`.
  - `locate`: write to `sources.json` the 35 sources of F9, each with its `source_id`, raw SHA-256, the snapshot-workset ref that holds it and that workset's member count. It scans `objects/worksets/sec/snapshot/` and prefers the workset with the fewest members. It stops with exit 2 if a source has no workset, or if the workset for the 2023Q1 or 2026Q3 quarterly source has more than one member: `run_publish` publishes every quarter its input touches, so a larger workset would time other quarters and move other pointers on the copy.
  - `transform [--only <source_id>]`: `etl.commands.run_transform` once per distinct snapshot-workset ref, or for one source's workset. For each source it records the row count, distinct keys, keys merged by class (combined filing: same name, several form types; rename: same form, several names; both), wall time of its workset, and outcome or failure reason.
  - `publish-2023Q1`: `run_publish` on the transformed workset that holds the 2023Q1 quarterly source, then `capture_quarter` and `read_quarter`. It records the outcome, the gate, the change counts, the row count read and the publish wall time.
  - `candidate-2026Q3`: `run_publish` on the transformed workset that holds the 2026Q3 quarterly source. It records the outcome (expected `awaiting_approval`), the change counts and the wall time. It runs `validate_candidate_content` on the gated candidate, and checks that the 2026Q3 pointer still names the v1 generation. It never calls `approve`.

- [x] **Step 1: Confirm that no writer runs,** with plan 6 Task 6 Step 1's `pgrep`. Expected: no output.
- [x] **Step 2: Hash `data/` and copy it,** with plan 6 Task 6 Step 2's commands and `W=/tmp/stage2a-scratch-$(date -u +%Y%m%dT%H%M%SZ)`. Record `$W`.
- [x] **Step 3: Write the scratch config.** Copy `conf/sec-edgar-local.json` to `specs/evidence/stage2a/scratch/config.json`. Set `storage.root` to `$W/data`, `logging.root` to `$W/logs`, `runtime.release_manifest` to the `<2A>` manifest path, and `etl` to `sec-index-parser-v2` / `sec-index-v2`. Change nothing else.
- [x] **Step 4: Write `retransform.py`** to the Interfaces above. Then run `locate` on the 2a interpreter (`releases/sha256=<2A>/venv/bin/python -I -B -X pycache_prefix=/dev/null`). Expected: 35 entries, 28 quarterly and 7 daily. If the store refuses the binding or the producer check, stop and report the error.
- [x] **Step 5: Probe one small source.** Run `transform --only <source_id of daily 2026-07-22>`. A binding or producer refusal first shows here. If one occurs, stop and report it. Expected: the source transforms, with only the rename class merged (spec §1.1).
- [x] **Step 6: Run `transform`** for all sources in the background. Expected: all 35 sources transform. No source stays quarantined. If one does, its record names the reason, and the reason is not a repeat that differs only in form type or company name. Otherwise stop and ask.
- [x] **Step 7: Run `publish-2023Q1`, then `candidate-2026Q3`.** Expected: 2023Q1 `published` with gate `clear` and nonempty rows read back. 2026Q3 `awaiting_approval`, its candidate valid, and its pointer unchanged.
- [x] **Step 8: Apply the budget stop rule.** If either publish wall time exceeds 1,500 s, stop. Report both times to the owner and ask them to choose: approve a named limit backed by the measured time, or add a cost fix and measure again. Log the answer as a Decision. The release selection (Task 11) waits for it.
- [x] **Step 9: Confirm `data/` is unchanged,** with plan 6 Task 6 Step 4's commands. Expected: `data-unchanged`.
- [x] **Step 10: Record and commit.** Copy `sources.json`, `results.json` and both hash files into `specs/evidence/stage2a/scratch/`. Append `## Scratch re-transform` to `release.md`: the scratch path, the interpreter, a per-source table, both rebuilds against 1,500 s, 1,800 s and 3,300 s, the path taken under Step 8, and the lines "The 2026Q3 candidate was not approved." and "No SEC request was sent. Nothing was written under `data/`." Commit: `docs(evidence): record the Stage 2a scratch re-transform`. Then `rm -rf "$W"`.

> Deviation: the implementer's login expired after the evidence run and before its report. The controller checked `results.json`, re-hashed `data/`, committed `8e1de77` and removed the scratch copy. The task review ran in a fresh session, with the ledger in place of the missing report.

---

### Task 11: Select the release in the live config (spec §6 "Live-config selection"; HUMAN checkpoint)

**Files:**
- Modify: `conf/sec-edgar-local.json` (`runtime.release_manifest`, `etl.parser_version`, `etl.schema_version`)
- Modify: `specs/evidence/stage2a/release.md`

- [x] **Step 1: Edit the config.** Set `runtime.release_manifest` to `/Users/lowell/Projects/sec-edgar-local/releases/sha256=<2A>/release.json`, `etl.parser_version` to `sec-index-parser-v2` and `etl.schema_version` to `sec-index-v2`. Change nothing else.
- [x] **Step 2: Offline preflight** with plan 6 Task 7 Step 2's command on the 2a interpreter. Expected: `floor 480`, `reserve 1800`, `release <2A>`, a new `effective` SHA-256 (before: `fb93b0e8…`, F10), and three changed values in `git diff`. Run no launcher command.
- [x] **Step 3: Owner checkpoint (HUMAN).** Show the diff, the Step 2 output and the Task 10 times. Ask for approval of the selection. Stop until the owner answers. Log the answer as a Decision. The approval authorizes no SEC traffic.
- [x] **Step 4: Record and commit.** Append `## Live-config selection` to `release.md`, with the effective-config SHA-256, floor, reserve, binding and "No SEC request was sent in this stage." Commit: `chore(config): select the 2a release`.

---

### Task 12: Parent-spec and runbook amendments (spec §7)

**Files:**
- Modify: `specs/sec-filing-index-ingestion-spec.md` (§§4.4, 4.8, 4.9, 6, 9)
- Modify: `docs/runbooks/local-ingestion.md`, `docs/runbooks/release-upgrades.md`
- Modify: `specs/evidence/stage2a/release.md` (the Task 11 commit hash)

- [x] **Step 1: Write the amendments** that spec §7 lists, each tagged `(Stage 2a, plan 7, <date>)`: the §4.4 duplicate paragraph in the spec's words, the §4.8 versions with `<2A>`, its commit and the effective-config SHA-256, the §4.9 paragraph on v1 readability and the one-way release, the §6 duplicate-test line, and the §9 versioned-transition record.
- [x] **Step 2: Update the runbooks** with the new versions and the one-way note: after a v2 run writes to a store, selecting the 1c release for it is unsupported.
- [x] **Step 3: Owner review of the wording (HUMAN).** Show the diff. Apply the answer and log it as a Decision.

> Deviation: on the owner's answer (D13), R3 and §4.5 were also amended. The task review then found that §4.4 no longer described the v1 row and that one §4.9 sentence could be false. Hand fix `2c6d84a` fixed both, and the owner kept it at the completion gate (D14).

- [x] **Step 4: Commit:** `docs(specs): amend the parent spec and runbooks for sec-index-v2`.

---

## After the last task

Run the writing-plans Plan Completion Protocol, step 3a included. Deferred item 1 of section `2-sec-filing-index-ingestion-spec — 2026-10-31` stays open: it is done only when Stage 2b covers or re-quarantines the 35 sources (spec §6). Its `→ planned` note was written at plan commit (`9bbfa9a`); do not tick it. Then remove the worktree and `/tmp/s2a-venv`.

> Deviation: Tasks 9–12 ran on `main` after the Task 8 merge, so the final whole-branch review ran at Task 8. At completion, Codex reviewed `f2610ce..2c6d84a` (finishing-a-development-branch Step 4b, D14) and found nothing.

## Handoff to later stages

Stage 2a shipped what its roadmap `Produces` lists: the stage spec and this plan, the owner-approved `sec-index-v2` design, the change with offline tests, the offline re-transform of the 35 duplicate-key sources, the reviewed release, and the reviewed live-config selection. The bullets name what each later stage consumes as built, the traps found in execution, and the deferred items. They cite the stage spec (`specs/completed/sec-filing-index-duplicate-key.md`) and do not restate it. No item was deferred by this plan. Item 1 of `specs/deferred_items.md`, section `2-sec-filing-index-ingestion-spec — 2026-10-31`, stays open for Stage 2b.

- **Stage 2b (baseline coverage on the Stage 2a release).**
  - Consumes as built:
    - Release `e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec`, built at Git revision `32863852ce57f1da99db4720bd1c729727b4ec0c`. Manifest: `/Users/lowell/Projects/sec-edgar-local/releases/sha256=e49d3ba87f7d4eb3082c5bfbfce44bb02ade6a4acd8dfc1a595d3dc424c67eec/release.json`. Build and verification: `specs/evidence/stage2a/release.md`.
    - The live config `conf/sec-edgar-local.json` selects that release with `sec-index-parser-v2` / `sec-index-v2`, at commit `4d1f806c70a522ce377b5c0391c9287ba2c246d7`. The effective-config SHA-256 is `f2082322b6fe7838504bbd622cb5a8e702512b482943c28ca9be7164f4755733` (before: `fb93b0e8…`). The floor is 480 s and the reserve is 1,800 s.
    - The scratch run on a copy of `data/` (Task 10): all 35 sources transform. The 2023Q1 publish took 733.8 s, which is 41 % of the 1,800 s reserve and 22 % of the 3,300 s launcher default. The 2026Q3 candidate took 1,306.7 s, which is 73 % and 40 %. The 2026Q3 margin to the 1,500 s budget is 193.3 s. It shrinks as daily sources are added to a quarter, because the rebuild re-transforms every daily source of its active generation inline. The scratch objects were deleted, and the live store has never met the release.
  - Expectations (spec §6, "Handoff to Stage 2b"):
    - Each quarter's first v2 publish is a full rebuild.
    - The 26 daily-only v1 generations stay readable as v1 rows. They change only by `provenance_refreshed` or by real changes.
    - 2026Q3 stops at `awaiting_approval` on its first quarterly publish. On the scratch copy: added 21,571, withdrawn 42, provenance_refreshed 280,923. Spec §1.1 counts 47 distinct absent daily keys. 5 of them are only in the quarantined daily sources (plan 7 F9), which the v1 base does not hold, so the gate shows 42. The 2 date differences in base dailies count as `provenance_refreshed`, because a later daily carries the quarterly date. This is existing §4.4 behavior, not a v2 effect. This plan never approved the candidate.
    - 2023Q1 had no v1 base (`baseline_publication_missing`), so its first publish maps no base rows.
  - Traps:
    - **One-way release.** After a v2 run writes to a store, selecting the 1c release for that store is unsupported (spec D10). The live config already selects the 2a release, so the first launcher run writes v2.
    - **Plan 2's campaign configs no longer load.** `load_config` on the new release refuses `conf/stage2/*.json` (v1 configs), so `scripts/baseline-campaign.py`, `history` and `approve` on those configs stop. Stage 2b needs v2 campaign configs.
    - **Plan 2 Handoff traps that still apply.** Read that section (`specs/plans/completed/2-sec-filing-index-ingestion-spec.md`, "Handoff to later stages"). Stage 3 trap (a), the retained-member `state_conflict`, applies to every workflow command. Trap (b), `permit_expired`, and trap (d), the unregistered daily bodies after 2026-10-30, are unchanged. Trap (c) is now expected to clear: the seven quarantined daily sources transformed on the scratch copy.
    - **The acceptance driver's retained-row limit.** `scripts/accept-sec-native.py` `validate_read` cannot validate a generation that holds a retained row whose snapshot was replaced. The older provenance check `sources <= expected_sources` (from `2b64551`) refuses it, before and after this plan.
    - **Do not repeat P7's claim** that the change "breaks no retained check". `scripts/verify-sec-native-adjudication.py` loads the current driver, so it would now refuse the retained `fc68adef` selection. Its evidence folder is gone, so it cannot run either way.
    - **Stale count after a campaign.** `docs/runbooks/local-ingestion.md:66` gives the retained whole-source quarantines (total 51). It is true until a v2 campaign covers or re-quarantines those sources, and then it must change.
  - Deferred into this stage: item 1 of section `2-sec-filing-index-ingestion-spec — 2026-10-31`, by its "Done when". Its `→ planned` note named this plan, which is now retired, so the item ages from 2026-10-31 until Stage 2b's plan adds its own note.

- **Stages 3, 4 and 5 (daily catch-up, manual reconciliation, local scheduling).**
  - Consumes as built: the release, config, reserve and floor in the Stage 2b bullet, wherever these entries name the 1c release (roadmap default (xii)). Plan 6's Handoff, "Stages 3, 4 and 5" bullet, still applies to the three members listed as already complete. This plan did not re-check that list.
  - Readers meet two row versions. A v1 generation reads back as v1 rows with scalar `company_name` and `form_type`. A v2 generation reads back as v2 rows with `form_types` and `company_names` lists (spec D2, D7; parent spec §4.4). A multi-quarter read can hold both.
  - Traps:
    - In a v2 generation, a retained (`unresolved_absence`) row from a v1 base keeps its v1 `parser_version` and `schema_version`. The manifest's `schema_version` governs the file layout (spec D8). A reader must take the layout from the manifest, not from a row. The parent spec does not state spec D8.
    - Fixture-mode continuation of v1-origin pending work is refused. `resolve_child` runs the current interpreter for `runtime.kind=fixture`, and its `load_config` refuses v1. Native-runtime continuation is supported (spec D11, `test_release_2a`).
    - A fixture config with parser `sec-index-parser-v1` and schema `sec-index-v2` loads and then fails at transform with `parser and schema versions do not pair`. A future load-time pair check must cover only the two release parsers, because `fixture-envelope-v1` in `tests/fixtures/config/local.json` must still load.
    - The era tests `test_release_origin`, `test_release_1b` and `test_release_1c` run only their own older releases as children. `test_release_2a` and `test_release_upgrade` cover the new release.
  - Deferred into these stages: nothing new from this plan.
