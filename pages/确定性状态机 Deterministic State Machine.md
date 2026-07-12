---
来源: papers/simulation_core_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [KG, EvidenceFirst]
---

# 确定性状态机 Deterministic State Machine

## 核心内容

确定性状态机是用固定规则而不是概率模型来判断系统状态的机制，每一步推理都对应明确的规则，结果是确定的、可复现的、不依赖统计分布。典型的EvidenceFirst流程：给定问题和构建好的证据子图，先做实体检索（精确匹配、串匹配、token overlap三种方式映射到图节点）→ 找候选答案节点 → 测候选实体到答案节点的最短路径 → 如果路径存在且长度≤阈值就是checked path → 如果有缺口触发repair → missing entity触发实体增强修复，disconnected pair触发bridge repair → repair完再跑一次同样的结构检查 → 通过就是repaired path，还有缺口就是residual gap → 根本没有可用的图证据就fallback到段落检索。整个过程没有随机性。

## 和我的项目的关系

这是[[EvidenceFirst]]的核心架构创新。绝大多数GraphRAG系统用LLM来做路径选择和推理判断，结果不可复现且LLM的推理能力不稳定。EvidenceFirst把「这条路通不通」这个判断从LLM手里拿出来，交给确定性的BFS最短路径检查。LLM只负责最后的自然语言生成，不负责结构判断。这种「符号负责结构，神经负责语义」的分工，是EvidenceFirst最深刻的设计洞见，也是面试时要重点讲的架构亮点。

## 交叉引用

- [[知识图谱 KG]]
- [[EvidenceFirst]]
- [[符号人工智能 Symbolic AI]]
- [[神经符号方法 Neuro-Symbolic AI]]
- [[可验证性 Verifiability]]

## 更新记录

- 2026-07-04: 首次建页
