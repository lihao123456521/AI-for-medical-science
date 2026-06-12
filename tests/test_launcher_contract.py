import json
import re
import unittest
from pathlib import Path


class LauncherContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Path(__file__).resolve().parents[1]
        cls.launcher = (cls.project / "windows_launcher.pyw").read_text(encoding="utf-8")
        cls.app_source = (cls.project / "app.py").read_text(encoding="utf-8")

    def test_health_endpoint_exposes_build_identity(self):
        self.assertIn("APP_BUILD_ID", self.app_source)
        self.assertRegex(self.app_source, r'"build_id"\s*:\s*APP_BUILD_ID')

    def test_launcher_requires_matching_build_identity(self):
        self.assertIn("EXPECTED_BUILD_ID", self.launcher)
        self.assertIn("health.get(\"build_id\") == EXPECTED_BUILD_ID", self.launcher)

    def test_launcher_does_not_reuse_stale_healthy_service(self):
        choose_port = re.search(r"def choose_port\(\).*?(?=\ndef )", self.launcher, re.S)
        self.assertIsNotNone(choose_port)
        self.assertIn("is_matching_health", choose_port.group(0))
        self.assertNotIn("if is_health_ok(port):\n            return port", choose_port.group(0))


if __name__ == "__main__":
    unittest.main()
