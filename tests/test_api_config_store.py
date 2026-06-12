import json
import tempfile
import unittest
from pathlib import Path

from core.api_config_store import ApiConfigStore


class ApiConfigStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ApiConfigStore(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_saved_config_is_masked_but_resolves_full_key_locally(self):
        saved = self.store.save_verified({
            "api_key": "local-secret-123456",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
        })

        masked = self.store.current_masked()
        resolved = self.store.resolve_request_config({"use_saved_config": True})

        self.assertEqual(masked["config_id"], saved["config_id"])
        self.assertNotIn("api_key", masked)
        self.assertEqual(masked["api_key_masked"], "loca...3456")
        self.assertEqual(resolved["api_key"], "local-secret-123456")

    def test_unverified_config_is_still_saved_locally_and_reusable(self):
        saved = self.store.save_local({
            "api_key": "slow-provider-secret-123456",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": "https://api.deepseek.com",
        }, test_ok=False)

        restarted = ApiConfigStore(Path(self.temp.name))
        masked = restarted.current_masked()
        resolved = restarted.resolve_request_config({"config_id": saved["config_id"]})

        self.assertEqual(masked["test_ok"], False)
        self.assertEqual(resolved["api_key"], "slow-provider-secret-123456")
        self.assertEqual(len(restarted.history_masked()), 1)

    def test_history_config_can_be_activated_without_resubmitting_key(self):
        first = self.store.save_verified({"api_key": "first-local-secret-111111", "provider": "openai", "model": "gpt-4.1-mini"})
        self.store.save_verified({"api_key": "second-local-secret-222222", "provider": "deepseek", "model": "deepseek-chat"})

        activated = self.store.activate(first["config_id"])
        resolved = self.store.resolve_request_config({"config_id": first["config_id"]})

        self.assertEqual(activated["provider"], "openai")
        self.assertNotIn("api_key", activated)
        self.assertEqual(resolved["api_key"], "first-local-secret-111111")

    def test_explicit_key_overrides_saved_config(self):
        self.store.save_verified({"api_key": "saved-local-secret-111111", "provider": "openai", "model": "gpt-4.1-mini"})

        resolved = self.store.resolve_request_config({
            "api_key": "one-shot-local-secret-999999",
            "provider": "custom",
            "model": "custom-model",
            "base_url": "https://example.test/v1",
        })

        self.assertEqual(resolved["api_key"], "one-shot-local-secret-999999")
        self.assertEqual(resolved["provider"], "custom")

    def test_clear_all_removes_current_and_history(self):
        self.store.save_verified({"api_key": "local-secret-111111", "provider": "openai", "model": "gpt-4.1-mini"})

        self.store.clear_all()

        self.assertEqual(self.store.current_masked(), {})
        self.assertEqual(self.store.history_masked(), [])
        self.assertFalse((Path(self.temp.name) / "api_config.json").exists())
        self.assertFalse((Path(self.temp.name) / "api_config_history.json").exists())

    def test_delete_non_current_config_keeps_active_config(self):
        first = self.store.save_verified({"api_key": "first-placeholder-111111", "provider": "openai", "model": "gpt-4.1-mini"})
        second = self.store.save_verified({"api_key": "second-placeholder-222222", "provider": "deepseek", "model": "deepseek-chat"})

        result = self.store.delete(first["config_id"])

        self.assertEqual(result["config"]["config_id"], second["config_id"])
        self.assertEqual([row["config_id"] for row in result["history"]], [second["config_id"]])
        self.assertEqual(self.store.resolve_request_config({"use_saved_config": True})["api_key"], "second-placeholder-222222")

    def test_delete_current_config_activates_most_recent_remaining(self):
        first = self.store.save_verified({"api_key": "first-placeholder-111111", "provider": "openai", "model": "gpt-4.1-mini"})
        second = self.store.save_verified({"api_key": "second-placeholder-222222", "provider": "deepseek", "model": "deepseek-chat"})

        result = self.store.delete(second["config_id"])

        self.assertEqual(result["config"]["config_id"], first["config_id"])
        self.assertEqual(self.store.resolve_request_config({"use_saved_config": True})["api_key"], "first-placeholder-111111")

    def test_delete_only_config_clears_current_and_history(self):
        only = self.store.save_verified({"api_key": "only-placeholder-111111", "provider": "openai", "model": "gpt-4.1-mini"})

        result = self.store.delete(only["config_id"])

        self.assertEqual(result, {"config": {}, "history": []})
        self.assertFalse((Path(self.temp.name) / "api_config.json").exists())

    def test_files_are_local_json_and_plaintext_never_appears_in_masked_payload(self):
        secret = "local-secret-never-return-1234"
        self.store.save_verified({"api_key": secret, "provider": "openai", "model": "gpt-4.1-mini"})

        payload = json.dumps({"current": self.store.current_masked(), "history": self.store.history_masked()})

        self.assertNotIn(secret, payload)


if __name__ == "__main__":
    unittest.main()
