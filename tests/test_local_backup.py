import importlib.util
import json
import tempfile
import unittest
import zipfile
from datetime import datetime
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

    def test_create_accepts_fixed_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "kb"; (root / "pages").mkdir(parents=True)
            archive = backup.create(root, Path(folder) / "backups", datetime(2026, 1, 2, 3, 4, 5))
            self.assertEqual(archive.name, "knowledge-base-20260102-030405.zip")
            self.assertEqual(backup.verify(archive)["createdAt"], "2026-01-02T03:04:05")

    def test_verify_rejects_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "bad.zip"
            with zipfile.ZipFile(archive, "w") as item:
                item.writestr("pages/A.md", "changed")
                item.writestr("manifest.json", '{"files":{"pages/A.md":"bad"}}')
            with self.assertRaises(ValueError):
                backup.verify(archive)

    def test_preview_reports_conflicts_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source"; (source / "pages").mkdir(parents=True)
            (source / "pages" / "A.md").write_text("old\n", encoding="utf-8")
            (source / "pages" / "B.md").write_text("new\n", encoding="utf-8")
            archive = backup.create(source, Path(folder) / "backups")
            root = Path(folder) / "kb"; (root / "pages").mkdir(parents=True)
            (root / "pages" / "A.md").write_text("changed\n", encoding="utf-8")
            result = backup.preview(archive, root)
            self.assertIn("pages/A.md", result["changed"])
            self.assertIn("pages/B.md", result["added"])
            self.assertEqual((root / "pages" / "A.md").read_text(encoding="utf-8"), "changed\n")

    def test_verify_rejects_unmanifested_member(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "extra.zip"
            with zipfile.ZipFile(archive, "w") as item:
                item.writestr("pages/A.md", "ok")
                item.writestr("extra.txt", "not audited")
                item.writestr("manifest.json", json.dumps({"files": {"pages/A.md": __import__("hashlib").sha256(b"ok").hexdigest()}}))
            with self.assertRaises(ValueError):
                backup.verify(archive)


if __name__ == "__main__":
    unittest.main()
