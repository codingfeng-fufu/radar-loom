# Viewer Math and WebUI Bypass Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render TeX in the knowledge-base Viewer and add an explicit, non-persistent dangerous permission mode to the installed Claude Code WebUI.

**Architecture:** KaTeX runs after sanitized Markdown enters the Viewer DOM. A guarded local Node script reproducibly patches the installed WebUI frontend and backend bundles, while the control script verifies/applies the patch before service startup.

**Tech Stack:** HTML/CSS/JavaScript, KaTeX, Python unittest, Node.js, claude-code-webui SDK, Playwright CLI.

---

### Task 1: Viewer math contract

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html`

- [ ] Add failing assertions for `katex.min.css`, `katex.min.js`, `auto-render.min.js`, all four delimiter definitions, `renderMathInElement`, `trust: false`, and math rendering after `DOMPurify.sanitize`.
- [ ] Run `python3 -m unittest discover -s tests -p 'test_viewer_contract.py' -v`; expect the new math contract to fail.
- [ ] Add KaTeX assets, responsive math CSS and `renderMathInElement(elements.content, {delimiters, throwOnError:false, trust:false, strict:'warn'})` after sanitized Markdown insertion.
- [ ] Re-run the viewer contract; expect all tests to pass.

### Task 2: Reproducible WebUI patch

**Files:**
- Create: `/home/u2023312337/webui/patch-dangerous-mode.mjs`
- Create: `/home/u2023312337/webui/test-dangerous-mode.mjs`
- Modify: `/home/u2023312337/webui/webui-control`
- Modify: installed `claude-code-webui` frontend/backend bundles through the patch script.

- [ ] Write a Node test that runs the patch against fixture copies and asserts it adds the `bypassPermissions` option, warning text, mode-state predicate and backend `extraArgs` mapping; run it and expect failure because the patch script is absent.
- [ ] Implement a version-guarded, idempotent patcher using exact source fragments and atomic temp-file rename.
- [ ] Run the Node test twice and expect both runs to pass with identical second-run output.
- [ ] Add `node "$BASE/patch-dangerous-mode.mjs" --check` to `webui-control start`; patch application remains an explicit maintenance command, while startup refuses an unpatched bundle.
- [ ] Apply the patch, restart WebUI and confirm both bundle markers exist.

### Task 3: Runtime and browser verification

**Files:**
- Create temporary files only under `/tmp` or `.playwright-cli`, then remove them.

- [ ] Serve a temporary formula page through the knowledge-base server and use Playwright to assert inline/display KaTeX nodes, delimiter coverage, retained invalid formula and no horizontal page overflow.
- [ ] Use Playwright to assert the fourth mode is visible, default mode is not bypass, selecting it reveals the red warning, and refresh resets to default.
- [ ] Send one harmless API request with `bypassPermissions` and one with `default`; assert init/result success and the expected permission mode without file changes.
- [ ] Confirm ports 18080 and 18081 remain bound only to `127.0.0.1`.

### Task 4: Documentation and completion

**Files:**
- Modify: `Web操作台部署完成报告.md`
- Modify: `reports/2026-07-12_Web操作台部署完成报告.html`
- Modify: `docs/superpowers/plans/2026-07-13-viewer-math-webui-bypass.md`

- [ ] Document formula syntax, CDN dependency, fourth-mode behavior, security warning and patch replay command in both reports.
- [ ] Run the full unittest suite, health check, Node patch tests, browser checks, listener checks and `git diff --check`.
- [ ] Stage and commit only this task's knowledge-base files with `git commit --only`, leaving existing staged and unstaged user changes untouched.
- [ ] Audit every design requirement against current files and runtime evidence, then mark the active goal complete.
