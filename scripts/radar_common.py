#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 公共模块(§9)。

提供路径常量、frontmatter 解析、页面扫描、双链解析、Mermaid ID 消毒等共用能力。
所有脚本通过本模块访问库结构,路径解析统一基于脚本所在目录的父目录(库根)。
"""
from __future__ import annotations

import datetime
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# §9.1 模块级常量
# --------------------------------------------------------------------------- #
VAULT_ROOT = Path(__file__).resolve().parent.parent
PAGES_DIR = VAULT_ROOT / "pages"
TEMPLATE_FILE = VAULT_ROOT / "templates" / "概念页模板.md"
GRAPH_FILE = VAULT_ROOT / "graph.md"
INDEX_FILE = VAULT_ROOT / "_index.md"

WIKILINK_RE = re.compile(r"\[\[([^\]|#\n]+?)(?:\|[^\]]*)?\]\]")
# 说明:捕获组 1 为目标页名;支持 [[目标|别名]] 形式(别名丢弃);
# 排除 ] | # 换行,避免跨行误匹配与锚点;非贪婪。

CATEGORY_TAGS = {"KG", "RAG", "LLM机制", "可信度", "多智能体", "前沿", "基础", "评测"}
PROJECT_TAGS = {"GSAD", "ChronoLink", "EvidenceFirst", "TripleChecker", "CoMaGRAG"}
STRUCT_TAGS = {"MOC", "项目"}

TAG_TO_CATEGORY_PAGE = {
    "KG": "知识图谱 KG",
    "RAG": "检索增强生成 RAG-GraphRAG",
    "LLM机制": "大模型机制与推理 LLM Mechanisms",
    "可信度": "幻觉与可信度 Hallucination Trustworthiness",
    "多智能体": "多智能体系统 Multi-Agent Systems",
    "前沿": "前沿趋势 Frontier",
    "基础": "机器学习与NLP基础 ML-NLP Foundations",
    "评测": "评测方法 Evaluation Methods",
}

CATEGORY_ORDER = ("KG", "RAG", "LLM机制", "可信度", "多智能体", "基础", "评测", "前沿")
GRAPH_SLUGS = {
    "KG": "kg", "RAG": "rag", "LLM机制": "llm", "可信度": "trust",
    "多智能体": "agents", "前沿": "frontier", "基础": "basics", "评测": "eval",
}
GRAPH_DIR_FILES = {tag: VAULT_ROOT / f"graph_{slug}.md" for tag, slug in GRAPH_SLUGS.items()}


# --------------------------------------------------------------------------- #
# §9.3 PageInfo 数据类
# --------------------------------------------------------------------------- #
@dataclass
class PageInfo:
    name: str            # 文件名去 .md
    path: Path
    frontmatter: dict
    body: str            # 去掉 frontmatter 的正文
    links: list[str] = field(default_factory=list)  # 正文中提取的双链目标名(保序,可重复)


# --------------------------------------------------------------------------- #
# §9.2 parse_frontmatter
# --------------------------------------------------------------------------- #
def _strip_quotes(s: str) -> str:
    """去掉包裹引号:首尾为同一种引号时去掉。"""
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """手写 frontmatter 解析,不引入 PyYAML。

    规则见 §9.2:以 ``---\\n`` 开头才视为有 frontmatter;区内逐行按第一个冒号分割;
    ``[a, b]`` 形态的 value 解析为列表;无法解析的行忽略。返回 (字典, 正文)。
    """
    if not text.startswith("---\n"):
        return ({}, text)
    lines = text.split("\n")
    # lines[0] == "---"
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        # 找不到结束分隔符,视为无合法 frontmatter
        return ({}, text)
    fm_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1:])
    fm: dict = {}
    for line in fm_lines:
        if ":" not in line:
            continue  # 无法解析的行忽略,不报错
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner == "":
                fm[key] = []
            else:
                fm[key] = [_strip_quotes(item) for item in inner.split(",")]
        else:
            fm[key] = value
    return (fm, body)


# --------------------------------------------------------------------------- #
# §9.3 scan_pages
# --------------------------------------------------------------------------- #
def scan_pages() -> dict[str, PageInfo]:
    """遍历 PAGES_DIR/*.md 加上 VAULT_ROOT/首页.md,返回 {name: PageInfo}。

    若 PAGES_DIR 不存在,向 stderr 报错并 sys.exit(2)。
    """
    if not PAGES_DIR.exists():
        print(f"错误: pages/ 目录不存在,当前库根目录推断为 {VAULT_ROOT}", file=sys.stderr)
        sys.exit(2)

    paths = sorted(PAGES_DIR.glob("*.md"))
    home = VAULT_ROOT / "首页.md"
    if home.exists():
        paths.append(home)

    pages: dict[str, PageInfo] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        name = path.stem
        links = [m.strip() for m in WIKILINK_RE.findall(body)]
        pages[name] = PageInfo(name=name, path=path, frontmatter=fm, body=body, links=links)
    return pages


# --------------------------------------------------------------------------- #
# §9.4 resolve_link
# --------------------------------------------------------------------------- #
def resolve_link(target: str, pages: dict) -> str | None:
    """匹配顺序:精确同名 → 大小写不敏感同名(casefold)→ None(断链)。"""
    target = target.strip()
    if target in pages:
        return target
    cf = target.casefold()
    for name in pages:
        if name.casefold() == cf:
            return name
    return None


# --------------------------------------------------------------------------- #
# §9.5 mermaid_id
# --------------------------------------------------------------------------- #
_mermaid_name_to_id: dict[str, str] = {}
_mermaid_used_ids: set[str] = set()


def reset_mermaid_id_state() -> None:
    """每次渲染前重置消毒 ID 的内部状态。"""
    global _mermaid_name_to_id, _mermaid_used_ids
    _mermaid_name_to_id = {}
    _mermaid_used_ids = set()


def mermaid_id(name: str) -> str:
    """把页面名消毒为合法 Mermaid 节点 ID。

    规则:非字母数字/中文换 `_`;首字符为数字则前缀 `n_`;
    同一次渲染内同一 name 返回同一 ID;不同 name 消毒后冲突时,后者追加 `_2`、`_3`……
    """
    if name in _mermaid_name_to_id:
        return _mermaid_name_to_id[name]
    base = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "_", name)
    if base and base[0].isdigit():
        base = "n_" + base
    candidate = base
    if candidate not in _mermaid_used_ids:
        _mermaid_used_ids.add(candidate)
        _mermaid_name_to_id[name] = candidate
        return candidate
    i = 2
    while True:
        cand = f"{base}_{i}"
        if cand not in _mermaid_used_ids:
            _mermaid_used_ids.add(cand)
            _mermaid_name_to_id[name] = cand
            return cand
        i += 1


# --------------------------------------------------------------------------- #
# §9.6 today
# --------------------------------------------------------------------------- #
def today() -> str:
    """返回 YYYY-MM-DD。"""
    return datetime.date.today().isoformat()


def parse_source(value: str) -> tuple[str, str | None]:
    """Classify a source and return its local path when applicable."""
    value = value.strip()
    if value.startswith(("papers/", "raw/")):
        path = re.split(r"\s+p\.(?:\d+)(?:-\d+)?(?:\s|$)", value, maxsplit=1)[0]
        return ("local", path)
    if value.startswith(("http://", "https://")):
        return ("url", None)
    if value.startswith("对话记录"):
        return ("chat", None)
    return ("unknown", None)
