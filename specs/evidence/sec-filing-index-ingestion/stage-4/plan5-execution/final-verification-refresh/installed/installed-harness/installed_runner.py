from network_guard import install
install()
import json,pathlib,hashlib,sys
from locked_proof import marker_environment,locked_requirements,installed_inventory,assert_inventory,inventory,package_inventory
root=pathlib.Path(__file__).parent
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(), marker_environment())
version=json.loads((root/'expected-distribution.json').read_text())['version']
actual=installed_inventory()
assert_inventory(expected,actual,version)
import sec_edgar_ingest
if sec_edgar_ingest.__version__ != version: raise ValueError('installed module version differs from reviewed distribution')
base=pathlib.Path(sec_edgar_ingest.__file__).resolve().parent.parent
if 'site-packages' not in base.parts: raise ValueError('production import escaped isolated site-packages')
sources=json.loads((root/'expected-sources.json').read_text())
actual_sources=package_inventory(base)
if set(actual_sources)!=set(sources): raise ValueError('installed source inventory differs')
if actual_sources!=sources: raise ValueError('installed source bytes differ')
from workflow_proof import sequence
output=pathlib.Path(sys.argv[1]); output.mkdir(exist_ok=False)
report=sequence(output)
print(json.dumps({'import_root':str(base),'dependencies':actual,
    'applicable_lock':expected,'source_equality':sources,'sequence':report},sort_keys=True))
