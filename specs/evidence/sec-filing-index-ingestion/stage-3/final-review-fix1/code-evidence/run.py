import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
label = sys.argv[1]
target = evidence / label
target.mkdir(exist_ok=False)
env = dict(os.environ, SEC_EDGAR_TASK6_PROOF_DIR=str(target / 'proof'))
argv = ['uv', 'run', '--offline', '--frozen', 'python',
        'packages/sec-edgar-ingest/tests/network_guard.py', *sys.argv[2:], '-v']
started = time.time()
completed = subprocess.run(argv, cwd=root, env=env, capture_output=True, timeout=180)
(target / 'stdout.txt').write_bytes(completed.stdout)
(target / 'stderr.txt').write_bytes(completed.stderr)
metadata = {'argv': argv, 'cwd': str(root), 'env': {'SEC_EDGAR_TASK6_PROOF_DIR': env['SEC_EDGAR_TASK6_PROOF_DIR']},
            'started_at_unix': started, 'duration_seconds': time.time() - started, 'exit_code': completed.returncode}
(target / 'command.json').write_text(json.dumps(metadata, indent=2) + '\n')
records = {path.relative_to(target).as_posix(): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'bytes': path.stat().st_size} for path in target.rglob('*') if path.is_file()}
(target / 'inventory.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps(metadata, indent=2))
sys.stdout.buffer.write(completed.stdout)
sys.stderr.buffer.write(completed.stderr)
sys.exit(completed.returncode)
