from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_VIEW = ROOT / "graph-view.html"


class GraphViewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = GRAPH_VIEW.read_text(encoding="utf-8")

    def test_uses_cytoscape_and_fcose_with_structured_data(self):
        for value in ("cytoscape.min.js", "cytoscape-fcose", "graph-data.json", "name: 'fcose'"):
            with self.subTest(value=value):
                self.assertIn(value, self.html)

    def test_workspace_has_stable_full_screen_regions(self):
        for element_id in ("toolbar", "filters", "graph", "details", "loading", "errorState", "emptyState"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("100dvh", self.html)
        self.assertIn("minmax(0, 1fr)", self.html)

    def test_search_filters_focus_and_layout_controls_are_implemented(self):
        for function in ("applyFilters", "focusNode", "clearFocus", "runLayout", "renderDetails"):
            with self.subTest(function=function):
                self.assertRegex(self.html, rf"function\s+{function}\s*\(")
        for element_id in ("search", "categoryFilters", "projectFilters", "neighborOnly", "fitButton", "layoutButton", "labelsToggle"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_node_content_is_written_safely_and_links_target_viewer(self):
        self.assertIn("textContent", self.html)
        self.assertIn("node.data('href')", self.html)
        self.assertNotRegex(self.html, r"details[^\n]*\.innerHTML\s*=")

    def test_mobile_drawers_and_accessible_controls_exist(self):
        self.assertIn("@media (max-width: 760px)", self.html)
        self.assertIn('aria-label="打开筛选"', self.html)
        self.assertIn('aria-label="关闭详情"', self.html)
        self.assertIn("filters-open", self.html)
        self.assertIn("details-open", self.html)
        self.assertIsNone(re.search(r"letter-spacing\s*:\s*-", self.html))


if __name__ == "__main__":
    unittest.main()
