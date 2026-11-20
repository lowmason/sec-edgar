"""The as-of query: each record of the sample and of its partners that was public by a time.

A held filing is known from the time its stored copy was last modified, or else from the time
we fetched it (C8). Each record of the filing takes that time, and so does each index row of
it. An index row of a filing that we do not hold takes the time the index file was last
modified. `answer` first checks each file that it reads against the manifest of its set, and
refuses when one differs. Every time comes from the tables, never from the clock. This module
writes nothing and does not import `requests`.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sec_filing_data import manifest
from sec_filing_data.layout import Layout
from sec_filing_data.links import HELD_IN_PARTNER, HELD_IN_SAMPLE
from sec_filing_data.tables import STAMP_KEYS, read_stamp
from sec_filing_data.times import NEW_YORK

ASOF_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership", "links")
# An index row of a filing that we do not hold.
HELD_IN_INDEX = "index"
HELD_IN = (HELD_IN_SAMPLE, HELD_IN_PARTNER, HELD_IN_INDEX)

_TABLES_SET = "tables"
# The tables that each set gives to the answer, and where the filings of the set are held.
_SET_TABLES = {
    _TABLES_SET: ("index", "filings", "parties", "documents", "facts", "ownership"),
    manifest.STAGE4_SET: ("filings", "parties", "documents", "ownership", "links"),
}
_SET_HELD_IN = {_TABLES_SET: HELD_IN_SAMPLE, manifest.STAGE4_SET: HELD_IN_PARTNER}

_TIMESTAMP = pa.timestamp("us", tz="UTC")
_HELD_SCHEMA = pa.schema(
    [("accession_number", pa.string()), ("known_from", _TIMESTAMP), ("held_in", pa.string())]
)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)
_ONE_MICROSECOND = timedelta(microseconds=1)


class AsOfRefused(Exception):
    """A file that the answer reads does not match its manifest, or is missing."""


@dataclass(frozen=True)
class ManifestUsed:
    set_name: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class Answer:
    """The instant in UTC, the manifests that bind the answer, and one table for each name of
    ASOF_TABLES."""

    at: datetime
    manifests: tuple[ManifestUsed, ...]
    tables: dict[str, pa.Table]


@dataclass(frozen=True)
class _CheckedSet:
    """One table set: its manifest as read, and the tables that the answer reads from it."""

    name: str
    used: ManifestUsed
    listed: dict
    tables: dict[str, pa.Table]


def parse_at(text: str) -> datetime:
    """The instant that `text` names, in UTC.

    A date `YYYY-MM-DD` is the end of that day in New York: 1 µs before the next day starts.
    Any other text is an ISO 8601 instant, which must give its UTC offset or `Z`. Else
    `ValueError`, which quotes the text.
    """
    try:
        if _DATE.fullmatch(text):
            next_day = date.fromisoformat(text) + timedelta(days=1)
            start = datetime.combine(next_day, time(0), tzinfo=NEW_YORK)
            return start.astimezone(UTC) - _ONE_MICROSECOND
        moment = datetime.fromisoformat(text)
        if moment.utcoffset() is None:
            raise ValueError("an instant needs a UTC offset or Z")
        return moment.astimezone(UTC)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"not a date or an instant: {text!r}: {error}") from None


def known_from(filing: dict) -> datetime | None:
    """The time from which we know a filing, from its `filings` row (C8).

    A filing whose fetch is not `ok` is not held: None. A held filing is known from the time
    its stored copy was last modified, or else from the time we fetched it.
    """
    if filing["outcome"] != "ok":
        return None
    if filing["last_modified_at"] is not None:
        return filing["last_modified_at"]
    return filing["fetched_at"]


def answer(root: Path, at: datetime) -> Answer:
    """Each record of the sample and of its partners whose `known_from` is at or before `at`.

    A naive `at` raises `ValueError`. A file that does not match its manifest raises
    `AsOfRefused`, and no answer comes back.
    """
    if at.utcoffset() is None:
        raise ValueError(f"at has no UTC offset: {at.isoformat()}")
    at = at.astimezone(UTC)
    layout = Layout(root)
    tables_set = _checked_set(layout, _TABLES_SET)
    stage4_set = _checked_set(layout, manifest.STAGE4_SET)
    _check_builds_on(layout, tables_set, stage4_set)
    sets = (tables_set, stage4_set)
    held = _held_filings(sets)
    cutoff = pa.scalar(at, type=_TIMESTAMP)
    # The rows of `tables/` come first, then the rows of `stage4/tables/`.
    tables = {
        name: pa.concat_tables(
            [
                _answer_part(name, checked.tables[name], _SET_HELD_IN[checked.name], held, cutoff)
                for checked in sets
                if name in checked.tables
            ]
        )
        for name in ASOF_TABLES
    }
    return Answer(at, tuple(checked.used for checked in sets), tables)


def _checked_set(layout: Layout, set_name: str) -> _CheckedSet:
    """The manifest of `set_name` and the tables that the answer reads, each checked."""
    folder = manifest.set_folder(layout, set_name)
    if not folder.is_dir():
        raise AsOfRefused(f"{folder} is not a folder")
    try:
        path = manifest.find_manifest(layout, set_name)
    except (FileNotFoundError, ValueError) as error:
        # Each names the folder, the file or the versions.
        raise AsOfRefused(str(error)) from error
    data = path.read_bytes()
    try:
        listed = json.loads(data)
    except ValueError as error:
        raise AsOfRefused(f"{path} is not JSON: {error}") from error
    outputs = {entry["path"]: entry for entry in listed["outputs"]}
    tables = {
        name: _checked_table(layout, folder / f"{name}.parquet", outputs, path)
        for name in _SET_TABLES[set_name]
    }
    used = ManifestUsed(set_name, path, hashlib.sha256(data).hexdigest())
    return _CheckedSet(set_name, used, listed, tables)


def _checked_table(
    layout: Layout, path: Path, outputs: dict[str, dict], manifest_path: Path
) -> pa.Table:
    """The table in `path`, read once as bytes. Its size, SHA-256 and stamp must equal its
    entry in the manifest, and the table is parsed from the same bytes."""
    entry = outputs.get(path.relative_to(layout.root).as_posix())
    if entry is None:
        raise AsOfRefused(f"{path} is not listed in {manifest_path}")
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise AsOfRefused(f"{path} does not exist") from None
    if len(data) != entry["bytes"]:
        raise AsOfRefused(
            f"{path} has {len(data)} bytes, and {manifest_path} lists {entry['bytes']}"
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry["sha256"]:
        raise AsOfRefused(
            f"{path} has SHA-256 {digest}, and {manifest_path} lists {entry['sha256']}"
        )
    # The stamp and the table come from the checked bytes, never from a second read of the file.
    stamp = read_stamp(pa.BufferReader(data))
    listed = {key: entry[key] for key in STAMP_KEYS}
    if stamp != listed:
        raise AsOfRefused(f"{path} has the stamp {stamp}, and {manifest_path} lists {listed}")
    return pq.read_table(pa.BufferReader(data))


def _check_builds_on(layout: Layout, tables_set: _CheckedSet, stage4_set: _CheckedSet) -> None:
    """Refuse unless the `stage4` manifest builds on the `tables` manifest that was checked."""
    builds_on = stage4_set.listed.get("builds_on") or {}
    expected = {
        "path": tables_set.used.path.relative_to(layout.root).as_posix(),
        "sha256": tables_set.used.sha256,
    }
    if {key: builds_on.get(key) for key in expected} != expected:
        raise AsOfRefused(
            f"{stage4_set.used.path} builds on {builds_on.get('path')} with SHA-256"
            f" {builds_on.get('sha256')}, but {tables_set.used.path} has SHA-256"
            f" {tables_set.used.sha256}"
        )


def _held_filings(sets: tuple[_CheckedSet, ...]) -> pa.Table:
    """Each held filing of both `filings` tables: its accession, `known_from` and `held_in`.

    The `filings` tables hold one row for each fetched filing, a few hundred at most, so
    `known_from` reads them row by row. The large tables are matched to this one with
    `pyarrow.compute`.
    """
    columns = ["accession_number", "outcome", "last_modified_at", "fetched_at"]
    rows = [
        {
            "accession_number": filing["accession_number"],
            "known_from": moment,
            "held_in": _SET_HELD_IN[checked.name],
        }
        for checked in sets
        for filing in checked.tables["filings"].select(columns).to_pylist()
        if (moment := known_from(filing)) is not None
    ]
    return pa.Table.from_pylist(rows, schema=_HELD_SCHEMA)


def _answer_part(
    name: str, table: pa.Table, set_held_in: str, held: pa.Table, cutoff: pa.Scalar
) -> pa.Table:
    """The rows of one stored table whose `known_from` is at or before `cutoff`, with every
    stored column unchanged, then `known_from`, then `held_in` (except for `links`, which
    stores its `held_in`: C9)."""
    found = pc.index_in(
        table["accession_number"], value_set=held["accession_number"].combine_chunks()
    )
    known = pc.take(held["known_from"], found)
    if name == "index":
        # A filing that we do not hold: the index file listed the row by then.
        known = pc.coalesce(known, table["index_last_modified_at"])
        held_in = pc.coalesce(pc.take(held["held_in"], found), pa.scalar(HELD_IN_INDEX))
    else:
        held_in = pa.repeat(set_held_in, table.num_rows)
    answered = table.replace_schema_metadata(None).append_column(
        pa.field("known_from", _TIMESTAMP), known
    )
    if name != "links":
        answered = answered.append_column(pa.field("held_in", pa.string()), held_in)
    # A null `known_from` is a filing that we do not hold: the filter drops its rows.
    return answered.filter(pc.less_equal(known, cutoff))
