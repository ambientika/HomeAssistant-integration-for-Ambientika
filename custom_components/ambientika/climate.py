"""Platform for climate control integration."""

from __future__ import annotations

from ambientika_py import Device, DeviceStatus, FanSpeed, HumidityLevel, OperatingMode

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    HVACAction,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
# from homeassistant.util.percentage import (
# ordered_list_item_to_percentage,
# percentage_to_ordered_list_item,
# )

from returns.result import Failure, Success

from .const import (
    DOMAIN,
    LOGGER,
    # ORDERED_NAMED_FAN_SPEEDS,
    # ORDERED_NAMED_HUMIDITY_LEVELS,
)
from .hub import AmbientikaHub

FAN_SPEED_AMBIENTIKA_TO_HVAC = {
    FanSpeed.Low: FAN_LOW,
    FanSpeed.Medium: FAN_MEDIUM,
    FanSpeed.High: FAN_HIGH,
}
FAN_SPEED_HVAC_TO_AMBIENTIKA = {
    value: key for key, value in FAN_SPEED_AMBIENTIKA_TO_HVAC.items()
}
HUMIDITY_LEVEL_TO_INT = {
    HumidityLevel.Dry: 1,
    HumidityLevel.Normal: 2,
    HumidityLevel.Moist: 3,
}
HUMIDITY_INT_TO_LEVEL = {value: key for key, value in HUMIDITY_LEVEL_TO_INT.items()}


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the `climate` entities for each device."""
    hub: AmbientikaHub = _hass.data[DOMAIN][entry.entry_id]

    # TODO: should we not mount the slave devices?
    async_add_entities((AmbientikaClimate(device) for device in hub.devices), True)


class AmbientikaClimate(ClimateEntity):
    """Representation of an Ambientika device."""

    # TODO:
    # _attr_should_poll = True

    _attr_has_entity_name = True
    _attr_name = None
    _attr_translation_key = "climate"
    _attr_max_humidity = 3
    _attr_min_humidity = 1
    # _attr_icon = "mdi:air-conditioner"
    # _attr_device_class = "climate"

    def __init__(self, device: Device) -> None:
        """Initialize an Ambientika device."""
        self._device = device
        self._status: DeviceStatus | None = None

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"climate_{self._device.name}_{self._device.serial_number}"

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
    def available(self) -> bool:
        """Returns wether the device is currently available."""
        return self._status is not None

    @property
    def name(self) -> str:
        """Return the display name of this device."""
        return self._device.name

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Returns the features supported by this device."""
        return (
            ClimateEntityFeature.TARGET_HUMIDITY
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.PRESET_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if device is on."""
        if not self._status:
            return

        return self._status["operating_mode"] != OperatingMode.Off

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return [FAN_SPEED_AMBIENTIKA_TO_HVAC[fan_speed] for fan_speed in FanSpeed]

    @property
    def fan_mode(self) -> str | None:
        """Returns the current fan mode."""
        if not self._status:
            return

        return FAN_SPEED_AMBIENTIKA_TO_HVAC.get(self._status["fan_speed"])

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit."""
        return UnitOfTemperature.CELSIUS

    @property
    def preset_modes(self) -> list[str] | None:
        """Returns the list of available operating modes."""
        return [name for name, _ in OperatingMode.__members__.items()]

    @property
    def preset_mode(self) -> str | None:
        """Returns the current operating mode."""
        if not self._status:
            return

        return self._status["operating_mode"].name

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        if not self._status:
            return

        return self._status["humidity"]

    @property
    def target_humidity(self) -> int | None:
        """Return the target humidity."""
        if not self._status:
            return

        return HUMIDITY_LEVEL_TO_INT[self._status["humidity_level"]]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if not self._status:
            return

        return self._status["temperature"]

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """List the valid HVAC modes."""
        return [HVACMode.OFF, HVACMode.FAN_ONLY]

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Set the HVAC operating mode. Does nothing for this device."""
        if not self._status:
            return

        if self._status["operating_mode"] == OperatingMode.Off:
            return HVACMode.OFF
        else:
            return HVACMode.FAN_ONLY

    @property
    def hvac_action(self) -> str | None:
        """Return the current HVAC action."""
        if not self._status:
            return

        if self._status["operating_mode"] == OperatingMode.Off:
            return HVACAction.OFF
        else:
            return HVACAction.FAN

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set the new HVAC Mode."""
        if not self._status:
            return

        if hvac_mode == HVACMode.OFF:
            await self.async_set_device(operation_mode="Off")
        else:
            await self.async_set_device(operation_mode="Auto")

    async def async_set_preset_mode(self, preset_mode: str):
        """Set the fan operation mode."""
        if not self._status:
            return

        await self.async_set_device(operation_mode=preset_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        if not self._status:
            return

        await self.async_set_device(fan_mode=fan_mode)
        # self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the humidity."""
        if not self._status:
            return

        await self.async_set_device(humidity=humidity)
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn device on."""
        if not self._status:
            return

        await self.async_set_hvac_mode(hvac_mode=HVACMode.FAN_ONLY)

    async def async_turn_off(self) -> None:
        """Turn device off."""
        if not self._status:
            return

        await self.async_set_hvac_mode(hvac_mode=HVACMode.OFF)

    async def async_set_device(
        self,
        fan_mode: str | None = None,
        operation_mode: str | None = None,
        humidity: int | None = None,
    ) -> None:
        """Make changes to the device."""
        if not self._status:
            return

        if operation_mode:
            target_mode = OperatingMode[operation_mode]
        else:
            if self._status["operating_mode"]:
                target_mode = self._status["operating_mode"]
            else:
                target_mode = OperatingMode.Auto

        if fan_mode:
            target_speed = FanSpeed[FAN_SPEED_HVAC_TO_AMBIENTIKA[fan_mode].name]
        else:
            if self._status["fan_speed"]:
                target_speed = self._status["fan_speed"]
            else:
                target_speed = FanSpeed.Low

        if humidity:
            target_humidity = HUMIDITY_INT_TO_LEVEL[humidity]
        else:
            if self._status["humidity_level"]:
                target_humidity = self._status["humidity_level"]
            else:
                target_humidity = HumidityLevel.Normal

        LOGGER.debug(
            "Writing to device %s: mode %s, fan speed %s, humidity_level %s",
            self._device.serial_number,
            target_mode,
            target_speed,
            target_humidity,
        )
        status = await self._device.change_mode(
            {
                "operating_mode": target_mode,
                "fan_speed": target_speed,
                "humidity_level": target_humidity,
            }
        )
        match status:
            case Success(_):
                LOGGER.debug(
                    "Writing to device %s: success", self._device.serial_number
                )
                self._status["last_operating_mode"] = self._status["operating_mode"]
                self._status["operating_mode"] = target_mode
            case Failure(error):
                LOGGER.error(
                    "Writing to device %s: failed. %s",
                    self._device.serial_number,
                    error,
                )

    async def async_update(self) -> None:
        """Fetch new state data for this device."""
        LOGGER.debug(
            "[%s] Updating device %s.",
            "climate",
            self._device.serial_number,
        )
        status = await self._device.status()
        match status:
            case Success(data):
                LOGGER.debug(
                    "[%s] Updating device %s: operating_mode=%s humidity=%s fan_speed=%s humidity_level=%s",
                    "climate",
                    self._device.serial_number,
                    data["operating_mode"],
                    data["humidity"],
                    data["fan_speed"],
                    data["humidity_level"],
                )
                self._status = data
            case Failure(error):
                LOGGER.error(
                    "[%s] Updating device %s: failed. %s",
                    "climate",
                    self._device.serial_number,
                    error,
                )
                self._status = None
