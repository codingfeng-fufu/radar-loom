---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度]
---

# 选择性预测 Selective Prediction

## 核心内容

选择性预测（又称拒答 Abstention）的核心思想是「让模型在不确定的时候选择不回答，而不是强行给出一个可能错误的答案」。通过允许模型对一部分样本不给出来换在选择回答的样本上更高的准确率。评测方式通常是画Risk-Coverage曲线：横轴是Coverage（模型选择回答的样本比例），纵轴是Risk（在这些回答里的错误率）。理想的曲线从左下角开始，随着Coverage增加缓慢上升。选择一个合适的工作点是关键的工程权衡。

## 和我的项目的关系

[[EvidenceFirst]]的passage fallback状态本质上就是一种结构化的选择性预测——当没有可用的图证据时，系统转向段落级fallback而不是强行从空图编造答案。但EvidenceFirst比传统选择性预测更进一步：它不是输出一个简单的「我不会」，而是输出「我不会，因为这里缺了一个实体」、「我不会，因为这两个节点之间没有路径」这样的结构化诊断信息。这把「拒答」从一个用户体验问题变成了一个系统迭代的反馈信号。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[不确定性量化 Uncertainty Quantification]]
- [[模型校准 Calibration]]
- [[EvidenceFirst]]
- [[确定性状态机 Deterministic State Machine]]

## 更新记录

- 2026-07-04: 首次建页
