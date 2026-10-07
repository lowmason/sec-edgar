"""One-shot final-fix retention of all current SDD versions against six historical maps."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

BASE = '9098fe9b664d9f44a663fdd8357e34030c37e932'
PROOF_HEAD = 'beb54a7ab9df3a99f76cb26fe269b36868802e3c'
ROOT = Path.cwd().resolve()
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = Path(__file__).resolve().parent
BUNDLES = [VERIFICATION / 'sec-edgar-wheel-n0zc5qlc', VERIFICATION / 'sec-edgar-stage-2-46bhxh8j']
PRIOR = [
    (VERIFICATION, '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926', 'sdd-retention-map.json'),
    (VERIFICATION / 'task-8-fix1-checkpoint', 'dab1d3fafa0a558be4502fa9ea390d97d279f1f4b1c6f9f3c2bcdd67507247b3', 'retention-map.json'),
    (VERIFICATION / 'task-8-fix2-checkpoint', 'd156894ae7ec3a3e646dfdcba1e5946a35d09b80004ea7a3c8b791d65afa35ea', 'retention-map.json'),
    (VERIFICATION / 'task-8-controller-review-checkpoint', '29cc50fd9a83bd65761eace992cb342d75a23cb9e80cebd601ef097dfe55146d', 'retention-map.json'),
    (VERIFICATION / 'task-8-i1-checkpoint', '97005523e67dbdfe2252c46a4d64268b2dc8a0cc780e8359cc0ad16420b39551', 'retention-map.json'),
    (VERIFICATION / 'task-8-controller-acceptance-checkpoint', '65c3687df9d1d899240b0999ab81c62a146090a9c01ec3dcd25270ea99bd616b', 'retention-map.json'),
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
        files = json.loads(manifest.read_text())['files']
        for item in files:
            target = (VERIFICATION if directory == VERIFICATION else ROOT) / item['path']
            body = target.read_bytes()
            assert len(body) == item['bytes'] and sha(body) == item['sha256'], target
        counts[manifest.relative_to(ROOT).as_posix()] = len(files)
        for path in (manifest, directory / 'evidence-inventory.json', directory / map_name):
            previous = subprocess.check_output(['git', 'show', f'{BASE}:{path.relative_to(ROOT).as_posix()}'])
            assert path.read_bytes() == previous, path
    assert list(counts.values()) == [4813, 4661, 2532, 9, 119, 16]
    assert sum(counts.values()) == 12150
    return counts


def snapshot_source():
    result = {}
    for path in sorted(SDD.rglob('*')):
        assert not path.is_symlink(), path
        if path.is_file():
            body = path.read_bytes()
            result[path.relative_to(SDD).as_posix()] = {'bytes': len(body), 'sha256': sha(body)}
    return result


def whitespace_requires_verbatim_gzip(body):
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return bool(re.search(r'(?m)[ \t]+\r?$', text))


def verify_bundles():
    results = []
    for root in BUNDLES:
        files = json.loads((root / 'sha256-manifest.json').read_text())
        for item in files:
            body = (root / item['path']).read_bytes()
            assert len(body) == item['bytes'] and sha(body) == item['sha256']
        physical = [path for path in root.rglob('*') if path.is_file()]
        assert len(physical) == len(files) + 1
        results.append({'root': root.relative_to(ROOT).as_posix(), 'inner_payload_records': len(files),
                        'physical_files': len(physical), 'physical_bytes': sum(path.stat().st_size for path in physical),
                        'manifest': record(root / 'sha256-manifest.json'), 'root_map': record(root / 'retention-map.json')})
    assert [item['physical_files'] for item in results] == [79, 97]
    assert [item['physical_bytes'] for item in results] == [489607, 502536]
    return results


def main():
    assert ROOT == Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
    assert CHECKPOINT == VERIFICATION / 'final-review-fix1-checkpoint'
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    assert head == PROOF_HEAD
    assert subprocess.check_output(['git', 'diff', '--cached', '--name-only']) == b''
    expected_status = [' D packages/sec-edgar-index-ingest/README.md', ' D packages/sec-edgar-index-ingest/pyproject.toml',
                       ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py',
                       ' D packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed',
                       '?? specs/evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/']
    status = subprocess.check_output(['git', 'status', '--short']).decode().splitlines()
    assert status == expected_status, status
    prior_counts = verify_previous()
    bundles = verify_bundles()
    known, maps = {}, []
    for directory, _, map_name in PRIOR:
        path = directory / map_name
        maps.append(path.relative_to(ROOT).as_posix())
        for item in json.loads(path.read_text())['files']:
            if directory == VERIFICATION:
                name, length, digest = item['path'], item['bytes'], item['sha256']
            else:
                name, length, digest = item['original_path'], item['original_bytes'], item['original_sha256']
            known[name] = {'bytes': length, 'sha256': digest, 'map': maps[-1]}
    originals = []
    source_records = snapshot_source()
    assert not set(known) - set(source_records)
    full_review = source_records['whole-branch-review-9098fe9.md']
    assert full_review == {'bytes': 23529, 'sha256': '16b8c5be98c911415790077fb5f03da8df86416554b8a2966a6b05e9e62a21ac'}
    unchanged = 0
    for relative, original in source_records.items():
        previous = known.get(relative)
        if previous and original['sha256'] == previous['sha256'] and original['bytes'] == previous['bytes']:
            unchanged += 1
            continue
        path = SDD / relative
        body = path.read_bytes()
        assert original == {'bytes': len(body), 'sha256': sha(body)}
        reasons = []
        if path.suffix in ('.diff', '.patch'):
            reasons.append('verbatim diff/patch context retained losslessly without text-whitespace reinterpretation')
        if len(body) > 1024 * 1024 and path.suffix == '.json':
            reasons.append('large structured source/map retained losslessly')
        if whitespace_requires_verbatim_gzip(body):
            reasons.append('verbatim trailing whitespace retained losslessly')
        compressed = bool(reasons)
        destination = Path('sdd') / (relative + '.gz' if compressed else relative)
        target = CHECKPOINT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(), target
        stored = gzip.compress(body, compresslevel=9, mtime=0) if compressed else body
        target.write_bytes(stored)
        assert (gzip.decompress(target.read_bytes()) if compressed else target.read_bytes()) == body
        item = {'original_path': relative, 'original_bytes': len(body), 'original_sha256': sha(body),
                'change': 'changed' if previous else 'new', 'retained_path': destination.as_posix(),
                'retained_bytes': len(stored), 'retained_sha256': sha(stored), 'encoding': 'gzip' if compressed else 'identity'}
        if previous:
            item.update(previous_sha256=previous['sha256'], previous_retention_map=previous['map'])
        if compressed:
            item['encoding_reasons'] = reasons
            item['retrieval'] = {'operation': 'gzip decompression of retained_path', 'expected_output_bytes': len(body),
                                 'expected_output_sha256': sha(body)}
        originals.append(item)
    assert len(source_records) == unchanged + len(originals)
    required = {'whole-branch-review-9098fe9.md', 'final-review-fix1-brief.md', 'final-review-fix1-report.md',
                'final-review-fix1-package-receipt.json', 'review-9098fe9..beb54a7.diff',
                'authored-final-review-fix1-9098fe9..beb54a7.diff', 'final-review-fix1-changed-paths-9098fe9..beb54a7.json',
                'final-review-fix1-evidence/latest-complete-check.command.json',
                'final-review-fix1-evidence/latest-complete-check-corrected.command.json',
                'final-review-fix1-evidence/fresh-proof-inspection.json',
                'final-review-fix1-evidence/process-proof-inspection.json'}
    assert required <= {item['original_path'] for item in originals}, required - {item['original_path'] for item in originals}
    now = datetime.now(timezone.utc).isoformat()
    save('retention-map.json', {'schema_version': 'sec-final-review-fix1-retention-v1', 'recorded_at': now,
        'source_base': BASE, 'actual_source_proof_head': PROOF_HEAD, 'original_root': str(SDD), 'retained_root': str(CHECKPOINT),
        'original_repository_relative_prefix': SDD.relative_to(ROOT).as_posix(),
        'retained_repository_relative_prefix': CHECKPOINT.relative_to(ROOT).as_posix(),
        'lookup': 'Exact original_path selects this version. Otherwise use unchanged fallback maps newest first. Historical references retain historical bytes.',
        'unchanged_fallback_maps_newest_first': list(reversed(maps)), 'current_source_file_count': len(source_records),
        'unchanged_source_file_count': unchanged, 'new_or_changed_source_file_count': len(originals),
        'new_or_changed_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'all_copied_or_decompressed_bytes_verified': True, 'original_paths_missing_now': [], 'exclusions': [],
        'files': originals, 'fresh_proof_bundles': bundles,
        'frozen_package_range': {'base': BASE, 'head': PROOF_HEAD,
                                'later_controller_range': 'actual BASE..checkpointB after B is committed'}})
    # Keep a directly readable control and a lossless compact retrieval companion, with no self-hash reference.
    map_body = (CHECKPOINT / 'retention-map.json').read_bytes()
    map_gzip = CHECKPOINT / 'retention-map.json.gz'
    map_gzip.write_bytes(gzip.compress(map_body, compresslevel=9, mtime=0))
    assert gzip.decompress(map_gzip.read_bytes()) == map_body
    save('retention-map-gzip-retrieval.json', {'original': record(CHECKPOINT / 'retention-map.json'),
        'retained': record(map_gzip), 'retrieval': 'gzip decompression of retention-map.json.gz',
        'expected_output_bytes': len(map_body), 'expected_output_sha256': sha(map_body)})
    source_body = (json.dumps(source_records, indent=2, sort_keys=True) + '\n').encode()
    source_inventory = CHECKPOINT / 'sdd-source-inventory.json.gz'
    source_inventory.write_bytes(gzip.compress(source_body, compresslevel=9, mtime=0))
    assert gzip.decompress(source_inventory.read_bytes()) == source_body
    save('sdd-source-inventory-retrieval.json', {'source_file_count': len(source_records), 'retained': record(source_inventory),
        'retrieval': 'gzip decompression of sdd-source-inventory.json.gz', 'expected_output_bytes': len(source_body),
        'expected_output_sha256': sha(source_body), 'scope': 'all current SDD source names, lengths and hashes frozen at copy time'})
    inspection = json.loads((SDD / 'final-review-fix1-evidence/fresh-proof-inspection.json').read_text())
    preserved_inputs = json.loads((SDD / 'final-review-fix1-evidence/preservation-and-check-environment.json').read_text())
    package = json.loads((SDD / 'final-review-fix1-package-receipt.json').read_text())
    assert package['base'] == BASE and package['head'] == PROOF_HEAD
    assert inspection['check']['command']['exit'] == 0 and inspection['check']['test_records'] == 302
    authored = json.loads((SDD / 'final-review-fix1-changed-paths-9098fe9..beb54a7.json').read_text())
    candidate_files = [record(ROOT / path) for path in authored['included_paths']]
    for item in candidate_files:
        assert (ROOT / item['path']).read_bytes() == subprocess.check_output(['git', 'show', f"{PROOF_HEAD}:{item['path']}"])
    save('source-revisions.json', {'recorded_at': now, 'source_base': BASE, 'actual_precommit_head': head,
        'last_implementation_head': '66f4aa9caa5b9c5bbe943026e7dbc7adc1e8b25f', 'frozen_package_range': package,
        'candidate_authored_hashes': candidate_files, 'unchanged_inputs_equal_BASE': preserved_inputs['unchanged_inputs'],
        'production_and_typing_source_hashes': inspection['installed']['package_source_hashes'],
        'all19_sources_equal_current_wheel_and_sdist': True, 'artifacts': inspection['installed']['artifact_hashes'],
        'current_prescribed_check': inspection['check'], 'fresh_installed_bundle': bundles[0], 'fresh_combined_bundle': bundles[1],
        'owner_yes': inspection['owner_yes'], 'sdk_source_hashes_unchanged': 27,
        'pending': ['controller fresh scoped Max review', 'controller whole-branch completion protocol'],
        'all22_s7_checks': 'reserved', 'source_docs_proof_frozen_after_checkpoint_commit': True,
        'no_future_commit_or_review_sha_claim': True})
    primary_argv = [sys.executable, str(SDD / 'verify_primary.py')]
    primary = subprocess.run(primary_argv, capture_output=True, text=True)
    save('primary-final-preservation.json', {'argv': primary_argv, 'cwd': str(ROOT), 'stdout': primary.stdout,
        'stderr': primary.stderr, 'exit_code': primary.returncode, 'recorded_at': datetime.now(timezone.utc).isoformat()})
    assert primary.returncode == 0
    primary_status = json.loads(primary.stdout)
    assert primary_status['changed_protected_files'] == primary_status['restored_deletions'] == []
    assert primary_status['primary_status'].splitlines() == expected_status[:4] + ['?? specs/sec-filing-index-ingestion-roadmap.md']
    assert snapshot_source() == source_records
    save('retention-assertions.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts,
        'all_six_prior_manifest_inventory_and_map_controls_equal_BASE': True,
        'all_new_original_or_decompressed_bytes_verified': True, 'current_sdd_unchanged_during_copy': True,
        'no_previous_checkpoint_or_primary_written': True, 'no_current_sdd_deleted': True,
        'all_primary_protected_files_and_original_status_preserved': True,
        'new_or_changed_sdd_files': len(originals), 'unchanged_source_files_using_prior_maps': unchanged,
        'no_recursive_copy_or_symlink': True, 'no_additional_suite_or_acquisition_rerun': True,
        'frozen_standard_and_authored_packages_cover_exact_BASE_through_A': True,
        'scope': 'Retention after actual final-fix tests/install/approved combined proofs; scoped review and Stage2 completion remain pending.'})
    assert verify_previous() == prior_counts
    save('retention-result.json', {'recorded_at': now, 'exit_code': 0,
        'new_or_changed_sdd_files': len(originals), 'new_or_changed_sdd_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_sdd_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'current_source_files': len(source_records), 'unchanged_source_files': unchanged,
        'compressed_sdd_files': sum(item['encoding'] == 'gzip' for item in originals),
        'prior_checkpoint_manifest_records_verified_unchanged': prior_counts, 'fresh_proof_bundles': bundles,
        'frozen_package_base': BASE, 'frozen_package_head': PROOF_HEAD,
        'later_controller_package_range': 'BASE through actual checkpoint B commit, generated after B exists',
        'all22_s7_checks': 'reserved'})
    print(json.dumps({'stage': 'copy_and_source_assertions_complete_before_execution_receipt',
        'new_or_changed_sdd_files': len(originals), 'original_bytes': sum(item['original_bytes'] for item in originals),
        'retained_bytes': sum(item['retained_bytes'] for item in originals),
        'prior_records_verified_unchanged': sum(prior_counts.values()), 'source_file_count': len(source_records),
        'unchanged_fallback_files': unchanged, 'compressed_sdd_files': sum(item['encoding'] == 'gzip' for item in originals)}))


if __name__ == '__main__':
    main()
