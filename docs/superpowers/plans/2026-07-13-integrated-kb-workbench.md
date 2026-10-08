# Integrated Knowledge Base Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make port 18080 a unified knowledge-base workspace with persistent document navigation/preview and the existing Claude Code chat.

**Architecture:** A reproducible patcher replaces only the vendor package's static entry document with a workbench shell and preserves the original chat document as `claude.html`. The shell embeds the existing port-18081 Viewer and same-origin Claude UI in resizable panes; the Viewer reports its active file through a restricted `postMessage` bridge.

**Tech Stack:** Node.js 24, HTML/CSS/JavaScript, existing claude-code-webui 0.1.56, Python unittest contract tests, Playwright browser verification.

---

### Task 1: Viewer active-file bridge

**Files:**
- Modify: `<repo-root>/tests/test_viewer_contract.py`
- Modify: `<repo-root>/viewer.html`

- [ ] Add a failing contract test requiring a `notifyActiveFile(file)` function, a `window.parent.postMessage` call, the message type `kb-active-file`, and an explicit `http://127.0.0.1:18080` target origin.
- [ ] Run `python3 -m unittest tests/test_viewer_contract.py -v` through discovery and confirm failure because the bridge is absent.
- [ ] Implement `notifyActiveFile(file)` and call it only after a validated Markdown file renders successfully. Report `{ type: 'kb-active-file', file, title }`; do nothing when the Viewer is top-level.
- [ ] Run the Viewer contract tests and confirm they pass.
- [ ] Commit only the Viewer and test files.

### Task 2: Reproducible workbench patcher

**Files:**
- Create: `<local-webui-root>/patch-integrated-workbench.mjs`
- Create: `<local-webui-root>/test-integrated-workbench.mjs`
- Generate: `<local-webui-root>/app/node_modules/claude-code-webui/dist/static/index.html`
- Generate: `<local-webui-root>/app/node_modules/claude-code-webui/dist/static/claude.html`
- Generate: `<local-webui-root>/app/node_modules/claude-code-webui/dist/static/workbench.css`
- Generate: `<local-webui-root>/app/node_modules/claude-code-webui/dist/static/workbench.js`

- [ ] Write failing Node tests against a temporary fake vendor directory. Require preservation of the original index as `claude.html`, generation of all three workbench assets, idempotent re-application, `--check` marker validation, localhost-only Viewer origin, safe origin checking, non-submitting prompt insertion, resizable/collapsible desktop panes, and mobile file/preview/Claude tabs.
- [ ] Run `node <local-webui-root>/test-integrated-workbench.mjs` and confirm failure because the patcher is absent.
- [ ] Implement an atomic, idempotent patcher. It must discover the single Vite JS/CSS entry in the original document, preserve that document as `claude.html`, and write a stable shell rather than editing the minified React bundle.
- [ ] Implement workbench CSS with `100dvh`, a stable toolbar, `minmax(0, 1fr)` tracks, a draggable split controlled by `--knowledge-width`, icon collapse controls, and `@media (max-width: 760px)` tab behavior.
- [ ] Implement workbench JavaScript that accepts `kb-active-file` only from `http://127.0.0.1:18081`, tracks the current file, switches Viewer URLs, opens an Ask-Claude dialog, inserts but never submits the composed prompt into the same-origin Claude textarea/contenteditable, and falls back to clipboard with a visible status.
- [ ] Run the Node tests, apply the patch to the installed package, then run the patcher with `--check`.

### Task 3: Startup integration and recovery

**Files:**
- Modify: `<local-webui-root>/webui-control`
- Modify: `<local-webui-root>/patch-dangerous-mode.mjs` only if its installed-file discovery conflicts with `claude.html`

- [ ] Add a failing test assertion that `webui-control start` checks both `patch-dangerous-mode.mjs --check` and `patch-integrated-workbench.mjs --check` before launch.
- [ ] Update `webui-control` with the second check while preserving localhost binding, environment propagation and knowledge-base cwd.
- [ ] Run both patcher tests and both `--check` commands.
- [ ] Restart with `<local-webui-root>/webui-control restart` and confirm `18080/`, `18080/claude.html`, `18081/viewer.html`, and `18081/graph-view.html` return HTTP 200.

### Task 4: Browser verification and documentation

**Files:**
- Modify: `<repo-root>/Web操作台部署完成报告.md`
- Modify: `<repo-root>/reports/2026-07-12_Web操作台部署完成报告.html`

- [ ] At 1440 x 900, verify the Viewer and Claude iframes are nonblank, current-file messages update the toolbar, file navigation renders Markdown, the divider changes pane width, collapse/restore works, and Ask Claude inserts the path/question without sending.
- [ ] Verify the Claude pane still exposes normal, plan, accept edits and dangerously skip permissions; confirm a new conversation initializes with cwd `<repo-root>`.
- [ ] At 390 x 844, verify file/preview/Claude tabs preserve iframe state and no controls overlap.
- [ ] Update both deployment reports to replace the old “no file tree” limitation with the integrated-workbench behavior, standalone fallback URLs, and reinstall recovery commands.
- [ ] Run knowledge-base contract tests, Node patch tests, health check, listener check and `git diff --check`.
- [ ] Commit only knowledge-base integration files, preserving the user's staged Markov/script changes and unrelated task-book/homepage changes.

### Task 5: Final handoff

- [ ] Confirm the workbench is live at `http://127.0.0.1:18080/` and both services listen only on `127.0.0.1`.
- [ ] Report the exact verification results, commit hash, standalone fallback URLs and any residual limitation.

### Task 6: Knowledge-only refresh control

**Files:**
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`

- [ ] Add a failing patcher contract requiring a `refreshKnowledge` icon button with `aria-label` and `title` set to `刷新知识库`, a handler that reloads `knowledgeFrame` without assigning or reloading `claudeFrame`, a temporary disabled state, and completion status text.
- [ ] Run `node <local-webui-root>/test-integrated-workbench.mjs` and confirm failure because the control is absent.
- [ ] Add the stable 32 px icon button beside `询问 Claude`; preserve the current Viewer URL, disable the button until the iframe `load` event, then show `知识库已刷新`.
- [ ] Apply the patch, restart 18080, and use Playwright to verify the Viewer document reloads while the Claude textarea value and current permission mode remain unchanged.
- [ ] Run both WebUI patch tests, both `--check` commands, listener and HTTP checks.

### Task 7: Mathematical authoring rule and health gate

**Files:**
- Modify: `<repo-root>/CLAUDE.md`
- Modify: `<repo-root>/scripts/check_health.py`
- Modify: `<repo-root>/tests/test_v3_scripts.py`
- Modify: `<repo-root>/pages/扩散模型 Diffusion Models DDPM.md`

- [ ] Add failing tests for an `undelimited_math_lines` helper: it must flag DDPM-style raw equations and LaTeX commands outside delimiters, while ignoring fenced code, inline code, URLs and valid `$...$`/`$$...$$` math.
- [ ] Run the focused health tests and confirm failure because the helper and E11 finding do not exist.
- [ ] Add the explicit LaTeX authoring rule to `CLAUDE.md` and implement conservative ERROR E11 detection in `check_health.py`.
- [ ] Rewrite the DDPM reference page formulas with inline/display LaTeX and run health check until E11 and all existing findings are clean.

### Task 8: Deterministic Viewer math extraction

**Files:**
- Modify: `<repo-root>/viewer.html`
- Modify: `<repo-root>/tests/test_viewer_contract.py`

- [ ] Add failing contract and browser cases for extraction/restoration of four delimiter types, exclusion of fenced/inline code, invalid-math survival and repeated page render.
- [ ] Replace direct delimiter substitutions with a math-region token store that runs before marked and restores after sanitize.
- [ ] Run Viewer tests and Playwright against the DDPM page; require nonzero inline/display KaTeX nodes and zero page errors.

### Task 9: Simple Claude Markdown rendering

**Files:**
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`

- [ ] Add failing patcher tests requiring pinned marked/DOMPurify assets, an assistant-only renderer, sanitizer use, disabled GFM tables/raw HTML, stable message-component replacement and dedicated Markdown styles.
- [ ] Implement the reproducible vendor-bundle patch and chat document assets without changing user/tool/system/thinking renderers.
- [ ] Apply and check the patch, then verify headings, emphasis, lists, links, inline/fenced code and blockquotes in an existing history; inject an unsafe HTML fixture and confirm it is removed.

### Task 10: Combined completion verification

- [ ] Verify the refresh control reloads the Viewer while preserving Claude textarea content and permission mode.
- [ ] Run Viewer contracts, v3 script tests, both WebUI patch tests, both patch checks, health check, HTTP/listener checks and `git diff --check`.
- [ ] Update Markdown and HTML deployment reports with the formula contract, refresh control and Claude Markdown support.
- [ ] Commit only task-owned knowledge-base files while preserving the user's staged and unrelated changes.
