#!/usr/bin/env python3
"""SubagentStart hook: records where a wm:implementer started, so the done-gate can see exactly
what it changed.

The record is a snapshot of the working tree (see wm_git.snapshot), keyed by the subagent's
agent_id. It is what lets the gate attribute changes to the implementer, and catch edits that
no Edit or Write call showed, such as `sed -i` or a heredoc. Without a record, the gate falls
back to comparing with HEAD. It fails open.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_git
import wm_runtime


def handle(payload: dict[str, Any]) -> None:
    if wm_config.role_for(str(payload.get("agent_type") or "")) != "implementer":
        return
    root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
    agent = str(payload.get("agent_id") or "")
    if root is None or not agent:
        return
    tree = wm_git.snapshot(root)
    if tree is None:
        wm_runtime.receipt("baseline", payload, "error", "couldn't snapshot the working tree")
        return
    record = {"tree": tree, "head": wm_git.head_tree(root), "root": str(root), "t": time.time()}
    wm_runtime.write_json(wm_runtime.state_file("baseline", agent), record)
    wm_runtime.receipt("baseline", payload, "recorded", tree)


if __name__ == "__main__":
    sys.exit(wm_runtime.run("baseline", handle, fail_closed=False))
