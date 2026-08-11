import ast
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class GuardrailTests(unittest.TestCase):
    def test_only_login_read_and_write_wire_operations_exist(self):
        source = (ROOT / "src/deco_lab/client.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        operations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "operation"
                        and isinstance(value, ast.Constant)
                    ):
                        operations.append(value.value)
        self.assertEqual(set(operations), {"login", "read", "write"})
        self.assertEqual(source.count('"operation": "write"'), 1)
        self.assertIn('"channel": channel', source)
        self.assertIn('"bandwidth": bandwidth', source)

    def test_candidate_values_are_constants_and_no_generic_runner_exists(self):
        source = (ROOT / "src/deco_lab/client.py").read_text(encoding="utf-8")
        self.assertIn("LAB_CHANNEL = 11", source)
        self.assertIn('LAB_BANDWIDTH = "HT20"', source)
        all_source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "src/deco_lab").glob("*.py")
        )
        self.assertNotRegex(all_source, r"arbitrary|generic_endpoint|raw_payload")

    def test_app_is_manual_experimental_and_writes_default_locked(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(config["boot"], "manual")
        self.assertEqual(config["stage"], "experimental")
        self.assertFalse(config["options"]["writes_enabled"])
        self.assertFalse(
            config["options"]["firmware_write_compatibility_acknowledged"]
        )
        self.assertFalse(config["options"]["lab_enabled"])
        self.assertNotIn("homeassistant_api", config)
        self.assertNotIn("services", config)

    def test_ui_exposes_only_fixed_experiment_route(self):
        service = (ROOT / "src/deco_lab/service.py").read_text(encoding="utf-8")
        routes = re.findall(r'app\.router\.add_post\("([^"]+)"', service)
        self.assertEqual(
            routes,
            ["/api/v1/refresh", "/api/v1/experiment/channel-11-ht20"],
        )
