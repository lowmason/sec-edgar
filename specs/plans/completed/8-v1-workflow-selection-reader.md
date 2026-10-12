# V1 Workflow-Selection Reader Implementation Plan

**Status: COMPLETE (2026-10-12)** — executed via subagent-driven-development; deferred items in specs/deferred_items.md

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A stored `sec-workflow-selection-v1` selection is readable again (`read_workflow_result` and exact replay), while every new selection is still written as `sec-workflow-selection-v2`.

**Supersedes:** plan 7's Global Constraint "No deployed state exists (development is local-fixture only), so the selection format moves to `sec-workflow-selection-v2` without a v1 reader." The owner reversed it on 2026-10-12 (D1). The completed plan 7 file is left unedited as history; this plan, not plan 7, now governs the selection-format rule.

**Architecture:** `workflows/results.py` `_validate_selection` becomes format-aware: v1 is exactly the 20 base keys, v2 is those plus `superseded`, and a v1 selection reads as having superseded nothing. The validator only reads. It never rewrites or upgrades a selection, because the report pins the stored bytes' sha256 (`_validate_report`) and `freeze_selection` re-serializes what it is given with `put_once`. `freeze_selection` refuses to write a first-time selection that is not v2, so v1 stays read-only. `select_work` already writes v2 and is untouched.

**Tech Stack:** Python 3.14, stdlib `unittest` through `tests/network_guard.py`, uv workspace (`--offline --frozen`), the local-fixture backend, and the committed plan-5 proof bundle under `specs/evidence/`.

**Spec:** none (spec-less quick fix). Requirements: deferred item "v1 workflow selections are unreadable" in `specs/deferred_items.md`, section `7-gated-revert-supersession — 2026-10-12`.

**Branch and BASE:** worktree `musing-feynman-5988f9` on branch `claude/hopeful-lederberg-a5ba7d`, cut from `main` at **BASE=`0e64af34`** (plan 7, merged by fast-forward, not pushed). Per-task reviews and the final Codex run diff against `0e64af34`.

## Global Constraints

- Offline only: every command uses `uv run --offline --frozen --package sec-edgar-ingest …`; no SEC, Azure, credential, deployment or trigger activity.
- Pinned dependencies unchanged (`pyproject.toml`, `uv.lock` untouched).
- No new state kinds; the Azure adapters need no change (the selection is opaque JSON to both the local and Azure stores, and nothing under `storage/` mentions it).
- Lean process (`lean-stage-process`): red/green TDD per task, a review per task, a final whole-branch review, then the full offline suite plus wheel build and CLI smoke (`scripts/check-sec-edgar-ingest.sh`). No evidence bundles, hash-bound snapshots or preservation audits.
- The full offline suite must print nothing to stdout (`unittest -v` reports on stderr).
- Selection format rule (D1): `sec-workflow-selection-v2` is the only format ever written. `sec-workflow-selection-v1` is read-only: exactly the 20 base keys, no `superseded`, read as having superseded nothing. A v1 selection that carries `superseded`, a v2 selection that lacks it, and any other format value are refused with `Conflict('selection differs from frozen workflow intent')`. A stored selection is never rewritten or upgraded in place.

  > Deviation from plan 7: plan 7 chose "no v1 reader". Owner decision D1 reverses that; everything else in plan 7's Global Constraints stands.
- Tests may only open a temporary copy of the committed evidence bundle. Opening the local store sets WAL mode and `read_workflow_result` repairs index rows, so after any test run `git status --porcelain -- specs/evidence` must print nothing.
- Do not edit `specs/evidence/`, the completed plan 7, or the plan-5 spec text; they record v1 as it was.
- Do not push, open a PR, merge or deploy. Integration goes back to the owner.
- Every commit message ends with a blank line, then exactly `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` (D2). Work stays on this branch, never on `main`.

Single-file test command, from the repository root (add `-k <substring>` to select tests; repeat `-k` to OR them):

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_results.py' -v
```

## Decisions

- **D1** (owner, brief, 2026-10-12): Make stored `sec-workflow-selection-v1` selections readable again; new selections stay `sec-workflow-selection-v2`. This reverses plan 7's "no v1 reader" constraint and fixes it immediately after plan 7. Applied in: Global Constraints, Task 1, Task 2.
- **D2** (owner, brief, 2026-10-12): Every commit message ends with a blank line, then exactly `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; work on a new branch, not on `main`. Applied in: Global Constraints.
- **D3** (owner, plan review, 2026-10-12): Plan approved as written, including the four defaults below and Task 2's first-write guard (kept). Execute via subagent-driven-development in a fresh session. Applied in: whole plan; Task 2 stays.

**Defaults set while planning (approved at plan review, D3):**

1. A v1 selection reads as "superseded nothing" and is never upgraded in place (the report pins its bytes). Task 1.
2. Task 2's first-write guard is included. It is small, but a reviewer could reject it separately: without it, Task 1 alone lets `freeze_selection` persist a brand-new v1 selection (measured: the Task 2 test fails with "Conflict not raised"). Drop Task 2 if you read it as YAGNI.
3. The real-evidence tests read the committed plan-5 bundle at `specs/evidence/…/installed-sequence/work/.fixture-state`. They fail loudly if that bundle moves. Precedent: `test_etl_contracts.py` reads the committed stage-2 bundle through `parents[3]`.
4. Out of scope: any other format value, CLI or status output, and docs. No living doc names the selection format (checked `README.md`, `packages/sec-edgar-ingest/README.md`, `docs/runbooks/`).

## Evidence gathered while planning (2026-10-12, scratch copies in `/tmp`, nothing committed)

- `specs/evidence` holds 75 `selection.json` files. 74 are workflow selections: all `sec-workflow-selection-v1` with the same 20 keys, none with `superseded`. The 75th, `stage-1/runtime/public-metadata/selection.json`, is not a workflow selection.
- 73 of the 74 have a report. Today all 73 fail `read_workflow_result` with `Conflict('selection differs from frozen workflow intent')`. With v1 read as "no superseded entries" all 73 read OK, so the format/`superseded` gate is the only blocker. The 74th is a crash-point fixture with no report.
- `run_workflow(context, settings, intent, None, store, objects)` replays the three proof workflows (`proof-baseline`, `proof-overlap`, `proof-repeat`) to their stored outcomes once v1 is accepted, with the stored `selection.json` bytes unchanged. Every member already has its receipt, or the selection has none, so no dispatcher is needed.
- Only `_validate_selection` reads `superseded`; `select_work` writes it. Nothing reads it after `freeze_selection` (`run_workflow` uses `halted`, `jobs`, `gaps`, `already_complete`, `parent_ref`, `requested_quarters`, `directories`, `boundary_before`, `discovered_sources`, `unresolved_before`, `discovery_call`).
- Draft Task 1 tests, run before the fix: 2 fail (6 subtests, all with the expected `Conflict`), 4 pass as guards.

## File structure

| File | Change | Task |
|---|---|---|
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py` | `LEGACY_SELECTION_FORMAT`; `_validate_selection` accepts v1 and v2 with their own key sets (1); `freeze_selection` refuses a first-time non-v2 selection (2) | 1, 2 |
| `packages/sec-edgar-ingest/tests/test_workflow_selection_v1.py` | New: reads the committed v1 bundle from a temporary copy | 1 |
| `packages/sec-edgar-ingest/tests/test_workflow_results.py` | New test that a new v1 selection cannot be frozen | 2 |

---

### Task 1: Read stored v1 selections

**Files:**
- Create: `packages/sec-edgar-ingest/tests/test_workflow_selection_v1.py`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:16` (constant), `:152-159` (`_validate_selection` field set and format check), `:180` (`superseded` read)

**Interfaces:**
- Consumes: `freeze_selection(context, selection, store, objects) -> dict`, `read_workflow_result(path, store, objects) -> WorkflowResult`, and `run_workflow(context, settings, intent, dispatcher, store, objects) -> WorkflowResult`, all unchanged.
- Produces: `results.LEGACY_SELECTION_FORMAT = 'sec-workflow-selection-v1'`. `_validate_selection` accepts exactly two shapes: v1 with the 20 base keys, and `SELECTION_FORMAT` (v2) with those plus `superseded`. For v1, `freeze_selection` returns the mapping unchanged and does not touch the stored bytes.

- [x] **Step 1: Write the failing test module**

Create `packages/sec-edgar-ingest/tests/test_workflow_selection_v1.py`:

```python
# tests/test_workflow_selection_v1.py
"""Stored `sec-workflow-selection-v1` selections stay readable (plan 8).

The plan-5 proof bundle committed under specs/evidence holds real v1 selections, reports and
the state rows that index them. Every test opens a temporary copy: reading a report repairs
index rows, and opening the local store sets WAL mode, so the committed bundle must stay untouched.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.models import RunContext, parse_json
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.workflows.results import freeze_selection, read_workflow_result
from sec_edgar_ingest.workflows.runner import run_workflow

EVIDENCE = (Path(__file__).resolve().parents[3] / 'specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution'
            '/final-verification-refresh/installed/installed-sequence/work/.fixture-state')
V1, V2 = 'sec-workflow-selection-v1', 'sec-workflow-selection-v2'
# (run, command, outcome the stored report recorded): proof workflows with a member run, a daily
# overlap, and a repeat whose two members were already complete.
RUNS = (('proof-baseline', 'backfill', 'success'), ('proof-overlap', 'daily', 'success'),
        ('proof-repeat', 'backfill', 'unchanged'))


class StoredV1SelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / '.fixture-state'
        shutil.copytree(EVIDENCE, root)
        # The saved owner binding names the bundle's original root, so reopen the copy under that binding.
        binding = json.loads(next((root / 'objects/locks').glob('**/binding.json')).read_bytes())
        self.store, self.objects = LocalStateStore(root, binding=binding), LocalObjectStore(root, binding=binding)
        self.addCleanup(self.store.close)

    def stored(self, run, command):
        base = f'runs/sec/{run}/{command}/a/'
        intent = parse_json(self.objects.read(base + 'intent.json'))
        body = self.objects.read(base + 'selection.json')
        return base, RunContext.from_mapping(intent['context']), intent['intent'], body

    def test_the_bundle_holds_v1_selections_without_superseded(self):
        for run, command, _ in RUNS:
            with self.subTest(run=run):
                selection = parse_json(self.stored(run, command)[3])
                self.assertEqual(selection['format_version'], V1)
                self.assertNotIn('superseded', selection)

    def test_stored_v1_reports_are_readable(self):
        for run, command, outcome in RUNS:
            with self.subTest(run=run):
                base = self.stored(run, command)[0]
                self.assertEqual(read_workflow_result(base + 'result.json', self.store, self.objects).outcome, outcome)

    def test_stored_v1_selection_replays_without_rewriting_it(self):
        for run, command, outcome in RUNS:
            with self.subTest(run=run):
                base, context, intent, body = self.stored(run, command)
                frozen = freeze_selection(context, parse_json(body), self.store, self.objects)
                self.assertEqual(frozen, parse_json(body))
                # Every member already has its receipt (or the selection has none), so nothing dispatches.
                settings = Settings.from_mapping(context.to_mapping()['effective_config'])
                replayed = run_workflow(context, settings, intent, None, self.store, self.objects)
                self.assertEqual(replayed.outcome, outcome)
                self.assertEqual(self.objects.read(base + 'selection.json'), body)

    def test_a_v1_selection_may_not_carry_superseded(self):
        base, context, _, body = self.stored('proof-repeat', 'backfill')
        with self.assertRaisesRegex(Conflict, 'selection differs from frozen workflow intent'):
            freeze_selection(context, {**parse_json(body), 'superseded': []}, self.store, self.objects)
        self.assertEqual(self.objects.read(base + 'selection.json'), body)

    def test_a_v2_selection_must_carry_superseded(self):
        base, context, _, body = self.stored('proof-repeat', 'backfill')
        with self.assertRaisesRegex(Conflict, 'selection differs from frozen workflow intent'):
            freeze_selection(context, {**parse_json(body), 'format_version': V2}, self.store, self.objects)
        self.assertEqual(self.objects.read(base + 'selection.json'), body)

    def test_unknown_formats_are_refused(self):
        _, context, _, body = self.stored('proof-repeat', 'backfill')
        for label, version in (('future', 'sec-workflow-selection-v3'), ('not a string', ['v1']), ('missing', None)):
            with self.subTest(label):
                selection = {**parse_json(body), 'format_version': version}
                if version is None:
                    del selection['format_version']
                with self.assertRaisesRegex(Conflict, 'selection differs from frozen workflow intent'):
                    freeze_selection(context, selection, self.store, self.objects)


if __name__ == '__main__':
    unittest.main()
```

- [x] **Step 2: Run it to verify it fails for the right reason**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_selection_v1.py' -v
```

Expected: `Ran 6 tests`, `FAILED (errors=6)`. Exactly two tests fail, `test_stored_v1_reports_are_readable` and `test_stored_v1_selection_replays_without_rewriting_it`, once per run (6 subtests), every one with `Conflict: selection differs from frozen workflow intent`. The other four tests (`…holds_v1_selections_without_superseded`, `…v1_selection_may_not_carry_superseded`, `…v2_selection_must_carry_superseded`, `…unknown_formats_are_refused`) already pass: they are guards that pin the other half of the rule, so they are not red and that is expected. Then:

```bash
git status --porcelain -- specs/evidence
```

Expected: no output.

- [x] **Step 3: Implement the reader**

All three edits are in `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py`.

(a) Directly after `SELECTION_FORMAT = 'sec-workflow-selection-v2'` (line 16), add:

```python
# Plan 5 wrote v1, which has no `superseded` key. A stored v1 selection stays readable, as one that
# superseded nothing, and is never written. Its exact bytes are pinned by the report, so it is not upgraded.
LEGACY_SELECTION_FORMAT = 'sec-workflow-selection-v1'
```

(b) In `_validate_selection`, replace

```python
              'member_provenance', 'already_complete', 'superseded', 'discovery_call',
              'discovery_error', 'parent_ref', 'parent_provenance', 'discovery_session',
              'required_units', 'halted', 'requested_quarters', 'directories',
              'boundary_before', 'gaps', 'discovered_sources', 'unresolved_before'}
    selection = _plain(selection)
    if set(selection) != fields or selection['format_version'] != SELECTION_FORMAT or selection['context'] != context.to_mapping() or selection['invocation'] != _plain(invocation):
        raise Conflict('selection differs from frozen workflow intent')
```

with

```python
              'member_provenance', 'already_complete', 'discovery_call',
              'discovery_error', 'parent_ref', 'parent_provenance', 'discovery_session',
              'required_units', 'halted', 'requested_quarters', 'directories',
              'boundary_before', 'gaps', 'discovered_sources', 'unresolved_before'}
    formats = {LEGACY_SELECTION_FORMAT: fields, SELECTION_FORMAT: fields | {'superseded'}}
    selection = _plain(selection)
    version = selection.get('format_version')
    if (not isinstance(version, str) or version not in formats or set(selection) != formats[version]
            or selection['context'] != context.to_mapping() or selection['invocation'] != _plain(invocation)):
        raise Conflict('selection differs from frozen workflow intent')
```

(c) Replace `superseded = selection['superseded']` with

```python
    superseded = selection.get('superseded', [])  # absent only from a v1 selection, which superseded nothing
```

- [x] **Step 4: Run the new module to verify it passes**

Same command as Step 2. Expected: `Ran 6 tests`, `OK`, and `git status --porcelain -- specs/evidence` still prints nothing.

- [x] **Step 5: Run the regressions for the v2 path**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_results.py' -v
```

Expected: `Ran 20 tests`, `OK` (about 80 s). These hand-built selections are v2 with `superseded: []`.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -v -k test_gated_then_reverted_member_is_superseded_by_the_later_download -k test_a_stored_supersession_stays_valid_without_rescanning_the_registry
```

Expected: `Ran 2 tests`, `OK` (in the planning dry run the first took 150 s and the second 48 s). These freeze and re-validate v2 selections with non-empty `superseded` entries, including forged ones. For each of the runs in this step, redirect stdout (`> /tmp/plan8-task1.stdout`, keeping stderr on screen) and check that `wc -c < /tmp/plan8-task1.stdout` prints `0`.

- [x] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/tests/test_workflow_selection_v1.py
git commit -F - <<'EOF'
fix(workflows): read stored sec-workflow-selection-v1 selections

_validate_selection required the v2 format and its superseded key, so every
stored v1 report failed read_workflow_result and replay with state_conflict.
v1 is now the 20 base keys and reads as having superseded nothing; v2 is
unchanged. The validator does not rewrite a selection: the report pins the
stored bytes. Tests read the committed plan-5 proof bundle from a temporary
copy.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: New selections are only frozen as v2

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py` (`freeze_selection`, first statement of the `except FileNotFoundError:` branch, `:345-346` before Task 1's edits)
- Test: `packages/sec-edgar-ingest/tests/test_workflow_results.py` (models import, line 17; new test after `test_selection_substitution_and_missing_evidence_refuse`)

**Interfaces:**
- Consumes: `results.SELECTION_FORMAT` (v2) and Task 1's `_validate_selection`, which now accepts v1.
- Produces: `freeze_selection` raises `Conflict('new selection must use the current format')` when no `selection.json` exists yet and the proposed selection's `format_version` is not `SELECTION_FORMAT`. It writes nothing in that case. A stored selection of any readable format still goes through the existing path.

- [x] **Step 1: Write the failing test**

In `packages/sec-edgar-ingest/tests/test_workflow_results.py`, add `parse_json` to the models import:

```python
from sec_edgar_ingest.models import Error, Source, canonical_json, parse_json, to_mapping_value
```

and insert after `test_selection_substitution_and_missing_evidence_refuse` (before `test_fatal_discovery_without_result_preserves_frozen_prior_jobs`):

```python
    def test_a_new_selection_cannot_be_frozen_in_the_legacy_v1_format(self):
        path = workflow_path(self.context).rsplit('/', 1)[0] + '/selection.json'
        legacy = {**self.selection(), 'format_version': 'sec-workflow-selection-v1'}
        del legacy['superseded']
        with self.assertRaisesRegex(Conflict, 'new selection must use the current format'):
            freeze_selection(self.context, legacy, self.f.store, self.f.objects)
        with self.assertRaises(FileNotFoundError):
            self.f.objects.read(path)
        frozen = freeze_selection(self.context, self.selection(), self.f.store, self.f.objects)
        self.assertEqual(frozen['format_version'], 'sec-workflow-selection-v2')
        self.assertEqual(parse_json(self.f.objects.read(path))['format_version'], 'sec-workflow-selection-v2')
```

- [x] **Step 2: Run it to verify it fails**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_results.py' -v -k test_a_new_selection_cannot_be_frozen
```

Expected: `Ran 1 test`, `FAILED (failures=1)` with `AssertionError: Conflict not raised`. That is the point: after Task 1 alone, a new v1 selection would be frozen and persisted.

- [x] **Step 3: Add the guard**

In `freeze_selection` (`results.py`), replace

```python
    except FileNotFoundError:
        from .checked import _authority
        call = selection['discovery_call']
```

with

```python
    except FileNotFoundError:
        # First: the checks below can put_once a terminal capture, and a refused selection must leave nothing behind.
        if selection.get('format_version') != SELECTION_FORMAT:
            raise Conflict('new selection must use the current format')
        from .checked import _authority
        call = selection['discovery_call']
```

The guard must stay the first statement in the branch: `_capture_or_validate_discovery_failure(…, store)` further down writes `terminal.json`.

- [x] **Step 4: Run it to verify it passes, then the regressions**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_results.py' -v
```

Expected: `Ran 21 tests`, `OK`.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_selection_v1.py' -v
```

Expected: `Ran 6 tests`, `OK`. Then run the runner suite, which freezes new selections through `select_work` (they must still be v2) and replays them:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_runner.py' -v
```

Expected: `OK`. This file holds `RunnerTests.test_deadline_after_selection_records_undispatched_units_without_child_work`, which is listed under "Load-flaky multi-process tests" in `specs/deferred_items.md`: if it is the only failure, re-run it alone three times before treating it as real, and do not debug it in this task. Finally `git status --porcelain -- specs/evidence` prints nothing.

- [x] **Step 5: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/tests/test_workflow_results.py
git commit -F - <<'EOF'
fix(workflows): freeze new selections only in the current format

With v1 readable, freeze_selection would also have persisted a brand-new v1
selection. v1 stays read-only: a first-time selection must be v2. The guard
runs before any capture is written.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
EOF
```

---

## Plan completion

1. Run the final whole-branch review (subagent-driven-development's closing `code-reviewer`) over `0e64af34..HEAD`. For the Codex second-opinion seat, use the recipe with `-c model=gpt-6-astra` (the default model is rejected for the ChatGPT account):

   ```bash
   mkdir -p /tmp/codex-review && codex exec review -c sandbox_mode=read-only -c model=gpt-6-astra --base 0e64af34 -o /tmp/codex-review/plan8.md
   ```

   Resolve or consciously defer its findings. Engage with them critically; fix the underlying issue and push back where warranted.
2. Run `scripts/check-sec-edgar-ingest.sh` from the repository root (about 30 minutes: full offline suite, wheel and sdist build, CLI help, compileall, whitespace check). Also capture the suite's stdout separately and confirm it is empty, and confirm the committed evidence is untouched:

   ```bash
   uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' > /tmp/plan8-suite.stdout 2> /tmp/plan8-suite.stderr; tail -n 3 /tmp/plan8-suite.stderr; wc -c < /tmp/plan8-suite.stdout; git status --porcelain -- specs/evidence
   ```

   Expected: `OK`, then `0`, then no output.

   If a multi-process test fails, look it up under "Load-flaky multi-process tests" in `specs/deferred_items.md`. Re-run a listed test alone three times, and re-run the full check if those pass, before treating the failure as real.
3. Run writing-plans' Plan Completion Protocol. In its deferred-items step, tick the item "v1 workflow selections are unreadable" (section `7-gated-revert-supersession — 2026-10-12`) as `- [x]` and append:
   `→ done in plan 8 (owner reversed plan 7's decision 2026-10-12; this supersedes the item's "Revisit if" condition; test_workflow_selection_v1.py now reads the committed v1 artifacts, which the item said no test did)`.
   Leave the rest of that item's text as it is. Append a plan-8 section only if the protocol's gate defers something.
4. Stop and hand integration (merge, PR or cleanup) back to the owner. Do not merge, push or deploy without that decision.
