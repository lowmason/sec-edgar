import sys
from pathlib import Path
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
import json,hashlib,sqlite3,platform,time,traceback
from datetime import datetime,timezone
from collections import Counter
from sec_edgar_ingest.models import Source,Snapshot,url_source_id
from sec_edgar_ingest.etl.parser import iter_observations,PARSER_VERSION,SCHEMA_VERSION,ParseError
from sec_edgar_ingest.etl.transform import _seen_database,_remember_observation
OUT=Path(__file__).parent
E=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
started=time.monotonic()
report={'argv':sys.argv,'cwd':str(ROOT),'platform':platform.platform(),'python':sys.version,'guard_installed':network_guard._INSTALLED,'scope':'ten retained receipts only; no global range or all22_stage7_checks claims','receipts':[]}
for item in json.loads((E/'specimens/matrix.json').read_text())['matrix']:
    rid=item['evidence_id']; inspection=json.loads((E/item['inspection']).read_text()); path=E/inspection['original_path']
    body=path.read_bytes(); digest=hashlib.sha256(body).hexdigest()
    r={'evidence_id':rid,'original_path':str(path),'bytes':len(body),'sha256':digest,'receipt_url':item['url'],'rows':0,'status':'running','quarter_counts':{},'selected_inspected_rows':[]}
    report['receipts'].append(r)
    try:
        assert len(body)==item['original_bytes']==inspection['original_bytes']
        assert digest==item['original_sha256']==inspection['original_sha256']
        receipt=(E/f'listings/{rid}.body').read_bytes()
        assert receipt==body
        kind='quarterly' if item['text_family']=='quarterly ISO-date master' else 'daily'
        url=item['url']; alias=url.endswith('/full-index/master.zip')
        if alias:
            url='https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/master.zip'
            r['root_alias_context']='Root receipt parsed under matching 2026Q4 family/source context; exact bytes equal SEC-0144; root URL is not a valid Source contract.'
        period=(url.split('/')[-1][7:15] if kind=='daily' else url.split('/')[-3]+'Q'+url.split('/')[-2][-1])
        if kind=='daily': period=f'{period[:4]}-{period[4:6]}-{period[6:]}'
        rep='zip' if kind=='quarterly' else 'idx'
        source=Source(url_source_id(url),url,kind,period,rep)
        snap=Snapshot(source.source_id,digest,f'raw/sec/indexes/kind={kind}/period={period}/sha256={digest}/master.{rep}',len(body),datetime.now(timezone.utc),{},rep,'sec-'+kind+'-envelope-v1')
        r['source']=source.to_mapping(); r['selected_family']=item['text_family']
        selected=set(inspection['observations'].get('date_bound_raw_rows',{}).values())|set(inspection['observations'].get('representative_raw_rows',{}).values())
        dbpath=OUT/f'{rid}.sqlite'; db=_seen_database(dbpath)
        counts=Counter(); minimum=maximum=None; duplicates=0; conflicts=[]
        for obs in iter_observations(path,source,snap,parser_version=PARSER_VERSION,schema_version=SCHEMA_VERSION):
            r['rows']+=1
            d=obs.row.filing_date.isoformat(); minimum=d if minimum is None else min(minimum,d); maximum=d if maximum is None else max(maximum,d)
            counts[f'{d[:4]}Q{(obs.row.filing_date.month-1)//3+1}']+=1
            exists=db.execute('SELECT 1 FROM seen WHERE cik=? AND path=?',(obs.row.cik,obs.row.archive_path)).fetchone()
            try: _remember_observation(db,obs)
            except ParseError as error:
                conflicts.append({'physical_line':error.line_number,'reason':error.reason,'original_fields':obs.original_fields,'row':obs.row.to_mapping(),'first_payload':json.loads(db.execute('SELECT payload FROM seen WHERE cik=? AND path=?',(obs.row.cik,obs.row.archive_path)).fetchone()[0])})
                exists=None
            duplicates+=exists is not None
            raw='|'.join(obs.original_fields)
            if raw in selected: r['selected_inspected_rows'].append({'line_number':obs.line_number,'original_fields':obs.original_fields,'row':obs.row.to_mapping()}); selected.remove(raw)
        distinct=db.execute('SELECT COUNT(*) FROM seen').fetchone()[0]; db.close(); dbpath.unlink()
        r.update(date_minimum=minimum,date_maximum=maximum,quarter_counts=dict(counts),identical_duplicate_keys=duplicates,conflicting_duplicate_keys=len(conflicts),conflicts=conflicts,distinct_keys=distinct,missing_inspected_rows=sorted(selected))
        assert r['rows']==item['row_count']
        expected=[datetime.strptime(v,'%Y%m%d').date().isoformat() if len(v)==8 else v for v in item['filing_date_bounds']]
        assert [minimum,maximum]==expected
        assert not selected
        r['status']='BLOCKED' if conflicts else 'DONE'
    except Exception as exc:
        r.update(status='BLOCKED',error_type=type(exc).__name__,reason=str(exc),physical_line=getattr(exc,'line_number',None),traceback=traceback.format_exc())
    print(json.dumps(r),flush=True)
report['runtime_seconds']=time.monotonic()-started
report['exit_code']=0 if all(r['status']=='DONE' for r in report['receipts']) else 1
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(report['exit_code'])
