#!/usr/bin/env python3
"""Serve the knowledge base and keep generated index/graph files fresh."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ALLOWED_ORIGIN = "http://127.0.0.1:18080"


class RefreshError(RuntimeError):
    """Raised when a generated knowledge-base artifact cannot be refreshed."""


class KnowledgeBuilder:
    def __init__(self, root: Path | str, timeout: int = 30):
        self.root = Path(root).resolve()
        self.timeout = timeout
        self._lock = threading.Lock()
        self._scripts = (
            self.root / "scripts" / "build_index.py",
            self.root / "scripts" / "render_graph.py",
        )
        self._outputs = (
            self.root / "_index.md",
            self.root / "graph-data.json",
        )

    def source_paths(self) -> list[Path]:
        paths = sorted((self.root / "pages").glob("*.md"))
        home = self.root / "首页.md"
        if home.exists():
            paths.append(home)
        return paths

    def is_stale(self) -> bool:
        if any(not output.exists() for output in self._outputs):
            return True
        sources = self.source_paths()
        if not sources:
            return False
        newest_source = max(path.stat().st_mtime_ns for path in sources)
        oldest_output = min(path.stat().st_mtime_ns for path in self._outputs)
        return newest_source > oldest_output

    def revision(self) -> str:
        graph_data = self.root / "graph-data.json"
        if not graph_data.exists():
            raise RefreshError("graph-data.json was not generated")
        return hashlib.sha256(graph_data.read_bytes()).hexdigest()[:16]

    def refresh(self, force: bool = False) -> dict[str, object]:
        with self._lock:
            if not force and not self.is_stale():
                return {"rebuilt": False, "revision": self.revision(), "output": ""}

            output_lines = []
            for script in self._scripts:
                if not script.exists():
                    raise RefreshError(f"missing generator: {script.relative_to(self.root)}")
                try:
                    completed = subprocess.run(
                        [sys.executable, str(script)],
                        cwd=self.root,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        check=False,
                    )
                except subprocess.TimeoutExpired as error:
                    raise RefreshError(f"{script.name} timed out after {self.timeout}s") from error
                combined = "\n".join(part for part in (completed.stdout.strip(), completed.stderr.strip()) if part)
                if completed.returncode != 0:
                    detail = combined or f"exit status {completed.returncode}"
                    raise RefreshError(f"{script.name}: {detail}")
                if combined:
                    output_lines.append(combined)

            return {
                "rebuilt": True,
                "revision": self.revision(),
                "output": "\n".join(output_lines),
            }


class KnowledgeRequestHandler(SimpleHTTPRequestHandler):
    builder: KnowledgeBuilder

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        if urlsplit(self.path).path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
        super().end_headers()

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def refresh_payload(self, force: bool) -> tuple[int, dict[str, object]]:
        try:
            result = self.builder.refresh(force=force)
        except RefreshError as error:
            return 500, {"ok": False, "error": str(error)}
        return 200, {"ok": True, **result}

    def do_OPTIONS(self) -> None:
        if urlsplit(self.path).path != "/api/refresh":
            self.send_error(404)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/refresh":
            self.send_error(404)
            return
        status, payload = self.refresh_payload(force=True)
        self.send_json(status, payload)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/revision":
            status, payload = self.refresh_payload(force=False)
            payload.pop("output", None)
            self.send_json(status, payload)
            return
        if path in {"/_index.md", "/graph-data.json"}:
            status, payload = self.refresh_payload(force=False)
            if status != 200:
                self.send_json(status, payload)
                return
        super().do_GET()


def create_server(
    host: str,
    port: int,
    directory: Path | str,
    builder: KnowledgeBuilder | None = None,
) -> ThreadingHTTPServer:
    root = Path(directory).resolve()
    active_builder = builder or KnowledgeBuilder(root)
    class BoundKnowledgeRequestHandler(KnowledgeRequestHandler):
        pass

    BoundKnowledgeRequestHandler.builder = active_builder
    handler = partial(BoundKnowledgeRequestHandler, directory=str(root))
    return ThreadingHTTPServer((host, port), handler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="提供知识库静态页面并自动刷新索引与图谱")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent.parent)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    server = create_server(args.host, args.port, args.directory)
    print(f"知识库服务已启动:http://{args.host}:{args.port}/viewer.html", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
