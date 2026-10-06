"""A project's working-model configuration, `.claude/working-model.json`, with its defaults.

Shared by the wm plugin's hooks. They run on the system `python3`, which may be 3.9, so this
code avoids newer syntax. Paths are relative to the repository root, with `/` separators.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

CONFIG_FILE = ".claude/working-model.json"

DEFAULT_PATHS = {
    "workOrders": "docs/work-orders",
    "consults": "docs/consults",
    "decisions": "docs/adr",
}

# Lead-owned in every project: the instructions and the workflow's own configuration.
DEFAULT_LEAD_OWNED = ("CLAUDE.md", ".claude/")

# Lockfiles, wherever they are: dependencies are the lead's decision.
LOCKFILES = frozenset(
    {
        "Cargo.lock",
        "Gemfile.lock",
        "Pipfile.lock",
        "bun.lock",
        "bun.lockb",
        "composer.lock",
        "go.sum",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "yarn.lock",
    }
)

# Agent types the hooks act on, with the role each one plays. Plugin agents are namespaced
# ("wm:implementer"); the bare name is accepted too.
ROLES = {
    "implementer": "implementer",
    "fable-advisor": "advisor",
    "reviewer": "read-only",
    "scout": "read-only",
    "researcher": "read-only",
}


def role_for(agent_type: str) -> str | None:
    """The role of a wm agent, or None for any other agent and for the main session."""
    namespace, _, name = agent_type.rpartition(":")
    if namespace not in ("", "wm"):
        return None
    return ROLES.get(name)


def repository_root(cwd: Path) -> Path | None:
    """The root of the git repository (or worktree) that holds `cwd`."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    output = completed.stdout.strip()
    return Path(output) if completed.returncode == 0 and output else None


def adopted(root: Path) -> bool:
    return (root / CONFIG_FILE).is_file()


def has_own_working_model(root: Path) -> bool:
    """The project ships its own copy of the working model's hooks, as projects set up before
    the plugin do. The plugin then stays out of its way."""
    return (root / ".claude" / "hooks" / "agent_gate.py").is_file()


def load(root: Path) -> dict[str, Any]:
    """The project's configuration with defaults filled in. A missing or invalid file gives the
    defaults: no gates, no tests, and only the default lead-owned paths."""
    try:
        raw = json.loads((root / CONFIG_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    paths = dict(DEFAULT_PATHS)
    paths.update(
        {k: v for k, v in (raw.get("paths") or {}).items() if isinstance(v, str) or v is None}
    )
    return {
        "gates": _entries(raw.get("gates")),
        "tests": _entries(raw.get("tests")),
        "leadOwned": [p for p in raw.get("leadOwned") or [] if isinstance(p, str)],
        "denyCommands": [
            d for d in raw.get("denyCommands") or [] if isinstance(d, dict) and d.get("pattern")
        ],
        "paths": paths,
        "protectedBranches": raw.get("protectedBranches") or ["main"],
    }


def _entries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [e for e in value if isinstance(e, dict) and isinstance(e.get("run"), str)]


def lead_owned_reason(relative: str, config: dict[str, Any]) -> str | None:
    """Why only the lead may write `relative`, or None if anyone may."""
    name = relative.rsplit("/", 1)[-1]
    if name in LOCKFILES:
        return f"{name} is a lockfile, and dependencies are the lead's decision."
    if name.startswith(".env") and name != ".env.example":
        return "Environment files hold secrets."
    owned = list(DEFAULT_LEAD_OWNED)
    owned += [path.rstrip("/") + "/" for path in config["paths"].values() if path]
    owned += config["leadOwned"]
    for entry in owned:
        if _covers(entry, relative):
            return f"{entry} is lead-owned (.claude/working-model.json)."
    return None


def _covers(entry: str, relative: str) -> bool:
    if entry.endswith("/"):
        return relative.startswith(entry)
    return relative == entry or matches(relative, entry)


def matches(path: str, pattern: str) -> bool:
    """Glob matching with gitignore-style `**`: `*` stays within a directory, `**` crosses them,
    and a pattern ending in `/` matches everything below that directory."""
    if pattern.endswith("/"):
        pattern += "**"
    return _compile(pattern).match(path) is not None


_CACHE: dict[str, re.Pattern[str]] = {}


def _compile(pattern: str) -> re.Pattern[str]:
    if pattern not in _CACHE:
        parts: list[str] = []
        i = 0
        while i < len(pattern):
            if pattern.startswith("**/", i):
                parts.append("(?:.*/)?")
                i += 3
            elif pattern.startswith("**", i):
                parts.append(".*")
                i += 2
            elif pattern[i] == "*":
                parts.append("[^/]*")
                i += 1
            elif pattern[i] == "?":
                parts.append("[^/]")
                i += 1
            else:
                parts.append(re.escape(pattern[i]))
                i += 1
        _CACHE[pattern] = re.compile("".join(parts) + r"\Z")
    return _CACHE[pattern]
