---
page_type: interview
summary: "Coding Agent 的核心是 ReAct 循环 + Agent-Computer Interface（ACI）+ 沙箱执行 + 测试反馈：LLM 不直接写最终 patch，而是通过精心设计的命令式工具（文件查看器、精确编辑、全局搜索、shell/测试执行）在仓库中观察-修改-验证，配合仓库地图/语义检索压缩上下文、用补丁式编辑降低误改、用沙箱和权限策略控制爆炸半径，最后用 SWE-bench 类基准和真实任务成功率做评估。"
source: ["https://arxiv.org/abs/2405.15793 (Yang et al., SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering, 2024)", "https://arxiv.org/abs/2407.16741 (Wang et al., OpenHands: An Open Platform for AI Software Development Agents, NeurIPS 2024)", "https://arxiv.org/abs/2402.01030 (Wang et al., CodeAct: Executable Code Actions Elicit Better LLM Agents, 2024)", "https://arxiv.org/abs/2310.06770 (Jimenez et al., SWE-bench: Can Language Models Resolve Real-World GitHub Issues?, ICLR 2024)", "https://arxiv.org/abs/2210.03629 (Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models, ICLR 2023)", "https://aider.chat/docs/repomap.html (Aider Repository Map 官方文档)", "https://www.anthropic.com/engineering/building-effective-agents (Anthropic, Building Effective Agents, 2024)"]
confidence: 高
first_recorded: 2026-08-02
tags: ["Agent", "Coding", "LLM", "系统设计", "工具调用"]
roles: ["Agent工程师", "大模型工程师", "后端工程师", "算法工程师"]
difficulty: "深入"
question: "请设计一个能在真实代码仓库中自主完成任务（修 bug、加功能、重构）的 Coding Agent，需要说明整体架构、上下文管理、工具接口、执行反馈循环、安全边界和评估方法。"
related_concepts: ["ReAct Agent 工作原理", "AI Agent上下文窗口不足的工程应对", "Agent 记忆架构", "设计一个AI Agent的记忆系统"]
---

# 设计一个Coding Agent

## 面试问题

请设计一个能在真实代码仓库中自主完成任务（修 bug、加功能、重构）的 Coding Agent，需要说明整体架构、上下文管理、工具接口、执行反馈循环、安全边界和评估方法。

## 考察意图

1. **系统分解：** 能否把 Coding Agent 拆成编排器、上下文管理器、ACI 工具层、沙箱执行器、评估回路等独立模块，而不是"调一次 LLM 生成补丁"。
2. **工具设计：** 是否理解 Agent-Computer Interface（ACI）的设计原则——给 LLM 的命令必须窄接口、强反馈、可恢复，而不是直接开放整个 shell。
3. **反馈闭环：** 能否把"运行测试、读报错、再修改"构成 ReAct 循环，并知道何时停止、何时求助。
4. **上下文工程：** 如何让模型在 128K 窗口内仍能导航大型仓库——仓库地图、语义检索、按需展开、补丁式编辑。
5. **安全与边界：** 沙箱隔离、网络/文件系统权限、危险操作审批、prompt 注入防护、多租户隔离。
6. **评估意识：** 知道 SWE-bench 等基准的评测协议、pass@k、测试覆盖率、真实任务成功率的差异。

## 30 秒回答

1. **结论：** Coding Agent 不是"LLM 一次生成补丁"，而是一个运行在**沙箱**里的 **ReAct 自主循环**，通过精心设计的 **Agent-Computer Interface（ACI）**——文件查看、精确编辑、全局搜索、shell/测试执行——在真实仓库中**观察→定位→修改→验证**，直到测试通过或触发停止条件。
2. **主链路：** 任务进入后，编排器构建包含 issue 描述、仓库地图（repo map）和相关文件片段的上下文；LLM 用 thought-action 发出一条 ACI 命令；执行器在沙箱里跑、把 stdout/stderr/退出码/差异反馈回来；循环中持续做上下文压缩（旧观察外置、新结果进入）、补丁式编辑（避免整文件重写）和测试门控；最终产出一个可应用的 patch/PR。
3. **关键取舍：** LLM 在循环里是规划者不是执行者；接口越窄、反馈越结构化、编辑越精确，模型越不容易走偏；代价是每轮都要付 LLM 调用和测试运行的延迟成本。必须设硬预算（步数、token、时长）和人工审批点（删除、推送、改 CI），并在 SWE-bench 类基准加线上任务成功率上双轨评估。

```mermaid
flowchart LR
    T[Issue/任务] --> P[编排器 Planner]
    P --> CTX[上下文管理器<br/>仓库地图 + 语义检索]
    CTX --> L[LLM thought/action]
    L --> ACI{ACI 工具}
    ACI -->|find/grep| S[搜索]
    ACI -->|open/scroll| V[文件查看器]
    ACI -->|edit| E[精确编辑]
    ACI -->|bash/test| X[沙箱执行]
    S --> FB[结构化反馈]
    V --> FB
    E --> FB
    X --> FB
    FB --> CTX
    CTX --> L
    L -->|stop| OUT[Patch / PR]
    X -.危险操作.-> H[人工审批]
```

*图：核心是 LLM ↔ ACI ↔ 沙箱的反馈闭环。上下文管理器在每轮决定窗口里放什么；危险操作绕过自治循环走人工审批。*

## 2 分钟回答

**先把系统拆成五层。** 最上层是**编排器**，负责解析任务、选择策略（直接修 vs 先复现 vs 先问澄清）、维护步数/预算/停止条件；下一层是**上下文管理器**，维护仓库地图（基于 tree-sitter/LSP 的符号地图）、相关文件片段、历史命令输出，按相关性和预算注入；中间是 **LLM 推理核心**，跑 ReAct/CodeAct 风格的 thought-action 循环；再下一层是 **Agent-Computer Interface（ACI）**，把 LLM 的意图翻译成一组窄而明确的命令；最底层是**沙箱执行器**，跑 shell、测试、构建，做资源和权限隔离。

**ACI 是系统好坏的关键，不是 LLM 本身。** SWE-agent 的核心洞见是：给 LLM 一个设计良好的 ACI，比换一个更强的模型带来的提升更大。典型 ACI 工具包括：带语法高亮和窗口的文件查看器（`open <file> <line>`、`scroll`）、基于行号或 search/replace 的精确编辑（不是写整个文件）、`find`/`grep`/`ripgrep` 全局搜索、`bash` 命令（带超时和输出截断）、`test`/`run` 命令（结构化解析测试通过/失败位置）。每个工具必须返回**结构化反馈**：退出码、截断后的 stdout、报错文件与行号、当前 diff 状态。CodeAct 的经验是让 LLM 输出可执行的 Python/bash 代码作为 action，比 JSON 函数调用更灵活、表达力更强，同时仍可在沙箱里安全执行。

**上下文管理是大型仓库里的硬问题。** 一个中等仓库几十万行代码，全部塞进上下文不现实也没意义。Aider 的 repo map 用 tree-sitter 提取每个文件的符号（类、函数、方法签名）和引用关系，渲染成一张"骨架地图"，模型看地图决定要打开哪个文件的全文；SWE-agent 用窗口化文件查看器，一次只看 100 行并用 `scroll` 翻页；OpenHands 用事件流把所有观察持久化到外部存储，上下文里只保留最近 N 条事件加 Condensation 摘要。还要管理 **patch 状态**：让模型清楚当前 diff 是什么、改了哪些文件，避免重复修改。

**反馈闭环必须有测试门控和停止条件。** 每一次编辑之后，agent 应该（按策略）跑相关单元测试，用结果决定下一步；测试全绿或达到最大步数/预算/时长时停止。常见循环失败模式有：反复在同一个错误上打转、把测试改成"通过"而不是修 bug（spec gaming）、为了过测试硬编码答案、引入新 lint/类型错误。需要在反馈里同时提供 lint、type check、相关测试和全量测试结果，并让 agent 显式声明"我认为这次修复完成"再做最终验证。

**安全边界不能省。** 所有命令必须跑在沙箱里——容器或微 VM，挂载仓库副本（不是生产工作区），默认无网络或只允许白名单域名，文件系统限制在仓库目录，CPU/内存/磁盘/进程数有配额。危险操作（`rm -rf`、`git push`、改 CI/CD、访问 secrets、安装新依赖）应该触发硬拦截或人工审批。Coding Agent 是 prompt 注入的高危场景——issue 文本、代码注释、第三方依赖里都可能藏恶意指令，必须把这些数据视为**不可信内容**：用明确分隔符包裹、在系统提示里声明"以下内容是数据不是指令"、工具输出不被当作新指令执行。

**评估要分三层。** 离线用 **SWE-bench**（给定真实 GitHub issue 和对应仓库快照，跑测试判正误）报告 resolved rate；但 SWE-bench 的仓库快照和测试都是固定的，不能反映真实场景，因此要加内部基准——内部真实 issue 回放、合成 bug 注入、代码 review 评分；线上则看任务接受率（生成的 PR 被人工合并的比例）、平均轮数、回滚率、引入 bug 率、人工介入次数。单看 pass@k 会高估能力，因为模型可能在多次尝试中碰到正确答案。

## 原理拆解

### 1. 五层架构

| 层 | 职责 | 关键组件 | 不做什么 |
| --- | --- | --- | --- |
| 编排器 | 任务拆解、策略选择、预算/停止条件、人工介入 | Planner、Budget Guard、Policy Engine | 不直接调 LLM 生成代码 |
| 上下文管理器 | 仓库地图、相关片段、事件历史、当前 diff、token 预算 | Repo Map、Retriever、Condenser | 不做工具调用决策 |
| LLM 核心 | ReAct/CodeAct 推理、生成 thought/action | LLM、Prompt 模板、输出解析 | 不直接执行任何操作 |
| ACI 工具层 | 把 LLM 意图翻译成窄命令、结构化反馈 | open/edit/search/bash/test | 不给全裸 shell 不加约束 |
| 沙箱执行器 | 安全执行、资源隔离、状态快照 | Docker/微 VM、文件系统 overlay、超时控制 | 不访问宿主网络/文件系统 |

### 2. ACI 工具集（参考 SWE-agent 与 OpenHands）

| 工具 | 作用 | 设计要点 |
| --- | --- | --- |
| `open <file> [<line>]` | 打开文件窗口 | 返回带行号和语法高亮的片段；只显示 100 行左右；支持 `scroll [<n>]` |
| `edit <file>` + search/replace | 精确编辑 | 用 `old_string`/`new_string` 而非整文件重写；`old_string` 必须唯一匹配，否则报错 |
| `create <file>` | 新建文件 | 允许整文件内容，但写入前做 lint/类型检查 |
| `find <name/pattern>` | 按文件名搜索 | 结果带路径和类型，默认排除 `.git`/`node_modules` |
| `search <regex>` | 全文搜索 | 等价 `rg`；返回带文件、行号、匹配片段 |
| `bash <command>` | 执行 shell | 必须有超时（默认 30–120s）、输出截断（如 2000 行）、禁用危险内置 |
| `test [<target>]` | 跑测试 | 解析输出为结构化结果：通过/失败数、失败用例名、报错位置 |
| `submit` | 提交 patch | 触发最终验证、生成 diff/PR 描述；停止循环 |

设计原则：**命令窄、反馈结构化、错误可恢复**。例如 edit 失败时返回"未找到唯一匹配，以下是 N 个候选位置"而不是让 LLM 猜；bash 输出超长时返回头尾加"省略 M 行"并给出 `tail`/`grep` 建议。

### 3. ReAct/CodeAct 循环

每一步 LLM 的输入包含：

1. 系统指令（角色、ACI 规范、安全约束、输出格式）；
2. 任务描述（issue 正文、复现步骤、期望行为）；
3. 仓库地图（精简符号图，通常 1K–4K token）；
4. 当前打开的文件窗口；
5. 最近若干步的 action-observation（更早的被压缩成摘要）；
6. 当前 diff 摘要；
7. 可用工具列表及 schema。

输出是一段 thought（推理）加一个 action（一条 ACI 命令或一段可执行代码）。执行器把 action 跑出来，observation 回到输入队列，进入下一轮。

停止条件（满足任一即停）：

- LLM 调用 `submit`；
- 目标测试全绿且代码检查通过；
- 达到最大步数（如 30–50 步）；
- 达到 token 或时长预算；
- 连续 K 步没有新进展（检测重复 action）；
- 触发危险操作审批且被拒绝。

### 4. 仓库地图（repo map）的构建

Aider 式仓库地图大致流程：

1. 用 tree-sitter 解析所有源文件，提取符号定义（类、函数、方法）和引用；
2. 构建符号定义→被引用位置图；
3. 对每个符号计算 PageRank 或类似的"重要性"分；
4. 按预算（如 1K–4K token）取最相关的符号，渲染成带文件路径和签名的骨架；
5. 对当前任务，额外加入与 issue 文本、已修改文件语义相近的符号。

地图的价值是让模型**在不读全文的情况下知道仓库里有什么、在哪里、该打开什么**，把全仓库导航问题变成几次 `open`/`search`。

### 5. 补丁式编辑 vs 整文件重写

- **整文件重写**：模型输出整个文件新内容。缺点是容易在不相关区域引入改动、重复代码、转义错误、丢失注释；长文件会快速耗尽 token。
- **search/replace 编辑**：模型给出 `old_string` 和 `new_string`。优点是 diff 最小、意图明确、可 review、token 消耗低；缺点是 `old_string` 不唯一时需要候选机制。
- **AST 级编辑**：用 tree-sitter 定位符号并替换整段函数/类，最精确但工具链复杂。

工程上推荐 search/replace 为默认，新建文件用 create，重构性大块改动才用 AST 级编辑。每次编辑后立即跑 lint/type check 阻断错误累积。

### 6. 上下文压缩策略

随着循环变长，早期观察会塞满上下文：

- **窗口化**：文件查看器只看 100 行，不把整个文件放进来；
- **输出截断**：bash/test 输出截断头尾，超长则建议模型用 `grep`/`tail` 缩小；
- **事件摘要**：超过 N 步的旧 action-observation 用小模型压成一段摘要（"第 3–7 步尝试了 X/Y/Z，最终定位到文件 F 函数 G"）；
- **外置存储**：完整事件流存磁盘或数据库，需要时通过 `history <id>` 类工具回查；
- **差异视图**：始终注入当前 `git diff --stat` 而非每次完整 diff；
- **相关性过滤**：搜索结果按与任务的语义/关键词相关度排序，丢弃分数低的。

### 7. 安全模型

| 威胁 | 缓解 |
| --- | --- |
| 恶意 shell 命令 | 命令白名单/黑名单、容器内非 root 执行、seccomp 过滤 |
| 网络外泄代码/密钥 | 默认禁网，只允许白名单域名（如包管理镜像） |
| 文件系统越权 | 容器只挂载仓库副本，只读挂载系统目录 |
| 资源耗尽 | CPU/内存/磁盘/进程数/超时限制 |
| Prompt 注入（issue/注释/依赖） | 把所有外部数据标记为不可信、分隔符隔离、工具输出不被当作指令执行 |
| 危险操作（rm、push、改 CI、装依赖） | 策略引擎拦截，触发人工审批 |
| 多租户数据泄露 | 每次任务独立沙箱、按租户分网络/存储、结束后销毁 |
| 供应链攻击 | 锁版本、不允许任务中安装未审计依赖、私钥不下发 |

### 8. 评估体系

- **SWE-bench / SWE-bench Verified**：给定 issue 和仓库快照，用隐藏测试判正误；报告 resolved rate。Verified 子集由人工筛选，标注更可靠。
- **内部回放基准**：从内部 issue 跟踪系统采样已修复问题，按时间切分训练/测试集，避免数据泄漏。
- **合成 bug 注入**：在干净代码上用变异算子注入 bug，知道精确"正确补丁"，可测精准率。
- **代码 review 评分**：让资深工程师对生成 PR 做多维打分（正确性、可读性、最小性、是否引入回归）。
- **线上指标**：PR 接受率、平均轮数、回滚率、新引入 bug 率、人工介入次数、端到端时长。
- **安全与越权测试**：构造含 prompt 注入的恶意 issue，验证沙箱和策略是否守住。

## 递进追问与参考回答

### Q1：为什么要专门设计 ACI？直接让 LLM 写完整 patch 不行吗？

直接生成完整 patch 在小仓库、短任务上确实能跑通，但在真实仓库里有三个问题：**无法导航**——模型不知道仓库结构，容易改错文件；**无法验证**——没有反馈循环，第一次猜错就没有机会修正；**无法应对规模**——整文件重写长文件会爆上下文并引入不相关改动。SWE-agent 论文的核心结论是 ACI 设计比模型选择对最终解决率影响更大：窄命令强迫模型一步步观察和验证，结构化反馈让每一步都有明确信号，精确编辑把爆炸半径控制在最小。可以把它类比成人类工程师不是盯着 issue 写最终 diff，而是先 grep、看文件、跑复现、再改、再测。

### Q2：ReAct 和 CodeAct 怎么选？

ReAct 输出 thought + 结构化函数调用（JSON），优点是 schema 明确、易校验、易审计；缺点是表达力受限，复杂条件逻辑要用很多次函数调用拼。CodeAct 让 LLM 直接输出可执行的 Python/bash 代码作为 action，在一个代码块里完成多步操作、变量绑定和错误处理，表达力更强、轮数更少；代价是需要更强的沙箱和更严格的代码审查。工程上可以混合：默认 CodeAct 处理文件遍历、批量替换、结果分析这类高表达力需求；对 submit、改 CI、推送等危险操作降级为结构化函数调用并走审批。

### Q3：怎么防止 agent 在循环里反复试同一个错误？

至少三层。**检测层**：记录最近 N 步 action 的规范化签名（命令+参数+退出码），发现重复或近似重复时给模型一个显式信号"你在第 K 步试过这个，结果是 X，请换思路"。**预算层**：最大步数、token、时长硬上限；连续失败阈值（如 3 步无新进展）触发停止或升级到更强模型。**策略层**：让模型定期做"自我反思"——每若干步要求它总结已知信息、剩余未知、下一步计划；如果它反复卡在同一处，编排器可以切换策略（如从"直接修"切到"先写复现测试"）或回退到人类。

### Q4：长仓库/多模块仓库怎么让模型不迷路？

三层导航。**顶层是 repo map**：tree-sitter 提取符号图，按重要性和当前任务相关度渲染成骨架，告诉模型"仓库里有什么"。**中层是语义检索**：把 issue、栈轨迹、注释做 embedding，检索相关代码片段和历史 commit。**底层是窗口化查看**：只在需要时 `open` 具体文件的若干行，用 `scroll` 翻页。同时用 **工作记忆** 维持当前已打开文件、已运行测试、当前 diff 的状态，让模型不用每轮重新发现。关键是不要一次性把所有检索结果塞进 prompt，而是让模型像人一样通过工具按需展开。

### Q5：怎么保证 agent 改的是问题本身，而不是"为了过测试而改测试"？

这是 SWE-bench 时代的经典问题（spec gaming）。技术上：**测试与代码分离**——agent 可以跑测试但不能修改测试文件，ACI 层把 `test/`、`*_test.py`、`*.spec.*` 等路径设为只读。**隐藏测试集**：最终用 agent 没见过的测试判正误，SWE-bench 就用了这个机制。**变更审查**：submit 时强制跑 lint、type check、覆盖率变化检测，禁止删除已有测试或断言。**语义一致性**：用独立 LLM 或人工审查"代码改动是否回应了 issue 描述"。**多测验证**：除了 issue 相关测试，还要跑全量回归测试，防止修一个坏一片。

### Q6：沙箱要做到什么程度才够？容器够吗？

取决于威胁模型。**默认假设仓库和 issue 都是对抗性的**——代码里可能有恶意 install 脚本、issue 里可能有 prompt 注入、依赖里可能有挖矿程序。容器（Docker）提供基本隔离，但共享宿主内核，容器逃逸风险不为零；对不可信代码建议上微 VM（Firecracker、gVisor、Kata Containers）或独立虚机。资源上要限 CPU、内存、磁盘、进程数、文件描述符，并加 pid/网络 namespace；网络默认禁用，只对必要包管理镜像放行；文件系统用 overlay，任务结束整体销毁。还要考虑冷启动延迟——镜像预热、快照恢复、仓库镜像缓存能显著降低每任务开销。

### Q7：多 agent 协作写代码有价值吗？

有价值但不是银弹。**适合并行化的环节**：一个 agent 复现 bug、一个定位根因、一个写修复、一个写测试，能降低端到端时长；**适合分工的环节**：前端、后端、数据库、DevOps 各有专长 agent，通过接口契约协作。**不适合的场景**：小 bug、强耦合改动、需要全局一致性判断的重构——多 agent 会引入协调开销和接口不一致风险。工程上通常是一个**主管 agent（orchestrator）**做规划和分解，多个**子 agent**在独立沙箱里完成明确子任务，产物通过 PR 或 patch 的形式回合，由主管 agent 整合并跑全量测试。要避免的反模式是让多个 agent 共享同一个工作目录和上下文。

### Q8：怎么评估一个 Coding Agent 真的"能用"，而不只是在 SWE-bench 上刷分？

SWE-bench 解决率是必要不充分指标。要补四类评估：**时间切分的内部基准**——用过去 N 个月真实 issue 回放，避免训练污染；**人对 PR 的多维评分**——正确性、最小性、可读性、测试质量、是否符合代码规范；**线上闭环**——PR 合并率、review 轮数、回滚率、上线后 bug 率；**对抗性评估**——恶意 issue、含 prompt 注入的代码、需要跨服务理解的任务、需求模糊的任务。一个 agent 如果 SWE-bench 分数高但线上 PR 接受率低，往往是"在固定仓库快照上过拟合"，真实价值有限。

## 常见错误回答

- **"让 LLM 读 issue 然后直接输出 patch"**：没有反馈循环、没有验证、无法导航仓库，在真实工程里几乎不可用。
- **"把整个仓库塞进上下文就行"**：长仓库爆窗口、成本高、注意力稀释；即便塞进去，模型也不会自动找到相关位置。
- **"给 LLM 一个完整的 bash 权限"**：裸 shell 是最差的 ACI 设计——输出无结构、危险命令无防护、错误不可恢复，agent 极易走偏。
- **"ACI 就是 OpenAI function calling"**：function calling 是 LLM 侧的调用机制，ACI 是接口设计学——命令粒度、反馈格式、错误恢复都需要专门设计。
- **"用更强的模型就能解决问题"**：SWE-agent 论文显示同一模型用不同 ACI，解决率差异远大于换模型。
- **"跑通测试就完成了"**：agent 可能改测试、硬编码答案、引入回归；必须用隐藏测试、全量回归和代码审查。
- **"不需要沙箱，反正跑在 CI 里"**：CI 通常有生产密钥、内网访问和持久缓存，绝不是不可信代码的合适执行环境。
- **"多 agent 一定比单 agent 强"**：协调开销和接口不一致常常抵消并行收益，小任务单 agent 更稳。
- **"只看 pass@1 就够"**：pass@k 反映尝试多次后的成功概率，但真实场景只有一次尝试机会；要看 pass@1 和端到端成本。

## 评分标准

**不合格（0–2）**

- 只回答"让 LLM 生成 patch"，没有反馈循环和工具设计；
- 说不出沙箱、权限、prompt 注入等任何安全考虑；
- 不知道 SWE-bench 是什么，或只凭直觉评估。

**合格（3–4）**

- 能画出编排器+LLM+工具+沙箱的基本架构；
- 知道 ReAct 循环、文件查看/编辑/搜索/执行等 ACI 工具；
- 提到测试反馈、步数预算、危险操作审批；
- 知道用 SWE-bench 或类似基准评估。

**优秀（5–6）**

- 能系统讲清 ACI 设计原则（窄接口、结构化反馈、可恢复错误）和补丁式编辑；
- 理解 repo map/tree-sitter、上下文压缩、事件外置等长仓库导航策略；
- 能讨论 ReAct vs CodeAct、单 agent vs 多 agent 的取舍；
- 能设计完整的安全模型：沙箱、网络、prompt 注入、危险操作审批、多租户隔离；
- 知道 SWE-bench 的局限，能给出内部基准+线上指标+对抗评估的组合方案。

**加分项**

- 提到 SWE-agent、OpenHands、Aider、Devin、Claude Code 等真实系统的具体设计差异；
- 了解 AST 级编辑、LSP 集成、tree-sitter 符号图等实现细节；
- 能讨论评测中的 spec gaming、数据污染、pass@k 偏差；
- 有在真实代码库里部署或调优 coding agent 的经验；
- 理解 ACI 设计对解决率的影响常常大于模型升级。

## 关联概念

- [[ReAct Agent 工作原理]]
- [[AI Agent上下文窗口不足的工程应对]]
- [[Agent 记忆架构]]
- [[设计一个AI Agent的记忆系统]]
- [[多智能体系统 Multi-Agent Systems]]
- [[提示注入 Prompt Injection]]
- [[检索增强生成 RAG-GraphRAG]]
- [[思维链 Chain-of-Thought]]

## 来源核验

来源：

- Yang et al., *SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering*, 2024, https://arxiv.org/abs/2405.15793 （ACI 设计原则、文件查看器/搜索/编辑/命令行工具集、SWE-bench 上解决率显著提升的一手来源）
- Wang et al., *OpenHands: An Open Platform for AI Software Development Agents*, NeurIPS 2024, https://arxiv.org/abs/2407.16741 （事件流架构、沙箱 runtime、CodeActAgent、可扩展 agent 平台一手来源）
- Wang et al., *CodeAct: Executable Code Actions Elicit Better LLM Agents*, 2024, https://arxiv.org/abs/2402.01030 （以可执行代码而非 JSON 函数调用作为 action 的经验对比与一手来源）
- Jimenez et al., *SWE-bench: Can Language Models Resolve Real-World GitHub Issues?*, ICLR 2024, https://arxiv.org/abs/2310.06770 （真实 GitHub issue 评测协议、隐藏测试判正误的基准来源）
- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models*, ICLR 2023, https://arxiv.org/abs/2210.03629 （thought-action-observation 循环范式的一手来源）
- Aider Documentation, *Repository Map*, https://aider.chat/docs/repomap.html （基于 tree-sitter 的仓库地图构建和排名工程实践）
- Anthropic, *Building Effective Agents*, 2024, https://www.anthropic.com/engineering/building-effective-agents （agent 系统中工具、编排、状态和最小可行复杂度的工程实践）

信度：高。SWE-agent、OpenHands（NeurIPS 2024）、CodeAct、SWE-bench（ICLR 2024）、ReAct（ICLR 2023）均为同行评审或被广泛引用的一手论文；Aider 是其作者维护的官方文档；Anthropic 工程文章给出工业界视角。各来源在 ACI 设计、反馈循环、沙箱执行、SWE-bench 评测协议等关键事实上口径一致。

说明：用户特别提到"Pi agent"，但经多轮检索未在可核验的一手来源中找到以此命名的 coding agent 系统，因此本页未将其作为具体参考；若用户后续提供 Pi agent 的论文或仓库链接，可在更新记录中补入。

## 更新记录

- 2026-08-02: 首次建页
