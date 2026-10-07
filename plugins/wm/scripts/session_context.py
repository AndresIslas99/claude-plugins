#!/usr/bin/env python3
"""SessionStart hook: puts the working model's essentials into every session (wm plugin).

An adopted project (one with .claude/working-model.json) gets a one-line pointer, because its
CLAUDE.md carries the full model. Any other project gets the defaults that apply everywhere,
and an offer to adopt the full workflow. A project that ships its own copy of the model gets
nothing. It also prunes state older than a week. It fails open.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_runtime

ADOPTED = (
    'This project follows the wm working model: the "Working model" section of CLAUDE.md and '
    ".claude/working-model.json. Carry it out with /wm:implement, /wm:design-session and "
    "/wm:ask-fable; /wm:doctor checks the setup."
)

DEFAULTS = """\
Working model (wm plugin), in effect in every project:
- You are the lead. You decide, write precise briefs, review, and commit when asked. Delegate what doesn't need your judgment:
  - codebase searches go to wm:scout (Haiku); the built-in Explore runs on your model, so a hook redirects it;
  - web research goes to wm:researcher (Sonnet), which reports dated sources;
  - write decided code yourself, and run the project's checks before you commit. Delegate a change to wm:implementer (Sonnet) only when it would flood your context or splits into parallel parts, with a brief that leaves no decision open and a real check to pass; review its diff;
  - an independent review of a risky diff (security, tenant isolation, concurrency, data integrity, a new public contract) goes to wm:reviewer (Opus);
  - for an extreme problem (security, data integrity, concurrency, irreversible designs), work at xhigh effort. Only after two failed attempts, consult wm:fable-advisor (Fable, 5x Sonnet's cost; the user approves every call).
- A subagent costs about 20K tokens to start. Never switch the session's model mid-task, because caches are per model. Continue a subagent with SendMessage instead of starting a new one.
- This project hasn't adopted the full workflow: work orders, path-scoped rules, and the gates the hooks enforce. When the user starts substantial work here, offer /wm:adopt."""


def handle(payload: dict[str, Any]) -> None:
    wm_runtime.prune_state()
    root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
    if root is not None and wm_config.has_own_working_model(root):
        return
    text = ADOPTED if root is not None and wm_config.adopted(root) else DEFAULTS
    wm_runtime.emit(
        {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
    )


if __name__ == "__main__":
    sys.exit(wm_runtime.run("session_context", handle, fail_closed=False))
