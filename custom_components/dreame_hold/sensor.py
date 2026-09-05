"""Sensor platform for Dreame Hold."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PROP_ACTIVITY_PROGRESS,
    PROP_BATTERY_LEVEL,
    PROP_STATUS,
    PROP_STATUS_MIRROR,
    STATUS_NAMES,
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity

BATTERY_DESCRIPTION = SensorEntityDescription(
    key="battery_level",
    name="Battery",
    device_class=SensorDeviceClass.BATTERY,
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
)

STATUS_DESCRIPTION = SensorEntityDescription(
    key="status",
    name="Status",
    device_class=SensorDeviceClass.ENUM,
    options=[*STATUS_NAMES.values(), "unknown"],
    entity_category=EntityCategory.DIAGNOSTIC,
)

PROGRESS_DESCRIPTION = SensorEntityDescription(
    key="activity_progress",
    name="Activity progress",
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DreameHoldBatterySensor(coordinator),
            DreameHoldStatusSensor(coordinator),
            DreameHoldProgressSensor(coordinator),
        ]
    )


class DreameHoldBatterySensor(DreameHoldEntity, SensorEntity):
    entity_description = BATTERY_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> int | None:
        return self._property(PROP_BATTERY_LEVEL)


class DreameHoldStatusSensor(DreameHoldEntity, SensorEntity):
    """Raw status code decoded to a name; see const.STATUS_NAMES.

    Codes we haven't observed yet (other models, firmware, or device
    states like an error condition) surface as "unknown" rather than
    raising, with the raw code kept in `status_code` for diagnosis.
    """

    entity_description = STATUS_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def _raw_status(self) -> int | None:
        status = self._property(PROP_STATUS)
        if status is None:
            status = self._property(PROP_STATUS_MIRROR)
        return status

    @property
    def native_value(self) -> str:
        status = self._raw_status
        if status is None:
            return "unknown"
        return STATUS_NAMES.get(status, "unknown")

    @property
    def extra_state_attributes(self) -> dict:
        return {"status_code": self._raw_status}


class DreameHoldProgressSensor(DreameHoldEntity, SensorEntity):
    """Progress % of the currently active self-clean/drying cycle.

    Meaningless (0) while idle or charging — that's the device's own
    reported value in those states, not a placeholder we're inserting.
    """

    entity_description = PROGRESS_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> int | None:
        return self._property(PROP_ACTIVITY_PROGRESS)
