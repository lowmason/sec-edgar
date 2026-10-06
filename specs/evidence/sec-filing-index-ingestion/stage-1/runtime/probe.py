import importlib
import json
import platform
import sys
import sysconfig
from importlib.metadata import version
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

matrix = Path('/evidence/runtime/dependency-matrix.csv').read_text()
modules = ['azure.identity', 'azure.storage.blob', 'azure.data.tables']
if 'azure-storage-file-datalake,' in matrix:
    modules.append('azure.storage.filedatalake')
for module in modules:
    importlib.import_module(module)
direct = Path('/evidence/runtime/requirements.in').read_text().splitlines()
installed = {}
for line in direct:
    line = line.strip()
    if line and not line.startswith('#'):
        name, pin = line.split('==')
        assert version(name) == pin, (name, pin, version(name))
        installed[name] = pin
assert sys.version_info[:2] == (3, 14)
assert platform.machine() in ('x86_64', 'amd64'), platform.machine()
rows = pa.table({'probe_id': [1, 2], 'text': ['SEC', 'café'],
                 'optional': pa.array([None, 'x'], type=pa.string())})
target = Path('/out/roundtrip.parquet')
pq.write_table(rows, target)
restored = pq.read_table(target)
assert restored.equals(rows)
print(json.dumps({'python': sys.version, 'machine': platform.machine(),
                  'abi': sysconfig.get_config_var('SOABI'),
                  'installed': installed, 'parquet_roundtrip': 'passed'}))
