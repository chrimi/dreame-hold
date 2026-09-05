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
    """True while the device reports STATUS_CHARGING.

    CAUTION: do not use this alone as a "cut power once charging is done"
    automation trigger. FINDINGS.md documents two snapshots at genuine,
    owner-confirmed 100% battery ~1h apart where this flipped true then
    false then (implicitly) true again — the charge controller appears to
    issue brief maintenance/top-off pulses even once full, so this sensor
    can turn back on after the battery already reached 100%. For a smart-
    plug cutoff automation, trigger on `sensor.<name>_battery` reaching
    100 and staying there for a sustained window (e.g. HA's trigger `for:`
    with 20-30 minutes) instead — that rides through these pulses. This
    sensor remains useful as a live diagnostic of the raw reported state.
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
