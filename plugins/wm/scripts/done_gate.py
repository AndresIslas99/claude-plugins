#!/usr/bin/env python3
"""The implementer's done-gate: a work order isn't done while its gates fail.

When wm:implementer's report claims STATUS: DONE (or has no status), this runs the project's
gates for the changed files (`gates`, then `tests`, in .claude/working-model.json) and scans
the added lines for gate suppressions. On a failure it sends the implementer back to work, so
it fixes the cause or reports PARTIAL or BLOCKED honestly. That happens at most MAX_BLOCKS
times per agent, so it can't loop forever.

Subagents end by calling the SubagentHandback tool with their report, and Claude Code
discards a SubagentStop block that arrives after it ("turn ended by tool result", measured
2026-10-06). So the gate runs as a PreToolUse hook on SubagentHandback and denies the
handback; as a SubagentStop hook it covers a subagent that ends with plain text instead.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm_config

MAX_BLOCKS = 2
TAIL_LINES = 30
DEFAULT_TIMEOUT_SECONDS = 600

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


def main() -> int:
    payload = json.load(sys.stdin)
    if wm_config.role_for(str(payload.get("agent_type") or "")) != "implementer":
        return 0
    handback = payload.get("hook_event_name") == "PreToolUse"
    agent = str(payload.get("agent_id") or payload.get("session_id") or "unknown")
    if handback:
        message = _text(payload.get("tool_input"))
    elif _consume_pass(agent):
        return 0  # the handback already went through this gate
    else:
        message = str(payload.get("last_assistant_message") or "") or _last_message(payload)

    failures = _check(message, Path(str(payload.get("cwd") or ".")))
    if not failures:
        if handback:
            _record_pass(agent)
        return 0

    if _record_block(agent) > MAX_BLOCKS:
        if handback:
            _record_pass(agent)
        warning = (
            f"wm done-gate: the implementer finished with failing checks after {MAX_BLOCKS} "
            "retries. Verify the gates before committing."
        )
        print(json.dumps({"systemMessage": warning}))
        return 0

    reason = (
        "Done-gate (wm): your report claims DONE, but:\n\n"
        + "\n\n".join(failures)
        + "\n\nFix the causes without suppressing them, then end with your report again. "
        "If you can't, report STATUS: PARTIAL (or BLOCKED) with the failing output."
    )
    if handback:
        decision: dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    else:
        decision = {"decision": "block", "reason": reason}
    print(json.dumps(decision))
    return 0


def _check(message: str, cwd: Path) -> list[str]:
    """What stands between the report and DONE; empty when nothing does."""
    statuses = STATUS.findall(message)  # the last one counts, if the report quotes an earlier one
    status = statuses[-1].upper() if statuses else None
    if status in ("BLOCKED", "PARTIAL"):
        return []  # an honest report: the lead takes it from here
    root = wm_config.repository_root(cwd)
    if root is None:
        return []
    tracked = _git(root, "diff", "--name-only", "HEAD").splitlines()
    untracked = _git(root, "ls-files", "--others", "--exclude-standard").splitlines()
    changed = sorted({path for path in tracked + untracked if path})

    failures: list[str] = []
    if message and not status:
        failures.append(
            "Your reply doesn't end with the report from your instructions "
            "(STATUS: DONE | BLOCKED | PARTIAL, then SUMMARY, FILES, ...)."
        )
    if changed:
        config = wm_config.load(root)
        failures += _suppressions(root, untracked)
        failures += _run_gates(root, changed, config)
    return failures


def _applicable(entries: list[dict[str, Any]], changed: list[str]) -> list[dict[str, Any]]:
    """The entries whose `when` globs match a changed file; an entry without `when` always runs."""
    result = []
    for entry in entries:
        globs = [g for g in entry.get("when") or [] if isinstance(g, str)]
        if not globs or any(wm_config.matches(p, g) for p in changed for g in globs):
            result.append(entry)
    return result


def _run_gates(root: Path, changed: list[str], config: dict[str, Any]) -> list[str]:
    failures = [
        failure for entry in _applicable(config["gates"], changed) if (failure := _run(root, entry))
    ]
    if not failures:  # the slow checks run only when the fast ones pass
        failures = [
            failure
            for entry in _applicable(config["tests"], changed)
            if (failure := _run(root, entry))
        ]
    return failures


def _run(root: Path, entry: dict[str, Any]) -> str | None:
    command = str(entry["run"])
    timeout = entry.get("timeout") if isinstance(entry.get("timeout"), int) else None
    timeout = timeout or DEFAULT_TIMEOUT_SECONDS
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


def _suppressions(root: Path, untracked: list[str]) -> list[str]:
    found: list[str] = []
    for path, text in _added_lines(root, untracked):
        if path.startswith(".claude/"):
            continue  # hooks and rules spell out the patterns they look for
        for extensions, pattern, label in SUPPRESSIONS:
            if path.endswith(extensions) and pattern.search(text):
                found.append(f"- {path} adds {label}: `{text.strip()[:100]}`")
                break
    if not found:
        return []
    return [
        "New gate suppressions (only the lead adds one, with the reason in a comment):\n"
        + "\n".join(found[:20])
    ]


def _added_lines(root: Path, untracked: list[str]) -> Iterator[tuple[str, str]]:
    path = None
    diff = _git(root, "diff", "--unified=0", "--no-color", "--no-ext-diff", "HEAD")
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[len("+++ b/") :] if line.startswith("+++ b/") else None
        elif line.startswith("+") and path is not None:
            yield path, line[1:]
    for name in untracked:
        file = root / name
        try:
            if file.stat().st_size > 1_000_000:
                continue
            for text in file.read_text(encoding="utf-8").splitlines():
                yield name, text
        except (OSError, UnicodeDecodeError):
            continue


def _text(value: object) -> str:
    """Every string inside a tool input (SubagentHandback carries the report in `message`)."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(_text(item) for item in value)
    return ""


def _record_block(agent: str) -> int:
    """Count one more block for `agent` and return the new count."""
    counter = _state_file(agent, "count")
    try:
        count = int(counter.read_text()) + 1
    except (OSError, ValueError):
        count = 1
    counter.write_text(str(count))
    return count


def _record_pass(agent: str) -> None:
    """Remember that `agent`'s handback passed, so its SubagentStop doesn't run the gates again."""
    _state_file(agent, "passed").touch()


def _consume_pass(agent: str) -> bool:
    marker = _state_file(agent, "passed")
    if not marker.exists():
        return False
    marker.unlink()
    return True


def _state_file(agent: str, kind: str) -> Path:
    state = Path(tempfile.gettempdir()) / "wm-done-gate"
    state.mkdir(exist_ok=True)
    name = re.sub(r"[^\w.-]", "_", agent)  # outside the f-string: Python 3.9 runs these hooks
    return state / f"{name}.{kind}"


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


def _git(cwd: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return completed.stdout if completed.returncode == 0 else ""


if __name__ == "__main__":
    sys.exit(main())
