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

import json
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
USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def handle(payload: dict[str, Any]) -> None:
    tool_input = payload.get("tool_input") or {}
    response = payload.get("tool_response")
    if not isinstance(response, dict):
        return
    subagent = str(tool_input.get("subagent_type") or response.get("agentType") or "")
    name = wm_config.agent_name(subagent)
    agent_id = str(response.get("agentId") or "")
    resolved = str(response.get("resolvedModel") or "")
    status = str(response.get("status") or "")
    finished = status in ("", "completed")
    # The response's `usage` covers only the last message, so the run's cost comes from the
    # subagent's own transcript when it can be read (measured 2026-10-07).
    usage = transcript_usage(payload, agent_id) if finished else None
    scope = "run"
    if usage is None:
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        scope = "last message"
    family = wm_config.model_family(resolved) if resolved else ""
    cost = estimate_cost(family, usage) if finished else None
    order = WORK_ORDER.search(str(tool_input.get("prompt") or ""))
    wm_runtime.receipt(
        "agent_report",
        payload,
        "usage",
        subagent,
        subagent_id=agent_id,
        status=status,
        resolved_model=resolved,
        duration_ms=response.get("totalDurationMs"),
        usage=usage,
        usage_scope=scope,
        cost_usd_estimate=cost,
        work_order=order.group(0) if order else None,
    )
    if family in ("fable", "mythos"):
        _count_fable(str(payload.get("session_id") or "unknown"))
    if name is None:
        return
    if not finished:
        if name == "implementer":
            wm_runtime.emit(
                _context(
                    f"wm: {subagent} is still running (status: {status}), so its done-gate verdict "
                    "isn't ready. Wait for its report, then run the gates yourself before accepting."
                )
            )
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
        where = "" if scope == "run" else ", last message only"
        notes.append(f"wm: {subagent} cost about ${cost:.2f} at list prices ({resolved}{where}).")
    wm_runtime.emit(_context("\n".join(notes)))


def _context(text: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}


def transcript_usage(payload: dict[str, Any], agent_id: str) -> dict[str, int] | None:
    """The token counts of a subagent's whole run, summed from its transcript, which sits next to
    the parent's: <session>/subagents/agent-<id>.jsonl. Each message is counted once."""
    parent = payload.get("transcript_path")
    if not isinstance(parent, str) or not parent.endswith(".jsonl") or not agent_id:
        return None
    path = Path(parent[: -len(".jsonl")]) / "subagents" / f"agent-{agent_id}.jsonl"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    totals: dict[str, int] = {}
    seen: set[str] = set()
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
            continue
        key = str(message.get("id") or entry.get("uuid") or len(seen))
        if key in seen:
            continue
        seen.add(key)
        for field in USAGE_FIELDS:
            value = message["usage"].get(field)
            if isinstance(value, int):
                totals[field] = totals.get(field, 0) + value
    return totals or None


def verdict_note(agent_id: str) -> str:
    verdict = wm_runtime.read_json(wm_runtime.state_file("verdict", agent_id)) if agent_id else None
    if verdict is None:
        return (
            "wm done-gate: no verdict was recorded for this implementer, so the gate may not have "
            "run. Run the gates yourself before accepting the work."
        )
    outcome = verdict.get("outcome")
    checked = ", ".join(f"`{c}`" for c in verdict.get("checked") or [])
    changed = verdict.get("changed", 0)
    files = f"{changed} changed file{'' if changed == 1 else 's'}"
    lines = []
    if outcome == "PASSED":
        if not changed:
            lines.append("wm done-gate: PASSED. The implementer left no changes to check.")
        elif checked:
            lines.append(f"wm done-gate: PASSED. It checked {files} with {checked}.")
        else:
            lines.append(
                f"wm done-gate: PASSED on integrity only. No configured gate covers the {files}."
            )
        if verdict.get("no_gates_configured"):
            lines.append(
                "No gates are configured (.claude/working-model.json), so only integrity was "
                "checked. Verify the behavior yourself."
            )
    elif outcome == "FAILING":
        lines.append(
            "wm done-gate: FAILING. Don't accept or commit this as done. "
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
    history = verdict.get("history") or []
    if history:
        reasons = "; ".join(failure.splitlines()[0] for round_ in history for failure in round_)
        lines.append(f"It was sent back {len(history)} time(s) first, for: {reasons}")
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
