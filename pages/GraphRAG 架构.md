---
摘要: 微软GraphRAG是2024年引爆GraphRAG方向的经典工作。
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG]
---

# GraphRAG 架构

## 核心内容

微软GraphRAG是2024年引爆GraphRAG方向的经典工作。核心流程：从文档里用LLM自动抽取实体和关系构建知识图谱 → 用Louvain算法做社区发现，把图谱分成多个子图社区 → 对每个社区做摘要生成 → 查询时支持Local模式（精确实体查询）和Global模式（全局摘要查询）两种模式。GraphRAG的核心贡献是证明了图结构能显著提升对大规模文档的问答质量，特别是需要聚合跨文档信息的问题。但GraphRAG也有明显的局限性：它只关心「能不能找到答案」，不关心「找到的答案对不对」——没有做任何来源验证或可观测性设计。

## 和我的项目的关系

[[EvidenceFirst]]就是在GraphRAG框架上加了可观测性层。我在论文里明确说了：EvidenceFirst不对GraphRAG的检索或生成部分做任何修改，只在中间加了状态机和verifier。这是一个非常巧妙的定位——我不是在做「又一个GraphRAG变体」来刷EM指标，我是在做「所有GraphRAG系统都应该加的质量监控层」。这个定位让我的工作跳出了SOTA竞争的红海，进入了一个没人认真做过的蓝海方向——GraphRAG的可观测性。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[EvidenceFirst]]
- [[可观测性 Observability]]
- [[LightRAG]]
- [[确定性状态机 Deterministic State Machine]]

## 更新记录

- 2026-07-04: 首次建页
