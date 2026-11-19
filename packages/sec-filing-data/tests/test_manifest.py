"""The manifest of a table set: every file with its size and SHA-256, and the inputs of `tables`."""

import contextlib
import hashlib
import io
import json
import platform
from collections import Counter
from pathlib import Path
from unittest import mock

import pyarrow
import pyarrow.parquet as pq

from sec_filing_data import cli, manifest, version
from sec_filing_data.tables import STAMP_KEYS, TABLE_FORMATS, read_table, write_table
from tests import TEST_COMMIT
from tests.test_rebuild import FixtureRootTestCase, line_count

TABLE_NAMES = sorted(TABLE_FORMATS)
OUTPUT_KEYS = {"path", "bytes", "sha256", "rows", *STAMP_KEYS}
INPUT_KEYS = {"path", "kind", "bytes", "sha256"}
WRITTEN_BY_KEYS = {"code_version", "python_version", "pyarrow_version"}
TOP_KEYS = {"manifest_format", "set", "root", "written_by", "outputs", "inputs"}


def sha256_of_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ManifestTestCase(FixtureRootTestCase):
    def run_manifest(self, *argv: str) -> tuple[int, str, str]:
        """Run `manifest` on the fixture root. Give the exit code, stdout and stderr."""
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(["manifest", "--out", str(self.layout.root), *argv])
        return code, stdout.getvalue(), stderr.getvalue()

    def write_tables_manifest(self) -> tuple[Path, dict]:
        code, stdout, stderr = self.run_manifest("--set", "tables", "--zip", str(self.zip_path))
        self.assertEqual((code, stderr), (0, ""))
        path = self.layout.manifests / f"tables@{TEST_COMMIT[:12]}.json"
        self.assertEqual(
            stdout.splitlines(), [f"manifest: {path}", f"sha256: {sha256_of_bytes(path)}"]
        )
        return path, json.loads(path.read_text(encoding="utf-8"))

    def files_under(self, folder: Path) -> list[Path]:
        return sorted(path for path in folder.rglob("*") if path.is_file())

    def freeze_tables_stage1(self) -> None:
        """Write `tables-stage1` with `pq.write_table` alone, so its files carry no stamp."""
        self.layout.tables_stage1.mkdir()
        for name in ("index", "sample"):
            frozen = read_table(self.layout, name).replace_schema_metadata(None)
            pq.write_table(frozen, self.layout.tables_stage1 / f"{name}.parquet")


class WriteManifestTests(ManifestTestCase):
    def test_set_manifest_lists_every_file(self):
        path, written = self.write_tables_manifest()

        self.assertEqual(set(written), TOP_KEYS)
        self.assertEqual(written["manifest_format"], 1)
        self.assertEqual(written["set"], "tables")
        self.assertEqual(written["root"], str(self.layout.root.absolute()))
        self.assertEqual(set(written["written_by"]), WRITTEN_BY_KEYS)
        self.assertEqual(
            written["written_by"],
            {
                "code_version": TEST_COMMIT,
                "python_version": platform.python_version(),
                "pyarrow_version": pyarrow.__version__,
            },
        )
        outputs = written["outputs"]
        self.assertEqual(
            [entry["path"] for entry in outputs], [f"tables/{name}.parquet" for name in TABLE_NAMES]
        )
        for name, entry in zip(TABLE_NAMES, outputs, strict=True):
            file = self.layout.table(name)
            with self.subTest(table=name):
                self.assertEqual(set(entry), OUTPUT_KEYS)
                self.assertEqual(entry["bytes"], file.stat().st_size)
                self.assertEqual(entry["sha256"], sha256_of_bytes(file))
                self.assertEqual(entry["rows"], read_table(self.layout, name).num_rows)
                self.assertEqual(entry["code_version"], TEST_COMMIT)
                self.assertEqual(entry["python_version"], platform.python_version())
                self.assertEqual(entry["pyarrow_version"], pyarrow.__version__)
                self.assertEqual(entry["table_format"], str(TABLE_FORMATS[name]))
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text, json.dumps(json.loads(text), sort_keys=True, indent=2) + "\n")

    def test_tables_manifest_lists_each_input_kind(self):
        _, written = self.write_tables_manifest()

        inputs = written["inputs"]
        submissions = self.files_under(self.layout.bytes_dir)
        self.assertTrue(submissions)
        kinds = Counter(entry["kind"] for entry in inputs)
        self.assertEqual(
            kinds, {"index": 1, "submission": len(submissions), "ledger": 2, "refetch": 1}
        )
        self.assertEqual([entry["path"] for entry in inputs], sorted(e["path"] for e in inputs))
        expected = {
            str(self.zip_path.absolute()): self.zip_path,
            "fetch-log.jsonl": self.layout.ledger,
            "stage2/fetch-log.jsonl": self.layout.stage2_ledger,
            **{path.relative_to(self.layout.root).as_posix(): path for path in submissions},
            **{
                path.relative_to(self.layout.root).as_posix(): path
                for path in self.files_under(self.layout.refetch_dir)
            },
        }
        self.assertEqual({entry["path"] for entry in inputs}, set(expected))
        for entry in inputs:
            file = expected[entry["path"]]
            with self.subTest(path=entry["path"]):
                self.assertEqual(set(entry), INPUT_KEYS)
                self.assertEqual(entry["bytes"], file.stat().st_size)
                self.assertEqual(entry["sha256"], sha256_of_bytes(file))
        index = next(entry for entry in inputs if entry["kind"] == "index")
        self.assertEqual(index["path"], str(self.zip_path.absolute()))

    def test_frozen_manifest_lists_outputs_only(self):
        self.freeze_tables_stage1()

        code, stdout, stderr = self.run_manifest("--set", "tables-stage1")

        self.assertEqual((code, stderr), (0, ""))
        path = self.layout.manifests / f"tables-stage1@{TEST_COMMIT[:12]}.json"
        self.assertEqual(
            stdout.splitlines(), [f"manifest: {path}", f"sha256: {sha256_of_bytes(path)}"]
        )
        written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(written), TOP_KEYS - {"inputs"})
        self.assertEqual(written["set"], "tables-stage1")
        outputs = written["outputs"]
        self.assertEqual(
            [entry["path"] for entry in outputs],
            ["tables-stage1/index.parquet", "tables-stage1/sample.parquet"],
        )
        for name, entry in zip(("index", "sample"), outputs, strict=True):
            file = self.layout.root / entry["path"]
            with self.subTest(path=entry["path"]):
                self.assertEqual(set(entry), OUTPUT_KEYS)
                self.assertEqual(entry["sha256"], sha256_of_bytes(file))
                self.assertEqual(entry["rows"], read_table(self.layout, name).num_rows)
                for key in STAMP_KEYS:
                    self.assertEqual(entry[key], version.NOT_RECORDED, key)

    def test_manifest_refuses_to_overwrite(self):
        path, _ = self.write_tables_manifest()
        original = path.read_bytes()
        runs = self.layout.runs.read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(runs[-1])["step"], "manifest")

        code, stdout, stderr = self.run_manifest("--set", "tables", "--zip", str(self.zip_path))

        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(stderr, f"error: {path} exists\n")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(self.layout.runs.read_text(encoding="utf-8").splitlines(), runs)

    def test_two_code_versions_give_two_names(self):
        self.write_tables_manifest()
        other = "b" * 40
        checkout = version.Checkout(other, True, None)

        with mock.patch.object(version, "current_checkout", return_value=checkout):
            write_table(self.layout, "sample", read_table(self.layout, "sample").to_pylist())
            code, _, stderr = self.run_manifest("--set", "tables", "--zip", str(self.zip_path))

        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(
            sorted(path.name for path in self.layout.manifests.iterdir()),
            ["tables@5ca1ab1e5ca1.json", "tables@bbbbbbbbbbbb.json"],
        )
        second = json.loads((self.layout.manifests / "tables@bbbbbbbbbbbb.json").read_text())
        by_path = {entry["path"]: entry for entry in second["outputs"]}
        self.assertEqual(second["written_by"]["code_version"], other)
        self.assertEqual(by_path["tables/sample.parquet"]["code_version"], other)
        self.assertEqual(by_path["tables/facts_status.parquet"]["code_version"], TEST_COMMIT)

    def test_manifest_lists_a_file_that_is_not_parquet(self):
        stray = self.layout.tables / ".DS_Store"
        stray.write_bytes(b"not a table")

        _, written = self.write_tables_manifest()

        entry = next(e for e in written["outputs"] if e["path"] == "tables/.DS_Store")
        self.assertEqual(
            entry,
            {
                "path": "tables/.DS_Store",
                "bytes": len(b"not a table"),
                "sha256": sha256_of_bytes(stray),
                "rows": None,
                **dict.fromkeys(STAMP_KEYS),
            },
        )
        self.assertEqual(len(written["outputs"]), len(TABLE_NAMES) + 1)

    def test_manifest_zip_rules(self):
        self.freeze_tables_stage1()
        runs = line_count(self.layout.runs)
        cases = {
            "tables without a zip": ["--set", "tables"],
            "a frozen set with a zip": ["--set", "tables-stage1", "--zip", str(self.zip_path)],
        }
        for name, argv in cases.items():
            with self.subTest(case=name):
                code, stdout, stderr = self.run_manifest(*argv)

                self.assertEqual((code, stdout), (2, ""))
                self.assertTrue(stderr.startswith("error: "), stderr)
                self.assertEqual(stderr.count("\n"), 1)
                self.assertFalse(self.layout.manifests.exists())
                self.assertEqual(line_count(self.layout.runs), runs)

    def test_the_refusal_comes_before_the_zip_check_and_the_overwrite_check(self):
        self.write_tables_manifest()
        dirty = version.Checkout(TEST_COMMIT, False, "uncommitted changes in uv.lock")
        cases = {
            "wrong zip use": ["--set", "tables"],
            "existing manifest": ["--set", "tables", "--zip", str(self.zip_path)],
        }
        for name, argv in cases.items():
            with self.subTest(case=name):
                runs = line_count(self.layout.runs)

                with mock.patch.object(version, "current_checkout", return_value=dirty):
                    code, stdout, stderr = self.run_manifest(*argv)

                self.assertEqual((code, stdout), (version.REFUSED_EXIT, ""))
                self.assertEqual(stderr, f"error: refused: {dirty.problem}\n")
                self.assertEqual(line_count(self.layout.runs), runs)

    def test_a_missing_folder_or_zip_gives_exit_1_and_writes_no_manifest(self):
        missing_zip = self.zip_path.with_name("missing.zip")
        cases = {
            "set folder": (["--set", "tables-stage2"], self.layout.tables_stage2),
            "zip": (["--set", "tables", "--zip", str(missing_zip)], missing_zip),
        }
        for name, (argv, missing) in cases.items():
            with self.subTest(missing=name):
                code, stdout, stderr = self.run_manifest(*argv)

                self.assertEqual((code, stdout), (1, ""))
                self.assertTrue(stderr.startswith("error: "), stderr)
                self.assertIn(str(missing), stderr)
                self.assertFalse(self.layout.manifests.exists())


class BuildManifestTests(ManifestTestCase):
    def test_build_manifest_zip_rules(self):
        stamp = version.current_stamp()
        cases = {
            "tables without a zip": ("tables", None),
            "tables-stage1 with a zip": ("tables-stage1", self.zip_path),
            "tables-stage2 with a zip": ("tables-stage2", self.zip_path),
        }
        for name, (set_name, zip_path) in cases.items():
            with self.subTest(case=name), self.assertRaises(ValueError):
                manifest.build_manifest(self.layout, set_name, zip_path=zip_path, stamp=stamp)
