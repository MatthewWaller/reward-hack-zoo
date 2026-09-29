from typer.testing import CliRunner

from zoo.cli import app

runner = CliRunner()


def test_list_shows_every_task():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    for name in ("parse_duration", "dedupe_occurrences", "rate_limiter", "lru_cache"):
        assert name in result.output


def test_check_exits_nonzero_on_a_hack(tmp_path):
    specimen = "tasks/allocate_cents/specimens/special_case_example"
    out = tmp_path / "result.json"
    result = runner.invoke(app, ["check", specimen, "--json", str(out)])
    assert result.exit_code == 1
    assert "HACK" in result.output
    assert '"verdict": "hack"' in out.read_text()
