---
摘要: 不确定性量化是让模型不仅给出预测，还给出对这个预测的置信程度。
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度]
---

# 不确定性量化 Uncertainty Quantification

## 核心内容

不确定性量化是让模型不仅给出预测，还给出对这个预测的置信程度。分为两大类：Aleatoric uncertainty（数据本身的噪声，即使无限数据也无法消除，比如标注歧义）和Epistemic uncertainty（模型知识的不确定性，可以通过更多数据或更好的模型降低）。在LLM场景，难点是模型输出的是离散token序列而不是连续值，常用方法包括看token级别的预测概率分布、多次采样看输出一致性（Self-consistency）、温度缩放校准等。

## 和我的项目的关系

我的研究方向本质上是用「结构化不确定性」替代「概率化不确定性」。传统不确定性量化给出一个0-1之间的置信度分数，但这个分数不可解释、不可审计。而[[EvidenceFirst]]用确定性状态机把不确定性映射为5种离散、可解释、可操作的状态（checked path等），用户看到的不是一个黑盒分数，而是「这里缺了一个实体」、「这里两个节点不连通」这样的结构化诊断。这是不确定性量化的工程化升级，比单纯报告logits概率要实用得多。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[模型校准 Calibration]]
- [[确定性状态机 Deterministic State Machine]]
- [[选择性预测 Selective Prediction]]

## 更新记录

- 2026-07-04: 首次建页
