"""Compare all original matrix fields with the frozen Task 2 review evidence."""
import csv
import hashlib
import json
import pathlib
BASE=pathlib.Path(__file__).resolve().parents[1]
version_map = json.loads((BASE/'versions/version-map.json').read_text())
expected_original_hashes = {'quarterly.csv': 'd738bebd7f73ddf278f701551eafb51574f7ea74e45536543be0384dd85bfdf8', 'daily.csv': 'fb8c5dfa54d56c14a1bc1041475519d4c9138f63f7b79cd652f90ccc47a29bf8'}
reports=[json.loads(p.read_text()) for p in (BASE/'specimens').glob('SEC-*.inspection.json')]
selected={r['url']:r for r in reports}
results={}
for name in ('quarterly.csv','daily.csv'):
    version = version_map['versions']['task2_quarterly' if name == 'quarterly.csv' else 'task2_daily']
    original_path = BASE/version['path']
    assert original_path.parent == BASE/'versions'
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == version['sha256'] == expected_original_hashes[name]
    original=list(csv.DictReader(original_path.open()))
    current=list(csv.DictReader((BASE/name).open()))
    assert len(current)==len(original), (name,len(current),len(original))
    changes=0
    for old,new in zip(original,current):
        report=selected.get(old['discovered_url'])
        allowed={'source_status','selection_reason'} if name=='quarterly.csv' else {'outcome'}
        for field,value in old.items():
            if new[field]!=value:
                assert report and field in allowed,(name,old['discovered_url'],field,value,new[field])
                changes+=1
        if name=='daily.csv':
            assert new['inspection_evidence_id']==(report['evidence_id'] if report else '')
            assert new['inspection_artifact']==(f"specimens/{report['evidence_id']}.inspection.json" if report else '')
    results[name]={'original_rows':len(original),'current_rows':len(current),'authorized_original_field_changes':changes,'all_other_original_fields':'byte-string equal in same row order'}
print(json.dumps({'retained_version_map':'versions/version-map.json', 'original_matrix_hashes':expected_original_hashes,'result':'PASS','matrices':results,'tail_recovery':'All four recovered daily tail rows match frozen original fields and row order'},indent=2))
