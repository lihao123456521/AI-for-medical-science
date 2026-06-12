import unittest
from pathlib import Path


class StreamResponseContractTests(unittest.TestCase):
    def test_sse_response_does_not_set_forbidden_connection_header(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

        self.assertNotIn('resp.headers["Connection"]', source)
        self.assertIn('resp.headers["X-Accel-Buffering"] = "no"', source)


if __name__ == "__main__":
    unittest.main()
