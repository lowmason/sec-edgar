"""Read and verify current retained process/recovery/guard proof after the full check."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
from sec_edgar_ingest.models import CommandResult
from sec_edgar_ingest.worksets import decode_snapshot_workset, encode_workset

EVIDENCE = Path('.sdd/2-sec-filing-index-ingestion-stage-2-spec/final-review-fix1-evidence')
TRACES = EVIDENCE / 'latest-complete-traces'


def read(folder, name):
    return json.loads((TRACES / folder / name).read_text())


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main():
    race = read('acquisition', 'three-collector-race.json')
    assert len(race['processes']) == 3 and len({row['pid'] for row in race['processes']}) == 3
    assert all(row['exit'] == 0 for row in race['processes'])
    events = Counter(row['event'] for row in race['events'])
    assert (events['bind_read_absent'], events['bind_insert_attempt'], events['bind_insert_success'], events['bind_insert_conflict']) == (3, 3, 1, 2)
    absent = [row['monotonic_ns'] for row in race['events'] if row['event'] == 'bind_read_absent']
    inserts = [row['monotonic_ns'] for row in race['events'] if row['event'] == 'bind_insert_attempt']
    assert max(absent) < min(inserts)
    body = bytes.fromhex(race['raw_hex'])
    assert sha(body) == race['winner']['sha256'] and len(body) == race['winner']['byte_count']
    frozen_body = bytes.fromhex(race['workset_hex'])
    frozen = decode_snapshot_workset(frozen_body)
    assert encode_workset(frozen) == frozen_body
    assert len({record['result']['snapshot_workset_ref'] for record in race['records']}) == 1
    assert all(record['result']['snapshot_workset_ref'] == race['replay']['snapshot_workset_ref'] for record in race['records'])
    assert race['replay']['downloaded'] == 0 and race['replay']['unchanged'] == 1
    starts = sorted(row['monotonic_ns'] for row in race['events'] if row['event'] == 'request-start')
    spacing = [(current - previous) / 1e9 for previous, current in zip(starts, starts[1:])]
    assert len(starts) == 3 and min(spacing) >= 1 / 3

    takeover = read('acquisition', 'integrated-takeover.json')
    assert takeover['parent_exit'] == -15 and takeover['successor_exit'] == 0
    assert takeover['old_child_drained'] and takeover['zero_successor_through_guard']
    assert takeover['child_alarm_disposition'] == 'default-fatal'
    assert all(row['successor_requests'] == 0 for row in takeover['unsafe_observations'])
    assert takeover['successor_first_start'] >= takeover['unsafe_until_mono']
    assert takeover['successor_first_start'] > takeover['old_socket_closed']
    wire = takeover['all_wire_starts']
    assert len(wire) == 4 and takeover['ordered_priorities'] == ['daily', 'daily', 'daily', 'backfill']
    wire_spacing = [current['monotonic'] - previous['monotonic'] for previous, current in zip(wire, wire[1:])]
    assert min(wire_spacing) >= 1 / 3
    timer = read('acquisition', 'independent-child-deadline.json')
    assert timer['child_exit']['exitcode'] == -14
    timer_body = bytes.fromhex(timer['body_hex'])
    assert len(timer_body) > 0 and sha(timer_body) == timer['body_sha256'] == timer['receipt']['sha256']
    assert timer['receipt']['byte_count'] == len(timer_body)
    stale = read('acquisition', 'stale-dispatch.json')
    assert not stale['receipt']['complete']
    assert all(row['event'] != 'socket-start' for row in stale['transport'])
    assert all(row['event'] != 'request-received' for row in stale['server'])

    crashes = []
    prefixes = []
    for path in sorted((TRACES / 'collection').glob('*crash-*.json')):
        value = json.loads(path.read_text())
        exits = [value[name]['exit_code'] for name in ('crash', 'recovered', 'repeated')]
        assert exits == [73, 0, 0]
        snapshot_body = value['snapshot_workset_bytes'].encode()
        snapshot = decode_snapshot_workset(snapshot_body)
        assert encode_workset(snapshot) == snapshot_body
        record = {'path': path.name, 'process_exits': exits, 'snapshot_id': snapshot.workset_id,
                  'process_pids': sorted({event['pid'] for event in value['events'] if 'pid' in event})}
        crashes.append(record)
        if path.name.startswith('retry-prefix-'):
            prefix = bytes.fromhex(value['after']['body_hex'])
            assert prefix == b'retained retry prefix' and not value['after']['old_temporary_exists']
            sidecar = json.loads(value['after']['sidecar_bytes'])
            assert sidecar['receipt']['sha256'] == sha(prefix) and sidecar['receipt']['byte_count'] == len(prefix)
            assert sidecar['body_path'].startswith('quarantine/sec/')
            assert encode_workset(decode_snapshot_workset(value['recovered_snapshot_workset_bytes'].encode())) == value['recovered_snapshot_workset_bytes'].encode()
            prefixes.append(record | {'retained_prefix_sha256': sha(prefix), 'old_temporary_exists': False})
    assert len(crashes) == 14 and len(prefixes) == 7
    results = []
    for path in sorted((TRACES / 'acquisition').glob('result-crash-*.json')):
        value = json.loads(path.read_text())
        assert value['crash']['exit'] == 74 and value['replay']['exit'] == 0
        after = bytes.fromhex(value['after_result_hex'])
        result = CommandResult.from_json(after)
        assert result.to_json() == after
        assert value['after_attempt']['result'] == result.to_mapping()
        if value['before_result_hex']:
            assert value['before_result_hex'] == value['after_result_hex']
        results.append({'path': path.name, 'crash_exit': 74, 'replay_exit': 0,
                        'result_sha256': sha(after), 'actual_context': result.context.to_mapping(),
                        'prior_immutable_result_preserved': bool(value['before_result_hex'])})
    assert len(results) == 4

    guards = []
    for path in sorted((TRACES / 'guard').glob('*.json')):
        value = json.loads(path.read_text())
        assert value['exit'] == 0
        proof = value['proof']
        denied = proof['denied']
        assert all(denied) if isinstance(denied, list) else denied
        guards.append({'path': path.name, 'exit': value['exit'], 'proof': proof})
    assert len(guards) == 7
    proof = {'recorded_at': datetime.now(timezone.utc).isoformat(), 'exit_code': 0,
             'three_collectors': {'processes': race['processes'], 'events': dict(events), 'minimum_start_spacing_seconds': min(spacing),
                                  'winner': race['winner'], 'replay_downloaded': 0, 'replay_unchanged': 1},
             'takeover': {'parent_pid': takeover['parent_pid'], 'parent_exit': -15, 'successor_exit': 0,
                          'zero_successor_observations': len(takeover['unsafe_observations']),
                          'unsafe_until_utc': takeover['old_journal']['value']['unsafe_until'],
                          'unsafe_until_mono': takeover['unsafe_until_mono'], 'old_socket_closed': takeover['old_socket_closed'],
                          'successor_first_start': takeover['successor_first_start'], 'old_child_drained': True,
                          'wire_priority_order': takeover['ordered_priorities'], 'minimum_wire_spacing_seconds': min(wire_spacing)},
             'independent_timer': {'child_exit': timer['child_exit'], 'prefix_bytes': len(timer_body), 'prefix_sha256': sha(timer_body)},
             'stale_dispatch': {'server_requests': 0, 'socket_starts': 0},
             'collection_crashes': crashes, 'retry_prefix_preservation': prefixes,
             'result_attempt_crashes': results, 'guard_receipts': guards,
             'scope': 'synthetic local macOS process/selected-loopback evidence; all22 S7 reserved; no live provider assertion'}
    path = EVIDENCE / 'process-proof-inspection.json'
    assert not path.exists()
    path.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'exit_code': 0, 'collectors': race['processes'], 'zero_successor_observations': len(takeover['unsafe_observations']),
                      'minimum_wire_spacing_seconds': min(wire_spacing), 'timer_exit': -14,
                      'collection_crashes': len(crashes), 'prefix_crashes': len(prefixes),
                      'result_crashes': len(results), 'guard_receipts': len(guards)}))


if __name__ == '__main__':
    main()
