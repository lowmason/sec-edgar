"""Verify every Task 7 inventory and final exact wheel/source boundary."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
from etl_proof import inventory,digest,save,metadata
import json,zipfile
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/verification'
roots=[OUT/'specimens',OUT/'sequence',OUT/'installed',OUT/'installed-before-readme-correction',
       OUT/'sdd-history']
roots.extend(p.parent for p in (OUT/'sdd-history/task7-evidence').rglob('sha256.json'))
roots.extend([OUT/'installed/installed-sequence',OUT/'installed-before-readme-correction/installed-sequence'])
checked=[]
for root in roots:
    manifest=root/'sha256.json'
    records=json.loads(manifest.read_text())
    for relative,value in records.items():
        p=Path(relative)
        assert not p.is_absolute() and '..' not in p.parts and (root/p).resolve().is_relative_to(root.resolve())
        assert digest(root/p)==value,(manifest,relative)
    checked.append({'manifest':str(manifest.relative_to(OUT)),'records':len(records),'bytes':sum(v['bytes'] for v in records.values())})
installed=json.loads((OUT/'installed/report.json').read_text())
wheel=OUT/'installed'/installed['wheel_name']
assert digest(wheel)==digest(ROOT/'dist'/wheel.name)==installed['wheel']
with zipfile.ZipFile(wheel) as archive:
    assert (ROOT/'packages/sec-edgar-ingest/README.md').read_text().strip() in archive.read('sec_edgar_ingest-0.1.0.dist-info/METADATA').decode()
    for name,value in installed['source_equality'].items():
        assert digest(ROOT/'packages/sec-edgar-ingest/src'/name)==value
        import hashlib
        body=archive.read(name)
        assert value=={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
commands=[]
for base in [OUT/'sdd-history/task7-evidence',OUT]:
    for p in base.rglob('*.json'):
        if base==OUT and 'sdd-history' in p.parts: continue
        value=json.loads(p.read_text())
        if isinstance(value,dict) and isinstance(value.get('exit'),int) and ('argv' in value or p.name=='report.json'):
            commands.append({'path':p.relative_to(OUT).as_posix(),'exit':value['exit'],'argv':value.get('argv'),
                             'has_full_inline_logs':'stdout' in value and 'stderr' in value,
                             'has_full_separate_logs':(p.parent/'stdout.txt').exists() and (p.parent/'stderr.txt').exists()})
assert json.loads((OUT/'specimens/report.json').read_text())['exit']==1
assert all(json.loads((OUT/name/'report.json').read_text())['exit']==0 for name in ('sequence','installed'))
save(OUT/'artifact-inspection.json',{**metadata(),'exit':0,'verified_inventories':checked,'commands_and_results':commands,
     'wheel':digest(wheel),'source_files_equal':len(installed['source_equality']),'wheel_readme_equals_tree':True,
     'status':'DONE_WITH_CONCERNS: retained specimen source acceptance remains blocked'})
print('Verified',sum(v['records'] for v in checked),'inventory records,',len(commands),'command/result records, exact wheel and',len(installed['source_equality']),'sources.')
