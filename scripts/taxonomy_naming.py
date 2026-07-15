#!/usr/bin/env python3
"""Bounded external category naming with deterministic local fallback."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass


HTML_RE = re.compile(r"<[^>]+>")
CJK_RE = re.compile(r"[\u3400-\u9fff]")


@dataclass
class NamingRequest:
    category_id: str
    representative_pages: list[dict[str, str]]
    keywords: list[str]
    neighbor_definitions: list[str]


@dataclass(eq=True)
class NamingResult:
    name: str
    definition: str
    naming_status: str


class KeywordNamer:
    def name(self, request: NamingRequest) -> NamingResult:
        keywords = []
        for keyword in request.keywords:
            value = str(keyword).strip()
            if value and value not in keywords:
                keywords.append(value)
        name = " ".join(keywords[:2]) or f"未命名类别 {request.category_id[-6:]}"
        titles = [str(item.get("title", "")).strip() for item in request.representative_pages]
        titles = [title for title in titles if title]
        if titles:
            definition = f"包含与{'、'.join(titles[:3])}相关的知识页。"
        else:
            definition = f"由关键词{'、'.join(keywords[:3]) or '待识别主题'}形成的知识类别。"
        return NamingResult(name=name, definition=definition, naming_status="pending")


def _valid_name(name: object) -> bool:
    if not isinstance(name, str) or not name.strip() or HTML_RE.search(name):
        return False
    limit = 30 if CJK_RE.search(name) else 60
    return len(name.strip()) <= limit


def _valid_definition(definition: object) -> bool:
    return (
        isinstance(definition, str)
        and bool(definition.strip())
        and len(definition.strip()) <= 240
        and HTML_RE.search(definition) is None
    )


class CommandNamer:
    def __init__(self, command: list[str], timeout: int = 60):
        if not command:
            raise ValueError("naming command must not be empty")
        self.command = list(command)
        self.timeout = timeout
        self.fallback = KeywordNamer()

    def name(self, request: NamingRequest) -> NamingResult:
        payload = json.dumps(asdict(request), ensure_ascii=False, sort_keys=True)
        try:
            completed = subprocess.run(
                self.command,
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return self.fallback.name(request)
        if completed.returncode != 0:
            return self.fallback.name(request)
        try:
            response = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError):
            return self.fallback.name(request)
        if not isinstance(response, dict) or set(response) != {"name", "definition"}:
            return self.fallback.name(request)
        if not _valid_name(response["name"]) or not _valid_definition(response["definition"]):
            return self.fallback.name(request)
        return NamingResult(
            name=response["name"].strip(),
            definition=response["definition"].strip(),
            naming_status="ready",
        )


def name_changed_categories(
    requests: list[NamingRequest],
    namer,
    max_calls: int,
) -> list[NamingResult]:
    fallback = KeywordNamer()
    results = []
    for index, request in enumerate(requests):
        if index < max(0, int(max_calls)):
            results.append(namer.name(request))
        else:
            results.append(fallback.name(request))
    return results
