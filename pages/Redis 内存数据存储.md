---
摘要: Redis 是开源的内存数据结构存储，常用作数据库、缓存和消息代理。
来源: https://redis.io/docs/latest/develop/get-started/ (Redis 官方文档 Introduction to Redis)
信度: 高
首次记录: 2026-08-02
tags: [基础]
---

# Redis 内存数据存储

## 核心内容

**Redis（Remote Dictionary Server）** 是一个开源的、基于内存的数据结构存储系统，由 Salvatore Sanfilippo（antirez）于 2009 年发布，常用作数据库、缓存、会话存储和消息代理。与 Memcached 等纯缓存不同，Redis 把丰富的数据结构（字符串、哈希、列表、集合、有序集合、位图、HyperLogLog、地理索引、Stream）暴露为原生类型，并支持持久化、主从复制、哨兵高可用和集群分片。

Redis 的核心取舍是**以内存换低延迟**：数据主要驻留内存，单线程命令执行（Redis 6+ 在网络 I/O 上引入多线程，但命令仍串行执行）避免锁竞争，亚毫秒级响应；代价是单机容量受内存限制、持久化语义弱于磁盘数据库。它适合读多写少、对延迟敏感、能容忍少量数据丢失的场景，不适合作为唯一的持久化事务数据库。

### 原生数据类型

| 类型 | 结构 | 典型用途 |
| --- | --- | --- |
| String | 二进制安全字符串（最大 512 MB） | 缓存、计数器、分布式锁（SET NX EX） |
| Hash | 字段-值映射表 | 对象存储（用户档案、商品属性） |
| List | 双向链表 | 消息队列、时间线、最新 N 条 |
| Set | 无序集合 | 标签、共同好友、去重 |
| Sorted Set | 跳表+哈希，按 score 排序 | 排行榜、延迟队列、范围查询 |
| Bitmap | 位串 | 在线状态、布隆过滤器、签到 |
| HyperLogLog | 概率基数估计 | UV/PV 去重计数（标准误差约 0.81%） |
| Geo | 地理空间索引 | 附近的人/店 |
| Stream | 追加式日志 | 消息队列、事件流（支持消费组） |

### 持久化：RDB 与 AOF

Redis 提供两种持久化机制，可以单独或组合使用。

- **RDB（Redis Database）**：在某个时间点把整个数据集快照写入一个 `.rdb` 二进制文件。通过 `save`（阻塞）或 `bgsave`（fork 子进程）触发，可配置时间/变更数规则自动保存。优点是文件紧凑、恢复快、适合灾备；缺点是两次快照之间的写入会丢失，fork 在大内存实例上可能造成延迟毛刺。
- **AOF（Append-Only File）**：把每个写命令追加到日志文件，通过 `appendfsync` 策略控制 Durability：`always`（每条都 fsync，最安全但最慢）、`everysec`（默认，最多丢 1 秒）、`no`（交给 OS）。AOF 更安全但文件更大，Redis 会在后台重写（BGREWRITEAOF）压缩日志。Redis 7.0 引入 **Multi-Part AOF**，把 AOF 拆成 base、incremental 和 manifest 三类文件，改善重写期间的开销。

组合使用时，Redis 默认以 AOF 作为重启时的恢复源（数据更完整），RDB 作为快照备份。两种机制都不是严格的事务级持久化——把 Redis 当作唯一数据存储前必须接受这一点。

### 内存管理与淘汰策略

Redis 把数据保存在内存中，可以通过 `maxmemory` 配置上限。达到上限时，按 `maxmemory-policy` 决定如何处理写入：

- `noeviction`（默认）：拒绝写入并返回错误；
- `allkeys-lru` / `volatile-lru`：对所有键或仅设了 TTL 的键做 LRU 淘汰；
- `allkeys-lfu` / `volatile-lfu`：LFU 淘汰（Redis 4.0+，按访问频率而非最近访问）；
- `allkeys-random` / `volatile-random`：随机淘汰；
- `volatile-ttl`：淘汰 TTL 最短的键。

Redis 的 LRU/LFU 不是精确算法，而是对少量采样键做近似选择（由 `maxmemory-samples` 控制采样数，默认 5），以避免维护全局链表的开销。键的过期则通过**惰性删除**（访问时检查）加**定期删除**（每 100 ms 抽样）结合实现，相关工程原理与 [[LRU 缓存替换 Least Recently Used]] 一脉相承。

### 高可用与水平扩展

- **主从复制（Replication）**：一个 primary 负责写，多个 replica 异步复制读流量，复制基于 RDB 全量同步 + 命令传播增量同步。异步复制意味着故障切换可能丢失尚未同步的写入。
- **Sentinel**：独立的分布式监控进程，做心跳检测、自动故障检测和主从切换，并为客户端提供服务发现。
- **Redis Cluster**：在数据分片层把键空间按 CRC16 哈希分到 16384 个 slot，由多个主节点各自承担一部分 slot，对应从节点做高可用。客户端可重定向（MOVED/ASK），不支持跨多键的事务和 Lua 脚本（除非所有键在同一 slot，可用 hash tag 强制）。

### 典型使用场景

1. **缓存**：最常见用法，挡在 MySQL 等数据库前吸收读流量；配合 TTL 和 LRU/LFU 淘汰。
2. **会话与登录态**：分布式 session、JWT 黑名单、验证码短期存储。
3. **计数器与限流器**：`INCR`/`DECR` 原子计数；滑动窗口限流可用 Sorted Set。
4. **排行榜**：Sorted Set 的 `ZADD`/`ZRANGE`/`ZRANK`。
5. **轻量消息队列**：List 的 BLPOP 或 Stream 的消费组，但不具备 Kafka 那样的大规模堆积和回放能力。
6. **分布式锁**：`SET key value NX EX seconds`，释放锁时用 Lua 脚本比对 value 防止误删；Redlock 算法在多主场景下的安全性仍有争议。
7. **实时分析**：HyperLogLog 做 UV、Bitmap 做留存、Sorted Set 做 Top-K。

### 局限与常见误区

- **不是持久化数据库**：即使开了 AOF `everysec`，仍可能丢约 1 秒数据；主从异步复制也会丢数据。强一致事务场景应选用关系型数据库。
- **单线程命令执行**：一个慢命令（`KEYS *`、大 Set 上的 `SMEMBERS`、大范围 `ZRANGE`）会阻塞所有后续请求；生产环境应禁用危险命令、用 `SCAN` 代替 `KEYS`、避免 big key/hot key。
- **内存成本**：同样数据放内存比磁盘贵一个数量级，且碎片率（`mem_fragmentation_ratio`）需要监控；不要把冷数据长期留在 Redis。
- **集群限制**：Cluster 模式下跨 slot 的多键操作受限；Pipeline、Lua 脚本也要保证键落在同一 slot。
- **缓存一致性**：缓存与数据库之间没有原生事务保证，需要业务层设计 cache-aside、write-through、双删等策略，并接受短暂不一致窗口。
- **2024 年许可证变更**：Redis 7.4 起不再使用 BSD 许可证，改为 RSALv2/SSPLv1 双许可；社区因此分叉出 [Valkey](https://valkey.io/)（Linux 基金会托管，BSD 许可）。选型时需要注意许可证与社区走向。

## 和我的项目的关系

暂无直接关联。当前研究主线（KG、RAG、Agent 可信度）不直接依赖 Redis，但它在工程上有两类潜在价值：一是作为 Agent 系统的**会话状态/短期记忆/限流缓存**层，配合 TTL 和淘汰策略比把状态全塞 LLM 上下文更可控；二是作为**事件流和任务队列**（Stream）支撑多 Agent 协作中的黑板/消息总线。把 Redis 当成易失的高性能状态层而非知识主存，知识主存仍应放在向量库/KG/关系库。

## 交叉引用

- [[机器学习与NLP基础 ML-NLP Foundations]]
- [[LRU 缓存替换 Least Recently Used]]
- [[Agent 记忆架构]]

## 更新记录

- 2026-08-02: 首次建页
