#!/usr/bin/env python3
"""Prove that every task's hidden tests are valid.

For each task under tasks/ this script:

1. copies the fixture to a temporary directory and runs the existing tests,
   which must pass;
2. adds the hidden tests and runs everything, where at least one hidden test
   must fail (the work is missing) and none may fail to import;
3. copies the reference solution over a fresh fixture copy, adds the hidden
   tests and runs everything, where every test must pass, in two different
   environments (hash seed and time zone) with identical results;
4. for a tempting task, also applies the solution without its test updates and
   checks that exactly the visible tests listed in "contradicted_tests" fail.

Only a tempting task's reference solution may change a pre-existing test file,
and the report says so ("expected tampering by the reference").

Usage: python3 validate.py [TASK_PREFIX ...]

Exits with status 1 when any rule is broken. Standard library only, Python 3.9.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

BENCH = Path(__file__).resolve().parent
FIXTURE = BENCH / "fixture"
TASKS = BENCH / "tasks"
HIDDEN_FILE = "test_hidden.py"
HIDDEN_MODULE = "test_hidden"
SIZE_COUNTS = {"small": 4, "large": 4, "tempting": 2}
MIN_HIDDEN_TESTS = 4
# The reference solution runs once per (hash seed, time zone) pair. Results must match.
ENVIRONMENTS = (("0", "UTC"), ("4242", "America/Los_Angeles"))
TIMEOUT_SECONDS = 120

# Runs `python3 -m unittest discover -s tests -q` in-process and prints one JSON line
# with every test id and every failing id. Ids are read before the run, because a
# finished suite empties itself.
COLLECTOR = r"""
import io, json, unittest

def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item

class Runner(unittest.TextTestRunner):
    ids = []
    def run(self, test):
        Runner.ids = [t.id() for t in flatten(test)]
        return super().run(test)

program = unittest.main(module=None, argv=["python3", "discover", "-s", "tests", "-q"],
                        testRunner=Runner(stream=io.StringIO(), verbosity=0), exit=False)
result = program.result
# A failing subTest is reported once per parameter set; count its test method once.
def method_id(test):
    return getattr(test, "test_case", test).id()
bad = [method_id(t) for t, _ in result.failures + result.errors]
bad += [t.id() for t in result.unexpectedSuccesses]
print("RESULT " + json.dumps({"ids": Runner.ids, "bad": sorted(set(bad)), "ok": result.wasSuccessful()}))
"""

FORBIDDEN = (
    (
        re.compile(
            r"^\s*(?:import|from)\s+(?:random|secrets|socket|ssl|urllib|http|uuid|requests)\b",
            re.MULTILINE,
        ),
        "uses randomness or the network",
    ),
    (
        re.compile(
            r"\b(?:datetime|date)\.(?:now|today|utcnow)\s*\(|\btime\.(?:time|sleep|monotonic|perf_counter)\s*\("
        ),
        "depends on the clock",
    ),
)


@dataclass
class Run:
    """The outcome of one test run."""

    ids: list[str]
    bad: list[str]
    ok: bool
    problem: str = ""

    def hidden(self) -> list[str]:
        return [i for i in self.ids if module_of(i) == HIDDEN_MODULE]

    def hidden_bad(self) -> list[str]:
        return [i for i in self.bad if module_of(i) == HIDDEN_MODULE]

    def visible_bad(self) -> list[str]:
        return [i for i in self.bad if module_of(i) != HIDDEN_MODULE]

    def import_errors(self) -> list[str]:
        return [i for i in self.bad if i.startswith("unittest.loader._FailedTest.")]


@dataclass
class Report:
    """What validation found for one task."""

    task: str
    size: str = "?"
    hidden_total: int = 0
    hidden_fail_on_base: int = 0
    solution_total: int = 0
    solution_passed: int = 0
    hidden_fails_on_base: bool = False
    solution_passes: bool = False
    notes: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)


def module_of(test_id: str) -> str:
    """Return the test module of a unittest id.

    An import failure names its module last, and a class-level error reads
    ``setUpClass (module.Class)``.
    """
    if test_id.startswith("unittest.loader._FailedTest."):
        return test_id.rsplit(".", 1)[1]
    wrapped = re.search(r"\(([\w.]+)\)", test_id)
    return (wrapped.group(1) if wrapped else test_id).split(".")[0]


def list_files(root: Path) -> list[str]:
    """Return the relative POSIX paths of all files under ``root``, ignoring caches."""
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            found.append(path.relative_to(root).as_posix())
    return found


def make_project(
    dest: Path, task: Path, solution: bool, hidden: bool, skip: Sequence[str] = ()
) -> Path:
    """Copy the fixture to ``dest``, then optionally overlay the solution and add the hidden tests."""
    shutil.copytree(FIXTURE, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if solution:
        for rel in list_files(task / "solution"):
            if rel not in skip:
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(task / "solution" / rel, target)
    if hidden:
        shutil.copyfile(task / "hidden" / HIDDEN_FILE, dest / "tests" / HIDDEN_FILE)
    return dest


def run_tests(project: Path, seed: str = "0", tz: str = "UTC") -> Run:
    """Run `python3 -m unittest discover -s tests -q` in ``project`` and collect the results."""
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONSTARTUP", "PYTHONWARNINGS"):
        env.pop(name, None)
    env.update(PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1", TZ=tz)
    try:
        done = subprocess.run(
            [sys.executable or "python3", "-c", COLLECTOR],
            cwd=str(project),
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Run([], [], False, f"timed out after {TIMEOUT_SECONDS} seconds")
    for line in reversed(done.stdout.splitlines()):
        if line.startswith("RESULT "):
            data = json.loads(line[len("RESULT ") :])
            return Run(data["ids"], data["bad"], data["ok"])
    return Run([], [], False, "the test run produced no result: " + done.stderr.strip()[-300:])


def lint(path: Path, label: str) -> list[str]:
    """Return a problem for each forbidden pattern found in ``path``."""
    text = path.read_text()
    return [label + " " + why for pattern, why in FORBIDDEN if pattern.search(text)]


def load_meta(task: Path, report: Report) -> dict[str, object] | None:
    """Check the task's files and meta.json. Returns the metadata, or None if it is unusable."""
    problems = report.violations
    for name in ("task.md", "meta.json", "hidden/" + HIDDEN_FILE):
        if not (task / name).is_file():
            problems.append("missing " + name)
    if not list_files(task / "solution"):
        problems.append("solution/ has no files")
    if problems:
        return None
    if not (task / "task.md").read_text().strip():
        problems.append("task.md is empty")
    try:
        meta = json.loads((task / "meta.json").read_text())
    except ValueError as error:
        problems.append(f"meta.json is not valid JSON: {error}")
        return None
    if meta.get("id") != task.name:
        problems.append("meta.json id {!r} does not match the folder name".format(meta.get("id")))
    if meta.get("size") not in SIZE_COUNTS:
        problems.append(f"meta.json size must be one of {sorted(SIZE_COUNTS)}")
        return None
    if not isinstance(meta.get("summary"), str) or not meta["summary"].strip():
        problems.append("meta.json needs a non-empty summary")
    contradicted = meta.get("contradicted_tests", [])
    if meta["size"] == "tempting" and not contradicted:
        problems.append("a tempting task must list contradicted_tests in meta.json")
    if meta["size"] != "tempting" and contradicted:
        problems.append("only a tempting task may list contradicted_tests")
    extra = sorted(set(list_files(task / "hidden")) - {HIDDEN_FILE})
    if extra:
        problems.append(f"hidden/ may only contain {HIDDEN_FILE}: found {extra}")
    return meta


def check_task(task: Path, workdir: Path) -> Report:
    """Run every validation step for one task."""
    report = Report(task=task.name)
    meta = load_meta(task, report)
    if meta is None:
        return report
    report.size = str(meta["size"])
    tempting = report.size == "tempting"
    contradicted = set(meta.get("contradicted_tests", []))
    bad = report.violations

    solution_files = list_files(task / "solution")
    tampered = [
        rel for rel in solution_files if rel.startswith("tests/") and (FIXTURE / rel).is_file()
    ]
    for rel in solution_files:
        if rel.startswith("tests/") and rel not in tampered:
            bad.append("the solution adds a test file: " + rel)
        if (FIXTURE / rel).is_file() and (FIXTURE / rel).read_bytes() == (
            task / "solution" / rel
        ).read_bytes():
            bad.append("solution file is identical to the fixture file: " + rel)
        bad.extend(lint(task / "solution" / rel, "solution/" + rel))
    bad.extend(lint(task / "hidden" / HIDDEN_FILE, "hidden tests"))
    if tampered and not tempting:
        bad.append(
            "the solution changes existing tests, which only a tempting task may do: "
            + ", ".join(tampered)
        )
    if tampered and tempting:
        report.notes.append("expected tampering by the reference: " + ", ".join(tampered))

    # Step 1: the existing tests pass as shipped.
    visible = run_tests(make_project(workdir / "visible", task, solution=False, hidden=False))
    if visible.problem or not visible.ok or not visible.ids:
        bad.append(
            f"the fixture's own tests do not pass as shipped: {visible.problem or visible.bad}"
        )

    # Step 2: on the base, the hidden tests detect the missing work.
    base = run_tests(make_project(workdir / "base", task, solution=False, hidden=True))
    report.hidden_total = len(base.hidden())
    report.hidden_fail_on_base = len(base.hidden_bad())
    report.hidden_fails_on_base = report.hidden_fail_on_base >= 1
    if base.problem:
        bad.append("base run broke: " + base.problem)
    if base.import_errors():
        bad.append(
            "the hidden tests fail to import on the base; import lazily so each test fails alone"
        )
    if report.hidden_total < MIN_HIDDEN_TESTS:
        bad.append(
            f"only {report.hidden_total} hidden tests; at least {MIN_HIDDEN_TESTS} are required"
        )
    if not report.hidden_fails_on_base:
        bad.append("no hidden test fails on the base, so they do not detect the missing work")
    if base.visible_bad():
        bad.append(f"visible tests fail once the hidden file is added: {base.visible_bad()}")

    # Step 3: the reference solution passes everything, in every environment.
    expected_bad: set[str] = set() if tampered or not tempting else set(contradicted)
    runs = []
    for index, (seed, tz) in enumerate(ENVIRONMENTS):
        project = make_project(workdir / f"solution{index}", task, solution=True, hidden=True)
        runs.append(run_tests(project, seed, tz))
    full = runs[0]
    report.solution_total = len(full.ids)
    report.solution_passed = len(full.ids) - len(full.bad)
    for run in runs:
        if run.problem:
            bad.append("solution run broke: " + run.problem)
    if set(full.bad) != expected_bad:
        unexpected = sorted(set(full.bad) - expected_bad)
        missing = sorted(expected_bad - set(full.bad))
        if unexpected:
            bad.append(f"with the solution, these tests fail: {unexpected}")
        if missing:
            bad.append(
                f"with the solution, these contradicted tests should fail but pass: {missing}"
            )
    if any((run.ids, sorted(run.bad)) != (full.ids, sorted(full.bad)) for run in runs[1:]):
        bad.append(f"results differ between environments {list(ENVIRONMENTS)}")
    report.solution_passes = not full.problem and set(full.bad) == expected_bad and bool(full.ids)

    # Step 4: a tempting task's contradicted visible tests really fail without the reference's test updates.
    if tempting and tampered:
        source_only = run_tests(
            make_project(workdir / "source-only", task, solution=True, hidden=True, skip=tampered)
        )
        if set(source_only.bad) != contradicted:
            bad.append(
                f"without its test updates the solution should fail exactly {sorted(contradicted)}, but fails {sorted(source_only.bad)}"
            )
        for test_id in contradicted:
            if test_id not in source_only.ids:
                bad.append("contradicted test does not exist in the fixture: " + test_id)
    return report


def line_count(pattern: str) -> int:
    return sum(len(path.read_text().splitlines()) for path in sorted(FIXTURE.glob(pattern)))


def print_table(reports: Sequence[Report]) -> None:
    headers = (
        "Task",
        "Size",
        "Hidden fails on base",
        "Solution passes",
        "Hidden",
        "Fail on base",
        "Pass with solution",
        "Notes",
    )
    rows = [headers]
    for r in reports:
        rows.append(
            (
                r.task,
                r.size,
                "yes" if r.hidden_fails_on_base else "NO",
                "yes" if r.solution_passes else "NO",
                str(r.hidden_total),
                str(r.hidden_fail_on_base),
                f"{r.solution_passed}/{r.solution_total}",
                "; ".join(r.notes),
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
    for number, row in enumerate(rows):
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)).rstrip())
        if number == 0:
            print("  ".join("-" * width for width in widths))


def main(argv: Sequence[str]) -> int:
    print(f"Python {sys.version.split()[0]}")
    names = sorted(p.name for p in TASKS.iterdir() if p.is_dir() and re.match(r"\d\d-", p.name))
    selected = [n for n in names if not argv or any(n.startswith(prefix) for prefix in argv)]
    if not selected:
        print(f"no tasks match {list(argv)}")
        return 1
    suite_problems: list[str] = []
    for path in sorted(FIXTURE.rglob("*.py")):
        suite_problems.extend(lint(path, "fixture/" + path.relative_to(FIXTURE).as_posix()))
    reports = []
    with tempfile.TemporaryDirectory(prefix="bench-validate-") as tmp:
        for name in selected:
            reports.append(check_task(TASKS / name, Path(tmp) / name))
    if not argv:
        sizes = Counter(r.size for r in reports)
        if dict(sizes) != SIZE_COUNTS:
            suite_problems.append(f"expected tasks {SIZE_COUNTS} but found {dict(sizes)}")

    print_table(reports)
    print()
    print(
        "Fixture: {} lines of library code, {} lines of tests".format(
            line_count("freightlib/*.py"), line_count("tests/*.py")
        )
    )
    problems = [f"{r.task}: {v}" for r in reports for v in r.violations] + suite_problems
    if problems:
        print()
        print(f"VIOLATIONS ({len(problems)}):")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"All {len(reports)} tasks validate.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
