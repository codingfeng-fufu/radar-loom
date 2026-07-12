---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制]
---

# 层归一化 LayerNorm BatchNorm

## 核心内容

BatchNorm对每个mini-batch里的同一个特征维度做归一化（均值为0，方差为1），作用是稳定训练过程，减少梯度消失或爆炸，是CNN训练的标配。但它对batch size很敏感，而且在序列长度可变的NLP任务里不好用。LayerNorm对单个样本的所有特征维度做归一化，不依赖batch size，非常适合Transformer和NLP任务。BN在CV里是标准，LN在NLP里是标准。两者的核心作用都是让训练更稳定，但适用场景完全不同——BN看群体（batch内所有样本的同一特征），LN看个体（单个样本的所有特征）。

## 和我的项目的关系

LayerNorm本身和我的研究没有直接关系，但它的设计理念——「在不确定性中找确定性的锚点」——和我的工作有深层的共鸣。LayerNorm把每层的激活分布固定住，让训练过程从随机游走变成有约束的优化；[[EvidenceFirst]]把每个样本的推理状态固定成5种离散状态，让RAG系统从「输出一个字符串然后祈祷它是对的」变成「输出一个字符串同时告诉你它有多大概率是对的」。两者都是在不确定性系统里引入确定性的约束——一个在神经网络内部，一个在系统架构层面。这个类比能展示我的思考深度。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[Transformer 自注意力机制]]
- [[确定性状态机 Deterministic State Machine]]

## 更新记录

- 2026-07-04: 首次建页
