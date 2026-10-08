# RadarLoom

[English](README.md) · [中文](README.zh-CN.md)

RadarLoom 是一个本地优先的技术知识工作台，建立在 Markdown、Git 和显式链接之上。

它把知识笔记、论文阅读、工程面试准备、Ideas 和项目资料组织成一个可搜索的工作区，并从页面链接中生成关系图谱和自动发现的知识社区。Markdown 文件是唯一事实来源；索引、图谱、分类状态和社区摘要都是可以重新生成和审查的派生产物。

## RadarLoom 能做什么

- 用 frontmatter、来源、信度、标签和 `[[双链]]` 管理 Markdown 知识页。
- 在 Viewer 中渲染 Markdown、LaTeX、Mermaid、表格和代码高亮，并提供搜索、收藏、历史、导出和阅读进度。
- 根据页面之间的显式引用生成知识关系图。
- 使用 Leiden 对知识页引用图做社区发现，支持层级下钻和社区摘要。
- 将知识页、工程面试、论文笔记和 Ideas 分成独立工作区。
- 可选接入 Claude Code，用于检索、创建知识页、生成面试页、精读论文和整理 Ideas。
- 提供健康检查、可重建产物、本地备份、HTTP API 和 GitHub Actions。

RadarLoom 不依赖 Claude 也可以独立运行。Claude Code 和它的 WebUI 属于可选的本机扩展。

## 产品概念图

这张概念图展示了 RadarLoom 的桌面工作流：浏览知识页、查看社区图谱，并在需要时让 Claude 处理当前页面。

![RadarLoom 产品概念图](docs/assets/radarloom-product-concept.png)

## 架构

```mermaid
flowchart TB
    M[Markdown 页面] --> I[build_index.py]
    M --> G[显式 [[双链]]]
    G --> R[render_graph.py]
    G --> L[Leiden 社区发现]
    L --> C[community-data.json]
    I --> V[Viewer 与搜索]
    R --> W[交互式图谱工作台]
    C --> W
    P[论文笔记] --> V
    D[Ideas] --> IV[Idea Lab]
    A[可选 Claude Code] --> M
    A --> P
    A --> D
```

![RadarLoom 架构图](docs/assets/radarloom-architecture.png)

## 快速开始

环境要求：

- Python 3.11 或更高版本
- Node.js 20 或更高版本，用于 JavaScript 检查
- 支持现代 JavaScript 的浏览器

克隆仓库并安装分类和图谱依赖：

```bash
git clone <your-repository-url>
cd radar-loom
python3 -m pip install -r requirements-taxonomy.txt
npm ci
```

生成索引和图谱产物：

```bash
python3 scripts/build_index.py
python3 scripts/render_graph.py
python3 scripts/check_health.py
python3 scripts/taxonomy_cli.py validate
```

启动本地知识库服务：

```bash
python3 scripts/serve_kb.py --host 127.0.0.1 --port 18081 --directory .
```

打开以下地址：

- Viewer：`http://127.0.0.1:18081/viewer.html`
- 交互图谱：`http://127.0.0.1:18081/graph-view.html`
- 社区下钻：`http://127.0.0.1:18081/graph-view.html?mode=community`
- 论文笔记：`http://127.0.0.1:18081/viewer.html?section=notes`
- Idea Lab：`http://127.0.0.1:18081/ideas/viewer.html`

浏览器资源已经放在 `vendor/` 下。如需重新下载资源，运行 `bash scripts/vendor_web_assets.sh`。如果同时维护外部 Claude WebUI，可以设置 `WEBUI_VENDOR` 指向它的资源目录。

## 工作区

### 知识页

概念页放在 `pages/`。每页描述一个概念，并记录来源、信度、标签以及与其他页面的链接。新建页面可以使用 `create-knowledge-page` Skill，也可以使用命令行模板：

```bash
python3 scripts/new_page.py "Concept Name EnglishName" \
  --tags KG \
  --summary "这页解释的内容" \
  --source "https://example.com/source" \
  --confidence 中
```

### 工程面试页

工程面试页也放在 `pages/`，但使用 `page_type: interview`，并拥有独立的索引、图谱、taxonomy 和创建 Skill。它们不会进入知识页社区图谱。

### 论文笔记

论文笔记放在 `paper-notes/`，并在 Viewer 的“论文笔记”专区渲染。原始 PDF 属于本地输入，默认被 Git 忽略。使用 `paper-reading` Skill 生成笔记时，应记录来源位置、核心结论、限制和后续问题。

### Idea Lab

Ideas 放在 `ideas/` 下，拥有独立的页面、索引、图谱、健康检查和 `capture-idea` Skill。Idea Lab 不会修改主知识页的分类。

## 图谱和分类模型

页面图谱只使用正文中的显式引用：

```text
页面 A [[页面 B]]  ->  A -> B
```

知识社区从知识页引用图中发现。项目页、MOC 页和工程面试页不进入这张图。Leiden 以显式引用图作为输入，生成的数据写入 `community-data.json`。图谱页面先显示顶层社区，点击后再加载子社区或成员页面。

旧的 taxonomy 系统仍可用于动态分类实验。分类注册表保存在 `taxonomy.json`，可以单独校验和重组。

页面上的静态标签作为历史证据保留，动态自动归属保存在 `taxonomy.json`，分类运行不会反复改写页面 frontmatter。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `python3 scripts/build_index.py` | 重建知识页和面试页索引 |
| `python3 scripts/render_graph.py` | 重建页面图谱、社区数据和 Mermaid 快照 |
| `python3 scripts/check_health.py` | 检查元数据、链接、公式、索引和生成物 |
| `python3 scripts/community_graph.py` | 单独重建知识社区 |
| `python3 scripts/taxonomy_cli.py validate` | 校验 taxonomy 注册表 |
| `python3 scripts/local_backup.py create` | 创建本地备份 |
| `python3 scripts/doctor.py` | 检查本地依赖和服务 |
| `python3 ideas/scripts/check_idea_health.py` | 检查 Idea Lab |

## 测试和 CI

本地运行公开仓库检查：

```bash
npm run refresh:artifacts
npm run test:python
node scripts/ci_node_checks.mjs
```

GitHub Actions 会运行 Python 3.11/3.12 测试、Node 20/22 契约检查，以及生成物和健康检查。需要外部 Claude WebUI 的测试只有在显式配置本机控制脚本时才会运行。

## 可选的 Claude Code 集成

RadarLoom 可以脱离 Claude 使用。如果需要接入 Claude，请在本机单独安装 Claude Code 和兼容的 Claude WebUI，再将 WebUI 工作目录指向本仓库。仓库包含项目级 Skill 和提示词契约，但不会保存 API Key、会话状态或外部 WebUI 安装目录。

本机部署说明见 [Web 操作台使用与维护说明书](Web操作台使用与维护说明书.md)。其中的 `<repo-root>` 和 `<local-webui-root>` 是路径占位符，需要替换成你自己的目录。

## 数据和隐私

这个仓库面向个人本地知识，公开前请检查其中的内容。个人笔记、原始 PDF、备份、日志、凭据和他人项目材料不应上传到公开仓库。详细说明见 [SECURITY.md](SECURITY.md) 和 [GitHub 发布清单](docs/GITHUB发布清单.md)。

源数据是 Markdown 文件。索引和图谱等生成文件在有助于浏览和审查时可以提交，它们都能通过上面的命令重新生成。

## 贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)，了解页面规范、检查命令和 Pull Request 要求。

## 许可证

代码和项目文档使用 [MIT License](LICENSE)。知识页和附加材料可能有各自的来源与版权限制，重新分发前请检查页面中的来源信息。
