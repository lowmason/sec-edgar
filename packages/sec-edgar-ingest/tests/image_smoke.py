"""Run every sec-edgar-ingest command in the built Linux amd64 image, offline (Stage 6, D1).

Usage: image_smoke.py IMAGE

Fixture packs and the config are built on the host. Every command that touches state runs inside the
container, so the store's bound root is always the container path /work/.fixture-state.
"""
from network_guard import install
install()

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path

from support_reconcile import sha
from support_scenario import BASE_Q3, GATED_Q3, TODAY, scenario_pack, scenario_settings
from sec_edgar_ingest.models import canonical_json, to_mapping_value

COMMANDS = ('discover', 'collect', 'transform', 'publish', 'backfill', 'daily', 'reconcile',
            'approve', 'candidates', 'rollback', 'history')
# Colima shares the home directory with its VM; /tmp is not shared.
SMOKE_ROOT = Path.home() / '.cache' / 'sec-edgar-ingest-smoke'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit('image smoke failed: ' + message)


class Smoke:
    def __init__(self, image: str, work: Path):
        self.image, self.work = image, work
        self.deadline = (datetime.now(timezone.utc) + timedelta(seconds=1800)).isoformat()

    def docker(self, *args: str, entrypoint: str | None = None) -> subprocess.CompletedProcess:
        command = ['docker', 'run', '--rm', '--network', 'none', '--platform', 'linux/amd64',
                   '-v', f'{self.work}:/work']
        if entrypoint is not None:
            command += ['--entrypoint', entrypoint]
        return subprocess.run([*command, self.image, *args], capture_output=True, text=True, timeout=900)

    def expect(self, label: str, completed: subprocess.CompletedProcess, code: int) -> subprocess.CompletedProcess:
        require(completed.returncode == code, f'{label}: exit {completed.returncode}, expected {code}\n'
                                              f'{completed.stdout}\n{completed.stderr}')
        print(f'ok {label}: exit {code}')
        return completed

    def command(self, label: str, code: int, outcome: str, *argv: str) -> dict:
        message = json.loads(self.expect(label, self.docker(*argv), code).stdout)
        require(message['outcome'] == outcome, f'{label}: outcome {message["outcome"]}, expected {outcome}')
        return message

    def workflow(self, command: str, code: int, outcome: str, run: str, pack: str) -> dict:
        return self.command(command, code, outcome, command, '--config', '/work/config.json', '--run-id', run,
                            '--execution-id', 'manual', '--attempt-id', 'a', '--deadline', self.deadline,
                            '--state-dir', '/work', '--today', TODAY, '--fixture-pack', f'/work/{pack}/manifest.json')


def main(image: str) -> None:
    SMOKE_ROOT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='run-', dir=SMOKE_ROOT))
    smoke = Smoke(image, work)
    probe = smoke.expect('platform', smoke.docker(
        '-c', 'import os, platform, tempfile; print(platform.system(), platform.machine(), '
              'platform.python_version(), os.getuid(), tempfile.gettempdir())', entrypoint='python'), 0)
    require(probe.stdout.split() == ['Linux', 'x86_64', '3.14.8', '1000', '/tmp/sec-edgar-ingest'], probe.stdout)
    natives = smoke.expect('native imports', smoke.docker(
        '-c', 'import pyarrow, requests, cryptography.hazmat.bindings._rust, azure.identity, '
              'azure.storage.blob, azure.data.tables; print(pyarrow.__version__, requests.__version__)',
        entrypoint='python'), 0)
    require(natives.stdout.split() == ['25.0.1', '2.34.2'], natives.stdout)
    reported = smoke.expect('--version', smoke.docker('--version'), 0).stdout.strip()
    require(reported == version('sec-edgar-ingest'), reported)
    require(smoke.expect('--help', smoke.docker('--help'), 0).stdout.startswith('usage: sec-edgar-ingest'), '--help')
    for command in COMMANDS:
        shown = smoke.expect(f'{command} --help', smoke.docker(command, '--help'), 0).stdout
        require(shown.startswith(f'usage: sec-edgar-ingest {command}'), shown)

    for name, q3 in (('pack-1', BASE_Q3), ('pack-2', GATED_Q3)):
        scenario_pack(work, name, q3)
    (work / 'config.json').write_bytes(canonical_json(to_mapping_value(scenario_settings().to_mapping())))
    for path in (work, *work.rglob('*')):
        path.chmod(0o777 if path.is_dir() else 0o644)
    smoke.workflow('backfill', 0, 'success', 'base', 'pack-1')
    smoke.workflow('daily', 0, 'no_new_sources', 'day', 'pack-1')
    smoke.workflow('reconcile', 10, 'awaiting_approval', 'gate', 'pack-2')
    operator = ('--config', '/work/config.json', '--state-dir', '/work')
    request, = smoke.command('candidates', 0, 'success', 'candidates', *operator)['candidates']
    require(request['status'] == 'pending', str(request['status']))
    approved = smoke.command('approve', 0, 'success', 'approve', *operator, '--quarter', '2026Q3',
                             '--generation', request['generation_id'], '--quarterly-sha256', sha(GATED_Q3),
                             '--approver', 'Image Smoke')
    require(approved['activation_ref'] is not None, 'approve printed no activation_ref')
    history = smoke.command('history', 0, 'success', 'history', *operator, '--quarter', '2026Q3')
    lineage = history['lineage']
    require([entry['gate'] for entry in lineage] == ['awaiting_approval', 'clear'], str(lineage))
    require(len(history['activations']) == 1, str(history['activations']))
    smoke.command('rollback', 0, 'success', 'rollback', *operator, '--quarter', '2026Q3',
                  '--from-generation', lineage[0]['generation_id'], '--to-generation', lineage[1]['generation_id'],
                  '--operator', 'Image Smoke', '--reason', 'image smoke')
    history = smoke.command('history after rollback', 0, 'success', 'history', *operator, '--quarter', '2026Q3')
    require(len(history['rollbacks']) == 1, str(history['rollbacks']))
    shutil.rmtree(work)
    print(f'image smoke passed: {image}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: image_smoke.py IMAGE')
    main(sys.argv[1])
