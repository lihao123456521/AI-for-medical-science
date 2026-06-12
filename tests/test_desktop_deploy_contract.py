import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class DesktopDeployContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Path(__file__).resolve().parents[1]
        cls.script = cls.project / "scripts" / "deploy_windows_desktop.ps1"

    def test_script_declares_paths_backups_and_secret_exclusions(self):
        source = self.script.read_text(encoding="utf-8")

        for marker in ("SourceDir", "InstallDir", "RuntimeDir", "BackupRoot", "DesktopShortcut"):
            self.assertIn(marker, source)
        for private_name in (".env", "api_config.json", "api_config_history.json", "uploads"):
            self.assertIn(private_name, source)
        self.assertIn("Win32_Process", source)
        self.assertIn("$_.ProcessId -ne $PID", source)
        self.assertIn("$_.Name -in @(\"python.exe\", \"pythonw.exe\")", source)

    def test_fixture_deploy_replaces_app_but_preserves_private_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            install = root / "install"
            runtime = root / "runtime"
            backups = root / "backups"
            shortcut = root / "AI rare disease assistant.lnk"
            source.mkdir()
            install.mkdir()
            runtime.mkdir()
            (source / "app.py").write_text("new-version", encoding="utf-8")
            (source / ".env").write_text("must-not-copy", encoding="utf-8")
            (source / "data").mkdir()
            (source / "data" / "seed").mkdir()
            (source / "data" / "seed" / "manifest.json").write_text('{"case_count":93,"article_count":230}', encoding="utf-8")
            (install / "app.py").write_text("old-version", encoding="utf-8")
            (install / ".env").write_text("keep-local-env", encoding="utf-8")
            (runtime / "api_config.json").write_text('{"api_key":"local-only"}', encoding="utf-8")

            result = subprocess.run(
                [
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.script),
                    "-SourceDir", str(source), "-InstallDir", str(install), "-RuntimeDir", str(runtime),
                    "-BackupRoot", str(backups), "-DesktopShortcut", str(shortcut),
                    "-SkipProcessStop", "-SkipShortcut",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertEqual((install / "app.py").read_text(encoding="utf-8"), "new-version")
            self.assertEqual((install / ".env").read_text(encoding="utf-8"), "keep-local-env")
            self.assertIn("local-only", (runtime / "api_config.json").read_text(encoding="utf-8"))
            self.assertTrue(Path(payload["install_backup"]).exists())
            self.assertTrue(Path(payload["runtime_backup"]).exists())


if __name__ == "__main__":
    unittest.main()
