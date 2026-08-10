import json
import unittest

from deco_research.home_assistant import HomeAssistantPublisher, build_entity_states


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
        "mode": "healthy",
        "last_success_at": "2026-08-10T12:00:00+00:00",
        "mesh": {
            "node_count": 1,
            "online_count": 1,
            "offline_count": 0,
            "nodes": [
                {
                    "id": "living_room",
                    "name": "Living Room",
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
        },
    }


class HomeAssistantPublisherTests(unittest.IsolatedAsyncioTestCase):
    def test_entities_contain_only_sanitized_monitor_data(self):
        entities = build_entity_states(_status())
        self.assertEqual(
            entities["binary_sensor.free_the_deco_living_room_online"]["state"],
            "on",
        )
        self.assertEqual(entities["sensor.free_the_deco_2_4_ghz_channel"]["state"], 4)
        serialized = json.dumps(entities)
        self.assertNotIn("mac", serialized.lower())
        self.assertNotIn("password", serialized.lower())

    async def test_unchanged_states_are_not_republished(self):
        session = _Session()
        publisher = HomeAssistantPublisher(
            session, token="test-token", api_base="http://ha.invalid/api"
        )
        changed, total = await publisher.publish(_status())
        self.assertEqual(changed, total)
        first_count = len(session.posts)

        changed, second_total = await publisher.publish(_status())
        self.assertEqual(changed, 0)
        self.assertEqual(second_total, total)
        self.assertEqual(len(session.posts), first_count)
        self.assertTrue(
            all(
                call[1]["headers"]["Authorization"] == "Bearer test-token"
                for call in session.posts
            )
        )


if __name__ == "__main__":
    unittest.main()
