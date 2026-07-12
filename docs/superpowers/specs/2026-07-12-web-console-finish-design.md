# Web 操作台收尾设计

## 范围

保留现有 `claude-code-webui` 作为聊天入口。在知识库根目录增加一个由 Python 标准库托管的只读浏览入口，并以单文件 `viewer.html` 渲染 Markdown。增加 `reports/` 作为面向用户的 HTML 成品目录，同时更新 `CLAUDE.md` 的维护协议。

用户已明确授权跳过火山 endpoint 的 429 前置阻断。2026-07-12 的真实 UI 请求仍返回 429，因此该项作为未通过的已知限制记录，不能写成验收成功；其他验收继续执行。

## 架构与组件

- `/home/u2023312337/webui/kbserve-control` 管理 `127.0.0.1:18081` 上的 Python 静态服务，提供 `start`、`stop`、`restart`、`status` 和 `logs`。
- `viewer.html` 是知识库内的自包含应用外壳。它从同源静态服务读取 `_index.md`、`首页.md`、`pages/*.md` 和 `graph.md`，浏览器端通过 CDN 加载 marked、DOMPurify、highlight.js 和 Mermaid。
- 侧边栏按 `_index.md` 的二级标题和清单生成。正文先解析 frontmatter 和双方括号链接，再经 Markdown 渲染与 DOMPurify 清理，最后执行代码高亮和 Mermaid。
- `reports/` 跟踪 `.gitkeep` 和首份自包含部署报告；报告本身不依赖 CDN。

## 安全与错误处理

文件参数只接受库内相对 `.md` 路径。拒绝绝对路径、反斜杠、查询或片段字符、空路径、点路径段、`..` 路径段，以及允许集合之外的根目录。允许入口为根目录中的 `首页.md`、`_index.md`、`graph.md`、分类图谱和 `pages/*.md`。所有 Markdown HTML 输出由 DOMPurify 清理；加载失败在正文区域显示状态码与文件名，不把响应正文直接插入页面。

## 验收

- 自动测试覆盖路径校验、双方括号转换、frontmatter 拆分和索引解析。
- 浏览器验证默认首页、侧边栏、概念页、双方括号跳转、frontmatter 折叠、代码高亮、Mermaid 和路径拒绝。
- `ss -tlnp` 验证 18080 与 18081 均仅监听 `127.0.0.1`。
- 运行知识库现有测试与健康检查。
- UI 真实检索和测试摄入因 429 无法完成，部署报告如实记录为未通过；不伪造结果。
