import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pyarrow

from sec_filing_data import cli, version
from sec_filing_data.layout import Layout, record_step
from sec_filing_data.version import Checkout, inspect_checkout
from tests import TEST_COMMIT

GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@t",
    "-c",
    "commit.gpgsign=false",
    "-c",
    "core.hooksPath=/dev/null",
]
MODULE_PATH = Path("packages/sec-filing-data/src/sec_filing_data")

# One argv for each command that writes under the root, without `--out`.
WRITING_ARGV: list[list[str]] = [
    ["index", "--zip", "missing.zip"],
    ["sample"],
    ["fetch"],
    ["refetch", "--accession", "A"],
    ["envelopes"],
    ["facts"],
    ["ownership"],
    ["compare-refetches"],
    ["build-fetches"],
    ["manifest", "--set", "tables", "--zip", "missing.zip"],
]


def git(folder: Path, *args: str) -> str:
    result = subprocess.run(
        [*GIT, "-C", str(folder), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def make_repo(folder: Path) -> Path:
    """Commit the pinned files and two others in `folder`. Gives the module folder."""
    files = {
        MODULE_PATH / "x.py": "x = 1\n",
        Path("pyproject.toml"): "[project]\n",
        Path("uv.lock"): "version = 1\n",
        Path(".python-version"): "3.14\n",
        Path("README.md"): "readme\n",
        Path(".gitignore"): "__pycache__/\n",
    }
    for relative, text in files.items():
        (folder / relative).parent.mkdir(parents=True, exist_ok=True)
        (folder / relative).write_text(text, encoding="utf-8")
    git(folder, "init", "--quiet")
    git(folder, "add", "--all")
    git(folder, "commit", "--quiet", "--message", "first")
    return folder / MODULE_PATH


class VersionTestCase(unittest.TestCase):
    def make_folder(self) -> Path:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name).resolve()

    def make_module(self) -> Path:
        return make_repo(self.make_folder())

    def run_main(self, argv: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(argv)
        return status, stdout.getvalue(), stderr.getvalue()


class InspectCheckoutTests(VersionTestCase):
    def test_a_clean_tree_gives_the_commit(self):
        module = self.make_module()

        checkout = inspect_checkout(module)

        commit = git(module, "rev-parse", "HEAD")
        self.assertEqual(len(commit), 40)
        self.assertEqual(checkout, Checkout(commit, True, None))

    def test_changes_in_the_pinned_paths_refuse(self):
        def edit_the_lock(root: Path) -> None:
            with (root / "uv.lock").open("a", encoding="utf-8") as lock:
                lock.write("edit\n")

        def stage_a_module_edit(root: Path) -> None:
            (root / MODULE_PATH / "x.py").write_text("x = 2\n", encoding="utf-8")
            git(root, "add", str(MODULE_PATH / "x.py"))

        def add_an_untracked_file(root: Path) -> None:
            (root / "packages" / "sec-filing-data" / "new.py").write_text("", encoding="utf-8")

        cases = {
            "uv.lock": edit_the_lock,
            "packages/sec-filing-data/src/sec_filing_data/x.py": stage_a_module_edit,
            "packages/sec-filing-data/new.py": add_an_untracked_file,
        }
        for path, change in cases.items():
            with self.subTest(path=path):
                module = self.make_module()
                root = module.parents[3]
                change(root)

                checkout = inspect_checkout(module)

                self.assertEqual(checkout.commit, git(root, "rev-parse", "HEAD"))
                self.assertIs(checkout.clean, False)
                self.assertIn(path, checkout.problem)

    def test_edits_to_pyproject_and_python_version_refuse(self):
        for path in ("pyproject.toml", ".python-version"):
            with self.subTest(path=path):
                module = self.make_module()
                root = module.parents[3]
                with (root / path).open("a", encoding="utf-8") as pinned:
                    pinned.write("edit\n")

                checkout = inspect_checkout(module)

                self.assertEqual(checkout.commit, git(root, "rev-parse", "HEAD"))
                self.assertIs(checkout.clean, False)
                self.assertIn(path, checkout.problem)

    def test_changes_elsewhere_do_not_refuse(self):
        module = self.make_module()
        root = module.parents[3]
        (root / "README.md").write_text("changed\n", encoding="utf-8")
        (root / "specs").mkdir()
        (root / "specs" / "new.md").write_text("new\n", encoding="utf-8")
        (module / "__pycache__").mkdir()
        (module / "__pycache__" / "x.pyc").write_bytes(b"\0")

        checkout = inspect_checkout(module)

        self.assertEqual(checkout, Checkout(git(root, "rev-parse", "HEAD"), True, None))

    def test_no_repository_refuses(self):
        folder = self.make_folder()
        module = self.make_module()
        # A repository above the temporary folder must not count. With no `git` on the PATH, a
        # repository has no readable commit either.
        cases = {
            "a plain folder": (folder, {"GIT_CEILING_DIRECTORIES": str(folder.parent)}),
            "no git program": (module, {"PATH": ""}),
        }
        for name, (path, environment) in cases.items():
            with self.subTest(case=name), mock.patch.dict(os.environ, environment):
                checkout = inspect_checkout(path)

                self.assertEqual((checkout.commit, checkout.clean), (None, None))
                self.assertTrue(checkout.problem)


class RealCheckoutTests(VersionTestCase):
    def test_the_real_checkout_comes_from_the_module_path(self):
        # The suite patches `version.current_checkout`, so the real function runs in a
        # subprocess. Its current folder is no repository, and nothing patches it.
        code = (
            "import json\n"
            "from sec_filing_data import version\n"
            "first = version.current_checkout()\n"
            "second = version.current_checkout()\n"
            "print(json.dumps({\n"
            "    'commit': first.commit,\n"
            "    'clean': first.clean,\n"
            "    'problem': first.problem,\n"
            "    'same_object': first is second,\n"
            "    'cache': version.current_checkout.cache_info()._asdict(),\n"
            "}))\n"
        )
        folder = self.make_folder()
        # A repository above the temporary folder must not count.
        environment = {**os.environ, "GIT_CEILING_DIRECTORIES": str(folder.parent)}

        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=False,
            cwd=folder,
            env=environment,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        found = json.loads(result.stdout)
        module_folder = Path(version.__file__).resolve().parent
        top = git(module_folder, "rev-parse", "--show-toplevel")
        self.assertEqual(found["commit"], git(top, "rev-parse", "HEAD"))
        self.assertIsInstance(found["clean"], bool)
        self.assertTrue(found["same_object"])
        self.assertEqual((found["cache"]["misses"], found["cache"]["hits"]), (1, 1))


class RefusalTests(VersionTestCase):
    def test_a_refused_command_writes_nothing(self):
        module = self.make_module()
        (module.parents[3] / "uv.lock").write_text("edit\n", encoding="utf-8")
        checkouts = {
            "a changed path": (inspect_checkout(module), "uv.lock"),
            "no git": (Checkout(None, None, "no git"), "no git"),
        }
        for name, (checkout, reason) in checkouts.items():
            for argv in WRITING_ARGV:
                with self.subTest(checkout=name, command=argv[0]):
                    root = self.make_folder() / "root"
                    root.mkdir()

                    with (
                        mock.patch.object(version, "current_checkout", lambda: checkout),
                        mock.patch.dict(os.environ),
                    ):
                        os.environ.pop(cli.USER_AGENT_VARIABLE, None)
                        status, stdout, stderr = self.run_main([*argv, "--out", str(root)])

                    self.assertEqual(status, version.REFUSED_EXIT)
                    self.assertEqual(stdout, "")
                    self.assertEqual(stderr, f"error: refused: {checkout.problem}\n")
                    self.assertIn(reason, stderr)
                    self.assertEqual(os.listdir(root), [])

    def test_read_only_commands_run_on_a_dirty_tree(self):
        dirty = Checkout(TEST_COMMIT, False, "uncommitted changes in uv.lock")
        read_only = (
            ["report"],
            ["check-stage1"],
            ["check-frozen", "--folder", "tables-stage2"],
            # An empty manifest gives the `manifest:` line and exit 1: no refusal, no traceback.
            ["verify", "--manifest", os.devnull],
        )
        for argv in read_only:
            with self.subTest(command=argv[0]):
                root = self.make_folder() / "root"

                with mock.patch.object(version, "current_checkout", lambda: dirty):
                    status, _, stderr = self.run_main([*argv, "--out", str(root)])

                self.assertNotEqual(status, version.REFUSED_EXIT)
                self.assertEqual(stderr, "")
                step = json.loads((root / "runs.jsonl").read_text(encoding="utf-8"))
                self.assertEqual(step["step"], argv[0])
                self.assertEqual(step["code_version"], TEST_COMMIT)
                self.assertIs(step["tree_clean"], False)


class RunLineTests(VersionTestCase):
    def test_run_lines_carry_the_code_version(self):
        layout = Layout(self.make_folder() / "root")

        with record_step(layout, "step"):
            pass
        with (
            mock.patch.object(version, "current_checkout", lambda: Checkout(None, None, "no git")),
            record_step(layout, "step"),
        ):
            pass

        with_commit, without_commit = (
            json.loads(line) for line in layout.runs.read_text(encoding="utf-8").splitlines()
        )
        self.assertEqual(with_commit["code_version"], TEST_COMMIT)
        self.assertIs(with_commit["tree_clean"], True)
        self.assertIn("code_version", without_commit)
        self.assertIsNone(without_commit["code_version"])
        self.assertIn("tree_clean", without_commit)
        self.assertIsNone(without_commit["tree_clean"])


class StampTests(unittest.TestCase):
    def test_the_stamp_names_the_commit_and_both_versions(self):
        stamp = version.current_stamp()

        self.assertEqual(
            stamp, version.Stamp(TEST_COMMIT, platform.python_version(), pyarrow.__version__)
        )

    def test_the_stamp_has_no_commit_when_none_is_readable(self):
        with mock.patch.object(version, "current_checkout", lambda: Checkout(None, None, "x")):
            self.assertIsNone(version.current_stamp().code_version)


if __name__ == "__main__":
    unittest.main()
