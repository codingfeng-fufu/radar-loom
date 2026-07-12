---
摘要: 强化学习通过智能体与环境交互并最大化累积奖励来学习策略。
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制, 基础]
---

# 强化学习基本框架 Reinforcement Learning

## 核心内容

强化学习的核心要素：Agent（智能体）、Environment（环境）、State（状态）、Action（动作）、Reward（奖励）。Agent 在每个时间步观察当前状态，选择一个动作，环境转移到新状态并给出奖励，Agent 的目标是最大化累积奖励。Policy 是 Agent 的行为函数，从状态映射到动作；Value function 学习每个状态-动作对的价值；Q-learning 是经典的 value-based 方法；PPO 是目前最常用的 policy gradient 算法，也是 RLHF 里用来对齐 LLM 的算法。

## 和我的项目的关系

RL 对我的项目有两个直接关联：
- [[人类反馈强化学习 RLHF]] 就是 RL 在 LLM 对齐中的应用，PPO 是核心算法
- 更长远地看，[[Agent 记忆架构]] 里多智能体协作的行为可以用 RL 来优化——比如 TripleChecker 验证、EvidenceFirst 推理、Graph Fusion 融合这三个 Agent 可以组成一个协作系统，用 RL 来学习它们之间的最优协作策略
- 面试时如果被问到 RLHF，能讲清楚 PPO 的基本原理会很加分——大多数人只知道 RLHF 这个名词，不知道背后的 RL 框架

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[人类反馈强化学习 RLHF]]
- [[Agent 记忆架构]]
- [[多智能体系统 Multi-Agent Systems]]
- [[TripleChecker]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-04: 首次建页
