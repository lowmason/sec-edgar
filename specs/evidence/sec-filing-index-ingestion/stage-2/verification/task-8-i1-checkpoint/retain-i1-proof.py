"""One-shot mapped I1 proof checkpoint at the approved combined-sequence BASE."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = '49c50512202ca7950b222683776d8865b450b8b2'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = Path(__file__).resolve().parent
BUNDLE = VERIFICATION / 'sec-edgar-stage-2-k8g11etz'
INSTALLED = VERIFICATION / 'sec-edgar-wheel-1k5klfr3'
PRIOR = [
    (VERIFICATION, '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926', 'sdd-retention-map.json'),
    (VERIFICATION / 'task-8-fix1-checkpoint', 'dab1d3fafa0a558be4502fa9ea390d97d279f1f4b1c6f9f3c2bcdd67507247b3', 'retention-map.json'),
    (VERIFICATION / 'task-8-fix2-checkpoint', 'd156894ae7ec3a3e646dfdcba1e5946a35d09b80004ea7a3c8b791d65afa35ea', 'retention-map.json'),
    (VERIFICATION / 'task-8-controller-review-checkpoint', '29cc50fd9a83bd65761eace992cb342d75a23cb9e80cebd601ef097dfe55146d', 'retention-map.json'),
]


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
    for directory, expected, map_name in PRIOR:
        manifest = directory / 'sha256-manifest.json'
        assert sha(manifest.read_bytes()) == expected, manifest
        data = json.loads(manifest.read_text())
        for item in data['files']:
            target = (VERIFICATION if directory == VERIFICATION else ROOT) / item['path']
            body = target.read_bytes()
            assert len(body) == item['bytes'] and sha(body) == item['sha256'], target
        counts[manifest.relative_to(ROOT).as_posix()] = len(data['files'])
        for path in [manifest, directory / 'evidence-inventory.json', directory / map_name]:
            previous = subprocess.run(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'], capture_output=True, check=True).stdout
            assert path.read_bytes() == previous, path
    assert sum(counts.values()) == 12015
    return counts


def main():
    assert ROOT == Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert head == BASE
    prior_counts = verify_previous()
    known = {}
    maps = []
    for directory, _, map_name in PRIOR:
        path = directory / map_name
        maps.append(path.relative_to(ROOT).as_posix())
        for item in json.loads(path.read_text())['files']:
            if directory == VERIFICATION:
                name, byte_count, digest = item['path'], item['bytes'], item['sha256']
            else:
                name, byte_count, digest = item['original_path'], item['original_bytes'], item['original_sha256']
            known[name] = {'bytes': byte_count, 'sha256': digest, 'map': maps[-1]}
    originals = []
    source_records = {}
    unchanged = 0
    for path in sorted(SDD.rglob('*')):
        assert not path.is_symlink(), path
        if not path.is_file():
            continue
        relative = path.relative_to(SDD).as_posix()
        body = path.read_bytes()
        source_records[relative] = {'bytes': len(body), 'sha256': sha(body)}
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
        assert (gzip.decompress(stored) if compressed else stored) == body
        item = {'original_path': relative, 'original_bytes': len(body), 'original_sha256': sha(body),
            'change': 'changed' if previous else 'new', 'retained_path': destination.as_posix(),
            'retained_bytes': len(stored), 'retained_sha256': sha(stored), 'encoding': 'gzip' if compressed else 'identity'}
        if previous:
            item['previous_sha256'] = previous['sha256']
            item['previous_retention_map'] = previous['map']
        if compressed:
            item['retrieval'] = {'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)}
        originals.append(item)
    assert not set(known) - set(source_records)
    assert len(source_records) == unchanged + len(originals)
    required = {'task-8-report.md', 'progress.md', 'task-8-daily-endpoint-owner-answer.json', 'task-8-i1-closure-brief.md',
        'task-8-i1-combined-sequence.txt', 'controller-task8-i1-inspection.py', 'controller-task8-i1-inspection.json',
        'controller-task8-i1-inspection-first.py', 'controller-task8-i1-inspection-first-failure.json',
        'task-8-i1-proof-inspection.py', 'task-8-i1-proof-inspection-first.py', 'task-8-i1-proof-inspection.json',
        'task-8-i1-proof-inspection-execution.json', 'task-8-i1-proof-inspection-green-execution.json',
        'task-8-i1-inspection-helper-failure.json', 'task-8-i1-primary-preservation.json'}
    assert required <= {item['original_path'] for item in originals}
    now = datetime.now(timezone.utc).isoformat()
    save('retention-map.json', {'schema_version': 'sec-task8-i1-retention-v1', 'recorded_at': now, 'source_base': BASE,
        'original_root': str(SDD), 'retained_root': str(CHECKPOINT),
        'original_repository_relative_prefix': SDD.relative_to(ROOT).as_posix(), 'retained_repository_relative_prefix': CHECKPOINT.relative_to(ROOT).as_posix(),
        'lookup': 'Exact original_path matches select this current version; otherwise use unchanged fallback maps newest first. Historical checkpoint references keep their original bytes.',
        'unchanged_fallback_maps_newest_first': list(reversed(maps)), 'current_source_file_count': len(source_records),
        'unchanged_source_file_count': unchanged, 'new_or_changed_source_file_count': len(originals),
        'new_or_changed_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'all_copied_or_decompressed_bytes_verified': True, 'original_paths_missing_now': [], 'exclusions': [], 'files': originals,
        'combined_fixture_bundle_rootmap': record(BUNDLE / 'retention-map.json'),
        'reused_installed_proof_root_map': record(INSTALLED / 'retention-map.json'),
        'reused_installed_proof_manifest': record(INSTALLED / 'sha256-manifest.json')})
    inspection = json.loads((SDD / 'task-8-i1-proof-inspection.json').read_text())
    names = ['specs/evidence/sec-filing-index-ingestion/stage-2/verification.md',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification/fixture-sequence.py',
        'conf/sec-edgar-ingest.yaml', 'pyproject.toml', 'uv.lock', 'packages/sec-edgar-ingest/pyproject.toml',
        'packages/sec-edgar-ingest/README.md', 'packages/sec-edgar-ingest/tests/network_guard.py',
        'packages/sec-edgar-ingest/tests/test_network_guard.py', 'scripts/check-sec-edgar-ingest.sh',
        'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-report.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-daily-endpoint-owner-answer.json',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-i1-closure-brief.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-fix2-rereview.md']
    save('source-revisions.json', {'recorded_at': now, 'source_base': BASE, 'actual_precommit_head': head,
        'candidate_file_hashes': [record(ROOT / name) for name in names],
        'production_source_hashes': inspection['production_source_hashes'],
        'all18_production_sources_equal_BASE_and_validated_wheel': True, 'artifacts': inspection['artifacts'],
        'current_prescribed_check_log': record(SDD / 'task-8-fix2-final-check.txt'),
        'reused_installed_summary': record(INSTALLED / 'wheel-proof-summary.json'), 'fresh_install_or_suite_rerun_needed': False,
        'owner_answer': 'Yes: separate daily open config; quarterly2015Q1 unchanged',
        'combined_sequence': record(SDD / 'task-8-i1-combined-sequence.txt'), 'combined_bundle_manifest': record(BUNDLE / 'sha256-manifest.json'),
        'config_sha256': json.loads((BUNDLE / 'sequence-summary.json').read_text())['config_sha256'],
        'operative_scoped_I2_review': record(SDD / 'task-8-fix2-rereview.md'),
        'pending': ['fresh scoped I1 review', 'controller final whole-branch gates'], 'all_s7_checks': 'reserved',
        'no_future_commit_or_review_sha_claim': True})
    primary = json.loads((SDD / 'task-8-i1-primary-preservation.json').read_text())
    assert primary['exit_code'] == 0
    primary_status = json.loads(primary['stdout'])
    expected = [' D packages/sec-edgar-index-ingest/README.md', ' D packages/sec-edgar-index-ingest/pyproject.toml',
        ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py',
        ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed', '?? specs/sec-filing-index-ingestion-roadmap.md']
    assert primary_status['primary_status'].splitlines() == expected
    assert primary_status['changed_protected_files'] == primary_status['restored_deletions'] == []
    current_records = {path.relative_to(SDD).as_posix(): {'bytes': len(path.read_bytes()), 'sha256': sha(path.read_bytes())}
        for path in SDD.rglob('*') if path.is_file()}
    assert current_records == source_records
    save('retention-assertions.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts, 'all_prior_inventory_and_map_controls_equal_BASE': True,
        'all_new_original_or_decompressed_bytes_verified': True, 'current_sdd_unchanged_during_copy': True,
        'no_previous_checkpoint_or_primary_written': True, 'no_current_sdd_deleted': True,
        'all_primary_protected_files_and_original_status_preserved': True,
        'reused_install_and_successful_suite_not_rerun_or_copied': True, 'no_recursive_copy_or_symlink': True,
        'scope': 'Retention assertions after actual approved fixture execution; no future scoped review or Stage2 completion claim.'})
    entries = [record(path) for directory in (CHECKPOINT, BUNDLE) for path in sorted(directory.rglob('*')) if path.is_file()]
    manifest = CHECKPOINT / 'sha256-manifest.json'
    inventory = CHECKPOINT / 'evidence-inventory.json'
    save('sha256-manifest.json', {'schema_version': 'sec-task8-i1-sha256-v1', 'path_root': 'repository root',
        'exclusions': [{'path': path.relative_to(ROOT).as_posix(), 'reason': 'Own manifest/inventory control excluded to prevent a self-hash cycle'} for path in (manifest, inventory)], 'files': entries})
    save('evidence-inventory.json', {'schema_version': 'sec-task8-i1-inventory-v1', 'recorded_at': now, 'source_base': BASE,
        'covered_file_count': len(entries), 'covered_total_bytes': sum(item['bytes'] for item in entries),
        'new_checkpoint_covered_files': sum(item['path'].startswith(CHECKPOINT.relative_to(ROOT).as_posix() + '/') for item in entries),
        'new_checkpoint_covered_bytes': sum(item['bytes'] for item in entries if item['path'].startswith(CHECKPOINT.relative_to(ROOT).as_posix() + '/')),
        'combined_bundle_files': 97, 'combined_bundle_bytes': 502536, 'combined_bundle_inner_records': 96,
        'checkpoint_control_file_count': 2, 'manifest': record(manifest), 'retention_map': record(CHECKPOINT / 'retention-map.json'),
        'new_or_changed_sdd_files': len(originals), 'new_or_changed_sdd_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_sdd_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'changed_original_paths': [item['original_path'] for item in originals if item['change'] == 'changed'],
        'compressed_files': [item for item in originals if item['encoding'] == 'gzip'],
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts,
        'current_review': 'pending controller fresh scoped I1 review', 'I1': 'owner Yes; approved combined sequence executed/independently inspected',
        'I2_I3': 'ADDRESSED by earlier fresh scoped reviewers', 'all_s7_checks': 'reserved',
        'reused_install_and_full289_check_unchanged': True})
    for item in entries:
        assert record(ROOT / item['path']) == item
    assert verify_previous() == prior_counts
    print(json.dumps({'new_or_changed_sdd_files': len(originals), 'new_or_changed_sdd_bytes': sum(item['original_bytes'] for item in originals),
        'covered_file_count': len(entries), 'covered_total_bytes': sum(item['bytes'] for item in entries),
        'manifest_sha256': sha(manifest.read_bytes()), 'retention_map_sha256': sha((CHECKPOINT / 'retention-map.json').read_bytes()),
        'prior_records_verified': sum(prior_counts.values()), 'prior_checkpoints': 'unchanged'}, sort_keys=True))


if __name__ == '__main__':
    main()
