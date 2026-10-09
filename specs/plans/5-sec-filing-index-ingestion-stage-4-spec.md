# Stage 4: Backfill and daily catch-up workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan task-by-task via subagent-driven-development (the default) — or executing-plans when your human partner chose inline execution at the handoff. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved Stage 4 manual backfill/daily workflows with provable source coverage, conservative discovery, exact replay and durable repair.

**Architecture:** Compose the shipped discover/collect/transform/publish CLI boundaries. Separate original listing provenance, current completion, immutable historical captures and unfinished publish obligations; consumers use one validated evidence chain. Freeze selection before dispatch and commit immutable workflow reports before repairable indexes.

**Tech Stack:** Python >=3.14; stdlib dataclasses/unittest/SQLite; existing Requests/Azure SDK/PyArrow and complete frozen uv.lock; local fixture and existing Azure adapters.

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

**Status: PROPOSED FOR OWNER REVIEW (2026-10-08). Implementation remains stopped.** This replacement document preserves the approved specification. Original Plan 4 and its correction addendum supply scope/history; their earlier implementation permission is superseded by the stop. Only fresh approval of this replacement plan and a fresh execution handoff can restart work. No task below has been executed in this planning session.

## Authority and preservation gate

Planning checkout: `/Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar`, branch `codex/sec-edgar-stage-4-replan`, based on final stop checkpoint `e870a7318d47699c0e4a76ab59fba72781b0debe`. Primary main/local origin/main remain `fe95642bddf006f3d2d6cb3ccc57e595d75dc4cd`; no fetch. Original execution branch `codex/sec-edgar-stage-4` remains preserved. The original execution checkout is `/Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar`; it is read-only and must not be reset, removed, built into or used as the execution target for Plan 5.

Read the complete tracked [replanning handoff](../evidence/sec-filing-index-ingestion/stage-4/execution/replanning-handoff.md), original [implementation handoff](../evidence/sec-filing-index-ingestion/stage-4/implementation-handoff.md), [ultra review](../evidence/sec-filing-index-ingestion/stage-4/execution/ultra-plan-review.md), [correction addendum](../evidence/sec-filing-index-ingestion/stage-4/execution/execution-addendum.md), [stop checkpoint](../evidence/sec-filing-index-ingestion/stage-4/execution/implementation-stop.md), Task 1 report/review/fix logs and gap interface. Completed Stage 3 spec and completed Plan 3 are authoritative; primary untracked Stage 3 originals are historical.

Reverify original source and snapshot SHA-256 before any execution mutation:

| Document | Exact SHA-256 |
|---|---|
| Approved Stage 4 spec/source snapshot | `5b822a4113eaa18c53a18ae71f244d6b69d2abd9e533381a69644e4b88cd1b0a` |
| Original Plan 4/source snapshot | `d23d62c965f51a4af9a89edd615cc77ed267b58601875f06bcd27cc339c2508c` |
| Roadmap at approval | `0101934eadf0ca3241b03a458c80ec300012430875c44522410836ab6c0ecc03` |
| Original owner receipt | `1a4beabfe15f8d39bb710ba7f92fb9ac1ea60eafc926a8f28905ad6c2ea176bc` |

Preserve their bytes, PROPOSED headers, relative links, and read-only approved snapshots. Never replace Plan 4 in place. Plan IDs were inspected in active/completed directories; 5 is the next ID. Do not retire Plan 4/spec or mark Stage 4 complete while replanning.

Preservation roots are retained inputs, never output directories:

- `/private/tmp/sec-edgar-stage3-merged-closeout-hhgufen8`
- `/private/tmp/sec-edgar-stage4-reconcile-9mbg9qog`
- `/private/tmp/sec-edgar-primary-reconcile-1t9zru9x`
- `/private/tmp/sec-edgar-stage4-execution-preservation-bm3tc33_` (30,017 records / 424,389,627 bytes at original execution preflight)
- `/private/tmp/sec-edgar-stage4-replanning-ubszs55d` (this planning session's primary/retained pre-creation hash inventories)

Preserve primary's ignored roadmap, historical wheel/dist, untracked Stage 3 originals, all existing evidence, and these required absences:

```text
packages/sec-edgar-index-ingest/README.md
packages/sec-edgar-index-ingest/pyproject.toml
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py
packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed
```

During planning the earlier chat was archived concurrently, archiving its worktree. The snapshot ref `refs/codex/snapshots/44e1d887f038bc90b963848b95a277c13f57f9d9` resolves to the final stop checkpoint. Record the exact recovery disposition in the replanning verification receipt; do not infer that Git restores ignored files. Execution is gated on owner-reviewed preservation reconciliation against the 30,854-record retained pre-archive inventory. The planning tool cannot restore another chat's archived attachment. The owner later reported recovery; this session still found the original path absent and therefore does not certify restoration. Exact ignored evidence recovery is retained at `/private/tmp/sec-stage4-ignored-recovery-phpsldej`: all 12 SDD files and the ignored roadmap matched their pre-archive hashes; 1,555 records / 147,893,973 regular bytes plus three symlink targets were recovered. The remaining 433 unmatched records are environment/bytecode artifacts (374 `.venv` records and 59 package `.pyc` files), not approved source/snapshot evidence. Preserve its `receipt.json` SHA-256 `a1ccf73e2032ed2dd18f9f441c96f365d08f8f94496010d34f4c6c2f306a3597` and payload. No complete retained-tree preservation claim is made until these records and the managed attachment are reconciled; this gate does not prevent owner review of the replacement plan. Preserve the new planning checkout and original branch regardless.

The final planning preflight also observed newly added Stage 4 evidence in primary during external recovery. All original primary records and its index remain exact; every added file matches the stopped checkpoint. Preserve these additions in place and consult the verification receipt for their inventory. This planning session wrote no primary files.

After owner approval, run a fresh preservation preflight and inspect managed artifacts under using-git-worktrees. Create/reuse a separate execution checkout from the reviewed planning commit, after inspection; preserve both stopped and planning checkouts. Offline setup only. Never `git add -A`, stash/reset/restore in primary. Record primary HEAD/index/status, all regular/symlink hashes and required absences before/after any worktree operation. Use explicit staged paths in the execution checkout only.

## Partial code disposition and review protocol

Candidate Task 1 code is in `workflows/__init__.py`, `workflows/contracts.py`, `tests/test_workflow_contracts.py` at commits `791e91dc` and `3713cff7`. It is unaccepted; its interrupted review does not supply an acceptance gate. Task 1 of this plan adopts it as a candidate, runs all retained regressions afresh, extends evidence contracts, and obtains fresh spec/quality review. Preserve original commits/logs. Any replacement belongs in the new execution branch with a reviewed diff, never a reset of the stopped branch. Retain the test-only baseline race repair `775866aa`; historical 452-test baseline precedes the partial contracts and is not current Stage 4 verification.

Every task below owns an independently testable deliverable. For each: retain actual red output before implementation, keep test assertions unchanged for green, run listed scoped regressions, record commands/exits/stdout/stderr and create-only evidence, then commit its explicit paths and obtain fresh task-scoped spec/quality review before the next task. Existing candidate tests can begin green; add a genuinely new failing regression for new behavior rather than deleting candidate code to manufacture red. Findings affecting scope/acceptance go to owner; corrections already required by spec stay in scope. Resolve actual available roles/models; Opus/Sonnet/Haiku aliases are unavailable here and must not be claimed.

All commands below are execution instructions after approval, not authorization to run them in this planning session. Run from the inspected execution root. Test commands use `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p <named-pattern> -v`. Missing cache is a blocker. Never replace a cache failure with network or pin changes.

## File responsibilities and dependency order

| Task | Owned implementation/tests | Responsibility and predecessor |
|---|---|---|
| 1 | workflows/contracts.py; test_workflow_contracts.py | Reassess candidate contracts, reducer, typed completion record |
| 2 | workflows/provenance.py; workflows/members.py; discovery.py; tests/support_workflows.py; test_workflow_provenance.py | Real parent/session/listing provenance; projection and registry, consumes 1 |
| 3 | workflows/checked.py; test_workflow_checked.py | Persist exact child call before invoking shipped CLI and verify durable evidence, consumes 1–2 |
| 4 | workflows/completion.py; test_workflow_completion.py; tests/support_workflow_evidence.py | Current/historical completion and outstanding repair evidence, consumes 1–3 |
| 5 | workflows/processing.py; test_workflow_processing.py | One source collect→transform→publish, repair resolution, consumes 1–4 |
| 6 | workflows/results.py; test_workflow_results.py | Frozen intent/selection, immutable captures/report, index repair/replay, consumes 1–5 |
| 7 | workflows/legacy.py; test_workflow_legacy.py | Original pre-Stage4 provenance reconstruction, corrupt isolation/no recursive projections, consumes 1–4 |
| 8 | workflows/runner.py; test_workflow_runner.py | Discovery, pending union/selection, ordered dispatch, baseline/report attribution, consumes 1–7 |
| 9 | cli.py; test_workflow_cli.py; test_azure_state_payloads.py; runbook/READMEs | Manual CLI, validation/exception/log lifecycle, consumes 1–8 |
| 10 | tests/workflow_proof.py; test_workflow_acceptance.py; test_workflow_process.py; fixture bodies/manifest/expected | Real composition and spawned-process acceptance, consumes 1–9 |
| 11 | scripts/prove-sec-edgar-workflows.py; tests/locked_proof.py; test_workflow_installed_lock.py; check script; new evidence | Complete-lock isolated installed proof/full gates/integration handoff, consumes 1–10 |

Prefixes: implementation modules are `packages/sec-edgar-ingest/src/sec_edgar_ingest/`; tests are `packages/sec-edgar-ingest/tests/`. Exact paths appear in each task. Registry/pending uses completion.evaluate_member, never a second success predicate. No new physical table/container/dependency: non-Attempt workflow indexes route through existing SourceState; workflow reports route runs/* to results. Child Attempt remains shipped Attempts; active pointer remains the only data authority.

### Task 1: Reassess candidate contracts and define evidence results

**Files:** Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py`, `packages/sec-edgar-ingest/tests/test_workflow_contracts.py`; retain `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/__init__.py`.

**Interfaces:** Preserve `MemberResult`, `WorkflowResult`, `member_status`, `summarize`, `workflow_path` field/signature contracts. Add `CompletionEvaluation` below. Child-call records are defined in Task 3 before consumers; they are Mapping codecs, not free-standing success flags.

- [ ] Read candidate files and all retained Task 1 review/red/green evidence. Record adoption decision and exact candidate hashes; no task is already accepted.
- [ ] Add this failing typed-evidence regression to `test_workflow_contracts.py`:

```python
class CompletionRecordTests(unittest.TestCase):
    def test_incomplete_capture_cannot_claim_completion(self):
        from sec_edgar_ingest.workflows.contracts import CompletionEvaluation
        from sec_edgar_ingest.models import Error
        gap = Error('publication_missing', 'not committed', True, None, {})
        with self.assertRaises(ValueError):
            CompletionEvaluation(True, None, (), ())
        with self.assertRaises(ValueError):
            CompletionEvaluation(True, {'member_id': 'a' * 64}, (), (gap,))
        with self.assertRaises(ValueError):
            CompletionEvaluation(True, {'member_id': 'a' * 64}, ({'id': 'b' * 64},), ())
        value = CompletionEvaluation(False, None, (), (gap,))
        self.assertEqual(CompletionEvaluation.from_mapping(value.to_mapping()), value)
```

- [ ] Run guarded `test_workflow_contracts.py`; expected the new import/API failure while retained cases remain green. Record the actual failure.
- [ ] Add this exact structural record; storage authority remains Task 4:

```python
@dataclass(frozen=True, slots=True)
class CompletionEvaluation(Record):
    complete: bool
    capture: Mapping[str, object] | None
    obligations: tuple[Mapping[str, object], ...]
    gaps: tuple[Error, ...]

    def __post_init__(self):
        validate_record_fields(self)
        if self.complete and (self.capture is None or self.obligations or self.gaps):
            raise ValueError('completion requires capture and no unresolved obligations/gaps')
```

- [ ] Keep all candidate strict nested Mapping/unknown-field/ref/time/count tests, every EXIT_CODES classification, worst-source-status counting and fixed fatal precedence. Run direct and nested decoder rejection for all pending quarantined outcomes. Keep quarantine terminal failed/no accepted transform; no zero-row parser tolerance.
- [ ] Add the actual skipped-source regression, then replace summarize with the implementation below. Completed skipped sources participate in precedence before the reducer chooses an outcome; no post-reduction counter increment is allowed. These cases need no storage authority because Task 6 validates the captures before this pure reducer consumes the set.

```python
class SkippedSourceTests(unittest.TestCase):
    def test_complete_source_participates_in_quarantine_precedence(self):
        from sec_edgar_ingest.models import Source, Error
        from sec_edgar_ingest.workflows.contracts import MemberResult, summarize
        from sec_edgar_ingest.urls import source_id
        url = 'https://www.sec.gov/Archives/edgar/daily-index/2026/QTR4/master.20261001.idx'
        source = Source(source_id(url), url, 'daily', '2026-10-01', 'idx')
        refused = MemberResult('b' * 64, source,
            'worksets/sec/source/sha256=' + 'c' * 64 + '/workset.json',
            None, None, (), 'quarantined', False, False, True, (), (),
            'fixture-index-parser-v1', 'sec-index-v1')
        outcome, counts = summarize((refused,), (), 1, 0, 'backfill', ('d' * 64,))
        self.assertEqual(outcome, 'incomplete')
        self.assertEqual((counts['complete_sources'], counts['failed_sources'],
                          counts['quarantined_sources']), (1, 1, 1))
        with self.assertRaises(ValueError):
            summarize((refused,), (), 1, 0, 'backfill', (source.source_id,))
        with self.assertRaises(ValueError):
            summarize((), (), 0, 0, 'daily', ('d' * 64, 'd' * 64))
```

```python
def summarize(
    members: tuple[MemberResult, ...], gaps: tuple[Error, ...], discovered_new: int,
    unresolved_before: int = 0, command: str = 'daily',
    already_complete_sources: tuple[str, ...] = (),
) -> tuple[str, dict[str, int]]:
    for identity in already_complete_sources:
        require_hash(identity, 'already_complete_source')
    if len(set(already_complete_sources)) != len(already_complete_sources) or set(already_complete_sources) & {member.source.source_id for member in members}:
        raise ValueError('already-complete identities overlap or duplicate selected sources')
    grouped = {identity: 'complete' for identity in already_complete_sources}
    rank = {'complete': 0, 'pending': 1, 'failed': 2}
    for member in members:
        identity = member.source.source_id
        status = member_status(member.outcome)
        if identity not in grouped or rank[status] > rank[grouped[identity]]:
            grouped[identity] = status
    states = Counter(grouped.values())
    counts = {name + '_sources': states[name] for name in ('complete', 'pending', 'failed')}
    quarantined_ids = {member.source.source_id for member in members if member.quarantined}
    counts.update(
        discovered_sources=discovered_new,
        downloaded_sources=len({member.source.source_id for member in members if member.downloaded}),
        transformed_sources=len({member.source.source_id for member in members if member.transformed}),
        quarantined_sources=len(quarantined_ids),
    )
    quarters = Counter(quarter.outcome for member in members for quarter in member.quarters)
    counts.update(
        published_quarters=quarters['published'], unchanged_quarters=quarters['unchanged'],
        awaiting_approval_quarters=quarters['awaiting_approval'],
    )
    outcomes = {member.outcome for member in members} | {gap.code for gap in gaps}
    fatal = next((outcome for outcome in FATAL if outcome in outcomes), None)
    if fatal:
        return fatal, counts
    all_quarantined = bool(members) and not already_complete_sources and all(
        member.quarantined and member_status(member.outcome) == 'failed' for member in members
    )
    # Retained baseline gaps may derive solely from checked whole-source refusals.
    if all_quarantined and all(_gap_derived_from_quarantine(gap, quarantined_ids) for gap in gaps):
        return 'quarantined', counts
    if gaps or (states['complete'] and (states['failed'] or states['pending'])):
        return 'incomplete', counts
    if states['failed']:
        return 'incomplete', counts
    if states['pending']:
        return ('awaiting_approval' if outcomes == {'awaiting_approval'} else 'pending'), counts
    if not members:
        return ('no_new_sources' if command == 'daily' and not discovered_new and not unresolved_before else 'unchanged'), counts
    if command == 'daily' and not discovered_new and not unresolved_before and not counts['published_quarters']:
        return 'no_new_sources', counts
    return ('success' if counts['published_quarters'] else 'unchanged'), counts
```

Replace the WorkflowResult.__post_init__ reduction/count block (from `outcome, counts = summarize` through its equality check) with:

```python
        already = self.intent.get('already_complete_sources', ())
        if not isinstance(already, tuple):
            raise ValueError('already-complete sources must be an array')
        outcome, counts = summarize(
            self.members, self.gaps, self.intent['discovered_sources'],
            self.intent['unresolved_before'], self.context.command, already,
        )
        if self.outcome != outcome or self.to_mapping()['counts'] != counts:
            raise ValueError('workflow counters/outcome disagree with exact members/gaps')
```

- [ ] Keep the F5 gap interface exact: baseline_publication_missing; coverage_cause=selected_source_quarantine; nonempty unique source_ids array subset of selected terminal refused identities; optional source_id belongs to that array. Retain every gap. Structurally consistent markers cannot confer stored-object authority. Independent directory/missing-source/legacy/repair gaps prevent pure quarantine.
- [ ] Repeat guarded contracts test; expected all retained/new methods PASS. Run `git diff --check`; commit only owned paths with `feat: define validated workflow completion evidence`; fresh review must accept candidate invariants and reducer including skipped-complete mixed progress.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_contracts.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/contracts.py packages/sec-edgar-ingest/tests/test_workflow_contracts.py
git commit -m "feat: define validated workflow completion evidence"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 2: Original provenance, exact projections and durable registry

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/provenance.py`, `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py`, `packages/sec-edgar-ingest/tests/test_workflow_provenance.py`, `packages/sec-edgar-ingest/tests/support_workflows.py`; modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py` only to expose its retained-listing validator as public `reopen_listing` and update its internal call.

**Interfaces:** `read_parent(ref: str, store, objects) -> SourceWorkset`; `project_member(parent_ref: str, source_id: str, store, objects) -> Mapping[str,object]`; `read_member(value: Mapping[str,object],store,objects) -> SourceWorkset`; `transfer_binding(value, snapshot, store, objects) -> Binding`; `WorkflowMembers(store,objects).all() -> tuple[Mapping,...]`, `.inventory() -> tuple[tuple[Mapping,...],tuple[Error,...]]`, `.register(parent_ref,member_ref) -> Mapping`, `.record(result,context,evidence) -> Mapping`. Record/pending authority is completed in Tasks 4–5; this task never invents successful completion.

- [ ] Add the complete real-listing regression below; fixture_workset's arbitrary hash is insufficient here:

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import tempfile, unittest
from datetime import date
from pathlib import Path
from support import discovery_harness, listing_response, failed_response
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.workflows.provenance import project_member, read_member

class ProvenanceTests(unittest.TestCase):
    def test_valid_member_of_failed_parent_retains_original_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            h = discovery_harness(Path(directory), {
                '2026Q3': [failed_response(404)],
                '2026Q4': [listing_response('2026Q4', ['master.20261001.idx'])],
            })
            try:
                parent = h.run('daily', date(2026, 10, 7), 'provenance')
                self.assertFalse(parent.discovery_complete)
                parent_ref = h.workset_path(parent)
                parent_bytes = h.objects.read(parent_ref)
                value = project_member(parent_ref, parent.members[0].source_id, h.store, h.objects)
                child = read_member(value, h.store, h.objects)
                self.assertTrue(child.discovery_complete)
                self.assertEqual(child.members, (parent.members[0],))
                self.assertEqual(child.context, parent.context)
                self.assertEqual(h.objects.read(parent_ref), parent_bytes)
                self.assertEqual(value['parent_ref'], parent_ref)
                self.assertEqual(project_member(parent_ref, parent.members[0].source_id,
                                               h.store, h.objects), value)
                self.assertEqual(len(tuple(h.store.scan('WorkflowMember', {}))), 1)
                progress = h.state.directory_progress('provenance', child.directories[0].url)
                body_path = progress.value['evidence']['body_path']
                target = h.root / 'objects' / body_path
                retained = target.read_bytes()
                target.write_bytes(retained + b' ')
                try:
                    with self.assertRaises((Conflict, ValueError, OSError)):
                        read_member(value, h.store, h.objects)
                finally:
                    target.write_bytes(retained)
            finally:
                h.close()
    def test_corrupt_registry_is_reported_without_hiding_valid_sibling(self):
        from sec_edgar_ingest.workflows.members import WorkflowMembers
        with tempfile.TemporaryDirectory() as directory:
            h = discovery_harness(Path(directory), {
                '2026Q4': [listing_response('2026Q4', ['master.20261001.idx', 'master.20261002.idx'])]})
            try:
                parent = h.run('daily', date(2026, 10, 7), 'two-members')
                values = [project_member(h.workset_path(parent), source.source_id, h.store, h.objects)
                          for source in parent.members]
                self.assertEqual(len(values), 2)
                row = h.store.get('WorkflowMember', values[0]['member_id'])
                altered = row.to_mapping()['value']; altered['source']['period'] = '2026-10-03'
                h.store.replace('WorkflowMember', values[0]['member_id'], altered, row.version)
                valid, gaps = WorkflowMembers(h.store, h.objects).inventory()
                self.assertEqual(valid, (values[1],))
                self.assertEqual(len(gaps), 1)
                self.assertEqual(gaps[0].code, 'legacy_member_unresolved')
            finally:
                h.close()

    def test_retained_parent_and_member_tampering_refuses(self):
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as directory:
            h = discovery_harness(Path(directory), {
                '2026Q4': [listing_response('2026Q4', ['master.20261001.idx'])]})
            try:
                parent = h.run('daily', date(2026, 10, 7), 'tamper-member')
                value = project_member(h.workset_path(parent), parent.members[0].source_id, h.store, h.objects)
                variants = []
                for key in ('member_id', 'parent_ref', 'member_ref'):
                    altered = deepcopy(value)
                    altered[key] = '0' * 64 if key == 'member_id' else value[key].replace('sha256=', 'sha256=0')
                    variants.append(altered)
                altered = deepcopy(value); altered['source']['period'] = '2026-10-02'; variants.append(altered)
                altered = deepcopy(value); altered['source']['canonical_url'] += '.other'; variants.append(altered)
                for altered in variants:
                    with self.subTest(altered=altered):
                        with self.assertRaises((Conflict, ValueError, OSError, KeyError)):
                            read_member(altered, h.store, h.objects)
                progress = h.state.directory_progress(parent.discovery_id, parent.directories[0].url)
                saved = progress.to_mapping()['value']
                altered = deepcopy(saved); altered['evidence']['byte_count'] += 1
                # Select a real successful required unit; its checked receipt bytes must agree.
                h.store.replace('DirectoryProgress', __import__('hashlib').sha256(
                    canonical_json(to_mapping_value([parent.discovery_id, parent.directories[0].url]))).hexdigest(), altered, progress.version)
                with self.assertRaises((Conflict, ValueError, OSError, KeyError)):
                    read_member(value, h.store, h.objects)
            finally:
                h.close()

    def test_divergent_binding_winner_stays_unchanged(self):
        from sec_edgar_ingest.models import Binding
        from sec_edgar_ingest.state import AcquisitionState
        from support import fixture_snapshot
        from sec_edgar_ingest.workflows.provenance import transfer_binding
        with tempfile.TemporaryDirectory() as directory:
            h = discovery_harness(Path(directory), {
                '2026Q4': [listing_response('2026Q4', ['master.20261001.idx'])]})
            try:
                parent = h.run('daily', date(2026, 10, 7), 'binding-winner')
                value = project_member(h.workset_path(parent), parent.members[0].source_id, h.store, h.objects)
                state = AcquisitionState(h.store); source = parent.members[0]
                first = fixture_snapshot(source, b'first immutable raw bytes')
                second = fixture_snapshot(source, b'second immutable raw bytes')
                for snapshot, body in ((first, b'first immutable raw bytes'), (second, b'second immutable raw bytes')):
                    h.objects.put_once(snapshot.raw_path, body); state.remember_snapshot(snapshot)
                winner = state.bind_once(Binding(value['member_id'], source.source_id, first.sha256))
                with self.assertRaises(Conflict):
                    transfer_binding(value, second, h.store, h.objects)
                self.assertEqual(state.binding(value['member_id'], source.source_id), winner)
            finally:
                h.close()
```

- [ ] Run guarded `test_workflow_provenance.py`; expect missing provenance module. Keep the actual red output.
- [ ] Rename `_reopen_listing` to `reopen_listing` with identical body/internal caller. Create provenance functions below. The exact parent traversal check applies to cached units too; it does not make failed units complete.

```python
from ..models import to_mapping_value
import hashlib
from dataclasses import replace
from ..models import Binding, RunContext, canonical_json
from ..state import AcquisitionState
from ..storage.contracts import AlreadyExists, Conflict
from ..worksets import decode_source_workset, encode_workset, make_source_workset
from ..discovery import reopen_listing
from ..urls import child_url

def immutable(store, kind, key, value):
    try:
        store.insert(kind, key, value)
    except AlreadyExists:
        row = store.get(kind, key)
        if row is None or canonical_json(to_mapping_value(row.to_mapping()['value'])) != canonical_json(to_mapping_value(value)):
            raise Conflict(kind + ' immutable identity differs')

def source_ref(workset):
    return f'worksets/sec/source/sha256={workset.workset_id}/workset.json'

def read_source(ref, objects):
    body = objects.read(ref)
    workset = decode_source_workset(body)
    if source_ref(workset) != ref or encode_workset(workset) != body:
        raise Conflict('source reference or canonical bytes differ')
    return workset

RECOVERY_FORMAT = 'sec-workflow-parent-recovery-v1'

def rebuild_recovered_parent(session, progress, objects):
    from datetime import date
    from ..models import DirectoryOutcome, Error
    frozen = session['frozen']
    if session['discovery_id'] == '' or set(frozen) != {
            'context', 'today', 'end', 'mode', 'acquisition_mode', 'units', 'overlap_from'}:
        raise Conflict('recovery frozen discovery fields differ')
    origin = RunContext.from_mapping(frozen['context'])
    if origin.command != 'discover' or frozen['mode'] not in ('daily', 'quarterly'):
        raise Conflict('recovery is not original discovery provenance')
    if origin.pinned_on is None or origin.pinned_on.isoformat() != frozen['today']:
        raise Conflict('recovery changes original discovery date')
    units = frozen['units']
    if not units or len({unit['url'] for unit in units}) != len(units):
        raise Conflict('recovery requires unique frozen required units')
    expected = sorted(units, key=lambda unit: (unit['url'].count('/'), unit['url']))
    if len(progress) != len(expected) or [p['unit'] for p in progress] != expected:
        raise Conflict('recovery omits or reorders required units')
    entries, members, outcomes = {}, {}, []
    for captured in progress:
        if set(captured) != {'unit', 'value'}:
            raise Conflict('recovery progress fields differ')
        unit, value = captured['unit'], captured['value']
        if set(unit) not in ({'url', 'period', 'role'}, {'url', 'period', 'role', 'bridge_period'}):
            raise Conflict('recovery unit fields differ')
        if unit['role'] not in ('root', 'year', 'quarter'):
            raise Conflict('recovery unit role differs')
        if value is None:
            outcome = DirectoryOutcome(unit['url'], unit['period'], 'discovery_failed', None, (),
                Error('discovery_pending', 'original required unit has no retained completion', True, None, {}))
            outcomes.append(outcome)
            continue
        if set(value) != {'discovery_id', 'outcome', 'members', 'evidence', 'selection', 'observed_gap_token'}:
            raise Conflict('recovery directory progress fields differ')
        if value['discovery_id'] != session['discovery_id']:
            raise Conflict('recovery directory belongs to another original session')
        outcome = DirectoryOutcome.from_mapping(value['outcome'])
        if (outcome.url, outcome.period) != (unit['url'], unit['period']):
            raise Conflict('recovery directory metadata differs from frozen unit')
        if outcome.outcome == 'discovery_failed':
            if value['members'] or value['evidence'] is not None:
                raise Conflict('failed discovery progress introduces accepted evidence')
            outcomes.append(outcome)
            continue
        if unit['role'] != 'root':
            ancestor = unit['url'].rsplit('/', 2)[0] + '/index.json'
            name = unit['url'].rsplit('/', 2)[1]
            authorized = next((entry for entry in entries.get(ancestor, ())
                               if entry.name == name and entry.kind == 'dir'), None)
            if authorized is None or child_url(ancestor, authorized.href, authorized.name, True) + 'index.json' != unit['url']:
                raise Conflict('recovered successful child lacks actual successful ancestor')
        outcome, selected, children, received = reopen_listing(objects, value, unit, origin)
        entries[unit['url']] = children
        for source in selected:
            if source.source_id in members:
                raise Conflict('recovery duplicates source across required units')
            members[source.source_id] = source
        outcomes.append(outcome)
    return make_source_workset(origin, frozen['end'], session['discovery_id'],
        tuple(members.values()), tuple(outcomes), date.fromisoformat(frozen['overlap_from']),
        acquisition_mode=frozen['acquisition_mode'])


def validate_parent_recovery(parent_ref, descriptor, objects):
    from ..models import parse_json, require_hash
    if set(descriptor) != {'ref', 'sha256', 'bytes'}:
        raise Conflict('recovery descriptor fields differ')
    require_hash(descriptor['sha256'], 'recovery digest')
    expected_path = 'worksets/sec/workflow-parent-recovery/sha256=' + descriptor['sha256'] + '/recovery.json'
    if descriptor['ref'] != expected_path:
        raise Conflict('recovery descriptor address differs')
    objects.verify(descriptor['ref'], descriptor['sha256'], descriptor['bytes'])
    body = objects.read(descriptor['ref'])
    saved = parse_json(body)
    if canonical_json(to_mapping_value(saved)) != body or set(saved) != {'format_version', 'parent_ref', 'parent', 'session', 'progress'}:
        raise Conflict('recovery bytes/schema differ')
    if saved['format_version'] != RECOVERY_FORMAT or saved['parent_ref'] != parent_ref:
        raise Conflict('recovery version/original parent differs')
    parent = read_source(parent_ref, objects)
    rebuilt = rebuild_recovered_parent(saved['session'], saved['progress'], objects)
    if rebuilt != parent or saved['parent'] != parent.to_mapping():
        raise Conflict('recovery changes exact reconstructed original parent')
    return {'session': saved['session'], 'progress': saved['progress']}


def read_parent(ref, store, objects):
    parent = read_source(ref, objects)
    acquisition = AcquisitionState(store)
    row = acquisition.discovery_session(parent.discovery_id)
    if row is None:
        raise Conflict('original discovery session absent')
    saved = row.to_mapping()['value']
    frozen = saved['frozen']
    origin = RunContext.from_mapping(frozen['context'])
    identities = {saved.get('workset_id'), saved.get('predecessor_workset_id')}
    identities.update(item['workset_id'] for item in saved.get('history', ()))
    if parent.workset_id not in identities:
        recovery = store.get('WorkflowParentRecovery', parent.workset_id)
        if recovery is None:
            raise Conflict('parent is neither retained discovery revision nor validated recovery')
        snapshot = validate_parent_recovery(ref, recovery.to_mapping()['value'], objects)
        if (snapshot['session']['discovery_id'] != parent.discovery_id or
                canonical_json(to_mapping_value(snapshot['session']['frozen'])) != canonical_json(to_mapping_value(frozen))):
            raise Conflict('recovery changes original frozen discovery session')
        return parent
    if (origin != parent.context or frozen['end'] != parent.pinned_end_quarter or
            frozen['overlap_from'] != parent.overlap_from.isoformat() or
            frozen['acquisition_mode'] != parent.acquisition_mode):
        raise Conflict('parent changes frozen origin')
    units = {unit['url']: unit for unit in frozen['units']}
    if len(units) != len(frozen['units']) or set(units) != {d.url for d in parent.directories}:
        raise Conflict('parent omits or changes required discovery units')
    entries, reopened = {}, {}
    for unit in sorted(units.values(), key=lambda u: (u['url'].count('/'), u['url'])):
        directory = next(d for d in parent.directories if d.url == unit['url'])
        if directory.outcome == 'discovery_failed':
            if directory.error is None:
                raise Conflict('failed required unit lacks retained error')
            continue
        if unit['role'] != 'root':
            ancestor = unit['url'].rsplit('/', 2)[0] + '/index.json'
            name = unit['url'].rsplit('/', 2)[1]
            entry = next((e for e in entries.get(ancestor, ()) if e.name == name and e.kind == 'dir'), None)
            if entry is None or child_url(ancestor, entry.href, entry.name, True) + 'index.json' != unit['url']:
                raise Conflict('successful unit lacks actual successful parent child')
        progress = acquisition.directory_progress(parent.discovery_id, unit['url'])
        if progress is None:
            raise Conflict('successful listing progress absent')
        outcome, sources, children, received = reopen_listing(objects, progress.to_mapping()['value'], unit, origin)
        if outcome != directory:
            raise Conflict('parent outcome differs from original listing receipt')
        entries[unit['url']] = children
        reopened.update((source.source_id, source) for source in sources)
    if tuple(sorted(reopened)) != tuple(source.source_id for source in parent.members):
        raise Conflict('parent source set differs from successful listings')
    if any(reopened[source.source_id] != source for source in parent.members):
        raise Conflict('parent relabels original source')
    return parent

def projection(parent, source_id):
    selected = tuple(source for source in parent.members if source.source_id == source_id)
    directories = tuple(d for d in parent.directories if source_id in d.source_ids)
    if len(selected) != 1 or len(directories) != 1 or directories[0].outcome == 'discovery_failed':
        raise Conflict('projection needs exact successful immediate member')
    directory = replace(directories[0], source_ids=(source_id,))
    unit = hashlib.sha256(canonical_json(to_mapping_value([parent.workset_id, source_id]))).hexdigest()
    return make_source_workset(parent.context, parent.pinned_end_quarter, 'member-' + unit,
                               selected, (directory,), parent.overlap_from,
                               acquisition_mode=parent.acquisition_mode)

def project_member(parent_ref, source_id, store, objects):
    if any(row.value['member_ref'] == parent_ref for row in store.scan('WorkflowMember', {})):
        raise Conflict('a registered projection cannot become an original parent')
    parent = read_parent(parent_ref, store, objects)
    member = projection(parent, source_id)
    body = encode_workset(member)
    ref = source_ref(member)
    objects.put_once(ref, body)
    objects.verify(ref, hashlib.sha256(body).hexdigest(), len(body))
    value = {'member_id': member.workset_id, 'source': member.members[0].to_mapping(),
             'parent_ref': parent_ref, 'member_ref': ref}
    immutable(store, 'WorkflowMember', member.workset_id, value)
    return value

def read_member(value, store, objects):
    if set(value) != {'member_id', 'source', 'parent_ref', 'member_ref'}:
        raise Conflict('member record fields differ')
    row = store.get('WorkflowMember', value['member_id'])
    if row is None or canonical_json(to_mapping_value(row.to_mapping()['value'])) != canonical_json(to_mapping_value(dict(value))):
        raise Conflict('member record lacks exact registry binding')
    parent = read_parent(value['parent_ref'], store, objects)
    expected = projection(parent, value['source']['source_id'])
    actual = read_source(value['member_ref'], objects)
    if (actual != expected or actual.workset_id != value['member_id'] or
            actual.members[0].to_mapping() != value['source']):
        raise Conflict('member changes exact original projection')
    return actual

def transfer_binding(value, snapshot, store, objects):
    member = read_member(value, store, objects)
    acquisition = AcquisitionState(store)
    remembered = acquisition.snapshot(snapshot.source_id, snapshot.sha256)
    if remembered != snapshot or snapshot.source_id != member.members[0].source_id:
        raise Conflict('binding snapshot metadata differs')
    objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
    requested = Binding(member.workset_id, snapshot.source_id, snapshot.sha256)
    winner = acquisition.bind_once(requested)
    if winner != requested:
        raise Conflict('existing binding winner differs; immutable pin preserved')
    return winner
```

- [ ] Create workflows/members.py with the registry operations available at this task boundary. Task 5 extends this class with receipt/complete methods after checked evidence exists.

```python
from ..models import to_mapping_value
from ..storage.contracts import Conflict
from ..models import canonical_json
from .provenance import project_member, read_member, read_source

class WorkflowMembers:
    def __init__(self, store, objects):
        self.store, self.objects = store, objects

    def inventory(self):
        from ..models import Error
        valid, gaps = [], []
        for row in self.store.scan('WorkflowMember', {}):
            value = row.to_mapping()['value']
            try:
                read_member(value, self.store, self.objects)
                valid.append(value)
            except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
                identity = value.get('member_id') if isinstance(value, dict) else None
                gaps.append(Error('legacy_member_unresolved', str(error), False, None,
                    {'record_kind': 'WorkflowMember', 'member_id': identity,
                     'record_sha256': __import__('hashlib').sha256(canonical_json(to_mapping_value(value))).hexdigest()}))
        return tuple(sorted(valid, key=lambda v: (v['source']['period'], v['source']['source_id'], v['member_id']))), tuple(gaps)

    def all(self):
        values, gaps = self.inventory()
        if gaps:
            raise Conflict('registry contains unresolved corrupt members')
        return values

    def register(self, parent_ref, member_ref):
        selected = read_source(member_ref, self.objects)
        if len(selected.members) != 1:
            raise Conflict('registry requires singleton member')
        value = project_member(parent_ref, selected.members[0].source_id, self.store, self.objects)
        if value['member_ref'] != member_ref:
            raise Conflict('registered member differs from exact projection')
        return value
```

- [ ] Add real-store cases: altered parent/member/source/period/acquisition mode/endpoint, missing successful receipt, wrong receipt context, tampered listing SHA/length, missing required root/year, valid child not authorized by actual parent, and divergent existing Binding. Close/reopen SQLite and verify registry bytes/source identity survive. A conflicting binding test seeds a different accepted snapshot first and verifies the winner remains byte-identical after refusal. Each case modifies only its temporary store, retains before/after proof, and restores the temporary fixture if reused.
- [ ] Repeat guarded provenance test; run guarded `test_discovery.py`, `test_worksets.py`, `test_collection.py` as regressions. Expected PASS. Commit only owned paths with `feat: retain verified original workflow member provenance`; fresh review checks real listing evidence and required ledger, not only well-shaped hashes.

### Task 2 test-support deliverable

Create the builders below in `packages/sec-edgar-ingest/tests/support_workflows.py` now; later tasks consume them. This is fixture construction, not a fake production workflow. Original raw rows are nonempty and parser-compatible. Responses have explicit repeated entries so a fresh discovery cannot exhaust a one-response pack unnoticed.

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, io, zipfile
from pathlib import Path
from sec_edgar_ingest.models import canonical_json
BASE = 'https://www.sec.gov/Archives/edgar/'

def listing(url, children):
    return canonical_json(to_mapping_value({'directory': {'name': url[len(BASE):-len('index.json')],
        'parent-dir': '../', 'item': [
            {'name': name, 'href': name + ('/' if kind == 'dir' else ''), 'type': kind,
             'size': '1', 'last-modified': 'synthetic'} for name, kind in children]}}))

def idx(rows, kind):
    ending, title = ('\r\n', 'Filename') if kind == 'quarterly' else ('\n', 'File Name')
    body = ('CIK|Company Name|Form Type|Date Filed|' + title + ending + '-----' + ending +
            ending.join('|'.join(row) for row in rows) + ending).encode('ascii')
    if kind == 'daily':
        return body
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        info = zipfile.ZipInfo('master.idx', (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, body)
    return output.getvalue()

def build_pack(root, listings, bodies, overrides=None, repeats=8):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root / 'bodies').mkdir()
    merged = {url: listing(url, children) for url, children in listings.items()}
    merged.update(bodies)
    responses = {}
    for url, body in sorted(merged.items()):
        digest = hashlib.sha256(body).hexdigest()
        relative = 'bodies/' + digest + '.body'
        target = root / relative
        if not target.exists():
            target.write_bytes(body)
        spec = {'status': 200, 'headers': {'Content-Length': str(len(body)), 'X-Fixture': 'synthetic'},
                'body_path': relative, 'body_sha256': digest}
        responses[url] = [dict(spec) for _ in range(repeats)]
    responses.update(overrides or {})
    path = root / 'manifest.json'
    path.write_bytes(canonical_json(to_mapping_value({'fixture_version': 'sec-acquisition-fixture-v1',
                                    'provenance': 'synthetic', 'responses': responses})))
    return path
```

All overrides must reference hash-retained bodies in this pack. Keep fixture manifest canonical hash distinct from file-byte SHA if formatting differs; frozen intent uses FixturePack.load(...).manifest_sha256. Accepted handoff remains 2026-10-01; older historical dates/configs are explicitly fixture-only test contexts.


The same support module defines a generic command harness before dispatcher/member tests. It does not implement workflow behavior; main remains production code.

```python
from sec_edgar_ingest.models import to_mapping_value
import contextlib, io, json
from datetime import datetime, timedelta, timezone
from support import fixture_settings
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState

class CommandHarness:
    def __init__(self, root, pack, settings=None):
        self.root, self.pack = Path(root), Path(pack)
        self.settings = settings or fixture_settings(
            backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            etl={'parser_version': 'fixture-index-parser-v1'},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        self.config = self.root / 'config.json'
        self.config.write_bytes(canonical_json(to_mapping_value(self.settings.to_mapping())))
        self.deadline = datetime.now(timezone.utc) + timedelta(seconds=1800)
        self.opened = open_stores(self.settings, base_path=self.root)
        self.store, self.objects, self.leases = self.opened
        self.calls = []

    def invoke(self, command, flags=(), run='r', attempt='a', today='2026-10-07', deadline=None):
        argv = [command, '--config', str(self.config), '--run-id', run, '--execution-id', 'manual',
                '--attempt-id', attempt, '--deadline', (deadline or self.deadline).isoformat(),
                '--state-dir', str(self.root), '--today', today, *flags]
        if command in ('discover', 'collect', 'backfill', 'daily'):
            argv += ['--fixture-pack', str(self.pack)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        message = json.loads(stdout.getvalue())
        self.calls.append({'argv': argv, 'exit': code, 'stdout': message, 'stderr': stderr.getvalue()})
        return code, message

    def capture(self, quarter):
        value = capture_quarter(quarter, self.objects, EtlState(self.store))
        if value is None:
            raise AssertionError('expected published quarter ' + quarter)
        return value, tuple(row.to_mapping() for row in read_quarter(value, self.objects))

    def close(self):
        for resource in reversed(self.opened):
            if hasattr(resource, 'close'):
                resource.close()

def simple_pack(root, *, empty=False, conflicting=False):
    listings, bodies = {}, {}
    for family in ('full-index', 'daily-index'):
        base = BASE + family + '/'
        listings[base + 'index.json'] = [('2026', 'dir')]
        listings[base + '2026/index.json'] = [('QTR3', 'dir'), ('QTR4', 'dir')]
        for quarter in (3, 4):
            leaf = base + f'2026/QTR{quarter}/'
            listings[leaf + 'index.json'] = []
            if empty or (family == 'daily-index' and quarter == 3):
                continue
            kind = 'quarterly' if family == 'full-index' else 'daily'
            filename = 'master.zip' if kind == 'quarterly' else 'master.20261001.idx'
            listings[leaf + 'index.json'] = [(filename, 'file')]
            filed = ('2026-09-30' if quarter == 3 else '2026-10-01') if kind == 'quarterly' else '20261001'
            path = f'edgar/data/123456/0000123456-26-00000{quarter}.txt'
            row = ('123456', 'Example', '10-K', filed, path)
            rows = (row, ('123456', 'Changed', '10-K', filed, path)) if conflicting else (row,)
            bodies[leaf + filename] = idx(rows, kind)
    return build_pack(root, listings, bodies)
```



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_provenance.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/provenance.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/src/sec_edgar_ingest/discovery.py packages/sec-edgar-ingest/tests/support_workflows.py packages/sec-edgar-ingest/tests/test_workflow_provenance.py
git commit -m "feat: retain verified original workflow member provenance"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 3: Checked child dispatch and immutable child evidence

**Files:**
- Create: `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/checked.py`.
- Create: `packages/sec-edgar-ingest/tests/test_workflow_checked.py`.
- Create: `packages/sec-edgar-ingest/tests/support_checked.py`.
- Define `CheckedChild` in this Task 3 module with exact fields `call: Mapping[str, object]`, `result_ref: str`, `result: CommandResult | EtlResult`. Its constructor freezes `call`; it does not certify completion.

**Interfaces:**
- `ChildCall` is a closed validated Mapping with exactly `format_version`, `workflow_command`, `workflow_attempt_id`, `step_id`, `context`, `intent`, `input_ref`, `result_ref`. `context` is the expected CHILD RunContext template. Its `started_at` is the parent workflow's lower bound; the CLI chooses the actual child start and saves it durably. All other child context fields must match exactly.
- `child_attempt_id(run_id: str, workflow_command: str, workflow_attempt_id: str, step_id: str, command: str) -> str` includes the parent command.
- `make_call(context: RunContext, command: str, attempt_id: str, input_ref: str | None, fixture_sha256: str | None = None, *, workflow_command: str, workflow_attempt_id: str, step_id: str, today: date | None = None, mode: str | None = None, discovery_id: str | None = None, refresh: bool = False, force: bool = False) -> Mapping[str, object]`.
- `call_ref(call: Mapping[str, object]) -> str`; `call_key(call: Mapping[str, object]) -> str`.
- `read_child(call: Mapping[str, object], store: StateStore, objects: ObjectStore) -> CommandResult | EtlResult`. This reads immutable authority and checks any call index that exists. It refuses unfinished child Attempt indexes; dispatcher re-enters the shipped CLI to repair those before readback.
- `read_child_capture(call: Mapping[str, object], objects: ObjectStore) -> CommandResult | EtlResult` validates immutable call/command/result and source→snapshot→raw→transformed→observation→generation/candidate objects without mutable indexes or an active pointer. Task 6 uses this for historical report replay, together with its frozen provenance captures.
- `unfinished_child(call: Mapping[str, object], store: StateStore) -> tuple[RunContext, tuple[Error, ...]]` reads exact retained unfinished child evidence; it never marks the child complete.
- `Dispatcher(context: RunContext, settings: Settings, fixture_pack: Path | None, state_dir: Path | None, store: StateStore, objects: ObjectStore, observer: BoundaryObserver | None = None)`; `.execute(command: str, step_id: str, settings: Settings, flags: tuple[str, ...]) -> CheckedChild`.
- `ChildUnfinished` exposes `call`, `outcome`, `gaps`, `repair_pending`, `exit`, `stdout`, `stderr`. Task 5 propagates unfinished repair without writing member/workflow completion. Durable failed child results still return `CheckedChild`, because completed failed attempts are immutable.

**Authority and design constraints:** call object at `runs/sec/<run>/<workflow-command>/<workflow-attempt>/children/<child-attempt>/call.json` precedes the immutable `WorkflowChildCall` index. The state key hashes `[run_id, workflow_command, workflow_attempt_id, child_attempt_id]`. Calls describe expected invocation, never source completion. Read successful publication evidence through the exact result manifest paths, without consulting a later active pointer. Task 2 owns original parent/listing receipt reopening; this task validates the canonical child input chain and rejects a changed command/input/context before trusting results. No result stdout or exit code alone can authorize completion.

- [ ] **Step 1: Supply the real-store fixture builder and failing tests.**

Create `tests/support_checked.py` with the following complete builder. It uses real discovery, collection, transform, publication, result objects, SQLite state, and original fixture listing bodies. All network/provider construction is denied before imports. Its default fixture date is explicit and it gives every URL eight sequence entries so exact replay can prove cursor stability while new workflow runs can discover again.

```python
from network_guard import install
install()

from sec_edgar_ingest.models import to_mapping_value
import hashlib
import json
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from support import fixture_settings, fixture_source, listing_response, store_bundle, zip_bytes
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.models import RunContext, canonical_json


def workflow_fixture(root: Path, *, command='backfill', prefix=False):
    root.mkdir(parents=True, exist_ok=True)
    settings = fixture_settings(
        backfill={'start_quarter': '2026Q4', 'end_quarter': 'open'},
        daily={'start_date': '2026-10-01'},
        etl={'parser_version': 'fixture-index-parser-v1'},
        http={'retry_base_seconds': 0.001, 'retry_cap_seconds': 0.001},
        fixture={'allow_clock_override': True, 'allow_deadline_override': True},
    )
    now = datetime.now(timezone.utc)
    context = RunContext('checked-run', 'checked-execution', command, 'checked-attempt',
        settings.worker.image_digest, settings.etl.parser_version, settings.etl.schema_version,
        settings.config_sha256, now, now + timedelta(seconds=3600), command)
    context = pin_context(settings, context, date(2026, 10, 8))[0]
    bodies = root / 'bodies'
    bodies.mkdir(exist_ok=True)
    responses = {}

    def response(body, *, fault=None):
        digest = hashlib.sha256(body).hexdigest()
        (bodies / (digest + '.body')).write_bytes(body)
        value = {'status': 200, 'headers': {'Content-Length': str(len(body))},
                 'body_path': 'bodies/' + digest + '.body', 'body_sha256': digest}
        if fault is not None:
            value['fault'] = fault
        return value

    def listing(family, period, names):
        if period == family:
            url = f'https://www.sec.gov/Archives/edgar/{family}/index.json'
        elif 'Q' in period:
            year, ordinal = period.split('Q')
            url = f'https://www.sec.gov/Archives/edgar/{family}/{year}/QTR{ordinal}/index.json'
        else:
            url = f'https://www.sec.gov/Archives/edgar/{family}/{period}/index.json'
        spec = listing_response(period, names, family=family)
        responses[url] = [response(spec.body) for _ in range(8)]

    listing('full-index', 'full-index', ['2026/'])
    listing('full-index', '2026', ['QTR4/'])
    listing('full-index', '2026Q4', ['master.zip'])
    listing('daily-index', 'daily-index', ['2026/'])
    listing('daily-index', '2026', ['QTR3/', 'QTR4/'])
    listing('daily-index', '2026Q3', [])
    listing('daily-index', '2026Q4', ['master.20261001.idx'])
    quarterly = zip_bytes(b'CIK|Company Name|Form Type|Date Filed|Filename\r\n-----\r\n'
        b'123456|Quarterly|10-K|2026-10-01|edgar/data/123456/0000123456-26-000001.txt\r\n')
    daily = (b'CIK|Company Name|Form Type|Date Filed|File Name\n-----\n'
        b'123456|Daily|10-K|20261001|edgar/data/123456/0000123456-26-000002.txt\n')
    for source, body in ((fixture_source('2026Q4'), quarterly),
                         (fixture_source('2026-10-01', 'daily'), daily)):
        sequence = [response(body) for _ in range(8)]
        if prefix:
            sequence.insert(0, response(b'retained retry prefix', fault='read_timeout'))
        responses[source.canonical_url] = sequence
    pack = root / 'manifest.json'
    pack.write_bytes(canonical_json(to_mapping_value({'fixture_version': 'sec-acquisition-fixture-v1',
        'provenance': 'synthetic', 'responses': responses})))
    store, objects, leases = store_bundle(root / '.fixture-state')
    leases.close()
    return settings, context, pack, store, objects


def cursor_values(store):
    return [row.to_mapping() for row in store.scan('FixtureResponseCursor', {})]


def dispatch_chain(dispatcher, settings, *, discovery_id='checked-discovery'):
    found = dispatcher.execute('discover', 'discover', settings,
        ('--mode', 'quarterly', '--discovery-id', discovery_id))
    collected = dispatcher.execute('collect', 'collect-one', settings,
        ('--workset', found.result.source_workset_ref))
    transformed = dispatcher.execute('transform', 'transform-one', settings,
        ('--workset', collected.result.snapshot_workset_ref))
    published = dispatcher.execute('publish', 'publish-one', settings,
        ('--workset', transformed.result.transformed_workset_ref))
    return found, collected, transformed, published
```

Create `tests/test_workflow_checked.py`:

```python
from network_guard import install
install()

import hashlib
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from support import Faults, CollectionCrash
from support_checked import workflow_fixture, dispatch_chain, cursor_values
from sec_edgar_ingest.config import Settings, pin_context
from sec_edgar_ingest.models import Binding, canonical_json, parse_json, to_mapping_value
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.workflows.checked import (
    Dispatcher, ChildUnfinished, call_ref, child_attempt_id, read_child,
)


class CheckedWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.settings, self.context, self.pack, self.store, self.objects = workflow_fixture(self.root)
        self.addCleanup(self.store.close)
        self.dispatcher = Dispatcher(self.context, self.settings, self.pack, self.root,
                                     self.store, self.objects)

    def test_checked_record_freezes_call_and_rejects_result_reference_change(self):
        from sec_edgar_ingest.workflows.checked import CheckedChild
        child = self.dispatcher.execute('discover', 'record-discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-record-session'))
        mutable = child.to_mapping()['call']
        value = CheckedChild(mutable, child.result_ref, child.result)
        original = value.call['intent']['discovery_id']
        mutable['intent']['discovery_id'] = 'changed-session'
        self.assertEqual(value.call['intent']['discovery_id'], original)
        with self.assertRaises(ValueError):
            CheckedChild(child.call, child.result_ref + '.changed', child.result)
        with self.assertRaises(ValueError):
            CheckedChild(child.call, child.result_ref, child.result.to_mapping())

    def test_boolean_call_flags_reject_integer_substitution(self):
        from sec_edgar_ingest.workflows.checked import make_call, child_attempt_id, call_ref
        for command, field, kwargs in (
                ('discover', 'refresh', {'mode': 'quarterly', 'discovery_id': 'strict-flag-session'}),
                ('transform', 'force', {})):
            with self.subTest(command=command):
                attempt = child_attempt_id(self.context.run_id, self.context.command,
                    self.context.attempt_id, 'typed-' + command, command)
                input_ref = None if command == 'discover' else 'worksets/sec/snapshot/sha256=' + 'a' * 64 + '/workset.json'
                from sec_edgar_ingest.download import FixturePack
                fixture_sha256 = FixturePack.load(self.pack).manifest_sha256 if command == 'discover' else None
                call = make_call(self.context, command, attempt, input_ref, fixture_sha256,
                    workflow_command=self.context.command, workflow_attempt_id=self.context.attempt_id,
                    step_id='typed-' + command, **kwargs)
                for number in (0, 1):
                    changed = parse_json(canonical_json(to_mapping_value(call)))
                    changed['intent'][field] = number
                    with self.assertRaises((Conflict, ValueError)):
                        call_ref(changed)

    def test_daily_discovery_collection_keeps_origin_priority_in_checked_context(self):
        parent = replace(self.context, command='daily', priority='daily')
        dispatcher = Dispatcher(parent, self.settings, self.pack, self.root, self.store, self.objects)
        found = dispatcher.execute('discover', 'daily-discover', self.settings,
            ('--mode', 'daily', '--discovery-id', 'checked-daily-discovery'))
        collected = dispatcher.execute('collect', 'daily-collect', self.settings,
            ('--workset', found.result.source_workset_ref))
        self.assertEqual(found.result.context.priority, 'daily')
        self.assertEqual(collected.result.context.priority, 'daily')
        self.assertEqual(collected.call['context']['priority'], 'daily')
        self.assertEqual(read_child(collected.call, self.store, self.objects), collected.result)
        transformed = dispatcher.execute('transform', 'daily-transform', self.settings,
            ('--workset', collected.result.snapshot_workset_ref))
        published = dispatcher.execute('publish', 'daily-publish', self.settings,
            ('--workset', transformed.result.transformed_workset_ref))
        self.assertEqual(transformed.result.context.priority, 'backfill')
        self.assertEqual(published.result.context.priority, 'backfill')
        self.assertEqual(published.result.outcome, 'success')

    def test_real_input_chain_and_retained_retry_prefix(self):
        self.store.close()
        self.settings, self.context, self.pack, self.store, self.objects = workflow_fixture(
            self.root, prefix=True)
        self.dispatcher = Dispatcher(self.context, self.settings, self.pack, self.root,
                                     self.store, self.objects)
        found, collected, transformed, published = dispatch_chain(self.dispatcher, self.settings)
        self.assertEqual(collected.result.outcome, 'success')
        self.assertEqual(collected.result.quarantined, 1)
        self.assertEqual(transformed.result.quarantined, 0)
        self.assertEqual(published.result.outcome, 'success')
        acquisition = AcquisitionState(self.store)
        source = next(iter(self.store.scan('Source', {}))).value['source']
        history = acquisition.request_history(collected.result.context, source['canonical_url'])
        self.assertEqual(len(history), 2)
        first = history[0].value
        base = (f'quarantine/sec/{self.context.run_id}/{source["source_id"]}/'
                f'{collected.result.context.attempt_id}/{first["request_id"]}')
        self.assertEqual(self.objects.read(base + '/body'), b'retained retry prefix')
        self.assertEqual(parse_json(self.objects.read(base + '/receipt.json'))['error']['code'], 'read_timeout')
        for child in (found, collected, transformed, published):
            self.assertEqual(read_child(child.call, self.store, self.objects), child.result)
        capture = capture_quarter('2026Q4', self.objects, EtlState(self.store))
        self.assertEqual(len(list(read_quarter(capture, self.objects))), 1)

    def test_parent_command_namespace_and_exact_replay(self):
        backfill = self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-backfill'))
        daily_context = replace(self.context, command='daily', priority='daily')
        daily_dispatcher = Dispatcher(daily_context, self.settings, self.pack, self.root,
                                      self.store, self.objects)
        daily = daily_dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'daily', '--discovery-id', 'checked-daily'))
        self.assertNotEqual(backfill.result_ref, daily.result_ref)
        before = cursor_values(self.store)
        self.assertEqual(self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-backfill')).result, backfill.result)
        self.assertEqual(daily_dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'daily', '--discovery-id', 'checked-daily')).result, daily.result)
        self.assertEqual(cursor_values(self.store), before)
        self.assertNotEqual(child_attempt_id(self.context.run_id, 'backfill', self.context.attempt_id,
            'discover', 'discover'), child_attempt_id(self.context.run_id, 'daily',
            self.context.attempt_id, 'discover', 'discover'))

    def test_changed_flags_or_canonical_call_refuse(self):
        child = self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        before = cursor_values(self.store)
        with self.assertRaises(Conflict):
            self.dispatcher.execute('discover', 'discover', self.settings,
                ('--mode', 'quarterly', '--discovery-id', 'changed-discovery'))
        altered = dict(child.call)
        altered['step_id'] = 'different-step'
        with self.assertRaises((Conflict, ValueError)):
            read_child(altered, self.store, self.objects)
        target = self.root / '.fixture-state/objects' / call_ref(child.call)
        target.write_bytes(target.read_bytes() + b' ')
        with self.assertRaises(Conflict):
            read_child(child.call, self.store, self.objects)
        self.assertEqual(cursor_values(self.store), before)

    def test_call_is_durable_before_dispatch_and_reopen_uses_it(self):
        faults = Faults()
        def crash():
            raise CollectionCrash()
        faults.at('workflow_child.after_call', crash)
        stopped = Dispatcher(self.context, self.settings, self.pack, self.root,
                             self.store, self.objects, observer=faults)
        before = cursor_values(self.store)
        with self.assertRaises(CollectionCrash):
            stopped.execute('discover', 'discover', self.settings,
                ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        self.assertEqual(cursor_values(self.store), before)
        self.assertEqual(len(list(self.store.scan('WorkflowChildCall', {}))), 1)
        child = self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        self.assertEqual(child.result.outcome, 'success')

    def test_post_cas_repair_keeps_child_unfinished_until_checked_retry(self):
        found = self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        collected = self.dispatcher.execute('collect', 'collect-one', self.settings,
            ('--workset', found.result.source_workset_ref))
        transformed = self.dispatcher.execute('transform', 'transform-one', self.settings,
            ('--workset', collected.result.snapshot_workset_ref))
        original = EtlState.record_publication
        failures = []
        def fail_once(state, manifest):
            if not failures:
                failures.append(True)
                raise OSError('ordinary ancillary failure after CAS')
            return original(state, manifest)
        with patch.object(EtlState, 'record_publication', fail_once):
            with self.assertRaises(ChildUnfinished) as raised:
                self.dispatcher.execute('publish', 'publish-one', self.settings,
                    ('--workset', transformed.result.transformed_workset_ref))
        error = raised.exception
        self.assertTrue(error.repair_pending)
        with self.assertRaises(FileNotFoundError):
            read_child(error.call, self.store, self.objects)
        pointers = [row.to_mapping() for row in self.store.scan('QuarterPublication', {})]
        child = self.dispatcher.execute('publish', 'publish-one', self.settings,
            ('--workset', transformed.result.transformed_workset_ref))
        self.assertEqual(child.result.outcome, 'unchanged')
        self.assertEqual([row.to_mapping() for row in self.store.scan('QuarterPublication', {})], pointers)
        self.assertEqual(len(list(self.store.scan('PublicationReceipt', {}))), 1)

    def test_input_binding_and_raw_tamper_are_refused(self):
        _, collected, transformed, published = dispatch_chain(self.dispatcher, self.settings)
        source_rows = list(self.store.scan('Binding', {}))
        binding = source_rows[0]
        value = binding.to_mapping()['value']
        value['snapshot_sha256'] = 'f' * 64
        binding_key = value['source_workset_id'] + ':' + value['source_id']
        self.store.replace('Binding', binding_key, value, binding.version)
        with self.assertRaises((Conflict, ValueError)):
            read_child(transformed.call, self.store, self.objects)
        self.store.replace('Binding', binding_key, binding.to_mapping()['value'],
                           self.store.get('Binding', binding_key).version)
        raw = next(iter(self.store.scan('Snapshot', {}))).value['raw_path']
        (self.root / '.fixture-state/objects' / raw).write_bytes(b'corrupt retained raw')
        with self.assertRaises((Conflict, ValueError)):
            read_child(published.call, self.store, self.objects)

    def test_changed_context_and_flags_refuse_before_new_transport(self):
        self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        before = cursor_values(self.store)
        changed_settings_value = self.settings.to_mapping()
        changed_settings_value['etl']['parser_version'] = 'fixture-index-parser-v2'
        changed_settings = Settings.from_mapping(changed_settings_value)
        variants = (
            (self.settings, replace(self.context, execution_id='different-execution')),
            (self.settings, replace(self.context, deadline=self.context.deadline.replace(year=2027))),
            (changed_settings, replace(self.context, parser_version=changed_settings.etl.parser_version,
                config_sha256=changed_settings.config_sha256, effective_config={}, pinned_on=None)),
        )
        for settings, context in variants:
            context = pin_context(settings, context, self.context.pinned_on)[0]
            different = Dispatcher(context, settings, self.pack, self.root, self.store, self.objects)
            with self.assertRaises(Conflict):
                different.execute('discover', 'discover', settings,
                    ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        for flags in (
            ('--mode', 'quarterly', '--discovery-id', 'x', '--force'),
            ('--mode', 'quarterly', '--mode', 'daily', '--discovery-id', 'x'),
            ('--mode', 'quarterly', '--discovery-id', '../escape'),
        ):
            with self.assertRaises(ValueError):
                self.dispatcher.execute('discover', 'invalid-flags', self.settings, flags)
        self.assertEqual(cursor_values(self.store), before)

    def test_origin_collection_and_current_parser_are_separate_exact_contexts(self):
        found = self.dispatcher.execute('discover', 'discover', self.settings,
            ('--mode', 'quarterly', '--discovery-id', 'checked-discovery'))
        original = self.dispatcher.execute('collect', 'collect-one', self.settings,
            ('--workset', found.result.source_workset_ref))
        value = self.settings.to_mapping()
        value['etl']['parser_version'] = 'fixture-index-parser-v2'
        current = Settings.from_mapping(value)
        context = replace(self.context, attempt_id='new-parser-attempt',
            parser_version=current.etl.parser_version, config_sha256=current.config_sha256,
            effective_config={}, pinned_on=None)
        context = pin_context(current, context, self.context.pinned_on)[0]
        dispatcher = Dispatcher(context, current, self.pack, self.root, self.store, self.objects)
        reused = dispatcher.execute('collect', 'collect-origin', self.settings,
            ('--workset', found.result.source_workset_ref))
        self.assertEqual(reused.result.context.parser_version, 'fixture-index-parser-v1')
        self.assertEqual(reused.result.snapshot_workset_ref, original.result.snapshot_workset_ref)
        transformed = dispatcher.execute('transform', 'transform-current', current,
            ('--workset', reused.result.snapshot_workset_ref))
        published = dispatcher.execute('publish', 'publish-current', current,
            ('--workset', transformed.result.transformed_workset_ref))
        self.assertEqual(transformed.result.context.parser_version, 'fixture-index-parser-v2')
        self.assertEqual(published.result.context.parser_version, 'fixture-index-parser-v2')

    def test_historical_capture_survives_missing_mutable_child_indexes(self):
        from sec_edgar_ingest.workflows.checked import read_child_capture
        _, _, _, published = dispatch_chain(self.dispatcher, self.settings)
        class NoState:
            def get(self, kind, key):
                raise AssertionError('historical capture consulted current state')
        self.assertEqual(read_child_capture(published.call, self.objects), published.result)
        # Current completion and dispatch still require exact repaired mutable readback.
        with self.assertRaises(AssertionError):
            read_child(published.call, NoState(), self.objects)
```

- [ ] **Step 2: Run the targeted red command in the authorized execution session.**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_checked.py -v
```

Expected initially: import failure for `workflows.checked`; after implementation every named case must pass using real store/readback. Retain complete command/stdout/stderr/exit evidence, not only a summary.

- [ ] **Step 3: Implement the complete checked boundary.**

Create `workflows/checked.py` with this code. Keep the production CLI import inside `execute` so later workflow CLI composition does not create an import cycle.

```python
from __future__ import annotations

import argparse
import hashlib
import io
import re
from collections.abc import Mapping
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypedDict

from ..config import Settings, pin_context
from ..download import FixturePack
from ..models import CommandResult, Error, RunContext, canonical_json, parse_json, require_hash, safe_relative_path, to_mapping_value
from ..results import exit_code, read_result, result_path
from ..state import AcquisitionState, attempt_key
from ..storage.contracts import AlreadyExists, BoundaryObserver, Conflict, ObjectStore, StateStore, observe
from ..storage.contracts import deployment_binding
from ..worksets import decode_source_workset, decode_snapshot_workset, encode_workset, make_snapshot_workset
from ..etl.commands import read_etl_result, validate_workset_ref
from ..etl.contracts import Candidate, EtlResult, GenerationCapture, decode_transformed, transformed_ref, processing_key
from ..etl.manifest import validate_candidate, read_manifest
from ..etl.reader import validated_manifest
from ..etl.transform import _pinned_members, _read_manifest, read_observations
from ..etl.parser import supported_parser
from ..models import Record, validate_record_fields


@dataclass(frozen=True, slots=True)
class CheckedChild(Record):
    call: Mapping[str, object]
    result_ref: str
    result: CommandResult | EtlResult

    def __post_init__(self):
        validate_record_fields(self)
        safe_relative_path(self.result_ref, "checked result reference")
        if self.call.get("result_ref") != self.result_ref or result_path(self.result.context) != self.result_ref:
            raise ValueError("checked child result reference differs from decoded context/call")


class ChildCall(TypedDict):
    format_version: str
    workflow_command: str
    workflow_attempt_id: str
    step_id: str
    context: dict[str, object]
    intent: dict[str, object]
    input_ref: str | None
    result_ref: str


CALL_FIELDS = frozenset(ChildCall.__annotations__)
CHILD_COMMANDS = ('discover', 'collect', 'transform', 'publish')


def _segment(value, label):
    if '/' in safe_relative_path(value, label):
        raise ValueError(label + ' must be one safe path segment')


def child_attempt_id(run_id, workflow_command, workflow_attempt_id, step_id, command):
    for name, value in (('run_id', run_id), ('workflow_command', workflow_command),
                        ('workflow_attempt_id', workflow_attempt_id), ('step_id', step_id),
                        ('command', command)):
        _segment(value, name)
    if workflow_command not in ('backfill', 'daily') or command not in CHILD_COMMANDS:
        raise ValueError('unsupported workflow/child command')
    return 'wf-' + hashlib.sha256(canonical_json(
        to_mapping_value([run_id, workflow_command, workflow_attempt_id, step_id, command]))).hexdigest()[:40]


def make_call(context, command, attempt_id, input_ref, fixture_sha256=None, *,
              workflow_command, workflow_attempt_id, step_id, today=None,
              mode=None, discovery_id=None, refresh=False, force=False):
    expected = child_attempt_id(context.run_id, workflow_command, workflow_attempt_id, step_id, command)
    if attempt_id != expected or type(refresh) is not bool or type(force) is not bool:
        raise ValueError('child namespace or flag types differ')
    child = replace(context, command=command, attempt_id=attempt_id)
    settings = Settings.from_mapping(child.to_mapping()['effective_config'])
    if child.pinned_on is None or pin_context(settings, child, child.pinned_on)[0] != child:
        raise ValueError('child template requires exact pinned effective settings')
    if today is not None and (type(today) is not date or today != child.pinned_on):
        raise ValueError('child today differs from the pinned date')
    today_text = None if today is None else today.isoformat()
    if command == 'discover':
        if mode not in ('quarterly', 'daily') or discovery_id is None or input_ref is not None or force:
            raise ValueError('invalid discovery flags')
        _segment(discovery_id, 'discovery_id')
    elif mode is not None or discovery_id is not None or refresh:
        raise ValueError('non-discovery cannot carry discovery flags')
    if command == 'collect':
        if force or input_ref is None or not input_ref.startswith('worksets/sec/source/sha256='):
            raise ValueError('collection requires its exact source workset')
        if not re.fullmatch(r'worksets/sec/source/sha256=[0-9a-f]{64}/workset\.json', input_ref):
            raise ValueError('invalid source workset reference')
    if command in ('transform', 'publish'):
        validate_workset_ref(input_ref, 'snapshot' if command == 'transform' else 'transformed')
        if fixture_sha256 is not None or (command == 'publish' and force):
            raise ValueError('ETL cannot carry transport/force flags outside transform')
        intent = {'command': command, 'today': today_text, 'workset': input_ref,
                  'force': force if command == 'transform' else None}
    else:
        if settings.storage.backend == 'local-fixture':
            require_hash(fixture_sha256, 'fixture_sha256')
        elif fixture_sha256 is not None or today is not None:
            raise ValueError('Azure cannot carry fixture-only inputs')
        intent = {'command': command, 'today': today_text, 'fixture_sha256': fixture_sha256,
            'mode': mode if command == 'discover' else None,
            'discovery_id': discovery_id if command == 'discover' else None,
            'refresh': refresh if command == 'discover' else None,
            'workset': input_ref if command == 'collect' else None}
    if settings.storage.backend == 'azure' and today is not None:
        raise ValueError('Azure cannot carry date override')
    return {'format_version': 'sec-workflow-child-call-v1', 'workflow_command': workflow_command,
        'workflow_attempt_id': workflow_attempt_id, 'step_id': step_id,
        'context': child.to_mapping(), 'intent': intent, 'input_ref': input_ref,
        'result_ref': result_path(child)}


def _validated(call):
    if not isinstance(call, Mapping) or set(call) != CALL_FIELDS:
        raise Conflict('child call must have its exact versioned fields')
    value = parse_json(canonical_json(to_mapping_value(call)))
    context = RunContext.from_mapping(value['context'])
    intent = value['intent']
    if not isinstance(intent, dict):
        raise Conflict('child intent must be an exact mapping')
    family_flags = (('refresh', 'discover'),) if context.command in ('discover', 'collect') else (('force', 'transform'),)
    for field, applicable in family_flags:
        if field not in intent:
            raise Conflict('child intent lacks exact flag field')
        if context.command == applicable:
            if type(intent[field]) is not bool:
                raise Conflict('child flag must be an exact boolean')
        elif intent[field] is not None:
            raise Conflict('inapplicable child flag must be null')
    rebuilt = make_call(context, context.command, context.attempt_id, value['input_ref'],
        intent.get('fixture_sha256'), workflow_command=value['workflow_command'],
        workflow_attempt_id=value['workflow_attempt_id'], step_id=value['step_id'],
        today=date.fromisoformat(intent['today']) if intent.get('today') else None,
        mode=intent.get('mode'), discovery_id=intent.get('discovery_id'),
        refresh=intent['refresh'] if context.command == 'discover' else False,
        force=intent['force'] if context.command == 'transform' else False)
    if canonical_json(to_mapping_value(rebuilt)) != canonical_json(to_mapping_value(value)):
        raise Conflict('child call differs from its exact canonical identity/flags')
    return value, context


def call_ref(call):
    value, context = _validated(call)
    return (f'runs/sec/{context.run_id}/{value["workflow_command"]}/{value["workflow_attempt_id"]}'
            f'/children/{context.attempt_id}/call.json')


def call_key(call):
    value, context = _validated(call)
    return hashlib.sha256(canonical_json(to_mapping_value([context.run_id, value['workflow_command'],
        value['workflow_attempt_id'], context.attempt_id]))).hexdigest()


def _remember_call(call, store, objects):
    value, _ = _validated(call)
    body = canonical_json(to_mapping_value(value))
    objects.put_once(call_ref(value), body)
    objects.verify(call_ref(value), hashlib.sha256(body).hexdigest(), len(body))
    try:
        store.insert('WorkflowChildCall', call_key(value), value)
    except AlreadyExists:
        row = store.get('WorkflowChildCall', call_key(value))
        if row is None or canonical_json(to_mapping_value(row.to_mapping()['value'])) != body:
            raise Conflict('child call index differs from immutable authority')


def _authority(call, store, objects):
    value, context = _validated(call)
    if objects.read(call_ref(value)) != canonical_json(to_mapping_value(value)):
        raise Conflict('child call object differs from its canonical descriptor')
    row = store.get('WorkflowChildCall', call_key(value)) if store is not None else None
    if row is not None and canonical_json(to_mapping_value(row.to_mapping()['value'])) != canonical_json(to_mapping_value(value)):
        raise Conflict('child call index differs from its object')
    return value, context


def _context_matches(expected, actual):
    wanted = expected.to_mapping()
    wanted['started_at'] = actual.to_mapping()['started_at']
    if wanted != actual.to_mapping() or not expected.started_at <= actual.started_at < expected.deadline:
        raise Conflict('child result has changed identity/settings/date/deadline/start')
    settings = Settings.from_mapping(actual.to_mapping()['effective_config'])
    if pin_context(settings, actual, actual.pinned_on)[0] != actual:
        raise Conflict('saved child context cannot reproduce its pin')


def _source_input(path, objects):
    body = objects.read(path)
    workset = decode_source_workset(body)
    if path != f'worksets/sec/source/sha256={workset.workset_id}/workset.json' or encode_workset(workset) != body:
        raise Conflict('source input path/bytes disagree')
    return workset


def _snapshot_input(path, store, objects):
    body = objects.read(path)
    if store is not None:
        snapshots, members = _pinned_members(path, objects, AcquisitionState(store))
    else:
        snapshots = decode_snapshot_workset(body)
        if path != f'worksets/sec/snapshot/sha256={snapshots.workset_id}/workset.json':
            raise Conflict('snapshot input path differs from content identity')
        sources = _source_input(f'worksets/sec/source/sha256={snapshots.source_workset_id}/workset.json', objects)
        if make_snapshot_workset(sources, snapshots.snapshots) != snapshots:
            raise Conflict('snapshot input differs from original source membership/context')
        members = {source.source_id: source for source in sources.members}
    if encode_workset(snapshots) != body:
        raise Conflict('snapshot input must use canonical bytes')
    for snapshot in snapshots.snapshots:
        objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
    return snapshots, members


def _transformed_input(path, store, objects):
    workset = decode_transformed(objects.read(path))
    if transformed_ref(workset) != path:
        raise Conflict('transformed input address differs')
    snapshots, members = _snapshot_input(workset.snapshot_workset_ref, store, objects)
    if workset.origin_context != snapshots.context:
        raise Conflict('transformed origin context differs from its pinned snapshot workset')
    snapshots_by_id = {snapshot.source_id: snapshot for snapshot in snapshots.snapshots}
    covered = []
    for ref in workset.observations:
        if ref.source != members.get(ref.source.source_id) or ref.snapshot != snapshots_by_id.get(ref.source.source_id):
            raise Conflict('transformed observation differs from exact source/raw binding')
        retained, _ = _read_manifest(ref.manifest_ref, objects)
        if retained != ref:
            raise Conflict('transformed observation differs from retained manifest')
        for _ in read_observations(ref, objects):
            pass
        if store is not None:
            row = store.get('Processing', processing_key(ref.source.source_id, ref.snapshot.sha256,
                                                       ref.parser_version, ref.schema_version))
            if row is None or row.to_mapping()['value']['observation'] != ref.to_mapping():
                raise Conflict('Processing contents differ from exact observation/version identity')
        covered.append(ref.source.source_id)
    covered.extend(gap.source_id for gap in workset.failures)
    if len(covered) != len(set(covered)) or set(covered) != set(members):
        raise Conflict('transformed successes/failures must account for every pinned member')
    return workset


def _validate_input_output(call, result, store, objects):
    command = result.context.command
    if command == 'discover':
        if result.snapshot_workset_ref is not None or result.source_workset_ref is None:
            raise Conflict('discovery child lacks its source-only output')
        workset = _source_input(result.source_workset_ref, objects)
        if workset.discovery_id != call['intent']['discovery_id']:
            raise Conflict('discovery output differs from requested session')
        for field in ('run_id', 'command', 'config_sha256', 'image_digest', 'parser_version', 'schema_version', 'effective_config'):
            if getattr(workset.context, field) != getattr(result.context, field):
                raise Conflict('discovery output has changed frozen provenance')
    elif command == 'collect':
        source = _source_input(call['input_ref'], objects)
        if result.source_workset_ref != call['input_ref']:
            raise Conflict('collection result differs from exact requested source workset')
        for field in ('config_sha256', 'image_digest', 'parser_version', 'schema_version', 'effective_config'):
            if getattr(source.context, field) != getattr(result.context, field):
                raise Conflict('collection settings differ from origin acquisition context')
        if result.snapshot_workset_ref is not None:
            snapshots, _ = _snapshot_input(result.snapshot_workset_ref, store, objects)
            if snapshots.source_workset_id != source.workset_id:
                raise Conflict('collection snapshot output belongs to another source workset')
    elif command == 'transform':
        _snapshot_input(call['input_ref'], store, objects)
        if result.input_ref != call['input_ref'] or result.transformed_workset_ref is None:
            raise Conflict('transform result lacks its exact input/output chain')
        workset = _transformed_input(result.transformed_workset_ref, store, objects)
        if workset.snapshot_workset_ref != call['input_ref'] or workset.context != result.context or workset.failures != result.gaps:
            raise Conflict('transform result differs from durable transformed workset')
    else:
        workset = _transformed_input(call['input_ref'], store, objects)
        if result.input_ref != call['input_ref'] or result.transformed_workset_ref != call['input_ref']:
            raise Conflict('publication result differs from exact transformed input')
        if (workset.context.parser_version, workset.context.schema_version) != (
                result.context.parser_version, result.context.schema_version):
            raise Conflict('publication input versions differ')
        for quarter in result.quarters:
            if quarter.outcome in ('published', 'unchanged'):
                body = objects.read(quarter.manifest_ref)
                capture = GenerationCapture(quarter.quarter, quarter.generation_id, quarter.manifest_ref,
                                            hashlib.sha256(body).hexdigest(), len(body))
                manifest = validated_manifest(capture, objects)
                if (manifest.parser_version, manifest.schema_version) != (
                        result.context.parser_version, result.context.schema_version):
                    raise Conflict('publication manifest versions differ')
            elif quarter.outcome == 'awaiting_approval':
                payload = parse_json(objects.read(quarter.candidate_ref))
                manifest_ref = payload['manifest_ref']
                body = objects.read(manifest_ref)
                capture = GenerationCapture(payload['quarter'], payload['generation_id'], manifest_ref,
                                            hashlib.sha256(body).hexdigest(), len(body))
                candidate = Candidate(read_manifest(capture, objects), manifest_ref,
                    capture.manifest_sha256, capture.manifest_bytes, quarter.candidate_ref)
                if candidate.manifest.quarter != quarter.quarter:
                    raise Conflict('candidate belongs to another quarter')
                validate_candidate(candidate, objects)
                if store is not None:
                    row = store.get('Candidate', candidate.manifest.generation_id)
                    if row is None or row.to_mapping()['value'] != candidate.to_mapping():
                        raise Conflict('gate candidate index differs from immutable evidence')


def read_child_capture(call, objects):
    value, expected = _authority(call, None, objects)
    result = (read_etl_result if expected.command in ('transform', 'publish') else read_result)(
        value['result_ref'], objects)
    _context_matches(expected, result.context)
    intent_path = value['result_ref'].rsplit('/', 1)[0] + '/command.json'
    frozen = ({'context': result.context.to_mapping(), 'intent': value['intent']}
              if expected.command in ('transform', 'publish') else value['intent'])
    if objects.read(intent_path) != canonical_json(to_mapping_value(frozen)):
        raise Conflict('child frozen command differs from expected intent/context')
    _validate_input_output(value, result, None, objects)
    return result


def read_child(call, store, objects):
    value, expected = _authority(call, store, objects)
    result = read_child_capture(value, objects)
    row = store.get('Attempt', attempt_key(result.context))
    saved = row.to_mapping()['value'] if row is not None else None
    if saved is None or saved['context'] != result.context.to_mapping() or saved['result'] != result.to_mapping():
        raise Conflict('child result requires repaired exact Attempt readback')
    _validate_input_output(value, result, store, objects)
    return result


def unfinished_child(call, store):
    value, expected = _validated(call)
    matches = [row for row in store.scan('Attempt', {})
               if all(row.value['context'][field] == getattr(expected, field)
                      for field in ('run_id', 'command', 'attempt_id', 'execution_id', 'image_digest'))]
    if len(matches) != 1:
        raise Conflict('unfinished child lacks one exact begun Attempt')
    row = matches[0].to_mapping()['value']
    actual = RunContext.from_mapping(row['context'])
    _context_matches(expected, actual)
    if row['result'] is not None:
        raise Conflict('unfinished child index already contains a result')
    return actual, tuple(Error.from_mapping(error) for error in row.get('structured_errors', ()))


class ChildUnfinished(RuntimeError):
    def __init__(self, call, outcome, gaps, code, stdout, stderr):
        super().__init__('child has no repaired immutable result: ' + outcome)
        self.call, self.outcome, self.gaps = call, outcome, gaps
        self.exit, self.stdout, self.stderr = code, stdout, stderr
        self.repair_pending = any(gap.retryable and gap.details.get('type') == 'PublicationRepairPending'
                                  for gap in gaps)
        self.resumable = self.repair_pending or call['context']['command'] == 'publish'
        self.details = {'call': to_mapping_value(call), 'outcome': outcome, 'exit': code, 'stdout': stdout,
                        'stderr': stderr, 'gaps': [gap.to_mapping() for gap in gaps],
                        'repair_pending': self.repair_pending, 'resumable': self.resumable}


def _flags(command, flags):
    if any(not isinstance(flag, str) for flag in flags):
        raise ValueError('child flags must contain only text')
    parser = argparse.ArgumentParser(add_help=False, exit_on_error=False, allow_abbrev=False)
    if command == 'discover':
        parser.add_argument('--mode', required=True, choices=('quarterly', 'daily'))
        parser.add_argument('--discovery-id', required=True)
        parser.add_argument('--refresh', action='store_true')
    else:
        parser.add_argument('--workset', required=True)
        if command == 'transform':
            parser.add_argument('--force', action='store_true')
    try:
        parsed = parser.parse_args(flags)
    except (SystemExit, argparse.ArgumentError) as error:
        raise ValueError('invalid command-specific child flags') from error
    names = [flag for flag in flags if flag.startswith('--')]
    if len(names) != len(set(names)):
        raise ValueError('duplicate child flags')
    return vars(parsed)


class Dispatcher:
    def __init__(self, context, settings, fixture_pack, state_dir, store, objects, observer=None):
        if context.command not in ('backfill', 'daily') or context.pinned_on is None:
            raise ValueError('dispatcher requires a pinned workflow context')
        if pin_context(settings, context, context.pinned_on)[0] != context:
            raise ValueError('workflow context differs from current settings')
        if settings.storage.backend == 'local-fixture':
            if fixture_pack is None:
                raise ValueError('fixture workflow requires its explicit pack')
            self.pack = FixturePack.load(fixture_pack)
        else:
            if fixture_pack is not None or state_dir is not None:
                raise ValueError('fixture inputs are forbidden for Azure')
            self.pack = None
        self.context, self.settings, self.fixture_pack = context, settings, fixture_pack
        self.state_dir, self.store, self.objects, self.observer = state_dir, store, objects, observer

    def execute(self, command, step_id, settings, flags):
        from ..cli import main
        if command not in CHILD_COMMANDS or not isinstance(flags, tuple):
            raise ValueError('child command/flags require their closed interface')
        if deployment_binding(settings) != deployment_binding(self.settings):
            raise Conflict('origin child settings differ from the shared storage/issuer binding')
        parsed = _flags(command, flags)
        parent = self.context
        attempt = child_attempt_id(parent.run_id, parent.command, parent.attempt_id, step_id, command)
        child = replace(parent, command=command, attempt_id=attempt,
            image_digest=settings.worker.image_digest, parser_version=settings.etl.parser_version,
            schema_version=settings.etl.schema_version, config_sha256=settings.config_sha256,
            effective_config={}, pinned_on=None,
            priority='daily' if command == 'discover' and parsed['mode'] == 'daily' else 'backfill')
        if command == 'collect':
            child = replace(child, priority=_source_input(parsed['workset'], self.objects).context.priority)
        child = pin_context(settings, child, parent.pinned_on)[0]
        fixture = settings.storage.backend == 'local-fixture'
        today = parent.pinned_on if fixture and settings.fixture.allow_clock_override else None
        digest = self.pack.manifest_sha256 if command in ('discover', 'collect') and self.pack else None
        call = make_call(child, command, attempt, parsed.get('workset'), digest,
            workflow_command=parent.command, workflow_attempt_id=parent.attempt_id, step_id=step_id,
            today=today, mode=parsed.get('mode'), discovery_id=parsed.get('discovery_id'),
            refresh=parsed.get('refresh', False), force=parsed.get('force', False))
        if command == 'collect':
            source = _source_input(call['input_ref'], self.objects)
            for field in ('config_sha256', 'image_digest', 'parser_version', 'schema_version', 'effective_config'):
                if getattr(source.context, field) != getattr(child, field):
                    raise Conflict('collection dispatch differs from origin settings/versions')
        elif command in ('transform', 'publish'):
            supported_parser(child.parser_version, fixture=fixture)
            if command == 'transform':
                _snapshot_input(call['input_ref'], self.store, self.objects)
            else:
                transformed = _transformed_input(call['input_ref'], self.store, self.objects)
                if (transformed.context.parser_version, transformed.context.schema_version) != (
                        child.parser_version, child.schema_version):
                    raise Conflict('publication dispatch differs from transformed input versions')
        if self.fixture_pack is not None and FixturePack.load(self.fixture_pack).manifest_sha256 != self.pack.manifest_sha256:
            raise Conflict('fixture manifest changed after dispatcher construction')
        _remember_call(call, self.store, self.objects)
        observe(self.observer, 'workflow_child.after_call')
        with TemporaryDirectory(prefix='sec-workflow-child-') as directory:
            config = Path(directory) / 'config.json'
            config.write_bytes(canonical_json(to_mapping_value(settings.to_mapping())))
            argv = [command, '--config', str(config), '--run-id', parent.run_id,
                '--execution-id', parent.execution_id, '--attempt-id', attempt,
                '--deadline', parent.deadline.isoformat(), *flags]
            if self.state_dir is not None:
                argv.extend(('--state-dir', str(self.state_dir)))
            if today is not None:
                argv.extend(('--today', today.isoformat()))
            if command in ('discover', 'collect') and self.fixture_pack is not None:
                argv.extend(('--fixture-pack', str(self.fixture_pack)))
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(argv)
        try:
            result = read_child(call, self.store, self.objects)
        except FileNotFoundError:
            _, gaps = unfinished_child(call, self.store)
            outcome = next((gap.code for gap in gaps), 'internal_error')
            if exit_code(outcome) != code:
                raise Conflict('unfinished retained error differs from child exit')
            raise ChildUnfinished(call, outcome, gaps, code, stdout.getvalue(), stderr.getvalue())
        if exit_code(result.outcome) != code:
            raise Conflict('durable child result differs from child exit')
        try:
            printed = parse_json(stdout.getvalue())
        except ValueError as error:
            raise Conflict('child stdout lacks its exact result descriptor') from error
        if printed.get('outcome') != result.outcome or printed.get('result_ref') != call['result_ref']:
            raise Conflict('child stdout differs from independently read durable result')
        observe(self.observer, 'workflow_child.after_result')
        return CheckedChild(call, call['result_ref'], result)
```

Task 5 extends the same actual chain to fatal collection halt and terminal parser duplicate refusal; Task 6 exercises historical captures after pointer advancement; Task 10 supplies the workflow-level fixture/date/version/fixture hash corruption matrix. This task's supplied tests establish deterministic parent command namespaces, checked origin/current version separation, input/raw/binding refusals, strict flag/context identity, immutable before-dispatch call retention and the unfinished post-CAS command boundary before those consumers exist.

- [ ] **Step 4: Run the targeted green command and required regression subset.**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_checked.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_cli.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_etl_cli.py -v
git -c core.whitespace=cr-at-eol diff --check
```

Expected: all targeted tests pass; no network/auth/provider activity, no changed accepted limits/pins. Resolve scoped review before committing.

- [ ] **Step 5: Commit only the owned files.**

```bash
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/checked.py packages/sec-edgar-ingest/tests/support_checked.py packages/sec-edgar-ingest/tests/test_workflow_checked.py
git commit -m "feat: check workflow child identities and durable evidence"
```

### Task 4: Current completion, immutable historical captures and repair obligations

**Interfaces:** `evaluate_member(value,parser_version,schema_version,store,objects)->CompletionEvaluation`; `capture_member_provenance(value,store,objects)->Mapping`; `validate_member_provenance(evidence,objects)->SourceWorkset`; `capture_parent_provenance(parent_ref,store,objects)->Mapping`; `validate_parent_provenance(evidence,objects)->SourceWorkset`; `validate_discovery_session(session)->RunContext`; `validate_capture(capture,objects)->None`; `outstanding_repairs(value,store,objects)->tuple[Mapping,...]`; `resolve_repair(obligation,successful_publish_call,store,objects)->Mapping`; `validate_resolution_capture(resolution,objects)->None`. Current evaluation consumes Tasks 1–3; historical validation consumes original immutable objects only.

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/completion.py`; create `packages/sec-edgar-ingest/tests/test_workflow_completion.py`; extend test-owned `support_workflow_evidence.py` with the full fixture below. T4 does not execute children or select mutable latest snapshots.

The capture format is `sec-workflow-completion-v1`. Its discovery field is exact `{session, progress, recovery}`. Normal parents use `recovery=None`; recovered parents retain the T2 validated `WorkflowParentRecovery` descriptor (`{ref,sha256,bytes}`), keyed by parent workset ID in SourceState and pointing at `worksets/sec/workflow-parent-recovery/sha256=<sha>/recovery.json`. Historical validation delegates recovered ledger verification to the earlier T2 pure validator, including explicit unsuccessful units; it never relabels incomplete discovery or rewrites the original session. It freezes registry value, canonical parent/projection worksets, the actual discovery-session snapshot and required-unit DirectoryProgress records, exact Binding and Snapshot, fully read-back ObservationRef, full affected-quarter set and hash/length-bound GenerationCaptures. Historical validation reopens immutable bytes and captured discovery receipts without consulting current pointers or current Processing indexes. Current evaluation additionally checks the decoded live Processing identity and all active source membership under the publisher's affected-quarter rules.

Repair obligations are immutable objects plus recoverable SourceState indexes. Their identities include the exact T3 call and full affected-quarter set; the original child Attempt is evidence, not their resolution authority. A resolution links one obligation to a successful checked publish call and captures the exact PublicationReceipt/Processing memberships produced by the existing publisher. The resolution object's existence is checked against its contents and repair artifacts, never accepted as a boolean. The workflow's success receipt may retain these resolution descriptors for historical validation.

- [ ] **Step 1: Add meaningful red tests using the fixture and test code below.**

Test fixture file (complete code, depends only on T1-T3 and shipped builders):

```python
from sec_edgar_ingest.models import to_mapping_value
# tests/support_workflow_evidence.py
import contextlib
import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from support import discovery_harness, fixture_snapshot, listing_response
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.config import Settings, pin_context
from sec_edgar_ingest.etl.commands import read_etl_result
from sec_edgar_ingest.models import Binding, RunContext, canonical_json
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.worksets import encode_workset, make_snapshot_workset
from sec_edgar_ingest.workflows.provenance import project_member


def quarterly_bytes(day, name='A'):
    body = ('CIK|Company Name|Form Type|Date Filed|Filename\r\n-----\r\n'
            f'123456|{name}|10-K|{day}|edgar/data/123456/a.txt\r\n').encode()
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w') as archive:
        info = zipfile.ZipInfo('master.idx', (2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, body)
    return target.getvalue()


class EvidenceFixture:
    def __init__(self, root, command='daily'):
        self.root = Path(root)
        self.h = discovery_harness(self.root, {
            '2026Q3': [listing_response('2026Q3', ['master.zip'], family='full-index'),
                       listing_response('2026Q3', ['master.zip'], family='full-index')],
        })
        self.h.settings = Settings.from_mapping({
            **self.h.settings.to_mapping(),
            'backfill': {'start_quarter': '2026Q3', 'end_quarter': 'open'},
        })
        self.h.coordinator.settings = self.h.settings
        self.h.client.settings = self.h.settings
        parent = self.h.run('quarterly', date(2026, 10, 6), 'completion-old')
        self.parent_ref = self.h.workset_path(parent)
        self.source = next(s for s in parent.members if s.period == '2026Q3')
        self.value = project_member(self.parent_ref, self.source.source_id,
                                    self.h.store, self.h.objects)
        self.store, self.objects = self.h.store, self.h.objects
        self.sequence = 0
        self.calls = []
        self.settings = Settings.from_mapping({**self.h.settings.to_mapping(),
            'etl': {**self.h.settings.to_mapping()['etl'],
                    'parser_version': 'fixture-index-parser-v1'}})
        self.config = self.root / 'etl-config.json'
        self.config.write_bytes(canonical_json(to_mapping_value(self.settings.to_mapping())))
        now = datetime.now(timezone.utc)
        origin = parent.context
        self.workflow = pin_context(self.settings, replace(
            origin, run_id='completion-workflow', execution_id='completion-execution',
            parser_version=self.settings.etl.parser_version,
            schema_version=self.settings.etl.schema_version,
            config_sha256=self.settings.config_sha256,
            command=command, attempt_id='workflow-a', started_at=now,
            deadline=now + timedelta(seconds=3600), effective_config={}, pinned_on=None,
        ), date(2026, 10, 6))[0]
        bodies = self.root.parent / 'listing-bodies'
        bodies.mkdir(exist_ok=True)
        responses = {}
        for directory in parent.directories:
            progress = self.h.state.directory_progress(parent.discovery_id, directory.url).to_mapping()['value']
            body = self.objects.read(progress['evidence']['body_path'])
            digest = hashlib.sha256(body).hexdigest()
            (bodies / (digest + '.body')).write_bytes(body)
            spec = {'status': 200, 'headers': {'Content-Length': str(len(body))},
                    'body_path': 'listing-bodies/' + digest + '.body', 'body_sha256': digest}
            responses[directory.url] = [spec for _ in range(4)]
        raw = quarterly_bytes('2026-07-01')
        raw_digest = hashlib.sha256(raw).hexdigest()
        (bodies / (raw_digest + '.body')).write_bytes(raw)
        responses[self.source.canonical_url] = [
            {'status': 200, 'headers': {'Content-Length': str(len(raw))},
             'body_path': 'listing-bodies/' + raw_digest + '.body', 'body_sha256': raw_digest}
            for _ in range(4)]
        self.pack = self.root.parent / 'listing-manifest.json'
        self.pack.write_bytes(canonical_json(to_mapping_value({'fixture_version': 'sec-acquisition-fixture-v1',
                            'provenance': 'synthetic', 'responses': responses})))
        from sec_edgar_ingest.workflows.checked import Dispatcher
        dispatcher = Dispatcher(self.workflow, self.settings, self.pack,
                                self.root.parent, self.store, self.objects)
        found = dispatcher.execute('discover', 'initial-discovery', self.settings,
                                   ('--mode', 'quarterly', '--discovery-id', 'checked-completion-parent'))
        self.discovery_call = found.call
        self.parent_ref = found.result.source_workset_ref
        self.value = project_member(self.parent_ref, self.source.source_id,
                                    self.store, self.objects)

    def close(self):
        self.h.close()

    def revised_member(self):
        parent = self.h.run('quarterly', date(2026, 10, 6), 'completion-new', refresh=True)
        value = project_member(self.h.workset_path(parent), self.source.source_id,
                               self.store, self.objects)
        self.value = value
        return value

    def snapshot_input(self, body, seconds=0):
        from sec_edgar_ingest.workflows.provenance import read_member
        source_set = read_member(self.value, self.store, self.objects)
        snap = fixture_snapshot(self.source, body)
        snap = replace(snap, received_at=snap.received_at + timedelta(seconds=seconds))
        self.objects.put_once(snap.raw_path, body)
        acquisition = AcquisitionState(self.store)
        acquisition.remember_snapshot(snap)
        winner = acquisition.bind_once(Binding(source_set.workset_id,
                                                self.source.source_id, snap.sha256))
        if winner.snapshot_sha256 != snap.sha256:
            raise AssertionError('fixture attempted to overwrite an existing pin')
        snapshot_set = make_snapshot_workset(source_set, (snap,))
        ref = f'worksets/sec/snapshot/sha256={snapshot_set.workset_id}/workset.json'
        self.objects.put_once(ref, encode_workset(snapshot_set))
        return ref

    def invoke(self, command, input_ref, *, deadline=None):
        from sec_edgar_ingest.workflows.checked import Dispatcher, ChildUnfinished
        self.sequence += 1
        workflow = self.workflow if deadline is None else replace(self.workflow, deadline=deadline)
        dispatcher = Dispatcher(workflow, self.settings, self.pack,
                                self.root.parent, self.store, self.objects)
        with contextlib.ExitStack() as guards:
            if command in ('transform', 'publish'):
                guards.enter_context(patch('sec_edgar_ingest.cli.Coordinator', side_effect=AssertionError('ETL acquisition')))
                guards.enter_context(patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('ETL sender')))
            try:
                child = dispatcher.execute(command, f'{command}-{self.sequence}', self.settings,
                                           ('--workset', input_ref))
            except ChildUnfinished as error:
                self.calls.append(error.call)
                return error.exit, error.call, None
        self.calls.append(child.call)
        from sec_edgar_ingest.results import exit_code
        return exit_code(child.result.outcome), child.call, child.result

```


Tests:

```python
from sec_edgar_ingest.models import to_mapping_value
# tests/test_workflow_completion.py
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from support_workflow_evidence import EvidenceFixture, quarterly_bytes
from sec_edgar_ingest.etl.contracts import decode_transformed
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.workflows.completion import (
    evaluate_member, resolve_repair, validate_capture, validate_resolution,
)


class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = EvidenceFixture(Path(self.temp.name) / '.fixture-state')
        self.addCleanup(self.f.close)
        self.parser = self.f.workflow.parser_version
        self.schema = self.f.workflow.schema_version

    def evaluate(self):
        return evaluate_member(self.f.value, self.parser, self.schema,
                               self.f.store, self.f.objects)

    def transform(self, body, seconds=0):
        code, call, result = self.f.invoke('transform', self.f.snapshot_input(body, seconds))
        self.assertEqual(code, 0)
        return result.transformed_workset_ref

    def test_formerly_affected_quarter_stays_unresolved(self):
        original = self.transform(quarterly_bytes('2026-07-01'))
        self.assertEqual(self.f.invoke('publish', original)[0], 0)
        state = EtlState(self.f.store)
        q3 = state.pointer('2026Q3')
        self.assertTrue(self.evaluate().complete)
        self.f.revised_member()
        replacement = self.transform(quarterly_bytes('2026-10-01'), seconds=1)
        code, call, result = self.f.invoke('publish', replacement)
        self.assertEqual(code, 7)
        self.assertEqual({q.quarter: q.outcome for q in result.quarters},
                         {'2026Q3': 'invalid_source', '2026Q4': 'published'})
        new = decode_transformed(self.f.objects.read(replacement)).observations[0]
        self.assertEqual(dict(new.quarter_counts), {'2026Q4': 1})
        self.assertFalse(self.evaluate().complete)
        self.assertEqual(state.pointer('2026Q3'), q3)
        self.assertEqual(len(list(read_quarter(capture_quarter('2026Q4', self.f.objects, state),
                                               self.f.objects))), 1)
        self.assertEqual(len(list(read_quarter(capture_quarter('2026Q3', self.f.objects, state),
                                               self.f.objects))), 1)

    def test_current_index_identity_is_decoded_not_assumed(self):
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        self.f.invoke('publish', transformed)
        row = next(self.f.store.scan('Processing', {}))
        value = row.to_mapping()['value']
        value['observation']['parser_version'] = 'fixture-index-parser-v2'
        self.f.store.replace('Processing', value['processing_key'], value, row.version)
        evaluation = self.evaluate()
        self.assertFalse(evaluation.complete)
        self.assertTrue(evaluation.gaps)

    def test_historical_capture_survives_pointer_advance(self):
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        self.f.invoke('publish', transformed)
        captured = self.evaluate().capture
        self.f.revised_member()
        changed = self.transform(quarterly_bytes('2026-07-01', 'Changed'), seconds=1)
        self.f.invoke('publish', changed)
        validate_capture(captured, self.f.objects)
        self.assertNotEqual(captured['quarters'][0]['generation_id'],
                            EtlState(self.f.store).pointer('2026Q3').value['generation_id'])

    def test_fresh_attempt_resolves_repair_without_rewriting_original_attempt(self):
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        original = EtlState._record_membership
        fired = []
        def fail_once(state, *args):
            if not fired:
                fired.append(True)
                raise Conflict('retained ordinary ancillary failure')
            return original(state, *args)
        with patch.object(EtlState, '_record_membership', fail_once):
            code, failed_call, result = self.f.invoke('publish', transformed)
        self.assertEqual(code, 9)
        self.assertIsNone(result)
        evaluation = self.evaluate()
        self.assertFalse(evaluation.complete)
        self.assertEqual(len(evaluation.obligations), 1)
        old_attempt = [r.to_mapping() for r in self.f.store.scan('Attempt', {})
                       if r.value['context']['attempt_id'] == failed_call['context']['attempt_id']]
        pointers = [r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})]
        self.f.workflow = __import__('dataclasses').replace(self.f.workflow, attempt_id='fresh-workflow')
        code, fresh_call, result = self.f.invoke('publish', transformed)
        self.assertEqual(code, 0)
        self.assertEqual(result.quarters[0].outcome, 'unchanged')
        resolution = resolve_repair(evaluation.obligations[0], fresh_call,
                                    self.f.store, self.f.objects)
        validate_resolution(resolution, self.f.store, self.f.objects)
        self.assertTrue(self.evaluate().complete)
        self.assertEqual([r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})], pointers)
        self.assertEqual([r.to_mapping() for r in self.f.store.scan('Attempt', {})
                          if r.value['context']['attempt_id'] == failed_call['context']['attempt_id']], old_attempt)

    def test_missing_result_after_deadline_requires_fresh_attempt(self):
        from dataclasses import replace
        from sec_edgar_ingest.state import attempt_key
        from sec_edgar_ingest.models import RunContext
        from sec_edgar_ingest.workflows.checked import Dispatcher
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        with patch.object(EtlState, '_record_membership', side_effect=Conflict('ancillary')):
            code, call, result = self.f.invoke('publish', transformed)
        obligation = self.evaluate().obligations[0]
        self.assertEqual(code, 9)
        actual_key = attempt_key(RunContext.from_mapping(call['context']))
        old_attempt = self.f.store.get('Attempt', actual_key).to_mapping()
        command_ref = call['result_ref'].rsplit('/', 1)[0] + '/command.json'
        command_body = self.f.objects.read(command_ref)
        clock = self.f.workflow.deadline + timedelta(seconds=1)
        dispatcher = Dispatcher(self.f.workflow, self.f.settings, self.f.pack,
                                self.f.root.parent, self.f.store, self.f.objects)
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=clock), self.assertRaises(Conflict):
            dispatcher.execute('publish', call['step_id'], self.f.settings,
                               ('--workset', transformed))
        self.assertEqual(self.f.store.get('Attempt', actual_key).to_mapping(), old_attempt)
        self.assertEqual(self.f.objects.read(command_ref), command_body)
        self.assertFalse(self.evaluate().complete)
        self.f.workflow = replace(self.f.workflow, attempt_id='fresh-after-expiry',
                                  started_at=clock, deadline=clock + timedelta(seconds=3600))
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=clock):
            code, fresh_call, result = self.f.invoke('publish', transformed)
        self.assertEqual(code, 0)
        resolve_repair(obligation, fresh_call, self.f.store, self.f.objects)
        self.assertTrue(self.evaluate().complete)
        self.assertEqual(self.f.store.get('Attempt', actual_key).to_mapping(), old_attempt)

    def test_ordinary_public_publish_failure_is_pending_in_fresh_workflow(self):
        import contextlib
        import io
        from dataclasses import replace
        from sec_edgar_ingest.cli import main
        from sec_edgar_ingest.models import RunContext, parse_json
        from sec_edgar_ingest.state import attempt_key
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        original_method = EtlState._record_membership
        failures = []
        def fail_once(state, *args):
            if not failures:
                failures.append(True)
                raise Conflict('ordinary legacy ancillary repair failure')
            return original_method(state, *args)
        stdout = io.StringIO()
        arguments = ['publish', '--config', str(self.f.config),
            '--run-id', 'ordinary-legacy-run', '--execution-id', 'ordinary-legacy-execution',
            '--attempt-id', 'ordinary-legacy-publish',
            '--deadline', self.f.workflow.deadline.isoformat(),
            '--state-dir', str(self.f.root.parent), '--today', '2026-10-06',
            '--workset', transformed]
        with patch.object(EtlState, '_record_membership', fail_once), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = main(arguments)
        self.assertEqual(code, 9)
        legacy_rows = [r for r in self.f.store.scan('Attempt', {})
                       if r.value['context']['run_id'] == 'ordinary-legacy-run']
        self.assertEqual(len(legacy_rows), 1)
        original_row = legacy_rows[0].to_mapping()
        context = RunContext.from_mapping(original_row['value']['context'])
        self.assertIsNone(original_row['value']['result'])
        result_ref = f'runs/sec/{context.run_id}/publish/{context.attempt_id}/result.json'
        command_ref = result_ref.rsplit('/', 1)[0] + '/command.json'
        original_command = self.f.objects.read(command_ref)
        with self.assertRaises(FileNotFoundError):
            self.f.objects.read(result_ref)
        self.assertFalse(any(row.value['context']['run_id'] == 'ordinary-legacy-run'
                             for row in self.f.store.scan('WorkflowChildCall', {})))
        pointers = [r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})]
        self.f.workflow = replace(self.f.workflow, run_id='fresh-workflow-after-legacy',
                                  attempt_id='fresh-after-legacy', command='daily', priority='daily')
        evaluation = self.evaluate()
        self.assertFalse(evaluation.complete)
        self.assertEqual(len(evaluation.obligations), 1)
        payload = parse_json(self.f.objects.read(evaluation.obligations[0]['ref']))
        self.assertEqual(payload['call']['format_version'], 'sec-workflow-legacy-publish-v1')
        self.assertEqual(payload['call']['context'], context.to_mapping())
        self.assertEqual(payload['call']['input_ref'], transformed)
        code, fresh_call, repaired = self.f.invoke('publish', transformed)
        self.assertEqual(code, 0)
        self.assertEqual(repaired.quarters[0].outcome, 'unchanged')
        resolution = resolve_repair(evaluation.obligations[0], fresh_call,
                                    self.f.store, self.f.objects)
        validate_resolution(resolution, self.f.store, self.f.objects)
        self.assertTrue(self.evaluate().complete)
        self.assertEqual([r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})], pointers)
        self.assertEqual(self.f.store.get('Attempt', attempt_key(context)).to_mapping(), original_row)
        self.assertEqual(self.f.objects.read(command_ref), original_command)
        with self.assertRaises(FileNotFoundError):
            self.f.objects.read(result_ref)
        from sec_edgar_ingest.workflows.completion import validate_resolution_capture
        self.f.revised_member()
        newer = self.transform(quarterly_bytes('2026-07-01', 'Changed'), seconds=1)
        self.assertEqual(self.f.invoke('publish', newer)[0], 0)
        validate_resolution_capture(resolution, self.f.objects)
        advanced = [r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})]
        self.assertNotEqual(advanced, pointers)
        after_advance = self.evaluate()
        self.assertTrue(after_advance.complete)
        self.assertEqual(after_advance.obligations, ())
        self.assertEqual(self.f.store.get('Attempt', attempt_key(context)).to_mapping(), original_row)
        self.assertEqual(self.f.objects.read(command_ref), original_command)
    def test_copied_obligation_must_bind_original_command_and_exact_input(self):
        from copy import deepcopy
        import hashlib
        from sec_edgar_ingest.models import canonical_json, parse_json
        transformed = self.transform(quarterly_bytes('2026-07-01'))
        with patch.object(EtlState, '_record_membership', side_effect=Conflict('ancillary repair')):
            code, original_call, result = self.f.invoke('publish', transformed)
        self.assertEqual(code, 9)
        obligation = self.evaluate().obligations[0]
        original = parse_json(self.f.objects.read(obligation['ref']))
        self.f.workflow = __import__('dataclasses').replace(self.f.workflow,
                                                           attempt_id='fresh-tamper-proof')
        code, fresh_call, result = self.f.invoke('publish', transformed)
        self.assertEqual(code, 0)
        variants = []
        changed = deepcopy(original)
        changed['context']['execution_id'] = 'copied-foreign-execution'
        variants.append(changed)
        changed = deepcopy(original)
        changed['call']['workflow_attempt_id'] = 'copied-foreign-workflow'
        variants.append(changed)
        changed = deepcopy(original)
        changed['transformed_ref'] = 'worksets/sec/transformed/sha256=' + 'f' * 64 + '/workset.json'
        variants.append(changed)
        changed = deepcopy(original)
        changed['sources'] = []
        variants.append(changed)
        changed = deepcopy(original)
        changed['affected_quarters'] = []
        variants.append(changed)
        resolutions_before = [row.to_mapping() for row in self.f.store.scan('WorkflowRepairResolution', {})]
        for variant in variants:
            body = canonical_json(to_mapping_value(variant))
            digest = hashlib.sha256(body).hexdigest()
            path = f'worksets/sec/workflow-repairs/sha256={digest}/evidence.json'
            self.f.objects.put_once(path, body)
            descriptor = {'ref': path, 'sha256': digest, 'bytes': len(body),
                          'format_version': 'sec-workflow-repair-obligation-v1'}
            with self.subTest(variant=variant), self.assertRaises((Conflict, ValueError, FileNotFoundError)):
                resolve_repair(descriptor, fresh_call, self.f.store, self.f.objects)
        self.assertEqual([row.to_mapping() for row in self.f.store.scan('WorkflowRepairResolution', {})],
                         resolutions_before)
        resolution = resolve_repair(obligation, fresh_call, self.f.store, self.f.objects)
        validate_resolution(resolution, self.f.store, self.f.objects)

    def test_old_failed_parent_remains_valid_after_same_session_directory_repair(self):
        from datetime import date
        from support import discovery_harness, listing_response, failed_response
        from sec_edgar_ingest.workflows.provenance import project_member
        from sec_edgar_ingest.workflows.completion import capture_member_provenance, validate_member_provenance
        with tempfile.TemporaryDirectory() as tmp:
            h = discovery_harness(Path(tmp), {
                '2026Q3': [failed_response(404), listing_response('2026Q3', [])],
                '2026Q4': [listing_response('2026Q4', ['master.20261001.idx'])]})
            try:
                old = h.run('daily', date(2026, 10, 7), 'same-directory-session')
                self.assertFalse(old.discovery_complete)
                value = project_member(h.workset_path(old), old.members[0].source_id, h.store, h.objects)
                newer = h.run('daily', date(2026, 10, 7), 'same-directory-session')
                self.assertTrue(newer.discovery_complete)
                proof = capture_member_provenance(value, h.store, h.objects)
                validate_member_provenance(proof, h.objects)
                self.assertFalse(proof['parent']['discovery_complete'])
                failed = [p for p in proof['discovery']['progress']
                          if p['value']['outcome']['outcome'] == 'discovery_failed']
                self.assertEqual(len(failed), 1)
                self.assertEqual(failed[0]['value']['members'], [])
            finally:
                h.close()

```

- [ ] **Step 2: Run red** with `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_completion.py -v`. Expected failure is absent T4 APIs, not missing cache or fabricated fixtures. Do not perform network fetch.

- [ ] **Step 3: Implement the following complete completion core**.

```python
# workflows/completion.py
from __future__ import annotations

import hashlib
from collections.abc import Mapping
from contextlib import closing

from ..discovery import reopen_listing
from ..etl.commands import _affected_quarters
from ..etl.contracts import (GenerationCapture, ObservationRef, decode_transformed,
                             processing_key)
from ..etl.reader import capture_quarter, validated_manifest
from ..etl.state import EtlState
from ..etl.transform import _read_manifest
from ..models import (Binding, DirectoryOutcome, Error, RunContext, Snapshot,
                      Source, canonical_json, parse_json)
from ..state import AcquisitionState, attempt_key
from ..storage.contracts import AlreadyExists, Conflict
from ..urls import child_url
from ..worksets import decode_source_workset, encode_workset, make_source_workset
from .checked import read_child, read_child_capture
from .contracts import CompletionEvaluation
from .provenance import read_member, read_parent, validate_parent_recovery, projection as expected_projection

import re
from datetime import date
from ..config import Settings, pin_context
from ..models import quarter_for, quarter_value, require_hash, to_mapping_value
from ..urls import canonical_listing_url
from .provenance import read_parent

PARENT_PROVENANCE_FORMAT = 'sec-workflow-parent-provenance-v1'


def validate_discovery_session(session):
    session = parse_json(canonical_json(to_mapping_value(session)))
    if not isinstance(session, dict) or set(session) != {
            'discovery_id', 'frozen', 'workset_id', 'predecessor_workset_id', 'history', 'registered'}:
        raise Conflict('captured discovery session fields differ')
    if not isinstance(session['discovery_id'], str) or not session['discovery_id'] or type(session['registered']) is not bool:
        raise Conflict('captured discovery session identity or registration differs')
    for identity in (session['workset_id'], session['predecessor_workset_id']):
        if identity is not None:
            require_hash(identity, 'captured discovery workset identity')
    if not isinstance(session['history'], list):
        raise Conflict('captured discovery history must be an array')
    for revision in session['history']:
        if set(revision) != {'workset_id', 'predecessor_workset_id', 'resumed_by'}:
            raise Conflict('captured discovery revision fields differ')
        require_hash(revision['workset_id'], 'captured discovery revision')
        if revision['predecessor_workset_id'] is not None:
            require_hash(revision['predecessor_workset_id'], 'captured discovery predecessor')
        RunContext.from_mapping(revision['resumed_by'])
    frozen = session['frozen']
    if not isinstance(frozen, dict) or set(frozen) != {
            'context', 'today', 'end', 'mode', 'acquisition_mode', 'units', 'overlap_from'}:
        raise Conflict('captured discovery frozen fields differ')
    origin = RunContext.from_mapping(frozen['context'])
    settings = Settings.from_mapping(origin.to_mapping()['effective_config'])
    if origin.command != 'discover' or origin.pinned_on is None:
        raise Conflict('captured discovery requires its original pinned command')
    pinned, end = pin_context(settings, origin, origin.pinned_on)
    if pinned != origin or frozen['today'] != origin.pinned_on.isoformat() or frozen['end'] != end:
        raise Conflict('captured discovery original date/settings/endpoint differ')
    if frozen['mode'] not in ('daily', 'quarterly') or frozen['acquisition_mode'] not in ('refresh', 'reuse_accepted'):
        raise Conflict('captured discovery mode differs')
    overlap = date.fromisoformat(frozen['overlap_from'])
    if overlap.isoformat() != frozen['overlap_from'] or overlap > origin.pinned_on:
        raise Conflict('captured discovery overlap date differs')
    units = frozen['units']
    if not isinstance(units, list) or not units or [unit['url'] for unit in units] != sorted({unit['url'] for unit in units}):
        raise Conflict('captured discovery units must be exact ordered unique addresses')
    pattern = re.compile(r'https://www\.sec\.gov/Archives/edgar/(full-index|daily-index)/(?:([1-9][0-9]{3})/(?:QTR([1-4])/)?)?index\.json\Z')
    for unit in units:
        if not isinstance(unit, dict) or set(unit) not in ({'url', 'period', 'role'}, {'url', 'period', 'role', 'bridge_period'}):
            raise Conflict('captured discovery unit fields differ')
        if canonical_listing_url(unit['url']) != unit['url']:
            raise Conflict('captured discovery unit URL is not canonical')
        match = pattern.fullmatch(unit['url'])
        if match is None:
            raise Conflict('captured discovery unit lacks an accepted family/period address')
        family, year, ordinal = match.groups()
        expected_role = 'quarter' if ordinal is not None else 'year' if year is not None else 'root'
        expected_period = f'{year}Q{ordinal}' if ordinal is not None else year if year is not None else family
        if (unit['role'], unit['period']) != (expected_role, expected_period):
            raise Conflict('captured discovery unit role/period differs from address')
        if 'bridge_period' in unit:
            quarter_value(unit['bridge_period'])
            if expected_role != 'root' or family != 'full-index' or unit['bridge_period'] != quarter_for(origin.pinned_on):
                raise Conflict('captured root bridge period differs from original open quarter')
    return origin


def capture_parent_provenance(parent_ref, store, objects):
    parent = read_parent(parent_ref, store, objects)
    evidence = {'format_version': PARENT_PROVENANCE_FORMAT, 'parent_ref': parent_ref,
                'parent': parent.to_mapping(),
                'discovery': _discovery_snapshot(parent, store, objects)}
    validate_parent_provenance(evidence, objects)
    return _plain(evidence)


def validate_parent_provenance(evidence, objects):
    evidence = parse_json(canonical_json(to_mapping_value(evidence)))
    if not isinstance(evidence, dict) or set(evidence) != {'format_version', 'parent_ref', 'parent', 'discovery'} or evidence['format_version'] != PARENT_PROVENANCE_FORMAT:
        raise Conflict('captured parent provenance schema differs')
    parent = _read_set(evidence['parent_ref'], objects)
    if parent.to_mapping() != evidence['parent']:
        raise Conflict('captured parent differs from exact immutable source workset')
    validate_discovery_session(evidence['discovery']['session'])
    _validate_discovery(parent, evidence['discovery'], objects)
    return parent

CAPTURE_FORMAT = 'sec-workflow-completion-v1'
OBLIGATION_FORMAT = 'sec-workflow-repair-obligation-v1'
RESOLUTION_FORMAT = 'sec-workflow-repair-resolution-v1'
PROVENANCE_FORMAT = 'sec-workflow-member-provenance-v1'


def _plain(value):
    return parse_json(canonical_json(to_mapping_value(value)))


def _immutable(kind, key, value, store):
    try:
        store.insert(kind, key, _plain(value))
    except AlreadyExists:
        row = store.get(kind, key)
        if row is None or canonical_json(to_mapping_value(row.to_mapping()['value'])) != canonical_json(to_mapping_value(value)):
            raise Conflict(f'{kind} immutable evidence differs')


def _document(value, format_version, namespace, objects):
    value = _plain(value)
    body = canonical_json(to_mapping_value(value))
    identity = hashlib.sha256(body).hexdigest()
    path = f'worksets/sec/{namespace}/sha256={identity}/evidence.json'
    objects.put_once(path, body)
    return {'ref': path, 'sha256': identity, 'bytes': len(body), 'format_version': format_version}


from ..models import quarter_value, require_hash, require_number, safe_relative_path
from .checked import _authority, _context_matches, _transformed_input


def _read_document(descriptor, format_version, objects):
    if format_version not in (OBLIGATION_FORMAT, RESOLUTION_FORMAT):
        raise Conflict('unsupported repair document format')
    if set(descriptor) != {'ref', 'sha256', 'bytes', 'format_version'}:
        raise Conflict('repair document descriptor fields differ')
    require_hash(descriptor['sha256'], 'repair document digest')
    require_number(descriptor['bytes'], 'repair document bytes', integer=True)
    safe_relative_path(descriptor['ref'], 'repair document ref')
    namespace = ('workflow-repairs' if format_version == OBLIGATION_FORMAT
                 else 'workflow-repair-resolutions')
    expected_path = f"worksets/sec/{namespace}/sha256={descriptor['sha256']}/evidence.json"
    if descriptor['ref'] != expected_path or descriptor['format_version'] != format_version:
        raise Conflict('repair document address or version differs')
    objects.verify(descriptor['ref'], descriptor['sha256'], descriptor['bytes'])
    body = objects.read(descriptor['ref'])
    value = parse_json(body)
    if not isinstance(value, dict) or canonical_json(to_mapping_value(value)) != body or value.get('format_version') != format_version:
        raise Conflict('repair document canonical payload differs')
    if format_version == RESOLUTION_FORMAT:
        if set(value) != {'format_version', 'obligation', 'call', 'result', 'quarters', 'repair_artifacts'}:
            raise Conflict('repair resolution payload fields differ')
        _read_document(value['obligation'], OBLIGATION_FORMAT, objects)
        return value
    if set(value) != {'format_version', 'call', 'context', 'transformed_ref', 'sources', 'affected_quarters'}:
        raise Conflict('repair obligation payload fields differ')
    original_call = value['call']
    actual = RunContext.from_mapping(value['context'])
    if actual.command != 'publish' or not isinstance(original_call, dict):
        raise Conflict('repair obligation must describe original publication authority')
    if original_call.get('format_version') == LEGACY_PUBLISH_FORMAT:
        if _legacy_publish_call(actual, objects) != original_call:
            raise Conflict('repair obligation differs from original legacy command')
    elif original_call.get('format_version') == 'sec-workflow-child-call-v1':
        call, template = _authority(original_call, None, objects)
        _context_matches(template, actual)
        command_path = call['result_ref'].rsplit('/', 1)[0] + '/command.json'
        frozen = {'context': actual.to_mapping(), 'intent': call['intent']}
        if objects.read(command_path) != canonical_json(to_mapping_value(frozen)):
            raise Conflict('repair obligation differs from original checked command')
    else:
        raise Conflict('repair obligation uses an unknown original call authority')
    if original_call['input_ref'] != value['transformed_ref']:
        raise Conflict('repair obligation changes original publication input')
    transformed = _transformed_input(value['transformed_ref'], None, objects)
    if (transformed.context.parser_version, transformed.context.schema_version) != (
            actual.parser_version, actual.schema_version):
        raise Conflict('repair obligation original command/input versions differ')
    if value['sources'] != [ref.to_mapping() for ref in transformed.observations]:
        raise Conflict('repair obligation sources differ from exact decoded input')
    affected = value['affected_quarters']
    if not isinstance(affected, list) or affected != sorted(set(affected)):
        raise Conflict('repair obligation affected quarters duplicate or reorder units')
    for quarter in affected:
        quarter_value(quarter)
    observed = {quarter for ref in transformed.observations for quarter in ref.quarter_counts}
    if not observed <= set(affected):
        raise Conflict('repair obligation omits an observation output quarter')
    return value

def _read_set(path, objects):
    body = objects.read(path)
    result = decode_source_workset(body)
    if path != f'worksets/sec/source/sha256={result.workset_id}/workset.json' or encode_workset(result) != body:
        raise Conflict('source workset path or canonical bytes differ')
    return result


def _discovery_snapshot(parent, store, objects):
    state = AcquisitionState(store)
    row = state.discovery_session(parent.discovery_id)
    session = None if row is None else row.to_mapping()['value']
    identities = set() if session is None else ({session.get('workset_id'), session.get('predecessor_workset_id')} | {item['workset_id'] for item in session.get('history', ())})
    identities.discard(None)
    if session is None or parent.workset_id not in identities:
        recovered = store.get('WorkflowParentRecovery', parent.workset_id)
        if recovered is None:
            raise Conflict('parent absent from original session and immutable recovery evidence')
        descriptor = recovered.to_mapping()['value']
        ref = f'worksets/sec/source/sha256={parent.workset_id}/workset.json'
        snapshot = validate_parent_recovery(ref, descriptor, objects)
        return {**_plain(snapshot), 'recovery': descriptor}
    progress = []
    for unit in session['frozen']['units']:
        original = next(d for d in parent.directories if d.url == unit['url'])
        if original.outcome == 'discovery_failed':
            value = {'discovery_id': parent.discovery_id, 'outcome': original.to_mapping(),
                     'members': [], 'evidence': None, 'selection': {'ignored': []},
                     'observed_gap_token': None}
        else:
            row = state.directory_progress(parent.discovery_id, unit['url'])
            if row is None:
                raise Conflict('parent has missing successful directory progress')
            value = row.to_mapping()['value']
        progress.append({'unit': unit, 'value': value})
    return {'session': session, 'progress': progress, 'recovery': None}


def _validate_discovery(parent, evidence, objects):
    if set(evidence) != {'session', 'progress', 'recovery'}:
        raise Conflict('captured discovery evidence schema differs')
    if evidence['recovery'] is not None:
        ref = f'worksets/sec/source/sha256={parent.workset_id}/workset.json'
        validated = validate_parent_recovery(ref, evidence['recovery'], objects)
        if _plain(validated) != {'session': evidence['session'], 'progress': evidence['progress']}:
            raise Conflict('captured recovered-parent provenance differs')
        return
    session = evidence['session']
    frozen = session['frozen']
    context = RunContext.from_mapping(frozen['context'])
    if context != parent.context or session['discovery_id'] != parent.discovery_id:
        raise Conflict('captured parent discovery provenance differs')
    allowed = {session.get('workset_id'), session.get('predecessor_workset_id')} | {item['workset_id'] for item in session.get('history', ())}
    allowed.discard(None)
    if parent.workset_id not in allowed:
        raise Conflict('captured parent was never a session workset')
    required = {unit['url']: unit for unit in frozen['units']}
    supplied = {entry['unit']['url']: entry for entry in evidence['progress']}
    if len(required) != len(frozen['units']) or len(supplied) != len(evidence['progress']) or set(supplied) != set(required):
        raise Conflict('captured discovery required-unit ledger differs')
    outcomes, members, listings = [], {}, {}
    for unit in sorted(frozen['units'], key=lambda u: (u['url'].count('/'), u['url'])):
        entry = supplied[unit['url']]
        if entry['unit'] != unit or entry['value']['discovery_id'] != parent.discovery_id:
            raise Conflict('captured directory unit identity differs')
        value = entry['value']
        outcome = DirectoryOutcome.from_mapping(value['outcome'])
        if outcome.outcome != 'discovery_failed':
            outcome, selected, entries, _ = reopen_listing(objects, value, unit, context)
            if unit['role'] != 'root':
                parent_url = unit['url'].rsplit('/', 2)[0] + '/index.json'
                wanted = unit['url'].rsplit('/', 2)[1]
                candidate = next((item for item in listings.get(parent_url, ())
                                  if item.name == wanted and item.kind == 'dir'), None)
                if candidate is None or child_url(parent_url, candidate.href, candidate.name, True) + 'index.json' != unit['url']:
                    raise Conflict('captured successful directory lacks actual parent authorization')
            listings[unit['url']] = entries
            for source in selected:
                members[source.source_id] = source
        elif outcome.url != unit['url'] or outcome.period != unit['period'] or value['members']:
            raise Conflict('captured failed directory unit differs')
        outcomes.append(outcome)
    rebuilt = make_source_workset(context, frozen['end'], parent.discovery_id,
                                  tuple(members.values()), tuple(outcomes),
                                  __import__('datetime').date.fromisoformat(frozen['overlap_from']),
                                  acquisition_mode=frozen['acquisition_mode'])
    if rebuilt != parent:
        raise Conflict('captured discovery does not reconstruct exact original parent')


def capture_member_provenance(value, store, objects):
    projection = read_member(value, store, objects)
    parent = _read_set(value['parent_ref'], objects)
    evidence = {'format_version': PROVENANCE_FORMAT, 'member': _plain(value),
                'parent': parent.to_mapping(), 'projection': projection.to_mapping(),
                'discovery': _discovery_snapshot(parent, store, objects)}
    validate_member_provenance(evidence, objects)
    return evidence


def validate_member_provenance(evidence, objects):
    evidence = _plain(evidence)
    if set(evidence) != {'format_version', 'member', 'parent', 'projection', 'discovery'} or evidence['format_version'] != PROVENANCE_FORMAT:
        raise Conflict('unsupported member provenance capture')
    value = evidence['member']
    parent = _read_set(value['parent_ref'], objects)
    projection = _read_set(value['member_ref'], objects)
    if parent.to_mapping() != evidence['parent'] or projection.to_mapping() != evidence['projection']:
        raise Conflict('member provenance differs from immutable worksets')
    source = Source.from_mapping(value['source'])
    if value['member_id'] != projection.workset_id or projection.members != (source,) or source not in parent.members:
        raise Conflict('member provenance identity differs')
    directory = next(d for d in parent.directories if source.source_id in d.source_ids)
    singleton = __import__('dataclasses').replace(directory, source_ids=(source.source_id,))
    expected = expected_projection(parent, source.source_id)
    if expected != projection:
        raise Conflict('member projection changes original provenance')
    _validate_discovery(parent, evidence['discovery'], objects)


def validate_capture(capture, objects) -> None:
    capture = _plain(capture)
    fields = {'format_version', 'member', 'parent', 'projection', 'discovery',
              'binding', 'snapshot', 'observation', 'affected_quarters', 'quarters'}
    if set(capture) != fields or capture['format_version'] != CAPTURE_FORMAT:
        raise Conflict('unsupported completion capture shape')
    value = capture['member']
    parent = _read_set(value['parent_ref'], objects)
    projection = _read_set(value['member_ref'], objects)
    if parent.to_mapping() != capture['parent'] or projection.to_mapping() != capture['projection']:
        raise Conflict('captured source worksets differ from immutable objects')
    source = Source.from_mapping(value['source'])
    if value['member_id'] != projection.workset_id or projection.members != (source,) or source not in parent.members:
        raise Conflict('captured member identity differs')
    directory = next(d for d in parent.directories if source.source_id in d.source_ids)
    singleton = __import__('dataclasses').replace(directory, source_ids=(source.source_id,))
    expected = expected_projection(parent, source.source_id)
    if expected != projection:
        raise Conflict('projection changes original provenance')
    _validate_discovery(parent, capture['discovery'], objects)
    binding = Binding.from_mapping(capture['binding'])
    snapshot = Snapshot.from_mapping(capture['snapshot'])
    ref = ObservationRef.from_mapping(capture['observation'])
    if (binding.source_workset_id, binding.source_id, binding.snapshot_sha256) != (
            projection.workset_id, source.source_id, snapshot.sha256):
        raise Conflict('capture binding differs')
    if ref.source != source or ref.snapshot != snapshot:
        raise Conflict('capture observation differs from exact source/snapshot')
    objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
    durable, _ = _read_manifest(ref.manifest_ref, objects)
    if durable != ref:
        raise Conflict('capture observation differs from immutable readback')
    affected = capture['affected_quarters']
    quarters = [GenerationCapture.from_mapping(q) for q in capture['quarters']]
    if affected != sorted(set(affected)) or [q.quarter for q in quarters] != affected or not set(ref.quarter_counts) <= set(affected):
        raise Conflict('capture affected-quarter coverage differs')
    for quarter in quarters:
        manifest = validated_manifest(quarter, objects)
        if (manifest.parser_version, manifest.schema_version) != (ref.parser_version, ref.schema_version):
            raise Conflict('captured publication versions differ')
        if next((r for r in manifest.sources if r.source.source_id == source.source_id), None) != ref:
            raise Conflict('captured publication source membership differs')


from ..config import Settings, pin_context
from ..etl.commands import read_etl_result
from ..results import result_path
from .checked import _validate_input_output

LEGACY_PUBLISH_FORMAT = 'sec-workflow-legacy-publish-v1'


def _legacy_publish_call(context, objects):
    if context.command != 'publish':
        raise Conflict('legacy repair context is not a publish command')
    settings = Settings.from_mapping(context.to_mapping()['effective_config'])
    if context.pinned_on is None or pin_context(settings, context, context.pinned_on)[0] != context:
        raise Conflict('legacy publish context is not exactly pinned')
    path = result_path(context)
    command_path = path.rsplit('/', 1)[0] + '/command.json'
    body = objects.read(command_path)
    frozen = parse_json(body)
    if (not isinstance(frozen, dict) or set(frozen) != {'context', 'intent'}
            or canonical_json(to_mapping_value(frozen)) != body or frozen['context'] != context.to_mapping()):
        raise Conflict('legacy publish frozen command differs from exact Attempt context')
    intent = frozen['intent']
    if (not isinstance(intent, dict) or set(intent) != {'command', 'today', 'workset', 'force'}
            or intent['command'] != 'publish' or intent['force'] is not None
            or intent['today'] not in (None, context.pinned_on.isoformat())):
        raise Conflict('legacy publish frozen intent differs')
    workset = decode_transformed(objects.read(intent['workset']))
    from ..etl.contracts import transformed_ref
    if transformed_ref(workset) != intent['workset']:
        raise Conflict('legacy publish transformed input address differs')
    if not workset.complete:
        raise Conflict('legacy unfinished publication has no complete publishable input')
    if (workset.context.parser_version, workset.context.schema_version) != (
            context.parser_version, context.schema_version):
        raise Conflict('legacy publish input versions differ')
    return {'format_version': LEGACY_PUBLISH_FORMAT, 'context': context.to_mapping(),
            'intent': intent, 'input_ref': intent['workset'], 'result_ref': path}


def read_legacy_publish(call, store, objects):
    if set(call) != {'format_version', 'context', 'intent', 'input_ref', 'result_ref'} or call['format_version'] != LEGACY_PUBLISH_FORMAT:
        raise Conflict('legacy publication call schema differs')
    context = RunContext.from_mapping(call['context'])
    if _legacy_publish_call(context, objects) != _plain(call):
        raise Conflict('legacy publication descriptor differs from canonical command')
    result = read_etl_result(call['result_ref'], objects)
    if result.context != context:
        raise Conflict('legacy publication result differs from original exact context')
    # The earlier checked validation is namespace-independent at this layer:
    # it validates exact transformed input, raw chain, versions and all quarter artifacts.
    _validate_input_output(call, result, store, objects)
    if store is not None:
        row = store.get('Attempt', attempt_key(context))
        if row is None or row.to_mapping()['value']['context'] != context.to_mapping() or row.to_mapping()['value']['result'] != result.to_mapping():
            raise Conflict('legacy publication result requires repaired original Attempt')
    return result


def _read_publish_call(call, store, objects):
    if call.get('format_version') == LEGACY_PUBLISH_FORMAT:
        return read_legacy_publish(call, store, objects)
    return read_child(call, store, objects)


def _call_context(call, store, objects):
    template = RunContext.from_mapping(call['context'])
    row = store.get('Attempt', attempt_key(template))
    if row is None:
        return None
    value = row.to_mapping()['value']
    actual = RunContext.from_mapping(value['context'])
    if call.get('format_version') == LEGACY_PUBLISH_FORMAT:
        if actual != template or _legacy_publish_call(actual, objects) != _plain(call):
            raise Conflict('legacy unfinished publication differs from exact canonical Attempt')
    else:
        expected = template.to_mapping()
        expected['started_at'] = actual.started_at.isoformat()
        if expected != actual.to_mapping() or actual.started_at < template.started_at or actual.started_at >= actual.deadline:
            raise Conflict('unfinished publish Attempt differs from checked call')
        command_path = call['result_ref'].rsplit('/', 1)[0] + '/command.json'
        frozen = {'context': actual.to_mapping(), 'intent': _plain(call['intent'])}
        if objects.read(command_path) != canonical_json(to_mapping_value(frozen)):
            raise Conflict('unfinished publish command intent differs')
    return value


def _publish_calls(store, objects):
    checked, checked_paths = [], set()
    for row in store.scan('WorkflowChildCall', {}):
        value = row.to_mapping()['value']
        try:
            call, template = _authority(value, None, objects)
            if template.command != 'publish':
                continue
            _transformed_input(call['input_ref'], None, objects)
            attempt = _call_context(call, store, objects)
            if attempt is None:
                continue  # Before begin/command commit, this call cannot have reached CAS.
            checked.append(call); checked_paths.add(call['result_ref'])
        except (ValueError, OSError, Conflict, KeyError, TypeError):
            # T7 records corrupt command/Attempt evidence as a retained workflow gap.
            # Such a record supplies no source completion and cannot authorize a repair.
            continue
    legacy = []
    for row in store.scan('Attempt', {}):
        value = row.to_mapping()['value']
        try:
            context = RunContext.from_mapping(value['context'])
            if context.command != 'publish' or result_path(context) in checked_paths:
                continue
            call = _legacy_publish_call(context, objects)
            _transformed_input(call['input_ref'], None, objects)
            call_key = hashlib.sha256(canonical_json(to_mapping_value(call))).hexdigest()
            if value['result'] is None or store.get('WorkflowRepairObligation', call_key) is not None:
                legacy.append(call)
        except (ValueError, OSError, Conflict, KeyError, TypeError):
            # Inventory uncertainty is isolated by T7 rather than becoming false success.
            continue
    calls = checked + legacy
    if len({canonical_json(to_mapping_value(call)) for call in calls}) != len(calls):
        raise Conflict('duplicate original publication call authority')
    return tuple(calls)

def _obligations(source, store, objects):
    found = []
    for call in _publish_calls(store, objects):
        workset = decode_transformed(objects.read(call['input_ref']))
        if not any(ref.source == source for ref in workset.observations):
            continue
        call_key = hashlib.sha256(canonical_json(to_mapping_value(call))).hexdigest()
        saved = store.get('WorkflowRepairObligation', call_key)
        if saved is None:
            try:
                _read_publish_call(call, store, objects)
            except FileNotFoundError:
                attempt = _call_context(call, store, objects)
                if attempt is None:
                    continue
                if attempt['result'] is not None:
                    raise Conflict('finished Attempt lacks its immutable child result')
            else:
                continue
            recorded = [q['quarter'] for error in attempt['structured_errors']
                        for q in error.get('details', {}).get('quarters', ())]
            quarters = sorted(set(recorded) | set(_affected_quarters(workset.observations, objects, store)))
            payload = {'format_version': OBLIGATION_FORMAT, 'call': call,
                       'context': attempt['context'], 'transformed_ref': call['input_ref'],
                       'sources': [ref.to_mapping() for ref in workset.observations],
                       'affected_quarters': quarters}
            descriptor = _document(payload, OBLIGATION_FORMAT, 'workflow-repairs', objects)
            _read_document(descriptor, OBLIGATION_FORMAT, objects)
            _immutable('WorkflowRepairObligation', call_key,
                       {'call_sha256': call_key, 'descriptor': descriptor}, store)
        else:
            indexed = saved.to_mapping()['value']
            if indexed['call_sha256'] != call_key:
                raise Conflict('repair obligation call identity differs')
            descriptor = indexed['descriptor']
            payload = _read_document(descriptor, OBLIGATION_FORMAT, objects)
            if (payload['call'] != call or payload['transformed_ref'] != call['input_ref']
                    or payload['sources'] != [r.to_mapping() for r in workset.observations]):
                raise Conflict('repair obligation immutable input differs')
        resolution_row = store.get('WorkflowRepairResolution', call_key)
        if resolution_row is None:
            try:
                repaired = _read_publish_call(call, store, objects)
            except FileNotFoundError:
                pass
            else:
                if repaired.outcome in ('success', 'unchanged'):
                    if call.get('format_version') == LEGACY_PUBLISH_FORMAT:
                        # Exact original public retry may finish its own index. Its
                        # immutable result discharges this obligation directly.
                        captures, artifacts = _publication_captures(repaired, store, objects)
                        _write_resolution(descriptor, call, repaired, captures, artifacts, store, objects)
                    else:
                        resolve_repair(descriptor, call, store, objects)
                    resolution_row = store.get('WorkflowRepairResolution', call_key)
        if resolution_row is not None:
            validate_resolution_capture(resolution_row.to_mapping()['value'], objects)
        else:
            found.append(descriptor)
    return tuple(found)

def outstanding_repairs(value, store, objects):
    read_member(value, store, objects)
    return _obligations(Source.from_mapping(value['source']), store, objects)


def read_repair_obligation(path, objects):
    body = objects.read(path)
    descriptor = {'ref': path, 'sha256': hashlib.sha256(body).hexdigest(),
                  'bytes': len(body), 'format_version': OBLIGATION_FORMAT}
    _read_document(descriptor, OBLIGATION_FORMAT, objects)
    return descriptor


def _repair_artifacts(manifest, store):
    artifacts = []
    for ref in manifest.sources:
        if not ref.quarter_counts.get(manifest.quarter):
            continue
        key = processing_key(ref.source.source_id, ref.snapshot.sha256,
                             ref.parser_version, ref.schema_version)
        receipt_key = hashlib.sha256(canonical_json(to_mapping_value([key, manifest.quarter, manifest.generation_id]))).hexdigest()
        expected = {'processing_key': key, 'quarter': manifest.quarter,
                    'generation_id': manifest.generation_id,
                    'source_fingerprint': manifest.source_fingerprint}
        receipt = store.get('PublicationReceipt', receipt_key)
        processing = store.get('Processing', key)
        if receipt is None or receipt.to_mapping()['value'] != expected or processing is None:
            raise Conflict('checked publication repair artifacts are absent or differ')
        value = processing.to_mapping()['value']
        if value['processing_key'] != key or value['observation'] != ref.to_mapping() or value['publications'].get(manifest.quarter, {}).get(manifest.generation_id) != receipt_key:
            raise Conflict('checked publication Processing membership differs')
        artifacts.append({'receipt_key': receipt_key, 'receipt': expected,
                          'observation': ref.to_mapping()})
    return artifacts


def _publication_captures(result, store, objects):
    captures, artifacts = [], []
    for quarter in result.quarters:
        if quarter.outcome not in ('published', 'unchanged'):
            raise Conflict('repair resolution has unfinished publication quarter')
        body = objects.read(quarter.manifest_ref)
        capture = GenerationCapture(quarter.quarter, quarter.generation_id, quarter.manifest_ref,
                                    hashlib.sha256(body).hexdigest(), len(body))
        manifest = validated_manifest(capture, objects)
        captures.append(capture.to_mapping())
        artifacts.append({'quarter': quarter.quarter, 'records': _repair_artifacts(manifest, store)})
    return captures, artifacts


def _write_resolution(obligation, call, result, captures, artifacts, store, objects):
    original = _read_document(obligation, OBLIGATION_FORMAT, objects)
    if (result.context.command != 'publish' or result.outcome not in ('success', 'unchanged')
            or result.input_ref != original['transformed_ref']
            or call['input_ref'] != original['transformed_ref']):
        raise Conflict('repair resolution requires exact successful transformed input')
    if set(original['affected_quarters']) - {q['quarter'] for q in captures}:
        raise Conflict('repair resolution omitted formerly affected quarter')
    for ref_value in original['sources']:
        ref = ObservationRef.from_mapping(ref_value)
        for captured in captures:
            manifest = validated_manifest(GenerationCapture.from_mapping(captured), objects)
            if next((r for r in manifest.sources if r.source.source_id == ref.source.source_id), None) != ref:
                raise Conflict('repair resolution silently supersedes unfinished source evidence')
    payload = {'format_version': RESOLUTION_FORMAT, 'obligation': _plain(obligation),
               'call': _plain(call), 'result': result.to_mapping(),
               'quarters': captures, 'repair_artifacts': artifacts}
    descriptor = _document(payload, RESOLUTION_FORMAT, 'workflow-repair-resolutions', objects)
    call_key = hashlib.sha256(canonical_json(to_mapping_value(original['call']))).hexdigest()
    _immutable('WorkflowRepairResolution', call_key, descriptor, store)
    return descriptor


def resolve_repair(obligation, successful_publish_call, store, objects):
    call = _plain(successful_publish_call)
    result = _read_publish_call(call, store, objects)
    captures, artifacts = _publication_captures(result, store, objects)
    return _write_resolution(obligation, call, result, captures, artifacts, store, objects)


def _expected_artifacts(manifest):
    expected = []
    for ref in manifest.sources:
        if not ref.quarter_counts.get(manifest.quarter):
            continue
        key = processing_key(ref.source.source_id, ref.snapshot.sha256,
                             ref.parser_version, ref.schema_version)
        receipt_key = hashlib.sha256(canonical_json(to_mapping_value([key, manifest.quarter, manifest.generation_id]))).hexdigest()
        receipt = {'processing_key': key, 'quarter': manifest.quarter,
                   'generation_id': manifest.generation_id,
                   'source_fingerprint': manifest.source_fingerprint}
        expected.append({'receipt_key': receipt_key, 'receipt': receipt,
                         'observation': ref.to_mapping()})
    return expected


def validate_resolution_capture(resolution, objects):
    value = _read_document(resolution, RESOLUTION_FORMAT, objects)
    original = _read_document(value['obligation'], OBLIGATION_FORMAT, objects)
    call = value['call']
    result = (read_legacy_publish(call, None, objects)
              if call.get('format_version') == LEGACY_PUBLISH_FORMAT
              else read_child_capture(call, objects))
    if (result.to_mapping() != value['result'] or result.context.command != 'publish'
            or result.input_ref != original['transformed_ref']
            or call['input_ref'] != original['transformed_ref']
            or result.outcome not in ('success', 'unchanged')):
        raise Conflict('repair resolution child evidence differs')
    quarters = {q.quarter: q for q in result.quarters}
    captured = {q['quarter']: q for q in value['quarters']}
    if len(captured) != len(value['quarters']) or set(original['affected_quarters']) - set(captured) or set(quarters) != set(captured):
        raise Conflict('repair resolution quarter set differs')
    artifacts = {v['quarter']: v['records'] for v in value['repair_artifacts']}
    if len(artifacts) != len(value['repair_artifacts']) or set(artifacts) != set(captured):
        raise Conflict('repair resolution artifact coverage differs')
    for quarter, mapping in captured.items():
        capture = GenerationCapture.from_mapping(mapping)
        manifest = validated_manifest(capture, objects)
        q = quarters[quarter]
        if q.outcome not in ('published', 'unchanged') or (q.generation_id, q.manifest_ref) != (capture.generation_id, capture.manifest_ref):
            raise Conflict('repair resolution capture differs from successful command')
        if artifacts[quarter] != _expected_artifacts(manifest):
            raise Conflict('captured repair artifacts differ from manifest identities')
        for ref_value in original['sources']:
            ref = ObservationRef.from_mapping(ref_value)
            if next((r for r in manifest.sources if r.source.source_id == ref.source.source_id), None) != ref:
                raise Conflict('repair resolution source membership differs')
def validate_resolution(resolution, store, objects):
    validate_resolution_capture(resolution, objects)
    value = _read_document(resolution, RESOLUTION_FORMAT, objects)
    result = (read_legacy_publish(value['call'], None, objects)
              if value['call'].get('format_version') == LEGACY_PUBLISH_FORMAT
              else read_child_capture(value['call'], objects))
    artifact_by_quarter = {v['quarter']: v['records'] for v in value['repair_artifacts']}
    for mapping in value['quarters']:
        capture = GenerationCapture.from_mapping(mapping)
        manifest = validated_manifest(capture, objects)
        if artifact_by_quarter[capture.quarter] != _repair_artifacts(manifest, store):
            raise Conflict('repair resolution current recoverable indexes differ')


def evaluate_member(value, parser_version, schema_version, store, objects):
    source = Source.from_mapping(value['source'])
    obligations = ()
    try:
        projection = read_member(value, store, objects)
        obligations = _obligations(source, store, objects)
        acquisition = AcquisitionState(store)
        binding = acquisition.binding(projection.workset_id, source.source_id)
        if binding is None:
            return CompletionEvaluation(False, None, obligations,
                (Error('acquisition_pending', 'member has no exact raw pin', True, source.source_id, {}),))
        snapshot = acquisition.snapshot(source.source_id, binding.snapshot_sha256)
        key = processing_key(source.source_id, snapshot.sha256, parser_version, schema_version)
        row = store.get('Processing', key)
        if row is None:
            return CompletionEvaluation(False, None, obligations,
                (Error('transform_pending', 'member has no current Processing identity', True, source.source_id, {}),))
        processing = row.to_mapping()['value']
        ref = ObservationRef.from_mapping(processing['observation'])
        if processing['processing_key'] != key or (ref.source, ref.snapshot, ref.parser_version, ref.schema_version) != (source, snapshot, parser_version, schema_version):
            raise Conflict('decoded Processing identity differs from member pin/current versions')
        durable, _ = _read_manifest(ref.manifest_ref, objects)
        if durable != ref:
            raise Conflict('Processing differs from immutable observation')
        affected = _affected_quarters((ref,), objects, store)
        captures, gaps = [], []
        for quarter in affected:
            capture = capture_quarter(quarter, objects, EtlState(store))
            if capture is None:
                gaps.append(Error('publication_pending', 'affected quarter has no publication', True, source.source_id, {'quarter': quarter}))
                continue
            manifest = validated_manifest(capture, objects)
            if next((r for r in manifest.sources if r.source.source_id == source.source_id), None) != ref:
                gaps.append(Error('publication_pending', 'affected quarter does not contain exact current observation', True, source.source_id, {'quarter': quarter}))
                continue
            captures.append(capture.to_mapping())
        if gaps or obligations:
            return CompletionEvaluation(False, None, obligations, tuple(gaps))
        parent = _read_set(value['parent_ref'], objects)
        capture = {'format_version': CAPTURE_FORMAT, 'member': _plain(value),
                   'parent': parent.to_mapping(), 'projection': projection.to_mapping(),
                   'discovery': _discovery_snapshot(parent, store, objects), 'binding': binding.to_mapping(),
                   'snapshot': snapshot.to_mapping(), 'observation': ref.to_mapping(),
                   'affected_quarters': affected, 'quarters': captures}
        validate_capture(capture, objects)
        return CompletionEvaluation(True, capture, (), ())
    except (Conflict, ValueError, OSError, KeyError, StopIteration) as error:
        return CompletionEvaluation(False, None, obligations,
            (Error('state_conflict', str(error), False, source.source_id,
                   {'type': type(error).__name__}),))
```


- [ ] **Step 4: Run green** using the exact red command; add provenance-corruption, divergent binding winner and missing capture/file regressions from T2's fixtures, then run `test_etl_cli.py` and `test_etl_publication.py` because this task consumes their authoritative publication rules. No shipped publication implementation changes are proposed.
- [ ] **Step 5: Fresh task review** checks F1/F3 independently, decoder equality, complete historical validation, expiry/new-attempt resolution, pointer row equality and precise public signatures. Commit only after the review passes; no completion credit from a boolean mock.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_completion.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/completion.py packages/sec-edgar-ingest/tests/support_workflow_evidence.py packages/sec-edgar-ingest/tests/test_workflow_completion.py
git commit -m "feat: validate workflow completion and durable repair evidence"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 5: Checked single-member processing and immutable member receipts

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/processing.py`, `packages/sec-edgar-ingest/tests/test_workflow_processing.py`; complete `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py` receipt methods.

**Interfaces:** `ProcessedMember(result: MemberResult,evidence: Mapping[str,object])`; `process_member(value,context,dispatcher,store,objects,observer=None) -> ProcessedMember`; `validate_member_evidence(result,evidence,objects) -> None`; `WorkflowMembers.record(result,context,evidence) -> Mapping`; `.completed(value,parser_version,schema_version) -> Mapping|None`. Consumes T3 Dispatcher/ChildUnfinished/read_child_capture, T4 evaluate_member/outstanding_repairs/resolve_repair/validate_capture/validate_resolution_capture. T6 consumes these receipts. No orchestration, discovery inventory or report persistence lives here.

- [ ] Add the real retry-prefix/source-refusal regression below to `test_workflow_processing.py` before implementing process_member. It uses T2 builders and T3's actual CLI dispatcher, local coordinator and stores:

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, json, tempfile, unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from support_workflows import BASE, CommandHarness, simple_pack
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.models import RunContext, canonical_json
from sec_edgar_ingest.worksets import decode_source_workset
from sec_edgar_ingest.workflows.checked import Dispatcher
from sec_edgar_ingest.workflows.provenance import project_member
from sec_edgar_ingest.workflows.processing import process_member

class ProcessingTests(unittest.TestCase):
    def test_retry_prefix_is_retained_without_source_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = simple_pack(root / 'pack')
            manifest = json.loads(pack.read_text())
            url = BASE + 'daily-index/2026/QTR4/master.20261001.idx'
            prefix = b'retained truncated prefix'
            sha = hashlib.sha256(prefix).hexdigest()
            (pack.parent / 'bodies' / (sha + '.body')).write_bytes(prefix)
            manifest['responses'][url].insert(0, {
                'status': 200, 'headers': {'X-Fixture': 'partial'}, 'fault': 'read_timeout',
                'body_path': 'bodies/' + sha + '.body', 'body_sha256': sha})
            pack.write_bytes(canonical_json(to_mapping_value(manifest)))
            h = CommandHarness(root, pack)
            try:
                now = datetime.now(timezone.utc)
                context = RunContext('processing', 'manual', 'daily', 'a',
                    h.settings.worker.image_digest, h.settings.etl.parser_version,
                    h.settings.etl.schema_version, h.settings.config_sha256,
                    now, now + timedelta(seconds=1800), 'daily')
                context = pin_context(h.settings, context, date(2026, 10, 7))[0]
                dispatcher = Dispatcher(context, h.settings, pack, root, h.store, h.objects)
                discovered = dispatcher.execute('discover', 'discover', h.settings,
                    ('--mode', 'daily', '--discovery-id', 'processing-daily'))
                parent = decode_source_workset(h.objects.read(discovered.result.source_workset_ref))
                value = project_member(discovered.result.source_workset_ref,
                    parent.members[0].source_id, h.store, h.objects)
                processed = process_member(value, context, dispatcher, h.store, h.objects)
                self.assertFalse(processed.result.quarantined)
                self.assertEqual(processed.result.outcome, 'success')
                self.assertTrue(processed.result.transformed)
                self.assertEqual(len(processed.result.child_refs), 3)
                self.assertTrue(any(p.read_bytes() == prefix for p in
                    (root / '.fixture-state/objects/quarantine/sec').rglob('body')))
                capture, rows = h.capture('2026Q4')
                self.assertEqual(len(rows), 1)
            finally:
                h.close()
    def prepare(self, root, *, conflicting=False):
        h = CommandHarness(root, simple_pack(root / 'pack', conflicting=conflicting))
        now = datetime.now(timezone.utc)
        context = RunContext('processing', 'manual', 'daily', 'a',
            h.settings.worker.image_digest, h.settings.etl.parser_version,
            h.settings.etl.schema_version, h.settings.config_sha256,
            now, now + timedelta(seconds=1800), 'daily')
        context = pin_context(h.settings, context, date(2026, 10, 7))[0]
        dispatcher = Dispatcher(context, h.settings, h.pack, root, h.store, h.objects)
        found = dispatcher.execute('discover', 'discover', h.settings,
            ('--mode', 'daily', '--discovery-id', 'processing-daily'))
        parent = decode_source_workset(h.objects.read(found.result.source_workset_ref))
        value = project_member(found.result.source_workset_ref, parent.members[0].source_id, h.store, h.objects)
        return h, context, dispatcher, value

    def test_genuine_conflicting_source_has_no_accepted_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, context, dispatcher, value = self.prepare(Path(tmp), conflicting=True)
            try:
                processed = process_member(value, context, dispatcher, h.store, h.objects)
                self.assertTrue(processed.result.quarantined)
                self.assertFalse(processed.result.transformed)
                self.assertEqual(processed.result.outcome, 'quarantined')
                self.assertEqual(tuple(h.store.scan('Processing', {})), ())
                self.assertEqual(tuple(h.store.scan('QuarterPublication', {})), ())
                self.assertTrue(any(g.details for g in processed.result.gaps))
            finally:
                h.close()

    def test_member_evidence_rejects_forged_version_ref_quarter_and_outcome(self):
        from dataclasses import replace
        from sec_edgar_ingest.storage.contracts import Conflict
        from sec_edgar_ingest.workflows.processing import validate_member_evidence
        with tempfile.TemporaryDirectory() as tmp:
            h, context, dispatcher, value = self.prepare(Path(tmp))
            try:
                processed = process_member(value, context, dispatcher, h.store, h.objects)
                result = processed.result
                variants = (replace(result, parser_version='fixture-index-parser-v2'),
                            replace(result, snapshot_ref='worksets/sec/snapshot/sha256=' + '0' * 64 + '/workset.json'),
                            replace(result, quarters=()), replace(result, outcome='unchanged'))
                for changed in variants:
                    with self.subTest(changed=changed):
                        with self.assertRaises((Conflict, ValueError, OSError, KeyError)):
                            validate_member_evidence(changed, processed.evidence, h.objects)
            finally:
                h.close()

    def test_member_receipt_is_content_first_and_replays_identically(self):
        from sec_edgar_ingest.workflows.members import WorkflowMembers
        with tempfile.TemporaryDirectory() as tmp:
            h, context, dispatcher, value = self.prepare(Path(tmp))
            try:
                processed = process_member(value, context, dispatcher, h.store, h.objects)
                registry = WorkflowMembers(h.store, h.objects)
                first = registry.record(processed.result, context, processed.evidence)
                retained = h.objects.read(first['ref'])
                self.assertEqual(registry.record(processed.result, context, processed.evidence), first)
                self.assertEqual(h.objects.read(first['ref']), retained)
                self.assertEqual(registry.completed(value, context.parser_version, context.schema_version),
                                 processed.evidence['completion'])
            finally:
                h.close()
```

- [ ] Run guarded `test_workflow_processing.py`; expected missing processing module/API. Preserve exact red. Add a separate conflicting-row pack test with no previous pointer, expecting terminal failed quarantine, zero accepted Processing/observations/pointer, and exact line/raw details in the child evidence.
- [ ] Implement the processing sequence below. T4's repair descriptors are validated immutable documents; a new child uses the original transformed input/settings with a fresh deadline, never alters the expired original. The new child is pinned afresh with the saved effective settings; it keeps the original transformed input and versions while preserving the expired Attempt/command bytes.

```python
from collections.abc import Mapping
from dataclasses import dataclass
from ..config import Settings
from ..models import Error, Record, Source, canonical_json, parse_json, validate_record_fields
from ..state import AcquisitionState
from ..storage.contracts import Conflict, observe
from ..worksets import decode_snapshot_workset
from ..etl.contracts import decode_transformed
from .contracts import COMPLETE, MemberResult
from .checked import ChildUnfinished, read_child_capture
from .completion import evaluate_member, resolve_repair, validate_capture, validate_resolution_capture
from .provenance import read_member, transfer_binding

@dataclass(frozen=True, slots=True)
class ProcessedMember(Record):
    result: MemberResult
    evidence: Mapping[str, object]
    def __post_init__(self):
        validate_record_fields(self)

def process_member(value, context, dispatcher, store, objects, observer=None):
    member = read_member(value, store, objects)
    source = member.members[0]
    origin = Settings.from_mapping(member.context.to_mapping()['effective_config'])
    initial = evaluate_member(value, context.parser_version, context.schema_version, store, objects)
    resolutions, calls, gaps, quarters = [], [], [], ()
    for obligation in initial.obligations:
        objects.verify(obligation['ref'], obligation['sha256'], obligation['bytes'])
        saved = parse_json(objects.read(obligation['ref']))
        old = saved['call']['context']
        settings = Settings.from_mapping(old['effective_config'])
        repaired = dispatcher.execute('publish', 'repair-' + obligation['sha256'], settings,
                                      ('--workset', saved['transformed_ref']))
        calls.append(dict(repaired.call))
        resolutions.append(resolve_repair(obligation, repaired.call, store, objects))
    child_refs, snapshot_ref, transformed_ref = [], None, None
    downloaded = transformed = quarantined = False
    terminal_error = None
    try:
        collected = dispatcher.execute('collect', 'collect-' + value['member_id'], origin,
                                       ('--workset', value['member_ref']))
        calls.append(dict(collected.call)); child_refs.append(collected.result_ref)
        raw = collected.result
        gaps.extend(raw.gaps)
        outcome, snapshot_ref = raw.outcome, raw.snapshot_workset_ref
        quarantined = raw.outcome == 'quarantined' and snapshot_ref is None
        downloaded = snapshot_ref is not None
        if snapshot_ref is not None:
            snapshots = decode_snapshot_workset(objects.read(snapshot_ref))
            if snapshots.source_workset_id != member.workset_id or len(snapshots.snapshots) != 1:
                raise Conflict('collection changed exact singleton source workset')
            transfer_binding(value, snapshots.snapshots[0], store, objects)
        # Collection.quarantined counts failed body retention, not source refusal.
        if snapshot_ref is not None and outcome in COMPLETE:
            parsed = dispatcher.execute('transform', 'transform-' + value['member_id'], dispatcher.settings,
                                        ('--workset', snapshot_ref))
            calls.append(dict(parsed.call)); child_refs.append(parsed.result_ref)
            etl = parsed.result
            gaps.extend(etl.gaps)
            outcome, transformed_ref = etl.outcome, etl.transformed_workset_ref
            transformed = bool(etl.transformed or etl.unchanged)
            quarantined = bool(etl.quarantined) and outcome not in COMPLETE and not transformed
            if outcome in COMPLETE:
                published = dispatcher.execute('publish', 'publish-' + value['member_id'], dispatcher.settings,
                                               ('--workset', transformed_ref))
                calls.append(dict(published.call)); child_refs.append(published.result_ref)
                outcome, quarters = published.result.outcome, published.result.quarters
                gaps.extend(published.result.gaps)
    except ChildUnfinished as error:
        if error.resumable:
            raise  # No member completion/workflow report while publication repair is unfinished.
        calls.append(dict(error.call))
        outcome = error.outcome
        gaps.extend(error.gaps)
        terminal_error = dict(error.details)
    result = MemberResult(value['member_id'], source, value['parent_ref'], snapshot_ref,
        transformed_ref, tuple(child_refs), outcome, downloaded, transformed, quarantined,
        tuple(quarters), tuple(gaps), context.parser_version, context.schema_version)
    evaluated = evaluate_member(value, context.parser_version, context.schema_version, store, objects)
    if result.outcome in COMPLETE and not evaluated.complete:
        raise Conflict('child completion lacks all affected quarter/repair evidence')
    evidence = {'format_version': 'sec-workflow-member-evidence-v1', 'member': dict(value),
        'calls': calls, 'completion': evaluated.capture if result.outcome in COMPLETE else None,
        'resolutions': resolutions, 'terminal_error': terminal_error}
    validate_member_evidence(result, evidence, objects)
    observe(observer, 'workflow.after_member_processing')
    return ProcessedMember(result, evidence)
```

Repair dispatch exceptions occur before the source sequence; they propagate and leave the frozen job resumable. Retain the failed child's exact call/Attempt/error, including all quarter details. A completed immutable failed child requires a new workflow attempt/run for retry.

- [ ] Implement `validate_member_evidence` as the exact authority chain: strict evidence keys/version; member ID/source/original parent match; every successful call via read_child_capture, full deterministic call/ref/input context and saved source/snapshot/transformed codecs; MemberResult flags/outcome/ref/gaps/quarters exactly match the chained child results; terminal_error binds the persisted unfinished call and must never authorize COMPLETE; complete capture via validate_capture names the same member/source/snapshot/current versions, every publication outcome/capture and full affected set; each resolution via validate_resolution_capture. A completed historical capture is checked against immutable manifests, never current pointer equality. Add tampering tables mutating one child ref, snapshot, version, quarter, completion flag, terminal-error correlation or capture digest with matching structural counts; each must refuse before record. This validator must not merely call MemberResult.from_mapping.
- [ ] Persist the canonical member receipt object before its SourceState index. Exact path `runs/sec/<run>/<workflow-command>/<attempt>/members/<member-id>/result.json`; body `{format_version:'sec-workflow-member-receipt-v1',context:...,result:...,evidence:...}`; index key SHA of `[run,command,attempt,member_id,parser_version,schema_version]`, value its SHA/length descriptor plus member/current-version lookup fields. Missing index repairs only from validated immutable object; conflicting index refuses. Interrupted exact replay reads this object before dispatching the member again.
- [ ] Implement registry.completed by reading all exact member/version receipt descriptors, validating canonical bodies and validate_member_evidence, matching the member's immutable binding/snapshot and requested parser/schema, and checking outstanding_repairs is empty. Historical successful receipts discharge only their exact original bound member; fresh refresh/new discovery units are evaluated separately by Task 8. Never borrow success across member IDs/new snapshots/versions. Corrupt receipt is a gap/refusal, not silently skipped. In-progress source operations have no fabricated complete receipt.
- [ ] Run guarded processing tests with origin collection/current parser v2 replay, transport-prefix success, genuine malformed/conflicting source, all child-gap retention, partial Q3/Q4 publication, gate-only state, fatal first member, and expired original/fresh valid repair. Repair proof requires unchanged old Attempt/command/result bytes, completed PublicationReceipt membership and no additional pointer version. Repeat original `test_collection.py`, `test_etl_cli.py` guards. Commit owned paths with `feat: process exact workflow source units through checked commands`; fresh review accepts immutable receipt authority and strict quarantine.


The receipt validator and persistence methods are part of Task 5's implementation step; use this concrete code and retain the tampering regressions above.

```python
def validate_member_evidence(result, evidence, objects):
    from .contracts import member_status
    from ..results import exit_code
    fields = {'format_version', 'member', 'calls', 'completion', 'resolutions', 'terminal_error'}
    if set(evidence) != fields or evidence['format_version'] != 'sec-workflow-member-evidence-v1':
        raise Conflict('member evidence schema differs')
    value = evidence['member']
    if (result.member_id, result.source.to_mapping(), result.parent_ref) != (
            value['member_id'], value['source'], value['parent_ref']):
        raise Conflict('receipt changes registered member/source/parent')
    checked, repair_calls = [], []
    for call in evidence['calls']:
        if call['step_id'].startswith('repair-'):
            repaired = read_child_capture(call, objects)
            if repaired.context.command != 'publish' or repaired.outcome not in COMPLETE:
                raise Conflict('repair prefix is not successful checked publication')
            repair_calls.append(call)
            continue
        try:
            child = read_child_capture(call, objects)
        except FileNotFoundError:
            terminal = evidence['terminal_error']
            if terminal is None or terminal['call'] != call or result.outcome in COMPLETE:
                raise Conflict('missing result cannot authorize completed member')
            continue
        checked.append((call, child))
    if tuple(call['result_ref'] for call, child in checked) != result.child_refs:
        raise Conflict('receipt child result references differ')
    commands = tuple(child.context.command for call, child in checked)
    if commands not in ((), ('collect',), ('collect', 'transform'), ('collect', 'transform', 'publish')):
        raise Conflict('member child order differs')
    expected_gaps = [g.to_mapping() for call, child in checked for g in child.gaps]
    terminal = evidence['terminal_error']
    if terminal is not None:
        expected_gaps.extend(terminal['gaps'])
        exit_code(terminal['outcome'])
        if result.outcome != terminal['outcome']:
            raise Conflict('terminal source outcome differs from exact child failure')
    elif checked and result.outcome != checked[-1][1].outcome:
        raise Conflict('member outcome differs from final checked child')
    if [g.to_mapping() for g in result.gaps] != expected_gaps:
        raise Conflict('member omitted or invented child gaps')
    raw = checked[0][1] if checked else None
    parsed = checked[1][1] if len(checked) >= 2 else None
    published = checked[2][1] if len(checked) >= 3 else None
    if raw is not None and (checked[0][0]['input_ref'] != value['member_ref'] or
            result.snapshot_ref != raw.snapshot_workset_ref or result.downloaded != (raw.snapshot_workset_ref is not None)):
        raise Conflict('member collection/snapshot identity differs')
    if parsed is not None and (parsed.input_ref != result.snapshot_ref or
            parsed.transformed_workset_ref != result.transformed_ref or
            result.transformed != bool(parsed.transformed or parsed.unchanged)):
        raise Conflict('member transform identity/progress differs')
    for child in (parsed, published):
        if child is not None and (child.context.parser_version, child.context.schema_version) != (result.parser_version, result.schema_version):
            raise Conflict('member processing versions differ from exact child context')
    expected_quarantine = bool(parsed and parsed.quarantined and not result.transformed)
    if raw is not None and raw.outcome == 'quarantined' and raw.snapshot_workset_ref is None:
        expected_quarantine = True
    if result.quarantined != expected_quarantine:
        raise Conflict('transport body retention cannot create source quarantine')
    if published is not None and (published.input_ref != result.transformed_ref or published.quarters != result.quarters):
        raise Conflict('member publication input/quarter outcomes differ')
    if published is None and result.quarters:
        raise Conflict('member invents publication outcomes')
    complete = evidence['completion']
    if member_status(result.outcome) == 'complete':
        if complete is None or complete['member'] != value:
            raise Conflict('complete member lacks exact captured evidence')
        validate_capture(complete, objects)
        if (complete['observation']['parser_version'], complete['observation']['schema_version']) != (result.parser_version, result.schema_version):
            raise Conflict('member capture processing versions differ')
        from ..models import Snapshot
        from ..worksets import make_snapshot_workset, decode_source_workset
        projection = decode_source_workset(objects.read(value['member_ref']))
        exact = make_snapshot_workset(projection, (Snapshot.from_mapping(complete['snapshot']),))
        actual = decode_snapshot_workset(objects.read(result.snapshot_ref))
        if exact != actual:
            raise Conflict('member capture differs from exact pinned snapshot workset')
        captures = {c['quarter']: c for c in complete['quarters']}
        if set(captures) != {q.quarter for q in result.quarters}:
            raise Conflict('member omitted affected publication quarter')
        for quarter in result.quarters:
            captured = captures[quarter.quarter]
            if (quarter.generation_id, quarter.manifest_ref) != (captured['generation_id'], captured['manifest_ref']):
                raise Conflict('member quarter differs from immutable capture')
    elif complete is not None:
        raise Conflict('unresolved member invents complete capture')
    if len(evidence['resolutions']) != len(repair_calls):
        raise Conflict('repair prefix lacks exact resolution')
    resolution_calls = []
    for resolution in evidence['resolutions']:
        validate_resolution_capture(resolution, objects)
        objects.verify(resolution['ref'], resolution['sha256'], resolution['bytes'])
        resolution_calls.append(parse_json(objects.read(resolution['ref']))['call'])
    if resolution_calls != repair_calls:
        raise Conflict('repair resolution belongs to another checked prefix')
```

`ChildUnfinished.details` must contain the exact `call`, registered `outcome`, and complete `gaps` mappings. Task 3 defines that structure; this consumer does not parse arbitrary stdout into success. The collection terminal-refusal branch is included in process_member above.

In `workflows/members.py`, import the shipped strict codecs, T2 immutable/read_member, T4 outstanding_repairs/validate_capture and T5 validator. Use content-first receipt storage:

```python
from ..models import to_mapping_value
import hashlib
from .contracts import COMPLETE, MemberResult, workflow_path
from .provenance import immutable, read_member, project_member
from ..models import RunContext, canonical_json, parse_json
from ..storage.contracts import Conflict, observe

class WorkflowMembers:
    def __init__(self, store, objects):
        self.store, self.objects = store, objects

    def inventory(self):
        from ..models import Error
        valid, gaps = [], []
        for row in self.store.scan('WorkflowMember', {}):
            value = row.to_mapping()['value']
            try:
                read_member(value, self.store, self.objects)
                valid.append(value)
            except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
                identity = value.get('member_id') if isinstance(value, dict) else None
                gaps.append(Error('legacy_member_unresolved', str(error), False, None,
                    {'record_kind': 'WorkflowMember', 'member_id': identity,
                     'record_sha256': __import__('hashlib').sha256(canonical_json(to_mapping_value(value))).hexdigest()}))
        return tuple(sorted(valid, key=lambda v: (v['source']['period'], v['source']['source_id'], v['member_id']))), tuple(gaps)

    def all(self):
        values, gaps = self.inventory()
        if gaps:
            raise Conflict('registry contains unresolved corrupt members')
        return values

    def register(self, parent_ref, member_ref):
        from .provenance import read_source
        selected = read_source(member_ref, self.objects)
        if len(selected.members) != 1:
            raise Conflict('registry requires singleton member')
        value = project_member(parent_ref, selected.members[0].source_id, self.store, self.objects)
        if value['member_ref'] != member_ref:
            raise Conflict('registered member differs from exact projection')
        return value

    def record(self, result, context, evidence):
        from .processing import validate_member_evidence
        read_member(evidence['member'], self.store, self.objects)
        validate_member_evidence(result, evidence, self.objects)
        path = workflow_path(context).rsplit('/', 1)[0] + '/members/' + result.member_id + '/result.json'
        value = {'format_version': 'sec-workflow-member-receipt-v1', 'context': context.to_mapping(),
                 'result': result.to_mapping(), 'evidence': dict(evidence)}
        body = canonical_json(to_mapping_value(value))
        self.objects.put_once(path, body)
        self.objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
        key = hashlib.sha256(canonical_json(to_mapping_value([context.run_id, context.command, context.attempt_id,
            result.member_id, result.parser_version, result.schema_version]))).hexdigest()
        index = {'ref': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body),
                 'member_id': result.member_id, 'parser_version': result.parser_version,
                 'schema_version': result.schema_version}
        immutable(self.store, 'WorkflowMemberResult', key, index)
        return index

    def completed(self, value, parser_version, schema_version):
        from .completion import outstanding_repairs, validate_capture
        from .processing import validate_member_evidence
        from ..state import AcquisitionState
        read_member(value, self.store, self.objects)
        if outstanding_repairs(value, self.store, self.objects):
            return None
        candidates = []
        for row in self.store.scan('WorkflowMemberResult', {'member_id': value['member_id'],
                'parser_version': parser_version, 'schema_version': schema_version}):
            descriptor = row.to_mapping()['value']
            self.objects.verify(descriptor['ref'], descriptor['sha256'], descriptor['bytes'])
            body = self.objects.read(descriptor['ref'])
            receipt = parse_json(body)
            if canonical_json(to_mapping_value(receipt)) != body or receipt['format_version'] != 'sec-workflow-member-receipt-v1':
                raise Conflict('member receipt bytes/schema differ')
            result = MemberResult.from_mapping(receipt['result'])
            context = RunContext.from_mapping(receipt['context'])
            expected_path = workflow_path(context).rsplit('/', 1)[0] + '/members/' + result.member_id + '/result.json'
            if descriptor['ref'] != expected_path or receipt['evidence']['member'] != dict(value):
                raise Conflict('member receipt correlation/projection differs')
            validate_member_evidence(result, receipt['evidence'], self.objects)
            if (result.parser_version, result.schema_version) != (parser_version, schema_version):
                raise Conflict('receipt version lookup differs from decoded versions')
            if result.outcome not in COMPLETE:
                continue
            capture = receipt['evidence']['completion']
            binding = AcquisitionState(self.store).binding(value['member_id'], value['source']['source_id'])
            if binding is None or binding.to_mapping() != capture['binding']:
                raise Conflict('historical completed receipt changes immutable raw pin')
            validate_capture(capture, self.objects)
            candidates.append(capture)
        return None if not candidates else sorted(candidates, key=lambda capture: canonical_json(to_mapping_value(capture)))[0]
```

Object-created/index-missing repair is implemented by exact same `record` input from the frozen selection and validated member object, not by scanning unknown object paths. Exact receipt replay reads its deterministic path, validates its original workflow context and evidence, then calls record to repair the index. No broad production storage enumeration is needed.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_processing.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/processing.py packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/members.py packages/sec-edgar-ingest/tests/test_workflow_processing.py
git commit -m "feat: process exact workflow source units through checked commands"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 6: Frozen invocation, selection and report lifecycle

**Interfaces:** `freeze_workflow(context,intent,store,objects)->RunContext`; `freeze_selection(context,selection,store,objects)->Mapping`; `read_workflow_result(ref,store,objects)->WorkflowResult`; `write_workflow_result(result,store,objects,observer=None)->str`; `workflow_key(context)->str`. Consume Tasks 1–5 only; produce the exact frozen selection/report authority for Tasks 8–11.

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py`; create `packages/sec-edgar-ingest/tests/test_workflow_results.py`. Consume T4 historical validators and T3 checked calls; do not depend on runner, CLI, legacy reconstruction or later proof harness.

Selection format is `sec-workflow-selection-v1`, with exact keys (schema notation):

```text
{
    'format_version': 'sec-workflow-selection-v1',
    'context': context.to_mapping(),
    'invocation': frozen_invocation_mapping,
    'members': [registry_value, ...],
    'jobs': [{'member': registry_value, 'aliases': [registry_value]}, ...],
    'member_provenance': [T4_provenance_capture, ...],
    'already_complete': [T4_completion_capture, ...],
    'discovery_call': checked_discovery_call_or_none,
    'discovery_error': Error_mapping_or_none,
    'parent_ref': source_workset_ref_or_none,
    'parent_provenance': T4_parent_capture_or_none,
    'discovery_session': actual_captured_DiscoverySession_or_none,
    'required_units': [exact_frozen_discovery_unit_mapping, ...],
    'halted': bool,
    'requested_quarters': [quarter, ...],
    'directories': [DirectoryOutcome.to_mapping(), ...],
    'boundary_before': str_or_none,
    'gaps': [Error.to_mapping(), ...],
    'discovered_sources': int,
    'unresolved_before': int,
}
```

Each job is a singleton: `job['aliases'] == [job['member']]`. T8 does not delegate completion across aliases. Distinct unbound origins run separately; exact verified Binding reuse prevents extra body acquisition and logical filings. `members` is the complete frozen dispatch/pending union ordered by `(source.period, source.source_id, member_id)`. `already_complete` is disjoint and contains complete evidence captured before dispatch. Selection does not change on interrupted replay, and later active pointers do not invalidate saved captures.

WorkflowResult retains the existing record fields. Its `intent` additionally contains exact `invocation`, `selection` descriptor, `child_calls`, `completion_captures`, `repair_resolutions`, `member_receipts`, `already_complete_sources`, `discovered_sources`, `unresolved_before`. Captured resolution validation is immutable-only; current repair checks happen before finalization in T5. The report cannot finalize while any selected child has an unresolved repair obligation.

Index payload is exact `{context, intent, selection_ref, result_ref}`. Descriptors have exact `{ref,sha256,bytes}`. State is recoverable from canonical intent, selection and report objects. If an existing index contradicts these bytes, refuse; do not overwrite a conflicting descriptor as 'repair'. Missing indexes are reconstructed only from those complete immutable objects. Intent index is begun before intent object commit so its surviving start is available after an early crash; missing index after an intent-object commit is recoverable from the canonical intent's saved context.

- [ ] **Step 1: Add the complete result persistence core and write failing tests against its absent APIs.** Code below is the proposed implementation; the test cycle runs before installing it.

```python
# workflows/results.py
from __future__ import annotations
from ..models import to_mapping_value

import hashlib
from datetime import datetime, timezone

from ..config import Settings, pin_context
from ..models import RunContext, canonical_json, parse_json
from ..storage.contracts import AlreadyExists, CAS_ATTEMPTS, Conflict, observe
from .checked import read_child, read_child_capture, call_ref
from .completion import (validate_capture, validate_resolution_capture,
                         validate_member_provenance)
from .contracts import WorkflowResult, workflow_path
from .provenance import read_member

SELECTION_FORMAT = 'sec-workflow-selection-v1'


def _plain(value):
    return parse_json(canonical_json(to_mapping_value(value)))


def workflow_key(context):
    return hashlib.sha256(canonical_json(to_mapping_value([context.run_id, context.command, context.attempt_id]))).hexdigest()


def _sibling(context, name):
    return workflow_path(context).rsplit('/', 1)[0] + '/' + name


def _read(path, objects):
    body = objects.read(path)
    value = parse_json(body)
    if canonical_json(to_mapping_value(value)) != body:
        raise Conflict('workflow immutable object is not canonical JSON')
    return value, body


def _descriptor(path, body):
    return {'ref': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}


def _match_context(current, saved):
    expected = current.to_mapping()
    expected['started_at'] = saved.started_at.isoformat()
    if expected != saved.to_mapping():
        raise Conflict('workflow exact correlation/config/date/version/deadline differs')
    settings = Settings.from_mapping(saved.to_mapping()['effective_config'])
    if saved.pinned_on is None or pin_context(settings, saved, saved.pinned_on)[0] != saved:
        raise Conflict('workflow saved context is not exactly pinned')


def _index(context, invocation, store, objects):
    key = workflow_key(context)
    expected = {'context': context.to_mapping(), 'intent': _plain(invocation),
                'selection_ref': None, 'result_ref': None}
    for _ in range(CAS_ATTEMPTS):
        row = store.get('WorkflowAttempt', key)
        if row is None:
            try:
                store.insert('WorkflowAttempt', key, expected)
                return expected
            except AlreadyExists:
                continue
        value = row.to_mapping()['value']
        if set(value) != set(expected) or value['context'] != expected['context'] or value['intent'] != expected['intent']:
            raise Conflict('workflow Attempt conflicts with immutable saved intent')
        return value
    raise Conflict('workflow begin exhausted conditional races')


def freeze_workflow(current, intent, store, objects) -> RunContext:
    path = _sibling(current, 'intent.json')
    try:
        frozen, body = _read(path, objects)
    except FileNotFoundError:
        row = store.get('WorkflowAttempt', workflow_key(current))
        saved = current if row is None else RunContext.from_mapping(row.to_mapping()['value']['context'])
        _match_context(current, saved)
        if row is not None and row.to_mapping()['value']['intent'] != _plain(intent):
            raise Conflict('workflow begun intent changed')
        if datetime.now(timezone.utc) >= saved.deadline:
            raise TimeoutError('unfinished workflow deadline expired')
        frozen = {'context': saved.to_mapping(), 'intent': _plain(intent)}
        _index(saved, intent, store, objects)
        body = canonical_json(to_mapping_value(frozen))
        objects.put_once(path, body)
    else:
        if set(frozen) != {'context', 'intent'} or frozen['intent'] != _plain(intent):
            raise Conflict('workflow invocation differs from frozen intent')
        saved = RunContext.from_mapping(frozen['context'])
        _match_context(current, saved)
        if path != _sibling(saved, 'intent.json'):
            raise Conflict('workflow intent path differs')
        _index(saved, intent, store, objects)
    objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
    result_path = workflow_path(saved)
    try:
        objects.read(result_path)
    except FileNotFoundError:
        if datetime.now(timezone.utc) >= saved.deadline:
            raise TimeoutError('unfinished workflow deadline expired')
    else:
        read_workflow_result(result_path, store, objects)
    return saved


def _validate_selection(selection, context, invocation, store, objects):
    from ..models import DirectoryOutcome, Error
    from ..discovery import quarter_span
    from .checked import _authority
    from .completion import validate_parent_provenance, validate_discovery_session
    fields = {'format_version', 'context', 'invocation', 'members', 'jobs',
              'member_provenance', 'already_complete', 'discovery_call',
              'discovery_error', 'parent_ref', 'parent_provenance', 'discovery_session',
              'required_units', 'halted', 'requested_quarters', 'directories',
              'boundary_before', 'gaps', 'discovered_sources', 'unresolved_before'}
    selection = _plain(selection)
    if set(selection) != fields or selection['format_version'] != SELECTION_FORMAT or selection['context'] != context.to_mapping() or selection['invocation'] != _plain(invocation):
        raise Conflict('selection differs from frozen workflow intent')
    members = selection['members']
    keys = [(v['source']['period'], v['source']['source_id'], v['member_id']) for v in members]
    if keys != sorted(keys) or len({v['member_id'] for v in members}) != len(members):
        raise Conflict('selection member ordering/identity differs')
    jobs = selection['jobs']
    if [job['member'] for job in jobs] != members or any(set(job) != {'member', 'aliases'} or job['aliases'] != [job['member']] for job in jobs):
        raise Conflict('selection jobs must be canonical singleton member jobs')
    provenance = selection['member_provenance']
    if [e['member'] for e in provenance] != members:
        raise Conflict('selection member provenance coverage differs')
    for evidence in provenance:
        validate_member_provenance(evidence, objects)
    completed = selection['already_complete']
    for capture in completed:
        validate_capture(capture, objects)
        if (capture['observation']['parser_version'], capture['observation']['schema_version']) != (context.parser_version, context.schema_version):
            raise Conflict('skipped completion capture differs from pinned processing versions')
    completed_ids = [c['member']['member_id'] for c in completed]
    if len(set(completed_ids)) != len(completed_ids) or {v['member_id'] for v in members} & set(completed_ids):
        raise Conflict('selection completed captures overlap or duplicate members')
    if type(selection['halted']) is not bool:
        raise Conflict('selection halted marker is not boolean')
    for value in selection['directories']:
        DirectoryOutcome.from_mapping(value)
    for value in selection['gaps']:
        Error.from_mapping(value)
    error = selection['discovery_error']
    if error is not None:
        Error.from_mapping(error)
    call = selection['discovery_call']
    template = None
    discovery = None
    if call is not None:
        call, template = _authority(call, None, objects)
        if template.command != 'discover' or call['workflow_command'] != context.command or call['workflow_attempt_id'] != context.attempt_id or template.run_id != context.run_id:
            raise Conflict('selection discovery call belongs to another workflow')
        try:
            discovery = read_child_capture(call, objects)
        except FileNotFoundError:
            pass
    session = selection['discovery_session']
    units = selection['required_units']
    if not isinstance(units, list) or len({unit['url'] for unit in units}) != len(units):
        raise Conflict('selection required-directory ledger duplicates or changes type')
    if session is None:
        if units:
            raise Conflict('selection required units lack an actual captured discovery session')
    else:
        origin = validate_discovery_session(session)
        if units != session['frozen']['units']:
            raise Conflict('selection exact required-directory ledger differs from frozen session')
        expected_id = (call['intent']['discovery_id'] if call is not None
                       else 'workflow-' + context.command + '-' + context.run_id)
        expected_mode = 'daily' if context.command == 'daily' else 'quarterly'
        if session['discovery_id'] != expected_id or session['frozen']['mode'] != expected_mode:
            raise Conflict('selection captured session identity or discovery mode differs')
        current = template if template is not None else context
        for field in ('run_id', 'image_digest', 'parser_version', 'schema_version', 'config_sha256', 'effective_config'):
            if getattr(origin, field) != getattr(current, field):
                raise Conflict('selection discovery session differs from current frozen run provenance')
        if origin.pinned_on != context.pinned_on or session['frozen']['end'] != invocation['pinned_end_quarter']:
            raise Conflict('selection discovery session has stale date or endpoint; use a fresh run')
        if call is not None:
            mode = 'refresh' if call['intent']['refresh'] else 'reuse_accepted'
            if session['frozen']['acquisition_mode'] != mode:
                raise Conflict('selection discovery acquisition mode differs from checked call')
    parent_ref = selection['parent_ref']
    proof = selection['parent_provenance']
    if parent_ref is None:
        if proof is not None or selection['directories'] or error is None or not selection['halted']:
            raise Conflict('absent parent requires halted/error evidence and no claimed directory coverage')
        if discovery is not None and discovery.source_workset_ref is not None:
            raise Conflict('selection omits a durable discovery parent')
    else:
        if call is None or discovery is None or discovery.source_workset_ref != parent_ref or proof is None or session is None:
            raise Conflict('selection parent lacks checked discovery and complete captured provenance')
        parent = validate_parent_provenance(proof, objects)
        if proof['parent_ref'] != parent_ref or proof['discovery']['session'] != session:
            raise Conflict('selection parent/session capture differs from exact discovery authority')
        if parent.discovery_id != call['intent']['discovery_id'] or parent.context.pinned_on != context.pinned_on or parent.pinned_end_quarter != invocation['pinned_end_quarter']:
            raise Conflict('selection parent changes discovery identity/current date/endpoint')
        if [d.to_mapping() for d in parent.directories] != selection['directories']:
            raise Conflict('selection directory outcomes differ from exact captured parent')
        if {unit['url'] for unit in units} != {d.url for d in parent.directories}:
            raise Conflict('selection omits a frozen required directory')
    settings = Settings.from_mapping(context.to_mapping()['effective_config'])
    expected_requested = ([] if context.command == 'daily'
                          else list(quarter_span(settings.backfill.start_quarter, invocation['pinned_end_quarter'])))
    if selection['requested_quarters'] != expected_requested:
        raise Conflict('selection requested baseline units differ from pinned inclusive endpoints')
    for name in ('discovered_sources', 'unresolved_before'):
        if type(selection[name]) is not int or selection[name] < 0:
            raise Conflict('selection source-unit count is invalid')


def _repair_index_descriptor(context, field, descriptor, store):
    key = workflow_key(context)
    for _ in range(CAS_ATTEMPTS):
        row = store.get('WorkflowAttempt', key)
        if row is None:
            raise Conflict('workflow index vanished during descriptor repair')
        value = row.to_mapping()['value']
        if value['context'] != context.to_mapping():
            raise Conflict('workflow descriptor repair context differs')
        if value[field] is not None:
            if value[field] != descriptor:
                raise Conflict('workflow index descriptor conflicts with immutable authority')
            return
        value[field] = descriptor
        try:
            store.replace('WorkflowAttempt', key, value, row.version)
            return
        except Conflict:
            continue
    raise Conflict('workflow descriptor repair exhausted conditional races')


def freeze_selection(context, selection, store, objects):
    invocation, _ = _read(_sibling(context, 'intent.json'), objects)
    if invocation['context'] != context.to_mapping():
        raise Conflict('selection has no exact begun workflow intent')
    _index(context, invocation['intent'], store, objects)
    selection = _plain(selection)
    _validate_selection(selection, context, invocation['intent'], store, objects)
    path = _sibling(context, 'selection.json')
    body = canonical_json(to_mapping_value(selection))
    objects.put_once(path, body)
    objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
    if objects.read(path) != body:
        raise Conflict('frozen selection differs from exact proposed selection')
    _repair_index_descriptor(context, 'selection_ref', _descriptor(path, body), store)
    return _plain(selection)


def _validate_report(result, store, objects):
    from ..worksets import decode_source_workset
    context = result.context
    intent_fields = {'invocation', 'selection', 'child_calls', 'completion_captures',
                     'repair_resolutions', 'member_receipts', 'already_complete_sources',
                     'discovered_sources', 'unresolved_before'}
    if set(result.intent) != intent_fields:
        raise Conflict('workflow report intent schema differs')
    frozen, _ = _read(_sibling(context, 'intent.json'), objects)
    if frozen != {'context': context.to_mapping(), 'intent': _plain(result.intent['invocation'])}:
        raise Conflict('report differs from immutable invocation/context')
    selection, selection_body = _read(_sibling(context, 'selection.json'), objects)
    _validate_selection(selection, context, frozen['intent'], store, objects)
    expected_descriptor = _descriptor(_sibling(context, 'selection.json'), selection_body)
    if _plain(result.intent['selection']) != expected_descriptor:
        raise Conflict('report frozen-selection descriptor differs')
    _index(context, frozen['intent'], store, objects)
    row = store.get('WorkflowAttempt', workflow_key(context))
    value = row.to_mapping()['value']
    if value['selection_ref'] is not None and value['selection_ref'] != expected_descriptor:
        raise Conflict('report/index selection descriptor differs')
    if result.source_workset_ref != selection['parent_ref']:
        raise Conflict('report source workset differs from frozen discovery')
    if result.requested_quarters != tuple(selection['requested_quarters']) or result.to_mapping()['directories'] != selection['directories'] or result.boundary_before != selection['boundary_before']:
        raise Conflict('report coverage ledger differs from frozen selection')
    for name in ('discovered_sources', 'unresolved_before'):
        if result.intent[name] != selection[name]:
            raise Conflict('report source-unit count differs from frozen selection')
    completed = selection['already_complete']
    selected_source_ids = {m.source.source_id for m in result.members}
    already = sorted({c['member']['source']['source_id'] for c in completed} - selected_source_ids)
    if sorted(result.intent['already_complete_sources']) != already:
        raise Conflict('report skipped-source count lacks exact before-dispatch captures')
    captures = [_plain(c) for c in result.intent['completion_captures']]
    for capture in captures:
        validate_capture(capture, objects)
    for capture in completed:
        if capture not in captures:
            raise Conflict('report omitted skipped-source immutable capture')
    by_member = {c['member']['member_id']: c for c in captures}
    complete_ids = {m.member_id for m in result.members if m.outcome in ('success', 'unchanged', 'no_new_sources')}
    expected_capture_ids = complete_ids | {c['member']['member_id'] for c in completed}
    if len(by_member) != len(captures) or set(by_member) != expected_capture_ids:
        raise Conflict('report contains orphan/duplicate completion captures')
    selected = {v['member_id']: v for v in selection['members']}
    if [m.member_id for m in result.members] != list(selected):
        raise Conflict('report does not account for every frozen selected member')
    receipts = result.intent['member_receipts']
    if len(receipts) != len(result.members):
        raise Conflict('report member receipt coverage differs')
    allowed_unfinished, receipt_calls, receipt_completions, receipt_resolutions = [], [], [], []
    from .processing import validate_member_evidence
    from .contracts import PENDING
    for member, descriptor in zip(result.members, receipts):
        if descriptor is None:
            if member.child_refs or member.outcome not in PENDING:
                raise Conflict('only undispatched pending member may lack receipt')
            continue
        objects.verify(descriptor['ref'], descriptor['sha256'], descriptor['bytes'])
        receipt, receipt_body = _read(descriptor['ref'], objects)
        expected_path = _sibling(context, 'members/' + member.member_id + '/result.json')
        if (set(receipt) != {'format_version', 'context', 'result', 'evidence'}
                or receipt['format_version'] != 'sec-workflow-member-receipt-v1'
                or descriptor['ref'] != expected_path or receipt['context'] != context.to_mapping()
                or receipt['result'] != member.to_mapping()
                or descriptor['member_id'] != member.member_id
                or descriptor['parser_version'] != member.parser_version
                or descriptor['schema_version'] != member.schema_version
                or receipt['evidence']['member'] != selected[member.member_id]):
            raise Conflict('report member receipt identity/context differs')
        evidence = receipt['evidence']
        validate_member_evidence(member, evidence, objects)
        receipt_calls.extend(evidence['calls'])
        if evidence['completion'] is not None:
            receipt_completions.append(evidence['completion'])
        receipt_resolutions.extend(evidence['resolutions'])
        terminal = evidence['terminal_error']
        if terminal is not None:
            if terminal.get('repair_pending') or terminal['call']['context']['command'] == 'publish':
                raise Conflict('workflow report cannot finalize unfinished publication repair')
            allowed_unfinished.append(terminal['call'])
    expected_calls = receipt_calls + ([] if selection['discovery_call'] is None else [selection['discovery_call']])
    if {canonical_json(to_mapping_value(call)) for call in expected_calls} != {canonical_json(to_mapping_value(call)) for call in result.intent['child_calls']}:
        raise Conflict('report child calls differ from exact member receipts/discovery')
    if {canonical_json(to_mapping_value(c)) for c in completed + receipt_completions} != {canonical_json(to_mapping_value(c)) for c in result.intent['completion_captures']}:
        raise Conflict('report completion evidence differs from exact receipts/selection')
    if {canonical_json(to_mapping_value(r)) for r in receipt_resolutions} != {canonical_json(to_mapping_value(r)) for r in result.intent['repair_resolutions']}:
        raise Conflict('report repair resolutions differ from member receipts')
    calls = {_plain(c)['result_ref']: _plain(c) for c in result.intent['child_calls']}
    if len(calls) != len(result.intent['child_calls']):
        raise Conflict('report contains duplicate child calls')
    durable = {}
    for ref, call in calls.items():
        try:
            durable[ref] = read_child_capture(call, objects)
        except FileNotFoundError:
            failed_discovery = call == selection['discovery_call'] and selection['halted'] and selection['discovery_error'] is not None
            if not failed_discovery and call not in allowed_unfinished:
                raise Conflict('report contains unaccounted unfinished child')
    if selection['discovery_call'] is not None and selection['discovery_call'] not in list(calls.values()):
        raise Conflict('report omitted frozen discovery child')
    for member in result.members:
        if member.source.to_mapping() != selected[member.member_id]['source'] or member.parent_ref != selected[member.member_id]['parent_ref']:
            raise Conflict('report member provenance differs from selection')
        if (member.parser_version, member.schema_version) != (context.parser_version, context.schema_version):
            raise Conflict('report member versions differ from current pinned workflow')
        if member.snapshot_ref is not None:
            from ..worksets import decode_snapshot_workset
            snapshot_set = decode_snapshot_workset(objects.read(member.snapshot_ref))
            if snapshot_set.source_workset_id != selected[member.member_id]['member_id']:
                raise Conflict('report snapshot belongs to another original member alias')
        children = []
        for ref in member.child_refs:
            if ref not in durable:
                raise Conflict('report member lacks exact checked child result')
            children.append(durable[ref])
        by_command = {child.context.command: child for child in children}
        if len(by_command) != len(children):
            raise Conflict('report member repeats a child command')
        if 'collect' in by_command and by_command['collect'].snapshot_workset_ref != member.snapshot_ref:
            raise Conflict('member snapshot reference differs from collection child')
        if 'transform' in by_command:
            transform = by_command['transform']
            if transform.input_ref != member.snapshot_ref or transform.transformed_workset_ref != member.transformed_ref:
                raise Conflict('member transform chain differs')
        if 'publish' in by_command:
            publication = by_command['publish']
            if publication.input_ref != member.transformed_ref or publication.quarters != member.quarters:
                raise Conflict('member publication chain differs')
        if member.outcome in ('success', 'unchanged', 'no_new_sources'):
            if member.member_id not in by_member or 'publish' not in by_command:
                raise Conflict('complete member lacks child and immutable completion evidence')
            capture = by_member[member.member_id]
            from ..worksets import make_snapshot_workset
            from ..models import Snapshot
            projection = decode_source_workset(objects.read(selected[member.member_id]['member_ref']))
            if make_snapshot_workset(projection, (Snapshot.from_mapping(capture['snapshot']),)) != snapshot_set:
                raise Conflict('complete member snapshot capture differs from exact child input')
            if capture['member'] != selected[member.member_id] or (capture['observation']['parser_version'], capture['observation']['schema_version']) != (member.parser_version, member.schema_version):
                raise Conflict('complete member evidence/version differs')
            if set(capture['affected_quarters']) != {q.quarter for q in member.quarters}:
                raise Conflict('complete member report omitted an affected quarter')
            captured_quarters = {q['quarter']: q for q in capture['quarters']}
            for quarter in member.quarters:
                proof = captured_quarters[quarter.quarter]
                if (quarter.generation_id, quarter.manifest_ref) != (proof['generation_id'], proof['manifest_ref']):
                    raise Conflict('complete member capture differs from exact publish child')
        for child in children:
            if child.context.command in ('transform', 'publish') and (child.context.parser_version, child.context.schema_version) != (member.parser_version, member.schema_version):
                raise Conflict('member processing child uses another pinned version')
        child_gaps = [gap.to_mapping() for child in children for gap in child.gaps]
        member_gaps = [gap.to_mapping() for gap in member.gaps]
        if any(gap not in member_gaps for gap in child_gaps):
            raise Conflict('member omitted retained child error evidence')
    for gap in selection['gaps']:
        if gap not in [g.to_mapping() for g in result.gaps]:
            raise Conflict('report omitted frozen discovery/selection gap')
    from .contracts import summarize
    outcome, counts = summarize(result.members, result.gaps, result.intent['discovered_sources'],
                                result.intent['unresolved_before'], context.command,
                                tuple(result.intent['already_complete_sources']))
    if result.outcome != outcome or result.to_mapping()['counts'] != counts:
        raise Conflict('report outcome/counts differ from checked source evidence')
    for resolution in result.intent['repair_resolutions']:
        validate_resolution_capture(resolution, objects)
    return selection, expected_descriptor


def read_workflow_result(path, store, objects) -> WorkflowResult:
    mapping, body = _read(path, objects)
    result = WorkflowResult.from_mapping(mapping)
    if workflow_path(result.context) != path:
        raise Conflict('workflow report path differs from canonical command identity')
    selection, selection_descriptor = _validate_report(result, store, objects)
    descriptor = _descriptor(path, body)
    _repair_index_descriptor(result.context, 'selection_ref', selection_descriptor, store)
    _repair_index_descriptor(result.context, 'result_ref', descriptor, store)
    return result


def write_workflow_result(result, store, objects, observer=None) -> str:
    path = workflow_path(result.context)
    _validate_report(result, store, objects)
    # The deadline stops child work; final validated accounting of pending work
    # may be committed by an invocation that already began before the deadline.
    body = canonical_json(to_mapping_value(result.to_mapping()))
    objects.put_once(path, body)
    objects.verify(path, hashlib.sha256(body).hexdigest(), len(body))
    observe(observer, 'workflow.after_report_object')
    read_workflow_result(path, store, objects)
    observe(observer, 'workflow.after_attempt_finish')
    return path
```


Tests (complete code, real local stores and actual checked discovery/transform/publish):

```python
# tests/test_workflow_results.py
import hashlib
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from support import CollectionCrash, store_bundle
from support_workflow_evidence import EvidenceFixture, quarterly_bytes
from sec_edgar_ingest.etl.reader import read_quarter
from sec_edgar_ingest.etl.contracts import GenerationCapture
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.models import Error, Source, canonical_json
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.storage.contracts import Conflict, OwnershipLost, identity, table_for
from sec_edgar_ingest.worksets import decode_source_workset
from sec_edgar_ingest.workflows.checked import Dispatcher, ChildUnfinished
from sec_edgar_ingest.workflows.completion import (
    capture_member_provenance, capture_parent_provenance, validate_parent_provenance, evaluate_member,
)
from sec_edgar_ingest.workflows.contracts import (
    FORMAT_VERSION, MemberResult, WorkflowResult, summarize, workflow_path,
)
from sec_edgar_ingest.workflows.results import (
    freeze_workflow, freeze_selection, read_workflow_result,
    write_workflow_result, workflow_key,
)


class WorkflowResultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.f = EvidenceFixture(Path(self.temp.name) / '.fixture-state', command='backfill')
        self.addCleanup(self.f.close)
        self.invocation = {'command': 'backfill', 'today': '2026-10-06',
                           'fixture_sha256': hashlib.sha256(self.f.pack.read_bytes()).hexdigest(),
                           'pinned_end_quarter': '2026Q4'}
        self.context = freeze_workflow(self.f.workflow, self.invocation,
                                       self.f.store, self.f.objects)
        self.f.snapshot_input(quarterly_bytes('2026-07-01'))
        _, self.collect_call, collected = self.f.invoke('collect', self.f.value['member_ref'])
        snapshot_ref = collected.snapshot_workset_ref
        _, self.transform_call, transformed = self.f.invoke('transform', snapshot_ref)
        _, self.publish_call, self.published = self.f.invoke('publish', transformed.transformed_workset_ref)
        self.snapshot_ref = snapshot_ref
        self.transformed_ref = transformed.transformed_workset_ref
        self.capture = evaluate_member(self.f.value, self.context.parser_version,
            self.context.schema_version, self.f.store, self.f.objects).capture
        self.assertIsNotNone(self.capture)
        self.baseline_gap = Error('baseline_publication_missing',
            'valid empty Q4 listing remains an unresolved baseline unit', False, None,
            {'quarter': '2026Q4', 'coverage_cause': 'missing_source', 'source_ids': []})

    def selection(self, *, skipped=False):
        parent = decode_source_workset(self.f.objects.read(self.f.parent_ref))
        session = AcquisitionState(self.f.store).discovery_session(parent.discovery_id).to_mapping()['value']
        members = [] if skipped else [self.f.value]
        parent_provenance = capture_parent_provenance(self.f.parent_ref, self.f.store, self.f.objects)
        return {'format_version': 'sec-workflow-selection-v1',
                'context': self.context.to_mapping(), 'invocation': self.invocation,
                'members': members,
                'jobs': [{'member': value, 'aliases': [value]} for value in members],
                'member_provenance': [capture_member_provenance(value, self.f.store, self.f.objects)
                                      for value in members],
                'already_complete': [self.capture] if skipped else [],
                'discovery_call': self.f.discovery_call, 'discovery_error': None,
                'parent_ref': self.f.parent_ref,
                'parent_provenance': parent_provenance,
                'discovery_session': session,
                'required_units': session['frozen']['units'],
                'halted': False, 'requested_quarters': ['2026Q3', '2026Q4'],
                'directories': [d.to_mapping() for d in parent.directories],
                'boundary_before': None, 'gaps': [self.baseline_gap.to_mapping()],
                'discovered_sources': 1, 'unresolved_before': 0}

    def report(self, *, skipped=False):
        selection = freeze_selection(self.context, self.selection(skipped=skipped),
                                     self.f.store, self.f.objects)
        selection_path = workflow_path(self.context).rsplit('/', 1)[0] + '/selection.json'
        body = self.f.objects.read(selection_path)
        descriptor = {'ref': selection_path, 'sha256': hashlib.sha256(body).hexdigest(),
                      'bytes': len(body)}
        members = () if skipped else (MemberResult(
            self.f.value['member_id'], Source.from_mapping(self.f.value['source']),
            self.f.value['parent_ref'], self.snapshot_ref, self.transformed_ref,
            (self.collect_call['result_ref'], self.transform_call['result_ref'], self.publish_call['result_ref']),
            self.published.outcome, True, True, False, self.published.quarters, (),
            self.context.parser_version, self.context.schema_version),)
        already = (self.f.source.source_id,) if skipped else ()
        gaps = (self.baseline_gap,)
        outcome, counts = summarize(members, gaps, 1, 0, self.context.command, already)
        from sec_edgar_ingest.workflows.members import WorkflowMembers
        receipts = []
        if members:
            evidence = {'format_version': 'sec-workflow-member-evidence-v1', 'member': self.f.value,
                        'calls': [self.collect_call, self.transform_call, self.publish_call],
                        'completion': self.capture, 'resolutions': [], 'terminal_error': None}
            receipts.append(WorkflowMembers(self.f.store, self.f.objects).record(members[0], self.context, evidence))
        intent = {'invocation': self.invocation, 'selection': descriptor,
                  'member_receipts': receipts,
                  'child_calls': [self.f.discovery_call] + ([] if skipped else
                                  [self.collect_call, self.transform_call, self.publish_call]),
                  'completion_captures': [self.capture], 'repair_resolutions': [],
                  'already_complete_sources': list(already),
                  'discovered_sources': 1, 'unresolved_before': 0}
        return WorkflowResult(FORMAT_VERSION, self.context, intent, self.f.parent_ref,
            ('2026Q3', '2026Q4'), tuple(selection['directories']), members, gaps,
            None, None, outcome, counts, self.published.ended_at.isoformat())

    def delete_index(self, kind, key):
        # Test-only isolated corruption. Production has no state deletion API.
        partition, _ = identity(kind, key)
        with sqlite3.connect(self.f.store.database) as db:
            db.execute('DELETE FROM records WHERE table_name=? AND partition=? AND key=?',
                       (table_for(kind), partition, key))
            db.commit()

    def test_historical_report_reads_original_capture_after_pointer_advance(self):
        report = self.report()
        path = write_workflow_result(report, self.f.store, self.f.objects)
        before = self.f.objects.read(path)
        self.f.revised_member()
        snapshot = self.f.snapshot_input(quarterly_bytes('2026-07-01', 'Changed'), seconds=1)
        _, _, transformed = self.f.invoke('transform', snapshot)
        self.f.invoke('publish', transformed.transformed_workset_ref)
        reread = read_workflow_result(path, self.f.store, self.f.objects)
        self.assertEqual(reread, report)
        self.assertEqual(self.f.objects.read(path), before)
        capture = GenerationCapture.from_mapping(self.capture['quarters'][0])
        self.assertEqual(list(read_quarter(capture, self.f.objects))[0].company_name, 'A')
        self.assertNotEqual(capture.generation_id, EtlState(self.f.store).pointer('2026Q3').value['generation_id'])

    def test_report_object_crash_reopens_and_repairs_exact_index(self):
        report = self.report()
        pointers = [r.to_mapping() for r in self.f.store.scan('QuarterPublication', {})]
        def crash(point):
            if point == 'workflow.after_report_object':
                raise CollectionCrash()
        with self.assertRaises(CollectionCrash):
            write_workflow_result(report, self.f.store, self.f.objects, crash)
        path = workflow_path(report.context)
        body = self.f.objects.read(path)
        self.assertIsNone(self.f.store.get('WorkflowAttempt', workflow_key(self.context)).value['result_ref'])
        self.f.close()
        store, objects, leases = store_bundle(self.f.root)
        self.addCleanup(store.close)
        self.addCleanup(leases.close)
        with patch('sec_edgar_ingest.cli.BoundedSender', side_effect=AssertionError('report replay sender')):
            self.assertEqual(read_workflow_result(path, store, objects), report)
        self.assertEqual(objects.read(path), body)
        self.assertEqual([r.to_mapping() for r in store.scan('QuarterPublication', {})], pointers)
        self.assertEqual(store.get('WorkflowAttempt', workflow_key(self.context)).value['result_ref']['sha256'],
                         hashlib.sha256(body).hexdigest())

    def test_missing_workflow_and_child_indexes_recover_from_immutable_authority(self):
        from sec_edgar_ingest.workflows.checked import call_key
        report = self.report()
        path = write_workflow_result(report, self.f.store, self.f.objects)
        expected = self.f.store.get('WorkflowAttempt', workflow_key(self.context)).to_mapping()['value']
        self.delete_index('WorkflowAttempt', workflow_key(self.context))
        for call in (self.f.discovery_call, self.collect_call, self.transform_call, self.publish_call):
            self.delete_index('WorkflowChildCall', call_key(call))
        self.assertEqual(read_workflow_result(path, self.f.store, self.f.objects), report)
        self.assertEqual(self.f.store.get('WorkflowAttempt', workflow_key(self.context)).to_mapping()['value'], expected)

    def test_existing_conflicting_report_index_refuses(self):
        report = self.report()
        path = write_workflow_result(report, self.f.store, self.f.objects)
        key = workflow_key(self.context)
        row = self.f.store.get('WorkflowAttempt', key)
        original = row.to_mapping()['value']
        for name, replacement in [('context', {**original['context'], 'execution_id': 'different'}),
                                  ('intent', {**original['intent'], 'today': '2026-10-07'}),
                                  ('selection_ref', {**original['selection_ref'], 'bytes': 1}),
                                  ('result_ref', {**original['result_ref'], 'sha256': 'f' * 64})]:
            current = self.f.store.get('WorkflowAttempt', key)
            bad = {**original, name: replacement}
            self.f.store.replace('WorkflowAttempt', key, bad, current.version)
            with self.subTest(name=name), self.assertRaises(Conflict):
                read_workflow_result(path, self.f.store, self.f.objects)
            current = self.f.store.get('WorkflowAttempt', key)
            self.f.store.replace('WorkflowAttempt', key, original, current.version)

    def test_exact_replay_after_deadline_and_changed_invocation_refusal(self):
        report = self.report()
        path = write_workflow_result(report, self.f.store, self.f.objects)
        after = self.context.deadline + timedelta(seconds=1)
        with patch('sec_edgar_ingest.workflows.results.datetime') as clock:
            clock.now.return_value = after
            self.assertEqual(freeze_workflow(self.context, self.invocation, self.f.store, self.f.objects), self.context)
        before = self.f.objects.read(path)
        changes = {'execution_id': 'other', 'image_digest': 'sha256:' + 'f' * 64,
                   'parser_version': 'fixture-index-parser-v2',
                   'deadline': self.context.deadline + timedelta(seconds=1)}
        for field, value in changes.items():
            with self.subTest(field=field), self.assertRaises((Conflict, ValueError)):
                freeze_workflow(replace(self.context, **{field: value}), self.invocation,
                                self.f.store, self.f.objects)
        with self.assertRaises(Conflict):
            freeze_workflow(self.context, {**self.invocation, 'fixture_sha256': 'f' * 64},
                            self.f.store, self.f.objects)
        self.assertEqual(self.f.objects.read(path), before)
        fresh = replace(self.context, attempt_id='unfinished-expired')
        with patch('sec_edgar_ingest.workflows.results.datetime') as clock:
            clock.now.return_value = after
            with self.assertRaises(TimeoutError):
                freeze_workflow(fresh, self.invocation, self.f.store, self.f.objects)

    def test_skipped_before_dispatch_capture_is_required_and_counted_once(self):
        report = self.report(skipped=True)
        self.assertEqual(report.counts['complete_sources'], 1)
        self.assertEqual(report.counts['failed_sources'], 0)
        path = write_workflow_result(report, self.f.store, self.f.objects)
        changed = replace(report, intent={**report.to_mapping()['intent'], 'completion_captures': []})
        with self.assertRaises(Conflict):
            write_workflow_result(changed, self.f.store, self.f.objects)
        self.assertEqual(read_workflow_result(path, self.f.store, self.f.objects), report)

    def test_selection_substitution_and_missing_evidence_refuse(self):
        selection = self.selection()
        freeze_selection(self.context, selection, self.f.store, self.f.objects)
        changed = {**selection, 'jobs': []}
        with self.assertRaises(Conflict):
            freeze_selection(self.context, changed, self.f.store, self.f.objects)
        report = self.report()
        corrupted = replace(report, intent={**report.to_mapping()['intent'],
                                           'child_calls': [self.f.discovery_call, self.transform_call]})
        with self.assertRaises(Conflict):
            write_workflow_result(corrupted, self.f.store, self.f.objects)
        capture = self.capture['quarters'][0]
        target = self.f.root / 'objects' / capture['manifest_ref']
        body = target.read_bytes()
        target.write_bytes(body[:-1])
        with self.assertRaises((Conflict, ValueError, FileNotFoundError)):
            write_workflow_result(report, self.f.store, self.f.objects)
        target.write_bytes(body)

    def test_fatal_discovery_without_result_preserves_frozen_prior_jobs(self):
        dispatcher = Dispatcher(self.context, self.f.settings, self.f.pack,
                                self.f.root.parent, self.f.store, self.f.objects)
        with patch('sec_edgar_ingest.cli.discover', side_effect=OwnershipLost('fatal discovery ownership')):
            with self.assertRaises(ChildUnfinished) as failed:
                dispatcher.execute('discover', 'fatal-discovery', self.f.settings,
                                   ('--mode', 'quarterly', '--discovery-id', 'fatal-discovery-session'))
        error = Error(failed.exception.outcome, 'discovery has no durable source result',
                      False, None, failed.exception.details)
        selection = self.selection()
        selection.update(discovery_call=failed.exception.call, discovery_error=error.to_mapping(),
                         parent_ref=None, parent_provenance=None, discovery_session=None,
                         required_units=[], directories=[], halted=True,
                         gaps=[error.to_mapping()], discovered_sources=0, unresolved_before=1)
        freeze_selection(self.context, selection, self.f.store, self.f.objects)
        path = workflow_path(self.context).rsplit('/', 1)[0] + '/selection.json'
        body = self.f.objects.read(path)
        descriptor = {'ref': path, 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)}
        member = MemberResult(self.f.value['member_id'], self.f.source, self.f.value['parent_ref'],
                              None, None, (), 'pending', False, False, False, (), (),
                              self.context.parser_version, self.context.schema_version)
        outcome, counts = summarize((member,), (error,), 0, 1, 'backfill', ())
        intent = {'invocation': self.invocation, 'selection': descriptor,
                  'member_receipts': [None],
                  'child_calls': [failed.exception.call], 'completion_captures': [],
                  'repair_resolutions': [], 'already_complete_sources': [],
                  'discovered_sources': 0, 'unresolved_before': 1}
        result = WorkflowResult(FORMAT_VERSION, self.context, intent, None,
            ('2026Q3', '2026Q4'), (), (member,), (error,), None, None,
            outcome, counts, self.published.ended_at.isoformat())
        result_path = write_workflow_result(result, self.f.store, self.f.objects)
        self.assertEqual(read_workflow_result(result_path, self.f.store, self.f.objects), result)
        self.assertEqual(result.outcome, 'ownership_lost')
        self.assertEqual(result.counts['pending_sources'], 1)

    def test_parent_capture_retains_full_empty_discovery_authority(self):
        from support_workflows import simple_pack, CommandHarness
        from sec_edgar_ingest.workflows.checked import Dispatcher
        from sec_edgar_ingest.workflows.completion import capture_parent_provenance, validate_parent_provenance
        from sec_edgar_ingest.config import pin_context
        from datetime import date, datetime, timedelta, timezone
        from sec_edgar_ingest.models import RunContext
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root, empty=True))
            try:
                now = datetime.now(timezone.utc)
                context = RunContext('empty-parent-workflow', 'empty-parent-execution', 'backfill', 'empty-parent-attempt',
                    h.settings.worker.image_digest, h.settings.etl.parser_version, h.settings.etl.schema_version,
                    h.settings.config_sha256, now, now + timedelta(seconds=1800), 'backfill')
                context = pin_context(h.settings, context, date(2026, 10, 7))[0]
                invocation = {'command': 'backfill', 'today': '2026-10-07',
                              'fixture_sha256': hashlib.sha256(h.pack.read_bytes()).hexdigest(),
                              'pinned_end_quarter': '2026Q4'}
                context = freeze_workflow(context, invocation, h.store, h.objects)
                dispatcher = Dispatcher(context, h.settings, h.pack, h.root, h.store, h.objects)
                child = dispatcher.execute('discover', 'empty-discovery', h.settings,
                    ('--mode', 'quarterly', '--discovery-id', 'empty-parent-session'))
                proof = capture_parent_provenance(child.result.source_workset_ref, h.store, h.objects)
                parent = validate_parent_provenance(proof, h.objects)
                self.assertEqual(parent.members, ())
                self.assertTrue(parent.discovery_complete)
                self.assertGreater(len(proof['discovery']['progress']), 0)
                session = proof['discovery']['session']
                gaps = [Error('baseline_source_missing', 'valid empty listing leaves baseline source unresolved',
                              True, None, {'quarter': quarter}).to_mapping()
                        for quarter in ('2026Q3', '2026Q4')]
                selection = {'format_version': 'sec-workflow-selection-v1', 'context': context.to_mapping(),
                    'invocation': invocation, 'members': [], 'jobs': [], 'member_provenance': [],
                    'already_complete': [], 'discovery_call': child.call, 'discovery_error': None,
                    'parent_ref': child.result.source_workset_ref, 'parent_provenance': proof,
                    'discovery_session': session, 'required_units': session['frozen']['units'],
                    'halted': False, 'requested_quarters': ['2026Q3', '2026Q4'],
                    'directories': [d.to_mapping() for d in parent.directories], 'boundary_before': None,
                    'gaps': gaps, 'discovered_sources': 0, 'unresolved_before': 0}
                frozen = freeze_selection(context, selection, h.store, h.objects)
                self.assertEqual(frozen['parent_provenance'], proof)
                # Pure historical parent validation needs no surviving live session/index.
                validate_parent_provenance(proof, h.objects)
            finally:
                h.close()

    def test_empty_leaf_roles_bridge_and_listing_evidence_cannot_be_substituted(self):
        from copy import deepcopy
        from sec_edgar_ingest.workflows.completion import capture_parent_provenance, validate_parent_provenance
        from sec_edgar_ingest.models import parse_json, to_mapping_value
        selection = parse_json(canonical_json(to_mapping_value(self.selection(skipped=True))))
        proof = selection['parent_provenance']
        empty = next(value for value in proof['discovery']['progress']
                     if value['unit']['period'] == '2026Q4' and value['unit']['role'] == 'quarter')
        self.assertEqual(empty['value']['members'], [])
        variants = []
        changed = deepcopy(selection); changed['required_units'][0]['role'] = 'quarter'; variants.append(changed)
        changed = deepcopy(selection)
        root = next(unit for unit in changed['required_units'] if unit['role'] == 'root')
        root['bridge_period'] = '2026Q3'; variants.append(changed)
        changed = deepcopy(selection); changed['parent_provenance'] = None; variants.append(changed)
        changed = deepcopy(selection); changed['discovery_session']['frozen']['end'] = '2026Q3'; variants.append(changed)
        changed = deepcopy(selection)
        captured = next(value for value in changed['parent_provenance']['discovery']['progress']
                        if value['unit']['period'] == '2026Q4' and value['unit']['role'] == 'quarter')
        captured['value']['evidence']['byte_count'] += 1; variants.append(changed)
        changed = deepcopy(selection)
        changed['already_complete'][0]['observation']['parser_version'] = 'fixture-index-parser-v2'
        variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises((Conflict, ValueError, FileNotFoundError)):
                freeze_selection(self.context, changed, self.f.store, self.f.objects)
        target = self.f.root / 'objects' / empty['value']['evidence']['body_path']
        original = target.read_bytes()
        target.write_bytes(original + b' ')
        try:
            with self.assertRaises((Conflict, ValueError, FileNotFoundError)):
                validate_parent_provenance(proof, self.f.objects)
        finally:
            target.write_bytes(original)

    def test_unfinished_discovery_retains_actual_frozen_session_ledger(self):
        from sec_edgar_ingest.state import AcquisitionState
        dispatcher = Dispatcher(self.context, self.f.settings, self.f.pack,
                                self.f.root.parent, self.f.store, self.f.objects)
        original = AcquisitionState.begin_discovery
        def stop_after_begin(state, *args, **kwargs):
            result = original(state, *args, **kwargs)
            raise OwnershipLost('ownership lost after required-unit registration')
        with patch.object(AcquisitionState, 'begin_discovery', stop_after_begin):
            with self.assertRaises(ChildUnfinished) as failed:
                dispatcher.execute('discover', 'begun-fatal-discovery', self.f.settings,
                    ('--mode', 'quarterly', '--discovery-id', 'begun-fatal-session'))
        session = AcquisitionState(self.f.store).discovery_session('begun-fatal-session').to_mapping()['value']
        self.assertTrue(session['registered'])
        self.assertIsNone(session['workset_id'])
        self.assertTrue(session['frozen']['units'])
        error = Error(failed.exception.outcome, 'discovery has no durable source result',
                      False, None, failed.exception.details)
        selection = self.selection()
        selection.update(discovery_call=failed.exception.call, discovery_error=error.to_mapping(),
            parent_ref=None, parent_provenance=None, discovery_session=session,
            required_units=session['frozen']['units'], directories=[], halted=True,
            gaps=[error.to_mapping()], discovered_sources=0, unresolved_before=1)
        frozen = freeze_selection(self.context, selection, self.f.store, self.f.objects)
        self.assertEqual(frozen['required_units'], session['frozen']['units'])
        self.assertIsNone(frozen['parent_ref'])
        self.assertTrue(frozen['halted'])
        from copy import deepcopy
        omitted = deepcopy(selection); omitted['required_units'] = []
        with self.assertRaises(Conflict):
            freeze_selection(self.context, omitted, self.f.store, self.f.objects)

    def test_valid_old_capture_cannot_discharge_current_parser_backlog(self):
        from support_workflows import simple_pack
        from sec_edgar_ingest.config import Settings, pin_context
        from sec_edgar_ingest.models import parse_json, to_mapping_value
        from sec_edgar_ingest.workflows.completion import capture_parent_provenance
        mapping = self.f.settings.to_mapping()
        mapping['etl']['parser_version'] = 'fixture-index-parser-v2'
        settings = Settings.from_mapping(mapping)
        context = pin_context(settings, replace(self.context,
            run_id='v2-empty-discovery', execution_id='v2-empty-execution', attempt_id='v2-empty-attempt',
            parser_version=settings.etl.parser_version, config_sha256=settings.config_sha256,
            effective_config={}, pinned_on=None), self.context.pinned_on)[0]
        pack = simple_pack(self.f.root.parent / 'v2-empty-pack', empty=True)
        invocation = {'command': 'backfill', 'today': self.context.pinned_on.isoformat(),
                      'fixture_sha256': hashlib.sha256(pack.read_bytes()).hexdigest(),
                      'pinned_end_quarter': '2026Q4'}
        context = freeze_workflow(context, invocation, self.f.store, self.f.objects)
        dispatcher = Dispatcher(context, settings, pack, self.f.root.parent, self.f.store, self.f.objects)
        child = dispatcher.execute('discover', 'discover-v2-empty', settings,
                                  ('--mode', 'quarterly', '--discovery-id', 'v2-empty-session'))
        proof = capture_parent_provenance(child.result.source_workset_ref, self.f.store, self.f.objects)
        parent = decode_source_workset(self.f.objects.read(child.result.source_workset_ref))
        self.assertEqual(parent.members, ())
        self.assertTrue(parent.discovery_complete)
        selection = parse_json(canonical_json(to_mapping_value(self.selection(skipped=True))))
        selection.update(context=context.to_mapping(), invocation=invocation,
            discovery_call=child.call, parent_ref=child.result.source_workset_ref,
            parent_provenance=proof, discovery_session=proof['discovery']['session'],
            required_units=proof['discovery']['session']['frozen']['units'],
            directories=[d.to_mapping() for d in parent.directories],
            discovered_sources=0, unresolved_before=1)
        self.assertEqual(selection['already_complete'][0]['observation']['parser_version'],
                         'fixture-index-parser-v1')
        with self.assertRaisesRegex(Conflict, 'skipped completion capture differs'):
            freeze_selection(context, selection, self.f.store, self.f.objects)
```

- [ ] **Step 2: Run red** with `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_results.py -v`; then install the fully corrected implementation and rerun the same command for green.
- [ ] **Step 3: Fresh scoped review** checks immutable authority versus indexes, historical validation versus current checks, report-before-index ordering, all crash/reopen cases, strict exact-replay refusal and no later-task dependencies.
- [ ] **Step 4: Commit** only reviewed production/tests. Review the source-unit count test, immutable historical capture test, exact expiry replay test and fatal discovery no-result test as distinct acceptance checks.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_results.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/results.py packages/sec-edgar-ingest/tests/test_workflow_results.py
git commit -m "feat: persist frozen workflow selection and immutable results"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 7: Verified legacy recovery with isolated provenance failures

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/legacy.py`, `packages/sec-edgar-ingest/tests/test_workflow_legacy.py`. The pure recovery validator and read_parent branch were defined in Task 2 before Task 4 consumes them; this task creates their immutable captured inputs.

**Interfaces:** `bootstrap_legacy(store,objects) -> tuple[Error,...]`; `reconstruct_parent(session,store,objects) -> str`; `validate_parent_recovery(parent_ref,descriptor,objects) -> Mapping` returns `{session,progress}` after validating the exact reconstructed original parent. `progress` is an ordered array of `{unit,value}`, where value is an original DirectoryProgress map or None. Task 4's provenance capture consumes the recovery descriptor; its historical validator calls the pure object validator and compares this returned snapshot to the captured discovery evidence. The recovery SourceState index kind is `WorkflowParentRecovery`, key parent workset ID, value `{ref,sha256,bytes}`. This task does not change a DiscoverySession, fabricate accepted members from failed listings or mark source completion.

- [ ] Add these real command/store regressions to `test_workflow_legacy.py`. Temporary fault injection interrupts actual storage boundaries, and each test invokes shipped discovery/collection rather than manufacturing successful workflow records:

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from support_workflows import BASE, CommandHarness, simple_pack
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.local import LocalObjectStore, LocalStateStore
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.workflows.legacy import bootstrap_legacy
from sec_edgar_ingest.workflows.provenance import read_member, read_parent

class Crash(BaseException):
    pass

class LegacyTests(unittest.TestCase):
    def test_old_downloaded_unit_keeps_parent_and_exact_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                code, discovery = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'legacy'))
                self.assertEqual(code, 0)
                code, collection = h.invoke('collect', ('--workset', discovery['source_workset_ref']))
                self.assertEqual(code, 0)
                acquisition = AcquisitionState(h.store)
                parent = read_parent(discovery['source_workset_ref'], h.store, h.objects)
                original_pin = acquisition.binding(parent.workset_id, parent.members[0].source_id)
                self.assertIsNotNone(original_pin)
                self.assertEqual(tuple(h.store.scan('WorkflowMember', {})), ())
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                self.assertEqual(len(values), 1)
                member = read_member(values[0], h.store, h.objects)
                self.assertEqual(values[0]['parent_ref'], discovery['source_workset_ref'])
                self.assertEqual(acquisition.binding(member.workset_id, parent.members[0].source_id).snapshot_sha256,
                                 original_pin.snapshot_sha256)
                for repeat in range(3):
                    self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                    self.assertEqual(tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {})), values)
                self.assertFalse(any(value['parent_ref'] in {v['member_ref'] for v in values} for value in values))
            finally:
                h.close()

    def test_crash_before_parent_write_recovers_all_original_units(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            original_put = LocalObjectStore.put_once
            def stop_parent(objects, path, body):
                if path.startswith('worksets/sec/source/'):
                    raise Crash('before original parent-object write')
                return original_put(objects, path, body)
            try:
                with patch.object(LocalObjectStore, 'put_once', stop_parent):
                    with self.assertRaises(Crash):
                        h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'interrupted'))
                acquisition = AcquisitionState(h.store)
                before = acquisition.discovery_session('interrupted').to_mapping()
                self.assertIsNone(before['value']['workset_id'])
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                self.assertEqual(acquisition.discovery_session('interrupted').to_mapping(), before)
                values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                self.assertEqual(len(values), 1)
                recovered = read_parent(values[0]['parent_ref'], h.store, h.objects)
                self.assertEqual({d.url for d in recovered.directories},
                                 {u['url'] for u in before['value']['frozen']['units']})
                self.assertTrue(recovered.discovery_complete)
                self.assertIsNotNone(h.store.get('WorkflowParentRecovery', recovered.workset_id))
                self.assertEqual(read_member(values[0], h.store, h.objects).members, recovered.members)
            finally:
                h.close()

    def test_missing_progress_is_failed_and_does_not_invent_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            original_insert = LocalStateStore.insert
            missing = BASE + 'daily-index/2026/QTR4/index.json'
            def stop_unit(store, kind, key, value):
                if kind == 'DirectoryProgress' and value['outcome']['url'] == missing:
                    raise Crash('before successful quarter progress write')
                return original_insert(store, kind, key, value)
            try:
                with patch.object(LocalStateStore, 'insert', stop_unit):
                    with self.assertRaises(Crash):
                        h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'missing'))
                before = AcquisitionState(h.store).discovery_session('missing').to_mapping()
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                captures = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowParentRecovery', {}))
                self.assertEqual(len(captures), 1)
                from sec_edgar_ingest.models import parse_json
                recovery = parse_json(h.objects.read(captures[0]['ref']))
                parent = read_parent(recovery['parent_ref'], h.store, h.objects)
                self.assertFalse(parent.discovery_complete)
                self.assertEqual(parent.members, ())
                self.assertEqual(next(d for d in parent.directories if d.url == missing).error.code, 'discovery_pending')
                self.assertEqual(AcquisitionState(h.store).discovery_session('missing').to_mapping(), before)
            finally:
                h.close()

    def test_corrupt_parent_is_isolated_from_valid_sibling_and_never_recursive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                code, bad = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'bad'), run='bad')
                self.assertEqual(code, 0)
                code, good = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'good'), run='good')
                self.assertEqual(code, 0)
                target = h.objects.directory / bad['source_workset_ref']
                original = target.read_bytes()
                target.write_bytes(original + b' ')
                try:
                    gaps = bootstrap_legacy(h.store, h.objects)
                    self.assertTrue(any(g.code == 'legacy_member_unresolved' for g in gaps))
                    self.assertTrue(all('record_sha256' in g.details for g in gaps))
                    values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                    self.assertEqual(len(values), 1)
                    self.assertEqual(values[0]['parent_ref'], good['source_workset_ref'])
                finally:
                    target.write_bytes(original)
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                self.assertEqual(len(values), 2)
                for repeat in range(3):
                    self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                    self.assertEqual(tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {})), values)
                code, fresh = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'fresh'), run='fresh')
                self.assertEqual(code, 0)
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                self.assertEqual(len(values), 3)
                singleton_refs = {value['member_ref'] for value in values}
                self.assertFalse(any(value['parent_ref'] in singleton_refs for value in values))
                for value in values:
                    read_member(value, h.store, h.objects)
            finally:
                h.close()
    def test_recovery_capture_tampering_refuses(self):
        from copy import deepcopy
        from dataclasses import replace
        from sec_edgar_ingest.models import DirectoryOutcome, Error, parse_json
        from sec_edgar_ingest.storage.contracts import Conflict
        from sec_edgar_ingest.workflows.legacy import reconstruct_parent
        from sec_edgar_ingest.workflows.provenance import validate_parent_recovery
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                code, discovered = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'capture'))
                self.assertEqual(code, 0)
                session = AcquisitionState(h.store).discovery_session('capture').to_mapping()['value']
                ref = reconstruct_parent(session, h.store, h.objects)
                parent = read_parent(ref, h.store, h.objects)
                descriptor = h.store.get('WorkflowParentRecovery', parent.workset_id).to_mapping()['value']
                saved = parse_json(h.objects.read(descriptor['ref']))
                validate_parent_recovery(ref, descriptor, h.objects)
                variants = []
                changed = deepcopy(saved)
                changed['session']['frozen']['context']['execution_id'] = 'other'
                variants.append(changed)
                changed = deepcopy(saved)
                changed['progress'] = changed['progress'][1:]
                variants.append(changed)
                changed = deepcopy(saved)
                next(p for p in changed['progress'] if p['unit']['role'] == 'root')['value'] = None
                variants.append(changed)
                changed = deepcopy(saved)
                item = next(p for p in changed['progress'] if p['value'] and p['value']['members'])
                directory = DirectoryOutcome.from_mapping(item['value']['outcome'])
                item['value']['outcome'] = replace(directory, outcome='discovery_failed', listing_sha256=None,
                    source_ids=(), error=Error('discovery_pending', 'not complete', True, None, {})).to_mapping()
                item['value']['evidence'] = None
                variants.append(changed)
                changed = deepcopy(saved)
                changed['parent']['pinned_end_quarter'] = '2026Q3'
                variants.append(changed)
                for number, altered in enumerate(variants):
                    with self.subTest(number=number):
                        body = canonical_json(to_mapping_value(altered))
                        digest = hashlib.sha256(body).hexdigest()
                        path = 'worksets/sec/workflow-parent-recovery/sha256=' + digest + '/recovery.json'
                        h.objects.put_once(path, body)
                        with self.assertRaises((Conflict, ValueError, OSError, KeyError)):
                            validate_parent_recovery(ref, {'ref': path, 'sha256': digest, 'bytes': len(body)}, h.objects)
                for altered in ({**descriptor, 'ref': descriptor['ref'] + '.other'},
                                {**descriptor, 'sha256': '0' * 64},
                                {**descriptor, 'bytes': descriptor['bytes'] + 1}):
                    with self.subTest(descriptor=altered):
                        with self.assertRaises((Conflict, ValueError, OSError)):
                            validate_parent_recovery(ref, altered, h.objects)
                self.assertEqual(AcquisitionState(h.store).discovery_session('capture').to_mapping()['value'], session)
            finally:
                h.close()

    def test_legacy_registry_and_capture_survive_close_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = simple_pack(root / 'pack')
            h = CommandHarness(root, pack)
            try:
                code, discovered = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'reopen'))
                self.assertEqual(code, 0)
                code, collected = h.invoke('collect', ('--workset', discovered['source_workset_ref']))
                self.assertEqual(code, 0)
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                before = tuple(row.to_mapping() for row in h.store.scan('WorkflowMember', {}))
                session = AcquisitionState(h.store).discovery_session('reopen').to_mapping()
                h.close()
                h = CommandHarness(root, pack)
                self.assertEqual(bootstrap_legacy(h.store, h.objects), ())
                self.assertEqual(tuple(row.to_mapping() for row in h.store.scan('WorkflowMember', {})), before)
                self.assertEqual(AcquisitionState(h.store).discovery_session('reopen').to_mapping(), session)
                for row in before:
                    read_member(row['value'], h.store, h.objects)
            finally:
                h.close()

    def test_corrupt_source_and_processing_do_not_hide_valid_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                code, discovered = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'corrupt-state'))
                self.assertEqual(code, 0)
                code, collected = h.invoke('collect', ('--workset', discovered['source_workset_ref']))
                self.assertEqual(code, 0)
                code, transformed = h.invoke('transform', ('--workset', collected['snapshot_workset_ref']))
                self.assertEqual(code, 0)
                parent = read_parent(discovered['source_workset_ref'], h.store, h.objects)
                identity = parent.members[0].source_id
                source_row = h.store.get('Source', identity)
                source_value = source_row.to_mapping()['value']
                source_value['source']['source_id'] = '0' * 64
                h.store.replace('Source', identity, source_value, source_row.version)
                processing_row = next(h.store.scan('Processing', {}))
                processing_value = processing_row.to_mapping()['value']
                processing_value['observation']['source']['source_id'] = '0' * 64
                h.store.replace('Processing', processing_value['processing_key'], processing_value, processing_row.version)
                gaps = bootstrap_legacy(h.store, h.objects)
                self.assertTrue({'Source', 'Processing'} <= {g.details['record_kind'] for g in gaps})
                self.assertTrue(all(g.code == 'legacy_member_unresolved' and 'record_sha256' in g.details for g in gaps))
                values = tuple(row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {}))
                self.assertEqual(len(values), 1)
                self.assertEqual(values[0]['parent_ref'], discovered['source_workset_ref'])
                read_member(values[0], h.store, h.objects)
            finally:
                h.close()

```

- [ ] Run guarded `test_workflow_legacy.py`; expected missing legacy module/recovery API. Record actual red output. The recovery test must reach a new recovered ID not present in session current/predecessor/history; restoring the missing bytes of an already-finalized parent alone does not test that branch.
- [ ] Create `workflows/legacy.py` with the following code. Each session revision, command reference, source and Processing entry has its own exception boundary. StateStore.scan returns Versioned(value,version), so error identity uses the record's canonical hash and validated context rather than an unavailable row.key field. Existing projection refs are filtered even if their registry value is corrupt; they can never become new original parents:

```python
from ..models import to_mapping_value
import hashlib
from ..models import Error, RunContext, Source, canonical_json, parse_json
from ..state import AcquisitionState, attempt_key
from ..storage.contracts import Conflict
from ..worksets import encode_workset, decode_snapshot_workset
from ..results import read_result, result_path
from ..etl.commands import read_etl_result
from .provenance import (RECOVERY_FORMAT, immutable, source_ref, read_parent, read_member,
                        project_member, transfer_binding, rebuild_recovered_parent,
                        validate_parent_recovery)

LEGACY_ERRORS = (ValueError, OSError, Conflict, KeyError, TypeError)


def reconstruct_parent(session, store, objects):
    acquisition = AcquisitionState(store)
    progress = []
    for unit in sorted(session['frozen']['units'], key=lambda u: (u['url'].count('/'), u['url'])):
        row = acquisition.directory_progress(session['discovery_id'], unit['url'])
        progress.append({'unit': unit, 'value': None if row is None else row.to_mapping()['value']})
    parent = rebuild_recovered_parent(session, progress, objects)
    recovery = {'format_version': RECOVERY_FORMAT, 'parent_ref': source_ref(parent),
                'parent': parent.to_mapping(), 'session': session, 'progress': progress}
    body = canonical_json(to_mapping_value(recovery))
    digest = hashlib.sha256(body).hexdigest()
    path = 'worksets/sec/workflow-parent-recovery/sha256=' + digest + '/recovery.json'
    objects.put_once(source_ref(parent), encode_workset(parent))
    retained = store.get('WorkflowParentRecovery', parent.workset_id)
    if retained is not None:
        captured = validate_parent_recovery(source_ref(parent), retained.to_mapping()['value'], objects)
        if canonical_json(to_mapping_value(captured['session']['frozen'])) != canonical_json(to_mapping_value(session['frozen'])):
            raise Conflict('retained recovery changes frozen original session')
        read_parent(source_ref(parent), store, objects)
        return source_ref(parent)
    objects.put_once(path, body)
    objects.verify(path, digest, len(body))
    descriptor = {'ref': path, 'sha256': digest, 'bytes': len(body)}
    validate_parent_recovery(source_ref(parent), descriptor, objects)
    immutable(store, 'WorkflowParentRecovery', parent.workset_id, descriptor)
    read_parent(source_ref(parent), store, objects)
    return source_ref(parent)


def bootstrap_legacy(store, objects):
    gaps, parents, covered = [], {}, set()
    acquisition = AcquisitionState(store)
    registered, projection_refs = {}, set()

    def unresolved(kind, value, error, source_id=None, **details):
        digest = hashlib.sha256(canonical_json(to_mapping_value(value))).hexdigest()
        gaps.append(Error('legacy_member_unresolved', str(error), False, source_id,
                          {'record_kind': kind, 'record_sha256': digest, **details}))

    for row in store.scan('WorkflowMember', {}):
        value = row.to_mapping()['value']
        if isinstance(value.get('member_ref'), str):
            projection_refs.add(value['member_ref'])
        try:
            read_member(value, store, objects)
            registered[value['member_ref']] = value
            covered.add(value['source']['source_id'])
        except LEGACY_ERRORS as error:
            unresolved('WorkflowMember', value, error)

    def retain(ref):
        if ref in projection_refs:
            if ref not in registered:
                raise Conflict('corrupt registered projection cannot supply original provenance')
            ref = registered[ref]['parent_ref']
        parent = read_parent(ref, store, objects)
        parents[parent.workset_id] = (ref, parent)

    for row in store.scan('DiscoverySession', {}):
        session = row.to_mapping()['value']
        try:
            revisions = [session.get('workset_id'), session.get('predecessor_workset_id')]
            for historical in session.get('history', ()):
                try:
                    revisions.append(historical['workset_id'])
                except LEGACY_ERRORS as error:
                    unresolved('DiscoverySession', session, error, history_entry=historical)
        except LEGACY_ERRORS as error:
            unresolved('DiscoverySession', session, error)
            continue
        recovered, retained_ids = False, set()
        identities = [identity for identity in revisions if identity is not None]
        for identity in identities:
            ref = None
            try:
                from ..models import require_hash
                require_hash(identity, 'legacy original workset')
                if identity in retained_ids:
                    continue
                retained_ids.add(identity)
                ref = 'worksets/sec/source/sha256=' + identity + '/workset.json'
                retain(ref)
            except FileNotFoundError:
                if not recovered:
                    try:
                        retain(reconstruct_parent(session, store, objects))
                        recovered = True
                    except LEGACY_ERRORS as error:
                        unresolved('DiscoverySession', session, error, ref=ref)
            except LEGACY_ERRORS as error:
                unresolved('DiscoverySession', session, error, ref=ref)
        if not identities:
            try:
                retain(reconstruct_parent(session, store, objects))
            except LEGACY_ERRORS as error:
                unresolved('DiscoverySession', session, error)

    from .checked import _authority, _transformed_input
    from .completion import _call_context, _legacy_publish_call
    for row in store.scan('WorkflowChildCall', {}):
        value = row.to_mapping()['value']
        try:
            call, template = _authority(value, None, objects)
            if template.command == 'publish':
                _transformed_input(call['input_ref'], None, objects)
                try:
                    _call_context(call, store, objects)
                except FileNotFoundError:
                    continue  # Immutable command was not committed; CAS was unreachable.
        except LEGACY_ERRORS as error:
            unresolved('WorkflowChildCall', value, error)

    for row in store.scan('Attempt', {}):
        value = row.to_mapping()['value']
        try:
            context = RunContext.from_mapping(value['context'])
            if value.get('result') is None:
                if context.command == 'publish':
                    try:
                        _legacy_publish_call(context, objects)
                    except FileNotFoundError:
                        pass  # No command commit means no publication CAS.
                continue
            if context.command not in ('discover', 'collect', 'transform', 'publish'):
                raise Conflict('legacy acquisition Attempt command differs')
            child = (read_etl_result if context.command in ('transform', 'publish') else read_result)(
                result_path(context), objects)
            if child.context != context or child.to_mapping() != value['result']:
                raise Conflict('legacy Attempt result differs from immutable command object')
            refs = []
            source_set = getattr(child, 'source_workset_ref', None)
            if source_set is not None:
                refs.append(source_set)
            snapshot_ref = getattr(child, 'snapshot_workset_ref', None)
            if context.command == 'transform':
                snapshot_ref = child.input_ref
            if snapshot_ref is not None:
                snapshots = decode_snapshot_workset(objects.read(snapshot_ref))
                refs.append('worksets/sec/source/sha256=' + snapshots.source_workset_id + '/workset.json')
        except LEGACY_ERRORS as error:
            unresolved('Attempt', value, error)
            continue
        for ref in refs:
            try:
                retain(ref)
            except LEGACY_ERRORS as error:
                unresolved('Attempt', value, error, ref=ref, attempt_key=attempt_key(context))

    for ref, parent in sorted(parents.values(), key=lambda item: item[0]):
        for source in parent.members:
            try:
                value = project_member(ref, source.source_id, store, objects)
                pin = acquisition.binding(parent.workset_id, source.source_id)
                if pin is not None:
                    transfer_binding(value, acquisition.snapshot(source.source_id, pin.snapshot_sha256), store, objects)
                covered.add(source.source_id)
            except LEGACY_ERRORS as error:
                unresolved('SourceWorkset', parent.to_mapping(), error, source.source_id, parent_ref=ref)

    for kind in ('Source', 'Processing'):
        for row in store.scan(kind, {}):
            value = row.to_mapping()['value']
            try:
                source = Source.from_mapping(value['source'] if kind == 'Source' else value['observation']['source'])
                if source.source_id not in covered:
                    unresolved(kind, value, 'source has no verified original parent', source.source_id)
            except LEGACY_ERRORS as error:
                unresolved(kind, value, error)
    return tuple(gaps)
```

- [ ] Add immutable-capture tampering cases for recovery descriptor ref/SHA/length, saved frozen context/required ledger, a successful child without the original parent listing entry, accepted member in failed progress and parent source/endpoint relabeling. Each mutation creates a temporary alternate canonical object/descriptor; validate_parent_recovery must refuse. Add close/reopen verification using open_stores on the same temporary root, unchanged DiscoverySession/index hashes, divergent Binding winner refusal and corrupt Source/Processing sibling isolation.
- [ ] Run guarded legacy/provenance/completion tests, then shipped discovery/workset/collection regressions. Expected PASS with real receipt verification, exact pin readback and bounded registry growth. Commit only these owned paths with `feat: reconstruct verified legacy workflow backlog`; fresh review checks missing-progress provenance, per-record isolation and repeated bootstrap without recursive projection.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_legacy.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/legacy.py packages/sec-edgar-ingest/tests/test_workflow_legacy.py
git commit -m "feat: reconstruct verified legacy workflow backlog"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 8: Ordered workflow selection, dispatch and coverage assembly

**Files:** Create `packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py`, `packages/sec-edgar-ingest/tests/test_workflow_runner.py`.

**Interfaces:** `reuse_exact_binding(value,store,objects)->tuple[Error,...]` retains isolated reuse uncertainty; `select_work(context,settings,intent,dispatcher,store,objects)->Mapping` produces the exact Task 6 selection; `baseline_gaps(selection,results,evidences,store,objects)->tuple[Error,...]`; `run_workflow(context:RunContext,settings:Settings,intent:Mapping,dispatcher:Dispatcher,store,objects,observer=None)->WorkflowResult`. Consumes all earlier APIs, especially T6 frozen selection schema and T5 receipts. Selection uses singleton jobs (`aliases == [member]`) deliberately: each exact original member is its own checkpoint; counters collapse source identity and logical filing deduplication remains Stage 3. No delegated alias success is invented.

- [ ] Write these real-store failing tests in test_workflow_runner.py. T3/T4/T6 also supply complete repair/affected-quarter/replay regressions before this consumer runs.

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, json, tempfile, unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from support_workflows import BASE, CommandHarness, simple_pack, idx
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.models import RunContext, canonical_json
from sec_edgar_ingest.etl.reader import capture_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.workflows.checked import Dispatcher
from sec_edgar_ingest.workflows.runner import run_workflow
from sec_edgar_ingest.workflows.results import freeze_workflow, write_workflow_result, read_workflow_result
from sec_edgar_ingest.workflows.contracts import workflow_path

class RunnerTests(unittest.TestCase):
    def run_parent(self, h, *, run='runner', command='backfill'):
        now = datetime.now(timezone.utc)
        context = RunContext(run, 'manual', command, 'a', h.settings.worker.image_digest,
            h.settings.etl.parser_version, h.settings.etl.schema_version, h.settings.config_sha256,
            now, now + timedelta(seconds=1800), 'daily' if command == 'daily' else 'backfill')
        context = pin_context(h.settings, context, date(2026, 10, 7))[0]
        intent = {'command': command, 'today': '2026-10-07',
                  'fixture_sha256': hashlib.sha256(h.pack.read_bytes()).hexdigest(),
                  'pinned_end_quarter': '2026Q4'}
        context = freeze_workflow(context, intent, h.store, h.objects)
        dispatcher = Dispatcher(context, h.settings, h.pack, h.root, h.store, h.objects)
        report = run_workflow(context, h.settings, intent, dispatcher, h.store, h.objects)
        path = write_workflow_result(report, h.store, h.objects)
        self.assertEqual(read_workflow_result(path, h.store, h.objects), report)
        return report

    def test_deadline_after_selection_records_undispatched_units_without_child_work(self):
        from unittest.mock import patch
        from sec_edgar_ingest.workflows.runner import select_work
        from sec_edgar_ingest.workflows.results import freeze_selection
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                now = datetime.now(timezone.utc)
                context = RunContext('midrun-deadline', 'manual', 'backfill', 'a',
                    h.settings.worker.image_digest, h.settings.etl.parser_version,
                    h.settings.etl.schema_version, h.settings.config_sha256,
                    now, now + timedelta(seconds=1800), 'backfill')
                context = pin_context(h.settings, context, date(2026, 10, 7))[0]
                intent = {'command': 'backfill', 'today': '2026-10-07',
                    'fixture_sha256': hashlib.sha256(h.pack.read_bytes()).hexdigest(),
                    'pinned_end_quarter': '2026Q4'}
                context = freeze_workflow(context, intent, h.store, h.objects)
                dispatcher = Dispatcher(context, h.settings, h.pack, h.root, h.store, h.objects)
                selected = select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
                freeze_selection(context, selected, h.store, h.objects)
                expired = context.deadline + timedelta(seconds=1)
                with patch('sec_edgar_ingest.workflows.runner.datetime') as clock, \
                     patch('sec_edgar_ingest.workflows.results.datetime') as accounting_clock, \
                     patch.object(dispatcher, 'execute', side_effect=AssertionError('expired child dispatch')):
                    clock.now.return_value = expired
                    accounting_clock.now.return_value = expired
                    report = run_workflow(context, h.settings, intent, dispatcher, h.store, h.objects)
                    path = write_workflow_result(report, h.store, h.objects)
                    self.assertEqual(read_workflow_result(path, h.store, h.objects), report)
                self.assertEqual(report.counts['pending_sources'], 2)
                self.assertEqual(report.counts['complete_sources'], 0)
                self.assertNotEqual(report.outcome, 'success')
                self.assertTrue(all(member.outcome == 'pending' and not member.child_refs for member in report.members))
                self.assertEqual(report.intent['member_receipts'], (None, None))
                self.assertEqual(len(report.intent['child_calls']), 1)
                self.assertEqual(tuple(h.store.scan('Processing', {})), ())
                for quarter in ('2026Q3', '2026Q4'):
                    self.assertIsNone(EtlState(h.store).pointer(quarter))
            finally:
                h.close()

    def test_corrupt_retained_registry_and_receipt_do_not_block_valid_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                h.store.insert('WorkflowMember', 'broken-member-row', {'source': {'source_id': 'bad'}})
                first = self.run_parent(h, run='valid-with-corrupt-sibling')
                self.assertEqual(first.counts['complete_sources'], 2)
                self.assertEqual(first.outcome, 'incomplete')
                self.assertTrue(any(gap.code == 'legacy_member_unresolved' for gap in first.gaps))
                from sec_edgar_ingest.workflows.members import WorkflowMembers
                valid = WorkflowMembers(h.store, h.objects).inventory()[0]
                old = valid[0]
                h.store.insert('WorkflowMemberResult', 'broken-receipt-row', {
                    'member_id': old['member_id'], 'parser_version': h.settings.etl.parser_version,
                    'schema_version': h.settings.etl.schema_version, 'ref': 'missing/corrupt-receipt.json',
                    'sha256': 'a' * 64, 'bytes': 1})
                second = self.run_parent(h, run='valid-with-corrupt-receipt')
                self.assertGreaterEqual(second.counts['complete_sources'], 2)
                self.assertEqual(second.outcome, 'incomplete')
                self.assertTrue(any(gap.code == 'legacy_member_unresolved' and
                    gap.details.get('member_id') == old['member_id'] for gap in second.gaps))
                self.assertEqual([len(h.capture(quarter)[1]) for quarter in ('2026Q3', '2026Q4')], [1, 1])
            finally:
                h.close()

    def test_bounded_inclusive_backfill_captures_both_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); h = CommandHarness(root, simple_pack(root / 'pack'))
            try:
                report = self.run_parent(h)
                self.assertEqual(report.requested_quarters, ('2026Q3', '2026Q4'))
                self.assertEqual(report.outcome, 'success')
                self.assertEqual(report.counts['complete_sources'], 2)
                self.assertEqual([len(h.capture(q)[1]) for q in report.requested_quarters], [1, 1])
                self.assertEqual(len(report.intent['member_receipts']), 2)
                self.assertEqual(len(report.intent['completion_captures']), 2)
            finally:
                h.close()

    def test_all_refused_retains_baseline_gaps_and_quarantine_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); h = CommandHarness(root, simple_pack(root / 'pack', conflicting=True))
            try:
                report = self.run_parent(h)
                self.assertEqual(report.outcome, 'quarantined')
                self.assertEqual((report.counts['complete_sources'], report.counts['failed_sources'],
                                  report.counts['quarantined_sources']), (0, 2, 2))
                self.assertEqual({g.details['quarter'] for g in report.gaps if g.code == 'baseline_publication_missing'},
                                 {'2026Q3', '2026Q4'})
                self.assertTrue(all(g.details.get('coverage_cause') == 'selected_source_quarantine'
                                    for g in report.gaps if g.code == 'baseline_publication_missing'))
                self.assertEqual(tuple(h.store.scan('Processing', {})), ())
                for quarter in report.requested_quarters:
                    self.assertIsNone(capture_quarter(quarter, h.objects, EtlState(h.store)))
            finally:
                h.close()

    def test_refusal_and_valid_progress_are_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pack = simple_pack(root / 'pack', conflicting=True)
            manifest = json.loads(pack.read_text())
            url = BASE + 'full-index/2026/QTR4/master.zip'
            body = idx((('123456', 'Example', '10-K', '2026-10-01',
                         'edgar/data/123456/0000123456-26-000004.txt'),), 'quarterly')
            digest = hashlib.sha256(body).hexdigest()
            (pack.parent / 'bodies' / (digest + '.body')).write_bytes(body)
            for response in manifest['responses'][url]:
                response.update(body_path='bodies/' + digest + '.body', body_sha256=digest)
            pack.write_bytes(canonical_json(to_mapping_value(manifest))); h = CommandHarness(root, pack)
            try:
                report = self.run_parent(h)
                self.assertEqual(report.outcome, 'incomplete')
                self.assertEqual((report.counts['complete_sources'], report.counts['failed_sources']), (1, 1))
                self.assertEqual(len(h.capture('2026Q4')[1]), 1)
                self.assertIsNone(capture_quarter('2026Q3', h.objects, EtlState(h.store)))
            finally:
                h.close()

    def test_empty_quarter_is_independent_missing_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pack = simple_pack(root / 'pack', conflicting=True)
            manifest = json.loads(pack.read_text())
            url = BASE + 'full-index/2026/QTR3/index.json'
            from support_workflows import listing
            body = listing(url, [])
            digest = hashlib.sha256(body).hexdigest()
            (pack.parent / 'bodies' / (digest + '.body')).write_bytes(body)
            for response in manifest['responses'][url]:
                response.update(body_path='bodies/' + digest + '.body', body_sha256=digest)
            pack.write_bytes(canonical_json(to_mapping_value(manifest))); h = CommandHarness(root, pack)
            try:
                report = self.run_parent(h)
                self.assertEqual(report.outcome, 'incomplete')
                self.assertTrue(any(g.code == 'baseline_source_missing' and g.details['quarter'] == '2026Q3'
                                    for g in report.gaps))
                self.assertTrue(all('coverage_cause' not in g.details for g in report.gaps
                                    if g.code == 'baseline_publication_missing'))
                self.assertEqual(report.counts['quarantined_sources'], 1)
            finally:
                h.close()
```

- [ ] Run `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_runner.py -v`; expected missing runner import/API. Preserve actual red output.
- [ ] Implement this ordered control flow, with helpers below it:

```python
from ..models import to_mapping_value
# workflows/runner.py
from datetime import datetime, timezone
import hashlib
from ..models import Error, Source, canonical_json, parse_json
from ..collection import HALTING_OUTCOMES
from ..state import AcquisitionState
from ..storage.contracts import Conflict, observe
from ..discovery import quarter_span
from ..etl.reader import capture_quarter
from ..etl.state import EtlState
from .contracts import MemberResult, WorkflowResult, FATAL, summarize, workflow_path
from .checked import ChildUnfinished
from .completion import evaluate_member, capture_member_provenance, capture_parent_provenance
from .legacy import bootstrap_legacy
from .members import WorkflowMembers
from .processing import process_member, validate_member_evidence
from .provenance import project_member, read_parent, read_member, transfer_binding
from .results import freeze_selection


def reuse_exact_binding(value, store, objects):
    acquisition = AcquisitionState(store)
    member = read_member(value, store, objects)
    identity = value['source']['source_id']
    if acquisition.binding(member.workset_id, identity) is not None or member.acquisition_mode == 'refresh':
        return ()
    gaps = []
    source = acquisition.get_source(identity)
    if source is None:
        return ()
    try:
        if source.value['needs_acquisition']:
            return ()
    except (ValueError, KeyError, TypeError) as error:
        return (Error('legacy_member_unresolved', 'source reuse evidence is corrupt: ' + str(error),
                      False, identity, {'member_id': value['member_id']}),)
    candidates = {}
    verified, _ = WorkflowMembers(store, objects).inventory()
    # select_work has already retained inventory gaps; reuse cannot hide them.
    for other in verified:
        if other['source'] != value['source']:
            continue
        try:
            pin = acquisition.binding(other['member_id'], identity)
            if pin is None:
                continue
            snapshot = acquisition.snapshot(identity, pin.snapshot_sha256)
            objects.verify(snapshot.raw_path, snapshot.sha256, snapshot.byte_count)
            candidates[snapshot.sha256] = snapshot
        except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
            gaps.append(Error('legacy_member_unresolved', 'retained reuse pin is corrupt: ' + str(error),
                              False, identity, {'member_id': other['member_id']}))
    if len(candidates) != 1:
        return tuple(gaps)  # Ordinary checked collection establishes its exact binding.
    # Keep winner refusal outside candidate isolation; never overwrite a divergent binding.
    transfer_binding(value, next(iter(candidates.values())), store, objects)
    return tuple(gaps)


def run_workflow(context, settings, intent, dispatcher, store, objects, observer=None):
    registry, acquisition = WorkflowMembers(store, objects), AcquisitionState(store)
    selection_path = workflow_path(context).rsplit('/', 1)[0] + '/selection.json'
    try:
        selection = parse_json(objects.read(selection_path))
        selection = freeze_selection(context, selection, store, objects)
    except FileNotFoundError:
        selection = select_work(context, settings, intent, dispatcher, store, objects)
        selection = freeze_selection(context, selection, store, objects)
        observe(observer, 'workflow.after_selection')
    results, receipt_descriptors, evidences = [], [], []
    halted = selection['halted']
    for job in selection['jobs']:
        value = job['member']
        receipt_path = workflow_path(context).rsplit('/', 1)[0] + '/members/' + value['member_id'] + '/result.json'
        try:
            body = objects.read(receipt_path)
        except FileNotFoundError:
            body = None
        if body is not None:
            saved = parse_json(body)
            if canonical_json(to_mapping_value(saved)) != body or saved['context'] != context.to_mapping():
                raise Conflict('saved member receipt changes frozen context')
            result = MemberResult.from_mapping(saved['result'])
            descriptor = registry.record(result, context, saved['evidence'])
            evidence = saved['evidence']
        elif halted or datetime.now(timezone.utc) >= context.deadline:
            result = MemberResult(value['member_id'], Source.from_mapping(value['source']), value['parent_ref'],
                None, None, (), 'pending', False, False, False, (),
                (Error('workflow_deferred', 'halt/deadline left source undispatched', True,
                       value['source']['source_id'], {}),), context.parser_version, context.schema_version)
            descriptor = evidence = None  # Frozen selection is the undispatched-work authority.
        else:
            processed = process_member(value, context, dispatcher, store, objects, observer)
            result = processed.result
            evidence = parse_json(canonical_json(to_mapping_value(processed.evidence)))
            descriptor = registry.record(result, context, evidence)
            observe(observer, 'workflow.after_member_receipt')
        results.append(result)
        receipt_descriptors.append(descriptor)
        evidences.append(evidence)
        halted = halted or result.outcome in FATAL or any(gap.code in HALTING_OUTCOMES for gap in result.gaps)
    gaps = [Error.from_mapping(value) for value in selection['gaps']]
    gaps.extend(baseline_gaps(selection, tuple(results), evidences, store, objects))
    selected_ids = {result.source.source_id for result in results}
    already = tuple(sorted({capture['member']['source']['source_id'] for capture in selection['already_complete']} - selected_ids))
    outcome, counts = summarize(tuple(results), tuple(gaps), selection['discovered_sources'],
        selection['unresolved_before'], context.command, already)
    after = acquisition.daily_boundary()
    selection_body = objects.read(selection_path)
    child_calls = [] if selection['discovery_call'] is None else [selection['discovery_call']]
    captures = list(selection['already_complete'])
    resolutions = []
    for evidence in evidences:
        if evidence is None:
            continue
        child_calls.extend(evidence['calls'])
        if evidence['completion'] is not None:
            captures.append(evidence['completion'])
        resolutions.extend(evidence['resolutions'])
    report_intent = {'invocation': dict(intent),
        'selection': {'ref': selection_path, 'sha256': hashlib.sha256(selection_body).hexdigest(), 'bytes': len(selection_body)},
        'discovered_sources': selection['discovered_sources'], 'unresolved_before': selection['unresolved_before'],
        'already_complete_sources': list(already), 'member_receipts': receipt_descriptors,
        'completion_captures': captures, 'child_calls': child_calls, 'repair_resolutions': resolutions}
    return WorkflowResult('sec-workflow-result-v1', context, report_intent, selection['parent_ref'],
        tuple(selection['requested_quarters']), tuple(selection['directories']), tuple(results), tuple(gaps),
        selection['boundary_before'], after.isoformat() if after else None, outcome, counts,
        max(context.started_at, datetime.now(timezone.utc)).isoformat())
```

`select_work` and `baseline_gaps` are defined in this task, before this runner can pass. They must produce exactly the T6 schema; use the complete code below with the exact T6 selection schema. Selection is saved before collection/member dispatch, so exact replay never re-discovers or recomputes a queue. The discovery operation itself uses one deterministic ID per parent run/command; different workflow attempts reuse the same discovery session and immutable failed child result is retried only with a new child attempt. A fresh run gets fresh listings.

```python

def select_work(context, settings, intent, dispatcher, store, objects):
    acquisition, registry = AcquisitionState(store), WorkflowMembers(store, objects)
    before = acquisition.daily_boundary()
    gaps = list(bootstrap_legacy(store, objects))
    retained, registry_gaps = registry.inventory()
    gaps.extend(registry_gaps)
    pending_before, unresolved_ids_before = [], set()
    for value in retained:
        try:
            completed = registry.completed(value, context.parser_version, context.schema_version)
        except (ValueError, OSError, Conflict, KeyError, TypeError) as error:
            gaps.append(Error('legacy_member_unresolved', 'retained completion receipt is corrupt: ' + str(error),
                              False, value['source']['source_id'], {'member_id': value['member_id']}))
            completed = None
        if completed is None:
            evaluated = evaluate_member(value, context.parser_version, context.schema_version, store, objects)
            pending_before.append(value)
            if not evaluated.complete:
                unresolved_ids_before.add(value['source']['source_id'])
    known = {value['source']['source_id'] for value in retained}
    mode = 'daily' if context.command == 'daily' else 'quarterly'
    discovery_call = discovery_error = parent_ref = parent = None
    halted = False
    try:
        child = dispatcher.execute('discover', 'discover', settings,
            ('--mode', mode, '--discovery-id', 'workflow-' + context.command + '-' + context.run_id))
        discovery_call = dict(child.call)
        parent_ref = child.result.source_workset_ref
        if parent_ref is not None:
            parent = read_parent(parent_ref, store, objects)
        gaps.extend(child.result.gaps)
        for gap in child.result.gaps:
            normalized = HALTING_OUTCOMES.get(gap.code)
            if normalized is not None:
                gaps.append(Error(normalized, 'shared acquisition halt: ' + gap.message, gap.retryable,
                                  gap.source_id, {'cause': gap.to_mapping()}))
        halted = child.result.outcome in FATAL or any(gap.code in HALTING_OUTCOMES for gap in child.result.gaps)
    except ChildUnfinished as error:
        discovery_call = dict(error.call)
        discovery_error = Error(error.outcome, 'discovery has no durable source result', False, None, error.details)
        gaps.extend(error.gaps)
        halted = True
    current = []
    if parent is not None:
        for source in parent.members:
            value = project_member(parent_ref, source.source_id, store, objects)
            gaps.extend(reuse_exact_binding(value, store, objects))
            current.append(value)
    combined = {value['member_id']: value for value in (*pending_before, *current)}
    selected, complete = [], []
    for value in sorted(combined.values(), key=lambda v: (v['source']['period'], v['source']['source_id'], v['member_id'])):
        evaluation = evaluate_member(value, context.parser_version, context.schema_version, store, objects)
        if evaluation.complete:
            complete.append(evaluation.capture)
        else:
            selected.append(value)
    # Preserve every completed exact unit; reducer counts exclude selected source IDs.
    end = intent['pinned_end_quarter']
    requested = () if context.command == 'daily' else quarter_span(settings.backfill.start_quarter, end)
    for quarter in requested:
        if parent is None or not any(source.kind == 'quarterly' and source.period == quarter for source in parent.members):
            gaps.append(Error('baseline_source_missing', 'requested quarter has no validated source', True,
                              None, {'quarter': quarter}))
    session_row = acquisition.discovery_session('workflow-' + context.command + '-' + context.run_id)
    session = None if session_row is None else session_row.to_mapping()['value']
    parent_provenance = None if parent_ref is None else capture_parent_provenance(parent_ref, store, objects)
    if parent_provenance is not None:
        session = parent_provenance['discovery']['session']
    required = [] if session is None else session['frozen']['units']
    values = sorted(selected, key=lambda v: (v['source']['period'], v['source']['source_id'], v['member_id']))
    return {'format_version': 'sec-workflow-selection-v1', 'context': context.to_mapping(),
        'invocation': dict(intent), 'members': values, 'jobs': [{'member': value, 'aliases': [value]} for value in selected],
        'member_provenance': [capture_member_provenance(value, store, objects) for value in values],
        'already_complete': complete, 'discovery_call': discovery_call,
        'discovery_error': None if discovery_error is None else discovery_error.to_mapping(),
        'parent_ref': parent_ref, 'parent_provenance': parent_provenance,
        'discovery_session': session, 'required_units': required,
        'requested_quarters': list(requested),
        'directories': [] if parent is None else [directory.to_mapping() for directory in parent.directories],
        'halted': halted, 'boundary_before': before.isoformat() if before else None,
        'gaps': [gap.to_mapping() for gap in gaps],
        'discovered_sources': len({value['source']['source_id'] for value in current} - known),
        'unresolved_before': len(unresolved_ids_before)}


def baseline_gaps(selection, results, evidences, store, objects):
    gaps = []
    parent = None if selection['parent_ref'] is None else read_parent(selection['parent_ref'], store, objects)
    independent = (bool(selection['gaps']) or selection['halted'] or parent is None
                   or not parent.discovery_complete
                   or {unit['url'] for unit in selection['required_units']} != {d.url for d in parent.directories})
    for result, evidence in zip(results, evidences, strict=True):
        if evidence is not None:
            validate_member_evidence(result, evidence, objects)
        elif result.quarantined:
            raise Conflict('baseline quarantine attribution lacks checked stored receipt')
    refused = {result.source.source_id for result in results if result.quarantined and result.outcome not in ('pending', 'deferred')}
    by_source = {value['source']['source_id']: value for value in selection['members']}
    for quarter in selection['requested_quarters']:
        if capture_quarter(quarter, objects, EtlState(store)) is not None:
            continue
        causes = sorted(source_id for source_id, value in by_source.items()
                        if value['source']['kind'] == 'quarterly' and value['source']['period'] == quarter)
        details = {'quarter': quarter}
        if not independent and causes and set(causes) <= refused:
            # Earlier validators establish exact listings/selection/refusal, not this marker alone.
            details.update(coverage_cause='selected_source_quarantine', source_ids=causes)
        gaps.append(Error('baseline_publication_missing', 'requested baseline quarter lacks readable generation',
                          True, None, details))
    return tuple(gaps)
```

Before deriving F5 attribution validate every refused member's stored T5 child/evidence receipt, successful original complete discovery/required ledger, exact baseline source selection, and actual publication absence. No pointer glob/boolean may stand in for this check. Independent missing sources/directories/legacy/repair gaps stay unmarked. All-quarantined + no prior pointer retains baseline gaps and returns7; mixed valid progress returns3, including skipped complete captures. Normalize acquisition fatal gap codes through shipped collection.HALTING_OUTCOMES before reducing/reporting; access/ownership/shared-state failures halt subsequent acquisition immediately even with a source workset. A no-result discovery whose source parent is absent retains its frozen required session ledger and every older job pending. No deadline-expired source is silently dropped.

- [ ] Run scoped real-store cases for F1 Q3→Q4 after successful initial Q3 publication, valid empty fresh daily backlog, F3 ordinary post-CAS failure and process death, same-attempt replay, expired-original/new-valid repair, gate-only state, mixed gates/progress, failed-boundary hold, two parent commands sharing IDs and fresh vs exact replay. Discovery boundary/report source coverage are separate; no maximum date produces coverage.
- [ ] Run guarded runner, completion, processing, results and legacy tests. Expected PASS; inspect exact pointer/binding/request histories. Commit owned paths with `feat: assemble durable backfill and daily workflow coverage`; fresh review checks every selected unit and all affected quarters.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_runner.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/workflows/runner.py packages/sec-edgar-ingest/tests/test_workflow_runner.py
git commit -m "feat: assemble durable backfill and daily workflow coverage"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 9: Public workflow CLI lifecycle and operator documentation

**Files:** Modify `packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py`; create `packages/sec-edgar-ingest/tests/test_workflow_cli.py`; edit `packages/sec-edgar-ingest/README.md` and the existing `docs/runbooks/sec-edgar-ingest-acquisition.md`; add the workflow recovery cross-reference to existing `docs/runbooks/sec-edgar-etl-publication.md`. Their current command/installation/reader sections are the placement anchors. This task consumes T1–T8 and changes no dependency.

**Interfaces:** Preserve `main(argv:Sequence[str]|None=None)->int`. The only public workflow arguments are `backfill|daily --config PATH --run-id ID --execution-id ID --attempt-id ID --deadline UTC [--state-dir PATH --fixture-pack PATH --today YYYY-MM-DD]`. Invocation is exactly `{command,today,fixture_sha256,pinned_end_quarter}`: `today` preserves the supplied string or `None`; the context separately records the pinned date. T8 consumes `pinned_end_quarter`. T6 owns canonical `intent.json`, `selection.json`, report and repairable WorkflowAttempt index. T3 owns each actual child invocation.

- [ ] Add the failing tests below before implementing the branch. Run the guarded scoped command; retain the actual failure, initially argparse's missing workflow commands. Keep all existing acquisition/ETL tests.
- [ ] Replace `_parser` with this complete function. No workflow parser receives `--mode`, `--discovery-id`, `--refresh`, `--workset` or `--force`.

```python
def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='sec-edgar-ingest')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command')
    for command in ('discover', 'collect', 'transform', 'publish', 'backfill', 'daily'):
        sub = commands.add_parser(command)
        for name in ('config', 'run-id', 'execution-id', 'attempt-id', 'deadline'):
            sub.add_argument('--' + name, required=True)
        for name in ('state-dir', 'today'):
            sub.add_argument('--' + name)
        if command in ('discover', 'collect', 'backfill', 'daily'):
            sub.add_argument('--fixture-pack')
        if command == 'discover':
            sub.add_argument('--mode', required=True, choices=('quarterly', 'daily'))
            sub.add_argument('--discovery-id', required=True)
            sub.add_argument('--refresh', action='store_true')
        elif command in ('collect', 'transform', 'publish'):
            sub.add_argument('--workset', required=True)
        if command == 'transform':
            sub.add_argument('--force', action='store_true')
    return parser
```

- [ ] Insert this exact main branch after help and before regular command validation. Child command paths remain unchanged.

```diff
 def main(argv: Sequence[str] | None = None) -> int:
     parser = _parser()
     args = parser.parse_args(argv)
     if args.command is None:
         parser.print_help()
         return 0
+    if args.command in ('backfill', 'daily'):
+        return _workflow_main(args)
     try:
         settings, today, deadline, pack = _validate(args)
```

- [ ] Add the following helpers and imports to `cli.py`.

```python
from .models import to_mapping_value
import hashlib
from .workflows.checked import Dispatcher as WorkflowDispatcher, ChildUnfinished
from .workflows.contracts import workflow_path
from .workflows.results import freeze_workflow, read_workflow_result, write_workflow_result
from .workflows.runner import run_workflow


def _validate_workflow(args):
    for name in ('run_id', 'execution_id', 'attempt_id'):
        _segment(getattr(args, name), name)
    settings = load_config(Path(args.config))
    supported_parser(settings.etl.parser_version,
                     fixture=settings.storage.backend == 'local-fixture')
    if settings.etl.schema_version != SCHEMA_VERSION:
        raise ValueError('unsupported ETL schema version')
    if not settings.coordination.lease_seconds.is_integer():
        raise ValueError('coordination requires whole finite lease seconds')
    deadline = datetime.fromisoformat(args.deadline.replace('Z', '+00:00'))
    if deadline.utcoffset() != timezone.utc.utcoffset(deadline):
        raise ValueError('deadline must be timezone-aware UTC')
    today = date.fromisoformat(args.today) if args.today else None
    if args.today and today.isoformat() != args.today:
        raise ValueError('today must be a canonical ISO date')
    if settings.storage.backend == 'azure':
        if args.fixture_pack or args.state_dir or args.today:
            raise ValueError('fixture pack, state directory and date override are fixture-only')
        pack = None
    else:
        if not args.fixture_pack:
            raise ValueError('local-fixture workflow requires an explicit fixture pack')
        if args.today and (not settings.fixture or not settings.fixture.allow_clock_override):
            raise ValueError('today requires the explicit fixture clock override marker')
        pack = FixturePack.load(Path(args.fixture_pack))
    # Do not construct a fresh context here: the immutable saved pin must be read first.
    return settings, today, deadline, pack


def _workflow_frozen(path, objects):
    try:
        body = objects.read(path)
    except FileNotFoundError:
        return None
    value = parse_json(body)
    if (not isinstance(value, dict) or set(value) != {'context', 'intent'}
            or canonical_json(to_mapping_value(value)) != body):
        raise Conflict('workflow intent is not exact canonical context/intent')
    RunContext.from_mapping(value['context'])
    if (not isinstance(value['intent'], dict)
            or set(value['intent']) != {'command', 'today', 'fixture_sha256', 'pinned_end_quarter'}):
        raise Conflict('workflow invocation fields differ')
    return value


def _workflow_saved(args, store, objects):
    path = f'runs/sec/{args.run_id}/{args.command}/{args.attempt_id}/intent.json'
    frozen = _workflow_frozen(path, objects)
    if frozen is not None: return frozen
    # T6 begins its conditional index before writing intent bytes. Reopen that
    # actual durable start/pin if a process died between those two writes.
    key = hashlib.sha256(canonical_json(to_mapping_value([args.run_id, args.command, args.attempt_id]))).hexdigest()
    row = store.get('WorkflowAttempt', key)
    if row is None: return None
    value = row.to_mapping()['value']
    if set(value) != {'context', 'intent', 'selection_ref', 'result_ref'}:
        raise Conflict('workflow begun index fields differ')
    saved = RunContext.from_mapping(value['context'])
    if (saved.run_id, saved.command, saved.attempt_id) != (args.run_id, args.command, args.attempt_id):
        raise Conflict('workflow begun index correlation differs')
    if not isinstance(value['intent'], dict) or set(value['intent']) != {
            'command', 'today', 'fixture_sha256', 'pinned_end_quarter'}:
        raise Conflict('workflow begun invocation fields differ')
    return {'context': value['context'], 'intent': value['intent']}


def _workflow_context(args, settings, today, deadline, started, pinned):
    context = RunContext(args.run_id, args.execution_id, args.command, args.attempt_id,
        settings.worker.image_digest, settings.etl.parser_version, settings.etl.schema_version,
        settings.config_sha256, started, deadline, args.command)
    return pin_context(settings, context, today or pinned or started.date())


def _workflow_stdout(result, reference):
    sys.stdout.write(canonical_json(to_mapping_value({'outcome': result.outcome, 'result_ref': reference,
        'source_workset_ref': result.source_workset_ref,
        'counts': result.to_mapping()['counts']})).decode() + '\n')
    return exit_code(result.outcome)


def _workflow_main(args):
    try:
        settings, today, deadline, pack = _validate_workflow(args)
    except (ValueError, OSError, TypeError) as error:
        sys.stderr.write(canonical_json(to_mapping_value({'outcome': 'configuration', 'error': str(error)})).decode() + '\n')
        return 2
    opened, context = (), None
    try:
        opened = open_stores(settings, base_path=Path(args.state_dir) if args.state_dir else None)
        store, objects, leases = opened
        frozen = _workflow_saved(args, store, objects)
        saved = None if frozen is None else RunContext.from_mapping(frozen['context'])
        started = saved.started_at if saved is not None else Clock().now()
        pinned = saved.pinned_on if saved is not None else None
        # Exact supplied correlation/config/image/versions/deadline is compared by T6.
        # An omitted date reuses the saved pin, even after the calendar changes.
        if saved is None and deadline <= Clock().now():
            raise _ExpiredAttempt('an expired deadline permits only exact completed-result replay')
        try:
            context, end = _workflow_context(args, settings, today, deadline, started, pinned)
        except ValueError as error:
            if saved is None: raise _ExpiredAttempt(str(error)) from error
            raise
        intent = {'command': args.command, 'today': args.today,
            'fixture_sha256': pack.manifest_sha256 if pack is not None else None,
            'pinned_end_quarter': end}
        context = freeze_workflow(context, intent, store, objects)
        try:
            completed = read_workflow_result(workflow_path(context), store, objects)
        except FileNotFoundError:
            completed = None
        if completed is not None:
            log_event(context, 'result_replayed', {'result_ref': workflow_path(context)})
            return _workflow_stdout(completed, workflow_path(context))
        # Adapters belonging to children are constructed only inside their public CLI paths.
        dispatcher = WorkflowDispatcher(context, settings,
            Path(args.fixture_pack) if args.fixture_pack else None,
            Path(args.state_dir) if args.state_dir else None, store, objects)
        log_event(context, 'command_started', {'command': args.command})
        result = run_workflow(context, settings, intent, dispatcher, store, objects)
        reference = write_workflow_result(result, store, objects)
        log_event(context, 'command_finished', {'outcome': result.outcome,
            'result_ref': reference, 'counters': result.to_mapping()['counts']})
        return _workflow_stdout(result, reference)
    except Exception as exception:
        outcome = ('configuration' if isinstance(exception, (_ExpiredAttempt, TimeoutError)) else
            'ownership_lost' if isinstance(exception, (OwnershipLost, ClockUncertain)) else
            'state_conflict' if isinstance(exception, (Conflict, ValueError, OSError, KeyError)) else
            'internal_error')
        details = {'type': type(exception).__name__}
        if isinstance(exception, ChildUnfinished):
            outcome = exception.outcome
            details.update(exception.details)
        error = Error(outcome, str(exception),
            isinstance(exception, ChildUnfinished) and exception.resumable, None, details)
        if context is not None:
            log_event(context, 'command_error', {'outcome': outcome, 'error': error.to_mapping()})
        else:
            sys.stderr.write(canonical_json(to_mapping_value({'outcome': outcome, 'error': error.to_mapping()})).decode() + '\n')
        sys.stdout.write(canonical_json(to_mapping_value({'outcome': outcome, 'result_ref': None,
            'source_workset_ref': None, 'counts': None})).decode() + '\n')
        return exit_code(outcome)
    finally:
        for resource in reversed(opened):
            if hasattr(resource, 'close'):
                resource.close()
```

The adopted T1 WorkflowResult's parent reference field is `source_workset_ref`; MemberResult's corresponding field is `parent_ref`. Use those exact codec names throughout.

The tests below use production main, real local stores and canonical reports. Every helper is defined here or in T2. Adapter rejection is tested before any store is opened; changed completed intent is tested as a durable conflict after storage opens. Completed report replay repairs only its checked descriptor index and consumes no fixture response.

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import contextlib, io, json, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from support import fixture_settings
from support_workflows import CommandHarness, simple_pack
from sec_edgar_ingest.cli import main
from sec_edgar_ingest.models import canonical_json
from sec_edgar_ingest.storage.contracts import Conflict
from sec_edgar_ingest.workflows.results import read_workflow_result


def cli_call(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, json.loads(out.getvalue()) if out.getvalue() else None, err.getvalue()


class WorkflowCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.h = CommandHarness(self.root, simple_pack(self.root / 'pack'))
        self.addCleanup(self.h.close)

    def report(self, message):
        return read_workflow_result(message['result_ref'], self.h.store, self.h.objects)

    def test_public_commands_inclusive_baseline_and_daily_reader(self):
        code, message = self.h.invoke('backfill', run='baseline')
        self.assertEqual(code, 0, self.h.calls[-1])
        report = self.report(message)
        self.assertEqual(report.requested_quarters, ('2026Q3', '2026Q4'))
        self.assertEqual(report.counts['complete_sources'], 2)
        self.assertEqual(report.counts['quarantined_sources'], 0)
        self.assertEqual(len(self.h.capture('2026Q3')[1]), 1)
        self.assertEqual(len(self.h.capture('2026Q4')[1]), 1)
        code, daily = self.h.invoke('daily', run='overlap')
        self.assertEqual(code, 0, self.h.calls[-1])
        self.assertEqual(self.report(daily).counts['complete_sources'], 1)
        self.assertEqual(len(self.h.capture('2026Q4')[1]), 1)

    def test_completed_exact_replay_after_deadline_constructs_no_dispatcher(self):
        code, message = self.h.invoke('backfill')
        self.assertEqual(code, 0)
        saved = self.report(message)
        body = self.h.objects.read(message['result_ref'])
        cursors = tuple(r.to_mapping() for r in self.h.store.scan('FixtureResponseCursor', {}))
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=saved.context.deadline + timedelta(days=1)), \
             patch('sec_edgar_ingest.cli.WorkflowDispatcher', side_effect=AssertionError('replay dispatched')):
            code, replay, _ = cli_call(self.h.calls[0]['argv'])
        self.assertEqual((code, replay), (0, message))
        self.assertEqual(self.h.objects.read(message['result_ref']), body)
        self.assertEqual(tuple(r.to_mapping() for r in self.h.store.scan('FixtureResponseCursor', {})), cursors)

    def test_changed_exact_invocation_is_conflict_and_report_stays_immutable(self):
        self.h.invoke('backfill')
        argv = self.h.calls[0]['argv']
        original = self.h.objects.read(self.h.calls[0]['stdout']['result_ref'])
        for flag, value in (('--execution-id', 'other'), ('--today', '2026-10-08'),
                            ('--deadline', (self.h.deadline + timedelta(seconds=1)).isoformat())):
            changed = list(argv)
            changed[changed.index(flag) + 1] = value
            code, message, _ = cli_call(changed)
            self.assertEqual(code, 9, message)
            self.assertIsNone(message['result_ref'])
        self.assertEqual(self.h.objects.read(self.h.calls[0]['stdout']['result_ref']), original)

    def test_omitted_today_reopens_saved_pin_before_next_day_validation(self):
        self.h.settings = fixture_settings(
            backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            etl={'parser_version': 'fixture-index-parser-v1'},
            fixture={'allow_clock_override': True, 'allow_deadline_override': True})
        self.h.config.write_bytes(canonical_json(to_mapping_value(self.h.settings.to_mapping())))
        self.h.invoke('backfill', run='template')
        argv = list(self.h.calls[-1]['argv'])
        argv[argv.index('--run-id') + 1] = 'implicit-date'
        index = argv.index('--today')
        del argv[index:index + 2]
        first = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=first):
            code, message, _ = cli_call(argv)
        self.assertEqual(code, 0)
        saved = self.report(message)
        with patch('sec_edgar_ingest.cli.Clock.now', return_value=first + timedelta(days=1)), \
             patch('sec_edgar_ingest.cli.WorkflowDispatcher', side_effect=AssertionError('replay dispatched')):
            code, again, _ = cli_call(argv)
        self.assertEqual((code, again), (0, message))
        self.assertEqual(saved.context.pinned_on.isoformat(), '2026-10-07')

    def test_invalid_input_precedes_backend_construction_and_child_flags_stay_private(self):
        self.h.invoke('backfill')
        argv = list(self.h.calls[0]['argv'])
        argv[argv.index('--run-id') + 1] = '../escape'
        with patch('sec_edgar_ingest.cli.open_stores', side_effect=AssertionError('invalid input opened stores')):
            self.assertEqual(cli_call(argv)[0], 2)
        for flags in (('--force',), ('--refresh',), ('--workset', 'x'), ('--mode', 'daily')):
            with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
                main([*self.h.calls[0]['argv'], *flags])
            self.assertEqual(caught.exception.code, 2)

    def test_failure_closes_all_opened_resources_and_writes_no_report(self):
        import sec_edgar_ingest.cli as cli
        original, closed = cli.open_stores, []
        class ClosingProxy:
            def __init__(self, resource): self.resource = resource
            def __getattr__(self, name): return getattr(self.resource, name)
            def close(self):
                closed.append(type(self.resource).__name__)
                if hasattr(self.resource, 'close'): self.resource.close()
        def open_checked(*args, **kwargs):
            return tuple(ClosingProxy(r) for r in original(*args, **kwargs))
        with patch.object(cli, 'open_stores', side_effect=open_checked), \
             patch.object(cli, 'run_workflow', side_effect=Conflict('retained state conflict')):
            code, message = self.h.invoke('daily', run='conflict')
        self.assertEqual(code, 9)
        self.assertIsNone(message['result_ref'])
        self.assertEqual(len(closed), 3)
        with self.assertRaises(FileNotFoundError):
            self.h.objects.read('runs/sec/conflict/daily/a/result.json')
```

- [ ] Run `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_workflow_cli.py' -v`. Expect PASS only after full T1–T8 integration; fix any genuine contract mismatches before broadening checks.
- [ ] Run the same guarded command for `test_cli.py` and `test_etl_cli.py`; verify child flags, validation ordering and shipped exits remain correct. Commit only owned paths with `feat: expose checked backfill and daily workflow commands`; perform task review before T10.

Insert this operator text into the README and runbook under their existing command/provenance sections, using the existing document style:

> `backfill` and `daily` run the existing discover, collect, transform and publish commands through checked durable child results. Backfill takes inclusive endpoints from `backfill.start_quarter` and `backfill.end_quarter`; `open` resolves once when the invocation is pinned. Daily starts at the accepted `2026-10-01` handoff, discovers current/preceding and outage-spanning quarters, and retries every retained unresolved exact member. A missing newer listing does not withdraw an older source.
>
> Example fixture invocation: `sec-edgar-ingest backfill --config /absolute/local.json --run-id baseline-2026 --execution-id manual-1 --attempt-id attempt-1 --deadline 2026-10-08T13:00:00Z --state-dir /absolute/fixture-state --fixture-pack /absolute/manifest.json --today 2026-10-08`. Use `daily` with the same argument shape for handoff/catch-up. The config/fixture/date/state overrides are explicit fixture controls; the Azure backend refuses fixture overrides. Live identities, storage access, deployment and schedules require their later-stage authorization.
>
> Keep every correlation ID, config byte identity, image/parser/schema version, deadline, fixture manifest hash and supplied date unchanged for an exact retry. A completed report can replay after its deadline and returns its original captured generations. An unfinished expired invocation requires a new valid attempt; its original evidence stays immutable. Reports live at `runs/sec/<run-id>/<backfill|daily>/<attempt-id>/result.json`. The immutable report precedes its repairable index.
>
> Source counts and quarter operations have different labels: `complete_sources`, `pending_sources`, `failed_sources`, `quarantined_sources`, `published_quarters`, `unchanged_quarters`, and `awaiting_approval_quarters`. A valid empty quarterly directory is an unresolved baseline unit. Daily returns `no_new_sources` only with successful required listings and no unresolved work. Quarantine is a terminal whole-source refusal; retained failed retry prefixes remain transport evidence when a later body succeeds. Gated or partially published sources remain pending/failed until every affected quarter is complete. Closed-quarter removal needs Stage 5 approval; there is no workflow force bypass.
>
> Exit codes remain: 0 success/no-new/unchanged; 2 invalid inputs or unfinished expired deadline; 3 incomplete/discovery failure; 4 pending; 5 retry/deferred/throttled; 6 access blocked; 7 whole-source quarantine/invalid source; 8 lost ownership; 9 state/internal/publication conflict; 10 awaiting approval. A publish crash after pointer CAS remains an explicit repair obligation. Retry through the checked command boundary; a pointer alone does not prove member completion, and repair must not advance the pointer twice. Use `capture_quarter` then `read_quarter` to read the captured validated generation rather than globbing files or selecting a mutable latest snapshot.
>
> Offline native and installed-wheel proofs cover these fixture workflows and immutable evidence. They do not establish historical production coverage, deployed integration or complete-worker resource fit. All 22 Stage 7 checks remain reserved/not_run. Stage 5 owns reconciliation/approval, Stage 6 owns the worker/IaC/disabled schedules, Stage 7 owns integrated checks, and Stage 8 owns production activation/coverage.

Replace the README's stale final statement that Stage 3 acceptance is blocked by SEC-0141–0143 with: “The owner amended Stage 3 acceptance on 2026-10-07 to allow exactly the documented SEC-0141, SEC-0142 and SEC-0143 whole-source quarantines for 21, 24 and 6 conflicting observations. No source, duplicate winner or zero-row parser exception is approved. Other invalid retained rows or missing offline dependencies remain blockers; all 22 later integrated checks remain reserved/not_run.” Link to the existing Stage 3 verification record. Append this concrete ETL runbook sentence: “Public `backfill`/`daily` workflows use these same transform/publish and captured-reader boundaries; their source counters, frozen invocation and unresolved post-CAS repair are described in [acquisition recovery](sec-edgar-ingest-acquisition.md).”



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_cli.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/src/sec_edgar_ingest/cli.py packages/sec-edgar-ingest/tests/test_workflow_cli.py packages/sec-edgar-ingest/README.md docs/runbooks/sec-edgar-ingest-acquisition.md docs/runbooks/sec-edgar-etl-publication.md
git commit -m "feat: expose checked backfill and daily workflow commands"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 10: Real public command, process recovery and reader proof

**Files:** Create `packages/sec-edgar-ingest/tests/workflow_proof.py`, `test_workflow_process.py`, `test_workflow_acceptance.py`; add fixed synthetic fixtures under `packages/sec-edgar-ingest/tests/fixtures/workflows/proof/`; extend `support_workflows.py` only with the helpers explicitly listed below. No new runtime/test dependency. The proof code is test-only and imports production CLI/reader/results; it does not implement an alternate workflow.

**Interfaces consumed by T11:** `sequence(output:Path)->Mapping[str,object]`, `harness_files()->tuple[Path,...]`, `native(output:Path)->Mapping[str,object]`. `output` already exists, is otherwise empty, and belongs to a create-only top-level proof directory. Every call's argv/exit/stdout/stderr and every checked fixture/result/reader capture is retained. T11 supplies the script main/native|installed mode parser, exact inventory verifier and installed wrapper. Until T11, tests call these functions directly; no unreviewed standalone script main is needed.

- [ ] Write the fixed fixture generator and proof functions below, then their meaningful failing tests before any fixes to T1–T9. The fixed fixture files must be generated once during implementation and reviewed as synthetic bytes. Expected rows are specified separately from runtime reports. Check parser `fixture-index-parser-v1`, schema v1, 90-second exchange cap, and the existing received/expanded-byte caps from the local config; no synthetic extra preamble, zero-row source or parser exception is permitted.

```python
# tests/workflow_proof.py
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import contextlib, hashlib, io, json, multiprocessing, os, shutil, tempfile, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from support import fixture_settings
from support_workflows import BASE, CommandHarness, listing, idx, build_pack, simple_pack
from sec_edgar_ingest.models import canonical_json, parse_json
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.workflows.results import read_workflow_result

FIXTURE_ROOT = Path(__file__).resolve().parent / 'fixtures/workflows/proof'
BODY_FILES = ('full-root.json', 'full-year.json', 'full-q3.json', 'full-q4.json',
              'full-q3.zip', 'full-q4.zip', 'daily-root.json', 'daily-year.json',
              'daily-q3.json', 'daily-q4.json', 'daily-q4.idx')
EXPECTED = {'2026Q3': [{'cik': '0000123456', 'company_name': 'Example', 'form_type': '10-K',
    'filing_date': '2026-09-30', 'archive_path': 'edgar/data/123456/0000123456-26-000003.txt'}],
    '2026Q4': [{'cik': '0000123456', 'company_name': 'Example', 'form_type': '10-K',
    'filing_date': '2026-10-01', 'archive_path': 'edgar/data/123456/0000123456-26-000004.txt'}]}


def write_proof_fixtures(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    responses, values = {}, {}
    for family, tag in (('full-index', 'full'), ('daily-index', 'daily')):
        base = BASE + family + '/'
        values[tag + '-root.json'] = (base + 'index.json', listing(base + 'index.json', [('2026', 'dir')]))
        values[tag + '-year.json'] = (base + '2026/index.json', listing(base + '2026/index.json', [('QTR3', 'dir'), ('QTR4', 'dir')]))
        for quarter in (3, 4):
            leaf = base + f'2026/QTR{quarter}/'
            name = 'master.zip' if family == 'full-index' else 'master.20261001.idx'
            children = [] if family == 'daily-index' and quarter == 3 else [(name, 'file')]
            values[tag + f'-q{quarter}.json'] = (leaf + 'index.json', listing(leaf + 'index.json', children))
            if children:
                day = '2026-09-30' if quarter == 3 else '2026-10-01'
                if family == 'daily-index': day = day.replace('-', '')
                rows = [('123456', 'Example', '10-K', day, EXPECTED[f'2026Q{quarter}'][0]['archive_path'])]
                extension = '.zip' if family == 'full-index' else '.idx'
                values[tag + f'-q{quarter}' + extension] = (leaf + name, idx(rows, 'quarterly' if family == 'full-index' else 'daily'))
    if set(values) != set(BODY_FILES):
        raise AssertionError('fixed proof fixture inventory differs')
    for name in BODY_FILES:
        url, body = values[name]
        (destination / name).write_bytes(body)
        spec = {'status': 200, 'headers': {'Content-Length': str(len(body)), 'X-Fixture': 'synthetic'},
                'body_path': name, 'body_sha256': hashlib.sha256(body).hexdigest()}
        responses[url] = [dict(spec) for _ in range(16)]
    (destination / 'manifest.json').write_bytes(canonical_json(to_mapping_value({
        'fixture_version': 'sec-acquisition-fixture-v1', 'provenance': 'synthetic', 'responses': responses})))
    (destination / 'expected.json').write_bytes(canonical_json(to_mapping_value(EXPECTED)))


def harness_files():
    root = Path(__file__).resolve().parent
    fixed = ('support_workflows.py', 'workflow_proof.py', 'network_guard.py',
             'support.py', 'support_etl.py', 'fixtures/config/local.json')
    values = tuple(root / name for name in fixed) + tuple(
        FIXTURE_ROOT / name for name in ('manifest.json', 'expected.json', *BODY_FILES))
    if any(not path.is_file() for path in values):
        raise ValueError('a fixed test-only harness file is missing')
    return values


def put_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical_json(to_mapping_value(value)))


def assert_rows(harness, quarter, expected):
    capture, rows = harness.capture(quarter)
    names = ('cik', 'company_name', 'form_type', 'filing_date', 'archive_path')
    actual = sorted(({name: row[name] for name in names} for row in rows),
                    key=lambda row: (row['archive_path'], row['filing_date']))
    wanted = sorted(expected, key=lambda row: (row['archive_path'], row['filing_date']))
    if actual != wanted or len(rows) != len(expected):
        raise AssertionError({'quarter': quarter, 'actual': actual, 'expected': wanted})
    return {'capture': capture.to_mapping(), 'rows': rows, 'logical_rows': len(rows)}


def durable_report(harness, message):
    if not message.get('result_ref'):
        raise AssertionError('workflow command has no durable report')
    result = read_workflow_result(message['result_ref'], harness.store, harness.objects)
    if result.outcome != message['outcome'] or result.to_mapping()['counts'] != message['counts']:
        raise AssertionError('stdout differs from checked durable workflow report')
    return result


def sequence(output):
    output = Path(output)
    if not output.is_dir() or any(output.iterdir()):
        raise ValueError('sequence requires an existing empty create-only output directory')
    expected = json.loads((FIXTURE_ROOT / 'expected.json').read_text())
    if expected != EXPECTED:
        raise AssertionError('checked fixture expected rows differ')
    fixture = output / 'fixture'
    shutil.copytree(FIXTURE_ROOT, fixture)
    work = output / 'work'
    work.mkdir()
    h = CommandHarness(work, fixture / 'manifest.json')
    reports, readers = {}, {}
    try:
        for command, run in (('backfill', 'proof-baseline'), ('daily', 'proof-overlap'),
                             ('backfill', 'proof-repeat')):
            code, message = h.invoke(command, run=run)
            if code != 0: raise AssertionError(h.calls[-1])
            result = durable_report(h, message)
            if result.counts['quarantined_sources'] != 0 or result.counts['pending_sources'] or result.counts['failed_sources']:
                raise AssertionError(result.to_mapping())
            if run == 'proof-baseline' and (result.requested_quarters != ('2026Q3', '2026Q4') or result.counts['complete_sources'] != 2):
                raise AssertionError('inclusive baseline source accounting differs')
            if run == 'proof-overlap' and result.counts['complete_sources'] != 1:
                raise AssertionError('daily overlap source accounting differs')
            if run == 'proof-repeat' and (result.outcome != 'unchanged' or result.counts['complete_sources'] != 2):
                raise AssertionError('fresh unchanged repeat differs')
            reports[run] = result.to_mapping()
            readers[run] = {quarter: assert_rows(h, quarter, expected[quarter]) for quarter in expected}
        original = h.calls[0]
        before = h.objects.read(original['stdout']['result_ref'])
        cursors = tuple(row.to_mapping() for row in h.store.scan('FixtureResponseCursor', {}))
        code, replay = h.invoke('backfill', run='proof-baseline')
        if code != 0 or replay != original['stdout'] or h.objects.read(replay['result_ref']) != before:
            raise AssertionError('exact command replay changed report authority')
        if tuple(row.to_mapping() for row in h.store.scan('FixtureResponseCursor', {})) != cursors:
            raise AssertionError('exact completed replay consumed a fixture response')
        put_json(output / 'commands.json', h.calls)
    finally:
        h.close()
    legacy = output / 'legacy'
    legacy.mkdir()
    old = CommandHarness(legacy, fixture / 'manifest.json')
    try:
        code, found = old.invoke('discover', ('--mode', 'daily', '--discovery-id', 'old-child-only'), run='legacy-discover')
        if code != 0: raise AssertionError(old.calls[-1])
        code, collected = old.invoke('collect', ('--workset', found['source_workset_ref']), run='legacy-collect')
        if code != 0 or tuple(old.store.scan('WorkflowMember', {})):
            raise AssertionError('legacy setup must consist only of shipped child commands')
        code, message = old.invoke('daily', run='legacy-workflow')
        if code != 0: raise AssertionError(old.calls[-1])
        result = durable_report(old, message)
        if result.counts['complete_sources'] != 1 or result.counts['quarantined_sources']:
            raise AssertionError('legacy backlog source accounting differs')
        reports['legacy-workflow'] = result.to_mapping()
        readers['legacy-workflow'] = {'2026Q4': assert_rows(old, '2026Q4', expected['2026Q4'])}
        put_json(output / 'legacy-commands.json', old.calls)
    finally:
        old.close()
    put_json(output / 'checked-reports.json', reports)
    put_json(output / 'reader-captures.json', readers)
    return {'exit': 0, 'reports': reports, 'reader_captures': readers,
            'all22_stage7_checks': 'reserved/not_run'}
```

The test-only process worker below terminates with `os._exit(91)` at an actual named durable production boundary. It runs the public CLI; mocks install observers/faults only and never supply a successful result. The parent always closes before launch and reopens after death, so cached Python objects cannot satisfy recovery. Each marker is fsynced before termination. A fresh resumed CLI command must validate all durable evidence again.

```python
from sec_edgar_ingest.models import to_mapping_value
# Continue tests/workflow_proof.py; definitions precede native() and test users.
def process_worker(config, pack, state_dir, argv, point, marker):
    import sec_edgar_ingest.cli as cli
    from sec_edgar_ingest.workflows.checked import Dispatcher
    from sec_edgar_ingest.workflows.runner import run_workflow as actual_runner
    from sec_edgar_ingest.workflows.results import write_workflow_result as actual_report
    import sec_edgar_ingest.workflows.results as workflow_results
    actual_index = workflow_results._index
    from sec_edgar_ingest.etl.commands import run_publish as actual_publish, write_etl_result as actual_etl_result
    def boundary(name):
        if name != point: return
        with Path(marker).open('xb') as stream:
            stream.write(canonical_json(to_mapping_value({'point': name, 'pid': os.getpid()})))
            stream.flush()
            os.fsync(stream.fileno())
        os._exit(91)
    def dispatch(*args, **kwargs):
        kwargs['observer'] = boundary
        return Dispatcher(*args, **kwargs)
    def runner(*args, **kwargs):
        kwargs['observer'] = boundary
        return actual_runner(*args, **kwargs)
    def report(*args, **kwargs):
        kwargs['observer'] = boundary
        return actual_report(*args, **kwargs)
    def publish(*args, **kwargs):
        kwargs['observer'] = boundary
        return actual_publish(*args, **kwargs)
    def etl_result(*args, **kwargs):
        kwargs['observer'] = boundary
        return actual_etl_result(*args, **kwargs)
    def begun_index(*args, **kwargs):
        result = actual_index(*args, **kwargs)
        boundary('workflow.after_attempt_begin')
        return result
    with patch.object(cli, 'WorkflowDispatcher', side_effect=dispatch), \
         patch.object(cli, 'run_workflow', side_effect=runner), \
         patch.object(cli, 'write_workflow_result', side_effect=report), \
         patch.object(cli, 'run_publish', side_effect=publish), \
         patch.object(cli, 'write_etl_result', side_effect=etl_result), \
         patch.object(workflow_results, '_index', side_effect=begun_index), \
         patch.object(cli._NoFaults, 'hit', lambda self, name: boundary('collection.' + name)):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(argv)
    put_json(Path(marker).with_suffix('.unexpected.json'), {'exit': code, 'point': point})
    raise SystemExit(92)


PROCESS_POINTS = ('workflow.after_attempt_begin', 'workflow_child.after_call', 'collection.after_binding',
    'workflow_child.after_result', 'workflow.after_selection',
    'publication.after_pointer', 'publication.after_repair', 'etl_result.after_object',
    'workflow.after_member_processing', 'workflow.after_member_receipt',
    'workflow.after_report_object', 'workflow.after_attempt_finish')


def process_case(output, point):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    pack = simple_pack(output / 'pack')
    settings = fixture_settings(backfill={'start_quarter': '2026Q4', 'end_quarter': 'open'},
        etl={'parser_version': 'fixture-index-parser-v1'},
        fixture={'allow_clock_override': True, 'allow_deadline_override': False})
    h = CommandHarness(output, pack, settings)
    argv = ['backfill', '--config', str(h.config), '--run-id', 'process', '--execution-id', 'manual',
            '--attempt-id', 'a', '--deadline', h.deadline.isoformat(), '--state-dir', str(output),
            '--fixture-pack', str(pack), '--today', '2026-10-07']
    h.close()
    marker = output / 'death.json'
    child = multiprocessing.get_context('spawn').Process(target=process_worker,
        args=(h.config, pack, output, argv, point, marker))
    child.start()
    child.join(30)
    if child.is_alive():
        child.terminate(); child.join(5)
        raise AssertionError('worker did not reach durable boundary ' + point)
    if child.exitcode != 91 or not marker.is_file() or json.loads(marker.read_text())['point'] != point:
        raise AssertionError({'point': point, 'exit': child.exitcode})
    opened = open_stores(settings, base_path=output)
    store, objects, leases = opened
    try:
        before = [row.to_mapping() for row in store.scan('QuarterPublication', {})]
        result_ref = 'runs/sec/process/backfill/a/result.json'
        try: saved_body = objects.read(result_ref)
        except FileNotFoundError: saved_body = None
        if point == 'workflow.after_attempt_begin':
            begun = tuple(store.scan('WorkflowAttempt', {}))
            if len(begun) != 1 or begun[0].value['result_ref'] is not None:
                raise AssertionError('durable workflow start was not retained before intent write')
            try: objects.read('runs/sec/process/backfill/a/intent.json')
            except FileNotFoundError: pass
            else: raise AssertionError('before-intent interruption unexpectedly has intent bytes')
        if point in ('workflow.after_report_object', 'workflow.after_attempt_finish') and saved_body is None:
            raise AssertionError('report boundary has no immutable report')
        if point == 'publication.after_pointer':
            if len(before) != 1 or saved_body is not None:
                raise AssertionError('post-CAS setup lacks unfinished publication')
            publish_attempts = [row.to_mapping()['value'] for row in store.scan('Attempt', {})
                                if row.value['context']['command'] == 'publish']
            if len(publish_attempts) != 1 or publish_attempts[0]['result'] is not None:
                raise AssertionError('process death must retain begun publish without a result')
    finally:
        for resource in reversed(opened):
            if hasattr(resource, 'close'): resource.close()
    h = CommandHarness(output, pack, settings)
    h.deadline = datetime.fromisoformat(argv[argv.index('--deadline') + 1])
    try:
        code, message = h.invoke('backfill', run='process', attempt='a')
        if code != 0: raise AssertionError(h.calls[-1])
        result = durable_report(h, message)
        capture, rows = h.capture('2026Q4')
        if result.counts['complete_sources'] != 1 or result.counts['pending_sources'] or len(rows) != 1:
            raise AssertionError(result.to_mapping())
        after = [row.to_mapping() for row in h.store.scan('QuarterPublication', {})]
        if before and after != before:
            raise AssertionError('recovery advanced an already committed pointer')
        if saved_body is not None and h.objects.read(result_ref) != saved_body:
            raise AssertionError('completed historical report was rewritten during recovery')
        put_json(output / 'reopened.json', {'calls': h.calls, 'report': result.to_mapping(),
            'reader': capture.to_mapping(), 'rows': rows, 'pointers_before': before, 'pointers_after': after})
        return {'point': point, 'exit': 0, 'worker_exit': child.exitcode, 'report': message['result_ref']}
    finally:
        h.close()


def native(output):
    output = Path(output)
    sequence_output = output / 'sequence'
    sequence_output.mkdir(exist_ok=False)
    result = sequence(sequence_output)
    recovered = [process_case(output / ('process-' + point.replace('.', '-')), point) for point in PROCESS_POINTS]
    put_json(output / 'process-recovery.json', recovered)
    return {'exit': 0, 'sequence': result, 'process_recovery': recovered,
            'all22_stage7_checks': 'reserved/not_run'}
```

Add `test_workflow_process.py`:

```python
from network_guard import install
install()
import tempfile, unittest
from pathlib import Path
from workflow_proof import PROCESS_POINTS, process_case, sequence, harness_files

class WorkflowProcessTests(unittest.TestCase):
    def test_public_native_sequence_uses_explicit_test_only_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = sequence(Path(tmp))
            self.assertEqual(report['exit'], 0)
            self.assertEqual(set(report['reports']),
                {'proof-baseline', 'proof-overlap', 'proof-repeat', 'legacy-workflow'})
            self.assertTrue(all(path.is_relative_to(Path(__file__).resolve().parent) for path in harness_files()))

    def test_real_process_death_reopens_each_durable_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            for point in PROCESS_POINTS:
                with self.subTest(point=point):
                    result = process_case(Path(tmp) / point.replace('.', '-'), point)
                    self.assertEqual(result['worker_exit'], 91)
                    self.assertEqual(result['exit'], 0)
```

The acceptance support below is a deterministic fixture constructor. It emits successful root/year/quarter listings for the specified quarters, parser-valid nonempty source bodies, and optional leaf failures. It never supplies report/completion objects. Overrides are body-hash bound responses in the real fixture pack, and every normal response has 16 explicit cursor entries. Add these helpers to `support_workflows.py` before the following test imports.

```python
from sec_edgar_ingest.models import to_mapping_value
def quarter_pack(root, periods, *, empty_daily=False, failed_daily=(), moved=None, conflicting=()):
    periods = tuple(sorted(set(periods)))
    listings, bodies = {}, {}
    for family in ('full-index', 'daily-index'):
        base = BASE + family + '/'
        years = sorted({period[:4] for period in periods})
        listings[base + 'index.json'] = [(year, 'dir') for year in years]
        for year in years:
            listings[base + year + '/index.json'] = [
                ('QTR' + period[-1], 'dir') for period in periods if period.startswith(year)]
        for period in periods:
            year, quarter = period.split('Q')
            leaf = base + year + '/QTR' + quarter + '/'
            month = (int(quarter) - 1) * 3 + 1
            day = year + f'-{month:02d}-01'
            # Q4 must remain inside the overlap following a seed boundary of October 2.
            if period == '2026Q4': day = '2026-12-31'
            filename = 'master.zip' if family == 'full-index' else 'master.' + day.replace('-', '') + '.idx'
            listings[leaf + 'index.json'] = [] if family == 'daily-index' and empty_daily else [(filename, 'file')]
            filed = (moved or {}).get(period, day) if family == 'full-index' else day.replace('-', '')
            archive = 'edgar/data/123456/0000123456-' + year[-2:] + '-00000' + quarter + '.txt'
            row = ('123456', 'Example', '10-K', filed, archive)
            rows = (row, ('123456', 'Conflict', '10-K', filed, archive)) if period in conflicting else (row,)
            bodies[leaf + filename] = idx(rows, 'quarterly' if family == 'full-index' else 'daily')
    pack = build_pack(root, listings, bodies, repeats=16)
    if failed_daily:
        manifest = json.loads(pack.read_text())
        failure = b'fixture missing required directory'
        digest = hashlib.sha256(failure).hexdigest()
        (pack.parent / 'bodies' / (digest + '.body')).write_bytes(failure)
        for period in failed_daily:
            year, quarter = period.split('Q')
            url = BASE + 'daily-index/' + year + '/QTR' + quarter + '/index.json'
            response = {'status': 404, 'headers': {'Content-Length': str(len(failure))},
                        'body_path': 'bodies/' + digest + '.body', 'body_sha256': digest}
            manifest['responses'][url] = [dict(response) for _ in range(16)]
        pack.write_bytes(canonical_json(to_mapping_value(manifest)))
    return pack


def set_harness_settings(harness, settings):
    harness.settings = settings
    harness.config.write_bytes(canonical_json(to_mapping_value(settings.to_mapping())))


def prefix_response(pack, url, body=b'retained truncated retry prefix'):
    pack = Path(pack)
    manifest = json.loads(pack.read_text())
    digest = hashlib.sha256(body).hexdigest()
    (pack.parent / 'bodies' / (digest + '.body')).write_bytes(body)
    manifest['responses'][url].insert(0, {'status': 200,
        'headers': {'X-Fixture': 'partial'}, 'fault': 'read_timeout',
        'body_path': 'bodies/' + digest + '.body', 'body_sha256': digest})
    pack.write_bytes(canonical_json(to_mapping_value(manifest)))
    return body


def replace_pack_body(pack, url, body):
    pack = Path(pack)
    manifest = json.loads(pack.read_text())
    digest = hashlib.sha256(body).hexdigest()
    target = pack.parent / 'bodies' / (digest + '.body')
    if not target.exists(): target.write_bytes(body)
    response = {'status': 200, 'headers': {'Content-Length': str(len(body)), 'X-Fixture': 'synthetic'},
                'body_path': 'bodies/' + digest + '.body', 'body_sha256': digest}
    manifest['responses'][url] = [dict(response) for _ in range(16)]
    pack.write_bytes(canonical_json(to_mapping_value(manifest)))
```

Add `test_workflow_acceptance.py` with these actual regression setups. F6's complete installed inventory and live transitive mismatch are T11; these tests deliberately do not reduce it to the five direct pins.

```python
from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import hashlib, json, tempfile, unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from support import fixture_settings
from support_workflows import (BASE, CommandHarness, simple_pack, quarter_pack,
    set_harness_settings, prefix_response, replace_pack_body, idx)
from sec_edgar_ingest.models import RunContext, parse_json
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.workflows.results import read_workflow_result
from sec_edgar_ingest.workflows.completion import evaluate_member


class WorkflowAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def harness(self, pack, start='2026Q3', end='open'):
        settings = fixture_settings(backfill={'start_quarter': start, 'end_quarter': end},
            daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
            http={'retry_base_seconds': 0.001, 'retry_cap_seconds': 0.001},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        h = CommandHarness(self.root, pack, settings)
        self.addCleanup(h.close)
        return h

    def report(self, h, message):
        return read_workflow_result(message['result_ref'], h.store, h.objects)

    def test_F2_retry_prefix_survives_without_terminal_source_quarantine(self):
        pack = simple_pack(self.root / 'pack')
        prefix = prefix_response(pack, BASE + 'daily-index/2026/QTR4/master.20261001.idx')
        h = self.harness(pack)
        code, message = h.invoke('daily')
        self.assertEqual(code, 0, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.counts['complete_sources'], 1)
        self.assertEqual(report.counts['quarantined_sources'], 0)
        self.assertEqual(report.counts['failed_sources'], 0)
        calls = report.to_mapping()['intent']['child_calls']
        collect = next(call for call in calls if call['context']['command'] == 'collect')
        source = report.members[0].source
        history = AcquisitionState(h.store).request_history(RunContext.from_mapping(collect['context']), source.canonical_url)
        self.assertEqual(len(history), 2)
        first = history[0].value
        base = f'quarantine/sec/{report.context.run_id}/{source.source_id}/{collect["context"]["attempt_id"]}/{first["request_id"]}'
        self.assertEqual(h.objects.read(base + '/body'), prefix)
        self.assertEqual(parse_json(h.objects.read(base + '/receipt.json'))['error']['code'], 'read_timeout')
        self.assertEqual(len(h.capture('2026Q4')[1]), 1)

    def test_F4_parent_command_namespace_and_exact_completed_replay(self):
        h = self.harness(simple_pack(self.root / 'pack'))
        outputs = []
        for command in ('backfill', 'daily'):
            code, message = h.invoke(command, run='same', attempt='same')
            self.assertEqual(code, 0, h.calls[-1])
            outputs.append(message)
        reports = [self.report(h, value) for value in outputs]
        discovery = [next(call for call in result.to_mapping()['intent']['child_calls']
                          if call['context']['command'] == 'discover') for result in reports]
        self.assertNotEqual(discovery[0]['context']['attempt_id'], discovery[1]['context']['attempt_id'])
        self.assertEqual({call['workflow_command'] for call in discovery}, {'backfill', 'daily'})
        cursors = tuple(row.to_mapping() for row in h.store.scan('FixtureResponseCursor', {}))
        for command, expected in zip(('backfill', 'daily'), outputs):
            self.assertEqual(h.invoke(command, run='same', attempt='same'), (0, expected))
        self.assertEqual(tuple(row.to_mapping() for row in h.store.scan('FixtureResponseCursor', {})), cursors)

    def test_F5_all_conflicting_baseline_is_quarantined_with_gaps_and_no_pointer(self):
        h = self.harness(simple_pack(self.root / 'pack', conflicting=True))
        code, message = h.invoke('backfill')
        self.assertEqual(code, 7, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.outcome, 'quarantined')
        self.assertEqual(report.counts['complete_sources'], 0)
        self.assertEqual(report.counts['failed_sources'], 2)
        self.assertEqual(report.counts['quarantined_sources'], 2)
        self.assertEqual(tuple(h.store.scan('Processing', {})), ())
        self.assertEqual(tuple(h.store.scan('QuarterPublication', {})), ())
        baseline = [gap for gap in report.gaps if gap.code == 'baseline_publication_missing']
        self.assertEqual({gap.details['quarter'] for gap in baseline}, {'2026Q3', '2026Q4'})
        self.assertTrue(all(gap.details['coverage_cause'] == 'selected_source_quarantine' for gap in baseline))
        self.assertTrue(all(member.quarantined and member.gaps for member in report.members))

    def test_R1_empty_quarter_is_unresolved_and_preserves_valid_quarter(self):
        pack = simple_pack(self.root / 'pack')
        manifest = json.loads(pack.read_text())
        from support_workflows import listing
        from sec_edgar_ingest.models import canonical_json
        url = BASE + 'full-index/2026/QTR3/index.json'
        body = listing(url, [])
        digest = hashlib.sha256(body).hexdigest()
        (pack.parent / 'bodies' / (digest + '.body')).write_bytes(body)
        response = {'status': 200, 'headers': {'Content-Length': str(len(body))},
                    'body_path': 'bodies/' + digest + '.body', 'body_sha256': digest}
        manifest['responses'][url] = [dict(response) for _ in range(16)]
        pack.write_bytes(canonical_json(to_mapping_value(manifest)))
        h = self.harness(pack)
        code, message = h.invoke('backfill')
        self.assertEqual(code, 3)
        report = self.report(h, message)
        self.assertEqual(report.counts['complete_sources'], 1)
        self.assertIsNone(EtlState(h.store).pointer('2026Q3'))
        self.assertEqual(len(h.capture('2026Q4')[1]), 1)
        self.assertTrue(any(gap.details.get('quarter') == '2026Q3' for gap in report.gaps))

    def test_R1_mixed_valid_and_refused_members_preserves_good_pointer(self):
        h = self.harness(quarter_pack(self.root / 'pack', ('2026Q3', '2026Q4'),
                                      conflicting=('2026Q3',)))
        code, message = h.invoke('backfill')
        self.assertEqual(code, 3, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.counts['complete_sources'], 1)
        self.assertEqual(report.counts['failed_sources'], 1)
        self.assertEqual(report.counts['quarantined_sources'], 1)
        self.assertIsNone(EtlState(h.store).pointer('2026Q3'))
        self.assertEqual(len(h.capture('2026Q4')[1]), 1)
        self.assertEqual(len(tuple(h.store.scan('Processing', {}))), 1)

    def test_R2_older_nonempty_closed_withdrawal_gate_remains_pending(self):
        periods = ('2026Q3', '2026Q4')
        pack = quarter_pack(self.root / 'initial', periods, empty_daily=True)
        url = BASE + 'full-index/2026/QTR3/master.zip'
        a = ('123456', 'A', '10-K', '2026-07-01', 'edgar/data/123456/0000123456-26-000031.txt')
        b = ('123456', 'B', '10-K', '2026-07-02', 'edgar/data/123456/0000123456-26-000032.txt')
        replace_pack_body(pack, url, idx((a, b), 'quarterly'))
        h = self.harness(pack, end='2026Q3')
        self.assertEqual(h.invoke('backfill', run='closed-baseline')[0], 0)
        before = EtlState(h.store).pointer('2026Q3').to_mapping()
        revision = quarter_pack(self.root / 'revision', periods, empty_daily=True)
        replace_pack_body(revision, url, idx((a,), 'quarterly'))
        h.pack = revision
        code, found = h.invoke('discover', ('--mode', 'quarterly', '--discovery-id', 'gate-refresh', '--refresh'), run='gate-find')
        self.assertEqual(code, 0)
        code, collected = h.invoke('collect', ('--workset', found['source_workset_ref']), run='gate-collect')
        self.assertEqual(code, 0)
        code, transformed = h.invoke('transform', ('--workset', collected['snapshot_workset_ref']), run='gate-transform')
        self.assertEqual(code, 0)
        code, published = h.invoke('publish', ('--workset', transformed['transformed_workset_ref']), run='gate-publish')
        self.assertEqual(code, 10, h.calls[-1])
        self.assertEqual(EtlState(h.store).pointer('2026Q3').to_mapping(), before)
        current = fixture_settings(backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
            daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        set_harness_settings(h, current)
        code, message = h.invoke('daily', run='gate-backlog')
        self.assertEqual(code, 10, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.outcome, 'awaiting_approval')
        self.assertEqual(report.counts['pending_sources'], 1)
        self.assertEqual(report.counts['complete_sources'], 0)
        self.assertGreaterEqual(report.counts['awaiting_approval_quarters'], 1)
        self.assertEqual(EtlState(h.store).pointer('2026Q3').to_mapping(), before)
        self.assertEqual(len(h.capture('2026Q3')[1]), 2)

    def seed_older_unacquired(self, h):
        # Only actual shipped primitive discovery: no WorkflowMember or completion is fabricated.
        prior = fixture_settings(backfill={'start_quarter': '2025Q2', 'end_quarter': '2025Q2'},
            daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
            fixture={'allow_clock_override': True, 'allow_deadline_override': False})
        current = h.settings
        set_harness_settings(h, prior)
        code, result = h.invoke('discover', ('--mode', 'quarterly', '--discovery-id', 'older-unacquired'), run='older')
        self.assertEqual(code, 0)
        self.assertEqual(tuple(h.store.scan('WorkflowMember', {})), ())
        set_harness_settings(h, current)
        return result['source_workset_ref']

    def test_R2_outage_spans_Q4_Q1_Q2_and_keeps_older_pending(self):
        periods = ('2025Q2', '2026Q3', '2026Q4', '2027Q1', '2027Q2')
        handoff_pack = quarter_pack(self.root / 'handoff-pack', periods, empty_daily=True)
        h = self.harness(handoff_pack, start='2025Q2')
        code, _ = h.invoke('daily', run='handoff', today='2026-10-02')
        self.assertEqual(code, 0, h.calls[-1])
        self.assertEqual(AcquisitionState(h.store).daily_boundary(), date(2026, 10, 2))
        self.assertEqual(tuple(h.store.scan('WorkflowMember', {})), ())
        older_ref = self.seed_older_unacquired(h)
        h.pack = quarter_pack(self.root / 'outage-pack', periods)
        code, message = h.invoke('daily', run='outage', today='2027-04-01')
        self.assertEqual(code, 0, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.boundary_before, '2026-10-02')
        self.assertEqual(report.boundary_after, '2027-04-01')
        self.assertEqual(report.intent['unresolved_before'], 1)
        self.assertTrue(any(member.parent_ref == older_ref for member in report.members))
        periods_seen = {directory['period'] for directory in report.to_mapping()['directories']}
        self.assertTrue({'2025Q2', '2026Q4', '2027Q1', '2027Q2'} <= periods_seen)
        for quarter in ('2025Q2', '2026Q4', '2027Q1', '2027Q2'):
            self.assertEqual(len(h.capture(quarter)[1]), 1)

    def test_R2_failed_outage_directory_holds_boundary_with_independent_progress(self):
        periods = ('2025Q2', '2026Q3', '2026Q4', '2027Q1', '2027Q2')
        handoff_pack = quarter_pack(self.root / 'handoff-pack', periods, empty_daily=True)
        h = self.harness(handoff_pack, start='2025Q2')
        self.assertEqual(h.invoke('daily', run='handoff', today='2026-10-02')[0], 0)
        self.assertEqual(tuple(h.store.scan('WorkflowMember', {})), ())
        self.seed_older_unacquired(h)
        h.pack = quarter_pack(self.root / 'failed-outage-pack', periods, failed_daily=('2027Q1',))
        code, message = h.invoke('daily', run='outage-failed', today='2027-04-01')
        self.assertEqual(code, 3, h.calls[-1])
        report = self.report(h, message)
        self.assertEqual(report.boundary_before, '2026-10-02')
        self.assertEqual(report.boundary_after, '2026-10-02')
        failed = [directory for directory in report.to_mapping()['directories'] if directory['outcome'] == 'discovery_failed']
        self.assertEqual({directory['period'] for directory in failed}, {'2027Q1'})
        self.assertGreaterEqual(report.counts['complete_sources'], 1)
        self.assertEqual(len(h.capture('2025Q2')[1]), 1)
        self.assertEqual(len(h.capture('2027Q2')[1]), 1)
        self.assertIsNone(EtlState(h.store).pointer('2027Q1'))

    def test_R2_Q4_Q1_transition_uses_both_required_quarters(self):
        h = self.harness(quarter_pack(self.root / 'pack', ('2026Q3', '2026Q4', '2027Q1')))
        self.assertEqual(h.invoke('daily', run='q4', today='2026-12-31')[0], 0)
        code, message = h.invoke('daily', run='q1', today='2027-01-02')
        self.assertEqual(code, 0, h.calls[-1])
        report = self.report(h, message)
        periods = {directory['period'] for directory in report.to_mapping()['directories']}
        self.assertTrue({'2026Q4', '2027Q1'} <= periods)
        self.assertEqual(len(h.capture('2026Q4')[1]), 1)
        self.assertEqual(len(h.capture('2027Q1')[1]), 1)

    def test_F1_moved_quarter_remains_backlog_after_Q4_publishes(self):
        h = self.harness(simple_pack(self.root / 'initial'))
        self.assertEqual(h.invoke('backfill', run='initial')[0], 0)
        before = EtlState(h.store).pointer('2026Q3').to_mapping()
        h.pack = quarter_pack(self.root / 'revision', ('2026Q3', '2026Q4'),
                              moved={'2026Q3': '2026-10-01'}, empty_daily=True)
        code, found = h.invoke('discover', ('--mode', 'quarterly', '--discovery-id', 'revision', '--refresh'), run='revision-find')
        self.assertEqual(code, 0)
        code, collected = h.invoke('collect', ('--workset', found['source_workset_ref']), run='revision-collect')
        self.assertEqual(code, 0)
        code, transformed = h.invoke('transform', ('--workset', collected['snapshot_workset_ref']), run='revision-transform')
        self.assertEqual(code, 0)
        code, published = h.invoke('publish', ('--workset', transformed['transformed_workset_ref']), run='revision-publish')
        self.assertEqual(code, 7, h.calls[-1])
        from sec_edgar_ingest.etl.commands import read_etl_result
        result = read_etl_result(published['result_ref'], h.objects)
        quarters = {quarter.quarter: quarter.outcome for quarter in result.quarters}
        self.assertEqual(quarters, {'2026Q3': 'invalid_source', '2026Q4': 'published'})
        self.assertEqual(EtlState(h.store).pointer('2026Q3').to_mapping(), before)
        code, daily = h.invoke('daily', run='backlog')
        report = self.report(h, daily)
        self.assertNotEqual(report.outcome, 'no_new_sources')
        values = [row.to_mapping()['value'] for row in h.store.scan('WorkflowMember', {})
                  if row.value['parent_ref'] == found['source_workset_ref']]
        self.assertTrue(values)
        self.assertTrue(any(not evaluate_member(value, report.context.parser_version,
            report.context.schema_version, h.store, h.objects).complete for value in values))

    def test_F3_ordinary_post_CAS_failure_has_no_report_then_fresh_checked_repair(self):
        h = self.harness(simple_pack(self.root / 'pack'), start='2026Q4')
        import sec_edgar_ingest.cli as cli
        from sec_edgar_ingest.etl.commands import run_publish
        fired = []
        def boundary(point):
            if point == 'publication.after_pointer' and not fired:
                fired.append(True)
                raise OSError('ordinary retained post-CAS failure')
        def publish(*args, **kwargs): return run_publish(*args, observer=boundary, **kwargs)
        with patch.object(cli, 'run_publish', side_effect=publish):
            code, message = h.invoke('backfill', run='repair', attempt='original')
        self.assertEqual(code, 9, h.calls[-1])
        self.assertIsNone(message['result_ref'])
        self.assertEqual(fired, [True])
        pointers = [row.to_mapping() for row in h.store.scan('QuarterPublication', {})]
        self.assertEqual(len(pointers), 1)
        attempts = [row.to_mapping() for row in h.store.scan('Attempt', {}) if row.value['context']['command'] == 'publish']
        self.assertEqual(len(attempts), 1)
        self.assertIsNone(attempts[0]['value']['result'])
        self.assertEqual(attempts[0]['value']['structured_errors'][0]['details']['type'], 'PublicationRepairPending')
        with self.assertRaises(FileNotFoundError):
            h.objects.read('runs/sec/repair/backfill/original/result.json')
        h.pack = simple_pack(self.root / 'empty-after-repair', empty=True)
        code, message = h.invoke('daily', run='repair', attempt='fresh')
        self.assertEqual(code, 0, h.calls[-1])
        report = self.report(h, message)
        self.assertNotEqual(report.outcome, 'no_new_sources')
        self.assertTrue(report.intent['repair_resolutions'])
        self.assertEqual([row.to_mapping() for row in h.store.scan('QuarterPublication', {})], pointers)
        old = next(row.to_mapping() for row in h.store.scan('Attempt', {})
                   if row.value['context']['attempt_id'] == attempts[0]['value']['context']['attempt_id'])
        self.assertEqual(old, attempts[0])
```

- [ ] Generate fixed reviewed fixture bytes with `uv run --offline --frozen --package sec-edgar-ingest python -c 'import sys; sys.path.insert(0,"packages/sec-edgar-ingest/tests"); from workflow_proof import write_proof_fixtures,FIXTURE_ROOT; write_proof_fixtures(FIXTURE_ROOT)'`. The destination is create-only. Do not overwrite a retained fixture generation silently; inspect any existing directory and reconcile bytes before adopting it.
- [ ] Run guarded `test_workflow_acceptance.py` and `test_workflow_process.py`, retaining actual red/green outputs. F1/F2/F3/F4/F5 and R1/R2 assertions read production authority, preserve independent progress and require exact successful recovery. Run existing Stage 3 parser/ETL/reader regression files; the full suite in T11 must still enforce the exact SEC-0141/0142/0143 21/24/6 whole-source refusals.
- [ ] Review the fixture and process evidence with the owner before treating these as accepted offline coverage. Commit owned files with `test: prove workflow CLI and process recovery offline`; perform the task-scoped review. Native proof never marks Stage 7 checks run or adds live scope.

The fresh proof command after T11 supplies the script main is `uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/workflow_proof.py native --output /absolute/create-only/stage4-native-proof`. Installed mode is defined completely in T11 and requires the explicit reviewed wheel/source paths; use no editable import or glob-selected stale wheel.



**Exact task commands and review checkpoint:** Run the scoped command before the proposed implementation to retain actual red output, then rerun it unchanged for green. Expected red is the missing/new behavior identified above; expected green is exit 0 with all methods PASS. Missing cache is a blocker, never a substitute red result. Retain each listed regression command using the same guarded runner and exact test filename.

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_acceptance.py -v
git -c core.whitespace=cr-at-eol diff --check
git add packages/sec-edgar-ingest/tests/workflow_proof.py packages/sec-edgar-ingest/tests/test_workflow_acceptance.py packages/sec-edgar-ingest/tests/test_workflow_process.py packages/sec-edgar-ingest/tests/support_workflows.py packages/sec-edgar-ingest/tests/fixtures/workflows/proof
git commit -m "test: prove workflow CLI and process recovery offline"
```

Fresh task review must resolve spec compliance and code quality findings before the next dependent task. Record actual reviewer identity, scoped diff, test output and any changes; no task is accepted by this document.
### Task 11: Complete frozen-lock isolated installed proof

**Files:**
- Create: `packages/sec-edgar-ingest/tests/locked_proof.py`.
- Create: `packages/sec-edgar-ingest/tests/test_workflow_installed_lock.py`.
- Modify: `packages/sec-edgar-ingest/tests/workflow_proof.py` by adding `installed`, replacing its main with the complete command parser below, and adding `locked_proof.py` to its fixed harness file list.
- Reuse the accepted `uv.lock`, all existing pins, retained Stage 2 cached wheel directory and PyArrow offline cache. No dependency additions.

**Consumes:** Task 10 `workflow_proof.sequence(output: Path) -> Mapping[str, object]`, `workflow_proof.harness_files() -> tuple[Path, ...]`, and its `native(output: Path) -> Mapping[str, object]`. `sequence` executes fresh real backfill/daily/legacy/reader acceptance in the output directory and returns its assertions/evidence summary; it imports actual production modules from the interpreter, never a source-tree substitute. `harness_files` returns the complete fixed set of test-only modules, config, fixture manifests/expected JSON/bodies; each is beneath `packages/sec-edgar-ingest/tests`.

**Produces:**
- `locked_proof.marker_environment() -> dict[str, str]`.
- `locked_proof.locked_requirements(lock_body: bytes, export_text: str, environment: Mapping[str, str]) -> dict[str, str]`: validates the complete applicable dependency graph, exported versions/markers/hashes, and returns every resolved active dependency. No direct-pin shortcut.
- `locked_proof.installed_inventory() -> dict[str, str]`; `locked_proof.assert_inventory(expected: Mapping[str, str], actual: Mapping[str, str], distribution_version: str) -> None`: exact name/version set equals applicable graph plus the reviewed distribution.
- `locked_proof.digest(path: Path) -> dict[str, object]`; `locked_proof.inventory(root: Path) -> dict[str, dict[str, object]]`; `locked_proof.verify_inventory(root: Path) -> None`: inventory includes every retained file except its own `sha256.json`; exact membership is verified before reporting success.
- `workflow_proof.installed(output: Path, wheel: Path, reviewed_source: Path) -> Mapping[str, object]`.
- Script API: `workflow_proof.py native|installed --output ABS [--wheel ABS --reviewed-source ABS]`. Installed requires both explicit absolute paths. The reviewed source path is the `packages/sec-edgar-ingest/src` directory from the reviewed execution checkout.

The accepted lock currently uses only equality/inequality string markers and `and`/`or`; the supplied strict evaluator implements those actual accepted marker expressions and refuses any unknown syntax instead of treating a marker as true. It evaluates environment names using the isolated interpreter. In the current lock, `cffi` and `pycparser` are conditional on PyPy markers. Test a synthetic PyPy environment to prove inactive entries are excluded while every other applicable transitive dependency remains required.

- [ ] **Step 1: Write the complete-lock refusal tests.**

Create `tests/test_workflow_installed_lock.py`:

```python
from network_guard import install
install()

from sec_edgar_ingest.models import to_mapping_value
import tempfile
import unittest
from pathlib import Path

from locked_proof import (
    assert_inventory, locked_requirements, marker_environment, inventory, verify_inventory,
    package_inventory,
)
from sec_edgar_ingest.models import canonical_json


def small_lock_and_export():
    first, second = 'a' * 64, 'b' * 64
    lock = f'''version = 1
[[package]]
name = "sec-edgar-ingest"
version = "0.1.0"
source = {{ editable = "packages/sec-edgar-ingest" }}
dependencies = [{{name="requests"}}, {{name="pycparser", marker="implementation_name != 'PyPy'"}}]
[[package]]
name = "requests"
version = "2.34.2"
source = {{registry="https://pypi.org/simple"}}
wheels = [{{hash="sha256:{first}"}}]
[[package]]
name = "pycparser"
version = "3.0"
source = {{registry="https://pypi.org/simple"}}
wheels = [{{hash="sha256:{second}"}}]
'''.encode()
    export = (f'requests==2.34.2 --hash=sha256:{first}\n'
              f"pycparser==3.0 ; implementation_name != 'PyPy' --hash=sha256:{second}\n")
    return lock, export


class InstalledLockTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[3]
        self.lock = (self.repo / 'uv.lock').read_bytes()
        self.export = (self.repo / 'specs/evidence/sec-filing-index-ingestion/stage-3/'
                       'verification/installed/requirements.txt').read_text()
        self.environment = marker_environment()

    def test_complete_accepted_graph_rejects_wrong_transitive_with_direct_pins_intact(self):
        expected = locked_requirements(self.lock, self.export, self.environment)
        self.assertEqual(len(expected), 19 if self.environment['platform_python_implementation'] == 'PyPy' else 21)
        actual = dict(expected, **{'sec-edgar-ingest': '0.1.0'})
        actual['urllib3'] = '2.7.0'
        for direct in ('pyarrow', 'requests', 'azure-identity', 'azure-storage-blob', 'azure-data-tables'):
            self.assertEqual(actual[direct], expected[direct])
        with self.assertRaisesRegex(ValueError, 'installed dependency set'):
            assert_inventory(expected, actual, '0.1.0')

    def test_exact_set_rejects_missing_and_extra_distribution(self):
        expected = locked_requirements(self.lock, self.export, self.environment)
        for actual in (dict(expected), dict(expected, **{'sec-edgar-ingest': '0.1.0', 'unrequested': '1.0'})):
            with self.assertRaisesRegex(ValueError, 'installed dependency set'):
                assert_inventory(expected, actual, '0.1.0')
        self.assertIsNone(assert_inventory(expected, dict(expected, **{'sec-edgar-ingest': '0.1.0'}), '0.1.0'))

    def test_marker_exclusion_does_not_drop_other_transitives(self):
        lock, export = small_lock_and_export()
        cpython = dict(self.environment, implementation_name='cpython', platform_python_implementation='CPython')
        pypy = dict(self.environment, implementation_name='PyPy', platform_python_implementation='PyPy')
        self.assertEqual(locked_requirements(lock, export, cpython), {'requests': '2.34.2', 'pycparser': '3.0'})
        self.assertEqual(locked_requirements(lock, export, pypy), {'requests': '2.34.2'})

    def test_frozen_export_hash_or_transitive_omission_refuses(self):
        lock, export = small_lock_and_export()
        for altered in (export.replace('a' * 64, 'c' * 64),
                        export.splitlines()[0] + '\n',
                        export.replace("implementation_name != 'PyPy'", "unknown_name == 'anything'")):
            with self.assertRaises(ValueError):
                locked_requirements(lock, altered, self.environment)

    def test_inventory_checks_exact_files_and_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'proof.json').write_bytes(b'{}')
            (root / 'sha256.json').write_bytes(canonical_json(to_mapping_value(inventory(root))))
            verify_inventory(root)
            (root / 'extra.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'inventory membership'):
                verify_inventory(root)
            (root / 'extra.json').unlink()
            (root / 'proof.json').write_bytes(b'{"altered":true}')
            with self.assertRaisesRegex(ValueError, 'inventory bytes'):
                verify_inventory(root)

    def test_package_inventory_includes_py_typed_and_all_data_and_excludes_caches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'sec_edgar_ingest'
            package.mkdir()
            (package / '__init__.py').write_bytes(b'__version__="0.1.0"\n')
            (package / 'py.typed').write_bytes(b'')
            (package / 'schema.bin').write_bytes(b'production retained data')
            cache = package / '__pycache__'
            cache.mkdir()
            (cache / 'module.pyc').write_bytes(b'cache is not source')
            before = package_inventory(root)
            self.assertEqual(set(before), {'sec_edgar_ingest/__init__.py',
                'sec_edgar_ingest/py.typed', 'sec_edgar_ingest/schema.bin'})
            self.assertEqual(before['sec_edgar_ingest/py.typed']['bytes'], 0)
            (package / 'py.typed').write_bytes(b'changed marker')
            after = package_inventory(root)
            self.assertEqual(set(after), set(before))
            self.assertNotEqual(after, before)
            (package / 'schema.bin').unlink()
            self.assertNotEqual(set(package_inventory(root)), set(before))
```

- [ ] **Step 2: Run the targeted red command.**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_installed_lock.py -v
```

Expected initially: `locked_proof` import failure. The historical retained requirements file is read-only test input for accepted lock topology; it is not presented as fresh installed proof. Final installation always exports the actual accepted lock afresh.

- [ ] **Step 3: Implement the pure lock/export/inventory verifier.**

Create `tests/locked_proof.py`:

```python
from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import platform
import re
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path


def normalized(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
        raise ValueError('invalid distribution name')
    return re.sub(r'[-_.]+', '-', name).lower()


def marker_environment():
    return {'implementation_name': sys.implementation.name,
            'platform_python_implementation': platform.python_implementation()}


def _marker(expression, environment):
    if not expression:
        return True
    tree = ast.parse(expression, mode='eval')

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Name):
            if node.id not in environment:
                raise ValueError('unknown accepted-lock marker environment name')
            return environment[node.id]
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            values = [evaluate(value) for value in node.values]
            if any(type(value) is not bool for value in values):
                raise ValueError('marker boolean operands must be comparisons')
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
            left, right = evaluate(node.left), evaluate(node.comparators[0])
            if not isinstance(left, str) or not isinstance(right, str):
                raise ValueError('accepted-lock marker comparison requires strings')
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        raise ValueError('unsupported expression in the accepted lock marker')

    result = evaluate(tree)
    if type(result) is not bool:
        raise ValueError('lock marker must evaluate to a boolean')
    return result


def requirement_blocks(export_text):
    records, parts, name = [], [], None
    for line in export_text.splitlines(keepends=True):
        match = re.match(r'^([A-Za-z0-9][A-Za-z0-9_.-]*)==', line)
        if match:
            if name is not None:
                records.append((name, ''.join(parts)))
            name, parts = normalized(match.group(1)), [line]
        elif name is not None:
            parts.append(line)
        elif line.strip() and not line.lstrip().startswith('#'):
            raise ValueError('unexpected directive before locked requirements')
    if name is not None:
        records.append((name, ''.join(parts)))
    return records


def locked_requirements(lock_body, export_text, environment):
    lock = tomllib.loads(lock_body.decode('utf-8'))
    packages = {}
    for package in lock['package']:
        name = normalized(package['name'])
        if name in packages:
            raise ValueError('accepted lock contains ambiguous package alternatives')
        packages[name] = package
    if 'sec-edgar-ingest' not in packages:
        raise ValueError('lock lacks the reviewed distribution')
    active, visited, queue = {}, set(), ['sec-edgar-ingest']
    while queue:
        name = queue.pop()
        if name in visited:
            continue
        visited.add(name)
        package = packages[name]
        if name != 'sec-edgar-ingest':
            if 'registry' not in package['source']:
                raise ValueError('offline locked dependencies must retain registry artifact authority')
            active[name] = package['version']
        for dependency in package.get('dependencies', ()):
            if _marker(dependency.get('marker'), environment):
                target = normalized(dependency['name'])
                if target not in packages:
                    raise ValueError('locked dependency target is absent')
                queue.append(target)
    exported = {}
    for name, block in requirement_blocks(export_text):
        logical = ' '.join(line.rstrip().removesuffix('\\').strip()
            for line in block.splitlines() if line.strip() and not line.lstrip().startswith('#'))
        head, *hash_parts = logical.split('--hash=')
        match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s;]+)(?:\s*;\s*(.*))?\s*', head)
        if match is None or normalized(match.group(1)) != name:
            raise ValueError('export entry is not an exact pinned requirement')
        version, marker = match.group(2), match.group(3)
        if name not in packages or version != packages[name]['version']:
            raise ValueError('export version differs from accepted lock')
        hashes = set()
        for value in hash_parts:
            value = value.strip()
            if not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
                raise ValueError('export must retain only exact SHA256 artifact hashes')
            hashes.add(value)
        package = packages[name]
        expected_hashes = {artifact['hash'] for artifact in package.get('wheels', ())}
        if package.get('sdist'):
            expected_hashes.add(package['sdist']['hash'])
        if not hashes or hashes != expected_hashes:
            raise ValueError('export artifact hashes differ from accepted lock')
        if _marker(marker, environment):
            if name in exported:
                raise ValueError('duplicate active export entry')
            exported[name] = version
    if exported != active:
        raise ValueError('export dependency set differs from complete applicable lock graph')
    return dict(sorted(active.items()))


def installed_inventory():
    inventory = {}
    for distribution in importlib.metadata.distributions():
        name = normalized(distribution.metadata['Name'])
        if name in inventory:
            raise ValueError('duplicate installed distribution identity')
        inventory[name] = distribution.version
    return dict(sorted(inventory.items()))


def assert_inventory(expected, actual, distribution_version):
    wanted = {normalized(name): version for name, version in expected.items()}
    wanted['sec-edgar-ingest'] = distribution_version
    installed = {normalized(name): version for name, version in actual.items()}
    if installed != wanted:
        raise ValueError('installed dependency set differs: ' + json.dumps({
            'expected': wanted, 'actual': installed}, sort_keys=True))


def digest(path):
    body = Path(path).read_bytes()
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def inventory(root):
    root = Path(root)
    return {path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob('*')) if path.is_file() and path != root / 'sha256.json'}


def verify_inventory(root):
    root = Path(root)
    saved = json.loads((root / 'sha256.json').read_text())
    actual = inventory(root)
    if set(saved) != set(actual):
        raise ValueError('proof inventory membership differs')
    if saved != actual:
        raise ValueError('proof inventory bytes differ')


def package_inventory(source_root):
    source_root = Path(source_root)
    package = source_root / 'sec_edgar_ingest'
    if not package.is_dir():
        raise ValueError('production package directory is missing')
    return {path.relative_to(source_root).as_posix(): digest(path)
        for path in sorted(package.rglob('*'))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc'}
```

- [ ] **Step 4: Add the full isolated installed driver.**

Add these imports and functions to `tests/workflow_proof.py`; retain Task 10 `sequence`, `native`, and fixed `harness_files` definitions. All helpers used here are supplied; the artifact helpers come from the module defined immediately above.

```python
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
import tomllib
from pathlib import Path

from locked_proof import digest, inventory, requirement_blocks, verify_inventory, package_inventory


def _json_once(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')


def _logged(argv, cwd, output, label, environment, *, timeout=300):
    started = time.monotonic()
    record = {'argv': [str(value) for value in argv], 'cwd': str(cwd),
        'timeout_seconds': timeout, 'pythonpath_present': 'PYTHONPATH' in environment,
        'uv_python_downloads': environment.get('UV_PYTHON_DOWNLOADS')}
    try:
        completed = subprocess.run(argv, cwd=cwd, env=environment, capture_output=True,
                                   text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        record.update(exit=None, outcome='timeout', runtime_seconds=time.monotonic() - started)
        for name, value in (('stdout', error.stdout), ('stderr', error.stderr)):
            if isinstance(value, bytes):
                raw = output / (label + '.' + name + '.bin')
                with raw.open('xb') as stream:
                    stream.write(value)
                record[name + '_raw'] = {'path': raw.name, **digest(raw)}
                record[name] = value.decode('utf-8', errors='backslashreplace')
            else:
                record[name] = value or ''
        _json_once(output / (label + '.json'), record)
        raise
    record.update(exit=completed.returncode, outcome='completed', stdout=completed.stdout,
        stderr=completed.stderr, runtime_seconds=time.monotonic() - started)
    _json_once(output / (label + '.json'), record)
    if completed.returncode:
        raise RuntimeError('offline installed command failed: ' + label)
    return record


def _isolated_script(python, harness, script_name, *arguments):
    script = str(harness / script_name)
    bootstrap = ('import runpy,sys; sys.path.insert(0,' + repr(str(harness)) + '); '
                 'sys.argv=[' + repr(script) + ',*sys.argv[1:]]; '
                 'runpy.run_path(' + repr(script) + ',run_name="__main__")')
    return [str(python), '-I', '-c', bootstrap, *map(str, arguments)]


def installed(output, wheel, reviewed_source):
    tests_root = Path(__file__).resolve().parent
    repo = tests_root.parents[2]
    wheel, reviewed_source = wheel.resolve(), reviewed_source.resolve()
    if not wheel.is_file() or not (reviewed_source / 'sec_edgar_ingest').is_dir():
        raise ValueError('installed proof requires explicit reviewed wheel/source artifacts')
    lock_body = (repo / 'uv.lock').read_bytes()
    expected_sources = package_inventory(reviewed_source)
    with zipfile.ZipFile(wheel) as archive:
        wheel_sources = {name for name in archive.namelist()
                         if name.startswith('sec_edgar_ingest/') and not name.endswith('/')}
        if wheel_sources != set(expected_sources):
            raise ValueError('wheel source inventory differs from reviewed source')
        for name, expected in expected_sources.items():
            body = archive.read(name)
            if {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()} != expected:
                raise ValueError('wheel source bytes differ from reviewed source')
        metadata_files = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
        if len(metadata_files) != 1:
            raise ValueError('wheel must contain one distribution metadata file')
        from email.parser import Parser
        metadata = Parser().parsestr(archive.read(metadata_files[0]).decode('utf-8'))
        if metadata['Name'] != 'sec-edgar-ingest':
            raise ValueError('wheel distribution identity differs')
        distribution_version = metadata['Version']
        locked_distribution = next(package for package in tomllib.loads(lock_body.decode())['package']
                                   if package['name'] == 'sec-edgar-ingest')
        if distribution_version != locked_distribution['version']:
            raise ValueError('reviewed wheel version differs from accepted workspace lock')
    wheel_copy = output / wheel.name
    shutil.copy2(wheel, wheel_copy)
    (output / 'accepted-uv.lock').write_bytes(lock_body)
    _json_once(output / 'reviewed-sources.json', expected_sources)
    environment = {name: value for name, value in os.environ.items() if name != 'PYTHONPATH'}
    environment.update(UV_PYTHON_DOWNLOADS='never', PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(prefix='sec-workflow-installed-') as directory:
        outside = Path(directory)
        venv = outside / 'venv'
        _logged(['uv', 'venv', '--offline', '--python', sys.executable, str(venv)],
                outside, output, 'venv', environment)
        python = venv / 'bin/python'
        exported = _logged(['uv', 'export', '--offline', '--frozen', '--package', 'sec-edgar-ingest',
            '--no-emit-workspace', '--format', 'requirements-txt'], repo, output, 'lock-export', environment)
        requirements = outside / 'requirements.txt'
        requirements.write_text(exported['stdout'])
        shutil.copy2(requirements, output / 'requirements.txt')
        harness = outside / 'harness'
        harness.mkdir()
        files = tuple(harness_files()) + (tests_root / 'locked_proof.py',)
        seen = set()
        for source in files:
            source = Path(source).resolve()
            if not source.is_relative_to(tests_root) or not source.is_file():
                raise ValueError('installed harness must be explicit test-only files')
            relative = source.relative_to(tests_root)
            if relative in seen:
                continue
            seen.add(relative)
            destination = harness / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        shutil.copy2(requirements, harness / 'requirements.txt')
        (harness / 'accepted-uv.lock').write_bytes(lock_body)
        _json_once(harness / 'expected-sources.json', expected_sources)
        _json_once(harness / 'expected-distribution.json', {'version': distribution_version})
        verifier = '''import json, pathlib, sys
from locked_proof import marker_environment, locked_requirements
root=pathlib.Path(__file__).parent
environment=marker_environment()
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(), environment)
print(json.dumps({'environment':environment,'dependencies':expected},sort_keys=True))
'''
        (harness / 'verify_export.py').write_text(verifier)
        lock_report = _logged(_isolated_script(python, harness, 'verify_export.py'), outside,
                             output, 'verify-export', environment)
        expected_lock = json.loads(lock_report['stdout'])
        _json_once(output / 'applicable-lock.json', expected_lock)
        blocks = requirement_blocks(exported['stdout'])
        arrow, others = outside / 'arrow.txt', outside / 'others.txt'
        arrow.write_text(''.join(block for name, block in blocks if name == 'pyarrow'))
        others.write_text(''.join(block for name, block in blocks if name != 'pyarrow'))
        if not arrow.read_text().startswith('pyarrow==25.0.1'):
            raise ValueError('export must preserve accepted PyArrow pin')
        shutil.copy2(arrow, output / 'arrow-requirements.txt')
        shutil.copy2(others, output / 'other-requirements.txt')
        cached_wheels = repo / 'specs/evidence/sec-filing-index-ingestion/stage-2/' \
            'verification/sdd-history/task1-evidence/wheels'
        _logged(['uv', 'pip', 'install', '--offline', '--no-deps', '--require-hashes', '--link-mode', 'copy',
                 '--python', str(python), '-r', str(arrow)], outside, output, 'install-arrow', environment)
        _logged(['uv', 'pip', 'install', '--offline', '--no-index', '--link-mode', 'copy', '--find-links', str(cached_wheels),
                 '--require-hashes', '--python', str(python), '-r', str(others)],
                outside, output, 'install-dependencies', environment)
        _logged(['uv', 'pip', 'install', '--offline', '--no-index', '--no-deps', '--link-mode', 'copy', '--python',
                 str(python), str(wheel_copy)], outside, output, 'install-reviewed-wheel', environment)
        runner = '''from network_guard import install
install()
import json,pathlib,hashlib,sys
from locked_proof import marker_environment,locked_requirements,installed_inventory,assert_inventory,inventory,package_inventory
root=pathlib.Path(__file__).parent
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(), marker_environment())
version=json.loads((root/'expected-distribution.json').read_text())['version']
actual=installed_inventory()
assert_inventory(expected,actual,version)
import sec_edgar_ingest
if sec_edgar_ingest.__version__ != version: raise ValueError('installed module version differs from reviewed distribution')
base=pathlib.Path(sec_edgar_ingest.__file__).resolve().parent.parent
if 'site-packages' not in base.parts: raise ValueError('production import escaped isolated site-packages')
sources=json.loads((root/'expected-sources.json').read_text())
actual_sources=package_inventory(base)
if set(actual_sources)!=set(sources): raise ValueError('installed source inventory differs')
if actual_sources!=sources: raise ValueError('installed source bytes differ')
from workflow_proof import sequence
output=pathlib.Path(sys.argv[1]); output.mkdir(exist_ok=False)
report=sequence(output)
print(json.dumps({'import_root':str(base),'dependencies':actual,
    'applicable_lock':expected,'source_equality':sources,'sequence':report},sort_keys=True))
'''
        (harness / 'installed_runner.py').write_text(runner)
        retained_harness = output / 'installed-harness'
        shutil.copytree(harness, retained_harness)
        proof = _logged(_isolated_script(python, harness, 'installed_runner.py', output / 'installed-sequence'),
                        outside, output, 'installed-proof', environment, timeout=600)
        details = json.loads(proof['stdout'])
        _json_once(output / 'installed-dependencies.json', details['dependencies'])
        # Perform a live isolated-interpreter rejection after successful installation.
        # Copy installation isolates this disposable venv from cached wheel artifacts.
        negative = '''import json,pathlib
import importlib.metadata
from locked_proof import marker_environment,locked_requirements,installed_inventory,assert_inventory
root=pathlib.Path(__file__).parent
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(),marker_environment())
distribution=importlib.metadata.distribution('urllib3')
metadata_files=[path for path in distribution.files if str(path).endswith('.dist-info/METADATA')]
if len(metadata_files)!=1: raise ValueError('urllib3 metadata file not unique')
metadata=pathlib.Path(distribution.locate_file(metadata_files[0]))
body=metadata.read_text()
old='Version: '+expected['urllib3']+'\\n'
if body.count(old)!=1: raise ValueError('urllib3 metadata does not have exact original version')
metadata.write_text(body.replace(old,'Version: 2.7.0\\n'))
actual=installed_inventory()
for name in ('pyarrow','requests','azure-identity','azure-storage-blob','azure-data-tables'):
    if actual[name]!=expected[name]: raise ValueError('negative test changed a direct pin')
version=json.loads((root/'expected-distribution.json').read_text())['version']
try: assert_inventory(expected,actual,version)
except ValueError as error: print(json.dumps({'transitive_mismatch_refused':True,'error':str(error)}))
else: raise AssertionError('wrong transitive version accepted')
'''
        (harness / 'transitive_refusal.py').write_text(negative)
        refusal = _logged(_isolated_script(python, harness, 'transitive_refusal.py'), outside,
                          output, 'transitive-mismatch-refusal', environment)
        # Retain the final negative script too; exact inventory must include it.
        shutil.copy2(harness / 'transitive_refusal.py', retained_harness / 'transitive_refusal.py')
        for command in ('backfill', 'daily'):
            help_script = ('from network_guard import install; install(); '
                           'from sec_edgar_ingest.cli import main; '
                           f'raise SystemExit(main(["{command}","--help"]))')
            _logged([str(python), '-I', '-c', 'import sys; sys.path.insert(0,' + repr(str(harness)) + '); ' + help_script],
                    outside, output, command + '-help', environment)
        _logged([str(python), '-I', '-c', 'import sys; sys.path.insert(0,' + repr(str(harness)) + '); '
            'from network_guard import install; install(); from sec_edgar_ingest.cli import main; '
            'raise SystemExit(main(["--version"]))'], outside, output, 'version', environment)
    if (repo / 'uv.lock').read_bytes() != lock_body:
        raise ValueError('accepted lock changed during proof')
    return {'exit': 0, 'wheel_name': wheel.name, 'wheel': digest(wheel_copy),
        'accepted_lock': digest(output / 'accepted-uv.lock'),
        'requirements': digest(output / 'requirements.txt'),
        'applicable_lock': expected_lock, 'installed': details,
        'transitive_mismatch_refusal': json.loads(refusal['stdout']),
        'source_equality': expected_sources, 'all22_stage7_checks': 'reserved/not_run'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline workflow process and installed proof')
    parser.add_argument('mode', choices=('native', 'installed'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--reviewed-source', type=Path)
    args = parser.parse_args(argv)
    if not args.output.is_absolute():
        parser.error('output must be an explicit absolute path')
    if args.mode == 'installed':
        if (args.wheel is None or args.reviewed_source is None or
                not args.wheel.is_absolute() or not args.reviewed_source.is_absolute()):
            parser.error('installed requires absolute reviewed wheel and source paths')
    elif args.wheel is not None or args.reviewed_source is not None:
        parser.error('native does not accept installed-artifact arguments')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    report = {'mode': args.mode, 'exit': 0, 'all22_stage7_checks': 'reserved/not_run'}
    try:
        report.update(installed(output, args.wheel, args.reviewed_source)
                      if args.mode == 'installed' else native(output))
    except BaseException:
        report.update(exit=1, traceback=traceback.format_exc())
    report['runtime_seconds'] = time.monotonic() - started
    _json_once(output / 'report.json', report)
    _json_once(output / 'sha256.json', inventory(output))
    verify_inventory(output)
    print(json.dumps({'exit': report['exit'], 'report': str(output / 'report.json'),
                      'all22_stage7_checks': 'reserved/not_run'}))
    return report['exit']


if __name__ == '__main__':
    raise SystemExit(main())
```

The installed sequence's `stdout` must be reserved for its one JSON result; Task 10 sequence captures all CLI child stdout/stderr itself. If it emits progress, redirect it to retained files before `installed_runner` prints the final JSON. The imported `workflow_proof` uses the main guard, so copied harness import does not execute a second proof. Its fixed file inventory includes every helper it imports, including `support_checked.py` if Task 10 uses it.

- [ ] **Step 5: Run green verifier tests, then the full required offline suite/build and fresh native/installed proof.**

```bash
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p test_workflow_installed_lock.py -v
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/network_guard.py discover -s packages/sec-edgar-ingest/tests -p 'test_*.py' -v
uv build --offline --all-packages
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest --help
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest backfill --help
uv run --offline --frozen --package sec-edgar-ingest sec-edgar-ingest daily --help
uv run --offline --frozen --package sec-edgar-ingest python -m sec_edgar_ingest --version
uv run --offline --frozen --package sec-edgar-ingest python -m compileall -q packages/sec-edgar-ingest/src
git -c core.whitespace=cr-at-eol diff --check
```

Use an explicit fresh evidence directory for each proof; the script refuses reuse. In the execution checkout set a task-specific variable to its inspected absolute path, and create only evidence roots after verifying they do not already exist:

```bash
stage4_checkout=$(pwd -P)
stage4_native_output="$stage4_checkout/specs/evidence/sec-filing-index-ingestion/stage-4/verification/plan5-native-final"
stage4_installed_output="$stage4_checkout/specs/evidence/sec-filing-index-ingestion/stage-4/verification/plan5-installed-final"
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/workflow_proof.py native --output "$stage4_native_output"
uv run --offline --frozen --package sec-edgar-ingest python packages/sec-edgar-ingest/tests/workflow_proof.py installed --output "$stage4_installed_output" --wheel "$stage4_checkout/dist/sec_edgar_ingest-0.1.0-py3-none-any.whl" --reviewed-source "$stage4_checkout/packages/sec-edgar-ingest/src"
```

Expected: targeted/full suite exit 0; build/help/version/compile/whitespace exit 0; each proof summary exit 0; fresh actual installed backfill/daily/legacy/reader sequence, complete applicable lock inventory, wrong transitive refusal, exact source equality and exact evidence inventory. Before selecting the wheel, inspect `dist` and require exactly the reviewed build's distribution wheel; if the filename changes, record the actual metadata/version and explicit file rather than select a stale glob member. No unsupported historical range or deployed capacity claim follows from success. Missing cached exact artifacts leave this task blocked; do not fetch or change pins. All 22 Stage 7 checks remain reserved/not_run.

- [ ] **Step 6: Resolve installed/native review and commit explicitly owned files/evidence.**

```bash
git add packages/sec-edgar-ingest/tests/locked_proof.py packages/sec-edgar-ingest/tests/test_workflow_installed_lock.py packages/sec-edgar-ingest/tests/workflow_proof.py
git commit -m "test: prove workflow wheel against complete offline frozen lock"
```

The controller inventories and explicitly stages the two fresh proof directories in a separate evidence commit after review; never use `git add -A`. Preserve previous retained evidence and approved source/snapshot bytes. Task 11 passing is not permission to merge/deploy/activate schedules or stamp later-stage checks complete.

## Traceability, acceptance and integration

Every row is planned offline work. Historical baseline/Task 1/Stage 3 results are retained inputs; they discharge none of the fresh Stage 4 gates below. All task steps remain unchecked until a separately authorized execution session records actual outcomes.

| Approved requirement | Implementation / exact authority | Fresh offline acceptance |
|---|---|---|
| R1, inclusive required start/end and once-pinned open endpoint | T6 frozen context/intent; T8 quarter_span and requested_quarters; T9 public CLI | T8 bounded Q3/Q4 and empty-quarter tests; T9 input/date/replay cases; T10 native/installed sequence |
| R1, valid member survives unrelated malformed/missing unit | T2 successful immediate projection preserves incomplete parent; T5 singleton checkpoint; T7 isolated legacy inventory; T8 retained gaps | T2 real failed-parent listing; T7 corrupt sibling/reopen; T8 all-refused/mixed/independent empty; T10 mixed progress and gate backlog |
| R2, handoff 2026-10-01, baseline overlap, outage and Q4/Q1 | Shipped discovery required-unit ledger/gap tokens; T8 fresh discover/pending union; T9 pin | T10 actual first daily, Q4→Q1→Q2 outage listings, older unacquired backlog, failed directory boundary hold, empty daily distinction |
| Older acquired/transformed/unpublished/gated/quarantined work remains visible independent of needs_acquisition | T2 registry/binding; T4 current evidence/obligations; T5 receipts; T7 original legacy parents; T8 union and order | T4 original and revised pins, ordinary unfinished publish; T7 child-only legacy; T10 empty fresh discovery with older repair/gate/backlog |
| Exact source checkpoint/origin settings, immutable raw pins, no recursive projection | T2 read_parent/project_member/read_member/transfer_binding; T3 origin/config/readback; T5 collect origin/current ETL | T2 tamper/divergent winner; T3 origin/current versions/raw/input cases; T5 forged receipt versions; T7 repeated bootstrap and corruption |
| Actual original root/year/quarter traversal, required directories and listing SHA/length | T2 pure recovery and actual reopen_listing; T4 parent/member provenance; T6 full selection capture | T2 retained listing corruption; T4 old failed parent after same-session repair; T6 empty parent/altered units/replay; T7 missing-parent reconstruction |
| F1: every publisher-affected quarter, including formerly affected quarters | T4 _affected_quarters union and exact active membership; T5/T6 full publication/capture set | T4 successful original Q3 followed by Q4-only replacement: Q3 invalid_source remains pending, Q4 can publish, Q3 pointer retained; T10 fresh workflow refuses complete coverage |
| F2: retained transport prefix vs terminal whole-source refusal | T1 failed quarantine subset invariant; T5 derives source refusal from exact terminal child/absence of accepted transform | Retained candidate nested decoder cases rerun in T1; T3/T5 real read_timeout prefix followed by valid body; T5 conflicting-row refusal; T10 whole workflow counters |
| F3: current pointer, historical capture and unfinished repair are distinct | T4 checked and ordinary legacy obligations; strict immutable original-call/input validation; call-keyed resolutions; T5 repair prefix | T4 ordinary ancillary failure and expired-original/fresh valid child, altered obligation refusal and later active generation; T10 os._exit after CAS, exact reopen/retry; original bytes and pointer version checked |
| F4: backfill/daily may share run/attempt without child collision | T3 SHA namespace includes parent command, parent attempt, step and child command | T3 deterministic same-ID two-parent test; T9 same-ID public commands |
| F5: aggregate precedence retains baseline gaps and checked attribution | T1 reducer includes skipped complete sources before precedence; T6 validates receipts/captures; T8 checks actual baseline absence | T1 retained gap codec/forged-marker tests; T8 all-refused exit7, mixed or independent missing exit3, complete skipped + refused; T10 gate-only10/mixed3; named shared fatal exits |
| F6: entire applicable frozen dependency graph, not five direct versions | T11 lock/export artifact SHA and canonical name/version inventory, isolated reviewed-wheel --no-deps | T11 missing/unexpected/transitive mismatch tests and real isolated wrong dist-info refusal; fresh install from accepted cached exact artifacts only |
| Frozen invocation and selection before dispatch; exact interrupted replay | T3 immutable call before child; T6 intent/selection content before descriptors; T8 reuses frozen jobs/receipt paths | T6 changed context/fixture/date/version refusal, selection/report object-created/index-missing repair; T10 twelve actual process death/reopen points |
| Completed replay after deadline constructs no discovery/SEC sender | T6 immutable historical validators and repairable index; T9 saved pin/context before deadline logic | T9 patched dispatcher-construction refusal, unchanged fixture cursors/report bytes; T10 exact replay; T11 installed copied test-only harness outside checkout |
| Reports retain complete/pending/failed disjoint source counters, quarantine failed subset, gates pending subset; quarter operations separate | T1 strict codecs/reducer; T5 exact MemberResult/evidence; T6 checked workflow report; T8 frozen selection counts | T1 alias/worst-state/nested type tests; T5 flag/ref/version/outcome tampering; T6 all selected and skipped captures/receipts; actual persisted T10 command/result/reader files |
| Halt/deadline keeps undispatched work pending; no publication repair finalization | T3 ChildUnfinished and shipped halt outcome mapping; T5 propagates unfinished publish; T8 ordered jobs; T9 structured lifecycle | T3 unfinished post-CAS; T6 fatal discovery/member vs undispatched receipt-less pending; T8 actual mid-run deadline after frozen selection, no dispatch, durable pending accounting; T9 preadapter validation/named exits; T10 death and boundary hold |
| Existing per-quarter pointer CAS/reader, withdrawal gate; no approval/force bypass | T3 checked shipped publish; T4 exact manifests/captures; T5 reports all outcomes; T9 closed public flags | T4 retained Q3/Q4 reader proof; T10 closed withdrawal gate and old gated backlog; existing ETL/catalog/publication/process regressions |
| Offline source/network/auth isolation, unchanged pins/limits, complete proof retention | Every task guard and unchanged uv.lock; T10 process guard; T11 -I/removed PYTHONPATH/site-packages/source-byte inventory | Full check script, network/auth guard, exact native/installed evidence inventories, whitespace/build/help/version/compile, independent whole-branch review |
| Scope, preservation and future deployment boundaries | This plan's authority gate; new create-only preservation/evidence receipts; original snapshots immutable | Before/after primary/retained inventories and Git state; owner reviews coverage; all 22 Stage 7 checks remain reserved/not_run |

Strict retained refusals remain byte-specific and whole-source:

| Source | Raw SHA-256 | Bytes | Conflicts | Required result |
|---|---|---:|---:|---|
| SEC-0141 / 2010Q1 | `aca38d21ee64795f6095c86c0424f94e16a322a4ec0eb6fd38d2e5d6f86822de` | 3,729,148 | 21 | No accepted Processing/ObservationRef; no publication; source unresolved/quarantined |
| SEC-0142 / 2015Q1 | `984c3130c617c11d085a4deff77a01c21b1113d5bb4c8b2173f5f87eb9f2a728` | 3,901,000 | 24 | Same strict whole-source refusal |
| SEC-0143 / 2026Q3 | `393a535f84b71ed34845f67aa5e5275ecc86afeb1a6558ad5623b0d7d0babe71` | 3,502,663 | 6 | Same strict whole-source refusal |

Keep the original specimen exit1 and the separate hash-bound Stage 3 amendment evidence. Do not reclassify these sources as successful zero-row inputs, select a duplicate winner, edit raw bytes, add parser tolerance or infer successful historical range/capacity. Stage 4 fixture success is bounded to the actual chosen inputs/range. Existing Stage 3 acceptance verifier and tests remain regression authority; they are not a Stage 4 success receipt.

- [ ] After Task 11 scoped proof passes, obtain a fresh whole-branch structural/spec/code review against the unchanged approved spec and this replacement plan, using a reviewer independent of implementers. Use actual available model/role names and record them. Resolve every actionable finding with covering evidence; rerun only affected checks, broadening full gates when changes justify it. Record owner review of actual R1/R2 source coverage; no max date substitutes for coverage.
- [ ] Preserve each command's argv, exit, complete stdout/stderr, platform/Python/version data, frozen lock/wheel/source hash inventory, actual fixture bytes, checked result/receipt/capture descriptors, process PIDs/death markers and installed package provenance. Keep failures/intermediate evidence in distinct create-only directories; never overwrite an earlier failure with a success summary. Explicitly stage only owned files and evidence in the execution checkout. No network push, merge or worktree removal is implied by passing tests.
- [ ] Apply writing-plans' resolve-before-defer/completion protocol only after all implementation/review gates and required owner answers are resolved. Do not stamp/retire during planning. Preserve approved snapshot bytes regardless of later document retirement. Treat original Plan 4 as superseded through a new completion record rather than modifying its approved source; while it remains in the active plan directory, retain the shared approved specification under the skill's shared-spec rule. Retire only executed Plan 5, report any deferred items with exact closure conditions, and keep the final implementation acceptance record explicit. Tick only Stage 4's roadmap entry at completion and revalidate Stage 5–8 boundaries; preserve historical primary roadmap bytes.
- [ ] Integration is a deliberate later owner decision. Present the reviewed execution commit, diff, actual offline evidence and preserved-worktree status; do not merge or discard worktrees as an automatic proof side effect. Preserve the stopped branch/worktree, planning branch/worktree and all approved evidence. A later authorized integration/cleanup must first carry every needed ignored file into an independently verified preservation root.

## Planning-session self-review and owner handoff

This document replaces execution order and evidence contracts for the existing approved specification. It does not approve implementation. The adjacent `replanning/verification.json` and `replanning/structural-review.md` record actual planning checks, remaining preservation recovery disposition and resolved static findings. They must distinguish static syntax/contract review from project imports, tests, builds and installed proofs, which are not run in this planning session.

Owner review concerns the concrete task ordering, interfaces, regression setup, evidence authority and scope in Plan 5. Any fresh execution authorization belongs in a new immutable approval receipt naming exact Plan 5/spec/roadmap hashes and a fresh preservation preflight; original Plan 4 approval does not authorize resumption. The execution session starts separately from the reviewed planning commit using subagent-driven-development by default, with fresh task reviewers, or executing-plans only if the owner chooses it. Do not continue implementation in this planning session.
