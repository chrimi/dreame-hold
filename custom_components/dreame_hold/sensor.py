"""Sensor platform for Dreame Hold."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CLEANING_MODE_NAMES,
    DOMAIN,
    PROP_ACTIVITY_PROGRESS,
    PROP_BATTERY_LEVEL,
    PROP_CLEANING_MODE,
    PROP_CUSTOM_MODE_ENABLED,
    PROP_LAST_RUN_DURATION,
    PROP_SOILING_HEAVY,
    PROP_SOILING_LIGHT,
    PROP_SOILING_MODERATE,
    PROP_STATUS,
    PROP_STATUS_MIRROR,
    STATUS_NAMES,
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity
from .helpers import soiling_percentages

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

LAST_RUN_DURATION_DESCRIPTION = SensorEntityDescription(
    key="last_run_duration",
    name="Last cleaning run duration",
    device_class=SensorDeviceClass.DURATION,
    native_unit_of_measurement=UnitOfTime.SECONDS,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
)

SOILING_LIGHT_DESCRIPTION = SensorEntityDescription(
    key="soiling_light",
    name="Last run soiling: light",
    native_unit_of_measurement=PERCENTAGE,
    entity_category=EntityCategory.DIAGNOSTIC,
)

SOILING_MODERATE_DESCRIPTION = SensorEntityDescription(
    key="soiling_moderate",
    name="Last run soiling: moderate",
    native_unit_of_measurement=PERCENTAGE,
    entity_category=EntityCategory.DIAGNOSTIC,
)

SOILING_HEAVY_DESCRIPTION = SensorEntityDescription(
    key="soiling_heavy",
    name="Last run soiling: heavy",
    native_unit_of_measurement=PERCENTAGE,
    entity_category=EntityCategory.DIAGNOSTIC,
)

CLEANING_MODE_DESCRIPTION = SensorEntityDescription(
    key="cleaning_mode",
    name="Cleaning mode",
    device_class=SensorDeviceClass.ENUM,
    options=[*CLEANING_MODE_NAMES.values(), "unknown"],
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
            DreameHoldLastRunDurationSensor(coordinator),
            DreameHoldSoilingSensor(coordinator, SOILING_LIGHT_DESCRIPTION, PROP_SOILING_LIGHT),
            DreameHoldSoilingSensor(coordinator, SOILING_MODERATE_DESCRIPTION, PROP_SOILING_MODERATE),
            DreameHoldSoilingSensor(coordinator, SOILING_HEAVY_DESCRIPTION, PROP_SOILING_HEAVY),
            DreameHoldCleaningModeSensor(coordinator),
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


class DreameHoldLastRunDurationSensor(DreameHoldEntity, SensorEntity):
    """Duration of the last vacuuming run. Confirmed exactly against an
    owner-reported run (364s = 6 min 4 sec) — see FINDINGS.md."""

    entity_description = LAST_RUN_DURATION_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> int | None:
        return self._property(PROP_LAST_RUN_DURATION)


class DreameHoldSoilingSensor(DreameHoldEntity, SensorEntity):
    """Percentage of the last run spent on light/moderate/heavy soiling.

    Computed from the raw seconds properties using the same "floor the
    first two, remainder to the last" convention the app itself uses —
    confirmed to reproduce the app's own displayed breakdown (84%/14%/2%)
    exactly, which independent per-value rounding wouldn't guarantee
    (the three values wouldn't always sum to 100).
    """

    def __init__(
        self,
        coordinator: DreameHoldDataUpdateCoordinator,
        description: SensorEntityDescription,
        prop: tuple[int, int],
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._prop = prop
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"

    @property
    def native_value(self) -> int | None:
        light = self._property(PROP_SOILING_LIGHT)
        moderate = self._property(PROP_SOILING_MODERATE)
        heavy = self._property(PROP_SOILING_HEAVY)
        if light is None or moderate is None or heavy is None:
            return None

        percentages = soiling_percentages(light, moderate, heavy)
        if percentages is None:
            return None
        light_pct, moderate_pct, heavy_pct = percentages

        if self._prop == PROP_SOILING_LIGHT:
            return light_pct
        if self._prop == PROP_SOILING_MODERATE:
            return moderate_pct
        return heavy_pct


class DreameHoldCleaningModeSensor(DreameHoldEntity, SensorEntity):
    """Read-only: which cleaning mode is currently active.

    Not a `select` — confirmed on a real device that writing PROP_CLEANING_MODE
    directly (to switch to "quiet"/"turbo") doesn't actually change the
    mode. Likely a derived reflection of PROP_SUCTION_POWER +
    PROP_WATER_LEVEL rather than something settable on its own; exposed
    read-only until the real write mechanism is found (see FINDINGS.md).

    Only meaningful while "Custom mode: Enabled" (PROP_CUSTOM_MODE_ENABLED)
    is on - confirmed with the device owner: the app itself only shows a
    cleaning-mode picker (quiet/turbo/personalized) once you go to turn
    Custom mode on, defaulting to whatever was last selected there. While
    Custom mode is off, PROP_CLEANING_MODE's raw value is just that
    remembered last selection, not anything currently in effect -
    reporting it unconditionally (as an earlier version of this entity
    did) falsely implied a mode was "active" when it wasn't. Marked
    unavailable instead, matching the same `depends_on` treatment already
    used for Suction power/Water level in select.py.
    """

    entity_description = CLEANING_MODE_DESCRIPTION

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self._property(PROP_CUSTOM_MODE_ENABLED) == 1

    @property
    def native_value(self) -> str:
        value = self._property(PROP_CLEANING_MODE)
        if value is None:
            return "unknown"
        return CLEANING_MODE_NAMES.get(value, "unknown")
