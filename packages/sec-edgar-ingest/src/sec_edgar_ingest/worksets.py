"""Strict deterministic codecs for pinned source and snapshot worksets."""
import hashlib
from dataclasses import replace
from datetime import date

from .config import Settings, pin_context
from .models import (FORMAT_VERSION, DirectoryOutcome, RunContext, Snapshot, SnapshotWorkset,
                     Source, SourceWorkset, canonical_json, parse_json, quarter_for, quarter_value,
                     require_hash, require_text)


def workset_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def _payload(workset: SourceWorkset | SnapshotWorkset) -> dict[str, object]:
    if not isinstance(workset, (SourceWorkset, SnapshotWorkset)):
        raise ValueError("unsupported workset type")
    return {"format_version": FORMAT_VERSION,
            "workset_type": "source" if isinstance(workset, SourceWorkset) else "snapshot",
            **workset.to_mapping()}


def _identity(workset: SourceWorkset | SnapshotWorkset) -> str:
    value = _payload(workset)
    value.pop("workset_id")
    return workset_digest(value)


def _identified(workset: SourceWorkset | SnapshotWorkset):
    return replace(workset, workset_id=_identity(workset))


def encode_workset(workset: SourceWorkset | SnapshotWorkset) -> bytes:
    return canonical_json(_payload(workset))


def _decode(body: bytes, kind: str):
    if not isinstance(body, bytes):
        raise ValueError("workset body must be bytes")
    value = parse_json(body)
    if not isinstance(value, dict) or value.get("format_version") != FORMAT_VERSION or value.get("workset_type") != kind:
        raise ValueError("unsupported workset format version or type")
    identity = value.get("workset_id")
    require_hash(identity, "workset_id")
    payload = {key: item for key, item in value.items() if key != "workset_id"}
    if workset_digest(payload) != identity:
        raise ValueError("workset identity does not match the canonical payload")
    record_value = {key: item for key, item in value.items() if key not in ("format_version", "workset_type")}
    workset = (SourceWorkset if kind == "source" else SnapshotWorkset).from_mapping(record_value)
    if kind == "source":
        _validate_source(workset)
    else:
        _validate_snapshot(workset)
    return workset


def decode_source_workset(body: bytes) -> SourceWorkset:
    return _decode(body, "source")


def decode_snapshot_workset(body: bytes) -> SnapshotWorkset:
    return _decode(body, "snapshot")


def _validate_common(workset: SourceWorkset | SnapshotWorkset) -> dict[str, DirectoryOutcome]:
    require_hash(workset.workset_id, "workset_id")
    if not workset.context.effective_config:
        raise ValueError("workset context must pin its effective configuration")
    settings = Settings.from_mapping(workset.context.to_mapping()["effective_config"])
    pin_context(settings, workset.context, workset.context.started_at.date())
    end = quarter_value(workset.pinned_end_quarter)
    if end < quarter_value(settings.backfill.start_quarter) or end > quarter_value(quarter_for(workset.context.started_at.date())):
        raise ValueError("workset requires a resolved endpoint within the run's quarter range")
    if settings.backfill.end_quarter != "open" and workset.pinned_end_quarter != settings.backfill.end_quarter:
        raise ValueError("workset endpoint differs from the pinned effective configuration")
    if type(workset.overlap_from) is not date or workset.overlap_from > workset.context.started_at.date():
        raise ValueError("overlap_from must be a date no later than the run start")
    if workset.acquisition_mode not in ("reuse_accepted", "refresh"):
        raise ValueError("unsupported acquisition_mode")
    urls = [directory.url for directory in workset.directories]
    if len(set(urls)) != len(urls):
        raise ValueError("duplicate workset directories")
    if urls != sorted(urls):
        raise ValueError("workset directories must be in canonical order")
    by_source = {}
    for directory in workset.directories:
        for identity in directory.source_ids:
            if identity in by_source:
                raise ValueError("duplicate source membership across directory outcomes")
            by_source[identity] = directory
    return by_source


def _validate_source(workset: SourceWorkset, *, check_identity: bool = True) -> None:
    by_source = _validate_common(workset)
    require_text(workset.discovery_id, "discovery_id")
    identities = [source.source_id for source in workset.members]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate workset sources")
    if identities != sorted(identities):
        raise ValueError("source members must be in canonical order")
    if set(identities) != set(by_source):
        raise ValueError("directory outcomes must name every source member exactly once")
    for source in workset.members:
        if by_source[source.source_id].url != source.canonical_url.rsplit("/", 1)[0] + "/index.json":
            raise ValueError("source member must originate from its validated immediate listing child")
        source_period = quarter_for(date.fromisoformat(source.period)) if source.kind == "daily" else source.period
        if quarter_value(source_period) > quarter_value(workset.pinned_end_quarter):
            raise ValueError("source member is after the pinned endpoint")
    complete = bool(workset.directories) and all(directory.outcome != "discovery_failed" for directory in workset.directories)
    if type(workset.discovery_complete) is not bool or workset.discovery_complete != complete:
        raise ValueError("discovery completeness must match successful directory evidence")
    if check_identity and workset.workset_id != _identity(workset):
        raise ValueError("workset identity does not match its content")


def _validate_snapshot(workset: SnapshotWorkset, *, check_identity: bool = True) -> None:
    by_source = _validate_common(workset)
    require_hash(workset.source_workset_id, "source_workset_id")
    if not workset.directories or any(directory.outcome == "discovery_failed" for directory in workset.directories):
        raise ValueError("snapshot workset requires complete successful source discovery")
    identities = [snapshot.source_id for snapshot in workset.snapshots]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate snapshot members")
    if identities != sorted(identities):
        raise ValueError("snapshot members must be in canonical order")
    if set(identities) != set(by_source):
        raise ValueError("snapshot workset must name every source member exactly once")
    for snapshot in workset.snapshots:
        expected = "zip" if "/full-index/" in by_source[snapshot.source_id].url else "idx"
        if snapshot.representation != expected:
            raise ValueError("snapshot representation differs from its source member")
    if check_identity and workset.workset_id != _identity(workset):
        raise ValueError("workset identity does not match its content")


def make_source_workset(context: RunContext, end_quarter: str, discovery_id: str,
                        members: tuple[Source, ...], directories: tuple[DirectoryOutcome, ...],
                        overlap_from: date) -> SourceWorkset:
    workset = SourceWorkset("0" * 64, context, end_quarter, discovery_id,
                           tuple(sorted(members, key=lambda member: member.source_id)),
                           tuple(sorted(directories, key=lambda directory: directory.url)),
                           bool(directories) and all(directory.outcome != "discovery_failed" for directory in directories),
                           overlap_from, "refresh" if context.command == "refresh" else "reuse_accepted")
    _validate_source(workset, check_identity=False)
    return _identified(workset)


def make_snapshot_workset(source: SourceWorkset, snapshots: tuple[Snapshot, ...]) -> SnapshotWorkset:
    _validate_source(source)
    if not source.discovery_complete:
        raise ValueError("cannot snapshot an incomplete source workset")
    workset = SnapshotWorkset("0" * 64, source.workset_id, source.context,
                             tuple(sorted(snapshots, key=lambda snapshot: snapshot.source_id)),
                             source.pinned_end_quarter, source.directories, source.overlap_from,
                             source.acquisition_mode)
    _validate_snapshot(workset, check_identity=False)
    return _identified(workset)
