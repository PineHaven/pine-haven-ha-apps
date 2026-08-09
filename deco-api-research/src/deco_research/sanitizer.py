"""Reduce raw Deco replies to a non-identifying research snapshot."""

from collections import Counter
from typing import Any


def build_snapshot(devices: object, performance: object) -> dict[str, Any]:
    """Return only aggregate or low-risk categorical mesh information."""

    safe_devices = devices if isinstance(devices, list) else []
    online_count = 0
    master_count = 0
    models: set[str] = set()
    hardware_versions: set[str] = set()
    firmware_versions: set[str] = set()
    connections: Counter[str] = Counter()

    for device in safe_devices:
        if not isinstance(device, dict):
            continue
        if str(device.get("group_status", "")).lower() == "connected":
            online_count += 1
        if str(device.get("role", "")).lower() == "master":
            master_count += 1

        _add_label(models, device.get("device_model"))
        _add_label(hardware_versions, device.get("hardware_ver"))
        _add_label(firmware_versions, device.get("software_ver"))
        connection = _safe_label(device.get("connection_type"))
        if connection:
            connections[connection] += 1

    node_count = sum(1 for item in safe_devices if isinstance(item, dict))
    result = performance.get("result", {}) if isinstance(performance, dict) else {}
    if not isinstance(result, dict):
        result = {}

    return {
        "node_count": node_count,
        "online_count": online_count,
        "offline_count": max(node_count - online_count, 0),
        "master_count": master_count,
        "models": sorted(models),
        "hardware_versions": sorted(hardware_versions),
        "firmware_versions": sorted(firmware_versions),
        "connection_types": dict(sorted(connections.items())),
        "controller_performance": {
            "cpu_percent": _fraction_as_percent(result.get("cpu_usage")),
            "memory_percent": _fraction_as_percent(result.get("mem_usage")),
        },
    }


def _add_label(target: set[str], value: object) -> None:
    label = _safe_label(value)
    if label:
        target.add(label)


def _safe_label(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 96:
        return None
    if any(ord(character) < 32 for character in value):
        return None
    return value


def _fraction_as_percent(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    percent = float(value) * 100
    if not 0 <= percent <= 100:
        return None
    return round(percent, 1)
