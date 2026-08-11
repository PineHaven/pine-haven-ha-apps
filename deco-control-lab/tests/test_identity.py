import unittest

from deco_lab.identity import radio_snapshot, verify_single_lab_node


EXPECTED = "02-00-00-00-00-23"


def node(mac="02:00:00:00:00:23", role="master", status="connected"):
    return {
        "mac": mac,
        "role": role,
        "group_status": status,
        "device_model": "M9Plus",
        "hardware_ver": "2.0",
        "software_ver": "1.9.1",
    }


class IdentityTests(unittest.TestCase):
    def test_exactly_one_expected_controller_is_ready(self):
        result = verify_single_lab_node([node()], EXPECTED)
        self.assertTrue(result["ready"])
        self.assertEqual(result["node_count"], 1)
        self.assertTrue(result["model_supported"])
        self.assertTrue(result["hardware_supported"])
        self.assertNotIn(EXPECTED, str(result))

    def test_extra_node_blocks_the_gate(self):
        result = verify_single_lab_node([node(), node("00:11:22:33:44:55")], EXPECTED)
        self.assertFalse(result["ready"])
        self.assertFalse(result["single_node"])

    def test_wrong_identity_blocks_the_gate(self):
        result = verify_single_lab_node([node("00:11:22:33:44:55")], EXPECTED)
        self.assertFalse(result["ready"])
        self.assertFalse(result["expected_identity_match"])

    def test_wrong_hardware_blocks_the_gate(self):
        record = node()
        record["hardware_ver"] = "1.0"
        result = verify_single_lab_node([record], EXPECTED)
        self.assertFalse(result["ready"])
        self.assertFalse(result["hardware_supported"])

    def test_radio_snapshot_keeps_only_control_fields(self):
        raw = {
            "band2_4": {
                "host": {
                    "channel": "4",
                    "bandwidth": "HT40+",
                    "auto_channel": False,
                    "ssid": "must-not-leak",
                    "password": "must-not-leak",
                }
            }
        }
        result = radio_snapshot(raw)
        self.assertEqual(
            result,
            {
                "channel": 4,
                "bandwidth": "HT40",
                "automatic_channel": False,
                "automatic_width": None,
            },
        )
        self.assertNotIn("must-not-leak", str(result))
