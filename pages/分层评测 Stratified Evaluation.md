---
摘要: 分层评测是指不满足于报告整体平均指标，而是把测试集按某种属性（难度、类别、状态）划分成不同子集分别报告性能。
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst, 评测]
---

# 分层评测 Stratified Evaluation

## 核心内容

分层评测是指不满足于报告整体平均指标，而是把测试集按某种属性（难度、类别、状态）划分成不同子集分别报告性能。核心价值是暴露平均值掩盖的问题——比如整体准确率80%，但某个占比10%的困难子集准确率可能只有20%。分层评测的关键是选择有工程或学术意义的分层维度，而不是为了分层而分层。常见的分层维度包括：难度等级、问题类型、证据来源、系统内部状态等。

## 和我的项目的关系

[[EvidenceFirst]]的核心设计之一就是按证据状态分层评测，而不是只报告整体EM。论文的Table 2将测试结果按checked path/disconnected/missing entity/passage fallback四种状态分层报告，清晰展示了不同状态下的性能差异（如disconnected状态下EM只有0.455，远低于checked状态的0.703）。这种分层信息对可信AI至关重要，也是EvidenceFirst作为观测性层的核心交付物。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[确定性状态机 Deterministic State Machine]]
- [[审计风险队列 Audit Risk Queue]]
- [[RAG 评测指标 EM Recall MRR]]

## 更新记录

- 2026-07-04: 首次建页
