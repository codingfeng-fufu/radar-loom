---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [KG, RAG]
---

# 知识接地 Grounding

## 核心内容

Grounding（接地）是指生成的内容能够追溯并锚定到具体的、外部可验证的证据上，而不是悬空依赖模型的参数化记忆。在KG-RAG里，Grounding体现在两个层面：实体接地——问题里提到的实体被正确映射到图谱里的节点；证据接地——生成的答案能够关联到图谱里具体的路径或三元组。Grounding不是万能的：EvidenceFirst的核心发现就是结构上grounded（checked path）不代表语义上充分（gold-proxy precision只有0.151），Grounding解决的是「有没有挂钩证据」的问题，不解决「这个证据是不是真的对」的问题。

## 和我的项目的关系

这是我研究的核心概念枢纽。[[TripleChecker]]做三元组级别的Grounding验证——检查每个抽取的三元组是否真的被来源文本支撑。[[EvidenceFirst]]做推理级别的Grounding验证——检查整条答案的推理路径是否真的在图谱里连通。两者层层递进，共同构成了从数据到推理的完整Grounding链条。我在面试中应该把Grounding作为整个研究故事的锚点概念。

## 交叉引用

- [[知识图谱 KG]]
- [[检索增强生成 RAG-GraphRAG]]
- [[TripleChecker]]
- [[EvidenceFirst]]
- [[归因评测 Attribution]]
- [[溯源 Provenance]]

## 更新记录

- 2026-07-04: 首次建页
