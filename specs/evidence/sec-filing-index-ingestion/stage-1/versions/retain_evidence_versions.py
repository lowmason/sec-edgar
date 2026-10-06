import pathlib,csv,hashlib,json,datetime,subprocess
root=pathlib.Path('/Users/lowell/Projects/sec-edgar');base=root/'specs/evidence/sec-filing-index-ingestion/stage-1';versions=base/'versions';versions.mkdir(exist_ok=True);review=root/'.sdd/1-sec-filing-index-ingestion-stage-1-spec';receipt={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Byte-preserving extraction of added new-file diff lines; retain original line terminators and final newline; validate against historic index hash before retargeting; no claim timestamp/hash rewrite','versions':{}}
with (base/'index.csv').open(newline='') as handle:reader=csv.DictReader(handle);fields=reader.fieldnames;rows=list(reader)
by_id={row['evidence_id']:row for row in rows}
for name,diffname,key,eid in [('access-window.md','task-1-checkpoint-review.diff','access_authorized_not_activated','E-ACCESS'),('daily.csv','task-2-review.diff','task2_daily','E-T2-DAILY'),('quarterly.csv','task-2-review.diff','task2_quarterly',None)]:
    path=review/diffname;data=path.read_bytes();relative='specs/evidence/sec-filing-index-ingestion/stage-1/'+name;marker=f'diff --git a/{relative} b/{relative}\n'.encode();block=data.split(marker,1)[1].split(b'diff --git ',1)[0];body=b''.join(line[1:] for line in block.splitlines(keepends=True) if line.startswith(b'+') and not line.startswith(b'+++'));checksum=hashlib.sha256(body).hexdigest()
    if eid:assert checksum==by_id[eid]['sha256'],(name,checksum,by_id[eid]['sha256'])
    original=pathlib.Path(name);target=versions/f'{original.stem}-{checksum}{original.suffix}'
    if target.exists():assert target.read_bytes()==body
    else:target.write_bytes(body)
    receipt['versions'][key]={'path':str(target.relative_to(base)),'sha256':checksum,'bytes':len(body),'frozen_diff':str(path.relative_to(root)),'frozen_diff_sha256':hashlib.sha256(data).hexdigest(),'matched_historic_evidence_id':eid}
    if eid in ['E-ACCESS','E-T2-DAILY']:by_id[eid]['url_or_artifact']=str(target.relative_to(root))
for name,key,eid,category,claim,result,limitation in [('access-window.md','access_closed_current','E-ACCESS-CLOSED-T3','Source/probe observation','SEC investigation access closed with final shared accounting','Root closure 2026-10-06T00:06:34.377545Z;150 attempts;15293779 entity bytes;10 specimen receipts','Frozen current closure report; no renewed access authorization'),('daily.csv','task3_daily_current','E-T3-DAILY-CURRENT','Source/probe observation','Daily inventory retains five inspected selected specimen annotations','2176 rows; all original Task2 fields preserved except five authorized outcome annotations; linked selected inspection evidence','Frozen annotated inventory; D14 historical middle-quarter tail remains uninspected')]:
    body=(base/name).read_bytes();checksum=hashlib.sha256(body).hexdigest();original=pathlib.Path(name);target=versions/f'{original.stem}-{checksum}{original.suffix}'
    if target.exists():assert target.read_bytes()==body
    else:target.write_bytes(body)
    receipt['versions'][key]={'path':str(target.relative_to(base)),'sha256':checksum,'bytes':len(body),'source':'Current workspace snapshot at receipt creation UTC; no historical timestamp reassignment'}
    assert eid not in by_id
    rows.append(dict(zip(fields,[eid,claim,category,'Offline byte-preserving current-version retention',str(target.relative_to(root)),receipt['created_utc'],'Versioned Task3 closure/annotated state',result,limitation,checksum,'retain_evidence_versions.py; independent sha256 and shasum','0'])))
with (base/'index.csv.task3.tmp').open('w',newline='') as handle:writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)
(base/'index.csv.task3.tmp').replace(base/'index.csv');(versions/'version-map.json').write_text(json.dumps(receipt,indent=2)+'\n')
command=['shasum','-a','256',*[str(base/value['path']) for value in receipt['versions'].values()]];result=subprocess.run(command,capture_output=True,text=True,check=True);print(result.stdout);print('PASS: five immutable snapshots; original E-ACCESS/E-T2-DAILY hashes retained; only their references retargeted; two new current entries')
