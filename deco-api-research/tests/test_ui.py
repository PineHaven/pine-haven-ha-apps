import unittest

from deco_research.ui import UI_HTML


class UiTests(unittest.TestCase):
    def test_ingress_ui_is_self_contained_and_has_live_sections(self):
        self.assertIn("FREE THE DECO", UI_HTML)
        self.assertIn("Deco mesh", UI_HTML)
        self.assertIn("Client distribution", UI_HTML)
        self.assertIn("Radio status", UI_HTML)
        self.assertIn("api/v1/status", UI_HTML)
        self.assertNotIn("https://", UI_HTML)


if __name__ == "__main__":
    unittest.main()
