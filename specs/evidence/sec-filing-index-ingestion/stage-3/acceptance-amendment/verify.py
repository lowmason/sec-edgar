"""Verify the exact documentary exception against immutable offline evidence.

Run before the controller's completion stamp/retirement. This proof imports no
production parser and reuses the bound complete scans and actual refusal stores.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()

import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
import socket
import sqlite3
import subprocess
import time
from collections import Counter

BASE = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-3'
AMENDMENT = BASE / 'acceptance-amendment'
PRIMARY = Path('/Users/lowell/Projects/sec-edgar')
REVIEWED = '2343f39f0e21adc2ad401a9346a8c9ffa0509040'
EXPECTED = [
    ('SEC-0141', '2010Q1', 'aca38d21ee64795f6095c86c0424f94e16a322a4ec0eb6fd38d2e5d6f86822de', 3729148, 300561, 21, 6580),
    ('SEC-0142', '2015Q1', '984c3130c617c11d085a4deff77a01c21b1113d5bb4c8b2173f5f87eb9f2a728', 3901000, 318647, 24, 87808),
    ('SEC-0143', '2026Q3', '393a535f84b71ed34845f67aa5e5275ecc86afeb1a6558ad5623b0d7d0babe71', 3502663, 302315, 6, 40292),
]
FIELDS = ('receipt_id', 'period', 'sha256', 'bytes', 'rows', 'conflicts', 'first_conflict_line')
STRICT = {
    'logical_key': ['cik', 'archive_path'],
    'conflicting_duplicate': 'quarantine whole source',
    'accepted_processing': False,
    'accepted_observation_ref': False,
    'pointer_mutation': False,
    'winner_selection': False,
    'parser_tolerance': False,
    'normalization': False,
}
OBSERVED = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identity_bytes(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def identity(path):
    return identity_bytes(path.read_bytes())


def read_json(path):
    OBSERVED[str(path.relative_to(ROOT))] = identity(path)
    return json.loads(path.read_text())


def safe_path(root, relative):
    part = Path(relative)
    require(not part.is_absolute() and '..' not in part.parts, f'unsafe evidence path: {relative}')
    path = root / part
    require(path.resolve().is_relative_to(root.resolve()), f'evidence path escaped root: {relative}')
    return path


def verify_inventory(relative, expected, relocation=None, complete_tree=False):
    manifest = safe_path(BASE, relative)
    require(identity(manifest) == expected, f'changed immutable inventory: {relative}')
    records = read_json(manifest)
    root = manifest.parent
    relocation = relocation or {}
    require(manifest.name not in records, f'self-including inventory: {relative}')
    for name, value in records.items():
        path = safe_path(root, relocation.get(name, name))
        require(identity(path) == value, f'immutable payload mismatch: {relative}:{name}')
    if complete_tree:
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != manifest}
        require(actual == set(records), f'immutable tree file-set mismatch: {relative}')
    return {'records': len(records), 'inventory': expected, 'payload_bytes': sum(v['bytes'] for v in records.values())}


def validate_receipt(receipt):
    sources = receipt['allowlisted_sources']
    actual = [tuple(source[name] for name in FIELDS) for source in sources]
    require(actual == EXPECTED, 'exception must exactly match the three authorized sources')
    for source in sources:
        require(source['original_source_relative'] == f"specs/evidence/sec-filing-index-ingestion/stage-1/specimens/{source['sha256']}.zip", 'unexpected raw source resolution')
    require(receipt['strict_refusal'] == STRICT, 'strict refusal changed')
    require(receipt['owner_instruction'] == 'explicitly amend Stage 3 acceptance to allow these documented quarantines while retaining strict refusal', 'owner instruction changed')
    require((receipt['owner_date'], receipt['owner_timezone'], receipt['owner_time_of_day']) == ('2026-10-07', 'America/New_York', None), 'owner instruction timestamp invented or changed')
    require(receipt['reviewed_implementation'] == REVIEWED, 'reviewed implementation changed')
    for name in ('other_invalid_retained_rows', 'offline_cached_dependency_absence'):
        require(receipt[name] == 'blocker', f'blocker removed: {name}')
    for name in ('live_access_authorized', 'successful_catalog_range_established', 'deployed_capacity_established'):
        require(receipt[name] is False, f'scope expanded: {name}')
    require(receipt['all22_stage7_checks'] == 'reserved' and receipt['original_specimen_exit'] == 1, 'historical failure or Stage 7 reservation changed')
    require((receipt['full_scan_rows'], receipt['conflicting_observations'], receipt['classification']) == (970622, 51, {'form_type_only': 45, 'company_name_only': 6}), 'scan facts changed')


def check_negative_cases(receipt):
    mutations = [('additional source', lambda r: r['allowlisted_sources'].append(copy.deepcopy(r['allowlisted_sources'][0]))),
                 ('changed raw hash', lambda r: r['allowlisted_sources'][0].update(sha256='0' * 64)),
                 ('changed raw length', lambda r: r['allowlisted_sources'][0].update(bytes=1)),
                 ('changed row count', lambda r: r['allowlisted_sources'][0].update(rows=1)),
                 ('changed conflict count', lambda r: r['allowlisted_sources'][0].update(conflicts=0)),
                 ('changed first conflict line', lambda r: r['allowlisted_sources'][0].update(first_conflict_line=1)),
                 ('winner selection', lambda r: r['strict_refusal'].update(winner_selection=True)),
                 ('accepted processing', lambda r: r['strict_refusal'].update(accepted_processing=True)),
                 ('accepted observation', lambda r: r['strict_refusal'].update(accepted_observation_ref=True)),
                 ('pointer mutation', lambda r: r['strict_refusal'].update(pointer_mutation=True)),
                 ('live access', lambda r: r.update(live_access_authorized=True)),
                 ('removed invalid-row blocker', lambda r: r.update(other_invalid_retained_rows='allowed')),
                 ('removed cache blocker', lambda r: r.update(offline_cached_dependency_absence='allowed'))]
    rejected = []
    for name, mutate in mutations:
        candidate = copy.deepcopy(receipt)
        mutate(candidate)
        try:
            validate_receipt(candidate)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError(f'negative case accepted: {name}')
    return rejected


def check_sources(receipt):
    specimens = read_json(BASE / 'verification/specimens/report.json')
    preflight = read_json(BASE / 'verification/sdd-history/retained-parser-preflight/report.json')
    classification = read_json(BASE / 'verification/sdd-history/retained-parser-preflight/conflict-classification.json')
    refusal = read_json(BASE / 'verification/sdd-history/retained-parser-preflight/transform-refusal/report.json')
    require(specimens['exit'] == preflight['exit_code'] == 1, 'historical scan failure changed')
    require(specimens['network_guard'] and preflight['guard_installed'] and refusal['guard_installed'], 'retained proof guard missing')
    require(refusal['exit_code'] == 0 and refusal['status'] == 'DONE', 'retained actual refusal proof did not pass')
    require(len(specimens['receipts']) == len(preflight['receipts']) == 10, 'retained receipt set changed')
    require(sum(r['rows'] for r in specimens['receipts']) == sum(r['rows'] for r in preflight['receipts']) == 970622, 'full scan row count mismatch')
    allowlisted_ids = {r['receipt_id'] for r in receipt['allowlisted_sources']}
    for record in specimens['receipts']:
        if record['evidence_id'] not in allowlisted_ids:
            require(record['source_acceptance'] == 'accepted' and not record['conflicts'], 'other invalid retained source remains blocker')
    for record in preflight['receipts']:
        if record['evidence_id'] not in allowlisted_ids:
            require(record['status'] == 'DONE' and record['parser_status'] == 'DONE', 'other invalid preflight source remains blocker')
    require({r['evidence_id'] for r in specimens['receipts'] if r['conflicts']} == {r['receipt_id'] for r in receipt['allowlisted_sources']}, 'unexpected conflicting source')
    require(classification['source_report_sha256'] == identity(BASE / 'verification/sdd-history/retained-parser-preflight/report.json')['sha256'], 'classification report binding mismatch')
    require(classification['conflicting_observations'] == 51 and classification['aggregate'] == [{'fields': ['form_type'], 'count': 45}, {'fields': ['company_name'], 'count': 6}], 'classification mismatch')
    observed = []
    differences = Counter()
    for scanned in specimens['receipts']:
        relative = Path(scanned['original_path']).relative_to(ROOT)
        require(identity(PRIMARY / relative) == {'bytes': scanned['bytes'], 'sha256': scanned['sha256']}, f"original raw mismatch: {scanned['evidence_id']}")
        require(read_json(BASE / f"verification/specimens/{scanned['evidence_id']}.json") == scanned, 'per-receipt specimen mismatch')
        for conflict in scanned['conflicts']:
            first, row = conflict['first_payload'], conflict['row']
            require((row['cik'], row['archive_path']) == (first['cik'], first['archive_path']), 'conflict is not canonical duplicate')
            differences[tuple(sorted(k for k in row if row[k] != first[k]))] += 1
    require(differences == {('form_type',): 45, ('company_name',): 6}, 'observed conflict fields mismatch')
    for allowed in receipt['allowlisted_sources']:
        name = allowed['receipt_id']
        scan = next(r for r in specimens['receipts'] if r['evidence_id'] == name)
        prior = next(r for r in preflight['receipts'] if r['evidence_id'] == name)
        refused = next(r for r in refusal['receipts'] if r['receipt_id'] == name)
        for record in (scan, prior, refused):
            require((record['sha256'], record['bytes'], record['source']['period']) == (allowed['sha256'], allowed['bytes'], allowed['period']), f'{name}: input mismatch')
        for record in (scan, prior):
            require(record['rows'] == allowed['rows'] and len(record['conflicts']) == allowed['conflicts'], f'{name}: scan mismatch')
            require(record['conflicts'][0]['physical_line'] == allowed['first_conflict_line'], f'{name}: first line mismatch')
        require(scan['source_acceptance'] == 'blocked' and prior['status'] == 'BLOCKED', f'{name}: source accepted')
        require(refused['exception']['type'] == 'ParseError' and refused['exception']['reason'] == 'conflicting duplicate logical key' and refused['exception']['physical_line'] == allowed['first_conflict_line'], f'{name}: refusal changed')
        for flag in ('raw_preserved', 'processing_absent', 'observation_ref_absent', 'published_pointer_absent'):
            require(refused[flag] is True, f'{name}: refusal state changed: {flag}')
        store = BASE / 'verification/sdd-history/retained-parser-preflight/transform-refusal' / name
        raw = safe_path(store / 'objects', refused['raw_reference'])
        require(identity(raw) == {'bytes': allowed['bytes'], 'sha256': allowed['sha256']}, f'{name}: actual stored raw mismatch')
        error_path = safe_path(store / 'objects', refused['quarantine_error_ref'])
        require(identity(error_path)['sha256'] == refused['quarantine_error_sha256'], f'{name}: quarantine hash mismatch')
        error = read_json(error_path)
        require(error == refused['quarantine_error'] and error['code'] == 'transform_failed' and error['details']['line_number'] == allowed['first_conflict_line'] and error['details']['raw_sha256'] == allowed['sha256'], f'{name}: actual quarantine mismatch')
        with sqlite3.connect(f'file:{store / "state.sqlite3"}?mode=ro&immutable=1', uri=True) as connection:
            partitions = [r[0] for r in connection.execute('SELECT partition FROM records')]
        require(len(partitions) == 2 and {p.rsplit(':', 1)[-1] for p in partitions} == {'Binding', 'Snapshot'}, f'{name}: actual accepted state/pointer found')
        require(not list((store / 'objects').glob('curated/**/*')), f'{name}: curated output found')
        observed.append({**allowed, 'outcome': 'quarantined whole source', 'raw_original_verified': True, 'processing_absent': True, 'observation_ref_absent': True, 'published_pointer_absent': True, 'quarantine_error': identity(error_path), 'retained_sqlite': identity(store / 'state.sqlite3')})
    return observed


def check_implementation(receipt):
    audit = read_json(BASE / 'final-review-fix1/audit.json')
    full = read_json(BASE / 'final-review-fix1/full-check/command.json')
    installed = read_json(BASE / 'final-review-fix1/installed/report.json')
    require(audit['head'] == REVIEWED and full['exit'] == installed['exit'] == 0, 'reviewed implementation proof failed')
    require(full['network_guard'] and installed['network_guard'], 'implementation proof guard missing')
    report_text = (BASE / 'final-review-fix1/report.md').read_text()
    require('452 tests in163.537s' in report_text, 'current full-test proof mismatch')
    for name, expected in audit['sources_tests_docs'].items():
        path = ROOT / name
        if name == 'docs/runbooks/sec-edgar-etl-publication.md':
            path = AMENDMENT / 'originals/sec-edgar-etl-publication.md'
        require(identity(path) == expected, f'reviewed implementation artifact changed: {name}')
    domains = ['packages/sec-edgar-ingest', 'conf', 'tests', 'fixtures', 'scripts', 'README.md', 'pyproject.toml', 'uv.lock', '.python-version']
    changed = subprocess.check_output(['git', 'diff', '--name-only', REVIEWED, '--', *domains], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '--', *domains], cwd=ROOT, text=True).splitlines()
    require(not changed and not untracked, f'production/tests/config/metadata changed: {changed + untracked}')
    require(identity(ROOT / 'dist' / installed['wheel_name']) == installed['wheel'], 'reviewed wheel changed')
    return {'reviewed_commit': REVIEWED, 'unchanged_audited_files': len(audit['sources_tests_docs']) - 1, 'unchanged_git_domains': domains, 'historical_full_tests': 452, 'historical_full_check_exit': full['exit'], 'historical_installed_exit': installed['exit'], 'wheel': installed['wheel']}


def check_documents(receipt):
    for original, record in receipt['originals'].items():
        require(identity(safe_path(ROOT, record['resolution'])) == {'bytes': record['bytes'], 'sha256': record['sha256']}, f'original document changed: {original}')
    spec = ROOT / 'specs/sec-filing-index-ingestion-stage-3-spec.md'
    original = (AMENDMENT / 'originals/sec-filing-index-ingestion-stage-3-spec.md').read_text()
    current = spec.read_text()
    for text in (original, current):
        require(text.count('## 8. Verification and delivery gates') == text.count('## 9. Rollout note') == 1, 'spec section structure changed')
    require(current.split('## 8. Verification and delivery gates')[0] == original.split('## 8. Verification and delivery gates')[0], 'spec modified before acceptance section')
    require(current.split('## 9. Rollout note')[1] == original.split('## 9. Rollout note')[1], 'spec modified after acceptance section')
    require('**COMPLETE' not in current.split('## 8. Verification and delivery gates')[1], 'completion stamped by amendment')
    for source in receipt['allowlisted_sources']:
        require(source['sha256'] in current and source['receipt_id'] in current, 'spec exact source binding missing')
    prior_runbook = (AMENDMENT / 'originals/sec-edgar-etl-publication.md').read_text().split('\n\n')
    current_runbook = (ROOT / 'docs/runbooks/sec-edgar-etl-publication.md').read_text().split('\n\n')
    require(len(prior_runbook) == len(current_runbook), 'runbook paragraph structure changed')
    changes = [old for old, new in zip(prior_runbook, current_runbook, strict=True) if old != new]
    require(len(changes) == 2 and changes[0].startswith('Stage 3 acceptance remains **blocked**:') and changes[1].startswith('The specimen acceptance result currently exits 1'), 'runbook modified outside authorized acceptance paragraphs')
    for relative in ('specs/sec-filing-index-ingestion-stage-3-spec.md', 'specs/evidence/sec-filing-index-ingestion/stage-3/verification.md', 'docs/runbooks/sec-edgar-etl-publication.md'):
        text = ' '.join((ROOT / relative).read_text().split())
        require('retaining strict' in text and 'blockers' in text and 'reserved' in text, f'current documentary acceptance constraints missing: {relative}')
        OBSERVED[relative] = identity(ROOT / relative)


def run_verification():
    receipt = read_json(AMENDMENT / 'owner-amendment.json')
    validate_receipt(receipt)
    try:
        socket.getaddrinfo('example.invalid', 443)
    except AssertionError:
        guard_denied_dns = True
    else:
        raise ValueError('network guard failed to deny DNS')
    mapping = read_json(AMENDMENT / 'historical-resolution.json')
    require(mapping['exceptions'] == {'verification.md': 'acceptance-amendment/originals/verification.md'}, 'historical resolution expanded')
    require(mapping['inventory_identity'] == receipt['immutable_manifests']['delivery-sha256.json'], 'historical inventory binding mismatch')
    inventories = {}
    for name, expected in receipt['immutable_manifests'].items():
        relocation = mapping['exceptions'] if name == 'delivery-sha256.json' else None
        inventories[name] = verify_inventory(name, expected, relocation, name in ('verification/sha256.json', 'final-review-fix1/sha256.json', 'review-checkpoint/sha256.json'))
    require(inventories['verification/sha256.json']['records'] == 7525 and inventories['verification/sha256.json']['inventory']['sha256'] == '4554adb90acdda3e44bffac01bb878d3391d4ae523e0c4439aa4e1ab2c612b6b', 'frozen verification binding changed')
    sources = check_sources(receipt)
    implementation = check_implementation(receipt)
    check_documents(receipt)
    return {'acceptance': 'PASS: exact documented quarantines allowed; strict whole-source refusal retained', 'original_specimen_exit': 1, 'full_scan_rows': 970622, 'conflicts': 51, 'classification': {'form_type_only': 45, 'company_name_only': 6}, 'sources': sources, 'immutable_inventories': inventories, 'implementation': implementation, 'negative_cases_rejected': check_negative_cases(receipt), 'guard_denied_dns': guard_denied_dns, 'input_hashes': OBSERVED, 'all22_stage7_checks': 'reserved', 'live_access': 'closed', 'successful_catalog_range_established': False, 'deployed_capacity_established': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'refuse existing report to preserve prior results')
    started = time.perf_counter()
    report = {'argv': sys.argv, 'cwd': str(Path.cwd()), 'executable': sys.executable, 'python': sys.version, 'platform': platform.platform(), 'network_guard': True, 'dependencies': {name: importlib.metadata.version(name) for name in ('pyarrow', 'requests', 'azure-identity', 'azure-storage-blob', 'azure-data-tables')}}
    try:
        require(sys.version_info[:2] == (3, 14), 'selected runtime must be Python 3.14')
        require(report['dependencies'] == {'pyarrow': '25.0.1', 'requests': '2.34.2', 'azure-identity': '1.26.0', 'azure-storage-blob': '12.31.0', 'azure-data-tables': '12.7.0'}, 'offline cached dependencies mismatch')
        report.update(run_verification())
        report['exit'] = 0
    except Exception as error:
        report.update(exit=1, error_type=type(error).__name__, error=str(error))
    report['runtime_seconds'] = time.perf_counter() - started
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
    return report['exit']


if __name__ == '__main__':
    raise SystemExit(main())
