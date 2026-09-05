"""Select platform for Dreame Hold."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DRYING_MODE_NAMES,
    LANGUAGE_NAMES,
    PROP_DRYING_MODE,
    PROP_DRYING_MODE_MIRROR,
    PROP_PROPULSION_FORCE,
    PROP_SUCTION_POWER,
    PROP_VOICE_LANGUAGE,
    PROP_WATER_LEVEL,
    PROPULSION_FORCE_NAMES,
    SUCTION_POWER_NAMES,
    WATER_LEVEL_NAMES,
)
from .coordinator import DreameHoldDataUpdateCoordinator
from .entity import DreameHoldEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: DreameHoldDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            DreameHoldEnumSelect(
                coordinator,
                SelectEntityDescription(
                    key="drying_mode", name="Drying mode", entity_category=EntityCategory.CONFIG
                ),
                prop=PROP_DRYING_MODE,
                names=DRYING_MODE_NAMES,
                mirror_prop=PROP_DRYING_MODE_MIRROR,
            ),
            DreameHoldEnumSelect(
                coordinator,
                SelectEntityDescription(
                    key="voice_language", name="Voice language", entity_category=EntityCategory.CONFIG
                ),
                prop=PROP_VOICE_LANGUAGE,
                names=LANGUAGE_NAMES,
            ),
            DreameHoldEnumSelect(
                coordinator,
                SelectEntityDescription(
                    key="suction_power", name="Suction power", entity_category=EntityCategory.CONFIG
                ),
                prop=PROP_SUCTION_POWER,
                names=SUCTION_POWER_NAMES,
            ),
            DreameHoldEnumSelect(
                coordinator,
                SelectEntityDescription(
                    key="water_level", name="Water level", entity_category=EntityCategory.CONFIG
                ),
                prop=PROP_WATER_LEVEL,
                names=WATER_LEVEL_NAMES,
                # "level_2" is only ever observed as an implied side effect of
                # "Leiser Modus" (see const.py) - the app's own Personalized
                # Mode water-level picker only offers "daily"/"wet". Kept
                # decodable (for reading) but not offered as something to
                # select, since picking it doesn't correspond to a real app
                # action.
                selectable_options=["daily", "wet"],
            ),
            # NOTE: "Cleaning mode" (PROP_CLEANING_MODE) is NOT here - see
            # sensor.py. Confirmed on a real device that selecting
            # "quiet"/"turbo" does not actually change the mode, so it's
            # exposed read-only until the real write mechanism is found.
            DreameHoldEnumSelect(
                coordinator,
                SelectEntityDescription(
                    key="propulsion_force",
                    name="Self propulsion force",
                    entity_category=EntityCategory.CONFIG,
                ),
                prop=PROP_PROPULSION_FORCE,
                names=PROPULSION_FORCE_NAMES,
            ),
        ]
    )


class DreameHoldEnumSelect(DreameHoldEntity, SelectEntity):
    """Generic select entity backed by a numeric property and a
    name<->value enum map (see const.py's *_NAMES dicts).

    Writes go through DreameCloudDevice.set_property via the executor,
    then request a coordinator refresh so the UI reflects the confirmed
    new state rather than assuming the write succeeded. A value the
    device reports that isn't in `names` (e.g. a code from a different
    model/firmware/region) surfaces as an unavailable current_option
    rather than raising.

    `selectable_options` lets the offered dropdown differ from the full
    set of decodable values - e.g. Water level decodes an internal
    "level_2" the app itself never lets you pick directly (only "daily"/
    "wet" are real choices in Personalized Mode); defaults to all of
    `names` when not given.
    """

    def __init__(
        self,
        coordinator: DreameHoldDataUpdateCoordinator,
        description: SelectEntityDescription,
        prop: tuple[int, int],
        names: dict[int, str],
        mirror_prop: tuple[int, int] | None = None,
        selectable_options: list[str] | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._prop = prop
        self._mirror_prop = mirror_prop
        self._names = names
        self._values = {v: k for k, v in names.items()}
        self._attr_unique_id = f"{coordinator.device.device_id}_{description.key}"
        self._attr_options = list(names.values()) if selectable_options is None else selectable_options

    @property
    def current_option(self) -> str | None:
        value = self._property(self._prop)
        if value is None:
            return None
        return self._names.get(value)

    async def async_select_option(self, option: str) -> None:
        if option not in self._attr_options:
            raise HomeAssistantError(f"'{option}' is not selectable for {self.entity_description.key}")
        value = self._values.get(option)
        if value is None:
            raise HomeAssistantError(f"Unknown option '{option}' for {self.entity_description.key}")

        siid, piid = self._prop
        try:
            await self.hass.async_add_executor_job(self.coordinator.device.set_property, siid, piid, value)
            if self._mirror_prop is not None:
                m_siid, m_piid = self._mirror_prop
                await self.hass.async_add_executor_job(
                    self.coordinator.device.set_property, m_siid, m_piid, value
                )
        except Exception as ex:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.key} to '{option}': {ex}"
            ) from ex
        await self.coordinator.async_request_refresh()
