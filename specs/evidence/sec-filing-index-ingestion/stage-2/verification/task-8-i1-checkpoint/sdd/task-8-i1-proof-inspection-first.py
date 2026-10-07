"""Read-only I1 source/artifact/context checks; write only new Task 8 receipts."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from sec_edgar_ingest.models import CommandResult
from sec_edgar_ingest.worksets import decode_source_workset, decode_snapshot_workset, encode_workset

BASE = '49c50512202ca7950b222683776d8865b450b8b2'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
BUNDLE = VERIFICATION / 'sec-edgar-stage-2-k8g11etz'
INSTALLED = VERIFICATION / 'sec-edgar-wheel-1k5klfr3'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(body), 'sha256': sha(body)}


def save(name, value):
    path = SDD / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    assert str(ROOT) == '/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar'
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert head == BASE
    owner = json.loads((SDD / 'task-8-daily-endpoint-owner-answer.json').read_text())
    assert owner['answer'] == 'Yes' and owner['owner'] == 'Lowell Mason'
    assert sha((SDD / 'task-8-daily-endpoint-owner-answer.json').read_bytes()) == 'f9720b21df9f56135386496f39bb2ec4d310614410b1b5f8645fdc07a7b963ac'
    rows = json.loads((BUNDLE / 'sha256-manifest.json').read_text())
    assert len(rows) == 96
    for row in rows:
        body = (BUNDLE / row['path']).read_bytes()
        assert len(body) == row['bytes'] and sha(body) == row['sha256'], row['path']
    controller = json.loads((SDD / 'controller-task8-i1-inspection.json').read_text())
    assert controller['exit_code'] == 0 and controller['all_payload_hashes_match']
    summary = json.loads((BUNDLE / 'sequence-summary.json').read_text())
    durable = BUNDLE / 'state/.fixture-state/objects'
    result_contexts = []
    source_origins = []
    for results in (summary['quarterly_results'], summary['daily_results']):
        discover = results[0]
        body = (durable / discover['source_workset_ref']).read_bytes()
        workset = decode_source_workset(body)
        assert encode_workset(workset) == body
        assert sha(body) in discover['source_workset_ref']
        source_mapping = json.loads(body)
        source_origins.append({'ref': discover['source_workset_ref'], 'origin_context': source_mapping['context']})
        for value in results:
            context = value['context']
            assert context['command'] == ('discover' if value is discover else 'collect')
            assert context['run_id'] == discover['context']['run_id']
            assert context['config_sha256'] == discover['context']['config_sha256']
            if value is not discover:
                assert context['attempt_id'] != discover['context']['attempt_id']
                assert context['started_at'] != discover['context']['started_at']
            if value['snapshot_workset_ref']:
                frozen_body = (durable / value['snapshot_workset_ref']).read_bytes()
                frozen = decode_snapshot_workset(frozen_body)
                assert encode_workset(frozen) == frozen_body
                assert json.loads(frozen_body)['context'] == source_mapping['context']
                assert sha(frozen_body) in value['snapshot_workset_ref']
            result_contexts.append({'attempt_id': context['attempt_id'], 'execution_id': context['execution_id'],
                'started_at': context['started_at'], 'command': context['command'], 'config_sha256': context['config_sha256'],
                'source_workset_ref': value['source_workset_ref'], 'snapshot_workset_ref': value['snapshot_workset_ref']})
    state = json.loads((BUNDLE / 'final-state-records.json').read_text())
    counts = Counter(row['value']['context']['attempt_id'] for row in state['TransportAttempt'])
    assert dict(counts) == {'discover-1': 3, 'collect-1': 1, 'daily-discover-1': 4, 'daily-collect-1': 2, 'daily-collect-2': 1}
    assert counts['collect-2'] == counts['daily-collect-3'] == 0
    cursor_values = [row['value'] for row in state['FixtureResponseCursor']]
    assert len(cursor_values) == 10
    # Full cursor contents remain in the retained bundle; no writable SQLite reopening.
    import_roots = ROOT / 'packages/sec-edgar-ingest/src'
    wheel = ROOT / 'dist/sec_edgar_ingest-0.1.0-py3-none-any.whl'
    source_rows = []
    with zipfile.ZipFile(wheel) as archive:
        for path in sorted((import_roots / 'sec_edgar_ingest').rglob('*.py')):
            previous = subprocess.run(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'], capture_output=True, check=True).stdout
            body = path.read_bytes()
            assert body == previous == archive.read(path.relative_to(import_roots).as_posix())
            source_rows.append(record(path))
        assert not any(name.endswith(('network_guard.py', 'test_network_guard.py')) for name in archive.namelist())
    assert len(source_rows) == 18
    unchanged = [ROOT / name for name in ['packages/sec-edgar-ingest/README.md', 'packages/sec-edgar-ingest/pyproject.toml',
        'pyproject.toml', 'uv.lock', 'conf/sec-edgar-ingest.yaml', 'packages/sec-edgar-ingest/tests/network_guard.py',
        'packages/sec-edgar-ingest/tests/test_network_guard.py', 'scripts/check-sec-edgar-ingest.sh',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification/fixture-sequence.py']]
    for path in unchanged:
        previous = subprocess.run(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'], capture_output=True, check=True).stdout
        assert path.read_bytes() == previous, path
    artifacts = []
    for name in ['sec_edgar_ingest-0.1.0-py3-none-any.whl', 'sec_edgar_ingest-0.1.0.tar.gz']:
        path = ROOT / 'dist' / name
        assert path.read_bytes() == (INSTALLED / 'build-artifacts' / name).read_bytes()
        artifacts.append(record(path))
    check = record(SDD / 'task-8-fix2-final-check.txt')
    assert check['sha256'] == 'f8d4af430fadfec27aea03ef51e936f94652c8defd82b8c9ab9c5ca433a8809c'
    files = [path for path in BUNDLE.rglob('*') if path.is_file()]
    save('task-8-i1-proof-inspection.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT), 'source_base': BASE,
        'owner_authorization': record(SDD / 'task-8-daily-endpoint-owner-answer.json'),
        'combined_sequence_wrapper': record(SDD / 'task-8-i1-combined-sequence.txt'),
        'combined_bundle_root': BUNDLE.relative_to(ROOT).as_posix(), 'combined_bundle_file_count': len(files),
        'combined_bundle_total_bytes': sum(path.stat().st_size for path in files), 'inner_payload_records_verified': len(rows),
        'combined_manifest': record(BUNDLE / 'sha256-manifest.json'), 'combined_rootmap': record(BUNDLE / 'retention-map.json'),
        'independent_controller_inspection': record(SDD / 'controller-task8-i1-inspection.json'),
        'current_result_contexts': result_contexts, 'immutable_source_origin_contexts': source_origins,
        'snapshots_keep_source_origin_current_results_keep_collect_context': True,
        'transport_counts_by_attempt_with_zero_reuse_attempts': dict(counts) | {'collect-2': 0, 'daily-collect-3': 0},
        'final_table_counts': {name: len(rows) for name, rows in state.items()},
        'production_source_hashes': source_rows, 'all18_production_sources_equal_BASE_and_validated_wheel': True,
        'unchanged_build_guard_driver_and_check_files': [record(path) for path in unchanged],
        'artifacts': artifacts, 'artifacts_byte_identical_to_validated_fresh_install': True,
        'current_prescribed_check_log': check, 'current_check_result': '289 tests/107.544s; build/help/version/compile/diff; exit0',
        'reused_installed_summary': record(INSTALLED / 'wheel-proof-summary.json'), 'fresh_install_or_suite_rerun_needed': False,
        'no_driver_or_production_contract_change': True, 'no_network_or_auth_in_this_inspection': True,
        'pending': ['fresh scoped I1 review', 'controller final whole-branch gates'], 'all_s7_checks': 'reserved'})
    argv = [sys.executable, str(SDD / 'verify_primary.py')]
    primary = subprocess.run(argv, capture_output=True, text=True)
    save('task-8-i1-primary-preservation.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': argv, 'cwd': str(ROOT), 'stdout': primary.stdout, 'stderr': primary.stderr, 'exit_code': primary.returncode,
        'kind': 'separate read-only primary preservation; no primary or status mutation'})
    assert primary.returncode == 0
    result = json.loads(primary.stdout)
    assert result['changed_protected_files'] == result['restored_deletions'] == []
    print(json.dumps({'exit_code': 0, 'combined_files': len(files), 'combined_bytes': sum(path.stat().st_size for path in files),
        'all18_sources_and_artifacts_unchanged': True, 'primary_preservation': 'passed', 'no_rerun_needed': True}))


if __name__ == '__main__':
    main()
