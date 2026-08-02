# Viewer Page Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add page-scoped controls that copy or download the active article as exact source Markdown, body-only Markdown, rendered rich text, original `.md`, or self-contained `.html`.

**Architecture:** Keep export inside `viewer.html`. Commit one immutable export snapshot only after a current-generation render succeeds, and have every command read that snapshot at activation time. Build clipboard HTML and standalone HTML from one sanitized article-clone helper; embed required assets for HTML download and abort instead of emitting a partial document.

**Tech Stack:** Vanilla HTML/CSS/JavaScript, DOMPurify, Marked, KaTeX, Mermaid, Python `unittest`, Playwright.

---

## File Map

- Modify: `viewer.html` — snapshot, title actions, menus, clipboard formats, downloads, self-contained HTML, status feedback.
- Modify: `tests/test_viewer_contract.py` — source-level contracts for state, security, accessibility, and filename behavior.
- Modify: `tests/desktop_experience.spec.cjs` — end-to-end clipboard, download, navigation, layout, error, and performance regressions.
- Reference only: `vendor/katex/katex.min.css`, `vendor/katex/fonts/*` — fetched and embedded during HTML export.

### Task 1: Retain An Immutable Active Export Snapshot

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html`

- [ ] **Step 1: Write the failing contract test**

Add to `ViewerContractTests`:

```python
def test_export_snapshot_retains_exact_source_and_is_generation_owned(self):
    for value in (
        "let activeExportSnapshot = null",
        "return { source, metadata, body, pageMetadata: parseMetadata(metadata) }",
        "Object.freeze({ token, file, section, title: pageTitle, source: page.source, body: page.body })",
        "activeExportSnapshot = snapshot",
        "closeExportMenus()",
    ):
        self.assertIn(value, self.html)
    commit_at = self.html.index("activeExportSnapshot = snapshot")
    guard_at = self.html.rfind("if (token !== navigationGeneration) return", 0, commit_at)
    self.assertGreater(guard_at, self.html.index("async function renderPageData"))
```

- [ ] **Step 2: Run RED**

Run: `python3 -m unittest tests.test_viewer_contract.ViewerContractTests.test_export_snapshot_retains_exact_source_and_is_generation_owned -v`

Expected: `FAIL` because exact `source` and snapshot state are absent.

- [ ] **Step 3: Implement exact source retention and generation-owned commit**

Add state beside the existing generation counters:

```js
let activeExportSnapshot = null;
let openExportMenu = null;
```

Replace `fetchPageData()` with:

```js
async function fetchPageData(file) {
  const response = await fetch(file, { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const source = await response.text();
  const { metadata, body } = splitFrontmatter(source);
  return { source, metadata, body, pageMetadata: parseMetadata(metadata) };
}
```

Add an initial menu closer, which Task 2 expands:

```js
function closeExportMenus() {
  openExportMenu?.setAttribute('hidden', '');
  openExportMenu = null;
}
```

Immediately after `const token = ++navigationGeneration;` in `navigateTo()`, call `closeExportMenus();`. In the no-page branch set `activeExportSnapshot = null` before clearing `elements.content`. Do not clear it in the catch branch because failed navigation preserves the readable article.

At the final generation guard in `renderPageData()`, commit:

```js
const pageTitle = elements.content.querySelector('h1')?.textContent?.trim()
  || file.split('/').pop().replace(/\.md$/, '');
const snapshot = Object.freeze({
  token, file, section, title: pageTitle, source: page.source, body: page.body,
});
if (token !== navigationGeneration) return;
document.title = `${pageTitle} · 技术雷达`;
activeExportSnapshot = snapshot;
setMessage('');
updateActiveNavigation(file);
notifyActiveFile(file, pageTitle, pageMetadata);
```

- [ ] **Step 4: Run GREEN and commit**

Run: `python3 -m unittest tests.test_viewer_contract.ViewerContractTests.test_export_snapshot_retains_exact_source_and_is_generation_owned tests.test_viewer_contract.ViewerContractTests.test_navigation_has_one_generation_owned_async_path tests.test_viewer_contract.ViewerContractTests.test_navigation_exposes_busy_state_without_clearing_article -v`

Expected: `Ran 3 tests` and `OK`.

Commit:

```bash
git add viewer.html tests/test_viewer_contract.py
git commit -m "feat: retain active viewer export source"
```

### Task 2: Add Responsive Accessible Menus Beside The Article Title

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing menu contracts**

Add a Python test asserting `mountExportActions`, `aria-label="复制当前页面"`, `aria-label="下载当前页面"`, the five exact `data-export-command` values (`copy-source`, `copy-body`, `copy-rich`, `download-markdown`, `download-html`), Escape handling, and `['ArrowDown', 'ArrowUp', 'Home', 'End']` navigation.

Add this Playwright test body under the name `viewer export menus are accessible and a long title does not overlap actions`:

```js
await page.route('**/pages/LongExportTitle.md', route => route.fulfill({
  status: 200, contentType: 'text/markdown; charset=utf-8',
  body: '# 这是一个用于验证标题换行且不会遮挡复制和下载按钮的非常长的知识页面标题\n\n正文。',
}));
await page.goto(`${knowledgeUrl}/viewer.html?f=pages%2FLongExportTitle.md`);
const copy = page.getByRole('button', { name: '复制当前页面' });
const download = page.getByRole('button', { name: '下载当前页面' });
await copy.click();
await expect(page.getByRole('menuitem', { name: '原始 Markdown' })).toBeFocused();
await page.keyboard.press('End');
await expect(page.getByRole('menuitem', { name: '渲染后的富文本' })).toBeFocused();
await page.keyboard.press('Escape');
await expect(copy).toBeFocused();
const [titleBox, copyBox, downloadBox] = await Promise.all([
  page.locator('.article-title').boundingBox(), copy.boundingBox(), download.boundingBox(),
]);
expect(titleBox.x + titleBox.width).toBeLessThanOrEqual(copyBox.x);
expect(copyBox.x + copyBox.width).toBeLessThanOrEqual(downloadBox.x);
expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
```

- [ ] **Step 2: Run RED**

Run the new Python test and:

`npx playwright test tests/desktop_experience.spec.cjs --config tests/playwright.config.cjs --reporter=line -g "viewer export menus are accessible"`

Expected: failures because the action group is absent.

- [ ] **Step 3: Implement styles and menu behavior**

Add `.article-header` as a flex row with `gap:16px`; `.article-title` as `flex:1 1 auto;min-width:0;overflow-wrap:anywhere`; `.export-actions` as a fixed-size flex group; 36px icon triggers; absolute right-aligned menus; `[hidden]{display:none}`; hover/focus styles using existing tokens. Under 760px allow the header to wrap and keep actions at 36px.

Implement these exact interfaces:

```js
function closeExportMenus({ restoreFocus = false } = {})
function toggleExportMenu(trigger, menu)
function handleExportMenuKeydown(event)
function createExportControl(kind, label, commands)
function mountExportActions(snapshot)
async function handleExportCommand(event)
```

`mountExportActions()` must move the rendered top-level H1 into a `.article-header`, or create an H1 from `snapshot.title` when absent. It appends copy and download controls containing five `<button role="menuitem">` commands. Opening focuses the first item; arrows wrap; Home/End jump; Escape closes and restores trigger focus; only one menu opens; outside pointer-down and new navigation close it. Mark the header `data-export-ui="true"` and call `mountExportActions(snapshot)` immediately after snapshot commit.

Use this temporary complete dispatcher until Task 3:

```js
async function handleExportCommand(event) {
  const button = event.target.closest('[data-export-command]');
  if (!button || button.getAttribute('aria-busy') === 'true') return;
  setMessage(`导出功能正在准备：${button.textContent}`);
}
```

- [ ] **Step 4: Run GREEN and commit**

Run both new tests. Expected: PASS, correct focus return, no overlap or root overflow.

Commit: `git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs && git commit -m "feat: add viewer export menus"`

### Task 3: Copy Source, Body, And Dual-MIME Rich Text

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing clipboard tests**

Add a contract asserting `cloneExportArticle`, removal of `[data-export-ui]`, DOMPurify sanitization, both `writeText(snapshot.source)` and `writeText(snapshot.body)`, `new ClipboardItem`, and Blob entries for `text/html` and `text/plain`.

Add this reusable Playwright initializer:

```js
async function installClipboardCapture(page, { rich = true } = {}) {
  await page.addInitScript(({ rich }) => {
    window.__clipboardWrites = [];
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
      writeText: async text => window.__clipboardWrites.push({ kind: 'text', text }),
      write: rich ? async items => {
        const item = items[0];
        const html = await (await item.getType('text/html')).text();
        const plain = await (await item.getType('text/plain')).text();
        window.__clipboardWrites.push({ kind: 'rich', html, plain });
      } : undefined,
    }});
    if (!rich) Object.defineProperty(window, 'ClipboardItem', { configurable: true, value: undefined });
  }, { rich });
}
```

Add browser cases that route a source containing frontmatter, bold text, and KaTeX; assert original copy is byte-identical, body copy omits only frontmatter, rich copy contains sanitized `<strong>` and `.katex` in HTML plus readable plain text, and export controls are absent. Add a second case with `rich:false` asserting plain-text fallback and the exact status `Plain text copied because rich-text clipboard is unavailable.`

- [ ] **Step 2: Run RED**

Run the contract and Playwright with `-g "viewer copies exact|falls back truthfully"`. Expected: no clipboard writes.

- [ ] **Step 3: Implement shared clone and copy commands**

Implement:

```js
function cloneExportArticle() {
  const clone = elements.content.cloneNode(true);
  clone.removeAttribute('id');
  clone.removeAttribute('aria-busy');
  clone.querySelectorAll('[data-export-ui]').forEach(node => node.remove());
  const article = document.createElement('article');
  article.className = elements.content.className;
  article.innerHTML = DOMPurify.sanitize(clone.innerHTML, {
    USE_PROFILES: { html: true }, FORBID_TAGS: ['script'], FORBID_ATTR: ['style'],
  });
  return article;
}
```

Implement `copyRichText()` using `article.outerHTML` and `article.innerText.trim()`. When both `ClipboardItem` and `navigator.clipboard.write` exist, call one `navigator.clipboard.write()` with:

```js
new ClipboardItem({
  'text/html': new Blob([html], { type: 'text/html' }),
  'text/plain': new Blob([plain], { type: 'text/plain' }),
})
```

Otherwise call `writeText(plain)` and report the exact fallback. Add generation-owned success feedback that clears after 2600ms only if no newer status exists. Replace the dispatcher so it captures `const snapshot = activeExportSnapshot` at click time, ignores repeated busy activation, uses exact success messages from the spec, closes only on success, keeps the menu on failure, and reports failures through `setMessage(message, true)`.

Add a temporary `runDownloadCommand(command)` that throws `Download command is unavailable: ${command}` so the dispatcher remains complete until Task 4.

- [ ] **Step 4: Run GREEN and commit**

Run the new clipboard tests plus `-g "complex knowledge pages"`. Expected: all pass.

Commit: `git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs && git commit -m "feat: copy viewer pages in three formats"`

### Task 4: Download Exact Markdown With Normalized Filenames

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing download tests**

Add a contract for `normalizeExportFilename`, regex `/[\/\\:*?"<>|\x00-\x1f\x7f]/g`, trimming trailing spaces/periods, fallback `knowledge-page`, basename preference, `new Blob([snapshot.source], { type: 'text/markdown;charset=utf-8' })`, and `URL.revokeObjectURL(url)`.

Add a Playwright test routing source with frontmatter and trailing blank lines, wait for `page.waitForEvent('download')`, choose `原始 .md`, assert `suggestedFilename()` equals the routed basename, and `fs.readFileSync(await download.path(), 'utf8')` exactly equals source.

- [ ] **Step 2: Run RED**

Run the new contract and Playwright with `-g "downloads exact Markdown"`. Expected: unavailable download error.

- [ ] **Step 3: Implement filename and Blob helpers**

```js
function normalizeExportFilename(name) {
  const value = String(name || '').replace(/[\/\\:*?"<>|\x00-\x1f\x7f]/g, '_')
    .trim().replace(/[. ]+$/g, '');
  return value || 'knowledge-page';
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function downloadMarkdown(snapshot) {
  const sourceName = snapshot.file.split('/').pop() || `${snapshot.title}.md`;
  const filename = `${normalizeExportFilename(sourceName.replace(/\.md$/i, ''))}.md`;
  triggerBlobDownload(new Blob([snapshot.source], {
    type: 'text/markdown;charset=utf-8',
  }), filename);
}
```

Update `runDownloadCommand(command, snapshot)` to call `downloadMarkdown(snapshot)` and report `Markdown downloaded.` for `download-markdown`; retain an explicit unavailable error for `download-html`.

- [ ] **Step 4: Run GREEN and commit**

Expected: exact bytes and basename pass.

Commit: `git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs && git commit -m "feat: download original viewer markdown"`

### Task 5: Download A Strictly Self-Contained HTML Article

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing HTML export tests**

Add a contract asserting `buildSelfContainedHtml`, `fetchRequiredBlob`, `blobToDataUrl`, `inlineKatexCss`, the local KaTeX CSS path, URL API resolution, safe link protocols, image data URL assignment, `<!doctype html>`, and absence of an emitted script template.

Add one browser fixture containing an image, `$$x^2$$`, and Mermaid. Intercept the image with a 1x1 PNG, download HTML, and assert: normalized title filename; doctype/title/viewport; `data:image/png;base64`; `data:font/woff2;base64`; `.katex`; rendered `<svg`; article styles; no export actions, sidebar, `<script`, or `vendor/katex` URL. Add a failure fixture whose image returns 404; assert no download event, an alert naming the asset, readable article unchanged, and menu remains open.

- [ ] **Step 2: Run RED**

Run the contract and Playwright with `-g "self-contained article|required image"`. Expected: unavailable HTML error.

- [ ] **Step 3: Implement strict asset embedding**

Implement these interfaces:

```js
async function fetchRequiredBlob(url, label)
function blobToDataUrl(blob)
function safeResolvedLink(rawUrl)
async function embedArticleImages(article)
async function inlineKatexCss()
async function buildSelfContainedHtml(snapshot)
async function downloadSelfContainedHtml(snapshot)
```

`fetchRequiredBlob` must wrap network exceptions and reject every non-OK response with the supplied label. `blobToDataUrl` must use `FileReader`. `embedArticleImages` must resolve each `src` with `new URL(rawUrl, document.baseURI)`, accept only HTTP(S), fetch and replace with data URLs, remove `srcset`, and reject on any failure. Resolve fragment links unchanged, normal links to absolute `http:`, `https:`, or `mailto:`, and remove unsafe hrefs.

`inlineKatexCss()` must fetch `vendor/katex/katex.min.css`, find every CSS `url()` reference with `/url\((['"]?)([^)'"\s]+)\1\)/g`, resolve against the CSS URL, fetch each unique font, convert it to a data URL, and replace all occurrences. Any stylesheet or font failure rejects export.

Define an `EXPORTED_ARTICLE_CSS` string containing only article typography/layout, tables, code, images, KaTeX overflow, Mermaid, interview-page hierarchy, and the existing narrow viewport rule. It must not contain shell, navigation, quality, taxonomy, or export-control styles.

`buildSelfContainedHtml()` must clone via `cloneExportArticle()`, await image and conditional KaTeX embedding, sanitize again with HTML/SVG profiles while forbidding scripts and event attributes, escape the document title, and return this exact document structure:

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>escaped rendered title</title>
<style>inlined KaTeX CSS followed by article CSS</style>
</head>
<body>
<article>sanitized current article with rendered KaTeX and Mermaid SVG</article>
<!-- No JavaScript is required to read this export. -->
</body>
</html>
```

`downloadSelfContainedHtml()` must finish all awaited resource work before creating a Blob, use normalized rendered title plus `.html`, and report `HTML downloaded.`. Update `runDownloadCommand()` to await it. On rejection, the existing command handler must create no Blob/download, name the failed resource in an alert, preserve snapshot/article, and leave the menu open.

- [ ] **Step 4: Run GREEN and commit**

Run the new contract and both browser cases. Expected: complete offline payload passes and missing asset produces zero downloads.

Commit: `git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs && git commit -m "feat: export self-contained viewer html"`

### Task 6: Lock Navigation Identity And Run Full Regression

**Files:**
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write a rapid-navigation export regression**

Route a slow page and an immediate final page, start both `navigateTo()` calls, wait for the final H1, then copy original Markdown and assert the clipboard contains only the final source. This test must use the clipboard capture from Task 3 and wait beyond the slow response before copying.

- [ ] **Step 2: Run the focused test**

Run: `npx playwright test tests/desktop_experience.spec.cjs --config tests/playwright.config.cjs --reporter=line -g "export always reads the final active page"`

Expected: PASS. If it exposes a stale export, replace the handler guard with this exact activation-time identity check:

```js
const snapshot = activeExportSnapshot;
if (!snapshot || snapshot.token !== navigationGeneration) return;
```

- [ ] **Step 3: Run all Viewer contracts**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: all tests pass with `OK`.

- [ ] **Step 4: Run the complete desktop suite**

With workbench at `http://127.0.0.1:18080` and knowledge server at `http://127.0.0.1:18081`, run:

`npx playwright test tests/desktop_experience.spec.cjs --config tests/playwright.config.cjs --reporter=line`

Expected: all tests pass, including existing 300ms same-section and 500ms cross-section navigation budgets.

- [ ] **Step 5: Verify scope and commit regression coverage**

Run:

```bash
git diff --check
git status --short
git diff -- viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs
```

Expected: no whitespace errors; only the three planned files belong to this feature; unrelated worktree changes remain untouched and unstaged.

Commit: `git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs && git commit -m "test: cover viewer export navigation and recovery"`

## Plan Self-Review

- [ ] **Step 1: Verify specification coverage**

Map every design requirement to a task: five formats; exact source; frontmatter-free body; dual-MIME rich copy and truthful fallback; title-side responsive controls; keyboard menus; basename/normalized names; article-only HTML; embedded image and KaTeX fonts; retained Mermaid SVG; safe links; no scripts; hard asset failure; no server API; no extra page fetch; current-generation snapshot; recoverable status/error behavior; existing navigation, context, scroll, history, and performance behavior.

- [ ] **Step 2: Scan for forbidden placeholders**

Run: `bad='T''BD|T''ODO|implement'' later|fill'' in details|add'' appropriate|add'' validation|handle'' edge cases|write'' tests for the above|similar'' to task|保留现有''逻辑|[.]''[.]''[.]'; rg -n "$bad" docs/superpowers/plans/2026-08-02-viewer-page-export.md`

Expected: no output.

- [ ] **Step 3: Check naming consistency**

Run: `rg -n "activeExportSnapshot|closeExportMenus|mountExportActions|handleExportCommand|cloneExportArticle|normalizeExportFilename|triggerBlobDownload|buildSelfContainedHtml|runDownloadCommand" docs/superpowers/plans/2026-08-02-viewer-page-export.md`

Expected: all names are consistent; temporary download dispatchers are explicitly replaced in later tasks.

- [ ] **Step 4: Commit only this plan**

Run:

```bash
git diff --check -- docs/superpowers/plans/2026-08-02-viewer-page-export.md
git status --short
git add docs/superpowers/plans/2026-08-02-viewer-page-export.md
git diff --cached --name-only
git commit -m "docs: plan viewer page export"
```

Expected: the cached list contains only `docs/superpowers/plans/2026-08-02-viewer-page-export.md`, then Git creates the plan commit.
