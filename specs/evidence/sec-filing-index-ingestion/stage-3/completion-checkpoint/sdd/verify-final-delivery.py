"""Read-only final audit, run after every metadata payload and inventory is saved."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path, PurePosixPath
ROOT = Path.cwd()
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import hashlib
import json
import platform
import subprocess
import time

stage=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3'
primary=Path('/Users/lowell/Projects/sec-edgar')
started=time.monotonic()
def digest(path):
    b=path.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def git(where,*args):
    return subprocess.run(['git',*args],cwd=where,capture_output=True,text=True,check=True).stdout.rstrip('\n')
m=stage/'completion-sha256.json'
records=json.loads(m.read_bytes())
for relative,expected in records.items():
    pure=PurePosixPath(relative)
    p=stage/relative
    assert not pure.is_absolute() and str(pure)==relative and not any(x in ('.','..') for x in pure.parts),relative
    assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(stage.resolve()),relative
    assert digest(p)==expected,relative
actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file() and p!=m}
assert actual==set(records),{'extra':sorted(actual-set(records)),'missing':sorted(set(records)-actual)}
pre=json.loads((stage/'verification/sdd-history/preservation-preflight/receipt.json').read_bytes())
protected=json.loads((stage/'verification/sdd-history/preservation-preflight/primary-inventory.json').read_bytes())
for r in protected:
    p=primary/r['path']
    if r.get('absent'):
        assert not p.exists() and not p.is_symlink(),r['path']
    else:
        assert digest(p)=={'bytes':r['bytes'],'sha256':r['sha256']},r['path']
assert git(primary,'rev-parse','HEAD')==pre['head']
assert git(primary,'status','--short','--branch')==pre['status']
domains=['packages/sec-edgar-ingest','conf','tests','fixtures','scripts','README.md','pyproject.toml','uv.lock','.python-version']
unchanged=subprocess.run(['git','diff','--quiet','2343f39f0e21adc2ad401a9346a8c9ffa0509040','--',*domains],cwd=ROOT,capture_output=True)
assert unchanged.returncode==0
receipt=json.loads((stage/'completion-checkpoint/completion-receipt.json').read_bytes())
assert receipt['status']=='COMPLETE' and not receipt['deferred_items'] and not receipt['open_review_findings']
for key in ['plan','spec']:
    r=receipt['retirement'][key]
    assert digest(ROOT/r['to'])=={'bytes':r['bytes'],'sha256':r['sha256']}
assert receipt['completion_review']['spec']=='PASS' and receipt['completion_review']['quality']=='Approved'
review=stage/receipt['completion_review']['path']
assert digest(review)=={'bytes':receipt['completion_review']['bytes'],'sha256':receipt['completion_review']['sha256']}
assert not git(ROOT,'status','--porcelain','--untracked-files=normal'), 'Tracked/untracked worktree not clean'
result={'schema':'sec-stage3-final-delivery-audit-v1','exit':0,'failures':[],'network_guard':True,
 'head':git(ROOT,'rev-parse','HEAD'),'branch':git(ROOT,'branch','--show-current'),'worktree_clean':True,
 'payload_records':len(records),'payload_bytes':sum(r['bytes'] for r in records.values()),'inventory':digest(m),
 'coverage_complete':True,'primary_records':len(protected),'primary_existing_bytes':sum(r.get('bytes',0) for r in protected),
 'primary_status_head_and_bytes_unchanged':True,'reviewed_implementation_unchanged':True,
 'quarantine_acceptance':'approved exact exceptions; strict refusal unchanged','all22_stage7_checks':'reserved',
 'live_access_authorizations':'closed','python':sys.version,'platform':platform.platform(),
 'runtime_seconds':time.monotonic()-started}
print(json.dumps(result,indent=2,sort_keys=True))
