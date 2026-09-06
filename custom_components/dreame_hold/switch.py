"""Switch platform for Dreame Hold."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PROP_AUTO_DRYING_DISABLED,
    PROP_AUTO_SELFCLEAN_DISABLED,
    PROP_CUSTOM_MODE_ENABLED,
    PROP_ELECTROLYZED_WATER_DISABLED,
    PROP_LIGHT_SWITCH,
    PROP_SCHEDULED_DRYING_WEEKDAYS,
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity
from .helpers import WEEKDAYS, decode_weekday_mask, derive_one_time_flag, encode_weekday_mask


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(key="light", name="Light"),
                prop=PROP_LIGHT_SWITCH,
                on_value=1,
                off_value=0,
            ),
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(
                    key="auto_self_clean", name="Automatic self-clean", entity_category=EntityCategory.CONFIG
                ),
                prop=PROP_AUTO_SELFCLEAN_DISABLED,
                on_value=0,
                off_value=1,
            ),
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(
                    key="auto_drying",
                    name="Automatic roller brush drying",
                    entity_category=EntityCategory.CONFIG,
                ),
                prop=PROP_AUTO_DRYING_DISABLED,
                on_value=0,
                off_value=1,
            ),
            # "Custom mode: " prefix groups this with the other
            # custom-cleaning-mode entities (select.py's "Custom mode:
            # Suction power"/"...: Water level", and "...: Prepare
            # electrolyzed water" below) in the UI - otherwise they sort
            # alphabetically scattered with no visual connection.
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(
                    key="custom_cleaning_mode",
                    name="Custom mode: Enabled",
                    entity_category=EntityCategory.CONFIG,
                ),
                prop=PROP_CUSTOM_MODE_ENABLED,
                on_value=1,
                off_value=0,
            ),
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(
                    key="prepare_electrolyzed_water",
                    name="Custom mode: Prepare electrolyzed water",
                    entity_category=EntityCategory.CONFIG,
                ),
                prop=PROP_ELECTROLYZED_WATER_DISABLED,
                on_value=0,
                off_value=1,
                # Confirmed on a real device: this can only actually be
                # toggled while "Custom mode: Enabled" is on.
                depends_on=(PROP_CUSTOM_MODE_ENABLED, 1),
            ),
            *[DreameHoldWeekdaySwitch(coordinator, day, index) for index, day in enumerate(WEEKDAYS)],
        ]
    )


class DreameHoldSwitch(DreameHoldEntity, SwitchEntity):
    """Generic on/off switch backed by a single numeric property.

    Several of the device's flags use inverted semantics (0=on, 1=off,
    e.g. PROP_AUTO_SELFCLEAN_DISABLED) - pass the actual on_value/off_value
    pair rather than assuming 0=off/1=on.

    `depends_on` marks the switch unavailable unless another property
    currently equals a required value - e.g. "Prepare electrolyzed water"
    only actually works while "Custom cleaning mode" is on (confirmed on
    a real device).
    """

    def __init__(
        self,
        coordinator: DreameHoldDataUpdateCoordinator,
        description: SwitchEntityDescription,
        prop: tuple[int, int],
        on_value: int,
        off_value: int,
        depends_on: tuple[tuple[int, int], int] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._prop = prop
        self._on_value = on_value
        self._off_value = off_value
        self._depends_on = depends_on
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        if self._depends_on is not None:
            dep_prop, dep_value = self._depends_on
            return self._property(dep_prop) == dep_value
        return True

    @property
    def is_on(self) -> bool | None:
        value = self._property(self._prop)
        if value is None:
            return None
        return value == self._on_value

    async def _set(self, value: int) -> None:
        siid, piid = self._prop
        try:
            await self.hass.async_add_executor_job(self.coordinator.device.set_property, siid, piid, value)
        except Exception as ex:
            raise HomeAssistantError(f"Failed to set {self.entity_description.key}: {ex}") from ex
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(self._on_value)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(self._off_value)


class DreameHoldWeekdaySwitch(DreameHoldEntity, SwitchEntity):
    """One weekday bit of PROP_SCHEDULED_DRYING_WEEKDAYS.

    Write path confirmed working live (see FINDINGS.md's "Live write-path
    testing" section). Only available while "Automatic roller brush
    drying" is on (turning that off resets the whole schedule to 0 on the
    device, confirmed) - modeled via `depends_on` like the
    electrolyzed-water switch above.

    All 7 of these share one encoded property, so toggling one requires a
    read-modify-write of the whole mask. `_set` deliberately fetches a
    *fresh* value from the device right before writing (not the
    coordinator's polled/cached value, which can be up to
    DEFAULT_SCAN_INTERVAL seconds stale) - toggling two of these switches
    in quick succession against a stale cached base would otherwise let
    the second write silently undo the first. It also re-derives the
    mask's "one-time" flag from the resulting day selection (see
    `derive_one_time_flag`) rather than preserving the previous flag.

    Names are prefixed with a 1-7 index so Home Assistant's alphabetical
    entity sort still lands in Monday..Sunday order.
    """

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator, day: str, index: int) -> None:
        super().__init__(coordinator)
        self.entity_description = SwitchEntityDescription(
            key=f"scheduled_drying_{day}",
            name=f"Scheduled drying: {index + 1} {day.capitalize()}",
            entity_category=EntityCategory.CONFIG,
        )
        self._day = day
        self._attr_unique_id = f"{coordinator.device.device_id}_{self.entity_description.key}"

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self._property(PROP_AUTO_DRYING_DISABLED) == 0

    @property
    def is_on(self) -> bool | None:
        value = self._property(PROP_SCHEDULED_DRYING_WEEKDAYS)
        if value is None:
            return None
        return decode_weekday_mask(value)[self._day]

    async def _set(self, enabled: bool) -> None:
        siid, piid = PROP_SCHEDULED_DRYING_WEEKDAYS
        try:
            fresh = await self.hass.async_add_executor_job(
                self.coordinator.device.get_properties, [{"siid": siid, "piid": piid}]
            )
        except Exception as ex:
            raise HomeAssistantError(f"Failed to read current schedule before setting {self._day}: {ex}") from ex

        current = 0
        if fresh:
            match = next((r for r in fresh if r.get("siid") == siid and r.get("piid") == piid), None)
            if match and match.get("code") == 0:
                current = match.get("value") or 0

        decoded = decode_weekday_mask(current)
        decoded[self._day] = enabled
        decoded.pop("one_time")
        # Derive the one-time flag from the resulting day selection rather
        # than preserving whatever it was before this toggle - a schedule
        # can't be both "one-time" and repeat on specific days. Turning a
        # day on always makes this a repeating schedule; turning the last
        # remaining day off correctly falls back to "one-time" (see
        # derive_one_time_flag's docstring for the bug this fixes).
        new_value = encode_weekday_mask(decoded, one_time=derive_one_time_flag(decoded))

        try:
            await self.hass.async_add_executor_job(self.coordinator.device.set_property, siid, piid, new_value)
        except Exception as ex:
            raise HomeAssistantError(f"Failed to set scheduled drying {self._day}: {ex}") from ex
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
