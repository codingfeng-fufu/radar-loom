# Web 操作台部署完成报告

> 日期:2026-07-12<br>
> 范围:《补充任务书_Web操作台收尾》,经用户授权跳过“429 时停止”的前置阻断<br>
> 结论:本地聊天入口与知识库浏览入口均已部署;浏览功能和火山 endpoint 对话/摄入补验收均已通过

## 访问入口

| 用途 | 本机地址 | 监听范围 |
|---|---|---|
| Claude Code WebUI 聊天 | `http://127.0.0.1:18080` | 仅 `127.0.0.1` |
| 技术雷达知识库浏览 | `http://127.0.0.1:18081/viewer.html` | 仅 `127.0.0.1` |
| 交互式知识图谱 | `http://127.0.0.1:18081/graph-view.html` | 仅 `127.0.0.1` |

远程使用时,在 VSCode 的“端口”面板分别转发 `18080` 和 `18081`,可见性保持为“专用/本地”,再打开转发后的地址。两个服务均未开放公网,未配置域名或 HTTPS。

## 启停命令

聊天入口:

```bash
/home/u2023312337/webui/webui-control start
/home/u2023312337/webui/webui-control stop
/home/u2023312337/webui/webui-control restart
/home/u2023312337/webui/webui-control status
```

知识库浏览入口:

```bash
/home/u2023312337/webui/kbserve-control start
/home/u2023312337/webui/kbserve-control stop
/home/u2023312337/webui/kbserve-control restart
/home/u2023312337/webui/kbserve-control status
```

两个服务都由 tmux 托管。服务器重启后需要手动运行两个 `start` 命令;当前环境没有可用的 root 权限或 user-bus,未配置系统级自启动。

## Viewer 使用方式

- 无参数打开 `viewer.html` 时显示 `首页.md`。
- 左侧目录从 `_index.md` 实时读取,按分类折叠;点击条目打开相应概念页。
- 直接地址格式为 `viewer.html?f=pages/页面名.md`;中文和空格由浏览器进行 URL 编码。
- 页面 frontmatter 在正文前以“页面元数据”折叠块展示,默认收起。
- 正文按 GFM 渲染,双方括号链接可跳转,代码块启用 highlight.js,Mermaid 代码块生成图形。
- 数学公式由 KaTeX 渲染,支持行内 `$...$`、`\\(...\\)` 和块级 `$$...$$`、`\\[...\\]`;错误公式保留原文且不阻断页面。
- `viewer.html?f=graph.md` 打开全库核心图谱。
- `graph-view.html` 打开 Cytoscape.js/fCoSE 交互图谱,支持搜索、分类/项目筛选、一跳邻居、详情和 Viewer 跳转;数据由 `python3 scripts/render_graph.py` 生成到 `graph-data.json`。
- 查看器为只读工具,不提供编辑、搜索或主题切换。

查看器的 marked、DOMPurify、highlight.js 和 Mermaid 由用户浏览器从 CDN 加载。静态服务器本身不安装 npm 包;浏览器断网或 CDN 不可达时,Markdown 渲染功能不可用。

## WebUI 权限模式

聊天输入框下方的模式按钮依次循环 `normal`、`plan`、`accept edits` 和 `dangerously skip permissions`。第四档会让 Claude 不经确认执行命令和修改文件,界面显示红色警示;它不作为默认值,刷新页面后回到 `normal`。

WebUI 安装包重装后需重新应用并校验本地补丁:

```bash
node /home/u2023312337/webui/patch-dangerous-mode.mjs
node /home/u2023312337/webui/patch-dangerous-mode.mjs --check
```

## 报告约定

面向用户阅读的盘点报告、迁移报告和阶段汇总等成品,同时保留 Markdown 源文件并在 `reports/` 下生成一份自包含 HTML,命名为 `YYYY-MM-DD_主题.html`。HTML 样式内嵌,可以通过 18081 静态服务直接打开。知识库概念页仍然只使用 Markdown。

本报告对应的 HTML 为 `reports/2026-07-12_Web操作台部署完成报告.html`。

## 验收记录

| 验收项 | 状态 | 实际结果 |
|---|---|---|
| 默认首页和 `_index.md` 侧栏 | 通过 | 浏览器显示首页,侧栏解析出 9 个分组 |
| 概念页和 frontmatter | 通过 | 打开 `GraphRAG 架构`,元数据折叠块存在且默认收起 |
| 双链导航 | 通过 | 该页面生成 6 个 viewer 内部链接 |
| Mermaid | 通过 | `graph.md` 实际生成 1 个 SVG,页面无渲染错误 |
| 数学公式 | 通过 | 四种定界符生成 4 个 KaTeX 节点与 2 个块级节点;错误公式不阻断,390px 下无页面溢出 |
| 路径校验 | 通过 | `?f=../xxx.md` 显示拒绝信息,未发起库外文件读取 |
| 基本 sanitize | 通过 | 渲染结果通过 DOMPurify 后才进入正文 DOM |
| 桌面/移动布局 | 通过 | 390×844 下显示移动导航,无横向页面溢出 |
| 监听地址 | 通过 | 18080 和 18081 均只监听 `127.0.0.1` |
| UI 真实检索对话 | 通过 | 2026-07-13 补验收:实际读取 `_index.md` 与 `pages/GraphRAG 架构.md`,返回完整答案 |
| UI 测试摄入并恢复 | 通过 | 临时页进入索引后页面数 88→89,健康检查 0/0;随后删除并恢复至 88 页,健康检查仍为 0/0 |
| 危险权限第四档 | 通过 | UI 可选择且显示红色警示;刷新恢复 normal;真实 API init 为 `bypassPermissions`,普通请求仍为 `default` |
| 交互式知识图谱 | 通过 | 103 节点、470 边完成 fCoSE 布局;搜索、筛选、一跳聚焦、详情跳转及 1440×900/390×844 布局通过 |

2026-07-12 的 429 历史证据保存在 `/home/u2023312337/webui/preflight.ndjson`。2026-07-13 补验收日志保存在 `/home/u2023312337/webui/retrieval-20260713.ndjson`、`ingest-20260713.ndjson` 和 `ingest-restore-20260713.ndjson`;补验收期间未再出现 429。

## 已知限制

1. 候选一聊天区不渲染 Markdown,也不提供知识库文件树;浏览知识页和成品报告使用 18081 入口。
2. 火山 endpoint 曾于 2026-07-12 返回 429;2026-07-13 已恢复并完成补验收,后续额度状态仍由上游服务控制。
3. 查看器的渲染库依赖浏览器访问 CDN。
4. 两个服务在服务器重启后均需手动启动。
5. Python 静态服务器是只读访问用途的轻量服务,不承担身份认证;必须保持仅绑定 localhost 并通过受控端口转发访问。
6. `dangerously skip permissions` 会绕过 Claude Code 的工具确认,只应在明确了解操作范围时临时启用;刷新后自动回到 normal。
