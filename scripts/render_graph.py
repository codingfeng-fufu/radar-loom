#!/usr/bin/env python3
"""Render a core overview and eight category graphs."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402
import taxonomy_models as tm  # noqa: E402


CATEGORY_COLORS = {
    "KG": "#22856f",
    "RAG": "#3978c5",
    "LLM机制": "#c6534f",
    "可信度": "#b57b1f",
    "多智能体": "#7c5cab",
    "基础": "#68717d",
    "评测": "#16849b",
    "前沿": "#b14f85",
}


def graph_data(pages):
    edges = []
    broken = []
    for name, page in pages.items():
        for target in page.links:
            resolved = rc.resolve_link(target, pages)
            if resolved is None:
                broken.append((name, target))
            else:
                edges.append((name, resolved))
    edges = list(dict.fromkeys(edges))
    degree = {name: 0 for name in pages}
    for source, target in edges:
        degree[source] += 1
        degree[target] += 1
    return edges, broken, degree


def interview_graph_data(interview_pages, knowledge_pages):
    """Build the interview profile graph, with knowledge concepts as navigation-only nodes."""
    edges = []
    broken = []
    external = set()
    for name, page in interview_pages.items():
        for target in page.links:
            resolved = rc.resolve_link(target, interview_pages)
            if resolved is None:
                broken.append((name, target))
            else:
                edges.append((name, resolved))
        related = page.frontmatter.get("related_concepts", [])
        if isinstance(related, str):
            related = [related]
        for target in related:
            resolved = rc.resolve_link(target, knowledge_pages)
            if resolved is None:
                broken.append((name, target))
            else:
                external.add(resolved)
                edges.append((name, resolved))
    edges = list(dict.fromkeys(edges))
    degree = {name: 0 for name in interview_pages}
    for source, target in edges:
        if source in degree:
            degree[source] += 1
        if target in degree:
            degree[target] += 1
    return edges, broken, degree, external


def node_kind(page):
    tags = page.frontmatter.get("tags", [])
    if "MOC" in tags:
        return "moc"
    if "项目" in tags:
        return "project"
    return "concept"


def primary_category(page):
    tags = page.frontmatter.get("tags", [])
    return next((tag for tag in rc.CATEGORY_ORDER if tag in tags), None)


def viewer_href(page):
    relative = "首页.md" if page.name == "首页" else f"pages/{page.path.name}"
    return f"viewer.html?f={quote(relative, safe='')}"


def _taxonomy_payload(registry, node_ids=None):
    if registry is None:
        return {
            "schemaVersion": 2,
            "generatedAt": None,
            "categories": [],
            "memberships": [],
            "events": [],
            "publish": {"candidates": [], "representatives": [], "lastRun": None},
            "stats": {"categories": 0, "activeCategories": 0, "memberships": 0, "forming": 0, "pendingPages": 0, "seedCategories": 0, "automaticCategories": 0, "candidates": 0},
        }
    categories = []
    for category_id in sorted(registry.categories):
        category = registry.categories[category_id]
        categories.append({
            "id": category.id,
            "name": category.name,
            "definition": category.definition,
            "status": category.status,
            "namingStatus": category.naming_status,
            "parents": sorted(category.parents),
            "related": sorted(category.related),
            "aliases": sorted(category.aliases),
            "redirectTo": category.redirect_to,
            "createdAt": category.created_at,
            "updatedAt": category.updated_at,
            "lastStableAt": category.last_stable_at,
            "stableRuns": category.stable_runs,
            "algorithmVersion": category.algorithm_version,
            "source": "seed" if category.id.startswith("cat_seed_") else "automatic",
        })
    memberships = []
    for membership in sorted(registry.memberships, key=lambda item: (item.page, item.category_id)):
        memberships.append({
            "page": Path(membership.page).stem,
            "category": membership.category_id,
            "score": membership.score,
            "signals": dict(sorted(membership.signals.items())),
            "reason": membership.reason,
            "firstAssignedAt": membership.first_assigned_at,
            "lastConfirmedAt": membership.last_confirmed_at,
        })
    sorted_events = sorted(
        registry.events,
        key=lambda event: (event.created_at, event.type, tuple(event.category_ids)),
    )[-100:]
    events = [
        {
            "type": event.type,
            "categoryIds": sorted(event.category_ids),
            "reason": event.reason,
            "createdAt": event.created_at,
        }
        for event in sorted_events
    ]
    node_ids = set(node_ids) if node_ids is not None else {Path(item.page).stem for item in registry.memberships}
    raw_candidates = getattr(registry, "candidates", []) or []
    candidates = []
    for candidate in raw_candidates:
        item = candidate.to_dict() if hasattr(candidate, "to_dict") else dict(candidate)
        members = item.get("members", item.get("pages", []))
        members = sorted(Path(m).stem if "/" in str(m) else str(m) for m in members if Path(str(m)).stem in node_ids)
        item["members"] = members
        candidates.append(item)
    candidates.sort(key=lambda item: (str(item.get("category", item.get("id", ""))), item["members"]))
    grouped = {}
    for membership in registry.memberships:
        page_id = Path(membership.page).stem
        if page_id in node_ids:
            grouped.setdefault(membership.category_id, []).append({"page": page_id, "score": membership.score})
    for category in categories:
        if category["status"] == "merged":
            continue
        representatives = sorted(grouped.get(category["id"], []), key=lambda item: (-item["score"], item["page"]))[:5]
        existing = next((item for item in candidates if item.get("category") == category["id"] or item.get("id") == category["id"]), None)
        if existing is None:
            candidates.append({"category": category["id"], "members": sorted(item["page"] for item in grouped.get(category["id"], [])), "representatives": representatives})
        else:
            existing["representatives"] = representatives
    representatives = [
        {"category": category["id"], "pages": [item["page"] for item in sorted(grouped.get(category["id"], []), key=lambda item: (-item["score"], item["page"]))[:5]]}
        for category in categories if category["status"] != "merged"
    ]
    last_run = getattr(registry, "last_run", None)
    last_run = last_run.to_dict() if hasattr(last_run, "to_dict") else last_run
    return {
        "schemaVersion": 2,
        "generatedAt": registry.generated_at,
        "categories": categories,
        "memberships": memberships,
        "events": events,
        "stats": {
            "categories": len(categories),
            "activeCategories": sum(category["status"] != "merged" for category in categories),
            "memberships": len(memberships),
            "forming": sum(category["status"] == "forming" for category in categories),
            "pendingPages": len(registry.pending_pages),
            "seedCategories": sum(c["source"] == "seed" for c in categories),
            "automaticCategories": sum(c["source"] == "automatic" for c in categories),
            "candidates": len(candidates),
        },
        "publish": {"candidates": candidates, "representatives": representatives, "lastRun": last_run},
    }


def render_graph_data(pages, edges, broken, degree, registry=None, *, external_nodes=frozenset(), profile="knowledge", external_pages=None):
    isolated = [name for name, value in degree.items() if value == 0 and name != "首页"]
    nodes = []
    all_names = set(pages) | set(external_nodes)
    for name in sorted(all_names):
        if name in external_nodes and name not in pages:
            nodes.append({"id": name, "label": name, "kind": "concept", "nodeType": "external-concept",
                          "external": True, "tags": [], "category": None, "confidence": "", "summary": "",
                          "degree": 0, "href": viewer_href((external_pages or {}).get(name)) if external_pages and name in external_pages else ""})
            continue
        page = pages[name]
        item = {
            "id": name,
            "label": name,
            "kind": node_kind(page),
            "tags": page.frontmatter.get("tags", []),
            "category": primary_category(page),
            "confidence": page.frontmatter.get("信度", ""),
            "summary": page.frontmatter.get("摘要", ""),
            "degree": degree[name],
            "href": viewer_href(page),
        }
        if profile == "interview":
            item.update({"external": False, "nodeType": "interview"})
        nodes.append(item)
    graph_edges = [
        {"id": f"e{index:04d}", "source": source, "target": target}
        for index, (source, target) in enumerate(sorted(edges), start=1)
    ]
    payload = {
        "generated": rc.today(),
        "stats": {
            "nodes": len(pages) if profile == "interview" else len(nodes),
            "nodeCount": len(pages) if profile == "interview" else len(nodes),
            "internalNodeCount": len(pages),
            "externalNodeCount": len(nodes) - len(pages),
            "edges": len(graph_edges),
            "isolated": len(isolated),
            "broken": len(broken),
        },
        "categories": CATEGORY_COLORS,
        "nodes": nodes,
        "edges": graph_edges,
        "taxonomy": _taxonomy_payload(registry, pages),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def mermaid_lines(nodes, edges, external=frozenset()):
    rc.reset_mermaid_id_state()
    lines = ["```mermaid", "graph LR"]
    for name in sorted(nodes):
        suffix = ":::ext" if name in external else ""
        lines.append(f'    {rc.mermaid_id(name)}["{name}"]{suffix}')
    for source, target in sorted(edges):
        lines.append(f"    {rc.mermaid_id(source)} --> {rc.mermaid_id(target)}")
    if external:
        lines.append("    classDef ext fill:#eee,stroke:#999;")
    lines.append("```")
    return lines


def render_overview(pages, edges, broken, degree):
    top = sorted(pages, key=lambda n: (-degree[n], n))[:15]
    nodes = set(top)
    overview_edges = [(s, d) for s, d in edges if s in nodes and d in nodes]
    isolated = sorted(n for n, value in degree.items() if value == 0 and n != "首页")
    lines = [
        "# 技术雷达 · 核心图谱概览", "",
        f"> 生成:{rc.today()} · 命令:`python3 scripts/render_graph.py`",
        f"> 全库:节点 {len(pages)} · 边 {len(edges)} · 孤立 {len(isolated)} · 断链 {len(broken)}",
        f"> 概览:节点 {len(nodes)} · 边 {len(overview_edges)}（全库度前 15 的诱导子图）", "",
        "分类子图：", "",
    ]
    for tag in rc.CATEGORY_ORDER:
        lines.append(f"- `{rc.GRAPH_DIR_FILES[tag].name}` — {tag}")
    lines.extend(["", *mermaid_lines(nodes, overview_edges), "", "## 核心节点(全库度前 5)", ""])
    for name in sorted(pages, key=lambda n: (-degree[n], n))[:5]:
        lines.append(f"- {name}(度 {degree[name]})")
    lines.extend(["", "## 孤立节点(全库口径)", ""])
    lines.extend([f"- {name}" for name in isolated] or ["- 无"])
    if broken:
        lines.extend(["", "## 断链", ""])
        lines.extend(f"- {source} → {target}" for source, target in broken)
    return "\n".join(lines) + "\n"


def render_category(tag, pages, edges):
    seeds = {name for name, page in pages.items() if tag in page.frontmatter.get("tags", [])}
    nodes = set(seeds)
    for source, target in edges:
        if source in seeds or target in seeds:
            nodes.update((source, target))
    selected_edges = [(s, d) for s, d in edges if s in nodes and d in nodes and (s in seeds or d in seeds)]
    lines = [
        f"# 技术雷达 · {tag} 分类子图", "",
        f"> 生成:{rc.today()} · 核心节点 {len(seeds)} · 含一跳邻居节点 {len(nodes)} · 边 {len(selected_edges)}", "",
        "灰色节点为分类外的一跳邻居。", "",
        *mermaid_lines(nodes, selected_edges, nodes - seeds),
    ]
    return "\n".join(lines) + "\n", len(nodes), len(selected_edges)


def parse_args(argv=None):
    return argparse.ArgumentParser(description="生成技术雷达分层图谱").parse_args(argv)


def main(argv=None) -> int:
    parse_args(argv)
    all_pages = rc.scan_pages()
    pages, interview_pages = rc.partition_pages(all_pages)
    registry_path = rc.VAULT_ROOT / "taxonomy.json"
    registry = tm.load_registry(registry_path) if registry_path.exists() else tm.Registry.empty("", rc.today())
    existing_pages = {
        page.path.relative_to(rc.VAULT_ROOT).as_posix()
        for page in pages.values()
    }
    tm.validate_registry(registry, existing_pages)
    edges, broken, degree = graph_data(pages)
    rc.GRAPH_FILE.write_text(render_overview(pages, edges, broken, degree), encoding="utf-8")
    rc.GRAPH_DATA_FILE.write_text(
        render_graph_data(pages, edges, broken, degree, registry),
        encoding="utf-8",
    )
    print(f"已生成 graph.md | 概览节点 {min(15, len(pages))}")
    print(f"已生成 graph-data.json | 节点 {len(pages)} 边 {len(edges)}")
    for tag in rc.CATEGORY_ORDER:
        text, node_count, edge_count = render_category(tag, pages, edges)
        path = rc.GRAPH_DIR_FILES[tag]
        path.write_text(text, encoding="utf-8")
        print(f"已生成 {path.name} | 节点 {node_count} 边 {edge_count}")
    print(f"全库节点 {len(pages)} · 边 {len(edges)} · 断链 {len(broken)}")
    for source, target in broken:
        print(f"  - {source} → {target}")

    interview_registry_path = rc.VAULT_ROOT / "interview-taxonomy.json"
    interview_registry = (tm.load_registry(interview_registry_path)
                          if interview_registry_path.exists()
                          else tm.Registry.empty("", rc.today()))
    interview_existing = {page.path.relative_to(rc.VAULT_ROOT).as_posix() for page in interview_pages.values()}
    tm.validate_registry(interview_registry, interview_existing)
    i_edges, i_broken, i_degree, external = interview_graph_data(interview_pages, pages)
    rc.INTERVIEW_GRAPH_FILE.write_text(
        "# 工程面试 · 隔离图谱\n\n" +
        f"> 生成:{rc.today()} · 内部节点 {len(interview_pages)} · 边 {len(i_edges)} · 断链 {len(i_broken)}\n\n" +
        "\n".join(mermaid_lines(set(interview_pages) | external, i_edges, external)) + "\n",
        encoding="utf-8",
    )
    rc.INTERVIEW_GRAPH_DATA_FILE.write_text(
        render_graph_data(interview_pages, i_edges, i_broken, i_degree, interview_registry,
                          external_nodes=external, profile="interview", external_pages=pages), encoding="utf-8")
    print(f"已生成 interview-graph.md | 节点 {len(interview_pages)} 边 {len(i_edges)}")
    print(f"已生成 interview-graph-data.json | 节点 {len(interview_pages)} 边 {len(i_edges)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
