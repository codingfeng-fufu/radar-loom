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

    def test_live_refresh_polls_revision_and_replaces_the_graph_safely(self):
        self.assertIn("/api/revision", self.html)
        self.assertRegex(self.html, r"setInterval\([^,]+,\s*4000\)")
        self.assertRegex(self.html, r"async function\s+loadGraph\s*\(")
        self.assertRegex(self.html, r"async function\s+checkForUpdates\s*\(")
        self.assertIn("state.refreshing", self.html)
        self.assertIn("state.cy?.destroy()", self.html)
        self.assertIn("el.categoryFilters.replaceChildren()", self.html)
        self.assertIn("el.projectFilters.replaceChildren()", self.html)
        self.assertIn("status.revision !== state.revision", self.html)

    def test_workbench_refresh_message_is_supported_by_the_graph_page(self):
        self.assertIn("window.addEventListener('message'", self.html)
        self.assertIn("http://127.0.0.1:18080", self.html)
        self.assertIn("event.data?.type === 'kb-refresh'", self.html)
        self.assertIn("location.reload()", self.html)

    def test_graph_has_three_stable_modes_and_manual_rebuild(self):
        for value in ('data-mode="knowledge"', 'data-mode="taxonomy"', 'data-mode="combined"'):
            self.assertIn(value, self.html)
        self.assertIn('id="rebuildTaxonomy"', self.html)
        self.assertIn("/api/taxonomy/rebuild", self.html)

    def test_taxonomy_elements_and_details_are_rendered_without_inner_html(self):
        for function in ("taxonomyElements", "combinedElements", "renderCategoryDetails", "renderMembershipDetails"):
            self.assertRegex(self.html, rf"function\s+{function}\s*\(")
        self.assertIn("data(status)", self.html)
        self.assertNotRegex(self.html, r"detailContent[^\n]*innerHTML")

    def test_mode_switch_does_not_resize_workspace_or_duplicate_handlers(self):
        self.assertIn("state.mode", self.html)
        self.assertIn("replaceGraphElements", self.html)
        self.assertIn("bindModeIndependentHandlersOnce", self.html)
        self.assertIn("aspect-ratio", self.html)


if __name__ == "__main__":
    unittest.main()
