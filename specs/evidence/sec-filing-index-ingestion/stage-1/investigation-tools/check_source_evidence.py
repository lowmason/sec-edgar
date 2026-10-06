"""Independent offline verification of retained specimen observations."""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile
BASE = pathlib.Path(__file__).resolve().parents[1]
reports = [json.loads(path.read_text()) for path in sorted((BASE/'specimens').glob('SEC-*.inspection.json'))]
expected_count = int(sys.argv[1])
assert len(reports) == expected_count, len(reports)
paths = {}
for report in reports:
    original = BASE/report['original_path']
    data = original.read_bytes()
    metadata = json.loads((BASE/report['receipt_artifact']).read_text())
    assert data == (BASE/metadata['body_artifact']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == report['original_sha256'] == metadata['sha256']
    assert len(data) == metadata['received_bytes'] == report['original_bytes']
    paths[original] = report['original_sha256']
    if report['derivative_path']:
        derivative = BASE/report['derivative_path']
        decoded = derivative.read_bytes()
        with zipfile.ZipFile(original) as archive:
            assert archive.namelist() == ['master.idx']
            assert archive.testzip() is None
            assert archive.read('master.idx') == decoded
        assert hashlib.sha256(decoded).hexdigest() == report['derivative_sha256']
        paths[derivative] = report['derivative_sha256']
    else:
        decoded = data
    assert len(decoded) == report['expanded_bytes']
    observations = report['observations']
    text = decoded.decode(observations['strict_encoding'], errors='strict')
    rows = [line for line in text.splitlines()[text.splitlines().index(observations['column_header'])+1:] if line and not set(line)<={'-'}]
    assert len(rows) == observations['row_count']
    assert all(len(row.split('|')) == 5 for row in rows)
    assert min(row.split('|')[3] for row in rows) == observations['minimum_filing_date']
    assert max(row.split('|')[3] for row in rows) == observations['maximum_filing_date']
for name in ('quarterly.csv','daily.csv'):
    rows = list(csv.DictReader((BASE/name).open()))
    for report in reports:
        matches = [row for row in rows if row['discovered_url']==report['url']]
        if matches:
            assert len(matches)==1
            assert matches[0]['source_status' if name == 'quarterly.csv' else 'outcome']=='retained_inspected_specimen'
            assert report['evidence_id'] in matches[0]['selection_reason' if name == 'quarterly.csv' else 'inspection_evidence_id']
result = subprocess.run(['shasum','-a','256',*map(str,paths)],capture_output=True,text=True,check=True)
for line in result.stdout.splitlines():
    checksum, name = line.split('  ',1)
    assert paths[pathlib.Path(name)] == checksum
by_url = {report['url']:report for report in reports}
root=by_url['https://www.sec.gov/Archives/edgar/full-index/master.zip']
quarter=by_url['https://www.sec.gov/Archives/edgar/full-index/2026/QTR4/master.zip']
assert (BASE/root['original_path']).read_bytes() == (BASE/quarter['original_path']).read_bytes()
assert (BASE/root['derivative_path']).read_bytes() == (BASE/quarter['derivative_path']).read_bytes()
print(result.stdout)
print(f'PASS: {len(reports)} receipts; {len(paths)} unique original/derivative files; receipt originals, hashes, CRC, full rows/date bounds, selected matrix annotations and root/QTR byte equality')
