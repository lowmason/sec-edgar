import platform
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq

from sec_filing_data import version
from sec_filing_data.layout import Layout
from sec_filing_data.rebuild import compare_table
from sec_filing_data.tables import (
    SCHEMAS,
    STAGE3_TABLES,
    STAGE4_TABLES,
    STAMP_KEYS,
    TABLE_FORMATS,
    read_stamp,
    read_table,
    schema_fingerprint,
    write_table,
)
from tests import TEST_COMMIT

STATUS_ROW = {
    "accession_number": "0000000001-26-000001",
    "form_type": "10-K",
    "record_count": 3,
    "reason": None,
}
FACTS_STATUS_ROW = {
    "accession_number": "0000000001-26-000001",
    "form_type": "10-K",
    "source_document": "a.xml",
    "fact_count": 3,
    "reason": None,
}

# The fingerprint of each schema at its format number. A schema change needs a new number
# in `TABLE_FORMATS` and a new line here.
SCHEMA_FINGERPRINTS = {
    ("index", 2): "a7857af677b0e856d626122c613dff01ae4d766b2841cb2568dddd2d8bb55e2d",
    ("sample", 1): "9886543d42ba21b786105cc19314423dbe59d9ceb7398e1de601ca730d391a97",
    ("fetches", 1): "1bfc23da407bd93ace0d59aa073a3e99f60018301df3e4be104f48f4a1508050",
    ("filings", 2): "c70f25e610e2b566b692bb7b092599f3e5960e024c14c9c15f5e9656de9d13b5",
    ("parties", 2): "bba2192ed60a8e6b51556c594054a8191ec48f4e3e89f4a68a6850dcfd6e0ffb",
    ("documents", 2): "40f91b91ba0d1819d20c876d6c5e5170ee737d62ed84accf0abcf5f1408f730b",
    ("facts", 2): "4b4a1a91f687ef129c5536ab89cc2ef2291bbeda6b648f006ea0d87591443030",
    ("facts_status", 1): "a0d12f8149eb016d3efc8458caf7d96635f4f61aaca16f6f1f6c9380ef6d6e23",
    ("ownership", 2): "f40995ce69a304dd4ce568a3106376f0cce78488a544cb87ddb04f410b6271a6",
    ("ownership_status", 1): "fd8744133acfd2fb77070ba8247e8b72ddc2fbad948b8c34a84f93cc30027ff8",
    ("refetches", 1): "8f0f9ed4ca108ee081d70f862a8f62cadc3d66e66255c948a1b5710d96c28b19",
    ("partners", 1): "f0d74d67c35e1a6cbf341e07c517cc72ea178a209805c3b1e2707743bef40c5f",
    ("links", 1): "dee89c92c27f2d799d1d15f497edd260cb23db94e292a75c3a6c14438a2caa54",
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


class TableFormatTests(unittest.TestCase):
    def test_each_schema_matches_its_format_number(self) -> None:
        self.assertEqual(set(TABLE_FORMATS), set(SCHEMAS))
        for name, schema in SCHEMAS.items():
            with self.subTest(table=name):
                self.assertEqual(
                    SCHEMA_FINGERPRINTS[(name, TABLE_FORMATS[name])], schema_fingerprint(schema)
                )

    def test_a_changed_schema_with_the_old_number_fails(self) -> None:
        sample = SCHEMAS["sample"]
        swapped = pa.schema([sample.field(1), sample.field(0), *list(sample)[2:]])
        retyped = pa.schema(
            pa.field("draw", pa.int64()) if field.name == "draw" else field for field in sample
        )
        changed = {
            "an added string column": sample.append(pa.field("extra", pa.string())),
            "two columns swapped": swapped,
            "draw as int64": retyped,
        }
        for description, schema in changed.items():
            with self.subTest(change=description):
                self.assertNotEqual(schema_fingerprint(schema), SCHEMA_FINGERPRINTS[("sample", 1)])


class Stage4LayoutTests(unittest.TestCase):
    def test_stage4_paths_stay_under_one_root(self) -> None:
        layout = Layout(Path("/r"))
        view = layout.stage4_view

        self.assertEqual(layout.stage4_bytes, Path("/r/stage4/bytes"))
        self.assertEqual(layout.stage4_ledger, Path("/r/stage4/fetch-log.jsonl"))
        self.assertEqual(layout.stage4_tables, Path("/r/stage4/tables"))
        self.assertEqual(layout.partner_submission("A"), Path("/r/stage4/bytes/A.txt"))
        self.assertEqual(view.table("links"), Path("/r/stage4/tables/links.parquet"))
        self.assertEqual(view.runs, Path("/r/runs.jsonl"))
        self.assertEqual(view.lock, Path("/r/fetch.lock"))
        self.assertEqual(view.manifests, Path("/r/manifests"))
        # The Stage 3 paths do not move.
        self.assertEqual(layout.table("links"), Path("/r/tables/links.parquet"))
        # A folder for the Stage 4 tables moves them and nothing else.
        moved = Layout(Path("/r"), stage4_tables_dir=Path("/t"))
        self.assertEqual(moved.stage4_view.table("links"), Path("/t/links.parquet"))
        self.assertEqual(moved.table("links"), Path("/r/tables/links.parquet"))
        self.assertEqual(moved.stage4_bytes, Path("/r/stage4/bytes"))

    def test_a_stage4_table_is_written_under_stage4(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        layout = Layout(Path(folder.name) / "root")

        write_table(layout.stage4_view, "partners", [])

        path = layout.root / "stage4" / "tables" / "partners.parquet"
        self.assertTrue(path.exists())
        self.assertEqual(read_stamp(path)["table_format"], "1")
        self.assertFalse((layout.root / "tables").exists())

    def test_the_table_name_tuples_split_the_stages(self) -> None:
        self.assertEqual(
            STAGE3_TABLES,
            (
                "index",
                "sample",
                "fetches",
                "filings",
                "parties",
                "documents",
                "facts",
                "facts_status",
                "ownership",
                "ownership_status",
                "refetches",
            ),
        )
        self.assertEqual(
            STAGE4_TABLES,
            (
                "partners",
                "fetches",
                "filings",
                "parties",
                "documents",
                "ownership",
                "ownership_status",
                "links",
            ),
        )
        self.assertEqual(set(STAGE3_TABLES) | set(STAGE4_TABLES), set(SCHEMAS))
        self.assertEqual(set(STAGE3_TABLES) & {"partners", "links"}, set())


class StampTests(unittest.TestCase):
    def setUp(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def layout(self, name: str) -> Layout:
        return Layout(self.root / name)

    def test_a_written_table_carries_the_stamp(self) -> None:
        layout = self.layout("root")
        write_table(layout, "sample", [])

        self.assertEqual(
            read_stamp(layout.table("sample")),
            {
                "code_version": TEST_COMMIT,
                "python_version": platform.python_version(),
                "pyarrow_version": pa.__version__,
                "table_format": "1",
            },
        )
        footer = pq.read_metadata(layout.table("sample")).metadata
        self.assertEqual(
            set(footer),
            {b"ARROW:schema", *(f"sec_filing_data.{key}".encode() for key in STAMP_KEYS)},
        )

    def test_no_commit_writes_not_recorded(self) -> None:
        layout = self.layout("root")
        with mock.patch.object(
            version, "current_checkout", lambda: version.Checkout(None, None, "no git")
        ):
            write_table(layout, "sample", [])

        self.assertEqual(read_stamp(layout.table("sample"))["code_version"], "not recorded")

    def test_a_file_with_no_stamp_reads_not_recorded(self) -> None:
        path = self.root / "plain.parquet"
        pq.write_table(pa.Table.from_pylist([], schema=SCHEMAS["sample"]), path)

        self.assertEqual(read_stamp(path), dict.fromkeys(STAMP_KEYS, "not recorded"))

    def test_same_rows_and_stamp_give_the_same_bytes(self) -> None:
        first, second = self.layout("first"), self.layout("second")
        write_table(first, "facts_status", [FACTS_STATUS_ROW])
        write_table(second, "facts_status", [FACTS_STATUS_ROW])

        self.assertEqual(
            first.table("facts_status").read_bytes(), second.table("facts_status").read_bytes()
        )

    def test_compare_ignores_the_stamp(self) -> None:
        first, second = self.layout("first"), self.layout("second")
        write_table(first, "facts_status", [FACTS_STATUS_ROW])
        with mock.patch.object(
            version, "current_checkout", lambda: version.Checkout("b" * 40, True, None)
        ):
            write_table(second, "facts_status", [FACTS_STATUS_ROW])

        self.assertNotEqual(
            read_stamp(first.table("facts_status")), read_stamp(second.table("facts_status"))
        )
        self.assertEqual(
            compare_table(read_table(first, "facts_status"), read_table(second, "facts_status")),
            "equal",
        )
