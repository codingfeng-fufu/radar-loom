import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import taxonomy_candidates as tc  # noqa: E402
from taxonomy_models import Candidate, Category, Membership  # noqa: E402


def unit(values):
    value = np.asarray(values, dtype=np.float32)
    return value / np.linalg.norm(value)


class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.config = {"forming_min_pages": 3, "candidate_min_pages": 2,
                       "candidate_neighborhood_k": 12, "candidate_cohesion_threshold": .78,
                       "candidate_related_threshold": .70, "representative_page_limit": 5}

    def test_two_close_pages_form_candidate_inside_the_same_seed_category(self):
        vectors = {"A": unit([1, 0]), "B": unit([.99, .1]), "C": unit([0, 1])}
        memberships = [Membership("A.md", "cat_seed_a", .9, {"tags": 1}, "seed"), Membership("B.md", "cat_seed_a", .9, {"tags": 1}, "seed")]
        categories = {"cat_seed_a": Category("cat_seed_a", "A", "", "stable")}
        groups = tc.discover_groups(vectors, {"A": "A.md", "B": "B.md", "C": "C.md"}, memberships, categories, {}, self.config, "2026-07-19")
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].members, ["A.md", "B.md"])
        self.assertEqual(groups[0].parent_category_ids, ["cat_seed_a"])

    def test_complete_link_does_not_collapse_a_similarity_chain(self):
        self.config["candidate_compact_threshold"] = .75
        self.config["candidate_max_pages"] = 10
        vectors = {
            "A": unit([1.0, 0.0]), "B": unit([.8, .6]),
            "C": unit([.28, .96]), "D": unit([-.35, .94]),
        }
        memberships = [Membership(f"{name}.md", "cat_seed_a", .9, {"tags": 1}, "seed") for name in vectors]
        categories = {"cat_seed_a": Category("cat_seed_a", "A", "", "stable")}
        groups = tc.discover_groups(vectors, {name: f"{name}.md" for name in vectors}, memberships,
                                    categories, {}, self.config, "2026-07-19")
        self.assertTrue(groups)
        self.assertLess(max(len(group.members) for group in groups), 4)

    def test_topic_name_prefers_repeated_chinese_subject(self):
        pages = ["pages/操作系统 Operating System.md", "pages/操作系统运行机制.md",
                 "pages/操作系统同步与互斥.md", "pages/操作系统死锁.md"]
        self.assertEqual(tc.temporary_name(pages), "操作系统")

    def test_candidate_id_and_name_are_order_independent(self):
        candidate = tc.candidate_id(["b.md", "a.md"])
        self.assertTrue(candidate.startswith("candidate_"))
        self.assertEqual(candidate, tc.candidate_id(["a.md", "b.md"]))
        self.assertEqual(tc.temporary_name(["Zeta page", "Alpha page"]), "Alpha Zeta …")
        self.assertEqual(tc.temporary_name(["中文", "Alpha-123"]), "123 Alpha 中文")
        self.assertEqual(tc.temporary_name([]), "新主题")
        self.assertEqual(len(tc.temporary_name(["abcdefghijklmnop"])), 12)
        self.assertTrue(tc.temporary_name(["abcdefghijklmnop"]).endswith("…"))

    def test_novel_group_is_frozen_and_snapshot_preserves_signals(self):
        group = tc.NovelGroup(["a.md", "b.md"], .9, {"semantic_cohesion": .9, "links": .2}, ["cat_x"])
        with self.assertRaises((AttributeError, TypeError)):
            group.members = []
        result = tc.snapshot_candidates([group], [], self.config, "2026-07-19")
        self.assertEqual(result[0].signals, group.signals)

    def test_active_non_seed_category_suppresses_fully_explained_group(self):
        vectors = {"A": unit([1, 0]), "B": unit([.99, .1])}
        memberships = [Membership("A.md", "cat_auto", .9, {}, "auto"), Membership("B.md", "cat_auto", .9, {}, "auto")]
        categories = {"cat_auto": Category("cat_auto", "Auto", "", "stable")}
        groups = tc.discover_groups(vectors, {"A": "A.md", "B": "B.md"}, memberships, categories, {"cat_auto": unit([1, 0])}, self.config, "2026-07-19")
        self.assertEqual(groups, [])

    def test_snapshot_only_includes_forming_candidates_and_preserves_first_seen(self):
        group = tc.NovelGroup(["a.md", "b.md"], .9, {"semantic_cohesion": .9}, ["cat_x"])
        previous = [Candidate(tc.candidate_id(["a.md", "b.md"]), "Old", ["a.md", "b.md"], .8, 3, {}, [], "2026-07-01", "2026-07-18")]
        result = tc.snapshot_candidates([group], previous, self.config, "2026-07-19")
        self.assertEqual(result[0].first_seen_at, "2026-07-01")
        self.assertEqual(result[0].target_size, 3)
        self.assertEqual(tc.snapshot_candidates([tc.NovelGroup(["a.md", "b.md", "c.md"], .9, {}, [])], [], self.config, "2026-07-19"), [])


if __name__ == "__main__":
    unittest.main()
