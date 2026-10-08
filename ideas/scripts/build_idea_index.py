#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import idea_common as common  # noqa: E402


def summary(idea: common.Idea) -> str:
    marker = "## 原始想法"
    if marker not in idea.body:
        return ""
    value = idea.body.split(marker, 1)[1].split("\n## ", 1)[0].strip()
    return " ".join(value.split())[:180]


def render(ideas: dict[str, common.Idea]) -> tuple[str, dict]:
    valid = [idea for idea in ideas.values() if common.ID_RE.fullmatch(idea.id)]
    valid.sort(key=lambda idea: (str(idea.metadata.get("updated", "")), idea.id), reverse=True)
    status_counts = Counter(str(idea.metadata.get("status", "captured")) for idea in valid)
    by_problem: dict[str, list[common.Idea]] = defaultdict(list)
    by_domain: dict[str, list[common.Idea]] = defaultdict(list)
    entries = []
    for idea in valid:
        problem = str(idea.metadata.get("problem") or "").strip()
        if problem:
            by_problem[problem].append(idea)
        for domain in common.as_list(idea.metadata.get("domains")):
            by_domain[domain].append(idea)
        entries.append({
            "id": idea.id, "title": idea.title, "file": f"pages/{idea.path.name}",
            "status": str(idea.metadata.get("status") or "captured"),
            "status_label": common.STATUS_LABELS.get(str(idea.metadata.get("status")), "未知"),
            "created": str(idea.metadata.get("created") or ""), "updated": str(idea.metadata.get("updated") or ""),
            "problem": problem, "domains": common.as_list(idea.metadata.get("domains")),
            "blockers": common.as_list(idea.metadata.get("blockers")), "restart_when": common.as_list(idea.metadata.get("restart_when")),
            "derived_from": common.as_list(idea.metadata.get("derived_from")), "combined_into": common.as_list(idea.metadata.get("combined_into")),
            "related_ideas": common.as_list(idea.metadata.get("related_ideas")), "external_refs": common.as_list(idea.metadata.get("external_refs")),
            "summary": summary(idea),
        })
    lines = ["# Idea 索引（机器生成，勿手工编辑）", "", f"> 生成：{common.today()} · Idea {len(valid)} · 运行 `python3 ideas/scripts/build_idea_index.py` 刷新", "", "## 最近更新", ""]
    lines.extend([f"- [{idea.id} · {idea.title}](pages/{idea.path.name}) · {common.STATUS_LABELS.get(str(idea.metadata.get('status')), '未知')} · {idea.metadata.get('updated', '')}" for idea in valid[:10]] or ["- 无"])
    lines.extend(["", "## 按状态", ""])
    for status in common.VALID_STATUSES:
        lines.append(f"### {common.STATUS_LABELS[status]} ({status_counts[status]})")
        selected = [idea for idea in valid if str(idea.metadata.get("status")) == status]
        lines.extend([f"- [{idea.id} · {idea.title}](pages/{idea.path.name})" for idea in selected] or ["- 无"])
        lines.append("")
    lines.extend(["## 按问题", ""])
    for problem, selected in sorted(by_problem.items()):
        lines.append(f"### {problem}")
        lines.extend(f"- {idea.id} · {idea.title}" for idea in selected)
        lines.append("")
    lines.extend(["## 按领域", ""])
    for domain, selected in sorted(by_domain.items()):
        lines.append(f"### {domain}")
        lines.extend(f"- {idea.id} · {idea.title}" for idea in selected)
        lines.append("")
    payload = {"version": 1, "generated": common.today(), "stats": {"ideas": len(valid), "statuses": dict(status_counts)}, "entries": entries}
    return "\n".join(lines).rstrip() + "\n", payload


def main() -> int:
    text, payload = render(common.scan_ideas())
    common.atomic_write(common.INDEX_FILE, text)
    common.atomic_write(common.INDEX_DATA_FILE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"已生成 Idea 索引 | 页面 {payload['stats']['ideas']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
