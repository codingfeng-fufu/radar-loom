---
摘要: 缩放律以幂律刻画 LLM loss 随参数、数据、算力的下降规律。
来源: https://arxiv.org/abs/2001.08361
信度: 中
首次记录: 2026-07-13
tags: [LLM机制, 基础]
---

# Scaling Law 大模型缩放律

## 核心内容

Scaling Law(缩放律)刻画的是:在数据充分、架构合理的前提下,语言模型的测试交叉熵 loss 随参数量 $N$、数据量 $D$、训练算力 $C$ 呈**幂律下降**,即 $L(N)\approx (N_c/N)^{\alpha_N}$、$L(D)\approx (D_c/D)^{\alpha_D}$、$L(C)\approx (C_c/C)^{\alpha_C}$,且三条曲线之间存在稳定的联合关系。它把"大模型行不行"这个玄学问题变成了可外推的工程曲线:给定预算就能预测 loss、也能预测在什么规模上值得投入更多算力。

**两条主线的差异**:Kaplan 2020(OpenAI 原文)拟合出 loss 主要由 $N$ 主导,建议给定算力预算时"参数量优先、数据够用就行"—— GPT-3 175B 就是这个哲学下的产物。**Chinchilla 2022**(DeepMind)用更大的扫参范围重新拟合,得出计算最优的正确配比是**参数与数据大致按 1:20 同步放大**(即 70B 模型应配 1.4T tokens),推翻了 Kaplan 的"重参数轻数据"结论,直接催生了 LLaMA、DeepSeek 等"小参数大数据"训练范式的转向。

**关键区别于 [[涌现能力 Emergent Abilities]]**:缩放律描述的是 loss 的**连续、平滑、可预测**下降;涌现描述的是下游任务准确率在某个规模阈值后**离散、跳跃**的能力出现。同一份训练曲线,前者看 loss 曲线,后者看具体 benchmark 得分,两者互不替代。近年也有工作(Schaeffer 2023)质疑涌现只是指标选择造成的假象,如果换成平滑指标,涌现会退化回一条缩放律。

## 曲线可视化

**图 1 · 三条幂律曲线(log-log 坐标下呈直线)**

<figure>
<img src="pages/_images/scaling-law/curve1-three-power-laws.svg" alt="L(N)、L(D)、L(C) 三条幂律曲线在 log-log 坐标下的对比" style="width:100%;max-width:720px;">
<figcaption style="color:#898781;font-size:12px;margin-top:4px">
幂律 $L=(x_c/x)^\alpha$ 在 log-log 图上是直线,斜率 $=-\alpha$。三条线斜率不同:$\alpha_D > \alpha_N > \alpha_C$,意味着等比例扩大时,数据的边际贡献最陡、算力最平缓。任何弯折都说明模型已跌出该维度的幂律区间。
</figcaption>
</figure>

**图 2 · Kaplan vs Chinchilla:固定算力下的最优参数量**

<figure>
<img src="pages/_images/scaling-law/curve2-kaplan-vs-chinchilla.svg" alt="Kaplan 2020 与 Chinchilla 2022 在固定算力下推荐的最优参数量对比" style="width:100%;max-width:720px;">
<figcaption style="color:#898781;font-size:12px;margin-top:4px">
同一算力预算 C 下两派给出的最优 N。虚线段落展示 GPT-3 与 Chinchilla-optimal 在同算力下的差距——Chinchilla 拟合表明 GPT-3 在给定算力上**参数过大、数据不足**,这正是 LLaMA 系列反过来"小参数大数据"的直接动因。
</figcaption>
</figure>

> 互动版(含 hover 十字线、tooltip、深色模式):`reports/2026-07-13_scaling-law-curves.html`

## 和我的项目的关系

缩放律对我目前的方向主要是**框定预算和选型**的工具,而非直接建模对象:

- [[TripleChecker]] / KG 抽取管线:缩放律告诉我在 KG 抽取任务上,7B → 70B 的收益是可预测的幂律下降而非线性,给定 GPU 预算可以先算好 loss 差,再决定是否值得上更大的 backbone。Chinchilla 配比也提示我在做领域微调时,不能只堆参数不喂数据。
- [[EvidenceFirst]] / 可信度评测:缩放律本身**不改善事实性和可信度**——loss 降低不等于幻觉减少,这也是为什么需要 RAG、模型校准等外挂机制。这一点在面试时可以作为"为什么光靠 scaling 解决不了 hallucination"的标准回答。
- 与 [[涌现能力 Emergent Abilities]] 的辩证:缩放律给了可预测性,涌现给了不可预测性,项目设计上要两边都留手——评测指标既要看 loss 类的平滑量,也要看下游任务的阈值行为。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[涌现能力 Emergent Abilities]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[语言模型困惑度 Perplexity]]
- [[TripleChecker]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-13: 首次建页
