import json,pathlib
import importlib.metadata
from locked_proof import marker_environment,locked_requirements,installed_inventory,assert_inventory
root=pathlib.Path(__file__).parent
expected=locked_requirements((root/'accepted-uv.lock').read_bytes(),
    (root/'requirements.txt').read_text(),marker_environment())
distribution=importlib.metadata.distribution('urllib3')
metadata_files=[path for path in distribution.files if str(path).endswith('.dist-info/METADATA')]
if len(metadata_files)!=1: raise ValueError('urllib3 metadata file not unique')
metadata=pathlib.Path(distribution.locate_file(metadata_files[0]))
body=metadata.read_text()
old='Version: '+expected['urllib3']+'\n'
if body.count(old)!=1: raise ValueError('urllib3 metadata does not have exact original version')
metadata.write_text(body.replace(old,'Version: 2.7.0\n'))
actual=installed_inventory()
for name in ('pyarrow','requests','azure-identity','azure-storage-blob','azure-data-tables'):
    if actual[name]!=expected[name]: raise ValueError('negative test changed a direct pin')
version=json.loads((root/'expected-distribution.json').read_text())['version']
try: assert_inventory(expected,actual,version)
except ValueError as error: print(json.dumps({'transitive_mismatch_refused':True,'error':str(error)}))
else: raise AssertionError('wrong transitive version accepted')
