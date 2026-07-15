---
摘要: 归一化把数据或激活的尺度统一到可比较区间,分为数据归一化与网络归一化两大家族,是训练稳定与距离度量有效的前提。
来源: https://scikit-learn.org/stable/modules/preprocessing.html
信度: 高
首次记录: 2026-07-15
tags: [基础, LLM机制]
---

# 归一化 Normalization

## 核心内容

归一化(Normalization)泛指**把数值调整到一个可比较的尺度**。它并不是单一算法,而是一个跨越预处理、优化、深度网络设计的概念族,常见分两大类:

1. **数据/特征归一化**——把训练样本的特征缩放到统一区间或分布,让距离度量、梯度更新、正则项对各特征公平。
2. **网络内部归一化**——在神经网络的前向路径中对激活或权重做归一化,稳定训练、缓解协变量偏移(covariate shift)、允许更大的学习率。

两者数学操作相似(减均值、除标准差之类),但**作用对象、时机、目标完全不同**:一个作用于数据集,一个作用于每个 mini-batch/层的激活;混淆这两层是入门常见误区。

### 数据归一化的主流方法

给定特征列 $\{x_1,\ldots,x_N\}$:

- **Z-score 标准化(Standardization)**:$x'=\frac{x-\mu}{\sigma}$。把每列变成均值 0、方差 1;假设近似高斯,适合 SVM、线性/逻辑回归、PCA、KMeans、[[K近邻 KNN K-Nearest Neighbors]] 等对量纲敏感的算法。
- **Min-Max 缩放**:$x'=\frac{x-x_{\min}}{x_{\max}-x_{\min}}$,把每列压到 $[0,1]$。保留分布形状,但对异常值极敏感——一个离群点会把大多数样本挤到很窄区间。
- **MaxAbs**:$x'=x/\max(|x|)$,不平移只缩放,保留稀疏结构,适合稀疏矩阵(如 TF-IDF)。
- **Robust Scaler**:$x'=\frac{x-\text{median}}{\text{IQR}}$,用中位数与四分位距代替均值方差,对异常值鲁棒。
- **L2 归一化(样本级)**:$x'=x/\lVert x\rVert_2$,把每个样本向量投到单位球面上,使内积等价于余弦相似度。稠密向量检索、[[对比学习 Contrastive Learning]] 的标准前处理。

**关键工程细则**:
- 缩放器**只在训练集上 fit**,再 transform 训练/验证/测试集;否则会造成信息泄漏(data leakage)。
- 稀疏矩阵慎用 Min-Max/Z-score(会破坏 0),优先 MaxAbs 或 L2。
- 树模型(决策树、随机森林、GBDT、XGBoost)**不需要**特征归一化,因为它们只看分裂阈值,尺度无关。

### 网络内部归一化家族

深度网络训练里常用的归一化,以"沿哪个维度算均值和方差"区分。设 4-D 输入 $x\in\mathbb{R}^{N\times C\times H\times W}$($N$ batch,$C$ 通道,$H\times W$ 空间):

- **BatchNorm(Ioffe & Szegedy, 2015)**:沿 $(N,H,W)$ 归一化,每个通道一组统计量。CV/CNN 的标配,依赖较大 batch size,推理时用移动平均的均值方差。
- **LayerNorm(Ba et al., 2016)**:沿 $(C,H,W)$ 或最后一维归一化,对单个样本操作,不依赖 batch。Transformer/NLP 的标配,详见 [[层归一化 LayerNorm BatchNorm]]。
- **InstanceNorm**:沿 $(H,W)$ 归一化,每样本每通道一组。风格迁移常用,去除样本内的整体亮度/风格差异。
- **GroupNorm(Wu & He, 2018)**:把通道分组,组内做 LN。小 batch 时替代 BN 的稳健选择。
- **RMSNorm(Zhang & Sennrich, 2019)**:LN 的简化版,只除以均方根 $\text{RMS}(x)=\sqrt{\frac{1}{d}\sum x_i^2}$,不减均值。LLaMA、T5 等现代 LLM 大量采用,少一次求均值算力更省。

统一表达:

$$
\hat{x}_i = \frac{x_i-\mu}{\sqrt{\sigma^2+\epsilon}},\quad y_i=\gamma\,\hat{x}_i+\beta
$$

$\gamma,\beta$ 是可学习的仿射参数,负责恢复表征能力;$\epsilon$ 数值稳定项。差别只在 $\mu,\sigma^2$ 沿哪些维度求。

**为什么有效**:原论文(BN)提出的解释是"减少内部协变量偏移",但后续研究(Santurkar et al., 2018 *How Does Batch Normalization Help Optimization?*, NeurIPS)通过实验表明真正原因是**平滑了损失面 landscape**,让梯度尺度更均匀,支持更大学习率。这一"机制解释被推翻但方法保留"是深度学习经验主导领域的典型案例。

### 与相关概念的边界

- **归一化 vs 标准化(Standardization)**:中文语境常混用,严格意义上"归一化"=缩到区间(Min-Max);"标准化"=减均值除方差(Z-score)。scikit-learn 的 `Normalizer` 特指样本级 L2 归一化,不是 Z-score。
- **归一化 vs 白化(Whitening)**:白化在归一化基础上再做去相关(PCA whitening、ZCA),使协方差矩阵变为单位阵;归一化不改变特征间相关性。
- **归一化 vs 正则化(Regularization)**:两者概念完全不同——归一化调整数据/激活的尺度,正则化(L1/L2/Dropout/Weight Decay)约束模型复杂度以防过拟合。
- **归一化 vs 权重归一化(WeightNorm, Salimans & Kingma 2016)**:后者归一化的是权重向量的模长而非激活,与本页讨论的激活归一化平行。
- **Softmax 与归一化**:Softmax 把 logits 归一化为概率分布 $\sigma_i=\frac{e^{z_i}}{\sum_j e^{z_j}}$,是"概率归一化"的特例,不属于本页主线。

### 常见陷阱

- **测试集泄漏**:用全量数据 fit 缩放器再切分,或对每个 batch 重新 fit,都会让评估过于乐观。
- **推理时 BN 状态错误**:PyTorch 里忘记 `model.eval()` 会让 BN 使用当前 batch 统计而非训练时移动平均,推理结果不稳定。
- **对已经归一化的数据再归一化**:嵌入模型输出常已 L2 归一化,若下游再做 Z-score 会破坏方向信息。
- **Min-Max 对时间序列的漂移**:训练集统计的 $x_{\min},x_{\max}$ 在生产环境可能被新数据突破,需要重新校准或改用 Robust Scaler。

## 和我的项目的关系

归一化在我的 KG / RAG 主线里处处存在但常被忽视:

- **向量检索前处理**:任何 [[检索增强生成 RAG-GraphRAG]] 系统的嵌入向量都要 L2 归一化,才能让 FAISS/HNSW 的内积检索等价于余弦相似度。[[TripleChecker]] 从嵌入库召回候选三元组时,如果索引和查询使用不同的归一化策略,召回结果会完全错乱。
- **多特征打分融合**:[[混合检索 Hybrid Retrieval]] 里融合 BM25 得分与向量得分需要先把两者放到同一尺度(Min-Max 或 Z-score),否则线性组合无意义。
- **LLM 架构选择**:近年 LLM 从 LayerNorm 转向 RMSNorm 是训练效率的重要优化,与 [[Transformer 自注意力机制]] 的实现细节相关;理解这条演进有助于面试时讲清"为什么 LLaMA 快"。
- **数据审计信号**:[[EvidenceFirst]] 里如果要给不同来源可信度打综合分,不同维度(时效性、引用次数、匹配度)必须先归一化再加权,否则量级大的维度会淹没其他信号。

## 交叉引用

- [[层归一化 LayerNorm BatchNorm]]
- [[K近邻 KNN K-Nearest Neighbors]]
- [[对比学习 Contrastive Learning]]
- [[混合检索 Hybrid Retrieval]]
- [[Transformer 自注意力机制]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-15: 首次建页,系统梳理数据归一化(Z-score/Min-Max/MaxAbs/Robust/L2)与网络归一化家族(BN/LN/IN/GN/RMSNorm),并厘清与标准化/白化/正则化的边界。
