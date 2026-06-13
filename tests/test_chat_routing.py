import unittest

from core.chat_routing import classify_chat_request, has_detailed_case, select_llm_attachments
from core.llm_client import local_fallback_reply


class ChatRoutingTests(unittest.TestCase):
    def test_general_question_does_not_use_case_or_retrieve(self):
        route = classify_chat_request("Python如何读取PDF？", has_confirmed_case=True)

        self.assertFalse(route.retrieve_evidence)
        self.assertFalse(route.use_case_context)
        self.assertEqual(route.mode, "general")

    def test_case_followup_uses_case_without_retrieval_cards(self):
        route = classify_chat_request("这个患者下一步需要补充哪些检查？", has_confirmed_case=True)

        self.assertTrue(route.use_case_context)
        self.assertFalse(route.retrieve_evidence)
        self.assertEqual(route.mode, "case_followup")

    def test_explicit_similarity_request_retrieves_only_after_case_confirmation(self):
        confirmed = classify_chat_request("请检索并比较相似病例和文献", has_confirmed_case=True)
        unconfirmed = classify_chat_request("请检索并比较相似病例和文献", has_confirmed_case=False)

        self.assertTrue(confirmed.retrieve_evidence)
        self.assertTrue(confirmed.use_case_context)
        self.assertFalse(unconfirmed.retrieve_evidence)
        self.assertFalse(unconfirmed.use_case_context)

    def test_treatment_word_alone_does_not_force_retrieval(self):
        route = classify_chat_request("手术是什么意思？", has_confirmed_case=True)

        self.assertFalse(route.retrieve_evidence)
        self.assertFalse(route.use_case_context)
        self.assertEqual(route.mode, "general_medical")
        self.assertTrue(route.use_article_context)

    def test_unrelated_question_uses_no_medical_database_context(self):
        route = classify_chat_request("Python如何读取PDF？", has_confirmed_case=False)

        self.assertEqual(route.mode, "general")
        self.assertFalse(route.use_article_context)

    def test_initial_analysis_requires_detailed_case(self):
        detailed = {"age": "56", "sex": "男", "imaging": "尿道肿块", "pathology": "鳞癌"}

        self.assertTrue(has_detailed_case(detailed))
        self.assertFalse(has_detailed_case({"free_text": "你好"}))
        self.assertTrue(classify_chat_request("分析", True, "initial_patient_analysis").retrieve_evidence)

    def test_local_fallback_does_not_expand_similarity_for_general_treatment_question(self):
        report = {"similar_cases": [{"case_id": "CASE-1"}], "related_articles": []}

        answer = local_fallback_reply("手术是什么意思？", report, "general")

        self.assertNotIn("相似病例与治疗转归", answer)


    def test_image_attachment_is_forwarded_even_for_general_route(self):
        route = classify_chat_request("请观察这张图片", has_confirmed_case=False)
        attachments = [{"type": "image", "stored_as": "scan.jpg"}]

        self.assertEqual(select_llm_attachments(attachments, route), attachments)

    def test_non_image_attachment_still_requires_case_context(self):
        route = classify_chat_request("Python如何读取文件？", has_confirmed_case=False)
        attachments = [{"type": "pdf", "stored_as": "report.pdf"}]

        self.assertEqual(select_llm_attachments(attachments, route), [])


if __name__ == "__main__":
    unittest.main()
