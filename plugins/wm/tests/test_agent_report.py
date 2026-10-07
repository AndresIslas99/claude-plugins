#!/usr/bin/env python3
"""Scenario tests for agent_report.py, the PostToolUse hook that tells the lead what the checks saw.

python3 plugins/wm/tests/test_agent_report.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from support import Suite, make_repository, run_hook, state


def payload(
    root: Path, subagent: str, agent_id: str, model: str, prompt: str = "go"
) -> dict[str, Any]:
    """A PostToolUse(Agent) payload with the response fields seen from Claude Code 2.1.292."""
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "cwd": str(root),
        "session_id": "s1",
        "tool_input": {"subagent_type": subagent, "prompt": prompt, "description": "x"},
        "tool_response": {
            "agentId": agent_id,
            "agentType": subagent,
            "content": [],
            "resolvedModel": model,
            "status": "completed",
            "totalDurationMs": 9000,
            "totalTokens": 50000,
            "totalToolUseCount": 4,
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 2000,
                "cache_read_input_tokens": 40000,
                "cache_creation_input_tokens": 7000,
            },
        },
    }


def main() -> int:
    suite = Suite("agent-report")
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        root = make_repository(base / "repo", {"src/app.py": "VALUE = 1\n"}, {"models": {}})
        data = base / "data"
        (data / "state").mkdir(parents=True)
        verdict = {"outcome": "PASSED", "checked": ["just lint"], "changed": 2, "warnings": []}
        (data / "state" / "verdict-a1").write_text(json.dumps(verdict))

        transcript = base / "session-1.jsonl"
        transcript.write_text("")
        subagents = base / "session-1" / "subagents"
        subagents.mkdir(parents=True)
        message = {
            "role": "assistant",
            "id": "m1",
            "usage": {"input_tokens": 10, "output_tokens": 100_000},
        }
        lines = [
            {"message": message},
            {"message": message},  # the same message logged twice is counted once
            {"message": {"role": "assistant", "id": "m2", "usage": {"output_tokens": 100_000}}},
        ]
        (subagents / "agent-a1.jsonl").write_text("\n".join(json.dumps(line) for line in lines))

        prompt = "Carry out docs/work-orders/0007-add-rates.md. Follow your protocol."
        with_transcript = payload(root, "wm:implementer", "a1", "claude-sonnet-5-5", prompt)
        with_transcript["transcript_path"] = str(transcript)
        passed = run_hook("agent_report.py", with_transcript, data=data, policy="open")
        suite.contains("the cost comes from the whole run", passed.context, "cost about $2.00")
        suite.contains("the lead gets the PASSED verdict", passed.context, "wm done-gate: PASSED")
        suite.contains("and the cost", passed.context, "at list prices")
        suite.contains("it counts the files", passed.context, "checked 2 changed files with")
        (data / "state" / "verdict-a3").write_text(json.dumps(dict(verdict, changed=1)))
        one = run_hook(
            "agent_report.py",
            payload(root, "wm:implementer", "a3", "claude-sonnet-5-5"),
            data=data,
            policy="open",
        )
        suite.contains("one file is singular", one.context, "checked 1 changed file with")

        none = run_hook(
            "agent_report.py",
            payload(root, "wm:implementer", "a2", "claude-sonnet-5-5"),
            data=data,
            policy="open",
        )
        suite.contains(
            "no verdict means the gate may not have run", none.context, "no verdict was recorded"
        )

        failing = {
            "outcome": "FAILING",
            "failures": ["`just test` failed"],
            "warnings": ["Deleted test files: x"],
        }
        (data / "state" / "verdict-a3").write_text(json.dumps(failing))
        failed = run_hook(
            "agent_report.py",
            payload(root, "wm:implementer", "a3", "claude-sonnet-5-5"),
            data=data,
            policy="open",
        )
        suite.contains(
            "a FAILING verdict says don't accept", failed.context, "Don't accept or commit"
        )
        suite.contains("warnings are passed on", failed.context, "Deleted test files")

        drifted = run_hook(
            "agent_report.py",
            payload(root, "wm:scout", "a4", "claude-opus-5-5"),
            data=data,
            policy="open",
        )
        suite.contains(
            "a scout that ran on Opus is flagged", drifted.context, "meant to run on haiku"
        )

        on_plan = run_hook(
            "agent_report.py",
            payload(root, "wm:scout", "a5", "claude-haiku-4-5-20251001"),
            data=data,
            policy="open",
        )
        suite.check(
            "a scout on Haiku isn't flagged", "meant to run" not in on_plan.context, on_plan.context
        )

        other = run_hook(
            "agent_report.py",
            payload(root, "general-purpose", "a6", "claude-sonnet-5-5"),
            data=data,
            policy="open",
        )
        suite.equal("other agents get no note", other.decision, "allow")

        run_hook(
            "agent_report.py",
            payload(root, "wm:fable-advisor", "a7", "claude-fable-5-1"),
            data=data,
            policy="open",
        )
        suite.equal(
            "a Fable consult is counted for the session",
            (state(data, "fable", "s1") or {}).get("count"),
            1,
        )

        launched = payload(root, "wm:implementer", "a8", "claude-sonnet-5-5")
        launched["tool_response"]["status"] = "async_launched"
        running = run_hook("agent_report.py", launched, data=data, policy="open")
        suite.contains(
            "a background launch isn't reported as done", running.context, "still running"
        )

        quiet = {
            "outcome": "PASSED",
            "checked": [],
            "changed": 0,
            "warnings": [],
            "history": [["`just lint` failed:\nx"]],
        }
        (data / "state" / "verdict-a9").write_text(json.dumps(quiet))
        retried = run_hook(
            "agent_report.py",
            payload(root, "wm:implementer", "a9", "claude-sonnet-5-5"),
            data=data,
            policy="open",
        )
        suite.contains(
            "no changes left is said plainly", retried.context, "left no changes to check"
        )
        suite.contains(
            "and the send-backs are reported",
            retried.context,
            "sent back 1 time(s) first, for: `just lint` failed:",
        )

        receipts = [
            json.loads(line)
            for line in (data / "state" / "receipts.jsonl").read_text().splitlines()
        ]
        usage = [
            r for r in receipts if r.get("decision") == "usage" and r.get("subagent_id") == "a1"
        ]
        suite.equal(
            "usage is recorded with its work order",
            usage[0].get("work_order") if usage else None,
            "docs/work-orders/0007-add-rates.md",
        )
        suite.check(
            "and a cost estimate",
            bool(usage) and isinstance(usage[0].get("cost_usd_estimate"), float),
        )
    return suite.finish()


if __name__ == "__main__":
    sys.exit(main())
