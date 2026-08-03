---
摘要: 中文KG抽取的溯源保真度审计(Source-Faithfulness Auditing)两层无监督验证器,一作论文,投稿NLPCC 2026;15,000 行受控 benchmark 上 SU-F1=0.804。
来源: ~/Evaluating_Knowledge_Graph_Extraction_via_Dual-Cycle_Consistency/TripleChecker/main.pdf
信度: 高
首次记录: 2026-07-20
tags: [项目, TripleChecker, KG, 可信度, 评测]
---

# TripleChecker

## 核心内容

TripleChecker 是一个**中文 KG 抽取的溯源保真度审计器**(source-faithfulness auditor)。它假设抽取系统对每条三元组 $t_i=(s_i,p_i,o_i)$ 同时返回一条溯源片段 $\sigma_i$,并对每条三元组做两层无监督判定:**Layer 1** 校验 $\sigma_i$ 是否为文档 $D$ 的严格子串;**Layer 2** 用中文 NLI 判定 $\sigma_i$ 是否语义蕴含由 **RTAV**(Relation-Type-Aware Verbalization)复述而来的中文假设句 $h_i$。图级得分 $\mathrm{Score}(G\mid D)$ 可分解为 $\mathrm{SAR}\times\mathrm{EPR}$——溯源可核锚率与蕴含通过率的乘积,直接指示每条三元组是否"由 $D$ 支持"。

## 一、问题定义

- **要解决**:LLM 从中文文档抽 KG 时会伪造原文里没有的三元组;这些"源不支持"(source-unsupported, SU)的边喂到下游 KG-RAG 会污染答案。目标是**无需人工标注**、面向"是否由 $D$ 支持"这条契约做自动审计。

- **审计契约(paper §3.1)**:每条三元组 $t_i$ 带溯源 $\sigma_i$,审计器对 $t_i$ 打二元 label $\ell_i\in\{\text{PASS},\text{FAIL}\}$;图级得分定义为
  $$\mathrm{Score}(G\mid D)=\frac{|\{i:\ell_i=\mathrm{PASS}\}|}{N}.$$
  并进一步分解:
  $$\mathrm{Score}(G\mid D)=\mathrm{SAR}\times\mathrm{EPR}=\frac{\sum_i V_1(t_i)}{N}\times\frac{\sum_i V_1(t_i)V_2(t_i)}{\max(\sum_i V_1(t_i),1)}.$$
  SAR(Source-Anchor Rate)量化"溯源是否可核",EPR(Entailment-Pass Rate)量化"溯源是否真的蕴含三元组"。

- **现有方法不够**:
  - 只校验 subject / object 是否在原文,拦不住"关系幻觉"(主客体真实、关系伪造)。
  - 通用 NLI 直接搬会踩中文谓词是名词的坑,固定模板方向反转:`(马云, 创始人, 阿里巴巴)` 用"X 的 Y 是 Z"会被读成"马云的创始人是阿里巴巴",NLI 拒真。
  - 现成事实核查模型在中文 span-triple 设置下几乎失效——MiniCheck 中文场景基本失灵。

- **两个 failure case**:
  1. **关系冲突型**(paper case study):文档讲天城公主嫁国峻,LLM 同时抽出 `(天城公主, 丈夫, 国峻)` 与 `(天城公主, 丈夫, 温鹏程)`;`G_full` 答"温鹏程",`G_tc` 过滤后答"国峻"。
  2. **同谓词 object 替换的 real-span 语义幻觉(W1)**:把 gold object 换成另一篇文档同谓词的 object,`source_span` 依然真实。Layer 1 完全拦不住,只有 Layer 2 能过滤(实测 Layer 2 recall 0.948)。

## 二、核心方法

**一句话**:溯源片段 $\sigma_i$ 作为强锚点 + Layer 1 字符串校验 + Layer 2 中文 NLI 蕴含 + RTAV 关系类型感知 verbalization。

**关键步骤**:

1. **抽 KG 时同时输出 $\sigma_i$**(方法前提)。

2. **Layer 1(source-anchor check)**:
   $$V_1(t_i)=\mathbb{1}[\sigma_i\ne\varnothing\wedge\sigma_i\sqsubseteq D].$$
   零成本、放最外层,直接拒掉伪造来源。

3. **RTAV verbalization**:按谓词映射到 6 类粗粒度关系类型 $\kappa(p_i)\in\{\text{identity},\text{event},\text{attribute},\text{location},\text{affiliation},\text{temporal}\}$,每类挑选类型专属的中文模板 $\varphi_{\kappa}$:
   $$h_i=\varphi_{\kappa(p_i)}(s_i,p_i,o_i).$$
   字典覆盖率:DuIE2.0 59.1%,CMeIE 0.4%,FinRE 0.0%;未命中字典的谓词由**离线 LLM 生成候选 + NLI 打分筛选**的模板 bank 提供,再未命中则退到 generic fallback。目的是解决中文名词谓词方向反转问题。

4. **Layer 2(NLI entailment check)**:用 `Erlangshen-RoBERTa-110M-NLI` 计算蕴含分数,长文档滑窗聚合用 `max`:
   $$\tau_i=\max_{w\in W(\sigma_i)}\mathrm{NLI}(w,h_i),\qquad V_2(t_i)=\mathbb{1}[\tau_i\ge\delta].$$
   主实验 $\delta=0.5$,`max_length=256`,`stride=128`。

5. **联合判定**:$\ell_i=\mathrm{PASS}\iff V_1(t_i)\cdot V_2(t_i)=1$。

**和 baseline 相比多做了什么**:引入 $\sigma_i$ 作为强锚点;RTAV 中文谓词类型感知 verbalization;完全无监督;直接把审计器接到下游 KG-RAG QA 上测 answer-level 影响,而非只报 verifier F1。

**做过但没进主系统的路线**(体现研究深度,paper §5 已诚实报告):

- **v2 蒸馏**(Qwen-plus 软标签):proxy F1 高但下游 QA 三元组均量塌到 1.33,过度过滤,**主动放弃**——作为 proxy 指标与下游脱节的负面结论呈现。
- **RL span localization**:rule-based 已足够,RL 提不动。
- **Seq2Seq learnable RTAV**:小 T5 学不出可泛化模板;最终用"离线 LLM 生成候选 + NLI 筛选"的模板 bank 替代。

## 三、贡献边界(自己 vs 实现协作)

**可以主张"我主导"**:

- 问题定义与方法路径选择(为什么走 $\sigma_i$ + 两层验证,而不是蒸馏或纯 LLM judge)。
- SAR × EPR 分解口径与 SU-positive 评测框架的设计。
- RTAV 6 类中文谓词类型体系与方向反转规则的语言学动机。
- 实验设计:15,000 行受控 benchmark 构造(gold + fake-span / object-replacement / subject-replacement / predicate-mismatch 四类负例)、supported-loss budget 政策曲线、W1 real-span 语义幻觉补充实验、下游 QA 三条对照(`G_full` / `G_rand` / `G_tc`)。
- 负面结果的取舍与叙事策略(v2 蒸馏失败、RL 失败、unseen-schema 口径限制的诚实呈现)。
- 论文写作与主要结论定型。

**协作完成、方法层面归我**:

- 消融维度、阈值扫描范围、case study 挑选标准。
- Clustered bootstrap CI 与 paired t-test 的口径选择。

**如实说"具体实现细节可以事后查代码"**:

- LLM 缓存 hash 与缓存实现。
- LoRA 微调超参、`ignore_mismatched_sizes` 之类细节。
- Bootstrap 1000 次重采样具体代码路径。
- RL policy 的 action / reward 具体形式。
- Seq2Seq learnable RTAV 训练 recipe。

**话术**:被追问具体代码时不硬装——"方法层面的决定是我做的,具体超参和实现是我和 coding assistant 协作完成,可以打开代码走一遍"。

## 四、实验结果

### 4.1 受控 benchmark(paper §4.2, Table 2)

15,000 行受控 benchmark:DuIE2.0 + CMeIE + FinRE,每类 1000 篇文档抽 3000 条 gold,再合成 4 类 3000 条负例(`fake_span` / `object_replacement` / `subject_replacement` / `predicate_mismatch`),SU-positive 评测。

**主结果**(TripleChecker fixed $\delta=0.5$):

| 指标 | 值 | 95% CI |
|---|---|---|
| Pass-R | 0.811 | — |
| SU-R | 0.704 | — |
| **SU-F1** | **0.804** | [0.7989, 0.8091] |
| Accuracy | 0.725 | — |

对比 fixed-template baseline,paired delta **+0.005** [0.0009, 0.0096](clustered bootstrap 1000 resamples over (dataset, `doc_id`, `triple_id`))。

**按负例条件切片(SU-R)**:

| 条件 | Layer 2 拒绝率 |
|---|---|
| `fake_span` | 1.000 |
| `object_replacement` | 0.709 |
| `subject_replacement` | 0.604 |
| `predicate_mismatch` | 0.503 |

**Supported-loss budget 政策曲线**(paper §4.3):在 12,000 条 gold 上允许损失 25/50/100/250/500 条 supported,系统可正确拒绝的 SU 条数分别为 **3806 / 4337 / 5073 / 6625 / 8164**。政策曲线单调,给部署方在"召回幻觉"与"保留合法边"之间提供可调 knob。

### 4.2 人工校准(paper §4.4, Table 3)

- **200 条 DuIE 人工标注**:PASS-P/R/F1 = 0.694 / 0.970 / 0.809;SU-R / SU-F1 = 0.149 / 0.247。
- **扩展 383 条(Qwen 生成负例)**:SU-R 0.625,SU-F1 0.647。
- **50 条二人盲评校准子集**:标注者与审计器 label 一致 47/50;分歧 3 条由第三位裁定后并入。

### 4.3 RTAV 消融(paper §4.6)

fixed-template / LLM-only / **RTAV** 三档 verifier F1:**0.762 / 0.788 / 0.811**。RTAV 相对 fixed 提升 0.049,相对纯 LLM 提升 0.023。**Predicate-hiding split**:100 seeds 平均 +0.151 SU-F1,85/100 seeds 正增益,支撑"幻觉检测口径下对 unseen 谓词有增益"。

### 4.4 下游 QA 敏感性(paper §4.7)

100 篇文档、191 个 QA pair:

| KG | EM | 备注 |
|---|---|---|
| `G_full` | 0.482 | 未过滤 |
| `G_rand` | — | 随机过滤到同大小 |
| **`G_tc`** | **0.791** | TripleChecker 过滤 |

**+30.9 EM 点**;与 `G_rand` 对齐 KG 大小依然领先,收益来自语义过滤而非 KG 压缩。paired t 检验 $p\ll 0.001$,bootstrap 95% CI 不重叠。

**W1 real-span 语义幻觉补充实验**:注入 97 条真实 span 但语义替换的三元组,Layer 1 拒 0 / Layer 2 拒 **92**(recall **0.948**);`G_tc^{sem}` 0.780 vs `G_rand^{sem}` 0.555,**EM +22.5 点**——证明 Layer 2 具**独立下游贡献**。

### 4.5 面试锚点数字

- **SU-F1 = 0.804,95% CI [0.7989, 0.8091]**(主 headline)
- **paired delta 相对 fixed-template = +0.005 [0.0009, 0.0096]**
- **RTAV vs fixed vs LLM-only:0.811 / 0.762 / 0.788**
- **Layer 2 W1 recall = 0.948**
- **下游 EM:0.482 → 0.791(+30.9 点)**
- **Human calibration 200 条 DuIE:PASS-F1 = 0.809**
- 其他数字可以说"记不清,详细查 main.pdf Table 2/3"。

## 五、潜在追问与应对

- **Q1「完全依赖 $\sigma_i$,抽取系统不输出 span 怎么办?」**
  承认这是方法适用边界(paper §5 已限定)。现代能带 span 的抽取系统已普遍;不带 span 的老系统可用 rule-based fallback(取包含 subject 和 object 的最短窗口)。

- **Q2「SU-F1 = 0.804 看起来漂亮,但 SU-R 只有 0.704,漏检的是什么?」**
  按 Table 2 条件切片诚实回答:`fake_span` 已经 1.000;主要漏检在 `predicate_mismatch`(0.503)和 `subject_replacement`(0.604),因为这些负例在真实 $\sigma$ 下语义仍可能被 NLI 判为蕴含(尤其宽泛 span)。补丁方向是把 span 拉紧、把 RTAV 模板做得更谓词敏感。

- **Q3「跨域退化,方法是不是领域敏感?」**
  paper 已报告:v2 蒸馏在 FinRE 上退化(0.741 F1),原因是 Qwen-plus 对金融关系短 span 打软标签本身不稳定(56.8% 样本软标签 <0.5),**不是主系统方法失败**。主系统 v1(NLI 直接用)在 FinRE 上 F1 = 0.897 不退化。

- **Q4「unseen predicates 泛化怎么样?」**
  必须限定口径:PASS-positive + patched bank 上 bank 模板 0.783 **没超过** generic fallback 0.802;但 **hallucination-positive + prepatch bank** 上 100 seeds 平均 +0.151,85/100 正增益——**只在"幻觉检测口径"下声称对 unseen 谓词有增益**,不越界。

- **Q5「和 MiniCheck / FactScore 等 fact-checking 工作比?」**
  MiniCheck 中文 setting 基本失效;7B Bespoke 因显存没跑(诚实承认)。FactScore 是英文长文档场景,任务不同不直接可比。TripleChecker 的定位是"中文 KG triple source-faithfulness auditing 这个 sub-task"。

- **Q6「如果 $\sigma_i$ 本身也是编的?」**
  Layer 1 就是干这个的——不是原文子串直接拒。这也是为什么两层顺序不能倒;paper Table 2 中 `fake_span` 拒绝率 1.000 印证。

- **Q7「Broader failure modes?」**
  paper §5 诚实报告:200 条 human calibration 的 57 条 FN 中,**49/57 是宽泛 span**(span 过长导致 NLI 把 unrelated triple 也判 entail),**8/57 是 verbalization 方向错**。这是当前系统已知薄弱点。

## 六、电梯陈述

**30 秒**:

> 做的是中文 KG 抽取的**溯源保真度审计**——要求抽取系统对每条三元组给出溯源片段 $\sigma$,由审计器判断 $\sigma$ 是否真的支持这条三元组。方法是两层无监督验证:Layer 1 校验 $\sigma$ 是原文子串,Layer 2 用中文 NLI 判 $\sigma$ 是否蕴含由 RTAV(关系类型感知模板)复述出的中文假设句。图级得分 $\mathrm{Score}(G\mid D)$ 可分解为 SAR × EPR。在 15,000 行受控 benchmark 上 SU-F1 = 0.804(CI [0.799, 0.809]),下游 KG-RAG QA 上 EM 从 0.482 提到 0.791。

**3 分钟**(动机 → 方法 → 实验 → 局限):

1. **动机(30s)**:KG-RAG 主流化,但抽取自带幻觉;现成中文事实核查方法在 span-triple 设置下不 work。定义清楚:审计契约是"每条三元组是否由文档支持",而不是"事实上是否为真"。
2. **方法(1min)**:要求抽取系统同时输出溯源 $\sigma$ 作为强锚点;Layer 1 字符串匹配零成本兜底;Layer 2 用 `Erlangshen-RoBERTa-110M-NLI` 判蕴含,滑窗聚合用 max;RTAV 按 6 类粗粒度关系类型选模板,DuIE 字典覆盖 59.1%,未命中由离线 LLM 生成 + NLI 筛选的模板 bank 补齐;$\mathrm{Score}=\mathrm{SAR}\times\mathrm{EPR}$ 提供可解释的两级分解。
3. **实验(1min)**:三层证据。**受控 benchmark**——15,000 行,SU-F1 = 0.804,paired 相对 fixed-template +0.005 [0.0009, 0.0096],supported-loss budget 政策曲线单调。**人工校准**——200 条 DuIE PASS-F1 0.809,50 条盲评一致率 47/50。**下游 QA**——`G_tc` EM 0.791 vs `G_full` 0.482;W1 real-span 语义幻觉注入,Layer 2 独立召回 92/97 = 0.948,证明两层都必要。
4. **局限(30s)**:依赖抽取系统输出 span;蒸馏路线 proxy 与下游脱节,主系统仍用无监督 NLI;unseen predicate 泛化只在"幻觉检测口径"下声称;当前已知薄弱点是宽泛 span 导致的 NLI 过度蕴含(FN 49/57)与 verbalization 方向错(8/57)——诚实报告。

## 项目文件位置(备查)

- 项目根:`~/Evaluating_Knowledge_Graph_Extraction_via_Dual-Cycle_Consistency/TripleChecker/`
- 论文源码:`main.tex` / `main.pdf`
- 现状总表:`PROJECT_STATUS.md`
- 背景 briefing:`docs/BACKGROUND_FOR_CLAUDE_CODE (1).md`
- 核心实现:`triple_checker.py`(Layer1 + Layer2 + verbalize + evaluate)
- Case study:`results/case_study/case_summary.txt`

## 交叉引用

- [[知识图谱 KG]]
- [[知识图谱构建流程 KG Construction Pipeline]]
- [[文本蕴含与自然语言推理 NLI]]
- [[KG-RAG 工作原理]]
- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[归因评测 Attribution]]
- [[可验证性 Verifiability]]
- [[RAGChecker]]
- [[MiniCheck 高效事实核查]]

## 更新记录

- 2026-07-20: 从占位页扩为完整项目备忘(问题定义 / 方法 / 贡献边界 / 实验 / 追问 / 电梯陈述),用于保研套磁与面试脱稿准备
- 2026-07-20: 移除「七、代码级深度回顾」附录,决定以论文口径为准(codebase 级细节暂不纳入知识页)
- 2026-08-03: 交叉引用新增 [[MiniCheck 高效事实核查]]（英文 baseline，中文 setting 已在 Q5 记录为失效）
- 2026-07-20: 按 main.pdf 重写主内容——以 SU-F1 = 0.804 on 15,000 行受控 benchmark 为主 headline,替代早期 PROJECT_STATUS.md 的「EM 0.47→0.79」叙事;补齐 SAR × EPR 分解、Table 2 条件切片、supported-loss budget 曲线、Table 3 人工校准、RTAV 消融口径、paper §5 已知失效模式
