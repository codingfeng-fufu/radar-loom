from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "viewer.html"


class ViewerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = VIEWER.read_text(encoding="utf-8")

    def test_single_file_loads_required_rendering_libraries(self):
        for library in ("marked", "purify", "highlight", "mermaid"):
            with self.subTest(library=library):
                self.assertIn(library, self.html.lower())

    def test_highlight_uses_a_browser_bundle(self):
        self.assertIn("cdnjs.cloudflare.com/ajax/libs/highlight.js", self.html)
        self.assertNotIn("highlight.js@11.11.1/lib/common.min.js", self.html)

    def test_defaults_to_home_and_builds_sidebar_from_index(self):
        self.assertRegex(self.html, r"DEFAULT_FILE\s*=\s*['\"]首页\.md['\"]")
        self.assertIn("_index.md", self.html)
        self.assertRegex(self.html, r"function\s+parseIndex\s*\(")

    def test_path_policy_rejects_traversal_and_limits_markdown_roots(self):
        self.assertRegex(self.html, r"function\s+validatePath\s*\(")
        self.assertIn("segment === '..'", self.html)
        self.assertIn("pages/", self.html)
        self.assertIn(".md", self.html)

    def test_render_pipeline_handles_frontmatter_wikilinks_and_sanitizing(self):
        self.assertRegex(self.html, r"function\s+splitFrontmatter\s*\(")
        self.assertRegex(self.html, r"function\s+rewriteWikilinks\s*\(")
        self.assertIn("DOMPurify.sanitize", self.html)
        self.assertIn("details", self.html)

    def test_render_pipeline_handles_highlighting_and_mermaid(self):
        self.assertIn("hljs.highlightElement", self.html)
        self.assertIn("mermaid.run", self.html)

    def test_viewer_has_stable_responsive_layout_and_accessible_controls(self):
        self.assertIn("@media", self.html)
        self.assertIn('aria-label="打开导航"', self.html)
        self.assertIn('id="sidebar"', self.html)
        self.assertIsNone(re.search(r"letter-spacing\s*:\s*-", self.html))


if __name__ == "__main__":
    unittest.main()
