"""Tests for helpers.extract_hold_devices — pure logic, no HA dependency.

The "page"/"records" shape used here is the confirmed real cloud response
shape (decoded from the obfuscated API string table, see NOTICE.md), not
a guess.
"""
from helpers import extract_hold_devices


def test_confirmed_shape_filters_to_hold_models():
    response = {
        "page": {
            "records": [
                {"did": "1", "model": "dreame.vacuum.r2228"},
                {"did": "2", "model": "dreame.hold.w2306f"},
                {"did": "3", "model": "mova.hold.h1000"},
            ]
        }
    }
    result = extract_hold_devices(response)
    assert {d["did"] for d in result} == {"2", "3"}


def test_no_hold_devices_returns_empty():
    response = {"page": {"records": [{"did": "1", "model": "dreame.vacuum.r2228"}]}}
    assert extract_hold_devices(response) == []


def test_not_a_dict_returns_empty():
    assert extract_hold_devices(None) == []
    assert extract_hold_devices([1, 2, 3]) == []


def test_fallback_generic_shape_still_finds_devices():
    """If the account/region ever returns a differently-nested shape."""
    response = {"data": {"list": [{"did": "9", "model": "dreame.hold.w2306f"}]}}
    result = extract_hold_devices(response)
    assert {d["did"] for d in result} == {"9"}


def test_missing_model_field_excluded_not_crashed():
    response = {"page": {"records": [{"did": "1"}]}}
    assert extract_hold_devices(response) == []
