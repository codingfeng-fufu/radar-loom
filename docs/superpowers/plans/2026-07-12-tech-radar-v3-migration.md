# Technical Radar v3 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing technical-radar knowledge base to the approved v3 retrieval-first, traceable-ingestion design without losing the 88 existing concept pages.

**Architecture:** Keep Markdown as the source of truth and Python standard-library scripts as deterministic derived-data and validation tools. Extend the shared parser/constants, generate a committed `_index.md`, generate ignored overview and eight tag graphs, and make page creation plus health checks enforce summaries and reachable sources.

**Tech Stack:** Python 3.10+ standard library, Markdown/frontmatter, Mermaid, Git, `unittest`.

---

### Task 1: Migration safety snapshot

**Files:**
- Track: all current files not ignored by `.gitignore`

- [ ] Inspect `git status --short` and confirm the 88 concept pages and v3 specification are present.
- [ ] Run the current `render_graph.py` and `check_health.py` once and retain their output in the session record.
- [ ] Commit the complete pre-migration state with `git add -A && git commit -m "wip: 迁移前全量快照(含88个未跟踪概念页原始状态)"`.
- [ ] Verify the snapshot with `git show --stat --oneline HEAD`.

### Task 2: Specify script behavior with standard-library tests

**Files:**
- Create: `tests/test_v3_scripts.py`

- [ ] Add `unittest` coverage for `parse_source`, eight category mappings, CoMaGRAG as a legal project tag, deterministic index rendering, local-source validation, summary validation, graph full/overview statistics, one-hop external nodes, restored broken-link reporting, and no-op `--help` behavior.
- [ ] Run `python3 -m unittest tests/test_v3_scripts.py -v` and confirm the v3 assertions fail against the v2/current implementation.

### Task 3: Normalize PDF names and static structure

**Files:**
- Rename: the five `papers/* (N).pdf` files to underscore names matching frontmatter and `_images/` directories
- Modify: `.gitignore`
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `首页.md`
- Modify: `templates/概念页模板.md`
- Create: `pages/机器学习与NLP基础 ML-NLP Foundations.md`
- Create: `pages/评测方法 Evaluation Methods.md`

- [ ] Rename all five PDFs with `mv` and verify the four referenced source paths plus the interview PDF exist under normalized names.
- [ ] Replace `CLAUDE.md` exactly with v3 section 5.
- [ ] Apply the five README revisions from v3 section 6, keeping it the user-facing workflow source and referring detailed CC behavior to `CLAUDE.md`.
- [ ] Add `_index.md` and the two MOC pages to `首页.md` classification entry points.
- [ ] Replace the concept template with v3 section 7, including the required `摘要` field.
- [ ] Consolidate ignored graph outputs to `graph*.md` while preserving PDF ignore rules.

### Task 4: Upgrade shared behavior and index generation

**Files:**
- Modify: `scripts/radar_common.py`
- Create: `scripts/build_index.py`

- [ ] Extend category/project constants and mappings exactly as v3 section 10.1 specifies.
- [ ] Add `INDEX_FILE`, the eight deterministic graph paths, and `parse_source(value)`.
- [ ] Implement `build_index.py` with argparse, pure `render_index(pages)` output, the eight fixed category sections, a project section, summary placeholders, deterministic ordering, and the specified stdout line.
- [ ] Run the focused common/index tests and confirm they pass.

### Task 5: Rewrite graph rendering

**Files:**
- Modify: `scripts/render_graph.py`

- [ ] Add argparse so help and invalid arguments never render files.
- [ ] Compute full-vault edges, degrees, isolated nodes, and broken links once.
- [ ] Render `graph.md` with separate full-vault and top-15 overview statistics, valid Markdown links to all eight tag graphs, full-vault isolated nodes, and a broken-link section when needed.
- [ ] Render each category graph with tagged seed nodes plus their one-hop neighbors; mark non-seed neighbors with Mermaid class `ext` and omit subgraph-local isolation claims.
- [ ] Print one status line per graph and a final full-vault summary.
- [ ] Run focused graph tests and inspect generated Markdown headers.

### Task 6: Upgrade page creation and health checks

**Files:**
- Modify: `scripts/new_page.py`
- Modify: `scripts/check_health.py`

- [ ] Add required `--summary` and optional `--force-source` arguments to page creation.
- [ ] Validate summary length/content and source type/path before writing; populate `摘要`; refresh the index through `build_index.main([])` after success.
- [ ] Add argparse to health checking and retain E1-E7/W1-W2 behavior.
- [ ] Add E8 by comparing `_index.md` to the exact expected `build_index.render_index()` output.
- [ ] Add E9 for unknown or missing local sources, E10 for missing summaries, and W3 for summaries longer than 60 characters.
- [ ] Run focused creation/health tests and then the complete `unittest` file.

### Task 7: Migrate summaries, confidence, and tags

**Files:**
- Modify: 88 existing concept pages in `pages/`

- [ ] Process pages in deterministic filename order and insert one concrete summary of at most 60 Chinese characters before `来源`.
- [ ] Reclassify clearly foundational ML/DL/NLP pages to include `基础` and clearly evaluation/statistics pages to include `评测`, removing only the demonstrably misapplied category tags.
- [ ] Apply the v3 confidence rule: foundational consensus pages retain high confidence; other lecture-PDF high-confidence pages become medium; existing medium confidence remains medium.
- [ ] Inspect GSAD, ChronoLink, and CoMaGRAG references/tags and record ambiguous project-tag decisions instead of inventing relationships.
- [ ] Run `build_index.py` and `check_health.py` after each batch of at most 30 pages; require no E8/E9/E10 before continuing.

### Task 8: Full acceptance and completion commit

**Files:**
- Generate/track: `_index.md`
- Generate/ignore: `graph.md`, `graph_*.md`

- [ ] Verify all four executable scripts show help without business side effects and reject unknown arguments with exit 2.
- [ ] Verify `_index.md` is tracked, contains all concept pages, and contains no `(缺摘要)`.
- [ ] Run `python3 scripts/check_health.py` and require ERROR 0.
- [ ] Run `python3 scripts/render_graph.py` and require one overview plus eight category graph files.
- [ ] Inject a temporary broken link with `apply_patch`, verify it appears in stdout and `graph.md`, then remove it with `apply_patch` and rerun cleanly.
- [ ] Verify the RAG graph connects `GNN-RAG 图神经网络检索增强` to at least one external gray neighbor.
- [ ] Exercise `new_page.py` in a temporary copy of the vault: missing local source exits 2; `--force-source` succeeds; successful creation refreshes `_index.md`.
- [ ] Simulate one index hit and one index miss by reading `_index.md` under the new `CLAUDE.md` protocol and record the observed response requirements.
- [ ] Run `python3 -m unittest discover -s tests -v`, `python3 scripts/build_index.py`, `python3 scripts/render_graph.py`, and `python3 scripts/check_health.py` as the final verification sequence.
- [ ] Commit with `git add -A && git commit -m "radar: v3 迁移完成——检索索引/摄入协议/来源修复/88页入库"`.
- [ ] Verify `git status --short --untracked-files=all` is clean except ignored generated/PDF assets and capture pre/post `git log --oneline` for the delivery report.

### Task 9: Delivery record

**Files:**
- No additional product files unless an implementation deviation must be documented

- [ ] Report the before/after Git log, each acceptance result, any ambiguous tag decisions left unchanged, the five intentionally untouched project placeholders, and every deviation from v3 (or explicitly state none).
