"""The `verify` checks of a `stage4` manifest: parts 1 and 2 of the Stage 3 command.

1. Files: each listed file is there with its listed size and SHA-256, no unlisted file sits in
   `stage4/tables/` or `stage4/bytes/`, and each output carries its listed stamp. The `tables`
   manifest that `builds_on` names has its listed SHA-256, and each `tables/` file and each
   sampled amendment's byte file that Stage 4 reads is the file that manifest lists.
2. Binding: each source hash of the Stage 4 tables, and each ledger hash of `fetches`, ties to a
   listed input. A `links` row binds to the inputs of the place that holds its filing.

`verify.run_verify` calls `check` for a manifest whose set is `stage4`. Each part reads the root in
place and writes nothing. This module does not import `requests`.
"""

import json
from functools import partial
from pathlib import Path

import pyarrow.parquet as pq

from sec_filing_data import verify
from sec_filing_data.amendments import is_amendment
from sec_filing_data.layout import Layout
from sec_filing_data.links import HELD_IN_PARTNER, HELD_IN_SAMPLE
from sec_filing_data.manifest import files_under, sha256_of

# The files of `tables/` that Stage 4 reads.
STAGE4_READS = ("index", "sample", "filings", "parties")
# The Stage 4 tables whose records name the hash of the file they came from.
BINDING_TABLES = ("filings", "parties", "documents", "ownership", "links")

# The kind of the listed inputs that are submission files.
SUBMISSION = "submission"


def check(layout: Layout, manifest: dict, *, rows: int, seed: int) -> list[str]:
    """The lines of a `stage4` manifest after the seed line: `files`, one `binding` line for
    each of BINDING_TABLES, then `binding fetches`.

    `rows` and `seed` are for the re-derivation of rows, which this module does not run yet.
    """
    return [
        verify.guarded("files", partial(check_files, layout, manifest)),
        *check_binding(layout, manifest),
    ]


# Part 1


def check_files(layout: Layout, manifest: dict) -> str:
    """`ok`, or the first file failure, with the path as the manifest lists it."""
    outputs, inputs = manifest["outputs"], manifest["inputs"]
    for entry in [*outputs, *inputs]:
        if (problem := verify.content_problem(layout.root / entry["path"], entry)) is not None:
            return f"{entry['path']}: {problem}"
    for folder, listed in ((layout.stage4_tables, outputs), (layout.stage4_bytes, inputs)):
        names = {entry["path"] for entry in listed}
        for path in sorted(files_under(folder)):
            if (relative := _relative(layout, path)) not in names:
                return f"{relative}: not listed"
    for entry in outputs:
        if (problem := verify.stamp_problem(layout.root / entry["path"], entry)) is not None:
            return f"{entry['path']}: {problem}"
    return _builds_on_problem(layout, manifest["builds_on"]) or verify.OK


def _builds_on_problem(layout: Layout, builds_on: dict) -> str | None:
    """Why the `tables` manifest that `builds_on` names is not as listed, or why a file that
    Stage 4 reads is not as that manifest lists it. None when all is as listed.

    A sampled amendment that was not fetched has no byte file and no listed input, and that is
    as listed.
    """
    named = builds_on["path"]
    path = layout.root / named
    if not path.is_file():
        return f"{named}: missing"
    if sha256_of(path) != builds_on["sha256"]:
        return f"{named}: SHA-256 differs from the listed value"
    tables = _read_tables_manifest(layout, builds_on)
    outputs = {entry["path"]: entry for entry in tables["outputs"]}
    for name in STAGE4_READS:
        file = layout.table(name)
        entry = outputs.get(_relative(layout, file))
        if entry is None or verify.content_problem(file, entry) is not None:
            return f"{_relative(layout, file)}: differs from {named}"
    inputs = {entry["path"]: entry for entry in tables["inputs"]}
    for accession in _sampled_amendments(layout):
        file = layout.submission(accession)
        if not _is_as_listed(file, inputs.get(_relative(layout, file))):
            return f"{_relative(layout, file)}: differs from {named}"
    return None


def _read_tables_manifest(layout: Layout, builds_on: dict) -> dict:
    return json.loads((layout.root / builds_on["path"]).read_text(encoding="utf-8"))


def _sampled_amendments(layout: Layout) -> list[str]:
    """The accessions of the `sample` rows whose form type is an amendment, in table order."""
    table = pq.read_table(layout.table("sample"), columns=["accession_number", "form_type"])
    return [row["accession_number"] for row in table.to_pylist() if is_amendment(row["form_type"])]


def _is_as_listed(path: Path, entry: dict | None) -> bool:
    """True when the file at `path` is the one that `entry` lists. No file and no entry agree."""
    if entry is None:
        return not path.exists()
    return verify.content_problem(path, entry) is None


def _relative(layout: Layout, path: Path) -> str:
    return path.relative_to(layout.root).as_posix()


# Part 2


def check_binding(layout: Layout, manifest: dict) -> list[str]:
    """One line for each of BINDING_TABLES, then `fetches`.

    A records hash must match some listed input. A ledger hash must match the input at its own
    path: so a file that shares its bytes with another is not covered by the other's hash.
    """
    try:
        inputs = {entry["path"]: entry for entry in manifest["inputs"]}
        listed = {entry["sha256"] for entry in inputs.values()}
        root = manifest["root"]
    except Exception as error:
        # No table can be checked without the listed inputs, so one line stands for the part.
        return [f"binding: {verify.failure(error)}"]
    view = layout.stage4_view
    checks = {
        name: (
            partial(_links_result, layout, manifest, listed)
            if name == "links"
            else partial(verify.records_result, view, name, listed)
        )
        for name in BINDING_TABLES
    }
    checks["fetches"] = partial(verify.fetches_result, view, root, inputs)
    return [verify.guarded(f"binding {name}", check) for name, check in checks.items()]


def _links_result(layout: Layout, manifest: dict, partner_listed: set[str]) -> str:
    """`ok`, or the first `links` row whose source hash no input of its place lists.

    A row held in `partner` binds to the Stage 4 inputs. A row held in `sample` binds to the
    `submission` inputs of the `builds_on` manifest, where the sampled bytes are listed.
    """
    tables = _read_tables_manifest(layout, manifest["builds_on"])
    listed = {
        HELD_IN_PARTNER: partner_listed,
        HELD_IN_SAMPLE: {
            entry["sha256"] for entry in tables["inputs"] if entry["kind"] == SUBMISSION
        },
    }
    table = pq.read_table(
        layout.stage4_view.table("links"), columns=["accession_number", "held_in", "source_sha256"]
    )
    for row in table.to_pylist():
        if row["source_sha256"] not in listed.get(row["held_in"], set()):
            return (
                f"source_sha256 {row['source_sha256']} of {row['accession_number']}"
                " matches no listed input"
            )
    return verify.OK
