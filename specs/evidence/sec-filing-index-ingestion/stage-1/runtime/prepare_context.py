"""Create an explicit bounded upload context after public pin selection."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

runtime = Path(__file__).resolve().parent
stage = runtime.parent
mode = sys.argv[1]
assert mode in ('resolve', 'validate')
context = Path(sys.argv[2])
assert str(context).startswith('/private/tmp/')
context.mkdir(exist_ok=False)
selection = json.loads((runtime/'public-metadata/selection.json').read_text())
if mode == 'resolve':
    direct = [('azure-identity',selection['azure-identity']),('azure-storage-blob',selection['azure-storage-blob']),
              ('azure-data-tables',selection['azure-data-tables']),('requests',selection['requests']),('pyarrow',selection['pyarrow'])]
    (runtime/'requirements.in').write_text('\n'.join(name+'=='+pin for name,pin in direct)+'\n')
    pip_metadata = json.loads((runtime/'public-metadata/pip.json').read_text())
    wheels = [item for item in pip_metadata['urls'] if item['filename'].endswith('-py3-none-any.whl')]
    assert len(wheels) == 1
    wheel = wheels[0]
    (runtime/'installer.lock').write_text('pip=='+selection['pip']+' --hash=sha256:'+wheel['digests']['sha256']+'\n')
    (runtime/'base-image.json').write_text(json.dumps({**selection,'base_reference':'docker.io/library/python@'+selection['child_digest'],
        'os_variant':'Debian bookworm slim','libc':'glibc; exact runtime value pending observed environment',
        'installer':{'name':'pip','version':selection['pip'],'wheel_url':wheel['url'],'sha256':wheel['digests']['sha256']},
        'registry':'Docker Hub official library/python','pull_authorization':'Public anonymous pull token in runtime memory; rate/availability limits still apply',
        'rollback_image':'No prior worker/release image exists or is published by this probe; base digest alone is not rollback deployment evidence',
        'datalake_omission':'Recorded operations use Blob content/conditions and Table entities; no DFS ACL/path rename/filesystem API operation selected',
        'requests_choice':'Synchronous SEC transport candidate; also required by Azure core. No async operations justify additional HTTP client dependencies.',
        'performance':'Native ACR Linux amd64 requested; no production worker fit or performance proof'},indent=2)+'\n')

files = ['run_probe.py','probe.py','decode_specimens.py','requirements.in','installer.lock','base-image.json']
if mode == 'validate':
    files += ['requirements.lock','dependency-matrix.csv','import_dependencies.py']
evidence = context/'evidence'
(evidence/'runtime').mkdir(parents=True)
for name in files:
    shutil.copyfile(runtime/name,evidence/'runtime'/name)
if mode == 'validate':
    (evidence/'specimens').mkdir()
    shutil.copyfile(stage/'specimens/matrix.json',evidence/'specimens/matrix.json')
    matrix = json.loads((stage/'specimens/matrix.json').read_text())
    for entry in matrix['matrix']:
        digest = entry['original_sha256']
        name = digest+('.zip' if entry['derivative_sha256'] else '.idx')
        original = stage/'specimens'/name
        assert hashlib.sha256(original.read_bytes()).hexdigest() == digest
        assert original.stat().st_size == entry['original_bytes']
        shutil.copyfile(original,evidence/'specimens'/name)
hashes = {str(path.relative_to(evidence)):hashlib.sha256(path.read_bytes()).hexdigest()
          for path in sorted(evidence.rglob('*')) if path.is_file()}
(evidence/'input-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
dockerfile = 'FROM docker.io/library/python@'+selection['child_digest']+'\n'
dockerfile += 'COPY evidence/ /evidence/\nRUN find /evidence -type f -exec chmod 0444 {} + && find /evidence -type d -exec chmod 0555 {} + && mkdir -p /out /tmp/probe-home && python -m venv /opt/probe-env && chown -R 1000:1000 /out /tmp/probe-home /opt/probe-env\n'
dockerfile += 'USER 1000:1000\nENV HOME=/tmp/probe-home PATH=/opt/probe-env/bin:$PATH\nRUN python /evidence/runtime/run_probe.py '+mode+'\n'
(context/'Dockerfile').write_text(dockerfile)
(context/'.dockerignore').write_text('*\n!Dockerfile\n!evidence/\n!evidence/**\n')
allowlist = {str(path.relative_to(context)):{'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
             for path in sorted(context.rglob('*')) if path.is_file()}
receipt = runtime/'results'/(context.name+'-allowlist.json')
receipt.write_text(json.dumps({'context':str(context),'mode':mode,'files':allowlist,'total_bytes':sum(item['bytes'] for item in allowlist.values()),
                             'no_credentials_packages_git_or_user_configs':True},indent=2)+'\n')
print(json.dumps({'context':str(context),'allowlist_receipt':str(receipt),'files':len(allowlist),'bytes':sum(item['bytes'] for item in allowlist.values())},indent=2))
