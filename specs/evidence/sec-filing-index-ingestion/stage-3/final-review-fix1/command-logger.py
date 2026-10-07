"""Retain exact command outcome and native execution metadata without network."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
from etl_proof import metadata, save
import os, subprocess, time
output=Path(sys.argv[1]); output.mkdir(parents=True,exist_ok=False)
argv=sys.argv[2:]
started=time.monotonic()
env=dict(os.environ, UV_PYTHON_DOWNLOADS='never')
if argv==['scripts/check-sec-edgar-ingest.sh']:
    env['SEC_EDGAR_TASK7_PROCESS_PROOF']=str(output/'processes')
result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True)
(output/'stdout.txt').write_text(result.stdout)
(output/'stderr.txt').write_text(result.stderr)
save(output/'command.json',{**metadata(),'argv':argv,'cwd':str(ROOT),'exit':result.returncode,'runtime_seconds':time.monotonic()-started})
print(result.stdout[-1000:]); print(result.stderr[-1500:]); print('EXIT',result.returncode)
raise SystemExit(result.returncode)
