import asyncio
import unittest

from deco_research.options import ProbeOptions
from deco_research.service import ProbeRuntime


class ProbeRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_disarmed_runtime_waits_without_creating_a_client(self):
        options = ProbeOptions.from_dict({"probe_enabled": False})
        runtime = ProbeRuntime(options)
        task = asyncio.create_task(runtime.poll_until_stopped())
        await asyncio.sleep(0)

        self.assertEqual(runtime.status()["mode"], "disarmed")
        self.assertIsNone(runtime.status()["last_attempt_at"])

        runtime.stop()
        await task

    async def test_armed_cycle_performs_fixed_reads_once(self):
        options = ProbeOptions.from_dict(
            {
                "probe_enabled": True,
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
        await runtime._poll_once(client)

        self.assertEqual(
            client.calls, ["devices", "performance", "clients", "wireless"]
        )
        self.assertEqual(runtime.status()["mode"], "healthy")
        self.assertEqual(
            runtime.status()["mesh"]["wireless_radio"]["band2_4"]["channel"],
            11,
        )


if __name__ == "__main__":
    unittest.main()
