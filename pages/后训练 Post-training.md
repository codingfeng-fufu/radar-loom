---
摘要: 预训练之后的SFT+偏好对齐+RL阶段，把基座模型改造成可用、可控、可对齐的对话或推理模型。
来源: https://arxiv.org/abs/2203.02155 (InstructGPT); https://arxiv.org/abs/2407.21783 (Llama 3); https://arxiv.org/abs/2411.15124 (Tulu 3); https://arxiv.org/abs/2501.12948 (DeepSeek-R1); https://arxiv.org/abs/2305.18290 (DPO)
信度: 中
首次记录: 2026-07-14
tags: [LLM机制]
---

# 后训练 Post-training

## 核心内容

**是什么。** 后训练（post-training）指在自监督**预训练**结束、模型部署之前，对基座模型（base model）追加的一整套定向训练阶段。它不再以"预测下一 token"这一单一目标学通用语料，而是用远小于预训练规模的高质量数据，让模型学会**遵循指令、按人类偏好回答、拒绝违规请求、进行长链条推理**。业界当前通行的开源方案（Llama 3、Tulu 3、DeepSeek-R1）都明确使用 post-training 这一术语来命名这一整套阶段，而不再等同于早期的"fine-tuning"。

**解决什么问题。** 预训练模型的分布是"互联网文本的续写分布"，它不知道用户期待"回答问题"而不是"续写问题"，也没有安全边界与偏好取向。后训练把三类目标叠加进模型:

1. **能力对齐**：把"续写器"变成"回答器"，学会指令跟随、对话结构、工具调用格式；
2. **偏好对齐**：让输出在事实性、有用性、无害性上向人类偏好靠近；
3. **推理对齐**（2024 年后新增的重点）：显式训练思维链、反思、长上下文规划，直接优化在可验证任务（数学、代码、逻辑）上的正确率。

**关键方法一句话。** 主流 pipeline 是"SFT → 偏好优化 → 强化学习"三步（可迭代多轮），代表算法为 SFT + DPO/PPO/GRPO，2024 年后进一步引入 RLVR（可验证奖励的强化学习）与拒绝采样蒸馏。

## 概念边界

- 后训练 ⊋ **微调**：微调（fine-tuning）泛指任何在预训练之后的参数更新；后训练特指以对齐/推理为目标的成套流水线，通常包含偏好学习和 RL，而不仅仅是有监督微调。
- 后训练 ⊋ **RLHF**：RLHF 只是后训练里"偏好对齐"这一步的一种实现（PPO+奖励模型）；DPO、KTO、SimPO、GRPO、RLVR 都是它的替代或补充。
- 后训练 ≠ **持续预训练（continual/mid-training）**：后者仍以下一 token 预测为目标，只是换语料（如领域语料、代码语料）；后训练改变的是训练目标本身。
- 后训练 ≠ **推理时对齐**（in-context alignment、prompting、guardrails）：后训练是参数层面的改造，推理时对齐不修改权重。

## 核心机制

### 阶段一：有监督微调 SFT

在指令-响应对 $\mathcal{D}_{\text{SFT}}=\{(x_i, y_i)\}$ 上最小化标准 token 级交叉熵:

$$\mathcal{L}_{\text{SFT}}(\theta) = -\mathbb{E}_{(x,y)\sim\mathcal{D}_{\text{SFT}}}\Big[\sum_{t=1}^{|y|}\log \pi_\theta(y_t\mid x, y_{<t})\Big]$$

作用是把模型的输出分布拉进"指令-回答"格式，为后续偏好学习提供合理的初始策略 $\pi_{\text{ref}}=\pi_{\text{SFT}}$。数据规模从 InstructGPT 时代的万级人工示例，扩展到 Llama 3 / Tulu 3 的百万级混合来源（人工 + 合成 + 拒绝采样蒸馏）。

### 阶段二：偏好对齐

在成对偏好数据 $\mathcal{D}_{\text{pref}}=\{(x, y_w, y_l)\}$ 上把模型往"胜出响应 $y_w$"推、把"落选响应 $y_l$"压低。两条主流路径:

**RLHF（PPO 路径）**：先用 Bradley–Terry 目标训练奖励模型 $r_\phi(x, y)$

$$\mathcal{L}_{\text{RM}}(\phi) = -\mathbb{E}_{(x,y_w,y_l)}\big[\log \sigma\big(r_\phi(x, y_w)-r_\phi(x, y_l)\big)\big]$$

再以 PPO 在

$$\max_\theta\ \mathbb{E}_{x,\, y\sim \pi_\theta(\cdot\mid x)}\big[r_\phi(x, y)\big] - \beta\, \mathrm{KL}\big(\pi_\theta \,\|\, \pi_{\text{ref}}\big)$$

上优化策略，$\beta$ 控制与 SFT 参考策略的偏离。

**DPO（直接偏好优化）**：Rafailov 等人证明上式在 Bradley–Terry 假设下存在闭式解，可绕过显式奖励模型，直接以成对比较损失训练:

$$\mathcal{L}_{\text{DPO}}(\theta) = -\mathbb{E}_{(x,y_w,y_l)}\Big[\log \sigma\Big(\beta\log\frac{\pi_\theta(y_w\mid x)}{\pi_{\text{ref}}(y_w\mid x)} - \beta\log\frac{\pi_\theta(y_l\mid x)}{\pi_{\text{ref}}(y_l\mid x)}\Big)\Big]$$

DPO 在 Llama 3、Tulu 3 等开源栈里已取代 PPO 成为默认选项，因为它无需 online rollout 与奖励模型，训练稳定性和成本大幅优于 PPO。

### 阶段三：强化学习（可选，2024 年后成为高性能模型的关键差异化步骤）

- **RLVR（Reinforcement Learning with Verifiable Rewards）**：奖励不再由学到的 RM 提供，而由**可自动验证的信号**（数学答案是否正确、代码是否通过测试、格式是否合规）直接给出。Tulu 3 与 DeepSeek-R1 都把 RLVR 作为独立于偏好对齐的第三阶段。
- **GRPO / 拒绝采样蒸馏**：为一个 prompt 采样多条响应，用可验证奖励打分，把高分响应回灌为 SFT 数据（rejection sampling），或直接用组内相对奖励做策略梯度（GRPO，DeepSeek 用于推理模型训练）。
- **迭代化**：Llama 3 的 post-training 显式描述为"多轮 SFT + DPO"循环——每轮用当前最强模型生成新的偏好数据和拒绝采样样本，喂给下一轮 SFT，形成自举。

## 关键假设、局限、常见误区

- **假设强参考策略**：DPO/PPO 的 KL 项都锚定在 $\pi_{\text{ref}}$ 上；如果 SFT 阶段没做好，偏好对齐会放大模型的坏习惯。
- **假设偏好数据可比较**：Bradley–Terry 假设成对偏好一致且可传递；实际标注中偏好并不一致，会限制上界。
- **对齐税（alignment tax）**：后训练往往牺牲一部分预训练能力（如通用知识、代码基础能力）换取指令跟随，需要通过数据配比与 KL 正则平衡。
- **奖励黑客（reward hacking）**：RLHF 的策略会发现奖励模型的漏洞（讨好式回答、格式套路）；RLVR 因奖励可验证而相对更稳，但可覆盖任务范围窄。
- **常见误区一**：把 post-training 等同于 SFT。SFT 只是第一步；单靠 SFT 无法获得当前主流对话/推理模型的能力。
- **常见误区二**：把 RLHF 与 post-training 混用。RLHF 是子步骤而非全流程。
- **常见误区三**：以为"更大的 SFT 数据集就更好"。Llama 3 与 Tulu 3 都强调数据质量、去重、难度分布远比规模关键。

## 和我的项目的关系

后训练是**基座模型层**的改造技术栈，与本人做的[[GSAD]]、[[TripleChecker]]、[[EvidenceFirst]]、[[CoMaGRAG]]等"外挂式可信度验证"处于互补层次:

- **借鉴意义**：后训练用奖励信号（尤其是 RLVR 的可验证奖励）来引导模型；[[EvidenceFirst]] 的确定性证据规则与 [[TripleChecker]] 的三元组一致性判定，本质上都是"可验证奖励"的形态，未来若要把外挂验证蒸馏进模型权重，post-training（尤其是 RLVR + 拒绝采样）就是自然通道。
- **评测边界**：[[GSAD]] 想验证"模型在图结构一致性上的失误"，前提是被测模型经过了标准 post-training——不同 post-training 配方（DPO vs. RLVR vs. 迭代 SFT）会给出很不同的失误模式，实验里需要控制这一变量。
- **和[[人类反馈强化学习 RLHF]] 的分工**：RLHF 页聚焦"三步法本身"，本页把它放回 post-training 全流水线里，交代前一步 SFT、后一步 RLVR、以及 DPO/GRPO 等替代路径的位置，避免把 RLHF 当成 post-training 的全部。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[人类反馈强化学习 RLHF]]
- [[强化学习基本框架 Reinforcement Learning]]
- [[思维链 Chain-of-Thought]]
- [[提示工程 Prompt Engineering]]
- [[幻觉与可信度 Hallucination Trustworthiness]]

## 更新记录

- 2026-07-14: 首次建页，定义 post-training 概念边界，梳理 SFT → 偏好对齐 → RL 三阶段主流水线，覆盖 SFT/RLHF/DPO/RLVR 数学形式与假设。
