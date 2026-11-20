"""The `verify` checks of a `stage4` manifest: the three parts of the Stage 3 command.

1. Files: each listed file is there with its listed size and SHA-256, no unlisted file sits in
   `stage4/tables/` or `stage4/bytes/`, and each output carries its listed stamp. The `tables`
   manifest that `builds_on` names has its listed SHA-256, and each `tables/` file and each
   sampled amendment's byte file that Stage 4 reads is the file that manifest lists.
2. Binding: each source hash of the Stage 4 tables, and each ledger hash of `fetches`, ties to a
   listed input. A `links` row binds to the inputs of the place that holds its filing.
3. Re-derivation: the whole `partners` table is chosen again, and a seeded sample of rows of
   each of BINDING_TABLES is derived again, with the steps' own code, from the bytes of the
   listed files, hashed as they are read.

`verify.run_verify` calls `check` for a manifest whose set is `stage4`. Each part reads the root in
place and writes nothing. This module does not import `requests`.
"""

import hashlib
import json
import random
from functools import cached_property, partial
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from sec_filing_data import verify
from sec_filing_data.amendments import is_amendment
from sec_filing_data.layout import Layout
from sec_filing_data.ledger import last_ok, parse_ledger
from sec_filing_data.links import (
    HELD_IN_PARTNER,
    HELD_IN_SAMPLE,
    LinkContext,
    amendment_filings,
    link_context,
    link_row,
)
from sec_filing_data.manifest import files_under, sha256_of
from sec_filing_data.partner_tables import PartnerRecords, partner_records
from sec_filing_data.partners import choose_partners, distinct_partners, partner_fetch_rows
from sec_filing_data.tables import as_table_rows, read_table

# The files of `tables/` that Stage 4 reads.
STAGE4_READS = ("index", "sample", "filings", "parties")
# The Stage 4 tables whose records name the hash of the file they came from.
BINDING_TABLES = ("filings", "parties", "documents", "ownership", "links")

# The kind of the listed inputs that are submission files.
SUBMISSION = "submission"


def check(layout: Layout, manifest: dict, *, rows: int, seed: int) -> list[str]:
    """The lines of a `stage4` manifest after the seed line: `files`, one `binding` line for
    each of BINDING_TABLES, `binding fetches`, `rederive partners`, then one `rederive` line
    for each of BINDING_TABLES, which draws `rows` rows with `seed`.
    """
    return [
        verify.guarded("files", partial(check_files, layout, manifest)),
        *check_binding(layout, manifest),
        *rederive(layout, manifest, rows=rows, seed=seed),
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


# Part 3


def rederive(layout: Layout, manifest: dict, *, rows: int, seed: int) -> list[str]:
    """`rederive partners`, then one line for each of BINDING_TABLES: `ok, <n> rows`, or the
    first row that the steps do not derive again from the hashed files. Each table draws with
    its own `random.Random(seed)`.
    """
    try:
        sources = _Sources(layout, manifest)
    except Exception as error:
        # No row can be derived without the listed files, so one line stands for the part.
        return [f"rederive: {verify.failure(error)}"]
    checks = {"partners": partial(_partners_result, sources)}
    for name in BINDING_TABLES:
        checks[name] = partial(_rederive_table, sources, name, rows, seed)
    return [verify.guarded(f"rederive {name}", check) for name, check in checks.items()]


def _partners_result(sources: _Sources) -> str:
    """`ok, <n> rows` when the stored `partners` table is the derived one, row for row. Else the
    row counts, stored against derived, or the first row that differs."""
    stored = read_table(sources.view, "partners").to_pylist()
    derived = sources.partners
    if len(stored) != len(derived):
        return f"rows: {len(stored)} against {len(derived)}"
    for position, (row, other) in enumerate(zip(stored, derived, strict=True)):
        if row != other:
            return f"row {position} of {row['accession_number']}: {verify.difference(row, [other])}"
    return f"{verify.OK}, {len(stored)} rows"


def _rederive_table(sources: _Sources, name: str, count: int, seed: int) -> str:
    """`ok, <n> rows`, or the first of the `n` drawn rows of `name` that is not derived again."""
    table = read_table(sources.view, name)
    positions = verify.draw_positions(table.num_rows, count, random.Random(seed))
    drawn = table.take(pa.array(positions, pa.int64())).to_pylist()
    for position, row in zip(positions, drawn, strict=True):
        if (problem := _row_problem(sources, name, row)) is not None:
            return f"row {position} of {row['accession_number']}: {problem}"
    return f"{verify.OK}, {len(positions)} rows"


def _row_problem(sources: _Sources, name: str, row: dict) -> str | None:
    """Why `row` of table `name` is not derived again from the files, or None when it is."""
    try:
        derived = sources.derived_rows(name, row)
    except verify.RederiveError as error:
        return str(error)
    except Exception as error:
        return verify.failure(error)
    return None if row in derived else verify.difference(row, derived)


class _Sources:
    """The files that part 3 reads, and what the steps derive from them.

    Each file is read once, through `read_listed`, and the bytes that were read are hashed and
    parsed. The Stage 4 bytes and ledger are listed in the `stage4` manifest. The `tables/`
    files and the sampled bytes are listed in the `tables` manifest that `builds_on` names, and
    the bytes of that manifest are hashed against `builds_on` before they are parsed. The
    partners are chosen again from those files, never read from `partners.parquet`, and the
    fetch rows are built again from the Stage 4 ledger. Each value is derived when a line first
    needs it, so a file that no drawn row needs is not read.
    """

    def __init__(self, layout: Layout, manifest: dict) -> None:
        self.layout = layout
        self.view = layout.stage4_view
        self._bytes: dict[str, bytes] = {}
        self._rows: dict[str, list[dict]] = {}
        self._records: dict[str, PartnerRecords] = {}
        builds_on = manifest["builds_on"]
        self._tables_path = builds_on["path"]
        tables = json.loads(self.read_listed(builds_on))
        self._inputs = {entry["path"]: entry for entry in manifest["inputs"]}
        self._outputs = {entry["path"]: entry for entry in tables["outputs"]}
        self._sampled = {
            entry["path"]: entry for entry in tables["inputs"] if entry["kind"] == SUBMISSION
        }
        # Inputs that share a hash have equal bytes, so either serves.
        self._by_sha256: dict[str, dict] = {}
        for entry in [*self._inputs.values(), *self._sampled.values()]:
            self._by_sha256.setdefault(entry["sha256"], entry)

    def read_listed(self, entry: dict) -> bytes:
        """The bytes of a listed file. Its file is read once, and the bytes that were read are
        hashed and given. Bytes whose SHA-256 differs from the entry raise `RederiveError`.

        Bytes are kept by SHA-256, so a file shared by many rows is read once.
        """
        sha256 = entry["sha256"]
        if sha256 not in self._bytes:
            listed = entry["path"]
            data = (self.layout.root / listed).read_bytes()
            if hashlib.sha256(data).hexdigest() != sha256:
                raise verify.RederiveError(f"{listed}: SHA-256 differs from the listed value")
            self._bytes[sha256] = data
        return self._bytes[sha256]

    def raw(self, sha256: str | None) -> bytes | None:
        """The bytes of the listed input whose SHA-256 is `sha256`, or None for a null hash."""
        if sha256 is None:
            return None
        entry = self._by_sha256.get(sha256)
        if entry is None:
            raise verify.RederiveError(f"no listed input has SHA-256 {sha256}")
        return self.read_listed(entry)

    def stage3_rows(self, name: str) -> list[dict]:
        """The rows of `tables/<name>`, parsed from the bytes that the `tables` manifest lists."""
        if name not in self._rows:
            path = _relative(self.layout, self.layout.table(name))
            entry = self._outputs.get(path)
            if entry is None:
                raise verify.RederiveError(f"{path} is not listed in {self._tables_path}")
            data = self.read_listed(entry)
            self._rows[name] = pq.read_table(pa.BufferReader(data)).to_pylist()
        return self._rows[name]

    def _read_sampled(self, accession: str) -> bytes | None:
        """The listed bytes of a sampled filing, or None when the `tables` manifest lists none."""
        entry = self._sampled.get(_relative(self.layout, self.layout.submission(accession)))
        return None if entry is None else self.read_listed(entry)

    @cached_property
    def partners(self) -> list[dict]:
        """The `partners` rows that the sampled filings choose, as the table reads them back."""
        chosen = choose_partners(
            self.stage3_rows("index"), self.stage3_rows("sample"), self._read_sampled
        )
        return as_table_rows("partners", chosen)

    @cached_property
    def _distinct(self) -> dict[str, dict]:
        """The first `partners` row of each partner, by accession, in accession order."""
        return {row["accession_number"]: row for row in distinct_partners(self.partners)}

    @cached_property
    def _ledger(self) -> list[dict]:
        """The records of the Stage 4 ledger input."""
        path = _relative(self.layout, self.layout.stage4_ledger)
        entry = self._inputs.get(path)
        if entry is None:
            raise verify.RederiveError(f"{path} is not a listed input")
        return parse_ledger(self.read_listed(entry))

    @cached_property
    def _fetched(self) -> dict[str, dict]:
        """The `fetches` row of each partner, by accession, from the Stage 4 ledger."""
        rows = partner_fetch_rows(self.layout, self.partners, self._ledger)
        return {row["accession_number"]: row for row in rows}

    @cached_property
    def _ok_records(self) -> dict[str, dict]:
        return last_ok(self._ledger)

    def partner(self, accession: str) -> PartnerRecords:
        """The rows of one partner, from the listed input whose SHA-256 is its fetch row's."""
        if accession not in self._records:
            partner = self._distinct.get(accession)
            if partner is None:
                raise verify.RederiveError("its accession is not a partner")
            fetched = self._fetched[accession]
            self._records[accession] = partner_records(
                partner, fetched, self.raw(fetched["sha256"]), self._ok_records.get(accession)
            )
        return self._records[accession]

    @cached_property
    def _sample_filings(self) -> dict[str, dict]:
        """The rows of `tables/filings` by accession."""
        return {row["accession_number"]: row for row in self.stage3_rows("filings")}

    @cached_property
    def context(self) -> LinkContext:
        """The context of the `links` rows (C13): `tables/index`, `tables/filings` and
        `tables/parties`, and the partner rows derived again, in accession order."""
        records = [self.partner(accession) for accession in self._distinct]
        filings = {
            HELD_IN_SAMPLE: self.stage3_rows("filings"),
            HELD_IN_PARTNER: as_table_rows("filings", [parts.filing for parts in records]),
        }
        parties = {
            HELD_IN_SAMPLE: self.stage3_rows("parties"),
            HELD_IN_PARTNER: as_table_rows(
                "parties", [row for parts in records for row in parts.parties]
            ),
        }
        return link_context(self.stage3_rows("index"), filings, parties)

    def derived_rows(self, name: str, row: dict) -> list[dict]:
        """The rows of table `name` that the steps derive for the filing of `row`, as the table
        reads them back."""
        if name == "links":
            return as_table_rows(name, self._link_rows(row))
        parts = self.partner(row["accession_number"])
        if name == "filings":
            return as_table_rows(name, [parts.filing])
        if name == "parties":
            return as_table_rows(name, parts.parties)
        if name == "documents":
            return as_table_rows(name, parts.documents)
        return as_table_rows(name, parts.ownership)

    def _link_rows(self, row: dict) -> list[dict]:
        """The `links` rows of the filing of `row`, held where `row` says. A filing that is not
        an `ok` amendment gives none. The bytes are the listed input whose SHA-256 is the row's
        `source_sha256`."""
        held_in = row["held_in"]
        filing = self._held_filing(held_in, row["accession_number"])
        return [
            link_row(amendment, held_in, self.raw(row["source_sha256"]), self.context)
            for amendment in amendment_filings([filing])
        ]

    def _held_filing(self, held_in: str, accession: str) -> dict:
        """The `filings` row of a held filing, with the table's types: the hashed `tables/filings`
        row of a sampled filing, or the derived row of a partner."""
        if held_in == HELD_IN_PARTNER:
            return as_table_rows("filings", [self.partner(accession).filing])[0]
        if held_in != HELD_IN_SAMPLE:
            raise verify.RederiveError(
                f"held_in {held_in!r} is neither {HELD_IN_SAMPLE!r} nor {HELD_IN_PARTNER!r}"
            )
        filing = self._sample_filings.get(accession)
        if filing is None:
            raise verify.RederiveError("its accession is not in tables/filings")
        return filing
