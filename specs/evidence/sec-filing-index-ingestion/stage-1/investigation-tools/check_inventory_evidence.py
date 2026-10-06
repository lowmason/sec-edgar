"""Read retained evidence only; no network and no production format claims."""
import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib

base = pathlib.Path(__file__).resolve().parents[1]

def csv_rows(name):
    with (base / name).open(newline='') as handle:
        return list(csv.DictReader(handle))

quarterly = csv_rows('quarterly.csv')
daily = csv_rows('daily.csv')
requests = csv_rows('requests.csv')
expected = {f'{year}Q{quarter}' for year in range(2010, 2027) for quarter in range(1, 5)}
summaries = [row for row in quarterly if row['representation'] == 'quarter_summary']
assert len(summaries) == 68
assert {row['quarter'] for row in summaries} == expected
assert len({row['quarter'] for row in summaries}) == len(summaries)
assert sum(row['development_subset'] == 'true' for row in summaries) == 48
for row in summaries:
    assert (row['development_subset'] == 'true') == (row['quarter'] >= '2015Q1')
    assert row['listing_evidence_id'], row
    assert row['source_status'] in ('available', 'valid_no_source', 'discovery_failed', 'listed_source_pending')
metadata = {row['attempt_id']: json.loads((base / row['response_headers_artifact']).read_text()) for row in requests}
for row in quarterly + daily:
    identifier = row['listing_evidence_id']
    if identifier:
        assert identifier in metadata, row
    if row.get('source_status', row.get('outcome')) != 'listed_source_pending' or row.get('representation') == 'required_handoff_summary':
        continue
    retained = metadata[identifier]
    assert retained['outcome'] == 'success'
    child_name = row['discovered_url'].rsplit('/', 1)[-1]
    assert any(child['name'] == child_name and child['type'] == 'file' for child in retained['discovered_children']), row
for row in requests:
    retained = metadata[row['attempt_id']]
    body = base / 'listings' / (row['attempt_id'] + '.body')
    digest, count = hashlib.sha256(), 0
    if body.exists():
        with body.open('rb') as handle:
            for chunk in iter(lambda: handle.read(65536), b''):
                digest.update(chunk)
                count += len(chunk)
    assert count == int(row['received_bytes'])
    assert digest.hexdigest() == row['body_sha256']
    assert retained['received_bytes'] == count
    intent = base / retained['intent_artifact']
    assert intent.exists()
assert len({row['attempt_id'] for row in requests}) == len(requests)
state = json.loads((base / 'sec-window-state.json').read_text())
assert state['attempts'] == len(requests)
assert state['received_bytes'] == sum(int(row['received_bytes']) for row in requests)
for previous, current in zip(requests, requests[1:]):
    assert (dt.datetime.fromisoformat(current['start_utc']) - dt.datetime.fromisoformat(previous['start_utc'])).total_seconds() >= 0.34
handoff = [row for row in daily if row['representation'] == 'required_handoff_summary']
assert len(handoff) == 1 and handoff[0]['listed_date'] == '20261001'
assert {row['directory_period'] for row in daily if row['representation'] == 'directory_summary' and row['directory_period'] != 'root'} == expected
result = {'method': 'Offline retained-evidence cross-check; no SEC requests', 'pinned_end_quarter': '2026Q4',
          'requested_quarter_summaries': len(summaries), 'development_quarter_summaries': 48,
          'quarterly_summary_outcomes': dict(collections.Counter(row['source_status'] for row in summaries)),
          'quarterly_representation_rows': len(quarterly) - len(summaries), 'daily_rows': len(daily),
          'daily_boundary_outcomes': dict(collections.Counter(row['outcome'] for row in daily if row['representation'] == 'directory_summary')),
          'required_handoff': handoff[0], 'attempts': len(requests), 'received_bytes': state['received_bytes'],
          'request_outcomes': dict(collections.Counter(row['outcome'] for row in requests)),
          'byte_hash_intent_cross_checks': 'PASS', 'crosscheck_retained_child_entries': 'PASS', 'start_spacing': 'PASS',
          'limitation': 'Availability accounting is separate from source-body format support or ingestion completeness'}
print(json.dumps(result, indent=2))
