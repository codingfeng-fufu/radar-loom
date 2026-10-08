from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ideas" / "scripts"))
import build_idea_index  # noqa: E402
import check_idea_health  # noqa: E402
import idea_common  # noqa: E402
import new_idea  # noqa: E402
import render_idea_graph  # noqa: E402


class IdeaLabTest(unittest.TestCase):
    def make_root(self) -> Path:
        temporary = Path(tempfile.mkdtemp()) / "ideas"
        (temporary / "pages").mkdir(parents=True)
        (temporary / "templates").mkdir()
        (temporary / "templates" / "idea.md").write_text((ROOT / "ideas" / "templates" / "idea.md").read_text(encoding="utf-8"), encoding="utf-8")
        return temporary

    def test_create_idea_uses_stable_sequential_ids_and_preserves_original(self):
        root = self.make_root()
        first = new_idea.create_idea("未经整理的原话", "一个标题", "一个问题", ["Agent"], root)
        second = new_idea.create_idea("第二条", None, "", [], root)
        self.assertTrue(first.name.startswith(f"IDEA-{idea_common.today()[:4]}-001 "))
        self.assertTrue(second.name.startswith(f"IDEA-{idea_common.today()[:4]}-002 "))
        metadata, body = idea_common.parse_frontmatter(first.read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "captured")
        self.assertEqual(metadata["domains"], ["Agent"])
        self.assertIn("未经整理的原话", body)

    def test_index_and_graph_are_isolated_and_structured(self):
        root = self.make_root()
        new_idea.create_idea("Idea A", "Idea A", "共同问题", ["RAG"], root)
        ideas = idea_common.scan_ideas(root)
        index_text, index_data = build_idea_index.render(ideas)
        graph_text, graph_data = render_idea_graph.render(ideas)
        self.assertIn("Idea A", index_text)
        self.assertEqual(index_data["stats"]["ideas"], 1)
        self.assertEqual(graph_data["stats"]["ideas"], 1)
        self.assertTrue(any(node["data"]["type"] == "problem" for node in graph_data["nodes"]))
        json.dumps(index_data, ensure_ascii=False)
        self.assertIn("graph LR", graph_text)

    def test_health_requires_generated_files_and_valid_blocked_state(self):
        root = self.make_root()
        path = new_idea.create_idea("Idea A", "Idea A", "", [], root)
        text = path.read_text(encoding="utf-8").replace("status: captured", "status: blocked")
        path.write_text(text, encoding="utf-8")
        errors, _ = check_idea_health.check(root)
        self.assertTrue(any("I8" in error for error in errors))
        self.assertTrue(any("I13" in error for error in errors))

    def test_skill_and_viewer_contracts(self):
        skill = (ROOT / ".claude" / "skills" / "capture-idea" / "SKILL.md").read_text(encoding="utf-8")
        viewer = (ROOT / "ideas" / "viewer.html").read_text(encoding="utf-8")
        graph_viewer = (ROOT / "ideas" / "graph-view.html").read_text(encoding="utf-8")
        self.assertIn("name: capture-idea", skill)
        self.assertIn("Never replace the `## 原始想法`", skill)
        self.assertIn("python3 ideas/scripts/check_idea_health.py", skill)
        self.assertIn("data/idea-index.json", viewer)
        self.assertIn("/api/ideas", viewer)
        self.assertIn("候选只提供线索，不自动合并", viewer)
        self.assertIn("openKnowledge", viewer)
        self.assertIn("idea-claude-request", viewer)
        self.assertIn("交给 Claude 整理", viewer)
        self.assertIn("requestClaude('attempt'", viewer)
        self.assertIn("kb-refresh-result", viewer)
        self.assertIn("kb-refresh-result", graph_viewer)
        self.assertIn("idea-graph-data.json", graph_viewer)
        self.assertIn("cytoscape", graph_viewer)


if __name__ == "__main__":
    unittest.main()
