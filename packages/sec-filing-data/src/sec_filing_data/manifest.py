"""The manifest of one table set: each file of the set folder with its size and SHA-256.

The manifest of `tables` also lists the inputs that `rebuild` reads. The manifest of `stage4`
lists the files under `stage4/bytes/` and the Stage 4 ledger, and names the `tables` manifest that
it builds on. The name of a manifest holds the first 12 characters of the code version, so
manifests of two code versions never share a name.
"""

import hashlib
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from sec_filing_data import version
from sec_filing_data.layout import Layout
from sec_filing_data.tables import STAMP_KEYS, read_stamp

MANIFEST_FORMAT = 1
STAGE4_SET = "stage4"
SETS = ("tables", "tables-stage1", "tables-stage2", STAGE4_SET)
# The set that `rebuild` makes. Its manifest lists the inputs of `rebuild`, and it needs the zip.
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


def set_folder(layout: Layout, set_name: str) -> Path:
    """The folder of the table files of `set_name`."""
    return layout.stage4_tables if set_name == STAGE4_SET else layout.root / set_name


def set_version(folder: Path) -> str:
    """The one code version in the stamps of the `*.parquet` files of `folder`.

    Files of several versions raise `ValueError`, which names each version. A file that pyarrow
    cannot read raises `ValueError`, which names the file. A folder that is missing or holds no
    table raises `FileNotFoundError`.
    """
    versions = {_code_version(path) for path in folder.glob("*.parquet")}
    if not versions:
        raise FileNotFoundError(f"{folder} holds no table")
    if len(versions) > 1:
        named = ", ".join(sorted(versions))
        raise ValueError(f"{folder} holds tables of {len(versions)} code versions: {named}")
    return versions.pop()


def _code_version(path: Path) -> str:
    try:
        return read_stamp(path)["code_version"]
    except pa.ArrowException as error:
        # pyarrow's message does not name the file.
        raise ValueError(f"{path}: {error}") from error


def find_manifest(layout: Layout, set_name: str) -> Path:
    """The manifest of `set_name` under the code version of its table stamps.

    A manifest that does not exist raises `FileNotFoundError`. So do the errors of `set_version`.
    """
    path = manifest_path(layout, set_name, set_version(set_folder(layout, set_name)))
    if not path.is_file():
        raise FileNotFoundError(f"{path} does not exist")
    return path


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


def _listed(named: list[tuple[str, Path, str]]) -> list[dict]:
    """The input entries of `named` (name, file, kind), sorted by name."""
    return sorted((_input(*item) for item in named), key=lambda entry: entry["path"])


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
    return _listed(named)


def _stage4_inputs(layout: Layout) -> list[dict]:
    """The inputs of the Stage 4 tables that `stage4/` holds: the partner bytes and the ledger."""
    return _listed(
        [
            *(
                (_relative(layout, path), path, "submission")
                for path in files_under(layout.stage4_bytes)
            ),
            (_relative(layout, layout.stage4_ledger), layout.stage4_ledger, "ledger"),
        ]
    )


def _builds_on(layout: Layout) -> dict:
    """The `tables` manifest that the Stage 4 tables read from: its path and SHA-256."""
    path = find_manifest(layout, _LIVE_SET)
    return {"path": _relative(layout, path), "sha256": sha256_of(path)}


def build_manifest(
    layout: Layout, set_name: str, *, zip_path: Path | None, stamp: version.Stamp
) -> dict:
    """The manifest of the folder `set_name` under the root, as a dict.

    A `tables` manifest needs `zip_path`, and every other set takes none: else `ValueError`. A
    missing set folder, zip, ledger or `tables` manifest raises `FileNotFoundError`. The
    `stage4` manifest also raises `ValueError` when the files of `tables` name several versions.
    """
    if (problem := zip_problem(set_name, zip_path)) is not None:
        raise ValueError(problem)
    folder = set_folder(layout, set_name)
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
    elif set_name == STAGE4_SET:
        manifest["inputs"] = _stage4_inputs(layout)
        manifest["builds_on"] = _builds_on(layout)
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
