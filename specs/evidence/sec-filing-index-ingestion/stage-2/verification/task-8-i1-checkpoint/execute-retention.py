"""Capture actual retention exit and finalize only this new checkpoint's controls."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

root = Path.cwd().resolve()
checkpoint = Path(__file__).resolve().parent
bundle = root / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-k8g11etz'
argv = [sys.executable, str(checkpoint / 'retain-i1-proof.py')]
started = datetime.now(timezone.utc).isoformat()
result = subprocess.run(argv, capture_output=True, text=True)
receipt = checkpoint / 'retention-execution.json'
assert not receipt.exists()
receipt.write_text(json.dumps({'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'argv': argv, 'cwd': str(root), 'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode,
    'scope': 'Actual one-shot retention; initial printed manifest precedes adding this execution receipt to the finalized manifest.'}, indent=2, sort_keys=True) + '\n')
print(result.stdout, end='')
print(result.stderr, end='')
if result.returncode:
    raise SystemExit(result.returncode)


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


manifest_path = checkpoint / 'sha256-manifest.json'
inventory_path = checkpoint / 'evidence-inventory.json'
manifest = json.loads(manifest_path.read_text())
excluded = {manifest_path, inventory_path}
entries = [record(path) for directory in (checkpoint, bundle) for path in sorted(directory.rglob('*')) if path.is_file() and path not in excluded]
manifest['files'] = entries
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
inventory = json.loads(inventory_path.read_text())
prefix = checkpoint.relative_to(root).as_posix() + '/'
inventory.update({'covered_file_count': len(entries), 'covered_total_bytes': sum(item['bytes'] for item in entries),
    'new_checkpoint_covered_files': sum(item['path'].startswith(prefix) for item in entries),
    'new_checkpoint_covered_bytes': sum(item['bytes'] for item in entries if item['path'].startswith(prefix)),
    'manifest': record(manifest_path), 'retention_execution': record(receipt),
    'physical_checkpoint_file_count': sum(path.is_file() for path in checkpoint.rglob('*')),
    'physical_checkpoint_total_bytes': 0,
    'own_manifest_and_inventory_excluded_from_hash_coverage': True,
    'physical_byte_total_includes_both_excluded_controls': True})
other_bytes = sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file() and path != inventory_path)
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
assert sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file()) == inventory['physical_checkpoint_total_bytes']
namespace = runpy.run_path(str(checkpoint / 'retain-i1-proof.py'))
prior = namespace['verify_previous']()
assert prior == inventory['prior_checkpoint_manifest_records_verified_unchanged']
print(json.dumps({'exit_code': 0, 'final_manifest_sha256': record(manifest_path)['sha256'],
    'retention_map_sha256': record(checkpoint / 'retention-map.json')['sha256'],
    'covered_files': len(entries), 'covered_bytes': inventory['covered_total_bytes'],
    'physical_checkpoint_files': inventory['physical_checkpoint_file_count'],
    'physical_checkpoint_bytes': inventory['physical_checkpoint_total_bytes'],
    'combined_bundle_files': inventory['combined_bundle_files'], 'combined_bundle_bytes': inventory['combined_bundle_bytes'],
    'new_or_changed_sdd_files': inventory['new_or_changed_sdd_files'],
    'new_or_changed_sdd_bytes': inventory['new_or_changed_sdd_original_bytes'],
    'prior_records_verified_unchanged': sum(prior.values())}, sort_keys=True))
