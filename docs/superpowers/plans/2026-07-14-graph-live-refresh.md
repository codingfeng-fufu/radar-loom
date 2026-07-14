# Graph Live Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the graph and generated index update reliably after knowledge-page edits, both from the workbench refresh button and while the graph view remains open.

**Architecture:** Replace the plain static server with a localhost-only Python server that exposes fixed refresh and revision endpoints while preserving static-file behavior. The workbench calls the refresh endpoint before reloading its knowledge iframe, and the graph view polls the revision endpoint and replaces its Cytoscape data only when the revision changes.

**Tech Stack:** Python 3 standard library, existing index/graph scripts, vanilla browser JavaScript, Cytoscape.js, Node contract tests, Python `unittest`, Playwright CLI.

---

### Task 1: Local knowledge server

**Files:**
- Create: `scripts/serve_kb.py`
- Create: `tests/test_serve_kb.py`

- [ ] Write failing tests for source freshness detection, forced rebuild, automatic stale rebuild, stable revision values, localhost CORS, and failed generator responses.
- [ ] Run `python3 -m unittest tests.test_serve_kb -v` and confirm failures are caused by the missing `serve_kb` module.
- [ ] Implement `KnowledgeBuilder`, `KnowledgeRequestHandler`, and CLI arguments `--host`, `--port`, and `--directory` using only the standard library.
- [ ] Run `python3 -m unittest tests.test_serve_kb -v` and confirm all server tests pass.

### Task 2: Graph live reload contract

**Files:**
- Modify: `graph-view.html`
- Modify: `tests/test_graph_view_contract.py`

- [ ] Add failing contract assertions for `/api/revision`, a 4-second polling interval, guarded refresh concurrency, Cytoscape instance replacement, and `kb-refresh` message handling.
- [ ] Run `python3 -m unittest tests.test_graph_view_contract -v` and confirm the new assertions fail.
- [ ] Refactor graph loading into `loadGraph()`, destroy the previous Cytoscape instance before replacement, record the current revision, and poll for changes without relayout when unchanged.
- [ ] Add the trusted-parent `kb-refresh` listener and preserve the existing error screen for initial-load failures.
- [ ] Run `python3 -m unittest tests.test_graph_view_contract -v` and confirm the graph contract passes.

### Task 3: Workbench refresh protocol

**Files:**
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`

- [ ] Add failing assertions that the refresh handler POSTs `/api/refresh`, checks `response.ok`, reports a failure without reloading, and sends `kb-refresh` only after success.
- [ ] Run `node /home/u2023312337/webui/test-integrated-workbench.mjs` and confirm the new assertions fail.
- [ ] Implement the async refresh handler and update the patch-completeness marker so existing installations receive the new workbench JavaScript.
- [ ] Run the Node test and both patch idempotence checks.

### Task 4: Service control and documentation

**Files:**
- Modify: `/home/u2023312337/webui/kbserve-control`
- Modify: `Web操作台使用与维护说明书.md`
- Modify: `tests/test_web_console_manual.py`

- [ ] Add failing documentation assertions for automatic graph refresh and the fixed refresh API behavior.
- [ ] Update `kbserve-control` to run `python3 scripts/serve_kb.py --host 127.0.0.1 --port 18081 --directory /home/u2023312337/知识库`.
- [ ] Document refresh timing, manual refresh semantics, and troubleshooting output without exposing credentials.
- [ ] Run documentation and service CLI tests.

### Task 5: End-to-end verification

**Files:**
- Regenerate as needed: `_index.md`, `graph-data.json`, `graph.md`, `graph_*.md`

- [ ] Run the complete Python, health, WebUI patch, dangerous-mode, dedicated-config, and diff checks.
- [ ] Restart both localhost services and verify ports `18080` and `18081` bind only to `127.0.0.1`.
- [ ] Use Playwright to open the graph, create a temporary valid knowledge page, wait for the node count to increase automatically, then remove the page and verify the count returns.
- [ ] Verify the manual refresh button rebuilds generated files before reloading and reports no console errors.
- [ ] Commit repository changes, merge to `master`, rerun the full verification on the merged result, clean the worktree, and leave both services running.
