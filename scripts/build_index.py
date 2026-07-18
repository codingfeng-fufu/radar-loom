#!/usr/bin/env python3
"""Build the committed retrieval index from page frontmatter."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
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


DIFFICULTY_ORDER = {"基础": 0, "进阶": 1, "深入": 2}


def _interview_summary(frontmatter: dict) -> str:
    return str(frontmatter.get("summary") or frontmatter.get("摘要") or "").strip()


def _interview_question(frontmatter: dict) -> str:
    for key in ("question", "original_question", "原问题", "问题"):
        value = str(frontmatter.get(key) or "").strip()
        if value:
            return value
    return "(未记录)"


def _as_list(value) -> list[str]:
    return normalize_tags(value)


def render_interview_index(interview_pages: dict[str, rc.PageInfo]) -> tuple[str, int, int]:
    pages = list(interview_pages.values())
    missing = sum(not _interview_summary(p.frontmatter) for p in pages)
    def sort_key(p):
        fm = p.frontmatter
        roles = sorted(_as_list(fm.get("roles")))
        role = roles[0] if roles else ""
        difficulty = str(fm.get("difficulty") or "").strip()
        tags = sorted(_as_list(fm.get("tags")))
        return (role, DIFFICULTY_ORDER.get(difficulty, 99), difficulty, tags, p.name)
    def section_sort_key(p):
        fm = p.frontmatter
        difficulty = str(fm.get("difficulty") or "").strip()
        return (DIFFICULTY_ORDER.get(difficulty, 99), difficulty, sorted(_as_list(fm.get("tags"))), p.name)
    lines = ["# 面试索引(机器生成,勿手工编辑)", "", f"> 生成:{rc.today()} · 面试页 {len(pages)} · 运行 `python3 scripts/build_index.py` 刷新"]
    for role in sorted({r for p in pages for r in _as_list(p.frontmatter.get("roles"))}):
        lines.extend(["", f"## 角色: {role}", ""])
        selected = sorted((p for p in pages if role in _as_list(p.frontmatter.get("roles"))), key=section_sort_key)
        for p in selected:
            fm = p.frontmatter
            tags = " ".join(f"#{t}" for t in sorted(_as_list(fm.get("tags"))))
            roles = ", ".join(sorted(_as_list(fm.get("roles"))) or ["未指定"])
            difficulty = str(fm.get("difficulty") or "未分级").strip()
            summary = _interview_summary(fm) or "(缺摘要)"
            lines.append(f"- [[{p.name}]] `{tags}` — 原问题: {_interview_question(fm)} · 摘要: {summary} · 角色: {roles} · 难度: {difficulty}")
    lines.extend(["", "## 难度", ""])
    for difficulty in ("基础", "进阶", "深入"):
        lines.append(f"### {difficulty}")
        selected = sorted((p for p in pages if str(p.frontmatter.get("difficulty") or "").strip() == difficulty), key=sort_key)
        lines.extend([f"- [[{p.name}]]" for p in selected] or ["- 无"])
    return "\n".join(lines) + "\n", len(pages), missing


def atomic_write_pair(outputs: tuple[tuple[Path, str], tuple[Path, str]]) -> None:
    backups = {destination: destination.read_bytes() if destination.exists() else None for destination, _ in outputs}
    temporaries = []
    try:
        for destination, content in outputs:
            fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
            temporary = Path(temporary_name)
            temporaries.append(temporary)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        for temporary, (destination, _) in zip(temporaries, outputs):
            temporary.replace(destination)
    except Exception:
        for destination, previous in backups.items():
            if previous is None:
                destination.unlink(missing_ok=True)
            else:
                destination.write_bytes(previous)
        raise
    finally:
        for temporary in temporaries:
            temporary.unlink(missing_ok=True)


def render_indexes(all_pages: dict[str, rc.PageInfo]) -> tuple[str, str, dict[str, int]]:
    knowledge, interviews = rc.partition_pages(all_pages)
    knowledge_text, concepts, projects, knowledge_missing = render_index(knowledge)
    interview_text, interview_count, interview_missing = render_interview_index(interviews)
    stats = {"concepts": concepts, "projects": projects, "knowledge_missing": knowledge_missing, "interviews": interview_count, "interview_missing": interview_missing}
    return knowledge_text, interview_text, stats


def parse_args(argv=None):
    return argparse.ArgumentParser(description="生成技术雷达检索索引").parse_args(argv)


def main(argv=None) -> int:
    parse_args(argv)
    knowledge, interviews = rc.partition_pages(rc.scan_pages())
    text, concepts, projects, missing = render_index(knowledge)
    interview_text, interview_count, interview_missing = render_interview_index(interviews)
    atomic_write_pair(((rc.INDEX_FILE, text), (rc.INTERVIEW_INDEX_FILE, interview_text)))
    print(f"已生成 _index.md | 概念页 {concepts} 项目页 {projects} 缺摘要 {missing}")
    print(f"已生成 _interview_index.md | 面试页 {interview_count} 缺摘要 {interview_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
