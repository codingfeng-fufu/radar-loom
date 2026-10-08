#!/usr/bin/env python3
"""Create, verify, and stage-restore portable local knowledge-base backups."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / ".backups"
INCLUDE = ("pages/*.md", "paper-notes/*.md", "*.md", "config/*.json", "graph-data.json", "community-data.json", "interview-graph-data.json")


def files(root: Path):
    seen = set()
    for pattern in INCLUDE:
        for path in root.glob(pattern):
            if path.is_file() and ".trash" not in path.parts and path not in seen:
                seen.add(path)
                yield path


def create(root: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"knowledge-base-{datetime.now():%Y%m%d-%H%M%S}.zip"
    manifest = {"version": 1, "createdAt": datetime.now().isoformat(), "files": {}}
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files(root):
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            archive.writestr(relative, data)
            manifest["files"][relative] = hashlib.sha256(data).hexdigest()
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    verify(target)
    return target


def verify(archive_path: Path) -> dict:
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"CRC 校验失败: {bad}")
        manifest = json.loads(archive.read("manifest.json"))
        for name, digest in manifest.get("files", {}).items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError(f"非法路径: {name}")
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"摘要不匹配: {name}")
    return manifest


def stage_restore(archive_path: Path, destination: Path | None = None) -> Path:
    verify(archive_path)
    target = destination or Path(tempfile.mkdtemp(prefix="kb-restore-check-"))
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(target)
    return target


def prune(directory: Path, keep: int) -> None:
    for path in sorted(directory.glob("knowledge-base-*.zip"), reverse=True)[max(1, keep):]:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify", "stage-restore"))
    parser.add_argument("archive", nargs="?", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    if args.command == "create":
        target = create(args.root, args.destination); prune(args.destination, args.keep)
        print(f"备份完成: {target}")
    elif not args.archive:
        parser.error("verify/stage-restore 需要 archive")
    elif args.command == "verify":
        manifest = verify(args.archive); print(f"校验通过: {len(manifest['files'])} 个文件")
    else:
        print(f"恢复演练完成: {stage_restore(args.archive, args.destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
