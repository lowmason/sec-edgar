"""Repair-round audit: exact original mapping, new proofs and timeout bytes."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
from etl_proof import save,digest,metadata
import json,zipfile,hashlib
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/verification'
prior=OUT/'prior-task7-before-fix1'
mapping=json.loads((prior/'relocation.json').read_text())['moved_prefixes']
original=json.loads((prior/'original-root-inventory.json').read_text())
for name,value in original.items():
    prefix=name.split('/')[0]
    actual=OUT/(mapping[prefix]+name[len(prefix):] if prefix in mapping else name)
    assert digest(actual)==value,(name,actual)
verified=[]
for name in ('specimens','sequence','installed','installed/installed-sequence','prior-task7-before-fix1'):
    base=OUT/name; records=json.loads((base/'sha256.json').read_text())
    for relative,value in records.items():
        assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
        assert digest(base/relative)==value,(name,relative)
    verified.append({'path':name,'records':len(records),'inventory':digest(base/'sha256.json')})
installed=json.loads((OUT/'installed/report.json').read_text());wheel=OUT/'installed'/installed['wheel_name']
assert installed['exit']==0 and digest(wheel)==digest(ROOT/'dist'/wheel.name)==installed['wheel']
with zipfile.ZipFile(wheel) as archive:
    for name,value in installed['source_equality'].items():
        assert digest(ROOT/'packages/sec-edgar-ingest/src'/name)==value
        body=archive.read(name);assert value=={'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
    assert (ROOT/'packages/sec-edgar-ingest/README.md').read_text().strip() in archive.read('sec_edgar_ingest-0.1.0.dist-info/METADATA').decode()
timeouts=OUT/'final-check/timeouts'
children=json.loads((timeouts/'test_first_timeout_reaps_all_real_children_with_kill_fallback/observed.json').read_text())
assert [v['alive'] for v in children['children']]==[False,False]
assert [v['exit'] for v in children['children']]==[-9,-15]
partial=json.loads((timeouts/'test_partial_race_start_reaps_already_started_child/observed.json').read_text())
assert partial['children'][0]['alive'] is False and partial['children'][1]['pid'] is None
base=timeouts/'test_real_subprocess_timeout_retains_partial_output_bytes'
record=json.loads((base/'timeout.json').read_text())
assert record['outcome']=='timeout' and record['exit'] is None
for stream in ('stdout','stderr'): assert digest(base/record[stream+'_raw_file'])==record[stream+'_raw']
commands={name:json.loads((OUT/name/'command.json').read_text()) for name in ('final-check','sequence-command','installed-command')}
assert all(value['exit']==0 for value in commands.values())
assert json.loads((OUT/'specimens/report.json').read_text())['exit']==1
save(Path(__file__).parent/'audit.json',{**metadata(),'exit':0,'original_records_verified':len(original),
 'inventories_verified':verified,'commands':commands,'timeout_children':children,'partial_start':partial,
 'timeout_record':record,'wheel':digest(wheel),'source_files_equal':len(installed['source_equality']),
 'wheel_readme_equal':True,'specimen_scan_repeated':False,'status':'DONE_WITH_CONCERNS'})
print('Verified',len(original),'original payloads,',sum(v['records'] for v in verified),'proof inventory records, exact wheel/28sources/README, and actual timeout evidence.')
