---
摘要: Adam结合动量与RMSprop的一阶矩、二阶矩自适应学习率优化器，是深度学习默认优化器
来源: https://arxiv.org/abs/1412.6980
信度: 高
首次记录: 2026-08-09
tags: [基础, LLM机制]
---

# Adam优化器 Adam Optimizer

## 核心内容

Adam(Adaptive Moment Estimation,Kingma & Ba,ICLR 2015)是一种**自适应学习率的一阶梯度优化器**,为随机目标函数而设计。它把两条原本独立的改进路线合到一起:**Momentum** 用梯度的一阶滑动平均积累"方向惯性",**RMSprop** 用梯度平方的滑动平均逐坐标缩放学习率。Adam 在此基础上加入**偏差修正(bias correction)**,补偿零初始化导致的早期矩估计偏向零的问题,并在论文里给出了收敛性证明。它通常是 Transformer、CNN、RNN 等深度网络的默认优化器,也是现代 LLM 训练栈(经 AdamW 修正权重衰减后)的起点。它解决的核心问题是:SGD 在病态条件、稀疏梯度、非平稳目标下学习率难以调、收敛慢;Adam 用少量额外状态($m_t,v_t$)和超参数($\beta_1,\beta_2,\epsilon$)换得对超参数更鲁棒、跨坐标自适应的更新。

### 算法推导

设待优化参数为 $\theta_t$,随机小批量上计算的目标函数梯度为 $g_t=\nabla_\theta L(\theta_{t-1})$。Adam 维护两个与 $\theta$ 同形状的状态向量:

- $m_t$:梯度的**一阶矩**(均值)指数滑动平均,类似 Momentum 的速度项;
- $v_t$:梯度平方的**二阶原始矩**(非中心化方差)指数滑动平均,类似 RMSprop 的平方梯度。

更新规则为:

$$
m_t = \beta_1 m_{t-1} + (1-\beta_1)\,g_t
$$

$$
v_t = \beta_2 v_{t-1} + (1-\beta_2)\,g_t^{\odot 2}
$$

其中 $\odot$ 表示逐元素平方。由于 $m_0=v_0=0$,在训练早期两个矩都偏向零,Adam 做偏差修正:

$$
\hat{m}_t = \frac{m_t}{1-\beta_1^t},\qquad
\hat{v}_t = \frac{v_t}{1-\beta_2^t}
$$

当 $t\to\infty$ 时 $\beta^t\to 0$,修正项趋近 1,因此偏差修正只在早期(<1000 步)显著。最终参数更新:

$$
\theta_t = \theta_{t-1} - \frac{\alpha}{\sqrt{\hat{v}_t}+\epsilon}\,\hat{m}_t
$$

$\alpha$ 是基础学习率,分母 $\sqrt{\hat{v}_t}+\epsilon$ 是逐坐标的自适应缩放:某坐标历史梯度大,该坐标分母就大,实际步长被压小;梯度小的坐标反而获得相对更大的更新。$\epsilon$ 防止除零,同时约束单步更新的下界,典型取 $10^{-8}$。

### 超参数与典型取值

| 超参 | 含义 | 论文默认 | 工程经验 |
|------|------|----------|----------|
| $\alpha$ | 基础学习率 | $0.001$ | Transformer 预训练常用 $1\times10^{-4}\sim 3\times10^{-4}$,配 warmup |
| $\beta_1$ | 一阶矩衰减 | $0.9$ | 通常保持默认;部分实现对 BERT 用 $0.9$ |
| $\beta_2$ | 二阶矩衰减 | $0.999$ | 大模型/低精度训练有时调到 $0.95$ 或 $0.995$,以平滑梯度尖峰 |
| $\epsilon$ | 数值稳定项 | $10^{-8}$ | 混合精度训练常需放大到 $10^{-6}\sim 10^{-5}$,避免 fp16 下 underflow |

$\beta_1,\beta_2$ 越接近 1,滑动平均窗口越长,统计量越平滑但对梯度分布变化的响应越慢;$\beta_2$ 过高会让 $v_t$ 在梯度突变时跟不上,反而引入陈旧的尺度估计。

### 直觉:为什么有效

- **惯性与阻尼解耦**:$m_t$ 决定"往哪走"(方向),$v_t$ 决定"每维走多快"(步长)。SGD 把两者绑在一起,而 Adam 允许方向快变、步长慢变,适应损失面的不同曲率方向。
- **对角预处理的廉价近似**:$\sqrt{\hat{v}_t}^{-1}$ 可以看作对梯度做了一次对角 Fisher/曲率近似的预条件。对稀疏特征(NLP 中的低频词、推荐中的长尾 ID),该特征只在出现时有梯度,但 $v_t$ 维持较小值,因此一旦出现就能获得较大更新——这是 Adam 在稀疏场景显著优于 SGD 的关键。
- **不变性视角**:在参数重缩放 $\theta\to c\theta$ 下,Adam 的更新方向在稳定状态近似不变(Reddi et al., 2018 对此有更严格讨论),这降低了对初始化与特征量纲的敏感度。

### 收敛性与已知问题

原论文在 Regret 框架下证明 Adam 的遗憾界为 $O(\sqrt{T})$,与自适应在线优化的下界一致。但后续工作指出了几个重要问题:

1. **Adam 可能不收敛**。Reddi et al., ICLR 2018 *On the Convergence of Adam and Beyond* 构造了一维反例:当某一步的梯度 $g_t$ 使 $v_t$ 突然小于历史 $v_{t-1}$ 时(即 $\beta_2 v_{t-1}+(1-\beta_2)g_t^2<v_{t-1}$),自适应学习率反而上升,可能越过最小值。他们提出 **AMSGrad**,用 $v_t^{\max}=\max(v_{t-1}^{\max},v_t)$ 替代 $v_t$,保证学习率单调非增。
2. **权重衰减与 L2 正则不等价**。在自适应梯度下,把 $\lambda\theta$ 直接加进梯度(L2 正则)会被 $\sqrt{v_t}$ 缩放,导致权重大的参数衰减反而少。Loshchilov & Hutter, ICLR 2019 *Decoupled Weight Decay Regularization* 提出 **AdamW**,把权重衰减从梯度里解耦:

$$
\theta_t = \theta_{t-1} - \eta_t\!\left(\frac{\hat{m}_t}{\sqrt{\hat{v}_t}+\epsilon}+\lambda\,\theta_{t-1}\right)
$$

   AdamW 是 BERT、GPT、LLaMA 等几乎所有现代大模型实际使用的变体。许多框架里的 `Adam(weight_decay=...)` 在历史上做的是 L2 而非解耦衰减,使用时需要确认实现。

3. **泛化差距**。部分研究(Wilson et al., 2017 *The Marginal Value of Adaptive Gradient Methods*)观察到 Adam 在视觉任务上的泛化有时差于精调的 SGD+momentum;但在 NLP/LLM 与稀疏场景下 Adam 家族几乎是唯一实用选择。
4. **内存开销**:每个参数额外维护 $m_t,v_t$ 两个状态,显存占用是 SGD+momentum 的 2 倍、纯 SGD 的 3 倍。千亿模型训练中这是优化器状态显存的主要部分,因此催生 8-bit Adam、Adafactor(只存二阶矩的分解形式)、ZeRO 分片等工程方案。

### 与 SGD、Momentum、RMSprop 的对照

| 方法 | 一阶状态 | 二阶状态 | 自适应学习率 | 偏差修正 | 典型场景 |
|------|----------|----------|--------------|----------|----------|
| SGD | 无 | 无 | 否 | — | 凸优化、精调 baseline |
| Momentum | $m_t=\beta m_{t-1}+g_t$ | 无 | 否 | — | CV 大 batch 训练 |
| RMSprop | 无 | $v_t=\beta v_{t-1}+(1-\beta)g_t^2$ | 是 | 否 | RNN、非平稳目标 |
| Adam | $m_t$ | $v_t$ | 是 | 是 | 通用默认、LLM |
| AdamW | $m_t$ | $v_t$ | 是 | 是 | 现代 Transformer/LLM |
| AMSGrad | $m_t$ | $v_t^{\max}$ | 是(单调) | 是 | 对收敛严格敏感的场景 |

### 常见陷阱

- **学习率仍需调**:Adam "自适应"不等于不用调学习率。基础学习率 $\alpha$ 与 warmup、schedule 仍然是 LLM 训练最敏感的超参之一。
- **$\epsilon$ 在 fp16/bf16 下太小**:导致 $\sqrt{v_t}$ underflow 为 0,实际步长爆炸;混合精度训练通常把 $\epsilon$ 放到 $10^{-6}$ 或以上。
- **把 weight decay 与 L2 混淆**:用 Adam 时务必用 AdamW 风格的解耦衰减,否则正则强度被自适应项"吞掉"。
- **梯度累积下的偏差修正**:部分实现按优化器 step 而非 micro-step 计 $t$,梯度累积会改变 $t$ 的含义,需要核对实现。
- **与 BatchNorm 的相互作用**:Adam 对梯度尺度的自适应并不能替代归一化,深层网络仍依赖 [[层归一化 LayerNorm BatchNorm]] 稳定激活分布,二者共同决定训练动态。
- **$\beta_2=0.999$ 对突变分布反应慢**:强化学习、GAN、对抗训练这类梯度分布快速变化的场景,有时需要降低 $\beta_2$ 或换 RMSprop。

## 和我的项目的关系

Adam 本身不是我的研究对象,但它是几乎所有实验栈的底层依赖,与几个项目有工程与方法层面的关联:

- **[[TripleChecker]] / [[EvidenceFirst]]**:若用 LoRA 或全参微调小模型做证据打分、claim 分类,默认起点就是 AdamW($\beta_1=0.9,\beta_2=0.95$ 或 $0.999$),需要注意学习率 warmup 与权重衰减分组(bias、LayerNorm 参数通常不做衰减)。
- **[[CoMaGRAG]]**:涉及 KG 与 RAG 的图神经网络训练时,稀疏索引/关系嵌入会产生高度稀疏的梯度,这正是 Adam 家族相比 SGD 优势最大的场景;但需要关注 $v_t$ 对低频嵌入的更新是否过激。
- 更深层的方法论共鸣:Adam 用**滑动平均 + 偏差修正**把"早期不可靠的估计"和"后期稳态估计"统一在同一更新式里,这与 EvidenceFirst 中"早期证据不足时显式标记低置信度、后期积累足够证据后再下结论"的状态机思路异曲同工——都是在不打断流程的前提下,对估计的可靠性做时间维度上的自适应修正。

## 交叉引用

- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[大模型机制与推理 LLM Mechanisms]]
- [[层归一化 LayerNorm BatchNorm]]
- [[Transformer 架构 Architecture]]
- [[后训练 Post-training]]
- [[过拟合 Overfitting]]

## 更新记录

- 2026-08-09: 首次建页。覆盖 Adam 的算法推导(一阶/二阶矩、偏差修正、参数更新)、超参默认值与工程调整、"为什么有效"的直觉、AMSGrad/AdamW 两项关键后续、与 SGD/Momentum/RMSprop 的对照表,以及混合精度与权重衰减等常见陷阱。
