"""The project's checks for a set of changed files: its `gates`, then its `tests`.

done_gate.py runs them on the implementer's changes before it may report DONE, and
commit_gate.py on the lead's changes before a commit. Each entry in .claude/working-model.json
runs in the repository root when a changed file matches one of its `when` globs; an entry
without `when` always runs. The tests run only when every gate passed, and everything runs
within gateBudgetSeconds.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

import wm_config

TAIL_LINES = 30
DEFAULT_TIMEOUT_SECONDS = 600


def run(root: Path, changed: list[str], config: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(the commands that ran, the failures), each failure with the tail of its output."""
    checked: list[str] = []
    failures: list[str] = []
    deadline = time.monotonic() + config["gateBudgetSeconds"]
    for group in ("gates", "tests"):  # the slow checks run only when the fast ones pass
        for entry in applicable(config[group], changed):
            remaining = int(deadline - time.monotonic())
            if remaining < 5:
                failures.append(
                    f"The checks ran out of their {config['gateBudgetSeconds']}-second budget "
                    f"before `{entry['run']}` (gateBudgetSeconds in .claude/working-model.json)."
                )
                return checked, failures
            failure = _run(root, entry, remaining)
            checked.append(str(entry["run"]))
            if failure:
                failures.append(failure)
        if failures:
            break
    return checked, failures


def applicable(entries: list[dict[str, Any]], changed: list[str]) -> list[dict[str, Any]]:
    """The entries whose `when` globs match a changed file; an entry without `when` always runs."""
    result = []
    for entry in entries:
        globs = [g for g in entry.get("when") or [] if isinstance(g, str)]
        if not globs or any(wm_config.matches(p, g) for p in changed for g in globs):
            result.append(entry)
    return result


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
