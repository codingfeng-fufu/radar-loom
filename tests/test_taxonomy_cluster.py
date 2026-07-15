from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import taxonomy_models as tm  # noqa: E402

try:
    import taxonomy_cluster as tc  # noqa: E402
except ModuleNotFoundError:
    tc = None


def unit(values):
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


CONFIG = {
    "random_seed": 20260715,
    "forming_min_pages": 3,
    "stable_min_pages": 5,
    "stable_min_runs": 2,
    "cluster_match_threshold": 0.4,
    "cluster_fusion_jaccard": 0.35,
    "related_threshold": 0.9,
    "parent_containment_threshold": 0.8,
}


def registry_fixture():
    registry = tm.Registry.empty("hash", "2026-07-01")
    registry.categories = {
        "cat_old": tm.Category("cat_old", "原类别", "原类别", "stable"),
        "cat_merged": tm.Category("cat_merged", "被合并类别", "重叠类别", "stable"),
    }
    registry.memberships = [
        tm.Membership(f"pages/{name}.md", "cat_old", 0.9, {}, "old")
        for name in ("A", "B", "C", "D")
    ] + [
        tm.Membership(f"pages/{name}.md", "cat_merged", 0.9, {}, "old")
        for name in ("A", "B")
    ]
    return registry


def has_parent_cycle(relations):
    def visit(node, active, done):
        if node in active:
            return True
        if node in done:
            return False
        active.add(node)
        if any(visit(parent, active, done) for parent in relations[node].parents):
            return True
        active.remove(node)
        done.add(node)
        return False

    done = set()
    return any(visit(node, set(), done) for node in relations)


class TaxonomyClusterModuleTests(unittest.TestCase):
    def test_taxonomy_cluster_module_exists(self):
        self.assertIsNotNone(tc, "scripts/taxonomy_cluster.py must exist")


@unittest.skipUnless(tc is not None, "taxonomy_cluster is not implemented yet")
class TaxonomyClusterTests(unittest.TestCase):
    def test_semantic_clusters_use_normalized_hdbscan_and_minimum_size(self):
        vectors = {
            "A": unit([1.0, 0.0]), "B": unit([0.999, 0.01]), "C": unit([0.999, -0.01]),
            "X": unit([0.0, 1.0]), "Y": unit([0.01, 0.999]), "Z": unit([-0.01, 0.999]),
        }
        groups = tc.semantic_clusters(vectors, min_cluster_size=3, min_samples=2)
        self.assertEqual(groups, [{"A", "B", "C"}, {"X", "Y", "Z"}])

    def test_louvain_clusters_are_deterministic_for_fixed_seed(self):
        edges = [
            ("A", "B"), ("B", "C"), ("C", "A"),
            ("X", "Y"), ("Y", "Z"), ("Z", "X"),
        ]
        pages = {"A", "B", "C", "X", "Y", "Z"}
        first = tc.graph_clusters(edges, pages, seed=20260715)
        second = tc.graph_clusters(edges, pages, seed=20260715)
        self.assertEqual(first, second)
        self.assertEqual(first, [{"A", "B", "C"}, {"X", "Y", "Z"}])

    def test_candidate_clusters_fuse_by_overlap(self):
        vectors = {name: unit([1.0, 0.0]) for name in ("A", "B", "C", "D")}
        fused = tc.fuse_clusters(
            [{"A", "B", "C"}],
            [{"B", "C", "D"}],
            vectors,
            [("A", "B"), ("C", "D")],
            CONFIG,
        )
        self.assertEqual(fused, [{"A", "B", "C", "D"}])

    def test_matching_preserves_main_id_across_split_and_redirects_merge(self):
        vectors = {
            "A": unit([1.0, 0.0]), "B": unit([1.0, 0.02]), "C": unit([1.0, -0.02]),
            "D": unit([0.0, 1.0]), "E": unit([0.02, 1.0]), "F": unit([-0.02, 1.0]),
        }
        result = tc.reconcile_clusters(
            registry_fixture(),
            [{"A", "B", "C"}, {"D", "E", "F"}],
            vectors,
            CONFIG,
            today="2026-07-15",
        )

        self.assertIn("cat_old", result.categories)
        self.assertEqual(result.categories["cat_merged"].status, "merged")
        self.assertEqual(result.categories["cat_merged"].redirect_to, "cat_old")
        self.assertIn("被合并类别", result.categories["cat_old"].aliases)
        self.assertTrue(any(event.type == "split" for event in result.events))

    def test_reconciliation_is_deterministic_for_the_same_snapshot(self):
        vectors = {
            "A": unit([1.0, 0.0]), "B": unit([1.0, 0.02]), "C": unit([1.0, -0.02]),
            "D": unit([0.0, 1.0]), "E": unit([0.02, 1.0]), "F": unit([-0.02, 1.0]),
        }
        first = tc.reconcile_clusters(
            registry_fixture(), [{"A", "B", "C"}, {"D", "E", "F"}], vectors, CONFIG, "2026-07-15"
        )
        second = tc.reconcile_clusters(
            registry_fixture(), [{"D", "E", "F"}, {"A", "B", "C"}], vectors, CONFIG, "2026-07-15"
        )
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_parent_relations_are_acyclic_and_related_relations_are_symmetric(self):
        groups = {
            "a": {"1", "2"},
            "b": {"1", "2", "3", "4"},
            "c": {"5", "6", "7"},
            "d": {"8", "9", "10"},
        }
        centroids = {
            "a": unit([1.0, 0.0]), "b": unit([1.0, 0.0]),
            "c": unit([0.0, 1.0]), "d": unit([0.05, 1.0]),
        }
        relations = tc.infer_relations(groups, centroids, CONFIG)

        self.assertFalse(has_parent_cycle(relations))
        self.assertEqual(relations["a"].parents, ["b"])
        self.assertEqual(relations["c"].related, ["d"])
        self.assertEqual(relations["d"].related, ["c"])


if __name__ == "__main__":
    unittest.main()
