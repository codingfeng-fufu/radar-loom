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
        self.assertIn("spacingFactor", self.html)

    def test_workspace_has_stable_full_screen_regions(self):
        for element_id in ("toolbar", "filters", "graph", "details", "loading", "errorState", "emptyState"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("100dvh", self.html)
        self.assertIn("minmax(0, 1fr)", self.html)
        self.assertIn('rel="icon" href="data:,"', self.html)

    def test_search_filters_focus_and_layout_controls_are_implemented(self):
        for function in ("applyFilters", "focusNode", "clearFocus", "runLayout", "renderDetails"):
            with self.subTest(function=function):
                self.assertRegex(self.html, rf"function\s+{function}\s*\(")
        for element_id in ("search", "categoryFilters", "projectFilters", "neighborOnly", "fitButton", "layoutButton", "labelsToggle"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_initial_layout_uses_fast_fcose_and_manual_layout_can_refine(self):
        self.assertIn("quality: animate ? 'default' : 'draft'", self.html)
        self.assertIn("numIter: animate ? 1200 : 450", self.html)

    def test_node_content_is_written_safely_and_links_target_viewer(self):
        self.assertIn("textContent", self.html)
        self.assertIn("node.data('href')", self.html)
        self.assertNotRegex(self.html, r"details[^\n]*\.innerHTML\s*=")

    def test_mobile_drawers_and_accessible_controls_exist(self):
        self.assertIn("@media (max-width: 760px)", self.html)
        self.assertRegex(self.html, r"@media \(max-width: 760px\)[\s\S]*?\.graph \{ aspect-ratio: auto; \}")
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
        self.assertIn("fetchRevision().then", self.html)

    def test_workbench_refresh_reports_real_graph_completion(self):
        self.assertIn("type: 'kb-refresh-result'", self.html)
        self.assertIn("surface: 'graph'", self.html)
        self.assertIn("notifyRefreshResult(true)", self.html)
        self.assertIn("notifyRefreshResult(false", self.html)

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
        self.assertIn("seedInitialPositions", self.html)

    def test_root_only_taxonomy_uses_a_responsive_compact_grid(self):
        self.assertIn("const compactMobile = state.cy.width() <= 480", self.html)
        self.assertIn("const compactGraph = window.matchMedia('(max-width: 760px)').matches", self.html)
        self.assertIn("const gridWidth = Math.min(state.cy.width(), compactMobile ? 260 : 660)", self.html)
        self.assertIn("const gridHeight = Math.min(state.cy.height(), compactMobile ? 480 : 500)", self.html)
        self.assertIn("compactGraph ? 84 : Math.min(70", self.html)
        self.assertIn("'font-size': compactGraph ? 20 : 14", self.html)
        self.assertIn("state.cy.one('layoutstop'", self.html)
        self.assertIn("state.cy.zoom(0.72)", self.html)
        self.assertIn("state.cy.center()", self.html)
        self.assertIn("Math.min(70, 42 + Math.sqrt(Number(node.data('degree')) + 1) * 4)", self.html)
        self.assertRegex(
            self.html,
            re.compile(
                r"name: 'grid'.*?padding: 50,.*?avoidOverlapPadding: 30, "
                r"spacingFactor: 1\.25,.*?boundingBox: \{ x1: 0, y1: 0, w: gridWidth, h: gridHeight \},.*?"
                r"cols: compactMobile \? 2 : Math\.min\(3, state\.cy\.nodes\(\)\.length\)",
                re.DOTALL,
            ),
        )

    def test_persists_and_restores_graph_workspace(self):
        self.assertIn("radar-graph-state-v1", self.html)
        for function in (
            "readPersistedState",
            "persistGraphState",
            "restoreGraphViewport",
            "notifyGraphContext",
        ):
            with self.subTest(function=function):
                self.assertRegex(self.html, rf"function\s+{function}\s*\(")
        self.assertIn("selectedNodeId", self.html)
        self.assertIn("state.cy.on('pan zoom'", self.html)

    def test_refreshes_in_place_and_uses_local_dependencies(self):
        self.assertNotIn("cdn.jsdelivr.net", self.html)
        self.assertNotIn("location.reload()", self.html)
        self.assertIn("await loadGraph", self.html)
        self.assertIn("vendor/cytoscape/cytoscape.min.js", self.html)

    def test_reports_graph_context_and_uses_stable_tool_icons(self):
        self.assertIn("kb-context", self.html)
        self.assertIn("kind: 'graph'", self.html)
        self.assertIn("visibleNodes", self.html)
        self.assertIn("data-icon=", self.html)
        self.assertNotIn(">⌗<", self.html)

    def test_profile_selects_data_url_and_independent_storage(self):
        self.assertIn("profileParam", self.html)
        self.assertIn("['knowledge', 'interview'].includes(profileParam)", self.html)
        self.assertIn("profileParam : 'knowledge'", self.html)
        self.assertIn("knowledge: 'graph-data.json'", self.html)
        self.assertIn("interview: 'interview-graph-data.json'", self.html)
        self.assertIn("radar-graph-state-knowledge-v1", self.html)
        self.assertIn("radar-graph-state-interview-v1", self.html)
        self.assertIn("fetch(GRAPH_DATA_URL", self.html)

    def test_external_nodes_are_distinct_link_to_knowledge_and_do_not_inflate_stats(self):
        self.assertIn("nodeType: node.external ? 'external' : 'page'", self.html)
        self.assertIn('node[nodeType = "external"]', self.html)
        self.assertIn("viewer.html?section=knowledge&f=", self.html)
        self.assertIn("internalVisibleNodes", self.html)
        self.assertIn(".not('[nodeType = \"external\"]')", self.html)
        self.assertIn("internalNodes", self.html)
        self.assertIn("internalPayloadNodes", self.html)
        self.assertIn("!node.external", self.html)
        self.assertIn("internalPayloadNodes.filter", self.html)

    def test_graph_context_includes_profile_and_section(self):
        self.assertIn("profile: PROFILE", self.html)
        self.assertIn("section: PROFILE", self.html)

    def test_background_tap_collapses_taxonomy_members_before_clearing_focus(self):
        self.assertRegex(
            self.html,
            r"state\.cy\.on\('tap', \(event\) => \{ if \(event\.target === state\.cy\) \{\s*collapseTaxonomyMembers\(\);\s*clearFocus\(\{ close: true \}\);",
        )

    def test_taxonomy_sources_and_candidate_progress_are_visually_distinct(self):
        self.assertIn('[source = "seed"]', self.html)
        self.assertIn('[source = "automatic"]', self.html)
        self.assertIn("种子分类", self.html)
        self.assertIn("自动分类", self.html)
        self.assertIn("候选分类", self.html)
        self.assertRegex(self.html, r"label:\s*`\$\{candidateName\}\s+\$\{members\.length\}/\$\{targetSize\}")

    def test_taxonomy_legend_swatches_match_node_styles(self):
        self.assertRegex(self.html, r"\.legend-line\.seed-source\s*\{[^}]*border-color:\s*#b97832")
        self.assertRegex(self.html, r"\.legend-line\.automatic-source\s*\{[^}]*border-color:\s*#6176a8[^}]*border-top-style:\s*double")
        self.assertRegex(self.html, r"\.legend-line\.candidate-source\s*\{[^}]*border-color:\s*#6dc5ad[^}]*border-top-style:\s*dashed")

    def test_taxonomy_expansion_guards_missing_data_and_detects_candidate_lifecycle(self):
        self.assertIn("state.payload?.taxonomy?.categories", self.html)
        self.assertIn("if (!categoryId || !Array.isArray(categories)) return []", self.html)
        self.assertIn("category?.nodeType === 'candidate'", self.html)
        self.assertIn("category?.status === 'candidate'", self.html)
        self.assertIn("category?.lifecycle === 'candidate'", self.html)
        self.assertIn("categoryNode.data('nodeType') === 'candidate'", self.html)
        self.assertIn("source: categoryNode.id()", self.html)
        self.assertIn("edgeType: isCandidate ? 'candidate-member' : 'membership'", self.html)


if __name__ == "__main__":
    unittest.main()
