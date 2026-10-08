#!/usr/bin/env python3
"""Diagnose the local knowledge-base runtime without changing user data."""
from __future__ import annotations

import json
import shutil
import socket
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def port_open(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main() -> int:
    checks = []
    for command in ("python3", "node", "npx", "git", "tmux"):
        checks.append({"check": command, "ok": bool(shutil.which(command)), "detail": shutil.which(command) or "未安装"})
    for required in ("viewer.html", "scripts/serve_kb.py", "graph-data.json", "community-data.json"):
        checks.append({"check": required, "ok": (ROOT / required).is_file(), "detail": str(ROOT / required)})
    for port in (18080, 18081):
        checks.append({"check": f"port:{port}", "ok": port_open(port), "detail": "服务运行中" if port_open(port) else "未监听"})
    status = subprocess.run(["git", "-C", str(ROOT), "status", "--short"], capture_output=True, text=True, check=False)
    checks.append({"check": "git-worktree", "ok": status.returncode == 0, "detail": f"{len(status.stdout.splitlines())} 个未提交项目"})
    print(json.dumps({"ok": all(item["ok"] for item in checks if not item["check"].startswith("port:")), "checks": checks}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
