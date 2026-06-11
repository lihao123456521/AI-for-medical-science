import unittest

from core.data_loader import CaseRecord, case_sort_key


def make_record(case_id: str, **overrides):
    values = {
        "case_id": case_id,
        "sheet": "用户新增",
        "diagnosis": "影像资料病例",
        "sex": "",
        "age": None,
        "history": "",
        "prior_operation": "",
        "symptoms": "",
        "tumor": "",
        "grade": "",
        "tnm": "",
        "lymph_node": "",
        "ls": "",
        "immuno": "",
        "imaging": "尿道肿块",
        "pathology": "",
        "surgery": "",
        "other_treatment": "",
        "recurrence": "",
        "followup": "",
        "remarks": "",
        "source_row": 0,
    }
    values.update(overrides)
    return CaseRecord(**values)


class CaseMetadataTests(unittest.TestCase):
    def test_source_metadata_is_public_and_searchable(self):
        rec = make_record(
            "USER-077",
            patient_name="甲",
            source_case_number=12,
            source_document="影像片子汇总.pdf",
            source_pages=[13, 14],
            source_hash="abc",
            source_import_key="abc:12",
            imaging_findings=[{"text": "双侧腹股沟淋巴结"}],
        )

        public = rec.as_public_dict()

        self.assertEqual(public["source_case_number"], 12)
        self.assertEqual(public["source_pages"], [13, 14])
        self.assertIn("甲", rec.searchable_text)
        self.assertIn("双侧腹股沟淋巴结", rec.searchable_text)

    def test_imported_cases_sort_by_source_number_without_reordering_other_cases(self):
        rows = [
            make_record("USER-090", source_document="影像片子汇总.pdf", source_case_number=12),
            make_record("USER-001"),
            make_record("USER-079", source_document="影像片子汇总.pdf", source_case_number=2),
            make_record("USER-078", source_document="影像片子汇总.pdf", source_case_number=1),
        ]

        ordered = sorted(rows, key=case_sort_key)

        self.assertEqual([row.source_case_number for row in ordered[:3]], [1, 2, 12])
        self.assertEqual(ordered[-1].case_id, "USER-001")

    def test_old_case_constructor_remains_valid(self):
        rec = make_record("USER-001")

        self.assertEqual(rec.source_pages, [])
        self.assertEqual(rec.imaging_findings, [])
        self.assertEqual(rec.source_import_key, "")


if __name__ == "__main__":
    unittest.main()
