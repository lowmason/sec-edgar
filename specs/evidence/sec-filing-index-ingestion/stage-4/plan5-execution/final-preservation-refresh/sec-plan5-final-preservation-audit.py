import os,json,pathlib,hashlib,subprocess,datetime,stat
E=pathlib.Path('/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar')
P=pathlib.Path('/Users/lowell/Projects/sec-edgar')
B=E/'specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/preflight'
OUT=pathlib.Path('/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar/specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/final-preservation-refresh/results');OUT.mkdir(exist_ok=False)
errors=[]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(root,*args):
 c=subprocess.run(['git','--no-optional-locks','-C',str(root),*args],capture_output=True,text=True,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 if c.returncode:errors.append({'git':list(args),'root':str(root),'exit':c.returncode,'stderr':c.stderr})
 return c.stdout.strip()
def inventory(root):
 records=[];special=[]
 for base,dirs,files in os.walk(root,followlinks=False):
  dirs[:]=sorted(d for d in dirs if d!='.git')
  for name in sorted(files+ [d for d in dirs if pathlib.Path(base,d).is_symlink()]):
   p=pathlib.Path(base,name);rel=p.relative_to(root).as_posix()
   if name=='.git':continue
   s=p.lstat()
   if stat.S_ISLNK(s.st_mode):records.append({'path':rel,'link':os.readlink(p)})
   elif stat.S_ISREG(s.st_mode):records.append({'path':rel,'bytes':s.st_size,'sha256':sha(p)})
   else:special.append(rel)
 return sorted(records,key=lambda r:r['path']),special
def compare(root,baseline,name):
 before=json.loads(baseline.read_text());after,special=inventory(root)
 (OUT/(name+'-after.json')).write_text(json.dumps(after,indent=2)+'\n')
 a={r['path']:r for r in before};b={r['path']:r for r in after}
 missing=sorted(a.keys()-b.keys());added=sorted(b.keys()-a.keys());changed=[{'path':p,'before':a[p],'after':b[p]} for p in sorted(a.keys()&b.keys()) if a[p]!=b[p]]
 r={'root':str(root),'baseline':str(baseline),'baseline_sha256':sha(baseline),'before_records':len(a),'after_records':len(b),'regular_records':sum('sha256'in x for x in after),'symlink_records':sum('link'in x for x in after),'exact_matching_records':sum(a[p]==b[p] for p in a.keys()&b.keys()),'missing':missing,'added':added,'changed':changed,'special_files':special,'passed':not(missing or added or changed or special)}
 if not r['passed']:errors.append({'inventory':name,'missing':missing,'added':added,'changed':changed,'special':special})
 print(name,r['before_records'],r['after_records'],r['exact_matching_records'],r['passed'],flush=True)
 return r
pre=json.loads((B/'preflight.json').read_text());report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Read-only stdlib os.walk without following symlinks; exclude entries named .git; compare all path membership, regular byte sizes and SHA-256 hashes, literal symlink targets. Git uses --no-optional-locks and GIT_OPTIONAL_LOCKS=0; no project imports/tests/build/network/mutations. Directory modes, mtime, permissions and volatile .git metadata are outside record inventory.'}
report['primary_inventory']=compare(P,B/'primary-before.json','primary')
report['retained_inventories']=[compare(pathlib.Path(r['root']),B/f'retained-{i}-before.json',f'retained-{i}') for i,r in enumerate(pre['retained_roots'])]
report['primary_git']={'head':git(P,'rev-parse','HEAD'),'origin_main':git(P,'rev-parse','refs/remotes/origin/main'),'status':git(P,'status','--porcelain'),'index_sha256':sha(P/'.git/index'),'required_absences':{p:not os.path.lexists(P/p) for p in pre['required_absences']}}
pg=report['primary_git'];pg['passed']=pg['head']==pre['primary_head'] and pg['origin_main']==pre['origin_main'] and pg['status']==pre['primary_status'] and pg['index_sha256']==pre['primary_index_sha256'] and all(pg['required_absences'].values())
if not pg['passed']:errors.append({'primary_git':pg})
refs={'refs/heads/codex/sec-edgar-stage-4':'e870a7318d47699c0e4a76ab59fba72781b0debe','refs/codex/snapshots/44e1d887f038bc90b963848b95a277c13f57f9d9':'e870a7318d47699c0e4a76ab59fba72781b0debe','refs/heads/codex/sec-edgar-stage-4-replan':'b788b44a84d077817a4a3cb24378157c0e1b163c'}
report['preserved_refs']=[{'ref':r,'expected':v,'actual':git(P,'rev-parse',r)} for r,v in refs.items()]
for r in report['preserved_refs']:
 r['passed']=r['actual']==r['expected']
 if not r['passed']:errors.append({'ref':r})
planning=pathlib.Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-4-replan/sec-edgar')
report['planning']={'root':str(planning),'head':git(planning,'rev-parse','HEAD'),'branch':git(planning,'branch','--show-current'),'status':git(planning,'status','--porcelain'),'index_path':git(planning,'rev-parse','--git-path','index')}
pi=pathlib.Path(report['planning']['index_path']);pi=pi if pi.is_absolute() else planning/pi
report['planning']['path_exists']=planning.exists()
report['planning']['index_sha256']=sha(pi) if pi.is_file() else None
if not planning.exists():errors.append({'planning_checkout_absent':str(planning)})
# Entire planning tracked tree is independently bound to preserved commit via blob-byte equality.
tracked=git(P,'ls-tree','-rz','--full-tree','b788b44a84d077817a4a3cb24378157c0e1b163c').split('\0'); mismatches=[];count=0
for rec in tracked:
 if not rec:continue
 meta,path=rec.split('\t',1);mode,kind,blob=meta.split();p=(planning if planning.exists() else pathlib.Path('/private/tmp/sec-stage4-plan5-independent-th0wqyvh/checkpoint'))/path;count+=1
 data=subprocess.run(['git','--no-optional-locks','-C',str(P),'cat-file','blob',blob],capture_output=True)
 if data.returncode:errors.append({'blob_read':blob,'stderr':data.stderr.decode()});continue
 if mode=='120000':actual=os.readlink(p).encode() if p.is_symlink() else None
 else:actual=p.read_bytes() if p.is_file() and not p.is_symlink() else None
 if actual!=data.stdout:mismatches.append({'path':path,'blob':blob,'expected_sha256':hashlib.sha256(data.stdout).hexdigest(),'actual_sha256':hashlib.sha256(actual).hexdigest() if actual is not None else None})
report['planning']['tracked_comparison_root']=str(planning if planning.exists() else pathlib.Path('/private/tmp/sec-stage4-plan5-independent-th0wqyvh/checkpoint'));report['planning']['tracked_records_compared']=count;report['planning']['tracked_mismatches']=mismatches
report['planning']['passed']=report['planning']['head']==refs['refs/heads/codex/sec-edgar-stage-4-replan'] and report['planning']['branch']=='codex/sec-edgar-stage-4-replan' and report['planning']['status']=='' and not mismatches
if not report['planning']['passed']:errors.append({'planning':report['planning']})
report['stopped_original_path_absent']=not os.path.lexists('/Users/lowell/.codex/worktrees/sec-edgar-stage-4/sec-edgar')
if not report['stopped_original_path_absent']:errors.append({'stopped_path':'unexpectedly present'})
report['ignored_recovery_receipt']={'path':'/private/tmp/sec-stage4-ignored-recovery-phpsldej/receipt.json','sha256':sha(pathlib.Path('/private/tmp/sec-stage4-ignored-recovery-phpsldej/receipt.json'))}
report['ignored_recovery_receipt']['passed']=report['ignored_recovery_receipt']['sha256']=='a1ccf73e2032ed2dd18f9f441c96f365d08f8f94496010d34f4c6c2f306a3597'
if not report['ignored_recovery_receipt']['passed']:errors.append({'receipt':report['ignored_recovery_receipt']})
# Source and snapshot authorities compared in execution, planning and retained independent checkpoint.
verify=json.loads((E/'specs/evidence/sec-filing-index-ingestion/stage-4/replanning/verification.json').read_text());authorities=verify['authority']+[{'path':verify['plan']['path'],'sha256':verify['plan']['sha256']},{'path':'specs/evidence/sec-filing-index-ingestion/stage-4/replanning/approval/approved-plan-5.md','sha256':verify['plan']['sha256']}]
report['authority_checks']=[]
for root in [E,planning,pathlib.Path('/private/tmp/sec-stage4-plan5-independent-th0wqyvh/checkpoint')]:
 for a in authorities:
  p=root/a['path'];actual=sha(p) if p.is_file() else None;r={'root':str(root),'path':a['path'],'expected':a['sha256'],'actual':actual,'passed':actual==a['sha256']};report['authority_checks'].append(r)
  if not r['passed']:errors.append({'authority':r})
report['limitations']=['Planning checkout absent at final audit. Its status/index/working tree cannot be verified; independent retained checkpoint tracked tree compared to preserved b788b44 commit instead. No complete planning ignored-file or index baseline supplied; no claim of planning worktree preservation/restoration.','No mode/mtime/directory membership audit; exact record membership means regular files and symlinks. .git metadata intentionally excluded except explicit HEAD/index/status/refs checks.','433 original stopped runtime/bytecode records remain covered by owner-approved offline regeneration disposition; absent original checkout is not represented as restored.','Point-in-time final preservation audit only; no implementation review or tests.']
report['errors']=errors;report['passed']=not errors
(OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'errors':errors,'planning_records':count,'authority_checks':len(report['authority_checks']),'output':str(OUT)},indent=2),flush=True)
raise SystemExit(bool(errors))
