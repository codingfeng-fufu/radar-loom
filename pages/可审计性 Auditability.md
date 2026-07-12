---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 可审计性 Auditability

## 核心内容

可审计性是指第三方（监管者、用户、内审人员）能够独立检验AI系统决策过程和依据的能力，不需要依赖系统开发者的说明。核心要求是决策过程可追溯、证据不可篡改、检验算法公开。在LLM推理系统中，可审计性意味着从用户提问到最终答案的每一步都有可独立验证的记录，包括检索到的证据、推理的中间状态、模型调用的参数。关键技术包括artifact指纹固定、离线验证器、开源检验代码。

## 和我的项目的关系

[[EvidenceFirst]]专门设计了离线verifier机制，通过SHA-256指纹固定所有参与实验的artifact文件，任何人都可以独立运行验证代码重现论文报告的所有数字。这实现了严格的可审计性，区别于大多数RAG论文只报告指标不提供可复现检验的做法。可审计性是EvidenceFirst作为「观测性层」而非「性能优化层」的核心标志。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[可观测性 Observability]]
- [[可验证性 Verifiability]]
- [[SHA-256 产物指纹]]
- [[实验可复现性 Reproducibility]]

## 更新记录

- 2026-07-04: 首次建页
