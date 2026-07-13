---
摘要: 扩散模型通过前向加噪与反向去噪学习数据分布,训练目标是分层VAE的ELBO简化形式,已成为主流生成模型。
来源: 对话记录 2026-07-13
信度: 高
首次记录: 2026-07-13
tags: [基础]
---

# 扩散模型 Diffusion Models DDPM

## 核心内容

扩散模型(Diffusion Models,以 DDPM 2020 为代表)是一类**基于逐步加噪-去噪的深度生成模型**,目前在图像、视频、音频、分子生成等领域占据主导地位,也是 Sora / Stable Diffusion / DALL·E 3 的核心。

**两条马尔可夫链**:
- **前向过程 $q(x_t\mid x_{t-1})$**:固定、无参、逐步向真实样本 $x_0$ 加高斯噪声,经 $T$ 步(常见 $T=1000$)几乎退化为纯噪声 $x_T\approx\mathcal{N}(0,I)$。用重参数化可写成一次到位:$x_t=\sqrt{\bar\alpha_t}x_0+\sqrt{1-\bar\alpha_t}\epsilon$,其中 $\epsilon\sim\mathcal{N}(0,I)$,$\bar\alpha_t$ 由预定义 $\beta_t$ 累积得到。
- **反向过程 $p_\theta(x_{t-1}\mid x_t)$**:由神经网络(通常是 U-Net,视频/文本序列用 DiT / Transformer)参数化,从 $x_T$ 逐步去噪到 $x_0$。

**训练目标——分层 VAE 的 ELBO 退化**:把扩散过程看作一个"T 步、共享参数、每步高斯"的分层 [[变分自编码器 VAE Variational Autoencoder]],ELBO 展开重参数化后,惊人地简化为**每步预测该步添加的噪声 ε**:

$$
\mathcal{L}_{\text{simple}}=\mathbb{E}_{t,x_0,\epsilon}\left[\lVert\epsilon-\epsilon_\theta(x_t,t)\rVert_2^2\right]
$$

一个纯 MSE 损失。这就是"扩散模型比 VAE 好训"的根源:目标从难以稳定的 KL + 重构变成了逐步去噪回归。EM/VAE 的隐变量视角在这里被"分层化 + 时间步条件化"复用——因此把它挂在 [[EM算法 Expectation-Maximization]] → VAE → 扩散这条隐变量链的末端是自洽的。

**采样(推断)**:
- **DDPM 采样**:严格按训练时的马尔可夫链倒推,需 T=1000 步,慢。
- **DDIM**:改成非马尔可夫、确定性 ODE 轨迹,可 20–50 步出图。
- **一致性模型 / 蒸馏**(2023 起):把多步教师蒸馏成 1–4 步学生,推理速度接近 GAN。

**条件生成**:
- **Classifier-free guidance(CFG)**:训练时随机丢弃条件,推断时用 $\epsilon_\theta(x_t,c)$ 与 $\epsilon_\theta(x_t,\varnothing)$ 的线性外推,几乎所有文生图工作都在用。
- **Latent Diffusion(Stable Diffusion 的关键)**:先用 VAE 把图像压到低维隐空间,再在其中做扩散,把 512×512 图像的算力需求砍到 1/64 量级——**一个"VAE 编码器 + 隐空间扩散 + VAE 解码器"的三明治**,直接把 VAE 和扩散串成生产系统。

**与其它生成模型对比**:
- vs GAN:训练稳定、覆盖模式全,但采样慢(GAN 一次前向,扩散多步)。
- vs 自回归 LM:一次生成整张图,不像 LM 逐 token,并行度高;但目前文本上自回归仍是主流。
- vs VAE:样本清晰度显著优于 VAE,代价是采样多步。

**扩展方向**:得分匹配(Score-based SDE,Song & Ermon)与扩散在数学上等价、Flow Matching / Rectified Flow(SD3、Meta MovieGen)是当前更简洁的替代目标、离散扩散用于文本/图。

## 和我的项目的关系

扩散模型不是我 KG / RAG 主线的直接算法,但作为"隐变量 + ELBO"链的收官,以及当前生成式 AI 的绝对主角,几个可挂点:

- **面试骨架收官**:EM → GMM → HMM → LDA → VAE → 对比学习(对照)→ **扩散**,这条线走完,能把统计机器学习、深度生成、自监督表示三大块串成一个统一的"隐变量视角",区分度极高。尤其是"扩散 = 分层 VAE 的 ELBO 退化为逐步去噪回归"这条推导,是把 VAE 段落自然过渡到扩散段落的关键。
- **KG / 三元组生成的潜在路径**:若 [[TripleChecker]] 未来要做"给定实体上下文生成候选三元组"这种生成式补全,离散扩散(D3PM / Multinomial Diffusion)是一条值得关注的路线——比自回归 LM 更容易做全局一致性约束(整张子图一次去噪,而不是逐条自回归)。信度还低,先记着。
- **多模态 RAG 的检索粒度**:Stable Diffusion 的 Latent Diffusion 思路——"先压缩到语义隐空间再操作",可以借鉴到多模态检索的向量库设计:先用 VAE / 对比学习把图像/文档压到低维稠密表示,再在其中做检索或生成,避免直接操作原始像素/长文本的算力浪费。
- **超出主线,谨慎投入**:图像扩散工程量大,除非项目明确转向多模态生成,否则保持"看得懂主流工作、能讲清训练目标推导、能选对采样器"这个深度即可,不必自己训。

## 交叉引用

- [[变分自编码器 VAE Variational Autoencoder]]
- [[EM算法 Expectation-Maximization]]
- [[对比学习 Contrastive Learning]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-13: 首次建页
