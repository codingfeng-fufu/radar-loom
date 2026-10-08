#!/usr/bin/env python3
"""Shared parsing and storage helpers for the isolated Idea Lab."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

IDEAS_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = IDEAS_ROOT / "pages"
INBOX_DIR = IDEAS_ROOT / "inbox"
DATA_DIR = IDEAS_ROOT / "data"
TEMPLATE_FILE = IDEAS_ROOT / "templates" / "idea.md"
INDEX_FILE = IDEAS_ROOT / "_index.md"
INDEX_DATA_FILE = DATA_DIR / "idea-index.json"
GRAPH_FILE = IDEAS_ROOT / "graph.md"
GRAPH_DATA_FILE = DATA_DIR / "idea-graph-data.json"

ID_RE = re.compile(r"^IDEA-(\d{4})-(\d{3})$")
FILENAME_RE = re.compile(r"^(IDEA-\d{4}-\d{3})\s+(.+)\.md$")
VALID_STATUSES = (
    "captured", "exploring", "attempted", "blocked", "dormant", "validated", "abandoned"
)
STATUS_LABELS = {
    "captured": "刚记录", "exploring": "探索中", "attempted": "已尝试",
    "blocked": "被阻塞", "dormant": "休眠中", "validated": "已验证", "abandoned": "已放弃",
}
FORBIDDEN_FILENAME = set('/\\:*?"<>|')


@dataclass(frozen=True)
class Idea:
    id: str
    title: str
    path: Path
    metadata: dict
    body: str


def today() -> str:
    return date.today().isoformat()


def _unquote(value: str):
    value = value.strip()
    if not value:
        return ""
    if value[0:1] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value.strip('"')
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    marker = text.find("\n---\n", 4)
    if marker < 0:
        return {}, text
    raw = text[4:marker]
    body = text[marker + 5:]
    result: dict = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line or line[:1].isspace() or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                parsed = json.loads(value)
                result[key] = parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                result[key] = [_unquote(item) for item in value[1:-1].split(",") if item.strip()]
        elif value:
            result[key] = _unquote(value)
        else:
            values = []
            cursor = index + 1
            while cursor < len(lines):
                match = re.match(r"^\s+-\s*(.*)$", lines[cursor])
                if not match:
                    break
                values.append(_unquote(match.group(1)))
                cursor += 1
            result[key] = values
            index = cursor - 1
        index += 1
    return result, body


def as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [] if value in (None, "") else [str(value).strip()]


def scan_ideas(root: Path = IDEAS_ROOT) -> dict[str, Idea]:
    pages = root / "pages"
    ideas: dict[str, Idea] = {}
    if not pages.exists():
        return ideas
    for path in sorted(pages.glob("*.md")):
        metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        idea_id = str(metadata.get("id") or "").strip()
        title = str(metadata.get("title") or path.stem).strip()
        key = idea_id or f"__invalid__:{path.name}"
        if key in ideas:
            key = f"__duplicate__:{idea_id}:{path.name}"
        ideas[key] = Idea(idea_id, title, path, metadata, body)
    return ideas


def next_id(year: int | None = None, root: Path = IDEAS_ROOT) -> str:
    year = year or date.today().year
    prefix = f"IDEA-{year}-"
    numbers = [int(idea.id.rsplit("-", 1)[1]) for idea in scan_ideas(root).values() if idea.id.startswith(prefix) and ID_RE.fullmatch(idea.id)]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError(f"{year} 年 Idea 编号已用尽")
    return f"{prefix}{number:03d}"


def safe_title(title: str) -> str:
    value = " ".join(title.split()).strip()
    if not value or len(value) > 120 or any(char in FORBIDDEN_FILENAME for char in value) or ".." in value:
        raise ValueError("标题为空、过长或包含非法路径字符")
    return value


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def json_text(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)
