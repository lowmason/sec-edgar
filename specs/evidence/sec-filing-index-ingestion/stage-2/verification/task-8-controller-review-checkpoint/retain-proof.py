from pathlib import Path
import datetime,gzip,hashlib,json,subprocess,sys
root=Path.cwd()
sdd=root/'.sdd/2-sec-filing-index-ingestion-stage-2-spec'
v=root/'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
cp=Path(__file__).resolve().parent
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head=='5f9fe217eb038f2d2a94b84e915c78babf87a1ef',head
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
def h(data):return hashlib.sha256(data).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
maps=[v/'sdd-retention-map.json',v/'task-8-fix1-checkpoint/retention-map.json',v/'task-8-fix2-checkpoint/retention-map.json']
known={}
for path in maps:
    for row in json.loads(path.read_text())['files']:
        known[row.get('original_path',row.get('path'))]=row.get('original_sha256',row.get('sha256'))
prior=[]
for manifest,base in [(v/'sha256-manifest.json',v),(v/'task-8-fix1-checkpoint/sha256-manifest.json',root),(v/'task-8-fix2-checkpoint/sha256-manifest.json',root)]:
    data=manifest.read_bytes(); records=json.loads(data)['files']
    for row in records:
        b=(base/row['path']).read_bytes()
        assert len(b)==row['bytes'] and h(b)==row['sha256'],row['path']
    prior.append({'path':str(manifest.relative_to(root)),'sha256':h(data),'records':len(records)})
primary=subprocess.run([str(root/'.venv/bin/python'),str(sdd/'verify_primary.py')],capture_output=True,text=True)
assert primary.returncode==0,primary.stdout+primary.stderr
status={'recorded_at':started,'reviewed_source_head':head,'task_1_through_7':'Spec/Quality PASS','task_8':{'I2':'ADDRESSED after fresh GPT-6.1 Max scoped fix2 review','I3':'ADDRESSED after fresh GPT-6.1 Max scoped fix1 review','I1':'NEEDS_CONTEXT: single closed2015Q1 fixture endpoint excludes required October2026 daily sources; separate daily end=open configuration prepared but not executed'},'current_check':{'tests':289,'seconds':107.544,'exit_code':0,'sha256':'f8d4af430fadfec27aea03ef51e936f94652c8defd82b8c9ab9c5ca433a8809c'},'whole_branch_review':'pending; not yet eligible','stage2_completion':'unticked, no stamp or retirement','stage3':'no work or planning','all22_s7_checks':'reserved','live_sec_azure_compute_authority':'closed','primary':json.loads(primary.stdout),'prior_manifests':prior}
write(sdd/'controller-stage2-pending-owner-status.json',status)
rows=[]
for p in sorted(sdd.rglob('*')):
    if not p.is_file():continue
    name=p.relative_to(sdd).as_posix(); b=p.read_bytes(); digest=h(b)
    if known.get(name)==digest:continue
    compressed=name.endswith('.diff') and len(b)>500000
    dest=cp/'sdd'/(name+'.gz' if compressed else name)
    dest.parent.mkdir(parents=True,exist_ok=True)
    stored=gzip.compress(b,mtime=0) if compressed else b
    dest.write_bytes(stored)
    row={'original_path':name,'original_bytes':len(b),'original_sha256':digest,'retained_path':dest.relative_to(cp).as_posix(),'retained_bytes':len(stored),'retained_sha256':h(stored),'encoding':'gzip' if compressed else 'identity','change':'changed' if name in known else 'new'}
    recovered=gzip.decompress(dest.read_bytes()) if compressed else dest.read_bytes()
    assert recovered==b,name
    if compressed:row['retrieval']={'operation':'gzip decompression of retained_path','expected_output_bytes':len(b),'expected_output_sha256':digest}
    rows.append(row)
missing=sorted(set(known)-{p.relative_to(sdd).as_posix() for p in sdd.rglob('*') if p.is_file()})
assert not missing,missing
mapping={'schema_version':'sec-stage2-controller-review-retention-v1','recorded_at':started,'reviewed_source_head':head,'original_root':str(sdd),'retained_root':str(cp),'original_repository_relative_prefix':str(sdd.relative_to(root)),'retained_repository_relative_prefix':str(cp.relative_to(root)),'files':rows,'original_paths_missing_now':missing,'all_copied_or_decompressed_bytes_verified':True,'unchanged_fallback_maps_newest_first':[str(p.relative_to(root)) for p in reversed(maps)],'new_or_changed_source_file_count':len(rows),'new_or_changed_original_bytes':sum(r['original_bytes'] for r in rows),'new_or_changed_retained_bytes':sum(r['retained_bytes'] for r in rows),'exclusions':[]}
write(cp/'retention-map.json',mapping)
write(cp/'retention-execution.json',{'argv':sys.argv,'cwd':str(root),'started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':0,'copied_or_decompressed_equal':True,'prior_manifests_verified':prior})
excluded={'sha256-manifest.json','evidence-inventory.json'}
payload=[]
for p in sorted(cp.rglob('*')):
    if p.is_file() and p.name not in excluded:
        b=p.read_bytes(); payload.append({'path':str(p.relative_to(root)),'bytes':len(b),'sha256':h(b)})
manifest={'schema_version':'sec-stage2-controller-review-sha256-v1','files':payload,'exclusions':[{'path':str((cp/n).relative_to(root)),'reason':'Control references excluded to prevent self-hash cycles'} for n in sorted(excluded)]}
write(cp/'sha256-manifest.json',manifest)
inventory={'schema_version':'sec-stage2-controller-review-inventory-v1','reviewed_source_head':head,'recorded_at':started,'files_covered':len(payload),'covered_total_bytes':sum(r['bytes'] for r in payload),'new_or_changed_sdd_files':len(rows),'manifest_sha256':h((cp/'sha256-manifest.json').read_bytes()),'retention_map_sha256':h((cp/'retention-map.json').read_bytes()),'prior_manifests_unchanged':prior,'I1_owner_answer':'pending','Task8_Stage2':'not complete','whole_branch_review':'pending','self_hash_exclusions':sorted(excluded)}
write(cp/'evidence-inventory.json',inventory)
for row in payload:
    b=(root/row['path']).read_bytes()
    assert len(b)==row['bytes'] and h(b)==row['sha256'],row['path']
print(json.dumps(inventory,indent=2))
