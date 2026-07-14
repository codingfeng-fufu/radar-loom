# 索引(机器生成,勿手工编辑)

> 生成:2026-07-14 · 页面 98 · 运行 `python3 scripts/build_index.py` 刷新

## KG

- [[FinGraph 财务知识图谱]] `#KG` — FinGraph是专门为财务分析场景设计的领域知识图谱，核心是把财报中的结构化和非结构化数据转化为可计算的图结构。
- [[GNN-RAG 图神经网络检索增强]] `#RAG #KG #前沿` — GNN-RAG（arxiv 2024）把 GNN 引入 RAG 的检索阶段。
- [[Graph Fusion 图融合]] `#KG` — Graph Fusion是解决多来源知识图谱融合问题的技术，把多个异构KG合并成一个统一的高质量KG。
- [[KG-RAG 工作原理]] `#KG #RAG` — KG-RAG在普通RAG的向量检索之外，额外引入知识图谱作为结构化检索层。
- [[SHA-256 产物指纹]] `#KG #EvidenceFirst` — SHA-256指纹用于验证实验产物未被修改并保证结果可复现。
- [[StructRAG 结构化知识推理]] `#RAG #KG #前沿` — StructRAG（Li et al.
- [[TransE 图嵌入]] `#KG` — TransE把知识图谱关系建模为头实体到尾实体的向量平移。
- [[主流知识图谱 Mainstream KGs]] `#KG` — 主流知识图谱包括Wikidata、DBpedia、YAGO及领域知识图谱。
- [[人类反馈的知识图谱构建 Human-in-the-Loop KG]] `#KG` — 人机协同知识图谱构建用人工反馈校正LLM执行的抽取与融合任务。
- [[依存句法分析 Dependency Parsing]] `#KG #基础` — 依存句法分析是分析句子里词和词之间的语法依存关系的任务，用有向图表示，边从修饰词指向被修饰词，边上标注关系类型。
- [[关系图卷积网络 RGCN]] `#KG` — RGCN是专门为异构图（有多种类型的节点和边的图，知识图谱就是典型的异构图）设计的GNN变体。
- [[命名实体识别 NER]] `#KG #基础` — 命名实体识别是从文本中识别出具有特定意义实体的任务，是知识图谱构建的第一步。
- [[图神经网络 GNN]] `#KG` — 图神经网络通过消息传递聚合邻居信息并学习节点表示。
- [[图结构一致性 Graph Structure Consistency]] `#KG` — 图结构一致性是指知识图谱内部的三元组在结构上不自相矛盾。
- [[实体对齐 Entity Alignment]] `#KG` — 实体对齐是判断不同知识图谱（或同一图谱不同来源）里的两个实体是否指向同一个现实世界对象的问题。
- [[实体消歧 Entity Disambiguation]] `#KG` — 实体消歧是指在文本中识别出一个实体名称后，确定它指向知识库中哪个具体实体的过程，又称实体链接。
- [[序列标注模型 HMM CRF]] `#KG #基础` — HMM与CRF以概率图模型方式联合预测序列中各位置的标签。
- [[开放信息抽取 OpenIE]] `#KG` — OpenIE无需预定义关系本体即可从文本抽取开放类型三元组。
- [[异构图 Heterogeneous Graph]] `#KG` — 异构图同时包含多种节点和关系类型，知识图谱是其典型形式。
- [[文本蕴含与自然语言推理 NLI]] `#KG #TripleChecker` — NLI判断前提文本对假设是蕴含、矛盾还是中立，并可用于知识验证。
- [[本体 Ontology]] `#KG` — 本体定义知识图谱中的概念类、关系和约束，是图谱的模式层。
- [[知识冲突 Knowledge Conflict]] `#KG #RAG` — 知识冲突是指模型的参数化知识（训练时记住的）和检索到的外部知识（KG或文本）发生矛盾时如何处理的问题。
- [[知识图谱构建流程 KG Construction Pipeline]] `#KG` — 知识图谱构建涵盖数据获取、信息抽取、对齐、融合和质量评估。
- [[知识图谱补全 Knowledge Graph Completion]] `#KG` — 知识图谱补全是填补KG中缺失三元组的任务，KG天生是不完整的——总有一些关系没有被抽取出来。
- [[知识图谱质量评估维度]] `#KG #TripleChecker #评测` — 知识图谱质量由完整性、准确性、一致性、时效性和溯源性衡量。
- [[知识接地 Grounding]] `#KG #RAG` — Grounding（接地）是指生成的内容能够追溯并锚定到具体的、外部可验证的证据上，而不是悬空依赖模型的参数化记忆。
- [[确定性状态机 Deterministic State Machine]] `#KG #EvidenceFirst` — 确定性状态机用固定规则产生可复现、可解释的系统状态判断。
- [[神经符号方法 Neuro-Symbolic AI]] `#KG` — 神经符号方法试图结合神经网络的学习能力和符号系统的可解释性、确定性推理能力，是当前可信AI研究的重要方向。
- [[符号人工智能 Symbolic AI]] `#KG` — 符号AI是用显式的逻辑规则、符号、谓词来表示和操作知识的AI范式，典型如知识图谱、专家系统、逻辑推理机。
- [[置信度评分 Confidence Scoring]] `#KG #TripleChecker` — 置信度评分是给知识图谱里的每条三元组或每个节点分配一个可靠性分数，解决KG构建质量不均的问题。
- [[词性标注 POS Tagging]] `#KG #基础` — 词性标注是给句子里每个词标注语法类别的任务，是很多 NLP 任务的预处理步骤。
- [[资源描述框架 RDF OWL SPARQL]] `#KG` — RDF（资源描述框架）是W3C制定的知识表示标准，用三元组（主语，谓词，宾语）来表示知识，每个元素用URI标识。
- [[链接预测 Link Prediction]] `#KG` — 链接预测是知识图谱补全最常见的子任务，目标是预测两个实体之间是否存在某种特定关系，或者预测给定头实体和关系的尾实体。

## RAG

- [[GNN-RAG 图神经网络检索增强]] `#RAG #KG #前沿` — GNN-RAG（arxiv 2024）把 GNN 引入 RAG 的检索阶段。
- [[GraphRAG 架构]] `#RAG` — 微软GraphRAG是2024年引爆GraphRAG方向的经典工作。
- [[KG-RAG 工作原理]] `#KG #RAG` — KG-RAG在普通RAG的向量检索之外，额外引入知识图谱作为结构化检索层。
- [[LightRAG]] `#RAG` — LightRAG以实体图上的局部和全局检索简化GraphRAG流程。
- [[RAG 评测指标 EM Recall MRR]] `#RAG #评测` — RAG评测分别衡量检索召回、排序质量和最终答案准确性。
- [[RAGChecker]] `#RAG #可信度` — RAGChecker以细粒度指标分别诊断RAG的检索和生成错误。
- [[Self-RAG]] `#RAG` — Self-RAG是让LLM学会自我反思的RAG框架，ICLR 2024的代表作。
- [[StructRAG 结构化知识推理]] `#RAG #KG #前沿` — StructRAG（Li et al.
- [[交替检索推理 IRCoT]] `#RAG` — IRCoT在多跳问答中交替执行思维链推理与证据检索。
- [[信息检索 IR基础模型 Information Retrieval]] `#RAG #基础` — 信息检索从布尔匹配、向量空间发展到概率模型和神经检索。
- [[分布偏移 Distribution Shift]] `#可信度 #RAG` — 分布偏移是指模型部署时遇到的数据分布和训练/测试时的数据分布不一致，是AI系统落地失败的首要原因之一。
- [[混合检索 Hybrid Retrieval]] `#RAG` — 混合检索是把多种检索策略的结果融合起来，弥补单一策略的盲区。
- [[知识冲突 Knowledge Conflict]] `#KG #RAG` — 知识冲突是指模型的参数化知识（训练时记住的）和检索到的外部知识（KG或文本）发生矛盾时如何处理的问题。
- [[知识接地 Grounding]] `#KG #RAG` — Grounding（接地）是指生成的内容能够追溯并锚定到具体的、外部可验证的证据上，而不是悬空依赖模型的参数化记忆。
- [[纠错RAG CRAG]] `#RAG #可信度` — CRAG先评估检索质量，再通过补充搜索和结果融合纠正RAG输入。

## LLM机制

- [[BERT与GPT的区别 BERT vs GPT]] `#LLM机制 #基础` — BERT 和 GPT 是 Transformer 架构的两个代表性分支，核心区别在于注意力方向和预训练任务。
- [[LLM 推理优化 KV Cache Quantization]] `#LLM机制` — LLM推理优化的两个核心技术是KV Cache和量化。
- [[Scaling Law 大模型缩放律]] `#LLM机制 #基础` — 缩放律以幂律刻画 LLM loss 随参数、数据、算力的下降规律。
- [[Transformer 自注意力机制]] `#LLM机制 #基础` — 自注意力机制是Transformer的核心，也是大模型技术栈的基础技术。
- [[上下文学习 In-context Learning]] `#LLM机制` — 上下文学习让LLM仅凭提示中的示例完成任务而无需更新参数。
- [[人类反馈强化学习 RLHF]] `#LLM机制` — RLHF是让LLM对齐人类偏好的核心技术，ChatGPT就是用RLHF做的对齐。
- [[位置编码 Positional Encoding]] `#LLM机制 #基础` — 位置编码为Transformer注入词序信息以打破注意力的排列不变性。
- [[卷积神经网络 CNN]] `#LLM机制 #基础` — 卷积神经网络的核心思想是局部连接和权重共享。
- [[层归一化 LayerNorm BatchNorm]] `#LLM机制 #基础` — BatchNorm与LayerNorm通过不同归一化维度稳定神经网络训练。
- [[强化学习基本框架 Reinforcement Learning]] `#LLM机制 #基础` — 强化学习通过智能体与环境交互并最大化累积奖励来学习策略。
- [[循环神经网络 RNN LSTM]] `#LLM机制 #基础` — 循环神经网络在每个时间步用相同的权重处理序列，当前隐藏状态由当前输入和上一时间步的隐藏状态共同决定。
- [[思维链 Chain-of-Thought]] `#LLM机制` — 思维链提示通过显式中间推理步骤提升LLM复杂任务表现。
- [[提示工程 Prompt Engineering]] `#LLM机制` — 提示工程是通过设计输入prompt的格式、内容、示例来引导LLM输出想要的结果，是大模型应用开发最基础的技能。
- [[数据增强 Data Augmentation]] `#LLM机制 #基础` — 数据增强是通过对现有数据做各种变换来生成新的训练数据，从而增加数据多样性、减少过拟合。
- [[文本摘要 Text Summarization]] `#LLM机制 #基础` — 文本摘要通过抽取式或生成式方法压缩原文并保留关键信息。
- [[旋转位置编码 RoPE]] `#LLM机制 #基础` — RoPE（旋转位置编码）是现在LLM最常用的位置编码方案，GPT-3、LLaMA系列都用它。
- [[机器翻译 Machine Translation]] `#LLM机制 #基础` — 机器翻译经历规则、统计、神经网络到大模型驱动的技术演进。
- [[涌现能力 Emergent Abilities]] `#LLM机制` — 涌现能力是指当模型规模超过某个阈值后，突然出现的能力——在小模型上几乎不存在，在大模型上性能显著提升。
- [[激活函数 Activation Functions]] `#LLM机制 #基础` — 激活函数为神经网络引入非线性，没有它多层网络等价于单层线性模型。
- [[语言模型困惑度 Perplexity]] `#LLM机制` — 困惑度（Perplexity，PPL）是评估语言模型最经典的指标，衡量模型对测试文本的「惊讶程度」。
- [[过拟合 Overfitting]] `#LLM机制 #基础` — 过拟合指模型记住训练噪声而无法泛化到验证集和测试集。
- [[预训练与微调 Pretrain vs Finetune]] `#LLM机制 #基础` — 预训练学习通用语言表示，微调让基础模型适配特定任务和领域。

## 可信度

- [[RAGChecker]] `#RAG #可信度` — RAGChecker以细粒度指标分别诊断RAG的检索和生成错误。
- [[ReDeEP 机制可解释性]] `#可信度 #前沿` — ReDeEP（Sun et al.
- [[不确定性量化 Uncertainty Quantification]] `#可信度` — 不确定性量化是让模型不仅给出预测，还给出对这个预测的置信程度。
- [[分层评测 Stratified Evaluation]] `#可信度 #EvidenceFirst #评测` — 分层评测是指不满足于报告整体平均指标，而是把测试集按某种属性（难度、类别、状态）划分成不同子集分别报告性能。
- [[分布偏移 Distribution Shift]] `#可信度 #RAG` — 分布偏移是指模型部署时遇到的数据分布和训练/测试时的数据分布不一致，是AI系统落地失败的首要原因之一。
- [[反事实评测 Counterfactual Evaluation]] `#可信度 #EvidenceFirst #评测` — 反事实评测通过系统性地改变输入的某个属性，观察输出如何变化，来理解模型的依赖关系和潜在偏见。
- [[可审计性 Auditability]] `#可信度 #EvidenceFirst` — 可审计性是指第三方（监管者、用户、内审人员）能够独立检验AI系统决策过程和依据的能力，不需要依赖系统开发者的说明。
- [[可观测性 Observability]] `#可信度 #EvidenceFirst` — 可观测性是指系统能够暴露其内部运行状态的能力，来自软件工程和分布式系统领域。
- [[可验证性 Verifiability]] `#可信度 #EvidenceFirst` — 可验证性是指AI系统的输出和推理过程可以被客观检验和确认的属性。
- [[审计风险队列 Audit Risk Queue]] `#可信度 #EvidenceFirst` — 审计风险队列按风险排序样本以集中有限的人工审查资源。
- [[对抗样本 Adversarial Examples]] `#可信度` — 对抗样本是经过精心设计的微小扰动输入，对人类几乎不可察觉，但能让模型产生完全错误的输出。
- [[引用召回与精确率 Citation Recall Precision]] `#可信度 #TripleChecker #评测` — 引用召回率与精确率衡量生成声明是否得到充分且正确的证据支持。
- [[归因评测 Attribution]] `#可信度 #TripleChecker #评测` — 归因评测是指验证生成内容里的具体声明（claim）是否能在指定的来源材料中找到支撑证据的过程。
- [[提示注入 Prompt Injection]] `#可信度` — 提示注入通过恶意输入劫持LLM指令并破坏既定行为边界。
- [[机器遗忘 Machine Unlearning]] `#可信度 #前沿` — 机器遗忘让训练好的模型精确去除特定训练数据的影响,服务隐私合规与被遗忘权。
- [[模型校准 Calibration]] `#可信度` — 模型校准衡量的是「模型说它有80%把握的时候，是不是真的大约80%的情况下是对的」。
- [[溯源 Provenance]] `#可信度 #EvidenceFirst` — 溯源记录数据或结论的来源、转换过程和依赖关系。
- [[纠错RAG CRAG]] `#RAG #可信度` — CRAG先评估检索质量，再通过补充搜索和结果融合纠正RAG输入。
- [[红队测试 Red-teaming]] `#可信度` — 红队测试是主动尝试攻破一个AI系统的可信性，找出它的失败模式，类似网络安全里的渗透测试。
- [[选择性预测 Selective Prediction]] `#可信度` — 选择性预测允许模型在不确定时拒答，以降低已回答样本的风险。

## 多智能体

- [[Agent 记忆架构]] `#多智能体` — Agent记忆由工作记忆、情景记忆和语义记忆三个层次协同构成。
- [[ReAct Agent 工作原理]] `#多智能体` — ReAct是2022年提出的Agent经典范式，现在是几乎所有LLM Agent的基础架构。

## 基础

- [[BERT与GPT的区别 BERT vs GPT]] `#LLM机制 #基础` — BERT 和 GPT 是 Transformer 架构的两个代表性分支，核心区别在于注意力方向和预训练任务。
- [[EM算法 Expectation-Maximization]] `#基础` — EM算法是一种处理含隐变量的极大似然估计的迭代算法,通过E步求隐变量后验期望、M步最大化期望对数似然,交替进行直至收敛。
- [[Scaling Law 大模型缩放律]] `#LLM机制 #基础` — 缩放律以幂律刻画 LLM loss 随参数、数据、算力的下降规律。
- [[Transformer 自注意力机制]] `#LLM机制 #基础` — 自注意力机制是Transformer的核心，也是大模型技术栈的基础技术。
- [[主题模型 LDA]] `#基础` — LDA（Latent Dirichlet Allocation，潜在狄利克雷分配）是一种无监督的文本主题发现模型。
- [[位置编码 Positional Encoding]] `#LLM机制 #基础` — 位置编码为Transformer注入词序信息以打破注意力的排列不变性。
- [[依存句法分析 Dependency Parsing]] `#KG #基础` — 依存句法分析是分析句子里词和词之间的语法依存关系的任务，用有向图表示，边从修饰词指向被修饰词，边上标注关系类型。
- [[信息检索 IR基础模型 Information Retrieval]] `#RAG #基础` — 信息检索从布尔匹配、向量空间发展到概率模型和神经检索。
- [[关联规则挖掘 Apriori]] `#基础` — 关联规则挖掘是从事务数据库里找频繁共现的项目集的任务，典型场景是购物篮分析。
- [[卷积神经网络 CNN]] `#LLM机制 #基础` — 卷积神经网络的核心思想是局部连接和权重共享。
- [[变分自编码器 VAE Variational Autoencoder]] `#基础` — VAE用神经网络参数化隐变量后验和生成器,通过最大化ELBO训练,是EM思想在深度生成模型上的延伸,也是扩散模型的前身。
- [[命名实体识别 NER]] `#KG #基础` — 命名实体识别是从文本中识别出具有特定意义实体的任务，是知识图谱构建的第一步。
- [[对比学习 Contrastive Learning]] `#基础` — 对比学习通过拉近正样本对、推开负样本对学习表示,以InfoNCE为核心损失,是稠密检索与多模态对齐的基础范式。
- [[层归一化 LayerNorm BatchNorm]] `#LLM机制 #基础` — BatchNorm与LayerNorm通过不同归一化维度稳定神经网络训练。
- [[序列标注模型 HMM CRF]] `#KG #基础` — HMM与CRF以概率图模型方式联合预测序列中各位置的标签。
- [[强化学习基本框架 Reinforcement Learning]] `#LLM机制 #基础` — 强化学习通过智能体与环境交互并最大化累积奖励来学习策略。
- [[循环神经网络 RNN LSTM]] `#LLM机制 #基础` — 循环神经网络在每个时间步用相同的权重处理序列，当前隐藏状态由当前输入和上一时间步的隐藏状态共同决定。
- [[扩散模型 Diffusion Models DDPM]] `#基础` — 扩散模型通过前向加噪与反向去噪学习数据分布,训练目标是分层VAE的ELBO简化形式,已成为主流生成模型。
- [[数据增强 Data Augmentation]] `#LLM机制 #基础` — 数据增强是通过对现有数据做各种变换来生成新的训练数据，从而增加数据多样性、减少过拟合。
- [[文本摘要 Text Summarization]] `#LLM机制 #基础` — 文本摘要通过抽取式或生成式方法压缩原文并保留关键信息。
- [[旋转位置编码 RoPE]] `#LLM机制 #基础` — RoPE（旋转位置编码）是现在LLM最常用的位置编码方案，GPT-3、LLaMA系列都用它。
- [[机器翻译 Machine Translation]] `#LLM机制 #基础` — 机器翻译经历规则、统计、神经网络到大模型驱动的技术演进。
- [[激活函数 Activation Functions]] `#LLM机制 #基础` — 激活函数为神经网络引入非线性，没有它多层网络等价于单层线性模型。
- [[词性标注 POS Tagging]] `#KG #基础` — 词性标注是给句子里每个词标注语法类别的任务，是很多 NLP 任务的预处理步骤。
- [[过拟合 Overfitting]] `#LLM机制 #基础` — 过拟合指模型记住训练噪声而无法泛化到验证集和测试集。
- [[预训练与微调 Pretrain vs Finetune]] `#LLM机制 #基础` — 预训练学习通用语言表示，微调让基础模型适配特定任务和领域。
- [[马尔可夫 Markov]] `#基础` — 未来只依赖当下的建模假设,派生出马尔可夫链/HMM/MDP/MCMC等一族方法
- [[高斯混合模型 GMM Gaussian Mixture Model]] `#基础` — GMM是用K个高斯分量的加权和拟合数据的概率模型,通过EM算法估计参数,常用于软聚类和密度估计。

## 评测

- [[McNemar检验]] `#评测` — McNemar检验是专门用于配对二分类数据的统计显著性检验方法，是NLP实验中比较两个系统差异的标配工具。
- [[RAG 评测指标 EM Recall MRR]] `#RAG #评测` — RAG评测分别衡量检索召回、排序质量和最终答案准确性。
- [[分层评测 Stratified Evaluation]] `#可信度 #EvidenceFirst #评测` — 分层评测是指不满足于报告整体平均指标，而是把测试集按某种属性（难度、类别、状态）划分成不同子集分别报告性能。
- [[反事实评测 Counterfactual Evaluation]] `#可信度 #EvidenceFirst #评测` — 反事实评测通过系统性地改变输入的某个属性，观察输出如何变化，来理解模型的依赖关系和潜在偏见。
- [[基准数据集 Benchmark]] `#评测` — 基准数据集提供统一的评测标准，让不同系统的结果可以直接比较，推动领域进展，明确当前最难的问题在哪里。
- [[实验可复现性 Reproducibility]] `#评测` — 实验可复现性是指其他研究者用完全相同的代码、数据、参数重新运行你的实验，能得到完全相同的结果。
- [[引用召回与精确率 Citation Recall Precision]] `#可信度 #TripleChecker #评测` — 引用召回率与精确率衡量生成声明是否得到充分且正确的证据支持。
- [[归因评测 Attribution]] `#可信度 #TripleChecker #评测` — 归因评测是指验证生成内容里的具体声明（claim）是否能在指定的来源材料中找到支撑证据的过程。
- [[消融实验 Ablation Study]] `#评测` — 消融实验通过逐步去掉系统的某个组件，观察性能变化，来验证每个组件的贡献。
- [[知识图谱质量评估维度]] `#KG #TripleChecker #评测` — 知识图谱质量由完整性、准确性、一致性、时效性和溯源性衡量。

## 前沿

- [[BigQuery Dremel 宽表建模 BigQuery-Dremel]] `#前沿` — Google Dremel/BigQuery 提出的嵌套列式宽表反规范化数仓范式
- [[GNN-RAG 图神经网络检索增强]] `#RAG #KG #前沿` — GNN-RAG（arxiv 2024）把 GNN 引入 RAG 的检索阶段。
- [[Google Bigtable 宽表模型 Bigtable]] `#前沿` — Google 2006 论文提出的稀疏分布式多维排序 Map 宽列存储
- [[ReDeEP 机制可解释性]] `#可信度 #前沿` — ReDeEP（Sun et al.
- [[StructRAG 结构化知识推理]] `#RAG #KG #前沿` — StructRAG（Li et al.
- [[机器遗忘 Machine Unlearning]] `#可信度 #前沿` — 机器遗忘让训练好的模型精确去除特定训练数据的影响,服务隐私合规与被遗忘权。

## 项目

- [[ChronoLink]]
- [[CoMaGRAG]]
- [[EvidenceFirst]]
- [[GSAD]]
- [[TripleChecker]]
