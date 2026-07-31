---
摘要: Cross-encoder拼接query和doc输入同一编码器，用交叉注意力做精排重排
来源: https://arxiv.org/abs/1901.04085 (Nogueira & Cho 2019, Passage Re-ranking with BERT); Xiao et al. 2023, C-Pack/BGE-Reranker; Hogun et al. 2023, mxbai-rerank
信度: 高
首次记录: 2026-07-31
tags: [基础, RAG]
---

# 交叉编码器 Cross-Encoder

## 核心内容

交叉编码器（Cross-Encoder / Reranker）是一种**单塔交互架构**：把 query 和 document 拼接成一个序列 `<[BOS_never_used_51bce0c785ca2f68081bfa7d91973934]> query [SEP] passage [SEP]` 喂给同一个 Transformer 编码器，让两部分 token 在每一层都通过自注意力（self-attention 在这里实质是 cross-attention）进行双向交互，最终取 `<[BOS_never_used_51bce0c785ca2f68081bfa7d91973934]>` 位置的输出向量经线性层映射为一个相关性标量分数。它解决了双塔编码器（dual encoder）无法捕捉细粒度词级交互的问题——query 中的每个词都能直接 attend 到 document 的每个词，显著提升排序精度，但代价是无法离线预计算 document 向量，必须对每个 (query, doc) 对做一次完整的前向推理。

**架构演进脉络**：
- **2019 monoBERT**（Nogueira & Cho, arXiv:1901.04085）：开创"用 BERT 做段落重排"的范式。在 MS MARCO  passage ranking 任务上首次证明，把 BERT 当成交互式打分器效果远超 BM25 和当时的双塔；后续 duoBERT 版本还引入了两两 pair-wise 判别。
- **2021 monoT5**（Nogueira et al.）：把 reranker 换成 encoder-decoder（T5），生成"true"/"false" token 的概率作为相关性分数，效果进一步提升但推理更慢。
- **2023 BGE-Reranker**（Xiao et al., BAAI C-Pack）：开源中文/英文双语 reranker，大规模硬负训练 + 蒸馏，成为当前最常用的开源 reranker 基线。
- **2023 mxbai-rerank**（mixedbread.ai）：基于 DeBERTa 的多语言 reranker，在多项 benchmark 上达到 SOTA。
- **2023+ LLM reranker**：RankLLaMA、RankGPT、RankVicuna 等工作把 LLaMA/GPT 系 decoder-only 模型用作 reranker，通过 pointwise/pairwise/listwise prompting 或专门微调进行排序；效果上限高但推理成本比 BERT 类 reranker 高出一个数量级。

**核心机制**：

给定候选 $(q, d)$，相关性分数为：
$$
s(q, d) = w^\top \mathrm{BERT}_{\mathrm{CLS}}\big([\mathrm{CLS}]\; q\; [\mathrm{SEP}]\; d\; [\mathrm{SEP}]\big) \in \mathbb{R}
$$

**训练目标三类**：
- **Pointwise**：把 $(q, d^+)$ 标为正、$(q, d^-)$ 标为负，用二元交叉熵损失：
  $$\mathcal{L}_{\mathrm{point}} = -y \log \sigma(s(q,d)) - (1-y)\log(1-\sigma(s(q,d)))$$
  简单稳定，但忽略候选之间的相对顺序。
- **Pairwise（Margin / Hinge Rank Loss）**：同一 query 的正样本分数必须高于负样本：
  $$\mathcal{L}_{\mathrm{pair}} = \max(0, \epsilon - s(q,d^+) + s(q,d^-))$$
  monoBERT 最初用的是 pointwise，但实践表明 pairwise + hard negative 在排序任务上更优。
- **Listwise（ListNet / LambdaLoss）**：直接优化整个候选列表的排序（如 softmax over top-k），与 NDCG/MRR 等检索指标更对齐；训练实现更复杂但理论上限最高。

**关键工程要点**：
- **不能用于首阶段召回**：每对 (q, d) 都需单独前向，对百万级语料库直接重排不可行；标准流水线是"BM25/双塔召回 top-k（k=50~200）→ cross-encoder 重排取 top-n（n=3~10）"。
- **蒸馏是关键**：大 reranker（monoT5-3B、LLaMA-7B）的分数可以蒸馏到小 BERT-base reranker；BGE-reranker 用 LLM 打分做软标签蒸馏，在小模型上保留了大模型 90%+ 的效果。
- **输入长度是瓶颈**：BERT-base 截断到 512 token，长文档需要分段（MaxP / FirstP / Slide-window）再聚合分数；长上下文 reranker（基于 Longformer/Llama-3-8B）缓解这一问题但推理慢。
- **温度校准**：cross-encoder 输出的原始分数不直接是概率，生产环境常用温度缩放或 Platatt scaling 做校准，便于下游阈值决策。
- **Late interaction（ColBERT 范式）**：介于双塔和 cross-encoder 之间的折中——document 端离线编码所有 token embedding，query 端在线编码后通过 MaxSim 算子做细粒度匹配，既保留了词级交互，又能做 ANN 检索。本质是"token 级双塔"。

**与双塔的取舍对比**：
| 维度 | 双塔 Dual Encoder | 交叉编码器 Cross-Encoder |
|------|-------------------|--------------------------|
| 编码方式 | 两路独立编码 | 拼接后单次编码 |
| 离线预计算 | 可以，doc 向量可存库 | 不能，每对独立推理 |
| 推理速度 | 极快（ANN O(log N)） | 慢（O(K) 次前向） |
| 词级交互 | 无（压缩到单向量） | 完整（全层 cross-attention） |
| 适合阶段 | 首阶段召回（top-K 从百万到百） | 末阶段重排（top-K 从百到十） |
| 精度上限 | 较低 | 显著更高 |
| 代表模型 | BGE-embedding, E5, DPR, SBERT | BGE-reranker, monoBERT, mxbai-rerank, RankLLaMA |

**局限与误区**：
- **延迟高，不适合实时大批量**：cross-encoder 的延迟随候选数线性增长，生产中必须严格限制 top-k 数量；对延迟敏感的系统通常用小模型（6 层 distilled BERT）或 GPU 批处理。
- **对输入扰动更敏感**：由于能看到 query 和 doc 的交互，对抗性词注入（把无关 doc 中插入 query 关键词）更容易骗过 cross-encoder 而非双塔——需要配合训练时的数据增强。
- **"重排一定更好"是误区**：当召回结果本身质量极差时，cross-encoder 的收益有限；提升上限首先要扩大召回池的覆盖。
- **LLM reranker ≠ 通用替代**：用 GPT-4 做 reranker 效果好但成本极高，且在简单场景相对 BERT reranker 的边际收益很小，只在对精度极度敏感且有预算时采用。

## 和我的项目的关系

- **[[EvidenceFirst]]**：检索流水线的标准末段。召回阶段用 BGE embedding + BM25 混合检索拉 top-100，再用 BGE-reranker 重排取 top-5~10 送给 LLM，在几乎不增加延迟的情况下把答案质量提升一个台阶。置信度状态检查（state determination）可以直接利用 reranker 分数：高置信度直通，低置信度进入人工审计队列。
- **[[CoMaGRAG]]**：候选实体粗召回（双塔/BLINK bi-encoder）之后，用 cross-encoder 做 mention-entity 精排；对 KG 多跳路径的每条候选路径也可以用 cross-encoder 打分判断路径相关性。
- **[[TripleChecker]]**：三元组可信度细粒度判别时，把"声明文本"与"三元组证据"拼成 pair 送入 cross-encoder，比单纯嵌入相似度能更好识别细粒度事实冲突（如属性值不一致、关系类型错配）。

## 交叉引用

- [[双塔Embedding Dual Encoder]]
- [[对比学习 Contrastive Learning]]
- [[信息检索 IR基础模型 Information Retrieval]]
- [[混合检索 Hybrid Retrieval]]
- [[BERT与GPT的区别 BERT vs GPT]]
- [[RAG 评测指标 EM Recall MRR]]
- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[检索增强生成 RAG-GraphRAG]]
- [[EvidenceFirst]]
- [[CoMaGRAG]]
- [[TripleChecker]]

## 更新记录

- 2026-07-31: 首次建页
