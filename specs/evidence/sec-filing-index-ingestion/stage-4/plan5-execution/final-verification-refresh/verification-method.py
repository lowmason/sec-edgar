import asyncio, hashlib, json, os, shutil, time, zipfile
from email.parser import Parser
from pathlib import Path

ROOT=Path('/Users/lowell/.codex/worktrees/sec-edgar-stage4-plan5/sec-edgar')
OUT=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-4/plan5-execution/final-verification-refresh'
OLD=OUT.parent/'task-11'
BASE='6528a4e7596ed55078cbe31892f448b3075773b3'
ENV=dict(os.environ, UV_PYTHON_DOWNLOADS='never', PYTHONDONTWRITEBYTECODE='1')
ENV.pop('PYTHONPATH',None)
def once(path,value):
    with path.open('x') as f: json.dump(value,f,indent=2,sort_keys=True); f.write('\n')
def digest(path):
    body=path.read_bytes(); return {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
def inventory(root):
    return {str(p.relative_to(root)):digest(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'sha256.json'}
async def command(label,argv,cwd=ROOT):
    start=time.monotonic()
    with (OUT/(label+'.stdout')).open('xb') as so, (OUT/(label+'.stderr')).open('xb') as se:
        p=await asyncio.create_subprocess_exec(*map(str,argv),cwd=cwd,env=ENV,stdout=so,stderr=se)
        code=await p.wait()
    record={'argv':list(map(str,argv)),'cwd':str(cwd),'exit':code,'runtime_seconds':time.monotonic()-start,
      'stdout':(OUT/(label+'.stdout')).read_text(errors='backslashreplace'),
      'stderr':(OUT/(label+'.stderr')).read_text(errors='backslashreplace'),
      'environment_overrides':{'UV_PYTHON_DOWNLOADS':'never','PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':None}}
    once(OUT/(label+'.json'),record)
    print(label+' exit='+str(code)+' seconds='+str(round(record['runtime_seconds'],3)),flush=True)
    if code: raise RuntimeError(label+' failed')
    return record
async def integrity(label):
    await command(label+'-head',['git','rev-parse','HEAD'])
    await command(label+'-runtime',['git','diff','--exit-code',BASE,'--','packages/sec-edgar-ingest','uv.lock','pyproject.toml'])
async def other_checks():
    for label in ('green','build','help','backfill-help','daily-help','version','compile','whitespace'):
        await command(label,json.loads((OLD/(label+'.json')).read_text())['argv'])
        if label=='build':
            distribution=OUT/'distributions'; distribution.mkdir()
            expected=('sec_edgar_ingest-0.1.0-py3-none-any.whl','sec_edgar_ingest-0.1.0.tar.gz')
            wheels=list((ROOT/'dist').glob('sec_edgar_ingest-*.whl'))
            if [p.name for p in wheels]!=[expected[0]]: raise ValueError('ambiguous wheel selection')
            for name in expected:
                with (distribution/name).open('xb') as f: f.write((ROOT/'dist'/name).read_bytes())
            selected=distribution/expected[0]
            with zipfile.ZipFile(selected) as z:
                names=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
                assert len(names)==1
                meta=Parser().parsestr(z.read(names[0]).decode())
            assert meta['Name']=='sec-edgar-ingest' and meta['Version']=='0.1.0'
            once(OUT/'wheel-selection.json',{'method':'successful exact required build; explicit matching filenames; retained immutable copies before proof',
              'wheel':str(selected),'metadata':{'Name':meta['Name'],'Version':meta['Version']},'artifacts':inventory(distribution)})
    native=json.loads((OLD/'native-command.json').read_text())['argv']; native[-1]=str(OUT/'native')
    installed=json.loads((OLD/'installed-command.json').read_text())['argv']
    installed[installed.index('--output')+1]=str(OUT/'installed')
    installed[installed.index('--wheel')+1]=str(OUT/'distributions/sec_edgar_ingest-0.1.0-py3-none-any.whl')
    await asyncio.gather(command('native-command',native),command('installed-command',installed))
async def monitor(tasks):
    index=0
    while any(not t.done() for t in tasks):
        await integrity('integrity-%03d'%index); index+=1
        await asyncio.sleep(30)
async def main():
    OUT.mkdir(exist_ok=False)
    shutil.copyfile(__file__,OUT/'verification-method.py')
    once(OUT/'retained-task11-before.json',inventory(OLD))
    await integrity('preflight')
    full=json.loads((OLD/'full-suite.json').read_text())['argv']
    tasks=[asyncio.create_task(command('full-suite',full)),asyncio.create_task(other_checks())]
    monitoring=asyncio.create_task(monitor(tasks))
    results=await asyncio.gather(*tasks,return_exceptions=True)
    monitoring.cancel()
    try: await monitoring
    except asyncio.CancelledError: pass
    await integrity('postflight')
    before=json.loads((OUT/'retained-task11-before.json').read_text())
    after=inventory(OLD)
    once(OUT/'retained-task11-after.json',after)
    assert before==after,'retained evidence changed'
    once(OUT/'orchestration-result.json',{'errors':[str(r) for r in results if isinstance(r,BaseException)],'retained_task11_exact_equal':True,'all22_stage7_checks':'reserved/not_run'})
    if any(isinstance(r,BaseException) for r in results): raise RuntimeError('verification failure; no rerun')
asyncio.run(main())
