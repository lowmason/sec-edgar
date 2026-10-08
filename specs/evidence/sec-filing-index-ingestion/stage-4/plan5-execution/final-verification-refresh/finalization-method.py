import hashlib,json,os,re,subprocess,time
from pathlib import Path
ROOT=Path('/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar')
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/final-verification-refresh'
ENV=dict(os.environ,UV_PYTHON_DOWNLOADS='never',PYTHONDONTWRITEBYTECODE='1'); ENV.pop('PYTHONPATH',None)
def once(path,value):
    with path.open('x') as f: json.dump(value,f,sort_keys=True,indent=2); f.write('\n')
def command(label,argv):
    start=time.monotonic(); p=subprocess.run(argv,cwd=ROOT,env=ENV,capture_output=True,text=True)
    once(OUT/(label+'.json'),{'argv':argv,'cwd':str(ROOT),'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode,'runtime_seconds':time.monotonic()-start})
    if p.returncode: raise RuntimeError(label+' failed')
    return p.stdout
SCRIPT='''import json,sys
from pathlib import Path
sys.path.insert(0,'packages/sec-edgar-ingest/tests')
from locked_proof import inventory,verify_inventory,locked_requirements,marker_environment,package_inventory,digest
root=Path(sys.argv[1]); old=root.parent/'task-11'
for name in ('native','installed'):
    verify_inventory(root/name)
    assert (name+'/sha256.json') in inventory(root)
verify_inventory(old)
lock=Path('uv.lock').read_bytes(); export=(root/'installed/requirements.txt').read_text()
env=marker_environment(); cp=locked_requirements(lock,export,env)
pypy=locked_requirements(lock,export,dict(env,implementation_name='PyPy',platform_python_implementation='PyPy'))
assert len(cp)==21 and len(pypy)==19 and set(cp)-set(pypy)=={'cffi','pycparser'}
n=json.loads((root/'native/report.json').read_text()); i=json.loads((root/'installed/report.json').read_text())
assert n['exit']==i['exit']==0
assert i['source_equality']==package_inventory(Path('packages/sec-edgar-ingest/src'))
assert len(i['installed']['dependencies'])==22
assert i['transitive_mismatch_refusal']['transitive_mismatch_refused'] is True
exits=[json.loads(p.read_text()) for p in sorted((root/'native').rglob('worker-exit.json'))]
assert len(n['process_recovery'])==12 and all(r['exit']==0 and r['worker_exit']==91 for r in n['process_recovery'])
anchors=[str(p.relative_to(root)) for p in sorted((root/'native').rglob('obligation.json'))]
assert len(anchors)==2
print(json.dumps({'marker_environment':env,'cpython_dependencies':cp,'synthetic_pypy_dependencies':pypy,
 'native_inventory_files':len(inventory(root/'native')),'installed_inventory_files':len(inventory(root/'installed')),
 'source_inventory_files':len(i['source_equality']),'installed_import_root':i['installed']['import_root'],
 'native_worker_exit_records':exits,'native_process_recovery':n['process_recovery'],'native_repair_authority_paths':anchors,'lock':digest(Path('uv.lock')),'requirements':digest(root/'installed/requirements.txt'),
 'retained_task11_inventory_verified':True,'nested_manifests_in_outer_inventory':True,
 'transitive_mismatch_refusal':i['transitive_mismatch_refusal'],'all22_stage7_checks':'reserved/not_run'},sort_keys=True))
'''
assert json.loads((OUT/'orchestration-result.json').read_text())['errors']==[]
with (OUT/'finalization-method.py').open('x') as f: f.write(Path(__file__).read_text())
checks=json.loads(command('proof-contract-check',['uv','run','--offline','--frozen','--package','sec-edgar-ingest','python','-c',SCRIPT,str(OUT)]))
once(OUT/'verification-summary.json',checks)
command('parser-change-scope',['git','diff','--name-only','ca2c953e79100d6fd890c43b73de214777b22596','6528a4e7596ed55078cbe31892f448b3075773b3','--','packages/sec-edgar-ingest/src'])
suite=json.loads((OUT/'full-suite.json').read_text())
match=re.search(r'Ran (\d+) tests in ([\d.]+)s',suite['stderr']); assert suite['exit']==0 and match and suite['stderr'].rstrip().endswith('OK')
counts={'tests':int(match[1]),'unittest_seconds':float(match[2]),'command_seconds':suite['runtime_seconds']}
once(OUT/'suite-summary.json',counts)
command('final-runtime',['git','diff','--exit-code','6528a4e7596ed55078cbe31892f448b3075773b3','--','packages/sec-edgar-ingest','uv.lock','pyproject.toml'])
command('final-head',['git','rev-parse','HEAD'])
wheel=json.loads((OUT/'wheel-selection.json').read_text())
durable_lines=['# Corrected-runtime final verification refresh','',
 'Reviewed runtime code head: `6528a4e7596ed55078cbe31892f448b3075773b3`. Checkout bookkeeping HEAD changes are separately captured by periodic and final command records. All package source/tests, uv.lock and pyproject.toml matched the reviewed runtime throughout the single full-suite run. No implementation change or commit was performed by this verifier.', '',
 f"Required guarded suite: **{counts['tests']} unique tests PASS**, exit 0, unittest duration {counts['unittest_seconds']}s and command runtime {counts['command_seconds']:.3f}s. The targeted lock suite separately passed six tests; those are not added to the unique full-suite count. Exact argv/cwd, full stdout/stderr, exit and runtime are retained for every check.", '',
 '| Check | Exit | Runtime seconds |','| --- | --- | --- |']
for label in ('green','full-suite','build','help','backfill-help','daily-help','version','compile','whitespace','native-command','installed-command','proof-contract-check'):
    r=json.loads((OUT/(label+'.json')).read_text())
    durable_lines.append(f"| {label} | {r['exit']} | {r['runtime_seconds']:.3f} |")
durable_lines+=['',
 f"Native: all 12 real process-death points exited 91 and reopened checked completion passed; exact evidence inventory is {checks['native_inventory_files']} files. Two original-call repair authority anchors, immutable report/pointer behavior and actual backfill/daily/legacy/reader captures are retained. Installed: exact evidence inventory is {checks['installed_inventory_files']} files; all {checks['source_inventory_files']} package files match reviewed source, fresh explicitly selected wheel and isolated installed bytes. Import root: `{checks['installed_import_root']}`.", '',
 'Complete applicable lock proof: 21 active CPython dependencies plus sec-edgar-ingest 0.1.0. Synthetic PyPy evaluation has 19 dependencies, excluding exactly cffi and pycparser. Live disposable installed urllib3 metadata changed to 2.7.0 was refused; all direct pins remained intact and the accepted urllib3 is 2.8.0. Accepted lock hash: `'+checks['lock']['sha256']+'`; fresh frozen export hash: `'+checks['requirements']['sha256']+'`.', '',
 'Fresh selected wheel and matching sdist were retained immediately after the successful required offline build, before installed proof. Distribution metadata is sec-edgar-ingest 0.1.0. Explicit selected wheel: `'+wheel['wheel']+'`. Artifact signatures:', '', '```json',json.dumps(wheel['artifacts'],indent=2,sort_keys=True),'```','',
 'Methods: verification-method.py retains asynchronous subprocess orchestration, separate full stdout/stderr streams, offline frozen command templates and 30-second HEAD/runtime checks. finalization-method.py retains exact graph/package/proof/manifest assertions. Every proof child command retains its own exact argv/cwd/output/exit/runtime. Installation uses existing Stage 2 cached wheels and cached PyArrow 25.0.1, copied into a fresh external disposable venv with -I, no PYTHONPATH, frozen actual lock export, hash requirements and a fixed copied test-only harness. No fetch or pin change occurred.', '',
 'Exact inventories exclude only each inventory’s own full path, include nested sha256.json files, and verify exact membership and bytes. The complete root inventory is generated last; its final count/hash are in the external .sdd final-verification-refresh-report.md so this report is itself retained in the manifest without self-reference. Original Task 11 evidence was compared byte-and-membership exactly before/after and its existing complete manifest verified unchanged.', '',
 'Original SEC-0141/0142/0143 entire-source refusal/specimen evidence remains applicable and was not rerun. Conflicts remain 21/24/6 with original raw hashes retained in task-11/verification-summary.json. Parser/transform runtime is unchanged from original Task 11; only workflows/results.py and workflows/runner.py differ in corrected production source. No original refusal execution is represented as freshly run.', '',
 'Scope limits: this evidence supplies technical checks and actual fixture coverage only. Owner actual coverage approval, controller evidence review and known absent former planning checkout disposition remain separate gates. Controller separately reports physical preservation of 138,438 records and 28,873 blobs at bookkeeping commit de05280a. No integration, historical-range or deployed-capacity claim follows. All 22 Stage 7 checks remain reserved/not_run; no network/provider/live/deploy/merge/push/cleanup or schedule activation occurred. Evidence is uncommitted for controller review and explicit staging.','']
with (OUT/'refresh-report.md').open('x') as f: f.write('\n'.join(durable_lines))
INVENTORY_SCRIPT='''import json,sys
from pathlib import Path
sys.path.insert(0,'packages/sec-edgar-ingest/tests')
from locked_proof import inventory,verify_inventory,digest
root=Path(sys.argv[1]); saved=inventory(root)
with (root/'sha256.json').open('x') as f: json.dump(saved,f,indent=2,sort_keys=True); f.write('\\n')
verify_inventory(root)
for child in ('native','installed'): verify_inventory(root/child)
print(json.dumps({'exact_outer_inventory_files':len(saved),'sha256_manifest':digest(root/'sha256.json'),'native':len(inventory(root/'native')),'installed':len(inventory(root/'installed')),'nested_manifests_included':[key for key in saved if key.endswith('/sha256.json')]}))
'''
# Inventory command result lives outside the inventoried root so it cannot change membership after verification.
argv=['uv','run','--offline','--frozen','--package','sec-edgar-ingest','python','-c',INVENTORY_SCRIPT,str(OUT)]
start=time.monotonic(); p=subprocess.run(argv,cwd=ROOT,env=ENV,capture_output=True,text=True)
record={'argv':argv,'cwd':str(ROOT),'stdout':p.stdout,'stderr':p.stderr,'exit':p.returncode,'runtime_seconds':time.monotonic()-start}
assert p.returncode==0,p.stderr
inventory_result=json.loads(p.stdout)
lines=['# Final verification refresh report','',
 'Scope: authorized final verification only, after independently accepted whole-branch corrections. No runtime or test implementation edits, commit, merge, push, cleanup or live actions occurred. Reviewed runtime commit: `6528a4e7596ed55078cbe31892f448b3075773b3`; starting checkout HEAD: `cea1ef2542e6e9d7ef5e7eeae34c616ed8557960` (controller evidence bookkeeping). Periodic and final exact git diffs confirmed package source/tests, uv.lock and pyproject.toml equal reviewed runtime throughout verification. All 22 Stage 7 checks remain reserved/not_run.','',
 '## Fresh checks','',f"The required guarded full suite ran exactly once: **{counts['tests']} tests PASS**, exit 0; unittest duration **{counts['unittest_seconds']} seconds**, command duration **{counts['command_seconds']:.3f} seconds**. Full stdout/stderr, exact argv/cwd, exit and runtime are retained in `full-suite.json` and raw streams. Targeted lock tests also passed. The required build, root/backfill/daily help, module version, compile and whitespace commands all passed with exit 0; each exact command record is retained.", '',
 'The orchestration retained its method and streamed outputs, ran the suite independently of build/command/proof checks, built before selecting distributions, and checked runtime identity every 30 seconds. Native and installed proofs ran against fresh create-only outputs. `native-command.json` and `installed-command.json` retain exact paths and command runtime. Every subprocess created by the proof harness retains its own argv/cwd/stdout/stderr/exit/runtime evidence.', '',
 f"Installed proof: {len(checks['cpython_dependencies'])} active CPython dependencies plus sec-edgar-ingest 0.1.0; synthetic PyPy graph has {len(checks['synthetic_pypy_dependencies'])} dependencies and excludes exactly cffi and pycparser. All {checks['source_inventory_files']} production files match reviewed source, selected wheel and actual isolated installed bytes. Actual import root: `{checks['installed_import_root']}`. Live disposable installed urllib3 2.7.0 metadata mismatch was refused with direct pins unchanged; expected urllib3 is 2.8.0.", '',
 'Native proof retained all twelve real process-death worker exits 91 and successful reopened checked completion, with backfill/daily/legacy/reader sequence evidence and two original-call repair authority anchors. The harness asserts immutable historical report/pointer behavior; its complete nested command and authority evidence remains included in the native and outer inventories. Task 5 missing-result terminal/error/failed history remains the accepted failure authority and is not represented as COMPLETE by successful recovery cases.', '',
 'The actual updated source was built with `uv build --offline --all-packages`; exact wheel and matching sdist are retained in `distributions/` before installed execution. Explicit wheel selection inspected the unique matching distribution filename and metadata, never an unchecked glob. `wheel-selection.json` records full SHA256s and sizes. The installed proof exported the actual frozen accepted lock afresh, installed PyArrow 25.0.1 from the existing uv offline cache and other requirements from retained Stage 2 wheels, and used copy linking, an external disposable venv, -I, no PYTHONPATH and a copied test-only harness. No fetch, pin change or dependency addition occurred.', '',
 '## Retained applicable evidence and exact inventories','',
 'SEC-0141/0142/0143 whole-source refusal and original specimen evidence was retained rather than rerun, as authorized. The runtime correction changes only workflows/results.py and workflows/runner.py; parser/transform runtime is unchanged from original Task 11. Original conflicts remain 21/24/6 with the accepted raw hashes documented in task-11/implementation-report.md and verification-summary.json. This refresh does not represent original source refusal execution as fresh execution.', '',
 f"Exact refreshed inventories passed native ({checks['native_inventory_files']} files), installed ({checks['installed_inventory_files']} files), and complete outer refresh ({inventory_result['exact_outer_inventory_files']} files). Each inventory excludes only its own full path, includes nested sha256.json manifests, and verifies exact membership plus bytes. Outer manifest SHA256: `{inventory_result['sha256_manifest']['sha256']}`. Retained original Task 11 evidence was byte-and-membership compared before/after and its original complete inventory independently verified unchanged.", '',
 '## Limits and ownership','',
 'This is verification evidence for the corrected runtime, not an integration or owner gate closure. Controller separately reports refreshed physical-preservation verification of 138,438 records and 28,873 blobs (bookkeeping commit de05280a); that audit is separate from these technical proofs. The known absent former planning checkout and its disposition remain unresolved. Owner coverage review and controller evidence review remain outside this report. No supported historical-range or deployed-capacity claim follows from offline success. No SEC/Azure/authentication/compute/provisioning/deployment/image-build or schedule activation occurred. Evidence and report are uncommitted and left for controller review and explicit staging.', '',
 '## Exact outer-inventory command evidence','',
 'The final inventory command output is embedded here, outside the inventoried root, to avoid changing the inventory after verification. All other checks have individual JSON evidence records.', '', '```json',json.dumps(record,indent=2,sort_keys=True),'```','']
report=ROOT/'.sdd/5-sec-filing-index-ingestion-stage-4-spec/final-verification-refresh-report.md'
with report.open('x') as f: f.write('\n'.join(lines))
print(json.dumps({'counts':counts,'inventories':inventory_result,'report':str(report)},indent=2))
