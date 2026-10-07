import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import json
import os
import subprocess
name, *modules = sys.argv[1:]
command = ['uv', 'run', '--offline', '--frozen', 'python', 'packages/sec-edgar-ingest/tests/network_guard.py', *modules, '-v']
result = subprocess.run(command, capture_output=True, text=True)
path = Path('.sdd/3-sec-filing-index-ingestion-stage-3-spec/task5-evidence') / (name + '.json')
with path.open('x') as stream:
    json.dump(dict(argv=command, cwd=str(Path.cwd()), env={key: value for key, value in os.environ.items() if key.startswith('SEC_EDGAR_TASK5_')}, stdout=result.stdout, stderr=result.stderr, exit=result.returncode), stream, indent=2)
print(result.stdout)
print(result.stderr)
raise SystemExit(result.returncode)
