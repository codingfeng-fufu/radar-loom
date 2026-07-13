# Interactive Knowledge Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a polished, full-screen Cytoscape knowledge-graph workspace backed by deterministic repository data.

**Architecture:** `render_graph.py` produces `graph-data.json` from the same parsed pages and edges used by Mermaid. A standalone `graph-view.html` loads that JSON and delegates layout/rendering to Cytoscape.js with fCoSE while implementing repository-specific search, filters, focus and Viewer navigation.

**Tech Stack:** Python 3.11, unittest, JSON, HTML/CSS/JavaScript, Cytoscape.js, cytoscape-fcose, Playwright CLI.

---

### Task 1: Structured graph data

**Files:**
- Modify: `tests/test_v3_scripts.py`
- Modify: `scripts/radar_common.py`
- Modify: `scripts/render_graph.py`
- Create: `graph-data.json`

- [ ] Add failing tests for `GRAPH_DATA_FILE`, deterministic `render_graph_data`, 102+ nodes, valid edge references, stable sorting, node kinds and required metadata.
- [ ] Run `python3 -m unittest tests/test_v3_scripts.py -v` through discovery and confirm the new tests fail because the JSON API is absent.
- [ ] Implement category colors, node kind/category selection and deterministic JSON rendering; write `graph-data.json` from `render_graph.main`.
- [ ] Run the graph tests and generate the current data file.

### Task 2: Graph workspace contract

**Files:**
- Create: `tests/test_graph_view_contract.py`
- Create: `graph-view.html`

- [ ] Add failing contract tests for Cytoscape/fCoSE assets, full-screen stable layout, search, category/project filters, neighbor focus, details, Viewer links, safe `textContent`, loading/error/empty states and mobile drawers.
- [ ] Run the contract test and confirm failure because `graph-view.html` is absent.
- [ ] Implement the workspace with Cytoscape styles, fCoSE layout, search suggestions, composable filters, one-hop focus, selection details and responsive panels.
- [ ] Run the contract tests and full Python tests.

### Task 3: Integration and documentation

**Files:**
- Modify: `viewer.html`
- Modify: `README.md`
- Modify: `Web操作台部署完成报告.md`
- Modify: `reports/2026-07-12_Web操作台部署完成报告.html`

- [ ] Add an “交互图谱” command in Viewer navigation without changing generated `_index.md`.
- [ ] Document the graph URL, controls, data regeneration and Mermaid fallback in README and both deployment reports.
- [ ] Regenerate graph artifacts and verify deterministic output on a second run.

### Task 4: Browser and completion verification

**Files:**
- Modify implementation files only when verification exposes a defect.

- [ ] Use Playwright at 1440×900 to verify nonblank canvas pixels, node/edge counts, search, filter, focus, details, Viewer link and layout controls.
- [ ] Use Playwright at 390×844 to verify filter drawer, bottom details, stable canvas and no incoherent overlap.
- [ ] Run full tests in an isolated committed-state worktree with ignored PDF sources linked read-only, plus health, listener and diff checks.
- [ ] Commit only this task's files with `git commit --only`, preserving the user's staged Markov/script changes and unstaged homepage/task-book changes.
