import contextlib
import datetime
import hashlib
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from sec_filing_data import cli, index
from sec_filing_data.layout import Layout
from sec_filing_data.tables import SCHEMAS, read_table

FIXTURE = Path(__file__).parent / "fixtures" / "master-fixture.idx"
SHARED_PATH = "edgar/data/1326200/0001104659-26-081696.txt"


def write_zip(folder: Path, text: str) -> Path:
    """Write `text` as member master.idx with CRLF line endings, as the real file has."""
    path = folder / "master.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("master.idx", text.replace("\n", "\r\n").encode("utf-8"))
    return path


def fingerprint(path: Path) -> tuple[str, int]:
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data)


class IndexTestCase(unittest.TestCase):
    def make_folder(self) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    def read_zip_of(self, text: str) -> list[dict]:
        zip_path = write_zip(self.make_folder(), text)
        sha256, size = fingerprint(zip_path)
        return index.read_index(zip_path, sha256=sha256, size=size)


class ReadIndexTests(IndexTestCase):
    def setUp(self):
        self.text = FIXTURE.read_text(encoding="utf-8")
        self.lines = self.text.split("\n")  # 17 lines and a final empty piece
        self.zip_path = write_zip(self.make_folder(), self.text)
        self.sha256, self.size = fingerprint(self.zip_path)

    def test_keeps_every_row(self):
        rows = index.read_index(self.zip_path, sha256=self.sha256, size=self.size)

        self.assertEqual(len(rows), 6)
        self.assertEqual([row["line_number"] for row in rows], [12, 13, 14, 15, 16, 17])
        self.assertEqual(
            rows[0],
            {
                "line_number": 12,
                "cik": 1000097,
                "company_name": "KINGDON CAPITAL MANAGEMENT, L.L.C.",
                "form_type": "13F-HR",
                "date_filed": datetime.date(2026, 8, 14),
                "filename": "edgar/data/1000097/0001000097-26-000006.txt",
                "accession_number": "0001000097-26-000006",
            },
        )
        for row in rows:
            self.assertIs(type(row["date_filed"]), datetime.date)
        shared = [row for row in rows if row["filename"] == SHARED_PATH]
        self.assertEqual(
            [row["form_type"] for row in shared], ["SC 13D/A", "SC TO-T/A"]
        )
        self.assertEqual(
            {row["accession_number"] for row in shared}, {"0001104659-26-081696"}
        )
        self.assertEqual({row["company_name"] for row in shared}, {"GENCO SHIPPING & TRADING LTD"})

    def test_refuses_wrong_hash_or_size(self):
        with self.subTest("hash"):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                index.read_index(self.zip_path, sha256="0" * 64, size=self.size)
        with self.subTest("size"):
            with self.assertRaisesRegex(ValueError, "size"):
                index.read_index(self.zip_path, sha256=self.sha256, size=self.size + 1)

    def test_refuses_before_parsing(self):
        not_a_zip = self.make_folder() / "master.zip"
        not_a_zip.write_bytes(b"this is not a zip file")

        with self.assertRaisesRegex(ValueError, "size"):
            index.read_index(not_a_zip, sha256=self.sha256, size=self.size)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            index.read_index(not_a_zip, sha256="0" * 64, size=len(b"this is not a zip file"))

    def test_bad_row_names_line(self):
        lines = list(self.lines)
        lines[13] = "1000177|NORDIC AMERICAN TANKERS Ltd|6-K|2026-08-27"  # line 14, 4 fields
        with self.assertRaisesRegex(ValueError, r"line 14\b.*5 fields"):
            self.read_zip_of("\n".join(lines))

    def test_row_with_extra_pipe_names_line(self):
        lines = list(self.lines)
        lines[14] = lines[14].replace("SAP SE", "SAP|SE")  # line 15, 6 fields
        with self.assertRaisesRegex(ValueError, r"line 15\b.*5 fields"):
            self.read_zip_of("\n".join(lines))

    def test_bad_cik_or_date_names_line(self):
        for name, old, new in [
            ("cik", "1000184|SAP SE", "x1000184|SAP SE"),
            ("date", "6-K|2026-07-28", "6-K|28/07/2026"),
        ]:
            with self.subTest(name):
                lines = list(self.lines)
                lines[14] = lines[14].replace(old, new)  # line 15
                with self.assertRaisesRegex(ValueError, r"line 15\b"):
                    self.read_zip_of("\n".join(lines))

    def test_header_mismatch_raises(self):
        text = self.text.replace("Form Type", "Type of Form")
        with self.assertRaisesRegex(ValueError, "header"):
            self.read_zip_of(text)

    def test_missing_dashed_line_raises(self):
        lines = list(self.lines)
        del lines[10]  # the dashed line
        with self.assertRaisesRegex(ValueError, "dashed"):
            self.read_zip_of("\n".join(lines))

    def test_keeps_last_row_without_final_newline(self):
        rows = self.read_zip_of(self.text.rstrip("\n"))

        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[-1]["line_number"], 17)

    def test_skips_empty_lines_but_counts_them(self):
        lines = list(self.lines)
        lines.insert(13, "")  # an empty line between line 13 and the old line 14
        rows = self.read_zip_of("\n".join(lines))

        self.assertEqual(len(rows), 6)
        self.assertEqual([row["line_number"] for row in rows], [12, 13, 15, 16, 17, 18])

    def test_line_separator_characters_do_not_shift_line_numbers(self):
        lines = list(self.lines)
        lines[13] = lines[13].replace("NORDIC", "NOR\x85DIC\u2028")  # line 14
        rows = self.read_zip_of("\n".join(lines))

        self.assertEqual([row["line_number"] for row in rows], [12, 13, 14, 15, 16, 17])


class IndexCommandTests(IndexTestCase):
    def test_index_command_writes_only_under_out(self):
        zip_folder = self.make_folder()
        zip_path = write_zip(zip_folder, FIXTURE.read_text(encoding="utf-8"))
        sha256, size = fingerprint(zip_path)
        before = sorted(os.listdir(zip_folder)), sha256
        root = self.make_folder() / "root"

        stdout = io.StringIO()
        with (
            mock.patch.object(index, "INDEX_SHA256", sha256),
            mock.patch.object(index, "INDEX_SIZE", size),
            contextlib.redirect_stdout(stdout),
        ):
            status = cli.main(["index", "--zip", str(zip_path), "--out", str(root)])

        self.assertEqual(status, 0)
        self.assertEqual(stdout.getvalue(), "rows: 6\n")
        self.assertEqual((sorted(os.listdir(zip_folder)), fingerprint(zip_path)[0]), before)
        table = read_table(Layout(root), "index")
        self.assertEqual(table.schema, SCHEMAS["index"])
        self.assertEqual(table.num_rows, 6)
        self.assertEqual(table["line_number"].to_pylist(), [12, 13, 14, 15, 16, 17])
        written = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        self.assertEqual(written, ["runs.jsonl", "tables/index.parquet"])
        step = json.loads((root / "runs.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(step["step"], "index")
        self.assertEqual(set(step), {"step", "started_at", "finished_at", "seconds"})

    def test_index_command_refuses_another_file(self):
        zip_path = write_zip(self.make_folder(), FIXTURE.read_text(encoding="utf-8"))
        root = self.make_folder() / "root"

        with self.assertRaisesRegex(ValueError, "size"):
            cli.main(["index", "--zip", str(zip_path), "--out", str(root)])
        self.assertFalse((root / "tables").exists())


if __name__ == "__main__":
    unittest.main()
