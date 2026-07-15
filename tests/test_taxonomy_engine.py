from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import taxonomy_models as tm  # noqa: E402
import taxonomy_signals as ts  # noqa: E402

try:
    import taxonomy_engine as te  # noqa: E402
except ModuleNotFoundError:
    te = None


CONFIG = json.loads((ROOT / "config" / "taxonomy.json").read_text(encoding="utf-8"))


class FakeEncoder:
    model_name = "fake-v1"
    max_chars = 10_000

    def encode(self, texts):
        vectors = []
        for text in texts:
            if "Failed" in text:
                raise RuntimeError("intentional encoder failure")
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vectors.append([digest[0] + 1, digest[1] + 1, digest[2] + 1])
        return np.asarray(vectors, dtype=np.float32)


def markdown(title, tags, summary="摘要"):
    return (
        "---\n"
        f"tags: [{', '.join(tags)}]\n"
        f"摘要: {summary}\n"
        "---\n"
        f"# {title}\n"
    )


class TaxonomyEngineModuleTests(unittest.TestCase):
    def test_taxonomy_engine_module_exists(self):
        self.assertIsNotNone(te, "scripts/taxonomy_engine.py must exist")
        self.assertTrue((SCRIPTS / "taxonomy_cli.py").exists(), "scripts/taxonomy_cli.py must exist")


@unittest.skipUnless(te is not None, "taxonomy_engine is not implemented yet")
class TaxonomyEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pages").mkdir()
        (self.root / "config").mkdir()
        (self.root / "config" / "taxonomy.json").write_text(
            json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8"
        )
        (self.root / "pages" / "A.md").write_text(markdown("A", ["KG", "RAG"]), encoding="utf-8")
        (self.root / "pages" / "B.md").write_text(markdown("B", ["基础"]), encoding="utf-8")
        self.engine = te.TaxonomyEngine(self.root, CONFIG, encoder=FakeEncoder())

    def tearDown(self):
        self.temp.cleanup()

    def test_migration_preserves_all_legacy_category_memberships(self):
        registry = self.engine.migrate(today="2026-07-15")
        self.assertEqual(set(registry.categories), set(ts.LEGACY_TAG_TO_SEED_ID.values()))
        pairs = {(item.page, item.category_id) for item in registry.memberships}
        self.assertIn(("pages/A.md", ts.LEGACY_TAG_TO_SEED_ID["KG"]), pairs)
        self.assertIn(("pages/A.md", ts.LEGACY_TAG_TO_SEED_ID["RAG"]), pairs)
        self.assertIn(("pages/B.md", ts.LEGACY_TAG_TO_SEED_ID["基础"]), pairs)
        self.assertTrue((self.root / "taxonomy.json").exists())

    def test_sync_handles_changed_and_deleted_pages_without_blocking_registry(self):
        self.engine.migrate(today="2026-07-15")
        (self.root / "pages" / "A.md").unlink()
        (self.root / "pages" / "Failed.md").write_text(
            markdown("Failed", ["KG"]), encoding="utf-8"
        )

        result = self.engine.sync(today="2026-07-16", allow_global=False)

        self.assertNotIn("pages/A.md", {item.page for item in result.memberships})
        self.assertIn("pages/Failed.md", result.pending_pages)
        self.assertEqual(result.changes_since_global, 2)
        tm.validate_registry(result, {"pages/B.md", "pages/Failed.md"})

    def test_no_change_sync_does_not_rewrite_registry(self):
        self.engine.migrate(today="2026-07-15")
        before = (self.root / "taxonomy.json").read_bytes()
        self.engine.sync(today="2026-07-15", allow_global=False)
        self.assertEqual((self.root / "taxonomy.json").read_bytes(), before)

    def test_global_trigger_is_due_by_count_or_age(self):
        registry = tm.Registry.empty("hash", "2026-07-01")
        registry.changes_since_global = 5
        self.assertTrue(te.global_due(registry, CONFIG, "2026-07-15"))
        registry.changes_since_global = 0
        registry.last_global_at = "2026-07-01"
        self.assertTrue(te.global_due(registry, CONFIG, "2026-07-15"))
        registry.last_global_at = "2026-07-14"
        self.assertFalse(te.global_due(registry, CONFIG, "2026-07-15"))

    def test_status_and_validate_do_not_construct_encoder(self):
        self.engine.migrate(today="2026-07-15")
        reader = te.TaxonomyEngine(self.root, CONFIG)
        status = reader.status()
        reader.validate()
        self.assertEqual(status["categories"], 8)
        self.assertEqual(status["pending_pages"], 0)

    def test_cli_help_exposes_all_commands(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPTS / "taxonomy_cli.py"), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        for command in ("migrate", "sync", "global", "status", "validate"):
            self.assertIn(command, completed.stdout)


if __name__ == "__main__":
    unittest.main()
