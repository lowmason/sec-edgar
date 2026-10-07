import sys
from pathlib import Path
ROOT=Path.cwd(); OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import json,hashlib,time,platform,traceback
from support_etl import seed_snapshot,etl_context
from sec_edgar_ingest.models import Source,url_source_id
from sec_edgar_ingest.etl.parser import PARSER_VERSION,ParseError
from sec_edgar_ingest.etl.transform import transform_member,_pinned_members
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.contracts import processing_key,observation_base
from sec_edgar_ingest.state import AcquisitionState
start=time.monotonic()
report={'argv':sys.argv,'cwd':str(ROOT),'platform':platform.platform(),'python':sys.version,'guard_installed':network_guard._INSTALLED,'receipts':[]}
E=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
for item in json.loads((E/'specimens/matrix.json').read_text())['matrix'][:3]:
    rid=item['evidence_id']; body=(E/f'listings/{rid}.body').read_bytes()
    assert len(body)==item['original_bytes'] and hashlib.sha256(body).hexdigest()==item['original_sha256']
    period=item['url'].split('/')[-3]+'Q'+item['url'].split('/')[-2][-1]
    source=Source(url_source_id(item['url']),item['url'],'quarterly',period,'zip')
    store,objects,snapshot_set=seed_snapshot(OUT/rid,source,body)
    snapshot_ref=f'worksets/sec/snapshot/sha256={snapshot_set.workset_id}/workset.json'
    decoded,sources=_pinned_members(snapshot_ref,objects,AcquisitionState(store))
    assert decoded==snapshot_set and sources[source.source_id]==source
    snapshot=decoded.snapshots[0]
    settings,context=etl_context(parser_version=PARSER_VERSION,attempt=rid.lower())
    state=EtlState(store)
    r={'receipt_id':rid,'source':source.to_mapping(),'sha256':snapshot.sha256,'bytes':len(body),'snapshot_ref':snapshot_ref,'snapshot':snapshot.to_mapping(),'context':context.to_mapping()}
    try:
        transform_member(source,snapshot,context,settings,objects,state)
        raise AssertionError('complete conflicting source unexpectedly accepted')
    except ParseError as error:
        r['exception']={'type':type(error).__name__,'physical_line':error.line_number,'reason':error.reason,'message':str(error),'traceback':traceback.format_exc()}
        assert error.reason=='conflicting duplicate logical key'
    quarantine=f'quarantine/sec/{context.run_id}/{source.source_id}/transform/{context.attempt_id}/error.json'
    qbody=objects.read(quarantine); q=json.loads(qbody)
    assert q['code']=='transform_failed' and q['details']['line_number']==r['exception']['physical_line'] and q['details']['raw_sha256']==snapshot.sha256
    assert objects.read(snapshot.raw_path)==body
    key=processing_key(source.source_id,snapshot.sha256,context.parser_version,context.schema_version)
    assert store.get('Processing',key) is None
    assert not list(store.scan('Processing',{}))
    assert not list(store.scan('QuarterPublication',{}))
    assert state.pointer(period) is None
    base=observation_base(source.source_id,snapshot.sha256,context.parser_version,context.schema_version)
    assert not (objects.directory/base).exists()
    r.update(quarantine_error_ref=quarantine,quarantine_error=q,quarantine_error_sha256=hashlib.sha256(qbody).hexdigest(),raw_reference=snapshot.raw_path,raw_preserved=True,processing_absent=True,observation_ref_absent=True,published_pointer_absent=True,status='DONE')
    report['receipts'].append(r); print(json.dumps(r),flush=True)
report.update(runtime_seconds=time.monotonic()-start,exit_code=0,status='DONE')
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
