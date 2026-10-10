#!/usr/bin/env python3
"""Create an engineering interview page from the repository template."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path.cwd()
TEMPLATE = REPO_ROOT / "templates" / "工程面试页模板.md"
FORBIDDEN_TITLE_CHARS = set('/\\:*?"<>|')
VALID_DIFFICULTIES = {"基础", "进阶", "深入"}
PLACEHOLDER_PATTERN = re.compile(
    r"__(?:TITLE_RAW|TITLE|SUMMARY|SOURCE|TAGS|ROLES|DIFFICULTY|QUESTION_RAW|QUESTION|RELATED)__|\{DATE\}"
)


def die(message: str) -> None:
    print(f"错误: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title")
    for name in ("question", "summary", "roles", "difficulty", "source"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--tags", default="")
    parser.add_argument("--related-concepts", default="")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def split_items(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def yaml_list(values: list[str]) -> str:
    encoded = (json.dumps(value, ensure_ascii=False) for value in values)
    return f"[{', '.join(encoded)}]"


def validate_args(args) -> tuple[str, list[str]]:
    title = args.title.strip()
    if not title or any(char in FORBIDDEN_TITLE_CHARS for char in title) or ".." in title or "\n" in title or "\r" in title:
        die("标题为空或含非法路径字符")
    if args.difficulty not in VALID_DIFFICULTIES:
        die("difficulty 必须为 基础/进阶/深入")
    roles = split_items(args.roles)
    if not roles:
        die("roles 不能为空")
    for name, value in (("source", args.source), ("question", args.question), ("summary", args.summary)):
        if not value.strip():
            die(f"{name} 不能为空")
    return title, roles


def render_template(args, title: str, roles: list[str]) -> str:
    values = {
        "__TITLE_RAW__": title,
        "__TITLE__": title,
        "__SUMMARY__": json.dumps(args.summary.strip(), ensure_ascii=False),
        "__SOURCE__": yaml_list([args.source.strip()]),
        "__TAGS__": yaml_list(split_items(args.tags)),
        "__ROLES__": yaml_list(roles),
        "__DIFFICULTY__": json.dumps(args.difficulty, ensure_ascii=False),
        "__QUESTION_RAW__": args.question.strip(),
        "__QUESTION__": json.dumps(args.question.strip(), ensure_ascii=False),
        "__RELATED__": yaml_list(split_items(args.related_concepts)),
        "{DATE}": date.today().isoformat(),
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    return PLACEHOLDER_PATTERN.sub(lambda match: values[match.group(0)], template)


def create_page(args) -> Path:
    title, roles = validate_args(args)
    target = ROOT / "pages" / f"{title}.md"
    if target.exists() and not args.force:
        die(f"页面已存在: {target.relative_to(ROOT)}，使用 --force 覆盖")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_template(args, title, roles), encoding="utf-8")
    return target


def main(argv=None) -> int:
    target = create_page(parse_args(argv))
    print(f"已创建 {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
