---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制]
---

# 预训练与微调 Pretrain vs Finetune

## 核心内容

大模型训练分为两个阶段：预训练在大规模无标注语料上学习语言通用表示，计算成本极高；微调在特定任务的有标注数据上继续训练，让基础模型适配具体任务。LLM 时代纯微调范式被 Prompt-based 方法和 RLHF 替代，但在格式控制、领域适配、成本优化场景下仍不可替代。

## 和我的项目的关系

我的项目不需要自己做预训练，但微调是重要的成本优化选项：[[TripleChecker]] 的 qwen-plus 验证器未来可以考虑蒸馏后再微调；[[EvidenceFirst]] 的确定性规则如果要蒸馏成端到端模型也需要微调。关键是理解从纯提示词到微调的整个技术选型光谱。

## 交叉引用

- [[人类反馈强化学习 RLHF]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[提示工程 Prompt Engineering]]
- [[思维链 Chain-of-Thought]]

## 更新记录

- 2026-07-04: 首次建页
