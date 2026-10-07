"""Real pinned SDK request construction with an in-memory HTTP transport only."""
import hashlib
import importlib
import importlib.util
import json
import tempfile
import unittest
from collections import deque
from datetime import timedelta
from importlib.metadata import version
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from azure.core.credentials import AzureSasCredential
from azure.core.exceptions import DeserializationError, HttpResponseError
from azure.core.pipeline.transport import HttpResponse, HttpTransport
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
from requests.structures import CaseInsensitiveDict

from support import FixtureClock, fixture_settings, fixture_snapshot, fixture_source

BLOB_ENDPOINT = "https://secedgardevb8617.blob.core.windows.net"
TABLE_ENDPOINT = "https://secedgardevb8617.table.core.windows.net"
DATE = "Tue, 06 Oct 2026 00:00:00 GMT"
RETRY = dict(retry_total=0, retry_connect=0, retry_read=0, retry_status=0)


class ScriptedStream:
    def __init__(self, response):
        self.response = response
        self.content_length = int(response.headers["Content-Length"])
        self._chunks = iter((response.body(),))

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._chunks)


class ScriptedResponse(HttpResponse):
    def __init__(self, request, status, headers, body):
        super().__init__(request, None)
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers)
        self.reason = "scripted offline response"
        self.content_type = self.headers.get("Content-Type")
        self._body = body
        self.location_mode = "primary"

    def read(self):
        return self._body

    def close(self):
        pass

    def body(self):
        return self._body

    def text(self, encoding=None):
        return self._body.decode(encoding or "utf-8")

    def stream_download(self, pipeline, **kwargs):
        return ScriptedStream(self)


class ScriptedTransport(HttpTransport):
    def __init__(self, responses):
        self.responses = deque(responses)
        self.requests = []

    def open(self):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def send(self, request, **kwargs):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unscripted HTTP request; network transport is forbidden")
        status, headers, body = self.responses.popleft()
        if request.method == "GET" and ".blob.core.windows.net" in request.url and status == 200 and body:
            headers = {**headers, "Content-Range": f"bytes 0-{len(body) - 1}/{len(body)}"}
            status = 206
        return ScriptedResponse(request, status, headers, body)


def response(status=200, *, etag='"opaque-service-etag"', body=b"", headers=None):
    result = {"Date": DATE, "Content-Length": str(len(body)), "Content-Type": "application/octet-stream"}
    if etag is not None:
        result["ETag"] = etag
    result.update(headers or {})
    return status, result, body


def entity(key="identity", value=None, etag='W/"exact-observed-opaque"', kind="Source"):
    return {"PartitionKey": "sec-owner-lowell-mason:" + kind, "RowKey": key,
            "StableKey": key, "Payload": json.dumps(value if value is not None else {"count": 1}),
            "Timestamp": "2026-10-06T00:00:00Z", **({"odata.etag": etag} if etag is not None else {})}


def table_response(status=200, *, value=None, headers=None, etag='W/"actual-read-etag"'):
    body = json.dumps(value if value is not None else entity()).encode()
    return response(status, etag=etag, body=body, headers={"Content-Type": "application/json", **(headers or {})})


def blob_error(status, code):
    return response(status, body=f"<Error><Code>{code}</Code><Message>offline contract failure</Message></Error>".encode(),
                    headers={"Content-Type": "application/xml", "x-ms-error-code": code})


def table_error(status, code):
    return table_response(status, value={"odata.error": {"code": code, "message": {"lang": "en-US", "value": "offline failure"}}})


class AzureContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("sec_edgar_ingest.storage.azure"),
                             "Pinned SDK adapters must issue conditional storage HTTP requests")
        self.azure = importlib.import_module("sec_edgar_ingest.storage.azure")
        self.contracts = importlib.import_module("sec_edgar_ingest.storage.contracts")

    def blobs(self, responses):
        transport = ScriptedTransport(responses)
        service = BlobServiceClient(BLOB_ENDPOINT, api_version="2026-04-06", transport=transport, **RETRY)
        self.addCleanup(service.close)
        return service, transport

    def tables(self, responses):
        transport = ScriptedTransport(responses)
        # Synthetic SAS only satisfies the SDK's pure constructor; every send uses this transport.
        service = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential("sv=offline&sig=synthetic"),
                                     api_version="2020-12-06", transport=transport, **RETRY)
        self.addCleanup(service.close)
        store = self.azure.AzureStateStore(service.get_table_client("SourceState"), service.get_table_client("Attempts"))
        return store, transport

    def test_installed_pins_are_exact(self):
        self.assertEqual(version("azure-storage-blob"), "12.31.0")
        self.assertEqual(version("azure-data-tables"), "12.7.0")
        self.assertEqual(version("azure-core"), "1.41.0")

    def test_blob_create_is_explicit_version_and_if_none_match(self):
        service, transport = self.blobs([response(201)])
        objects = self.azure.AzureObjectStore(service)
        self.assertEqual(objects.put_once("worksets/source/identity.json", b"manifest"), "worksets/source/identity.json")
        request = transport.requests[0]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.headers["x-ms-version"], "2026-04-06")
        self.assertEqual(request.headers["If-None-Match"], "*")
        self.assertNotIn("If-Match", request.headers)
        self.assertEqual(request.body, b"manifest")
        self.assertTrue(request.url.startswith(BLOB_ENDPOINT + "/worksets/source/identity.json"))
        self.assertFalse(transport.responses)

    def test_blob_collision_verifies_equal_content_and_preserves_different_content(self):
        for body, succeeds in ((b"accepted", True), (b"different", False)):
            with self.subTest(succeeds=succeeds):
                service, transport = self.blobs([blob_error(409, "BlobAlreadyExists"), response(body=body)])
                objects = self.azure.AzureObjectStore(service)
                if succeeds:
                    self.assertEqual(objects.put_once("raw/immutable", b"accepted"), "raw/immutable")
                else:
                    with self.assertRaises(self.contracts.Conflict):
                        objects.put_once("raw/immutable", b"accepted")
                self.assertEqual([request.method for request in transport.requests], ["PUT", "GET"])
                self.assertEqual(transport.requests[0].headers["If-None-Match"], "*")
                self.assertFalse(transport.responses)

    def test_blob_stage_promote_uses_blob_create_without_dfs_rename(self):
        body = b"staged bytes"
        snapshot = fixture_snapshot(fixture_source(), body)
        service, transport = self.blobs([response(201), response(body=body), response(body=body),
                                        response(201), response(body=body)])
        objects = self.azure.AzureObjectStore(service)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt"
            path.write_bytes(body)
            temporary = objects.stage("raw/.staging/body", path)
            self.assertEqual(objects.promote(temporary, snapshot.raw_path, snapshot.sha256, len(body)), snapshot.raw_path)
        writes = [request for request in transport.requests if request.method == "PUT"]
        self.assertEqual(len(writes), 2)
        self.assertTrue(all(request.headers["If-None-Match"] == "*" for request in writes))
        self.assertTrue(all(".blob.core.windows.net/" in request.url for request in transport.requests))
        self.assertFalse(any("rename" in request.url or "copy" in request.headers for request in transport.requests))
        self.assertFalse(transport.responses)

    def test_blob_errors_do_not_retry_or_become_immutable_success(self):
        service, transport = self.blobs([blob_error(500, "InternalError")])
        with self.assertRaises(HttpResponseError):
            self.azure.AzureObjectStore(service).put_once("raw/identity", b"body")
        self.assertEqual(len(transport.requests), 1)
        service, transport = self.blobs([blob_error(404, "BlobNotFound")])
        with self.assertRaises(FileNotFoundError):
            self.azure.AzureObjectStore(service).read("raw/absent")
        self.assertEqual(len(transport.requests), 1)

    def test_table_insert_is_atomic_create_and_returns_actual_write_etag(self):
        store, transport = self.tables([response(204, etag='W/"write-response-version"')])
        row = store.insert("Source", "identity", {"count": 1})
        self.assertEqual(row.version, 'W/"write-response-version"')
        request = transport.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["x-ms-version"], "2020-12-06")
        self.assertNotIn("If-Match", request.headers)
        payload = json.loads(request.body)
        self.assertEqual(payload["PartitionKey"], "sec-owner-lowell-mason:Source")
        self.assertEqual(payload["RowKey"], "identity")
        self.assertEqual(json.loads(payload["Payload"]), {"count": 1})
        self.assertIn("/SourceState", request.url)

    def test_table_replace_uses_put_and_exact_opaque_if_match(self):
        store, transport = self.tables([response(204, etag='W/"updated-service-version"')])
        row = store.replace("Source", "identity", {"count": 2}, 'W/"opaque-original-version"')
        self.assertEqual(row.version, 'W/"updated-service-version"')
        request = transport.requests[0]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.headers["If-Match"], 'W/"opaque-original-version"')
        self.assertEqual(request.headers["x-ms-version"], "2020-12-06")
        self.assertNotIn("If-None-Match", request.headers)
        for invalid in ("", "*"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                store.replace("Source", "identity", {}, invalid)
        self.assertEqual(len(transport.requests), 1)

    def test_table_create_conflict_stale_replace_and_not_found_map_exactly(self):
        store, transport = self.tables([table_error(409, "EntityAlreadyExists"), table_error(412, "UpdateConditionNotSatisfied"), table_error(404, "ResourceNotFound")])
        with self.assertRaises(self.contracts.AlreadyExists):
            store.insert("Source", "identity", {})
        with self.assertRaises(self.contracts.Conflict):
            store.replace("Source", "identity", {}, 'W/"stale"')
        self.assertIsNone(store.get("Source", "absent"))
        self.assertEqual(len(transport.requests), 3)

    def test_table_get_uses_raw_header_never_timestamp_fabricated_etag(self):
        store, transport = self.tables([table_response(value=entity(etag=None), etag='W/"real-header-only"'),
                                        table_response(value=entity(etag=None), etag=None)])
        row = store.get("Source", "identity")
        self.assertEqual(row.version, 'W/"real-header-only"')
        self.assertEqual(row.value["count"], 1)
        with self.assertRaises(self.contracts.Conflict):
            store.get("Source", "identity")
        self.assertEqual(len(transport.requests), 2)

    def test_table_query_exhausts_continuations_including_empty_page(self):
        page1 = table_response(value={"value": [entity("one", {"pending": True}, 'W/"page-one"')]},
                               headers={"x-ms-continuation-NextPartitionKey": "partition", "x-ms-continuation-NextRowKey": "row1"})
        page2 = table_response(value={"value": []}, headers={"x-ms-continuation-NextPartitionKey": "partition", "x-ms-continuation-NextRowKey": "row2"})
        page3 = table_response(value={"value": [entity("two", {"pending": True}, 'W/"page-three"'), entity("three", {"pending": False})]})
        store, transport = self.tables([page1, page2, page3])
        rows = tuple(store.scan("Source", {"pending": True}))
        self.assertEqual([row.version for row in rows], ['W/"page-one"', 'W/"page-three"'])
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual(parse_qs(urlsplit(transport.requests[1].url).query)["NextRowKey"], ["row1"])
        self.assertEqual(parse_qs(urlsplit(transport.requests[2].url).query)["NextRowKey"], ["row2"])
        self.assertTrue(all(request.headers["x-ms-version"] == "2020-12-06" for request in transport.requests))

    def test_table_query_missing_service_etag_and_unknown_errors_fail_closed(self):
        store, transport = self.tables([table_response(value={"value": [entity(etag=None)]}), table_error(500, "InternalError")])
        with self.assertRaises(self.contracts.Conflict):
            tuple(store.scan("Source", {}))
        with self.assertRaises(HttpResponseError):
            store.insert("Source", "identity", {})
        self.assertEqual(len(transport.requests), 2)

    def test_attempt_rows_use_only_attempts_table(self):
        store, transport = self.tables([response(204), response(204), response(204)])
        for kind in ("Attempt", "TransportAttempt", "Failure"):
            store.insert(kind, "key", {"kind": kind})
        self.assertTrue(all("/Attempts" in request.url for request in transport.requests))
        self.assertTrue(all(request.method == "POST" for request in transport.requests))

    def test_lease_acquire_renew_and_release_use_service_id_and_pinned_version(self):
        service, transport = self.blobs([response(201), response(201, headers={"x-ms-lease-id": "actual-server-lease"}),
                                        response(headers={"x-ms-lease-id": "actual-server-lease", "Date": "Tue, 06 Oct 2026 00:00:20 GMT"}), response()])
        clock = FixtureClock()
        leases = self.azure.AzureLeaseStore(service, clock=clock)
        handle = leases.acquire("owner", 60)
        self.assertEqual(handle.lease_id, "actual-server-lease")
        self.assertEqual(handle.observed_until, clock.now() + timedelta(seconds=58))
        clock.advance(20)
        renewed = leases.renew(handle)
        self.assertEqual(renewed.lease_id, "actual-server-lease")
        self.assertEqual(renewed.observed_until, clock.now() + timedelta(seconds=58))
        leases.release(renewed)
        self.assertTrue(all(request.headers["x-ms-version"] == "2026-04-06" for request in transport.requests))
        self.assertTrue(all("/locks/sec-owner-lowell-mason/sentinel.json" in request.url for request in transport.requests))
        self.assertEqual(transport.requests[1].headers["x-ms-lease-action"], "acquire")
        for request in transport.requests[2:]:
            self.assertEqual(request.headers["x-ms-lease-id"], "actual-server-lease")
        self.assertFalse(transport.responses)

    def test_lease_owned_check_rewrites_same_journal_with_exact_etag_and_actual_id(self):
        journal = b'{"epoch":7,"not_before":"2026-10-06T00:00:30Z"}'
        service, transport = self.blobs([response(etag='"sentinel-etag"'), response(etag='"sentinel-etag"', body=journal), response(201)])
        clock = FixtureClock()
        leases = self.azure.AzureLeaseStore(service, clock=clock)
        handle = self.contracts.LeaseHandle("owner", "actual-server-lease", clock.now() + timedelta(seconds=58))
        leases.assert_owned(handle)
        request = transport.requests[-1]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(request.headers["x-ms-lease-id"], handle.lease_id)
        self.assertEqual(request.headers["If-Match"], '"sentinel-etag"')
        self.assertNotIn("If-None-Match", request.headers)
        self.assertEqual(request.body, journal)

    def test_lease_conflict_loss_expiry_and_unbounded_clock_fail_closed(self):
        service, transport = self.blobs([response(201), blob_error(409, "LeaseAlreadyPresent")])
        clock = FixtureClock()
        with self.assertRaises(self.contracts.Conflict):
            self.azure.AzureLeaseStore(service, clock=clock).acquire("owner", 60)
        service, transport = self.blobs([blob_error(412, "LeaseIdMismatchWithLeaseOperation")])
        leases = self.azure.AzureLeaseStore(service, clock=clock)
        handle = self.contracts.LeaseHandle("owner", "old-server-lease", clock.now() + timedelta(seconds=58))
        with self.assertRaises(self.contracts.OwnershipLost):
            leases.renew(handle)
        clock.advance(60)
        with self.assertRaises(self.contracts.OwnershipLost):
            leases.assert_owned(handle)
        self.assertEqual(len(transport.requests), 1)
        for headers in ({"Date": ""}, {"Date": "Tue, 06 Oct 2026 00:00:20 GMT"}):
            with self.subTest(headers=headers):
                service, transport = self.blobs([response(201), response(201, headers={**headers, "x-ms-lease-id": "real-id"})])
                with self.assertRaises(self.contracts.ClockUncertain):
                    try:
                        self.azure.AzureLeaseStore(service, clock=FixtureClock()).acquire("owner", 60)
                    except DeserializationError as error:
                        self.fail(f"Raw server Date must be rejected as ClockUncertain before SDK deserialization: {error}")

    def test_factory_conditions_fixed_registry_before_authority_clients(self):
        settings = fixture_settings(storage={"backend": "azure", "root": None, "account_name": "secedgardevb8617",
                                             "blob_endpoint": BLOB_ENDPOINT, "table_endpoint": TABLE_ENDPOINT,
                                             "raw_container": "raw", "workset_container": "worksets",
                                             "quarantine_container": "quarantine", "lock_container": "locks",
                                             "lock_blob": "sec-owner-lowell-mason/sentinel.json",
                                             "binding_registry_blob": "sec-owner-lowell-mason/binding.json"},
                                    etl={"parser_version": "sec-envelope-v1"},
                                    worker={"image_digest": "sha256:" + "1" * 64, "provenance": "configured-image"})
        service, transport = self.blobs([response(201)])
        with patch.object(self.azure, "ManagedIdentityCredential") as credential, patch.object(self.azure, "BlobServiceClient", return_value=service) as blob_factory, patch.object(self.azure, "TableServiceClient") as table_factory:
            tables = table_factory.return_value
            source = tables.get_table_client.return_value
            source.url = TABLE_ENDPOINT
            tables.get_table_client.side_effect = lambda name: self._factory_table(name)
            state, objects, leases = self.azure.open_azure_stores(settings)
            credential.assert_called_once_with()
            self.assertEqual(blob_factory.call_args.kwargs["api_version"], "2026-04-06")
            self.assertEqual(table_factory.call_args.kwargs["api_version"], "2020-12-06")
            self.assertEqual([call.args[0] for call in tables.get_table_client.call_args_list],
                             ["SourceState", "Attempts", "ActivePointers"])
            self.assertEqual(state.active_client.table_name, "ActivePointers")
            for factory in (blob_factory, table_factory):
                self.assertEqual({key: factory.call_args.kwargs[key] for key in RETRY}, RETRY)
        request = transport.requests[0]
        self.assertIn("/locks/sec-owner-lowell-mason/binding.json", request.url)
        self.assertEqual(request.headers["If-None-Match"], "*")
        registry = json.loads(request.body)
        self.assertEqual(registry["namespace"], "sec-owner-lowell-mason")
        self.assertEqual(registry["account"], "secedgardevb8617")
        different = json.dumps({"namespace": "other"}).encode()
        service, transport = self.blobs([blob_error(409, "BlobAlreadyExists"), response(body=different)])
        with patch.object(self.azure, "ManagedIdentityCredential"), patch.object(self.azure, "BlobServiceClient", return_value=service), patch.object(self.azure, "TableServiceClient") as table_factory:
            with self.assertRaises(self.contracts.Conflict):
                self.azure.open_azure_stores(settings)
            table_factory.assert_not_called()

    def _factory_table(self, name):
        from unittest.mock import Mock
        return Mock(url=TABLE_ENDPOINT, table_name=name)

    def test_lease_observation_rejects_clock_jump_nonfinite_and_excess_latency(self):
        for fault in ("wall_jump", "nonfinite", "slow"):
            with self.subTest(fault=fault):
                service, transport = self.blobs([response(201), response(201, headers={"x-ms-lease-id": "actual-server-lease"})])
                clock = FixtureClock()
                send = transport.send
                def advance_clock(request, **kwargs):
                    if request.headers.get("x-ms-lease-action") == "acquire":
                        if fault == "wall_jump":
                            clock.instant += timedelta(seconds=20)
                        elif fault == "nonfinite":
                            clock.elapsed = float("nan")
                        else:
                            clock.advance(3)
                    return send(request, **kwargs)
                transport.send = advance_clock
                with self.assertRaises(self.contracts.ClockUncertain):
                    self.azure.AzureLeaseStore(service, clock=clock).acquire("owner", 60)
