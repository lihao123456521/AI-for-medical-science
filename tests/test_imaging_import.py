import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_imaging_pdf_cases import create_storage_backup, import_segments


def segment_row(number: int) -> dict:
    return {
        "patient_name": f"患者{number}",
        "source_case_number": number,
        "source_pages": [number],
        "imaging": f"{number}.姓名：患者{number}\n影像结论：尿道异常。",
        "imaging_findings": [{"text": "尿道异常", "source_page": number}],
        "medical_images": [
            {
                "type": "image",
                "filename": f"case-{number}.jpg",
                "stored_as": f"case-{number}.jpg",
                "url": f"/uploads/case-{number}.jpg",
                "source_page": number,
                "physician_annotation": "尿道异常",
            }
        ],
    }


class ImagingImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name)
        cases = [{"case_id": f"USER-{index:03d}", "diagnosis": "旧病例"} for index in range(1, 77)]
        articles = [{"article_id": f"ARTICLE-{index:03d}", "title": "旧文章"} for index in range(1, 231)]
        deleted = ["OLD-001"]
        (self.data_dir / "user_cases.json").write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")
        (self.data_dir / "articles.json").write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
        (self.data_dir / "deleted_cases.json").write_text(json.dumps(deleted), encoding="utf-8")
        (self.data_dir / "library_state.json").write_text(
            json.dumps({"updated_at": "old", "user_cases": cases, "articles": articles, "deleted_case_ids": deleted}, ensure_ascii=False),
            encoding="utf-8",
        )
        self.article_bytes = (self.data_dir / "articles.json").read_bytes()
        self.numbers = list(range(1, 11)) + list(range(12, 19))
        self.rows = [segment_row(number) for number in self.numbers]

    def tearDown(self):
        self.temp.cleanup()

    def test_import_adds_17_once_and_preserves_articles(self):
        first = import_segments(self.data_dir, self.rows, source_hash="pdfhash")
        second = import_segments(self.data_dir, self.rows, source_hash="pdfhash")

        self.assertEqual(first["before_case_count"], 76)
        self.assertEqual(first["added"], 17)
        self.assertEqual(first["after_case_count"], 93)
        self.assertEqual(first["article_count"], 230)
        self.assertEqual(second["added"], 0)
        self.assertEqual(second["after_case_count"], 93)
        self.assertEqual((self.data_dir / "articles.json").read_bytes(), self.article_bytes)

    def test_original_numbers_and_ids_are_stable(self):
        import_segments(self.data_dir, self.rows, source_hash="pdfhash")
        saved = json.loads((self.data_dir / "user_cases.json").read_text(encoding="utf-8"))
        imported = [row for row in saved if row.get("source_hash") == "pdfhash"]

        self.assertEqual([row["source_case_number"] for row in imported], self.numbers)
        self.assertEqual(imported[0]["case_id"], "USER-077")
        self.assertEqual(imported[-1]["case_id"], "USER-093")
        self.assertEqual([row["source_import_key"] for row in imported], [f"pdfhash:{n}" for n in self.numbers])

    def test_backup_contains_source_of_truth_before_write(self):
        backup = create_storage_backup(self.data_dir, timestamp="20260611-120000")

        self.assertEqual(json.loads((backup / "user_cases.json").read_text(encoding="utf-8"))[0]["case_id"], "USER-001")
        self.assertEqual(len(json.loads((backup / "articles.json").read_text(encoding="utf-8"))), 230)
        self.assertTrue((backup / "library_state.json").exists())


if __name__ == "__main__":
    unittest.main()
