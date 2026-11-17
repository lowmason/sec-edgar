"""Parse an SEC complete submission file (`<accession>.txt`) from its bytes.

The file can reach hundreds of MB, so the parser never decodes it whole and never
splits it into lines. It finds line-initial tags with `bytes.find`, decodes only the
header, and returns document text as byte offsets into the original `raw`.
"""

from dataclasses import dataclass

HEADER_OPEN = b"<SEC-HEADER>"
HEADER_CLOSE = b"</SEC-HEADER>"
DOCUMENT_OPEN = b"<DOCUMENT>"
DOCUMENT_CLOSE = b"</DOCUMENT>"
TEXT_OPEN = b"<TEXT>"
TEXT_CLOSE = b"</TEXT>"

ACCEPTANCE_TAG = "<ACCEPTANCE-DATETIME>"
PRIVATE_TO_PUBLIC = "PRIVATE-TO-PUBLIC"

NAME_LABEL = "COMPANY CONFORMED NAME"
CIK_LABEL = "CENTRAL INDEX KEY"

TEXT_WRAPPER_TAGS = (b"xml", b"xbrl")


class EnvelopeError(ValueError):
    """The bytes are not a complete submission file."""


@dataclass(frozen=True)
class Party:
    role: str
    name: str | None
    cik: str | None


@dataclass
class _PartyBuilder:
    role: str
    name: str | None = None
    cik: str | None = None


@dataclass(frozen=True)
class Document:
    sequence: int | None
    type: str
    filename: str | None
    description: str | None
    text_offset: int
    text_length: int


@dataclass(frozen=True)
class Submission:
    fields: tuple[tuple[str, str], ...]
    acceptance_datetime: str | None
    private_to_public: bool
    parties: tuple[Party, ...]
    documents: tuple[Document, ...]

    def field(self, label: str) -> str | None:
        """The first value filed under `label`, or None."""
        for field_label, value in self.fields:
            if field_label == label:
                return value
        return None


def parse_submission(raw: bytes) -> Submission:
    """Read the header and the document list of a complete submission file.

    Raises EnvelopeError for a missing header, a `<DOCUMENT>` with no
    `</DOCUMENT>`, and a document with no `<TEXT>` or no `</TEXT>`.
    """
    header_open = _find_line_tag(raw, HEADER_OPEN, 0)
    header_close = (
        _find_line_tag(raw, HEADER_CLOSE, header_open) if header_open >= 0 else -1
    )
    if header_close < 0:
        raise EnvelopeError("no <SEC-HEADER> ... </SEC-HEADER> block")
    header_start = raw.index(b"\n", header_open) + 1
    header = raw[header_start:header_close].decode("utf-8", errors="replace")
    fields, acceptance_datetime, private_to_public, parties = _parse_header(header)
    documents = _parse_documents(raw, header_close + len(HEADER_CLOSE))
    return Submission(
        fields, acceptance_datetime, private_to_public, parties, documents
    )


def document_text(raw: bytes, doc: Document) -> bytes:
    """The text of `doc` without surrounding whitespace or one outer XML/XBRL wrapper."""
    text = raw[doc.text_offset : doc.text_offset + doc.text_length].strip()
    for tag in TEXT_WRAPPER_TAGS:
        opening = b"<" + tag + b">"
        closing = b"</" + tag + b">"
        if (
            len(text) >= len(opening) + len(closing)
            and text[: len(opening)].lower() == opening
            and text[-len(closing) :].lower() == closing
        ):
            return text[len(opening) : -len(closing)].strip()
    return text


def _find_line_tag(raw: bytes, tag: bytes, start: int, end: int | None = None) -> int:
    """Index of the first `tag` at a line start at or after `start`, or -1.

    A line start is byte 0 or the byte after `\\n`. With `end`, the tag must end
    before `end`.
    """
    if start == 0 and raw.startswith(tag, 0, end):
        return 0
    found = raw.find(b"\n" + tag, max(start - 1, 0), end)
    return found + 1 if found >= 0 else -1


def _parse_header(
    header: str,
) -> tuple[tuple[tuple[str, str], ...], str | None, bool, tuple[Party, ...]]:
    fields: list[tuple[str, str]] = []
    acceptance_datetime = None
    private_to_public = False
    builders: list[_PartyBuilder] = []
    current: _PartyBuilder | None = None

    for line in header.split("\n"):
        line = line.removesuffix("\r")
        if PRIVATE_TO_PUBLIC in line:
            private_to_public = True
        if not line:
            continue
        if line[0] in " \t":
            if current is not None:
                _read_party_detail(current, line)
            continue

        current = None
        if line.startswith("<"):
            if line.startswith(ACCEPTANCE_TAG) and acceptance_datetime is None:
                acceptance_datetime = line[len(ACCEPTANCE_TAG) :].strip() or None
            continue
        label, colon, value = line.partition(":")
        label, value = label.strip(), value.strip()
        if not colon or not label:
            continue
        if value:
            fields.append((label, value))
        else:
            current = _PartyBuilder(role=label)
            builders.append(current)

    parties = tuple(Party(b.role, b.name, b.cik) for b in builders)
    return tuple(fields), acceptance_datetime, private_to_public, parties


def _read_party_detail(party: _PartyBuilder, line: str) -> None:
    """Keep the first name and the first CIK among the indented lines of a party."""
    label, _, value = line.partition(":")
    label, value = label.strip(), value.strip()
    if label == NAME_LABEL and party.name is None:
        party.name = value or None
    elif label == CIK_LABEL and party.cik is None:
        party.cik = value or None


def _parse_documents(raw: bytes, start: int) -> tuple[Document, ...]:
    documents = []
    position = start
    while (open_at := _find_line_tag(raw, DOCUMENT_OPEN, position)) >= 0:
        close_at = _find_line_tag(raw, DOCUMENT_CLOSE, open_at)
        if close_at < 0:
            raise EnvelopeError(f"<DOCUMENT> at byte {open_at} has no </DOCUMENT>")
        documents.append(_parse_document(raw, open_at, close_at))
        position = close_at + len(DOCUMENT_CLOSE)
    return tuple(documents)


def _parse_document(raw: bytes, open_at: int, close_at: int) -> Document:
    text_tag = _find_line_tag(raw, TEXT_OPEN, open_at, close_at)
    if text_tag < 0:
        raise EnvelopeError(f"<DOCUMENT> at byte {open_at} has no <TEXT>")
    text_offset = raw.index(b"\n", text_tag) + 1
    text_close = _find_line_tag(raw, TEXT_CLOSE, text_offset, close_at)
    if text_close < 0:
        raise EnvelopeError(f"<DOCUMENT> at byte {open_at} has no </TEXT>")

    meta = raw[open_at:text_tag].decode("utf-8", errors="replace")
    values = _tag_values(meta)
    sequence = values.get("SEQUENCE")
    return Document(
        sequence=int(sequence)
        if sequence and sequence.isascii() and sequence.isdigit()
        else None,
        type=values.get("TYPE") or "",
        filename=values.get("FILENAME") or None,
        description=values.get("DESCRIPTION") or None,
        text_offset=text_offset,
        text_length=text_close - text_offset,
    )


def _tag_values(meta: str) -> dict[str, str]:
    """The first `<NAME>value` line for each tag name, with the value stripped."""
    values: dict[str, str] = {}
    for line in meta.split("\n"):
        tag, closing, rest = line.removesuffix("\r").partition(">")
        if closing and tag.startswith("<") and tag[1:] not in values:
            values[tag[1:]] = rest.strip()
    return values
