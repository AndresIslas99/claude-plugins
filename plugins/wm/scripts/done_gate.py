#!/usr/bin/env python3
"""The implementer's done-gate: a work order isn't done while its checks fail.

Two entry points run the same checks (measured 2026-10-07 on Claude Code 2.1.292):
- In auto mode a subagent ends by calling SubagentHandback. This hook runs as PreToolUse on that
  tool and denies the handback, because Claude Code discards a SubagentStop block that comes
  after a handback.
- In the other permission modes the subagent ends with plain text. This hook runs as SubagentStop
  and blocks.

The checks look at the implementer's own changes: the diff between the snapshot baseline.py took
when it started and the working tree now, or HEAD when there's no snapshot.
- Integrity is checked whatever the report says, and a failure always sends the implementer
  back: lead-owned files changed by any tool, new gate suppressions, check configuration
  weakened (`|| true`, `continue-on-error`), or HEAD moved, by a commit, reset or checkout that
  the guard couldn't see, such as one a script made.
- Quality is checked when the report claims DONE or has no status: the report's format, then the
  project's gates for the changed files (`gates`, then `tests`, in .claude/working-model.json),
  within a time budget.
- Warnings never block, and go to the lead: deleted test files, and test files that lost more
  assertions than they gained.

The implementer is sent back at most MAX_BLOCKS times; after that the report passes with a
FAILING verdict. It passes the same way as soon as the implementer reports BLOCKED or PARTIAL on
the failures it was last sent back for, because it can't undo them within its limits. Every
outcome is written as a verdict, which agent_report.py hands to the lead.
If the checks themselves break, that counts as a failure, so the gate still converges.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config
import wm_git
import wm_runtime

MAX_BLOCKS = 2
TAIL_LINES = 30
DEFAULT_TIMEOUT_SECONDS = 600
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

STATUS = re.compile(r"^\W*STATUS:\W*(DONE|BLOCKED|PARTIAL)\b", re.MULTILINE | re.IGNORECASE)

# What silences a gate instead of satisfying it, by file type.
PY = (".py", ".pyi")
JS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".svelte")
SUPPRESSIONS = (
    (PY, re.compile(r"#\s*type:\s*ignore"), "`# type: ignore`"),
    (PY, re.compile(r"#\s*(ruff:\s*)?noqa\b", re.IGNORECASE), "`# noqa`"),
    (PY, re.compile(r"#\s*(pyrefly|pyright|mypy):\s*ignore"), "a type-checker ignore"),
    (PY, re.compile(r"#\s*pragma:\s*no\s*cover"), "`# pragma: no cover`"),
    (PY, re.compile(r"\bpytest\.(skip|xfail|importorskip)\s*\("), "a pytest skip or xfail"),
    (
        PY,
        re.compile(r"@pytest\.mark\.(skip|skipif|xfail|filterwarnings)\b"),
        "a pytest skip, xfail or warning filter",
    ),
    (PY, re.compile(r"\bwarnings\.(filterwarnings|simplefilter)\s*\("), "a warning filter"),
    (JS, re.compile(r"@ts-(ignore|expect-error|nocheck)\b"), "a TypeScript suppression"),
    (JS, re.compile(r"\beslint-disable"), "an eslint-disable"),
    (JS, re.compile(r"\bbiome-ignore\b"), "a biome-ignore"),
    (
        JS,
        re.compile(r"\b(it|test|describe)\.(skip|todo)\s*\(|\bx(it|describe|test)\s*\("),
        "a skipped test",
    ),
    ((".sh", ".bash"), re.compile(r"#\s*shellcheck\s+disable="), "`# shellcheck disable`"),
    ((".go",), re.compile(r"//\s*nolint"), "`//nolint`"),
    ((".rs",), re.compile(r"#!?\[allow\("), "an `#[allow(...)]`"),
)
WEAKENING = re.compile(r"\|\|\s*true\b|continue-on-error:\s*true|--no-verify\b")
ASSERTION = re.compile(
    r"\bassert\b|\bexpect\s*\(|\bself\.assert\w*\s*\(|\bassert[A-Z]\w*\s*\(|\bt\.(Error|Fatal)"
)


class Result:
    def __init__(self) -> None:
        self.integrity: list[str] = []
        self.quality: list[str] = []
        self.warnings: list[str] = []
        self.checked: list[str] = []
        self.changed = 0
        self.no_gates = False


def handle(payload: dict[str, Any]) -> None:
    if wm_config.role_for(str(payload.get("agent_type") or "")) != "implementer":
        return
    handback = payload.get("hook_event_name") == "PreToolUse"
    agent = str(payload.get("agent_id") or payload.get("session_id") or "unknown")
    if not handback and _consume_pass(agent):
        return  # the handback already went through this gate
    if handback:
        message = _text(payload.get("tool_input"))
    else:
        message = str(payload.get("last_assistant_message") or "") or _last_message(payload)
    statuses = STATUS.findall(message)  # the last one counts, if the report quotes an earlier one
    status = statuses[-1].upper() if statuses else None

    try:
        root = wm_config.repository_root(Path(str(payload.get("cwd") or ".")))
        if root is None:
            _verdict(
                agent, "UNCHECKED", status, Result(), ["not a git repository: nothing was checked"]
            )
            return
        result = evaluate(root, agent, message, status)
    except Exception as error:  # noqa: BLE001 - a broken check counts as a failure, so the gate converges
        result = Result()
        result.integrity.append(f"The gate couldn't run its checks ({error}).")

    claims_done = status not in ("BLOCKED", "PARTIAL")
    blocking = result.integrity + (result.quality if claims_done else [])
    if not blocking:
        outcome = "PASSED" if claims_done else f"REPORTED_{status}"
        _verdict(agent, outcome, status, result)
        if handback:
            _record_pass(agent)
        wm_runtime.receipt("done_gate", payload, "pass", outcome, checked=result.checked)
        return

    # A BLOCKED or PARTIAL report on the same failures as the last send-back means the
    # implementer can't undo them within its limits (a lead-owned file, a commit): it's the lead's.
    acknowledged = not claims_done and _sent_back_for(agent) == blocking
    blocks = _record_block(agent)
    if blocks > MAX_BLOCKS or acknowledged:
        _verdict(agent, "FAILING", status, result, blocking)
        if handback:
            _record_pass(agent)
        why = (
            f"reported {status} on failures it can't undo itself"
            if acknowledged
            else f"finished with failing checks after {MAX_BLOCKS} retries"
        )
        warning = (
            f"wm done-gate: the implementer {why}. The lead has the details; verify before "
            "committing."
        )
        wm_runtime.receipt("done_gate", payload, "gave-up", "; ".join(blocking)[:400])
        wm_runtime.emit({"systemMessage": warning})
        return

    _verdict(agent, "SENT_BACK", status, result, blocking)
    first = "your report claims DONE, but" if claims_done else "before you hand back"
    advice = (
        "Fix the causes without suppressing them, then end with your report again. If you can't, "
        "report STATUS: PARTIAL (or BLOCKED) with the failing output."
        if claims_done
        else "Undo those changes, then end with your report again."
    )
    if result.integrity:
        advice += (
            " If undoing a change would break your limits, as with a lead-owned file or a commit, "
            "leave it and report STATUS: BLOCKED naming it: the lead takes it from there."
        )
    reason = f"Done-gate (wm): {first}:\n\n" + "\n\n".join(blocking) + f"\n\n{advice}"
    wm_runtime.receipt("done_gate", payload, "deny", "; ".join(blocking)[:400])
    if handback:
        wm_runtime.pre_tool("deny", reason)
    else:
        wm_runtime.emit({"decision": "block", "reason": reason})


def evaluate(root: Path, agent: str, message: str, status: str | None) -> Result:
    result = Result()
    config = wm_config.load(root)
    baseline = wm_runtime.read_json(wm_runtime.state_file("baseline", agent)) or {}
    base = baseline.get("tree") if baseline.get("root") == str(root) else None
    if base and not wm_git.is_tree(root, str(base)):
        result.warnings.append(
            "The implementer's starting snapshot was missing, so its changes were compared with HEAD."
        )
        base = None
    base = base or wm_git.head_tree(root) or EMPTY_TREE
    current = wm_git.snapshot(root)
    if current is None:
        result.integrity.append(
            "The gate couldn't snapshot the working tree (is another git process running?)."
        )
        return result
    started_at = baseline.get("commit") if baseline.get("root") == str(root) else None
    if started_at and wm_git.head_commit(root) != started_at:
        result.integrity.append(
            "HEAD moved while you worked, by a commit, reset or checkout: version control is the "
            "lead's. Don't try to undo it; report what ran instead."
        )
    changed = wm_git.changes(root, base, current)
    result.changed = len(changed)
    result.no_gates = not config["gates"] and not config["tests"]
    _integrity(root, base, current, changed, config, result)
    if message and status is None:
        result.quality.append(
            "Your reply doesn't end with the report from your instructions "
            "(STATUS: DONE | BLOCKED | PARTIAL, then SUMMARY, FILES, ...)."
        )
    if status not in ("BLOCKED", "PARTIAL") and changed:
        _run_gates(root, [path for _, path in changed], config, result)
    return result


def _integrity(
    root: Path,
    base: str,
    current: str,
    changed: list[tuple[str, str]],
    config: dict[str, Any],
    result: Result,
) -> None:
    owned = sorted({path for _, path in changed if wm_config.lead_owned_reason(path, config)})
    if owned:
        result.integrity.append(
            "Changed lead-owned files (by any tool): "
            + ", ".join(owned[:10])
            + ". Don't edit them back yourself: the lead restores them, or keeps the change."
        )
    deleted_tests = [
        p for s, p in changed if s == "D" and wm_config.matches_any(p, config["testGlobs"])
    ]
    if deleted_tests:
        result.warnings.append("Deleted test files: " + ", ".join(deleted_tests[:10]))

    suppressions: list[str] = []
    weakened: list[str] = []
    added: Counter[str] = Counter()
    removed: Counter[str] = Counter()
    for sign, path, text in wm_git.line_changes(root, base, current):
        is_test = wm_config.matches_any(path, config["testGlobs"])
        if sign == "-":
            if is_test and ASSERTION.search(text):
                removed[path] += 1
            continue
        if is_test and ASSERTION.search(text):
            added[path] += 1
        if not path.startswith(".claude/"):  # rules and hooks spell out these patterns
            for extensions, pattern, label in SUPPRESSIONS:
                if path.endswith(extensions) and pattern.search(text):
                    suppressions.append(f"- {path} adds {label}: `{text.strip()[:100]}`")
                    break
        if wm_config.matches_any(path, config["checkGlobs"]) and WEAKENING.search(text):
            weakened.append(f"- {path}: `{text.strip()[:100]}`")
    if suppressions:
        result.integrity.append(
            "New gate suppressions (only the lead adds one, with the reason in a comment):\n"
            + "\n".join(suppressions[:20])
        )
    if weakened:
        result.integrity.append(
            "Weakened check configuration (only the lead changes how checks run):\n"
            + "\n".join(weakened[:20])
        )
    thinner = sorted(p for p in removed if removed[p] > added.get(p, 0) and p not in deleted_tests)
    if thinner:
        result.warnings.append(
            "Test files that lost more assertions than they gained: " + ", ".join(thinner[:10])
        )


def _applicable(entries: list[dict[str, Any]], changed: list[str]) -> list[dict[str, Any]]:
    """The entries whose `when` globs match a changed file; an entry without `when` always runs."""
    result = []
    for entry in entries:
        globs = [g for g in entry.get("when") or [] if isinstance(g, str)]
        if not globs or any(wm_config.matches(p, g) for p in changed for g in globs):
            result.append(entry)
    return result


def _run_gates(root: Path, changed: list[str], config: dict[str, Any], result: Result) -> None:
    deadline = time.monotonic() + config["gateBudgetSeconds"]
    for group in ("gates", "tests"):  # the slow checks run only when the fast ones pass
        for entry in _applicable(config[group], changed):
            remaining = int(deadline - time.monotonic())
            if remaining < 5:
                result.quality.append(
                    f"The checks ran out of their {config['gateBudgetSeconds']}-second budget "
                    f"before `{entry['run']}` (gateBudgetSeconds in .claude/working-model.json)."
                )
                return
            failure = _run(root, entry, remaining)
            result.checked.append(str(entry["run"]))
            if failure:
                result.quality.append(failure)
        if result.quality:
            return


def _run(root: Path, entry: dict[str, Any], remaining: int) -> str | None:
    command = str(entry["run"])
    own = entry.get("timeout") if isinstance(entry.get("timeout"), int) else DEFAULT_TIMEOUT_SECONDS
    timeout = max(1, min(own, remaining))
    try:
        completed = subprocess.run(
            ["bash", "-c", command],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"`{command}` didn't finish within {timeout} seconds."
    except OSError as error:
        return f"`{command}` couldn't run: {error}"
    if completed.returncode == 0:
        return None
    output = (completed.stdout + completed.stderr).strip().splitlines()[-TAIL_LINES:]
    return f"`{command}` failed:\n" + "\n".join(output)


def _verdict(
    agent: str,
    outcome: str,
    status: str | None,
    result: Result,
    failures: list[str] | None = None,
) -> None:
    path = wm_runtime.state_file("verdict", agent)
    previous = wm_runtime.read_json(path) or {}
    history = list(previous.get("history") or [])
    if previous.get("outcome") == "SENT_BACK" and previous.get("failures"):
        history.append(previous["failures"])
    record = {
        "outcome": outcome,
        "status": status,
        "failures": failures or [],
        "history": history,
        "warnings": result.warnings,
        "checked": result.checked,
        "changed": result.changed,
        "no_gates_configured": result.no_gates,
        "t": time.time(),
    }
    wm_runtime.write_json(path, record)


def _text(value: object) -> str:
    """Every string inside a tool input (SubagentHandback carries the report in `message`)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value)
    return ""


def _sent_back_for(agent: str) -> list[str] | None:
    """The failures of `agent`'s last send-back, if its latest verdict is one."""
    previous = wm_runtime.read_json(wm_runtime.state_file("verdict", agent)) or {}
    return previous.get("failures") if previous.get("outcome") == "SENT_BACK" else None


def _record_block(agent: str) -> int:
    """Count one more block for `agent` and return the new count."""
    path = wm_runtime.state_file("blocks", agent)
    count = int((wm_runtime.read_json(path) or {}).get("count") or 0) + 1
    wm_runtime.write_json(path, {"count": count})
    return count


def _record_pass(agent: str) -> None:
    """Remember that `agent`'s handback passed, so its SubagentStop doesn't run the checks again."""
    wm_runtime.write_json(wm_runtime.state_file("passed", agent), {"t": time.time()})


def _consume_pass(agent: str) -> bool:
    path = wm_runtime.state_file("passed", agent)
    if not path.exists():
        return False
    path.unlink()
    return True


def _last_message(payload: dict[str, Any]) -> str:
    """The subagent's final text, from its own transcript, when the payload doesn't carry it."""
    transcript = payload.get("agent_transcript_path")
    if not isinstance(transcript, str):
        return ""
    try:
        lines = Path(transcript).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get("message") if isinstance(entry, dict) else None
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
        texts = [
            block.get("text", "")
            for block in content or []
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if any(texts):
            return "\n".join(texts)
    return ""


if __name__ == "__main__":
    sys.exit(wm_runtime.run("done_gate", handle, fail_closed=True))
