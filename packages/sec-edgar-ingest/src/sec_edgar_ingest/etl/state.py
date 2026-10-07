"""ETL indexes and the per-quarter conditional publication boundary."""
from __future__ import annotations

import hashlib

from ..models import Versioned, canonical_json, quarter_value, require_hash
from ..storage.contracts import AlreadyExists, CAS_ATTEMPTS, Conflict, StateStore
from .contracts import Candidate, GenerationCapture, GenerationManifest, ObservationRef, processing_key

POINTER_FIELDS = frozenset({'quarter', 'generation_id', 'manifest_ref', 'manifest_sha256', 'manifest_bytes', 'source_fingerprint'})


def _processing_key(ref: ObservationRef) -> str:
    return processing_key(ref.source.source_id, ref.snapshot.sha256, ref.parser_version, ref.schema_version)


class EtlState:
    def __init__(self, store: StateStore):
        self.store = store

    def processing(self, ref: ObservationRef) -> Versioned | None:
        return self.store.get('Processing', _processing_key(ref))

    def accept_transform(self, ref: ObservationRef) -> None:
        key = _processing_key(ref)
        value = {'processing_key': key, 'observation': ref.to_mapping(), 'publications': {}}
        try:
            self.store.insert('Processing', key, value)
        except AlreadyExists:
            current = self.processing(ref)
            if current is None or canonical_json(current.to_mapping()['value']['observation']) != canonical_json(ref.to_mapping()):
                raise Conflict('accepted transform differs for the immutable processing identity')

    def pointer(self, quarter: str) -> Versioned | None:
        quarter_value(quarter)
        return self.store.get('QuarterPublication', quarter)

    def commit_pointer(self, quarter: str, value: dict[str, object], previous: Versioned | None) -> Versioned:
        quarter_value(quarter)
        if set(value) != POINTER_FIELDS or value['quarter'] != quarter:
            raise ValueError('pointer must contain the exact quarter publication fields')
        require_hash(value['source_fingerprint'], 'source_fingerprint')
        GenerationCapture.from_mapping({name: item for name, item in value.items() if name != 'source_fingerprint'})
        if previous is None:
            return self.store.insert('QuarterPublication', quarter, value)
        if previous.value.get('quarter') != quarter:
            raise ValueError('previous pointer belongs to another quarter')
        return self.store.replace('QuarterPublication', quarter, value, previous.version)

    def _immutable(self, kind: str, key: str, value: dict[str, object]) -> None:
        try:
            self.store.insert(kind, key, value)
        except AlreadyExists:
            current = self.store.get(kind, key)
            if current is None or canonical_json(current.to_mapping()['value']) != canonical_json(value):
                raise Conflict(f'{kind} has conflicting immutable content')

    def record_candidate(self, candidate: Candidate) -> None:
        self._immutable('Candidate', candidate.manifest.generation_id, candidate.to_mapping())

    def record_publication(self, manifest: GenerationManifest) -> None:
        for ref in manifest.sources:
            if not ref.quarter_counts.get(manifest.quarter):
                continue
            self.accept_transform(ref)
            key = _processing_key(ref)
            receipt_key = hashlib.sha256(canonical_json([key, manifest.quarter, manifest.generation_id])).hexdigest()
            receipt = {'processing_key': key, 'quarter': manifest.quarter,
                       'generation_id': manifest.generation_id, 'source_fingerprint': manifest.source_fingerprint}
            self._immutable('PublicationReceipt', receipt_key, receipt)
            self._record_membership(ref, manifest.quarter, manifest.generation_id, receipt_key)

    def _record_membership(self, ref: ObservationRef, quarter: str, generation_id: str, receipt_key: str) -> None:
        for _ in range(CAS_ATTEMPTS):
            current = self.processing(ref)
            if current is None:
                raise Conflict('accepted processing index is absent')
            value = current.to_mapping()['value']
            publications = value['publications']
            generations = publications.setdefault(quarter, {})
            if generation_id in generations:
                if generations[generation_id] != receipt_key:
                    raise Conflict('processing publication membership conflicts')
            generations[generation_id] = receipt_key
            value['published'] = all(publications.get(output_quarter) for output_quarter in ref.quarter_counts)
            if value == current.to_mapping()['value']:
                return
            try:
                self.store.replace('Processing', _processing_key(ref), value, current.version)
                return
            except Conflict:
                continue
        raise Conflict('processing publication membership exhausted conditional races')
