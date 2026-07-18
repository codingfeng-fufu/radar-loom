from __future__ import annotations

import importlib
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import radar_common as rc  # noqa: E402


def page(name: str, metadata: dict) -> rc.PageInfo:
    return rc.PageInfo(name, Path(name + ".md"), metadata, "")


class InterviewIndexTests(unittest.TestCase):
    def setUp(self):
        self.module = importlib.import_module("build_index")
        self.pages = {
            "知识": page("知识", {"tags": ["KG"], "摘要": "知识摘要"}),
            "Z面试": page("Z面试", {"page_type": "interview", "question": "如何做Z?", "summary": "Z摘要", "tags": ["z"], "roles": ["后端"], "difficulty": "深入"}),
            "A面试": page("A面试", {"page_type": "interview", "原问题": "如何做A?", "摘要": "A摘要", "tags": ["a"], "roles": ["前端"], "difficulty": "基础"}),
            "缺摘要": page("缺摘要", {"page_type": "interview", "question": "缺摘要问题", "tags": ["b"], "roles": ["前端"], "difficulty": "进阶"}),
        }

    def test_render_indexes_isolates_pages_and_orders_interviews(self):
        knowledge, interview, stats = self.module.render_indexes(self.pages)
        self.assertIn("[[知识]]", knowledge)
        self.assertNotIn("面试", knowledge)
        self.assertIn("[[A面试]]", interview)
        self.assertNotIn("[[知识]]", interview)
        self.assertIn("原问题: 如何做A?", interview)
        self.assertIn("角色: 前端", interview)
        self.assertIn("角色: 前端", interview.split("[[A面试]]", 1)[1].split("\n", 1)[0])
        self.assertIn("难度: 基础", interview)
        self.assertLess(interview.index("A面试"), interview.index("Z面试"))
        self.assertEqual(stats["interviews"], 3)

    def test_interview_entry_tags_are_sorted(self):
        self.pages["A面试"].frontmatter["tags"] = ["zeta", "alpha"]
        rendered, _, _ = self.module.render_interview_index({"A面试": self.pages["A面试"]})
        self.assertLess(rendered.index("#alpha"), rendered.index("#zeta"))

    def test_role_section_orders_multi_role_entries_by_difficulty(self):
        self.pages["深入多角色"] = page("深入多角色", {"page_type": "interview", "question": "q", "summary": "s", "tags": ["a"], "roles": ["前端", "后端"], "difficulty": "深入"})
        self.pages["基础多角色"] = page("基础多角色", {"page_type": "interview", "question": "q", "summary": "s", "tags": ["b"], "roles": ["前端", "后端"], "difficulty": "基础"})
        rendered, _, _ = self.module.render_interview_index({"深入多角色": self.pages["深入多角色"], "基础多角色": self.pages["基础多角色"]})
        section = rendered.split("## 角色: 前端", 1)[1].split("## 角色:", 1)[0]
        self.assertLess(section.index("基础多角色"), section.index("深入多角色"))

    def test_interview_summary_fallback_and_missing_count(self):
        rendered, count, missing = self.module.render_interview_index({k: v for k, v in self.pages.items() if k != "知识"})
        self.assertEqual(count, 3)
        self.assertEqual(missing, 1)
        self.assertIn("A摘要", rendered)
        self.assertIn("(缺摘要)", rendered)

    def test_render_indexes_is_deterministic_for_input_order(self):
        first = self.module.render_indexes(self.pages)[1]
        reversed_pages = dict(reversed(list(self.pages.items())))
        self.assertEqual(first, self.module.render_indexes(reversed_pages)[1])

    def test_main_writes_both_indexes_and_prints_summaries(self):
        old_scan, old_index, old_interview = rc.scan_pages, rc.INDEX_FILE, rc.INTERVIEW_INDEX_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                rc.scan_pages = lambda: self.pages
                rc.INDEX_FILE = Path(tmp) / "_index.md"
                rc.INTERVIEW_INDEX_FILE = Path(tmp) / "_interview_index.md"
                out = io.StringIO()
                with redirect_stdout(out):
                    self.module.main([])
                self.assertTrue(rc.INDEX_FILE.exists())
                self.assertTrue(rc.INTERVIEW_INDEX_FILE.exists())
                self.assertIn("已生成 _index.md", out.getvalue())
                self.assertIn("已生成 _interview_index.md", out.getvalue())
        finally:
            rc.scan_pages, rc.INDEX_FILE, rc.INTERVIEW_INDEX_FILE = old_scan, old_index, old_interview

    def test_atomic_pair_rolls_back_when_second_replace_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            sentinel = Path(str(first) + ".tmp")
            sentinel.write_text("sentinel", encoding="utf-8")
            first.write_text("old-a", encoding="utf-8")
            second.write_text("old-b", encoding="utf-8")
            original_replace = Path.replace
            calls = {"count": 0}
            def fail_second(self, target):
                calls["count"] += 1
                if calls["count"] == 2:
                    raise OSError("injected")
                return original_replace(self, target)
            Path.replace = fail_second
            try:
                with self.assertRaises(OSError):
                    self.module.atomic_write_pair(((first, "new-a"), (second, "new-b")))
            finally:
                Path.replace = original_replace
            self.assertEqual(first.read_text(encoding="utf-8"), "old-a")
            self.assertEqual(second.read_text(encoding="utf-8"), "old-b")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "sentinel")


if __name__ == "__main__":
    unittest.main()
