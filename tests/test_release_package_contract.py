import unittest
from pathlib import Path


class ReleasePackageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Path(__file__).resolve().parents[1]
        cls.build_script = (cls.project / "scripts" / "build_release_packages.ps1").read_text(encoding="utf-8")
        cls.release_workflow = (cls.project / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    def test_build_script_explicitly_copies_public_seed_after_private_json_exclusions(self):
        self.assertIn('Join-Path $ProjectRoot "data\\seed"', self.build_script)
        self.assertIn('Join-Path $packageRoot "data\\seed"', self.build_script)
        self.assertIn("Copy-Item", self.build_script)

    def test_missing_csc_is_a_hard_failure(self):
        self.assertIn("csc.exe was not found", self.build_script)
        self.assertNotIn("Write-Warning", self.build_script)

    def test_windows_exe_is_named_uropuc_and_asserted(self):
        self.assertIn('"UroPUC.exe"', self.build_script)
        self.assertIn('Test-Path (Join-Path $windowsRoot "UroPUC.exe")', self.build_script)
        self.assertIn('throw "Windows package root is missing UroPUC.exe', self.build_script)

    def test_release_assets_use_uropuc_names(self):
        self.assertIn("UroPUC-windows.zip", self.build_script)
        self.assertIn("UroPUC-macos.tar.gz", self.build_script)
        self.assertIn("UroPUC-linux.tar.gz", self.build_script)
        self.assertNotIn("AI-rare-disease-assistant.exe", self.build_script)
        self.assertNotIn("AI-for-medical-science-windows.zip", self.release_workflow)

    def test_workflow_requires_exe_inside_windows_zip(self):
        self.assertIn('"AI-for-medical-science/UroPUC.exe" -notin $names', self.release_workflow)
        self.assertIn("dist/UroPUC-windows.zip", self.release_workflow)
        self.assertIn("dist/UroPUC.exe", self.release_workflow)


if __name__ == "__main__":
    unittest.main()
