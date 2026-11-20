"""The `verify` command: a manifest checked against the root, in three parts.

1. Files: each listed file is there with its listed size and SHA-256, no unlisted file sits in a
   checked folder, and each output carries its listed stamp.
2. Binding: each record hash, and each ledger hash of `fetches` and `refetches`, ties to a
   listed input. This covers every row.
3. Re-derivation: a seeded sample of rows of each records table is derived again, with the
   steps' own code, from the bytes of the listed inputs, hashed as they are read.

Parts 2 and 3 run only for a manifest that lists inputs. Each part reads the root in place and
writes nothing. A `stage4` manifest has its own checks, in `verify_stage4`. This module does not
import `requests`.
"""

import hashlib
import json
import random
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sec_filing_data import index, sample
from sec_filing_data.facts import extract_facts, fact_rows, in_fact_forms
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import fetch_rows, last_ok, parse_ledger
from sec_filing_data.manifest import MANIFEST_FORMAT, STAGE4_SET, files_under, sha256_of
from sec_filing_data.ownership import extract_ownership, ownership_form, ownership_rows
from sec_filing_data.provenance import filing_times, record_provenance
from sec_filing_data.submissions import FilingRecords, filing_records
from sec_filing_data.tables import STAMP_KEYS, as_table_rows, read_stamp

VERIFY_SEED = 20261119
DEFAULT_ROWS = 20
# The tables whose records name the hash of the file they came from.
RECORDS_TABLES = ("index", "filings", "parties", "documents", "facts", "ownership")

OK = "ok"
NO_INPUTS = "not run, no inputs listed"


def run_verify(
    layout: Layout, manifest_path: Path, *, rows: int = DEFAULT_ROWS, seed: int = VERIFY_SEED
) -> tuple[int, list[str]]:
    """Check the root against the manifest. Give the exit code and one line for each check.

    The exit code is 0 when each line is `ok` or `not run`, and 1 otherwise. A manifest that is
    not a readable manifest of format 1 gives one line. So does a root that is not the
    manifest's root, after the seed line.
    """
    try:
        manifest = _read_manifest(manifest_path)
    except OSError as error:
        return 1, [f"manifest: {manifest_path}: {error.strerror}"]
    except ValueError as error:
        return 1, [f"manifest: {manifest_path}: {error}"]
    lines = [f"seed: {seed}"]
    root = str(layout.root.absolute())
    if root != manifest.get("root"):
        lines.append(f"files: --out {root} differs from the manifest root {manifest.get('root')}")
        return 1, lines
    if manifest.get("set") == STAGE4_SET:
        # `verify_stage4` imports this module's checks, as `ownership.extract_ownership` imports
        # its parsers, so the import sits here and not at the top of the module.
        from sec_filing_data import verify_stage4

        lines += verify_stage4.check(layout, manifest, rows=rows, seed=seed)
    else:
        lines.append(guarded("files", partial(check_files, layout, manifest)))
        if "inputs" in manifest:
            lines += check_binding(layout, manifest)
            lines += rederive(layout, manifest, rows=rows, seed=seed)
        else:
            lines += [f"binding: {NO_INPUTS}", f"rederive: {NO_INPUTS}"]
    return (0 if all(_passes(line) for line in lines) else 1), lines


def _read_manifest(path: Path) -> dict:
    """The manifest at `path`. A file that is not a manifest of format 1 raises `ValueError`."""
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("not a JSON object")
    if manifest.get("manifest_format") != MANIFEST_FORMAT:
        raise ValueError(f"manifest_format is {manifest.get('manifest_format')!r}, not 1")
    return manifest


def guarded(label: str, check: Callable[[], str]) -> str:
    """The line `<label>: <result>`, where `check` gives the result: `ok`, or the failure.

    A check that raises gives `failed: <ExceptionType>: <message>`, so one table that cannot
    be read does not stop the others.
    """
    try:
        result = check()
    except Exception as error:
        result = failure(error)
    return f"{label}: {result}"


def failure(error: Exception) -> str:
    return f"failed: {type(error).__name__}: {error}"


def _passes(line: str) -> bool:
    """The seed line, and a line whose result is `ok`, `ok, <n> rows` or `not run`, pass."""
    if line.startswith("seed: "):
        return True
    result = line.partition(": ")[2]
    return result == OK or result.startswith(f"{OK}, ") or result.startswith("not run")


# Part 1


def check_files(layout: Layout, manifest: dict) -> str:
    """`ok`, or the first file failure, with the path as the manifest lists it."""
    outputs = manifest["outputs"]
    inputs = manifest.get("inputs", [])
    # An absolute path, as the zip is listed, replaces the root in the join.
    for entry in [*outputs, *inputs]:
        if (problem := content_problem(layout.root / entry["path"], entry)) is not None:
            return f"{entry['path']}: {problem}"
    checked = [(layout.root / manifest["set"], outputs)]
    if "inputs" in manifest:
        checked += [(layout.bytes_dir, inputs), (layout.refetch_dir, inputs)]
    for folder, listed in checked:
        names = {entry["path"] for entry in listed}
        for path in sorted(files_under(folder)):
            if (relative := path.relative_to(layout.root).as_posix()) not in names:
                return f"{relative}: not listed"
    for entry in outputs:
        if (problem := stamp_problem(layout.root / entry["path"], entry)) is not None:
            return f"{entry['path']}: {problem}"
    return OK


def content_problem(path: Path, entry: dict) -> str | None:
    """Why `path` is not the file that `entry` lists, or None when it is."""
    if not path.is_file():
        return "missing"
    size = path.stat().st_size
    if size != entry["bytes"]:
        return f"{size} bytes, listed {entry['bytes']}"
    if sha256_of(path) != entry["sha256"]:
        return "SHA-256 differs from the listed value"
    return None


def stamp_problem(path: Path, entry: dict) -> str | None:
    """Why the stamp in the table at `path` differs from `entry`, or None when it does not.

    A file that is not a table lists no stamp.
    """
    if path.suffix != ".parquet":
        return None
    stamp = read_stamp(path)
    for key in STAMP_KEYS:
        if stamp[key] != entry[key]:
            return f"stamp {key} {stamp[key]} differs from the listed {entry[key]}"
    return None


# Part 2


def check_binding(layout: Layout, manifest: dict) -> list[str]:
    """One line for each records table, then `fetches`, then `refetches`.

    A records hash must match some listed input. A ledger hash must match the input at its own
    path: so a file that shares its bytes with another is not covered by the other's hash.
    """
    try:
        inputs = {entry["path"]: entry for entry in manifest["inputs"]}
        listed = {entry["sha256"] for entry in inputs.values()}
        root = manifest["root"]
    except Exception as error:
        # No table can be checked without the listed inputs, so one line stands for the part.
        return [f"binding: {failure(error)}"]
    checks = {name: partial(records_result, layout, name, listed) for name in RECORDS_TABLES}
    checks["fetches"] = partial(fetches_result, layout, root, inputs)
    checks["refetches"] = partial(_refetches_result, layout, inputs)
    return [guarded(f"binding {name}", check) for name, check in checks.items()]


def records_result(layout: Layout, name: str, listed: set[str]) -> str:
    """`ok`, or the first source hash of `name` that no listed input has.

    Only `filings` has the hash in `sha256`, and only its `ok` rows have one.
    """
    path = layout.table(name)
    if name == "filings":
        column = "sha256"
        table = _ok_rows(pq.read_table(path, columns=["outcome", column]))
    else:
        column = "source_sha256"
        table = pq.read_table(path, columns=[column])
    # `unique` keeps the order of first appearance, and a null counts as a value.
    for value in pc.unique(table[column]).to_pylist():
        if value not in listed:
            return f"{column} {value} matches no listed input"
    return OK


def fetches_result(layout: Layout, root: str, inputs: dict[str, dict]) -> str:
    """`ok`, or the first `ok` row whose file is not the listed input at its path.

    `fetches.path` keeps the root as it was given, so it is compared with the manifest root.
    """
    table = pq.read_table(
        layout.table("fetches"), columns=["accession_number", "outcome", "sha256", "path"]
    )
    for row in _ok_rows(table).to_pylist():
        accession, path = row["accession_number"], row["path"]
        try:
            relative = Path(path).relative_to(root).as_posix()
        except ValueError:
            return f"{accession} {path} is not under {root}"
        if (problem := ledger_problem(inputs.get(relative), row["sha256"])) is not None:
            return f"{accession} {path} {problem}"
    return OK


def _refetches_result(layout: Layout, inputs: dict[str, dict]) -> str:
    """`ok`, or the first `ok` row whose kept refetch copy is not the listed input."""
    table = pq.read_table(
        layout.table("refetches"), columns=["accession_number", "outcome", "refetch_sha256"]
    )
    for row in _ok_rows(table).to_pylist():
        accession = row["accession_number"]
        relative = layout.refetched(accession).relative_to(layout.root).as_posix()
        if (problem := ledger_problem(inputs.get(relative), row["refetch_sha256"])) is not None:
            return f"{accession} {relative} {problem}"
    return OK


def _ok_rows(table: pa.Table) -> pa.Table:
    return table.filter(pc.equal(table["outcome"], OK))


def ledger_problem(listed: dict | None, sha256: str | None) -> str | None:
    """Why a listed input is not the file that a ledger hash names, or None when it is."""
    if listed is None:
        return "is not a listed input"
    if listed["sha256"] != sha256:
        return f"has the listed SHA-256 {listed['sha256']}, the ledger gives {sha256}"
    return None


# Part 3


class RederiveError(Exception):
    """A listed input whose bytes are not as listed, or a drawn row that the inputs do not give."""


def draw_positions(total: int, count: int, rng: random.Random) -> list[int]:
    """`count` positions of a table of `total` rows, sorted. A smaller table gives every row."""
    return sorted(rng.sample(range(total), min(count, total)))


def draw_index_positions(
    with_times: list[int], without: list[int], count: int, rng: random.Random
) -> list[int]:
    """`count // 2` positions from `with_times`, then the rest of `count` from `without`, sorted.

    A half with too few rows gives all of them, and the other half is not topped up.
    """
    drawn = rng.sample(with_times, min(count // 2, len(with_times)))
    drawn += rng.sample(without, min(count - count // 2, len(without)))
    return sorted(drawn)


def split_by_times(table: pa.Table) -> tuple[list[int], list[int]]:
    """The positions of the rows of `table` whose `fetched_at` is not null, and of the others.

    Positions count across the whole table, whatever its chunks.
    """
    # In pyarrow 25, `indices_nonzero` of a chunked array with no rows ends the process, so the
    # mask is made one array first.
    timed = pc.is_valid(table["fetched_at"]).combine_chunks()
    return pc.indices_nonzero(timed).to_pylist(), pc.indices_nonzero(pc.invert(timed)).to_pylist()


def rederive(layout: Layout, manifest: dict, *, rows: int, seed: int) -> list[str]:
    """One line for each records table: `ok, <n> rows`, or the first drawn row that the steps
    do not derive again from the listed inputs. Each table draws with its own
    `random.Random(seed)`.
    """
    try:
        sources = _Sources(layout, manifest["inputs"])
    except Exception as error:
        # No row can be derived without the sample and the fetch rows, so one line stands for
        # the part.
        return [f"rederive: {failure(error)}"]
    return [
        guarded(f"rederive {name}", partial(_rederive_table, sources, name, rows, seed))
        for name in RECORDS_TABLES
    ]


def _rederive_table(sources: _Sources, name: str, count: int, seed: int) -> str:
    """`ok, <n> rows`, or the first of the `n` drawn rows of `name` that is not derived again.

    `index` draws half of its rows from the rows with filing times: those whose `fetched_at`
    is not null.
    """
    table = pq.read_table(sources.layout.table(name))
    rng = random.Random(seed)
    if name == "index":
        with_times, without = split_by_times(table)
        positions = draw_index_positions(with_times, without, count, rng)
    else:
        positions = draw_positions(table.num_rows, count, rng)
    drawn = table.take(pa.array(positions, pa.int64())).to_pylist()
    for position, row in zip(positions, drawn, strict=True):
        if (problem := _row_problem(sources, name, row)) is not None:
            return f"row {position} of {row['accession_number']}: {problem}"
    return f"{OK}, {len(positions)} rows"


def _row_problem(sources: _Sources, name: str, row: dict) -> str | None:
    """Why `row` of table `name` is not derived again from the inputs, or None when it is."""
    try:
        derived = sources.derived_rows(name, row)
    except RederiveError as error:
        return str(error)
    except Exception as error:
        return failure(error)
    return None if row in derived else difference(row, derived)


def difference(row: dict, derived: list[dict]) -> str:
    """The first column in which `row` differs from the derived row nearest to it: the one that
    differs from it in the fewest columns."""
    if not derived:
        return "its filing gives no rows of this table"
    differing = [_differing_columns(row, other) for other in derived]
    columns, nearest = min(zip(differing, derived, strict=True), key=lambda pair: len(pair[0]))
    if not columns:
        return f"its columns {list(row)} differ from the derived {list(nearest)}"
    column = columns[0]
    return f"column {column}: {row.get(column)!r} in the table, {nearest.get(column)!r} derived"


def _differing_columns(row: dict, other: dict) -> list[str]:
    return [column for column in {**row, **other} if row.get(column) != other.get(column)]


class _Sources:
    """The listed inputs of a manifest, and what the steps derive from them.

    Each input is read through `read_listed`. The sample is drawn again from the `index` input
    with the committed sample seed, never read from `sample.parquet`. The fetch rows are built
    again from the Stage 1 ledger input.
    """

    def __init__(self, layout: Layout, inputs: list[dict]) -> None:
        self.layout = layout
        self._bytes: dict[str, bytes] = {}
        self._filings: dict[tuple[str, str | None], FilingRecords] = {}
        self._derived: dict[tuple[str, str, str | None], list[dict]] = {}
        # Inputs that share a hash have equal bytes, so either serves.
        self._by_sha256: dict[str, dict] = {}
        for entry in inputs:
            self._by_sha256.setdefault(entry["sha256"], entry)
        zip_entry = _input_where(inputs, "kind", "index")
        self.index_sha256 = zip_entry["sha256"]
        # The constants are read here, at call time: the tests patch them for the fixture zip.
        lines = index.parse_index(
            self.read_listed(zip_entry),
            sha256=index.INDEX_SHA256,
            size=index.INDEX_SIZE,
            label=zip_entry["path"],
        )
        self.index_lines = {line["line_number"]: line for line in lines}
        drawn = sample.draw_sample(lines)
        self.sample = {row["accession_number"]: row for row in drawn}
        ledger = _input_where(inputs, "path", layout.ledger.relative_to(layout.root).as_posix())
        records = parse_ledger(self.read_listed(ledger))
        self.fetched = {row["accession_number"]: row for row in fetch_rows(layout, drawn, records)}
        self.ok_records = last_ok(records)

    def read_listed(self, entry: dict) -> bytes:
        """The bytes of a listed input. Its file is read once, and the bytes that were read are
        hashed and given. Bytes whose SHA-256 differs from the entry raise `RederiveError`.

        Bytes are kept by SHA-256, so a file shared by many rows is read once.
        """
        sha256 = entry["sha256"]
        if sha256 not in self._bytes:
            # The zip is listed by its absolute path, every other input by its path under the root.
            listed = entry["path"]
            path = Path(listed) if entry["kind"] == "index" else self.layout.root / listed
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != sha256:
                raise RederiveError(f"{listed}: SHA-256 differs from the listed value")
            self._bytes[sha256] = data
        return self._bytes[sha256]

    def raw(self, sha256: str | None) -> bytes | None:
        """The bytes of the listed input whose SHA-256 is `sha256`, or None for a null hash."""
        if sha256 is None:
            return None
        entry = self._by_sha256.get(sha256)
        if entry is None:
            raise RederiveError(f"no listed input has SHA-256 {sha256}")
        return self.read_listed(entry)

    def derived_rows(self, name: str, row: dict) -> list[dict]:
        """The rows of table `name` that the steps derive for the filing of `row`, as the table
        reads them back. A row of `index` derives one row: its own line of the zip."""
        if name == "index":
            return as_table_rows(name, [self._index_row(row)])
        accession = row["accession_number"]
        sha256 = row["sha256" if name == "filings" else "source_sha256"]
        key = (name, accession, sha256)
        if key not in self._derived:
            self._derived[key] = as_table_rows(name, self._filing_rows(name, accession, sha256))
        return self._derived[key]

    def _index_row(self, row: dict) -> dict:
        """The parsed line of `row`. When its accession is sampled, the line also takes the
        times of its filing, as `envelopes` gives them."""
        if row["source_sha256"] != self.index_sha256:
            raise RederiveError(
                f"source_sha256 {row['source_sha256']} is not the SHA-256 of the listed index input"
            )
        line = self.index_lines.get(row["line_number"])
        if line is None:
            raise RederiveError(f"the index input has no data line {row['line_number']}")
        accession = line["accession_number"]
        if accession not in self.sample:
            return line
        # The filing's bytes are found by the hash of its fetch row, from the Stage 1 ledger.
        filing = self.filing(accession, self.fetched[accession]["sha256"]).filing
        return {**line, **filing_times(filing)}

    def filing(self, accession: str, sha256: str | None) -> FilingRecords:
        """The `filings`, `parties` and `documents` rows of a sampled filing, from the listed
        input whose SHA-256 is `sha256`."""
        key = (accession, sha256)
        if key not in self._filings:
            sampled = self.sample.get(accession)
            if sampled is None:
                raise RederiveError("its accession is not in the sample")
            self._filings[key] = filing_records(
                sampled, self.fetched[accession], self.raw(sha256), self.ok_records.get(accession)
            )
        return self._filings[key]

    def _filing_rows(self, name: str, accession: str, sha256: str | None) -> list[dict]:
        """The rows of table `name` that the steps write for one sampled filing, from the
        listed input whose SHA-256 is `sha256`."""
        records = self.filing(accession, sha256)
        if name == "filings":
            return [records.filing]
        if name == "parties":
            return records.parties
        if name == "documents":
            return records.documents
        form_type = self.sample[accession]["form_type"]
        outcome = self.fetched[accession]["outcome"]
        # The steps copy the provenance of the `filings` row as the table reads it back.
        provenance = record_provenance(as_table_rows("filings", [records.filing])[0])
        raw = self.raw(sha256)
        if name == "facts":
            if not in_fact_forms(form_type):
                return []
            return fact_rows(accession, extract_facts(outcome, raw), provenance)
        form = ownership_form(form_type)
        if form is None:
            return []
        extraction = extract_ownership(form, outcome, raw)
        return ownership_rows(accession, form_type, extraction, provenance)


def _input_where(inputs: list[dict], key: str, value: str) -> dict:
    """The first listed input whose `key` is `value`."""
    found = next((entry for entry in inputs if entry[key] == value), None)
    if found is None:
        raise RederiveError(f"no listed input has {key} {value}")
    return found
