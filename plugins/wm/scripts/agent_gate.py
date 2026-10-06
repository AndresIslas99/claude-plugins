#!/usr/bin/env python3
"""PreToolUse hook on the Agent tool: the model routing of the wm working model.

- Searches go to `wm:scout` (Haiku). The built-in Explore agent runs on the session's model,
  even when CLAUDE_CODE_SUBAGENT_MODEL is set (measured 2026-10-06), so it is allowed only
  with an explicitly cheaper model.
- Every call to Fable asks the user first: launching `wm:fable-advisor`, or any agent with a
  Fable model. In a headless session in auto mode, a `permissions.ask` rule alone didn't stop
  the call (the classifier answered), while this hook's "ask" did (measured 2026-10-06).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config

CHEAP_MODELS = ("haiku", "sonnet", "claude-haiku", "claude-sonnet")


def main() -> int:
    payload = json.load(sys.stdin)
    root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
    if root is not None and wm_config.has_own_working_model(root):
        return 0
    tool_input = payload.get("tool_input") or {}
    agent = str(tool_input.get("subagent_type") or "")
    model = str(tool_input.get("model") or "").lower()

    if agent == "Explore" and not model.startswith(CHEAP_MODELS):
        return _decide(
            "deny",
            "Searches go to the wm:scout agent (Haiku); the built-in Explore runs on the "
            'session\'s model. Retry with subagent_type "wm:scout".',
        )
    if agent.rpartition(":")[2] == "fable-advisor":
        description = str(tool_input.get("description") or "a consult")
        return _decide(
            "ask", f"Consult Fable (5x Sonnet's cost) about: {description}. Approve? (wm)"
        )
    if "fable" in model:
        return _decide(
            "ask",
            "Fable costs 5x Sonnet and is reserved for the wm:fable-advisor agent. "
            "Allow this Fable call anyway? (wm)",
        )
    return 0


def _decide(decision: str, reason: str) -> int:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
