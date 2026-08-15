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
            code = """
import json
import app
c = app.app.test_client()
first = c.get('/api/cases?limit=500').get_json()
case_id = next((x['case_id'] for x in first.get('cases', []) if str(x['case_id']).startswith(('SEED-CASE-', 'USER-'))), '')
patched = c.patch(f'/api/case/{case_id}/label', json={'label': '重点随访组'}).get_json()
after = c.get('/api/cases?limit=500&q=').get_json()
sheets = {x['case_id']: x.get('sheet') for x in after.get('cases', [])}
print(json.dumps({'case_id': case_id, 'patched_ok': patched.get('ok'), 'sheet': sheets.get(case_id)}))
"""
            result = run_app_script(code, runtime)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertTrue(out["case_id"], "知识库应至少包含一个病例")
            self.assertTrue(out["patched_ok"], "Excel 内置病例标签应允许编辑")
            self.assertEqual(out["sheet"], "重点随访组")
            saved = json.loads((runtime / "user_cases.json").read_text(encoding="utf-8"))
            saved_sheet = next((row.get("sheet") for row in saved if row.get("case_id") == out["case_id"]), None)
            self.assertEqual(saved_sheet, "重点随访组")

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
