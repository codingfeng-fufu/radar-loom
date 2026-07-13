---
摘要: 缩放律以幂律刻画 LLM loss 随参数、数据、算力的下降规律。
来源: https://arxiv.org/abs/2001.08361
信度: 中
首次记录: 2026-07-13
tags: [LLM机制, 基础]
---

# Scaling Law 大模型缩放律

## 核心内容

Scaling Law(缩放律)刻画的是:在数据充分、架构合理的前提下,语言模型的测试交叉熵 loss 随参数量 $N$、数据量 $D$、训练算力 $C$ 呈**幂律下降**,即 $L(N)\approx (N_c/N)^{\alpha_N}$、$L(D)\approx (D_c/D)^{\alpha_D}$、$L(C)\approx (C_c/C)^{\alpha_C}$,且三条曲线之间存在稳定的联合关系。它把"大模型行不行"这个玄学问题变成了可外推的工程曲线:给定预算就能预测 loss、也能预测在什么规模上值得投入更多算力。

**两条主线的差异**:Kaplan 2020(OpenAI 原文)拟合出 loss 主要由 $N$ 主导,建议给定算力预算时"参数量优先、数据够用就行"—— GPT-3 175B 就是这个哲学下的产物。**Chinchilla 2022**(DeepMind)用更大的扫参范围重新拟合,得出计算最优的正确配比是**参数与数据大致按 1:20 同步放大**(即 70B 模型应配 1.4T tokens),推翻了 Kaplan 的"重参数轻数据"结论,直接催生了 LLaMA、DeepSeek 等"小参数大数据"训练范式的转向。

**关键区别于 [[涌现能力 Emergent Abilities]]**:缩放律描述的是 loss 的**连续、平滑、可预测**下降;涌现描述的是下游任务准确率在某个规模阈值后**离散、跳跃**的能力出现。同一份训练曲线,前者看 loss 曲线,后者看具体 benchmark 得分,两者互不替代。近年也有工作(Schaeffer 2023)质疑涌现只是指标选择造成的假象,如果换成平滑指标,涌现会退化回一条缩放律。

## 曲线可视化

**图 1 · 三条幂律曲线(log-log 坐标下呈直线)**

<figure>
<svg viewBox="0 0 720 260" role="img" aria-label="L(N)、L(D)、L(C) 三条幂律曲线在 log-log 坐标下的对比">
  <!-- panel N -->
  <g>
    <text x="44" y="14" font-size="12" font-weight="600" fill="#2a78d6">■ L(N) · α = 0.076</text>
    <line x1="44"  y1="36"     x2="228" y2="36"     stroke="#e1e0d9"/>
    <line x1="44"  y1="72.13"  x2="228" y2="72.13"  stroke="#e1e0d9"/>
    <line x1="44"  y1="126.56" x2="228" y2="126.56" stroke="#e1e0d9"/>
    <line x1="44"  y1="169.91" x2="228" y2="169.91" stroke="#e1e0d9"/>
    <line x1="44"  y1="200.68" x2="228" y2="200.68" stroke="#e1e0d9"/>
    <text x="38" y="39"     font-size="10" fill="#898781" text-anchor="end">7</text>
    <text x="38" y="75.13"  font-size="10" fill="#898781" text-anchor="end">5</text>
    <text x="38" y="129.56" font-size="10" fill="#898781" text-anchor="end">3</text>
    <text x="38" y="172.91" font-size="10" fill="#898781" text-anchor="end">2</text>
    <text x="38" y="203.68" font-size="10" fill="#898781" text-anchor="end">1.5</text>
    <path d="M44,36 L44,216 L228,216" stroke="#c3c2b7" fill="none"/>
    <text x="44"     y="232" font-size="10" fill="#898781" text-anchor="middle">1e5</text>
    <text x="105.33" y="232" font-size="10" fill="#898781" text-anchor="middle">1e7</text>
    <text x="166.67" y="232" font-size="10" fill="#898781" text-anchor="middle">1e9</text>
    <text x="228"    y="232" font-size="10" fill="#898781" text-anchor="middle">1e11</text>
    <text x="136"    y="252" font-size="11" fill="#52514e" text-anchor="middle">N (参数量)</text>
    <text transform="translate(14,126) rotate(-90)" font-size="11" fill="#52514e" text-anchor="middle">Loss (nats)</text>
    <line x1="44" y1="76.64" x2="228" y2="188.96" stroke="#2a78d6" stroke-width="2" stroke-linecap="round"/>
  </g>
  <!-- panel D -->
  <g>
    <text x="284" y="14" font-size="12" font-weight="600" fill="#1baf7a">■ L(D) · α = 0.095</text>
    <line x1="284" y1="36"     x2="468" y2="36"     stroke="#e1e0d9"/>
    <line x1="284" y1="72.13"  x2="468" y2="72.13"  stroke="#e1e0d9"/>
    <line x1="284" y1="126.56" x2="468" y2="126.56" stroke="#e1e0d9"/>
    <line x1="284" y1="169.91" x2="468" y2="169.91" stroke="#e1e0d9"/>
    <line x1="284" y1="200.68" x2="468" y2="200.68" stroke="#e1e0d9"/>
    <path d="M284,36 L284,216 L468,216" stroke="#c3c2b7" fill="none"/>
    <text x="284"   y="232" font-size="10" fill="#898781" text-anchor="middle">1e6</text>
    <text x="357.6" y="232" font-size="10" fill="#898781" text-anchor="middle">1e8</text>
    <text x="431.2" y="232" font-size="10" fill="#898781" text-anchor="middle">1e10</text>
    <text x="376"   y="252" font-size="11" fill="#52514e" text-anchor="middle">D (tokens)</text>
    <line x1="284" y1="63.13" x2="468" y2="180.12" stroke="#1baf7a" stroke-width="2" stroke-linecap="round"/>
  </g>
  <!-- panel C -->
  <g>
    <text x="524" y="14" font-size="12" font-weight="600" fill="#c98500">■ L(C) · α = 0.050</text>
    <line x1="524" y1="36"     x2="708" y2="36"     stroke="#e1e0d9"/>
    <line x1="524" y1="72.13"  x2="708" y2="72.13"  stroke="#e1e0d9"/>
    <line x1="524" y1="126.56" x2="708" y2="126.56" stroke="#e1e0d9"/>
    <line x1="524" y1="169.91" x2="708" y2="169.91" stroke="#e1e0d9"/>
    <line x1="524" y1="200.68" x2="708" y2="200.68" stroke="#e1e0d9"/>
    <path d="M524,36 L524,216 L708,216" stroke="#c3c2b7" fill="none"/>
    <text x="524"    y="232" font-size="10" fill="#898781" text-anchor="middle">1e-3</text>
    <text x="576.57" y="232" font-size="10" fill="#898781" text-anchor="middle">1e-1</text>
    <text x="629.14" y="232" font-size="10" fill="#898781" text-anchor="middle">1e1</text>
    <text x="681.71" y="232" font-size="10" fill="#898781" text-anchor="middle">1e3</text>
    <text x="616"    y="252" font-size="11" fill="#52514e" text-anchor="middle">C (PF-days)</text>
    <line x1="524" y1="102.57" x2="708" y2="188.79" stroke="#c98500" stroke-width="2" stroke-linecap="round"/>
  </g>
</svg>
<figcaption style="color:#898781;font-size:12px;margin-top:4px">
幂律 $L=(x_c/x)^\alpha$ 在 log-log 图上是直线,斜率 $=-\alpha$。三条线斜率不同:$\alpha_D > \alpha_N > \alpha_C$,意味着等比例扩大时,数据的边际贡献最陡、算力最平缓。任何弯折都说明模型已跌出该维度的幂律区间。
</figcaption>
</figure>

**图 2 · Kaplan vs Chinchilla:固定算力下的最优参数量**

<figure>
<svg viewBox="0 0 720 360" role="img" aria-label="Kaplan 2020 与 Chinchilla 2022 在固定算力下推荐的最优参数量对比">
  <!-- horizontal gridlines: N = 1e7..1e13 -->
  <line x1="74" y1="306" x2="696" y2="306" stroke="#e1e0d9"/>
  <line x1="74" y1="259" x2="696" y2="259" stroke="#e1e0d9"/>
  <line x1="74" y1="212" x2="696" y2="212" stroke="#e1e0d9"/>
  <line x1="74" y1="165" x2="696" y2="165" stroke="#e1e0d9"/>
  <line x1="74" y1="118" x2="696" y2="118" stroke="#e1e0d9"/>
  <line x1="74" y1="71"  x2="696" y2="71"  stroke="#e1e0d9"/>
  <line x1="74" y1="24"  x2="696" y2="24"  stroke="#e1e0d9"/>
  <text x="68" y="309" font-size="10.5" fill="#898781" text-anchor="end">1e7</text>
  <text x="68" y="262" font-size="10.5" fill="#898781" text-anchor="end">1e8</text>
  <text x="68" y="215" font-size="10.5" fill="#898781" text-anchor="end">1e9</text>
  <text x="68" y="168" font-size="10.5" fill="#898781" text-anchor="end">1e10</text>
  <text x="68" y="121" font-size="10.5" fill="#898781" text-anchor="end">1e11</text>
  <text x="68" y="74"  font-size="10.5" fill="#898781" text-anchor="end">1e12</text>
  <text x="68" y="27"  font-size="10.5" fill="#898781" text-anchor="end">1e13</text>
  <!-- axes -->
  <path d="M74,24 L74,306 L696,306" stroke="#c3c2b7" fill="none"/>
  <!-- x ticks: C = 1e18,1e20,1e22,1e24,1e26 -->
  <text x="74"    y="322" font-size="10.5" fill="#898781" text-anchor="middle">1e18</text>
  <text x="229.5" y="322" font-size="10.5" fill="#898781" text-anchor="middle">1e20</text>
  <text x="385"   y="322" font-size="10.5" fill="#898781" text-anchor="middle">1e22</text>
  <text x="540.5" y="322" font-size="10.5" fill="#898781" text-anchor="middle">1e24</text>
  <text x="696"   y="322" font-size="10.5" fill="#898781" text-anchor="middle">1e26</text>
  <text x="385" y="346" font-size="12" fill="#52514e" text-anchor="middle">算力 C (FLOPs)</text>
  <text transform="translate(20,165) rotate(-90)" font-size="12" fill="#52514e" text-anchor="middle">最优参数量 N</text>

  <!-- Kaplan: N = k1 * C^0.73, endpoints (1e18, 1.70e7) → (1e26, 1.17e13, clip near top) -->
  <line x1="74" y1="295.19" x2="696" y2="24" stroke="#eb6834" stroke-width="2" stroke-linecap="round"/>
  <!-- Chinchilla: N = k2 * C^0.50, endpoints (1e18, 7.14e7) → (1e26, 7.14e11) -->
  <line x1="74" y1="266.14" x2="696" y2="77.86" stroke="#2a78d6" stroke-width="2" stroke-linecap="round"/>

  <!-- GPT-3 anchor on Kaplan line: C=3.14e23, N=1.75e11 → (501.28, 106.58) -->
  <circle cx="501.28" cy="106.58" r="5.5" fill="#eb6834" stroke="#fcfcfb" stroke-width="2"/>
  <text x="493" y="98" font-size="11.5" fill="#eb6834" font-weight="600" text-anchor="end">GPT-3 (175B)</text>

  <!-- Chinchilla-optimal at same compute: C=3.14e23, N≈4e10 → (501.28, 136.71) -->
  <circle cx="501.28" cy="136.71" r="5" fill="#2a78d6" stroke="#fcfcfb" stroke-width="2"/>
  <text x="493" y="152" font-size="11.5" fill="#2a78d6" font-weight="600" text-anchor="end">Chinchilla-optimal · 同算力</text>

  <!-- gap line -->
  <line x1="501.28" y1="106.58" x2="501.28" y2="136.71" stroke="#898781" stroke-width="1" stroke-dasharray="4 3"/>

  <!-- direct labels on curves at right end -->
  <text x="702" y="28"  font-size="12" fill="#eb6834" font-weight="600">Kaplan</text>
  <text x="702" y="82"  font-size="12" fill="#2a78d6" font-weight="600">Chinchilla</text>

  <!-- legend / annotation -->
  <text x="90"  y="46" font-size="11" fill="#52514e">Kaplan (N ∝ C^0.73):算力翻 10× → 参数翻 5.4×、数据翻 1.9×</text>
  <text x="90"  y="62" font-size="11" fill="#52514e">Chinchilla (N ∝ C^0.50):算力翻 10× → 参数与数据各翻 3.2×</text>
</svg>
<figcaption style="color:#898781;font-size:12px;margin-top:4px">
同一算力预算 C 下两派给出的最优 N。虚线段落展示 GPT-3 与 Chinchilla-optimal 在同算力下的差距——Chinchilla 拟合表明 GPT-3 在给定算力上**参数过大、数据不足**,这正是 LLaMA 系列反过来"小参数大数据"的直接动因。
</figcaption>
</figure>

> 互动版(含 hover 十字线、tooltip、深色模式):`reports/2026-07-13_scaling-law-curves.html`

## 和我的项目的关系

缩放律对我目前的方向主要是**框定预算和选型**的工具,而非直接建模对象:

- [[TripleChecker]] / KG 抽取管线:缩放律告诉我在 KG 抽取任务上,7B → 70B 的收益是可预测的幂律下降而非线性,给定 GPU 预算可以先算好 loss 差,再决定是否值得上更大的 backbone。Chinchilla 配比也提示我在做领域微调时,不能只堆参数不喂数据。
- [[EvidenceFirst]] / 可信度评测:缩放律本身**不改善事实性和可信度**——loss 降低不等于幻觉减少,这也是为什么需要 RAG、模型校准等外挂机制。这一点在面试时可以作为"为什么光靠 scaling 解决不了 hallucination"的标准回答。
- 与 [[涌现能力 Emergent Abilities]] 的辩证:缩放律给了可预测性,涌现给了不可预测性,项目设计上要两边都留手——评测指标既要看 loss 类的平滑量,也要看下游任务的阈值行为。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[涌现能力 Emergent Abilities]]
- [[预训练与微调 Pretrain vs Finetune]]
- [[语言模型困惑度 Perplexity]]
- [[TripleChecker]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-13: 首次建页
