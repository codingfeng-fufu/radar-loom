# 技术雷达 · 个人技术动态知识库

追踪 KG / RAG / LLM 领域新技术动态的个人知识库。按概念建页、增量更新、双链关联、图谱按需渲染。

与 `MASTER_knowledge_base.md` 的分工:那边是体系化沉淀的"教科书",这里是持续追新的"雷达屏"。雷达上反复出现、已经想清楚的内容,月末人工升级合并过去。

## 核心范式

1. **一个概念一个页面**,放在 `pages/` 下,文件名即概念名(格式:`中文名 英文名.md`)
2. **同一概念的新进展,回到原页面追加"更新记录"**,永远不建第二个页面
3. 页面间关联用双方括号链接语法写在正文里,不维护独立索引
4. 需要看全局关联时运行 `python3 scripts/render_graph.py`,生成 `graph.md`,VSCode 里 `Ctrl+Shift+V` 预览

## 日常工作流

1. 每周固定一次扫描新论文/动态(arXiv cs.CL / cs.AI、会议录用列表、可信的技术博客)
2. 判断是否建页,标准是二选一:与我的研究方向直接相关;或同一主题第二次进入视野
3. 建页:`python3 scripts/new_page.py "概念名 EnglishName" --tags KG --source "https://..." --confidence 中`
4. 已有页面的更新:直接编辑原文件,在"更新记录"末尾追加一行
5. 提交:`git add -A && git commit -m "radar: 新增/更新 <页面名>"`

## 脚本

| 脚本 | 用途 | 命令 |
|---|---|---|
| `render_graph.py` | 扫描双链,生成 Mermaid 图谱快照 `graph.md` | `python3 scripts/render_graph.py` |
| `new_page.py` | 按模板建新页,自动填字段、连分类页 | 见上方工作流第 3 条 |
| `check_health.py` | 检查断链、缺字段、重复嫌疑页 | `python3 scripts/check_health.py` |

## 月度维护

月末执行一次:

1. `python3 scripts/check_health.py`,清零告警
2. `python3 scripts/render_graph.py`,查看孤立节点——孤立说明记录太浅或缺关联,回头补
3. 把本月已想清楚、稳定下来的内容升级合并进 `MASTER_knowledge_base.md`(人工操作,本库脚本不碰那个文件)

## Claude Code 使用协议

CC 在本库执行建页/更新任务时必须遵守:

1. **建页前先查重**:在 `pages/` 内按中文名和英文名分别搜索;已有页面 → 改为追加更新记录
2. **只用 `new_page.py` 建页**,不手工拼文件;`--source` 与 `--confidence` 必给
3. **主动连双链**:正文提到的、`pages/` 里已存在的概念写成双链;与 GSAD / ChronoLink / EvidenceFirst / TripleChecker 有关则写进"和我的项目的关系"并打项目标签
4. **说明性文字里不写裸双方括号示例**(会被图谱脚本当成真实链接)
5. **每次批量写入后**:跑 `check_health.py`,修复告警,然后 git 提交,message 格式 `radar: 新增/更新 <页面名>`
6. **禁止**:删除页面(除非用户明确要求);修改 `MASTER_knowledge_base.md`;改动 `scripts/` 与 `templates/`(除非用户要求)
