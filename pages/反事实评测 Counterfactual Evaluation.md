---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 反事实评测 Counterfactual Evaluation

## 核心内容

反事实评测通过系统性地改变输入的某个属性，观察输出如何变化，来理解模型的依赖关系和潜在偏见。核心问题是「如果这个输入特征变了，结果会不一样吗？」。在RAG和归因研究中，反事实评测特指通过移除特定组件（checker、repair、reader context等）来验证每个组件声称的作用是否真实存在。这是比消融实验更严格的因果推断方法，因为它直接操纵原因变量观察结果变化。

## 和我的项目的关系

[[EvidenceFirst]]的消融实验本质上就是系统化的反事实评测。通过逐个移除状态检查器、图修复模块、reader上下文等组件，观察答案质量和可观测性指标的变化，严谨地验证了每个组件的真实作用。特别是关于去掉checker后EM差异仅0.6个百分点（McNemar检验p=0.659）的发现，揭示了「性能不变但可观测性大幅提升」的核心洞察，这是只用整体指标评测无法发现的。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[分层评测 Stratified Evaluation]]
- [[McNemar检验]]

## 更新记录

- 2026-07-04: 首次建页
