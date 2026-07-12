---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度]
---

# 模型校准 Calibration

## 核心内容

模型校准衡量的是「模型说它有80%把握的时候，是不是真的大约80%的情况下是对的」。现代深度神经网络普遍存在过度自信问题——给出很高的置信度但实际准确率达不到。常用校准方法包括Temperature Scaling（用一个标量缩放logits让softmax输出更平滑）、Platt Scaling、直方图分箱等。评测指标是ECE（Expected Calibration Error），把样本按置信度分箱，计算每个箱里平均置信度和实际准确率的差异。

## 和我的项目的关系

[[EvidenceFirst]]的Table 2报告的Risk vs Coverage分析本质上就是在做校准分析——检查「checked path」这个状态标记是否真的对应了更高的准确率。虽然Risk 1.000但gold-proxy precision只有0.151这个结果看起来像是「过度自信」，但这其实是有意的设计：EvidenceFirst追求的是结构层面的保守校准（「只要我说checked，那结构上一定连通」），而不是语义层面的校准（「只要我说checked，那答案一定对」）。这是一个重要的概念区分，面试时要讲清楚。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[不确定性量化 Uncertainty Quantification]]
- [[选择性预测 Selective Prediction]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-04: 首次建页
