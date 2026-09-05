"""Time platform for Dreame Hold."""
from __future__ import annotations

from datetime import time as dt_time

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PROP_AUTO_DRYING_DISABLED, PROP_SCHEDULED_DRYING_TIME
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity

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

    CAUTION: the write direction for the whole scheduled-drying feature
    (this entity plus the weekday switches in switch.py) is less
    confirmed than the rest of the integration - only reading/decoding
    real values has been verified, not writing a freshly-picked time back
    to the device. See FINDINGS.md's "Live write-path testing" section.

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
        siid, piid = PROP_SCHEDULED_DRYING_TIME
        try:
            await self.hass.async_add_executor_job(self.coordinator.device.set_property, siid, piid, seconds)
        except Exception as ex:
            raise HomeAssistantError(f"Failed to set scheduled drying time: {ex}") from ex
        await self.coordinator.async_request_refresh()
