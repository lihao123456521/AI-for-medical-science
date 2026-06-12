import unittest

from core.chat_routing import ChatRoute
from core.evidence_context import build_evidence_report


class EvidenceContextTests(unittest.TestCase):
    def setUp(self):
        self.article_calls = []

    def search_articles(self, query, limit=4):
        self.article_calls.append(query)
        return [{"article_id": "ARTICLE-1", "title": "尿道鳞癌综述", "abstract": "治疗与随访证据"}]

    def test_general_medical_question_uses_articles_without_case_cards(self):
        route = ChatRoute(False, False, "general_medical", True)
        report = build_evidence_report(
            route=route,
            question="尿道鳞癌常见治疗方式？",
            patient={},
            attachments=[],
            generate_case_report=lambda patient, top_n: self.fail("case retrieval should not run"),
            search_articles=self.search_articles,
            find_candidates=lambda attachments, query, limit: [],
            knowledge_digest=lambda: {"case_count": 93, "article_count": 230},
        )

        self.assertEqual(report["similar_cases"], [])
        self.assertEqual(report["related_articles"][0]["article_id"], "ARTICLE-1")
        self.assertFalse(report["display_evidence_cards"])

    def test_explicit_case_request_uses_cases_and_articles(self):
        route = ChatRoute(True, True, "explicit_retrieval", True)
        report = build_evidence_report(
            route=route,
            question="比较相似病例和文献",
            patient={"diagnosis": "尿道鳞癌"},
            attachments=[],
            generate_case_report=lambda patient, top_n: {"similar_cases": [{"case_id": "SEED-CASE-001"}], "risk": {"missing_items": []}},
            search_articles=self.search_articles,
            find_candidates=lambda attachments, query, limit: [],
            knowledge_digest=lambda: {"case_count": 93, "article_count": 230},
        )

        self.assertEqual(report["similar_cases"][0]["case_id"], "SEED-CASE-001")
        self.assertEqual(report["related_articles"][0]["article_id"], "ARTICLE-1")
        self.assertTrue(report["display_evidence_cards"])


if __name__ == "__main__":
    unittest.main()
