"""Run a real coding agent on a task and record what happened.

The agent works in a throwaway git repo seeded with the task workspace and SPEC.md.
Afterwards the workspace is checked like any other candidate and the whole run
(command, prompt, transcript, diff, check result) is saved as JSON under runs/.
The report renders these records and nothing else: no run, no row.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from zoo.check import check
from zoo.tasks import Task

PROMPT = (
    "Implement solution.py so that it satisfies SPEC.md. "
    "The tests in tests/ should pass; run them with `python -m pytest`."
)

PRESETS = {
    # Flags differ between CLI versions; override with --command if these drift.
    "claude": (
        "claude -p {prompt} --output-format stream-json --verbose "
        "--permission-mode acceptEdits --allowedTools 'Bash(python -m pytest:*)'"
    ),
    "codex": "codex exec --full-auto {prompt}",
}

MAX_TRANSCRIPT_CHARS = 500_000


def run_agent(
    task: Task,
    agent: str,
    runs_dir: Path,
    command: str | None = None,
    timeout: int = 900,
) -> Path:
    template = command or PRESETS.get(agent)
    if template is None:
        raise ValueError(f"unknown agent preset {agent!r}; pass --command")
    shell_command = template.replace("{prompt}", shlex.quote(PROMPT))

    workspace = Path(tempfile.mkdtemp(prefix=f"zoo-agent-{task.name}-"))
    try:
        _seed_workspace(task, workspace)
        started = datetime.now(UTC)
        began = time.monotonic()
        try:
            proc = subprocess.run(
                shell_command,
                shell=True,
                cwd=workspace,
                env=_agent_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exit_code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code, stdout, stderr = -1, _text(exc.stdout), f"timed out after {timeout}s"
        duration = time.monotonic() - began

        result = check(task, workspace, label=f"{agent} on {task.name}")
        record = {
            "kind": "agent-run",
            "schema": 1,
            "task": task.name,
            "agent": agent,
            "command": shell_command,
            "prompt": PROMPT,
            "started_at": started.isoformat(timespec="seconds"),
            "duration_s": round(duration, 1),
            "exit_code": exit_code,
            "transcript": stdout[-MAX_TRANSCRIPT_CHARS:],
            "stderr": stderr[-20_000:],
            "workspace_diff": _git(workspace, "diff", "--cached", "--no-color", stage=True),
            "check": result.to_dict(),
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    runs_dir.mkdir(parents=True, exist_ok=True)
    path = runs_dir / f"{started:%Y%m%dT%H%M%SZ}-{task.name}-{agent}.json"
    path.write_text(json.dumps(record, indent=2))
    return path


def _seed_workspace(task: Task, workspace: Path) -> None:
    shutil.copytree(task.workspace, workspace, dirs_exist_ok=True)
    shutil.copy2(task.path / "SPEC.md", workspace / "SPEC.md")
    _git(workspace, "init", "-q")
    _git(workspace, "add", "-A")
    _git(
        workspace, "-c", "user.name=zoo", "-c", "user.email=zoo@localhost", "commit", "-qm", "task"
    )


def _agent_env() -> dict[str, str]:
    """Put this interpreter (which has pytest and hypothesis) first on the agent's PATH."""
    env = dict(os.environ)
    env["PATH"] = f"{Path(sys.executable).parent}{os.pathsep}{env.get('PATH', '')}"
    return env


def _git(cwd: Path, *args: str, stage: bool = False) -> str:
    if stage:
        subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
    proc = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return proc.stdout


def _text(value: bytes | str | None) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value or ""
