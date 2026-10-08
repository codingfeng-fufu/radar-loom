---
page_type: project_interview
summary: 面向中文财务报表的可审计数值问答与 Coding Agent 系统，具备审计回路、Repair 子循环和确定性评估框架。
source: <local-user-home>/作品集/coding/README.md
confidence: 高
tags: [Coding Agent, 财务报表, 审计, 数值问答, Agent评估]
---

# FinCoder：带审计回路的金融 Coding Agent

## 一句话介绍

FinCoder 是一个面向中文财务报表的可审计数值问答 Agent：模型负责规划和选取工具，程序负责隔离执行、确定性计算、来源追溯和结果审计，审计失败后自动进入 Repair 子循环。

## 30 秒回答

普通的 LLM + 工具系统可能会读错报表口径、算错单位，最后还无法证明数字来自哪里。FinCoder 把 Agent Loop、工具注册、隔离执行、append-only 审计链和确定性评估组合在一起。每次计算都会形成带 `ref_node` 的计算 DAG，结果经过单位检查、来源检查、交叉核验和独立重算；失败时把审计报告反馈给模型，最多 Repair 两次，仍不能通过就拒绝交付。当前 10 份真实 A 股年报的 30 个主报表槽位全部找到，27 PASS、3 WARN、0 FAIL；26 个端到端评估用例全部通过。

## 1. 项目背景

### 要解决的问题

- 财务报表同时存在 Excel、文本 PDF、扫描版 PDF 和跨页表格。
- 同一个指标有合并口径、母公司口径、单位换算和期间差异。
- LLM 可能选错行、混用不同单位或生成没有来源的数字。
- 只保存最终答案无法回答“这个数字来自哪一页哪一行、怎么算出来的”。
- 用另一个 LLM 当 Judge 无法可靠判断 Decimal 数值和来源是否正确。

### 核心原则

模型负责理解、规划和选择；程序负责解析、校验、计算、审计和拒答。任何不确定结果都不能直接交付。

## 2. 系统整体架构

## 2A. 谁使用、谁买单

直接用户是财务分析师、投研人员、审计人员和财务共享中心；买单方通常是券商、银行、审计咨询公司或大型企业财务部门。购买理由不是“能聊天”，而是减少报表取数、单位换算和复核的人力成本，并降低错误数字进入研究报告或审计底稿的风险。当前项目是可验证原型，商业化还需要接入权限、数据隐私、并发和企业文档流程。

```text
用户问题
   |
   v
Agent Loop：LLM Call -> Tool Call -> 隔离执行 -> 结果回注
   |                         |
   |                         +--> Tool Registry / Pydantic Schema
   |                         +--> SUBPROCESS / WORKER / INPROCESS_GUARD
   |                         +--> Append-only Chain Store（JSONL + fsync）
   |
   +--> Audit：单位、来源、勾稽、cross-check、独立重算
              |
              +--> 通过：交付答案
              '--> 失败：Repair 子循环 -> 预算耗尽后拒答

Evaluation：Task Case -> Session Archive -> 七维确定性 Scorer -> Gates 报告
```

## 3. 我的个人贡献

- 参与 Agent Loop、工具协议、执行器、计算链和审计器的整体设计与实现。
- 设计工具的 Protocol + JSON Schema + Pydantic 双重契约，以及统一 `ToolResult` 返回边界。
- 实现或参与 Excel/PDF 文档读取、表格查询、单位感知计算和来源节点追溯。
- 设计 Repair 子循环、任务级审计边界和 `ref_node` 计算 DAG。
- 搭建七维确定性评估框架，支持真实模型、Mock 状态机和历史 session 零成本重评分。
- 参与真实年报验收、对抗测试、注入防御和预算护栏。

## 4. 核心技术实现

### 4.1 Agent Loop 与工具边界

主循环固定为“LLM 规划 -> 工具调用 -> 隔离执行 -> 结果回注”。工具注册表同时暴露给模型 JSON Schema、给执行器 Pydantic 校验、给类型检查器 Python Protocol。所有执行器始终返回 `ToolResult`，异常不能穿透到对话循环。

工具按风险选择隔离策略：Bash 使用 subprocess 并杀进程组，计算使用 worker process 防止异常耗时，文件读取和编辑使用 in-process guard。工具结果有大小限制和截断标记，避免任意文件输出污染上下文。

### 4.2 Append-only 审计链与计算 DAG

每次 `calc` 产生一个唯一 `node_id`，操作数优先引用已有 `ref_node`，从而形成从最终 `calc_root` 回到文件、页码、sheet、行列的 DAG。审计链采用 JSONL 追加写，写入后 `flush + fsync`，拒绝覆盖和删除节点。

写入前强制检查：表达式重算结果、ref_node 存在性、循环引用、单位代数和调用来源。审计器只沿当前任务的 root trace，禁止扫描整个会话的所有数字，避免跨任务复用来源。

### 4.3 财务文档解析与多格式处理

Excel 通过表发现和 `TableDoc` 持久化支持点查；中文文本 PDF 使用 stream 优先、lattice 回退，并通过行列结构自检判断是否可用。跨页表格会检查列数和右对齐，必要时切换解析器；扫描版 PDF、低置信度表格和源文件变化都会进入明确的失败或 stale 状态。

在 5 份真实 A 股年报上做过解析 spike，stream 的 PASS+RECOVERABLE 率为 93%，lattice 为 40%，因此选择 stream 优先并在结构评分低于 0.6 时回退。

### 4.4 审计与 Repair 子循环

审计覆盖单位检查、资产负债表勾稽、同口径 cross-check、来源完整性和异构 provider 独立重算。审计失败不会直接把错误答案返回给用户，而是把结构化审计报告注入下一轮模型上下文，让模型重新选择事实或计算。

Repair 最多重试两次，预算耗尽后返回 `failed` 或 `refused`，严格区分“技术上做不到”和“系统判断不应回答”。勾稽检查的 WARN 不会无条件阻塞只查询某个具体报表行的任务，只有与当前问题相关的 FAIL 才进入阻塞链路。

### 4.5 确定性评估框架

评估保存的不只是最终文本，还包括 messages、tool calls、计算 DAG、来源、耗时、security events 和运行版本。七个评分维度分别检查 Answer、Provenance、Trajectory、Refusal、Injection、Repair 和 Efficiency。

财务正确性由 Decimal、Pint、结构化来源和轨迹不变式判断，不使用 LLM Judge。真实模型用于测效果，Mock 用于确定性故障回归，rescore 可以对历史 session 零成本重新评分。

## 5. 最难的问题

### 难题一：如何证明一个数字真的来自正确来源

只在答案中附文件名不够，系统需要证明每个操作数和计算根之间的关系。因此使用 `ref_node` DAG，来源节点明确保存 file/page/sheet/row/col/report type，审计器沿 root trace 反向遍历，而不是做全文数字匹配。

### 难题二：如何处理财务口径和单位冲突

主体、报表类型、期间、单位和指标标签必须同时匹配；Operand 的 `value` 和 `ref_node` 强制 XOR，单位代数在写入计算链前检查。混合口径或无法唯一消歧时系统拒答，而不是让模型自行猜测。

### 难题三：如何让修复不是无限循环

Repair 不是简单重试。每次审计报告明确指出 orphan number、单位不一致、来源不匹配或重算失败，下一轮只针对这些证据修复；同时受最大轮数、调用次数、token 和 wall-time 预算约束。

### 难题四：如何评估 Agent 而不被平均分掩盖严重错误

正常回答准确率、完整溯源、必须拒答召回、过度拒答、孤儿数字、跨任务复用、未处理注入和预算超限被设置为独立 gates。没有适用样本时标记 `NOT_EVALUATED`，不能当作 PASS。

## 6. 项目结果与量化验证

### 6.1 代码与测试

| 指标 | 结果 |
|---|---:|
| 单元测试 | 406 通过 |
| 评估框架测试 | 48 通过 |
| 对抗测试 | 42 通过 |
| 全量测试口径 | 约 497 通过 |
| ruff | clean |
| mypy --strict | 29 个文件通过 |

### 6.2 真实 PDF 批量验收

| 指标 | 结果 |
|---|---:|
| 真实 A 股年报 | 10 份 |
| 主报表槽位 | 30 个 |
| 成功发现 | 30/30，100% coverage |
| PASS / WARN / FAIL | 27 / 3 / 0 |
| PASS rate | 90% |
| 低置信度表格 | 4 个，已显式标记 |

### 6.3 端到端 Agent 评估

| 用例集 | 通过率 |
|---|---:|
| Excel 回归（含计算） | 8/8 |
| Excel 母公司口径 | 2/2 |
| Excel 拒答 | 4/4 |
| 合成 PDF 边界 | 4/4 |
| 真实 PDF 年报 | 7/7 |
| 总计 | 26/26，100% |

通过的 gates 包括 answer accuracy、provenance coverage、must-refuse recall、normal over-refusal、orphan numbers、cross-task reuse 和 budget exceeded。当前 README 的 41 用例口径与部分旧材料的 26 用例口径不同，面试时应说明具体引用的是哪一版评估档案。

### 6.4 Kimi 种子在线评估

两份真实年报的 Kimi seed：2/2 通过，answer/provenance/trajectory 均为 2/2；13 次 LLM 调用、75,527 tokens、151.087 秒，工具延迟 P50 1,252ms、P95 45,018ms，预算超限 0。

## 7. 现场演示顺序

1. 输入一份 Excel 或中文财报 PDF。
2. 提问一个带单位和期间的营业收入问题。
3. 展示工具查询、计算节点和来源链。
4. 注入一个单位或口径错误，展示审计失败和 Repair。
5. 展示最终审计报告，说明通过或拒答原因。
6. 打开评估报告，展示确定性 gates 而不是只看最终回答。

## 8. 可能追问

### 为什么不用 LLM Judge？

数值、单位和来源都有结构化真值，用 Decimal、单位换算和 DAG 追溯更可靠；LLM Judge 可以评估表达清晰度，但不能覆盖财务正确性。

### 为什么用 JSONL 而不是数据库存审计链？

当前场景主要是追加写和顺序读，JSONL 透明、离线可检查、容易做 hash 和恢复。未来多进程或分布式写入时再替换为专用 append-only 日志。

### 为什么 WARN 不全部拒答？

报表整体不完整不代表当前查询的目标行不可用。只有影响当前问题的 FAIL 才阻塞，避免系统因为无关的勾稽信息过度拒答。

### 这个项目的限制是什么？

Linux-only，扫描版 PDF 和复杂多级表头仍有边界；当前单进程 JSONL 审计链不适合多用户并发，外部 API 也带来隐私和延迟约束。

## 9. 1 分钟总结

FinCoder 的核心价值是把“模型会不会算”转化成“系统能不能证明、发现并修复错误”。我围绕工具协议、隔离执行、计算 DAG、审计器、Repair 和确定性评估构建了完整闭环。最终不仅能在 Excel 和真实财报 PDF 上回答数值问题，还能在来源、单位、口径或计算不满足约束时拒绝交付。

## 来源

- `<local-user-home>/作品集/coding/README.md`
- `<local-user-home>/作品集/coding/docs/project-status.md`
- `<local-user-home>/作品集/coding/evals/README.md`
- `<local-user-home>/作品集/coding/FinCoder_完整任务书.md`
