from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import taxonomy_models as tm  # noqa: E402
except ModuleNotFoundError:
    tm = None


NOW = "2026-07-15T00:00:00+08:00"


class TaxonomyModuleContractTests(unittest.TestCase):
    def test_taxonomy_models_module_exists(self):
        self.assertIsNotNone(tm, "scripts/taxonomy_models.py must exist")


@unittest.skipUnless(tm is not None, "taxonomy_models is not implemented yet")
class TaxonomyModelTests(unittest.TestCase):
    def make_registry(self):
        registry = tm.Registry.empty(parameters_hash="abc", now=NOW)
        registry.categories = {
            "a": tm.Category(id="a", name="A", definition="A 类", status="stable"),
            "b": tm.Category(id="b", name="B", definition="B 类", status="stable"),
        }
        return registry

    def test_registry_round_trip_is_deterministic_and_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "taxonomy.json"
            registry = self.make_registry()
            registry.memberships.append(
                tm.Membership(
                    page="pages/GNN.md",
                    category_id="a",
                    score=0.9,
                    signals={"semantic": 0.9},
                    reason="语义",
                )
            )
            tm.write_registry(path, registry, existing_pages={"pages/GNN.md"})
            first = path.read_bytes()
            loaded = tm.load_registry(path)
            tm.write_registry(path, loaded, existing_pages={"pages/GNN.md"})

            self.assertEqual(path.read_bytes(), first)
            payload = json.loads(first)
            self.assertEqual(list(payload["categories"]), ["a", "b"])
            self.assertEqual(payload["memberships"][0]["page"], "pages/GNN.md")

    def test_validation_rejects_parent_cycles_and_dangling_memberships(self):
        registry = self.make_registry()
        registry.categories["a"].parents = ["b"]
        registry.categories["b"].parents = ["a"]
        registry.memberships.append(
            tm.Membership(
                page="pages/X.md",
                category_id="missing",
                score=0.8,
                signals={},
                reason="x",
            )
        )
        with self.assertRaises(tm.TaxonomyValidationError):
            tm.validate_registry(registry, existing_pages={"pages/X.md"})

    def test_validation_rejects_asymmetric_related_redirect_cycles_and_bad_scores(self):
        registry = self.make_registry()
        registry.categories["a"].related = ["b"]
        with self.assertRaisesRegex(tm.TaxonomyValidationError, "related"):
            tm.validate_registry(registry, existing_pages=set())

        registry.categories["b"].related = ["a"]
        registry.categories["a"].status = "merged"
        registry.categories["a"].redirect_to = "b"
        registry.categories["b"].status = "merged"
        registry.categories["b"].redirect_to = "a"
        with self.assertRaisesRegex(tm.TaxonomyValidationError, "redirect"):
            tm.validate_registry(registry, existing_pages=set())

        registry.categories["a"].status = "stable"
        registry.categories["a"].redirect_to = None
        registry.categories["b"].status = "stable"
        registry.categories["b"].redirect_to = None
        registry.memberships.append(
            tm.Membership("pages/X.md", "a", math.nan, {}, "invalid")
        )
        with self.assertRaisesRegex(tm.TaxonomyValidationError, "score"):
            tm.validate_registry(registry, existing_pages={"pages/X.md"})

    def test_ids_and_parameter_hashes_are_stable(self):
        first = tm.new_category_id(["pages/B.md", "pages/A.md"], set())
        second = tm.new_category_id(["pages/A.md", "pages/B.md"], set())
        occupied = tm.new_category_id(["pages/A.md", "pages/B.md"], {first})
        self.assertEqual(first, second)
        self.assertNotEqual(first, occupied)
        self.assertTrue(first.startswith("cat_"))
        self.assertEqual(tm.parameters_hash({"b": 2, "a": 1}), tm.parameters_hash({"a": 1, "b": 2}))

    def test_events_may_reference_historical_category_ids(self):
        registry = self.make_registry()
        registry.events.append(
            tm.TaxonomyEvent(
                type="delete",
                category_ids=["category_removed_from_current_snapshot"],
                reason="类别成员已为空",
                created_at=NOW,
            )
        )

        try:
            tm.validate_registry(registry, existing_pages=set())
        except tm.TaxonomyValidationError as error:
            self.fail(f"historical event IDs must remain auditable: {error}")


if __name__ == "__main__":
    unittest.main()
