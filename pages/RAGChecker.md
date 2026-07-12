---
摘要: RAGChecker以细粒度指标分别诊断RAG的检索和生成错误。
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG, 可信度]
---

# RAGChecker

## 核心内容

RAGChecker是2024年的工作，是细粒度的RAG诊断框架，把RAG的错误分解到检索模块和生成模块，分别用精确的指标衡量。核心思路：把最终答案拆分成一系列原子化的claim，对每个claim判断有没有检索到的证据支撑——如果有支撑但答案还是错了，那是生成模块的问题；如果根本就没检索到相关证据，那是检索模块的问题。用LLM-as-judge来做这个细粒度判断，输出每个模块的精确的错误率。RAGChecker最大的贡献是结束了「RAG效果不好到底是谁的锅」这个争吵，让大家可以针对性地优化。

## 和我的项目的关系

RAGChecker是事后评估框架，[[EvidenceFirst]]是运行时监控框架——两者是互补关系而不是竞争关系。RAGChecker在你整个系统跑完之后给你出一份诊断报告，告诉你哪里错了；EvidenceFirst在系统运行的过程中实时告诉你「这个回答我有多大把握」、「哪里可能出问题了」。面试时可以把这个关系讲清楚：我不是在做「又一个RAG诊断工具」，我是在做「可观测的RAG运行时」——前者是体检，后者是实时心电监护。这个定位差异很清晰，能体现我对领域生态的理解。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[归因评测 Attribution]]
- [[引用召回与精确率 Citation Recall Precision]]

## 更新记录

- 2026-07-04: 首次建页
