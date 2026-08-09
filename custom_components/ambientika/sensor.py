"""Sensor platform for ambientika.

References:
 - https://github.com/ludeeus/integration_blueprint/blob/main/custom_components/integration_blueprint/sensor.py
 - https://github.com/home-assistant/example-custom-config/blob/master/custom_components/detailed_hello_world_push/sensor.py
  https://github.com/DeebotUniverse/Deebot-4-Home-Assistant/blob/dev/custom_components/deebot/sensor.py

"""

from __future__ import annotations

from ambientika_py import Device

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor.const import SensorDeviceClass

from .const import DOMAIN, AirQuality, FilterStatus
from .entity import AmbientikaCoordinatorEntity
from .hub import AmbientikaHub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the `sensor` entities for each device."""
    hub: AmbientikaHub = hass.data[DOMAIN][entry.entry_id]

    # TODO: this could be simplified with ENTITY_DESCTIPTIONS, but requires event subscription
    # https://github.com/DeebotUniverse/Deebot-4-Home-Assistant/blob/dev/custom_components/deebot/sensor.py#L79
    # async_add_entities(TemperatureSensor(hub, device) for device in hub.devices)
    # async_add_entities(HumiditySensor(hub, device) for device in hub.devices)
    async_add_entities(AirQualitySensor(hub, device) for device in hub.devices)
    async_add_entities(FilterStatusSensor(hub, device) for device in hub.devices)


class SensorBase(AmbientikaCoordinatorEntity):
    """Base representation of an Ambientika Sensor."""

    # TODO:
    # should_poll = False

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)

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

class TemperatureSensor(SensorBase):
    """Sensor for the Air Quality status."""

    _attr_has_entity_name = True
    _attr_translation_key = "temperature"
    # _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_unit_of_measurement = "°C"

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device.name}_temperature"

    @property
    def state(self):
        """State of the sensor."""
        if self._status:
            return self._status["temperature"]


class HumiditySensor(SensorBase):
    """Sensor for the Air Quality status."""

    _attr_has_entity_name = True
    _attr_translation_key = "humidity"
    # _attr_icon = "mdi:air-purifier"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_unit_of_measurement = "%"

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device.name}_humidity"

    @property
    def state(self):
        """State of the sensor."""
        if self._status:
            return self._status["humidity"]


class AirQualitySensor(SensorBase):
    """Sensor for the Air Quality status."""

    _attr_has_entity_name = True
    _attr_translation_key = "air_quality"
    _attr_icon = "mdi:air-purifier"

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device.name}_air_quality"

    @property
    def state(self):
        """State of the sensor."""
        if self._status:
            return AirQuality[self._status["air_quality"]]


class FilterStatusSensor(SensorBase):
    """Sensor for the Filter Status."""

    _attr_has_entity_name = True
    _attr_translation_key = "filter_status"
    _attr_icon = "mdi:air-filter"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._device.name}_filter_status"

    @property
    def state(self):
        """State of the sensor."""
        if self._status:
            return FilterStatus[self._status["filters_status"]]

    @property
    def options(self):
        """Return the list of available options."""
        return [name for name, _ in FilterStatus.__members__.items()]
