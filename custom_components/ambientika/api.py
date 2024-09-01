"""API Client.

This uses https://pypi.org/project/ambientika/ as a facade.
Ambientika API: https://app.ambientika.eu:4521/swagger/index.html.
"""

from returns.result import Failure
from returns.primitives.exceptions import UnwrapFailedError


from ambientika_py import authenticate, Device

from .const import DEFAULT_HOST, LOGGER


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

    async def async_get_data(self) -> list[Device]:
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
                "Server can't be reached or Invalid credentials"
            ) from exception  # no idea if the UnwrapFilaedError should be used here.

        LOGGER.debug("fetching houses.")
        houses = await api_client.houses()
        if isinstance(houses, Failure):
            raise AmbientikaApiClientError("Ambientika does not have houses set up")

        try:
            # TODO: write tests
            LOGGER.debug("fetching devices.")
            return [
                # AmbientikaEntity(device)
                device
                for house in houses.unwrap()
                for room in house.rooms
                for device in room.devices
            ]
        except UnwrapFailedError as exception:
            raise AmbientikaApiClientError("Could not fetch devices") from exception
        except Exception as exception:
            raise AmbientikaApiClientError("Unknown error") from exception
