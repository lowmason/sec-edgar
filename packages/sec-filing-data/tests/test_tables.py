import tempfile
import unittest
from pathlib import Path

from sec_filing_data.layout import Layout
from sec_filing_data.tables import read_table, write_table

STATUS_ROW = {
    "accession_number": "0000000001-26-000001",
    "form_type": "10-K",
    "record_count": 3,
    "reason": None,
}


class WriteTableTest(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.layout = Layout(Path(folder.name))

    def test_rejects_a_key_that_is_not_in_the_schema(self) -> None:
        rows = [STATUS_ROW, {**STATUS_ROW, "record_cuont": 4}]
        with self.assertRaisesRegex(ValueError, r"ownership_status.*'record_cuont'"):
            write_table(self.layout, "ownership_status", rows)
        self.assertFalse(self.layout.table("ownership_status").exists())

    def test_writes_a_missing_key_as_null(self) -> None:
        row = {key: value for key, value in STATUS_ROW.items() if key != "record_count"}
        write_table(self.layout, "ownership_status", [row])
        written = read_table(self.layout, "ownership_status").to_pylist()
        self.assertEqual(written, [{**row, "record_count": None}])
