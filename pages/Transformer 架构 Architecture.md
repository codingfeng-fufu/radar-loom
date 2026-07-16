---
摘要: Transformer用堆叠的自注意力和前馈子层加残差归一化实现并行序列建模,是现代LLM的架构基石。
来源: https://arxiv.org/abs/1706.03762
信度: 高
首次记录: 2026-07-16
tags: [LLM机制, 基础]
---

# Transformer 架构 Architecture

## 核心内容

**Transformer** 是 Vaswani et al.(NeurIPS 2017)在 *Attention Is All You Need* 中提出的序列建模架构,用**堆叠的自注意力子层 + 前馈子层**、辅以**残差连接**与**归一化**,替代了此前主导 NLP 的 RNN/LSTM 与主导 CV 序列问题的 CNN 编码器。它解决了两个长期难题:

1. **序列并行化**——RNN 必须按时间步串行计算 $h_t = f(h_{t-1}, x_t)$,无法充分利用 GPU;Transformer 一次前向内所有位置并行计算,训练效率提升一个数量级以上。
2. **长距离依赖**——RNN 的信息要沿时间步传递 $O(n)$ 步,梯度衰减严重;自注意力任意两位置直接一步交互,理论路径长度 $O(1)$。

关键思想是"用注意力代替循环":整个模型没有循环或卷积,只有 attention、线性层、归一化、残差。到 2020 年前后,Transformer 已经从 NLP 扩散到 CV(ViT)、语音(Whisper)、生物(AlphaFold 2)、代码、多模态等所有序列/集合建模场景,是当代大模型的通用底座。

本页是"Transformer 家族的目录页",给出**整体结构、数据流、复杂度、变体分家**,每个部件展开细节请跳到对应子页。

### 三个架构族

原始 Transformer 是**编码器-解码器**结构(6 层编码器 + 6 层解码器),用于机器翻译。后续演化出三个族群:

- **Encoder-only**:BERT、RoBERTa、DeBERTa。只保留编码器,双向自注意力,擅长**理解与判别**任务(分类、抽取、检索、NLI)。
- **Decoder-only**:GPT-1/2/3/4、LLaMA、Qwen、Claude、DeepSeek。只保留解码器,因果自注意力,擅长**生成与统一任务处理**,是当前商用主流。
- **Encoder-Decoder**:原始 Transformer、T5、BART、FLAN-T5、Whisper。同时保留双向编码器与因果解码器,通过**交叉注意力**连接两侧,适合有明确"输入→输出"边界的任务(翻译、摘要、语音识别)。

三族的分工与胜负,详见 [[BERT与GPT的区别 BERT vs GPT]] 与 [[编码器-解码器结构 Encoder-Decoder Architecture]]。

### 数据流:一个 encoder-decoder 前向

给定输入 token 序列 $x = (x_1, \dots, x_n)$ 与目标序列 $y = (y_1, \dots, y_m)$:

1. **输入嵌入 + 位置编码**:$X_0 = \text{Embed}(x) + \text{PE}(x) \in \mathbb{R}^{n\times d}$。参见 [[词嵌入 Word Embedding]] 与 [[位置编码 Positional Encoding]](现代 LLM 常用 [[旋转位置编码 RoPE]])。
2. **编码器 $N$ 层堆叠**:每层由两个子层组成,均带残差与 LayerNorm:

$$
\begin{aligned}
X'_l &= \text{LN}\bigl(X_{l-1} + \text{MHSA}(X_{l-1})\bigr) \\
X_l &= \text{LN}\bigl(X'_l + \text{FFN}(X'_l)\bigr)
\end{aligned}
$$

其中 MHSA 是 [[多头注意力 Multi-Head Attention]],FFN 是 [[前馈网络 FFN Feed-Forward Network]],残差与归一化分别参见 [[残差连接 Residual Connection]] 与 [[层归一化 LayerNorm BatchNorm]]。这里写的是原始 **Post-LN**;现代 LLM 普遍改用 Pre-LN,细节见 LayerNorm 页。

3. **解码器 $N$ 层堆叠**:每层比编码器多一个**交叉注意力**子层。查询来自解码器上一层,键值来自编码器输出 $X_N$:

$$
\begin{aligned}
Y'_l &= \text{LN}\bigl(Y_{l-1} + \text{MaskedMHSA}(Y_{l-1})\bigr) \\
Y''_l &= \text{LN}\bigl(Y'_l + \text{CrossAttn}(Y'_l, X_N)\bigr) \\
Y_l &= \text{LN}\bigl(Y''_l + \text{FFN}(Y''_l)\bigr)
\end{aligned}
$$

**掩码**保证位置 $t$ 只关注 $\leq t$ 的历史,是自回归生成的基础;参见 [[BERT与GPT的区别 BERT vs GPT]] 的因果掩码讨论。

4. **输出投影**:$\hat{p}(y_t) = \text{softmax}(W_o Y_N^{(t)})$,其中 $W_o$ 常与输入嵌入 tied,减少参数量并稳定训练。

原始超参:$d_{\text{model}}=512$,$d_{\text{ff}}=2048$($=4d$),多头 $h=8$、$d_k=d_v=64$,层数 $N=6$,dropout $0.1$。现代 LLM 沿用同一模板,规模放大到 $d_{\text{model}}=4096$–$16384$、$N=32$–$120$、$h=32$–$128$。

### 复杂度与瓶颈

设序列长度 $n$,隐藏维度 $d$,层数 $N$:

- **自注意力**:$O(n^2 d)$ 时间与 $O(n^2)$ 内存($QK^\top$ 是 $n\times n$)。这是 Transformer 的**长上下文瓶颈**,直接催生 FlashAttention(Dao et al. 2022)、稀疏注意力、线性注意力、状态空间模型(Mamba)、滑动窗口(Longformer、Mistral)等一整条研究线。
- **FFN**:$O(n d^2)$ 时间。当 $n \ll d$(短序列)时 FFN 是主导开销;$n \gg d$(长序列)时注意力主导。
- **参数量**:每层约 $12 d^2$(4 个投影 $d^2$ + FFN 两个 $d\cdot 4d$)。Encoder-only $N$ 层的参数量约为 $12Nd^2$,不含 embedding。GPT-3 的 175B 里嵌入约 0.6B、注意力约 60B、FFN 约 115B——FFN 占大头,这也是**MoE**(混合专家)首先替换 FFN 的原因。

### 训练要点

Transformer 训练远比 RNN 敏感,原论文与后续实践总结出几个必备技巧:

- **学习率 warmup + 反平方根衰减**:$\text{lr}(t) = d^{-0.5} \cdot \min(t^{-0.5}, t \cdot t_{\text{warmup}}^{-1.5})$。Post-LN 架构不 warmup 几乎必炸。
- **Label smoothing** $\epsilon = 0.1$:防止 softmax 输出过于自信,提升泛化。
- **Dropout** 在嵌入、注意力权重、FFN 输出三处独立使用。
- **权重初始化**:Xavier/scaled init,配合 Pre-LN 后可省 warmup。
- **梯度裁剪**:防止训练早期 loss spike。
- **混合精度(fp16/bf16) + gradient checkpointing**:大模型显存与算力工程标配。

### Transformer 相对 RNN/CNN 的胜出原因

- **并行度**:一次前向所有位置并行,充分利用 GPU 矩阵乘。
- **表示能力**:任意两位置可直接交互,不受因果链 / 局部感受野约束。
- **可扩展性**:结构近乎"堆积木",加深加宽都稳定,配合 Scaling Law(参见 [[Scaling Law 大模型缩放律]])形成"越大越好"的良性循环。
- **迁移能力**:预训练 + 微调 / prompt / RLHF 范式(参见 [[预训练与微调 Pretrain vs Finetune]]、[[后训练 Post-training]])在 Transformer 上最成熟。

### Transformer 的局限与后续路线

- **二次复杂度**:长上下文是瓶颈。**FlashAttention** 通过 IO 感知的分块算法把内存从 $O(n^2)$ 降到 $O(n)$、常数因子改善数倍,但计算量仍是 $O(n^2 d)$。**线性注意力**(Performer、Linformer)与**状态空间模型**(Mamba, Gu & Dao 2023)提供 $O(n)$ 替代,在超长序列上有优势,但通用效果尚未全面赶上 Transformer。
- **推理内存**:KV cache 随上下文线性增长,对长对话/长文档服务是主要显存压力,催生了分组查询注意力(GQA)、多查询注意力(MQA)、[[LLM 推理优化 KV Cache Quantization]]、PagedAttention/vLLM 等一系列工程优化。
- **"知识存哪"是黑箱**:研究表明大部分事实知识存在 FFN 的 key-value memory 中(Geva et al. 2021),而不是注意力矩阵。这一发现催生了模型编辑(model editing)与机器遗忘等方向,参见 [[机器遗忘 Machine Unlearning]]。
- **位置外推**:训练时最大长度为 $L$,推理超过 $L$ 时正弦位置编码尚能一定程度外推,而学习式位置编码几乎全失效。RoPE + 位置插值(Position Interpolation)、YaRN、NTK-aware scaling 等一系列改造把主流模型的上下文推到 128K–2M。

### 部件页导航

Transformer 由以下部件组成,每个部件已在库里有独立页面:

| 部件 | 页面 |
|------|------|
| 缩放点积自注意力 | [[Transformer 自注意力机制]] |
| 多头结构与实现 | [[多头注意力 Multi-Head Attention]] |
| 位置信息注入 | [[位置编码 Positional Encoding]] / [[旋转位置编码 RoPE]] |
| 前馈子层 | [[前馈网络 FFN Feed-Forward Network]] |
| 残差通路 | [[残差连接 Residual Connection]] |
| 归一化 | [[层归一化 LayerNorm BatchNorm]] |
| 激活 | [[激活函数 Activation Functions]] |
| 输入表示 | [[词嵌入 Word Embedding]] |
| 编码器-解码器 vs 三族 | [[编码器-解码器结构 Encoder-Decoder Architecture]] / [[BERT与GPT的区别 BERT vs GPT]] |
| 推理优化 | [[LLM 推理优化 KV Cache Quantization]] |

## 和我的项目的关系

我的所有项目都建立在 Transformer 类 LLM 之上,但 Transformer 本身不是我要改进的对象——**我利用它的长处、绕过它的短处**:

- **利用长处**:自然语言理解、蕴含判断、语义相似度是 Transformer 的强项,直接用作 [[EvidenceFirst]]、[[TripleChecker]] 的语义处理引擎。
- **绕过短处**:Transformer 的结构推理与事实一致性判断不可靠,这正是我要用**符号系统 / 状态机 / 图结构**补齐的地方,参见 [[神经符号方法 Neuro-Symbolic AI]] 与 [[确定性状态机 Deterministic State Machine]]。
- **成本意识**:自注意力的 $O(n^2)$ 让"多轮 LLM 调用"的开销累积得很快,EvidenceFirst 的设计目标之一就是保证每次验证只需一次 LLM 前向 + 一次轻量 BFS,避免"每检查一条证据都跑一遍 LLM"的成本陷阱。
- **面试与解释**:被问"你为什么要在 RAG 之上加状态机"时,可从 Transformer 的能力边界切入——"注意力矩阵可以对齐相关性,但不能保证事实正确;因此需要额外一层结构化验证"——比简单说"提升准确率"更能显示对底层机制的理解。

## 交叉引用

- [[Transformer 自注意力机制]]
- [[多头注意力 Multi-Head Attention]]
- [[前馈网络 FFN Feed-Forward Network]]
- [[残差连接 Residual Connection]]
- [[编码器-解码器结构 Encoder-Decoder Architecture]]
- [[位置编码 Positional Encoding]]
- [[旋转位置编码 RoPE]]
- [[层归一化 LayerNorm BatchNorm]]
- [[激活函数 Activation Functions]]
- [[词嵌入 Word Embedding]]
- [[BERT与GPT的区别 BERT vs GPT]]
- [[LLM 推理优化 KV Cache Quantization]]
- [[Scaling Law 大模型缩放律]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[后训练 Post-training]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-16: 首次建页。给出 Transformer 主页/hub:三大架构族、encoder-decoder 数据流公式、复杂度分析(自注意力 $O(n^2 d)$、FFN $O(nd^2)$、参数分布)、训练要点(warmup、label smoothing、dropout)、相对 RNN/CNN 的胜出原因、长上下文与 FFN 知识存储等局限,以及各部件页导航。
