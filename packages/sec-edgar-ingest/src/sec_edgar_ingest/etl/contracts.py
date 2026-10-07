"""Immutable ETL records, explicit Arrow schemas, and canonical workset codecs."""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

import pyarrow as pa

from ..models import (Error, IMAGE_PATTERN, Record, RunContext, SCHEMA_VERSION, Snapshot, Source,
                      canonical_json, parse_json, quarter_value, require_hash, require_number,
                      require_text, require_utc, safe_relative_path, validate_record_fields)

TRANSFORMED_FORMAT = 'sec-transformed-workset-v1'
GENERATION_FORMAT = 'sec-generation-v1'
RESULT_FORMAT = 'sec-etl-result-v1'
ORIGINAL_FIELD_COUNT = 5


def _versions(parser_version: str, schema_version: str) -> None:
    for label, version in (('parser_version', parser_version), ('schema_version', schema_version)):
        safe_relative_path(version, label)
        if '/' in version:
            raise ValueError(f'{label} must be a single path segment')


def _record(record: Record) -> None:
    validate_record_fields(record)
    for name, value in record.to_mapping().items():
        if name.endswith(('_sha256', '_fingerprint')) or name in ('generation_id', 'base_generation_id', 'retained_from_generation', 'workset_id'):
            if value is not None:
                require_hash(value, name)
        if name.endswith('_ref') and value is not None:
            safe_relative_path(value, name)
        if name in ('quarter',):
            quarter_value(value)
    if hasattr(record, 'parser_version'):
        _versions(record.parser_version, record.schema_version)
        if record.schema_version != SCHEMA_VERSION:
            raise ValueError('unsupported schema_version')


def _counts(record: Record, *names: str) -> None:
    for name in names:
        require_number(getattr(record, name), name, integer=True)


@dataclass(frozen=True, slots=True)
class IndexRow(Record):
    cik: str
    company_name: str
    form_type: str
    archive_path: str
    filing_date: date
    accession_number: str | None
    source_id: str
    source_sha256: str
    parser_version: str
    schema_version: str

    def __post_init__(self):
        _record(self)
        if re.fullmatch(r'[0-9]{10}', self.cik) is None:
            raise ValueError('cik must be a zero-padded ten-digit identifier')
        require_text(self.company_name, 'company_name')
        require_text(self.form_type, 'form_type')
        safe_relative_path(self.archive_path, 'archive_path')
        segments = self.archive_path.split('/')
        if (len(segments) >= 4 and segments[:2] == ['edgar', 'data']
                and re.fullmatch(r'[0-9]{1,10}', segments[2])
                and segments[2].zfill(10) != self.cik):
            raise ValueError('archive path CIK disagrees with the row CIK')
        require_hash(self.source_id, 'source_id')
        if self.accession_number is not None and re.fullmatch(r'[0-9]{10}-[0-9]{2}-[0-9]{6}', self.accession_number) is None:
            raise ValueError('invalid accession_number')


@dataclass(frozen=True, slots=True)
class Observation(Record):
    row: IndexRow
    original_fields: tuple[str, str, str, str, str]
    line_number: int

    def __post_init__(self):
        _record(self)
        if len(self.original_fields) != ORIGINAL_FIELD_COUNT:
            raise ValueError('original_fields must retain exactly five fields')
        require_number(self.line_number, 'line_number', positive=True, integer=True)


@dataclass(frozen=True, slots=True)
class ObservationRef(Record):
    source: Source
    snapshot: Snapshot
    parser_version: str
    schema_version: str
    rows_ref: str
    manifest_ref: str
    rows_sha256: str
    rows_bytes: int
    source_row_count: int
    distinct_key_count: int
    quarter_counts: Mapping[str, int]

    def __post_init__(self):
        _record(self)
        _counts(self, 'rows_bytes', 'source_row_count', 'distinct_key_count')
        if self.source.source_id != self.snapshot.source_id or self.source.representation != self.snapshot.representation:
            raise ValueError('observation source and snapshot disagree')
        if self.distinct_key_count > self.source_row_count:
            raise ValueError('distinct keys exceed source rows')
        for quarter, count in self.quarter_counts.items():
            quarter_value(quarter)
            require_number(count, 'quarter count', integer=True, positive=True)
        if sum(self.quarter_counts.values()) != self.source_row_count:
            raise ValueError('quarter counts must account for every retained observation')
        base = observation_base(self.source.source_id, self.snapshot.sha256, self.parser_version, self.schema_version)
        if self.rows_ref != base + '/rows.parquet' or self.manifest_ref != base + '/manifest.json':
            raise ValueError('observation references must match processing identity')


@dataclass(frozen=True, slots=True)
class TransformedWorkset(Record):
    workset_id: str
    snapshot_workset_ref: str
    origin_context: RunContext
    context: RunContext
    observations: tuple[ObservationRef, ...]
    failures: tuple[Error, ...]
    complete: bool

    def __post_init__(self):
        _record(self)
        if re.fullmatch(r'worksets/sec/snapshot/sha256=[0-9a-f]{64}/workset.json', self.snapshot_workset_ref) is None:
            raise ValueError('exact snapshot workset reference required')
        identities = [ref.source.source_id for ref in self.observations]
        if len(set(identities)) != len(identities):
            raise ValueError('duplicate transformed source')
        if self.complete and self.failures:
            raise ValueError('complete workset cannot contain failures')
        for ref in self.observations:
            if (ref.parser_version, ref.schema_version) != (self.context.parser_version, self.context.schema_version):
                raise ValueError('observation versions disagree with transform context')


@dataclass(frozen=True, slots=True)
class FileRef(Record):
    path: str
    sha256: str
    byte_count: int
    row_count: int
    role: Literal['data', 'changes']

    def __post_init__(self):
        _record(self)
        safe_relative_path(self.path, 'path')
        require_hash(self.sha256, 'sha256')
        _counts(self, 'byte_count', 'row_count')


@dataclass(frozen=True, slots=True)
class GenerationManifest(Record):
    quarter: str
    generation_id: str
    base_generation_id: str | None
    source_fingerprint: str
    parser_version: str
    schema_version: str
    image_digest: str
    sources: tuple[ObservationRef, ...]
    files: tuple[FileRef, ...]
    row_count: int
    added: int
    updated: int
    withdrawn: int
    unresolved_absence: int
    provenance_refreshed: int
    quarter_mode: Literal['open', 'closed']
    membership_source: ObservationRef | None
    retained_from_generation: str | None
    gate: Literal['clear', 'awaiting_approval']
    format_version: str = GENERATION_FORMAT

    def __post_init__(self):
        _record(self)
        if self.format_version != GENERATION_FORMAT:
            raise ValueError('unsupported generation format')
        if IMAGE_PATTERN.fullmatch(self.image_digest) is None:
            raise ValueError('immutable producing image digest required')
        _counts(self, 'row_count', 'added', 'updated', 'withdrawn', 'unresolved_absence', 'provenance_refreshed')
        if len({ref.source.source_id for ref in self.sources}) != len(self.sources):
            raise ValueError('duplicate generation source')
        if len({ref.path for ref in self.files}) != len(self.files):
            raise ValueError('duplicate generation file')
        for ref in self.sources:
            if (ref.parser_version, ref.schema_version) != (self.parser_version, self.schema_version):
                raise ValueError('generation sources must use one parser/schema')
        if self.membership_source is not None:
            if self.membership_source not in self.sources or self.membership_source.source.kind != 'quarterly' or self.membership_source.source.period != self.quarter:
                raise ValueError('membership source must be the selected quarterly source for this quarter')
        if self.membership_source is None and (self.withdrawn or self.gate == 'awaiting_approval'):
            raise ValueError('withdrawals and withdrawal gates require quarterly membership authority')


@dataclass(frozen=True, slots=True)
class Candidate(Record):
    manifest: GenerationManifest
    manifest_ref: str
    manifest_sha256: str
    manifest_bytes: int
    candidate_ref: str | None

    def __post_init__(self):
        _record(self)
        _counts(self, 'manifest_bytes')


@dataclass(frozen=True, slots=True)
class PublicationResult(Record):
    quarter: str
    outcome: str
    generation_id: str | None
    manifest_ref: str | None
    candidate_ref: str | None
    conflicts: int

    def __post_init__(self):
        _record(self)
        require_text(self.outcome, 'outcome')
        _counts(self, 'conflicts')


@dataclass(frozen=True, slots=True)
class GenerationCapture(Record):
    quarter: str
    generation_id: str
    manifest_ref: str
    manifest_sha256: str
    manifest_bytes: int

    def __post_init__(self):
        _record(self)
        _counts(self, 'manifest_bytes')


@dataclass(frozen=True, slots=True)
class EtlResult(Record):
    context: RunContext
    outcome: str
    input_ref: str
    transformed_workset_ref: str | None
    transformed: int
    published: int
    unchanged: int
    quarantined: int
    awaiting_approval: int
    failed: int
    quarters: tuple[PublicationResult, ...]
    gaps: tuple[Error, ...]
    started_at: datetime
    ended_at: datetime
    format_version: str = RESULT_FORMAT

    def __post_init__(self):
        _record(self)
        if self.format_version != RESULT_FORMAT:
            raise ValueError('unsupported ETL result format')
        require_text(self.outcome, 'outcome')
        _counts(self, 'transformed', 'published', 'unchanged', 'quarantined', 'awaiting_approval', 'failed')
        require_utc(self.started_at, 'started_at')
        require_utc(self.ended_at, 'ended_at')
        if self.ended_at < self.started_at:
            raise ValueError('ETL result ends before it starts')
        if len({result.quarter for result in self.quarters}) != len(self.quarters):
            raise ValueError('duplicate quarter result')


def canonical_schema() -> pa.Schema:
    names = ('cik', 'company_name', 'form_type', 'archive_path', 'filing_date',
             'accession_number', 'source_id', 'source_sha256', 'parser_version', 'schema_version')
    return pa.schema([pa.field(name, pa.date32() if name == 'filing_date' else pa.string(),
                               nullable=name == 'accession_number') for name in names])


def observation_schema() -> pa.Schema:
    return pa.schema([*canonical_schema(),
                      pa.field('original_fields', pa.list_(pa.field('item', pa.string(), nullable=False), ORIGINAL_FIELD_COUNT), nullable=False),
                      pa.field('line_number', pa.int64(), nullable=False)])


def change_schema() -> pa.Schema:
    return pa.schema([pa.field('change_type', pa.string(), nullable=False),
                      pa.field('cik', pa.string(), nullable=False),
                      pa.field('archive_path', pa.string(), nullable=False),
                      pa.field('before', pa.struct(canonical_schema()), nullable=True),
                      pa.field('after', pa.struct(canonical_schema()), nullable=True),
                      pa.field('reason', pa.string(), nullable=True)])


def processing_key(source_id: str, snapshot_sha256: str, parser_version: str, schema_version: str) -> str:
    require_hash(source_id, 'source_id')
    require_hash(snapshot_sha256, 'snapshot_sha256')
    _versions(parser_version, schema_version)
    return hashlib.sha256(canonical_json([source_id, snapshot_sha256, parser_version, schema_version])).hexdigest()


def observation_base(source_id: str, snapshot_sha256: str, parser_version: str, schema_version: str) -> str:
    processing_key(source_id, snapshot_sha256, parser_version, schema_version)
    return f'observations/sec/indexes/source={source_id}/sha256={snapshot_sha256}/parser={parser_version}/schema={schema_version}'


def encode_transformed(workset: TransformedWorkset) -> bytes:
    if type(workset) is not TransformedWorkset:
        raise ValueError('expected transformed workset')
    payload = {'format_version': TRANSFORMED_FORMAT, **workset.to_mapping()}
    identity_payload = {name: value for name, value in payload.items() if name != 'workset_id'}
    if hashlib.sha256(canonical_json(identity_payload)).hexdigest() != workset.workset_id:
        raise ValueError('transformed workset identity differs from canonical payload')
    return canonical_json(payload)


def decode_transformed(body: bytes) -> TransformedWorkset:
    if type(body) is not bytes:
        raise ValueError('transformed workset must be bytes')
    payload = parse_json(body)
    if not isinstance(payload, dict) or payload.get('format_version') != TRANSFORMED_FORMAT:
        raise ValueError('unsupported transformed workset format')
    workset = TransformedWorkset.from_mapping({name: value for name, value in payload.items() if name != 'format_version'})
    if encode_transformed(workset) != body:
        raise ValueError('transformed workset must use canonical JSON bytes')
    return workset


def transformed_ref(workset: TransformedWorkset) -> str:
    encode_transformed(workset)
    return f'worksets/sec/transformed/sha256={workset.workset_id}/workset.json'
