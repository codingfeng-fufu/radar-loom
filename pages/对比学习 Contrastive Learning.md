---
摘要: 对比学习通过拉近正样本对、推开负样本对学习表示,以InfoNCE为核心损失,是稠密检索与多模态对齐的基础范式。
来源: 对话记录 2026-07-13
信度: 高
首次记录: 2026-07-13
tags: [基础]
---

# 对比学习 Contrastive Learning

## 核心内容

对比学习(Contrastive Learning)是一种**自监督表示学习范式**:不依赖人工标签,而是通过"锚点-正样本-负样本"的相对关系学习编码器,让语义相似的样本在嵌入空间靠近、不相似的样本远离。判别式方法直接学"是什么",生成式方法学"怎么生成";对比学习学的是"哪些是一伙的",目标更弱、数据利用更高效。

**核心损失 InfoNCE**:给定锚点 $x$、正样本 $x^+$、一批负样本 $\{x_j^-\}$(通常来自同 batch 其他样本或外挂队列),

$$
\mathcal{L}=-\log\frac{\exp(\operatorname{sim}(x,x^+)/\tau)}{\exp(\operatorname{sim}(x,x^+)/\tau)+\sum_j\exp(\operatorname{sim}(x,x_j^-)/\tau)}
$$

- sim(·,·) 通常是余弦相似度;
- **温度 τ** 是关键超参:τ 小 → 分布尖锐、对"最难负样本"敏感、梯度大但容易训崩;τ 大 → 分布平滑、区分度差。经验值 0.05–0.1。
- InfoNCE 与互信息下界等价(van den Oord 2018),因此对比学习在信息论上有明确解释。

**正样本构造**——这一步决定了学到什么语义:
- **图像**:同一张图的两种数据增强(裁剪+颜色抖动+高斯模糊),代表工作 SimCLR、MoCo。
- **文本**:同一句子过两次不同 dropout(SimCSE)、回译、同义改写、query-passage 对。
- **多模态**:图-文成对(CLIP)、语音-文本成对,天然正样本。
- **图/KG**:同一节点的两种子图视图、同一实体的多语言别名。

**关键工程点**:
- **负样本数量决定上限**:大 batch(SimCLR 用 4k+)或动量队列(MoCo)或跨设备 all-gather 攒负样本。
- **困难负样本挖掘(hard negative mining)**:太简单的负样本梯度贡献几乎为零,稠密检索里 ANCE / RocketQA 就是围绕"怎么高效挖硬负"做文章。
- **[[变分自编码器 VAE Variational Autoencoder]]** 通过 KL 正则约束隐空间形状,对比学习则通过"均匀性 + 对齐性"(Wang & Isola 2020)间接约束——两者是塑造嵌入空间的两条不同路径。

**典型应用**:视觉自监督预训练(SimCLR / MoCo / BYOL 无负样本变体)、句向量(SimCSE)、稠密检索(DPR / ANCE / E5 / BGE)、多模态对齐(CLIP / ALIGN)、KG 嵌入的自监督预训练。

## 和我的项目的关系

对比学习是 RAG 主线的**核心训练范式**,直接影响多个模块:

- **稠密检索器训练**:双塔编码器(query encoder + passage encoder)的标准做法就是 InfoNCE + 硬负样本。做 [[EvidenceFirst]] / [[CoMaGRAG]] 的检索前端时,BGE / E5 / GTE 这类嵌入模型都是对比学习产物;若要在特定领域(法律 / 医疗 / KG 语料)做适配,微调路径基本就是"造 query-passage 正对 + 硬负挖掘 + InfoNCE"。
- **对比 VAE 正则**:上一节说 [[变分自编码器 VAE Variational Autoencoder]] 通过 KL 拉均匀,对比学习通过均匀性损失拉均匀。稠密检索实践中很少走 VAE 路线,几乎全部走对比学习——因为 InfoNCE 直接优化"相似的近、不相似的远",目标与检索评估口径一致。
- **KG 嵌入的自监督预训练**:在做 [[TripleChecker]] 的实体表征时,可以用"同实体不同别名 / 不同语言"作正对,"同类型不同实体"作硬负,给下游三元组打分器一个更好的 warm start。
- **面试串讲**:对比学习是"没有生成、也能学好表示"的代表,与生成式的 VAE / 扩散模型对照讲——判别式(交叉熵)→ 生成式(ELBO)→ 对比式(InfoNCE),这三条路径覆盖了现代表示学习的主要方向。

## 交叉引用

- [[变分自编码器 VAE Variational Autoencoder]]
- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[EvidenceFirst]]
- [[CoMaGRAG]]
- [[TripleChecker]]

## 更新记录

- 2026-07-13: 首次建页
