"""`verify`: the files of a manifest, the binding of each record hash to a listed input, and the
re-derivation of a seeded sample of rows from the hashed bytes."""

import contextlib
import copy
import datetime
import io
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from functools import partial
from pathlib import Path
from unittest import mock

from sec_filing_data import sample, verify
from sec_filing_data.manifest import files_under, sha256_of, write_manifest
from sec_filing_data.tables import read_table, write_table
from sec_filing_data.verify import DEFAULT_ROWS, RECORDS_TABLES, VERIFY_SEED, run_verify

from tests import TEST_COMMIT, test_report
from tests.test_client import FakeResponse
from tests.test_index import FIXTURE, fingerprint
from tests.test_rebuild import (
    FETCHED_13F,
    FixtureRootTestCase,
    file_digests,
    line_count,
    path_stamps,
    run_cli,
)
from tests.test_xbrl import FIXTURE_BYTES as INSTANCE_BYTES
from tests.test_xbrl import INS_NAME, PRIMARY, submission_with, wrapped

SEED_LINE = f"seed: {VERIFY_SEED}"
BINDING_TABLES = (*RECORDS_TABLES, "fetches", "refetches")
# The lines before Part 3: the seed, the files line, then one binding line for each table.
ALL_OK = [SEED_LINE, "files: ok", *(f"binding {name}: ok" for name in BINDING_TABLES)]
NO_INPUTS = ["binding: not run, no inputs listed", "rederive: not run, no inputs listed"]


def line_of(table: str) -> int:
    """The position of the line of `table` in ALL_OK."""
    return ALL_OK.index(f"binding {table}: ok")


def with_line(position: int, line: str) -> list[str]:
    """ALL_OK with the line at `position` changed to `line`."""
    return [*ALL_OK[:position], line, *ALL_OK[position + 1 :]]


class VerifyTestCase(FixtureRootTestCase):
    def write_manifest(self, set_name: str = "tables") -> Path:
        zip_path = self.zip_path if set_name == "tables" else None
        return write_manifest(self.layout, set_name, zip_path=zip_path)

    def verify(self, manifest_path: Path, *argv: str) -> tuple[int, list[str]]:
        return run_cli(
            "verify", "--out", str(self.layout.root), "--manifest", str(manifest_path), *argv
        )

    def relative(self, path: Path) -> str:
        return path.relative_to(self.layout.root).as_posix()

    def byte_files(self) -> list[Path]:
        return sorted(files_under(self.layout.bytes_dir))

    def append_a_byte(self, path: Path) -> None:
        with path.open("ab") as handle:
            handle.write(b"\n")

    def assert_fails_with(self, manifest_path: Path, position: int, line: str) -> list[str]:
        """Run `verify`. Expect exit 1, and ALL_OK with only the line at `position` changed."""
        code, lines = self.verify(manifest_path)

        self.assertEqual(code, 1)
        self.assertEqual(lines[: len(ALL_OK)], with_line(position, line))
        return lines

    def rederive_ok(self, names: tuple[str, ...] = RECORDS_TABLES) -> list[str]:
        """The `rederive` lines of the tables `names` on an untouched root, at the default rows.

        `index` draws min(10, rows with times) + min(10, rows without). Each other table draws
        min(20, its rows).
        """
        lines = []
        for name in names:
            table = read_table(self.layout, name)
            if name == "index":
                timed = sum(at is not None for at in table["fetched_at"].to_pylist())
                count = min(10, timed) + min(10, table.num_rows - timed)
            else:
                count = min(20, table.num_rows)
            lines.append(f"rederive {name}: ok, {count} rows")
        return lines

    def rederive_line(self, lines: list[str], name: str) -> str:
        """The one `rederive` line of table `name` in `lines`."""
        found = [line for line in lines if line.startswith(f"rederive {name}: ")]
        self.assertEqual(len(found), 1, lines)
        return found[0]


class VerifyPassTests(VerifyTestCase):
    def test_an_untouched_root_passes(self):
        path = self.write_manifest()

        code, lines = self.verify(path)

        self.assertEqual(code, 0)
        self.assertEqual(
            RECORDS_TABLES, ("index", "filings", "parties", "documents", "facts", "ownership")
        )
        self.assertEqual((VERIFY_SEED, DEFAULT_ROWS), (20261119, 20))
        self.assertEqual(lines, [*ALL_OK, *self.rederive_ok()])
        self.assertEqual(run_verify(self.layout, path), (code, lines))

    def test_the_seed_line_names_the_seed(self):
        path = self.write_manifest()

        code, lines = self.verify(path, "--seed", "7", "--rows", "3")

        self.assertEqual(code, 0)
        self.assertEqual(lines[: len(ALL_OK)], ["seed: 7", *ALL_OK[1:]])

    def test_a_frozen_manifest_runs_part_1_only(self):
        shutil.copytree(self.layout.tables, self.layout.tables_stage2)
        path = self.write_manifest("tables-stage2")

        result = self.verify(path)

        self.assertEqual(result, (0, [SEED_LINE, "files: ok", *NO_INPUTS]))


class VerifyFilesTests(VerifyTestCase):
    def test_a_changed_byte_fails(self):
        path = self.write_manifest()
        changed = self.byte_files()[0]
        size = changed.stat().st_size
        self.append_a_byte(changed)

        self.assert_fails_with(
            path, 1, f"files: {self.relative(changed)}: {size + 1} bytes, listed {size}"
        )

    def test_a_byte_changed_in_place_fails_on_the_hash(self):
        path = self.write_manifest()
        changed = self.byte_files()[0]
        data = changed.read_bytes()
        changed.write_bytes(bytes([data[0] ^ 1]) + data[1:])

        self.assert_fails_with(
            path, 1, f"files: {self.relative(changed)}: SHA-256 differs from the listed value"
        )

    def test_a_removed_file_fails(self):
        path = self.write_manifest()
        self.layout.table("sample").unlink()

        self.assert_fails_with(path, 1, "files: tables/sample.parquet: missing")

    def test_a_removed_input_fails_under_its_listed_path(self):
        path = self.write_manifest()
        # The zip is listed by its absolute path, and the ledger by a path under the root.
        cases = [
            (self.zip_path, str(self.zip_path.absolute())),
            (self.layout.stage2_ledger, self.relative(self.layout.stage2_ledger)),
        ]
        for target, listed in cases:
            with self.subTest(file=target.name):
                data = target.read_bytes()
                target.unlink()

                code, lines = self.verify(path)

                target.write_bytes(data)
                self.assertEqual(code, 1)
                self.assertEqual(lines[1], f"files: {listed}: missing")

    def test_an_unlisted_file_fails(self):
        path = self.write_manifest()
        extras = (
            self.layout.bytes_dir / "extra.txt",
            self.layout.refetch_dir / "extra.txt",
            self.layout.tables / "extra.parquet",
            # A nested folder is checked too: the scan goes to any depth.
            self.layout.bytes_dir / "sub" / "extra.txt",
            self.layout.refetch_dir / "sub" / "extra.txt",
            self.layout.tables / "sub" / "extra.parquet",
        )
        for extra in extras:
            with self.subTest(file=self.relative(extra)):
                extra.parent.mkdir(exist_ok=True)
                extra.write_bytes(b"not listed")

                code, lines = self.verify(path)

                extra.unlink()
                if extra.parent.name == "sub":
                    extra.parent.rmdir()
                self.assertEqual(code, 1)
                failure = f"files: {self.relative(extra)}: not listed"
                self.assertEqual(lines[: len(ALL_OK)], with_line(1, failure))

    def test_swapped_byte_files_fail(self):
        path = self.write_manifest()
        files = self.byte_files()
        first = next(file for file in files if file.read_bytes() == FETCHED_13F)
        second = next(file for file in files if file != first)
        scratch = first.with_name("swap.tmp")
        first.rename(scratch)
        second.rename(first)
        scratch.rename(second)

        code, lines = self.verify(path)

        self.assertEqual(code, 1)
        # The manifest came before the swap, so the binding lines still pass.
        self.assertEqual(lines[2 : len(ALL_OK)], ALL_OK[2:])
        self.assertTrue(lines[1].startswith("files: bytes/"), lines[1])
        self.assertTrue(
            any(self.relative(swapped) in lines[1] for swapped in (first, second)), lines[1]
        )

    def test_a_changed_stamp_fails(self):
        path = self.write_manifest()
        written = json.loads(path.read_text(encoding="utf-8"))
        entry = next(e for e in written["outputs"] if e["path"] == "tables/sample.parquet")
        entry["code_version"] = "b" * 40
        path.write_text(json.dumps(written), encoding="utf-8")

        self.assert_fails_with(
            path,
            1,
            f"files: tables/sample.parquet: stamp code_version {TEST_COMMIT}"
            f" differs from the listed {'b' * 40}",
        )

    def test_verify_needs_the_manifest_root(self):
        path = self.write_manifest()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        other = Path(folder.name) / "other"

        result = run_cli("verify", "--out", str(other), "--manifest", str(path))

        self.assertEqual(
            result,
            (
                1,
                [
                    SEED_LINE,
                    f"files: --out {other} differs from the manifest root {self.layout.root}",
                ],
            ),
        )


class VerifyBindingTests(VerifyTestCase):
    def test_a_source_hash_with_no_input_fails(self):
        write_table(
            self.layout,
            "facts",
            [{"accession_number": "0001000097-26-000006", "source_sha256": "0" * 64}],
        )
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("facts"),
            f"binding facts: source_sha256 {'0' * 64} matches no listed input",
        )

    def test_the_first_source_hash_with_no_input_is_named(self):
        rows = read_table(self.layout, "parties").to_pylist()
        rows[1]["source_sha256"] = "2" * 64
        rows[2]["source_sha256"] = "1" * 64
        write_table(self.layout, "parties", rows)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("parties"),
            f"binding parties: source_sha256 {'2' * 64} matches no listed input",
        )

    def test_a_filing_hash_with_no_input_fails(self):
        rows = read_table(self.layout, "filings").to_pylist()
        rows[0]["sha256"] = "3" * 64
        write_table(self.layout, "filings", rows)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("filings"),
            f"binding filings: sha256 {'3' * 64} matches no listed input",
        )

    def test_the_hash_of_a_filing_that_is_not_ok_is_not_checked(self):
        rows = read_table(self.layout, "filings").to_pylist()
        rows[0].update(outcome="failed", sha256="3" * 64)
        write_table(self.layout, "filings", rows)
        path = self.write_manifest()

        # Only the lines before Part 3 are checked: Part 3 may flag the edited row.
        self.assertEqual(self.verify(path)[1][: len(ALL_OK)], ALL_OK)

    def test_a_missing_source_hash_fails(self):
        rows = read_table(self.layout, "documents").to_pylist()
        rows[0]["source_sha256"] = None
        write_table(self.layout, "documents", rows)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("documents"),
            "binding documents: source_sha256 None matches no listed input",
        )

    def test_the_rows_of_fetches_and_refetches_that_are_not_ok_are_not_checked(self):
        fetches = read_table(self.layout, "fetches").to_pylist()
        fetches[0].update(outcome="failed", path=None, sha256=None)
        write_table(self.layout, "fetches", fetches)
        refetches = read_table(self.layout, "refetches").to_pylist()
        refetches[0].update(outcome="failed", refetch_sha256=None)
        write_table(self.layout, "refetches", refetches)
        path = self.write_manifest()

        # Only the lines before Part 3 are checked: Part 3 may flag the edited rows.
        self.assertEqual(self.verify(path)[1][: len(ALL_OK)], ALL_OK)

    def test_the_path_check_catches_one_of_two_equal_files(self):
        files = self.byte_files()
        counts = Counter(file.read_bytes() for file in files)
        edited = next(file for file in files if counts[file.read_bytes()] > 1)
        ledger_hash = sha256_of(edited)
        self.append_a_byte(edited)
        path = self.write_manifest()

        # The ledger hash is still listed, for the other copy. Only the path check shows the edit.
        self.assert_fails_with(
            path,
            line_of("fetches"),
            f"binding fetches: {edited.stem} {edited} has the listed SHA-256 {sha256_of(edited)},"
            f" the ledger gives {ledger_hash}",
        )

    def test_an_edited_refetch_copy_is_caught_by_its_path(self):
        accession = read_table(self.layout, "refetches").to_pylist()[0]["accession_number"]
        copy = self.layout.refetched(accession)
        ledger_hash = sha256_of(copy)
        self.append_a_byte(copy)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("refetches"),
            f"binding refetches: {accession} {self.relative(copy)}"
            f" has the listed SHA-256 {sha256_of(copy)}, the ledger gives {ledger_hash}",
        )

    def test_a_fetches_path_outside_the_root_fails(self):
        rows = read_table(self.layout, "fetches").to_pylist()
        accession = rows[0]["accession_number"]
        outside = f"/elsewhere/bytes/{accession}.txt"
        rows[0]["path"] = outside
        write_table(self.layout, "fetches", rows)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("fetches"),
            f"binding fetches: {accession} {outside} is not under {self.layout.root}",
        )

    def test_a_fetches_path_that_is_not_a_listed_input_fails(self):
        rows = read_table(self.layout, "fetches").to_pylist()
        accession = rows[0]["accession_number"]
        unlisted = str(self.layout.bytes_dir / "elsewhere" / f"{accession}.txt")
        rows[0]["path"] = unlisted
        write_table(self.layout, "fetches", rows)
        path = self.write_manifest()

        self.assert_fails_with(
            path,
            line_of("fetches"),
            f"binding fetches: {accession} {unlisted} is not a listed input",
        )

    def test_verify_names_a_missing_table(self):
        self.layout.table("ownership").unlink()
        path = self.write_manifest()

        lines = self.assert_fails_with(
            path,
            line_of("ownership"),
            f"binding ownership: failed: FileNotFoundError: {self.layout.table('ownership')}",
        )
        # Part 3 names the table too, and derives the other tables.
        self.assertEqual(
            lines[len(ALL_OK) :],
            [
                *self.rederive_ok(RECORDS_TABLES[:-1]),
                f"rederive ownership: failed: FileNotFoundError: {self.layout.table('ownership')}",
            ],
        )


class VerifyRederiveTests(VerifyTestCase):
    def test_a_changed_value_fails_the_rederive(self):
        rows = read_table(self.layout, "parties").to_pylist()
        rows[0]["name"] = "NOT THE FILED NAME"
        write_table(self.layout, "parties", rows)
        path = self.write_manifest()

        code, lines = self.verify(path, "--rows", "1000")

        self.assertEqual(code, 1)
        # The changed row still has a listed source hash: only the re-derivation shows the change.
        self.assertIn("binding parties: ok", lines)
        line = self.rederive_line(lines, "parties")
        self.assertTrue(
            line.startswith(f"rederive parties: row 0 of {rows[0]['accession_number']}: "), line
        )
        self.assertIn("column name: 'NOT THE FILED NAME'", line)

    def test_a_changed_index_time_fails(self):
        rows = read_table(self.layout, "index").to_pylist()
        # A row with a public time is a row with times: its `fetched_at` is not null.
        position = next(n for n, row in enumerate(rows) if row["public_at"] is not None)
        rows[position]["public_at"] += datetime.timedelta(seconds=1)
        write_table(self.layout, "index", rows)
        path = self.write_manifest()

        code, lines = self.verify(path, "--rows", "1000")

        self.assertEqual(code, 1)
        line = self.rederive_line(lines, "index")
        accession = rows[position]["accession_number"]
        self.assertTrue(line.startswith(f"rederive index: row {position} of {accession}: "), line)
        self.assertIn("column public_at: ", line)

    def test_rederive_ignores_sample_parquet(self):
        rows = read_table(self.layout, "sample").to_pylist()
        for row in rows:
            row["url"] += "?changed"
        write_table(self.layout, "sample", rows)
        path = self.write_manifest()

        # The sample comes from the zip and its seed, so the URLs of the tables still match.
        self.assertEqual(self.verify(path), (0, [*ALL_OK, *self.rederive_ok()]))

    def test_rederive_reads_the_bytes_it_hashed(self):
        path = self.write_manifest()
        changed = next(file for file in self.byte_files() if file.read_bytes() == FETCHED_13F)
        # No other file under the root has its hash, so `verify` must read this one.
        same = [file for file in files_under(self.layout.root) if file.read_bytes() == FETCHED_13F]
        self.assertEqual(same, [changed])
        self.append_a_byte(changed)

        code, lines = self.verify(path, "--rows", "1000")

        self.assertEqual(code, 1)
        filings = read_table(self.layout, "filings")["accession_number"].to_pylist()
        self.assertEqual(
            self.rederive_line(lines, "filings"),
            f"rederive filings: row {filings.index(changed.stem)} of {changed.stem}:"
            f" {self.relative(changed)}: SHA-256 differs from the listed value",
        )


class VerifyDrawTests(unittest.TestCase):
    def test_same_seed_draws_same_rows(self):
        drawn = verify.draw_positions(1000, 20, random.Random(5))

        self.assertEqual(verify.draw_positions(1000, 20, random.Random(5)), drawn)
        self.assertNotEqual(verify.draw_positions(1000, 20, random.Random(6)), drawn)
        self.assertEqual(drawn, sorted(set(drawn)))
        self.assertEqual(len(drawn), 20)

    def test_draw_sizes(self):
        with_times, without = list(range(740)), list(range(740, 302_499))
        # An odd count gives its extra row to the rows without times.
        for count, split in {20: (10, 10), 21: (10, 11), 1: (0, 1)}.items():
            with self.subTest(count=count):
                drawn = verify.draw_index_positions(
                    with_times, without, count, random.Random(VERIFY_SEED)
                )

                self.assertEqual(drawn, sorted(set(drawn)))
                self.assertEqual(
                    (sum(n < 740 for n in drawn), sum(n >= 740 for n in drawn)), split
                )
        # Neither half is topped up from the other: 2 rows in one half give 2 + 10.
        for timed, untimed in (([0, 1], list(range(2, 100))), (list(range(98)), [98, 99])):
            with self.subTest(with_times=len(timed), without=len(untimed)):
                drawn = verify.draw_index_positions(timed, untimed, 20, random.Random(VERIFY_SEED))

                self.assertEqual(len(drawn), 12)
        # A small table gives every row once.
        small = verify.draw_positions(5, 1000, random.Random(VERIFY_SEED))
        self.assertEqual(small, [0, 1, 2, 3, 4])


class VerifyWiderRootTests(VerifyTestCase):
    """A root on which `facts` has rows and one accession of the index is not sampled.

    One 6-K of the index fixture is a 10-Q here, fetched with an XBRL instance. The sample takes
    4 of the 5 accessions, so the index has a row without times, as on the live root.
    """

    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        fixture = Path(folder.name) / FIXTURE.name
        text = FIXTURE.read_text(encoding="utf-8")
        fixture.write_text(text.replace("|6-K|2026-07-28|", "|10-Q|2026-07-28|"), encoding="utf-8")
        self.enterContext(mock.patch.object(test_report, "FIXTURE", fixture))
        self.enterContext(
            mock.patch.object(sample, "draw_sample", partial(sample.draw_sample, size=4))
        )
        super().setUp()

    def fetch(self, session, **kwargs) -> int:
        instance = ("EX-101.INS", INS_NAME, wrapped(INSTANCE_BYTES, "XBRL"))
        with_facts = submission_with(PRIMARY, instance)
        for row in read_table(self.layout, "sample").to_pylist():
            if row["form_type"] == "10-Q":
                session.replies[row["url"]] = FakeResponse(200, [with_facts])
        return super().fetch(session, **kwargs)

    def test_facts_and_index_rows_outside_the_sample_are_derived(self):
        sampled = {row["accession_number"] for row in read_table(self.layout, "sample").to_pylist()}
        index_rows = read_table(self.layout, "index").to_pylist()
        self.assertTrue(any(row["accession_number"] not in sampled for row in index_rows))
        self.assertGreater(read_table(self.layout, "facts").num_rows, 0)
        path = self.write_manifest()

        self.assertEqual(self.verify(path), (0, [*ALL_OK, *self.rederive_ok()]))

    def index_halves(self) -> tuple[list[int], list[int]]:
        """The positions of the `index` rows with filing times, and of the rows without."""
        fetched_at = read_table(self.layout, "index")["fetched_at"].to_pylist()
        timed = [position for position, at in enumerate(fetched_at) if at is not None]
        untimed = [position for position, at in enumerate(fetched_at) if at is None]
        return timed, untimed

    def test_index_draws_half_its_rows_from_rows_with_times(self):
        timed, untimed = self.index_halves()
        # The sampled accessions have 5 rows, all with times. The unsampled one has 1, without.
        self.assertEqual((len(timed), len(untimed)), (5, 1))
        path = self.write_manifest()
        for rows in (3, 5):
            with self.subTest(rows=rows):
                split = min(rows // 2, len(timed)) + min(rows - rows // 2, len(untimed))
                # The split differs from a plain draw, and from a draw with its halves swapped.
                plain = min(rows, len(timed) + len(untimed))
                swapped = min(rows // 2, len(untimed)) + min(rows - rows // 2, len(timed))
                self.assertNotIn(split, (plain, swapped))
                drawn = verify.draw_index_positions(
                    timed, untimed, rows, random.Random(VERIFY_SEED)
                )
                self.assertEqual(len(drawn), split)
                self.assertTrue(set(drawn) & set(timed) and set(drawn) & set(untimed), drawn)

                code, lines = self.verify(path, "--rows", str(rows))

                self.assertEqual(code, 0)
                line = self.rederive_line(lines, "index")
                self.assertEqual(line, f"rederive index: ok, {split} rows")

    def test_a_changed_index_column_fails(self):
        original = read_table(self.layout, "index").to_pylist()
        sampled = {row["accession_number"] for row in read_table(self.layout, "sample").to_pylist()}
        accessions = [row["accession_number"] for row in original]
        positions = {
            "sampled": next(n for n, accession in enumerate(accessions) if accession in sampled),
            "unsampled": next(
                n for n, accession in enumerate(accessions) if accession not in sampled
            ),
        }
        for kind, position in positions.items():
            for column in ("company_name", "form_type"):
                with self.subTest(row=kind, column=column):
                    rows = copy.deepcopy(original)
                    rows[position][column] += " CHANGED"
                    write_table(self.layout, "index", rows)
                    path = self.write_manifest()

                    code, lines = self.verify(path, "--rows", "1000")

                    path.unlink()
                    self.assertEqual(code, 1)
                    line = self.rederive_line(lines, "index")
                    accession = rows[position]["accession_number"]
                    self.assertTrue(
                        line.startswith(
                            f"rederive index: row {position} of {accession}: column {column}: "
                        ),
                        line,
                    )


class VerifyManifestTests(VerifyTestCase):
    def test_verify_refuses_an_unreadable_manifest(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        cases = {
            "not JSON": ("{", "Expecting"),
            "format 2": (json.dumps({"manifest_format": 2}), "manifest_format is 2, not 1"),
            "not an object": ("[]", "not a JSON object"),
        }
        for name, (text, reason) in cases.items():
            with self.subTest(manifest=name):
                path = Path(folder.name) / f"{name}.json"
                path.write_text(text, encoding="utf-8")

                code, lines = self.verify(path)

                self.assertEqual(code, 1)
                self.assertEqual(len(lines), 1)
                self.assertTrue(lines[0].startswith(f"manifest: {path}: {reason}"), lines[0])

    def test_verify_refuses_a_missing_manifest(self):
        path = self.layout.manifests / "missing.json"

        result = self.verify(path)

        self.assertEqual(result, (1, [f"manifest: {path}: No such file or directory"]))


class VerifyMalformedManifestTests(VerifyTestCase):
    """A manifest of format 1 that is wrong inside. Each check names its failure, and no
    exception escapes, so every line shows."""

    def setUp(self) -> None:
        super().setUp()
        self.original = json.loads(self.write_manifest().read_text(encoding="utf-8"))

    def verify_changed(self, change) -> tuple[int, list[str]]:
        """Write the manifest again with `change` applied to its dict. Run `verify` on it.

        Give the result of `run_verify`. The command gives the same result and no stderr.
        """
        path = self.layout.manifests / "changed.json"
        written = copy.deepcopy(self.original)
        change(written)
        path.write_text(json.dumps(written), encoding="utf-8")
        result = run_verify(self.layout, path)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertEqual(self.verify(path), result)
        self.assertEqual(stderr.getvalue(), "")
        return result

    def test_a_malformed_inputs_list_gives_failure_lines(self):
        changes = {
            "inputs null": lambda written: written.update(inputs=None),
            "an input that is a number": lambda written: written.update(inputs=[1]),
            "an input with no sha256": lambda written: written["inputs"][0].pop("sha256"),
            "an input with no path": lambda written: written["inputs"][0].pop("path"),
            "an input whose path is a list": lambda written: written["inputs"][0].update(path=[]),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                code, lines = self.verify_changed(change)

                self.assertEqual(code, 1)
                self.assertEqual(lines[0], SEED_LINE)
                self.assertTrue(lines[1].startswith("files: failed: "), lines[1])
                self.assertTrue(lines[2].startswith("binding: failed: "), lines[2])
                # Part 3 cannot draw its sample without the inputs: one line for the part.
                self.assertEqual(len(lines), 4, lines)
                self.assertTrue(lines[3].startswith("rederive: failed: "), lines[3])

    def test_a_malformed_outputs_list_gives_a_files_failure_line(self):
        changes = {
            "no outputs": lambda written: written.pop("outputs"),
            "outputs null": lambda written: written.update(outputs=None),
            "an output that is a number": lambda written: written.update(outputs=[1]),
            "no set": lambda written: written.pop("set"),
        }
        for name, change in changes.items():
            with self.subTest(change=name):
                code, lines = self.verify_changed(change)

                self.assertEqual(code, 1)
                self.assertEqual(lines[0], SEED_LINE)
                self.assertTrue(lines[1].startswith("files: failed: "), lines[1])
                # The binding lines do not read the outputs.
                self.assertEqual(lines[2 : len(ALL_OK)], ALL_OK[2:])

    def test_a_manifest_with_no_root_names_the_mismatch(self):
        result = self.verify_changed(lambda written: written.pop("root"))

        failure = f"files: --out {self.layout.root} differs from the manifest root None"
        self.assertEqual(result, (1, [SEED_LINE, failure]))


class VerifyCommandTests(VerifyTestCase):
    def test_verify_writes_only_its_run_line(self):
        path = self.write_manifest()
        digests, stamps = file_digests(self.layout.root), path_stamps(self.layout.root)
        runs = line_count(self.layout.runs)

        code, lines = self.verify(path)

        self.assertEqual((code, lines[: len(ALL_OK)]), (0, ALL_OK))
        self.assertEqual(file_digests(self.layout.root), digests)
        self.assertEqual(path_stamps(self.layout.root), stamps)
        records = [json.loads(line) for line in self.layout.runs.read_text().splitlines()]
        self.assertEqual(len(records), runs + 1)
        self.assertEqual(records[-1]["step"], "verify")

    def test_verify_never_loads_requests(self):
        path = self.write_manifest()
        # Part 3 parses the zip, so the subprocess names the fixture zip as the tests do.
        sha256, size = fingerprint(self.zip_path)
        code = (
            "import sys\n"
            "from sec_filing_data import cli, index\n"
            "index.INDEX_SHA256, index.INDEX_SIZE = sys.argv[3], int(sys.argv[4])\n"
            "print(cli.main(['verify', '--out', sys.argv[1], '--manifest', sys.argv[2]]))\n"
            "print('requests' in sys.modules)\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", code, str(self.layout.root), str(path), sha256, str(size)],
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.splitlines()[-2:], ["0", "False"])
