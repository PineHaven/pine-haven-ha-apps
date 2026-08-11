"""Publish sanitized FREE THE DECO telemetry through MQTT Discovery."""

import json
import os
from typing import Any

import aiohttp

CORE_API_BASE = "http://supervisor/core/api"
MQTT_STATE_TOPIC = "free_the_deco/state"
DISCOVERY_PREFIX = "homeassistant/device"
SUPPORT_URL = "https://github.com/PineHaven/pine-haven-ha-apps"


class HomeAssistantPublishError(RuntimeError):
    """A redacted Home Assistant publishing failure."""


class HomeAssistantPublisher:
    """Register durable MQTT entities using only Home Assistant's scoped API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str | None = None,
        api_base: str = CORE_API_BASE,
    ) -> None:
        self._session = session
        self._token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN")
        self._api_base = api_base.rstrip("/")
        self._last_entity_payloads: dict[str, dict[str, Any]] = {}
        self._last_discovery_payloads: dict[str, str] = {}

    @property
    def available(self) -> bool:
        return bool(self._token)

    async def publish(self, status: dict[str, Any]) -> tuple[int, int]:
        """Publish discovery plus one sanitized state packet."""

        if not self._token:
            raise HomeAssistantPublishError("home_assistant_token_unavailable")

        entities = build_entity_states(status)
        discovery = build_device_discovery(status, entities)
        removed_topics = set(self._last_discovery_payloads) - set(discovery)
        for topic in sorted(removed_topics):
            await self._mqtt_publish(topic, "", retain=True)
            del self._last_discovery_payloads[topic]
        for topic, payload in discovery.items():
            if self._last_discovery_payloads.get(topic) == payload:
                continue
            await self._mqtt_publish(topic, payload, retain=True)
            self._last_discovery_payloads[topic] = payload

        state_payload = json.dumps(
            {
                entry["object_id"]: {
                    "state": entry["state"],
                    "attributes": entry["attributes"],
                }
                for entry in entities.values()
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        # State is intentionally not retained. expire_after in discovery makes
        # entities unavailable if the App stops, without restoring ghost data.
        await self._mqtt_publish(MQTT_STATE_TOPIC, state_payload, retain=False)

        changed = sum(
            self._last_entity_payloads.get(entity_id) != payload
            for entity_id, payload in entities.items()
        )
        self._last_entity_payloads = entities
        return changed, len(entities)

    async def _mqtt_publish(self, topic: str, payload: str, retain: bool) -> None:
        try:
            response = await self._session.post(
                f"{self._api_base}/services/mqtt/publish",
                headers={"Authorization": f"Bearer {self._token}"},
                json={
                    "topic": topic,
                    "payload": payload,
                    "qos": 1,
                    "retain": retain,
                },
            )
            response.raise_for_status()
            await response.read()
            response.release()
        except aiohttp.ClientResponseError as err:
            code = (
                "home_assistant_mqtt_unavailable"
                if err.status in {404, 405}
                else "home_assistant_publish_failed"
            )
            raise HomeAssistantPublishError(code) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HomeAssistantPublishError("home_assistant_publish_failed") from err


def build_device_discovery(
    status: dict[str, Any], entities: dict[str, dict[str, Any]]
) -> dict[str, str]:
    """Create one retained Device Discovery document per logical device."""

    app_version = str(status.get("app_version") or "unknown")
    expire_after = _safe_positive_int(status.get("mqtt_expire_after_seconds"), 240)
    mesh = status.get("mesh") if isinstance(status.get("mesh"), dict) else {}
    nodes = {
        node.get("id"): node
        for node in mesh.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entities.values():
        grouped.setdefault(entry["device_key"], []).append(entry)

    messages: dict[str, str] = {}
    for device_key, entries in sorted(grouped.items()):
        if device_key == "monitor":
            device = {
                "identifiers": ["free_the_deco_monitor"],
                "name": "FREE THE DECO",
                "manufacturer": "Pine Haven",
                "model": "Local Deco Monitor",
                "sw_version": app_version,
            }
        else:
            node_id = device_key.removeprefix("node_")
            node = nodes.get(node_id, {})
            node_name = str(node.get("name") or "Deco")
            device = {
                "identifiers": [f"free_the_deco_node_{node_id}"],
                "name": f"{node_name} Deco",
                "manufacturer": "TP-Link",
                "model": str(node.get("model") or "Deco M9 Plus"),
            }
            if node.get("hardware_version"):
                device["hw_version"] = str(node["hardware_version"])
            if node.get("firmware_version"):
                device["sw_version"] = str(node["firmware_version"])

        components: dict[str, dict[str, Any]] = {}
        for entry in sorted(entries, key=lambda item: item["object_id"]):
            object_id = entry["object_id"]
            component = dict(entry["discovery"])
            state_expression = f"value_json[{object_id!r}][\"state\"]"
            if "state_class" in component or "unit_of_measurement" in component:
                value_template = (
                    "{{ "
                    + state_expression
                    + " if "
                    + state_expression
                    + " is number else 'None' }}"
                )
            elif component.get("device_class") == "timestamp":
                value_template = (
                    "{{ "
                    + state_expression
                    + " if "
                    + state_expression
                    + " is string and "
                    + state_expression
                    + " != 'unknown' else 'None' }}"
                )
            else:
                value_template = "{{ " + state_expression + " }}"
            component.update(
                {
                    "platform": entry["component"],
                    "unique_id": object_id,
                    "default_entity_id": entry["entity_id"],
                    "value_template": value_template,
                    "json_attributes_topic": MQTT_STATE_TOPIC,
                    "json_attributes_template": (
                        "{{ value_json["
                        + repr(object_id)
                        + "][\"attributes\"] | to_json }}"
                    ),
                    "expire_after": expire_after,
                }
            )
            components[object_id] = component

        payload = {
            "device": device,
            "origin": {
                "name": "FREE THE DECO",
                "sw_version": app_version,
                "support_url": SUPPORT_URL,
            },
            "state_topic": MQTT_STATE_TOPIC,
            "qos": 1,
            "components": components,
        }
        topic = f"{DISCOVERY_PREFIX}/free_the_deco_{device_key}/config"
        messages[topic] = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return messages


def build_entity_states(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Convert only sanitized status fields into durable entity definitions."""

    mode = str(status.get("mode") or "unknown")
    last_success = status.get("last_success_at")
    mesh = status.get("mesh") if isinstance(status.get("mesh"), dict) else {}
    health = status.get("health") if isinstance(status.get("health"), dict) else {}
    publisher = (
        status.get("publisher") if isinstance(status.get("publisher"), dict) else {}
    )
    refresh = (
        status.get("manual_refresh")
        if isinstance(status.get("manual_refresh"), dict)
        else {}
    )
    recovery = (
        status.get("recovery") if isinstance(status.get("recovery"), dict) else {}
    )
    entities: dict[str, dict[str, Any]] = {}

    _add(
        entities,
        "binary_sensor.free_the_deco_monitoring_healthy",
        "on" if mode in {"healthy", "degraded"} and not status.get("data_stale") else "off",
        "FREE THE DECO Monitoring Healthy",
        "mdi:router-wireless",
        component_name="Monitoring Healthy",
        device_class="connectivity",
        mode=mode,
        error_code=status.get("error_code"),
    )
    _add(
        entities,
        "binary_sensor.free_the_deco_data_stale",
        "on" if status.get("data_stale") is True else "off",
        "FREE THE DECO Data Stale",
        "mdi:database-clock-outline",
        component_name="Data Stale",
        device_class="problem",
        stale_after_seconds=status.get("stale_after_seconds"),
    )
    for entity_id, state, name, component_name, icon in (
        (
            "sensor.free_the_deco_last_success",
            last_success or "unknown",
            "FREE THE DECO Last Success",
            "Last Success",
            "mdi:clock-check-outline",
        ),
        (
            "sensor.free_the_deco_last_attempt",
            status.get("last_attempt_at") or "unknown",
            "FREE THE DECO Last Attempt",
            "Last Attempt",
            "mdi:clock-outline",
        ),
        (
            "sensor.free_the_deco_next_poll",
            status.get("next_poll_at") or "unknown",
            "FREE THE DECO Next Poll",
            "Next Poll",
            "mdi:clock-fast",
        ),
    ):
        _add(
            entities,
            entity_id,
            state,
            name,
            icon,
            component_name=component_name,
            device_class="timestamp",
        )

    for entity_id, state, name, component_name, icon in (
        (
            "sensor.free_the_deco_app_uptime",
            status.get("app_uptime_seconds"),
            "FREE THE DECO App Uptime",
            "App Uptime",
            "mdi:timer-outline",
        ),
        (
            "sensor.free_the_deco_poll_age",
            status.get("poll_age_seconds"),
            "FREE THE DECO Poll Age",
            "Poll Age",
            "mdi:clock-alert-outline",
        ),
    ):
        _add_metric(
            entities,
            entity_id,
            state,
            name,
            icon,
            component_name=component_name,
            device_class="duration",
            unit_of_measurement="s",
            state_class="measurement",
        )

    for key, suffix, name, component_name in (
        ("successful_cycles", "successful_cycles", "Successful Cycles", "Successful Cycles"),
        ("failed_cycles", "failed_cycles", "Failed Cycles", "Failed Cycles"),
        (
            "consecutive_failures",
            "consecutive_failures",
            "Consecutive Failures",
            "Consecutive Failures",
        ),
    ):
        _add_metric(
            entities,
            f"sensor.free_the_deco_{suffix}",
            status.get(key, 0),
            f"FREE THE DECO {name}",
            "mdi:counter",
            component_name=component_name,
        )

    health_rows = (
        ("deco_read", "deco_read_health", "Deco Read Health", "Deco Read Health"),
        ("session", "session_health", "Session Health", "Session Health"),
    )
    for key, suffix, name, component_name in health_rows:
        value = health.get(key, {}) if isinstance(health.get(key), dict) else {}
        _add(
            entities,
            f"sensor.free_the_deco_{suffix}",
            value.get("status", "unknown"),
            f"FREE THE DECO {name}",
            "mdi:heart-pulse",
            component_name=component_name,
            error_code=value.get("error_code"),
            last_success_at=value.get("last_success_at"),
        )
    _add(
        entities,
        "sensor.free_the_deco_home_assistant_publishing_health",
        publisher.get("status", "unknown"),
        "FREE THE DECO Home Assistant Publishing Health",
        "mdi:home-assistant",
        component_name="Home Assistant Publishing Health",
        error_code=publisher.get("error_code"),
        last_publish_at=publisher.get("last_publish_at"),
    )
    _add(
        entities,
        "sensor.free_the_deco_last_error_category",
        status.get("error_code") or "none",
        "FREE THE DECO Last Error Category",
        "mdi:alert-circle-outline",
        component_name="Last Error Category",
    )
    _add(
        entities,
        "sensor.free_the_deco_recovery_status",
        recovery.get("status", "not_needed"),
        "FREE THE DECO Recovery Status",
        "mdi:restore",
        component_name="Recovery Status",
        last_recovery_at=recovery.get("last_recovery_at"),
    )
    _add(
        entities,
        "sensor.free_the_deco_manual_refresh_status",
        refresh.get("status", "idle"),
        "FREE THE DECO Manual Refresh Status",
        "mdi:refresh",
        component_name="Manual Refresh Status",
        requested_at=refresh.get("requested_at"),
        completed_at=refresh.get("completed_at"),
        error_code=refresh.get("error_code"),
    )

    if not mesh:
        return entities

    _add_metric(
        entities,
        "sensor.free_the_deco_online_nodes",
        mesh.get("online_count"),
        "FREE THE DECO Online Nodes",
        "mdi:access-point-network",
        component_name="Online Nodes",
        total_nodes=mesh.get("node_count"),
        offline_nodes=mesh.get("offline_count"),
    )
    _add_metric(
        entities,
        "sensor.free_the_deco_offline_nodes",
        mesh.get("offline_count"),
        "FREE THE DECO Offline Nodes",
        "mdi:access-point-network-off",
        component_name="Offline Nodes",
    )

    clients = mesh.get("connected_clients", {})
    connections = (
        clients.get("connection_types", {}) if isinstance(clients, dict) else {}
    )
    interfaces = clients.get("interfaces", {}) if isinstance(clients, dict) else {}
    _add_metric(
        entities,
        "sensor.free_the_deco_connected_clients",
        clients.get("reported_count") if isinstance(clients, dict) else None,
        "FREE THE DECO Connected Clients",
        "mdi:devices",
        component_name="Connected Clients",
        connection_types=connections,
        interfaces=interfaces,
    )
    for key, suffix, name, icon in (
        ("band2_4", "2_4_ghz_clients", "2.4 GHz Clients", "mdi:wifi"),
        ("band5", "5_ghz_clients", "5 GHz Clients", "mdi:wifi"),
        ("wired", "wired_clients", "Wired Clients", "mdi:ethernet"),
    ):
        _add_metric(
            entities,
            f"sensor.free_the_deco_{suffix}",
            connections.get(key, 0) if isinstance(connections, dict) else 0,
            f"FREE THE DECO {name}",
            icon,
            component_name=name,
        )

    performance = mesh.get("controller_performance", {})
    for key, suffix, name in (
        ("cpu_percent", "controller_cpu", "Controller CPU"),
        ("memory_percent", "controller_memory", "Controller Memory"),
    ):
        _add_metric(
            entities,
            f"sensor.free_the_deco_{suffix}",
            performance.get(key) if isinstance(performance, dict) else None,
            f"FREE THE DECO {name}",
            "mdi:memory",
            component_name=name,
            unit_of_measurement="%",
            state_class="measurement",
        )

    radio = mesh.get("wireless_radio", {})
    band2 = radio.get("band2_4", {}) if isinstance(radio, dict) else {}
    _add_metric(
        entities,
        "sensor.free_the_deco_2_4_ghz_channel",
        band2.get("channel") if isinstance(band2, dict) else None,
        "FREE THE DECO 2.4 GHz Channel",
        "mdi:radio-tower",
        component_name="2.4 GHz Channel",
        configured_width_mhz=(
            band2.get("configured_width_mhz") if isinstance(band2, dict) else None
        ),
        pine_haven_zigbee_channels=[11, 15, 20],
    )
    _add_metric(
        entities,
        "sensor.free_the_deco_2_4_ghz_width",
        band2.get("configured_width_mhz") if isinstance(band2, dict) else None,
        "FREE THE DECO 2.4 GHz Width",
        "mdi:arrow-expand-horizontal",
        component_name="2.4 GHz Width",
        unit_of_measurement="MHz",
    )

    coexistence = mesh.get("coexistence", {})
    current = (
        coexistence.get("current", {}) if isinstance(coexistence, dict) else {}
    )
    networks = (
        current.get("zigbee_networks", []) if isinstance(current, dict) else []
    )
    control = (
        coexistence.get("control_readiness", {})
        if isinstance(coexistence, dict)
        else {}
    )
    _add(
        entities,
        "sensor.free_the_deco_zigbee_coexistence_risk",
        current.get("risk", "unknown") if isinstance(current, dict) else "unknown",
        "FREE THE DECO Zigbee Coexistence Risk",
        "mdi:access-point-network-off",
        component_name="Zigbee Coexistence Risk",
        model=coexistence.get("model") if isinstance(coexistence, dict) else None,
        zigbee_networks=networks,
    )
    _add(
        entities,
        "sensor.free_the_deco_radio_control_readiness",
        control.get("state", "unknown") if isinstance(control, dict) else "unknown",
        "FREE THE DECO Radio Control Readiness",
        "mdi:lock-outline",
        component_name="Radio Control Readiness",
        writes_enabled=(
            control.get("writes_enabled") if isinstance(control, dict) else None
        ),
        live_validation=(
            control.get("live_validation") if isinstance(control, dict) else None
        ),
        required_next_step=(
            control.get("required_next_step") if isinstance(control, dict) else None
        ),
    )

    nodes = mesh.get("nodes", [])
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                continue
            node_id = node["id"]
            name = str(node.get("name") or "Deco")
            device_key = f"node_{node_id}"
            _add(
                entities,
                f"binary_sensor.free_the_deco_{node_id}_online",
                "on" if node.get("online") is True else "off",
                f"{name} Deco Online",
                "mdi:access-point-network",
                component_name="Online",
                device_key=device_key,
                device_class="connectivity",
                internet=node.get("internet"),
                role=node.get("role"),
                connection_types=node.get("connection_types"),
                signal_2_4=node.get("signal_2_4"),
                signal_5=node.get("signal_5"),
            )
            _add_metric(
                entities,
                f"sensor.free_the_deco_{node_id}_backhaul_speed",
                node.get("backhaul_speed_mbps"),
                f"{name} Deco Backhaul Speed",
                "mdi:ethernet",
                component_name="Backhaul Speed",
                device_key=device_key,
                unit_of_measurement="Mbit/s",
                state_class="measurement",
                maximum_mbps=node.get("backhaul_max_speed_mbps"),
            )

    return entities


def _add_metric(
    entities: dict[str, dict[str, Any]],
    entity_id: str,
    state: object,
    name: str,
    icon: str,
    **metadata_and_attributes: object,
) -> None:
    _add(
        entities,
        entity_id,
        "unknown" if state is None else state,
        name,
        icon,
        **metadata_and_attributes,
    )


def _add(
    entities: dict[str, dict[str, Any]],
    entity_id: str,
    state: object,
    name: str,
    icon: str,
    *,
    component_name: str,
    device_key: str = "monitor",
    device_class: str | None = None,
    state_class: str | None = None,
    unit_of_measurement: str | None = None,
    **attributes: object,
) -> None:
    component, object_id = entity_id.split(".", 1)
    clean_attributes = {
        key: value for key, value in attributes.items() if value is not None
    }
    clean_attributes.update(
        {
            "friendly_name": name,
            "icon": icon,
            "source": "FREE THE DECO",
        }
    )
    discovery: dict[str, Any] = {
        "name": component_name,
        "icon": icon,
        "entity_category": "diagnostic",
    }
    if device_class:
        discovery["device_class"] = device_class
    if state_class:
        discovery["state_class"] = state_class
    if unit_of_measurement:
        discovery["unit_of_measurement"] = unit_of_measurement
    if component == "binary_sensor":
        discovery.update({"payload_on": "on", "payload_off": "off"})

    entities[entity_id] = {
        "entity_id": entity_id,
        "object_id": object_id,
        "component": component,
        "device_key": device_key,
        "state": state,
        "attributes": clean_attributes,
        "discovery": discovery,
    }


def _safe_positive_int(value: object, default: int) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return default
