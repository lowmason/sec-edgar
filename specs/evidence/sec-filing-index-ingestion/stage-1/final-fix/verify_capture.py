"""Verify the independent frozen correction capture without altering any manifest."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
TASK=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest_path=TASK/'correction-evidence-manifest.json';manifest=json.loads(manifest_path.read_text())
freeze=json.loads((TASK/'correction-freeze.json').read_text())
assert digest(manifest_path)==freeze['evidence_manifest_sha256']
assert len(manifest['records'])==freeze['manifest_files']
assert len({r['path'] for r in manifest['records']})==len(manifest['records'])
for r in manifest['records']:
    path=ROOT/r['path'];assert path.is_file() and path.stat().st_size==r['bytes'] and digest(path)==r['sha256'],r
for r in json.loads((TASK/'generation-versions.json').read_text())['records']:
    live=ROOT/r['source_path'];immutable=ROOT/r['immutable_path']
    assert live.read_bytes()==immutable.read_bytes() and digest(immutable)==r['sha256'],r
assert freeze['finding_sha256']==digest(ROOT/freeze['immutable_finding_path'])
assert not {r['path'] for r in manifest['records']} & set(manifest['explicit_excluded_paths'])
assert freeze['scoped_re_review']=='pending' and freeze['owner_acceptance']=='pending'
print(json.dumps({'result':'PASS','files_verified':len(manifest['records']),'finding_sha256':freeze['finding_sha256'],
                 'evidence_manifest_sha256':freeze['evidence_manifest_sha256'],'owner_acceptance':'pending',
                 'scope':'Correction immutable generation only; no later review/acceptance outcome inferred.'},indent=2))
