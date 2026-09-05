"""Base entity for Dreame Hold."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DreameHoldDataUpdateCoordinator


class DreameHoldEntity(CoordinatorEntity[DreameHoldDataUpdateCoordinator]):
    """Common base for all Dreame Hold entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DreameHoldDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        device_id = coordinator.device.device_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            manufacturer=MANUFACTURER,
            model=coordinator.model,
            name=f"Dreame {coordinator.model or device_id}",
        )

    def _property(self, key: tuple[int, int], default: Any = None) -> Any:
        """Look up a polled (siid, piid) property from the coordinator's last data."""
        if self.coordinator.data is None:
            return default
        return self.coordinator.data.get(key, default)
