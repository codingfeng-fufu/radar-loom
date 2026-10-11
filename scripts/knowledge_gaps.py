"""Read-only discovery of weakly connected or under-described knowledge pages."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


def discover_gaps(root: Path) -> dict[str, object]:
    paths = sorted((root / "pages").glob("*.md"))
    known = {path.stem for path in paths}
    outgoing: dict[str, list[str]] = {}
    incoming: Counter[str] = Counter()
    metadata = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        links = [target.strip() for target in re.findall(r"\[\[([^\]|]+)", text)]
        outgoing[path.stem] = links
        for target in links:
            if target in known:
                incoming[target] += 1
        front = re.search(r"\A---\s*\n(.*?)\n---", text, re.DOTALL)
        header = front.group(1) if front else ""
        body = text[front.end():] if front else text
        metadata[path.stem] = {
            "summary": bool(re.search(r"(?m)^(?:摘要|summary):\s*\S", header)),
            "source": bool(re.search(r"(?m)^(?:来源|source):\s*\S", header)),
            "confidence": bool(re.search(r"(?m)^(?:信度|confidence):\s*\S", header)),
            "bodyLength": len(body.strip()),
        }
    gaps = []
    for name in sorted(known):
        info = metadata[name]
        in_count = incoming[name]
        out_links = [target for target in outgoing[name] if target in known]
        reasons = []
        if in_count == 0 and not out_links:
            reasons.append("孤立节点")
        if in_count >= 5 and not info["summary"]:
            reasons.append("高频引用但缺少摘要")
        if not info["source"] or not info["confidence"]:
            reasons.append("证据字段不完整")
        if len(out_links) == 0 and in_count > 0:
            reasons.append("只有入链，缺少出链")
        if reasons:
            score = min(100, len(reasons) * 20 + min(in_count, 10) * 4)
            gaps.append({"file": f"pages/{name}.md", "title": name, "score": score, "reasons": reasons, "incoming": in_count, "outgoing": len(out_links), "bodyLength": info["bodyLength"]})
    gaps.sort(key=lambda item: (-item["score"], item["title"]))
    return {"version": 1, "pages": len(paths), "gaps": gaps, "counts": {"gaps": len(gaps), "isolated": sum("孤立节点" in item["reasons"] for item in gaps), "evidenceIncomplete": sum("证据字段不完整" in item["reasons"] for item in gaps)}}
