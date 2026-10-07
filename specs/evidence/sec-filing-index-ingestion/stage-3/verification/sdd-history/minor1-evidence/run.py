import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import json
import subprocess
command = ['uv', 'run', '--offline', '--frozen', 'python', 'packages/sec-edgar-ingest/tests/network_guard.py', 'test_etl_publication', '-v']
result = subprocess.run(command, capture_output=True, text=True)
path = Path('.sdd/3-sec-filing-index-ingestion-stage-3-spec/minor1-evidence/green-publication.json')
with path.open('x') as stream:
    json.dump(dict(argv=command, cwd=str(Path.cwd()), stdout=result.stdout, stderr=result.stderr, exit=result.returncode), stream, indent=2)
print(result.stdout)
print(result.stderr)
raise SystemExit(result.returncode)
