"""Read-only chronology and exact-byte evidence timestamp correction check."""
import base64
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

patch_path = Path(__file__).with_name('timestamp-correction-patch.json')
patch = json.loads(patch_path.read_text())
manifest = Path(patch['manifest_path'])
digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
assert digest == patch['manifest_sha256_unchanged']
generated = json.loads(manifest.read_text())['generated_utc']
assert generated == patch['manifest_generated_utc']
assert datetime.fromisoformat(patch['fresh_observation_utc']) >= datetime.fromisoformat(generated)
old_index = Path(patch['retained_old_index']).read_bytes()
assert hashlib.sha256(old_index).hexdigest() == patch['expected_old_index_sha256']
old_raw = base64.b64decode(patch['old_row_raw_base64'], validate=True)
new_raw = base64.b64decode(patch['new_row_raw_base64'], validate=True)
assert old_index.count(old_raw) == 1
assert hashlib.sha256(old_raw).hexdigest() == patch['old_row_raw_sha256']
assert hashlib.sha256(new_raw).hexdigest() == patch['new_row_raw_sha256']
expected = old_index.replace(old_raw, new_raw, 1)
assert hashlib.sha256(expected).hexdigest() == patch['expected_new_index_sha256']
old_rows = list(csv.DictReader(old_index.decode().splitlines()))
new_rows = list(csv.DictReader(expected.decode().splitlines()))
changes = [(a['evidence_id'], key) for a,b in zip(old_rows,new_rows,strict=True) for key in a if a[key] != b[key]]
assert changes == [('E-T4-ARTIFACTS','accessed_or_received_at_utc')]
mode = sys.argv[1]
assert mode in ('--pre','--post')
current = Path(patch['target_index']).read_bytes()
assert current == (old_index if mode == '--pre' else expected)
if mode == '--post':
    row = next(item for item in csv.DictReader(current.decode().splitlines()) if item['evidence_id'] == patch['evidence_id'])
    assert row == patch['new_row'] and row['sha256'] == digest
    assert datetime.fromisoformat(row['accessed_or_received_at_utc']) >= datetime.fromisoformat(generated)
print(json.dumps({'result':'passed','mode':mode,'manifest_sha256_unchanged':digest,
    'manifest_generated_utc':generated,'fresh_documented_observation_utc':patch['fresh_observation_utc'],
    'changed_cells':changes,'old_index_sha256':patch['expected_old_index_sha256'],
    'expected_new_index_sha256':patch['expected_new_index_sha256'],'no_new_probe_or_manifest_generation':True},indent=2))
