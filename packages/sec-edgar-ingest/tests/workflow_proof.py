from network_guard import install
install()
from sec_edgar_ingest.models import to_mapping_value
import contextlib, hashlib, json, multiprocessing, os, shutil
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from support import fixture_settings
from support_workflows import BASE, CommandHarness, listing, idx, simple_pack
from sec_edgar_ingest.models import canonical_json
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


def harness_files() -> tuple[Path, ...]:
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


def sequence(output: Path) -> Mapping[str, object]:
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
    settings = h.settings
    guards = {'parser_version': settings.etl.parser_version, 'schema_version': settings.etl.schema_version,
              'exchange_deadline_seconds': settings.http.exchange_deadline_seconds,
              'max_received_bytes': settings.http.max_received_bytes,
              'max_expanded_bytes': settings.http.max_expanded_bytes}
    expected_guards = {'parser_version': 'fixture-index-parser-v1', 'schema_version': 'sec-index-v1',
                       'exchange_deadline_seconds': 90, 'max_received_bytes': 67108864,
                       'max_expanded_bytes': 536870912}
    if guards != expected_guards:
        h.close()
        raise AssertionError('proof configuration guards differ')
    put_json(output / 'checked-config.json', guards)
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
        with Path(marker).with_suffix('.stdout').open('x', buffering=1) as stdout, \
             Path(marker).with_suffix('.stderr').open('x', buffering=1) as stderr, \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
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
    put_json(output / 'worker-command.json', {'argv': argv, 'point': point})
    child = multiprocessing.get_context('spawn').Process(target=process_worker,
        args=(h.config, pack, output, argv, point, marker))
    child.start()
    child.join(30)
    if child.is_alive():
        child.terminate(); child.join(5)
        raise AssertionError('worker did not reach durable boundary ' + point)
    if child.exitcode != 91 or not marker.is_file() or json.loads(marker.read_text())['point'] != point:
        raise AssertionError({'point': point, 'exit': child.exitcode})
    put_json(output / 'worker-exit.json', {'exit': child.exitcode, 'point': point})
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


def native(output: Path) -> Mapping[str, object]:
    output = Path(output)
    if not output.is_dir() or any(output.iterdir()):
        raise ValueError('native requires an existing empty create-only output directory')
    sequence_output = output / 'sequence'
    sequence_output.mkdir(exist_ok=False)
    result = sequence(sequence_output)
    recovered = [process_case(output / ('process-' + point.replace('.', '-')), point) for point in PROCESS_POINTS]
    put_json(output / 'process-recovery.json', recovered)
    return {'exit': 0, 'sequence': result, 'process_recovery': recovered,
            'all22_stage7_checks': 'reserved/not_run'}
