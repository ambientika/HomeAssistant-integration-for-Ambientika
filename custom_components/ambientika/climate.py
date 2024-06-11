"""Platform for climate control integration."""

from __future__ import annotations

from ambientika_py import Device, DeviceStatus, FanSpeed, OperatingMode
from returns.result import Failure, Success

from homeassistant.core import HomeAssistant
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .hub import AmbientikaHub


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ambientika platform."""
    hub: AmbientikaHub = _hass.data[DOMAIN][entry.entry_id]

    async_add_entities((AmbientikaFan(device) for device in hub.devices), True)


class AmbientikaFan(ClimateEntity):
    """Representation of an Ambientika device."""

    _device: Device
    _state: DeviceStatus | None

    def __init__(self, device: Device) -> None:
        """Initialize an Ambientika device."""
        self._device = device
        self._state = None

    @property
    def name(self) -> str:
        """Return the display name of this device."""
        return self._device.name

    @property
    def available(self) -> bool:
        """Returns wether the device is currently available."""
        return self._state is not None

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        if self._state:
            return self._state["humidity"]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if self._state:
            return self._state["temperature"]

    @property
    def fan_mode(self) -> str | None:
        """Returns the current fan mode."""
        if self._state:
            return self._state["fan_speed"].name

    @property
    def fan_modes(self) -> list[str] | None:
        """Returns the set of available fan modes."""
        return [name for name, _ in FanSpeed.__members__.items()]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Set the HVAC operating mode. Does nothing for this device."""
        if self._state:
            if self._state["operating_mode"] == OperatingMode.Off:
                return HVACMode.OFF
            else:
                return HVACMode.FAN_ONLY

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """List the valid HVAC modes."""
        return [HVACMode.OFF, HVACMode.FAN_ONLY]

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit."""
        return UnitOfTemperature.CELSIUS

    @property
    def preset_mode(self) -> str | None:
        """Returns the current operating mode."""
        if self._state:
            return self._state["operating_mode"].name

    @property
    def preset_modes(self) -> list[str] | None:
        """Returns the list of available operating modes."""
        return [name for name, _ in OperatingMode.__members__.items()]

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the device."""
        return self._device.serial_number

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Returns the features supported by this device."""
        return ClimateEntityFeature.FAN_MODE | ClimateEntityFeature.PRESET_MODE

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if self._state:
            return self._state["operating_mode"] != OperatingMode.Off

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        if self._state:
            if await self._device.change_mode(
                {
                    "operating_mode": self._state["operating_mode"],
                    "fan_speed": FanSpeed[fan_mode],
                    "humidity_level": self._state["humidity_level"],
                }
            ):
                self._state["fan_speed"] = FanSpeed[fan_mode]

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set the new HVAC Mode."""
        if not self._state:
            return

        if (
            hvac_mode == HVACMode.OFF
            and self._state["operating_mode"] != OperatingMode.Off
        ):
            if await self._device.change_mode(
                {
                    "operating_mode": OperatingMode.Off,
                    "fan_speed": self._state["fan_speed"],
                    "humidity_level": self._state["humidity_level"],
                }
            ):
                self._state["last_operating_mode"] = self._state["operating_mode"]
                self._state["operating_mode"] = OperatingMode.Off
        elif (
            hvac_mode == HVACMode.FAN_ONLY
            and self._state["operating_mode"] == OperatingMode.Off
        ):
            if await self._device.change_mode(
                {
                    "operating_mode": self._state["last_operating_mode"],
                    "fan_speed": self._state["fan_speed"],
                    "humidity_level": self._state["humidity_level"],
                }
            ):
                self._state["operating_mode"] = self._state["last_operating_mode"]
                self._state["last_operating_mode"] = OperatingMode.Off

    async def async_set_preset_mode(self, preset_mode: str):
        """Set the fan operation mode."""
        if not self._state:
            return

        if await self._device.change_mode(
            {
                "operating_mode": OperatingMode[preset_mode],
                "fan_speed": self._state["fan_speed"],
                "humidity_level": self._state["humidity_level"],
            }
        ):
            self._state["last_operating_mode"] = self._state["operating_mode"]
            self._state["operating_mode"] = self._state["last_operating_mode"]

    async def async_update(self) -> None:
        """Fetch new state data for this device."""
        status = await self._device.status()
        match status:
            case Success(data):
                self._state = data
            case Failure(error):
                LOGGER.error(
                    "Could not fetch status for device %s. %s",
                    self._device.serial_number,
                    error,
                )
                self._state = None
