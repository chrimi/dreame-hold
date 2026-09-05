"""Binary sensor platform for Dreame Hold."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CHARGING_STATUS_CODES, DOMAIN, PROP_STATUS, PROP_STATUS_MIRROR
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity

CHARGING_DESCRIPTION = BinarySensorEntityDescription(
    key="charging",
    name="Charging",
    device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DreameHoldChargingBinarySensor(coordinator)])


class DreameHoldChargingBinarySensor(DreameHoldEntity, BinarySensorEntity):
    """True exactly while the device is drawing charge current.

    This is the intended trigger for a "cut power to the charging smart
    plug once charging is done" automation: turns off as soon as the
    status leaves STATUS_CHARGING (e.g. to docked_idle once full), so the
    plug isn't kept live on trickle/maintenance charge indefinitely.
    """

    entity_description = CHARGING_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def is_on(self) -> bool | None:
        status = self._property(PROP_STATUS)
        if status is None:
            status = self._property(PROP_STATUS_MIRROR)
        if status is None:
            return None
        return status in CHARGING_STATUS_CODES
