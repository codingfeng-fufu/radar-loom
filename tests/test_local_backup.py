import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("local_backup", Path(__file__).parents[1] / "scripts/local_backup.py")
backup = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(backup)


class LocalBackupTests(unittest.TestCase):
    def test_create_verify_and_stage_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "kb"; (root / "pages").mkdir(parents=True)
            (root / "pages" / "A.md").write_text("# A\n", encoding="utf-8")
            destination = Path(folder) / "backups"
            archive = backup.create(root, destination)
            self.assertIn("pages/A.md", backup.verify(archive)["files"])
            restored = backup.stage_restore(archive, Path(folder) / "restored")
            self.assertEqual((restored / "pages/A.md").read_text(encoding="utf-8"), "# A\n")

    def test_verify_rejects_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as item:
                item.writestr("pages/A.md", "changed")
                item.writestr("manifest.json", '{"files":{"pages/A.md":"bad"}}')
            with self.assertRaises(ValueError):
                backup.verify(archive)


if __name__ == "__main__":
    unittest.main()
