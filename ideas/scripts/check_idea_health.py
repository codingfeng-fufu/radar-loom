#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import idea_common as common  # noqa: E402


def check(root: Path = common.IDEAS_ROOT) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    ideas = common.scan_ideas(root)
    valid_ids = {idea.id for idea in ideas.values() if common.ID_RE.fullmatch(idea.id)}
    seen = set()
    for idea in ideas.values():
        rel = idea.path.relative_to(root)
        if not common.ID_RE.fullmatch(idea.id):
            errors.append(f"[ERROR I1] {rel}: 缺少或无效的 Idea ID")
            continue
        if idea.id in seen:
            errors.append(f"[ERROR I2] {rel}: Idea ID 重复 {idea.id}")
        seen.add(idea.id)
        match = common.FILENAME_RE.fullmatch(idea.path.name)
        if not match or match.group(1) != idea.id:
            errors.append(f"[ERROR I3] {rel}: 文件名必须以 {idea.id} 开头")
        if not idea.title:
            errors.append(f"[ERROR I4] {rel}: 缺少标题")
        status = str(idea.metadata.get("status") or "")
        if status not in common.VALID_STATUSES:
            errors.append(f"[ERROR I5] {rel}: 非法状态 {status or '(空)'}")
        for field in ("created", "updated"):
            value = str(idea.metadata.get(field) or "")
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(f"[ERROR I6] {rel}: {field} 必须为 YYYY-MM-DD")
        if not re.search(r"^## 原始想法\s*$", idea.body, re.MULTILINE):
            errors.append(f"[ERROR I7] {rel}: 缺少原始想法章节")
        if status == "blocked" and not common.as_list(idea.metadata.get("blockers")):
            errors.append(f"[ERROR I8] {rel}: blocked 状态必须记录 blockers")
        if status == "abandoned" and "放弃" not in idea.body:
            errors.append(f"[ERROR I9] {rel}: abandoned 状态必须记录放弃理由")
        for field in ("derived_from", "combined_into", "related_ideas"):
            for target in common.as_list(idea.metadata.get(field)):
                if target == idea.id:
                    errors.append(f"[ERROR I10] {rel}: 不得引用自身")
                elif target not in valid_ids:
                    errors.append(f"[ERROR I11] {rel}: {field} 指向不存在的 {target}")
        for source in common.as_list(idea.metadata.get("derived_from")):
            other = ideas.get(source)
            if other and idea.id not in common.as_list(other.metadata.get("combined_into")):
                errors.append(f"[ERROR I12] {rel}: {source} 缺少反向 combined_into 关系")
    for generated in (root / "_index.md", root / "data" / "idea-index.json", root / "graph.md", root / "data" / "idea-graph-data.json"):
        if not generated.exists():
            errors.append(f"[ERROR I13] 缺少生成物 {generated.relative_to(root)}")
        elif any(idea.path.stat().st_mtime_ns > generated.stat().st_mtime_ns for idea in ideas.values()):
            errors.append(f"[ERROR I13] 生成物过期 {generated.relative_to(root)}")
    for external in (root / "data" / "idea-index.json", root / "data" / "idea-graph-data.json"):
        if external.exists():
            try:
                json.loads(external.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                errors.append(f"[ERROR I14] 无效 JSON {external.relative_to(root)}")
    return errors, warnings


def main() -> int:
    errors, warnings = check()
    for issue in errors + warnings:
        print(issue)
    print(f"Idea 健康检查完成:ERROR {len(errors)} 条,WARN {len(warnings)} 条。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

