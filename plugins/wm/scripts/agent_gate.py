#!/usr/bin/env python3
"""PreToolUse hook on the Agent tool: the model routing of the wm working model.

It is the one handler for Agent calls, so no two hooks race to rewrite the same call:
- wm agents don't start other agents; they report back to the lead.
- Searches go to `wm:scout` (Haiku). The built-in Explore runs on the session's model even with
  CLAUDE_CODE_SUBAGENT_MODEL set (measured 2026-10-06), so it is allowed only on a cheap model.
- Every call to Fable asks the user first, up to a per-session cap. A `permissions.ask` rule
  alone didn't stop a headless session in auto mode, where the classifier answered (measured
  2026-10-06); this hook's "ask" does, and headless runs deny it.
- A project (`models` in .claude/working-model.json) or the machine (WM_MODELS) can move a wm
  agent to another model, for example the scout when its Haiku model is retired. The rewrite
  goes through `updatedInput`, which Claude Code honors for Agent calls (measured 2026-10-07).

It fails closed: if it breaks, the launcher blocks the call.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_runtime

CHEAP_MODELS = ("haiku", "sonnet", "claude-haiku", "claude-sonnet")


def handle(payload: dict[str, Any]) -> None:
    root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
    if root is not None and wm_config.has_own_working_model(root):
        return
    config = wm_config.load(root)
    tool_input = payload.get("tool_input") or {}
    agent = str(tool_input.get("subagent_type") or "")
    model = str(tool_input.get("model") or "").lower()
    name = wm_config.agent_name(agent)

    if wm_config.role_for(str(payload.get("agent_type") or "")) is not None:
        return _deny(
            payload, "wm agents don't start other agents; report back to the lead instead."
        )
    if agent == "Explore" and not model.startswith(CHEAP_MODELS):
        return _deny(
            payload,
            "Searches go to the wm:scout agent (Haiku); the built-in Explore runs on the "
            'session\'s model. Retry with subagent_type "wm:scout".',
        )
    if name == "fable-advisor" or "fable" in model:
        return _fable(payload, config, tool_input, name)
    updated = dict(tool_input)
    changes: list[str] = []
    override = wm_config.model_override(name, config) if name else None
    if override and not model:
        updated["model"] = override
        changes.append(f"routes {agent} to {override}")
    # A background launch returns before the implementer runs, so PostToolUse would reach the lead
    # with no verdict (measured 2026-10-07). Parallel orders in their own worktrees stay background.
    foreground = tool_input.get("run_in_background") is False
    if name == "implementer" and tool_input.get("isolation") != "worktree" and not foreground:
        updated["run_in_background"] = False
        changes.append("runs the implementer in the foreground, so the lead gets its gate verdict")
    if changes:
        reason = "wm " + "; ".join(changes)
        wm_runtime.receipt("agent_gate", payload, "rewrite", reason)
        wm_runtime.pre_tool("allow", reason, updated)


def _fable(
    payload: dict[str, Any], config: dict[str, Any], tool_input: dict[str, Any], name: str | None
) -> None:
    session = str(payload.get("session_id") or "unknown")
    used = fable_consults(session)
    cap = config["fableConsultsPerSession"]
    if used >= cap:
        return _deny(
            payload,
            f"This session has already used its {cap} Fable consults (fable.maxConsultsPerSession "
            "in .claude/working-model.json). Keep working at xhigh effort, or start a new session.",
        )
    subject = str(tool_input.get("description") or "a consult")
    route = "" if name == "fable-advisor" else " outside wm:fable-advisor"
    reason = (
        f"Consult Fable{route} (list price 2.5x Opus, 5x Sonnet) about: {subject}. "
        f"This session has used {used} of {cap} consults. Approve? (wm)"
    )
    wm_runtime.receipt("agent_gate", payload, "ask", reason)
    wm_runtime.pre_tool("ask", reason)


def fable_consults(session: str) -> int:
    data = wm_runtime.read_json(wm_runtime.state_file("fable", session)) or {}
    count = data.get("count")
    return count if isinstance(count, int) else 0


def _deny(payload: dict[str, Any], reason: str) -> None:
    wm_runtime.receipt("agent_gate", payload, "deny", reason)
    wm_runtime.pre_tool("deny", reason)


if __name__ == "__main__":
    sys.exit(wm_runtime.run("agent_gate", handle, fail_closed=True))
