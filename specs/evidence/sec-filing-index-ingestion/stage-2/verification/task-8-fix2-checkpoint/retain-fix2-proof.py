"""One-shot append-only retention for Task 8 fix2 at its frozen source BASE."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = '35b47692168677acbe0410a33fc758d6d569a7a4'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = Path(__file__).resolve().parent
FIX1 = VERIFICATION / 'task-8-fix1-checkpoint'
INSTALLED = VERIFICATION / 'sec-edgar-wheel-1k5klfr3'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def record(path):
    body = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(body), 'sha256': sha(body)}


def save(name, value):
    path = CHECKPOINT / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def verify_previous():
    counts = {}
    anchors = [(VERIFICATION / 'sha256-manifest.json', '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926'),
               (FIX1 / 'sha256-manifest.json', 'dab1d3fafa0a558be4502fa9ea390d97d279f1f4b1c6f9f3c2bcdd67507247b3')]
    for path, expected in anchors:
        assert sha(path.read_bytes()) == expected
        data = json.loads(path.read_text())
        for item in data['files']:
            target = (VERIFICATION if path.parent == VERIFICATION else ROOT) / item['path']
            body = target.read_bytes()
            assert len(body) == item['bytes'] and sha(body) == item['sha256'], item['path']
        counts[path.relative_to(ROOT).as_posix()] = len(data['files'])
    for path in [VERIFICATION / 'evidence-inventory.json', FIX1 / 'evidence-inventory.json']:
        previous = subprocess.run(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'], capture_output=True, check=True).stdout
        assert path.read_bytes() == previous, path
    return counts


def main():
    assert ROOT == Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert head == BASE
    prior_counts = verify_previous()
    old_map = VERIFICATION / 'sdd-retention-map.json'
    fix1_map = FIX1 / 'retention-map.json'
    known = {item['path']: {'bytes': item['bytes'], 'sha256': item['sha256'], 'map': old_map.relative_to(ROOT).as_posix()} for item in json.loads(old_map.read_text())['files']}
    known.update({item['original_path']: {'bytes': item['original_bytes'], 'sha256': item['original_sha256'], 'map': fix1_map.relative_to(ROOT).as_posix()} for item in json.loads(fix1_map.read_text())['files']})
    originals = []
    all_current = set()
    unchanged = 0
    for path in sorted(SDD.rglob('*')):
        assert not path.is_symlink(), path
        if not path.is_file():
            continue
        relative = path.relative_to(SDD).as_posix()
        all_current.add(relative)
        body = path.read_bytes()
        previous = known.get(relative)
        if previous and previous['sha256'] == sha(body) and previous['bytes'] == len(body):
            unchanged += 1
            continue
        compressed = path.suffix == '.diff' and len(body) > 1024 * 1024
        destination = Path('sdd') / (relative + '.gz' if compressed else relative)
        retained = CHECKPOINT / destination
        retained.parent.mkdir(parents=True, exist_ok=True)
        assert not retained.exists()
        stored = gzip.compress(body, compresslevel=9, mtime=0) if compressed else body
        retained.write_bytes(stored)
        retrieved = gzip.decompress(retained.read_bytes()) if compressed else retained.read_bytes()
        assert retrieved == body
        item = {'original_path': relative, 'original_bytes': len(body), 'original_sha256': sha(body),
                'change': 'changed' if previous else 'new', 'retained_path': destination.as_posix(),
                'retained_bytes': len(stored), 'retained_sha256': sha(stored), 'encoding': 'gzip' if compressed else 'identity'}
        if previous:
            item['previous_sha256'] = previous['sha256']
            item['previous_retention_map'] = previous['map']
        if compressed:
            item['retrieval'] = {'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)}
        originals.append(item)
    assert not set(known) - all_current
    assert len(all_current) == unchanged + len(originals)
    required = {'task-8-report.md', 'task-8-fix1-rereview.md', 'task-8-fix2-brief.md', 'controller-task8-fix1-retention-inspection.json', 'controller-task8-fix2-check-inspection.json', 'task-8-fix2-guard-red.txt', 'task-8-fix2-guard-green.txt', 'task-8-fix2-final-check.txt'}
    assert required <= {item['original_path'] for item in originals}
    now = datetime.now(timezone.utc).isoformat()
    save('retention-map.json', {'schema_version': 'sec-task8-fix2-retention-v1', 'recorded_at': now, 'source_base': BASE,
        'original_root': str(SDD), 'retained_root': str(CHECKPOINT),
        'original_repository_relative_prefix': SDD.relative_to(ROOT).as_posix(), 'retained_repository_relative_prefix': CHECKPOINT.relative_to(ROOT).as_posix(),
        'lookup': 'Exact original_path matches select this current version; otherwise use the newest exact fix1 map, then the original map. Historical checkpoint references keep their original bytes.',
        'unchanged_fallback_maps_newest_first': [fix1_map.relative_to(ROOT).as_posix(), old_map.relative_to(ROOT).as_posix()],
        'current_source_file_count': len(all_current), 'unchanged_source_file_count': unchanged,
        'new_or_changed_source_file_count': len(originals), 'new_or_changed_original_bytes': sum(v['original_bytes'] for v in originals),
        'new_or_changed_retained_bytes': sum(v['retained_bytes'] for v in originals),
        'all_copied_or_decompressed_bytes_verified': True, 'exclusions': [], 'files': originals,
        'reused_installed_proof_root_map': (INSTALLED / 'retention-map.json').relative_to(ROOT).as_posix(),
        'reused_installed_proof_manifest': (INSTALLED / 'sha256-manifest.json').relative_to(ROOT).as_posix()})
    inspection = json.loads((SDD / 'task-8-fix2-proof-inspection.json').read_text())
    names = ['packages/sec-edgar-ingest/tests/network_guard.py', 'packages/sec-edgar-ingest/tests/test_network_guard.py',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification.md', 'conf/sec-edgar-ingest.yaml', 'pyproject.toml', 'uv.lock',
        'packages/sec-edgar-ingest/pyproject.toml', 'packages/sec-edgar-ingest/README.md',
        'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-report.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-fix1-rereview.md', '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-fix2-brief.md']
    save('source-revisions.json', {'recorded_at': now, 'source_base': BASE, 'actual_precommit_head': head,
        'candidate_file_hashes': [record(ROOT / name) for name in names],
        'production_source_hashes': inspection['production_source_hashes'],
        'all18_production_sources_equal_BASE_and_validated_wheel': True, 'artifacts': inspection['artifacts'],
        'current_check_log': record(SDD / 'task-8-fix2-final-check.txt'), 'reused_installed_summary': record(INSTALLED / 'wheel-proof-summary.json'),
        'fresh_install_rerun_needed': False, 'pending': ['fresh scoped I2 re-review', 'I1 owner answer and approved combined Step4', 'controller final whole-branch gates'],
        'no_future_commit_or_review_sha_claim': True})
    save('retention-assertions.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts, 'prior_inventory_controls_equal_BASE': True,
        'all_new_original_or_decompressed_bytes_verified': True, 'no_previous_checkpoint_or_primary_written': True,
        'no_current_sdd_deleted': True, 'reused_install_not_rerun_or_copied': True, 'no_recursive_copy_or_symlink': True,
        'scope': 'Retention assertions after actual test execution; no future scoped review or completion claim.'})
    entries = [record(path) for directory in (CHECKPOINT, INSTALLED) for path in sorted(directory.rglob('*')) if path.is_file()]
    manifest_path = CHECKPOINT / 'sha256-manifest.json'
    inventory_path = CHECKPOINT / 'evidence-inventory.json'
    save('sha256-manifest.json', {'schema_version': 'sec-task8-fix2-sha256-v1', 'path_root': 'repository root',
        'exclusions': [{'path': path.relative_to(ROOT).as_posix(), 'reason': 'Own manifest/inventory control excluded to prevent a self-hash cycle'} for path in (manifest_path, inventory_path)], 'files': entries})
    inventory = {'schema_version': 'sec-task8-fix2-inventory-v1', 'recorded_at': now, 'source_base': BASE,
        'covered_file_count': len(entries), 'covered_total_bytes': sum(v['bytes'] for v in entries),
        'new_checkpoint_covered_files': sum(v['path'].startswith(CHECKPOINT.relative_to(ROOT).as_posix() + '/') for v in entries),
        'new_checkpoint_covered_bytes': sum(v['bytes'] for v in entries if v['path'].startswith(CHECKPOINT.relative_to(ROOT).as_posix() + '/')),
        'reused_installed_proof_files': sum(v['path'].startswith(INSTALLED.relative_to(ROOT).as_posix() + '/') for v in entries),
        'reused_installed_proof_bytes': sum(v['bytes'] for v in entries if v['path'].startswith(INSTALLED.relative_to(ROOT).as_posix() + '/')),
        'reused_proof_already_tracked_not_new_copy': True, 'checkpoint_control_file_count': 2,
        'manifest': record(manifest_path), 'retention_map': record(CHECKPOINT / 'retention-map.json'),
        'new_or_changed_sdd_files': len(originals), 'new_or_changed_sdd_original_bytes': sum(v['original_bytes'] for v in originals),
        'new_or_changed_sdd_retained_bytes': sum(v['retained_bytes'] for v in originals),
        'changed_original_paths': [v['original_path'] for v in originals if v['change'] == 'changed'],
        'compressed_files': [v for v in originals if v['encoding'] == 'gzip'],
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts,
        'current_review': 'pending controller scoped I2 re-review', 'I1': 'owner answer pending; optional approved-daily sequence not executed', 'all_s7_checks': 'reserved'}
    save('evidence-inventory.json', inventory)
    for item in entries:
        assert record(ROOT / item['path']) == item
    assert verify_previous() == prior_counts
    print(json.dumps({key: inventory[key] for key in ('covered_file_count', 'covered_total_bytes', 'new_checkpoint_covered_files', 'new_checkpoint_covered_bytes', 'new_or_changed_sdd_files', 'new_or_changed_sdd_original_bytes', 'new_or_changed_sdd_retained_bytes', 'reused_installed_proof_files', 'reused_installed_proof_bytes')}, sort_keys=True))
    print(json.dumps({'manifest_sha256': sha(manifest_path.read_bytes()), 'retention_map_sha256': sha((CHECKPOINT / 'retention-map.json').read_bytes()),
        'prior_checkpoints': 'unchanged', 'compressed_files': [(v['original_path'], v['original_bytes'], v['retained_bytes']) for v in originals if v['encoding'] == 'gzip']}))


if __name__ == '__main__':
    main()
