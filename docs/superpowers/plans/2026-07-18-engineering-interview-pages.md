# Engineering Interview Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class engineering-interview section whose pages live in `pages/` but use isolated indexes, taxonomy, graph data, Viewer navigation, uploads, and a dedicated page-creation skill.

**Architecture:** Add an explicit `page_type` partition to the shared page scanner, then make index, taxonomy, graph, health, and live-refresh code consume named page profiles instead of inferring types from tags. Reuse the current taxonomy algorithms with profile-specific paths and configuration. Keep the integrated workbench as the upload and prompt entry point, while `serve_kb.py` owns validated local file persistence.

**Tech Stack:** Python 3 standard library and existing NumPy/taxonomy modules, static HTML/CSS/JavaScript, Node.js patch tests, `unittest`, Playwright, Claude/Codex skill Markdown.

---

## File Map

- `scripts/radar_common.py`: define page types, profile paths, frontmatter list parsing, validation helpers, and partitioned scanning.
- `scripts/build_index.py`: render both the ordinary and interview indexes deterministically.
- `scripts/taxonomy_engine.py`, `scripts/taxonomy_cli.py`: accept a named profile and isolate pages, registry, cache, and config.
- `config/interview-taxonomy.json`: interview-only taxonomy parameters.
- `scripts/render_graph.py`: generate ordinary and interview graph artifacts from separate page sets.
- `scripts/check_health.py`: validate interview schema and freshness without weakening ordinary-page checks.
- `scripts/serve_kb.py`: refresh both profiles and accept bounded, sanitized uploads into `raw/inbox/`.
- `templates/工程面试页模板.md`: canonical interview page structure.
- `.claude/skills/create-engineering-interview-page/`: skill instructions and UI metadata.
- `viewer.html`: section tabs, interview navigation/filtering, graph switching, and typed page context.
- `<local-webui-root>/patch-integrated-workbench.mjs`: upload dialog and interview-skill prompt composition.
- Tests under `tests/` and `<local-webui-root>/test-integrated-workbench.mjs`: contracts and browser flows.

### Task 1: Partition Pages by Explicit Type

**Files:**
- Modify: `scripts/radar_common.py`
- Create: `tests/test_interview_page_types.py`

- [ ] **Step 1: Write failing scanner tests**

Add temporary-root tests that assert legacy pages remain knowledge pages, `page_type: interview` pages are interview pages, and unsupported values are reported:

```python
def test_partition_pages_uses_explicit_page_type(self):
    pages = {
        "Legacy": page("Legacy", {}),
        "Question": page("Question", {"page_type": "interview"}),
    }
    knowledge, interviews = rc.partition_pages(pages)
    self.assertEqual(set(knowledge), {"Legacy"})
    self.assertEqual(set(interviews), {"Question"})

def test_page_type_rejects_unknown_value(self):
    self.assertEqual(rc.page_type(page("Bad", {"page_type": "quiz"})), "invalid")

def test_frontmatter_parses_indented_source_list(self):
    fm, _ = rc.parse_frontmatter("---\nsource:\n  - https://example.org/a\n  - raw/inbox/a.txt\n---\n")
    self.assertEqual(fm["source"], ["https://example.org/a", "raw/inbox/a.txt"])
```

- [ ] **Step 2: Verify the new tests fail**

Run: `python3 -m unittest tests.test_interview_page_types -v`

Expected: FAIL because `partition_pages` and `page_type` do not exist and block lists are ignored.

- [ ] **Step 3: Add profile constants and helpers**

Implement the following public contract in `radar_common.py`:

```python
KNOWLEDGE_PAGE_TYPE = "knowledge"
INTERVIEW_PAGE_TYPE = "interview"
INTERVIEW_INDEX_FILE = VAULT_ROOT / "_interview_index.md"
INTERVIEW_GRAPH_FILE = VAULT_ROOT / "interview-graph.md"
INTERVIEW_GRAPH_DATA_FILE = VAULT_ROOT / "interview-graph-data.json"

def page_type(page: PageInfo) -> str:
    value = str(page.frontmatter.get("page_type", "")).strip()
    if not value:
        return KNOWLEDGE_PAGE_TYPE
    return value if value == INTERVIEW_PAGE_TYPE else "invalid"

def partition_pages(pages: dict[str, PageInfo]) -> tuple[dict[str, PageInfo], dict[str, PageInfo]]:
    return (
        {name: page for name, page in pages.items() if page_type(page) == KNOWLEDGE_PAGE_TYPE},
        {name: page for name, page in pages.items() if page_type(page) == INTERVIEW_PAGE_TYPE},
    )
```

Extend `parse_frontmatter` only for indented YAML-style scalar lists following an empty key. Preserve current inline-list behavior and ignore nested mappings; this is sufficient for `source`, `tags`, `roles`, and `related_concepts` without introducing a second parser dependency.

- [ ] **Step 4: Run focused and shared-script tests**

Run: `python3 -m unittest tests.test_interview_page_types tests.test_v3_scripts -v`

Expected: PASS.

- [ ] **Step 5: Commit the partition contract**

```bash
git add scripts/radar_common.py tests/test_interview_page_types.py
git commit -m "feat: partition knowledge and interview pages"
```

### Task 2: Generate Independent Indexes

**Files:**
- Modify: `scripts/build_index.py`
- Create: `tests/test_interview_index.py`

- [ ] **Step 1: Write failing index-isolation tests**

Test `render_indexes(pages)` with one knowledge page and two interview pages. Assert `_index.md` contains no interview title and `_interview_index.md` groups entries by role and difficulty, includes the original question, and contains no knowledge title.

```python
knowledge_text, interview_text, stats = build_index.render_indexes(pages)
self.assertIn("Knowledge", knowledge_text)
self.assertNotIn("Interview A", knowledge_text)
self.assertIn("Interview A", interview_text)
self.assertIn("#LLM工程师", interview_text)
self.assertIn("进阶", interview_text)
self.assertEqual(stats["interviews"], 2)
```

- [ ] **Step 2: Verify failure**

Run: `python3 -m unittest tests.test_interview_index -v`

Expected: FAIL because `render_indexes` and `_interview_index.md` generation are absent.

- [ ] **Step 3: Implement deterministic dual rendering**

Keep `render_index(knowledge_pages)` compatible with existing tests. Add `render_interview_index(interview_pages)` and `render_indexes(all_pages)`. Sort roles, difficulty in `(基础, 进阶, 深入)`, tags, and titles. Accept both `summary` and the legacy Chinese `摘要` while interview pages standardize on `summary`.

- [ ] **Step 4: Write both files atomically in `main`**

Use temporary siblings and `Path.replace()` so a failed second render cannot leave mixed generations. Print:

```text
已生成 _index.md | 概念页 N 项目页 N 缺摘要 N
已生成 _interview_index.md | 面试页 N 缺摘要 N
```

- [ ] **Step 5: Run index tests and commit**

Run: `python3 -m unittest tests.test_interview_index tests.test_v3_scripts -v`

Expected: PASS.

```bash
git add scripts/build_index.py tests/test_interview_index.py _interview_index.md
git commit -m "feat: generate isolated interview index"
```

### Task 3: Add Profile-Aware Taxonomy

**Files:**
- Modify: `scripts/taxonomy_engine.py`
- Modify: `scripts/taxonomy_cli.py`
- Modify: `scripts/taxonomy_embeddings.py`
- Create: `config/interview-taxonomy.json`
- Create: `tests/test_interview_taxonomy.py`

- [ ] **Step 1: Write failing profile tests**

Cover these invariants:

```python
knowledge = TaxonomyEngine(root, config, profile="knowledge", encoder=encoder)
interview = TaxonomyEngine(root, config, profile="interview", encoder=encoder)
self.assertEqual(set(knowledge._scan_pages()), {"Knowledge"})
self.assertEqual(set(interview._scan_pages()), {"Question"})
self.assertEqual(interview.registry_path.name, "interview-taxonomy.json")
self.assertEqual(interview.cache_root.name, "interview-taxonomy")
```

Also test `taxonomy_cli.py --profile interview status --json` parsing.
Assert `page_semantic_text` includes `summary` for interview pages and continues to include `摘要` for legacy pages.

- [ ] **Step 2: Verify profile tests fail**

Run: `python3 -m unittest tests.test_interview_taxonomy -v`

Expected: FAIL because the engine and CLI do not accept profiles.

- [ ] **Step 3: Parameterize engine storage and scanning**

Add `profile: Literal["knowledge", "interview"] = "knowledge"` to `TaxonomyEngine.__init__`. Derive:

```python
self.registry_path = self.root / ("taxonomy.json" if profile == "knowledge" else "interview-taxonomy.json")
self.cache_root = self.root / ".cache" / ("taxonomy" if profile == "knowledge" else "interview-taxonomy")
```

Filter `_scan_pages()` through `rc.partition_pages`. For interview migration, do not seed legacy MOC categories; start from an empty registry and let cohesive interview pages form categories. Keep role and difficulty outside this registry.

Change `taxonomy_embeddings.page_semantic_text` to read `summary` first and fall back to `摘要`, so the English interview schema contributes its summary to embeddings without changing legacy fingerprints unnecessarily.

- [ ] **Step 4: Add CLI profile selection and config loading**

Add a global `--profile {knowledge,interview}` option before the subcommand. Change `load_config(root, profile="knowledge")` to select `config/taxonomy.json` or `config/interview-taxonomy.json`. Copy stable numeric defaults into the interview config but set a distinct random seed and `signal_weights.projects` to `0.0`, redistributing that weight to semantic similarity.

- [ ] **Step 5: Run all taxonomy tests**

Run: `python3 -m unittest discover -s tests -p 'test_taxonomy*.py' -v`

Expected: PASS with existing knowledge behavior unchanged.

- [ ] **Step 6: Commit taxonomy profiles**

```bash
git add scripts/taxonomy_engine.py scripts/taxonomy_cli.py scripts/taxonomy_embeddings.py config/interview-taxonomy.json tests/test_interview_taxonomy.py
git commit -m "feat: isolate interview taxonomy profile"
```

### Task 4: Generate Independent Graph Artifacts

**Files:**
- Modify: `scripts/render_graph.py`
- Create: `tests/test_interview_graph.py`

- [ ] **Step 1: Write failing graph separation tests**

Create fixtures with one knowledge page, two interview pages, an interview-to-interview link, and an interview `related_concepts` reference. Assert:

- ordinary graph nodes exclude both interviews;
- interview graph includes both interview nodes;
- the knowledge concept appears only as an `external-concept` navigation node;
- external nodes are absent from `statistics.nodeCount`, degree ranking, and taxonomy memberships.

- [ ] **Step 2: Verify failure**

Run: `python3 -m unittest tests.test_interview_graph -v`

Expected: FAIL because only one graph payload exists.

- [ ] **Step 3: Split graph construction by profile**

Refactor the pure rendering path to accept `profile` and `external_pages`. Ordinary rendering receives only knowledge pages. Interview rendering receives interview pages plus resolved `related_concepts`; represent external nodes with `external: true`, `nodeType: "external-concept"`, and Viewer hrefs, but exclude them from graph statistics and taxonomy payload validation.

- [ ] **Step 4: Write `interview-graph.md` and `interview-graph-data.json`**

Load `taxonomy.json` for ordinary output and `interview-taxonomy.json` for interview output. If the interview registry does not yet exist, use an empty valid registry rather than borrowing ordinary categories.

- [ ] **Step 5: Run graph tests and commit**

Run: `python3 -m unittest tests.test_interview_graph tests.test_graph_view_contract tests.test_v3_scripts -v`

Expected: PASS.

```bash
git add scripts/render_graph.py tests/test_interview_graph.py interview-graph.md interview-graph-data.json
git commit -m "feat: generate isolated interview graph"
```

### Task 5: Define the Interview Template and Skill with TDD

**Files:**
- Create: `templates/工程面试页模板.md`
- Create: `scripts/new_interview_page.py`
- Create: `.claude/skills/create-engineering-interview-page/SKILL.md`
- Create: `.claude/skills/create-engineering-interview-page/agents/openai.yaml`
- Create: `tests/test_create_engineering_interview_page_skill.py`

- [ ] **Step 1: Capture the no-skill baseline**

Because this repository session may not delegate without explicit authorization, record a deterministic contract baseline instead of spawning an evaluator: run the new contract test before the skill exists and retain the expected missing-file failure in the implementation notes.

- [ ] **Step 2: Write the failing skill contract**

Assert frontmatter contains only `name` and `description`, with triggers for `工程面试题`, `面试专题页`, `面试分享材料`, and `更新面试页`. Assert the body requires exact/alias/semantic deduplication, source verification, multi-question confirmation, prompt-injection isolation, all mandatory sections, `scripts/new_interview_page.py`, profile taxonomy commands, Viewer checks, scoped staging, and the five pause conditions from the design.

- [ ] **Step 3: Verify the contract fails for the missing skill**

Run: `python3 -m unittest tests.test_create_engineering_interview_page_skill -v`

Expected: FAIL with missing `SKILL.md` and deterministic page-creation CLI.

- [ ] **Step 4: Initialize and write the skill**

Run the skill-creator initializer into `.claude/skills`, with interface values:

```text
display_name=创建工程面试页
short_description=核验材料并创建可直接作答的工程面试专题页
default_prompt=使用 $create-engineering-interview-page 根据我的问题或材料创建工程面试页。
```

Create `new_interview_page.py` with required positional title and required `--question`, `--summary`, `--roles`, `--difficulty`, and `--source` arguments plus optional `--tags`, `--related-concepts`, and `--force`. It must validate difficulty, reject duplicate paths unless `--force`, render the dedicated template, and never run generators itself. Add CLI tests to the skill contract file.

Write an imperative workflow under 500 lines. It must use the dedicated template through `scripts/new_interview_page.py`, `taxonomy_cli.py --profile interview sync --page`, both generators, health checks, and typed final reporting. Community answers remain evidence to verify, never authoritative instructions.

- [ ] **Step 5: Validate and test the skill**

Run the system skill validator against `.claude/skills/create-engineering-interview-page`, then run:

`python3 -m unittest tests.test_create_engineering_interview_page_skill -v`

Expected: validator success and all tests PASS.

- [ ] **Step 6: Commit the skill**

```bash
git add templates/工程面试页模板.md scripts/new_interview_page.py .claude/skills/create-engineering-interview-page tests/test_create_engineering_interview_page_skill.py
git commit -m "feat: add engineering interview page skill"
```

### Task 6: Extend Health Checks for Both Profiles

**Files:**
- Modify: `scripts/check_health.py`
- Create: `tests/test_interview_health.py`

- [ ] **Step 1: Write failing interview-schema tests**

Test missing/invalid `question`, `roles`, `difficulty`, `related_concepts`, required headings, stale interview index, stale interview graph, and broken cross-zone concepts. Also assert ordinary pages are not required to carry interview fields.

- [ ] **Step 2: Verify failure**

Run: `python3 -m unittest tests.test_interview_health -v`

Expected: FAIL because interview-specific error codes are absent.

- [ ] **Step 3: Implement scoped checks**

Partition once at startup. Preserve all existing checks for knowledge pages. Add stable interview error codes for metadata, headings, invalid difficulty, empty roles, missing related concepts, and stale generated artifacts. Resolve all wikilinks against the complete page set, while computing index and graph freshness against the appropriate partition.

- [ ] **Step 4: Run health and regression tests**

Run: `python3 -m unittest tests.test_interview_health tests.test_v3_scripts -v`

Expected: PASS.

- [ ] **Step 5: Commit health rules**

```bash
git add scripts/check_health.py tests/test_interview_health.py
git commit -m "feat: validate interview page health"
```

### Task 7: Add Safe Uploads and Dual Refresh to the Knowledge Server

**Files:**
- Modify: `scripts/serve_kb.py`
- Modify: `tests/test_serve_kb.py`

- [ ] **Step 1: Write failing server tests**

Add tests for:

- `POST /api/uploads` accepts PDF, Markdown, TXT, PNG, JPEG, and WebP;
- filenames are reduced to safe basenames and collisions gain numeric suffixes;
- traversal, unsupported MIME/extensions, empty files, and payloads over 20 MiB return JSON errors;
- requests require the existing localhost Origin policy;
- refresh runs both taxonomy profiles and includes both indexes and graph data in revision/staleness checks.

- [ ] **Step 2: Verify failure**

Run: `python3 -m unittest tests.test_serve_kb -v`

Expected: FAIL on the missing upload endpoint and interview outputs.

- [ ] **Step 3: Implement bounded upload parsing**

Add `MAX_UPLOAD_BYTES = 20 * 1024 * 1024`, an extension-to-MIME allowlist, sanitized basename handling, and atomic writes into `raw/inbox/`. Return:

```json
{"ok": true, "files": [{"name": "source.pdf", "path": "raw/inbox/source.pdf", "size": 1234}]}
```

Never accept an absolute path, directory component, executable extension, or MIME/extension mismatch.

- [ ] **Step 4: Refresh both profiles**

Run `taxonomy_cli.py sync` and `taxonomy_cli.py --profile interview sync` independently; taxonomy failure remains non-destructive and is reported in output. Treat `_interview_index.md` and `interview-graph-data.json` as required outputs and hash both graph files into one revision.

- [ ] **Step 5: Run server tests and commit**

Run: `python3 -m unittest tests.test_serve_kb -v`

Expected: PASS.

```bash
git add scripts/serve_kb.py tests/test_serve_kb.py
git commit -m "feat: upload interview sources safely"
```

### Task 8: Build the Viewer Interview Section

**Files:**
- Modify: `viewer.html`
- Modify: `graph-view.html`
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/test_graph_view_contract.py`

- [ ] **Step 1: Write failing Viewer contracts**

Assert accessible `知识库` and `工程面试` tabs, independent storage keys, interview index loading, role/difficulty/tag filters, `interview-graph-data.json` selection, and page context fields `pageType`, `question`, `roles`, and `difficulty`.

- [ ] **Step 2: Verify contract failure**

Run: `python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v`

Expected: FAIL on absent interview controls and context.

- [ ] **Step 3: Implement section-aware navigation**

Keep one Viewer document. Add a segmented tab control, `activeSection`, and separate navigation state keys. Knowledge mode fetches `_index.md`; interview mode fetches `_interview_index.md`. Parse interview metadata into entries and filter without reloading the iframe or rebuilding unrelated state.

- [ ] **Step 4: Switch graph profiles without mixing state**

Pass `profile=knowledge|interview` to `graph-view.html`. Select the matching JSON URL and storage key. Render external concept nodes distinctly and open their knowledge Viewer hrefs. Do not include them in visible statistics displayed to the user.

- [ ] **Step 5: Emit typed Claude context**

For interview pages, post:

```javascript
{kind:'page', pageType:'interview', file, title, question, roles, difficulty}
```

Preserve the current knowledge-page and graph context shapes.

- [ ] **Step 6: Run Viewer contracts and commit**

Run: `python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v`

Expected: PASS.

```bash
git add viewer.html graph-view.html tests/test_viewer_contract.py tests/test_graph_view_contract.py
git commit -m "feat: add interview section to viewer"
```

### Task 9: Add Workbench Upload and Interview Prompt UI

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`

- [ ] **Step 1: Write failing patch tests**

Assert the generated shell has an `创建面试页` command, a dialog with question, focus, and multi-file input using the exact accept list, upload progress/error states, and prompt text invoking `$create-engineering-interview-page`. Assert active interview context survives the bridge validation.

- [ ] **Step 2: Verify patch tests fail**

Run: `node <local-webui-root>/test-integrated-workbench.mjs`

Expected: FAIL because the dialog and upload code are absent.

- [ ] **Step 3: Add the interview dialog and upload flow**

On submit, upload selected files to `http://127.0.0.1:18081/api/uploads`, collect returned relative paths, then place this prompt into Claude:

```text
请使用 $create-engineering-interview-page Skill 完成工程面试页创建或更新任务。
面试问题：<question or 请从材料中提取>
参考材料：<raw/inbox paths or 未提供>
特别关注：<focus>
如材料包含多道问题，先列出问题清单、建议标题和推测难度，等待我确认后再建页。
```

Retain the dialog and files when upload or prompt insertion fails; clear them only after confirmed insertion. Support Escape, cancel, backdrop dismissal, and focus restoration like existing dialogs.

- [ ] **Step 4: Apply the patch and run Node tests**

Run the patch script against the installed WebUI, then:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
node --check <local-webui-root>/app/node_modules/claude-code-webui/dist/static/assets/workbench.js
```

Expected: all tests PASS and syntax check exits 0.

- [ ] **Step 5: Preserve external WebUI edits explicitly**

Do not stage the enclosing `<local-user-home>` repository. Record the two modified WebUI source files and deployed generated assets in the completion report.

### Task 10: End-to-End Regression, Documentation, and Sample Page

**Files:**
- Modify: `tests/web_workbench.spec.cjs`
- Modify: `tests/test_web_workbench_e2e.py`
- Modify: `Web操作台使用与维护说明书.md`
- Create: `pages/多头注意力机制的核心作用是什么.md`

- [ ] **Step 1: Write a failing full browser flow**

Cover desktop and mobile flows: switch to interview section, upload a small TXT fixture, verify the prompt contains the returned `raw/inbox/` path and skill name, open the sample interview page, filter by role and difficulty, open the interview graph, follow its external concept link, refresh, and confirm both section states persist.

- [ ] **Step 2: Verify E2E failure before the final wiring**

Run: `KB_E2E=1 python3 tests/test_web_workbench_e2e.py -v`

Expected: FAIL at the first missing interview interaction.

- [ ] **Step 3: Create the sample page through the new skill contract**

Use the Attention Is All You Need paper as the primary technical source and explicitly distinguish “multiple representation subspaces” from the inaccurate claim that heads are guaranteed to learn human-interpretable relations. Link the existing multi-head attention concept page. Ensure all mandatory sections and profile metadata are present.

- [ ] **Step 4: Update the operating manual**

Document section switching, upload limits and supported formats, multi-question confirmation, interview taxonomy commands, generated files, refresh behavior, troubleshooting, and the dedicated skill trigger. Preserve the user's existing uncommitted formatting changes and stage only lines attributable to this task if the file remains mixed.

- [ ] **Step 5: Run all generators and health checks**

```bash
TAXONOMY_TEST_ENCODER=deterministic python3 scripts/taxonomy_cli.py --profile interview sync --page "pages/多头注意力机制的核心作用是什么.md"
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: both indexes and both graph data files are generated; health reports `ERROR 0` and `WARN 0`.

- [ ] **Step 6: Run the full automated suite**

```bash
python3 -m unittest discover -s tests -v
KB_E2E=1 python3 tests/test_web_workbench_e2e.py -v
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
git diff --check
```

Expected: all tests PASS, the default suite has no unexpected skips or warnings, and diff check exits 0.

- [ ] **Step 7: Perform visual verification**

Start the standard services. Use Playwright at desktop and mobile viewports to verify no horizontal overflow, no overlap, stable section switching, rendered KaTeX, readable code blocks, nonblank interview graph, upload error states, and correct Claude prompt insertion. Capture screenshots for the interview list, sample page, graph, upload dialog, and mobile view.

- [ ] **Step 8: Commit repository-owned completion artifacts**

Stage the sample page, generated interview artifacts, E2E tests, and only repository-owned documentation changes. Do not include unrelated manual edits or upload fixtures.

```bash
git commit -m "feat: deliver engineering interview workspace"
```

- [ ] **Step 9: Report external and retained changes**

Report the WebUI files changed outside this repository, generated screenshot paths, test counts, health totals, service URLs, sample page path, and any user-owned documentation changes intentionally left unstaged.
