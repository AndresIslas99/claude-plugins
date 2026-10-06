#!/usr/bin/env python3
"""PreToolUse hook that keeps the wm agents within their roles.

    subagent_guard.py [implementer | advisor | read-only]

The role comes from the payload's `agent_type` (wm:implementer, wm:fable-advisor, and the
read-only wm:reviewer, wm:scout and wm:researcher). An argument overrides it, as the tests do.
Any other agent, and the main session, pass untouched.

The wm agents don't change version control, dependencies, secrets, remote systems or the
machine's environment, and they write only where their role allows. Those are the lead's
decisions; a denied agent reports the need instead. This guards against mistakes, not
against an adversary: a determined shell command can get around a pattern list.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config

# Git subcommands that only read. Every other subcommand changes the repository or a remote.
READ_ONLY_GIT = frozenset(
    {
        "blame",
        "cat-file",
        "check-ignore",
        "describe",
        "diff",
        "for-each-ref",
        "grep",
        "help",
        "log",
        "ls-files",
        "ls-tree",
        "merge-base",
        "name-rev",
        "rev-list",
        "rev-parse",
        "shortlog",
        "show",
        "status",
        "version",
    }
)
# `git`, then any global options (-C <path>, -c <key=value>, --no-pager, ...), then the subcommand.
GIT_INVOCATION = re.compile(
    r"\bgit((?:\s+-[Cc]\s+\S+|\s+--?[A-Za-z][\w-]*(?:=\S+)?)*)\s+([a-z][a-z-]*)"
)

BASH_RULES = (
    (r"--no-verify\b", "Git hooks are quality gates and are never skipped."),
    (
        (
            r"\buv\s+(add|remove|lock)\b|\buv\s+pip\b|\bpip3?\s+install\b|\bpoetry\s+(add|remove)\b"
            r"|\b(npm|pnpm|yarn|bun)\s+(add|install|i|remove|uninstall)\b"
            r"|\bcargo\s+(add|remove|install)\b|\bgo\s+(get|install)\b"
            r"|\b(gem|brew)\s+install\b|\bbundle\s+add\b"
        ),
        "Dependencies are the lead's decision. Report what you need instead.",
    ),
    (r"\bsops\b", "Secrets stay encrypted."),
    (r"\b(gh|ssh|scp)\b", "Remote systems are the lead's."),
    (
        r"\brm\s+(-\w+\s+)*(-\w*[rR]|--recursive)",
        "Recursive deletes are the lead's. Report what should go.",
    ),
    (
        (
            r"\bdocker\s+(system\s+prune|(volume|image|container)\s+(rm|prune)|rmi?\b)"
            r"|\bdocker\s+compose\b[^|;&\n]*\bdown\b[^|;&\n]*(\s-v\b|--volumes)"
        ),
        "Removing containers, images or volumes is the lead's call.",
    ),
    (r"\bcolima\s+(stop|delete)\b", "Stopping the Docker VM affects the user's environment."),
    (
        r"\b(curl|wget)\b[^|\n]*\|\s*(ba|z)?sh\b",
        "Piping a download into a shell is never allowed.",
    ),
)


def main() -> int:
    payload = json.load(sys.stdin)
    role = (
        sys.argv[1]
        if len(sys.argv) > 1
        else wm_config.role_for(str(payload.get("agent_type") or ""))
    )
    if role is None:
        return 0
    cwd = Path(str(payload.get("cwd") or "."))
    root = wm_config.repository_root(cwd)
    config = wm_config.load(root) if root is not None else wm_config.load(cwd)
    tool = str(payload.get("tool_name") or "")
    tool_input = payload.get("tool_input") or {}

    reason = None
    if tool == "Bash":
        reason = _check_command(str(tool_input.get("command") or ""), config)
    elif tool in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
        path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        reason = _check_write(role, path, cwd, root, config)

    if reason:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"{reason} (wm guard)",
            }
        }
        print(json.dumps(output))
    return 0


def _check_command(command: str, config: dict[str, Any]) -> str | None:
    for match in GIT_INVOCATION.finditer(command):
        subcommand = match.group(2)
        if subcommand not in READ_ONLY_GIT:
            return f"`git {subcommand}` changes the repository; version control is the lead's."
    for pattern, reason in BASH_RULES:
        if re.search(pattern, command):
            return reason
    for rule in config["denyCommands"]:
        try:
            if re.search(str(rule["pattern"]), command):
                return str(rule.get("reason") or "This project's configuration denies it.")
        except re.error:
            continue
    return None


def _check_write(
    role: str, path: str, cwd: Path, root: Path | None, config: dict[str, Any]
) -> str | None:
    if role == "read-only":
        return "This agent is read-only."
    target = Path(path).expanduser()
    if not target.is_absolute():
        target = cwd / target
    if ".claude" in target.parts:
        return "Claude Code's agents, skills, rules, hooks and settings are the lead's."
    relative = _relative(target, root)
    if role == "advisor":
        consults = str(config["paths"].get("consults") or "")
        if consults and relative is not None and relative.startswith(consults.rstrip("/") + "/"):
            return None
        return f"The advisor writes only its memo, inside {consults or 'the consults directory'}/."
    if relative is None:
        return None  # outside the repository, for example a scratch file
    return wm_config.lead_owned_reason(relative, config)


def _relative(target: Path, root: Path | None) -> str | None:
    if root is None:
        return None
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


if __name__ == "__main__":
    sys.exit(main())
