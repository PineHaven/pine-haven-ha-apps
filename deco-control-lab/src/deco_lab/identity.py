"""Identity and radio sanitizers for the one-Deco laboratory."""

import re
from typing import Any

from .options import normalize_mac


def verify_single_lab_node(devices: object, expected_mac: str) -> dict[str, Any]:
    """Return a non-identifying gate result for exactly one expected controller."""

    records = (
        [item for item in devices if isinstance(item, dict)]
        if isinstance(devices, list)
        else []
    )
    only = records[0] if len(records) == 1 else {}
    observed_mac = normalize_mac(only.get("mac"))
    role = str(only.get("role", "")).strip().lower()
    model = _safe_label(only.get("device_model"))
    hardware = _safe_label(only.get("hardware_ver"))
    firmware = _safe_label(only.get("software_ver"))
    model_supported = _normalized_label(model) in {"m9plus", "decom9plus"}
    hardware_supported = _normalized_label(hardware) in {
        "2",
        "20",
        "v2",
        "v20",
    }
    online = str(only.get("group_status", "")).strip().lower() == "connected"
    expected_match = bool(observed_mac and observed_mac == expected_mac)
    controller = role == "master"
    return {
        "node_count": len(records),
        "single_node": len(records) == 1,
        "expected_identity_match": expected_match,
        "expected_mac_suffix": (
            expected_mac[-5:].replace("-", ":") if expected_mac else None
        ),
        "controller_role": controller,
        "online": online,
        "model": model,
        "model_supported": model_supported,
        "hardware_version": hardware,
        "hardware_supported": hardware_supported,
        "firmware_version": firmware,
        "ready": (
            len(records) == 1
            and expected_match
            and controller
            and online
            and model_supported
            and hardware_supported
        ),
    }


def radio_snapshot(wireless: object) -> dict[str, Any]:
    source = wireless if isinstance(wireless, dict) else {}
    band = source.get("band2_4")
    band_data = band if isinstance(band, dict) else {}
    host = band_data.get("host")
    host_data = host if isinstance(host, dict) else {}
    width = host_data.get("bandwidth")
    if width is None:
        width = host_data.get("channel_width")
    return {
        "channel": _channel(host_data.get("channel")),
        "bandwidth": _bandwidth(width),
        "automatic_channel": _optional_boolean(host_data.get("auto_channel")),
        "automatic_width": _optional_boolean(host_data.get("auto_bandwidth")),
    }


def _channel(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        channel = value
    elif isinstance(value, str) and value.strip().isdigit():
        channel = int(value.strip())
    else:
        return None
    return channel if 1 <= channel <= 13 else None


def _bandwidth(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper().replace(" ", "")
    if normalized in {"HT20", "20", "20MHZ"}:
        return "HT20"
    if normalized in {"HT40", "HT40+", "HT40-", "40", "40MHZ"}:
        return "HT40"
    return None


def _optional_boolean(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def _safe_label(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 96 or any(ord(char) < 32 for char in value):
        return None
    if re.search(r"(?:ssid|password|secret)", value, re.IGNORECASE):
        return None
    return value


def _normalized_label(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())
