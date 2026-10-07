"""Generate the final complete Stage 3 inventory after all payloads are saved."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import hashlib
import json

stage=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3'
target=stage/'completion-sha256.json'
assert not target.exists(), 'Refuse replacing an existing final inventory'
records={}
for p in sorted(stage.rglob('*')):
    if p.is_file() and p!=target:
        assert not p.is_symlink() and p.resolve().is_relative_to(stage.resolve()),str(p)
        b=p.read_bytes()
        records[p.relative_to(stage).as_posix()]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
target.write_text(json.dumps(records,indent=2,sort_keys=True)+'\n')
for relative,expected in json.loads(target.read_bytes()).items():
    b=(stage/relative).read_bytes()
    assert {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}==expected,relative
actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() and p!=target}
assert actual==set(records)
b=target.read_bytes()
print(json.dumps({'exit':0,'records':len(records),'payload_bytes':sum(r['bytes'] for r in records.values()),
    'inventory':{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},'coverage':'all other current Stage3 files; excludes only itself',
    'network_guard':True,'live_access_authorizations':'closed'},indent=2,sort_keys=True))
