"""Freeze the correction generation; this is not the controller's acceptance candidate."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
BASE=ROOT/'specs/evidence/sec-filing-index-ingestion/stage-1'
TASK=BASE/'final-fix'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
versions=[]
for source in (BASE/'index.csv',BASE/'readiness-checklist.md',BASE/'stage-7-checks.md',ROOT/'specs/sec-filing-index-ingestion-stage-1-findings.md'):
    target=TASK/'generation'/ (source.name+'.'+digest(source))
    target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists()
    target.write_bytes(source.read_bytes())
    versions.append({'source_path':str(source.relative_to(ROOT)),'immutable_path':str(target.relative_to(ROOT)),
                     'bytes':source.stat().st_size,'sha256':digest(source)})
(TASK/'generation-versions.json').write_text(json.dumps({'generation':'Final-review correction capture; scoped re-review pending','records':versions},indent=2)+'\n')
exclude_names={'correction-evidence-manifest.json','correction-freeze.json','controller-boundary.json','correction-report.md'}
records=[]
for path in sorted(BASE.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':continue
    if path.parent==TASK and path.name in exclude_names:continue
    if path.parent==TASK/'checks' and path.name.startswith('capture-'):continue
    records.append({'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path)})
finding=ROOT/'specs/sec-filing-index-ingestion-stage-1-findings.md'
records.append({'path':str(finding.relative_to(ROOT)),'bytes':finding.stat().st_size,'sha256':digest(finding)})
manifest=TASK/'correction-evidence-manifest.json'
manifest.write_text(json.dumps({'captured_at_utc':datetime.now(timezone.utc).isoformat(),'generation':'Final-review correction candidate before scoped re-review',
 'owner_acceptance':'pending','scope':'Fresh exact retained-byte inventory; not owner acceptance or controller final freeze.',
 'exclusions':['This manifest itself; correction-freeze.json carries its hash afterward (no circular hashes).',
 'controller-boundary.json is a mutable controller process supplement; its initial pending bytes can later record completed re-review/final hashes.',
 'capture-* command/output receipts and correction-report.md are post-capture supplements.',
 'Later scoped/final review, acceptance and completion receipts are outside this immutable generation; no PASS or acceptance is predicted.',
 'Transient __pycache__/.pyc files.'],
 'explicit_excluded_paths':[str((TASK/name).relative_to(ROOT)) for name in sorted(exclude_names)],'records':records},indent=2)+'\n')
frozen_finding=next(r for r in versions if r['source_path']==str(finding.relative_to(ROOT)))
freeze={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'generation':'Correction review candidate; final acceptance freeze owned by controller',
 'finding_path':str(finding.relative_to(ROOT)),'finding_sha256':digest(finding),'immutable_finding_path':frozen_finding['immutable_path'],
 'evidence_manifest_path':str(manifest.relative_to(ROOT)),'evidence_manifest_sha256':digest(manifest),
 'manifest_files':len(records),'scoped_re_review':'pending','owner_acceptance':'pending','controller_boundary_path':str((TASK/'controller-boundary.json').relative_to(ROOT))}
(TASK/'correction-freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps(freeze,indent=2))
