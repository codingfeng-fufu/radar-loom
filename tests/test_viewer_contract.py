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
        self.assertIn("vendor/highlight/highlight.min.js", self.html)
        self.assertNotIn("highlight.js@11.11.1/lib/common.min.js", self.html)

    def test_katex_assets_and_all_supported_delimiters_are_present(self):
        self.assertIn("katex.min.css", self.html)
        self.assertIn("katex.min.js", self.html)
        self.assertIn("auto-render.min.js", self.html)
        self.assertNotIn('<script defer src="https://cdn.jsdelivr.net/npm/katex', self.html)
        for delimiter in ("'$$'", "'$'", r"'\\('", r"'\\['"):
            with self.subTest(delimiter=delimiter):
                self.assertIn(delimiter, self.html)

    def test_math_runs_after_sanitizing_with_safe_error_handling(self):
        sanitize_at = self.html.index("DOMPurify.sanitize")
        render_at = self.html.index("renderMathInElement")
        self.assertLess(sanitize_at, render_at)
        self.assertRegex(self.html, r"function\s+extractMathRegions\s*\(")
        self.assertRegex(self.html, r"function\s+restoreMathRegions\s*\(")
        self.assertIn("NodeFilter.SHOW_TEXT", self.html)
        self.assertIn("MATHREGION_${regions.length}_END", self.html)
        self.assertIn("replaceAll(region.token, () => region.source)", self.html)
        self.assertIn("extractMathRegions(rewriteWikilinks(body))", self.html)
        self.assertLess(self.html.index("marked.parse(math.markdown"), sanitize_at)
        self.assertLess(sanitize_at, self.html.index("restoreMathRegions(elements.content, math.regions)"))
        self.assertNotIn("@@KATEX_", self.html)
        self.assertIn("throwOnError: false", self.html)
        self.assertIn("trust: false", self.html)
        self.assertIn("strict: 'warn'", self.html)

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

    def test_successful_render_reports_active_file_to_workbench(self):
        self.assertRegex(self.html, r"function\s+notifyActiveFile\s*\(")
        self.assertIn("window.parent.postMessage", self.html)
        self.assertIn("kb-context", self.html)
        self.assertIn("kb-open-navigation", self.html)
        self.assertIn("kb-refresh", self.html)
        self.assertIn("retryIndexLoad(activeSection)", self.html)
        self.assertIn("http://127.0.0.1:18080", self.html)
        self.assertLess(self.html.index("await mermaid.run"), self.html.rindex("notifyActiveFile(file, pageTitle, pageMetadata)"))

    def test_uses_only_local_browser_dependencies(self):
        self.assertNotIn("cdn.jsdelivr.net", self.html)
        self.assertNotIn("cdnjs.cloudflare.com", self.html)
        for asset in (
            "vendor/marked/marked.min.js",
            "vendor/dompurify/purify.min.js",
            "vendor/katex/katex.min.css",
            "vendor/mermaid/mermaid.min.js",
        ):
            with self.subTest(asset=asset):
                self.assertIn(asset, self.html)

    def test_sidebar_search_and_persisted_expansion_are_implemented(self):
        for value in ('id="navigationSearch"', 'aria-label="搜索知识页"', 'id="collapseAll"'):
            with self.subTest(value=value):
                self.assertIn(value, self.html)
        for function in (
            "filterNavigation",
            "saveNavigationState",
            "restoreNavigationState",
            "retryIndexLoad",
        ):
            with self.subTest(function=function):
                self.assertRegex(self.html, rf"function\s+{function}\s*\(")
        self.assertIn("radar-viewer-navigation-v1", self.html)
        self.assertIn("event.key === '/'", self.html)
        self.assertIn("event.key.toLowerCase() === 'k'", self.html)

    def test_reports_structured_page_context(self):
        self.assertIn("kb-context", self.html)
        self.assertIn("kind: 'page'", self.html)
        self.assertIn("title:", self.html)

    def test_primary_sections_are_accessible_compact_tabs(self):
        self.assertIn('role="tablist"', self.html)
        self.assertIn('role="tab"', self.html)
        self.assertIn('data-section="knowledge"', self.html)
        self.assertIn('data-section="interview"', self.html)
        self.assertIn('>知识库<', self.html)
        self.assertIn('>工程面试<', self.html)
        self.assertIn("activeSection", self.html)
        self.assertRegex(self.html, r"\.section-tabs\s*\{[^}]*height:\s*36px")

    def test_sections_load_separate_indexes_and_persist_separate_state(self):
        self.assertIn("knowledge: { indexUrl: '_index.md'", self.html)
        self.assertIn("interview: { indexUrl: '_interview_index.md'", self.html)
        self.assertIn("radar-viewer-navigation-knowledge-v1", self.html)
        self.assertIn("radar-viewer-navigation-interview-v1", self.html)
        self.assertIn("radar-viewer-active-file-knowledge-v1", self.html)
        self.assertIn("radar-viewer-active-file-interview-v1", self.html)
        self.assertIn("search:", self.html)
        self.assertIn("filters:", self.html)

    def test_interview_navigation_parses_metadata_and_exposes_filters(self):
        self.assertRegex(self.html, r"function\s+parseInterviewIndex\s*\(")
        for field in ("question", "summary", "tags", "roles", "difficulty"):
            with self.subTest(field=field):
                self.assertIn(field, self.html)
        for element_id in ("roleFilter", "difficultyFilter", "tagFilter"):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn('aria-label="岗位筛选"', self.html)
        self.assertIn('aria-label="难度筛选"', self.html)
        self.assertIn('aria-label="知识方向筛选"', self.html)

    def test_cross_zone_links_deep_links_and_graph_profile_are_section_aware(self):
        self.assertRegex(self.html, r"function\s+sectionForFile\s*\(")
        self.assertRegex(self.html, r"function\s+switchSection\s*\(")
        self.assertIn("page_type", self.html)
        self.assertIn("pageType", self.html)
        self.assertIn("graph-view.html?profile=${activeSection}", self.html)
        self.assertIn("data-section", self.html)

    def test_taxonomy_summary_fetches_profile_data_and_renders_safe_status(self):
        for value in ('id="taxonomySummary"', 'taxonomy.stats', 'taxonomy.lastRun', 'seedCategories', 'automaticCategories', 'candidates'):
            with self.subTest(value=value):
                self.assertIn(value, self.html)
        self.assertIn("graph-view.html?profile=${activeSection}&mode=taxonomy", self.html)
        self.assertRegex(self.html, r"graph-data\.json")
        self.assertRegex(self.html, r"interview-graph-data\.json")
        self.assertRegex(self.html, r"function\s+refreshTaxonomySummary\s*\(")
        self.assertIn("let taxonomyRefreshGeneration = 0", self.html)
        self.assertIn("const refreshToken = ++taxonomyRefreshGeneration", self.html)
        self.assertGreaterEqual(self.html.count("refreshToken !== taxonomyRefreshGeneration || activeSection !== section"), 2)
        self.assertIn("动态分类状态不可用", self.html)
        self.assertNotIn("taxonomySummary.innerHTML", self.html)

    def test_taxonomy_summary_supports_new_and_legacy_payload_fallbacks(self):
        for value in (
            "taxonomy.candidates", "publish.candidates", "taxonomy.lastRun", "publish.lastRun",
            "category.source === 'seed'", "category.source === 'automatic'", "category?.status === 'forming'",
            "stats?.activeCategories", "categories.length", "stats?.forming",
        ):
            with self.subTest(value=value):
                self.assertIn(value, self.html)
        self.assertIn("countValue(taxonomy.candidates) ?? countValue(publish.candidates)", self.html)
        self.assertIn("taxonomy.lastRun && typeof taxonomy.lastRun === 'object' ? taxonomy.lastRun : publish.lastRun", self.html)

    def test_interview_context_is_typed_and_refresh_preserves_section(self):
        self.assertIn("pageType: 'interview'", self.html)
        self.assertIn("question:", self.html)
        self.assertIn("roles:", self.html)
        self.assertIn("difficulty:", self.html)
        self.assertIn("retryIndexLoad(activeSection)", self.html)
        self.assertIn("return navigateTo(navigationStates[section].activeFile", self.html)

    def test_interview_section_without_file_does_not_fall_back_to_home(self):
        self.assertIn("requestedSection === 'interview' ? null : DEFAULT_FILE", self.html)
        self.assertIn("resolveSectionFile", self.html)
        self.assertIn("navigationState.entries[0]?.file || null", self.html)

    def test_tabs_have_panel_relationships_and_keyboard_activation(self):
        self.assertIn('id="primarySections"', self.html)
        self.assertIn('aria-controls="viewerPanel"', self.html)
        self.assertIn('id="viewerPanel"', self.html)
        self.assertIn('role="tabpanel"', self.html)
        self.assertIn('aria-labelledby="knowledgeTab"', self.html)
        self.assertIn("tab.tabIndex = selected ? 0 : -1", self.html)
        for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
            self.assertIn(key, self.html)
        self.assertRegex(self.html, r"function\s+handleSectionTabKeydown\s*\(")

    def test_metadata_detection_canonicalizes_cross_zone_history(self):
        self.assertIn("history.replaceState({ file, section: detectedSection }", self.html)
        self.assertIn("canonicalViewerUrl(file, detectedSection)", self.html)
        self.assertLess(self.html.index("const detectedSection = sectionForFile"), self.html.index("history.replaceState({ file, section: detectedSection }"))

    def test_retry_handler_does_not_forward_mouse_event_as_section(self):
        self.assertIn("const failedIntent = { requestedFile, sectionHint: hintedSection, historyMode }", self.html)
        self.assertIn("retry.addEventListener('click', () => navigateTo(failedIntent.requestedFile, failedIntent))", self.html)
        self.assertNotIn("retry.addEventListener('click', () => retryIndexLoad(activeSection))", self.html)
        self.assertNotIn("retry.addEventListener('click', retryIndexLoad)", self.html)

    def test_navigation_has_one_generation_owned_async_path(self):
        self.assertIn("let navigationGeneration = 0", self.html)
        self.assertRegex(self.html, r"async function\s+navigateTo\s*\(")
        self.assertIn("const token = ++navigationGeneration", self.html)
        self.assertIn("if (token !== navigationGeneration) return", self.html)
        self.assertIn("await fetchIndexData", self.html)
        self.assertIn("await fetchPageData", self.html)
        self.assertNotIn("switchSection(section, { render: false });\n      renderMarkdown", self.html)
        self.assertIn("navigateTo(file, { sectionHint: section, historyMode: 'push' })", self.html)


if __name__ == "__main__":
    unittest.main()
