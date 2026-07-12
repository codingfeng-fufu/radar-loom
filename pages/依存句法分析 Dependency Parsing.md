---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [KG]
---

# 依存句法分析 Dependency Parsing

## 核心内容

依存句法分析是分析句子里词和词之间的语法依存关系的任务，用有向图表示，边从修饰词指向被修饰词，边上标注关系类型。KG 抽取中一个重要观察是：两个实体在依存树里路径越短，越可能有直接关系。常用工具包括 Stanford Parser 和 SpaCy。

## 和我的项目的关系

依存句法分析是 OpenIE 时代关系抽取的核心技术，虽然现在大模型直接端到端抽取三元组，但依存树的思路仍然有用：[[TripleChecker]] 里可以用依存路径长度作为置信度特征——如果头实体和尾实体在原文本的依存树里相隔太远，那这个三元组可能是幻觉；[[EvidenceFirst]] 里路径搜索本质上就是把文本层面的依存关系映射到 KG 层面的语义关系。

## 交叉引用

- [[知识图谱 KG]]
- [[开放信息抽取 OpenIE]]
- [[词性标注 POS Tagging]]
- [[实体消歧 Entity Disambiguation]]
- [[TripleChecker]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-04: 首次建页
