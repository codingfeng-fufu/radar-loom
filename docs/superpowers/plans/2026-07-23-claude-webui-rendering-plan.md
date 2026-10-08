# Claude WebUI Rendering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply the approved C-direction visual system consistently to Claude conversation, history, loading, error, tool, permission, and context states.

**Architecture:** Keep Claude's request/session protocol unchanged. Extend the existing `patch-integrated-workbench.mjs` frontend patch with stable semantic classes and a single scoped CSS theme, add only small rendering helpers where current bundled markup cannot expose required states, then regenerate the deployed static bundle through the existing patch/check scripts.

**Tech Stack:** Claude Code WebUI bundled React asset, Node.js patch scripts, CSS, Playwright, Node assertion tests.

---

### Task 1: Lock the rendering contract

**Files:**
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs` only after the test is red

- [ ] **Step 1: Add failing assertions** for the deployed patch source to contain the C-direction root classes, history state classes, tool summary/detail classes, context bar class, permission-state classes, responsive constraints, and Markdown renderer hook.
- [ ] **Step 2: Run `node <local-webui-root>/test-integrated-workbench.mjs` and verify the new assertions fail for the missing contract.
- [ ] **Step 3:** Keep the assertions focused on observable class names and behavior, not minified implementation offsets.

### Task 2: Add the unified Claude visual layer

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`

- [ ] **Step 1: Add scoped theme variables and layout rules for `.claude-shell`, `.claude-header`, `.claude-thread`, `.claude-composer`, and `.claude-context-bar` using the approved gray-green/white palette, 6-8px radii, readable max width, independent message scrolling, and mobile wrapping.
- [ ] **Step 2: Add styles for `.claude-user-message`, `.claude-assistant-message`, `.claude-markdown`, headings, lists, tables, blockquotes, inline code, fenced code, and horizontal overflow.
- [ ] **Step 3: Add consistent styles for `.claude-tool-summary`, `.claude-tool-detail`, `.claude-status-running`, `.claude-status-success`, `.claude-status-warning`, `.claude-status-error`, `.claude-permission-panel`, and `.claude-danger-panel`.
- [ ] **Step 4: Add history, empty, loading, and error state styles that share the same surfaces and typography without nesting decorative cards.
- [ ] **Step 5:** Run the patch script in check mode and the contract test.

### Task 3: Expose tool, permission, and context semantics

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Test: `<local-webui-root>/test-integrated-workbench.mjs`

- [ ] **Step 1: Add a failing test that verifies the patch output contains semantic wrappers for tool summaries/details, permission prompts, dangerous mode, and knowledge context.
- [ ] **Step 2: Patch the existing minified render fragments to add those classes while preserving event handlers, request payloads, and permission callbacks.
- [ ] **Step 3: Ensure context text remains dismissible and does not alter the current `kb-context` message protocol.
- [ ] **Step 4: Run the focused Node test and verify the generated static bundle contains the same classes.

### Task 4: Improve history and state feedback

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Test: `<local-webui-root>/test-integrated-workbench.mjs`

- [ ] **Step 1: Add a failing contract for history rows, recent-session loading, empty history, and retry/error state selectors.
- [ ] **Step 2: Add class hooks and visual rules to the existing history markup without changing history API paths or session IDs.
- [ ] **Step 3: Ensure the project path and session metadata remain readable on desktop and mobile.
- [ ] **Step 4: Run the history regression flow against `/api/projects/<encoded>/histories` and confirm recent sessions remain visible.

### Task 5: Regenerate and visually verify the deployed UI

**Files:**
- Modify: generated WebUI static assets under `<local-webui-root>/app/node_modules/claude-code-webui/dist/static/`
- Do not modify: knowledge-base Markdown, graph data, or Claude session files

- [ ] **Step 1: Run `node <local-webui-root>/patch-integrated-workbench.mjs` and its check mode.
- [ ] **Step 2: Restart `<local-webui-root>/webui-control` and verify `http://127.0.0.1:18080/` loads.
- [ ] **Step 3: Use Playwright at desktop and mobile widths to verify conversation Markdown, code block overflow, tool expansion, permission panel, history list, loading state, and error state.
- [ ] **Step 4: Capture screenshots under `output/playwright/` and inspect for overlap, clipping, unreadable contrast, and input-bar obstruction.
- [ ] **Step 5: Run `node <local-webui-root>/test-integrated-workbench.mjs`, `node <local-webui-root>/test-dangerous-mode.mjs`, and the repository test suite.

### Task 6: Final verification and handoff

**Files:**
- Review only: `git diff`, WebUI logs, generated asset status

- [ ] **Step 1: Confirm `webui-control status` and `kbserve-control status` are healthy.
- [ ] **Step 2: Confirm the history API returns recent knowledge-base sessions and opening one preserves the current layout.
- [ ] **Step 3: Run `python3 scripts/check_health.py` to ensure the UI work did not change knowledge-base artifacts.
- [ ] **Step 4: Report changed WebUI files, browser verification results, and any remaining visual limitations.
