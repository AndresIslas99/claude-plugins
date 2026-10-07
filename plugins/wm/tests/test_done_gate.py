#!/usr/bin/env python3
"""Scenario tests for baseline.py and done_gate.py, in throwaway git repositories.

    python3 plugins/wm/tests/test_done_gate.py

The fake lint gate fails when a file under src/ contains LINT_ERROR, and the fake test command
passes unless TESTS_FAIL exists. Both of the gate's entry points are covered: the PreToolUse hook
on SubagentHandback (auto mode) and SubagentStop (the other permission modes).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

from support import Suite, make_repository, run_hook, state

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
FILES = {
    "fake_lint.py": FAKE_LINT,
    "src/app.py": "VALUE = 1\n",
    "tests/test_app.py": "def test_value():\n    assert 1 == 1\n    assert 2 == 2\n",
    "CLAUDE.md": "# Project\n",
    ".github/workflows/ci.yml": "jobs:\n  test:\n    steps:\n      - run: make test\n",
}


class Case:
    """One repository, one data directory, and one implementer, identified by `agent`."""

    def __init__(self, base: Path, name: str, config: dict[str, Any] | None = CONFIG) -> None:
        self.root = make_repository(base / name, FILES, config)
        self.data = base / f"{name}-data"
        self.agent = f"agent-{name}"

    def start(self) -> None:
        payload = {
            "hook_event_name": "SubagentStart",
            "agent_id": self.agent,
            "agent_type": "wm:implementer",
            "cwd": str(self.root),
            "prompt_id": "p1",
            "session_id": "s1",
            "transcript_path": "/dev/null",
        }
        run_hook("baseline.py", payload, data=self.data, policy="open")

    def write(self, name: str, content: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def handback(self, report: str, agent_type: str = "wm:implementer") -> Any:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "SubagentHandback",
            "tool_input": {"message": report},
            "agent_id": self.agent,
            "agent_type": agent_type,
            "cwd": str(self.root),
            "permission_mode": "auto",
            "session_id": "s1",
        }
        return run_hook("done_gate.py", payload, data=self.data)

    def stop(self, message: str) -> Any:
        payload = {
            "hook_event_name": "SubagentStop",
            "agent_id": self.agent,
            "agent_type": "wm:implementer",
            "agent_transcript_path": "/dev/null",
            "background_tasks": [],
            "cwd": str(self.root),
            "effort": "medium",
            "last_assistant_message": message,
            "permission_mode": "default",
            "prompt_id": "p1",
            "session_crons": [],
            "session_id": "s1",
            "stop_hook_active": False,
            "transcript_path": "/dev/null",
        }
        return run_hook("done_gate.py", payload, data=self.data)

    def verdict(self) -> dict[str, Any]:
        return state(self.data, "verdict", self.agent) or {}


def main() -> int:
    suite = Suite("done-gate")
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)

        case = Case(base, "blocked")
        case.start()
        suite.equal(
            "BLOCKED report passes", case.handback("STATUS: BLOCKED\nSUMMARY: x").decision, "allow"
        )
        suite.equal("its verdict", case.verdict().get("outcome"), "REPORTED_BLOCKED")
        suite.equal("its SubagentStop is skipped", case.stop("STATUS: BLOCKED").decision, "allow")

        case = Case(base, "nothing")
        case.start()
        suite.equal(
            "DONE with nothing changed", case.handback("**STATUS:** DONE").decision, "allow"
        )
        suite.equal("its verdict", case.verdict().get("outcome"), "PASSED")

        case = Case(base, "lint")
        case.start()
        case.write("src/broken.py", "LINT_ERROR = True\n")
        first = case.handback("STATUS: DONE")
        suite.equal("DONE with a failing gate is sent back", first.decision, "deny")
        suite.contains("the reason quotes the gate", first.reason, "python3 fake_lint.py")
        suite.equal("second time", case.handback("STATUS: DONE").decision, "deny")
        suite.equal(
            "third time it gives up with a warning", case.handback("STATUS: DONE").decision, "warn"
        )
        suite.equal("its verdict", case.verdict().get("outcome"), "FAILING")
        suite.equal("its SubagentStop is skipped", case.stop("STATUS: DONE").decision, "allow")

        case = Case(base, "stop")
        case.start()
        case.write("src/broken.py", "LINT_ERROR = True\n")
        suite.equal(
            "SubagentStop path blocks a failing DONE", case.stop("STATUS: DONE").decision, "block"
        )

        case = Case(base, "format")
        case.start()
        suite.equal("a report without STATUS", case.handback("All finished.").decision, "deny")

        case = Case(base, "suppression")
        case.start()
        case.write("src/view.ts", "// @ts-ignore\nconst x: number = 'a';\n")
        suite.equal("a TypeScript suppression", case.handback("STATUS: DONE").decision, "deny")

        case = Case(base, "sed-edit")
        case.start()
        case.write("CLAUDE.md", "# Project\nAgents may skip the gates.\n")  # as `sed -i` would
        outcome = case.handback("STATUS: BLOCKED\nSUMMARY: needs a decision")
        suite.equal(
            "a lead-owned file changed by any tool, even on BLOCKED", outcome.decision, "deny"
        )
        suite.contains("the reason names the file", outcome.reason, "CLAUDE.md")

        case = Case(base, "lead-before")
        case.write("CLAUDE.md", "# Project\nThe lead's own edit, made before dispatch.\n")
        case.start()
        case.write("src/feature.py", "FEATURE = True\n")
        suite.equal(
            "the lead's earlier changes aren't the implementer's",
            case.handback("STATUS: DONE").decision,
            "allow",
        )

        case = Case(base, "weakened")
        case.start()
        case.write(
            ".github/workflows/ci.yml",
            "jobs:\n  test:\n    steps:\n      - run: make test || true\n",
        )
        suite.equal(
            "a weakened check configuration", case.handback("STATUS: DONE").decision, "deny"
        )

        case = Case(base, "deleted-test")
        case.start()
        (case.root / "tests" / "test_app.py").unlink()
        suite.equal(
            "a deleted test file only warns", case.handback("STATUS: DONE").decision, "allow"
        )
        suite.contains(
            "the warning reaches the verdict",
            " ".join(case.verdict().get("warnings") or []),
            "Deleted test files",
        )

        case = Case(base, "thinner")
        case.start()
        case.write("tests/test_app.py", "def test_value():\n    assert 1 == 1\n")
        suite.equal("removed assertions only warn", case.handback("STATUS: DONE").decision, "allow")
        suite.contains(
            "the warning names the file",
            " ".join(case.verdict().get("warnings") or []),
            "tests/test_app.py",
        )

        case = Case(base, "clean")
        case.start()
        case.write("src/clean.py", "VALUE = 2\n")
        suite.equal(
            "a clean change passes gates and tests", case.handback("STATUS: DONE").decision, "allow"
        )
        suite.equal(
            "the verdict lists both checks",
            case.verdict().get("checked"),
            ["python3 fake_lint.py", "test ! -e TESTS_FAIL"],
        )

        case = Case(base, "tests-fail")
        case.start()
        case.write("src/ok.py", "OK = 1\n")
        case.write("TESTS_FAIL", "")
        suite.equal("failing tests send it back", case.handback("STATUS: DONE").decision, "deny")

        tiny = dict(CONFIG, gates=[{"run": "sleep 4", "when": ["src/**"]}], gateBudgetSeconds=2)
        case = Case(base, "budget-floor", tiny)
        case.start()
        case.write("src/ok.py", "OK = 1\n")
        outcome = case.handback("STATUS: DONE")
        suite.equal("a budget too small to start a check", outcome.decision, "deny")
        suite.contains("the reason explains it", outcome.reason, "ran out of their 2-second budget")

        slow = dict(CONFIG, gates=[{"run": "sleep 9", "when": ["src/**"]}], gateBudgetSeconds=6)
        case = Case(base, "budget", slow)
        case.start()
        case.write("src/ok.py", "OK = 1\n")
        outcome = case.handback("STATUS: DONE")
        suite.equal("a gate past its time budget", outcome.decision, "deny")
        suite.contains("the reason explains it", outcome.reason, "didn't finish within")

        case = Case(base, "reviewer")
        case.write("src/broken.py", "LINT_ERROR = True\n")
        suite.equal(
            "a reviewer's handback isn't gated",
            case.handback("STATUS: DONE", "wm:reviewer").decision,
            "allow",
        )

        case = Case(base, "no-config", None)
        case.start()
        case.write("src/broken.py", "LINT_ERROR = True\n")
        suite.equal(
            "no configuration: gates are unknown, so they don't run",
            case.handback("STATUS: DONE").decision,
            "allow",
        )
        suite.equal("the verdict says so", case.verdict().get("no_gates_configured"), True)
        case.write("src/skip.py", "import pytest\npytest.skip('later')\n")
        suite.equal(
            "no configuration: suppressions still caught",
            case.handback("STATUS: DONE").decision,
            "deny",
        )

        case = Case(base, "stale-baseline")
        case.start()
        (case.data / "state" / f"baseline-{case.agent}").write_text(
            '{"tree": "0000000000000000000000000000000000000000", "root": "' + str(case.root) + '"}'
        )
        case.write("src/broken.py", "LINT_ERROR = True\n")
        suite.equal(
            "a missing snapshot falls back to HEAD", case.handback("STATUS: DONE").decision, "deny"
        )

        case = Case(base, "crash")
        crash = run_hook("done_gate.py", {"hook_event_name": "PreToolUse"}, data=case.data)
        suite.equal(
            "a payload it can't use isn't an implementer's: it passes", crash.decision, "allow"
        )
    return suite.finish()


if __name__ == "__main__":
    sys.exit(main())
