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


if __name__ == "__main__":
    unittest.main()
