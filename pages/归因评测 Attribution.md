---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, TripleChecker]
---

# 归因评测 Attribution

## 核心内容

归因评测是指验证生成内容里的具体声明（claim）是否能在指定的来源材料中找到支撑证据的过程。区别于Grounding（架构层面是否基于检索生成），归因是评测层面的操作——给定一个已经生成的输出，逐句逐claim地检验它是否真的被来源支撑。标准流程分为三步：Claim分解（把长文本拆解为原子化声明）、证据检索（对每个claim找最相关的证据片段）、蕴含判断（常用NLI模型或LLM-as-judge）。归因评测是RAG系统可信度的黄金标准。

## 和我的项目的关系

[[TripleChecker]]本质上就是把归因评测框架应用到了三元组这种最小粒度的claim上，把「评测机制」变成了「过滤机制」。TripleChecker的claim-evidence-entailment三步流程和归因评测的标准方法论完全同构，区别只在于TripleChecker运行在推理时，而传统归因评测运行在事后。这意味着TripleChecker的理论基础非常扎实，可以直接引用Rashkin等人2023年测量归因的经典工作作为理论支撑。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[TripleChecker]]
- [[文本蕴含与自然语言推理 NLI]]
- [[溯源 Provenance]]
- [[引用召回与精确率 Citation Recall Precision]]

## 更新记录

- 2026-07-04: 首次建页
