---
摘要: TCP通过三次握手建立可靠连接、四次挥手可靠关闭的连接管理核心机制，出自RFC 793标准。
来源: https://www.rfc-editor.org/rfc/rfc793
信度: 高
首次记录: 2026-07-28
tags: [基础]
---

# TCP三次握手与四次挥手 TCP Handshake and Teardown

## 核心内容

TCP（传输控制协议，Transmission Control Protocol）是面向连接的、可靠的字节流传输协议，定义于 RFC 793（Postel, 1981；RFC 9293 于 2022 年更新但核心机制不变）。三次握手与四次挥手是 TCP 连接生命周期中建立与释放的两次状态协商过程：前者在不可靠的 IP 网络上同步双方初始序列号并确认收发能力，后者在全双工通道上双向独立地关闭数据流，避免数据丢失或半开连接残留。

### 三次握手（Three-Way Handshake）建立连接

目标：双方互相确认对方的发送和接收能力正常，并交换初始序列号 ISN（Initial Sequence Number），防止历史重复连接造成混乱。

| 阶段 | 发起方（Client） | 标志位 / 序列号 | 接收方（Server） | 状态变迁 |
|---|---|---|---|---|
| 1 | 发送 SYN | SYN, seq = x | 收到 SYN | Client: CLOSED → SYN-SENT；Server: LISTEN → SYN-RECEIVED |
| 2 | 收到 SYN+ACK | SYN, ACK, seq = y, ack = x+1 | 发送 SYN+ACK | Client: SYN-SENT → ESTABLISHED；Server: SYN-RECEIVED |
| 3 | 发送 ACK | ACK, ack = y+1 | 收到 ACK | Server: SYN-RECEIVED → ESTABLISHED |

关键要点：
- **为什么是三次而不是两次**：两次握手无法阻止历史重复的 SYN 被误当成新连接。第三次 ACK 让 Server 确认 Client 确实在线且序列号正确，这正是 RFC 793 §3.4 明确给出的理由——防止"old duplicate connection initiations"。
- SYN 与 FIN 各消耗一个序列号（即使不携带数据），因此确认号为 seq+1。
- ISN 并非从 0 开始，而是随时间递增的计数器，避免短时间内重用同一四元组时旧报文被误认。

### 四次挥手（Four-Way Wavehand）关闭连接

TCP 是全双工协议，两个方向的数据流必须独立关闭——"我没有数据发给你了"并不代表"你也没有数据发给我了"，因此每个方向都需要一组 FIN+ACK，共四次。

| 阶段 | 主动关闭方（Active Close） | 标志位 | 被动关闭方（Passive Close） | 状态变迁 |
|---|---|---|---|---|
| 1 | 发送 FIN | FIN, seq = u | 收到 FIN | Active: ESTABLISHED → FIN-WAIT-1；Passive: ESTABLISHED → CLOSE-WAIT |
| 2 | 收到 ACK | ACK, ack = u+1 | 发送 ACK | Active: FIN-WAIT-1 → FIN-WAIT-2 |
| 3 | 收到 FIN | FIN, seq = w, ack = u+1 | 发送 FIN（应用调用 close 后） | Passive: CLOSE-WAIT → LAST-ACK；Active: FIN-WAIT-2 → TIME-WAIT |
| 4 | 发送 ACK | ACK, ack = w+1 | 收到 ACK → CLOSED | Active: TIME-WAIT → 等待 2MSL → CLOSED |

关键要点：
- **CLOSE-WAIT 状态**：被动关闭方收到 FIN 后先回 ACK，但必须等自己的应用层把剩余数据发完才会发 FIN，这段时间即为 CLOSE-WAIT；大量 CLOSE-WAIT 堆积通常意味着应用层未正确 close socket。
- **TIME-WAIT 与 2MSL**：主动关闭方发送最后一个 ACK 后必须等待 2 倍 MSL（Maximum Segment Lifetime，报文最大生存时间，通常 2×60s=120s 或 2×30s=60s）。两个原因：（1）保证最后一个 ACK 能到达对方——若丢失，对方会重发 FIN，等待期内可重传 ACK；（2）让本次连接的所有陈旧报文在网络中自然消亡，避免四元组复用时旧报文混入新连接。
- **半关闭（Half-Close）**：主动关闭方发完 FIN 后仍可继续接收数据，直到对方也发 FIN，这是全双工独立关闭的直接体现。
- **同时打开 / 同时关闭**：RFC 793 也规定了两端同时发 SYN 或同时发 FIN 的特殊情况，前者仍收敛到 ESTABLISHED，后者双方都进入 CLOSING → TIME-WAIT → CLOSED。

### 常见面试考点与误区

- **为什么建立是三次、关闭是四次**：建立时 Server 可把 ACK 和 SYN 合并在一个报文里（SYN+ACK）；关闭时被动方收到 FIN 只代表对方不再发数据，但自己可能还有数据要发，ACK 和 FIN 不能合并，必须分两次，所以多一个报文。
- **SYN 洪水攻击（SYN Flood）**：攻击者发大量 SYN 但不回第三次 ACK，Server 的 SYN-RECEIVED 队列被占满导致无法处理正常连接。现代 OS 用 SYN Cookie 等机制缓解。
- **ISN 可预测性问题**：早期 TCP 的 ISN 按固定速率递增，攻击者若猜出 ISN 可伪造 TCP 报文注入连接，这是 TCP 协议本身的安全短板（需靠上层 TLS/IPsec 弥补）。
- **listen 的 backlog 参数**：对应半连接队列（SYN-RECEIVED）与全连接队列（ESTABLISHED 但未 accept）的大小，调优不当会导致新连接被丢弃。

## 和我的项目的关系

暂无直接关联。本页作为计算机网络基础知识存档，便于排查服务端开发中遇到的连接状态异常（如 CLOSE-WAIT 堆积、TIME-WAIT 过多导致端口耗尽、SYN Flood 告警）。

## 交叉引用

- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-07-28: 首次建页
