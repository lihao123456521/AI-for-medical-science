import unittest
from pathlib import Path


class ReleasePackageContractTests(unittest.TestCase):
    def test_build_script_explicitly_copies_public_seed_after_private_json_exclusions(self):
        source = (Path(__file__).resolve().parents[1] / "scripts" / "build_release_packages.ps1").read_text(encoding="utf-8")

        self.assertIn('Join-Path $ProjectRoot "data\\seed"', source)
        self.assertIn('Join-Path $packageRoot "data\\seed"', source)
        self.assertIn("Copy-Item", source)


if __name__ == "__main__":
    unittest.main()
