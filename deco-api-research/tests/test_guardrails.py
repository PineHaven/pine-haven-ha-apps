import ast
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).parents[1]


class SourceGuardrailTests(unittest.TestCase):
    def test_only_read_and_login_wire_operations_exist(self):
        source_path = APP_ROOT / "src" / "deco_research" / "client.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        operations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "operation"
                    and isinstance(value, ast.Constant)
                ):
                    operations.append(value.value)

        self.assertTrue(operations)
        self.assertEqual(set(operations), {"read", "login"})
        self.assertNotIn("reboot_decos", source)
        self.assertNotIn('operation": "write', source)
        self.assertIn('("client", "client_list")', source)
        self.assertIn('("device", "device_list")', source)
        self.assertIn('("network", "performance")', source)
        self.assertIn('("wireless", "wlan")', source)
        self.assertNotIn('("network_optimize", "acs_optimize")', source)

    def test_app_requests_only_scoped_home_assistant_api_access(self):
        config = (APP_ROOT / "config.yaml").read_text(encoding="utf-8")
        forbidden = (
            "host_network: true",
            "hassio_api: true",
            "docker_api: true",
            "full_access: true",
            "privileged:",
            "map:",
        )
        for setting in forbidden:
            self.assertNotIn(setting, config)
        self.assertEqual(config.count("homeassistant_api: true"), 1)

        publisher = (APP_ROOT / "src" / "deco_research" / "home_assistant.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("/services/mqtt/publish", publisher)
        self.assertNotIn("/states/", publisher)

    def test_container_drops_root_before_starting_runtime(self):
        dockerfile = (APP_ROOT / "Dockerfile").read_text(encoding="utf-8")
        service = (APP_ROOT / "src" / "deco_research" / "service.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("useradd --system --gid deco-research", dockerfile)
        self.assertNotIn("USER deco-research", dockerfile)
        self.assertLess(
            service.index("drop_process_privileges()"),
            service.index("runtime = ProbeRuntime("),
        )


if __name__ == "__main__":
    unittest.main()
