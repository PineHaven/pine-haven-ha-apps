"""Ingress service for the physically isolated FREE THE DECO laboratory."""

import asyncio
import logging
import os
import secrets
import signal
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import aiohttp
from aiohttp import web

from .client import DecoLabClient, ProbeError
from .identity import radio_snapshot, verify_single_lab_node
from .options import LabOptions, load_options
from .privileges import PrivilegeDropError, drop_process_privileges
from .ui import UI_HTML

LOGGER = logging.getLogger("deco_lab")
APP_VERSION = os.environ.get("APP_VERSION", "dev")
READBACK_ATTEMPTS = 15
READBACK_INTERVAL_SECONDS = 2
ROLLBACK_WRITE_ATTEMPTS = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class LabRuntime:
    """Own fail-closed identity state and a single bounded experiment."""

    def __init__(self, options: LabOptions) -> None:
        self.options = options
        self._stop = asyncio.Event()
        self._refresh = asyncio.Event()
        self._experiment = asyncio.Event()
        self._intent_token = secrets.token_urlsafe(24)
        self._experiment_attempted = False
        self._state: dict[str, Any] = {
            "schema_version": 1,
            "app_version": APP_VERSION,
            "mode": "starting" if options.lab_enabled else "disabled",
            "lab_enabled": options.lab_enabled,
            "writes_enabled": options.writes_enabled,
            "firmware_write_compatibility_acknowledged": (
                options.firmware_write_compatibility_acknowledged
            ),
            "target_configured": bool(options.host and options.expected_mac),
            "last_attempt_at": None,
            "last_success_at": None,
            "error_code": None,
            "identity": None,
            "radio": None,
            "control_ready": False,
            "experiment": {
                "state": "locked" if not options.writes_enabled else "idle",
                "candidate": {"channel": 11, "bandwidth": "HT20"},
                "hold_seconds": options.hold_seconds,
                "baseline": None,
                "candidate_readback": None,
                "rollback_readback": None,
                "started_at": None,
                "completed_at": None,
                "error_code": None,
            },
            "audit": [],
        }

    def status(self) -> dict[str, Any]:
        payload = deepcopy(self._state)
        payload["intent_token"] = self._intent_token
        return payload

    async def run(self, session: aiohttp.ClientSession) -> None:
        if not self.options.lab_enabled:
            await self._stop.wait()
            return
        await self._refresh_baseline(session)

        while not self._stop.is_set():
            stop_task = asyncio.create_task(self._stop.wait())
            refresh_task = asyncio.create_task(self._refresh.wait())
            experiment_task = asyncio.create_task(self._experiment.wait())
            tasks = {stop_task, refresh_task, experiment_task}
            try:
                done, _ = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            if stop_task in done and stop_task.result():
                break
            if refresh_task in done and refresh_task.result():
                self._refresh.clear()
                await self._refresh_baseline(session)
            if experiment_task in done and experiment_task.result():
                self._experiment.clear()
                await self._run_experiment(session)

    async def _refresh_baseline(self, session: aiohttp.ClientSession) -> None:
        self._state.update(
            {"mode": "reading", "last_attempt_at": _now(), "error_code": None}
        )
        client = self._client(session)
        try:
            devices = await client.read_devices()
            wireless = await client.read_wireless_status()
            identity = verify_single_lab_node(devices, self.options.expected_mac)
            radio = radio_snapshot(wireless)
            ready = bool(
                identity["ready"]
                and radio["channel"] is not None
                and radio["bandwidth"] in {"HT20", "HT40"}
            )
            self._state.update(
                {
                    "mode": "ready" if ready else "identity_blocked",
                    "last_success_at": _now(),
                    "identity": identity,
                    "radio": radio,
                    "control_ready": (
                        ready
                        and self.options.writes_enabled
                        and self.options.firmware_write_compatibility_acknowledged
                    ),
                    "error_code": None,
                }
            )
            self._audit("baseline_read", "succeeded" if ready else "blocked")
        except ProbeError as err:
            self._record_error(err.code)
            self._audit("baseline_read", "failed", err.code)
        except Exception:  # noqa: BLE001 - daemon boundary deliberately redacts
            self._record_error("internal_error")
            self._audit("baseline_read", "failed", "internal_error")

    def request_refresh(self) -> tuple[bool, str]:
        if not self.options.lab_enabled:
            return False, "lab_disabled"
        if self._state["mode"] in {"reading", "experiment_running"}:
            return False, "operation_in_progress"
        self._refresh.set()
        return True, "queued"

    def request_experiment(self, intent_token: object) -> tuple[bool, str]:
        if intent_token != self._intent_token:
            return False, "invalid_intent_token"
        if not self.options.writes_enabled:
            return False, "writes_locked_in_app_options"
        if self._experiment_attempted:
            return False, "one_experiment_per_app_start"
        if not self._state["control_ready"]:
            return False, "identity_or_radio_gate_not_ready"
        if self._state["mode"] in {"reading", "experiment_running"}:
            return False, "operation_in_progress"
        self._experiment_attempted = True
        self._state["experiment"]["state"] = "queued"
        self._experiment.set()
        return True, "queued"

    async def _run_experiment(self, session: aiohttp.ClientSession) -> None:
        experiment = self._state["experiment"]
        experiment.update(
            {
                "state": "preflight",
                "baseline": None,
                "candidate_readback": None,
                "rollback_readback": None,
                "started_at": _now(),
                "completed_at": None,
                "error_code": None,
            }
        )
        self._state["mode"] = "experiment_running"
        self._state["control_ready"] = False
        baseline: dict[str, Any] | None = None
        candidate_attempted = False
        client = self._client(session)

        try:
            devices = await client.read_devices()
            wireless = await client.read_wireless_status()
            identity = verify_single_lab_node(devices, self.options.expected_mac)
            baseline = radio_snapshot(wireless)
            if not identity["ready"]:
                raise LabGateError("identity_gate_failed")
            if baseline["channel"] is None or baseline["bandwidth"] not in {
                "HT20",
                "HT40",
            }:
                raise LabGateError("rollback_capture_failed")
            if (
                baseline["channel"] == 11
                and baseline["bandwidth"] == "HT20"
            ):
                raise LabGateError("candidate_already_active")

            experiment["baseline"] = baseline
            experiment["state"] = "applying_candidate"
            self._audit("candidate_write", "started")
            candidate_attempted = True
            await client.apply_channel_11_ht20()

            experiment["state"] = "verifying_candidate"
            candidate = await self._read_until(
                session,
                expected_channel=11,
                expected_bandwidth="HT20",
            )
            experiment["candidate_readback"] = candidate
            self._audit("candidate_readback", "succeeded")

            experiment["state"] = "holding"
            await asyncio.wait_for(
                self._stop.wait(), timeout=self.options.hold_seconds
            )
        except TimeoutError:
            # Normal end of the bounded hold period.
            pass
        except LabGateError as err:
            experiment["error_code"] = err.code
            self._audit("experiment", "blocked", err.code)
        except ProbeError as err:
            experiment["error_code"] = err.code
            self._audit("experiment", "failed", err.code)
        except Exception:  # noqa: BLE001 - daemon boundary deliberately redacts
            experiment["error_code"] = "internal_error"
            self._audit("experiment", "failed", "internal_error")
        finally:
            if candidate_attempted and baseline is not None:
                experiment["state"] = "rolling_back"
                try:
                    rollback = await self._restore_with_retries(
                        session,
                        channel=baseline["channel"],
                        bandwidth=baseline["bandwidth"],
                    )
                    experiment["rollback_readback"] = rollback
                    experiment["state"] = "rolled_back"
                    self._audit("rollback", "succeeded")
                except ProbeError as err:
                    experiment["state"] = "rollback_failed"
                    experiment["error_code"] = "rollback_failed"
                    self._audit("rollback", "failed", err.code)
                except Exception:  # noqa: BLE001
                    experiment["state"] = "rollback_failed"
                    experiment["error_code"] = "rollback_failed"
                    self._audit("rollback", "failed", "internal_error")
            elif experiment["error_code"]:
                experiment["state"] = "blocked"

            result_state = experiment["state"]
            experiment["completed_at"] = _now()
            await self._refresh_baseline(session)
            self._state["control_ready"] = False
            if result_state == "rolled_back":
                self._state["mode"] = "complete"
            elif result_state == "rollback_failed":
                self._state["mode"] = "attention"

    async def _read_until(
        self,
        session: aiohttp.ClientSession,
        expected_channel: int,
        expected_bandwidth: str,
    ) -> dict[str, Any]:
        last_error: ProbeError | None = None
        for _ in range(READBACK_ATTEMPTS):
            try:
                client = self._client(session)
                radio = radio_snapshot(await client.read_wireless_status())
                if (
                    radio["channel"] == expected_channel
                    and radio["bandwidth"] == expected_bandwidth
                ):
                    return radio
            except ProbeError as err:
                last_error = err
            await asyncio.sleep(READBACK_INTERVAL_SECONDS)
        if last_error is not None:
            raise last_error
        raise ProbeError

    async def _restore_with_retries(
        self,
        session: aiohttp.ClientSession,
        channel: int,
        bandwidth: str,
    ) -> dict[str, Any]:
        last_error: ProbeError | None = None
        for attempt in range(ROLLBACK_WRITE_ATTEMPTS):
            try:
                rollback_client = self._client(session)
                await rollback_client.restore_captured_radio(channel, bandwidth)
                return await self._read_until(
                    session,
                    expected_channel=channel,
                    expected_bandwidth=bandwidth,
                )
            except ProbeError as err:
                last_error = err
                if attempt + 1 < ROLLBACK_WRITE_ATTEMPTS:
                    await asyncio.sleep(READBACK_INTERVAL_SECONDS)
        if last_error is not None:
            raise last_error
        raise ProbeError

    def _client(self, session: aiohttp.ClientSession) -> DecoLabClient:
        return DecoLabClient(
            session=session,
            host=self.options.host,
            username=self.options.username,
            password=self.options.password,
            verify_ssl=self.options.verify_ssl,
        )

    def _record_error(self, code: str) -> None:
        self._state.update(
            {"mode": "error", "error_code": code, "control_ready": False}
        )

    def _audit(self, action: str, result: str, error_code: str | None = None) -> None:
        self._state["audit"].append(
            {
                "at": _now(),
                "action": action,
                "result": result,
                "error_code": error_code,
            }
        )
        self._state["audit"] = self._state["audit"][-40:]

    def stop(self) -> None:
        self._stop.set()
        self._refresh.set()
        self._experiment.set()

    async def wait_stopped(self) -> None:
        await self._stop.wait()


class LabGateError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        options = load_options(os.environ.get("OPTIONS_PATH", "/data/options.json"))
    except (OSError, ValueError):
        LOGGER.error("Lab options are invalid; values were not logged")
        raise SystemExit(2) from None

    try:
        drop_process_privileges()
    except PrivilegeDropError:
        LOGGER.error("Lab App could not enter its restricted runtime account")
        raise SystemExit(3) from None

    timeout = aiohttp.ClientTimeout(total=40)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        runtime = LabRuntime(options)
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
            return web.json_response({"status": "ok", "mode": runtime.status()["mode"]})

        async def status(_: web.Request) -> web.Response:
            return web.json_response(runtime.status())

        async def refresh(_: web.Request) -> web.Response:
            accepted, reason = runtime.request_refresh()
            return web.json_response(
                {"accepted": accepted, "reason": reason},
                status=202 if accepted else 409,
            )

        async def experiment(request: web.Request) -> web.Response:
            try:
                body = await request.json()
            except (ValueError, TypeError):
                body = {}
            token = body.get("intent_token") if isinstance(body, dict) else None
            accepted, reason = runtime.request_experiment(token)
            return web.json_response(
                {"accepted": accepted, "reason": reason},
                status=202 if accepted else 409,
            )

        app.router.add_get("/", page)
        app.router.add_get("/health", health)
        app.router.add_get("/api/v1/status", status)
        app.router.add_post("/api/v1/refresh", refresh)
        app.router.add_post("/api/v1/experiment/channel-11-ht20", experiment)

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8099)
        await site.start()
        LOGGER.info(
            "FREE THE DECO LAB %s started; writes %s",
            APP_VERSION,
            "ENABLED" if options.writes_enabled else "LOCKED",
        )

        loop = asyncio.get_running_loop()
        for signum in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(signum, runtime.stop)
            except NotImplementedError:
                pass

        task = asyncio.create_task(runtime.run(session))
        await runtime.wait_stopped()
        await task
        await runner.cleanup()
