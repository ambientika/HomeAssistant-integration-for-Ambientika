"""API Client.

This uses https://pypi.org/project/ambientika/ as a facade.
"""

from returns.result import Failure
from returns.primitives.exceptions import UnwrapFailedError

from custom_components.ambientika.const import DEFAULT_HOST, LOGGER

from ambientika_py import authenticate


class AmbientikaApiClientError(Exception):
    """Exception to indicate a general API error."""


class AmbientikaApiClientAuthenticationError(AmbientikaApiClientError):
    """Exception to indicate an authentication error."""


class AmbientikaApiClient:
    """API Client Class."""

    def __init__(self, username: str, password: str) -> None:
        """Create an instance of the API."""
        self._username = username
        self._password = password
        self._host = DEFAULT_HOST

    # @staticmethod
    # async def test_credentials(username: str, password: str) -> bool | None:
    #     """Validate credentials."""
    #     LOGGER.debug("Authenticating with Ambientika API.")
    #     api_client = await authenticate(username, password, DEFAULT_HOST)

    #     LOGGER.debug(api_client)
    #     if Failure(api_client):
    #         raise AmbientikaApiClientAuthenticationError("Invalid credentials")
    #     return True

    # async def async_get_data(self) -> list[dict[Device, DeviceStatus]]:
    async def async_get_data(self) -> list:
        """Get all devices from the API.

        The devices are flattend. Meaning, the information about rooms and houses is not made available to hass.
        """

        try:
            LOGGER.debug("Authenticating with Ambientika API.")
            authenticator = await authenticate(
                self._username, self._password, self._host
            )
            api_client = authenticator.unwrap()
        except UnwrapFailedError as exception:
            raise AmbientikaApiClientAuthenticationError(
                "Invalid credentials"
            ) from exception  # no idea if the UnwrapFilaedError should be used here.

        LOGGER.debug("fetching houses.")
        houses = await api_client.houses()
        if isinstance(houses, Failure):
            raise AmbientikaApiClientError("Ambientika does not have houses set up")

        try:
            LOGGER.debug("success.")
            # TODO: write tests
            devices = [
                device
                for house in houses.unwrap()
                for room in house.rooms
                for device in room.devices
            ]
        except UnwrapFailedError as exception:
            raise AmbientikaApiClientError("Could not fetch devices") from exception
        except Exception as exception:
            raise AmbientikaApiClientError("Unknown error") from exception

        # TODO: this part adds the status to the device. I don't know how to expose this yet.
        # devices = []
        # for device in devices:
        #     try:
        #         LOGGER.debug("fetching device status.")
        #         device_status = await device.status()
        #         devices.append(
        #             {"device_info": device, "device_state": device_status.unwrap()}
        #         )
        #     except UnwrapFailedError as _exception:
        #         LOGGER.error(
        #             "Could not fetch device status: %s", device_status.failure()
        #         )

        LOGGER.debug("success.")
        LOGGER.warning(devices)

        return devices
