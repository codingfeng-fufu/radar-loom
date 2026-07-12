---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 溯源 Provenance

## 核心内容

溯源（Provenance，又称来源追溯、世系追踪）是追踪数据或结论的产生过程，回答「它从哪里来、经过了什么转换、依赖了什么前提」的问题。来自数据库领域的Where-provenance和Why-provenance概念。在AI/RAG场景中，溯源具体化为「这个生成的答案是基于哪些检索到的文档/三元组得出的」，核心应用是Citation grounding——要求模型生成的每个声明都能关联到具体的来源文本。溯源是可信AI的基础设施，没有溯源就没有可验证性和可审计性。

## 和我的项目的关系

我的整个研究设计哲学直接继承自数据库溯源研究。[[TripleChecker]]验证每个三元组的来源文本支撑，是三元组级别的Why-provenance。[[EvidenceFirst]]记录每条答案的证据路径和状态转换，是推理级别的Where-provenance。把「为什么」从模糊的事后解释变成可以保存的精确事实结构，这是我的工作区别于主流GraphRAG研究的方法论特征。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[TripleChecker]]
- [[可验证性 Verifiability]]
- [[可审计性 Auditability]]
- [[引用召回与精确率 Citation Recall Precision]]

## 更新记录

- 2026-07-04: 首次建页
