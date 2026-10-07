import sys
sys.path.insert(0, 'packages/sec-edgar-ingest/tests')
import network_guard
network_guard.install()
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from support import fixture_source
from support_etl import seed_snapshot, etl_context
from sec_edgar_ingest.etl.contracts import transformed_ref
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.transform import transform_workset
from sec_edgar_ingest.state import AcquisitionState

root = Path(__file__).parent / 'retained-artifacts'
body = (b'CIK|Company Name|Form Type|Date Filed|File Name\n-----\n'
        b'123456|Example Corp|10-K/A|20250825|edgar/data/123456/0000123456-25-000001.txt\n')
store, objects, origin = seed_snapshot(root, fixture_source('2026-09-30', 'daily'), body)
settings, context = etl_context()
path = f'worksets/sec/snapshot/sha256={origin.workset_id}/workset.json'
state, acquisition = EtlState(store), AcquisitionState(store)
class Crash(BaseException):
    pass

def crash(point):
    if point == 'transform.after_manifest':
        raise Crash(point)

try:
    try:
        transform_workset(path, context, settings, objects, state, acquisition, observer=crash)
    except Crash:
        pass
    assert list(store.scan('Processing', {})) == []
    with patch('sec_edgar_ingest.etl.transform.iter_observations', side_effect=AssertionError('reparse')):
        first = transform_workset(path, context, settings, objects, state, acquisition)
    assert first.complete
    again = transform_workset(path, context, settings, objects, state, acquisition, force=True)
    assert first == again
    ref = first.observations[0]
    identities = {}
    for name, artifact_path in {'raw': ref.snapshot.raw_path, 'observation': ref.rows_ref,
                               'observation_manifest': ref.manifest_ref, 'snapshot_workset': path,
                               'transformed_workset': transformed_ref(first)}.items():
        data = objects.read(artifact_path)
        identities[name] = {'path': artifact_path, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    proof = {'identities': identities, 'transformed_workset_id': first.workset_id,
             'manifest_repair_without_reparse': True, 'force_same_bytes': True,
             'accepted_processing_rows': len(list(store.scan('Processing', {}))),
             'observation': ref.to_mapping(), 'context': context.to_mapping()}
    (Path(__file__).parent / 'artifact-hashes.json').write_text(json.dumps(proof, indent=2))
    print(json.dumps(proof, indent=2))
finally:
    store.close()
