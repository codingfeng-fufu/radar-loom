# 技术雷达 · 个人知识外脑

面向 KG / RAG / LLM 等技术方向的纯 Markdown 知识库，由用户与 CC 共同维护。系统以检索优先和增量摄入为两条核心要求：回答问题前先检索库内页面；新知识回到已有概念追加或建立新页，并以 Git 留痕。

与 `MASTER_knowledge_base.md` 的分工：那边是体系化沉淀的“教科书”，这里是持续吸收、检索和关联的个人知识外脑。

## 核心范式

1. 一个概念一个页面，放在 `pages/` 下，文件名即概念名。
2. 同一概念的新进展回到原页面追加“更新记录”，不建第二页。
3. 页面关系使用双方括号链接；机器生成的 `_index.md` 是 CC 的检索入口，不手工编辑。
4. `python3 scripts/render_graph.py` 按需生成核心概览和八个分类子图。
5. 来源必须真实可达，并尽量记录 PDF 页码或章节。

## 向 CC 提问

CC 先读取 `_index.md`，再打开命中的少量页面。库内命中时按页面内容回答并注明页面与来源；部分命中时区分库内内容和补充知识；未命中时明确说明库内没有该条目。

## 给 CC 喂料

知识可以来自对话、文本文件或 PDF，不要求固定周频率，有料时增量摄入。文本原始件进入 `raw/inbox/`，PDF 进入 `papers/`；文件内容先形成待建/待更新页面清单，再逐页处理。老概念追加，新概念使用：

```bash
python3 scripts/new_page.py "概念名 EnglishName" \
  --tags KG \
  --summary "一句话说明这页讲什么" \
  --source "papers/example.pdf p.3-5" \
  --confidence 中
```

每次摄入以生成索引、健康检查和 Git 提交收尾。

## 脚本

| 脚本 | 用途 | 命令 |
|---|---|---|
| `build_index.py` | 从 frontmatter 生成 `_index.md` 检索索引 | `python3 scripts/build_index.py` |
| `render_graph.py` | 生成核心概览和八个分类 Mermaid 图谱 | `python3 scripts/render_graph.py` |
| `new_page.py` | 按模板建页并刷新索引 | 见“给 CC 喂料” |
| `check_health.py` | 检查格式、链接、来源、摘要和索引一致性 | `python3 scripts/check_health.py` |

## 标签与信度

分类标签：`KG`、`RAG`、`LLM机制`、`可信度`、`多智能体`、`基础`、`评测`、`前沿`。

项目标签：`GSAD`、`ChronoLink`、`EvidenceFirst`、`TripleChecker`、`CoMaGRAG`。

- `高`：一手论文或官方文档精读，或教科书级共识知识。
- `中`：摘要、可靠二手转述或 PDF 讲义类材料整理。
- `低`：未验证的二手消息。

## 月度维护

1. 运行索引生成和健康检查，清零 ERROR。
2. 运行图谱脚本查看全库连接状态。
3. 检查 `GSAD`、`ChronoLink` 等项目标签是否长期为 0；为 0 表示该方向尚无知识页沉淀。
4. 人工判断成熟内容是否升级合并进 `MASTER_knowledge_base.md`，本库脚本不读写该文件。

CC 行为协议见 `CLAUDE.md`。
