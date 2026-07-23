# Web 操作台桌面体验收口实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不增加业务功能的前提下，让桌面端完整知识工作旅程具备稳定恢复、可信反馈、明确闭环和统一视觉。

**Architecture:** 保留现有外层 WebUI、Viewer、图谱和 Claude iframe 边界。每个模块只管理自身可观测状态，通过已有 `postMessage` 通道向外层报告上下文和刷新完成事件。状态恢复使用带版本的 `sessionStorage`，真实用户旅程由独立 Playwright 套件验收。

**Tech Stack:** 原生 HTML/CSS/JavaScript、Node.js WebUI 补丁脚本、Python 知识库服务、Playwright、`unittest`、KaTeX、Cytoscape.js。

---

## 文件边界

- `/home/u2023312337/webui/patch-integrated-workbench.mjs`：外层工作台状态、双栏恢复、刷新闭环、Claude 输入桥接与对话视觉。
- `/home/u2023312337/webui/test-integrated-workbench.mjs`：WebUI 补丁产物和纯函数契约。
- `viewer.html`：导航、页面加载、阅读状态、内容渲染和 Viewer 恢复。
- `graph-view.html`：图谱新鲜度、加载/布局/重组状态、失败回退和图谱恢复。
- `scripts/serve_kb.py`：仅在现有 API 响应缺少可观测结果时补充结构化响应，不增加新端点。
- `tests/desktop_experience.spec.cjs`：新建的桌面完整旅程与故障注入测试。
- `tests/test_viewer_contract.py`、`tests/test_graph_view_contract.py`、`tests/test_serve_kb.py`：模块契约和服务响应测试。
- `.claude/skills/create-knowledge-page/SKILL.md`、`.claude/skills/create-engineering-interview-page/SKILL.md`：创建任务最终报告的固定闭环。
- `Web操作台使用与维护说明书.md`：只记录经验证的最终行为和恢复路径。

`/home/u2023312337/知识库` 和 `/home/u2023312337/webui` 不属于同一 Git 根。跨边界任务必须分别在知识库与 `/home/u2023312337` 上层仓库做精确路径提交，不得使用 `git add .` 或 `git add -A`。

### Task 1: 建立桌面旅程基线

**Files:**
- Create: `docs/desktop-experience-baseline.md`
- Create: `tests/desktop_experience.spec.cjs`
- Modify: `tests/playwright.config.cjs`

- [ ] **Step 1: 写入可重复的基线测试骨架**

```js
const { test, expect } = require('@playwright/test');

for (const viewport of [
  { name: 'desktop-wide', width: 1440, height: 900 },
  { name: 'desktop-tall', width: 1112, height: 1243 },
]) {
  test.describe(viewport.name, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    test('complete desktop journey preserves state and layout', async ({ page }) => {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await page.goto('http://127.0.0.1:18080/');
      await expect(page.locator('#workbench')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      expect(errors).toEqual([]);
    });
  });
}
```

- [ ] **Step 2: 运行骨架并确认测试环境可用**

Run: `npx playwright test tests/desktop_experience.spec.cjs --workers=1`

Expected: 两个视口用例通过；这一步只证明基线环境，不声称旅程已完整。

- [ ] **Step 3: 在基线文档中记录可复现问题**

```markdown
| ID | 旅程阶段 | 视口 | 复现步骤 | 期望 | 实际 | 证据 | 优先级 | 状态 |
|---|---|---|---|---|---|---|---|---|
```

对设计中的 10 个端到端场景各执行一次，只记录已复现事实；每条记录包含截图路径、控制台错误或计算后布局数据。

- [ ] **Step 4: 将每个 P0/P1 问题转为会失败的 Playwright 用例**

用例名称必须描述用户可观测结果，例如：

```js
test('restores split width after a full page reload', async ({ page }) => {
  await page.goto('http://127.0.0.1:18080/');
  await page.evaluate(() => sessionStorage.setItem('radar-workbench-state-v1', JSON.stringify({ version: 1, knowledgeWidth: 64, knowledgeCollapsed: false, claudeCollapsed: false })));
  await page.reload();
  await expect(page.locator('#divider')).toHaveAttribute('aria-valuenow', '64');
});
```

其他 P0/P1 用例在后续对应任务中给出完整实现；基线盘点新发现的问题先记录，不在没有复现证据时写空测试。

- [ ] **Step 5: 确认新用例因对应缺陷而失败**

Run: `npx playwright test tests/desktop_experience.spec.cjs --workers=1`

Expected: 每个新回归用例有明确的断言失败，不得因选择器错误、服务未启动或超时失败。

- [ ] **Step 6: Commit**

```bash
git add docs/desktop-experience-baseline.md tests/desktop_experience.spec.cjs tests/playwright.config.cjs
git commit -m "test: capture desktop experience baseline"
```

### Task 2: 收口外层工作台恢复

**Files:**
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 为带版本的外层状态添加失败契约**

```js
assert.deepEqual(normalizeWorkbenchState({ version: 1, knowledgeWidth: 64, knowledgeCollapsed: false, claudeCollapsed: false }), {
  version: 1, knowledgeWidth: 64, knowledgeCollapsed: false, claudeCollapsed: false,
});
assert.equal(normalizeWorkbenchState({ version: 99, knowledgeWidth: 64 }), null);
assert.deepEqual(normalizeWorkbenchState({ version: 1, knowledgeWidth: 'wide', knowledgeCollapsed: true }), {
  version: 1, knowledgeWidth: 58, knowledgeCollapsed: true, claudeCollapsed: false,
});
```

同时在 Playwright 中拖动分隔条到 `64%`，刷新后断言 `aria-valuenow="64"`；折叠单侧后刷新，断言折叠状态恢复。

- [ ] **Step 2: 运行聚焦测试并确认 RED**

Run: `node /home/u2023312337/webui/test-integrated-workbench.mjs`

Expected: FAIL，缺少 `normalizeWorkbenchState` 或对应持久化契约。

- [ ] **Step 3: 实现局部容错恢复**

在补丁源中导出 `normalizeWorkbenchState`，并向生成的外层 JS 注入：

```js
const WORKBENCH_STATE_KEY = 'radar-workbench-state-v1';
function persistWorkbenchState() {
  safeDraftSet(sessionStorage, WORKBENCH_STATE_KEY, JSON.stringify({
    version: 1,
    knowledgeWidth: Number(divider.getAttribute('aria-valuenow')),
    knowledgeCollapsed: workbench.classList.contains('knowledge-collapsed'),
    claudeCollapsed: workbench.classList.contains('claude-collapsed'),
  }));
}
```

恢复时分别校验宽度和两个布尔字段；单个无效字段回退默认值，不清除其他有效字段。拖动结束、键盘调整和折叠切换后保存，初始化 iframe 前恢复。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
npx playwright test tests/desktop_experience.spec.cjs -g "restores split width" --workers=1
```

Expected: PASS；快照中两个 iframe 均不被裁切。

- [ ] **Step 5: Commit**

```bash
git add tests/desktop_experience.spec.cjs
git commit -m "test: cover desktop workbench state"
git -C /home/u2023312337 add -- webui/test-integrated-workbench.mjs webui/patch-integrated-workbench.mjs
git -C /home/u2023312337 commit -m "fix: restore desktop workbench state" -- webui/test-integrated-workbench.mjs webui/patch-integrated-workbench.mjs
```

### Task 3: 建立可信的刷新与状态闭环

**Files:**
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `viewer.html`
- Modify: `graph-view.html`
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/test_graph_view_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 先写刷新成功事件和失败保留测试**

Viewer 和图谱成功完成原地更新后必须发送：

```js
window.parent.postMessage({
  type: 'kb-refresh-result',
  ok: true,
  surface: 'viewer', // 图谱为 graph
  revision,
}, location.origin);
```

失败发送 `{ type: 'kb-refresh-result', ok: false, surface, error }`。外层只接受 `VIEWER_ORIGIN` 且 `event.source === knowledgeFrame.contentWindow` 的事件。

Playwright 通过路由模拟 `/api/refresh` 失败，断言：当前页标题未变、Claude 草稿未变、状态区显示失败及影响范围。

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v
npx playwright test tests/desktop_experience.spec.cjs -g "failed refresh" --workers=1
```

Expected: FAIL，当前实现使用固定 `600ms` 计时器宣告刷新完成，没有消费真实完成事件。

- [ ] **Step 3: 将外层状态改为结构化状态**

用 `setWorkbenchStatus({ kind, title, detail, persistent })` 取代单字符串 `showStatus`。`kind` 只允许 `progress | success | warning | error`；先显示“正在更新分类、索引与图谱”，API 返回后显示“正在恢复当前视图”，只在收到 `kb-refresh-result.ok === true` 后显示成功。

- [ ] **Step 4: 使 Viewer 和图谱在真实完成点上报结果**

Viewer 在索引和当前页均已更新后上报；图谱在新数据、筛选、选中节点、zoom 和 pan 恢复后上报。无法重建时保留现有 DOM/Cytoscape 实例。

- [ ] **Step 5: 验证 GREEN**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v
npx playwright test tests/desktop_experience.spec.cjs -g "refresh" --workers=1
```

Expected: PASS；状态区不会在 Viewer/图谱尚未恢复时显示成功。

- [ ] **Step 6: Commit**

```bash
git add viewer.html graph-view.html tests/test_viewer_contract.py tests/test_graph_view_contract.py tests/desktop_experience.spec.cjs
git commit -m "fix: report knowledge refresh completion"
git -C /home/u2023312337 add -- webui/test-integrated-workbench.mjs webui/patch-integrated-workbench.mjs
git -C /home/u2023312337 commit -m "fix: close the knowledge refresh feedback loop" -- webui/test-integrated-workbench.mjs webui/patch-integrated-workbench.mjs
```

### Task 4: 收口 Viewer 阅读与导航体验

**Files:**
- Modify: `viewer.html`
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写入加载竞态、失败保留和宽内容回归**

```js
test('failed page navigation keeps the last readable article', async ({ page }) => {
  await page.goto('http://127.0.0.1:18081/viewer.html?f=%E9%A6%96%E9%A1%B5.md');
  const oldTitle = await page.locator('#content h1').textContent();
  await page.route('**/pages/Unavailable.md', route => route.fulfill({ status: 503, body: 'unavailable' }));
  await page.evaluate(() => navigateTo('pages/Unavailable.md', { sectionHint: 'knowledge', historyMode: 'push' }));
  await expect(page.locator('#content h1')).toHaveText(oldTitle);
  await expect(page.getByRole('alert')).toContainText('当前内容已保留');
});
test('math tables code and long paths stay inside the reading column', async ({ page }) => {
  await page.goto('http://127.0.0.1:18081/viewer.html?f=pages%2F%E6%89%A9%E6%95%A3%E6%A8%A1%E5%9E%8B%20Diffusion%20Models%20DDPM.md');
  await expect(page.locator('.katex').first()).toBeVisible();
  await expect(page.locator('#content')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
```

契约测试要求正文状态容器具有 `role="status"`/`role="alert"`，页面切换不在请求开始时清空 `#content`。

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract -v
npx playwright test tests/desktop_experience.spec.cjs -g "readable article|math tables" --workers=1
```

- [ ] **Step 3: 实现不破坏旧内容的导航状态**

为导航请求保留已有 request token 竞态保护。开始时只更新页面顶部状态；成功解析完成后一次替换正文；失败时保留旧正文并显示“未能打开目标页，当前内容已保留”。

统一阅读列最大宽度、段落节奏和次级文字颜色；`table`、`pre`、`.katex-display` 各自水平滚动，不扩张页面根宽度。

- [ ] **Step 4: 验证 GREEN 和快速切页竞态**

Run:

```bash
python3 -m unittest tests.test_viewer_contract -v
npx playwright test tests/web_workbench.spec.cjs -g "latest viewer navigation|failed cross-section" --workers=1
npx playwright test tests/desktop_experience.spec.cjs -g "readable article|math tables" --workers=1
```

- [ ] **Step 5: Commit**

```bash
git add viewer.html tests/test_viewer_contract.py tests/desktop_experience.spec.cjs
git commit -m "fix: stabilize desktop knowledge reading"
```

### Task 5: 收口图谱新鲜度与操作反馈

**Files:**
- Modify: `graph-view.html`
- Modify: `tests/test_graph_view_contract.py`
- Modify: `tests/taxonomy_observability.spec.cjs`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 先写图谱新鲜度和失败回退测试**

```js
test('graph reports a stale state while preserving its last revision', async ({ page }) => {
  await page.goto('http://127.0.0.1:18081/graph-view.html');
  const revision = await page.locator('#graphStatus').getAttribute('data-revision');
  await page.route('**/api/revision', route => route.fulfill({ status: 503, body: '{}' }));
  await page.evaluate(() => checkForUpdates());
  await expect(page.locator('#graphStatus')).toHaveAttribute('data-state', 'stale');
  await expect(page.locator('#graphStatus')).toHaveAttribute('data-revision', revision);
  await expect(page.locator('#graph canvas').first()).toBeVisible();
});
test('failed graph refresh preserves mode and selected node', async ({ page }) => {
  await page.goto('http://127.0.0.1:18081/graph-view.html');
  await page.locator('[data-mode="combined"]').click();
  await page.locator('#search').fill('扩散模型');
  await page.locator('.search-result').first().click();
  const before = await page.evaluate(() => ({ mode: state.mode, selected: state.selected?.id() || null, zoom: state.cy.zoom(), pan: state.cy.pan() }));
  await page.route('**/graph-data.json*', route => route.fulfill({ status: 503, body: '{}' }));
  await page.evaluate(() => loadGraph('failed-test-revision').catch(() => {}));
  expect(await page.evaluate(() => ({ mode: state.mode, selected: state.selected?.id() || null, zoom: state.cy.zoom(), pan: state.cy.pan() }))).toEqual(before);
});
test('taxonomy rebuild success identifies the new revision', async ({ page }) => {
  await page.route('**/api/taxonomy/rebuild', route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({ ok: true, revision: 'revision-after-rebuild' }),
  }));
  await page.route('**/graph-data.json*', route => route.continue());
  await page.goto('http://127.0.0.1:18081/graph-view.html');
  await page.locator('#taxonomyRebuild').click();
  await expect(page.locator('#graphStatus')).toHaveAttribute('data-revision', 'revision-after-rebuild');
  await expect(page.locator('#graphStatus')).toHaveAttribute('data-state', 'current');
});
```

契约测试要求图谱状态只使用 `checking | current | rebuilding | stale | error`，并始终保留最后成功 revision。

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_graph_view_contract -v
npx playwright test tests/taxonomy_observability.spec.cjs tests/desktop_experience.spec.cjs -g "graph reports|failed graph|rebuild success" --workers=1
```

- [ ] **Step 3: 实现单一图谱状态模型**

增加 `setGraphStatus(kind, detail, revision)`，由初始加载、revision 检查、`loadGraph`、布局和分类重组共用。周期检查失败时状态为 `stale`，不销毁旧图；只有首次加载无可用图时显示阻断错误面板。

分类重组成功后显示响应中的 revision，再加载并恢复图谱；失败显示“重组未完成，仍显示 revision X”。

- [ ] **Step 4: 验证 GREEN 与布局稳定性**

Run:

```bash
python3 -m unittest tests.test_graph_view_contract -v
npx playwright test tests/taxonomy_observability.spec.cjs tests/desktop_experience.spec.cjs -g "graph|taxonomy" --workers=1
```

额外读取刷新前后的 `cy.zoom()`、`cy.pan()` 和选中节点 ID，要求有效状态相等。

- [ ] **Step 5: Commit**

```bash
git add graph-view.html tests/test_graph_view_contract.py tests/taxonomy_observability.spec.cjs tests/desktop_experience.spec.cjs
git commit -m "fix: make graph freshness and recovery explicit"
```

### Task 6: 收口 Claude 历史、输入和错误表达

**Files:**
- Modify: `/home/u2023312337/webui/test-integrated-workbench.mjs`
- Modify: `/home/u2023312337/webui/test-dangerous-mode.mjs`
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写入真实历史路径和连续输入回归**

```js
test('second ask-Claude insertion updates the controlled textarea', async ({ page }) => {
  await page.goto('http://127.0.0.1:18080/');
  for (const question of ['第一个问题', '第二个问题']) {
    await page.locator('#askClaude').click();
    await page.locator('#question').fill(question);
    await page.locator('#insertPrompt').click();
    await expect(page.frameLocator('#claudeFrame').getByRole('textbox', { name: 'Claude prompt' })).toHaveValue(new RegExp(question));
  }
});
test('opening a long history keeps the composer at the viewport bottom', async ({ page }) => {
  await page.goto('http://127.0.0.1:18080/');
  const claude = page.frameLocator('#claudeFrame');
  await claude.getByRole('button', { name: 'View conversation history' }).click();
  await claude.locator('div.cursor-pointer').first().click();
  await expect.poll(() => page.frames().find(frame => frame.url().includes('/projects/home/')).evaluate(() => {
    const shell = document.querySelector('.claude-shell');
    const composer = document.querySelector('.claude-composer').getBoundingClientRect();
    return shell.scrollTop === 0 && Math.abs(composer.bottom - innerHeight) < 1;
  })).toBe(true);
});
```

为 `401`、`429`、`stream_error`、Claude 二进制路径无效各写一个测试，断言显示“影响 + 保留状态 + 恢复动作”三部分，Composer 仍可见。

```js
assert.deepEqual(describeClaudeFailure('HTTP 401'), {
  kind: 'auth', title: '认证不可用', effect: '当前消息未完成，输入内容已保留', recovery: '检查 WebUI 专用 API 配置后重试',
});
assert.deepEqual(describeClaudeFailure('HTTP 429'), {
  kind: 'rate-limit', title: '上游限流', effect: '当前消息未完成，输入内容已保留', recovery: '等待额度或速率恢复后手动重试',
});
assert.equal(describeClaudeFailure('stream_error').kind, 'stream');
assert.equal(describeClaudeFailure('Claude Code native binary not found').kind, 'local-runtime');
```

Playwright 另通过拦截 Claude 请求返回 `429` 验证真实错误面板：主标题为“上游限流”，正文包含“输入内容已保留”和“手动重试”，`.claude-composer` 仍可见。其他三种映射由 Node 契约测试覆盖，不向生产代码添加测试后门。

- [ ] **Step 2: 确认 RED**

Run:

```bash
npx playwright test tests/desktop_experience.spec.cjs -g "ask-Claude|long history|401|429|stream" --workers=1
```

Expected: 未被已有修复覆盖的用例失败；已通过的输入或布局用例作为回归保护保留。

- [ ] **Step 3: 统一 Claude 状态语义与视觉**

在现有补丁中为历史 loading/empty/error、请求 running、工具 success/error、Reasoning、限流和权限提示保留稳定语义类。复用已确认的中性浅色主题和低饱和工具/思考色；不解析或改写 Claude 消息数据。

错误文案将原始错误作为可展开技术详情；主文案映射为：认证不可用、上游限流、响应中断、本机 Claude 不可用。不自动重试、不自动重发用户消息。

- [ ] **Step 4: 验证桌面两视口的长会话**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/test-dangerous-mode.mjs
npx playwright test tests/desktop_experience.spec.cjs -g "ask-Claude|history|401|429|stream" --workers=1
```

截图并检查工具块、Reasoning、Markdown、错误块和 Composer 不重叠；读取计算后颜色，禁止使用原始高饱和 Tailwind 颜色。

- [ ] **Step 5: Commit**

```bash
git add tests/desktop_experience.spec.cjs
git commit -m "test: cover Claude desktop conversations"
git -C /home/u2023312337 add -- webui/test-integrated-workbench.mjs webui/test-dangerous-mode.mjs webui/patch-integrated-workbench.mjs
git -C /home/u2023312337 commit -m "fix: stabilize Claude desktop conversations" -- webui/test-integrated-workbench.mjs webui/test-dangerous-mode.mjs webui/patch-integrated-workbench.mjs
```

### Task 7: 统一创建任务的最终报告闭环

**Files:**
- Modify: `.claude/skills/create-knowledge-page/SKILL.md`
- Modify: `.claude/skills/create-engineering-interview-page/SKILL.md`
- Modify: `tests/test_create_knowledge_page_skill.py`
- Modify: `tests/test_create_engineering_interview_page_skill.py`

- [ ] **Step 1: 为两个 Skill 的最终报告写失败契约**

两类页面必须按下列固定顺序报告，测试检查标题和顺序：

```text
页面：pages/LRU 缓存替换 Least Recently Used.md
内容：新建 LRU 定义、O(1) 实现、扫描污染与工程近似页
来源：Wikipedia Cache replacement policies（信度：高）
分类：已同步到“基础”；动态归属为 Cache Systems，分数 0.87
验证：索引和图谱已生成；ERROR 0 / WARN 0；Viewer 渲染通过
提交：bc1a43d
```

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_create_knowledge_page_skill tests.test_create_engineering_interview_page_skill -v
```

- [ ] **Step 3: 只收口最终报告，不改变创建流程**

修改两个 `SKILL.md` 的最终输出段。分类失败时必须说明页面已保留、使用上一版 taxonomy；健康检查未达 `ERROR 0 / WARN 0` 时不得使用“完成”。

- [ ] **Step 4: 验证 GREEN**

Run:

```bash
python3 -m unittest tests.test_create_knowledge_page_skill tests.test_create_engineering_interview_page_skill -v
```

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/create-knowledge-page/SKILL.md .claude/skills/create-engineering-interview-page/SKILL.md tests/test_create_knowledge_page_skill.py tests/test_create_engineering_interview_page_skill.py
git commit -m "docs: standardize page creation handoff"
```

### Task 8: 统一视觉与错误文案

**Files:**
- Modify: `/home/u2023312337/webui/patch-integrated-workbench.mjs`
- Modify: `viewer.html`
- Modify: `graph-view.html`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 先写跨模块视觉契约**

Playwright 分别读取外层、Viewer、图谱和 Claude 的主文字、次文字、边框、主强调、成功、警告和错误计算后颜色，断言它们属于同一组精确 RGB 值。断言常规卡片/弹窗圆角不超过 `8px`，按钮高度属于 `32px` 或 `36px` 两个等级。

- [ ] **Step 2: 确认 RED**

Run: `npx playwright test tests/desktop_experience.spec.cjs -g "visual tokens|error language" --workers=1`

- [ ] **Step 3: 在各边界内对齐同一组 token**

```css
--ui-bg: #f7f8f7;
--ui-surface: #ffffff;
--ui-surface-soft: #eef1ef;
--ui-text: #202421;
--ui-muted: #66706a;
--ui-border: #d8ded9;
--ui-accent: #087f68;
--ui-success: #18794e;
--ui-warning: #9a6700;
--ui-danger: #b42318;
```

每个 iframe 仍保留本地 CSS 变量，但数值和语义一致；不引入跨 iframe CSS 依赖。统一加载、成功、失败标题的句式，原始异常放在次级详情。

- [ ] **Step 4: 在两个基准视口进行视觉检查**

Run:

```bash
npx playwright test tests/desktop_experience.spec.cjs -g "visual tokens|complete desktop journey" --workers=1 --update-snapshots
```

检查顶栏、目录、阅读区、图谱工具栏、Claude 工具块、状态提示和弹窗；不为快照差异盲目更新基线。

- [ ] **Step 5: Commit**

```bash
git add viewer.html graph-view.html tests/desktop_experience.spec.cjs
git commit -m "style: align knowledge desktop feedback"
git -C /home/u2023312337 add -- webui/patch-integrated-workbench.mjs
git -C /home/u2023312337 commit -m "style: align Claude desktop feedback" -- webui/patch-integrated-workbench.mjs
```

### Task 9: 全旅程回归与文档固化

**Files:**
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `docs/desktop-experience-baseline.md`
- Modify: `Web操作台使用与维护说明书.md`

- [ ] **Step 1: 补齐完整旅程用例**

一个用例连续执行：恢复工作台 -> 搜索并打开复杂页 -> 切换图谱并恢复 -> 连续两次询问 Claude -> 打开历史会话 -> 刷新知识库 -> 确认新 revision。创建页面使用隔离临时库或模拟 Claude 输出，不在每次回归中污染真实知识库。

- [ ] **Step 2: 运行全量自动验证**

Run:

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/test-dangerous-mode.mjs
python3 -m unittest discover -s tests -v
npx playwright test tests/desktop_experience.spec.cjs tests/web_workbench.spec.cjs tests/taxonomy_observability.spec.cjs --workers=1
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected: 所有命令退出码为 `0`；健康检查为 `ERROR 0 / WARN 0`；浏览器控制台无未处理异常。

- [ ] **Step 3: 执行服务重启验收**

Run:

```bash
/home/u2023312337/webui/kbserve-control restart
/home/u2023312337/webui/webui-control restart
/home/u2023312337/webui/kbserve-control status
/home/u2023312337/webui/webui-control status
```

重启后再运行 `complete desktop journey` 用例，确认恢复行为不依赖旧进程内存。

- [ ] **Step 4: 关闭基线问题并更新说明书**

`docs/desktop-experience-baseline.md` 中每个 P0/P1 必须关联自动化用例和最终证据；未关闭 P2/P3 保留为已知限制，不改写为完成。说明书只更新已验证的恢复、刷新、错误和历史会话行为。

- [ ] **Step 5: 最终范围检查**

Run:

```bash
git status --short
git diff --check
git diff --stat
```

确认没有业务新入口、Markdown schema 变化、分类算法变化、会话数据改写或新服务端点。

- [ ] **Step 6: Commit**

```bash
git add tests/desktop_experience.spec.cjs docs/desktop-experience-baseline.md Web操作台使用与维护说明书.md
git commit -m "test: lock the desktop knowledge journey"
```
