"""The `verify` command: a manifest checked against the root, in three parts.

1. Files: each listed file is there with its listed size and SHA-256, no unlisted file sits in a
   checked folder, and each output carries its listed stamp.
2. Binding: each record hash, and each ledger hash of `fetches` and `refetches`, ties to a
   listed input. This covers every row.
3. Re-derivation: a seeded sample of rows is derived again from the hashed bytes (not built yet).

Parts 2 and 3 run only for a manifest that lists inputs. Each part reads the root in place and
writes nothing. This module does not import `requests`.
"""

import json
from collections.abc import Callable
from functools import partial
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from sec_filing_data.layout import Layout
from sec_filing_data.manifest import MANIFEST_FORMAT, files_under, sha256_of
from sec_filing_data.tables import STAMP_KEYS, read_stamp

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
    lines.append(_guarded("files", partial(check_files, layout, manifest)))
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


def _guarded(label: str, check: Callable[[], str]) -> str:
    """The line `<label>: <result>`, where `check` gives the result: `ok`, or the failure.

    A check that raises gives `failed: <ExceptionType>: <message>`, so one table that cannot
    be read does not stop the others.
    """
    try:
        result = check()
    except Exception as error:
        result = _failure(error)
    return f"{label}: {result}"


def _failure(error: Exception) -> str:
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
        if (problem := _content_problem(layout.root / entry["path"], entry)) is not None:
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
        if (problem := _stamp_problem(layout.root / entry["path"], entry)) is not None:
            return f"{entry['path']}: {problem}"
    return OK


def _content_problem(path: Path, entry: dict) -> str | None:
    """Why `path` is not the file that `entry` lists, or None when it is."""
    if not path.is_file():
        return "missing"
    size = path.stat().st_size
    if size != entry["bytes"]:
        return f"{size} bytes, listed {entry['bytes']}"
    if sha256_of(path) != entry["sha256"]:
        return "SHA-256 differs from the listed value"
    return None


def _stamp_problem(path: Path, entry: dict) -> str | None:
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
        return [f"binding: {_failure(error)}"]
    checks = {name: partial(_records_result, layout, name, listed) for name in RECORDS_TABLES}
    checks["fetches"] = partial(_fetches_result, layout, root, inputs)
    checks["refetches"] = partial(_refetches_result, layout, inputs)
    return [_guarded(f"binding {name}", check) for name, check in checks.items()]


def _records_result(layout: Layout, name: str, listed: set[str]) -> str:
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


def _fetches_result(layout: Layout, root: str, inputs: dict[str, dict]) -> str:
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
        if (problem := _ledger_problem(inputs.get(relative), row["sha256"])) is not None:
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
        if (problem := _ledger_problem(inputs.get(relative), row["refetch_sha256"])) is not None:
            return f"{accession} {relative} {problem}"
    return OK


def _ok_rows(table: pa.Table) -> pa.Table:
    return table.filter(pc.equal(table["outcome"], OK))


def _ledger_problem(listed: dict | None, sha256: str | None) -> str | None:
    """Why a listed input is not the file that a ledger hash names, or None when it is."""
    if listed is None:
        return "is not a listed input"
    if listed["sha256"] != sha256:
        return f"has the listed SHA-256 {listed['sha256']}, the ledger gives {sha256}"
    return None


# Part 3


def rederive(layout: Layout, manifest: dict, *, rows: int, seed: int) -> list[str]:
    """Part 3: derive a seeded sample of rows again from the hashed bytes. Not built: no lines."""
    return []
