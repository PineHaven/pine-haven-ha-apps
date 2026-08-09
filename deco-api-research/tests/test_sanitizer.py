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
                "connection_type": ["wired", "band5"],
                "is_wired": True,
                "eth_bkhl_ports": ["sensitive-port-id"],
                "wired_port_list": ["sensitive-wired-port-id"],
                "backhual_speed": "1000",
                "backhual_max_speed": "1200",
                "signal_level": {"band2_4": 4, "band5": 3},
                "inet_status": "online",
                "inet_error_msg": "",
            },
            {
                "group_status": "disconnected",
                "role": "slave",
                "connection_type": [],
                "is_wired": False,
                "backhual_speed": "sensitive-unparsed-speed",
                "backhual_max_speed": "sensitive-unparsed-maximum",
                "signal_level": {"band2_4": 2, "band5": 1},
                "inet_status": "offline",
                "inet_error_msg": "sensitive-internet-error",
            }
        ]
        result = build_snapshot(
            devices,
            {"result": {"cpu_usage": 0.25, "mem_usage": 0.5}},
            [
                {
                    "name": "sensitive-client-name",
                    "mac": "sensitive-client-id",
                    "ip": "sensitive-client-address",
                    "online": True,
                    "connection_type": "band5",
                    "interface": "main",
                    "client_mesh": True,
                    "enable_priority": True,
                    "remain_time": 90,
                    "down_speed": 800,
                    "up_speed": "80",
                },
                {
                    "name": "second-sensitive-client-name",
                    "online": True,
                    "connection_type": "wired",
                    "interface": "iot",
                    "client_mesh": False,
                    "enable_priority": False,
                    "remain_time": 0,
                    "down_speed": 200,
                    "up_speed": "sensitive-unparsed-upload",
                }
            ],
        )
        serialized = json.dumps(result)

        for secret in (
            "sensitive-hardware-id",
            "sensitive-network-address",
            "sensitive-room-name",
            "sensitive-radio-id",
            "sensitive-client-name",
            "sensitive-client-id",
            "sensitive-client-address",
            "sensitive-port-id",
            "sensitive-wired-port-id",
            "sensitive-unparsed-speed",
            "sensitive-unparsed-maximum",
            "sensitive-internet-error",
            "second-sensitive-client-name",
            "sensitive-unparsed-upload",
        ):
            self.assertNotIn(secret, serialized)

        self.assertEqual(result["node_count"], 2)
        self.assertEqual(result["online_count"], 1)
        self.assertEqual(result["controller_performance"]["cpu_percent"], 25.0)
        self.assertEqual(result["connection_types"], {"band5": 1, "wired": 1})
        self.assertEqual(
            result["mesh_health"]["backhaul"]["wired_status"],
            {"wired": 1, "wireless": 1},
        )
        self.assertEqual(
            result["mesh_health"]["backhaul"]["speed"],
            {
                "sample_count": 1,
                "nonzero_count": 1,
                "unparsed_count": 1,
                "total": 1000.0,
                "average": 1000.0,
                "minimum": 1000.0,
                "maximum": 1000.0,
            },
        )
        self.assertEqual(
            result["mesh_health"]["signal"]["band5"]["average"], 2.0
        )
        self.assertEqual(
            result["mesh_health"]["internet"]["states"],
            {"offline": 1, "online": 1},
        )
        self.assertEqual(
            result["mesh_health"]["internet"]["nonempty_error_field_count"],
            1,
        )
        self.assertEqual(result["connected_clients"]["reported_count"], 2)
        self.assertEqual(
            result["connected_clients"]["connection_types"],
            {"band5": 1, "wired": 1},
        )
        self.assertEqual(
            result["connected_clients"]["interfaces"], {"iot": 1, "main": 1}
        )
        self.assertEqual(
            result["connected_clients"]["mesh_membership"],
            {"false": 1, "true": 1},
        )
        self.assertEqual(
            result["connected_clients"]["priority"],
            {"false": 1, "true": 1},
        )
        self.assertEqual(
            result["connected_clients"]["restrictions"],
            {"active": 1, "inactive": 1},
        )
        self.assertEqual(
            result["connected_clients"]["traffic"]["download"]["total"],
            1000.0,
        )
        self.assertEqual(
            result["connected_clients"]["traffic"]["upload"]["unparsed_count"],
            1,
        )
        self.assertEqual(
            result["observed_fields"]["device_records"]["signal_level"],
            ["object"],
        )
        self.assertEqual(
            result["observed_fields"]["client_records"]["mac"], ["string"]
        )
        self.assertEqual(
            result["observed_fields"]["performance_result"]["cpu_usage"],
            ["number"],
        )

    def test_invalid_performance_values_are_not_forwarded(self):
        result = build_snapshot([], {"result": {"cpu_usage": "raw-secret"}})
        self.assertIsNone(result["controller_performance"]["cpu_percent"])

    def test_unexpected_telemetry_values_are_counted_not_returned(self):
        result = build_snapshot(
            [
                {
                    "backhual_speed": "unexpected-sensitive-text",
                    "signal_level": {"band2_4": "unexpected-sensitive-signal"},
                    "inet_status": "unexpected-sensitive-status",
                    "inet_error_msg": "unexpected-sensitive-error",
                }
            ],
            {},
            [
                {
                    "down_speed": float("inf"),
                    "up_speed": "unexpected-sensitive-traffic",
                    "remain_time": "unexpected-sensitive-restriction",
                }
            ],
        )
        serialized = json.dumps(result)

        self.assertNotIn("unexpected-sensitive", serialized)
        self.assertEqual(
            result["mesh_health"]["backhaul"]["speed"]["unparsed_count"], 1
        )
        self.assertEqual(
            result["mesh_health"]["signal"]["band2_4"]["unparsed_count"], 1
        )
        self.assertEqual(
            result["connected_clients"]["traffic"]["download"]["unparsed_count"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
