"""Fixture stores and a twice-run selection for the Stage 2a1 per-phase selection checks (H1, H2, P7)."""
from network_guard import install
install()

import contextlib
import hashlib
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from support import fixture_settings
from support_process import checked_dispatcher, checked_fault
from support_reconcile import A, B, Q3_URL, Q4_URL, X, Y, quarterly
from support_workflow_evidence import EvidenceFixture, quarterly_bytes
from support_workflows import BASE, CommandHarness, build_pack, idx, quarter_pack, replace_pack_body, simple_pack
from sec_edgar_ingest.config import pin_context
from sec_edgar_ingest.models import RunContext, canonical_json, freeze, to_mapping_value
from sec_edgar_ingest.runtime import configured_descriptor
from sec_edgar_ingest.state import AcquisitionState, attempt_key
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.workflows.checked import ChildUnfinished
from sec_edgar_ingest.workflows.completion import evaluate_member
from sec_edgar_ingest.workflows.contracts import LOCAL_CONTRACT, WORKFLOW_PRIORITY
from sec_edgar_ingest.workflows.members import WorkflowMembers
from sec_edgar_ingest.workflows.results import freeze_selection, freeze_workflow, write_workflow_result
from sec_edgar_ingest.workflows.runner import run_workflow, select_work

# The oracle "without kept values" (P7): `select_work` gets None from the name, so every check runs today's code.
NO_CHECKS = patch('sec_edgar_ingest.workflows.runner.SelectionChecks', lambda *args: None)

SCENARIOS = ('finished', 'pending', 'superseded', 'repair_obligation', 'corrupt_member', 'corrupt_parent',
             'corrupt_publish_call', 'empty')
TODAY = date(2026, 10, 7)
# A fault that leaves the discovery child without a durable result (ChildUnfinished), as in
# test_workflow_runner.test_no_result_discovery_keeps_required_ledger_and_older_pending_jobs.
DISCOVERY_FAILURE = 'discovery.finish_failure'


def workflow_start(h, command, run, *, started=None, store=None, objects=None):
    """A pinned and frozen workflow context, its intent and the fixture `Dispatcher`, as `RunnerTests.run_parent`
    builds them. `started` fixes the context's clock; the stores default to the harness's own."""
    store = h.store if store is None else store
    objects = h.objects if objects is None else objects
    started = datetime.now(timezone.utc) if started is None else started
    context = RunContext(run, 'manual', command, 'a', h.settings.etl.parser_version, h.settings.etl.schema_version,
                         h.settings.config_sha256, started, started + timedelta(seconds=1800),
                         WORKFLOW_PRIORITY[command], runtime=configured_descriptor(h.settings),
                         format_version='sec-local-run-context-v1')
    context, end = pin_context(h.settings, context, TODAY)
    intent = {'contract_version': LOCAL_CONTRACT, 'command': command, 'today': TODAY.isoformat(),
              'fixture_sha256': hashlib.sha256(h.pack.read_bytes()).hexdigest(), 'pinned_end_quarter': end}
    context = freeze_workflow(context, intent, store, objects)
    return context, intent, checked_dispatcher(context, h.settings, h.pack, h.root, store, objects)


def _close(opened):
    for resource in reversed(opened):
        if hasattr(resource, 'close'):
            resource.close()


def _restore(pristine, state):
    shutil.rmtree(state)
    shutil.copytree(pristine, state)


def discovery_flags(context):
    """The discovery child's flags, as `runner.select_work` builds them."""
    mode = 'daily' if context.command == 'daily' else 'quarterly'
    flags = ('--mode', mode, '--discovery-id', 'workflow-' + context.command + '-' + context.run_id)
    if context.command == 'reconcile':
        flags += ('--refresh',)
    return flags


def _discovery_fault(h, discovery_fails):
    # A one-shot fault of its own for each discovery child, so each one fails.
    return checked_fault(h.root, point=DISCOVERY_FAILURE) if discovery_fails else contextlib.nullcontext()


def select_twice(harness, command, *, discovery_fails=False):
    """`canonical_json` of one `select_work` with real checks and one under `NO_CHECKS` (plan 9 D4).

    Each selection runs on its own copy of the harness store, placed at the harness's storage root so that the
    settings, the context and the deployment binding stay the same. Both share one pinned context and intent.

    The discovery is primed. H1 compares selections for the same store, intent and discovery result, but two fresh
    discovery children never agree: each takes its context's `started_at` and each receipt's `received_at` from the
    wall clock, and each receipt records a random temporary path. A frozen `checked_clock` does not help, because
    the coordinator then refuses a wall clock that diverges from its monotonic clock. So the selection's own
    discovery child (the same pinned context, attempt and step) runs once on the store before it is copied. Each
    selection's discovery child then resumes that session from its cached listings and returns the same parent, or
    raises again under `discovery_fails`. The harness store is its untouched copy again afterwards.
    """
    # `freeze` first: a list of already-complete captures holds FrozenMapping values.
    return _twice(harness, command, discovery_fails, lambda select: canonical_json(to_mapping_value(freeze(select()))))


def refusal_twice(harness, command):
    """The type and message of the exception that `select_work` raises with real checks, and under `NO_CHECKS`, as
    `select_twice` runs them. A selection that returns fails the caller."""
    def refusal(select):
        try:
            selection = select()
        except Exception as error:
            return type(error).__name__, str(error)
        raise AssertionError('select_work returned a selection: ' + repr(selection['gaps']))
    return _twice(harness, command, False, refusal)


def _twice(harness, command, discovery_fails, outcome):
    """`outcome(select)` for the selection with real checks and for the one under `NO_CHECKS` (see `select_twice`)."""
    h = harness
    state = Path(h.settings.storage.root)
    instant = datetime.now(timezone.utc)
    results = []
    h.close()
    with tempfile.TemporaryDirectory(prefix='sec-select-twice-') as temporary:
        original, primed = Path(temporary) / 'original', Path(temporary) / 'primed'
        shutil.copytree(state, original)
        try:
            opened = open_stores(h.settings)
            store, objects, _ = opened
            try:
                context, _, dispatcher = workflow_start(h, command, 'select-twice', started=instant,
                                                        store=store, objects=objects)
                with _discovery_fault(h, discovery_fails), contextlib.suppress(ChildUnfinished):
                    dispatcher.execute('discover', 'discover', h.settings, discovery_flags(context))
            finally:
                _close(opened)
            shutil.copytree(state, primed)
            for oracle in (contextlib.nullcontext(), NO_CHECKS):
                _restore(primed, state)
                opened = open_stores(h.settings)
                store, objects, _ = opened
                try:
                    context, intent, dispatcher = workflow_start(h, command, 'select-twice', started=instant,
                                                                 store=store, objects=objects)
                    with _discovery_fault(h, discovery_fails), oracle:
                        results.append(outcome(lambda: select_work(context, h.settings, intent, dispatcher,
                                                                   store, objects)))
                finally:
                    _close(opened)
        finally:
            _restore(original, state)
            h.opened = open_stores(h.settings)
            h.store, h.objects, h.leases = h.opened
    return tuple(results)


def _workflow(h, command, run, *codes):
    """One workflow command through the CLI. It must report, and exit with one of `codes`."""
    code, message = h.invoke(command, run=run)
    if code not in codes or message.get('result_ref') is None:
        raise AssertionError(f'{command} {run!r} exited {code}: {h.calls[-1]}')
    return message


def _finished(root):
    """Both members of simple_pack complete, as in test_workflow_runner.test_bounded_inclusive_backfill_captures_both_quarters."""
    h = CommandHarness(root, simple_pack(root / 'pack'))
    _workflow(h, 'backfill', 'finished', 0)
    return h


def _pending(root):
    """Both members are refused and stay pending, as the older run of
    test_workflow_runner.test_no_result_discovery_keeps_required_ledger_and_older_pending_jobs."""
    h = CommandHarness(root, simple_pack(root / 'pack', conflicting=True))
    _workflow(h, 'backfill', 'older', 7)
    return h


def _reconcile_pack(root, number, q3_rows, q4_rows=(X, Y)):
    """support_reconcile.ReconcileFixture.pack: each phase gets a fresh pack, so every response cursor restarts."""
    pack = quarter_pack(root / f'pack-{number}', ('2026Q3', '2026Q4'), empty_daily=True)
    replace_pack_body(pack, Q3_URL, quarterly(q3_rows))
    replace_pack_body(pack, Q4_URL, quarterly(q4_rows))
    return pack


def _superseded(root):
    """test_reconcile_workflow.test_gated_then_reverted_member_is_superseded_by_the_later_download, before its revert-2
    reconcile. The pack is the fresh one of that reconcile, whose selection supersedes both held members (D4)."""
    settings = fixture_settings(backfill={'start_quarter': '2026Q3', 'end_quarter': 'open'},
        daily={'start_date': '2026-10-01'}, etl={'parser_version': 'fixture-index-parser-v1'},
        http={'retry_base_seconds': 0.001, 'retry_cap_seconds': 0.001},
        fixture={'allow_clock_override': True, 'allow_deadline_override': False})
    h = CommandHarness(root, _reconcile_pack(root, 1, (A, B)), settings)
    _workflow(h, 'backfill', 'base', 0)
    h.pack = _reconcile_pack(root, 2, (A,))
    _workflow(h, 'reconcile', 'gate', 10)
    # A plain backfill binds its member to the gated bytes by reuse.
    h.pack = _reconcile_pack(root, 3, (A,))
    _workflow(h, 'backfill', 'plain', 10)
    # The SEC reverts to the base bytes; that download completes during this run, so the gate still holds it.
    h.pack = _reconcile_pack(root, 4, (A, B))
    _workflow(h, 'reconcile', 'revert-1', 10)
    h.pack = _reconcile_pack(root, 5, (A, B))
    return h


def _transformed(f):
    code, _, result = f.invoke('transform', f.snapshot_input(quarterly_bytes('2026-07-01')))
    if code != 0:
        raise AssertionError(f'transform exited {code}')
    return result.transformed_workset_ref


def _failed_publish(f, transformed):
    with checked_fault(f.root):
        code, call, result = f.invoke('publish', transformed)
    if (code, result) != (9, None):
        raise AssertionError(f'faulted publish exited {code}')
    return call


def _repair_obligation(f):
    """test_workflow_completion.test_fresh_attempt_resolves_repair_without_rewriting_original_attempt, before its
    repair: a faulted publish leaves one repair obligation."""
    _failed_publish(f, _transformed(f))
    evaluation = evaluate_member(f.value, f.workflow.parser_version, f.workflow.schema_version, f.store, f.objects)
    if evaluation.complete or len(evaluation.obligations) != 1:
        raise AssertionError(evaluation)


def _corrupt_publish_call(f):
    """test_workflow_completion.test_corrupt_begun_checked_call_blocks_completion: the begun checked publish call's
    Attempt row is changed after a later publish succeeds."""
    transformed = _transformed(f)
    call = _failed_publish(f, transformed)
    code = f.invoke('publish', transformed)[0]
    if code != 0:
        raise AssertionError(f'fresh publish exited {code}')
    key = attempt_key(RunContext.from_mapping(call['context']))
    attempt = f.store.get('Attempt', key)
    altered = attempt.to_mapping()['value']
    altered['context']['execution_id'] = 'corrupt-begun-execution'
    f.store.replace('Attempt', key, altered, attempt.version)


def _corrupt_parent(f):
    """The member's parent fails its re-validation (spec §4.4 item 1): its stored DiscoverySession row changes the frozen
    overlap date, so `read_parent` refuses it with 'parent changes frozen origin' (D4)."""
    discovery_id = 'checked-completion-parent'
    row = AcquisitionState(f.store).discovery_session(discovery_id)
    value = row.to_mapping()['value']
    value['frozen'] = {**value['frozen'], 'overlap_from': '2026-01-02'}
    f.store.replace('DiscoverySession', hashlib.sha256(discovery_id.encode()).hexdigest(), value, row.version)


def _corrupt_registration(f):
    """The session corruption of test_workflow_completion.test_historical_provenance_rejects_session_and_registry_corruption,
    made in the stored DiscoverySession row of the member's parent. `read_parent` does not read `registered`, so the
    member is selected and its provenance capture refuses it: `select_work` raises (spec §4.4 item 1, D4)."""
    discovery_id = 'checked-completion-parent'
    row = AcquisitionState(f.store).discovery_session(discovery_id)
    f.store.replace('DiscoverySession', hashlib.sha256(discovery_id.encode()).hexdigest(),
                    {**row.to_mapping()['value'], 'registered': 'copied-registration'}, row.version)


def _from_evidence(root, prepare):
    """An EvidenceFixture store, as test_workflow_completion.CompletionTests.setUp builds it, prepared by `prepare`
    and opened by a CommandHarness on an empty pack, as in
    test_workflow_runner.test_formerly_affected_q3_is_not_completed_by_q4_publication."""
    f = EvidenceFixture(root / '.fixture-state')
    try:
        prepare(f)
        settings = f.settings
    finally:
        f.close()
    return CommandHarness(root, simple_pack(root / 'fresh-pack', empty=True), settings=settings)


def _corrupt_member(root):
    """test_workflow_runner.test_corrupt_retained_registry_and_receipt_do_not_block_valid_siblings, before its second run:
    a corrupt registry row, one valid run, then a corrupt receipt row for one of its members."""
    h = CommandHarness(root, simple_pack(root / 'pack'))
    h.store.insert('WorkflowMember', 'broken-member-row', {'source': {'source_id': 'bad'}})
    _workflow(h, 'backfill', 'valid-with-corrupt-sibling', 3)
    old = WorkflowMembers(h.store, h.objects).inventory()[0][0]
    h.store.insert('WorkflowMemberResult', 'broken-receipt-row', {
        'member_id': old['member_id'], 'parser_version': h.settings.etl.parser_version,
        'schema_version': h.settings.etl.schema_version, 'ref': 'missing/corrupt-receipt.json',
        'sha256': 'a' * 64, 'bytes': 1})
    return h


def _empty(root):
    """A first run's store: one low-level discovery, no registered member and no publish call, as
    test_pre_dispatch_cost.SelectionChecksTests.discovered builds it."""
    h = CommandHarness(root, simple_pack(root / 'pack'))
    code, message = h.invoke('discover', ('--mode', 'daily', '--discovery-id', 'empty-store'))
    if code != 0:
        raise AssertionError(message)
    return h


def scenario(root: Path, name: str) -> CommandHarness:
    """A fixture store for one selection-equality case, or the `corrupt_registration` refusal case. The caller closes
    the harness."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    builders = {'finished': _finished, 'pending': _pending, 'superseded': _superseded,
                'repair_obligation': lambda root: _from_evidence(root, _repair_obligation),
                'corrupt_member': _corrupt_member,
                'corrupt_parent': lambda root: _from_evidence(root, _corrupt_parent),
                'corrupt_publish_call': lambda root: _from_evidence(root, _corrupt_publish_call),
                'empty': _empty,
                # Not a selection-equality case: `select_work` raises on it (see `refusal_twice`).
                'corrupt_registration': lambda root: _from_evidence(root, _corrupt_registration)}
    return builders[name](root)


def daily_pack(root, members):
    """simple_pack's listings, with `members` daily sources in daily-index/2026/QTR3 and none in QTR4."""
    listings, bodies = {}, {}
    for family in ('full-index', 'daily-index'):
        base = BASE + family + '/'
        listings[base + 'index.json'] = [('2026', 'dir')]
        listings[base + '2026/index.json'] = [('QTR3', 'dir'), ('QTR4', 'dir')]
        listings[base + '2026/QTR4/index.json'] = []
    days = [date(2026, 7, 1) + timedelta(days=offset) for offset in range(members)]
    if any(day.month > 9 for day in days):
        raise ValueError('daily sources must stay inside 2026Q3')
    names = ['master.' + day.strftime('%Y%m%d') + '.idx' for day in days]
    leaf = BASE + 'daily-index/2026/QTR3/'
    listings[leaf + 'index.json'] = [(name, 'file') for name in names]
    listings[BASE + 'full-index/2026/QTR3/index.json'] = []
    for number, (day, name) in enumerate(zip(days, names), start=1):
        path = f'edgar/data/123456/0000123456-26-{number:06d}.txt'
        bodies[leaf + name] = idx((('123456', 'Example', '10-K', day.strftime('%Y%m%d'), path),), 'daily')
    return build_pack(root, listings, bodies)


def registered_store(root: Path, members: int) -> CommandHarness:
    """A fixture `daily` run over `members` daily sources whose deadline leaves no dispatch time, as
    test_workflow_runner.test_deadline_after_selection_records_undispatched_units_without_child_work runs one.
    Every member is registered, and none is processed."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    h = CommandHarness(root, daily_pack(root / 'pack', members))
    try:
        context, intent, dispatcher = workflow_start(h, 'daily', 'registered')
        selected = select_work(context, h.settings, intent, dispatcher, h.store, h.objects)
        # Discovery runs in real time: report the gaps here instead of a bare count mismatch further down.
        if len(selected['members']) != members:
            raise AssertionError(selected['gaps'])
        freeze_selection(context, selected, h.store, h.objects)
        expired = context.deadline + timedelta(seconds=1)
        with patch('sec_edgar_ingest.workflows.runner.datetime') as clock, \
                patch('sec_edgar_ingest.workflows.results.datetime') as accounting_clock, \
                patch.object(dispatcher, 'execute', side_effect=AssertionError('expired child dispatch')):
            clock.now.return_value = expired
            accounting_clock.now.return_value = expired
            report = run_workflow(context, h.settings, intent, dispatcher, h.store, h.objects)
            write_workflow_result(report, h.store, h.objects)
        if report.counts['pending_sources'] != members or tuple(h.store.scan('Processing', {})):
            raise AssertionError(report.counts)
    except BaseException:
        h.close()
        raise
    return h
