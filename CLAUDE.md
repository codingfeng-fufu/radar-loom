# CLAUDE.md — 技术雷达知识库 · 助手常驻备忘

> 本文件是 Claude 在本知识库工作时的常驻上下文,每次会话自动加载。
> 目的:即使 session `resume` 失效,靠本文件也能恢复角色与工作模式。
> 与自动记忆 `~/.claude/projects/-home-u2023312337/memory/tech_radar_kb_role.md` 互为镜像;有变更两边一起改。

## 我的角色

我是用户的助手。`/home/u2023312337/知识库` 这个"技术雷达"知识库是我和用户**协作学习的活 KB**:用户配合我学习 KG/RAG/LLM 等领域,我负责把学到的东西沉淀进这个 KB。不是静态参考,要持续维护、丰富、连边。

## 用户背景

研究者,方向:KG 抽取质量评估(双循环一致性,验证器用 qwen-plus 蒸馏,跨域 DuIE/FinRE/CMeIE)。详见自动记忆 `project_kg_context.md`。

## KB 结构(库根 `/home/u2023312337/知识库`)

- `pages/` — 概念页(知识沉淀处,**唯一**被脚本扫描;平铺,禁止子目录)
- `raw/` — 只读原始证据(仿 LLM_wiki):`inbox/`(投入)、`processed/`(归档)、`assets/`;只放 markdown,不放 PDF
- `papers/` — PDF 存放(gitignored,不入库)
- `scripts/` — `new_page.py`(建页)、`render_graph.py`(出图)、`check_health.py`(自检)、`radar_common.py`(公共模块)
- `templates/概念页模板.md`、`首页.md`、`README.md`、`graph.md`(生成物,gitignored)
- `技术雷达_设计文档_v2.md` — 实现级规格书,已实现并通过 §15 验收

## 工作流

1. 建概念页(先查重,老概念回原页追加"更新记录"):
   ```bash
   python3 scripts/new_page.py "中文名 EnglishName" --tags <分类[,项目]> --source "<url 或 papers/xxx.pdf 或 raw/...>" --confidence <高/中/低>
   ```
   - 分类标签(至少一个):`KG`/`RAG`/`LLM机制`/`可信度`/`多智能体`/`前沿`
   - 项目标签:`GSAD`/`ChronoLink`/`EvidenceFirst`/`TripleChecker`(注意 `CoMaGRAG` 是项目页但**不是**合法 tag)
   - 脚本自动填 frontmatter、连分类/项目页交叉引用;我补"核心内容"和"和我的项目的关系",正文用 `[[页名]]` 主动连双链
2. 自检:`python3 scripts/check_health.py`(ERROR 必须为 0)
3. 出图:`python3 scripts/render_graph.py`(VSCode 打开 `graph.md`,Ctrl+Shift+V 预览)
4. 提交:`git add -A && git commit -m "radar: 新增/更新 <页名>"`

## 铁律

- 建页只用 `new_page.py`,必给 `--source` 和 `--confidence`
- 正文提到已有概念就连双链;说明文字里**不写裸 `[[...]]`**(会被图谱当真实链接)
- 每次写入后跑 `check_health.py` 再提交
- `raw/` 只读不重写;不删页面、不改 `MASTER_knowledge_base.md`、不改 `scripts/`+`templates/`(除非用户要求)
- PDF 放 `papers/`(不入库),markdown 原始件放 `raw/inbox/`
- 我能直接 Read PDF:用户把 PDF 放进 `papers/` 后告诉我,我读它提炼成概念页

## 当前状态(2026-07-04)

- 11 个 page(6 分类 MOC + 5 项目占位)+ 首页;**尚无概念页**
- 图谱:12 节点 / 19 边 / 0 断链;`check_health` ERROR 0
- 5 个项目页(`GSAD`/`ChronoLink`/`EvidenceFirst`/`TripleChecker`/`CoMaGRAG`)是占位,待用户给一句话简介填充
- git:`init 基线` / `test 验收清理` / `raw 目录` / `papers 目录` 共 4 个 commit

## 对设计文档 v2 的偏离(均用户确认或环境所致,已记录)

1. 新增 `raw/` 原始证据目录(仿 LLM_wiki,用户要求)
2. 新增 `papers/` + `.gitignore` 加 `papers/*.pdf`(用户要求)
3. §10.2 孤立节点:MOC 页若孤立也提示(只 `首页` 排除)——文档表述矛盾,按括注意图实现
4. §15 步骤8 用 `--allow-empty`(步骤7 清理后工作树干净)
5. commit 加 `Co-Authored-By: Claude` trailer(Claude Code 约定)
6. 设计文档曾被外部 markdown 格式化程序重排(非我所为,语义未变)

## resume 失效时的恢复步骤

1. 读本文件恢复角色与约定
2. `python3 scripts/check_health.py` 和 `python3 scripts/render_graph.py` 看当前状态
3. `git log --oneline` 看历史;`ls pages/` 看已有概念页
4. 继续:用户给话题/PDF/笔记 → 建概念页 → 自检 → 出图 → 提交
