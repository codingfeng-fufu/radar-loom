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

**面试锚点数字**:EM 从 0.47 提到 0.79、Table 3 F1 0.811、MiniCheck F1 0.14、Layer 2 recall 0.948。其他数字可以说"记不清,详细查 PROJECT_STATUS 表"。

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
