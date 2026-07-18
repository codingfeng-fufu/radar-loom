# 技术雷达知识库 Web 操作台使用与维护说明书

> 适用环境：`/home/u2023312337/知识库` 及 `/home/u2023312337/webui`  
> 更新日期：2026-07-18
> 读者：知识库日常使用者、Claude Code 使用者和后续维护者

## 项目定位与系统组成

本项目是技术雷达知识库的本地 Web 操作台。它把三类能力放在同一工作流中：

1. 浏览纯 Markdown 知识库、页面元数据和双方括号链接；
2. 查看 Cytoscape.js 交互式知识图谱；
3. 在知识库根目录中与 Claude Code 对话，让 Claude 检索、更新或创建知识页。

系统由两个仅监听本机的服务组成：

| 服务 | 端口 | 作用 | 控制脚本 |
|---|---:|---|---|
| 一体化操作台 | `18080` | 外层工作台与右侧 Claude Code WebUI | `/home/u2023312337/webui/webui-control` |
| 知识库服务 | `18081` | Viewer、Markdown、交互图谱及索引/图谱刷新 API | `/home/u2023312337/webui/kbserve-control` |

`18080` 的左侧通过 iframe 加载 `18081` 的 Viewer，右侧加载 Claude Code WebUI。两个 iframe 相互独立，外层工作台只传递当前文件路径、知识库刷新命令和待插入的提示词。

## 快速开始

首次使用或服务器重启后，执行：

```bash
/home/u2023312337/webui/kbserve-control start
/home/u2023312337/webui/webui-control start
```

然后打开：

- 一体化操作台：`http://127.0.0.1:18080/`
- 独立 Viewer：`http://127.0.0.1:18081/viewer.html`
- 交互式图谱：`http://127.0.0.1:18081/graph-view.html`

常用管理命令：

```bash
# 一体化操作台
/home/u2023312337/webui/webui-control start
/home/u2023312337/webui/webui-control stop
/home/u2023312337/webui/webui-control restart
/home/u2023312337/webui/webui-control status
/home/u2023312337/webui/webui-control logs 100

# 知识库服务
/home/u2023312337/webui/kbserve-control start
/home/u2023312337/webui/kbserve-control stop
/home/u2023312337/webui/kbserve-control restart
/home/u2023312337/webui/kbserve-control status
/home/u2023312337/webui/kbserve-control logs 100
```

`start` 对已运行服务是幂等的。修改 WebUI 配置或补丁后使用 `restart`；只修改 Markdown 页面时通常点击操作台顶部的“刷新知识库”即可。

远程使用时，在 VSCode“端口”面板转发 `18080` 和 `18081`，可见性保持为专用或本地。不要把服务直接暴露到公网。

## 一体化操作台

### 页面结构

- 顶部显示当前知识库文件，并提供“刷新知识库”“创建面试页”“创建知识页”“询问 Claude”和两侧折叠按钮。
- 左侧是知识库目录与 Markdown 预览。
- 中间分隔条可以拖动，调整知识库与 Claude 的宽度。
- 右侧是 Claude Code 对话区。

窄屏下使用“文件 / 预览 / Claude”三个标签切换。标签切换不会重载 Claude 会话。

### 刷新知识库

“刷新知识库”会先请求 `POST /api/refresh`，由本机知识库服务依次执行增量分类、索引和图谱生成；只有索引与图谱生成成功后才会重载当前 Viewer 或图谱页。右侧 Claude iframe 不刷新，当前会话、未发送输入和权限模式会保留。

对应的固定生成命令是：

```bash
cd /home/u2023312337/知识库
python3 scripts/taxonomy_cli.py sync
python3 scripts/build_index.py
python3 scripts/render_graph.py
```

按钮不向服务传递脚本名、路径或命令；服务只允许执行上述两个项目脚本。失败时页面不重载，顶部状态条会显示简短错误。

### 询问当前页面

1. 在左侧打开知识页。
2. 点击“询问 Claude”。
3. 输入问题并点击“放入 Claude 输入框”。
4. 检查右侧生成的提示词，再自行发送。

操作台会要求 Claude 先读取当前相对路径，再回答问题。它不会自动发送，也不会自动把整页正文塞入上下文。

### 创建知识页

点击“创建知识页”，填写：

- **知识主题**：必填，可以是中英文概念名或自然语言描述；
- **来源或已有材料**：可选，可以是 URL、本地文件路径、论文信息或简短材料；
- **特别关注点**：可选，例如核心公式、工程实现、评测或项目关系。

操作台会把结构化指令放入 Claude 输入框，显式调用 `$create-knowledge-page`。该 Skill 位于 `.claude/skills/create-knowledge-page/`，会执行：

1. 精确标题、别名和语义三层查重；
2. 核验用户材料，或研究原始论文、官方文档等可靠来源；
3. 判断应新建页面还是更新已有页面；
4. 自适应撰写概念边界、机制、适用条件、局限、项目关系和交叉引用；
5. 检查 LaTeX、元数据、来源与双链；
6. 构建索引、渲染图谱、运行健康检查并提交本次相关文件。

疑似重复、主题过宽、来源不足或材料冲突时，Skill 会暂停并提出一个具体问题；其他单页任务默认端到端完成。

### 工程面试区与创建面试页

Viewer 左侧的“知识库 / 工程面试”标签分别读取 `_index.md` 和 `_interview_index.md`。面试区可按岗位、难度和知识方向组合筛选；页面、过滤状态和区域会写入会话状态，后退、前进和刷新后仍保留。面试交互图谱读取 `interview-graph-data.json`；面试节点通过 `related_concepts` 跳转已有知识页，知识节点不计入面试分类成员。

“创建面试页”支持填写题目、关注点和多选上传材料。支持 `.pdf`、`.md`、`.txt`、`.png`、`.jpg`、`.jpeg` 和 `.webp`；单文件及整个请求均不得超过 20 MiB，文件名最多 240 个 UTF-8 字节，不得包含路径分隔符或控制字符。服务保存到 `raw/inbox/`，同名文件自动加数字后缀；提示词必须使用服务返回的相对路径。

提示词显式调用 `$create-engineering-interview-page` Skill，并要求材料含多道问题时，先列出问题清单、建议标题和推测难度，等待人工确认后再建页。操作台优先直接写入 Claude 输入框；只有直接写入成功才清空表单。若输入框未就绪，则复制到剪贴板并保留表单，用户检查后自行粘贴和发送。

## Viewer、数学公式与交互式图谱

Viewer 默认打开 `首页.md`。左侧目录由 `_index.md` 生成，按分类折叠。直接打开页面的地址格式为：

```text
http://127.0.0.1:18081/viewer.html?f=pages/页面名.md
```

Viewer 支持：

- frontmatter 折叠显示；
- 双方括号链接跳转；
- GFM Markdown；
- highlight.js 代码高亮；
- Mermaid 图形；
- KaTeX 数学公式；
- DOMPurify HTML 清洗。

数学表达必须使用 LaTeX。行内公式使用 `$...$`，块级公式使用独立成行的 `$$...$$`。写完数学页面后必须运行健康检查，并在 Viewer 中实际确认公式渲染。

交互式图谱使用 Cytoscape.js 和 fCoSE 布局，提供三种模式：**知识关系**显示页面与双方括号链接；**分类结构**显示类别的多上位、相关和重定向关系；**综合视图**同时显示页面、类别、知识链接和全部动态归属。分类详情包含边界、生命周期、成员数、上下位、相关类别和最近事件；页面详情显示所有归属、分数和语义/双链/标签/项目信号。

图谱页每 4 秒请求一次 `GET /api/revision`；服务发现 Markdown、`taxonomy.json` 或生成物变化时会自动重建，版本变化后图谱画布自动更新。版本未变化时不会重新布局。图谱工具栏的重组按钮调用本机 `POST /api/taxonomy/rebuild`，按钮在运行期间显示忙碌状态，成功后重新加载图谱数据。

需要手工验证生成结果时仍可运行：

```bash
cd /home/u2023312337/知识库
python3 scripts/render_graph.py
```

图谱数据写入 `graph-data.json`；`graph.md` 和分类 Mermaid 图保留为可审计备用视图，不手工编辑。
面试区对应的机器生成物是 `_interview_index.md`、`interview-graph.md`、`interview-graph-data.json` 和 `interview-taxonomy.json`，同样只通过构建、图谱和分类脚本更新。

## 可演化分类图谱

### 数据和模型

自动分类结果位于根目录 `taxonomy.json`，该文件提交到 Git，记录稳定类别 ID、名称、定义、父/相关关系、页面多归属、分项信号、别名、重定向和变更事件。页面原有八类标签不会被自动删除或批量重写，继续作为历史和人工信号。嵌入向量及清单位于 Git 忽略的 `.cache/taxonomy/`。

默认语义模型是 `intfloat/multilingual-e5-small`。首次使用执行：

```bash
cd /home/u2023312337/知识库
python3 -m pip install --user -r requirements-taxonomy.txt
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small'); print('模型缓存完成')"
```

模型下载完成后可离线复用本机 Hugging Face 缓存。更换 `config/taxonomy.json` 中的模型会改变参数指纹，并要求重建向量缓存。

### 自动运行和 CLI

页面保存后执行增量分类。累计新增或修改 5 个页面时触发全局重组；知识库服务也每 60 秒做一次低成本到期检查，距上次全局运行满每周 7 天时触发。图谱页可手动触发同一全局流程。

```bash
python3 scripts/taxonomy_cli.py migrate --dry-run
python3 scripts/taxonomy_cli.py migrate
python3 scripts/taxonomy_cli.py sync --page "pages/页面名.md"
python3 scripts/taxonomy_cli.py sync --no-global
python3 scripts/taxonomy_cli.py global
python3 scripts/taxonomy_cli.py global --no-llm
python3 scripts/taxonomy_cli.py status --json
python3 scripts/taxonomy_cli.py validate

# 面试页分类：--profile 必须放在子命令之前
python3 scripts/taxonomy_cli.py --profile interview sync
python3 scripts/taxonomy_cli.py --profile interview sync --page "pages/面试页名.md"
python3 scripts/taxonomy_cli.py --profile interview global --no-llm
python3 scripts/taxonomy_cli.py --profile interview status --json
python3 scripts/taxonomy_cli.py --profile interview validate
```

`migrate` 从八个历史分类建立种子；`sync` 处理新增、修改和删除；`global` 运行 HDBSCAN、Louvain、结构融合与生命周期更新；`status` 纯读状态；`validate` 检查引用、父关系环、重定向和分数。`global --no-llm` 完全使用本地关键词回退，不调用命名模型。

### 命名和故障边界

本地向量、近邻、聚类和图社区不使用付费 API。只有新增或实质变化的类别进入命名预算。知识库服务只接收非密钥变量 `TAXONOMY_NAMER_COMMAND=/home/u2023312337/webui/claude-taxonomy-namer`；权限为 `700` 的 `claude-taxonomy-namer` 才读取 `runtime.env`，服务进程不读取或记录 API Key、完整提示词。

嵌入、聚类、schema 或引用校验失败时保留上一版有效 `taxonomy.json`，不发布部分结果。单页增量分类失败会把页面放入待重试队列，不回滚已经保存的 Markdown 页面。Claude 命名遇到 HTTP 429、超时、非法 JSON 或调用预算耗尽时，类别仍成立并使用确定性关键词名称，`naming_status` 标记为 `pending`。

## Claude Code 对话区

右侧采用平面会话布局：Claude 回答以无气泡正文显示，用户消息右对齐，工具与系统消息使用紧凑状态条，底部 Composer 固定显示。浅色和深色主题都使用中性颜色，代码块支持横向滚动。

Claude 助手消息支持安全 Markdown 渲染：标题、段落、粗斜体、列表、引用、链接、行内代码和代码块。用户消息保持纯文本。原始 HTML 和表格不会进入渲染结果，链接在新标签页打开并附带安全属性。

### 权限模式

输入区下方的权限控件循环四档：

| 模式 | 含义 |
|---|---|
| `normal` | 常规确认流程 |
| `plan` | 先规划，不直接修改 |
| `accept edits` | 接受编辑操作，其他高风险工具仍按规则处理 |
| `dangerously skip permissions` | 绕过工具确认，允许 Claude 直接执行命令和修改文件 |

危险模式使用红色警示，不作为默认模式。只在明确理解任务范围、工作目录和 Git 状态时临时使用。刷新 Claude 页面后模式恢复为 `normal`。

## 知识库工作流

Claude Code 的项目协议在 `CLAUDE.md`。日常使用遵循两条主线。

### 检索作答

Claude 先读取 `_index.md`，再打开少量命中页面。回答时区分库内内容和模型补充知识，并注明页面及可用的来源定位。

### 增量摄入

- 老概念的新进展更新原页，不建立重复页。
- 新概念优先使用“创建知识页”入口或 `$create-knowledge-page`。
- 文本原始件进入 `raw/inbox/`，PDF 进入 `papers/`。
- 批量材料先列出待建和待更新清单，再修改页面。

手工建页仍可调用：

```bash
python3 scripts/new_page.py "概念中文名 EnglishName" \
  --tags KG \
  --summary "一句话摘要" \
  --source "真实来源或本地路径" \
  --confidence 中
```

每次摄入以索引、图谱、健康检查和 scoped Git 提交收尾。不要手工编辑 `_index.md` 或 `graph*.md`。

## 火山 Coding Plan 专用配置

WebUI 使用独立 Claude 配置，不读取用户主目录的 `~/.claude/settings.json`：

```text
CLAUDE_CONFIG_DIR=/home/u2023312337/webui/claude-config
```

专用设置文件：

```text
/home/u2023312337/webui/claude-config/settings.json
```

运行环境和密钥文件：

```text
/home/u2023312337/webui/runtime.env
```

当前 Coding Plan 参数为：

```text
ANTHROPIC_BASE_URL: https://ark.cn-beijing.volces.com/api/coding
ANTHROPIC_MODEL: ark-code-latest
```

密钥保存在 `runtime.env` 的 `ANTHROPIC_AUTH_TOKEN` 字段中，本说明书不记录密钥值。该文件权限必须保持 `600`：

```bash
chmod 600 /home/u2023312337/webui/runtime.env
```

更换密钥后重启 WebUI：

```bash
/home/u2023312337/webui/webui-control restart
```

启动器会在 tmux 子进程内部重新读取 `runtime.env`，避免常驻 tmux server 继承旧 Endpoint 或旧配置。

## 目录、进程、端口与数据流

关键目录：

```text
/home/u2023312337/知识库/        Markdown 页面、脚本、图谱与项目级 Skill
/home/u2023312337/webui/         WebUI 安装、补丁、配置、控制脚本与日志
/home/u2023312337/webui/app/     claude-code-webui npm 安装目录
/home/u2023312337/webui/claude-config/  WebUI 专用 Claude 配置和会话状态
```

进程由 tmux 托管：

```text
浏览器
  -> 127.0.0.1:18080 一体化工作台
       -> 右侧 Claude Code -> 火山 Coding Plan
       -> 左侧 Viewer iframe -> 127.0.0.1:18081
  -> 127.0.0.1:18081 独立 Viewer / 图谱 / Markdown 文件
       -> GET /api/revision 检查页面变化并按需重建
       -> POST /api/refresh 强制重建索引和图谱
```

检查监听地址：

```bash
ss -ltnp '( sport = :18080 or sport = :18081 )'
```

正常结果必须显示 `127.0.0.1:18080` 和 `127.0.0.1:18081`，不能显示 `0.0.0.0` 或公网地址。

## 日常维护与验证

### 页面维护

```bash
cd /home/u2023312337/知识库
python3 scripts/build_index.py
python3 scripts/taxonomy_cli.py sync
python3 scripts/render_graph.py
python3 scripts/check_health.py
```

健康检查必须达到：

```text
健康检查完成:ERROR 0 条,WARN 0 条。
```

### 知识库自动化测试

```bash
cd /home/u2023312337/知识库
python3 -m unittest discover -s tests -v
git diff --check
```

### WebUI 补丁测试

```bash
node /home/u2023312337/webui/test-integrated-workbench.mjs
node /home/u2023312337/webui/test-dangerous-mode.mjs
bash /home/u2023312337/webui/test-dedicated-claude-config.sh
```

### 重装后恢复补丁

升级或重装 `claude-code-webui` 后，重新应用并检查：

```bash
node /home/u2023312337/webui/patch-dangerous-mode.mjs
node /home/u2023312337/webui/patch-integrated-workbench.mjs
node /home/u2023312337/webui/patch-dangerous-mode.mjs --check
node /home/u2023312337/webui/patch-integrated-workbench.mjs --check
/home/u2023312337/webui/webui-control restart
```

补丁脚本会验证上游唯一代码片段。若上游版本不兼容，它会明确失败，避免静默生成错误界面。

## 常见故障与恢复

### 页面无法访问

依次检查：

```bash
/home/u2023312337/webui/webui-control status
/home/u2023312337/webui/kbserve-control status
/home/u2023312337/webui/webui-control logs 100
/home/u2023312337/webui/kbserve-control logs 100
```

服务未运行时执行对应 `start`。端口被占用时用 `ss -ltnp` 找到占用进程，不要直接改为公网端口。

### 左侧知识库空白或文件不更新

确认 `18081` 正常，再运行 `build_index.py`。浏览器仍显示旧资源时按 `Ctrl+Shift+R`，或点击操作台顶部刷新按钮。

### 数学公式显示原文

检查公式是否使用 `$...$` 或 `$$...$$`，再运行 `check_health.py`。如果 Markdown 和公式均不渲染，检查浏览器是否能访问 CDN，并查看控制台中的 KaTeX、marked 或 DOMPurify 加载错误。

### 图谱内容过期

先点击操作台顶部“刷新知识库”。如果状态条报错，查看 `/home/u2023312337/webui/kbserve-control logs 100`；也可分别运行 `python3 scripts/build_index.py` 和 `python3 scripts/render_graph.py` 查看完整脚本输出。不要手工修补 `graph-data.json` 或 `graph*.md`。
面试区缺页或图谱为空时，依次运行 `python3 scripts/taxonomy_cli.py --profile interview sync`、`python3 scripts/build_index.py` 和 `python3 scripts/render_graph.py`，再点击刷新或按 `Ctrl+Shift+R`。若仍无内容，检查页面是否精确标注 `page_type: interview`，并运行 `python3 scripts/check_health.py`。

### Claude 返回 HTTP 401

HTTP 401 表示密钥缺失、无效，或 Endpoint 与密钥类型不匹配。确认 `runtime.env` 中使用 Coding Plan 的 `/api/coding` 地址，密钥已填写且文件仍为 `600`，然后重启。排查时不要把密钥打印到终端、日志或聊天中。

### Claude 返回 HTTP 429

HTTP 429 表示上游额度或速率限制。知识库 Viewer 不受影响；等待额度恢复后再试。不要通过重复快速请求绕开限流。

### Claude 仍像在使用用户主目录配置

先重启 WebUI，再检查新进程的非敏感环境：

```bash
pid=$(pgrep -f '^node /home/u2023312337/webui/app/node_modules/.bin/claude-code-webui ' | head -1)
tr '\0' '\n' <"/proc/$pid/environ" | grep -E '^(CLAUDE_CONFIG_DIR|ANTHROPIC_BASE_URL|ANTHROPIC_MODEL)='
```

结果应指向 `/home/u2023312337/webui/claude-config`、`/api/coding` 和 `ark-code-latest`。不要扩大 grep 范围到认证字段。

### Skill 未被发现

确认 Claude 的工作目录是 `/home/u2023312337/知识库`，并确认 `.claude/skills/create-knowledge-page/SKILL.md` 存在。新会话比恢复很久以前的会话更适合验证新 Skill。

### 补丁检查失败

先运行对应测试，再应用补丁。若提示“expected one ...”，说明上游 bundle 已变化；不要绕过校验做模糊替换，应重新定位组件并更新测试夹具。

## 安全边界与已知限制

1. 两个服务没有身份认证和 HTTPS，只允许监听 `127.0.0.1`，远程访问必须经过受控端口转发。
2. `runtime.env` 含 API 密钥，不应加入知识库 Git、复制进文档或发送到对话。
3. `dangerously skip permissions` 会绕过工具确认，可能直接执行命令、修改或删除文件；只在明确任务范围时临时启用。
4. Viewer 是只读浏览工具，不在页面中直接编辑 Markdown。
5. Viewer 的 marked、DOMPurify、highlight.js、Mermaid 和 KaTeX 依赖浏览器访问 CDN；断网时渲染能力会下降。
6. 左右区域是独立 iframe。打开知识页不会自动把全文发送给 Claude，需要使用“询问 Claude”或明确要求读取页面。
7. tmux 保证 SSH 会话断开后服务继续运行，但服务器重启后需要手动执行两个 `start` 命令。
8. 火山 Coding Plan 的额度、限流和模型路由由上游控制，本项目只能报告实际错误，不能改变上游状态。
9. 上游 Claude WebUI 的历史项目枚举对中文路径可能不稳定；新会话和当前知识库默认路径不受该列表限制。
10. 项目级 Skill 会执行 Git 提交。使用前应检查工作树，避免把无关改动混入摄入提交。

## 关键文件索引

| 文件 | 用途 |
|---|---|
| `README.md` | 知识库入口与核心工作流 |
| `CLAUDE.md` | Claude Code 在本库中的行为协议 |
| `.claude/skills/create-knowledge-page/SKILL.md` | 高质量知识页创建与更新 Skill |
| `.claude/skills/create-engineering-interview-page/SKILL.md` | 工程面试页查重、创建、写作与验收 Skill |
| `templates/概念页模板.md` | 概念页基础结构 |
| `scripts/new_page.py` | 新建页面骨架 |
| `scripts/build_index.py` | 生成 `_index.md` |
| `scripts/render_graph.py` | 生成图谱数据和审计视图 |
| `scripts/taxonomy_cli.py` | 分类迁移、增量同步、全局重组、状态和校验 |
| `scripts/taxonomy_engine.py` | 分类流程编排和原子发布 |
| `config/taxonomy.json` | 模型、阈值、权重、预算和调度配置 |
| `taxonomy.json` | 提交到 Git 的动态分类注册表 |
| `scripts/serve_kb.py` | 提供静态页面、固定刷新 API 和图谱版本检查 |
| `scripts/check_health.py` | 检查元数据、链接、来源、索引和公式 |
| `viewer.html` | 单文件 Markdown Viewer |
| `graph-view.html` | 交互式知识图谱 |
| `/home/u2023312337/webui/webui-control` | 一体化操作台生命周期管理 |
| `/home/u2023312337/webui/kbserve-control` | 知识库静态服务生命周期管理 |
| `/home/u2023312337/webui/runtime.env` | 火山 Coding Plan 环境和密钥 |
| `/home/u2023312337/webui/claude-taxonomy-namer` | 隔离密钥的分类命名包装器 |
| `/home/u2023312337/webui/claude-config/settings.json` | WebUI 专用 Claude 设置 |
| `/home/u2023312337/webui/patch-integrated-workbench.mjs` | 一体化工作台、创建入口、Markdown 和对话主题补丁 |
| `/home/u2023312337/webui/patch-dangerous-mode.mjs` | 第四档权限模式补丁 |
| `/home/u2023312337/webui/test-integrated-workbench.mjs` | 工作台补丁契约测试 |
| `/home/u2023312337/webui/test-dangerous-mode.mjs` | 危险模式补丁测试 |

部署历史和原始验收证据见 `Web操作台部署完成报告.md`；本文档作为当前使用与维护入口，后续行为变化应同步更新这里。
