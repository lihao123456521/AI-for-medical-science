import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SeedInitializationTests(unittest.TestCase):
    def test_fresh_app_runtime_starts_with_public_database_and_no_api_config(self):
        project = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            env = os.environ.copy()
            env["USCC_DATA_DIR"] = str(runtime)
            env["DATA_PATH"] = str(project / "data" / "knowledge_base.xlsx")
            code = """
import json
import app
c = app.app.test_client()
s = c.get('/api/summary').get_json()
print(json.dumps({'total_cases': s['total_cases'], 'articles': s['articles']}))
"""
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertEqual(summary, {"total_cases": 93, "articles": 230})
            self.assertFalse((runtime / "api_config.json").exists())
            self.assertFalse((runtime / "api_config_history.json").exists())


if __name__ == "__main__":
    unittest.main()
