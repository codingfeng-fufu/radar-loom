---
摘要: 词嵌入把词映射为低维稠密向量,让语义可计算,从Word2Vec到BERT上下文嵌入是NLP表示学习的基石。
来源: https://arxiv.org/abs/1301.3781
信度: 高
首次记录: 2026-07-16
tags: [基础]
---

# 词嵌入 Word Embedding

## 核心内容

**词嵌入(word embedding)**是把词或子词映射到一个低维**稠密实值向量**的表示学习方法,记为 $v_w \in \mathbb{R}^d$($d$ 通常 100–1024)。目标是让**语义或句法相近的词在向量空间中距离近**,从而把"符号级"的语言问题转成"向量级"的几何问题——相似度可用余弦/点积计算,类比关系可用向量加减近似,分类/检索/聚类等下游任务可直接在向量上做。

它要解决的是**符号表示的稀疏与孤立**:传统的 **one-hot** 表示把词汇表 $V$ 里每个词映射到一个 $|V|$ 维的独立单位向量,任意两个不同词的相似度都是 0,同义词与反义词一视同仁,维度爆炸且无法泛化。词嵌入通过**分布式表示(distributed representation,Hinton 1986)**把语义摊到 $d$ 维每一维上,再借助**分布假设**(Harris 1954、Firth 1957:"a word is characterized by the company it keeps")从大规模语料自动学出这些向量。

从演进上看词嵌入历经三代:

1. **计数式(count-based)**:LSA、HAL、共现矩阵 + SVD/PPMI;
2. **静态神经嵌入(static neural embedding)**:Word2Vec、GloVe、FastText——每个词一个固定向量;
3. **上下文嵌入(contextual embedding)**:ELMo、BERT、GPT hidden states——同一个词在不同句子里得到不同向量,是当前主流。

现代 NLP 里,狭义的"词嵌入"通常指前两代;广义上也涵盖上下文嵌入与句/段/文档嵌入。sentence-embedding、dense retrieval、multilingual embedding 等下游方向都是它的延伸。

### 分布假设与计数式嵌入

**分布假设**是所有词嵌入方法的理论前提:词的语义由它出现的上下文分布决定。

最朴素的实现是**共现矩阵**:对语料统计 $M \in \mathbb{R}^{|V|\times|V|}$,$M_{ij}$ 表示词 $i$ 与词 $j$ 在窗口大小 $k$ 内共现的次数。直接把 $M$ 的每一行当作词的表示可行但维度太高;实际会做两步优化:

- **权重变换**:用 **PMI(点互信息)** 或 PPMI(截断到正值)代替原始计数,$\text{PMI}(i,j) = \log \frac{p(i,j)}{p(i)p(j)}$。它抑制高频停用词的主导作用,突出统计上"显著相关"的共现。
- **降维**:对(P)PMI 矩阵做截断 SVD,$M \approx U \Sigma V^\top$,取 $U \Sigma^{1/2}$ 的前 $d$ 列作为词向量。这就是 **LSA / LSI**(Deerwester et al. 1990)的核心。

Levy & Goldberg(NIPS 2014)证明 **Skip-gram + Negative Sampling 隐式在做 shifted PPMI 矩阵分解**,把神经方法与计数方法在数学上打通了。所以两条路线不是"神经派 vs 统计派",而是同一目标的不同实现。

### 静态神经嵌入:Word2Vec / GloVe / FastText

**Word2Vec**(Mikolov et al. 2013a, 2013b)是引爆词嵌入方向的代表工作,提出两种目标:

- **CBOW(Continuous Bag-of-Words)**:用上下文窗口 $c$ 内的词预测中心词 $w_t$。
- **Skip-gram**:反过来,用中心词 $w_t$ 预测窗口内每个上下文词 $w_{t+j}$。目标函数

$$
\mathcal{L}_{\text{SG}} = -\frac{1}{T}\sum_{t=1}^{T}\sum_{-c \leq j \leq c,\, j \neq 0} \log p(w_{t+j}\mid w_t)
$$

原始 softmax $p(w_O\mid w_I) = \frac{\exp(v_{w_O}^\top v_{w_I})}{\sum_{w \in V}\exp(v_w^\top v_{w_I})}$ 分母对整个词表求和,训练不可行。Word2Vec 用两种加速:

- **Hierarchical Softmax**:把 softmax 换成沿 Huffman 树的一串二分类,复杂度从 $O(\lvert V\rvert)$ 降到 $O(\log \lvert V\rvert)$。
- **Negative Sampling**:每个正样本 $(w_I, w_O)$ 只采 $k$ 个负样本 $w_n$(通常 $k=5$–20),优化

$$
\log \sigma(v_{w_O}^\top v_{w_I}) + \sum_{n=1}^{k}\mathbb{E}_{w_n \sim P_n(w)}\left[\log \sigma(-v_{w_n}^\top v_{w_I})\right]
$$

负样本分布 $P_n(w) \propto U(w)^{3/4}$($U$ 是 unigram 频率),$3/4$ 幂做了经验平滑,可以让稀有词也被合理抽到。

**GloVe**(Pennington et al. EMNLP 2014)从共现矩阵出发拟合

$$
\mathcal{L}_{\text{GloVe}} = \sum_{i,j} f(X_{ij})\left(v_i^\top \tilde{v}_j + b_i + \tilde{b}_j - \log X_{ij}\right)^2
$$

其中 $X_{ij}$ 是 $i,j$ 的共现次数,$f$ 是抑制高频对的权重函数。它把计数法和局部窗口预测法揉在了一起。

**FastText**(Bojanowski et al. TACL 2017)把词拆成字符 n-gram,词向量是其所有 n-gram 向量之和。这样**未登录词(OOV)** 也能拼出向量,对形态丰富的语言(德语、俄语、土耳其语)和拼写变体特别友好。

这三个模型都属于"静态嵌入":训练完成后,每个词得到**一个固定向量**,无论出现在什么句子里都不变。经典产物如 GoogleNews-vectors-300、GloVe-6B/840B、FastText 157 语种 300d 向量,直到 2020 年前后仍是许多 NLP baseline 的默认输入。

**类比性质**是静态嵌入最出名的现象:$v_{\text{king}} - v_{\text{man}} + v_{\text{woman}} \approx v_{\text{queen}}$,即向量的线性运算能对应到语义关系(性别、时态、国家-首都)。这是分布假设+skip-gram 目标在几何上的副产品,但也不是普适的——Rogers et al.(2017)与 Nissim et al.(2020)指出许多类比结论对选词与评测协议敏感,不宜过度神化。

### 上下文嵌入:同一个词,不同向量

静态嵌入的根本局限是**一词多义**:`bank` 无论指银行还是河岸,拿到的都是同一个向量。**上下文嵌入(contextualized embedding)** 解决这一问题——同一个词在不同句子里得到不同向量,由整段输入共同决定。

代表工作:

- **ELMo**(Peters et al. NAACL 2018):双向 LSTM 语言模型的隐状态拼接,是"上下文嵌入"名词的提出者。
- **BERT / RoBERTa / DeBERTa**:Transformer encoder 的每一层隐状态都是词的上下文向量。参考 [[BERT与GPT的区别 BERT vs GPT]]。
- **GPT hidden states**:decoder-only 模型的隐状态也可当上下文嵌入用,但因因果注意力只看历史,通常不如 encoder 家族在**表示学习**任务上的效果。

到 2020 年之后,**句子/段落嵌入**成为主流应用形态:

- **Sentence-BERT**(Reimers & Gurevych EMNLP 2019):双塔 BERT + 池化 + 对比学习目标,把整句压成一个向量,广泛用于语义相似度、检索。
- **SimCSE / GTE / BGE / E5 / Jina-embed**:后续以 [[对比学习 Contrastive Learning]] 为骨干、以 MS MARCO 等大规模弱监督对为数据,把英语与多语句嵌入推到 SOTA。
- **OpenAI text-embedding、Cohere embed、Voyage 等 API 模型**:同样思路的商用封装。

到 2026 年,大多数生产系统里"词嵌入"实际上是"句/段嵌入":输入是任意长度的文本片段,输出一个 512–4096 维向量,直接进向量数据库供 [[信息检索 IR基础模型 Information Retrieval]] 与 [[混合检索 Hybrid Retrieval]] 检索。

### 评测

词嵌入的评测分**内在(intrinsic)** 与 **外在(extrinsic)** 两类:

- **内在**:
  - **词相似度**:在 WordSim-353、SimLex-999、MEN 等人类标注对上算余弦相似度,再与人工评分求 Spearman 相关。
  - **词类比**:Mikolov 提出的 Google Analogy(19,544 对语义 + 语法类比),BATS 是更严格的替代。
  - 内在指标已被广泛质疑与下游任务弱相关(Faruqui et al. 2016),仅供参考。
- **外在**:嵌入接下游任务(NER、情感分类、NLI、检索、问答)的准确率/F1/召回。**MTEB(Massive Text Embedding Benchmark,Muennighoff et al. 2023)** 是当前(2026)句嵌入的事实标准,覆盖 8 大类任务、上百种语言。

### 常见误区与陷阱

- **"训练一个新的 Word2Vec 是标准操作"** — 2026 年的生产 pipeline 中,除非领域极其小众且大模型 tokenizer 不覆盖,几乎没人再从头训 Word2Vec/GloVe;上游有现成的多语句嵌入 API 或开源 checkpoint,直接微调更划算。
- **"嵌入维度越高越好"** — 静态嵌入通常 $d\in[100, 300]$ 边际收益就饱和;句嵌入常见 $d\in[384, 1024]$,更高维度带来的检索质量提升有限,却显著增加存储与内存(参考 Matryoshka 表示 Kusupati et al. 2022:训练时同一模型输出多个可截断维度,存储可弹性)。
- **"大模型隐状态直接当句向量最准"** — LLM 最后一层的 mean pooling 做句向量在检索任务上通常**弱于**专门蒸馏的 BGE / E5,因为语言模型目标与"句子表示"目标不一致。需要 [[对比学习 Contrastive Learning]] 或专门监督再训一步。
- **"余弦相似度是万能度量"** — 余弦忽略幅长;当向量幅长本身编码了置信度或频率(某些静态嵌入),点积或欧氏距离更合适。检索模型的训练目标决定了应该用哪种度量,不能随意换。
- **"embedding 里没有偏见"** — Bolukbasi et al.(2016)、Caliskan et al.(2017,Science)在 Word2Vec/GloVe 中系统性发现性别、种族偏见(如 $v_{\text{programmer}} - v_{\text{man}} + v_{\text{woman}} \approx v_{\text{homemaker}}$)。上下文嵌入把偏见变得更隐蔽而非消失,任何依赖 embedding 做决策(简历排序、推荐)的系统都需专门做公平性评估。
- **"OOV 用 UNK 就够了"** — 高频固定 UNK 会让所有未登录词坍缩到同一点,严重影响长尾场景;实际生产用 subword(BPE、WordPiece、SentencePiece)或 FastText 式字符 n-gram 拆分,天然消除 OOV 问题。

### 概念边界

词嵌入不包含也不等同于以下相邻主题:

- **Tokenization(BPE / WordPiece / SentencePiece)**:决定"词"的粒度,是嵌入的**前置步骤**,独立主题。
- **图嵌入 / 知识图谱嵌入**:如 [[TransE 图嵌入]],目标是把图节点/关系嵌入向量,数据源是图三元组而非文本序列。
- **稠密检索(dense retrieval)**:是嵌入的**应用**,包含查询-文档不对称训练、负样本挖掘等特殊工程,不等同于"训一个 embedding"。
- **多模态嵌入**:CLIP、SigLIP 类,把文本与图像/音频对齐到共享空间,是词嵌入思想的跨模态延伸。

## 和我的项目的关系

词嵌入是几乎所有 KG/RAG 项目的最底层地基,但在不同项目里承担不同角色:

- **[[EvidenceFirst]] 的证据检索**:句嵌入(BGE-large-zh、E5-mistral 等)是稠密检索器的输出,直接决定"证据召回"的天花板;实践建议是**领域数据上做一次 SimCSE / InfoNCE 微调**再上线,通用嵌入在专业语料(财报、法律、医学)上召回明显偏低。
- **[[TripleChecker]] 的三元组一致性判别**:虽然主要靠 [[文本蕴含与自然语言推理 NLI]] 模型,但**候选证据召回阶段**依赖句嵌入检索。可以把三元组序列化(`头实体 [SEP] 关系 [SEP] 尾实体`)后走同一 embedding 空间,让 KG 三元组与自然语言证据在同一向量库中互查。
- **[[CoMaGRAG]] 的实体对齐/消歧**:实体名、别名、上下文的 embedding 相似度是 [[实体消歧 Entity Disambiguation]] 与 [[实体对齐 Entity Alignment]] 的核心特征;跨语言场景要用 LaBSE、E5-multilingual 之类的多语句嵌入。
- **[[GSAD]] 的语义搜索**:若涉及大规模文本索引,直接使用商用 embedding API 起量最快;真正上生产再评估自建。
- **面试与解释**:遇到"你为什么选 BGE 而不是 OpenAI"这类问题,能从"训练目标、开源可控、多语覆盖、成本"四点回答;而不是简单说"BGE 效果好"。
- **成本意识**:嵌入的**存储与检索开销**在百万文档级别就会成为主要成本。Matryoshka 表示、乘积量化(PQ)、HNSW 索引是必备工程知识,不该在写论文时才想起来。

## 交叉引用

- [[Transformer 自注意力机制]]
- [[BERT与GPT的区别 BERT vs GPT]]
- [[对比学习 Contrastive Learning]]
- [[信息检索 IR基础模型 Information Retrieval]]
- [[混合检索 Hybrid Retrieval]]
- [[K近邻 KNN K-Nearest Neighbors]]
- [[TransE 图嵌入]]
- [[实体消歧 Entity Disambiguation]]
- [[实体对齐 Entity Alignment]]
- [[文本蕴含与自然语言推理 NLI]]
- [[归一化 Normalization]]
- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[EvidenceFirst]]
- [[TripleChecker]]

## 更新记录

- 2026-07-16: 首次建页,给出词嵌入定义与三代演进(计数→静态→上下文),补齐 Word2Vec/GloVe/FastText 目标函数与实现细节、类比性质与局限、上下文/句嵌入主流方案、内在与外在评测(含 MTEB)、六条常见误区,以及在 EvidenceFirst/TripleChecker/CoMaGRAG 里的分工建议。
