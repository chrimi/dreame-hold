"""Tests for DreameCloudDevice — mocks the _cloud_base layer, no real
network calls.

`API_STRINGS` is the real, decoded field-name table (see NOTICE.md /
test_cloud_base.py) — used wherever the code under test looks up a real
dict key by name (e.g. `data[api_strings[8]]`), so a plain unconfigured
MagicMock (which would return another MagicMock, not a string, from
`__getitem__`) won't silently break the lookup.
"""
from unittest.mock import MagicMock

import pytest

from dreame_cloud.cloud_base import DREAME_STRINGS, _decode_api_strings
from dreame_cloud.cloud_device import ActionIdentifier, DreameCloudDevice

API_STRINGS = _decode_api_strings(DREAME_STRINGS)


def make_device(device_id: str = "123") -> DreameCloudDevice:
    return DreameCloudDevice(
        username="user@example.com", password="secret", country="eu", account_type="dreame", device_id=device_id
    )


def test_action_identifier_matches():
    action = ActionIdentifier(siid=2, aiid=1, name="start")
    assert action.matches(2, 1) is True
    assert action.matches(2, 2) is False


def test_object_name_requires_model_and_uid():
    device = make_device()
    with pytest.raises(AssertionError):
        _ = device.object_name


def test_object_name_once_populated():
    device = make_device()
    device._model = "dreame.hold.w2306f"
    device._uid = "u1"
    assert device.object_name == "dreame.hold.w2306f/u1/123/0"


def test_initialize_mqtt_connection_state_success():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base.connected = True
    device._cloud_base._api_strings = API_STRINGS
    device._cloud_base._api_call.return_value = {
        "code": 0,
        "data": {"masterUid": "u1", "did": "123", "model": "dreame.hold.w2306f", "bindDomain": "host.example.com:8883"},
    }

    assert device._initialize_mqtt_connection_state() is True
    assert device._uid == "u1"
    assert device._device_id == "123"
    assert device._model == "dreame.hold.w2306f"
    assert device._host == "host.example.com:8883"


def test_initialize_mqtt_connection_state_connect_fails():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base.connected = False
    device._cloud_base.connect.return_value = False

    assert device._initialize_mqtt_connection_state() is False


def test_initialize_mqtt_connection_state_missing_key():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base.connected = True
    device._cloud_base._api_strings = API_STRINGS
    device._cloud_base._api_call.return_value = {"code": 0, "data": {"did": "123"}}  # missing masterUid etc.

    assert device._initialize_mqtt_connection_state() is False


def test_initialize_mqtt_connection_state_error_code():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base.connected = True
    device._cloud_base._api_strings = API_STRINGS
    device._cloud_base._api_call.return_value = {"code": 1, "msg": "failed"}

    assert device._initialize_mqtt_connection_state() is False


def test_send_device_offline_raises_timeout_error():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base._id = 1
    device._cloud_base._api_call.return_value = {"code": 80001, "msg": "device offline"}

    with pytest.raises(TimeoutError):
        device.send("get_properties", parameters=[])
    assert device.device_reachable is False


def test_send_error_code_raises_runtime_error():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base._id = 1
    device._cloud_base._api_call.return_value = {"code": 42, "msg": "bad request"}

    with pytest.raises(RuntimeError):
        device.send("get_properties", parameters=[])


def test_send_none_response_raises_connection_error():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base._id = 1
    device._cloud_base._api_call.return_value = None

    with pytest.raises(ConnectionError):
        device.send("get_properties", parameters=[])


def test_send_success_returns_result_and_marks_reachable():
    device = make_device()
    device._cloud_base = MagicMock()
    device._cloud_base._id = 1
    device._device_reachable = False
    device._cloud_base._api_call.return_value = {
        "code": 0,
        "data": {"result": [{"siid": 2, "piid": 1, "code": 0, "value": 7}]},
    }

    result = device.send("get_properties", parameters=[{"siid": 2, "piid": 1}])

    assert result == [{"siid": 2, "piid": 1, "code": 0, "value": 7}]
    assert device.device_reachable is True


def test_get_properties_delegates_to_send():
    device = make_device()
    device.send = MagicMock(return_value=[{"siid": 2, "piid": 1, "code": 0, "value": 7}])

    result = device.get_properties([{"siid": 2, "piid": 1}])

    device.send.assert_called_once_with(
        "get_properties", parameters=[{"siid": 2, "piid": 1}], retry_count=1
    )
    assert result == [{"siid": 2, "piid": 1, "code": 0, "value": 7}]


def test_set_property_wraps_into_set_properties():
    device = make_device()
    device.set_properties = MagicMock(return_value=None)

    device.set_property(2, 1, 5)

    device.set_properties.assert_called_once_with(
        [{"did": "123", "siid": 2, "piid": 1, "value": 5}], retry_count=2
    )


def test_action_sends_correct_payload():
    device = make_device()
    device.send = MagicMock(return_value=None)

    device.action(2, 3, parameters=["arg"])

    device.send.assert_called_once_with(
        "action", parameters={"did": "123", "siid": 2, "aiid": 3, "in": ["arg"]}, retry_count=2
    )


def test_execute_action_returns_false_on_failure():
    device = make_device()
    device.action = MagicMock(side_effect=RuntimeError("boom"))

    ok = device.execute_action(ActionIdentifier(siid=2, aiid=3, name="my_action"))

    assert ok is False


def test_execute_action_returns_true_on_success():
    device = make_device()
    device.action = MagicMock(return_value=None)

    ok = device.execute_action(ActionIdentifier(siid=2, aiid=3, name="my_action"))

    assert ok is True
