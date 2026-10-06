"""Retain the authorized quarterly proof and prepare the pending daily alternative.

The optional daily switch is for use only after the owner approves separate configs.
Its presence does not constitute that approval. Default execution retains the exact
closed-quarter daily refusal and leaves the prescribed combined Step 4 gate pending.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.models import CommandResult
from sec_edgar_ingest.storage.local import LocalStateStore

REPOSITORY = Path(__file__).resolve().parents[5]
VERIFICATION = Path(__file__).resolve().parent
PACK = REPOSITORY / 'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json'
PREFIX = ['uv', 'run', '--offline', '--frozen', '--package', 'sec-edgar-ingest', 'sec-edgar-ingest']


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def inspect_state(root: Path) -> dict:
    store = LocalStateStore(root)
    try:
        return {kind: [row.to_mapping() for row in store.scan(kind, {})]
                for kind in ('Binding', 'TransportAttempt', 'Attempt', 'FixtureResponseCursor')}
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-approved-daily', action='store_true')
    options = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='sec-edgar-stage-2-') as temporary:
        root = Path(temporary)
        config = json.loads((REPOSITORY / 'conf/sec-edgar-ingest.yaml').read_text())
        config['backfill'] = {'start_quarter': '2015Q1', 'end_quarter': '2015Q1'}
        literal = {**config, 'storage': {**config['storage'], 'root': str(root / 'state')}}
        literal_path = root / 'literal-config.json'
        save_json(literal_path, literal)
        config['fixture'] = {'allow_clock_override': True, 'allow_deadline_override': True}
        config['storage']['root'] = '.fixture-state'
        quarterly_path = root / 'quarterly-config.json'
        save_json(quarterly_path, config)
        daily = {**config, 'backfill': {**config['backfill'], 'end_quarter': 'open'}}
        daily_path = root / 'proposed-daily-config.json'
        save_json(daily_path, daily)
        state_base = root / 'state'
        state_root = state_base / config['storage']['root']
        common = ['--config', str(quarterly_path), '--fixture-pack', str(PACK),
                  '--state-dir', str(state_base), '--deadline', '2099-01-01T00:00:00Z']
        quarter_args = ['--today', '2026-10-06', '--mode', 'quarterly', '--discovery-id', 'fixture-quarter',
                        '--run-id', 'fixture-run', '--execution-id', 'fixture-discover', '--attempt-id', 'discover-1']
        daily_args = ['--today', '2026-10-06', '--mode', 'daily', '--discovery-id', 'fixture-daily',
                      '--run-id', 'fixture-daily', '--execution-id', 'fixture-daily-discover', '--attempt-id', 'daily-discover-1']
        calls = []
        summary = {'provenance': 'synthetic', 'scope': 'one archived quarter fixture subset',
                   'prescribed_step_4': 'pending owner daily endpoint decision',
                   'driver_corrections': ['relative configured storage.root with explicit absolute --state-dir base',
                                          'explicit fixture clock/deadline override markers'],
                   'config_sha256': {'quarterly': Settings.from_mapping(config).config_sha256,
                                     'proposed_daily': Settings.from_mapping(daily).config_sha256}}

        def invoke(command, arguments, expected, *, config_path=None, label=None, extras=None):
            selected = list(common)
            if config_path is not None:
                selected[selected.index('--config') + 1] = str(config_path)
            argv = PREFIX + [command] + selected + arguments
            if extras is not None:
                argv = PREFIX + [command] + extras + arguments
            completed = subprocess.run(argv, cwd=REPOSITORY, capture_output=True, text=True, timeout=120)
            label = label or arguments[arguments.index('--attempt-id') + 1]
            save_json(root / (label + '.argv.json'), argv)
            (root / (label + '.stdout')).write_text(completed.stdout)
            (root / (label + '.stderr')).write_text(completed.stderr)
            save_json(root / (label + '.exit.json'), {'exit': completed.returncode, 'expected': expected})
            calls.append({'label': label, 'argv': argv, 'exit': completed.returncode})
            assert completed.returncode == expected, completed.stderr
            return json.loads(completed.stdout) if completed.stdout else None

        def result(output):
            return CommandResult.from_json((state_root / 'objects' / output['result_ref']).read_bytes())

        try:
            literal_common = ['--config', str(literal_path), '--fixture-pack', str(PACK),
                              '--deadline', '2099-01-01T00:00:00Z']
            invoke('discover', quarter_args, 2, extras=literal_common, label='literal-absolute-root-refusal')
            discovered = invoke('discover', quarter_args, 0)
            collect_args = ['--workset', discovered['source_workset_ref'], '--run-id', 'fixture-run',
                            '--execution-id', 'fixture-collect', '--attempt-id', 'collect-1']
            first = invoke('collect', collect_args, 0)
            before = inspect_state(state_root)
            second = invoke('collect', ['--workset', discovered['source_workset_ref'], '--run-id', 'fixture-run',
                                        '--execution-id', 'fixture-collect-retry', '--attempt-id', 'collect-2'], 0)
            replay = invoke('collect', collect_args, 0, label='collect-1-exact-replay')
            after = inspect_state(state_root)
            assert replay == first
            assert second['snapshot_workset_ref'] == first['snapshot_workset_ref']
            assert after['Binding'] == before['Binding']
            assert after['TransportAttempt'] == before['TransportAttempt']
            assert (result(first).downloaded, result(second).unchanged) == (1, 1)
            invoke('discover', daily_args, 2, label='closed-quarter-daily-refusal')
            save_json(root / 'prepared-two-config-commands.json', {
                'approval_required': 'owner selection of separate daily end=open config',
                'driver_after_approval': PREFIX[:-1] + ['python', str(Path(__file__).resolve()), '--include-approved-daily'],
                'proposed_daily_discovery_argv': PREFIX + ['discover'] +
                    [str(daily_path) if item == str(quarterly_path) else item for item in common] + daily_args})
            summary['quarterly_results'] = [result(output).to_mapping() for output in (discovered, first, second)]
            summary['quarterly_no_http_replay'] = True
            if options.include_approved_daily:
                daily_discovered = invoke('discover', daily_args, 0, config_path=daily_path)
                source = daily_discovered['source_workset_ref']
                pending_args = ['--workset', source, '--run-id', 'fixture-daily',
                                '--execution-id', 'fixture-daily-collect', '--attempt-id', 'daily-collect-1']
                pending = invoke('collect', pending_args, 3, config_path=daily_path)
                assert pending['outcome'] == 'incomplete'
                pinned = inspect_state(state_root)
                exact = invoke('collect', pending_args, 3, config_path=daily_path, label='daily-collect-1-replay')
                assert exact == pending
                assert inspect_state(state_root)['TransportAttempt'] == pinned['TransportAttempt']
                recovered = invoke('collect', ['--workset', source, '--run-id', 'fixture-daily',
                    '--execution-id', 'fixture-daily-retry', '--attempt-id', 'daily-collect-2'], 0, config_path=daily_path)
                complete = inspect_state(state_root)
                assert all(pin in complete['Binding'] for pin in pinned['Binding'])
                assert len(complete['TransportAttempt']) == len(pinned['TransportAttempt']) + 1
                assert recovered['snapshot_workset_ref'] is not None
                final = invoke('collect', ['--workset', source, '--run-id', 'fixture-daily',
                    '--execution-id', 'fixture-daily-offline', '--attempt-id', 'daily-collect-3'], 0, config_path=daily_path)
                assert final['snapshot_workset_ref'] == recovered['snapshot_workset_ref']
                assert inspect_state(state_root)['TransportAttempt'] == complete['TransportAttempt']
                summary['daily_results'] = [result(output).to_mapping() for output in (daily_discovered, pending, recovered, final)]
                summary['prescribed_step_4'] = 'executed with explicitly approved separate configs'
            save_json(root / 'final-state-records.json', inspect_state(state_root))
            print(json.dumps({'quarterly': 'passed', 'prescribed_step_4': summary['prescribed_step_4'], 'original_root': str(root)}))
        finally:
            save_json(root / 'calls.json', calls)
            save_json(root / 'sequence-summary.json', summary)
            retained = VERIFICATION / root.name
            shutil.copytree(root, retained)
            save_json(retained / 'retention-map.json', {'original_root': str(root), 'retained_root': str(retained),
                'configured_relative_root': config['storage']['root'], 'state_dir_base': str(state_base),
                'original_durable_root': str(state_root), 'retained_durable_root': str(retained / 'state' / config['storage']['root'])})
            save_json(retained / 'sha256-manifest.json', [{'path': str(path.relative_to(retained)),
                'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                for path in sorted(retained.rglob('*')) if path.is_file() and path.name != 'sha256-manifest.json'])


if __name__ == '__main__':
    main()
