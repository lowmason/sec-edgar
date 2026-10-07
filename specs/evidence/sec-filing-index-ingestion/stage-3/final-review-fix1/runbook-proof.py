"""Explicit offline fixture seed followed by the documented cli.main arguments."""
import sys
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
from etl_proof import save, digest, metadata, invoke, capture_evidence, inventory
from support import fixture_source
from support_etl import seed_snapshot
from sec_edgar_ingest.etl.contracts import decode_transformed
from sec_edgar_ingest.etl.state import EtlState
from datetime import datetime, timezone, timedelta
import subprocess

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=False)
acquisition = ROOT / 'conf/sec-edgar-ingest.yaml'
config = ROOT / 'conf/sec-edgar-etl-fixture.yaml'
original = acquisition.read_bytes()
(out / 'acquisition-config.json').write_bytes(original)
(out / 'etl-config.json').write_bytes(config.read_bytes())
body = b'CIK|Company Name|Form Type|Date Filed|File Name\n-----\n123456|Example|10-K|20261001|edgar/data/123456/0000123456-26-000001.txt\n'
source = fixture_source('2026-10-01', 'daily')
store, objects, snapshots = seed_snapshot(out / '.fixture-state', source, body)
reference = f'worksets/sec/snapshot/sha256={snapshots.workset_id}/workset.json'
snapshot_bytes = objects.read(reference)
raw = {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('master.idx')}
deadline = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
def argv(command, ref, attempt):
    return [command, '--config', 'conf/sec-edgar-etl-fixture.yaml', '--state-dir', str(out), '--run-id', 'replay-001', '--execution-id', 'local-001', '--attempt-id', attempt, '--deadline', deadline, '--workset', ref]
code, transformed = invoke(argv('transform', reference, 'transform-v1'), out, 'transform')
assert code == 0, transformed
workset = decode_transformed(objects.read(transformed['transformed_workset_ref']))
assert workset.origin_context.parser_version == 'fixture-envelope-v1'
assert workset.context.parser_version == 'fixture-index-parser-v1'
code, published = invoke(argv('publish', transformed['transformed_workset_ref'], 'publish-v1'), out, 'publish')
assert code == 0, published
capture = capture_evidence(objects, EtlState(store))
assert len(capture['rows']) == 1
assert capture['rows'][0]['cik'] == '0000123456'
assert acquisition.read_bytes() == original
assert objects.read(reference) == snapshot_bytes
assert raw == {p.relative_to(out).as_posix(): digest(p) for p in out.rglob('master.idx')}
records = {kind: [v.to_mapping() for v in store.scan(kind, {})] for kind in ('Attempt', 'Binding', 'Snapshot', 'Processing', 'QuarterPublication', 'PublicationReceipt', 'TransportAttempt')}
assert records['TransportAttempt'] == []
store.close()
save(out / 'report.json', {**metadata(), 'head': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(), 'guard_wrapper': 'network_guard.install before package imports; etl_proof.invoke calls actual cli.main while denying Coordinator, BoundedSender, RequestClient constructors', 'source': source.to_mapping(), 'snapshot_ref': reference, 'snapshot_workset': snapshots.to_mapping(), 'transformed_workset': workset.to_mapping(), 'raw_pins': raw, 'transform': transformed, 'publish': published, 'capture': capture, 'records': records, 'acquisition_config': digest(acquisition), 'etl_config': digest(config), 'acquisition_byte_equal': True, 'raw_byte_equal': True})
save(out / 'sha256.json', inventory(out))
print('Documented transform/publish exit 0; original provenance/raw preserved; captured one expected filing.')
