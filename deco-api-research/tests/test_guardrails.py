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
        self.assertIn('("device", "device_list")', source)
        self.assertIn('("network", "performance")', source)

    def test_app_requests_no_supervisor_or_host_privileges(self):
        config = (APP_ROOT / "config.yaml").read_text(encoding="utf-8")
        forbidden = (
            "host_network: true",
            "hassio_api: true",
            "homeassistant_api: true",
            "docker_api: true",
            "full_access: true",
            "privileged:",
            "map:",
        )
        for setting in forbidden:
            self.assertNotIn(setting, config)


if __name__ == "__main__":
    unittest.main()
