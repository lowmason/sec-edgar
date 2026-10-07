"""Read-only proof audit; writes its result only in the new sibling root."""
import hashlib, json, subprocess, zipfile
from pathlib import Path
ROOT=Path.cwd()
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/final-review-fix1'
def digest(path):
    body=path.read_bytes(); return {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
def verify(root):
    values=json.loads((root/'sha256.json').read_text())
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'sha256.json'}
    assert actual==set(values), (root,actual ^ set(values))
    for name,value in values.items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert digest(root/name)==value, name
    return {'records':len(values),'bytes':sum(v['bytes'] for v in values.values()),'inventory':digest(root/'sha256.json')}
frozen=verify(OUT.parent/'verification')
assert frozen['records']==7525
assert frozen['inventory']['sha256']=='4554adb90acdda3e44bffac01bb878d3391d4ae523e0c4439aa4e1ab2c612b6b'
checks={name:verify(OUT/name) for name in ('runbook','sequence','installed')}
report=json.loads((OUT/'installed/report.json').read_text())
wheel=ROOT/'dist'/report['wheel_name']
assert digest(wheel)==report['wheel']==digest(OUT/'installed'/wheel.name)
with zipfile.ZipFile(wheel) as archive:
    for path,value in report['source_equality'].items():
        body=archive.read(path)
        assert {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}==value==digest(ROOT/'packages/sec-edgar-ingest/src'/path)
    metadata=archive.read(next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))).decode()
    assert (ROOT/'packages/sec-edgar-ingest/README.md').read_text().strip() in metadata
copies={}
for kind in ('code','doc'):
    source=ROOT/f'.sdd/3-sec-filing-index-ingestion-stage-3-spec/final-fix1-{kind}-evidence'
    target=OUT/f'{kind}-evidence'
    files={p.relative_to(source).as_posix():digest(p) for p in source.rglob('*') if p.is_file()}
    assert files=={p.relative_to(target).as_posix():digest(p) for p in target.rglob('*') if p.is_file()}
    copies[kind]={'records':len(files),'bytes':sum(v['bytes'] for v in files.values())}
paths=list((ROOT/'packages/sec-edgar-ingest/src').rglob('*.py'))+list((ROOT/'packages/sec-edgar-ingest/tests').rglob('*.py'))+[ROOT/p for p in ('conf/sec-edgar-ingest.yaml','conf/sec-edgar-etl-fixture.yaml','docs/runbooks/sec-edgar-etl-publication.md','packages/sec-edgar-ingest/README.md','scripts/check-sec-edgar-ingest.sh','uv.lock')]
result={'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'frozen':frozen,'proofs':checks,'copies':copies,'wheel':digest(wheel),'python_source_count':len(report['source_equality']),'package_readme_metadata_equal':True,'sources_tests_docs':{p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)},'all22_stage7_checks':'reserved'}
(OUT/'audit.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='sources_tests_docs'},indent=2))
