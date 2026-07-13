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

VALID_CONFIDENCE = {"高", "中", "低"}
CODE_ORDER = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "E8": 8, "E9": 9, "E10": 10, "E11": 11, "W1": 12, "W2": 13, "W3": 14}

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


def main(argv=None) -> int:
    parse_args(argv)
    pages = rc.scan_pages()
    findings: list[tuple[str, int, str]] = []  # (page_name, code_order, line)

    def add(name: str, code: str, line: str) -> None:
        findings.append((name, CODE_ORDER[code], line))

    for name, info in pages.items():
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
            elif source_type == "local" and not (rc.VAULT_ROOT / local_path).exists():
                add(name, "E9", f"[ERROR E9] 页面《{name}》 本地来源不存在:{local_path}")
            summary = str(fm.get("摘要", "")).strip()
            if not summary:
                add(name, "E10", f"[ERROR E10] 页面《{name}》 缺少摘要")
            elif len(summary) > 60:
                add(name, "W3", f"[WARN W3] 页面《{name}》 摘要超过60字")

        for line_number in undelimited_math_lines(info.body):
            add(name, "E11", f"[ERROR E11] 页面《{name}》 第{line_number}行疑似含未定界数学表达式,请使用 $...$ 或 $$...$$")

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

    expected_index, _, _, _ = build_index.render_index(pages)
    actual_index = rc.INDEX_FILE.read_text(encoding="utf-8") if rc.INDEX_FILE.exists() else None
    if actual_index != expected_index:
        add("_index", "E8", "[ERROR E8] _index.md 缺失或与页面/摘要实况不一致,请运行 build_index.py")

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
