import contextlib
import datetime
import hashlib
import io
import json
import os
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from sec_filing_data import cli, index
from sec_filing_data.layout import Layout
from sec_filing_data.tables import FILING_TIME_COLUMNS, SCHEMAS, read_table

FIXTURE = Path(__file__).parent / "fixtures" / "master-fixture.idx"
SHARED_PATH = "edgar/data/1326200/0001104659-26-081696.txt"


def write_zip(folder: Path, text: str, *, extra: bytes = b"") -> Path:
    """Write `text` as member master.idx with CRLF line endings, as the real file has.

    `extra` is the extra field of the member, as the central directory keeps it.
    """
    path = folder / "master.zip"
    member = zipfile.ZipInfo("master.idx", date_time=(2026, 10, 31, 3, 49, 36))
    member.extra = extra
    member.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, text.replace("\n", "\r\n").encode("utf-8"))
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
                "source_url": index.INDEX_URL,
                "source_sha256": self.sha256,
                "index_built_at": None,
                "index_data_through": "September 30, 2026",
                "index_received_at": datetime.datetime(
                    2026, 10, 31, 17, 54, 33, 39228, tzinfo=datetime.UTC
                ),
                "index_last_modified_at": datetime.datetime(
                    2026, 10, 31, 7, 50, 9, tzinfo=datetime.UTC
                ),
            },
        )
        for row in rows:
            self.assertIs(type(row["date_filed"]), datetime.date)
        self.assertEqual({tuple(row) for row in rows}, {tuple(rows[0])})
        self.assertEqual(
            list(rows[0])[-6:],
            [
                "source_url",
                "source_sha256",
                "index_built_at",
                "index_data_through",
                "index_received_at",
                "index_last_modified_at",
            ],
        )
        shared = [row for row in rows if row["filename"] == SHARED_PATH]
        self.assertEqual(
            [row["form_type"] for row in shared], ["SC 13D/A", "SC TO-T/A"]
        )
        self.assertEqual(
            {row["accession_number"] for row in shared}, {"0001104659-26-081696"}
        )
        self.assertEqual({row["company_name"] for row in shared}, {"GENCO SHIPPING & TRADING LTD"})

    def test_constants_are_the_receipt_values(self):
        self.assertEqual(
            index.INDEX_URL, "https://www.sec.gov/Archives/edgar/full-index/2026/QTR3/master.zip"
        )
        self.assertEqual(
            index.INDEX_RECEIVED_AT,
            datetime.datetime(2026, 10, 31, 17, 54, 33, 39228, tzinfo=datetime.UTC),
        )
        self.assertEqual(
            index.INDEX_LAST_MODIFIED_AT,
            datetime.datetime(2026, 10, 31, 7, 50, 9, tzinfo=datetime.UTC),
        )

    def test_data_through_is_the_stripped_header_value_or_none(self):
        with self.subTest("as filed"):
            lines = list(self.lines)
            lines[1] = "Last Data Received:\t  June 30, 2026   "
            self.assertEqual(
                {row["index_data_through"] for row in self.read_zip_of("\n".join(lines))},
                {"June 30, 2026"},
            )
        with self.subTest("absent"):
            lines = [line for line in self.lines if not line.startswith("Last Data Received:")]
            rows = self.read_zip_of("\n".join(lines))
            self.assertEqual(len(rows), 6)
            self.assertEqual({row["index_data_through"] for row in rows}, {None})

    def test_extended_timestamp_gives_the_built_time(self):
        extra = struct.pack("<HHBI", 0x5455, 5, 3, 1793432975)
        zip_path = write_zip(self.make_folder(), self.text, extra=extra)
        sha256, size = fingerprint(zip_path)

        rows = index.read_index(zip_path, sha256=sha256, size=size)

        built = datetime.datetime(2026, 10, 31, 7, 49, 35, tzinfo=datetime.UTC)
        self.assertEqual({row["index_built_at"] for row in rows}, {built})
        self.assertEqual({row["source_sha256"] for row in rows}, {sha256})
        with self.subTest("no extra field"):
            self.assertEqual({row["index_built_at"] for row in self.read_zip_of(self.text)}, {None})

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


def member_with(extra: bytes) -> zipfile.ZipInfo:
    member = zipfile.ZipInfo("master.idx")
    member.extra = extra
    return member


def block(header_id: int, data: bytes, *, size: int | None = None) -> bytes:
    return struct.pack("<HH", header_id, len(data) if size is None else size) + data


BUILT = datetime.datetime(2026, 10, 31, 7, 49, 35, tzinfo=datetime.UTC)
STAMP = struct.pack("<I", 1793432975)


class MemberMtimeTests(unittest.TestCase):
    def test_reads_bytes_1_to_5_of_the_field(self):
        for flags in (1, 3, 7):
            with self.subTest(flags=flags):
                member = member_with(block(0x5455, bytes([flags]) + STAMP))
                self.assertEqual(index.member_mtime(member), BUILT)

    def test_does_not_size_the_field_from_its_flags(self):
        # Flags 7 would announce three times, but the block size is 5.
        member = member_with(block(0x5455, bytes([7]) + STAMP))
        self.assertEqual(index.member_mtime(member), BUILT)
        # A central-directory field may be longer than the flags tell. Bytes 1-5 still hold mtime.
        longer = member_with(block(0x5455, bytes([3]) + STAMP + STAMP))
        self.assertEqual(index.member_mtime(longer), BUILT)

    def test_walks_past_other_blocks(self):
        other = block(0x7875, b"\x01\x04\xf5\x01\x00\x00\x04\x14\x00\x00\x00")
        member = member_with(other + block(0x5455, bytes([3]) + STAMP))
        self.assertEqual(index.member_mtime(member), BUILT)

    def test_none_without_the_field(self):
        for name, extra in [
            ("empty", b""),
            ("other block", block(0x7875, b"\x01\x04\xf5\x01\x00\x00\x04\x14\x00\x00\x00")),
        ]:
            with self.subTest(name):
                self.assertIsNone(index.member_mtime(member_with(extra)))

    def test_none_when_the_mtime_flag_is_clear(self):
        member = member_with(block(0x5455, bytes([2]) + STAMP))
        self.assertIsNone(index.member_mtime(member))

    def test_none_when_the_field_is_too_short(self):
        for data in (b"", b"\x01", b"\x01\x01\x02\x03"):
            with self.subTest(size=len(data)):
                self.assertIsNone(index.member_mtime(member_with(block(0x5455, data))))

    def test_none_for_a_truncated_or_malformed_extra(self):
        for name, extra in [
            ("one byte", b"U"),
            ("header cut short", b"UT\x05"),
            ("data cut short", block(0x5455, bytes([3]) + STAMP, size=5)[:-2]),
            ("size beyond the data", block(0x5455, bytes([3]) + STAMP, size=40)),
            ("block before is cut short", block(0x7875, b"\x01", size=99) + block(0x5455, bytes([3]) + STAMP)),
        ]:
            with self.subTest(name):
                self.assertIsNone(index.member_mtime(member_with(extra)))


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
        row = table.to_pylist()[0]
        self.assertEqual(row["source_url"], index.INDEX_URL)
        self.assertEqual(row["source_sha256"], sha256)
        self.assertEqual(row["index_data_through"], "September 30, 2026")
        self.assertEqual(row["index_received_at"], index.INDEX_RECEIVED_AT)
        self.assertEqual(row["index_last_modified_at"], index.INDEX_LAST_MODIFIED_AT)
        for column in ("index_built_at", *FILING_TIME_COLUMNS):
            self.assertEqual(table[column].null_count, 6, column)
        written = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
        self.assertEqual(written, ["runs.jsonl", "tables/index.parquet"])
        step = json.loads((root / "runs.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(step["step"], "index")
        self.assertEqual(set(step), {"step", "started_at", "finished_at", "seconds"})

    def test_run_index_writes_the_table_and_returns_its_rows(self):
        zip_path = write_zip(self.make_folder(), FIXTURE.read_text(encoding="utf-8"))
        sha256, size = fingerprint(zip_path)
        layout = Layout(self.make_folder() / "root")

        with (
            mock.patch.object(index, "INDEX_SHA256", sha256),
            mock.patch.object(index, "INDEX_SIZE", size),
        ):
            rows = index.run_index(layout, zip_path)

        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["source_sha256"], sha256)
        written = read_table(layout, "index").to_pylist()
        # The table also holds the null filing times, which the rows leave out.
        self.assertEqual(
            [{key: row[key] for key in rows[0]} for row in written], rows
        )

    def test_index_command_refuses_another_file(self):
        zip_path = write_zip(self.make_folder(), FIXTURE.read_text(encoding="utf-8"))
        root = self.make_folder() / "root"

        with self.assertRaisesRegex(ValueError, "size"):
            cli.main(["index", "--zip", str(zip_path), "--out", str(root)])
        self.assertFalse((root / "tables").exists())


if __name__ == "__main__":
    unittest.main()
