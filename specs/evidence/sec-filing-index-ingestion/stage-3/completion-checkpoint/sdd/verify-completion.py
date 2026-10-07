"""Guarded controller audit of the completed documents and preserved evidence."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT/'packages/sec-edgar-ingest/tests'))
from network_guard import install
install()
import hashlib
import json
import platform
import re
import subprocess
import time

STAGE = ROOT/'specs/evidence/sec-filing-index-ingestion/stage-3'
CHECKPOINT = STAGE/'completion-checkpoint'
PRIMARY = Path('/Users/lowell/Projects/sec-edgar')
REVIEWED = '2343f39f0e21adc2ad401a9346a8c9ffa0509040'
started = time.monotonic()
failures = []
def check(condition, explanation):
    if not condition:
        failures.append(explanation)
def identity(path):
    data = path.read_bytes()
    return {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
def git(where, *args):
    result = subprocess.run(['git', *args], cwd=where, capture_output=True, text=True, check=True)
    return result.stdout.rstrip('\n')
def manifest(root, name, relocation=None):
    records = json.loads((root/name).read_bytes())
    for relative, expected in records.items():
        path = root/(relocation or {}).get(relative, relative)
        check(not Path(relative).is_absolute() and '..' not in Path(relative).parts, 'unsafe manifest path: '+relative)
        check(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'missing/unsafe payload: '+str(path))
        if path.is_file():
            check(identity(path)==expected, 'hash mismatch: '+str(path))
    return {'records':len(records),'payload_bytes':sum(p['bytes'] for p in records.values()),'inventory':identity(root/name)}

preflight = json.loads((STAGE/'verification/sdd-history/preservation-preflight/receipt.json').read_bytes())
inventory_path = STAGE/'verification/sdd-history/preservation-preflight/primary-inventory.json'
check(identity(inventory_path)==preflight['inventory'], 'primary inventory drift')
protected = json.loads(inventory_path.read_bytes())
checked_bytes = 0
for record in protected:
    p = PRIMARY/record['path']
    if record.get('absent'):
        check(not p.exists() and not p.is_symlink(), 'primary absence drift: '+record['path'])
    else:
        check(p.is_file(), 'primary missing: '+record['path'])
        if p.is_file():
            check(identity(p)=={'bytes':record['bytes'],'sha256':record['sha256']}, 'primary bytes drift: '+record['path'])
            checked_bytes += record['bytes']
check(git(PRIMARY,'status','--short','--branch')==preflight['status'], 'primary status drift')
check(git(PRIMARY,'rev-parse','HEAD')==preflight['head'], 'primary HEAD drift')

source_domains = ['packages/sec-edgar-ingest','conf','tests','fixtures','scripts','README.md','pyproject.toml','uv.lock','.python-version']
source_check = subprocess.run(['git','diff','--quiet',REVIEWED,'--',*source_domains],cwd=ROOT,capture_output=True)
check(source_check.returncode==0, 'reviewed implementation changed')
old_delivery = manifest(STAGE,'delivery-sha256.json',{'verification.md':'acceptance-amendment/originals/verification.md'})
frozen = {name: manifest(STAGE/name,'sha256.json') for name in ['verification','final-review-fix1','review-checkpoint','acceptance-amendment']}
amendment_command = json.loads((STAGE/'acceptance-amendment/command.json').read_bytes())
amendment_report = json.loads((STAGE/'acceptance-amendment/report.json').read_bytes())
check(amendment_command['exit']==0 and amendment_report['exit']==0, 'acceptance verification failed')
for name, expected in amendment_command['files'].items():
    check(identity(STAGE/'acceptance-amendment'/name)==expected, 'acceptance command binding: '+name)
check((STAGE/'acceptance-amendment/stdout.txt').read_bytes()==(STAGE/'acceptance-amendment/report.json').read_bytes(), 'acceptance stdout differs')
check((STAGE/'acceptance-amendment/stderr.txt').read_bytes()==b'', 'acceptance stderr nonempty')
check(amendment_report['original_specimen_exit']==1 and amendment_report['conflicts']==51, 'historical refusal altered')
check(all(r['processing_absent'] and r['observation_ref_absent'] and r['published_pointer_absent'] for r in amendment_report['sources']), 'quarantined source became accepted')
check(amendment_report['all22_stage7_checks']=='reserved' and amendment_report['live_access']=='closed', 'authority boundary drift')
# Pre-retirement proof's old spec path resolves to the exact preserved pre-retirement copy.
for relative, expected in amendment_report['input_hashes'].items():
    path = ROOT/relative
    if relative=='specs/sec-filing-index-ingestion-stage-3-spec.md':
        path = CHECKPOINT/'originals/spec-after-acceptance-before-completion.md'
    check(path.is_file() and identity(path)==expected, 'pre-retirement input binding drift: '+relative)

plan = ROOT/'specs/plans/completed/3-sec-filing-index-ingestion-stage-3-spec.md'
spec = ROOT/'specs/completed/sec-filing-index-ingestion-stage-3-spec.md'
roadmap = ROOT/'specs/sec-filing-index-ingestion-roadmap.md'
plan_text = plan.read_text()
spec_text = spec.read_text()
check(len(re.findall(r'^- \[x\]',plan_text,re.M))==34, 'completed step count')
check(not re.findall(r'^- \[ \]',plan_text,re.M), 'unchecked plan steps')
check(len(re.findall(r'^> Deviation:',plan_text,re.M))==6, 'deviation count')
status = '**Status: COMPLETE (2026-10-07)** — executed via subagent-driven-development; nothing deferred'
check(status in plan_text and status in spec_text, 'completion status missing')
check(not (ROOT/'specs/plans/3-sec-filing-index-ingestion-stage-3-spec.md').exists(), 'old plan not retired')
check(not (ROOT/'specs/sec-filing-index-ingestion-stage-3-spec.md').exists(), 'old spec not retired')
old_roadmap = (CHECKPOINT/'originals/roadmap-before-completion.md').read_bytes()
prefix = roadmap.read_bytes().split(b'\n## Stage 3 completion and later-stage consistency\n')[0]
check(prefix==old_roadmap.replace(b'- [ ] Stage 3: Replayable ETL and safe publication',b'- [x] Stage 3: Replayable ETL and safe publication'), 'roadmap baseline altered')
check(all(f'- [ ] Stage {n}:' in roadmap.read_text() for n in range(4,9)), 'later stage checkbox altered')
check(identity(roadmap)==identity(CHECKPOINT/'roadmap-after-completion.md'), 'isolated roadmap archival copy differs')
check(not (ROOT/'specs/deferred_items.md').exists(), 'unexpected deferred backlog')
backlog = json.loads((CHECKPOINT/'deferred-stats/command.json').read_bytes())
check(backlog['exit']==0 and not backlog['backlog_exists'] and not backlog['stderr'], 'backlog proof failed')

checked_links = 0
for p in [plan,spec,roadmap,ROOT/'docs/runbooks/sec-edgar-etl-publication.md',STAGE/'verification.md',STAGE/'acceptance-amendment/README.md']:
    for destination in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)',p.read_text()):
        destination = destination.strip('<>')
        if destination.startswith(('#','http:','https:','app:','codex:')):
            continue
        target = (p.parent/destination.partition('#')[0]).resolve()
        checked_links += 1
        check(target.exists(), 'broken link: '+str(p.relative_to(ROOT))+' -> '+destination)
full_check = json.loads((STAGE/'final-review-fix1/full-check/command.json').read_bytes())
test_log = (STAGE/'final-review-fix1/full-check/stderr.txt').read_text()
ok_tests = re.findall(r'^test_.* \.\.\. ok$',test_log,re.M)
check(full_check['exit']==0 and len(ok_tests)==452 and re.search(r'Ran 452 tests in 163\.537s\n\nOK',test_log), 'current full check evidence mismatch')
result = {
 'schema':'stage-3-completion-controller-audit-v1','exit':1 if failures else 0,'failures':failures,
 'network_guard':True,'live_access_authorizations':'closed','all22_stage7_checks':'reserved',
 'python':sys.version,'platform':platform.platform(),'runtime_seconds':time.monotonic()-started,
 'head':git(ROOT,'rev-parse','HEAD'),'reviewed_implementation':REVIEWED,
 'implementation_unchanged':source_check.returncode==0,'historical_full_tests':len(ok_tests),'historical_full_check_exit':full_check['exit'],
 'fresh_acceptance_exit':amendment_report['exit'],'historical_specimen_exit':amendment_report['original_specimen_exit'],
 'primary_records':len(protected),'primary_existing_bytes':checked_bytes,'primary_status_and_head_unchanged':git(PRIMARY,'status','--short','--branch')==preflight['status'] and git(PRIMARY,'rev-parse','HEAD')==preflight['head'],
 'primary_roadmap':identity(PRIMARY/'specs/sec-filing-index-ingestion-roadmap.md'),
 'protected_absences':list(preflight['protected_absences']),
 'old_delivery_snapshot':old_delivery,'frozen_manifests':frozen,
 'plan':identity(plan),'spec':identity(spec),'roadmap':identity(roadmap),
 'completed_steps':34,'deviations':6,'local_links_checked':checked_links,
 'deferred_backlog':{'file_exists':False,'open':0,'aged_over_45_days':0,'closure_rate':None,'stdout':backlog['stdout']},
}
target = CHECKPOINT/'controller-verification.json'
assert not target.exists(), 'Refuse overwriting controller audit'
target.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
raise SystemExit(result['exit'])
