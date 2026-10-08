# Web Console Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the local knowledge-base browsing and reporting layer around the existing chat WebUI while recording the unresolved 429 limitation accurately.

**Architecture:** A tmux control script runs Python's static HTTP server on localhost. A single HTML file fetches and safely renders repository Markdown, while repository policy and a self-contained deployment report document the operating model.

**Tech Stack:** Bash, Python `http.server`, HTML/CSS/JavaScript, marked, DOMPurify, highlight.js, Mermaid, Python unittest, Playwright.

---

### Task 1: Viewer behavior contract

**Files:**
- Create: `tests/test_viewer_contract.py`
- Create: `viewer.html`

- [x] Write tests that assert the required viewer functions, CDN libraries, default page, allowed-path policy, sanitizer, sidebar parser, frontmatter, wikilinks, highlighting, and Mermaid hooks.
- [x] Run the viewer contract test and confirm failure because `viewer.html` is absent.
- [x] Implement the single-file viewer with responsive sidebar, loading/error states, sanitized Markdown rendering and navigation.
- [x] Re-run the viewer contract tests and confirm they pass.

### Task 2: Static service control

**Files:**
- Create: `<local-webui-root>/kbserve-control`

- [x] Write a shell-level preflight that confirms the control script does not yet exist.
- [x] Implement `start`, `stop`, `restart`, `status`, and `logs` for a tmux-hosted `python3 -m http.server 18081 --bind 127.0.0.1 --directory <repo-root>` process.
- [x] Start the service and verify the listener and HTTP responses.

### Task 3: Repository policy and report convention

**Files:**
- Modify: `CLAUDE.md`
- Create: `reports/.gitkeep`
- Create: `reports/2026-07-12_Web操作台部署完成报告.html`
- Create: `Web操作台部署完成报告.md`

- [x] Add the viewer protection rule and dual Markdown/HTML report convention to `CLAUDE.md`.
- [x] Add the reports directory marker.
- [x] Produce Markdown and self-contained HTML reports with ports, forwarding, controls, viewer usage, report convention, verification results, 429 status and known limits.

### Task 4: End-to-end verification

**Files:**
- Modify only implementation/report files when verification exposes a defect.

- [x] Run existing unit tests, viewer tests, `scripts/check_health.py`, and shell syntax checks.
- [x] Use a real browser to verify the viewer on desktop and mobile, including navigation, Mermaid, frontmatter and `../` rejection.
- [x] Verify both listeners are localhost-only and capture final service status.
- [x] Review the diff without reverting the user's pre-existing `首页.md` change or modifying the supplemental task book.
- [x] Commit the knowledge-base deliverables with a scoped commit.
