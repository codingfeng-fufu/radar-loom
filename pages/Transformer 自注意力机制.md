---
摘要: 自注意力机制是Transformer的核心，也是大模型技术栈的基础技术。
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制, 基础]
---

# Transformer 自注意力机制

## 核心内容

自注意力机制是Transformer的核心，也是大模型技术栈的基础技术。核心思想：每个token的表示通过和序列中所有其他位置做注意力加权求和得到——每个token映射成Query、Key、Value三个向量，Q和所有K做点积后softmax得到注意力权重，再对V加权求和。多头注意力让这个过程并行做多次，每个头关注不同的语义维度，最后拼接。优势是并行计算（不像RNN要串行）、能捕捉长距离依赖、可解释（能看到每个token关注了哪些位置）。

## 和我的项目的关系

我的研究不直接改进Transformer本身，但我所有工作都建立在LLM的一个关键特性之上——LLM非常擅长自然语言理解和生成，但非常不擅长精确的结构推理和事实验证。[[TripleChecker]]和[[EvidenceFirst]]的架构设计都利用了这个分工：让LLM做它擅长的语义理解（实体识别、自然语言蕴含判断、答案生成），让符号系统做它擅长的结构推理（连通性检查、路径搜索、状态机）。这个分工的洞察本质上来自对Transformer能力边界的深刻理解。

## 交叉引用

- [[Transformer 架构 Architecture]]
- [[多头注意力 Multi-Head Attention]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[位置编码 Positional Encoding]]
- [[层归一化 LayerNorm BatchNorm]]
- [[残差连接 Residual Connection]]
- [[前馈网络 FFN Feed-Forward Network]]
- [[神经符号方法 Neuro-Symbolic AI]]

## 更新记录

- 2026-07-04: 首次建页
- 2026-07-16: 补齐交叉引用,指向新增的 Transformer 架构 hub、多头注意力、残差连接与 FFN 部件页。
