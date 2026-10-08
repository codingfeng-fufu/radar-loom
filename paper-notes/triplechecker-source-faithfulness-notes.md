# TripleChecker: Source-Faithfulness Auditing for Chinese KG Extraction

**作者/机构**：Anonymous Authors / Anonymous Institution  
**Venue/年份**：论文未报告  
**原文**：`papers/77_TripleChecker_Source_Faithf (3).pdf`  
**材料范围**：12 页论文全文；文件内没有独立附录或补充材料  
**一句话总结**：TripleChecker 把中文知识图谱抽取的“来源是否支持三元组”落实为一个可执行的两层审计契约：先核验抽取器给出的来源片段确实存在于原文，再用关系类型感知的中文 verbalization 与 NLI 判断语义支持；系统易解释、无需在线调用 LLM，但默认阈值主要保障合法三元组留存，对真实不支持三元组的主动拒绝能力仍有限。

## 1. 问题与动机

### 1.1 论文解决的具体问题

论文研究的是**中文 KG 抽取的来源保真度**，而不是开放世界事实核查。给定文档 $D$、抽取三元组 $t_i=(s_i,p_i,o_i)$ 以及抽取器同时返回的来源片段 $\sigma_i$，审计器判断该片段是否真的支持该三元组（§1、§3.1，PDF p.1、p.3）。

这一区分很重要：

- 它验证“这条边能否由当前文档追溯和支持”；
- 它不验证三元组在现实世界中是否客观为真；
- 它不发现抽取器遗漏的事实，也不衡量 KG 完整性；
- 它不覆盖需要跨句或多跳证据才能成立的关系（§3.1、§5，PDF p.3、p.10–11）。

论文的真实工程动机是：抽取器生成的 KG 一旦包含没有来源支持的边，下游检索、问答和推理会把这些边当成结构化事实继续放大。与在问答末端再做事实核查相比，构图阶段的审计能够把问题拦截在知识进入图谱之前（§1，PDF p.1–2）。

### 1.2 已有方法卡在哪里

论文指出三类不足（§1–2，PDF p.1–3）：

1. **只检查实体是否出现不够**：subject 和 object 都可能真实出现，但关系方向或谓词本身仍然错误。
2. **固定中文模板容易反转关系**：例如 $(\text{马云},\text{创始人},\text{阿里巴巴})$ 应复述为“马云是阿里巴巴的创始人”，朴素的“$s$ 的 $p$ 是 $o$”会变成方向相反的句子。
3. **通用事实核查器与任务契约不一致**：本文需要区分伪造来源片段和真实片段中的语义不支持，而不是只给一个不可诊断的事实分数。

**阅读判断**：论文抓住的是一个明确且有部署接口的问题。其价值不主要来自发明新的 NLI 架构，而是把“抽取结果必须带可核验来源”变成了可计算、可分解、可配置阈值的 KG 准入机制。

## 2. 核心方法

### 2.1 完整数据流

Figure 1 展示了两层流水线（PDF p.4）：

1. 抽取器输出三元组 $t_i$ 和来源片段 $\sigma_i$；
2. Layer 1 检查 $\sigma_i$ 是否为文档 $D$ 的非空严格子串；
3. 通过 Layer 1 后，用 RTAV 将三元组复述为中文假设句 $h_i$；
4. Layer 2 用中文 NLI 判断 $\sigma_i$ 是否蕴含 $h_i$；
5. 输出 `PASS`、`FAKE_SPAN` 或 `SOURCE_UNSUPPORTED`，并汇总图级诊断指标。

### 2.2 Layer 1：来源片段真实性

来源片段真实性定义为（§3.2，PDF p.4）：

$$
V_1(t_i)=\mathbb{1}[\sigma_i\ne\varnothing\wedge\sigma_i\sqsubseteq D].
$$

若 $V_1(t_i)=0$，系统立即判为 `FAKE_SPAN`，不再调用 NLI。这一层几乎不需要模型成本，并能把“来源本身是编的”和“来源真实但不支持三元组”分开。

**工程含义**：Layer 1 适合作为廉价短路，但严格子串匹配依赖抽取器和原文使用完全一致的字符表示。OCR、空白、全半角、标点或预处理差异都可能造成误拒；论文没有提供规范化匹配策略（§5，PDF p.10–11）。

### 2.3 RTAV：关系类型感知复述

RTAV（Relation-Type-Aware Verbalization）先把谓词映射到六类粗粒度关系：identity、event、attribute、location、affiliation、temporal，再根据关系类型选择主客体方向合适的中文模板（§3.3，PDF p.4–5）。其目标不是生成更流畅的句子，而是降低中文名词型谓词在 NLI 输入中发生方向反转的概率。

对于词典未覆盖的谓词，作者构建离线模板 bank：候选包括 RTAV 模板、所有格模板、通用关系模板以及可选的 LLM 生成模板；候选被标准化为 $\{s,p,o\}$ 槽位，并用正例与 subject/object 替换负例之间的 NLI 分数间隔进行选择（§3.3，PDF p.5）：

$$
\varphi^{(p)}=\arg\max_{\psi_k}
\left[
\mathbb{E}_{D_p^+}\mathrm{NLI}(\sigma,\psi_k(s,p,o))
-
\mathbb{E}_{D_p^-}\mathrm{NLI}(\sigma,\psi_k(s,p,o))
\right].
$$

模板 bank 在推理时是静态资源，不更新验证器参数。不过，它使用关系 schema 下的实例进行离线选择，因此不能简单理解为完全无数据依赖的方法；论文也没有给出文档级模板来源记录，无法核验同文档信息是否参与模板选择（§3.3、§5，PDF p.5、p.10–11）。

### 2.4 Layer 2：NLI 语义支持

系统把来源片段或其滑动窗口作为 premise，把 RTAV 复述句作为 hypothesis。主实验使用 `Erlangshen-RoBERTa-110M-NLI`，`max_length=256`、`stride=128`，并取所有窗口中的最大蕴含分数（§3.2、§4.1，PDF p.4–5）：

$$
\tau_i=\max_{w\in W(\sigma_i)}\mathrm{NLI}(w,h_i),
\qquad
V_2(t_i)=\mathbb{1}[\tau_i\ge\delta].
$$

主结果固定 $\delta=0.5$。联合判定为：只有 $V_1(t_i)V_2(t_i)=1$ 才输出 `PASS`（§3.2，PDF p.4）。

最大值聚合适合“长片段中只需一个窗口提供充分证据”的情形，但也会放大偶然高分窗口。论文在 180 条多窗口 CMeIE 三元组上报告 max / mean / majority 的 F1 分别为 $0.837/0.662/0.475$，支持 max 在该诊断集上的选择，但没有测量分布外长文档上的虚假高分率（§4.5，PDF p.9）。

### 2.5 图级评分与诊断

论文把图级通过率分解为 Span Authenticity Rate（SAR）与 Entailment-Pass Rate（EPR）（§3.2，PDF p.4）：

$$
\mathrm{Score}(G\mid D)
=
\frac{\sum_i V_1(t_i)V_2(t_i)}{N}
=
\mathrm{SAR}\times\mathrm{EPR},
$$

其中

$$
\mathrm{SAR}=\frac{\sum_i V_1(t_i)}{N},
\qquad
\mathrm{EPR}=\frac{\sum_i V_1(t_i)V_2(t_i)}{\max(\sum_i V_1(t_i),1)}.
$$

这里 SAR 在论文中是 **Span Authenticity Rate**，不应改写为 Source-Anchor Rate。分解的工程价值是区分“抽取器伪造引用”与“引用真实但关系不被支持”两类故障。

## 3. 实验与证据

### 3.1 数据与证据层级

受控 benchmark 来自 DuIE2.0、CMeIE-V2 和 FinRE。每个数据集包含 1,000 条 gold supported triple，以及各 1,000 条 fabricated-span、subject-replacement、object-replacement、predicate-mismatch 负例，总计 15,000 行，其中 3,000 条 supported、12,000 条 source-unsupported（§4.1–4.2，PDF p.5–6，Table 1）。

这些标签主要由构造过程定义，不是 15,000 条独立人工标注。作者明确把它定位为受控扰动压力测试，而非真实生产环境中不支持三元组占比的估计（§4.1，PDF p.5–6）。

论文另提供三类校准证据：

- 200 条 DuIE 人工标注集（§4.4，PDF p.8，Table 3）；
- 383 条、160 篇文档的本地 Qwen 自然噪声集，经过 agent adjudication，而非独立人工金标（§4.4，PDF p.8，Table 3）；
- 对受控标签抽取 300 条进行盲双 agent 有效性审计，以及 50 条自然噪声盲校准子集（§4.4，PDF p.8）。

**阅读判断**：论文采用“受控机制测试 + 小规模人工校准 + 下游敏感性分析”的证据链，比只报一个合成分类分数更完整；但 headline 指标仍主要由合成扰动贡献，不能直接外推为生产误报和漏报率。

### 3.2 固定阈值主结果

在 $\delta=0.5$ 下，TripleChecker 在 15,000 行受控 benchmark 上得到（§4.2，PDF p.6–7，Table 1）：

| 指标 | 结果 |
|---|---:|
| PASS recall | 0.811 |
| Source-unsupported recall | 0.704 |
| Source-unsupported F1 | 0.804，95% CI $[0.7989,0.8091]$ |
| Accuracy | 0.725，95% CI $[0.7193,0.7317]$ |

按负例条件切片，拒绝率为（§4.2，PDF p.6）：

| 负例类型 | 拒绝率 |
|---|---:|
| fabricated span | 1.000 |
| object replacement | 0.709 |
| subject replacement | 0.604 |
| predicate mismatch | 0.503 |

这说明 Layer 1 对伪造 span 的机制性测试完全通过，但真正困难的是具有真实 span 的语义扰动，尤其谓词错配。

与同一 NLI scorer 的 fixed-template baseline 相比，TripleChecker 的固定阈值 SU-F1 仅高 $0.005$，clustered-bootstrap 95% CI 为 $[0.0009,0.0096]$；各自调到最佳阈值后，差异为 $0.003$，CI 为 $[0.0007,0.0054]$（§4.2，PDF p.6–7）。

**阅读判断**：置信区间支持差异不是纯随机波动，但效应量很小。因此不应把论文概括成“RTAV 显著提高总体分类性能”；更准确的贡献是把 span 真实性、语义支持、方向诊断和准入政策组织成一套可部署审计流程。

### 3.3 阈值政策与 supported-loss budget

Table 2 表明阈值选择决定了系统到底是“保留优先”还是“拒绝优先”（§4.3，PDF p.7）：

| 政策 | $\delta$ | PASS recall | SU recall | SU-F1 |
|---|---:|---:|---:|---:|
| 固定策略 | 0.500 | 0.811 | 0.704 | 0.804 |
| 高保留策略 | 0.082 | 0.950 | 0.475 | 0.639 |
| 最佳 SU-F1 | 0.976 | 0.288 | 0.974 | 0.905 |

严格追求 SU-F1 会丢弃约四分之三的 supported triples；高保留策略则只能发现不到一半的 unsupported rows。论文因此把阈值解释为部署政策，而不是一个通用最优常数。

在 12,000 条受控 unsupported rows 上，允许损失 25/50/100/250/500 条 supported rows 时，可拒绝的 unsupported rows 分别为 3806/4337/5073/6625/8164（§4.3，PDF p.7）。这种 supported-loss budget 比单独报告 F1 更接近 KG 准入场景的业务决策。

### 3.4 人工校准与自然噪声

200 条 DuIE 人工集包含 133 条 supported triple。固定阈值下（§4.4，PDF p.8，Table 3）：

- PASS precision / recall / F1：$0.694/0.970/0.809$；
- SU recall / F1：$0.149/0.247$；
- 133 条 supported 中保留 129 条；
- 67 条 unsupported 中有 57 条仍被保留。

标注者间 Pearson $r=0.821$、Spearman $\rho=0.849$，exact agreement 为 $68\%$（§4.4，PDF p.8）。在这个更接近自然误差的人工集上，默认阈值明显偏向覆盖率，而不是强力清除不支持三元组。论文也据此把 $\delta=0.5$ 定位为 construction-time retention/quarantine gate（§4.4–4.5，PDF p.8–9）。

人工集上的 supported-loss budget 同样揭示权衡：允许损失 4/25/100 条 supported triples 时，分别拒绝 10/67、22/67、59/67 条 unsupported triples（§4.5，PDF p.9）。

383 条本地 Qwen 自然噪声集上，TripleChecker 的 PASS P/R/F1 为 $0.699/0.739/0.718$，SU recall/F1 为 $0.625/0.647$（§4.4，PDF p.8，Table 3）。同页 scalar baselines 的 SU-F1 最高达到 $0.661$，因此 TripleChecker 并非这个诊断集上的最佳纯分类器。agent adjudication 还使 SU-F1 从 $0.615$ 变为 $0.647$、PASS-F1 从 $0.771$ 变为 $0.718$，说明结果对标签裁决规则较敏感。

50 条盲校准子集在保守裁决前的 source-support label 一致为 47/50，完整 decision 一致为 44/50（§4.4，PDF p.8）。300 条受控标签盲审中，283 条有效、15 条无效、2 条不确定；在已决定样本中有效率为 $94.97\%$，修正后该样本的固定阈值 SU-F1 从 $0.7737$ 变为 $0.7644$（§4.4，PDF p.8）。

**阅读判断**：这些审计提高了论文对标签噪声的透明度，但 agent adjudication 不能替代更大规模、独立、双人盲标的自然抽取错误集。

### 3.5 RTAV 与窗口聚合消融

在 200 条标注三元组上，fixed template、LLM verbalization、RTAV 的 accuracy/F1 分别为（§4.6，PDF p.9）：

| Verbalization | Accuracy | F1 |
|---|---:|---:|
| Fixed template | 0.714 | 0.762 |
| LLM | 0.751 | 0.788 |
| RTAV | 0.790 | 0.811 |

谓词隐藏诊断的 100 个随机 split 中，RTAV 相对 generic fallback 的 held-out SU-F1 平均提升 $0.151$，并在 85/100 个 split 上胜出（§4.6，PDF p.9）。

这支持“关系方向敏感的 verbalization 比统一模板更可靠”，但并未证明模板 bank 对新文档、新 schema 或完全未见谓词具有稳定的端到端泛化能力。论文自己也把缺少 document-level template provenance 和文档级 held-out 评测列为限制（§5，PDF p.10–11）。

### 3.6 下游问答敏感性

下游实验在 100 篇文档上构造约 30% unsupported-triple 注入，并比较完整噪声图 $G_{full}$、与过滤后图等大小的随机子图 $G_{rand}$、以及 TripleChecker 过滤图 $G_{tc}$（§4.7，PDF p.10）。论文报告：

- $G_{tc}$ 的 EM 为 $0.791$；
- $G_{rand}$ 的 EM 为 $0.482$；
- $G_{tc}$ 比 $G_{rand}$ 高 $30.9$ 个百分点；
- $G_{tc}$ 比 $G_{full}$ 高 $32.0$ 个百分点。

因此 $0.482$ 对应的是 $G_{rand}$，不是 $G_{full}$。随机等大小对照说明收益不只是来自删边后图变小。

Layer 2 独立贡献实验注入 97 条“span 真实但语义被替换”的噪声三元组：Layer 1 拒绝 0 条，Layer 2 拒绝 92 条，recall 为 $0.948$；$G_{tc}^{sem}$ 与 $G_{rand}^{sem}$ 的 EM 分别为 $0.780$ 和 $0.555$，相差 $22.5$ 个百分点（§4.7，PDF p.10）。

**阅读判断**：该实验很好地证明两层不是冗余的，尤其 Layer 2 能处理真实 span 内的关系污染。但它仍是 injected-noise sensitivity analysis，而非真实生产 KG-RAG 的外部验证；不能据此声称系统在自然问答环境中必然带来相同幅度的收益。

### 3.7 可复现性、成本与部署难度

**论文提供的信息**（§3–4，PDF p.4–10）：

- NLI checkpoint、阈值、最大长度、stride 和聚合方式明确；
- 受控负例类型和每类规模明确；
- 模板 bank 的候选生成与选择目标明确；
- 统计结果包含 clustered bootstrap CI，并报告多种校准和消融。

**论文未报告或不足的信息**：

- 完整端到端吞吐量、单条延迟、GPU 型号、显存和能耗；
- 三个数据集从原始记录到 15,000 行 benchmark 的完整可执行复现链；
- 每个模板对应的文档级训练/选择来源；
- 不同文本规范化、OCR 和分句器下 Layer 1 的鲁棒性；
- 大规模真实抽取流量中的告警率、人工复核负担和长期漂移；
- 7B 级强事实核查模型的完整对照结果，因而不能据现有结果宣称压倒所有强 verifier。

**工程判断**：在线路径不需要 LLM judge，也不训练新 verifier；Layer 1 可短路，Layer 2 使用 110M NLI 模型，部署门槛明显低于逐条调用大模型。真正的成本和风险会转移到上游 span 定位质量、离线模板 bank 维护、阈值校准以及被隔离三元组的人工处置。

### 3.8 方法新颖性

**作者主张**：工作贡献包括来源片段驱动的两层中文 KG 审计、RTAV、可解释的 SAR/EPR 分解、受控与人工校准证据，以及下游敏感性分析（§1，PDF p.2）。

**阅读判断**：单个组件并非全新——严格子串检查、NLI 和模板 verbalization 都是已有技术。较有价值的新颖性来自任务契约与系统组合：把 provenance 当成抽取接口的一部分，显式区分假 span 与真 span 语义不支持，并把模型阈值转译成 supported-loss budget。标量分类增益很小，因此论文的最佳定位是“可操作的审计框架”，而不是“显著更强的新分类模型”。

## 4. 局限性

### 4.1 作者明确承认的局限

1. **依赖抽取器返回 span**：无来源片段的旧系统需要另加 localization，已经改变原始审计契约（§5，PDF p.10–11）。
2. **严格字符串匹配脆弱**：字符规范化、OCR、分词和标点差异可能造成 Layer 1 误拒（§5，PDF p.10–11）。
3. **宽泛 span 导致误通过**：人工集 57 个 false positives 中，49 个来自过宽 span；其余 8 个与对称谓词的 RTAV 方向错误有关（§4.5、§5，PDF p.9–11）。
4. **关系方向与语义粒度仍困难**：列表、标题以及 starring、director、chairman 等关系容易因 span 包含多个候选事实而被 NLI 过度判为蕴含（§4.5、§5，PDF p.9–11）。
5. **schema 泛化证据有限**：模板来源缺乏文档级 provenance，未完成严格 document-held-out 的 RTAV 鲁棒性评测（§5，PDF p.10–11）。
6. **任务边界有限**：不验证外部真值、遗漏事实、图谱完整性或多跳支持（§3.1、§5，PDF p.3、p.10–11）。

### 4.2 证据显示但讨论仍不足的局限

1. **默认阈值的自然错误拒绝率偏低**：人工集 SU recall 只有 $0.149$。若部署目标是自动清除错误边，$\delta=0.5$ 不够；若提高阈值，又会迅速损失 supported triples。
2. **headline benchmark 类别先验不自然**：负例占 80%，且四类负例数量完全均衡，SU-F1 和最佳阈值会受到这一人为分布影响。
3. **最大窗口聚合存在选择偏差风险**：窗口越多，出现偶然高 entailment score 的机会越大；180 条诊断不足以量化这一风险。
4. **自然噪声证据仍弱**：383 条数据由本地模型生成并经 agent 裁决，同页 scalar baseline 还略高于 TripleChecker，不能作为独立的人类外部验证。
5. **下游增益来自受控注入**：它证明过滤机制在预设攻击模型下有用，但不估计真实 KG 中错误类型、相关性和严重度。
6. **缺少完整系统成本曲线**：没有把 span 生成、模板维护、NLI 推理和人工复核一起计入每百万三元组的真实成本。

## 5. 与当前研究的关联

根据现有项目页 `pages/TripleChecker.md` 与知识图谱质量框架页 `pages/知识图谱质量评估维度.md`，这篇论文最适合作为当前研究中“**三元组进入 KG 前的来源准确性审计层**”，而不是泛化为全部 KG 质量保障：

- 对 `TripleChecker` 项目本身，论文提供了最可信的统一口径：source-faithfulness、SAR/EPR、受控 SU benchmark、人工校准和准入政策。项目叙述应优先使用这些论文证据，而不是更强但未被本文独立支持的宣传数字。
- 对 KG 质量研究主线，它覆盖的是三元组级来源支持；图级一致性、时效性、完整性和多跳推理可信度仍需其他模块处理。
- 对 NLI 研究，它提供了一个具体反例：同一个 NLI scorer 的总体提升很小，系统成败更多取决于 hypothesis verbalization、span 边界和阈值政策，而不是只换更大的分类器。
- 对后续 EvidenceFirst 类路径验证，TripleChecker 可以提供经过来源审计的候选边，但现有 `pages/EvidenceFirst.md` 仍是占位页，尚无足够材料证明两者已经形成可复现的端到端系统。

可直接复用的研究设计包括：

1. 把错误拆成可诊断类型，而不是只报总 F1；
2. 同时报告固定阈值、最优阈值与业务约束下的 policy curve；
3. 用等大小随机删边对照，排除“图变小所以问答变好”的混杂；
4. 单独构造真实 span 的语义噪声，证明语义层具有独立贡献；
5. 对自动构造标签做抽样有效性审计，并展示修正前后的指标变化。

需要避免的是：把受控合成 benchmark 的 SU-F1 直接表述为真实生产准确率，或把 $G_{rand}=0.482$ 错写成 $G_{full}=0.482$。

## 6. 待验证问题

1. 代码中的 Layer 1 是否进行 Unicode、全半角、空白和标点规范化，还是完全按公式做严格子串匹配？
2. 模板 bank 的每个谓词使用了哪些文档和实例进行选择？能否重建 document-held-out split，排除同文档信息泄漏？
3. 受控 benchmark 的 subject/object replacement 是否保证替换实体在 span 中自然出现，四类负例的语言学难度是否相当？
4. 论文所用 NLI checkpoint 的 entailment score 是原始三分类概率还是经过额外校准的分数？不同数据域的 calibration error 如何？
5. $G_{full}$ 的精确 EM、每个图的平均节点/边数、QA 构造规则和检索器设置，需要结合代码与结果文件复核；正文只明确报告 $G_{tc}=0.791$ 及相对差值。
6. 在真实抽取器输出上，宽 span、错 span、缺 span 和语义错误的联合分布是什么？默认阈值的人工复核队列规模多大？
7. max aggregation 在窗口数量增加时是否出现 false-pass rate 单调上升？可否用 top-$k$、校准后的 noisy-OR 或证据窗口定位替代？
8. 与更强中文或多语事实核查器、现代小型指令模型比较后，RTAV 的优势是否仍然成立？
9. 论文没有报告运行成本；需要在目标硬件上测量每秒三元组数、P95 延迟、显存和每百万三元组成本。

## 7. 定位索引

| 关键内容 | PDF 定位 |
|---|---|
| 任务定义、动机与贡献 | §1，p.1–2 |
| 相关工作与审计边界 | §2、§3.1，p.2–3 |
| Figure 1 两层架构 | Figure 1，p.4 |
| Layer 1、Layer 2 与联合判定公式 | §3.2，p.4 |
| SAR × EPR 分解 | §3.2，p.4 |
| RTAV 六类关系与方向问题 | §3.3，p.4–5 |
| 离线模板 bank 与选择目标 | §3.3，p.5 |
| 数据集、受控负例和 NLI 配置 | §4.1，p.5–6 |
| 15,000 行固定阈值主结果 | §4.2，Table 1，p.6–7 |
| fixed-template paired delta | §4.2，p.6–7 |
| 三种阈值政策与 supported-loss budget | §4.3，Table 2，p.7 |
| 200 条人工集与 383 条自然噪声集 | §4.4，Table 3，p.8 |
| 300 条标签有效性审计与 50 条盲校准 | §4.4，p.8 |
| 人工集 policy behavior 与 false-positive 归因 | §4.5，p.9 |
| max / mean / majority 聚合诊断 | §4.5，p.9 |
| RTAV 消融与 predicate-hiding split | §4.6，p.9 |
| 下游注入噪声问答与 Layer 2 隔离实验 | §4.7，p.10 |
| 作者局限、结论 | §5–6，p.10–11 |

## 阅读结论

这篇论文最可信的结论不是“TripleChecker 在所有场景中都能高召回地清除幻觉”，而是：**要求抽取器返回来源片段后，可以用廉价的 span 真实性检查与小型中文 NLI 构成一套可解释的构图审计接口；Layer 2 对真实 span 的语义污染确有独立作用，阈值必须按 supported-loss budget 部署。** 最大限制是自然错误上的默认 SU recall 很低，且性能高度受 span 边界、关系方向和合成数据分布影响。
