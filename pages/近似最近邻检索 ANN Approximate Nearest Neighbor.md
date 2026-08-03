---
摘要: 以召回换延迟的大规模高维向量检索，IVF/HNSW/PQ 是 FAISS 的三大支柱
来源: https://arxiv.org/abs/1702.08734
信度: 高
首次记录: 2026-08-03
tags: [基础, RAG]
---

# 近似最近邻检索 ANN Approximate Nearest Neighbor

## 核心内容

ANN（Approximate Nearest Neighbor，近似最近邻）检索解决的是"在百万到十亿级、维度数百到数千的稠密向量库里，快速找出与查询向量最近的 $K$ 个"这一问题。精确 KNN 暴力扫描的时间是 $O(Nd)$，在 $N=10^9$、$d=128$ 时即使全放到 GPU 也无法实时返回；ANN 通过在**召回率—查询延迟—内存占用**三角上做有控制的让步，把单次查询压缩到对数级或常数级距离计算。FAISS（Johnson, Douze, Jégou, "Billion-scale similarity search with GPUs", arXiv:1702.08734, 2017）是 Meta 开源的向量检索库，把三大类方法——IVF 倒排划分、PQ 乘积量化压缩、HNSW 图索引——组合成可拼装的索引工厂，是目前 RAG 向量召回、图像检索、推荐召回的工程事实标准。[[K近邻 KNN K-Nearest Neighbors]] 讲的是"什么是最近邻"，本页讲"怎样在大数据上快速近似地找到它"。

## 问题定义与度量

给定库向量集 $\mathcal{D}=\{x_i\}_{i=1}^N \subset \mathbb{R}^d$、查询 $q$ 和距离度量 $d(\cdot,\cdot)$，精确 KNN 返回

$$\mathcal{N}_K(q)=\{x_i \mid d(q,x_i) \text{ 最小的 } K \text{ 个}\}.$$

ANN 索引返回候选集 $\hat{\mathcal{N}}_K(q)$，允许其中一部分不是真邻居，用 **Recall@K** 衡量质量：

$$\mathrm{Recall@K}(q)=\frac{|\mathcal{N}_K(q)\cap\hat{\mathcal{N}}_K(q)|}{K}.$$

工程上还会看 1-recall@1（最近邻是否找对）和 Recall@R, $R>K$（取更大候选池再精排时的召回，常用于两阶段检索）。FAISS 基准与 ANN-benchmarks 都以 Recall 对查询延迟（QPS 或 ms/query）的曲线作为索引选型主图。

距离度量上，L2（欧氏距离）和内积（Inner Product，归一化后等价余弦）是 FAISS 一等支持的两种；余弦检索通常先把向量 L2 归一化再用 `IndexFlatIP`。

## 方法族谱

高维下精确树索引（KD-Tree、Ball-Tree）会退化到接近暴力（[[K近邻 KNN K-Nearest Neighbors]] 已讨论），ANN 因此发展出三条技术路线，FAISS 的索引就是这三条线及其组合：

| 路线 | 代表方法 | 核心思想 | 典型代价 |
|---|---|---|---|
| 空间划分（cell-probe） | IVF、k-means Voronoi、LSH | 把空间切成单元，查询只看邻近的几个单元 | 查询扫描比 $\approx\text{nprobe}/\text{nlist}$ |
| 量化压缩 | PQ、OPQ、SQ | 把向量压成短码，在压缩域算近似距离 | 存储从 $4d$ 字节降到 $M$ 字节量级 |
| 图导航 | HNSW、NSW、Vamana | 在向量上建近邻图，贪心搜索沿图收敛 | 查询 $O(\log N)$ 次距离计算 |

这三条路线并不互斥：IVF 负责"少看"，PQ 负责"看的时候每条更省内存/更快"，HNSW 可以独立用，也可以当 IVF 的粗量化器或底图。FAISS 的 `index_factory` 字符串就是这些组件的拼装 DSL。

## FAISS 核心索引

### Flat：精确基线

`IndexFlatL2` / `IndexFlatIP`（factory `"Flat"`）不做任何索引，暴力扫描全库，$O(Nd)$。它是所有近似索引的召回上限基线，也充当 IVF/HNSW 的粗量化器和底存。无训练、无参数、支持 GPU；需要 `add_with_ids` 时外包一层 `IDMap,Flat`。

### IVF：倒排划分

`IndexIVFFlat`（factory `"IVFx,Flat"`，$x$ 是 nlist）先用 k-means 把空间聚成 `nlist` 个 Voronoi 单元，每个库向量落入最近质心对应的倒排列表。查询时用粗量化器找查询所在单元，只扫描 `nprobe` 个邻近列表里的向量。扫描比例近似为 $\text{nprobe}/\text{nlist}$（实际因列表长度不均而偏高），漏检发生在"真邻居所在单元没被 probe 到"时。

关键经验法则（FAISS wiki "Faiss indexes"）：质心数取 $\text{nlist}\approx C\sqrt{N}$，$C$ 取约 10，以平衡"找质心"和"扫倒排"两段代价。`nprobe` 是查询时旋钮——调大提召回、降速度；`nprobe=nlist` 退化为暴力但更慢。

### PQ：乘积量化压缩

Product Quantization（Jégou, Douze, Schmid, IEEE TPAMI 2011, DOI 10.1109/TPAMI.2010.57）把向量 $x\in\mathbb{R}^d$ 切成 $M$ 个子向量 $x^1,\dots,x^M$（要求 $M\mid d$），每个子空间独立用 k-means 聚成 $2^{n_{\text{bits}}}$ 个质心（通常 $n_{\text{bits}}=8$，即 256 个），于是一个向量被压成 $M$ 个 1 字节码字，总码长 $M$ 字节。存储从 float32 的 $4d$ 字节降到 $M$ 字节，$d=128,M=32$ 时压缩 16 倍。

查询时用 **Asymmetric Distance Computation (ADC)**：查询本身不压缩，预计算查询到每个子质心的距离表 $d(q^j,c^j_k)$，库向量的近似距离由各子空间查表求和得到：

$$d(q,x)\approx\sum_{j=1}^{M}d\!\left(q^j,c^j_{\mathrm{code}_j(x)}\right).$$

全程不还原向量，距离计算变成 $M$ 次查表加法，CPU cache 友好。`IndexPQ`（factory `"PQMxnbits"`）是纯 PQ；`OPQ` 是先做一个正交旋转矩阵让各子空间方差更均衡，再 PQ，常能白拿几个点召回。

### IVF-PQ：组合拳

`IndexIVFPQ`（factory `"IVFx,PQy"`）是 FAISS 大规模场景最常用的索引：IVF 负责把扫描范围降到 $\text{nprobe}/\text{nlist}$，PQ 负责把每条残差向量压成 $M$ 字节。注意 IVF-PQ 量化的是向量相对其质心的**残差** $x-c_{\text{cell}}$，而不是原始向量，这能显著降低量化误差（即论文中的 IVFADC）。再叠加一个精排阶段就是 `IndexIVFPQR`（`"IVFx,PQy+z"`）：先用短码取大候选池，再用更多字节的 PQ 码重排。

### HNSW：分层近邻图

HNSW（Malkov & Yashunin, arXiv:1603.09320, IEEE TPAMI 2020）在向量上构建一个多层小世界图：上层是长程边、稀疏，下层是短程边、稠密。插入时从顶层贪心走到最接近的节点再下沉，查询沿图贪心扩展、用候选优先队列（beam search）收敛。三个参数：

- `M`：每个节点每层的邻居数，4–64 之间；越大越准但越占内存。
- `efConstruction`：建图时的搜索宽度，影响图质量。
- `efSearch`：查询时的搜索宽度，查询时调，越大召回越高越慢。

FAISS wiki 给出 HNSW 内存约 $(d\cdot 4 + M\cdot 2\cdot 4)$ 字节/向量（向量本身 $4d$ 字节 + 图边）。`IndexHNSWFlat` 不压缩底向量，`IndexHNSWSQ`/`IndexHNSWPQ` 再叠加标量/乘积量化。HNSW **不支持删除**（删点会破坏图结构），也不需要训练，但构建较慢、内存占用高。

### 其他常用组件

- **SQ（Scalar Quantizer）**：`SQ8`/`SQ4`/`SQfp16`，逐维量化到 8/4/16 bit，比 PQ 简单、精度损失通常可接受，常与 HNSW 搭配压内存。
- **LSH**：`IndexLSH` 把向量用随机旋转/紧框架投影成二值码，按汉明距离粗筛；FAISS wiki 明确指出纯 LSH 需要大量哈希函数、内存不划算，实践中已基本被 IVF/HNSW 取代。
- **GPU 索引**：FAISS 的核心贡献之一是让 k-selection（top-k）跑到理论峰值的 55%，GPU 暴力比当时 SOTA 快 8.5 倍（FAISS 论文摘要），并支持 GPU 版 IVF-PQ；单机 4 块 Titan X 可在 12 小时内构建 10 亿向量的 k-NN 图。

## FAISS 索引选型

FAISS wiki "Guidelines to choose an index" 给出的决策顺序（L2 为主）：

1. **查询很少（千到万次）**：构建成本摊不薄，直接用 `"Flat"` 暴力。
2. **要精确结果**：唯一选择是 `"Flat"` / `"IDMap,Flat"`。
3. **内存不紧张、数据集中等**：`"HNSW{M}"` 最快最准；或 `"IVF1024,PQ{N}x4fs,RFlat"`。
4. **内存有些紧张**：先聚类再用 Flat 底存，`"IVFx,...,Flat"`，用 nprobe 权衡。
5. **内存很紧张**：`"OPQ{M}_{D},...,PQ{M}x4fsr"`，OPQ 降维 + 4-bit PQ，$M/2$ 字节/向量。
6. **极致压缩**：RaBitQ 可压到每维 1 bit（$d/8+8$ 字节/向量）。

经验起点：$N<10^5$ 直接 Flat；$10^5$–$10^7$ 用 HNSW 或 IVF-PQ；$10^8$ 以上用 IVF-PQ + GPU 训练 + 调 nprobe；内存受限就叠 OPQ/SQ。

## 复杂度与权衡直觉

| 索引 | 建库 | 单次查询（近似） | 每向量存储 | 可删除 |
|---|---|---|---|---|
| Flat | $O(1)$ | $O(Nd)$ | $4d$ B | 是 |
| IVFFlat | k-means $O(\text{nlist}\cdot N\cdot d\cdot\text{iter})$ | $O((\text{nprobe}/\text{nlist})\cdot N\cdot d)$ | $4d+8$ B | 是 |
| IVFPQ | k-means + PQ 训练 | 查表求和，扫描比例同上 | $M+8$ B | 是 |
| HNSW | $O(N\log N)$ | $O(\log N)$ 次距离计算 | $4d+8M$ B | 否 |
| PQ | k-means（$M$ 个子空间） | $O(N\cdot M)$ 查表 | $M$ B | 是 |

三条权衡线：

- **召回 vs 延迟**：调大 `nprobe`/`efSearch`、增加 `M`、用更粗的 PQ 码，都是在这条线上移动。
- **内存 vs 召回**：从 Flat → SQ8 → PQ32 → PQ16 → OPQ+PQ4，内存递减、召回递减。
- **建库 vs 查询**：HNSW 建图慢但查询极快；IVF 训练快但查询依赖 nprobe；PQ 训练最久但查询又快又省内存。

## 适用条件、局限与常见误区

- **适用前提：向量在度量空间中有近邻结构**。ANN 的所有近似都建立在"近邻在空间上聚集"这一直觉上；若数据在高维下距离集中（维度诅咒）、最近邻与远邻不可分，任何索引都救不了召回，需要先换更好的嵌入或降维。
- **误区 1："HNSW 一定比 IVF-PQ 准"**。在同内存预算下，IVF-PQ + 精排的召回可以反超 HNSW，尤其在 $N$ 极大、底向量必须压缩时。选型要以自己数据上的 Recall-QPS 曲线为准，不能只看 ANN-benchmarks 默认配置。
- **误区 2："PQ 是有损压缩所以不能用于检索"**。ADC 不压缩查询，只压缩库向量，距离排序在子空间加性近似下仍高度保真；$n_{\text{bits}}=8$、$M$ 取够时召回损失通常很小，且可用 RFlat/PQR 精排补回。
- **误区 3："IVF 的 nlist 越大越快"**。nlist 过大时，粗量化器（找最近质心）本身的 $O(\text{nlist}\cdot d)$ 会成为瓶颈；FAISS 建议 $\text{nlist}\sim C\sqrt{N}$。
- **误区 4："ANN 索引本身解决语义"**。FAISS 只做向量距离计算，语义质量完全取决于上游嵌入模型；垃圾嵌入进、垃圾邻居出。
- **局限：不擅长带过滤的检索**。纯 ANN 是"全库 KNN"，实际 RAG 常要"在满足元数据过滤的子集里 KNN"，需要 post-filtering（先取大候选再过滤，召回受限）或 pre-filtering（分区内建索引），FAISS 本身不直接提供结构化过滤，向量库（Milvus、pgvector）在这一层做了封装。
- **局限：动态更新**。HNSW 不支持删除，IVF-PQ 的 k-means 质心在数据分布漂移后会过期，大规模生产系统需要定期重建索引或用分片滚动重建。
- **与精确 KNN 的边界**：需要 100% 召回的场景（去重、精确指纹匹配、安全审计）必须用 Flat 或 [[SHA-256 产物指纹]] 这类精确方法，ANN 不适用。

## 和我的项目的关系

- **[[TripleChecker]]**：三元组审计时需要在已核实三元组库里召回语义相近的候选做对照，底层就是 ANN。选型上，三元组库量级在 $10^5$–$10^6$ 时用 `HNSWFlat` + 余弦即可，量级更大或需要把嵌入压进有限显存时上 `IVFPQ`；关键是 Recall@K 要设到 0.95+，否则"漏看一个相似的已核实反例"会直接放过关系幻觉。
- **[[EvidenceFirst]]**：证据可审计要求检索结果可复现，ANN 的非确定性（HNSW 的贪心顺序、IVF 的 nprobe 截断）会让两次搜索结果略不同。生产中应固定随机种子、记录 nprobe/efSearch 参数，并对高风险判定走 Flat 精排兜底，避免"近似检索的随机性"污染审计结论。
- **[[CoMaGRAG]] / RAG 主线**：RAG 向量召回层几乎就是 FAISS/类似库的封装，理解 IVF-PQ 的 nprobe 与 PQ 码长如何影响召回，是诊断"RAG 没召回相关文档"时定位是检索问题还是生成问题的前提。两阶段检索（ANN 取大候选 → [[交叉编码器 Cross-Encoder]] 精排）是标准范式。
- **面试与教学**：讲"维度诅咒为什么让 KD-Tree 失效""PQ 为什么能压 16 倍还能算距离""HNSW 的多层图直觉"，ANN 是从 KNN 基础到向量数据库工程的必经一环。

## 交叉引用

- [[K近邻 KNN K-Nearest Neighbors]]
- [[检索增强生成 RAG-GraphRAG]]
- [[信息检索 IR基础模型 Information Retrieval]]
- [[双塔Embedding Dual Encoder]]
- [[交叉编码器 Cross-Encoder]]
- [[对比学习 Contrastive Learning]]
- [[混合检索 Hybrid Retrieval]]
- [[RAG 评测指标 EM Recall MRR]]
- [[SHA-256 产物指纹]]

## 更新记录

- 2026-08-03: 首次建页，依据 FAISS 论文（arXiv:1702.08734）、FAISS 官方 wiki、HNSW（arXiv:1603.09320）与 PQ（IEEE TPAMI 2011, DOI 10.1109/TPAMI.2010.57）整理方法族谱、FAISS 索引选型与工程权衡
