from pathlib import Path
import hashlib,json,datetime
from sec_edgar_ingest.worksets import decode_snapshot_workset,encode_workset
root=Path.cwd(); sdd=root/'.sdd/2-sec-filing-index-ingestion-stage-2-spec'
p=root/'specs/evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-k8g11etz'
manifest=json.loads((p/'sha256-manifest.json').read_text())
for row in manifest:
    b=(p/row['path']).read_bytes()
    assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],row['path']
summary=json.loads((p/'sequence-summary.json').read_text())
assert summary['prescribed_step_4']=='executed with explicitly approved separate configs'
calls=json.loads((p/'calls.json').read_text())
assert len(calls)==11
for call in calls:
    ex=json.loads((p/(call['label']+'.exit.json')).read_text())
    assert call['exit']==ex['exit']==ex['expected'],call['label']
q=summary['quarterly_results']; d=summary['daily_results']
assert [x['outcome'] for x in d]==['success','incomplete','success','success']
assert (d[1]['downloaded'],d[1]['pending'],d[1]['snapshot_workset_ref'])==(1,1,None)
assert (d[2]['downloaded'],d[2]['unchanged'],d[3]['downloaded'],d[3]['unchanged'])==(1,1,0,2)
assert d[2]['snapshot_workset_ref']==d[3]['snapshot_workset_ref']
assert q[1]['snapshot_workset_ref']==q[2]['snapshot_workset_ref']
assert (q[1]['downloaded'],q[2]['unchanged'])==(1,1)
state=json.loads((p/'final-state-records.json').read_text())
transports=[x['value'] for x in state['TransportAttempt']]
assert len(transports)==11 and len(state['Binding'])==3
late=sorted((x for x in transports if x['url'].endswith('master.20261002.idx')),key=lambda x:x['begun_at'])
assert [x['status'] for x in late]==[404,200]
assert sum(x['url'].endswith('master.20261001.idx') for x in transports)==1
assert sum(x['url'].endswith('full-index/2015/QTR1/master.zip') for x in transports)==1
assert not any(x['context']['attempt_id']=='daily-collect-3' for x in transports)
objects=p/'state/.fixture-state/objects'; snapshots=[]
for result in (q[1],d[2]):
    body=(objects/result['snapshot_workset_ref']).read_bytes()
    decoded=decode_snapshot_workset(body)
    assert encode_workset(decoded)==body
    assert 'sha256='+decoded.workset_id in result['snapshot_workset_ref']
    for snap in decoded.snapshots:
        b=(objects/snap.raw_path).read_bytes()
        assert len(b)==snap.byte_count and hashlib.sha256(b).hexdigest()==snap.sha256
        assert any(x['value']['source_workset_id']==decoded.source_workset_id and x['value']['source_id']==snap.source_id and x['value']['snapshot_sha256']==snap.sha256 for x in state['Binding'])
        snapshots.append({'source_id':snap.source_id,'sha256':snap.sha256,'bytes':snap.byte_count,'raw_path':snap.raw_path})
receipt={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'read-only independent retained combined-sequence inspection; no command rerun or network','bundle':str(p.relative_to(root)),'manifest_records':len(manifest),'all_payload_hashes_match':True,'command_exits_expected':[{'label':x['label'],'exit':x['exit']} for x in calls],'final_transport_rows':len(transports),'binding_count':len(state['Binding']),'delayed_statuses':[x['status'] for x in late],'daily_outcomes':[x['outcome'] for x in d],'recovery_and_final_snapshot_ref':d[2]['snapshot_workset_ref'],'completed_members_fetched_once':True,'final_attempt_transport_rows':0,'canonical_worksets_and_raw_pins_verified':snapshots,'exit_code':0}
(sdd/'controller-task8-i1-inspection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
