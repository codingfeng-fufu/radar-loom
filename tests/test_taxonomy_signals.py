from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import radar_common as rc  # noqa: E402
import taxonomy_models as tm  # noqa: E402

try:
    import taxonomy_signals as ts  # noqa: E402
except ModuleNotFoundError:
    ts = None


def unit(values):
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def page(name, tags=None, links=None):
    return rc.PageInfo(
        name=name,
        path=Path("pages") / f"{name}.md",
        frontmatter={"tags": list(tags or [])},
        body="",
        links=list(links or []),
    )


def registry_fixture():
    registry = tm.Registry.empty("hash", "2026-07-15T00:00:00+08:00")
    registry.categories = {
        "cat_seed_kg": tm.Category("cat_seed_kg", "KG", "图结构", "stable"),
        "cat_seed_rag": tm.Category("cat_seed_rag", "RAG", "检索生成", "stable"),
    }
    registry.memberships = [
        tm.Membership("pages/KGPage.md", "cat_seed_kg", 1.0, {}, "seed"),
        tm.Membership("pages/RAGPage.md", "cat_seed_rag", 1.0, {}, "seed"),
    ]
    return registry


CONFIG = {
    "assignment_threshold": 0.62,
    "forming_cohesion_threshold": 0.78,
    "forming_min_pages": 3,
    "signal_weights": {"semantic": 0.6, "links": 0.25, "tags": 0.1, "projects": 0.05},
}


class TaxonomySignalModuleTests(unittest.TestCase):
    def test_taxonomy_signals_module_exists(self):
        self.assertIsNotNone(ts, "scripts/taxonomy_signals.py must exist")


@unittest.skipUnless(ts is not None, "taxonomy_signals is not implemented yet")
class TaxonomySignalTests(unittest.TestCase):
    def test_incremental_score_combines_all_configured_signals(self):
        score = ts.combine_signals(
            {"semantic": 0.8, "links": 0.6, "tags": 1.0, "projects": 0.0},
            CONFIG["signal_weights"],
        )
        self.assertAlmostEqual(score, 0.73)

    def test_page_can_join_multiple_categories_above_threshold(self):
        pages = {
            "KGPage": page("KGPage", tags=["KG"], links=["Hybrid"]),
            "RAGPage": page("RAGPage", tags=["RAG"], links=["Hybrid"]),
            "Hybrid": page("Hybrid", tags=["KG", "RAG"], links=["KGPage", "RAGPage"]),
        }
        vectors = {
            "KGPage": unit([1.0, 0.0]),
            "RAGPage": unit([0.0, 1.0]),
            "Hybrid": unit([1.0, 1.0]),
        }

        assignments = ts.classify_page("Hybrid", vectors, registry_fixture(), pages, CONFIG)

        self.assertEqual(
            {item.category_id for item in assignments},
            {"cat_seed_kg", "cat_seed_rag"},
        )
        self.assertTrue(all(item.score >= CONFIG["assignment_threshold"] for item in assignments))
        self.assertTrue(all("semantic" in item.signals for item in assignments))

    def test_three_novel_cohesive_pages_form_category_but_one_outlier_does_not(self):
        vectors = {
            "KGPage": unit([1.0, 0.0]),
            "RAGPage": unit([0.9, 0.1]),
            "New A": unit([0.0, 1.0]),
            "New B": unit([0.03, 1.0]),
            "New C": unit([-0.03, 1.0]),
            "Outlier": unit([-1.0, 0.0]),
        }
        registry = registry_fixture()
        registry.memberships = [
            tm.Membership("pages/KGPage.md", "cat_seed_kg", 1.0, {}, "seed"),
            tm.Membership("pages/RAGPage.md", "cat_seed_kg", 1.0, {}, "seed"),
        ]

        formed = ts.detect_forming_group("New C", vectors, registry, CONFIG)

        self.assertIsNotNone(formed)
        self.assertEqual(formed.members, ["New A", "New B", "New C"])
        self.assertGreaterEqual(formed.cohesion, CONFIG["forming_cohesion_threshold"])
        self.assertIsNone(ts.detect_forming_group("Outlier", vectors, registry, CONFIG))


if __name__ == "__main__":
    unittest.main()
