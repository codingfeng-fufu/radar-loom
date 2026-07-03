# raw/ · 原始证据区(只读)

本目录存放**原始来源材料**,约定参照 [LLM_wiki](../../LLM_wiki) 的 `raw/`:不可变证据层,**只读**。

## 与 pages/ 的分工

- `raw/` = 原始证据:论文导出的 markdown、网页存档、粗糙笔记、source card 等。**只读,不重写**。
- `pages/` = 维护的知识:我(Claude)读取 `raw/` 里的证据,按概念页模板提炼成 `pages/*.md`,连双链、打标签。知识沉淀发生在 `pages/`,不发生在 `raw/`。

流程:`raw/inbox/`(投入原始件)→ 我提炼建概念页到 `pages/` → 原始件归档到 `raw/processed/`。

## 子目录

- `inbox/` — 新投入的原始材料,可按主题建子目录(如 `inbox/kg/`、`inbox/rag/`)。我据此建概念页。
- `processed/` — 已转化为概念页的原始件归档(可加 hash 后缀防重名,参照 LLM_wiki)。
- `assets/` — 原始材料引用的图片等附件。

## 规则

1. `raw/` 里的文件**只读**,不重写、不删除(除非用户明确要求)。
2. `raw/` 只放文本/markdown,不放二进制(PDF 等请自行存到他处,在概念页 `来源` 字段填链接)。
3. 建概念页时,`来源` 字段填原始件路径或外链,例如 `raw/inbox/kg/xxx.md` 或 `https://arxiv.org/abs/...`。
4. `raw/` 不被 `check_health.py` / `render_graph.py` 扫描(两脚本只看 `pages/` 与 `首页.md`),所以这里的内容不参与健康检查与图谱。

> 本目录是对设计文档 v2 §2 目录结构的扩展(用户要求,仿 LLM_wiki)。`pages/` 仍为唯一的知识沉淀位置。
