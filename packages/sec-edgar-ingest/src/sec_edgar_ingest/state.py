"""Durable source observations, accepted receipts, first pins and attempt audit."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .models import Binding, BodyReceipt, CommandResult, Error, Permit, RunContext, Snapshot, Source, Versioned, canonical_json, require_number, require_text, require_utc
from .storage.contracts import AlreadyExists, CAS_ATTEMPTS, Conflict, StateStore


def attempt_key(context: RunContext) -> str:
    return hashlib.sha256(canonical_json({name: getattr(context, name) for name in
        ("run_id", "execution_id", "command", "attempt_id", "image_digest")})).hexdigest()


class AcquisitionState:
    def __init__(self, store: StateStore, *, clock=None):
        self.store = store
        self.clock = clock
        self.active_context = None

    def _now(self) -> datetime:
        instant = self.clock.now() if self.clock is not None else datetime.now(timezone.utc)
        require_utc(instant, "clock.now")
        return instant

    def _update_source(self, source: Source, change) -> Versioned:
        for _ in range(CAS_ATTEMPTS):
            current = self.get_source(source.source_id)
            value = current.to_mapping()["value"] if current is not None else {
                "source": source.to_mapping(), "first_discovered_at": None, "last_discovered_at": None,
                "discovery_status": "unobserved", "acquisition_status": "pending", "needs_acquisition": True,
                "latest_downloaded_snapshot": None, "latest_received_at": None, "last_error": None,
            }
            if Source.from_mapping(value["source"]) != source:
                raise Conflict("source identity has conflicting metadata")
            change(value)
            try:
                if current is None:
                    return self.store.insert("Source", source.source_id, value)
                return self.store.replace("Source", source.source_id, value, current.version)
            except (AlreadyExists, Conflict):
                continue
        raise Conflict("source update exhausted conditional races")

    def observe(self, source: Source, at: datetime, discovery_status: str) -> None:
        require_utc(at, "discovery time")
        require_text(discovery_status, "discovery_status")
        def change(value):
            first = value["first_discovered_at"]
            last = value["last_discovered_at"]
            value["first_discovered_at"] = min(at, datetime.fromisoformat(first)).isoformat() if first else at.isoformat()
            if last is None or at >= datetime.fromisoformat(last):
                value["last_discovered_at"] = at.isoformat()
                value["discovery_status"] = discovery_status
        self._update_source(source, change)

    def get_source(self, source_id: str) -> Versioned | None:
        return self.store.get("Source", source_id)

    def pending_sources(self) -> tuple[Source, ...]:
        return tuple(Source.from_mapping(row.to_mapping()["value"]["source"])
                     for row in self.store.scan("Source", {"needs_acquisition": True}))

    def remember_snapshot(self, snapshot: Snapshot) -> Snapshot:
        row = self.get_source(snapshot.source_id)
        source = None if row is None else Source.from_mapping(row.to_mapping()["value"]["source"])
        if source is not None:
            expected = f"raw/sec/indexes/kind={source.kind}/period={source.period}/sha256={snapshot.sha256}/master.{source.representation}"
            if snapshot.raw_path != expected:
                raise Conflict("snapshot address disagrees with observed source")
        key = snapshot.source_id + ":" + snapshot.sha256
        try:
            self.store.insert("Snapshot", key, snapshot.to_mapping())
            accepted = snapshot
        except AlreadyExists:
            accepted = self.snapshot(snapshot.source_id, snapshot.sha256)
            if (accepted.raw_path, accepted.byte_count, accepted.representation, accepted.envelope_version) != (
                    snapshot.raw_path, snapshot.byte_count, snapshot.representation, snapshot.envelope_version):
                raise Conflict("same snapshot hash has conflicting immutable metadata")
        if source is not None:
            def change(value):
                latest = value["latest_received_at"]
                is_newer = latest is None or snapshot.received_at > datetime.fromisoformat(latest)
                is_current = latest is not None and snapshot.received_at == datetime.fromisoformat(latest) and value["latest_downloaded_snapshot"] == accepted.sha256
                if is_newer or is_current:
                    value["latest_downloaded_snapshot"] = accepted.sha256
                    value["latest_received_at"] = snapshot.received_at.isoformat()
                    value["acquisition_status"] = "downloaded"
                    value["needs_acquisition"] = False
            self._update_source(source, change)
        return accepted

    def snapshot(self, source_id: str, sha256: str) -> Snapshot:
        row = self.store.get("Snapshot", source_id + ":" + sha256)
        if row is None:
            raise Conflict("snapshot is not durably remembered")
        return Snapshot.from_mapping(row.to_mapping()["value"])

    def binding(self, workset_id: str, source_id: str) -> Binding | None:
        row = self.store.get("Binding", workset_id + ":" + source_id)
        return None if row is None else Binding.from_mapping(row.to_mapping()["value"])

    def bind_once(self, binding: Binding) -> Binding:
        existing = self.binding(binding.source_workset_id, binding.source_id)
        if existing is not None:
            return existing
        self.snapshot(binding.source_id, binding.snapshot_sha256)
        try:
            self.store.insert("Binding", binding.source_workset_id + ":" + binding.source_id, binding.to_mapping())
            return binding
        except AlreadyExists:
            winner = self.binding(binding.source_workset_id, binding.source_id)
            if winner is None:
                raise Conflict("binding vanished after create conflict")
            return winner

    def _insert_immutable(self, kind: str, key: str, value: dict[str, object]) -> None:
        try:
            self.store.insert(kind, key, value)
        except AlreadyExists:
            existing = self.store.get(kind, key)
            if existing is None or existing.to_mapping()["value"] != value:
                raise Conflict("immutable audit row differs after create conflict")

    def begin_attempt(self, context: RunContext) -> None:
        key = attempt_key(context)
        existing = self.store.get("Attempt", key)
        if existing is None:
            value = {"context": context.to_mapping(), "started_at": context.started_at.isoformat(),
                     "ended_at": None, "outcome": "in_progress", "result": None, "structured_errors": []}
            try:
                self.store.insert("Attempt", key, value)
            except AlreadyExists:
                existing = self.store.get("Attempt", key)
                if existing is None:
                    raise Conflict("attempt vanished after create conflict")
        if existing is not None and existing.to_mapping()["value"]["context"] != context.to_mapping():
            raise Conflict("attempt identity has conflicting provenance")
        self.active_context = context

    def finish_attempt(self, result: CommandResult) -> None:
        key = attempt_key(result.context)
        for _ in range(CAS_ATTEMPTS):
            existing = self.store.get("Attempt", key)
            if existing is None:
                raise Conflict("attempt was never begun")
            value = existing.to_mapping()["value"]
            if value["context"] != result.context.to_mapping():
                raise Conflict("result context differs from begun attempt")
            if value["result"] is not None:
                if value["result"] != result.to_mapping():
                    raise Conflict("finished attempt cannot be replaced")
                return
            value.update(ended_at=result.ended_at.isoformat(), outcome=result.outcome,
                         result=result.to_mapping(), structured_errors=[gap.to_mapping() for gap in result.gaps])
            try:
                self.store.replace("Attempt", key, value, existing.version)
                return
            except Conflict:
                continue
        raise Conflict("attempt finish exhausted conditional races")

    def record_failure(self, source: Source, error: Error) -> None:
        if error.source_id is not None and error.source_id != source.source_id:
            raise ValueError("failure belongs to a different source")
        at = self._now()
        value = {"source_id": source.source_id, "error": error.to_mapping(), "recorded_at": at.isoformat(),
                 "attempt_key": attempt_key(self.active_context) if self.active_context is not None else None}
        key = hashlib.sha256(canonical_json(value)).hexdigest()
        self._insert_immutable("Failure", key, value)
        def change(value):
            value["last_error"] = error.to_mapping()
            value["needs_acquisition"] = True
            if value["latest_downloaded_snapshot"] is None:
                value["acquisition_status"] = "failed"
        self._update_source(source, change)

    def request_attempt(self, context: RunContext, receipt: BodyReceipt, permit: Permit, ordinal: int) -> None:
        require_number(ordinal, "request ordinal", positive=True, integer=True)
        if ordinal > 5:
            raise ValueError("request ordinal exceeds five total attempts")
        next_allowed_at = getattr(permit, "next_allowed_at", None)
        if next_allowed_at is not None:
            require_utc(next_allowed_at, "next_allowed_at")
        value = {"attempt_key": attempt_key(context), "context": context.to_mapping(), "request_id": permit.request_id,
                 "ordinal": ordinal, "url": receipt.url, "status": receipt.status, "byte_count": receipt.byte_count,
                 "ownership_epoch": permit.epoch, "next_allowed_at": next_allowed_at.isoformat() if next_allowed_at is not None else None,
                 "receipt": receipt.to_mapping(), "permit": permit.to_mapping()}
        key = hashlib.sha256(canonical_json([attempt_key(context), permit.request_id, ordinal])).hexdigest()
        self._insert_immutable("TransportAttempt", key, value)
