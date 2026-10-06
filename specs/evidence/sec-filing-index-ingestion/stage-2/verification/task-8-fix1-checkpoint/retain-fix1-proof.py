"""Retain new/changed Task 8 fix1 evidence without rewriting the old checkpoint.

Run once from the repository root after report/verification creation. The source
SDD remains intact. SHA inventories exclude their two own control files.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = 'a62c05c0a961fecc2f1ac854b9dac68be3add7ef'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = Path(__file__).resolve().parent
WHEEL_PROOF = VERIFICATION / 'sec-edgar-wheel-1k5klfr3'
ORIGINAL_MANIFEST_SHA = '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926'


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def save(name: str, value: object) -> None:
    path = CHECKPOINT / name
    assert not path.exists(), path
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def record(path: Path) -> dict[str, object]:
    body = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(body), 'sha256': digest(body)}


def verify_original() -> int:
    manifest_path = VERIFICATION / 'sha256-manifest.json'
    assert digest(manifest_path.read_bytes()) == ORIGINAL_MANIFEST_SHA
    manifest = json.loads(manifest_path.read_text())
    for item in manifest['files']:
        body = (VERIFICATION / item['path']).read_bytes()
        assert len(body) == item['bytes'] and digest(body) == item['sha256'], item['path']
    return len(manifest['files'])


def main() -> None:
    assert ROOT == Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert head == BASE, head
    original_verified = verify_original()
    original_map_path = VERIFICATION / 'sdd-retention-map.json'
    original_map = json.loads(original_map_path.read_text())
    original_by_path = {item['path']: item for item in original_map['files']}
    source_records = []
    unchanged_count = 0
    current_source_count = 0
    for path in sorted(SDD.rglob('*')):
        assert not path.is_symlink(), path
        if not path.is_file():
            continue
        current_source_count += 1
        relative = path.relative_to(SDD).as_posix()
        body = path.read_bytes()
        original_hash = digest(body)
        old = original_by_path.get(relative)
        if old and old['sha256'] == original_hash and old['bytes'] == len(body):
            unchanged_count += 1
            continue
        compressed = path.suffix == '.diff' and len(body) > 1024 * 1024
        retained_relative = Path('sdd') / (relative + '.gz' if compressed else relative)
        retained = CHECKPOINT / retained_relative
        assert not retained.exists(), retained
        retained.parent.mkdir(parents=True, exist_ok=True)
        retained_body = gzip.compress(body, compresslevel=9, mtime=0) if compressed else body
        retained.write_bytes(retained_body)
        actual_retained = retained.read_bytes()
        assert actual_retained == retained_body
        retrieved = gzip.decompress(actual_retained) if compressed else actual_retained
        assert retrieved == body
        item = {
            'original_path': relative,
            'original_bytes': len(body),
            'original_sha256': original_hash,
            'change': 'new' if old is None else 'changed',
            'retained_path': retained_relative.as_posix(),
            'retained_bytes': len(retained_body),
            'retained_sha256': digest(retained_body),
            'encoding': 'gzip' if compressed else 'identity',
        }
        if old is not None:
            item['previous_sha256'] = old['sha256']
        if compressed:
            item['retrieval'] = {'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(body), 'expected_output_sha256': original_hash}
        source_records.append(item)
    original_paths_missing_now = sorted(set(original_by_path) - {path.relative_to(SDD).as_posix() for path in SDD.rglob('*') if path.is_file()})
    assert not original_paths_missing_now, original_paths_missing_now
    assert current_source_count == unchanged_count + len(source_records)
    assert {'task-8-report.md', 'task-8-review.md', 'task-8-fix1-brief.md', 'task-8-fix1-guard-red.txt', 'task-8-fix1-covering.txt', 'task-8-fix1-final-check.txt', 'controller-task8-fix1-check-inspection.json'} <= {item['original_path'] for item in source_records}
    recorded_at = datetime.now(timezone.utc).isoformat()
    save('retention-map.json', {
        'schema_version': 'sec-task8-fix1-retention-v1',
        'recorded_at': recorded_at,
        'source_base': BASE,
        'original_root': str(SDD),
        'retained_root': str(CHECKPOINT),
        'original_repository_relative_prefix': SDD.relative_to(ROOT).as_posix(),
        'retained_repository_relative_prefix': CHECKPOINT.relative_to(ROOT).as_posix(),
        'lookup': 'Exact original_path matches here select the new current receipt; unchanged paths resolve through the original sdd-retention-map.json. Historical original checkpoint references keep their original bytes.',
        'unchanged_fallback_map': original_map_path.relative_to(ROOT).as_posix(),
        'original_manifest_sha256': ORIGINAL_MANIFEST_SHA,
        'current_source_file_count': current_source_count,
        'unchanged_source_file_count': unchanged_count,
        'new_or_changed_source_file_count': len(source_records),
        'new_or_changed_original_bytes': sum(item['original_bytes'] for item in source_records),
        'new_or_changed_retained_bytes': sum(item['retained_bytes'] for item in source_records),
        'all_copied_or_decompressed_bytes_verified': True,
        'original_paths_missing_now': original_paths_missing_now,
        'exclusions': [],
        'files': source_records,
        'fresh_installed_proof_root_map': (WHEEL_PROOF / 'retention-map.json').relative_to(ROOT).as_posix(),
        'fresh_installed_proof_manifest': (WHEEL_PROOF / 'sha256-manifest.json').relative_to(ROOT).as_posix(),
    })
    named = [
        'README.md', 'packages/sec-edgar-ingest/README.md',
        'packages/sec-edgar-ingest/tests/support.py',
        'packages/sec-edgar-ingest/tests/network_guard.py',
        'packages/sec-edgar-ingest/tests/test_network_guard.py',
        'scripts/check-sec-edgar-ingest.sh',
        'docs/runbooks/sec-edgar-ingest-acquisition.md',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification.md',
        'conf/sec-edgar-ingest.yaml', 'pyproject.toml', 'uv.lock',
        'packages/sec-edgar-ingest/pyproject.toml',
        'packages/sec-edgar-ingest/tests/fixtures/acquisition/manifest.json',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-review.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-fix1-brief.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-report.md',
    ]
    proof_inspection = json.loads((SDD / 'task-8-fix1-proof-inspection.json').read_text())
    save('source-revisions.json', {
        'recorded_at': recorded_at,
        'source_base': BASE,
        'actual_precommit_head': head,
        'pending': ['fresh scoped I2/I3 review', 'I1 owner choice and actual approved combined Step4', 'final controller whole-branch gates'],
        'candidate_file_hashes': [record(ROOT / name) for name in named],
        'production_source_hashes': proof_inspection['production_sources_identical_to_base_and_built_wheel'],
        'all18_production_python_sources_equal_base_and_both_wheels': True,
        'actual_current_artifacts': proof_inspection['artifacts'],
        'current_check_log': record(SDD / 'task-8-fix1-final-check.txt'),
        'fresh_installed_proof': record(WHEEL_PROOF / 'wheel-proof-summary.json'),
        'current_fix_report': record(SDD / 'task-8-report.md'),
        'no_future_commit_or_review_sha_claim': True,
    })
    save('retention-assertions.json', {
        'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())],
        'cwd': str(ROOT),
        'all_new_original_bytes_or_lossless_decompression_verified': True,
        'original_checkpoint_manifest_records_unchanged': original_verified,
        'original_manifest_sha256': ORIGINAL_MANIFEST_SHA,
        'no_original_checkpoint_written': True,
        'no_current_sdd_deleted': True,
        'no_primary_checkout_written': True,
        'no_recursive_copy_or_symlink': True,
        'scope': 'Evidence retention assertions reached after current proof execution; no self-issued review PASS or final Step4 claim.',
    })
    entries = [record(path) for directory in (CHECKPOINT, WHEEL_PROOF) for path in sorted(directory.rglob('*')) if path.is_file()]
    assert not any(Path(item['path']).name in ('evidence-inventory.json',) for item in entries)
    own_manifest_relative = (CHECKPOINT / 'sha256-manifest.json').relative_to(ROOT).as_posix()
    own_inventory_relative = (CHECKPOINT / 'evidence-inventory.json').relative_to(ROOT).as_posix()
    assert not any(item['path'] in (own_manifest_relative, own_inventory_relative) for item in entries)
    save('sha256-manifest.json', {
        'schema_version': 'sec-task8-fix1-sha256-v1',
        'path_root': 'repository root',
        'exclusions': [
            {'path': own_manifest_relative, 'reason': 'Own SHA manifest excluded to prevent a self-hash cycle'},
            {'path': own_inventory_relative, 'reason': 'Inventory references SHA manifest; excluded to prevent a hash cycle'},
        ],
        'files': entries,
    })
    manifest_path = CHECKPOINT / 'sha256-manifest.json'
    inventory = {
        'schema_version': 'sec-task8-fix1-inventory-v1',
        'recorded_at': recorded_at,
        'source_base': BASE,
        'covered_file_count': len(entries),
        'covered_total_bytes': sum(item['bytes'] for item in entries),
        'checkpoint_covered_files': sum(item['path'].startswith(CHECKPOINT.relative_to(ROOT).as_posix() + '/') for item in entries),
        'fresh_installed_proof_files': sum(item['path'].startswith(WHEEL_PROOF.relative_to(ROOT).as_posix() + '/') for item in entries),
        'fresh_installed_proof_bytes': proof_inspection['fresh_proof_total_bytes'],
        'checkpoint_control_file_count': 2,
        'control_files_excluded_from_hash_payload': [own_manifest_relative, own_inventory_relative],
        'manifest': record(manifest_path),
        'retention_map': record(CHECKPOINT / 'retention-map.json'),
        'new_or_changed_sdd_files': len(source_records),
        'new_or_changed_sdd_original_bytes': sum(item['original_bytes'] for item in source_records),
        'new_or_changed_sdd_retained_bytes': sum(item['retained_bytes'] for item in source_records),
        'changed_original_paths': [item['original_path'] for item in source_records if item['change'] == 'changed'],
        'compressed_files': [item for item in source_records if item['encoding'] == 'gzip'],
        'original_checkpoint_manifest_records_verified_unchanged': original_verified,
        'original_manifest_sha256': ORIGINAL_MANIFEST_SHA,
        'all_s7_checks': 'reserved',
        'required_combined_step4': 'I1 owner answer remains pending; prepared optional approved-daily sequence not executed',
        'new_fix_review': 'pending controller scoped re-review',
    }
    save('evidence-inventory.json', inventory)
    for item in entries:
        assert record(ROOT / item['path']) == item, item['path']
    assert verify_original() == original_verified
    print(json.dumps({key: inventory[key] for key in ('covered_file_count', 'covered_total_bytes', 'new_or_changed_sdd_files', 'new_or_changed_sdd_original_bytes', 'new_or_changed_sdd_retained_bytes', 'fresh_installed_proof_files', 'fresh_installed_proof_bytes')}, sort_keys=True))
    print(json.dumps({'manifest_sha256': digest(manifest_path.read_bytes()), 'retention_map_sha256': digest((CHECKPOINT / 'retention-map.json').read_bytes()), 'original_checkpoint': 'unchanged', 'compressed_files': [(item['original_path'], item['original_bytes'], item['retained_bytes']) for item in source_records if item['encoding'] == 'gzip']}))


if __name__ == '__main__':
    main()
