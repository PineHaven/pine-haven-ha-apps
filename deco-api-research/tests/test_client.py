import unittest

from deco_research.client import DecoReadOnlyClient, ProbeProtocolError


class _Url:
    scheme = "https"
    host = "deco.invalid"


class _Headers:
    @staticmethod
    def getall(_name, _default):
        return []


class _Response:
    def __init__(self):
        self.history = []
        self.url = _Url()
        self.headers = _Headers()

    @staticmethod
    def raise_for_status():
        return None

    @staticmethod
    async def json(content_type=None):
        del content_type
        return {"data": "ciphertext"}


class _Session:
    def __init__(self):
        self.url = None

    async def post(self, url, **_kwargs):
        self.url = url
        return _Response()


class ClientGuardrailTests(unittest.IsolatedAsyncioTestCase):
    async def test_authenticated_reads_use_admin_path(self):
        session = _Session()
        client = DecoReadOnlyClient(
            session=session,
            host="https://deco.invalid",
            username="operator",
            password="secret",
            verify_ssl=False,
        )
        client._stok = "opaque-session"
        client._encode_payload = lambda _payload: "encoded"
        client._decrypt_data = lambda _data: {"result": {"device_list": []}}

        await client._encrypted_call(
            area="device",
            form="device_list",
            payload={"operation": "read"},
        )

        self.assertEqual(
            session.url,
            "https://deco.invalid/cgi-bin/luci/;stok=opaque-session/admin/device",
        )

    async def test_unlisted_read_is_rejected_before_network_access(self):
        client = DecoReadOnlyClient(
            session=None,
            host="https://deco.invalid",
            username="operator",
            password="secret",
            verify_ssl=False,
        )
        with self.assertRaises(ProbeProtocolError):
            await client._authenticated_read("system", "system", None)

    async def test_client_summary_uses_global_read_query(self):
        client = DecoReadOnlyClient(
            session=None,
            host="https://deco.invalid",
            username="operator",
            password="secret",
            verify_ssl=False,
        )
        captured = {}

        async def authenticated_read(area, form, params):
            captured.update(area=area, form=form, params=params)
            return {"result": {"client_list": []}}

        client._authenticated_read = authenticated_read

        self.assertEqual(await client.read_clients(), [])
        self.assertEqual(
            captured,
            {
                "area": "client",
                "form": "client_list",
                "params": {"device_mac": "default"},
            },
        )


if __name__ == "__main__":
    unittest.main()
