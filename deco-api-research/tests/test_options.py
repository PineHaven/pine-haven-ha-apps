import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from deco_research.options import MonitorOptions, OptionsError, normalize_mac


class MonitorOptionsTests(unittest.TestCase):
    def test_disabled_monitor_needs_no_target(self):
        options = MonitorOptions.from_dict({"monitoring_enabled": False})
        self.assertFalse(options.monitoring_enabled)
        self.assertIsNone(options.host)
        self.assertEqual(options.poll_interval_seconds, 60)
        self.assertTrue(options.publish_to_home_assistant)

    def test_enabled_monitor_requires_all_connection_values(self):
        with self.assertRaisesRegex(OptionsError, "requires_target"):
            MonitorOptions.from_dict(
                {
                    "monitoring_enabled": True,
                    "exclusive_session_acknowledged": True,
                }
            )

    def test_enabled_monitor_requires_exclusive_session_acknowledgement(self):
        with self.assertRaisesRegex(OptionsError, "exclusive_session"):
            MonitorOptions.from_dict(
                {
                    "monitoring_enabled": True,
                    "host": "https://deco.invalid",
                    "username": "operator",
                    "password": "secret",
                }
            )

    def test_target_must_not_embed_credentials(self):
        with self.assertRaisesRegex(OptionsError, "must_not_contain_credentials"):
            MonitorOptions.from_dict(
                {
                    "monitoring_enabled": True,
                    "host": "https://operator:secret@deco.invalid",
                    "username": "operator",
                    "password": "secret",
                    "exclusive_session_acknowledged": True,
                }
            )

    def test_target_must_not_select_an_arbitrary_path(self):
        with self.assertRaisesRegex(OptionsError, "must_not_contain_path"):
            MonitorOptions.from_dict(
                {
                    "monitoring_enabled": True,
                    "host": "https://deco.invalid/admin",
                    "username": "operator",
                    "password": "secret",
                    "exclusive_session_acknowledged": True,
                }
            )

    def test_poll_interval_is_bounded(self):
        with self.assertRaisesRegex(OptionsError, "out_of_range"):
            MonitorOptions.from_dict({"poll_interval_seconds": 29})

    def test_node_aliases_are_normalized(self):
        options = MonitorOptions.from_dict(
            {"node_aliases_json": '{"aa:bb:cc:dd:ee:ff":"Living Room"}'}
        )
        self.assertEqual(
            options.node_aliases,
            {"AA-BB-CC-DD-EE-FF": "Living Room"},
        )
        self.assertEqual(normalize_mac("aa:bb:cc:dd:ee:ff"), "AA-BB-CC-DD-EE-FF")


if __name__ == "__main__":
    unittest.main()
