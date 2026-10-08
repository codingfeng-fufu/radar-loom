# Web 操作台可信工作闭环设计

## 目标

在不增加搜索、页面质量面板或活动历史中心的前提下，收口桌面端三个产品问题：统一状态语言、展示最近一次操作结果、明确 Claude 当前实际上下文。

用户在任何关键操作后都应能回答四个问题：系统正在做什么、哪些内容发生了变化、失败时保留了什么、Claude 当前基于什么工作。

## 范围

本轮覆盖：

- 知识库刷新与分类重组的统一状态表达；
- 最近一次操作的结构化结果摘要；
- 当前页面、图谱节点、项目目录和 Claude 运行模式的上下文可见性；
- 成功、部分成功、失败和超时情况下的保留状态与恢复动作；
- 桌面端真实浏览器回归和无障碍语义。

本轮不覆盖：

- 全局搜索或搜索结果重排；
- 页面质量评分或质量仪表盘；
- 跨会话活动历史；
- 新的知识库业务操作；
- 移动端重新设计。

## 设计原则

1. 外层工作台是唯一的全局状态呈现者，Viewer、图谱和 Claude 只上报自身事实。
2. iframe 之间仅传输结构化数据，不传 HTML，不共享 CSS。
3. “成功”只能来自真实完成事件，不能由固定计时器推断。
4. 操作失败不能清空当前页面、图谱视图或 Claude 草稿。
5. 默认界面保持克制，详细信息按需展开。
6. 只保存当前会话内最近一次结果，不建设活动历史系统。

## 信息架构

### 顶栏上下文

顶栏现有文件信息扩展为一个紧凑的上下文区域，默认显示当前主要对象：

- 页面模式：页面标题或相对路径；
- 图谱模式：图谱模式和选中节点；
- 项目：Claude 当前工作目录固定显示为知识库项目；
- 运行模式：标准、权限确认、危险跳过确认三类之一。

上下文区域不展示操作教学文字。鼠标悬停或点击后出现详情浮层，列出完整路径、页面类型、图谱筛选摘要、Claude 工作目录和运行模式说明。

### 全局状态条

全局状态条复用现有 `#status`，但采用固定结构：

- `kind`：`progress | success | warning | error`；
- `title`：一句可扫描的状态标题；
- `detail`：影响范围或当前阶段；
- `effect`：失败或部分成功时，明确哪些状态已保留；
- `recovery`：用户可以执行的一个恢复动作；
- `persistent`：是否保持到用户关闭或下一次操作。

进行中状态保持显示。成功状态自动收起但可从最近结果入口重新查看。警告和错误保持显示，直到用户关闭或发起新操作。

### 最近结果摘要

顶栏增加一个紧凑的“最近结果”入口，只保存当前 `sessionStorage` 会话内最后一次操作。摘要支持以下字段：

```js
{
  version: 1,
  operation: 'knowledge-refresh' | 'taxonomy-rebuild' | 'page-handoff',
  status: 'success' | 'partial' | 'failed',
  startedAt: 'ISO-8601',
  finishedAt: 'ISO-8601',
  revision: 'string | null',
  changes: [
    { label: '索引', value: '已更新' },
    { label: '图谱', value: '124 节点 · 689 边' }
  ],
  health: { errors: 0, warnings: 0 } | null,
  preserved: ['当前页面', 'Claude 草稿'],
  recovery: '重新刷新知识库 | null',
  technicalDetail: 'string | null'
}
```

结果面板只显示真实可获得的数据。后端未返回变更数量时显示“已更新”，不推测数量。原始错误放在可展开技术详情中。

## 组件边界

### 外层 WebUI

`<local-webui-root>/patch-integrated-workbench.mjs` 负责：

- 校验并消费结构化消息；
- 维护统一状态模型；
- 保存和恢复最近一次结果；
- 渲染顶栏上下文和结果摘要；
- 映射用户可读错误文案；
- 拒绝来源、窗口或数据结构不合法的消息。

### Viewer

`viewer.html` 负责上报：

- 当前页面上下文；
- 页面或索引恢复的真实完成结果；
- 页面类型和相对路径；
- 刷新失败时实际保留的页面。

Viewer 不决定外层显示文案。

### 图谱

`graph-view.html` 负责上报：

- 当前模式、选中节点和筛选摘要；
- revision、节点数和边数；
- 分类重组和图谱恢复的完成结果；
- 失败时保留的模式、选中节点和 revision。

图谱不在外层注入 DOM，也不依赖外层样式。

### 知识库服务

`scripts/serve_kb.py` 只补充现有接口响应中可直接获得的结果数据，例如 revision、生成阶段、节点数、边数和健康检查计数。不新增业务端点，不扫描 Git 历史，不保存操作记录。

## 消息协议

保留 `kb-context` 和 `kb-refresh-result`，统一为版本化结构：

```js
{
  type: 'kb-context',
  version: 1,
  context: {
    surface: 'viewer' | 'graph',
    title: 'string',
    file: 'relative/path.md | null',
    mode: 'knowledge | taxonomy | combined | null',
    selected: { id: 'string', label: 'string' } | null,
    revision: 'string | null'
  }
}
```

```js
{
  type: 'kb-operation-result',
  version: 1,
  operation: 'knowledge-refresh' | 'taxonomy-rebuild',
  ok: true,
  partial: false,
  surface: 'viewer' | 'graph',
  revision: 'string | null',
  stats: { nodes: 124, edges: 689, errors: 0, warnings: 0 },
  preserved: [],
  error: null
}
```

外层只接受 `VIEWER_ORIGIN` 且 `event.source === knowledgeFrame.contentWindow` 的消息。未知版本、未知操作、负数统计、绝对路径和超长字符串全部拒绝。

## 状态生命周期

知识库刷新依次经历：

1. `progress`：正在更新分类、索引与图谱；
2. `progress`：接口完成，正在恢复当前 Viewer 或图谱；
3. `success`：收到当前 surface 的真实完成事件；
4. `warning`：部分产物已更新，但当前 surface 未能恢复；
5. `error`：生成接口失败，保留旧视图和 Claude 草稿；
6. `warning`：超时，系统不声明成功，允许用户手动重试。

分类重组遵循同一生命周期，但 operation 为 `taxonomy-rebuild`，并在成功结果中显示新 revision 和分类统计。

## Claude 上下文可见性

外层维护一个经过校验的 `activeContext`，同时显示 Claude 固定工作目录和运行模式。询问、创建知识页和创建面试页时，提示词仍通过现有受控输入桥接，不自动发送。

上下文详情至少包含：

- 当前页面路径或图谱模式；
- 图谱选中节点和可见节点/边数量；
- Claude 工作目录 `<repo-root>`；
- 当前运行模式；
- 危险模式的明确视觉警告。

外层不得声称 Claude 已读取页面，只能说明“将要求 Claude 读取”或“提示词已包含当前上下文”。

## 错误处理

所有用户可见错误遵循相同结构：

- 标题：发生了什么；
- 影响：本次操作未完成或部分完成；
- 保留：页面、图谱视图和草稿的实际保留情况；
- 恢复：一个明确动作；
- 技术详情：原始错误，可展开查看。

`401`、`429`、`stream_error`、Claude 二进制缺失继续使用现有映射。刷新和分类错误不得自动重试，避免重复执行生成任务。

## 存储

使用版本化 `sessionStorage`：

- `radar-workbench-result-v1`：最近一次操作结果；
- 继续使用现有 `radar-workbench-state-v1` 和 Claude 草稿键；
- 数据无效时逐字段回退，不清空其他有效状态；
- 关闭浏览器会话后自动失效。

不使用服务端数据库，不写入知识库 Markdown，不建立跨会话历史。

## 验收标准

1. 用户无需查看 iframe 内部状态即可判断刷新是否真正完成。
2. 刷新成功后能看到 revision、图谱规模和健康状态中实际可获得的部分。
3. 刷新或分类失败后，结果明确列出保留状态和恢复动作。
4. 页面与图谱切换后，顶栏上下文在一次消息往返内更新。
5. Claude 上下文详情始终显示知识库工作目录和当前运行模式。
6. 伪造来源、错误窗口或非法消息无法改变上下文和结果摘要。
7. 刷新、历史会话、连续输入、公式和图谱桌面回归继续通过。
8. `python3 scripts/check_health.py` 最终为 `ERROR 0 / WARN 0`。

## 测试策略

- Node 契约测试：状态规范化、消息校验、结果存储、Claude 错误映射；
- Python 契约测试：刷新和分类接口的结构化响应；
- Playwright：成功刷新、失败保留、分类部分成功、上下文切换、恶意消息拒绝、会话恢复；
- 两个桌面视口：`1440x900` 与 `1112x1243`；
- 最终全量运行 Viewer、图谱、服务、WebUI 补丁和桌面旅程测试。
