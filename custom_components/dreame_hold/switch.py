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
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity


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
            DreameHoldSwitch(
                coordinator,
                SwitchEntityDescription(
                    key="custom_cleaning_mode",
                    name="Custom cleaning mode",
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
                    name="Prepare electrolyzed water",
                    entity_category=EntityCategory.CONFIG,
                ),
                prop=PROP_ELECTROLYZED_WATER_DISABLED,
                on_value=0,
                off_value=1,
            ),
        ]
    )


class DreameHoldSwitch(DreameHoldEntity, SwitchEntity):
    """Generic on/off switch backed by a single numeric property.

    Several of the device's flags use inverted semantics (0=on, 1=off,
    e.g. PROP_AUTO_SELFCLEAN_DISABLED) - pass the actual on_value/off_value
    pair rather than assuming 0=off/1=on.
    """

    def __init__(
        self,
        coordinator: DreameHoldDataUpdateCoordinator,
        description: SwitchEntityDescription,
        prop: tuple[int, int],
        on_value: int,
        off_value: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._prop = prop
        self._on_value = on_value
        self._off_value = off_value
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"

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
