"""Verify every local artifact reference in the evidence index independently."""
import csv
import hashlib
import json
import pathlib
BASE = pathlib.Path(__file__).resolve().parents[1]
ROOT = BASE.parents[3]
rows = list(csv.DictReader((BASE/'index.csv').open()))
assert len({row['evidence_id'] for row in rows}) == len(rows)
results = []
for row in rows:
    for reference in row['url_or_artifact'].split(';'):
        reference = reference.strip()
        if reference.startswith(('https://', 'http://')):
            continue
        assert reference, row['evidence_id']
        path = pathlib.Path(reference)
        path = path if path.is_absolute() else ROOT/path
        assert path.is_file(), (row['evidence_id'], str(path), 'missing local artifact')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == row['sha256'], (row['evidence_id'], reference, row['sha256'], actual)
        results.append({'evidence_id':row['evidence_id'], 'local_reference':reference, 'sha256':actual})
print(json.dumps({'result':'PASS', 'index_rows':len(rows),'local_reference_hashes_verified':len(results),'method':'Each semicolon-delimited local artifact read and independently SHA-256 hashed; remote URLs skipped','references':results},indent=2))
