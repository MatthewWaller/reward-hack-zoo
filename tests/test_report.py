import json

from zoo.report import load_runs, render


def test_report_shows_specimens_and_empty_run_state(specimen_rows):
    html = render(list(specimen_rows.values()), runs=[])
    assert "No recorded agent runs yet" in html
    assert "skip_the_hard_test" in html
    assert "illustrative fixture hand-written" in html
    assert "$specimen_table" not in html and "$stats" not in html


def test_report_renders_recorded_runs_escaped(tmp_path, specimen_rows):
    result = specimen_rows["lru_cache/honest"].result.to_dict()
    record = {
        "kind": "agent-run",
        "task": "lru_cache",
        "agent": "claude",
        "command": "claude -p '<prompt>'",
        "started_at": "2026-10-01T12:00:00+00:00",
        "duration_s": 42.0,
        "exit_code": 0,
        "transcript": "<script>alert(1)</script>",
        "workspace_diff": "",
        "check": result,
    }
    (tmp_path / "run.json").write_text(json.dumps(record))
    (tmp_path / "not-a-run.json").write_text(json.dumps({"kind": "something-else"}))
    (tmp_path / "broken.json").write_text("{")

    runs = load_runs(tmp_path)
    assert len(runs) == 1
    html = render([], runs)
    assert "No recorded agent runs yet" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>alert(1)" not in html


def test_missing_runs_dir_is_empty(tmp_path):
    assert load_runs(tmp_path / "nope") == []
