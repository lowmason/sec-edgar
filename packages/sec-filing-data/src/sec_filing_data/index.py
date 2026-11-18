"""O1: the rows of the 2026Q3 `master.idx`, read in place from its zip."""

import hashlib
import io
import struct
import zipfile
from datetime import UTC, date, datetime
from pathlib import Path

from sec_filing_data.layout import Layout
from sec_filing_data.tables import write_table

INDEX_SHA256 = "526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150"
INDEX_SIZE = 3_505_445

# The three constants below are copied from the receipt of this file in the parked engine
# (spec 6.2). The code and the tests never read that file. Its path, in the main checkout, is:
# data/objects/staging/sec/88738b7d-cd8e-48c4-b301-b78dc4b993bd/wf-02586348dbe3e7033d621f8c2cd9c908fa3f62f7/5005901a1e8132207ea0cf7a0d4bec1d7b9ca3a6f0371b9e45c9eb2863045086/4fdd5bb903fc43f5921ee46c2bf47714/receipt.json
INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.zip"
INDEX_RECEIVED_AT = datetime(2026, 10, 31, 17, 54, 33, 39228, tzinfo=UTC)
INDEX_LAST_MODIFIED_AT = datetime(2026, 10, 31, 7, 50, 9, tzinfo=UTC)

MEMBER = "master.idx"
HEADER = "CIK|Company Name|Form Type|Date Filed|Filename"
FIELD_COUNT = 5
DATA_THROUGH_PREFIX = "Last Data Received:"

_EXTENDED_TIMESTAMP = 0x5455
_MTIME_FLAG = 1
_MTIME_END = 5  # flags byte, then the four bytes of mtime


def read_index(zip_path: Path, *, sha256: str, size: int) -> list[dict]:
    """Return one row per data line of `master.idx`, in file order, with no dedupe.

    Raises ValueError for a wrong size or SHA-256 before any parse, and for a bad
    header or a bad row afterwards.
    """
    data = zip_path.read_bytes()
    if len(data) != size:
        raise ValueError(f"{zip_path}: size {len(data)}, expected {size}")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError(f"{zip_path}: SHA-256 differs from {sha256}")

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        text = archive.read(MEMBER).decode("utf-8")
        built_at = member_mtime(archive.getinfo(MEMBER))
    # Split on "\n" only: str.splitlines also splits on characters that would shift line numbers.
    lines = [line.removesuffix("\r") for line in text.split("\n")]

    try:
        header_at = lines.index(HEADER)
    except ValueError:
        raise ValueError(f"{MEMBER}: no header line {HEADER!r}") from None
    dashes = lines[header_at + 1] if header_at + 1 < len(lines) else ""
    if not dashes or set(dashes) != {"-"}:
        raise ValueError(f"{MEMBER}: no dashed line after the header at line {header_at + 1}")

    source = {
        "source_url": INDEX_URL,
        "source_sha256": sha256,
        "index_built_at": built_at,
        "index_data_through": _data_through(lines[:header_at]),
        "index_received_at": INDEX_RECEIVED_AT,
        "index_last_modified_at": INDEX_LAST_MODIFIED_AT,
    }
    first_data_at = header_at + 2
    return [
        {**_parse_row(number, line), **source}
        for number, line in enumerate(lines[first_data_at:], start=first_data_at + 1)
        if line
    ]


def _parse_row(line_number: int, line: str) -> dict:
    fields = line.split("|")
    if len(fields) != FIELD_COUNT:
        raise ValueError(
            f"{MEMBER} line {line_number}: expected {FIELD_COUNT} fields, got {len(fields)}"
        )
    cik, company_name, form_type, date_filed, filename = fields
    try:
        cik_number = int(cik)
        filed = date.fromisoformat(date_filed)
    except ValueError as error:
        raise ValueError(f"{MEMBER} line {line_number}: {error}") from None
    return {
        "line_number": line_number,
        "cik": cik_number,
        "company_name": company_name,
        "form_type": form_type,
        "date_filed": filed,
        "filename": filename,
        "accession_number": filename.rsplit("/", 1)[-1].removesuffix(".txt"),
    }


def run_index(layout: Layout, zip_path: Path) -> list[dict]:
    """Write the `index` table from the zip at `zip_path`, and return its rows."""
    rows = read_index(zip_path, sha256=INDEX_SHA256, size=INDEX_SIZE)
    write_table(layout, "index", rows)
    return rows


def member_mtime(info: zipfile.ZipInfo) -> datetime | None:
    """The UTC modification time in the extended-timestamp field (`0x5455`) of `info.extra`.

    Python's `zipfile` does not decode this field. The field holds a flags byte, then the
    mtime as four unsigned little-endian bytes when flags bit 0 is set. The code does not
    size the field from its flags. It returns None when there is no usable field, and when
    the extra data is truncated or malformed.
    """
    extra = info.extra
    offset = 0
    while offset + 4 <= len(extra):
        header_id, size = struct.unpack_from("<HH", extra, offset)
        offset += 4
        if offset + size > len(extra):
            return None
        data = extra[offset : offset + size]
        offset += size
        if header_id == _EXTENDED_TIMESTAMP and size >= _MTIME_END and data[0] & _MTIME_FLAG:
            return datetime.fromtimestamp(int.from_bytes(data[1:_MTIME_END], "little"), UTC)
    return None


def _data_through(header_lines: list[str]) -> str | None:
    for line in header_lines:
        if line.startswith(DATA_THROUGH_PREFIX):
            return line.removeprefix(DATA_THROUGH_PREFIX).strip()
    return None
