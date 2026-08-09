"""Shared entity support for Ambientika devices."""

from __future__ import annotations

from ambientika_py import Device, DeviceStatus

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .hub import AmbientikaHub


class AmbientikaCoordinatorEntity(CoordinatorEntity[AmbientikaHub]):
    """Base entity backed by the shared Ambientika coordinator status."""

    def __init__(self, coordinator: AmbientikaHub, device: Device) -> None:
        """Initialize an entity for an Ambientika device."""
        super().__init__(coordinator)
        self._device = device

    @property
    def device_status(self) -> DeviceStatus | None:
        """Return the latest shared status for this device."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._device.serial_number)

    @property
    def _status(self) -> DeviceStatus | None:
        """Provide the shared status to existing entity properties."""
        return self.device_status

    @property
    def available(self) -> bool:
        """Return whether the coordinator and this device status are available."""
        return super().available and self.device_status is not None
