import unittest

from core.llm_client import build_request_policy, classify_provider_error


class LlmPolicyTests(unittest.TestCase):
    def test_normal_deepseek_policy_disables_retries_and_streams(self):
        policy = build_request_policy("deepseek", "general")

        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.max_output_tokens, 350)
        self.assertLessEqual(policy.read_timeout, 75)
        self.assertTrue(policy.stream)

    def test_initial_analysis_has_larger_but_bounded_output(self):
        policy = build_request_policy("openai", "initial_patient_analysis")

        self.assertEqual(policy.max_output_tokens, 550)
        self.assertEqual(policy.max_retries, 0)
        self.assertTrue(policy.stream)

    def test_connection_test_is_small_and_non_retrying(self):
        policy = build_request_policy("custom", "connection_test")

        self.assertEqual(policy.max_output_tokens, 24)
        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.read_timeout, 20)

    def test_timeout_message_warns_request_may_have_been_accepted(self):
        message = classify_provider_error(TimeoutError("read timed out"), "deepseek", "req-1")

        self.assertIn("可能已经接收", message)
        self.assertIn("不要立即重复发送", message)
        self.assertIn("req-1", message)

    def test_auth_and_quota_errors_are_classified(self):
        self.assertIn("鉴权失败", classify_provider_error(Exception("invalid_api_key"), "openai", "r1"))
        self.assertIn("余额", classify_provider_error(Exception("402 insufficient balance"), "deepseek", "r2"))


if __name__ == "__main__":
    unittest.main()
