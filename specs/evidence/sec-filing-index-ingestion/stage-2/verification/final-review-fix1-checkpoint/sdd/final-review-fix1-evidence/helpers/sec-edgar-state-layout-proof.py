"""Retain size-safe state layout and CAS-loser observations through offline pinned SDKs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
sys.path.insert(0, str(Path.cwd() / 'packages/sec-edgar-ingest/tests'))
import network_guard
network_guard.install()
from test_azure_state_payloads import AzureStatePayloadTests
from test_azure_contracts import TABLE_ENDPOINT


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main():
    test = AzureStatePayloadTests()
    test.setUp()
    root = Path('.sdd/2-sec-filing-index-ingestion-stage-2-spec/final-review-fix1-evidence/state-layout')
    assert not root.exists()
    root.mkdir()
    try:
        store, objects = test.stores()
        test.register_intended_history(store)
        original = store.get('DiscoveryBoundary', 'daily')
        value = original.to_mapping()['value']
        logical = test.azure.payload_bytes(value)
        changed = deepcopy(value)
        changed['gaps'].pop(next(iter(changed['gaps'])))
        winner = store.replace('DiscoveryBoundary', 'daily', changed, original.version)
        before_loser = set(test.transport.blobs)
        losing = deepcopy(value)
        losing['loser_candidate_only'] = True
        try:
            store.replace('DiscoveryBoundary', 'daily', losing, original.version)
            raise AssertionError('stale complete-record CAS unexpectedly succeeded')
        except test.contracts.Conflict:
            pass
        candidates = set(test.transport.blobs) - before_loser
        assert len(candidates) == 1
        assert store.get('DiscoveryBoundary', 'daily') == winner
        candidate_path = candidates.pop()
        candidate_body = test.transport.blobs[candidate_path]
        candidate = json.loads(candidate_body)
        assert candidate['value'] == losing
        descriptor, etag = test.transport.rows[('SourceState', 'sec-owner-lowell-mason:DiscoveryBoundary', 'daily')]
        assert descriptor['PayloadSha256'] != sha(candidate_body) and etag == winner.version
        assert sha(candidate_body) in candidate_path
        # Whole logical values above the Table entity ceiling use the same one-row format in Attempts.
        large = {'text': '😀' * 300000}
        attempt = store.insert('Attempt', 'overflow-attempt', large)
        assert store.get('Attempt', 'overflow-attempt') == attempt
        blobs = []
        for index, (path, body) in enumerate(sorted(test.transport.blobs.items())):
            target = root / f'content-{index:02}.json'
            target.write_bytes(body)
            blobs.append({'path': path, 'bytes': len(body), 'sha256': sha(body), 'retained_bytes_file': target.name})
        entities = []
        for (table, partition, key), (wire, version) in sorted(test.transport.rows.items()):
            entity = {name: item for name, item in wire.items() if '@' not in name}
            properties = {name: len(item.encode('utf-16-le')) for name, item in entity.items() if isinstance(item, str)}
            data_bytes = sum(len(name.encode('utf-16-le')) +
                             (len(item.encode('utf-16-le')) if isinstance(item, str) else 8)
                             for name, item in entity.items())
            assert max(properties.values()) <= 65536 and data_bytes + 1024 <= 1048576
            test.azure._check_table_entity(entity)
            entities.append({'table': table, 'partition': partition, 'key': key, 'etag': version,
                             'entity': entity, 'string_utf16_bytes': properties,
                             'property_name_and_value_bytes': data_bytes, 'conservative_entity_bound_bytes': data_bytes + 1024})
        requests = []
        for request in test.transport.requests:
            body = request.body
            if hasattr(body, 'read'):
                body = body.read()
            if isinstance(body, str):
                body = body.encode()
            requests.append({'method': request.method, 'url': request.url,
                             'headers': dict(request.headers), 'body_bytes': len(body or b''),
                             'body_sha256': sha(body) if body else None})
        proof = {'kind': 'offline scripted actual SDK wire/layout', 'live_storage_access': False,
                 'inventory_units': 86, 'original_logical_utf8_bytes': len(logical),
                 'original_logical_utf16_bytes': len(logical.decode().encode('utf-16-le')),
                 'original_etag': original.version, 'winner_etag': winner.version,
                 'winner_verified_after_distinct_losing_candidate': True,
                 'losing_candidate_immutable_path': candidate_path,
                 'losing_candidate_sha256': sha(candidate_body), 'losing_candidate_referenced_by_winner': False,
                 'above_entity_logical_utf8_bytes': len(test.azure.payload_bytes(large)),
                 'state_and_objects_share_same_object_store': store.objects is objects,
                 'entities': entities, 'immutable_contents': blobs, 'requests': requests}
        (root / 'state-layout-proof.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'units': 86, 'logical_utf16_bytes': proof['original_logical_utf16_bytes'],
                          'table_entities': len(entities), 'immutable_contents': len(blobs),
                          'max_emitted_string_utf16_bytes': max(max(item['string_utf16_bytes'].values()) for item in entities),
                          'max_emitted_conservative_entity_bytes': max(item['conservative_entity_bound_bytes'] for item in entities),
                          'distinct_losing_candidate_retained': True}))
    finally:
        test.doCleanups()


if __name__ == '__main__':
    main()
