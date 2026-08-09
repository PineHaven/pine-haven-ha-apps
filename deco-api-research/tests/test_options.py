import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from deco_research.options import OptionsError, ProbeOptions


class ProbeOptionsTests(unittest.TestCase):
    def test_disarmed_probe_needs_no_target(self):
        options = ProbeOptions.from_dict({"probe_enabled": False})
        self.assertFalse(options.probe_enabled)
        self.assertIsNone(options.host)

    def test_armed_probe_requires_all_connection_values(self):
        with self.assertRaisesRegex(OptionsError, "requires_target"):
            ProbeOptions.from_dict(
                {
                    "probe_enabled": True,
                    "exclusive_session_acknowledged": True,
                }
            )

    def test_armed_probe_requires_exclusive_session_acknowledgement(self):
        with self.assertRaisesRegex(OptionsError, "exclusive_session"):
            ProbeOptions.from_dict(
                {
                    "probe_enabled": True,
                    "host": "https://deco.invalid",
                    "username": "operator",
                    "password": "secret",
                }
            )

    def test_target_must_not_embed_credentials(self):
        with self.assertRaisesRegex(OptionsError, "must_not_contain_credentials"):
            ProbeOptions.from_dict(
                {
                    "probe_enabled": True,
                    "host": "https://operator:secret@deco.invalid",
                    "username": "operator",
                    "password": "secret",
                    "exclusive_session_acknowledged": True,
                }
            )

    def test_target_must_not_select_an_arbitrary_path(self):
        with self.assertRaisesRegex(OptionsError, "must_not_contain_path"):
            ProbeOptions.from_dict(
                {
                    "probe_enabled": True,
                    "host": "https://deco.invalid/admin",
                    "username": "operator",
                    "password": "secret",
                    "exclusive_session_acknowledged": True,
                }
            )


if __name__ == "__main__":
    unittest.main()
