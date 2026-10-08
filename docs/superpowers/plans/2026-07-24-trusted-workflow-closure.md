# Web 操作台可信工作闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让桌面端用户能在外层工作台统一看见当前操作状态、最近一次真实结果和 Claude 实际工作上下文。

**Architecture:** 保留外层 WebUI、Viewer、图谱和 Claude iframe 边界。Viewer 与图谱只通过版本化 `postMessage` 上报事实，知识库服务在现有响应中补充可直接获得的统计，外层负责校验、状态生命周期、会话内结果存储和统一呈现。

**Tech Stack:** 原生 HTML/CSS/JavaScript、Node.js WebUI 补丁脚本、Python HTTP 服务、`unittest`、Playwright、`sessionStorage`。

---

## 文件边界

- `<local-webui-root>/patch-integrated-workbench.mjs`：消息校验、状态模型、结果存储、顶栏上下文和最近结果面板。
- `<local-webui-root>/test-integrated-workbench.mjs`：纯函数、补丁产物和幂等部署契约。
- `viewer.html`：页面上下文和页面恢复结果上报。
- `graph-view.html`：图谱上下文、revision、规模和分类重组结果上报。
- `scripts/serve_kb.py`：在现有刷新与分类接口中返回实际生成统计。
- `tests/test_viewer_contract.py`、`tests/test_graph_view_contract.py`、`tests/test_serve_kb.py`：模块契约。
- `tests/desktop_experience.spec.cjs`：桌面完整旅程和安全边界测试。
- `Web操作台使用与维护说明书.md`：最终用户可见行为和恢复说明。

知识库与 `<local-webui-root>` 属于不同 Git 仓库。每个任务必须精确暂存路径，不使用 `git add .` 或 `git add -A`，不覆盖现有未提交文件。

### Task 1: 建立版本化消息与结果模型

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`

- [ ] **Step 1: 为消息和结果规范化写失败契约**

在 `test-integrated-workbench.mjs` 导入并测试：

```js
assert.deepEqual(normalizeOperationResult({
  version: 1,
  operation: 'knowledge-refresh',
  ok: true,
  partial: false,
  surface: 'graph',
  revision: 'abc123',
  stats: { nodes: 124, edges: 689, errors: 0, warnings: 0 },
  preserved: [],
  error: null,
}), {
  version: 1,
  operation: 'knowledge-refresh',
  status: 'success',
  surface: 'graph',
  revision: 'abc123',
  stats: { nodes: 124, edges: 689, errors: 0, warnings: 0 },
  preserved: [],
  error: null,
});
assert.equal(normalizeOperationResult({ version: 2, operation: 'knowledge-refresh' }), null);
assert.equal(normalizeOperationResult({ version: 1, operation: 'unknown', ok: true }), null);
assert.equal(normalizeOperationResult({ version: 1, operation: 'knowledge-refresh', ok: true, stats: { nodes: -1 } }), null);
```

同时测试 `normalizeKnowledgeContext` 拒绝绝对路径、未知 surface、超过 1000 字符的标题和无效图谱模式。

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
```

Expected: FAIL，缺少 `normalizeOperationResult` 或 `normalizeKnowledgeContext`。

- [ ] **Step 3: 实现无 DOM 的纯函数模型**

在补丁模块导出：

```js
export function normalizeOperationResult(value) {
  if (!value || value.version !== 1) return null;
  if (!['knowledge-refresh', 'taxonomy-rebuild', 'page-handoff'].includes(value.operation)) return null;
  const stats = normalizeNonNegativeStats(value.stats);
  if (value.stats && !stats) return null;
  return {
    version: 1,
    operation: value.operation,
    status: value.ok === true ? (value.partial === true ? 'partial' : 'success') : 'failed',
    surface: value.surface === 'graph' ? 'graph' : 'viewer',
    revision: cleanOptionalText(value.revision, 200),
    stats,
    preserved: normalizeTextList(value.preserved, 10, 100),
    error: cleanOptionalText(value.error, 2000),
  };
}
```

所有字符串先限长，所有统计只接受有限非负整数。未知字段丢弃，不把消息对象直接保存或渲染。

- [ ] **Step 4: 验证 GREEN 和补丁幂等性**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/patch-integrated-workbench.mjs --check
```

Expected: PASS；补丁检查仍返回 `already-patched` 或在应用新版后返回 `already-patched`。

- [ ] **Step 5: Commit**

```bash
git -C <local-user-home> add -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
git -C <local-user-home> commit -m "feat: validate workbench operation messages" -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
```

### Task 2: 统一全局状态生命周期

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写状态呈现和关闭行为测试**

在补丁契约中断言生成的外层页面包含 `effect`、`recovery`、技术详情和显式关闭按钮。新增 Playwright 用例：

```js
test('failed refresh explains impact preservation and recovery', async ({ page }) => {
  await page.goto(workbenchUrl);
  await page.route('http://127.0.0.1:18081/api/refresh', route => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, error: 'simulated failure' }),
  }));
  await page.locator('#refreshKnowledge').click();
  const status = page.locator('#status');
  await expect(status).toHaveAttribute('data-kind', 'error');
  await expect(status).toContainText('本次刷新未完成');
  await expect(status).toContainText('当前页面和 Claude 草稿已保留');
  await expect(status.getByRole('button', { name: '重新刷新知识库' })).toBeVisible();
  await status.getByRole('button', { name: '关闭状态' }).click();
  await expect(status).toBeHidden();
});
```

- [ ] **Step 2: 确认 RED**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
npx playwright test tests/desktop_experience.spec.cjs -g "impact preservation" --workers=1
```

Expected: FAIL，现有状态条没有 effect、recovery 和关闭控件。

- [ ] **Step 3: 扩展 `setWorkbenchStatus`**

使用单一状态对象：

```js
setWorkbenchStatus({
  kind: 'error',
  title: '知识库刷新失败',
  detail: '本次刷新未完成',
  effect: '当前页面和 Claude 草稿已保留',
  recovery: { label: '重新刷新知识库', action: requestKnowledgeRefresh },
  technicalDetail: error.message,
  persistent: true,
});
```

只用 `textContent` 创建节点。`progress` 保持显示，`success` 自动收起，`warning/error` 保持到关闭或下一次操作。开始新操作时替换旧状态，不叠加 toast。

- [ ] **Step 4: 验证两视口和状态恢复**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
npx playwright test tests/desktop_experience.spec.cjs -g "refresh|desktop shell" --workers=1
```

Expected: PASS；状态条不遮挡顶栏、分隔条或 Claude Composer。

- [ ] **Step 5: Commit**

```bash
git add -- tests/desktop_experience.spec.cjs
git commit -m "test: cover unified workbench status"
git -C <local-user-home> add -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
git -C <local-user-home> commit -m "feat: unify workbench operation status" -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
```

### Task 3: 让现有服务返回真实结果统计

**Files:**
- Modify: `scripts/serve_kb.py`
- Modify: `tests/test_serve_kb.py`

- [ ] **Step 1: 写刷新与分类响应契约**

新增断言：

```python
self.assertEqual(payload["version"], 1)
self.assertEqual(payload["operation"], "knowledge-refresh")
self.assertTrue(payload["ok"])
self.assertRegex(payload["revision"], r"^[0-9a-f]+$")
self.assertGreaterEqual(payload["stats"]["nodes"], 0)
self.assertGreaterEqual(payload["stats"]["edges"], 0)
self.assertEqual(payload["stats"]["errors"], 0)
self.assertEqual(payload["stats"]["warnings"], 0)
```

分类重组响应使用 `operation == "taxonomy-rebuild"`，失败响应保留 `version`、`operation`、`ok: false` 和原始 `error`。

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_serve_kb.KnowledgeServerTests -v
```

Expected: FAIL，现有响应缺少版本或完整统计。

- [ ] **Step 3: 从已有生成结果组装响应**

增加无副作用辅助函数：

```python
def operation_payload(operation, revision, graph_data, health, **extra):
    return {
        "version": 1,
        "operation": operation,
        "ok": True,
        "revision": revision,
        "stats": {
            "nodes": int(graph_data.get("stats", {}).get("nodes", 0)),
            "edges": int(graph_data.get("stats", {}).get("edges", 0)),
            "errors": int(health.get("errors", 0)),
            "warnings": int(health.get("warnings", 0)),
        },
        **extra,
    }
```

复用已生成的 `graph-data.json` 和健康检查结果；不重复运行生成器，不解析命令行日志猜测统计，不新增端点。

- [ ] **Step 4: 验证接口成功和失败路径**

Run:

```bash
python3 -m unittest tests.test_serve_kb -v
```

Expected: PASS；失败测试仍证明旧静态内容可访问。

- [ ] **Step 5: Commit**

```bash
git add -- scripts/serve_kb.py tests/test_serve_kb.py
git commit -m "feat: report knowledge operation results"
```

### Task 4: 上报 Viewer 与图谱的真实上下文和结果

**Files:**
- Modify: `viewer.html`
- Modify: `graph-view.html`
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/test_graph_view_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写版本化消息和切换测试**

契约测试要求两个页面发送 `version: 1`。Playwright 验证页面与图谱切换：

```js
test('topbar context follows viewer and graph without claiming Claude read it', async ({ page }) => {
  await page.goto(workbenchUrl);
  await expect(page.locator('#contextSummary')).toContainText('首页.md');
  const frame = page.frames().find(item => item.url().includes('127.0.0.1:18081'));
  await frame.goto('http://127.0.0.1:18081/graph-view.html');
  await page.frameLocator('#knowledgeFrame').locator('[data-mode="combined"]').click();
  await expect(page.locator('#contextSummary')).toContainText('综合图谱');
  await expect(page.locator('#contextDetail')).not.toContainText('Claude 已读取');
});
```

图谱失败回退测试断言结果包含旧 revision、模式和选中节点的保留项。

- [ ] **Step 2: 确认 RED**

Run:

```bash
python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v
npx playwright test tests/desktop_experience.spec.cjs -g "topbar context" --workers=1
```

Expected: FAIL，消息缺少版本或外层缺少新上下文区域。

- [ ] **Step 3: 统一上报函数**

Viewer 发送：

```js
postWorkbenchMessage({
  type: 'kb-context', version: 1,
  context: { surface: 'viewer', title, file, pageType, revision: null }
});
```

图谱发送：

```js
postWorkbenchMessage({
  type: 'kb-context', version: 1,
  context: {
    surface: 'graph', title: modeLabel(state.mode), mode: state.mode,
    selected: state.selected ? { id: state.selected.id(), label: state.selected.data('label') } : null,
    visibleNodes: state.cy.nodes().not('.filtered').length,
    visibleEdges: state.cy.edges().not('.filtered').length,
    revision: state.revision,
  }
});
```

刷新与分类结束时发送 `kb-operation-result`。失败结果必须携带实际 `preserved` 列表，不发送成功事件。

- [ ] **Step 4: 验证切换、恢复和安全来源**

Run:

```bash
python3 -m unittest tests.test_viewer_contract tests.test_graph_view_contract -v
npx playwright test tests/desktop_experience.spec.cjs -g "context|refresh|graph" --workers=1
```

Expected: PASS；页面、图谱模式和选中节点变化后顶栏在一次消息往返内更新。

- [ ] **Step 5: Commit**

```bash
git add -- viewer.html graph-view.html tests/test_viewer_contract.py tests/test_graph_view_contract.py tests/desktop_experience.spec.cjs
git commit -m "feat: report active knowledge context"
```

### Task 5: 增加最近结果摘要与 Claude 上下文详情

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写会话恢复和上下文详情测试**

```js
test('last operation result and Claude context survive a page reload', async ({ page }) => {
  await page.goto(workbenchUrl);
  await page.evaluate(() => sessionStorage.setItem('radar-workbench-result-v1', JSON.stringify({
    version: 1, operation: 'knowledge-refresh', status: 'success',
    revision: 'abc123', stats: { nodes: 124, edges: 689, errors: 0, warnings: 0 },
    preserved: [], finishedAt: '2026-07-24T12:00:00.000Z'
  })));
  await page.reload();
  await page.locator('#lastResultButton').click();
  await expect(page.locator('#lastResultPanel')).toContainText('abc123');
  await expect(page.locator('#lastResultPanel')).toContainText('124 节点');
  await page.locator('#contextButton').click();
  await expect(page.locator('#contextDetail')).toContainText('<repo-root>');
  await expect(page.locator('#contextDetail')).toContainText(/标准|权限确认|危险跳过确认/);
});
```

Node 测试要求损坏 JSON、未知版本和单个非法字段局部回退，不清除工作台布局或 Claude 草稿键。

- [ ] **Step 2: 确认 RED**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
npx playwright test tests/desktop_experience.spec.cjs -g "last operation result" --workers=1
```

Expected: FAIL，缺少结果入口和上下文详情。

- [ ] **Step 3: 实现紧凑入口与会话存储**

外层 SHELL 新增：

```html
<button id="contextButton" type="button" aria-expanded="false" aria-controls="contextDetail">
  <span id="contextSummary">首页.md</span>
</button>
<button id="lastResultButton" type="button" aria-expanded="false" aria-controls="lastResultPanel">最近结果</button>
<section id="contextDetail" hidden></section>
<section id="lastResultPanel" hidden></section>
```

使用 `radar-workbench-result-v1` 保存规范化后的最近结果。危险模式使用 `--ui-danger` 和明确文本，不依赖颜色作为唯一信号。结果面板显示 revision、实际统计、健康状态、保留项、恢复动作和可展开技术详情。

- [ ] **Step 4: 部署并验证真实刷新结果**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/patch-integrated-workbench.mjs
<local-webui-root>/webui-control restart
npx playwright test tests/desktop_experience.spec.cjs -g "last operation result|successful refresh|context" --workers=1
```

Expected: PASS；真实刷新后摘要显示接口返回的 revision 与统计，刷新页面后仍可查看。

- [ ] **Step 5: Commit**

```bash
git add -- tests/desktop_experience.spec.cjs
git commit -m "test: cover trusted workbench handoff"
git -C <local-user-home> add -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
git -C <local-user-home> commit -m "feat: show workbench context and recent result" -- webui/patch-integrated-workbench.mjs webui/test-integrated-workbench.mjs
```

### Task 6: 安全边界、文档和全量验收

**Files:**
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `Web操作台使用与维护说明书.md`

- [ ] **Step 1: 写伪造消息拒绝测试**

```js
test('forged and malformed messages cannot replace trusted context', async ({ page }) => {
  await page.goto(workbenchUrl);
  const before = await page.locator('#contextSummary').textContent();
  await page.evaluate(() => window.dispatchEvent(new MessageEvent('message', {
    origin: 'http://127.0.0.1:18081',
    source: window,
    data: { type: 'kb-context', version: 1, context: { surface: 'viewer', file: '/etc/passwd', title: '伪造' } },
  })));
  await expect(page.locator('#contextSummary')).toHaveText(before);
});
```

另测未知版本、负数统计和超长错误详情均被拒绝。

- [ ] **Step 2: 更新说明书**

只记录经验证的最终行为：

- 状态条四类状态及自动收起规则；
- 最近结果仅在当前浏览器会话保留；
- 上下文详情与“Claude 尚未自动读取”的边界；
- 刷新、分类、Claude 错误的保留状态和恢复入口；
- 服务启动与故障排查命令。

- [ ] **Step 3: 运行全部自动化验证**

Run:

```bash
node <local-webui-root>/test-integrated-workbench.mjs
node <local-webui-root>/test-dangerous-mode.mjs
python3 -m unittest discover -s tests -v
npx playwright test tests/desktop_experience.spec.cjs tests/web_workbench.spec.cjs tests/taxonomy_observability.spec.cjs --workers=1
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

Expected:

```text
integrated workbench patch tests: PASS
dangerous mode patch tests: PASS
健康检查完成:ERROR 0 条,WARN 0 条。
```

所有 Playwright 用例通过；两个桌面视口无根级横向滚动、遮挡或控制台错误。

- [ ] **Step 4: 重启并执行一次完整人工旅程**

Run:

```bash
<local-webui-root>/webui-control restart
curl -fsS http://127.0.0.1:18080/ >/dev/null
curl -fsS http://127.0.0.1:18081/api/revision >/dev/null
```

在浏览器执行：进入工作台、切换页面、切换图谱并选节点、询问 Claude、刷新、查看最近结果、整页刷新、恢复现场。检查上下文、状态和结果摘要与实际操作一致。

- [ ] **Step 5: Commit**

```bash
git add -- tests/desktop_experience.spec.cjs Web操作台使用与维护说明书.md
git commit -m "docs: document trusted desktop workflow"
```

## 完成标准

- 外层工作台成为唯一全局状态呈现者；
- 成功只由真实完成事件触发；
- 最近结果只保存规范化数据并能在当前会话恢复；
- Claude 上下文显示当前对象、固定工作目录和运行模式，不声称已自动读取；
- 非法来源、窗口、版本、路径和统计无法修改 UI 状态；
- 所有自动化测试通过，健康检查为 `ERROR 0 / WARN 0`；
- 两个 Git 仓库均只提交本计划相关路径。
