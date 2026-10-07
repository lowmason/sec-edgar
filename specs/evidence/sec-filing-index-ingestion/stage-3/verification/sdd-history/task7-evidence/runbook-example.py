"""Exercise the documented saved-capture reader and post-CAS repair example."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import json
from sec_edgar_ingest.config import Settings
from sec_edgar_ingest.storage import open_stores
from sec_edgar_ingest.etl.reader import capture_quarter, read_quarter
from sec_edgar_ingest.etl.state import EtlState
from sec_edgar_ingest.etl.contracts import GenerationCapture
from sec_edgar_ingest.etl.publication import repair_publication
from etl_proof import save, metadata
base=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/verification/sequence/raw-sequence'
settings=Settings.from_mapping(json.loads((base/'config.json').read_text()))
store,objects,leases=open_stores(settings,base_path=base)
try:
    state=EtlState(store)
    capture=capture_quarter('2026Q4',objects,state)
    if capture is None: raise RuntimeError('quarter has no published generation')
    saved=GenerationCapture.from_mapping(json.loads(json.dumps(capture.to_mapping())))
    rows=[row.to_mapping() for row in read_quarter(saved,objects)]
    pointer=state.pointer('2026Q4')
    repair_publication('2026Q4',objects,state)
    assert pointer==state.pointer('2026Q4')
    save(ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3/verification/runbook-proof.json',
         {**metadata(),'exit':0,'saved_capture':saved.to_mapping(),'rows':rows,'pointer_unchanged':True})
finally:
    leases.close(); store.close()
print('Saved capture validated, rows read, repair left pointer unchanged.')
