from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import taxonomy_engine as te  # noqa: E402
import taxonomy_models as tm  # noqa: E402


CONFIG = json.loads((ROOT / "config" / "taxonomy.json").read_text(encoding="utf-8"))


def page(title, body, tags=""):
    tag_line = f"tags: [{tags}]\n" if tags else "tags: []\n"
    return f"---\n{tag_line}摘要: {body}\n---\n# {title}\n\n{body}\n"


class TaxonomyEndToEndTests(unittest.TestCase):
    def test_three_novel_pages_form_and_then_shrink_a_category(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"TAXONOMY_TEST_ENCODER": "deterministic"}, clear=False
        ):
            vault = Path(directory)
            (vault / "pages").mkdir()
            (vault / "pages" / "Seed.md").write_text(
                page("Seed", "knowledge graph entity relation", "KG"), encoding="utf-8"
            )
            engine = te.TaxonomyEngine(vault, CONFIG)
            engine.migrate(today="2026-07-15")
            topic = "quantum banana lattice phase transport coherent spectral boundary operator manifold tensor diffusion kernel"
            for name in ("Novel A", "Novel B", "Novel C"):
                (vault / "pages" / f"{name}.md").write_text(page(name, topic), encoding="utf-8")

            registry = engine.sync(today="2026-07-16", allow_global=False)
            formed = [category for category in registry.categories.values() if category.status == "forming"]
            self.assertEqual(len(formed), 1)
            category_id = formed[0].id
            self.assertEqual(
                sum(item.category_id == category_id for item in registry.memberships), 3
            )

            (vault / "pages" / "Novel C.md").unlink()
            registry = engine.sync(today="2026-07-17", allow_global=False)
            self.assertEqual(
                sum(item.category_id == category_id for item in registry.memberships), 2
            )
            tm.validate_registry(
                registry,
                {"pages/Seed.md", "pages/Novel A.md", "pages/Novel B.md"},
            )


if __name__ == "__main__":
    unittest.main()
