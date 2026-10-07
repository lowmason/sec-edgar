"""Retain actual argv, exit, timing, stdout/stderr and hash observations."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import hashlib
import json
import os
import subprocess
import time
OUT = Path(__file__).resolve().parent
require_new = [OUT / name for name in ('command.json', 'stdout.txt', 'stderr.txt', 'report.json')]
if any(path.exists() for path in require_new):
    raise SystemExit('refuse overwriting prior verification receipts')
argv = ['uv', 'run', '--offline', '--frozen', '--python', sys.executable, 'python', str(OUT / 'verify.py'), '--output', str(OUT / 'report.json')]
environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', UV_NO_MANAGED_PYTHON='1')
started = time.perf_counter()
with (OUT / 'stdout.txt').open('wb') as stdout, (OUT / 'stderr.txt').open('wb') as stderr:
    process = subprocess.run(argv, cwd=ROOT, env=environment, stdout=stdout, stderr=stderr, timeout=60)
elapsed = time.perf_counter() - started
observations = {}
for name in ('verify.py', 'owner-amendment.json', 'historical-resolution.json', 'report.json', 'stdout.txt', 'stderr.txt'):
    path = OUT / name
    body = path.read_bytes()
    observations[name] = {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}
receipt = {'argv': argv, 'cwd': str(ROOT), 'exit': process.returncode, 'runtime_seconds': elapsed, 'network_guard_installed_in_logger_and_child': True, 'environment': {key: environment[key] for key in ('PYTHONDONTWRITEBYTECODE', 'UV_NO_MANAGED_PYTHON')}, 'files': observations}
(OUT / 'command.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
raise SystemExit(process.returncode)
