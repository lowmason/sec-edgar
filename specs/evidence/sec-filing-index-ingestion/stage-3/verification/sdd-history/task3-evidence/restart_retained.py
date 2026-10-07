import sys
sys.path.insert(0, 'packages/sec-edgar-ingest/tests')
import network_guard
network_guard.install()
import json
from pathlib import Path
from unittest.mock import patch
from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.models import RunContext
from sec_edgar_ingest.storage.local import LocalStateStore, LocalObjectStore
from sec_edgar_ingest.state import AcquisitionState
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.transform import transform_workset
base = Path(__file__).parent
proof = json.loads((base / 'artifact-hashes.json').read_text())
context = RunContext.from_mapping(proof['context'])
settings = Settings.from_mapping(context.to_mapping()['effective_config'])
store, objects = LocalStateStore(base / 'retained-artifacts'), LocalObjectStore(base / 'retained-artifacts')
try:
    with patch('sec_edgar_ingest.etl.transform.iter_observations', side_effect=AssertionError('reparse')):
        result = transform_workset(proof['identities']['snapshot_workset']['path'], context, settings,
                                   objects, EtlState(store), AcquisitionState(store))
    assert result.complete and result.workset_id == proof['transformed_workset_id']
    assert result.observations[0].to_mapping() == proof['observation']
    print(json.dumps({'restart_reused_exact_processing_and_workset': True, 'workset_id': result.workset_id,
                      'observation': result.observations[0].to_mapping()}, indent=2))
finally:
    store.close()
