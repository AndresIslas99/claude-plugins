#!/usr/bin/env python3
"""Checks of the plugin's own files: hooks.json wiring, agent pinning and context budgets.

    python3 plugins/wm/tests/test_manifest.py

These catch regressions that silently disable enforcement. An unquoted ${CLAUDE_PLUGIN_ROOT}
breaks on paths with spaces (claude-code #78490). A gate wired as "open" would let failures
through. And an unpinned agent inherits a more expensive model.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from support import PLUGIN, Suite

sys.path.insert(0, str(PLUGIN / "scripts"))
import session_context

LAUNCH = re.compile(r'^bash "\$\{CLAUDE_PLUGIN_ROOT\}/scripts/launch\.sh" (closed|open) (\w+\.py)$')
CLOSED = {"agent_gate.py", "done_gate.py"}
PINNED = {
    "implementer": "sonnet",
    "reviewer": "opus",
    "fable-advisor": "fable",
    "scout": "haiku",
    "researcher": "sonnet",
}


def frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text().split("---\n", 2)[1].splitlines()
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in lines) if v}


def main() -> int:
    suite = Suite("manifest")
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())["hooks"]
    seen = set()
    for event, groups in hooks.items():
        for group in groups:
            for hook in group["hooks"]:
                match = LAUNCH.match(hook["command"])
                suite.check(
                    f"{event} runs through the quoted launcher", match is not None, hook["command"]
                )
                if not match:
                    continue
                policy, script = match.groups()
                seen.add(script)
                suite.check(f"{script} exists", (PLUGIN / "scripts" / script).is_file())
                expected = "closed" if script in CLOSED else "open"
                suite.equal(f"{script} fails {expected}", policy, expected)
                suite.check(f"{event} {script} has a timeout", isinstance(hook.get("timeout"), int))
    suite.equal(
        "every hook script is wired",
        seen,
        {
            "session_context.py",
            "baseline.py",
            "agent_gate.py",
            "subagent_guard.py",
            "done_gate.py",
            "commit_gate.py",
            "agent_report.py",
        },
    )
    matchers = {g.get("matcher") for groups in hooks.values() for g in groups}
    suite.check(
        "the agent_type matchers are anchored", "^wm:implementer$" in matchers, str(matchers)
    )

    for name, model in PINNED.items():
        meta = frontmatter(PLUGIN / "agents" / f"{name}.md")
        suite.equal(f"{name} is pinned to {model}", meta.get("model"), model)
        suite.check(f"{name} has maxTurns", meta.get("maxTurns", "").isdigit())
        tools = meta.get("tools", "")
        suite.check(f"{name} can't start agents", "Agent" not in tools.split(", "), tools)
    suite.equal(
        "the implementer runs at medium effort",
        frontmatter(PLUGIN / "agents" / "implementer.md").get("effort"),
        "medium",
    )

    for skill in sorted((PLUGIN / "skills").glob("*/SKILL.md")):
        description = frontmatter(skill).get("description", "")
        suite.check(
            f"{skill.parent.name}'s description fits the 1,536-character listing cap",
            0 < len(description) <= 1536,
            str(len(description)),
        )
    suite.equal(
        "/wm:adopt is invoked by the user only",
        frontmatter(PLUGIN / "skills" / "adopt" / "SKILL.md").get("disable-model-invocation"),
        "true",
    )
    for label, text in (
        ("defaults", session_context.DEFAULTS),
        ("adopted", session_context.ADOPTED),
    ):
        suite.check(
            f"the SessionStart {label} text stays under 2,000 characters",
            len(text) < 2000,
            str(len(text)),
        )
    return suite.finish()


if __name__ == "__main__":
    sys.exit(main())
