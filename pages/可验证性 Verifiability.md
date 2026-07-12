---
来源: papers/trustworthy_ai_and_frontier_1.pdf
信度: 高
首次记录: 2026-07-04
tags: [可信度, EvidenceFirst]
---

# 可验证性 Verifiability

## 核心内容

可验证性是指AI系统的输出和推理过程可以被客观检验和确认的属性。与可审计性强调第三方检验不同，可验证性更关注「每一步是否都有依据支撑」。在KG-RAG系统中，可验证性意味着生成的答案必须能够被知识图谱中的路径或节点支撑，每一个事实陈述都有对应的证据来源。核心方法包括证据路径检查、NLI验证来源与结论的蕴含关系、结构化状态标记。

## 和我的项目的关系

[[EvidenceFirst]]和[[TripleChecker]]都围绕可验证性设计。TripleChecker用NLI模型验证三元组是否被来源文本蕴含，是抽取阶段的可验证性。EvidenceFirst用确定性状态机验证答案是否被图谱路径支撑，是推理阶段的可验证性。两者共同构成了从数据抽取到推理输出的完整可验证性链条，这是我研究工作的主线。

## 交叉引用

- [[幻觉与可信度 Hallucination Trustworthiness]]
- [[EvidenceFirst]]
- [[TripleChecker]]
- [[可观测性 Observability]]
- [[可审计性 Auditability]]
- [[文本蕴含与自然语言推理 NLI]]

## 更新记录

- 2026-07-04: 首次建页
