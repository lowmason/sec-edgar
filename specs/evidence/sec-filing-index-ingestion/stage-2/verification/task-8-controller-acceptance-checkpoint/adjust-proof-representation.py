"""Retain diff context bytes losslessly without treating them as authored whitespace."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path.cwd().resolve()
checkpoint = Path(__file__).resolve().parent
source = root / '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-i1-authored-review.diff'
original_copy = checkpoint / 'sdd/task-8-i1-authored-review.diff'
compressed_copy = original_copy.with_name(original_copy.name + '.gz')
assert original_copy.read_bytes() == source.read_bytes()
assert not compressed_copy.exists()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(body), 'sha256': sha(body)}


def write_new(path, value):
    assert not path.exists()
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


started = datetime.now(timezone.utc).isoformat()
write_new(checkpoint / 'staging-whitespace-first-failure.json', {
    'recorded_at': started, 'historical_execution_time': 'not separately recorded',
    'argv': ['git', '-c', 'core.whitespace=cr-at-eol', 'diff', '--cached', '--check'], 'cwd': str(root),
    'stdout': 'specs/evidence/sec-filing-index-ingestion/stage-2/verification/task-8-controller-acceptance-checkpoint/sdd/task-8-i1-authored-review.diff:7: trailing whitespace.\n+ \n',
    'stderr': '', 'exit_code': 2,
    'cause': 'Exact retained Git diff has a blank context line containing a space. It is evidence, not a new source edit.',
    'correction': 'Losslessly gzip this copied diff with original/compressed hashes and retrieval mapping; keep original SDD and prior proofs unchanged.'})
body = source.read_bytes()
stored = gzip.compress(body, compresslevel=9, mtime=0)
compressed_copy.write_bytes(stored)
assert gzip.decompress(compressed_copy.read_bytes()) == body
map_path = checkpoint / 'retention-map.json'
previous_map = record(map_path)
retention_map = json.loads(map_path.read_text())
items = [item for item in retention_map['files'] if item['original_path'] == source.name]
assert len(items) == 1
item = items[0]
assert item['original_sha256'] == sha(body) and item['original_bytes'] == len(body)
item.update({'retained_path': compressed_copy.relative_to(checkpoint).as_posix(), 'retained_bytes': len(stored),
    'retained_sha256': sha(stored), 'encoding': 'gzip',
    'retrieval': {'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)},
    'representation_reason': 'Preserve original Git diff context whitespace as compressed evidence bytes.'})
retention_map['new_or_changed_retained_bytes'] = sum(value['retained_bytes'] for value in retention_map['files'])
map_path.write_text(json.dumps(retention_map, indent=2, sort_keys=True) + '\n')
# Remove only this new staged identity copy after its durable, verified replacement exists.
argv = ['git', 'rm', '--cached', '--', original_copy.relative_to(root).as_posix()]
r = subprocess.run(argv, capture_output=True, text=True)
assert r.returncode == 0, (r.stdout, r.stderr)
assert gzip.decompress(compressed_copy.read_bytes()) == original_copy.read_bytes() == source.read_bytes()
original_copy.unlink()
write_new(checkpoint / 'representation-adjustment.json', {'started_at': started,
    'finished_at': datetime.now(timezone.utc).isoformat(), 'argv': [sys.executable, str(Path(__file__).resolve())],
    'cwd': str(root), 'previous_retention_map': previous_map, 'current_retention_map': record(map_path),
    'original_source': record(source), 'compressed_retained_copy': record(compressed_copy),
    'retrieval': item['retrieval'], 'staging_argv': argv, 'staging_stdout': r.stdout, 'staging_stderr': r.stderr,
    'staging_exit_code': r.returncode, 'verified_before_removing_new_duplicate': True,
    'no_original_sdd_or_previous_checkpoint_or_production_change': True, 'exit_code': 0})
manifest_path = checkpoint / 'sha256-manifest.json'
inventory_path = checkpoint / 'evidence-inventory.json'
manifest = json.loads(manifest_path.read_text())
entries = [record(path) for path in sorted(checkpoint.rglob('*')) if path.is_file() and path not in {manifest_path, inventory_path}]
manifest['files'] = entries
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
inventory = json.loads(inventory_path.read_text())
inventory.update({'covered_file_count': len(entries), 'covered_total_bytes': sum(value['bytes'] for value in entries),
    'manifest': record(manifest_path), 'retention_map': record(map_path),
    'new_or_changed_sdd_retained_bytes': retention_map['new_or_changed_retained_bytes'],
    'compressed_files': [value for value in retention_map['files'] if value['encoding'] == 'gzip'],
    'representation_adjustment': record(checkpoint / 'representation-adjustment.json'),
    'physical_checkpoint_file_count': sum(path.is_file() for path in checkpoint.rglob('*')),
    'physical_checkpoint_total_bytes': 0})
other_bytes = sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file() and path != inventory_path)
for _ in range(20):
    serialized = (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode()
    total = other_bytes + len(serialized)
    if inventory['physical_checkpoint_total_bytes'] == total:
        break
    inventory['physical_checkpoint_total_bytes'] = total
else:
    raise AssertionError('inventory byte count did not stabilize')
inventory_path.write_bytes(serialized)
for value in entries:
    assert record(root / value['path']) == value
for value in retention_map['files']:
    data = (checkpoint / value['retained_path']).read_bytes()
    decoded = gzip.decompress(data) if value['encoding'] == 'gzip' else data
    assert len(decoded) == value['original_bytes'] and sha(decoded) == value['original_sha256']
    assert decoded == (source.parent / value['original_path']).read_bytes()
assert sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file()) == inventory['physical_checkpoint_total_bytes']
print(json.dumps({'exit_code': 0, 'physical_files': inventory['physical_checkpoint_file_count'],
    'physical_bytes': inventory['physical_checkpoint_total_bytes'], 'covered_files': len(entries),
    'covered_bytes': inventory['covered_total_bytes'], 'manifest_sha256': record(manifest_path)['sha256'],
    'retention_map_sha256': record(map_path)['sha256'], 'both_diff_originals_losslessly_retained': True}, sort_keys=True))
