---
摘要: 机器遗忘让训练好的模型精确去除特定训练数据的影响,服务隐私合规与被遗忘权。
来源: 对话记录 2026-07-13
信度: 中
首次记录: 2026-07-13
tags: [可信度, 前沿]
---

# 机器遗忘 Machine Unlearning

## 核心内容

机器遗忘(Machine Unlearning)是指在不重新从零训练的前提下,让已训练好的模型 $M$ 精确去除特定训练样本子集 $D_f \subset D$(称为 forget set)、某类知识或某个用户数据的影响,使遗忘后的模型 $M'$ 行为等价或近似等价于"从未见过 $D_f$"训练出来的参照模型 $M_{\text{retrain}}$。

### 形式化

给定训练算法 $\mathcal{A}$、原始数据集 $D$、待遗忘子集 $D_f$、保留集 $D_r = D \setminus D_f$,理想的遗忘算子 $\mathcal{U}$ 满足:

$$\mathcal{U}(\mathcal{A}(D), D, D_f) \stackrel{d}{=} \mathcal{A}(D_r)$$

即遗忘后的模型与在 $D_r$ 上重训得到的模型在分布上不可区分。放宽为 $(\epsilon, \delta)$-近似遗忘时,借用差分隐私式的定义:对任意可测集合 $S$,

$$e^{-\epsilon} \Pr[\mathcal{A}(D_r) \in S] - \delta \le \Pr[\mathcal{U}(\cdot) \in S] \le e^{\epsilon} \Pr[\mathcal{A}(D_r) \in S] + \delta$$

### 驱动力

- **法规合规**:GDPR Art.17(被遗忘权)、CCPA、《个人信息保护法》第 47 条,均要求"删除个人数据"扩展至从模型参数中删除其影响。
- **版权与许可下架**:Getty vs Stability、NYT vs OpenAI 等诉讼推动"训练数据可撤回"成为必需能力。
- **有害数据事后清理**:偏见、隐私 PII、越狱示例、CSAM 等在训练后被发现,需要定向消除而不重训。
- **后门/投毒防御**:攻击者注入的投毒样本一旦定位,可通过遗忘定向清除。
- **模型持续演化**:知识过期(某公司被收购、某人物身份变更)时,把陈旧事实"卸载"再增量学习新事实。

## 方法路线

### 1. 精确遗忘 Exact Unlearning

代表工作是 **SISA (Sharded, Isolated, Sliced, Aggregated)**(Bourtoule et al. 2019):

- **Sharded**:数据集切成 $S$ 个不相交分片 $D_1, \dots, D_S$,每片独立训一个子模型 $M_i$。
- **Sliced**:每个分片内再按序切成若干 slice,按增量方式训练并保存中间检查点。
- **Aggregated**:推理时用投票/平均聚合 $\{M_i\}$。
- 当收到遗忘请求时,只需回滚到"目标样本进入之前"的检查点,重训受影响的那个分片。期望重训代价约为 $O(1/S)$ 倍完整重训。

理论保证:严格等价于"从未见过 $D_f$"训练的模型(在同一切片和随机种子下)。代价:训练架构必须提前配合、聚合会略微降低精度、分片数过多时单片数据不足。

其他精确路线:

- **DaRE 森林(Delete-and-Retrain-Efficient)**:面向随机森林/GBDT 的精确遗忘,记录节点级统计量支持增量删除。
- **k-anonymized retraining**:对少量样本用凸优化封闭解重训(仅适用线性模型/凸损失)。

### 2. 近似遗忘 Approximate Unlearning

不改训练流程,直接对权重做"反向剥离":

- **影响函数(Influence Function)**:Koh & Liang 2017。用 $\theta^{-i} \approx \theta - H_\theta^{-1} \nabla_\theta \ell(z_i, \theta)$ 估计移除样本 $z_i$ 后的参数变化,其中 $H_\theta = \nabla_\theta^2 \mathcal{L}(\theta)$。适合小数据、凸或近凸损失;深网中 Hessian 逆需要 stochastic estimator (LiSSA) 且不稳定。
- **Fisher 信息遮罩**:用 $F = \mathbb{E}[\nabla \log p(y \mid x, \theta) \nabla \log p(y \mid x, \theta)^\top]$ 度量参数重要性,对与 $D_f$ 高度相关的方向做定向扰动。
- **梯度上升(Gradient Ascent on forget set)**:在 $D_f$ 上做 $\theta \leftarrow \theta + \eta \nabla_\theta \mathcal{L}(D_f; \theta)$ 若干步,迫使模型"抬升"遗忘集损失;通常搭配 $D_r$ 上的常规下降做正则,防止效用崩塌。
- **参数扰动 + Noise Injection**:向遗忘方向注入高斯噪声,形式上对齐 $(\epsilon, \delta)$-DP 保证。
- **Fine-tuning on retain set**:在 $D_r$(甚至只是一小份代表性子集)上短时微调,让模型对 $D_f$ 的记忆通过灾难性遗忘自然衰减。作 baseline 常用,但对具体样本的"遗忘充分性"缺乏保证。
- **教师-学生蒸馏遗忘**:用另一个未见 $D_f$ 的教师模型蒸馏学生,间接实现遗忘;代价是要有可信教师。

近似遗忘速度快、无需改训练流程,但没有严格等价保证,通常需要配合"成员推断攻击(MIA)不能区分"这类经验指标来评估。

### 3. LLM 场景专用

参数量 $10^9$–$10^{12}$,SISA 完全不可行。主流做法:

- **Task Vector / Task Arithmetic**(Ilharco et al. 2023):算出"包含目标知识的微调权重"与"基座"之差 $\tau = \theta_{\text{ft}} - \theta_{\text{base}}$,遗忘时执行 $\theta' = \theta - \lambda \tau$。简单有效但需要可训练出 $\theta_{\text{ft}}$ 的成对数据。
- **RLHF/DPO 反向对齐**:构造"应拒绝回答"的偏好对,用 [[人类反馈强化学习 RLHF]] 把不想要的行为压下去。本质是"行为遗忘"而非"权重遗忘",模型可能仍在参数中保留知识。
- **定位-编辑(Locate-and-Edit)**:反向使用 ROME / MEMIT,先用因果追踪定位存储该事实的 MLP 层,再用低秩权重更新覆盖为"我不知道"或空指针。粒度可精确到单条事实。
- **Negative Preference Optimization (NPO)** 与 **Gradient Difference**:在 forget set 上用负偏好目标,同时在 retain set 上保留原分布,LLM unlearning 的当前主流训练目标之一。
- **代表评测**:
  - **TOFU benchmark**(Maini et al. 2024):200 个虚构作者传记,可控测量"遗忘目标传记 + 保留其他传记 + 保留通用能力"。
  - **"Who's Harry Potter?"**(Eldan & Russinovich 2023):在 Llama-2 上遗忘《哈利·波特》全书内容,提出"generic replacement"技术。
  - **WMDP**(Weapons of Mass Destruction Proxy, 2024):遗忘生物/化学/网络攻击类危险知识的评测。

## 评测三维度

三个维度必须同时看,存在明显 trade-off:

- **遗忘充分性 Forget Quality**:目标数据是否真被遗忘。指标:
  - **成员推断攻击(MIA)**:遗忘后攻击者能否判断某样本曾在训练集中。理想是攻击 AUC $\approx 0.5$。
  - **目标集精度掉零**:分类任务上 $\text{Acc}(M', D_f) \to$ 随机基线。
  - **KL 散度对比重训**:$\mathrm{KL}(M'(x) \Vert M_{\text{retrain}}(x))$ 越小越好。
  - **提取攻击(Extraction Attack)**:LLM 场景,用提示试图诱导原始训练文本。
- **模型效用保持 Utility**:其他任务不能被破坏。指标:$\text{Acc}(M', D_r)$、下游 benchmark 分数、语言模型的困惑度 PPL、通用能力(MMLU、HellaSwag 等)。
- **效率 Efficiency**:时间/算力相对完整重训的开销。SISA $\approx 1/S$、影响函数 $\approx$ 一次 Hessian-vector 积、LLM 权重编辑 $\approx$ 秒级。

当前没有方法在三者上同时占优。**评测陷阱**:仅报告 $\text{Acc}(M', D_f) = 0$ 而不做 MIA/提取攻击,极易掩盖"知识仍在参数中,只是被行为层压下去"的假遗忘。

## 关键挑战

- **理论保证 vs 可扩展性**:精确遗忘有保证但难扩展;近似遗忘可扩展但保证弱。
- **遗忘的可组合性**:多次连续遗忘请求会累积误差,导致模型性能下降或遗忘不彻底(catastrophic forgetting of retain set)。
- **审计与可验证性**:如何向监管方证明"该数据确实已从模型中删除"?候选方案:重训基线比对、MIA 报告、承诺-揭露协议、[[SHA-256 产物指纹]] 链。
- **遗忘的可撤销风险**:攻击者若能拿到遗忘前后的两个权重,可能通过差分反推被遗忘数据(unlearning as an attack surface,Chen et al. 2021)。
- **概念/关系级遗忘**:相对样本级,更难。要求删除的是"某人的所有事实"而非"某段训练文本"。

## 和我的项目的关系

- **EvidenceFirst**:强相关。被遗忘权要求"能证明数据已被删除",这恰好是 EvidenceFirst 强调的可审计性/溯源能力——遗忘操作本身需要生成可验证的证据链(哪条数据、哪次遗忘、遗忘后模型指纹),配合 [[SHA-256 产物指纹]] 就是天然的合规产物。可扩展为"遗忘证书 Unlearning Certificate":输入(原模型指纹、$D_f$ 描述、遗忘算法参数、随机种子)→ 输出(新模型指纹、MIA 报告、重训基线比对)。
- **TripleChecker**:中等相关。当质量评估判定某条三元组错误或过时,除了在 KG 层删除,还需要考虑下游 LLM 是否已经"记住"了这条错误知识——这就是 LLM unlearning 的场景。可作为 TripleChecker 的下游能力方向,尤其配合定位-编辑技术做单条事实卸载。
- **GSAD**:弱相关。动态知识撤回与时序演化中,过期知识的"遗忘"是天然需求,但 GSAD 更偏检索层而非参数层,通常靠 RAG 换库解决即可,不一定要走 unlearning。若模型有参数化记忆(小模型 + 长期部署场景),仍需考虑。
- **ChronoLink / CoMaGRAG**:暂无直接关联,但若图谱中含个人隐私实体,需要同步考虑图侧删除与模型侧遗忘的一致性。

## 交叉引用

- [[前沿趋势 Frontier]]
- [[EvidenceFirst]]
- [[TripleChecker]]
- [[溯源 Provenance]]
- [[可审计性 Auditability]]
- [[SHA-256 产物指纹]]
- [[人类反馈强化学习 RLHF]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[对抗样本 Adversarial Examples]]
- [[提示注入 Prompt Injection]]

## 更新记录

- 2026-07-13: 首次建页
- 2026-07-13: 扩写——补形式化定义、方法细节(SISA/影响函数/Task Vector/NPO)、评测三维度指标、关键挑战、LLM 专用小节与 benchmark(TOFU/WMDP/Harry Potter)
