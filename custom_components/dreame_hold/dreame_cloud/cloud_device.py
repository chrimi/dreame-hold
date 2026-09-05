"""Device-level Dreame/MOVA cloud client (login + MQTT + get/set properties).

Adapted from antondaubert/dreame-mower's dreame/cloud/cloud_device.py (MIT
license), which itself descends from Tasshack/dreame-vacuum's protocol.py.
Renamed from DreameMowerCloudDevice -> DreameCloudDevice; the only functional
change is that ActionIdentifier (originally imported from the mower's
homeassistant-coupled const.py) is redefined locally so this module has zero
Home Assistant dependency. See NOTICE at the repo root for full attribution.
"""

import logging
import json
import random
import ssl
from threading import Lock, Timer
from paho.mqtt import client as mqtt_client
from typing import Any, NamedTuple, Optional, Callable, Dict

from .cloud_base import DreameCloudBase

_LOGGER = logging.getLogger(__name__)

RECONNECT_DELAY_SECONDS = 10
MQTT_KEEPALIVE_SECONDS = 50


class ActionIdentifier(NamedTuple):
    """siid/aiid pair identifying a device action (e.g. trigger self-clean)."""
    siid: int
    aiid: int
    name: str

    def matches(self, siid: int, aiid: int) -> bool:
        """Check if given siid and aiid match this action identifier."""
        return self.siid == siid and self.aiid == aiid


class DreameCloudDevice:
    _mqtt_message_callback: Optional[Callable[[Dict[str, Any]], None]]
    _mqtt_connected_callback: Optional[Callable[[], None]]
    _mqtt_disconnected_callback: Optional[Callable[[], None]]

    def __init__(
        self,
        username: str,
        password: str,
        country: str,
        account_type: str,
        device_id: str,
    ) -> None:
        self._cloud_base = DreameCloudBase(username, password, country, account_type)

        self._device_id = device_id
        self._mqtt_reconnect_timer: Optional[Timer] = None
        self._host: Optional[str] = None
        self._model: Optional[str] = None
        self._uid: Optional[str] = None

        self._mqtt_client_connected = False
        self._mqtt_client_connecting = False
        self._mqtt_client: Optional[mqtt_client.Client] = None
        self._mqtt_message_callback = None
        self._mqtt_connected_callback = None
        self._mqtt_disconnected_callback = None
        self._mqtt_client_key: Optional[str] = None
        self._device_reachable = True
        self._send_lock = Lock()

    @property
    def device_id(self) -> str:
        return self._device_id

    @property
    def object_name(self) -> str:
        assert self._model is not None, "Model must be set before accessing object_name"
        assert self._uid is not None, "UID must be set before accessing object_name"
        return f"{self._model}/{self._uid}/{self._device_id}/0"

    @property
    def connected(self) -> bool:
        return self._cloud_base.connected and self._mqtt_client_connected

    @property
    def device_reachable(self) -> bool:
        return self._device_reachable

    def disconnect(self):
        if self._mqtt_client is not None:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
            self._mqtt_client = None
            self._mqtt_client_connected = False
            self._mqtt_client_connecting = False
        self._mqtt_message_callback = None
        self._mqtt_connected_callback = None
        self._mqtt_disconnected_callback = None

        self._cloud_base.disconnect()

    def _mqtt_reconnect_timer_cancel(self):
        if self._mqtt_reconnect_timer is not None:
            self._mqtt_reconnect_timer.cancel()
            del self._mqtt_reconnect_timer
            self._mqtt_reconnect_timer = None

    def _mqtt_reconnect_timer_task(self):
        self._mqtt_reconnect_timer_cancel()
        if not self._mqtt_client:
            return
        if self._mqtt_client_connected:
            return
        if not self._mqtt_client_connecting:
            self._mqtt_client_connecting = True
        try:
            _LOGGER.debug("MQTT reconnect timer firing; attempting reconnect...")
            self._mqtt_client.reconnect()
        except Exception as ex:
            _LOGGER.warning("MQTT reconnect attempt failed: %s", ex, exc_info=True)
            self._mqtt_reconnect_timer = Timer(RECONNECT_DELAY_SECONDS, self._mqtt_reconnect_timer_task)
            self._mqtt_reconnect_timer.start()

    def _refresh_mqtt_credentials(self) -> bool:
        if self._mqtt_client_key != self._cloud_base._key and self._mqtt_client is not None:
            self._mqtt_client_key = self._cloud_base._key
            self._mqtt_client.username_pw_set(self._cloud_base._uuid, self._mqtt_client_key)
            return True
        return False

    @staticmethod
    def _on_mqtt_client_connect(client, self, flags, rc):
        self._mqtt_client_connecting = False
        self._mqtt_reconnect_timer_cancel()
        if rc == 0:
            if not self._mqtt_client_connected:
                self._mqtt_client_connected = True
            client.subscribe(
                f"/{self._cloud_base._api_strings[7]}/{self._device_id}/{self._uid}/{self._model}/{self._cloud_base._country}/")
            if self._mqtt_connected_callback:
                try:
                    self._mqtt_connected_callback()
                except Exception as ex:
                    _LOGGER.error("Error in MQTT connected callback: %s", ex, exc_info=True)
        else:
            _LOGGER.warning("MQTT client connection failed: %s", rc)
            if not self._refresh_mqtt_credentials():
                self._mqtt_client_connected = False

    @staticmethod
    def _on_mqtt_client_disconnect(client, self, rc):
        was_connected = self._mqtt_client_connected
        self._mqtt_client_connected = False

        if was_connected and self._mqtt_disconnected_callback:
            try:
                self._mqtt_disconnected_callback()
            except Exception as ex:
                _LOGGER.error("Error in MQTT disconnected callback: %s", ex, exc_info=True)

        if rc == 0:
            return

        _LOGGER.warning("Unexpected MQTT disconnect rc=%s", rc)

        if not self._refresh_mqtt_credentials():
            if rc == 5 and self._cloud_base._key_expire:
                self._cloud_base.connect()
                self._refresh_mqtt_credentials()

        if not self._mqtt_client:
            return

        if not self._mqtt_client_connecting:
            self._mqtt_client_connecting = True
            try:
                _LOGGER.info("Attempting immediate MQTT reconnect...")
                client.reconnect()
            except Exception as ex:
                _LOGGER.warning("Immediate reconnect failed: %s", ex, exc_info=True)

        if not self._mqtt_client_connected:
            self._mqtt_reconnect_timer_cancel()
            self._mqtt_reconnect_timer = Timer(RECONNECT_DELAY_SECONDS, self._mqtt_reconnect_timer_task)
            self._mqtt_reconnect_timer.start()

    @staticmethod
    def _on_mqtt_client_message(client, self, message):
        self._device_reachable = True

        if self._mqtt_message_callback:
            try:
                payload = message.payload.decode("utf-8")
                response = json.loads(payload)
                if "data" in response and response["data"]:
                    self._mqtt_message_callback(response["data"])
            except json.JSONDecodeError as ex:
                _LOGGER.error("MQTT message JSON decode error: %s payload=%r", ex, message.payload, exc_info=True)
            except Exception as ex:
                _LOGGER.error("Unhandled error processing MQTT message: %s", ex, exc_info=True)

    @staticmethod
    def get_random_agent_id() -> str:
        letters = "ABCDEF"
        result_str = "".join(random.choice(letters) for i in range(13))
        return result_str

    def connect(
        self,
        message_callback: Callable[[Dict[str, Any]], None],
        connected_callback: Callable[[], None],
        disconnected_callback: Callable[[], None],
    ) -> bool:
        """Connect to cloud and establish MQTT for real-time updates."""
        if message_callback is None or connected_callback is None or disconnected_callback is None:
            raise ValueError("connect requires message_callback, connected_callback, and disconnected_callback")

        if self.connected:
            self._mqtt_message_callback = message_callback
            self._mqtt_connected_callback = connected_callback
            self._mqtt_disconnected_callback = disconnected_callback
            return True

        if not self._initialize_mqtt_connection_state():
            return False

        self._mqtt_message_callback = message_callback
        self._mqtt_connected_callback = connected_callback
        self._mqtt_disconnected_callback = disconnected_callback

        if self._mqtt_client:
            self._refresh_mqtt_credentials()
            if not self._mqtt_client_connected and not self._mqtt_client_connecting:
                try:
                    self._mqtt_client_connecting = True
                    self._mqtt_client.reconnect()
                except Exception as ex:
                    _LOGGER.warning("connect: immediate MQTT reconnect failed: %s", ex, exc_info=True)
                    self._mqtt_reconnect_timer_cancel()
                    self._mqtt_reconnect_timer = Timer(RECONNECT_DELAY_SECONDS, self._mqtt_reconnect_timer_task)
                    self._mqtt_reconnect_timer.start()
            return True

        try:
            assert self._host is not None, "Host must be set after initialization"
            host_str = self._host.strip()
            parts = host_str.split(":") if host_str else []
            host_name = parts[0] if parts else ""
            if not host_name:
                _LOGGER.error("connect: Invalid host '%s' (empty host name)", host_str)
                return False
            if len(parts) < 2:
                _LOGGER.error("connect: Missing port in host '%s'", host_str)
                return False
            try:
                port = int(parts[1])
            except ValueError:
                _LOGGER.error("connect: Non-integer port in host '%s'", host_str)
                return False
            self._mqtt_client = mqtt_client.Client(
                mqtt_client.CallbackAPIVersion.VERSION1,  # type: ignore[attr-defined]
                f"{self._cloud_base._api_strings[53]}{self._uid}{self._cloud_base._api_strings[54]}{DreameCloudDevice.get_random_agent_id()}{self._cloud_base._api_strings[54]}{host_name}",
                clean_session=True,
                userdata=self,
            )
            self._mqtt_client.on_connect = DreameCloudDevice._on_mqtt_client_connect
            self._mqtt_client.on_disconnect = DreameCloudDevice._on_mqtt_client_disconnect
            self._mqtt_client.on_message = DreameCloudDevice._on_mqtt_client_message
            self._mqtt_client.reconnect_delay_set(1, 15)
            self._mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
            self._mqtt_client.tls_insecure_set(True)
            self._refresh_mqtt_credentials()
            self._mqtt_client.connect(host_name, port, MQTT_KEEPALIVE_SECONDS)
            self._mqtt_client.loop_start()
            return True
        except Exception as e:
            _LOGGER.error("MQTT client connection failed. error: %s", e)
            return False

    def _initialize_mqtt_connection_state(self) -> bool:
        """Fetch model/uid/host needed for both MQTT and REST relay calls."""
        if not self._cloud_base.connected:
            if not self._cloud_base.connect():
                _LOGGER.warning("_initialize_mqtt_connection_state: Unable to connect. Connection failed.")
                return False

        response = self._cloud_base._api_call(
            f"{self._cloud_base._api_strings[23]}/{self._cloud_base._api_strings[24]}/{self._cloud_base._api_strings[27]}/{self._cloud_base._api_strings[29]}",
            {"did": self._device_id},
        )
        if not response or response.get("code") != 0 or "data" not in response:
            _LOGGER.warning(
                "_initialize_mqtt_connection_state: Failed to fetch base device info for did=%s", self._device_id
            )
            return False

        data = response["data"]
        if not data:
            _LOGGER.warning(
                "_initialize_mqtt_connection_state: Base device info is empty for did=%s", self._device_id
            )
            return False
        try:
            self._uid = data[self._cloud_base._api_strings[8]]
            self._device_id = str(data["did"])
            self._model = data[self._cloud_base._api_strings[35]]
            self._host = data[self._cloud_base._api_strings[9]]
        except KeyError as ex:
            _LOGGER.warning(
                "_initialize_mqtt_connection_state: Base device info missing required key: %s", ex, exc_info=True
            )
            return False
        return True

    def get_device_info(self) -> Optional[dict]:
        if not self._cloud_base.connected:
            _LOGGER.info("get_device_info: Not connected. Attempting to connect.")
            self._cloud_base.connect()

        if not self._cloud_base.connected:
            _LOGGER.warning("get_device_info: Unable to connect. Connection failed.")
            return None

        devices = self._cloud_base.get_devices()
        if devices is not None:
            found = list(
                filter(
                    lambda d: str(d["did"]) == self._device_id,
                    devices[self._cloud_base._api_strings[34]][self._cloud_base._api_strings[36]],
                )
            )
            if len(found) > 1:
                _LOGGER.warning("get_device_info: Found %d devices with ID %s, using first one", len(found), self._device_id)
            if len(found) > 0:
                return found[0]

        _LOGGER.warning("get_device_info: Device with ID %s not found in devices list", self._device_id)
        return None

    def send(self, method: str, parameters: Any, retry_count: int = 2) -> Any:
        """Send one command to the device; only one may be in flight at a time."""
        with self._send_lock:
            return self._send(method, parameters, retry_count)

    def _send(self, method: str, parameters: Any, retry_count: int = 2) -> Any:
        host = ""
        if self._host and len(self._host):
            host = f"-{self._host.split('.')[0]}"

        api_response = self._cloud_base._api_call(
            f"{self._cloud_base._api_strings[37]}{host}/{self._cloud_base._api_strings[27]}/{self._cloud_base._api_strings[38]}",
            {
                "did": self._device_id,
                "id": self._cloud_base._id,
                "data": {
                    "did": self._device_id,
                    "id": self._cloud_base._id,
                    "method": method,
                    "params": parameters,
                },
            },
            retry_count,
        )
        self._cloud_base._id = self._cloud_base._id + 1

        if api_response and api_response.get("code") == 80001:
            self._device_reachable = False
            _LOGGER.warning(
                "DreameCloudDevice.send device offline (80001): %s", api_response)
            raise TimeoutError(
                f"Device offline: {api_response.get('msg', 'Device may be offline and command sending timed out')}")

        if api_response and api_response.get("code", 0) != 0:
            code = api_response.get("code")
            msg = api_response.get("msg", f"Unknown error code: {code}")
            _LOGGER.warning(
                "DreameCloudDevice.send failed with code %s: %s", code, msg)
            raise RuntimeError(f"Cloud API error {code}: {msg}")

        if api_response is None:
            _LOGGER.warning("DreameCloudDevice.send received None response")
            raise ConnectionError("No response from cloud API")

        self._device_reachable = True

        if "data" not in api_response:
            _LOGGER.debug("DreameCloudDevice.send response has no 'data' field: %s", api_response)
            return None

        if "result" not in api_response["data"]:
            _LOGGER.debug("DreameCloudDevice.send response has no 'result' in data: %s", api_response)
            return None

        return api_response["data"]["result"]

    def get_batch_device_datas(self, props) -> Any:
        if not self._cloud_base.connected:
            _LOGGER.info("get_batch_device_datas: Not connected. Attempting to connect.")
            self._cloud_base.connect()

        if not self._cloud_base.connected:
            raise ConnectionError("get_batch_device_datas: Unable to connect. Connection failed.")

        api_response = self._cloud_base._api_call(
            f"{self._cloud_base._api_strings[23]}/{self._cloud_base._api_strings[26]}/{self._cloud_base._api_strings[44]}",
            {"did": self._device_id, self._cloud_base._api_strings[35]: props},
        )
        if api_response is None or "data" not in api_response:
            return None
        return api_response["data"]

    def check_device_version(self, lang: Optional[str] = None, lang_in_query: bool = False) -> Any:
        """Query the cloud OTA service for firmware update availability.

        Without `lang`, the response's `description` field is an error
        blob ("缺少必要的请求参数: lang" - "missing required parameter:
        lang") instead of release notes text; this appears to be a
        pre-existing quirk in the upstream cloud_device.py this was
        adapted from too, not something introduced here. The parameter
        name is confirmed by that error message; the expected value
        format (e.g. "en", "en_US", "de") is not confirmed - pass one
        and see what comes back.

        Neither placement has been observed to work: passing `lang` in
        the JSON body (the default) and passing it as a URL query
        parameter (`lang_in_query=True`, `?lang=...`) both still returned
        the same "missing lang" error blob in testing (tried with "en"
        and "en_US"). Kept as a documented, unresolved limitation rather
        than pursued further — likely a pre-existing server-side quirk in
        this cloud endpoint, not something fixable from the client side
        without more information about what it actually expects.
        """
        if not self._cloud_base.connected:
            _LOGGER.info("check_device_version: Not connected. Attempting to connect.")
            self._cloud_base.connect()

        if not self._cloud_base.connected:
            raise ConnectionError("check_device_version: Unable to connect. Connection failed.")

        params = {"did": self._device_id}
        path = f"{self._cloud_base._api_strings[23]}/{self._cloud_base._api_strings[24]}/checkDeviceVersion"
        if lang:
            if lang_in_query:
                path = f"{path}?lang={lang}"
            else:
                params["lang"] = lang

        api_response = self._cloud_base._api_call(path, params)
        if api_response is None or "data" not in api_response:
            return None
        return api_response["data"]

    def set_batch_device_datas(self, props) -> Any:
        if not self._cloud_base.connected:
            raise ConnectionError("set_batch_device_datas: Not connected. Call login() first.")

        api_response = self._cloud_base._api_call(
            f"{self._cloud_base._api_strings[23]}/{self._cloud_base._api_strings[26]}/{self._cloud_base._api_strings[45]}",
            {"did": self._device_id, self._cloud_base._api_strings[35]: props},
        )
        if api_response is None or "result" not in api_response:
            return None
        return api_response["result"]

    def get_properties(self, parameters: Any = None, retry_count: int = 1) -> Any:
        return self.send("get_properties", parameters=parameters, retry_count=retry_count)

    def set_property(self, siid: int, piid: int, value: Any = None, retry_count: int = 2) -> Any:
        return self.set_properties([
            {
                "did": str(self.device_id),
                "siid": siid,
                "piid": piid,
                "value": value,
            }
        ], retry_count=retry_count)

    def set_properties(self, parameters: Any = None, retry_count: int = 2) -> Any:
        return self.send("set_properties", parameters=parameters, retry_count=retry_count)

    def action(self, siid: int, aiid: int, parameters=None, retry_count: int = 2) -> Any:
        if parameters is None:
            parameters = []

        return self.send("action", parameters={
            "did": str(self.device_id),
            "siid": siid,
            "aiid": aiid,
            "in": parameters,
        }, retry_count=retry_count)

    def execute_action(self, action: ActionIdentifier) -> bool:
        """Execute a device action with consistent error handling and logging."""
        try:
            self.action(action.siid, action.aiid)
            return True
        except Exception as ex:
            _LOGGER.error("%s action failed: %s", action.name, ex)
            return False

    def get_file_download_url(self, filename: str) -> Optional[str]:
        """Return a signed download URL for the given device file path."""
        api = self._cloud_base._api_strings
        url = f"{api[23]}/{api[39]}/{api[55]}"
        params = {
            "did": self._device_id,
            api[35]: self._model,
            api[40]: filename,
            api[21]: self._cloud_base._country,
        }
        resp = self._cloud_base._api_call(url, params, raise_on_error=True)
        if resp["code"] != 0:
            return None
        data = resp["data"]
        if isinstance(data, str) and data.startswith("http"):
            return data
        return None
