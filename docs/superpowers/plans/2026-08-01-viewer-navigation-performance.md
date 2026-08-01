# Viewer Navigation Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make desktop Viewer page switches immediate by removing maintenance work from ordinary reads, caching parsed section indexes, and rendering articles before optional quality or taxonomy enrichment.

**Architecture:** Generated indexes and graph JSON become static read artifacts; only explicit refresh endpoints run taxonomy and generators. The Viewer keeps one parsed-index cache per section, preserves last-intent-wins navigation, renders fetched Markdown immediately, and updates page quality and taxonomy summary asynchronously with generation guards.

**Tech Stack:** Python 3 `ThreadingHTTPServer`, vanilla HTML/CSS/JavaScript, Marked, DOMPurify, KaTeX, Highlight.js, Mermaid, Python `unittest`, Playwright.

---

## File Map

- Modify `scripts/serve_kb.py`: separate static artifact reads from explicit maintenance operations.
- Modify `tests/test_serve_kb.py`: prove static reads and catalog reads never invoke refresh while explicit refresh retains rebuild behavior.
- Modify `viewer.html`: add section-index caching, immediate loading feedback, cache invalidation, progressive enrichment, and conditional render work.
- Modify `tests/test_viewer_contract.py`: lock the new navigation, enrichment, and conditional-render contracts.
- Modify `tests/desktop_experience.spec.cjs`: exercise slow enrichment, request counts, rapid navigation, cache invalidation, and performance budgets.

No production file is created. Do not modify graph rendering, Claude UI, mobile layout, taxonomy algorithms, page content, or generated index/graph artifacts in feature commits.

### Task 1: Make Generated Artifacts Pure Read Endpoints

**Files:**
- Modify: `tests/test_serve_kb.py`
- Modify: `scripts/serve_kb.py:501-536`

- [ ] **Step 1: Replace the stale static-artifact test with failing no-refresh contracts**

In `KnowledgeServerTests`, replace `test_interview_static_artifacts_trigger_refresh` and add a catalog test:

```python
    def test_generated_artifact_gets_do_not_run_refresh(self):
        self.builder.refresh(force=True)
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("read triggered refresh")):
            for path in (
                "/_index.md", "/_interview_index.md",
                "/graph-data.json", "/interview-graph-data.json",
            ):
                with self.subTest(path=path):
                    with urlopen(self.base + path, timeout=5) as response:
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_catalog_reads_current_graphs_without_running_refresh(self):
        self.builder.refresh(force=True)
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("catalog triggered refresh")):
            response, payload = self.request_json("/api/catalog")
        self.assertEqual(response.status, 200)
        self.assertEqual(
            [(entry["section"], entry["file"]) for entry in payload["entries"]],
            [],
        )
        self.assertEqual(payload["edges"], [])
```

The fixture graph nodes are empty, so an empty combined catalog is the exact expected payload.

- [ ] **Step 2: Run the server tests and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_serve_kb.KnowledgeServerTests.test_generated_artifact_gets_do_not_run_refresh \
  tests.test_serve_kb.KnowledgeServerTests.test_catalog_reads_current_graphs_without_running_refresh -v
```

Expected: both tests fail with `read triggered refresh` or `catalog triggered refresh` because `do_GET()` currently calls `refresh_payload(force=False)`.

- [ ] **Step 3: Remove refresh calls from GET handlers**

In `KnowledgeRequestHandler.do_GET()`, replace only the `/api/catalog` and `/api/revision` branches with the following code. Leave the complete `/api/taxonomy/status` branch unchanged, and delete the later generated-path branch that calls `refresh_payload(force=False)` for indexes and graph JSON:

```python
    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/catalog":
            try:
                knowledge = json.loads(
                    (self.builder.root / "graph-data.json").read_text(encoding="utf-8")
                )
                interview = json.loads(
                    (self.builder.root / "interview-graph-data.json").read_text(encoding="utf-8")
                )
                self.send_json(200, catalog_payload(knowledge, interview))
            except (OSError, json.JSONDecodeError) as error:
                self.send_json(500, {"ok": False, "error": f"catalog unavailable: {error}"})
            return
        if path == "/api/revision":
            try:
                payload = {"ok": True, "revision": self.builder.revision(), "rebuilt": False}
            except RefreshError as error:
                self.send_json(500, {"ok": False, "error": str(error)})
                return
            self.send_json(200, payload)
            return
```

Do not retain the generated-path `refresh_payload()` branch. Do not change `POST /api/refresh` or `POST /api/taxonomy/rebuild`.

- [ ] **Step 4: Update the revision endpoint expectation**

Rename `test_refresh_and_revision_endpoints_rebuild_and_set_localhost_cors` to `test_explicit_refresh_rebuilds_and_revision_is_read_only`. Keep its current assertions and wrap the revision request to prove it does not invoke maintenance:

```python
        response, refreshed = self.request_json("/api/refresh", method="POST")
        with mock.patch.object(self.builder, "refresh", side_effect=AssertionError("revision triggered refresh")):
            _, revision = self.request_json("/api/revision")
```

- [ ] **Step 5: Run the server suite and verify GREEN**

Run: `python3 -m unittest tests.test_serve_kb -v`

Expected: all server and builder tests pass. Builder-level periodic-refresh tests remain valid because explicit callers may still use `KnowledgeBuilder.refresh()`; ordinary GET handlers no longer call it.

- [ ] **Step 6: Commit the server read-path change**

```bash
git add -- scripts/serve_kb.py tests/test_serve_kb.py
git diff --cached --check
git commit -m "perf: keep knowledge reads off refresh lock"
```

### Task 2: Cache Section Indexes And Expose Immediate Navigation Feedback

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html:90-100,180-205,425-438,657-850`

- [ ] **Step 1: Add failing Viewer cache and loading-state contracts**

Add these tests to `ViewerContractTests`:

```python
    def test_section_indexes_are_cached_and_invalidatable(self):
        for value in (
            "indexData: null", "indexPromise: null", "loadSectionIndex",
            "invalidateSectionIndexes", "state.indexData", "state.indexPromise",
        ):
            self.assertIn(value, self.html)
        self.assertNotIn("let parsed = await fetchIndexData(hintedSection)", self.html)

    def test_navigation_exposes_busy_state_without_clearing_article(self):
        self.assertIn("function setNavigationBusy", self.html)
        self.assertIn("elements.content.setAttribute('aria-busy', String(busy))", self.html)
        self.assertIn("setMessage(`正在打开${title ? `「${title}」` : '页面'}`)", self.html)
        self.assertNotIn("elements.content.replaceChildren();\n      setMessage('正在", self.html)

    def test_successful_refresh_invalidates_indexes_before_recovery(self):
        self.assertIn("invalidateSectionIndexes()", self.html)
        self.assertIn("refreshActiveSurface(activeSection)", self.html)
```

- [ ] **Step 2: Run focused contracts and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_viewer_contract.ViewerContractTests.test_section_indexes_are_cached_and_invalidatable \
  tests.test_viewer_contract.ViewerContractTests.test_navigation_exposes_busy_state_without_clearing_article \
  tests.test_viewer_contract.ViewerContractTests.test_successful_refresh_invalidates_indexes_before_recovery -v
```

Expected: all three tests fail because the Viewer has no parsed-index cache, busy helper, or explicit invalidation path.

- [ ] **Step 3: Add cache state and a coalescing loader**

Extend each `navigationStates` entry:

```javascript
      groups: [], entries: [], activeFile: SECTIONS[section].defaultFile,
      expanded: new Set(), initialized: false, indexData: null, indexPromise: null,
      search: '', filters: { role: '', difficulty: '', tag: '' }
```

Replace direct index fetching with:

```javascript
    async function loadSectionIndex(section, { force = false } = {}) {
      const state = navigationStates[section];
      if (force) {
        state.indexData = null;
        state.indexPromise = null;
      }
      if (state.indexData) return state.indexData;
      if (!state.indexPromise) {
        state.indexPromise = fetchIndexData(section)
          .then((parsed) => {
            state.indexData = parsed;
            return parsed;
          })
          .finally(() => { state.indexPromise = null; });
      }
      return state.indexPromise;
    }

    function invalidateSectionIndexes() {
      for (const state of Object.values(navigationStates)) {
        state.indexData = null;
        state.indexPromise = null;
        state.initialized = false;
      }
    }
```

Use `await loadSectionIndex(hintedSection)` in `navigateTo()`. If metadata detects another section, use `await loadSectionIndex(detectedSection)`.

- [ ] **Step 4: Add non-destructive navigation feedback**

Add CSS:

```css
    article[aria-busy="true"] { opacity: .72; transition: opacity 120ms ease; }
```

Add the helper:

```javascript
    function setNavigationBusy(busy, title = '') {
      elements.content.setAttribute('aria-busy', String(busy));
      if (busy) setMessage(`正在打开${title ? `「${title}」` : '页面'}`);
      else if (!elements.message.classList.contains('error')) setMessage('');
    }
```

At the start of `navigateTo()`, resolve the requested title from cached entries when available and call `setNavigationBusy(true, title)`. Clear busy only when the current token succeeds or fails. Token-stale requests must not clear a newer request's busy state.

- [ ] **Step 5: Separate explicit refresh recovery from ordinary retry**

Add:

```javascript
    async function refreshActiveSurface(section = activeSection) {
      invalidateSectionIndexes();
      catalogPromise = null;
      await loadSectionIndex(section, { force: true });
      return navigateTo(navigationStates[section].activeFile, {
        sectionHint: section,
        historyMode: 'replace',
      });
    }
```

Keep `retryIndexLoad()` for navigation failures. Change only the `kb-refresh` message handler to:

```javascript
      if (event.data?.type === 'kb-refresh') {
        refreshActiveSurface(activeSection)
          .then((ok) => notifyRefreshResult(ok, ok ? '' : '当前页面恢复失败'));
      }
```

- [ ] **Step 6: Run Viewer contracts and commit**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: all Viewer contracts pass. Update older string-based assertions that explicitly require `await fetchIndexData` or `retryIndexLoad(activeSection)` so they assert the new named loader and refresh-recovery path instead; do not weaken generation-token assertions.

Commit:

```bash
git add -- viewer.html tests/test_viewer_contract.py
git diff --cached --check
git commit -m "perf: cache viewer section indexes"
```

### Task 3: Render Articles Before Quality And Taxonomy Enrichment

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html:205-275,425-455,525-595,687-760`

- [ ] **Step 1: Add failing progressive-enrichment contracts**

Add:

```python
    def test_article_render_does_not_await_page_quality(self):
        insert_at = self.html.index("elements.content.innerHTML = DOMPurify.sanitize")
        quality_at = self.html.index("void renderPageQuality")
        self.assertLess(insert_at, quality_at)
        self.assertNotIn("await renderPageQuality(pageMetadata, body, file, metadata)", self.html)

    def test_enrichment_is_generation_and_identity_guarded(self):
        for value in (
            "let enrichmentGeneration = 0", "const enrichmentToken = ++enrichmentGeneration",
            "file !== navigationState.activeFile", "section !== activeSection",
            "void refreshTaxonomySummary(section, enrichmentToken, file)",
        ):
            self.assertIn(value, self.html)

    def test_quality_has_local_fallback_while_catalog_is_unavailable(self):
        self.assertIn("renderPageQuality(\n          pageMetadata, body, file, metadata, enrichmentToken, section\n        )", self.html)
        self.assertIn("catalog = null", self.html)
        self.assertIn("'未检测到'", self.html)
```

- [ ] **Step 2: Run focused contracts and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_viewer_contract.ViewerContractTests.test_article_render_does_not_await_page_quality \
  tests.test_viewer_contract.ViewerContractTests.test_enrichment_is_generation_and_identity_guarded \
  tests.test_viewer_contract.ViewerContractTests.test_quality_has_local_fallback_while_catalog_is_unavailable -v
```

Expected: failures because `renderPageData()` currently awaits quality before Markdown insertion and taxonomy refresh has only a section-level token.

- [ ] **Step 3: Split primary render from enrichment**

Introduce `let enrichmentGeneration = 0`. Remove `await renderPageQuality(pageMetadata, body, file, metadata)` from the start of `renderPageData(file, section, page, token)`. After the article is rendered, history/title are committed, and the busy state is cleared, start enrichment:

```javascript
        const enrichmentToken = ++enrichmentGeneration;
        void renderPageQuality(
          pageMetadata, body, file, metadata, enrichmentToken, section
        );
        void refreshTaxonomySummary(section, enrichmentToken, file);
```

Move `refreshTaxonomySummary(section)` out of `commitSection()` so every navigation has one explicitly guarded enrichment launch.

- [ ] **Step 4: Guard quality and taxonomy DOM writes**

Change quality to accept identity:

```javascript
    async function renderPageQuality(metadata, body, file, rawMetadata, token, section) {
      elements.qualitySummary.textContent = '读取中';
      let catalog = null;
      try { catalog = await loadCatalog(); } catch {}
      if (token !== enrichmentGeneration || file !== navigationState.activeFile || section !== activeSection) return;
      const quality = objectivePageQuality(metadata, body, file, catalog, rawMetadata);
      elements.qualitySummary.textContent = quality.complete ? '基础字段完整' : '存在未检测字段';
      elements.qualityFacts.replaceChildren();
      for (const [label, value] of [['摘要', quality.summary], ['来源', quality.source], ['信度', quality.confidence], ['标签', quality.tags], ['引用', quality.links], ['断链', quality.broken], ['健康状态', quality.health], ['结构', quality.structure]]) {
        const term = document.createElement('dt');
        const detail = document.createElement('dd');
        term.textContent = label;
        detail.textContent = value;
        elements.qualityFacts.append(term, detail);
      }
      elements.qualityPanel.hidden = false;
    }
```

Change taxonomy summary to accept `(section, token, file)`. Before every success or failure DOM write, require:

```javascript
      if (token !== enrichmentGeneration || section !== activeSection || file !== navigationState.activeFile) return;
```

Remove `taxonomyRefreshGeneration`; the single enrichment generation owns quality and taxonomy for the active page.

- [ ] **Step 5: Run Viewer contracts and commit**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: all tests pass and no contract requires article rendering to await catalog.

Commit:

```bash
git add -- viewer.html tests/test_viewer_contract.py
git diff --cached --check
git commit -m "perf: render articles before enrichment"
```

### Task 4: Skip Unneeded Per-Page Renderers

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html:687-755`

- [ ] **Step 1: Add failing conditional-render contracts**

Add:

```python
    def test_expensive_renderers_run_only_when_content_requires_them(self):
        self.assertIn("if (math.regions.length)", self.html)
        self.assertIn("const codeBlocks = elements.content.querySelectorAll", self.html)
        self.assertIn("if (mermaidBlocks.length)", self.html)
        self.assertIn("await renderMermaidDiagrams(elements.content)", self.html)
```

- [ ] **Step 2: Run the focused contract and verify RED**

Run:

```bash
python3 -m unittest \
  tests.test_viewer_contract.ViewerContractTests.test_expensive_renderers_run_only_when_content_requires_them -v
```

Expected: failure because KaTeX and Mermaid helpers currently run for every page.

- [ ] **Step 3: Add exact content guards**

Use the already extracted math regions:

```javascript
        if (math.regions.length) {
          restoreMathRegions(elements.content, math.regions);
          renderMathInElement(elements.content, {
            delimiters: [
              { left: '$$', right: '$$', display: true },
              { left: '$', right: '$', display: false },
              { left: '\\(', right: '\\)', display: false },
              { left: '\\[', right: '\\]', display: true },
            ],
            throwOnError: false,
            trust: false,
            strict: 'warn',
          });
        }
```

Preserve math restoration correctness: when regions exist, restoration must still precede KaTeX. Then guard code and Mermaid work:

```javascript
        const codeBlocks = elements.content.querySelectorAll('pre code:not(.language-mermaid)');
        codeBlocks.forEach((block) => hljs.highlightElement(block));
        const mermaidBlocks = elements.content.querySelectorAll('pre code.language-mermaid');
        if (mermaidBlocks.length) {
          mermaidBlocks.forEach((block) => {
            const container = document.createElement('div');
            container.className = 'mermaid';
            container.textContent = block.textContent;
            block.parentElement.replaceWith(container);
          });
          await renderMermaidDiagrams(elements.content);
        }
```

- [ ] **Step 4: Run rendering regressions and commit**

Run:

```bash
python3 -m unittest tests.test_viewer_contract -v
KB_URL=http://127.0.0.1:18081 npx playwright test \
  tests/desktop_experience.spec.cjs \
  -g "complex knowledge pages|invalid Mermaid|interview body hierarchy" \
  --workers=1 --config tests/playwright.config.cjs
```

Expected: contracts pass; KaTeX remains visible, Mermaid renders, and invalid Mermaid remains isolated.

Commit:

```bash
git add -- viewer.html tests/test_viewer_contract.py
git diff --cached --check
git commit -m "perf: skip unused article renderers"
```

### Task 5: Add Browser Navigation And Performance Regressions

**Files:**
- Modify: `tests/desktop_experience.spec.cjs`
- Modify if browser evidence requires a scoped correction: `viewer.html`

- [ ] **Step 1: Add a reusable measured-navigation helper**

Near the top of the Playwright file, add:

```javascript
async function measuredNavigate(page, file, section) {
  return page.evaluate(async ({ file, section }) => {
    const started = performance.now();
    const ok = await navigateTo(file, { sectionHint: section, historyMode: 'push' });
    return { ok, elapsed: performance.now() - started };
  }, { file, section });
}
```

- [ ] **Step 2: Add a failing slow-enrichment test**

```javascript
test('slow enrichment never blocks article navigation', async ({ page }) => {
  await page.route('**/api/catalog', route => new Promise(resolve => {
    setTimeout(() => resolve(route.fulfill({ status: 200, contentType: 'application/json', body: '{"entries":[],"edges":[]}' })), 1500);
  }));
  await page.route('**/graph-data.json', route => new Promise(resolve => {
    setTimeout(() => resolve(route.fulfill({ status: 200, contentType: 'application/json', body: '{"taxonomy":{"categories":[],"stats":{}}}' })), 1500);
  }));
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');
  const result = await measuredNavigate(page, 'pages/词嵌入 Word Embedding.md', 'knowledge');
  expect(result.ok).toBe(true);
  expect(result.elapsed).toBeLessThan(300);
  await expect(page.locator('#content h1')).toContainText('词嵌入');
});
```

Run this test before implementation integration and verify it fails under the old blocking quality path or exceeds the budget.

- [ ] **Step 3: Add request-count and cross-section budgets**

Add a test that counts only index responses after initial load:

```javascript
test('navigation reuses one index per section and meets desktop budgets', async ({ page }) => {
  const counts = { knowledge: 0, interview: 0 };
  page.on('request', request => {
    const pathname = new URL(request.url()).pathname;
    if (pathname === '/_index.md') counts.knowledge += 1;
    if (pathname === '/_interview_index.md') counts.interview += 1;
  });
  await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FK%E8%BF%91%E9%82%BB%20KNN%20K-Nearest%20Neighbors.md`);
  await expect(page.locator('#content h1')).toContainText('K近邻');
  const same = await measuredNavigate(page, 'pages/词嵌入 Word Embedding.md', 'knowledge');
  const cross = await measuredNavigate(page, 'pages/多头注意力机制的核心作用是什么.md', 'interview');
  const interviewAgain = await measuredNavigate(page, 'pages/知识图谱的存储方式与索引优化.md', 'interview');
  expect(same.elapsed).toBeLessThan(300);
  expect(cross.elapsed).toBeLessThan(500);
  expect(interviewAgain.elapsed).toBeLessThan(300);
  expect(counts).toEqual({ knowledge: 1, interview: 1 });
});
```

- [ ] **Step 4: Add rapid-click and loading-feedback coverage**

Route the first target page with a 250 ms delay and the second without delay. Trigger two `navigateTo()` calls without awaiting the first. Assert within 100 ms that `#content[aria-busy="true"]` and the status are visible, then assert the final title is the second target and never changes back after the first response completes.

Use these exact final assertions:

```javascript
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'true', { timeout: 100 });
  await expect(page.locator('#message')).toContainText('正在打开');
  await expect(page.locator('#content h1')).toContainText('词嵌入');
  await page.waitForTimeout(300);
  await expect(page.locator('#content h1')).toContainText('词嵌入');
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
```

- [ ] **Step 5: Add explicit-refresh invalidation coverage**

Start from a loaded knowledge page, count `_index.md`, then dispatch the trusted refresh message from the parent workbench or call `refreshActiveSurface('knowledge')` in the standalone fixture. Assert one additional `_index.md` request and that the active article becomes readable again. Do not call `/api/refresh` from this test; it verifies the Viewer recovery half after the workbench has already completed server refresh.

- [ ] **Step 6: Run the performance group on a clean server**

Start a dedicated server on an unused port:

```bash
python3 scripts/serve_kb.py --host 127.0.0.1 --port 18086 --directory /home/u2023312337/知识库
```

In another shell run:

```bash
KB_URL=http://127.0.0.1:18086 npx playwright test \
  tests/desktop_experience.spec.cjs \
  -g "slow enrichment|navigation reuses|rapid navigation|refresh invalidates" \
  --workers=1 --config tests/playwright.config.cjs
```

Expected: all new tests pass; failure messages expose measured durations. Stop the dedicated server after the run.

- [ ] **Step 7: Make only evidence-driven scoped corrections**

If a budget fails, inspect the recorded request count and measured stage before editing. Permitted corrections are limited to `viewer.html` cache, busy-state, enrichment guards, or renderer guards. Do not loosen 100/300/500 ms thresholds and do not add arbitrary sleeps.

- [ ] **Step 8: Commit browser coverage and final corrections**

```bash
git add -- tests/desktop_experience.spec.cjs viewer.html
git diff --cached --check
git diff --cached --name-only
git commit -m "test: enforce viewer navigation budgets"
```

The staged file list must contain only the two paths above; if `viewer.html` required no final correction, stage only the Playwright test.

### Task 6: Full Verification And Operational Check

**Files:**
- Verification only; do not commit generated artifacts from this task.

- [ ] **Step 1: Run all Python tests**

Run: `python3 -m unittest discover -s tests -q`

Expected: all tests pass with zero failures.

- [ ] **Step 2: Run the full desktop browser suites with project config**

Use a clean dedicated knowledge server and the existing workbench service:

```bash
KB_URL=http://127.0.0.1:18086 npx playwright test \
  tests/desktop_experience.spec.cjs \
  tests/web_workbench.spec.cjs \
  tests/taxonomy_observability.spec.cjs \
  --workers=1 --config tests/playwright.config.cjs
```

Expected: all browser tests pass. Use `KB_VIEWER_URL=http://127.0.0.1:18086` as well if a test references that variable; do not silently fall back to a stale long-running server.

- [ ] **Step 3: Verify static read latency and no maintenance side effects**

Against the clean server, run:

```bash
curl -sS -o /dev/null -w 'index start=%{time_starttransfer}s total=%{time_total}s\n' http://127.0.0.1:18086/_index.md
curl -sS -o /dev/null -w 'catalog start=%{time_starttransfer}s total=%{time_total}s\n' http://127.0.0.1:18086/api/catalog
```

Expected: both return in well under 0.3 seconds and server logs contain no taxonomy, index-generation, or graph-generation operation for these GETs.

- [ ] **Step 4: Run repository generators and health checks explicitly**

```bash
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: `ERROR 0`, `WARN 0`, and no broken links. These commands may update generated artifacts in the working tree; do not stage them unless their semantic content changed because of an in-scope source change, which this plan does not make.

- [ ] **Step 5: Review final diff and runtime behavior**

Run:

```bash
git diff --check
git status --short
git log --oneline -6
```

Confirm that feature commits touch only `scripts/serve_kb.py`, `viewer.html`, and their three test files. Confirm the long-running `18081` service is restarted after merge so it runs the new GET behavior; otherwise the old in-memory handler continues serving the blocking implementation.

- [ ] **Step 6: Finish the branch**

Use `superpowers:verification-before-completion`, then `superpowers:finishing-a-development-branch`. Present the four integration choices and do not remove the worktree before a successful merge or explicit discard confirmation.
