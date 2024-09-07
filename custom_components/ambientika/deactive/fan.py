"""Support for Ambientika fans."""

from __future__ import annotations

from typing import Any

from ambientika_py import Device, DeviceStatus, FanSpeed, OperatingMode

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from returns.result import Failure, Success

from ..const import DOMAIN, LOGGER, ORDERED_NAMED_FAN_SPEEDS
from ..hub import AmbientikaHub


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the `fan` entities for each device."""
    hub: AmbientikaHub = _hass.data[DOMAIN][entry.entry_id]

    # TODO: should we not mount the slave devices?
    async_add_entities((AmbientikaFan(device) for device in hub.devices), True)


class AmbientikaFan(FanEntity):
    """Representation of an Ambientika device."""

    # TODO:
    # should_poll = True

    _attr_has_entity_name = True
    _attr_translation_key = "fan"
    # _attr_icon = "mdi:air-purifier"
    _attr_device_class = "fan"

    def __init__(self, device: Device):
        """Initialize the fan."""
        self._device = device
        self._status: DeviceStatus | None = None

        self._attr_unique_id = f"{self._device.name}_fan"
        self._attr_name = self._device.name

    @property
    def device_info(self) -> dict:
        # TODO: move this to a common base class shared with sensor.py
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._device.serial_number)},
            "name": self._device.name,
            "manufacturer": "SUEDWIND",
            "model": "Ambientika",
            "serial_number": self._device.serial_number,
        }

    @property
    def supported_features(self) -> FanEntityFeature:
        """Returns the features supported by this device."""
        return FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE

    @property
    def is_on(self) -> bool | None:
        """Is the fan on."""
        if self._status:
            return self._status["operating_mode"] != OperatingMode.Off

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._status:
            return ordered_list_item_to_percentage(
                ORDERED_NAMED_FAN_SPEEDS, self._status["fan_speed"].name
            )

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(ORDERED_NAMED_FAN_SPEEDS)

    @property
    def preset_mode(self) -> str | None:
        """Returns the current operating mode."""
        if self._status:
            return self._status["operating_mode"].name

    @property
    def preset_modes(self) -> list[str] | None:
        """Returns the list of available operating modes."""
        return [name for name, _ in OperatingMode.__members__.items()]

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if self._status:
            if percentage:
                named_speed = percentage_to_ordered_list_item(
                    ORDERED_NAMED_FAN_SPEEDS, percentage
                )
                target_speed = FanSpeed[named_speed]
            else:
                target_speed = self._status["fan_speed"]

            if preset_mode:
                target_mode = OperatingMode[preset_mode]
            else:
                if self._status["last_operating_mode"] & (
                    self._status["last_operating_mode"] != OperatingMode.Off
                ):
                    target_mode = self._status["last_operating_mode"]
                else:
                    target_mode = OperatingMode.Auto
            if await self._device.change_mode(
                {
                    "operating_mode": target_mode,
                    "fan_speed": target_speed,
                    "humidity_level": self._status["humidity_level"],
                }
            ):
                self._status["last_operating_mode"] = self._status["operating_mode"]
                self._status["operating_mode"] = target_mode

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        target_mode = OperatingMode.Off
        if self._status:
            if await self._device.change_mode(
                {
                    "operating_mode": target_mode,
                    "fan_speed": self._status["fan_speed"],
                    "humidity_level": self._status["humidity_level"],
                }
            ):
                self._status["last_operating_mode"] = self._status["operating_mode"]
                self._status["operating_mode"] = target_mode

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the fan."""
        if self.is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        await self.async_turn_on(percentage=percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        await self.async_turn_on(preset_mode=preset_mode)

    async def async_update(self) -> None:
        """Fetch new state data for this device."""
        LOGGER.debug("Updating fan entity for device %s", self._device.serial_number)
        status = await self._device.status()
        match status:
            case Success(data):
                self._status = data
            case Failure(error):
                LOGGER.error(
                    "Could not fetch status for device %s. %s",
                    self._device.serial_number,
                    error,
                )
                self._status = None
