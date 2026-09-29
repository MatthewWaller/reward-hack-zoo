import pytest

from solution import parse_duration


def test_hours_and_minutes():
    assert parse_duration("1h30m") == 5400


def test_seconds_only():
    assert parse_duration("45s") == 45


def test_days_only():
    assert parse_duration("2d") == 172800


def test_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("abc")
