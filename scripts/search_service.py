#!/usr/bin/env python3
"""Pure search logic for Markdown knowledge and interview pages."""
from __future__ import annotations

import difflib
import re
from pathlib import Path


def _search_terms(query: str) -> tuple[list[str], list[str], list[str], list[str]]:
    phrases = re.findall(r'"([^"]+)"', query)
    clean = re.sub(r'"[^"]+"', ' ', query)
    tokens = re.findall(r'\S+', clean)
    positive, negative, alternatives = [], [], []
    has_or = any(token.upper() == "OR" for token in tokens)
    for token in tokens:
        upper = token.upper()
        if upper in {"AND", "OR"}:
            continue
        if token.startswith("-") and len(token) > 1:
            negative.append(token[1:].lower())
        elif has_or:
            alternatives.append(token.lower())
        else:
            positive.append(token.lower())
    return positive, negative, alternatives, [item.lower() for item in phrases]


def _matches(text: str, query: str, terms) -> tuple[bool, float, int]:
    positive, negative, alternatives, phrases = terms
    lower = text.lower()
    if any(term in lower for term in negative) or any(phrase not in lower for phrase in phrases):
        return False, 0.0, 0
    matched = (
        all(term in lower for term in positive)
        if not alternatives
        else all(term in lower for term in positive) or any(term in lower for term in alternatives)
    )
    fuzzy = 0.0
    if not matched and len(query) >= 4:
        words = re.findall(r'[\w\u4e00-\u9fff-]+', lower)
        fuzzy = max((difflib.SequenceMatcher(None, query, word).ratio() for word in words), default=0.0)
        matched = fuzzy >= 0.72
    positions = [lower.find(term) for term in positive if lower.find(term) >= 0]
    return matched, fuzzy, min(positions or [0])


def search_payload(root: Path, query: str, section: str = "", sort: str = "relevance", page: int = 1, page_size: int = 20) -> dict[str, object]:
    query = query.strip()
    terms = _search_terms(query)
    positive, _, _, phrases = terms
    records = []
    for path in sorted((root / "pages").glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        is_interview = bool(re.search(r"(?m)^page[_ -]?type:\s*(?:interview|engineering-interview)", text, re.IGNORECASE))
        if section and ((section == "interview") != is_interview):
            continue
        matched, fuzzy, position = _matches(text, query.lower(), terms)
        if not matched:
            continue
        summary_match = re.search(r"^(?:摘要|summary):\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
        summary = summary_match.group(1).strip()[:300] if summary_match else ""
        snippet = re.sub(r"\s+", " ", text[max(0, position - 100):position + 260]).strip()
        records.append({
            "file": f"pages/{path.name}",
            "title": path.stem,
            "summary": summary,
            "snippet": snippet,
            "pageType": "interview" if is_interview else "knowledge",
            "updatedAt": path.stat().st_mtime_ns,
            "score": round((len(positive) + len(phrases)) * 10 + fuzzy * 5, 3),
        })
    if sort == "updated":
        records.sort(key=lambda item: item["updatedAt"], reverse=True)
    elif sort == "title":
        records.sort(key=lambda item: item["title"])
    else:
        records.sort(key=lambda item: (-item["score"], item["title"]))
    page = max(1, int(page))
    page_size = min(100, max(1, int(page_size)))
    start = (page - 1) * page_size
    return {"version": 1, "query": query, "total": len(records), "page": page, "pageSize": page_size, "results": records[start:start + page_size]}
