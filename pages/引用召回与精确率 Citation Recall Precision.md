---
摘要: 引用召回率与精确率衡量生成声明是否得到充分且正确的证据支持。
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度, TripleChecker, 评测]
---

# 引用召回与精确率 Citation Recall Precision

## 核心内容

Citation Recall和Citation Precision是「让LLM生成带引用的文本」这个研究方向的两个核心指标。Citation Precision衡量模型给出的每条引用是否真的支撑了它标注的那句话——高Precision意味着「凡有引用必有依据」。Citation Recall衡量一句话需要的所有支撑证据是否都被引用了——高Recall意味着「凡需依据必有引用」。两个指标存在经典的trade-off：引用多了Recall升高但Precision下降，引用少了Precision高但Recall不足。

## 和我的项目的关系

[[EvidenceFirst]]的Support Recall指标（Table 3里的1.0000）本质上就是Citation Recall的一种量化：衡量gold标注的支撑证据是否都被reader的推理过程覆盖了。EvidenceFirst做到了100%的Support Recall，但代价是Precision极低（gold-proxy precision只有0.151）——这是一个非常有意思的trade-off发现，我在面试里可以主动提到这个点，展示我对指标权衡的深刻理解，而不是盲目追求单一指标最大化。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[TripleChecker]]
- [[EvidenceFirst]]
- [[归因评测 Attribution]]
- [[溯源 Provenance]]

## 更新记录

- 2026-07-04: 首次建页
