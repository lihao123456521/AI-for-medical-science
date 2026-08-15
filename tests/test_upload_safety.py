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


def test_empty_and_corrupt_uploads_are_rejected_without_residue():
    with tempfile.TemporaryDirectory() as tmp:
        runtime = Path(tmp) / "runtime"
        runtime.mkdir()
        code = r'''
import io
import json
import app

c = app.app.test_client()
empty = c.post('/api/upload', data={'file': (io.BytesIO(b''), 'empty.txt')})
corrupt = c.post('/api/upload', data={'file': (io.BytesIO(b'not a pdf'), 'broken.pdf')})
fake_image = c.post('/api/upload', data={'file': (io.BytesIO(b'not a png'), 'broken.png')})
print(json.dumps({
    'empty_status': empty.status_code,
    'corrupt_status': corrupt.status_code,
    'fake_image_status': fake_image.status_code,
    'files': sorted(p.name for p in app.UPLOAD_DIR.iterdir() if p.is_file()),
}))
'''
        result = run_app_script(code, runtime)
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout.strip().splitlines()[-1])
        assert out["empty_status"] == 400
        assert out["corrupt_status"] == 400
        assert out["fake_image_status"] == 400
        assert out["files"] == []
