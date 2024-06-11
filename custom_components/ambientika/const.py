"""Constants for ambientika."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Ambientika"
DOMAIN = "ambientika"
VERSION = "0.0.1"

DEFAULT_HOST = "https://app.ambientika.eu:4521"  # This is the default from ambientika_py. I am not aware of other values yet.
