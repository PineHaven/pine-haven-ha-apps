"""Reduce raw Deco replies to a non-identifying research snapshot."""

from collections import Counter
from typing import Any


def build_snapshot(
    devices: object, performance: object, clients: object | None = None
) -> dict[str, Any]:
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

    safe_clients = clients if isinstance(clients, list) else []
    client_connections: Counter[str] = Counter()
    client_interfaces: Counter[str] = Counter()
    online_clients = 0
    for client in safe_clients:
        if not isinstance(client, dict):
            continue
        if client.get("online") is True:
            online_clients += 1
        connection = _safe_label(client.get("connection_type"))
        if connection:
            client_connections[connection] += 1
        interface = _safe_label(client.get("interface"))
        if interface:
            client_interfaces[interface] += 1

    client_count = sum(1 for item in safe_clients if isinstance(item, dict))

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
        "connected_clients": {
            "reported_count": client_count,
            "online_count": online_clients,
            "connection_types": dict(sorted(client_connections.items())),
            "interfaces": dict(sorted(client_interfaces.items())),
        },
        "observed_fields": {
            "device_records": _record_field_types(safe_devices),
            "client_records": _record_field_types(safe_clients),
            "performance_result": _field_types(result),
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


def _record_field_types(records: list[object]) -> dict[str, list[str]]:
    observed: dict[str, set[str]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        for key, value in record.items():
            safe_key = _safe_label(key)
            if safe_key:
                observed.setdefault(safe_key, set()).add(_value_type(value))
    return {key: sorted(types) for key, types in sorted(observed.items())}


def _field_types(record: dict[object, object]) -> dict[str, list[str]]:
    return _record_field_types([record])


def _value_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    return "other"
