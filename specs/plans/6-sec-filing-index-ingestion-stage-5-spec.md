# Stage 5: Reconciliation and withdrawal approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `reconcile` workflow, exact approval of gated closed-quarter withdrawals, an explicit recorded pointer rollback, and the operator `candidates` listing and quarter history, with no force bypass.

**Architecture:** `reconcile` is a third command on the shipped Stage 4 runner. Only its discovery differs: `--mode quarterly --refresh`. The shared reducer reports gate-only unresolved work as `awaiting_approval` even beside completed sources. An approval is one immutable object per candidate. It is bound to the candidate's manifest, base generation, gate record and quarterly hash, and mirrored into the `Approvals` table. The single reader validation function, `validated_manifest`, accepts an approved candidate, and `approve` then moves the quarter pointer with the shipped compare-and-swap. Workflow completion also accepts a strictly later observation of the same source. The runner reports a source that reverts to older bytes as a `source_reverted` gap. `rollback` writes an immutable record, then moves the pointer back to an earlier generation in the quarter's exact lineage by the same compare-and-swap.

**Tech Stack:** Python >=3.14; stdlib unittest, dataclasses and SQLite; PyArrow; the pinned Azure SDKs, exercised only through in-memory transports; `uv`, offline and frozen.

**Spec:** [Stage 5 spec](../sec-filing-index-ingestion-stage-5-spec.md). Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 5 — on plan completion, tick the stage and re-validate later stages against what shipped.

## Global Constraints

Copied verbatim from [spec §2](../sec-filing-index-ingestion-stage-5-spec.md#2-constraints-inherited-by-plan-6); every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- Backfill, daily ingestion and reconciliation differ in source selection, not in their downloader, parser or publication code.
- The quarterly baseline is reconciled periodically.
- Each scheduled run refreshes every supported quarterly source.
- Unchanged bytes skip transformation when parser and schema versions also match.
- Reconciliation failures leave the last valid catalog active and identify the affected quarters.
- An HTTP failure, absent listing or open-quarter absence is not a withdrawal.
- A closed-quarter replacement that removes records requires explicit approval tied to its source hash before those records leave the active catalog (4.4).
- If keys disappear, stage the entire replacement and a change report; leave the prior generation active until approval names that exact source hash and candidate generation.
- Approval cannot be reused for a later download.
- After a replacement is approved, old daily observations cannot recreate a key it excludes.
- A subsequent valid quarterly snapshot may reintroduce the key, recorded as a new change.
- No response failure, empty replacement or unexplained format change can produce withdrawals.
- A gated candidate is `awaiting_approval`, not current.
- **Withdrawal pending:** retain the active generation and emit an approval request naming exact hashes. This is a distinct gated outcome, not successful reconciliation.
- The pointer update is the publication boundary.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- Moving a quarter pointer back requires an explicit recorded rollback; it cannot reverse downstream exports already consumed.
- A rollback changes active pointers; it does not erase source history or retract data that consumers have already used.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

The accepted pins carry over unchanged: Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, and the existing `uv.lock`. Stage 5 adds no dependencies and no config keys; `reconciliation.require_withdrawal_approval` is already enforced as `true`. Existing config, workset and binding-registry bytes are never rewritten. Work is offline only: no SEC, Azure, credential, deployment or trigger activity. All 22 Stage 7 integrated checks remain reserved/not_run.

**Process (owner decision, 2026-10-11):** lean. Each task gets red/green TDD and a review, and a final whole-branch review closes the stage. The stage exit runs the full offline suite plus a wheel build and CLI smoke test. Earlier stages' preservation audits, hash-bound approval snapshots and evidence bundles are not carried forward. Azure adapters stay in step with the local backend.

---

## Execution setup

1. **Use the existing worktree.** The planning session already created branch `stage-5-reconcile` from `main` at `6ef957bb`, in the worktree `/Users/lowell/Projects/sec-edgar/.claude/worktrees/stage-5-reconcile`. Its first commit, `docs(specs): add Stage 5 spec and Plan 6`, holds the spec, this plan and the roadmap planning note. Do not create another branch or worktree, and do not redo that commit. Start the execution session in that directory, or enter it with `EnterWorktree(path="/Users/lowell/Projects/sec-edgar/.claude/worktrees/stage-5-reconcile")`. Then confirm `git branch --show-current` prints `stage-5-reconcile`.

   Stage files by explicit path only; never use `git add -A`. Never touch the primary checkout at `/Users/lowell/Projects/sec-edgar`: it holds unrelated unstaged deletions and untracked drafts. Every commit message ends with the attribution trailer supplied by the executing session.
2. **Working directory.** Run every command below from the worktree root.
3. **Focused tests.** `<pattern>` is a test-file glob and `<name>` an optional test-name substring:

   ```bash
   uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p '<pattern>' -k '<name>' -v
   ```

4. **Baseline.** Before Task 1, run the full suite once (about 15 minutes; Task 7 Step 6 has the command) and record the result. Report any pre-existing failure to the owner; do not fix it in passing.

## File map

| File | Responsibility | Task |
|---|---|---|
| `src/sec_edgar_ingest/etl/contracts.py` | `require_line`; `WithdrawalApproval` (1) and `QuarterRollback` (6) records | 1, 6 |
| `src/sec_edgar_ingest/etl/manifest.py` | `approval_ref`, `approval_for`, `read_approval` (1); shared `retained_base` (5) | 1, 5 |
| `src/sec_edgar_ingest/etl/reader.py` | `validated_manifest` accepts exactly approved gated generations | 1 |
| `src/sec_edgar_ingest/etl/state.py` | Approval (1) and rollback (6) indexes | 1, 6 |
| `src/sec_edgar_ingest/storage/contracts.py`, `storage/azure.py` | `APPROVAL_KINDS` → `Approvals` table and client | 1, 6 |
| `src/sec_edgar_ingest/etl/approval.py` (new) | `approve` operation, `ApprovalOutcome` | 2 |
| `src/sec_edgar_ingest/results.py` | Refused exit 2 and stale exit 11 for approval (2) and rollback (6) | 2, 6 |
| `src/sec_edgar_ingest/cli.py` | `_operator_main`; `approve` (2), `reconcile` (3), `candidates` (5), `rollback` (6) | 2, 3, 5, 6 |
| `src/sec_edgar_ingest/workflows/contracts.py`, `checked.py`, `runner.py`, `results.py` | Reconcile command, refresh rule, run-level gate reducer | 3 |
| `src/sec_edgar_ingest/workflows/completion.py`, `runner.py` | `accounts_for`, `source_revert_gaps` | 4 |
| `src/sec_edgar_ingest/etl/history.py` (new) | `lineage`, `quarter_history`, `withdrawal_candidates` | 5 |
| `src/sec_edgar_ingest/etl/rollback.py` (new) | `rollback` operation, `RollbackOutcome`, `rollback_ref` | 6 |
| `tests/support_approval.py` (new) | `GateFixture`, `operator_cli`, `row` | 1 |
| `tests/support_reconcile.py` (new) | `ReconcileFixture`, fixture rows and packs | 3 |
| `tests/test_etl_approval.py` (new) | Approval evidence, reader and `approve` | 1, 2 |
| `tests/test_reconcile_workflow.py` (new) | Reconcile, supersession and revert | 3, 4 |
| `tests/test_workflow_contracts.py`, `tests/test_workflow_runner.py` | Exit-code table, reconcile contracts, run-level gate reducer | 2, 3, 6 |
| `tests/test_etl_history.py` (new) | History and candidates | 5 |
| `tests/test_etl_rollback.py` (new) | Recorded rollback | 6 |
| `tests/test_reconcile_acceptance.py` (new) | Operator flow through the CLI only | 7 |
| `README.md`, `docs/runbooks/sec-edgar-reconciliation-approval.md` (new), ETL runbook | Operator docs | 7 |

All `src/` and `tests/` paths are under `packages/sec-edgar-ingest/`.

---

### Task 1: Approval evidence, reader acceptance and the Approvals table

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py` (constants beside `RESULT_FORMAT` at line 19; new code after `GenerationCapture`, line 247)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py` (imports at lines 4-18; new functions after `gate_payload`, line 57)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py:13,28-34`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py:8` and after `record_candidate` (line 59)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py:126-129`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py:76-106,517-519`
- Create: `packages/sec-edgar-ingest/tests/support_approval.py`
- Create: `packages/sec-edgar-ingest/tests/test_etl_approval.py`
- Modify: `packages/sec-edgar-ingest/tests/test_etl_storage.py` (new test after `test_active_pointer_real_sdk_insert_replace_and_conflict`)
- Modify: `packages/sec-edgar-ingest/tests/test_azure_contracts.py:358-360`

**Interfaces:**
- Consumes: shipped `Candidate`, `GenerationCapture`, `gate_ref(manifest)`, `gate_payload(candidate)`, `validate_candidate`, `EtlState._immutable`, `seed_observation`, `etl_context`, `open_stores`.
- Produces:
  - `etl.contracts`: `APPROVAL_FORMAT = 'sec-withdrawal-approval-v1'`, `MAX_OPERATOR_CHARS = 256`, `require_line(value: object, label: str, limit: int) -> None`, and `WithdrawalApproval(Record)` with fields `quarter, generation_id, base_generation_id, source_fingerprint, quarterly_sha256, candidate_ref, gate_sha256, manifest_ref, manifest_sha256, manifest_bytes, approver, approved_at: datetime, format_version`.
  - `etl.manifest`:
    - `approval_ref(quarter: str, generation_id: str) -> str`
    - `approval_for(candidate: Candidate, approver: str, approved_at: datetime) -> WithdrawalApproval`
    - `read_approval(candidate: Candidate, objects: ObjectStore) -> WithdrawalApproval`, which raises `FileNotFoundError` when the object is absent and `ValueError` when it is non-canonical or unbound.
  - `EtlState.record_approval(approval) -> None` and `EtlState.approval(generation_id) -> WithdrawalApproval | None`.
  - Storage: `APPROVAL_KINDS = frozenset({"WithdrawalApproval"})`, `table_for('WithdrawalApproval') == 'Approvals'`, and `AzureStateStore(..., approval_client=TableClient | None)`.
  - Test support:
    - `support_approval.row(name='Example', number=1, day='2026-10-01') -> bytes`
    - `operator_cli(*argv) -> (int, dict | None, str)`
    - `GateFixture`, with `root`, `store`, `objects`, `state`, `settings`, `context`, `pin(day)`, `observation(**kw)`, `publish(*refs, quarter='2026Q4', **kw)`, `capture(quarter='2026Q4')`, `rows(capture=None) -> [(row_number, company_name)]`, `candidate(candidate_ref) -> Candidate`, `gated() -> (base GenerationCapture, revised ObservationRef, Candidate)`, `object_path(ref) -> Path` and `write_config() -> Path`.

- [ ] **Step 1: Create the shared gated-candidate fixture**

`GateFixture` opens stores exactly as the CLI does: `open_stores(settings, base_path=root)` resolves to `root/.fixture-state` with the settings binding. Operator CLI calls with `--state-dir root` therefore see the same state. Do not use `support.store_bundle` here; it opens the stores directly at `root`.

Create `packages/sec-edgar-ingest/tests/support_approval.py`:

```python
"""Real gated-candidate fixtures shared by approval, history and operator CLI tests."""
from network_guard import install
install()

import contextlib
import io
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from pathlib import Path

from support import fixture_settings
from support_etl import etl_context, seed_observation
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.etl.contracts import Candidate
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import canonical_json, to_mapping_value
from sec_edgar_ingest.storage import open_stores


def row(name='Example', number=1, day='2026-10-01'):
    return f'123456|{name}|10-K|{day}|edgar/data/123456/0000123456-26-{number:06}.txt\n'.encode()


def operator_cli(*argv):
    """Run one operator command through the console entry point; stdout is empty on usage errors."""
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(list(argv))
    return code, (json.loads(stdout.getvalue()) if stdout.getvalue() else None), stderr.getvalue()


class GateFixture(unittest.TestCase):
    """Stores open exactly as the CLI opens them, so operator commands see the same state."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings, self.context = etl_context(command='publish')
        self.pin(date(2026, 10, 7))
        self.store, self.objects, leases = open_stores(self.settings, base_path=self.root)
        leases.close()
        self.addCleanup(self.store.close)
        self.state = EtlState(self.store)

    def pin(self, day):
        self.settings = fixture_settings(etl={'parser_version': self.context.parser_version},
                                         fixture={'allow_clock_override': True})
        self.context = pin_context(self.settings, replace(self.context, config_sha256=self.settings.config_sha256,
                                   effective_config={}, pinned_on=None), day)[0]

    def observation(self, **kwargs):
        return seed_observation(self.objects, self.state, self.context, self.settings, **kwargs)

    def publish(self, *refs, quarter='2026Q4', **kwargs):
        from sec_edgar_ingest.etl.publication import publish_quarter
        return publish_quarter(quarter, refs, self.context, self.settings, self.objects, self.state, **kwargs)

    def capture(self, quarter='2026Q4'):
        from sec_edgar_ingest.etl.reader import capture_quarter
        return capture_quarter(quarter, self.objects, self.state)

    def rows(self, capture=None):
        """(row number, company) pairs of a fully validated quarter read."""
        from sec_edgar_ingest.etl.reader import read_quarter
        return [(int(item.archive_path.rsplit('-', 1)[1].removesuffix('.txt')), item.company_name)
                for item in read_quarter(capture or self.capture(), self.objects)]

    def candidate(self, candidate_ref):
        generation_id = candidate_ref.split('sha256=', 1)[1].split('/', 1)[0]
        return Candidate.from_mapping(self.store.get('Candidate', generation_id).to_mapping()['value'])

    def gated(self):
        """Publish rows 1 and 2 while 2026Q4 is open, then stage the closed withdrawal of row 2."""
        initial = self.observation(rows=row() + row(number=2))
        self.assertEqual(self.publish(initial).outcome, 'published')
        base = self.capture()
        revised = self.observation(rows=row(), seconds=1)
        self.pin(date(2027, 1, 1))
        result = self.publish(revised)
        self.assertEqual(result.outcome, 'awaiting_approval')
        return base, revised, self.candidate(result.candidate_ref)

    def object_path(self, ref):
        return self.objects.directory / ref

    def write_config(self):
        path = self.root / 'config.json'
        path.write_bytes(canonical_json(to_mapping_value(self.settings.to_mapping())))
        return path
```

- [ ] **Step 2: Write the failing tests**

Create `packages/sec-edgar-ingest/tests/test_etl_approval.py`:

```python
"""Offline withdrawal approval evidence, reader acceptance and the approve operation."""
from network_guard import install
install()

import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone

from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.contracts import Candidate, WithdrawalApproval
from sec_edgar_ingest.etl.manifest import approval_for, approval_ref, read_approval, read_manifest
from sec_edgar_ingest.etl.publication import pointer_value, repair_publication
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import Conflict, blob_address, table_for

APPROVED_AT = datetime(2027, 1, 2, tzinfo=timezone.utc)


class ApprovalEvidenceTests(GateFixture):
    def test_approval_binds_the_exact_candidate_and_validates_its_fields(self):
        base, revised, candidate = self.gated()
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        manifest = candidate.manifest
        self.assertEqual((approval.quarter, approval.generation_id, approval.base_generation_id),
                         ('2026Q4', manifest.generation_id, base.generation_id))
        self.assertEqual(approval.quarterly_sha256, revised.snapshot.sha256)
        self.assertEqual(approval.gate_sha256,
                         hashlib.sha256(self.objects.read(candidate.candidate_ref)).hexdigest())
        self.assertEqual((approval.manifest_ref, approval.format_version),
                         (candidate.manifest_ref, 'sec-withdrawal-approval-v1'))
        self.assertEqual(WithdrawalApproval.from_mapping(approval.to_mapping()), approval)
        ref = approval_ref('2026Q4', manifest.generation_id)
        self.assertEqual(ref, 'approvals/sec/filing_index/year=2026/quarter=4/generation='
                         + manifest.generation_id + '/approval.json')
        self.assertEqual(blob_address(ref), ('approvals', ref.removeprefix('approvals/')))
        for approver in ('', '   ', 'two\nlines', 'tab\there', 'x' * 257, 'zero\u200bwidth'):
            with self.subTest(approver=approver), self.assertRaises(ValueError):
                approval_for(candidate, approver, APPROVED_AT)
        self.assertEqual(approval_for(candidate, 'x' * 256, APPROVED_AT).approver, 'x' * 256)
        with self.assertRaises(ValueError):
            approval_for(candidate, 'Lowell Mason', APPROVED_AT.replace(tzinfo=None))
        with self.assertRaises(ValueError):
            replace(approval, format_version='sec-withdrawal-approval-v0')
        clear = Candidate(read_manifest(base, self.objects), base.manifest_ref, base.manifest_sha256,
                          base.manifest_bytes, None)
        with self.assertRaisesRegex(ValueError, 'exact awaiting-approval candidate'):
            approval_for(clear, 'Lowell Mason', APPROVED_AT)

    def test_reader_accepts_an_awaiting_approval_pointer_only_with_its_exact_approval(self):
        _, _, candidate = self.gated()
        self.state.commit_pointer('2026Q4', pointer_value(candidate), self.state.pointer('2026Q4'))
        with self.assertRaisesRegex(ValueError, 'awaiting-approval'):
            self.capture()
        with self.assertRaisesRegex(ValueError, 'awaiting-approval'):
            repair_publication('2026Q4', self.objects, self.state)
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        ref = approval_ref('2026Q4', candidate.manifest.generation_id)
        self.objects.put_once(ref, canonical_json(approval.to_mapping()))
        self.assertEqual(self.rows(), [(1, 'Example')])
        repair_publication('2026Q4', self.objects, self.state)
        self.assertEqual(read_approval(candidate, self.objects), approval)
        path = self.object_path(ref)
        path.write_bytes(json.dumps(approval.to_mapping(), indent=1).encode())
        with self.assertRaisesRegex(ValueError, 'canonical JSON'):
            self.capture()
        path.write_bytes(canonical_json(replace(approval, quarterly_sha256='0' * 64).to_mapping()))
        with self.assertRaisesRegex(ValueError, 'not bound'):
            self.capture()

    def test_approval_index_is_immutable_and_routes_to_the_approvals_table(self):
        _, _, candidate = self.gated()
        approval = approval_for(candidate, 'Lowell Mason', APPROVED_AT)
        self.assertIsNone(self.state.approval(approval.generation_id))
        self.state.record_approval(approval)
        self.state.record_approval(approval)
        self.assertEqual(self.state.approval(approval.generation_id), approval)
        with self.assertRaises(Conflict):
            self.state.record_approval(replace(approval, approver='Someone Else'))
        self.assertEqual(table_for('WithdrawalApproval'), 'Approvals')


if __name__ == '__main__':
    unittest.main()
```

In `packages/sec-edgar-ingest/tests/test_etl_storage.py`, add this method to `EtlStorageTests` right after `test_active_pointer_real_sdk_insert_replace_and_conflict`:

```python
    def test_withdrawal_approval_real_sdk_routes_to_the_approvals_table(self):
        from azure.core.credentials import AzureSasCredential
        from azure.data.tables import TableServiceClient
        from sec_edgar_ingest.storage.azure import AzureStateStore
        from test_azure_contracts import ScriptedTransport, table_response, TABLE_ENDPOINT, RETRY
        transport = ScriptedTransport([table_response(201, etag='W/"approval"')])
        service = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential('sv=offline&sig=synthetic'), api_version='2020-12-06', transport=transport, **RETRY)
        self.addCleanup(service.close)
        tables = service.get_table_client
        store = AzureStateStore(tables('SourceState'), tables('Attempts'), active_client=tables('ActivePointers'),
                                approval_client=tables('Approvals'))
        created = store.insert('WithdrawalApproval', 'a' * 64, {'approver': 'Lowell Mason'})
        self.assertEqual(created.version, 'W/"approval"')
        self.assertEqual(len(transport.requests), 1)
        self.assertIn('/Approvals', transport.requests[0].url)
        print('approval-wire', transport.requests[0].method, transport.requests[0].url.split('?')[0])
        without = AzureStateStore(tables('SourceState'), tables('Attempts'), active_client=tables('ActivePointers'))
        with self.assertRaisesRegex(ValueError, 'Approvals client'):
            without.get('WithdrawalApproval', 'a' * 64)
        with self.assertRaises(ValueError):
            AzureStateStore(tables('SourceState'), tables('Attempts'), approval_client=tables('ActivePointers'))
```

In `packages/sec-edgar-ingest/tests/test_azure_contracts.py`, replace lines 358-360 of `test_factory_conditions_fixed_registry_before_authority_clients`:

```python
            self.assertEqual([call.args[0] for call in tables.get_table_client.call_args_list],
                             ["SourceState", "Attempts", "ActivePointers", "Approvals"])
            self.assertEqual(state.active_client.table_name, "ActivePointers")
            self.assertEqual(state.approval_client.table_name, "Approvals")
```

- [ ] **Step 3: Run the tests to verify they fail**

Run the focused command with `-p 'test_etl_approval.py'` and no `-k`.
Expected: an `ImportError` (`cannot import name 'WithdrawalApproval'`).

Then run it with `-p 'test_etl_storage.py' -k approvals_table`.
Expected: a `TypeError` naming the unexpected keyword argument `approval_client`.

- [ ] **Step 4: Add the approval record**

In `etl/contracts.py`, add these constants after `RESULT_FORMAT = 'sec-etl-result-v1'`:

```python
APPROVAL_FORMAT = 'sec-withdrawal-approval-v1'
MAX_OPERATOR_CHARS = 256
```

After the `GenerationCapture` class, add the helper below and the record after it. `require_text` already refuses control characters; `isprintable` also refuses format and separator characters such as U+200B and U+2028.

```python
def require_line(value: object, label: str, limit: int) -> None:
    """Operator-entered text: one printable line of bounded length."""
    require_text(value, label)
    if len(value) > limit or not value.isprintable():
        raise ValueError(f'{label} must be one printable line of at most {limit} characters')


@dataclass(frozen=True, slots=True)
class WithdrawalApproval(Record):
    """Immutable operator approval of one exact gated candidate generation."""
    quarter: str
    generation_id: str
    base_generation_id: str
    source_fingerprint: str
    quarterly_sha256: str
    candidate_ref: str
    gate_sha256: str
    manifest_ref: str
    manifest_sha256: str
    manifest_bytes: int
    approver: str
    approved_at: datetime
    format_version: str = APPROVAL_FORMAT

    def __post_init__(self):
        _record(self)
        if self.format_version != APPROVAL_FORMAT:
            raise ValueError('unsupported approval format')
        _counts(self, 'manifest_bytes')
        require_line(self.approver, 'approver', MAX_OPERATOR_CHARS)
        require_utc(self.approved_at, 'approved_at')
```

`_record` already validates the hash-named fields, the `_ref` paths and `quarter`.

- [ ] **Step 5: Add approval addressing, binding and reading**

In `etl/manifest.py`, add `from datetime import datetime` to the stdlib imports. Then change the two package imports to:

```python
from ..models import canonical_json, parse_json, quarter_for, quarter_value, require_hash
from ..storage.contracts import Conflict, ObjectStore
from .contracts import (Candidate, FileRef, GenerationCapture, GenerationManifest, IndexRow,
                        ObservationRef, WithdrawalApproval, canonical_schema, change_schema)
```

Directly after `gate_payload`, add:

```python
def approval_ref(quarter: str, generation_id: str) -> str:
    year, ordinal = quarter_value(quarter)
    require_hash(generation_id, 'generation_id')
    return f'approvals/sec/filing_index/year={year}/quarter={ordinal}/generation={generation_id}/approval.json'


def approval_for(candidate: Candidate, approver: str, approved_at: datetime) -> WithdrawalApproval:
    manifest = candidate.manifest
    if manifest.gate != 'awaiting_approval' or candidate.candidate_ref != gate_ref(manifest):
        raise ValueError('approval requires an exact awaiting-approval candidate')
    return WithdrawalApproval(manifest.quarter, manifest.generation_id, manifest.base_generation_id,
                              manifest.source_fingerprint, manifest.membership_source.snapshot.sha256,
                              candidate.candidate_ref, hashlib.sha256(gate_payload(candidate)).hexdigest(),
                              candidate.manifest_ref, candidate.manifest_sha256, candidate.manifest_bytes,
                              approver, approved_at)


def read_approval(candidate: Candidate, objects: ObjectStore) -> WithdrawalApproval:
    """Return the stored approval only when it names this exact candidate, base and source hash."""
    manifest = candidate.manifest
    body = objects.read(approval_ref(manifest.quarter, manifest.generation_id))
    approval = WithdrawalApproval.from_mapping(parse_json(body))
    if canonical_json(approval.to_mapping()) != body:
        raise ValueError('approval must use canonical JSON')
    if approval != approval_for(candidate, approval.approver, approval.approved_at):
        raise ValueError('approval is not bound to this exact candidate, base and source hash')
    return approval
```

- [ ] **Step 6: Accept approved candidates in the reader and index approvals**

In `etl/reader.py`, change the manifest import to:

```python
from .manifest import gate_ref, generation_base, iter_file_rows, read_approval, read_manifest, validate_candidate
```

Then replace `validated_manifest` with:

```python
def validated_manifest(capture: GenerationCapture, objects: ObjectStore) -> GenerationManifest:
    manifest = read_manifest(capture, objects)
    candidate = Candidate(manifest, capture.manifest_ref, capture.manifest_sha256,
                          capture.manifest_bytes, gate_ref(manifest))
    if manifest.gate != 'clear':
        # Cheap binding check first; validate_candidate then proves content and the gate record.
        try:
            read_approval(candidate, objects)
        except FileNotFoundError as error:
            raise ValueError('an awaiting-approval generation cannot be current without its exact approval') from error
    validate_candidate(candidate, objects)
    return manifest
```

In `etl/state.py`, add `WithdrawalApproval` to the `.contracts` import. Add these methods after `record_candidate`:

```python
    def record_approval(self, approval: WithdrawalApproval) -> None:
        self._immutable('WithdrawalApproval', approval.generation_id, approval.to_mapping())

    def approval(self, generation_id: str) -> WithdrawalApproval | None:
        require_hash(generation_id, 'generation_id')
        row = self.store.get('WithdrawalApproval', generation_id)
        return None if row is None else WithdrawalApproval.from_mapping(row.to_mapping()['value'])
```

- [ ] **Step 7: Route approval records to `Approvals`, locally and on Azure**

In `storage/contracts.py`, add this constant after `ATTEMPT_KINDS`:

```python
APPROVAL_KINDS = frozenset({"WithdrawalApproval"})
```

Then replace `table_for` with:

```python
def table_for(kind: str) -> str:
    if kind == "QuarterPublication":
        return "ActivePointers"
    if kind in APPROVAL_KINDS:
        return "Approvals"
    return "Attempts" if kind in ATTEMPT_KINDS else "SourceState"
```

The local store keys every record by a `table_name` column, so it needs no other change.

In `storage/azure.py`, replace `AzureStateStore.__init__`, `close` and `_client` with:

```python
    def __init__(self, source_client: TableClient, attempt_client: TableClient, *,
                 objects: ObjectStore | None = None, observer: BoundaryObserver | None = None,
                 active_client: TableClient | None = None, approval_client: TableClient | None = None):
        for client, name in ((active_client, "ActivePointers"), (approval_client, "Approvals")):
            if client is not None:
                _check_endpoint(client.url, "table")
                if client.table_name != name:
                    raise ValueError(f"Table client must use the accepted {name} binding")
        self.active_client = active_client
        self.approval_client = approval_client
        for client, name in ((source_client, "SourceState"), (attempt_client, "Attempts")):
            _check_endpoint(client.url, "table")
            if client.table_name != name:
                raise ValueError("Table client must use the accepted table binding")
        self.source_client = source_client
        self.attempt_client = attempt_client
        self.objects = objects
        self.observer = observer

    def close(self) -> None:
        self.source_client.close()
        self.attempt_client.close()
        for client in (self.active_client, self.approval_client):
            if client is not None:
                client.close()

    def _client(self, kind: str) -> TableClient:
        table = table_for(kind)
        if table == "ActivePointers":
            if self.active_client is None:
                raise ValueError("quarter pointer operations require the ActivePointers client")
            return self.active_client
        if table == "Approvals":
            if self.approval_client is None:
                raise ValueError("approval operations require the Approvals client")
            return self.approval_client
        return self.attempt_client if table == "Attempts" else self.source_client
```

In `open_azure_stores`, replace the `AzureStateStore(...)` construction with:

```python
    state = AzureStateStore(tables.get_table_client(storage.source_table), tables.get_table_client(storage.attempt_table),
                            objects=objects, observer=observer, active_client=tables.get_table_client("ActivePointers"),
                            approval_client=tables.get_table_client("Approvals"))
```

- [ ] **Step 8: Run the tests to verify they pass**

Run the focused command once for each pattern, with no `-k`: `test_etl_approval.py`, `test_etl_storage.py`, `test_azure_contracts.py` and `test_etl_publication.py`.
Expected: every run ends `OK`. `test_awaiting_approval_pointer_is_refused_by_capture_and_repair` still passes, because the new refusal message contains `awaiting-approval`.

- [ ] **Step 9: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/reader.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py packages/sec-edgar-ingest/tests/support_approval.py packages/sec-edgar-ingest/tests/test_etl_approval.py packages/sec-edgar-ingest/tests/test_etl_storage.py packages/sec-edgar-ingest/tests/test_azure_contracts.py
git commit -m "feat(etl): bind withdrawal approvals to exact gated candidates"
```

---

### Task 2: The `approve` operation, exit codes and CLI

**Files:**
- Create: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py:10-17`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py` (imports; `_parser`; new helpers before `main`; `main` routing)
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_contracts.py:108-128`
- Modify: `packages/sec-edgar-ingest/tests/test_etl_approval.py` (imports, new `ApproveTests` class)

**Interfaces:**
- Consumes (Task 1): `approval_for`, `approval_ref`, `read_approval`, `require_line`, `MAX_OPERATOR_CHARS`, `EtlState.record_approval`, `EtlState.approval`, `GateFixture`, `operator_cli`, `row`.
- Produces:
  - `etl.approval`:
    - `APPROVAL_OUTCOMES` and `class ApprovalRefused(ValueError)`
    - `ApprovalOutcome(Record)` with fields `outcome: str`, `publication: PublicationResult | None`, `approval: WithdrawalApproval | None` and `error: Error | None`
    - `load_candidate(quarter, generation_id, objects) -> Candidate`
    - `approve(quarter: str, generation_id: str, quarterly_sha256: str, approver: str, objects, state: EtlState, *, observer=None) -> ApprovalOutcome`
  - Observer points: `approval.before_pointer`, `approval.cas_lost` and `approval.after_pointer`.
  - Exit codes: `EXIT_CODES['approval_refused'] == 2` and `EXIT_CODES['approval_stale'] == 11`.
  - CLI `approve`:
    - stdout carries the canonical keys `outcome, quarter, generation_id, approval_ref, approval, publication, error`;
    - one stderr line has event `withdrawal_approval`;
    - a configuration error exits 2 and writes nothing to stdout.
  - `cli._operator_main(args, event: str | None, empty: dict, run: Callable[[ObjectStore, EtlState], dict]) -> int`, reused by Tasks 5 and 6. It loads the config (exit 2, nothing on stdout, on a configuration error), opens and closes the stores, merges `run`'s result over `empty`, maps any exception to `state_conflict` or `internal_error` (exit 9), writes the optional stderr event line, prints canonical JSON and returns the outcome's exit code.

- [ ] **Step 1: Write the failing tests**

In `packages/sec-edgar-ingest/tests/test_etl_approval.py`, add these imports below the existing ones:

```python
from support import Faults
from sec_edgar_ingest.etl.approval import approve
```

Add this class before the `if __name__ == '__main__':` block:

```python
class ApproveTests(GateFixture):
    def approve(self, candidate, quarterly_sha256, approver='Lowell Mason', **kwargs):
        return approve('2026Q4', candidate.manifest.generation_id, quarterly_sha256, approver,
                       self.objects, self.state, **kwargs)

    def assert_unwritten(self, candidate):
        self.assertIsNone(self.state.approval(candidate.manifest.generation_id))
        with self.assertRaises(FileNotFoundError):
            self.objects.read(approval_ref('2026Q4', candidate.manifest.generation_id))

    def moved_base(self):
        """A clear closed-quarter update (no withdrawal) that publishes over the candidate's base."""
        return self.observation(rows=row('Updated') + row(number=2), seconds=2)

    def test_approve_activates_the_exact_candidate_once(self):
        _, revised, candidate = self.gated()
        result = self.approve(candidate, revised.snapshot.sha256)
        self.assertEqual((result.outcome, result.publication.outcome, result.publication.generation_id),
                         ('success', 'published', candidate.manifest.generation_id))
        self.assertEqual(result.approval, self.state.approval(candidate.manifest.generation_id))
        self.assertEqual(result.approval, read_approval(candidate, self.objects))
        self.assertEqual(self.capture().generation_id, candidate.manifest.generation_id)
        self.assertEqual(self.rows(), [(1, 'Example')])
        pointer = self.state.pointer('2026Q4')
        again = self.approve(candidate, revised.snapshot.sha256, 'Someone Else')
        self.assertEqual((again.outcome, again.approval.approver), ('unchanged', 'Lowell Mason'))
        self.assertEqual(self.state.pointer('2026Q4'), pointer)

    def test_refusals_write_nothing(self):
        base, revised, candidate = self.gated()
        generation = candidate.manifest.generation_id
        cases = {
            'wrong quarterly hash': ('2026Q4', generation, '0' * 64, 'Lowell Mason'),
            'clear generation': ('2026Q4', base.generation_id, revised.snapshot.sha256, 'Lowell Mason'),
            'missing generation': ('2026Q4', 'f' * 64, revised.snapshot.sha256, 'Lowell Mason'),
            'invalid quarter': ('2026Q5', generation, revised.snapshot.sha256, 'Lowell Mason'),
            'invalid hash text': ('2026Q4', generation, 'not-a-hash', 'Lowell Mason'),
            'invalid approver': ('2026Q4', generation, revised.snapshot.sha256, 'two\nlines'),
        }
        pointer = self.state.pointer('2026Q4')
        for label, args in cases.items():
            with self.subTest(label):
                result = approve(*args, self.objects, self.state)
                self.assertEqual((result.outcome, result.error.code), ('approval_refused', 'approval_refused'))
                self.assertIsNone(result.publication)
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assert_unwritten(candidate)

    def test_a_moved_base_makes_the_candidate_stale_without_writes(self):
        _, revised, candidate = self.gated()
        self.assertEqual(self.publish(self.moved_base()).outcome, 'published')
        pointer = self.state.pointer('2026Q4')
        result = self.approve(candidate, revised.snapshot.sha256)
        self.assertEqual((result.outcome, result.error.code), ('approval_stale', 'approval_stale'))
        self.assertEqual(result.error.details['base_generation_id'], candidate.manifest.base_generation_id)
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assert_unwritten(candidate)

    def test_the_first_stored_approval_wins(self):
        _, revised, candidate = self.gated()
        first = approval_for(candidate, 'First Approver', APPROVED_AT)
        self.objects.put_once(approval_ref('2026Q4', candidate.manifest.generation_id),
                              canonical_json(first.to_mapping()))
        result = self.approve(candidate, revised.snapshot.sha256)
        self.assertEqual((result.outcome, result.approval), ('success', first))
        self.assertEqual(self.state.approval(candidate.manifest.generation_id), first)

    def test_a_lost_pointer_race_rereads_to_unchanged(self):
        _, revised, candidate = self.gated()
        faults = Faults()
        faults.at('approval.before_pointer', lambda: self.assertEqual(
            self.approve(candidate, revised.snapshot.sha256, 'Second Approver').outcome, 'success'))
        result = self.approve(candidate, revised.snapshot.sha256, observer=faults)
        self.assertEqual((result.outcome, result.publication.conflicts), ('unchanged', 1))
        self.assertEqual(result.approval.approver, 'Lowell Mason')

    def test_a_lost_pointer_race_to_a_new_generation_is_stale(self):
        _, revised, candidate = self.gated()
        moved = self.moved_base()
        faults = Faults()
        faults.at('approval.before_pointer', lambda: self.assertEqual(self.publish(moved).outcome, 'published'))
        result = self.approve(candidate, revised.snapshot.sha256, observer=faults)
        self.assertEqual(result.outcome, 'approval_stale')
        self.assertNotEqual(self.capture().generation_id, candidate.manifest.generation_id)

    def test_after_approval_only_a_new_quarterly_snapshot_changes_membership(self):
        _, revised, candidate = self.gated()
        self.assertEqual(self.approve(candidate, revised.snapshot.sha256).outcome, 'success')
        self.publish(self.observation(period='2026-10-02', kind='daily', rows=row(number=2)))
        self.assertEqual(self.rows(), [(1, 'Example')])
        returned = self.observation(rows=row() + row('Returned', number=2), seconds=2)
        self.assertEqual(self.publish(returned).outcome, 'published')
        self.assertEqual(read_manifest(self.capture(), self.objects).added, 1)
        self.assertEqual(self.rows(), [(1, 'Example'), (2, 'Returned')])
        renamed = self.observation(rows=row('Renamed'), seconds=3)
        gated = self.publish(renamed)
        self.assertEqual(gated.outcome, 'awaiting_approval')
        later = self.candidate(gated.candidate_ref)
        self.assertEqual(self.approve(later, revised.snapshot.sha256).outcome, 'approval_refused')
        self.assertEqual(self.approve(later, renamed.snapshot.sha256).outcome, 'success')
        self.assertEqual(self.rows(), [(1, 'Renamed')])

    def test_approve_cli_maps_named_outcomes_to_exit_codes(self):
        _, revised, candidate = self.gated()
        generation = candidate.manifest.generation_id
        command = ('approve', '--config', str(self.write_config()), '--state-dir', str(self.root),
                   '--quarter', '2026Q4', '--generation', generation, '--approver', 'Lowell Mason')
        code, message, _ = operator_cli(*command, '--quarterly-sha256', '0' * 64)
        self.assertEqual((code, message['outcome'], message['approval_ref']), (2, 'approval_refused', None))
        code, message, events = operator_cli(*command, '--quarterly-sha256', revised.snapshot.sha256)
        self.assertEqual((code, message['outcome']), (0, 'success'))
        self.assertEqual((message['quarter'], message['generation_id']), ('2026Q4', generation))
        self.assertEqual(message['approval_ref'], approval_ref('2026Q4', generation))
        self.assertEqual(message['approval']['approver'], 'Lowell Mason')
        self.assertEqual(json.loads(events.splitlines()[-1])['event'], 'withdrawal_approval')
        code, message, _ = operator_cli(*command, '--quarterly-sha256', revised.snapshot.sha256)
        self.assertEqual((code, message['outcome']), (0, 'unchanged'))
        missing = ('approve', '--config', str(self.root / 'missing.json'), '--quarter', '2026Q4',
                   '--generation', generation, '--quarterly-sha256', revised.snapshot.sha256, '--approver', 'x')
        self.assertEqual(operator_cli(*missing)[:2], (2, None))

    def test_approve_cli_reports_a_stale_candidate_with_exit_11(self):
        _, revised, candidate = self.gated()
        self.assertEqual(self.publish(self.moved_base()).outcome, 'published')
        code, message, _ = operator_cli(
            'approve', '--config', str(self.write_config()), '--state-dir', str(self.root),
            '--quarter', '2026Q4', '--generation', candidate.manifest.generation_id,
            '--quarterly-sha256', revised.snapshot.sha256, '--approver', 'Lowell Mason')
        self.assertEqual((code, message['outcome']), (11, 'approval_stale'))
```

In `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`, add two entries to the `expected` table of `test_all_exit_outcomes_have_explicit_member_and_coverage_status`, after `'awaiting_approval'`:

```python
            'approval_refused': ('failed', 'incomplete'),
            'approval_stale': ('failed', 'incomplete'),
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the focused command with `-p 'test_etl_approval.py'`.
Expected: `ModuleNotFoundError: No module named 'sec_edgar_ingest.etl.approval'`. The new top-level import fails the whole module, Task 1's tests included, until Step 3.

Run it with `-p 'test_workflow_contracts.py' -k all_exit_outcomes`.
Expected: an `AssertionError` from the set comparison.

- [ ] **Step 3: Implement the operation**

Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py`:

```python
"""Operator approval of one exact gated withdrawal candidate, committed by pointer CAS."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from ..models import Error, Record, canonical_json, quarter_value, require_hash, validate_record_fields
from ..storage.contracts import AlreadyExists, BoundaryObserver, CAS_ATTEMPTS, Conflict, ObjectStore, observe
from .contracts import (MAX_OPERATOR_CHARS, Candidate, GenerationCapture, PublicationResult, WithdrawalApproval,
                        require_line)
from .manifest import (approval_for, approval_ref, gate_ref, generation_base, read_approval, read_manifest,
                       validate_candidate)
from .publication import pointer_value
from .reader import capture_from_pointer
from .state import EtlState

APPROVAL_OUTCOMES = ('success', 'unchanged', 'approval_refused', 'approval_stale')


class ApprovalRefused(ValueError):
    """The request does not name a valid gated candidate; nothing was written."""


@dataclass(frozen=True, slots=True)
class ApprovalOutcome(Record):
    outcome: str
    publication: PublicationResult | None
    approval: WithdrawalApproval | None
    error: Error | None

    def __post_init__(self):
        validate_record_fields(self)
        if self.outcome not in APPROVAL_OUTCOMES:
            raise ValueError('unsupported approval outcome')
        committed = self.outcome in ('success', 'unchanged')
        if committed != (self.publication is not None and self.approval is not None and self.error is None):
            raise ValueError('approval outcome evidence differs from its outcome')
        if not committed and (self.error is None or self.error.code != self.outcome):
            raise ValueError('refused or stale approval requires its matching error')


def _now() -> datetime:
    """Patchable UTC approval clock."""
    return datetime.now(timezone.utc)


def _refused(message: str) -> ApprovalOutcome:
    return ApprovalOutcome('approval_refused', None, None, Error('approval_refused', message, False, None, {}))


def _committed(outcome: str, candidate: Candidate, approval: WithdrawalApproval, conflicts: int) -> ApprovalOutcome:
    publication = PublicationResult(candidate.manifest.quarter, 'published' if outcome == 'success' else 'unchanged',
                                    candidate.manifest.generation_id, candidate.manifest_ref, None, conflicts)
    return ApprovalOutcome(outcome, publication, approval, None)


def load_candidate(quarter: str, generation_id: str, objects: ObjectStore) -> Candidate:
    """Read one gated candidate from its exact immutable address and validate all of its evidence."""
    manifest_ref = generation_base(quarter, generation_id) + '/manifest.json'
    try:
        body = objects.read(manifest_ref)
    except FileNotFoundError as error:
        raise ApprovalRefused('no generation exists at the exact candidate address') from error
    capture = GenerationCapture(quarter, generation_id, manifest_ref, hashlib.sha256(body).hexdigest(), len(body))
    manifest = read_manifest(capture, objects)
    if manifest.gate != 'awaiting_approval':
        raise ApprovalRefused('generation is not an awaiting-approval candidate')
    candidate = Candidate(manifest, manifest_ref, capture.manifest_sha256, capture.manifest_bytes, gate_ref(manifest))
    validate_candidate(candidate, objects)
    return candidate


def _store_approval(approval: WithdrawalApproval, candidate: Candidate, objects: ObjectStore) -> WithdrawalApproval:
    try:
        objects.put_once(approval_ref(approval.quarter, approval.generation_id), canonical_json(approval.to_mapping()))
    except Conflict:
        pass  # The first approval wins; read_approval re-validates its exact binding.
    return read_approval(candidate, objects)


def approve(quarter: str, generation_id: str, quarterly_sha256: str, approver: str,
            objects: ObjectStore, state: EtlState, *, observer: BoundaryObserver | None = None) -> ApprovalOutcome:
    try:
        quarter_value(quarter)
        require_hash(generation_id, 'generation_id')
        require_hash(quarterly_sha256, 'quarterly_sha256')
        require_line(approver, 'approver', MAX_OPERATOR_CHARS)
    except ValueError as error:
        return _refused(str(error))
    try:
        candidate = load_candidate(quarter, generation_id, objects)
    except ApprovalRefused as error:
        return _refused(str(error))
    if candidate.manifest.membership_source.snapshot.sha256 != quarterly_sha256:
        return _refused('quarterly hash differs from the candidate membership snapshot')
    pending = approval_for(candidate, approver, _now())
    for conflicts in range(CAS_ATTEMPTS):
        current = state.pointer(quarter)
        active = None if current is None else capture_from_pointer(current).generation_id
        if active == generation_id:
            stored = read_approval(candidate, objects)
            state.record_approval(stored)
            return _committed('unchanged', candidate, stored, conflicts)
        if active != candidate.manifest.base_generation_id:
            return ApprovalOutcome('approval_stale', None, None, Error(
                'approval_stale', 'candidate base generation is no longer active', False, None,
                {'active_generation_id': active, 'base_generation_id': candidate.manifest.base_generation_id}))
        stored = _store_approval(pending, candidate, objects)
        state.record_approval(stored)
        observe(observer, 'approval.before_pointer')
        try:
            state.commit_pointer(quarter, pointer_value(candidate), current)
        except (AlreadyExists, Conflict):
            observe(observer, 'approval.cas_lost')
            continue
        observe(observer, 'approval.after_pointer')
        return _committed('success', candidate, stored, conflicts)
    raise Conflict('approval exhausted conditional pointer races')
```

Corrupt evidence is not caught here. Examples are an invalid manifest, a non-canonical approval and a gate-record mismatch. Each raises `ValueError` or `Conflict`, which the CLI reports as `state_conflict`.

- [ ] **Step 4: Add the exit codes**

In `results.py`, replace `EXIT_CODES` with:

```python
EXIT_CODES = {
    'success': 0, 'no_new_sources': 0, 'unchanged': 0, 'configuration': 2,
    'approval_refused': 2, 'discovery_failed': 3, 'incomplete': 3, 'pending': 4,
    'retry_exhausted': 5, 'deferred': 5, 'throttled': 5,
    'access_blocked': 6, 'quarantined': 7, 'invalid_source': 7,
    'ownership_lost': 8, 'state_conflict': 9, 'internal_error': 9,
    'publication_conflict': 9, 'awaiting_approval': 10, 'approval_stale': 11,
}
```

- [ ] **Step 5: Add the `approve` CLI**

In `cli.py`, add these imports beside the other `.etl` imports:

```python
from .etl.approval import approve
from .etl.manifest import approval_ref
```

In `_parser`, insert this code after the `for command in (...)` loop, just before `return parser`:

```python
    sub = commands.add_parser('approve')
    for name in ('config', 'quarter', 'generation', 'quarterly-sha256', 'approver'):
        sub.add_argument('--' + name, required=True)
    sub.add_argument('--state-dir')
```

Add these helpers immediately before `def main`:

```python
def _operator_settings(args) -> Settings:
    settings = load_config(Path(args.config))
    if settings.storage.backend == 'azure' and args.state_dir:
        raise ValueError('state directory is fixture-only')
    return settings


def _operator_main(args, event: str | None, empty: dict[str, object], run) -> int:
    """Run one operator command on the configured stores and print its canonical result."""
    try:
        settings = _operator_settings(args)
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(canonical_json({'outcome': 'configuration', 'error': str(error)}).decode() + '\n')
        return 2
    opened = ()
    try:
        opened = open_stores(settings, base_path=Path(args.state_dir) if args.state_dir else None)
        store, objects, _ = opened
        value = {**empty, **run(objects, EtlState(store))}
    except Exception as exception:
        outcome = ('state_conflict' if isinstance(exception, (Conflict, ValueError, OSError, KeyError))
                   else 'internal_error')
        value = {**empty, 'outcome': outcome, 'error': Error(
            outcome, str(exception), False, None, {'type': type(exception).__name__}).to_mapping()}
    finally:
        for resource in reversed(opened):
            if hasattr(resource, 'close'):
                resource.close()
    body = to_mapping_value(value)
    if event is not None:
        sys.stderr.write(canonical_json({'event': event, 'fields': body}).decode() + '\n')
    sys.stdout.write(canonical_json(body).decode() + '\n')
    return exit_code(value['outcome'])


def _approve_main(args) -> int:
    def run(objects, state):
        result = approve(args.quarter, args.generation, args.quarterly_sha256, args.approver, objects, state)
        ref = None if result.approval is None else approval_ref(result.approval.quarter, result.approval.generation_id)
        return {**result.to_mapping(), 'approval_ref': ref}
    return _operator_main(args, 'withdrawal_approval',
                          {'quarter': args.quarter, 'generation_id': args.generation, 'approval_ref': None,
                           'approval': None, 'publication': None, 'error': None}, run)
```

Each operator command supplies only its `run` callback and the keys its output always carries; `_operator_main` owns configuration, store lifetime, failure mapping and output.

In `main`, route `approve` before `_validate`, which reads acquisition-only arguments. Do this right after the existing workflow routing:

```python
    if args.command in ('backfill', 'daily'):
        return _workflow_main(args)
    if args.command == 'approve':
        return _approve_main(args)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run the focused command once for each pattern: `test_etl_approval.py`, `test_workflow_contracts.py` and `test_workflow_cli.py`.
Expected: `OK` each time.

- [ ] **Step 7: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/approval.py packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_etl_approval.py packages/sec-edgar-ingest/tests/test_workflow_contracts.py
git commit -m "feat(etl): approve exact gated withdrawals by pointer CAS"
```

---

### Task 3: The `reconcile` workflow command and the run-level gate outcome

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py` (new constants after `FORMAT_VERSION`; `summarize` at lines 193-198; `workflow_path` at line 206)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/checked.py:70,393` (plus one import)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py:156-161`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py:190-191`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py:30,70,76,355-358,442`
- Modify: `packages/sec-edgar-ingest/tests/support_workflows.py:77`
- Create: `packages/sec-edgar-ingest/tests/support_reconcile.py`
- Create: `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py`
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_contracts.py` (two new tests in `CoverageTests`)
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_runner.py:353`

**Interfaces:**
- Consumes: shipped `run_workflow`, `select_work`, `summarize`, `member_status`, `Dispatcher`, `CommandHarness`, `quarter_pack`, `replace_pack_body`, `idx`, `read_workflow_result`.
- Produces:
  - `workflows.contracts.WORKFLOW_COMMANDS = ('backfill', 'daily', 'reconcile')`.
  - `workflows.contracts.WORKFLOW_PRIORITY = {'backfill': 'backfill', 'daily': 'daily', 'reconcile': 'reconciliation'}`.
  - `summarize` returns `awaiting_approval` whenever every unresolved member outcome is `awaiting_approval` and there is no gap or failed source, even beside completed sources (spec §3).
  - The validator conflict message `selection discovery refresh differs from its workflow command`.
  - `support_reconcile`:
    - constants `Q3_URL`, `Q4_URL`, `A`, `B`, `C`, `X`, `Y`
    - `quarterly(rows) -> bytes` and `sha(rows) -> str`
    - `ReconcileFixture`, with `harness(q3_rows, q4_rows=(X, Y)) -> CommandHarness`, `run_phase(h, command, run, q3_rows=None, q4_rows=(X, Y)) -> (code, message, WorkflowResult | None)`, `names(h, quarter) -> [company_name]` and `candidates(h) -> [Candidate]`.

- [ ] **Step 1: Create the reconcile fixture**

Create `packages/sec-edgar-ingest/tests/support_reconcile.py`:

```python
"""Fixture packs and a command harness for reconcile workflow tests."""
from network_guard import install
install()

import hashlib
import tempfile
import unittest
from pathlib import Path

from support import fixture_settings
from support_workflows import BASE, CommandHarness, idx, quarter_pack, replace_pack_body
from sec_edgar_ingest.etl.contracts import Candidate
from sec_edgar_ingest.workflows.results import read_workflow_result

Q3_URL = BASE + 'full-index/2026/QTR3/master.zip'
Q4_URL = BASE + 'full-index/2026/QTR4/master.zip'
A = ('123456', 'A', '10-K', '2026-07-01', 'edgar/data/123456/0000123456-26-000031.txt')
B = ('123456', 'B', '10-K', '2026-07-02', 'edgar/data/123456/0000123456-26-000032.txt')
C = ('123456', 'C', '10-K', '2026-07-03', 'edgar/data/123456/0000123456-26-000033.txt')
X = ('123456', 'X', '10-K', '2026-10-01', 'edgar/data/123456/0000123456-26-000041.txt')
Y = ('123456', 'Y', '10-K', '2026-10-02', 'edgar/data/123456/0000123456-26-000042.txt')


def quarterly(rows):
    return idx(rows, 'quarterly')


def sha(rows):
    return hashlib.sha256(quarterly(rows)).hexdigest()


class ReconcileFixture(unittest.TestCase):
    """On the harness's pinned 2026-10-07, 2026Q3 is closed and 2026Q4 is open."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packs = 0

    def pack(self, q3_rows, q4_rows):
        # Each phase gets a fresh pack: a new manifest hash restarts every response cursor.
        self.packs += 1
        pack = quarter_pack(self.root / f'pack-{self.packs}', ('2026Q3', '2026Q4'), empty_daily=True)
        replace_pack_body(pack, Q3_URL, quarterly(q3_rows))
        replace_pack_body(pack, Q4_URL, quarterly(q4_rows))
        return pack

    def harness(self, q3_rows, q4_rows=(X, Y)):
        settings = fixture_settings(backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
            http={'retry_base_seconds': 0.001, 'retry_cap_seconds': 0.001},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        h = CommandHarness(self.root, self.pack(q3_rows, q4_rows), settings)
        self.addCleanup(h.close)
        return h

    def run_phase(self, h, command, run, q3_rows=None, q4_rows=(X, Y)):
        if q3_rows is not None:
            h.pack = self.pack(q3_rows, q4_rows)
        code, message = h.invoke(command, run=run)
        report = (None if message.get('result_ref') is None
                  else read_workflow_result(message['result_ref'], h.store, h.objects))
        return code, message, report

    def names(self, h, quarter):
        return [value['company_name'] for value in h.capture(quarter)[1]]

    def candidates(self, h):
        return [Candidate.from_mapping(row.to_mapping()['value']) for row in h.store.scan('Candidate', {})]
```

In `packages/sec-edgar-ingest/tests/support_workflows.py`, change line 77 so that `reconcile` receives the fixture pack:

```python
        if command in ('discover', 'collect', 'backfill', 'daily', 'reconcile'):
```

- [ ] **Step 2: Write the failing tests**

Create `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py`:

```python
"""Offline reconcile workflow: shared runner, refreshed quarterly selection, corrections and gates."""
from network_guard import install
install()

import unittest
from unittest.mock import patch

from support_reconcile import A, B, C, X, ReconcileFixture
from sec_edgar_ingest.etl.manifest import read_manifest
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.workflows.checked import Dispatcher


class ReconcileWorkflowTests(ReconcileFixture):
    def baseline(self):
        h = self.harness((A, B))
        code, _, report = self.run_phase(h, 'backfill', 'base')
        self.assertEqual((code, report.outcome), (0, 'success'), h.calls[-1])
        return h, report

    def test_unchanged_reconcile_refreshes_through_the_shared_runner(self):
        h, baseline = self.baseline()
        pointers = {quarter: EtlState(h.store).pointer(quarter) for quarter in ('2026Q3', '2026Q4')}
        code, message, report = self.run_phase(h, 'reconcile', 'same', (A, B))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        self.assertEqual(message['result_ref'], 'runs/sec/same/reconcile/a/result.json')
        self.assertEqual((report.context.command, report.context.priority), ('reconcile', 'reconciliation'))
        self.assertEqual(report.requested_quarters, ('2026Q3', '2026Q4'))
        self.assertEqual((report.counts['published_quarters'], report.counts['unchanged_quarters']), (0, 2))
        calls = report.to_mapping()['intent']['child_calls']
        discovery = calls[0]
        self.assertEqual((discovery['intent']['mode'], discovery['intent']['refresh'],
                          discovery['intent']['discovery_id'], discovery['context']['priority']),
                         ('quarterly', True, 'workflow-reconcile-same', 'backfill'))
        self.assertEqual({call['context']['command'] for call in calls},
                         {'discover', 'collect', 'transform', 'publish'})
        self.assertIs(baseline.to_mapping()['intent']['child_calls'][0]['intent']['refresh'], False)
        self.assertEqual({quarter: EtlState(h.store).pointer(quarter) for quarter in pointers}, pointers)
        with self.assertRaises(SystemExit):
            h.invoke('reconcile', ('--refresh',), run='public-refresh')

    def test_corrections_update_and_add_while_open_quarter_absence_is_retained(self):
        h, _ = self.baseline()
        revised = ('123456', 'A Revised', *A[2:])
        code, _, report = self.run_phase(h, 'reconcile', 'fix', (revised, B, C), (X,))
        self.assertEqual((code, report.outcome), (0, 'success'), h.calls[-1])
        closed = read_manifest(h.capture('2026Q3')[0], h.objects)
        self.assertEqual((closed.updated, closed.added, closed.withdrawn, closed.gate), (1, 1, 0, 'clear'))
        self.assertEqual(self.names(h, '2026Q3'), ['A Revised', 'B', 'C'])
        opened = read_manifest(h.capture('2026Q4')[0], h.objects)
        self.assertEqual((opened.quarter_mode, opened.unresolved_absence, opened.withdrawn), ('open', 1, 0))
        self.assertEqual(self.names(h, '2026Q4'), ['X', 'Y'])

    def test_closed_withdrawal_beside_an_unchanged_quarter_awaits_approval(self):
        h, _ = self.baseline()
        before = EtlState(h.store).pointer('2026Q3')
        code, _, report = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual((code, report.outcome), (10, 'awaiting_approval'), h.calls[-1])
        self.assertEqual((report.counts['awaiting_approval_quarters'], report.counts['pending_sources'],
                          report.counts['complete_sources']), (1, 1, 1))
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])

    def test_invalid_correction_keeps_the_prior_generation_and_names_its_quarter(self):
        h, _ = self.baseline()
        before = EtlState(h.store).pointer('2026Q3')
        conflict = ('123456', 'Conflict', *A[2:])
        code, _, report = self.run_phase(h, 'reconcile', 'invalid', (A, conflict, B))
        self.assertEqual((code, report.outcome), (3, 'incomplete'), h.calls[-1])
        self.assertEqual(report.counts['quarantined_sources'], 1)
        self.assertEqual([member.source.period for member in report.members if member.quarantined], ['2026Q3'])
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), before)

    def test_selection_requires_refresh_exactly_for_reconcile(self):
        execute = Dispatcher.execute

        def flipped(dispatcher, command, step_id, settings, flags):
            if command == 'discover':
                flags = (tuple(flag for flag in flags if flag != '--refresh') if '--refresh' in flags
                         else (*flags, '--refresh'))
            return execute(dispatcher, command, step_id, settings, flags)

        h = self.harness((A, B))
        with patch.object(Dispatcher, 'execute', flipped):
            for command in ('backfill', 'reconcile'):
                with self.subTest(command=command):
                    code, message = h.invoke(command, run='flipped-' + command)
                    self.assertEqual((code, message['outcome']), (9, 'state_conflict'), h.calls[-1])
                    self.assertIn('refresh differs from its workflow command', h.calls[-1]['stderr'])


if __name__ == '__main__':
    unittest.main()
```

In `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`, add these two methods to `CoverageTests`. The module already imports `replace`, `Error`, `fixture_context`, `fixture_source`, `summarize` and `workflow_path`. The completed and gated members need distinct sources and member IDs; otherwise `summarize` groups them as one source and the test never puts a gate beside completed work.

```python
    def test_reconcile_is_a_workflow_command_with_reconciliation_priority(self):
        from sec_edgar_ingest.workflows.contracts import WORKFLOW_COMMANDS, WORKFLOW_PRIORITY
        context = fixture_context(command='reconcile', priority='reconciliation')
        self.assertEqual(workflow_path(context), 'runs/sec/fixture-run/reconcile/fixture-attempt/result.json')
        self.assertEqual(WORKFLOW_COMMANDS, ('backfill', 'daily', 'reconcile'))
        self.assertEqual(WORKFLOW_PRIORITY, {'backfill': 'backfill', 'daily': 'daily', 'reconcile': 'reconciliation'})
        with self.assertRaises(ValueError):
            workflow_path(fixture_context(command='publish'))

    def test_gate_only_unresolved_work_is_awaiting_approval_beside_completed_sources(self):
        done = replace(self.member(), member_id='b' * 64, source=fixture_source('2015Q2'))
        gated = self.member('awaiting_approval', (self.publication('awaiting_approval'),))
        for command in ('backfill', 'daily', 'reconcile'):
            with self.subTest(command=command):
                outcome, counts = summarize((done, gated), (), 1, 0, command)
                self.assertEqual((outcome, counts['complete_sources'], counts['pending_sources'],
                                  counts['awaiting_approval_quarters']), ('awaiting_approval', 1, 1, 1))
        deferred = replace(self.member('deferred'), member_id='c' * 64, source=fixture_source('2015Q3'))
        self.assertEqual(summarize((done, gated, deferred), (), 1)[0], 'incomplete')
        reverted = Error('source_reverted', 'older bytes', True, done.source.source_id, {'quarter': '2015Q2'})
        self.assertEqual(summarize((done, gated), (reverted,), 1)[0], 'incomplete')
        failed = replace(self.member('invalid_source'), member_id='c' * 64, source=fixture_source('2015Q3'),
                         transformed=False, quarantined=True)
        self.assertEqual(summarize((done, gated, failed), (), 1)[0], 'incomplete')
```

In `packages/sec-edgar-ingest/tests/test_workflow_runner.py`, change line 353 of `test_gate_only_and_mixed_gate_progress_preserve_current_pointer`. Under the amended reducer, both the gate-only and the mixed run await approval:

```python
                    self.assertEqual(report.outcome, 'awaiting_approval')
```

- [ ] **Step 3: Run the tests to verify they fail**

Run the focused command with `-p 'test_reconcile_workflow.py'`.
Expected: every test fails. `main` sees `reconcile` as an invalid argparse choice and raises `SystemExit: 2`.

Run it with `-p 'test_workflow_contracts.py' -k awaiting_approval_beside`.
Expected: an `AssertionError` showing `'incomplete'` where `'awaiting_approval'` was expected.

- [ ] **Step 4: Implement the command**

In `workflows/contracts.py`, add after `FORMAT_VERSION = 'sec-workflow-result-v1'`:

```python
WORKFLOW_COMMANDS = ('backfill', 'daily', 'reconcile')
WORKFLOW_PRIORITY = {'backfill': 'backfill', 'daily': 'daily', 'reconcile': 'reconciliation'}
```

In `workflow_path`, change the first check to:

```python
    if context.command not in WORKFLOW_COMMANDS:
        raise ValueError('workflow command required')
```

In `summarize`, replace the two `incomplete` checks and the `pending` branch (from `if gaps or (states['complete'] ...` through the `awaiting_approval if outcomes == {'awaiting_approval'}` return) with:

```python
    if gaps or states['failed']:
        return 'incomplete', counts
    if states['pending']:
        unresolved = {member.outcome for member in members if member_status(member.outcome) == 'pending'}
        # Gate-only unresolved work is the distinct gated outcome, even beside completed sources.
        if unresolved == {'awaiting_approval'}:
            return 'awaiting_approval', counts
        return ('incomplete' if states['complete'] else 'pending'), counts
```

Every other path is unchanged. A gap or failed source is still `incomplete`. Other pending work is still `incomplete` beside completed sources and `pending` without them, and a gate with no completed source is still `awaiting_approval`.

In `workflows/checked.py`, add the import `from .contracts import WORKFLOW_COMMANDS`; `workflows/contracts.py` does not import `checked`. In `child_attempt_id`, use:

```python
    if workflow_command not in WORKFLOW_COMMANDS or command not in CHILD_COMMANDS:
```

In `Dispatcher.__init__`, use:

```python
        if context.command not in WORKFLOW_COMMANDS or context.pinned_on is None:
```

In `workflows/runner.py`, replace the discovery dispatch in `select_work` (the `mode = ...` line through the `dispatcher.execute('discover', ...)` call) with:

```python
    mode = 'daily' if context.command == 'daily' else 'quarterly'
    flags = ('--mode', mode, '--discovery-id', 'workflow-' + context.command + '-' + context.run_id)
    if context.command == 'reconcile':
        flags += ('--refresh',)  # Reconciliation differs only by re-fetching every listed source.
    discovery_call = discovery_error = parent_ref = parent = None
    halted = False
    try:
        child = dispatcher.execute('discover', 'discover', settings, flags)
```

In `workflows/results.py`, inside `_validate_selection`, insert this immediately after the `raise Conflict('selection discovery call belongs to another workflow')` check:

```python
        if call['intent']['refresh'] is not (context.command == 'reconcile'):
            raise Conflict('selection discovery refresh differs from its workflow command')
```

In `cli.py`, apply these changes:

1. Import `WORKFLOW_COMMANDS` and `WORKFLOW_PRIORITY` beside `workflow_path`:

   ```python
   from .workflows.contracts import WORKFLOW_COMMANDS, WORKFLOW_PRIORITY, workflow_path
   ```

2. In `_parser`, change the loop header and the `--fixture-pack` condition:

   ```python
       for command in ('discover', 'collect', 'transform', 'publish', *WORKFLOW_COMMANDS):
   ```

   ```python
           if command in ('discover', 'collect', *WORKFLOW_COMMANDS):
   ```

3. In `_workflow_context`, pass the command's priority:

   ```python
   def _workflow_context(args, settings, today, deadline, started, pinned):
       context = RunContext(args.run_id, args.execution_id, args.command, args.attempt_id,
           settings.worker.image_digest, settings.etl.parser_version, settings.etl.schema_version,
           settings.config_sha256, started, deadline, WORKFLOW_PRIORITY[args.command])
       return pin_context(settings, context, today or pinned or started.date())
   ```

4. In `main`, use:

   ```python
       if args.command in WORKFLOW_COMMANDS:
           return _workflow_main(args)
   ```

- [ ] **Step 5: Run the tests to verify they pass**

Run the focused command with `-p 'test_reconcile_workflow.py'`, then with `-p 'test_workflow_*.py'`. The second run covers every shipped workflow test file, because `WorkflowResult` and the report validator (`workflows/results.py:504`) re-derive each stored outcome through `summarize`.
Expected: `OK` both times. The only shipped assertion this task changes is `test_workflow_runner.py:353`, edited in Step 2. If any other shipped test fails, stop and report it to the owner; do not edit its expectation.

Compatibility note (spec §3): a stored `sec-workflow-result-v1` report re-validates its outcome with the amended reducer. A Stage 4-era report whose run had a gate beside completed sources was written as `incomplete`, so it no longer validates, and replaying that exact attempt is refused as `state_conflict`. No such report exists outside temporary test state: the retained Stage 4 evidence holds only a gate-only report (outcome `awaiting_approval` under both reducers). The result format is therefore not bumped.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/checked.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/support_workflows.py packages/sec-edgar-ingest/tests/support_reconcile.py packages/sec-edgar-ingest/tests/test_reconcile_workflow.py packages/sec-edgar-ingest/tests/test_workflow_contracts.py packages/sec-edgar-ingest/tests/test_workflow_runner.py
git commit -m "feat(workflows): add reconcile and report gate-only work as awaiting approval"
```

---

### Task 4: Supersession and revert detection

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/completion.py` (new `accounts_for` before `LEGACY_PUBLISH_FORMAT`; checks at lines 408 and 778)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py` (imports; `run_workflow` line 109; new `source_revert_gaps` after `baseline_gaps`)
- Modify: `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py` (imports, two classes)

**Interfaces:**
- Consumes:
  - Task 2: `approve(...)`.
  - Task 3: `ReconcileFixture`, `sha`, `C`.
  - Task 1: `GateFixture`, `row`.
  - Shipped: `AcquisitionState.get_source` and `.snapshot`, and `capture_from_pointer`.
- Produces:
  - `workflows.completion.accounts_for(active: ObservationRef | None, ref: ObservationRef) -> bool`.
  - `workflows.runner.source_revert_gaps(results: tuple[MemberResult, ...], store, objects) -> tuple[Error, ...]`. Each gap has code `source_reverted`, is retryable, carries `source_id`, and has details `quarter, observed_sha256, observed_at, first_received_at, active_sha256, active_received_at, generation_id`.
  - Repair-resolution checks (`completion.py:666,730`) stay exact.

- [ ] **Step 1: Write the failing tests**

In `packages/sec-edgar-ingest/tests/test_reconcile_workflow.py`, extend the imports:

```python
from support_approval import GateFixture, row
from support_etl import etl_context
from support_reconcile import sha
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.transform import transform_member
from sec_edgar_ingest.workflows.completion import accounts_for
```

Add these classes before the `if __name__ == '__main__':` block:

```python
class SupersessionRuleTests(GateFixture):
    def test_accounts_for_exact_or_strictly_later_same_source_observation(self):
        first = self.observation(rows=row() + row(number=2))
        later = self.observation(rows=row(), seconds=1)
        daily = self.observation(period='2026-10-02', kind='daily', rows=row())
        self.assertTrue(accounts_for(first, first))
        self.assertTrue(accounts_for(later, first))
        self.assertFalse(accounts_for(first, later))
        self.assertFalse(accounts_for(None, first))
        self.assertFalse(accounts_for(daily, first))
        settings, context = etl_context('fixture-index-parser-v2', command='publish')
        upgraded = transform_member(later.source, later.snapshot, context, settings, self.objects, self.state)
        self.assertFalse(accounts_for(upgraded, first))


class SupersessionWorkflowTests(ReconcileFixture):
    def test_superseded_gated_member_completes_on_the_following_reconcile(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, first = self.run_phase(h, 'reconcile', 'gate-1', (A,))
        self.assertEqual((code, first.counts['awaiting_approval_quarters']), (10, 1), h.calls[-1])
        # Both gated members stay pending in this run whatever their processing order.
        code, _, second = self.run_phase(h, 'reconcile', 'gate-2', (A, C))
        self.assertEqual((code, second.outcome), (10, 'awaiting_approval'), h.calls[-1])
        latest = next(candidate for candidate in self.candidates(h)
                      if candidate.manifest.membership_source.snapshot.sha256 == sha((A, C)))
        approved = approve('2026Q3', latest.manifest.generation_id, sha((A, C)), 'Lowell Mason',
                           h.objects, EtlState(h.store))
        self.assertEqual(approved.outcome, 'success')
        code, _, report = self.run_phase(h, 'reconcile', 'after-approval', (A, C))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'C'])

    def test_revert_to_older_bytes_is_reported_not_published(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0)
        code, _, added = self.run_phase(h, 'reconcile', 'add', (A, B, C))
        self.assertEqual((code, added.outcome), (0, 'success'), h.calls[-1])
        active = EtlState(h.store).pointer('2026Q3')
        code, _, report = self.run_phase(h, 'reconcile', 'revert', (A, B))
        self.assertEqual((code, report.outcome), (3, 'incomplete'), h.calls[-1])
        gap, = [gap for gap in report.gaps if gap.code == 'source_reverted']
        self.assertTrue(gap.retryable)
        self.assertEqual((gap.details['quarter'], gap.details['observed_sha256'], gap.details['active_sha256']),
                         ('2026Q3', sha((A, B)), sha((A, B, C))))
        self.assertEqual(EtlState(h.store).pointer('2026Q3'), active)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B', 'C'])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the focused command with `-p 'test_reconcile_workflow.py'`.
Expected: the module fails to import with `ImportError: cannot import name 'accounts_for'`. The Task 3 tests in the same module fail with it; that is expected until Step 3.

- [ ] **Step 3: Implement the supersession rule**

In `workflows/completion.py`, add this function immediately before `LEGACY_PUBLISH_FORMAT = ...`:

```python
def accounts_for(active: ObservationRef | None, ref: ObservationRef) -> bool:
    """The active generation holds the member's exact observation or a strictly later one of its source."""
    if active is None:
        return False
    if active == ref:
        return True
    return (active.source == ref.source
            and (active.parser_version, active.schema_version) == (ref.parser_version, ref.schema_version)
            and active.snapshot.sha256 != ref.snapshot.sha256
            and active.snapshot.received_at > ref.snapshot.received_at)
```

In `validate_capture`, replace the membership check at line 408:

```python
        active = next((r for r in manifest.sources if r.source.source_id == source.source_id), None)
        if not accounts_for(active, ref):
            raise Conflict('captured publication source membership differs')
```

In `evaluate_member`, replace the membership check at line 778:

```python
            active = next((r for r in manifest.sources if r.source.source_id == source.source_id), None)
            if not accounts_for(active, ref):
                gaps.append(Error('publication_pending', 'affected quarter does not contain exact current observation', True, source.source_id, {'quarter': quarter}))
                continue
```

Leave the checks at lines 666 and 730 unchanged. They verify one specific repaired publication.

- [ ] **Step 4: Implement revert detection**

In `workflows/runner.py`, replace the import `from ..etl.reader import capture_quarter` with:

```python
from ..etl.manifest import read_manifest
from ..etl.reader import capture_from_pointer, capture_quarter
```

Next, in `run_workflow`, add a line after `gaps.extend(baseline_gaps(...))`:

```python
    gaps.extend(source_revert_gaps(tuple(results), store, objects))
```

Then add this function after `baseline_gaps`:

```python
def source_revert_gaps(results, store, objects) -> tuple[Error, ...]:
    """Report sources whose newest download repeats older bytes that the active generation supersedes.

    Identical bytes keep their first receipt, so receipt-ordered selection keeps the newer
    snapshot and the member publishes unchanged; without this gap the run would read as reconciled.
    """
    acquisition, state, found = AcquisitionState(store), EtlState(store), {}
    for result in results:
        quarters = sorted({q.quarter for q in result.quarters if q.outcome in ('published', 'unchanged')})
        identity = result.source.source_id
        row = acquisition.get_source(identity) if quarters else None
        if row is None:
            continue
        value = row.to_mapping()['value']
        latest, observed = value['latest_downloaded_snapshot'], value['latest_received_at']
        if latest is None or observed is None:
            continue
        observed_at = datetime.fromisoformat(observed)
        first = acquisition.snapshot(identity, latest).received_at
        for quarter in quarters:
            pointer = state.pointer(quarter)
            if pointer is None:
                continue
            capture = capture_from_pointer(pointer)
            manifest = read_manifest(capture, objects)
            active = next((ref for ref in manifest.sources if ref.source.source_id == identity), None)
            if active is None or active.snapshot.sha256 == latest:
                continue
            if first < active.snapshot.received_at < observed_at:
                found[identity, quarter] = Error(
                    'source_reverted', 'newest download repeats older bytes that the active generation supersedes',
                    True, identity, {'quarter': quarter, 'observed_sha256': latest, 'observed_at': observed,
                                     'first_received_at': first.isoformat(),
                                     'active_sha256': active.snapshot.sha256,
                                     'active_received_at': active.snapshot.received_at.isoformat(),
                                     'generation_id': capture.generation_id})
    return tuple(found[key] for key in sorted(found))
```

The reducer, as amended in Task 3, still turns any workflow gap into `incomplete`. The report validator requires only that the frozen selection gaps are present, so this added gap passes report validation.

- [ ] **Step 5: Run the tests to verify they pass**

Run the focused command with `-p 'test_reconcile_workflow.py'`, then with `-p 'test_workflow_*.py'`.
Expected: `OK` both times.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/completion.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/tests/test_reconcile_workflow.py
git commit -m "feat(workflows): complete superseded members and report source reverts"
```

---

### Task 5: The `candidates` listing and quarter history

**Files:**
- Create: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py` (new `retained_base`; `_base_manifest` at lines 171-186 uses it)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py` (import, `_parser`, `_candidates_main`, `main` routing)
- Create: `packages/sec-edgar-ingest/tests/test_etl_history.py`

**Interfaces:**
- Consumes:
  - Task 1: `read_approval`, `EtlState.approval`, `GateFixture`, `operator_cli` and `row`.
  - Task 2: `approve` and `_operator_main`.
  - Shipped: `capture_quarter`, `capture_from_pointer`, `iter_file_rows`, `gate_ref` and `gate_payload`.
- Produces:
  - `etl.manifest.retained_base(manifest: GenerationManifest, objects) -> GenerationCapture | None`: the exact base capture from `retained-base.json`, validated as the candidate validator already does. Both `_base_manifest` and `lineage` use it.
  - `etl.history.lineage(capture: GenerationCapture | None, objects) -> Iterator[tuple[GenerationCapture, GenerationManifest]]`, newest first, through each exact retained base; `None` yields nothing. Task 6 uses it for rollback targets.
  - `etl.history.quarter_history(quarter, objects, state) -> tuple[dict, ...]`. Entries run newest first, with keys `generation_id, base_generation_id, manifest_ref, quarter_mode, gate, row_count, added, updated, withdrawn, unresolved_absence, provenance_refreshed, membership_sha256, changes, approval`.
  - `etl.history.withdrawal_candidates(objects, state) -> tuple[dict, ...]`. Entries are sorted by quarter and then generation, with keys `quarter, generation_id, base_generation_id, quarterly_sha256, candidate_ref, changes, withdrawn, status, approved, latest_observed_sha256, latest_observed_at`.
  - CLI `candidates` prints `{"candidates": [...], "error": null, "outcome": "success"}` and exits 0. Failures exit 9 with `candidates: null`.

- [ ] **Step 1: Write the failing tests**

Create `packages/sec-edgar-ingest/tests/test_etl_history.py`:

```python
"""Offline withdrawal approval requests and per-quarter generation lineage."""
from network_guard import install
install()

import unittest

from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.history import quarter_history, withdrawal_candidates


class HistoryTests(GateFixture):
    def approve(self, candidate, revised):
        result = approve('2026Q4', candidate.manifest.generation_id, revised.snapshot.sha256, 'Lowell Mason',
                         self.objects, self.state)
        self.assertEqual(result.outcome, 'success')
        return result

    def test_history_walks_the_exact_lineage_with_approval_evidence(self):
        base, revised, candidate = self.gated()
        approved = self.approve(candidate, revised)
        returned = self.observation(rows=row() + row('Returned', number=2), seconds=2)
        self.assertEqual(self.publish(returned).outcome, 'published')
        history = quarter_history('2026Q4', self.objects, self.state)
        self.assertEqual([entry['gate'] for entry in history], ['clear', 'awaiting_approval', 'clear'])
        self.assertEqual([entry['generation_id'] for entry in history[1:]],
                         [candidate.manifest.generation_id, base.generation_id])
        self.assertEqual(history[0]['base_generation_id'], candidate.manifest.generation_id)
        self.assertEqual((history[0]['added'], history[1]['withdrawn'], history[2]['row_count']), (1, 1, 2))
        self.assertEqual(history[1]['approval'], approved.approval.to_mapping())
        self.assertEqual(history[1]['membership_sha256'], revised.snapshot.sha256)
        self.assertEqual((history[2]['approval'], history[2]['base_generation_id']), (None, None))
        self.assertTrue(history[1]['changes']['path'].endswith('/changes.parquet'))
        self.assertEqual(quarter_history('2026Q3', self.objects, self.state), ())

    def test_candidates_report_status_approval_and_withdrawn_rows(self):
        base, revised, candidate = self.gated()
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual((listed['status'], listed['approved'], listed['quarterly_sha256']),
                         ('pending', False, revised.snapshot.sha256))
        self.assertEqual((listed['base_generation_id'], listed['candidate_ref']),
                         (base.generation_id, candidate.candidate_ref))
        self.assertEqual([item['archive_path'] for item in listed['withdrawn']],
                         ['edgar/data/123456/0000123456-26-000002.txt'])
        # seed_observation records no acquisition state; the CLI acceptance covers observed hashes.
        self.assertEqual((listed['latest_observed_sha256'], listed['latest_observed_at']), (None, None))
        self.approve(candidate, revised)
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual((listed['status'], listed['approved']), ('active', True))
        self.publish(self.observation(rows=row() + row('Returned', number=2), seconds=2))
        listed, = withdrawal_candidates(self.objects, self.state)
        self.assertEqual(listed['status'], 'stale')

    def test_candidates_cli_prints_the_listing(self):
        _, _, candidate = self.gated()
        code, message, _ = operator_cli('candidates', '--config', str(self.write_config()),
                                        '--state-dir', str(self.root))
        self.assertEqual((code, message['outcome'], message['error']), (0, 'success', None))
        self.assertEqual([entry['generation_id'] for entry in message['candidates']],
                         [candidate.manifest.generation_id])
        self.assertEqual(operator_cli('candidates', '--config', str(self.root / 'missing.json'))[:2], (2, None))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the focused command with `-p 'test_etl_history.py'`.
Expected: `ModuleNotFoundError: No module named 'sec_edgar_ingest.etl.history'`.

- [ ] **Step 3: Implement history and the listing**

In `etl/manifest.py`, move the retained-base read out of `_base_manifest` so that history and rollback reuse the validator's exact check. Replace `_base_manifest` with:

```python
def retained_base(manifest: GenerationManifest, objects: ObjectStore) -> GenerationCapture | None:
    """The exact capture a generation was built against, from its immutable retained-base record."""
    if not manifest.base_generation_id:
        return None
    body = objects.read(generation_base(manifest.quarter, manifest.generation_id) + '/retained-base.json')
    retained = GenerationCapture.from_mapping(parse_json(body))
    if canonical_json(retained.to_mapping()) != body or (retained.quarter, retained.generation_id) != (
            manifest.quarter, manifest.base_generation_id):
        raise ValueError('exact base dependency differs')
    if retained.generation_id == manifest.generation_id:
        raise ValueError('self-referential base dependency')
    return retained


def _base_manifest(manifest, objects):
    if not manifest.base_generation_id and manifest.unresolved_absence:
        raise ValueError('unresolved absence requires an exact retained dependency')
    retained = retained_base(manifest, objects)
    if retained is None:
        return None
    previous = read_manifest(retained, objects)
    validate_files(previous, objects)
    return previous
```

The behavior and messages of `_base_manifest` are unchanged; the shipped retained-base tamper tests in `test_etl_catalog.py` keep covering them.

Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py`:

```python
"""Read-only withdrawal approval requests and per-quarter generation lineage."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import closing

from ..models import quarter_value
from ..state import AcquisitionState
from ..storage.contracts import Conflict, ObjectStore
from .contracts import Candidate, FileRef, GenerationCapture, GenerationManifest, IndexRow
from .manifest import gate_payload, gate_ref, iter_file_rows, read_approval, read_manifest, retained_base
from .reader import capture_from_pointer, capture_quarter
from .state import EtlState

COUNTS = ('row_count', 'added', 'updated', 'withdrawn', 'unresolved_absence', 'provenance_refreshed')


def _changes(manifest: GenerationManifest) -> FileRef:
    return next(ref for ref in manifest.files if ref.role == 'changes')


def lineage(capture: GenerationCapture | None,
            objects: ObjectStore) -> Iterator[tuple[GenerationCapture, GenerationManifest]]:
    """Newest-first (capture, manifest) pairs through each generation's exact retained base."""
    seen = set()
    while capture is not None:
        if capture.generation_id in seen:
            raise Conflict('generation lineage repeats a generation')
        seen.add(capture.generation_id)
        manifest = read_manifest(capture, objects)
        yield capture, manifest
        capture = retained_base(manifest, objects)


def quarter_history(quarter: str, objects: ObjectStore, state: EtlState) -> tuple[dict[str, object], ...]:
    """Newest-first lineage from the active pointer, with the approval of each approved gated generation."""
    entries = []
    for capture, manifest in lineage(capture_quarter(quarter, objects, state), objects):
        approval = None
        if manifest.gate == 'awaiting_approval':
            candidate = Candidate(manifest, capture.manifest_ref, capture.manifest_sha256,
                                  capture.manifest_bytes, gate_ref(manifest))
            approval = read_approval(candidate, objects).to_mapping()
        entries.append({'generation_id': manifest.generation_id, 'base_generation_id': manifest.base_generation_id,
                        'manifest_ref': capture.manifest_ref, 'quarter_mode': manifest.quarter_mode,
                        'gate': manifest.gate, **{name: getattr(manifest, name) for name in COUNTS},
                        'membership_sha256': (manifest.membership_source.snapshot.sha256
                                              if manifest.membership_source else None),
                        'changes': _changes(manifest).to_mapping(), 'approval': approval})
    return tuple(entries)


def withdrawal_candidates(objects: ObjectStore, state: EtlState) -> tuple[dict[str, object], ...]:
    """Each recorded gated candidate as an approval request with its current status."""
    acquisition, entries = AcquisitionState(state.store), []
    for row in state.store.scan('Candidate', {}):
        candidate = Candidate.from_mapping(row.to_mapping()['value'])
        manifest = candidate.manifest
        capture = GenerationCapture(manifest.quarter, manifest.generation_id, candidate.manifest_ref,
                                    candidate.manifest_sha256, candidate.manifest_bytes)
        if (read_manifest(capture, objects) != manifest or candidate.candidate_ref != gate_ref(manifest)
                or objects.read(candidate.candidate_ref) != gate_payload(candidate)):
            raise Conflict('candidate index differs from its immutable manifest and gate record')
        pointer = state.pointer(manifest.quarter)
        active = None if pointer is None else capture_from_pointer(pointer).generation_id
        status = ('active' if active == manifest.generation_id
                  else 'pending' if active == manifest.base_generation_id else 'stale')
        source = manifest.membership_source
        observed = acquisition.get_source(source.source.source_id)
        observed = None if observed is None else observed.to_mapping()['value']
        changes = _changes(manifest)
        with closing(iter_file_rows(changes, objects)) as rows:
            withdrawn = [IndexRow(**value['before']).to_mapping() for value in rows
                         if value['change_type'] == 'withdrawn']
        entries.append({'quarter': manifest.quarter, 'generation_id': manifest.generation_id,
                        'base_generation_id': manifest.base_generation_id,
                        'quarterly_sha256': source.snapshot.sha256, 'candidate_ref': candidate.candidate_ref,
                        'changes': changes.to_mapping(), 'withdrawn': withdrawn, 'status': status,
                        'approved': state.approval(manifest.generation_id) is not None,
                        'latest_observed_sha256': None if observed is None else observed['latest_downloaded_snapshot'],
                        'latest_observed_at': None if observed is None else observed['latest_received_at']})
    return tuple(sorted(entries, key=lambda entry: (quarter_value(entry['quarter']), entry['generation_id'])))
```

- [ ] **Step 4: Add the `candidates` CLI**

In `cli.py`, add the import:

```python
from .etl.history import withdrawal_candidates
```

In `_parser`, add this code after the `approve` subparser:

```python
    sub = commands.add_parser('candidates')
    sub.add_argument('--config', required=True)
    sub.add_argument('--state-dir')
```

Add this function after `_approve_main`. The listing is read-only, so it writes no stderr event line:

```python
def _candidates_main(args) -> int:
    return _operator_main(args, None, {'candidates': None, 'error': None},
                          lambda objects, state: {'outcome': 'success',
                                                  'candidates': list(withdrawal_candidates(objects, state))})
```

In `main`, add after the `approve` routing:

```python
    if args.command == 'candidates':
        return _candidates_main(args)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run the focused command once for each pattern: `test_etl_history.py`, `test_etl_approval.py`, `test_etl_catalog.py` and `test_etl_publication.py`. The last two cover the `_base_manifest` refactor.
Expected: `OK` each time.

- [ ] **Step 6: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/history.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/manifest.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_etl_history.py
git commit -m "feat(etl): list withdrawal candidates and quarter lineage"
```

---

### Task 6: Recorded pointer rollback

**Files:**
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py` (constants beside `APPROVAL_FORMAT`; new record after `WithdrawalApproval`)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py` (import; methods after `approval`)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py` (`APPROVAL_KINDS`)
- Create: `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/rollback.py`
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py` (`EXIT_CODES`)
- Modify: `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py` (imports, `_parser`, `_rollback_main`, `main` routing)
- Create: `packages/sec-edgar-ingest/tests/test_etl_rollback.py`
- Modify: `packages/sec-edgar-ingest/tests/test_etl_storage.py` (new test after Task 1's approvals-table test)
- Modify: `packages/sec-edgar-ingest/tests/test_workflow_contracts.py` (exit-outcome table)

**Interfaces:**
- Consumes:
  - Task 1: `require_line`, `MAX_OPERATOR_CHARS`, `validated_manifest` with approval acceptance, `APPROVAL_KINDS`, `GateFixture`, `operator_cli` and `row`.
  - Task 2: `approve` and `_operator_main`.
  - Task 5: `lineage`.
  - Shipped: `capture_from_pointer`, `EtlState.pointer`, `EtlState.commit_pointer`, `EtlState._immutable`, `observe`, `CAS_ATTEMPTS` and `Faults`.
- Produces:
  - `etl.contracts`: `ROLLBACK_FORMAT = 'sec-pointer-rollback-v1'`, `MAX_REASON_CHARS = 1024`, and `QuarterRollback(Record)` with fields `quarter, from_generation_id, to_generation_id, from_pointer_version, to_manifest_ref, to_manifest_sha256, to_manifest_bytes: int, operator, reason, rolled_back_at: datetime, format_version`, plus the property `rollback_id -> str`.
  - `EtlState.record_rollback(record) -> None` and `EtlState.rollbacks(quarter) -> tuple[QuarterRollback, ...]`, sorted by `(rolled_back_at, rollback_id)`.
  - `table_for('QuarterRollback') == 'Approvals'`.
  - `etl.rollback`:
    - `ROLLBACK_OUTCOMES` and `class RollbackRefused(ValueError)`
    - `RollbackOutcome(Record)` with fields `outcome: str`, `active: GenerationCapture | None`, `rollback: QuarterRollback | None` and `error: Error | None`
    - `rollback_ref(record: QuarterRollback) -> str`
    - `rollback(quarter, from_generation, to_generation, operator, reason, objects, state, *, observer=None) -> RollbackOutcome`
  - Observer points: `rollback.before_pointer`, `rollback.cas_lost` and `rollback.after_pointer`.
  - Exit codes: `EXIT_CODES['rollback_refused'] == 2` and `EXIT_CODES['rollback_stale'] == 11`.
  - CLI `rollback`:
    - stdout carries the canonical keys `outcome, quarter, from_generation_id, to_generation_id, rollback_ref, active, rollback, error`;
    - one stderr line has event `quarter_rollback`.

- [ ] **Step 1: Write the failing tests**

Create `packages/sec-edgar-ingest/tests/test_etl_rollback.py`:

```python
"""Offline recorded pointer rollback within one quarter's exact lineage."""
from network_guard import install
install()

import json
import unittest

from support import Faults
from support_approval import GateFixture, operator_cli, row
from sec_edgar_ingest.etl.approval import approve
from sec_edgar_ingest.etl.contracts import QuarterRollback
from sec_edgar_ingest.etl.rollback import rollback, rollback_ref
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import table_for


class RollbackTests(GateFixture):
    def lineage_of_two(self):
        """Publish G1 {1, 2} then G2 {1 Renamed, 2} in the open 2026Q4."""
        first = self.observation(rows=row() + row(number=2))
        self.assertEqual(self.publish(first).outcome, 'published')
        older = self.capture()
        second = self.observation(rows=row('Renamed') + row(number=2), seconds=1)
        self.assertEqual(self.publish(second).outcome, 'published')
        return older, self.capture(), second

    def rollback(self, source, target, operator='Lowell Mason', reason='SEC correction withdrawn', **kwargs):
        return rollback('2026Q4', source, target, operator, reason, self.objects, self.state, **kwargs)

    def test_rollback_records_then_restores_an_earlier_lineage_generation(self):
        older, newer, _ = self.lineage_of_two()
        before = self.state.pointer('2026Q4')
        result = self.rollback(newer.generation_id, older.generation_id)
        self.assertEqual((result.outcome, result.active), ('success', older))
        self.assertEqual(self.capture(), older)
        self.assertEqual(self.rows(), [(1, 'Example'), (2, 'Example')])
        record = result.rollback
        self.assertEqual((record.quarter, record.from_generation_id, record.to_generation_id,
                          record.from_pointer_version, record.operator, record.reason, record.format_version),
                         ('2026Q4', newer.generation_id, older.generation_id, before.version, 'Lowell Mason',
                          'SEC correction withdrawn', 'sec-pointer-rollback-v1'))
        self.assertEqual((record.to_manifest_ref, record.to_manifest_sha256, record.to_manifest_bytes),
                         (older.manifest_ref, older.manifest_sha256, older.manifest_bytes))
        ref = rollback_ref(record)
        self.assertEqual(ref, 'approvals/sec/filing_index/year=2026/quarter=4/rollback='
                         + record.rollback_id + '/rollback.json')
        self.assertEqual(self.objects.read(ref), canonical_json(record.to_mapping()))
        self.assertEqual(QuarterRollback.from_mapping(record.to_mapping()), record)
        self.assertEqual(self.state.rollbacks('2026Q4'), (record,))
        self.assertEqual(table_for('QuarterRollback'), 'Approvals')
        pointer = self.state.pointer('2026Q4')
        again = self.rollback(newer.generation_id, older.generation_id, reason='repeated')
        self.assertEqual((again.outcome, again.active, again.rollback), ('unchanged', older, None))
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assertEqual(self.state.rollbacks('2026Q4'), (record,))

    def test_rollback_is_not_a_pin_and_never_rolls_forward(self):
        older, newer, second = self.lineage_of_two()
        self.assertEqual(self.rollback(newer.generation_id, older.generation_id).outcome, 'success')
        forward = self.rollback(older.generation_id, newer.generation_id)
        self.assertEqual((forward.outcome, forward.error.code), ('rollback_refused', 'rollback_refused'))
        self.assertEqual(self.capture(), older)
        # Receipt-ordered selection rebuilds the same deterministic generation from the restored base.
        self.assertEqual(self.publish(second).outcome, 'published')
        self.assertEqual(self.capture(), newer)

    def test_refusals_and_stale_requests_write_nothing(self):
        older, newer, _ = self.lineage_of_two()
        pointer = self.state.pointer('2026Q4')
        cases = {
            'same generation': ('2026Q4', newer.generation_id, newer.generation_id, 'Lowell Mason', 'x'),
            'unknown target': ('2026Q4', newer.generation_id, 'f' * 64, 'Lowell Mason', 'x'),
            'invalid hash text': ('2026Q4', newer.generation_id, 'not-a-hash', 'Lowell Mason', 'x'),
            'invalid quarter': ('2026Q5', newer.generation_id, older.generation_id, 'Lowell Mason', 'x'),
            'invalid operator': ('2026Q4', newer.generation_id, older.generation_id, 'two\nlines', 'x'),
            'long reason': ('2026Q4', newer.generation_id, older.generation_id, 'Lowell Mason', 'r' * 1025),
            'no pointer': ('2026Q3', newer.generation_id, older.generation_id, 'Lowell Mason', 'x'),
        }
        for label, args in cases.items():
            with self.subTest(label):
                result = rollback(*args, self.objects, self.state)
                self.assertEqual((result.outcome, result.error.code), ('rollback_refused', 'rollback_refused'))
                self.assertIsNone(result.rollback)
        stale = rollback('2026Q4', 'e' * 64, older.generation_id, 'Lowell Mason', 'x', self.objects, self.state)
        self.assertEqual((stale.outcome, stale.error.details['active_generation_id']),
                         ('rollback_stale', newer.generation_id))
        self.assertEqual(self.state.pointer('2026Q4'), pointer)
        self.assertEqual(self.state.rollbacks('2026Q4'), ())

    def test_an_approved_gated_generation_is_a_valid_target(self):
        _, revised, candidate = self.gated()
        approved = approve('2026Q4', candidate.manifest.generation_id, revised.snapshot.sha256, 'Lowell Mason',
                           self.objects, self.state)
        self.assertEqual(approved.outcome, 'success')
        returned = self.observation(rows=row() + row('Returned', number=2), seconds=2)
        self.assertEqual(self.publish(returned).outcome, 'published')
        latest = self.capture()
        result = self.rollback(latest.generation_id, candidate.manifest.generation_id)
        self.assertEqual((result.outcome, self.capture().generation_id),
                         ('success', candidate.manifest.generation_id))
        self.assertEqual(self.rows(), [(1, 'Example')])

    def test_a_lost_pointer_race_is_stale_and_keeps_its_attempt_record(self):
        older, newer, _ = self.lineage_of_two()
        third = self.observation(rows=row('Third') + row(number=2), seconds=2)
        faults = Faults()
        faults.at('rollback.before_pointer', lambda: self.assertEqual(self.publish(third).outcome, 'published'))
        result = self.rollback(newer.generation_id, older.generation_id, observer=faults)
        self.assertEqual((result.outcome, result.error.details['from_generation_id']),
                         ('rollback_stale', newer.generation_id))
        self.assertNotIn(self.capture().generation_id, (older.generation_id, newer.generation_id))
        attempt, = self.state.rollbacks('2026Q4')
        self.assertEqual((attempt.from_generation_id, attempt.to_generation_id),
                         (newer.generation_id, older.generation_id))

    def test_rollback_cli_maps_named_outcomes_to_exit_codes(self):
        older, newer, _ = self.lineage_of_two()
        command = ('rollback', '--config', str(self.write_config()), '--state-dir', str(self.root),
                   '--quarter', '2026Q4', '--operator', 'Lowell Mason', '--reason', 'bad correction')
        code, message, _ = operator_cli(*command, '--from-generation', 'e' * 64,
                                        '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome'], message['rollback_ref']), (11, 'rollback_stale', None))
        code, message, events = operator_cli(*command, '--from-generation', newer.generation_id,
                                             '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome'], message['active']['generation_id']),
                         (0, 'success', older.generation_id))
        self.assertEqual(message['rollback_ref'], rollback_ref(QuarterRollback.from_mapping(message['rollback'])))
        self.assertEqual(json.loads(events.splitlines()[-1])['event'], 'quarter_rollback')
        code, message, _ = operator_cli(*command, '--from-generation', newer.generation_id,
                                        '--to-generation', older.generation_id)
        self.assertEqual((code, message['outcome']), (0, 'unchanged'))
        code, message, _ = operator_cli(*command, '--from-generation', older.generation_id,
                                        '--to-generation', newer.generation_id)
        self.assertEqual((code, message['outcome']), (2, 'rollback_refused'))


if __name__ == '__main__':
    unittest.main()
```

In `packages/sec-edgar-ingest/tests/test_etl_storage.py`, add this method to `EtlStorageTests` right after `test_withdrawal_approval_real_sdk_routes_to_the_approvals_table`:

```python
    def test_quarter_rollback_real_sdk_routes_to_the_approvals_table(self):
        from azure.core.credentials import AzureSasCredential
        from azure.data.tables import TableServiceClient
        from sec_edgar_ingest.storage.azure import AzureStateStore
        from test_azure_contracts import ScriptedTransport, table_response, TABLE_ENDPOINT, RETRY
        transport = ScriptedTransport([table_response(201, etag='W/"rollback"')])
        service = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential('sv=offline&sig=synthetic'), api_version='2020-12-06', transport=transport, **RETRY)
        self.addCleanup(service.close)
        tables = service.get_table_client
        store = AzureStateStore(tables('SourceState'), tables('Attempts'), active_client=tables('ActivePointers'),
                                approval_client=tables('Approvals'))
        self.assertEqual(store.insert('QuarterRollback', 'b' * 64, {'operator': 'Lowell Mason'}).version, 'W/"rollback"')
        self.assertIn('/Approvals', transport.requests[0].url)
```

In `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`, add two entries to the `expected` table of `test_all_exit_outcomes_have_explicit_member_and_coverage_status`, after the `'approval_stale'` entry from Task 2:

```python
            'rollback_refused': ('failed', 'incomplete'),
            'rollback_stale': ('failed', 'incomplete'),
```

- [ ] **Step 2: Run the tests to verify they fail**

Run the focused command with `-p 'test_etl_rollback.py'`.
Expected: `ImportError: cannot import name 'QuarterRollback'`.

Run it with `-p 'test_etl_storage.py' -k quarter_rollback`.
Expected: an `AssertionError`; the request goes to `/SourceState`.

Run it with `-p 'test_workflow_contracts.py' -k all_exit_outcomes`.
Expected: an `AssertionError` from the set comparison.

- [ ] **Step 3: Add the rollback record, index and routing**

In `etl/contracts.py`, add these constants after `MAX_OPERATOR_CHARS`:

```python
ROLLBACK_FORMAT = 'sec-pointer-rollback-v1'
MAX_REASON_CHARS = 1024
```

After the `WithdrawalApproval` class, add:

```python
@dataclass(frozen=True, slots=True)
class QuarterRollback(Record):
    """Immutable, write-ahead operator record of one pointer move back within a quarter's exact lineage."""
    quarter: str
    from_generation_id: str
    to_generation_id: str
    from_pointer_version: str
    to_manifest_ref: str
    to_manifest_sha256: str
    to_manifest_bytes: int
    operator: str
    reason: str
    rolled_back_at: datetime
    format_version: str = ROLLBACK_FORMAT

    def __post_init__(self):
        _record(self)
        if self.format_version != ROLLBACK_FORMAT:
            raise ValueError('unsupported rollback format')
        require_hash(self.from_generation_id, 'from_generation_id')
        require_hash(self.to_generation_id, 'to_generation_id')
        if self.from_generation_id == self.to_generation_id:
            raise ValueError('rollback must change the active generation')
        require_text(self.from_pointer_version, 'from_pointer_version')
        _counts(self, 'to_manifest_bytes')
        require_line(self.operator, 'operator', MAX_OPERATOR_CHARS)
        require_line(self.reason, 'reason', MAX_REASON_CHARS)
        require_utc(self.rolled_back_at, 'rolled_back_at')

    @property
    def rollback_id(self) -> str:
        """One identity per attempted move from an exact pointer version to one target."""
        return hashlib.sha256(canonical_json([self.quarter, self.from_generation_id, self.to_generation_id,
                                              self.from_pointer_version])).hexdigest()
```

`_record` validates `quarter`, `to_manifest_sha256` and `to_manifest_ref`. It does not treat `from_generation_id` or `to_generation_id` as hashes, hence the explicit checks.

In `etl/state.py`, add `QuarterRollback` to the `.contracts` import. Add these methods after `approval`:

```python
    def record_rollback(self, record: QuarterRollback) -> None:
        self._immutable('QuarterRollback', record.rollback_id, record.to_mapping())

    def rollbacks(self, quarter: str) -> tuple[QuarterRollback, ...]:
        """Every write-ahead rollback record of one quarter; the pointer decides which took effect."""
        quarter_value(quarter)
        records = (QuarterRollback.from_mapping(row.to_mapping()['value'])
                   for row in self.store.scan('QuarterRollback', {'quarter': quarter}))
        return tuple(sorted(records, key=lambda record: (record.rolled_back_at, record.rollback_id)))
```

In `storage/contracts.py`, change `APPROVAL_KINDS` to:

```python
APPROVAL_KINDS = frozenset({"WithdrawalApproval", "QuarterRollback"})
```

`AzureStateStore._client` already routes every `Approvals` kind to the approval client (Task 1).

- [ ] **Step 4: Implement the operation**

Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/rollback.py`:

```python
"""Explicit recorded rollback of one quarter pointer to an earlier generation in its exact lineage."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import islice

from ..models import Error, Record, canonical_json, parse_json, quarter_value, require_hash, validate_record_fields
from ..storage.contracts import AlreadyExists, BoundaryObserver, CAS_ATTEMPTS, Conflict, ObjectStore, observe
from .contracts import MAX_OPERATOR_CHARS, MAX_REASON_CHARS, GenerationCapture, QuarterRollback, require_line
from .history import lineage
from .reader import capture_from_pointer, validated_manifest
from .state import EtlState

ROLLBACK_OUTCOMES = ('success', 'unchanged', 'rollback_refused', 'rollback_stale')


class RollbackRefused(ValueError):
    """The target is not an earlier generation in the active lineage; nothing was written."""


@dataclass(frozen=True, slots=True)
class RollbackOutcome(Record):
    outcome: str
    active: GenerationCapture | None
    rollback: QuarterRollback | None
    error: Error | None

    def __post_init__(self):
        validate_record_fields(self)
        if self.outcome not in ROLLBACK_OUTCOMES:
            raise ValueError('unsupported rollback outcome')
        if self.outcome in ('success', 'unchanged'):
            valid = (self.active is not None and self.error is None
                     and (self.rollback is not None) == (self.outcome == 'success'))
        else:
            valid = (self.active is None and self.rollback is None
                     and self.error is not None and self.error.code == self.outcome)
        if not valid:
            raise ValueError('rollback outcome evidence differs from its outcome')


def _now() -> datetime:
    """Patchable UTC rollback clock."""
    return datetime.now(timezone.utc)


def _failed(outcome: str, message: str, **details: str) -> RollbackOutcome:
    return RollbackOutcome(outcome, None, None, Error(outcome, message, False, None, details))


def rollback_ref(record: QuarterRollback) -> str:
    year, ordinal = quarter_value(record.quarter)
    return f'approvals/sec/filing_index/year={year}/quarter={ordinal}/rollback={record.rollback_id}/rollback.json'


def _ancestor(active: GenerationCapture, generation_id: str, objects: ObjectStore) -> GenerationCapture:
    for capture, _ in islice(lineage(active, objects), 1, None):
        if capture.generation_id == generation_id:
            return capture
    raise RollbackRefused("target is not an earlier generation in this quarter's exact lineage")


def _store_rollback(record: QuarterRollback, objects: ObjectStore) -> QuarterRollback:
    ref = rollback_ref(record)
    try:
        objects.put_once(ref, canonical_json(record.to_mapping()))
    except Conflict:
        pass  # The first record of this exact attempted move wins; it is re-validated below.
    body = objects.read(ref)
    stored = QuarterRollback.from_mapping(parse_json(body))
    if canonical_json(stored.to_mapping()) != body or rollback_ref(stored) != ref or (
            stored.to_manifest_ref, stored.to_manifest_sha256, stored.to_manifest_bytes) != (
            record.to_manifest_ref, record.to_manifest_sha256, record.to_manifest_bytes):
        raise ValueError('stored rollback differs from this exact pointer move')
    return stored


def rollback(quarter: str, from_generation: str, to_generation: str, operator: str, reason: str,
             objects: ObjectStore, state: EtlState, *, observer: BoundaryObserver | None = None) -> RollbackOutcome:
    try:
        quarter_value(quarter)
        require_hash(from_generation, 'from_generation')
        require_hash(to_generation, 'to_generation')
        if from_generation == to_generation:
            raise ValueError('rollback requires two different generations')
        require_line(operator, 'operator', MAX_OPERATOR_CHARS)
        require_line(reason, 'reason', MAX_REASON_CHARS)
    except ValueError as error:
        return _failed('rollback_refused', str(error))
    for _ in range(CAS_ATTEMPTS):
        current = state.pointer(quarter)
        if current is None:
            return _failed('rollback_refused', 'quarter has no active generation')
        active = capture_from_pointer(current)
        if active.generation_id == to_generation:
            return RollbackOutcome('unchanged', active, None, None)
        if active.generation_id != from_generation:
            return _failed('rollback_stale', 'active generation is not the rollback source',
                           active_generation_id=active.generation_id, from_generation_id=from_generation)
        try:
            target = _ancestor(active, to_generation, objects)
        except RollbackRefused as error:
            return _failed('rollback_refused', str(error))
        manifest = validated_manifest(target, objects)
        stored = _store_rollback(QuarterRollback(
            quarter, from_generation, to_generation, current.version, target.manifest_ref,
            target.manifest_sha256, target.manifest_bytes, operator, reason, _now()), objects)
        state.record_rollback(stored)
        observe(observer, 'rollback.before_pointer')
        try:
            state.commit_pointer(quarter, {**target.to_mapping(), 'source_fingerprint': manifest.source_fingerprint},
                                 current)
        except (AlreadyExists, Conflict):
            observe(observer, 'rollback.cas_lost')
            continue
        observe(observer, 'rollback.after_pointer')
        return RollbackOutcome('success', target, stored, None)
    raise Conflict('rollback exhausted conditional pointer races')
```

As in `approve`, corrupt evidence is not caught here: an invalid lineage, target manifest or stored record raises `ValueError` or `Conflict`, which the CLI reports as `state_conflict`. A gated target without its exact approval fails `validated_manifest` the same way. The stored, first-wins record is the one indexed and returned.

- [ ] **Step 5: Add the exit codes and the CLI**

In `results.py`, add the two names to `EXIT_CODES`, keeping Task 2's entries:

```python
EXIT_CODES = {
    'success': 0, 'no_new_sources': 0, 'unchanged': 0, 'configuration': 2,
    'approval_refused': 2, 'rollback_refused': 2, 'discovery_failed': 3, 'incomplete': 3, 'pending': 4,
    'retry_exhausted': 5, 'deferred': 5, 'throttled': 5,
    'access_blocked': 6, 'quarantined': 7, 'invalid_source': 7,
    'ownership_lost': 8, 'state_conflict': 9, 'internal_error': 9,
    'publication_conflict': 9, 'awaiting_approval': 10, 'approval_stale': 11, 'rollback_stale': 11,
}
```

In `cli.py`, add the import:

```python
from .etl.rollback import rollback, rollback_ref
```

In `_parser`, add this code after the `candidates` subparser:

```python
    sub = commands.add_parser('rollback')
    for name in ('config', 'quarter', 'from-generation', 'to-generation', 'operator', 'reason'):
        sub.add_argument('--' + name, required=True)
    sub.add_argument('--state-dir')
```

Add this function after `_candidates_main`:

```python
def _rollback_main(args) -> int:
    def run(objects, state):
        result = rollback(args.quarter, args.from_generation, args.to_generation, args.operator, args.reason,
                          objects, state)
        return {**result.to_mapping(),
                'rollback_ref': None if result.rollback is None else rollback_ref(result.rollback)}
    return _operator_main(args, 'quarter_rollback',
                          {'quarter': args.quarter, 'from_generation_id': args.from_generation,
                           'to_generation_id': args.to_generation, 'rollback_ref': None, 'active': None,
                           'rollback': None, 'error': None}, run)
```

In `main`, add after the `candidates` routing:

```python
    if args.command == 'rollback':
        return _rollback_main(args)
```

- [ ] **Step 6: Run the tests to verify they pass**

Run the focused command once for each pattern: `test_etl_rollback.py`, `test_etl_storage.py`, `test_workflow_contracts.py`, `test_etl_approval.py` and `test_etl_history.py`.
Expected: `OK` each time.

- [ ] **Step 7: Commit**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/state.py packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/contracts.py packages/sec-edgar-ingest/src/sec_edgar_ingest/etl/rollback.py packages/sec-edgar-ingest/src/sec_edgar_ingest/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_etl_rollback.py packages/sec-edgar-ingest/tests/test_etl_storage.py packages/sec-edgar-ingest/tests/test_workflow_contracts.py
git commit -m "feat(etl): record and apply explicit quarter pointer rollback"
```

---

### Task 7: Operator acceptance, documentation and the stage exit

**Files:**
- Create: `packages/sec-edgar-ingest/tests/test_reconcile_acceptance.py`
- Create: `docs/runbooks/sec-edgar-reconciliation-approval.md`
- Modify: `packages/sec-edgar-ingest/README.md` (workflow section, about lines 129-171)
- Modify: `docs/runbooks/sec-edgar-etl-publication.md` ("No-op, gate and repair" section)

**Interfaces:**
- Consumes everything from Tasks 1-6, through the CLI only, apart from the library APIs `quarter_history` and `EtlState.rollbacks`.
- Produces: a stage-exit test file, operator documentation, and verified suite, build and help evidence.

- [ ] **Step 1: Write the acceptance test**

Create `packages/sec-edgar-ingest/tests/test_reconcile_acceptance.py`. Every reconcile re-fetches each quarterly source, because refresh members never reuse an earlier binding, so the revert phase reprocesses the Q3 source and reports it:

```python
"""R5/R7/R10 operator acceptance: reconcile, review, approve, reintroduce and roll back through the CLI."""
from network_guard import install
install()

import unittest

from support_approval import operator_cli
from support_reconcile import A, B, ReconcileFixture, sha
from sec_edgar_ingest.etl.history import quarter_history
from sec_edgar_ingest.etl.state import EtlState


class ReconcileAcceptanceTests(ReconcileFixture):
    def test_reconcile_gate_review_approve_reintroduce_and_roll_back(self):
        h = self.harness((A, B))
        self.assertEqual(self.run_phase(h, 'backfill', 'base')[0], 0, h.calls[-1])
        code, _, report = self.run_phase(h, 'reconcile', 'same', (A, B))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        code, _, report = self.run_phase(h, 'reconcile', 'gate', (A,))
        self.assertEqual((code, report.outcome, report.counts['awaiting_approval_quarters']),
                         (10, 'awaiting_approval', 1), h.calls[-1])
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])

        operator = ('--config', str(h.config), '--state-dir', str(h.root))
        code, listing, _ = operator_cli('candidates', *operator)
        self.assertEqual(code, 0)
        request, = listing['candidates']
        self.assertEqual((request['status'], request['approved'], request['quarterly_sha256'],
                          request['latest_observed_sha256']), ('pending', False, sha((A,)), sha((A,))))
        self.assertEqual([row['company_name'] for row in request['withdrawn']], ['B'])

        command = ('approve', *operator, '--quarter', '2026Q3', '--generation', request['generation_id'],
                   '--approver', 'Lowell Mason')
        self.assertEqual(operator_cli(*command, '--quarterly-sha256', sha((A, B)))[0], 2)
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B'])
        code, approved, _ = operator_cli(*command, '--quarterly-sha256', sha((A,)))
        self.assertEqual((code, approved['outcome']), (0, 'success'))
        self.assertEqual(self.names(h, '2026Q3'), ['A'])
        self.assertEqual(operator_cli(*command, '--quarterly-sha256', sha((A,)))[1]['outcome'], 'unchanged')

        code, _, report = self.run_phase(h, 'reconcile', 'after', (A,))
        self.assertEqual((code, report.outcome), (0, 'unchanged'), h.calls[-1])
        returned = ('123456', 'B Returned', *B[2:])
        code, _, report = self.run_phase(h, 'reconcile', 'returned', (A, returned))
        self.assertEqual((code, report.outcome), (0, 'success'), h.calls[-1])
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B Returned'])
        history = quarter_history('2026Q3', h.objects, EtlState(h.store))
        self.assertEqual([entry['gate'] for entry in history], ['clear', 'awaiting_approval', 'clear'])
        self.assertEqual((history[0]['added'], history[1]['withdrawn']), (1, 1))
        self.assertEqual(history[1]['approval']['approver'], 'Lowell Mason')
        code, listing, _ = operator_cli('candidates', *operator)
        self.assertEqual([(entry['status'], entry['approved']) for entry in listing['candidates']],
                         [('stale', True)])

        # The SEC reverts to the approved (A,) bytes: reported, not published.
        code, _, report = self.run_phase(h, 'reconcile', 'revert', (A,))
        self.assertEqual((code, report.outcome), (3, 'incomplete'), h.calls[-1])
        self.assertEqual([gap.code for gap in report.gaps], ['source_reverted'])
        self.assertEqual(self.names(h, '2026Q3'), ['A', 'B Returned'])
        history = quarter_history('2026Q3', h.objects, EtlState(h.store))
        target = next(entry for entry in history if entry['membership_sha256'] == sha((A,)))
        code, rolled, _ = operator_cli('rollback', *operator, '--quarter', '2026Q3',
                                       '--from-generation', history[0]['generation_id'],
                                       '--to-generation', target['generation_id'],
                                       '--operator', 'Lowell Mason', '--reason', 'SEC reverted to the approved bytes')
        self.assertEqual((code, rolled['outcome']), (0, 'success'))
        self.assertEqual(self.names(h, '2026Q3'), ['A'])
        self.assertEqual([record.to_generation_id for record in EtlState(h.store).rollbacks('2026Q3')],
                         [target['generation_id']])
        code, _, report = self.run_phase(h, 'reconcile', 'restored', (A,))
        self.assertEqual((code, report.outcome, report.gaps), (0, 'unchanged', ()), h.calls[-1])
        code, listing, _ = operator_cli('candidates', *operator)
        self.assertEqual([(entry['status'], entry['approved']) for entry in listing['candidates']],
                         [('active', True)])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the acceptance test**

Run the focused command with `-p 'test_reconcile_acceptance.py'`.
Expected: `OK`. The test only exercises Tasks 1-6, so a failure here is a defect in those tasks. Diagnose it before continuing; do not weaken the assertion.

- [ ] **Step 3: Write the operator runbook**

Create `docs/runbooks/sec-edgar-reconciliation-approval.md`:

````markdown
# Reconciliation and withdrawal approval

Stage 5 adds four commands:

- `reconcile` refreshes every supported quarterly source through the Stage 4 workflow runner.
- `candidates` lists gated withdrawals.
- `approve` activates one exact gated candidate.
- `rollback` moves a quarter back to an earlier generation of its exact lineage, with a record.

Everything here uses local fixture state or offline evidence. Live SEC, Azure, credential, schedule and deployment work stays reserved for Stages 6–8.

## Run a reconciliation

`sec-edgar-ingest reconcile` takes the same arguments as `backfill`: config, run, execution and attempt IDs, and deadline. Local fixtures also take a fixture pack, state directory and date. Discovery is always `--mode quarterly --refresh`, with discovery ID `workflow-reconcile-<run-id>`; there is no public `--refresh` flag. Requested quarters run from `backfill.start_quarter` through the pinned endpoint. The report is `runs/sec/<run-id>/reconcile/<attempt-id>/result.json`.

| Outcome | Exit | Meaning |
|---|---|---|
| `unchanged` | 0 | Every refreshed source returned bytes that are already published |
| `success` | 0 | At least one quarter published a correction |
| `incomplete` | 3 | A gap (including `source_reverted`), a failure, or non-gate pending work beside completed sources. Read `gaps` and member outcomes |
| `awaiting_approval` | 10 | The only unresolved work is gated, even beside completed sources. Review `candidates` |

A failed or quarantined correction leaves the quarter's prior generation active. The failed member's source period names the affected quarter.

A `source_reverted` gap means the SEC now serves bytes identical to an older snapshot than the active one. The active generation stays, and every reconcile reports the gap. To follow the SEC, roll back (below) to the generation whose membership hash equals the gap's `observed_sha256`; `quarter_history` lists each generation's membership hash. If no generation in the lineage holds those bytes, the gap repeats until the SEC serves different bytes. Restored bytes that differ in any way are a new snapshot and publish normally.

## Review a withdrawal request

`sec-edgar-ingest candidates --config PATH [--state-dir PATH]` prints `{"candidates": [...], "error": null, "outcome": "success"}`. Each entry names:

- `quarter`, `generation_id`, `base_generation_id`, `quarterly_sha256` and `candidate_ref`;
- the change file, and every `withdrawn` key's prior row;
- `status`:
  - `pending`: its base is active;
  - `active`;
  - `stale`: the base moved on, or an approved candidate was later superseded;
- `approved`;
- the membership source's `latest_observed_sha256` and `latest_observed_at`.

Before approving, confirm all three:

1. `status` is `pending`.
2. Every `withdrawn` row should leave the active catalog.
3. `latest_observed_sha256` equals `quarterly_sha256`. If it differs, the SEC no longer serves the candidate's bytes. Run `reconcile` first and review again. If the SEC went back to the base's bytes, do not approve: the run stays `awaiting_approval` until the source changes (a known, deferred limitation).

## Approve

```text
sec-edgar-ingest approve --config PATH --quarter YYYYQn --generation ID \
  --quarterly-sha256 HASH --approver TEXT [--state-dir PATH]
```

| Outcome | Exit | Next action |
|---|---|---|
| `success` | 0 | The pointer moved. The next reconcile resolves the gated members. |
| `unchanged` | 0 | The candidate was already active. |
| `approval_refused` | 2 | Correct the arguments. Nothing was written. |
| `approval_stale` | 11 | The base moved. Reconcile to stage a candidate against the current generation, then review it. |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or an unexpected failure. Stop and investigate. |

The approval object is immutable: `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/generation=<id>/approval.json`, format `sec-withdrawal-approval-v1`. The first stored approval wins. An approval binds one candidate generation, so a later download, or a rebuild on another base, needs its own approval. `approve` writes the approval object, the `Approvals` index and the conditional pointer replace. It does not repair Processing or PublicationReceipt indexes; the next publish that touches the quarter repairs them.

## Roll back

```text
sec-edgar-ingest rollback --config PATH --quarter YYYYQn --from-generation ID \
  --to-generation ID --operator TEXT --reason TEXT [--state-dir PATH]
```

`--from-generation` must be the active generation, and `--to-generation` an earlier generation of its exact lineage; take both from `quarter_history`. The command writes an immutable record first, at `approvals/sec/filing_index/year=<yyyy>/quarter=<q>/rollback=<id>/rollback.json` (format `sec-pointer-rollback-v1`), then swaps the pointer. A record whose swap lost a race stays as evidence of the attempt; the pointer decides what took effect.

| Outcome | Exit | Next action |
|---|---|---|
| `success` | 0 | The pointer moved to the target. |
| `unchanged` | 0 | The target was already active. |
| `rollback_refused` | 2 | Correct the arguments; the target must be earlier in the active lineage. Nothing was written. |
| `rollback_stale` | 11 | The active generation changed. Re-read `quarter_history` and decide again. |
| `state_conflict` / `internal_error` | 9 | Corrupt evidence or an unexpected failure. Stop and investigate. |

A rollback is not a pin: the next publish of a newer observation builds forward again. It cannot retract data consumers already used. Rolling back past an approved withdrawal makes its candidate `pending` again; re-activating it needs another `approve`.

## History

`quarter_history(quarter, objects, state)` in `sec_edgar_ingest.etl.history` returns the active generation's lineage, newest first, through each exact `retained-base.json`. Each entry carries the counts, gate, mode, membership hash and change file, plus the approval for each approved gated generation. `EtlState.rollbacks(quarter)` returns the quarter's rollback records; after a rollback, they name the generations the lineage no longer shows.

## Not provided

- Roll-forward, pins and dismissal of stale candidates.
- Approver and rollback-operator identity mapping, alerts for pending approvals, and schedules belong to Stage 6.
- Integrated checks, including the rollback rehearsal, belong to Stage 7.
````

- [ ] **Step 4: Update the README**

In `packages/sec-edgar-ingest/README.md`, make these replacements:

1. In the report path, replace `` `runs/sec/<run-id>/<backfill|daily>/<attempt-id>/result.json` `` with `` `runs/sec/<run-id>/<backfill|daily|reconcile>/<attempt-id>/result.json` ``.
2. Replace:

   ```text
   every affected quarter is complete. Closed-quarter removal needs Stage 5 approval; there
   is no workflow force bypass.
   ```

   with:

   ```text
   every affected quarter is complete. Closed-quarter removal needs an explicit `approve`
   (below); there is no workflow force bypass.
   ```

3. Replace:

   ```text
   Exit codes remain: 0 success/no-new/unchanged; 2 invalid inputs or unfinished expired
   deadline; 3 incomplete/discovery failure; 4 pending; 5 retry/deferred/throttled; 6
   access blocked; 7 whole-source quarantine/invalid source; 8 lost ownership; 9
   state/internal/publication conflict; 10 awaiting approval. A publish crash after pointer
   ```

   with:

   ```text
   Exit codes: 0 success/no-new/unchanged; 2 invalid inputs, unfinished expired deadline
   or refused approval/rollback; 3 incomplete/discovery failure; 4 pending; 5 retry/deferred/throttled;
   6 access blocked; 7 whole-source quarantine/invalid source; 8 lost ownership; 9
   state/internal/publication conflict; 10 awaiting approval (gate-only unresolved work, even
   beside completed sources); 11 stale approval/rollback. A publish crash after pointer
   ```

4. Replace `Stage 5 owns reconciliation/approval,` with `Stage 5 provides reconciliation, approval and recorded rollback,`.
5. Insert this paragraph immediately before the line beginning `Offline native and isolated installed-wheel workflow proofs passed`:

   ```markdown
   `reconcile` takes the same arguments as `backfill` and runs through the same workflow runner. Its discovery always refreshes every supported quarterly source. Unchanged bytes report `unchanged`, and corrections publish through the shipped precedence and gate rules. A closed-quarter withdrawal stays `awaiting_approval` until an operator reviews it with `sec-edgar-ingest candidates --config PATH` and activates that exact candidate with `sec-edgar-ingest approve --config PATH --quarter YYYYQn --generation ID --quarterly-sha256 HASH --approver TEXT`. Approval is immutable, the first approval wins, and it binds one candidate generation, so a later download needs its own approval. A newest download that repeats older bytes is reported as a `source_reverted` gap rather than published. `sec-edgar-ingest rollback` then moves the quarter back to the generation that holds those bytes, writing an immutable record first. See the [reconciliation and approval runbook](../../docs/runbooks/sec-edgar-reconciliation-approval.md).

   ```

- [ ] **Step 5: Update the ETL runbook**

In `docs/runbooks/sec-edgar-etl-publication.md`, replace:

```text
against the winning generation. A gated candidate is never current. Stage 3
provides no approval mutation or pointer rollback command; those operations
remain reserved for later authorized work.
```

with:

```text
against the winning generation. A gated candidate is not current until Stage 5's
`approve` activates that exact candidate. Stage 5's `rollback` moves a quarter back
to an earlier generation of its exact lineage, with a record. See the
[reconciliation and approval runbook](sec-edgar-reconciliation-approval.md).
```

- [ ] **Step 6: Run the full offline suite**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -v 2>&1 | tail -5
```

Expected: the final line is `OK` (skips allowed), after roughly 15 minutes. Compare the result with the baseline run from Execution setup.

- [ ] **Step 7: Build the wheel and smoke-test help**

```bash
out="$(mktemp -d)" && uv build --offline --package sec-edgar-ingest --out-dir "$out" && python3 -m zipfile -l "$out"/sec_edgar_ingest-*.whl | grep -E 'sec_edgar_ingest/etl/(approval|history|rollback)\.py'
```

Expected: all three module paths are listed.

```bash
for command in reconcile approve candidates rollback; do uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest "$command" --help >/dev/null || echo "help failed: $command"; done
```

Expected: no output.

- [ ] **Step 8: Check whitespace**

```bash
git -c core.whitespace=cr-at-eol diff --check main...HEAD
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add packages/sec-edgar-ingest/tests/test_reconcile_acceptance.py docs/runbooks/sec-edgar-reconciliation-approval.md docs/runbooks/sec-edgar-etl-publication.md packages/sec-edgar-ingest/README.md
git commit -m "docs: document reconciliation, withdrawal approval and rollback"
```

---

## Stage exit

1. Run the final whole-branch review (subagent-driven-development's closing reviewer). Resolve or consciously defer its findings.
2. Run writing-plans' Plan Completion Protocol. Its deferred-items step must record the owner-deferred limitation from spec §4, whether or not anything else is deferred. Create `specs/deferred_items.md` if it does not exist yet. The item:
   - **What:** a gated member whose source later reverts to its base bytes cannot clear. Each run re-stages the same candidate, and the run stays `awaiting_approval`.
   - **Fix:** let a later completed download of the same source supersede older pending members. This touches `workflows/completion.py` and the runner's member selection.
   - **Size:** plan.
   - **Done when:** that supersession rule lands, with a gated-then-reverted fixture that completes.
3. Add `Stage 5: COMPLETE (<date>) — implemented by plan 6 (specs/plans/completed/6-sec-filing-index-ingestion-stage-5-spec.md)` to the spec's Rollout note (§10).
4. Tick `- [x] Stage 5` in the roadmap and re-validate Stages 6–8 against what shipped. Stage 6 must map the approval and rollback operator roles (spec §5 read/write sets). Stage 7's rollback rehearsal consumes `rollback`.
5. Hand integration (merge, PR or cleanup) back to the owner. Do not merge, push or deploy without that decision.
