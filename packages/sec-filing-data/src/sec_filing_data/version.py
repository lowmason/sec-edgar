"""The code version: the commit of the git checkout that holds the running package.

Every command that writes under the root refuses to start unless the pinned paths have no
uncommitted change. So a table can name the one commit that made it.
"""

import functools
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pyarrow

# The paths from the top of the checkout. A change in any of them blocks a run.
PINNED_PATHS = ("packages/sec-filing-data", "pyproject.toml", "uv.lock", ".python-version")
NOT_RECORDED = "not recorded"
# The exit code of a refused command. No other outcome uses it.
REFUSED_EXIT = 3


@dataclass(frozen=True)
class Checkout:
    """The state of the checkout that holds the code.

    A clean checkout has its 40-character `commit`, `clean` True and no `problem`. A dirty one
    has its commit, `clean` False and a `problem` that names each changed pinned path. When no
    commit can be read, `commit` and `clean` are None and `problem` says why.
    """

    commit: str | None
    clean: bool | None
    problem: str | None


def _git(folder: Path | str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(folder), *arguments], capture_output=True, text=True, check=False
    )


def inspect_checkout(path: Path) -> Checkout:
    """Read the commit and the pinned-path changes of the checkout that holds `path`."""
    try:
        top = _git(path, "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            return _unreadable(f"{path} is not in a git checkout: {top.stderr.strip()}")
        folder = top.stdout.strip()
        head = _git(folder, "rev-parse", "--verify", "HEAD^{commit}")
        if head.returncode != 0:
            return _unreadable(f"git has no commit for {folder}: {head.stderr.strip()}")
        status = _git(
            folder, "status", "--porcelain=v1", "--untracked-files=all", "--", *PINNED_PATHS
        )
    except FileNotFoundError:
        return _unreadable("git is not installed")
    if status.returncode != 0:
        return _unreadable(f"git status failed for {folder}: {status.stderr.strip()}")
    commit = head.stdout.strip()
    # Each line is one change: two status characters, a space, then the path.
    changed = [line[3:] for line in status.stdout.splitlines()]
    if not changed:
        return Checkout(commit, True, None)
    return Checkout(commit, False, f"uncommitted changes in {', '.join(changed)}")


def _unreadable(problem: str) -> Checkout:
    return Checkout(None, None, problem)


@functools.cache
def current_checkout() -> Checkout:
    """The checkout of the running code, read once. Callers look this up on the module."""
    return inspect_checkout(Path(__file__).resolve().parent)


@dataclass(frozen=True)
class Stamp:
    """What a table records about the code that wrote it."""

    code_version: str | None
    python_version: str
    pyarrow_version: str


def current_stamp() -> Stamp:
    return Stamp(current_checkout().commit, platform.python_version(), pyarrow.__version__)
