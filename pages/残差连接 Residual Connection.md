---
摘要: 残差连接以y=x+F(x)让梯度直通深层,是训练百层以上Transformer/ResNet的必要条件。
来源: https://arxiv.org/abs/1512.03385
信度: 高
首次记录: 2026-07-16
tags: [LLM机制, 基础]
---

# 残差连接 Residual Connection

## 核心内容

**残差连接(residual connection / skip connection)** 是 He et al.(CVPR 2016, *Deep Residual Learning for Image Recognition*)在 ResNet 中提出的结构原语,把某个非线性变换 $F$ 的输出**加上**其输入,而不是只保留 $F(x)$:

$$
y = x + F(x)
$$

这一改动让"从 $y$ 出发计算 $x$ 的梯度"沿两条通路进行——一条穿过 $F$、一条恒等直通——彻底缓解了深层网络的**梯度消失**与**优化困难**,是当代 100+ 层网络(ResNet-152、Transformer 96 层 GPT-3、AlphaFold 2 的 48 层 Evoformer)得以训练成功的关键结构性发明。

在 [[Transformer 架构 Architecture]] 中,残差连接出现在**每个子层的外围**:注意力子层和 FFN 子层都被残差包裹,并在残差前或后接 [[层归一化 LayerNorm BatchNorm]](分别对应 Pre-LN 与 Post-LN 两种变体)。

### 为什么梯度能"直通"

设深层堆叠 $y_L = y_0 + \sum_{l=0}^{L-1} F_l(y_l)$,对某层 $y_l$ 的梯度可展开为

$$
\frac{\partial \mathcal{L}}{\partial y_l} = \frac{\partial \mathcal{L}}{\partial y_L}\left(1 + \frac{\partial}{\partial y_l}\sum_{k=l}^{L-1} F_k(y_k)\right)
$$

**关键的 $1$**:即便所有 $F_k$ 的导数因链式乘积衰减到接近 0,梯度里仍有一份来自恒等映射的 $1$ 直接乘回来。没有残差时,梯度是纯乘积 $\prod_k \partial F_k / \partial y_k$,只要每层的导数范数略小于 1,梯度就以指数速度衰减——这就是**梯度消失**的机理。残差把"乘积"变成"乘积 + 常数",打破了指数衰减。

这一分析出自 He et al.(ECCV 2016, *Identity Mappings in Deep Residual Networks*),该论文的另一个重要结论是**残差路径上应尽量保持恒等**:任何在 residual path 上加入的 BN、激活、gating 都会显著恶化深层训练。这直接推动了后来 Pre-LN 的采用——把 LN 放在残差**分支的入口**,让主残差通路是纯恒等映射。

### 为什么"学残差"比"直接学"容易

原论文 He et al. 2016 给出的直觉:若真正想学的目标函数 $H(x)$ 接近恒等,让网络去学 **残差** $F(x) = H(x) - x$ 比直接学 $H(x)$ 简单得多——学 $F(x) \approx 0$ 比学 $H(x) \approx x$ 需要的表达力更小,权重可以从零附近开始安全增长。这也是**残差初始化**的常见做法:初始化时让 $F(x)$ 输出接近 0(如把 $F$ 的最后一个投影矩阵初始化为很小的值),整个网络最初等价于恒等映射,再逐渐"雕刻"出有用的变换。

### 在 Transformer 里的具体位置

每个 Transformer block 包含两个残差包裹的子层:

**Post-LN(原论文)**:

$$
\begin{aligned}
z &= \text{LN}\bigl(x + \text{MHSA}(x)\bigr) \\
y &= \text{LN}\bigl(z + \text{FFN}(z)\bigr)
\end{aligned}
$$

**Pre-LN(现代 LLM)**:

$$
\begin{aligned}
z &= x + \text{MHSA}(\text{LN}(x)) \\
y &= z + \text{FFN}(\text{LN}(z))
\end{aligned}
$$

两者的关键区别在于**主残差通路是否被 LN 打断**:Post-LN 每次残差相加后立刻归一化,深层训练时梯度经过多层 LN 缩放,容易失稳、需要精心 warmup;Pre-LN 主残差通路是纯恒等,深层稳定得多,但末端激活尺度会累积漂移,通常在最末层后加一个 final LN 收敛数值范围。参见 [[层归一化 LayerNorm BatchNorm]] 的详细讨论。

### 残差 stream:激活的"信息通道"

近年机制可解释性研究(Elhage et al. Anthropic 2021, *A Mathematical Framework for Transformer Circuits*)把 Pre-LN Transformer 的主残差通路称为 **residual stream**,并给出如下视角:

- 每个 token 的 residual stream 是一个 $d$ 维向量,初始等于嵌入 + 位置编码;
- 每个 MHSA / FFN 子层都是"**从 residual stream 读、加一个增量,再写回 residual stream**";
- 因此模型的最终表示 = 嵌入 + $\sum_{l} (\text{MHSA}_l + \text{FFN}_l)$ 的累加;
- 不同子层学习"写在 residual stream 的哪些维度",可以近似看作**分工写入**;
- 输出投影读取 residual stream 的特定线性方向,决定下一 token 的分布。

这一"stream + 读写增量"视角是当前 mechanistic interpretability 主流分析框架,包括 induction head、attention sink、feature circuits 都基于它展开。它也解释了为何"直接把 residual stream 的中间态取出做 probing"能拿到丰富的语言学、事实性信号——所有子层的中间产物都被叠加在同一通路上。

### 与优化的其他关系

- **Lipschitz 与稳定性**:残差让每层的雅可比矩阵 $I + \partial F / \partial x$ 的谱靠近单位阵,数值上更稳定,允许更大学习率与更深网络。
- **Ensemble 视角**:Veit et al.(NeurIPS 2016)证明 $L$ 层残差网络在推理时相当于 $2^L$ 条不同深度路径的隐式集成——从 $y = x + F_1$ 展开就能看到,任何长度的子路径都存在。深度剪枝(随机丢层 stochastic depth)在残差网络上有效正是这个原因。
- **梯度直连不等于无限深皆有效**:即便有残差,过深仍会遇到表达冗余、数值累积漂移问题。Transformer 到千层规模需要额外技巧(Sub-LN、DeepNet 的 $\alpha$ 缩放、Muon 优化器等)。

### 与其他"跳连"结构的对比

- **DenseNet 密集连接**(Huang et al. CVPR 2017):每层输出**拼接**到后续所有层的输入,而不是相加。表达能力更强但内存开销显著更高,现代大模型未采用。
- **Highway Networks**(Srivastava et al. 2015):残差连接的前身,用可学习门控 $y = T(x)\odot F(x) + (1-T(x))\odot x$。ResNet 相当于将 $T$ 固定为 $1$ 的极简化,证明**门控其实并不必要**——恒等即可。
- **ReZero**(Bachlechner et al. 2020):$y = x + \alpha F(x)$,$\alpha$ 是初始化为 0 的可学习标量,让训练最初完全等价于恒等映射,随训练逐步"打开"每层。是一种"更极端的残差初始化"思路,少数改造模型使用。

### 常见误区

- **"残差就是把两个张量加起来"** — 加法只是形式,关键是**加号左边必须是主通路的恒等映射**(至少在残差分支之外),一旦被 LN/激活/scaling 挡住就失去"梯度直通"性质。Post-LN vs Pre-LN 的核心差异就在这里。
- **"残差是为了做 ensemble"** — 集成视角是事后解释,不是设计动机;设计动机是缓解深层梯度消失与优化困难。
- **"没有 BN/LN 也可以随便加残差"** — 早期 ResNet 若去掉 BN,残差本身不够稳定;Transformer 靠 LN 保持每子层输入分布合理。归一化与残差是**配套使用**的。
- **"维度不匹配时用零填充就行"** — CV 领域 ResNet 在下采样处会做 $1\times 1$ 卷积匹配维度;Transformer 里所有子层保持 $d_{\text{model}}$ 不变,残差天然维度对齐,不需要投影快捷方式(shortcut projection)。若你在 Transformer 里遇到需要投影快捷方式的场景,说明架构设计出错了。

## 和我的项目的关系

残差连接本身与我的项目没有直接对应,但它体现的"**主通路 + 增量修正**"设计范式值得借鉴:

- **[[EvidenceFirst]] 的架构直觉**:LLM 生成的答案可视为"主通路",证据验证与状态机是"增量修正";用状态机每次只**修正**答案的置信度而非重生成答案,类似残差"只学差量"的思路,能保持稳定性同时增强能力。
- **[[TripleChecker]] 的 pipeline 组合**:多个检查器(NLI、KG 一致性、来源核验)输出的分数**加和/加权融合**而不是"级联覆盖",是残差式融合;级联覆盖会让一个模块的错误传递到后续,加和融合则每个模块独立贡献增量。
- **调试直觉**:发现 LLM 生成质量突然下降时,如果是"完全跑偏",说明主通路(基础生成)出问题;如果是"细节错误",说明增量修正(FFN 事实检索)出问题。这种"分层归因"思路和残差 stream 的读写视角同源。
- **面试与解释**:"为什么 Transformer 能训练几十层?"标准答案里必须包含残差;能补一句"主残差通路必须保持恒等,这是 Pre-LN 相对 Post-LN 更稳定的原因",展示对结构细节的敏感度。

## 交叉引用

- [[Transformer 架构 Architecture]]
- [[Transformer 自注意力机制]]
- [[多头注意力 Multi-Head Attention]]
- [[前馈网络 FFN Feed-Forward Network]]
- [[层归一化 LayerNorm BatchNorm]]
- [[激活函数 Activation Functions]]
- [[卷积神经网络 CNN]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-16: 首次建页。给出 $y=x+F(x)$ 定义与梯度直通推导、"学残差比学 $H(x)$ 容易"的直觉、Pre-LN 与 Post-LN 在残差通路上的差异、residual stream 与 mechanistic interpretability 视角、与 DenseNet/Highway/ReZero 的对比,以及四条常见误区。
