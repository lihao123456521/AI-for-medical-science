import json
import tempfile
import unittest
from pathlib import Path

from core.seed_data import audit_seed_payload, build_seed_payload, initialize_runtime_from_seed, sanitize_for_external_llm


class SeedDataTests(unittest.TestCase):
    def test_case_deidentification_removes_identity_paths_secrets_and_images(self):
        cases = [{
            "case_id": "USER-685",
            "patient_name": "周相如",
            "diagnosis": "尿道鳞癌",
            "imaging": "姓名：周相如\n住院号：12345678\n2017-04-25 CT提示尿道肿块",
            "remarks": r"来源 C:\Users\ASUS\Desktop\影像片子汇总.pdf，API " + "sk-" + "secret-1234567890",
            "medical_images": [{"stored_as": "private.jpg", "url": "/uploads/private.jpg"}],
            "source_document": "影像片子汇总.pdf",
            "source_hash": "abcdef",
        }]

        payload = build_seed_payload(cases, [])
        text = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(payload["cases"][0]["case_id"], "SEED-CASE-001")
        self.assertNotIn("周相如", text)
        self.assertNotIn("12345678", text)
        self.assertNotIn("C:\\Users", text)
        self.assertNotIn("secret-1234567890", text)
        self.assertNotIn("private.jpg", text)
        self.assertNotIn("2017-04-25", text)
        self.assertIn("2017年", text)
        self.assertNotIn("patient_name", payload["cases"][0])
        self.assertNotIn("source_document", payload["cases"][0])

    def test_articles_keep_medical_content_but_drop_local_file_metadata(self):
        articles = [{
            "article_id": "ARTICLE-9",
            "title": "尿道鳞癌综述",
            "abstract": "讨论治疗和随访。",
            "content": "医学正文",
            "source_file": "患者资料.pdf",
            "stored_as": "local-private.pdf",
            "article_images": [{"stored_as": "scan.png"}],
            "source_url": "https://doi.org/10.1000/example",
        }]

        payload = build_seed_payload([], articles)
        article = payload["articles"][0]

        self.assertEqual(article["article_id"], "SEED-ARTICLE-001")
        self.assertEqual(article["content"], "医学正文")
        self.assertEqual(article["source_url"], "https://doi.org/10.1000/example")
        self.assertNotIn("source_file", article)
        self.assertNotIn("stored_as", article)
        self.assertNotIn("article_images", article)

    def test_audit_rejects_identity_and_secret_patterns(self):
        findings = audit_seed_payload({"cases": [{"notes": "姓名：张三 " + "sk-" + "abcdefghijklmnop"}], "articles": []})

        self.assertTrue(any("identity" in item or "secret" in item for item in findings))

    def test_imaging_and_visit_numbers_are_redacted(self):
        payload = build_seed_payload([{"imaging": "MRI（影像号：L00689150），门诊号: A123456，超声号：24085998"}], [])
        text = json.dumps(payload, ensure_ascii=False)

        self.assertNotIn("L00689150", text)
        self.assertNotIn("A123456", text)
        self.assertNotIn("24085998", text)

    def test_source_filenames_are_removed_from_public_notes(self):
        payload = build_seed_payload([{
            "remarks": "来源文件：影像片子汇总.pdf（保存为 imaging-summary-617fbd6fbdd3.pdf）。原资料编号 1。"
        }], [])
        text = json.dumps(payload, ensure_ascii=False)

        self.assertNotIn("影像片子汇总.pdf", text)
        self.assertNotIn("imaging-summary-617fbd6fbdd3.pdf", text)

    def test_outbound_sanitizer_keeps_json_structure_and_clinical_fields(self):
        """出站脱敏只替换身份值，不能把单行 JSON 上下文整段吞掉。"""
        context = {
            "conversation_mode": "initial_patient_brief",
            "patient_input_current_chat_only": {
                "age": 65,
                "sex": "男",
                "diagnosis": "尿道鳞状细胞癌",
                "free_text": "姓名:张三；性别:男；住院号:12345678；诊断:尿道SCC",
            },
        }
        text = json.dumps(context, ensure_ascii=False)
        out = sanitize_for_external_llm(text)

        self.assertIn("尿道鳞状细胞癌", out)
        self.assertIn("尿道SCC", out)
        self.assertIn("65", out)
        self.assertNotIn("张三", out)
        self.assertNotIn("12345678", out)
        parsed = json.loads(out)
        self.assertEqual(parsed["conversation_mode"], "initial_patient_brief")

    def test_outbound_sanitizer_redacts_structured_json_identity_fields(self):
        context = {
            "patient_name": "张三",
            "name": "李四",
            "姓名": "王五",
            "住院号": "H123456",
            "病案号": "M123456",
            "身份证号": "310101199001011234",
            "联系电话": "13800138000",
            "家庭住址": "上海市某区某路 1 号",
            "age": 65,
            "sex": "男",
            "diagnosis": "尿道鳞状细胞癌",
            "tnm": "T2N0M0",
            "pathology": "鳞状细胞癌",
            "imaging": "尿道占位",
            "treatment": "手术",
            "followup": "未见复发",
            "history_messages": [
                {"role": "user", "content": "请分析患者张三，住院号 H123456。"},
            ],
        }
        out = sanitize_for_external_llm(json.dumps(context, ensure_ascii=False))
        parsed = json.loads(out)

        for key in ("patient_name", "name", "姓名", "住院号", "病案号", "身份证号", "联系电话", "家庭住址"):
            self.assertNotEqual(parsed[key], context[key], key)
        self.assertNotIn("张三", out)
        self.assertNotIn("H123456", out)
        for key in ("age", "sex", "diagnosis", "tnm", "pathology", "imaging", "treatment", "followup"):
            self.assertEqual(parsed[key], context[key], key)

    def test_initialize_only_populates_empty_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed"
            runtime = root / "runtime"
            seed.mkdir()
            (seed / "user_cases.json").write_text('[{"case_id":"SEED-CASE-001"}]', encoding="utf-8")
            (seed / "articles.json").write_text('[{"article_id":"SEED-ARTICLE-001"}]', encoding="utf-8")

            first = initialize_runtime_from_seed(runtime, seed)
            (runtime / "user_cases.json").write_text('[{"case_id":"LOCAL-1"}]', encoding="utf-8")
            second = initialize_runtime_from_seed(runtime, seed)

            self.assertTrue(first["initialized"])
            self.assertFalse(second["initialized"])
            self.assertIn("LOCAL-1", (runtime / "user_cases.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
