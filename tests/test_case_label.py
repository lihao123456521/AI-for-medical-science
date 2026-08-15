import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def run_app_script(code: str, runtime: Path):
    project = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["USCC_DATA_DIR"] = str(runtime)
    env["DATA_PATH"] = str(project / "data" / "knowledge_base.xlsx")
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


class CaseLabelTests(unittest.TestCase):
    def test_excel_case_label_editable_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            runtime.mkdir()
            # Keep the runtime non-empty so app.py retains workbook-backed records.
            (runtime / "articles.json").write_text('[{"title":"audit-sentinel"}]', encoding="utf-8")
            code = """
import json
import zipfile
from io import BytesIO
import app
c = app.app.test_client()
target = next(r for r in app.kb.records if not app._is_user_case(r))
case_id = target.case_id
patched = c.patch(f'/api/case/{case_id}/label', json={'label': '重点随访组'}).get_json()
after = c.get('/api/cases?limit=500&q=').get_json()
sheets = {x['case_id']: x.get('sheet') for x in after.get('cases', [])}
backup_names = zipfile.ZipFile(BytesIO(c.get('/api/export').data)).namelist()
print(json.dumps({
    'case_id': case_id,
    'patched_ok': patched.get('ok'),
    'sheet': sheets.get(case_id),
    'override_in_backup': 'case_label_overrides.json' in backup_names,
}))
"""
            result = run_app_script(code, runtime)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertTrue(out["case_id"], "知识库应至少包含一个病例")
            self.assertTrue(out["patched_ok"], "Excel 内置病例标签应允许编辑")
            self.assertEqual(out["sheet"], "重点随访组")
            self.assertTrue(out["override_in_backup"], "病例标签覆盖必须包含在完整备份中")
            overrides = json.loads((runtime / "case_label_overrides.json").read_text(encoding="utf-8"))
            self.assertEqual(overrides[out["case_id"]], "重点随访组")
            saved = json.loads((runtime / "user_cases.json").read_text(encoding="utf-8"))
            self.assertFalse(any(row.get("case_id") == out["case_id"] for row in saved))

            # 重启进程后覆盖仍然生效
            code_restart = f"""
import json
import app
c = app.app.test_client()
after = c.get('/api/cases?limit=500&q=').get_json()
sheets = {{x['case_id']: x.get('sheet') for x in after.get('cases', [])}}
print(json.dumps({{'sheet': sheets.get({out['case_id']!r})}}))
"""
            result2 = run_app_script(code_restart, runtime)
            self.assertEqual(result2.returncode, 0, result2.stderr)
            out2 = json.loads(result2.stdout.strip().splitlines()[-1])
            self.assertEqual(out2["sheet"], "重点随访组")


if __name__ == "__main__":
    unittest.main()
