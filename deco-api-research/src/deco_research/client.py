"""Bounded TP-Link Deco API client containing read operations only.

Authentication/encryption is adapted from amosyuen/ha-tplink-deco 3.9.7
under the MIT License. See THIRD_PARTY_NOTICES.md.
"""

import asyncio
import base64
import hashlib
import json
import math
import re
import secrets
from typing import Any
from urllib.parse import quote_plus

import aiohttp
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad

AES_KEY_BYTES = 16
MIN_AES_KEY = 10 ** (AES_KEY_BYTES - 1)
MAX_AES_KEY = (10**AES_KEY_BYTES) - 1
PKCS1_V15_HEADER_BYTES = 11
ALLOWED_READ_CALLS = frozenset(
    {
        ("device", "device_list"),
        ("network", "performance"),
    }
)


class ProbeError(Exception):
    """A categorized error safe to report without its raw message."""

    code = "unexpected_api_error"


class ProbeAuthError(ProbeError):
    code = "authentication_error"


class ProbeConnectionError(ProbeError):
    code = "connection_error"


class ProbeTimeoutError(ProbeError):
    code = "timeout_error"


class ProbeProtocolError(ProbeError):
    code = "protocol_error"


class DecoReadOnlyClient:
    """Client with a closed set of two post-authentication read calls."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool,
        timeout_seconds: int = 30,
    ) -> None:
        self._session = session
        self._host = host
        self._username = username
        self._password = password
        self._ssl: bool | None = None if verify_ssl else False
        self._timeout_seconds = timeout_seconds
        self._operation_lock = asyncio.Lock()

        self._aes_key: int | None = None
        self._aes_key_bytes: bytes | None = None
        self._aes_iv: int | None = None
        self._aes_iv_bytes: bytes | None = None
        self._password_rsa_n: int | None = None
        self._password_rsa_e: int | None = None
        self._sign_rsa_n: int | None = None
        self._sign_rsa_e: int | None = None
        self._seq: int | None = None
        self._stok: str | None = None
        self._cookie: str | None = None

    async def read_devices(self) -> list[dict[str, Any]]:
        """Read the mesh device inventory."""

        async with self._operation_lock:
            data = await self._authenticated_read(
                area="device", form="device_list", params=None
            )
        try:
            devices = data["result"]["device_list"]
        except (KeyError, TypeError) as err:
            raise ProbeProtocolError from err
        if not isinstance(devices, list):
            raise ProbeProtocolError
        return devices

    async def read_performance(self) -> dict[str, Any]:
        """Read controller CPU and memory data."""

        async with self._operation_lock:
            return await self._authenticated_read(
                area="network", form="performance", params=None
            )

    async def _authenticated_read(
        self, area: str, form: str, params: dict[str, Any] | None
    ) -> dict[str, Any]:
        if (area, form) not in ALLOWED_READ_CALLS:
            raise ProbeProtocolError
        await self._login_if_needed()
        payload: dict[str, Any] = {"operation": "read"}
        if params is not None:
            payload["params"] = params
        result = await self._encrypted_call(area=area, form=form, payload=payload)
        if result.get("error_code") not in (None, 0, ""):
            raise ProbeProtocolError
        return result

    async def _login_if_needed(self) -> None:
        if self._seq is None or self._stok is None or self._cookie is None:
            await self._login()

    async def _login(self) -> None:
        if self._aes_key is None:
            self._generate_aes_key_and_iv()
        if self._password_rsa_n is None:
            keys = await self._plain_login_read("keys")
            try:
                password_key = keys["result"]["password"]
                self._password_rsa_n = int(password_key[0], 16)
                self._password_rsa_e = int(password_key[1], 16)
            except (KeyError, IndexError, TypeError, ValueError) as err:
                raise ProbeProtocolError from err
        if self._seq is None:
            auth = await self._plain_login_read("auth")
            try:
                key = auth["result"]["key"]
                self._sign_rsa_n = int(key[0], 16)
                self._sign_rsa_e = int(key[1], 16)
                self._seq = int(auth["result"]["seq"])
            except (KeyError, IndexError, TypeError, ValueError) as err:
                raise ProbeProtocolError from err

        encrypted_password = _rsa_encrypt(
            self._password_rsa_n,
            self._password_rsa_e,
            self._password.encode("utf-8"),
        )
        response = await self._encrypted_call(
            area="login",
            form="login",
            payload={
                "params": {"password": encrypted_password},
                "operation": "login",
            },
            login=True,
        )
        if response.get("error_code") not in (None, 0, ""):
            self._clear_auth()
            raise ProbeAuthError
        try:
            self._stok = response["result"]["stok"]
        except (KeyError, TypeError) as err:
            raise ProbeProtocolError from err
        if not self._cookie:
            raise ProbeProtocolError

    async def _plain_login_read(self, form: str) -> dict[str, Any]:
        return await self._post_json(
            url=f"{self._host}/cgi-bin/luci/;stok=/login",
            form=form,
            data=json.dumps({"operation": "read"}),
        )

    async def _encrypted_call(
        self,
        area: str,
        form: str,
        payload: dict[str, Any],
        login: bool = False,
    ) -> dict[str, Any]:
        if login:
            url = f"{self._host}/cgi-bin/luci/;stok=/login"
        else:
            url = f"{self._host}/cgi-bin/luci/;stok={self._stok}/admin/{area}"
        response = await self._post_json(
            url=url, form=form, data=self._encode_payload(payload)
        )
        try:
            encrypted_data = response["data"]
        except (KeyError, TypeError) as err:
            raise ProbeProtocolError from err
        return self._decrypt_data(encrypted_data)

    async def _post_json(self, url: str, form: str, data: str) -> dict[str, Any]:
        cookies = {}
        if self._cookie:
            name, separator, value = self._cookie.partition("=")
            if separator:
                cookies[name] = value

        try:
            async with asyncio.timeout(self._timeout_seconds):
                response = await self._session.post(
                    url,
                    params={"form": form},
                    data=data,
                    headers={"Content-Type": "application/json"},
                    cookies=cookies,
                    ssl=self._ssl,
                )
                response.raise_for_status()

                if (
                    response.history
                    and response.url.scheme == "https"
                    and self._host.startswith("http://")
                    and response.url.host == response.history[0].url.host
                ):
                    self._host = "https://" + self._host[len("http://") :]

                for header in response.headers.getall("Set-Cookie", []):
                    match = re.search(r"(sysauth=[a-f0-9]+)", header)
                    if match:
                        self._cookie = match.group(1)
                        break

                body = await response.json(content_type=None)
                if not isinstance(body, dict):
                    raise ProbeProtocolError
                if body.get("error_code") not in (None, 0, ""):
                    raise ProbeProtocolError
                return body
        except TimeoutError as err:
            raise ProbeTimeoutError from err
        except aiohttp.ClientResponseError as err:
            if err.status in {401, 403}:
                self._clear_auth()
                raise ProbeAuthError from err
            raise ProbeConnectionError from err
        except (aiohttp.ClientConnectionError, aiohttp.ServerDisconnectedError) as err:
            self._clear_auth()
            raise ProbeConnectionError from err
        except aiohttp.ClientError as err:
            raise ProbeConnectionError from err

    def _generate_aes_key_and_iv(self) -> None:
        self._aes_key = secrets.randbelow(MAX_AES_KEY - MIN_AES_KEY) + MIN_AES_KEY
        self._aes_iv = secrets.randbelow(MAX_AES_KEY - MIN_AES_KEY) + MIN_AES_KEY
        self._aes_key_bytes = str(self._aes_key).encode("utf-8")
        self._aes_iv_bytes = str(self._aes_iv).encode("utf-8")

    def _encode_payload(self, payload: dict[str, Any]) -> str:
        encrypted_data = self._encode_data(payload)
        signature = self._encode_sign(len(encrypted_data))
        return f"sign={signature}&data={quote_plus(encrypted_data)}"

    def _encode_data(self, payload: dict[str, Any]) -> str:
        if self._aes_key_bytes is None or self._aes_iv_bytes is None:
            raise ProbeProtocolError
        plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        cipher = AES.new(self._aes_key_bytes, AES.MODE_CBC, self._aes_iv_bytes)
        return base64.b64encode(cipher.encrypt(pad(plaintext, AES.block_size))).decode()

    def _encode_sign(self, data_length: int) -> str:
        if None in (
            self._aes_key,
            self._aes_iv,
            self._sign_rsa_n,
            self._sign_rsa_e,
            self._seq,
        ):
            raise ProbeProtocolError
        auth_hash = hashlib.md5(
            f"{self._username}{self._password}".encode()
        ).hexdigest()
        sign_text = (
            f"k={self._aes_key}&i={self._aes_iv}&h={auth_hash}"
            f"&s={self._seq + data_length}"
        )
        return _rsa_encrypt(
            self._sign_rsa_n, self._sign_rsa_e, sign_text.encode("utf-8")
        )

    def _decrypt_data(self, encrypted_data: object) -> dict[str, Any]:
        if not isinstance(encrypted_data, str) or not encrypted_data:
            self._clear_auth()
            raise ProbeProtocolError
        if self._aes_key_bytes is None or self._aes_iv_bytes is None:
            raise ProbeProtocolError
        try:
            cipher = AES.new(self._aes_key_bytes, AES.MODE_CBC, self._aes_iv_bytes)
            plaintext = unpad(
                cipher.decrypt(base64.b64decode(encrypted_data)), AES.block_size
            )
            result = json.loads(plaintext.decode("utf-8"))
        except (ValueError, TypeError, json.JSONDecodeError) as err:
            raise ProbeProtocolError from err
        if not isinstance(result, dict):
            raise ProbeProtocolError
        return result

    def _clear_auth(self) -> None:
        self._seq = None
        self._stok = None
        self._cookie = None


def _rsa_encrypt(modulus: int, exponent: int, plaintext: bytes) -> str:
    public_key = RSA.construct((modulus, exponent)).publickey()
    encryptor = PKCS1_v1_5.new(public_key)
    block_size = (int(math.log2(modulus)) + 8) >> 3
    bytes_per_block = block_size - PKCS1_V15_HEADER_BYTES

    encrypted = bytearray()
    for index in range(0, len(plaintext), bytes_per_block):
        encrypted.extend(encryptor.encrypt(plaintext[index : index + bytes_per_block]))
    return encrypted.hex()
