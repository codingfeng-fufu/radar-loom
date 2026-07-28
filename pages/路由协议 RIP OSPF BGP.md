---
摘要: RIP距离矢量、OSPF链路状态、BGP路径矢量三类核心IP路由协议的算法、报文与适用场景。
来源: https://www.rfc-editor.org/rfc/rfc2453  https://www.rfc-editor.org/rfc/rfc2328  https://www.rfc-editor.org/rfc/rfc4271
信度: 高
首次记录: 2026-07-28
tags: [基础]
---

# 路由协议 RIP OSPF BGP

## 核心内容

路由协议（Routing Protocol）解决"在由大量路由器互联的 IP 网络中，如何让每台路由器自动学习到所有可达目的网络的最优路径"的问题，工作在网络层，核心输出是路由器中的**路由表（Routing Table）**——目的前缀 → 下一跳/出接口。三类经典算法分别对应三类协议：距离矢量（RIP）、链路状态（OSPF）、路径矢量（BGP）。它们覆盖了从企业网内部到全球互联网的所有路由场景。

先区分两个概念：
- **IGP（Interior Gateway Protocol，内部网关协议）**：在一个自治系统（AS）内部运行，如 RIP、OSPF、IS-IS、EIGRP；
- **EGP（Exterior Gateway Protocol，外部网关协议）**：在 AS 之间运行，目前只有 BGP（BGP-4）。

### 一、RIP（Routing Information Protocol）— 距离矢量

**标准**：RFC 1058（RIP v1）、RFC 2453（RIP v2）。

**算法**：Bellman-Ford（距离矢量，Distance Vector）。

**工作原理**：
- 每台路由器维护一张"到每个目的网络的距离（跳数 hop count）"表，初始只知道直连网络（距离 1）。
- 每 30 秒向**直连邻居**发送整张路由表（Response 报文），邻居收到后用 Bellman-Ford 规则更新：
$$
\text{if } D(X) > D_{\text{neighbor}}(X) + 1 \text{, then } D(X) \leftarrow D_{\text{neighbor}}(X) + 1, \text{nexthop} \leftarrow \text{neighbor}
$$
- 经过反复传播，所有路由器最终学到全网路径——这叫"路由收敛"。

**关键特性**：
- **度量（Metric）**：跳数，最大值 15，16 即视为"不可达"——这从根本上限制了 RIP 只适合小规模网络（直径 ≤15 跳）。
- **更新方式**：定时广播/组播（v1 广播到 255.255.255.255，v2 组播到 224.0.0.9），同时**触发更新**（Triggered Update）：度量变化时立刻发出，不等 30 秒。
- **防环机制**：
  - **水平分割（Split Horizon）**：从一个接口学到的路由不再从此接口发回；
  - **毒性逆转（Poison Reverse）**：把失效路由标为 16（无穷大）反向发回，加速收敛；
  - **抑制时间（Hold-Down）**：路由被标不可达后一段时间内不接受相同或更差的路径更新，避免坏消息传太慢引发"计数到无穷（Count-to-Infinity）"。
- **v1 vs v2**：v2 支持 VLSM/CIDR（携带子网掩码）、组播、简单认证，是目前实际使用版本。
- **报文**：UDP 520 端口，报文最大 512 字节（一次最多 25 条路由），超出分片发送。

**优缺点**：实现极简、资源占用低；但跳数度量不反映真实带宽/延迟（10 Gbps 和 64 kbps 等价）、收敛慢（坏消息传得慢）、直径受限。仅适合小型分支网络或历史遗留环境。

### 二、OSPF（Open Shortest Path First）— 链路状态

**标准**：RFC 2328（OSPF v2，IPv4）、RFC 5340（OSPF v3，IPv6）。

**算法**：Dijkstra 最短路径优先 SPF（Link-State）。

**工作原理**：核心思想是"全网路由器都知道同一张完整的网络拓扑图，各自独立算最短路径"，而不是 RIP 那样"只知道邻居告诉你的距离"：

1. **邻居发现**：路由器通过 Hello 协议（组播 224.0.0.5，10 秒/次）在直连链路上发现邻居，协商参数后建立邻接（Adjacency）。
2. **链路状态泛洪（Flooding）**：每个路由器生成一个 LSA（Link-State Advertisement），描述自己直连的链路、IP 前缀、代价、邻居；所有 LSA 通过可靠泛洪传遍整个区域，每台路由器最终拥有一致的**链路状态数据库 LSDB**（= 全网拓扑快照）。
3. **独立 SPF 计算**：每台路由器以自己为根，在 LSDB 上跑 Dijkstra 算法，得到到每个目的网络的最短路径树，再生成本地路由表。
4. **增量更新**：拓扑变化时只泛洪变化的 LSA（不是整张表），并触发部分路由重算，收敛快（秒级）。

**关键特性**：
- **度量**：Cost = 参考带宽 / 接口带宽（默认参考 100 Mbps，100 Mbps 口 cost=1，1 Gbps 也是 1——现代网络常用 auto-cost reference-bandwidth 100000 抬到 100 Gbps 以区分高速链路）。反映真实链路能力，且可人工调整。
- **区域划分（Area）**：为了控制 LSDB 规模，OSPF 把 AS 划分为若干区域，所有区域必须连到骨干 Area 0；区域边界路由器 ABR 汇总区域间路由，避免域内 LSA 扩散到全网，把 Dijkstra 计算限制在区域内。
  - 区域内路由（Intra-Area，O）
  - 区域间路由（Inter-Area，O IA）
  - AS 外部路由（External Type 1/Type 2，O E1/O E2）——由 ASBR 注入
- **指定路由器 DR/BDR**：在广播多路访问网络（如以太网）上，所有路由器两两建立邻接会产生 $O(n^2)$ 邻接关系和泛洪量，因此选举 DR（Designated Router）和 BDR（Backup），其他路由器只与 DR/BDR 邻接，由 DR 向全网广播 LSA。
- **报文类型**：直接封装在 IP 协议号 89，五种报文：Hello、DBD（数据库描述）、LSR（链路状态请求）、LSU（更新）、LSAck（确认）。
- **等价路由 ECMP**：多条 cost 相等的路径可做负载分担。

**优缺点**：收敛快、无跳数限制、支持层次化、支持 VLSM/CIDR、度量合理、有认证；但实现复杂、CPU/内存占用高（维护 LSDB+跑 SPF）、排障门槛高。是企业网、园区网、运营商 IGP 主力。

### 三、BGP（Border Gateway Protocol）— 路径矢量

**标准**：RFC 4271（BGP-4，当前版本）。

**算法**：路径矢量（Path Vector）——本质是距离矢量，但矢量里存的是完整的 AS 路径而非度量，并且策略（Policy）优先于最短路径。

**工作原理**：
- BGP 在 AS 边界路由器（BGP Speaker / Peer）之间建立 TCP 连接（端口 179），交换路由前缀及路径属性；连接建立后只发增量更新（UPDATE 报文），不做定时全量刷新，靠 KEEPALIVE（默认 60 秒）维持邻居，超时（Hold Time 默认 180 秒）则断开。
- **iBGP vs eBGP**：同一 AS 内的 BGP 邻居称 iBGP（internal BGP），不同 AS 间称 eBGP（external BGP）。iBGP 为防止环路要求：从 iBGP 学到的路由不再转发给其他 iBGP 邻居——这意味着 AS 内所有 BGP 路由器必须**全互联**，或通过**路由反射器 RR（Route Reflector）** / **联邦 Confederation** 解决扩展性。
- **AS-Path 防环**：收到一条路由若 AS-Path 中已含自己的 AS 号，则丢弃（eBGP 环路天然防御）。
- **路径选择**：BGP 不只是算"最短"，而是按策略和一套严格的属性优先级选最优路径，属性主要有：
  1. **Weight**（Cisco 私有，本地有效）
  2. **Local Preference**（本地 AS 内有效，默认 100，越大越优）
  3. **Locally Originated**（本地 network/aggregate 优先）
  4. **AS-Path Length**（经过 AS 越少越优）
  5. **Origin**（IGP < EGP < Incomplete）
  6. **MED（Multi-Exit Discriminator）**（告诉相邻 AS 从哪个入口进来更好，越小越优）
  7. **eBGP 优于 iBGP**
  8. **IGP cost 到 BGP next-hop 最小**
  9. 其他 tie-breaker（Router ID、邻居 IP 等）
- **路由策略**：通过 Route-map / Prefix-list / AS-path ACL 控制哪些前缀接收、发送、如何改属性，是 ISP 实现商业策略（如客户优先、peer 限制、不做 transit）的核心手段。
- **收敛速度**：BGP 收敛很慢（分钟级），且全表规模大（IPv4 全表 ~100 万条前缀），对路由器内存和 CPU 要求高。

**关键特性**：
- **可靠传输**：基于 TCP，无需自带重传/分段/确认机制。
- **CIDR 与聚合**：BGP-4 原生支持 CIDR 和路由聚合（route aggregation/summarization），是支撑互联网从小规模扩展到今天规模的关键。
- **扩展性**：支撑全球 7 万+ AS 互联，但也存在路由表膨胀、路由泄露、BGP 劫持（如 2008 YouTube Hijack、2018 Amazon Route 53 Hijack）等安全问题。
- **现代增强**：BGPsec / RPKI（Resource Public Key Infrastructure）给路由起源和路径做密码学签名，缓解劫持。

### 四、三大协议对比

| 维度 | RIP | OSPF | BGP |
|---|---|---|---|
| 类型 | IGP，距离矢量 | IGP，链路状态 | EGP（兼 iBGP），路径矢量 |
| 算法 | Bellman-Ford | Dijkstra SPF | 路径矢量 + 策略选路 |
| 度量 | 跳数（max 15） | Cost（带宽反比） | AS-Path 长度 + 多属性策略 |
| 传输 | UDP 520 | IP 协议 89 | TCP 179 |
| 更新范围 | 直连邻居 | 区域内泛洪 LSA | BGP 邻居之间增量 UPDATE |
| 更新内容 | 整张路由表（定期 30s） | 邻居/链路变化时发 LSA 增量 | 增量 UPDATE + KEEPALIVE |
| 收敛速度 | 慢（数十秒到分钟） | 快（秒级） | 慢（分钟级） |
| 规模 | 小型网络（≤15 跳） | 中大型企业网/运营商 | 全球互联网（7万+ AS） |
| 层次化 | 无 | Area 0 + 普通区域 | iBGP/eBGP + RR/联邦 |
| 负载分担 | 等开销支持 | ECMP 多路径 | 多条等价/不等价（策略控） |
| 资源占用 | 极低 | 中高（LSDB+SPF 计算） | 高（100万+ 前缀） |
| 典型场景 | 小型分支/遗留 | 企业/园区/运营商 IGP | ISP 间互联、数据中心出口 |

### 五、常见误区

- **误区 1：OSPF 一定比 RIP 好**。在只有几台路由器的小网络里 RIP 足够，OSPF 的复杂配置和资源开销反而得不偿失；选协议看场景。
- **误区 2：BGP 选"最短路径"**。BGP 的核心是**策略**而非最短 AS-Path；AS-Path 长度只是第 4 条比较规则，Local Pref、MED、商业关系常先决定。例如 ISP 即使经过更多 AS 也会优先客户路由而非 peer 路由。
- **误区 3：BGP 距离矢量算法是 Bellman-Ford**。BGP 属于路径矢量，每条路由携带完整 AS-Path（解决了距离矢量的计数到无穷问题），并且不进行"邻居距离 +1"松弛，而是基于策略决定。
- **误区 4：OSPF 邻居 = 邻接**。Hello 发现后状态从 Down → Init → 2-Way（邻居） → ExStart → Exchange → Loading → Full（邻接）；广播网络上 DRother 之间停在 2-Way，不交换 LSA 是正常的。
- **误区 5：RIP 不能做 ECMP**。RIP v2 和大多数实现支持等价多路径，但"等价"指跳数相同。
- **误区 6：iBGP 需要全网全互联**。是的（或用 RR/联邦），因为水平分割规则"iBGP 路由不传给 iBGP 邻居"——否则会产生环路；初学者常漏此规则导致 iBGP 路由不传播。

## 和我的项目的关系

暂无直接关联。本页补全网络基础组中网络层的核心协议，与 [[OSI参考模型与TCP-IP模型 OSI and TCP-IP Models]] 的网络层条目相呼应，也为理解分布式系统中的"多副本状态一致性"（距离矢量/链路状态算法与 Gossip、一致性协议有概念映射：距离矢量 ≈ 谣言传播，链路状态 ≈ 可靠广播 + 本地计算）提供基础。排查数据中心出口路由、BGP 劫持、路由泄露、OSPF 邻居卡在 ExStart/Exchange、RIP 路由抖环等实战问题时，本页内容直接可用。

## 交叉引用

- [[OSI参考模型与TCP-IP模型 OSI and TCP-IP Models]]
- [[随机接入协议 ALOHA CSMA CSMA-CD CSMA-CA]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-28: 首次建页
