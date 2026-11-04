"""Compatibility shims for the ambientika_py library.

``ambientika_py`` <= 0.0.6 has no ``FanSpeed.Night``. While a unit runs in Night mode the cloud
API reports ``"fanSpeed": "Night"``, so ``Device.status()`` raises ``KeyError: 'Night'`` and
every entity of that unit stops updating. The enum member was added upstream in
wingertge/ambientika-py#9 (merged 2026-09-08) but is not released on PyPI yet.

``ensure_night_fan_speed()`` adds the member at runtime, mirroring the upstream fix exactly
(``Night = 3``). It is a no-op as soon as an installed ambientika_py already knows ``Night``,
so it can stay in place until the requirement is bumped, and then be deleted.
"""

from __future__ import annotations

from enum import IntEnum
from types import ModuleType


def ensure_night_fan_speed(module: ModuleType) -> bool:
    """Make ``module.FanSpeed`` include ``Night = 3``. Return True if it was patched."""
    fan_speed = module.FanSpeed
    if "Night" in fan_speed.__members__:
        return False
    members = {name: member.value for name, member in fan_speed.__members__.items()}
    members["Night"] = 3
    module.FanSpeed = IntEnum("FanSpeed", members)
    return True
