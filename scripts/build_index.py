#!/usr/bin/env python3
"""Build the committed retrieval index from page frontmatter."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402


def normalize_tags(value) -> list[str]:
    if isinstance(value, list):
        return value
    return [] if value is None else [str(value)]


def render_index(pages: dict[str, rc.PageInfo]) -> tuple[str, int, int, int]:
    concepts = []
    projects = []
    for page in pages.values():
        tags = normalize_tags(page.frontmatter.get("tags"))
        if "项目" in tags:
            projects.append(page)
        elif "MOC" not in tags and page.name != "首页":
            concepts.append(page)

    missing = sum(not str(p.frontmatter.get("摘要", "")).strip() for p in concepts)
    lines = ["# 索引(机器生成,勿手工编辑)", "", f"> 生成:{rc.today()} · 页面 {len(concepts)} · 运行 `python3 scripts/build_index.py` 刷新"]
    for tag in rc.CATEGORY_ORDER:
        lines.extend(["", f"## {tag}", ""])
        selected = sorted((p for p in concepts if tag in normalize_tags(p.frontmatter.get("tags"))), key=lambda p: p.name)
        if not selected:
            lines.append("- 无")
        for page in selected:
            tags = " ".join(f"#{t}" for t in normalize_tags(page.frontmatter.get("tags")))
            summary = str(page.frontmatter.get("摘要", "")).strip() or "(缺摘要)"
            lines.append(f"- [[{page.name}]] `{tags}` — {summary}")
    lines.extend(["", "## 项目", ""])
    for page in sorted(projects, key=lambda p: p.name):
        lines.append(f"- [[{page.name}]]")
    return "\n".join(lines) + "\n", len(concepts), len(projects), missing


def parse_args(argv=None):
    return argparse.ArgumentParser(description="生成技术雷达检索索引").parse_args(argv)


def main(argv=None) -> int:
    parse_args(argv)
    text, concepts, projects, missing = render_index(rc.scan_pages())
    rc.INDEX_FILE.write_text(text, encoding="utf-8")
    print(f"已生成 _index.md | 概念页 {concepts} 项目页 {projects} 缺摘要 {missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
