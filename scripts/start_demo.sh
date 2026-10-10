#!/usr/bin/env bash
set -euo pipefail

# One-command local demo: rebuild lightweight artifacts, then serve the workspace.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="127.0.0.1"
PORT="18081"
SKIP_REFRESH=0

usage() {
  printf '用法: bash scripts/start_demo.sh [--host HOST] [--port PORT] [--skip-refresh]\n'
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:?缺少 --host 参数}"; shift 2 ;;
    --port) PORT="${2:?缺少 --port 参数}"; shift 2 ;;
    --skip-refresh) SKIP_REFRESH=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf '未知参数: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

cd "$ROOT"
command -v python3 >/dev/null 2>&1 || { echo '缺少 python3' >&2; exit 1; }

if [[ "$SKIP_REFRESH" -eq 0 ]]; then
  python3 scripts/build_index.py
  # Graph generation can be unavailable in a minimal clone without optional
  # taxonomy dependencies. The Viewer remains useful, so keep startup alive.
  if ! python3 scripts/render_graph.py; then
    echo '警告: 图谱生成失败，继续启动 Viewer；安装 requirements-taxonomy.txt 后可重试。' >&2
  fi
fi

echo "RadarLoom 已启动: http://${HOST}:${PORT}/viewer.html"
exec python3 scripts/serve_kb.py --host "$HOST" --port "$PORT" --directory "$ROOT"
