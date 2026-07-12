---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 中
首次记录: 2026-07-04
tags: [可信度]
---

# 红队测试 Red-teaming

## 核心内容

红队测试是主动尝试攻破一个AI系统的可信性，找出它的失败模式，类似网络安全里的渗透测试。对LLM系统，红队通常包括：尝试构造能诱导幻觉的问题、尝试prompt injection攻击、尝试找出模型在benchmark上表现好但在特定输入上表现极差的「角落案例」。红队和benchmark形成互补——benchmark衡量平均情况下的表现，红队专门找最坏情况。这是可信AI工程化的必备环节，而不只是学术研究。

## 和我的项目的关系

[[EvidenceFirst]]的审计风险队列本质上就是自动化红队的输出。系统自动把20%最有可能出错的样本挑出来形成审计队列，这相当于系统自己做自己的红队。这种「内置红队」设计的优势是可以持续运行，而不只是上线前做一次。在面试里可以把这个作为我对可信AI工程化的思考——学术研究关注平均指标，工业落地关注最坏情况，而我的工作在两者之间架起了桥梁。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[审计风险队列 Audit Risk Queue]]
- [[对抗样本 Adversarial Examples]]
- [[提示注入 Prompt Injection]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-04: 首次建页
