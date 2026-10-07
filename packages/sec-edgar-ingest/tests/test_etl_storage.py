"""Offline ETL logical object routing contracts."""
import unittest
from sec_edgar_ingest.storage.contracts import blob_address


class EtlStorageTests(unittest.TestCase):
    def test_logical_paths_use_accepted_containers(self):
        self.assertEqual(blob_address('runs/sec/r/transform/a/result.json'),
                         ('results', 'runs/sec/r/transform/a/result.json'))
        path = 'curated/sec/filing_index/year=2026/quarter=4/generation=g/manifest.json'
        self.assertEqual(blob_address(path), ('manifests', path))
        path = 'observations/sec/indexes/source=s/sha256=h/parser=p/schema=v/rows.parquet'
        self.assertEqual(blob_address(path), ('generations', path))
        self.assertEqual(blob_address('raw/sec/a'), ('raw', 'sec/a'))
        with self.assertRaises(ValueError):
            blob_address('curated/../raw/a')

    def test_local_materialize_is_exclusive_and_cleans_failed_copy(self):
        import tempfile
        from pathlib import Path
        from sec_edgar_ingest.storage.local import LocalObjectStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            objects = LocalObjectStore(root/'store')
            body = b'rows' * (1024 * 300)
            objects.put_once('observations/sec/rows.parquet', body)
            target = root/'rows.parquet'
            objects.materialize('observations/sec/rows.parquet', target)
            self.assertEqual(target.read_bytes(), body)
            with self.assertRaises(FileExistsError):
                objects.materialize('observations/sec/rows.parquet', target)
            self.assertEqual(target.read_bytes(), body)
            missing = root/'missing.parquet'
            with self.assertRaises(FileNotFoundError):
                objects.materialize('observations/sec/missing.parquet', missing)
            self.assertFalse(missing.exists())

    def test_pointer_commit_uses_actual_revision_and_propagates_conflict(self):
        import tempfile
        from pathlib import Path
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.local import LocalStateStore
        from sec_edgar_ingest.storage.contracts import Conflict, AlreadyExists
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStateStore(Path(directory))
            self.addCleanup(store.close)
            state = EtlState(store)
            value = dict(quarter='2026Q4', generation_id='a'*64, manifest_ref='curated/sec/generation=a/manifest.json', manifest_sha256='b'*64, manifest_bytes=10, source_fingerprint='c'*64)
            self.assertIsNone(state.pointer('2026Q4'))
            first = state.commit_pointer('2026Q4', value, None)
            with self.assertRaises((AlreadyExists, Conflict)):
                state.commit_pointer('2026Q4', value, None)
            next_value = {**value, 'generation_id': 'd'*64}
            second = state.commit_pointer('2026Q4', next_value, first)
            self.assertNotEqual(first.version, second.version)
            with self.assertRaises(Conflict):
                state.commit_pointer('2026Q4', value, first)
            self.assertEqual(state.pointer('2026Q4'), second)
            for bad in ({**value, 'quarter': '2026Q3'}, {**value, 'extra': True}, {**value, 'manifest_sha256': '*'}):
                with self.assertRaises(ValueError):
                    state.commit_pointer('2026Q4', bad, second)

    def test_azure_logical_writes_and_streamed_materialization_use_mapped_paths(self):
        import tempfile
        from pathlib import Path
        from azure.storage.blob import BlobServiceClient
        from sec_edgar_ingest.storage.azure import AzureObjectStore
        from test_azure_contracts import ScriptedTransport, response, BLOB_ENDPOINT, RETRY
        for path, container in [('runs/sec/r/result.json', 'results'), ('curated/sec/g/manifest.json', 'manifests'), ('observations/sec/s/rows.parquet', 'generations'), ('staging/sec/temp', 'raw')]:
            transport = ScriptedTransport([response(201), response(body=b'rows')])
            service = BlobServiceClient(BLOB_ENDPOINT, api_version='2026-04-06', transport=transport, **RETRY)
            self.addCleanup(service.close)
            objects = AzureObjectStore(service)
            objects.put_once(path, b'rows')
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory)/'materialized'
                objects.materialize(path, target)
                self.assertEqual(target.read_bytes(), b'rows')
            for request in transport.requests:
                self.assertEqual(request.url.split('?')[0], BLOB_ENDPOINT+'/'+container+'/'+path)
                print('mapped-wire', request.method, request.url.split('?')[0], request.headers.get('If-None-Match'))
            self.assertEqual(transport.requests[0].headers['If-None-Match'], '*')

    def test_active_pointer_real_sdk_insert_replace_and_conflict(self):
        from azure.core.credentials import AzureSasCredential
        from azure.data.tables import TableServiceClient
        from sec_edgar_ingest.storage.azure import AzureStateStore
        from sec_edgar_ingest.storage.contracts import Conflict
        from test_azure_contracts import ScriptedTransport, table_response, table_error, TABLE_ENDPOINT, RETRY
        transport = ScriptedTransport([table_response(201, etag='W/"first"'), table_response(204, etag='W/"second"'), table_error(412, 'UpdateConditionNotSatisfied')])
        service = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential('sv=offline&sig=synthetic'), api_version='2020-12-06', transport=transport, **RETRY)
        self.addCleanup(service.close)
        store = AzureStateStore(service.get_table_client('SourceState'), service.get_table_client('Attempts'), active_client=service.get_table_client('ActivePointers'))
        first = store.insert('QuarterPublication', '2026Q4', {'generation': 'a'})
        second = store.replace('QuarterPublication', '2026Q4', {'generation': 'b'}, first.version)
        self.assertEqual(second.version, 'W/"second"')
        with self.assertRaises(Conflict):
            store.replace('QuarterPublication', '2026Q4', {'generation': 'c'}, first.version)
        for request in transport.requests:
            self.assertIn('/ActivePointers', request.url)
            print('pointer-wire', request.method, request.url.split('?')[0], request.headers.get('If-Match'))
        self.assertEqual(transport.requests[1].headers['If-Match'], first.version)
        old = AzureStateStore(service.get_table_client('SourceState'), service.get_table_client('Attempts'))
        with self.assertRaises(ValueError):
            old.get('QuarterPublication', '2026Q4')
        with self.assertRaises(ValueError):
            AzureStateStore(service.get_table_client('SourceState'), service.get_table_client('Attempts'), active_client=service.get_table_client('Approvals'))

    def test_transform_acceptance_and_publication_receipts_are_idempotent(self):
        import tempfile
        from dataclasses import replace
        from pathlib import Path
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.etl.contracts import Candidate
        from sec_edgar_ingest.storage.local import LocalStateStore
        from sec_edgar_ingest.storage.contracts import Conflict
        from test_etl_contracts import observation_ref, generation_manifest
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStateStore(Path(directory))
            self.addCleanup(store.close)
            state = EtlState(store)
            ref = observation_ref()
            self.assertIsNone(state.processing(ref))
            state.accept_transform(ref)
            accepted = state.processing(ref)
            state.accept_transform(ref)
            self.assertEqual(state.processing(ref), accepted)
            with self.assertRaises(Conflict):
                state.accept_transform(replace(ref, rows_sha256='f'*64))
            manifest = generation_manifest()
            state.record_publication(manifest)
            state.record_publication(manifest)
            self.assertEqual(len(list(store.scan('PublicationReceipt', {}))), 1)
            self.assertEqual(len(list(store.scan('Source', {}))), 0)
            candidate = Candidate(manifest, 'curated/sec/g/manifest.json', 'a'*64, 10, None)
            state.record_candidate(candidate)
            state.record_candidate(candidate)
            self.assertEqual(len(list(store.scan('Candidate', {}))), 1)

    def test_large_active_pointer_record_uses_verified_content_first_descriptor(self):
        import json
        from azure.core.credentials import AzureSasCredential
        from azure.data.tables import TableServiceClient
        from azure.storage.blob import BlobServiceClient
        from sec_edgar_ingest.storage.azure import AzureStateStore, AzureObjectStore
        from test_azure_contracts import BLOB_ENDPOINT, TABLE_ENDPOINT, RETRY
        from test_azure_state_payloads import LimitedStorageTransport
        transport = LimitedStorageTransport()
        blobs = BlobServiceClient(BLOB_ENDPOINT, api_version='2026-04-06', transport=transport, **RETRY)
        tables = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential('sv=offline&sig=synthetic'), api_version='2020-12-06', transport=transport, **RETRY)
        self.addCleanup(blobs.close)
        self.addCleanup(tables.close)
        objects = AzureObjectStore(blobs)
        store = AzureStateStore(tables.get_table_client('SourceState'), tables.get_table_client('Attempts'), active_client=tables.get_table_client('ActivePointers'), objects=objects)
        value = {'retained_evidence': 'x' * (70 * 1024)}
        first = store.insert('QuarterPublication', '2026Q4', value)
        saved = store.get('QuarterPublication', '2026Q4')
        self.assertEqual(saved.to_mapping()['value'], value)
        self.assertEqual(saved.version, first.version)
        writes = [request for request in transport.requests if request.method in ('PUT', 'POST')]
        self.assertIn('/worksets/state/sha256%3D', writes[0].url)
        self.assertIn('/ActivePointers', writes[1].url)
        descriptor = json.loads(writes[1].body)
        self.assertNotIn('Payload', descriptor)
        self.assertEqual(descriptor['PayloadFormat'], 'sec-state-blob-v1')
        self.assertGreater(descriptor['PayloadByteCount'], 64*1024)
        self.assertEqual(transport.requests[1].method, 'GET')
        print('large-pointer-descriptor', descriptor, 'etag', saved.version)

    def test_stream_failure_deletes_only_created_scratch(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from sec_edgar_ingest.storage.azure import AzureObjectStore
        from azure.storage.blob import BlobServiceClient
        from test_azure_contracts import BLOB_ENDPOINT, ScriptedTransport, RETRY
        service = BlobServiceClient(BLOB_ENDPOINT, api_version='2026-04-06', transport=ScriptedTransport([]), **RETRY)
        self.addCleanup(service.close)
        objects = AzureObjectStore(service)
        def broken_chunks():
            yield b'prefix'
            raise OSError('truncated stream')
        with tempfile.TemporaryDirectory() as directory, patch.object(objects, '_blob') as blob:
            blob.return_value.download_blob.return_value.chunks.side_effect = broken_chunks
            target = Path(directory)/'scratch'
            with self.assertRaises(OSError):
                objects.materialize('observations/sec/s/rows.parquet', target)
            self.assertFalse(target.exists())
            target.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):
                objects.materialize('observations/sec/s/rows.parquet', target)
            self.assertEqual(target.read_bytes(), b'existing')

    def test_missing_active_client_refuses_large_write_before_content_upload(self):
        from unittest.mock import Mock
        from sec_edgar_ingest.storage.azure import AzureStateStore
        from test_azure_contracts import TABLE_ENDPOINT
        objects = Mock()
        store = AzureStateStore(Mock(url=TABLE_ENDPOINT, table_name='SourceState'), Mock(url=TABLE_ENDPOINT, table_name='Attempts'), objects=objects)
        with self.assertRaises(ValueError):
            store.insert('QuarterPublication', '2026Q4', {'large': 'x' * 70000})
        objects.put_once.assert_not_called()

    def test_materialize_close_failure_removes_its_created_scratch(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from sec_edgar_ingest.storage.local import LocalObjectStore
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            objects = LocalObjectStore(root/'store')
            objects.put_once('raw/sec/source', b'raw')
            target = root/'scratch'
            original_open = Path.open
            class FailingClose:
                def __init__(self, stream):
                    self.stream = stream
                def __enter__(self):
                    return self.stream
                def __exit__(self, *args):
                    self.stream.close()
                    raise OSError('scratch flush failed')
            def open_file(path, *args, **kwargs):
                stream = original_open(path, *args, **kwargs)
                return FailingClose(stream) if path == target else stream
            with patch.object(Path, 'open', open_file), self.assertRaises(OSError):
                objects.materialize('raw/sec/source', target)
            self.assertFalse(target.exists())

    def test_conflicting_transform_cannot_leave_a_publication_receipt(self):
        import tempfile
        from dataclasses import replace
        from pathlib import Path
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.local import LocalStateStore
        from sec_edgar_ingest.storage.contracts import Conflict
        from test_etl_contracts import observation_ref, generation_manifest
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStateStore(Path(directory))
            self.addCleanup(store.close)
            state = EtlState(store)
            state.accept_transform(observation_ref())
            manifest = replace(generation_manifest(), sources=(replace(observation_ref(), rows_sha256='f'*64),))
            with self.assertRaises(Conflict):
                state.record_publication(manifest)
            self.assertEqual(list(store.scan('PublicationReceipt', {})), [])

    def test_publication_membership_is_monotonic_and_cas_is_bounded(self):
        import tempfile
        from dataclasses import replace
        from pathlib import Path
        from unittest.mock import patch
        from sec_edgar_ingest.etl.state import EtlState
        from sec_edgar_ingest.storage.local import LocalStateStore
        from sec_edgar_ingest.storage.contracts import Conflict, CAS_ATTEMPTS
        from test_etl_contracts import observation_ref, generation_manifest
        with tempfile.TemporaryDirectory() as directory:
            store = LocalStateStore(Path(directory))
            self.addCleanup(store.close)
            state = EtlState(store)
            state.accept_transform(observation_ref())
            manifest = generation_manifest()
            with patch.object(store, 'replace', side_effect=Conflict('race')) as replace_row:
                with self.assertRaises(Conflict):
                    state.record_publication(manifest)
                self.assertEqual(replace_row.call_count, CAS_ATTEMPTS)
            state.record_publication(manifest)
            newer = replace(manifest, generation_id='9'*64)
            state.record_publication(newer)
            state.record_publication(manifest)
            memberships = state.processing(observation_ref()).value['publications']['2015Q1']
            self.assertEqual(set(memberships), {manifest.generation_id, newer.generation_id})
            self.assertEqual(len(list(store.scan('PublicationReceipt', {}))), 2)
