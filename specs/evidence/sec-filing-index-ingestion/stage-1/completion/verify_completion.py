"""Read-only Stage 1 acceptance/retirement boundary checks; no deployment proof."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-1'
COMPLETION = BASE / 'completion'
PLAN = 'specs/plans/completed/1-sec-filing-index-ingestion-stage-1-spec.md'
SPEC = 'specs/completed/sec-filing-index-ingestion-stage-1-spec.md'
ROADMAP = 'specs/sec-filing-index-ingestion-roadmap.md'
FINDING = 'specs/sec-filing-index-ingestion-stage-1-findings.md'
FINDING_HASH = '939a724eccf22147015a59d5940ed57f02cc4e9fe9d942a9cd78ae73c34615ff'
MANIFEST_HASH = '124e96041548daba8216aa495fc69021751555b0f0e4c890ac85e934f512a131'
CONSISTENCY_HEADING = '\n## Stage 1 completion and later-stage consistency\n'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def check_records(records: list[dict], aliases: dict[str, str]) -> int:
    for record in records:
        path = ROOT / aliases.get(record['path'], record['path'])
        assert path.is_file(), f'Missing retained record: {path}'
        assert path.stat().st_size == record['bytes'], f'Byte count changed: {path}'
        assert digest(path) == record['sha256'], f'Hash changed: {path}'
    return len(records)


def git(*args: str) -> str:
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def check_acceptance() -> int:
    acceptance = read_json(BASE / 'final-candidate/owner-acceptance.json')
    assert acceptance['owner'] == 'Lowell Mason'
    assert acceptance['owner_message'] == 'Approved'
    assert acceptance['accepted_revision'] == 'F1'
    assert acceptance['accepted_date'] == '2026-10-05'
    assert acceptance['accepted_finding']['sha256'] == FINDING_HASH
    assert acceptance['accepted_evidence_manifest']['sha256'] == MANIFEST_HASH
    manifest_path = ROOT / acceptance['accepted_evidence_manifest']['path']
    assert digest(manifest_path) == MANIFEST_HASH
    immutable_finding = acceptance['immutable_finding']
    assert digest(ROOT / immutable_finding) == FINDING_HASH
    live = (ROOT / FINDING).read_bytes()
    frozen = (ROOT / immutable_finding).read_bytes()
    assert live.startswith(frozen), 'Accepted technical bytes changed'
    assert b'## 10.' in live[len(frozen):], 'Acceptance appendix missing'
    records = read_json(manifest_path)['records']
    assert len(records) == 1584
    return check_records(records, {FINDING: immutable_finding})


def check_preservation(context: dict) -> int:
    aliases = {record['path']: record['retained_path'] for record in context['before_documents']}
    check_records(context['before_documents'], aliases)
    for record in context['mutable_process_receipts']:
        aliases[record['path']] = record['retained_path']
        check_records([record], aliases)
        retained = read_json(ROOT / record['retained_path'])
        current = read_json(ROOT / record['path'])
        before_completion = retained.pop('completion')
        current_completion = current.pop('completion')
        assert retained == current, 'Controller process receipt changed outside authorized completion field'
        assert current_completion == before_completion or 'COMPLETE' in current_completion
    records = read_json(ROOT / context['task7_before_manifest'])['records']
    assert len(records) == 1592
    check_records(records, aliases)
    deleted = []
    for record in context['protected_tracked_paths']:
        path = ROOT / aliases.get(record['path'], record['path'])
        if record['present']:
            assert path.is_file(), f'Protected tracked path missing: {path}'
            assert digest(path) == record['sha256'], f'Protected tracked path changed: {path}'
        else:
            assert not path.exists(), f'Original deletion restored: {path}'
            deleted.append(record['path'])
    assert len(deleted) == 4
    assert all(path.startswith('packages/sec-edgar-index-ingest/') for path in deleted)
    protected = read_json(BASE / 'protected-before-state.json')
    for record in protected['protected_documents']:
        path = ROOT / aliases.get(record['path'], record['path'])
        assert digest(path) == record['sha256'], f'Original protected hash changed: {path}'
    for record in protected['original_worktree']:
        path = ROOT / aliases.get(record['path'], record['path'])
        if record['before_status'] == 'deleted':
            assert not path.exists(), f'Original package deletion restored: {path}'
        else:
            assert digest(path) == record['sha256'], f'Original worktree hash changed: {path}'
    approved = subprocess.run(
        ['git', 'show', f"{protected['approval_head']}:specs/sec-filing-index-ingestion-stage-1-spec.md"],
        cwd=ROOT, capture_output=True,
    )
    assert approved.returncode == 0, approved.stderr
    assert hashlib.sha256(approved.stdout).hexdigest() == protected['approved_spec_sha256']
    ancestry = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', protected['approval_head'], 'HEAD'],
        cwd=ROOT, capture_output=True,
    )
    assert ancestry.returncode == 0, 'Original approval is not ancestral to observed HEAD'
    assert not (ROOT / '.venv').exists() and not (ROOT / 'uv.lock').exists()
    return len(records)


def check_retirement(context: dict) -> dict:
    plan = (ROOT / PLAN).read_text()
    spec = (ROOT / SPEC).read_text()
    roadmap = (ROOT / ROADMAP).read_text()
    before_roadmap = (COMPLETION / 'before' / Path(ROADMAP).name).read_text()
    completion_date = context['completion_date']
    assert f'**Status: COMPLETE ({completion_date})** — executed via subagent-driven-development; nothing deferred' in plan
    assert f'**Status: COMPLETE ({completion_date})**' in spec
    assert not (ROOT / 'specs/plans/1-sec-filing-index-ingestion-stage-1-spec.md').exists()
    assert not (ROOT / 'specs/sec-filing-index-ingestion-stage-1-spec.md').exists()
    assert not list((ROOT / 'specs/plans').glob('*-sec-filing-index-ingestion-stage-1-spec.md'))
    steps = re.findall(r'^- \[([ x])\] \*\*Step ', plan, re.MULTILINE)
    before_plan = (COMPLETION / 'before' / Path(PLAN).name).read_text()
    assert len(steps) == len(re.findall(r'^- \[ \] \*\*Step ', before_plan, re.MULTILINE))
    assert steps and all(mark == 'x' for mark in steps)
    assert f'Stage 1: COMPLETE ({completion_date}) — implemented by plan 1' in spec
    for required in [PLAN, FINDING, FINDING_HASH, MANIFEST_HASH, 'revision F1', 'accepted 2026-10-05', 'Next: resume the roadmap.']:
        assert required in spec, f'Completion stamp missing: {required}'
    assert CONSISTENCY_HEADING in roadmap
    baseline, note = roadmap.split(CONSISTENCY_HEADING, 1)
    assert baseline.replace('- [x] Stage 1:', '- [ ] Stage 1:') == before_roadmap.rstrip('\n')
    stages = re.findall(r'^- \[([ x])\] Stage (\d):', roadmap, re.MULTILINE)
    assert stages == [('x', '1'), *[(' ', str(number)) for number in range(2, 9)]]
    for required in ['F1', FINDING_HASH, 'Stage 2', 'Stage 7', 'historical baseline', 'owner']:
        assert required in note
    return {'completed_steps': len(steps), 'roadmap_checked_stages': [1], 'later_stage_definitions': 'byte-identical'}


def check_links() -> int:
    checked = 0
    for document in [PLAN, SPEC, ROADMAP, FINDING]:
        path = ROOT / document
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                continue
            target, _, fragment = link.partition('#')
            resolved = path.parent / target.strip('<>')
            assert resolved.exists(), f'Broken local link: {document}: {link}'
            if fragment:
                headings = re.findall(r'^#+\s+(.+)$', resolved.read_text(), re.MULTILINE)
                anchors = [re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-') for heading in headings]
                assert fragment in anchors, f'Broken local heading: {document}: {link}'
            checked += 1
    return checked


def check_reserved_obligations() -> int:
    rows = re.findall(r'^\| S7-(\d\d) .*$', (BASE / 'stage-7-checks.md').read_text(), re.MULTILINE)
    assert rows == [f'{number:02d}' for number in range(1, 23)]
    lines = [line for line in (BASE / 'stage-7-checks.md').read_text().splitlines() if line.startswith('| S7-')]
    assert all(line.endswith('| reserved/not_run |') for line in lines)
    assert not (ROOT / 'specs/deferred_items.md').exists(), 'Backlog boundary changed; inspect/tick explicitly'
    return len(rows)


def main() -> None:
    context = read_json(COMPLETION / 'context.json')
    accepted_records = check_acceptance()
    preserved_records = check_preservation(context)
    retirement = check_retirement(context)
    links = check_links()
    reserved = check_reserved_obligations()
    for document in [PLAN, SPEC, ROADMAP, str(Path(__file__).relative_to(ROOT))]:
        for number, line in enumerate((ROOT / document).read_text().splitlines(), 1):
            assert line.rstrip() == line, f'Trailing whitespace: {document}:{number}'
    assert not git('diff', '--cached', '--name-only'), 'Staged changes exist before controller review'
    git('diff', '--check')
    assert not git('ls-files', '--', ROADMAP), 'Roadmap was incidentally tracked'
    status = git('status', '--porcelain=v1')
    assert f'?? {ROADMAP}\n' in status, 'Roadmap not untracked'
    print(json.dumps({'result': 'PASS', 'scope': 'offline acceptance/retirement documentation; no production build/tests or Stage7 proof', 'completion_date': context['completion_date'], 'accepted_manifest_hash': MANIFEST_HASH, 'accepted_manifest_records': accepted_records, 'task7_before_records_preserved': preserved_records, 'protected_tracked_paths': len(context['protected_tracked_paths']), **retirement, 'local_links_resolved': links, 'stage7_reserved_not_run': reserved, 'backlog': {'exists': False, 'open': 0, 'closure_rate': None, 'aged_open': 0}, 'git_diff_check': 'PASS', 'staged_paths': [], 'roadmap_tracking': 'untracked', 'head_observed': git('rev-parse', 'HEAD').strip(), 'controller_review_commit_archive': 'not asserted by this checker'}, indent=2))


if __name__ == '__main__':
    main()
