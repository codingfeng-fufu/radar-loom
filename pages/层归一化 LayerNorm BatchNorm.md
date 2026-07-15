---
摘要: BatchNorm与LayerNorm通过不同归一化维度稳定神经网络训练。
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制, 基础]
---

# 层归一化 LayerNorm BatchNorm

## 核心内容

BatchNorm(BN)与 LayerNorm(LN)都是"网络内部归一化"——在前向路径中把某一层的激活分布调整到均值 0、方差 1,再用可学习的仿射参数 $\gamma,\beta$ 恢复表征能力。两者数学操作几乎相同,**唯一的差别在于"沿哪些维度求均值方差"**,而这个选择决定了它们的适用范围。宏观直觉:BN "看群体"(batch 内所有样本的同一特征),LN "看个体"(单个样本的所有特征)。BN 是 CV/CNN 的标配,LN 是 Transformer/NLP 的标配。它们的通用作用:抑制层间协变量偏移的表面症状、**平滑损失面**从而支持更大学习率、缓解梯度消失/爆炸,并降低对权重初始化的敏感度。归一化的整体家族参见 [[归一化 Normalization]]。

### 数学定义

统一表达是:

$$
\hat{x}_i = \frac{x_i - \mu}{\sqrt{\sigma^2 + \epsilon}},\qquad y_i = \gamma\,\hat{x}_i + \beta
$$

$\epsilon$ 是防除零的数值稳定项(常取 $10^{-5}$),$\gamma,\beta$ 是可学习参数。区别只在 $\mu,\sigma^2$ 沿哪些维度求。

**BatchNorm**(Ioffe & Szegedy, 2015)。对 CNN 输入 $x\in\mathbb{R}^{N\times C\times H\times W}$($N$ 批大小,$C$ 通道,$H\times W$ 空间维),BN 沿 $(N,H,W)$ 三个维度求统计量,**每个通道一组** $\mu_c,\sigma_c^2$:

$$
\mu_c = \frac{1}{N H W}\sum_{n,h,w} x_{n,c,h,w},\qquad
\sigma_c^2 = \frac{1}{N H W}\sum_{n,h,w}(x_{n,c,h,w}-\mu_c)^2
$$

可学习参数 $\gamma_c,\beta_c$ 也是每通道一组,共 $2C$ 个参数。

**LayerNorm**(Ba, Kiros & Hinton, 2016)。对 Transformer 的序列输入 $x\in\mathbb{R}^{N\times T\times d}$($N$ 批,$T$ 序列长度,$d$ 隐藏维),LN 沿最后一维 $d$ 求统计量,**每个 (n,t) 位置一组** $\mu_{n,t},\sigma_{n,t}^2$:

$$
\mu_{n,t} = \frac{1}{d}\sum_{i=1}^{d} x_{n,t,i},\qquad
\sigma_{n,t}^2 = \frac{1}{d}\sum_{i=1}^{d}(x_{n,t,i}-\mu_{n,t})^2
$$

可学习参数 $\gamma\in\mathbb{R}^d,\beta\in\mathbb{R}^d$ 在所有 $(n,t)$ 位置共享,共 $2d$ 个参数。

一句话对比:**BN 的统计量沿"batch × 空间/时间"聚合,LN 沿"特征"聚合。**

### 具体数值例子

取一个 mini-batch $x\in\mathbb{R}^{2\times 3}$(两个样本,每样本 3 维特征):

$$
x = \begin{bmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{bmatrix}
$$

**BN 处理(沿 batch 方向,每列独立)**:

- 特征 0: $[1,4]$,$\mu=2.5,\sigma^2=2.25,\sigma=1.5$,归一化为 $[-1,\ 1]$。
- 特征 1: $[2,5]$,$\mu=3.5,\sigma=1.5$,归一化为 $[-1,\ 1]$。
- 特征 2: $[3,6]$,$\mu=4.5,\sigma=1.5$,归一化为 $[-1,\ 1]$。

结果(忽略 $\gamma,\beta,\epsilon$):

$$
\text{BN}(x) = \begin{bmatrix} -1 & -1 & -1 \\ 1 & 1 & 1 \end{bmatrix}
$$

**LN 处理(沿特征方向,每行独立)**:

- 样本 0: $[1,2,3]$,$\mu=2,\sigma^2=\frac{2}{3},\sigma\approx 0.816$,归一化为 $[-1.225,\ 0,\ 1.225]$。
- 样本 1: $[4,5,6]$,$\mu=5,\sigma\approx 0.816$,归一化为 $[-1.225,\ 0,\ 1.225]$。

结果:

$$
\text{LN}(x) \approx \begin{bmatrix} -1.225 & 0 & 1.225 \\ -1.225 & 0 & 1.225 \end{bmatrix}
$$

**观察**:

- BN 抹掉了"列间"的绝对差异——每列输出都是 $[-1,1]$,但保留了"同一样本相对其他样本"的位置信息(样本 0 在每列都比样本 1 小)。
- LN 抹掉了"样本间"的整体尺度差异(两个样本的输出完全一样),但保留了"同一样本内部"的相对结构(样本 0 从小到大,样本 1 也从小到大)。
- 如果特征 2 是"数量级差很多"的量纲(比如年收入 vs 年龄),BN 能把它们统一到可比的尺度;LN 却会把"年收入 200000"这个数字压回样本自己的均值附近,反而丢失了跨样本的相对信息——这正是**BN 更适合 CV(通道量纲一致)、LN 更适合 NLP(样本级绝对尺度不重要)**的直觉根源。

### 训练与推理:BN 的移动平均陷阱

BN 训练时用当前 mini-batch 的 $\mu,\sigma^2$;推理时若还用"batch 内统计",单条输入会得到 $\mu=x,\sigma=0$ 从而爆炸。因此 BN 层内部维护:

$$
\bar\mu \leftarrow (1-m)\,\bar\mu + m\,\mu_{\text{batch}},\qquad
\bar\sigma^2 \leftarrow (1-m)\,\bar\sigma^2 + m\,\sigma^2_{\text{batch}}
$$

其中 $m$ 是动量(PyTorch 默认 0.1)。**推理时改用 $\bar\mu,\bar\sigma^2$**,与批大小、单样本推理无关。

工程后果:

- PyTorch 里必须 `model.eval()`(内部调用 `BatchNorm2d.eval()`)才会切换到移动平均。忘记这一步是最常见的 BN 部署 bug——线上单样本推理时用 batch 内统计,$\sigma\to 0$ 导致输出全部塌到 $\gamma\cdot 0+\beta=\beta$。
- 训练 batch size 特别小(比如 GPU 显存受限只能开 batch=2)时,$\mu,\sigma$ 估计噪声大,BN 反而伤性能。这也是 GroupNorm 和 LN 的起点。
- 分布式训练要用 **SyncBatchNorm** 聚合各卡的统计量,否则每卡各自算,等价于把有效 batch size 缩小。

LN 因为完全在单样本内部计算,**训练与推理行为完全一致**,不需要维护移动平均,不受 batch size 影响。这是 Transformer 选择 LN 的一大工程理由。

### 为什么 Transformer 选 LayerNorm 而不是 BatchNorm

三条硬约束:

1. **变长序列**:NLP 输入序列长度 $T$ 不一,batch 内做 padding。BN 若沿 $T$ 维度聚合,padding 位置会污染统计量;要做掩码就要在每个 BN 层里传掩码,工程复杂度和错误率飙升。LN 不涉及 batch 内跨样本聚合,天然不受影响。
2. **小 batch 训练**:LLM 预训练每卡 batch size 可能很小(靠梯度累积扩大有效 batch),BN 在小 batch 下噪声大;LN 无此问题。
3. **在线/流式推理**:对话式 LLM 推理是一个 token 一个 token 出,batch=1 是常态;BN 的移动平均要额外维护、还有分布偏移风险,LN 没有这层负担。

此外,自回归解码时 BN 会在时间维度上引入未来 token 的信息(因为要沿 $T$ 求均值),违反因果掩码;LN 只在单 token 的特征维内计算,不破坏因果性。

### Pre-LN 与 Post-LN

Transformer 里 LN 的**位置**同样重要。原始 Transformer(Vaswani et al., 2017)采用 **Post-LN**:

$$
y = \text{LN}\bigl(x + \text{Sublayer}(x)\bigr)
$$

即残差相加之后再归一化。这在浅层 Transformer 上工作良好,但深层时训练极不稳定,需要精心设计学习率 warmup。

现代 LLM(GPT-2 起、LLaMA 系列、大多数开源模型)改用 **Pre-LN**(Xiong et al., 2020 *On Layer Normalization in the Transformer Architecture*, ICML):

$$
y = x + \text{Sublayer}\bigl(\text{LN}(x)\bigr)
$$

即先归一化再进子层,残差通路上是恒等映射。好处:

- 梯度可以直接通过残差通路流回浅层,不经过 LN 的缩放,深层训练稳定得多,可以省掉 warmup 或大幅缩短。
- 但残差路径不断累加不归一化的量,末端激活会漂,所以模型最后通常加一个额外的 **final LN**(在所有 block 之后、投影到词表之前)。

Post-LN 训练难但**推理数值范围更收敛**;Pre-LN 训练稳但**最终表示分布更松**。这是深层网络的经典 trade-off,和 [[Transformer 自注意力机制]] 的稳定性讨论同源。

### RMSNorm:LayerNorm 的算力简化

LLaMA、T5 等采用 **RMSNorm**(Zhang & Sennrich, 2019),它省掉 LN 的减均值步骤,只除以均方根:

$$
\text{RMSNorm}(x) = \gamma \cdot \frac{x}{\sqrt{\frac{1}{d}\sum_{i=1}^{d} x_i^2 + \epsilon}}
$$

对比 LN 少了一次求均值和一次减法,理论运算量减少约 7~10%,在 100B+ 参数的模型上累积成明显的训练/推理加速。实证上 RMSNorm 的性能与 LN 相当甚至略好——原论文的解释是"减均值不是 LN 起作用的关键,重新缩放才是"。

### 其他归一化家族对照

| 名称 | 归一化维度(4D 情形) | 每样本每通道独立? | 典型场景 |
|------|---------------------|------------------|---------|
| BatchNorm | $(N,H,W)$ | 每通道一组统计量 | CNN、ResNet、大批量视觉 |
| LayerNorm | $(C,H,W)$ 或最后一维 | 每样本一组 | Transformer、NLP、小批量 |
| InstanceNorm | $(H,W)$ | 每样本每通道 | 风格迁移、GAN |
| GroupNorm | 通道分组内 $(g,H,W)$ | 每样本每组 | 小 batch 视觉、检测/分割 |
| RMSNorm | 最后一维,无中心化 | 每样本一组 | LLaMA、T5、现代 LLM |

一句话规律:归一化维度越"个体化"(不跨 batch),对 batch size 越鲁棒,但抓不到"整个数据集在这个特征上的整体尺度"。

### 常见陷阱

- **推理时忘记 `model.eval()`**:BN 使用当前 batch 统计,单条推理输出被压缩到常数附近。
- **BN 的 batch size 太小**(如 1 或 2):方差估计噪声主导训练,考虑换 GroupNorm/LN。
- **多卡训练不用 SyncBN**:每卡独立算 BN,有效 batch 被切小,大模型上性能会掉。
- **在残差前后混用 Pre-LN/Post-LN**:同一网络里不一致会让训练轨迹难以复现。
- **LN 的 axis 写错**:PyTorch `nn.LayerNorm(normalized_shape=d)` 默认在最后 $d$ 维归一化,若把整个 `[T,d]` 传进去会同时沿序列维聚合,变成一种奇怪的"per-sample BN"变体,静默出错。
- **数据预处理阶段错用 BN 思路**:在数据 pipeline 里"每个 batch 重新算均值方差再缩放"不是 BN 而是数据泄漏,详见 [[归一化 Normalization]] §测试集泄漏。
- **RMSNorm 与 LN 混用**:预训练用 RMSNorm、微调时替换成 LN(或反之)会破坏权重语义,$\gamma$ 参数尺度完全不同。

### "为什么有效"的现代解释

原论文(Ioffe & Szegedy, 2015)提出的解释是"减少内部协变量偏移(Internal Covariate Shift)"——每层输入分布随训练变化,归一化把它固定住。但后续研究(Santurkar et al., 2018 *How Does Batch Normalization Help Optimization?*, NeurIPS)通过实验证明:即便人为破坏了归一化后的分布(注入随机噪声重新引入偏移),BN 依然有效。真正的作用是**平滑了损失面 landscape**,让梯度尺度和方向更均匀,允许更大的学习率、降低对初始化的依赖。

这一"机制解释被推翻但方法保留"是深度学习经验主导领域的典型案例。工程上关心"能不能用、什么时候用",理论解释仍在演化。

## 和我的项目的关系

LayerNorm 本身和我的研究没有直接关系,但它的设计理念——**"在不确定性中找确定性的锚点"**——和我的工作有深层的共鸣。LayerNorm 把每层的激活分布固定住,让训练过程从随机游走变成有约束的优化;[[EvidenceFirst]] 把每个样本的推理状态固定成 5 种离散状态(见 [[确定性状态机 Deterministic State Machine]]),让 RAG 系统从"输出一个字符串然后祈祷它是对的"变成"输出一个字符串同时告诉你它有多大概率是对的"。两者都是在不确定性系统里引入确定性的约束——一个在神经网络内部,一个在系统架构层面。

工程上的直接关联更少但仍存在:

- 若我在 [[TripleChecker]] 里用一个小型分类头判断三元组是否可信,输入是长度不定的证据片段,分类头前的归一化几乎一定是 LN 而不是 BN——出于变长和小批量的同样原因。
- 若我 fine-tune 一个 LLaMA 系列模型做证据打分,需要意识到它用的是 RMSNorm 而不是 LN;`γ` 参数在两种归一化下的语义不同,权重迁移或 LoRA 目标层选择时都要匹配。

## 交叉引用

- [[归一化 Normalization]]
- [[Transformer 自注意力机制]]
- [[Robust Scaler 鲁棒缩放]]
- [[确定性状态机 Deterministic State Machine]]
- [[大模型机制与推理 LLM Mechanisms]]

## 更新记录

- 2026-07-04: 首次建页
- 2026-07-15: 大幅扩写。补充 BN/LN 的完整数学定义、$2\times 3$ 数值例子、训练/推理行为差异、Transformer 选 LN 的三条硬约束、Pre-LN 与 Post-LN 对比、RMSNorm 简介、归一化家族对照表、常见陷阱与"为什么有效"的现代解释。
