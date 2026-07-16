# Web Workbench Usability Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair every issue confirmed in the 2026-07-16 end-to-end usability audit while preserving the existing two-service, static-page architecture.

**Architecture:** Keep the workbench patch, Viewer, and graph as separate owners. Introduce a validated `kb-context` iframe protocol, browser-session state for navigation/graph/drafts, and checked-in browser distributions for all rendering dependencies. Use contract tests for stable source-level guarantees and Playwright for real interaction and offline verification.

**Tech Stack:** Static HTML/CSS/JavaScript, Node.js patch scripts and tests, Python `unittest`, Cytoscape.js, KaTeX, Mermaid, Marked, DOMPurify, Highlight.js, Playwright CLI.

---

## File Map

- Modify `/home/u2023312337/webui/patch-integrated-workbench.mjs`: workbench dialogs, context protocol, Claude prompts, refresh phases, draft persistence, SVG icons, local Claude Markdown assets.
- Modify `/home/u2023312337/webui/test-integrated-workbench.mjs`: patch contract and generated-asset assertions.
- Modify `/home/u2023312337/webui/patch-dangerous-mode.mjs`: replace the permission-mode Unicode tool character with stable inline SVG/CSS output.
- Modify `/home/u2023312337/webui/test-dangerous-mode.mjs`: permission control icon regression assertions.
- Modify `viewer.html`: local dependencies, search UI, directory persistence, no-flicker navigation, page context messages and resource errors.
- Modify `graph-view.html`: local dependencies, stable SVG icons, graph state persistence, in-place refresh and graph context messages.
- Modify `首页.md`: Web-first user journey and secondary maintenance instructions.
- Modify `Web操作台使用与维护说明书.md`: document search, graph context, state restoration, local assets and dialog behavior while preserving pre-existing user formatting changes.
- Modify `tests/test_viewer_contract.py`: Viewer search, persistence, local resource and context contracts.
- Modify `tests/test_graph_view_contract.py`: graph state, refresh, context and icon contracts.
- Create `tests/test_home_web_first.py`: homepage guidance contract.
- Create `tests/test_vendor_assets.py`: exact local browser asset inventory and CDN prohibition.
- Create `tests/test_web_workbench_e2e.py`: Playwright-backed desktop/mobile/offline interaction regression entry point.
- Create `scripts/vendor_web_assets.sh`: reproducible fixed-version browser asset fetch and placement.
- Create `vendor/`: checked-in Viewer/graph browser distributions, styles and KaTeX fonts.
- Create `/home/u2023312337/webui/vendor/`: checked-in/generated Claude WebUI Marked and DOMPurify browser distributions.

### Task 1: Establish Failing Contracts for All Audit Findings

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/test_graph_view_contract.py`
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/test-dangerous-mode.mjs`
- Create: `tests/test_home_web_first.py`
- Create: `tests/test_vendor_assets.py`

- [ ] **Step 1: Add failing Viewer contracts**

Add focused tests that require local asset URLs, search controls, keyboard handling, persisted expansion state, retry behavior and `kb-context` page messages:

```python
def test_uses_only_local_browser_dependencies(self):
    self.assertNotIn("cdn.jsdelivr.net", self.html)
    for asset in ("vendor/marked/marked.min.js", "vendor/katex/katex.min.css", "vendor/mermaid/mermaid.min.js"):
        self.assertIn(asset, self.html)

def test_sidebar_search_and_persisted_expansion_are_implemented(self):
    for value in ('id="navigationSearch"', 'aria-label="搜索知识页"', 'id="collapseAll"'):
        self.assertIn(value, self.html)
    for function in ("filterNavigation", "saveNavigationState", "restoreNavigationState", "retryIndexLoad"):
        self.assertRegex(self.html, rf"function\s+{function}\s*\(")
    self.assertIn("radar-viewer-navigation-v1", self.html)
    self.assertIn("event.key === '/'", self.html)
    self.assertIn("event.key.toLowerCase() === 'k'", self.html)

def test_reports_structured_page_context(self):
    self.assertIn("kb-context", self.html)
    self.assertIn("kind: 'page'", self.html)
    self.assertIn("event.source", self.html)
```

- [ ] **Step 2: Add failing graph contracts**

```python
def test_persists_and_restores_graph_workspace(self):
    self.assertIn("radar-graph-state-v1", self.html)
    for function in ("readPersistedState", "persistGraphState", "restoreGraphViewport", "notifyGraphContext"):
        self.assertRegex(self.html, rf"function\s+{function}\s*\(")
    self.assertIn("selectedNodeId", self.html)
    self.assertIn("state.cy.on('pan zoom'", self.html)

def test_refreshes_in_place_and_uses_local_dependencies(self):
    self.assertNotIn("cdn.jsdelivr.net", self.html)
    self.assertNotIn("location.reload()", self.html)
    self.assertIn("await loadGraph", self.html)
    self.assertIn("vendor/cytoscape/cytoscape.min.js", self.html)

def test_reports_graph_context_and_does_not_use_font_glyph_tools(self):
    self.assertIn("kb-context", self.html)
    self.assertIn("kind: 'graph'", self.html)
    self.assertIn("visibleNodes", self.html)
    self.assertNotIn(">⌗<", self.html)
```

- [ ] **Step 3: Add failing workbench contracts**

Require explicit cancel button types, unified dialog helpers, source validation, graph prompts, draft state and local Markdown assets:

```javascript
assert.match(shell, /id="cancelCreateKnowledge" type="button"/);
assert.match(shell, /id="cancelAsk" type="button"/);
for (const marker of ['openDialog', 'closeDialog', 'bindDialogDismissal', 'validateKnowledgeContext']) {
  assert.match(js, new RegExp(`function ${marker}\\(`));
}
assert.match(js, /event\.source !== knowledgeFrame\.contentWindow/);
assert.match(js, /context\.kind==='graph'/);
assert.match(js, /radar-claude-draft-v1/);
assert.match(js, /saveClaudeDraft/);
assert.match(js, /restoreClaudeDraft/);
assert.doesNotMatch(chat, /cdn\.jsdelivr\.net/);
assert.match(chat, /\/assets\/vendor\/marked\.min\.js/);
```

- [ ] **Step 4: Add failing homepage and vendor contracts**

`tests/test_home_web_first.py`:

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HomeWebFirstTests(unittest.TestCase):
    def test_home_leads_with_web_workbench(self):
        text = (ROOT / "首页.md").read_text(encoding="utf-8")
        first_screen = text[:900]
        for phrase in ("Web 操作台", "搜索", "交互图谱", "询问 Claude", "创建知识页"):
            self.assertIn(phrase, first_screen)
        self.assertIn("维护与排障", text)
        self.assertNotIn("要看全局图谱时运行", first_screen)
```

`tests/test_vendor_assets.py`:

```python
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class VendorAssetTests(unittest.TestCase):
    def test_required_assets_exist_and_are_nonempty(self):
        required = [
            "vendor/marked/marked.min.js", "vendor/dompurify/purify.min.js",
            "vendor/highlight/highlight.min.js", "vendor/highlight/github.min.css",
            "vendor/mermaid/mermaid.min.js", "vendor/katex/katex.min.js",
            "vendor/katex/auto-render.min.js", "vendor/katex/katex.min.css",
            "vendor/cytoscape/cytoscape.min.js", "vendor/cytoscape/layout-base.js",
            "vendor/cytoscape/cose-base.js", "vendor/cytoscape/cytoscape-fcose.js",
        ]
        for relative in required:
            path = ROOT / relative
            with self.subTest(path=relative):
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 100)

    def test_katex_fonts_are_present(self):
        fonts = list((ROOT / "vendor/katex/fonts").glob("*.woff2"))
        self.assertGreaterEqual(len(fonts), 20)
```

- [ ] **Step 5: Run the new tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract tests.test_home_web_first tests.test_vendor_assets -v
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/test-dangerous-mode.mjs
```

Expected: failures specifically report missing search/state/context/local assets, old `location.reload()`, missing dialog helpers and old homepage guidance. Fix test syntax until failures reflect missing behavior rather than import or parsing errors.

- [ ] **Step 6: Commit failing tests**

```bash
git add tests/test_viewer_contract.py tests/test_graph_view_contract.py tests/test_home_web_first.py tests/test_vendor_assets.py
git commit -m "test: cover web workbench usability regressions"
```

Commit the two `/home/u2023312337/webui` test files in that repository only if it is a separate Git worktree; otherwise leave them as tracked deployment-source changes for the final scoped commit.

### Task 2: Vendor Fixed Browser Assets and Remove CDN Runtime Dependencies

**Files:**
- Create: `scripts/vendor_web_assets.sh`
- Create: `vendor/**`
- Create: `/home/u2023312337/webui/vendor/marked.min.js`
- Create: `/home/u2023312337/webui/vendor/purify.min.js`
- Modify: `viewer.html`
- Modify: `graph-view.html`
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`

- [ ] **Step 1: Write the deterministic vendor script**

Create a shell script using `curl --fail --location --retry 3` and fixed jsDelivr package URLs. Download into a temporary directory, verify every file is nonempty, then atomically replace destination files. Include KaTeX `dist/fonts/*.woff2`; use the npm tarball for KaTeX so all font names referenced by `katex.min.css` are present.

Core declarations:

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fetch() { curl --fail --location --retry 3 --silent --show-error "$1" --output "$2"; test -s "$2"; }

fetch "https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js" "$TMP/marked.min.js"
fetch "https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js" "$TMP/purify.min.js"
fetch "https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/lib/common.min.js" "$TMP/highlight.min.js"
fetch "https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/styles/github.min.css" "$TMP/github.min.css"
fetch "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js" "$TMP/mermaid.min.js"
```

Add the corresponding Cytoscape/fCoSE URLs from the approved versions. For KaTeX, download `https://registry.npmjs.org/katex/-/katex-0.16.22.tgz`, extract `package/dist`, and copy JS, CSS and fonts.

- [ ] **Step 2: Run the vendor script**

Run:

```bash
bash scripts/vendor_web_assets.sh
python3 -m unittest tests.test_vendor_assets -v
```

Expected: vendor test passes and all files are served from repository-local paths.

- [ ] **Step 3: Point Viewer and graph to local assets**

Replace every `https://cdn.jsdelivr.net/npm/...` URL with the approved relative path. Add explicit boot guards:

```javascript
function requireRuntime(name, value) {
  if (!value) throw new Error(`${name} 本地资源加载失败，请重新运行 scripts/vendor_web_assets.sh`);
  return value;
}
```

Viewer checks `marked`, `DOMPurify`, `hljs`, `mermaid`, `katex` and `renderMathInElement` before rendering. Graph checks `cytoscape` before loading data and shows the existing `errorState` on failure.

- [ ] **Step 4: Copy Claude Markdown assets during patching**

Extend the patch script with a `copyVendorAssets()` function that copies the repository or WebUI vendor files into `${BASE}/vendor/marked.min.js` and `${BASE}/vendor/purify.min.js`, then change injected scripts to:

```html
<script src="/assets/vendor/marked.min.js"></script>
<script src="/assets/vendor/purify.min.js"></script>
```

Fail the patch command with a clear missing-file message instead of generating an online-dependent page.

- [ ] **Step 5: Verify GREEN for asset contracts**

Run:

```bash
python3 -m unittest tests.test_vendor_assets tests.test_viewer_contract tests.test_graph_view_contract -v
node /home/u2023312337/webui/test-integrated-workbench.mjs
rg -n "cdn\.jsdelivr\.net|unpkg\.com" viewer.html graph-view.html /home/u2023312337/webui/patch-integrated-workbench.mjs
```

Expected: tests pass; `rg` produces no runtime dependency matches except the reproducible vendor script.

- [ ] **Step 6: Commit local assets and references**

```bash
git add scripts/vendor_web_assets.sh vendor viewer.html graph-view.html tests/test_vendor_assets.py
git commit -m "fix: serve knowledge rendering assets locally"
```

### Task 3: Repair Dialog Lifecycle, Claude Context and Draft Persistence

**Files:**
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`

- [ ] **Step 1: Verify the Task 1 workbench tests fail for current behavior**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
```

Expected: FAIL on missing explicit cancel types, dialog lifecycle helpers, `kb-context`, graph prompt and draft persistence.

- [ ] **Step 2: Replace the old file-only state with validated context**

Use this state shape and validator in generated `workbench.js`:

```javascript
let activeContext={kind:'page',file:'首页.md',title:'首页'};
function validateKnowledgeContext(value){
  if(!value||typeof value!=='object')return null;
  if(value.kind==='page'&&typeof value.file==='string'&&!value.file.includes('..')){
    return {kind:'page',file:value.file,title:typeof value.title==='string'?value.title:value.file};
  }
  if(value.kind==='graph'&&['knowledge','taxonomy','combined'].includes(value.mode)){
    const selected=value.selected&&typeof value.selected.label==='string'?{
      label:value.selected.label,nodeType:String(value.selected.nodeType||'node'),
      neighbors:Array.isArray(value.selected.neighbors)?value.selected.neighbors.filter(item=>typeof item==='string').slice(0,20):[]
    }:null;
    return {kind:'graph',mode:value.mode,modeLabel:String(value.modeLabel||value.mode),
      visibleNodes:Number(value.visibleNodes)||0,visibleEdges:Number(value.visibleEdges)||0,
      categories:Array.isArray(value.categories)?value.categories.filter(item=>typeof item==='string'):[],
      projects:Array.isArray(value.projects)?value.projects.filter(item=>typeof item==='string'):[],selected};
  }
  return null;
}
```

The message listener must verify `event.origin`, `event.source` and `event.data.type === 'kb-context'` before updating context and labels.

- [ ] **Step 3: Implement graph-aware prompts**

Add `buildClaudeQuestion(context, questionText)` with three explicit branches. Page prompts retain the file-read requirement. Selected graph prompts include node label/type/neighbors. Unselected graph prompts include mode, filters and visible counts. Unit-test the generated strings in the Node patch test by extracting or evaluating generated JS in a DOM harness where practical.

- [ ] **Step 4: Implement one dialog lifecycle**

Change cancel controls to named `type="button"` buttons and add:

```javascript
function openDialog(dialogElement,focusTarget,trigger){dialogElement.__trigger=trigger;dialogElement.showModal();focusTarget?.focus()}
function closeDialog(dialogElement){if(dialogElement.open)dialogElement.close();dialogElement.__trigger?.focus()}
function bindDialogDismissal(dialogElement,cancelButton){
  cancelButton.addEventListener('click',()=>closeDialog(dialogElement));
  dialogElement.addEventListener('cancel',event=>{event.preventDefault();closeDialog(dialogElement)});
  dialogElement.addEventListener('click',event=>{if(event.target===dialogElement)closeDialog(dialogElement)});
}
```

Add an inline `role="alert"` error element to each dialog. `putInClaude()` returns `false` when both direct insertion and clipboard copy fail. Submission closes only on `true`.

- [ ] **Step 5: Persist and restore Claude drafts around refresh**

Use storage key `radar-claude-draft-v1`. Add `readClaudeInput`, `saveClaudeDraft`, `restoreClaudeDraft`, and an iframe `load` handler with bounded retries for the React textarea. Listen for input changes inside the same-origin Claude iframe and clear the key when the value becomes empty.

Call `saveClaudeDraft()` immediately before `/api/refresh`; call `restoreClaudeDraft()` after refresh completion and on Claude iframe load.

- [ ] **Step 6: Replace workbench Unicode-only icons**

Add a small `icon(name)` build-time helper returning audited inline SVG strings for refresh, collapse-left and collapse-right. Buttons retain text-independent `aria-label` and `title`.

- [ ] **Step 7: Run patch tests and apply the patch**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/patch-integrated-workbench.mjs
```

Expected: tests pass and patch exits 0, reporting generated workbench assets.

- [ ] **Step 8: Commit workbench source changes in its owning repository**

Inspect `/home/u2023312337/webui` with `git status --short`. If tracked there:

```bash
git -C /home/u2023312337/webui add patch-integrated-workbench.mjs test-integrated-workbench.mjs vendor
git -C /home/u2023312337/webui commit -m "fix: preserve workbench context and dialog state"
```

Do not commit generated `dist/static` output unless that repository already tracks it.

### Task 4: Add Viewer Search, Stable Navigation and Page Context

**Files:**
- Modify: `viewer.html`
- Modify: `tests/test_viewer_contract.py`

- [ ] **Step 1: Run Viewer contracts and verify RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract -v
```

Expected: failures for search markup, persisted expansion, retry, local context and no-flicker behavior.

- [ ] **Step 2: Add the fixed search header**

Place a search region above `#navigation` with a search icon, `<input id="navigationSearch" type="search" aria-label="搜索知识页">`, clear control and icon-only collapse-all button. Use stable inline SVG and dimensions; do not use font glyphs.

- [ ] **Step 3: Extend index parsing and filtering**

Keep parsed entries in `navigationState.entries`. Extract title, path, summary, category/project tags and aliases from `_index.md`. Implement:

```javascript
function normalizeSearch(value){return String(value||'').normalize('NFKC').toLocaleLowerCase('zh-CN').trim()}
function filterNavigation(query){
  const terms=normalizeSearch(query).split(/\s+/).filter(Boolean);
  if(!terms.length){renderCategorizedNavigation();return}
  const matches=navigationState.entries.filter(entry=>terms.every(term=>entry.searchText.includes(term)));
  renderSearchResults(matches,navigationState.activeFile);
}
```

Score exact/prefix title matches before aliases, tags and summary. Build DOM with `textContent`; do not inject index text with `innerHTML`.

- [ ] **Step 4: Persist directory expansion and remove page-change reloads**

Use `radar-viewer-navigation-v1` with `{expanded: string[]}`. On first load, expand only groups containing the active file; on later loads, restore explicit state. `loadPage()` updates active link classes without rerunning `loadNavigation()`.

The initial skeleton remains mounted while the first index fetch runs. Retry replaces only the error area. Add `retryIndexLoad()`.

- [ ] **Step 5: Add keyboard behavior**

At document level, focus search for `/` outside editable controls and `Ctrl+K`/`Meta+K`. On `Escape`, clear a nonempty query first; otherwise close mobile navigation. Preserve standard browser find and text-entry behavior.

- [ ] **Step 6: Send structured page context**

Replace or supplement `kb-active-file` with:

```javascript
window.parent.postMessage({type:'kb-context',context:{kind:'page',file,title:document.querySelector('article h1')?.textContent||file}},WORKBENCH_ORIGIN)
```

Send only after content, formulas, code highlighting and Mermaid rendering finish.

- [ ] **Step 7: Verify GREEN**

Run:

```bash
python3 -m unittest tests.test_viewer_contract -v
python3 scripts/check_health.py
```

Expected: Viewer contracts pass; health output remains `ERROR 0 / WARN 0`.

- [ ] **Step 8: Commit Viewer behavior**

```bash
git add viewer.html tests/test_viewer_contract.py
git commit -m "feat: add searchable persistent viewer navigation"
```

### Task 5: Preserve Graph State and Report Graph Context

**Files:**
- Modify: `graph-view.html`
- Modify: `tests/test_graph_view_contract.py`

- [ ] **Step 1: Run graph contracts and verify RED**

Run:

```bash
python3 -m unittest tests.test_graph_view_contract -v
```

Expected: failures for missing state schema, context reporting, local refresh and Unicode icon removal.

- [ ] **Step 2: Add validated persisted state**

Implement `readPersistedState()` with `try/catch`, `version === 1`, enumerated modes, string arrays, boolean toggles, finite zoom and finite pan coordinates. Unknown fields are ignored. Add a debounced `persistGraphState()` that reads current controls and Cytoscape viewport.

- [ ] **Step 3: Restore controls, selection and viewport in order**

Load persisted state before rendering filter controls. Intersect stored category/project arrays with values in the new payload. After `replaceGraphElements()` and `applyFilters()`, restore an existing selected node. Use `state.cy.one('layoutstop', restoreGraphViewport)` so the layout cannot overwrite stored zoom/pan.

- [ ] **Step 4: Refresh graph in place**

Replace the workbench message handler:

```javascript
if(event.data?.type==='kb-refresh'){
  persistGraphState();
  loadGraph().catch(showGraphError);
}
```

`loadGraph()` must fetch into a local payload, validate it, and only destroy/replace the existing graph after successful parsing. If fetch or validation fails, leave the old graph mounted and show a nonblocking error.

- [ ] **Step 5: Report graph context after every relevant transition**

Implement `notifyGraphContext()` with current mode label, visible node/edge counts, checked categories/projects and selected node data. Neighbor labels come from `selected.closedNeighborhood().nodes().not(selected)` and are capped at 20. Call after initial load, mode switch, filter changes, focus/clear and successful data replacement.

- [ ] **Step 6: Replace graph tool glyphs with inline SVG**

Use consistent 18 x 18 SVG icons for filter, fit and rebuild. Keep mode buttons textual. Set fixed 36 x 36 tool-button dimensions so icons cannot shift the mobile toolbar.

- [ ] **Step 7: Verify GREEN**

Run:

```bash
python3 -m unittest tests.test_graph_view_contract -v
python3 scripts/render_graph.py
```

Expected: graph contracts pass; generator reports the current node/edge summary without errors.

- [ ] **Step 8: Commit graph behavior**

```bash
git add graph-view.html tests/test_graph_view_contract.py graph-data.json graph.md graph_*.md
git commit -m "fix: preserve graph workspace across refreshes"
```

Only add generated Markdown files that are already tracked and actually changed by the generator.

### Task 6: Repair Permission Icon and Mobile Composer Details

**Files:**
- Modify: `/home/u2023312337/webui/patch-dangerous-mode.mjs`
- Modify: `/home/u2023312337/webui/test-dangerous-mode.mjs`
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`

- [ ] **Step 1: Add a failing icon contract**

Require the dangerous-mode patch not to inject `🔧`, and require an SVG marker or CSS mask with an accessible mode label.

```javascript
assert.doesNotMatch(output, /🔧/);
assert.match(output, /data-permission-icon/);
assert.match(output, /aria-label/);
```

- [ ] **Step 2: Run the test and verify RED**

```bash
node /home/u2023312337/webui/test-dangerous-mode.mjs
```

Expected: FAIL because the current mode control uses the tool glyph.

- [ ] **Step 3: Implement stable permission icon and narrow-screen layout**

Patch the control to render a local inline SVG before the mode text. In the conversation theme, make the permission control a flex row with `min-width:0`, wrapping descriptive text below 420px while keeping the icon fixed at 16 x 16.

- [ ] **Step 4: Verify and apply both patches**

```bash
node /home/u2023312337/webui/test-dangerous-mode.mjs
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/patch-dangerous-mode.mjs
node /home/u2023312337/webui/patch-integrated-workbench.mjs
```

Expected: all commands exit 0.

- [ ] **Step 5: Commit in the WebUI repository**

```bash
git -C /home/u2023312337/webui add patch-dangerous-mode.mjs test-dangerous-mode.mjs patch-integrated-workbench.mjs
git -C /home/u2023312337/webui commit -m "fix: stabilize workbench mobile tool controls"
```

### Task 7: Update Web-First Guidance and Maintenance Documentation

**Files:**
- Modify: `首页.md`
- Modify: `Web操作台使用与维护说明书.md`
- Modify: `tests/test_home_web_first.py`

- [ ] **Step 1: Run homepage contract and verify RED**

```bash
python3 -m unittest tests.test_home_web_first -v
```

Expected: FAIL because the first screen still directs users to scripts and VS Code.

- [ ] **Step 2: Rewrite the homepage first screen**

Lead with a concise “从 Web 操作台开始” section containing the actual local URL, Viewer search, interactive graph, Ask Claude, Create Knowledge Page and Refresh actions. Move script commands into “维护与排障”. Preserve category and project links.

- [ ] **Step 3: Update the maintenance manual without discarding existing edits**

Read the current dirty file and edit around its actual content. Document:

- search shortcuts and result fields;
- graph state restoration and graph-aware Claude prompts;
- dialog close methods;
- local asset refresh command;
- refresh phases and draft preservation;
- troubleshooting for missing local assets.

Do not reformat unrelated tables or erase the existing user-owned formatting diff.

- [ ] **Step 4: Verify docs and health**

```bash
python3 -m unittest tests.test_home_web_first -v
python3 scripts/build_index.py
python3 scripts/check_health.py
```

Expected: homepage test passes and health reports `ERROR 0 / WARN 0`.

- [ ] **Step 5: Commit only intended documentation hunks**

Use `git diff -- 首页.md Web操作台使用与维护说明书.md` and ensure pre-existing formatting changes remain intact. Stage the full file only after confirming all differences are intended or user-owned and preserved.

```bash
git add 首页.md Web操作台使用与维护说明书.md tests/test_home_web_first.py _index.md
git commit -m "docs: make the web workbench the primary entry point"
```

### Task 8: Add Real Browser Regression Coverage

**Files:**
- Create: `tests/test_web_workbench_e2e.py`
- Modify: `tests/test_web_console_manual.py` only if shared helpers are extracted without changing its existing intent.

- [ ] **Step 1: Write an executable Playwright regression wrapper**

The test should skip with a clear message when services are not available, otherwise drive the Playwright CLI session `kb-regression`. Use subprocess commands with timeouts and assert CLI output does not contain `### Error`.

Cover these flows in separate tests or named helper steps:

```python
DESKTOP = (1440, 900)
MOBILE = (390, 844)

def test_create_dialog_closes_three_ways(...): ...
def test_viewer_search_and_keyboard_shortcuts(...): ...
def test_graph_context_reaches_claude_prompt(...): ...
def test_graph_state_survives_refresh(...): ...
def test_claude_draft_survives_knowledge_refresh(...): ...
def test_offline_rendering_has_no_external_requests(...): ...
def test_mobile_layout_has_no_horizontal_overflow(...): ...
```

Use Playwright page evaluation for stable assertions such as `dialog.open`, focused element ID, iframe URL, input value, graph state and `document.documentElement.scrollWidth <= innerWidth`.

- [ ] **Step 2: Run against the current implementation and verify meaningful failures if any task remains incomplete**

```bash
python3 -m unittest tests.test_web_workbench_e2e -v
```

Expected before all implementation tasks: at least the original create-dialog or context/state scenario fails for the correct reason. After Tasks 2-7, all scenarios pass.

- [ ] **Step 3: Add offline request enforcement**

For the offline scenario, route-abort every request whose hostname is not `127.0.0.1` or `localhost`, reload Viewer and graph, then assert:

- `.katex` exists on the DDPM page;
- graph canvas contains Cytoscape rendered nodes;
- no failed external request was attempted;
- console error list is empty.

- [ ] **Step 4: Commit browser regression test**

```bash
git add tests/test_web_workbench_e2e.py
git commit -m "test: add end-to-end workbench usability coverage"
```

### Task 9: Full Deployment and Completion Audit

**Files:**
- Verify all files named in this plan.

- [ ] **Step 1: Run all source and unit tests fresh**

```bash
python3 -m unittest discover -s tests -v
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/test-dangerous-mode.mjs
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Regenerate and check the knowledge base**

```bash
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: generators exit 0; health reports `ERROR 0 / WARN 0`.

- [ ] **Step 3: Reapply patches and restart services**

```bash
node /home/u2023312337/webui/patch-dangerous-mode.mjs
node /home/u2023312337/webui/patch-integrated-workbench.mjs
/home/u2023312337/webui/kbserve-control restart
/home/u2023312337/webui/webui-control restart
/home/u2023312337/webui/kbserve-control status
/home/u2023312337/webui/webui-control status
```

Expected: both status commands report running services on `18081` and `18080`.

- [ ] **Step 4: Run desktop, mobile and offline browser regression fresh**

```bash
python3 -m unittest tests.test_web_workbench_e2e -v
```

Capture final screenshots for home/search, DDPM formulas, selected-node graph context, graph after refresh, Claude composer and mobile graph.

- [ ] **Step 5: Audit each approved requirement against evidence**

Create a local checklist from the design acceptance criteria and point each item to one passing contract test plus one runtime observation where applicable. Explicitly verify:

- dialog cancel/Escape/backdrop;
- page and graph Claude contexts;
- search title/tag/summary and shortcuts;
- graph mode/filter/node/viewport restore;
- local-only formula/Markdown/graph assets;
- Web-first homepage;
- no Unicode missing-glyph tools;
- no page-change sidebar flash;
- mobile overflow and console errors.

- [ ] **Step 6: Inspect repository state and commit remaining scoped changes**

```bash
git status --short
git diff --check
git diff --stat HEAD~10..HEAD
```

Do not revert or absorb unrelated user changes. Commit only remaining files directly required by the approved design.

- [ ] **Step 7: Mark the active goal complete only after all evidence is present**

Report test counts, health output, service URLs, screenshots, commits and any preserved unrelated worktree modifications. Do not claim completion if any acceptance criterion lacks direct evidence.

