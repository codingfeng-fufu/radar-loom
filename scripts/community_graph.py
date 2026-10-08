#!/usr/bin/env python3
"""Build the knowledge-page community graph from explicit wikilinks.

This module deliberately excludes interview, project and MOC pages. Community
membership is graph-derived; names and summaries are replaceable derived data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import igraph as ig
import leidenalg

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402

DEFAULT_RESOLUTION = 1.0
DEFAULT_SEED = 42
SCHEMA_VERSION = 1


def _knowledge_pages():
    pages = rc.scan_pages()
    knowledge, _ = rc.partition_pages(pages)
    # MOC and project pages are navigation/implementation structures, not
    # concept entities for the knowledge community graph.
    eligible = {name: page for name, page in knowledge.items()
            if name != "首页"
            and "MOC" not in page.frontmatter.get("tags", [])
            and "项目" not in page.frontmatter.get("tags", [])}
    return knowledge, eligible


def explicit_graph(all_knowledge_pages, eligible_pages):
    edges = []
    broken = []
    for source, page in eligible_pages.items():
        for target in page.links:
            resolved = rc.resolve_link(target, all_knowledge_pages)
            if resolved is None:
                broken.append((source, target))
            elif resolved in eligible_pages and source != resolved:
                edges.append((source, resolved))
    return sorted(set(edges)), sorted(set(broken))


def _stable_partition(nodes, edges, resolution, seed):
    names = sorted(nodes)
    index = {name: i for i, name in enumerate(names)}
    graph = ig.Graph(n=len(names), directed=False)
    pairs = Counter()
    for source, target in edges:
        if source in index and target in index and source != target:
            pairs[tuple(sorted((source, target)))] += 1
    graph.add_edges([(index[a], index[b]) for a, b in sorted(pairs)])
    graph.es["weight"] = [float(pairs[tuple(sorted((names[e.source], names[e.target])))]) for e in graph.es]
    if not names:
        return []
    # Leiden's Python API uses a random seed on the partition object.
    partition = leidenalg.find_partition(
        graph,
        leidenalg.RBConfigurationVertexPartition,
        weights="weight" if graph.ecount() else None,
        resolution_parameter=float(resolution),
        seed=int(seed),
    )
    groups = [sorted(names[i] for i in group) for group in partition]
    return sorted(groups, key=lambda group: (group[0], len(group)))


def _fallback_summary(members, pages):
    summaries = [str(pages[name].frontmatter.get("摘要", "")).strip() for name in members]
    summaries = [item for item in summaries if item]
    title = "、".join(members[:3]) + ("等" if len(members) > 3 else "")
    detail = "；".join(summaries[:3])
    return {
        "name": title or "未命名知识社区",
        "short": f"由 {len(members)} 个知识页通过显式引用形成的主题社区。",
        "detail": detail or "当前尚无可用摘要，社区结构由页面显式引用关系确定。",
        "provider": "fallback",
        "confidence": "低",
    }


def _llm_summary(members, pages, community_id):
    """Optionally ask a local JSON-line command to name/summarize a community.

    The command is opt-in through COMMUNITY_NAMER_COMMAND and cannot alter
    membership. Invalid, timed-out, or unavailable responses use the fallback.
    """
    command = os.environ.get("COMMUNITY_NAMER_COMMAND", "").strip()
    fallback = _fallback_summary(members, pages)
    if not command:
        return fallback
    request = {
        "community_id": community_id,
        "members": [{"title": name, "summary": str(pages[name].frontmatter.get("摘要", ""))} for name in members],
        "instruction": "仅命名并摘要这个已确定的页面集合，不得增删成员或捏造引用。返回 name、short、detail 三个字符串。",
    }
    try:
        completed = subprocess.run(shlex.split(command), input=json.dumps(request, ensure_ascii=False),
                                   capture_output=True, text=True, timeout=90, check=False)
        result = json.loads(completed.stdout) if completed.returncode == 0 else None
        if not isinstance(result, dict):
            return fallback
        values = {key: str(result.get(key, "")).strip() for key in ("name", "short", "detail")}
        if not all(values.values()) or any(len(values[key]) > limit for key, limit in (("name", 80), ("short", 240), ("detail", 2000))):
            return fallback
        return {"name": values["name"], "short": values["short"], "detail": values["detail"], "provider": "llm", "confidence": "中"}
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return fallback


def build_communities(pages, edges, broken, resolution=DEFAULT_RESOLUTION, seed=DEFAULT_SEED, max_depth=6):
    groups = _stable_partition(set(pages), edges, resolution, seed)
    memberships = {}
    communities = []
    leaf_ids = []
    for members in groups:
        digest = hashlib.sha1("\n".join(members).encode("utf-8")).hexdigest()[:12]
        cid = f"com_{digest}"
        leaf_ids.append(cid)
        for member in members:
            memberships[member] = cid
        summary = _llm_summary(members, pages, cid)
        communities.append({
            "id": cid,
            "level": 1,
            "parent": None,
            "members": members,
            "memberCount": len(members),
            "internalEdgeCount": sum(1 for a, b in edges if a in members and b in members),
            "name": summary["name"],
            "summary": summary["short"],
            "detail": summary["detail"],
            "summaryMeta": {"provider": summary["provider"], "confidence": summary["confidence"]},
        })
    cross = Counter()
    for source, target in edges:
        left, right = memberships.get(source), memberships.get(target)
        if left and right and left != right:
            cross[(left, right)] += 1
    # Recursively collapse the community graph while it still has meaningful
    # structure. This is an optional hierarchy, never a change to page edges.
    current = {cid: set(item["members"]) for cid, item in zip(leaf_ids, communities)}
    level = 1
    while level < max_depth and len(current) >= 3:
        child_edges = [(left, right) for (left, right), count in cross.items() if left in current and right in current]
        parent_groups = _stable_partition(set(current), child_edges, resolution, seed + level)
        if len(parent_groups) <= 1 or len(parent_groups) >= len(current):
            break
        next_current = {}
        for child_ids in parent_groups:
            member_set = sorted(set().union(*(current[child] for child in child_ids)))
            digest = hashlib.sha1((str(level + 1) + "\n" + "\n".join(member_set)).encode("utf-8")).hexdigest()[:12]
            cid = f"com_{digest}"
            summary = _llm_summary(member_set, pages, cid)
            communities.append({
                "id": cid, "level": level + 1, "parent": None,
                "children": sorted(child_ids), "members": member_set, "memberCount": len(member_set),
                "internalEdgeCount": sum(1 for a, b in edges if a in member_set and b in member_set),
                "name": summary["name"], "summary": summary["short"], "detail": summary["detail"],
                "summaryMeta": {"provider": summary["provider"], "confidence": summary["confidence"]},
            })
            for child in child_ids:
                child_item = next(item for item in communities if item["id"] == child)
                child_item["parent"] = cid
            next_current[cid] = set(member_set)
        current = next_current
        level += 1
    community_edges = [
        {"source": left, "target": right, "count": count}
        for (left, right), count in sorted(cross.items())
    ]
    for item in communities:
        if item.get("parent"):
            community_edges.append({"source": item["parent"], "target": item["id"], "count": 0, "edgeType": "hierarchy"})
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": rc.today(),
        "algorithm": {"name": "leiden", "resolution": float(resolution), "seed": int(seed)},
        "stats": {"pages": len(pages), "edges": len(edges), "communities": len(communities), "levels": max((item["level"] for item in communities), default=0)},
        "communities": communities,
        "memberships": memberships,
        "edges": community_edges,
        "broken": [{"source": a, "target": b} for a, b in broken],
    }
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description="生成知识页社区图谱")
    parser.add_argument("--resolution", type=float, default=DEFAULT_RESOLUTION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=rc.VAULT_ROOT / "community-data.json")
    args = parser.parse_args(argv)
    all_knowledge_pages, pages = _knowledge_pages()
    edges, broken = explicit_graph(all_knowledge_pages, pages)
    payload = build_communities(pages, edges, broken, args.resolution, args.seed)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"已生成 {args.output.name} | 社区 {payload['stats']['communities']} | 页面 {len(pages)} | 边 {len(edges)}")
    if broken:
        print(f"断链 {len(broken)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
