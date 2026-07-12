---
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度, 前沿]
---

# ReDeEP 机制可解释性

## 核心内容

ReDeEP（Sun et al., ICLR 2025）用机制可解释性（Mechanistic Interpretability）检测 RAG 里的幻觉。通过分析 LLM 内部的注意力头和 FFN，区分模型是在用外部检索内容还是在用参数化内部知识生成答案。当模型更多依赖参数化知识而忽略检索内容时，就容易产生幻觉。这是 RAG 幻觉检测的前沿工作，从内部机制入手。

## 和我的项目的关系

ReDeEP 和我的工作形成完美互补：ReDeEP 是「内部视角」——看 LLM 脑子里在想什么；[[TripleChecker]] 是「外部视角」——看生成内容和证据文本是否一致。两者结合可以构建更强的幻觉检测系统：内部机制异常 + 外部证据不一致 = 高置信度幻觉。面试时可以讲这个互补关系，展示我对整个领域的全景理解——我不是只做自己的那一点，而是知道我在整个领域坐标系里的位置。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[前沿趋势 Frontier]]
- [[TripleChecker]]
- [[RAGChecker]]

## 更新记录

- 2026-07-04: 首次建页
