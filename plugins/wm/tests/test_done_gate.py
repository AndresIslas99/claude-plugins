#!/usr/bin/env python3
"""Scenario tests for done_gate.py, in a throwaway git repository with fake gates.

    python3 plugins/wm/tests/test_done_gate.py

Run them with the same interpreter as the hooks (the system `python3`, which may be 3.9).
The fake lint gate fails when a file under src/ contains LINT_ERROR, and the fake test
command always passes. Both of the gate's entry points are covered: the PreToolUse hook on
SubagentHandback, and the SubagentStop fallback.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "scripts" / "done_gate.py"
STATE = Path(tempfile.gettempdir()) / "wm-done-gate"

FAKE_LINT = """\
import pathlib, sys
bad = [p for p in pathlib.Path("src").rglob("*") if p.is_file() and "LINT_ERROR" in p.read_text()]
print("lint errors in:", *bad) if bad else print("lint ok")
sys.exit(1 if bad else 0)
"""
CONFIG = {
    "gates": [{"run": "python3 fake_lint.py", "when": ["src/**"]}],
    "tests": [{"run": "python3 -c 'print(\"tests ok\")'", "when": ["src/**"]}],
}


def git(root: Path, *args: str) -> None:
    command = ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args]
    subprocess.run(command, cwd=root, check=True, capture_output=True)


def decision(payload: dict[str, object]) -> str:
    completed = subprocess.run(
        [sys.executable, str(GATE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return f"error: {completed.stderr.strip()}"
    if not completed.stdout.strip():
        return "allow"
    output = json.loads(completed.stdout)
    if "systemMessage" in output:
        return "warn"
    specific = output.get("hookSpecificOutput") or {}
    return str(specific.get("permissionDecision") or output.get("decision") or "unknown")


def main() -> int:
    shutil.rmtree(STATE, ignore_errors=True)
    results: list[tuple[str, str, str]] = []
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory)
        (repo / "fake_lint.py").write_text(FAKE_LINT)
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("VALUE = 1\n")
        (repo / ".claude").mkdir()
        config = repo / ".claude" / "working-model.json"
        config.write_text(json.dumps(CONFIG))
        git(repo, "init", "-q")
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "base")

        def scenario(name: str, event: str, agent: str, report: str, expected: str) -> None:
            payload: dict[str, object] = {"agent_id": agent, "cwd": str(repo)}
            payload["agent_type"] = (
                "wm:reviewer" if agent.startswith("reviewer") else "wm:implementer"
            )
            if event == "handback":
                payload.update(hook_event_name="PreToolUse", tool_name="SubagentHandback")
                payload["tool_input"] = {"message": report}
            else:
                payload.update(hook_event_name="SubagentStop", last_assistant_message=report)
            results.append((name, decision(payload), expected))

        scenario("handback reporting BLOCKED", "handback", "a1", "STATUS: BLOCKED", "allow")
        scenario("its SubagentStop is skipped", "stop", "a1", "STATUS: BLOCKED", "allow")
        scenario("stop reporting PARTIAL", "stop", "a2", "STATUS: PARTIAL", "allow")
        scenario("handback DONE, nothing changed", "handback", "a3", "**STATUS:** DONE", "allow")

        (repo / "src" / "broken.py").write_text("LINT_ERROR = True\n")
        scenario("handback DONE, the lint gate fails", "handback", "a4", "STATUS: DONE", "deny")
        scenario("second handback", "handback", "a4", "STATUS: DONE", "deny")
        scenario("third handback gives up with a warning", "handback", "a4", "STATUS: DONE", "warn")
        scenario("its SubagentStop is skipped", "stop", "a4", "STATUS: DONE", "allow")
        scenario("stop DONE with a failing gate", "stop", "a5", "STATUS: DONE", "block")
        scenario("handback without a STATUS line", "handback", "a6", "All finished.", "deny")
        scenario(
            "a reviewer's handback isn't gated", "handback", "reviewer1", "STATUS: DONE", "allow"
        )

        (repo / "src" / "broken.py").unlink()
        (repo / "src" / "view.ts").write_text("// @ts-ignore\nconst x: number = 'a';\n")
        scenario(
            "handback DONE with a TypeScript suppression", "handback", "a7", "STATUS: DONE", "deny"
        )

        (repo / "src" / "view.ts").unlink()
        (repo / "src" / "clean.py").write_text("VALUE = 2\n")
        scenario(
            "handback DONE, clean change: gates and tests",
            "handback",
            "a8",
            "STATUS: DONE",
            "allow",
        )
        scenario(
            "its SubagentStop doesn't run the gates again", "stop", "a8", "STATUS: DONE", "allow"
        )

        config.unlink()
        (repo / "src" / "broken.py").write_text("LINT_ERROR = True\n")
        scenario(
            "no config: gates aren't known, so they don't run",
            "handback",
            "a9",
            "STATUS: DONE",
            "allow",
        )
        (repo / "src" / "skip.py").write_text("import pytest\npytest.skip('later')\n")
        scenario(
            "no config: suppressions are still caught", "handback", "a10", "STATUS: DONE", "deny"
        )
    shutil.rmtree(STATE, ignore_errors=True)

    failures = [result for result in results if result[1] != result[2]]
    for name, got, expected in failures:
        print(f"FAIL {name}: got {got}, expected {expected}")
    print(f"{len(results) - len(failures)} of {len(results)} done-gate scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
