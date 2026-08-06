---
摘要: 多进程或线程安全协作访问共享资源的协议，含临界区、互斥锁、信号量与管程
来源: https://en.wikipedia.org/wiki/Mutual_exclusion
信度: 高
首次记录: 2026-08-06
tags: [基础]
---

# 操作系统同步与互斥 OS Synchronization and Mutual Exclusion

## 核心内容

同步（Synchronization）与互斥（Mutual Exclusion）回答一个问题：**多个独立推进的执行流（进程、线程、中断处理程序）共享内存、文件或设备时，如何让它们按正确的顺序访问共享状态，而不会产生不可预测的结果？** 互斥是同步的一种特例——保证同一片共享代码（临界区）一次只有一个执行流进入；同步则更广，还包括"事件 A 必须在事件 B 之前发生"这类顺序约束。

问题起源于 Dijkstra 1965 年的论文《Cooperating Sequential Processes》，他把并发编程从"碰巧正确"提升为可证明正确的学科。今天从内核自旋锁到数据库事务、从无锁队列到分布式共识，核心抽象都建立在这一页的概念之上。

### 临界区问题（Critical Section Problem）

每个进程的代码可划分为四段：

```
do {
    // entry section      请求进入
    // critical section   访问共享资源
    // exit section       释放
    // remainder section  其它不相关计算
} while (true);
```

设计 entry/exit 协议必须满足三项经典要求（Silberschatz《Operating System Concepts》Ch. 6；与 Coffman 死锁条件不同，别混淆）：

1. **互斥（Mutual Exclusion）**：若进程 $P_i$ 在临界区内，则其它任何进程不得在临界区内。
2. **进展（Progress）**：若无人在临界区内且有若干进程想进入，那么"谁下一个进入"只能由这些想进入的进程决定，且不能无限期推迟。
3. **有限等待（Bounded Waiting）**：进程发出请求后，在其被批准之前，其它进程进入临界区的次数存在上界。这条防饥饿（见 [[饥饿 Starvation]]）。

此外还有工程要求：在单 CPU 上不能长时间关中断；在多核上不能假设指令原子性；协议应尽量让不进入临界区的进程互不影响。

**竞态条件（Race Condition）** 是上述任一要求被违反时的实际症状：多个执行流并发读写同一变量，最终结果依赖于指令的相对时序。经典例子是 `counter++`——它由 `load / add / store` 三条机器指令组成，两次并发自增可能丢失一次更新。

### 软件解决方案

在没有任何硬件原子指令的假设下，纯软件也能构造互斥协议，但代价昂贵。

**严格轮转（Strict Alternation）**：共享变量 `turn` 表示允许谁进入。问题是若轮到 $P_0$ 但 $P_0$ 暂时不想进，$P_1$ 即使临界区空闲也不能进——违反进展条件。

**Peterson 算法（Peterson, 1981, *Information Processing Letters* 12(3):115–116）**：经典双进程方案，两个共享变量 `flag[2]` 和 `turn`：

```c
// 进程 i（另一个为 j = 1 - i）
flag[i] = true;
turn = j;
while (flag[j] && turn == j) { /* spin */ }
/* ---- 临界区 ---- */
flag[i] = false;
/* ---- 剩余区 ---- */
```

该算法同时满足互斥、进展和有限等待（上界为 1）。**但在现代乱序多核 CPU 上直接实现不正确**：编译器或硬件可能重排对 `flag` 与 `turn` 的写入，必须插入内存屏障才能保证 Peterson 原始证明所依赖的顺序可见性。

**Bakery 算法（Lamport, 1974, *CACM* 17(8):453–455）**：可扩展到 $n$ 个进程，且不假设对同一变量的读写是原子的（因此也适用于某些分布式与无原子硬件场景）。每个进程进入前"取一个号" `number[i] = 1 + max(number[0..n-1])`，然后按 $(\text{number}[i], i)$ 字典序最小者进入：

```c
choosing[i] = true;
number[i]   = 1 + max(number[0..n-1]);
choosing[i]  = false;
for (j = 0; j < n; j++) {
    if (j == i) continue;
    while (choosing[j]) { /* spin */ }
    while (number[j] != 0 &&
           (number[j] < number[i] ||
            (number[j] == number[i] && j < i))) { /* spin */ }
}
/* ---- 临界区 ---- */
number[i] = 0;
```

命名来自面包店发号：每位顾客拿到一个递增号码，号码最小的先被服务，同号时 ID 较小者优先。Bakery 满足三项要求且天然无死锁，但每次进入需扫描所有其它进程，复杂度 $O(n)$。

### 硬件支持

纯软件方案在通用硬件上性能差、正确性依赖细节。现代体系结构提供了多种原语。

**关中断（Disabling Interrupts）**：单处理器上，进入临界区前 `cli` 屏蔽中断，退出时 `sti`。临界区内不会被切换，也不会被中断处理程序重入。优点是简单；缺点是仅在单 CPU 上有效（多核上其它核仍可访问同一数据），且用户态不能关中断、长时间关中断会丢失时钟中断。因此仅用于内核中极短的临界区。

**原子指令**：硬件保证"读-改-写"在一个不可分割的总线事务中完成：

- **测试并设置（Test-and-Set, TAS）**：原子地把内存位设为 1 并返回旧值。用它实现自旋锁：`while (test_and_set(&lock)) ;`。
- **比较并交换（Compare-and-Swap, CAS）**：原子地执行 `if (*p == old) { *p = new; return true; } else return false;`。x86 上是 `CMPXCHG`，ARMv8 上是 `CAS`。CAS 是无锁数据结构的基础。
- **链接加载/条件存储（Load-Linked / Store-Conditional, LL/SC）**：ARM、MIPS、RISC-V 采用。`LL` 读取一个字并让处理器监控其地址；`SC` 仅在该地址自 LL 后未被修改时才写入成功。比 CAS 更适合实现无锁结构，且天然避免 CAS 的 ABA 问题。
- **原子交换（XCHG）**：原子交换寄存器与内存。x86 上最常见的自旋锁实现就是 `xchg` 把 1 锁入变量并测试旧值。

**内存屏障（Memory Barrier / Fence）**：现代 CPU 和编译器都会重排访存。屏障强制约束屏障前后的访存顺序，常见有 `rmb`（读屏障）、`wmb`（写屏障）、`mb`（全屏障），以及更弱的 acquire/release 语义。Peterson、无锁队列、RCU 等都依赖内存屏障才能在弱序硬件（ARM、POWER、RISC-V）上正确工作。

### 信号量（Semaphore）

Dijkstra 在 1965 年提出的经典抽象。一个信号量 $S$ 是一个整型变量，只能通过两个**原子**原语访问，P/V（来自荷兰语 Proberen / Verhogen，也常记作 `wait` / `signal`、`down` / `up`）：

$$P(S):\quad \text{while } S \le 0 \text{ do skip};\quad S \leftarrow S - 1$$

$$V(S):\quad S \leftarrow S + 1$$

朴素实现是忙等（自旋）。**实用实现把信号量关联一个等待队列**：$P$ 发现 $S \le 0$ 时把当前进程阻塞入队并调用调度器；$V$ 递增 $S$ 并从队列唤醒一个进程。这把"等待"从消耗 CPU 转为让出 CPU。

两类信号量：

- **二元信号量（Binary Semaphore / Mutex Semaphore）**：初值为 1，等价于互斥锁。
- **计数信号量（Counting Semaphore）**：初值为可用资源数 $k$，用于管理有 $k$ 个实例的资源池，或作为事件通知（初值 0 的信号量即"一次性门闩"）。

信号量既可用于互斥，也可用于**排序同步**（synchronization ordering）：让线程 A 中的 `V(S)` 先于线程 B 中的 `P(S)`，就强制了"A 先做、B 后做"的先后关系。

**互斥锁与二元信号量的区别**：语义上 mutex 强调"持有者"概念——谁加锁谁解锁，不可跨线程释放；信号量不记录持有者，任何线程都可 `V`。POSIX 的 `pthread_mutex_t` 还支持递归、错误检查、优先级继承等所有权特性，而 `sem_t` 只是计数原语。

### 管程（Monitor）与条件变量

信号量功能强大，但 `P/V` 散落在代码各处，容易漏掉一个 `V` 导致死锁，或在错误位置加 `P` 破坏互斥。

Hoare（1974, *CACM* 17(10):549–557）和 Brinch Hansen（1973）提出**管程**：把共享数据、操作它们的过程、以及初始化代码封装成一个模块，由编译器/运行时保证**同一时刻只有一个进程在管程内活动**——互斥由语言隐式保证，程序员不必手写。

仅有互斥不够：管程内的进程可能需要"等待某个条件成立"才能继续。为此引入**条件变量（Condition Variable）**，支持三个操作：

- `wait(c)`：释放管程锁，把当前进程挂到 $c$ 的队列；被唤醒后重新获取管程锁才返回。
- `signal(c)`：唤醒一个等待 $c$ 的进程（若有）。
- `broadcast(c)`：唤醒所有等待者。

两种 signal 语义的差别直接影响编程模型：

- **Hoare 语义（Signal-and-Urgent-Wait / Blocking Signal）**：signal 者立即挂起，把管程交给被唤醒者，被唤醒者运行完退出后 signal 者才能继续。条件在被唤醒者看来必然成立，推理简单，但实现需要一次额外切换。
- **Mesa 语义（Signal-and-Continue）**：signal 者继续运行，被唤醒者只是被放入就绪队列；等它真正拿到管程锁时，条件可能已被别的进程改变。因此 Mesa 风格要求把 `wait` 包在 `while (!condition) wait();` 中，而不是 `if`。Java 的 `Object.wait/notify`、POSIX 的 `pthread_cond_t` 都是 Mesa 语义。

### 经典同步问题

这三个问题之所以成为教学经典，是因为它们各自代表了一种典型的同步约束。

**生产者-消费者（有界缓冲区, Bounded Buffer）**：$n$ 个槽位的循环队列，生产者放入、消费者取出。需要三种原语：二元信号量 `mutex` 保护队列结构；计数信号量 `empty`（初值 $n$）记录空槽数；计数信号量 `full`（初值 0）记录已用槽数。生产者 `P(empty) → P(mutex) → 放入 → V(mutex) → V(full)`；消费者对称。注意 `empty/full` 必须在 `mutex` 之前 P，否则会死锁。

**读者-写者（Readers-Writers）**：共享数据可被多个读者并发访问，但写者必须独占。两种偏好策略：
- 第一读者-写者问题：读者优先，写者可能饥饿；
- 第二读者-写者问题：写者优先，一旦写者到达，后续读者等待，避免写者饥饿，但连续写者流也可能让读者饥饿。

**哲学家就餐（Dining Philosophers, Dijkstra, 1965）**：5 位哲学家围桌而坐，两人之间一根筷子，需要同时拿到左右两根才能吃。若每人都先拿起左边的筷子，就形成循环等待（死锁四条件全满足，见 [[操作系统死锁 Deadlock]]）。常用解法：

- 对筷子全局编号，哲学家总先拿编号小的——破坏循环等待；
- 允许至多 4 位哲学家同时就坐——破坏持有并等待；
- 用管程状态机让哲学家仅在两根筷子都可用时才拿起；
- 非对称方案：奇数位先左后右，偶数位先右后左。

### 现代实现：从自旋到 futex

**自旋锁（Spinlock）**：用 TAS/CAS 在用户态或内核态循环等待。持有者应在极短时间内释放，否则等待者浪费 CPU 并争用总线。Linux 内核中自旋锁还在等待时关闭本核抢占；用户态自旋只适合临界区远小于一次上下文切换代价（几十~几百纳秒）的场景。

**futex（Fast Userspace muTEX, Franke–Russell–Kirkwood, 2002 起, Linux）**：把"无竞争完全在用户态、有竞争才陷入内核"做成正式 ABI。`futex_wait(&uaddr, val)` 仅在 `*uaddr == val` 时把当前线程挂起；`futex_wake(&uaddr, n)` 唤醒 $n$ 个等待者。glibc 的 `pthread_mutex`、`sem_t`、`pthread_cond` 都建立在 futex 之上，无竞争时一次原子指令即可加解锁，竞争时才走系统调用。Windows 的 `WaitOnAddress` / `WakeByAddress` 是等价机制。

**读写锁（rwlock）**：读者共享、写者独占。POSIX `pthread_rwlock_t`、Linux `rw_semaphore`。注意 glibc 的 rwlock 默认偏好读者，持续读流会饿死写者。

**RCU（Read-Copy-Update）**：Linux 内核中的无锁读机制。读者完全不加锁，写者创建副本、修改、再发布；旧版本在所有读者退出静默区（grace period）后回收。适合读远多于写、可容忍短暂读到旧值的数据结构（路由表、进程列表）。

### 失败模式与常见误区

- **死锁**：四条件同时成立——互斥、持有并等待、不可抢占、循环等待。详见 [[操作系统死锁 Deadlock]]。
- **饥饿**：某进程长期拿不到锁或资源。可能源于不公平的锁（如某些自旋锁实现）或读者优先的读写锁。详见 [[饥饿 Starvation]]。
- **活锁**：进程未阻塞但持续做无效状态改变。例如两个进程都"礼貌地"把锁让给对方。详见 [[活锁 Livelock]]。
- **优先级反转（Priority Inversion）**：高优先级线程等待低优先级线程持有的锁，而中优先级线程又抢占了低优先级线程，导致高优先级被无限期拖慢。1997 年火星探路者号就因此复位。解决方法是**优先级继承**（持有者临时继承等待者的最高优先级，Linux `pthread_mutexattr_setprotocol(PTHREAD_PRIO_INHERIT)`）或**优先级天花板**（锁预先绑定一个最高优先级，持有者一开始就升到该优先级）。
- **误以为"原子性"只靠单条机器指令**：一条机器指令本身是原子的，但"读-改-写"序列不是。即使 `lock incq [mem]` 是原子的，它的"原子"也只是相对于其它 CPU 的普通访存；涉及多个变量的不变式仍需显式同步。
- **误以为"volatile"能解决并发**：C/C++ 的 `volatile` 只约束编译器不优化掉访存，不提供原子性、不插入内存屏障、不保证多核可见性顺序。Java 的 `volatile` 稍强（JMM 给了 acquire/release 语义），但仍不能把 `i++` 变成原子操作。应使用语言内存模型提供的原子类型（C++ `std::atomic`、Rust `Atomic*`、Java `j.u.c.a`）。
- **Peterson 算法在现代硬件上直接用是错的**：必须配合内存屏障，否则重排会让"先写 flag 再写 turn"的顺序在另一核上看起来反了。
- **Mesa 风格下用 `if (cond) wait()`**：被唤醒后条件可能已不成立，必须 `while (cond) wait()`。
- **解锁顺序**：通常应"后获取的先释放"以保持一致的加锁序，破坏加锁序是死锁的最常见来源。
- **信号量初始值错了**：互斥用初值 1；事件通知用初值 0；资源池用初值 $k$。初值大于 1 的计数信号量当互斥锁用就是 bug。

## 和我的项目的关系

暂无直接项目关联。但同步与互斥是后端服务、数据库、检索系统并发设计的底层知识：

- 高吞吐服务中的锁粒度选择（粗粒度锁 vs 细粒度锁 vs 分片锁 vs 无锁结构）直接决定 tail latency；
- RAG/检索系统里缓存、索引、连接池的并发访问都需要正确的同步原语；
- 多线程评估与评测脚本里的计数器、队列、日志聚合，若不加同步会出现静默错误，比直接崩溃更难定位；
- 理解 futex/Mesa 语义/内存模型有助于排查实际工程中"诡异"的偶发并发 bug。

## 交叉引用

- [[操作系统 Operating System]]
- [[进程与线程 Process and Thread]]
- [[操作系统运行机制 OS Runtime Mechanisms]]
- [[中断与异常 Interrupts and Exceptions]]
- [[操作系统死锁 Deadlock]]
- [[活锁 Livelock]]
- [[饥饿 Starvation]]
- [[银行家算法 Banker's Algorithm]]
- [[进程调度算法 CPU Scheduling Algorithms]]

## 更新记录

- 2026-08-06: 首次建页。涵盖临界区三要求、Peterson 与 Bakery 算法、硬件原子指令与内存屏障、信号量、管程与条件变量、三大经典问题、futex/自旋锁/RCU 及优先级反转。
