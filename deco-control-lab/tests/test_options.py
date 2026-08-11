import unittest

from deco_lab.options import LabOptions, OptionsError


def valid_options(**changes):
    data = {
        "lab_enabled": True,
        "isolated_single_node_acknowledged": True,
        "firmware_write_compatibility_acknowledged": False,
        "writes_enabled": False,
        "host": "http://192.0.2.72",
        "production_host": "http://192.0.2.161",
        "username": "admin",
        "password": "not-a-real-secret",
        "expected_mac": "02:00:00:00:00:23",
        "verify_ssl": False,
        "hold_seconds": 60,
    }
    data.update(changes)
    return data


class LabOptionsTests(unittest.TestCase):
    def test_enabled_lab_requires_isolation_acknowledgement(self):
        with self.assertRaisesRegex(
            OptionsError, "lab_requires_isolation_acknowledgement"
        ):
            LabOptions.from_dict(
                valid_options(isolated_single_node_acknowledged=False)
            )

    def test_lab_and_production_targets_must_differ(self):
        with self.assertRaisesRegex(
            OptionsError, "lab_target_must_not_equal_production_target"
        ):
            LabOptions.from_dict(
                valid_options(production_host="http://192.0.2.72")
            )

    def test_scheme_or_port_cannot_bypass_production_host_guard(self):
        for production_host in (
            "https://192.0.2.72",
            "http://192.0.2.72:8080",
        ):
            with self.subTest(production_host=production_host), self.assertRaisesRegex(
                OptionsError, "lab_target_must_not_equal_production_target"
            ):
                LabOptions.from_dict(
                    valid_options(production_host=production_host)
                )

    def test_writes_cannot_be_enabled_while_lab_is_disabled(self):
        with self.assertRaisesRegex(OptionsError, "writes_require_enabled_lab"):
            LabOptions.from_dict(
                valid_options(
                    lab_enabled=False,
                    firmware_write_compatibility_acknowledged=True,
                    writes_enabled=True,
                )
            )

    def test_writes_require_separate_firmware_compatibility_acknowledgement(self):
        with self.assertRaisesRegex(
            OptionsError,
            "writes_require_firmware_compatibility_acknowledgement",
        ):
            LabOptions.from_dict(valid_options(writes_enabled=True))

    def test_expected_mac_is_canonicalized(self):
        options = LabOptions.from_dict(valid_options(expected_mac="0200.0000.0023"))
        self.assertEqual(options.expected_mac, "02-00-00-00-00-23")

    def test_hold_period_is_bounded(self):
        for value in (14, 301):
            with self.subTest(value=value), self.assertRaisesRegex(
                OptionsError, "hold_seconds_out_of_range"
            ):
                LabOptions.from_dict(valid_options(hold_seconds=value))
