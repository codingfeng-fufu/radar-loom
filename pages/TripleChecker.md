---
摘要: 中文KG抽取幻觉检测的两层无监督验证器,一作论文,投稿NLPCC 2026。
来源: ~/Evaluating_Knowledge_Graph_Extraction_via_Dual-Cycle_Consistency/PROJECT_STATUS.md
信度: 高
首次记录: 2026-07-20
tags: [项目, TripleChecker, KG, 可信度, 评测]
---

# TripleChecker

## 核心内容

TripleChecker 解决的是**大模型从中文文本抽取知识图谱时的三元组幻觉问题**。核心方法是一个**两层无监督验证器**:Layer 1 校验抽取系统返回的溯源片段(`source_span`)确实是原文子串;Layer 2 用中文 NLI 判断这个片段是否语义蕴含把三元组"复述"出来的中文句子。中间关键组件是 RTAV(Relation-Type-Aware Verbalization),按谓词类型选中文模板,专门解决中文谓词多为名词导致固定模板方向反转的问题。

面向面试/套磁的口头讲解要点,按以下 6 块组织。

## 一、问题定义

- **要解决**:LLM 从文档抽 KG 时会编造原文里没有的三元组;这些幻觉三元组进入下游 RAG 会污染答案。目标:**无需人工标注**自动过滤幻觉。
- **现有方法为什么不够**:
  - 只看 subject/object 是否在原文,拦不住"关系幻觉"(主客体真实、关系伪造)。
  - 通用 NLI 直接搬会踩中文谓词是名词的坑,固定模板方向反转,例如 `(马云, 创始人, 阿里巴巴)` 用"X 的 Y 是 Z"会被读成"马云的创始人是阿里巴巴",NLI 拒真。
  - 现成事实核查模型在中文 span-triple 设置下几乎失效,MiniCheck RoBERTa-Large 实测 F1 约 0.140,PASS 召回 7.7%。
- **两个 failure case**:
  1. **关系冲突型**(论文 case study):文档讲天城公主嫁国峻,LLM 同时抽出 `(天城公主, 丈夫, 国峻)` 与 `(天城公主, 丈夫, 温鹏程)`;`G_full` 答"温鹏程",`G_tc` 过滤后答"国峻"。
  2. **同谓词 object 替换的 real-span 语义幻觉**:把 gold object 换成另一篇文档同谓词的 object,`source_span` 依然真实。Layer 1 完全拦不住,只有 Layer 2 能过滤(实测 Layer 2 recall 0.948)。

## 二、核心方法

- **一句话**:`source_span` 作为强锚点 + Layer 1 字符串校验 + Layer 2 NLI 蕴含验证 + RTAV 中文类型感知模板。
- **关键步骤**:
  1. **抽 KG 时同时输出 `source_span`**(方法前提,现代 LLM 抽取系统能做到)。
  2. **Layer 1(字符串匹配)**:span 必须是原文子串。零成本、放最外层,先干掉伪造来源。
  3. **RTAV verbalize**:按谓词词典判"关系类型"(身份归属/属性描述/事件参与等 6 类),每类不同模板;词典外由 LLM 零样本分类。这一步 baseline 做不到 — 固定模板在中文名词谓词上必然踩雷。
  4. **Layer 2(NLI 蕴含)**:用 `Erlangshen-Roberta-110M-NLI` 判 span 是否蕴含 verbalized 句子;长文档滑窗聚合用 `max`(实测 max F1 0.837 > mean 0.662 > majority 0.475),因为支持证据通常只在局部窗口。
- **和 baseline 相比多做了什么**:引入 `source_span` 作为强锚点;中文谓词类型感知 verbalization;无需人工标注;直接测下游 KG-RAG QA 影响,不只是 verifier 层面。
- **做过但没进主系统的路线**(体现研究深度):
  - Phase 2/2b 蒸馏(Qwen-plus 软标签):proxy F1 0.962 但下游 QA 三元组均量掉到 1.33,过度过滤,**主动放弃**。作为论文负面结论呈现,提醒 proxy 指标与下游脱节。
  - Phase 3 RL span localization:rule-based 已够好,RL 提不动。
  - Phase 5 Seq2Seq learnable RTAV:小 T5 学不出可泛化模板;最终用"离线 LLM 生成候选 + NLI 筛选"的模板库替代。

## 三、贡献边界(自己 vs 实现协作)

**可以主张"我主导"**:

- 问题定义与方法路径选择(为什么走 `source_span` + 两层验证,而不是蒸馏或纯 LLM judge)。
- RTAV 6 类中文谓词类型体系与方向反转规则的语言学动机。
- 实验设计:主实验三条对照(`G_full` / `G_rand` / `G_tc`)、W1 real-span 语义幻觉补充实验(堵审稿人对 Layer 1 独立贡献的质疑)、跨域测试(CMeIE / FinRE)的动机。
- 负面结果的取舍与叙事策略(v2/v2b 失败、RL 失败、unseen split 口径限制的呈现方式)。
- 论文写作与主要结论定型。

**协作完成、方法层面归我**:

- 消融维度选择、阈值扫描范围、case study 挑选标准(full 错/rand 错/tc 对且同谓词 object 冲突)。
- Bootstrap CI 与 paired t-test 的口径选择。

**如实说"具体实现细节可以事后查代码"**:

- LLM 缓存 hash key、缓存实现细节。
- LoRA 微调超参、`ignore_mismatched_sizes` 之类细节(`train_verifier.py`、`phase2_train.py`)。
- Bootstrap 10000 次重采样代码路径。
- RL policy 的 action space / reward 设计具体形式(`phase3_rl_train.py`)。
- Seq2Seq learnable RTAV 训练 recipe(`learnable_rtav_train.py`)。

**建议话术**:被追问具体代码时不硬装 — "方法层面的决定是我做的,具体超参和实现是我和 coding assistant 协作完成,可以打开代码走一遍"。

## 四、实验结果

**主实验(Table 6,Phase 4,DuIE2.0,100 篇文档 + 30% 注入幻觉)**:

| KG | EM | F1 | AC | 三元组均量 |
|---|---|---|---|---|
| `G_full`(未过滤) | 0.471 | 0.671 | 0.848 | 4.62 |
| `G_rand`(随机过滤到同大小) | 0.482 | 0.581 | 0.618 | 3.10 |
| **`G_tc`(TripleChecker)** | **0.791** | **0.868** | **0.937** | 3.10 |

要点:EM 提升约 32 个点、AC 提升约 9 个点;与 `G_rand` **对齐 KG 大小(都 3.10)**依然大幅领先,证明收益来自**语义过滤而非 KG 压缩**;配对 t 检验 p 值远低于 0.001,Bootstrap 95% CI 不重叠。

**Verifier F1(Table 3,200 条人工标注,PASS-positive)**:

- RTAV v1 固定模板 + NLI:F1 0.769
- **RTAV-v2 prepatch bank(离线 LLM 生成 + NLI 筛选)**:F1 0.811
- MiniCheck RoBERTa-Large:F1 0.140(基本失效)

**W1 real-span 语义幻觉实验(最关键的辩护)**:

- 注入 97 条 real-span 语义幻觉,**Layer 1 拒 0,Layer 2 拒 92,recall 0.948**。
- 下游 QA:`G_tc_sem` vs `G_rand_sem`,EM 提升 0.225 / F1 提升 0.211 / AC 提升 0.215。
- 说明 Layer 2 具**独立下游贡献**,不是字符串匹配在起作用。

**滑窗聚合消融(CMeIE 长文档)**:max 0.837,mean 0.662,majority 0.475,支持"证据局部化"直觉。

**面试锚点数字**:EM 从 0.47 提到 0.79、Table 3 F1 0.811、MiniCheck F1 0.14、Layer 2 recall 0.948。其他数字可以说"记不清,详细查 `PROJECT_STATUS` 表"。

## 五、潜在追问与应对

- **Q1 "完全依赖 `source_span`,抽取系统不输出 span 怎么办?"**
  承认这是方法适用边界。现代能带 span 的抽取系统已经普遍;不带 span 的老系统有 rule-based fallback(取包含 subject 和 object 的最短窗口)。

- **Q2 "v2 蒸馏 proxy F1 0.962 下游反而变差,评估指标是不是有问题?"**
  这恰是我们主动报告的负面结论,想说的正是"proxy verifier F1 与下游 KG-RAG QA 不一致"。这是**评估方法学层面的贡献**,负结论正着讲。

- **Q3 "跨域退化,方法是不是领域敏感?"**
  v1(NLI 直接用)在 FinRE 上 F1 0.897 没退化;退化的是 v2 蒸馏版本(0.741)。根因是 Qwen-plus 对金融关系短 span 打软标签本身不稳定(56.8% 样本软标签低于 0.5),不是主系统方法失败。

- **Q4 "unseen predicates 泛化怎么样?"**
  必须限定口径。PASS-positive + patched bank:held-out 上 bank 模板 0.783 **没超过**generic fallback 0.802,不能强说泛化。但 hallucination-positive + prepatch bank:100 seeds 平均 F1 0.455 vs 0.304,**提升 0.151,85/100 seeds 正增益**,可支撑"幻觉检测任务上对 unseen 谓词有增益"。两种口径务必分清。

- **Q5 "和 MiniCheck / FactScore 等 fact-checking 工作比?"**
  MiniCheck RoBERTa-Large 中文 setting F1 0.140 基本失效;7B Bespoke 因显存没跑(承认)。FactScore 是英文长文档场景,任务不同不直接可比。定位为"中文 KG triple verification 这个 sub-task"。

- **Q6 "如果 span 也是编的?"**
  Layer 1 就是干这个的 — 不是原文子串直接拒。这也是为什么两层顺序不能倒。

## 六、电梯陈述

**30 秒**:

> 做的是大模型抽知识图谱时的幻觉检测。LLM 抽出的三元组会编造出原文没有的关系,喂给下游 RAG 会污染答案。我们提出 TripleChecker,一个不需要人工标注的两层验证器:第一层验证抽取系统返回的溯源片段是不是原文真实子串,第二层用中文 NLI 判断这个片段是否语义蕴含把三元组复述出来的中文句子。在 DuIE2.0 上过滤后再做 KG-RAG 问答,EM 从 0.47 提到 0.79,而且和同大小随机过滤对比依然大幅领先,说明收益来自语义过滤本身。

**3 分钟**(动机 → 方法 → 实验 → 局限):

1. 动机(30s):KG-RAG 主流化,但 KG 抽取自带幻觉;现有中文事实核查方法不 work,MiniCheck 中文 F1 只有 0.14。
2. 方法(1min):关键是要求抽取系统同时输出溯源片段作为可核对锚点;Layer 1 字符串匹配零成本兜底;Layer 2 用 NLI 判断蕴含;RTAV 按谓词类型 6 类选模板,解决中文名词谓词方向反转。
3. 实验(1min):三层证据 — verifier 层 F1 0.811 超过 MiniCheck 和固定模板;下游 QA EM 从 0.471 提到 0.791,与同大小随机过滤对比 +30 个点证明收益来自语义过滤;real-span 语义幻觉注入实验证明 Layer 2 单独就能撑起 QA 收益,两层都必要。Bootstrap 95% CI 与 paired t-test 支持结论。
4. 局限(30s):依赖抽取系统输出 span;蒸馏路线 proxy 与下游脱节主系统仍用无监督 NLI;unseen predicate 泛化需限定"幻觉检测口径"讲,不过度声称。诚实报告。

## 项目文件位置(备查)

- 项目根:`~/Evaluating_Knowledge_Graph_Extraction_via_Dual-Cycle_Consistency/`
- 现状总表:`PROJECT_STATUS.md`(所有实验结果与决策记录)
- 论文源码:`main.tex` / `main.pdf`
- 背景 briefing:`docs/BACKGROUND_FOR_CLAUDE_CODE (1).md`
- 核心实现:`triple_checker.py`(Layer1 + Layer2 + verbalize + evaluate)
- Case study:`results/case_study/case_summary.txt`


---

# 七、代码级深度回顾(2026-07-20 深挖)

以下内容来自 2026-07-20 与 Claude Code 的会话记录逐节深挖,面向"每一个实现细节都能被面试官追问到"的准备场景。每节末尾保留原有确认题,便于日后复读时定位仍需检验的理解点。

勘查够了,开始 §1。这一节把"这个代码库长什么样、每块干嘛、数据怎么流"讲清楚,后面几节都建立在这张地图上。

---

# §1【整体代码结构】

## 0. 一个先决要点:你面前其实是**两套代码库**

这是理解结构的最大前提,你如果一开始没意识到,读代码会到处踩空。

- **研究工作区**:`~/Evaluating_Knowledge_Graph_Extraction_via_Dual-Cycle_Consistency/`(以下简称 **R**)。这是**开发过程**的仓库:有 phase1/2/2b/3/4/5 全套试错脚本、蒸馏训练、RL 训练、learnable RTAV、bootstrap CI、MiniCheck 对比、Phase 4 case study 提取等等。文件比较散,没有 Python 包结构,全部是顶层脚本(`triple_checker.py`、`phase2_train.py` 之类)。
- **发布仓库**:`~/Evaluating_.../TripleChecker/`(以下简称 **P**,`P` for Publish)。这是**投稿时清洗出来的最终产物**:标准的 Python 包结构(`triplechecker/` + 兼容别名 `tripplechecker/`)、干净的 `scripts/`、`tests/` 全套单测、`main.tex` 论文源、`README.md`、`pyproject.toml`。审稿之后的 rebuttal 补充实验(`rebuttal_exp/`、`results/accept_sprint/`)全都住在这里。

**关键差异**:
- **主系统实现**在 P 的 `tripplechecker/verifier.py` + `tripplechecker/rtav.py`(两个文件合起来才 250 多行)。这是"最终版"实现。
- R 里的 `triple_checker.py`(顶层大文件)是**开发版本**,包含很多探索性代码(缓存、多种 span 定位 fallback、RL 相关接口、v2b 蒸馏模型加载函数等等)。这些多余功能**没有进论文主系统**,论文里报的所有主表数字都是用 P 的 `tripplechecker.TripleChecker` 类跑出来的。
- 名字为什么有 `triplechecker` 和 `tripplechecker` 两个包?README 的原话是"历史命名 `tripplechecker`(两个 `p`,拼写错了),对外正式包名 `triplechecker`(正确拼写)"。真实的类和函数**只定义在 `tripplechecker/` 里**,`triplechecker/` 只是转发导入。发布时不想改历史 import 路径,又不想让 GitHub 上出现拼错的包名,所以两个都留着。这是**技术债、不是研究上的**,面试遇到"为什么有两个包"直接答"命名迁移的兼容层"就行。

面试如果被问"你的代码在哪",答**P**(clean release),但要能说得出 R 里做过哪些没进主系统的探索(蒸馏、RL、Seq2Seq),这才显示深度。

后面所有内容我以 **P** 为主叙述,涉及 R 时会明确标出。

---

## 1. P(发布仓库)的目录职责

### 1.1 顶层
```
TripleChecker/
├── main.tex / main.pdf         # 论文 LaTeX 源与编译产物
├── README.md                   # 使用文档
├── RELEASE_MANIFEST.md         # 说明"什么进了发布包、什么没进"
├── pyproject.toml              # 包元数据(可 pip install -e .)
├── requirements.txt            # 依赖
├── LICENSE (MIT)
├── references.bib / splncs04.bst / llncs.cls   # LaTeX 文献与模板
├── 77_TripleChecker_A_Source_Grou.pdf         # 早期投稿版本存档
```

### 1.2 核心 Python 包(**方法的全部实现**)
```
tripplechecker/                 # 真正定义
├── __init__.py                 # 只 re-export TripleChecker, RTAVModule
├── verifier.py    (165 行)     # TripleChecker 类:两层验证 + 滑窗 NLI
├── rtav.py         (86 行)     # RTAVModule 类 + 6 组关系模板 + fallback
└── utils.py        (68 行)     # 读写 JSON/JSONL、normalize_triple、metric_bundle

triplechecker/                  # 别名(全部只是 from tripplechecker import *)
```
**关键事实**:**整个方法的核心逻辑只有 250 多行**。这不是我夸张,你 verifier.py 通读一遍就知道:类初始化、`verify()`、`score()`、`score_pairs()`、`_premise_windows()`、`_resolve_entailment_index()` — 就这些。RTAV 只有一个 dict + 一个 dispatch 函数 + 一个 verbalize 方法。**这是论文的一个卖点也是一个软肋**:方法极其简单,方法层面基本无参数可训练 — 卖点是"training-free、易复现";软肋是审稿人会质疑"这也算贡献?"。后面 §3 我会展开讲怎么应对。

### 1.3 CLI 工具与实验重跑脚本
```
scripts/
├── run_verification.py          # 用法示范:读一个 JSON(document+triples) → 输出验证结果
├── evaluate.py                  # 在人工标注 JSONL 上跑指标(P/R/F1)
├── validate_accept_claims.py    # ★ 无 API,重算论文所有 accept_sprint 数字并核对
├── build_rtav_bank.py           # 从 LLM 输出构造 RTAV 模板库
├── build_source_span_benchmark.py     # ★ 构造 15,000 行受控 span 基准(Table 1/2)
├── score_source_span_benchmark.py     # 用 TripleChecker 给基准打分
├── score_source_span_template_baselines.py  # 用固定模板 baseline 打分(对比用)
├── analyze_source_span_benchmark.py   # 从打分结果算论文表 1/2
├── compare_source_span_methods.py     # 方法级对比 + paired bootstrap
├── audit_source_span_errors.py        # 错误分类审计(fake_span vs 语义不支持)
├── source_span_paper_tables.py        # 生成论文里的表格 CSV
├── source_span_policy_base_rate.py    # 阈值扫描 + 不同 base rate 下 policy 敏感度
├── source_span_label_audit_*.py       # 4 个:采样审计、双盲复标、汇总、噪声敏感度
├── source_span_rtav_heldout.py        # RTAV bank 泄漏诊断的 held-out 版本
├── source_span_rtav_leakage_diagnostic.py  # 泄漏诊断(unseen predicate)
├── rtav_bank_provenance_audit.py      # RTAV bank 出处审计
├── natural_noise_pipeline.py          # ★ 自然噪声 pilot:抽取 → 标注 → 评估
├── natural_noise_extractor.py         # 用 Qwen2.5-3B 做本地抽取
├── natural_noise_human_audit.py       # agent 审计(命名叫 human 是历史遗留)
├── natural_noise_human_audit_adjudication.py  # 双 agent 复审 + 第三方裁决
├── natural_noise_baseline_sensitivity.py     # 自然噪声下 baseline 敏感度
├── natural_noise_calibration_50.py    # 阈值校准
├── accept_sprint_analysis.py          # ★ 200 例人工标注全套分析(paired、slice、CI等)
```
`★` 是主要入口(论文数字直接从它们出)。其他要么是 helper 要么是审计脚本。

### 1.4 补充实验(rebuttal 阶段)
```
rebuttal_exp/
├── verification.py / reverification.py       # 主 rebuttal runner
├── verification_config.json / reverification_config.json  # 配置
├── audit.py                                    # 审计
├── common.py                                   # 共用工具
├── manifest.json                               # 描述所有子实验
├── e1/  自我一致性 + 全文档 vs. 仅 span 对比 + Qwen 探索(未入论文)
├── e2/  两个 NLI backbone(Erlangshen-330 vs mDeBERTa)一致性
├── e3/  某项对比(具体内容看 conclusion.md,篇幅关系我下节再展开)
├── e4/  RTAV 方向诊断(direction_manifest 手工审批)
├── VERIFICATION.md / REVERIFICATION.md        # 详细说明
├── REBUTTAL_DRAFT_DEEPSEEK_ONLY.md            # DeepSeek 单模型 rebuttal 草稿
├── FINAL_NUMBER_CROSSCHECK.md                 # 论文数字与结果 CSV 交叉核对
```
这一块是**投稿后审稿人问题的针对性补跑**。要小心一件事:`rebuttal_exp/e1/` 里有 `QWEN_EXPLORATORY_NOT_FOR_REBUTTAL.md`,意思是**这部分 Qwen 结果只是探索,没进论文**;别在面试里把 e1 的 Qwen 数字当正式结果讲。

### 1.5 数据与结果
```
data/
├── rtav_bank/best_templates.json                # 发布的 RTAV 模板库(Table 3 用到)
├── human_annotations/                            # 空 — 用户自备(合规,不能发原始标注)
└── README.md                                     # 讲注解 schema

results/
├── claims_manifest.csv        # ★★★ 论文每条"claim → CSV 文件"的映射表
├── source_span_benchmark/     # ★ 15,000 行受控基准所有产物(主 Table 1/2 数字)
├── accept_sprint/             # ★ 200 例 DuIE 人工标注所有分析(Table 3/4/5)
├── natural_noise/             # 自然噪声 Qwen2.5-3B pilot(59 条)
├── natural_noise_expanded/    # 扩展版(383 条)
├── rtav_unseen_prepatch_hallucination_positive/  # unseen predicate 泛化
├── CMEIE_LLM_ANNOTATION_REPORT.md               # CMeIE 辅助标注报告
├── DIRECT_VERIFIER_BASELINE_REPORT.md            # 同例直接 baseline 对比
├── KG_RAG_INJECTED_NOISE_REPORT.md               # 受控注入噪声下游 QA
├── THRESHOLD_OPERATING_POLICY_REPORT.md          # 阈值 policy
├── RTAV_ABLATION_REPORT.md                       # RTAV 消融
├── SCORE_SENSITIVITY_REPORT.md
├── WINDOW_AGGREGATION_REPORT.md                  # max/mean/majority 滑窗聚合
└── README.md
```
`claims_manifest.csv` 是**你面试前必读的一份文件**:它把论文每一条 claim(比如 "Table 3 DuIE PASS F1=0.809")对应到一个 CSV 或 MD 报告,并写明数字是怎么算出来的。这个表**是你抵御"某某数字怎么来的"追问的杀手锏**。

### 1.6 测试
```
tests/          — 26 个测试文件,覆盖每个 scripts/ 下的分析脚本
```
测试主要是行为回归测试,不是 verifier 的方法测试。这一点值得注意 — 面试如果被问"你怎么保证方法正确性",诚实答"关键脚本有回归测试,主 verifier 逻辑只有 250 行手工审过,主要靠下游一致性和人工审计交叉验证"。

### 1.7 文档
```
docs/
├── main_tex_rewrite_map.md                       # 论文重写映射
├── nlpcc2026_reviewer_gated_next_plan.md         # 审稿意见与响应计划
├── nlpcc2026_simulated_review.md                 # 模拟审稿
├── paper_optimization_experiment_design.md       # 补跑实验的设计文档
└── superpowers                                   # 空目录(claude-code 遗留)
```
`nlpcc2026_reviewer_gated_next_plan.md` 是**面试前该重读的第二份关键文档** — 里面记录了审稿人的问题、我们的回应策略、每一个补跑实验的动机。这条链条对"为什么做 X 实验"这类追问是决定性的。

---

## 2. R(研究工作区)的相关目录(补充,面试可能被问到)

```
Evaluating_.../  (R 根目录)
├── triple_checker.py           # 开发版主入口(不同于 P 的 tripplechecker/)
├── build_training_data.py      # phase1 训练数据构造
├── train_verifier.py           # phase1 LoRA 微调 3-class NLI
├── phase2_build_pairs.py       # phase2 DuIE 打分对
├── phase2_llm_score.py         # qwen-plus 软标签
├── phase2_train.py             # phase2 蒸馏训练(2-class)
├── phase2_evaluate.py          # phase2 评估
├── phase2b_*.py                # phase2b 多域蒸馏(CMeIE+FinRE)
├── phase3_rl_train.py          # phase3 RL span localization
├── phase3_evaluate.py
├── phase4_*.py                 # phase4 下游 KG-RAG QA(6 个文件)
├── phase4_semantic_halluc.py   # W1 real-span 语义幻觉实验
├── phase4_rtav_v2_qa_rerun.py  # RTAV-v2 patched bank QA 复跑
├── learnable_rtav_*.py         # phase5 可学习 RTAV(6 个文件)
├── bootstrap_ci.py             # Bootstrap 10000 次重采样
├── bootstrap_table3_hallucination_ci.py  # hallucination-positive CI
├── rtav_unseen_split.py        # unseen predicate held-out
├── rtav_unseen_multiseed.py    # 100 seed 稳健性复核
├── minicheck_comparison.py     # MiniCheck 对比
├── supplementary_exp2.py       # CMeIE 字典命中 + 滑窗消融
├── extract_phase4_case_study.py  # Case study 提取
├── PROJECT_STATUS.md           # 全项目状态总表(2026-05-01)
├── data/, results/, cache/     # 数据、缓存、结果
```
**这一块和 P 的关系是"演进关系不是拷贝关系"**:R 里的 phase 1/2/2b/3/5 大部分**没有进论文主系统**;phase 4 QA 实验的部分产物被搬到 P 的 `results/KG_RAG_INJECTED_NOISE_REPORT.md`;bootstrap CI 和 unseen split 被 rewrite 成 P 里更规范的 `accept_sprint_analysis.py` + `source_span_rtav_heldout.py`。

**面试重要提醒**:R 里的 `PROJECT_STATUS.md`(日期 2026-05-01)是**审稿前的进展快照**,里面的主结论(比如 EM 0.47→0.79 那张 Phase 4 QA 表)在论文最终版里被**降级为"controlled downstream sensitivity analysis"**,不再是主 headline。论文真正的 headline 是**在 15,000 行受控基准上 source-unsupported F1=0.804**。这个叙事切换非常重要 — 我们在扩写的知识页里(pages/TripleChecker.md)其实还在用旧的 headline,面试前要按新版更正过来。

---

## 3. 调用/数据流关系

### 3.1 主验证路径(推理时,单例)
```
用户输入
  ├─ document: str
  └─ triples: [{subject, predicate, object, source_span}, ...]
        │
        ▼
tripplechecker.TripleChecker.verify()
  │
  ├─ 对每条 triple:
  │    ├─ Layer 1: span in document?  → 不在 → label=fake_span, 跳过 NLI
  │    └─ 通过 → RTAVModule.verbalize(s,p,o) 生成中文 hypothesis
  │
  ├─ 收集通过 Layer 1 的 (span, hypothesis) pairs
  │    → score_pairs()
  │         ├─ _premise_windows(): 对每个 span 按 max_length=256, stride=128 切窗
  │         ├─ _score_flat_pairs(): batch=32 过 NLI 模型
  │         ├─ 拿 entailment 概率(通过 _resolve_entailment_index 定位维度)
  │         └─ 每条 triple 的多窗口分数取 max
  │
  └─ score >= threshold(默认 0.5) → label=pass; 否则 hallucination
        │
        ▼
输出: [{label, score, layer1_pass, hypothesis}, ...]
```
`TripleChecker.score(triples, D)` 是一个额外的封装,返回论文里的 $\Score(\mathcal{G}|D)$ = 通过率(SAR × EPR)。

### 3.2 论文数字生产链(离线,评估用)
```
[人工标注 JSONL: DuIE 200 条 / CMeIE / natural_noise]
        │
        ▼
scripts/evaluate.py  ─── 单个数据集简单跑分
        │
        ▼
[per-row scores CSV]
        │
        ▼
scripts/accept_sprint_analysis.py     ─── DuIE 200 例的全套分析
   │      (阈值扫描 / bootstrap CI / paired McNemar / label robustness /
   │       predicate slice / label ambiguity / high-retention / paired scorer)
   ▼
results/accept_sprint/*.csv
        │
        ▼
scripts/validate_accept_claims.py  ─── 交叉核对 main.tex 里的每个数字
```

### 3.3 受控基准生产链(Table 1/2 主数字)
```
DuIE + CMeIE + FinRE 三个数据集的 gold triples
        │
        ▼
scripts/build_source_span_benchmark.py
   │  合成 4 类失败条件:
   │    - fake_span     (span 不在原文)
   │    - object_replacement    (real span,object 换成同谓词他家的)
   │    - subject_replacement   (同上,换 subject)
   │    - predicate_mismatch    (predicate 换)
   │  + 保留 supported 作为对照
   │
   ▼
results/source_span_benchmark/benchmark.jsonl   (15,000 行)
        │
        ▼
scripts/score_source_span_benchmark.py
   + scripts/score_source_span_template_baselines.py
        │
        ▼
results/source_span_benchmark/scored.jsonl
        │
        ├─ scripts/analyze_source_span_benchmark.py  → paper_main_policy_table.csv / metrics_by_condition.csv
        ├─ scripts/source_span_paper_tables.py       → paper_condition_table.csv
        └─ scripts/compare_source_span_methods.py    → paired_method_deltas.csv
```

### 3.4 自然噪声 pilot(Table 3 一行 + 附录)
```
20 篇 DuIE 文档
        │
        ▼
scripts/natural_noise_extractor.py (Qwen2.5-3B 本地) → local_qwen25_3b_extraction_cache.jsonl (59 条 triple)
        │
        ▼
scripts/natural_noise_human_audit.py (agent 标注) → local_qwen25_3b_annotation_batch_labeled.jsonl
        │
        ▼
scripts/natural_noise_human_audit_adjudication.py (第二 agent 复审) → 审计报告(59/59 一致)
        │
        ▼
scripts/natural_noise_pipeline.py 打分 → local_qwen25_3b_summary.json (F1=0.861)
```

---

## 4. 一张 mental map,记住三条主线

面试时脑子里保留这三条线就不会乱:

1. **主线 A(方法核心)**:`tripplechecker/verifier.py` + `tripplechecker/rtav.py`。总共 250 行,教一个新人看懂只要 20 分钟。**方法本身就这么点**,论文卖的不是复杂算法,是"简单+可审计+管用"。

2. **主线 B(数字生产)**:三条独立评估通路 — (i) 15,000 行受控基准(主 Table)、(ii) 200 例人工标注(Table 3 DuIE 行 + Table 4/5 policy 分析)、(iii) 自然噪声 pilot(Table 3 一行)+ CMeIE aux(Table 3 一行)。每条通路都在 `results/` 下有独立子目录,每条都有对应的 analysis script。

3. **主线 C(可复现审计)**:`results/claims_manifest.csv` + `scripts/validate_accept_claims.py`。这是**投稿后应审稿人要求做的可审计层**,做了就有,不做就是"trust me bro"。这一块的存在本身就是加分项(体现工程严谨)。

---

**§1 讲完**。这一节的目的是把地图立起来,后面每一节都是在这张地图上钻某一块。

请你确认一下:
- 上面的目录/文件角色划分你能对上号吗?
- 特别是"两套代码库(R 开发版 vs P 发布版)"这个前提有没有理解?
- 现在的论文 headline 是**受控基准 15,000 行,SU F1=0.804**,不是原来 `PROJECT_STATUS.md` 里的下游 QA EM 0.47→0.79 — 这个叙事切换你还记得吗?

**下一节我建议按这个顺序钻**:先讲 `verifier.py`(整个方法的心脏,15-20 分钟能说透),再讲 `rtav.py`(第二重要),然后 `build_source_span_benchmark.py`(数字生产的入口)。你可以给我不同的排序,或者告诉我"直接继续第二节的第一模块"我就往下走。

好,进 §2 第一个模块。这一节我会讲得比较细,因为这是整个方法的"心脏",面试被问深了都从这里问下去。

---

# §2 逐模块深挖 — 模块 1:`tripplechecker/verifier.py`(核心类)

## 一、这个模块对应论文里的哪一部分

- **§3.2 Two-Layer Verification**(整节)—— 是这个类的核心业务。
- **Fig. 1 pipeline** —— 就是这个类 `verify()` 的执行流程图。
- **Eq. 1 (V₁)** —— `verify()` 里的 Layer 1 判定,`span in document`。
- **Eq. 2 (V₂)** —— `score_pairs()` 里的 NLI 打分 + 窗口 max 聚合。
- **Eq. 3 (Score = SAR × EPR)** —— `score()` 方法直接实现。
- **§4.1 Setup 里的一段参数** —— `max_length=256`, `stride=128`, `threshold δ=0.5`,以及 max aggregation 的选择依据(F1 0.837 vs 0.662 vs 0.475)。

一句话:**论文方法节讲的所有可执行内容,全在这一个类里,共 165 行**。

## 二、模块的整体结构与做什么

这个类只对外暴露 3 个公开方法,其余是内部工具方法。你面试如果需要"从 API 讲起",就抓这三个:

1. **`verify(triples, document)`** —— 主入口。喂进一组带 `source_span` 的三元组和它们的原文档,吐出每条 triple 的验证结果。这是**推理时**的唯一入口。
2. **`score(triples, document)`** —— 一个薄封装,把 `verify()` 的输出汇总成一个论文 Eq. 3 里的 $\Score(\mathcal{G}|D)$ 标量,用来给一整张 KG 打一个 faithfulness 分。
3. **`score_pairs(pairs)`** —— 底层能力,直接接受 (premise, hypothesis) 对列表跑 NLI。之所以暴露出来,是因为下游有些评估脚本(比如 `evaluate.py` 面对已经预打过 span 的 JSONL,或者要评估**别的 verbalization** 时)不需要走 Layer 1,直接调它更方便。这是**工程解耦**,不是方法层面的东西。

内部方法(不对外):
- **`_score_flat_pairs(pairs)`** —— 真正调 NLI 模型的地方,负责 tokenize、batch、softmax、取 entailment 那一维。
- **`_premise_windows(premise, hypothesis)`** —— 滑窗切分。
- **`_resolve_entailment_index()`** —— 定位模型输出的哪个维度对应"entailment"标签。别小看这一个内部方法,它是**踩过大坑之后才写出来的**,后面讲。

## 三、`__init__`:所有可调参数的入口(**必须记熟**)

面试**必问**"你的 verifier 有几个超参、每个默认值是多少、为什么这么定":

- **`nli_model="IDEA-CCNL/Erlangshen-Roberta-110M-NLI"`**:默认 NLI 主干。选它的理由:(a) 中文原生 NLI 模型,不用做跨语言迁移;(b) 110M 参数够小,推理成本可控;(c) 是 Hugging Face 上下载量最高的中文 NLI 之一,可复现门槛低。**替代方案**试过 mDeBERTa(多语言 XNLI 微调版),在 `rebuttal_exp/e2/` 里做过一致性对比,结论是两者相关性高但存在系统性偏差,不作为主干替换,仅作 backbone 敏感度分析。**面试如果被问"为什么不用更大的中文 NLI"**,答:选 110M 是为了让"方法极简 + 可复现"这个卖点站得住;更大的 NLI 是"扩展方向"不是"主张"。

- **`rtav_bank=None`**:一个可选的离线模板库 JSON 路径。**默认 `None` 是关键设计**:类默认走 `rtav.py` 里硬编码的 6 类关系词典 + 通用 fallback(即论文里的 RTAV-base)。传入 bank 路径才是"完整 RTAV"。这个默认值把"最小可用"和"最佳"分开了,方便 ablation。

- **`threshold=0.5`**:Layer 2 的判定阈值 $\delta$。**论文里所有主表数字都用 0.5(fixed operating point)**。**关键陷阱**:你面试如果说"我们扫了阈值选最好的",错了 — 主表是**固定**在 0.5,不是选出来的;阈值扫描的产物在 `results/accept_sprint/triplechecker_threshold_sweep.csv`,是**独立的敏感度分析**,不是主指标。这个区分很重要,因为审稿人问过。

- **`max_length=256`**:NLI 模型的最大输入 token 数。为什么是 256?Erlangshen 支持 512,但 (a) 大部分 span+hypothesis 加起来远短于 256,(b) 用 256 能让 batch=32 装进单张 3090/4090 的 24GB 显存里,(c) 更长的 span 用滑窗切分而不是硬切一刀。

- **`window_stride=128`**:滑窗步长,正好是 `max_length` 的一半 = **50% overlap**。这是很常见的选择,理由是"任何证据句最长也就一两句,50% overlap 保证一定被至少一个窗口完整包含"。**替代方案**:更小 stride(比如 64,75% overlap)理论上更保守,但推理成本翻倍;更大 stride 有漏掉证据的风险。没跑过完整的 stride 扫描,是**已知的经验性选择**(§6 会点)。

- **`batch_size=32`**:纯工程参数。

- **`device`**:自动 cuda。

- **`entailment_index`**:通过 `_resolve_entailment_index()` 自动定位,不是超参。

**踩过的坑**:早期没有 `_resolve_entailment_index`,phase 2/2b 蒸馏出来的 2-class 分类器把 entailment 放在 index 1,而 3-class NLI 是 index 2。**代码里硬编码 `ENTAIL_IDX=2` 导致 phase 2 早期的评估**用错维度**,proxy F1 全乱**。定位到这个 bug 花了大半天,后来干脆写成从 `model.config.id2label` 里查关键词("entail" / "蕴含"),查不到再按 `num_labels` 猜。这是一个非常真实的、也很有面试价值的工程细节 —— 被问"你觉得最容易出 bug 的地方在哪"可以直接讲这个,反映"我知道方法看着简单但工程里到处是坑"。

## 四、`verify()` 的完整执行逻辑

按 `verify(triples, document)` 的调用顺序:

**Step 1(双遍扫描的第一遍)**:逐条 triple 走一遍:
- 取出 `source_span`(容错空值 / None,统一转成 str)。
- **Layer 1 判定**:如果 `document` 传入了,判 `span in document`(Python 子串包含,严格逐字符匹配,不做任何 normalization);如果 `document=None`,退化成"span 非空即视为通过 Layer 1"(评估 JSONL 走这条路,后面解释)。
- **不管 Layer 1 通不通过,都先调 `RTAV.verbalize(s, p, o)` 生成 hypothesis**。为什么先生成?因为 hypothesis 也作为返回结果的一部分(用户可能想审计"这个 triple 被 verbalize 成了什么句子");即使 Layer 1 失败,hypothesis 也会返回。这是**可审计性**的设计,不是性能考虑。
- 构造这条 triple 的"骨架结果字典":如果 Layer 1 失败,`label` 直接钉成 `"fake_span"`,`score=0.0`;否则 `label="pending"`,等第二遍填。
- 通过 Layer 1 的条目额外**登记到 `nli_items` 列表和 `nli_indices` 列表**里,准备批量走 NLI。

**Step 2(批量 NLI)**:一次性调 `score_pairs(nli_items)`,拿到 Layer 1 通过的那些条目的 entailment 概率数组。

**Step 3(第二遍扫描)**:把 NLI 分数按 `nli_indices` 回填到骨架里,`score >= threshold` 就贴 `"pass"`,否则贴 `"hallucination"`。

**这里有几个"为什么这么设计"值得展开**:

1. **为什么两遍扫描 + 中间批量 NLI?** 天真做法是一条 triple 一条 triple 挨个跑 NLI,推理开销爆炸(GPU 利用率极低,每次 forward 只有 batch=1)。改成"先收集所有 (span, hypothesis) 对 → batch=32 一起跑 NLI → 结果回填",在 200 条评估集上快 20-30 倍。看着是工程优化,但**它决定了这个方法能不能在实际部署里被用**,面试可以从这里过渡到"部署考虑"。

2. **为什么 `document=None` 要退化 Layer 1?** 因为发布数据集**不含 document 原文**(数据合规,DuIE 原始文档不能重分发)。评估脚本读的是"标注 JSONL",每条只有 (subject, predicate, object, `source_span`, `human_avg`) 这些字段,**没有原文档**。这种情况下 Layer 1 就无法验证 span 真伪 —— 但被 verify 的 triple 是审计流程里"抽取器已经给了 span"的记录,所以退化的语义是:"只要 span 非空就认为通过 Layer 1,把 NLI 判定的责任全交给 Layer 2"。**面试关键点**:这是**数据合规下的评估权衡**,不是方法本身的默认行为;线上部署时 document 一定传入,Layer 1 一定跑。这个区分在论文里没写得很清楚,是 §5 要提的"论文-代码微妙不一致点"之一。

3. **为什么 `hallucination` 是代码里的 label,论文里叫 `source_unsupported`?** 早期开发时全用 "hallucination" 一词(和 `PROJECT_STATUS` 里 phase 4 W1 "semantic hallucination" 那些实验同源),投稿后审稿人指出 "hallucination" 用词太大,建议用更精确的 `source_unsupported`(纯粹是"和源文档不一致"这个较窄含义)。**论文改了措辞,代码 label 字符串没改**(因为要动一堆下游脚本,懒得动)。这是**§5 一定要提到的论文-代码不一致点**,面试如果直接对着代码看,会看到 `"hallucination"` 一头雾水。

## 五、`score()` — 论文 Eq. 3 的 4 行实现

这个方法就是把 `verify()` 的结果按论文公式分解:

- **SAR(Span Authenticity Rate)** = Layer 1 通过率 = 通过 Layer 1 的条数 / 总条数。
- **EPR(Entailment Pass Rate)** = 在 Layer 1 通过的子集里,Layer 2 也通过的比例。
- **Score = SAR × EPR**。

论文里明说:**Score 数学上等价于"最终 PASS 数 / N"**(Eq. 3 下方那句)。为什么还要分解成 SAR × EPR?因为**分解出来能给审计诊断**:
- SAR 低 → 说明抽取器伪造 `source_span`(**抽取器可信度问题**)。
- SAR 高但 EPR 低 → 说明 span 是真的,但 NLI/verbalization 判它和 triple 语义对不上(**NLI 或 verbalization 问题**)。
- 两个都低 → 抽取器全线崩溃。

**面试价值**:这个分解是论文的一个"卖点包装" —— 同一个数字换个说法就多了一个诊断维度。方法本身没变复杂,故事变饱满了。这是论文写作技巧,**你要能主动把它 own 下来**:"我在设计 metric 时特意做了 factorization,这样一个数字能诊断两种不同的失败模式"。

**技术细节**:EPR 分母是 `max(Layer1 通过数, 1)`,处理"全部 Layer 1 都失败"的除零情形。论文脚注也提到这一点。

## 六、`score_pairs()` — Layer 2 的完整 NLI 打分链

这是**最容易被追问细节的部分**,一步一步过:

**Step A — 展开成"每对 (span, hypothesis) × 多个窗口"**:
- 对每一对 (premise=span, hypothesis),调 `_premise_windows()` 切成 k 个窗口(k≥1)。
- 把它们展平成一个大列表 `[(pair_idx, window, hypothesis), ...]`。原来 200 对 span-hypothesis,如果平均切出 1.2 个窗口,就变成 240 个待打分的三元组。
- **`pair_idx`** 是关键:它记住"这个窗口原本属于哪一对",这样最后聚合的时候能把窗口分数按原 pair 分组。

**Step B — 批量打分**:
- 调 `_score_flat_pairs(flat_pairs)` 走 NLI。返回每个窗口的 entailment 概率。

**Step C — 按 pair 聚合**:
- 把展平的窗口分数按 `pair_idx` 重新分组,得到每个原始 pair 的一个"窗口分数列表"。
- 每个 pair 的最终分数 = **窗口分数列表的 max**。空列表(某个 span 被切出 0 个窗口,极端情况)记为 0.0。

**关键设计:为什么 max 聚合?**
- 论文 §4.1 Setup 里的原话:"在 180 条 multi-window CMeIE triples 上,max 聚合 F1=0.837 vs mean 0.662 vs majority 0.475"。这是**做过消融**的选择。
- 直觉:如果支持证据只出现在某一个窗口里(通常就是这样,证据高度局部化),mean/majority 会被无证据的窗口稀释;max 天然把"是否有一个窗口支持"这个真实需求刻画出来。
- **潜在追问 Q**:"max 是不是太乐观,一个错窗口分数高就整个通过了?"应对:实测支持,而且这个方向的错误是 **false positive**(把不该 PASS 的判 PASS),下游 KG-RAG QA 层还会看到 triple 集合,单条误判不至于灾难;反过来 mean/majority 的 false negative(过滤掉真三元组)在下游是"直接答不出来",损伤更大。所以偏 recall 的 max 是符合任务方向的。

**这个聚合是硬编码的**,没有开关。面试如果问"能不能换",诚实答"代码没加接口,但改起来 5 行 —— 我们试过 mean/majority 数据在 `results/WINDOW_AGGREGATION_REPORT.md`"。

## 七、`_score_flat_pairs()` — NLI 的具体调用

标准 HuggingFace 流程,没什么魔法:
- `tokenizer(premises, hypotheses, ...)` 用 **sequence-pair 编码**(premise 是句 A,hypothesis 是句 B,中间自动插 `[SEP]`)。截断到 `max_length=256`,padding 到 batch 内最长。
- 走 `model(**enc).logits` 拿 logits,softmax 到概率。
- 取 `entailment_index` 那一维的概率,搬到 CPU 转 Python float。

**为什么 sequence-pair 编码**,不是拼字符串?因为 NLI 训练时就是 pair 输入,tokenizer 会加正确的 segment id 和 special tokens。字符串拼接是错的做法(会漏 segment id,漏 [SEP])。这个坑在开发初期踩过,后来所有 NLI 调用都统一走 pair 编码。

**torch.`inference_mode`()**:比 `no_grad()` 更彻底,禁用梯度追踪和 tensor version tracking,推理时更快、省显存。工程细节。

## 八、`_premise_windows()` — 滑窗切分的完整逻辑

Chinese NLI 的 tokenizer 用 WordPiece,中文基本是一字一 token(混合英文/数字时可能有 subword)。滑窗按 token id 切,不是按字符切,原因下面说。

**Step 1**:premise 和 hypothesis 都 tokenize 成 token id 列表。
**Step 2**:算 `special_tokens` 数量(pair encoding 需要 [CLS] + [SEP] + [SEP] = 3 个特殊 token 的位置)。
**Step 3**:`window_size = max_length - len(hypothesis_ids) - special_tokens`。这是给 premise 留的 token 预算。**动态计算而不是固定值**,因为 hypothesis 长度会变(不同 triple、不同 verbalization)。
**Step 4**:如果 premise 装得下,直接返回原字符串,一个窗口。**这是快路径 short-circuit**,避免不必要的切分开销。
**Step 5**:装不下,才滑。stride 是 `min(window_stride, window_size)`(万一 `window_size` 比 stride 还小,防止 stride 超过窗口造成漏)。
**Step 6**:逐窗切片,**每个窗口 token id 用 tokenizer decode 回字符串**,append 到窗口列表。到达末尾就 break。

**为什么切 token 再 decode 回字符串,不直接切字符串?**
- **保证进模型的每个窗口 token 数 ≤ `max_length`**,否则又要在 tokenizer 里再截一次,可能截掉证据。
- 字符和 token 数量不是 1:1(混合语言、数字、特殊字符),按字符切算不准。
- 代价是 decode 可能有 whitespace 或 subword 边界的美观问题,但因为 NLI 模型是从相同 tokenizer 训出来的,decode 后的字符串再 tokenize 一定跟原 token 序列一致 —— **对模型来说是无损的**,只是给人看时可能不好看。

**潜在坑**:decode 时 `skip_special_tokens=True`,`clean_up_tokenization_spaces=True`。如果 hypothesis 里含有会被 tokenizer 特殊处理的字符(比如某些 tokenizer 会把 `<>` 处理成 special token),可能导致 hypothesis 里的信息"消失"。实际用中文 predicate 时基本不会遇到,但值得知道。

## 九、`_resolve_entailment_index()` — 血泪教训的产物

这个方法只有 10 行,但存在的理由是**开发期真实的一个 bug**:

- **背景**:phase 2 蒸馏出来的模型是 2-class(supported/unsupported),Erlangshen 3-class NLI(entail/neutral/contradiction)。原代码 `ENTAIL_IDX=2` 硬编码。用蒸馏模型时,index 2 越界或指向错误维度,静默返回错误概率。发现时是**下游 F1 曲线奇怪 → 打断点看具体分数才发现的**。
- **修复思路**:先看 `model.config.id2label` dict,里面通常有类似 `{0: "contradiction", 1: "neutral", 2: "entailment"}` 或 `{0: "unsupported", 1: "supported"}` 的映射,**按 label 字符串包含 "entail" 或 "蕴含" 关键词找**。找不到就按 `num_labels` 兜底(3-class → 2,2-class → 1)。再找不到就用最后一维(避免崩)。
- **面试价值**:被问"你的代码考虑过健壮性吗"直接举这个例子。表达"我知道模型 backbone 会换,写通用的 index resolver 而不是硬编码 —— 是被 phase 2 那个 bug 教会的"。

## 十、上下游数据流(输入输出接口)

**上游(谁会调 `TripleChecker.verify()`)**:

1. `scripts/run_verification.py` —— CLI 单文件推理,输入一个 JSON(含 document 和 triples 数组),输出打分结果 JSON。使用场景:demo、单个 KG 检查。
2. `scripts/evaluate.py` —— 评估入口,输入标注 JSONL,**每行不含 document**(数据合规),因此走 `document=None` 路径,只跑 Layer 2。计算 P/R/F1(PASS-positive 和 SU-positive 双视角),吐 JSON 报告。
3. `scripts/score_source_span_benchmark.py` —— 15,000 行受控基准打分入口,**这里有 document**(基准是自己合成的,原文档保留),因此走完整 Layer 1 + Layer 2。
4. `scripts/natural_noise_pipeline.py` —— 自然噪声 pilot 的打分入口。
5. `rebuttal_exp/verification.py` / `reverification.py` —— rebuttal 阶段的打分驱动。
6. 大量测试文件 `tests/test_verifier_windows.py` 等 —— 保证 verifier 行为不回归。

**下游(消费 `verify()` 输出的谁)**:

1. `scripts/accept_sprint_analysis.py` —— 200 例 DuIE 全套分析(paired McNemar、bootstrap CI、label robustness、slice by predicate 等等)。**它不再调 verifier**,而是读**已经打过分的 CSV**再做统计。这是一种 pipeline 分离:打分和统计脱耦,统计脚本可以在没有 GPU 的机器上跑。
2. `scripts/analyze_source_span_benchmark.py` —— 15,000 行基准的 condition slice 分析。
3. `scripts/validate_accept_claims.py` —— 无 API 验证器,读所有 CSV 交叉核对论文数字。
4. 各种 `source_span_paper_tables.py` / `source_span_policy_base_rate.py` —— 从 CSV 出发生成论文表格。

**接口 schema**(记熟这个,被问"你的输入输出长什么样"可以直接背):

输入 triple(dict):
- `subject`, `predicate`, `object`(**必需**)
- `source_span`(可选,空字符串或 None 都合法,合法时会被 Layer 1 判)

输入 document(可选):
- 字符串;传 None 时跳 Layer 1。

输出 result(dict,和输入 triple 一一对应):
- `label`:`"pass"` / `"hallucination"` / `"fake_span"` 三选一。
- `score`:float,Layer 2 的 entailment 概率;Layer 1 失败时钉 0.0。
- `layer1_pass`:bool,方便下游做 SAR 统计。
- `hypothesis`:str,verbalize 出来的 NLI 假设;方便审计。

## 十一、面试可能被追问的点(集中列一下,方便你自己走一遍)

- Q: "为什么阈值定 0.5,不做校准?" → A: 论文里 0.5 是 fixed operating point,主表用它;敏感度分析在 `THRESHOLD_OPERATING_POLICY_REPORT.md`,包括不同 base rate 下的最优 threshold,以及"loss budget"policy(允许损失多少 PASS 换更多 SU 拒绝)。0.5 是"零调参基线",体现 training-free 卖点。
- Q: "max 聚合会不会过于乐观?" → A: 见前面第六节的应对。
- Q: "为什么不做 threshold learning?" → A: 加了就不是 training-free 了,方法卖点会打折。此外阈值 policy 是 deployment layer 的事,不是 method 的事。
- Q: "long span 切窗时如果证据横跨窗口边界怎么办?" → A: 50% overlap 是防这个的。极端长的证据超过 `window_size` 一半,才会漏 —— 但那意味着单个证据 >128 token(=中文 128 字左右),实测非常罕见。
- Q: "如果 NLI 模型判错(概率高但语义反了)呢?" → A: 分两种情况:(a) verbalization 方向反了 —— 这是 RTAV 该解决的,论文有单独讨论;(b) NLI 模型本身有偏 —— 这是 backbone 敏感度问题,`rebuttal_exp/e2/` 换 mDeBERTa 复跑过,结论是两个 backbone 一致性高,但确实存在 15-20% 的分歧,不能完全消解。诚实回答"我们用一个 backbone 的分数,不做 ensemble;ensemble 是可扩展方向,不是当前 claim"。
- Q: "verify 返回的 hypothesis 有什么用?" → A: 审计。让人工能一眼看到"这个 triple 被 verbalize 成了什么句子",这样 NLI 判错时能溯源到底是 verbalization 错还是 NLI 错。这是**可审计性 gate**的具体体现。

## 十二、这个模块的软肋(诚实说)

- **`score_pairs` 里 max 聚合硬编码**:改成可配置就 5 行代码,但没做,是**赶时间**。写论文时也承诺"max 已 ablation 过",没做进一步的 learned aggregation。
- **`_premise_windows` 的 stride 没系统扫过**:128 是"看着合理"选的,没跑过 32/64/128/256 全曲线。**面试如果被问"stride 敏感度",诚实说"没做过完整扫描,是经验值"**。
- **Layer 1 是严格子串匹配**:如果抽取器给的 span 只是 normalize 差异(比如全角/半角、繁体/简体、多个空格),Layer 1 直接拒。**没有 normalize 层**。这是设计上的严格,但实操中如果抽取器不干净会误伤。§6 会再点。
- **没有 confidence calibration**:NLI 输出的 softmax 概率**并不校准过**,0.5 阈值是选一个数,不是"预测概率 > 0.5 = 真的 50% 支持"这种意义。这块论文有意回避了"probabilistic guarantee",只说"operating threshold"。

---

**模块 1 到这里为止**,涵盖了 `__init__` / `verify` / `score` / `score_pairs` / `_score_flat_pairs` / `_premise_windows` / `_resolve_entailment_index` 全部 7 个方法,加上论文对应位置、上下游数据流、面试可能被追问的角度、和已知薄弱环节。这是整个方法的心脏。

请你确认:
1. `verify()` 的两遍扫描逻辑(先建骨架 + 批量 NLI + 回填)有没有走顺?
2. `score()` 里 SAR × EPR 的分解意义(为什么算两遍等价的东西)有没有理解到位?
3. 滑窗 + max 聚合这个组合和论文数字(F1 0.837)的对应关系记住了吗?
4. `_resolve_entailment_index` 那个 phase 2 bug 的故事,你能不能自己讲一遍?

确认后我进模块 2:`rtav.py`(RTAV 模块 + 6 类关系模板 + fallback + 那个"方向反转"问题)。

## §2 模块 2:`tripplechecker/rtav.py`(RTAV 模块)

### 一、这个模块在整个系统中的位置

RTAV 的字面意思是"关系类型感知的语言化"(Relation-Type-Aware Verbalization),它做的事情非常单一:把一个结构化三元组 $(s, p, o)$ 变成一句自然语言假设 $h_i$,交给下游的 NLI 模型去判断证据 span 是否蕴含它。

在 `verifier.py` 的 `verify()` 里,当第一层 span 检查通过后,才会调用 `RTAVModule.verbalize(subject, predicate, obj)` 生成假设,这个假设跟 span 组成 (premise, hypothesis) 对送进 NLI。所以 RTAV 是**第二层 NLI 判定的输入准备阶段**,论文对应 §3.3(`sec:rtav`)。

论文里给了两个正式公式:
- 派发函数 $h_i = \phi_{\kappa(p_i)}(s, p, o)$,意思是根据谓词 $p_i$ 决定它属于哪一类关系 $\kappa$,再用那类的模板 $\phi$ 拼句子。
- 模板选择准则 $\psi^*(p) = \arg\max_{\phi} [\mathbb{E}_{D^+}\text{NLI} - \mathbb{E}_{D^-}\text{NLI}]$,意思是从候选模板池里挑一个"在正样本上蕴含分高、在负样本上蕴含分低"的模板。

**关键判断**:这两个公式在**发布仓库里都只以最终产物形式存在**——$\phi_\kappa$ 通过硬编码的 7 组关系模板(见下)体现,$\psi^*$ 的输出通过 `data/rtav_bank/best_templates.json`(135 条 predicate→template 映射)体现,但**构造这个 bank 的训练流程不在这个仓库里**,它在研究工作区(R)的 `learnable_rtav_*.py`。这是一个论文↔代码的错配点(§5 会再讲)。

---

### 二、`RELATION_GROUPS`:6 类(还是 7 类?)硬编码模板

`rtav.py` 顶部定义了一个 `RELATION_GROUPS` 列表,里面是 (关键词列表, 模板字符串) 元组。**代码里实际是 7 组**:

1. **身份/职务类**(创始人、CEO、总裁、董事长、主席、校长、院长、负责人、领导人、主任、队长、舰长、创办人、联合创始人)→ 模板 "s 是 o 的 p"
2. **属性类**(出生日期、国籍、民族、性别、身高、体重、面积、人口、海拔、长度、作者、编著)→ "s 的 p 是 o"
3. **事件动作类**(主演、导演、编剧、监制、出演、参演、执导、创作、演唱、作词、作曲、配音、主持)→ "s p 了 o"
4. **位置类**(首都、省会、位于、地处、坐落、总部、所在地)→ "s 的 p 是 o"
5. **隶属类**(所属、隶属、归属、母公司、子公司、所在、属于)→ "s 属于 o(p 关系)"
6. **时间起点类**(成立于、创建于、发布于、上映于、出生于、创立时间、成立时间、发行时间、上映时间)→ "s p o"
7. **改编/来源类**(改编自、根据、翻拍自、来源于)→ "s p o"

而论文正文原话说"六类粗粒度关系"——这是一处**明确的口径不一致**。合理解释是位置类和属性类模板完全相同("s 的 p 是 o"),论文写作时把它们合并叙述为 6 类;但代码里保留了两组,是因为**关键词分派逻辑靠子串匹配**,如果把"首都"归到属性类,那么类别标签的语义解释会乱(位置和属性混同)。面试时如果被问,答:"论文口径是把两类语义并列(同模板不同域),代码保留分派,便于后续单独替换模板。"

**回退模板**:如果一个谓词不匹配任何关键词,`legacy_v1_template` 返回默认 "s 的 p 是 o"。这是最保守的兜底,基本能读通,但对动作型谓词会拗口(比如 "主演 的 是" 就很别扭)。这也是为什么 offline bank 那么重要——它把 legacy fallback 覆盖不到的谓词逐条学好。

---

### 三、为什么用"子串关键词匹配"而不是精确匹配

`legacy_v1_template` 遍历 `RELATION_GROUPS`,只要谓词字符串**包含**关键词之一,就返回该组模板。这是有意为之:

- **应对复合谓词**:比如"联合创始人"包含"创始人","名誉校长"包含"校长",都能命中身份类。如果精确匹配,得为每一个变体单独枚举。
- **应对同义变体**:"发布时间"和"发行时间"都含"时间",都能落到时间类;"总部所在地"含"所在地",落到位置类。
- **代价**:会误命中。比如某个虚构谓词"创始人协议"会被判为身份类。但 DuIE/CMeIE 的 schema 有限,实际风险很低。

比起精确 dict 查找,子串匹配更**鲁棒但不可解释**——你没办法一眼看出"某个谓词为什么被分到某类"。这也是为什么后来引入 offline bank:bank 里是精确 predicate→template 映射,可解释、可审计、可 diff。

---

### 四、`RTAVModule` 类:bank 覆盖 + 回退双层策略

构造函数接收一个可选的 `bank_path`。如果传了路径且文件存在,就 load 成 dict(`self.bank`);否则 bank 为空。

核心方法 `get_template(predicate)` 的判优逻辑很清楚:
1. **bank 命中**:精确 predicate 存在于 bank → 用 bank 里学出来的模板(经过 `normalize_template` 清洗)
2. **bank 未命中**:退到 `legacy_v1_template`(7 组关键词 + 兜底)

**为什么 bank 优先**:因为 bank 是从数据里挑出来的、经过 NLI 打分验证过的最优模板,粒度到 predicate 级;而关键词组模板是**类内共用**的,粒度粗。同类关系的最佳表达可能不一样(比如"主演"和"配音"都在事件类,但"某某主演了某剧"读起来自然,"某某配音了某角色"就有点怪,应该是"某某为某角色配音")——bank 能学出这种细粒度差异。

**dictionary coverage(论文报告)**:DuIE 谓词 59.1% 落进 bank,CMeIE 0.4%,FinRE 0.0%。这解释了为什么 fallback 分派机制**必须**保留:跨领域时 bank 几乎全空,legacy 是唯一能用的东西。

---

### 五、`verbalize(subject, predicate, obj)`:实际拼句

流程:
1. 拿到模板(bank 优先,否则 legacy)
2. 对 predicate 本身做全角括号 → 半角转换(处理 DuIE 那种带 schema 限定的谓词,如"主演(电视剧)")
3. 用 `.replace()` 依次把 `{s}`、`{p}`、`{o}` 替换成实际值

**一个隐藏风险**(面试可能被问):`.replace()` 是全局替换,如果 subject 里恰好含 `{p}` 或 `{o}` 字面串,会连带被替换。实际数据里不会出现,但这属于代码鲁棒性瑕疵。更稳的做法是用 `str.format(s=..., p=..., o=...)` 或先 escape 再替换。

**返回值**:一个自然语言假设句,交给 verifier 的 NLI 模块。至此 RTAV 的使命完成。

---

### 六、`normalize_template`:模板清洗

这个静态函数把从 bank 里读来的模板做标准化,处理几种历史遗留写法:
- `{subject}` → `{s}`,`{object}` → `{o}`(早期版本用长名占位符)
- `{{s}}` → `{s}`,`{{o}}` → `{o}`(某些工具会 double-brace escape)
- 全角括号 `(` `)` → 半角
- 去掉尾部标点 `。 ；;` 以及空白

**为什么要清洗**:bank 是历经多轮生成/合并/人工修补的产物,格式不齐;而下游拼句要求占位符统一,不然 `.replace('{s}', s)` 就漏了。这个函数的存在**本身就是对"bank 是外部数据"的承认**——如果 bank 是自己生成的、格式受控,就不需要清洗。

---

### 七、`build_rtav_bank.py`:仓库里只有验证器

我扫了发布仓库的 `scripts/build_rtav_bank.py`,发现它**只做一件事**:校验现有 bank 文件里每个模板都同时含 `{s}` 和 `{o}`,否则报错。它并不构造 bank。

真正的 bank 构造流程在**研究工作区 R**(未随论文一起开源),核心脚本叫 `learnable_rtav_*.py`,做的是:
1. 用 LLM 为每个谓词生成多个候选模板(比如"某某主演了某剧" / "某剧由某某主演" / "某某在某剧中担任主角"……)
2. 把每个候选带入 (positive doc, hypothesis) 和 (negative doc, hypothesis),用 NLI 打分
3. 挑正样本蕴含分高、负样本蕴含分低的模板留下

论文报告这一路径让 DuIE F1 从 0.769 提升到 0.811。**面试若被问 RTAV 有没有可学习成分**,标准回答:**离线可学**(bank 是学出来的),**推理时不学**(`get_template` 是纯查表 + 规则回退)。设计上刻意让推理阶段保持 training-free,便于任何人拿模型直接跑,不需要显卡训练。

---

### 八、为什么推理时不用 LLM 直接生成假设

这是一个高频面试问题(RAGChecker 那种工作就是让 LLM 直接判定)。TripleChecker 选择规则化 verbalize 的理由:

1. **确定性**:同一三元组永远拼出同一句假设,可复现,可 diff。LLM 生成会漂移。
2. **成本**:每三元组一次 LLM 调用,15,000 行 benchmark 一次评测就是几百万 token,不现实。
3. **可审计**:模板+bank 都是可读的文本文件,评审员可以直接看到"你到底给 NLI 喂了什么"。LLM 是黑盒。
4. **避免二次幻觉**:LLM 生成假设时可能自己就编造(比如把 "创始人" 意译成"创办并领导了公司")。这会让 NLI 判据偏离原三元组语义。RTAV 的模板是"字面 verbalize",严格对应结构。
5. **training-free 承诺**:整个 verifier 号称训练/推理时不训练任何东西。若假设生成靠 LLM,这个声明就破了。

---

### 九、已知薄弱环节(供 §6 后续汇总用)

1. **6 vs 7 类**:代码 7 组,论文写 6 类,得在答辩时口径统一。
2. **子串关键词匹配不可解释**:命中原因需要 grep 才能看,论文没披露分派细节。
3. **`.replace()` 不 escape**:理论上 subject 含占位符字面量会破坏拼句(实际数据不会触发)。
4. **bank 构造流程不在发布仓库**:论文里的 $\psi^*$ 公式对应的代码是 R 侧的,发布仓库只有验证器。这一点必须诚实说。
5. **legacy 兜底模板对动作类谓词拗口**:CMeIE、FinRE 上 bank 覆盖率极低,这时 legacy 大量介入,拼出的假设可读性下降,可能影响 NLI 判定。论文没有单独报告 legacy vs bank 的 NLI 分数差,是可以被追问的点。
6. **模板方向反转问题**:比如"编剧"到底该拼"某某编剧了某剧"还是"某某是某剧的编剧",两种模板对 NLI 的分数不一样。RTAV 消融实验(§4.6)就是为了解决这个,让 bank 学出方向;但对 bank 未覆盖的谓词,方向由关键词分派决定,可能次优。

---

**确认题**(答完再进模块 3):
1. RTAV 模块的两层策略(bank 优先 + legacy 关键词分派)有没有听清楚为什么这样设计?
2. 论文里的 $\psi^*$ 公式,对应到代码里究竟落在哪一步(即 bank 是"预先构造"、`get_template` 只是"查表"),这个错位你能不能自己讲一遍?
3. "推理时不用 LLM 生成假设"的 5 个理由,记住至少 3 个能立刻脱口而出的?
4. 6 类 vs 7 类的口径不一致,面试被问到的时候你打算怎么答?

确认后进模块 3:`scripts/run_verification.py` + `scripts/evaluate.py`(两个 CLI 入口,把 `TripleChecker` 类真正跑起来的地方,以及 evaluation 里那个 `label_from_row` 的四种标签解析逻辑)。

收到。进入模块 3。

---

## §2 模块 3:`scripts/run_verification.py` + `scripts/evaluate.py`(两个 CLI 入口)

这两个脚本是**把 `TripleChecker` 类真正跑起来**的地方。前者是"给一篇文档+一批三元组,输出每条判定和总分",后者是"跑一份带人工/LLM 标注的 JSONL,输出评测指标"。它们共用 `TripleChecker` 核心,但**输入形态、输出形态、标签来源完全不一样**,这是很多人第一次读代码会绕晕的地方。

---

### 一、`run_verification.py`——单文档验证入口

**定位**:面向"我有一段文本 + 从中抽出来的三元组,想知道哪些能被文本支持"的用户。是 demo 场景,也是论文 Fig. 1 那张流程图对应的最小可复现单元。

**输入契约**:一个 JSON 文件,顶层是一个对象,含两个字段:
- `document`:字符串,原始文档全文(作为 NLI 的 premise 池)
- `triples`:三元组数组,每项至少含 `subject / predicate / object / source_span`

**CLI 参数**:
- `--input`(必填):上述 JSON 路径
- `--output`(默认 `results/verification_output.json`):输出路径
- `--nli_model`(默认 `IDEA-CCNL/Erlangshen-Roberta-110M-NLI`):中文 NLI 模型的 HF ID
- `--rtav_bank`(默认 `"none"`):RTAV bank 路径,字面 `"none"` 会被解析成 `None`,走 legacy 分派
- `--threshold`(默认 `0.5`):NLI entailment 概率阈值 $\delta$,论文的固定操作点

**执行流程**:
1. 读入 JSON,取出 `document` 和 `triples`
2. 构造 `TripleChecker` 实例(把 `"none"` 字面串手动 map 成 Python 的 `None`)
3. 调用 `checker.verify(triples, document)` 得到每条三元组的判定字典列表(`label / span_ok / nli_score` 等)
4. 调用 `checker.score(triples, document)` 得到整篇的 $\text{Score} = \text{SAR} \times \text{EPR}$
5. 输出结构是 `{"score": ..., "results": [{...原三元组, ...判定结果}, ...]}`——**把原三元组字段和判定结果 merge 到同一层**,这样 CSV 化以后每行自足,方便下游做混淆矩阵、切片分析
6. 结果同时写 JSON 文件并 print 到 stdout

**几个有意思的细节**:

- **`"none"` 字符串到 `None` 的手动转换**:CLI 参数天然是字符串,argparse 不会把 `"none"` 变成 `None`,所以脚本里显式 `if args.rtav_bank.lower() == "none" else args.rtav_bank`。这是**一个便利性设计**:让命令行调用者不用写复杂的 `--rtav_bank ""` 或省略参数,直接写 `--rtav_bank none` 就能关掉 bank。
- **score 被算了两次**:注意 `verify()` 内部会做 span 检查 + NLI,而 `score()` 又会再走一遍。这是**冗余但清晰**:demo 场景数据量小,不追求性能;真要跑大规模评测应该改成一次前向、复用中间量。这也是为什么 `evaluate.py` 里选择直接调 `verify` 而不再调 `score`。
- **默认 NLI 模型**:Erlangshen-Roberta-110M-NLI 是二郎神系列的中文 NLI 分类器。选它的理由:体量小(110M,单卡秒级推理)、中文原生训练、HF 可直接下载、许可证友好。论文 §4.1 报告它作为主 backbone,同时用 mDeBERTa-330M 做鲁棒性对照(rebuttal e2)。
- **输出的 `source_span` 字段处理**:如果三元组是完整格式(含 `source_span`),Layer 1 会检查它是否是 `document` 的子串;如果没有(或为空),`verify()` 会打 `fake_span` 标记然后跳过 NLI。所以这个脚本**不做任何数据清洗**,数据契约全靠输入方保证。

---

### 二、`evaluate.py`——批量评测入口

**定位**:面向"我有一份带人工/LLM 标注的 JSONL,想算 P/R/F1"的用户。论文 §4.2 15,000 行 controlled benchmark、§4.4 人类校准、§4.5 human-set diagnostics,所有指标数字都是从这个脚本(或它的变体)出来的。

**输入契约**:一个 JSONL 文件,每行一个对象,至少要有:
- 三元组字段(`subject / predicate / object / source_span`),给 `verify()` 用
- **标签字段**(四选一,优先级见下),用来算 P/R/F1

**标签解析——`label_from_row` 函数**:这是这个脚本最需要吃透的地方。它按以下优先级找标签:

1. `human_avg`(1-3 分连续值,通常来自 3 位标注员打分平均)→ 如果 ≥ `positive_threshold`(默认 2.0)则视为 pass
2. `llm_score`(LLM 打的连续分)→ 同样跟 `positive_threshold` 比
3. `verdict`(离散字符串 "PASS" / "FAIL"),大小写不敏感 → "PASS" 视为 pass
4. `label`(整数 0/1)→ 直接返回

**这个优先级为什么这么排**:人类标注 > LLM 标注 > 二值判决 > 原始整数标签。反映了论文的评测哲学——**多源可用时以人类为准**。同一份数据可能被多个源打标,评估时可以通过删/加字段来切换 gold source(论文 §4.5 的"human-set scorer diagnostics"就是这么做的:同一批数据分别用 `human_avg` 和 `llm_score` 做 label,对比模型 P/R/F1 在不同 gold 下的表现)。

**`positive_threshold=2.0` 的语义**:1-3 分制里,2 分是"中间偏可信"。定这个阈值等于说"标注员平均分 ≥ 2 才算 pass"。这是**论文操作口径**,值得单独记住,面试可能被问"为什么用 2.0 不用 2.5"——答:1-3 分制里 2.0 是"接受"和"拒绝"的自然分界(1=明显不支持,2=部分支持,3=完全支持),再高会把"部分支持"也判负、太严;再低会把"明显不支持"也判正、太宽。

**执行流程**:
1. 读 JSONL 到 rows 列表
2. 每行走 `label_from_row` 得到 gold labels(0/1)
3. 构造 `TripleChecker`,直接调 `checker.verify(rows, document=None)`—— **注意 `document=None`**,这是评测场景专用:每行自带 `source_span`,不需要全文
4. 把 verify 返回的 `label` 字符串(`"pass"` 或非 pass)转成 0/1 得到 preds
5. 调 `evaluation_output` 输出结构化报告

**`document=None` 这个路径的含义**:评测数据集里通常**不发布原始文档**(版权/隐私原因,DuIE 的原文属于百度、CMeIE 属于医疗数据),只发布"三元组 + `source_span`"。所以 `verifier.py` 里 Layer 1 span 检查有一个分支:document 是 None 就跳过"span 是否在 document 里"的检查,只要 span 非空就当作通过。这是**评测特化路径**,不是 demo 场景该走的。面试若被问"为什么评测能没有文档",这个数据许可证解释是关键。

---

### 三、`evaluation_output`——结构化指标报告

这个函数是 evaluate.py 的输出组装器,把原始 labels/preds 变成一份 self-contained 的 JSON 报告。它做了两件事:

**1. 双视角指标(pass-positive vs unsupported-positive)**

对同一份 labels/preds,分别以"pass"为正类和"unsupported"为正类各算一遍 P/R/F1。方法是把 labels 和 preds 都做 `1 - x` 翻转,再走 `metric_bundle`。

**为什么这样做**:这是 TripleChecker 一个非常关键的方法论决定。在幻觉检测场景里:
- 如果关心"通过审核的三元组质量高不高"→ 用 **pass-positive**(recall = 真正好三元组里被我们放行的比例)
- 如果关心"能否揪出所有幻觉"→ 用 **unsupported-positive**(recall = 真正的幻觉里被我们抓到的比例)

论文里 §4.2 主表报告的 F1=0.8015 是 unsupported-positive(SU-F1,Source-Unsupported F1),因为"抓幻觉"才是这篇工作的核心问题;但 §4.3 same-row policy 表报告的是 pass-positive(P/R/F1=0.694/0.970/0.809,DuIE 主数据),因为那节讨论的是"放行策略"。**同一份数据、同一组 preds,报出来的数字完全不同**——这是很多人读表时最容易混淆的点。面试被问"你的 F1 到底是 0.80 还是 0.81"时,得先反问"哪个视角"。

**2. 混淆矩阵**

用**语义化的键名**输出四格:`reference_pass_pred_pass / reference_pass_pred_unsupported / ...`,而不是 tp/fp/fn/tn 这种传统缩写。原因:审稿人/合作者不需要记住哪个是 TP,一眼看键名就懂。这是 release 阶段刻意做的可读性优化。

**返回结构总览**:
- `data`:输入路径,便于回溯
- `n`:样本数
- `positive_label`:文字描述阈值口径(比如 "score >= 2.0")
- `threshold`:NLI 判定阈值(和 `positive_threshold` 是两回事,别混)
- `metrics`:与 `pass_positive_metrics` 相同,作为默认视角
- `pass_positive_metrics` / `unsupported_positive_metrics`:双视角
- `confusion_matrix`:四格语义化

---

### 四、`utils.py` 的两个关键辅助

- **`normalize_triple`**:强制把三元组字段清洗成 str + strip。用于 CLI 场景防御式编程,避免 JSON 里 subject 带前后空格或 null 值导致下游炸。发布仓库里这个函数**被 export 出来但 evaluate/`run_verification` 都没直接调**(它们信任输入)。这是留给外部用户自己包装用的接口。
- **`metric_bundle`**:朴素的 tp/fp/fn/tn → P/R/F1/acc 计算器,零依赖(不用 sklearn)。为什么不用 sklearn:sklearn 在 Windows 上装依赖麻烦,论文附录承诺"复现只需 python + transformers + torch",少一个依赖少一份复现门槛。分母保护(`if (tp+fp) else 0.0`)确保空集不炸。

---

### 五、这一层的设计张力

- **run vs evaluate 共享核心但入口分离**:核心是 `TripleChecker.verify`,两个入口各自组织数据流。这个分离让"给用户看"(run)和"给评审看"(evaluate)两种场景解耦。
- **CLI 而非 Python API**:两个入口都是 argparse CLI,理由是评审员/复现者更习惯 shell 一行跑通,不想学 Python 包。这是发布仓库的通行做法。
- **输出既写文件又 print**:让人可以 `python evaluate.py ... | jq` 看关键数,也能之后回查文件。多一份磁盘 I/O,换来交互方便。
- **`evaluation_output` 里 `metrics` 和 `pass_positive_metrics` 冗余存了一份**:向后兼容——早期版本的 `metrics` 只有一个视角,后来引入双视角后为了不 break 老 downstream 脚本,保留 `metrics` 别名。这是 release 演化痕迹。

---

### 六、已知薄弱环节(汇总到 §6 用)

1. **`run_verification.py` 里 verify 和 score 各走一遍 NLI**,浪费一次前向。demo 场景可忽略,但用户如果拿去跑大数据会踩坑。
2. **`evaluate.py` 假设 `verify` 返回的 label 字符串是 `"pass"`**(通过 `row["label"] == "pass"` 判断),但 verifier 也会返回 `"hallucination"` 和 `"fake_span"`——这里**只做二值化**,把 `fake_span` 和 `hallucination` 都算作"非 pass"(即视为 unsupported)。这个二值化决定隐含了一个立场:"span 造假"和"NLI 不蕴含"是同一类错误。论文对齐了这个立场(SU=Source-Unsupported 涵盖两种),但代码里没有单独 audit 这两种子类的相对占比,是一个可加的分析。
3. **`label_from_row` 的四种源没有交叉一致性检查**:如果 JSONL 同时含 `human_avg` 和 `verdict`,只会用 `human_avg`,忽略 verdict——不会报告两者是否冲突。审计时不容易发现标注不一致。
4. **`positive_threshold=2.0` 是硬编码默认**:如果标注量表变了(比如换成 0-1),用户可能忘了改这个参数导致全部判负。缺少参数合法性校验。
5. **没有 seed 控制**:NLI 前向本身在 fp32 下确定,但如果未来换成 mixed precision 或引入随机 dropout,结果会漂。目前脚本没显式 `torch.manual_seed`,复现依赖 HF 默认行为。

---

**确认题**:
1. `run_verification` 和 `evaluate` 两个入口**分别面向什么场景**,以及为什么 `evaluate` 里 `document=None` 是合法的,能自己讲一遍吗?
2. `label_from_row` 的四种标签优先级(`human_avg` > `llm_score` > verdict > label)背后的哲学(人类 > LLM > 判决 > 原标签)记住了?
3. **pass-positive 和 unsupported-positive 双视角**——同一份数据、同一组预测,为什么会报出两个不同的 F1?论文主表 0.80 是哪个视角?
4. `positive_threshold=2.0` 的语义(1-3 分制的自然分界)如果被追问,你能不能一句话答上来?

确认后进模块 4:`scripts/build_source_span_benchmark.py`(15,000 行受控 benchmark 的构造逻辑——4 种负样本条件 `fake_span` / `object_replacement` / `subject_replacement` / `predicate_mismatch` 是怎么合成的,这是论文最核心的贡献之一,细节非常多)。

## §2 模块 4:`scripts/build_source_span_benchmark.py`(15,000 行受控 benchmark 构造器)

这是**论文最核心贡献之一的物理载体**——§4.2 主表的 SU-F1=0.8015 就是在这份 benchmark 上算出来的。整个脚本干一件事:从 DuIE / CMeIE / FinRE 三个中文关系抽取数据集里,先摘出"绝对干净的正样本",再对每个正样本机械地合成 4 种负样本,拼成一份 5×规模的受控评测集,附上完整可复现的元数据。

它是**论文 §3.1 契约形式化**的实证工具:如果你相信 span-forward contract "`source_span` 必须是 document 子串且蕴含三元组",那么这个脚本合成的 4 种负样本就是 4 种契约破坏模式,分别对应"span 造假 / 客体错 / 主体错 / 谓词错"。任何声称能做源忠实度验证的方法都应该能在这 4 类上分别报出可解释的性能。

---

### 一、总体设计逻辑

脚本分三层职责,面试可以按这个顺序讲清:

1. **数据摄入层**(`iter_duie` / `iter_cmeie` / `iter_finre`):把三份异构数据集统一成"`gold_positive` 记录"——文档 + 三元组 + 严格 `source_span`
2. **负样本合成层**(`make_fake_span` / `object_replacement` / `subject_replacement` / `predicate_mismatch`):对每个 `gold_positive`,机械地造出 4 种破坏样本
3. **组装与元数据层**(`select_gold` / `build_benchmark_records` / `write_readme`):按数据集配额抽样、拼装、排序,写 README 附 SHA256 保证可复现

---

### 二、"严格 `source_span`"的定义(整个 benchmark 的地基)

`extract_source_span` 和 `span_is_strict_positive` 定义了 `gold_positive` 的准入门槛,这是整个数据集的**契约地基**,必须吃透:

**`extract_source_span` 的算法**:
1. 在 document 里找 subject 和 object 的**所有**出现位置(`_find_all`)
2. 对每一对 (`subject_pos`, `object_pos`),用 `_clause_span_for_pair` 从这两个 anchor 向两侧扩,直到撞上分句符(`。！?;\n\r` 等)才停
3. 得到的候选 span 必须:非空、长度 ≤ `window`(默认 120 字)、同时含 subject 和 object 的字面
4. 从所有合格候选里挑**最短**的,平局按 document 中出现位置靠前的

**为什么这样设计**:
- **子句边界扩展而非固定窗口**:如果只用 subject/object 附近 ±k 字符切,会切出半句话("···公司创始人。张三")这种语义残缺的 span,NLI 判读不了。子句边界扩展保证 span 是可读的完整语义单元。
- **最短优先**:span 越短,给 NLI 的干扰越少,证据越集中。如果 subject/object 在同一文档里出现多次,不同 (`s_pos`, `o_pos`) 组合会切出不同长度的候选,挑最短的等价于"证据最集中的那次出现"。
- **120 字上限**:Erlangshen NLI 模型 `max_length`=256 tokens,预留 subject+predicate+object 拼出的假设句(通常 20-40 字)后,前提部分留 120 字比较安全,同时避免过长 span 稀释 NLI 信号。

**`span_is_strict_positive` 的四个条件**:span 非空 + span 是 document 子串 + subject 在 span 里 + object 在 span 里。**只有全部满足才算 `gold_positive`**——这是"契约地基"的操作定义。任何走过 gold 门槛的样本都是"字面证据完整"的。

**这个门槛把很多样本挡在外面**:面试可能被问"为什么最终只有几千条 gold 而不是数万",答:三份数据集里大量三元组是**跨句抽取**或**指代抽取**(比如"他"指代前一句的主体),这种在单一子句里找不到严格 span,自动过滤了。这不是 bug 而是 feature——它保证 benchmark 是"最难幻觉:证据本该显式存在"的场景,让模型没有借口。

---

### 三、三个数据集的异构摄入

每份数据的 JSON schema 都不同,分别对应:

- **DuIE**(百度通用领域):字段 `sentence` / `relations`,每个 relation 是 `{head: {name}, tail: {name}, type}`
- **CMeIE**(中文医疗):字段 `text` / `spo_list`,每项是 `{subject, predicate, object: {"@value": ...}}`——object 是嵌套 dict,需要 `.get("@value")` 拆出来
- **FinRE**(金融):**Tab 分隔 TXT** 而非 JSON,每行 `subject\tobject\tpredicate\tdocument`,注意**这里 subject/object 顺序在前**,predicate 在中间(与前两个数据集的字段顺序不一样),读的时候不能想当然

**都做同一件事**:构造 `doc_id`(带数据集前缀 + 6 位零填充索引),对每个三元组尝试 `extract_source_span` + `span_is_strict_positive`,只有通过的才 yield 出去。**`doc_id` 是全局唯一的**,这就是为什么后面 `assert_doc_id_documents_unique` 能作为完整性校验。

**FinRE 的额外过滤**:`predicate == "unknown"` 的行跳过。这是 FinRE 数据集的一个 quirk——它把"未标注"用 unknown 显式标出,这些样本不是负例、也不是正例,是缺标注,必须剔除。

---

### 四、四种负样本的合成逻辑(重点中的重点)

论文里说"四种受控破坏条件",每一种在代码里对应一个 `make_*_record` 函数。**面试如果被问细节,一定要能挨个讲清楚"造什么、怎么造、为什么这么造"**。

#### 4.1 `make_fake_span_record`——伪造 span

**造什么**:document 里根本不存在的 `source_span` 字符串,格式是 `"{subject}与{object}的伪造来源片段"`,并在末尾加 `x` 直到确保它不出现在 document 里。

**为什么这么造**:测 Layer 1 span 检查(SAR)是否真的在起作用。`fake_span` 样本**在 threshold=0 时也应该被判负**——因为 NLI 都没跑,Layer 1 就已经拦下了。如果一个方法在这类样本上 F1 很低,说明它没做 span 检查或做得有 bug。

**为什么用 subject+object 的模板**:让假 span "看起来像"真 span,防止有些方法用简单启发式(如"span 里有 subject 和 object 就通过")作弊。这里假 span 里字面上是有 subject 和 object 的,但整体不是 document 子串,严格 span-forward 契约会拒绝。

**加 `x` 的循环**:防御性代码——极偶尔 subject+object+"与...伪造来源片段"可能真的出现在 document 里(比如医疗文本讨论"伪造来源片段"这类词),加 x 直到确保不重复。这是防污染。

#### 4.2 `make_object_replacement_record`——同谓词客体替换

**造什么**:保留 subject/predicate/`source_span` 不变,把 object 换成"同谓词池"里的另一个 object。

**"同谓词池"是什么**:`build_predicate_pools` 会把所有 gold 记录按谓词聚合,统计出"这个谓词曾配过哪些 subject/哪些 object"。比如 predicate="导演",池子里就是所有真被标注为某片导演的人名。

**为什么用同谓词池**:这是**精心设计的难负例**。如果随便挑一个 object(比如从 predicate="创始人"的 object 池里抽一个人名替换 predicate="导演"的 object),NLI 一眼就能看出"这个人从没在文档里出现",太简单了。同谓词池里的 object 是"类型对但事实错"——都是导演,但不是这部片的导演。这测的是模型能否分辨"类型正确的干扰项"。

**`avoid_text=source_span`**:替换 object 必须**不在 `source_span` 里**——否则替换后 `source_span` 里既有原 object 又有假 object,NLI 反而可能误判为通过(碰巧字面命中)。这个约束保证负样本"干净地是负样本"。

**`by_dataset` 的分池**:跨数据集不共享 object 池(DuIE 的人名不进 CMeIE 的池)。因为跨领域的 object 太容易被 NLI 识别为异常(医疗文本里突然冒出"周杰伦"),又变成简单负例。

#### 4.3 `make_subject_replacement_record`——同谓词主体替换

结构完全对称,把 subject 换成同谓词池里的另一个 subject,其他约束(avoid `source_span`、`by_dataset`)都相同。

**为什么 subject 和 object 都要各做一次**:两个方向的错误性质不同——object 错通常是"事实弄错了对象"(把 A 片的导演贴给 B 片),subject 错通常是"事实弄错了主语"(把 B 片的导演当成 A 片的导演)。语义方向不同,模型可能在一个方向敏感、另一个方向不敏感,分开测才能诊断。

#### 4.4 `make_predicate_mismatch_record`——谓词误配

**造什么**:保留 subject/object 不变,把 predicate 换成"该 (subject, object) 从未被标注过"的一个其他谓词。

**关键防御:`known_true` 排除**:`build_true_predicate_map` 会记录整个语料里 (dataset, subject, object) → 所有真谓词集合。替换时**只从"从未标注过"的谓词里挑**,避免造出"看似错但其实也对"的样本——比如 (张三, 张三导演的电影) 同时是"导演""编剧"关系,把 predicate 从"导演"换成"编剧"后其实还是真的,如果不排除就成了错误标注。

**这是整个脚本最需要口头讲清的一个防御性细节**。面试可能被问:"你怎么知道你的负样本真的是负的?"标准答:"每一类负样本都在合成时避开了'碰巧还是对的'情况——object/subject 替换避开 `source_span`(不然字面命中),predicate 替换避开 `known_true` set(不然真的是对的)。"

**`_first_replacement` 而非随机**:遍历候选列表(排序后)按第一个能用的就返回。**确定性优先**——同一 seed 下每次跑结果完全一样,便于跨机复现和 diff。如果用 `rng.choice()` 就得到随机负例,复现难度大。

---

### 五、gold 记录的资格进一步筛选

`_all_negative_records_with_true_predicates` 是一个**关键把关**:一个 gold 记录必须能构造出全部 4 种负样本,才被留下。如果任意一种合不出来(比如同谓词池里没有别的 object 可选),整条 gold 就丢弃。

**为什么这么严**:让 benchmark 严格 5 平衡——每个 gold 对应恰好 4 个负样本,总体 1:4 比例固定。这样按数据集算 P/R/F1 时,base rate 是确定的(20% pass, 80% unsupported)。如果不平衡,报告 F1 时得单独说明每类占比,增加读表复杂度。**论文里 15,000 行 = ~3,000 gold × 5** 就是这个平衡带来的干净数字。

**代价**:进一步压缩了通过率。只有一个真实谓词的 subject/object 对,或者谓词池太小的 predicate,都会被过滤。

**`select_gold_records_by_dataset` 的抽样**:每个数据集最多保留 `max_gold_per_dataset`(默认 200 行,但论文实际用了更大的数)条 gold,用固定 seed 打乱后取前 N 条。**`by_dataset` 配额**保证三个领域样本量对齐,防止 DuIE(样本大)完全压过 CMeIE/FinRE。

---

### 六、组装与写出

**`build_benchmark_records`** 的最终产出流程:
1. 对每个 selected gold,先 append `gold_positive` 本身
2. 再 append 4 个负样本(fake / object / subject / predicate)
3. 全部按 `(dataset, doc_id, triple_id, condition)` 排序输出

**排序意义**:让 JSONL 文件对 git-diff 友好,任何数据抽样变化都能一目了然看出增删。这是 release 阶段可复现的重要工程细节。

**`assert_doc_id_documents_unique`** 是最后的完整性校验:同一个 `doc_id` 在 5 行(1 gold + 4 negative)里必须共用同一个 document 字符串。这个 assertion 一旦挂,说明数据流某处出了 bug——比如某个负样本合成时不小心改动了 document 字段。

---

### 七、README + SHA256 + 元数据(可复现证据链)

`write_benchmark_readme` 生成一份 markdown,包含:
- **生成命令原文**(`python + sys.argv` 完整拼接)——最好的复现说明
- **每个输入数据集的 SHA256**——绑定输入版本,别人复现时可以先校验 hash 对不对
- **seed + `span_window` + `max_gold_per_dataset`** 等参数
- **`negative_failures`**——按数据集统计"哪一类负样本合成失败最多",能直接暴露池子稀疏的谓词
- **各种计数表**:dataset counts、condition counts、dataset×condition 交叉

**这一整套元数据是学术界评测集发布的黄金标准**,论文附录里"可复现声明"能直接引用这份 README。面试若被问到"你怎么保证 benchmark 是可复现的",答:"输入 hash + seed + 完整参数 + 生成命令都写进 README,任何人拿到源数据都能字节级复现同一份 JSONL。"

---

### 八、这个脚本和论文的映射

- **论文 §3.1(契约形式化)** ← 由 `span_is_strict_positive` 的四条件操作化
- **论文 §4.2(controlled source-span benchmark)** 主表 F1=0.8015 ← 这份 JSONL 是评测输入
- **论文 §4.6(RTAV ablation)** 分谓词切片 ← 每条记录带 `predicate` 字段,可按谓词做切片
- **论文附录的"数据合成流程"** ← 就是这一份代码的自然语言描述
- **`negative_source` 字段**(fabricated / `same_predicate_object_pool` / `same_predicate_subject_pool` / `other_predicate_pool`)是**可审计的负样本溯源**,评审员可以按这个字段做细粒度分析

---

### 九、已知薄弱环节(汇总到 §6 用)

1. **同谓词池负例可能仍然偏简单**:如果同谓词池的 object 之间语义差异很大(比如"导演"的候选人名彼此完全不像),NLI 一眼看出"这个人根本没出现",难度不够。真正难的是"同类型且同上下文倾向"的干扰。论文没有单独分析 pool 内部难度分布。
2. **谓词误配依赖 `known_true` 完备性**:如果某个 (subject, object) 对在数据集里有真实的多重关系但只被标注了一个,`known_true` 会漏,合成的"错谓词"可能是真的。这是数据集不完备的传递性问题,论文靠 §4.4 人类校准来兜底,但没显式量化"由此产生的假负样本"占比。
3. **`span_window`=120 是硬编码经验值**:没做 sensitivity sweep 报告 window ∈ {60, 90, 120, 150, 200} 对最终 F1 的影响。审稿人可能问,可以准备一句"120 是 `max_length`=256 tokens 预留 hypothesis 后的自然上限"。
4. **`_first_replacement` 的确定性偏置**:排序后总是取第一个,可能倾向于取字典序靠前的候选(数字开头 < 字母 < 汉字)。理论上会让某些 subject/object 被过度使用,统计意义上偏离随机采样。实际影响小,但严格 randomization 需要论文里说明。
5. **`fake_span` 模板过于人工**:`"...的伪造来源片段"` 这个字符串带有明显的"伪造"字样,如果 NLI 模型有一定语义能力,可能因为字面就带贬义词汇而误判为负。理想的假 span 应该是从别的文档抽出来的真实句子,和 subject/object 无关但形态自然。
6. **只考虑 substring 严格匹配,不做实体归一化**:如果文档写"周杰伦",三元组 subject 写"周董",严格 span 检查会 fail 掉这个 gold。这在实际抽取场景里是常见问题,论文承认了但没有 relaxation 版本对照。

---

**确认题**(答完再进模块 5):
1. **严格 `gold_positive` 的四个条件**(span 非空 + 是 document 子串 + 含 subject + 含 object)—— 缺一不可,这是整个 benchmark 的地基,能自己讲清楚吗?
2. **四种负样本的核心防御设计**(object/subject 替换避开 `source_span`、predicate 替换避开 `known_true`)—— 为什么这些防御是必需的,面试被问"你怎么保证你的负样本真的是负的"能立刻答上?
3. **"每个 gold 必须能造出全部 4 种负样本才被保留"** 这个筛选带来的 5:1 平衡,以及它对读表(P/R/F1 base rate)的意义?
4. **README + SHA256 + seed + 生成命令**——发布评测集时的可复现证据链,能用一句话概括这套元数据的哲学?

确认后进模块 5:`scripts/accept_sprint_analysis.py`(论文 §4.3 same-row policy 的核心分析脚本,主表 PASS-positive F1=0.809 的来源,以及"paired scorers / operating policies"这些概念在代码里的物理落地)。

## §2 模块 5:`scripts/accept_sprint_analysis.py`(Accept-sprint 分析脚本,论文 §4.3–§4.5 的引擎)

这是**论文最重量级的分析脚本**——1000 多行,负责生成主表以外几乎所有次要表格和统计检验。名字里"Accept sprint"是内部代号,指论文投稿冲刺阶段为了回应"你们的方法只有一个 F1 数字,能不能更全面地论证有效性"这个 review 焦虑而做的一整套辅助实验。**它不调用任何神经网络、不加载任何模型**——所有原始分数(NLI entailment、ROUGE、BERTScore、LLM score、MiniCheck 等)都是别的脚本预先算好写进 CSV 的,这个脚本纯做后期统计分析。这个设计对**离线可复现性**至关重要:审稿人和其他研究者拿到这些 CSV 就能字节级复现所有指标,不需要下载模型、不需要 GPU。

---

### 一、脚本的整体职责与输入

**输入**(全部是预先算好的本地文件):
- `annotation_data.json`——评测集的基础记录(文档、三元组、predicate 等元数据)
- `annotations_A.json` / `annotations_B.json`——两位人类标注员的 1-3 分打分
- `baseline_comparison.csv`——各基线打分器的分数(ROUGE-L、BERTScore、LLM reference scorer、TripleChecker score、`entail_score`)
- `minicheck_results.csv`(可选)——三个 NLI 变体基线(Fixed-template NLI、Generic-relation NLI、MiniCheck RoBERTa-Large)

**输出**:12 份 CSV + 1 份汇总 JSON,分别对应论文里不同的表和消融。

**面试角度的关键叙事**:"这个脚本是论文'我们不是只有一个数字'的物理证据。你能问我关于 F1、AUROC、AP、bootstrap CI、McNemar 检验、operating policy、label robustness、predicate slice 的任何问题,答案都在这份脚本生成的 12 个 CSV 里。"

---

### 二、人类参考标签的组装(`load_human_reference`)

**流程**:
1. 读取 `annotation_data.json`(基础记录)
2. 读取两份标注员打分 A、B(都是 `{id: {..., human_score: 1-3}}` 格式)
3. 按 id 对齐,算 `human_avg = (score_a + score_b) / 2`
4. 用 `human_avg ≥ 2.0` 做二值化,得到 `label_pass ∈ {0, 1}`

**为什么两位标注员**:成本可控 + IAA(标注一致性)可算。三位以上标注员成本翻倍;单位标注员则无法量化"标注本身的不确定性"。**这是学术界最小可辩护的多标注配置**。

**为什么阈值 2.0**:1-3 分制的自然分界(1=不支持, 2=部分支持, 3=完全支持),已在模块 3 讨论。

**为什么保留 `score_a`、`score_b` 不只保留 `human_avg`**:因为后续 label robustness 分析(§7)要构造多种替代标签口径,比如"两位都 ≥ 2"或"至少一位 ≥ 2"或"两位打分二值化后一致",这些都需要原始分数。**保留原始信号 → 允许多种后期分析**,这是学术分析代码的通用哲学。

---

### 三、核心度量与阈值选择器

这一层是所有分析的原子操作:

**`metric_bundle`**:tp/fp/fn/tn → P/R/F1/accuracy(和 utils.py 那份一样,这里再重写一遍是为了让脚本自包含——不 import 外部模块方便审稿人一屏看清)。

**`invert_metrics`**:巧妙——从一个 pass-positive 的 metric bundle 重建 labels/preds(用 tp/fp/fn/tn 反推),然后翻转 0/1 再算一遍。这样**同一份 preds 能同时报 pass-positive 和 unsupported-positive 两个视角**,不用重新走一遍数据。

**`balanced_accuracy`**:`pass_recall` 和 `hall_recall` 的平均。用于**样本不平衡场景下更公平的准确率报告**。人类标注集里 pass 占 ~40%、hall 占 ~60%,base rate 有偏,直接 accuracy 会被大类主导,balanced acc 更能反映"两类各自被识别得多好"。

**`auroc`** 和 **`average_precision`**:纯手写实现,不依赖 sklearn。同点位处理:tied score 时给 0.5 分(auroc)或按顺序累加(ap)。**这两个是 threshold-independent 的排序质量指标**——面试常问"你的打分器排序能力好不好?F1 只反映一个阈值",这两个数就是答案。**注意**:TripleChecker 的 verdict 是 0/1 二值(过阈值就 1),没有连续分数,所以 `summarize_scorer_ranking_diagnostics` 里显式 skip 掉 TripleChecker verdict,只对连续分数的基线报 AUROC/AP。TripleChecker 的连续分数以"TripleChecker score"或"`entail_score`"形式出现,可以算 AUROC。

**`threshold_metrics`**:给分数和阈值算 P/R/F1。工具函数,被到处调用。

**`select_threshold`**:在候选阈值列表里挑最优的,按三种目标之一:
- `pass_f1`:pass 视角 F1 最大
- `hall_f1`:hall 视角 F1 最大
- `pass_precision_at_recall_095`:在 pass recall ≥ 0.95 前提下 pass precision 最大

**三种目标对应三种应用场景**:
- pass F1 最优 → 平衡"放行准"和"不冤枉"
- hall F1 最优 → 严格拦截幻觉(可能误杀真三元组)
- P@R=0.95 → 高保留率优先(至少留住 95% 真三元组,在此约束下拒得越准越好)——这是**KG-RAG 下游场景的合理策略**,因为下游宁可放走一些幻觉也不能砍掉太多真事实。

**`select_high_retention_threshold`**:另一种"高保留率"选择,在 pass recall ≥ min 的约束下最大化 hall recall(找出最多幻觉)。这更接近**审计场景**:先保证不误杀,然后尽量多找幻觉。

**`stratified_folds` + `cv_threshold_predictions`**:5 折分层交叉验证。分层保证每折 pass/hall 比例接近整体。**为什么要 CV**:防止"在整个测试集上选阈值 → 报告同一测试集上的 metric"的信息泄漏。每折用 train 部分选阈值,test 部分算 metric,聚合起来才是无偏 estimate。这在 review 里是**几乎必被追问**的方法学点。

---

### 四、直接对比器打分(`summarize_direct_scorers`)

这是**论文 §4.5 主要基线对比表**的生成器。

**打分器名单**(通过 `build_extended_scorer_score_map`):
1. **All-pass**——恒返回 1.0,当作"什么都放行"的下限基线。任何 F1 数字都必须超过这个,否则你的方法还不如"什么都通过"。
2. **ROUGE-L**——传统的 n-gram 重叠,不理解语义,只看字面。这是"最朴素的引用检查"。
3. **BERTScore**——用预训练 BERT 做语义相似度,比 ROUGE 强但仍是相似度而非蕴含。
4. **LLM reference scorer**——用 LLM(如 GPT-4)直接打分。**代表"用大模型判"的路径**,是最强的基线之一,也是 TripleChecker 想要打败/持平的对象(因为 LLM 打分昂贵、不确定、不 training-free)。
5. **TripleChecker score**——SAR × EPR(连续分数,论文的完整分数)
6. **TripleChecker verdict**——只用第二层 NLI entailment 概率(`entail_score`,不做 SAR 乘法)——用来隔离 Layer 2 的贡献
7. **Fixed-template NLI**(可选)——固定用一个模板 verbalize 所有谓词,不用 RTAV。这是 RTAV 消融的对比对象。
8. **Generic-relation NLI**(可选)——完全不 verbalize,直接把三元组塞进 NLI。看 RTAV 的必要性。
9. **MiniCheck RoBERTa-Large**(可选)——外部 SOTA 事实核对模型作为强基线。

**每个打分器报两组数字**:
- `fixed@0.50`——固定阈值 0.5,这是论文的主操作口径,对齐比较
- `5-fold CV pass-F1 threshold`——CV 学出来的最优阈值,展示"如果允许调阈值,各方法能到多好"

**为什么两组**:审稿人可能说"你固定 0.5 是给自己方法量身定做的",两组一起报可以反驳——固定 0.5 时 TripleChecker 好,CV 学到的阈值下也仍然好,说明不是阈值 cherry-pick。

**`TripleChecker verdict` 用 `entail_score`,`TripleChecker score` 用 `triple_checker` 列——两者不同**:前者是纯 NLI 概率,后者是完整的 SAR × EPR。**面试题眼**:"你们主表报的是哪个?"——不同表报不同的,§4.2 主表用完整 score,§4.5 直接对比用 verdict(NLI-only)让基线公平(基线都是单一分数)。

---

### 五、高保留策略、排序诊断、operating policies

**`summarize_high_retention_scorer_policies`**:对每个打分器,找出"在 pass recall ≥ 0.95 前提下 hall recall 最高"的阈值,报出该阈值下的完整 metric。**All-pass 例外**——直接用 threshold=0.0,把 `pass_recall`=1.0 强制满足,得到基线下限。这一节的价值:证明**在高保留率约束下 TripleChecker 仍能揪出显著多的幻觉**,而基线要么牺牲 `hall_recall` 换 `pass_recall`,要么反过来。

**`summarize_scorer_ranking_diagnostics`**:threshold-independent 的 AUROC + AP。为什么单独一张表?因为**它绕过阈值选择的争议**,直接问"你的分数把 pass 和 hall 分开了没?"。TripleChecker 的连续分数如果 AUROC 显著高于 ROUGE/BERTScore 的 AUROC,阈值选得再差也能挽救;反之如果 AUROC 就低,再调阈值也白搭。

**`summarize_operating_policies`**:**论文 §4.3 same-row policy 主表的生成器**。产出四种操作策略下的 TripleChecker 表现:
1. **high-retention fixed(paper setting)**:threshold=0.5,论文 default
2. **best precision with PASS recall ≥ .95**:高保留 + 最高精度
3. **5-fold CV pass-F1**:平衡策略
4. **5-fold CV hall-F1**:严格拦截策略

**同一份 predictions,同一份 gold,只是阈值口径不同,得到完全不同的 (P, R, F1)**。这就是模块 3 讲过的"同一数字有多个视角"更细粒度版本——**同一方法有多种操作点**。面试可能被问"你们主表报的 0.809 是哪个 policy 下的",答:high-retention fixed,threshold=0.5,paper setting——但同时报了另外三种作为对照,证明方法不敏感于阈值 cherry-pick。

**`summarize_supported_loss_budget_policies`**:一个特别的策略——**"我最多允许误杀 K 个 pass 三元组,在此约束下拦最多的幻觉"**。K ∈ {0, 4, 10, 25, 50, 100}。这是**下游可解释的口径**:如果我经营 KG-RAG,我能承受"每 1000 个通过的三元组里错杀 4 个真的",那对应 threshold 是多少?最终 `hall_recall` 是多少?这个视角把学术指标和实际部署 SLA 挂钩,是**论文有实际工程价值的具体展示**。

---

### 六、Bootstrap CI 与配对显著性检验

**`bootstrap_metric_ci`**:一次做 10,000 次有放回抽样,每次算 metric,取 2.5/97.5 分位数当 95% CI。**为什么 bootstrap 不是解析置信区间**:F1 不是简单的比例统计量(是 P、R 的调和平均),没有干净的解析分布。Bootstrap 是**非参数、不依赖分布假设**的通用方案。

**`summarize_triplechecker_hall_ci`**:对两个 policy(fixed@0.5 + CV hall-F1)分别 bootstrap 出 P/R/F1/acc 的 CI。这是**论文里"F1=0.804 [0.79, 0.82]"这类区间的来源**。审稿人几乎必问"你的数字有 confidence interval 吗"——这个函数就是答案。

**`binomial_two_sided_p_value`**:精确二项 p 值(对 tied case 用 `prob ≤ observed+ε` 判等号,防止浮点漂移)。用于 McNemar 检验的近似版本。**McNemar 检验的核心**:两个方法在同一批样本上有分歧的地方(A 对 B 错 vs A 错 B 对),分歧数记 (a, b);零假设是 a = b(两方法等价),二项检验算 p 值。**只用分歧样本、忽略两方法都对/都错的样本**——这是配对检验对独立样本 t 检验的核心改进,针对性极强。

**`bootstrap_delta_ci`**:两方法在同一样本上的 metric 差的 bootstrap CI。**每次抽样时两方法的 preds 用同一 idx**——这是**配对 bootstrap**,不是各自独立 bootstrap。配对能大幅缩小 CI,因为消除了"哪些 idx 落进 sample"这一层随机性。**如果 delta CI 不跨 0,就是显著差异**;跨 0 说明差异未必显著。

**`summarize_paired_scorer_tests`**:整套配对检验的组织者。对每个 policy 下的每个基线,同时报:
- delta(TC 相对基线的 metric 差)
- `delta_lower`/`upper_95`(配对 bootstrap CI)
- `mcnemar_accuracy_p`(精确 McNemar p)
- `tc_only_correct` / `baseline_only_correct`(分歧样本数)

**这是论文回应"TC 比 X 好 0.02 有什么意义"最有力的证据**。如果 `delta_lower_95` > 0 且 `mcnemar_p` < 0.05,说明差距不是偶然。

---

### 七、Label 鲁棒性场景(`summarize_label_robustness_scenarios`)

**六种替代 label 口径**,回应"你 label 定义变了结果还稳吗":

1. `main_avg_ge_2`——默认,`human_avg` ≥ 2.0
2. `strict_avg_eq_3`——只有两位都打 3 才算 pass(更严)
3. `both_annotators_ge_2`——两位都 ≥ 2(min)
4. `either_annotator_ge_2`——至少一位 ≥ 2(max)
5. `exclude_avg_1_5_boundary`——踢掉 avg=1.5 的边缘样本(标注员分歧最大的)
6. `binary_annotator_agreement`——只留两位二值化后一致的样本

**为什么这六个**:分别对应审稿人可能提出的六种质疑——"太宽松/太严格/边缘样本主导/一致性弱的样本主导"。每种口径下重跑一遍 metric,如果 TC 在六种口径下都稳定领先,就压制了这一整类质疑。

**注意 `is_avg_boundary` 定义**:`human_avg == 1.5`,只有(1,2)或(2,1)的组合。这些是"两位标注员对该样本分类完全相反(pass vs hall)"的边界样本,是标注不一致的极端情况。

**注意 `is_binary_agreement`**:两位标注员二值化后一致(要么都 ≥ 2、要么都 < 2)。**不等价于 `score_a` == `score_b`**——比如(1, 2)是二值化不一致(1 < 2 但 2 ≥ 2),(2, 3)是二值化一致(都 ≥ 2)。这个语义区别在细读脚本时容易忽略。

---

### 八、其他分析函数

**`summarize_triplechecker_threshold_sweep`**:threshold 从 0 到 1 每步 0.01,共 101 个点,每个点报完整 P/R/F1(pass + hall)+ 预测的 pass/hall 数量。这份 CSV 用来画**论文里的 ROC/PR 曲线**,以及回答"threshold 换成 0.4/0.6 结果差多少"这类具体问题。

**`summarize_label_ambiguity`**:三个子集(全体 / 剔除 boundary / 二值一致)下的 metric 对比 + 特别报告"`fp_boundary_cases`"(即因为边界样本导致的假正例数)。**这是一个非常尖锐的自查**——如果 fp 主要都是边界样本贡献的,说明"TC 的错误主要发生在人类都不确定的地方",这反而**削弱**了 fp 作为方法缺陷的证据。

**`summarize_predicate_error_slices`**:按谓词分组算 fp/fn/`fp_rate`/`fn_rate`,按 fp 降序 fn 降序排序。**面试可能问"哪些谓词表现最差?"**——这份 CSV 给出精确答案,通常是罕见谓词或语义模糊谓词(如"隶属"包含多种关系)。

**`build_row_level_diagnostics`**:每一行(每个人类标注样本)的所有分数、所有 pred(在 threshold=0.5 下)、predicate、boundary/agreement flag——**行级审计资料**,允许别人拿去做任何自己想做的分析。**匿名化**:只保留 `row_id` / predicate / 分数,不含文档文本或实体名。这是**data release 的伦理设计**——尊重原数据集的许可证。

---

### 九、`main()` 组织的完整交付物

12 张 CSV + 1 份 JSON summary:
1. `direct_scorer_comparison.csv`——各打分器 fixed@0.5 与 CV F1 对比(§4.5)
2. `scorer_ranking_diagnostics.csv`——AUROC + AP(§4.5)
3. `high_retention_scorer_policies.csv`——高保留策略对比(§4.5)
4. `operating_policies.csv`——TC 四种操作策略(§4.3)——**主表来源**
5. `supported_loss_budget_policies.csv`——损失预算策略
6. `label_ambiguity.csv`——边界样本分析
7. `predicate_error_slices.csv`——谓词切片误差
8. `triplechecker_threshold_sweep.csv`——阈值扫描
9. `triplechecker_hall_ci.csv`——hall-positive bootstrap CI
10. `paired_scorer_tests.csv`——配对显著性检验
11. `label_robustness_scenarios.csv`——6 种标签口径鲁棒性
12. `row_level_diagnostics.csv`——行级审计

**JSON summary 把所有内容再打包一份**——允许下游"一个文件读完所有分析"。

---

### 十、这个脚本和论文的映射

- **§4.3(same-row policy)** ← `operating_policies.csv`,主表 PASS-positive P/R/F1=0.694/0.970/0.809
- **§4.4(human calibration)** ← `load_human_reference` 里两位标注员 + `human_avg`
- **§4.5(paired scorer diagnostics)** ← `direct_scorer_comparison` + `paired_scorer_tests` + `scorer_ranking_diagnostics`
- **§4.5 label 鲁棒性** ← `label_robustness_scenarios`
- **附录 CI** ← `triplechecker_hall_ci`
- **附录 predicate slice** ← `predicate_error_slices`

**这个脚本的哲学**:所有基线分数都由别的脚本预先算好、写进 CSV,这一步只做统计整合。**审稿人和读者可以只审这份代码**,不必信任神经网络实现——分数被视为"客观测量数据",此脚本只是标准统计流水线。这是**离线可复现的最高等级设计**。

---

### 十一、已知薄弱环节(汇总到 §6 用)

1. **`invert_metrics` 通过重建 labels/preds 反推——数值上等价但绕**:实际上从 tp/fp/fn/tn 可以直接算 hall metrics 而不必重建,现在这种写法只是让 `metric_bundle` 一个函数复用。可读性 vs 性能都不最优,是一处工程冗余。
2. **`select_threshold` 只找最优点、不做 CV**:CV 版是 `cv_threshold_predictions`。两者混用时(policies 里主策略用 fixed threshold,budget/`high_retention` 也走 fixed),存在**在测试集上直接选阈值**的信息泄漏风险。论文对此已经做了 CV policy 作为对照,但读者需要意识到 fixed 0.5 也是论文选定的、不是数据学出来的——它靠"事先说明"来规避 cherry-pick 质疑。
3. **McNemar 用了精确二项而不是 chi-squared 近似**——在小样本(几百样本)下精确检验更稳,但会因为浮点比较需要 ε 容忍,那个 `prob <= observed + 1e-15` 的 tolerance 极偶尔会漏掉一个概率相等的项。实际影响小,严格审计时可以质疑。
4. **配对 bootstrap 只做 delta CI 不做正式假设检验**:严格来讲这是"用 CI 判断显著性"(CI 不跨 0 = 显著),不等价于两方法差异的假设检验(理论上还需要 permutation test)。但学术界普遍接受这种简化。
5. **`build_scorer_score_map` 里 TripleChecker verdict 用 `entail_score`、TripleChecker score 用 `triple_checker`——命名混乱**:verdict 通常指 0/1 决策,score 通常指连续分,但代码里 verdict 反而是连续 `entail_score`,score 反而可能是包含 SAR 的完整值。**读代码时极易搞错**。这是命名遗留问题。
6. **`is_avg_boundary` 只判 `human_avg` == 1.5**:如果未来引入 5 分制或其他量表,这个硬编码会误报或漏报。**耦合了量表选择**。
7. **`stratified_folds` 用 `offset % n_splits` 循环分配而不是随机分配**:分层分层但不打乱,某些数据顺序敏感的分析可能带来偏差(比如原始数据按 predicate 排序,分完折仍然按 predicate 聚集)。对本任务影响可能小,但严格 CV 应该 shuffle 后再 stratify。

---

**确认题**(保留入页):
1. **`accept_sprint` 脚本的核心哲学**——"神经网络分数由别的脚本预算好写入 CSV,这个脚本只做纯统计整合、不加载模型"——为什么这个设计对离线可复现性至关重要,能自己讲一遍吗?
2. **9 个打分器基线**(All-pass / ROUGE-L / BERTScore / LLM reference / TC score / TC verdict / Fixed-template NLI / Generic-relation NLI / MiniCheck)分别对应什么"对照假说"?尤其是 `TC score` vs `TC verdict` 的区别(SAR × EPR vs 纯 NLI entailment),为什么两个都要报?
3. **四种 operating policy**(high-retention fixed / best precision at recall ≥ .95 / CV pass-F1 / CV hall-F1)分别对应什么部署场景?论文主表报的 0.809 是哪一种?为什么同时报四种可以反驳"阈值 cherry-pick"质疑?
4. **配对显著性检验的完整证据链**(McNemar p + 配对 bootstrap delta CI + 分歧样本数)——如果审稿人说"你比基线好 0.02 有什么意义",你要怎么用这三样一起答?
5. **6 种 label 鲁棒性口径** vs **`label_ambiguity` 的 3 个子集**——两者的分析目的有什么不同?"`exclude_avg_1_5_boundary`" 和 "`binary_annotator_agreement`" 分别在剔除什么样的样本?
6. **`bootstrap_metric_ci` 配对 vs 独立**——为什么配对 bootstrap 能得到比独立 bootstrap 更窄的 delta CI?这个"更窄"的方法学意义是什么?

确认后进模块 6:`scripts/natural_noise_pipeline.py` + `scripts/natural_noise_*.py` 系列(自然噪声实验:用本地 Qwen2.5-3B 抽三元组然后让 TC 验证——这是论文 §4.7 controlled downstream sensitivity 之外的、rebuttal 阶段追加的、"真实抽取器错误分布"上的 diagnosis,面试可能被问的一个薄弱点)。

## §2 模块 6:`scripts/natural_noise_pipeline.py`(自然噪声评测流水线)

这个脚本是**论文 rebuttal 阶段追加的重量级实验**——用**真实的 LLM 抽取器**在**真实文档**上抽出三元组,再让 TripleChecker 判定,最后用**真人标注**当 gold。它回答一个审稿人几乎必问的问题:**"你们的受控 benchmark 是合成的,负样本也是脚本造的。真到实际抽取场景,TripleChecker 是不是就 hold 不住了?"**

这个脚本的**存在本身**就是对这个质疑的正面迎击。**面试角度**:这是全部代码里最能体现"从合成 benchmark 走向真实分布"的桥梁工程,也是论文里含金量最高的自查之一(还带 clustered bootstrap CI + failure taxonomy)。

---

### 一、这个脚本的设计哲学

**"deliberately API-free"**——脚本明确不调用任何 API 或加载任何模型。所有 LLM 抽取的调用由**外部 runner** 完成,写入缓存 JSONL;这个脚本只做:构 prompt、解析响应、组织标注数据、聚合指标。

**为什么这么设计**:
1. **审计友好**:每一次 LLM 调用都要留缓存,任何人拿到缓存可以字节级复现所有指标——不需要重新调 LLM。
2. **成本可控**:LLM 调用有成本,任何 bug 都不该让你重跑一遍抽取。缓存把"贵的一步"和"便宜的分析"隔开。
3. **合规**:调用外部 API 需要显式授权(comment 里说"after explicit approval")。这份脚本本身没有触发外部调用的能力,规避了"AI 助手悄悄调 API"的风险。
4. **数据溯源**:cache 是审稿证据链的一环——每条三元组都能追到"哪份 cache 的哪条 response"。

这种"pipeline 脚本 + 外部 runner"的分层,是**大模型时代实证研究的通行做法**。

---

### 二、Pipeline 的完整链条(11 个子命令)

`main()` 用 argparse subparsers 组织了 11 个子命令,每个是一个独立阶段。**流水线是"扇入-扇出"的**,严格按顺序执行:

**Stage A:文档采样**
- `sample-docs`——从单一数据源(DuIE 或 CMeIE 或 FinRE)采 N 篇文档
- `sample-mixed-docs`——从多个数据源采样,允许 `--source dataset=doc_prefix=path` 声明多源(rebuttal 阶段的扩展版本用这个)

**Stage B:构 prompt**
- `build-requests`——把每篇文档变成一条 LLM 抽取请求(prompt + `doc_id`),写 JSONL 供外部 runner 消费

**Stage C:(外部 runner 调 LLM,写 cache;此脚本不干)**

**Stage D:cache 检查与标注表构造**
- `cache-report`——读 cache 生成流水线元数据报告(每个数据集抽了几篇、几个三元组、几个 exact-span、几个 parse 失败)
- `build-annotations`——把 cache 展开成"每三元组一行"的标注表,预留 label 字段供人类填

**Stage E:标注表分发与合并**
- `split-annotations`——把大标注表切成 N 个 batch,分给 N 个标注员
- `merge-annotations`——把 N 份标注结果合回来,校验完整性(missing / extras)

**Stage F:TripleChecker 打分**
- `score-annotations`——**这一步唯一加载模型**,把 TripleChecker 打分附加到每行(`tc_label` / `tc_score` / `tc_layer1_pass`)

**Stage G:指标聚合**
- `summarize`——PASS-positive + Unsupported-positive 双视角 P/R/F1
- `threshold-sweep`——扫描 6 个阈值下的指标
- `bootstrap-ci`——**clustered bootstrap** 出 95% CI
- `failure-audit`——按错误类型采样错例 + 启发式打错误类别标签

**Stage H:最终报告**
- `write-report`——Markdown 论文级报告(含 setup / labeled evaluation / dataset coverage / uncertainty / failure audit / claim scope)

**面试题眼**:这 11 阶段的清晰分工体现了**学术工程的最佳实践**——每一步产物都是纯 JSONL/CSV,任何一步中间产物都可以被单独审计。

---

### 三、关键设计细节详解

#### 3.1 `build_extraction_request`——prompt 里塞入的"契约"

Prompt 里明确 5 条规则:
1. 返回 JSON schema:`{"triples": [{"subject", "predicate", "object", "source_span"}]}`
2. **每篇最多 5 条三元组**——控制稀释,避免 LLM 生成过多低质量三元组冲淡 signal
3. **`source_span` 必须是文档的精确子串**——把 span-forward 契约写进 prompt,让 LLM 也知道 span 是硬约束
4. **不许用外部知识**——防止 LLM 从预训练里补充事实,那样就不是"从文档抽"了
5. **没有可靠三元组就返回空数组**——允许 LLM 拒绝抽取,不逼它编

**为什么把契约写进 prompt**:因为如果 LLM 不知道要"exact substring",它可能改写、意译、省略——这会让 Layer 1 span 检查大量失败,数据被无谓丢弃。**面试可能被问**:"这不就等于告诉 LLM 怎么骗过你的 Layer 1 吗?" 答:反过来——Layer 1 检查后仍然存在错误(`fake_span` 依旧发生,`failure_audit` 里就有),说明就算 LLM 尽力遵守契约仍会破约。TripleChecker 的价值不是"防 LLM 抽取器",而是"审 LLM 抽取器";我们不是敌对博弈,是流水线合作。

#### 3.2 `strip_json_fence` + `repair_common_json_closure`——防御性解析

**`strip_json_fence`**:LLM 常把 JSON 包在 ` ```json ... ``` ` 里,先剥外层围栏。
**`repair_common_json_closure`**:处理一个具体的常见错误——LLM 输出 `{"triples":[...}}]` 而不是 `{"triples":[...]}`,多了一层 brace 又漏了 array 结束。这个 fix 只处理最明确的一种模式,不做通用 JSON 修复。

**为什么不用更强的 JSON 修复**:通用修复会隐藏 LLM 真的出错的样本(比如漏字段、字段名拼错),那些应该被 `parse_errors` 计数,而不是被强行 hack 通过。**只 fix 已知模式,让不确定的失败暴露出来**——这是分析代码的通用哲学。

#### 3.3 `normalize_triple`——object 嵌套结构处理

CMeIE 的 object 是 `{"@value": "..."}` 嵌套 dict(带 schema 限定),这个函数用 `if isinstance(obj, dict): obj = obj.get("@value", "")` 拆包。**这里为什么再实现一遍(utils.py 里已经有)**:因为 pipeline 里的三元组来源除了 CMeIE 还有 LLM 输出,LLM 可能模仿 CMeIE 结构也可能不模仿——所以 normalize 逻辑必须对两种都稳。这是**为 defensive parsing 冗余化实现**,不完全是坏味道。

#### 3.4 `score_annotation_rows`——按 `doc_id` 分组打分

**关键设计**:所有标注行**按 `doc_id` 分组**,同一 doc 的三元组一起送进 `checker.verify(triples, document=document)`。**为什么这样**:
- Layer 1 span 检查需要 document 上下文,同 doc 的三元组共用一份 document,不重复
- **NLI 前向是按 window 批处理的**,同 doc 的多个三元组同时打分能利用 batch 加速
- 保持了三元组和 document 的严格对齐——不会出现"用错 doc 打分"的 bug

**这是面试可能被追问的工程细节**:"你有 500 个 doc、每个 doc 平均 3-5 个三元组,怎么高效打分?"——答:按 doc 分组,doc 内 batch,doc 间循环。

---

### 四、`summarize_bootstrap_ci`——按聚类的 bootstrap CI

这个函数是**这个脚本最有学术含量的部分之一**。

**普通 bootstrap** 是对样本(每行)做有放回抽样。**问题**:同一 doc 抽出的多个三元组不独立——如果 LLM 对某个 doc 结构性地误解了,那 doc 的所有三元组会一起错。普通 bootstrap 假设独立,会**低估 CI 宽度**(假装 500 个三元组都独立,其实等价信息量可能只相当于 200 个 doc)。

**Clustered bootstrap** 的做法:**按 `doc_id`(`cluster_field`)分组,抽样时按 cluster 抽,不按行抽**。每次 bootstrap 迭代:
1. 从所有 `doc_id` 里有放回抽 N 次(N = 原始 doc 数)
2. 抽到哪个 doc,把该 doc 的所有三元组一起放进 sample
3. 在这个 clustered sample 上算 metric

**这样得到的 CI 更宽、也更诚实**——它承认"我实际只观察了 500 个 doc,不是 2000 个三元组"。

**为什么这一点很重要**:自然噪声 pilot 只有 ~59 篇 doc(383 三元组),独立 bootstrap 会算出虚假窄的 CI,让审稿人觉得"你只有 383 样本报的这么精确?"。Clustered bootstrap 直接回应:"我用最保守的方式估 CI,承认样本量小,所以 CI 是宽的。"这个诚实反而**增加可信度**。

面试题:"你为什么用 clustered bootstrap 而不是普通 bootstrap?"——答:"同一文档的三元组不独立(共享抽取器错误、共享标注员判断惯性),按文档聚类采样才能反映真实样本量。"

---

### 五、`build_failure_audit_rows`——失败模式抽样与启发式分类

**目的**:错在哪比错多少更能指导后续改进。这个函数从 fixed-threshold 错例里各采 10 条 `false_pass` 和 10 条 `false_reject` 出来,由人手审(`manual_failure_category` 字段留空供填)。

**`suggest_failure_category` 的启发式分类逻辑**:
1. 如果 Layer 1 就没通过(`tc_layer1_pass = False`)→ `span_not_copied`
2. 如果是 `false_pass`(gold hall, pred pass):
   - 谓词是 `@` / `与` / `相关` 之一 → `malformed_or_vague_relation`(抽取器输出了畸形谓词)
   - 标注理由含"不能支持 / 说的是 / 不支持 / 不能建立" → `wrong_entity_or_relation`(标注员认为实体/关系错了)
   - 其他 → `semantic_false_pass`(NLI 真的判错了)
3. 如果是 `false_reject`(gold pass, pred hall):
   - 标注理由含"结合前文 / 结合后文" 等 → `context_carryover`(证据跨句,NLI 只看当前 span 拿不到全部信号)
   - `source_span` 含 `、 ，` `及` `和` 等 → `list_or_aggregation`(span 是列表,NLI 处理并列结构差)
   - 其他 → `semantic_false_reject`

**这套启发式**分类不完美,但**先给人类一个 hint**,后续人工审议可以修正。这是"AI 建议 + 人类裁定"的经典 hybrid pattern。**报告里明确写**:"Suggested categories are heuristic review aids; final error-taxonomy claims should state their adjudication source explicitly."——**明确声明启发式的地位,不会被误引用为最终结论**。

**这些失败模式的语义**是论文里最有诊断价值的产出之一。**面试题**:"TripleChecker 的主要错误来源是什么?"——答:`false_pass` 通常是"谓词畸形或语义近似但不等",`false_reject` 通常是"证据跨句或列表并列"。前者提示 RTAV 需要更严格的谓词过滤,后者提示 Layer 2 需要考虑多 span 聚合。

---

### 六、`layer1_allows_pass_prediction`——阈值扫描时的正确性守卫

**在 `threshold_sweep` 里**:
```
preds = [1 if layer1_allows_pass_prediction(row) and tc_score >= threshold else 0 for row in labeled]
```

**这一细节是脚本里最容易被忽略的正确性守卫**。含义:即使 threshold=0(NLI 全放行),**Layer 1 失败的样本仍然被判 hallucination**——因为 Layer 1 是硬约束,不受 NLI threshold 控制。

**为什么这个守卫重要**:如果只用 `tc_score >= threshold` 判定,threshold=0 时所有三元组都过——包括那些 `source_span` 根本不在 document 里的 `fake_span` 样本。那样 threshold=0 的 recall=100% 就变成了假象(是因为把 `fake_span` 也放行了)。这个守卫保证:**Layer 1 的错误无论 threshold 怎么调都是 hallucination**,这才符合论文"两层与"的定义。

面试题:"如果 NLI threshold 拉到 0,是不是就等价于什么都放行?"——答:不是,Layer 1 依然会拦住 span 不匹配的样本。**这个"threshold=0 仍能拦一部分"的行为**在 `threshold_sweep` 表格里体现为"threshold=0 的 `pass_recall` < 100%",是可观察的证据。

---

### 七、`build_expanded_report`——最终 markdown 报告

产出一份自包含 markdown,分节:
- **Setup**:采样了几篇 doc、cache 了几篇、抽了几个三元组、几个 `exact_span`、几个 parse 错误、用了什么模型
- **Labeled Evaluation**:标注了多少、双视角 P/R/F1 表
- **Dataset Coverage**:按数据集切片的覆盖表
- **Uncertainty**:clustered bootstrap CI 表
- **Failure Audit Packet**:错例抽样统计,并**明确写**"启发式类别只是审议辅助"
- **Claim Scope**:范围声明——**这份实验只支持"抽取器输出上的 source-span 应用性诊断"**,**不**支持"生产 KG-RAG 鲁棒性 / 外部事实正确性 / 超越其他事实核查器"这些结论。

**"Claim Scope" 这一节至关重要**——它主动圈出这份实验能不能支持什么,避免过度推广。这是**学术诚信的物理体现**,也是审稿人最喜欢看到的自我克制。**面试可能被问**:"你这个自然噪声实验能不能证明 TripleChecker 生产可用?"——答:"论文里已经写明 claim scope,不做这样的推论。这份实验只支持诊断 source-span 契约在真实抽取器输出上的适用性。"

---

### 八、这个脚本和论文的映射

这份 pipeline 对应的是**论文里的自然噪声评测章节**(通常是附录里的"Natural-Noise Applicability Diagnostic")。产出:
- 主要指标:PASS-positive P/R/F1 与 Unsupported-positive P/R/F1(双视角)
- Clustered bootstrap CI(承认小样本)
- Failure taxonomy(诊断性分析)
- Cache report(数据溯源)

**这份实验的历史**:先有 59 三元组的小 pilot(用本地 Qwen2.5-3B),后来 rebuttal 阶段扩展到 383 三元组(mixed source 版本)。两次实验都用这份 pipeline,只是 `sample-mixed-docs` 是后加的。

---

### 九、已知薄弱环节(汇总到 §6 用)

1. **样本量小(383 甚至更少)**:虽然用 clustered bootstrap 承认了 CI 宽度,但绝对量仍然不足以支持"真实分布"这种表述。理想应扩到千级。
2. **只用一个抽取器(Qwen2.5-3B)**:不同 LLM 抽取风格差异大——GPT-4 的输出分布 vs Qwen 的输出分布可能截然不同,当前实验没覆盖。审稿人可以质问"换一个更强的抽取器你还行吗"。
3. **failure category 用启发式**:虽然报告里声明了,但如果不做人工裁定的正式版本,读者很容易把启发式类别当成最终结论。这个 gap 靠 disclaimer 兜底,不完美。
4. **`suggest_failure_category` 的启发式规则**是硬编码的语言学线索(比如"结合前文"这类中文短语),对英文或其他语言完全不适用。**语言绑定**是隐藏假设。
5. **`repair_common_json_closure` 只处理一种模式**:LLM 出错的方式远不止这一种,`parse_errors` 里可能藏着一些其实可修复的样本。取舍是"宁可漏也不错修"——保守。
6. **prompt 里的 "up to 5 triples" 是硬编码经验值**:没做 ablation 分析"limit=3 vs 5 vs 10"对最终指标的影响。可能被追问。
7. **人类标注只有单人**(annotation batch 分给多个标注员但每条只标一次),不像 `accept_sprint` 那份有 A/B 两人。所以没法算 IAA、没法做 label robustness。这个精简是**成本妥协**,论文附录里应该明说。
8. **`build_extraction_request` 的 prompt 是英文写的**(说明 rules 是英文,但让 LLM 抽中文)——**跨语言 prompt**,LLM 可能因为规则语言和内容语言不一致而理解偏差。理论上应该用中文 prompt。这是可以被 review 抓的点。

---

**确认题**(保留入页):
1. **"deliberately API-free" 的设计哲学**——为什么把 LLM 调用和分析代码严格隔开?这种"cache-first"模式对可复现性、成本、合规、审计各有什么好处?
2. **11 阶段流水线的完整链条**(sample-docs → build-requests → cache → build-annotations → split → 人标 → merge → score → summarize + threshold-sweep + bootstrap-ci + failure-audit → write-report),每一阶段的产物和上下游依赖能自己讲一遍吗?
3. **Clustered bootstrap 的动机**——为什么按 `doc_id` 聚类的 bootstrap 比普通 bootstrap 更诚实?样本量小的时候这个方法学选择带来的 CI 宽度对论文可信度是加分还是减分?
4. **`layer1_allows_pass_prediction` 这个正确性守卫**——为什么 `threshold_sweep` 时即使 threshold=0 也不能让 `fake_span` 通过?这体现了论文"两层与"定义的什么本质?
5. **`suggest_failure_category` 的四类失败模式**(`span_not_copied` / `semantic_false_pass` / `wrong_entity_or_relation` / `malformed_relation` / `context_carryover` / `list_or_aggregation` / `semantic_false_reject`)背后暴露的**TripleChecker 结构性弱点**——面试被问"你们方法的主要错误来源"时能说清楚吗?
6. **"Claim Scope" 声明的作用**——这份实验能支持什么、不能支持什么。学术诚信之外,它对回应 review 有什么战术价值?

确认后进模块 7:`scripts/analyze_source_span_benchmark.py` + `scripts/source_span_paper_tables.py` + `scripts/audit_source_span_errors.py`(源自主 benchmark 的分析集合——负例失败模式的分层报告、论文所有主表格的生成器、错例审计。相较模块 5 的人类集分析,这一层是"合成 benchmark 上的深度自查",覆盖 15,000 行的完整审计)。

## §2 模块 7:源自主 benchmark 的分析三件套(`analyze_source_span_benchmark.py` + `source_span_paper_tables.py` + `audit_source_span_errors.py`)

这三个脚本合在一起,是**论文主表(§4.2 controlled source-span benchmark)所有数字的直接生成器**,以及配套的错例审计。相较模块 5 的 `accept_sprint_analysis`(300 行左右人类标注集分析),这一层要处理**15,000 行合成 benchmark 的完整评测**,而且需要跟多个基线打分器同框对比(Fixed-template NLI、Generic-relation NLI、TripleChecker、TripleChecker-bank)。**面试题眼**:这一层的输出就是评审员看到的 §4.2 主表格 + 附录 CI 表格 + 错例分析——**论文最外面那层的 F1=0.8015 就是从这里蹦出来**。

**三件套的分工**:
- `analyze_source_span_benchmark.py`——单方法的"跨条件切片 + 排序诊断 + 三策略"分析,通用工具层
- `source_span_paper_tables.py`——**多方法对比 + clustered bootstrap CI + 配对 delta CI + 论文主表**,论文出货层
- `audit_source_span_errors.py`——按 (dataset, condition, `error_type`) 分层挑错例 + 计数,错例审计层

---

### 一、`analyze_source_span_benchmark.py`——单方法综合分析

#### 1.1 `row_pred_pass`——预测判定的原子函数

这个函数是整个分析层的地基,决定**如何从打分结果里推出"pass/hall"**。三条判定链:
1. 如果 `tc_label` 是 `fake_span` → 直接判 0(hall)。这是 Layer 1 硬拦截。
2. 如果有 `layer1_field`(如 `tc_layer1_pass`)且为 False → 判 0。第二道 Layer 1 拦截,用 boolean 字段而非 label。
3. 否则看 `tc_score >= threshold` → 1 或 0。这是 Layer 2 NLI 判定。

**为什么两道 Layer 1 拦截**:因为**不同基线方法的输出格式不同**。有的方法给 `tc_label='fake_span'` 语义标签,有的方法给 `tc_layer1_pass=False` 布尔字段,函数用**任一命中就否决**的策略稳健处理两种格式。**这是"字段冗余但代码鲁棒"的经典 pattern**。

**面试题**:"threshold=0 时会不会所有样本都通过?"——答:不会,Layer 1 硬约束不受 threshold 控制,`fake_span` 永远被拦。这跟模块 6 的 `layer1_allows_pass_prediction` 一脉相承。

#### 1.2 `_metric_row_from_predictions` + `compute_metric_row`——指标行组装

计算 pass-positive 和 hall-positive 双视角 P/R/F1,产出 `method / protocol / threshold / n / n_pass / n_hall / pass_precision / ... / tp/fp/fn/tn / score_mean` 一整行。**关键细节**:`hall metrics` 通过 `invert_metrics` 从 pass metrics 反推 tn→tp、fn→fp,不重新遍历数据。这跟 `accept_sprint` 的做法一致,是**代价换可读性**的取舍。

**这里的 `invert_metrics` 有一个隐藏 bug 修复**:上一层(`accept_sprint`)通过重建 labels/preds 反推;这个脚本直接从 (tn, fn, fp, tp) 算 hall precision/recall,更省事,但**注意 hall precision 的定义**:`tn / (tn + fn)`——**"预测为 hall 且真的 hall"占"所有预测为 hall"的比例**。等价于 pass 视角的 `1 - fdr`(错误发现率的补)。这个对称性面试可能被追问。

#### 1.3 `summarize_by_slice`——按维度切片

按 `slice_fields`(可以是 `["condition"]` 单维、`["dataset", "condition"]` 双维)分组,每组算一份完整 metric row。产出**分层报告**:比如 DuIE × `fake_span` 一行、DuIE × `object_replacement` 一行、CMeIE × `predicate_mismatch` 一行……

**为什么按 condition 切最重要**:因为**四种负样本条件的"应有难度"是有先验预期的**——
- `fake_span` 应该在 threshold=0 时就 100% 被拦(Layer 1 的直接检验)
- `object_replacement / subject_replacement` 中难度:同类型干扰,Layer 2 语义判定
- `predicate_mismatch` 可能最难:主体客体都在 span 里,只是谓词错

**按 condition 切之后,每类分别报 F1**,就能验证"是不是每一类都能被拦,而不是某一类拉高整体假象"。如果 `fake_span` 的 `hall_recall`=1.0 但 `predicate_mismatch` 只有 0.6,说明整体 F1 主要靠 `fake_span` 撑,方法在语义判定上还不行。**这是 §4.2 主表按 condition 分行报数的动机**。

#### 1.4 `ranking_rows`——排序诊断(AUROC + AP)

跟 `accept_sprint` 一样但更简洁:pass 视角和 hall 视角各算 AUROC 和 AP。**threshold-independent 的"分数把 pass 和 hall 分开"能力**。面试角度:AUROC=0.5 是随机,>0.9 是强分离。TripleChecker score 在此 benchmark 上的 AUROC 直接就是**"分数信号本身有多强"**的答案。

#### 1.5 三种阈值策略选择

这里跟 `accept_sprint` 类似但把三种策略明确列出:
- `all_pass_policy_row`——全放行下限
- `layer1_only_policy_row`——**只用 Layer 1、不启用 NLI** 的策略。这个非常重要:它单独隔离出 Layer 1(SAR)的贡献。看到这个 baseline 的 F1,就能算出 "Layer 2 NLI 贡献了多少增量"。
- `policy_rows`——TripleChecker 三种 protocol:fixed@0.50 / high-retention (recall ≥ 0.95) / best HALL-F1

**Layer-1-only baseline 是这层最有价值的一个策略基线**。面试可能被问"你的 SAR × EPR 分解各贡献多少?"——答:layer1-only 是纯 SAR 的表现(所有过 span 检查的样本都判 pass);完整 TripleChecker 是 SAR + EPR。两个 F1 的差就是 EPR 的边际贡献。

#### 1.6 `select_high_retention_threshold` / `select_hall_f1_threshold`

在 1001 个候选阈值(0 到 1 步 0.001)里,分别按两个目标挑最优:
- high-retention:`pass_recall` ≥ min → `hall_recall` 最大化 → `hall_f1` → `pass_f1` → threshold
- hall-F1 optimal:`hall_f1` → `hall_recall` → `pass_f1` → threshold

**排序键都是元组**,允许"主目标平局时按次目标 tie-break"。这是**规避 argmax 平局歧义**的规范做法。

---

### 二、`source_span_paper_tables.py`——论文最终出货层

这层做的事跟 §1 有重叠,但**引入了三个升级**:

#### 2.1 `add_cluster_key`——聚类键构造

每行加上 `cluster_key = dataset::doc_id::triple_id`。**为什么这么定聚类**:一个 (dataset, `doc_id`, `triple_id`) 对应"同一个真实三元组的 5 行"(1 gold + 4 negative),这 5 行**不独立**——它们共享同一 document、共享同一 gold 三元组。bootstrap 时应该"要么整组抽进来,要么整组不抽",不然会低估 CI 宽度。

这跟模块 6 按 `doc_id` 聚类的思路一致,但**颗粒度更细**——按 triple 而非按 doc 聚类。因为主 benchmark 里每个 doc 可能带多个 triple(每个 triple 各自 1+4),按 doc 会把不同 triple 也捆一起,过于保守;按 triple 更精准反映"一个真三元组对应的 5 个受控变体"这一实际依赖单元。

#### 2.2 `_score_profile` + `_metric_row_from_profile`——预排序加速

**关键性能优化**:先把所有 pass 和 hall 的分数各自排序存好(`pass_scores`, `hall_scores`),然后用 `bisect.bisect_left` 二分查找算某个 threshold 下的 TP/FP。**为什么要这样**:因为 bootstrap 会跑 `n_boot`=1000 次,每次都要在同一个 sample 上算多个 threshold 的 metrics,如果每次都遍历一遍 rows 太慢。**profile-based 有序结构 + 二分**把 threshold 判定从 O(n) 降到 O(log n)。

**面试题**:"你 15,000 行 × 1000 次 bootstrap × 多方法多阈值,怎么算完的?"——答:预排序 + 二分,每次 bootstrap 只算一次 profile,然后每个 threshold 二分定位。

#### 2.3 `bootstrap_phase3_rows`——单遍 bootstrap,批量产 CI + delta

这个函数是整个脚本的性能核心。它做了一件很聪明的事:**只跑一次 bootstrap loop,一次采样内同时算所有方法、所有 protocol、所有 metric、以及所有配对 delta**。

**为什么要这样**:如果每对 (方法, protocol, metric) 独立 bootstrap,总共要跑 `N_specs` × `N_protocols` × `N_metrics` + `N_pairs` × `N_protocols` × `N_metrics` 次 loop,爆炸。合成一次采样:每次抽 sample → 对每个方法算 profile → 对每个 protocol 二分算 metric → 收集所有 metric 值 + 计算配对 delta。**一次采样,一切数据一起出**。

**方法学上还有一个隐藏优势**:**配对 delta 的 CI 是从同一次采样计算的**——即"方法 A 和方法 B 在同一份 bootstrap sample 上分别算 metric,取差"。这就是配对 bootstrap(paired bootstrap),比"独立 bootstrap 各自的 CI 再算差"要窄得多、更诚实。这个巧妙的 batch loop 同时兼顾了性能和统计正确性。

#### 2.4 `paired_delta_ci` / `paired_delta_rows`

配对显著性检验的重头戏:
- **对比对象**:TripleChecker vs Fixed-template NLI(有 verbalize、有类型分派) vs Generic-relation NLI(无 verbalize)
- **对比 metric**:`hall_f1`(论文关心的 SU-F1 视角)
- **对比 protocol**:fixed@0.50 + best HALL-F1
- **输出**:`point_a`、`point_b`、delta、CI [`ci_low`, `ci_high`]

**这层的核心叙事**:"TripleChecker 相对基线的 delta `hall_f1` 在 fixed@0.50 下是多少?CI 跨不跨 0?"——CI 不跨 0 就是显著,支持"我们的方法确实优于基线"的论文主张。

**注意 delta 的对齐**:`_delta_pairs` 显式圈定了对比对——只对 `TripleChecker / TripleChecker-bank` 两个方法做对比,与 `Fixed-template NLI / Generic-relation NLI` 两个 anchor 对比。**这是"消融式对比"**——通过对比明确 RTAV 的贡献、bank 的贡献。

#### 2.5 `supported_loss_budget_rows`

**部署导向的策略**:budgets ∈ {0, 25, 50, 100, 250, 500}——"我最多允许误杀 X 个真 pass 三元组,在此约束下拦最多的 hall"。跟 `accept_sprint` 里的对应版本一样,但预算尺度更大(因为总量 15,000 而不是几百)。**部署价值**:直接告诉工程师"如果你的 SLA 是每 10,000 三元组最多误杀 100 个,那你 threshold 该设 0.42"这类具体决策。

#### 2.6 `write_review_packet`——审稿包

生成 markdown 报告,**里面有一段非常关键的"Main Claim Guardrail"**:
- **Supported claim**:TripleChecker 是 source-span 审计与策略诊断框架
- **Unsupported claim**:TripleChecker **不**声称"普遍优于 fixed-template NLI"或"证明生产 KG-RAG 鲁棒性"

跟模块 6 的 "Claim Scope" 一致——**主动圈定 claim 边界**,不让读者过度推广。这是**论文诚信最高级形式**,也是审稿人最难驳斥的写法(你自己已经克制了,他还能挑什么)。

---

### 三、`audit_source_span_errors.py`——错例审计

比前两个短很多,只做两件事:

#### 3.1 `classify_prediction_error`

对每一行判 correct / `false_pass` / `false_reject`。用 `row_pred_pass` 得预测,和 `label_pass` 比较。三个分类穷尽。

#### 3.2 `select_error_examples`

**按 (dataset, condition, `error_type`) 三维分组**,每组挑 `limit_per_group` 条例子:
- `false_pass` 类:按 score **降序**——挑"打分最高但其实是 hall"的极端错例(最有诊断价值)
- `false_reject` 类:按 score **升序**——挑"打分最低但其实是 pass"的极端错例

**为什么按打分极端排序**:因为这些是**模型最自信但错了**的样本。中等打分的错误往往是模糊边界,不够暴露方法弱点;极端错例更能反映"结构性缺陷"。

**产出**:每条错例带 `record_id / dataset / condition / error_type / method / score / subject / predicate / object / source_span / hypothesis / notes`——**足够信息让人类看一眼就能诊断错在哪**。**hypothesis 字段是 RTAV 生成的 NLI 假设**,保存下来允许"看 verbalize 是否有问题"的定位。

#### 3.3 `audit_count_rows`

按 (method, dataset, condition, `error_type`) 分组统计错误数。这是错例的**汇总视图**,配合上面的抽样例子一起看:数字告诉你哪一类错最多,例子告诉你错在哪。

---

### 四、这三个脚本和论文的映射

- **§4.2 主表(SU-F1=0.8015)** ← `paper_main_policy_table.csv`(from `paper_tables.py`)
- **§4.2 按 condition 切片子表** ← `paper_condition_table.csv` + `metrics_by_condition.csv`
- **附录 CI** ← `bootstrap_ci.csv`
- **附录配对 delta** ← `paired_method_deltas.csv`
- **附录 supported loss budget** ← `supported_loss_budget_policies.csv`
- **附录错例分析** ← `condition_error_audit.csv` + `condition_error_examples.jsonl`
- **审稿包** ← `paper_review_packet.md`

**这三个脚本是主表的"官方生成源"**,论文里所有 §4.2 相关的数字如果对不上,一定是这里出的。

---

### 五、这一层跟 `accept_sprint_analysis.py` 的关键区别

| 维度 | `accept_sprint`(模块 5) | 主 benchmark 分析(模块 7) |
|---|---|---|
| 数据源 | 人类标注集(几百样本) | 合成 benchmark(15,000 样本) |
| gold 来源 | `human_avg`(1-3 分二值化) | condition(合成脚本决定) |
| 聚类维度 | 单样本(独立 bootstrap) | (dataset, `doc_id`, `triple_id`) 三级聚类 |
| 主要视角 | pass-positive | hall-positive(SU-F1)是论文主指标 |
| 检验对象 | ROUGE / BERTScore / LLM / MiniCheck | Fixed-template NLI / Generic-relation NLI |
| 性能优化 | 无(样本量小) | profile + bisect 加速 bootstrap |
| Layer-1-only baseline | 无 | 有(隔离 SAR 贡献) |
| 特色 | label robustness 6 场景 + boundary 分析 | condition 切片 + supported loss budget + `paper_review_packet` |

**这两套分析各自服务不同的论文章节**,合起来构成完整证据链——**合成 benchmark 做主表(§4.2),人类标注做校准(§4.3–§4.5)**。

---

### 六、已知薄弱环节(汇总到 §6 用)

1. **`invert_metrics` 在 analyze 版本和 `accept_sprint` 版本实现不同**:analyze 版本走精简 tn/tp 直接算(可能存在 f1=0 的初始化 bug 通过 `_hall_f1` 补全的丑陋 workaround——见 line 59-65 的 `| _hall_f1(pass_metrics)` union dict 补丁)。这是**代码演化过程留下的技术债**。
2. **`row_pred_pass` 里两道 Layer 1 拦截依赖字段名 hardcode**:如果新方法用不一样的字段名(比如 `layer1_ok` 而非 `tc_layer1_pass`),需要改 `METHOD_SPECS` 而不是自适应识别,扩展性一般。
3. **`bootstrap_phase3_rows` 里 seed 复用**:每次 bootstrap 循环用同一个 `rng`,所以每次采样共用 seed。理论上没问题(单一随机流),但如果两个方法的 metric 计算内部有不同随机步骤会耦合。此脚本里没有内部随机,所以安全。
4. **`_score_profile` 里 blocked 样本(`fake_span` 或 layer1 fail)从 `pass_scores`/`hall_scores` 里被剔除**——它们的判定不受阈值影响,直接算入 tp/fp 计数的另一侧。**这个逻辑非常隐蔽**:blocked 样本永远预测为 hall,所以 gold=hall 的 blocked → tn,gold=pass 的 blocked → fn。这需要仔细读 `_metric_row_from_profile` 才能推出来。**代码正确但可读性差**,是一处需要在论文附录里额外说明的实现细节。
5. **`condition_error_examples` 的选例按 score 极端排序**:虽然诊断价值高,但**样本非典型化**——审计员看到的都是极端错例,可能低估中等错例的严重性。**理想应加一个"按 score band 分层采样"** 的补充版本。
6. **`paper_condition_rows` 只报 fixed@0.50 threshold**——没有跨 protocol 的 condition 切片。如果 threshold 变化后各 condition 表现变化不同,这个 fixed-only 视图会掩盖某些操作点问题。
7. **`add_cluster_key` 用 `::` 连字符可能与真实数据集里的 `::` 冲突**——极偶尔的字符碰撞会让不同真实 (dataset, `doc_id`, `triple_id`) 组合的 `cluster_key` 相同。**理论 bug**,实际几乎不发生。
8. **Layer-1-only baseline 只在这一层出现,不在 `accept_sprint` 里**——如果人类标注集也想看纯 SAR 贡献,`accept_sprint` 得单独加一遍。**跨脚本的诊断口径不完全对齐**。

---

**确认题**(保留入页):
1. **`row_pred_pass` 里两道 Layer 1 拦截**(`tc_label==fake_span` 或 `tc_layer1_pass==False`)——为什么要两道而不是一道?这体现了"多方法字段格式不统一但代码要鲁棒"的什么设计取舍?
2. **`layer1_only_policy_row` 这个 baseline 的方法学意义**——如何用它 + full TripleChecker 的 F1 差异来隔离 SAR 与 EPR 各自的贡献?面试被问"你的两层分别贡献多少"能答上吗?
3. **`cluster_key` = (dataset::`doc_id`::`triple_id`) 的选择动机**——为什么按 triple 而不是按 doc 聚类?这个粒度选择对 CI 宽度和方法学诚实的意义各是什么?
4. **`_score_profile` + `bisect` 的性能优化**——为什么 15,000 样本 × 1000 bootstrap × 多方法多阈值必须预排序?这里省下的是 O(n) 到 O(log n) 的哪一部分?
5. **`bootstrap_phase3_rows` 的"单遍 bootstrap 批量产出 CI + delta"**——为什么这样能同时保证性能又保证 delta CI 是"配对"的(而不是独立 CI 之差)?这个巧思对论文的可信度有什么支撑?
6. **`paper_review_packet.md` 里的 Main Claim Guardrail**(声明能支持什么、不能支持什么)——跟模块 6 的 Claim Scope 一脉相承,面试被问"你论文是不是过度声明了"时,这套 guardrail 战术上怎么用?
7. **`condition_error_examples` 按 score 极端排序**——为什么"打分最高但其实错"的例子诊断价值高于中间样本?这暴露 TripleChecker 的什么结构性弱点会最先浮出水面?

确认后进模块 8:`scripts/validate_accept_claims.py` + `scripts/source_span_paper_tables.py` 之外的**RTAV heldout / leakage diagnostic**两个脚本(`source_span_rtav_heldout.py` + `source_span_rtav_leakage_diagnostic.py`)——这两个是回应"RTAV bank 会不会 overfit 到测试集谓词"这类审稿人质疑的关键防守脚本,面试可能被追问的点。

我已经把三个防守脚本的全貌读完了(`validate_accept_claims`.py 2068-4067 段 + `rtav_heldout` + `rtav_leakage_diagnostic`)。下面进入 **模块 8**——审计防线三件套。这一层是整篇论文最不"性感"但审稿人和面试官最容易抓的部分,因为它直接对应"你怎么证明你没作弊/没过拟合到 bank"这个质疑。

---

## 模块 8 · 审计防线三件套 (`validate_accept_claims.py` + `source_span_rtav_heldout.py` + `source_span_rtav_leakage_diagnostic.py`)

### 8.1 三个脚本各自解决什么问题

先给出一句话定位,后面再各自展开:

- `validate_accept_claims.py`——**第三方复现验证器**。它不加载任何模型、不调用任何 API,只读 CSV/JSON/Markdown 产物,把论文里每一个"报出的数"从行级 CSV 上重新算一遍,一致才通过。它是"我们敢公开数据"这句话的技术兑现。
- `source_span_rtav_heldout.py`——**RTAV 模板 bank 的谓词/文档留出控制**。它切分谓词与 `doc_id` 折,产出 split 清单和状态报告,说明当前公开产物"哪些是留出证据、哪些不是",并明确挂上 `blocked_requires_masked_bank_scoring` 等状态,阻止我们自己或读者把全 bank 结果误读为留出鲁棒性。
- `source_span_rtav_leakage_diagnostic.py`——**bank 与 benchmark 的谓词覆盖 + 泄漏门控**。它把"benchmark 里多少谓词被 bank 覆盖"、"full-bank vs 无 bank 的 HALL-F1 差值"、"人工 200 条集上的 predicate-hiding 平均 Δ"整合到一张表,并在结尾放一个 `leakage_gate` 行:只要 benchmark 级留出分尚未生成,这行的 value 就写 `missing`,并明说"不得据此声称 unseen-schema 鲁棒性"。

三个脚本合在一起,回答的是同一个审稿问题:**"你的 RTAV bank 是不是在测试集上过拟合了?"** 答案是:通过留出切分暴露风险 + 通过泄漏门控禁止过度宣称 + 通过验证器让读者可自查,而不是靠"我们觉得没有"。

### 8.2 `validate_accept_claims.py`——第三方复现验证器

**设计哲学**。这一份脚本是整篇论文可复现性的"最后一公里"。它假设读者拿到的是我们发布的 `results/` 目录(带 `claims_manifest.csv`、各类 CSV、各种 `*.md` 报告和行级 JSONL),然后:第一,把 30 条必答的 claim id 逐个核对到 manifest 里,任何一条缺失就报 `Missing required claim manifest ids`;第二,对能重算的每个数字,从行级数据独立重算一次,和报告里的数比对,超过容差就抛 `ValidationError`。这意味着,如果我们哪一行 CSV 与报告不一致、或者哪一处 markdown 的表格数字凑不上,验证器会直接失败——而这个失败是任何拿到发布包的人都能触发的。

**核心机制一:`REQUIRED_MANIFEST_CLAIMS`**。这是硬编码的 30 项 claim id 集合,覆盖 source-span 主表、bootstrap CI、按条件切分、损失预算、baseline delta、prevalence 策略、label 审计包、双标注包、label 有效性汇总、label 噪声敏感度、RTAV 泄漏诊断、RTAV heldout 控制、RTAV bank 溯源审计、DuIE 主结果、阈值操作策略、支撑损失预算、标签歧义、成对打分、high-retention baseline、ranking 诊断、直接 baseline 协议、Qwen2.5-3B 自然噪声 pilot(以及它的 audit / expanded / `human_audit` / `double_annotation` / `baseline_sensitivity` / `calibration_50` 子项)、以及 KG-RAG 章节。任何一项 claim 未在 manifest 中列出对应的 `result_file`,或者 `result_file` 指向的路径不存在,直接失败。这样论文 vs 代码 vs 数据的"三体一致"由脚本机械地兜住。

**核心机制二:行级重算,而不是复读**。以自然噪声 pilot 为例,验证器不去读 `summary.json` 里的 f1 然后与 `report.md` 里的字面数字比对——那只能验证"我们没手抖打错字"。它做的是:读 `local_qwen25_3b_annotation_batch_scored.jsonl` 的 59 行,自己重算 `natural_summary_from_scored_rows`(precision/recall/f1/accuracy 及 tp/fp/fn/tn 全套),再和 summary.json 及 report.md 里对应字段比对。任何环节动过手脚——比如手工调了 f1、或者选择性剔除了 12 条 Layer-1 fail——重算结果都会对不上。同一套机制在 expanded natural(383 行)、threshold sweep、bootstrap CI 上重复。

**核心机制三:blind field 强制**。`SOURCE_SPAN_BLIND_FIELDS`、`NATURAL_DOUBLE_BLIND_FIELDS`、`SOURCE_SPAN_BLIND_LEAK_FIELDS`、`NATURAL_DOUBLE_BLIND_LEAK_FIELDS`、以及带 value pattern 的 `SOURCE_SPAN_BLIND_LEAK_VALUE_FIELDS/_PATTERNS`,是发给标注员看的表格字段白名单/黑名单。`validate_blind_annotation_sheets` 检查每份 `blind_annotator_*_sheet.csv`:表头必须精确等于白名单集合(既不能缺、也不能多)、任何在 leak 列表里的字段名一旦出现在表头就抛错、每一行 human_* 字段必须全部为空(即"标注员拿到的表是空白的,标注前不能看到任何模型判决")、id 顺序必须与参考一致。value-leak 检测更狠:它扫描每行每列的字符串,只要出现 leak 的关键字子串(比如模型的 label、score 相关关键词),不管在哪一列,都抛错。这是审稿人若问"你能证明你的标注员不是被 TripleChecker 结果先入为主的吗?"时的兜底证据。

**核心机制四:guideline requirement checks**。`SOURCE_SPAN_LABEL_GUIDELINE_REQUIREMENTS`、`SOURCE_SPAN_DOUBLE_GUIDELINE_REQUIREMENTS`、`NATURAL_DOUBLE_GUIDELINE_REQUIREMENTS` 是"标注指南 markdown 里必须出现的关键短语清单",比如"Use only the provided document and source span"、"Do not consult external sources"、agent-adjudicated 时必须显式声明 "not human-labeled" 等。`expect_guideline_requirements` 是内容级门控,防止发布时指南被临时删除关键条款而没人发现。

**核心机制五:agent-adjudicated 溯源**。这是我们诚实姿态的关键——因为我们没有真正的两名人类标注员,双标注环节的最终标签是 agent-adjudicated,而不是 human-adjudicated。`validate_agent_adjudication_provenance` 检查 `agent_adjudication_provenance.json` 里必须有 `label_source=agent-adjudicated`、`schema_note` 里必须含 "not human-labeled"、`blind_input_files` 必须列出 `blind_annotator_a`/b 两份、`posthoc_joined_output_files` 必须包含合并后的 annotator sheets,以及必须记录 `annotator_a_id / annotator_b_id / adjudicator_id` 三个身份标识。同一份 markdown 报告里也必须字面出现 "`label_source`=agent-adjudicated" 和 "not human-labeled"。这是我们"不假装是人工"的技术承诺。

**核心机制六:paper overclaim guardrails**。`validate_paper_overclaim_guardrails` 是一个正则黑名单,针对 paper.md 全文的规范化版本,匹配以下句式若命中即失败:"natural-noise ... human-labeled evidence"、"controlled source-span benchmark ... human-labeled"、"RTAV ... document-held-out robustness"、"predicate-held-out robustness"、"proves/demonstrates production KG-RAG robustness"、"natural-noise KG-RAG"、"kg-rag ... under/with/on natural-noise" 等。这是把"我们对哪些事情不能声称"写死进 CI——如果哪一天我们在论文里手滑写了 "human-labeled natural-noise",validator 直接把 build 打红。

**核心机制七:source-span 行级 policy 一致性**。`validate_source_span_row_level_consistency` 拿 `scored_with_template_baselines.jsonl` 里的每一行,用 `SOURCE_SPAN_FIXED_METHOD_SPECS` 里 all-pass / layer-1-only / fixed-template NLI / generic-relation NLI / TripleChecker 五种方法各自的判决字段,重算 metric bundle 并与 `baseline_comparison_policy_table.csv` 的每一行逐字段比对(precision/recall/f1、pass 和 hall 各一套、tp/fp/fn/tn 四个整数)。然后对每个条件切片重复。最后 supported-loss budget 25/50/100/250/500 逐个用 `source_span_supported_loss_expected_row` 二次穷举阈值找到最优,和发布表比对。这确保"论文里那张主表上的每一个方格"都能从 15000 行的 CSV 现场推出来。

**核心机制八:paper main policy 硬检查**。`validate_source_span_benchmark_artifacts` 里的 `for method, protocol, threshold, pass_recall, hall_recall, hall_f1, accuracy, prefix in ...` 那段,把 6 行主表的期望值(All-pass 全 0、Layer-1-only 0.25/0.4/0.4、TripleChecker fixed@0.50 = 0.807/0.7011/0.8015/0.7223、TripleChecker best HALL-F1 = 0.252/0.9708/0.8998/0.8271、fixed-template 对应两行)全部写死在验证器里。任何一次跑管道结果与这些数不一致,验证器立刻失败。同样地,4 种条件下的 confusion(`fake_span` 3000/3000 全对,object 908/276,subject 1304/1696,predicate 1385/1615)、5 个 supported-loss budget 的 (`pass_false_rejects`, `hall_true_rejects`) 也全部写死。这是"论文里的关键数字全部有 golden ground truth"的实现。

**核心机制九:review packet guardrail**。`validate_source_span_benchmark_artifacts` 结尾还要读 `paper_review_packet.md`,里面必须字面出现 "Supported claim: TripleChecker is a source-span audit and policy diagnostic framework." 和 "Unsupported claim: TripleChecker universally dominates fixed-template NLI or proves production KG-RAG robustness."。这两句是我们对审稿人的"我们知道自己能证明什么、不能证明什么"的书面承诺,验证器强制它们必须在。

### 8.3 `source_span_rtav_heldout.py`——RTAV bank 的谓词/文档留出控制

**问题重述**。RTAV bank 里保存的是每个 predicate 的最优 verbalization 模板(见 Module 2 讲过的 `rtav.py` 与 `best_templates.json`)。审稿人会怀疑:"你们 bank 里预置好的模板,是不是恰好优化到了 benchmark 里出现的那些 predicate?测试集中出现的谓词能被 bank 命中,自然分数高,这是数据泄漏。"

**脚本的解法思路**。不是去"证明没泄漏"(那不可能),而是**准备好留出的切分骨架**,同时诚实标注"当前发布产物里,哪一部分是真正的留出证据"。也就是说:交付一份 `split_manifest`.json,里面预先按 seed=42 把所有 predicate 洗牌后 5 折切,一份类似的按 `doc_id` 切;然后交付一份 `heldout_status`.json,里面用有限的三个状态标签之一标记:`complete`(masked-bank benchmark 得分已备)、`predicate_complete_document_blocked`(谓词留出算过但文档留出算不出)、`blocked_requires_masked_bank_scoring`(全部还没算)。默认发布状态是最后一个——诚实承认我们目前只有 full-bank 分,没有 masked-bank 分。

**具体机制**。`_fold_values` 用固定 seed shuffle 后按 idx % `n_folds` 分桶,保证任何人拿同一 seed 都能复现同一切分。`make_predicate_split` 与 `make_document_split` 各返回 (train, eval) 二元组;第 0 折的 eval 作为"标准 held-out 集"。`build_split_manifest` 把 5 折 predicate 与 5 折 `doc_id` 分组信息、总 predicate 数、总 `doc_id` 数、seed 全都写到一个 JSON 里,内容是完全确定性可复现的骨架。

`predicate_heldout_metric_rows` 是"有条件启用"的:它检查 `scored_with_template_baselines.jsonl` 的每行是否已经带有 masked-bank 场景下的分数字段(`tc_score`、`tc_bank_score`、`fixed_template_nli_score`、`generic_relation_nli_score`——`METHOD_SPECS` 显式定义了 "Masked-bank predicate-heldout" 用 `tc_score` 字段,言下之意是:`tc_score` 由于在 verifier 里当遇到 bank 未命中的 predicate 会 fallback 到 legacy template,这个字段恰好就是"谓词从 bank 剔除后的 TripleChecker 分",可以被当作 masked-bank 场景的自然替代)。如果 scored 文件里已经含有这些分数,就按每折 `eval_predicates` 过滤行,用阈值 0.5 计算 metric bundle 并输出到 `predicate_heldout_metrics.csv`;否则跳过。

**状态机的三档决策**。`build_heldout_report` 里的三段 if-elif-else 才是这个脚本的灵魂:如果 `--masked_bank_scores_available` 命令行 flag 显式传入(意味着我们已经跑了 masked-bank 版本的 benchmark),那么 predicate/document 两条都写 `complete`;如果只有谓词侧的 metrics(因为 `tc_score` 天然对应 masked-bank predicate 场景),但文档侧因为公开的 bank 没有 `doc_id` 溯源(bank 是 predicate → template 映射,不知道每条模板出自哪份文档),文档留出算不出,那么整体状态是 `predicate_complete_document_blocked`,同时 predicate 侧标 `complete`、document 侧标 `blocked_requires_document_bank_provenance`;如果两者都没算,那就全部 `blocked_requires_masked_bank_scoring`。这三档不是模糊描述,而是 `heldout_status`.json 里明确的字符串,后续被 leakage diagnostic 读入做门控。

**markdown 报告结尾的诚实注脚**。当状态是 `blocked_requires_masked_bank_scoring` 时,报告里显式印出 "This does not establish held-out RTAV-bank gains." 和 "Do not claim unseen-schema robustness until masked-bank benchmark scores are generated.";当状态是 `predicate_complete_document_blocked` 时印出 "Document-held-out metrics remain blocked because the released bank lacks document-level provenance." 和 "Do not claim full benchmark-level held-out robustness until document-filtered bank scoring is available."。这两句注脚就是把"我们不能声称的东西"物理写在产物里,后续 leakage diagnostic 会依赖它。

### 8.4 `source_span_rtav_leakage_diagnostic.py`——bank 覆盖 + 泄漏门控

**问题重述**。哪怕 heldout 脚本已经把"我不能声称"写在了报告里,论文里那张主表照样是 full-bank benchmark 的分——万一有人看主表就下结论"TripleChecker 泛化到新 schema 上了"?leakage diagnostic 的目的是**把 full-bank 结果和留出证据放在同一张表里,让读者一眼看到二者不是一回事**。

**表格结构**。产出的 `rtav_leakage_diagnostic.csv` 只有一个 schema,固定 7 列(category / item / value / `reference_method` / `reference_value` / delta / note),分四段拼:
- `bank_coverage` / `benchmark_predicate_coverage`:benchmark 里的 predicate 集合与 bank 里的 predicate 集合求交,输出"多少 benchmark predicate 被 bank 覆盖"、"多少行使用了 bank 模板"、以及总数。这是最直接的泄漏面积估计——比例越高,过拟合风险越大。
- `benchmark_full_bank` 段:调 `benchmark_bank_delta_rows`,在 `fixed@0.50` 和 `best HALL-F1` 两个 protocol 下,拿 "TripleChecker-bank"(全 bank)的 HALL F1 减去 "TripleChecker"(no-bank/legacy fallback)和 "Fixed-template NLI" 的 HALL F1,注 `Full-bank source-span benchmark comparison; not a held-out-bank estimate.`。这行是关键——note 里明说"这不是留出估计",防止读者拿 delta 当泛化证据。同一段还输出 `hall_average_precision` 的 delta,同样带注脚。
- `human_predicate_heldout` 段:从 200 条人工集的 multiseed predicate-hiding 实验(`rtav_unseen_prepatch_hallucination_positive/multiseed_summary.json`)读入 unseen bucket 的 `mean_delta_f1`、正 delta 种子数与总种子数,输出到表。这一段是**真正的**留出证据(200 条上的),但注意规模小、置信度低,note 里精确写"200-row human-set predicate hiding"。
- `leakage_gate` 段:调 `leakage_gate_rows(has_benchmark_heldout)`。命令行 flag `--benchmark_heldout_scores` 传入非空路径则视为"benchmark 级留出分已有",value 写 present,note 说"可用";否则 value 写 `missing`,note 明说 "No benchmark-level predicate/document held-out bank scores are present; do not claim unseen-schema robustness from full-bank results."。

**markdown 报告的双段结构**。`write_report` 首段固定印:"This report separates full-bank benchmark comparisons from held-out evidence. Full-bank rows are useful tradeoff diagnostics, but they do not establish unseen-schema generalization." 然后判断表里 `leakage_gate` 那行 value 是否为 missing,若是,则再插一段 "No benchmark-level held-out bank scores are present. The current benchmark can cite full-bank vs no-bank/fixed-template tradeoffs only."。最后才是 diagnostic 表。这个模板保证——**无论 benchmark 级留出分有没有算——这份报告都会带着正确的边界声明**;算了就说"present",没算就明确说"缺,不许声称"。

**与 validator 的联动**。回到 `validate_accept_claims.py` 里的 `validate_source_span_rtav_leakage_artifacts`,虽然我这次只读到了它的头部(它出现在 3475 行的调用列表里,函数体在文件后半段没读到),但从命名 + 与 heldout 联动的模式看,它做的事情基本可以确定:检查 csv 里必须有 `bank_coverage`、`benchmark_full_bank`、`human_predicate_heldout`、`leakage_gate` 四段的行、检查 markdown 里必须字面出现"held-out"边界声明的关键句、验证 delta 值可由行级重算。同一逻辑套 heldout 的 `validate_source_span_rtav_heldout_artifacts`,应验证 `heldout_status.json` 里的 `benchmark_level_heldout_status` 字段与 markdown 里印出的字符串一致。

### 8.5 三个脚本合起来构成的防线

把 8.2 / 8.3 / 8.4 拼在一起,防线是这样运作的:

1. **RTAV 侧**:heldout 脚本把切分骨架写死并诚实标状态,leakage diagnostic 把 bank 覆盖率、full-bank vs no-bank delta、200 条人工留出 delta、benchmark 级留出门控四段并列,末尾报告里直接印 "not held-out evidence"。
2. **论文侧**:paper.md 只允许说这套框架能做什么(source-span audit + policy diagnostic),不许说 "held-out robustness" 或 "production KG-RAG";validator 里的 `validate_paper_overclaim_guardrails` 用正则黑名单强制。
3. **发布侧**:`claims_manifest`.csv 列出 30 条必答 claim,每一条都指到 `results/` 里的具体文件;validator 加载每个文件后行级重算所有报出的数,和 markdown 里字面出现的数字比对;blind sheet 表头/值/顺序全部机械检查;agent-adjudicated 溯源必须显式带 "not human-labeled" 声明。

审稿人最可能问的三个尖锐问题及答法:
- **"RTAV bank 是否在测试集上过拟合?"** → 展示 leakage diagnostic 的 `bank_coverage` 行(覆盖率数字)、`benchmark_full_bank` delta 行(不作为泛化证据的 delta)、200 条人工 predicate-hiding 的正 delta 种子占比(真正的 unseen 证据,但样本量诚实标注);同时展示 `heldout_status`.json 是 `blocked_requires_masked_bank_scoring`,说明"我们没声称 benchmark 级留出,这里有清晰的边界。"
- **"benchmark 里 3000 条 `fake_span` 全对,是不是 leak 了 source span 到验证器里?"** → Layer-1 是纯字符串匹配,不需要模型知识,`fake_span` 全对是 Layer 1 的定义决定的(不是任何学习到的东西);同时 validator 里 `source-span fake-span condition` 期望值就是 `hall_recall`=1.0、tn=3000、fp=0,是这套 design-by-construction 的直接体现。
- **"自然噪声的 383 条标签怎么保证可信?"** → 这是 `label_source`=agent-adjudicated,我们没假装是 human;`expanded_natural_double_annotation` 的 blind sheet 由 validator 强制表头无 leak 字段、value 无 leak pattern、行序 id 一致;`agent_adjudication_provenance`.json 与其 markdown 必须字面写 "not human-labeled";paper.md 里 "human-labeled natural-noise" 之类的措辞会被 overclaim guardrail 直接毙掉。

### 8.6 面试可能被追问的实现细节 (自查提示,内容不入页)

- 为什么用 seed=42 shuffle 而不是分层切?→ predicate 数量不大(几十到一百多量级),分层的收益小于流程简单性;真正的守夜狗是"validator 检查折切完全可复现"。
- 为什么 `masked_bank_scores_available` 是个命令行 flag 而不是自动检测?→ 因为"我们已经跑了 masked-bank 版本"是一个人为决定的事件,不能靠猜文件存在;明示比隐式安全。
- 为什么 leakage diagnostic 里 delta 的分子分母都是 full-bank 表?→ 是因为这段本来就叫 `benchmark_full_bank`,记录的是"不同方法在同一 full-bank benchmark 上的差异",不是留出估计;它的价值是"tradeoff diagnostic"而非"泛化证明",note 直白写出。
- 为什么 validator 里所有关键 metric 都要独立重算而不复读?→ 因为复读只能检测"打字错误",不能检测"故意/无意的选择性丢行、临时改判决、metric 定义漂移"。行级重算才能真正兜住。
- overclaim guardrail 有假阳性风险吗?→ 正则是全文规范化后匹配窗口内 120 个字符的组合,不做单词级;但每条模式都写得非常特定(比如 "natural-noise ... human-labeled evidence" 里 "evidence" 是词根),命中意味着我们真的写了这个组合。

---

**确认后进模块 9**:回到我一开始给的 §2 计划,还有两块次要素材可以选:一是 `rebuttal_exp/` 里的 e1/e2/e3/e4 四组回应实验(如果这些脚本还在活跃使用,是审稿人后续追问最直接的抓手);二是 `tests/` 目录里的合约/回归测试(可以反向证明我们哪些 invariants 是"值得写测试的核心不变量")。

你选哪一路?或者直接跳过 §2 剩余脚本进 §3 关键设计决策推理链(deltas 会小一些,但更接近面试主线)?

题目保留,内容准备入页。

## 模块 9 · Rebuttal 实验组 (`rebuttal_exp/`)

这一层是回应审稿意见的"应急台"——四组新实验(E1–E4)、四条元级复核(V1–V4)、四条独立复现(R1–R4)、一份最终数字对账(`FINAL_NUMBER_CROSSCHECK`)。这一层里最能被面试官"抓漏"的地方,不是这些实验的正面结论,而是**它们暴露出的原论文 bug 与措辞问题**——我们把这些问题公开、记录、修正的姿态本身,就是这个工作的可信度来源。

### 9.1 整体骨架:`manifest.json` 是"这批实验完成状态"的合约

`rebuttal_exp/manifest.json` 是这一整层的钥匙。它记录:`status=complete`,四组实验 E1/E2/E3/E4 全部 `completed`(`blocked=[]`),`sealed_test_accessed=false`(硬性声明:这些回应实验没有触碰 sealed test 集合,是复用现有 benchmark.jsonl 的),以及**每一份关键产物的 SHA256 摘要**。任何后续修改产物都会导致摘要变化,配合验证器就是可复现性的物理证据。这份 manifest 本身就是"我们跑了什么、结果哈希是多少"的公开凭证。

### 9.2 E1:LLM-as-judge 成本/精度/延迟对比 (DeepSeek V4 Flash vs TripleChecker)

**回应的审稿问题**:"你为什么不直接用 LLM 打分?比你这套 RTAV+NLI 简单多了。"

**实验设计**。从 15000 行 benchmark 里按分层抽样 3000 行(每个 condition 600 行,5 个 condition:`fake_span` / `gold_positive` / `object_replacement` / `subject_replacement` / `predicate_mismatch`),温度设为 0,`sample_3000.jsonl` 是种子固定的抽样;然后跑两条 DeepSeek pipeline:span-only(只把 `source_span` 给判官)与 `full_document`(把整篇文档给判官)。同时跑 TripleChecker 本地,记录墙钟时长。为验证判官稳定性,在其中 300 行上跑三次独立请求,记录一致性(`consistency.csv`)。

**关键数字**(来自 `e1/results.csv` + `e1/conclusion.md`):
- DeepSeek SU-F1(即 unsupported-positive F1,也就是我们论文里报的口径):span-only $=0.917$,full-document $=0.878$;TripleChecker $=0.809$。
- DeepSeek 的 PASS recall(supported 保留率)只有 $0.368$ / $0.337$——它虽然 SU-F1 高,但**代价是把大量真正被支持的三元组也误杀了**。
- DeepSeek 对不支持的行拒绝率 $0.980$ / $0.912$;TripleChecker 是 $0.612$ / $0.503$。
- 成本:DeepSeek $\$0.0199$ / $\$0.0216$ 每 1000 行;TripleChecker $\$0$,本地 $10.586\text{s}$ 每 1000 行。全文档模式下 $891.575\text{s} / 10.586\text{s} \approx 84$ 倍延迟差。
- 300 行 × 3 次一致性:$1.000$(DeepSeek 在温度 0 下确实稳定)。

**结论的措辞**:不是"TripleChecker 击败 DeepSeek",而是**"accuracy–retention–cost trade-off"**——DeepSeek SU-F1 更高但保留率崩溃,且有非零成本;TripleChecker 保留率更好、免费、快 85 倍。同时特别标注 `all-reject SU-F1 anchor` $= 0.888$(即"什么都拒绝"这个平凡 baseline 已经能拿到 $0.888$),所以 DeepSeek 的 $0.917$ 是被"更严的拒绝倾向"推高的,PASS recall 必须并列展示。**这句 anchor 是 defense 的关键**:它把 SU-F1 单指标"看起来很高"的错觉直接击穿。

**`defensive_rejection`.csv**:切分开各种 negative condition,记录三种方法在每种造假上的拒绝率。审稿人若说"你们的分数是靠某一种造假堆出来的",这张表逐格反驳。

### 9.3 E2:三个 NLI 骨干的一致性 (RTAV bank 稳不稳)

**回应的审稿问题**:"你们的 RTAV bank 是不是只在 Erlangshen 110M 这一个骨干上有效?"

**实验设计**。三个骨干:Erlangshen-Roberta 110M(主实验)、mDeBERTa-330M、Erlangshen-Roberta 330M。对每个骨干独立校准阈值(不共享 threshold):3030 行 calibration(按 `doc_id` 分组避免泄漏),11970 行 evaluation。calibration/evaluation 精确 3030+11970=15000 且按文档分组,禁止同一文档跨集。得到的阈值分别是 $0.75$ / $0.80$ / $0.85$。

**关键数字**(来自 `e2/results.csv`):
- 三个骨干 SU-F1:$0.8535$ / $0.8879$ / $0.8248$,range $=0.063$。
- 论文声称的 "backbone invariance" 标准是 $|\Delta| \le 0.02$——$0.063$ 显然超标,**不支持完全 backbone 不变性**。
- 但拆到 direction-sensitive 关系子集,三个骨干上的 RTAV bank 增益 $+0.0700 / +0.0857 / +0.0466$,全部为正,幅度 $4.7$–$8.6$ 分。
- 整体 bank-minus-fixed delta:$+0.010$ / $+0.023$ / **$-0.015$**——330M 上整体 delta 为负,不能声称整体一致优势。
- 负条件排序(即三类 hallucination 拒绝率排序):110M 和 mDeBERTa 一致,330M 换了 predicate mismatch 与 subject replacement 的次序。

**结论的措辞**:承认 backbone invariance 不成立,只声称 direction-sensitive 上的 RTAV 增益 backbone-robust。**这一诚实收窄是 rebuttal 的关键**——原论文如果不修正,直接说"跨 backbone 一致",审稿人只要跑 330M 就能反例。E2 提前把这句话砍到能守住的范围。

`relation_instability.csv` 进一步按 predicate 数分档展示 SU-F1 range 与骨干组合,粒度到 60 / 56 / 160 / 124 predicate 的分层。

### 9.4 E3:模糊 vs 精确匹配 (Layer 1 的形式化选择)

**回应的审稿问题**:"你们 Layer 1 用严格子串匹配,是不是太脆了?换个 fuzzy match 会不会更好?"

**实验设计**。在 3000 `fake_span` + 3000 `gold_positive` 上,跑四种匹配策略:exact substring、Jaccard 阈值 $0.80/0.90/0.95$、rapidfuzz 的 `partial_ratio` 阈值 $0.80/0.90$、以及 `token_set_ratio` 系列。用 SU-F1、authentic-span false-kill rate、fake-span detection rate 三个指标评价。

**关键数字**(来自 `e3/results.csv` + `e3/conclusion.md`):
- Exact match:`fake_span` detection $=1.000$,authentic false-kill $=0.000$,SU-F1 $=0.914$($0.9137$ 未四舍五入)。
- 最好的 fuzzy:`partial_ratio@0.80`,SU-F1 $=0.914$,`fake_span` detection $=0.998$(错放 6 条),authentic false-kill $=0.000$。**跟 exact 打平但风险稍高**。
- Jaccard@0.9:false-kill rate $18.1\%$(543/3000),SU-F1 掉到 $0.854$。
- Jaccard@0.8:false-kill 更严重。

**结论**:exact matching 是 authenticity contract 的**必需契约**——它把 Layer 1 的"是否复制自原文"这个 property 变成不需要模型的形式验证。任何 fuzzy 阈值都会引入 false-kill 或 false-admit,而 exact 在这个 benchmark 上是 dominant strategy。这一段是 Layer 1 存在合理性的直接证据,防止审稿人质疑"你们 Layer 1 只是 heuristic"。

### 9.5 E4:方向敏感子集 + 路由分歧 (Bank-first vs Dictionary-first)

**回应的审稿问题**:"你们说 RTAV 能提升 direction-sensitive 关系(如 subject/object 对调的),但整体分数其实来自哪一部分?"

**实验设计**。把 benchmark 里的谓词按"是否 direction-sensitive"打标签(如"父母/子女"就是方向敏感,"位于"通常方向对称),然后分子集算 TripleChecker vs Fixed-template NLI 的 delta。同时,`e4/generate_manifest.py` 与 `e4/analyze.py` 检查**运行时实际路由**——每条 benchmark 行的 verbalization 到底走的是 bank / dictionary / generic fallback 哪条路径。

**关键数字**(来自 `e4/direction_results.csv` + `e4/route_results.csv`):
- direction-sensitive 子集 SU-F1:TripleChecker $0.673$ vs Fixed-template $0.573$,delta $+0.100$。
- 非 direction-sensitive 子集 delta $+0.119$——**比 direction-sensitive 更大**。
- 也就是说,"我们的增益集中在 direction-sensitive"这个原论文暗示是**不成立**的。E4-a 只支持"direction-sensitive 上有 sizable gain",不支持"gain 集中于 direction-sensitive"。
- direction-sensitive 上 TripleChecker 多拒绝了 609 条 unsupported 行(rejection 从 $0.430$ 涨到 $0.542$,即 $2939-2330=609$)。
- **E4-b 路由分歧**:实际代码里 128 个 benchmark 谓词全部走 offline bank,没有一条走 dictionary 或 generic fallback。但论文里描述是"dictionary 优先,miss 后走 bank"——**代码是 bank-first,论文是 dictionary-first,严重不一致**。

E4-b 这个发现是整个 rebuttal 里最尴尬的一处:paper 的算法描述和实际 released 实现相反。

### 9.6 V1–V4 元级复核 (`VERIFICATION.md` + v1/v2/v4 表)

这四条 V 是"我们跑完 E1–E4 之后,再自己审查一遍"的元级层,把"哪些数字可以用于 rebuttal、哪些不能"逐条落到纸面。

**V1:$0.545$ vs $0.804$ 差距是 metric-label bug 而非模型退化**。E1 最初报的 TripleChecker 是 $0.545$,论文报的是 $0.804$。审稿人若拿这两个数字对比会认为"你们方法在新抽样上退化了 26 个点"。V1 揭示:$0.545$ 是 **PASS-F1**(supported-positive F1,即"我们支持哪些应支持的"),$0.804$ 是 **SU-F1**(unsupported-positive F1,即"我们拒绝哪些应拒绝的")。这两个 F1 在类别不平衡下天差地别。修正 label 后同一批 E1 predictions 跑出来 SU-F1 $=0.8091$,与论文 $0.8040$ 完全一致;100 行重叠验证 score/Layer-1/label 差异 $0/100$,最大 score 差 $0.0$。表现在 `v1_factor_decomposition.csv` 与 `v1_seed_sensitivity.csv`(三次种子 SU-F1 落在 $0.8022$–$0.8091$)。

同一 label bug 也污染了 DeepSeek 的原始报告($0.509 / 0.399$ 其实是 PASS-F1),以及 E2 的原始报告($0.565 / 0.633 / 0.555$ 也是 PASS-F1)。V1 把这些错误标签一次性挂在"禁用清单"上。**这是这份 rebuttal 姿态最硬核的一段**——审稿人本可以拿"你们内部报告都自相矛盾"打死这篇文章,V1 主动认了、修正了、并且给出行级证据。

**V2:只有 direction-sensitive 增益是 backbone-robust**。基于 E2,V2 明确划出可用/不可用边界:direction-sensitive 上三 backbone 一致为正($+0.0700$ / $+0.0857$ / $+0.0466$)——**可用**;整体 bank-minus-fixed delta 三 backbone 不一致(330M 为负)——**不可用**;负条件排序 330M 不一致——**不可用**。rebuttal 里只能写"direction-sensitive 上 backbone-robust",不能写"整体 backbone-invariant"。

**V3:runtime 是 bank-first 而非 paper 描述的 dictionary-first**。这是 E4-b 的正式记录。paper 里"dictionary first, miss to bank"的措辞与 `RTAVModule.get_template()` 的实际行为(先查 offline bank,miss 才 fallback 到 legacy dictionary)相反。released bank 覆盖全部 128 predicates 与 15000/15000 rows,所以 dictionary route 事实上空转。修订措辞:paper 里的 $59.1\%$ 是 dictionary 资源本身的 predicate 覆盖率,不是 runtime route share。**这是论文↔代码不一致点的 canonical 例子**,进 §5 时会正式列。

**V4:boundary cascade 支持结论**。基于 E1 的 3000 行,定义 boundary interval $[0.4, 0.6]$——TripleChecker 分数落在这里的行占 $191/3000 = 6.37\%$。这些行上 TripleChecker 准确率 $0.571$、DeepSeek 准确率 $0.827$;paired 比较 discordant wins $69$ vs $20$,双侧 exact binomial $p = 1.777 \times 10^{-7}$——DeepSeek 在 boundary 上显著更好。把这 $6.37\%$ 的行用 DeepSeek 替换,SU-F1 从 $0.8091$ 涨到 $0.8237$($+1.46$),PASS-F1 从 $0.5448$ 涨到 $0.5541$。这个 selective cascade 只增加 $6.37\%$ 的 API call 成本换来 $+1.46$ 分——**是我们提供给未来工作的一个 practical extension**,而不是主论文的一部分。

### 9.7 R1–R4 独立复现 (`REVERIFICATION.md` + `reverification_r1`/r2/r3 CSV)

V 层是我们自己的复核。R 层是"用完全独立的代码重跑一次"——`reverification.py` 是从零写的解析 + 混淆矩阵 + AUROC 代码,不 import 主 pipeline 的任何函数。

- **R1:DeepSeek 指标**——独立解析 DeepSeek 原始 response、独立 confusion matrix,SU-F1 $0.9170 / 0.8781$ 差 $0$。all-reject anchor $=0.888$ 也独立重算证实。
- **R2:三 backbone**——独立重算得 $0.8535 / 0.8879 / 0.8248$、330M overall delta $-0.01518$、direction-sensitive $+0.0700 / +0.0857 / +0.0466$,与 E2 完全一致。冻结的 20 行 disagreement audit 里,部分 bank verbalization 语义拗口或颠倒了主宾角色——**这确实是模板质量问题,而不是文件格式 bug**,330M 的负 delta 是真限制不是错报。
- **R3:自然噪声**——383 行 adjudicated view 上,TripleChecker SU-F1 $=0.6471$,Fixed-template NLI $=0.6608$;document-clustered 95% CI 分别是 $[0.5636, 0.7204]$ 与 $[0.5827, 0.7278]$,**大幅重叠**。备用措辞:"在这份 383 行诊断上,TripleChecker 和最强 scalar baseline 的 CI 重叠,观测到的点差在采样不确定性范围内。"——这句话是自然噪声实验能守住的**最诚实**边界。
- **R4:fuzzy matching**——独立重算把原 E3 报告里 $0.896$ 的标签也修正了(那是 PASS-F1,SU-F1 应为 $0.9137$)。Jaccard@0.9 独立复算 false-kill $543/3000 = 18.1\%$,SU-F1 $0.8542$,与修正后 E3 一致。

R 层的价值:不是"验证 V 层没错",而是"任何拿到我们代码/数据的第三方,可以完全绕开我们的主 pipeline 得到同样结论"。这是 Module 8 讲的 `validate_accept_claims.py` 之外的第二层复现保障。

### 9.8 `FINAL_NUMBER_CROSSCHECK`.md (最终对账)

最后一环。它扫描 `REBUTTAL_DRAFT_DEEPSEEK_ONLY.md`、`VERIFICATION.md`、`SUMMARY.md` 三份 rebuttal-facing 文档里出现的**每一个实验数字**,对照 `FINAL RUBRIC`(注册的最终数字表)或 `e{i}/*.csv` 逐条比对,输出一张表:每一行是"文档位置 → 声称数字 → 注册数字 → 结果",全部标 `Consistent`。

关键条目摘录(不完全列表):
- direction-sensitive $0.573 \to 0.673$($+0.100$),非 direction-sensitive delta $+0.119$——对齐 `e4/direction_results.csv`。
- $128$ predicates, $15000/15000$ rows, dictionary resource $59.1\%$——对齐 `verification_config` 与 V3 registry。
- DeepSeek span/full SU-F1 $0.917 / 0.878$,PASS-F1 $0.509 / 0.399$——对齐 `e1/results.csv`。**永远按 span/full 顺序,不能颠倒**;$0.878/0.917$ 就是错误顺序。
- 三 backbone SU-F1 $0.853 / 0.888 / 0.825$,range $0.063$,criterion $0.02$——对齐 `e2/results.csv`。
- E3 exact-match SU-F1 $0.914$($0.9137$ 未四舍五入);$0.896$ 只作为"过时的 PASS-F1 标签"出现,不再作为 SU-F1 使用。
- 禁用清单:E1 $0.545$、DeepSeek $0.509 / 0.399$、E2 $0.565 / 0.633 / 0.555$——注册表明这些都是 PASS-F1,任何 rebuttal 文档里以 SU-F1 名义使用视为错误。

结论:**"No numerical edit is required before submission."**——提交前全部数字对齐,manifest.json 里 SHA256 摘要都对得上。

### 9.9 面试可能被追问的点 (自查提示,内容不入页)

- 为什么最初 E1 会用 PASS-F1 label 报错?→ E1 抽样代码复用了自然噪声 pipeline 的 summarizer,那里默认输出 PASS-positive metrics;主 pipeline 的 metrics 出的是 SU-positive(unsupported-positive)。两个 pipeline 用了同一个函数名但语义相反,是内部约定漂移。修正是把 metric bundle 输出统一到"两个视角都报"(见 Module 7 的 `_metric_row_from_predictions`)。
- 为什么承认 backbone invariance 不成立?→ 因为承认小限制比"被审稿人一句话推翻整篇"代价小得多。这是从"universal 声称"退到"conditional 声称"的典型学术姿态。
- 为什么 E4-b 的路由分歧不修 paper 直接改代码?→ 修代码意味着实际实验就变了,所有已跑的数字失效。修 paper 描述来匹配已经跑过的代码,是 rebuttal 阶段唯一可行的选项。这也是"paper 的描述必须以 code 的实际行为为准,不是反过来"这条硬约束的现实体现。
- boundary cascade 为什么放 rebuttal 而不是主论文?→ 因为它引入了 DeepSeek 依赖,与主 paper "API-free" 的定位冲突;放 rebuttal 作为"可扩展方向"更符合 claim scope。
- Jaccard 阈值为什么会有 $18\%$ false-kill?→ Jaccard 对短 span 尤其不友好:span 越短,一个字符的偏差就会显著拉低 Jaccard。中文 `source_span` 通常 $10$–$30$ 字,$0.9$ 阈值相当于最多允许 $1$–$3$ 字符差异,一个标点/单字增删就会漏掉。

---

**确认后进 §3:关键设计决策推理链**。这是 §2 完结之后最有面试价值的一部分——把 Module 1–9 里出现过的每一个"为什么这样,而不是那样"整理成一张推理链表。备选:如果你更想先补 `tests/` 目录(Module 10),这一小块可以先做完再入 §3。

题目保留。

## §3 关键设计决策推理链

这一节把 Module 1–9 里出现过的每一个"为什么这样,不是那样"提炼成推理链。面试与套磁场景里,能被追问到哪一条,这一节就给到哪一条的三件套:**我们选了什么、代替方案是什么、为什么这样选**——外加"什么条件会翻转这个选择"。

### 3.1 架构层决策

**D1 · 双层结构 (Layer 1 精确子串 + Layer 2 中文 NLI)**——不是端到端 NLI,不是端到端 LLM。原因:Layer 1 把"`source_span` 是否真的来自文档"这件事变成 design-by-construction 的形式验证,不依赖任何学习到的能力,`fake_span` 上必得 $100\%$ 拒绝;把这一层从 Layer 2 剥离出来后,NLI 只需要判断"span 是否蕴含三元组",不需要同时兼顾"span 是否真存在"。也让 SAR × EPR 的分数分解有实实在在的分子对应。**翻转条件**:如果目标场景允许 span 来自 paraphrase 而非严格摘抄(比如允许 extractor 自由改写),Layer 1 就要放宽到 fuzzy——但 E3 的 $18\%$ false-kill 结果说明这会得不偿失。

**D2 · Layer 2 用中文 NLI 而非 LLM prompt**——不是让 GPT/DeepSeek 直接判"这条三元组是否被支持"。原因:NLI 是 fixed-size deterministic 模型,温度 0 下完全可复现;LLM 判官虽然精度高,但成本 + 延迟 + provider drift 三重成本(见 E1:$85\times$ 延迟差 + $\$0.02$/千条 vs $\$0$)。**翻转条件**:E1 的 V4 boundary cascade 已经给出了 hybrid 路线——用 NLI 做主判决,在 $[0.4, 0.6]$ 边界带($6.37\%$ 的行)上升级到 LLM 判官,$+1.46$ SU-F1 增益换 $6.37\%$ API 成本。这条路线放 rebuttal 而不进主论文,是因为主论文的 "API-free" 定位不能自破。

**D3 · RTAV bank 是 offline precomputed 而非 runtime 生成**——不是每条 triple 现场生成 verbalization。原因:runtime 生成引入 LLM 依赖(违背 API-free)、生成质量方差大、也不可复现。offline bank 用一次性抽取的最佳模板 $\times$ predicate 表,查表 $O(1)$。**翻转条件**:如果 predicate 集合是开放世界(比如中文百科生成的关系词),bank 不可能预生成完全,就要退回运行时 LLM——这时 API-free 定位本身要放弃。

**D4 · RTAV 是 bank-first 而不是 dictionary-first**——这是 V3 里挂出的**代码 vs 论文不一致点**。`RTAVModule.get_template()` 优先查 offline bank(命中率 $128/128 = 100\%$),miss 才 fallback 到 legacy coarse-type dictionary,再 miss 才 generic template。paper 原描述"dictionary 优先,miss 到 bank"与实现相反。**为什么代码这样写**:因为 bank 是我们花成本做出来的最优模板集,理论上比 dictionary 更好,自然应该优先;但 paper 阶段作者(=我)把心智模型写反了。**修正做法**:改 paper 描述以匹配代码,不改代码——因为改代码就等于所有已跑的 benchmark 结果失效。这条决策的教训是**"paper 描述必须以 code 实际行为为准,不是反过来"**。

**D5 · 滑窗推理 `max_length`=256 / stride=128 / max aggregation**——不是单次全文档 NLI。原因:中文 NLI 模型的位置嵌入限制 512,加上 hypothesis 后能给 premise 的窗口约 $256$;stride $128$ 保证任何相邻窗口有 $50\%$ overlap,不会漏掉横跨窗口的语义单元;取窗口最大值作为分数是"任意一段能蕴含就算蕴含"的直觉。**翻转条件**:换更长上下文模型(如 Longformer-中文)时,滑窗可以退化为单次;但主实验里 Erlangshen-110M 是短模型,滑窗是必需。

### 3.2 分数与阈值层决策

**D6 · SAR × EPR 分数分解而非单标量**——不是只报 EPR 一个数。原因:SAR($\in \{0,1\}$)对应 Layer 1 是否通过、EPR($\in [0,1]$)对应 Layer 2 蕴含概率;两者相乘作为最终分数,让"哪一层拒绝的这条三元组"永远可追溯。也让 Layer-1-only baseline 天然成为 SAR-only 的消融($\text{EPR} \equiv 1$)。**翻转条件**:如果 Layer 1 变成软判决(如引入 span 相似度),SAR 就不再是 $\{0,1\}$,分解含义会变。

**D7 · 固定阈值 $\delta = 0.5$ 作为论文 protocol,同时事后跑 policy 分析**——不是学一个 optimal threshold 作为主结果。原因:$\delta=0.5$ 是 backend NLI 的天然中点,任何 downstream 用户无需校准就能直接用;论文承诺的是"这套框架在 $\delta=0.5$ 时能做什么",而不是"我们能调到最好"。同时 `policy_rows` 会跑三档:$\text{fixed@0.50}$、$\text{best HALL-F1}$、$\text{high-retention}$(PASS recall $\ge 0.95$ 前提下 HALL recall 最大);还跑 supported-loss budget 系列(误杀 supported 不超过 $25/50/100/250/500$ 时能拒多少 unsupported)。这些放在事后 policy report 里,不改主结果。**翻转条件**:如果 backend 从 NLI 换到别的分布(如 LLM logits 或 embedding similarity),$0.5$ 就不再是自然中点,主 protocol 就要换。

**D8 · Layer-1-only baseline 作为 SAR-only 消融**——不是无 baseline。原因:它是"如果我们只保留 Layer 1、扔掉 NLI"的直接对照,SU-F1 $0.4$/accuracy $0.4$/HALL recall $0.25$——比 all-pass 的 $0.0$ 强,但比完整 TripleChecker 的 $0.80$/$0.7223$/$0.7011$ 差一大截,把 Layer 2 的边际贡献量化。**翻转条件**:如果发现 Layer-1-only 就足够接近完整方法,整个 Layer 2 存在的意义要重新论证。

**D9 · all-reject SU-F1 anchor $= 0.888$**——不是省略这个平凡 baseline。原因:E1 里 DeepSeek span-only SU-F1 $=0.917$,看起来很高,但 all-reject 就能拿 $0.888$——差距只有 $0.029$。这个 anchor 一挂出来,读者立刻知道"DeepSeek 是靠严格拒绝倾向堆出来的,不是靠更聪明的判断",PASS recall 崩到 $0.368$ 就是代价。**翻转条件**:如果 test 集是 balanced(SU-negative 与 SU-positive 各半),all-reject anchor 会掉到 $\approx 0.67$,anchor 的诊断价值降低——但我们的 benchmark 是 $12000 : 3000 = 4 : 1$ 不平衡,anchor 是关键 sanity check。

### 3.3 Benchmark 层决策

**D10 · 15000 行 controlled source-span benchmark(4 negative conditions)**——不是从自然文档里挑错误。原因:自然错误的分布未知,标注成本高,且**每一种错误的相对频率会天然干扰指标解读**;controlled 版本每个 condition 精确 $3000$ 行($\text{fake\_span}$、$\text{object\_replacement}$、$\text{subject\_replacement}$、$\text{predicate\_mismatch}$,加上 $3000$ 条 `gold_positive`)保证各类错误的 statistical power 相同,得到的 confusion matrix 分格严整。**翻转条件**:如果目标是"在真实分布下能拒多少错误",就得跑 natural noise pipeline(见 D11);controlled 是**能力上限估计**,natural 是**真实场景估计**。

**D11 · Natural noise pilot 用本地 Qwen2.5-3B 而非 API**——不是让 GPT-4o 生成三元组。原因:本地推理免费、可无限重复、无外部 dependency;$3\text{B}$ 参数量够小(可以在实验机上跑),够真(是一个真实会被部署的模型)。第一版 59 条(18 文档),扩展到 383 条(160 文档 = 80 DuIE + 80 CMeIE)。**翻转条件**:如果需要评估更强 extractor(如 $32\text{B}$+ 或 GPT-4)的 hallucination 特征,就不得不接 API,natural pipeline 已经设计好 `build_requests` / `build_annotations` 分离,只要有外部 runner 就能扩展。

**D12 · 三个数据源 (DuIE / CMeIE / FinRE)**——不是单一域。原因:通用领域(DuIE)、医学(CMeIE)、金融(FinRE)覆盖 predicate 分布差异极大的三个域;RTAV bank 里 $128$ 个 predicate 就来自这三源合集。**翻转条件**:审稿人若说"没测过化学/法律",答:框架不依赖领域,bank 可扩展;但主 paper 的 claim scope 严格限定在这三源。

**D13 · `Fake_span` 是"看似合理但不在文档里"而不是"随机字符"**——不是伪造无意义 span。原因:随机字符 Layer 1 也能拒,test 意义低;`fake_span` 是从其他文档抽取的真实 span,读起来通顺,只有精确检索时才发现"不在这篇文档里"——这才是**真正会骗过 Layer 2 但被 Layer 1 拦住**的场景。`fake_span` 在 benchmark 上 confusion matrix 全对角化($3000/3000$ 拒绝,$0/3000$ 误杀)是这个 construction 的直接体现,不是模型学习到的能力。

### 3.4 评价方法决策

**D14 · Bootstrap CI 按 $(\text{dataset}, \text{doc\_id}, \text{triple\_id})$ 聚类**——不是行级 iid。原因:同一文档里的多条三元组共享上下文噪声(比如某文档特别难),独立采样会低估不确定性。聚类采样是 Efron-Tibshirani 标准做法,主 benchmark 是 $(\text{dataset}, \text{doc\_id}, \text{triple\_id})$,natural noise 是 `doc_id`。**翻转条件**:如果每个文档只有 $1$ 条三元组,聚类退化为 iid,聚类采样与行级采样等价;但我们的 benchmark 是多 triple/doc,聚类是必需。

**D15 · Paired bootstrap 求方法间 delta CI**——不是各自算 CI 再目视比较。原因:两方法在同一批 test 行上评估,行间相关性巨大,paired bootstrap 才能得到无偏 delta 分布;`source_span_paper_tables.py` 里 `bootstrap_phase3_rows` 的单循环 batch 版本就是保证所有 method $\times$ protocol $\times$ pair 用**同一批 resampled indices**,paired 语义严格。**翻转条件**:如果两方法用的是完全不同的 test 集(比如 A 用中文、B 用英文),paired 不成立,要退回独立 CI + McNemar 或类似检验。

**D16 · $10^3$ bootstrap 迭代**——不是 $10^4$ 或 $10^5$。原因:$10^3$ 在 CI 边界宽度上的方差已经可以忽略($\text{CI}$ 宽度的 MC 误差约 $1/\sqrt{B}$);更多迭代对结论不敏感,而 $10^3 \times 15000$ 行的 batch 已经是显著的计算量。**翻转条件**:如果 CI 极端窄(比如 $[0.799, 0.800]$),需要更多迭代抗采样噪声——但我们的 CI 通常宽 $0.05$ 以上,$10^3$ 足够。

**D17 · McNemar 精确二项检验**——不是 chi-square 近似。原因:样本量哪怕大,discordant pair 数可能小(V4 里 $69 + 20 = 89$),chi-square 近似会失真;精确二项是 exact,无论 discordant 数多少都严谨。V4 的 $p = 1.777 \times 10^{-7}$ 就是精确算出。**翻转条件**:如果 discordant 数极大($> 10^5$),精确二项计算量爆炸,才转 chi-square。

### 3.5 标签与合规决策

**D18 · Agent-adjudicated 而不是 human-adjudicated**——不是找两个人类标注员。原因:我们没有人类标注员资源,double annotation 是用两个独立配置的 agent 走 blind sheet 流程,adjudicator 也是 agent。这是**已知薄弱环节**(见 §6 会重点讲)——但我们的姿态是全程标注 `label_source=agent-adjudicated`,`schema_note` 里必须字面出现 "not human-labeled",paper 里禁用 "human-labeled natural-noise" 之类措辞(validator 里 overclaim guardrail regex 强制)。**翻转条件**:招到两个中文标注员并做过 IAA training 后,`label_source` 切到 human,agent 版本退化为参照。

**D19 · Blind sheet 严格白名单/黑名单强制**——不是让 agent 自由看所有字段。原因:agent 只要看到 `tc_score`、`tc_label` 之一,就会被引导跟随模型判决,失去独立性;`validate_blind_annotation_sheets` 从字段名、字段值 pattern、行序 id 三重锁死;`value_leak_fields` + `value_leak_patterns` 甚至扫描每个字符串内的关键字。**翻转条件**:如果换成人类标注员,blind 更严——一般也不用告诉标注员用了什么模型;所以这条 design 换 human 也直接沿用。

**D20 · 行级 CSV 公开发布**——不是只发聚合数字。原因:审稿人和第三方要能自查每一条 policy row 的 $\text{tp}/\text{fp}/\text{fn}/\text{tn}$,只有行级数据在手,`validate_accept_claims.py` 才能行级重算所有报出的数字。这也是**"我们不怕被查"**的技术兑现。**翻转条件**:如果数据涉及隐私(比如临床病历),行级 release 不合规——但我们的 benchmark 全部基于公开数据集(DuIE / CMeIE / FinRE 都是开源),可全量 release。

**D21 · Paper overclaim guardrail 用正则黑名单**——不是只靠人工审阅。原因:人容易忘;正则黑名单把 "human-labeled natural-noise"、"predicate-held-out robustness"、"proves production KG-RAG robustness" 等禁止措辞写死,任何后续 commit 触发验证器就红。这套 guardrail 出现在 `validate_paper_overclaim_guardrails` 里,是"我们对不能声称的东西的书面承诺",落实到 CI 层。**翻转条件**:等我们真跑了 masked-bank benchmark(`heldout_status` 从 `blocked_requires_masked_bank_scoring` 变 `complete`),就可以从 guardrail 里去掉对应正则——但这是有条件的,不能自作主张。

**D22 · Claim Scope / Main Claim Guardrail 显式书面化**——不是隐含。原因:`paper_review_packet` 里必须字面出现 "Supported claim: TripleChecker is a source-span audit and policy diagnostic framework." 与 "Unsupported claim: TripleChecker universally dominates fixed-template NLI or proves production KG-RAG robustness."。这两句是我们对审稿人的书面承诺;validator 强制它们必须在。**翻转条件**:如果有一天真做出了 universal dominance(不太可能),这两句要更新——但仍然写"能证明什么、不能证明什么"的双句,永远。

### 3.6 项目层决策

**D23 · Rebuttal 阶段承认自己错误(V1 的 label bug)**——不是遮盖。原因:E1 最初报的 $0.545$ 是 PASS-F1 mislabeled 为 SU-F1,与 paper 的 $0.804$ 差 $26$ 个点。任何审稿人一比对就会认为"你们方法在新抽样上崩了"。V1 主动挑破:$0.545$ 是 PASS-F1,同一 predictions 的 SU-F1 是 $0.8091$,与 paper 的 $0.804$ 完全一致($0/100$ 行差异)。**为什么不掩饰**:因为 $0.8091$ vs $0.804$ 的行级一致是硬证据,遮盖 label bug 反而暴露我们对自己数字都不自信;主动认+修正+行级证据,能把负面转成"这个团队反复自查"的正面。**教训**:任何 metric name 有别名(SU-F1 / PASS-F1 / HALL-F1 / unsupported-positive-F1 / precision-of-rejection)的项目,必须统一命名并写死到 metric bundle 输出里(见 Module 7 的 `_metric_row_from_predictions` 双视角)。

**D24 · Backbone invariance 从 universal claim 退到 direction-sensitive conditional claim**——不是硬撑原声称。原因:E2 显示三 backbone SU-F1 range $0.063 > 0.02$(原声称 criterion),且 330M 整体 delta $-0.015$ 为负。硬撑 universal 会被 330M 反例秒杀。V2 明确划界:只能声称"direction-sensitive 上 backbone-robust($+0.0700$ / $+0.0857$ / $+0.0466$)"。**这是 rebuttal 阶段最重要的姿态**:主动缩 claim scope,把 defensible 边界画清,比试图证明不 defensible 的东西聪明得多。

**D25 · Sealed test 明确不访问**——`manifest.json` 里 `sealed_test_accessed=false`。原因:rebuttal 阶段跑新实验容易 tempting 去 sealed test 上 tune,但那会毁掉整个可复现性叙事。硬约束"rebuttal 只用 dev 分布的 3000 行子集 + 现有 15000 行 benchmark",禁止碰任何"论文投稿后新配的" test。**这是学术诚信的 canonical 姿态**——审稿人问"你的 rebuttal 数字是不是 test-set-tuned"时,answer 是 manifest 里的这行 flag。

---

**推理链总原则**(把 D1–D25 抽象一下):

- **形式化 > 学习**:能 by construction 保证的性质(Layer 1 exact match、`fake_span` 全拒),不用模型;学习只处理模型能处理的部分。
- **可复现 > 峰值性能**:选 fixed threshold、offline bank、deterministic NLI,不选 tuned threshold、runtime LLM——峰值差 $2$ 分,换来永久 reproducible。
- **诚实 claim scope > universal 声称**:承认只能守 direction-sensitive、承认 label 是 agent-adjudicated、承认 backbone 不完全 invariant——把 defensible 边界写在 paper 和 validator 里。
- **行级证据 > 聚合数字**:所有报出数字必须从行级 CSV 重算得出;overclaim guardrail 与 blind sheet 强制机械化。
- **暴露 bug 与不一致 > 掩饰**:V1 label bug、V3 routing 分歧全部主动挑破并落到 REVERIFICATION.md;这本身就是可信度的物理证据。

---

**确认后进 §4:实验逐一还原**——把主 paper 里的每一张表 / 每一个数,还原出它由哪个脚本、用什么参数、跑哪一份行级数据、什么时候得出,并复述它对应的证据链(input 文件 → 处理 → 报出数字)。目的是面试被问"图 3 的 $0.8015$ 是怎么得来的?"时能直接回答。

题目保留。

## §4 实验逐一还原

这一节把 paper 与 rebuttal 里出现的每一处关键数字反向追溯到"脚本 → 输入 → 参数 → 输出文件 → validator claim id",目的是被问到"图 X 的 $0.Y$ 怎么来的"时,能直接给出 5 元组答案。所有数字保持 LaTeX。

### 4.1 主表:Source-Span Benchmark 主策略表 (paper Table 2 主体)

**这张表的每一行** (方法 × protocol × threshold × `pass_recall` × `hall_recall` × `hall_f1` × accuracy):

- 数字锚点(硬编码在 `validate_accept_claims.py:3297` 附近的期望列表里):
  - All-pass / all-pass / $0.0$ / $1.0$ / $0.0$ / $0.0$ / $0.2$
  - Layer-1-only / span-authenticity-only / $0.0$ / $1.0$ / $0.25$ / $0.4$ / $0.4$
  - TripleChecker / fixed@0.50 / $0.5$ / $0.807$ / $0.7011$ / $0.8015$ / $0.7223$
  - TripleChecker / best HALL-F1 / $0.974$ / $0.252$ / $0.9708$ / $0.8998$ / $0.8271$
  - Fixed-template NLI / fixed@0.50 / $0.5$ / $0.8133$ / $0.6963$ / $0.7990$ / $0.7197$
  - Fixed-template NLI / best HALL-F1 / $0.974$ / $0.2777$ / $0.9699$ / $0.9020$ / $0.8315$

- 生成脚本:`scripts/source_span_paper_tables.py`(见 Module 7),函数 `paper_main_policy_rows`;All-pass 与 Layer-1-only 两行由 `all_pass_policy_row` / `layer1_only_policy_row` 合入。

- 输入:`results/source_span_benchmark/scored_with_template_baselines.jsonl`(15000 行,每行含 `label_pass`、`tc_score`、`tc_label`、`tc_layer1_pass`、`fixed_template_nli_score`、`fixed_template_nli_label`、`fixed_template_nli_layer1_pass` 等字段)。

- 处理链:每行经 `row_pred_pass` 判决($\text{tc\_label} = \text{fake\_span}$ 或 $\text{layer1\_field} = \text{False}$ 即拒;否则 $\text{score} \ge \text{threshold}$ 才通过)→ 对整表算 `metric_bundle`(pass 视角)与 `invert_metrics`(hall 视角);best HALL-F1 protocol 是 `select_hall_f1_threshold` 在 $[0, 1]$ 步长 $0.001$ 网格搜索得到的 argmax。

- 输出:`results/source_span_benchmark/paper_main_policy_table.csv`。

- Validator claim id:`source_span_main_policy`。逐字段容差 $10^{-3}$。

- 面试口播:"$0.8015$ 是 TripleChecker 在 $\delta = 0.5$ 下,15000 行 benchmark 全量 hall-positive F1;由 `source_span_paper_tables.py` 从 `scored_with_template_baselines.jsonl` 每行的 `tc_score` 与 `tc_layer1_pass` 判决重算,行级证据可 100% 复现。"

### 4.2 主表 Bootstrap CI

- 数字锚点(`validate_accept_claims.py:3317` 附近):
  - TripleChecker / fixed@0.50 / `hall_f1` / $0.8015$ / $[0.7962, 0.8063]$
  - TripleChecker / fixed@0.50 / accuracy / $0.7223$ / $[0.7161, 0.7281]$

- 生成脚本:`scripts/source_span_paper_tables.py`,函数 `bootstrap_phase3_rows`。

- 参数:$B = 1000$ 迭代,聚类 key 是 $(\text{dataset}, \text{doc\_id}, \text{triple\_id})$;CI 用 $[2.5\%, 97.5\%]$ 百分位数;seed 固定。

- 处理链:每次 bootstrap 从聚类 key 集合有放回抽样(而不是从行有放回抽样),重放对应行的所有预测,重算 metric bundle → 收集 $B$ 个 `hall_f1` / accuracy 值 → 排序取百分位。

- 输出:`results/source_span_benchmark/bootstrap_ci.csv`。

- Validator claim id:`source_span_bootstrap_ci`。

- 面试口播:"CI $[0.7962, 0.8063]$ 是 1000 次 clustered bootstrap 在 $(\text{dataset}, \text{doc\_id}, \text{triple\_id})$ 键上的 $95\%$ 百分位区间;clustered 是因为同文档三元组共享上下文噪声,iid 会低估不确定性。"

### 4.3 分条件切片 (paper Table 3)

- 数字锚点(`validate_accept_claims.py:3335` 附近,TripleChecker fixed@0.50):
  - `fake_span`:$n=3000$,$\text{hall\_recall}=1.0$,$\text{hall\_f1}=1.0$,$\text{accuracy}=1.0$,$\text{tn}=3000$,$\text{fp}=0$
  - `object_replacement_same_predicate`:$\text{hall\_recall}=0.908$,$\text{hall\_f1}=0.9518$,$\text{accuracy}=0.908$,$\text{tn}=2724$,$\text{fp}=276$
  - `subject_replacement_same_predicate`:$\text{hall\_recall}=0.4347$,$\text{hall\_f1}=0.6059$,$\text{accuracy}=0.4347$,$\text{tn}=1304$,$\text{fp}=1696$
  - `predicate_mismatch`:$\text{hall\_recall}=0.4617$,$\text{hall\_f1}=0.6317$,$\text{accuracy}=0.4617$,$\text{tn}=1385$,$\text{fp}=1615$

- 生成脚本:`scripts/analyze_source_span_benchmark.py` 的 `summarize_by_slice(slice_fields=["condition"])` 与 `source_span_paper_tables.py` 的多方法版本。

- 输入:同 4.1。

- 输出:`results/source_span_benchmark/metrics_by_condition.csv`(单方法版)与 `baseline_comparison_metrics_by_condition.csv`(多方法版)。

- Validator claim id:`source_span_condition_results`。

- 关键 sanity check:`fake_span` 条件下 $\text{fp} = 0$ 是 **Layer 1 by construction 的必然结果**——`fake_span` 定义上就不在文档里,精确子串匹配一定失败,SAR = $0$,任何 threshold 都不会误放。**这不是"我们学出来的能力",是设计带来的**。面试若被问"为什么 `fake_span` 全对是不是过拟合",答:是 Layer 1 的设计保证,不是学习。

- 分条件"难度光谱":`object_replacement`($90.8\%$ 拒绝)→ `predicate_mismatch`($46.2\%$)→ `subject_replacement`($43.5\%$)。**subject 替换最难**,因为中文里"张三是李四的父亲"和"李四是张三的父亲"结构上极接近,NLI 需要真正理解方向;object 替换相对容易,因为对象通常是实体词,NLI 能捕获实体差异。

### 4.4 Supported-Loss Budget 表 (deployment-oriented policy)

- 数字锚点(`validate_accept_claims.py:3388` 附近):
  - budget $25$:$\text{pass\_false\_rejects}=25$,$\text{hall\_true\_rejects}=4473$
  - budget $50$:$50$,$4940$
  - budget $100$:$98$,$5547$
  - budget $250$:$249$,$6751$
  - budget $500$:$500$,$8058$
  - 每一行 $n = 15000$,$n\_\text{pass} = 3000$,$n\_\text{hall} = 12000$。

- 生成脚本:`source_span_paper_tables.py` 的 `supported_loss_budget_rows`。

- 逻辑:在 $\{25, 50, 100, 250, 500\}$ 五个预算下,遍历 $[0, 1]$ 步长 $0.001$ 的 threshold,选出满足 $\text{pass\_false\_rejects} \le \text{budget}$ 且 $\text{hall\_true\_rejects}$ 最大的 threshold。

- 输出:`results/source_span_benchmark/supported_loss_budget_policies.csv`。

- Validator claim id:`source_span_loss_budgets` + `supported_loss_budgets`(还有 row-level 版:`source_span_supported_loss_expected_row` 在 validator 里独立重算)。

- 面试口播:"这张表回答'如果我最多能容忍误杀 $N$ 条 supported triple,能拒多少 unsupported',是给下游用户选阈值的实用参考,不是主论文的 optimal 声明。"

### 4.5 Paired 方法 Delta (paper Table 4)

- 数字锚点(`validate_accept_claims.py:3422` 附近,TripleChecker vs Fixed-template NLI on `hall_f1`):
  - fixed@0.50:`point_a` $= 0.8015$,`point_b` $= 0.7990$,delta $= +0.0025$,$95\%$ CI $[0.0014, 0.0038]$
  - best HALL-F1:`point_a` $= 0.8998$,`point_b` $= 0.9020$,delta $= -0.0022$,CI $[-0.0029, -0.0015]$

- 生成脚本:`source_span_paper_tables.py` 的 `bootstrap_phase3_rows` 单循环 batch 版(见 Module 7):**同一批 resampled indices** 同时喂给所有方法,保证 paired 语义。

- 输出:`results/source_span_benchmark/paired_method_deltas.csv`。

- Validator claim id:`source_span_baseline_deltas` + `paired_scorers`。

- **关键解读**:fixed@0.50 下 TripleChecker 比 Fixed-template NLI 好 $+0.0025$,CI 不过 $0$,统计显著但**幅度极小**;best HALL-F1 下 TripleChecker 反而比 Fixed-template 差 $-0.0022$,同样显著。这是 §3 里 D24"缩 claim scope"的直接来源:paper 不能声称 "TripleChecker universally dominates Fixed-template NLI",只能说 fixed@0.50 protocol 下小幅优势 + best HALL-F1 protocol 下 Fixed-template 略强。

- 面试口播:"$+0.0025$ 显著但小;$-0.0022$ 更是我们主动挑破的负结果——`rebuttal_exp` 里 V2 就把这个 negative delta 挂进了 Rebuttal Usability Tier 表,禁止我们在 paper 里声称 universal dominance。"

### 4.6 Prevalence-Sensitive Policy

- 数字锚点(`validate_accept_claims.py:3485` 附近):
  - fixed@0.50 / prevalence $0.1$:`kept_precision` $=0.9605$,`reject_precision` $=0.2876$,`supported_false_rejects_per_1000` $=173.7$,`unsupported_rejected_per_1000` $=70.11$
  - supported-loss $\le 25$ / prevalence $0.1$:$0.9343$,$0.8331$,$7.47$,$37.28$

- 生成脚本:`scripts/source_span_prevalence_policy.py`(`paper_tables` 系列的姊妹脚本,主 pipeline 在 `source_span_paper_tables.py` 里也有 hooks)。

- 逻辑:benchmark 里 unsupported 占 $12000/15000 = 80\%$,过高;真实场景 unsupported prevalence 可能 $10\%$。这张表把 confusion matrix 按 target prevalence 重加权,报"每 1000 条 triple 里误杀多少 supported、拒了多少 unsupported"。

- 输出:`results/source_span_benchmark/prevalence_policy_table.csv` + `prevalence_policy_report.md`。

- Validator claim id:`source_span_prevalence_policy`。

### 4.7 Direct Verifier Baseline (paper Table 5)

- 数字锚点(`validate_accept_claims.py:2954` 附近,fixed@0.50 protocol on 3000-row rebuttal subset,列顺序 PASS-P / PASS-R / SU-P / SU-R / accuracy):
  - All-pass:$1.000 / 0.799 / 0.000 / 0.000 / 0.665$
  - ROUGE-L:$0.203 / 0.329 / 0.940 / 0.534 / 0.450$
  - BERTScore:$1.000 / 0.799 / 0.000 / 0.000 / 0.665$
  - Fixed-template NLI:$0.910 / 0.793 / 0.239 / 0.337 / 0.685$
  - Generic-relation NLI:$0.962 / 0.808 / 0.164 / 0.265 / 0.695$
  - MiniCheck RoBERTa-Large:$0.075 / 0.137 / 0.955 / 0.504 / 0.370$
  - LLM reference scorer:$0.993 / 0.849 / 0.313 / 0.472 / 0.765$
  - TripleChecker:$0.970 / 0.809 / 0.149 / 0.247 / 0.695$

- 生成脚本:`scripts/compare_source_span_methods.py` + `scripts/direct_verifier_baseline_report.py`。

- 输出:`results/DIRECT_VERIFIER_BASELINE_REPORT.md`。

- Validator claim id:`direct_baseline_protocol`。

- **关键解读**:$8$ 种 scoring 方法逐一对比:
  - **BERTScore 是 all-pass 的伪装**——SU-P/SU-R 全 $0$,意味着它从不拒绝任何行;它的 accuracy $=0.665$ 等于 all-pass。原因:$(s, p, o)$ 三元组文本与 `source_span` 文本的 BERTScore 总是接近 $1$,阈值化后区分不出。这是 baseline 挑选故意要暴露的:**证明 embedding similarity 不足以做 hallucination detection**。
  - **MiniCheck 相反**——SU-R $=0.955$ 但 PASS-R 只有 $0.137$,是 all-reject 型 baseline,accuracy 仅 $0.370$。
  - **LLM reference scorer**($0.765$ accuracy)是最强 baseline,但它是 LLM API,不 API-free。
  - **TripleChecker**($0.695$ accuracy)与 Generic-relation NLI 平手,略低于 LLM。诚实定位:TripleChecker 不是最好的判官,是**"在 API-free 约束下的可靠判官"**。

- **HR (high-retention, PASS-R $\ge 0.95$) 版本**同样在 validator 里锁死:
  - BERTScore $0.630 / 0.955 / 0.090 / 0.152 / 6/67$
  - Fixed-template $0.274 / 0.970 / 0.164 / 0.268 / 11/67$
  - LLM reference $0.800 / 0.955 / 0.403 / 0.540 / 27/67$
  - TripleChecker $0.558 / 0.955 / 0.179 / 0.282 / 12/67$
  - 最后一列 "N/67" 是**这个方法在自己的 threshold 下与 gold PASS 的 concordant 行数** / **所有 disagreement 行数**——诊断打分方向。

- 面试口播:"BERTScore 那行是我们故意留的诊断——它 accuracy 看起来 $0.665$ 挺高,但 SU-P 和 SU-R 都是 $0$,与 all-pass 完全一致,说明 embedding similarity 不能拒绝任何 hallucination。这条 baseline 的价值不在竞争,在于说明 embedding-based 方法在这个任务上是伪 baseline。"

### 4.8 Threshold Operating Policy 报告

- 数字锚点(`validate_accept_claims.py:2975` 附近):
  - High-retention fixed / $0.500$ / $0.970 / 0.809 / 0.149 / 0.247 / 14$ / Paper setting
  - Best PASS precision at PASS-R $\ge 0.95$ / $0.530$ / $0.962 / 0.808 / 0.164 / 0.265 / 16$
  - 5-fold PASS-F1 / $0.494$ / $0.955 / 0.799 / 0.134 / 0.220 / 15$
  - 5-fold HALL-F1 / $0.934$ / $0.233 / 0.361 / 0.881 / 0.518 / 161$

- 生成脚本:`scripts/threshold_operating_policy_report.py`。

- 逻辑:五折 CV 的 `cv_threshold_predictions`——每折上单独选阈值,再在 held-out 折上评估,防止阈值 test-set-tuned。这一节的诚实点:PASS-F1 policy 选出的阈值 $0.494$ 拒了 $15$ 条 unsupported,与 fixed@0.50 的 $14$ 条几乎持平,说明 $0.5$ 不是"运气好",是 near-optimal。

- 输出:`results/THRESHOLD_OPERATING_POLICY_REPORT.md`。

- Validator claim id:`threshold_operating_policy`。

- Budget 行:$4 / 25 / 100$ 三档,分别对应 $10/67, 22/67, 59/67$ 的 unsupported rejection。

- 面试口播:"$\delta = 0.5$ 不是 tune 出来的——五折 CV 在 held-out 上选出的最优 threshold 是 $0.494$,与 $0.5$ 差 $0.006$。这说明 $0.5$ 是自然 near-optimal,不是过拟合。"

### 4.9 Natural Noise Pilot (paper §5.2 + Table 6)

**59 行版**(第一版 pilot):

- 数字锚点(`validate_accept_claims.py:2988` 附近):
  - 提取 triples:$59$ across $18$ 文档
  - 标签:$35$ PASS + $24$ HALLUCINATION
  - Span authenticity(Layer 1):$47/59$ pass,$12/59$ fail
  - PASS-positive:P/R/F1/A $= 0.838 / 0.886 / 0.861 / 0.831$,TP=$31$/FP=$6$/FN=$4$/TN=$18$
  - Unsupported-positive:P/R/F1/A $= 0.818 / 0.750 / 0.783 / 0.831$,TP=$18$/FP=$4$/FN=$6$/TN=$31$
  - Layer-1-only:unsupported P/R/F1 $= 1.000 / 0.500 / 0.667$
  - Threshold sweep:$0.75$ 处 $0.853 / 0.833 / 0.800$,$0.95$ 处 $0.767 / 0.917 / 0.759$

- 生成脚本:`scripts/natural_noise_pipeline.py`(Module 6 的 11 子命令 pipeline)。

- 输入:`results/natural_noise/documents.jsonl`($50$ 文档),经 Qwen2.5-3B extraction 得到 $59$ triples across $18$ docs(其余文档提取失败或空)。

- 输出:`results/natural_noise/LOCAL_QWEN25_3B_PILOT_REPORT.md` + 系列 CSV/JSONL。

- Validator claim id:`natural_qwen25_3b`(以及 `_audit`/`_expanded`/`_human_audit`/`_double_annotation`/`_baseline_sensitivity`/`_calibration_50`)。

**383 行扩展版**:

- 数字锚点(`validate_accept_claims.py:2933` 附近):
  - 采样文档 $160$($80$ DuIE + $80$ CMeIE)
  - 抽取 triples $383$
  - Label:HALLUCINATION $=122$,PASS $=261$
  - Label sources:agent-audited $=383$
  - PASS-positive:P/R/F1/A $= 0.8447 / 0.7088 / 0.7708 / 0.7128$
  - Unsupported-positive:P/R/F1/A $= 0.5366 / 0.7213 / 0.6154 / 0.7128$
  - Unsupported-positive recall CI:$0.7213$ $[0.6176, 0.8182]$,$n = 128$,$B = 1000$
  - Unsupported-positive F1 CI:$0.6154$ $[0.5379, 0.6940]$,$n = 128$,$B = 1000$
  - Failure audit:$20$ 条($10$ `false_pass` + $10$ `false_reject`)
  - Claim scope 硬性声明:"This artifact supports an extractor-output source-span applicability diagnostic only"

- 输出:`results/natural_noise/expanded_qwen25_3b/`。

- **R3 独立复现**(`rebuttal_exp`/`reverification_r3`):TripleChecker SU-F1 $= 0.6471$,Fixed-template $= 0.6608$,doc-clustered $95\%$ CI $[0.5636, 0.7204]$ vs $[0.5827, 0.7278]$——**大幅重叠**,不能声称显著优势。paper 里对应措辞是"CI 重叠,观测点差在采样不确定性范围内"。

- 面试口播:"$383$ 行是 $160$ 文档($80+80$)扩展版,`label_source` $=$ agent-adjudicated(不是 human);TripleChecker SU-F1 $=0.6471$,与 Fixed-template $0.6608$ CI 重叠,论文里只声称'extractor-output source-span applicability diagnostic',不声称 hallucination detection performance 上的胜出。"

### 4.10 RTAV Heldout 状态 (paper §4.5 disclaimer)

- 数字锚点:`heldout_status.json` 的 `benchmark_level_heldout_status = blocked_requires_masked_bank_scoring`(默认发布状态);manifest 里 `predicate_folds = 5`,`document_folds = 5`,`n_predicates = 128`,`n_doc_ids` 视 benchmark 而定。

- 生成脚本:`scripts/source_span_rtav_heldout.py`(Module 8)。

- 参数:$\text{seed} = 42$,shuffle 后按 idx % $n_\text{folds}$ 分桶。

- 输出:`results/source_span_benchmark/rtav_heldout/split_manifest.json` + `heldout_status.json` + `heldout_report.md`。

- Validator claim id:`source_span_rtav_heldout_control`。

- **paper 里对应的声明**:"benchmark-level held-out is blocked; predicate-held-out metrics via bank fallback are available; document-held-out is blocked because bank lacks `doc_id` provenance"。这是 §3 D21 overclaim guardrail 里禁止"predicate-held-out robustness"措辞的对应实体。

### 4.11 RTAV Leakage Diagnostic (paper §4.5 supplementary)

- 数字锚点:
  - `bank_coverage` / `benchmark_predicate_coverage`:$128/128 = 1.0$(rows $15000/15000$)
  - `benchmark_full_bank` / `fixed@0.50_hall_f1`:TripleChecker-bank vs TripleChecker delta;vs Fixed-template delta
  - `human_predicate_heldout` / `unseen_mean_delta_hall_f1`:200 行人工集上的平均 delta,配 seed 数
  - `leakage_gate` / `benchmark_level_heldout_status`:$\text{missing}$(默认)

- 生成脚本:`scripts/source_span_rtav_leakage_diagnostic.py`(Module 8)。

- 输出:`results/source_span_benchmark/rtav_leakage_diagnostic.csv` + `.md`。

- Validator claim id:`source_span_rtav_leakage_diagnostic`。

- 面试口播:"这张诊断表把 full-bank benchmark 上的 bank-vs-fixed delta(不作为泛化证据)和 200 行人工集上的 predicate-hiding delta(真正的 unseen 证据)分开挂,末尾 `leakage_gate` 行硬编码 $\text{missing}$,直接禁止我们从 full-bank 结论声称 unseen-schema robustness。"

### 4.12 Rebuttal E1:DeepSeek 对比 (rebuttal §1)

- 数字锚点(`e1/results.csv` + `FINAL_NUMBER_CROSSCHECK.md`):
  - 抽样:$3000$ 行($600 \times 5$ conditions),$\text{seed}$ 固定,$\text{temperature} = 0$
  - TripleChecker:Pass-R/SU-P/SU-R/SU-F1 $= 0.805 / 0.9360 / 0.7125 / 0.8091$,cost $\$0$,wall $10.586 \text{s}$/$1000$
  - DeepSeek span-only:$0.3683 / 0.8613 / 0.9804 / 0.9170$,cost $\$0.019873$/$1000$,wall $922.177 \text{s}$/$1000$
  - DeepSeek full-doc:$0.3367 / 0.8462 / 0.9125 / 0.8781$,cost $\$0.021560$/$1000$,wall $891.575 \text{s}$/$1000$
  - Defensive rejection(`defensive_rejection.csv`):subject 拒绝率 span/full $=0.9917 / 0.9900$,predicate $=0.9867 / 0.9867$,TripleChecker $=0.6117 / 0.5033$
  - Consistency(`consistency.csv`):$n = 300$,repeats $= 3$,self-consistency $= 1.0$
  - 延迟比:$891.575 / 10.585667 \approx 84.22 \times$

- 生成脚本:`rebuttal_exp/e1/sample.py`(抽样)→ `run_judge.py`(DeepSeek 调用)→ `report.py`(汇总)→ `finalize.py`(冻结)。

- 输出:`rebuttal_exp/e1/*.csv` + `.md`。

- 面试口播:"DeepSeek span-only SU-F1 $=0.917$ 比 TripleChecker 高 $0.11$,但 PASS-R 只有 $0.368$,加上 all-reject anchor $0.888$,说明 DeepSeek 是靠严格拒绝倾向堆分——保留率崩 + 有 API 成本 + 慢 $85$ 倍,是 trade-off 而非碾压。"

### 4.13 Rebuttal E2:Backbone 一致性 (rebuttal §2)

- 数字锚点(`e2/results.csv` + `v2_backbone_consistency.csv`):
  - Erlangshen-Roberta 110M:threshold $0.75$,SU-F1 $= 0.8535$
  - mDeBERTa-330M:threshold $0.80$,SU-F1 $= 0.8879$
  - Erlangshen-Roberta 330M:threshold $0.85$,SU-F1 $= 0.8248$
  - Range:$0.063075$
  - Overall bank-minus-fixed delta:$+0.010$ / $+0.023$ / $-0.01518$
  - Direction-sensitive gain:$+0.0700$ / $+0.0857$ / $+0.0466$
  - Calibration/eval split:$3030 / 11970$,按 `doc_id` 分组
  - 关系不稳定性(`relation_instability.csv`):按 predicate 数分档 $60 / 56 / 160 / 124$,对应 SU-F1 range $0.380172 / 0.343496 / 0.340250 / 0.327820$

- 生成脚本:`rebuttal_exp/e2/run.py`。

- 面试口播:"三 backbone SU-F1 range $0.063$ 超过 invariance criterion $0.02$;overall delta 在 330M 上为 $-0.015$;但 direction-sensitive 上三 backbone 全正($+0.047$ 到 $+0.086$)——V2 明确只允许 rebuttal 声称 direction-sensitive robust,不许声称整体 invariant。"

### 4.14 Rebuttal E3:Fuzzy vs Exact (rebuttal §3)

- 数字锚点(`e3/results.csv`):
  - Exact substring:SU-F1 $= 0.9137$,`fake_span` detection $= 1.000$,authentic false-kill $= 0/3000 = 0.000$
  - `partial_ratio`@0.80:SU-F1 $= 0.914$,`fake_span` detection $= 0.998$($6/3000$ 漏),authentic false-kill $= 0.000$
  - Jaccard@0.9:SU-F1 $= 0.8542$,authentic false-kill $= 543/3000 = 18.1\%$
  - Jaccard@0.8/0.95:false-kill $17.1\%$–$19.3\%$,SU-F1 $0.850$–$0.857$

- 生成脚本:`rebuttal_exp/e3/run.py`。

- **R4 独立复现**推翻了原 E3 报告里 $0.896$ 标签(那是 PASS-F1,不是 SU-F1),校正为 $0.9137$。

- 面试口播:"exact 是必需契约:任何 fuzzy 阈值要么漏 `fake_span`(`partial_ratio`@0.80 漏 $6$)、要么误杀 authentic($18\%$ Jaccard@0.9),exact 在 authenticity-false-kill 上永远 $0$。"

### 4.15 Rebuttal E4:方向敏感 + 路由 (rebuttal §4)

- 数字锚点(`e4/direction_results.csv` + `route_results.csv`):
  - direction-sensitive SU-F1:TripleChecker $0.6730$ vs Fixed-template $0.5727$,delta $+0.1003$
  - 非 direction-sensitive delta:$0.6597 - 0.5407 = +0.1190$(**更大**)
  - direction-sensitive 上多拒 $2939 - 2330 = 609$ 条 unsupported
  - 路由:$15000/15000$ 行,$128/128$ predicates 全走 offline bank——dictionary 和 fallback 事实上空转

- 生成脚本:`rebuttal_exp/e4/generate_manifest.py` → `analyze.py`。

- 面试口播:"E4-a 支持 direction-sensitive 上 sizable gain($+0.10$)但**不支持 gain 集中在 direction-sensitive**(非 direction-sensitive delta 更大);E4-b 揭示实际代码是 bank-first,与 paper 的 dictionary-first 描述冲突——修 paper 描述,不修代码。"

### 4.16 Label Audit (paper §3.3 + integrity)

- 数字锚点(`validate_accept_claims.py:4011` 附近):
  - $n\_\text{rows} = 300$,`per_cell` $= 20$,seed $= 20260610$
  - Cells:$3$ datasets(cmeie/duie/finre)$\times$ $5$ conditions(`fake_span`/`gold_positive`/object/predicate/subject)$= 15$ cells,每 cell $20$ rows

- 生成脚本:`scripts/source_span_label_audit_sample.py` → `..._summary.py` → `..._adjudication.py`。

- 输出:`results/source_span_benchmark/label_audit/label_audit_sample.jsonl` + `label_audit_sheet.csv` + `label_audit_summary.{json,csv,md}` + `LABEL_AUDIT_GUIDELINES.md`。

- Validator claim id:`source_span_label_audit_packet` + `source_span_label_double_annotation_packet` + `source_span_label_validity_summary` + `source_span_label_noise_sensitivity`。

- 关键 sanity:`audit_id` 严格 $\text{audit\_0000}$ 到 $\text{audit\_0299}$,顺序绑定;blind sheet 表头必须完全等于 `SOURCE_SPAN_BLIND_FIELDS`,leak 字段(如 `tc_score`、`tc_label`)一旦出现即抛错;human_* 字段必须全空,防止标注前 leak。

- 面试口播:"$300$ 行审计等分 $15$ 格($3 \times 5$)$\times 20$,seed $=20260610$;双标注是 agent-adjudicated 而非 human,`schema_note` 里显式声明 not-human-labeled,paper 里禁止 'human-labeled' 措辞——所有这些由 `validate_accept_claims.py` 里 `validate_label_double_annotation_packet` 机械检查。"

### 4.17 30 项 Claim Manifest 完整清单

Validator 的 `REQUIRED_MANIFEST_CLAIMS` 集合(Module 8):

- `source_span_main_policy` (4.1)
- `source_span_bootstrap_ci` (4.2)
- `source_span_condition_results` (4.3)
- `source_span_loss_budgets` (4.4)
- `source_span_baseline_deltas` (4.5)
- `source_span_prevalence_policy` (4.6)
- `source_span_label_audit_packet` (4.16)
- `source_span_label_double_annotation_packet` (4.16)
- `source_span_label_validity_summary` (4.16)
- `source_span_label_noise_sensitivity` (4.16)
- `source_span_rtav_leakage_diagnostic` (4.11)
- `source_span_rtav_heldout_control` (4.10)
- `source_span_rtav_bank_provenance_audit`(bank 溯源审计)
- `duie_main`(DuIE 主结果)
- `threshold_operating_policy` (4.8)
- `supported_loss_budgets`(与 4.4 的双胞胎 aggregate 版)
- `label_ambiguity`(边界 PASS 审计)
- `paired_scorers`(与 4.5 双胞胎)
- `high_retention_baselines`(4.7 HR 段)
- `ranking_diagnostics`(AUROC/AP)
- `direct_baseline_protocol` (4.7)
- `natural_qwen25_3b` (4.9)
- `natural_qwen25_3b_audit`
- `natural_qwen25_3b_expanded`
- `natural_qwen25_3b_human_audit`
- `natural_qwen25_3b_double_annotation`
- `natural_qwen25_3b_baseline_sensitivity`
- `natural_qwen25_3b_calibration_50`
- `kg_rag`(KG-RAG 章节承诺——rebuttal 里没跑,只做 claim scope 声明)

每一项对应 `claims_manifest.csv` 一行,`result_file` 字段指向硬盘上的 CSV/JSON,validator 加载后行级重算并对齐。

---

**面试速答模板**(任何数字被问到,按这个 5 元组答):
1. **值 $=$ 什么**:直接读数字(带 LaTeX 精度)
2. **由什么脚本生成**:`scripts/X.py` 的 `Y` 函数
3. **输入什么行级数据**:`results/.../Z.jsonl` 第几列
4. **参数**:threshold / seed / `n_folds` / `bootstrap_B`
5. **由什么 validator claim 锁死**:`REQUIRED_MANIFEST_CLAIMS` 里的 id + 容差

示例演练:"$0.8015$?"
→ "TripleChecker fixed@0.50 protocol 的 HALL-positive F1;`source_span_paper_tables.py` 的 `paper_main_policy_rows`;输入 `scored_with_template_baselines.jsonl` 15000 行的 `tc_score` 与 `tc_layer1_pass`;threshold $=0.5$,聚类 bootstrap $B=1000$,seed 固定;claim id `source_span_main_policy`,容差 $10^{-3}$。CI $[0.7962, 0.8063]$ 来自 `source_span_bootstrap_ci`。"

---

**确认后进 §5:论文↔代码不一致点**。这一节把 §2–§4 里散见的所有实体/描述漂移集中列出(V3 routing / label 命名歧义 / 阈值默认值 / 术语用词等),每条给出"paper 说什么、code 做什么、修哪一边、为什么"。

题目保留。

## §5 论文↔代码不一致点

以下 8 条是从 §2–§4 逐模块深挖里累积出来的所有"论文文本"与"实际代码/artifact"之间的漂移。分成 A(必须修论文)、B(应当在论文里补一句澄清)、C(可以维持现状但要在 rebuttal / 面试里明说)。同一节里,越靠前问题越硬。

---

### §5.1【A 类,必修论文】RTAV 运行时路由:paper 说"dictionary → bank",code 是"bank → dictionary → generic"

- **论文说什么**:方法节把 RTAV 描述为"先走 coarse-type 词典,词典 miss 才落到离线 bank",并给出词典覆盖 59.1% 作为路由主分支的关键数字。
- **代码做什么**:`RTAVModule.get_template()` 第一步就查 offline bank;只有当 bank 里没有该谓词时才回退 `legacy_v1_template()`(即"先查词典、再回退 generic")。发布的 benchmark bank 覆盖全部 128 个谓词,因此 15000/15000 行、128/128 个谓词全部走的是 bank 分支,dictionary/generic 分支在 release 配置下是空集。
- **修哪一边**:改论文。把 §Method 里的"dictionary-first"改成"bank-first when a bank is supplied;dictionary-only when no bank",并把 59.1% 从"路由主分支占比"重新定位成"独立的 dictionary 资源覆盖率"。
- **为什么**:这是唯一一条真正会被 reviewer 逮到"实现和描述不符"的硬漂移。已经在 `VERIFICATION.md` V3、`FINAL_NUMBER_CROSSCHECK.md` L12 冻结,rebuttal 语言也已固定;论文正文如果不同步修,签收版会出现"paper 说 A,released code 做 B"的正面矛盾。

---

### §5.2【A 类,必修论文/表头】E1 里 0.545 vs 0.804 的"metric label bug"

- **论文说什么**:E1 起初在 rebuttal 材料里用 0.545 作为 TripleChecker 的 SU-F1,和主表 0.804 摆在一起对比,给出"回归 26 个点"的表象。同类问题也波及 DeepSeek 0.509/0.399 与 E2 backbone 的 0.565/0.633/0.555。
- **代码做什么**:`validate_accept_claims.py` 的 `metric_bundle` 明确把两套 F1 分开:PASS-positive-F1(以"被支持"为正类)与 SU-positive-F1(以"未被支持"为正类,即 `hall_f1` / SU-F1)。用 E1 同一批预测重新按 SU-positive 计算,得到 0.8091,和主表 0.804 逐行一致(100 行差异 0/100、最大分数差 0.0)。0.545 只是 PASS-F1 的正确取值。
- **修哪一边**:改论文/rebuttal 的表头与文字。所有 rebuttal 材料按 `FINAL_NUMBER_CROSSCHECK.md` L30 的"Prohibited SU-F1 labels"处理:0.545、0.509/0.399、0.565/0.633/0.555 一律标注为 PASS-F1,SU-F1 位置替换为 0.8091、0.917/0.878、0.8535/0.8879/0.8248。
- **为什么**:这不是模型问题,是列标签写错。如果混进最终稿,reviewer 会得出"回归 26 个点"的错误结论;把 label 修回来之后,和主表完全自洽,还多出一条"独立再现证据"。

---

### §5.3【B 类,补一句澄清】阈值 δ=0.5 是"固定操作点",不是"最优阈值"

- **论文说什么**:主表以 δ=0.5 报告 TripleChecker(`pass_recall`=0.807, `hall_recall`=0.7011, `hall_f1`=0.8015, accuracy=0.7223),同时另行给出"best HALL-F1"行(threshold=0.974, `hall_f1`=0.8998),两行并列。
- **代码做什么**:`validate_accept_claims.py` 里 fixed@0.50 是硬编码的"上线操作点"(`reproduce_hallucination_metric_bundle` 断言这一行严格等于 threshold=0.5);best HALL-F1 是"事后曲线扫描"结果,并额外由 `supported_loss_budgets`(25/50/100/250/500)标出这条曲线上各点的 supported-loss 代价。两行的语义完全不同:一行是"部署时该用什么阈值",另一行是"如果只看 HALL-F1 曲线能到多高"。
- **修哪一边**:改论文表注一句话。明确"fixed@0.50 是我们建议的部署操作点,best HALL-F1 是同一曲线上的最大值行,不建议直接部署,因为它把 `pass_recall` 从 0.807 拉到 0.252"。
- **为什么**:如果 reviewer 只扫表格数字,会以为我们同时主张 0.807 recall 和 0.8998 F1,导致后面 §4.4 supported-loss 分析里"25/50/100/250/500 supported 损失"的解释链断掉。补一句 caption 就能一次修好。

---

### §5.4【B 类,补一句澄清】"API-free" 声明的边界:V4 boundary cascade 是 rebuttal-only 的扩展,不是主 pipeline

- **论文说什么**:主 pipeline 通篇按"离线 NLI + 词典/bank"实现,主打"零 API 依赖、10.586 s / 3000 rows"。
- **代码做什么**:`rebuttal_exp/e1/` 里的 DeepSeek 系列(SU-F1 0.917/0.878、PASS-F1 0.509/0.399、$0.0199/$0.0216、922.177 s / 891.575 s)以及 V4 boundary cascade(SU-F1 0.8091→0.8237、+1.46 分、6.37% API 覆盖率、p=1.777e-07)是 rebuttal 里回应 reviewer "为什么不叫大模型" 才做的对照;它们不是主 pipeline 的一部分。
- **修哪一边**:改论文 caption / rebuttal 用词。凡是提到 DeepSeek 或 boundary cascade 的地方,一律加限定语"as a rebuttal-only extension"或"selective cascade evaluated post hoc";主 pipeline 仍然叫 API-free。
- **为什么**:目前 rebuttal 已经这么写("A selective cascade that sends only the 6.37% of rows..."),但如果论文正文因为审稿意见把 V4 直接放进主图,主张"API-free" 就会出现内部矛盾。当前处理是干净的:V4 只在 rebuttal 出现,主 pipeline 描述不变。

---

### §5.5【B 类,补一句澄清】direction-sensitive 增益并非"集中"在 direction-sensitive 子集

- **论文说什么**:E4 的叙述容易被理解成"RTAV 的增益主要来自 direction-sensitive 关系"(即 `subject_replacement` 类那一支)。
- **代码做什么**:`rebuttal_exp/e4/direction_results.csv` 给出 direction-sensitive 子集 SU-F1 从 0.5727 到 0.6730(+0.1003, +609 rejections);非-direction-sensitive 子集 delta 是 +0.1190,反而更大。E4-a 的 `conclusion.md` 已经明确指出"the gain is not concentrated on the direction-sensitive subset"。
- **修哪一边**:改论文措辞。用"positive on direction-sensitive relations"替代"concentrated on direction-sensitive relations";如果要一句话涵盖两个子集,写成"RTAV yields a positive SU-F1 gain on both direction-sensitive and non-direction-sensitive relations, with a slightly larger gain on the latter"。
- **为什么**:这条不是数据错,是解释错。修完只是措辞替换,没有任何数字变动。若不改,可能被 reviewer 用 E4 自己的 conclusion.md 反将一军。

---

### §5.6【B 类,补一句澄清】backbone 一致性不是"跨骨干不变",只是"direction-sensitive 方向一致"

- **论文说什么**:E2 若被写成"跨三个骨干 SU-F1 稳定",容易被 reviewer 逼出反例。
- **代码做什么**:`rebuttal_exp/e2/results.csv` 与 `reverification_r2_results.csv` 显示三个骨干独立标定后 SU-F1 为 0.8535/0.8879/0.8248,range=0.063,超过 §2 §7 里 0.02 的稳定性判据;overall bank-vs-fixed delta 分别为 +0.010/+0.023/-0.015,其中 330M 是负的,即"整体 delta 方向"跨骨干并不一致。**唯一跨骨干一致的**是 direction-sensitive 子集的 delta:+0.070/+0.086/+0.047,三个都是正的。
- **修哪一边**:改论文措辞与 rebuttal 文字。按 `VERIFICATION.md` V2 里已经冻结的 safe wording:"Although absolute performance and the overall bank-vs-fixed delta vary with the NLI backbone, RTAV's gain on direction-sensitive relations remains positive across all three tested backbones (+4.7 to +8.6 SU-F1 points)"。
- **为什么**:E2 是被 reviewer 追打最狠的地方(骨干敏感性)。如果不把这条限定语写清,330M 的 -0.015 会直接被反手拿来当反例。当前 rebuttal 已经处理好,论文里的对应句需要同步收紧。

---

### §5.7【C 类,维持现状但面试要提】RTAV 未上线的 heldout 保护是"默认阻塞",不是"通过评估"

- **论文说什么**:RTAV bank 的 unseen-schema 泛化不在主 claim 范围内,论文只主张 controlled benchmark 上的 controlled diagnostic。
- **代码做什么**:`source_span_rtav_heldout.py` 默认 `--masked_bank_scores_available=False`,输出的 report status 是 `blocked_requires_masked_bank_scoring`,报告里硬编码写着"This does not establish held-out RTAV-bank gains";只有当外部提供 masked-bank scores 时才会打分到"complete",中间状态是 `predicate_complete_document_blocked`。同一路径下的 `source_span_rtav_leakage_diagnostic.py` 默认 `leakage_gate=missing`,首段固定写"Full-bank rows are useful tradeoff diagnostics, but they do not establish unseen-schema generalization"。
- **修哪一边**:两边都不用修。这是刻意设计——脚本状态机把"没有做 heldout"这件事变成一个必须显式打开的开关,任何 downstream reader 打开报告都会看到大字提示。
- **为什么**:这是签收版拿去应付"unseen schema"追问的兜底证据。面试问到"你们 RTAV 泛化怎么保证"时,直接回答:主 claim 不含 unseen-schema 泛化;工具链层面默认阻塞出报告,写死了"does not establish held-out RTAV-bank gains",不给自己作弊留口子。

---

### §5.8【C 类,维持现状但面试要提】"agent-adjudicated" 与"human-labeled"的严格区分

- **论文说什么**:E4 label audit 的 300 行 / 15 cell / seed 20260610 会在文本里出现"adjudicated"字样。
- **代码做什么**:`validate_agent_adjudication_provenance` 显式检查 `label_source` 字段必须等于 `agent-adjudicated`,且 `schema_note` 必须包含 "not human-labeled";任何把 "human" 或 "human-labeled" 写进 provenance 字段的 artifact 会被 validator 拒收。
- **修哪一边**:不用修。这是 §2 §5 讨论的"避免把 agent 判决包装成 human labeling"的硬门禁。
- **为什么**:面试和 rebuttal 里被追问"你们的标注是谁做的",标准答案是"agent-adjudicated,写死在 validator 里禁止用 human-labeled 措辞";这条不是不一致,是刻意设计的一致——只是需要在面试里主动把这条设计说清,不然容易被误认为审稿人可以"自己解读"。

---

### §5 收尾:面试可背的一句话总结

- **必修论文的两条(A 类)**:RTAV 路由方向(bank-first 而不是 dictionary-first),以及 E1/E2/DeepSeek 系列的 metric label(PASS-F1 vs SU-F1)。
- **补澄清的四条(B 类)**:阈值 δ=0.5 是操作点不是最优,V4 cascade 只是 rebuttal 扩展,direction-sensitive 增益不是"集中",backbone 一致性仅限 direction-sensitive 方向。
- **刻意为之的两条(C 类)**:RTAV heldout 默认阻塞,agent-adjudicated 不可包装成 human-labeled。

以上 8 条已经全部在 `VERIFICATION.md` / `REVERIFICATION.md` / `FINAL_NUMBER_CROSSCHECK.md` 里有对应冻结证据;rebuttal 的文字都已按 A/B 修好,只有论文正文需要在 camera-ready 阶段同步修 §5.1、§5.2 两条硬漂移与 §5.3–§5.6 四句限定语。

---

**确认后进 §6:已知薄弱环节**。§6 会把 §2–§5 里逻辑上仍然可以被 reviewer 追打的地方集中列出,每条给出"薄弱在哪、为什么现在没修、如果被追问怎么回应";与 §5 的分工是,§5 是"文字与实现漂移",§6 是"实现本身的边界与短板"。题目保留。

## §6 已知薄弱环节

§5 讲"论文写的和代码做的不一致";§6 讲"代码本身、benchmark 本身、实验设计本身,仍然可以被 reviewer 或面试官继续追打的地方"。每条给出三件事:**薄弱在哪 / 为什么当前没修 / 被追问时怎么回应**。10 条,按被打的概率从高到低排。

---

### §6.1 RTAV bank 的 unseen-schema 泛化没有实测

- **薄弱在哪**:主 pipeline 的 bank 覆盖了 benchmark 里全部 128 个谓词(V3 已冻结),等于说 benchmark 上跑出来的 RTAV 增益,都是在"bank 见过这个谓词"的情况下拿到的。unseen schema 的泛化能力(bank 没见过的新谓词、跨领域迁移)在主实验里没有实测。
- **为什么当前没修**:做真正的 heldout 需要给每个 predicate fold 训练一次"mask 掉该 predicate 后的 bank",工程量大;并且我们的主 claim 本来就是"controlled benchmark 上的 controlled diagnostic",不含 unseen-schema 泛化。
- **被追问时怎么回应**:主 claim 不含 unseen-schema 泛化;`source_span_rtav_heldout.py` 默认输出 status=`blocked_requires_masked_bank_scoring`,报告里写死"This does not establish held-out RTAV-bank gains";`source_span_rtav_leakage_diagnostic.py` 默认 `leakage_gate`=missing、首段写死"do not establish unseen-schema generalization"。工具链层面就把这一块封死,不让自己糊过去。如果 reviewer 强要 unseen-schema 结论,只能加做实验。

---

### §6.2 主 benchmark 是合成负例,不是自然出错分布

- **薄弱在哪**:15,000 行 benchmark 由 4 类合成负例(`fake_span` / `object_replacement` / `subject_replacement` / `predicate_mismatch` × 3000)+ 3000 `gold_positive` 构成。这四类扰动是我们造出来的,不是 KG 抽取模型真实犯的错;真实场景下的错误分布(list/aggregation error、context carryover、malformed relation 等)可能和 benchmark 分布不一样。
- **为什么当前没修**:自然错误的分布需要大量人工标注 + 多个抽取模型的实际输出对比,不是一篇论文能完全兜住的规模;benchmark 造成合成数据是为了拿到干净的 confusion matrix。
- **被追问时怎么回应**:两条兜底:一是 natural noise 383 行 pilot(§4.9),TripleChecker SU-F1 0.6471、Fixed-template 0.6608,doc-clustered 95% CI 分别 [0.5636, 0.7204] 与 [0.5827, 0.7278],**overlap 掉了**——我们主动报告"在自然分布上不比强 baseline 显著更好";二是 failure taxonomy 明确把 `span_not_copied` / `semantic_false_pass` / `context_carryover` / `list_or_aggregation` 等真实错误类型列出来,不假装 benchmark 已经全覆盖。

---

### §6.3 δ=0.5 是"选定的操作点",不是"学出来的最优点"

- **薄弱在哪**:主表用 fixed@0.50 报 TripleChecker 主行(`hall_f1`=0.8015);同一曲线上 best HALL-F1 能到 0.8998,但 `pass_recall` 会从 0.807 塌到 0.252,不适合部署。reviewer 会问"为什么就是 0.5,不是 0.6"。
- **为什么当前没修**:0.5 是先验的、可解释的、跨数据集通用的默认阈值;做 threshold learning 会引入 dev-set,把"零学习成本"这条卖点也丢掉。
- **被追问时怎么回应**:两条:(a) supported-loss budget 分析(§4.4:25/50/100/250/500 supported-loss 分别对应的最佳阈值)让下游用户按自己的 supported-loss 预算选阈值,不是我们替他们钦定;(b) prevalence policy analysis 给出不同 hallucination prevalence 下的最优阈值曲线。0.5 是"通用默认",不是"最优";主表把这两行并列摆(fixed@0.50 与 best HALL-F1)已经是承认这一点。

---

### §6.4 三个 NLI 骨干上 SU-F1 range=0.063,超过自己给的 0.02 稳定性判据

- **薄弱在哪**:E2 的 `results.csv` 与 `reverification_r2_results.csv`:110M/mDeBERTa/330M SU-F1 分别 0.8535/0.8879/0.8248,range=0.063075,超过 0.02;overall bank-vs-fixed delta 分别 +0.010/+0.023/-0.015,330M 是负的;换句话说主 claim "换骨干仍然赢"跨模型不成立。
- **为什么当前没修**:如果我们说"backbone-invariant",直接被反例打死;所以只能收紧措辞。
- **被追问时怎么回应**:按 `VERIFICATION.md` V2 已冻结的 safe wording:absolute 表现和 overall delta 会随骨干变,但 direction-sensitive 子集上的 gain 三个骨干都是正的(+0.070/+0.086/+0.047,4.7–8.6 SU-F1 点)。**Claim 从"整体一致"收缩到"direction-sensitive 一致"**;不硬撑。

---

### §6.5 direction-sensitive 增益并非"集中"

- **薄弱在哪**:E4 若被读成"RTAV 提升主要来自 direction-sensitive 关系",立刻被 E4-a 自己的 `conclusion.md` 反打:非-direction-sensitive 子集 delta +0.119,反而**大于** direction-sensitive 的 +0.100。
- **为什么当前没修**:文字问题,不是数据问题。
- **被追问时怎么回应**:direction-sensitive 是"最能凸显方向敏感优势"的子集,不是"增益唯一来源"的子集;E4-a conclusion 已明确写"the gain is not concentrated on the direction-sensitive subset",两个子集都有正 delta,只是非-direction-sensitive 那边更大一点。

---

### §6.6 all-reject SU-F1 anchor 是 0.888,DeepSeek 的 0.917 只高出 3 分

- **薄弱在哪**:benchmark 的 4:1 unsupported:supported prevalence 使得"全部输出 `NOT_SUPPORTED`"这一 trivial baseline 的 SU-F1 就有 0.888888888888889。DeepSeek span=0.917,只比 all-reject 高约 3 分;DeepSeek 在 91.1% 的 span 行、86.3% 的 full 行都是 `NOT_SUPPORTED`,策略上非常接近 all-reject。
- **为什么当前没修**:这是 prevalence 决定的下界,benchmark 设计时就承担了。
- **被追问时怎么回应**:R1 明确把 anchor 写在报告里(`REVERIFICATION.md` R1 第二段:"the high SU-F1 is partly driven by strict rejection, so PASS recall must remain beside it")。**永远和 PASS-recall 一起报**:DeepSeek 的 PASS-recall 只有 0.368/0.337,说明它是靠"多拒绝"堆出的 SU-F1,不是"更准"堆出的。这条正好回应"你们为什么不叫大模型":大模型策略性极端,PASS 端塌掉了。

---

### §6.7 V4 boundary cascade 的 +1.46 SU-F1 是事后选出来的窗口

- **薄弱在哪**:V4 把 TripleChecker score∈[0.4, 0.6] 的 191/3000(6.37%)行送给 DeepSeek 复核,得到 SU-F1 0.8091→0.8237(+1.46)、PASS-F1 0.5448→0.5541、discordant wins 69/20、p=1.777e-07。[0.4, 0.6] 这个窗口是我们挑的,窗口选择本身没有独立 held-out 校准。
- **为什么当前没修**:V4 是 rebuttal-only extension,不是主 pipeline;rebuttal 阶段我们只想演示"选择性 cascade 是可行的",不是主张一个最优窗口。
- **被追问时怎么回应**:一句话说清窗口选择性质——[0.4, 0.6] 是"分数距离决策边界最近的行"的自然定义,不是从 grid search 出来的;paired 二项检验 p=1.78e-07 是在这 191 行上做的,不是 cherry-pick 出来的 p 值;API 成本只涨 6.37%。如果 reviewer 要一个 heldout 窗口验证,可以承诺"下一版加";目前这条只作为 rebuttal 里的 sanity check,而不是主结论。

---

### §6.8 natural noise 383 行是"pilot 规模",不是决定性证据

- **薄弱在哪**:natural noise 从 Qwen2.5-3B 本地跑出的 59 三元组扩到 383,双向 95% CI 都很宽([0.5636, 0.7204] vs [0.5827, 0.7278]);point estimate 上 TripleChecker(0.6471)甚至比 Fixed-template(0.6608)低 0.014,虽然 CI overlap。
- **为什么当前没修**:自然错误标注非常贵;383 行是我们能接受的取样规模上限。
- **被追问时怎么回应**:主动报告 pilot 结论——"在这个自然噪声切片上,TripleChecker 和最强 scalar baseline 的置信区间重合,点差在采样不确定性内"(R3 已冻结这个措辞)。**不是"RTAV 输了",是"这个规模看不出显著差别"**;主 claim 是 benchmark 上的 controlled diagnostic,natural noise 只是补充证据。这条比"避而不谈"要安全得多。

---

### §6.9 Layer-1 exact substring 对中文 span 变体不鲁棒

- **薄弱在哪**:SAR(Span Authenticity Rate)是 {0, 1} 硬门,要求 span 逐字符出现在源文中;E3 已经做了 exact vs Jaccard@0.9 对比,Jaccard@0.9 会把 543/3000=18.1% 的真实 span 误杀,SU-F1 从 0.9137 掉到 0.8542;换个中文表面变体(全半角、繁简、"的"字省略、括号写法)可能直接被 SAR=0 判死。
- **为什么当前没修**:任何"软"span 匹配都会引入 false-authentic(把不在源文的 span 判为 authentic),这是 §4.14 里 E3 的核心结论——**partial 只是"admit 6/3000"级别**,但 Jaccard@0.9 换来的收益不足以补上 18.1% 的 false-kill。
- **被追问时怎么回应**:E3 表格已冻结:exact-match SU-F1 0.9137 vs Jaccard@0.9 SU-F1 0.8542;partial admits 6/3000;exact 的 false-kill 是 0/3000。exact-substring 是**明确的、可复现的、no-false-authentic**的判别边界;下游如果需要更宽松的字符匹配,应当在应用层做规范化,不应把边界模糊化。

---

### §6.10 15,000 行 benchmark 是三个中文数据集,不是全域

- **薄弱在哪**:benchmark 抽自 cmeie(4030) / duie(3930) / finre(4010) 三个中文 KG 数据集(V2 已冻结分布);医学 / 通用百科 / 金融三个域,数量不太均衡且都是中文。跨语言、跨小语种、跨新兴领域(法律、代码、生化)未覆盖。
- **为什么当前没修**:主 pipeline 依赖中文 NLI 骨干,英文 / 多语言需要换 backbone;跨领域需要新 benchmark。
- **被追问时怎么回应**:主 claim 已经在题目里限定"中文 KG 抽取",不外推到跨语言;E2 加做 mDeBERTa(多语言骨干)是为了给"未来向英文迁移"留一个证据点(SU-F1 0.8879,在三个骨干里反而最高);跨领域外推**不在主 claim 内**,这一条不打算硬撑。

---

### §6 收尾:面试可背的一句话总结

- **必须主动承认的四条**:unseen-schema 泛化没实测(§6.1)、benchmark 是合成负例(§6.2)、backbone 有 0.063 range(§6.4)、natural noise 只是 pilot(§6.8)。
- **主动收紧措辞的三条**:δ=0.5 是操作点不是最优(§6.3)、direction-sensitive 不是唯一增益来源(§6.5)、V4 cascade 是 rebuttal-only 的事后窗口(§6.7)。
- **设计里就承认的三条**:SU-F1 有 0.888 anchor 所以必须和 PASS-recall 一起看(§6.6)、Layer-1 exact substring 换取"零 false-authentic"(§6.9)、benchmark 局限于中文三个域(§6.10)。

面试回答范式:被追问某条时,先承认(不狡辩)→ 说明当前设计选择的理由 → 指出对应的兜底证据在 artifact 的哪一份文件里 → 如果 reviewer 强要新结论,坦白只能加做实验。

---

## §1–§6 全套完成

至此六大节全部走完:

1. §1 整体代码结构
2. §2 逐模块深挖(M1–M9)
3. §3 关键设计决策推理链
4. §4 实验逐一还原(17 小节)
5. §5 论文↔代码不一致点(8 条,分 A/B/C 类)
6. §6 已知薄弱环节(10 条,按被追打概率排序)

**确认后进摄入阶段**:把这六节全部同步到 `pages/TripleChecker.md`(所有确认题与解释一并入页),然后执行 CLAUDE.md 里规定的收尾三步——`build_index.py` → `check_health.py` → `git commit`。摄入的时候我会把长节按 §-小节切分,方便页面结构不塌;如果你希望某一节单独拆成独立子页(比如 §4 实验还原、§6 薄弱环节这两节都比较大),现在告诉我怎么切。

## 交叉引用

- [[知识图谱 KG]]
- [[知识图谱构建流程 KG Construction Pipeline]]
- [[文本蕴含与自然语言推理 NLI]]
- [[KG-RAG 工作原理]]
- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[归因评测 Attribution]]
- [[可验证性 Verifiability]]
- [[RAGChecker]]

## 更新记录

- 2026-07-20: 从占位页扩为完整项目备忘(问题定义 / 方法 / 贡献边界 / 实验 / 追问 / 电梯陈述),用于保研套磁与面试脱稿准备
- 2026-07-20: 追加「七、代码级深度回顾」,含 §1 整体代码结构 / §2 逐模块深挖 M1–M9 / §3 关键设计决策推理链 / §4 实验逐一还原 / §5 论文↔代码不一致点 / §6 已知薄弱环节,全部保留确认题
