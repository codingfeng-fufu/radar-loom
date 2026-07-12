---
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG]
---

# LightRAG

## 核心内容

LightRAG是微软GraphRAG的轻量级重构版本，去掉了社区发现和社区摘要生成，改为直接在实体图上做Local/Global双模式检索。核心简化：把实体和关系的描述直接存在图节点和边上，检索时把结构信息和描述文本一起送给LLM，不需要先生成社区摘要再检索。这样构建成本大幅降低，检索速度大幅提升，效果在大多数场景下和原版GraphRAG接近但成本只有几分之一。LightRAG是目前工业界落地GraphRAG的首选基线，因为它简单、快、够用。

## 和我的项目的关系

[[EvidenceFirst]]的基线之一就是LightRAG，因为LightRAG已经是GraphRAG在工业界的事实标准。EvidenceFirst不对LightRAG的核心逻辑做任何修改，只在它外面加了可观测性壳——这是一个非常重要的设计选择，意味着任何已经在用LightRAG的团队都可以零成本接入EvidenceFirst，不需要改他们现有的pipeline，只需要加一个状态机中间件。这大大提升了工作的实用价值，也是WISE（工业界顶会）接收它的重要原因之一。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[GraphRAG 架构]]
- [[EvidenceFirst]]
- [[Self-RAG]]

## 更新记录

- 2026-07-04: 首次建页
