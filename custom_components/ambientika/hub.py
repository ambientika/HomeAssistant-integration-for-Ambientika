"""A demonstration 'hub' that connects several devices."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

# from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import UpdateFailed, DataUpdateCoordinator

from .api import (
    AmbientikaApiClient,
    AmbientikaApiClientAuthenticationError,
    AmbientikaApiClientError,
)
from .const import DOMAIN, LOGGER


class AmbientikaHub(DataUpdateCoordinator):
    """Connection Hub to all devices."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config: Mapping[str, Any]) -> None:
        """Init dummy hub."""
        self._hass_config = hass
        self._hass = hass
        self.devices = []

        self._credentials = {
            "username": config.get(CONF_USERNAME, ""),
            "password": config.get(CONF_PASSWORD, ""),
        }

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=5),
        )

    async def login(self) -> None:
        """Async loading of the devices."""

        self.client = AmbientikaApiClient(
            username=self._credentials["username"],
            password=self._credentials["password"],
        )
        self.devices = await self.client.async_get_data()

    # def register_platform_add_entities(
    #     self,
    #     _entry: ConfigEntry,
    #     async_add_entities: AddEntitiesCallback,
    # ) -> None:
    #     """Create entities from descriptions and add them."""

    #     # TODO: Implement this method
    #     # new_entites: list[AmbientikaFan] = []

    #     # for device in self._devices:
    #     #     for description in descriptions:
    #     #         if capability := description.capability_fn(device.capabilities):
    #     #             new_entites.append(entity_class(device, capability, description))

    #     async_add_entities((AmbientikaFan(device) for device in self._devices), True)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except AmbientikaApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except AmbientikaApiClientError as exception:
            raise UpdateFailed(exception) from exception
