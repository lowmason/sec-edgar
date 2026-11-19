"""The manifest of one table set: each file of the set folder with its size and SHA-256.

The manifest of `tables` also lists the inputs that `rebuild` reads. Its name holds the first
12 characters of the code version, so manifests of two code versions never share a name.
"""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

from sec_filing_data import version
from sec_filing_data.layout import Layout
from sec_filing_data.tables import STAMP_KEYS, read_stamp

MANIFEST_FORMAT = 1
SETS = ("tables", "tables-stage1", "tables-stage2")
# The set that `rebuild` makes. Only its manifest lists inputs, and it needs the zip.
_LIVE_SET = "tables"


def sha256_of(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def zip_problem(set_name: str, zip_path: Path | None) -> str | None:
    """Why `zip_path` does not fit `set_name`, or None when it fits."""
    if set_name == _LIVE_SET and zip_path is None:
        return f"--zip is required for --set {_LIVE_SET}"
    if set_name != _LIVE_SET and zip_path is not None:
        return f"--zip is only for --set {_LIVE_SET}"
    return None


def manifest_path(layout: Layout, set_name: str, commit: str) -> Path:
    return layout.manifests / f"{set_name}@{commit[:12]}.json"


def _relative(layout: Layout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


def files_under(folder: Path) -> list[Path]:
    """Every file under `folder`, at any depth. Give none when the folder is missing."""
    return [path for path in folder.rglob("*") if path.is_file()]


def _output(layout: Layout, path: Path) -> dict:
    entry = {
        "path": _relative(layout, path),
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
        "rows": None,
        **dict.fromkeys(STAMP_KEYS),
    }
    # A file of any other kind has no rows and no stamp: for example `.DS_Store` or a `.part`.
    if path.suffix == ".parquet":
        entry["rows"] = pq.read_metadata(path).num_rows
        entry.update(read_stamp(path))
    return entry


def _input(name: str, path: Path, kind: str) -> dict:
    return {"path": name, "kind": kind, "bytes": path.stat().st_size, "sha256": sha256_of(path)}


def _inputs(layout: Layout, zip_path: Path) -> list[dict]:
    """The inputs that `rebuild` reads. The zip is named by its absolute path."""
    ledgers = [layout.ledger]
    if layout.stage2_ledger.exists():
        ledgers.append(layout.stage2_ledger)
    named = [
        (str(zip_path.absolute()), zip_path, "index"),
        *((_relative(layout, path), path, "submission") for path in files_under(layout.bytes_dir)),
        *((_relative(layout, path), path, "ledger") for path in ledgers),
        *((_relative(layout, path), path, "refetch") for path in files_under(layout.refetch_dir)),
    ]
    return sorted((_input(*item) for item in named), key=lambda entry: entry["path"])


def build_manifest(
    layout: Layout, set_name: str, *, zip_path: Path | None, stamp: version.Stamp
) -> dict:
    """The manifest of the folder `set_name` under the root, as a dict.

    A `tables` manifest needs `zip_path`, and a frozen set takes none: else `ValueError`. A
    missing set folder, zip or ledger raises `FileNotFoundError`.
    """
    if (problem := zip_problem(set_name, zip_path)) is not None:
        raise ValueError(problem)
    folder = layout.root / set_name
    if not folder.is_dir():
        raise FileNotFoundError(f"{folder} is not a folder")
    manifest = {
        "manifest_format": MANIFEST_FORMAT,
        "set": set_name,
        "root": str(layout.root.absolute()),
        "written_by": {
            "code_version": stamp.code_version,
            "python_version": stamp.python_version,
            "pyarrow_version": stamp.pyarrow_version,
        },
        "outputs": sorted(
            (_output(layout, path) for path in files_under(folder)), key=lambda entry: entry["path"]
        ),
    }
    if zip_path is not None:
        manifest["inputs"] = _inputs(layout, zip_path)
    return manifest


def write_manifest(layout: Layout, set_name: str, *, zip_path: Path | None) -> Path:
    """Write the manifest of `set_name` under the current code version. Give its path.

    The whole manifest is built before the folder or the file exists, so a failure leaves
    nothing behind. A manifest that exists is never overwritten: `FileExistsError`.
    """
    stamp = version.current_stamp()
    manifest = build_manifest(layout, set_name, zip_path=zip_path, stamp=stamp)
    text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    path = manifest_path(layout, set_name, stamp.code_version)
    layout.manifests.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)
    return path
