#!/usr/bin/env python3
"""PreToolUse hook on Bash: the lead can't commit while the project's checks fail.

The lead does decided work inline (T1 and T2), where the implementer's done-gate doesn't see
it, so this gate checks that work where it lands. When the main session runs `git commit`, it
runs the project's gates, then its tests (wm_checks.py), for every file that differs from HEAD:
staged, unstaged and untracked, because the checks run on the working tree. If they fail, it
denies the commit with their output.

It acts only on the main session's commits, in a project with gates or tests in
.claude/working-model.json; subagents can't commit at all (subagent_guard.py). Every other
command passes untouched. The launcher runs it fail-open, so a broken interpreter never blocks
the lead's other commands; a commit whose checks can't run is denied here instead.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_checks
import wm_config
import wm_git
import wm_runtime

DIRECTORY = re.compile(r"(?:^|\s)-C\s+(\S+)")


def handle(payload: dict[str, Any]) -> None:
    if payload.get("agent_id") or payload.get("agent_type"):
        return  # a subagent: subagent_guard.py denies its commits outright
    command = str((payload.get("tool_input") or {}).get("command") or "")
    commits = [m for m in wm_git.INVOCATION.finditer(command) if m.group(2) == "commit"]
    if not commits:
        return
    cwd = Path(str(payload.get("cwd") or "."))
    where = DIRECTORY.search(commits[0].group(1) or "")
    directory = cwd / where.group(1).strip("'\"") if where else cwd
    try:
        checked, failures = _check(directory)
    except Exception as error:  # noqa: BLE001 - a commit whose checks can't run is denied
        checked, failures = [], [f"The commit gate couldn't run the checks ({error})."]
    if failures is None:
        return  # not an adopted repository, or one with no checks configured
    if not failures:
        wm_runtime.receipt("commit_gate", payload, "pass", ", ".join(checked))
        return
    reason = (
        "wm commit gate: the project's checks fail, so this commit would record a failure:\n\n"
        + "\n\n".join(failures)
        + "\n\nFix the causes, then commit again. If the user wants this commit anyway, they can "
        "make it from their own terminal."
    )
    wm_runtime.receipt("commit_gate", payload, "deny", "; ".join(failures)[:400])
    wm_runtime.pre_tool("deny", reason)


def _check(directory: Path) -> tuple[list[str], list[str] | None]:
    """(the commands that ran, the failures), or None for the failures when there's nothing to
    check."""
    root = wm_config.repository_root(directory)
    if root is None or not wm_config.adopted(root):
        return [], None
    config = wm_config.load(root)
    if not config["gates"] and not config["tests"]:
        return [], None
    current = wm_git.snapshot(root)
    if current is None:
        raise RuntimeError("it couldn't snapshot the working tree")
    base = wm_git.head_tree(root) or wm_git.EMPTY_TREE
    changed = [path for _, path in wm_git.changes(root, base, current)]
    return wm_checks.run(root, changed, config)


if __name__ == "__main__":
    sys.exit(wm_runtime.run("commit_gate", handle, fail_closed=False))
