#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 图谱渲染(§10)。

扫描 pages/ 与 首页.md 中的双链,生成 Mermaid 图谱快照。
分层渲染:
  - graph.md        → 概览图(度前15的核心节点,不卡)
  - graph_kg.md     → KG领域子图
  - graph_rag.md    → RAG领域子图
  - graph_trust.md  → 可信度领域子图
"""
import sys
from pathlib import Path

# 确保无论从哪个 cwd 运行都能 import 本目录下的 radar_common
sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402


def render_subgraph(filename: str, title: str, node_filter, pages, edges, description: str):
    """渲染子图的通用函数。"""
    rc.reset_mermaid_id_state()

    # 筛选符合条件的节点
    selected_nodes = [n for n in pages if node_filter(n, pages[n])]
    if not selected_nodes:
        return 0, 0

    # 筛选两端都在selected_nodes里的边
    sub_edges = [(s, d) for s, d in edges if s in selected_nodes and d in selected_nodes]

    # 计算度和核心节点
    degree = {n: 0 for n in selected_nodes}
    for s, d in sub_edges:
        degree[s] += 1
        degree[d] += 1

    core = sorted(selected_nodes, key=lambda n: (-degree[n], n))[:5]
    isolated = sorted(n for n in selected_nodes if degree[n] == 0 and n != "首页")

    # 写文件
    lines = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"> 生成:{rc.today()} · 命令:`python3 scripts/render_graph.py`")
    lines.append(f"> 节点 {len(selected_nodes)} · 边 {len(sub_edges)} · 孤立 {len(isolated)}")
    lines.append("")
    lines.append(description)
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    # 节点按name排序
    for n in sorted(selected_nodes):
        lines.append(f'    {rc.mermaid_id(n)}["{n}"]')
    # 边按(源,目标)排序
    for s, d in sorted(sub_edges):
        lines.append(f"    {rc.mermaid_id(s)} --> {rc.mermaid_id(d)}")
    lines.append("```")
    lines.append("")
    lines.append("## 核心节点(度前 5)")
    lines.append("")
    for n in core:
        lines.append(f"- {n}(度 {degree[n]})")
    lines.append("")
    lines.append("## 孤立节点")
    lines.append("")
    if isolated:
        for n in isolated:
            lines.append(f"- {n}")
    else:
        lines.append("- 无")

    rc.VAULT_ROOT.joinpath(filename).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(selected_nodes), len(sub_edges)


def main() -> int:
    pages = rc.scan_pages()

    # ---- 构建完整边集 ----
    edges: list[tuple[str, str]] = []
    broken: list[tuple[str, str]] = []
    for name in pages:
        for target in pages[name].links:
            resolved = rc.resolve_link(target, pages)
            if resolved is None:
                broken.append((name, target))
            else:
                edges.append((name, resolved))
    edges = list(dict.fromkeys(edges))

    # ---- 计算每个节点的度,用于筛选核心节点 ----
    degree = {n: 0 for n in pages}
    for s, d in edges:
        degree[s] += 1
        degree[d] += 1

    # ---- 1. 概览图:度前15的核心节点 ----
    top15 = sorted(pages.keys(), key=lambda n: (-degree[n], n))[:15]
    _, _ = render_subgraph(
        "graph.md",
        "技术雷达 · 核心图谱概览",
        lambda name, _: name in top15,
        pages,
        edges,
        "只显示度前15的核心枢纽节点,用于快速概览,渲染不卡。"
        "如需查看完整领域图谱,请打开对应子图:"
        ""
        "- graph_kg.md —— KG领域子图"
        "- graph_rag.md —— RAG领域子图"
        "- graph_trust.md —— 可信度领域子图",
    )

    # ---- 2. KG领域子图 ----
    _, _ = render_subgraph(
        "graph_kg.md",
        "技术雷达 · KG领域子图",
        lambda name, p: "KG" in p.frontmatter.get("tags", []),
        pages,
        edges,
        "所有带`KG`标签的概念节点,覆盖知识图谱全领域。",
    )

    # ---- 3. RAG领域子图 ----
    _, _ = render_subgraph(
        "graph_rag.md",
        "技术雷达 · RAG领域子图",
        lambda name, p: "RAG" in p.frontmatter.get("tags", []),
        pages,
        edges,
        "所有带`RAG`标签的概念节点,覆盖检索增强生成全领域。",
    )

    # ---- 4. 可信度领域子图 ----
    _, _ = render_subgraph(
        "graph_trust.md",
        "技术雷达 · 可信度领域子图",
        lambda name, p: "可信度" in p.frontmatter.get("tags", []),
        pages,
        edges,
        "所有带`可信度`标签的概念节点,覆盖可信AI、幻觉检测、可验证性等方向。",
    )

    # ---- stdout 汇总 ----
    print(f"已生成分层图谱:")
    print(f"  - graph.md      → 核心概览(度前15)")
    print(f"  - graph_kg.md   → KG领域子图")
    print(f"  - graph_rag.md  → RAG领域子图")
    print(f"  - graph_trust.md → 可信度领域子图")
    print(f"总节点 {len(pages)} · 总边 {len(edges)} · 断链 {len(broken)}")
    for s, t in broken:
        print(f"  - {s} → {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
