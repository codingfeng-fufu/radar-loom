---
摘要: TCP/IP 网络层无连接数据报协议，IPv4/IPv6 提供寻址、路由与分片
来源: https://www.rfc-editor.org/rfc/rfc791
信度: 高
首次记录: 2026-08-03
tags: [基础]
---

# 网际协议 Internet Protocol

## 核心内容

IP（Internet Protocol，网际协议）是 TCP/IP 协议族的网络层核心协议，定义在 IPv4 中是 RFC 791（1981 年 9 月，Postel 等），IPv6 中是 RFC 8200（2017 年 7 月，Deering & Hinden，Obsoletes 2460）。IP 的职责只有三件事：用固定长度地址标识源和目的主机、把数据报（datagram）从源逐跳送到目的、在路径 MTU 不足时对长数据报做分片与重组。RFC 791 §1.2 明确划定了边界：IP **不**提供端到端可靠性、流量控制、排序、重传或连接——这些全部交给上层（通常是 TCP）。RFC 791 §1.4 把 IP 实现的基本功能概括为 addressing 和 fragmentation，把 TTL、ToS、Options、Header Checksum 列为四个关键服务机制。

## IP 的服务模型

- **无连接（connectionless）**：RFC 791 §1.4 明确"IP treats each internet datagram as an independent entity unrelated to any other"，没有握手、没有虚电路、没有会话状态。每个数据报独立选路，同一连接的不同包可以走不同路径甚至乱序到达。
- **尽力而为（best-effort）**：IP 不保证送达、不保证顺序、不保证不重复；出错时直接丢包，必要时通过 ICMP 报告差错（RFC 791 §1.4 末段）。
- **介质无关**：IP 跑在任何能携带数据报的链路层之上（Ethernet、Wi-Fi、PPP、串行链路等），通过分片适配不同网络的 MTU。

这种"极简网络层 + 丰富传输层"的拆分是 Internet 可演进的根本原因：链路层技术可以任意替换，传输层可以根据需要选择 TCP（可靠）或 UDP（轻量），IP 只负责"把包送到下一跳"。

## IPv4 数据报首部

按 RFC 791 §3.1 Figure 4，IPv4 首部最小 20 字节、最长 60 字节（IHL 以 4 字节为单位，最大 15）：

| 字段 | 长度 | 作用 |
|---|---|---|
| Version | 4 bit | IP 版本号，IPv4 固定为 4 |
| IHL | 4 bit | Internet Header Length，单位 4 字节，最小 5（即 20 字节） |
| Type of Service | 8 bit | 期望的服务质量（时延/吞吐/可靠性优先级），后被 DiffServ 重新解释 |
| Total Length | 16 bit | 整个数据报长度（首部 + 数据），单位字节，故 IPv4 数据报最大 65535 字节 |
| Identification | 16 bit | 同一原始数据报的所有分片共用一个 ID，用于重组 |
| Flags | 3 bit | 比特位：保留、DF（Don't Fragment）、MF（More Fragments） |
| Fragment Offset | 13 bit | 当前分片在原始数据报中的偏移，单位 8 字节 |
| Time to Live | 8 bit | 每经过一个路由器减 1，到 0 丢包，防止路由环路导致包无限循环 |
| Protocol | 8 bit | 上层协议号（TCP=6、UDP=17、ICMP=1、OSPF=89），由 IANA 维护 |
| Header Checksum | 16 bit | 只校验首部，不校验数据；每跳 TTL 减 1 后必须重算 |
| Source Address | 32 bit | 源 IPv4 地址 |
| Destination Address | 32 bit | 目的 IPv4 地址 |
| Options + Padding | 变长 | 可选字段（源路由、时间戳、安全标签等），很少使用 |

几个工程后果：

1. **首部校验和不覆盖数据**——链路层通常有自己的 CRC，但 IP 层不为数据错误负责，端到端完整性由 TCP 校验和或应用层保证。
2. **DF 位与 PMTUD**：设 DF=1 时路由器不能分片，遇到 MTU 不足会回 ICMP "Fragmentation Needed"，发送方据此做路径 MTU 发现（PMTUD，RFC 1191）。
3. **TTL 既是生命也是排障工具**：traceroute 就是靠逐跳发送 TTL=1,2,3… 的包并收集 ICMP Time Exceeded 来还原路径。
4. **Protocol 字段是解复用键**：IP 用它决定把 payload 交给 TCP、UDP 还是其他协议，类似 UDP/TCP 用端口向上解复用。

## IPv6 数据报首部

RFC 8200 §3 定义的 IPv6 固定首部只有 40 字节，比带选项的 IPv4 简洁：

| 字段 | 长度 | 作用 |
|---|---|---|
| Version | 4 bit | 固定为 6 |
| Traffic Class | 8 bit | 对应 IPv4 ToS/DSCP |
| Flow Label | 20 bit | 标记同一流，便于 QoS 和硬件转发（RFC 6437） |
| Payload Length | 16 bit | 后续载荷长度（含扩展首部），不含 40 字节固定首部 |
| Next Header | 8 bit | 下一头部类型，取值与 IPv4 Protocol 字段共用 IANA 编号空间 |
| Hop Limit | 8 bit | 等价于 IPv4 TTL，每跳减 1 |
| Source Address | 128 bit | 源 IPv6 地址 |
| Destination Address | 128 bit | 目的 IPv6 地址 |

主要差异：

- **地址从 32 bit 扩到 128 bit**，理论地址空间从 $2^{32}$ 扩到 $2^{128}$，从根上解决 IPv4 地址耗尽问题。
- **删去首部校验和**：IPv4 每跳都要重算校验和（因为 TTL 变了），IPv6 认为链路层和传输层已经覆盖完整性，去掉以提速转发。
- **删去分片字段**：IPv6 路由器**不再做分片**，只允许源主机分片。源通过 PMTUD（IPv6 版在 RFC 8201）发现路径 MTU，必要时加上 Fragment 扩展首部（Next Header=44）。这把分片责任从网络核心移到端系统，简化了路由器。
- **选项改为扩展首部链**：IPv4 的 Options 塞进主首部导致长度可变、路由器处理慢；IPv6 把可选功能（Hop-by-Hop、Destination Options、Routing、Fragment、AH、ESP）做成一串链式扩展首部，路由器只需处理链中必要的部分。Next Header 字段指向下一个首部（扩展首部或传输层首部）。
- **固定 40 字节、不再有 IHL**：所有 IPv6 包首部等长，硬件定长解析更快。

## IPv4 vs IPv6 要点对照

| 维度 | IPv4 (RFC 791) | IPv6 (RFC 8200) |
|---|---|---|
| 地址长度 | 32 bit | 128 bit |
| 首部长度 | 20–60 字节（含选项） | 固定 40 字节 + 扩展首部 |
| 首部校验和 | 有，每跳重算 | 无 |
| 分片 | 源和路由器都可分 | 仅源主机可分 |
| 选项 | 塞在主首部里 | 独立扩展首部链 |
| 广播 | 支持广播地址 | 取消广播，用组播/任播替代 |
| NAT 依赖 | 大量依赖 NAT 缓解地址不足 | 设计目标之一是端到端可达，少用 NAT |
| QoS 字段 | ToS（8 bit） | Traffic Class（8 bit）+ Flow Label（20 bit） |

## 关键假设、局限与常见误区

- **误区 1：IP 保证送达**。不，IP 是 best-effort，丢包、乱序、重复都被允许；可靠性是 TCP 的事，UDP 应用要自己处理。
- **误区 2：IP 地址等于主机身份**。IP 地址标识的是**网络接口**而非主机；一台多宿主主机有多个 IP，移动后 IP 会变，身份需要上层（如 TLS 证书、应用账号）保证。
- **误区 3：同一 TCP 连接的包走同一路径**。IP 是无连接的，中间路由变化会让同一五元组的包走不同路径，TCP 靠序列号处理乱序。
- **误区 4：IPv6 只是更长地址的 IPv4**。IPv6 重新设计了分片模型、选项机制、地址自动配置（SLAAC）、邻居发现（NDP 取代 ARP）等，不是简单扩地址。
- **局限：IP 不加密不认证**。原生 IP 报文头和载荷都是明文；机密性与完整性由 IPsec（AH/ESP，作为扩展首部或独立框架）或上层 TLS 提供。
- **局限：IPv4 地址耗尽与 NAT 破坏端到端**。NAT 让主机没有全局地址，使得入站连接、P2P、某些应用层协议（如 FTP active mode、SIP）复杂化；这是 IPv6 被推动的主因之一。

## 和我的项目的关系

暂无直接关联。本页是网络基础主题，与 [[OSI参考模型与TCP-IP模型 OSI and TCP-IP Models]] 互补：后者讲分层框架并把 IP 列为 L3 代表协议，本页讲 IP 本身的服务模型、首部与版本差异。排查服务端问题时，L3 层的排障动作围绕 IP 展开：`ping` 依赖 ICMP（封装在 IP 里）验证可达性，`traceroute` 利用 TTL/Hop Limit 还原路径，`ip route`/`route -n` 查路由表，`tcpdump` 抓 IP 包看源目的地址与 DF/MF 位。与 [[路由协议 RIP OSPF BGP]] 配合可理解控制平面如何决定 IP 包的下一跳。

## 交叉引用

- [[OSI参考模型与TCP-IP模型 OSI and TCP-IP Models]]
- [[TCP三次握手与四次挥手 TCP Handshake and Teardown]]
- [[路由协议 RIP OSPF BGP]]

## 更新记录

- 2026-08-03: 首次建页，依据 RFC 791（IPv4）与 RFC 8200（IPv6）整理服务模型、首部字段、版本差异与局限
