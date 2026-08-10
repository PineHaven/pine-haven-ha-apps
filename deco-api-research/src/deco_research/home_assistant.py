"""Publish sanitized FREE THE DECO telemetry to Home Assistant."""

import os
from typing import Any

import aiohttp

CORE_API_BASE = "http://supervisor/core/api"


class HomeAssistantPublishError(RuntimeError):
    """A redacted Home Assistant publishing failure."""


class HomeAssistantPublisher:
    """Write state-only telemetry through the App's scoped HA API token."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        token: str | None = None,
        api_base: str = CORE_API_BASE,
    ) -> None:
        self._session = session
        self._token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN")
        self._api_base = api_base.rstrip("/")
        self._last_payloads: dict[str, dict[str, Any]] = {}

    @property
    def available(self) -> bool:
        return bool(self._token)

    async def publish(self, status: dict[str, Any]) -> tuple[int, int]:
        """Publish changed entities and return changed/total counts."""

        if not self._token:
            raise HomeAssistantPublishError("home_assistant_token_unavailable")

        payloads = build_entity_states(status)
        changed = 0
        for entity_id, payload in payloads.items():
            if self._last_payloads.get(entity_id) == payload:
                continue
            await self._post_state(entity_id, payload)
            self._last_payloads[entity_id] = payload
            changed += 1
        return changed, len(payloads)

    async def _post_state(self, entity_id: str, payload: dict[str, Any]) -> None:
        try:
            response = await self._session.post(
                f"{self._api_base}/states/{entity_id}",
                headers={"Authorization": f"Bearer {self._token}"},
                json=payload,
            )
            response.raise_for_status()
            await response.read()
            response.release()
        except aiohttp.ClientError as err:
            raise HomeAssistantPublishError("home_assistant_publish_failed") from err


def build_entity_states(status: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Convert only sanitized status fields into Home Assistant states."""

    mode = status.get("mode", "unknown")
    last_success = status.get("last_success_at")
    mesh = status.get("mesh") if isinstance(status.get("mesh"), dict) else {}
    entities: dict[str, dict[str, Any]] = {}

    _add(
        entities,
        "binary_sensor.free_the_deco_monitoring_healthy",
        "on" if mode in {"healthy", "degraded"} else "off",
        "FREE THE DECO Monitoring Healthy",
        "mdi:router-wireless",
        device_class="connectivity",
        mode=mode,
        error_code=status.get("error_code"),
    )
    _add(
        entities,
        "sensor.free_the_deco_last_success",
        last_success or "unknown",
        "FREE THE DECO Last Success",
        "mdi:clock-check-outline",
        device_class="timestamp",
    )

    if not mesh:
        return entities

    _add_metric(
        entities,
        "sensor.free_the_deco_online_nodes",
        mesh.get("online_count"),
        "FREE THE DECO Online Nodes",
        "mdi:access-point-network",
        total_nodes=mesh.get("node_count"),
        offline_nodes=mesh.get("offline_count"),
    )
    _add_metric(
        entities,
        "sensor.free_the_deco_offline_nodes",
        mesh.get("offline_count"),
        "FREE THE DECO Offline Nodes",
        "mdi:access-point-network-off",
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
        unit_of_measurement="MHz",
    )

    nodes = mesh.get("nodes", [])
    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                continue
            node_id = node["id"]
            name = str(node.get("name") or "Deco")
            _add(
                entities,
                f"binary_sensor.free_the_deco_{node_id}_online",
                "on" if node.get("online") is True else "off",
                f"{name} Deco Online",
                "mdi:access-point-network",
                device_class="connectivity",
                internet=node.get("internet"),
                role=node.get("role"),
                connection_types=node.get("connection_types"),
                signal_2_4=node.get("signal_2_4"),
                signal_5=node.get("signal_5"),
            )
            if node.get("backhaul_speed_mbps") is not None:
                _add_metric(
                    entities,
                    f"sensor.free_the_deco_{node_id}_backhaul_speed",
                    node.get("backhaul_speed_mbps"),
                    f"{name} Deco Backhaul Speed",
                    "mdi:ethernet",
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
    **attributes: object,
) -> None:
    _add(
        entities,
        entity_id,
        "unknown" if state is None else state,
        name,
        icon,
        **attributes,
    )


def _add(
    entities: dict[str, dict[str, Any]],
    entity_id: str,
    state: object,
    name: str,
    icon: str,
    **attributes: object,
) -> None:
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
    entities[entity_id] = {"state": state, "attributes": clean_attributes}
