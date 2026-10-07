"""Capture actual final-fix retention exit and finalize only its new checkpoint controls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

root = Path.cwd().resolve()
checkpoint = Path(__file__).resolve().parent
argv = [sys.executable, str(checkpoint / 'retain-final-fix-proof.py')]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(argv, capture_output=True, text=True)
receipt = checkpoint / 'retention-execution.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'argv': argv, 'cwd': str(root), 'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode}, indent=2, sort_keys=True) + '\n')
print(result.stdout, end='')
print(result.stderr, end='')
if result.returncode:
    raise SystemExit(result.returncode)


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


namespace = runpy.run_path(str(checkpoint / 'retain-final-fix-proof.py'))
bundles = namespace['BUNDLES']
retained = json.loads((checkpoint / 'retention-result.json').read_text())
manifest_path = checkpoint / 'sha256-manifest.json'
inventory_path = checkpoint / 'evidence-inventory.json'
assert not manifest_path.exists() and not inventory_path.exists()
entries = [record(path) for directory in [checkpoint, *bundles] for path in sorted(directory.rglob('*'))
           if path.is_file() and path not in (manifest_path, inventory_path)]
manifest = {'schema_version': 'sec-final-review-fix1-sha256-v1', 'path_root': 'repository root',
    'source_base': namespace['BASE'], 'actual_source_proof_head': namespace['PROOF_HEAD'],
    'exclusions': [{'path': path.relative_to(root).as_posix(), 'reason': 'Own manifest/inventory excluded to prevent a self-hash cycle'}
                   for path in (manifest_path, inventory_path)], 'files': entries}
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
prefix = checkpoint.relative_to(root).as_posix() + '/'
inventory = {'schema_version': 'sec-final-review-fix1-inventory-v1', 'recorded_at': datetime.now(timezone.utc).isoformat(),
    **retained, 'covered_file_count': len(entries), 'covered_total_bytes': sum(item['bytes'] for item in entries),
    'new_checkpoint_covered_files': sum(item['path'].startswith(prefix) for item in entries),
    'new_checkpoint_covered_bytes': sum(item['bytes'] for item in entries if item['path'].startswith(prefix)),
    'manifest': record(manifest_path), 'retention_map': record(checkpoint / 'retention-map.json'),
    'retention_map_gzip': record(checkpoint / 'retention-map.json.gz'), 'retention_execution': record(receipt),
    'physical_checkpoint_file_count': sum(path.is_file() for path in checkpoint.rglob('*')) + 1,
    'physical_checkpoint_total_bytes': 0, 'own_manifest_and_inventory_excluded_from_hash_coverage': True,
    'physical_byte_total_includes_both_excluded_controls': True, 'fresh_scoped_Max_review': 'pending controller',
    'all22_s7_checks': 'reserved', 'no_stage2_stamp_tick_retirement_cleanup_integration': True}
other_bytes = sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file())
for _ in range(20):
    body = (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode()
    total = other_bytes + len(body)
    if inventory['physical_checkpoint_total_bytes'] == total:
        break
    inventory['physical_checkpoint_total_bytes'] = total
else:
    raise AssertionError('inventory byte count did not stabilize')
inventory_path.write_bytes(body)
for item in entries:
    assert record(root / item['path']) == item
assert sum(path.is_file() for path in checkpoint.rglob('*')) == inventory['physical_checkpoint_file_count']
assert sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file()) == inventory['physical_checkpoint_total_bytes']
assert namespace['verify_previous']() == retained['prior_checkpoint_manifest_records_verified_unchanged']
source_body = namespace['gzip'].decompress((checkpoint / 'sdd-source-inventory.json.gz').read_bytes())
assert namespace['snapshot_source']() == json.loads(source_body)
print(json.dumps({'stage': 'finalized_new_checkpoint', 'exit_code': 0, 'manifest_sha256': record(manifest_path)['sha256'],
    'retention_map_sha256': record(checkpoint / 'retention-map.json')['sha256'],
    'covered_files': len(entries), 'covered_bytes': inventory['covered_total_bytes'],
    'physical_checkpoint_files': inventory['physical_checkpoint_file_count'],
    'physical_checkpoint_bytes': inventory['physical_checkpoint_total_bytes'],
    'new_or_changed_sdd_files': retained['new_or_changed_sdd_files'],
    'original_sdd_bytes': retained['new_or_changed_sdd_original_bytes'],
    'retained_sdd_bytes': retained['new_or_changed_sdd_retained_bytes'],
    'prior_records_verified_unchanged': sum(retained['prior_checkpoint_manifest_records_verified_unchanged'].values())}, sort_keys=True))
