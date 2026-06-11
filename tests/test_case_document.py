import unittest
import tempfile
from pathlib import Path

from core.case_document import assign_layout_events, segment_numbered_cases
from core.case_parser import parse_case_file


class NumberedCaseSegmentationTests(unittest.TestCase):
    def test_missing_number_and_report_subsections_do_not_split_cases(self):
        text = """1.姓名：甲
CT报告：
1.膀胱壁增厚
2.淋巴结肿大
2.姓名：乙
MRI报告
1.尿道肿块
12.姓名：丙
CT报告"""

        rows = segment_numbered_cases(text)

        self.assertEqual([row.source_case_number for row in rows], [1, 2, 12])
        self.assertIn("2.淋巴结肿大", rows[0].text)
        self.assertEqual(rows[1].patient_name, "乙")

    def test_case_start_accepts_ascii_colon_and_chinese_separator(self):
        text = "1、姓名: 甲\n内容\n2.姓名：乙\n内容"

        rows = segment_numbered_cases(text)

        self.assertEqual([(row.source_case_number, row.patient_name) for row in rows], [(1, "甲"), (2, "乙")])

    def test_image_before_new_name_stays_with_previous_case(self):
        events = [
            {"kind": "text", "page": 3, "y": 20, "text": "病例1续页"},
            {"kind": "image", "page": 3, "y": 100, "xref": 11},
            {"kind": "text", "page": 3, "y": 500, "text": "2.姓名：乙"},
            {"kind": "image", "page": 3, "y": 700, "xref": 12},
        ]

        owned = assign_layout_events(events, starting_case_number=1)

        self.assertEqual(owned[1]["images"][0]["xref"], 11)
        self.assertEqual(owned[2]["images"][0]["xref"], 12)

    def test_repeated_image_xref_on_later_page_is_preserved_as_a_separate_placement(self):
        events = [
            {"kind": "text", "page": 17, "y": 20, "text": "14.姓名：甲"},
            {"kind": "image", "page": 17, "y": 100, "xref": 50},
            {"kind": "image", "page": 19, "y": 30, "xref": 50},
            {"kind": "text", "page": 19, "y": 200, "text": "15.姓名：乙"},
        ]

        owned = assign_layout_events(events)

        self.assertEqual([(row["page"], row["xref"]) for row in owned[14]["images"]], [(17, 50), (19, 50)])

    def test_text_case_file_returns_all_numbered_candidates(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cases.txt"
            path.write_text("1.姓名：甲\nCT：尿道肿块\n2.姓名：乙\nMRI：淋巴结肿大", encoding="utf-8")

            parsed = parse_case_file(path)

        self.assertEqual([row["source_case_number"] for row in parsed["cases"]], [1, 2])
        self.assertEqual(parsed["cases"][1]["patient_name"], "乙")


if __name__ == "__main__":
    unittest.main()
