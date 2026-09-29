import json
import shlex
import sys

from zoo.agent_runner import PRESETS, run_agent
from zoo.tasks import get_task


def test_fake_agent_run_is_checked_and_recorded(tmp_path):
    """A stand-in 'agent' that copies the honest fixture; no real agent CLI is called."""
    task = get_task("merge_date_ranges")
    honest = task.path / "specimens" / "honest" / "solution.py"
    copy = f"import shutil; shutil.copy({str(honest)!r}, 'solution.py')"
    command = f"{shlex.quote(sys.executable)} -c {shlex.quote(copy)} {{prompt}}"

    path = run_agent(task, agent="fake", command=command, runs_dir=tmp_path)

    record = json.loads(path.read_text())
    assert record["kind"] == "agent-run"
    assert record["exit_code"] == 0
    assert "SPEC.md" in record["command"]
    assert "+++ b/solution.py" in record["workspace_diff"]
    assert record["check"]["verdict"] == "clean"


def test_presets_take_the_prompt():
    assert all("{prompt}" in template for template in PRESETS.values())
