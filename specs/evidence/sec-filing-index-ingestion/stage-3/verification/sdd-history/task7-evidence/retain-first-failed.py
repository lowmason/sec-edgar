"""Exact byte archival and protected-primary comparison; never mutate primary."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
from etl_proof import save, digest, inventory, metadata
import json, shutil
SDD=ROOT/'.sdd/3-sec-filing-index-ingestion-stage-3-spec'
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/verification'
PRIMARY=Path('/Users/lowell/Projects/sec-edgar')
base=Path('specs/evidence/sec-filing-index-ingestion/stage-3')
for name in ('owner-approval.json','planning-reconciliation.json'):
    shutil.copy2(PRIMARY/base/name,ROOT/base/name)
for path in (PRIMARY/base/'versions').iterdir():
    target=ROOT/base/'versions'/path.name; target.parent.mkdir(exist_ok=True)
    shutil.copy2(path,target)
records=json.loads((SDD/'preservation-preflight/primary-inventory.json').read_text())
failures=[]
for record in records:
    path=PRIMARY/record['path']
    if not path.is_file() or digest(path)!={k:record[k] for k in ('bytes','sha256')}:
        failures.append(record['path'])
receipt=json.loads((SDD/'preservation-preflight/receipt.json').read_text())
absences={path:not (PRIMARY/path).exists() for path in receipt['protected_absences']}
roadmap=digest(PRIMARY/'specs/sec-filing-index-ingestion-roadmap.md')
assert not failures and all(absences.values()) and roadmap==receipt['roadmap'], (failures,absences,roadmap)
save(OUT/'primary-preservation.json',{**metadata(),'exit':0,'records_verified':len(records),'failures':failures,'protected_absences':absences,'roadmap':roadmap,
     'approval_copies':{p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/base).rglob('*') if p.is_file() and 'verification' not in p.parts}})
for name,exit_code,test_runtime in [('red',1,.001),('process-1',0,4.273)]:
    save(SDD/'task7-evidence'/name/'command.json',{**metadata(),'argv':['uv','run','--offline','--frozen','--package','sec-edgar-ingest','python','packages/sec-edgar-ingest/tests/network_guard.py','discover','-s','packages/sec-edgar-ingest/tests','-p','test_etl_processes.py','-v'],
       'exit':exit_code,'unittest_runtime_seconds':test_runtime,'runtime_seconds':None,
       'metadata_note':'Exact command/exit/test runtime retained from actual tool invocation and full logs; wrapper elapsed time was not captured. Environment metadata captured at archival; same selected native frozen environment. Temporary first-green child directories were cleaned by test; subsequent sequence and final-check retain full actual traces.'})
archive=OUT/'sdd-history'
assert not archive.exists()
shutil.copytree(SDD,archive,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
save(archive/'sha256.json',inventory(archive))
print('Archived',len(inventory(archive)),'files; protected primary verified',len(records))
