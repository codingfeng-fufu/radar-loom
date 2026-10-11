#!/usr/bin/env python3
"""Create, verify, and stage-restore portable local knowledge-base backups."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / ".backups"
# Portable knowledge state, excluding caches, source code, and machine-local
# Claude/WebUI state.  Ideas and taxonomy registries are first-class user data.
INCLUDE = (
    "pages/*.md", "paper-notes/*.md", "ideas/*.md", "ideas/pages/*.md", "ideas/data/*.json",
    "*.md", "config/*.json", "taxonomy.json", "interview-taxonomy.json",
    "graph-data.json", "community-data.json", "interview-graph-data.json",
)


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
    manifest = {"version": 2, "createdAt": datetime.now().isoformat(), "scope": "portable-knowledge-state", "files": {}}
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
        files_manifest = manifest.get("files", {})
        if not isinstance(files_manifest, dict):
            raise ValueError("manifest files 必须是对象")
        members = {item.filename for item in archive.infolist() if not item.is_dir()}
        if members - set(files_manifest) - {"manifest.json"}:
            raise ValueError("归档包含未列入 manifest 的文件")
        for name, digest in files_manifest.items():
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError(f"非法路径: {name}")
            if name == "manifest.json" or name not in members:
                raise ValueError(f"manifest 文件缺失: {name}")
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


def preview(archive_path: Path, destination: Path) -> dict[str, list[str]]:
    """Compare an archive with a destination without writing any files."""
    manifest = verify(archive_path)
    added, changed, unchanged = [], [], []
    for name, digest in manifest.get("files", {}).items():
        target = destination / name
        if not target.exists():
            added.append(name)
            continue
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            changed.append(name)
        else:
            unchanged.append(name)
    return {"added": sorted(added), "changed": sorted(changed), "unchanged": sorted(unchanged)}


def prune(directory: Path, keep: int) -> None:
    for path in sorted(directory.glob("knowledge-base-*.zip"), reverse=True)[max(1, keep):]:
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify", "preview", "stage-restore"))
    parser.add_argument("archive", nargs="?", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()
    if args.command == "create":
        target = create(args.root, args.destination); prune(args.destination, args.keep)
        print(f"备份完成: {target}")
    elif not args.archive:
        parser.error("verify/preview/stage-restore 需要 archive")
    elif args.command == "verify":
        manifest = verify(args.archive); print(f"校验通过: {len(manifest['files'])} 个文件")
    elif args.command == "preview":
        result = preview(args.archive, args.root)
        print(json.dumps({key: len(value) for key, value in result.items()}, ensure_ascii=False))
    else:
        print(f"恢复演练完成: {stage_restore(args.archive, args.destination)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
