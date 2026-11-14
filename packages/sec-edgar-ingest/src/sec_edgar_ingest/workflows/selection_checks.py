"""Kept store-wide checks for one phase of one selection (spec §4.1, H2, H3)."""
from __future__ import annotations

from collections.abc import Mapping

from ..etl.contracts import TransformedWorkset, decode_transformed
from ..models import SourceWorkset
from . import completion, provenance

PublishCall = tuple[Mapping[str, object], TransformedWorkset]


class SelectionChecks:
    """The publish-call authority and the parent re-validations, each computed once until `renew()`.

    A value is kept only after its computation returns. A computation that raises keeps nothing, so the next
    caller runs it again. The owner calls `renew()` when a child execution returns or raises, so a kept value
    never crosses one. Both computations are looked up on their modules at call time.
    """

    def __init__(self, store, objects):
        self.store, self.objects = store, objects
        self._publish_calls: tuple[PublishCall, ...] | None = None
        self._parents: dict[str, SourceWorkset] = {}

    def publish_calls(self) -> tuple[PublishCall, ...]:
        """Each checked publish call with its decoded transformed input."""
        if self._publish_calls is None:
            decoded = []
            # A plain loop, not a generator: a StopIteration from a decode propagates as itself (PEP 479).
            for call in completion._publish_calls(self.store, self.objects):
                decoded.append((call, decode_transformed(self.objects.read(call['input_ref']))))
            self._publish_calls = tuple(decoded)
        return self._publish_calls

    def parent(self, ref: str) -> SourceWorkset:
        """The parent at `ref`, re-validated by `read_parent`."""
        if not isinstance(ref, str):
            # A corrupt row's ref (a JSON array or object) cannot be a key. `read_parent` refuses it with today's
            # message, so it is never kept.
            return provenance.read_parent(ref, self.store, self.objects)
        if ref not in self._parents:
            self._parents[ref] = provenance.read_parent(ref, self.store, self.objects)
        return self._parents[ref]

    def renew(self) -> None:
        """Drop every kept value."""
        self._publish_calls = None
        self._parents = {}
