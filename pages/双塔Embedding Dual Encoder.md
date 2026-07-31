---
摘要: 双塔架构用两个独立编码器把输入映射到共享嵌入空间，是稠密检索与语义匹配的基础范式
来源: https://arxiv.org/abs/1908.10084 (Sentence-BERT, Reimers & Gurevych 2019); https://arxiv.org/abs/2004.04906 (DPR, Karpukhin et al. 2020); Bromley et al. 1993 (原始Siamese网络)
信度: 高
首次记录: 2026-07-31
tags: [基础, RAG]
---

# 双塔Embedding Dual Encoder

## 核心内容

双塔Embedding（Dual Encoder / Siamese Network / Two-Tower Model）是一种**对称编码架构**：用两个结构相同的编码器分别把两路输入（query 和 document、句子A和句子B、图像和文本等）映射到同一个共享的稠密向量空间，再通过余弦相似度或点积计算匹配分数。它解决了跨编码器（cross-encoder）无法离线预计算、检索速度慢的问题——候选文档的嵌入可以一次性算好存进向量库，在线只需要编码 query 后做 ANN 近邻检索，延迟从 O(N) 降到 O(log N)。

**架构演进脉络**：
- **1993 原始 Siamese 网络**（Bromley et al.）：用于签名验证，首次提出"两个共享权重的子网络 + 距离度量"的结构。
- **2019 Sentence-BERT**（Reimers & Gurevych, EMNLP 2019）：把 BERT 改造成双塔，加 mean pooling 产出句向量，解决了 vanilla BERT 做语义相似度需要 O(N²) 交叉编码的瓶颈（1万句子从 65 小时降到 5 秒）。
- **2020 DPR**（Karpukhin et al.）：开放域 QA 场景的双编码器，query 和 passage 各用一个独立 BERT（权重不共享），点积打分，用 in-batch negatives 训练，首次证明稠密检索可以超越 BM25。
- **工业界代表**：Facebook DPR、Google Twin-BERT、微软 MT-DNN、开源的 BGE / E5 / GTE / Jina-Embeddings 系列均为双塔架构。

**核心机制**：

给定 query 编码器 $E_q$ 和 document 编码器 $E_d$（权重可共享或独立），相似度为：
$$
s(q, d) = \operatorname{sim}(E_q(q), E_d(d)) = \frac{E_q(q) \cdot E_d(d)}{\lVert E_q(q)\rVert \, \lVert E_d(d)\rVert}
$$
或直接用点积 $E_q(q)^\top E_d(d)$。训练目标通常是 [[对比学习 Contrastive Learning]] 的 InfoNCE 损失：
$$
\mathcal{L} = -\log \frac{\exp(s(q, d^+)/\tau)}{\exp(s(q, d^+)/\tau) + \sum_{j=1}^{B-1} \exp(s(q, d_j^-)/\tau)}
$$
其中 $d^+$ 为正样本，同 batch 内其他 B-1 个 document 为 in-batch negatives，$\tau$ 为温度参数。

**关键工程要点**：
- **权重共享 vs 独立**：对称任务（同义句判断）通常共享权重；非对称任务（query→doc、图文检索）通常使用两个独立编码器（DPR 风格），容量分配也可以不同。
- **池化策略**：CLS 向量、mean pooling、max pooling，Sentence-BERT 实验表明 mean pooling 最稳。
- **负样本质量决定上限**：in-batch negatives 简单高效但偏易；ANCE / RocketQA 提出异步硬负挖掘，用当前模型检索 top-rank 错误样本作负样本，显著提升召回。
- **向量归一化**：训练时 L2 归一化 + 余弦相似度，能让嵌入空间更均匀，与 FAISS 内积检索兼容。
- **与 [[交叉编码器 Cross-Encoder]] 的取舍**：双塔快但表达力弱（query 和 doc 之间无交叉注意力，无法捕捉细粒度交互词）；cross-encoder 慢但准。工业界通常"双塔粗排召回 + cross-encoder 精排重排"。

**局限与误区**：
- **词汇不匹配问题**：双塔把整段文本压缩成单个向量，丢失了词级信号，对"精确关键词命中但语义不相关"的负样本区分度不如 BM25——这也是为什么 [[混合检索 Hybrid Retrieval]] 必须保留稀疏通路。
- **域偏移敏感**：在通用语料上训好的 embedding 模型迁移到垂直领域（医疗/法律/代码）时召回率骤降，需要领域微调。
- **维度与索引的权衡**：维度越高表达力越强，但存储和检索成本线性增加；常用 768（BERT-base）或 1024（BERT-large）。

## 和我的项目的关系

- **[[EvidenceFirst]]**：检索前端的核心。系统用的 BGE / E5 等嵌入模型本质都是双塔，query 侧在线编码、passage 侧离线建库，FAISS 做 ANN 检索。硬负挖掘和 InfoNCE 微调是领域适配的标准路径。
- **[[CoMaGRAG]]**：实体链接和提及-实体匹配的候选召回阶段也是双塔范式——mention encoder 和 entity encoder 各自编码，向量近邻搜索生成候选集，再交给 [[交叉编码器 Cross-Encoder]] 或 GNN 精排。
- **[[TripleChecker]]**：三元组置信度评估时，如果要做事实声明到 KG 三元组的语义对齐，双塔 embedding 可以作为粗召回通路，缩小需要精判的候选范围。

## 交叉引用

- [[交叉编码器 Cross-Encoder]]
- [[对比学习 Contrastive Learning]]
- [[词嵌入 Word Embedding]]
- [[信息检索 IR基础模型 Information Retrieval]]
- [[混合检索 Hybrid Retrieval]]
- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[检索增强生成 RAG-GraphRAG]]
- [[K近邻 KNN K-Nearest Neighbors]]
- [[EvidenceFirst]]
- [[CoMaGRAG]]
- [[TripleChecker]]

## 更新记录

- 2026-07-31: 首次建页
