"""The fixtures are the harness's regression suite: each must be caught exactly as labelled."""

import pytest

from zoo.tasks import all_tasks

SPECIMENS = [(t.name, s) for t in all_tasks() for s in t.specimens()]
IDS = [f"{task}/{s.name}" for task, s in SPECIMENS]


def test_there_is_at_least_one_honest_and_one_hack_per_task():
    for task in all_tasks():
        kinds = {s.kind for s in task.specimens()}
        assert kinds == {"honest", "hack"}, task.name


def test_every_species_has_a_specimen():
    from zoo.detectors import SPECIES

    covered = {species for _, s in SPECIMENS for species in s.species}
    assert covered == set(SPECIES)


@pytest.mark.parametrize(("task", "specimen"), SPECIMENS, ids=IDS)
def test_detector_matches_fixture_label(specimen_rows, task, specimen):
    row = specimen_rows[f"{task}/{specimen.name}"]
    assert row.result.flagged() == set(specimen.species)
    if specimen.kind == "honest":
        assert row.result.verdict == "clean"
        assert all(suite.green for suite in row.result.suites.values())
    else:
        assert row.result.verdict == "hack"


@pytest.mark.parametrize(("task", "specimen"), SPECIMENS, ids=IDS)
def test_hidden_tests_separate_honest_from_hacks(specimen_rows, task, specimen):
    hidden = specimen_rows[f"{task}/{specimen.name}"].result.suites["hidden"]
    assert hidden.green == (specimen.kind == "honest")


@pytest.mark.parametrize(("task", "specimen"), SPECIMENS, ids=IDS)
def test_every_fixture_says_it_is_hand_written(task, specimen):
    marker = "ILLUSTRATIVE FIXTURE"
    for path in specimen.path.rglob("*.py"):
        assert marker in path.read_text(), path
