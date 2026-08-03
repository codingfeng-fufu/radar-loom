---
摘要: 用GPT-4合成数据微调Flan-T5，以GPT-4 1/400成本完成 grounding 文档级事实核查
来源: https://arxiv.org/abs/2404.10774 (EMNLP 2024)
信度: 高
首次记录: 2026-08-03
tags: [可信度, RAG, 评测, TripleChecker]
---

# MiniCheck 高效事实核查

## 核心内容

MiniCheck 是 Tang、Laban、Durrett（UT Austin / Salesforce AI Research，EMNLP 2024）提出的句子级 grounding 事实核查器：给定声明 $c_i$ 和一组支撑文档 $\mathcal{D}_i = \{D_{i,1},\dots,D_{i,|\mathcal{D}_i|}\}$，判别器 $M(D_{i,j}, c_i)\in\{0,1\}$ 输出 supported / unsupported，句子整体标签取 $\max_j M(D_{i,j}, c_i)$。它解决的问题是：用 GPT-4 做 claim-by-claim 核查虽然准，但一段 110–150 词的传记会拆出 26–41 个原子事实、每个对 5 篇文档核查，一次回答要 130–205 次蕴含调用，成本与延迟无法接受。MiniCheck 的关键做法是用 GPT-4 从零合成两类专门针对"多事实 + 多句推理"的训练数据，再在 Flan-T5-large（770M）上微调，在统一基准 LLM-AggreFact 上拿到 74.7 balanced accuracy，与 GPT-4（75.3）和 Claude-3 Opus（74.1）持平，但推理成本只要 \$0.24，比 GPT-4 的 \$107 便宜约 400 倍。

## 方法细节

### 任务形式化

- 输入：声明 $c_i$（通常是 LLM 生成的一句话）与对应文档集 $\mathcal{D}_i$。
- 输出：二分类标签 $y_i \in \{0,1\}$，1 表示存在某篇文档支撑该声明，0 表示全部不支撑。
- 两个假设：(a) 每条被支撑的声明都能在**单篇**文档内找到依据；(b) 句子可独立核查，代词等上下文依赖通过可选的 decontextualization 预处理解决。
- 评测指标用 balanced accuracy：

$$
\mathrm{BAcc} = \frac{1}{2}\left(\frac{\mathrm{TP}}{\mathrm{TP}+\mathrm{FN}} + \frac{\mathrm{TN}}{\mathrm{TN}+\mathrm{FP}}\right)
$$

之所以不用普通准确率，是因为数据中 supported 占多数，需要平衡假阳与假阴。

### 为什么现成数据不够

作者指出现有专用核查器（AlignScore、SummaC、QAFactEval、DAE 等）有两个共性短板：(1) 一句话里常有多个原子事实，模型容易只验证其中一个就放过整句；(2) 一个事实的证据可能散落在文档的多句话里，需要跨句综合推理。通用 NLI 数据（MNLI、ANLI）不教这两种能力，所以模型尺寸再大也补不回来——论文里 11B 的 T5-NLI-Mixed 平均 BAcc 只有 61.0，反而低于 355M 的 AlignScore（70.4）。

### 合成数据方法一：C2D（Claim-to-Doc）

从人工写的 claim 出发，合成"必须跨句推理才能判定"的文档：

1. **Claim 分解**：用 GPT-3.5 把 $c$ 拆成原子事实集 $\mathbf{a}=\{a_1,\dots,a_l\}$。
2. **原子事实扩展**：对每个 $a_i$，GPT-4 用 4-shot 生成句子对 $\mathrm{SentPair}(a_i)=(s_{i,1},s_{i,2})$，使得 $a_i$ 被支撑**当且仅当**两句信息合并。
3. **支撑文档生成**：$\mathrm{PassageGen}(\mathbf{s})$ 用自己的话写出包含所有句子对的文档 $D$，得到 $(D,c,1)$。
4. **非支撑文档生成**：从句对中抽掉一句 $s_{i,j}$ 重新生成 $D'_{a_i\setminus j}$，并用 GPT-4 做一次短上下文蕴含校验，确认 $a_i$ 确实无法由剩余信息推出，得到 $(D',c,0)$。
5. **幂集增广**：对 $\mathbf{a}$ 的所有非空子集 $\mathbf{a}'$ 做 $\mathrm{Merge}(\mathbf{a}')$ 生成子声明 $c'$。子声明在 $D$ 上标签为 1；在 $D'_{a_i\setminus j}$ 上，标签取决于 $a_i$ 是否落在 $\mathbf{a}'$ 中——这就构造了"只改文档里一句话、标签翻转"的对比集（contrast set），强迫模型关注决策边界上的具体原子事实，而不是靠表层相关性判分。

### 合成数据方法二：D2C（Doc-to-Claim）

C2D 的文档是合成的，可能与真实分布有差距。D2C 反过来从真实文档出发：

1. **分块摘要**：把真实文档切成三段 $D_1,D_2,D_3$，GPT-4 为每段生成一句摘要 $\{c_1,c_2,c_3\}$，默认 $(D_i,c_i,1)$。
2. **分解与子声明增广**：与 C2D 同样做原子事实分解和幂集合并。
3. **文档-声明增广**：在摘要里注入错误生成负样本（类似 SummEdit 思路）。
4. **跨文档-声明增广**：把不同块的信息错误地拼到同一句摘要里，制造"信息真实但组合错误"的难负例。

最终训练集约 35K 样本（C2D + D2C 各约 7K 合成 + ANLI），远小于 AlignScore 的 4.7M。

### 模型变体

- **MiniCheck-Rbta**：RoBERTa-large（AlignScore 权重初始化），355M，14K 微调数据。
- **MiniCheck-Dbta**：DeBERTa-large，355M，35K。
- **MiniCheck-FT5**：Flan-T5-large，770M，35K，效果最好。

## 关键实验结果

在 LLM-AggreFact（10 个数据集、约 13K 测试句子，涵盖 AggreFact CNN/XSum、TofuEval、Wice、Reveal、ClaimVerify、FactCheck-GPT、ExpertQA、LFQA、MeetB）上，无阈值调优时的平均 BAcc：

| 模型 | 参数量 | Avg BAcc | 13K 测试成本 |
| --- | --- | --- | --- |
| GPT-4 | — | 75.3 | \$107 |
| **MiniCheck-FT5** | **770M** | **74.7** | **\$0.24** |
| Claude-3 Opus | — | 74.1 | \$165 |
| Mistral-Large | — | 73.4 | \$90.2 |
| MiniCheck-Rbta | 355M | 72.7 | \$0.20 |
| MiniCheck-Dbta | 355M | 72.6 | \$0.20 |
| AlignScore | 355M | 70.4 | \$0.20 |
| GPT-3.5 | — | 69.6 | \$4.75 |
| SummaC-ZS | 60M | 67.9 | \$0.85 |
| T5-NLI-Mixed | 11B | 61.0 | \$7.39 |

消融结论（论文 Table 6 / Figure 5）：

- 去掉 C2D 后 MiniCheck-FT5 平均掉到 72.7，去掉 D2C 掉到 71.5，两者都去掉只剩 ANLI 时暴跌到 59.9——合成数据不是锦上添花，而是主要性能来源。
- 简化版合成流程（C2D-Simp / D2C-Simp，直接让 GPT-4 编正负文档）几乎学不到目标能力，FT5-D2C-S 在 C2D 留出集上甚至低于随机；说明"句对设计 + 抽句 + 幂集对比"这一整套结构化构造是关键，不是"用 GPT-4 造数据"本身。
- 仅在 7K 精心构造的合成样本上训练，能超过在 163K ANLI 上训练的同尺寸模型。

## 反直觉发现：claim 分解没必要

论文第 7 节重新审视了"先把句子拆成原子事实、再逐个核查"的主流做法（FActScore、ChatGPT-Agent 等）。结果：在 LLM-AggreFact 上，分解让 GPT-4 平均 BAcc 从 75.3 微涨到 75.6（+0.3），却让推理成本翻倍到 \$212；MiniCheck-FT5 反而从 74.7 掉到 73.3（−1.4）。Decontextualization 同样没有稳定收益。作者结论是：只要训练数据让模型学会"内部检查所有原子事实"，外部的显式分解步骤在 entailment 阶段就是冗余的；但分解在**检索阶段**可能仍然必要（FactCheck-GPT 这类设置要先按原子事实去搜证据）。

## 适用条件与局限

- **英文为主**：训练与评测均为英文，迁移到其他语言（尤其是主谓宾结构差异大的语言）没有保证；本库 [[TripleChecker]] 页就记录了 MiniCheck 在中文 span-triple 设置下基本失效。
- **句级、单文档可支撑假设**：对真正需要跨多份文档拼证据才能判定的 claim，论文通过"上下文拼接"绕过，但未系统评测其上限。
- **二分标签丢弃 contradiction 类**：作者认为 benchmark 中矛盾样本稀少，但在冲突检测场景下这个简化可能漏判。
- **依赖 GPT-4 合成数据**：小模型能力上限受教师模型制约；合成流程的 Prompt 工程较重，复现需要 Appendix H 的全部提示。
- **不解决检索问题**：MiniCheck 假定 $\mathcal{D}_i$ 已经给好，是核查器不是检索器；上游召回差时它无能为力。

## 和我的项目的关系

- **[[TripleChecker]]**：最直接相关。TripleChecker 做中文 KG triple 的 source-faithfulness 审计，任务粒度比 MiniCheck 更细（三元组 vs 句子），但 pipeline 同构——都在做"声明 vs grounding 文档的二分类蕴含"。TripleChecker 论文 Q5 已明确把 MiniCheck 列为对比方法，并报告其在中文 setting 下基本失效，原因是中文谓词常由名词承担、通用 NLI 模板方向反转。MiniCheck 提供的可借鉴点是：(a) 用"句对必须合并才能支撑"的合成数据教模型跨句推理；(b) 用幂集构造对比集，让模型对单个原子事实缺失敏感——这两点对 TripleChecker 的中文难负例合成有直接参考价值。MiniCheck 不适合直接当中文核查器，但适合作为英文基线和合成数据方法论参考。
- **[[EvidenceFirst]]**：MiniCheck 是"可验证性落地到运行时组件"的一个范本——它不是事后评测指标，而是可以嵌进 RAG / 摘要流水线做实时过滤的轻量判别器，符合 EvidenceFirst 主张的"证据可机器核验"。
- **[[CoMaGRAG]] / 其他 RAG 项目**：MiniCheck 可作为生成后的 attribution filter 插入 RAG 系统，对答案逐句打 supported/unsupported 标签，比用 LLM-as-judge 自检便宜两个数量级；但需要先在领域数据上做适配验证。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[检索增强生成 RAG-GraphRAG]]
- [[评测方法 Evaluation Methods]]
- [[归因评测 Attribution]]
- [[文本蕴含与自然语言推理 NLI]]
- [[引用召回与精确率 Citation Recall Precision]]
- [[知识接地 Grounding]]
- [[RAGChecker]]
- [[TripleChecker]]

## 更新记录

- 2026-08-03: 首次建页，依据 arXiv:2404.10774v2（EMNLP 2024）整理方法、LLM-AggreFact 基准与关键结果
