#!/usr/bin/env python3
"""Checks that the wm working model is set up and working, and prints a report.

    doctor.py [project-directory]

The /wm:doctor skill runs it. It checks the hooks' scripts and Python, the Claude Code version,
the project's .claude/working-model.json (whether every gate command exists and every glob
matches a file, because a gate that never runs is a silent failure), the model routing, and the
receipts of recent hook decisions. It changes nothing, and it always exits 0.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_git
import wm_runtime

SCRIPTS = (
    "launch.sh",
    "wm_runtime.py",
    "wm_config.py",
    "wm_git.py",
    "agent_gate.py",
    "subagent_guard.py",
    "baseline.py",
    "done_gate.py",
    "agent_report.py",
    "session_context.py",
)
MIN_HANDBACK_VERSION = (2, 1, 271)
KNOWN_KEYS = {
    "$comment",
    "version",
    "gates",
    "tests",
    "leadOwned",
    "denyCommands",
    "paths",
    "protectedBranches",
    "testGlobs",
    "checkGlobs",
    "models",
    "fable",
    "gateBudgetSeconds",
}


def main() -> int:
    project = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else Path.cwd()
    lines: list[str] = ["# wm doctor", ""]
    try:
        lines += environment()
        lines += project_report(project)
        lines += receipts_report()
    except Exception as error:  # noqa: BLE001 - the doctor must always report something
        lines.append(f"✗ The doctor itself failed: {error}")
    print("\n".join(lines))
    return 0


def environment() -> list[str]:
    here = Path(__file__).resolve().parent
    lines = ["## Environment", ""]
    lines.append(f"✓ Python {sys.version.split()[0]} at {sys.executable}")
    if sys.version_info < (3, 9):  # noqa: UP036 - it diagnoses interpreters the hooks don't support
        lines.append("✗ The hooks need Python 3.9 or later; set WM_PYTHON to one.")
    missing = [name for name in SCRIPTS if not (here / name).is_file()]
    lines.append(
        f"✗ Missing hook scripts: {', '.join(missing)}"
        if missing
        else "✓ All hook scripts are present"
    )
    version = _claude_version()
    if version is None:
        lines.append("! Couldn't read the Claude Code version (`claude --version`).")
    elif version < MIN_HANDBACK_VERSION:
        lines.append(
            f"! Claude Code {'.'.join(map(str, version))} predates SubagentHandback (2.1.271): "
            "the done-gate runs only on SubagentStop."
        )
    else:
        lines.append(
            f"✓ Claude Code {'.'.join(map(str, version))}: in auto mode the done-gate runs on "
            "SubagentHandback, and in other modes on SubagentStop."
        )
    overrides = os.environ.get("WM_MODELS")
    if overrides:
        lines.append(f"✓ Machine-wide model overrides (WM_MODELS): {overrides}")
    lines.append(f"✓ State and receipts: {wm_runtime.state_dir()}")
    return lines + [""]


def project_report(project: Path) -> list[str]:
    lines = ["## Project", ""]
    root = wm_git.repository_root(project)
    if root is None:
        return lines + [
            f"! {project} isn't in a git repository: the done-gate has nothing to diff.",
            "",
        ]
    lines.append(f"✓ Repository: {root}")
    if wm_config.has_own_working_model(root):
        own = (
            "! This project ships its own copy of the working model's hooks (.claude/hooks/); the "
            "plugin stays out of its way. Disable the plugin here, or migrate the project to it."
        )
        return [*lines, own, ""]
    config_path = root / wm_config.CONFIG_FILE
    if not config_path.is_file():
        return lines + [
            "! Not adopted: there's no .claude/working-model.json, so no gates run. Run /wm:adopt.",
            "",
        ]
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except ValueError as error:
        return lines + [
            f"✗ .claude/working-model.json isn't valid JSON ({error}); the hooks use defaults.",
            "",
        ]
    unknown = sorted(set(raw) - KNOWN_KEYS) if isinstance(raw, dict) else []
    if unknown:
        lines.append(
            f"! Unknown keys in .claude/working-model.json, which are ignored: {', '.join(unknown)}"
        )
    config = wm_config.load(root)
    tracked = (wm_git.git(root, "ls-files") or "").splitlines()
    if not config["gates"] and not config["tests"]:
        lines.append("! No gates or tests are configured: the done-gate checks only integrity.")
    for group in ("gates", "tests"):
        for entry in config[group]:
            lines += _gate_report(group, entry, tracked)
    for rule in config["denyCommands"]:
        try:
            re.compile(str(rule["pattern"]))
        except re.error as error:
            lines.append(f"✗ denyCommands pattern {rule['pattern']!r} doesn't compile ({error}).")
    for key, path in config["paths"].items():
        if path and not (root / path).is_dir():
            lines.append(f"! paths.{key} ({path}) doesn't exist yet.")
    if config["models"]:
        lines.append(f"✓ Project model overrides: {config['models']}")
    lines.append(
        "✓ Fable consults per session: "
        f"{config['fableConsultsPerSession']}; gate time budget: {config['gateBudgetSeconds']} s"
    )
    return lines + [""]


def _gate_report(group: str, entry: dict[str, Any], tracked: list[str]) -> list[str]:
    command = str(entry["run"])
    first = command.split()[0] if command.split() else ""
    lines = []
    if first and shutil.which(first) is None:
        lines.append(
            f"✗ {group}: `{command}`: `{first}` isn't on PATH, so this check always fails."
        )
    globs = [g for g in entry.get("when") or [] if isinstance(g, str)]
    if globs:
        hits = sum(1 for path in tracked if wm_config.matches_any(path, globs))
        if hits == 0:
            lines.append(
                f"! {group}: `{command}`: its globs {globs} match no tracked file, so it never runs."
            )
        else:
            lines.append(f"✓ {group}: `{command}` covers {hits} tracked files")
    else:
        lines.append(f"✓ {group}: `{command}` runs on every change")
    return lines


def receipts_report() -> list[str]:
    lines = ["## Recent hook decisions (7 days)", ""]
    path = wm_runtime.state_dir() / "receipts.jsonl"
    if not path.exists():
        return lines + ["No receipts yet.", ""]
    cutoff = time.time() - 7 * 24 * 3600
    counts: Counter[tuple[str, str]] = Counter()
    errors: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("t", 0) < cutoff:
            continue
        counts[(str(entry.get("hook")), str(entry.get("decision")))] += 1
        if entry.get("decision") == "error":
            errors.append(
                f"- {time.strftime('%Y-%m-%d %H:%M', time.localtime(entry['t']))} {entry.get('hook')}: {entry.get('reason')}"
            )
    for (hook, decision), count in sorted(counts.items()):
        marker = "✗" if decision == "error" else "!" if decision in ("gave-up", "deny") else "✓"
        lines.append(f"{marker} {hook} {decision}: {count}")
    if errors:
        lines += [
            "",
            "Hook failures (the launcher applied each hook's failure policy):",
            *errors[-5:],
        ]
    return lines + [""]


def _claude_version() -> tuple[int, ...] | None:
    try:
        completed = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", completed.stdout)
    return tuple(int(part) for part in match.groups()) if match else None


if __name__ == "__main__":
    sys.exit(main())
