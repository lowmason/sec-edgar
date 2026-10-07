from pathlib import Path
import hashlib, json, subprocess
root = Path('/Users/lowell/Projects/sec-edgar')
baseline = json.loads((Path(__file__).parent / 'preflight/baseline.json').read_text())
changed = []
for name, record in baseline['files'].items():
    current = root / name
    if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != record['sha256']:
        changed.append(name)
deleted = ['packages/sec-edgar-index-ingest/README.md', 'packages/sec-edgar-index-ingest/pyproject.toml', 'packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py', 'packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed']
restored = [name for name in deleted if (root / name).exists()]
status = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain=v1']).decode()
print(json.dumps({'changed_protected_files': changed, 'restored_deletions': restored, 'primary_status': status}, indent=2))
assert not changed and not restored
