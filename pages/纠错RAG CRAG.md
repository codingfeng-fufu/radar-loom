---
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG, 可信度]
---

# 纠错RAG CRAG

## 核心内容

CRAG（Corrective Retrieval Augmented Generation）是2024年的工作，核心洞察是：RAG系统不要假设检索到的文档总是对的，而是要先评估检索结果和问题的相关性，如果评估为「不相关」就触发网络搜索做补充检索，如果评估为「部分相关」就同时用原检索结果和新检索结果融合。CRAG在RAG的检索步骤和生成步骤之间加了一个「评估-纠错」的中间层，这和EvidenceFirst的设计理念高度共鸣——都是在生成前对中间结果做质量判断。CRAG关注的是检索层的质量，EvidenceFirst关注的是结构层的质量。

## 和我的项目的关系

CRAG和[[EvidenceFirst]]是同一条技术路线上的两个不同层次的工作。CRAG解决的是「检索到的文本好不好」的问题，EvidenceFirst解决的是「检索到的结构通不通」的问题。两者可以结合使用——一个完整的可信RAG系统应该先过CRAG的文本相关性检查，再过EvidenceFirst的结构连通性检查，最后才送到LLM生成。这个「分层质量保障」的思路是我未来可以延伸的研究方向，面试时可以主动提，展示我对领域有系统性的思考而不是只盯着自己的一篇论文。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[RAGChecker]]
- [[Self-RAG]]

## 更新记录

- 2026-07-04: 首次建页
