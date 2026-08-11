import json
import unittest

from deco_research.home_assistant import (
    MQTT_STATE_TOPIC,
    HomeAssistantPublisher,
    build_device_discovery,
    build_entity_states,
)


class _Response:
    @staticmethod
    def raise_for_status():
        return None

    @staticmethod
    async def read():
        return b""

    @staticmethod
    def release():
        return None


class _Session:
    def __init__(self):
        self.posts = []

    async def post(self, url, **kwargs):
        self.posts.append((url, kwargs))
        return _Response()


def _status():
    return {
        "schema_version": 4,
        "app_version": "1.2.0",
        "mode": "healthy",
        "last_success_at": "2026-08-10T12:00:00+00:00",
        "last_attempt_at": "2026-08-10T12:00:00+00:00",
        "next_poll_at": "2026-08-10T12:01:00+00:00",
        "app_uptime_seconds": 600,
        "poll_age_seconds": 0,
        "stale_after_seconds": 180,
        "mqtt_expire_after_seconds": 240,
        "data_stale": False,
        "successful_cycles": 10,
        "failed_cycles": 1,
        "consecutive_failures": 0,
        "health": {
            "deco_read": {"status": "healthy"},
            "session": {"status": "authenticated"},
        },
        "publisher": {"status": "healthy"},
        "recovery": {"status": "not_needed"},
        "manual_refresh": {"status": "idle"},
        "mesh": {
            "node_count": 1,
            "online_count": 1,
            "offline_count": 0,
            "nodes": [
                {
                    "id": "m9plus",
                    "name": "Workshop",
                    "model": "Deco M9 Plus",
                    "hardware_version": "2.0",
                    "firmware_version": "1.9.1",
                    "online": True,
                    "internet": "online",
                    "role": "controller",
                    "connection_types": [],
                    "signal_2_4": 3,
                    "signal_5": 3,
                    "backhaul_speed_mbps": None,
                }
            ],
            "controller_performance": {
                "cpu_percent": 32.0,
                "memory_percent": 34.0,
            },
            "connected_clients": {
                "reported_count": 9,
                "connection_types": {"band2_4": 4, "band5": 3, "wired": 2},
                "interfaces": {"main": 9},
            },
            "wireless_radio": {"band2_4": {"channel": 4, "configured_width_mhz": 40}},
            "coexistence": {
                "model": "conservative_frequency_geometry_v1",
                "current": {
                    "risk": "high",
                    "zigbee_networks": [
                        {"id": "core", "channel": 15, "risk": "primary_overlap"}
                    ],
                },
                "control_readiness": {
                    "state": "disarmed",
                    "writes_enabled": False,
                    "live_validation": "not_tested",
                    "required_next_step": "Validate in a controlled experiment.",
                },
            },
        },
    }


class HomeAssistantPublisherTests(unittest.IsolatedAsyncioTestCase):
    def test_entities_contain_only_sanitized_monitor_data(self):
        entities = build_entity_states(_status())
        self.assertEqual(
            entities["binary_sensor.free_the_deco_m9plus_online"]["state"],
            "on",
        )
        self.assertEqual(entities["sensor.free_the_deco_2_4_ghz_channel"]["state"], 4)
        self.assertEqual(
            entities["sensor.free_the_deco_zigbee_coexistence_risk"]["state"],
            "high",
        )
        self.assertEqual(
            entities["sensor.free_the_deco_radio_control_readiness"]["state"],
            "disarmed",
        )
        serialized = json.dumps(entities)
        self.assertNotIn("mac", serialized.lower())
        self.assertNotIn("password", serialized.lower())

    def test_device_discovery_preserves_ids_and_contains_no_hardware_identifier(self):
        status = _status()
        entities = build_entity_states(status)
        messages = build_device_discovery(status, entities)

        self.assertEqual(len(messages), 2)
        serialized = json.dumps(messages)
        self.assertNotIn("mac", serialized.lower())
        self.assertNotIn("password", serialized.lower())
        monitor = json.loads(
            messages["homeassistant/device/free_the_deco_monitor/config"]
        )
        component = monitor["components"]["free_the_deco_monitoring_healthy"]
        self.assertEqual(
            component["default_entity_id"],
            "binary_sensor.free_the_deco_monitoring_healthy",
        )
        self.assertEqual(component["unique_id"], "free_the_deco_monitoring_healthy")
        self.assertEqual(component["expire_after"], 240)
        self.assertEqual(monitor["state_topic"], MQTT_STATE_TOPIC)

        node = json.loads(
            messages["homeassistant/device/free_the_deco_node_m9plus/config"]
        )
        self.assertEqual(node["device"]["identifiers"], ["free_the_deco_node_m9plus"])
        self.assertEqual(node["device"]["name"], "Workshop Deco")

    def test_missing_numeric_measurement_renders_home_assistant_none(self):
        status = _status()
        status["mesh"]["nodes"][0]["backhaul_speed_mbps"] = None
        entities = build_entity_states(status)
        messages = build_device_discovery(status, entities)

        self.assertEqual(
            entities["sensor.free_the_deco_m9plus_backhaul_speed"]["state"],
            "unknown",
        )
        node = json.loads(
            messages["homeassistant/device/free_the_deco_node_m9plus/config"]
        )
        component = node["components"]["free_the_deco_m9plus_backhaul_speed"]
        self.assertEqual(
            component["value_template"],
            "{{ value_json['free_the_deco_m9plus_backhaul_speed'][\"state\"] "
            "if value_json['free_the_deco_m9plus_backhaul_speed'][\"state\"] "
            "is number else 'None' }}",
        )

    def test_non_numeric_diagnostics_keep_their_string_state(self):
        status = _status()
        entities = build_entity_states(status)
        messages = build_device_discovery(status, entities)
        monitor = json.loads(
            messages["homeassistant/device/free_the_deco_monitor/config"]
        )

        component = monitor["components"]["free_the_deco_radio_control_readiness"]
        self.assertEqual(
            component["value_template"],
            "{{ value_json['free_the_deco_radio_control_readiness'][\"state\"] }}",
        )

    def test_missing_timestamp_renders_home_assistant_none(self):
        status = _status()
        status["next_poll_at"] = None
        entities = build_entity_states(status)
        messages = build_device_discovery(status, entities)

        self.assertEqual(entities["sensor.free_the_deco_next_poll"]["state"], "unknown")
        monitor = json.loads(
            messages["homeassistant/device/free_the_deco_monitor/config"]
        )
        component = monitor["components"]["free_the_deco_next_poll"]
        self.assertEqual(
            component["value_template"],
            "{{ value_json['free_the_deco_next_poll'][\"state\"] if "
            "value_json['free_the_deco_next_poll'][\"state\"] is string and "
            "value_json['free_the_deco_next_poll'][\"state\"] != 'unknown' "
            "else 'None' }}",
        )

    async def test_discovery_is_deduplicated_but_state_refreshes_each_cycle(self):
        session = _Session()
        publisher = HomeAssistantPublisher(
            session, token="test-token", api_base="http://ha.invalid/api"
        )
        changed, total = await publisher.publish(_status())
        self.assertEqual(changed, total)
        first_count = len(session.posts)
        self.assertEqual(first_count, 3)

        changed, second_total = await publisher.publish(_status())
        self.assertEqual(changed, 0)
        self.assertEqual(second_total, total)
        self.assertEqual(len(session.posts), first_count + 1)
        second_state = session.posts[-1][1]["json"]
        self.assertEqual(second_state["topic"], MQTT_STATE_TOPIC)
        self.assertEqual(second_state["qos"], 1)
        self.assertFalse(second_state["retain"])
        self.assertTrue(
            all(
                call[1]["headers"]["Authorization"] == "Bearer test-token"
                for call in session.posts
            )
        )

    async def test_removed_node_discovery_is_cleared_with_retained_empty_payload(self):
        session = _Session()
        publisher = HomeAssistantPublisher(
            session, token="test-token", api_base="http://ha.invalid/api"
        )
        await publisher.publish(_status())
        status_without_node = _status()
        status_without_node["mesh"]["nodes"] = []
        status_without_node["mesh"]["node_count"] = 0
        status_without_node["mesh"]["online_count"] = 0
        await publisher.publish(status_without_node)

        removals = [
            call[1]["json"]
            for call in session.posts
            if call[1]["json"]["payload"] == ""
        ]
        self.assertEqual(len(removals), 1)
        self.assertEqual(
            removals[0]["topic"],
            "homeassistant/device/free_the_deco_node_m9plus/config",
        )
        self.assertTrue(removals[0]["retain"])


if __name__ == "__main__":
    unittest.main()
