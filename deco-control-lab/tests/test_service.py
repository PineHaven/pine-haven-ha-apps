import unittest

from deco_lab.options import LabOptions
from deco_lab.service import LabRuntime


EXPECTED = "02-00-00-00-00-23"


class FakeClient:
    def __init__(self):
        self.channel = 4
        self.bandwidth = "HT40"

    async def read_devices(self):
        return [
            {
                "mac": EXPECTED,
                "role": "master",
                "group_status": "connected",
                "device_model": "M9Plus",
                "hardware_ver": "2.0",
                "software_ver": "1.9.1",
            }
        ]

    async def read_wireless_status(self):
        return {
            "band2_4": {
                "host": {
                    "channel": self.channel,
                    "bandwidth": self.bandwidth,
                }
            }
        }

    async def apply_channel_11_ht20(self):
        self.channel = 11
        self.bandwidth = "HT20"

    async def restore_captured_radio(self, channel, bandwidth):
        self.channel = channel
        self.bandwidth = bandwidth


def options(writes_enabled=False):
    return LabOptions(
        lab_enabled=True,
        isolated_single_node_acknowledged=True,
        firmware_write_compatibility_acknowledged=writes_enabled,
        writes_enabled=writes_enabled,
        host="http://192.0.2.72",
        production_host="http://192.0.2.161",
        username="admin",
        password="not-a-real-secret",
        expected_mac=EXPECTED,
        verify_ssl=False,
        hold_seconds=0,
    )


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_only_baseline_verifies_identity_but_keeps_control_locked(self):
        runtime = LabRuntime(options(writes_enabled=False))
        fake = FakeClient()
        runtime._client = lambda _session: fake
        await runtime._refresh_baseline(object())
        status = runtime.status()
        self.assertEqual(status["mode"], "ready")
        self.assertTrue(status["identity"]["ready"])
        self.assertFalse(status["control_ready"])
        accepted, reason = runtime.request_experiment(status["intent_token"])
        self.assertFalse(accepted)
        self.assertEqual(reason, "writes_locked_in_app_options")

    async def test_experiment_applies_candidate_and_verifies_rollback(self):
        runtime = LabRuntime(options(writes_enabled=True))
        fake = FakeClient()
        runtime._client = lambda _session: fake
        await runtime._refresh_baseline(object())
        accepted, reason = runtime.request_experiment(runtime.status()["intent_token"])
        self.assertTrue(accepted)
        self.assertEqual(reason, "queued")
        await runtime._run_experiment(object())
        status = runtime.status()
        self.assertEqual(status["experiment"]["state"], "rolled_back")
        self.assertEqual(status["experiment"]["baseline"]["channel"], 4)
        self.assertEqual(status["experiment"]["candidate_readback"]["channel"], 11)
        self.assertEqual(status["experiment"]["rollback_readback"]["channel"], 4)
        self.assertEqual(fake.channel, 4)
        accepted, reason = runtime.request_experiment(status["intent_token"])
        self.assertFalse(accepted)
        self.assertEqual(reason, "one_experiment_per_app_start")
