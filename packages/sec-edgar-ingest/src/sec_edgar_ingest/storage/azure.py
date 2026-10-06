"""Pinned Blob/Table SDK adapters using conditional Storage operations only."""
from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from azure.core import MatchConditions
from azure.core.exceptions import HttpResponseError, ResourceExistsError, ResourceModifiedError, ResourceNotFoundError
from azure.data.tables import TableClient, TableServiceClient, UpdateMode
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobLeaseClient, BlobServiceClient

from ..config import ACCOUNT_NAME, LOCK_BLOB, Settings
from ..models import Versioned, parse_json, require_hash, require_number, require_text, require_utc, safe_relative_path
from .contracts import (AlreadyExists, BoundaryObserver, ClockUncertain, Conflict, FILE_CHUNK_BYTES,
                        LeaseHandle, OwnershipLost, TimeBounds, REGISTRY_PATH, deployment_binding, exact_version,
                        identity, observe, payload_bytes, table_for, validate_raw_address)

RETRY_OPTIONS = dict(retry_total=0, retry_connect=0, retry_read=0, retry_status=0)
STORAGE_CONNECTION_TIMEOUT_SECONDS = 5
STORAGE_READ_TIMEOUT_SECONDS = 10
CONTAINERS = frozenset({"raw", "worksets", "quarantine", "locks"})


def _check_endpoint(url: str, kind: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != f"{ACCOUNT_NAME}.{kind}.core.windows.net"
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment):
        raise ValueError("Storage client must use the fixed credential-free account endpoint")


def _row_key(key: str) -> str:
    require_text(key, "key")
    return quote(key, safe="-._~")


def _etag(version: str | None) -> str:
    try:
        exact_version(version)
    except ValueError as error:
        raise Conflict("Storage response omitted an actual opaque ETag") from error
    return version


class AzureStateStore:
    def __init__(self, source_client: TableClient, attempt_client: TableClient, *, observer: BoundaryObserver | None = None):
        for client, name in ((source_client, "SourceState"), (attempt_client, "Attempts")):
            _check_endpoint(client.url, "table")
            if client.table_name != name:
                raise ValueError("Table client must use the accepted table binding")
        self.source_client = source_client
        self.attempt_client = attempt_client
        self.observer = observer

    def close(self) -> None:
        self.source_client.close()
        self.attempt_client.close()

    def _client(self, kind: str) -> TableClient:
        return self.attempt_client if table_for(kind) == "Attempts" else self.source_client

    def _entity(self, kind: str, key: str, value: dict[str, object]) -> dict[str, str]:
        partition, key = identity(kind, key)
        return {"PartitionKey": partition, "RowKey": _row_key(key), "StableKey": key,
                "Payload": payload_bytes(value).decode("utf-8")}

    def _value(self, entity, partition: str, key: str, version: str) -> Versioned:
        if entity.get("PartitionKey") != partition or entity.get("RowKey") != _row_key(key) or entity.get("StableKey") != key:
            raise Conflict("Table entity disagrees with its stable identity")
        value = parse_json(entity.get("Payload"))
        if not isinstance(value, dict):
            raise Conflict("Table payload must be a JSON object")
        return Versioned(value, _etag(version))

    def get(self, kind: str, key: str) -> Versioned | None:
        partition, key = identity(kind, key)
        observed = {}
        def capture(response):
            observed["etag"] = response.http_response.headers.get("ETag")
        try:
            entity = self._client(kind).get_entity(partition_key=partition, row_key=_row_key(key), raw_response_hook=capture)
        except ResourceNotFoundError as error:
            if error.status_code == 404:
                return None
            raise
        return self._value(entity, partition, key, observed.get("etag"))

    def insert(self, kind: str, key: str, value: dict[str, object]) -> Versioned:
        entity = self._entity(kind, key, value)
        observed = {}
        def capture(response):
            observed["etag"] = response.http_response.headers.get("ETag")
        try:
            self._client(kind).create_entity(entity=entity, raw_response_hook=capture)
        except ResourceExistsError as error:
            if error.status_code == 409:
                raise AlreadyExists("Table state identity already exists") from error
            raise
        result = Versioned(parse_json(entity["Payload"]), _etag(observed.get("etag")))
        observe(self.observer, "state.after_insert")
        return result

    def replace(self, kind: str, key: str, value: dict[str, object], version: str) -> Versioned:
        exact_version(version)
        entity = self._entity(kind, key, value)
        observed = {}
        def capture(response):
            observed["etag"] = response.http_response.headers.get("ETag")
        try:
            self._client(kind).update_entity(entity=entity, mode=UpdateMode.REPLACE, etag=version,
                                            match_condition=MatchConditions.IfNotModified, raw_response_hook=capture)
        except (ResourceModifiedError, ResourceNotFoundError) as error:
            if error.status_code in (404, 412):
                raise Conflict("Table row absent or ETag changed") from error
            raise
        result = Versioned(parse_json(entity["Payload"]), _etag(observed.get("etag")))
        observe(self.observer, "state.after_replace")
        return result

    def scan(self, kind: str, filters: dict[str, object]) -> Iterator[Versioned]:
        partition, _ = identity(kind, "scan")
        detached_filters = parse_json(payload_bytes(filters))
        versions = {}
        def capture(response):
            versions.clear()
            body = parse_json(response.http_response.body())
            for entity in body.get("value", []):
                versions[entity["RowKey"]] = entity.get("odata.etag")
        escaped_partition = partition.replace("'", "''")
        pages = self._client(kind).query_entities(query_filter=f"PartitionKey eq '{escaped_partition}'",
                                                results_per_page=128, raw_response_hook=capture).by_page()
        for page in pages:
            for entity in page:
                key = entity.get("StableKey")
                version = versions.get(entity.get("RowKey"))
                row = self._value(entity, partition, key, version)
                value = row.to_mapping()["value"]
                if all(name in value and value[name] == expected for name, expected in detached_filters.items()):
                    yield row


class AzureObjectStore:
    def __init__(self, service: BlobServiceClient, *, observer: BoundaryObserver | None = None):
        _check_endpoint(service.url, "blob")
        self.service = service
        self.observer = observer

    def close(self) -> None:
        self.service.close()

    def _blob(self, path: str):
        segments = safe_relative_path(path, "object path").split("/", 1)
        if len(segments) != 2 or segments[0] not in CONTAINERS:
            raise ValueError("object path must name an accepted Blob container")
        return self.service.get_blob_client(container=segments[0], blob=segments[1])

    def _upload(self, path: str, stream, sha256: str, byte_count: int) -> str:
        blob = self._blob(path)
        observe(self.observer, "object.before_upload")
        try:
            blob.upload_blob(stream, length=byte_count, overwrite=False, match_condition=MatchConditions.IfMissing)
        except (ResourceExistsError, ResourceModifiedError) as error:
            if error.status_code not in (409, 412):
                raise
            self.verify(path, sha256, byte_count)
        observe(self.observer, "object.after_upload")
        return path

    def put_once(self, path: str, body: bytes) -> str:
        if not isinstance(body, bytes):
            raise ValueError("immutable object body must be bytes")
        return self._upload(path, body, hashlib.sha256(body).hexdigest(), len(body))

    def read(self, path: str) -> bytes:
        try:
            return self._blob(path).download_blob(max_concurrency=1).readall()
        except ResourceNotFoundError as error:
            if error.status_code == 404:
                raise FileNotFoundError(path) from error
            raise

    def stage(self, path: str, body: Path) -> str:
        digest, byte_count = hashlib.sha256(), 0
        with Path(body).open("rb") as stream:
            while chunk := stream.read(FILE_CHUNK_BYTES):
                digest.update(chunk)
                byte_count += len(chunk)
            stream.seek(0)
            return self._upload(path, stream, digest.hexdigest(), byte_count)

    def verify(self, path: str, sha256: str, byte_count: int) -> None:
        require_hash(sha256, "sha256")
        require_number(byte_count, "byte_count", integer=True)
        digest, actual_bytes = hashlib.sha256(), 0
        try:
            for chunk in self._blob(path).download_blob(max_concurrency=1).chunks():
                digest.update(chunk)
                actual_bytes += len(chunk)
        except ResourceNotFoundError as error:
            if error.status_code == 404:
                raise FileNotFoundError(path) from error
            raise
        if digest.hexdigest() != sha256 or actual_bytes != byte_count:
            raise Conflict("immutable Blob differs from expected hash or length")

    def promote(self, temporary_ref: str, raw_path: str, sha256: str, byte_count: int) -> str:
        validate_raw_address(raw_path, sha256, byte_count)
        self.verify(temporary_ref, sha256, byte_count)
        observe(self.observer, "object.before_promote")
        reference = self.put_once(raw_path, self.read(temporary_ref))
        self.verify(reference, sha256, byte_count)
        observe(self.observer, "object.after_promote")
        return reference


class _WallClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def monotonic(self) -> float:
        return time.monotonic()


class AzureLeaseStore:
    def __init__(self, service: BlobServiceClient, *, lease_seconds: int = 60, uncertainty_seconds: float = 2,
                 clock=None, observer: BoundaryObserver | None = None):
        _check_endpoint(service.url, "blob")
        require_number(lease_seconds, "lease_seconds", integer=True)
        require_number(uncertainty_seconds, "uncertainty_seconds")
        if not 15 <= lease_seconds <= 60 or uncertainty_seconds > 2:
            raise ValueError("finite Azure lease/clock bounds exceed the accepted policy")
        self.blob = service.get_blob_client(container="locks", blob=LOCK_BLOB)
        self.lease_seconds = lease_seconds
        self.uncertainty_seconds = uncertainty_seconds
        self.clock = clock or _WallClock()
        self.observer = observer

    def _start(self):
        before = self.clock.now()
        require_utc(before, "clock.now")
        return before, self.clock.monotonic(), {}

    def _capture(self, observed):
        def capture(response):
            observed["date"] = response.http_response.headers.get("Date")
            observed["etag"] = response.http_response.headers.get("ETag")
            if response.http_response.status_code < 400:
                try:
                    server_date = parsedate_to_datetime(observed["date"] or "")
                    require_utc(server_date, "Storage Date")
                except (ValueError, TypeError, IndexError) as error:
                    raise ClockUncertain("Storage response has no usable server Date") from error
                observed["server_date"] = server_date
        return capture

    def _observation(self, before: datetime, mono: float, observed: dict) -> TimeBounds:
        after = self.clock.now()
        require_utc(after, "clock.now")
        elapsed = self.clock.monotonic() - mono
        try:
            server_date = observed.get("server_date")
            require_utc(server_date, "Storage Date")
        except (ValueError, TypeError, IndexError) as error:
            raise ClockUncertain("Storage response has no usable server Date") from error
        uncertainty = timedelta(seconds=self.uncertainty_seconds)
        if (not math.isfinite(elapsed) or elapsed < 0 or elapsed > self.uncertainty_seconds or after < before
                or abs((after - before).total_seconds() - elapsed) > self.uncertainty_seconds
                or server_date > after + uncertainty or server_date + timedelta(seconds=1) < before - uncertainty):
            raise ClockUncertain("Storage server observation exceeds the accepted uncertainty")
        # Date is rounded to whole seconds. The entire measured operation RTT bounds response transit.
        if 1 + elapsed > self.uncertainty_seconds:
            raise ClockUncertain("Storage Date precision plus RTT exceeds the accepted uncertainty")
        return TimeBounds(server_date, server_date + timedelta(seconds=1 + elapsed), self.clock.monotonic())

    def _bounded_until(self, before: datetime, mono: float, observed: dict) -> datetime:
        bounds = self._observation(before, mono, observed)
        return min(before, bounds.lower) + timedelta(seconds=self.lease_seconds - self.uncertainty_seconds)

    def _current(self, handle: LeaseHandle) -> None:
        require_utc(self.clock.now(), "clock.now")
        if self.clock.now() >= handle.observed_until:
            raise OwnershipLost("observed lease window has expired")

    def _ensure_sentinel(self) -> None:
        try:
            self.blob.upload_blob(b"{}", overwrite=False, match_condition=MatchConditions.IfMissing)
        except (ResourceExistsError, ResourceModifiedError) as error:
            if error.status_code not in (409, 412):
                raise

    def acquire(self, owner: str, seconds: int) -> LeaseHandle:
        require_text(owner, "owner")
        require_number(seconds, "lease seconds", integer=True)
        if seconds != self.lease_seconds:
            raise ValueError("lease duration must equal the one configured deployment duration")
        self._ensure_sentinel()
        before, mono, observed = self._start()
        lease = BlobLeaseClient(self.blob)
        try:
            lease.acquire(lease_duration=seconds, raw_response_hook=self._capture(observed))
        except HttpResponseError as error:
            if error.status_code in (409, 412):
                raise Conflict("fixed sentinel is already leased or changed") from error
            raise
        if not lease.id:
            raise OwnershipLost("Storage did not return an actual acquired lease ID")
        bounds = self._observation(before, mono, observed)
        until = min(before, bounds.lower) + timedelta(seconds=self.lease_seconds - self.uncertainty_seconds)
        observe(self.observer, "lease.after_acquire")
        return LeaseHandle(owner, lease.id, until, bounds.upper,
                           bounds.upper + timedelta(seconds=self.lease_seconds), bounds)

    def renew(self, handle: LeaseHandle) -> LeaseHandle:
        self._current(handle)
        before, mono, observed = self._start()
        lease = BlobLeaseClient(self.blob, lease_id=handle.lease_id)
        try:
            lease.renew(raw_response_hook=self._capture(observed))
        except HttpResponseError as error:
            if error.status_code in (404, 409, 412):
                raise OwnershipLost("fixed sentinel lease changed during renewal") from error
            raise
        if lease.id != handle.lease_id:
            raise OwnershipLost("Storage renewal did not confirm the actual lease ID")
        bounds = self._observation(before, mono, observed)
        until = min(before, bounds.lower) + timedelta(seconds=self.lease_seconds - self.uncertainty_seconds)
        observe(self.observer, "lease.after_renew")
        return LeaseHandle(handle.owner_id, lease.id, until, handle.acquired_upper,
                           bounds.upper + timedelta(seconds=self.lease_seconds), bounds)

    def release(self, handle: LeaseHandle) -> None:
        self._current(handle)
        try:
            BlobLeaseClient(self.blob, lease_id=handle.lease_id).release()
        except HttpResponseError as error:
            if error.status_code in (404, 409, 412):
                raise OwnershipLost("fixed sentinel lease changed during release") from error
            raise
        observe(self.observer, "lease.after_release")

    def observe_time(self, handle: LeaseHandle | None = None) -> TimeBounds:
        if handle is None:
            self._ensure_sentinel()
        else:
            self._current(handle)
        before, mono, observed = self._start()
        try:
            self.blob.get_blob_properties(lease=handle.lease_id if handle is not None else None,
                                          raw_response_hook=self._capture(observed))
        except HttpResponseError as error:
            if error.status_code in (404, 409, 412):
                raise OwnershipLost("sentinel clock observation failed ownership") from error
            raise
        return self._observation(before, mono, observed)

    def assert_owned(self, handle: LeaseHandle) -> None:
        self.read_journal(handle)

    def read_journal(self, handle: LeaseHandle) -> Versioned:
        self._current(handle)
        before, mono, observed = self._start()
        hook = self._capture(observed)
        try:
            properties = self.blob.get_blob_properties(lease=handle.lease_id, raw_response_hook=hook)
            version = _etag(properties.etag)
            body = self.blob.download_blob(lease=handle.lease_id, etag=version, match_condition=MatchConditions.IfNotModified,
                                           max_concurrency=1, raw_response_hook=hook).readall()
            # Reads alone do not prove Blob lease ownership. This exact rewrite fences the read.
            self.blob.upload_blob(body, overwrite=True, lease=handle.lease_id, etag=version,
                                  match_condition=MatchConditions.IfNotModified, raw_response_hook=hook)
        except HttpResponseError as error:
            if error.status_code in (404, 409, 412):
                raise OwnershipLost("fixed sentinel no longer recognizes the actual lease/version") from error
            raise
        self._observation(before, mono, observed)
        self._current(handle)
        value = parse_json(body)
        if not isinstance(value, dict):
            raise Conflict("sentinel journal must be a JSON object")
        observe(self.observer, "journal.after_read")
        return Versioned(value, _etag(observed.get("etag")))

    def write_journal(self, handle: LeaseHandle, value: dict[str, object], version: str) -> Versioned:
        exact_version(version)
        self._current(handle)
        body = payload_bytes(value)
        before, mono, observed = self._start()
        observe(self.observer, "journal.before_write")
        try:
            self.blob.upload_blob(body, overwrite=True, lease=handle.lease_id, etag=version,
                                  match_condition=MatchConditions.IfNotModified,
                                  raw_response_hook=self._capture(observed))
        except HttpResponseError as error:
            if error.status_code in (404, 409, 412):
                raise OwnershipLost("sentinel write lost the actual lease or exact version") from error
            raise
        self._observation(before, mono, observed)
        self._current(handle)
        observe(self.observer, "journal.after_write")
        return Versioned(parse_json(body), _etag(observed.get("etag")))


def open_azure_stores(settings: Settings, *, observer: BoundaryObserver | None = None):
    validated = Settings.from_mapping(settings.to_mapping())
    if validated.storage.backend != "azure":
        raise ValueError("Azure factory requires validated Azure settings")
    if not validated.coordination.lease_seconds.is_integer():
        raise ValueError("Azure finite lease duration must use whole seconds")
    credential = ManagedIdentityCredential()
    storage = validated.storage
    options = {**RETRY_OPTIONS, "connection_timeout": STORAGE_CONNECTION_TIMEOUT_SECONDS,
               "read_timeout": STORAGE_READ_TIMEOUT_SECONDS}
    blob_service = BlobServiceClient(account_url=storage.blob_endpoint, credential=credential,
                                    api_version=storage.blob_api_version, **options)
    objects = AzureObjectStore(blob_service, observer=observer)
    objects.put_once(REGISTRY_PATH, payload_bytes(deployment_binding(validated)))
    tables = TableServiceClient(endpoint=storage.table_endpoint, credential=credential,
                               api_version=storage.table_api_version, **options)
    state = AzureStateStore(tables.get_table_client(storage.source_table), tables.get_table_client(storage.attempt_table),
                            observer=observer)
    leases = AzureLeaseStore(blob_service, lease_seconds=int(validated.coordination.lease_seconds),
                             uncertainty_seconds=validated.coordination.clock_uncertainty_seconds, observer=observer)
    return state, objects, leases
