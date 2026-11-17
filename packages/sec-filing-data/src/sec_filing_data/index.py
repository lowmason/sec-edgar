"""O1: the rows of the 2026Q3 `master.idx`, read in place from its zip."""

import datetime
import hashlib
import io
import zipfile
from pathlib import Path

INDEX_SHA256 = "526d2dbf2dd2e4c6ac4b1b6e0b383476997e74c5a5c243dcf71dfeaff7cc9150"
INDEX_SIZE = 3_505_445

MEMBER = "master.idx"
HEADER = "CIK|Company Name|Form Type|Date Filed|Filename"
FIELD_COUNT = 5


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
    # Split on "\n" only: str.splitlines also splits on characters that would shift line numbers.
    lines = [line.removesuffix("\r") for line in text.split("\n")]

    try:
        header_at = lines.index(HEADER)
    except ValueError:
        raise ValueError(f"{MEMBER}: no header line {HEADER!r}") from None
    dashes = lines[header_at + 1] if header_at + 1 < len(lines) else ""
    if not dashes or set(dashes) != {"-"}:
        raise ValueError(f"{MEMBER}: no dashed line after the header at line {header_at + 1}")

    first_data_at = header_at + 2
    return [
        _parse_row(number, line)
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
        filed = datetime.date.fromisoformat(date_filed)
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
