"""Retain the exact correction inputs before any live document changes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / 'specs/evidence/sec-filing-index-ingestion/stage-1'
OUTPUT = BASE / 'final-fix'
WORK = ROOT / '.sdd/1-sec-filing-index-ingestion-stage-1-spec'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

records = []
paths = [BASE / 'index.csv', BASE / 'readiness-checklist.md', BASE / 'stage-7-checks.md',
         ROOT / 'specs/sec-filing-index-ingestion-stage-1-findings.md',
         WORK / 'final-whole-branch-review.md', WORK / 'task-6-report.md',
         WORK / 'final-fix-before-manifest.json']
for source in paths:
    target = OUTPUT / 'before' / (source.name + '.' + digest(source))
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    target.write_bytes(source.read_bytes())
    records.append({'source_path':str(source.relative_to(ROOT)), 'immutable_path':str(target.relative_to(ROOT)),
                    'bytes':source.stat().st_size, 'sha256':digest(source)})
(OUTPUT / 'historical-path-map.json').write_text(json.dumps({
    'captured_at_utc':datetime.now(timezone.utc).isoformat(),
    'semantics':'Exact old path plus SHA256 resolves to these immutable bytes; historical rows/hashes/results remain unchanged.',
    'records':records}, indent=2)+'\n')
print(json.dumps({'frozen_inputs':len(records), 'mutable_index_has_no_live_stage7_reference':
    not any(r.get('url_or_artifact','').split(';')[-1].strip()==str((BASE/'stage-7-checks.md').relative_to(ROOT))
            for r in __import__('csv').DictReader((BASE/'index.csv').open()))},indent=2))
