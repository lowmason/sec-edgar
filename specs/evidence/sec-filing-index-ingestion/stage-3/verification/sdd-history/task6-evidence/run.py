import sys
from pathlib import Path
root = Path.cwd()
sys.path.insert(0, str(root / 'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import json
import os
import subprocess
name, *tests = sys.argv[1:]
evidence = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec/task6-evidence'
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'SEC_EDGAR_TASK6_PROOF_DIR': str(evidence / (name + '-proof'))}
argv = ['uv', 'run', '--offline', '--frozen', 'python', 'packages/sec-edgar-ingest/tests/network_guard.py', *tests, '-v']
result = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True)
record = {'argv': argv, 'cwd': str(root), 'env': {key: env.get(key) for key in ('PATH', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'SEC_EDGAR_TASK6_PROOF_DIR')}, 'stdout': result.stdout, 'stderr': result.stderr, 'exit': result.returncode}
(evidence / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print(result.stdout, result.stderr, sep='\n')
raise SystemExit(result.returncode)
