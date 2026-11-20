"""`verify` on a `stage4` manifest, parts 1 and 2: the files of the manifest, and the binding of
each source hash of the Stage 4 tables to a listed input."""

import copy
import json
from collections.abc import Callable
from pathlib import Path

from sec_filing_data import manifest, verify_stage4, version
from sec_filing_data.manifest import sha256_of
from sec_filing_data.tables import read_table, write_table
from sec_filing_data.verify import RECORDS_TABLES, VERIFY_SEED

from tests.stage4_root import (
    PARTNER_13D_A1,
    PARTNER_D,
    SAMPLED_8K_A,
    SAMPLED_13D,
    SAMPLED_D_A,
    Stage4RootTestCase,
    write_both_manifests,
)
from tests.test_verify import ALL_OK as STAGE3_OK

SEED_LINE = f"seed: {VERIFY_SEED}"
# The lines before Part 3: the seed, the files line, then one binding line for each table.
OK_LINES = [
    SEED_LINE,
    "files: ok",
    "binding filings: ok",
    "binding parties: ok",
    "binding documents: ok",
    "binding ownership: ok",
    "binding links: ok",
    "binding fetches: ok",
]
FILES, LINKS = 1, 6


def with_line(label: str, result: str) -> list[str]:
    """OK_LINES with the line of `label` changed to `<label>: <result>`."""
    return [f"{label}: {result}" if line.startswith(f"{label}: ") else line for line in OK_LINES]


def changed(rows: list[dict], accession: str, **values) -> list[dict]:
    """`rows`, with `values` set in the row of `accession`."""
    return [{**row, **values} if row["accession_number"] == accession else row for row in rows]


class VerifyStage4TestCase(Stage4RootTestCase):
    def verify(self, manifest_path: Path) -> tuple[int, list[str]]:
        code, stdout, stderr = self.run_cli("verify", "--manifest", str(manifest_path))
        self.assertEqual(stderr, "")
        return code, stdout.splitlines()

    def assert_fails_with(self, manifest_path: Path, label: str, result: str) -> None:
        """Run `verify`. Expect exit 1, and OK_LINES with only the line of `label` changed."""
        code, lines = self.verify(manifest_path)

        self.assertEqual(code, 1)
        self.assertEqual(lines[: len(OK_LINES)], with_line(label, result))

    def assert_passes(self, manifest_path: Path) -> None:
        code, lines = self.verify(manifest_path)

        self.assertEqual((code, lines[: len(OK_LINES)]), (0, OK_LINES))

    def relative(self, path: Path) -> str:
        return path.relative_to(self.layout.root).as_posix()

    def tables_manifest_path(self) -> Path:
        return manifest.manifest_path(self.layout, "tables", version.current_checkout().commit)

    def rewrite(self, name: str, transform: Callable[[list[dict]], list[dict]]) -> None:
        """Write the Stage 4 table `name` again, with its rows changed by `transform`."""
        rows = read_table(self.layout.stage4_view, name).to_pylist()
        write_table(self.layout.stage4_view, name, transform(rows))

    def append_a_byte(self, path: Path) -> None:
        with path.open("ab") as handle:
            handle.write(b"\n")


class VerifyStage4PassTests(VerifyStage4TestCase):
    def test_an_untouched_stage4_root_passes(self):
        _, stage4_path = write_both_manifests(self)

        code, lines = self.verify(stage4_path)

        self.assertEqual(code, 0)
        self.assertEqual(lines[: len(OK_LINES)], OK_LINES)
        self.assertEqual(verify_stage4.STAGE4_READS, ("index", "sample", "filings", "parties"))
        self.assertEqual(
            verify_stage4.BINDING_TABLES, ("filings", "parties", "documents", "ownership", "links")
        )

    def test_the_tables_manifest_still_verifies(self):
        tables_path, _ = write_both_manifests(self)

        code, lines = self.verify(tables_path)

        self.assertEqual(code, 0)
        self.assertEqual(lines[: len(STAGE3_OK)], STAGE3_OK)
        rederived = lines[len(STAGE3_OK) :]
        self.assertEqual(
            [line.partition(": ")[0] for line in rederived],
            [f"rederive {name}" for name in RECORDS_TABLES],
        )
        for line in rederived:
            self.assertIn(": ok, ", line)

    def test_a_changed_original_byte_file_is_not_read(self):
        _, stage4_path = write_both_manifests(self)
        self.append_a_byte(self.layout.submission(SAMPLED_13D))

        self.assert_passes(stage4_path)

    def test_a_sampled_amendment_with_no_bytes_and_no_entry_passes(self):
        # A sampled amendment whose fetch failed has no bytes file, no input entry in the `tables`
        # manifest, and no `links` row.
        self.layout.submission(SAMPLED_8K_A).unlink()
        self.rewrite(
            "links", lambda rows: [r for r in rows if r["accession_number"] != SAMPLED_8K_A]
        )
        _, stage4_path = write_both_manifests(self)

        self.assert_passes(stage4_path)


class VerifyStage4FilesTests(VerifyStage4TestCase):
    def test_a_changed_partner_byte_fails(self):
        _, stage4_path = write_both_manifests(self)
        path = self.layout.partner_submission(PARTNER_D)
        listed = path.stat().st_size
        self.append_a_byte(path)

        self.assert_fails_with(
            stage4_path, "files", f"{self.relative(path)}: {listed + 1} bytes, listed {listed}"
        )

    def test_a_partner_byte_of_the_same_length_fails_on_its_hash(self):
        _, stage4_path = write_both_manifests(self)
        path = self.layout.partner_submission(PARTNER_D)
        data = path.read_bytes()
        path.write_bytes(data[:-1] + (b"x" if data[-1:] != b"x" else b"y"))

        self.assert_fails_with(
            stage4_path, "files", f"{self.relative(path)}: SHA-256 differs from the listed value"
        )

    def test_a_changed_output_table_fails(self):
        _, stage4_path = write_both_manifests(self)
        listed = next(
            entry["bytes"]
            for entry in json.loads(stage4_path.read_text(encoding="utf-8"))["outputs"]
            if entry["path"] == "stage4/tables/links.parquet"
        )
        # The rewrite keeps the stamp, so only the size or the hash of the file can show it.
        self.rewrite("links", lambda rows: changed(rows, SAMPLED_D_A, link_rule="x"))
        size = (self.layout.stage4_tables / "links.parquet").stat().st_size
        self.assertNotEqual(size, listed)

        self.assert_fails_with(
            stage4_path, "files", f"stage4/tables/links.parquet: {size} bytes, listed {listed}"
        )

    def test_a_changed_output_table_of_the_same_size_fails_on_its_hash(self):
        _, stage4_path = write_both_manifests(self)
        path = self.layout.stage4_tables / "partners.parquet"
        data = path.read_bytes()
        # One flipped bit after the 4-byte magic number keeps the size and the stamp.
        path.write_bytes(data[:4] + bytes([data[4] ^ 1]) + data[5:])

        self.assert_fails_with(
            stage4_path,
            "files",
            "stage4/tables/partners.parquet: SHA-256 differs from the listed value",
        )

    def test_an_unlisted_partner_file_fails(self):
        _, stage4_path = write_both_manifests(self)
        (self.layout.stage4_bytes / "extra.txt").write_bytes(b"extra")

        self.assert_fails_with(stage4_path, "files", "stage4/bytes/extra.txt: not listed")

    def test_an_unlisted_stage4_table_file_fails(self):
        _, stage4_path = write_both_manifests(self)
        (self.layout.stage4_tables / "extra.parquet.part").write_bytes(b"extra")

        self.assert_fails_with(
            stage4_path, "files", "stage4/tables/extra.parquet.part: not listed"
        )

    def test_a_stamp_that_differs_from_its_entry_fails(self):
        _, stage4_path = write_both_manifests(self)
        written = json.loads(stage4_path.read_text(encoding="utf-8"))
        # The file is as listed, and the stamp in it is not the stamp that the entry lists.
        entry = next(
            entry for entry in written["outputs"] if entry["path"].endswith("/links.parquet")
        )
        stamped = entry["table_format"]
        entry["table_format"] = "9"
        edited = self.layout.manifests / "edited.json"
        edited.write_text(json.dumps(written), encoding="utf-8")

        self.assert_fails_with(
            edited,
            "files",
            f"{entry['path']}: stamp table_format {stamped} differs from the listed 9",
        )

    def test_a_changed_index_table_fails(self):
        _, stage4_path = write_both_manifests(self)
        rows = read_table(self.layout, "index").to_pylist()
        rows[0]["company_name"] = "CHANGED CORP"
        write_table(self.layout, "index", rows)

        self.assert_fails_with(
            stage4_path,
            "files",
            f"tables/index.parquet: differs from {self.relative(self.tables_manifest_path())}",
        )

    def test_a_changed_tables_manifest_fails(self):
        tables_path, stage4_path = write_both_manifests(self)
        written = json.loads(tables_path.read_text(encoding="utf-8"))
        tables_path.write_text(json.dumps({**written, "note": "added"}), encoding="utf-8")

        self.assert_fails_with(
            stage4_path,
            "files",
            f"{self.relative(tables_path)}: SHA-256 differs from the listed value",
        )

    def test_a_missing_tables_manifest_fails(self):
        tables_path, stage4_path = write_both_manifests(self)
        tables_path.unlink()

        code, lines = self.verify(stage4_path)

        self.assertEqual(code, 1)
        self.assertEqual(lines[FILES], f"files: {self.relative(tables_path)}: missing")
        # A `links` row of the sample binds through that manifest, so its line fails too.
        self.assertTrue(
            lines[LINKS].startswith("binding links: failed: FileNotFoundError: "), lines[LINKS]
        )
        for position in set(range(len(OK_LINES))) - {FILES, LINKS}:
            self.assertEqual(lines[position], OK_LINES[position])

    def test_a_changed_sampled_amendment_byte_file_fails(self):
        tables_path, stage4_path = write_both_manifests(self)
        path = self.layout.submission(SAMPLED_D_A)
        self.append_a_byte(path)

        self.assert_fails_with(
            stage4_path,
            "files",
            f"{self.relative(path)}: differs from {self.relative(tables_path)}",
        )


class VerifyStage4BindingTests(VerifyStage4TestCase):
    def test_a_links_row_binds_by_its_set(self):
        # Before the `stage4` manifest, so that Part 1 still passes.
        self.rewrite("links", lambda rows: changed(rows, SAMPLED_D_A, held_in="partner"))
        _, stage4_path = write_both_manifests(self)

        # The bytes of SAMPLED_D_A are a listed input of the `tables` manifest, not of `stage4`.
        sha256 = sha256_of(self.layout.submission(SAMPLED_D_A))
        self.assert_fails_with(
            stage4_path,
            "binding links",
            f"source_sha256 {sha256} of {SAMPLED_D_A} matches no listed input",
        )

    def test_a_partner_links_row_held_in_sample_fails(self):
        self.rewrite("links", lambda rows: changed(rows, PARTNER_13D_A1, held_in="sample"))
        _, stage4_path = write_both_manifests(self)

        sha256 = sha256_of(self.layout.partner_submission(PARTNER_13D_A1))
        self.assert_fails_with(
            stage4_path,
            "binding links",
            f"source_sha256 {sha256} of {PARTNER_13D_A1} matches no listed input",
        )

    def test_a_links_row_held_nowhere_fails(self):
        self.rewrite("links", lambda rows: changed(rows, SAMPLED_D_A, held_in="elsewhere"))
        _, stage4_path = write_both_manifests(self)

        sha256 = sha256_of(self.layout.submission(SAMPLED_D_A))
        self.assert_fails_with(
            stage4_path,
            "binding links",
            f"source_sha256 {sha256} of {SAMPLED_D_A} matches no listed input",
        )

    def test_a_sample_links_row_binds_to_the_submission_inputs_only(self):
        # The Stage 1 ledger is a listed input of the `tables` manifest, but not a submission.
        ledger_sha256 = sha256_of(self.layout.ledger)
        self.rewrite(
            "links", lambda rows: changed(rows, SAMPLED_D_A, source_sha256=ledger_sha256)
        )
        _, stage4_path = write_both_manifests(self)

        self.assert_fails_with(
            stage4_path,
            "binding links",
            f"source_sha256 {ledger_sha256} of {SAMPLED_D_A} matches no listed input",
        )

    def test_a_filings_hash_that_no_input_lists_fails(self):
        self.rewrite("filings", lambda rows: changed(rows, PARTNER_D, sha256="0" * 64))
        _, stage4_path = write_both_manifests(self)

        self.assert_fails_with(
            stage4_path, "binding filings", f"sha256 {'0' * 64} matches no listed input"
        )

    def test_a_fetches_row_with_another_hash_fails(self):
        row = next(
            row
            for row in read_table(self.layout.stage4_view, "fetches").to_pylist()
            if row["accession_number"] == PARTNER_D
        )
        self.rewrite("fetches", lambda rows: changed(rows, PARTNER_D, sha256="1" * 64))
        _, stage4_path = write_both_manifests(self)

        listed = sha256_of(self.layout.partner_submission(PARTNER_D))
        self.assert_fails_with(
            stage4_path,
            "binding fetches",
            f"{PARTNER_D} {row['path']} has the listed SHA-256 {listed},"
            f" the ledger gives {'1' * 64}",
        )


class VerifyStage4MalformedTests(VerifyStage4TestCase):
    """A `stage4` manifest of format 1 that is wrong inside. Each check names its failure."""

    def setUp(self) -> None:
        super().setUp()
        _, stage4_path = write_both_manifests(self)
        self.original = json.loads(stage4_path.read_text(encoding="utf-8"))

    def verify_edited(self, edit: Callable[[dict], object]) -> tuple[int, list[str]]:
        """Write the manifest again with `edit` applied to its dict. Run `verify` on it."""
        written = copy.deepcopy(self.original)
        edit(written)
        edited = self.layout.manifests / "edited.json"
        edited.write_text(json.dumps(written), encoding="utf-8")
        return self.verify(edited)

    def test_a_malformed_inputs_list_gives_failure_lines(self):
        edits = {
            "inputs null": lambda written: written.update(inputs=None),
            "no inputs": lambda written: written.pop("inputs"),
            "an input with no sha256": lambda written: written["inputs"][0].pop("sha256"),
        }
        for name, edit in edits.items():
            with self.subTest(edit=name):
                code, lines = self.verify_edited(edit)

                self.assertEqual(code, 1)
                self.assertEqual(lines[0], SEED_LINE)
                self.assertTrue(lines[FILES].startswith("files: failed: "), lines[FILES])
                # No table can be checked without the listed inputs: one line for the part.
                self.assertTrue(lines[2].startswith("binding: failed: "), lines[2])

    def test_a_malformed_outputs_list_gives_a_files_failure_line(self):
        code, lines = self.verify_edited(lambda written: written.pop("outputs"))

        self.assertEqual(code, 1)
        self.assertTrue(lines[FILES].startswith("files: failed: "), lines[FILES])
        # The binding lines do not read the outputs.
        self.assertEqual(lines[2 : len(OK_LINES)], OK_LINES[2:])

    def test_a_manifest_with_no_builds_on_fails_files_and_links_only(self):
        code, lines = self.verify_edited(lambda written: written.pop("builds_on"))

        self.assertEqual(code, 1)
        self.assertTrue(lines[FILES].startswith("files: failed: "), lines[FILES])
        self.assertTrue(lines[LINKS].startswith("binding links: failed: "), lines[LINKS])
        for position in set(range(len(OK_LINES))) - {FILES, LINKS}:
            self.assertEqual(lines[position], OK_LINES[position])
