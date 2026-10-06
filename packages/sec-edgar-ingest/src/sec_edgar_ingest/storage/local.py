"""SQLite CAS and durable write-once files for offline acquisition fixtures."""
from __future__ import annotations

import errno
import hashlib
import io
import os
import sqlite3
import stat
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import LOCK_BLOB
from ..models import Versioned, parse_json, require_hash, require_number, require_text, require_utc, safe_relative_path
from .contracts import (AlreadyExists, BoundaryObserver, CAS_ATTEMPTS, Conflict, FILE_CHUNK_BYTES,
                        LeaseHandle, OwnershipLost, REGISTRY_PATH, SENTINEL_PATH, deployment_binding,
                        exact_version, identity, observe, payload_bytes, table_for, validate_raw_address)

DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW


class LocalObjectStore:
    def __init__(self, root: Path, *, observer: BoundaryObserver | None = None, binding=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.directory = self.root / "objects"
        self.directory.mkdir(exist_ok=True)
        if self.directory.is_symlink():
            raise ValueError("object root must not be a symlink")
        self.observer = observer
        self._write_once(REGISTRY_PATH, io.BytesIO(payload_bytes(binding or deployment_binding(root=self.root))), notify=False)

    @contextmanager
    def _parent(self, path: str, *, create: bool = False):
        segments = safe_relative_path(path, "object path").split("/")
        descriptor = os.open(self.directory, DIRECTORY_FLAGS)
        try:
            for segment in segments[:-1]:
                if create:
                    try:
                        os.mkdir(segment, dir_fd=descriptor)
                        os.fsync(descriptor)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(segment, DIRECTORY_FLAGS, dir_fd=descriptor)
                except OSError as error:
                    if error.errno in (errno.ENOTDIR, errno.ELOOP):
                        raise ValueError("object parents must be real directories") from error
                    raise
                os.close(descriptor)
                descriptor = child
            yield descriptor, segments[-1]
        finally:
            os.close(descriptor)

    @contextmanager
    def _open(self, path: str):
        with self._parent(path) as (parent, name):
            try:
                descriptor = os.open(name, FILE_FLAGS, dir_fd=parent)
            except OSError as error:
                if error.errno == errno.ELOOP:
                    raise ValueError("object must not be a symlink") from error
                raise
            with os.fdopen(descriptor, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("object must be a regular file")
                yield stream

    def _write_once(self, path: str, stream, *, notify: bool = True) -> str:
        with self._parent(path, create=True) as (parent, name):
            temporary = ".pending-" + uuid.uuid4().hex
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            digest, byte_count = hashlib.sha256(), 0
            try:
                with os.fdopen(descriptor, "wb") as target:
                    while chunk := stream.read(FILE_CHUNK_BYTES):
                        target.write(chunk)
                        digest.update(chunk)
                        byte_count += len(chunk)
                    target.flush()
                    os.fsync(target.fileno())
                if notify:
                    observe(self.observer, "object.after_fsync")
                    observe(self.observer, "object.before_link")
                try:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                except FileExistsError:
                    self.verify(path, digest.hexdigest(), byte_count)
                os.fsync(parent)
                if notify:
                    observe(self.observer, "object.after_link")
            finally:
                os.unlink(temporary, dir_fd=parent)
                os.fsync(parent)
        return path

    def put_once(self, path: str, body: bytes) -> str:
        if not isinstance(body, bytes):
            raise ValueError("immutable object body must be bytes")
        return self._write_once(path, io.BytesIO(body))

    def read(self, path: str) -> bytes:
        with self._open(path) as stream:
            return stream.read()

    def stage(self, path: str, body: Path) -> str:
        with Path(body).open("rb") as stream:
            return self._write_once(path, stream)

    def verify(self, path: str, sha256: str, byte_count: int) -> None:
        require_hash(sha256, "sha256")
        require_number(byte_count, "byte_count", integer=True)
        digest, actual_bytes = hashlib.sha256(), 0
        with self._open(path) as stream:
            while chunk := stream.read(FILE_CHUNK_BYTES):
                digest.update(chunk)
                actual_bytes += len(chunk)
        if digest.hexdigest() != sha256 or actual_bytes != byte_count:
            raise Conflict("immutable object differs from expected hash or length")

    def promote(self, temporary_ref: str, raw_path: str, sha256: str, byte_count: int) -> str:
        validate_raw_address(raw_path, sha256, byte_count)
        self.verify(temporary_ref, sha256, byte_count)
        observe(self.observer, "object.before_promote")
        with self._open(temporary_ref) as stream:
            reference = self._write_once(raw_path, stream)
        self.verify(reference, sha256, byte_count)
        observe(self.observer, "object.after_promote")
        return reference


class LocalStateStore:
    def __init__(self, root: Path, *, page_size: int = 128, observer: BoundaryObserver | None = None, binding=None):
        require_number(page_size, "page_size", positive=True, integer=True)
        self.root = Path(root).resolve()
        LocalObjectStore(self.root, binding=binding)
        self.database = self.root / "state.sqlite3"
        if self.database.is_symlink():
            raise ValueError("state database must not be a symlink")
        self.page_size = page_size
        self.observer = observer
        self._closed = False
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE IF NOT EXISTS records (table_name TEXT NOT NULL, partition TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, version TEXT NOT NULL, PRIMARY KEY(table_name, partition, key))")
            connection.commit()

    @contextmanager
    def _connection(self):
        if self._closed:
            raise ValueError("state client is closed")
        connection = sqlite3.connect(self.database, timeout=5)
        try:
            connection.execute("PRAGMA synchronous=FULL")
            yield connection
        finally:
            connection.close()

    def close(self) -> None:
        self._closed = True

    def get(self, kind: str, key: str) -> Versioned | None:
        partition, key = identity(kind, key)
        with self._connection() as connection:
            row = connection.execute("SELECT value, version FROM records WHERE table_name=? AND partition=? AND key=?", (table_for(kind), partition, key)).fetchone()
        return None if row is None else Versioned(parse_json(row[0]), row[1])

    def insert(self, kind: str, key: str, value: dict[str, object]) -> Versioned:
        partition, key = identity(kind, key)
        body, version = payload_bytes(value).decode("utf-8"), uuid.uuid4().hex
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)", (table_for(kind), partition, key, body, version))
                connection.commit()
        except sqlite3.IntegrityError as error:
            raise AlreadyExists("state identity already exists") from error
        observe(self.observer, "state.after_insert")
        return Versioned(parse_json(body), version)

    def replace(self, kind: str, key: str, value: dict[str, object], version: str) -> Versioned:
        exact_version(version)
        partition, key = identity(kind, key)
        body, next_version = payload_bytes(value).decode("utf-8"), uuid.uuid4().hex
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute("UPDATE records SET value=?, version=? WHERE table_name=? AND partition=? AND key=? AND version=?", (body, next_version, table_for(kind), partition, key, version)).rowcount
            if count != 1:
                connection.rollback()
                raise Conflict("state row absent or revision changed")
            connection.commit()
        observe(self.observer, "state.after_replace")
        return Versioned(parse_json(body), next_version)

    def scan(self, kind: str, filters: dict[str, object]) -> Iterator[Versioned]:
        partition, _ = identity(kind, "scan")
        detached_filters = parse_json(payload_bytes(filters))
        last_key = ""
        while True:
            with self._connection() as connection:
                rows = connection.execute("SELECT key, value, version FROM records WHERE table_name=? AND partition=? AND key>? ORDER BY key LIMIT ?", (table_for(kind), partition, last_key, self.page_size)).fetchall()
            if not rows:
                return
            for key, body, version in rows:
                value = parse_json(body)
                if all(name in value and value[name] == expected for name, expected in detached_filters.items()):
                    yield Versioned(value, version)
                last_key = key


class _WallClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class LocalLeaseStore:
    def __init__(self, root: Path, *, clock=None, observer: BoundaryObserver | None = None, binding=None):
        self.store = LocalStateStore(root, observer=observer, binding=binding)
        self.objects = LocalObjectStore(root, binding=binding)
        try:
            self.objects.read(SENTINEL_PATH)
        except FileNotFoundError:
            try:
                self.objects.put_once(SENTINEL_PATH, b"{}")
            except Conflict:
                self.objects.read(SENTINEL_PATH)
        self.clock = clock or _WallClock()

    def close(self) -> None:
        self.store.close()

    def acquire(self, owner: str, seconds: int) -> LeaseHandle:
        require_text(owner, "owner")
        require_number(seconds, "lease seconds", positive=True, integer=True)
        for _ in range(CAS_ATTEMPTS):
            now = self.clock.now()
            require_utc(now, "clock.now")
            current = self.store.get("_Lease", LOCK_BLOB)
            if current is not None and datetime.fromisoformat(current.value["expires_at"]) > now:
                raise Conflict("fixed sentinel is already leased")
            lease_id = str(uuid.uuid4())
            until = now + timedelta(seconds=seconds)
            value = {"owner_id": owner, "lease_id": lease_id, "seconds": seconds, "expires_at": until.isoformat()}
            try:
                if current is None:
                    self.store.insert("_Lease", LOCK_BLOB, value)
                else:
                    self.store.replace("_Lease", LOCK_BLOB, value, current.version)
                return LeaseHandle(owner, lease_id, until)
            except (AlreadyExists, Conflict):
                continue
        raise Conflict("lease acquisition exhausted conditional races")

    def _owned(self, handle: LeaseHandle) -> Versioned:
        now = self.clock.now()
        require_utc(now, "clock.now")
        row = self.store.get("_Lease", LOCK_BLOB)
        if (row is None or row.value["owner_id"] != handle.owner_id or row.value["lease_id"] != handle.lease_id
                or datetime.fromisoformat(row.value["expires_at"]) <= now):
            raise OwnershipLost("fixed sentinel lease is absent, expired, or replaced")
        return row

    def assert_owned(self, handle: LeaseHandle) -> None:
        self._owned(handle)

    def renew(self, handle: LeaseHandle) -> LeaseHandle:
        row = self._owned(handle)
        until = self.clock.now() + timedelta(seconds=row.value["seconds"])
        value = row.to_mapping()["value"]
        value["expires_at"] = until.isoformat()
        try:
            self.store.replace("_Lease", LOCK_BLOB, value, row.version)
        except Conflict as error:
            raise OwnershipLost("lease changed during renewal") from error
        return LeaseHandle(handle.owner_id, handle.lease_id, until)

    def release(self, handle: LeaseHandle) -> None:
        row = self._owned(handle)
        value = row.to_mapping()["value"]
        value["expires_at"] = self.clock.now().isoformat()
        try:
            self.store.replace("_Lease", LOCK_BLOB, value, row.version)
        except Conflict as error:
            raise OwnershipLost("lease changed during release") from error
