"""Tests for helpers.py — pure logic, no Home Assistant dependency."""
from helpers import (
    WEEKDAYS,
    decode_weekday_mask,
    derive_one_time_flag,
    encode_weekday_mask,
    soiling_percentages,
)


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


def test_wire_order_is_reversed_not_monday_first():
    """Regression test for a confirmed live bug: the "daily except
    Thursday" sample used to originally "confirm" a Monday-first digit
    order is a palindrome (1110111 reads the same forwards/backwards), so
    it couldn't actually distinguish direction - Thursday sits at digit
    position 4 either way, being the exact middle of the week.

    A real asymmetric single-day write exposed the truth: writing
    "saturday" alone (under the old, buggy Monday-first order) produced
    wire value 10 - and the Dreame app displayed that schedule as
    *Tuesday*, not Saturday. So the true digit order is Sunday, Saturday,
    Friday, Thursday, Wednesday, Tuesday, Monday - the reverse of
    WEEKDAYS. This test pins that down explicitly: "saturday" alone must
    NOT reproduce wire value 10 (the old bug), and "tuesday" alone must
    (matching what the app actually showed for that raw value).
    """
    saturday_only = {day: False for day in WEEKDAYS}
    saturday_only["saturday"] = True
    assert encode_weekday_mask(saturday_only, one_time=False) != 10

    tuesday_only = {day: False for day in WEEKDAYS}
    tuesday_only["tuesday"] = True
    assert encode_weekday_mask(tuesday_only, one_time=False) == 10
    assert decode_weekday_mask(10) == {
        "one_time": False,
        "monday": False,
        "tuesday": True,
        "wednesday": False,
        "thursday": False,
        "friday": False,
        "saturday": False,
        "sunday": False,
    }


def test_derive_one_time_flag_true_when_no_days_selected():
    assert derive_one_time_flag({}) is True
    assert derive_one_time_flag({day: False for day in WEEKDAYS}) is True


def test_derive_one_time_flag_false_when_any_day_selected():
    assert derive_one_time_flag({"monday": True}) is False
    assert derive_one_time_flag({day: True for day in WEEKDAYS}) is False


def test_setting_time_with_no_days_produces_valid_one_time_mask():
    """Regression test for the reported bug: a time-only schedule (no
    weekday ever touched) must encode as "10000000" (one-time, no
    repeat) — not "0" (repeats on no days), which the app can't display."""
    days = {day: False for day in WEEKDAYS}
    encoded = encode_weekday_mask(days, one_time=derive_one_time_flag(days))
    assert encoded == 10000000
