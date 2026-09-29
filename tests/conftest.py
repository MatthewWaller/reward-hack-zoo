import pytest

from zoo.report import check_all_specimens


@pytest.fixture(scope="session")
def specimen_rows():
    """Every specimen checked once per session; this is the slow part of the suite."""
    return {row.result.candidate: row for row in check_all_specimens()}
