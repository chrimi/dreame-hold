"""Data update coordinator for Dreame Hold."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Callable

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
        self._property_locks: dict[tuple[int, int], asyncio.Lock] = {}

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

    async def async_update_property_atomic(
        self, prop: tuple[int, int], mutate: Callable[[Any], Any]
    ) -> None:
        """Atomically read-modify-write a single property.

        Used for PROP_SCHEDULED_DRYING_WEEKDAYS, which multiple entities
        (7 weekday switches plus the start-time entity's mask-repair step)
        all read-modify-write. `mutate` is a plain function: current raw
        value -> new raw value to write (return the input unchanged to
        skip the write entirely, e.g. when no change is needed).

        Fixes a real problem found via live testing: the original version
        of this pattern re-fetched a *fresh* value from the device before
        every single write, specifically to avoid two near-simultaneous
        toggles both computing their new mask from the same stale base
        (whichever wrote last would silently undo the other's change).
        That worked, but doubled network calls per toggle - with 7 quick
        toggles (each already serialized by DreameCloudDevice's internal
        send lock to one in-flight command at a time, ~0.6s/call), the
        last of the 7 took over 8 seconds to complete, comfortably past
        Home Assistant's frontend action timeout - producing exactly the
        "connection lost" errors reported live.

        This version removes the redundant read: an `asyncio.Lock` per
        property makes the whole read-decide-write sequence one atomic
        section (not just the individual network call, like
        DreameCloudDevice._send_lock already does), so a queued-up second
        toggle sees the *first toggle's own write* as its base the moment
        it acquires the lock - no network round trip needed to learn that.
        A device read only happens when there's no cached value yet at
        all (e.g. right after startup, before the coordinator's first
        poll) - self.data is otherwise kept authoritative for this
        property by writing our own result back into it here, and gets
        reconciled against the real device again on the next regular
        poll regardless.
        """
        siid, piid = prop
        lock = self._property_locks.setdefault(prop, asyncio.Lock())
        async with lock:
            if self.data and prop in self.data:
                current = self.data[prop]
            else:
                fresh = await self.hass.async_add_executor_job(
                    self.device.get_properties, [{"siid": siid, "piid": piid}]
                )
                current = 0
                if fresh:
                    match = next(
                        (r for r in fresh if r.get("siid") == siid and r.get("piid") == piid), None
                    )
                    if match and match.get("code") == 0:
                        current = match.get("value") or 0

            new_value = mutate(current)
            if new_value == current:
                return

            await self.hass.async_add_executor_job(self.device.set_property, siid, piid, new_value)
            if self.data is not None:
                self.data[prop] = new_value
