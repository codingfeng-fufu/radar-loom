---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制]
---

# 上下文学习 In-context Learning

## 核心内容

In-context Learning（上下文学习，又称小样本学习）是GPT-3发现的LLM最神奇的能力：在推理时把任务描述和几个示例放在prompt里，不需要任何梯度更新或微调，模型就能完成新任务。分三种形式：Zero-shot——只有任务描述，没有示例；One-shot——一个示例；Few-shot——几个示例。为什么有效至今没有统一的理论解释，主流假说包括任务识别、隐式贝叶斯推理、分布内类比等。上下文学习的局限性是对prompt的格式和示例选择非常敏感，长度有限制。它是LLM能快速适配新任务的核心能力。

## 和我的项目的关系

上下文学习是整个LLM应用范式的基础，也正是因为有了ICL，[[EvidenceFirst]]这样的模块化架构才成为可能。EvidenceFirst不需要训练任何模型——实体映射用LLM的ICL能力做，NLI验证用LLM的ICL能力做，答案生成也用LLM的ICL能力做，所有的模块都是直接调用现成的LLM，不需要微调。如果没有ICL，每一个模块都需要单独标注数据微调，EvidenceFirst这样的系统根本不可能做出来。可以说，我所有的工作都是站在ICL这个巨人的肩膀上。面试时可以主动提这个背景，展示我对大模型阶段研究范式转型的理解。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[提示工程 Prompt Engineering]]
- [[思维链 Chain-of-Thought]]
- [[TripleChecker]]

## 更新记录

- 2026-07-04: 首次建页
