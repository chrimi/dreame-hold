"""Tests for helpers.py — pure logic, no Home Assistant dependency."""
from helpers import WEEKDAYS, decode_weekday_mask, encode_weekday_mask, soiling_percentages


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


def test_decode_real_daily_except_thursday_value():
    """Real observed value (leading 0 dropped in transmission)."""
    decoded = decode_weekday_mask(1110111)
    assert decoded["one_time"] is False
    assert decoded["monday"] is True
    assert decoded["tuesday"] is True
    assert decoded["wednesday"] is True
    assert decoded["thursday"] is False
    assert decoded["friday"] is True
    assert decoded["saturday"] is True
    assert decoded["sunday"] is True


def test_decode_real_repeat_off_value():
    decoded = decode_weekday_mask(10000000)
    assert decoded["one_time"] is True
    assert all(decoded[day] is False for day in WEEKDAYS)


def test_encode_matches_real_daily_except_thursday_value():
    days = {day: True for day in WEEKDAYS}
    days["thursday"] = False
    assert encode_weekday_mask(days, one_time=False) == 1110111


def test_encode_matches_real_repeat_off_value():
    assert encode_weekday_mask({}, one_time=True) == 10000000


def test_encode_decode_round_trip():
    for one_time in (True, False):
        days = {day: (i % 2 == 0) for i, day in enumerate(WEEKDAYS)}
        encoded = encode_weekday_mask(days, one_time=one_time)
        decoded = decode_weekday_mask(encoded)
        assert decoded["one_time"] == one_time
        for day in WEEKDAYS:
            assert decoded[day] == days[day]


def test_decode_missing_days_default_to_disabled():
    assert encode_weekday_mask({"monday": True}) == encode_weekday_mask(
        {"monday": True, "tuesday": False, "wednesday": False}
    )
