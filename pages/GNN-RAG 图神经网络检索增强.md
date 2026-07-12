---
摘要: GNN-RAG（arxiv 2024）把 GNN 引入 RAG 的检索阶段。
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG, KG, 前沿]
---

# GNN-RAG 图神经网络检索增强

## 核心内容

GNN-RAG（arxiv 2024）把 GNN 引入 RAG 的检索阶段。先用 GNN 在知识图谱上做推理，找到和问题相关的实体路径；再把这些路径转换成 LLM 能理解的上下文来生成答案。核心是分工：GNN 擅长在图上做多跳推理，LLM 擅长语言理解和生成，两者各展所长。代表了「用专门的图模块做图的事，不是把所有任务都交给 LLM」这个方向。

## 和我的项目的关系

GNN-RAG 的分工思想正是我所有项目遵循的设计哲学：
- [[TripleChecker]] 里 NLI 模型做语义验证，规则过滤做结构约束，不是全扔给 LLM
- [[EvidenceFirst]] 里确定性状态机做路径检查，LLM 做自然语言理解，硬规则和软模型结合
- [[Graph Fusion 图融合]] 里对齐算法做结构匹配，LLM 做语义对齐
- 面试时可以把 GNN-RAG 作为我设计哲学的「同道中人」来引用——我不是唯一一个相信「专门模块做专门事」的人，这是整个领域的趋势

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[知识图谱 KG]]
- [[图神经网络 GNN]]
- [[前沿趋势 Frontier]]
- [[EvidenceFirst]]
- [[TripleChecker]]

## 更新记录

- 2026-07-04: 首次建页
