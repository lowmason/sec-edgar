"""Retain administrative completion and all new SDD bytes against seven prior maps."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

ROOT = Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
VERIFICATION = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification'
CHECKPOINT = VERIFICATION / 'completion-checkpoint'
REVIEWED = 'e458010ead6709c16e992fa22a33997d3aa36ef0'
PRIOR = [
    (VERIFICATION, '89f4b9c48517d0af42a1099777e910ba8c634b7d337c80c06a8658c03f2ec926', 'sdd-retention-map.json', 4813),
    (VERIFICATION / 'task-8-fix1-checkpoint', 'dab1d3fafa0a558be4502fa9ea390d97d279f1f4b1c6f9f3c2bcdd67507247b3', 'retention-map.json', 4661),
    (VERIFICATION / 'task-8-fix2-checkpoint', 'd156894ae7ec3a3e646dfdcba1e5946a35d09b80004ea7a3c8b791d65afa35ea', 'retention-map.json', 2532),
    (VERIFICATION / 'task-8-controller-review-checkpoint', '29cc50fd9a83bd65761eace992cb342d75a23cb9e80cebd601ef097dfe55146d', 'retention-map.json', 9),
    (VERIFICATION / 'task-8-i1-checkpoint', '97005523e67dbdfe2252c46a4d64268b2dc8a0cc780e8359cc0ad16420b39551', 'retention-map.json', 119),
    (VERIFICATION / 'task-8-controller-acceptance-checkpoint', '65c3687df9d1d899240b0999ab81c62a146090a9c01ec3dcd25270ea99bd616b', 'retention-map.json', 16),
    (VERIFICATION / 'final-review-fix1-checkpoint', '31eaa515aaa8fd343c580d509d54dee5e1ea04c275ce04736ebb3ce596326ddc', 'retention-map.json', 5208),
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

def snapshot():
    result = {}
    for path in sorted(SDD.rglob('*')):
        assert not path.is_symlink(), path
        if path.is_file():
            body = path.read_bytes()
            result[path.relative_to(SDD).as_posix()] = {'bytes': len(body), 'sha256': sha(body)}
    return result

def verify_prior():
    counts = {}
    for directory, expected, map_name, count in PRIOR:
        manifest = directory / 'sha256-manifest.json'
        assert sha(manifest.read_bytes()) == expected, manifest
        items = json.loads(manifest.read_text())['files']
        assert len(items) == count
        for item in items:
            target = (VERIFICATION if directory == VERIFICATION else ROOT) / item['path']
            body = target.read_bytes()
            assert len(body) == item['bytes'] and sha(body) == item['sha256'], target
        counts[manifest.relative_to(ROOT).as_posix()] = len(items)
        for control in (manifest, directory / 'evidence-inventory.json', directory / map_name):
            committed = subprocess.check_output(['git', 'show', f'{REVIEWED}:{control.relative_to(ROOT).as_posix()}'], cwd=ROOT)
            assert control.read_bytes() == committed, control
    assert sum(counts.values()) == 17358
    return counts

def gzip_required(path, body):
    reasons = []
    if path.suffix in ('.diff', '.patch'):
        reasons.append('verbatim diff/patch preserved losslessly')
    if path.suffix == '.json' and len(body) > 1024 * 1024:
        reasons.append('large structured map preserved losslessly')
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        text = ''
    if re.search(r'(?m)[ \t]+\r?$', text) or text.endswith(('\n\n', '\r\n\r\n')):
        reasons.append('verbatim text whitespace preserved losslessly')
    return reasons

def validate_documents():
    names = ['specs/plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md',
             'specs/completed/sec-filing-index-ingestion-stage-2-spec.md']
    items = []
    for name in names:
        path = ROOT / name
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            local, separator, fragment = target.partition('#')
            destination = (path.parent / unquote(local)).resolve()
            assert destination.is_relative_to(ROOT) and destination.is_file(), (name, target)
            if separator:
                headings = []
                for title in re.findall(r'^#{1,6}\s+(.+)$', destination.read_text(), re.M):
                    title = re.sub(r'<[^>]*>', '', title).lower()
                    title = re.sub(r'[^\w\- ]', '', title).replace(' ', '-')
                    headings.append(title)
                assert fragment in headings, (name, target, headings)
            items.append({'document': name, 'markdown_target': target, 'resolved_repository_path': destination.relative_to(ROOT).as_posix(),
                          'fragment_validated': bool(separator), 'target': record(destination)})
    plan = (ROOT / names[0]).read_text()
    assert len(re.findall(r'^- \[x\] \*\*Step ', plan, re.M)) == 33
    assert not re.findall(r'^- \[ \] \*\*Step ', plan, re.M)
    for name in names:
        assert '**Status: COMPLETE (2026-10-06)**' in (ROOT / name).read_text()
    stage7 = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md'
    rows = re.findall(r'^\| S7-\d\d.*$', stage7.read_text(), re.M)
    assert len(rows) == 22 and all(row.endswith('| reserved/not_run |') for row in rows)
    equality = json.loads((SDD / 'completion-evidence/tested-reviewed-source-equality.json').read_text())
    for item in equality['files_equal_reviewed_head']:
        assert record(ROOT / item['path']) == item
    roadmap = json.loads((SDD / 'completion-evidence/roadmap-exact-checkbox.json').read_text())
    for item in roadmap['files']:
        path = Path(item['root']) / item['path']
        assert sha(path.read_bytes()) == item['after_sha256']
        assert len(re.findall(rb'^- \[ \] Stage [3-8]:', path.read_bytes(), re.M)) == 6
    save('documentation-validation.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'local_link_occurrences_verified': len(items), 'links': items, 'actual_completed_steps': 33,
        'all22_stage7_rows_unchanged_reserved': record(stage7), 'both_retired_status_headers_verified': True,
        'all_runtime_build_test_existing_helper_hashes_reverified': len(equality['files_equal_reviewed_head']),
        'exact_one_checkbox_roadmap_bytes_reverified': True, 'later_stages_3_through_8_unticked': True})

def main():
    assert Path.cwd().resolve() == ROOT
    assert Path(__file__).resolve().parent == CHECKPOINT
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip() == REVIEWED
    prior_counts = verify_prior()
    source = snapshot()
    known, maps = {}, []
    for directory, _, map_name, _ in PRIOR:
        path = directory / map_name
        map_path = path.relative_to(ROOT).as_posix()
        maps.append(map_path)
        for item in json.loads(path.read_text())['files']:
            if directory == VERIFICATION:
                name, length, digest = item['path'], item['bytes'], item['sha256']
            else:
                name, length, digest = item['original_path'], item['original_bytes'], item['original_sha256']
            known[name] = {'bytes': length, 'sha256': digest, 'map': map_path}
    assert not set(known) - set(source), set(known) - set(source)
    originals, unchanged = [], 0
    for name, item in source.items():
        previous = known.get(name)
        if previous and all(item[key] == previous[key] for key in ('bytes', 'sha256')):
            unchanged += 1
            continue
        path = SDD / name
        body = path.read_bytes()
        assert {'bytes': len(body), 'sha256': sha(body)} == item
        reasons = gzip_required(path, body)
        destination = Path('sdd') / (name + '.gz' if reasons else name)
        target = CHECKPOINT / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        assert not target.exists(), target
        stored = gzip.compress(body, compresslevel=9, mtime=0) if reasons else body
        target.write_bytes(stored)
        assert (gzip.decompress(target.read_bytes()) if reasons else target.read_bytes()) == body
        result = {'original_path': name, 'original_bytes': len(body), 'original_sha256': sha(body),
                  'retained_path': destination.as_posix(), 'retained_bytes': len(stored), 'retained_sha256': sha(stored),
                  'encoding': 'gzip' if reasons else 'identity', 'change': 'changed' if previous else 'new'}
        if previous:
            result.update(previous_sha256=previous['sha256'], previous_retention_map=previous['map'])
        if reasons:
            result.update(encoding_reasons=reasons, retrieval={'operation': 'gzip decompression of retained_path',
                'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)})
        originals.append(result)
    required = {'review-9098fe9..e458010.diff', 'authored-final-review-fix1-9098fe9..e458010.diff',
        'final-review-fix1-changed-paths-9098fe9..e458010.json', 'final-review-fix1-package-9098fe9..e458010.json',
        'final-review-fix1-rereview.md', 'final-review-fix1-rereview-brief.md', 'final-review-fix1-rereview-routing.json',
        'whole-branch-review-resolution.json', 'progress.md', 'minor-ledger.md', 'completion-brief.md',
        'completion-evidence/clock-and-gate.json', 'completion-evidence/deferred-stats.json',
        'completion-evidence/tested-reviewed-source-equality.json', 'completion-evidence/document-markup.json',
        'completion-evidence/roadmap-exact-checkbox.json', 'completion-evidence/completion-primary-preservation.json',
        'completion-evidence/administrative-document-markup.diff', 'completion-report.md'}
    assert required <= {item['original_path'] for item in originals}, required - {item['original_path'] for item in originals}
    assert source['whole-branch-review-9098fe9.md'] == {'bytes': 23529, 'sha256': '16b8c5be98c911415790077fb5f03da8df86416554b8a2966a6b05e9e62a21ac'}
    assert source['final-review-fix1-rereview.md'] == {'bytes': 19250, 'sha256': 'ab14da124bc45c87e13ddc9edcb534a89ea6a4089d3772e838c8743628ed34c2'}
    assert len(source) == unchanged + len(originals)
    save('retention-map.json', {'schema_version': 'sec-stage2-completion-retention-v1',
        'recorded_at': datetime.now(timezone.utc).isoformat(), 'reviewed_head': REVIEWED,
        'original_root': str(SDD), 'retained_root': str(CHECKPOINT), 'lookup': 'Exact original_path selects current version; otherwise use fallback maps newest first. Historical maps retain their historical bytes.',
        'unchanged_fallback_maps_newest_first': list(reversed(maps)), 'current_source_file_count': len(source),
        'unchanged_source_file_count': unchanged, 'new_or_changed_source_file_count': len(originals),
        'new_or_changed_original_bytes': sum(item['original_bytes'] for item in originals),
        'new_or_changed_retained_bytes': sum(item['retained_bytes'] for item in originals),
        'all_copied_or_decompressed_bytes_verified': True, 'original_paths_missing_now': [], 'exclusions': [], 'files': originals})
    body = (CHECKPOINT / 'retention-map.json').read_bytes()
    (CHECKPOINT / 'retention-map.json.gz').write_bytes(gzip.compress(body, compresslevel=9, mtime=0))
    assert gzip.decompress((CHECKPOINT / 'retention-map.json.gz').read_bytes()) == body
    save('retention-map-gzip-retrieval.json', {'original': record(CHECKPOINT / 'retention-map.json'),
        'retained': record(CHECKPOINT / 'retention-map.json.gz'), 'retrieval': 'gzip decompression',
        'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)})
    body = (json.dumps(source, indent=2, sort_keys=True) + '\n').encode()
    (CHECKPOINT / 'sdd-source-inventory.json.gz').write_bytes(gzip.compress(body, compresslevel=9, mtime=0))
    assert gzip.decompress((CHECKPOINT / 'sdd-source-inventory.json.gz').read_bytes()) == body
    save('sdd-source-inventory-retrieval.json', {'source_file_count': len(source),
        'retained': record(CHECKPOINT / 'sdd-source-inventory.json.gz'), 'retrieval': 'gzip decompression',
        'expected_output_bytes': len(body), 'expected_output_sha256': sha(body)})
    validate_documents()
    assert snapshot() == source
    assert verify_prior() == prior_counts
    save('retention-assertions.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'argv': [sys.executable, str(Path(__file__).resolve())], 'cwd': str(ROOT),
        'seven_prior_manifest_records_verified_unchanged': prior_counts, 'seven_prior_manifest_inventory_map_controls_equal_reviewed_head': True,
        'all_current_sdd_bytes_covered_by_current_or_prior_maps': True, 'no_missing_originals': True,
        'all_new_copied_or_decompressed_bytes_verified': True, 'sdd_frozen_during_copy': True,
        'new_or_changed_sdd_files': len(originals), 'unchanged_fallback_files': unchanged,
        'current_source_files': len(source), 'compressed_sdd_files': sum(item['encoding'] == 'gzip' for item in originals),
        'no_prior_control_or_payload_edits': True, 'no_sdd_worktree_branch_cleanup_or_integration': True,
        'runtime_build_test_existing_helpers_equal_tested_reviewed_source': True,
        'no_suite_install_or_acquisition_rerun': True, 'all22_stage7_checks': 'reserved'})
    print(json.dumps({'exit_code': 0, 'new_or_changed_sdd_files': len(originals),
        'original_bytes': sum(item['original_bytes'] for item in originals), 'retained_bytes': sum(item['retained_bytes'] for item in originals),
        'current_sdd_files': len(source), 'unchanged_fallback_files': unchanged,
        'compressed_sdd_files': sum(item['encoding'] == 'gzip' for item in originals),
        'prior_records_verified_unchanged': sum(prior_counts.values()),
        'local_document_links_verified': json.loads((CHECKPOINT / 'documentation-validation.json').read_text())['local_link_occurrences_verified'],
        'retention_map': record(CHECKPOINT / 'retention-map.json')}))

if __name__ == '__main__':
    main()
