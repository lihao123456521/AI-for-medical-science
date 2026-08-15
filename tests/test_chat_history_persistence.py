import json
import os
import subprocess
import sys
import tempfile
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


def test_chat_history_persists_restarts_and_is_exported():
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Path(tmp) / "runtime"
        runtime.mkdir()
        history = {
            "chats": [{
                "id": "chat-1",
                "title": "65岁男性尿道鳞癌",
                "updatedAt": 123456789,
                "patient": {"age": "65", "diagnosis": "尿道鳞癌"},
                "messages": [{"id": "m1", "role": "user", "content": "分析这个患者"}],
                "attachments": [],
            }],
            "activeId": "chat-1",
        }
        first = run_app_script(
            f"""
import io, json, zipfile
import app
c = app.app.test_client()
payload = {history!r}
saved = c.put('/api/chat/history', json=payload)
loaded = c.get('/api/chat/history')
names = zipfile.ZipFile(io.BytesIO(c.get('/api/export').data)).namelist()
print(json.dumps({{'saved': saved.status_code, 'history': loaded.get_json()['history'], 'exported': 'chat_history.json' in names}}, ensure_ascii=False))
""",
            runtime,
        )
        assert first.returncode == 0, first.stderr
        first_out = json.loads(first.stdout.strip().splitlines()[-1])
        assert first_out["saved"] == 200
        assert first_out["history"]["chats"][0]["title"] == history["chats"][0]["title"]
        assert first_out["exported"] is True

        second = run_app_script(
            """
import json
import app
c = app.app.test_client()
print(json.dumps(c.get('/api/chat/history').get_json(), ensure_ascii=False))
""",
            runtime,
        )
        assert second.returncode == 0, second.stderr
        second_out = json.loads(second.stdout.strip().splitlines()[-1])
        assert second_out["history"]["activeId"] == "chat-1"
