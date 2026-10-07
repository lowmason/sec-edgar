"""Controller completion procedure; execute only after scoped acceptance review."""
from pathlib import Path
import os
import re
import shutil

root = Path.cwd()
w = root / '.sdd/3-sec-filing-index-ingestion-stage-3-spec'
stage = root / 'specs/evidence/sec-filing-index-ingestion/stage-3'
old_plan = root / 'specs/plans/3-sec-filing-index-ingestion-stage-3-spec.md'
new_plan = root / 'specs/plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md'
old_spec = root / 'specs/sec-filing-index-ingestion-stage-3-spec.md'
new_spec = root / 'specs/completed/sec-filing-index-ingestion-stage-3-spec.md'
assert old_plan.is_file() and old_spec.is_file()
assert not new_plan.exists() and not new_spec.exists()
assert not any(p != old_plan and p.name.endswith('sec-filing-index-ingestion-stage-3-spec.md') for p in (root/'specs/plans').glob('*.md'))
checkpoint = stage / 'completion-checkpoint'
checkpoint.mkdir(exist_ok=True)
originals = checkpoint / 'originals'
originals.mkdir(exist_ok=True)
for source, name in [
    (w/'completion-inputs/plan-before-completion.md', 'plan-before-completion.md'),
    (old_spec, 'spec-after-acceptance-before-completion.md'),
    (w/'completion-inputs/roadmap-before-completion.md', 'roadmap-before-completion.md'),
]:
    shutil.copyfile(source, originals/name)
shutil.copyfile(w/'completion-inputs/later-stage-revalidation.md', checkpoint/'later-stage-revalidation.md')
shutil.copytree(w/'deferred-stats', checkpoint/'deferred-stats', dirs_exist_ok=True)

status = '**Status: COMPLETE (2026-10-07)** — executed via subagent-driven-development; nothing deferred'
plan = old_plan.read_text()
plan = re.sub(r'^\*\*Status:\*\*.*$', status, plan, count=1, flags=re.M)
assert len(re.findall(r'^- \[ \]', plan, re.M)) == 34
plan = re.sub(r'^- \[ \]', '- [x]', plan, flags=re.M)
plan = plan.replace('Live-access authorizations remain closed and Stage 3 remains unticked.', 'Live-access authorizations remain closed. The unticked status at initial approval is historical; the completed rollout stamp supplies current evidence.')
plan = plan.replace('## Approval and execution handoff', '## Historical approval and execution handoff')
plan = plan.replace('The planning session stops after recording it; no code has been implemented and all live-access authorizations remain closed.', 'This preserves the planning-time handoff: the planning session stopped after recording approval with no implementation. All live-access authorizations remain closed at completion.')
plan = plan.replace('Preflight + immutable planning receipt; no roadmap edit', 'Preflight + immutable planning receipt; primary unchanged, isolated completion roadmap update')
plan = plan.replace('Status + preflight + handoff below', 'Status + preflight + historical handoff + completed rollout stamp')
notes = {
    ('Task 3', 'Step 2'): 'The existing Task 1 accept_transform create/adopt contract already met this step; etl/state.py needed no redundant edit. Parquet compliant nested lists are disabled to preserve the explicit original_fields item schema.',
    ('Task 4', 'Step 3'): 'Every noninitial candidate retains exact base GenerationCapture in immutable candidate-prefix retained-base.json, even when retained_from_generation is None, so complete deltas/gates are validated against their actual base.',
    ('Task 5', 'Step 2'): 'publication_conflict may retain the last uncommitted manifest_ref; generation_id and clear candidate_ref remain None. PublicationRepairError retains truthful committed outcomes if ordinary ancillary repair fails after CAS.',
    ('Task 6', 'Step 3'): 'Affected quarters are derived from validated authoritative manifests rather than repairable receipts. Ordinary post-CAS repair failures preserve retryable Attempt progress and exit 9 without a frozen terminal result; independent quarters still run. The result writer adds keyword-only observer and serializes canonical_json(to_mapping()) instead of the illustrative nonexistent to_json().',
    ('Task 7', 'Step 2'): 'All 970,622 retained rows were scanned; exact SEC-0141/0142/0143 sources have 21/24/6 conflicts and remain wholly quarantined. Owner-authorized hash-bound acceptance permits these documented refusal outcomes; original specimens exit 1 remains unchanged.',
    ('Task 7', 'Step 3'): 'The current check passes 452 tests/build/help/version/compile on native macOS ARM64/Python 3.14.0; documentary checks use cached 3.14.7. All 22 integrated checks remain reserved. Preserved historical diff whitespace exit 2 is disclosed separately from scoped exit 0.',
}
lines = plan.splitlines(keepends=True)
task = None
insertions = []
for i, line in enumerate(lines):
    match = re.match(r'### (Task \d+):', line)
    if match:
        task = match.group(1)
    step = re.match(r'- \[x\] \*\*(Step \d+):', line)
    if step and (task, step.group(1)) in notes:
        j = i + 1
        while j < len(lines) and not re.match(r'^- \[x\]|^### |^## ', lines[j]):
            j += 1
        insertions.append((j, '\n> Deviation: ' + notes[(task, step.group(1))] + '\n\n'))
assert len(insertions) == 6
for index, note in reversed(insertions):
    lines.insert(index, note)
plan = ''.join(lines)
plan += """
## Completed rollout stamp

> Stage 3: COMPLETE (2026-10-07) — executed via subagent-driven-development; nothing deferred.

The reviewed implementation revision is 2343f39f0e21adc2ad401a9346a8c9ffa0509040. [Current verification](../evidence/sec-filing-index-ingestion/stage-3/verification.md) retains 452 successful tests, full build/CLI checks, real process races/deaths/recovery and the exact installed-wheel proof. The [owner amendment](../evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/owner-amendment.json) accepts documented quarantines for exact SEC-0141/0142/0143 bytes while retaining strict whole-source refusal. It supersedes only the former delivery-acceptance blocker. The [completion receipt](../evidence/sec-filing-index-ingestion/stage-3/completion-checkpoint/completion-receipt.json) binds amendment/reviews, preservation and retirement. No skipped step, unfixed finding, unanswered owner decision or deferred item remains.

Only this Stage 3 plan/spec are retired. The isolated roadmap copy receives its Stage 3 checkbox after the authoritative stamp; protected primary remains unchanged. Stages 4–8 remain unticked and independently revalidated. All 22 Stage 7 checks remain reserved. Stage 4 requires a separate owner-initiated roadmap resume; all live-access authorizations remain closed.
"""
spec = old_spec.read_text()
spec = re.sub(r'^\*\*Status:\*\*.*$', status, spec, count=1, flags=re.M)
spec = spec.replace('**Owner approval record:**', '> Historical approval record: this paragraph retains initial authorization and its planning-time status; the completed rollout stamp supplies current evidence.\n\n**Owner approval record:**', 1)
spec = spec.replace('Plan 3 implements the following matrix; no assertion here means those new tests have already run:', 'The planning matrix below defines the verification obligations; the completed stamp and retained evidence record their actual execution:')
start = spec.index('Stage 3 remains **unticked**.', spec.index('## 9. Rollout note'))
spec = spec[:start] + """
> Stage 3: COMPLETE (2026-10-07) — implemented by [completed Plan 3](plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md).
> Evidence: [current verification](evidence/sec-filing-index-ingestion/stage-3/verification.md), reviewed implementation revision 2343f39f0e21adc2ad401a9346a8c9ffa0509040 and [completion receipt](evidence/sec-filing-index-ingestion/stage-3/completion-checkpoint/completion-receipt.json).

Seven tasks and their task/whole-branch reviews are resolved. The current native full check passes 452 tests in 163.537 seconds and wheel/sdist/help/version/compile checks. Raw-only sequence, actual process races/forced exits, post-CAS repair and isolated installed-wheel proof pass. The reviewed 111,195-byte wheel SHA-256 is eb8bb3b318b3b1a4fe1983291efb92161e22fac998f86230b5f2b7f3cf15c3ab.

On 2026-10-07 Lowell Mason explicitly amended Stage 3 acceptance to allow documented quarantines while retaining strict refusal. This applies only to exact SEC-0141/0142/0143 bytes bound in the [owner receipt](evidence/sec-filing-index-ingestion/stage-3/acceptance-amendment/owner-amendment.json). Their 21/24/6 conflicts and specimen exit 1 remain historical evidence. They yield no accepted observation output or publication. No successful historical range or deployed capacity is inferred. Every other invalid source or missing cached dependency remains subject to the strict gates.

The [whole-branch review and resolved repair](evidence/sec-filing-index-ingestion/stage-3/review-checkpoint/final-re-review-1.md) records implementation findings ADDRESSED; its then-blocked acceptance disposition is superseded only by the owner amendment and scoped acceptance review retained in the completion checkpoint. The separate Codex CLI second opinion is SKIPPED under the Codex-controller rule; none is claimed. No skipped/descoped step, unfixed finding, unanswered decision or deferred item remains. The required backlog reporter found no deferred-items file; no empty backlog was created.

Primary preservation rechecks all 19,088 records / 294,399,711 existing bytes, original roadmap and four legacy-path absences without mutating the primary checkout. Only this Stage 3 plan/spec are retired. The authoritative stamp precedes the isolated roadmap's Stage 3 checkbox update. Parent design, ADR, F1 and roadmap remain active.

Later-stage revalidation: Stage 4 consumes shipped contracts but requires historical/daily workflow composition and R1/R2 proof. Stage 5 consumes candidates/gates but requires reconciliation, approval mutation, stale replay/reintroduction and R5/R7/R10 proof. Stage 6 requires the full worker image, Azure definitions, ADF start/poll/result handling, disabled triggers and telemetry. Stage 7 retains all 22 integrated checks reserved/not_run, including actual identities/HNS/ETags/network and worker memory/runtime/scratch. Stage 8 requires production coverage, controlled schedule enablement and observed durable scheduled reports. Native offline proofs discharge none of those checks. The [independent consistency receipt](evidence/sec-filing-index-ingestion/stage-3/completion-checkpoint/later-stage-revalidation.md) records the boundary.

Stage 4 requires a separate owner-initiated roadmap resume. SEC, Azure, authentication, compute, provisioning, deployment, image build and fetch authorizations remain closed.
""".lstrip()
mapping = {old_plan.resolve(): new_plan.resolve(), old_spec.resolve(): new_spec.resolve()}
def relocate(text, old, new):
    def link(match):
        dest = match.group(1)
        if dest.startswith(('#', 'http:', 'https:', 'app:', 'codex:', '/')):
            return match.group(0)
        path, separator, fragment = dest.partition('#')
        target = (old.parent/path).resolve()
        target = mapping.get(target, target)
        replacement = os.path.relpath(target, new.parent).replace(os.sep, '/')
        return '](' + replacement + (separator+fragment if separator else '') + ')'
    return re.sub(r'\]\(([^)]+)\)', link, text)
old_plan.write_text(relocate(plan, old_plan, new_plan))
old_spec.write_text(relocate(spec, old_spec, new_spec))

roadmap = (w/'completion-inputs/roadmap-before-completion.md').read_text()
assert roadmap.count('- [ ] Stage 3: Replayable ETL and safe publication') == 1
roadmap = roadmap.replace('- [ ] Stage 3: Replayable ETL and safe publication', '- [x] Stage 3: Replayable ETL and safe publication')
roadmap += """
## Stage 3 completion and later-stage consistency

Stage 3 completed 2026-10-07 through [completed Plan 3](plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md) and its [authoritative stamp](completed/sec-filing-index-ingestion-stage-3-spec.md#9-rollout-note). [Verification](evidence/sec-filing-index-ingestion/stage-3/verification.md) and [completion receipt](evidence/sec-filing-index-ingestion/stage-3/completion-checkpoint/completion-receipt.json) bind reviewed implementation and the owner-approved strict quarantine acceptance amendment. This copy preserves original derivation/earlier consistency notes; current stamps govern stage status. The primary roadmap remains protected byte-for-byte.

Stage 3 supplies offline transformation, canonical generations, changes, conditional publication, pointer readers and repair consumed by Stages 4–5. Exact SEC-0141/0142/0143 sources remain quarantined for 21/24/6 conflicts; original specimens exit 1 remains refusal evidence. No successful global historical range or deployed capacity is established.

Stages 4–8 remain unticked with scope unchanged. Stage 4 requires workflow composition and coverage/outage/overlap proof. Stage 5 requires reconciliation/approval and stale-replay/reintroduction history. Stage 6 requires the worker image, Azure definitions, ADF start/poll/result handling, disabled triggers and telemetry. All 22 Stage 7 integrated checks remain reserved/not_run. Stage 8 requires accepted production coverage and observed schedules. [Revalidation](evidence/sec-filing-index-ingestion/stage-3/completion-checkpoint/later-stage-revalidation.md) records outstanding boundaries. Later-stage planning, live access, image builds/deployment and schedules remain closed. Stage 4 requires a separate owner-initiated roadmap resume.
"""
(root/'specs/sec-filing-index-ingestion-roadmap.md').write_text(roadmap)
shutil.copyfile(root/'specs/sec-filing-index-ingestion-roadmap.md', checkpoint/'roadmap-after-completion.md')
print('Marked 34 steps and 6 deviations; prepared retirement links and isolated roadmap update.')
