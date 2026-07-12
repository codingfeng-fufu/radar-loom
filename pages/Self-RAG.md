---
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG]
---

# Self-RAG

## 核心内容

Self-RAG是让LLM学会自我反思的RAG框架，ICLR 2024的代表作。核心思路：训练一个特殊的token机制，让模型在生成时动态决定——是否需要检索（Retrieve token）、检索结果是否相关（IsREL token）、生成内容是否有来源支撑（IsSUP token）、整体是否有用（IsUSE token）。这样模型能自适应地决定何时检索、如何用检索结果，而不是无条件地把所有检索结果都用上。Self-RAG的关系：它是在生成阶段做自我评估，EvidenceFirst是在生成前做结构化状态记录，两者理念相通但层次不同，可以结合使用。

## 和我的项目的关系

Self-RAG和[[EvidenceFirst]]有一个很重要的理念共鸣：都认为「不是所有RAG输出的质量都是一样的」，RAG系统应该对自己输出的质量有自知之明。但Self-RAG用的是「神经自省」——让LLM自己评估自己，结果还是概率性的、不可靠的；EvidenceFirst用的是「符号验证」——用确定性的结构检查来评估状态，结果是可复现的、可审计的。面试时可以把这个对比讲清楚：EvidenceFirst在Self-RAG的方向上更进了一步，把「自我评估」从LLM的主观判断变成了客观的结构事实。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[EvidenceFirst]]
- [[可验证性 Verifiability]]
- [[提示注入 Prompt Injection]]

## 更新记录

- 2026-07-04: 首次建页
