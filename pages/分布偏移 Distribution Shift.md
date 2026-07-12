---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, RAG]
---

# 分布偏移 Distribution Shift

## 核心内容

分布偏移是指模型部署时遇到的数据分布和训练/测试时的数据分布不一致，是AI系统落地失败的首要原因之一。常见类型包括：协变量偏移（输入分布变了但输出关系不变）、概念偏移（类别比例变了）、概念漂移（输入输出关系本身变了）。对RAG系统而言，最直接的分布偏移体现在检索质量上——benchmark数据集通常提供精心curated的检索结果，而真实环境的检索噪声大得多。分布偏移是机器学习的「阴暗面」，很少在论文里被公开讨论但决定了大多数项目的生死。

## 和我的项目的关系

[[EvidenceFirst]]专门设计了Tavily真实Web检索探针实验来测试分布偏移下的系统行为。结果显示从benchmark curated检索切换到live Web检索后，checked path比例从29%降到20%，residual gap从39%升到67%，但系统依然能感知并响应这种分布偏移，而不是静默失败。这种「在分布偏移下依然知道自己不知道」的能力，正是可观测性层的核心价值——性能可以下降，但可观测性不能下降。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[检索增强生成 RAG-GraphRAG]]
- [[可观测性 Observability]]
- [[确定性状态机 Deterministic State Machine]]
- [[对抗样本 Adversarial Examples]]

## 更新记录

- 2026-07-04: 首次建页
