---
摘要: 审计风险队列按风险排序样本以集中有限的人工审查资源。
来源: papers/simulation_core_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 审计风险队列 Audit Risk Queue

## 核心内容

审计风险队列是把系统判断为「高风险」的样本自动聚合成一个优先审查的队列，把有限的人工审计资源集中在最需要的地方，而不是平均用力。EvidenceFirst的实现方式是：每个样本进入disconnected或residual gap状态就自动进入审计队列，这些状态对应的错误率明显高于checked path状态。20%的review budget就能集中67%的错误，相当于抽样效率提升了3倍以上。核心洞察是「错误不是均匀分布的」，结构化状态标记可以用来预测错误概率。

## 和我的项目的关系

[[EvidenceFirst]]的审计风险队列是把学术研究转化为工程价值的关键设计。大多数GraphRAG论文的产出是一个更好的EM数字，工业落地价值有限——运营团队根本不知道什么时候该相信系统的输出。而审计风险队列直接对接了真实的业务流程：运营团队不需要看所有的输出，只需要看队列里的20%就能抓住大多数错误。这个设计让EvidenceFirst从一个「更好的问答系统」变成了「可运维的问答系统」，这是论文能被WISE接收的重要原因——工业界关心可运维性远胜于多几个点的EM。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[分层评测 Stratified Evaluation]]
- [[红队测试 Red-teaming]]
- [[可观测性 Observability]]

## 更新记录

- 2026-07-04: 首次建页
