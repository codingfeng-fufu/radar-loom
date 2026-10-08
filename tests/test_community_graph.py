from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import community_graph as cg  # noqa: E402
import radar_common as rc  # noqa: E402


def page(name: str, links: list[str]) -> rc.PageInfo:
    return rc.PageInfo(name, Path(f"pages/{name}.md"), {"摘要": f"{name} 摘要", "tags": ["基础"]}, "", links)


class CommunityGraphTests(unittest.TestCase):
    def test_explicit_edges_only_include_eligible_knowledge_pages(self):
        all_pages = {"A": page("A", ["B", "项目"]), "B": page("B", ["A"]), "项目": page("项目", [])}
        edges, broken = cg.explicit_graph(all_pages, {"A": all_pages["A"], "B": all_pages["B"]})
        self.assertEqual(edges, [("A", "B"), ("B", "A")])
        self.assertEqual(broken, [])

    def test_community_payload_is_deterministic_and_preserves_directed_cross_edges(self):
        pages = {name: page(name, []) for name in ("A", "B", "C", "D")}
        edges = [("A", "B"), ("B", "A"), ("C", "D"), ("D", "C"), ("B", "C")]
        first = cg.build_communities(pages, edges, [], resolution=1.0, seed=42)
        second = cg.build_communities(pages, edges, [], resolution=1.0, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(first["algorithm"], {"name": "leiden", "resolution": 1.0, "seed": 42})
        self.assertEqual(set(first["memberships"]), set(pages))
        self.assertTrue(all(item["summaryMeta"]["provider"] == "fallback" for item in first["communities"]))
        self.assertEqual(sum(edge["count"] for edge in first["edges"]), 1)

    def test_real_community_graph_excludes_structural_pages(self):
        all_pages, eligible = cg._knowledge_pages()
        self.assertNotIn("首页", eligible)
        for page_info in eligible.values():
            self.assertNotIn("MOC", page_info.frontmatter.get("tags", []))
            self.assertNotIn("项目", page_info.frontmatter.get("tags", []))
        edges, broken = cg.explicit_graph(all_pages, eligible)
        payload = cg.build_communities(eligible, edges, broken)
        self.assertEqual(payload["broken"], [])
        self.assertEqual(set(payload["memberships"]), set(eligible))


if __name__ == "__main__":
    unittest.main()
