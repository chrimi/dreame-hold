"""Number platform for Dreame Hold."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PROP_VOICE_VOLUME
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity

VOLUME_DESCRIPTION = NumberEntityDescription(
    key="voice_volume",
    name="Voice volume",
    native_min_value=0,
    native_max_value=100,
    native_step=1,
    native_unit_of_measurement=PERCENTAGE,
    mode=NumberMode.SLIDER,
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DreameHoldVoiceVolumeNumber(coordinator)])


class DreameHoldVoiceVolumeNumber(DreameHoldEntity, NumberEntity):
    entity_description = VOLUME_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> int | None:
        return self._property(PROP_VOICE_VOLUME)

    async def async_set_native_value(self, value: float) -> None:
        siid, piid = PROP_VOICE_VOLUME
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.device.set_property, siid, piid, int(value)
            )
        except Exception as ex:
            raise HomeAssistantError(f"Failed to set voice volume: {ex}") from ex
        await self.coordinator.async_request_refresh()
