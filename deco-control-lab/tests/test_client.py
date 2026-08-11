import unittest
from unittest.mock import AsyncMock

from deco_lab.client import DecoLabClient, ProbeProtocolError


class ClientTests(unittest.IsolatedAsyncioTestCase):
    def client(self):
        return DecoLabClient(
            session=object(),
            host="http://192.0.2.72",
            username="admin",
            password="not-a-real-secret",
            verify_ssl=False,
        )

    async def test_candidate_is_fixed_to_channel_11_ht20(self):
        client = self.client()
        client._authenticated_write = AsyncMock()
        await client.apply_channel_11_ht20()
        client._authenticated_write.assert_awaited_once_with(
            channel=11, bandwidth="HT20"
        )

    async def test_rollback_accepts_only_recognized_captured_pairs(self):
        client = self.client()
        client._authenticated_write = AsyncMock()
        await client.restore_captured_radio(4, "HT40")
        client._authenticated_write.assert_awaited_once_with(
            channel=4, bandwidth="HT40"
        )
        for channel, width in ((0, "HT40"), (14, "HT40"), (4, "AUTO")):
            with self.subTest(channel=channel, width=width), self.assertRaises(
                ProbeProtocolError
            ):
                await client.restore_captured_radio(channel, width)
