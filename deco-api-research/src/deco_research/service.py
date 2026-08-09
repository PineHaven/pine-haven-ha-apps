"""Ingress service and bounded polling loop."""

import asyncio
import logging
import os
import signal
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import aiohttp
from aiohttp import web

from .client import DecoReadOnlyClient, ProbeError
from .options import ProbeOptions, load_options
from .privileges import PrivilegeDropError, drop_process_privileges
from .sanitizer import build_snapshot

LOGGER = logging.getLogger("deco_research")
APP_VERSION = os.environ.get("APP_VERSION", "dev")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProbeRuntime:
    """Own the probe state and make only sanitized state externally visible."""

    def __init__(self, options: ProbeOptions) -> None:
        self.options = options
        self._stop = asyncio.Event()
        self._state: dict[str, Any] = {
            "schema_version": 1,
            "app_version": APP_VERSION,
            "mode": "disarmed" if not options.probe_enabled else "armed",
            "probe_enabled": options.probe_enabled,
            "target_configured": bool(
                options.host and options.username and options.password
            ),
            "capabilities": ["device_inventory", "controller_performance"],
            "last_attempt_at": None,
            "last_success_at": None,
            "error_code": None,
            "mesh": None,
        }

    def status(self) -> dict[str, Any]:
        return deepcopy(self._state)

    async def poll_until_stopped(self) -> None:
        if not self.options.probe_enabled:
            await self._stop.wait()
            return

        timeout = aiohttp.ClientTimeout(total=35)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            client = DecoReadOnlyClient(
                session=session,
                host=self.options.host,
                username=self.options.username,
                password=self.options.password,
                verify_ssl=self.options.verify_ssl,
            )
            await self._poll_once(client)
            await self._stop.wait()

    async def _poll_once(self, client: DecoReadOnlyClient) -> None:
        self._state["mode"] = "probing"
        self._state["last_attempt_at"] = _now()
        self._state["error_code"] = None
        try:
            devices = await client.read_devices()
            performance = await client.read_performance()
            self._state["mesh"] = build_snapshot(devices, performance)
            self._state["last_success_at"] = _now()
            self._state["mode"] = "healthy"
            LOGGER.info("Read-only probe completed; sanitized snapshot updated")
        except ProbeError as err:
            self._state["mode"] = "error"
            self._state["error_code"] = err.code
            LOGGER.warning("Read-only probe failed with category: %s", err.code)
        except Exception:  # noqa: BLE001 - daemon boundary deliberately redacts errors
            self._state["mode"] = "error"
            self._state["error_code"] = "internal_error"
            LOGGER.error("Read-only probe failed with category: internal_error")

    def stop(self) -> None:
        self._stop.set()

    async def wait_stopped(self) -> None:
        await self._stop.wait()


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        options = load_options(os.environ.get("OPTIONS_PATH", "/data/options.json"))
    except (OSError, ValueError):
        LOGGER.error("App options are invalid; values were not logged")
        raise SystemExit(2) from None

    try:
        drop_process_privileges()
    except PrivilegeDropError:
        LOGGER.error("App could not enter its restricted runtime account")
        raise SystemExit(3) from None

    runtime = ProbeRuntime(options)
    app = web.Application()

    async def health(_: web.Request) -> web.Response:
        status_payload = runtime.status()
        return web.json_response({"status": "ok", "mode": status_payload["mode"]})

    async def status(_: web.Request) -> web.Response:
        return web.json_response(runtime.status())

    app.router.add_get("/", status)
    app.router.add_get("/health", health)
    app.router.add_get("/api/v1/status", status)

    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8099)
    await site.start()

    LOGGER.info(
        "FREE THE DECO API Research %s started in %s mode",
        APP_VERSION,
        "ARMED" if options.probe_enabled else "DISARMED",
    )

    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(signum, runtime.stop)
        except NotImplementedError:
            pass

    poll_task = asyncio.create_task(runtime.poll_until_stopped())
    await runtime.wait_stopped()
    await poll_task
    await runner.cleanup()
