"""Data update coordinator for Dreame Hold."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_COUNTRY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ACCOUNT_TYPE,
    CONF_DEVICE_ID,
    CONF_MODEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    POLLED_PROPERTIES,
)
from .dreame_cloud.cloud_device import DreameCloudDevice


class DreameHoldDataUpdateCoordinator(DataUpdateCoordinator[dict[tuple[int, int], Any]]):
    """Polls the device's cloud properties on a fixed interval.

    The underlying DreameCloudDevice is a plain synchronous client (requests
    + a background MQTT thread for its own bookkeeping), so every call into
    it from here goes through the executor.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.entry = entry
        self.model: str | None = entry.data.get(CONF_MODEL)
        self.device = DreameCloudDevice(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            country=entry.data[CONF_COUNTRY],
            account_type=entry.data[CONF_ACCOUNT_TYPE],
            device_id=entry.data[CONF_DEVICE_ID],
        )

    async def _async_update_data(self) -> dict[tuple[int, int], Any]:
        try:
            connected = await self.hass.async_add_executor_job(
                self.device._initialize_mqtt_connection_state
            )
            if not connected:
                raise UpdateFailed("Could not connect to the Dreame cloud (login or device lookup failed)")

            self.model = self.device._model or self.model

            params = [{"siid": s, "piid": p} for s, p in POLLED_PROPERTIES]
            result = await self.hass.async_add_executor_job(self.device.get_properties, params)
        except Exception as ex:  # noqa: BLE001 - surfaced to HA as UpdateFailed below
            if "401" in str(ex) or "Token Expired" in str(ex):
                raise ConfigEntryAuthFailed from ex
            raise UpdateFailed(f"Error communicating with device: {ex}") from ex

        if not isinstance(result, list):
            raise UpdateFailed(f"Unexpected response from device: {result!r}")

        data: dict[tuple[int, int], Any] = {}
        for item in result:
            if item.get("code") == 0:
                data[(item["siid"], item["piid"])] = item.get("value")
        return data
