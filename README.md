# 技术雷达知识库

面向 KG / RAG / LLM 等技术方向的纯 Markdown 知识库，由用户与 CC 共同维护。系统以检索优先和增量摄入为两条核心要求：回答问题前先检索库内页面；新知识回到已有概念追加或建立新页，并以 Git 留痕。

这是一个本地优先的 Markdown 知识库工具：页面、双链、索引、图谱和自动分类都可以用 Git 追踪。Claude Code 集成属于可选的本机扩展；核心 Viewer、图谱、索引和健康检查不依赖 Claude 或云端服务。

完整的本机 Claude/WebUI 配置见 [Web 操作台使用与维护说明书](Web操作台使用与维护说明书.md)。其中带有 `<repo-root>`、`<local-webui-root>` 的命令是路径模板，请替换为实际目录。

## 快速开始

需要 Python 3.11+；自动分类和部分测试需要 `requirements-taxonomy.txt` 中的依赖。浏览器资源已经随仓库提供。

```bash
git clone <your-repository-url>
cd <repository-directory>
python3 -m pip install -r requirements-taxonomy.txt
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
python3 scripts/serve_kb.py --host 127.0.0.1 --port 18081 --directory .
```

然后打开 `http://127.0.0.1:18081/viewer.html`。交互图谱地址是 `http://127.0.0.1:18081/graph-view.html`。

运行测试：

```bash
npm ci
npm run test:python
node scripts/ci_node_checks.mjs
```

Claude WebUI 需要单独安装在本机，并通过环境变量或外部控制脚本连接到本知识库目录；仓库不包含 API Key、Claude 会话配置或 WebUI 安装目录。

## 本地可靠性

- 本机 WebUI 控制脚本的 `start` 命令会在 `.backups/` 自动保留每日一份 ZIP 备份，默认保留最近 14 份。
- 手动备份：`python3 scripts/local_backup.py create`；校验：`python3 scripts/local_backup.py verify <备份.zip>`；恢复演练：`python3 scripts/local_backup.py stage-restore <备份.zip> --destination /tmp/kb-restore`。
- 环境诊断：`python3 scripts/doctor.py`，只读检查依赖、关键文件、端口和 Git 工作树。
- Viewer 在服务暂不可用时可显示最近一次只读缓存；缓存不是正式数据，服务恢复后以 Markdown 文件为准。

面向实习展示的项目背景、架构、真实维护案例和可复核指标见 [项目展示稿](docs/project-portfolio.md)。

## Idea Lab

`ideas/` 是与技术知识库完全隔离的想法实验室，用于保存原始灵感、失败尝试、阻塞点、重新启动条件和 Idea 组合关系。它拥有独立索引、图谱、健康检查和项目级 `capture-idea` Skill，不进入主知识库分类或图谱统计。

- Web 入口：操作台顶部的 `Ideas`
- 独立入口：`http://127.0.0.1:18081/ideas/viewer.html`
- 快速创建：`python3 ideas/scripts/new_idea.py "原始想法" --problem "想解决的问题"`
- 独立检查：`python3 ideas/scripts/check_idea_health.py`

快速记录不会调用 Claude；需要整理、追加尝试或组合旧 Idea 时使用 `$capture-idea`。

与 `MASTER_knowledge_base.md` 的分工：那边是体系化沉淀的“教科书”，这里是持续吸收、检索和关联的个人知识外脑。

## 核心范式

1. 一个概念一个页面，放在 `pages/` 下，文件名即概念名。
2. 同一概念的新进展回到原页面追加“更新记录”，不建第二页。
3. 页面关系使用双方括号链接；机器生成的 `_index.md` 是 CC 的检索入口，不手工编辑。
4. `python3 scripts/render_graph.py` 按需生成交互图谱数据、核心概览和八个分类子图。
5. 来源必须真实可达，并尽量记录 PDF 页码或章节。
6. 页面保留人工标签作为历史证据；动态自动归属保存在可审计、可回滚的 `taxonomy.json`，不反复改写页面 frontmatter。

## 向 CC 提问

CC 先读取 `_index.md`，再打开命中的少量页面。库内命中时按页面内容回答并注明页面与来源；部分命中时区分库内内容和补充知识；未命中时明确说明库内没有该条目。

## 给 CC 喂料

知识可以来自对话、文本文件或 PDF，不要求固定周频率，有料时增量摄入。文本原始件进入 `raw/inbox/`，PDF 进入 `papers/`；文件内容先形成待建/待更新页面清单，再逐页处理。老概念追加，新概念使用：

```bash
python3 scripts/new_page.py "概念名 EnglishName" \
  --tags KG \
  --summary "一句话说明这页讲什么" \
  --source "papers/example.pdf p.3-5" \
  --confidence 中
```

每次摄入以生成索引、健康检查和 Git 提交收尾。

含数学内容时必须使用 LaTeX 定界符:行内公式写成 `$...$`,独立公式使用单独成行的 `$$...$$`;不得用 Unicode 符号或普通文本模拟公式。`check_health.py` 会以 `ERROR E11` 拦截高置信度的未定界数学表达式。

## 脚本

| 脚本 | 用途 | 命令 |
|---|---|---|
| `build_index.py` | 从 frontmatter 生成 `_index.md` 检索索引 | `python3 scripts/build_index.py` |
| `render_graph.py` | 生成知识图、`community-data.json`、核心概览和八个分类 Mermaid 图谱 | `python3 scripts/render_graph.py` |
| `community_graph.py` | 仅以知识页显式引用生成 Leiden 社区派生数据 | `python3 scripts/community_graph.py` |
| `taxonomy_cli.py` | 迁移、增量分类、全局重组、状态和校验 | `python3 scripts/taxonomy_cli.py --help` |
| `new_page.py` | 按模板建页并刷新索引 | 见“给 CC 喂料” |
| `check_health.py` | 检查格式、链接、来源、摘要和索引一致性 | `python3 scripts/check_health.py` |

## 持续集成与本地检查

GitHub Actions 位于 `.github/workflows/ci.yml`，会在 Push 和 Pull Request 时运行：

- Python 3.11/3.12 单元测试；
- Node 20/22 的 Viewer/脚本契约检查；
- 索引、图谱、健康检查和 taxonomy 产物校验。

本地运行等价检查：

```bash
npm run test:python
node scripts/ci_node_checks.mjs
npm run refresh:artifacts
```

真实 Claude WebUI 联调依赖本机 Claude CLI 和独立 WebUI 服务，不在公共 CI 中启动；可按 `npm run test:e2e:all` 在配置好本地环境后执行。

## 图谱工作台

知识库静态服务启动后打开 `http://127.0.0.1:18081/graph-view.html`。工作台使用 Cytoscape.js 与 fCoSE 布局，提供知识关系、社区结构、分类结构和综合视图，支持节点搜索、动态分类导航、一跳聚焦、归属分数与信号详情和 Viewer 跳转。知识社区只使用概念知识页之间的显式引用边，由 Leiden 派生并写入 `community-data.json`；工程/项目、面试和 MOC 不参与该社区图。数据来自 `graph-data.json`、`community-data.json` 与 `taxonomy.json`；`viewer.html?f=graph.md` 及八个分类 Mermaid 图保留为可审计备用视图。

## 可演化分类

Viewer 左侧的动态分类摘要是紧凑状态入口，点击后使用精确链接
`graph-view.html?profile=knowledge&mode=taxonomy` 打开分类结构。候选分类在达到
2 页时出现，达到 3 页才允许晋升；候选名称由本地规则生成，不调用 Claude。
分类快照过期或运行失败时摘要会明确显示状态，旧快照仍保留用于审计。

首次迁移及日常检查：

```bash
python3 scripts/taxonomy_cli.py migrate
python3 scripts/taxonomy_cli.py sync
python3 scripts/taxonomy_cli.py status
python3 scripts/taxonomy_cli.py validate
```

页面保存后的增量分类只处理变化页面；累计变化达到 5 页或距上次全局运行满 7 天时自动重组，也可在图谱页手动触发。向量和中间缓存位于未提交的 `.cache/taxonomy/`，分类快照、稳定 ID、别名、重定向和事件保存在提交到 Git 的 `taxonomy.json`。

## 标签与信度

分类标签：`KG`、`RAG`、`LLM机制`、`可信度`、`多智能体`、`基础`、`评测`、`前沿`。

项目标签：`GSAD`、`ChronoLink`、`EvidenceFirst`、`TripleChecker`、`CoMaGRAG`。

- `高`：一手论文或官方文档精读，或教科书级共识知识。
- `中`：摘要、可靠二手转述或 PDF 讲义类材料整理。
- `低`：未验证的二手消息。

## 月度维护

1. 运行索引生成和健康检查，清零 ERROR。
2. 运行图谱脚本查看全库连接状态。
3. 检查 `GSAD`、`ChronoLink` 等项目标签是否长期为 0；为 0 表示该方向尚无知识页沉淀。
4. 人工判断成熟内容是否升级合并进 `MASTER_knowledge_base.md`，本库脚本不读写该文件。

CC 行为协议见 `CLAUDE.md`。
