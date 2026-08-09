import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from deco_research.sanitizer import build_snapshot


class SanitizerTests(unittest.TestCase):
    def test_snapshot_discards_identifiers_and_names(self):
        devices = [
            {
                "mac": "sensitive-hardware-id",
                "device_ip": "sensitive-network-address",
                "custom_nickname": "sensitive-room-name",
                "bssid_2g": "sensitive-radio-id",
                "device_model": "Deco Test",
                "hardware_ver": "V2",
                "software_ver": "Test Build",
                "group_status": "connected",
                "role": "master",
                "connection_type": "wired",
            }
        ]
        result = build_snapshot(
            devices,
            {"result": {"cpu_usage": 0.25, "mem_usage": 0.5}},
        )
        serialized = json.dumps(result)

        for secret in (
            "sensitive-hardware-id",
            "sensitive-network-address",
            "sensitive-room-name",
            "sensitive-radio-id",
        ):
            self.assertNotIn(secret, serialized)

        self.assertEqual(result["node_count"], 1)
        self.assertEqual(result["online_count"], 1)
        self.assertEqual(result["controller_performance"]["cpu_percent"], 25.0)

    def test_invalid_performance_values_are_not_forwarded(self):
        result = build_snapshot([], {"result": {"cpu_usage": "raw-secret"}})
        self.assertIsNone(result["controller_performance"]["cpu_percent"])


if __name__ == "__main__":
    unittest.main()
