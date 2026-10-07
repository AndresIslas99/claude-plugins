"""A project's working-model configuration, `.claude/working-model.json`, with its defaults.

Shared by the wm plugin's hooks. They run on the system `python3`, which may be 3.9, so this
code avoids newer syntax. Paths are relative to the repository root, with `/` separators.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from wm_git import repository_root

__all__ = ["repository_root"]

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

# Where tests live, to notice deleted test files and removed assertions.
DEFAULT_TEST_GLOBS = (
    "**/test_*.py",
    "**/*_test.py",
    "**/tests/**",
    "**/__tests__/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/*_test.go",
)

# Files that define checks, where `|| true` or `continue-on-error` would weaken a gate.
DEFAULT_CHECK_GLOBS = (
    ".github/workflows/**",
    "lefthook.yml",
    ".pre-commit-config.yaml",
    "justfile",
    "Makefile",
    "package.json",
    "pyproject.toml",
    "tox.ini",
    "setup.cfg",
)

# The model each wm role is meant to run on; the agent files set the same aliases.
INTENDED_MODELS = {
    "implementer": "sonnet",
    "reviewer": "opus",
    "fable-advisor": "fable",
    "scout": "haiku",
    "researcher": "sonnet",
}

# Agent types the hooks act on, with the role each one plays. Plugin agents are namespaced
# ("wm:implementer"); the bare name is accepted too.
ROLES = {
    "implementer": "implementer",
    "fable-advisor": "advisor",
    "reviewer": "read-only",
    "scout": "read-only",
    "researcher": "read-only",
}

DEFAULT_FABLE_CONSULTS_PER_SESSION = 3
DEFAULT_GATE_BUDGET_SECONDS = 1500  # below the hook's registered timeout of 1800


def agent_name(agent_type: str) -> str | None:
    """The wm agent's bare name ("implementer"), or None for any other agent."""
    namespace, _, name = agent_type.rpartition(":")
    if namespace not in ("", "wm") or name not in ROLES:
        return None
    return name


def role_for(agent_type: str) -> str | None:
    """The role of a wm agent, or None for any other agent and for the main session."""
    name = agent_name(agent_type)
    return ROLES[name] if name else None


def adopted(root: Path) -> bool:
    return (root / CONFIG_FILE).is_file()


def has_own_working_model(root: Path) -> bool:
    """The project ships its own copy of the working model's hooks, as projects set up before
    the plugin do. The plugin then stays out of its way."""
    return (root / ".claude" / "hooks" / "agent_gate.py").is_file()


def load(root: Path | None) -> dict[str, Any]:
    """The project's configuration with defaults filled in. A missing or invalid file gives the
    defaults: no gates, no tests, and only the default lead-owned paths."""
    raw: Any = {}
    if root is not None:
        try:
            raw = json.loads((root / CONFIG_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    paths = dict(DEFAULT_PATHS)
    for key, value in (raw.get("paths") or {}).items():
        if isinstance(value, str) or value is None:
            paths[key] = value
    fable = raw.get("fable") if isinstance(raw.get("fable"), dict) else {}
    budget = raw.get("gateBudgetSeconds")
    return {
        "gates": _entries(raw.get("gates")),
        "tests": _entries(raw.get("tests")),
        "leadOwned": _strings(raw.get("leadOwned")),
        "denyCommands": [
            d for d in raw.get("denyCommands") or [] if isinstance(d, dict) and d.get("pattern")
        ],
        "paths": paths,
        "protectedBranches": _strings(raw.get("protectedBranches")) or ["main"],
        "testGlobs": _strings(raw.get("testGlobs")) or list(DEFAULT_TEST_GLOBS),
        "checkGlobs": _strings(raw.get("checkGlobs")) or list(DEFAULT_CHECK_GLOBS),
        "models": _models(raw.get("models")),
        "fableConsultsPerSession": _positive_int(
            fable.get("maxConsultsPerSession"), DEFAULT_FABLE_CONSULTS_PER_SESSION
        ),
        "gateBudgetSeconds": _positive_int(budget, DEFAULT_GATE_BUDGET_SECONDS),
        "loaded": bool(raw),
    }


def model_override(name: str, config: dict[str, Any]) -> str | None:
    """A model chosen for a wm agent by the project (`models`) or the machine (WM_MODELS,
    for example "scout=sonnet"), or None to keep the agent's own."""
    environment: dict[str, str] = {}
    for item in os.environ.get("WM_MODELS", "").split(","):
        key, _, value = item.partition("=")
        if key.strip() and value.strip():
            environment[key.strip()] = value.strip()
    return config["models"].get(name) or environment.get(name)


def intended_model(name: str, config: dict[str, Any]) -> str:
    return model_override(name, config) or INTENDED_MODELS[name]


def model_family(model: str) -> str:
    lowered = model.lower()
    for family in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if family in lowered:
            return family
    return lowered


def _entries(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [e for e in value if isinstance(e, dict) and isinstance(e.get("run"), str)]


def _strings(value: object) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _models(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if k in INTENDED_MODELS and isinstance(v, str)}


def _positive_int(value: object, default: int) -> int:
    return (
        value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default
    )


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
        if covers(entry, relative):
            return f"{entry} is lead-owned (.claude/working-model.json)."
    return None


def covers(entry: str, relative: str) -> bool:
    if entry.endswith("/"):
        return relative.startswith(entry)
    return relative == entry or matches(relative, entry)


def matches(path: str, pattern: str) -> bool:
    """Glob matching with gitignore-style `**`: `*` stays within a directory, `**` crosses them,
    and a pattern ending in `/` matches everything below that directory."""
    if pattern.endswith("/"):
        pattern += "**"
    return _compile(pattern).match(path) is not None


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


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
