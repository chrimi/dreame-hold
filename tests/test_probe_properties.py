"""Tests for dev/probe_properties.py's pure siid-spec parser."""
from probe_properties import parse_int_spec


def test_single_value():
    assert parse_int_spec("5") == [5]


def test_range():
    assert parse_int_spec("1-4") == [1, 2, 3, 4]


def test_mixed_values_and_ranges():
    assert parse_int_spec("1-8,16,17,19") == [1, 2, 3, 4, 5, 6, 7, 8, 16, 17, 19]


def test_overlapping_ranges_deduped_and_sorted():
    assert parse_int_spec("1-3,2-4") == [1, 2, 3, 4]


def test_whitespace_tolerant():
    assert parse_int_spec(" 1-3 , 5 ") == [1, 2, 3, 5]


def test_trailing_comma_ignored():
    assert parse_int_spec("1,2,") == [1, 2]
