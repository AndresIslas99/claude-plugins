#!/usr/bin/env python3
"""Scenario tests for commit_gate.py, in throwaway git repositories.

    python3 plugins/wm/tests/test_commit_gate.py

The fake lint gate fails when a file under src/ contains LINT_ERROR, and the fake test command
fails while TESTS_FAIL exists. The payloads are the main session's Bash calls, except where a
test says otherwise.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from support import Suite, hanging_git, make_repository, run_hook

FAKE_LINT = """\
import pathlib, sys
bad = [p for p in pathlib.Path("src").rglob("*") if p.is_file() and "LINT_ERROR" in p.read_text()]
print("lint errors in:", *bad) if bad else print("lint ok")
sys.exit(1 if bad else 0)
"""
CONFIG: dict[str, Any] = {
    "gates": [{"run": "python3 fake_lint.py", "when": ["src/**"]}],
    "tests": [{"run": "test ! -e TESTS_FAIL", "when": ["src/**", "tests/**"]}],
}
FILES = {"fake_lint.py": FAKE_LINT, "src/app.py": "VALUE = 1\n"}


def main() -> int:
    suite = Suite("commit-gate")
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        repo = make_repository(base / "repo", FILES, CONFIG)
        data = base / "data"

        def bash(
            command: str,
            *,
            cwd: Path = repo,
            env: dict[str, str] | None = None,
            **extra: Any,
        ) -> Any:
            payload: dict[str, Any] = {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": command, "description": "x"},
                "cwd": str(cwd),
                "permission_mode": "default",
                "session_id": "s1",
            }
            payload.update(extra)
            return run_hook("commit_gate.py", payload, data=data, policy="open", env=env)

        (repo / "src" / "app.py").write_text("VALUE = 1  # LINT_ERROR\n")
        denied = bash("git add -A && git commit -m 'add a value'")
        suite.equal("a commit while a gate fails is denied", denied.decision, "deny")
        suite.contains("it says it's the commit gate", denied.reason, "wm commit gate")
        suite.contains("with the gate's output", denied.reason, "lint errors in: src/app.py")
        suite.contains("and the way out", denied.reason, "from their own terminal")
        for command in (
            "rtk git commit -am x",
            "git -c user.name=x commit -m x",
            "cd src && git commit --amend --no-edit",
        ):
            suite.equal(f"{command}: denied too", bash(command).decision, "deny")
        suite.equal(
            "git -C points it at another repository",
            bash(f"git -C {repo} commit -m x", cwd=base).decision,
            "deny",
        )
        for command in ("git status", "git diff --stat", "ls src", "echo committed"):
            suite.equal(f"{command}: not a commit, so it passes", bash(command).decision, "allow")
        suite.equal(
            "a subagent's commit is the guard's to deny",
            bash("git commit -m x", agent_id="a1", agent_type="wm:implementer").decision,
            "allow",
        )

        (repo / "src" / "app.py").write_text("VALUE = 2\n")
        (repo / "TESTS_FAIL").write_text("")
        suite.equal("the tests run once the gates pass", bash("git commit -am x").decision, "deny")
        (repo / "TESTS_FAIL").unlink()
        suite.equal(
            "a commit with passing checks goes through", bash("git commit -am x").decision, "allow"
        )

        (repo / "src" / "draft.py").write_text("LINT_ERROR = True\n")
        suite.equal(
            "an untracked file is checked too, as the checks see the working tree",
            bash("git commit -m x").decision,
            "deny",
        )
        (repo / "src" / "draft.py").unlink()

        started = time.monotonic()
        hung = bash("git commit -m x", env=hanging_git(base))
        elapsed = time.monotonic() - started
        suite.equal("a git that hangs: the commit is denied", hung.decision, "deny")
        suite.contains("saying the checks couldn't run", hung.reason, "couldn't run the checks")
        suite.check("within the git timeout", elapsed < 15, f"took {elapsed:.1f} seconds")

        plain = make_repository(base / "plain", FILES)
        (plain / "src" / "app.py").write_text("LINT_ERROR = 1\n")
        suite.equal(
            "a repository that hasn't adopted wm is left alone",
            bash("git commit -am x", cwd=plain).decision,
            "allow",
        )
        bare = make_repository(base / "no-checks", FILES, {"leadOwned": []})
        (bare / "src" / "app.py").write_text("LINT_ERROR = 1\n")
        suite.equal(
            "an adopted repository with no checks is left alone",
            bash("git commit -am x", cwd=bare).decision,
            "allow",
        )
        suite.equal(
            "outside any repository it passes",
            bash("git commit -m x", cwd=base).decision,
            "allow",
        )
    return suite.finish()


if __name__ == "__main__":
    sys.exit(main())
