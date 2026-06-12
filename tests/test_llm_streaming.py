import sys
import types
import unittest
from unittest.mock import patch

from core.llm_client import ask_llm, stream_ask_llm


class _FailingCompletions:
    def create(self, **kwargs):
        raise TimeoutError("read timed out")


class _FailingOpenAI:
    def __init__(self, **kwargs):
        self.chat = types.SimpleNamespace(completions=_FailingCompletions())


class LlmStreamingTests(unittest.TestCase):
    def test_no_key_returns_local_answer_without_network(self):
        chunks = list(stream_ask_llm(
            question="什么是尿道鳞癌？",
            report={"similar_cases": [], "related_articles": [], "risk": {"missing_items": []}},
            patient={},
            api_key_override="",
            provider_override="deepseek",
        ))

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].strip())

    def test_timeout_has_request_id_and_no_retry_warning(self):
        fake_module = types.SimpleNamespace(OpenAI=_FailingOpenAI)
        with patch.dict(sys.modules, {"openai": fake_module}):
            with self.assertRaises(RuntimeError) as caught:
                list(stream_ask_llm(
                    question="分析病例",
                    report={"similar_cases": [], "related_articles": [], "risk": {"missing_items": []}},
                    patient={"diagnosis": "尿道鳞癌"},
                    api_key_override="unit-test-secret",
                    model_override="deepseek-chat",
                    provider_override="deepseek",
                ))

        message = str(caught.exception)
        self.assertIn("请求 ID", message)
        self.assertIn("不要立即重复发送", message)

    def test_non_streaming_api_error_does_not_append_local_answer(self):
        fake_module = types.SimpleNamespace(OpenAI=_FailingOpenAI)
        with patch.dict(sys.modules, {"openai": fake_module}):
            result = ask_llm(
                question="分析病例",
                report={"similar_cases": [], "related_articles": [], "risk": {"missing_items": []}},
                patient={"diagnosis": "尿道鳞癌"},
                api_key_override="unit-test-placeholder",
                model_override="deepseek-chat",
                provider_override="deepseek",
            )

        self.assertEqual(result["provider"], "api_error")
        self.assertNotIn("local_fallback", result["provider"])
        self.assertNotIn("本地模式", result["answer"])


if __name__ == "__main__":
    unittest.main()
