---
摘要: LLM推理优化的两个核心技术是KV Cache和量化。
来源: papers/foundational_knowledge_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [LLM机制]
---

# LLM 推理优化 KV Cache Quantization

## 核心内容

LLM推理优化的两个核心技术是KV Cache和量化。KV Cache：Transformer生成每个新token时需要重新计算所有历史token的Key和Value，这是冗余的——把这些历史KV缓存下来，生成下一个token时直接用，推理速度提升一个数量级以上，现在所有LLM推理框架都默认开KV Cache。量化：把模型参数从FP32/FP16压缩到INT8/INT4，减少显存占用和计算量，轻微损失精度但通常在可接受范围内，让大模型能在消费级显卡上跑。vLLM的PagedAttention进一步优化了KV Cache的内存管理，像操作系统管理虚拟内存一样管理KV Cache，大幅提升吞吐量。

## 和我的项目的关系

推理优化本身不是我的研究方向，但它是我的研究能落地的前提。[[EvidenceFirst]]的设计目标之一就是在不增加太多推理成本的前提下增加可观测性——状态机的BFS搜索开销和LLM推理开销比起来可以忽略不计，而且所有验证逻辑都是纯CPU运算，不占用GPU资源。如果我的设计每回答一个问题都要多跑一次LLM，那运营成本就翻倍了，工业界不会用；但EvidenceFirst的架构是一次LLM调用加一次轻量BFS，额外开销几乎可以忽略，这是它能落地的关键。面试时提这个点，展示我有工程成本意识，不是个只看指标的书呆子。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[Transformer 自注意力机制]]
- [[EvidenceFirst]]
- [[实验可复现性 Reproducibility]]

## 更新记录

- 2026-07-04: 首次建页
