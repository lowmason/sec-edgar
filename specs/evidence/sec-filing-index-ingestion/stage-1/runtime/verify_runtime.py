"""Verify retained isolated compatibility outcomes; performs no network access."""
import csv
import hashlib
import json
import sys
from pathlib import Path

runtime = Path(__file__).resolve().parent
resolver = Path(sys.argv[1])
validations = [Path(arg) for arg in sys.argv[2:]]
assert len(validations) == 2 and validations[0].resolve() != validations[1].resolve()
selection = json.loads((runtime/'public-metadata/selection.json').read_text())
report = json.loads((resolver/'resolver-report.json').read_text())
packages = {item['metadata']['name'].lower().replace('_','-'):item for item in report['install']}
with (runtime/'dependency-matrix.csv').open(newline='') as stream:
    matrix = list(csv.DictReader(stream))
assert len(matrix) == len(packages)
for row in matrix:
    item = packages[row['distribution'].lower().replace('_','-')]
    assert row['version'] == item['metadata']['version']
    assert row['sha256'] == item['download_info']['archive_info']['hashes']['sha256']
    assert row['source_url'] == item['download_info']['url']
    assert row['artifact_filename'].endswith('.whl')
    assert (resolver/(row['artifact_filename']+'.WHEEL.txt')).is_file()
    assert (resolver/(row['artifact_filename']+'.METADATA.txt')).is_file()
lock = (runtime/'requirements.lock').read_text()
assert lock == (resolver/'requirements.lock').read_text()
for row in matrix:
    assert row['distribution']+'=='+row['version']+' --hash=sha256:'+row['sha256'] in lock
assert json.loads((resolver/'overall.json').read_text())['exit_code'] == 0
for result in [resolver,*validations]:
    exported = json.loads((result/'export-receipt.json').read_text())
    for name, expected in exported['artifacts'].items():
        assert hashlib.sha256((result/name).read_bytes()).hexdigest() == expected
checks = []
for result in validations:
    assert json.loads((result/'overall.json').read_text())['exit_code'] == 0
    commands = [json.loads(path.read_text()) for path in sorted(result.glob('*.command.json'))]
    assert commands and all(item['exit_code'] == 0 for item in commands)
    for name in ['install','pip-check','pip-inspect','pip-debug','core-probe','http-import','dependency-imports','decode-specimens']:
        assert (result/(name+'.command.json')).is_file()
    install = json.loads((result/'install.command.json').read_text())
    assert '--require-hashes' in install['args'] and '/evidence/runtime/requirements.lock' in install['args']
    environment = json.loads((result/'environment.json').read_text())
    assert environment['python'].startswith(selection['tag'].split(':')[-1].split('-')[0]+' ')
    assert environment['machine'] in ('x86_64','amd64')
    assert environment['abi'].startswith('cpython-314-')
    assert environment['libc'][0] == 'glibc'
    assert 'bookworm' in environment['os_release']
    inspect = json.loads((result/'pip-inspect.stdout.txt').read_text())
    installed = {item['metadata']['name'].lower().replace('_','-'):item['metadata']['version'] for item in inspect['installed']}
    for name,item in packages.items():
        assert installed[name] == item['metadata']['version']
    assert installed['pip'] == selection['pip']
    supported_tags = {line.strip() for line in (result/'pip-debug.stdout.txt').read_text().splitlines()}
    for row in matrix:
        assert set(row['wheel_tags'].split(';')) & supported_tags, row['distribution']
    imports = json.loads((result/'dependency-imports.stdout.txt').read_text())['offline_distribution_imports']
    assert {item['distribution'].lower().replace('_','-') for item in imports} == set(packages)
    assert all(item['result'] == 'passed' for item in imports)
    core = json.loads((result/'core-probe.stdout.txt').read_text())
    assert core['parquet_roundtrip'] == 'passed'
    parquet = (result/'roundtrip.parquet').read_bytes()
    assert parquet[:4] == parquet[-4:] == b'PAR1'
    decoded = json.loads((result/'decode-specimens.stdout.txt').read_text())['selected']
    source = json.loads((runtime.parent/'specimens/matrix.json').read_text())['matrix']
    assert len(decoded) == len(source) == 10
    for actual,expected in zip(decoded,source,strict=True):
        assert actual['evidence_id'] == expected['evidence_id']
        assert actual['original_sha256'] == expected['original_sha256']
        assert actual['decoded_sha256'] == (expected['derivative_sha256'] or expected['original_sha256'])
        assert actual['bytes'] == expected['expanded_bytes']
        assert actual['newline_counts'] == expected['newline_counts']
    inputs = json.loads((result/'input-verification.json').read_text())
    assert inputs['unchanged'] is True
    assert inputs['before_and_after_sha256']['runtime/requirements.lock'] == hashlib.sha256(lock.encode()).hexdigest()
    assert inputs['before_and_after_sha256']['runtime/base-image.json'] == hashlib.sha256((runtime/'base-image.json').read_bytes()).hexdigest()
    checks.append({'result_directory':str(result),'command_count':len(commands),'locked_distributions':len(packages),'selected_specimens':10,'environment':environment})
print(json.dumps({'result':'passed','resolver':str(resolver),'fresh_validations':checks,
                  'limits':'No Azure authentication/data access, production parser or worker capacity proof.'},indent=2))
