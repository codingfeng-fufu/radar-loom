"""Read-only discovery of weakly connected or under-described knowledge pages."""
from __future__ import annotations

import re
import json
from collections import Counter
from pathlib import Path


def discover_gaps(root: Path) -> dict[str, object]:
    state_path = root / ".knowledge-gap-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except (OSError, ValueError, json.JSONDecodeError):
        state = {}
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
            "tags": re.findall(r"#[^\s#]+", header),
        }
    gaps = []
    taxonomy = {}
    try:
        taxonomy = json.loads((root / "taxonomy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        taxonomy = {}
    pending = set(taxonomy.get("pending_pages", []))
    low_confidence = Counter()
    for membership in taxonomy.get("memberships", []):
        if float(membership.get("score", 1)) < 0.55:
            low_confidence[Path(str(membership.get("page", ""))).stem] += 1
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
        stable_path = f"pages/{name}.md"
        if stable_path in pending or name in pending:
            reasons.append("taxonomy 待处理")
        if low_confidence[name]:
            reasons.append(f"低置信度归属 {low_confidence[name]} 个")
        candidates = []
        for other, other_info in metadata.items():
            if other == name or other in out_links:
                continue
            shared = len(set(info["tags"]) & set(other_info["tags"]))
            if shared:
                candidates.append((shared, other))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        if reasons:
            score = min(100, len(reasons) * 20 + min(in_count, 10) * 4)
            gaps.append({"file": f"pages/{name}.md", "title": name, "score": score, "status": state.get(f"pages/{name}.md", {}).get("status", "open"), "reasons": reasons, "incoming": in_count, "outgoing": len(out_links), "bodyLength": info["bodyLength"], "suggestedLinks": [{"title": other, "sharedTags": shared} for shared, other in candidates[:5]]})
    gaps.sort(key=lambda item: (-item["score"], item["title"]))
    weak_links = []
    try:
        community = json.loads((root / "community-data.json").read_text(encoding="utf-8"))
        names = {item["id"]: item.get("name", item["id"]) for item in community.get("communities", [])}
        for edge in community.get("edges", []):
            if int(edge.get("count", 0)) <= 1:
                weak_links.append({"source": edge.get("source"), "target": edge.get("target"), "sourceName": names.get(edge.get("source"), edge.get("source")), "targetName": names.get(edge.get("target"), edge.get("target")), "count": edge.get("count", 0)})
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        weak_links = []
    return {"version": 1, "generatedAt": taxonomy.get("generated_at"), "pages": len(paths), "gaps": gaps, "communityWeakLinks": weak_links[:100], "counts": {"gaps": len(gaps), "isolated": sum("孤立节点" in item["reasons"] for item in gaps), "evidenceIncomplete": sum("证据字段不完整" in item["reasons"] for item in gaps), "taxonomyPending": sum("taxonomy 待处理" in item["reasons"] for item in gaps), "lowConfidence": sum("低置信度归属" in " ".join(item["reasons"]) for item in gaps), "communityWeakLinks": len(weak_links)}}


def update_gap_status(root: Path, file: str, status: str) -> dict[str, object]:
    if not file.startswith("pages/") or ".." in Path(file).parts or status not in {"open", "in_progress", "resolved", "dismissed"}:
        raise ValueError("invalid gap status request")
    path = root / file
    if not path.is_file():
        raise FileNotFoundError(file)
    state_path = root / ".knowledge-gap-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except (OSError, ValueError, json.JSONDecodeError):
        state = {}
    state[file] = {"status": status, "updatedAt": __import__("datetime").datetime.now().isoformat()}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"version": 1, "file": file, "status": status}
