---
摘要: Google Dremel/BigQuery 提出的嵌套列式宽表反规范化数仓范式
来源: 对话记录 2026-07-14
信度: 中
首次记录: 2026-07-14
tags: [前沿]
---

# BigQuery Dremel 宽表建模 BigQuery-Dremel

## 核心内容

Dremel 是 Google 在 VLDB 2010 论文《Dremel: Interactive Analysis of Web-Scale Datasets》中提出的**交互式列式分析引擎**,后作为 **BigQuery** 商业化。它对外倡导的建模范式即"**宽表(wide table with nested & repeated fields)**":把传统数仓的星型/雪花模型**反规范化**到一张事实表,把维度提前展平进事实表,并用 `RECORD / REPEATED`(基于 Protocol Buffers 的嵌套模型)保留一对多关系,避免笛卡尔展开。

之所以推荐反规范化,是因为在列式存储 + shared-nothing MPP 引擎上,**JOIN 代价远高于宽扫描**,而"只读用到的列"让宽表几乎无 IO 惩罚。存储层面,Dremel 提出的**列式嵌套编码**——每列存 `(value, repetition_level, definition_level)` 三元组——正是后来开源 **Parquet** 沿用的核心思想。工程上宽表通常按时间分区(Partition)、按用户/事件聚簇(Cluster),冷热分层。

与 [[Google Bigtable 宽表模型 Bigtable]] 的"宽"不同:Bigtable 的宽是**在线服务的稀疏动态列**,Dremel/BigQuery 的宽是**离线分析的严格 schema + 嵌套列**。

## 和我的项目的关系

CoMaGRAG / GSAD 的评测与审计数据(每条问题、每个算子、每次 LLM 调用、每次归一化结果)天然是"多层嵌套 + 一对多",目前分散在若干 JSON/Markdown 中,后续如需做交互式分析,BigQuery-Dremel 的"嵌套宽表 + 列式"范式是首选建模路线:一条 run 记录展平所有阶段的输入/输出/中间证据到 REPEATED RECORD,而不是拆多张小表 JOIN。

## 交叉引用

- [[前沿趋势 Frontier]]
- [[Google Bigtable 宽表模型 Bigtable]]
- [[RAG 评测指标 EM Recall MRR]]

## 更新记录

- 2026-07-14: 首次建页
