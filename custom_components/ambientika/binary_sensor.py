"""Binary sensor platform for ambientika."""

from __future__ import annotations

from ambientika_py import Device, DeviceStatus
from returns.result import Failure, Success

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .hub import AmbientikaHub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the `binary_sensor` entities for each device."""
    hub: AmbientikaHub = hass.data[DOMAIN][entry.entry_id]

    # TODO: this could be simplified with ENTITY_DESCTIPTIONS, but requires event subscription
    # https://github.com/DeebotUniverse/Deebot-4-Home-Assistant/blob/dev/custom_components/deebot/sensor.py#L79
    async_add_entities(HumidityAlarmBinarySensor(device) for device in hub.devices)
    async_add_entities(NightAlarmBinarySensor(device) for device in hub.devices)


class BinarySensorBase(BinarySensorEntity):
    """Base representation of an Ambientika Sensor."""

    # TODO:
    # should_poll = False

    def __init__(self, device: Device) -> None:
        """Initialize the sensor."""
        self._device = device
        self._status: DeviceStatus | None = None

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

    # TODO: move this to a common base class shared with climate.py
    async def async_update(self) -> None:
        """Fetch new state data for this device."""
        LOGGER.debug(
            "Updating binary sensor entity for device %s", self._device.serial_number
        )
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


class HumidityAlarmBinarySensor(BinarySensorBase):
    """Humidity Alarm Binary Sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "humidity_alarm"
    _attr_icon = "mdi:alarm-light"

    def __init__(self, device) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._attr_unique_id = f"{self._device.name}_humidity_alarm"
        LOGGER.debug(f"Creating AmbientikaBinarySensor: {self._device.name}")

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        if self._status:
            return self._status["humidity_alarm"] is True


class NightAlarmBinarySensor(BinarySensorBase):
    """Humidity Alarm Binary Sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "night_alarm"
    _attr_icon = "mdi:alarm-light"

    def __init__(self, device) -> None:
        """Initialize the sensor."""
        super().__init__(device)
        self._attr_unique_id = f"{self._device.name}_night_alarm"
        LOGGER.debug(f"Creating AmbientikaBinarySensor: {self._device.name}")

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        if self._status:
            return self._status["night_alarm"] is True
