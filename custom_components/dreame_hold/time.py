"""Time platform for Dreame Hold."""
from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PROP_AUTO_DRYING_DISABLED,
    PROP_SCHEDULED_DRYING_TIME,
    PROP_SCHEDULED_DRYING_WEEKDAYS,
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity
from .helpers import WEEKDAYS, decode_weekday_mask, derive_one_time_flag, encode_weekday_mask

SCHEDULED_DRYING_TIME_DESCRIPTION = TimeEntityDescription(
    key="scheduled_drying_time",
    name="Scheduled drying start time",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DreameHoldScheduledDryingTime(coordinator)])


class DreameHoldScheduledDryingTime(DreameHoldEntity, TimeEntity):
    """Start time of the scheduled roller-brush-drying cycle.

    Write path confirmed working live, including a 5-second read-back
    (see FINDINGS.md's "Live write-path testing" section).

    Only available while "Automatic roller brush drying" is on - turning
    that off resets the schedule to 0 on the device (confirmed).
    """

    entity_description = SCHEDULED_DRYING_TIME_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self._property(PROP_AUTO_DRYING_DISABLED) == 0

    @property
    def native_value(self) -> dt_time | None:
        seconds = self._property(PROP_SCHEDULED_DRYING_TIME)
        if not seconds:
            return None
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return dt_time(hour=hours, minute=minutes, second=secs)

    async def async_set_value(self, value: dt_time) -> None:
        seconds = value.hour * 3600 + value.minute * 60 + value.second
        time_siid, time_piid = PROP_SCHEDULED_DRYING_TIME
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_property, time_siid, time_piid, seconds
            )
            await self._ensure_valid_weekday_mask()
        except Exception as ex:
            raise HomeAssistantError(f"Failed to set scheduled drying time: {ex}") from ex
        await self.coordinator.async_request_refresh()

    async def _ensure_valid_weekday_mask(self) -> None:
        """Fix confirmed bug: setting a time without ever touching a
        weekday switch left PROP_SCHEDULED_DRYING_WEEKDAYS at its all-zero
        default ("repeats on no days" — invalid, the app couldn't display
        it at all) instead of a valid one-time schedule ("10000000").

        Fetches a fresh mask (not the coordinator's cached one) and
        corrects only its one-time flag via derive_one_time_flag, leaving
        any already-selected days untouched — so setting the time after
        picking days doesn't turn a repeating schedule into a one-time one.
        """
        wd_siid, wd_piid = PROP_SCHEDULED_DRYING_WEEKDAYS
        fresh = await self.hass.async_add_executor_job(
            self.coordinator.device.get_properties, [{"siid": wd_siid, "piid": wd_piid}]
        )
        current = 0
        if fresh:
            match = next((r for r in fresh if r.get("siid") == wd_siid and r.get("piid") == wd_piid), None)
            if match and match.get("code") == 0:
                current = match.get("value") or 0

        decoded = decode_weekday_mask(current)
        days = {day: decoded[day] for day in WEEKDAYS}
        correct_one_time = derive_one_time_flag(days)
        if decoded["one_time"] == correct_one_time:
            return  # already valid, no write needed

        new_mask = encode_weekday_mask(days, one_time=correct_one_time)
        await self.hass.async_add_executor_job(self.coordinator.device.set_property, wd_siid, wd_piid, new_mask)
