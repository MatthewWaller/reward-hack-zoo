from zoo.sandbox import build_clean_room, build_submission
from zoo.tasks import get_task


def test_candidate_tests_dir_replaces_the_original(tmp_path):
    task = get_task("lru_cache")
    candidate = tmp_path / "candidate"
    (candidate / "tests").mkdir(parents=True)
    (candidate / "solution.py").write_text("x = 1\n")
    submission = build_submission(task, candidate, tmp_path / "submission")
    assert not (submission / "tests" / "test_visible.py").exists()
    assert (submission / "solution.py").read_text() == "x = 1\n"


def test_clean_room_drops_config_and_restores_tests(tmp_path):
    task = get_task("rate_limiter")
    specimen = task.path / "specimens" / "force_pass_conftest"
    submission = build_submission(task, specimen, tmp_path / "submission")
    assert (submission / "conftest.py").exists()
    assert not (submission / "specimen.toml").exists()

    clean = build_clean_room(task, submission, tmp_path / "clean")
    assert not (clean / "conftest.py").exists()
    assert (clean / "hidden" / "test_hidden.py").exists()
    original = (task.workspace / "tests" / "test_visible.py").read_text()
    assert (clean / "tests" / "test_visible.py").read_text() == original
