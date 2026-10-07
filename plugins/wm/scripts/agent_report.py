#!/usr/bin/env python3
"""PostToolUse hook on the Agent tool: tells the lead what the wm checks saw.

After every Agent call it:
- for wm:implementer, hands the lead the done-gate's verdict for that run (done_gate.py writes
  it). A report is a claim; the verdict is evidence. No verdict means the gate didn't run, and
  the lead must check the gates itself;
- compares the model the subagent ran on (`resolvedModel`) with the model the role is meant to
  use. Silent model inheritance is the costliest routing failure users report;
- records tokens, duration and a list-price cost estimate per agent and work order in the
  receipts, which is the telemetry that per-order cost comparisons are built from;
- counts Fable consults per session, for agent_gate.py's cap.

It fails open: it only informs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_runtime

# List prices in dollars per million tokens: input, output, cache read, cache write (5 minutes).
PRICES = {
    "fable": (10.0, 50.0, 0.25, 12.5),
    "mythos": (10.0, 50.0, 0.25, 12.5),
    "opus": (4.0, 20.0, 0.20, 5.0),
    "sonnet": (2.0, 10.0, 0.20, 2.5),
    "haiku": (1.0, 5.0, 0.10, 1.25),
}
WORK_ORDER = re.compile(r"[\w./-]*work-orders/[\w.-]+\.md")


def handle(payload: dict[str, Any]) -> None:
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response")
    if not isinstance(response, dict):
        return
    subagent = str(tool_input.get("subagent_type") or response.get("agentType") or "")
    name = wm_config.agent_name(subagent)
    agent_id = str(response.get("agentId") or "")
    resolved = str(response.get("resolvedModel") or "")
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    family = wm_config.model_family(resolved) if resolved else ""
    cost = estimate_cost(family, usage)
    order = WORK_ORDER.search(str(tool_input.get("prompt") or ""))
    wm_runtime.receipt(
        "agent_report",
        payload,
        "usage",
        subagent,
        subagent_id=agent_id,
        resolved_model=resolved,
        total_tokens=response.get("totalTokens"),
        duration_ms=response.get("totalDurationMs"),
        usage=usage,
        cost_usd_estimate=cost,
        work_order=order.group(0) if order else None,
    )
    if family in ("fable", "mythos"):
        _count_fable(str(payload.get("session_id") or "unknown"))
    if name is None:
        return

    notes: list[str] = []
    root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
    config = wm_config.load(root)
    intended = wm_config.intended_model(name, config)
    if resolved and wm_config.model_family(intended) != family:
        notes.append(
            f"wm: {subagent} ran on {resolved}, but its role is meant to run on {intended}. "
            "Check the model routing (/wm:doctor)."
        )
    if name == "implementer":
        notes.append(verdict_note(agent_id))
    if cost is not None:
        notes.append(f"wm: {subagent} cost about ${cost:.2f} at list prices ({resolved}).")
    wm_runtime.emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n".join(notes),
            }
        }
    )


def verdict_note(agent_id: str) -> str:
    verdict = wm_runtime.read_json(wm_runtime.state_file("verdict", agent_id)) if agent_id else None
    if verdict is None:
        return (
            "wm done-gate: no verdict was recorded for this implementer, so the gate may not have "
            "run. Run the gates yourself before accepting the work."
        )
    outcome = verdict.get("outcome")
    checked = ", ".join(f"`{c}`" for c in verdict.get("checked") or []) or "no gate commands"
    lines = []
    if outcome == "PASSED":
        lines.append(
            f"wm done-gate: PASSED. It checked {verdict.get('changed', 0)} changed files with "
            f"{checked}."
        )
        if verdict.get("no_gates_configured"):
            lines.append(
                "No gates are configured (.claude/working-model.json), so only integrity was "
                "checked. Verify the behavior yourself."
            )
    elif outcome == "FAILING":
        lines.append(
            "wm done-gate: FAILING after its retries. Don't accept or commit this as done. "
            "Failures:\n" + "\n".join(verdict.get("failures") or [])
        )
    elif outcome in ("REPORTED_BLOCKED", "REPORTED_PARTIAL"):
        lines.append(
            f"wm done-gate: the implementer reported {verdict.get('status')}; integrity checks passed."
        )
    elif outcome == "SENT_BACK":
        lines.append(
            "wm done-gate: the implementer stopped while it had been sent back. Failures:\n"
            + "\n".join(verdict.get("failures") or [])
        )
    else:
        lines.append(f"wm done-gate: {outcome}.")
    warnings = verdict.get("warnings") or []
    if warnings:
        lines.append("Review these in the diff: " + "; ".join(warnings))
    return "\n".join(lines)


def estimate_cost(family: str, usage: dict[str, Any]) -> float | None:
    prices = PRICES.get(family)
    if prices is None or not usage:
        return None
    counts = [
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        usage.get("cache_read_input_tokens"),
        usage.get("cache_creation_input_tokens"),
    ]
    if not any(isinstance(c, int) for c in counts):
        return None
    total = sum((c if isinstance(c, int) else 0) * p for c, p in zip(counts, prices))
    return round(total / 1_000_000, 4)


def _count_fable(session: str) -> None:
    path = wm_runtime.state_file("fable", session)
    count = int((wm_runtime.read_json(path) or {}).get("count") or 0) + 1
    wm_runtime.write_json(path, {"count": count})


if __name__ == "__main__":
    sys.exit(wm_runtime.run("agent_report", handle, fail_closed=False))
