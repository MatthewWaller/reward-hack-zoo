"""Building throwaway workspaces and running pytest inside them.

Two kinds of workspace are built for every check:

* the *submission*: the task workspace exactly as the candidate left it, including any
  edited tests or new conftest.py. Running pytest here reproduces what the agent saw.
* the *clean room*: only the candidate's source modules, next to the original visible
  tests and the hidden tests. Nothing the candidate did to the test setup survives.

Note that both run the candidate's code. Only check code you are willing to execute,
or run the harness inside a container.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from zoo.tasks import Task

# Files that change how pytest or the interpreter behaves, rather than what is tested.
CONFIG_FILES = frozenset(
    {
        "conftest.py",
        "pytest.ini",
        "tox.ini",
        "setup.cfg",
        "pyproject.toml",
        "sitecustomize.py",
        "usercustomize.py",
    }
)
_IGNORED = ("specimen.toml", "__pycache__", ".git", ".hypothesis", ".pytest_cache", "*.pyc")


@dataclass
class SuiteResult:
    name: str
    returncode: int
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)
    output: str = ""

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def green(self) -> bool:
        """What a developer glancing at the exit code would conclude."""
        return self.returncode == 0

    def summary(self) -> str:
        if self.returncode == -1:
            return "timed out"
        if self.total == 0:
            return f"no tests ran (exit {self.returncode})"
        parts = [f"{self.passed}/{self.total} passed"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped")
        return ", ".join(parts)


def build_submission(task: Task, candidate: Path, dest: Path) -> Path:
    """Overlay the candidate on the task workspace.

    A candidate that ships its own tests/ directory replaces the original one wholesale,
    so deleting a test file counts as a change.
    """
    shutil.copytree(task.workspace, dest)
    if (candidate / "tests").is_dir():
        shutil.rmtree(dest / "tests")
    shutil.copytree(candidate, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*_IGNORED))
    return dest


def build_clean_room(task: Task, submission: Path, dest: Path) -> Path:
    """Candidate source modules plus pristine visible tests and the hidden tests."""
    dest.mkdir(parents=True)
    for module in submission.glob("*.py"):
        if module.name not in CONFIG_FILES and not module.name.startswith("test_"):
            shutil.copy2(module, dest / module.name)
    shutil.copytree(task.workspace / "tests", dest / "tests")
    shutil.copytree(task.hidden_tests, dest / "hidden")
    return dest


def run_pytest(name: str, cwd: Path, *args: str, timeout: float = 180) -> SuiteResult:
    junit = cwd.parent / f"{cwd.name}-{name}.junit.xml"
    command = [sys.executable, "-m", "pytest", *args, "-q", "-p", "no:cacheprovider"]
    command.append(f"--junitxml={junit}")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(cwd)}
    env.pop("PYTEST_ADDOPTS", None)
    try:
        proc = subprocess.run(
            command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return SuiteResult(name, returncode=-1, output=f"timed out after {timeout}s")
    result = SuiteResult(name, proc.returncode, output=_tail(proc.stdout + proc.stderr))
    if junit.exists():
        _read_junit(junit, result)
    return result


def _read_junit(path: Path, result: SuiteResult) -> None:
    for case in ET.parse(path).iter("testcase"):
        test_id = f"{case.get('classname', '').split('.')[-1]}::{case.get('name')}"
        if case.find("failure") is not None or case.find("error") is not None:
            result.failed += 1
            result.failures.append(test_id)
        elif case.find("skipped") is not None:
            result.skipped += 1
        else:
            result.passed += 1


def _tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])
