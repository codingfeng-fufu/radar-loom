#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 图谱渲染(§10)。

扫描 pages/ 与 首页.md 中的双链,生成 Mermaid 图谱快照 graph.md。
无参数。退出码恒为 0(断链不导致渲染失败)。
"""
import sys
from pathlib import Path

# 确保无论从哪个 cwd 运行都能 import 本目录下的 radar_common
sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402


def main() -> int:
    pages = rc.scan_pages()
    rc.reset_mermaid_id_state()

    # ---- §10.2.2 构建边集与断链 ----
    edges: list[tuple[str, str]] = []
    broken: list[tuple[str, str]] = []
    for name in pages:
        for target in pages[name].links:
            resolved = rc.resolve_link(target, pages)
            if resolved is None:
                broken.append((name, target))  # 断链不进图
            else:
                edges.append((name, resolved))
    # ---- §10.2.3 去重边(保序) ----
    edges = list(dict.fromkeys(edges))

    # ---- §10.2.4 节点集 ----
    node_names = list(pages.keys())

    # ---- §10.2.5 度 / 核心节点 / 孤立节点 ----
    degree = {n: 0 for n in node_names}
    for s, d in edges:
        degree[s] += 1
        degree[d] += 1

    core = sorted(node_names, key=lambda n: (-degree[n], n))[:5]

    # 孤立:度为 0 且不是「首页」。MOC 页若孤立也提示(依 §10.2 括注,见实现报告)。
    isolated = sorted(n for n in node_names if degree[n] == 0 and n != "首页")

    # ---- §10.3 写 graph.md ----
    lines: list[str] = []
    lines.append("# 技术雷达 · 图谱快照")
    lines.append("")
    lines.append(f"> 生成:{rc.today()} · 命令:`python3 scripts/render_graph.py`")
    lines.append(f"> 节点 {len(node_names)} · 边 {len(edges)} · 孤立 {len(isolated)} · 断链 {len(broken)}")
    lines.append("")
    lines.append("在 VSCode 中按 `Ctrl+Shift+V` 预览本文件即可查看图谱。")
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    # 节点按 name 排序(同时确立 Mermaid ID 的确定性分配顺序)
    for n in sorted(node_names):
        lines.append(f'    {rc.mermaid_id(n)}["{n}"]')
    # 边按(源,目标)排序
    for s, d in sorted(edges):
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
    if broken:
        lines.append("")
        lines.append("## 断链")
        lines.append("")
        for s, t in broken:
            lines.append(f"- {s} → {t}")

    rc.GRAPH_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- §10.2.7 stdout ----
    print(f"已生成 graph.md | 节点 {len(node_names)} 边 {len(edges)} 孤立 {len(isolated)} 断链 {len(broken)}")
    for s, t in broken:
        print(f"- {s} → {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
