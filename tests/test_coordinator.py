"""Tests for shared Ambientika device status coordination."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from ambientika_py import FanSpeed, HumidityLevel, OperatingMode
from returns.result import Failure, Success

from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.ambientika.binary_sensor import HumidityAlarmBinarySensor
from custom_components.ambientika.climate import AmbientikaClimate
from custom_components.ambientika.const import LOGGER
from custom_components.ambientika.hub import AmbientikaHub
from custom_components.ambientika.sensor import AirQualitySensor


def _device(serial_number: str, result: object) -> SimpleNamespace:
    """Create a minimal device with a mocked status method."""
    return SimpleNamespace(
        serial_number=serial_number,
        name=f"Device {serial_number}",
        status=AsyncMock(return_value=result),
        change_mode=AsyncMock(),
    )


def _status(serial_number: str) -> dict:
    """Return a representative device status packet."""
    return {
        "operating_mode": OperatingMode.Auto,
        "fan_speed": FanSpeed.Low,
        "humidity_level": HumidityLevel.Normal,
        "temperature": 21,
        "humidity": 45,
        "air_quality": "Good",
        "filters_status": "Good",
        "humidity_alarm": False,
        "night_alarm": False,
        "device_serial_number": serial_number,
    }


def _hub(*devices: SimpleNamespace) -> AmbientikaHub:
    """Create a coordinator instance without starting Home Assistant."""
    hub = object.__new__(AmbientikaHub)
    hub.devices = list(devices)
    hub._device_errors = {}
    return hub


class _EntityCoordinator:
    """Minimal coordinator surface used by CoordinatorEntity."""

    def __init__(self, data: dict) -> None:
        self.data = data
        self.last_update_success = True
        self.async_request_refresh = AsyncMock()


class AmbientikaCoordinatorTest(IsolatedAsyncioTestCase):
    """Verify status polling, error classification, and entity behavior."""

    async def test_one_status_request_is_shared_by_all_entities(self) -> None:
        """Fetch once and expose the same status object to every entity type."""
        status = _status("SERIAL-A")
        device = _device("SERIAL-A", Success(status))
        hub = _hub(device)

        data = await hub._async_update_data()
        coordinator = _EntityCoordinator(data)
        entities = (
            AmbientikaClimate(coordinator, device),
            AirQualitySensor(coordinator, device),
            HumidityAlarmBinarySensor(coordinator, device),
        )

        device.status.assert_awaited_once_with()
        for entity in entities:
            self.assertIs(entity.device_status, status)
            self.assertTrue(entity.available)

    async def test_missing_packet_makes_entities_unavailable_without_error(self) -> None:
        """Treat the documented missing packet response as an offline device."""
        device = _device(
            "SERIAL-A",
            Failure({"status_code": 404, "data": "Status packet not found!"}),
        )
        hub = _hub(device)

        with self.assertNoLogs(LOGGER.name, level="ERROR"):
            data = await hub._async_update_data()

        entity = AmbientikaClimate(_EntityCoordinator(data), device)
        self.assertIsNone(data["SERIAL-A"])
        self.assertFalse(entity.available)

    async def test_online_device_updates_when_another_device_is_offline(self) -> None:
        """Keep successful device data when a second device has no packet."""
        online_status = _status("SERIAL-A")
        online = _device("SERIAL-A", Success(online_status))
        offline = _device(
            "SERIAL-B",
            Failure({"status_code": 404, "data": "Status packet not found!"}),
        )
        hub = _hub(online, offline)

        data = await hub._async_update_data()

        self.assertIs(data["SERIAL-A"], online_status)
        self.assertIsNone(data["SERIAL-B"])
        online.status.assert_awaited_once_with()
        offline.status.assert_awaited_once_with()

    async def test_device_recovers_on_the_next_refresh(self) -> None:
        """Replace an offline value when the status packet returns."""
        status = _status("SERIAL-A")
        device = _device("SERIAL-A", Success(status))
        device.status.side_effect = [
            Failure({"status_code": 404, "data": "Status packet not found!"}),
            Success(status),
        ]
        hub = _hub(device)

        first_data = await hub._async_update_data()
        with self.assertLogs(LOGGER.name, level="INFO") as logs:
            second_data = await hub._async_update_data()

        self.assertIsNone(first_data["SERIAL-A"])
        self.assertIs(second_data["SERIAL-A"], status)
        self.assertEqual(device.status.await_count, 2)
        self.assertEqual(len(logs.output), 1)

    async def test_other_api_error_is_reported_once(self) -> None:
        """Keep unexpected server failures visible without recurring warnings."""
        device = _device(
            "SERIAL-A", Failure({"status_code": 500, "data": "Server error"})
        )
        hub = _hub(device)

        with self.assertLogs(LOGGER.name, level="WARNING") as logs:
            first_data = await hub._async_update_data()
            second_data = await hub._async_update_data()

        self.assertIsNone(first_data["SERIAL-A"])
        self.assertIsNone(second_data["SERIAL-A"])
        self.assertEqual(len(logs.output), 1)
        self.assertIn("HTTP 500", logs.output[0])

    async def test_authentication_failure_requests_reauthentication(self) -> None:
        """Raise the Home Assistant authentication exception for HTTP 401."""
        device = _device(
            "SERIAL-A", Failure({"status_code": 401, "data": "Unauthorized"})
        )
        hub = _hub(device)

        with self.assertRaises(ConfigEntryAuthFailed):
            await hub._async_update_data()

    async def test_successful_write_requests_shared_refresh(self) -> None:
        """Refresh the coordinator after a successful device write."""
        status = _status("SERIAL-A")
        device = _device("SERIAL-A", Success(status))
        device.change_mode.return_value = Success(None)
        coordinator = _EntityCoordinator({"SERIAL-A": status})
        entity = AmbientikaClimate(coordinator, device)

        await entity.async_set_device(operation_mode="Off")

        device.change_mode.assert_awaited_once()
        coordinator.async_request_refresh.assert_awaited_once_with()
