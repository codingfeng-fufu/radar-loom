---
摘要: LRU用近期访问时间近似最优替换,以哈希表加双向链表实现O(1)存取,是缓存与页面替换基线算法。
来源: https://en.wikipedia.org/wiki/Cache_replacement_policies
信度: 高
首次记录: 2026-07-16
tags: [基础]
---

# LRU 缓存替换 Least Recently Used

## 核心内容

LRU(Least Recently Used,最近最少使用)是一种**缓存替换策略**:当缓存满、需要淘汰一项以给新项腾位置时,选择**最久没有被访问过**的那一项淘汰。它把"最近用过"视为"未来还会用"的代理,依赖的是**引用局部性(locality of reference)**——一个刚被访问的对象在近期再次被访问的概率显著高于随机。作为缓存替换家族里的经典基线,LRU 广泛出现在 CPU cache、操作系统页面替换、数据库缓冲池、CDN/Web 缓存、语言运行时 memoization 以及 LLM 推理的 KV cache 逐出等场景。

它要对比的理论上限是 **Belady 最优替换算法(OPT / MIN)**:每次淘汰"最远的将来才会再被访问"的项。OPT 需要预知未来访问序列,因此只能用作离线分析基线;LRU 的意义就在于**只使用过去信息**近似这个不可实现的上限。

### 形式化与关键性质

设缓存容量为 $C$,访问序列 $r_1, r_2, \dots, r_n$。定义时刻 $t$ 之前对象 $x$ 的**最近访问时间**为

$$
\tau_t(x) = \max\{s < t : r_s = x\}
$$

若访问 $r_t$ 未命中且缓存已满,LRU 淘汰

$$
\arg\min_{x \in \text{Cache}_t} \tau_t(x)
$$

即最小的最近访问时间对应的对象。

LRU 属于 Mattson 等 1970 年正式定义的**栈算法(stack algorithm)**:对任意访问序列和任意缓存大小 $C$,若把此刻缓存中的项按 LRU 序排列,则容量 $C'>C$ 的缓存中包含的正是容量 $C$ 的缓存中的所有项加上额外的 $C'-C$ 项。这条性质有两个直接推论:

1. **单调性(无 Belady 异常)**:LRU 的缺失次数关于缓存容量 $C$ 单调不增,增大缓存不会反常地降低命中率。FIFO 就不具备这一性质——著名的 Belady 异常在 FIFO 上真实存在。
2. **单次遍历得到所有容量的命中曲线**:借助**LRU 栈距离(stack distance / reuse distance)**,一次扫描访问序列即可得到所有 $C$ 值下的命中率曲线,这是容量规划与在线调参的重要工具。

竞争比方面,LRU 相对 OPT 的最差竞争比为 $C$:存在对手序列使 LRU 的缺失数是 OPT 的 $C$ 倍(可达上界)。任何**确定性**在线替换算法都不可能优于 $C$-竞争比,因此 LRU 在这一意义上是"确定性策略里的最优之一"。

### 标准实现:哈希表 + 双向链表

要在每次访问上做到 $O(1)$ 摊还,标准做法是**双向链表 + 哈希表**双结构:

- 双向链表按"从最近到最远"顺序保存所有条目,头是 MRU、尾是 LRU;
- 哈希表把 key 映射到链表节点,支持 $O(1)$ 定位。

关键操作:

- `get(k)`:哈希查节点,若命中则把节点从当前位置摘下、挂到链表头,返回值;
- `put(k, v)`:若已存在则更新值并前移;若不存在且容量已满,摘掉链表尾节点、从哈希表删除对应 key,再把新节点插到头部。

摘链和插链都是常数次指针操作;哈希表期望 $O(1)$。因此 LRU cache 的 `get`/`put` 都是**期望 $O(1)$**,空间开销为 $O(C)$。这一实现正是 LeetCode 146 的标准解法,也是绝大多数语言标准库/框架的实现思路。

代表性封装:

- **Python** `functools.lru_cache` / `functools.cache`:自带并发锁与统计,可直接装饰函数;
- **Java** `LinkedHashMap` 传入 `accessOrder=true` 即得 LRU;
- **Go**:`hashicorp/golang-lru`、`groupcache/lru` 等库;
- **Guava** `CacheBuilder.maximumSize(...)`(实际是 W-TinyLFU 变体的近似 LRU);
- **Caffeine**:高性能 Java 缓存,底层为 **W-TinyLFU**——LRU 之上加频率感知的准入策略。

### 硬件与操作系统里的近似

真正在 CPU 缓存里维护"精确 LRU 序"需要为每路记录访问时间戳,代价高。硬件上普遍使用**Pseudo-LRU(PLRU)**:

- **Tree-PLRU**:$k$ 路组相联缓存用 $k-1$ 位组织成二叉树,每次访问翻转从根到该路的路径位,替换时沿"反方向"下降找路;开销 $O(\log k)$ bits/组。
- **Bit-PLRU(MRU-bit)**:每路一位标记"最近是否被访问过",全部被置位后统一清零,失去部分序但硬件极简。

操作系统层面用 **Clock / Second-Chance** 算法近似 LRU:页表项维护一位 reference bit,页框排成环形,时钟指针扫描,遇到 reference=1 就清零并跳过、遇到 0 就淘汰。Linux 内核采用**双链表变体(active / inactive LRU list)**,并配合 workingset 检测决定页在两条链表间的迁移。

### LRU 的短板与常见改进

LRU 只依赖**一次最近访问**,不区分频次,因此存在几类系统性问题:

1. **扫描污染(scan pollution / one-hit wonder)**:一次大范围顺序扫描会把所有热点数据挤出缓存,而扫描本身几乎不产生复用。
2. **循环序列**:序列长度略大于缓存容量时,LRU 命中率为 0;OPT 在同样容量下仍能保住大部分。
3. **不适应长期频率**:某项被访问一万次而后短暂沉默,可能被一个刚出现的冷项挤出。

主流改进沿两条主线:

- **抗扫描**:**2Q**(Johnson & Shasha 1994)、**LIRS**(Jiang & Zhang 2002)、MySQL InnoDB 的**中点插入(midpoint insertion)**——新页先入 LRU 链表的"中点"位置,只有再次被访问才升入"新页保护区",避免扫描直接冲掉热点。
- **融合频率**:**LFU**(Least Frequently Used)、**ARC**(Megiddo & Modha 2003,USENIX FAST)在 LRU 与 LFU 之间自适应切换;**W-TinyLFU**(Einziger et al. 2015,Caffeine)用 Count-Min Sketch 估计频率作为**准入过滤器**,只允许"频率高于将被淘汰项"的新条目进入 LRU。

在极端热点长尾的负载(CDN、社交 feed)上,W-TinyLFU 与 ARC 的命中率通常显著高于纯 LRU;但在多数普通工作负载上,LRU 与其近似仍是稳定且实现最简的选择。

### 适用条件与常见误区

- **假设**:访问模式具有**时间局部性**。均匀随机访问或反局部性(anti-locality)负载上,LRU 退化到与随机替换相近,甚至更差(如上文循环序列)。
- **和 TTL / 失效策略正交**:LRU 决定"满了淘汰谁",TTL/写失效决定"何时使某项失效"。生产缓存往往两者共存。
- **并发实现是难点**:朴素双链表操作在多线程下需要粗粒度锁,严重限制吞吐。生产级实现要么分片(sharded LRU),要么用**批量重排 + 环形缓冲**记录访问、异步维护顺序(Caffeine 的做法)。
- **`lru_cache` 不是"数据缓存"**:Python `functools.lru_cache` 只在**进程内**、**参数可哈希**、**函数纯**的前提下工作;跨进程/服务的缓存应使用 Redis/Memcached,后者内部也是 LRU / LRU 近似。
- **"最近"如何定义**:硬件、OS、Redis(`allkeys-lru`)之类的近似 LRU 使用**采样比较**(Redis 默认从 N 个随机 key 里挑最老的)以规避维护严格链表的成本,和"教科书 LRU"命中率相近但复杂度大幅下降。

## 和我的项目的关系

LRU 与 KG/RAG 主线没有强绑定,但在几处系统组件里是"默认工具":

- **[[LLM 推理优化 KV Cache Quantization]] 的 KV 缓存管理**:vLLM 的 PagedAttention 用类页表机制切分 KV cache,块级逐出策略在多请求并发时接近 LRU;做 EvidenceFirst 这类"多次调用同一 prompt 前缀 + 少量变化"的验证流程时,prompt 前缀命中 KV 复用能显著降低成本,前提是缓存策略偏向保留高频前缀而非新提交请求。
- **[[EvidenceFirst]] 的状态机与检索缓存**:BFS 阶段会反复用同一实体或同一证据查询节点。给证据检索层加一个 LRU 缓存(容量按活跃对话数量 × 单会话平均实体数估算)可以避免同一实体在多轮验证中重复走向量库,是工程侧几十行代码就能拿到的加速。
- **[[混合检索 Hybrid Retrieval]] 的 BM25/向量结果缓存**:相同 query 的检索结果适合按 query hash 做 LRU;需要注意 query 重复度不高时 LRU 命中率会很低,此时改用 W-TinyLFU 或直接不缓存更合算——不要把"能用 LRU"和"该用 LRU"混同。
- **[[实验可复现性 Reproducibility]] 中的坑**:装了 `functools.lru_cache` 的辅助函数会让多次评测结果依赖调用顺序(第一次未命中较慢,后续命中很快),做时延测试时应显式 `cache_clear()` 或在冷启动下测量。

## 交叉引用

- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[LLM 推理优化 KV Cache Quantization]]
- [[EvidenceFirst]]
- [[混合检索 Hybrid Retrieval]]
- [[实验可复现性 Reproducibility]]

## 更新记录

- 2026-07-16: 首次建页,给出 LRU 定义、与 OPT 的关系、栈算法与单调性、$O(1)$ 实现、硬件/OS 近似(PLRU、Clock)、扫描污染与 2Q/ARC/W-TinyLFU 等主流改进,以及在 KV cache、EvidenceFirst 检索缓存中的适用场景。
