#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import idea_common as common  # noqa: E402


def render(ideas: dict[str, common.Idea]) -> tuple[str, dict]:
    valid = {key: idea for key, idea in ideas.items() if common.ID_RE.fullmatch(idea.id)}
    nodes = []
    edges = []
    virtual = set()
    for idea in valid.values():
        status = str(idea.metadata.get("status") or "captured")
        nodes.append({"data": {"id": idea.id, "label": idea.title, "type": "idea", "status": status, "file": f"pages/{idea.path.name}"}})
        problem = str(idea.metadata.get("problem") or "").strip()
        if problem:
            node_id = "problem:" + problem
            virtual.add((node_id, problem, "problem"))
            edges.append({"data": {"id": f"{idea.id}:addresses:{node_id}", "source": idea.id, "target": node_id, "type": "addresses"}})
        for blocker in common.as_list(idea.metadata.get("blockers")):
            node_id = "blocker:" + blocker
            virtual.add((node_id, blocker, "blocker"))
            edges.append({"data": {"id": f"{idea.id}:blocked:{node_id}", "source": idea.id, "target": node_id, "type": "blocked_by"}})
        for relation in ("derived_from", "combined_into", "related_ideas"):
            relation_type = "related_to" if relation == "related_ideas" else relation
            for target in common.as_list(idea.metadata.get(relation)):
                if target in valid:
                    edges.append({"data": {"id": f"{idea.id}:{relation_type}:{target}", "source": idea.id, "target": target, "type": relation_type}})
    nodes.extend({"data": {"id": node_id, "label": label, "type": kind}} for node_id, label, kind in sorted(virtual))
    counts = Counter(node["data"]["status"] for node in nodes if node["data"]["type"] == "idea")
    payload = {"version": 1, "generated": common.today(), "stats": {"ideas": len(valid), "nodes": len(nodes), "edges": len(edges), "statuses": dict(counts)}, "nodes": nodes, "edges": edges}
    lines = ["# Idea 图谱（机器生成，勿手工编辑）", "", f"> 生成：{common.today()} · Idea {len(valid)} · 节点 {len(nodes)} · 边 {len(edges)}", "", "```mermaid", "graph LR"]
    for idea in valid.values():
        label = idea.title.replace('"', "'")
        lines.append(f'    {idea.id.replace("-", "_")}["{label}"]')
    for edge in edges:
        source, target = edge["data"]["source"], edge["data"]["target"]
        if source in valid and target in valid:
            lines.append(f'    {source.replace("-", "_")} --> {target.replace("-", "_")}')
    lines.extend(["```", ""])
    return "\n".join(lines), payload


def main() -> int:
    text, payload = render(common.scan_ideas())
    common.atomic_write(common.GRAPH_FILE, text)
    common.atomic_write(common.GRAPH_DATA_FILE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"已生成 Idea 图谱 | Idea {payload['stats']['ideas']} 节点 {payload['stats']['nodes']} 边 {payload['stats']['edges']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

