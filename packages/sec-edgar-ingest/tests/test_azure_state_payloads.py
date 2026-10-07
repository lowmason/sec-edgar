"""Size and recovery contracts through real pinned SDKs, with offline service limits."""
import copy
import json
import re
import unittest
from dataclasses import replace
from datetime import date
from unittest.mock import patch
from urllib.parse import parse_qs, unquote, urlsplit

from azure.core.credentials import AzureSasCredential
from azure.core.exceptions import HttpResponseError
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient

from support import fixture_context, fixture_settings
from test_azure_contracts import (BLOB_ENDPOINT, TABLE_ENDPOINT, RETRY, ScriptedTransport,
                                  ScriptedResponse, response, table_response, table_error, blob_error)


class LimitedStorageTransport(ScriptedTransport):
    """Only these offline Blob/Table operations exist; all writes enforce Table limits."""
    def __init__(self):
        super().__init__(())
        self.rows = {}
        self.blobs = {}
        self.revision = 0
        self.fail_table_write = False
        self.truncate_blob_write = False

    def send(self, request, **kwargs):
        self.requests.append(request)
        parsed = urlsplit(request.url)
        path = unquote(parsed.path)
        body = request.body
        if hasattr(body, "read"):
            body = body.read()
        if parsed.netloc == urlsplit(BLOB_ENDPOINT).netloc:
            if request.method == "PUT":
                if path in self.blobs:
                    result = blob_error(409, "BlobAlreadyExists")
                else:
                    self.blobs[path] = body[:-1] if self.truncate_blob_write else body
                    self.truncate_blob_write = False
                    result = response(201)
            elif request.method == "GET":
                if path not in self.blobs:
                    result = blob_error(404, "BlobNotFound")
                else:
                    saved = self.blobs[path]
                    result = response(206, body=saved, headers={"Content-Range": f"bytes 0-{len(saved)-1}/{len(saved)}"})
            else:
                raise AssertionError(f"unsupported offline Blob operation: {request.method}")
        elif parsed.netloc == urlsplit(TABLE_ENDPOINT).netloc:
            table = path.lstrip("/").split("(", 1)[0]
            if request.method in ("POST", "PUT"):
                value = json.loads(body)
                # Edm.String is UTF-16, independent of HTTP JSON wire encoding.
                strings = {name: item for name, item in value.items() if isinstance(item, str)}
                if any(len(item.encode("utf-16-le")) > 65536 for item in strings.values()):
                    result = table_error(400, "PropertyValueTooLarge")
                elif len(value) + 1 > 255 or sum(len(item.encode("utf-16-le")) for item in strings.values()) + 1024 > 1048576:
                    result = table_error(400, "EntityTooLarge")
                elif any(len(value[name]) > 1024 for name in ("PartitionKey", "RowKey")):
                    result = table_error(400, "KeyValueTooLarge")
                else:
                    key = (table, value["PartitionKey"], value["RowKey"])
                    old = self.rows.get(key)
                    if self.fail_table_write:
                        self.fail_table_write = False
                        result = table_error(500, "InternalError")
                    elif request.method == "POST" and old is not None:
                        result = table_error(409, "EntityAlreadyExists")
                    elif request.method == "PUT" and (old is None or old[1] != request.headers["If-Match"]):
                        result = table_error(412, "UpdateConditionNotSatisfied")
                    else:
                        self.revision += 1
                        etag = f'W/"service-{self.revision}"'
                        self.rows[key] = (copy.deepcopy(value), etag)
                        result = response(204, etag=etag)
            elif request.method == "GET":
                match = re.search(r"PartitionKey='([^']*)',RowKey='([^']*)'", path)
                if match:
                    saved = self.rows.get((table, *match.groups()))
                    result = table_response(value={**saved[0], "odata.etag": saved[1]}, etag=saved[1]) if saved else table_error(404, "ResourceNotFound")
                else:
                    partition = parse_qs(parsed.query)["$filter"][0].split("'", 2)[1]
                    values = [{**value, "odata.etag": etag} for (name, kind, _), (value, etag) in self.rows.items()
                              if name == table and kind == partition]
                    result = table_response(value={"value": values})
            else:
                raise AssertionError(f"unsupported offline Table operation: {request.method}")
        else:
            raise AssertionError(f"unapproved offline endpoint: {request.url}")
        status, headers, saved_body = result
        return ScriptedResponse(request, status, headers, saved_body)


class AzureStatePayloadTests(unittest.TestCase):
    def setUp(self):
        import sec_edgar_ingest.storage.azure as azure
        import sec_edgar_ingest.storage.contracts as contracts
        self.azure, self.contracts = azure, contracts
        self.transport = LimitedStorageTransport()
        self.settings = fixture_settings(storage={
            "backend": "azure", "root": None, "account_name": "secedgardevb8617",
            "blob_endpoint": BLOB_ENDPOINT, "table_endpoint": TABLE_ENDPOINT,
            "raw_container": "raw", "workset_container": "worksets",
            "quarantine_container": "quarantine", "lock_container": "locks",
            "lock_blob": "sec-owner-lowell-mason/sentinel.json",
            "binding_registry_blob": "sec-owner-lowell-mason/binding.json"},
            etl={"parser_version": "sec-envelope-v1"},
            worker={"image_digest": "sha256:" + "1" * 64, "provenance": "configured-image"})

    def stores(self):
        blobs = BlobServiceClient(BLOB_ENDPOINT, api_version="2026-04-06", transport=self.transport, **RETRY)
        tables = TableServiceClient(TABLE_ENDPOINT, credential=AzureSasCredential("sv=offline&sig=synthetic"),
                                    api_version="2020-12-06", transport=self.transport, **RETRY)
        self.addCleanup(blobs.close)
        self.addCleanup(tables.close)
        with patch.object(self.azure, "ManagedIdentityCredential"), patch.object(self.azure, "BlobServiceClient", return_value=blobs), patch.object(self.azure, "TableServiceClient", return_value=tables):
            state, objects, _ = self.azure.open_azure_stores(self.settings)
        return state, objects

    def register_intended_history(self, store):
        from sec_edgar_ingest.config import pin_context
        from sec_edgar_ingest.discovery import _inventory
        from sec_edgar_ingest.state import AcquisitionState
        settings = fixture_settings(backfill={"start_quarter": "2010Q1", "end_quarter": "open"})
        context = replace(fixture_context(command="discover"), config_sha256=settings.config_sha256, effective_config={})
        context, end = pin_context(settings, context, date(2026, 10, 6))
        state = AcquisitionState(store)
        units, overlap = _inventory(settings, state, "quarterly", date(2026, 10, 6), end)
        self.assertEqual((len(units), end), (86, "2026Q4"))
        frozen = {"context": context.to_mapping(), "mode": "quarterly", "acquisition_mode": "reuse_accepted",
                  "units": list(units), "today": "2026-10-06", "overlap_from": overlap.isoformat()}
        state.begin_discovery("intended-history", frozen, context, "quarterly", "reuse_accepted")
        return state

    def test_intended_history_registration_round_trips_and_replaces_with_whole_record_cas(self):
        store, _ = self.stores()
        try:
            state = self.register_intended_history(store)
        except HttpResponseError as error:
            self.fail(f"accepted intended-history registration exceeds the offline Table limit: {error}")
        boundary = store.get("DiscoveryBoundary", "daily")
        self.assertEqual(len(boundary.value["gaps"]), 86)
        self.assertGreater(len(self.azure.payload_bytes(boundary.value).decode().encode("utf-16-le")), 65536)
        reopened, _ = self.stores()
        self.assertEqual(reopened.get("DiscoveryBoundary", "daily"), boundary)
        self.assertEqual(tuple(reopened.scan("DiscoveryBoundary", {"day": None})), (boundary,))
        self.assertEqual(len(state.failed_directories()), 86)
        changed = boundary.to_mapping()["value"]
        changed["gaps"].pop(next(iter(changed["gaps"])))
        winner = reopened.replace("DiscoveryBoundary", "daily", changed, boundary.version)
        self.assertEqual(winner.to_mapping()["value"], changed)
        self.assertNotEqual(winner.version, boundary.version)
        with self.assertRaises(self.contracts.Conflict):
            store.replace("DiscoveryBoundary", "daily", boundary.to_mapping()["value"], boundary.version)
        self.assertEqual(store.get("DiscoveryBoundary", "daily"), winner)
        with self.assertRaises(self.contracts.AlreadyExists):
            store.insert("DiscoveryBoundary", "daily", boundary.to_mapping()["value"])
        self.assertEqual(store.get("DiscoveryBoundary", "daily"), winner)

    def test_large_values_above_entity_limit_round_trip_without_splitting_table_updates(self):
        store, _ = self.stores()
        value = {"text": "😀" * 300000, "pending": True}
        self.assertGreater(len(self.azure.payload_bytes(value)), 1048576)
        try:
            written = store.insert("DirectoryProgress", "large", value)
        except HttpResponseError as error:
            self.fail(f"large logical record must use verified immutable content: {error}")
        reopened, _ = self.stores()
        self.assertEqual(reopened.get("DirectoryProgress", "large"), written)
        self.assertEqual(tuple(reopened.scan("DirectoryProgress", {"pending": True})), (written,))
        writes = [request for request in self.transport.requests if request.method in ("POST", "PUT")
                  and urlsplit(request.url).netloc == urlsplit(TABLE_ENDPOINT).netloc]
        self.assertEqual(len(writes), 1)
        emitted = json.loads(writes[0].body)
        self.assertNotIn("Payload", emitted)
        self.assertLess(len(json.dumps(emitted).encode()), 65536)

    def test_inline_rows_keep_original_payload_and_replace_both_formats(self):
        store, _ = self.stores()
        small = {"nested": {"a": [1, "é"]}}
        inline = store.insert("Source", "compatible", small)
        saved = self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", "compatible")][0]
        self.assertEqual({name: item for name, item in saved.items() if "@" not in name}, {"PartitionKey": "sec-owner-lowell-mason:Source", "RowKey": "compatible",
                                 "StableKey": "compatible", "Payload": self.azure.payload_bytes(small).decode()})
        self.assertEqual(store.get("Source", "compatible"), inline)
        large = {"text": "x" * 40000}
        try:
            overflow = store.replace("Source", "compatible", large, inline.version)
        except HttpResponseError as error:
            self.fail(f"inline record must conditionally transition to complete large value: {error}")
        self.assertEqual(store.get("Source", "compatible"), overflow)
        restored = store.replace("Source", "compatible", small, overflow.version)
        self.assertEqual(store.get("Source", "compatible"), restored)
        self.assertEqual(self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", "compatible")][0], saved)

    def test_missing_corrupt_and_wrong_identity_large_content_is_refused(self):
        store, _ = self.stores()
        try:
            row = store.insert("Source", "large", {"text": "x" * 40000})
        except HttpResponseError as error:
            self.fail(f"large record cannot reach corruption checks: {error}")
        path = next(path for path in self.transport.blobs if path.startswith("/worksets/state/"))
        original = self.transport.blobs.pop(path)
        with self.assertRaises(self.contracts.Conflict):
            store.get("Source", "large")
        self.transport.blobs[path] = original[:-1]
        with self.assertRaises(self.contracts.Conflict):
            tuple(store.scan("Source", {}))
        self.transport.blobs[path] = original
        self.assertEqual(store.get("Source", "large"), row)
        saved, etag = self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", "large")]
        copied = {**saved, "RowKey": "other", "StableKey": "other"}
        self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", "other")] = (copied, etag)
        with self.assertRaises(self.contracts.Conflict):
            store.get("Source", "other")

    def test_partial_blob_never_publishes_table_and_failed_table_candidate_retries(self):
        store, _ = self.stores()
        value = {"text": "x" * 40000}
        self.transport.truncate_blob_write = True
        try:
            with self.assertRaises(self.contracts.Conflict):
                store.insert("Source", "partial", value)
        except HttpResponseError as error:
            self.fail(f"partial large content must be verified before Table publish: {error}")
        self.assertIsNone(store.get("Source", "partial"))
        path = next(path for path in self.transport.blobs if path.startswith("/worksets/state/"))
        corrupt = self.transport.blobs[path]
        with self.assertRaises(self.contracts.Conflict):
            store.insert("Source", "partial", value)
        self.assertEqual(self.transport.blobs[path], corrupt)
        self.assertIsNone(store.get("Source", "partial"))
        self.transport.fail_table_write = True
        with self.assertRaises(HttpResponseError) as caught:
            store.insert("Source", "retry", value)
        self.assertEqual(caught.exception.status_code, 500)
        self.assertIsNone(store.get("Source", "retry"))
        before = copy.deepcopy(self.transport.blobs)
        row = store.insert("Source", "retry", value)
        self.assertEqual(store.get("Source", "retry"), row)
        self.assertEqual(self.transport.blobs, before)

    def test_oversized_stable_identity_is_refused_before_any_storage_write(self):
        store, _ = self.stores()
        before = len(self.transport.requests)
        try:
            with self.assertRaises(ValueError):
                store.insert("Source", "😀" * 40000, {})
        except HttpResponseError as error:
            self.fail(f"oversized identity reached Table instead of failing validation: {error}")
        self.assertEqual(len(self.transport.requests), before)

    def test_content_descriptor_rejects_invalid_format_digest_length_and_noncanonical_envelope(self):
        store, _ = self.stores()
        store.insert("Source", "large", {"text": "x" * 40000})
        key = ("SourceState", "sec-owner-lowell-mason:Source", "large")
        original, etag = self.transport.rows[key]
        for changes in ({"PayloadFormat": "latest"}, {"PayloadSha256": "z" * 64},
                        {"PayloadByteCount": original["PayloadByteCount"] + 1}, {"Payload": "{}"}):
            with self.subTest(changes=changes):
                self.transport.rows[key] = ({**original, **changes}, etag)
                with self.assertRaises(self.contracts.Conflict):
                    store.get("Source", "large")
        import hashlib
        path = next(path for path in self.transport.blobs if path.startswith("/worksets/state/"))
        envelope = json.loads(self.transport.blobs[path])
        for name, edit in (("noncanonical", lambda value: None),
                           ("namespace/kind", lambda value: value.update(partition="other:Source")),
                           ("stable key", lambda value: value.update(key="other")),
                           ("unknown content field", lambda value: value.update(latest=True))):
            with self.subTest(name=name):
                changed = copy.deepcopy(envelope)
                edit(changed)
                body = json.dumps(changed).encode() if name == "noncanonical" else self.azure.payload_bytes(changed)
                digest = hashlib.sha256(body).hexdigest()
                self.transport.blobs[f"/worksets/state/sha256={digest}.json"] = body
                self.transport.rows[key] = ({**original, "PayloadSha256": digest, "PayloadByteCount": len(body)}, etag)
                with self.assertRaises(self.contracts.Conflict):
                    store.get("Source", "large")

    def test_utf16_threshold_keeps_safe_inline_and_overflows_one_more_character(self):
        store, _ = self.stores()
        overhead = len(self.azure.payload_bytes({"text": ""}).decode().encode("utf-16-le"))
        for character in ("x", "😀"):
            with self.subTest(character=character):
                width = len(character.encode("utf-16-le"))
                count = (65536 - overhead) // width
                safe = {"text": character * count}
                large = {"text": character * (count + 1)}
                inline = store.insert("Source", character, safe)
                saved = self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", self.azure._row_key(character))][0]
                self.assertIn("Payload", saved)
                bigger = store.replace("Source", character, large, inline.version)
                self.assertEqual(store.get("Source", character), bigger)
                saved = self.transport.rows[("SourceState", "sec-owner-lowell-mason:Source", self.azure._row_key(character))][0]
                self.assertNotIn("Payload", saved)
