"""Configuration flow.

This will prompt the user for input when adding the intergation.
https://developers.home-assistant.io/docs/config_entries_config_flow_handler
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .api import (
    AmbientikaApiClient,
    AmbientikaApiClientAuthenticationError,
    AmbientikaApiClientError,
)
from .const import DOMAIN, LOGGER


class AmbientikaFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow Class."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                devices = await _test_pairing(
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
                )
            except AmbientikaApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "auth"
            except AmbientikaApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            except Exception as exception:  # pylint: disable=broad-except
                LOGGER.exception(exception)
                errors["base"] = "unknown"

            if not errors:
                if len(devices) == 0:
                    return self.async_abort(reason="no_supported_devices_found")

                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, vol.UNDEFINED),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=errors,
        )


async def _test_pairing(username, password) -> list:
    client = AmbientikaApiClient(username, password)
    return await client.async_get_data()
