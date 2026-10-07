#!/usr/bin/env python3
"""Tests for launch.sh: every failure becomes the hook's policy, even from a path with spaces.

python3 plugins/wm/tests/test_launcher.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from support import LAUNCHER, Suite

SCRIPTS = {
    "ok.py": "import sys\nsys.stdin.read()\nprint('{}')\n",
    "crash.py": "raise RuntimeError('boom')\n",
    "blocks.py": "import sys\nsys.stderr.write('no')\nsys.exit(2)\n",
}


def launch(
    directory: Path, policy: str, script: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ, WM_PYTHON=sys.executable)
    environment.update(env or {})
    return subprocess.run(
        ["bash", str(directory / "launch.sh"), policy, script],
        input="{}",
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def main() -> int:
    suite = Suite("launcher")
    with tempfile.TemporaryDirectory() as directory:
        scripts = Path(directory) / "Application Support" / "wm scripts"  # spaces, as in ~/Library
        scripts.mkdir(parents=True)
        shutil.copy(LAUNCHER, scripts / "launch.sh")
        for name, body in SCRIPTS.items():
            (scripts / name).write_text(body)

        suite.equal(
            "a working hook from a path with spaces",
            launch(scripts, "closed", "ok.py").returncode,
            0,
        )
        missing = launch(scripts, "closed", "missing.py")
        suite.equal("closed: a missing script blocks", missing.returncode, 2)
        suite.check("and says why", "missing" in missing.stderr, missing.stderr)
        suite.equal(
            "open: a missing script lets it through",
            launch(scripts, "open", "missing.py").returncode,
            0,
        )
        crashed = launch(scripts, "closed", "crash.py")
        suite.equal("closed: a crash blocks", crashed.returncode, 2)
        suite.check("and says why", "exit code 1" in crashed.stderr, crashed.stderr)
        suite.equal(
            "open: a crash lets it through", launch(scripts, "open", "crash.py").returncode, 0
        )
        suite.equal(
            "a hook's own exit 2 passes through", launch(scripts, "open", "blocks.py").returncode, 2
        )
        fallback = launch(scripts, "closed", "ok.py", {"WM_PYTHON": "/nonexistent/python3"})
        suite.equal("a wrong WM_PYTHON falls back to python3", fallback.returncode, 0)
    return suite.finish()


if __name__ == "__main__":
    sys.exit(main())
