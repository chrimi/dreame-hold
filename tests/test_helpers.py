"""Tests for helpers.py — pure logic, no Home Assistant dependency."""
from helpers import soiling_percentages


def test_matches_real_observed_run():
    """307/54/3 seconds is a real captured run (see FINDINGS.md); the app
    displayed 84%/14%/2% for it."""
    assert soiling_percentages(307, 54, 3) == (84, 14, 2)


def test_no_data_returns_none():
    assert soiling_percentages(0, 0, 0) is None


def test_all_one_category():
    assert soiling_percentages(100, 0, 0) == (100, 0, 0)
    assert soiling_percentages(0, 100, 0) == (0, 100, 0)
    assert soiling_percentages(0, 0, 100) == (0, 0, 100)


def test_always_sums_to_100():
    for light, moderate, heavy in [(1, 1, 1), (7, 3, 1), (500, 250, 1), (2, 2, 2)]:
        result = soiling_percentages(light, moderate, heavy)
        assert sum(result) == 100
