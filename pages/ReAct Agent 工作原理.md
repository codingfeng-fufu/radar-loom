---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [多智能体]
---

# ReAct Agent 工作原理

## 核心内容

ReAct是2022年提出的Agent经典范式，现在是几乎所有LLM Agent的基础架构。核心模式：让LLM交替输出推理（Thought）和动作（Action）——先想「我现在需要做什么」，然后调用工具执行，拿到观察（Observation）后，再想下一步做什么，循环往复直到得到最终答案。ReAct的创新点是把「推理链」和「工具使用」结合起来了，之前的CoT只有推理没有行动，之前的工具调用只有行动没有推理。ReAct的优势是每一步都有明确的推理过程，出问题时可以回溯哪一步想错了；缺点是对LLM的指令遵循能力要求很高，经常跑偏或死循环。

## 和我的项目的关系

[[EvidenceFirst]]里的确定性状态机本质上就是把ReAct的「Thought-Action-Observation」循环从LLM手里拿出来，变成硬编码的确定性规则。ReAct让LLM自己决定下一步做什么，结果不稳定；EvidenceFirst不让LLM做决策，LLM只负责自然语言理解和生成，结构决策完全由状态机做。这个对比非常适合在面试里讲：ReAct是「神经Agent」，EvidenceFirst是「神经符号Agent」——我用符号系统接管了最关键的结构决策部分，只把语义理解留给LLM，这样就把LLM的优势和符号系统的优势都发挥出来了。

## 交叉引用

- [[多智能体系统 Multi-Agent Systems]]
- [[Agent 记忆架构]]
- [[思维链 Chain-of-Thought]]
- [[神经符号方法 Neuro-Symbolic AI]]
- [[确定性状态机 Deterministic State Machine]]

## 更新记录

- 2026-07-04: 首次建页
