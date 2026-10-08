# Knowledge Page Skill and Claude UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a project-scoped high-quality knowledge-page Skill, expose it through the integrated WebUI, redesign the right-side Claude conversation surface, and document the completed system.

**Architecture:** Keep knowledge-page quality policy in `.claude/skills/create-knowledge-page/` and let the outer workbench generate only a structured Skill invocation. Keep all Claude UI changes reproducible in `<local-webui-root>/patch-integrated-workbench.mjs`, where exact vendor fragments receive stable semantic classes and `claude.html` receives tokenized theme CSS. Preserve the upstream network, history, permission, and message data paths.

**Tech Stack:** Claude Code project Skills, Markdown/YAML, Python `unittest`, Node.js ESM contract tests, static HTML/CSS/JavaScript patching, Playwright CLI, existing knowledge-base Python scripts.

---

### Task 1: Scaffold and Contract-Test the Project Skill

**Files:**
- Create: `.claude/skills/create-knowledge-page/SKILL.md`
- Create: `.claude/skills/create-knowledge-page/agents/openai.yaml`
- Create: `tests/test_create_knowledge_page_skill.py`

- [ ] **Step 1: Write the failing Skill contract test**

Create `tests/test_create_knowledge_page_skill.py` with tests that load the Skill and assert:

```python
SKILL = ROOT / ".claude/skills/create-knowledge-page/SKILL.md"

self.assertEqual(frontmatter["name"], "create-knowledge-page")
self.assertIn("创建知识页", frontmatter["description"])
for phrase in ("_index.md", "scripts/new_page.py", "scripts/build_index.py",
               "scripts/render_graph.py", "scripts/check_health.py"):
    self.assertIn(phrase, body)
for requirement in ("精确", "别名", "语义", "来源", "LaTeX", "ERROR 0", "WARN 0"):
    self.assertIn(requirement, body)
```

Also assert that the workflow treats supplied material as data rather than agent instructions, lists the four pause conditions, stages only task-related files, and has no `TBD` or template markers.

- [ ] **Step 2: Run the Skill test and verify RED**

Run:

```bash
python3 -m unittest tests.test_create_knowledge_page_skill -v
```

Expected: failure because `.claude/skills/create-knowledge-page/SKILL.md` does not exist.

- [ ] **Step 3: Initialize the Skill with the official scaffold tool**

Run:

```bash
python3 <codex-home>/skills/.system/skill-creator/scripts/init_skill.py \
  create-knowledge-page \
  --path <repo-root>/.claude/skills \
  --interface 'display_name=创建高质量知识页' \
  --interface 'short_description=查重、核验来源并创建或更新高质量技术知识页' \
  --interface 'default_prompt=Use $create-knowledge-page to create or update a verified technical knowledge page.'
```

Expected: Skill folder, `SKILL.md`, and `agents/openai.yaml` are created.

- [ ] **Step 4: Replace the scaffold with the approved workflow**

Write a concise imperative `SKILL.md` whose frontmatter contains only `name` and `description`. Implement these ordered phases:

```text
1. Parse topic, optional source/material, and optional focus.
2. Read CLAUDE.md, _index.md, template, and tag definitions.
3. Check exact title, aliases/abbreviations, and semantic overlap.
4. Update an existing page when it is the same concept; pause when ambiguous.
5. Verify supplied sources or research primary/official sources when absent.
6. Create the skeleton with new_page.py, then write adaptive substantive sections.
7. Check metadata, claims, links, formulas, project relevance, and placeholders.
8. Build index, render graph, run health, visually verify mathematical pages.
9. Review the diff, stage only task files, and create a radar: commit.
```

Explicitly include the four pause conditions and prompt-injection boundary from the design spec.

- [ ] **Step 5: Validate metadata and run GREEN tests**

Run:

```bash
python3 <codex-home>/skills/.system/skill-creator/scripts/quick_validate.py \
  .claude/skills/create-knowledge-page
python3 -m unittest tests.test_create_knowledge_page_skill -v
```

Expected: both commands pass.

- [ ] **Step 6: Commit the Skill**

```bash
git add .claude/skills/create-knowledge-page tests/test_create_knowledge_page_skill.py
git commit -m "feat: add high-quality knowledge page skill"
```

### Task 2: Add the Create-Knowledge-Page Workbench Entry

**Files:**
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`

- [ ] **Step 1: Extend the external workbench test first**

Add assertions for these generated shell markers:

```js
for (const marker of [
  'createKnowledge', 'createKnowledgeDialog', 'knowledgeTopic',
  'knowledgeSources', 'knowledgeFocus', 'insertKnowledgePrompt'
]) assert.match(shell, new RegExp(marker));
```

Assert the generated JavaScript:

```js
assert.match(js, /\$create-knowledge-page/);
assert.match(js, /知识主题/);
assert.match(js, /来源或已有材料/);
assert.match(js, /特别关注点/);
assert.match(js, /knowledgeTopic\.value\.trim\(\)/);
assert.doesNotMatch(js, /requestSubmit\(|\.submit\(/);
```

Keep the existing consecutive native-input-event and clipboard fallback assertions.

- [ ] **Step 2: Run the Node test and verify RED**

```bash
node <local-webui-root>/test-integrated-workbench.mjs
```

Expected: failure because the create-page controls are absent.

- [ ] **Step 3: Add the form and structured prompt generator**

Update the workbench shell with a `创建知识页` button and a separate dialog containing the three approved fields. Generate this logical payload without auto-submitting:

```text
请使用 $create-knowledge-page Skill 完成一次知识页创建或更新任务。
知识主题：<required topic>
来源或已有材料：<value or 未提供，请研究可靠公开来源>
特别关注点：<value or 无额外要求>
```

Reuse `setNativeValue()`, consecutive input verification, the Claude mobile-tab switch, and clipboard fallback. Keep field values until insertion succeeds; clear them after success.

- [ ] **Step 4: Run GREEN and idempotence checks**

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/patch-integrated-workbench.mjs
node <local-webui-root>/patch-integrated-workbench.mjs --check
```

Expected: test passes; patch reports `patched` or `already-patched`; check exits 0.

### Task 3: Add Stable Claude Conversation Hooks and Visual Tokens

**Files:**
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`

- [ ] **Step 1: Add failing redesign contract assertions**

Assert that patched `claude.html` contains a `data-claude-conversation-theme` style marker and CSS variables including:

```text
--cc-bg --cc-surface --cc-text --cc-muted --cc-border --cc-accent --cc-danger
```

Assert that the patched vendor JavaScript contains stable semantic class names:

```text
claude-shell claude-header claude-thread claude-empty-state
claude-message-row claude-message-body claude-composer
```

Assert the CSS includes `.dark`, `@media (max-width: 640px)`, `max-width:760px`, fixed Composer sizing, user-message alignment, assistant flat layout, code overflow handling, focus-visible state, and dangerous-mode styling. Assert no negative `letter-spacing` and no radius above 8px in the custom stylesheet.

- [ ] **Step 2: Run the Node test and verify RED**

```bash
node <local-webui-root>/test-integrated-workbench.mjs
```

Expected: failure on the first missing semantic hook.

- [ ] **Step 3: Patch exact vendor fragments with semantic classes**

Extend `prepareChat()` or a focused helper so exact upstream fragments receive semantic class names for the application shell, header, thread, empty state, shared message row/body, and Composer. Each replacement must:

```text
- verify the original fragment exists;
- accept an already-patched fragment;
- throw a descriptive error for unknown vendor content;
- preserve React behavior and all event handlers.
```

Do not add a DOM MutationObserver.

- [ ] **Step 4: Inject the tokenized light/dark responsive stylesheet**

Add one marked style block to `claude.html`. Implement the approved neutral palette, 48px header, flat centered 760px thread, assistant text layout, right-aligned user surface, compact status strips, Markdown/code styling, bottom Composer, four permission states, dark theme, and 390px-safe mobile behavior.

- [ ] **Step 5: Run patch tests and dangerous-mode regression**

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
node <local-webui-root>/patch-integrated-workbench.mjs
node <local-webui-root>/patch-integrated-workbench.mjs --check
node <local-webui-root>/patch-dangerous-mode.mjs --check
```

Expected: all tests and checks pass.

### Task 4: Write the User and Maintenance Manual

**Files:**
- Create: `Web操作台使用与维护说明书.md`
- Modify: `README.md`

- [ ] **Step 1: Write a failing documentation contract test**

Create `tests/test_web_console_manual.py` and assert that the manual exists and contains the twelve approved sections, both service control commands, all three URLs, the dedicated Claude config directory, the Coding Plan endpoint without any key, the create-page Skill, four permission modes, test commands, troubleshooting cases, localhost restrictions, and key file index entries.

- [ ] **Step 2: Run the documentation test and verify RED**

```bash
python3 -m unittest tests.test_web_console_manual -v
```

Expected: failure because `Web操作台使用与维护说明书.md` does not exist.

- [ ] **Step 3: Write the complete manual and README entry**

Use the current runtime files as facts. Start with:

```bash
<local-webui-root>/webui-control start
<local-webui-root>/kbserve-control start
```

Cover daily use, Viewer/math/graph, Claude UI and permission modes, the new create-page flow, dedicated Coding Plan config, process/port/data flow, testing, troubleshooting, security boundaries, known limitations, and key file index. Never include the API key. Add a visible README link near the introduction.

- [ ] **Step 4: Run documentation and health checks**

```bash
python3 -m unittest tests.test_web_console_manual -v
python3 scripts/check_health.py
git diff --check
```

Expected: tests pass; health reports ERROR 0 and WARN 0; diff check is clean.

- [ ] **Step 5: Commit repository documentation**

```bash
git add README.md Web操作台使用与维护说明书.md tests/test_web_console_manual.py
git commit -m "docs: add web console user and maintenance manual"
```

### Task 5: Browser Acceptance and Final Verification

**Files:**
- Update only if verification exposes a defect: `<local-webui-root>/patch-integrated-workbench.mjs`
- Update only if verification exposes a defect: `<local-webui-root>/test-integrated-workbench.mjs`

- [ ] **Step 1: Restart the patched WebUI**

```bash
<local-webui-root>/webui-control restart
```

Expected: `WebUI 已启动:http://127.0.0.1:18080`.

- [ ] **Step 2: Verify desktop flows with Playwright CLI**

At 1440x900, verify empty state, create-page dialog field validation, generated `$create-knowledge-page` prompt, two consecutive insertions, message Markdown, code overflow, tool rows, all four permission modes, history/settings controls, and zero console errors. Capture a screenshot and inspect it for overlap and visual hierarchy.

- [ ] **Step 3: Verify dark and mobile flows**

Toggle dark theme and inspect contrast. At 390x844, switch to Claude, verify the header and Composer remain visible, the create-page entry remains reachable, permission text fits, user messages stay within 88%, and there is no horizontal page overflow.

- [ ] **Step 4: Run the complete verification suite**

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_health.py
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
bash <local-webui-root>/test-dedicated-claude-config.sh
node <local-webui-root>/patch-integrated-workbench.mjs --check
node <local-webui-root>/patch-dangerous-mode.mjs --check
git diff --check
```

Expected: every command exits 0; health reports ERROR 0 and WARN 0.

- [ ] **Step 5: Review repository state and commit any verification fixes**

Use `git status --short` and `git diff` to confirm no unrelated files are included. Commit only repository-owned fixes; keep `<local-webui-root>/` deployment files outside the knowledge-base Git commit.
