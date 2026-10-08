#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import idea_common as common  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="创建独立 Idea 页面")
    parser.add_argument("idea", help="原始想法；默认同时作为标题")
    parser.add_argument("--title", help="显示标题")
    parser.add_argument("--problem", default="", help="想解决的问题")
    parser.add_argument("--domains", default="", help="逗号分隔的领域")
    parser.add_argument("--root", type=Path, default=common.IDEAS_ROOT, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def create_idea(original: str, title: str | None, problem: str, domains: list[str], root: Path) -> Path:
    original = original.strip()
    if not original:
        raise ValueError("原始想法不能为空")
    display_title = common.safe_title(title or original[:60])
    idea_id = common.next_id(root=root)
    template = (root / "templates" / "idea.md").read_text(encoding="utf-8")
    replacements = {
        "__ID__": idea_id,
        "__TITLE_JSON__": common.json_text(display_title),
        "__TITLE__": display_title,
        "__DATE__": common.today(),
        "__PROBLEM_JSON__": common.json_text(problem.strip()),
        "__ORIGINAL__": original,
        "domains: []": f"domains: {json.dumps(domains, ensure_ascii=False)}",
    }
    for source, target in replacements.items():
        template = template.replace(source, target)
    path = root / "pages" / f"{idea_id} {display_title}.md"
    common.atomic_write(path, template)
    return path


def main(argv=None) -> int:
    args = parse_args(argv)
    domains = [item.strip() for item in args.domains.split(",") if item.strip()]
    try:
        path = create_idea(args.idea, args.title, args.problem, domains, args.root)
    except (OSError, ValueError) as error:
        print(f"错误: {error}", file=sys.stderr)
        return 2
    print(f"已创建 {path.relative_to(args.root.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

