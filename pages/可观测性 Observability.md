---
摘要: 可观测性是指系统能够暴露其内部运行状态的能力，来自软件工程和分布式系统领域。
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 可观测性 Observability

## 核心内容

可观测性是指系统能够暴露其内部运行状态的能力，来自软件工程和分布式系统领域。核心思想是「日志、轨迹、指标三位一体」，让系统能够回答事先没有预料到的问题。在AI系统中，可观测性超越了传统监控，要求系统不仅报告健康状态，还要能够重现推理过程、追踪证据来源。关键方法包括状态机记录、证据轨迹保存、SHA-256指纹固定artifact。

## 和我的项目的关系

[[EvidenceFirst]]的核心设计目标就是可观测性。通过确定性状态机将每条query的处理过程映射为5种状态（checked path, disconnected, missing entity, residual gap, passage fallback），配合SHA-256指纹固定所有artifact，实现了GraphRAG系统的可观测性升级。这是论文的核心贡献之一，区别于所有只追求EM指标的GraphRAG工作。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[确定性状态机 Deterministic State Machine]]
- [[SHA-256 产物指纹]]
- [[可审计性 Auditability]]
- [[可验证性 Verifiability]]

## 更新记录

- 2026-07-04: 首次建页
