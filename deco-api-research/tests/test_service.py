import asyncio
import unittest
from unittest.mock import patch

from deco_research.options import MonitorOptions
from deco_research.service import ProbeRuntime


class ProbeRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_runtime_waits_without_creating_a_client(self):
        options = MonitorOptions.from_dict({"monitoring_enabled": False})
        runtime = ProbeRuntime(options)
        task = asyncio.create_task(runtime.poll_until_stopped(None))
        await asyncio.sleep(0)

        self.assertEqual(runtime.status()["mode"], "disabled")
        self.assertIsNone(runtime.status()["last_attempt_at"])

        runtime.stop()
        await task

    async def test_monitor_cycle_performs_fixed_reads_once(self):
        options = MonitorOptions.from_dict(
            {
                "monitoring_enabled": True,
                "exclusive_session_acknowledged": True,
                "host": "https://deco.invalid",
                "username": "operator",
                "password": "secret",
            }
        )
        runtime = ProbeRuntime(options)

        class FakeClient:
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

        client = FakeClient()
        self.assertTrue(await runtime._poll_once(client))

        self.assertEqual(
            client.calls, ["devices", "performance", "clients", "wireless"]
        )
        self.assertEqual(runtime.status()["mode"], "healthy")
        self.assertEqual(
            runtime.status()["mesh"]["wireless_radio"]["band2_4"]["channel"],
            11,
        )

    async def test_enabled_monitor_repeats_until_stopped(self):
        options = MonitorOptions(
            monitoring_enabled=True,
            host="https://deco.invalid",
            username="operator",
            password="secret",
            exclusive_session_acknowledged=True,
            verify_ssl=False,
            poll_interval_seconds=0.001,
            publish_to_home_assistant=False,
            node_aliases={},
        )
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
