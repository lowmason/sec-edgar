"""Read the facts of one XBRL instance document, as filed.

Filers choose their own prefixes, so elements are matched by local name. Values stay as
filed text, with no numeric conversion. Only the `xsi:nil` attribute is matched by its
namespace URI.
"""

import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass, field
from io import BytesIO

from sec_filing_data.envelope import Document

INSTANCE_TYPE = "EX-101.INS"
SEC_EXTRACTED_SUFFIX = "_htm.xml"

_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"
_DOCTYPE = b"<!DOCTYPE"
_TRUE = ("true", "1")


class XbrlError(ValueError):
    """The bytes are not an instance document this parser reads."""


@dataclass(frozen=True)
class Fact:
    concept: str
    value: str | None
    unit: str | None
    period_start: str | None
    period_end: str | None
    period_instant: str | None
    decimals: str | None
    context_id: str
    dimensions: str | None
    is_nil: bool


@dataclass(frozen=True)
class _Context:
    period_start: str | None = None
    period_end: str | None = None
    period_instant: str | None = None
    dimensions: str | None = None


@dataclass(frozen=True)
class _RawFact:
    """A fact as read from its element. Its concept, context and unit are not resolved yet."""

    namespace: str | None
    local_name: str
    value: str | None
    context_id: str
    unit_ref: str | None
    decimals: str | None
    is_nil: bool


@dataclass
class _Scan:
    prefixes: dict[str, str] = field(default_factory=dict)
    contexts: dict[str, _Context] = field(default_factory=dict)
    units: dict[str, str | None] = field(default_factory=dict)
    facts: list[_RawFact] = field(default_factory=list)


def find_instance(documents: Sequence[Document]) -> Document | None:
    """The first `EX-101.INS` document, else the first SEC-extracted `*_htm.xml`, else None."""
    for document in documents:
        if document.type == INSTANCE_TYPE:
            return document
    for document in documents:
        if document.filename is not None and document.filename.endswith(SEC_EXTRACTED_SUFFIX):
            return document
    return None


def parse_instance(xml: bytes) -> list[Fact]:
    """The facts of an instance document, in file order.

    A fact is a direct child of the root that has a `contextRef` attribute and no child
    element. A `contextRef` or `unitRef` that names nothing leaves that fact's period,
    dimension or unit columns null. Raises XbrlError for a DOCTYPE and for XML that does
    not parse.
    """
    if _DOCTYPE in xml:
        raise XbrlError("the document has a DOCTYPE declaration")
    scan = _scan(xml)
    no_context = _Context()
    facts = []
    for raw in scan.facts:
        context = scan.contexts.get(raw.context_id, no_context)
        facts.append(
            Fact(
                concept=_concept(raw, scan.prefixes),
                value=raw.value,
                unit=scan.units.get(raw.unit_ref) if raw.unit_ref is not None else None,
                period_start=context.period_start,
                period_end=context.period_end,
                period_instant=context.period_instant,
                decimals=raw.decimals,
                context_id=raw.context_id,
                dimensions=context.dimensions,
                is_nil=raw.is_nil,
            )
        )
    return facts


def _scan(xml: bytes) -> _Scan:
    """Read the document in one pass. Each child of the root is dropped once it is read."""
    scan = _Scan()
    depth = 0
    try:
        for event, item in ET.iterparse(BytesIO(xml), events=("start-ns", "start", "end")):
            if event == "start-ns":
                prefix, namespace = item
                if prefix:
                    scan.prefixes.setdefault(namespace, prefix)
            elif event == "start":
                depth += 1
            else:
                depth -= 1
                if depth == 1:
                    _read_child(scan, item)
                    item.clear()
    except ET.ParseError as error:
        raise XbrlError(f"not well-formed XML: {error}") from error
    return scan


def _read_child(scan: _Scan, element: ET.Element) -> None:
    name = _local_name(element.tag)
    if element.get("contextRef") is not None:
        _read_fact(scan, element)
    elif name == "context" and (context_id := element.get("id")) is not None:
        scan.contexts[context_id] = _read_context(element)
    elif name == "unit" and (unit_id := element.get("id")) is not None:
        scan.units[unit_id] = _read_unit(element) or None


def _read_fact(scan: _Scan, element: ET.Element) -> None:
    """Keep a fact. An element with child elements (a tuple) is skipped."""
    if len(element) > 0:
        return
    namespace, local_name = _split_tag(element.tag)
    is_nil = element.get(_XSI_NIL, "").strip() in _TRUE
    scan.facts.append(
        _RawFact(
            namespace=namespace,
            local_name=local_name,
            value=None if is_nil else element.text or "",
            context_id=element.attrib["contextRef"],
            unit_ref=element.get("unitRef"),
            decimals=element.get("decimals"),
            is_nil=is_nil,
        )
    )


def _concept(raw: _RawFact, prefixes: dict[str, str]) -> str:
    """`prefix:local` with the document's own prefix, else `{namespace}local`."""
    if raw.namespace is None:
        return raw.local_name
    prefix = prefixes.get(raw.namespace)
    if prefix is None:
        return f"{{{raw.namespace}}}{raw.local_name}"
    return f"{prefix}:{raw.local_name}"


def _read_context(element: ET.Element) -> _Context:
    period = _child(element, "period")
    return _Context(
        period_start=_child_text(period, "startDate"),
        period_end=_child_text(period, "endDate"),
        period_instant=_child_text(period, "instant"),
        dimensions=_dimensions(element),
    )


def _dimensions(context: ET.Element) -> str | None:
    """Each member as `<dimension>=<member>`, sorted and joined with `;`, or None."""
    members = []
    for member in context.iter():
        name = _local_name(member.tag)
        if name == "explicitMember":
            members.append(f"{member.get('dimension', '')}={(member.text or '').strip()}")
        elif name == "typedMember":
            domain = next(iter(member), None)
            text = (domain.text or "").strip() if domain is not None else ""
            members.append(f"{member.get('dimension', '')}={text}")
    return ";".join(sorted(members)) or None


def _read_unit(element: ET.Element) -> str:
    """The measure text, a `divide` as `numerator/denominator`, several measures joined `*`."""
    divide = _child(element, "divide")
    if divide is None:
        return _measures(element)
    numerator = _measures(_child(divide, "unitNumerator"))
    denominator = _measures(_child(divide, "unitDenominator"))
    return f"{numerator}/{denominator}"


def _measures(parent: ET.Element | None) -> str:
    if parent is None:
        return ""
    return "*".join(
        (measure.text or "").strip() for measure in parent if _local_name(measure.tag) == "measure"
    )


def _child(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((child for child in parent if _local_name(child.tag) == name), None)


def _child_text(parent: ET.Element | None, name: str) -> str | None:
    child = _child(parent, name)
    if child is None:
        return None
    return (child.text or "").strip() or None


def _local_name(tag: str) -> str:
    return _split_tag(tag)[1]


def _split_tag(tag: str) -> tuple[str | None, str]:
    """The namespace (or None) and the local name of an ElementTree tag."""
    if tag.startswith("{"):
        namespace, _, local_name = tag[1:].partition("}")
        return namespace, local_name
    return None, tag
