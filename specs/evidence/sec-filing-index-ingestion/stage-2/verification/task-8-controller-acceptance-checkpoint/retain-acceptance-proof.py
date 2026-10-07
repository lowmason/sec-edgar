"""Append-only controller acceptance receipts; final whole-branch review remains pending."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = 'adaff4c573809964fa679e4b788004050098f7fd'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = Path(__file__).resolve().parent
PRIOR = [
    (VERIFICATION, '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926', 'sdd-retention-map.json'),
    (VERIFICATION / 'task-8-fix1-checkpoint', 'dab1d3fafa0a558be4502fa9ea390d97d279f1f4b1c6f9f3c2bcdd67507247b3', 'retention-map.json'),
    (VERIFICATION / 'task-8-fix2-checkpoint', 'd156894ae7ec3a3e646dfdcba1e5946a35d09b80004ea7a3c8b791d65afa35ea', 'retention-map.json'),
    (VERIFICATION / 'task-8-controller-review-checkpoint', '29cc50fd9a83bd65761eace992cb342d75a23cb9e80cebd601ef097dfe55146d', 'retention-map.json'),
    (VERIFICATION / 'task-8-i1-checkpoint', '97005523e67dbdfe2252c46a4d64268b2dc8a0cc780e8359cc0ad16420b39551', 'retention-map.json'),
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
    assert sum(counts.values()) == 12134
    return counts


def main():
    assert ROOT == Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    assert head == BASE
    assert subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True, check=True).stdout == ''
    prior_counts = verify_previous()
    argv = [sys.executable, str(SDD / 'verify_primary.py')]
    started = datetime.now(timezone.utc).isoformat()
    primary = subprocess.run(argv, capture_output=True, text=True)
    save('primary-preservation.json', {'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'argv': argv, 'cwd': str(ROOT), 'stdout': primary.stdout, 'stderr': primary.stderr, 'exit_code': primary.returncode,
        'kind': 'separate read-only primary verification; no primary mutation'})
    assert primary.returncode == 0
    p = json.loads(primary.stdout)
    assert p['changed_protected_files'] == p['restored_deletions'] == []
    assert p['primary_status'].splitlines() == [' D packages/sec-edgar-index-ingest/README.md',
        ' D packages/sec-edgar-index-ingest/pyproject.toml', ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py',
        ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed', '?? specs/sec-filing-index-ingestion-roadmap.md']
    known = {}
    maps = []
    for directory, _, map_name in PRIOR:
        path = directory / map_name
        maps.append(path.relative_to(ROOT).as_posix())
        for item in json.loads(path.read_text())['files']:
            name, size, digest = ((item['path'], item['bytes'], item['sha256']) if directory == VERIFICATION
                else (item['original_path'], item['original_bytes'], item['original_sha256']))
            known[name] = {'bytes': size, 'sha256': digest, 'map': maps[-1]}
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
        compressed = path.suffix == '.diff' and len(body) > 256 * 1024
        destination = Path('sdd') / (relative + '.gz' if compressed else relative)
        retained = CHECKPOINT / destination
        retained.parent.mkdir(parents=True, exist_ok=True)
        assert not retained.exists()
        stored = gzip.compress(body, compresslevel=9, mtime=0) if compressed else body
        retained.write_bytes(stored)
        assert (gzip.decompress(retained.read_bytes()) if compressed else retained.read_bytes()) == body
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
    assert {item['original_path'] for item in originals} == {'controller-task8-i1-retention-inspection.json', 'minor-ledger.md',
        'progress.md', 'review-49c5051..adaff4c.diff', 'task-8-i1-authored-review.diff', 'task-8-i1-rereview.md'}
    assert (SDD / 'task-8-i1-rereview.md').read_text().startswith('**I1 — ADDRESSED.** No new Critical, Important, or Minor findings.')
    assert 'Task 8: complete, per-task Spec PASS and Quality PASS' in (SDD / 'progress.md').read_text()
    assert 'Tasks 1–8: no Minor findings' in (SDD / 'minor-ledger.md').read_text()
    now = datetime.now(timezone.utc).isoformat()
    save('retention-map.json', {'schema_version': 'sec-task8-controller-acceptance-retention-v1', 'recorded_at': now, 'source_base': BASE,
        'original_root': str(SDD), 'retained_root': str(CHECKPOINT),
        'original_repository_relative_prefix': SDD.relative_to(ROOT).as_posix(), 'retained_repository_relative_prefix': CHECKPOINT.relative_to(ROOT).as_posix(),
        'lookup': 'Exact original_path matches select this current version; otherwise use unchanged fallback maps newest first. Historical checkpoint references keep original bytes.',
        'unchanged_fallback_maps_newest_first': list(reversed(maps)), 'current_source_file_count': len(source_records),
        'unchanged_source_file_count': unchanged, 'new_or_changed_source_file_count': len(originals),
        'new_or_changed_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'all_copied_or_decompressed_bytes_verified': True, 'original_paths_missing_now': [], 'exclusions': [], 'files': originals})
    names = ['specs/plans/2-sec-filing-index-ingestion-stage-2-spec.md', 'specs/evidence/sec-filing-index-ingestion/stage-2/verification.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/task-8-i1-rereview.md', '.sdd/2-sec-filing-index-ingestion-stage-2-spec/progress.md',
        '.sdd/2-sec-filing-index-ingestion-stage-2-spec/minor-ledger.md', '.sdd/2-sec-filing-index-ingestion-stage-2-spec/controller-task8-i1-retention-inspection.json']
    doc = ROOT / names[1]
    assert doc.read_bytes() == subprocess.run(['git', 'show', f'{BASE}:{names[1]}'], capture_output=True, check=True).stdout
    save('source-revisions.json', {'recorded_at': now, 'source_base': BASE, 'actual_precommit_head': head,
        'candidate_file_hashes': [record(ROOT / name) for name in names], 'verification_md_unchanged_from_BASE': True,
        'kind': 'administrative controller acceptance retention only; no implementation/suite/install rerun',
        'per_task_status': 'Controller records Task1–8 per-task Spec PASS/Quality PASS from retained original full plus fresh scoped reviews',
        'whole_branch_status': 'fresh final review pending', 'all_s7_checks': 'reserved',
        'no_future_commit_or_review_sha_claim': True})
    current = {path.relative_to(SDD).as_posix(): {'bytes': len(path.read_bytes()), 'sha256': sha(path.read_bytes())}
        for path in SDD.rglob('*') if path.is_file()}
    assert current == source_records
    save('retention-assertions.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts, 'all_prior_inventory_and_map_controls_equal_BASE': True,
        'all_new_original_or_decompressed_bytes_verified': True, 'current_sdd_unchanged_during_copy': True,
        'no_previous_checkpoint_or_verification_md_or_primary_written': True, 'no_current_sdd_deleted': True,
        'all_primary_protected_files_and_original_status_preserved': True, 'no_recursive_copy_or_symlink': True,
        'scope': 'Administrative retention after actual scoped acceptance; final whole-branch review/completion remain pending.'})
    entries = [record(path) for path in sorted(CHECKPOINT.rglob('*')) if path.is_file()]
    manifest = CHECKPOINT / 'sha256-manifest.json'
    inventory = CHECKPOINT / 'evidence-inventory.json'
    save('sha256-manifest.json', {'schema_version': 'sec-task8-controller-acceptance-sha256-v1', 'path_root': 'repository root',
        'exclusions': [{'path': path.relative_to(ROOT).as_posix(), 'reason': 'Own manifest/inventory control excluded to prevent a self-hash cycle'} for path in (manifest, inventory)], 'files': entries})
    save('evidence-inventory.json', {'schema_version': 'sec-task8-controller-acceptance-inventory-v1', 'recorded_at': now, 'source_base': BASE,
        'covered_file_count': len(entries), 'covered_total_bytes': sum(item['bytes'] for item in entries),
        'checkpoint_control_file_count': 2, 'manifest': record(manifest), 'retention_map': record(CHECKPOINT / 'retention-map.json'),
        'new_or_changed_sdd_files': len(originals), 'new_or_changed_sdd_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_sdd_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'changed_original_paths': [item['original_path'] for item in originals if item['change'] == 'changed'],
        'compressed_files': [item for item in originals if item['encoding'] == 'gzip'],
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts,
        'per_task_status': 'controller acceptance Task1–8 Spec PASS/Quality PASS; no Minor findings',
        'whole_branch_status': 'pending fresh final whole-branch review', 'all_s7_checks': 'reserved'})
    assert verify_previous() == prior_counts
    print(json.dumps({'new_or_changed_sdd_files': len(originals), 'original_sdd_bytes': sum(item['original_bytes'] for item in originals),
        'retained_sdd_bytes': sum(item['retained_bytes'] for item in originals), 'prior_records_verified_unchanged': sum(prior_counts.values()),
        'compressed_originals': [item['original_path'] for item in originals if item['encoding'] == 'gzip'], 'exit_code': 0}, sort_keys=True))


if __name__ == '__main__':
    main()
