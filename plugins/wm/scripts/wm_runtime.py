"""Shared plumbing for the wm hooks: input, output, state, receipts and the failure policy.

The hooks run on the system `python3`, which may be 3.9, so this code avoids newer syntax.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

RECEIPTS_MAX_BYTES = 2_000_000
STATE_MAX_AGE_SECONDS = 7 * 24 * 3600


def read_payload() -> dict[str, Any]:
    """The hook's JSON input, read as UTF-8 whatever the platform's encoding is."""
    raw = sys.stdin.buffer.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw.decode("utf-8", errors="replace"))
    return payload if isinstance(payload, dict) else {}


def emit(output: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(output) + "\n")


def pre_tool(decision: str, reason: str, updated_input: dict[str, Any] | None = None) -> None:
    specific: dict[str, Any] = {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }
    if updated_input is not None:
        specific["updatedInput"] = updated_input
    emit({"hookSpecificOutput": specific})


def state_dir() -> Path:
    """Where the hooks keep their state: the plugin's data directory, or a temporary one."""
    base = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(
        tempfile.gettempdir(), "wm-plugin-data"
    )
    path = Path(base) / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_file(kind: str, key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120] or "unknown"
    return state_dir() / f"{kind}-{safe}"


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    temporary.replace(path)


def receipt(
    hook: str, payload: dict[str, Any], decision: str, reason: str = "", **extra: Any
) -> None:
    """Append one decision to receipts.jsonl. A receipt never breaks a hook."""
    try:
        entry = {
            "t": round(time.time(), 3),
            "hook": hook,
            "event": payload.get("hook_event_name"),
            "mode": payload.get("permission_mode"),
            "session": payload.get("session_id"),
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "tool": payload.get("tool_name"),
            "decision": decision,
            "reason": reason[:500],
        }
        entry.update(extra)
        path = state_dir() / "receipts.jsonl"
        if path.exists() and path.stat().st_size > RECEIPTS_MAX_BYTES:
            path.replace(path.with_name("receipts.1.jsonl"))
        with path.open("a", encoding="utf-8") as receipts:
            receipts.write(json.dumps(entry, default=str) + "\n")
    except Exception:  # noqa: BLE001, S110 - a broken receipt must not change a decision
        pass


def prune_state() -> None:
    """Delete per-agent state older than a week."""
    try:
        cutoff = time.time() - STATE_MAX_AGE_SECONDS
        for path in state_dir().iterdir():
            if path.name.startswith("receipts"):
                continue
            if path.stat().st_mtime < cutoff:
                path.unlink()
    except OSError:
        pass


def run(hook: str, handler: Callable[[dict[str, Any]], None], *, fail_closed: bool) -> int:
    """Run `handler` on the payload. An unexpected error blocks the action (`fail_closed`) or lets
    it through, and either way leaves a receipt."""
    payload: dict[str, Any] = {}
    try:
        payload = read_payload()
        handler(payload)
        return 0
    except Exception:  # noqa: BLE001 - the failure policy has to see every error
        detail = traceback.format_exc(limit=2).strip().splitlines()[-1]
        receipt(hook, payload, "error", detail)
        if fail_closed:
            sys.stderr.write(
                f"wm: the {hook} hook failed ({detail}). The action was blocked to stay on the "
                "safe side; run /wm:doctor.\n"
            )
            return 2
        return 0
