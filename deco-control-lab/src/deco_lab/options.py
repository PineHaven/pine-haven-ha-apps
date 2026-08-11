"""Strict configuration parsing for the isolated FREE THE DECO laboratory."""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


class OptionsError(ValueError):
    """An intentionally non-secret configuration error."""


@dataclass(frozen=True)
class LabOptions:
    """Validated App options. Secrets are never rendered or logged."""

    lab_enabled: bool
    isolated_single_node_acknowledged: bool
    firmware_write_compatibility_acknowledged: bool
    writes_enabled: bool
    host: str
    production_host: str
    username: str
    password: str
    expected_mac: str
    verify_ssl: bool
    hold_seconds: int

    @classmethod
    def from_dict(cls, data: dict) -> "LabOptions":
        enabled = data.get("lab_enabled") is True
        isolated_ack = data.get("isolated_single_node_acknowledged") is True
        firmware_ack = (
            data.get("firmware_write_compatibility_acknowledged") is True
        )
        writes_enabled = data.get("writes_enabled") is True
        host = _normalize_host(data.get("host"))
        production_host = _normalize_host(data.get("production_host"))
        username = _required_text(data.get("username"))
        password = _required_text(data.get("password"))
        expected_mac = normalize_mac(data.get("expected_mac"))
        verify_ssl = data.get("verify_ssl") is True
        hold_seconds = _hold_seconds(data.get("hold_seconds", 60))

        if enabled and not isolated_ack:
            raise OptionsError("lab_requires_isolation_acknowledgement")
        if enabled and not all(
            (host, production_host, username, password, expected_mac)
        ):
            raise OptionsError("lab_requires_target_identity_and_credentials")
        if enabled and _same_host(host, production_host):
            raise OptionsError("lab_target_must_not_equal_production_target")
        if writes_enabled and not enabled:
            raise OptionsError("writes_require_enabled_lab")
        if writes_enabled and not firmware_ack:
            raise OptionsError("writes_require_firmware_compatibility_acknowledgement")

        return cls(
            lab_enabled=enabled,
            isolated_single_node_acknowledged=isolated_ack,
            firmware_write_compatibility_acknowledged=firmware_ack,
            writes_enabled=writes_enabled,
            host=host or "",
            production_host=production_host or "",
            username=username or "",
            password=password or "",
            expected_mac=expected_mac or "",
            verify_ssl=verify_ssl,
            hold_seconds=hold_seconds,
        )


def load_options(path: str | Path = "/data/options.json") -> LabOptions:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise OptionsError("options_must_be_an_object")
    return LabOptions.from_dict(data)


def normalize_mac(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    compact = re.sub(r"[^0-9a-fA-F]", "", value)
    if len(compact) != 12:
        return None
    return "-".join(
        compact[index : index + 2] for index in range(0, 12, 2)
    ).upper()


def _normalize_host(value: object) -> str | None:
    value = _required_text(value)
    if value is None:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OptionsError("target_must_be_http_or_https")
    if parsed.username is not None or parsed.password is not None:
        raise OptionsError("target_must_not_contain_credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise OptionsError("target_must_not_contain_path_query_or_fragment")
    try:
        port = parsed.port
    except ValueError as err:
        raise OptionsError("invalid_target_port") from err
    if port is not None and not 1 <= port <= 65535:
        raise OptionsError("invalid_target_port")
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


def _required_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _hold_seconds(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OptionsError("hold_seconds_must_be_an_integer")
    if not 15 <= value <= 300:
        raise OptionsError("hold_seconds_out_of_range")
    return value


def _same_host(first: str | None, second: str | None) -> bool:
    if not first or not second:
        return False
    return urlsplit(first).hostname == urlsplit(second).hostname
