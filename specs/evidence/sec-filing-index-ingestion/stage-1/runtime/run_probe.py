"""Bounded ACR investigation launcher; exports evidence even on failure."""
import base64
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import sysconfig
import tarfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

OUT = Path('/out')
EVIDENCE = Path('/evidence')
RUNTIME = EVIDENCE / 'runtime'
OUT.mkdir(exist_ok=True)

def command(name, args):
    started = datetime.now(timezone.utc).isoformat()
    timed_out = False
    try:
        result = subprocess.run(args, capture_output=True, timeout=1200, env={**os.environ, 'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_CACHE_DIR': '1'})
    except subprocess.TimeoutExpired as error:
        timed_out = True
        result = subprocess.CompletedProcess(args, 124, stdout=error.stdout or b'', stderr=error.stderr or b'')
    (OUT / (name + '.stdout.txt')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(result.stderr)
    (OUT / (name + '.command.json')).write_text(json.dumps({'args': args, 'started_utc': started,
        'ended_utc': datetime.now(timezone.utc).isoformat(), 'exit_code': result.returncode, 'timed_out':timed_out}, indent=2)+'\n')
    assert result.returncode == 0, (name, result.returncode)

def verify_inputs():
    manifest = json.loads((EVIDENCE / 'input-hashes.json').read_text())
    for relative, expected in manifest.items():
        assert hashlib.sha256((EVIDENCE / relative).read_bytes()).hexdigest() == expected, relative
    return manifest

def resolve():
    command('resolve', [sys.executable, '-m', 'pip', 'install', '--dry-run', '--ignore-installed', '--only-binary=:all:',
                        '--report', str(OUT / 'resolver-report.json'), '-r', str(RUNTIME / 'requirements.in')])
    report = json.loads((OUT / 'resolver-report.json').read_text())
    records = []
    pins = []
    for item in report['install']:
        metadata = item['metadata']
        download = item['download_info']
        sha = download['archive_info']['hashes']['sha256']
        pins.append(metadata['name']+'=='+metadata['version']+' --hash=sha256:'+sha)
        records.append((item, sha))
    lock = OUT / 'requirements.lock'
    lock.write_text('\n'.join(sorted(pins, key=str.lower))+'\n')
    wheelhouse = Path('/tmp/probe-wheelhouse')
    command('download', [sys.executable, '-m', 'pip', 'download', '--only-binary=:all:', '--require-hashes',
                         '--dest', str(wheelhouse), '-r', str(lock)])
    columns = ['distribution','version','direct_or_transitive','requires_python','artifact_filename','wheel_tags','sha256','source_url','install_result','import_result','limitation']
    with (OUT / 'dependency-matrix.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item, sha in records:
            metadata = item['metadata']
            matches = [path for path in wheelhouse.iterdir() if hashlib.sha256(path.read_bytes()).hexdigest() == sha]
            assert len(matches) == 1, (metadata['name'], matches)
            wheel = matches[0]
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                wheel_name = next(name for name in names if name.endswith('.dist-info/WHEEL'))
                metadata_name = next(name for name in names if name.endswith('.dist-info/METADATA'))
                wheel_text = archive.read(wheel_name).decode('utf-8')
                (OUT / (wheel.name+'.WHEEL.txt')).write_text(wheel_text)
                (OUT / (wheel.name+'.METADATA.txt')).write_bytes(archive.read(metadata_name))
            writer.writerow(dict(zip(columns, [metadata['name'], metadata['version'], 'direct' if item['requested'] else 'transitive',
                metadata.get('requires_python',''), wheel.name, ';'.join(line[5:] for line in wheel_text.splitlines() if line.startswith('Tag: ')),
                sha, item['download_info']['url'], 'resolved/downloaded only; fresh install pending', 'pending', 'exact selected wheel only; no source build'])))

def validate():
    command('install', [sys.executable,'-m','pip','install','--require-hashes','--only-binary=:all:','-r',str(RUNTIME/'requirements.lock')])
    command('pip-check', [sys.executable,'-m','pip','check'])
    command('pip-inspect', [sys.executable,'-m','pip','inspect'])
    command('pip-debug', [sys.executable,'-m','pip','debug','--verbose'])
    command('core-probe', [sys.executable,str(RUNTIME/'probe.py')])
    command('http-import', [sys.executable,'-c','import requests; print(requests.__version__)'])
    command('dependency-imports', [sys.executable,str(RUNTIME/'import_dependencies.py')])
    matrix = json.loads((EVIDENCE/'specimens/matrix.json').read_text())
    for entry in matrix['matrix']:
        if entry['derivative_sha256']:
            command(entry['evidence_id']+'-zip-test', [sys.executable,'-m','zipfile','-t',str(EVIDENCE/'specimens'/(entry['original_sha256']+'.zip'))])
    command('decode-specimens', [sys.executable,str(RUNTIME/'decode_specimens.py'),str(EVIDENCE/'specimens')])

exit_code = 1
try:
    inputs = verify_inputs()
    assert sys.version_info[:2] == (3,14)
    assert platform.machine() in ('x86_64','amd64')
    (OUT/'environment.json').write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),
        'abi':sysconfig.get_config_var('SOABI'),'libc':platform.libc_ver(), 'os_release':Path('/etc/os-release').read_text(),
        'method':'ACR COPY inputs chmod read-only; no host bind; native Azure amd64 requested; no production performance claim'},indent=2)+'\n')
    command('bootstrap-pip', [sys.executable,'-m','pip','install','--require-hashes','--no-deps','-r',str(RUNTIME/'installer.lock')])
    command('pip-version', [sys.executable,'-m','pip','--version'])
    if sys.argv[1] == 'resolve':
        resolve()
    else:
        validate()
    assert verify_inputs() == inputs
    (OUT/'input-verification.json').write_text(json.dumps({'before_and_after_sha256':inputs,'unchanged':True},indent=2)+'\n')
    exit_code = 0
except Exception:
    (OUT/'failure.txt').write_text(traceback.format_exc())
finally:
    (OUT/'overall.json').write_text(json.dumps({'exit_code':exit_code,'ended_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as bundle:
        for path in sorted(OUT.iterdir()):
            if path.is_file():
                bundle.add(path, arcname=path.name)
    body = buffer.getvalue()
    assert len(body) <= 4 * 1024 * 1024, 'Evidence export exceeds 4MiB bound'
    encoded = base64.b64encode(body).decode('ascii')
    chunks = [encoded[offset:offset+4096] for offset in range(0,len(encoded),4096)]
    digest = hashlib.sha256(body).hexdigest()
    print('TASK4_BEGIN '+json.dumps({'bytes':len(body),'sha256':digest,'encoding':'tar.gz/base64','chunks':len(chunks)}),flush=True)
    for index, chunk in enumerate(chunks):
        print('TASK4_CHUNK '+str(index)+' '+chunk,flush=True)
    print('TASK4_END '+digest,flush=True)
sys.exit(exit_code)
