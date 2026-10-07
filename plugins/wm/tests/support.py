"""Helpers for the wm hook tests: run a hook the way Claude Code does, and build repositories.

Hooks run through launch.sh with the interpreter running the tests (WM_PYTHON), so the suite
proves the hooks work on that Python; CI runs it on 3.9 and on a current version. Each run gets
its own CLAUDE_PLUGIN_DATA, so no state leaks between tests or into a real installation.

The payloads carry the fields Claude Code 2.1.292 was seen sending (2026-10-07), so the tests
exercise the shapes the hooks will really get.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
LAUNCHER = SCRIPTS / "launch.sh"


class Outcome:
    """What a hook did: its exit code, its parsed JSON output and its stderr."""

    def __init__(self, completed: subprocess.CompletedProcess[str]) -> None:
        self.code = completed.returncode
        self.stderr = completed.stderr
        self.output: dict[str, Any] = (
            json.loads(completed.stdout) if completed.stdout.strip() else {}
        )

    @property
    def specific(self) -> dict[str, Any]:
        return self.output.get("hookSpecificOutput") or {}

    @property
    def decision(self) -> str:
        """allow, deny, ask, block, warn (gave up and let it pass), context, or exit-2."""
        if self.code == 2:
            return "exit-2"
        if "systemMessage" in self.output:
            return "warn"
        decision = self.specific.get("permissionDecision") or self.output.get("decision")
        if decision:
            return str(decision)
        return "context" if self.specific.get("additionalContext") else "allow"

    @property
    def reason(self) -> str:
        return str(
            self.specific.get("permissionDecisionReason")
            or self.output.get("reason")
            or self.stderr
        )

    @property
    def context(self) -> str:
        return str(self.specific.get("additionalContext") or "")

    @property
    def updated_input(self) -> dict[str, Any] | None:
        return self.specific.get("updatedInput")


def run_hook(
    script: str,
    payload: dict[str, Any],
    *,
    data: Path,
    policy: str = "closed",
    env: dict[str, str] | None = None,
    args: tuple[str, ...] = (),
) -> Outcome:
    environment = dict(os.environ, CLAUDE_PLUGIN_DATA=str(data), WM_PYTHON=sys.executable)
    environment.pop("WM_MODELS", None)
    environment.update(env or {})
    completed = subprocess.run(
        ["bash", str(LAUNCHER), policy, script, *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    return Outcome(completed)


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def make_repository(
    root: Path, files: dict[str, str], config: dict[str, Any] | None = None
) -> Path:
    """A git repository with `files` committed, and `config` as .claude/working-model.json."""
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    if config is not None:
        (root / ".claude").mkdir(exist_ok=True)
        (root / ".claude" / "working-model.json").write_text(json.dumps(config))
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    return root


def state(data: Path, kind: str, key: str) -> dict[str, Any] | None:
    path = data / "state" / f"{kind}-{key}"
    return json.loads(path.read_text()) if path.exists() else None


class Suite:
    """Collects checks and prints the failures; main() returns its exit code."""

    def __init__(self, title: str) -> None:
        self.title = title
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))

    def equal(self, name: str, got: object, expected: object) -> None:
        self.check(name, got == expected, f"got {got!r}, expected {expected!r}")

    def contains(self, name: str, text: str, part: str) -> None:
        self.check(name, part in text, f"{part!r} not in {text[:300]!r}")

    def finish(self) -> int:
        failures = [r for r in self.results if not r[1]]
        for name, _, detail in failures:
            print(f"FAIL {self.title}: {name}: {detail}")
        print(
            f"{len(self.results) - len(failures)} of {len(self.results)} {self.title} checks passed"
        )
        return 1 if failures else 0
