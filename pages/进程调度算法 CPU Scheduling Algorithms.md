---
摘要: 决定哪个就绪进程获得 CPU 的策略集合，按目标分为批处理、交互式、实时与多核调度
来源: https://en.wikipedia.org/wiki/Scheduling_(computing); Silberschatz《Operating System Concepts》第 6 章
信度: 高
首次记录: 2026-08-05
tags: [基础]
---

# 进程调度算法 CPU Scheduling Algorithms

## 核心内容

进程调度（CPU scheduling）是操作系统的核心决策之一：当 CPU 空闲、就绪队列非空时，调度器必须选择其中一个进程把 CPU 交给它。负责选择的模块称为**调度器（scheduler）**，执行实际切换的模块称为**分派器（dispatcher）**——它把选中进程的上下文加载到 CPU 上并跳转到其恢复点。调度算法决定了系统的吞吐、响应速度、可预测性和公平性，是 [[操作系统运行机制 OS Runtime Mechanisms]] 的策略层。

本页系统梳理经典调度算法家族（批处理、交互式、实时、多核）以及 Linux/Windows 的工业级实现，并给出评价指标、对比与典型误区。

### 何时调度

调度发生在以下时机（"调度点"）：

1. 进程从运行转为阻塞（发起阻塞式 I/O、等待信号量）——通常调度另一个就绪进程。
2. 进程从运行终止。
3. 进程从运行被抢占、回到就绪（定时器中断、更高优先级进程就绪）。
4. 进程从阻塞变为就绪（I/O 完成、中断到达）——可能抢占当前进程。
5. 显式 `sched_yield`。

其中 1、2 是"非抢占式调度"也会发生的切换；3、4 只在**抢占式调度（preemptive scheduling）**中存在。非抢占式算法一旦把 CPU 交给进程，就让它一直运行到终止或主动阻塞；抢占式算法可在任意中断点夺回 CPU。现代通用 OS 都是抢占式的。

### 评价指标

调度算法没有单一最优解，而是在以下指标间权衡：

| 指标 | 定义 |
|------|------|
| **CPU 利用率（utilization）** | CPU 忙的时间比例，目标接近 100% |
| **吞吐（throughput）** | 单位时间完成的进程数 |
| **周转时间（turnaround time）** | $T_{\text{turnaround}} = T_{\text{completion}} - T_{\text{arrival}}$，从提交到完成 |
| **等待时间（waiting time）** | $T_{\text{waiting}} = T_{\text{turnaround}} - T_{\text{burst}}$，在就绪队列中等待的总时长 |
| **响应时间（response time）** | $T_{\text{response}} = T_{\text{first response}} - T_{\text{arrival}}$，从提交到首次产出 |
| **公平性（fairness）** | 各进程获得的 CPU 份额与其权重成比例，避免 [[饥饿 Starvation]] |
| **可预测性（predictability）** | 相同负载下结果稳定，对实时系统关键 |
| **开销（overhead）** | 调度本身的 CPU 与缓存代价 |

批处理系统关心吞吐、周转与 CPU 利用率；交互式系统关心响应时间与公平；实时系统关心截止期（deadline）的可预测性。

### 批处理调度算法

#### FCFS（First-Come, First-Served，先来先服务）

按到达顺序排队，非抢占。实现最简单（FIFO 队列），但有著名的 **护航效应（convoy effect）**：一个 CPU 密集长作业排在前面时，后面许多 I/O 密集短作业全部阻塞在它后面，CPU 利用率和平均周转都很差。平均等待时间对到达顺序敏感，通常较长。

#### SJF（Shortest Job First，短作业优先）

每次选择**下一次 CPU burst 最短**的进程。可证明：当所有进程同时到达时，SJF 给出**最小平均等待时间**。SJF 分两种：

- **非抢占式 SJF**：一旦选中就让它跑完这次 burst。
- **抢占式 SJF**（亦称 **SRTF，Shortest Remaining Time First**）：新到进程若剩余 burst 比当前进程剩余时间短，则抢占。

难点在于需要预知每个进程的下一次 CPU burst 时长——这通常无法精确知道。实际系统用**指数平均**预测：

$$\tau_{n+1} = \alpha t_n + (1-\alpha)\tau_n$$

其中 $t_n$ 是第 $n$ 次实测 burst，$\tau_n$ 是历史估计，$\alpha\in[0,1]$ 控制新旧权重。SJF 的另一个缺陷是可能让长作业**饥饿**——不断到来的短作业让长作业永远拿不到 CPU。需要**老化（aging）**机制：等待越久，实际优先级越高，最终一定能被调度。

#### HRRN（Highest Response Ratio Next，最高响应比优先）

非抢占算法，每次选择响应比最大的进程：

$$R = \frac{w + s}{s} = 1 + \frac{w}{s}$$

其中 $w$ 是已等待时间，$s$ 是预计服务时间。短作业天然 $R$ 高（分母小），长作业等待时间 $w$ 增长后 $R$ 也会升高，从而缓解 SJF 的饥饿问题。需要预估服务时间。

### 交互式调度算法

#### RR（Round Robin，时间片轮转）

最经典的公平抢占算法。就绪队列按 FIFO 排列，每个进程最多连续运行一个**时间片（quantum / time slice）** $q$，到时被定时器中断抢占、回到队尾。

- $q$ 极大时，RR 退化为 FCFS；
- $q$ 极小时，RR 近似"处理器共享（processor sharing）"，但上下文切换开销占主导。

经验上 $q$ 取 10–100 ms，应明显大于一次上下文切换的代价（1–10 μs），让切换开销占比低于 1% 左右。RR 的平均等待时间通常比 SJF 差，但响应时间好、公平、无饥饿，是通用分时系统的基石。

#### 优先级调度（Priority Scheduling）

每个进程有一个优先级，调度器选优先级最高者。可抢占（新到更高优先级进程立即抢占）或非抢占。优先级可静态（创建时确定）或动态（根据行为调整）。问题：

- **饥饿**：低优先级进程可能永远得不到 CPU；
- **优先级反转（priority inversion）**：高优先级进程等待低优先级进程持有的锁，而中优先级进程抢占了低优先级进程，导致高优先级被间接阻塞。解法见 [[饥饿 Starvation]] 中的优先级继承（PIP）与优先级天花板（PCP）协议，经典案例是 1997 年火星探路者号。

#### MLFQ（Multilevel Feedback Queue，多级反馈队列）

由 Corbato 于 1962 年在 CTSS 中提出，是最有影响力的调度思想之一。维护多个按优先级排序的就绪队列，规则：

1. 新进程进入最高优先级队列；
2. 每个队列内用 RR，且优先级越高，时间片越短；
3. 进程用完整个时间片仍未阻塞（CPU 密集型）→ 降级到下一优先级，时间片翻倍；
4. 进程在时间片内发起 I/O 阻塞（I/O 密集型）→ 留在原队列或升级，以保持响应性；
5. 周期性地把所有进程提升回最高优先级，防止低优先级饥饿（aging）。

MLFQ 自动学习进程行为：交互式短作业留在高优先级获得快速响应，CPU 密集长作业沉到低优先级在后台跑完，无需预先知道 burst 时长。FreeBSD ULE、Windows、Solaris 传统调度器都基于 MLFQ 思想。

#### Fair-Share Scheduling（公平共享调度）

调度对象不是单个进程，而是"用户/组/容器"等**主体（principal）**：保证每个主体获得其应得的 CPU 份额，主体内部再在进程间分配。这是现代云与多租户系统的基础（Linux cgroup、cgroup v2 的 `cpu.weight`、Kubernetes CPU requests/limits 都属此类）。

#### Lottery / Stride Scheduling

彩票调度（Waldspurger 1994）：每个进程持有与其权重成正比的彩票数，每次调度随机抽一张彩票，持有该彩票的进程运行一个时间片。长期看来，CPU 份额正比于彩票数，且新进程加入后立即可按比例获得份额。Stride 调度是其确定性版本：每个进程有步长 $s_i = 1/w_i$，每次选 pass 值最小者，运行后 pass 加上 $s_i$。

### 实时调度算法

实时系统要求任务在截止期前完成，分**硬实时**（错过即失败，如汽车制动）与**软实时**（错过降低体验，如音视频）。任务模型通常为周期任务 $(C_i, T_i, D_i)$，其中 $C_i$ 是最坏执行时间、$T_i$ 是周期、$D_i$ 是相对截止期。

#### RM（Rate-Monotonic，速率单调）

静态优先级：周期越短优先级越高。Liu & Layland（1973）证明：对 $n$ 个独立、周期固定、$D_i=T_i$ 的任务，若总利用率

$$U = \sum_{i=1}^{n} \frac{C_i}{T_i} \leq n(2^{1/n}-1)$$

则 RM 可调度。当 $n\to\infty$ 时上界趋于 $\ln 2 \approx 0.693$。这是充分条件，不是必要条件——实际可调度的任务集利用率可能更高。

#### EDF（Earliest Deadline First，最早截止期优先）

动态优先级：每次选择绝对截止期最早的任务运行。理论上 EDF 对单处理器是**最优**的——只要存在任何可行调度，EDF 就能找到，可调度条件为 $U \leq 1$。但 EDF 在瞬时过载时行为难以预测（截止期错过会雪崩），且运行时开销比 RM 高；实际系统常在关键路径用 RM 保底，非关键路径用 EDF。

Linux 自 3.14（2014）加入 `SCHED_DEADLINE`，实现 EDF 的变种 CBS（Constant Bandwidth Server），用于对延迟敏感的音视频与工业负载。

### Linux 调度器演进

Linux 把进程称为 task（见 [[进程与线程 Process and Thread]]），调度类按优先级从高到低排列：

1. `SCHED_DEADLINE`（EDF/CBS，用于实时截止期任务）
2. `SCHED_FIFO`、`SCHED_RR`（POSIX 实时策略，优先级 1–99）
3. `SCHED_NORMAL`/`SCHED_BATCH`/`SCHED_IDLE`（普通任务，由 **CFS** 调度）

#### O(1) 调度器（2.6，2003–2007）

由 Ingo Molnár 设计，用两个优先级数组（active/expired）和位图，在常数时间内选出最高优先级任务，解决了早期 O(n) 调度器在 SMP 上的扩展性问题。但其交互性启发式规则复杂、调参困难，在某些负载下响应不稳。

#### CFS（Completely Fair Scheduler，2.6.23，2007 至今）

由 Ingo Molnár 设计，CFS 不再直接分配时间片，而是维护一颗按**虚拟运行时间 `vruntime`** 排序的红黑树，每次选 `vruntime` 最小的任务运行。每个任务的 `vruntime` 增长速度与其 nice 值相关：

$$\Delta\text{vruntime}_i = \Delta t_{\text{exec}} \cdot \frac{w_0}{w_i}$$

其中 $w_0$ 是 nice=0 的权重（常量 `NICE_0_LOAD` = 1024），$w_i$ 是任务 $i$ 的权重（nice 越小权重越大）。结果是高权重任务 `vruntime` 增长慢、留在红黑树最左端更久，得到更多 CPU；低权重任务 `vruntime` 增长快，让出 CPU。理想情况下，$n$ 个任务在一个调度周期内各运行约 $T/n \cdot w_i / \sum w_j$。

CFS 通过两个 sysctl 控制粒度：`sched_latency_ns`（目标调度周期，默认约 6 ms 用于延迟敏感配置或 24 ms 用于吞吐配置）与 `min_granularity_ns`（任务最小运行时间，防止过细切换）。唤醒任务时 `vruntime` 会被减去一个"沉睡额度"（sleep average），保证 I/O 密集型交互式任务醒来后能快速抢占。CFS 对 NICE 范围的 CPU 份额比为 1:1.25（每降一优先级权重乘约 1.25）。

#### 其他

- **BFS / MuqSS**（Con Kolivas）：面向桌面的 O(1) 调度器，强调交互响应，曾用于 -ck 内核补丁集。
- **EEVDF（Earliest Eligible Virtual Deadline First）**：2023 年并入 Linux 6.6 主线，替代 CFS 用于普通任务，更精确地按权重和延迟请求调度。
- **FreeBSD ULE**、**Windows 调度器**：基于 MLFQ + 优先级提升 + 多处理器亲和。

### 多核/SMP 调度

在多核系统上，单队列与多队列各有取舍：

- **单队列（SQMS，Single-Queue Multiprocessor Scheduling）**：所有 CPU 共享一个就绪队列，实现简单、负载天然均衡，但需要锁、扩展性差，且缓存亲和性差（一个任务可能在不同核间迁移）。
- **多队列（MQMS，Multi-Queue MPS）**：每个 CPU 一个就绪队列，无锁、可扩展、缓存亲和好，但需要独立的**负载均衡（load balancing）**算法在队列间迁移任务。Linux CFS 采用 per-CPU runqueue（每核一棵红黑树）+ 调度域（scheduling domain）周期性负载均衡。

关键机制：

- **CPU 亲和性（affinity）**：`sched_setaffinity` 把任务绑定到一组 CPU，避免缓存抖动；NUMA 系统上还需考虑本地内存访问。
- **工作窃取（work stealing）**：空闲核从繁忙核的队列偷任务，Go 运行时、tokio、Cilk 等用户态调度器常用。
- **负载均衡周期**：Linux 在时钟中断中按调度域层级检查队列长度差异，必要时迁移任务；主动均衡（active balancing）在严重不均衡时把任务拉走。
- **PMT / 节能**：现代调度器还考虑 Intel Turbo Boost、ARM big.LITTLE、睿频与能效核（P-core/E-core）的差异。

### 经典算法对比

| 算法 | 抢占 | 平均等待 | 响应 | 开销 | 饥饿 | 适用场景 |
|------|------|---------|------|------|------|---------|
| FCFS | 否 | 高（护航效应） | 差 | 极低 | 无 | 简单批处理 |
| SJF / SRTF | 可选 | **最小** | SRTF 较好 | 中（需预测） | 有 | 已知 burst 的批处理 |
| HRRN | 否 | 较好 | 一般 | 中 | 无 | 批处理 |
| RR | 是 | 中 | 好 | 低–中 | 无 | 分时/通用 |
| 优先级 | 可选 | 中 | 较好 | 低 | **有** | 通用、实时 |
| MLFQ | 是 | 较好 | **好** | 中 | 需 aging | 通用/交互 |
| Fair-share | 是 | 按主体 | 好 | 中 | 无 | 多租户 |
| RM | 是 | 实时保证 | 可预测 | 低 | 无 | 硬实时 |
| EDF | 是 | 最优单处理 | 可预测 | 中–高 | 过载雪崩 | 实时/截止期 |
| CFS | 是 | 公平 | 好 | 红黑树 $O(\log n)$ | 无 | Linux 通用 |

### 算例

四个进程同时到达，CPU burst 如下：P1=6，P2=8，P3=7，P4=3（单位 ms）。

**FCFS**（按 P1–P4 顺序）：
完成时间依次 6、14、21、24；等待 = 0、6、14、21；平均等待 10.25 ms。

**SJF（非抢占）**（按 P4、P1、P3、P2）：
完成 3、9、16、24；等待 = 0、3、9、16；平均等待 7.0 ms。

**RR，q=4**：
执行序列 P1(4) P2(4) P3(4) P4(3) P1(2) P2(4) P3(3) P2(1)；
完成时间 P4=15、P1=16、P3=23、P2=24；等待 P1=10、P2=16、P3=16、P4=12；平均等待 13.5 ms。

可以看到 SJF 平均等待最优，但 RR 响应时间（首次产出）最快（P1、P2、P3、P4 分别在 4、8、12、15 ms 首次获得 CPU），而 SJF 下 P2 要等到 16 ms 才首次运行。这正是交互式系统选 RR/MLFQ 而非 SJF 的原因。

### 常见误区

- **"SJF 最优"**：在所有进程同时到达、最小化平均等待的特定意义下成立；对响应时间、公平性、未知 burst 都不成立。
- **"时间片越小越好"**：过小时间片让上下文切换开销主导；典型 Linux 配置切换一次 1–10 μs，时间片不应低于毫秒级。
- **"RR 公平"**：RR 在 CPU 份额上公平，但如果进程 nice 值或权重不同就不再公平；公平应按权重衡量，这是 CFS 的目标。
- **"CFS 严格按 nice 比例分配 CPU"**：CFS 在长期、持续运行、无休眠、单核条件下近似按权重比例；唤醒、多核迁移、cgroup 配额都会造成短期偏差。
- **"EDF 总是优于 RM"**：EDF 在单处理器上利用率上界更宽松（$U\leq 1$ vs $\ln 2$），但需要运行时计算截止期、过载时行为差；RM 实现简单、可预测性强，安全关键系统偏好 RM。
- **"优先级高就一定先跑"**：在 Linux 上，`SCHED_NORMAL` 的 nice 值由 CFS 解释为权重而非硬优先级；真正的硬实时优先级是 `SCHED_FIFO`/`SCHED_RR` 的 1–99。
- **"加核就能线性加速"**：锁竞争、缓存一致性流量、负载不均、Amdahl 定律都让加速比受限；调度器的迁移决策直接影响这一点。
- **"调度器只决定 CPU"**：现代 I/O 调度器（mq-deadline、BFQ、none）、网络调度（TC、eBPF）、GPU 调度也都是调度问题，算法思想相通。
- **"MLFQ 一定会让交互式任务更快"**：MLFQ 需要正确设置老化周期与降级规则；配置不当（如老化太频繁）会让 CPU 密集任务反复升到高优先级，反而损害交互响应。

## 和我的项目的关系

暂无直接关联。调度算法是理解后端高并发、协程运行时与资源隔离的基础：Go 调度器的 G-M-P 模型、`tokio` 的 work-stealing、Kubernetes 的 CPU request/limit 与 cgroup CFS 带宽控制，都是这些经典算法在不同层次的再现。在多智能体或检索系统中安排 Agent 任务、推理请求与 I/O 任务时，同样面临"短任务优先 vs 公平 vs 截止期"的权衡；理解调度算法有助于设计合理的队列、优先级与超时策略。

## 交叉引用

- [[操作系统 Operating System]]
- [[操作系统运行机制 OS Runtime Mechanisms]]
- [[进程与线程 Process and Thread]]
- [[饥饿 Starvation]]
- [[操作系统死锁 Deadlock]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-08-05: 首次建页
