# 搜索、页面质量与操作历史实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为桌面工作台增加统一搜索、客观页面质量摘要和本地操作历史。

**Architecture:** Python 索引脚本生成可复用的页面字段，Viewer 提供当前页质量摘要；外层 WebUI 独立加载两个专区索引并执行统一搜索，同时接收版本化操作结果并写入受限的 localStorage。两个专区的页面导航和图谱仍然分离。

**Tech Stack:** Python stdlib、原生 HTML/CSS/JavaScript、Node 契约测试、Playwright。

---

### Task 1: 扩展索引为搜索与质量数据源

**Files:**
- Modify: `scripts/build_index.py`
- Modify: `tests/test_build_index.py` 或现有索引测试文件
- Modify: `_index.md`、`_interview_index.md`（运行脚本生成）

- [ ] **Step 1: 写索引字段测试**

断言普通页记录包含标题、别名、标签、摘要、来源、信度、出站链接和质量字段；面试页记录包含岗位、难度、知识方向和摘要。缺失字段必须使用空列表或 `null`，不能省略导致消费者分支不一致。

- [ ] **Step 2: 运行索引测试确认失败**

运行 `python3 -m unittest tests.test_build_index -v`，确认新增字段尚不存在。

- [ ] **Step 3: 实现字段提取**

复用现有 Markdown 元数据解析和链接解析，生成稳定的结构化字段；统计出站链接时只计算页面链接，记录解析失败项；质量对象只包含客观布尔值和计数，不执行模型调用。

- [ ] **Step 4: 生成索引并验证**

运行 `python3 scripts/build_index.py` 和索引测试，检查 0 个缺摘要页面、字段可被 JSON/Markdown 消费。

- [ ] **Step 5: Commit**

按精确路径提交脚本和测试；生成索引若包含用户已有变更，先检查 diff 后再单独暂存。

### Task 2: Viewer 当前页质量摘要

**Files:**
- Modify: `viewer.html`
- Modify: `tests/test_viewer_contract.py`
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写 Viewer 契约和浏览器失败测试**

断言 Viewer 具备质量入口、摘要/来源/信度/标签/引用统计和未知状态；加载缺失字段页面时显示“未检测到”，不显示成功徽章。

- [ ] **Step 2: 实现质量数据解析与面板**

从当前索引记录读取质量字段，使用 `textContent` 渲染；质量面板为当前页内的紧凑可展开区域，不重建正文、不改变目录高度。断链数量大于零时链接到现有图谱/健康信息，不在前端重新扫描全库。

- [ ] **Step 3: 验证桌面布局和失败降级**

运行 Viewer 契约测试及 Playwright 质量用例，覆盖正常页、缺失元数据页和页面切换后面板更新。

- [ ] **Step 4: Commit**

精确提交 Viewer、契约测试和新增回归测试。

### Task 3: 外层统一搜索

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `viewer.html` 或现有 Viewer 导航接口（仅在需要提供目标 URL 时）
- Modify: `tests/desktop_experience.spec.cjs`

- [ ] **Step 1: 写纯函数搜索测试**

测试 Unicode 小写归一化、空白分词、标题前缀优先级、专区分组、缺索引和结果字段限长。

- [ ] **Step 2: 实现索引加载和搜索面板**

工作台初始化分别请求 `_index.md`、`_interview_index.md`，解析为内存数组；搜索只在输入变化时过滤已加载数组，结果通过现有 iframe URL/消息导航打开。未知或不完整记录丢弃，不把原始对象直接注入 DOM。

- [ ] **Step 3: 实现错误和无结果状态**

索引请求失败显示专区级错误但保留另一专区；无结果显示查询词和清除入口；搜索面板不覆盖 Claude Composer 或分隔条。

- [ ] **Step 4: 验证桌面搜索与跨专区跳转**

Playwright 覆盖普通页命中、面试页命中、同词分区展示、清除、索引失败和刷新恢复。

- [ ] **Step 5: Commit**

精确提交 WebUI 补丁、Node 契约和知识库回归测试。

### Task 4: 本地操作历史

**Files:**
- Modify: `<local-webui-root>/patch-integrated-workbench.mjs`
- Modify: `<local-webui-root>/test-integrated-workbench.mjs`
- Modify: `tests/desktop_experience.spec.cjs`
- Modify: `Web操作台使用与维护说明书.md`

- [ ] **Step 1: 写历史规范化和上限测试**

断言只保留允许字段、错误摘要限长、最多 50 条、最新优先、非法消息被丢弃，且不含正文或 Claude 内容。

- [ ] **Step 2: 实现 localStorage 适配器和历史面板**

在已有 `normalizeOperationResult` 后写入 `radar-workbench-history-v1`；localStorage 异常时使用内存退化。历史入口支持状态筛选、单条展开和清空。

- [ ] **Step 3: 接入现有结果事件**

成功、警告和错误结果均写入历史；进度事件不产生历史条目；重复 revision/operation 在同一时间窗口内不重复写入。

- [ ] **Step 4: 验证刷新恢复、隐私和布局**

Playwright 覆盖写入、刷新恢复、筛选、清空、本地存储禁用和长错误摘要；检查面板不改变工作台三栏尺寸。

- [ ] **Step 5: 更新说明书并 Commit**

只补充历史字段、保留策略和隐私语义，精确提交相关文件。

### Task 5: 全量验证与交付收口

- [ ] **Step 1: 运行 Python 全量测试**

运行 `python3 -m unittest discover -s tests -q`，必须 0 failures。

- [ ] **Step 2: 运行 WebUI 契约与桌面 Playwright**

运行两个 Node 契约测试和桌面回归；历史窄视口测试若失败，记录为测试兼容性问题，不改变桌面布局。

- [ ] **Step 3: 重建索引、图谱和健康检查**

运行 `build_index.py`、`render_graph.py`、`check_health.py`，确认图谱无断链、健康检查无 ERROR/WARN。

- [ ] **Step 4: 检查服务和精确 Git diff**

确认 18080/18081 服务可访问；只报告本轮文件和用户原有未提交内容的边界。

