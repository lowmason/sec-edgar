"""Inspect current retained offline proof without rerunning acquisition."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import sys
import tarfile
import types
import zipfile

ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
EVIDENCE = SDD / 'final-review-fix1-evidence'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
BASE = '9098fe9b664d9f44a663fdd8357e34030c37e932'
sys.path.insert(0, str(ROOT / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
from sec_edgar_ingest.models import CommandResult
from sec_edgar_ingest.worksets import decode_source_workset, decode_snapshot_workset, encode_workset


def sha(body):
    return hashlib.sha256(body).hexdigest()


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(body), 'sha256': sha(body)}


def save(name, value):
    path = EVIDENCE / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def manifest(root):
    rows = json.loads((root / 'sha256-manifest.json').read_text())
    for row in rows:
        target = root / row['path']
        body = target.read_bytes()
        assert len(body) == row['bytes'] and sha(body) == row['sha256'], target
    files = [path for path in root.rglob('*') if path.is_file()]
    assert len(files) == len(rows) + 1
    return {'root': root.relative_to(ROOT).as_posix(), 'payload_records': len(rows),
            'physical_files': len(files), 'physical_bytes': sum(path.stat().st_size for path in files),
            'manifest': record(root / 'sha256-manifest.json'), 'rootmap': record(root / 'retention-map.json')}


def sqlite_dump_matches(root, state):
    with sqlite3.connect((root / 'state/.fixture-state/state.sqlite3').as_uri() + '?mode=ro&immutable=1', uri=True) as connection:
        columns = [row[1] for row in connection.execute('PRAGMA table_info(records)')]
        rows = connection.execute('SELECT * FROM records').fetchall()
    parsed = [dict(zip(columns, row)) for row in rows]
    counts = {}
    for kind, saved in state.items():
        actual = [row for row in parsed if row['partition'] == 'sec-owner-lowell-mason:' + kind]
        counts[kind] = len(actual)
        assert len(actual) == len(saved), kind
        for row in saved:
            assert any(json.loads(candidate['value']) == row['value'] and candidate['version'] == row['version']
                       for candidate in actual), kind
    return counts


def inspect_combined(root):
    summary = json.loads((root / 'sequence-summary.json').read_text())
    assert summary['prescribed_step_4'] == 'executed with explicitly approved separate configs'
    calls = json.loads((root / 'calls.json').read_text())
    expected = [2, 0, 0, 0, 0, 2, 0, 3, 3, 0, 0]
    assert [call['exit'] for call in calls] == expected
    for call in calls:
        exit_receipt = json.loads((root / (call['label'] + '.exit.json')).read_text())
        assert exit_receipt['exit'] == exit_receipt['expected'] == call['exit']
        assert json.loads((root / (call['label'] + '.argv.json')).read_text()) == call['argv']
    q, d = summary['quarterly_results'], summary['daily_results']
    assert [value['outcome'] for value in d] == ['success', 'incomplete', 'success', 'success']
    assert (d[1]['downloaded'], d[1]['pending'], d[1]['failed'], d[1]['snapshot_workset_ref']) == (1, 1, 1, None)
    assert (d[2]['downloaded'], d[2]['unchanged'], d[3]['downloaded'], d[3]['unchanged']) == (1, 1, 0, 2)
    assert q[1]['snapshot_workset_ref'] == q[2]['snapshot_workset_ref']
    assert d[2]['snapshot_workset_ref'] == d[3]['snapshot_workset_ref']
    for first, replay in [('collect-1', 'collect-1-exact-replay'), ('daily-collect-1', 'daily-collect-1-replay')]:
        assert (root / (first + '.stdout')).read_bytes() == (root / (replay + '.stdout')).read_bytes()
    state = json.loads((root / 'final-state-records.json').read_text())
    counts = sqlite_dump_matches(root, state)
    assert counts == {'Attempt': 7, 'Binding': 3, 'FixtureResponseCursor': 10, 'TransportAttempt': 11}
    transports = [row['value'] for row in state['TransportAttempt']]
    by_attempt = Counter(value['context']['attempt_id'] for value in transports)
    assert dict(by_attempt) == {'discover-1': 3, 'collect-1': 1, 'daily-discover-1': 4, 'daily-collect-1': 2, 'daily-collect-2': 1}
    late = sorted((value for value in transports if value['url'].endswith('master.20261002.idx')), key=lambda value: value['begun_at'])
    assert [value['status'] for value in late] == [404, 200]
    assert sum(value['url'].endswith('master.20261001.idx') for value in transports) == 1
    assert sum(value['url'].endswith('full-index/2015/QTR1/master.zip') for value in transports) == 1
    cursors = [row['value'] for row in state['FixtureResponseCursor']]
    assert sorted(value['cursor'] for value in cursors) == [1] * 9 + [2]
    objects = root / 'state/.fixture-state/objects'
    worksets, raw, contexts = {}, {}, []
    for results in (q, d):
        source = decode_source_workset((objects / results[0]['source_workset_ref']).read_bytes())
        for result in results:
            context = result['context']
            result_ref = f"runs/sec/{context['run_id']}/{context['command']}/{context['attempt_id']}/result.json"
            actual = CommandResult.from_json((objects / result_ref).read_bytes())
            assert actual.to_mapping() == result
            assert actual.context.command == ('discover' if result is results[0] else 'collect')
            if result is not results[0]:
                assert actual.context.attempt_id != source.context.attempt_id
            contexts.append({'attempt': actual.context.attempt_id, 'execution': actual.context.execution_id,
                             'current_started_at': actual.context.started_at.isoformat(),
                             'source_origin_started_at': source.context.started_at.isoformat()})
            for field, decoder, kind in [('source_workset_ref', decode_source_workset, 'source'),
                                         ('snapshot_workset_ref', decode_snapshot_workset, 'snapshot')]:
                ref = result[field]
                if ref is None:
                    continue
                body = (objects / ref).read_bytes()
                frozen = decoder(body)
                assert encode_workset(frozen) == body
                assert ref == f'worksets/sec/{kind}/sha256={frozen.workset_id}/workset.json'
                worksets[ref] = frozen.workset_id
                if kind == 'snapshot':
                    assert frozen.context == source.context and frozen.source_workset_id == source.workset_id
                    for snap in frozen.snapshots:
                        original = (objects / snap.raw_path).read_bytes()
                        assert sha(original) == snap.sha256 and len(original) == snap.byte_count
                        assert any(row['value']['source_workset_id'] == frozen.source_workset_id
                                   and row['value']['source_id'] == snap.source_id
                                   and row['value']['snapshot_sha256'] == snap.sha256 for row in state['Binding'])
                        raw[snap.raw_path] = {'source_id': snap.source_id, 'sha256': snap.sha256, 'bytes': snap.byte_count}
    assert len(worksets) == 4 and len(raw) == 3
    return {'manifest': manifest(root), 'command_exits': [{'label': call['label'], 'exit': call['exit']} for call in calls],
            'table_counts': counts, 'transports_by_attempt': dict(by_attempt) | {'collect-2': 0, 'daily-collect-3': 0},
            'delayed_statuses': [value['status'] for value in late], 'cursor_values': sorted(value['cursor'] for value in cursors),
            'config_sha256': summary['config_sha256'], 'worksets': worksets, 'raw': raw, 'contexts': contexts,
            'exact_complete_and_incomplete_replays_equal': True, 'completed_members_fetched_once': True}


def inspect_installed(root):
    calls = json.loads((root / 'commands.json').read_text())
    assert len(calls) == 11 and all(call['exit'] == 0 for call in calls)
    for call in calls:
        assert json.loads((root / (call['label'] + '.argv.json')).read_text()) == call['argv']
        assert json.loads((root / (call['label'] + '.exit.json')).read_text())['exit'] == 0
    installed = json.loads((root / 'installed-versions.json').read_text())
    assert len(installed['versions']) == 21
    assert 'fresh-env/lib/python3.14/site-packages/' in installed['package_file']
    summary = json.loads((root / 'wheel-proof-summary.json').read_text())
    assert summary['exact_replay_no_http'] and summary['transport_count'] == 4
    sources = []
    source_root = ROOT / 'packages/sec-edgar-ingest/src'
    artifacts = root / 'build-artifacts'
    wheel_name, sdist_name = 'sec_edgar_ingest-0.1.0-py3-none-any.whl', 'sec_edgar_ingest-0.1.0.tar.gz'
    with zipfile.ZipFile(artifacts / wheel_name) as archive:
        for path in sorted((source_root / 'sec_edgar_ingest').rglob('*')):
            if path.suffix != '.py' and path.name != 'py.typed':
                continue
            body = path.read_bytes()
            assert archive.read(path.relative_to(source_root).as_posix()) == body
            previous = subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'])
            sources.append(record(path) | {'equals_base': body == previous})
    assert len(sources) == 19
    assert [row['path'] for row in sources if not row['equals_base']] == [
        'packages/sec-edgar-ingest/src/sec_edgar_ingest/storage/azure.py',
        'packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py']
    with tarfile.open(artifacts / sdist_name) as archive:
        for name in ('README.md', 'pyproject.toml'):
            assert archive.extractfile('sec_edgar_ingest-0.1.0/' + name).read() == (ROOT / 'packages/sec-edgar-ingest' / name).read_bytes()
    for name in (wheel_name, sdist_name):
        assert (artifacts / name).read_bytes() == (ROOT / 'dist' / name).read_bytes()
    return {'manifest': manifest(root), 'installed_versions': installed, 'command_count': len(calls),
            'artifact_hashes': [record(artifacts / name) for name in (wheel_name, sdist_name)],
            'package_source_hashes': sources, 'all19_source_and_typing_files_equal_wheel': True,
            'only_two_production_files_changed_from_BASE': True, 'exact_replay_no_http': True, 'transport_count': 4}


def inspect_compatibility():
    from support import fixture_source, fixture_workset, fixture_snapshot
    import sec_edgar_ingest.worksets as current
    old = types.ModuleType('sec_edgar_ingest._final_fix_base_worksets')
    old.__package__ = 'sec_edgar_ingest'
    previous = subprocess.check_output(['git', 'show', f'{BASE}:packages/sec-edgar-ingest/src/sec_edgar_ingest/worksets.py'])
    exec(compile(previous, 'BASE/worksets.py', 'exec'), old.__dict__)
    results = []
    for sources in [(fixture_source(),), (fixture_source('2024-02-29', 'daily'),),
                    (fixture_source('2026-10-01', 'daily'), fixture_source('2026-10-02', 'daily'))]:
        source = fixture_workset(sources)
        snapshots = tuple(fixture_snapshot(member, b'exact unchanged bytes') for member in sources)
        old_frozen = old.make_snapshot_workset(source, snapshots)
        new_frozen = current.make_snapshot_workset(source, snapshots)
        assert old.encode_workset(old_frozen) == current.encode_workset(new_frozen)
        results.append({'kinds': [member.kind for member in sources], 'source_id': source.workset_id,
                        'snapshot_id': new_frozen.workset_id, 'encoded_bytes_equal_BASE': True})
    old_objects = VERIFICATION / 'sec-edgar-stage-2-k8g11etz/state/.fixture-state/objects'
    historical = []
    for path in sorted((old_objects / 'worksets/sec').rglob('workset.json')):
        body = path.read_bytes()
        value = json.loads(body)
        decoder = decode_source_workset if value['workset_type'] == 'source' else decode_snapshot_workset
        frozen = decoder(body)
        assert current.encode_workset(frozen) == body
        historical.append(record(path) | {'workset_id': frozen.workset_id})
    assert len(historical) == 4
    return {'generated_BASE_byte_comparisons': results, 'four_historical_combined_worksets_decode_and_encode_unchanged': historical}


def inspect_check():
    label = 'latest-complete-check-corrected'
    command = json.loads((EVIDENCE / (label + '.command.json')).read_text())
    assert command['exit'] == 0 and command['argv'] == ['scripts/check-sec-edgar-ingest.sh']
    stdout = (EVIDENCE / (label + '.stdout.txt')).read_text()
    stderr = (EVIDENCE / (label + '.stderr.txt')).read_text()
    assert re.search(r'Ran 302 tests in [0-9.]+s\s+OK', stderr)
    tests = re.findall(r'^test_.* \.\.\. ok$', stderr, flags=re.MULTILINE)
    assert len(tests) == 302
    assert not re.search(r'(^|\n)(FAIL|ERROR|WARNING|Traceback)|ResourceWarning|FAILED \(', stderr)
    assert 'Successfully built dist/sec_edgar_ingest-0.1.0.tar.gz' in stderr
    assert 'Successfully built dist/sec_edgar_ingest-0.1.0-py3-none-any.whl' in stderr
    assert stdout.splitlines()[-1] == '0.1.0'
    return {'command': command, 'test_records': len(tests), 'test_footer': re.search(r'Ran 302 tests in [0-9.]+s', stderr)[0],
            'stdout': record(EVIDENCE / (label + '.stdout.txt')),
            'stderr': record(EVIDENCE / (label + '.stderr.txt')), 'all_output_lines_inspected': True}


def main():
    installed, combined = map(lambda name: VERIFICATION / name, sys.argv[1:])
    assert len(sys.argv) == 3
    owner_path = VERIFICATION / 'task-8-i1-checkpoint/sdd/task-8-daily-endpoint-owner-answer.json'
    owner = json.loads(owner_path.read_text())
    assert owner['answer'] == 'Yes' and owner['owner'] == 'Lowell Mason'
    assert sha(owner_path.read_bytes()) == 'f9720b21df9f56135386496f39bb2ec4d310614410b1b5f8645fdc07a7b963ac'
    sdk = json.loads((ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/sdk-signatures.json').read_text())
    for name, digest in sdk['source_sha256'].items():
        assert sha((Path(sdk['source_root']) / name).read_bytes()) == digest
    result = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'base': BASE,
              'actual_implementation_head': subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip(),
              'platform': platform.platform(), 'python': sys.version,
              'owner_yes': record(owner_path), 'sdk_source_hashes_unchanged': len(sdk['source_sha256']),
              'check': inspect_check(), 'installed': inspect_installed(installed),
              'combined': inspect_combined(combined), 'compatibility': inspect_compatibility(),
              'all22_stage7_checks': 'reserved', 'live_access_or_credentials_used': False,
              'fresh_scoped_review': 'pending controller', 'exit_code': 0}
    primary = subprocess.run([sys.executable, str(SDD / 'verify_primary.py')], capture_output=True, text=True)
    save('primary-preservation.json', {'argv': [sys.executable, str(SDD / 'verify_primary.py')], 'cwd': str(ROOT),
                                     'stdout': primary.stdout, 'stderr': primary.stderr, 'exit_code': primary.returncode})
    assert primary.returncode == 0
    preserved = json.loads(primary.stdout)
    assert preserved['changed_protected_files'] == preserved['restored_deletions'] == []
    result['primary'] = preserved
    save('fresh-proof-inspection.json', result)
    print(json.dumps({'exit_code': 0, 'installed': result['installed']['manifest'], 'combined': result['combined']['manifest'],
                      'test_footer': result['check']['test_footer'], 'production_files': 19, 'sdk_source_hashes': 27}))


if __name__ == '__main__':
    main()
