"""Read-only audit of the frozen Plan 3 delivery and protected primary state."""
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests')
from network_guard import install
install()

import hashlib
import importlib.metadata
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import time
import zipfile

ROOT = Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar')
PRIMARY = Path('/Users/lowell/Projects/sec-edgar')
W = ROOT / '.sdd/3-sec-filing-index-ingestion-stage-3-spec'
EVIDENCE = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-3/verification'


def digest(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def git(root, *arguments):
    return subprocess.run(['git', *arguments], cwd=root, capture_output=True,
                          text=True, check=True).stdout.rstrip('\n')


def main():
    started = time.monotonic()
    failures = []
    preflight = json.loads((W / 'preservation-preflight/receipt.json').read_bytes())
    records = json.loads((W / 'preservation-preflight/primary-inventory.json').read_bytes())
    primary_bytes = 0
    absences = []
    for record in records:
        path = PRIMARY / record['path']
        if record.get('absent'):
            absences.append(record['path'])
            if path.exists() or path.is_symlink():
                failures.append([record['path'], 'expected absent'])
            continue
        if not path.is_file():
            failures.append([record['path'], 'missing protected file'])
            continue
        body = path.read_bytes()
        primary_bytes += len(body)
        if digest(body) != {'bytes': record['bytes'], 'sha256': record['sha256']}:
            failures.append([record['path'], 'protected bytes changed'])
    status_equal = git(PRIMARY, 'status', '--short', '--branch') == preflight['status']
    head_equal = git(PRIMARY, 'rev-parse', 'HEAD') == preflight['head']
    if not status_equal or not head_equal:
        failures.append(['primary', 'status or HEAD drift'])

    manifest_path = EVIDENCE / 'sha256.json'
    inventory = json.loads(manifest_path.read_bytes())
    for relative, expected in inventory.items():
        pure = PurePosixPath(relative)
        path = EVIDENCE / relative
        if (pure.is_absolute() or str(pure) != relative or
                any(part in ('.', '..') for part in pure.parts) or
                path.is_symlink() or not path.resolve().is_relative_to(EVIDENCE.resolve())):
            failures.append([relative, 'unsafe inventory path'])
            continue
        if digest(path.read_bytes()) != expected:
            failures.append([relative, 'evidence hash or length drift'])
    actual = {p.relative_to(EVIDENCE).as_posix() for p in EVIDENCE.rglob('*')
              if p.is_file() and p != manifest_path}
    if actual != set(inventory):
        failures.append(['inventory', {'extra': sorted(actual - set(inventory)),
                                      'missing': sorted(set(inventory) - actual)}])

    installed = json.loads((EVIDENCE / 'installed/report.json').read_bytes())
    wheel_path = EVIDENCE / 'installed' / installed['wheel_name']
    wheel_bytes = wheel_path.read_bytes()
    if digest(wheel_bytes) != installed['wheel'] or wheel_bytes != (ROOT / 'dist' / wheel_path.name).read_bytes():
        failures.append(['wheel', 'reported or built wheel mismatch'])
    with zipfile.ZipFile(wheel_path) as archive:
        for relative, expected in installed['source_equality'].items():
            body = (ROOT / 'packages/sec-edgar-ingest/src' / relative).read_bytes()
            if body != archive.read(relative) or digest(body) != expected:
                failures.append([relative, 'source/wheel/report mismatch'])
        metadata = archive.read('sec_edgar_ingest-0.1.0.dist-info/METADATA')
        if not metadata.endswith((ROOT / 'packages/sec-edgar-ingest/README.md').read_bytes()):
            failures.append(['wheel', 'package README metadata mismatch'])

    receipt = {
        'argv': sys.argv, 'cwd': str(Path.cwd()), 'executable': sys.executable,
        'python': sys.version, 'platform': platform.platform(),
        'dependencies': {name: importlib.metadata.version(name) for name in
                         ('sec-edgar-ingest', 'pyarrow', 'requests', 'azure-identity',
                          'azure-storage-blob', 'azure-data-tables')},
        'network_guard': True, 'live_access_authorizations': 'closed',
        'all22_stage7_checks': 'reserved',
        'reviewed_delivery_head': git(ROOT, 'rev-parse', 'HEAD'),
        'merge_base_main': git(ROOT, 'merge-base', 'main', 'HEAD'),
        'primary': {'records': len(records), 'existing_bytes': primary_bytes,
                    'protected_absences': absences, 'status_equal_preflight': status_equal,
                    'head_equal_preflight': head_equal},
        'evidence': {'records': len(inventory),
                     'bytes': sum(value['bytes'] for value in inventory.values()),
                     'inventory': digest(manifest_path.read_bytes()),
                     'coverage_complete': actual == set(inventory)},
        'wheel': digest(wheel_bytes), 'package_python_sources': len(installed['source_equality']),
        'failures': failures, 'exit': 1 if failures else 0,
        'runtime_seconds': time.monotonic() - started,
        'stage_3_acceptance': 'blocked by retained-source conflicting observations',
    }
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt['exit']


if __name__ == '__main__':
    raise SystemExit(main())
