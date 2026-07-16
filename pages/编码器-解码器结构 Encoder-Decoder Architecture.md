---
摘要: 编码器双向理解输入,解码器因果生成并通过交叉注意力关注编码器输出,原始Transformer与T5的核心结构。
来源: https://arxiv.org/abs/1706.03762
信度: 高
首次记录: 2026-07-16
tags: [LLM机制, 基础]
---

# 编码器-解码器结构 Encoder-Decoder Architecture

## 核心内容

**编码器-解码器(encoder-decoder)** 是原始 Transformer(Vaswani et al. 2017)采用的结构:一个**双向编码器**负责把输入序列压缩为一组上下文表示,一个**因果解码器**负责根据这组表示自回归地生成输出序列,两者通过**交叉注意力(cross-attention)**连接。它是**序列到序列(seq2seq)** 建模的标准范式,直接沿用了 2014 年 Sutskever/Cho 用 RNN 做机器翻译的整体思想,把 RNN 换成 Transformer。

到 2026 年,主流商用 LLM 全部是 decoder-only,但 encoder-decoder 并未消失——它在**输入-输出边界清晰、任务导向的 seq2seq 场景**里仍有独特优势:机器翻译、语音识别(Whisper)、结构化 SQL/代码生成、部分摘要与改写任务。本页梳理它与另外两族(encoder-only、decoder-only)的差别、交叉注意力的机制、以及各自的适用条件。

三族对比与胜负参见 [[BERT与GPT的区别 BERT vs GPT]];本页聚焦"encoder-decoder 内部如何工作"以及"什么时候它比 decoder-only 更合适"。

### 高层结构

给定源序列 $x = (x_1, \dots, x_n)$ 与目标序列 $y = (y_1, \dots, y_m)$:

1. **编码器**:$N$ 层堆叠,每层由**双向自注意力 + FFN** 组成,输出上下文表示 $H = (h_1, \dots, h_n) \in \mathbb{R}^{n\times d}$。编码器每个位置可以看到输入所有位置,天然承担"理解"角色。
2. **解码器**:$N$ 层堆叠,每层比编码器**多一个**子层——交叉注意力。解码器每个 block 的三个子层依次为:
   - **因果自注意力(masked self-attention)**:目标位置 $t$ 只关注 $\leq t$ 的目标 token,保证自回归性;
   - **交叉注意力(cross-attention / encoder-decoder attention)**:目标位置作为 query,编码器输出 $H$ 作为 key/value,让解码器**从源序列检索所需信息**;
   - **FFN**。
3. **输出投影**:解码器末层过 linear + softmax 得到 $\hat{p}(y_t \mid y_{<t}, x)$。

每个子层外套一层残差 + LayerNorm(参见 [[残差连接 Residual Connection]] 与 [[层归一化 LayerNorm BatchNorm]])。

### 交叉注意力:两侧的桥

交叉注意力用的还是 [[多头注意力 Multi-Head Attention]] 的缩放点积公式,但 Q/K/V 来源不同:

$$
\text{CrossAttn}(Y, H) = \text{softmax}\!\left(\frac{(YW_Q)(HW_K)^\top}{\sqrt{d_k}}\right)(HW_V)
$$

- $Y \in \mathbb{R}^{m\times d}$:解码器上一子层的输出(**目标侧**);
- $H \in \mathbb{R}^{n\times d}$:编码器最终输出(**源侧**);
- 注意力矩阵形状 $m \times n$,每一行对应一个目标位置,列表示它关注到源序列每个位置的权重。

**关键性质**:

1. **不对称**:query 来自目标序列,key/value 来自源序列。编码器输出**只作为 K/V**,不作为 Q——它是"被检索的知识库"。
2. **每一步生成都会重新与编码器对齐**:解码位置 $t$ 生成 $y_t$ 时,cross-attention 决定 $y_t$ 从源序列的哪些位置抽取信息。在机器翻译里这直接对应"对齐(alignment)",可以可视化——早期神经机器翻译论文(Bahdanau et al. 2015)展示的"注意力热图"就是这个矩阵。
3. **K/V 只需计算一次**:整个生成过程中源序列不变,编码器输出 $H$ 只走一次前向,后续 $m$ 步解码复用同一份 $K, V$。这是 encoder-decoder 相对 decoder-only 在 seq2seq 上的一个效率优势。
4. **无掩码**:不同于因果自注意力,交叉注意力没有因果掩码——目标位置可以关注源序列的任意位置(未来、过去都行,源序列本来就是给定的)。

### 训练与推理

**训练**:采用 **teacher forcing**——把真实目标 $y_{<t}$ 直接喂进解码器,预测 $y_t$。整个序列 $y$ 一次前向即可,并行度高,和 decoder-only 相同。

**推理**:自回归采样,每步生成一个 token 后拼回输入。**编码器只跑一次**,解码器逐步跑;为了避免每步都重跑解码器全部历史,同样使用 [[LLM 推理优化 KV Cache Quantization]] 里的 KV cache——缓存目标侧自注意力的 K/V,以及编码器侧的 K/V(后者从头到尾不变,天然可复用)。

**长度控制**:seq2seq 里目标长度不由源长度决定,常用 length penalty 或 min/max length 约束;beam search 是经典解码策略,现代大模型更倾向 sampling(top-k、nucleus)。

### 三族对比:何时该用哪个

**Encoder-only(BERT/RoBERTa/DeBERTa)**:输入完全可见,输出是每个位置或整句的判别式表示。适合分类、抽取、检索、NLI、判分。**不擅长生成**——没有因果自注意力,无法做自回归解码。

**Decoder-only(GPT/LLaMA/Claude/Qwen/DeepSeek)**:因果自注意力,天然支持自回归。通过 **prompt = 输入 + 生成 = 输出** 的"任务统一"形式吞并了几乎所有任务(包括原本 BERT 擅长的判别任务),是 2024 年后商用 LLM 的绝对主流。

**Encoder-Decoder(T5/BART/FLAN-T5/Whisper)**:双向理解 + 因果生成的组合。相对 decoder-only 的**独特优势**:

- **输入-输出边界清晰**:翻译、语音识别、结构化生成这类"给定输入 X,产出 Y,X 不参与 Y 的自回归"的任务里,把 X 与 Y 分开更符合任务结构;
- **交叉注意力对齐可解释**:cross-attention 矩阵天然是"目标→源"对齐,便于调试与错误定位;
- **编码器可以是双向的**:对源侧的理解利用了双向上下文,理论上信息更丰富;
- **训练目标灵活**:T5 用 span corruption(遮盖连续 span,由解码器还原),UL2 混合 R-denoising、S-denoising、X-denoising,在同一模型内统一多种任务形态。

**为什么大多数任务还是 decoder-only 赢了**:

- **任务统一 + 规模化**:decoder-only 一个模型处理任意任务,规模化收益(Scaling Law)最直接。
- **In-context learning 是因果 LM 的副产品**:encoder-decoder 里 prompt 与生成天然被切分,少了"prompt 也是历史 token"的性质,ICL 与 CoT 的展现不如 decoder-only。
- **服务同构**:所有请求都是"前缀 + 生成",KV cache 与推理引擎同构。encoder-decoder 需要维护两个 forward 路径与两套 KV cache,推理服务更复杂。
- **Tay et al.(2022, UL2)** 证明:decoder-only + 混合去噪目标可以拿到大部分 encoder-decoder 的收益,而反过来不容易。

因此现代取舍:**除非任务本身有强"输入-输出"结构且有充足训练数据**,新项目默认选 decoder-only。真正剩下的 encoder-decoder 强势场景包括:

- **机器翻译**:NLLB、M2M-100 依然是 encoder-decoder;
- **语音识别**:Whisper(encoder 处理 mel-spectrogram,decoder 生成文本);
- **图像描述与 image-to-text**:早期视觉-语言模型多为 encoder-decoder;
- **专业 SQL / 代码生成**:CodeT5 等在受限领域仍常见。

### 具体家族样例

- **原始 Transformer(2017)**:6 encoder + 6 decoder,机器翻译 WMT En-De。
- **BART**(Lewis et al. 2020):encoder-decoder 版 BERT,预训练目标是"任意噪声还原"(掩码、删除、置换、旋转)。生成质量强,擅长摘要。
- **T5**(Raffel et al. JMLR 2020)与 **FLAN-T5**:把所有 NLP 任务都写成 "text-to-text",训练目标是 span corruption,配合大规模指令微调形成 FLAN-T5。
- **mT5、ByT5、UL2**:T5 的多语言、字节级、混合去噪扩展。
- **Whisper**(Radford et al. 2022):OpenAI 的多语音识别与翻译模型,decoder 通过特殊 token 控制任务(转写/翻译)。
- **AlphaFold 2 的 Evoformer + Structure Module**:虽然不叫 seq2seq,结构上也是"编码 MSA/pair 表示 + 解码坐标",思想同源。

### 常见误区

- **"encoder-decoder 就是两个 encoder 堆一起"** — 错,decoder 多了因果掩码和交叉注意力,与 encoder 的每一层结构不同。
- **"cross-attention 是双向的"** — 不是。cross-attention 的 Q 来自目标(单向、因果),K/V 来自源(双向、可自由访问),整体是"因果查询访问双向记忆"。
- **"decoder-only 不能做机器翻译"** — 能做,GPT-4/Claude 类模型翻译效果强于绝大多数专门翻译模型;但训练数据与工程流水线上,encoder-decoder 仍在垂类翻译系统里保有份额。
- **"T5 是 decoder-only 的祖师"** — T5 是 encoder-decoder;把 T5 与 GPT-3 混同是常见笔误。
- **"encoder-decoder 的 KV cache 比 decoder-only 小"** — 目标侧 KV cache 结构相同;但**编码器侧的 K/V 只算一次不随生成步骤增长**,是 encoder-decoder 相对 decoder-only 在同长度输入-输出下的真实推理优势(输入越长优势越明显)。

## 和我的项目的关系

我的项目都基于 decoder-only LLM,但 encoder-decoder 的思路在几处有借鉴价值:

- **[[EvidenceFirst]] 的两阶段设计**:先"编码"证据材料(retrieval + 压缩)再"解码"答案(生成 + 状态机验证),结构上就是 encoder-decoder——只不过"编码器"是检索系统 + embedding,"解码器"是 LLM,交叉注意力对应 LLM 在生成时对证据的 attend。这是**架构类比**,能帮助我在设计时保持接口清晰。
- **[[TripleChecker]] 的判别式后端**:三元组验证本质是"输入(三元组+证据) → 输出(判定)",没有生成需求,天然适合 encoder-only 或轻量 encoder-decoder 后端(如 DeBERTa 或 mT5-small),而非动用 LLM。这一分工能显著降低推理成本。
- **翻译/多语场景**:若项目涉及跨语言证据,专门的翻译模型(NLLB、mBART)通常好于把翻译任务交给通用 LLM。
- **面试话术**:被问"为什么 GPT 赢了 T5",标准答案包含"任务统一 × ICL × 服务同构 × UL2 实证",避免只说"GPT 更好"。

## 交叉引用

- [[Transformer 架构 Architecture]]
- [[Transformer 自注意力机制]]
- [[多头注意力 Multi-Head Attention]]
- [[前馈网络 FFN Feed-Forward Network]]
- [[残差连接 Residual Connection]]
- [[层归一化 LayerNorm BatchNorm]]
- [[位置编码 Positional Encoding]]
- [[BERT与GPT的区别 BERT vs GPT]]
- [[机器翻译 Machine Translation]]
- [[文本摘要 Text Summarization]]
- [[LLM 推理优化 KV Cache Quantization]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-16: 首次建页。给出编码器-解码器结构、交叉注意力公式与四条性质、训练/推理流程、三族(encoder-only/decoder-only/encoder-decoder)何时用哪个的取舍(含 UL2、任务统一、ICL、服务同构四点论证)、代表家族样例(Transformer、BART、T5、Whisper、AlphaFold),以及五条常见误区。
