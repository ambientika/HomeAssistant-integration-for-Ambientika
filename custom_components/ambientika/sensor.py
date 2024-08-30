"""Sensor platform for integration_ambientika.

References:
 - https://github.com/ludeeus/integration_blueprint/blob/main/custom_components/integration_blueprint/sensor.py
 - https://github.com/home-assistant/example-custom-config/blob/master/custom_components/detailed_hello_world_push/sensor.py
  https://github.com/DeebotUniverse/Deebot-4-Home-Assistant/blob/dev/custom_components/deebot/sensor.py

"""

from __future__ import annotations
from abc import abstractmethod

from ambientika_py import DeviceStatus
from returns.result import Failure, Success

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, LOGGER
from .hub import AmbientikaHub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the `sensor` entities for each device."""
    hub: AmbientikaHub = hass.data[DOMAIN][entry.entry_id]

    # TODO: this could be simplified with ENTITY_DESCTIPTIONS, but requires event subscription
    # https://github.com/DeebotUniverse/Deebot-4-Home-Assistant/blob/dev/custom_components/deebot/sensor.py#L79
    async_add_entities((AirQualitySensor(device) for device in hub.devices), True)
    async_add_entities((FilterStatusSensor(device) for device in hub.devices), True)


class SensorBase(Entity):
    """Base representation of an Ambientika Sensor."""

    # TODO:
    # should_poll = False

    def __init__(self, device) -> None:
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

    @property
    def available(self) -> bool:
        """Return False if we can't resolve the device's status."""
        return self._status is not None

    @property
    @abstractmethod
    def _attr_key(self) -> str:
        """Force the implementation of this property in the child class."""
        pass

    @property
    def state(self):
        """Generic imeplentation to return the state of the sensor.

        This requires `_attr_key` to be implemented in the child class.
        """
        if self._status:
            return self._status[self._attr_key]

    # TODO: move this to a common base class shared with climate.py
    async def async_update(self) -> None:
        """Fetch new state data for this device."""
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


class AirQualitySensor(SensorBase):
    """Sensor representation."""

    _attr_key = "air_quality"  # type: ignore

    def __init__(self, device):
        """Initialize the sensor."""
        super().__init__(device)

        self._attr_unique_id = f"{self._device.name}_air_quality"
        self._attr_name = f"{self._device.name} Air Quality"
        self._attr_icon = "mdi:air-purifier"


class FilterStatusSensor(SensorBase):
    """Sensor representation."""

    _attr_key = "filters_status"  # type: ignore

    def __init__(self, device):
        """Initialize the sensor."""
        super().__init__(device)

        self._attr_unique_id = f"{self._device.name}_filter_status"
        self._attr_name = f"{self._device.name} Filter Status"
        self._attr_icon = "mdi:air-filter"
