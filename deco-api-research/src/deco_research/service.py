"""Continuous read-only monitoring runtime and Home Assistant Ingress service."""

import asyncio
import logging
import os
import signal
import time
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


def _future(seconds: float) -> str:
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
        self._started_monotonic = time.monotonic()
        self._last_success_monotonic: float | None = None
        self._next_poll_monotonic: float | None = None
        self._stale_after_seconds = (
            options.poll_interval_seconds * options.stale_after_intervals
        )
        self._state: dict[str, Any] = {
            "schema_version": 4,
            "app_version": APP_VERSION,
            "mode": "starting" if options.monitoring_enabled else "disabled",
            "monitoring_enabled": options.monitoring_enabled,
            "target_configured": bool(
                options.host and options.username and options.password
            ),
            "poll_interval_seconds": options.poll_interval_seconds,
            "stale_after_intervals": options.stale_after_intervals,
            "stale_after_seconds": self._stale_after_seconds,
            "mqtt_expire_after_seconds": (
                self._stale_after_seconds + options.poll_interval_seconds
            ),
            "started_at": _now(),
            "next_poll_at": None,
            "last_poll_trigger": None,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "consecutive_failures": 0,
            "last_cycle_duration_ms": None,
            "capabilities": [
                "continuous_read_only_monitoring",
                "device_inventory",
                "controller_performance",
                "connected_client_summary",
                "response_field_schema",
                "mesh_node_health",
                "anonymous_client_telemetry",
                "wireless_radio_status",
                "zigbee_coexistence_diagnostics",
                "radio_control_preflight",
                "mqtt_device_discovery",
                "operational_diagnostics",
            ],
            "last_attempt_at": None,
            "last_success_at": None,
            "error_code": None,
            "health": {
                "deco_read": {
                    "status": "waiting" if options.monitoring_enabled else "disabled",
                    "last_success_at": None,
                    "error_code": None,
                },
                "session": {
                    "status": "waiting" if options.monitoring_enabled else "disabled",
                    "last_success_at": None,
                    "error_code": None,
                },
            },
            "publisher": {
                "enabled": publisher is not None,
                "status": "waiting" if publisher is not None else "disabled",
                "last_publish_at": None,
                "changed_entities": 0,
                "total_entities": 0,
                "error_code": None,
            },
            "recovery": {
                "status": "not_needed",
                "last_recovery_at": None,
            },
            "manual_refresh": {
                "status": "idle",
                "requested_at": None,
                "started_at": None,
                "completed_at": None,
                "error_code": None,
            },
            "mesh": None,
        }

    def status(self) -> dict[str, Any]:
        """Return a computed, redacted operational snapshot."""

        payload = deepcopy(self._state)
        current = time.monotonic()
        uptime = max(0.0, current - self._started_monotonic)
        payload["app_uptime_seconds"] = round(uptime, 1)

        if self._last_success_monotonic is None:
            payload["poll_age_seconds"] = None
            stale_age = uptime
        else:
            poll_age = max(0.0, current - self._last_success_monotonic)
            payload["poll_age_seconds"] = round(poll_age, 1)
            stale_age = poll_age

        data_stale = (
            self.options.monitoring_enabled
            and stale_age >= self._stale_after_seconds
        )
        payload["data_stale"] = data_stale
        if data_stale and payload["mode"] not in {"disabled", "polling"}:
            payload["mode"] = "stale"

        if self._next_poll_monotonic is None:
            payload["next_poll_in_seconds"] = None
        else:
            remaining = max(0.0, self._next_poll_monotonic - current)
            payload["next_poll_in_seconds"] = round(remaining, 1)
        return payload

    async def poll_until_stopped(self, session: aiohttp.ClientSession) -> None:
        if not self.options.monitoring_enabled:
            await self._publish_state()
            await self._stop.wait()
            return

        client: DecoReadOnlyClient | None = None
        trigger = "startup"
        while not self._stop.is_set():
            if client is None:
                client = DecoReadOnlyClient(
                    session=session,
                    host=self.options.host,
                    username=self.options.username,
                    password=self.options.password,
                    verify_ssl=self.options.verify_ssl,
                )
            success = await self._poll_once(client, trigger=trigger)
            if not success:
                client = None
            if self._stop.is_set():
                break

            self._next_poll_monotonic = (
                time.monotonic() + self.options.poll_interval_seconds
            )
            self._state["next_poll_at"] = _future(
                self.options.poll_interval_seconds
            )
            trigger = await self._wait_for_refresh_or_timeout()
            if trigger == "stop":
                break

    async def _wait_for_refresh_or_timeout(self) -> str:
        stop_task = asyncio.create_task(self._stop.wait())
        refresh_task = asyncio.create_task(self._refresh.wait())
        tasks = {stop_task, refresh_task}
        done: set[asyncio.Task[bool]] = set()
        try:
            done, _ = await asyncio.wait(
                tasks,
                timeout=self.options.poll_interval_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        self._next_poll_monotonic = None
        self._state["next_poll_at"] = None
        if stop_task in done and stop_task.result():
            return "stop"
        if refresh_task in done and refresh_task.result():
            self._refresh.clear()
            return "manual"
        return "scheduled"

    async def _poll_once(
        self, client: DecoReadOnlyClient, trigger: str = "scheduled"
    ) -> bool:
        cycle_started = time.monotonic()
        prior_failures = int(self._state["consecutive_failures"])
        self._state.update(
            {
                "mode": "polling",
                "last_attempt_at": _now(),
                "last_poll_trigger": trigger,
                "next_poll_at": None,
                "error_code": None,
            }
        )
        self._next_poll_monotonic = None
        if trigger == "manual":
            self._state["manual_refresh"].update(
                {
                    "status": "running",
                    "started_at": _now(),
                    "completed_at": None,
                    "error_code": None,
                }
            )

        success = False
        try:
            # The wire boundary remains exactly four fixed read operations.
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
            success_at = _now()
            self._last_success_monotonic = time.monotonic()
            self._state.update(
                {
                    "last_success_at": success_at,
                    "mode": "healthy",
                    "successful_cycles": self._state["successful_cycles"] + 1,
                    "consecutive_failures": 0,
                    "error_code": None,
                }
            )
            self._state["health"] = {
                "deco_read": {
                    "status": "healthy",
                    "last_success_at": success_at,
                    "error_code": None,
                },
                "session": {
                    "status": "authenticated",
                    "last_success_at": success_at,
                    "error_code": None,
                },
            }
            if prior_failures:
                self._state["recovery"] = {
                    "status": "recovered",
                    "last_recovery_at": success_at,
                }
            else:
                self._state["recovery"]["status"] = "not_needed"
            if trigger == "manual":
                self._complete_manual_refresh("succeeded")
            LOGGER.info("Read-only monitor cycle completed")
            success = True
        except ProbeError as err:
            self._record_failure(err.code)
            if trigger == "manual":
                self._complete_manual_refresh("failed", err.code)
            LOGGER.warning("Read-only monitor failed with category: %s", err.code)
        except Exception:  # noqa: BLE001 - daemon boundary deliberately redacts errors
            self._record_failure("internal_error")
            if trigger == "manual":
                self._complete_manual_refresh("failed", "internal_error")
            LOGGER.error("Read-only monitor failed with category: internal_error")
        finally:
            elapsed_ms = max(0.0, (time.monotonic() - cycle_started) * 1000)
            self._state["last_cycle_duration_ms"] = round(elapsed_ms, 1)

        await self._publish_state()
        return success

    def _record_failure(self, error_code: str) -> None:
        self._state.update(
            {
                "mode": "error",
                "error_code": error_code,
                "failed_cycles": self._state["failed_cycles"] + 1,
                "consecutive_failures": self._state["consecutive_failures"] + 1,
            }
        )
        session_status = {
            "authentication_error": "authentication_failed",
            "connection_error": "unavailable",
            "timeout_error": "unavailable",
        }.get(error_code, "indeterminate")
        session_error = error_code if error_code != "internal_error" else "internal_error"
        last_success = self._state["last_success_at"]
        self._state["health"] = {
            "deco_read": {
                "status": "error",
                "last_success_at": last_success,
                "error_code": error_code,
            },
            "session": {
                "status": session_status,
                "last_success_at": last_success,
                "error_code": session_error,
            },
        }
        self._state["recovery"]["status"] = "retrying"

    def _complete_manual_refresh(
        self, status: str, error_code: str | None = None
    ) -> None:
        self._state["manual_refresh"].update(
            {
                "status": status,
                "completed_at": _now(),
                "error_code": error_code,
            }
        )

    async def _publish_state(self) -> None:
        if self.publisher is None:
            return
        publisher_state = self._state["publisher"]
        previous_publish_at = publisher_state["last_publish_at"]
        publish_at = _now()
        # Advertise healthy in the packet being attempted. If delivery fails,
        # Home Assistant never receives that packet and the local status is
        # immediately changed to error below.
        publisher_state.update(
            {
                "status": "healthy",
                "last_publish_at": publish_at,
                "error_code": None,
            }
        )
        try:
            changed, total = await self.publisher.publish(self.status())
            publisher_state.update(
                {
                    "status": "healthy",
                    "last_publish_at": publish_at,
                    "changed_entities": changed,
                    "total_entities": total,
                    "error_code": None,
                }
            )
        except HomeAssistantPublishError as err:
            publisher_state.update(
                {
                    "status": "error",
                    "last_publish_at": previous_publish_at,
                    "error_code": str(err),
                }
            )
            if self._state["mode"] == "healthy":
                self._state["mode"] = "degraded"
            LOGGER.warning("Home Assistant telemetry publishing failed")
        except Exception:  # noqa: BLE001 - publisher boundary redacts internals
            publisher_state.update(
                {
                    "status": "error",
                    "last_publish_at": previous_publish_at,
                    "error_code": "home_assistant_publish_internal_error",
                }
            )
            if self._state["mode"] == "healthy":
                self._state["mode"] = "degraded"
            LOGGER.error("Home Assistant telemetry publishing failed internally")

    def request_refresh(self) -> tuple[bool, str]:
        if not self.options.monitoring_enabled:
            return False, "monitoring_disabled"
        refresh = self._state["manual_refresh"]
        if refresh["status"] in {"queued", "running"}:
            return False, "refresh_already_pending"
        refresh.update(
            {
                "status": "queued",
                "requested_at": _now(),
                "started_at": None,
                "completed_at": None,
                "error_code": None,
            }
        )
        self._refresh.set()
        return True, "queued"

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
            return web.json_response(
                {
                    "status": "ok" if payload["mode"] != "stale" else "stale",
                    "mode": payload["mode"],
                }
            )

        async def status(_: web.Request) -> web.Response:
            return web.json_response(runtime.status())

        async def refresh(_: web.Request) -> web.Response:
            accepted, reason = runtime.request_refresh()
            if not accepted:
                return web.json_response(
                    {"accepted": False, "reason": reason},
                    status=409,
                )
            return web.json_response(
                {
                    "accepted": True,
                    "reason": reason,
                    "manual_refresh": runtime.status()["manual_refresh"],
                },
                status=202,
            )

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
