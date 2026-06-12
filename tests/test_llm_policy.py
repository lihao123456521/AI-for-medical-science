import unittest

from core.llm_client import build_llm_context, build_request_policy, classify_provider_error


class LlmPolicyTests(unittest.TestCase):
    def test_normal_deepseek_policy_disables_retries_and_streams(self):
        policy = build_request_policy("deepseek", "general")

        self.assertEqual(policy.max_retries, 0)
        self.assertLessEqual(policy.max_output_tokens, 260)
        self.assertGreaterEqual(policy.read_timeout, 150)
        self.assertTrue(policy.stream)

    def test_initial_analysis_has_larger_but_bounded_output(self):
        policy = build_request_policy("openai", "initial_patient_analysis")

        self.assertLessEqual(policy.max_output_tokens, 420)
        self.assertEqual(policy.max_retries, 0)
        self.assertTrue(policy.stream)

    def test_connection_test_is_small_and_non_retrying(self):
        policy = build_request_policy("custom", "connection_test")

        self.assertEqual(policy.max_output_tokens, 24)
        self.assertEqual(policy.max_retries, 0)
        self.assertEqual(policy.read_timeout, 20)

    def test_model_context_is_bounded_but_keeps_database_evidence(self):
        long_text = "病例证据" * 10000
        report = {
            "similar_cases": [{"case_id": f"CASE-{i}", "diagnosis": long_text, "evidence_summary": [long_text]} for i in range(6)],
            "related_articles": [{"article_id": f"ART-{i}", "title": long_text, "abstract": long_text} for i in range(6)],
            "risk": {"missing_items": ["病理分期"]},
            "knowledge_digest": {"summary": long_text},
        }

        context = build_llm_context(
            question="请结合数据库分析",
            mode="initial_patient_analysis",
            report=report,
            patient={"diagnosis": long_text},
            history=[{"role": "user", "content": long_text}] * 20,
            attachments=[],
        )
        encoded = __import__("json").dumps(context, ensure_ascii=False)

        self.assertLessEqual(len(encoded), 24000)
        self.assertIn("CASE-0", encoded)
        self.assertIn("ART-0", encoded)
        self.assertNotIn("CASE-4", encoded)

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
