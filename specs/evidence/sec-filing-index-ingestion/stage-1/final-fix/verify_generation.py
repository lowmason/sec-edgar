"""Read-only correction checks, reusing stable Task6 functions without rewriting history."""
import csv
import hashlib
import importlib.util
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
TASK=BASE/'final-fix'
CATEGORIES={'Verified documentation','Source/probe observation','Owner decision','Assumption','Reserved Stage 7 check'}

def read_json(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def old_path(record, maps):
    path=ROOT/record['path']
    if path.is_file() and digest(path)==record['sha256']:
        return path
    target=maps.get((record['path'],record['sha256']))
    assert target, ('historical record unresolved', record)
    return ROOT/target

def verify_history():
    mapping=read_json(TASK/'historical-path-map.json')['records']
    maps={(r['source_path'],r['sha256']):r['immutable_path'] for r in mapping}
    for r in mapping:
        path=ROOT/r['immutable_path']
        assert path.stat().st_size==r['bytes'] and digest(path)==r['sha256'], r
    # Exact controller pre-fix bytes and original manifest resolve through immutable aliases.
    before=next(ROOT/r['immutable_path'] for r in mapping if r['source_path'].endswith('final-fix-before-manifest.json'))
    outcomes={}
    for path in (before,BASE/'task6/evidence-manifest.json'):
        manifest=read_json(path)
        retargeted=[]
        for r in manifest['records']:
            resolved=old_path(r,maps)
            assert resolved.stat().st_size==r['bytes'] and digest(resolved)==r['sha256'],r
            if str(resolved.relative_to(ROOT))!=r['path']:
                retargeted.append({'old_path':r['path'],'sha256':r['sha256'],'immutable_path':str(resolved.relative_to(ROOT))})
        outcomes[path.name]={'files_verified':len(manifest['records']),'immutable_old_references':retargeted}
    freeze=read_json(BASE/'task6/draft-freeze.json')
    assert digest(BASE/'task6/evidence-manifest.json')==freeze['evidence_manifest_sha256']
    assert digest(ROOT/freeze['immutable_finding_path'])==freeze['finding_sha256']
    for r in read_json(BASE/'task6/draft-artifact-versions.json')['records']:
        p=ROOT/r['immutable_path']
        assert p.stat().st_size==r['bytes'] and digest(p)==r['sha256'],r
    return outcomes

def verify_claims():
    rows=list(csv.DictReader((BASE/'index.csv').open(newline='')))
    columns=list(rows[0])
    assert columns=='evidence_id,claim,category,method,url_or_artifact,accessed_or_received_at_utc,versions,result,limitation,sha256,command,exit_code'.split(',')
    assert len({r['evidence_id'] for r in rows})==len(rows)
    assert set(r['category'] for r in rows)==CATEGORIES
    mapping=read_json(TASK/'historical-path-map.json')['records']
    old_index=next(ROOT/r['immutable_path'] for r in mapping if r['source_path']==str((BASE/'index.csv').relative_to(ROOT)))
    assert (BASE/'index.csv').read_bytes().startswith(old_index.read_bytes())
    historical=list(csv.DictReader(old_index.open(newline='')))
    claims=read_json(TASK/'claims.json')['records']
    assert rows==historical+claims and len(historical)==383
    provenance=read_json(TASK/'claim-provenance.json')['records']
    assert {r['evidence_id'] for r in claims}=={r['evidence_id'] for r in provenance}
    by_id={r['evidence_id']:r for r in claims}
    docs=0
    for p in provenance:
        r=by_id[p['evidence_id']]
        source=ROOT/p['source_artifact']
        assert source.stat().st_size==p['source_bytes'] and digest(source)==p['source_sha256']==r['sha256']
        assert p['time_value']==r['accessed_or_received_at_utc'] and p['time_semantics'] in r['method']
        if r['category']=='Verified documentation':
            assert p['source_url'].startswith(('https://learn.microsoft.com/','https://raw.githubusercontent.com/Azure/','https://github.com/Azure/','https://azure.microsoft.com/'))
            assert p['source_url'] in r['url_or_artifact']
            receipt=ROOT/p['receipt_artifact']; assert receipt.is_file()
            metadata=read_json(receipt)
            if receipt.name=='regional-table-receipt.json':
                assert metadata['end_utc']==p['time_value'] and metadata['url']==p['source_url']
                assert metadata['bytes']==p['source_bytes'] and metadata['sha256']==p['source_sha256']
                raw=source.read_text();offset=raw.index('[',raw.index('const data'))
                original,_=json.JSONDecoder().raw_decode(raw[offset:])
                assert original[p['source_array_ordinal']]==p['selected_row']
            elif receipt.name=='retrieval-metadata.json':
                candidates=[s for s in metadata['records'] if p['source_url']==s.get('source_url') or p['source_url'] in s.get('source_urls',[])]
                assert candidates,p
                assert any(s.get('retained_at_utc')==p['time_value'] and s.get('outcome')!='failed retrieval' for s in candidates),p
            elif receipt.name=='sources-v1.json':
                assert metadata['checkpoint_utc']==p['time_value']
                assert any(s['url']==p['source_url'] for s in metadata['sources'])
            else:
                source_data=read_json(source)
                assert source_data['source_url']==p['source_url'] and source_data['retrieved_at_utc']==p['time_value']
            docs+=1
        if r['category']=='Assumption':
            assert p['responsible_owner']=='Lowell Mason'
            assert p['impact'] and p['resolution_obligation']
            assert all(field in r['limitation'] for field in ('Impact:','Responsible owner:','Resolution obligation:'))
        if r['category']=='Owner decision':
            receipt=read_json(source)
            assert receipt['accepted_proposal_sha256']=='038cb2ddcd2ca444d7a3855a4686cb457aa13bd373c767bee854ed657d59f944'
        if r['category']=='Reserved Stage 7 check':
            assert p['status']=='reserved/not_run'
            assert p['responsible_actor'] and p['required_passing_artifact']
            assert p['required_passing_artifact'] in r['result'] and p['responsible_actor'] in r['limitation']
    reserved=[r for r in provenance if r['category']=='Reserved Stage 7 check']
    assert {r['stage7_id'] for r in reserved}=={f'S7-{i:02}' for i in range(1,23)}
    text=(BASE/'stage-7-checks.md').read_text()
    assert 'Accepted-if-owner-confirms' not in text and 'Accepted R3 D-01–D-04 binding' in text
    assert len(re.findall(r'^\| S7-',text,re.MULTILINE))==22
    assert len(re.findall(r'\| reserved/not_run \|$',text,re.MULTILINE))==22
    coverage=(TASK/'coverage.md').read_text()
    assert all(r['evidence_id'] in coverage for r in claims)
    finding=(ROOT/'specs/sec-filing-index-ingestion-stage-1-findings.md').read_text()
    checklist=(BASE/'readiness-checklist.md').read_text()
    assert all(r['evidence_id'] in finding for r in claims),[r['evidence_id'] for r in claims if r['evidence_id'] not in finding]
    assert 'With fixes' in finding and 'scoped re-review' in finding and 'owner acceptance' in finding
    assert 'With fixes' in checklist and 'unrun for this draft' not in checklist
    assert read_json(TASK/'controller-boundary.json')['owner_acceptance']=='pending'
    return {'historical_rows_exact':len(historical),'appended_claims':len(claims),'total_rows':len(rows),
        'all_category_counts':dict(Counter(r['category'] for r in rows)),
        'new_category_counts':dict(Counter(r['category'] for r in claims)),
        'official_source_provenance_records':docs,'reserved_checks':len(reserved),'all_new_ids_cited_in_finding':True,
        'claim_scope_limit':'Metadata/hash/coverage checks do not prove effective deployment or replace material review.'}

def stable_checks():
    spec=importlib.util.spec_from_file_location('historical_integrity',BASE/'task6/verify_integrity.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return {'protection':module.check_protection(),'accounting':module.check_accounting(),
            'provider_decisions_runtime':module.check_decisions_provider_runtime(),
            'index_and_links':module.check_index_and_links()}

if __name__=='__main__':
    result={'history':verify_history(),'claims':verify_claims(),'stable_readonly_checks':stable_checks(),
            'result':'PASS','semantics':'Fresh correction-generation offline evidence checks only; owner acceptance/re-review pending.'}
    print(json.dumps(result,indent=2))
