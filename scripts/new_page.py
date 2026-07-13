#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 建页脚本(§11)。

按模板创建新概念页,自动填充 frontmatter、连接分类/项目页。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402
import build_index  # noqa: E402

USAGE = (
    '用法示例:python3 scripts/new_page.py "概念中文名 EnglishName" '
    '--tags KG --summary "一句话摘要" --source "https://arxiv.org/abs/xxxx.xxxxx" --confidence 中'
)

FORBIDDEN_TITLE_CHARS = set('/\\:*?"<>|')


def die(msg: str) -> None:
    """校验失败:中文错误说明 + 用法示例,退出码 2。"""
    print(f"错误:{msg}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    sys.exit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python3 scripts/new_page.py",
        description="按模板创建技术雷达概念页",
        add_help=True,
    )
    parser.add_argument("title", nargs="?", help="页面标题,格式「概念中文名 EnglishName」")
    parser.add_argument("--tags", help="逗号分隔的标签,需含至少一个分类标签")
    parser.add_argument("--source", help="来源链接")
    parser.add_argument("--summary", help="一句话摘要(不超过60字)")
    parser.add_argument("--force-source", action="store_true", help="允许暂时使用不存在的本地来源")
    parser.add_argument("--confidence", default="中", help="信度:高/中/低(默认 中)")
    return parser.parse_args()


def validate(args: argparse.Namespace) -> tuple[str, list[str], str, str, str]:
    """校验并返回 (title, tags, source, confidence);失败 die() 退出 2。"""
    # ---- title ----
    if args.title is None:
        die("缺少必填的位置参数:页面标题(概念中文名 EnglishName)。")
    title = args.title.strip()
    if not title:
        die("页面标题不能为空。")
    if any(c in FORBIDDEN_TITLE_CHARS for c in title) or "\n" in title or "\r" in title:
        die('页面标题含有非法字符(禁止 / \\ : * ? " < > | 及换行)。')

    # ---- tags ----
    if args.tags is None:
        die("缺少必填参数 --tags(逗号分隔,需含至少一个分类标签)。")
    tags = [t.strip() for t in args.tags.split(",")]
    allowed = rc.CATEGORY_TAGS | rc.PROJECT_TAGS
    for t in tags:
        if t not in allowed:
            die(f"非法 tag「{t}」:tag 必须属于分类标签或项目标签之一。")
    if not any(t in rc.CATEGORY_TAGS for t in tags):
        die("--tags 必须至少包含一个分类标签(KG/RAG/LLM机制/可信度/多智能体/前沿)。")

    # ---- source ----
    if args.source is None or not args.source.strip():
        die("缺少必填参数 --source(不能为空)。")
    source = args.source.strip()
    source_type, local_path = rc.parse_source(source)
    if source_type == "unknown":
        die("--source 必须是 papers/raw 本地路径、完整 URL 或对话记录日期。")
    if source_type == "local" and not (rc.VAULT_ROOT / local_path).exists() and not args.force_source:
        die(f"本地来源不存在:{local_path}(确需跳过时使用 --force-source)。")

    if args.summary is None or not args.summary.strip():
        die("缺少必填参数 --summary(不能为空)。")
    summary = args.summary.strip()
    if len(summary) > 60:
        die("--summary 不能超过60字。")

    # ---- confidence ----
    if args.confidence not in ("高", "中", "低"):
        die(f"非法信度「{args.confidence}」:信度必须为 高/中/低 之一。")

    return title, tags, summary, source, args.confidence


def dedup_check(title: str) -> None:
    """§11.2 查重;精确存在 exit 1,大小写/空格不敏感重名 exit 1。"""
    target_path = rc.PAGES_DIR / f"{title}.md"
    if target_path.exists():
        print(
            f'页面已存在: pages/{title}.md — 请到该页面的"更新记录"追加,而不是新建。',
            file=sys.stderr,
        )
        sys.exit(1)
    title_key = title.casefold().replace(" ", "")
    suspects = []
    if rc.PAGES_DIR.exists():
        for p in rc.PAGES_DIR.glob("*.md"):
            if p.stem.casefold().replace(" ", "") == title_key:
                suspects.append(p.stem)
    if suspects:
        print("页面名与已有页面疑似重复:", file=sys.stderr)
        for s in suspects:
            print(f"  - pages/{s}.md", file=sys.stderr)
        print("若确为不同概念,请更换名称后重试。", file=sys.stderr)
        sys.exit(1)


def build_content(title: str, tags: list[str], summary: str, source: str, confidence: str) -> str:
    """§11.3 读模板并做替换,返回新页正文。"""
    text = rc.TEMPLATE_FILE.read_text(encoding="utf-8")
    # 1. 占位符
    text = text.replace("{TITLE}", title).replace("{DATE}", rc.today())
    # 2. frontmatter 三处字符串替换
    text = text.replace("摘要:", f"摘要: {summary}", 1)
    text = text.replace("来源: ", f"来源: {source}")
    text = text.replace("信度: 中", f"信度: {confidence}")
    text = text.replace("tags: []", f"tags: [{', '.join(tags)}]")
    # 3. 交叉引用区:替换孤行 `- `
    xref = []
    for t in tags:
        if t in rc.CATEGORY_TAGS:
            xref.append(f"- [[{rc.TAG_TO_CATEGORY_PAGE[t]}]]")
        elif t in rc.PROJECT_TAGS:
            xref.append(f"- [[{t}]]")
    lines = text.split("\n")
    out: list[str] = []
    in_xref = False
    replaced = False
    for line in lines:
        if line.strip() == "## 交叉引用":
            in_xref = True
            out.append(line)
            continue
        if in_xref and line.startswith("## "):
            in_xref = False  # 进入下一节
        if in_xref and not replaced and line.strip() == "-":
            out.extend(xref)
            replaced = True
            continue
        out.append(line)
    return "\n".join(out)


def main() -> int:
    args = parse_args()
    title, tags, summary, source, confidence = validate(args)
    dedup_check(title)

    rc.PAGES_DIR.mkdir(parents=True, exist_ok=True)
    content = build_content(title, tags, summary, source, confidence)
    target_path = rc.PAGES_DIR / f"{title}.md"
    target_path.write_text(content, encoding="utf-8")
    build_index.main([])

    print(
        f'已创建 pages/{title}.md(tags: {", ".join(tags)}, 信度: {confidence})。'
        f'请补充"核心内容"与"和我的项目的关系"。'
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
