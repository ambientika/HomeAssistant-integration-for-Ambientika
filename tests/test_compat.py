"""Tests for the FanSpeed.Night compatibility shim (no Home Assistant needed)."""

import importlib.util
import pathlib
import types
import unittest
from enum import IntEnum

_PATH = pathlib.Path(__file__).parents[1] / "custom_components" / "ambientika" / "compat.py"
_spec = importlib.util.spec_from_file_location("ambientika_compat", _PATH)
compat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compat)


def _fake_library(with_night: bool) -> types.ModuleType:
    """A stand-in for ambientika_py whose status parsing looks FanSpeed up at call time."""
    module = types.ModuleType("ambientika_py_fake")
    members = {"Low": 0, "Medium": 1, "High": 2}
    if with_night:
        members["Night"] = 3
    module.FanSpeed = IntEnum("FanSpeed", members)

    def parse(data):  # mirrors Device.status(): FanSpeed[data["fanSpeed"]]
        return module.FanSpeed[data["fanSpeed"]]

    module.parse = parse
    return module


class EnsureNightFanSpeedTest(unittest.TestCase):
    def test_unpatched_library_raises(self):
        lib = _fake_library(with_night=False)
        with self.assertRaises(KeyError):
            lib.parse({"fanSpeed": "Night"})

    def test_patch_adds_night_and_keeps_existing_values(self):
        lib = _fake_library(with_night=False)
        self.assertTrue(compat.ensure_night_fan_speed(lib))
        self.assertEqual(lib.parse({"fanSpeed": "Night"}).value, 3)
        self.assertEqual(lib.parse({"fanSpeed": "Medium"}).value, 1)
        self.assertEqual([m.name for m in lib.FanSpeed], ["Low", "Medium", "High", "Night"])

    def test_noop_when_library_already_fixed(self):
        lib = _fake_library(with_night=True)
        original = lib.FanSpeed
        self.assertFalse(compat.ensure_night_fan_speed(lib))
        self.assertIs(lib.FanSpeed, original)

    def test_idempotent(self):
        lib = _fake_library(with_night=False)
        compat.ensure_night_fan_speed(lib)
        patched = lib.FanSpeed
        self.assertFalse(compat.ensure_night_fan_speed(lib))
        self.assertIs(lib.FanSpeed, patched)

    def test_old_and_new_members_compare_equal(self):
        # Mappings built from the original enum still match values parsed after the patch.
        lib = _fake_library(with_night=False)
        old_low = lib.FanSpeed.Low
        compat.ensure_night_fan_speed(lib)
        self.assertEqual({old_low: "low"}.get(lib.parse({"fanSpeed": "Low"})), "low")


if __name__ == "__main__":
    unittest.main()
