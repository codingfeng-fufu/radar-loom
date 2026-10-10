#!/usr/bin/env python3
"""Build browser and workbench catalog payloads from generated graph data."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def paper_notes_payload(root: Path) -> dict[str, object]:
    entries = []
    for path in sorted((root / "paper-notes").glob("*.md"), key=lambda item: item.stat().st_mtime_ns, reverse=True):
        if path.name == ".gitkeep":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        title_match = re.search(r"(?m)^#\s+(.+?)\s*$", text)
        summary_match = re.search(r"(?m)^\*\*一句话总结\*\*[:：]\s*(.+?)\s*$", text)
        entries.append({
            "id": path.stem,
            "title": title_match.group(1).strip() if title_match else path.stem,
            "file": f"paper-notes/{path.name}",
            "section": "notes",
            "summary": (summary_match.group(1).strip() if summary_match else "")[:1000],
            "tags": ["论文笔记"],
            "aliases": [],
            "updatedAt": path.stat().st_mtime_ns,
        })
    return {"version": 1, "entries": entries}


def catalog_payload(knowledge: dict, interview: dict, root: Path | None = None) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    edges: list[dict[str, str]] = []
    for section, graph in (("knowledge", knowledge), ("interview", interview)):
        for node in graph.get("nodes", []):
            if not isinstance(node, dict):
                continue
            node_id = node.get("id")
            label = node.get("label") or node_id
            href = node.get("href")
            if not isinstance(node_id, str) or not isinstance(label, str) or not isinstance(href, str):
                continue
            file = parse_qs(urlsplit(href).query).get("f", [""])[0]
            if not file.startswith("pages/") or not file.endswith(".md"):
                continue
            entries.append({
                "id": node_id,
                "title": label,
                "file": file,
                "section": section,
                "tags": [tag for tag in node.get("tags", []) if isinstance(tag, str)][:50],
                "summary": str(node.get("summary") or "")[:1000],
                "confidence": str(node.get("confidence") or "")[:20],
            })
        for edge in graph.get("edges", []):
            if isinstance(edge, dict) and isinstance(edge.get("source"), str) and isinstance(edge.get("target"), str):
                edges.append({"section": section, "source": edge["source"], "target": edge["target"]})
    if root is not None:
        entries.extend(paper_notes_payload(root)["entries"])
    return {"version": 1, "entries": entries, "edges": edges}
