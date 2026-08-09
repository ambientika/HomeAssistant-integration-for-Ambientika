"""A demonstration 'hub' that connects several devices.

References:
 - https://developers.home-assistant.io/docs/integration_fetching_data/#coordinated-single-api-poll-for-data-for-all-entities

"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from ambientika_py import Device, DeviceStatus
from returns.result import Failure, Success

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


from .api import (
    AmbientikaApiClient,
    AmbientikaApiClientAuthenticationError,
    AmbientikaApiClientError,
)
from .const import DOMAIN, LOGGER


MISSING_STATUS_PACKET = "Status packet not found!"


def _is_missing_status_packet(error: object) -> bool:
    """Return whether an API error is the expected offline-device response."""
    return (
        isinstance(error, dict)
        and error.get("status_code") == 404
        and error.get("data") == MISSING_STATUS_PACKET
    )


def _is_authentication_error(error: object) -> bool:
    """Return whether an API error indicates invalid authentication."""
    return isinstance(error, dict) and error.get("status_code") == 401


class AmbientikaHub(DataUpdateCoordinator[dict[str, DeviceStatus | None]]):
    """Connection Hub to all devices."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config: Mapping[str, Any]) -> None:
        """Initialize the hub to manage all devices and the API facade."""
        self._hass_config = hass
        self._hass = hass
        self._credentials = {
            "username": config.get(CONF_USERNAME, ""),
            "password": config.get(CONF_PASSWORD, ""),
        }
        self.devices: list[Device] = []
        self._device_errors: dict[str, str] = {}

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

    async def _async_update_data(self) -> dict[str, DeviceStatus | None]:
        """Fetch each known device status exactly once."""
        LOGGER.debug("Fetching Ambientika device statuses.")
        statuses: dict[str, DeviceStatus | None] = {}

        for device in self.devices:
            serial_number = device.serial_number

            try:
                result = await device.status()
            except AmbientikaApiClientAuthenticationError as exception:
                raise ConfigEntryAuthFailed(exception) from exception
            except AmbientikaApiClientError as exception:
                statuses[serial_number] = None
                self._report_device_error(serial_number, exception)
                continue
            except Exception as exception:
                statuses[serial_number] = None
                self._report_device_error(serial_number, exception)
                continue

            match result:
                case Success(status):
                    statuses[serial_number] = status
                    self._report_device_recovery(serial_number)
                case Failure(error) if _is_missing_status_packet(error):
                    statuses[serial_number] = None
                    self._report_missing_status(serial_number)
                case Failure(error) if _is_authentication_error(error):
                    raise ConfigEntryAuthFailed(
                        "Ambientika authentication failed while fetching device status"
                    )
                case Failure(error):
                    statuses[serial_number] = None
                    self._report_device_error(serial_number, error)
                case _:
                    statuses[serial_number] = None
                    self._report_device_error(
                        serial_number, TypeError("Unexpected status response")
                    )

        return statuses

    def _report_missing_status(self, serial_number: str) -> None:
        """Record the expected missing-packet state without recurring errors."""
        if self._device_errors.get(serial_number) == "missing_status":
            return

        self._device_errors[serial_number] = "missing_status"
        LOGGER.debug(
            "Ambientika device %s is unavailable because no status packet is present",
            self._masked_serial(serial_number),
        )

    def _report_device_error(self, serial_number: str, error: object) -> None:
        """Log an unexpected per-device error once per error state."""
        if isinstance(error, dict):
            status_code = error.get("status_code")
            error_state = f"http:{status_code}"
            description = f"HTTP {status_code}"
        else:
            error_state = f"exception:{type(error).__name__}"
            description = type(error).__name__

        if self._device_errors.get(serial_number) == error_state:
            return

        self._device_errors[serial_number] = error_state
        LOGGER.warning(
            "Could not fetch status for Ambientika device %s (%s)",
            self._masked_serial(serial_number),
            description,
        )

    def _report_device_recovery(self, serial_number: str) -> None:
        """Log a device recovery once after a recorded error state."""
        if self._device_errors.pop(serial_number, None) is None:
            return

        LOGGER.info(
            "Ambientika device %s is available again",
            self._masked_serial(serial_number),
        )

    @staticmethod
    def _masked_serial(serial_number: str) -> str:
        """Return a short non-identifying serial suffix for logs."""
        return f"...{serial_number[-4:]}" if serial_number else "unknown"
