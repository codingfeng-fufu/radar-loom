#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path.cwd()
TEMPLATE = REPO_ROOT / "templates" / "工程面试页模板.md"
FORBIDDEN = set('/\\:*?"<>|')

def die(msg):
    print(f"错误: {msg}", file=sys.stderr); raise SystemExit(2)

def parse_args():
    p = argparse.ArgumentParser(description="创建工程面试专题页")
    p.add_argument("title")
    for name in ("question", "summary", "roles", "difficulty", "source"):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--tags", default="")
    p.add_argument("--related-concepts", default="")
    p.add_argument("--force", action="store_true")
    return p.parse_args()

def items(value):
    return [x.strip() for x in value.split(",") if x.strip()]

def yaml_list(values):
    return "[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in values) + "]"

def main():
    a = parse_args(); title = a.title.strip()
    if not title or any(c in FORBIDDEN for c in title) or "\n" in title or "\r" in title or ".." in title:
        die("标题为空或含非法路径字符")
    if a.difficulty not in ("基础", "进阶", "深入"): die("difficulty 必须为 基础/进阶/深入")
    roles = items(a.roles)
    if not roles: die("roles 不能为空")
    if not a.source.strip(): die("source 不能为空")
    if not a.question.strip(): die("question 不能为空")
    if not a.summary.strip(): die("summary 不能为空")
    target = ROOT / "pages" / f"{title}.md"
    if target.exists() and not a.force: die(f"页面已存在: {target.relative_to(ROOT)}，使用 --force 覆盖")
    text = TEMPLATE.read_text(encoding="utf-8")
    from datetime import date
    vals = {"__TITLE_RAW__": title, "__TITLE__": title, "__SUMMARY__": json.dumps(a.summary.strip(), ensure_ascii=False), "__SOURCE__": yaml_list([a.source.strip()]), "__TAGS__": yaml_list(items(a.tags)), "__ROLES__": yaml_list(roles), "__DIFFICULTY__": json.dumps(a.difficulty, ensure_ascii=False), "__QUESTION_RAW__": a.question.strip(), "__QUESTION__": json.dumps(a.question.strip(), ensure_ascii=False), "__RELATED__": yaml_list(items(a.related_concepts)), "{DATE}": date.today().isoformat()}
    text = re.sub(r"__(?:TITLE_RAW|TITLE|SUMMARY|SOURCE|TAGS|ROLES|DIFFICULTY|QUESTION_RAW|QUESTION|RELATED)__|\{DATE\}", lambda m: vals[m.group(0)], text)
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(text, encoding="utf-8")
    print(f"已创建 {target.relative_to(ROOT)}")
    return 0
if __name__ == "__main__": sys.exit(main())
