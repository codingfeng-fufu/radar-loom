#!/usr/bin/env python3
"""Export a self-contained static snapshot of the knowledge base."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


EXCLUDED = {'.git', '.trash', '__pycache__'}


def export_static(root: Path, output: Path) -> int:
    output.mkdir(parents=True, exist_ok=True)
    count = 0
    for source in root.rglob('*'):
        relative = source.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts) or relative.parts[:1] == ('output',):
            continue
        target = output / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output/static-kb'))
    args = parser.parse_args()
    print(f'exported {export_static(Path.cwd(), args.output)} files to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
