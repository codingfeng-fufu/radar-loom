#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 健康检查(§12-§13)。

检查断链、缺字段、非法 tag、概念页缺分类、重复嫌疑页等。
退出码:全部通过 → 0;存在任一 ERROR → 1(WARN 不影响退出码)。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402
import build_index  # noqa: E402
import render_graph  # noqa: E402
import taxonomy_models as tm  # noqa: E402

VALID_CONFIDENCE = {"高", "中", "低"}
CODE_ORDER = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8, "E9": 9, "E10": 10, "E11": 11,
              "E12": 12, "E13": 13, "E14": 14, "E15": 15, "E16": 16, "E17": 17, "E18": 18, "E19": 19, "E20": 20,
              "W1": 21, "W2": 22, "W3": 23}
INTERVIEW_HEADINGS = ("面试问题", "考察意图", "30 秒回答", "2 分钟回答", "原理拆解", "递进追问与参考回答", "常见错误回答", "评分标准", "关联概念", "来源核验", "更新记录")

RAW_MATH_PATTERNS = (
    re.compile(r"\\(?:frac|sum|prod|mathbb|mathbf|mathrm|theta|epsilon|alpha|beta|gamma|pi|mid|left|right|sqrt|cdot|propto|argmax|argmin|deg)\b"),
    re.compile(r"[√∑∏‖]"),
    re.compile(r"(?:[A-Za-z]\s*[+*/−-]\s*)+[A-Za-z]\s*(?:≈|=)"),
)
SUBSCRIPT_PATTERN = re.compile(r"(?<![A-Za-z0-9Α-Ωα-ω])((?:[A-Za-z]|[Α-Ωα-ω])[A-Za-z0-9Α-Ωα-ω]*)_[A-Za-z0-9{Α-Ωα-ω]")


def normalize_tags(fm: dict) -> list:
    """frontmatter 的 tags 归一为 list;缺失→[],非 list→单元素 list。"""
    raw = fm.get("tags")
    if isinstance(raw, list):
        return raw
    if raw is None:
        return []
    return [str(raw)]


def is_optional_local_source(path: str | None) -> bool:
    """Local research inputs may be intentionally omitted from public clones."""
    if not path:
        return False
    return Path(path).parts[:1] in {("papers",), ("raw",)}


def check_update_record(body: str) -> tuple[bool, bool]:
    """返回(「更新记录」小节是否存在, 是否有 `- ` 条目)。"""
    lines = body.split("\n")
    in_sec = False
    exists = False
    has_entry = False
    for line in lines:
        if line.strip() == "## 更新记录":
            in_sec = True
            exists = True
            continue
        if in_sec and line.startswith("## "):
            in_sec = False  # 进入下一节
        if in_sec and line.lstrip().startswith("- "):
            has_entry = True
    return exists, has_entry


def undelimited_math_lines(body: str) -> list[int]:
    """返回疑似包含未定界数学表达式的正文行号。"""
    findings: list[int] = []
    in_fence = False
    display_end: str | None = None
    for number, original in enumerate(body.splitlines(), 1):
        stripped = original.lstrip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        line = original
        if display_end:
            if display_end in line:
                line = line.split(display_end, 1)[1]
                display_end = None
            else:
                continue
        for start, end in (("$$", "$$"), (r"\[", r"\]")):
            while start in line:
                before, after = line.split(start, 1)
                if end in after:
                    line = before + " " + after.split(end, 1)[1]
                else:
                    line = before
                    display_end = end
                    break
            if display_end:
                break

        line = re.sub(r"`[^`\n]*`", " ", line)
        line = re.sub(r"\\\([^\n]*?\\\)", " ", line)
        line = re.sub(r"(?<!\$)\$(?!\$)[^\n$]+?\$(?!\$)", " ", line)
        line = re.sub(r"https?://\S+", " ", line)
        subscript_math = any(not (len(match.group(1)) > 1 and match.group(1).isupper()) for match in SUBSCRIPT_PATTERN.finditer(line))
        if subscript_math or any(pattern.search(line) for pattern in RAW_MATH_PATTERNS):
            findings.append(number)
    return findings


def parse_args(argv=None):
    return argparse.ArgumentParser(description="检查技术雷达健康状态").parse_args(argv)

def _values(value):
    return value if isinstance(value, list) else ([] if value is None else [value])

def _interview_summary(fm):
    return str(fm.get("summary") or fm.get("摘要") or "").strip()

def _interview_question(fm):
    return str(fm.get("question") or fm.get("original_question") or fm.get("原问题") or fm.get("问题") or "").strip()

def _check_registry(path, pages, add, code):
    if not path.exists():
        return
    try:
        registry = tm.load_registry(path)
        existing = {p.path.relative_to(rc.VAULT_ROOT).as_posix() for p in pages.values()}
        tm.validate_registry(registry, existing)
    except Exception as exc:
        add(path.stem, code, f"[ERROR {code}] {path.name} taxonomy registry invalid or stale: {exc}")


def main(argv=None) -> int:
    parse_args(argv)
    pages = rc.scan_pages()
    knowledge_pages, interview_pages = rc.partition_pages(pages)
    findings: list[tuple[str, int, str]] = []  # (page_name, code_order, line)

    def add(name: str, code: str, line: str) -> None:
        findings.append((name, CODE_ORDER[code], line))

    # Explicit unsupported page types are neither knowledge nor interview pages,
    # but must remain visible to health reporting instead of disappearing.
    for name, info in pages.items():
        if rc.page_type(info) == "invalid":
            add(name, "E12", f"[ERROR E12] 页面《{name}》 page_type 不支持,必须为 interview 或省略(知识页)")

    for name, info in knowledge_pages.items():
        fm = info.frontmatter
        tags = normalize_tags(fm)
        is_struct = any(t in rc.STRUCT_TAGS for t in tags)
        is_home = (name == "首页")

        # ---- E1 断链 / W1 大小写不敏感命中 ----
        for target in info.links:
            resolved = rc.resolve_link(target, pages)
            if resolved is None:
                add(name, "E1", f"[ERROR E1] 页面《{name}》 链接 [[{target}]] 无法解析")
            elif resolved != target:
                add(name, "W1",
                    f"[WARN W1] 页面《{name}》 链接 [[{target}]] 靠大小写不敏感命中 [[{resolved}]],"
                    f"建议改为 [[{resolved}]]")

        # ---- E2 缺来源(STRUCT 页与首页豁免)----
        laiyuan = fm.get("来源", "")
        if (not laiyuan) and not is_struct and not is_home:
            add(name, "E2", f"[ERROR E2] 页面《{name}》 缺少来源(来源字段为空)")

        # ---- E3 缺信度/非法值(同 E2 豁免)----
        xindu = fm.get("信度")
        if (xindu not in VALID_CONFIDENCE) and not is_struct and not is_home:
            add(name, "E3", f"[ERROR E3] 页面《{name}》 信度缺失或非法值(应为 高/中/低)")

        # ---- E4 缺 tags(首页豁免)----
        if len(tags) == 0 and not is_home:
            add(name, "E4", f"[ERROR E4] 页面《{name}》 缺少 tags")

        # ---- E5 非法 tag(无豁免)----
        allowed_all = rc.CATEGORY_TAGS | rc.PROJECT_TAGS | rc.STRUCT_TAGS
        for t in tags:
            if t not in allowed_all:
                add(name, "E5", f"[ERROR E5] 页面《{name}》 含非法 tag「{t}」")

        # ---- E6 概念页缺分类(无 STRUCT 且无 CATEGORY)----
        has_category = any(t in rc.CATEGORY_TAGS for t in tags)
        if not is_struct and not has_category:
            add(name, "E6", f"[ERROR E6] 页面《{name}》 概念页缺少分类标签")

        # ---- W2 概念页更新记录 ----
        if not is_struct and not is_home:
            exists, has_entry = check_update_record(info.body)
            if not exists or not has_entry:
                add(name, "W2", f"[WARN W2] 页面《{name}》 缺少「更新记录」小节或无条目")

            source_type, local_path = rc.parse_source(str(fm.get("来源", "")))
            if source_type == "unknown":
                add(name, "E9", f"[ERROR E9] 页面《{name}》 来源类型未知")
            elif source_type == "local" and not (rc.VAULT_ROOT / local_path).exists() and not is_optional_local_source(local_path):
                add(name, "E9", f"[ERROR E9] 页面《{name}》 本地来源不存在:{local_path}")
            summary = str(fm.get("摘要", "")).strip()
            if not summary:
                add(name, "E10", f"[ERROR E10] 页面《{name}》 缺少摘要")
            elif len(summary) > 60:
                add(name, "W3", f"[WARN W3] 页面《{name}》 摘要超过60字")

        for line_number in undelimited_math_lines(info.body):
            add(name, "E11", f"[ERROR E11] 页面《{name}》 第{line_number}行疑似含未定界数学表达式,请使用 $...$ 或 $$...$$")

    for name, info in interview_pages.items():
        fm = info.frontmatter
        if fm.get("page_type") != "interview":
            add(name, "E12", f"[ERROR E12] 面试页《{name}》 page_type 必须精确为 interview")
        if not _interview_summary(fm):
            add(name, "E12", f"[ERROR E12] 面试页《{name}》 缺少 summary/摘要")
        sources = _values(fm.get("source"))
        if not sources or any(not str(s).strip() or rc.parse_source(str(s))[0] == "unknown" or (rc.parse_source(str(s))[0] == "local" and not (rc.VAULT_ROOT / rc.parse_source(str(s))[1]).exists() and not is_optional_local_source(rc.parse_source(str(s))[1])) for s in sources):
            add(name, "E14", f"[ERROR E14] 面试页《{name}》 source 缺失、非法或本地来源不存在")
        if fm.get("confidence") not in VALID_CONFIDENCE and fm.get("信度") not in VALID_CONFIDENCE:
            add(name, "E12", f"[ERROR E12] 面试页《{name}》 confidence/信度缺失或非法值")
        for key in ("first_recorded", "tags", "roles"):
            if not _values(fm.get(key)) or any(not str(v).strip() for v in _values(fm.get(key))):
                add(name, "E12", f"[ERROR E12] 面试页《{name}》 缺少或为空字段 {key}")
        if str(fm.get("difficulty", "")).strip() not in {"基础", "进阶", "深入"}:
            add(name, "E13", f"[ERROR E13] 面试页《{name}》 difficulty 必须为 基础/进阶/深入")
        if not _interview_question(fm):
            add(name, "E12", f"[ERROR E12] 面试页《{name}》 question/原问题 不能为空")
        if "related_concepts" not in fm:
            add(name, "E12", f"[ERROR E12] 面试页《{name}》 缺少 related_concepts 字段")
        for target in info.links:
            resolved = rc.resolve_link(target, pages)
            if resolved is None:
                add(name, "E15", f"[ERROR E15] 面试页《{name}》 跨区链接 [[{target}]] 无法解析")
        for target in _values(fm.get("related_concepts")):
            if rc.resolve_link(str(target), pages) is None:
                add(name, "E15", f"[ERROR E15] 面试页《{name}》 related_concepts [[{target}]] 无法解析")
        headings = {m.group(1).strip() for m in re.finditer(r"^##+\s+(.+?)\s*$", info.body, re.M)}
        missing = [h for h in INTERVIEW_HEADINGS if h not in headings]
        if missing:
            add(name, "E16", f"[ERROR E16] 面试页《{name}》 缺少必需小节: {', '.join(missing)}")
        if "[TODO" in info.body or "TODO]" in info.body or "<待" in info.body:
            add(name, "E17", f"[ERROR E17] 面试页《{name}》 含未解析占位符")
        for line_number in undelimited_math_lines(info.body):
            add(name, "E18", f"[ERROR E18] 面试页《{name}》 第{line_number}行疑似含未定界数学表达式")

    # Separate generated artifacts by page type.
    expected_index, expected_interview, _ = build_index.render_indexes(pages)
    actual = rc.INDEX_FILE.read_text(encoding="utf-8") if rc.INDEX_FILE.exists() else None
    if actual != expected_index: add("_index", "E8", "[ERROR E8] _index.md 缺失或与页面/摘要实况不一致,请运行 build_index.py")
    actual_i = rc.INTERVIEW_INDEX_FILE.read_text(encoding="utf-8") if rc.INTERVIEW_INDEX_FILE.exists() else None
    if actual_i != expected_interview: add("_interview_index", "E19", "[ERROR E19] _interview_index.md 缺失或与面试页面实况不一致")

    _check_registry(rc.VAULT_ROOT / "taxonomy.json", knowledge_pages, add, "E20")
    if interview_pages or (rc.VAULT_ROOT / "interview-taxonomy.json").exists():
        _check_registry(rc.VAULT_ROOT / "interview-taxonomy.json", interview_pages, add, "E19")

    # ---- E7 重复嫌疑(文件名 casefold+去空格)----
    groups: dict[str, list[str]] = {}
    for name in pages:
        key = name.casefold().replace(" ", "")
        groups.setdefault(key, []).append(name)
    for names in groups.values():
        if len(names) > 1:
            ns = sorted(names)
            for i in range(len(ns)):
                for j in range(i + 1, len(ns)):
                    add(ns[i], "E7", f"[ERROR E7] 页面《{ns[i]}》与《{ns[j]}》 文件名大小写/空格不敏感重复")

    # Graph artifacts are checked independently for knowledge and interview zones.
    registry_path = rc.VAULT_ROOT / "taxonomy.json"
    try:
        registry = tm.load_registry(registry_path) if registry_path.exists() else tm.Registry.empty("", rc.today())
    except Exception as exc:
        add("taxonomy", "E20", f"[ERROR E20] taxonomy.json taxonomy registry invalid or unreadable: {exc}")
        registry = tm.Registry.empty("", rc.today())
    edges, broken, degree = render_graph.graph_data(knowledge_pages)
    expected_graph = render_graph.render_overview(knowledge_pages, edges, broken, degree)
    if not rc.GRAPH_FILE.exists() or rc.GRAPH_FILE.read_text(encoding="utf-8") != expected_graph:
        add("graph", "E20", "[ERROR E20] graph.md 缺失或过期")
    expected_data = render_graph.render_graph_data(knowledge_pages, edges, broken, degree, registry)
    if not rc.GRAPH_DATA_FILE.exists() or rc.GRAPH_DATA_FILE.read_text(encoding="utf-8") != expected_data:
        add("graph-data", "E20", "[ERROR E20] graph-data.json 缺失或过期")
    for tag in rc.CATEGORY_ORDER:
        expected_category, _, _ = render_graph.render_category(tag, knowledge_pages, edges)
        category_path = rc.GRAPH_DIR_FILES[tag]
        if not category_path.exists() or category_path.read_text(encoding="utf-8") != expected_category:
            add(category_path.name, "E20", f"[ERROR E20] {category_path.name} 缺失或过期")
    i_edges, i_broken, i_degree, external = render_graph.interview_graph_data(interview_pages, knowledge_pages)
    i_registry_path = rc.VAULT_ROOT / "interview-taxonomy.json"
    try:
        i_registry = tm.load_registry(i_registry_path) if i_registry_path.exists() else tm.Registry.empty("", rc.today())
    except Exception as exc:
        add("interview-taxonomy", "E19", f"[ERROR E19] interview-taxonomy.json taxonomy registry invalid or unreadable: {exc}")
        i_registry = tm.Registry.empty("", rc.today())
    expected_i_graph = "# 工程面试 · 隔离图谱\n\n" + f"> 生成:{rc.today()} · 内部节点 {len(interview_pages)} · 边 {len(i_edges)} · 断链 {len(i_broken)}\n\n" + "\n".join(render_graph.mermaid_lines(set(interview_pages) | external, i_edges, external)) + "\n"
    if not rc.INTERVIEW_GRAPH_FILE.exists() or rc.INTERVIEW_GRAPH_FILE.read_text(encoding="utf-8") != expected_i_graph:
        add("interview-graph", "E19", "[ERROR E19] interview-graph.md 缺失或过期")
    expected_i_data = render_graph.render_graph_data(interview_pages, i_edges, i_broken, i_degree, i_registry, external_nodes=external, profile="interview", external_pages=knowledge_pages)
    if not rc.INTERVIEW_GRAPH_DATA_FILE.exists() or rc.INTERVIEW_GRAPH_DATA_FILE.read_text(encoding="utf-8") != expected_i_data:
        add("interview-graph-data", "E19", "[ERROR E19] interview-graph-data.json 缺失或过期")

    # ---- 输出(按页面名、code 序排序)----
    findings.sort(key=lambda x: (x[0], x[1]))
    err = 0
    warn = 0
    for _, _, line in findings:
        print(line)
        if line.startswith("[ERROR"):
            err += 1
        else:
            warn += 1
    print(f"健康检查完成:ERROR {err} 条,WARN {warn} 条。")
    return 1 if err > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
