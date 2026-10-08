---
page_type: project_interview
summary: 面向开放语料的知识图谱融合与图约束问答系统，支持可追溯抽取、图文证据检索和 citation 回答。
source: <local-user-home>/作品集/OpenFusionKGQA/README.md
confidence: 高
tags: [知识图谱, GraphRAG, 图谱融合, 问答, 可追溯]
---

# OpenFusionKGQA

## 一句话介绍

OpenFusionKGQA 是一个将开放文本抽取为可追溯知识图谱，并结合图结构、原文片段和社区报告完成带引用问答的 GraphRAG beta 原型。

## 30 秒回答

普通向量 RAG 能找相似文本，但难以表达实体之间的关系，也无法稳定融合不同文档中对同一实体和关系的描述。OpenFusionKGQA 先把 txt、Markdown 和 PDF 变成带 provenance 的 text units，再做实体、关系和三元组抽取；融合阶段完成实体归一、关系对齐、证据检查、评分和 rejected-triple 记录。在线问答根据问题选择 local 或 global 路由，从 text units、entities 和 community reports 三层证据中召回，最后生成带 citation 的回答。默认离线 release gate 为 459 tests 通过，Offline QA 7/7 通过；HotpotQA real100 为 78/100，通过率 78%。

## 1. 项目背景

### 要解决的问题

- 开放文本中的实体别名、关系表达和重复事实不一致。
- 只用向量检索难以完成多实体、多跳和全局主题问题。
- 抽取错误如果直接进入图谱，会污染后续问答。
- 答案必须能回到原文 chunk 或图谱证据，而不是只输出自由生成文本。

### 项目定位

这是 runnable beta prototype，不是完整复现 Microsoft GraphRAG，也不是生产 SaaS。重点是验证“开放文本 -> 图谱融合 -> 图文证据问答 -> 评估与发布检查”的工程闭环。

## 2. 系统整体架构

## 2A. 谁使用、谁买单

直接用户是知识工程师、研究团队和企业内部知识库建设人员；潜在买单方是需要处理大量开放文档的企业、咨询机构和知识管理平台。价值在于减少人工实体整理和跨文档检索成本，并让问答结果带有图谱和原文证据。当前是 beta 原型，商业化前仍需提升真实 LLM 抽取鲁棒性、权限治理和生产部署能力。

```text
Documents (.txt/.md/.pdf)
        |
        v
Document Scan -> Text Units + provenance
        |
        v
Entity / Relationship / Triple Extraction
        |
        v
Graph Fusion：归一、对齐、证据检查、评分、拒绝记录
        |
        +--> JSON artifacts / optional Neo4j
        +--> vectors: text units / entities / community reports
        |
        v
GraphRAG QA：local/global route -> evidence retrieval -> cited answer
```

## 3. 我的个人贡献

- 负责 GraphRAG v2 原型的索引、融合、问答和 CLI 组织。
- 设计候选实体、关系、三元组到最终实体/关系/拒绝三元组的 artifact 契约。
- 实现 JSON 离线图存储和 Neo4j production-path 的双后端接口。
- 设计 local/global QA、三层向量召回、社区报告和 citation 元数据。
- 搭建 offline QA、HotpotQA、抽取评估、失败分类和 release verification 脚本。

## 4. 核心技术实现

### 4.1 从开放文本到稳定 artifact

文档首先被扫描成 text units，每个 unit 保留 source、chunk 和位置 provenance。抽取结果不直接覆盖最终图谱，而是依次落到 candidate_entities、candidate_relationships、candidate_triples，再经过融合生成 entities、relationships、rejected_triples 和 graph.json。

这种分层让每一步都能 inspect 和复现，也允许在不重新抽取的情况下调试融合或问答阶段。

### 4.2 图谱融合与拒绝机制

融合阶段对候选实体做名称归一和别名处理，对关系做关系文本对齐，对三元组执行证据检查和评分。无法满足证据或结构约束的候选进入 `rejected_triples`，而不是静默丢弃或强行写入图谱。

默认 JSON artifacts 便于离线 demo 和 CI；需要服务化验证时切换到 Neo4j。两种 graph store 使用相同的索引契约和运行元数据。

### 4.3 三层向量召回与 GraphRAG 路由

向量检索不是只建一个文本索引，而是分为 text units、entities 和 community reports 三层。local 问题优先找局部实体、关系和原文证据；global 问题可以利用社区检测和社区报告回答文档集合的主题问题。

Embedding provider 可插拔，支持 mock、OpenAI-compatible 和 sentence-transformers；后端可以使用 NumPy 或 FAISS-GPU。这样既能在无 API key 的环境运行离线 demo，也能切换到真实模型验证。

### 4.4 Citation 与运行可观测性

回答不仅保存文本，还保存使用过的证据和 citation 元数据。每次运行写入 `run_events.jsonl`、`run_summary.json` 等 artifacts，CLI 可检查 graph、entities、relationships、rejected triples、vectors 和 run 状态，便于定位“召回错、融合错还是答案选择错”。

### 4.5 可复现发布链路

`verify_release.sh` 会关闭真实 LLM smoke 和 Neo4j 环境，验证默认离线路径：安全检查、安装、CLI、索引、问答、图谱检查、运行检查、QA eval 和全量测试。真实 LLM 路径则显式要求配置，不允许缺少凭据时静默退回 mock。

## 5. 最难的问题

### 难题一：抽取错误如何不污染图谱

用 candidate/final/rejected 三层 artifact 把“模型提议”和“系统接受”分开；融合阶段保留评分和证据，拒绝结果也持久化，后续可以导出 review queue，而不是无法解释地丢失。

### 难题二：local 和 global 问题不能用同一种检索

局部问题需要实体和邻接证据，全局问题需要跨文档主题和社区摘要。系统采用路由和三层向量索引，分别评估局部证据召回与社区报告质量，避免一个 top-k 策略包打天下。

### 难题三：mock、真实 LLM 和 Neo4j 如何保持行为一致

provider、extractor、answerer 和 graph store 都通过接口注入；默认 demo 用 mock 保证离线可复现，真实路径缺少凭据则明确失败。release gate 固定走离线路径，生产路径另行做显式验证，避免把 mock 结果冒充真实模型效果。

### 难题四：如何区分证据召回问题和答案生成问题

HotpotQA 结果中 support recall 为 1.0，但 EM 低于 1.0，说明证据大多找到了，剩余损失主要在最终答案选择和表达。项目保留 failure taxonomy、逐题结果和 support 指标，能把问题定位到不同阶段。

## 6. 项目结果与量化验证

| 指标 | 结果 | 口径 |
|---|---:|---|
| Release verification | 通过 | 默认离线发布链路 |
| Full pytest | 459 通过，4 skipped | README 最新本地 gate |
| Offline QA | 7/7 通过 | 示例离线问答集 |
| HotpotQA isolated real20 | 16/20，EM 0.80，token F1 0.80 | 真实抽取隔离评估 |
| HotpotQA isolated real100 | 78/100，EM 0.60，token F1 0.7083 | 真实抽取隔离评估 |
| HotpotQA support recall | 1.0 | 证据支持召回 |

结果说明：证据检索和 citation grounding 相对稳定，但最终答案选择仍有改进空间；真实 LLM 抽取和结构化输出解析仍处于 beta 阶段。

## 7. 现场演示顺序

1. 用示例文档执行 `kgqa index`。
2. 查看 entities、relationships 和 rejected triples。
3. 提一个 local 问题，展示实体和原文证据。
4. 提一个 global 问题，展示 community report 路径。
5. 展示带 citation 的答案和 `inspect run` 运行记录。
6. 运行 offline release gate，展示无 API key 的可复现验证。

## 8. 可能追问

### 和普通向量 RAG 有什么区别？

它保留原文检索，但额外构建实体、关系、三元组和社区证据，使问题可以沿图结构组织多跳和全局证据。

### 为什么默认使用 JSON，而不是强制 Neo4j？

JSON artifacts 更容易离线运行、检查和进入 CI；Neo4j 是可选 production-path，适合服务化和社区图投影。

### support recall 1.0 为什么 EM 只有 0.60？

说明证据已经召回，但最终答案选择、组合或表达仍可能出错。项目把 retrieval 和 answer selection 分开评估，而不是把问题归因给图谱召回。

### 当前限制是什么？

这是 beta prototype，真实 LLM 抽取、复杂多跳推理、社区报告质量和生产部署仍有边界；API skeleton 不是托管生产服务。

## 9. 1 分钟总结

OpenFusionKGQA 的核心是把开放文本问答拆成可检查的图谱工程链路：先保留原文 provenance，再做候选抽取和融合，拒绝不可靠三元组，最后按 local/global 问题类型组织图文证据并生成 citation。项目已经具备可运行 CLI、离线 release gate、Neo4j 路径和 benchmark，但当前仍应诚实定位为 beta，主要改进方向是最终答案选择和真实 LLM 抽取鲁棒性。

## 来源

- `<local-user-home>/作品集/OpenFusionKGQA/README.md`
- `<local-user-home>/作品集/OpenFusionKGQA/docs/artifacts.md`
- `<local-user-home>/作品集/OpenFusionKGQA/docs/graphfusion_implementation_guide.md`
- `<local-user-home>/作品集/OpenFusionKGQA/docs/project_interview_defense_guide.md`
