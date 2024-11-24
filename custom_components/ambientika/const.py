"""Constants for ambientika."""

from enum import StrEnum
from logging import Logger, getLogger


LOGGER: Logger = getLogger(__package__)

NAME = "Ambientika"
DOMAIN = "ambientika"
VERSION = "1.0.0"

DEFAULT_HOST = "https://app.ambientika.eu:4521"  # This is the default from ambientika_py. I am not aware of other values yet.

# ORDERED_NAMED_FAN_SPEEDS = [name for name, _ in FanSpeed.__members__.items()]
# ORDERED_NAMED_HUMIDITY_LEVELS = [name for name, _ in HumidityLevel.__members__.items()]


class FilterStatus(StrEnum):
    """The filter status of the device."""

    Bad = "bad"
    Medium = "medium"
    Good = "good"


class AirQuality(StrEnum):
    """The air quality of the device."""

    VeryGood = "very_good"
    Good = "good"
    Medium = "medium"
    Poor = "poor"
    Bad = "bad"
