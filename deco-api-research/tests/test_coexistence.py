import unittest

from deco_research.coexistence import build_coexistence_diagnostics


class CoexistenceDiagnosticsTests(unittest.TestCase):
    def test_current_channel_four_at_40mhz_flags_core_and_extension_risks(self):
        result = build_coexistence_diagnostics(
            {
                "channel": 4,
                "configured_width_mhz": 40,
                "firmware_width_token": "HT40",
                "automatic_channel": False,
            }
        )

        current = result["current"]
        by_id = {row["id"]: row for row in current["zigbee_networks"]}
        self.assertEqual(current["risk"], "high")
        self.assertEqual(by_id["core"]["risk"], "primary_overlap")
        self.assertEqual(
            by_id["ambience"]["risk"], "possible_40mhz_extension"
        )
        self.assertEqual(
            by_id["perimeter"]["risk"], "possible_40mhz_extension"
        )
        self.assertEqual(current["firmware_width_token"], "HT40")

    def test_width_only_plan_removes_extensions_but_not_core_overlap(self):
        result = build_coexistence_diagnostics(
            {"channel": 4, "configured_width_mhz": 40}
        )

        width_only = result["width_only_20mhz"]
        self.assertEqual(width_only["possible_extension_exposures_removed"], 2)
        self.assertTrue(width_only["core_direct_overlap_remains"])

    def test_candidate_ranking_is_geometry_only_and_control_stays_disarmed(self):
        result = build_coexistence_diagnostics(
            {"channel": 4, "configured_width_mhz": 40}
        )
        candidates = result["candidate_plans"]

        self.assertEqual(candidates[0]["id"], "protect_core_and_perimeter")
        self.assertEqual(candidates[0]["geometry_rank"], 1)
        self.assertFalse(result["control_readiness"]["writes_enabled"])
        self.assertEqual(result["control_readiness"]["state"], "disarmed")
        self.assertEqual(
            result["control_readiness"]["firmware_contract"][
                "known_bandwidth_tokens"
            ],
            ["HT20", "HT40"],
        )

    def test_unknown_radio_values_fail_closed(self):
        result = build_coexistence_diagnostics({})

        self.assertEqual(result["current"]["risk"], "unknown")
        self.assertIsNone(result["width_only_20mhz"]["assessment"])


if __name__ == "__main__":
    unittest.main()
