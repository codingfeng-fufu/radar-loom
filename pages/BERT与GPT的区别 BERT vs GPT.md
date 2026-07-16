---
摘要: BERT 和 GPT 是 Transformer 架构的两个代表性分支,核心区别在于注意力方向和预训练任务。
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制, 基础]
---

# BERT与GPT的区别 BERT vs GPT

## 核心内容

BERT(Devlin et al., NAACL 2019)和 GPT(Radford et al., 2018)都从 2017 年的原始 [[Transformer 自注意力机制]] 派生,但选择了两条相反的技术路线,并因此各自定义了一整个模型家族与使用范式:

- **BERT = encoder-only + 双向自注意力 + Masked Language Modeling(MLM)**,擅长"读懂一段文本"——分类、抽取、句对推断、检索排序。
- **GPT = decoder-only + 因果(单向)自注意力 + 自回归语言建模(Causal LM)**,擅长"续写一段文本"——生成、对话、代码、任意可以套进"prompt→completion"的任务。

到 2020 年前后,GPT 路线通过 in-context learning、指令微调与 RLHF 逐步吞并了大多数任务(包括原本 BERT 擅长的分类/抽取),现代主流 LLM(GPT-4、Claude、LLaMA、Qwen、DeepSeek)几乎全部是 decoder-only 架构;但 BERT 家族并未消失——它在**编码器需求**(检索器、重排器、句向量、判别式分类)场景仍是最主流的选择。

### 架构层面的差异

两者共用 Transformer block(多头自注意力 + FFN + 残差 + 归一化),差异集中在**注意力掩码**和**输入组织**两处。

**注意力掩码**:设序列长度为 $n$,注意力矩阵 $A \in \mathbb{R}^{n\times n}$ 的每一位 $A_{ij}$ 表示 token $i$ 关注 token $j$ 的权重。

- **BERT 双向注意力**:$A_{ij}$ 对所有 $i, j$ 都可能非零,即每个 token 都能看到整段输入的左右上下文。适合"理解",不适合从左到右生成——如果直接让 BERT 生成,前面的 token 已经看过后面的答案,训练与推理会漏答案。
- **GPT 因果注意力**:$A_{ij} = 0 \text{ 若 } j > i$,即 token $i$ 只能关注位置 $\leq i$ 的历史。数学上等价于给注意力分数加上下三角掩码

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}} + M\right)V, \quad M_{ij} = \begin{cases} 0 & j \leq i \\ -\infty & j > i \end{cases}
$$

这使得 GPT 天然可以做自回归生成:训练时并行学 $p(x_t \mid x_{<t})$,推理时按位置从左到右采样。

**输入组织**:

- BERT 的输入总是以特殊 token `[CLS]` 起头、句子间用 `[SEP]` 分割;`[CLS]` 位置在预训练与下游任务里承担"整句表示"的角色。
- GPT 输入是纯 token 流,没有 `[CLS]`/`[SEP]` 概念;任务信息完全用**自然语言 prompt**注入,如 `翻译:...` 或 few-shot 示例。

**规模档位对比**(原始论文):

| 模型 | 层数 | 隐藏维度 | 头数 | 参数量 |
|------|------|---------|------|--------|
| BERT-base | 12 | 768 | 12 | ~110M |
| BERT-large | 24 | 1024 | 16 | ~340M |
| GPT-1 | 12 | 768 | 12 | ~117M |
| GPT-2 XL | 48 | 1600 | 25 | ~1.5B |
| GPT-3 | 96 | 12288 | 96 | ~175B |
| GPT-4 / Claude / LLaMA-405B | 不公开或数百层 | 数千至上万 | 数十至上百 | 数百 B 至万亿级 MoE |

### 预训练目标的差异

预训练目标是两条路线更本质的分歧,直接决定了模型学到的表示形态。

**BERT · Masked Language Modeling(MLM)**:随机遮盖输入 15% 的 token,让模型根据双向上下文预测被遮盖处的原 token。为了缓解预训练与微调之间"输入分布不一致"(下游任务里没有 `[MASK]` token),Devlin et al. 采用 80/10/10 策略——被选中的 15% token 里 80% 替换为 `[MASK]`、10% 随机替换、10% 保持不变。MLM 的目标函数为

$$
\mathcal{L}_{\text{MLM}} = -\mathbb{E}_{x \sim \mathcal{D}}\left[\sum_{i \in \mathcal{M}} \log p_\theta(x_i \mid x_{\setminus \mathcal{M}})\right]
$$

其中 $\mathcal{M}$ 是被遮盖位置的集合。BERT 原论文还附带了 **Next Sentence Prediction(NSP)**——判断句 B 是否为句 A 的下一句;后续 RoBERTa(Liu et al. 2019)证明去掉 NSP 反而更好,现在几乎无人使用。

**GPT · Causal / Autoregressive Language Modeling**:标准的左到右语言建模,目标函数

$$
\mathcal{L}_{\text{CLM}} = -\mathbb{E}_{x \sim \mathcal{D}}\left[\sum_{t=1}^{n} \log p_\theta(x_t \mid x_{<t})\right]
$$

两个目标函数的关键差别:

- **信息效率**:MLM 每个样本只在 15% 位置上产生梯度;CLM 每个位置都产生梯度,数据利用率更高。这是 ELECTRA(Clark et al. 2020,提出 Replaced Token Detection 让所有 token 都产生信号)与 T5 span corruption 试图弥补的问题。
- **表示形态**:MLM 学到的是**上下文条件下的 token 分布**,是判别式底座;CLM 学到的是**联合分布的自回归分解**,天然支持采样生成。
- **零样本能力**:Wang et al.(NeurIPS 2022,"What Language Model Architecture and Pretraining Objective Work Best for Zero-Shot Generalization?")系统比较了 encoder-only、decoder-only、encoder-decoder ×(MLM、CLM、span corruption)的九个组合,结论是 **decoder-only + causal LM** 在零样本任务上综合最优,这为 GPT 路线的最终胜出提供了实证依据。

### 使用范式的差异

**BERT 路线:预训练 + 任务特定 fine-tuning**。下游任务通常在 BERT 顶上加一个轻量分类头/回归头,再用**任务的标注数据**做监督微调。典型模式:

- 句子分类:取 `[CLS]` 隐状态过 MLP;
- 序列标注(NER):每个位置隐状态过 MLP;
- 句对任务(NLI、语义相似度):`[CLS]` 隐状态过 MLP;
- 抽取式 QA:预测答案起止位置。

每个任务一个专门微调好的 checkpoint,任务之间不共享参数。

**GPT 路线:预训练 + prompt / in-context learning + 指令微调 + RLHF**。GPT-3 的核心发现(Brown et al. 2020)是**任务统一**:只要把任务包装成"prompt → completion"的自然语言形式,一个模型就能处理翻译、QA、摘要、代码、推理等任意任务,零样本或少样本即可,无需为每个任务准备标注数据和单独训练。这条路线随后叠加两层加工:

- **指令微调(instruction tuning)**:用多任务指令-回答数据继续微调,让模型学会"听懂"指令(FLAN、T0、InstructGPT);
- **RLHF / DPO 等偏好对齐**:参考 [[人类反馈强化学习 RLHF]] 与 [[后训练 Post-training]]。

结果就是 ChatGPT / Claude / DeepSeek 这类**单一模型处理任意任务**的产品形态。

### 为什么 decoder-only 赢了

到 2024 年,几乎所有开源与商用主流 LLM 都是 decoder-only。原因不是"BERT 不好",而是决策变量本身发生了迁移:

1. **任务统一 vs 任务专用**:每个企业维护几十个 BERT-based 分类器成本高、迭代慢;一个 LLM 加不同 prompt 就能替代,运维摊薄到一处。
2. **规模化的边际收益**:Scaling law 在 CLM 上得到充分验证,加参数与数据几乎稳定改善;MLM 的规模化收益在 300M–1B 参数量以上就明显放缓。参考 [[Scaling Law 大模型缩放律]]。
3. **上下文学习是 CLM 的副产品**:因果目标下,一段 prompt 里的示例天然是"历史 token",模型可以在推理时无需梯度更新完成任务学习——这正是 [[上下文学习 In-context Learning]] 与 [[涌现能力 Emergent Abilities]] 的物质基础。BERT 因为需要 `[MASK]` 位置,不具备这种"prompt 即程序"的形态。
4. **推理服务同构**:所有请求都是"前缀 + 生成",KV cache 复用度高;参考 [[LLM 推理优化 KV Cache Quantization]]。BERT 类模型的判别式推理各任务形状不同,难以在同一套推理引擎里高吞吐服务。
5. **中间路线(encoder-decoder)也在收缩**:T5(Raffel et al. 2020)、BART(Lewis et al. 2020)、FLAN-T5 曾在翻译、摘要上占优,但 decoder-only 在同等算力下追平并超过,现在仅在需要严格"输入→输出"结构且训练数据充足的封闭领域(如某些企业级翻译、结构化 SQL 生成)仍有优势。

### BERT 仍然占优的场景

到 2026 年,BERT 家族并未消亡,而是收缩到几个"判别式底座刚需"的岗位:

- **稠密向量检索器与句向量模型**:Sentence-BERT、BGE、E5、Jina-Embeddings 等主流开源 embedding 模型均为 BERT 派生,双塔架构比 decoder-only 更适合把整句压缩成单个向量;参考 [[信息检索 IR基础模型 Information Retrieval]] 与 [[混合检索 Hybrid Retrieval]]。
- **重排(reranker)与交叉编码器**:cross-encoder 需要一次前向读完 query+doc,BERT 天生对齐这个用例,BGE-reranker、mxbai-rerank 均为 BERT 型。
- **NER、词性、依存等序列标注**:参考 [[命名实体识别 NER]]、[[词性标注 POS Tagging]],成熟 pipeline(spaCy transformers、HuggingFace token-classification)仍以 BERT/RoBERTa/DeBERTa 为主。
- **NLI 判别与 fact-checking**:参考 [[文本蕴含与自然语言推理 NLI]],DeBERTa-v3-large-mnli 之类的模型至今是零样本文本分类与三元组一致性检查的常用工具。
- **端侧与低延迟场景**:BERT-base / DistilBERT / MobileBERT 可以量化到 100–200MB、单核毫秒级推理,LLM 达不到这一档位。

BERT 家族的持续演进代表作:**RoBERTa**(更大批次 + 去 NSP + 更多数据)、**ALBERT**(参数共享)、**DeBERTa / DeBERTa-v3**(解耦位置注意力 + ELECTRA 式训练,截至 2024 年在 GLUE/SuperGLUE 上依然强势)、**ELECTRA**(replaced token detection,样本效率高)、**DistilBERT / TinyBERT**(蒸馏压缩)。

### 常见误区

- **"BERT 已经过时"** — 上一节列出的 embedding、rerank、NLI、NER 等场景 BERT 仍是主力;混淆"生产型 LLM 是 decoder-only"与"所有语言模型都是 decoder-only"是常见错觉。
- **"MLM 和 CLM 只是掩码方向不同"** — 数学上确实只差一个掩码矩阵,但在**表示学习、数据效率、推理形态、下游范式**四个维度上全线不同,不可互换。
- **"GPT 用 prompt 就不需要微调"** — GPT 路线只是把**每任务微调**换成了**一次性指令微调 + 少量 RLHF + prompt**;真正"零训练"的只有推理阶段,预训练与后训练的算力开销更大。
- **"BERT 不能生成"** — BERT 可通过迭代式 MLM 或 Gibbs 采样生成,但质量与效率远逊于 GPT,工程上没人这么做。
- **"encoder-decoder(T5)是折中方案"** — 早期确实如此,但 UL2(Tay et al. 2022)证明用"混合去噪目标 + decoder-only"就能拿到 encoder-decoder 的收益,现在 encoder-decoder 更多是历史选择而非当前推荐。

## 和我的项目的关系

我的项目都基于 GPT 路线的大模型,但 BERT 家族在几个组件里仍是首选:

- **[[TripleChecker]] 的三元组验证**:NLI 判别是天然的 BERT 用例。用 DeBERTa-v3-large-mnli 之类的现成模型判断"证据是否蕴含 claim",比让 LLM 每次读全文再回答"是/否"便宜一个数量级,且判别式模型输出的概率可以直接用作置信度分数,参考 [[置信度评分 Confidence Scoring]]。
- **[[EvidenceFirst]] 的检索层**:句向量与 reranker 建议全部走 BGE / E5 之类的 BERT 派生模型;把 LLM 只留在最后的"读证据、组答案"环节,是成本-性能最优的分工。
- **[[CoMaGRAG]] 的实体消歧与提及-实体链接**:参考 [[实体消歧 Entity Disambiguation]],主流方案(BLINK、GENRE 之外的判别式版本)仍以 BERT encoder + 双塔或 cross-encoder 为主。
- **KG 抽取质量检测的启发**:BERT 的 MLM 思路可以借鉴到 KG 三元组验证——随机遮盖三元组的头/关系/尾,让 KG-BERT 类模型预测遮盖位置,和抽取结果对比可发现潜在幻觉,是 [[TripleChecker]] 的一条可探索技术支线。
- **面试话术层面**:遇到"为什么现在都是 decoder-only"这类问题,可以从"任务统一 × scaling law × in-context learning × 推理服务同构"四点切入,避免只答"GPT 效果好"这种表面回答。

## 交叉引用

- [[Transformer 自注意力机制]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[上下文学习 In-context Learning]]
- [[涌现能力 Emergent Abilities]]
- [[后训练 Post-training]]
- [[人类反馈强化学习 RLHF]]
- [[Scaling Law 大模型缩放律]]
- [[LLM 推理优化 KV Cache Quantization]]
- [[文本蕴含与自然语言推理 NLI]]
- [[信息检索 IR基础模型 Information Retrieval]]
- [[混合检索 Hybrid Retrieval]]
- [[命名实体识别 NER]]
- [[实体消歧 Entity Disambiguation]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[TripleChecker]]

## 更新记录

- 2026-07-04: 首次建页
- 2026-07-16: 扩写正文,补齐架构层面差异(注意力掩码公式、规模档位对比)、MLM/CLM 目标函数与信息效率对比、使用范式(fine-tuning vs prompt/ICL/RLHF)、decoder-only 胜出的五点原因、BERT 仍占优的判别式场景、五条常见误区,以及与 TripleChecker/EvidenceFirst/CoMaGRAG 的分工建议。
