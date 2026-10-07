"""Git plumbing for the wm hooks: snapshots of the working tree and diffs between them.

A snapshot is the tree object of the whole working tree, untracked files included and ignored
files excluded. It is written through a copy of the index, so the real index and the files stay
untouched. The done-gate diffs the implementer's starting snapshot against the current one, which
catches every change, whichever tool made it: Edit, Write, `sed -i`, a heredoc or `git apply`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

# git's empty tree, the base when a repository has no commits yet.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# A git invocation inside a shell command: its global options (-C, -c and flags), its subcommand
# and the subcommand's first argument.
INVOCATION = re.compile(
    r"\bgit((?:\s+-[Cc]\s+\S+|\s+--?[A-Za-z][\w-]*(?:=\S+)?)*)\s+([a-z][a-z-]*)(?:\s+(\S+))?"
)


def _timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("WM_GIT_TIMEOUT") or 20))
    except ValueError:
        return 20.0


# The seconds one git call may take. Claude Code lets an action through when a hook outlives its
# own timeout (30 seconds for the shortest), so a git that hangs, on a stuck lock or a wrapper on
# PATH that loops, has to fail here, where each hook applies its failure policy. WM_GIT_TIMEOUT
# changes it; snapshot() gives `git add` four times as long, because it reads the whole tree.
TIMEOUT_SECONDS = _timeout()


class GitTimeoutError(Exception):
    """Git didn't answer in time."""


def git(
    cwd: Path, *args: str, env: dict[str, str] | None = None, timeout: float = TIMEOUT_SECONDS
) -> str | None:
    """The command's stdout, or None if git failed or isn't installed. Raises GitTimeoutError if
    git hangs."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        command = " ".join(args)[:80]
        raise GitTimeoutError(
            f"git {command} didn't answer within {timeout:g} seconds; "
            "WM_GIT_TIMEOUT allows more for a slow repository"
        ) from error
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
        if git(root, "add", "--all", "--", ".", env=env, timeout=TIMEOUT_SECONDS * 4) is None:
            return None
        tree = git(root, "write-tree", env=env)
    return tree.strip() if tree else None


def is_tree(root: Path, object_id: str) -> bool:
    kind = git(root, "cat-file", "-t", object_id)
    return kind is not None and kind.strip() == "tree"


def head_tree(root: Path) -> str | None:
    tree = git(root, "rev-parse", "--verify", "--quiet", "HEAD^{tree}")
    return tree.strip() if tree else None


def head_commit(root: Path) -> str | None:
    """The commit HEAD points at, or None on a branch with no commits yet."""
    commit = git(root, "rev-parse", "--verify", "--quiet", "HEAD")
    return commit.strip() if commit else None


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
