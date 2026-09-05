"""Config flow for Dreame Hold."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_COUNTRY, CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    ACCOUNT_TYPE_DREAME,
    ACCOUNT_TYPES,
    CONF_ACCOUNT_TYPE,
    CONF_DEVICE_ID,
    CONF_MODEL,
    COUNTRIES,
    DEFAULT_COUNTRY,
    DOMAIN,
    LOGGER,
)
from .dreame_cloud.cloud_base import DreameCloudBase
from .helpers import extract_hold_devices


class DreameHoldConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Dreame Hold."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str | None = None
        self._password: str | None = None
        self._country: str = DEFAULT_COUNTRY
        self._account_type: str = ACCOUNT_TYPE_DREAME
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._country = user_input[CONF_COUNTRY]
            self._account_type = user_input[CONF_ACCOUNT_TYPE]

            cloud = DreameCloudBase(
                username=self._username,
                password=self._password,
                country=self._country,
                account_type=self._account_type,
            )
            connected = await self.hass.async_add_executor_job(cloud.connect)
            if not connected:
                errors["base"] = "login_error"
            else:
                devices_response = await self.hass.async_add_executor_job(cloud.get_devices)
                self._devices = extract_hold_devices(devices_response)
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    return await self._async_create_entry(self._devices[0])
                else:
                    return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Required(CONF_COUNTRY, default=DEFAULT_COUNTRY): vol.In(COUNTRIES),
                    vol.Required(CONF_ACCOUNT_TYPE, default=ACCOUNT_TYPE_DREAME): vol.In(ACCOUNT_TYPES),
                }
            ),
            errors=errors,
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        options = {d["did"]: f"{d.get('model', 'unknown model')} ({d['did']})" for d in self._devices}

        if user_input is not None:
            selected_did = user_input[CONF_DEVICE_ID]
            device = next(d for d in self._devices if d["did"] == selected_did)
            return await self._async_create_entry(device)

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE_ID): vol.In(options)}),
        )

    async def _async_create_entry(self, device: dict[str, Any]) -> FlowResult:
        did = str(device["did"])
        model = device.get("model", "dreame.hold")

        await self.async_set_unique_id(did)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Dreame {model}",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_COUNTRY: self._country,
                CONF_ACCOUNT_TYPE: self._account_type,
                CONF_DEVICE_ID: did,
                CONF_MODEL: model,
            },
        )
