"""Reduce raw Deco replies to a non-identifying research snapshot."""

import math
import re
from collections import Counter
from typing import Any

MAX_REPORTED_NUMBER = 10**15
NUMERIC_TEXT = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")


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
    ethernet_backhaul_ports = 0
    backhaul_speed_samples: list[float] = []
    backhaul_speed_unparsed = 0
    backhaul_max_speed_samples: list[float] = []
    backhaul_max_speed_unparsed = 0
    signal_samples: dict[str, list[float]] = {"band2_4": [], "band5": []}
    signal_unparsed: Counter[str] = Counter()
    internet_states: Counter[str] = Counter()

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
        for connection in _safe_labels(device.get("connection_type")):
            connections[connection] += 1

        ethernet_backhaul_ports += _safe_list_length(device.get("eth_bkhl_ports"))

        if (
            "backhual_speed" in device
            and device.get("backhual_speed") is not None
            and not _append_number(backhaul_speed_samples, device["backhual_speed"])
        ):
            backhaul_speed_unparsed += 1
        if (
            "backhual_max_speed" in device
            and device.get("backhual_max_speed") is not None
            and not _append_number(
                backhaul_max_speed_samples, device["backhual_max_speed"]
            )
        ):
            backhaul_max_speed_unparsed += 1

        signal_level = device.get("signal_level")
        if isinstance(signal_level, dict):
            for band, samples in signal_samples.items():
                if band not in signal_level or signal_level[band] is None:
                    continue
                if not _append_number(samples, signal_level[band]):
                    signal_unparsed[band] += 1

        internet_states[_internet_state(device.get("inet_status"))] += 1

    node_count = sum(1 for item in safe_devices if isinstance(item, dict))
    result = performance.get("result", {}) if isinstance(performance, dict) else {}
    if not isinstance(result, dict):
        result = {}

    safe_clients = clients if isinstance(clients, list) else []
    client_connections: Counter[str] = Counter()
    client_interfaces: Counter[str] = Counter()
    client_mesh: Counter[str] = Counter()
    client_priority: Counter[str] = Counter()
    client_restrictions: Counter[str] = Counter()
    down_speed_samples: list[float] = []
    down_speed_unparsed = 0
    up_speed_samples: list[float] = []
    up_speed_unparsed = 0
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

        client_mesh[_boolean_state(client.get("client_mesh"))] += 1
        client_priority[_boolean_state(client.get("enable_priority"))] += 1

        remain_time = _number(client.get("remain_time"))
        if remain_time is None:
            client_restrictions["unknown"] += 1
        elif remain_time > 0:
            client_restrictions["active"] += 1
        else:
            client_restrictions["inactive"] += 1

        if (
            "down_speed" in client
            and client.get("down_speed") is not None
            and not _append_number(down_speed_samples, client["down_speed"])
        ):
            down_speed_unparsed += 1
        if (
            "up_speed" in client
            and client.get("up_speed") is not None
            and not _append_number(up_speed_samples, client["up_speed"])
        ):
            up_speed_unparsed += 1

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
        "mesh_health": {
            "backhaul": {
                "connection_types": dict(sorted(connections.items())),
                "ethernet_backhaul_ports_reported": ethernet_backhaul_ports,
                "reported_unit": "megabits_per_second",
                "speed": _numeric_summary(
                    backhaul_speed_samples, backhaul_speed_unparsed
                ),
                "maximum_speed": _numeric_summary(
                    backhaul_max_speed_samples, backhaul_max_speed_unparsed
                ),
            },
            "signal": {
                band: _numeric_summary(signal_samples[band], signal_unparsed[band])
                for band in signal_samples
            },
            "internet": {
                "states": dict(sorted(internet_states.items())),
            },
        },
        "connected_clients": {
            "reported_count": client_count,
            "online_count": online_clients,
            "connection_types": dict(sorted(client_connections.items())),
            "interfaces": dict(sorted(client_interfaces.items())),
            "mesh_membership": dict(sorted(client_mesh.items())),
            "priority": dict(sorted(client_priority.items())),
            "restrictions": dict(sorted(client_restrictions.items())),
            "traffic": {
                "reported_unit": "firmware_native",
                "download": _numeric_summary(
                    down_speed_samples, down_speed_unparsed
                ),
                "upload": _numeric_summary(up_speed_samples, up_speed_unparsed),
            },
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


def _safe_labels(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    labels = []
    for item in values:
        label = _safe_label(item)
        if label:
            labels.append(label)
    return labels


def _safe_list_length(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _internet_state(value: object) -> str:
    if value is True:
        return "online"
    if value is False:
        return "offline"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"online", "connected", "up"}:
            return "online"
        if normalized in {"offline", "disconnected", "down"}:
            return "offline"
    return "unknown"


def _boolean_state(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "unknown"


def _number(value: object) -> float | None:
    number: float
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str) and NUMERIC_TEXT.fullmatch(value.strip()):
        number = float(value.strip())
    else:
        return None
    if not math.isfinite(number) or not 0 <= number <= MAX_REPORTED_NUMBER:
        return None
    return number


def _append_number(target: list[float], value: object) -> bool:
    number = _number(value)
    if number is None:
        return False
    target.append(number)
    return True


def _numeric_summary(
    values: list[float], unparsed_count: int = 0
) -> dict[str, int | float | None]:
    if not values:
        return {
            "sample_count": 0,
            "nonzero_count": 0,
            "unparsed_count": unparsed_count,
            "total": None,
            "average": None,
            "minimum": None,
            "maximum": None,
        }
    total = sum(values)
    return {
        "sample_count": len(values),
        "nonzero_count": sum(value > 0 for value in values),
        "unparsed_count": unparsed_count,
        "total": round(total, 3),
        "average": round(total / len(values), 3),
        "minimum": round(min(values), 3),
        "maximum": round(max(values), 3),
    }


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
