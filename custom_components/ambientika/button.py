"""Button platform for integration_ambientika.

References:
 - https://developers.home-assistant.io/docs/core/entity/button
 - [BUG](https://github.com/wingertge/ambientika-py/issues/2)
 - https://app.ambientika.eu:4521/swagger/index.html#operations-Device-get_Device_device_status

"""

from __future__ import annotations

from ambientika_py import Device

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from returns.result import Failure, Success

from .const import DOMAIN, LOGGER
from .hub import AmbientikaHub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the `button` entities for each device."""
    hub: AmbientikaHub = hass.data[DOMAIN][entry.entry_id]

    # TODO: should we not mount the slave devices?
    async_add_entities((FilterResetButton(device, hub) for device in hub.devices), True)


class FilterResetButton(ButtonEntity):
    """Representation of a button.

    ambientika_py does not offer a method for resetting the filter.
    Because of that we have to use the API directly - and therefore forward the AmbientikaHub to the Button.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "filter_reset"

    def __init__(self, device: Device, hub: AmbientikaHub) -> None:
        """Initialize the button."""
        self._device = device
        self._hub = hub
        self._attr_unique_id = f"{self._device.name}_filter_reset"

    @property
    def device_info(self):
        # TODO: move this to a common base class shared with climate.py
        """Return information to link this entity with the correct device."""
        return {
            "identifiers": {(DOMAIN, self._device.serial_number)},
            "name": self._device.name,
            "manufacturer": "SUEDWIND",
            "model": "Ambientika",
            "serial_number": self._device.serial_number,
        }

    async def async_press(self) -> None:
        """Handle the button press."""
        LOGGER.debug(
            "[%s] pressed %s.",
            "button",
            self._device.serial_number,
        )
        response = await self._device.api.get(
            "device/reset-filter", {"deviceSerialNumber": self._device.serial_number}
        )
        match response:
            case Success(data):
                LOGGER.debug(
                    "[%s] press %s: success. %s",
                    "button",
                    self._device.serial_number,
                    data,
                )
            case Failure(error):
                LOGGER.error(
                    "[%s] press %s: failed. %s",
                    "button",
                    self._device.serial_number,
                    error,
                )
