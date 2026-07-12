---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [RAG]
---

# RAG 评测指标 EM Recall MRR

## 核心内容

RAG问答常用三大类指标：检索侧指标——Precision@k（前k个结果里有多少相关的）、Recall@k（所有相关文档里有多少被找到了），衡量检索准不准；生成侧指标——EM（Exact Match，答案字符串完全一致才给分）、F1（答案和标准答案的token级重叠），衡量生成对不对；排序指标——MRR（Mean Reciprocal Rank，第一个正确答案排名的倒数的平均）、Hits@k（正确答案出现在前k个的比例），衡量排序好不好。三大指标各有侧重：检索召回率高不代表最终答案对，最终答案对不代表检索质量高，需要综合看。

## 和我的项目的关系

[[EvidenceFirst]]最有特色的一点就是它不只报告这些传统指标，还额外报告了「状态分布」这个新指标——多少样本进入checked path、多少进入disconnected、多少进入residual gap。这是我提出的「可观测性指标」，传统RAG论文都不报告这个。面试时可以主动提出：现在RAG评测有一个盲区——两个系统可能有完全相同的EM，但一个90%的样本都是checked path，另一个只有30%，它们的运维成本天差地别，但传统指标完全看不出来。这展示我对RAG评测有超出论文标准的深度思考。

## 交叉引用

- [[检索增强生成 RAG-GraphRAG]]
- [[EvidenceFirst]]
- [[分层评测 Stratified Evaluation]]
- [[审计风险队列 Audit Risk Queue]]

## 更新记录

- 2026-07-04: 首次建页
