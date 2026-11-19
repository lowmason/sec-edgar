"""The manifest of a table set: every file with its size and SHA-256, and the inputs of `tables`."""

import contextlib
import hashlib
import io
import json
import platform
import tempfile
from collections import Counter
from pathlib import Path
from unittest import mock

import pyarrow
import pyarrow.parquet as pq

from sec_filing_data import cli, manifest, version
from sec_filing_data.layout import Layout
from sec_filing_data.manifest import files_under
from sec_filing_data.tables import (
    STAGE3_TABLES,
    STAGE4_TABLES,
    STAMP_KEYS,
    TABLE_FORMATS,
    read_table,
    write_table,
)
from tests import TEST_COMMIT
from tests.stage4_root import Stage4RootTestCase, write_both_manifests
from tests.test_rebuild import FixtureRootTestCase, line_count

TABLE_NAMES = sorted(STAGE3_TABLES)
STAGE4_TABLE_NAMES = sorted(set(STAGE4_TABLES))
OUTPUT_KEYS = {"path", "bytes", "sha256", "rows", *STAMP_KEYS}
INPUT_KEYS = {"path", "kind", "bytes", "sha256"}
WRITTEN_BY_KEYS = {"code_version", "python_version", "pyarrow_version"}
TOP_KEYS = {"manifest_format", "set", "root", "written_by", "outputs", "inputs"}
OTHER_COMMIT = "b" * 40


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


class Stage4ManifestTests(Stage4RootTestCase):
    def manifest_paths(self) -> tuple[Path, Path]:
        """The paths of the `tables` and `stage4` manifests that the root's commit names."""
        return (
            manifest.manifest_path(self.layout, "tables", TEST_COMMIT),
            manifest.manifest_path(self.layout, "stage4", TEST_COMMIT),
        )

    def write_tables_manifest(self) -> Path:
        code, _, stderr = self.run_cli("manifest", "--set", "tables", "--zip", str(self.zip_path))
        self.assertEqual((code, stderr), (0, ""))
        return self.manifest_paths()[0]

    def rewrite_under(self, commit: str, layout: Layout, name: str) -> None:
        """Write the table `name` again from its own rows, under the code version `commit`."""
        rows = read_table(layout, name).to_pylist()
        checkout = version.Checkout(commit, True, None)
        with mock.patch.object(version, "current_checkout", return_value=checkout):
            write_table(layout, name, rows)

    def test_stage4_manifest_lists_outputs_inputs_and_builds_on(self):
        tables_path, stage4_path = write_both_manifests(self)

        self.assertEqual(stage4_path.name, "stage4@5ca1ab1e5ca1.json")
        text = stage4_path.read_text(encoding="utf-8")
        written = json.loads(text)
        self.assertEqual(text, json.dumps(written, sort_keys=True, indent=2) + "\n")
        self.assertEqual(set(written), TOP_KEYS | {"builds_on"})
        self.assertEqual(written["manifest_format"], 1)
        self.assertEqual(written["set"], "stage4")
        self.assertEqual(written["root"], str(self.layout.root.absolute()))
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
            [entry["path"] for entry in outputs],
            [f"stage4/tables/{name}.parquet" for name in STAGE4_TABLE_NAMES],
        )
        for name, entry in zip(STAGE4_TABLE_NAMES, outputs, strict=True):
            file = self.layout.stage4_tables / f"{name}.parquet"
            with self.subTest(table=name):
                self.assertEqual(set(entry), OUTPUT_KEYS)
                self.assertEqual(entry["bytes"], file.stat().st_size)
                self.assertEqual(entry["sha256"], sha256_of_bytes(file))
                self.assertEqual(entry["rows"], read_table(self.layout.stage4_view, name).num_rows)
                self.assertEqual(entry["code_version"], TEST_COMMIT)
                self.assertEqual(entry["python_version"], platform.python_version())
                self.assertEqual(entry["pyarrow_version"], pyarrow.__version__)
                self.assertEqual(entry["table_format"], str(TABLE_FORMATS[name]))
        inputs = written["inputs"]
        self.assertEqual(Counter(entry["kind"] for entry in inputs), {"submission": 5, "ledger": 1})
        self.assertNotIn("index", {entry["kind"] for entry in inputs})
        self.assertEqual([entry["path"] for entry in inputs], sorted(e["path"] for e in inputs))
        expected = {
            "stage4/fetch-log.jsonl": (self.layout.stage4_ledger, "ledger"),
            **{
                path.relative_to(self.layout.root).as_posix(): (path, "submission")
                for path in files_under(self.layout.stage4_bytes)
            },
        }
        self.assertEqual({entry["path"] for entry in inputs}, set(expected))
        for entry in inputs:
            file, kind = expected[entry["path"]]
            with self.subTest(path=entry["path"]):
                self.assertEqual(set(entry), INPUT_KEYS)
                self.assertEqual(entry["kind"], kind)
                self.assertEqual(entry["bytes"], file.stat().st_size)
                self.assertEqual(entry["sha256"], sha256_of_bytes(file))
        self.assertEqual(
            written["builds_on"],
            {"path": "manifests/tables@5ca1ab1e5ca1.json", "sha256": sha256_of_bytes(tables_path)},
        )

    def test_stage4_manifest_builds_on_the_tables_that_the_stamps_name(self):
        tables_path = self.write_tables_manifest()
        newer = version.Checkout("c" * 40, True, None)

        with mock.patch.object(version, "current_checkout", return_value=newer):
            code, _, stderr = self.run_cli("manifest", "--set", "stage4")

        self.assertEqual((code, stderr), (0, ""))
        path = manifest.manifest_path(self.layout, "stage4", newer.commit)
        self.assertEqual(path.name, "stage4@cccccccccccc.json")
        written = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(written["written_by"]["code_version"], newer.commit)
        self.assertEqual(
            written["builds_on"],
            {"path": "manifests/tables@5ca1ab1e5ca1.json", "sha256": sha256_of_bytes(tables_path)},
        )

    def test_stage4_manifest_needs_the_tables_manifest(self):
        code, stdout, stderr = self.run_cli("manifest", "--set", "stage4")

        self.assertEqual((code, stdout), (1, ""))
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertIn("manifests/tables@5ca1ab1e5ca1.json", stderr)
        self.assertEqual(stderr.count("\n"), 1)
        self.assertFalse(self.manifest_paths()[1].exists())

    def test_stage4_manifest_needs_the_ledger(self):
        self.write_tables_manifest()
        self.layout.stage4_ledger.unlink()

        code, stdout, stderr = self.run_cli("manifest", "--set", "stage4")

        self.assertEqual((code, stdout), (1, ""))
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertIn(str(self.layout.stage4_ledger), stderr)
        self.assertFalse(self.manifest_paths()[1].exists())

    def test_stage4_manifest_names_both_versions_when_the_tables_hold_two(self):
        self.rewrite_under(OTHER_COMMIT, self.layout, "sample")

        code, stdout, stderr = self.run_cli("manifest", "--set", "stage4")

        self.assertEqual((code, stdout), (1, ""))
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertIn(TEST_COMMIT, stderr)
        self.assertIn(OTHER_COMMIT, stderr)
        self.assertFalse(self.manifest_paths()[1].exists())

    def test_stage4_manifest_refuses_to_overwrite(self):
        _, stage4_path = write_both_manifests(self)
        original = stage4_path.read_bytes()

        code, stdout, stderr = self.run_cli("manifest", "--set", "stage4")

        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(stderr, f"error: {stage4_path} exists\n")
        self.assertEqual(stage4_path.read_bytes(), original)

    def test_stage4_takes_no_zip(self):
        runs = line_count(self.layout.runs)

        code, stdout, stderr = self.run_cli(
            "manifest", "--set", "stage4", "--zip", str(self.zip_path)
        )

        self.assertEqual((code, stdout), (2, ""))
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertEqual(stderr.count("\n"), 1)
        self.assertFalse(self.layout.manifests.exists())
        self.assertEqual(line_count(self.layout.runs), runs)

    def test_set_version_gives_the_one_version(self):
        self.assertEqual(manifest.set_version(self.layout.stage4_tables), TEST_COMMIT)
        self.assertEqual(manifest.set_version(self.layout.tables), TEST_COMMIT)

    def test_set_version_refuses_two_versions(self):
        self.rewrite_under(OTHER_COMMIT, self.layout.stage4_view, "links")

        with self.assertRaises(ValueError) as caught:
            manifest.set_version(self.layout.stage4_tables)

        self.assertIn(TEST_COMMIT, str(caught.exception))
        self.assertIn(OTHER_COMMIT, str(caught.exception))

    def test_set_version_needs_a_table(self):
        with tempfile.TemporaryDirectory() as name:
            empty = Path(name)
            (empty / "stray.txt").write_text("not a table", encoding="utf-8")
            for folder in (empty, empty / "missing"):
                with self.subTest(folder=folder.name), self.assertRaises(FileNotFoundError):
                    manifest.set_version(folder)

    def test_set_folder_is_the_stage4_tables_or_a_folder_of_the_root(self):
        self.assertEqual(manifest.set_folder(self.layout, "stage4"), self.layout.stage4_tables)
        for name in ("tables", "tables-stage1", "tables-stage2"):
            with self.subTest(set=name):
                self.assertEqual(manifest.set_folder(self.layout, name), self.layout.root / name)

    def test_find_manifest_names_the_manifest_of_the_stamped_version(self):
        tables_path, stage4_path = write_both_manifests(self)

        self.assertEqual(manifest.find_manifest(self.layout, "tables"), tables_path)
        self.assertEqual(manifest.find_manifest(self.layout, "stage4"), stage4_path)

    def test_find_manifest_needs_the_manifest(self):
        for set_name, path in zip(("tables", "stage4"), self.manifest_paths(), strict=True):
            with self.subTest(set=set_name), self.assertRaises(FileNotFoundError) as caught:
                manifest.find_manifest(self.layout, set_name)
            self.assertIn(str(path), str(caught.exception))
