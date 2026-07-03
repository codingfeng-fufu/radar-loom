#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术雷达 · 健康检查(§12-§13)。

检查断链、缺字段、非法 tag、概念页缺分类、重复嫌疑页等。
退出码:全部通过 → 0;存在任一 ERROR → 1(WARN 不影响退出码)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import radar_common as rc  # noqa: E402

VALID_CONFIDENCE = {"高", "中", "低"}
CODE_ORDER = {"E1": 1, "E2": 2, "E3": 3, "E4": 4, "E5": 5, "E6": 6, "E7": 7, "W1": 8, "W2": 9}


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


def main() -> int:
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
