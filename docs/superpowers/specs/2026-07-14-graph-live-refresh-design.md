# 图谱动态刷新设计

## 背景与根因

操作台顶部的“刷新知识库”目前只向 Viewer iframe 发送 `kb-refresh` 消息，Viewer 收到后执行 `location.reload()`。该链路没有运行 `scripts/build_index.py` 和 `scripts/render_graph.py`，因此 `_index.md` 和 `graph-data.json` 仍是旧数据。当 iframe 停留在 `graph-view.html` 时，图谱页还没有 `kb-refresh` 消息处理器，手动刷新也不会完成。

## 方案比较

1. 仅在 Claude 的建页 Skill 末尾强制运行生成脚本。改动最小，但无法覆盖用户手工编辑，也不能修复已经失效的刷新按钮。
2. 在浏览器中直接重新计算图谱。不需要服务端端点，但会复制 Python 中的 frontmatter、双链和标签解析规则，容易产生两套不一致的图谱口径。
3. 将本机静态服务升级为受限的知识库服务，由它调用现有 Python 生成脚本，并向操作台和图谱页暴露固定的刷新/版本端点。该方案复用唯一的数据生成逻辑，同时覆盖手动刷新和文件变化后的自动更新。

采用方案 3。

## 架构

新增 `scripts/serve_kb.py`，继续使用 Python 标准库 `ThreadingHTTPServer` 提供静态文件，并添加两个固定 API：

- `POST /api/refresh`：在互斥锁内顺序执行 `build_index.py` 和 `render_graph.py`，成功后返回 JSON 版本号与脚本输出。
- `GET /api/revision`：比较 `pages/*.md` 及 `首页.md` 与生成产物的修改时间。如来源较新则自动重建，然后返回 `graph-data.json` 的稳定版本标识。

服务仅绑定 `127.0.0.1`。API 不接受命令、路径或脚本名参数，CORS 只允许 `http://127.0.0.1:18080`。生成过程设置超时，错误以非 2xx JSON 返回。

## 数据流

1. 用户点击顶部刷新按钮。
2. 操作台请求 `POST http://127.0.0.1:18081/api/refresh`。
3. 服务重建索引和图谱产物。
4. 操作台收到成功响应后，向当前知识库 iframe 发送 `kb-refresh`。
5. Viewer 和图谱页均重新载入，iframe `load` 事件解除按钮的忙状态。
6. 图谱页每 4 秒请求一次 `/api/revision`。版本变化时重新拉取 `graph-data.json` 并更换 Cytoscape 实例；版本未变化时不重排布局。

## 错误处理

- 手动刷新失败时，按钮恢复可用，状态条显示服务端返回的简短错误，当前页面不重载。
- 自动版本检查失败时保留现有图谱，只记录 console warning，下一轮继续尝试。
- 生成脚本只要有一个失败，API 整体失败，不宣告刷新完成。

## 测试与验收

- Python 单元测试覆盖新鲜度判断、强制刷新、自动刷新、互斥与 API CORS/错误响应。
- HTML 合同测试覆盖图谱轮询、版本变化后更新、`kb-refresh` 消息处理。
- WebUI 补丁测试覆盖“先 POST 重建，再 postMessage 重载”和失败状态。
- 浏览器端制造一个临时测试页，验证无需手工运行脚本即能出现新节点；测试后删除临时页并再次刷新。
