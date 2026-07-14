---
摘要: Google 2006 论文提出的稀疏分布式多维排序 Map 宽列存储
来源: 对话记录 2026-07-14
信度: 中
首次记录: 2026-07-14
tags: [前沿]
---

# Google Bigtable 宽表模型 Bigtable

## 核心内容

Bigtable 是 Google 在 OSDI 2006 论文《Bigtable: A Distributed Storage System for Structured Data》中提出的**分布式稀疏宽列存储系统**,为 Web 索引、Google Earth、Analytics 等 PB 级在线数据服务而设计。它把一张表建模为一个稀疏、分布式、持久化的多维排序 Map:

$$(\text{row key},\ \text{column family:column qualifier},\ \text{timestamp}) \rightarrow \text{value}$$

关键设计:**行键**任意字符串按字典序全局排序,行内更新原子;**列族**在建表时声明且数量少,**列限定符**可动态扩展到成百上千,这就是"宽"的直接来源;**cell 保留多版本**,GC 可配。表按行键切分为 **tablet**,单 tablet 由一个 tablet server 负责读写;数据落于 GFS 上的 SSTable,写入走 memtable + SSTable 合并(即经典 LSM Tree 思路),元数据由 Chubby 分布式锁服务托管。

在业界谱系上,Bigtable 是 NoSQL 宽列存储的开山之作,**HBase / Cassandra 的数据模型直接沿用它**;Google 云上以 **Cloud Bigtable** 商业化对外服务。

## 和我的项目的关系

暂无直接关联。CoMaGRAG 与 GSAD 目前的数据规模用不到 Bigtable 级别的存储,但其"稀疏列 + 多版本 cell"的建模思路,可作为图谱事实存储或答案权利索引在数据规模上升后的候选路线之一,值得留意。

## 交叉引用

- [[前沿趋势 Frontier]]
- [[BigQuery Dremel 宽表建模 BigQuery-Dremel]]
- [[主流知识图谱 Mainstream KGs]]

## 更新记录

- 2026-07-14: 首次建页
