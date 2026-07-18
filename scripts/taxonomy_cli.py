#!/usr/bin/env python3
"""Command line interface for the evolving taxonomy."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from taxonomy_engine import TaxonomyEngine, load_config


ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="维护技术雷达的可演化分类图谱")
    parser.add_argument("--profile", choices=("knowledge", "interview"), default="knowledge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    migrate = subparsers.add_parser("migrate", help="从历史标签创建初始分类注册表")
    migrate.add_argument("--dry-run", action="store_true")

    sync = subparsers.add_parser("sync", help="增量同步新增、修改和删除页面")
    sync.add_argument("--page", action="append", dest="pages")
    sync.add_argument("--no-global", action="store_true")

    global_parser = subparsers.add_parser("global", help="执行全库聚类与结构重组")
    global_parser.add_argument("--no-llm", action="store_true")

    status = subparsers.add_parser("status", help="显示分类注册表状态")
    status.add_argument("--json", action="store_true", dest="as_json")

    subparsers.add_parser("validate", help="校验分类注册表")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    engine = TaxonomyEngine(ROOT, load_config(ROOT, args.profile), profile=args.profile)
    try:
        if args.command == "migrate":
            registry = engine.migrate(dry_run=args.dry_run)
            prefix = "迁移预览" if args.dry_run else "迁移完成"
            print(f"{prefix}: 页面 {len(registry.page_fingerprints)}，种子类别 {len(registry.categories)}，历史归属 {len(registry.memberships)}")
        elif args.command == "sync":
            registry = engine.sync(page_paths=args.pages, allow_global=not args.no_global)
            print(f"增量分类完成: 类别 {len(registry.categories)}，归属 {len(registry.memberships)}，待重试 {len(registry.pending_pages)}")
        elif args.command == "global":
            registry = engine.global_rebuild(allow_llm=not args.no_llm)
            print(f"全局重组完成: 类别 {len(registry.categories)}，归属 {len(registry.memberships)}")
        elif args.command == "status":
            status = engine.status()
            if args.as_json:
                print(json.dumps(status, ensure_ascii=False, sort_keys=True))
            else:
                print(f"分类 {status['active_categories']}，归属 {status['memberships']}，待重试 {status['pending_pages']}，累计变化 {status['changes_since_global']}")
        elif args.command == "validate":
            engine.validate()
            print("分类注册表校验通过")
    except Exception as error:
        print(f"分类操作失败: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
