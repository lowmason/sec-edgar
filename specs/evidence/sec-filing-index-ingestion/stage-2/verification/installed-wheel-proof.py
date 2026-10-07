"""Build-artifact inspection and a fresh, pinned, offline wheel CLI proof."""
from __future__ import annotations

import email
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[5]
VERIFICATION = Path(__file__).resolve().parent
WHEELS = REPOSITORY / '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task1-evidence/wheels'
PACK = REPOSITORY / 'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json'


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def fingerprint(path):
    body = path.read_bytes()
    return {'path': str(path), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def inspect_artifacts(root):
    wheel = REPOSITORY / 'dist/sec_edgar_ingest-0.1.0-py3-none-any.whl'
    sdist = REPOSITORY / 'dist/sec_edgar_ingest-0.1.0.tar.gz'
    artifacts = root / 'build-artifacts'
    artifacts.mkdir()
    for path in (wheel, sdist):
        shutil.copy2(path, artifacts / path.name)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata = archive.read('sec_edgar_ingest-0.1.0.dist-info/METADATA')
        entrypoints = archive.read('sec_edgar_ingest-0.1.0.dist-info/entry_points.txt')
    with tarfile.open(sdist) as archive:
        members = archive.getnames()
        pkg_info = archive.extractfile('sec_edgar_ingest-0.1.0/PKG-INFO').read()
    for raw in (metadata, pkg_info):
        parsed = email.message_from_bytes(raw)
        assert parsed['Name'] == 'sec-edgar-ingest'
        assert parsed['Version'] == '0.1.0'
        assert parsed['Requires-Python'] == '>=3.14'
        assert set(parsed.get_all('Requires-Dist')) == {
            'requests==2.34.2', 'azure-identity==1.26.0', 'azure-storage-blob==12.31.0', 'azure-data-tables==12.7.0'}
    assert 'sec_edgar_ingest/results.py' in names
    assert 'sec_edgar_ingest-0.1.0/src/sec_edgar_ingest/results.py' in members
    assert b'sec-edgar-ingest = sec_edgar_ingest.cli:main' in entrypoints
    assert not any('sec_edgar_client/' in name or 'sec_edgar_download/' in name or 'sec_edgar_index_ingest/' in name for name in names)
    (root / 'wheel-METADATA').write_bytes(metadata)
    (root / 'sdist-PKG-INFO').write_bytes(pkg_info)
    (root / 'wheel-entry_points.txt').write_bytes(entrypoints)
    receipt = {'artifacts': [fingerprint(path) for path in (wheel, sdist)], 'wheel_members': names,
               'sdist_members': members, 'metadata_assertions': 'passed'}
    save_json(root / 'artifact-inspection.json', receipt)
    return wheel


def transport_count(state_root):
    with sqlite3.connect('file:' + str(state_root / 'state.sqlite3') + '?mode=ro', uri=True) as connection:
        return connection.execute("SELECT COUNT(*) FROM records WHERE partition='sec-owner-lowell-mason:TransportAttempt'").fetchone()[0]


def main():
    with tempfile.TemporaryDirectory(prefix='sec-edgar-wheel-') as temporary:
        root = Path(temporary)
        environment = root / 'fresh-env'
        commands = []
        summary = {'platform': platform.platform(), 'provenance': 'synthetic local fixture subset',
                   'dependency_authority': 'Task 1 cached pins only; offline/no-index; no lock changes',
                   'prescribed_step_4': 'not discharged by the independent installed-quarter fixture'}
        env = dict(os.environ)
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)

        def run(label, argv, *, cwd=root):
            completed = subprocess.run([str(item) for item in argv], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)
            save_json(root / (label + '.argv.json'), [str(item) for item in argv])
            (root / (label + '.stdout')).write_text(completed.stdout)
            (root / (label + '.stderr')).write_text(completed.stderr)
            save_json(root / (label + '.exit.json'), {'exit': completed.returncode, 'cwd': str(cwd)})
            commands.append({'label': label, 'argv': [str(item) for item in argv], 'exit': completed.returncode})
            assert completed.returncode == 0, completed.stderr
            return completed.stdout

        try:
            wheel = inspect_artifacts(root)
            requirements = root / 'pinned-requirements.txt'
            run('locked-export', ['uv', 'export', '--offline', '--frozen', '--no-dev', '--no-emit-workspace', '--output-file', requirements], cwd=REPOSITORY)
            run('fresh-environment', [REPOSITORY / '.venv/bin/python', '-m', 'venv', '--without-pip', environment])
            python = environment / 'bin/python'
            run('cached-pinned-install', ['uv', 'pip', 'install', '--offline', '--no-index', '--find-links', WHEELS,
                '--python', python, '--require-hashes', '-r', requirements])
            run('wheel-install', ['uv', 'pip', 'install', '--offline', '--no-index', '--no-deps', '--python', python, wheel])
            probe = """import importlib.metadata as m, json, platform, sys
import sec_edgar_ingest, sec_edgar_ingest.cli
print(json.dumps({'python': sys.version, 'platform': platform.platform(), 'prefix': sys.prefix,
'package_file': sec_edgar_ingest.__file__, 'cli_file': sec_edgar_ingest.cli.__file__,
'version': sec_edgar_ingest.__version__, 'versions': {dist.metadata['Name']: dist.version for dist in m.distributions()}}))
"""
            imported = json.loads(run('installed-import', [python, '-c', probe]))
            assert Path(imported['package_file']).is_relative_to(environment / 'lib')
            assert 'site-packages' in imported['package_file'] and 'site-packages' in imported['cli_file']
            assert imported['version'] == '0.1.0'
            pins = tomllib.loads((REPOSITORY / 'pyproject.toml').read_text())['tool']['uv']['constraint-dependencies']
            normalize = lambda name: name.lower().replace('_', '-').replace('.', '-')
            expected = {normalize(pin.split('==')[0]): pin.split('==')[1] for pin in pins}
            actual = {normalize(name): version for name, version in imported['versions'].items()}
            assert len(expected) == 20
            assert all(actual[name] == version for name, version in expected.items())
            assert set(actual) == set(expected) | {'sec-edgar-ingest'}
            save_json(root / 'installed-versions.json', imported)
            console = environment / 'bin/sec-edgar-ingest'
            run('installed-help', [console, '--help'])
            run('installed-version', [python, '-m', 'sec_edgar_ingest', '--version'])
            config = json.loads((REPOSITORY / 'conf/sec-edgar-ingest.yaml').read_text())
            config['backfill'] = {'start_quarter': '2015Q1', 'end_quarter': '2015Q1'}
            config['fixture'] = {'allow_clock_override': True, 'allow_deadline_override': True}
            config['storage']['root'] = '.fixture-state'
            path = root / 'wheel-fixture-config.json'
            save_json(path, config)
            state_base = root / 'state'
            state_root = state_base / '.fixture-state'
            common = ['--config', path, '--fixture-pack', PACK, '--state-dir', state_base,
                      '--deadline', '2099-01-01T00:00:00Z', '--today', '2026-10-06']
            discovered = json.loads(run('installed-discover', [console, 'discover', *common, '--mode', 'quarterly',
                '--discovery-id', 'wheel-quarter', '--run-id', 'wheel-run', '--execution-id', 'wheel-discover', '--attempt-id', 'discover-1']))
            collect = [console, 'collect', *common, '--workset', discovered['source_workset_ref'], '--run-id', 'wheel-run',
                       '--execution-id', 'wheel-collect', '--attempt-id', 'collect-1']
            first = json.loads(run('installed-collect', collect))
            before = transport_count(state_root)
            assert before == 4, 'three directory requests plus the original archive must be audited'
            replay = json.loads(run('installed-exact-replay', collect))
            second = json.loads(run('installed-pinned-replay', [console, 'collect', *common, '--workset', discovered['source_workset_ref'],
                '--run-id', 'wheel-run', '--execution-id', 'wheel-retry', '--attempt-id', 'collect-2']))
            assert first == replay
            assert first['snapshot_workset_ref'] == second['snapshot_workset_ref']
            assert transport_count(state_root) == before
            results = [json.loads((state_root / 'objects' / output['result_ref']).read_text()) for output in (discovered, first, second)]
            assert all(item['outcome'] == 'success' for item in results)
            assert (results[1]['downloaded'], results[2]['unchanged']) == (1, 1)
            snapshot = json.loads((state_root / 'objects' / first['snapshot_workset_ref']).read_text())
            for item in snapshot['snapshots']:
                body = (state_root / 'objects' / item['raw_path']).read_bytes()
                assert hashlib.sha256(body).hexdigest() == item['sha256']
                assert len(body) == item['byte_count']
            summary.update(installed_import=imported, installed_results=results, snapshot_workset=snapshot,
                           exact_replay_no_http=True, transport_count=before,
                           tested_entrypoint=str(console), tested_cwd=str(root))
            print(json.dumps({'installed_import': imported['package_file'], 'versions': len(expected),
                              'fixture_commands': 'passed', 'transport_count': before, 'original_root': str(root)}))
        finally:
            save_json(root / 'commands.json', commands)
            save_json(root / 'wheel-proof-summary.json', summary)
            retained = VERIFICATION / root.name
            # The generated environment is disposable. Retain import/entrypoint paths, pins,
            # logs, exact installed wheel/sdist, fixture config, state, originals and results.
            shutil.copytree(root, retained, ignore=shutil.ignore_patterns('fresh-env'))
            save_json(retained / 'retention-map.json', {'original_root': str(root), 'retained_root': str(retained),
                'exclusions': [{'path': 'fresh-env', 'reason': 'temporary installed environment; artifact bytes, lock export, import receipts, pins and command logs retained'}]})
            save_json(retained / 'sha256-manifest.json', [{'path': str(path.relative_to(retained)), 'bytes': path.stat().st_size,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in sorted(retained.rglob('*'))
                if path.is_file() and path.name != 'sha256-manifest.json'])


if __name__ == '__main__':
    main()
