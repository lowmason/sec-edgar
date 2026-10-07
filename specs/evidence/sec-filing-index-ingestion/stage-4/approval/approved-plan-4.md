# Stage 4: Backfill and daily catch-up workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver manually runnable baseline and daily workflows with exact source checkpoints, conservative discovery progress and durable complete/pending/failed coverage.

**Architecture:** Add a small workflow layer over the shipped discover/collect/transform/publish command boundaries. Derive complete, exact single-source worksets from successful discovery members, retain their parent bindings and track unresolved processing/publication independently of acquisition state. Commit immutable workflow reports before repairable state indexes; retain per-quarter pointer authority and all existing safety gates.

**Tech Stack:** Python >=3.14, stdlib dataclasses/unittest/SQLite, existing Requests/Azure SDK/PyArrow pins, existing local/Azure object/state adapters and offline guarded fixtures.

## Global Constraints

The following requirements are copied verbatim from the [Stage 4 spec](../sec-filing-index-ingestion-stage-4-spec.md#2-constraints-inherited-by-plan-4); every task inherits them:

- The implementation will live in **`packages/sec-edgar-ingest/`**, with `sec-edgar-ingest` as the distribution and CLI name and `sec_edgar_ingest` as the Python import package.
- `start_quarter` and `end_quarter` are required, inclusive parameters.
- One source file is the checkpoint and retry unit.
- An invalid member prevents a claim of complete coverage, not the retention of work already completed.
- Daily discovery starts at the approved handoff date and replays overlap with the baseline.
- Deduplication handles overlap; a calendar cutover is not trusted to prevent it.
- Also revisit pending and failed source identities regardless of their quarter.
- Never advance discovery past a failed directory read.
- Original bytes are retained.
- Downloaded, transformed and published are different states.
- ETL reads those bytes from ADLS and makes no SEC requests.
- ETL never silently follows a mutable “latest”.
- Refuse malformed rows rather than silently dropping them; quarantine the source and report the line and reason.
- An identical input fingerprint and unchanged versions are a no-op.
- A forced replay may rebuild output, but cannot create a second logical filing.
- A gated candidate is `awaiting_approval`, not current.
- The pointer update is the publication boundary.
- Per-source published flags are recoverable indexes, not a second commit authority.
- Atomicity is **per quarter**, not across the entire historical dataset.
- CI runs on committed fixtures and mocked SEC responses; it downloads nothing from the SEC.

Carry accepted pins unchanged: Python **>=3.14**, Requests **2.34.2**, Identity **1.26.0**, Blob **12.31.0** / **2026-04-06**, Tables **12.7.0** / **2020-12-06**, PyArrow **25.0.1**, existing complete `uv.lock`. No new dependencies. Preserve 90-second exchange, 67,108,864 received-byte and 536,870,912 expanded-byte guards; 3 requests/second/no bursts; one issuer; five total HTTP attempts; accepted 3,600-second worker allowance; 8,192-row ETL batches/SQLite scratch. These are selected limits, not measured deployed fit.

All live-access authorizations remain closed. Use offline evidence and fixtures only. All 22 Stage 7 integrated checks remain reserved/not_run. No SEC/Azure/authentication/compute/provisioning/deployment/image build/network fetch or trigger enablement is authorized. An unavailable cached dependency blocks execution rather than authorizing a fetch or changed pin. Raw/observation/generation/manifest/candidate/quarantine/report retention remains indefinite during development. Existing binding registry/config/workset bytes must not be rewritten.

**Status: PROPOSED (2026-10-07), awaiting owner approval.** No implementation step is authorized by this document.

> Roadmap: specs/sec-filing-index-ingestion-roadmap.md, Stage 4 — on plan completion, tick the
> stage and re-validate later stages against what shipped.

## Authority, preservation and execution preflight

Baseline is merged `main` / local `origin/main` **fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd**. Completed [Stage 3 spec](../completed/sec-filing-index-ingestion-stage-3-spec.md) and [Plan 3](completed/3-sec-filing-index-ingestion-stage-3-spec.md) are authoritative; the untracked originals are historical inputs. Fresh planning preservation is recorded in [reconciliation](../evidence/sec-filing-index-ingestion/stage-4/planning-reconciliation.json). Its protected copy lives at `/private/tmp/sec-edgar-stage4-reconcile-9mbg9qog/retained/`; all 19,089 regular-file copies / 294,547,731 bytes were hash verified. Four incoming byte-identical evidence collisions were moved to `displaced-originals/`, then supplied by the merged tree. Old tracked bytes replaced by the fast-forward also remain in `retained/`.

Required absences remain:

```text
packages/sec-edgar-index-ingest/README.md
packages/sec-edgar-index-ingest/pyproject.toml
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed
```

Before implementation, obtain explicit owner approval of exact spec/plan bytes, record hashes and immutable approved copies, and repeat primary preservation including any subsequent drift. Execute in a managed worktree under `using-git-worktrees`, branch `codex/sec-edgar-stage-4`, based on the approved merged baseline. Do not copy or stage primary historical inputs. Never use `git add -A`, stash, reset or restore in the primary checkout. No need to recreate the archived Stage 3 worktree. Preserve the ignored roadmap's pre-planning bytes and the proposed reconciliation bytes; workspace isolation does not authorize overwriting drift.

Model aliases Opus/Sonnet/Haiku in global instructions are not available in this Codex session; planning uses this session's configured model. At execution resolve actual available review roles/tier mappings through the execution skill; do not claim an unavailable alias was used.

The primary ignored `dist` wheel is historical Stage 2 output (79,085 bytes, SHA `349b9524fca4963de4a2ffdf3fb96f28708c01dba49564594a92944cc3ee5d28`); Stage 3's installed proof names a separate 111,195-byte wheel. Preserve both meanings; do not rebuild the primary to make its output match an archived proof.

## File structure and interfaces

All paths below are relative to the approved execution worktree. The package prefix is `packages/sec-edgar-ingest/`.

| File | Responsibility |
|---|---|
| `src/sec_edgar_ingest/workflows/contracts.py` | Typed workflow/member/result records, exact identities, coverage reducer |
| `src/sec_edgar_ingest/workflows/members.py` | Exact single-member projection and durable unresolved-member registry/receipts |
| `src/sec_edgar_ingest/workflows/steps.py` | Checked existing CLI invocation, exact child results, origin/current settings separation |
| `src/sec_edgar_ingest/workflows/runner.py` | Source sequence, halt/deadline, discovery and report construction |
| `src/sec_edgar_ingest/discovery.py` | Expose unchanged retained-listing validation as public reopen_listing for bootstrap |
| `src/sec_edgar_ingest/workflows/legacy.py` | Verified recovery of pre-Stage4 parent worksets and exact pins |
| `src/sec_edgar_ingest/workflows/results.py` | Frozen WorkflowAttempt intent, immutable report write/read/repair |
| `src/sec_edgar_ingest/workflows/cli.py` | Workflow-only validation/lifecycle/stdout; delegates existing child commands |
| `src/sec_edgar_ingest/cli.py` | Add two command help entries and early workflow routing |
| `tests/test_workflow_contracts.py`, `tests/test_workflow_members.py` | Coverage/projected pins/unresolved-state proofs |
| `tests/test_workflow_steps.py`, `tests/test_workflow_runner.py`, `tests/test_workflow_results.py` | Command/result boundaries, orchestration and crash repair |
| `tests/test_workflow_cli.py`, `tests/test_workflow_offline.py`, `tests/support_workflows.py` | Validation and real fixture end-to-end workflows |
| `tests/fixtures/workflows/{manifest.json,bodies/*,expected.json}` | Compact synthetic raw/listing fixtures and expected coverage |
| `scripts/prove-sec-edgar-workflows.py` | Guarded native/installed-wheel proof and hash inventory |
| `README.md`, `packages/sec-edgar-ingest/README.md`, `docs/runbooks/sec-edgar-workflows.md` | Manual operation, interpretation and recovery |

Create empty `workflows/__init__.py` with module docstring in Task 1. Use existing `Record`/canonical strict JSON codecs, `StateStore`, `ObjectStore`, `AcquisitionState`, `CommandResult`, `EtlResult`, `PublicationResult`. New state kinds default to SourceState via existing `table_for`; no table/container/SDK/registry change is required. Workflow reports use logical `runs/*`, already routed to results. A result belongs to one exact invocation, not a mutable status file.

**Review checkpoint:** each task is independently testable and ends in spec/quality review before proceeding. Task 7 consolidates acceptance; it does not defer task-level tests. Execution must raise any interface/spec deviation before changing the approved plan.

## Task 1: Coverage and workflow result contracts

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/__init__.py`, `.../workflows/contracts.py`; create `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`.

**Interfaces:** Consumes `RunContext`, `Source`, `Error`, `Record`, `PublicationResult`. Produces `MemberResult`, `WorkflowResult`, `member_status(outcome: str) -> str`, `summarize(members: tuple[MemberResult, ...], gaps: tuple[Error, ...], discovered_new: int, unresolved_before: int = 0, command: str = "daily") -> tuple[str, dict[str,int]]`, `workflow_path(context: RunContext) -> str`.

- [ ] **Step 1: Write failing coverage tests.** Use this complete initial test; extend the same table with all `EXIT_CODES` outcomes and unknown outcome refusal before committing.

```python
from network_guard import install
install()
import unittest
from dataclasses import replace
from support import fixture_context, fixture_source
from sec_edgar_ingest.models import Error
from sec_edgar_ingest.workflows.contracts import MemberResult, summarize

class CoverageTests(unittest.TestCase):
    def member(self, outcome='success', quarters=()):
        return MemberResult('a'*64, fixture_source(), 'worksets/sec/source/sha256='+'b'*64+'/workset.json',
                            'worksets/sec/snapshot/sha256='+'c'*64+'/workset.json',
                            'worksets/sec/transformed/sha256='+'d'*64+'/workset.json',
                            ('runs/sec/r/collect/a/result.json',), outcome, True, True, False, quarters, (),
                            'fixture-index-parser-v1', 'sec-index-v1')

    def test_empty_daily_is_not_failure_or_old_backlog(self):
        self.assertEqual(summarize((), (), 0)[0], 'no_new_sources')
        gap = Error('discovery_failed', 'failed', True, None, {})
        self.assertEqual(summarize((), (gap,), 0)[0], 'incomplete')
        pending = replace(self.member(), outcome='pending', transformed=False)
        self.assertEqual(summarize((pending,), (), 0)[0], 'pending')

    def test_valid_progress_does_not_erase_invalid_member(self):
        bad = replace(self.member(), member_id='b'*64, source=fixture_source('2015Q2'), outcome='invalid_source',
                      transformed=False, quarantined=True)
        outcome, counts = summarize((self.member(), bad), (), 2)
        self.assertEqual(outcome, 'incomplete')
        self.assertEqual((counts['complete_sources'], counts['failed_sources'],
                          counts['quarantined_sources']), (1, 1, 1))
        self.assertEqual(summarize((bad,), (), 1)[0], 'quarantined')
```

- [ ] **Step 2: Run red.**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_contracts.py -v
```

Expected: module import failure for `sec_edgar_ingest.workflows`, not a dependency/network error.

- [ ] **Step 3: Implement strict contracts and reducer.** Add this code; all nested fields inherit existing strict `Record` validation. Add post-init checks described directly after it.

```python
from dataclasses import dataclass
from collections.abc import Mapping
from collections import Counter
from ..models import Record, RunContext, Source, Error, require_hash, safe_relative_path, require_utc, require_number, quarter_value, validate_record_fields
from ..etl.commands import validate_workset_ref
from datetime import date, datetime
import re
from ..results import exit_code
from ..etl.contracts import PublicationResult

COMPLETE = frozenset(('success', 'unchanged', 'no_new_sources'))
PENDING = frozenset(('pending', 'deferred', 'throttled', 'awaiting_approval'))
FATAL = ('access_blocked', 'ownership_lost', 'state_conflict', 'internal_error')

@dataclass(frozen=True, slots=True)
class MemberResult(Record):
    member_id: str
    source: Source
    parent_ref: str
    snapshot_ref: str | None
    transformed_ref: str | None
    child_refs: tuple[str, ...]
    outcome: str
    downloaded: bool
    transformed: bool
    quarantined: bool
    quarters: tuple[PublicationResult, ...]
    gaps: tuple[Error, ...]
    parser_version: str
    schema_version: str

    def __post_init__(self):
        validate_record_fields(self)
        require_hash(self.member_id, 'member_id')
        member_status(self.outcome)
        if re.fullmatch(r'worksets/sec/source/sha256=[0-9a-f]{64}/workset\.json', self.parent_ref) is None:
            raise ValueError('invalid member parent reference')
        for ref,kind in ((self.snapshot_ref,'snapshot'),(self.transformed_ref,'transformed')):
            if ref is not None:
                validate_workset_ref(ref,kind)
        for ref in self.child_refs:
            if re.fullmatch(r'runs/sec/[^/]+/(collect|transform|publish)/[^/]+/result\.json',ref) is None:
                raise ValueError('invalid child result reference')
            safe_relative_path(ref,'child_ref')
        if self.schema_version != 'sec-index-v1' or self.parser_version not in (
                'sec-index-parser-v1','fixture-index-parser-v1','fixture-index-parser-v2'):
            raise ValueError('unsupported member processing versions')
        if len({q.quarter for q in self.quarters}) != len(self.quarters):
            raise ValueError('duplicate member quarter results')
        if self.outcome in COMPLETE and (not self.snapshot_ref or not self.transformed_ref or
                any(q.outcome not in ('published','unchanged') for q in self.quarters)):
            raise ValueError('complete member lacks successful ETL/publication captures')
        if self.quarantined and (self.transformed or self.outcome in COMPLETE):
            raise ValueError('quarantined member cannot claim accepted transform')

@dataclass(frozen=True, slots=True)
class WorkflowResult(Record):
    format_version: str
    context: RunContext
    intent: Mapping[str, object]
    source_workset_ref: str | None
    requested_quarters: tuple[str, ...]
    directories: tuple[Mapping[str, object], ...]
    members: tuple[MemberResult, ...]
    gaps: tuple[Error, ...]
    boundary_before: str | None
    boundary_after: str | None
    outcome: str
    counts: Mapping[str, int]
    ended_at: str

    def __post_init__(self):
        validate_record_fields(self)
        if self.format_version != 'sec-workflow-result-v1':
            raise ValueError('unsupported workflow result version')
        workflow_path(self.context)
        ended = datetime.fromisoformat(self.ended_at)
        require_utc(ended,'ended_at')
        if ended < self.context.started_at:
            raise ValueError('workflow ended before start')
        if len({m.member_id for m in self.members}) != len(self.members):
            raise ValueError('duplicate workflow member IDs')
        if self.source_workset_ref is not None and re.fullmatch(
                r'worksets/sec/source/sha256=[0-9a-f]{64}/workset\.json',self.source_workset_ref) is None:
            raise ValueError('invalid workflow discovery reference')
        for key in ('discovered_sources','unresolved_before'):
            require_number(self.intent[key],key,integer=True)
        outcome,counts = summarize(self.members,self.gaps,self.intent['discovered_sources'],
                                   self.intent['unresolved_before'],self.context.command)
        already = tuple(self.intent.get('already_complete_sources', ()))
        if len(set(already)) != len(already) or set(already) & {m.source.source_id for m in self.members}:
            raise ValueError('already-complete source set overlaps or duplicates selected results')
        for identity in already:
            require_hash(identity,'already_complete_source')
        counts['complete_sources'] += len(already)
        if self.outcome != outcome or self.to_mapping()['counts'] != counts:
            raise ValueError('workflow counters/outcome disagree with exact members/gaps')
        ordered = tuple(sorted(self.requested_quarters,key=quarter_value))
        if ordered != self.requested_quarters or len(set(ordered)) != len(ordered):
            raise ValueError('invalid requested quarter ordering')
        for value in (self.boundary_before,self.boundary_after):
            if value is not None and date.fromisoformat(value).isoformat() != value:
                raise ValueError('invalid discovery boundary date')

def member_status(outcome):
    exit_code(outcome)
    return 'complete' if outcome in COMPLETE else 'pending' if outcome in PENDING else 'failed'

def summarize(members, gaps, discovered_new, unresolved_before=0, command="daily"):
    grouped = {}
    rank = {'complete': 0, 'pending': 1, 'failed': 2}
    for member in members:
        identity = member.source.source_id
        status = member_status(member.outcome)
        if identity not in grouped or rank[status] > rank[grouped[identity]]:
            grouped[identity] = status
    states = Counter(grouped.values())
    counts = {name+'_sources': states[name] for name in ('complete', 'pending', 'failed')}
    counts.update(discovered_sources=discovered_new,
                  downloaded_sources=len({m.source.source_id for m in members if m.downloaded}),
                  transformed_sources=len({m.source.source_id for m in members if m.transformed}),
                  quarantined_sources=len({m.source.source_id for m in members if m.quarantined}))
    quarters = Counter(q.outcome for m in members for q in m.quarters)
    counts.update(published_quarters=quarters['published'],
                  unchanged_quarters=quarters['unchanged'],
                  awaiting_approval_quarters=quarters['awaiting_approval'])
    outcomes = {m.outcome for m in members} | {g.code for g in gaps}
    fatal = next((o for o in FATAL if o in outcomes), None)
    if fatal:
        return fatal, counts
    if gaps or (states['complete'] and (states['failed'] or states['pending'])):
        return 'incomplete', counts
    if states['failed']:
        if all(m.quarantined for m in members):
            return 'quarantined', counts
        return 'incomplete', counts
    if states['pending']:
        return ('awaiting_approval' if outcomes == {'awaiting_approval'} else 'pending'), counts
    if not members:
        return ('no_new_sources' if command == 'daily' else 'unchanged'), counts
    if command == 'daily' and not discovered_new and not unresolved_before and not counts['published_quarters']:
        return 'no_new_sources', counts
    return ('success' if counts['published_quarters'] else 'unchanged'), counts

def workflow_path(context):
    if context.command not in ('backfill', 'daily'):
        raise ValueError('workflow command required')
    for name in ('run_id', 'execution_id', 'attempt_id'):
        if '/' in safe_relative_path(getattr(context, name), name):
            raise ValueError('workflow IDs require one segment')
    return f'runs/sec/{context.run_id}/{context.command}/{context.attempt_id}/result.json'
```

The post-init code above is part of each class. Add a `WorkflowResult.from_mapping(result.to_mapping()) == result` roundtrip with real nested Mapping/DirectoryOutcome fields; generic `dict[...]` is unsupported by the existing Record decoder. Reject invalid refs, duplicate quarters/IDs, invented success, changed counts and invalid UTC/end ordering. Full reference authority is checked against stored objects in Tasks 2–4; structural validation alone never supplies successful publication authority. Zero-output valid sources can complete with no quarters. Do not broaden existing `read_result` to guess workflow types.

Add this strict nested-record roundtrip test to `CoverageTests` before green:

```python
    def test_workflow_mapping_roundtrip_and_counter_refusal(self):
        from datetime import datetime,timezone
        from dataclasses import replace
        from sec_edgar_ingest.workflows.contracts import WorkflowResult
        context=replace(fixture_context(),command='daily')
        member=self.member()
        outcome,counts=summarize((member,),(),1,0,'daily')
        result=WorkflowResult('sec-workflow-result-v1',context,
            {'invocation':{},'discovered_sources':1,'unresolved_before':0,
             'already_complete_sources':[]},
            'worksets/sec/source/sha256='+'b'*64+'/workset.json',(),(),(member,),(),
            None,None,outcome,counts,datetime.now(timezone.utc).isoformat())
        self.assertEqual(WorkflowResult.from_mapping(result.to_mapping()),result)
        wrong=result.to_mapping()
        wrong['counts']['complete_sources']=2
        with self.assertRaises(ValueError):
            WorkflowResult.from_mapping(wrong)
```

- [ ] **Step 4: Run green and rejection cases.** Repeat Step 2; all coverage/invalid-counter/ref/outcome cases PASS.
- [ ] **Step 5: Commit explicit files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/__init__.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py packages/sec-edgar-ingest/tests/test_workflow_contracts.py
git commit -m "feat: define workflow coverage and report contracts"
```

## Task 2: Exact source projections and unresolved-member retention

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py`, `packages/sec-edgar-ingest/tests/test_workflow_members.py`.

**Interfaces:** Consumes strict source-workset codec, canonical bytes and state/object adapters. Produces `project_member(parent_ref: str, source_id: str, objects: ObjectStore) -> str`; `WorkflowMembers.register(parent_ref, member_ref)`, `pending(parser_version, schema_version) -> tuple[dict,...]`, `record(result: MemberResult, context: RunContext) -> None`. Registry values contain member ID, source mapping, parent ref and projected ref; result receipt key includes run/command/attempt/member/current versions.

- [ ] **Step 1: Write failing projection/retention tests.** Initial complete test body:

```python
from network_guard import install
install()
import unittest, tempfile
from pathlib import Path
from support import fixture_source, fixture_workset, store_bundle, fixture_context
from sec_edgar_ingest.worksets import encode_workset, decode_source_workset
from sec_edgar_ingest.workflows.members import project_member, WorkflowMembers

class MemberTests(unittest.TestCase):
    def test_successful_member_of_incomplete_parent_is_exact_and_durable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, objects, leases = store_bundle(Path(tmp))
            try:
                source = fixture_source()
                parent = fixture_workset((source,), discovery_complete=False)
                ref = f'worksets/sec/source/sha256={parent.workset_id}/workset.json'
                objects.put_once(ref, encode_workset(parent))
                projected_ref = project_member(ref, source.source_id, objects)
                child = decode_source_workset(objects.read(projected_ref))
                self.assertTrue(child.discovery_complete)
                self.assertFalse(parent.discovery_complete)
                self.assertEqual(child.members, (source,))
                self.assertEqual(child.context, parent.context)
                registry = WorkflowMembers(store, objects)
                registry.register(ref, projected_ref)
                self.assertEqual(len(registry.pending('fixture-index-parser-v1', 'sec-index-v1')), 1)
            finally:
                leases.close(); store.close()
```

Add refusal tests before green for wrong parent/ref, source not in parent, altered source/period/listing hash, ambiguous membership, missing raw refs, immutable-member replacement. Add retained downloaded-but-untransformed, gated, partially published and current-version replay receipts; old-version success cannot clear new-version pending. Reopen the real store to show registry is durable.

- [ ] **Step 2: Run red.** Same guarded discover command, pattern `test_workflow_members.py`; expected missing module/API.
- [ ] **Step 3: Implement exact projection and immutable registry.**

```python
import hashlib
from dataclasses import replace
from ..models import canonical_json
from ..worksets import decode_source_workset, make_source_workset, encode_workset
from ..storage.contracts import AlreadyExists, Conflict
from .contracts import MemberResult, member_status

def source_ref(workset):
    return f'worksets/sec/source/sha256={workset.workset_id}/workset.json'

def read_source(ref, objects):
    body = objects.read(ref)
    workset = decode_source_workset(body)
    if source_ref(workset) != ref or encode_workset(workset) != body:
        raise Conflict('noncanonical source-workset reference')
    return workset

def project_member(parent_ref, identity, objects):
    parent = read_source(parent_ref, objects)
    selected = [s for s in parent.members if s.source_id == identity]
    if len(selected) != 1:
        raise Conflict('projection requires one exact original member')
    directories = [d for d in parent.directories if identity in d.source_ids]
    if len(directories) != 1 or directories[0].outcome == 'discovery_failed':
        raise Conflict('projection requires successful immediate directory evidence')
    directory = replace(directories[0], source_ids=(identity,))
    unit_id = hashlib.sha256(canonical_json([parent.workset_id, identity])).hexdigest()
    member = make_source_workset(parent.context, parent.pinned_end_quarter,
                                'member-'+unit_id, tuple(selected), (directory,),
                                parent.overlap_from, acquisition_mode=parent.acquisition_mode)
    body = encode_workset(member)
    ref = source_ref(member)
    objects.put_once(ref, body)
    objects.verify(ref, hashlib.sha256(body).hexdigest(), len(body))
    return ref

class WorkflowMembers:
    def __init__(self, store, objects):
        self.store, self.objects = store, objects

    def immutable(self, kind, key, value):
        try:
            self.store.insert(kind, key, value)
        except AlreadyExists:
            row = self.store.get(kind, key)
            if row is None or row.to_mapping()['value'] != value:
                raise Conflict(kind+' immutable identity changed')

    def register(self, parent_ref, member_ref):
        member = read_source(member_ref, self.objects)
        if len(member.members) != 1:
            raise Conflict('workflow member must be singleton')
        expected = project_member(parent_ref, member.members[0].source_id, self.objects)
        if expected != member_ref:
            raise Conflict('workflow member differs from exact parent projection')
        value = {'member_id': member.workset_id, 'source': member.members[0].to_mapping(),
                 'parent_ref': parent_ref, 'member_ref': member_ref}
        self.immutable('WorkflowMember', member.workset_id, value)
        return value

    def record(self, result, context):
        row = self.store.get('WorkflowMember', result.member_id)
        if row is None or row.value['parent_ref'] != result.parent_ref:
            raise Conflict('member receipt lacks its registered parent')
        if row.to_mapping()['value']['source'] != result.source.to_mapping():
            raise Conflict('member receipt changes original source')
        value = {'context': context.to_mapping(), 'member_id': result.member_id,
                 'parser_version': result.parser_version, 'schema_version': result.schema_version,
                 'complete': member_status(result.outcome) == 'complete',
                 'result': result.to_mapping()}
        key = hashlib.sha256(canonical_json([context.run_id, context.command,
                   context.attempt_id, result.member_id, result.parser_version,
                   result.schema_version])).hexdigest()
        self.immutable('WorkflowMemberResult', key, value)

    def pending(self, parser_version, schema_version):
        complete = {row.value['member_id'] for row in self.store.scan('WorkflowMemberResult',
                    {'parser_version': parser_version, 'schema_version': schema_version,
                     'complete': True})}
        values = [row.to_mapping()['value'] for row in self.store.scan('WorkflowMember', {})
                  if row.value['member_id'] not in complete and not current_complete(
                      row.to_mapping()['value'],parser_version,schema_version,self.store,self.objects)]
        for value in values:
            self.register(value['parent_ref'], value['member_ref'])
        return tuple(sorted(values, key=lambda v: (v['source']['period'],
                         v['source']['source_id'], v['member_id'])))
```

Strengthen `record` with authoritative child validation in Task 3: only a checked `MemberResult` built from exact stored child results can mark complete. On `pending`, decode each successful receipt and revalidate its child refs/pointer captures; missing/corrupt receipts fail closed. Avoid a source-only latest pointer. Add SHA/path/current-version/ref binding tests rather than trusting a caller's `complete=True`.

- [ ] **Step 4: Run green.** Guarded `test_workflow_members.py`, all tests PASS; inspect SourceState unchanged acquisition records/config registry.
- [ ] **Step 5: Commit explicit files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/tests/test_workflow_members.py
git commit -m "feat: retain exact workflow members and unresolved processing"
```

## Task 3: Checked child execution and source completion

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/steps.py`, `packages/sec-edgar-ingest/tests/test_workflow_steps.py`; strengthen receipt validation in `.../workflows/members.py`.

**Interfaces:** Consumes existing `cli.main`, `read_result`, `read_etl_result` and exact registry members. Produces `StepRunner(context, settings, fixture_pack, state_dir, objects, observer=None)`, `runner.execute(command: str, step_id: str, settings: Settings, flags: list[str]) -> CommandResult | EtlResult`, `runner.member(value: dict) -> MemberResult`. Fatal/no-durable-result errors raise `StepFailure(outcome, details)` and retain child invocation evidence; post-CAS repair errors remain resumable, never finalized as success.

- [ ] **Step 1: Write failing execution-boundary tests.** Start with a real `seed_snapshot` transform/publish and wrap the CLI to corrupt only stdout; result readback must decide success. Test fabricated result_ref/correlation, mismatched parser/fixture hash, unknown outcome and nonzero exit carrying valid partial quarter captures. Supply this child-spy assertion in each test:

```python
with patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('live sender')):
    result = runner.execute('transform', 'transform-'+member_id,
                            settings, ['--workset', snapshot_ref])
self.assertEqual(result.context.command, 'transform')
self.assertEqual(result.input_ref, snapshot_ref)
self.assertEqual(len(list(store.scan('TransportAttempt', {}))), 0)
```

Use `support_etl.etl_context`, `seed_snapshot`, `support.store_bundle`, `fixture_source`; the configured parser must be `fixture-index-parser-v1`. Test real collection using a complete fixture pack and exact projected origin config, then changed current parser `fixture-index-parser-v2` transformation. Tests require all child identity checks, not just matching exit code.

- [ ] **Step 2: Run red.** Guarded pattern `test_workflow_steps.py`; expected missing `StepRunner`.
- [ ] **Step 3: Implement a checked adapter around the existing command lifecycle.** Core dispatch:

```python
import contextlib, hashlib, io, tempfile
from pathlib import Path
from ..config import Settings
from ..models import canonical_json, parse_json, RunContext, Source
from ..results import read_result, result_path, exit_code
from ..etl.commands import read_etl_result
from ..storage.contracts import Conflict, observe
from .contracts import MemberResult, COMPLETE
from .members import read_source

class StepFailure(RuntimeError):
    def __init__(self, outcome, details):
        super().__init__(outcome)
        self.outcome, self.details = outcome, details

class StepRunner:
    def __init__(self, context, settings, fixture_pack, state_dir, objects, observer=None):
        self.context, self.settings = context, settings
        self.fixture_pack, self.state_dir = fixture_pack, state_dir
        self.objects, self.observer = objects, observer

    def execute(self, command, step_id, settings, flags):
        from ..cli import main
        attempt = self.context.attempt_id+'-'+hashlib.sha256(step_id.encode()).hexdigest()
        with tempfile.TemporaryDirectory(prefix='sec-workflow-config-') as tmp:
            config = Path(tmp)/'config.json'
            config.write_bytes(canonical_json(settings.to_mapping()))
            argv = [command, '--config', str(config), '--run-id', self.context.run_id,
                    '--execution-id', self.context.execution_id, '--attempt-id', attempt,
                    '--deadline', self.context.deadline.isoformat(), *flags]
            if settings.storage.backend == 'local-fixture':
                argv += ['--today', self.context.pinned_on.isoformat()]
                if self.state_dir is not None:
                    argv += ['--state-dir', str(self.state_dir)]
                if command in ('discover', 'collect'):
                    argv += ['--fixture-pack', str(self.fixture_pack)]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(argv)
        message = parse_json(output.getvalue())
        expected_ref = f'runs/sec/{self.context.run_id}/{command}/{attempt}/result.json'
        if message.get('result_ref') is None:
            raise StepFailure(message['outcome'], {'step_id': step_id, 'stdout': message})
        if message['result_ref'] != expected_ref:
            raise Conflict('child returned another command result path')
        read = read_etl_result if command in ('transform', 'publish') else read_result
        result = read(expected_ref, self.objects)
        expected = (self.context.run_id, self.context.execution_id, command, attempt,
                    settings.config_sha256, settings.worker.image_digest,
                    settings.etl.parser_version, settings.etl.schema_version,
                    self.context.deadline)
        actual = tuple(getattr(result.context, name) for name in ('run_id','execution_id',
                    'command','attempt_id','config_sha256','image_digest','parser_version',
                    'schema_version','deadline'))
        if actual != expected or code != exit_code(result.outcome):
            raise Conflict('child durable result has mismatched intent or exit')
        observe(self.observer, 'workflow.after_child')
        return result

    def member(self, value):
        source_set = read_source(value['member_ref'], self.objects)
        origin = Settings.from_mapping(source_set.context.to_mapping()['effective_config'])
        source = source_set.members[0]
        child_refs, quarters, gaps = [], (), ()
        snapshot_ref = transformed_ref = None
        downloaded = transformed = quarantined = False
        collected = self.execute('collect', 'collect-'+value['member_id'], origin,
                                 ['--workset', value['member_ref']])
        child_refs.append(result_path(collected.context))
        snapshot_ref = collected.snapshot_workset_ref
        outcome, gaps = collected.outcome, collected.gaps
        downloaded, quarantined = snapshot_ref is not None, bool(collected.quarantined)
        if snapshot_ref is not None and collected.outcome in COMPLETE:
            parsed = self.execute('transform', 'transform-'+value['member_id'], self.settings,
                                  ['--workset', snapshot_ref])
            child_refs.append(result_path(parsed.context))
            transformed_ref = parsed.transformed_workset_ref
            outcome, gaps = parsed.outcome, parsed.gaps
            transformed = bool(parsed.transformed or parsed.unchanged)
            quarantined = quarantined or bool(parsed.quarantined)
            if parsed.outcome in COMPLETE:
                published = self.execute('publish', 'publish-'+value['member_id'], self.settings,
                                         ['--workset', transformed_ref])
                child_refs.append(result_path(published.context))
                outcome, gaps, quarters = published.outcome, published.gaps, published.quarters
        return MemberResult(value['member_id'], source, value['parent_ref'], snapshot_ref,
                            transformed_ref, tuple(child_refs), outcome, downloaded,
                            transformed, quarantined, quarters, tuple(gaps),
                            self.context.parser_version, self.context.schema_version)
```

Before dispatch, compare `FixturePack.load(...).manifest_sha256` with the frozen workflow intent; preserve explicit fixture provenance. Verify every `--workset` input against the returned `source_workset_ref` or `input_ref`. Decode collect's snapshot workset and prove exact projected source membership/binding, then transform's exact observations, then publish's exact transformed ref. `member()` must accumulate all child gaps, not replace preceding nonempty gaps. Validated success requires all affected quarters represented (derive using Stage 3's authoritative publication workset/active manifest rules); no quarter may disappear. Preserve each exact original child result and captured generation rather than reducing to source success.

A `StepFailure` with `result_ref=None` may represent interrupted publish repair. Inspect the existing Attempt/intent and error details: if retryable `PublicationRepairPending` or interrupted unfinished child, propagate a resumable exception to Task 4, leaving workflow/member receipts unfinished. Otherwise build a failed member receipt carrying structured error and any returned partial-quarter details. Halt codes stop later requests. Malformed/absent stdout is a state conflict with durable invocation evidence; never substitute empty success. The CLI itself keeps stdout JSON and existing child intent/result repair; do not duplicate sender/state logic in workflow code.

For an unfinished Azure workflow resumed on another pin date, return pending requiring a new run before creating new children; an exact saved completed child may replay. Fixture clock override remains explicitly marked. Each retry obtains new child attempt IDs through a new workflow attempt; completed failures are never rewritten.

- [ ] **Step 4: Run green including origin/current-version and post-CAS repair cases.** Guarded `test_workflow_steps.py` PASS; re-run `test_etl_cli.py` and `test_cli.py` to confirm no existing command regression.
- [ ] **Step 5: Commit explicit files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/steps.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/tests/test_workflow_steps.py
git commit -m "feat: compose checked acquisition and ETL command boundaries"
```

## Task 4: Backfill/daily orchestration, legacy backlog and durable report repair

**Files:** Create `packages/sec-edgar-ingest/tests/support_workflows.py` (fixture builders/harness in this task, extended in Task 6), `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py`, `.../workflows/results.py`, `.../workflows/legacy.py` (verified legacy source-parent lookup), modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py` (`_reopen_listing` definition/call at lines 240/301), `packages/sec-edgar-ingest/tests/test_workflow_runner.py`, `.../test_workflow_results.py`; extend `.../workflows/members.py`, `.../tests/test_workflow_members.py` for legacy bootstrap.

**Interfaces:** Produces `run_workflow(context: RunContext, settings: Settings, intent: dict, steps: StepRunner, store: StateStore, objects: ObjectStore, observer=None) -> WorkflowResult`; `freeze_workflow(current: RunContext, intent: dict, store, objects) -> RunContext`; `write_workflow_result(result, store, objects, observer=None) -> str`; `read_workflow_result(path, objects) -> WorkflowResult`; `bootstrap_legacy(store, objects, registry, current_versions) -> tuple[Error,...]`. Consumes Task 1–3 types. WorkflowAttempt remains in SourceState; explicitly test that routing and content-first large-record descriptor behavior. Existing Attempts table remains for child command attempts; no new physical table.

- [ ] **Step 1: Write red orchestration and crash tests.** Use a recording `StepRunner` over actual local object/state stores, then real child commands in Task 6. Initial failure sequence:

```python
from network_guard import install
install()
import unittest, tempfile
from pathlib import Path
from support_workflows import WorkflowHarness

class WorkflowRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.harness = WorkflowHarness(Path(self.temp.name))
        self.addCleanup(self.harness.close)

    def test_failed_directory_keeps_boundary_but_valid_source_finishes(self):
        result = self.harness.run('daily', scenario='failed-directory-and-valid-source')
        self.assertEqual(result.boundary_before, result.boundary_after)
        self.assertEqual(result.outcome, 'incomplete')
        self.assertEqual(result.counts['complete_sources'], 1)
        self.assertTrue(any(g.code == 'discovery_failed' for g in result.gaps))
        self.assertEqual(result.members[0].quarters[0].outcome, 'published')

    def test_legacy_downloaded_backlog_survives_absent_fresh_listing(self):
        self.harness.seed_legacy(downloaded=True, published=False)
        self.assertEqual(list(self.harness.store.scan('WorkflowMember', {})), [])
        result = self.harness.run('daily', scenario='empty-valid-listings')
        self.assertEqual(result.counts['complete_sources'], 1)
        self.assertNotEqual(result.outcome, 'no_new_sources')
        self.assertEqual(self.harness.transport_requests_for_legacy_body(), self.harness.legacy_requests)
```

`harness` is a test-owned fixture service created in this task as `support_workflows.WorkflowHarness` (code below; Task 6 extends scenarios); for this task build it from the interfaces in this plan using a recording checked child runner and real stores, not a fake production state machine. Its scenario IDs and expected outcomes are defined in Task 6. Cover expired-deadline undispatched work, fatal first member preventing second fetch, quarantine plus valid member, missing quarterly source, gate, multi-output-quarter partial commit, and same-attempt replay with no child calls. Crash tests raise after child result / after member receipt / after report object / before WorkflowAttempt finish; exact retry returns identical refs/bytes and repairs indexes with no second pointer advance. A corrupt report or changed intent refuses.

- [ ] **Step 2: Run red.** Guarded patterns `test_workflow_runner.py` and `test_workflow_results.py`; expected absent APIs, not unavailable fixtures or cache.
- [ ] **Step 3: Implement frozen intent/report commit and orchestrator.** Report commit core:

```python
import hashlib
from datetime import datetime, timezone
from ..models import RunContext, canonical_json, parse_json
from ..storage.contracts import AlreadyExists, CAS_ATTEMPTS, Conflict, observe
from .contracts import WorkflowResult, workflow_path

def workflow_key(context):
    return hashlib.sha256(canonical_json([context.run_id, context.command,
                                         context.attempt_id])).hexdigest()

def freeze_workflow(current, intent, store, objects):
    path = workflow_path(current).replace('result.json', 'intent.json')
    key = workflow_key(current)
    for _ in range(CAS_ATTEMPTS):
        row = store.get('WorkflowAttempt', key)
        saved = current if row is None else RunContext.from_mapping(row.to_mapping()['value']['context'])
        expected, actual = current.to_mapping(), saved.to_mapping()
        expected['started_at'] = actual['started_at']
        if expected != actual:
            raise Conflict('workflow correlation/config/date/deadline changed')
        value = {'context': saved.to_mapping(), 'intent': intent, 'result_ref': None}
        if row is None:
            try:
                store.insert('WorkflowAttempt', key, value)
            except AlreadyExists:
                continue
        elif row.to_mapping()['value']['intent'] != intent:
            raise Conflict('workflow frozen intent changed')
        body = canonical_json({'context':saved.to_mapping(),'intent':intent})
        objects.put_once(path, body)
        objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
        if objects.read(path) != body:
            raise Conflict('workflow intent bytes changed')
        return saved
    raise Conflict('workflow begin exhausted CAS')

def read_workflow_result(path, objects):
    body = objects.read(path)
    result = WorkflowResult.from_mapping(parse_json(body))
    if workflow_path(result.context) != path or canonical_json(result.to_mapping()) != body:
        raise Conflict('workflow result identity/bytes changed')
    return result

def write_workflow_result(result, store, objects, observer=None):
    path = workflow_path(result.context)
    key = workflow_key(result.context)
    row = store.get('WorkflowAttempt', key)
    if row is None or row.to_mapping()['value']['context'] != result.context.to_mapping():
        raise Conflict('workflow result lacks exact frozen attempt')
    # Selection/count bookkeeping belongs in report, not the original invocation intent.
    if result.intent['invocation'] != row.to_mapping()['value']['intent']:
        raise Conflict('workflow result differs from frozen invocation')
    body = canonical_json(result.to_mapping())
    objects.put_once(path, body)
    objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
    observe(observer, 'workflow.after_report_object')
    for _ in range(CAS_ATTEMPTS):
        row = store.get('WorkflowAttempt', key)
        value = row.to_mapping()['value']
        descriptor = {'ref': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
        if value['result_ref'] is not None:
            if value['result_ref'] != descriptor:
                raise Conflict('workflow attempt result cannot be replaced')
            return path
        value['result_ref'] = descriptor
        try:
            store.replace('WorkflowAttempt', key, value, row.version)
            observe(observer, 'workflow.after_attempt_finish')
            return path
        except Conflict:
            continue
    raise Conflict('workflow report index repair exhausted CAS')
```

Read `intent.json` as well as the state row and require exact canonical equality, so either side's corruption fails closed. A report object with missing row cannot create an invented invocation; recover only from its exact retained intent and begun context. Completed replay validates report/ref/hash/length, invocation and child captures, repairs WorkflowAttempt, then returns before creating StepRunner/sender. Expired deadline allows only this completed replay; unfinished work requires a fresh valid attempt.

Orchestration uses the complete final selection/runner code in the Task 4 implementation detail below. Its queue is frozen before member dispatch, and exact retry consumes that selection. Legacy upgrade reads original AcquisitionState/Processing and verified parent refs before queue selection; no empty new ledger can hide old work.

- [ ] **Step 4: Run green and real store crash replays.** Guarded patterns from Step 2 PASS. Recheck original AcquisitionState boundary tests (`test_discovery.py`) and strict whole-workset ETL publication tests (`test_etl_publication.py`) remain unchanged.
- [ ] **Step 5: Commit explicit files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py packages/sec-edgar-ingest/tests/support_workflows.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/legacy.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/tests/test_workflow_runner.py packages/sec-edgar-ingest/tests/test_workflow_results.py packages/sec-edgar-ingest/tests/test_workflow_members.py
git commit -m "feat: compose workflows with legacy backlog and durable reports"
```

### Task 4 implementation detail: verified legacy bootstrap

Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/legacy.py` as part of Task 4. This is the defined `bootstrap_legacy` API consumed by `runner.py`. Its minimum safe implementation performs exact parent recovery and pinned-binding transfer; uncertain prior publication is deliberately rechecked through existing ETL rather than falsely marked complete.

```python
from datetime import date
from ..config import Settings
from ..models import Source, Binding, DirectoryOutcome, Error, RunContext, canonical_json
from ..state import AcquisitionState
from ..worksets import make_source_workset, encode_workset, decode_snapshot_workset
from ..discovery import _reopen_listing
from ..storage.contracts import Conflict
from .members import read_source, project_member, source_ref

def bootstrap_legacy(store, objects, registry, current_versions):
    parents, gaps = {}, []
    registered={row.value['member_ref']:row.to_mapping()['value'] for row in store.scan('WorkflowMember',{})}
    def retain_parent(ref):
        if ref in registered:
            value=registered[ref]
            registry.register(value['parent_ref'],value['member_ref'])
            return
        parent = read_source(ref, objects)
        parents[parent.workset_id] = (ref, parent)
    for row in store.scan('DiscoverySession', {}):
        value = row.to_mapping()['value']
        identities = {value.get('workset_id'), value.get('predecessor_workset_id')}
        identities.update(h['workset_id'] for h in value.get('history', []))
        for identity in sorted(i for i in identities if i):
            ref = f'worksets/sec/source/sha256={identity}/workset.json'
            try:
                retain_parent(ref)
            except (ValueError, OSError, Conflict) as error:
                gaps.append(Error('legacy_member_unresolved', str(error), False, None, {'parent_ref':ref}))
        frozen = value['frozen']
        origin = RunContext.from_mapping(frozen['context'])
        outcomes, members = [], {}
        for unit in frozen['units']:
            progress = AcquisitionState(store).directory_progress(value['discovery_id'],unit['url'])
            if progress is None:
                outcome = DirectoryOutcome(unit['url'],unit['period'],'discovery_failed',None,(),
                    Error('discovery_pending','legacy directory has no retained completion',True,None,{}))
            else:
                saved = progress.to_mapping()['value']
                outcome = DirectoryOutcome.from_mapping(saved['outcome'])
                if outcome.outcome != 'discovery_failed':
                    outcome, selected, entries, at = _reopen_listing(objects,saved,unit,origin)
                    for source in selected:
                        members[source.source_id] = source
            outcomes.append(outcome)
        parent = make_source_workset(origin, frozen['end'], value['discovery_id'],
            tuple(members.values()),tuple(outcomes),date.fromisoformat(frozen['overlap_from']),
            acquisition_mode=frozen['acquisition_mode'])
        ref = source_ref(parent)
        objects.put_once(ref,encode_workset(parent))
        retain_parent(ref)
    for row in store.scan('Attempt', {}):
        result = row.to_mapping()['value'].get('result')
        if not result:
            continue
        ref = result.get('source_workset_ref')
        if ref:
            retain_parent(ref)
        snapshot_ref = result.get('snapshot_workset_ref')
        if result['context']['command']=='transform':
            snapshot_ref = result.get('input_ref')
        if snapshot_ref:
            snapshots = decode_snapshot_workset(objects.read(snapshot_ref))
            retain_parent(f'worksets/sec/source/sha256={snapshots.source_workset_id}/workset.json')
    acquisition = AcquisitionState(store)
    sources = {row.value['source']['source_id']:Source.from_mapping(row.to_mapping()['value']['source'])
               for row in store.scan('Source', {})}
    for row in store.scan('Processing', {}):
        source = Source.from_mapping(row.to_mapping()['value']['observation']['source'])
        sources[source.source_id] = source
    covered = {value['source']['source_id'] for value in registered.values()}
    for ref,parent in sorted(parents.values()):
        for source in parent.members:
            member_ref = project_member(ref,source.source_id,objects)
            member = read_source(member_ref,objects)
            registry.register(ref,member_ref)
            covered.add(source.source_id)
            binding = acquisition.binding(parent.workset_id,source.source_id)
            if binding is not None:
                snapshot = acquisition.snapshot(source.source_id,binding.snapshot_sha256)
                objects.verify(snapshot.raw_path,snapshot.sha256,snapshot.byte_count)
                acquisition.bind_once(Binding(member.workset_id,source.source_id,snapshot.sha256))
    for identity,source in sorted(sources.items()):
        if identity not in covered:
            gaps.append(Error('legacy_member_unresolved','no verified retained parent source workset',
                              True,identity,{'source':source.to_mapping()}))
    return tuple(gaps)
```

Never project a registered singleton as a new parent: the exact registered-ref filter above prevents projection-of-projection growth. Add three repeated daily runs asserting registry cardinality grows only with genuinely new discovery projections, old queue cardinality stays zero, and no member parent_ref is another registered singleton member_ref. Treat exceptions per session/parent as explicit legacy gaps so one damaged legacy record does not hide others. Promote `_reopen_listing` to public `reopen_listing` with unchanged logic and update its callers/tests in the same task; private-helper import above becomes that exact public import. Old source sets include failed directories but only successful exact members project. Do not reconstruct when saved progress/evidence is corrupt. Test reconstruction after a crash before parent object, including all missing required units. Reconstructed parent does not replace the old DiscoverySession or mutate old worksets.

The concrete `current_complete` helper below supplies current-pointer membership checks for legacy already-published work; no `WorkflowLegacyComplete` kind is added. A missing/corrupt/changed quarter membership remains pending.

### Task 4 test support: real minimal harness available before Task 6

Move `listing`, `idx`, `build_pack` from Task 6's code block into `tests/support_workflows.py` now, alongside this harness. Task 6 extends its scenario matrix; Task 4 is independently executable.

```python
from network_guard import install
install()
import contextlib, io, json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from support import fixture_settings
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.reader import capture_quarter,read_quarter
from sec_edgar_ingest.workflows.results import read_workflow_result

class WorkflowHarness:
    def __init__(self,root):
        self.root,self.serial=Path(root),0
        self.settings=fixture_settings(backfill={'start_quarter':'2026Q3','end_quarter':'open'},
            etl={'parser_version':'fixture-index-parser-v1'},
            fixture={'allow_clock_override':True,'allow_deadline_override':False})
        self.config=self.root/'config.json'
        self.config.write_bytes(canonical_json(self.settings.to_mapping()))
        self.opened=open_stores(self.settings,base_path=self.root)
        self.store,self.objects,self.leases=self.opened
        self.pack=None
        self.calls=[]
        self.public_cli=False

    def close(self):
        for resource in reversed(self.opened):
            if hasattr(resource,'close'):
                resource.close()

    def prepare(self,scenario):
        listings={}
        for family in ('full-index','daily-index'):
            root=BASE+family+'/'
            listings[root+'index.json']=[('2026','dir')]
            listings[root+'2026/index.json']=[('QTR3','dir'),('QTR4','dir')]
            for q in (3,4):
                listings[root+f'2026/QTR{q}/index.json']=[]
        first=('123456','Example','10-K','2026-09-30','edgar/data/123456/0000123456-26-000001.txt')
        second=('123456','Example','10-Q','2026-10-01','edgar/data/123456/0000123456-26-000002.txt')
        bodies={}
        if scenario in ('bounded-backfill','handoff-and-overlap','nonempty-unchanged-listings',
                        'legacy-seed','failed-directory-and-valid-source'):
            for q,rows in ((3,(first,)),(4,(first,second))):
                url=BASE+f'full-index/2026/QTR{q}/'
                listings[url+'index.json']=[('master.zip','file')]
                bodies[url+'master.zip']=idx(rows,'quarterly')
            url=BASE+'daily-index/2026/QTR4/'
            listings[url+'index.json']=[('master.20261001.idx','file')]
            daily=(second[0],second[1],second[2],'20261001',second[4])
            third=('123456','Example','8-K','20261001','edgar/data/123456/0000123456-26-000003.txt')
            bodies[url+'master.20261001.idx']=idx((daily,third),'daily')
        packroot=self.root/('pack-'+str(self.serial))
        self.pack=build_pack(packroot,listings,bodies)
        if scenario=='failed-directory-and-valid-source':
            value=json.loads(self.pack.read_text())
            url=BASE+'daily-index/2026/QTR3/index.json'
            value['responses'][url][0]['status']=404
            self.pack.write_bytes(canonical_json(value))
        if scenario not in ('bounded-backfill','handoff-and-overlap','nonempty-unchanged-listings',
                            'legacy-seed','failed-directory-and-valid-source','empty-valid-listings'):
            raise ValueError('scenario requires explicit fixture extension: '+scenario)

    def invoke(self,command,run_id,attempt_id='a1',today='2026-10-07',extra=()):
        deadline=(datetime.now(timezone.utc)+timedelta(seconds=1800)).isoformat()
        argv=[command,'--config',str(self.config),'--run-id',run_id,'--execution-id','manual',
            '--attempt-id',attempt_id,'--deadline',deadline,'--state-dir',str(self.root),
            '--today',today,*extra]
        if command in ('backfill','daily','discover','collect'):
            argv+=['--fixture-pack',str(self.pack)]
        output,errors=io.StringIO(),io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            if command in ('backfill','daily') and not self.public_cli:
                from sec_edgar_ingest.workflows.runner import run_workflow
                from sec_edgar_ingest.workflows.results import freeze_workflow,write_workflow_result
                from sec_edgar_ingest.workflows.steps import StepRunner
                from sec_edgar_ingest.models import RunContext
                from sec_edgar_ingest.config import pin_context
                from sec_edgar_ingest.download import FixturePack
                from sec_edgar_ingest.results import exit_code
                now=datetime.now(timezone.utc)
                context=RunContext(run_id,'manual',command,attempt_id,self.settings.worker.image_digest,
                    self.settings.etl.parser_version,self.settings.etl.schema_version,
                    self.settings.config_sha256,now,datetime.fromisoformat(deadline),
                    'daily' if command=='daily' else 'backfill')
                context,end=pin_context(self.settings,context,__import__('datetime').date.fromisoformat(today))
                intent={'command':command,'config_sha256':self.settings.config_sha256,
                    'effective_config':self.settings.to_mapping(),'pinned_end_quarter':end,
                    'today':today,'fixture_sha256':FixturePack.load(self.pack).manifest_sha256}
                context=freeze_workflow(context,intent,self.store,self.objects)
                steps=StepRunner(context,self.settings,self.pack,self.root,self.objects)
                result=run_workflow(context,self.settings,intent,steps,self.store,self.objects)
                ref=write_workflow_result(result,self.store,self.objects)
                code=exit_code(result.outcome)
                print(canonical_json({'outcome':result.outcome,'result_ref':ref}).decode())
            else:
                code=main(argv)
        message=json.loads(output.getvalue())
        self.calls.append({'argv':argv,'exit':code,'stdout':message,'stderr':errors.getvalue()})
        return code,message

    def run(self,command,scenario):
        self.serial+=1
        self.prepare(scenario)
        code,message=self.invoke(command,command+'-'+str(self.serial))
        result=read_workflow_result(message['result_ref'],self.objects)
        if code!=__import__('sec_edgar_ingest.results',fromlist=['exit_code']).exit_code(result.outcome):
            raise AssertionError('stdout/exit/report mismatch')
        return result

    def seed_legacy(self,downloaded,published):
        self.serial+=1
        self.prepare('legacy-seed')
        code,discovered=self.invoke('discover','legacy',extra=('--mode','daily','--discovery-id','legacy-daily'))
        if code!=0:
            raise AssertionError(discovered)
        if downloaded:
            code,collected=self.invoke('collect','legacy',extra=('--workset',discovered['source_workset_ref']))
            if code!=0:
                raise AssertionError(collected)
            if published:
                code,parsed=self.invoke('transform','legacy',extra=('--workset',collected['snapshot_workset_ref']))
                if code!=0:
                    raise AssertionError(parsed)
                code,published=self.invoke('publish','legacy',extra=('--workset',parsed['transformed_workset_ref']))
                if code!=0:
                    raise AssertionError(published)
        self.legacy_requests=self.transport_requests_for_legacy_body()

    def transport_requests_for_legacy_body(self):
        url=BASE+'daily-index/2026/QTR4/master.20261001.idx'
        return len(tuple(self.store.scan('TransportAttempt',{'url':url})))

    def capture_rows(self,quarter):
        capture=capture_quarter(quarter,self.objects,EtlState(self.store))
        if capture is None:
            raise AssertionError('quarter not published: '+quarter)
        return [row.to_mapping() for row in read_quarter(capture,self.objects)]
```

Task 4 tests `setUp` creates a TemporaryDirectory/WorkflowHarness and adds both cleanup callbacks. The legacy-body-request assertion compares request count **after recovery** with `self.harness.legacy_requests`, rather than asserting total history is zero. Deadline replay tests reuse the exact retained argv from `calls` so they do not accidentally generate a new deadline; `invoke` exposes `argv` for that purpose. Synthetic duplicate/gate/CAS/outage variants in Task 6 extend `prepare` with the exact matrix inputs and process observers; unsupported scenario names fail loudly as shown.

### Task 4 implementation detail: exact reuse and final selection

Implement these helpers in `workflows/members.py`; `WorkflowMembers.pending` uses `current_complete` in addition to validated successful receipt evidence. This replaces the proposed separate `WorkflowLegacyComplete` kind: no extra completion authority is needed.

```python
from ..models import Binding
from ..state import AcquisitionState
from ..etl.contracts import ObservationRef, processing_key
from ..etl.state import EtlState
from ..etl.reader import capture_quarter, validated_manifest
from ..etl.transform import read_observations


def current_complete(value, parser_version, schema_version, store, objects):
    acquisition = AcquisitionState(store)
    identity = value['source']['source_id']
    binding = acquisition.binding(value['member_id'], identity)
    if binding is None:
        return False
    snapshot = acquisition.snapshot(identity, binding.snapshot_sha256)
    objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
    key = processing_key(identity,snapshot.sha256,parser_version,schema_version)
    row = store.get('Processing',key)
    if row is None:
        return False
    ref = ObservationRef.from_mapping(row.to_mapping()['value']['observation'])
    if ref.snapshot != snapshot or ref.source.to_mapping() != value['source']:
        raise Conflict('accepted Processing differs from exact projected binding')
    # Iterator exhausts validated observation file; never trust published flags alone.
    for _ in read_observations(ref,objects):
        pass
    for quarter in ref.quarter_counts:
        capture = capture_quarter(quarter,objects,EtlState(store))
        if capture is None:
            return False
        manifest = validated_manifest(capture,objects)
        if not any(candidate.to_mapping()==ref.to_mapping() for candidate in manifest.sources):
            return False
    return True


def reuse_exact_binding(value, store, objects):
    acquisition = AcquisitionState(store)
    member = read_source(value['member_ref'],objects)
    identity = value['source']['source_id']
    if acquisition.binding(member.workset_id,identity) is not None:
        return
    source_row = acquisition.get_source(identity)
    if (member.acquisition_mode!='reuse_accepted' or source_row is None
            or source_row.value['needs_acquisition']):
        return
    candidates = {}
    for row in store.scan('WorkflowMember', {}):
        other = row.to_mapping()['value']
        if other['source'] != value['source']:
            continue
        binding = acquisition.binding(other['member_id'],identity)
        if binding is not None:
            snapshot=acquisition.snapshot(identity,binding.snapshot_sha256)
            objects.verify(snapshot.raw_path,snapshot.sha256,snapshot.byte_count)
            candidates[(snapshot.received_at,snapshot.sha256)] = snapshot
    if not candidates:
        return
    latest_time = max(at for at,sha in candidates)
    selected=[snapshot for (at,sha),snapshot in candidates.items() if at==latest_time]
    if len(selected)!=1:
        raise Conflict('retained exact bindings have ambiguous equal-time hashes')
    snapshot=selected[0]
    acquisition.bind_once(Binding(member.workset_id,identity,snapshot.sha256))


def selection_jobs(values, parser_version, schema_version, store, objects):
    grouped = {}
    acquisition=AcquisitionState(store)
    for value in values:
        reuse_exact_binding(value,store,objects)
        member=read_source(value['member_ref'],objects)
        binding=acquisition.binding(member.workset_id,value['source']['source_id'])
        snapshot = binding.snapshot_sha256 if binding is not None else None
        # Unbound reuse units with the same exact config can share acquisition.
        token = ('bound',snapshot) if snapshot else ('unbound',member.context.config_sha256,
                  member.acquisition_mode,member.workset_id if member.acquisition_mode=='refresh' else '')
        key=(value['source']['source_id'],token,parser_version,schema_version)
        grouped.setdefault(key,[]).append(value)
    jobs=[]
    for aliases in grouped.values():
        aliases=sorted(aliases,key=lambda v:v['member_id'])
        jobs.append({'member':aliases[0],'aliases':aliases})
    return sorted(jobs,key=lambda job:(job['member']['source']['period'],
                         job['member']['source']['source_id'],job['member']['member_id']))
```

`pending()` returns only members that are neither verified current-complete nor validated complete receipts under current versions. A current pointer that advances away from an observation makes `current_complete` false; a previously hash-bound completed WorkflowMemberResult remains an auditable completed invocation, but cannot bypass new refresh/current-version selection. Missing referenced files produce a state gap/refusal, never true completion.

Use this final orchestration sequence in `runner.py` in place of the earlier selection core. It defines selection before dispatch and consumes concrete helpers, retaining exact alias parents without duplicate source operations:

```python
import hashlib
from datetime import datetime,timezone
from ..config import pin_context
from ..discovery import quarter_span
from ..state import AcquisitionState
from ..models import Source,Error,canonical_json
from ..storage.contracts import observe
from ..etl.state import EtlState
from ..etl.reader import capture_quarter
from .contracts import WorkflowResult,MemberResult,summarize,FATAL,workflow_path
from .members import WorkflowMembers,project_member,read_source,current_complete,reuse_exact_binding,selection_jobs
from .legacy import bootstrap_legacy
from ..models import parse_json, Binding
from ..collection import HALTING_OUTCOMES
from .steps import StepFailure
from ..worksets import decode_snapshot_workset


def run_workflow(context, settings, intent, steps, store, objects, observer=None):
    acquisition=AcquisitionState(store)
    registry=WorkflowMembers(store,objects)
    selection_ref=workflow_path(context).replace('result.json','selection.json')
    try:
        body=objects.read(selection_ref)
        selection=parse_json(body)
        if canonical_json(selection)!=body or selection['context']!=context.to_mapping():
            raise ValueError('changed workflow selection')
    except FileNotFoundError:
        before=acquisition.daily_boundary()
        legacy_gaps=bootstrap_legacy(store,objects,registry,(context.parser_version,context.schema_version))
        known={row.value['source']['source_id'] for row in store.scan('WorkflowMember',{})}
        pending_before=registry.pending(context.parser_version,context.schema_version)
        mode='daily' if context.command=='daily' else 'quarterly'
        discovered=None
        parent=None
        gaps=list(legacy_gaps)
        halted=False
        try:
            discovered=steps.execute('discover','discover',settings,
                ['--mode',mode,'--discovery-id',context.run_id+'-'+mode])
            if discovered.source_workset_ref is not None:
                parent=read_source(discovered.source_workset_ref,objects)
            for gap in discovered.gaps:
                mapped=HALTING_OUTCOMES.get(gap.code,gap.code)
                gaps.append(Error(mapped,gap.message,gap.retryable,gap.source_id,
                                  {**gap.to_mapping()['details'],'original_code':gap.code}))
                halted=halted or mapped in FATAL
            halted=halted or discovered.outcome in FATAL
        except StepFailure as error:
            # Resumable post-CAS child errors must be propagated, never finalized.
            if error.details.get('resumable'):
                raise
            gaps.append(Error(error.outcome,str(error),False,None,error.details))
            halted=True
        current=[]
        new_ids={source.source_id for source in parent.members if source.source_id not in known} if parent else set()
        for source in parent.members if parent else ():
            ref=project_member(discovered.source_workset_ref,source.source_id,objects)
            value=registry.register(discovered.source_workset_ref,ref)
            reuse_exact_binding(value,store,objects)
            current.append(value)
        end=parent.pinned_end_quarter if parent else pin_context(settings,context,context.pinned_on)[1]
        requested=() if mode=='daily' else quarter_span(settings.backfill.start_quarter,end)
        for quarter in requested:
            if parent is None or not any(s.kind=='quarterly' and s.period==quarter for s in parent.members):
                gaps.append(Error('baseline_source_missing','requested quarter has no validated source',
                                  True,None,{'quarter':quarter}))
        all_members={v['member_id']:v for v in (*pending_before,*current)}
        unresolved=[value for value in all_members.values() if not current_complete(value,
                    context.parser_version,context.schema_version,store,objects)]
        session=acquisition.discovery_session(context.run_id+'-'+mode)
        required_units=[] if session is None else session.to_mapping()['value']['frozen']['units']
        selection={'context':context.to_mapping(),'parent_ref':discovered.source_workset_ref if discovered else None,
            'directories':[d.to_mapping() for d in parent.directories] if parent else [],
            'required_units':required_units,'halted':halted,
            'requested_quarters':list(requested),'gaps':[g.to_mapping() for g in gaps],
            'boundary_before':before.isoformat() if before else None,
            'discovered_sources':len(new_ids),
            'unresolved_before':len({v['source']['source_id'] for v in pending_before}),
            'jobs':selection_jobs(unresolved,context.parser_version,context.schema_version,store,objects),
            'already_complete':[v for v in current if v not in unresolved]}
        objects.put_once(selection_ref,canonical_json(selection))
        observe(observer,'workflow.after_selection')
    if selection['parent_ref'] is not None:
        read_source(selection['parent_ref'],objects)
    results=[]
    halted=selection['halted']
    for job in selection['jobs']:
        value=job['member']
        for alias in job['aliases']:
            registry.register(alias['parent_ref'],alias['member_ref'])
        if halted or datetime.now(timezone.utc)>=context.deadline:
            result=MemberResult(value['member_id'],Source.from_mapping(value['source']),value['parent_ref'],
                None,None,(),'pending',False,False,False,(),
                (Error('workflow_deferred','halt/deadline left source pending',True,value['source']['source_id'],{}),),
                context.parser_version,context.schema_version)
        else:
            result=steps.member(value)
            halted=result.outcome in FATAL
            if result.snapshot_ref is not None:
                snapshots=decode_snapshot_workset(objects.read(result.snapshot_ref))
                snapshot=snapshots.snapshots[0]
                if len(snapshots.snapshots)!=1 or snapshot.source_id!=value['source']['source_id']:
                    raise ValueError('completed collection changed singleton source membership')
                for alias in job['aliases']:
                    acquisition.bind_once(Binding(alias['member_id'],snapshot.source_id,snapshot.sha256))
        registry.record(result,context)
        observe(observer,'workflow.after_member_receipt')
        results.append(result)
    gaps=list(Error.from_mapping(g) for g in selection['gaps'])
    for quarter in selection['requested_quarters']:
        if capture_quarter(quarter,objects,EtlState(store)) is None:
            gaps.append(Error('baseline_publication_missing','requested baseline quarter has no readable generation',
                              True,None,{'quarter':quarter}))
    gaps=tuple(gaps)
    outcome,counts=summarize(tuple(results),gaps,selection['discovered_sources'],
                            selection['unresolved_before'],context.command)
    # Known completed input sources need no child execution. Account them explicitly.
    complete_ids={v['source']['source_id'] for v in selection['already_complete']}
    counted={result.source.source_id for result in results}
    counts['complete_sources']+=len(complete_ids-counted)
    after=acquisition.daily_boundary()
    report_intent={'invocation':intent,'discovered_sources':selection['discovered_sources'],
        'unresolved_before':selection['unresolved_before'],'selection_ref':selection_ref,
        'required_units':selection['required_units'],
        'already_complete_sources':sorted(complete_ids-counted)}
    return WorkflowResult('sec-workflow-result-v1',context,report_intent,selection['parent_ref'],
        tuple(selection['requested_quarters']),tuple(selection['directories']),tuple(results),gaps,
        selection['boundary_before'],after.isoformat() if after else None,outcome,counts,
        max(context.started_at,datetime.now(timezone.utc)).isoformat())
```

Update `WorkflowResult.__post_init__` to include `intent['already_complete_sources']` after the reducer exactly as the runner does, and reject overlap with selected-result source IDs or duplicate complete IDs. Validate this set against selection.json and current-complete captures on report read, with immutable before-dispatch captures retained in selection. Count already complete downloaded/transformed source status separately if reported; do not infer fresh body fetch. A baseline no-op remains unchanged; no-new applies only to daily. For a daily fresh projection whose exact completed input is rebound, no unresolved-before/new IDs/advanced quarters means no_new_sources even with nonempty listing.

The final runner retains discovery/StepFailure fatal/pending gaps before selection: preserve DiscoverySession required units and older registry queue when no durable source ref exists; `parent_ref=None` permits no current projection and every older unit is pending if halted. `PublicationRepairPending` bypasses report finalization and propagates the existing structured resumable error; it cannot be swallowed as member success. Test both paths with actual exited processes. This is the exception boundary described in Task 3, not a second publication implementation.

## Task 5: Manual commands, validation, logs and runbook

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/cli.py`, `packages/sec-edgar-ingest/tests/test_workflow_cli.py`, `docs/runbooks/sec-edgar-workflows.md`; modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py:62` and `:283` (parser/main), root and package READMEs; add `WorkflowAttempt` routing/content descriptor assertions to `packages/sec-edgar-ingest/tests/test_azure_contracts.py` and `test_azure_state_payloads.py`.

**Interfaces:** `workflows.cli.main(argv: Sequence[str]) -> int`; existing main dispatches only `backfill|daily`. Existing four command semantics remain unchanged. Workflow stdout is `{outcome,result_ref,counts,source_workset_ref}`; durable result/intent/member refs provide full report. Logs carry workflow context and child result/source/generation IDs.

- [ ] **Step 1: Write failing CLI cases.** Complete starter test:

```python
from network_guard import install
install()
import contextlib, io, unittest
from unittest.mock import patch
from sec_edgar_ingest.cli import main

class WorkflowCliTests(unittest.TestCase):
    def test_help_names_manual_workflows(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main([]), 0)
        for command in ('backfill', 'daily'):
            self.assertIn(command, stdout.getvalue())

    def test_missing_intent_refuses_before_adapters(self):
        with patch('sec_edgar_ingest.workflows.cli.open_stores',
                   side_effect=AssertionError('adapter opened')):
            with self.assertRaises(SystemExit) as raised:
                main(['backfill'])
        self.assertEqual(raised.exception.code, 2)
```

Add reversed/future endpoints, missing handoff/config/IDs/deadline, unknown parser/schema, malformed/future fixture date, changed frozen fixture hash, unknown flags, Azure fixture override refusal and exact replay before sender construction. Real repeat nonempty daily listings must return no_new_sources after successful coverage; body failures cannot. Keep existing commands' zero/nonzero contracts.

- [ ] **Step 2: Run red.** Guarded pattern `test_workflow_cli.py`; expected help/unknown command/API failure.
- [ ] **Step 3: Add route and workflow lifecycle.** In `cli.main`, resolve `raw = list(sys.argv[1:] if argv is None else argv)` and insert before existing parser dispatch:

```python
if raw and raw[0] in ('backfill', 'daily'):
    from .workflows.cli import main as workflow_main
    return workflow_main(raw)
```

Add workflow help parsers after the existing command loop:

```python
for command in ('backfill', 'daily'):
    commands.add_parser(command, help='run the manual '+command+' workflow')
```

Workflow CLI uses this lifecycle:

```python
import argparse, sys
from pathlib import Path
from datetime import date, datetime, timezone
from ..config import load_config, pin_context
from ..coordination import Clock
from ..download import FixturePack
from ..etl.parser import supported_parser, SCHEMA_VERSION
from ..models import RunContext, canonical_json, quarter_for, safe_relative_path
from ..results import exit_code, log_event
from ..storage import open_stores
from ..storage.contracts import Conflict
from .contracts import workflow_path
from .results import freeze_workflow, read_workflow_result, write_workflow_result
from .runner import run_workflow
from .steps import StepRunner

def parser():
    p = argparse.ArgumentParser(prog='sec-edgar-ingest')
    p.add_argument('command', choices=('backfill', 'daily'))
    for name in ('config','run-id','execution-id','attempt-id','deadline'):
        p.add_argument('--'+name, required=True)
    for name in ('state-dir','fixture-pack','today'):
        p.add_argument('--'+name)
    return p

def main(argv):
    args = parser().parse_args(argv)
    opened = ()
    context = None
    try:
        settings = load_config(Path(args.config))
        supported_parser(settings.etl.parser_version, fixture=settings.storage.backend == 'local-fixture')
        deadline = datetime.fromisoformat(args.deadline.replace('Z','+00:00'))
        now = Clock().now()
        today = date.fromisoformat(args.today) if args.today else now.date()
        if args.today and today.isoformat() != args.today:
            raise ValueError('today requires canonical ISO date')
        if settings.storage.backend == 'azure':
            if args.state_dir or args.fixture_pack or args.today:
                raise ValueError('local fixture overrides forbidden for Azure')
            pack_hash = None
        else:
            if not args.fixture_pack:
                raise ValueError('local workflow requires explicit fixture pack')
            pack_hash = FixturePack.load(Path(args.fixture_pack)).manifest_sha256
        for name in ('run_id','execution_id','attempt_id'):
            if '/' in safe_relative_path(getattr(args,name),name):
                raise ValueError('workflow IDs require one segment')
        if args.command == 'daily' and settings.daily.start_date > today:
            raise ValueError('daily handoff is in the future')
        # pin_context validates required inclusive endpoints and accepted allowance.
        # Load exact saved context before calling it for expired completed replay.
        active = deadline > now
        if active:
            context = RunContext(args.run_id, args.execution_id, args.command, args.attempt_id,
                settings.worker.image_digest, settings.etl.parser_version, settings.etl.schema_version,
                settings.config_sha256, now, deadline, 'daily' if args.command == 'daily' else 'backfill')
            context, endpoint = pin_context(settings, context, today)
        else:
            context = None
            endpoint = None
        if active and args.command == 'daily' and endpoint != quarter_for(today):
            raise ValueError('daily endpoint must include current quarter')
        opened = open_stores(settings, base_path=Path(args.state_dir) if args.state_dir else None)
        store, objects, leases = opened
        if not active:
            path = f'runs/sec/{args.run_id}/{args.command}/{args.attempt_id}/result.json'
            prior = read_workflow_result(path, objects)
            saved = prior.context
            if (saved.run_id, saved.execution_id, saved.attempt_id, saved.command, saved.deadline) != (args.run_id, args.execution_id, args.attempt_id, args.command, deadline):
                raise Conflict('expired replay changed correlation or deadline')
            if args.today and saved.pinned_on != today:
                raise Conflict('expired replay changed pin date')
            context, endpoint = pin_context(settings, saved, saved.pinned_on)
            today = saved.pinned_on
        intent = {'command':args.command, 'config_sha256':settings.config_sha256,
                  'effective_config':settings.to_mapping(), 'pinned_end_quarter':endpoint,
                  'today':today.isoformat(), 'fixture_sha256':pack_hash}
        context = freeze_workflow(context, intent, store, objects)
        try:
            result = read_workflow_result(workflow_path(context), objects)
        except FileNotFoundError:
            if Clock().now() >= context.deadline:
                raise ValueError('expired unfinished workflow requires new valid attempt')
            steps = StepRunner(context, settings, args.fixture_pack, args.state_dir, objects)
            result = run_workflow(context, settings, intent, steps, store, objects)
        ref = write_workflow_result(result, store, objects)
        log_event(context, 'workflow_finished', {'outcome':result.outcome,'result_ref':ref,'counts':result.counts})
        sys.stdout.write(canonical_json({'outcome':result.outcome,'result_ref':ref,
            'counts':result.counts,'source_workset_ref':result.source_workset_ref}).decode()+'\n')
        return exit_code(result.outcome)
    except (ValueError, OSError, Conflict) as error:
        outcome = 'state_conflict' if isinstance(error, Conflict) else 'configuration'
        sys.stderr.write(canonical_json({'outcome':outcome,'error':str(error)}).decode()+'\n')
        sys.stdout.write(canonical_json({'outcome':outcome,'result_ref':None}).decode()+'\n')
        return exit_code(outcome)
    finally:
        for resource in reversed(opened):
            if hasattr(resource,'close'):
                resource.close()
```

The saved-context branch above executes before any expired `RunContext` construction: validate raw deadline/IDs/settings first, open only the selected backend, locate exact retained WorkflowAttempt/intent and report, construct replay context using its original start/pin date, compare every frozen field, and replay/repair completed results without StepRunner. An expired deadline with no exact completed result refuses. This matches shipped child CLI behavior rather than inventing a deadline. Validate daily endpoint/backfill dates before any new adapters for active attempts. Exception mapping must distinguish configuration (pre-dispatch), storage/state conflicts (9), access/halt/ownership codes, expired pending work and interrupted child repair (retryable, no final result), never label a runtime corrupt manifest a configuration success. Unexpected exceptions retain structured WorkflowAttempt error with partial selection/child refs and return 9 without synthesizing coverage.

Runbook text includes executable **fixture-only** examples:

```bash
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest backfill --config /absolute/path/fixture-config.json --run-id baseline-fixture --execution-id manual --attempt-id a1 --deadline 2026-10-07T23:59:00Z --state-dir /private/tmp/sec-workflows-demo --fixture-pack packages/sec-edgar-ingest/tests/fixtures/workflows/manifest.json --today 2026-10-07
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest daily --config /absolute/path/fixture-config.json --run-id daily-fixture --execution-id manual --attempt-id a1 --deadline 2026-10-07T23:59:00Z --state-dir /private/tmp/sec-workflows-demo --fixture-pack packages/sec-edgar-ingest/tests/fixtures/workflows/manifest.json --today 2026-10-07
```

Replace static deadline in copied examples with a freshly generated UTC deadline within 3,600 seconds; show the exact stdlib command `python -c 'from datetime import datetime,timedelta,timezone; print((datetime.now(timezone.utc)+timedelta(seconds=1800)).isoformat())'`. Explain inclusive configured ranges, accepted handoff, body/ETL/quarter counters, no-new vs failure, closed-quarter gate, partial advances, legacy provenance gaps, and exact interrupted replay vs new failed-attempt retry. Link pointer-reader instructions; no trigger/approval command or live Azure example that implies authorization. Document all22 Stage7 reservations.

- [ ] **Step 4: Run green and mocked adapter compatibility.** Guarded `test_workflow_cli.py`, `test_cli.py`, `test_etl_cli.py`, `test_azure_contracts.py`, `test_azure_state_payloads.py` PASS. Assert new WorkflowAttempt/member kinds route to existing SourceState; large state is immutable object descriptor before CAS, real mocked opaque ETags preserved.
- [ ] **Step 5: Commit explicit files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/cli.py packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_workflow_cli.py packages/sec-edgar-ingest/tests/test_azure_contracts.py packages/sec-edgar-ingest/tests/test_azure_state_payloads.py docs/runbooks/sec-edgar-workflows.md README.md packages/sec-edgar-ingest/README.md
git commit -m "feat: expose manual backfill and daily workflow commands"
```

## Task 6: Compact fixture backfill and outage/overlap acceptance

**Files:** Extend `packages/sec-edgar-ingest/tests/support_workflows.py`; create `packages/sec-edgar-ingest/tests/test_workflow_offline.py`, `packages/sec-edgar-ingest/tests/fixtures/workflows/manifest.json`, `.../bodies/*`, `.../expected.json`. Add real process termination/replay cases to `test_workflow_results.py`.

**Interfaces:** `WorkflowHarness(root: Path)` owns real local stores, source fixtures/config and `invoke(command, run_id, attempt_id='a1', today='2026-10-07') -> tuple[int, WorkflowResult]`; `build_pack(root, listings: Mapping[str,list], bodies: Mapping[str,bytes], overrides: Mapping[str,list] | None = None) -> Path`. `seed_legacy(downloaded, published)` uses existing acquisition/discovery/collection commands (and ETL only when published=True), not direct fabrication of WorkflowMember. `run(command, scenario)` selects the explicit matrix below and invokes real CLI. Task 4 can inject only the child command runner to isolate report/crash behavior; Task 6's acceptance cases use actual CLI, coordinator, transport fixture pack, stores, parser, publisher and pointer reader.

- [ ] **Step 1: Write acceptance tests and exact expected scenarios.** Required scenario matrix:

| Scenario | Synthetic inputs | Observable assertions |
|---|---|---|
| `bounded-backfill` | 2026Q3 ZIP with one Sep30 key; 2026Q4 ZIP with same Sep30 key plus Oct01 second key | requested=(Q3,Q4), two complete sources, two readable quarter captures, 2 unique logical keys, cross-quarter quarter membership correct |
| `invalid-and-valid-quarter` | Q3 has conflicting duplicate; Q4 valid | exit3/incomplete, Q3 failed/quarantined/no observations or pointer from that source; valid Q4 progress retained; requested Q3 accounted for |
| `empty-baseline-quarter` | valid Q3 leaf empty; Q4 valid | `baseline_source_missing` Q3 gap, incomplete coverage |
| `handoff-and-overlap` | baseline open Q4; listed daily Oct01 overlaps baseline key plus new key | no duplicate key, quarterly precedence, handoff Oct01 retained |
| `failed-directory-and-valid-source` | valid roots/years; Q3 directory HTTP404; Q4 body valid | discovery boundary unchanged, Q4 publishes, Q3 error retained, incomplete |
| `empty-valid-listings` | roots/year/required quarter leaves valid with zero bodies | daily no_new only with no old unresolved queue; otherwise retry/report backlog |
| `nonempty-unchanged-listings` | identical successful daily sources listed on new discovery run | no body re-fetch, no new pointer/events, no_new_sources with zero unresolved-before |
| `outage-across-quarters` | prior boundary 2025-06-30, pin2026-01-02; roots include 2025Q2–Q4/2026Q1; daily data and pending2024Q1 | every outage quarter plus old pending inspected; source dates partition correctly; no yesterday-only URL |
| `year-rollover` | prior2025Q4 and open2026Q1 daily sources, handoff configured2025-12-31 | both quarters covered; cross-year pending survives; first boundary from handoff |
| `legacy-body-pending` | legacy Source registered by discovery; body unbound; latest listing omits it | original listing/source authority recovered; fresh collection retry, unresolved identity retained if body404 |
| `legacy-etl-pending` | old exact Binding/SnapshotWorkset downloaded; new listing empty; no WorkflowMember | no body fetch; current ETL completes old source; corrupt provenance produces explicit gap |
| `partial-output` | one daily file with dates in2025Q3 and2026Q4; injected second quarter CAS conflict | first capture remains readable, second conflict retained, source unresolved; retry repairs without duplicate filing |
| `approval-pending` | seeded closed quarter + validated quarterly replacement removing one key | awaiting_approval candidate inactive, old pointer unchanged, source pending, no approval bypass |
| `halt-and-deadline` | first member403 or clock deadline before second dispatch | shared halt/nonzero; remaining units pending, no extra request reservation |
| `parser-replay` | successful retained source under fixture parserv1 then currentv2 | original raw/binding/config byte identity; new Processing identities; unchanged logical row set; no body request |
| `crash-four-boundaries` | force process exit after child/report/member/attempt commit boundaries | exact retry readback/repair, one pointer advance, immutable report bytes and captures |

Write this real end-to-end starter test:

```python
from network_guard import install
install()
import tempfile, unittest
from pathlib import Path
from support_workflows import WorkflowHarness
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter

class OfflineWorkflowTests(unittest.TestCase):
    def test_bounded_fixture_backfill_and_daily_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = WorkflowHarness(Path(tmp))
            h.public_cli = True
            self.addCleanup(h.close)
            baseline = h.run('backfill', 'bounded-backfill')
            self.assertEqual(baseline.requested_quarters, ('2026Q3','2026Q4'))
            self.assertEqual(baseline.counts['complete_sources'], 2)
            before = h.capture_rows('2026Q4')
            daily = h.run('daily', 'handoff-and-overlap')
            after = h.capture_rows('2026Q4')
            self.assertGreaterEqual(len(after), len(before))
            self.assertEqual(len({(r['cik'],r['archive_path']) for r in after}), len(after))
            repeated = h.run('daily', 'nonempty-unchanged-listings')
            self.assertEqual(repeated.outcome, 'no_new_sources')
            self.assertEqual(h.capture_rows('2026Q4'), after)
```

Use the verified reader signatures `capture_quarter(quarter, objects, EtlState(store)) -> GenerationCapture | None` and `read_quarter(capture, objects) -> Iterator[IndexRow>`; harness captures generation plus validated file rows, not raw directory globs. Record each scenario's CLI exit/stdout/stderr/durable report, request history, state snapshots, before/after pointer captures and raw/manifest hashes. No fixture counts stand in for retained SEC specimens.

Add this bounded-history/no-projection-recursion test to `OfflineWorkflowTests`:

```python
    def test_three_new_discoveries_do_not_project_old_singletons_again(self):
        from sec_edgar_ingest.workflows.members import WorkflowMembers
        with tempfile.TemporaryDirectory() as tmp:
            h=WorkflowHarness(Path(tmp))
            h.public_cli=True
            self.addCleanup(h.close)
            h.run('backfill','bounded-backfill')
            h.run('daily','handoff-and-overlap')
            before=len(tuple(h.store.scan('WorkflowMember',{})))
            for offset in range(1,4):
                result=h.run('daily','nonempty-unchanged-listings')
                self.assertEqual(result.outcome,'no_new_sources')
                rows=tuple(h.store.scan('WorkflowMember',{}))
                # One genuinely new parent discovery yields one new source alias.
                self.assertEqual(len(rows),before+offset)
                singleton_refs={row.value['member_ref'] for row in rows}
                self.assertFalse(any(row.value['parent_ref'] in singleton_refs for row in rows))
                pending=WorkflowMembers(h.store,h.objects).pending('fixture-index-parser-v1','sec-index-v1')
                self.assertEqual(pending,())
```

- [ ] **Step 2: Run red.** Guarded `test_workflow_offline.py`; expected unsupported workflow or violated assertion. Earlier task isolated tests already pass; this is a composition gate.
- [ ] **Step 3: Generate compact fixtures and complete the harness.** The fixture pack builder is:

```python
import hashlib, io, json, zipfile
from pathlib import Path
from sec_edgar_ingest.models import canonical_json

BASE = 'https://www.sec.gov/Archives/edgar/'

def listing(url, children):
    name = url[len(BASE):-len('index.json')]
    return canonical_json({'directory':{'name':name,'parent-dir':'../',
        'item':[{'name':child, 'href':child+('/' if kind=='dir' else ''),
                 'type':kind, 'size':'1', 'last-modified':'2026-10-01 00:00:00'}
                for child,kind in children]}})

def idx(rows, kind):
    title = 'Filename' if kind=='quarterly' else 'File Name'
    newline = '\r\n' if kind=='quarterly' else '\n'
    body = (f'CIK|Company Name|Form Type|Date Filed|{title}'+newline+'-----'+newline+
            newline.join('|'.join(row) for row in rows)+newline).encode('ascii')
    if kind=='daily':
        return body
    output = io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        info = zipfile.ZipInfo('master.idx',(2026,1,1,0,0,0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info,body)
    return output.getvalue()

def build_pack(root, listings, bodies, overrides=None):
    root.mkdir(parents=True, exist_ok=True)
    responses = {}
    merged = {url:listing(url,children) for url,children in listings.items()}
    merged.update(bodies)
    for url,body in sorted(merged.items()):
        digest = hashlib.sha256(body).hexdigest()
        relative = 'bodies/'+digest+'.body'
        path = root/relative
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(body)
        responses[url] = [{'status':200,'headers':{'Content-Length':str(len(body)),
            'X-Fixture':'synthetic'}, 'body_path':relative,'body_sha256':digest}]
    responses.update(overrides or {})
    path = root/'manifest.json'
    path.write_bytes(canonical_json({'fixture_version':'sec-acquisition-fixture-v1',
                                    'provenance':'synthetic','responses':responses}))
    return path
```

Required root/year/leaf entries are actual immediate children. Generate both source families' roots (`full-index`, `daily-index`), relevant years and every required quarter; no request bypasses root-parent traversal. For failure overrides still write original error body bytes/hash in the same way. Drive sequential responses through actual fixture cursor state; retries remain accounted five-attempt budget, never reset it by selecting another pack invisibly. Freeze each changed pack only in a new workflow attempt/run.

Harness builds Settings from `support.fixture_settings` with `etl.parser_version='fixture-index-parser-v1'`, explicit fixture clock override marker, `backfill.start_quarter='2026Q3'`, `end_quarter='open'` and accepted daily start. Historical outage scenarios explicitly use a fixture-only earlier handoff and dates; label them as synthetic testing rather than changed deployed D14/F1 decisions. Deadline is real UTC now+1,800s; retain injected logical pin date. Write config canonical bytes to harness root; use local storage root `.fixture-state`. Call public CLI with fresh run IDs per discovery run, explicit fixture/state/date, capture JSON/stdout/stderr and `read_workflow_result`. Reopen via `open_stores` only for readback/captures, closing all handles. `seed_legacy` invokes original four commands with old parser/config and saves actual DiscoverySession/DirectoryProgress/Source/Binding; never creates WorkflowMember directly. `capture_rows` uses the actual installed reader and returns normalized dictionaries plus generation capture in retained proof. `transport_requests_for_legacy_body` scans exact TransportAttempt URL/source IDs, not a mock call count.

- [ ] **Step 4: Run green, including real spawned process crashes and independent store reopen.** Guarded `test_workflow_offline.py` plus `test_workflow_results.py` PASS. Record row/key/generation assertions for every scenario from the matrix; unknown provenance/invalid source must stay a nonzero gap.
- [ ] **Step 5: Commit explicit fixtures and tests.** Before adding bodies, inspect every candidate file's synthetic provenance and hash. Stage only enumerated fixture paths from the generated manifest (no broad index add).

```bash
git add packages/sec-edgar-ingest/tests/support_workflows.py packages/sec-edgar-ingest/tests/test_workflow_offline.py packages/sec-edgar-ingest/tests/test_workflow_results.py packages/sec-edgar-ingest/tests/fixtures/workflows/manifest.json packages/sec-edgar-ingest/tests/fixtures/workflows/expected.json
# Add each exact bodies/<sha>.body named by the reviewed manifest as a separate path argument.
git commit -m "test: prove bounded backfill and durable daily catch-up offline"
```

## Task 7: Fresh native/installed proof, reviews and completion checkpoint

**Files:** Create `scripts/prove-sec-edgar-workflows.py`; modify `scripts/check-sec-edgar-ingest.sh` command-help coverage; retain generated proofs only under `specs/evidence/sec-filing-index-ingestion/stage-4/verification/`; on accepted completion retire Stage 4 plan/spec only. No Stage 4 status tick before acceptance.

**Interfaces:** Proof script `--output ABS_PATH --installed` imports existing test guard before production code; drives the Task 6 harness against the installed distribution; reports runtime/interpreter/distribution version/source hashes/wheel SHA/fixture SHA/results; output inventory excludes itself to avoid self-dependent hashes. Controller verifies wheel-source hashes against reviewed implementation, not editable source imports.

- [ ] **Step 1: Write failing installed-proof assertions.** Before installation, isolated env must refuse importing absent `sec_edgar_ingest`; after installation require no editable path, `importlib.metadata.distribution('sec-edgar-ingest').version=='0.1.0'`, module file under the venv, no repository src path in `sys.path`, all six commands help present, baseline/daily/read sequence with expected fixture counts and zero live authorization. Copy test guard/harness into a separate temporary test-support directory; use installed package only. Acceptance fails if a workflow result/child capture is corrupt, discovery failure is no-new, legacy pending is omitted, or gated quarters are reported complete.

- [ ] **Step 2: Run red installed absence gate.**

```bash
uv venv --offline --python 3.14 /private/tmp/sec-edgar-stage4-installed-env
/private/tmp/sec-edgar-stage4-installed-env/bin/python -I -c 'import sec_edgar_ingest'
```

Expected import failure in the fresh env. Use a freshly generated unique temporary root if the path already exists; never reuse an unknown venv or remove retained evidence.

- [ ] **Step 3: Implement proof script and offline build checks.** Proof script sets test-support path only, imports/installs `network_guard`, then invokes actual package `main` through the fixture harness and verifies results using installed `workflows.results`/pointer reader. Use this complete installed proof body after the script's argument parsing. Arguments are `--output`, `--test-support`, `--reviewed-source`, `--wheel`, `--installed`; all filesystem arguments must be absolute. `--test-support` is the separately copied tests/support/fixtures directory, never a repository source path. Native full-scenario acceptance remains the guarded suite; the installed boundary proves baseline/daily/legacy/read composition independently.

```python
import argparse,hashlib,json,sys,tempfile
from pathlib import Path

p=argparse.ArgumentParser()
for name in ('output','test-support','reviewed-source','wheel'):
    p.add_argument('--'+name,required=True,type=Path)
p.add_argument('--installed',action='store_true',required=True)
args=p.parse_args()
if any(not getattr(args,name).is_absolute() for name in ('output','test_support','reviewed_source','wheel')):
    raise ValueError('proof requires absolute paths')
sys.path.insert(0,str(args.test_support))
from network_guard import install
install()
import importlib.metadata
import sec_edgar_ingest
from support_workflows import WorkflowHarness
from sec_edgar_ingest.models import canonical_json

module=Path(sec_edgar_ingest.__file__).resolve()
if not module.is_relative_to(Path(sys.prefix).resolve()):
    raise RuntimeError('installed proof imported checkout')
if importlib.metadata.distribution('sec-edgar-ingest').version!='0.1.0':
    raise RuntimeError('wrong installed distribution')
source_hashes={path.relative_to(module.parent).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
               for path in module.parent.rglob('*.py')}
reviewed_hashes={path.relative_to(args.reviewed_source).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in args.reviewed_source.rglob('*.py')}
if source_hashes!=reviewed_hashes:
    raise RuntimeError('installed source differs from reviewed implementation')
for distribution,version in (('requests','2.34.2'),('azure-identity','1.26.0'),
                             ('azure-storage-blob','12.31.0'),('azure-data-tables','12.7.0'),('pyarrow','25.0.1')):
    if importlib.metadata.version(distribution)!=version:
        raise RuntimeError('dependency pin mismatch: '+distribution)
args.output.mkdir(parents=True,exist_ok=False)
records=[]
for label in ('baseline-daily','legacy-downloaded'):
    root=args.output/label
    root.mkdir()
    h=WorkflowHarness(root)
    h.public_cli=True
    try:
        if label=='baseline-daily':
            baseline=h.run('backfill','bounded-backfill')
            assert baseline.requested_quarters==('2026Q3','2026Q4')
            assert baseline.counts['complete_sources']==2
            old=h.capture_rows('2026Q4')
            daily=h.run('daily','handoff-and-overlap')
            new=h.capture_rows('2026Q4')
            assert len(new)>len(old)
            assert len({(r['cik'],r['archive_path']) for r in new})==len(new)
            repeat=h.run('daily','nonempty-unchanged-listings')
            assert repeat.outcome=='no_new_sources'
            assert h.capture_rows('2026Q4')==new
            reports=[baseline,daily,repeat]
        else:
            h.seed_legacy(downloaded=True,published=False)
            assert not tuple(h.store.scan('WorkflowMember',{}))
            before=h.transport_requests_for_legacy_body()
            recovered=h.run('daily','empty-valid-listings')
            assert recovered.outcome!='no_new_sources'
            assert recovered.counts['complete_sources']==1
            assert h.transport_requests_for_legacy_body()==before
            reports=[recovered]
        (root/'calls.json').write_bytes(canonical_json(h.calls))
        (root/'reports.json').write_bytes(canonical_json([r.to_mapping() for r in reports]))
        records.append({'scenario':label,'outcomes':[r.outcome for r in reports]})
    finally:
        h.close()
report={'exit':0,'installed_module':str(module),'source_hashes':source_hashes,
        'reviewed_source_hashes_match':True,'wheel_sha256':hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
        'scenarios':records,'live_access_authorizations':'closed','all22_stage7_checks':'reserved'}
(args.output/'report.json').write_bytes(canonical_json(report))
inventory={path.relative_to(args.output).as_posix():{'bytes':path.stat().st_size,
           'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
           for path in args.output.rglob('*') if path.is_file()}
(args.output/'sha256.json').write_bytes(canonical_json(inventory))
print(canonical_json(report).decode())
```

Record argv, real exit/stdout/stderr and UTC recording time outside the proof inventory (controller envelope, hashed separately). Compare the inventory's exact payload file set and all hashes; exclude only the inventory itself. Use unique output paths and create-only semantics. Require guard denial checks and source/raw/registry/pointer captures from native acceptance. No production resource, image, deployment or range support claim. Add backfill/daily help checks to `scripts/check-sec-edgar-ingest.sh` without weakening its offline/frozen guard.

- [ ] **Step 4: Run complete fresh verification and review.**

```bash
./scripts/check-sec-edgar-ingest.sh
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest backfill --help
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest daily --help
```

Expected full guarded suite PASS (baseline Stage3 is 452 historical tests; record actual expanded count), wheel/sdist/help/version/compile pass. Build only in execution worktree; use resulting wheel by exact SHA. Install offline into the fresh env with `uv pip install --offline --python /private/tmp/sec-edgar-stage4-installed-env/bin/python <absolute-reviewed-wheel>`. If cache is missing, stop as an offline execution blocker. Run installed proof with `python -I` and explicit copied support path configured inside script, output outside package/worktree code. Verify proof inventory and installed-source hashes. No project/source path may satisfy installed imports.

Run whole-branch review through `requesting-code-review` after all scoped task reviews. Resolve findings, then re-run only checks justified by repairs plus the final full acceptance check. Preserve each failed proof/red cycle and its corrected result; do not overwrite historical Stage3 evidence. Explain any code/design change as a deviation and get owner input for a changed acceptance boundary.

- [ ] **Step 5: Commit explicit proof/check/evidence paths, apply completion protocol only after gates.**

```bash
git add scripts/prove-sec-edgar-workflows.py scripts/check-sec-edgar-ingest.sh
# Add the exact inspected Stage4 verification files listed in its new inventory.
git commit -m "test: retain native and installed workflow acceptance evidence"
```

Run `writing-plans` resolve-before-defer gate and backlog reporter offline. Stamp Stage4 COMPLETE only with covered matrix, resolved reviews and exact retained proofs; retire Plan4 and Stage4 spec together and fix relative links. Update ignored execution roadmap after the stamp; append later-stage consistency note retaining Stage5–8 unticked and all22 Stage7 checks reserved. Preserve final ignored payload for integration. Use `finishing-a-development-branch` to choose owner-approved integration and managed-worktree cleanup; never merge/overwrite primary or authorize live operations merely because fixture tests pass. Completion is not authorization for Stage5 planning.

## Self-review and owner checkpoint

Spec coverage: §1 authority/preservation → preflight; §2 constraints → Global Constraints; §3 intent/discovery → Tasks4–5; §4 projection/backlog/legacy/halt → Tasks2–4; §5 per-quarter reports/gates/no-new → Tasks1,3–6; §6 native/installed/later-stage limits → Task7. No later-stage build/activation is included. Required baseline/daily examples, signatures, state kinds, exact command/result boundaries and matrix are included above.

Before execution, owner review must assess the proposed singleton projection/parent binding, cross-version legacy recovery and daily no-new/report semantics. Approval authorizes this plan's offline implementation only. Stop here; Stage4 remains unticked and no implementation code has been written.

**Recommended handoff after approval:** open a fresh chat with the exact approved Plan4 path and immutable approval receipt. Execute task-by-task with `subagent-driven-development`, or use `executing-plans` if the owner selects inline execution. Do not carry historical untracked Stage3 originals as authority into execution.
