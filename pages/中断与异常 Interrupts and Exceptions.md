---
摘要: CPU 异步响应硬件事件、同步处理指令故障的硬件机制，OS 夺回控制权的入口
来源: https://en.wikipedia.org/wiki/Interrupt
信度: 高
首次记录: 2026-08-05
tags: [基础]
---

# 中断与异常 Interrupts and Exceptions

## 核心内容

中断（Interrupt）与异常（Exception）是 CPU 在正常指令流之外**异步或同步地转移控制权**的硬件机制。没有它们，OS 就无法在 I/O 完成时被唤醒、无法在程序出错时接管、也无法从死循环的用户程序手中夺回 CPU——所有现代多任务操作系统都建立在这套机制之上。

严格来说，Intel/AMD 体系结构把这一类事件统称为"异常（exceptions）"，再细分为中断、故障、陷阱、中止；ARM 则统称为"异常（exception）"，分为同步异常、IRQ、FIQ、SError。日常语境里"中断"通常狭义地指硬件中断，而"异常"指 CPU 指令执行产生的同步事件。本页采用这一常用区分，并在术语差异处注明。

### 精确分类

| 类别 | 触发源 | 同步/异步 | 返回行为 | 典型例子 |
|------|--------|----------|---------|---------|
| **硬件中断（Interrupt）** | 外部设备/控制器 | 异步 | 返回到被中断的下一条指令 | 网卡收包、磁盘 DMA 完成、定时器到期 |
| **故障（Fault）** | 当前指令 | 同步 | 修复后**重新执行**触发指令 | 缺页 `#PF`、段不存在 `#NP` |
| **陷阱（Trap）** | 当前指令 | 同步 | 执行触发指令的**下一条** | 调试断点 `#BP`、系统调用 |
| **中止（Abort）** | 当前指令 | 同步 | 不可恢复，终止进程/系统 | 机器检查 `#MC`、双重故障 `#DF` |

关键区别：**故障**报告的指令尚未成功执行，处理完后 CPU 回到该指令重执行（典型如缺页：OS 把页从磁盘换入后回到故障指令，这次能成功访问）；**陷阱**报告的指令已经执行完毕，CPU 回到下一条（典型如 `int3` 断点、`syscall`）。

### x86 异常向量表

x86 保留向量 0–31 给 CPU 异常，32–255 由 OS 分配给外部中断和系统调用。常见异常：

| 向量 | 助记符 | 名称 | 类型 | 说明 |
|------|--------|------|------|------|
| 0 | `#DE` | Divide Error | Fault | `div`/`idiv` 除零 |
| 1 | `#DB` | Debug | Fault/Trap | 调试寄存器断点、单步 |
| 2 | NMI | Non-Maskable Interrupt | Interrupt | 不可屏蔽，硬件错误等 |
| 3 | `#BP` | Breakpoint | Trap | `int3` 指令，调试器断点 |
| 4 | `#OF` | Overflow | Trap | `into` 指令，EFLAGS.OF=1 |
| 5 | `#BR` | Bound Range Exceeded | Fault | `bound` 指令越界 |
| 6 | `#UD` | Invalid Opcode | Fault | 未定义/特权指令 |
| 7 | `#NM` | Device Not Available | Fault | FPU/SSE 不可用（延迟保存） |
| 8 | `#DF` | Double Fault | Abort | 处理前一异常时又触发异常 |
| 10 | `#TS` | Invalid TSS | Fault | 任务状态段错误 |
| 11 | `#NP` | Segment Not Present | Fault | 段描述符 P=0 |
| 12 | `#SS` | Stack-Segment Fault | Fault | 栈段越界或不存在 |
| 13 | `#GP` | General Protection | Fault | 特权/边界违规 |
| 14 | `#PF` | Page Fault | Fault | 页表项无效或权限不足，CR2 记录故障地址 |
| 16 | `#MF` | x87 FP Exception | Fault | 浮点错误 |
| 17 | `#AC` | Alignment Check | Fault | 数据未对齐（CR4.AM 启用） |
| 18 | `#MC` | Machine Check | Abort | 硬件总线/缓存错误 |
| 19 | `#XM` | SIMD FP Exception | Fault | SSE/AVX 浮点异常 |
| 20 | `#VE` | Virtualization Exception | Fault | EPT violation 等 |

每个异常是否压入**错误码**（error code）由架构规定；缺页异常还把故障线性地址放入 `CR2`，OS 据此判断是合法缺页（换入）还是非法访问（发 `SIGSEGV`）。

### 中断控制器

单根中断线无法支持多 CPU 与数十上百设备，现代系统使用专用中断控制器：

**1. 8259 PIC（Programmable Interrupt Controller）**：传统 PC 使用两片级联，共 15 个 IRQ，已被淘汰，不支持 SMP。

**2. APIC（Advanced Programmable Interrupt Controller）**：x86 现代标准，分为两部分：

- **LAPIC（Local APIC）**：每个 CPU 核内置，负责接收并投递本核中断；包含本地定时器（APIC timer）、性能监控中断、 thermal sensor 中断，并能发送 **IPI（Inter-Processor Interrupt）**。
- **IOAPIC（I/O APIC）**：芯片组/PCH 中，把设备引脚的中断分发给某个 LAPIC，支持 24/120+ 个中断。

**3. MSI / MSI-X（Message Signaled Interrupts）**：设备不再通过专用引脚，而是直接向 LAPIC 的内存映射寄存器写一个指定数据字来"发中断"。优点：无需共享引脚、中断数更多（MSI-X 可独立屏蔽每个向量）、可按队列绑定不同 CPU；现代 NVMe、网卡普遍使用 MSI-X。

**4. ARM GIC（Generic Interrupt Controller）**：ARM 架构的标准控制器，主要版本 GICv2/v3/v4。v3 后将组件拆为：

- **Distributor（GICD）**：全局，管理 SPI（Shared Peripheral Interrupt，设备中断）。
- **Redistributor（GICR）**：每核一个，管理 SGI（Software Generated Interrupt，即 IPI）和 PPI（Private Peripheral Interrupt，如每核定时器）。
- **CPU Interface**：每核，与 CPU 交互。
- **LPI（Locality-specific Peripheral Interrupt）**：基于内存表的消息中断，类似 MSI。

### 顶半部与底半部

中断处理必须**极短**——ISR 期间本 IRQ 线被屏蔽，过长会丢失后续中断。Linux 把工作分为两部分：

**顶半部（top-half / hardirq）**：实际响应硬件的 ISR，运行在**中断上下文**，本 IRQ 线在本 CPU 上被屏蔽。它只做最小必要工作（读走数据、确认中断、调度底半部），然后返回。

**底半部（bottom-half）**：延迟处理不紧急的工作，有多种机制：

- **softirq**：编译时静态定义的 10 种类型（HI、TIMER、NET_TX、NET_RX、BLOCK、IRQ_POLL、TASKLET、SCHED、HRTIMER、RCU），运行在中断返回前夕；可在多 CPU 并发，所以处理函数必须可重入。
- **tasklet**：建立在 softirq 之上的更简单接口，动态注册；同一 tasklet 保证不在多 CPU 并发，但已被标记为过时。
- **workqueue**：把工作交给**内核线程**在进程上下文执行，**可以睡眠**，适合需要等待锁或做大量 I/O 的处理。
- **threaded IRQ**：把 ISR 本身作为内核线程运行，响应中断后唤醒线程处理；实时性好，被 `-rt` 补丁和 `PREEMPT_RT` 内核大量使用。

Windows 对应概念为 DPC（Deferred Procedure Call）和 work item。

### 中断上下文约束

顶半部/softirq 运行在中断上下文，不属于任何进程，因此受到严格限制：

- **不能睡眠或调度**：没有可调度的进程上下文，调用任何可能阻塞的函数（`mutex_lock`、`copy_from_user`、`kmalloc(GFP_KERNEL)`）都会导致内核崩溃。
- **不能访问用户空间**：中断可能打断任何进程，当前 `current` 的用户态与中断无关。
- **不能让出 CPU**：不能调用 `schedule()`。
- **时间敏感**：应在微秒级完成；长时间关中断会导致延迟飙升、定时器不准、其他设备丢中断。
- **时间戳**：使用 `jiffies` 或 `ktime_get()` 等快速时钟，不能调用可能睡眠的 RTC 接口。

只有 workqueue 和 threaded IRQ 运行在进程上下文，可以正常睡眠。

### 中断屏蔽、嵌套与优先级

- **屏蔽（masking）**：每个 IRQ 线可被单独屏蔽；`cli`/`sti` 或 ARM 的 `DAIF` 可屏蔽全部可屏蔽中断。NMI 不可屏蔽，用于不可推迟的严重事件。
- **嵌套**：现代 x86/Linux 默认情况下，ISR 运行时本 IRQ 在本 CPU 屏蔽，但其他 IRQ 可抢占（中断嵌套）；实时内核可把绝大多数中断线程化以降低延迟。
- **优先级**：APIC 每个向量有优先级；ARM GIC 对中断分 16 个优先级；高优先级中断可抢占低优先级 ISR。

### IPI：处理器间中断

在 SMP 系统中，CPU 之间通过 LAPIC/GIC 发送 IPI 通信，典型用途：

- **Reschedule interrupt**：唤醒目标 CPU 上的调度器，让它重新选进程运行。
- **TLB shootdown**：一个 CPU 修改页表后通知其他 CPU 失效其 TLB 表项。
- **CPU stop / CPU tick**：挂起目标 CPU、时钟广播。
- **Function call interrupts**：让目标 CPU 执行指定函数。

### ARM64 异常向量

ARM64 异常级别 EL0–EL3 各自有一张向量表（VBAR_ELx），按四个维度分 16 个入口：

- 当前异常级别（同 EL 使用 SP0 或 SPx） vs 来自低 EL
- 同步异常（SYNC） vs IRQ vs FIQ vs SError（系统错误，如异步数据中止）

同步异常包括 `svc` 系统调用、未定义指令、未对齐访问、MMU 故障等；IRQ/FIQ 是普通/快速硬件中断；SError 类似 x86 的 MCE，用于硬件报告不可恢复错误。FIQ 优先级高于 IRQ，用于低延迟场景。

### 信号：软件层面的类异常机制

Unix 信号（signal）是内核把事件通知给进程的软件机制，与硬件异常有清晰对应：

- **故障型**：`SIGSEGV`（段错误，对应 `#PF`）、`SIGFPE`（算术异常，对应 `#DE`）、`SIGILL`（非法指令，对应 `#UD`）、`SIGBUS`（总线错误）。
- **陷阱型**：`SIGTRAP`（对应 `#BP`/`#DB`）。
- **中止型**：`SIGKILL`（不可捕获、不可忽略，强制终止）。
- **异步事件型**：`SIGINT`（Ctrl+C）、`SIGTERM`、`SIGIO` 等类似硬件中断，进程可注册处理程序异步响应。

内核在返回用户态前检查待处理信号，若进程注册了 handler 则构造信号帧切到 handler 执行，否则执行默认动作（终止、忽略、暂停、core dump）。这是硬件异常机制在用户空间的对应物。

### 常见误区

- **"中断和异常是一回事"**：硬件中断是异步的，异常是同步的；二者进入内核的方式类似，但起因和返回语义不同。
- **"中断处理程序可以睡眠"**：顶半部和 softirq 运行在中断上下文，绝对不能睡眠；只有 workqueue 或 threaded IRQ 可以。
- **"缺页是中断"**：缺页 `#PF` 是异常中的**故障**，同步触发，且修复后要重新执行故障指令。
- **"NMI 可以用 `cli` 屏蔽"**：NMI 不可屏蔽，专门用于无法被推迟的事件（硬件错误、watchdog、内核调试）。
- **"信号就是中断"**：信号是内核给用户态的软件通知，底层可能由硬件异常或内核事件产生，二者是不同层的机制。
- **"ISR 中可以做大量工作"**：长时间 ISR 会增加延迟、丢失中断；耗时工作必须放到 workqueue/threaded IRQ。
- **"MSI 比引脚中断快是因为用了内存写"**：MSI 的主要优势是可扩展性、无需共享引脚和天然支持多队列亲和性，单次投递开销与引脚中断相近。

OS 如何通过中断/异常夺回 CPU、系统调用流程与上下文切换等内容见 [[操作系统运行机制 OS Runtime Mechanisms]]；OS 的整体抽象与架构见 [[操作系统 Operating System]]。

## 和我的项目的关系

暂无直接关联。中断/异常机制揭示了"事件驱动的内核如何在不可信的用户程序面前保持控制"这一根本设计，对理解高性能 I/O（NAPI、`io_uring` 轮询模式为何能减少中断开销）、定时器、信号处理和系统编程有基础性意义。

## 交叉引用

- [[操作系统 Operating System]]
- [[操作系统运行机制 OS Runtime Mechanisms]]
- [[操作系统死锁 Deadlock]]
- [[机器学习与NLP基础 ML-NLP Foundations]]

## 更新记录

- 2026-08-05: 首次建页
