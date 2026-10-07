"""Git plumbing for the wm hooks: snapshots of the working tree and diffs between them.

A snapshot is the tree object of the whole working tree, untracked files included and ignored
files excluded. It is written through a copy of the index, so the real index and the files stay
untouched. The done-gate diffs the implementer's starting snapshot against the current one, which
catches every change, whichever tool made it: Edit, Write, `sed -i`, a heredoc or `git apply`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path


def git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> str | None:
    """The command's stdout, or None if git failed or isn't installed."""
    try:
        completed = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=False, env=env
        )
    except OSError:
        return None
    return completed.stdout if completed.returncode == 0 else None


def repository_root(cwd: Path) -> Path | None:
    output = git(cwd, "rev-parse", "--show-toplevel")
    return Path(output.strip()) if output and output.strip() else None


def snapshot(root: Path) -> str | None:
    """The tree object of the working tree as it is now."""
    index = git(root, "rev-parse", "--git-path", "index")
    if index is None:
        return None
    index_path = Path(index.strip())
    if not index_path.is_absolute():
        index_path = root / index_path
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory) / "index"
        if index_path.exists():
            shutil.copyfile(index_path, temporary)  # keeps the stat cache, so `add` stays fast
        env = dict(os.environ, GIT_INDEX_FILE=str(temporary))
        if git(root, "add", "--all", "--", ".", env=env) is None:
            return None
        tree = git(root, "write-tree", env=env)
    return tree.strip() if tree else None


def is_tree(root: Path, object_id: str) -> bool:
    kind = git(root, "cat-file", "-t", object_id)
    return kind is not None and kind.strip() == "tree"


def head_tree(root: Path) -> str | None:
    tree = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{tree}")
    return tree.strip() if tree else None


def changes(root: Path, base: str, current: str) -> list[tuple[str, str]]:
    """(status, path) for every file that differs between two trees; status is A, M, D or T."""
    output = git(root, "diff", "--name-status", "--no-renames", "-z", base, current)
    if not output:
        return []
    fields = output.split("\0")
    return [(fields[i][:1], fields[i + 1]) for i in range(0, len(fields) - 1, 2) if fields[i]]


def line_changes(root: Path, base: str, current: str) -> Iterator[tuple[str, str, str]]:
    """(sign, path, text) for every added (+) or removed (-) line between two trees.

    File headers are read only between a `diff --git` line and the first hunk, so a removed line
    whose text starts with "--" isn't taken for one.
    """
    diff = git(
        root,
        "-c",
        "core.quotePath=false",
        "diff",
        "--unified=0",
        "--no-color",
        "--no-ext-diff",
        "--no-renames",
        base,
        current,
    )
    path = None
    in_header = False
    for line in (diff or "").splitlines():
        if line.startswith("diff --git "):
            in_header, path = True, None
        elif in_header:
            if line.startswith(("--- a/", "+++ b/")):
                path = line[6:]
            elif line.startswith("@@"):
                in_header = False
        elif path is not None and line[:1] in ("+", "-"):
            yield line[0], path, line[1:]
