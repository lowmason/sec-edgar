from collections import Counter
import hashlib
import json
from pathlib import Path

sdd = Path('.sdd/2-sec-filing-index-ingestion-stage-2-spec')
text = (sdd/'task-7-fix1-covering-green.txt').read_text()
stdout, stderr = text.split('stdout:\n', 1)[1].split('\nstderr:\n', 1)
body, code = stderr.rsplit('\nexit_code=', 1)
lines = body.splitlines()
tests = [line for line in lines if line.startswith('test_')]
assert not stdout.strip() and code.strip() == '0'
assert len(tests) == 118 and all(line.endswith(' ... ok') for line in tests)
assert [line for line in lines if line and not line.startswith('test_')] == ['----------------------------------------------------------------------', 'Ran 118 tests in 18.188s', 'OK']
root = sdd/'task-7-fix1-covering-traces'
points = ('after_receipt_checkpoint', 'after_raw_promotion', 'after_promotion_receipt',
          'after_snapshot_record', 'after_binding', 'after_snapshot_workset_write', 'before_result_write')
prefix_sha = hashlib.sha256(b'retained retry prefix').hexdigest()
summary = {'covering_tests': len(tests), 'exit_code': 0, 'unexpected_output': [], 'retry_prefix_processes': []}
for index, point in enumerate(points):
    record = json.loads((root/('retry-prefix-crash-'+point+'.json')).read_text())
    assert [record[key]['exit_code'] for key in ('crash', 'recovered', 'repeated')] == [73, 0, 0]
    assert all(record[key][stream] == '' for key in ('crash', 'recovered', 'repeated') for stream in ('stdout', 'stderr'))
    events = record['events']
    assert Counter(event['event'] for event in events) == {'fetch': 2, 'forced_exit': 1, 'process_result': 2}
    checkpoint = next(event for event in events if event['event'] == 'forced_exit')
    assert checkpoint['point'] == point and checkpoint['fetch_count'] == 2
    assert len({event['pid'] for event in events}) == 3
    assert {event['pid'] for event in events if event['event'] == 'fetch'} == {checkpoint['pid']}
    assert len(checkpoint['retry_evidence']) == 1
    before = checkpoint['retry_evidence'][0]
    request = before['request']
    assert before['verified'] and not before['temporary_exists_after']
    assert before['temporary_body_hex'] == before['body_hex'] == b'retained retry prefix'.hex()
    assert record['after']['body_hex'] == before['body_hex']
    assert record['after']['sidecar_bytes'] == before['sidecar_bytes']
    assert not record['after']['old_temporary_exists']
    metadata = json.loads(before['sidecar_bytes'])
    assert metadata['receipt'] == request['receipt']
    assert metadata['context'] == request['context']
    assert metadata['error'] == request['error']
    assert metadata['request_id'] == request['request_id'] == request['permit']['request_id']
    assert metadata['body_path'] == before['path']
    assert metadata['source']['source_id'] == request['source_id']
    assert before['path'] == f"quarantine/sec/{request['context']['run_id']}/{request['source_id']}/{request['context']['attempt_id']}/{request['request_id']}/body"
    assert metadata['receipt']['sha256'] == prefix_sha
    assert metadata['receipt']['headers'] == {'X-Fixture': 'partial'}
    assert (metadata['receipt']['byte_count'], metadata['receipt']['complete'], metadata['error']['code']) == (21, False, 'read_timeout')
    for event in events:
        if event['event'] == 'process_result':
            result = event['result']
            assert (result['outcome'], result['downloaded'], result['unchanged'], result['pending'], result['failed'], result['quarantined']) == ('success', 0, 1, 0, 0, 0)
            assert result['gaps'] == []
            current = result['context']
            assert (current['run_id'], current['execution_id'], current['attempt_id']) == ('successor-run', 'successor-execution', 'successor-attempt')
            assert all(current[field] != request['context'][field] for field in ('run_id', 'execution_id', 'attempt_id'))
    assert record['snapshot_workset_bytes'] == record['recovered_snapshot_workset_bytes']
    if index >= 5:
        assert checkpoint['snapshot_workset_bytes'] == record['snapshot_workset_bytes']
    snapshot = json.loads(record['snapshot_workset_bytes'])['snapshots'][0]
    accepted_receipt = checkpoint['staged_receipts'][0]['receipt']
    assert (snapshot['sha256'], snapshot['byte_count'], snapshot['received_at'], snapshot['validators']) == (accepted_receipt['sha256'], accepted_receipt['byte_count'], accepted_receipt['received_at'], accepted_receipt['headers'])
    if index >= 1:
        raw = checkpoint['raw'][0]
        assert raw['verified'] and raw['path'] == snapshot['raw_path']
        assert hashlib.sha256(bytes.fromhex(raw['body_hex'])).hexdigest() == snapshot['sha256']
    if index >= 4:
        assert checkpoint['bindings'][0]['snapshot_sha256'] == snapshot['sha256']
    summary['retry_prefix_processes'].append({'point': point, 'exit_codes': [73, 0, 0],
        'pids': sorted({event['pid'] for event in events}), 'original_request_id': request['request_id'],
        'prefix_sha256': prefix_sha, 'before_after_body_and_sidecar_identical': True,
        'old_failed_spool_removed': True, 'successor_transport_calls': 0,
        'new_context_quarantined': 0, 'repeated_workset_bytes_identical': True})
    original = json.loads((root/('crash-'+point+'.json')).read_text())
    assert [original[key]['exit_code'] for key in ('crash', 'recovered', 'repeated')] == [73, 0, 0]
    assert all(original[key][stream] == '' for key in ('crash', 'recovered', 'repeated') for stream in ('stdout', 'stderr'))
    assert Counter(event['event'] for event in original['events']) == {'fetch': 1, 'forced_exit': 1, 'process_result': 2}
    assert len({event['pid'] for event in original['events']}) == 3
race = json.loads((root/'changed-original-bind-race.json').read_text())
counts = Counter(event['event'] for event in race['ordered_events'])
assert race['exit_codes'] == [0, 0]
assert counts['bind_read_absent'] == counts['bind_insert_attempt'] == 2
assert counts['bind_insert_success'] == counts['bind_insert_conflict'] == 1
assert len({result['candidate_sha256'] for result in race['results']}) == 2
assert len({result['result']['snapshot_workset_ref'] for result in race['results']}) == 1
assert max(event['monotonic_ns'] for event in race['ordered_events'] if event['event'] == 'bind_read_absent') < min(event['monotonic_ns'] for event in race['ordered_events'] if event['event'] == 'bind_insert_attempt')
summary['original_crash_proofs'] = 7
summary['actual_binding_race'] = {'different_originals': 2, 'insert_attempts': 2, 'insert_conflicts': 1, 'exit_codes': [0, 0]}
assert len(list(root.glob('*.json'))) == 16
print(json.dumps(summary, indent=2, sort_keys=True))
