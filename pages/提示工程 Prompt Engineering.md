---
来源: papers/foundational_knowledge_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [LLM机制]
---

# 提示工程 Prompt Engineering

## 核心内容

提示工程是通过设计输入prompt的格式、内容、示例来引导LLM输出想要的结果，是大模型应用开发最基础的技能。几个关键原则：明确任务，直接说你要什么，不要让模型猜；提供示例，Few-shot效果通常比Zero-shot好；引导推理，让模型一步一步想而不是直接给答案（Chain-of-Thought）；指定输出格式，如果需要JSON或特定结构就明确说；设置温度参数，需要创造性就调高，需要确定性就设为0。提示工程本质上是和LLM的「统计直觉」对话——你不是在给计算机写精确指令，你是在引导这个统计模型进入你想要的输出分布。

## 和我的项目的关系

提示工程是我所有工作的「隐形基础设施」。[[TripleChecker]]里的三元组抽取、NLI验证都是靠精心设计的prompt；[[EvidenceFirst]]里的实体映射、答案生成都需要prompt engineering。很多人忽略这一点，以为LLM就是调用API，但实际上prompt写得好不好直接决定最终效果——同一个模型，好的prompt可能比差的prompt准确率高20%以上。面试时可以主动提：我的工作不止是架构设计，我真的写过几百条prompt做AB测试，知道怎么把LLM的性能压榨到极限。

## 交叉引用

- [[大模型机制与推理 LLM Mechanisms]]
- [[上下文学习 In-context Learning]]
- [[思维链 Chain-of-Thought]]
- [[TripleChecker]]
- [[EvidenceFirst]]

## 更新记录

- 2026-07-04: 首次建页
