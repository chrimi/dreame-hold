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

    Independent of "Automatic roller brush drying"
    (PROP_AUTO_DRYING_DISABLED) - confirmed live that toggling that
    switch doesn't affect this property either way (see that constant's
    docstring), so availability isn't gated on it. A value of 0 (shown
    here as no time set) is itself the device's own "no schedule"
    state - see "Scheduled drying: Enabled" in switch.py for a friendlier
    on/off toggle around that.

    Available only while that "Enabled" switch is on (PROP_SCHEDULED_DRYING_TIME
    != 0) - matches the same gating on the weekday switches in switch.py,
    fixing a reported bug where the time/weekday entities could be
    fiddled with while the schedule itself was off, visibly out of sync
    with "Enabled". Turn "Enabled" on first (it seeds a real time via
    the last-known or default schedule) to make this adjustable.
    """

    entity_description = SCHEDULED_DRYING_TIME_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return bool(self._property(PROP_SCHEDULED_DRYING_TIME))

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

        Goes through the coordinator's `async_update_property_atomic`
        (same as the weekday switches in switch.py) rather than reading
        the device directly, so this can't race against a weekday switch
        toggled around the same time, and doesn't add an extra network
        round trip on top of whatever the weekday switches already did.
        """

        def mutate(current: int) -> int:
            decoded = decode_weekday_mask(current)
            days = {day: decoded[day] for day in WEEKDAYS}
            correct_one_time = derive_one_time_flag(days)
            if decoded["one_time"] == correct_one_time:
                return current  # already valid, no write needed
            return encode_weekday_mask(days, one_time=correct_one_time)

        await self.coordinator.async_update_property_atomic(PROP_SCHEDULED_DRYING_WEEKDAYS, mutate)
