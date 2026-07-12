---
摘要: BERT 和 GPT 是 Transformer 架构的两个代表性分支，核心区别在于注意力方向和预训练任务。
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制, 基础]
---

# BERT与GPT的区别 BERT vs GPT

## 核心内容

BERT 和 GPT 是 Transformer 架构的两个代表性分支，核心区别在于注意力方向和预训练任务。BERT 用双向自注意力，预训练 MLM（遮盖 token 预测），适合理解类任务；GPT 用单向因果注意力，预训练自回归语言建模，适合生成类任务。现在的 LLM 基本都是 GPT 路线的 decoder-only 架构。

## 和我的项目的关系

我的项目都基于 GPT 路线的大模型，但 BERT 的思路仍有启发：[[TripleChecker]] 里的 NLI 验证本质就是双向理解任务；BERT 的 MLM 思路可以借鉴到 KG 质量检测——随机遮盖三元组元素让模型预测，和原抽取值对比发现幻觉。

## 交叉引用

- [[Transformer 自注意力机制]]
- [[文本蕴含与自然语言推理 NLI]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[TripleChecker]]

## 更新记录

- 2026-07-04: 首次建页
