from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from support import valid_idx_response

sdd = Path('.sdd/2-sec-filing-index-ingestion-stage-2-spec')
text = (sdd / 'task-7-full-green.txt').read_text()
stdout, stderr = text.split('stdout:\n', 1)[1].split('\nstderr:\n', 1)
body, exit_code = stderr.rsplit('\nexit_code=', 1)
tests = [line for line in body.splitlines() if line.startswith('test_')]
assert not stdout.strip() and exit_code.strip() == '0'
assert len(tests) == 250 and all(line.endswith(' ... ok') for line in tests)
other = [line for line in body.splitlines() if line and not line.startswith('test_')]
assert other == ['----------------------------------------------------------------------', 'Ran 250 tests in 26.141s', 'OK']
summary = {'full_suite': {'tests': len(tests), 'exit_code': 0, 'unexpected_output': []}, 'crashes': []}
points = ('after_receipt_checkpoint', 'after_raw_promotion', 'after_promotion_receipt',
          'after_snapshot_record', 'after_binding', 'after_snapshot_workset_write', 'before_result_write')
root = sdd / 'task-7-full-traces'
expected_sha = hashlib.sha256(valid_idx_response('daily').body).hexdigest()
for index, point in enumerate(points):
    record = json.loads((root / ('crash-' + point + '.json')).read_text())
    assert [record[key]['exit_code'] for key in ('crash', 'recovered', 'repeated')] == [73, 0, 0]
    assert all(record[key][stream] == '' for key in ('crash', 'recovered', 'repeated')
               for stream in ('stdout', 'stderr'))
    events = record['events']
    assert Counter(event['event'] for event in events) == {'fetch': 1, 'forced_exit': 1, 'process_result': 2}
    pids = sorted({event['pid'] for event in events})
    assert len(pids) == 3
    checkpoint = next(event for event in events if event['event'] == 'forced_exit')
    assert checkpoint['point'] == point and checkpoint['fetch_count'] == 1
    assert len(checkpoint['staged_receipts']) == 1
    assert len(checkpoint['promotions']) == int(index >= 2)
    assert len(checkpoint['snapshots']) == int(index >= 3)
    assert len(checkpoint['bindings']) == int(index >= 4)
    receipt = checkpoint['staged_receipts'][0]
    transport = receipt['transport_attempt']
    fetch = next(event for event in events if event['event'] == 'fetch')
    assert receipt['request_id'] == transport['request_id'] == transport['permit']['request_id'] == fetch['request_id']
    assert transport['receipt'] == receipt['receipt']
    assert transport['context'] == receipt['context'] == fetch['context']
    assert receipt['receipt']['sha256'] == expected_sha
    assert receipt['temporary_ref'].endswith('/' + receipt['request_id'] + '/body')
    final = json.loads(record['snapshot_workset_bytes'])
    snapshot = final['snapshots'][0]
    assert snapshot['sha256'] == expected_sha
    raw = checkpoint['raw'][0]
    assert raw['path'] == snapshot['raw_path']
    assert raw['verified'] == (index > 0)
    if raw['verified']:
        original = bytes.fromhex(raw['body_hex'])
        assert hashlib.sha256(original).hexdigest() == snapshot['sha256']
        assert len(original) == snapshot['byte_count']
    if index >= 5:
        assert record['prior_snapshot_bytes'] == record['snapshot_workset_bytes']
    for event in events:
        if event['event'] == 'process_result':
            result = event['result']
            assert (result['outcome'], result['downloaded'], result['unchanged'], result['pending'], result['failed']) == ('success', 0, 1, 0, 0)
            assert result['gaps'] == []
    summary['crashes'].append({'point': point, 'exit_codes': [73, 0, 0], 'pids': pids,
                              'fetches': 1, 'snapshot_sha256': expected_sha,
                              'raw_present_before_exit': raw['verified'],
                              'existing_workset_bytes_equal': index >= 5})
race = json.loads((root / 'changed-original-bind-race.json').read_text())
assert race['exit_codes'] == [0, 0]
events = race['ordered_events']
assert events == sorted(events, key=lambda event: event['monotonic_ns'])
counts = Counter(event['event'] for event in events)
assert counts['receipt_checkpoint'] == counts['bind_read_absent'] == counts['bind_insert_attempt'] == counts['adopted'] == 2
assert counts['bind_insert_success'] == counts['bind_insert_conflict'] == 1
absent = [event for event in events if event['event'] == 'bind_read_absent']
inserts = [event for event in events if event['event'] == 'bind_insert_attempt']
assert max(event['monotonic_ns'] for event in absent) < min(event['monotonic_ns'] for event in inserts)
assert len({event['pid'] for event in inserts}) == 2
candidates = {result['candidate_sha256'] for result in race['results']}
expected = {hashlib.sha256(valid_idx_response('daily', company=name).body).hexdigest() for name in ('Original One', 'Original Two')}
assert candidates == expected and len(candidates) == 2
assert {result['result']['outcome'] for result in race['results']} == {'success'}
assert len({result['result']['snapshot_workset_ref'] for result in race['results']}) == 1
adopted = [event['snapshots'] for event in events if event['event'] == 'adopted']
assert adopted[0] == adopted[1] and adopted[0][0]['sha256'] in candidates
summary['race'] = {'exit_codes': race['exit_codes'], 'candidate_sha256': sorted(candidates),
                   'pids': sorted({event['pid'] for event in inserts}),
                   'two_absent_reads_before_inserts': True, 'actual_insert_attempts': 2,
                   'actual_insert_conflicts': 1, 'adopted_sha256': adopted[0][0]['sha256']}
partial = json.loads((root / 'two-source-process-resume.json').read_text())
assert [partial[key]['exit_code'] for key in ('crash', 'recovery', 'repeated')] == [73, 0, 0]
assert all(partial[key][stream] == '' for key in ('crash', 'recovery', 'repeated') for stream in ('stdout', 'stderr'))
result = partial['result']
assert (result['outcome'], result['downloaded'], result['unchanged'], result['pending'], result['failed']) == ('success', 1, 1, 0, 0)
fetches = [event for event in partial['events'] if event['event'] == 'fetch']
assert len(fetches) == len({event['url'] for event in fetches}) == len({event['pid'] for event in fetches}) == 2
summary['two_source_restart'] = {'exit_codes': [73, 0, 0], 'distinct_fetch_urls': [event['url'] for event in fetches],
                                 'downloaded': 1, 'unchanged': 1, 'pending': 0}
print(json.dumps(summary, indent=2, sort_keys=True))
