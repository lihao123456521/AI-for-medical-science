import re
import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (Path(__file__).resolve().parents[1] / "static" / "js" / "app.js").read_text(encoding="utf-8")

    def _function_body(self, name: str) -> str:
        match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{([\s\S]*?)\n\}}", self.source)
        self.assertIsNotNone(match, f"missing function {name}")
        return match.group(1)

    def test_chat_payload_uses_saved_config_id_without_browser_secret(self):
        body = self._function_body("apiPayloadExtras")

        self.assertIn("use_saved_config", body)
        self.assertIn("config_id", body)
        self.assertNotIn("API_KEY_STORAGE", body)
        self.assertNotIn("api_key:", body)

    def test_selecting_remembered_config_persists_only_non_secret_metadata(self):
        body = self._function_body("fillApiModalFromConfig")

        self.assertIn("config_id", body)
        self.assertNotIn("cfg.api_key", body)

    def test_startup_removes_legacy_browser_plaintext_key(self):
        self.assertIn("localStorage.removeItem(API_KEY_STORAGE)", self.source)

    def test_save_message_does_not_claim_failed_test_discarded_local_key(self):
        body = self._function_body("saveApiConfig")

        self.assertIn("data.saved", body)
        self.assertNotIn("未保存该配置", body)

    def test_send_message_has_inflight_duplicate_guard(self):
        body = self._function_body("sendMessage")

        self.assertIn("chatRequestInFlight", self.source)
        self.assertIn("if (chatRequestInFlight)", body)
        self.assertIn("chatRequestInFlight = true", body)
        self.assertIn("chatRequestInFlight = false", body)

    def test_api_errors_are_not_hidden_by_local_fallback_text(self):
        stream_body = self._function_body("streamChat")

        self.assertNotIn("local_fallback_after_api_error", stream_body)
        self.assertNotIn("已使用本地", stream_body)

    def test_remembered_api_history_has_independent_delete_action(self):
        history_body = self._function_body("renderApiHistoryList")

        self.assertIn("api-history-delete", history_body)
        self.assertIn("deleteRememberedApiConfig", history_body)
        self.assertIn("event.stopPropagation()", history_body)

    def test_delete_remembered_config_calls_backend_with_config_id(self):
        body = self._function_body("deleteRememberedApiConfig")

        self.assertIn("method:'DELETE'", body)
        self.assertIn("config_id", body)
        self.assertIn("fetchRememberedApiConfig", body)


if __name__ == "__main__":
    unittest.main()
