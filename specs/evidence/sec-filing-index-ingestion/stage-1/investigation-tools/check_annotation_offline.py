"""Synthetic daily-schema annotation regression; no live source claim."""
import csv
import json
import pathlib
import tempfile
import sys

source = pathlib.Path(__file__).with_name('summarize_source_evidence.py').read_text().split('quarterly = list(csv.DictReader')[0]
if '--reproduce-old' in sys.argv:
    start = source.index("    if name == 'daily.csv':")
    end = source.index("    temporary =", start)
    source = source[:start] + "    for row in rows:\n        report = by_url.get(row['discovered_url'])\n        if report:\n            row['source_status'] = 'retained_inspected_specimen'\n            row['selection_reason'] = report['evidence_id']\n" + source[end:]
with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
    base = pathlib.Path(directory)
    (base/'specimens').mkdir()
    report = {'url':'https://example.invalid/daily.idx','evidence_id':'SYNTHETIC','original_path':'specimens/hash.idx'}
    (base/'specimens/SEC-SYNTHETIC.inspection.json').write_text(json.dumps(report))
    (base/'quarterly.csv').write_text('discovered_url,source_status,selection_reason\nhttps://example.invalid/quarter.zip,listed_source_pending,original\n')
    daily = base/'daily.csv'
    daily.write_text('discovered_url,outcome,handoff_relation\nhttps://example.invalid/daily.idx,listed_source_pending,handoff\nhttps://example.invalid/tail.idx,listed_source_pending,after_handoff\n')
    source = source.replace('BASE = pathlib.Path(__file__).resolve().parents[1]', 'BASE = pathlib.Path('+repr(str(base))+')')
    exec(compile(source,'synthetic-annotation-helper','exec'), {'__file__':__file__})
    rows = list(csv.DictReader(daily.open()))
    assert len(rows)==2
    assert rows[0]['outcome']=='retained_inspected_specimen'
    assert rows[0]['inspection_evidence_id']=='SYNTHETIC'
    assert rows[0]['handoff_relation']=='handoff'
    assert rows[1]['outcome']=='listed_source_pending'
print('PASS: synthetic distinct daily schema, evidence annotations, preserved handoff and tail row; isolated CSV writes')
