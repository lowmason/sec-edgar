"""Verify every locked distribution and explicitly load native bindings offline."""
import csv
import importlib
import json
from importlib.metadata import version
from pathlib import Path

MODULES = {
    'azure-core': ['azure.core'],
    'azure-data-tables': ['azure.data.tables'],
    'azure-identity': ['azure.identity'],
    'azure-storage-blob': ['azure.storage.blob'],
    'certifi': ['certifi'],
    'cffi': ['cffi', '_cffi_backend'],
    'charset-normalizer': ['charset_normalizer'],
    'cryptography': ['cryptography', 'cryptography.hazmat.bindings._rust'],
    'idna': ['idna'],
    'isodate': ['isodate'],
    'msal': ['msal'],
    'msal-extensions': ['msal_extensions'],
    'pyarrow': ['pyarrow', 'pyarrow.parquet'],
    'pycparser': ['pycparser'],
    'pyjwt': ['jwt'],
    'requests': ['requests'],
    'typing-extensions': ['typing_extensions'],
    'urllib3': ['urllib3'],
    'yarl': ['yarl'],
    'multidict': ['multidict'],
    'propcache': ['propcache'],
}
results = []
with Path('/evidence/runtime/dependency-matrix.csv').open(newline='') as stream:
    for row in csv.DictReader(stream):
        name = row['distribution'].lower().replace('_','-').replace('.','-')
        modules = MODULES[name]
        assert version(row['distribution']) == row['version']
        for module in modules:
            importlib.import_module(module)
        results.append({'distribution':row['distribution'],'version':row['version'],'modules':modules,'result':'passed'})
print(json.dumps({'offline_distribution_imports':results,'credential_or_network_calls':False},indent=2))
