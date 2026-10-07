"""Independent M1 config/document validation; no pipeline execution or adapters."""
import sys
sys.path.insert(0,'packages/sec-edgar-ingest/tests')
from network_guard import install
install()
from pathlib import Path
import hashlib,json,platform,time
from sec_edgar_ingest.config import load_config,Settings
from sec_edgar_ingest.etl.parser import supported_parser
from sec_edgar_ingest.storage.contracts import deployment_binding
started=time.monotonic()
out=Path(__file__).parent
acquisition=Path('conf/sec-edgar-ingest.yaml')
etl=Path('conf/sec-edgar-etl-fixture.yaml')
def digest(path):
    body=path.read_bytes();return {'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
assert acquisition.read_bytes()==(out/'acquisition-config-before.yaml').read_bytes()
assert acquisition.read_bytes()==Path('/Users/lowell/Projects/sec-edgar/conf/sec-edgar-ingest.yaml').read_bytes()
original=load_config(acquisition); settings=load_config(etl)
assert isinstance(settings,Settings)
a=original.to_mapping(); b=settings.to_mapping()
assert a['etl']['parser_version']=='fixture-envelope-v1'
assert b['etl']['parser_version']=='fixture-index-parser-v1'
a['etl']['parser_version']=b['etl']['parser_version'];assert a==b
supported_parser(settings.etl.parser_version,fixture=settings.storage.backend=='local-fixture')
refusals=[]
for parser,fixture in [('fixture-envelope-v1',True),('fixture-index-parser-v1',False)]:
    try:supported_parser(parser,fixture=fixture)
    except ValueError as error:refusals.append({'parser':parser,'fixture':fixture,'reason':str(error)})
    else:raise AssertionError('unsupported parser was accepted')
supported_parser('sec-index-parser-v1',fixture=False)
root=Path.cwd()/settings.storage.root
assert deployment_binding(original,root=root)==deployment_binding(settings,root=root)
runbook=Path('docs/runbooks/sec-edgar-etl-publication.md').read_text()
assert runbook.count('--config conf/sec-edgar-etl-fixture.yaml')==2
assert "Path('conf/sec-edgar-etl-fixture.yaml').read_text()" in runbook
assert '--config conf/sec-edgar-ingest.yaml' not in runbook
record={'argv':sys.argv,'cwd':str(Path.cwd()),'python':sys.version,'platform':platform.platform(),
        'guard_installed':True,'exit':0,'runtime_seconds':time.monotonic()-started,
        'acquisition_before':digest(out/'acquisition-config-before.yaml'),'acquisition_after':digest(acquisition),
        'etl_file':digest(etl),'etl_config_sha256':settings.config_sha256,'parser':settings.etl.parser_version,
        'only_configuration_change':'etl.parser_version','same_deployment_binding':True,
        'actual_parser_refusals':refusals,'production_parser_accepted':True,
        'documented_transform_publish_execution':'pending code worker green/commit and explicit offline raw fixture seed',
        'all22_stage7_checks':'reserved'}
(out/'validation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
