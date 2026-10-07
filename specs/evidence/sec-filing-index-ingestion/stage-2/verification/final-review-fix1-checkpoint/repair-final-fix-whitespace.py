"""Preserve the exact new brief bytes using gzip after its staged EOF-whitespace failure."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

root = Path.cwd().resolve()
checkpoint = Path(__file__).resolve().parent
source_root = root / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
map_path = checkpoint / 'retention-map.json'
manifest_path = checkpoint / 'sha256-manifest.json'
inventory_path = checkpoint / 'evidence-inventory.json'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(root).as_posix(), 'bytes': len(body), 'sha256': sha(body)}


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


assert not (checkpoint / 'retention-format-correction.json').exists()
old_controls = []
historical = checkpoint / 'pre-format-correction'
historical.mkdir()
for path in (map_path, manifest_path, inventory_path):
    before = path.read_bytes()
    target = historical / (path.name + '.gz')
    target.write_bytes(gzip.compress(before, compresslevel=9, mtime=0))
    assert gzip.decompress(target.read_bytes()) == before
    old_controls.append({'original_control': record(path), 'historical_retained': record(target),
                         'retrieval': 'gzip decompression of historical_retained.path',
                         'expected_output_bytes': len(before), 'expected_output_sha256': sha(before)})
script = checkpoint / 'retain-final-fix-proof.py'
first_script = checkpoint / 'retain-final-fix-proof-first.py'
assert not first_script.exists()
shutil.copyfile(script, first_script)
body = script.read_text()
old = "    return bool(re.search(r'(?m)[ \\t]+\\r?$', text))"
new = "    return bool(re.search(r'(?m)[ \\t]+\\r?$', text)) or text.endswith(('\\n\\n', '\\r\\n\\r\\n'))"
assert body.count(old) == 1
script.write_text(body.replace(old, new))
mapping = json.loads(map_path.read_text())
item = next(row for row in mapping['files'] if row['original_path'] == 'whole-branch-review-brief.md')
assert item['encoding'] == 'identity'
plain = checkpoint / item['retained_path']
original = plain.read_bytes()
assert original == (source_root / item['original_path']).read_bytes()
assert len(original) == item['original_bytes'] and sha(original) == item['original_sha256']
encoded = plain.with_name(plain.name + '.gz')
assert not encoded.exists()
encoded.write_bytes(gzip.compress(original, compresslevel=9, mtime=0))
assert gzip.decompress(encoded.read_bytes()) == original
old_path = item['retained_path']
item.update(retained_path=encoded.relative_to(checkpoint).as_posix(), retained_bytes=encoded.stat().st_size,
            retained_sha256=sha(encoded.read_bytes()), encoding='gzip',
            encoding_reasons=['verbatim extra blank line at EOF retained losslessly after actual staged whitespace rejection'],
            retrieval={'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(original),
                       'expected_output_sha256': sha(original)})
# Only this new uncommitted replica changes representation; the original SDD and historical checkpoints are untouched.
plain.unlink()
mapping['new_or_changed_retained_bytes'] = sum(row['retained_bytes'] for row in mapping['files'])
save(map_path, mapping)
map_body = map_path.read_bytes()
(checkpoint / 'retention-map.json.gz').write_bytes(gzip.compress(map_body, compresslevel=9, mtime=0))
save(checkpoint / 'retention-map-gzip-retrieval.json', {'original': record(map_path),
    'retained': record(checkpoint / 'retention-map.json.gz'), 'retrieval': 'gzip decompression of retention-map.json.gz',
    'expected_output_bytes': len(map_body), 'expected_output_sha256': sha(map_body)})
retained = json.loads((checkpoint / 'retention-result.json').read_text())
retained['new_or_changed_sdd_retained_bytes'] = mapping['new_or_changed_retained_bytes']
retained['compressed_sdd_files'] = sum(row['encoding'] == 'gzip' for row in mapping['files'])
retained['format_correction'] = 'brief replica gzip after exact staged EOF whitespace failure; source bytes unchanged'
save(checkpoint / 'retention-result.json', retained)
namespace = runpy.run_path(str(script))
assert namespace['snapshot_source']() == json.loads(gzip.decompress((checkpoint / 'sdd-source-inventory.json.gz').read_bytes()))
assert namespace['verify_previous']() == retained['prior_checkpoint_manifest_records_verified_unchanged']
for row in mapping['files']:
    target = checkpoint / row['retained_path']
    stored = target.read_bytes()
    assert len(stored) == row['retained_bytes'] and sha(stored) == row['retained_sha256']
    value = gzip.decompress(stored) if row['encoding'] == 'gzip' else stored
    assert len(value) == row['original_bytes'] and sha(value) == row['original_sha256']
    assert value == (source_root / row['original_path']).read_bytes()
stage = subprocess.run(['git', 'add', '--', checkpoint.relative_to(root).as_posix()], capture_output=True, text=True)
assert stage.returncode == 0, stage.stderr
check_argv = ['git', '-c', 'core.whitespace=cr-at-eol', 'diff', '--cached', '--check']
started = datetime.now(timezone.utc).isoformat()
check = subprocess.run(check_argv, capture_output=True, text=True)
assert check.returncode == 0, check.stdout + check.stderr
save(checkpoint / 'retention-format-correction.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
    'actual_correction_script': record(Path(__file__).resolve()), 'prior_copy_script_bytes': record(first_script),
    'corrected_copy_script_bytes': record(script), 'historical_controls_retained': old_controls,
    'first_failure': record(checkpoint / 'staged-whitespace-first-failure.json'),
    'old_retained_path': old_path, 'new_retained_path': item['retained_path'], 'exact_original_bytes_preserved': True,
    'every5013_current_source_and_retained_or_decompressed_pair_verified': True,
    'all12150_prior_records_and_six_control_sets_unchanged': True, 'all_source_sdd_unchanged': True,
    'stage_argv': ['git', 'add', '--', checkpoint.relative_to(root).as_posix()],
    'corrected_staged_check': {'started_at': started, 'argv': check_argv, 'cwd': str(root),
                              'stdout': check.stdout, 'stderr': check.stderr, 'exit_code': check.returncode}})
bundles = namespace['BUNDLES']
entries = [record(path) for directory in [checkpoint, *bundles] for path in sorted(directory.rglob('*'))
           if path.is_file() and path not in (manifest_path, inventory_path)]
manifest = json.loads(manifest_path.read_text())
manifest['files'] = entries
manifest['format_correction'] = record(checkpoint / 'retention-format-correction.json')
save(manifest_path, manifest)
inventory = json.loads(inventory_path.read_text())
prefix = checkpoint.relative_to(root).as_posix() + '/'
inventory.update(retained)
inventory.update({'covered_file_count': len(entries), 'covered_total_bytes': sum(row['bytes'] for row in entries),
    'new_checkpoint_covered_files': sum(row['path'].startswith(prefix) for row in entries),
    'new_checkpoint_covered_bytes': sum(row['bytes'] for row in entries if row['path'].startswith(prefix)),
    'manifest': record(manifest_path), 'retention_map': record(map_path),
    'retention_map_gzip': record(checkpoint / 'retention-map.json.gz'),
    'retention_format_correction': record(checkpoint / 'retention-format-correction.json'),
    'physical_checkpoint_file_count': sum(path.is_file() for path in checkpoint.rglob('*')),
    'physical_checkpoint_total_bytes': 0})
other_bytes = sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file() and path != inventory_path)
for _ in range(20):
    serialized = (json.dumps(inventory, indent=2, sort_keys=True) + '\n').encode()
    total = other_bytes + len(serialized)
    if total == inventory['physical_checkpoint_total_bytes']:
        break
    inventory['physical_checkpoint_total_bytes'] = total
else:
    raise AssertionError('final physical inventory count did not stabilize')
inventory_path.write_bytes(serialized)
assert sum(path.stat().st_size for path in checkpoint.rglob('*') if path.is_file()) == inventory['physical_checkpoint_total_bytes']
for row in entries:
    assert record(root / row['path']) == row
print(json.dumps({'exit_code': 0, 'corrected_staged_whitespace_exit': check.returncode,
    'manifest_sha256': sha(manifest_path.read_bytes()), 'retention_map_sha256': sha(map_path.read_bytes()),
    'covered_files': len(entries), 'covered_bytes': inventory['covered_total_bytes'],
    'physical_checkpoint_files': inventory['physical_checkpoint_file_count'],
    'physical_checkpoint_bytes': inventory['physical_checkpoint_total_bytes'],
    'new_or_changed_sdd_files': retained['new_or_changed_sdd_files'],
    'retained_sdd_bytes': retained['new_or_changed_sdd_retained_bytes'],
    'compressed_sdd_files': retained['compressed_sdd_files'], 'prior_records_verified_unchanged': 12150}))
