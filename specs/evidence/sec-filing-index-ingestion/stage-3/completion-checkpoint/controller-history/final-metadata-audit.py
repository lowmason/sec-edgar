"""Guarded read-only verification of checkpoint payloads and commit ownership."""
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar/packages/sec-edgar-ingest/tests')
from network_guard import install
install()
import hashlib
import json
from pathlib import Path, PurePosixPath
import platform
import subprocess
import time

root = Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-3/sec-edgar')
primary = Path('/Users/lowell/Projects/sec-edgar')
w = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec'
stage = root / 'specs/evidence/sec-filing-index-ingestion/stage-3'
started = time.monotonic()
failures = []

def digest(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}

def git(where, *args):
    return subprocess.run(['git', *args], cwd=where, capture_output=True, text=True, check=True).stdout.rstrip('\n')

manifest_path = stage / 'delivery-sha256.json'
records = json.loads(manifest_path.read_bytes())
for relative, expected in records.items():
    pure = PurePosixPath(relative)
    path = stage / relative
    if (pure.is_absolute() or str(pure) != relative or any(p in ('.', '..') for p in pure.parts)
            or path.is_symlink() or not path.resolve().is_relative_to(stage.resolve())):
        failures.append([relative, 'unsafe inventory path'])
        continue
    if not path.is_file() or digest(path.read_bytes()) != expected:
        failures.append([relative, 'delivery hash/length mismatch'])
actual = {p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() and p != manifest_path}
if actual != set(records):
    failures.append(['coverage', {'extra': sorted(actual-set(records)), 'missing': sorted(set(records)-actual)}])

preflight = json.loads((w/'preservation-preflight/receipt.json').read_bytes())
primary_status_equal = git(primary, 'status', '--short', '--branch') == preflight['status']
primary_head_equal = git(primary, 'rev-parse', 'HEAD') == preflight['head']
if not primary_status_equal or not primary_head_equal:
    failures.append(['primary', 'status/HEAD drift'])
protected = json.loads((w/'preservation-preflight/primary-inventory.json').read_bytes())
roadmap_record = next(r for r in protected if r['path'] == 'specs/sec-filing-index-ingestion-roadmap.md')
if digest((primary/roadmap_record['path']).read_bytes()) != {'bytes':roadmap_record['bytes'], 'sha256':roadmap_record['sha256']}:
    failures.append(['roadmap', 'protected bytes changed'])
absences = [r['path'] for r in protected if r.get('absent')]
if any((primary/p).exists() or (primary/p).is_symlink() for p in absences):
    failures.append(['primary', 'protected absence changed'])

staged = git(root, 'diff', '--cached', '--name-only').splitlines()
prefix = 'specs/evidence/sec-filing-index-ingestion/stage-3/review-checkpoint/'
owned_manifest = 'specs/evidence/sec-filing-index-ingestion/stage-3/delivery-sha256.json'
if not staged or any(not(p.startswith(prefix) or p == owned_manifest) for p in staged):
    failures.append(['staged paths', staged])
source_check = subprocess.run(['git','diff','--quiet','2343f39f0e21adc2ad401a9346a8c9ffa0509040','--',
    'packages/sec-edgar-ingest/src','packages/sec-edgar-ingest/tests','packages/sec-edgar-ingest/README.md',
    'README.md','conf','docs'],cwd=root,capture_output=True)
if source_check.returncode != 0:
    failures.append(['reviewed source/docs', source_check.returncode])
receipt = {'network_guard':True, 'live_access_authorizations':'closed', 'python':sys.version,
    'platform':platform.platform(), 'reviewed_proof_head':git(root,'rev-parse','HEAD'),
    'delivery_records':len(records), 'delivery_bytes':sum(r['bytes'] for r in records.values()),
    'delivery_inventory':digest(manifest_path.read_bytes()), 'coverage_complete':actual == set(records),
    'primary_status_equal':primary_status_equal, 'primary_head_equal':primary_head_equal,
    'protected_absences':absences, 'roadmap':digest((primary/roadmap_record['path']).read_bytes()),
    'staged_paths':staged, 'source_docs_equal_reviewed_code_head':source_check.returncode == 0,
    'failures':failures, 'exit':1 if failures else 0, 'runtime_seconds':time.monotonic()-started}
(w/'controller-verification/final-metadata-audit.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True))
raise SystemExit(receipt['exit'])
