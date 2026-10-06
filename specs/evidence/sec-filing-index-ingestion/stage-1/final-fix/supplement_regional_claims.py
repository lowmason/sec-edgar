"""Append selected regional documentary claims and resource envelope evidence."""
import csv,io,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
TASK=BASE/'final-fix'
claims_path=TASK/'claims.json'; claims_data=json.loads(claims_path.read_text()); claims=claims_data['records']
provenance_path=TASK/'claim-provenance.json';provenance_data=json.loads(provenance_path.read_text());provenance=provenance_data['records']
groups_path=TASK/'claim-groups.json';groups=json.loads(groups_path.read_text())
fields=list(claims[0]); new=[]
def append(identifier,claim,source,time,semantics,url,receipt,group,extra=None):
    sha=hashlib.sha256(source.read_bytes()).hexdigest(); artifact=str(source.relative_to(ROOT))
    row=dict(zip(fields,[identifier,claim,'Verified documentation','Offline retained-source reconciliation; '+semantics,
         url+'; '+artifact,time,'Retained rolling official capability documentation','Documented capability only',
         'No selected subscription quota/capacity/profile/registration/policy or effective worker fit proof; checks reserved/not_run.',sha,'','']))
    new.append(row);claims.append(row);groups.setdefault(group,[]).append(identifier)
    provenance.append({'evidence_id':identifier,'category':'Verified documentation','source_artifact':artifact,
        'source_bytes':source.stat().st_size,'source_sha256':sha,'source_url':url,
        'receipt_artifact':str(receipt.relative_to(ROOT)),'time_value':time,'time_semantics':semantics,
        'scope':'Exact retained-source bytes only; no new access',**(extra or {})})
regional=json.loads((BASE/'provider/task5-fix1/regional-rows.json').read_text())
receipt=BASE/'provider/task5-fix1-root-region/regional-table-receipt.json';raw=BASE/'provider/task5-fix1-root-region/regional-table.html';meta=json.loads(receipt.read_text())
for n,row in enumerate(regional['selected_rows'],1):
    append(f'E-FF-DOC-REGION-{n:02}',row['RegionName']+' official product-table row: '+row['OfferingName']+' / '+row['ProductSkuName']+' is GA.',
        raw,meta['end_utc'],'Original completed HTTP receipt end time; start time and headers retained separately.',meta['url'],receipt,'regional',
        {'source_array_ordinal':row['source_array_ordinal'],'selected_row':{k:v for k,v in row.items() if k!='source_array_ordinal'}})
source=BASE/'provider/task5-storage/sources-v1.json';s=json.loads(source.read_text());r=next(v for v in s['sources'] if v['id']=='containers')
append('E-FF-DOC-CONSUMPTION','Official containers resource table includes 2 CPU/4Gi memory; Jobs features are discussed in the same guide. No measured full-worker fit follows.',
       source,s['checkpoint_utc'],'Historical checkpoint upper bound; exact per-request web time unavailable.',r['url'],source,'space')
stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n');writer.writerows(new)
with (BASE/'index.csv').open('ab') as handle:handle.write(stream.getvalue().encode())
claims_path.write_text(json.dumps(claims_data,indent=2)+'\n');provenance_path.write_text(json.dumps(provenance_data,indent=2)+'\n');groups_path.write_text(json.dumps(groups,indent=2)+'\n')
coverage=TASK/'coverage.md';text=coverage.read_text()
text+='\n## Selected regional/resource-envelope claims\n\n'
text+='Each GA statement is a separate original embedded JSON row with exact source ordinal, raw HTML/hash and original HTTP receipt, rather than subscription-capacity proof.\n\n'
text+='| ID / category | Claim | Provenance |\n|---|---|---|\n'
for row in new:text+='| '+row['evidence_id']+' / Verified documentation | '+row['claim']+' | '+row['url_or_artifact']+'; SHA256 '+row['sha256']+'; '+row['method']+'; '+row['accessed_or_received_at_utc']+' |\n'
text=text.replace('Newly appended category counts: '+str({'Verified documentation':133,'Source/probe observation':7,'Assumption':10,'Owner decision':4,'Reserved Stage 7 check':22}),
                  'Newly appended category counts: '+str({'Verified documentation':161,'Source/probe observation':7,'Assumption':10,'Owner decision':4,'Reserved Stage 7 check':22}))
coverage.write_text(text)
finding=ROOT/'specs/sec-filing-index-ingestion-stage-1-findings.md';text=finding.read_text()
text=text.replace('## 6. Resources, volume, temporary space and retry rationale',
 'Selected official regional GA statements use exact raw product-table byte/hash provenance and independent source-array ordinals: '+', '.join(groups['regional'])+'. They establish documentary regional offerings only; subscription eligibility/capacity remains S7-01.\n\n## 6. Resources, volume, temporary space and retry rationale')
text=text.replace('Initial candidates remain general-purpose Consumption', 'E-FF-DOC-CONSUMPTION supports the documented resource-envelope entry separately from the selected configuration and actual fit. Initial candidates remain general-purpose Consumption')
finding.write_text(text)
checklist=BASE/'readiness-checklist.md';text=checklist.read_text().replace('27 official regional GA rows','27 independently indexed official regional GA rows (E-FF-DOC-REGION-01 through E-FF-DOC-REGION-27; full claims in [coverage](final-fix/coverage.md))')
text=text.replace('| 1c. Networking, IaC, resources, execution settings, retention and alerts |','| 1c. Networking, IaC, resources, execution settings, retention and alerts | E-FF-DOC-CONSUMPTION; selected values remain separate. ');checklist.write_text(text)
print(json.dumps({'appended_supplement':len(new),'total_new_claims':len(claims),'total_index_rows':383+len(claims)},indent=2))
