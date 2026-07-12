#!/usr/bin/env python3
"""Render a core overview and eight category graphs."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402


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
    pages = rc.scan_pages()
    edges, broken, degree = graph_data(pages)
    rc.GRAPH_FILE.write_text(render_overview(pages, edges, broken, degree), encoding="utf-8")
    print(f"已生成 graph.md | 概览节点 {min(15, len(pages))}")
    for tag in rc.CATEGORY_ORDER:
        text, node_count, edge_count = render_category(tag, pages, edges)
        path = rc.GRAPH_DIR_FILES[tag]
        path.write_text(text, encoding="utf-8")
        print(f"已生成 {path.name} | 节点 {node_count} 边 {edge_count}")
    print(f"全库节点 {len(pages)} · 边 {len(edges)} · 断链 {len(broken)}")
    for source, target in broken:
        print(f"  - {source} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
