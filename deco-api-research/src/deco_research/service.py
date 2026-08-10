"""Continuous read-only monitoring runtime and Home Assistant Ingress service."""

import asyncio
import logging
import os
import signal
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp
from aiohttp import web

from .client import DecoReadOnlyClient, ProbeError
from .home_assistant import HomeAssistantPublisher, HomeAssistantPublishError
from .options import MonitorOptions, load_options
from .privileges import PrivilegeDropError, drop_process_privileges
from .sanitizer import build_snapshot
from .ui import UI_HTML

LOGGER = logging.getLogger("deco_research")
APP_VERSION = os.environ.get("APP_VERSION", "dev")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _future(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(
        timespec="seconds"
    )


class ProbeRuntime:
    """Own the monitor state and expose no raw Deco replies."""

    def __init__(
        self,
        options: MonitorOptions,
        publisher: HomeAssistantPublisher | None = None,
    ) -> None:
        self.options = options
        self.publisher = publisher
        self._stop = asyncio.Event()
        self._refresh = asyncio.Event()
        self._state: dict[str, Any] = {
            "schema_version": 2,
            "app_version": APP_VERSION,
            "mode": "starting" if options.monitoring_enabled else "disabled",
            "monitoring_enabled": options.monitoring_enabled,
            "target_configured": bool(
                options.host and options.username and options.password
            ),
            "poll_interval_seconds": options.poll_interval_seconds,
            "next_poll_at": None,
            "capabilities": [
                "continuous_read_only_monitoring",
                "device_inventory",
                "controller_performance",
                "connected_client_summary",
                "response_field_schema",
                "mesh_node_health",
                "anonymous_client_telemetry",
                "wireless_radio_status",
                "home_assistant_telemetry",
            ],
            "last_attempt_at": None,
            "last_success_at": None,
            "error_code": None,
            "publisher": {
                "enabled": publisher is not None,
                "status": "waiting" if publisher is not None else "disabled",
                "last_publish_at": None,
                "changed_entities": 0,
                "total_entities": 0,
                "error_code": None,
            },
            "mesh": None,
        }

    def status(self) -> dict[str, Any]:
        return deepcopy(self._state)

    async def poll_until_stopped(self, session: aiohttp.ClientSession) -> None:
        if not self.options.monitoring_enabled:
            await self._publish_state()
            await self._stop.wait()
            return

        client: DecoReadOnlyClient | None = None
        while not self._stop.is_set():
            if client is None:
                client = DecoReadOnlyClient(
                    session=session,
                    host=self.options.host,
                    username=self.options.username,
                    password=self.options.password,
                    verify_ssl=self.options.verify_ssl,
                )
            success = await self._poll_once(client)
            if not success:
                client = None
            if self._stop.is_set():
                break
            self._state["next_poll_at"] = _future(self.options.poll_interval_seconds)
            await self._wait_for_refresh_or_timeout()

    async def _wait_for_refresh_or_timeout(self) -> None:
        stop_task = asyncio.create_task(self._stop.wait())
        refresh_task = asyncio.create_task(self._refresh.wait())
        tasks = {stop_task, refresh_task}
        try:
            await asyncio.wait(
                tasks,
                timeout=self.options.poll_interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        self._refresh.clear()

    async def _poll_once(self, client: DecoReadOnlyClient) -> bool:
        self._state["mode"] = "polling"
        self._state["last_attempt_at"] = _now()
        self._state["next_poll_at"] = None
        self._state["error_code"] = None
        try:
            devices = await client.read_devices()
            performance = await client.read_performance()
            clients = await client.read_clients()
            wireless = await client.read_wireless_status()
            self._state["mesh"] = build_snapshot(
                devices,
                performance,
                clients,
                wireless,
                node_aliases=self.options.node_aliases,
            )
            self._state["last_success_at"] = _now()
            self._state["mode"] = "healthy"
            LOGGER.info("Read-only monitor cycle completed")
            await self._publish_state()
            return True
        except ProbeError as err:
            self._state["mode"] = "error"
            self._state["error_code"] = err.code
            LOGGER.warning("Read-only monitor failed with category: %s", err.code)
        except Exception:  # noqa: BLE001 - daemon boundary deliberately redacts errors
            self._state["mode"] = "error"
            self._state["error_code"] = "internal_error"
            LOGGER.error("Read-only monitor failed with category: internal_error")
        await self._publish_state()
        return False

    async def _publish_state(self) -> None:
        if self.publisher is None:
            return
        publisher_state = self._state["publisher"]
        try:
            changed, total = await self.publisher.publish(self._state)
            publisher_state.update(
                {
                    "status": "healthy",
                    "last_publish_at": _now(),
                    "changed_entities": changed,
                    "total_entities": total,
                    "error_code": None,
                }
            )
        except HomeAssistantPublishError as err:
            publisher_state.update(
                {
                    "status": "error",
                    "error_code": str(err),
                }
            )
            if self._state["mode"] == "healthy":
                self._state["mode"] = "degraded"
            LOGGER.warning("Home Assistant telemetry publishing failed")

    def request_refresh(self) -> bool:
        if not self.options.monitoring_enabled:
            return False
        self._refresh.set()
        return True

    def stop(self) -> None:
        self._stop.set()
        self._refresh.set()

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

    timeout = aiohttp.ClientTimeout(total=40)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        publisher = (
            HomeAssistantPublisher(session)
            if options.publish_to_home_assistant
            else None
        )
        runtime = ProbeRuntime(options, publisher)
        app = web.Application()

        async def page(_: web.Request) -> web.Response:
            return web.Response(
                text=UI_HTML,
                content_type="text/html",
                headers={
                    "Cache-Control": "no-store",
                    "Content-Security-Policy": (
                        "default-src 'self'; style-src 'unsafe-inline'; "
                        "script-src 'unsafe-inline'; connect-src 'self'"
                    ),
                    "X-Content-Type-Options": "nosniff",
                },
            )

        async def health(_: web.Request) -> web.Response:
            payload = runtime.status()
            return web.json_response({"status": "ok", "mode": payload["mode"]})

        async def status(_: web.Request) -> web.Response:
            return web.json_response(runtime.status())

        async def refresh(_: web.Request) -> web.Response:
            if not runtime.request_refresh():
                return web.json_response(
                    {"accepted": False, "reason": "monitoring_disabled"},
                    status=409,
                )
            return web.json_response({"accepted": True}, status=202)

        app.router.add_get("/", page)
        app.router.add_get("/health", health)
        app.router.add_get("/api/v1/status", status)
        app.router.add_post("/api/v1/refresh", refresh)

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8099)
        await site.start()

        LOGGER.info(
            "FREE THE DECO %s started with monitoring %s",
            APP_VERSION,
            "ENABLED" if options.monitoring_enabled else "DISABLED",
        )

        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(signum, runtime.stop)
            except NotImplementedError:
                pass

        poll_task = asyncio.create_task(runtime.poll_until_stopped(session))
        await runtime.wait_stopped()
        await poll_task
        await runner.cleanup()
