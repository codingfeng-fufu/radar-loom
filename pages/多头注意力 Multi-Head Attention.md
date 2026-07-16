---
摘要: 多头注意力把缩放点积注意力并行运行h次,每头在低维子空间学不同关注模式,再拼接投影回原维度。
来源: https://arxiv.org/abs/1706.03762
信度: 高
首次记录: 2026-07-16
tags: [LLM机制, 基础]
---

# 多头注意力 Multi-Head Attention

## 核心内容

**多头注意力(Multi-Head Attention, MHA)** 是 [[Transformer 架构 Architecture]] 里"用注意力代替循环"的具体实现:把**缩放点积注意力(scaled dot-product attention)**并行运行 $h$ 个"头",每头在一个 $d/h$ 维的低维子空间独立计算注意力,最后把所有头拼接后再线性投影回 $d$ 维。相比单头注意力,MHA 在**相同参数预算**下让模型能同时关注多种不同性质的关系(局部语法、指代、长距离主题依赖),是 Transformer 表示能力的关键放大器。

本页的定位是"多头结构 + 缩放点积注意力 + 现代变体"三合一;更简短的自注意力概念说明请见 [[Transformer 自注意力机制]]。

### 缩放点积注意力

给定查询矩阵 $Q \in \mathbb{R}^{n\times d_k}$、键矩阵 $K \in \mathbb{R}^{m\times d_k}$、值矩阵 $V \in \mathbb{R}^{m\times d_v}$,注意力输出为

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V
$$

三个环节:

1. **相似度打分** $S = QK^\top \in \mathbb{R}^{n\times m}$。每行 $i$ 是 query $i$ 与所有 key 的原始相似度。
2. **缩放** $S/\sqrt{d_k}$。为什么除以 $\sqrt{d_k}$——若 $Q,K$ 元素独立同分布且方差为 1,则 $QK^\top$ 的每项方差为 $d_k$,当 $d_k$ 较大时点积绝对值变大,softmax 落到极端区间、梯度接近零。除以 $\sqrt{d_k}$ 把方差重新归一到 1,让 softmax 处于合适的工作区间。
3. **加权求和** $\text{softmax}(S/\sqrt{d_k}) V$。每行是 value 的凸组合,权重就是归一化后的注意力分布。

**Q/K/V 从哪来**:

- **自注意力(self-attention)**:$Q,K,V$ 都来自同一个输入 $X$,即 $Q=XW_Q, K=XW_K, V=XW_V$。查询、键、值是"同一段序列的三种投影视角"。
- **交叉注意力(cross-attention)**:$Q$ 来自解码器输入,$K,V$ 来自编码器输出。见 [[编码器-解码器结构 Encoder-Decoder Architecture]]。

**掩码**:在 softmax 之前,把不允许关注的位置对应分数设为 $-\infty$。常见两类:

- **因果掩码(causal / look-ahead mask)**:上三角为 $-\infty$,让位置 $t$ 只能关注 $\leq t$,自回归生成的必需。
- **padding 掩码**:批内变长序列的 padding 位置置 $-\infty$,防止无效 token 参与统计。

### 多头结构

把总维度 $d$(通常记作 $d_{\text{model}}$)平均切成 $h$ 份,每头维度 $d_k = d_v = d/h$。对每个头 $i \in \{1,\dots,h\}$:

$$
\text{head}_i = \text{Attention}(X W_i^Q, X W_i^K, X W_i^V)
$$

其中 $W_i^Q, W_i^K \in \mathbb{R}^{d\times d_k}$、$W_i^V \in \mathbb{R}^{d\times d_v}$。$h$ 个头的输出**在特征维拼接**再乘一个输出投影:

$$
\text{MHA}(X) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)\, W^O, \quad W^O \in \mathbb{R}^{d\times d}
$$

**关键工程观察**:虽然有 $h$ 个头,但由于每头维度是 $d/h$,总投影参数量仍是 $4d^2$(三个输入投影 + 一个输出投影),与"单个 $d$ 维注意力"一致。**多头不增加参数,只重新分配了怎么用这些参数**。

原始 Transformer 用 $h=8, d_k=64, d=512$;BERT-base 用 $h=12, d_k=64, d=768$;GPT-3 175B 用 $h=96, d_k=128, d=12288$。头数与每头维度是自由配比,总维度和参数约束下有多种选择。

### 为什么"多头"有效

Vaswani et al. 原论文的直觉:一个 softmax 只能对齐一种"关注模式",多头让模型在多种子空间里同时对齐不同关系。后续机制可解释性工作(Voita et al. ACL 2019, Clark et al. BlackBoxNLP 2019)在预训练 Transformer 上做了大规模注意力头功能分析,发现头之间存在明确分工:

- 部分头稳定关注**相邻 token**(近似 n-gram);
- 部分头关注**句法依存对象**(动词—宾语、修饰—中心);
- 部分头关注**指代或语义共现**(代词—先行词);
- 相当比例的头是"冗余"或"注意力汇聚(attention sink)",可在推理时剪掉而几乎不损效果——这是 [[LLM 推理优化 KV Cache Quantization]] 里 head pruning 类工作的动机。

但 Michel et al.(NeurIPS 2019)也提出**"Are Sixteen Heads Really Better than One?"**,证明训练后可将大量头剪掉、性能几乎不变。这说明多头的价值主要出现在**优化过程**中——多头提供了多条并行学习通路,让训练更容易找到好的解;但训练完成后单个模型未必真的"用满"所有头。

### 计算复杂度

对一次自注意力前向,输入 $X \in \mathbb{R}^{n\times d}$:

- 投影 $Q, K, V$:$3 \cdot n \cdot d^2$ FLOPs。
- 计算 $QK^\top$:$n^2 \cdot d$ FLOPs。
- softmax:$n^2$ 逐元素,一般忽略。
- 乘 $V$:$n^2 \cdot d$ FLOPs。
- 输出投影:$n \cdot d^2$ FLOPs。

总计约 $O(n^2 d + n d^2)$。当 $n \ll d$ 时投影主导,当 $n \gg d$ 时 $n^2 d$ 主导。**内存瓶颈**是 $QK^\top \in \mathbb{R}^{n\times n}$,这一 $O(n^2)$ 显存占用是长上下文的核心痛点,催生了 FlashAttention 与后续变体。

### 现代变体

MHA 在 2022 年后经历了几波重要改造,全部针对**推理时 KV cache 占用**这一瓶颈:

- **Multi-Query Attention(MQA)**(Shazeer 2019):所有头共享一组 $K, V$(只 $Q$ 保持 $h$ 头)。KV cache 从 $O(h)$ 组降到 $O(1)$ 组,推理显存下降数倍,但训练效果略降。PaLM、Falcon 用过。
- **Grouped-Query Attention(GQA)**(Ainslie et al. EMNLP 2023):折中方案,把 $h$ 个 Q 头分成 $g$ 组共享 KV($1 \leq g \leq h$)。$g=1$ 即 MQA,$g=h$ 即 MHA。LLaMA-2/3、Mistral、Qwen 均采用 $g=8$ 左右的 GQA,是当前事实标准。
- **Multi-Head Latent Attention(MLA)**(DeepSeek-V2/V3 2024):把 KV 压缩到低秩隐向量再解压,KV cache 降到 GQA 的约 1/4,同时训练效果不劣。DeepSeek 系列的核心创新之一。
- **FlashAttention**(Dao et al. NeurIPS 2022, Dao 2023)/**FlashAttention-2/3**:不是模型侧改造,而是 IO 感知的注意力算子——通过 tiling 与 kernel fusion 让 $QK^\top$ 中间结果不物化到 HBM,时间与显存均线性于 $n$($O(n)$ 显存 + 数倍加速)。已成为主流训练框架的默认实现。

### 常见误区

- **"$\sqrt{d_k}$ 只是经验值"** — 不是,是方差匹配的推导结果;不除或除以 $d_k$ 都会明显影响训练稳定性。
- **"多头就是把序列切成几段各自算"** — 错,是把**特征维**切成 $h$ 份,每头看**完整序列**在不同子空间的投影。
- **"注意力权重可解释模型决策"** — 只是**软对齐**,Jain & Wallace(NAACL 2019)、Bibal et al.(ACL 2022)证明改变注意力权重不必然改变输出,反之亦然。用注意力做"模型解释"要慎重。
- **"softmax 是唯一选择"** — 也有 Linear Attention、Performer(核方法近似)、Longformer 局部+全局稀疏、Big Bird 混合稀疏等替代方案,但通用效果尚未超过 softmax 注意力。
- **"MHA 输出维度等于头数 × 每头维度"** — 输出维度总是 $d$(通过 $W^O$ 投影),头数和每头维度只是内部切分。

## 和我的项目的关系

多头注意力是我调用的 LLM 的核心零件,不直接参与设计,但几个工程决策与它相关:

- **[[EvidenceFirst]] 的推理成本估算**:知道注意力是 $O(n^2 d)$、KV cache 随上下文线性增长,能合理规划系统里"多长的证据窗口 × 多轮验证"的组合上限,避免设计出成本无法落地的方案。
- **模型选型**:面对同规模模型时,GQA(LLaMA-3、Mistral)与 MLA(DeepSeek-V3)在推理阶段显存友好度差别很大,自建推理服务时是关键选型依据。
- **注意力可视化不等于解释**:如果我在 [[TripleChecker]] 里想借"模型注意到了哪个 token"作为可信证据展示,需要意识到注意力权重与实际决策的因果关系薄弱——这个方向更应该做 [[归因评测 Attribution]] 而不是 attention viz。
- **面试话术**:被问到"为什么 LLM 上下文窗口越长成本越贵",能把 $O(n^2)$ 注意力、KV cache 线性增长、FlashAttention 缓解常数因子但不改渐近复杂度这三层讲清楚,比笼统答"因为要处理更多 token"专业得多。

## 交叉引用

- [[Transformer 架构 Architecture]]
- [[Transformer 自注意力机制]]
- [[编码器-解码器结构 Encoder-Decoder Architecture]]
- [[位置编码 Positional Encoding]]
- [[旋转位置编码 RoPE]]
- [[前馈网络 FFN Feed-Forward Network]]
- [[LLM 推理优化 KV Cache Quantization]]
- [[归因评测 Attribution]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-16: 首次建页。给出缩放点积注意力公式与 $\sqrt{d_k}$ 缩放推导、多头结构与参数守恒、注意力头功能分析、复杂度公式、MQA/GQA/MLA/FlashAttention 等现代变体,以及五条常见误区。
