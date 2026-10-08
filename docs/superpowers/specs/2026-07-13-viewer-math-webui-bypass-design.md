# Viewer 数学渲染与 WebUI 危险权限模式设计

## 目标

1. 技术雷达 `viewer.html` 正确渲染行内和块级 TeX 公式。
2. 现有 `claude-code-webui` 增加第四档 `Dangerously skip permissions`，由用户逐会话选择，默认不启用且刷新后不保留。
3. 对危险模式提供明确的红色视觉警示，并验证请求实际进入 Claude Code 的 `bypassPermissions` 模式。

## Viewer 数学渲染

使用 KaTeX 的浏览器构建和 auto-render 插件，资源通过 CDN 加载，保持 Viewer 单文件。Markdown 先经 marked 解析并由 DOMPurify 清理，再在清理后的正文 DOM 上调用 `renderMathInElement`。支持 `$...$`、`$$...$$`、`\\(...\\)` 和 `\\[...\\]`；渲染参数为 `throwOnError: false`、`trust: false`、`strict: "warn"`，错误公式保留可读内容，不中断页面其余部分。

## WebUI 第四档模式

前端在现有 `default`、`acceptEdits`、`plan` 之外增加 `bypassPermissions`。选项文字使用 `Dangerously skip permissions`，选中时显示“Claude 可不经确认执行命令和修改文件”的红色警示。状态仍由当前 React 页面内存管理，不写 localStorage，因此刷新后回到 `default`。

后端收到 `permissionMode: "bypassPermissions"` 时，将 SDK `permissionMode` 设为 `bypassPermissions`，并通过 SDK `extraArgs` 添加 `--allow-dangerously-skip-permissions`。其他三种模式不增加该参数。由于安装包只有编译产物，本地维护 `<local-webui-root>/patch-dangerous-mode.mjs`，对特定版本 bundle 做有前置断言的幂等补丁；包重装后可重新执行，若上游结构变化则明确失败而不是静默误改。

## 安全边界

- 危险模式不作为默认值，不持久化，也不通过服务启动参数全局开启。
- UI 明示风险，只有用户主动选择后请求才携带 `bypassPermissions`。
- 服务继续仅监听 `127.0.0.1`。
- 补丁不修改凭据、知识库脚本或用户当前未提交内容。

## 验收

- 契约测试覆盖 KaTeX CDN、四种定界符、DOMPurify 后渲染、`trust: false` 和错误容忍。
- 补丁测试覆盖幂等性、第四档文案、红色警示、前端模式值及后端危险参数映射。
- 浏览器用临时内存页面验证四种公式生成 `.katex`/`.katex-display`，无水平溢出。
- 浏览器确认第四档可见、默认未选、选中后警示可见。
- 真实 API 请求确认危险模式的 init 消息为 `permissionMode: "bypassPermissions"`，普通模式仍为 `default`。

