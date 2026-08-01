# Engineering Interview Body Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the three engineering interview pages for fast review, add interview-only body hierarchy styles, and enforce the same rules in the template and project Skill.

**Architecture:** Markdown remains the source of truth for emphasis, lists, tables, diagrams, captions, and warnings. `viewer.html` applies presentation only when the loaded page declares `page_type: interview`; it marks known sections after Markdown rendering and isolates Mermaid failures so one invalid diagram cannot block the article. The template and Skill prevent future pages from drifting from the confirmed structure.

**Tech Stack:** Markdown/frontmatter, vanilla HTML/CSS/JavaScript, Marked, DOMPurify, Mermaid, Python `unittest`, Playwright.

---

## File Map

- Modify `templates/工程面试页模板.md`: encode the confirmed body skeleton and authoring prompts.
- Modify `.claude/skills/create-engineering-interview-page/SKILL.md`: enforce emphasis, list, diagram, local-image, caption, and fallback rules.
- Modify `tests/test_create_engineering_interview_page_skill.py`: contract tests for the template and Skill.
- Modify `viewer.html`: interview-only body classes, section decoration, image captions, and isolated Mermaid error handling.
- Modify `tests/test_viewer_contract.py`: static contract tests for interview styling and Mermaid isolation.
- Modify `tests/desktop_experience.spec.cjs`: browser assertions for hierarchy, overflow, image behavior, and invalid Mermaid fallback.
- Modify `pages/设计一个AI Agent的记忆系统.md`: restructure the current content and add one Mermaid architecture diagram.
- Modify `pages/多头注意力机制的核心作用是什么.md`: restructure the current content and add one Mermaid mechanism diagram.
- Modify `pages/知识图谱的存储方式与索引优化.md`: restructure the current content and add one Mermaid storage/query diagram.
- Create `assets/interview/agent-memory-architecture.png`, `assets/interview/multi-head-attention-architecture.png`, or `assets/interview/kg-storage-architecture.png` only when the source audit qualifies the corresponding official image. Pages without a qualified image use Mermaid and do not create an asset.

### Task 1: Lock Template and Skill Authoring Rules

**Files:**
- Modify: `tests/test_create_engineering_interview_page_skill.py`
- Modify: `templates/工程面试页模板.md`
- Modify: `.claude/skills/create-engineering-interview-page/SKILL.md`

- [ ] **Step 1: Write failing template and Skill contract tests**

Add these assertions to `tests/test_create_engineering_interview_page_skill.py`:

```python
def test_interview_template_encodes_scan_first_body_hierarchy(self):
    template = (ROOT / "templates/工程面试页模板.md").read_text()
    for phrase in (
        "一句直接结论", "核心机制或主链路", "关键取舍、边界或失败条件",
        "三至五条", "官方图", "Mermaid", "图注", "答案首句直接给结论",
    ):
        self.assertIn(phrase, template)

def test_interview_skill_enforces_visual_evidence_rules(self):
    skill = (ROOT / ".claude/skills/create-engineering-interview-page/SKILL.md").read_text()
    for phrase in (
        "单段不超过三处加粗", "连续三项", "官方图优先", "保存到仓库本地",
        "禁止远程图片", "纯装饰图", "一至两张", "Mermaid", "图注",
    ):
        self.assertIn(phrase, skill)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python3 -m unittest tests.test_create_engineering_interview_page_skill -v`

Expected: the two new tests fail because the phrases are absent.

- [ ] **Step 3: Update the template with executable authoring prompts**

Replace placeholder prose under the existing headings with this structure while preserving all frontmatter keys and required headings:

```markdown
## 考察意图

用三至五条列出可观察的能力，每条采用“关键词：具体判断”的结构。

## 30 秒回答

1. 一句直接结论。
2. 核心机制或主链路。
3. 关键取舍、边界或失败条件。

<!-- 技术图：官方图适合且能保存到仓库本地时优先使用，并附来源与图注；否则按需使用 Mermaid。表格或文字更准确时不放图。 -->

## 2 分钟回答

每段只处理一个主题，以短主题句开头；连续三项以上的并列机制改为列表。

## 原理拆解

按关系选择编号流程、短列表、表格或 Mermaid，不为视觉效果重复表达同一内容。

## 递进追问与参考回答

每个问题使用三级标题，答案首句直接给结论。
```

- [ ] **Step 4: Add concise quality gates to the Skill**

Add a `## 正文呈现门槛` section before the completion commands. It must state:

```markdown
- 30 秒回答固定覆盖一句直接结论、核心机制或主链路、关键取舍/边界/失败条件。
- 加粗只用于答案骨架、关键阶段、数字与边界，单段不超过三处加粗；连续三项以上的并列内容先判断是否改为列表或表格。
- 每页按信息增量决定是否放图，原则上一至两张。官方图优先，但必须核验出处、保存到仓库本地、使用相对路径并写图注；禁止远程图片、来源不明图片和纯装饰图。
- 没有合适官方图时，架构、流程、时序和关系可使用 Mermaid；表格或文字更准确时不放图。
- 2 分钟回答按主题分段；递进追问的答案首句直接给结论。
```

- [ ] **Step 5: Run the focused tests and commit**

Run: `python3 -m unittest tests.test_create_engineering_interview_page_skill -v`

Expected: all tests pass.

Commit:

```bash
git add -- templates/工程面试页模板.md .claude/skills/create-engineering-interview-page/SKILL.md tests/test_create_engineering_interview_page_skill.py
git commit -m "feat: define interview page body hierarchy"
```

### Task 2: Add Interview-Only Semantic Decoration

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing Viewer contract tests**

Add tests that require a page-type class and deterministic section markers:

```python
def test_interview_pages_receive_scoped_body_hierarchy(self):
    for value in (
        "page-type-interview", "interview-answer-brief", "interview-warning-section",
        "interview-figure", "decorateInterviewBody",
    ):
        self.assertIn(value, self.html)
    self.assertIn("pageMetadata.page_type === 'interview'", self.html)

def test_regular_pages_clear_interview_body_state(self):
    self.assertIn("elements.content.classList.toggle('page-type-interview'", self.html)
```

- [ ] **Step 2: Run the contract test and verify RED**

Run: `python3 -m unittest tests.test_viewer_contract.ViewerContractTests.test_interview_pages_receive_scoped_body_hierarchy tests.test_viewer_contract.ViewerContractTests.test_regular_pages_clear_interview_body_state -v`

Expected: both tests fail because the markers and decorator do not exist.

- [ ] **Step 3: Implement section decoration without parsing prose**

Add `decorateInterviewBody(content, pageMetadata)` near `renderPageData`. It must toggle the page class on every navigation and decorate sections by their `h2` text only:

```javascript
function sectionUntilNextHeading(heading) {
  const nodes = [];
  for (let node = heading.nextElementSibling; node && node.tagName !== 'H2'; node = node.nextElementSibling) nodes.push(node);
  return nodes;
}

function decorateInterviewBody(content, pageMetadata) {
  const interview = pageMetadata.page_type === 'interview';
  content.classList.toggle('page-type-interview', interview);
  if (!interview) return;
  for (const heading of content.querySelectorAll(':scope > h2')) {
    const title = heading.textContent.trim();
    if (title === '30 秒回答') {
      heading.classList.add('interview-brief-heading');
      sectionUntilNextHeading(heading).forEach(node => node.classList.add('interview-answer-brief'));
    }
    if (title === '常见错误回答') {
      heading.classList.add('interview-warning-heading');
      sectionUntilNextHeading(heading).forEach(node => node.classList.add('interview-warning-section'));
    }
  }
  content.querySelectorAll(':scope > p > img').forEach(image => {
    image.parentElement.classList.add('interview-figure');
  });
}
```

Call `decorateInterviewBody(elements.content, pageMetadata)` after sanitization and before math/Mermaid rendering.

- [ ] **Step 4: Add scoped CSS**

Add styles under the existing article rules. Use existing color tokens and keep corners at 6px or less:

```css
article.page-type-interview { line-height: 1.7; }
article.page-type-interview > h2 { margin-top: 2em; }
article.page-type-interview > h3 { margin-top: 1.65em; color: #31443e; }
article.page-type-interview .interview-brief-heading { margin-bottom: 0; border: 0; }
article.page-type-interview .interview-answer-brief { margin: 0; padding: 0 18px 12px; background: #edf7f4; }
article.page-type-interview .interview-answer-brief:first-of-type { padding-top: 14px; border-top: 3px solid var(--accent); }
article.page-type-interview .interview-warning-section { margin: 0; padding: 12px 16px; background: #fff8e8; border-left: 4px solid var(--ui-warning); }
article.page-type-interview .interview-figure { margin: 22px auto; text-align: center; color: var(--muted); font-size: 13px; }
article.page-type-interview li + li { margin-top: 5px; }
```

Adjust selectors during implementation so adjacent brief nodes form one visual block without nested cards or doubled borders.

- [ ] **Step 5: Run contract tests and commit**

Run: `python3 -m unittest tests.test_viewer_contract -v`

Expected: all Viewer contract tests pass.

Commit:

```bash
git add -- viewer.html tests/test_viewer_contract.py
git commit -m "feat: style engineering interview answers"
```

### Task 3: Isolate Mermaid Rendering Failures

**Files:**
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `viewer.html`

- [ ] **Step 1: Write failing static and browser tests**

Require a helper and per-node failure state in `tests/test_viewer_contract.py`:

```python
def test_mermaid_failure_is_scoped_to_the_diagram(self):
    self.assertIn("async function renderMermaidDiagrams", self.html)
    self.assertIn("mermaid-error", self.html)
    self.assertNotIn("await mermaid.run({ nodes: elements.content.querySelectorAll('.mermaid') })", self.html)
```

Add a Playwright test that routes a temporary Markdown response containing one invalid Mermaid block and a following heading. Assert that `.mermaid-error` and the following heading are both visible and no root overflow occurs.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract.ViewerContractTests.test_mermaid_failure_is_scoped_to_the_diagram -v
npx playwright test tests/desktop_experience.spec.cjs -g "invalid Mermaid" --workers=1
```

Expected: static test fails; browser test fails because rendering aborts before completing the page.

- [ ] **Step 3: Implement per-diagram isolation**

Replace the global Mermaid call with:

```javascript
async function renderMermaidDiagrams(content) {
  for (const node of content.querySelectorAll('.mermaid')) {
    try {
      await mermaid.run({ nodes: [node] });
    } catch (error) {
      node.classList.add('mermaid-error');
      node.setAttribute('role', 'note');
      node.textContent = `图示暂时无法渲染：${error?.message || 'Mermaid 语法错误'}`;
    }
  }
}
```

Call `await renderMermaidDiagrams(elements.content)`. Add restrained `.mermaid-error` CSS using `--ui-warning`; do not display a stack trace.

- [ ] **Step 4: Run focused tests and commit**

Run the two commands from Step 2.

Expected: both pass; the article remains readable after an invalid diagram.

Commit:

```bash
git add -- viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs
git commit -m "fix: isolate Mermaid rendering failures"
```

### Task 4: Migrate the Three Existing Interview Pages

**Files:**
- Modify: `pages/设计一个AI Agent的记忆系统.md`
- Modify: `pages/多头注意力机制的核心作用是什么.md`
- Modify: `pages/知识图谱的存储方式与索引优化.md`
- Create if qualified by the source audit: `assets/interview/agent-memory-architecture.png`
- Create if qualified by the source audit: `assets/interview/multi-head-attention-architecture.png`
- Create if qualified by the source audit: `assets/interview/kg-storage-architecture.png`
- Modify: `tests/test_interview_health.py`

- [ ] **Step 1: Add content-structure regression tests**

Add a test over the three exact filenames. Parse the frontmatter with `radar_common.parse_page` and assert that each body contains a three-item ordered list under `## 30 秒回答`, at least one Mermaid or local `assets/interview/` image, and no remote Markdown image:

```python
INTERVIEW_PAGES = (
    "设计一个AI Agent的记忆系统.md",
    "多头注意力机制的核心作用是什么.md",
    "知识图谱的存储方式与索引优化.md",
)

def test_existing_interview_pages_use_scan_first_structure(self):
    for name in INTERVIEW_PAGES:
        body = radar_common.parse_page(ROOT / "pages" / name).body
        brief = body.split("## 30 秒回答", 1)[1].split("## ", 1)[0]
        self.assertRegex(brief, r"(?m)^1\. .+\n2\. .+\n3\. .+")
        self.assertTrue("```mermaid" in body or "](../assets/interview/" in body)
        self.assertNotRegex(body, r"!\[[^]]*\]\(https?://")
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 -m unittest tests.test_interview_health -v`

Expected: the new test fails for all three current pages.

- [ ] **Step 3: Audit official figures before editing**

For each page, inspect its existing `source` entries. Use an official figure only when it directly explains the page's main mechanism, has a stable first-party URL, has clear reuse terms or is part of an openly distributed paper, and remains legible at a 920px document width. Record the exact source beside the caption.

If any condition fails, use the following Mermaid subject instead:

- Agent memory: event capture to four memory layers to hybrid retrieval to context injection.
- Multi-head attention: input projections into parallel heads, concatenation, and output projection; annotate that head specialization is not guaranteed.
- KG storage: RDF/attribute-graph storage branches feeding indexes, query planning, and execution.

- [ ] **Step 4: Restructure each page without changing claims**

For every page:

1. Convert `考察意图` to three to five scan-friendly items.
2. Rewrite `30 秒回答` as exactly three ordered items: conclusion, mechanism, boundary.
3. Insert the chosen official figure or Mermaid immediately after the brief, followed by an italic caption beginning with `图：`.
4. Split `2 分钟回答` by topic and start each paragraph with a short bold theme sentence.
5. Convert three-or-more parallel mechanisms to lists; keep causal arguments as paragraphs.
6. Ensure each progressive-answer paragraph starts with its conclusion.
7. Preserve frontmatter fields, claims, numbers, citations, links, headings, and update history; append a `2026-08-01` migration record.

- [ ] **Step 5: Run content and health tests**

Run:

```bash
python3 -m unittest tests.test_interview_health tests.test_create_engineering_interview_page_skill -v
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: tests pass; health reports `ERROR 0` and `WARN 0`; interview index still reports 3 pages; interview graph remains isolated.

- [ ] **Step 6: Commit only migrated content and actual assets**

```bash
git add -- pages/设计一个AI\ Agent的记忆系统.md pages/多头注意力机制的核心作用是什么.md pages/知识图谱的存储方式与索引优化.md tests/test_interview_health.py
test ! -f assets/interview/agent-memory-architecture.png || git add -- assets/interview/agent-memory-architecture.png
test ! -f assets/interview/multi-head-attention-architecture.png || git add -- assets/interview/multi-head-attention-architecture.png
test ! -f assets/interview/kg-storage-architecture.png || git add -- assets/interview/kg-storage-architecture.png
git commit -m "content: improve engineering interview readability"
```

Do not stage generated indexes or graph files unless their content changed solely because of the three page edits and repository policy requires those generated artifacts in the same commit.

### Task 5: Desktop Visual Regression and Full Verification

**Files:**
- Modify: `tests/desktop_experience.spec.cjs`
- Test artifacts only: `output/playwright/interview-*.png`

- [ ] **Step 1: Add a three-page visual contract test**

For each migrated page, navigate with `section=interview` and assert:

```javascript
await expect(page.locator('#content')).toHaveClass(/page-type-interview/);
await expect(page.locator('.interview-answer-brief').first()).toBeVisible();
await expect(page.locator('.mermaid svg, .interview-figure img').first()).toBeVisible();
expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
```

Also assert that a normal knowledge page lacks `page-type-interview` after navigation, proving style cleanup between page types.

- [ ] **Step 2: Run the browser test and verify RED if coverage is incomplete**

Run: `npx playwright test tests/desktop_experience.spec.cjs -g "interview body hierarchy" --workers=1`

Expected before final adjustments: any missing class, diagram, or cleanup behavior fails explicitly.

- [ ] **Step 3: Make the smallest CSS/content corrections required by the browser test**

Restrict changes to `viewer.html` and the three migrated pages. Do not change the sidebar, workbench split, graph, or mobile layout.

- [ ] **Step 4: Capture and inspect desktop screenshots**

Capture all three pages at 1440×900 into `output/playwright/`. Confirm visually that the title, question, and main brief are visible in the first viewport; headings are distinguishable; diagrams fit; no text or formula overlaps; and the brief reads as one block rather than nested cards.

- [ ] **Step 5: Run full verification**

Run:

```bash
python3 -m unittest discover -s tests -q
npx playwright test tests/desktop_experience.spec.cjs tests/web_workbench.spec.cjs tests/taxonomy_observability.spec.cjs --workers=1
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: all unit and browser tests pass; health reports `ERROR 0` and `WARN 0`; graph reports no broken links.

- [ ] **Step 6: Commit final regression coverage and scoped corrections**

```bash
git add -- tests/desktop_experience.spec.cjs viewer.html pages/设计一个AI\ Agent的记忆系统.md pages/多头注意力机制的核心作用是什么.md pages/知识图谱的存储方式与索引优化.md
git commit -m "test: cover interview body hierarchy"
```

Before committing, use `git diff --cached --name-only` and remove any path unrelated to this plan from the index.
