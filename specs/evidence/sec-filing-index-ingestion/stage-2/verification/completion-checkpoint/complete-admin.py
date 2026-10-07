"""Administrative Stage 2 completion; no runtime, build or test changes."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path('/Users/lowell/.codex/worktrees/sec-edgar-stage-2/sec-edgar')
PRIMARY = Path('/Users/lowell/Projects/sec-edgar')
SDD = ROOT / '.sdd/2-sec-filing-index-ingestion-stage-2-spec'
EVIDENCE = SDD / 'completion-evidence'
CHECKPOINT = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint'
REVIEWED = 'e458010ead6709c16e992fa22a33997d3aa36ef0'
ORIGINAL_ROADMAP_SHA = 'e4fdf810785daa3700a92c96b65e08f671f4afbdfe273eed6154dcd255a9cf02'
DELETIONS = ['packages/sec-edgar-index-ingest/README.md', 'packages/sec-edgar-index-ingest/pyproject.toml',
    'packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/__init__.py',
    'packages/sec-edgar-index-ingest/src/sec_edgar_index_ingest/py.typed']
OLD_PLAN = Path('specs/plans/2-sec-filing-index-ingestion-stage-2-spec.md')
NEW_PLAN = Path('specs/plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md')
OLD_SPEC = Path('specs/sec-filing-index-ingestion-stage-2-spec.md')
NEW_SPEC = Path('specs/completed/sec-filing-index-ingestion-stage-2-spec.md')

def sha(body):
    return hashlib.sha256(body).hexdigest()

def command(argv, cwd=ROOT):
    return subprocess.check_output(argv, cwd=cwd)

def record(path):
    body = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(body), 'sha256': sha(body)}

def save(path, value):
    assert not path.exists(), path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    assert Path.cwd().resolve() == ROOT
    assert command(['git', 'rev-parse', 'HEAD']).decode().strip() == REVIEWED
    assert command(['git', 'diff', '--cached', '--name-only']) == b''
    expected_status = [' D ' + name for name in DELETIONS]
    assert command(['git', 'status', '--short']).decode().splitlines() == expected_status
    resolution_path = SDD / 'whole-branch-review-resolution.json'
    resolution = json.loads(resolution_path.read_text())
    assert resolution['composed_whole_branch_spec'] == resolution['composed_whole_branch_quality'] == 'PASS'
    assert resolution['fresh_scoped_review']['head'] == REVIEWED
    assert resolution['fresh_scoped_review']['findings'] == {'W-I1': 'ADDRESSED', 'W-I2': 'ADDRESSED', 'W-M1': 'ADDRESSED'}
    assert not resolution['fresh_scoped_review']['new_findings']
    assert all(not value for value in resolution['resolve_before_defer'].values())
    assert resolution['completion_protocol'] == 'released'
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo('America/New_York'))
    completion_date = local.date().isoformat()
    assert completion_date == '2026-10-06', completion_date
    EVIDENCE.mkdir()
    CHECKPOINT.mkdir()
    (CHECKPOINT / 'complete-admin.py').write_bytes(Path(__file__).read_bytes())
    save(EVIDENCE / 'clock-and-gate.json', {'recorded_at_utc': now.isoformat(), 'completion_local': local.isoformat(),
        'completion_timezone': 'America/New_York', 'completion_date': completion_date,
        'actual_clock_tool_utc': '2026-10-07 01:02:42 UTC', 'reviewed_head': REVIEWED,
        'resolution': record(resolution_path), 'resolve_before_defer': resolution['resolve_before_defer'],
        'second_review_seat': resolution['second_seat'], 'execution_scope': 'administrative documentation/retention only'})
    stats_argv = ['.venv/bin/python', '/Users/lowell/.agents/skills/writing-plans/scripts/deferred_stats.py']
    stats = subprocess.run(stats_argv, cwd=ROOT, capture_output=True, text=True)
    assert stats.returncode == 0 and not (ROOT / 'specs/deferred_items.md').exists()
    assert stats.stdout == 'Deferred backlog: no specs/deferred_items.md in this repo — nothing deferred.\n'
    save(EVIDENCE / 'deferred-stats.json', {'argv': stats_argv, 'cwd': str(ROOT), 'stdout': stats.stdout,
        'stderr': stats.stderr, 'exit_code': stats.returncode, 'runtime': sys.version,
        'runtime_adaptation': 'Existing local .venv Python used instead of downloading Python 3.13 with uv.',
        'exists': False, 'open': 0, 'closed': 0, 'closure_rate': None, 'aged_open_over_45_days': 0,
        'prior_item_ticking_pass': 'No backlog file exists; no earlier items to tick.',
        'nothing_deferred': True, 'no_backlog_created': True, 'triage_required': False})
    names = command(['git', 'ls-tree', '-r', '--name-only', REVIEWED]).decode().splitlines()
    selected = [name for name in names if name.startswith(('packages/sec-edgar-ingest/', 'packages/sec-edgar-client/',
        'packages/sec-edgar-download/', 'conf/', 'scripts/')) or name in ['pyproject.toml', 'uv.lock', 'README.md', '.gitignore',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification/fixture-sequence.py',
        'specs/evidence/sec-filing-index-ingestion/stage-2/verification/installed-wheel-proof.py']]
    source_files = []
    for name in selected:
        body = (ROOT / name).read_bytes()
        assert body == command(['git', 'show', f'{REVIEWED}:{name}']), name
        source_files.append(record(ROOT / name))
    source_receipt = json.loads((ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/source-revisions.json').read_text())
    assert source_receipt['current_prescribed_check']['test_records'] == 302
    assert source_receipt['current_prescribed_check']['command']['exit'] == 0
    check = source_receipt['current_prescribed_check']
    for name in ('stderr', 'stdout'):
        item = check[name]
        body = (ROOT / item['path']).read_bytes()
        assert len(body) == item['bytes'] and sha(body) == item['sha256']
    footer = (ROOT / check['stderr']['path']).read_text()
    assert 'Ran 302 tests in 106.619s' in footer and '\nOK\n' in footer
    save(EVIDENCE / 'tested-reviewed-source-equality.json', {'recorded_at': now.isoformat(), 'reviewed_head': REVIEWED,
        'last_implementation_head': source_receipt['last_implementation_head'], 'current_prescribed_check': check,
        'no_runtime_build_test_or_existing_helper_changes': True, 'files_equal_reviewed_head': source_files,
        'all19_package_sources_equal_current_wheel_and_sdist': source_receipt['all19_sources_equal_current_wheel_and_sdist'],
        'fresh_installed_bundle': source_receipt['fresh_installed_bundle'], 'fresh_combined_bundle': source_receipt['fresh_combined_bundle'],
        'owner_yes': source_receipt['owner_yes'], 'no_suite_install_or_acquisition_rerun': True})
    plan_path, spec_path = ROOT / OLD_PLAN, ROOT / OLD_SPEC
    plan_before, spec_before = plan_path.read_bytes(), spec_path.read_bytes()
    (EVIDENCE / 'plan-before.md').write_bytes(plan_before)
    (EVIDENCE / 'spec-before.md').write_bytes(spec_before)
    plan = plan_before.decode()
    steps = re.findall(r'^- \[([ xX])\] \*\*Step (\d+): (.*)$', plan, re.M)
    assert len(steps) == 33 and all(mark == ' ' for mark, _, _ in steps)
    live_plans = list((ROOT / 'specs/plans').glob('*-sec-filing-index-ingestion-stage-2-spec.md'))
    assert live_plans == [plan_path]
    status = f'**Status: COMPLETE ({completion_date})** — executed via subagent-driven-development; nothing deferred'
    plan = re.sub(r'^\*\*Status:\*\*.*$', status, plan, count=1, flags=re.M)
    plan = plan.replace('**Owner approval record:**', '> Historical approval record: the paragraph below preserves the approved planning receipt; the completion status and evidence above/below supersede its then-pending execution statements.\n\n**Owner approval record:**', 1)
    plan = plan.replace('## Reconciled baseline and execution boundary\n', '## Reconciled baseline and execution boundary\n\nThis section preserves the historical planning baseline and execution handoff. Current completion, interfaces and review results are recorded in the completion evidence.\n', 1)
    deviations = {
        (1, 3): 'Exact acquisition pins were retained; local verification used macOS 26.6.2 arm64/Python 3.14.0, distinct from accepted Linux amd64/Python 3.14.8 evidence and a future worker image.',
        (2, 2): 'RunContext adds deeply immutable effective_config and pinned_on; make_source_workset accepts keyword-only acquisition_mode, copied into SnapshotWorkset, with strict shared source/directory/raw-period identity validation.',
        (3, 3): 'AzureStateStore accepts keyword-only objects/observer and keeps legacy small Payload rows; oversized whole records use verified canonical worksets/state/sha256=<hash>.json objects plus one bounded Table descriptor with actual ETag CAS.',
        (4, 2): 'TimeBounds and LeaseHandle upper observations bound takeover; Azure clean release retains the full unsafe_until guard because journal update and release are separate operations, while local release_clean is atomic.',
        (5, 3): 'Coordinator.exchange adds keyword-only on_response and a shared fail-closed policy latch; durable request_history/begin_request retain retry ordinals and server delays across attempts without reusing historical host-monotonic values.',
        (6, 3): 'AcquisitionState adds discovery_session/begin_discovery/directory_gap/finish_discovery and record_directory evidence/selection/expected_gap keywords; immutable origin provenance is verified on cached recovery.',
        (7, 2): 'collection.stage_receipt adds optional keyword-only request_id; production supplies the verified actual transport reservation and omission fails closed, preserving BodyReceipt and write-once Binding identity.',
        (8, 4): 'Generated synthetic configs keep relative storage.root with absolute fixture --state-dir and explicit clock/deadline override flags; quarterly uses 2015Q1 and owner-approved dailyend=open uses 2026-10-06, with the exact Yes receipt retained.',
        (8, 5): 'The latest post-fix prescribed check passed 302 tests; fresh installed-wheel and approved combined/process/recovery proofs cover the final source, and fresh GPT-6.1 Max default-role fallback review closed all findings; same-family Codex CLI second seat was explicitly skipped.',
    }
    task = 0
    lines = []
    written_notes = []
    for line in plan.splitlines(keepends=True):
        match = re.match(r'### Task (\d+):', line)
        if match:
            task = int(match.group(1))
        step = re.match(r'- \[ \] \*\*Step (\d+):', line)
        if step:
            line = line.replace('- [ ] **Step', '- [x] **Step', 1)
        lines.append(line)
        if step and (task, int(step.group(1))) in deviations:
            key = task, int(step.group(1))
            lines.append('\n> Deviation: ' + deviations[key] + '\n')
            written_notes.append({'task': key[0], 'step': key[1], 'note': deviations[key]})
    plan = ''.join(lines)
    assert len(written_notes) == len(deviations)
    assert re.findall(r'```.*?```', plan_before.decode(), re.S) == re.findall(r'```.*?```', plan, re.S)
    plan_path.write_text(plan)
    spec = spec_before.decode()
    spec = re.sub(r'^\*\*Status:\*\*.*$', status, spec, count=1, flags=re.M)
    spec = spec.replace('**Owner approval record:**', '> Historical approval record: this paragraph retains the original authorization and its then-pending execution status. The completed rollout stamp and retained verification below supply current Stage 2 evidence.\n\n**Owner approval record:**', 1)
    spec = spec.replace('## 1. Resume/reconcile record\n', '## 1. Resume/reconcile record\n\nThis is the historical planning-time reconciliation record. Its scaffold, unticked-stage and protected-roadmap statements describe that baseline; §§5–6 record the completed Stage 2 result and the one authorized local checkbox reconciliation.\n', 1)
    spec = spec.split('## 5. Completion gates and rollout reference\n', 1)[0]
    spec += f'''## 5. Completion gates and rollout reference

> Stage 2: COMPLETE ({completion_date}) — implemented by [plan 2](plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md).
> Acquisition verification/review evidence: [verification report](evidence/sec-filing-index-ingestion/stage-2/verification.md), reviewed revision `{REVIEWED}`, and [branch-shared completion receipt](evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/completion-receipt.json).
> Next: resume the [roadmap](sec-filing-index-ingestion-roadmap.md).

All eight tasks and their Spec/Quality reviews are resolved. The latest prescribed offline check after the last implementation change passed all 302 tests in 106.619 seconds and completed build, CLI and whitespace checks with exit 0; its wrapper elapsed time was 106.99618458282202 seconds. The retained stderr SHA-256 is `dbd06ab5e7211f84abbb04ead35838721937e0ec54abe914cd20896403a6273a`. Documentation completion did not rerun acquisition, installation or the test suite; the completion receipt verifies the runtime, build inputs, tests and existing proof drivers equal the tested and reviewed revision.

Fresh [installed-wheel proof](evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-wheel-n0zc5qlc/sha256-manifest.json), [approved combined fixture sequence](evidence/sec-filing-index-ingestion/stage-2/verification/sec-edgar-stage-2-46bhxh8j/sha256-manifest.json) and [process/recovery inspection](evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/sdd/final-review-fix1-evidence/process-proof-inspection.json) retain exact bytes, versions, command exits, real local CAS losers, killed-child lifetime/takeover and crash-boundary recovery. Installed and combined manifests are respectively `126a1c3c666e1e41f63d37f68ec95ec145f55a28ec6a1ea97676fa9941caff47` and `beee194e1a67f1870c2b1d948c9ea29044f6ba0b6d9da0008443ccb13a8d4ab7`.

The [original full review](evidence/sec-filing-index-ingestion/stage-2/verification/final-review-fix1-checkpoint/sdd/whole-branch-review-9098fe9.md) and fresh [scoped final review](evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/sdd/final-review-fix1-rereview.md) jointly resolve W-I1, W-I2 and W-M1 as ADDRESSED with no new findings. The controller's [composed verdict](evidence/sec-filing-index-ingestion/stage-2/verification/completion-checkpoint/sdd/whole-branch-review-resolution.json) is Spec PASS and Quality PASS. Both required final reviewers used fresh GPT-6.1 Max (`gpt-6.1-sol`, effort `max`); unavailable `code-reviewer` role routing used the explicitly recorded default-role fallback. The Codex CLI second seat was SKIPPED under the same-family rule, with no second-review claim. No skipped/descoped step, unfixed finding, unanswered owner decision or deferred item remains. Backlog inspection found no `specs/deferred_items.md`; no empty backlog was created.

The separate daily endpoint answer is the owner's exact **“Yes”**, retained in the [owner receipt](evidence/sec-filing-index-ingestion/stage-2/verification/task-8-i1-checkpoint/sdd/task-8-daily-endpoint-owner-answer.json), SHA-256 `f9720b21df9f56135386496f39bb2ec4d310614410b1b5f8645fdc07a7b963ac`. Its controller-recorded `2026-10-06T23:03:32+00:00` is receipt provenance, not an owner-authored time of day. The sequence uses separate quarterly 2015Q1 and daily-end-open synthetic configurations with unchanged canonical source/workset/pin contracts.

Only Stage 2's implementing plan and spec are retired. The parent design, ADR, accepted F1/evidence and roadmap remain active. The local/untracked roadmap receives exactly its Stage 2 checkbox after this authoritative stamp. Stop at this completion boundary; a later stage requires the owner to request “resume the roadmap.”

## 6. Completed interfaces and later-stage consistency

The delivered package provides validated `discover`/`collect` commands, immutable source and snapshot worksets, durable source/discovery/attempt/result state, original-byte raw promotion and one write-once member binding. `RunContext` includes immutable `effective_config` and `pinned_on`; discovery checkpoint APIs preserve frozen origin provenance, and collection staging obtains a verified actual request reservation through keyword-only `request_id`. Azure state uses old small inline Payload entities or content-first verified whole-record objects at internal `worksets/state/sha256=<hash>.json` paths and a single property/entity-bounded Table descriptor with actual ETag CAS. Approved source/snapshot/raw paths and identities are unchanged.

Step-level deviations in retired plan 2 record the actual shared interfaces, conservative Azure release guard and corrected explicit fixture invocation. Azure journal mutation and lease release are separate operations, so Azure successors retain the full `unsafe_until` wait; local `release_clean` can atomically finalize the journal and release. Fixture configs use relative configured storage roots plus an absolute fixture-only state directory and explicit synthetic clock/deadline override markers. Local evidence was produced on macOS 26.6.2 arm64/Python 3.14.0 with the accepted acquisition pins; it is distinct from Linux amd64/Python 3.14.8 compatibility evidence and a future worker image. These execution deviations defer no safeguard.

Revalidation below is read-only consistency against shipped Stage 2 interfaces and the existing roadmap definitions. Every later checkbox remains unticked; no later-stage design or implementation begins here.

| Unticked stage | Revalidation against completed Stage 2 |
|---|---|
| 3 — Replayable ETL and safe publication | Pinned original snapshots, source/snapshot worksets and state interfaces are available. Deterministic row parsing, canonical observations, generation builder/publisher/reader and golden/raw-only replay remain this stage's existing R3/R6/R9 exits. F1's bounded families, date and nullable-accession obligations remain. |
| 4 — Backfill and daily catch-up workflows | Acquisition can resume unresolved work and preserves failed-directory boundaries, handoff/overlap and pending older sources. Composition with Stage 3 publication and manually runnable historical/daily workflows with R1/R2 evidence remains required. |
| 5 — Reconciliation and withdrawal approval | Immutable pins and absence/failure outcomes preserve the parent safeguards. Reconciliation workflow, corrected deltas, hash-bound candidate/approval records, stale replay/reintroduction and shared R5/R7/R10 evidence remain required. |
| 6 — Azure orchestration and deployment definitions | Azure data-plane adapters and acquisition results are delivered. A pinned complete-worker image, versioned resources/identities, ADF start/poll/result handling, disabled triggers, telemetry/alerts and R4/R11 delivery checks remain required. |
| 7 — Deployment checkpoint and recovery evidence | Local/mock proof does not discharge any of the [22 reserved integrated checks](evidence/sec-filing-index-ingestion/stage-1/stage-7-checks.md). Effective identity/network/owner-wide lease/CAS/HNS behavior, actual worker memory/runtime/temporary space, bounded live smoke and integrated replay/approval/rollback/runbooks remain reserved. |
| 8 — Baseline and scheduled-operation acceptance | No accepted production coverage or observed enabled schedules follows from fixtures. Accepted baseline/catch-up/reconciliation reports, controlled trigger enablement and matching durable scheduled reports/logs remain required. |
'''
    spec_path.write_text(spec)
    assert status in spec_path.read_text() and f'> Stage 2: COMPLETE ({completion_date})' in spec_path.read_text()
    stamped_at = datetime.now(timezone.utc).isoformat()
    stamp_record = record(spec_path)
    roadmap_receipts = []
    old_line = b'- [ ] Stage 2: Durable discovery and collection'
    new_line = b'- [x] Stage 2: Durable discovery and collection'
    for root in (PRIMARY, ROOT):
        path = root / 'specs/sec-filing-index-ingestion-roadmap.md'
        before = path.read_bytes()
        before_mode = stat.S_IMODE(path.stat().st_mode)
        assert sha(before) == ORIGINAL_ROADMAP_SHA and before.count(old_line) == 1
        assert not before.count(new_line)
        after = before.replace(old_line, new_line, 1)
        assert [line for line in after.decode().splitlines() if re.match(r'^- \[ \] Stage [3-8]:', line)] == [line for line in before.decode().splitlines() if re.match(r'^- \[ \] Stage [3-8]:', line)]
        assert len(re.findall(rb'^- \[ \] Stage [3-8]:', after, re.M)) == 6
        if not before_mode & stat.S_IWUSR:
            path.chmod(before_mode | stat.S_IWUSR)
        path.write_bytes(after)
        path.chmod(before_mode)
        assert path.read_bytes() == after and stat.S_IMODE(path.stat().st_mode) == before_mode
        roadmap_receipts.append({'root': str(root), 'path': 'specs/sec-filing-index-ingestion-roadmap.md',
            'before_sha256': sha(before), 'after_sha256': sha(after), 'before_bytes': len(before), 'after_bytes': len(after),
            'before_line': old_line.decode(), 'after_line': new_line.decode(), 'occurrences_changed': 1,
            'all_other_bytes_identical': after.replace(new_line, old_line, 1) == before,
            'mode_before': oct(before_mode), 'mode_after': oct(stat.S_IMODE(path.stat().st_mode)),
            'stage3_through_stage8_remain_unticked': True, 'spec_stamp_verified_before_edit_at': stamped_at,
            'authoritative_active_spec_stamp': stamp_record, 'never_staged': True})
    save(EVIDENCE / 'roadmap-exact-checkbox.json', {'recorded_at': datetime.now(timezone.utc).isoformat(), 'files': roadmap_receipts})
    # Only the named plan/spec are moved/staged; the roadmap remains local.
    command(['git', 'mv', '--', str(OLD_PLAN), str(NEW_PLAN)])
    command(['git', 'mv', '--', str(OLD_SPEC), str(NEW_SPEC)])
    plan = (ROOT / NEW_PLAN).read_text()
    plan_links = {
        '../sec-filing-index-ingestion-stage-2-spec.md': '../../completed/sec-filing-index-ingestion-stage-2-spec.md',
        '../sec-filing-index-ingestion-spec.md': '../../sec-filing-index-ingestion-spec.md',
        '../sec-filing-index-ingestion-adr.md': '../../sec-filing-index-ingestion-adr.md',
        '../sec-filing-index-ingestion-roadmap.md': '../../sec-filing-index-ingestion-roadmap.md',
        '../sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1': '../../sec-filing-index-ingestion-stage-1-findings.md#10-final-owner-acceptance--f1',
        '../completed/sec-filing-index-ingestion-stage-1-spec.md': '../../completed/sec-filing-index-ingestion-stage-1-spec.md',
        'completed/1-sec-filing-index-ingestion-stage-1-spec.md': '1-sec-filing-index-ingestion-stage-1-spec.md',
    }
    plan = re.sub(r'\]\(([^)]+)\)', lambda match: '](' + plan_links.get(match.group(1), match.group(1)) + ')', plan)
    (ROOT / NEW_PLAN).write_text(plan)
    spec = (ROOT / NEW_SPEC).read_text()
    def spec_link(match):
        target = match.group(1)
        if target == 'plans/2-sec-filing-index-ingestion-stage-2-spec.md':
            target = 'plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md'
        if target.startswith('completed/'):
            target = target.removeprefix('completed/')
        else:
            target = '../' + target
        return '](' + target + ')'
    spec = re.sub(r'\]\(([^)]+)\)', spec_link, spec)
    (ROOT / NEW_SPEC).write_text(spec)
    assert not list((ROOT / 'specs/plans').glob('*-sec-filing-index-ingestion-stage-2-spec.md'))
    assert len(re.findall(r'^- \[x\] \*\*Step ', plan, re.M)) == 33
    assert not re.findall(r'^- \[ \] \*\*Step ', plan, re.M)
    assert re.findall(r'```.*?```', plan_before.decode(), re.S) == re.findall(r'```.*?```', plan, re.S)
    save(EVIDENCE / 'document-markup.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'actual_steps_before': 33, 'actual_steps_completed': 33, 'unchecked_steps_remaining': 0,
        'deviation_notes': written_notes, 'all_approved_plan_code_examples_unchanged': True,
        'original_owner_approval_paragraphs_preserved_and_marked_historical': True,
        'no_other_active_plan_implements_spec_suffix': True, 'status': status,
        'old_plan': str(OLD_PLAN), 'retired_plan': record(ROOT / NEW_PLAN),
        'old_spec': str(OLD_SPEC), 'retired_spec': record(ROOT / NEW_SPEC),
        'active_authoritative_stamp_existed_before_roadmap_edit': stamp_record,
        'retirement_commit_subject': 'chore(specs): retire plan 2', 'all22_stage7_checks': 'reserved'})
    baseline = json.loads((SDD / 'preflight/baseline.json').read_text())
    changed = []
    for name, item in baseline['files'].items():
        path = PRIMARY / name
        if name == 'specs/sec-filing-index-ingestion-roadmap.md':
            assert item['sha256'] == ORIGINAL_ROADMAP_SHA
            assert sha(path.read_bytes()) == roadmap_receipts[0]['after_sha256']
        elif not path.is_file() or sha(path.read_bytes()) != item['sha256']:
            changed.append(name)
    assert not changed
    assert all(not (PRIMARY / name).exists() and not (ROOT / name).exists() for name in DELETIONS)
    primary_status = command(['git', 'status', '--porcelain=v1'], PRIMARY).decode()
    assert primary_status.splitlines() == expected_status + ['?? specs/sec-filing-index-ingestion-roadmap.md']
    assert command(['git', 'ls-files', '--', 'specs/sec-filing-index-ingestion-roadmap.md'], PRIMARY) == b''
    assert command(['git', 'ls-files', '--', 'specs/sec-filing-index-ingestion-roadmap.md']) == b''
    save(EVIDENCE / 'completion-primary-preservation.json', {'recorded_at': datetime.now(timezone.utc).isoformat(),
        'baseline_path': record(SDD / 'preflight/baseline.json'), 'protected_files_checked': len(baseline['files']),
        'permitted_exact_checkbox_path': 'specs/sec-filing-index-ingestion-roadmap.md',
        'all_other_protected_files_byte_identical': True, 'changed_protected_files_except_authorized_checkbox': changed,
        'original_four_deletions_absent_in_primary_and_worktree': DELETIONS, 'primary_status': primary_status,
        'roadmap_untracked_in_primary_and_ignored_untracked_in_worktree': True,
        'original_verify_primary_baseline_unchanged': True, 'no_primary_integration_performed': True})
    for item in source_files:
        path = ROOT / item['path']
        assert record(path) == item, path
    report = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-2/verification.md'
    report.write_bytes(report.read_bytes() + f'''\n## Administrative Stage 2 completion — {completion_date}

Fresh GPT-6.1 Max scoped review of `9098fe9b664d9f44a663fdd8357e34030c37e932..{REVIEWED}` resolved W-I1, W-I2 and W-M1 as ADDRESSED, with no new findings. The original whole-branch review and scoped closure compose Spec PASS and Quality PASS. Required `code-reviewer` routing used the recorded default-role fallback; a same-family Codex CLI second seat was SKIPPED. No required step, owner answer or finding remains unresolved and nothing was deferred. Existing local Python ran deferred backlog reporting: no backlog file exists, zero open/closed/aged items, closure rate n/a; no empty backlog was created.

The [retired plan 2](../../../plans/completed/2-sec-filing-index-ingestion-stage-2-spec.md) records all 33 completed steps and the actual interface, conservative Azure guard, fixture invocation and local runtime deviations. The [authoritative Stage 2 spec stamp](../../../completed/sec-filing-index-ingestion-stage-2-spec.md#5-completion-gates-and-rollout-reference) precedes the exact one-checkbox local roadmap change; Stage 3–8 remain unticked and all 22 Stage 7 integrated checks remain reserved. Parent/F1/Stage 1 evidence and original deletions are preserved.

The [completion receipt](verification/completion-checkpoint/completion-receipt.json) and [retention map](verification/completion-checkpoint/retention-map.json) bind the retired document bytes, current 302-test/check/install/combined/process proof, full/scoped review packages and complete SDD coverage against seven prior checkpoints. Documentation-only completion retains the post-implementation 302-test result (106.619 seconds, complete wrapper exit 0 in 106.99618458282202 seconds); no tests, installation, acquisition or live access were rerun. Runtime/build/test/existing helper bytes still equal the tested and reviewed revision. Integration and exact SDD/worktree cleanup remain controller-owned.
'''.encode())
    (EVIDENCE / 'administrative-document-markup.diff').write_bytes(command(['git', 'diff', '--no-ext-diff', '--binary', '--no-renames', REVIEWED, '--', str(OLD_PLAN), str(NEW_PLAN), str(OLD_SPEC), str(NEW_SPEC), str(report.relative_to(ROOT))]))
    save(CHECKPOINT / 'completion-receipt.json', {'schema_version': 'sec-stage2-completion-v1',
        'recorded_at_utc': now.isoformat(), 'completion_local': local.isoformat(), 'completion_date': completion_date,
        'completion_timezone': 'America/New_York', 'reviewed_head': REVIEWED, 'current_precommit_head': REVIEWED,
        'whole_branch_review_composition': {'spec': 'PASS', 'quality': 'PASS', 'resolved': ['W-I1','W-I2','W-M1'], 'new': []},
        'scoped_verdict': record(SDD / 'final-review-fix1-rereview.md'), 'composed_resolution': record(resolution_path),
        'status': status, 'retired_plan': record(ROOT / NEW_PLAN), 'retired_spec': record(ROOT / NEW_SPEC),
        'active_spec_stamp_preceded_roadmap_edit': True, 'stamp_before_roadmap': stamp_record,
        'actual_steps_completed': 33, 'current_prescribed_check': check,
        'source_equality_receipt_original': record(EVIDENCE / 'tested-reviewed-source-equality.json'),
        'primary_preservation_receipt_original': record(EVIDENCE / 'completion-primary-preservation.json'),
        'roadmap_exact_change_receipt_original': record(EVIDENCE / 'roadmap-exact-checkbox.json'),
        'deferred_stats_receipt_original': record(EVIDENCE / 'deferred-stats.json'),
        'fresh_installed_bundle': source_receipt['fresh_installed_bundle'], 'fresh_combined_bundle': source_receipt['fresh_combined_bundle'],
        'all22_stage7_checks': 'reserved', 'later_stages_3_through_8': 'unticked, definitions unchanged',
        'nothing_deferred': True, 'no_unanswered_owner_question': True, 'no_backlog_created': True,
        'planned_retirement_commit_subject': 'chore(specs): retire plan 2',
        'no_future_commit_sha_claim': True, 'no_runtime_build_test_existing_helper_change_or_rerun': True,
        'cleanup_integration_owner': 'controller; no SDD/worktree/branch removal, merge, push or PR performed'})
    print(json.dumps({'administrative_markup': 'applied', 'completion_date': completion_date,
        'steps_completed': 33, 'deviation_notes': len(written_notes), 'source_files_verified': len(source_files),
        'primary_protected_files_verified': len(baseline['files']), 'roadmap': roadmap_receipts[0],
        'checkpoint': str(CHECKPOINT), 'next': 'validate local links, stabilize own SDD receipts, retain new/changed bytes against seven maps'}, indent=2))

if __name__ == '__main__':
    main()
