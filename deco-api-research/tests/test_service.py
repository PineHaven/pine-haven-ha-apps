import asyncio
import unittest
from unittest.mock import patch

from deco_research.client import ProbeAuthError
from deco_research.home_assistant import HomeAssistantPublishError
from deco_research.options import MonitorOptions
from deco_research.service import ProbeRuntime


def _enabled_options(**overrides):
    values = {
        "monitoring_enabled": True,
        "host": "https://deco.invalid",
        "username": "operator",
        "password": "secret",
        "exclusive_session_acknowledged": True,
        "verify_ssl": False,
        "poll_interval_seconds": 60,
        "publish_to_home_assistant": False,
        "node_aliases": {},
        "stale_after_intervals": 3,
    }
    values.update(overrides)
    return MonitorOptions(**values)


class _SuccessfulClient:
    def __init__(self):
        self.calls = []

    async def read_devices(self):
        self.calls.append("devices")
        return []

    async def read_performance(self):
        self.calls.append("performance")
        return {}

    async def read_clients(self):
        self.calls.append("clients")
        return []

    async def read_wireless_status(self):
        self.calls.append("wireless")
        return {"band2_4": {"host": {"channel": "11"}}}


class ProbeRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_runtime_waits_without_creating_a_client(self):
        options = MonitorOptions.from_dict({"monitoring_enabled": False})
        runtime = ProbeRuntime(options)
        task = asyncio.create_task(runtime.poll_until_stopped(None))
        await asyncio.sleep(0)

        status = runtime.status()
        self.assertEqual(status["schema_version"], 4)
        self.assertEqual(status["mode"], "disabled")
        self.assertFalse(status["data_stale"])
        self.assertIsNone(status["last_attempt_at"])

        runtime.stop()
        await task

    async def test_monitor_cycle_performs_fixed_reads_once(self):
        runtime = ProbeRuntime(_enabled_options())
        client = _SuccessfulClient()
        self.assertTrue(await runtime._poll_once(client, trigger="startup"))

        self.assertEqual(
            client.calls, ["devices", "performance", "clients", "wireless"]
        )
        status = runtime.status()
        self.assertEqual(status["mode"], "healthy")
        self.assertEqual(status["successful_cycles"], 1)
        self.assertEqual(status["health"]["deco_read"]["status"], "healthy")
        self.assertEqual(status["health"]["session"]["status"], "authenticated")
        self.assertEqual(
            status["mesh"]["wireless_radio"]["band2_4"]["channel"],
            11,
        )
        self.assertEqual(
            status["mesh"]["coexistence"]["control_readiness"]["state"],
            "disarmed",
        )

    async def test_failure_is_categorized_and_next_success_records_recovery(self):
        runtime = ProbeRuntime(_enabled_options())

        class AuthFailureClient(_SuccessfulClient):
            async def read_devices(self):
                raise ProbeAuthError

        self.assertFalse(await runtime._poll_once(AuthFailureClient()))
        failed = runtime.status()
        self.assertEqual(failed["failed_cycles"], 1)
        self.assertEqual(failed["consecutive_failures"], 1)
        self.assertEqual(failed["health"]["session"]["status"], "authentication_failed")
        self.assertEqual(failed["recovery"]["status"], "retrying")

        self.assertTrue(await runtime._poll_once(_SuccessfulClient()))
        recovered = runtime.status()
        self.assertEqual(recovered["successful_cycles"], 1)
        self.assertEqual(recovered["consecutive_failures"], 0)
        self.assertEqual(recovered["recovery"]["status"], "recovered")
        self.assertIsNotNone(recovered["recovery"]["last_recovery_at"])

    async def test_manual_refresh_has_explicit_lifecycle_and_rejects_duplicate(self):
        runtime = ProbeRuntime(_enabled_options())
        accepted, reason = runtime.request_refresh()
        self.assertTrue(accepted)
        self.assertEqual(reason, "queued")
        self.assertEqual(runtime.status()["manual_refresh"]["status"], "queued")
        self.assertEqual(
            runtime.request_refresh(), (False, "refresh_already_pending")
        )

        self.assertTrue(await runtime._poll_once(_SuccessfulClient(), trigger="manual"))
        refresh = runtime.status()["manual_refresh"]
        self.assertEqual(refresh["status"], "succeeded")
        self.assertIsNotNone(refresh["started_at"])
        self.assertIsNotNone(refresh["completed_at"])

    async def test_publisher_health_matches_delivery_result(self):
        class Publisher:
            def __init__(self):
                self.payloads = []

            async def publish(self, payload):
                self.payloads.append(payload)
                return 4, 30

        publisher = Publisher()
        runtime = ProbeRuntime(_enabled_options(), publisher)
        await runtime._publish_state()
        self.assertEqual(
            publisher.payloads[-1]["publisher"]["status"], "healthy"
        )
        self.assertEqual(runtime.status()["publisher"]["status"], "healthy")
        self.assertEqual(runtime.status()["publisher"]["total_entities"], 30)

        class FailedPublisher:
            async def publish(self, _payload):
                raise HomeAssistantPublishError("home_assistant_publish_failed")

        failed_runtime = ProbeRuntime(_enabled_options(), FailedPublisher())
        await failed_runtime._publish_state()
        status = failed_runtime.status()
        self.assertEqual(status["publisher"]["status"], "error")
        self.assertEqual(
            status["publisher"]["error_code"], "home_assistant_publish_failed"
        )

    async def test_status_marks_data_stale_after_configured_intervals(self):
        runtime = ProbeRuntime(
            _enabled_options(poll_interval_seconds=1, stale_after_intervals=2)
        )
        runtime._started_monotonic -= 2.1
        status = runtime.status()
        self.assertTrue(status["data_stale"])
        self.assertEqual(status["mode"], "stale")
        self.assertEqual(status["stale_after_seconds"], 2)

    async def test_enabled_monitor_repeats_until_stopped(self):
        options = _enabled_options(poll_interval_seconds=0.001)
        runtime = ProbeRuntime(options)

        class FakeClient:
            cycles = 0

            def __init__(self, **_kwargs):
                pass

            async def read_devices(self):
                return []

            async def read_performance(self):
                return {}

            async def read_clients(self):
                return []

            async def read_wireless_status(self):
                FakeClient.cycles += 1
                if FakeClient.cycles == 2:
                    runtime.stop()
                return {}

        with patch("deco_research.service.DecoReadOnlyClient", FakeClient):
            await runtime.poll_until_stopped(None)

        self.assertEqual(FakeClient.cycles, 2)
        self.assertEqual(runtime.status()["mode"], "healthy")


if __name__ == "__main__":
    unittest.main()
