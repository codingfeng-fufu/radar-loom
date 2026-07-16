---
摘要: Transformer的position-wise FFN在每个token独立做两层MLP,承载大部分参数与事实性知识。
来源: https://arxiv.org/abs/1706.03762
信度: 高
首次记录: 2026-07-16
tags: [LLM机制, 基础]
---

# 前馈网络 FFN Feed-Forward Network

## 核心内容

**前馈网络(Position-wise Feed-Forward Network, FFN)** 是 [[Transformer 架构 Architecture]] 每个 block 中与注意力子层并列的第二个子层。它在每个位置**独立地**做一次两层 MLP(注意力**跨位置**做混合,FFN**跨特征**做混合),两者配合构成"混合信息 + 逐点变换"的完整表示学习环节。

FFN 是 Transformer 里**参数最集中的部件**——通常占单层参数的三分之二左右,大模型里占总参数量的约 60–70%——同时也是事实性知识的主要储存位置(Geva et al. EMNLP 2021)。

### 数学形式

原始 Transformer(Vaswani et al. 2017)中,FFN 定义为

$$
\text{FFN}(x) = W_2\,\sigma(W_1 x + b_1) + b_2
$$

其中 $x \in \mathbb{R}^d$,$W_1 \in \mathbb{R}^{d_{\text{ff}}\times d}$,$W_2 \in \mathbb{R}^{d\times d_{\text{ff}}}$,激活 $\sigma$ 在原论文里是 ReLU。**扩张比**通常取 $d_{\text{ff}} = 4d$(即先升维 4 倍,过激活,再降回 $d$),原始配置 $d=512, d_{\text{ff}}=2048$;GPT-3 175B 用 $d=12288, d_{\text{ff}}=49152$;LLaMA-2 70B 用 $d=8192, d_{\text{ff}}\approx 28672$(SwiGLU 会略小于 4 倍)。

**"position-wise"** 的含义:同一层里所有 token 位置**共享**同一组权重 $W_1, W_2$,每个位置的输入独立经过这套 MLP。这等价于在特征维做 $1\times 1$ 卷积——参数不随序列长度增长,只随隐藏维度 $d$ 增长。

参数量约为 $2 \cdot d \cdot d_{\text{ff}} = 8d^2$(若 $d_{\text{ff}}=4d$),比自注意力的 $4d^2$(四个投影)高一倍——这也是为什么 FFN 是 Transformer 的参数大头。

### 激活函数演化

原始 FFN 用 ReLU,现代 LLM 已几乎全部换成更平滑的门控变体:

- **GELU**(Hendrycks & Gimpel 2016):$\text{GELU}(x) = x\Phi(x)$,BERT、GPT-2/3 使用。参见 [[激活函数 Activation Functions]]。
- **Swish / SiLU**:$x\sigma(x)$,PaLM 使用。
- **GLU 家族**(Shazeer 2020, *GLU Variants Improve Transformer*):把 FFN 改成门控形式

$$
\text{FFN}_{\text{GLU}}(x) = W_2 \bigl((W_1 x) \odot \sigma(W_g x)\bigr)
$$

即先分别做两个投影,一个走激活作门控,一个走线性作值,逐元素相乘后再投影回来。常见变体:**GeGLU**($\sigma = \text{GELU}$)、**SwiGLU**($\sigma = \text{Swish}$)、**ReGLU**($\sigma = \text{ReLU}$)。SwiGLU 是当前主流选择(LLaMA、PaLM、Mistral、Qwen、DeepSeek、GLM 系列)。

GLU 引入了一个额外的 $W_g$ 投影,参数量增至 $3 \cdot d \cdot d_{\text{ff}}$。为保持总参数量,实际 GLU 家族会把 $d_{\text{ff}}$ 缩到约 $\frac{2}{3} \cdot 4d = \frac{8}{3}d$,例如 LLaMA-2 7B 的 $d=4096, d_{\text{ff}}=11008$($\approx 2.69 d$)。

### FFN 里存了什么?

Geva et al.(EMNLP 2021)*Transformer Feed-Forward Layers Are Key-Value Memories* 提出一个至今被广泛引用的机制解释:把 $W_1$ 的每一行看作"key" $k_i$,把 $W_2$ 的对应列看作"value" $v_i$,则 FFN 的输出可写作

$$
\text{FFN}(x) = \sum_{i=1}^{d_{\text{ff}}} \sigma(k_i^\top x) \cdot v_i
$$

这在结构上等价于**一次 soft key-value 检索**:$k_i^\top x$ 判断当前隐状态与第 $i$ 个 key 的匹配程度,通过激活函数产生一个"检索强度",然后按此强度加权对应的 value $v_i$ 并叠加。这一视角有几层实证支撑:

- Meng et al.(NeurIPS 2022, *Locating and Editing Factual Associations in GPT*)通过因果干预定位到"埃菲尔铁塔在巴黎"这类事实存储在特定层的 FFN 里,并可精准编辑单一 key-value 完成"知识修改"。
- Dai et al.(2022)提出**Knowledge Neurons**,证明部分 FFN 神经元与特定事实高度对齐。
- Bricken et al.(Anthropic 2023, *Towards Monosemanticity*)通过稀疏字典学习分解 FFN 激活,发现单神经元往往是多义的、但线性组合出的方向是可解释的"特征"。

结论:**注意力做"混合",FFN 做"检索与转化"**,大部分事实性知识(以及可以被针对性编辑或遗忘的记忆)存在 FFN 里。这是 [[机器遗忘 Machine Unlearning]] 与模型编辑方向的物质基础。

### MoE:稀疏化的 FFN

由于 FFN 参数占比大,把它替换成**混合专家(Mixture of Experts, MoE)** 是最直接的模型放大手段——参数量 $\times N$,计算量只 $\times k$(激活的专家数)。

标准 MoE-FFN:

$$
\text{MoE}(x) = \sum_{e=1}^{N} g_e(x)\, \text{FFN}_e(x)
$$

$g_e(x)$ 是 gating 网络对专家 $e$ 的权重,通常只取 top-$k$($k=1$–$2$)非零(**sparsely-gated MoE**,Shazeer et al. 2017)。代表工作:GShard、Switch Transformer(Fedus et al. 2021)、Mixtral 8×7B(Jiang et al. 2024)、DeepSeek-MoE、Qwen1.5-MoE。

MoE 的工程要点:

- **负载均衡损失**:防止某几个专家垄断路由;
- **专家并行(EP)** 通信 vs 计算的权衡;
- **推理时的专家 offloading / 稀疏激活加速**;
- **专家数量 $N$ 越大,总参数越大,但推理时激活的计算量不变**——这也是 Mixtral 8×7B 的"总参数 46.7B、每 token 激活 12.9B"数字的来源。

### 常见误区

- **"FFN 没什么可说的,就是普通 MLP"** — 结构上是普通 MLP,但**位置**(在注意力之后)、**扩张比**(4×)、**参数占比**(60%+)、**功能定位**(事实存储、语义变换)让它是 Transformer 里最重要的部件之一。
- **"SwiGLU 只是激活换了个函数"** — 是"激活 + 门控 + 参数量"的一整套改动,不能只换激活不换门控;许多复现失败于此。
- **"MoE 免费扩大模型"** — 参数是免费扩大了,但训练稳定性、路由平衡、显存与通信、推理架构均有额外复杂度,不是纯粹的性能白送。
- **"FFN 每层学到的都一样"** — 底层 FFN 更接近词法/句法特征,中高层 FFN 更接近语义/事实记忆(Geva et al. 2022, Tenney et al. ACL 2019)。定位与编辑事实时要选对层。
- **"注意力才是 Transformer 的核心"** — 从参数量、计算量、事实存储任一维度看,FFN 都是同等甚至更重要的部件;把 Transformer 只理解成"注意力"是常见的表述偏差。

## 和我的项目的关系

FFN 本身不是我要改的对象,但了解它的机制解释对几个决策直接有用:

- **[[TripleChecker]] / [[EvidenceFirst]] 的幻觉定位**:若某类事实(如"某公司 CEO")在 LLM 里被系统性答错,可以借鉴 ROME / MEMIT(基于 FFN key-value 编辑)的方向做定点修正,而不是走"喂更多数据全模型微调"的重路。
- **[[机器遗忘 Machine Unlearning]] 的可行性**:事实主要存于 FFN 意味着遗忘可通过局部编辑实现,不必重训整个模型;这条路径的成本与合规价值都很大。
- **模型选型的推理成本**:MoE 模型(Mixtral、DeepSeek-V3)在同"激活参数量"下能吃更大的"总参数量",在有充足显存的部署环境里是显著性价比的选项;资源紧张场景则不划算(装不下)。
- **面试话术**:被问"Transformer 里参数都在哪儿",标准答案是"约 2/3 在 FFN,尤其是扩张比 4× 的两个投影";再进一步能引到 Geva et al. 的 key-value memory 视角,显示对底层机制不止一层理解。

## 交叉引用

- [[Transformer 架构 Architecture]]
- [[Transformer 自注意力机制]]
- [[多头注意力 Multi-Head Attention]]
- [[残差连接 Residual Connection]]
- [[层归一化 LayerNorm BatchNorm]]
- [[激活函数 Activation Functions]]
- [[机器遗忘 Machine Unlearning]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-16: 首次建页。给出 position-wise FFN 定义与参数量、扩张比 4× 惯例、激活函数从 ReLU 到 SwiGLU 的演化、GLU 家族公式与参数守恒缩放、FFN 作为 key-value memory 的机制解释(Geva et al.、ROME)、MoE 稀疏化的工程要点,以及五条常见误区。
