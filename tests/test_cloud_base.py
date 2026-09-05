"""Tests for DreameCloudBase — mocks the HTTP layer, no real network calls.

Field/header names used in the fixtures below (access_token, region, ...)
come from decoding the real DREAME_STRINGS blob (see NOTICE.md) — not
guessed, so these tests exercise the actual parsing logic against
realistic payloads.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from dreame_cloud.cloud_base import DreameCloudBase


def make_base(account_type: str = "dreame") -> DreameCloudBase:
    return DreameCloudBase(username="user@example.com", password="secret", country="eu", account_type=account_type)


def _fake_response(status_code: int, payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = json.dumps(payload)
    return resp


LOGIN_PAYLOAD = {
    "access_token": "tok123",
    "refresh_token": "refresh123",
    "expires_in": 3600,
    "region": "eu",
    "uid": "u1",
}


def test_invalid_account_type_raises():
    with pytest.raises(ValueError):
        DreameCloudBase("u", "p", "eu", "bogus")


def test_mova_account_type_also_valid():
    base = make_base("mova")
    assert base.get_api_url()  # decodes without error


def test_get_api_url():
    base = make_base()
    assert base.get_api_url() == "https://eu.iot.dreame.tech:13267"


def test_not_connected_initially():
    assert make_base().connected is False


def test_connect_success_sets_connected_and_key():
    base = make_base()
    with patch("requests.Session.post", return_value=_fake_response(200, LOGIN_PAYLOAD)):
        assert base.connect() is True
    assert base.connected is True
    assert base._key == "tok123"
    assert base._secondary_key == "refresh123"


def test_connect_failure_bad_status_stays_disconnected():
    base = make_base()
    with patch("requests.Session.post", return_value=_fake_response(401, {"error_description": "invalid_login"})):
        assert base.connect() is False
    assert base.connected is False


def test_connect_timeout_returns_false():
    base = make_base()
    with patch("requests.Session.post", side_effect=requests.exceptions.Timeout()):
        assert base.connect() is False
    assert base.connected is False


def test_get_devices_requires_connection_first():
    base = make_base()
    with pytest.raises(ConnectionError):
        base.get_devices()


def test_get_devices_returns_data_on_success():
    base = make_base()
    devices_payload = {
        "code": 0,
        "data": {"page": {"records": [{"did": "1", "model": "dreame.hold.w2306f"}]}},
    }
    with patch(
        "requests.Session.post",
        side_effect=[_fake_response(200, LOGIN_PAYLOAD), _fake_response(200, devices_payload)],
    ):
        assert base.connect() is True
        devices = base.get_devices()
    assert devices == devices_payload["data"]


def test_get_devices_returns_none_on_error_code():
    base = make_base()
    error_payload = {"code": 1, "msg": "something failed"}
    with patch(
        "requests.Session.post",
        side_effect=[_fake_response(200, LOGIN_PAYLOAD), _fake_response(200, error_payload)],
    ):
        base.connect()
        assert base.get_devices() is None


def test_disconnect_resets_connected_state():
    base = make_base()
    with patch("requests.Session.post", return_value=_fake_response(200, LOGIN_PAYLOAD)):
        base.connect()
    assert base.connected is True
    base.disconnect()
    assert base.connected is False
