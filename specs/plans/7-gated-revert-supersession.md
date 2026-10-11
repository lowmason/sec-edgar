# Gated-Revert Supersession Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A gated member whose source later reverts to its base bytes stops holding every run at `awaiting_approval`. Its stale candidate is listed as `superseded`, and `approve` refuses it.

**Architecture:** Each workflow member's own download time is already recorded permanently in its `PromotionReceipt`. `Snapshot.received_at` cannot serve, because identical bytes keep their *first* receipt. The runner's member selection uses that event time: a pending member is **superseded** when a completed member of the same source has its own download strictly later than the newest download of the pending member's pinned bytes, by any retained member of that source. The member is then dropped from the run's jobs and from `unresolved_before`, and the decision is frozen into the selection (format v2) so replays reproduce it. Separately, a candidate whose base is still active but whose source has since downloaded different bytes gets the derived status `superseded` in `candidates`, and `approve` returns `approval_stale` for it.

**Tech Stack:** Python 3.14, stdlib `unittest` run through `tests/network_guard.py`, uv workspace (`--offline --frozen`), the local-fixture backend and the `ReconcileFixture` workflow harness.

## Origin and decisions

Spec-less plan, from `/deferred` on 2026-10-11 (requirements = deferred item "Gated-then-reverted member cannot clear", `specs/deferred_items.md`, section `6-sec-filing-index-ingestion-stage-5-spec — 2026-10-11`). Background: Stage 5 spec §4 "Known limitation" (`specs/completed/sec-filing-index-ingestion-stage-5-spec.md`). The owner chose these on 2026-10-11:

1. **Rule site: runner selection**, not `accounts_for`. Completion captures and historical receipts keep their exact semantics. This deviates from the item's hint ("touches `workflows/completion.py` (`accounts_for`)"); `accounts_for` is unchanged.
2. **Stale-candidate guard: derive `superseded` and refuse it in `approve`.** Without it, the fix would make the stuck run go green while a candidate that withdraws rows the SEC serves again stays approvable.
3. **Plan directly** (no brainstorming), accepting that the selection format bump and the approval refusal make this slightly larger than "Size: plan".

Two design points settled during planning:

- **The pending side is dated by its bytes, not by itself.** A member bound without downloading has no receipt of its own. That happens to a non-refresh `backfill` member that `collect_member` binds through `reusable_snapshot`. So the pending side's time is the newest own download of its pinned hash by any retained member of the source. This also keeps A → (A, B) → A correct: once the SEC serves A again, A's newest download is later than (A, B)'s, so the gate stands. The superseding side always uses the completed member's own download.
- **Only members that merely await publication are superseded.** `evaluate_member` turns corrupt evidence into a `state_conflict` gap instead of raising. So the drop requires that a member's evaluation gaps all be `publication_pending`, and that it has no repair obligations. Otherwise a corrupt member would vanish from the run instead of failing with exit 9. The gated member and the reuse-bound backfill member both produce only `publication_pending` (both are pinned and processed).
- **The validator checks only time-invariant facts.** `read_workflow_result` → `_validate_report` → `_validate_selection` runs on every later read of a stored report. Validation therefore checks immutable evidence only: bindings, promotion receipts, the completion receipt without the mutable outstanding-repair check, and that the recorded pending-side time is one of the bytes' recorded downloads. It never re-checks "newest" or "currently complete".

Consequence of decision 1, accepted: the **first** run after the revert still reports `awaiting_approval`, because the reverting download completes during that run. The **following** run completes. This matches Stage 5's existing "superseded gated member completes on the following reconcile".

The defect was reproduced before planning (scratch run, 2026-10-11). Baseline (A, B) → reconcile (A) gated → the SEC serves (A, B) → three more reconciles each exit 10. The gated member comes back as `awaiting_approval` each time while every (A, B) download completes `unchanged`. `candidates` lists the request `pending`, with `quarterly_sha256` (A) ≠ `latest_observed_sha256` (A, B). Promotion receipts were confirmed to carry each member's own download time (for example, an (A, B) re-download promoted at 23:23:01 whose snapshot was first received at 23:22:41).

## Global Constraints

- Offline only: every command uses `uv run --offline --frozen --package sec-edgar-ingest …`; no SEC, Azure, credential, deployment or trigger activity.
- Pinned dependencies unchanged (`pyproject.toml`, `uv.lock` untouched).
- Lean process (owner decision 2026-10-11): red/green TDD per task, a review per task, a final whole-branch review, then the full offline suite plus wheel build and CLI smoke (`scripts/check-sec-edgar-ingest.sh`). No evidence bundles, hash-bound snapshots or preservation audits.
- Azure adapters stay in step with the local backend (this plan adds no new state kinds, so nothing to route).
- The 22 reserved Stage 7 integrated checks stay reserved/not_run.
- No deployed state exists (development is local-fixture only), so the selection format moves to `sec-workflow-selection-v2` without a v1 reader.
- The full offline suite must print nothing to stdout (`unittest -v` reports on stderr).

Test command for one file, from the repository root:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -v
```

Add `-k <substring>` to select one test. Reconcile workflow tests take 30–90 s each.

## File structure

| File | Change | Task |
|---|---|---|
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py` | New `member_download`, `pinned_downloads`, `supersession`; `completed(..., repairs=)` | 1 |
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py` | `select_work` drops superseded members and freezes them | 1 |
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py` | `SELECTION_FORMAT` v2; `_validate_selection` validates `superseded` | 1 |
| `packages/sec-edgar-ingest/tests/test_workflow_results.py` | Hand-built selections become v2 with `superseded: []` | 1 |
| `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py` | Gated-then-reverted fixture; #11 runner cases | 1, 3 |
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py` | New `superseding_download`; `approve` refusal | 2 |
| `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py` | `withdrawal_candidates` status `superseded` | 2 |
| `packages/sec-edgar-ingest/tests/support_reconcile.py` | `run_phase` fails with diagnostics when no report | 3 |
| `docs/runbooks/sec-edgar-reconciliation-approval.md` | `superseded` status; drop the "known, deferred limitation" | 4 |

---

### Task 1: Download-time supersession in member selection

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py` (imports; `WorkflowMembers.completed` gains `repairs=True`; append three functions)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py:140-157` (retained loop), `:189` (`combined`), `:211-223` (returned selection)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:16` (`SELECTION_FORMAT`), `:149-176` (`_validate_selection`)
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_results.py:73`, `:322` (hand-built selections)
- Test: `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py` (class `SupersessionWorkflowTests`)

**Interfaces:**
- Produces: `workflows.members.member_download(value: Mapping, store) -> datetime | None`. This is the member's own download time, read from its `PromotionReceipt` for its pinned snapshot hash. It returns `None` when the member has no binding or no receipt (for example, bound by reuse).
- Produces: `workflows.members.pinned_downloads(value: Mapping, retained, store) -> tuple[datetime, ...]`. These are the sorted own-download times of the member's pinned bytes by every retained member of its source, including itself.
- Produces: `workflows.members.supersession(value: Mapping, finished, retained, store) -> dict | None`. `finished` holds the completed registry member values and `retained` the whole verified inventory. The result is `{'member': value, 'by': <newest qualifying completed member value>, 'downloaded_at': iso (newest pinned_downloads), 'by_downloaded_at': iso}`, or `None`.
- Produces: `WorkflowMembers.completed(value, parser_version, schema_version, *, repairs=True)`. With `repairs=False` it skips only the mutable outstanding-repair gate, for re-validating stored evidence.
- Produces: selection key `superseded`, a list of `supersession` entries sorted by `(member.source.period, member.source.source_id, member.member_id)`, under `format_version: 'sec-workflow-selection-v2'`.

- [ ] **Step 1: Write the failing test**

In `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py`, extend the imports:

```python
from sec_edgar_ingest.models import parse_json
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.workflows.results import _validate_selection
```

Append to `class SupersessionWorkflowTests` (after `test_revert_to_older_bytes_is_reported_not_published`):

```python
    def test_gated_then_reverted_member_is_superseded_by_the_later_download(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        base = EtlState(h.store).pointer('2026Q3')
        code, _, gated = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual((code, gated.outcome), (10, 'awaiting_approval'), h.calls[-1])
        # A plain backfill binds its member to the gated bytes by reuse: pending too, with no download receipt.
        code, _, plain = self.run_phase(h, 'backfill', 'plain', (A,))
        self.assertEqual((code, plain.outcome), (10, 'awaiting_approval'), h.calls[-1])
        # The SEC reverts to the base bytes; that download completes during this run, so the gate still holds it.
        code, _, first = self.run_phase(h, 'reconcile', 'revert-1', (A, B))
        self.assertEqual((code, first.outcome), (10, 'awaiting_approval'), h.calls[-1])
        code, _, report = self.run_phase(h, 'reconcile', 'revert-2', (A, B))
        self.assertEqual((code, report.outcome, report.counts['awaiting_approval_quarters']), (0, 'unchanged', 0),
                         h.calls[-1])
        self.assertEqual(report.intent['unresolved_before'], 0)
        selection = parse_json(h.objects.read(report.intent['selection']['ref']))
        self.assertEqual(selection['format_version'], 'sec-workflow-selection-v2')
        held = sorted({member.member_id for member in (*gated.members, *plain.members)
                       if member.outcome == 'awaiting_approval'})
        self.assertEqual(len(held), 2)  # the gated download and the reuse-bound backfill member
        # Same period and source, so the frozen order reduces to member id.
        self.assertEqual([entry['member']['member_id'] for entry in selection['superseded']], held)
        for entry in selection['superseded']:
            self.assertIn(entry['by']['member_id'], [member.member_id for member in first.members])
            self.assertLess(datetime.fromisoformat(entry['downloaded_at']),
                            datetime.fromisoformat(entry['by_downloaded_at']))
        # Both are dated by the gated bytes' newest download, the reuse-bound member having none of its own.
        self.assertEqual(len({entry['downloaded_at'] for entry in selection['superseded']}), 1)
        self.assertFalse(set(held) & {member.member_id for member in report.members})
        entry = selection['superseded'][0]
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), base)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])
        forged = {**selection, 'superseded': [{**entry, 'by_downloaded_at': entry['downloaded_at']}]}
        with self.assertRaisesRegex(Conflict, 'superseded'):
            _validate_selection(forged, report.context, selection['invocation'], h.store, h.objects)
```

Also add `from datetime import datetime` to the imports.

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -k gated_then_reverted -v`
Expected: FAIL at the `revert-2` assertion, because the run is still `(10, 'awaiting_approval', …)` instead of `(0, 'unchanged', 0)`. (Verified on 2026-10-11: before the fix, the gated member and a reuse-bound `backfill` member both stay `awaiting_approval` on every run, and the latter has no `PromotionReceipt`.)

- [ ] **Step 3: Add the download-time functions to `workflows/members.py`**

Change the imports at the top of `members.py` to:

```python
import hashlib
from collections.abc import Iterable, Mapping
from datetime import datetime

from ..models import RunContext, Snapshot, canonical_json, parse_json, to_mapping_value
```

Append at the end of the module:

```python
def member_download(value: Mapping, store) -> datetime | None:
    """When this member itself downloaded its pinned bytes, from its immutable promotion receipt.

    Identical bytes keep their first Snapshot receipt, so only a member's own receipt dates a download.
    A member bound without downloading (reuse) has no receipt.
    """
    from ..state import AcquisitionState
    acquisition = AcquisitionState(store)
    identity = value['source']['source_id']
    binding = acquisition.binding(value['member_id'], identity)
    receipt = None if binding is None else acquisition.promotion_receipt(value['member_id'], identity)
    if receipt is None:
        return None
    times = [Snapshot.from_mapping(snapshot).received_at for snapshot in receipt['snapshots']
             if snapshot['sha256'] == binding.snapshot_sha256]
    return max(times, default=None)


def pinned_downloads(value: Mapping, retained: Iterable[Mapping], store) -> tuple[datetime, ...]:
    """Every own download of this member's pinned bytes by a retained member of its source, oldest first."""
    from ..state import AcquisitionState
    acquisition = AcquisitionState(store)
    identity = value['source']['source_id']
    pinned = acquisition.binding(value['member_id'], identity)
    if pinned is None:
        return ()
    times = []
    for other in retained:
        binding = acquisition.binding(other['member_id'], identity) if other['source'] == value['source'] else None
        if binding is not None and binding.snapshot_sha256 == pinned.snapshot_sha256:
            downloaded = member_download(other, store)
            if downloaded is not None:
                times.append(downloaded)
    return tuple(sorted(times))


def supersession(value: Mapping, finished: Iterable[Mapping], retained: Iterable[Mapping], store) -> dict | None:
    """The newest completed member of this source downloaded strictly after the SEC last served this member's bytes.

    Dating the pending side by its bytes covers members bound by reuse, and keeps a gate that the SEC
    re-serves (A, then A+B, then A again) standing.
    """
    served = pinned_downloads(value, retained, store)
    if not served:
        return None
    later = [(theirs, other) for other in finished if other['source'] == value['source']
             for theirs in (member_download(other, store),) if theirs is not None and theirs > served[-1]]
    if not later:
        return None
    theirs, other = max(later, key=lambda item: (item[0], item[1]['member_id']))
    return {'member': value, 'by': other, 'downloaded_at': served[-1].isoformat(),
            'by_downloaded_at': theirs.isoformat()}
```

In the same file, give `WorkflowMembers.completed` a keyword that skips only the mutable repair gate. Change its signature and its first check:

```python
    def completed(self, value, parser_version, schema_version, *, repairs=True) -> Mapping | None:
```

```python
        if repairs and outstanding_repairs(value, self.store, self.objects):
            return None
```

- [ ] **Step 4: Drop superseded members in `select_work`**

In `runner.py`, change the import line `from .members import WorkflowMembers` to:

```python
from .members import WorkflowMembers, supersession
```

Replace the retained loop (currently lines 145–157, `pending_before, unresolved_ids_before = [], set()` through `unresolved_ids_before.add(...)`) with:

```python
    pending_before, finished, unresolved = [], [], []
    for value in retained:
        try:
            completed = registry.completed(value, context.parser_version, context.schema_version)
        except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
            gaps.append(Error('legacy_member_unresolved', 'retained completion receipt is corrupt: ' + str(error),
                              False, value['source']['source_id'], {'member_id': value['member_id']}))
            completed = None
        if completed is not None:
            finished.append(value)
            continue
        evaluated = evaluate_member(value, context.parser_version, context.schema_version, store, objects)
        pending_before.append(value)
        if not evaluated.complete:
            unresolved.append((value, evaluated))
    # A later completed download of the same source supersedes an older member that only awaits publication.
    # Repair obligations and corrupt evidence (state_conflict gaps) stay exact, so they still fail the run.
    superseded = [entry for value, evaluated in unresolved
                  if not evaluated.obligations and {gap.code for gap in evaluated.gaps} == {'publication_pending'}
                  for entry in (supersession(value, finished, retained, store),) if entry is not None]
    dropped = {entry['member']['member_id'] for entry in superseded}
    unresolved_ids_before = {value['source']['source_id'] for value, _ in unresolved if value['member_id'] not in dropped}
```

Replace the `combined` line (currently line 189) with:

```python
    combined = {value['member_id']: value for value in (*pending_before, *current) if value['member_id'] not in dropped}
```

In the returned selection dict, change `'format_version': 'sec-workflow-selection-v1'` to `'format_version': 'sec-workflow-selection-v2'`, and add after `'already_complete': complete,`:

```python
        'superseded': sorted(superseded, key=lambda entry: (entry['member']['source']['period'],
                             entry['member']['source']['source_id'], entry['member']['member_id'])),
```

- [ ] **Step 5: Validate the frozen `superseded` list**

In `results.py`, set `SELECTION_FORMAT = 'sec-workflow-selection-v2'`. In `_validate_selection`, add `'superseded'` to `fields`. Directly after the `completed_ids` overlap check (`raise Conflict('selection completed captures overlap or duplicate members')`), insert:

```python
    superseded = selection['superseded']
    order = [(e['member']['source']['period'], e['member']['source']['source_id'], e['member']['member_id'])
             for e in superseded]
    dropped = {key[2] for key in order}
    if order != sorted(order) or len(dropped) != len(order) or dropped & ({v['member_id'] for v in members} | set(completed_ids)):
        raise Conflict('selection superseded members overlap or are unordered')
    registry = WorkflowMembers(store, objects)
    retained, _ = registry.inventory()
    for entry in superseded:
        if set(entry) != {'member', 'by', 'downloaded_at', 'by_downloaded_at'}:
            raise Conflict('selection superseded entry fields differ')
        member, by = entry['member'], entry['by']
        read_member(member, store, objects)
        served, later = (datetime.fromisoformat(entry[name]) for name in ('downloaded_at', 'by_downloaded_at'))
        # Stored reports are re-validated on every read, so check only evidence that never changes.
        if (by['source'] != member['source'] or later <= served
                or registry.completed(by, context.parser_version, context.schema_version, repairs=False) is None
                or member_download(by, store) != later or served not in pinned_downloads(member, retained, store)):
            raise Conflict('selection superseded member lacks its later completed download')
```

Add these to the local imports at the top of `_validate_selection`. They are local because `runner.py` imports `results.py` at module level:

```python
    from datetime import datetime
    from .members import WorkflowMembers, member_download, pinned_downloads
    from .provenance import read_member
```

The `not evaluated.obligations` guard in `select_work` (Step 4) has no test of its own; this is deliberate. It keeps repair checks exact (Stage 5 spec §4), and a member with an outstanding repair obligation that is also superseded needs a publish-repair fixture out of proportion to this plan. Reviewers should not block on it.

- [ ] **Step 6: Move the hand-built selections in `tests/test_workflow_results.py` to v2**

At line 73 and line 322, change `'format_version': 'sec-workflow-selection-v1'` to `'format_version': 'sec-workflow-selection-v2'`. In both dicts, add `'superseded': [],` next to `'already_complete'`.

- [ ] **Step 7: Run the tests to verify they pass**

Run, from the repository root:

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_*.py' -v
```

Expected: all pass, including the existing `test_superseded_gated_member_completes_on_the_following_reconcile` and `test_revert_to_older_bytes_is_reported_not_published`. If the new test's `revert-2` outcome is a different completed outcome (for example `success`), stop and report it rather than loosening the assertion: `unchanged` is the expected reading, because no quarter's bytes change.

- [ ] **Step 8: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/tests/test_workflow_results.py packages/sec-edgar-ingest/tests/test_reconcile_workflow.py
git commit -m "fix(workflows): let a later completed download supersede older pending members"
```

### Task 2: Superseded candidates are listed and refused

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py` (imports; new `superseding_download`; `approve` loop)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py:64-67` (status)
- Test: `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py` (class `SupersessionWorkflowTests`)

**Interfaces:**
- Consumes: nothing from Task 1. It reads the mutable source row (`latest_downloaded_snapshot`, `latest_received_at`), which suits a live listing and a live refusal.
- Produces: `etl.approval.superseding_download(candidate: Candidate, store) -> dict[str, str] | None`. It returns `{'latest_observed_sha256', 'latest_observed_at'}` when the source's latest download is strictly later than the candidate's membership snapshot receipt **and** has different bytes; otherwise `None`.
- Produces: `candidates` status value `superseded` (in place of `pending` only), and `approve` → `approval_stale` (exit 11) with details `quarterly_sha256`, `latest_observed_sha256`, `latest_observed_at`.

- [ ] **Step 1: Write the failing test**

Add to the imports of `tests/test_reconcile_workflow.py`:

```python
from sec_edgar_ingest.etl.history import withdrawal_candidates
from sec_edgar_ingest.etl.manifest import approval_ref
```

Append to `class SupersessionWorkflowTests`:

```python
    def test_a_candidate_whose_source_moved_on_is_listed_superseded_and_refused(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        self.assertEqual(self.run_phase(h, 'reconcile', 'gate', (A,))[0], 10, h.calls[-1])
        listed, = withdrawal_candidates(h.objects, EtlState(h.store))
        self.assertEqual((listed['status'], listed['latest_observed_sha256']), ('pending', sha((A,))))
        self.assertEqual(self.run_phase(h, 'reconcile', 'revert', (A, B))[0], 10, h.calls[-1])
        listed, = withdrawal_candidates(h.objects, EtlState(h.store))
        self.assertEqual((listed['status'], listed['quarterly_sha256'], listed['latest_observed_sha256']),
                         ('superseded', sha((A,)), sha((A, B))))
        before = EtlState(h.store).pointer('2026Q3')
        result = approve('2026Q3', listed['generation_id'], sha((A,)), 'Lowell Mason', h.objects, EtlState(h.store))
        self.assertEqual((result.outcome, result.error.details['latest_observed_sha256']),
                         ('approval_stale', sha((A, B))))
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)
        self.assertIsNone(EtlState(h.store).approval(listed['generation_id']))
        with self.assertRaises(FileNotFoundError):
            h.objects.read(approval_ref('2026Q3', listed['generation_id']))
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -k moved_on -v`
Expected: FAIL: `('pending', …) != ('superseded', …)`.

- [ ] **Step 3: Add `superseding_download` and the `approve` refusal**

In `etl/approval.py`, add to the imports:

```python
from ..state import AcquisitionState
```

Add after `_now()`:

```python
def superseding_download(candidate: Candidate, store) -> dict[str, str] | None:
    """The source's latest download when it is strictly later than, and differs from, the candidate's membership.

    Such a candidate withdraws rows on the evidence of bytes the SEC no longer serves.
    """
    membership = candidate.manifest.membership_source
    row = AcquisitionState(store).get_source(membership.source.source_id)
    if row is None:
        return None
    value = row.to_mapping()['value']
    latest, observed = value['latest_downloaded_snapshot'], value['latest_received_at']
    if (latest is None or observed is None or latest == membership.snapshot.sha256
            or datetime.fromisoformat(observed) <= membership.snapshot.received_at):
        return None
    return {'latest_observed_sha256': latest, 'latest_observed_at': observed}
```

In `approve`, directly after the `if active != candidate.manifest.base_generation_id:` block (the `approval_stale` return for a moved base) and before `stored = _store_approval(pending, candidate, objects)`, insert:

```python
        superseded = superseding_download(candidate, state.store)
        if superseded is not None:
            return ApprovalOutcome('approval_stale', None, None, Error(
                'approval_stale', 'a later download of the source supersedes the candidate', False, None,
                {'quarterly_sha256': quarterly_sha256, **superseded}))
```

- [ ] **Step 4: List the status in `withdrawal_candidates`**

In `etl/history.py`, add this import (no cycle: `etl/approval.py` does not import `history`):

```python
from .approval import superseding_download
```

Replace the status expression (currently lines 66–67):

```python
        status = ('active' if active == manifest.generation_id
                  else 'pending' if active == manifest.base_generation_id else 'stale')
```

with:

```python
        status = ('active' if active == manifest.generation_id
                  else 'stale' if active != manifest.base_generation_id
                  else 'superseded' if superseding_download(candidate, state.store) is not None else 'pending')
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_*.py' -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_etl_approval.py' -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_etl_history.py' -v
```

Expected: all pass. The acceptance test's listings (`pending`, `stale`, `active`) are unchanged, because its pending review happens before any later download. `GateFixture` tests record no acquisition state, so `superseding_download` returns `None` there.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py packages/sec-edgar-ingest/tests/test_reconcile_workflow.py
git commit -m "fix(etl): list candidates superseded by a later download and refuse to approve them"
```

### Task 3: Fold in the triggered reconcile/workflow coverage (#11)

This plan edits `workflows/runner.py`, which fires the "Revisit if: those modules are next edited" trigger on the Stage 5 deferred item "Review Minor, reconcile/workflow coverage (T3/T4/T7)". This task does its runner-local cases. The rest are re-deferred at completion (see Plan completion).

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py:11-12, :278` (`source_revert_gaps` reads through `validated_manifest`)
- Modify: `packages/sec-edgar-ingest/tests/support_reconcile.py:58-64` (`run_phase`)
- Test: `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py`

**Interfaces:**
- Consumes: `etl.reader.validated_manifest(capture, objects)` (existing), and the `datetime` and `Conflict` imports that Task 1 added to `tests/test_reconcile_workflow.py` (add them if executing this task alone).
- Produces: `ReconcileFixture.run_phase` now fails the test with the call diagnostics when a run writes no report (it previously returned `None`, and callers then raised `AttributeError` on `report.outcome`).

- [ ] **Step 1: Write the failing test for `source_revert_gaps`**

Add to the imports of `tests/test_reconcile_workflow.py`:

```python
from sec_edgar_ingest.etl.reader import capture_from_pointer
from sec_edgar_ingest.workflows.runner import source_revert_gaps
```

Append to `class SupersessionWorkflowTests`:

```python
    def test_revert_detection_reads_the_active_generation_through_full_validation(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, added = self.run_phase(h, 'reconcile', 'add', (A, B, C))
        self.assertEqual(code, 0, h.calls[-1])
        capture = capture_from_pointer(EtlState(h.store).pointer('2026Q3'))
        data = next(ref for ref in read_manifest(capture, h.objects).files if ref.role != 'changes')
        with open(h.objects.directory / data.path, 'ab') as handle:
            handle.write(b'x')
        with self.assertRaises(Conflict):
            source_revert_gaps(added.members, h.store, h.objects)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_workflow.py' -k full_validation -v`
Expected: FAIL with `AssertionError: Conflict not raised`, because `read_manifest` does not verify generation files. (If `h.objects` has no `directory` attribute, use the `objects` root the harness exposes. `GateFixture.object_path` in `tests/support_approval.py` shows the local layout.)

- [ ] **Step 3: Read through `validated_manifest`**

In `runner.py`, delete `from ..etl.manifest import read_manifest` (its only use is in `source_revert_gaps`) and change the reader import to:

```python
from ..etl.reader import capture_from_pointer, capture_quarter, validated_manifest
```

In `source_revert_gaps`, replace `manifest = read_manifest(capture, objects)` with `manifest = validated_manifest(capture, objects)`.

- [ ] **Step 4: Assert the full revert-gap evidence and the daily refresh flip**

In `test_revert_to_older_bytes_is_reported_not_published`, after the existing `gap.details` assertion, add:

```python
        source_id = next(m.source.source_id for m in report.members if m.source.period == '2026Q3')
        self.assertEqual((gap.source_id, gap.details['generation_id']),
                         (source_id, capture_from_pointer(active).generation_id))
        first, held, observed = (datetime.fromisoformat(gap.details[name])
                                 for name in ('first_received_at', 'active_received_at', 'observed_at'))
        self.assertLess(first, held)
        self.assertLess(held, observed)
```

In `test_selection_requires_refresh_exactly_for_reconcile`, change `for command in ('backfill', 'reconcile'):` to `for command in ('backfill', 'daily', 'reconcile'):`. (A flipped daily discovery was verified on 2026-10-11 to give exit 9 `state_conflict` with "refresh differs from its workflow command".)

These two additions characterize existing behavior. Prove each can fail: temporarily swap `first.isoformat()` and `active.snapshot.received_at.isoformat()` in `source_revert_gaps`'s details (the ordering assertion fails), then restore it with the exact reverse edit.

- [ ] **Step 5: Make `run_phase` fail with diagnostics**

In `tests/support_reconcile.py`, replace the body of `run_phase` with:

```python
        if q3_rows is not None:
            h.pack = self.pack(q3_rows, q4_rows)
        code, message = h.invoke(command, run=run)
        if message.get('result_ref') is None:
            self.fail(f'{command} {run!r} exited {code} without a report: {h.calls[-1]}')
        return code, message, read_workflow_result(message['result_ref'], h.store, h.objects)
```

Every current caller expects a report (all assert exit 0, 3 or 10).

- [ ] **Step 6: Run the tests to verify they pass**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_reconcile_*.py' -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/tests/support_reconcile.py packages/sec-edgar-ingest/tests/test_reconcile_workflow.py
git commit -m "test(workflows): validate revert detection reads and pin revert-gap evidence"
```

### Task 4: Operator documentation

**Files:**
- Modify: `docs/runbooks/sec-edgar-reconciliation-approval.md` (the `status` list, "Before approving" step 3, the `approval_stale` row)

- [ ] **Step 1: Update the status list**

Replace:

```markdown
  - `pending`: its base is active;
  - `active`;
  - `stale`: the base moved on, or an approved candidate was later superseded;
```

with:

```markdown
  - `pending`: its base is active and the source still serves the candidate's bytes;
  - `superseded`: its base is active, but a later download of the source has different bytes. `approve` refuses it; the next reconcile clears the run;
  - `active`;
  - `stale`: the base moved on, or an approved candidate was later superseded;
```

- [ ] **Step 2: Update "Before approving" step 3**

Replace step 3:

```markdown
3. `latest_observed_sha256` equals `quarterly_sha256`. If it differs, the SEC no longer serves the candidate's bytes. Run `reconcile` first and review again. If the SEC went back to the base's bytes, do not approve: the run stays `awaiting_approval` until the source changes (a known, deferred limitation).
```

with:

```markdown
3. `latest_observed_sha256` equals `quarterly_sha256`. A later download with different bytes lists the candidate as `superseded`, and `approve` returns `approval_stale` for it. When the SEC goes back to the base's bytes, the run that downloads them still reports `awaiting_approval`. The next run drops the superseded gated member and completes.
```

- [ ] **Step 3: Update the `approval_stale` row**

Replace:

```markdown
| `approval_stale` | 11 | The base moved. Reconcile to stage a candidate against the current generation, then review it. |
```

with:

```markdown
| `approval_stale` | 11 | The base moved, or a later download supersedes the candidate (`error.details` names `latest_observed_sha256`). Reconcile, then review the current candidates. |
```

- [ ] **Step 4: Check the runbook no longer calls the limitation deferred**

Run: `grep -n "known, deferred limitation" docs/runbooks/sec-edgar-reconciliation-approval.md`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add docs/runbooks/sec-edgar-reconciliation-approval.md
git commit -m "docs: document superseded candidates and the cleared gated-then-reverted run"
```

## Plan completion

1. Run the final whole-branch review (subagent-driven-development's closing reviewer). For the Codex second-opinion seat, run the recipe with `-c model=gpt-6-astra` (the default model is rejected for the ChatGPT account). Resolve or consciously defer its findings.
2. Run `scripts/check-sec-edgar-ingest.sh` from the repository root (full offline suite, wheel and sdist build, CLI help, compileall, whitespace check). Also capture the suite's stdout separately and confirm it is empty:

   ```bash
   uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' > /tmp/plan7-suite.stdout 2> /tmp/plan7-suite.stderr; tail -n 3 /tmp/plan7-suite.stderr; wc -c < /tmp/plan7-suite.stdout
   ```

   Expected: `OK` and `0`.
3. Run writing-plans' Plan Completion Protocol. In its deferred-items step:
   - Tick the item "Gated-then-reverted member cannot clear" as `→ done in plan 7`.
   - Tick "Review Minor, reconcile/workflow coverage (T3/T4/T7)" as `→ trigger fired; runner-local cases done in plan 7, remainder re-deferred under plan 7`. Append one new item for what Task 3 did not do: the refresh/command check in `workflows/results.py` running only when `discovery_call` is present; spec R10 "a later download needs its own approval" covered at library level only (`tests/test_etl_approval.py`), not in `tests/test_reconcile_acceptance.py`; a revert in a quarter gated by another member of the same run is reported only on the next run; long unwrapped lines in `packages/sec-edgar-ingest/README.md`. Size: quick-fix. Revisit if: those modules are next edited or a regression slips through them.
4. Hand integration (merge, PR or cleanup) back to the owner. Do not merge, push or deploy without that decision.
