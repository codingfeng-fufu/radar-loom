---
摘要: IRCoT在多跳问答中交替执行思维链推理与证据检索。
来源: papers/engineering_and_frontier_works_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [RAG]
---

# 交替检索推理 IRCoT

## 核心内容

IRCoT（Interleaving Retrieval with Chain-of-Thought Reasoning）是ACL 2023的经典RAG工作，核心思想很简单：交替进行检索和推理——每生成一步CoT推理，就用这一步的推理结果做一次新的检索，而不是在最开始只检索一次然后生成完整答案。比如回答「A的老板的毕业学校是哪里？」，传统RAG一开始就检索「A的老板」，然后直接生成完整答案；IRCoT先生成第一步推理「我需要先知道A的老板是谁」，然后检索得到老板B，再生成第二步推理「我需要知道B的毕业学校」，再检索得到学校C，最后生成最终答案。交替检索推理的优势是解决了多跳推理中间状态丢失的问题，是多跳RAG领域的重要基线。

## 和我的项目的关系

IRCoT是[[EvidenceFirst]]的重要基线之一，也是所有多跳RAG工作都要对比的对象。但EvidenceFirst和IRCoT有一个本质的方法论区别：IRCoT每一步检索还是依赖LLM的推理来决定下一步检索什么，LLM想错了就会跑偏；而EvidenceFirst用知识图谱作为结构化的「记忆外部化」，路径是客观存在在图里的，不是LLM想出来的。这个对比很适合在面试里讲——如果面试官问「你的工作和IRCoT有什么不同」，就可以用这个「主观推理 vs 客观结构」的框架来回答。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[EvidenceFirst]]
- [[思维链 Chain-of-Thought]]
- [[KG-RAG 工作原理]]

## 更新记录

- 2026-07-04: 首次建页
